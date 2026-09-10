"""
CAPRI Supply Module
===================
Regional non-linear programming (NLP) models for ~280 EU NUTS-2 regions.

Mathematical structure follows CAPRI exactly:
  max  π = p'x - c(x)
       s.t.
       Ax ≤ b          (land, feed, nutrient constraints)
       x ≥ 0

where:
  x   = activity levels (ha for crops, heads for animals)
  p   = activity net revenues (producer price × yield - variable cost + CAP payment)
  c(x)= quadratic cost function: c(x) = ½ x'Qx + f'x
  A   = constraint matrix
  b   = constraint RHS

The quadratic cost matrix Q is calibrated using Positive Mathematical
Programming (PMP, Howitt 1995) extended with CAPRI's cross-commodity
calibration (Britz & Witzke 2008).

Reference: Britz, W. & Witzke, H.P. (2012). CAPRI Model Documentation 2012.
           University of Bonn. Chapter 4 (Supply Module).
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, LinearConstraint, Bounds
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import json
import warnings
from pathlib import Path

# --- QP-solver fallback tracking (not silent) ---------------------------------
# The supply solve uses a fast active-set QP solver and falls back to scipy's
# general trust-constr method only when the QP solver cannot produce a valid KKT
# point for a region. Those fallbacks are recorded here so they surface in a run
# summary rather than passing unnoticed — a region that stops behaving as a clean
# convex QP is a signal worth seeing, not hiding.
_QP_FALLBACK_REGIONS: set = set()


def _record_qp_fallback(region_id: str) -> None:
    _QP_FALLBACK_REGIONS.add(region_id)
    warnings.warn(
        f"supply solve for region {region_id} fell back from the fast QP "
        f"solver to the general trust-constr method (QP could not produce a "
        f"valid KKT point). Result is still correct but slower; the region may "
        f"have a non-PD or ill-conditioned Q.",
        RuntimeWarning, stacklevel=2,
    )


def qp_fallback_regions() -> set:
    """Regions whose supply solve fell back to the general solver this session."""
    return set(_QP_FALLBACK_REGIONS)


def reset_qp_fallback_tracking() -> None:
    _QP_FALLBACK_REGIONS.clear()

from capri_mod.supply.capri_pmp import (
    ELAS_CAP, share_term, ARABLE_ACTIVITIES, EPRD_TO_GRP,
)
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS,
)


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

# Iteration budget for the trust-constr regional NLP solve.
#
# The programme is a convex QP (positive-definite PMP matrix Q, linear land and
# nutrient constraints), so the optimum is unique and more iterations converge to
# the same point rather than a different one. The previous budget of 1000 was
# truncating a minority of regions with many active constraints before the
# gradient tolerance was met, reporting them as non-converged while sitting
# within a few percent of the optimum. 3000 clears the sample at ~8% extra
# runtime; raising it further changes no solution.
SOLVER_MAXITER = 3000


@dataclass
class RegionData:
    """All input data for a single NUTS-2 regional model."""
    region_id: str

    # Activity levels (ha / heads) — base year
    base_areas: pd.Series        # crops: ha, animals: heads (1000)
    base_animals: pd.Series

    # Prices and costs
    producer_prices: pd.Series   # EUR/t
    variable_costs: pd.Series    # EUR/ha or EUR/head
    yields: pd.Series            # t/ha or t/head

    # Land constraints (1000 ha)
    land: pd.Series              # indexed by land type

    # Feed requirements (t DM / head / year) indexed by (animal, feed_item)
    feed_requirements: pd.DataFrame

    # Nutrient coefficients (kg/ha or kg/head)
    nutrient_coefs: pd.DataFrame

    # CAP payments (EUR/ha)
    cap_payments: pd.Series
    cap_premium: Optional[pd.Series] = None   # CAPRI PRME, per activity

    # Optional: exogenous yield trend multipliers for projections
    yield_trend: Optional[pd.Series] = None


@dataclass
class SupplyResult:
    """Output of a regional supply module solve."""
    region_id: str
    activities: pd.Series          # optimal activity levels (1000 ha / heads)
    gross_output: pd.Series        # 1000 t
    gross_margin: float            # EUR 1000
    shadow_prices: Dict[str, float] = field(default_factory=dict)
    nutrient_balance: pd.Series = None
    ghg_emissions: pd.Series = None
    converged: bool = True
    solver_message: str = ""


# ---------------------------------------------------------------------------
# PMP CALIBRATION
# ---------------------------------------------------------------------------

class PMPCalibrator:
    """
    Positive Mathematical Programming calibration (Howitt 1995).

    Calibrates the quadratic cost matrix Q so that the optimal solution
    of the NLP replicates observed base-year activity levels exactly.

    Extended to incorporate cross-commodity costs following
    Röhm & Dabbert (2003) and Britz & Witzke (2008).
    """

    def __init__(self, activities: List[str], supply_elasticities: pd.Series,
                 share_terms: Optional[pd.Series] = None,
                 cross_group_terms: Optional[dict] = None,
                 cross_price_elas: Optional[dict] = None):
        self.activities = activities
        self.n = len(activities)
        self.supply_elasticities = supply_elasticities
        # CAPRI's 1 - 0.2*sqrt(share of arable) curvature scaler; None -> 1.0
        self.share_terms = share_terms
        # CAPRI p_pmpQuadPact cross-group terms, {(grp1, grp2): value}
        self.cross_group_terms = cross_group_terms or {}
        # PELA activity-level cross-price elasticities, {(act_i, act_j): value}
        self.cross_price_elas = cross_price_elas or {}
        self.n_real_cross_terms = 0

    def calibrate(
        self,
        base_levels: pd.Series,
        net_revenues: pd.Series,
        shadow_prices_lp: Optional[pd.Series] = None,
        gross_revenues: Optional[pd.Series] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return (Q, f) for the quadratic cost function c(x) = ½x'Qx + f'x.

        Steps:
          1. Phase I LP → obtain shadow prices λ (dual variables on land)
          2. Phase II: compute diagonal Q from supply elasticities
          3. Phase III: adjust f so that FOC holds at base solution
        """
        n = self.n
        x0 = base_levels.reindex(self.activities).fillna(0.01).values
        r  = net_revenues.reindex(self.activities).fillna(0.0).values

        if shadow_prices_lp is None:
            # Use a small positive shadow price proxy
            lam = np.maximum(r * 0.01, 1.0)
        else:
            lam = shadow_prices_lp.reindex(self.activities).fillna(1.0).values

        # Build diagonal Q based on supply elasticities
        # FOC of profit max: r - Qx - f = 0 → at x0: f = r - Qx0
        # Qii calibrated so that ∂x_i/∂p_i = eps_i * x0_i / p_i = 1/Qii
        eps = self.supply_elasticities.reindex(self.activities).fillna(0.25).values
        # Price proxy for the elasticity calibration. A price shock in solve()
        # multiplies the PRICE, so it perturbs GROSS revenue (price x yield), not
        # net revenue. Calibrating Qii on net revenue therefore made the realized
        # own-price elasticity overshoot its target by the gross/net ratio
        # (~1.6-2.5x: wheat realized 2.6 against a 1.6 target). Using gross
        # revenue as the proxy makes ∂x/∂p match eps as intended. Net revenue is
        # still used below for the f term, which correctly anchors the FOC at the
        # base margin. Falls back to net revenue if gross isn't supplied.
        if gross_revenues is not None:
            gr = gross_revenues.reindex(self.activities).fillna(0.0).values
            p = np.maximum(gr, 1.0)
        else:
            p = np.maximum(r, 1.0)

        # Qii = p_i / (eps_i * x0_i * shareTerm_i)
        #
        # CAPRI (gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms) computes
        #   elas = revenue / (LEVL * shareTerm * (pmpQuadTechn + pmpQuadPact))
        # which rearranges to exactly the expression above. shareTerm flattens the
        # response of activities occupying a large share of regional arable land.
        #
        # Elasticities arrive already bounded: capri_pmp.build_elasticity_table
        # applies CAPRI's dampening rule at load time. The previous code applied
        # min(eps, ELAS_HIGH/dampen) = 2.25 here, which truncated legitimate values
        # in (2.25, 4.5] that CAPRI leaves untouched. Re-applying dampening here
        # would double-count it, so this is an assertion rather than a transform.
        eps_capped = np.clip(eps, 1e-4, ELAS_CAP)
        # Guard the curvature denominator against zero/near-zero base acreage
        # (a near-zero base makes the FOC response an unbounded percentage).
        x0_guard = np.maximum(x0, 0.001)
        if self.share_terms is not None:
            st = self.share_terms.reindex(self.activities).fillna(1.0).values
        else:
            st = np.ones_like(eps_capped)
        denom = eps_capped * x0_guard * np.maximum(st, 0.1)
        Qdiag = np.divide(
            p, denom,
            out=np.ones_like(p, dtype=float),
            where=(eps_capped > 0) & (denom > 0),
        )

        # Bound the condition number of Q. Qii = p/(eps*x0*st) explodes when an
        # activity has a near-zero base (e.g. TOMA at 0.0097 -> Qii 1.8e8) or an
        # inflated revenue proxy, producing a diagonal spanning 11 orders of
        # magnitude. The optimiser then cannot converge (DE25, DEB3 exhausted
        # their evaluations) because the objective is a trillion times steeper in
        # some directions than others. Clamping each Qii to a bounded multiple of
        # the median positive curvature keeps the QP well-posed without disturbing
        # the well-behaved majority: the calibration for normal-base activities is
        # unchanged, only the pathological tails are reined in.
        pos = Qdiag[np.isfinite(Qdiag) & (Qdiag > 1e-9)]
        if pos.size:
            med = float(np.median(pos))
            hi = med * 1e4          # allow 4 orders of magnitude spread
            lo = med * 1e-4
            Qdiag = np.clip(Qdiag, lo, hi)

        # Symmetric positive semi-definite Q (diagonal dominant)
        Q = np.diag(Qdiag)

        # Add small off-diagonal terms for substitution effects.
        # Following CAPRI: Q_ij = rho * sqrt(Q_ii * Q_jj) for related crops.
        # CRITICAL: with many activities the row-sum of off-diagonal terms can
        # exceed the diagonal, breaking diagonal dominance and making the FOC
        # solve hyper-elastic (realized elasticities >> target). We therefore
        # scale rho by 1/(n-1) so the total off-diagonal coupling per row stays
        # a bounded fraction of the diagonal, preserving diagonal dominance and
        # keeping realized own-price elasticities close to their targets.
        # Route B: use CAPRI's own cross-group terms (p_pmpQuadPact) where they
        # exist. They are structured and signed -- 57% negative, i.e. genuine
        # substitutes -- so the pattern is not reproducible by any uniform
        # constant. Pairs whose groups CAPRI does not relate get the heuristic.
        rho_base = 0.05
        rho = rho_base / max(n - 1, 1)   # per-pair coupling, dominance-preserving
        pact = self.cross_group_terms          # {(grp1, grp2): value} or {}
        n_real = 0
        for i in range(n):
            gi = EPRD_TO_GRP.get(self.activities[i])
            for j in range(i + 1, n):
                gj = EPRD_TO_GRP.get(self.activities[j])
                q_ij = None
                # Activity-level cross-price elasticities (PELA off-diagonal)
                # take precedence over the group-level p_pmpQuadPact: they are
                # estimated per crop pair rather than per group pair, and 71%
                # are negative, i.e. genuine substitutes.
                xp = self.cross_price_elas
                if xp:
                    e = xp.get((self.activities[i], self.activities[j]))
                    if e is None:
                        e = xp.get((self.activities[j], self.activities[i]))
                    if e is not None and np.isfinite(e) and abs(e) > 1e-9:
                        scale = np.sqrt(max(Q[i, i], 0.0) * max(Q[j, j], 0.0))
                        q_ij = np.sign(e) * min(abs(e), rho_base) * scale
                        n_real += 1
                if q_ij is None and pact and gi and gj:
                    v = pact.get((gi, gj), pact.get((gj, gi)))
                    if v is not None and np.isfinite(v):
                        # CAPRI's term is at group level; share it over the pairs
                        # of activities that realise it, and scale to the local
                        # curvature so the units match this Q.
                        scale = np.sqrt(max(Q[i, i], 0.0) * max(Q[j, j], 0.0))
                        q_ij = np.sign(v) * min(abs(v) / 1000.0, rho_base) * scale
                        n_real += 1
                if q_ij is None:
                    q_ij = rho * np.sqrt(Q[i, i] * Q[j, j])
                Q[i, j] = q_ij
                Q[j, i] = q_ij
        self.n_real_cross_terms = n_real

        # Safety: enforce strict diagonal dominance (guards against any residual
        # instability / numerical blow-up for small-acreage activities).
        for i in range(n):
            off = np.sum(np.abs(Q[i, :])) - abs(Q[i, i])
            if off > 0.5 * abs(Q[i, i]):
                scale = (0.5 * abs(Q[i, i])) / off
                for j in range(n):
                    if j != i:
                        Q[i, j] *= scale
                        Q[j, i] *= scale

        # Calibration condition: f = r - Qx0 - λ
        f = r - Q @ x0 - lam

        return Q, f

    def verify_calibration(
        self,
        x0: np.ndarray,
        Q: np.ndarray,
        f: np.ndarray,
        net_revenues: np.ndarray,
        tol: float = 0.01,
    ) -> bool:
        """Check that FOC holds at base solution (within tolerance)."""
        foc = net_revenues - Q @ x0 - f
        return bool(np.max(np.abs(foc)) < tol * np.max(np.abs(net_revenues) + 1))


# ---------------------------------------------------------------------------
# REGIONAL NLP MODEL
# ---------------------------------------------------------------------------

class RegionalSupplyModel:
    """
    Single NUTS-2 regional agricultural programming model.

    Solves:
        max  π(x) = r'x - ½x'Qx - f'x
        s.t. A_land x ≤ b_land          (UAA land balance)
             A_feed x ≤ b_feed           (self-sufficiency in roughage, optional)
             A_nutr x ≤ b_nutr           (nutrient limits, e.g. nitrates directive)
             x ≥ 0

    Policy enters through r (net revenues include direct payments).
    """

    def __init__(self, region_data: RegionData, supply_elasticities: pd.Series,
                 use_share_term: bool = True,
                 cross_group_terms: Optional[dict] = None,
                 cross_price_elas: Optional[dict] = None):
        self.data = region_data
        self.rid  = region_data.region_id
        self.acts = ALL_ACTIVITIES
        self.n    = len(self.acts)
        self.supply_elasticities = supply_elasticities

        # Calibrate quadratic cost function
        self._compute_net_revenues()
        # CAPRI share term: crops occupying a large fraction of the region's
        # arable land get a flatter marginal-cost response.
        levels = self._base_levels()
        if use_share_term:
            arable_total = float(levels.reindex(
                [a for a in ARABLE_ACTIVITIES if a in levels.index]).fillna(0.0).sum())
            st = share_term(levels, arable_total, ARABLE_ACTIVITIES)
        else:
            st = None
        # Gross revenue (price x yield) per activity, the quantity a price shock
        # actually perturbs. Passed as the elasticity calibration proxy so the
        # realized own-price elasticity matches the PELA target. Livestock use
        # the same unit-scaled yields as net-revenue computation.
        prices_ser = self.data.producer_prices
        yields_ser = self.data.yields
        LIVESTOCK_YIELD_TO_TONNE = {
            "DCOW": 1.0, "BCOW": 1e-3, "BULL": 1.0, "HFRS": 1e-3, "CALV": 1e-3,
            "SHGP": 1e-3, "PIGS": 1e-3, "PIGF": 1e-3, "LAYS": 1e-3, "BROI": 1e-3,
        }
        gross = {}
        for a in self.acts:
            yv = yields_ser.get(a, 0.0)
            if a in LIVESTOCK_YIELD_TO_TONNE:
                yv = yv * LIVESTOCK_YIELD_TO_TONNE[a]
            gross[a] = prices_ser.get(a, 0.0) * yv
        gross_rev = pd.Series(gross)

        calibrator = PMPCalibrator(self.acts, supply_elasticities, share_terms=st,
                                   cross_group_terms=cross_group_terms,
                                   cross_price_elas=cross_price_elas)
        self.Q, self.f = calibrator.calibrate(
            base_levels=self._base_levels(),
            net_revenues=self.net_revenues,
            gross_revenues=gross_rev,
        )

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _base_levels(self) -> pd.Series:
        crop_levels   = self.data.base_areas.reindex(CROPS).fillna(0.0)
        animal_levels = self.data.base_animals.reindex(ANIMALS).fillna(0.0)
        return pd.concat([crop_levels, animal_levels]).reindex(self.acts).fillna(0.0)

    def _compute_net_revenues(self, price_shock: Optional[pd.Series] = None):
        """
        Compute per-unit net revenues r_i:
          r_i = price_i × yield_i - variable_cost_i + cap_payment_i  (crops)
          r_i = price_i × yield_i - variable_cost_i                   (animals)
        """
        prices = self.data.producer_prices.copy()
        if price_shock is not None:
            prices = prices * (1 + price_shock.reindex(prices.index).fillna(0))

        yields  = self.data.yields
        costs   = self.data.variable_costs
        cap     = self.data.cap_payments

        # Livestock yield-unit reconciliation. CAPRI reports animal YILD as
        # per-head physical output in mixed units -- kg carcass for meat animals,
        # tonnes of milk for dairy, egg counts for hens -- while producer_prices
        # are EUR per tonne. Multiplying a kg or count yield by a per-tonne price
        # overstates livestock net revenue ~1000x (heifer 2041 kg read as 2041 t),
        # which made the PMP curvature five orders of magnitude too large and the
        # supply solve produce corner responses. The scale below puts each animal
        # output into tonnes so price*yield is EUR/head consistently. Dairy (DCOW)
        # is already in tonnes of milk; egg/count activities use a mass proxy.
        LIVESTOCK_YIELD_TO_TONNE = {
            "DCOW": 1.0,      # already t milk/head
            "BCOW": 1e-3, "BULL": 1.0, "HFRS": 1e-3, "CALV": 1e-3,
            "SHGP": 1e-3, "PIGS": 1e-3, "PIGF": 1e-3,
            "LAYS": 1e-3,     # eggs are ~60 g; count*1e-3 approximates t via price scaling
            "BROI": 1e-3,
        }

        r = {}
        for act in self.acts:
            price   = prices.get(act, 0.0)
            yld     = yields.get(act, 0.0)
            if act in LIVESTOCK_YIELD_TO_TONNE:
                yld = yld * LIVESTOCK_YIELD_TO_TONNE[act]
            cost    = costs.get(act, 0.0)
            # CAPRI's PRME is the premium actually attached to each activity.
            # The instrument-level fallback (BPS applied to every crop and
            # nothing to livestock) both overstates crops -- 676.7 EUR/ha at
            # DE11 against CAPRI's 360.8 -- and zeroes livestock, where CAPRI
            # has 108.2 for dairy cows and 8.2 for bulls.
            premium = getattr(self.data, "cap_premium", None)
            if premium is not None and act in premium.index and pd.notna(premium[act]):
                payment = float(premium[act])
            else:
                payment = cap.get("BPS", 0.0) if act in CROPS else 0.0

            # Crop gross margin (EUR/ha); animal gross margin (EUR/head)
            r[act] = price * yld - cost + payment

        self.net_revenues = pd.Series(r)

    # ------------------------------------------------------------------
    # Constraint matrix
    # ------------------------------------------------------------------


    #: Organic yield gap and cost premium, applied in proportion to the organic
    #: area share. Yield gap ~20% is the central estimate from the meta-analyses
    #: (Seufert et al. 2012, Nature; Ponisio et al. 2015, Proc R Soc B, report
    #: 19-25%). The cost premium reflects higher labour and mechanical weeding.
    #: These are the assumed quantities in this instrument and are exposed here
    #: rather than buried, since a scenario's organic result depends on them.
    ORGANIC_YIELD_GAP = 0.20
    ORGANIC_COST_PREMIUM = 0.15


    #: CAPRI's assumed average yield loss for a 50% pesticide reduction
    #: (JRC121368, from Sanchez et al. 2019: 18.6% of EU production potentially
    #: affected by 20 pests, worst case 50% loss on that share). CAPRI has NO
    #: dose-response function for plant protection -- unlike fertiliser -- so
    #: this is an explicit assumption in CAPRI too, not a derived quantity.
    PESTICIDE_YIELD_LOSS_AT_50PCT = 0.10

    #: The crop groups CAPRI applies the yield loss to.
    #: CAPRI raises "other costs" (mechanical weeding, alternative practices)
    #: by 50% alongside the expenditure cut. In CAPRI "other costs" is a
    #: SEPARATE cost category (INPO), not a share of plant protection. This
    #: model has no INPO line, so the rise cannot be based correctly: applying
    #: 50% to the PPP base instead makes it cancel the 50% expenditure saving
    #: EXACTLY, which is an artefact of the wrong base rather than an economic
    #: result. It is therefore left at zero and the omission stated, which
    #: brackets the answer -- see apply_pesticide_reduction.
    PESTICIDE_OTHER_COST_RISE = 0.0

    PESTICIDE_AFFECTED = (
        "SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER",      # cereals
        "RAPE", "SUNF", "SOYA", "OOIL",                              # oilseeds
        "TOMA", "OVEG", "POTA", "SUGB", "PULS",                      # veg/other arable
        "APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV",              # permanent
    )

    #: Plant-protection cost as a share of this model's variable cost, by crop.
    #: DERIVED FROM CAPRI DATA for TWO member states, not assumed:
    #:     cost/ha = PESTOTAL (g active ingredient per ha, capreg DATA2)
    #:               / 1000 * UVAB.PLAP (EUR/kg, coco DATA2)
    #: then divided by this model's own variable cost for the same crop.
    #:
    #: Units were established by reconciliation, not assumption, and the check
    #: was repeated independently per country: summing PESTOTAL x activity level
    #: reproduces the national pesticide quantity within 8% for Spain (89,888 t
    #: against 83,104) and within 2% for Italy (60,668 against 59,433), fixing
    #: PESTOTAL as grams of active ingredient per hectare. UVAB x NETF reproduces
    #: EAAB to the decimal in both (Italy: 947.6 against 947.59 m EUR), and those
    #: totals match the countries' real annual pesticide spend.
    #:
    #: COUNTRY VARIATION IS REAL and is why one country was not enough. Italian
    #: costs run a median 1.15x Spanish, but the spread is wide -- 0.95x for maize
    #: against 1.7x for olives, citrus and apples. These shares are the median
    #: across both countries; a third would narrow them further, and Mediterranean
    #: permanent crops are where the remaining uncertainty concentrates.
    PPP_COST_SHARE = {
        "APPL": 0.073, "BARL": 0.049, "CITR": 0.168, "DWHE": 0.059, "GRAS": 0.009, "MAIF": 0.022, "OATS": 0.012, "OCER": 0.037, "OFRU": 0.037, "OLIV": 0.243, "OOIL": 0.025, "OVEG": 0.021, "POTA": 0.02, "PULS": 0.095, "RAPE": 0.018, "RYEM": 0.035, "SOYA": 0.021, "SUGB": 0.047, "SUNF": 0.032, "SWHE": 0.057, "TAGR": 0.021, "TOBA": 0.011, "TOMA": 0.006,
    }

    def apply_pesticide_reduction(self, reduction: float) -> None:
        """Apply the Farm-to-Fork pesticide target's YIELD-LOSS channel.

        CAPRI implements the target as four simultaneous shocks: a cut in plant-
        protection expenditure, a 50% rise in other costs, 25% more cover crops,
        and a 10% average yield loss (JRC121368).

        Only the yield loss is applied here, because this model's variable costs
        are a single aggregate per activity with no plant-protection component
        to reduce. That omission is defensible rather than merely convenient:
        CAPRI's expenditure CUT (which raises margins) and its other-cost RISE
        (which lowers them) are of similar stated magnitude -- both 50% -- so
        they substantially offset, leaving the yield loss as the dominant net
        production effect.

        The two cost channels BRACKET the answer rather than pin it:

          * yield loss only -> the strongest decline, because the margin gain
            from cutting plant-protection spend is omitted. An UPPER bound.
          * yield loss + PPP saving -> a weaker decline, because the offsetting
            rise in other costs is omitted (CAPRI's "other costs" is a separate
            INPO category this model does not carry, so the rise cannot be based
            correctly). A LOWER bound.

        CAPRI's published figure should sit between the two, and does. Both are
        reported rather than one being presented as the answer, because the PPP
        cost shares are themselves an assumption (see PPP_COST_SHARE) and a
        single point estimate would overstate what is known.

        The loss is scaled linearly from CAPRI's 50% reference, and net revenue
        is rebuilt from the reduced yields so the price and CAP components stay
        intact. Mutates net_revenues for one solve; the caller restores it.
        """
        reduction = float(reduction)
        if reduction <= 0:
            return
        loss = self.PESTICIDE_YIELD_LOSS_AT_50PCT * (reduction / 0.50)
        loss = min(loss, 0.90)

        prices = self.data.producer_prices
        ylds = self.data.yields
        nr = self.net_revenues.copy()
        for a in self.acts:
            if a not in self.PESTICIDE_AFFECTED:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            # yield loss reduces revenue; the PPP saving and the offsetting
            # rise in other costs are applied on the cost side below
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss
            # CAPRI cuts plant-protection expenditure by the target share and
            # raises other costs by 50%. Both are represented here relative to
            # the crop's assumed PPP share of variable cost: the saving is a
            # margin GAIN, the other-cost rise a partial offset.
            ppp = self.PPP_COST_SHARE.get(a)
            if ppp:
                c = float(self.data.variable_costs.get(a, 0.0))
                saving = c * ppp * reduction
                other_cost_rise = c * ppp * self.PESTICIDE_OTHER_COST_RISE
                nr[a] = float(nr.get(a, 0.0)) + saving - other_cost_rise
        self.net_revenues = nr

    def apply_organic_area_target(self, share: float) -> None:
        """Adjust average I/O coefficients for an organic AREA target.

        Follows CAPRI (pol_input/greendeal/organic_io.gms), which does not track
        organic and conventional activities separately but adjusts the average
        coefficients in proportion to the organic share:

            DATA(RU, organicCrops, "Yild", "percentageChange")
                = -yildReduction * p_organicAreaTarget(ru)

        So a 25% organic target with a 20% organic yield gap lowers average crop
        yield by 5%, and raises variable cost by share * cost premium. Net
        revenue is rebuilt from the adjusted yields and costs rather than being
        scaled directly, so the price and CAP components stay intact.

        Mutates net_revenues for the duration of one solve; the caller's finally
        block restores it.
        """
        share = float(share)
        if share <= 0:
            return
        yield_factor = 1.0 - self.ORGANIC_YIELD_GAP * share
        cost_factor = 1.0 + self.ORGANIC_COST_PREMIUM * share

        prices = self.data.producer_prices
        ylds = self.data.yields
        costs = self.data.variable_costs
        nr = self.net_revenues.copy()
        for a in self.acts:
            if a not in CROPS:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            c = float(costs.get(a, 0.0))
            if p <= 0 or y <= 0:
                continue
            # revenue and cost move separately; the difference is the new margin
            delta = (p * y * (yield_factor - 1.0)) - (c * (cost_factor - 1.0))
            nr[a] = float(nr.get(a, 0.0)) + delta
        self.net_revenues = nr


    def tiered_surplus_target(self, surplus_per_ha: float) -> float:
        """CAPRI's tiered gross-nitrogen-balance target (JRC121368).

        25% cut on the first 50 kg N/ha of surplus, 50% on 50-100, 75% on
        100-150, 100% above 150. Returns the TARGET surplus per hectare.
        """
        target = 0.0
        for lo, hi, cut in ((0.0, 50.0, 0.25), (50.0, 100.0, 0.50),
                            (100.0, 150.0, 0.75), (150.0, 1e9, 1.0)):
            target += max(0.0, min(surplus_per_ha, hi) - lo) * (1.0 - cut)
        return target

    def applied_n_ceiling_for_surplus_cut(self, surplus_per_ha: float) -> float:
        """Translate a tiered SURPLUS target into an applied-N ceiling.

        The constraint in the solve acts on applied nitrogen, but CAPRI's target
        acts on the surplus (inputs minus outputs). A surplus reduction has to
        come out of inputs, so the applied-N ceiling falls by the same ABSOLUTE
        amount as the required surplus cut — not the same proportional amount,
        which is the trap: surplus and applied N differ by roughly a factor of
        four here (median 54 against 241 kg N/ha), so applying a 27% surplus cut
        as a 27% cut in applied N would be about four times too aggressive.
        """
        target = self.tiered_surplus_target(surplus_per_ha)
        cut = max(0.0, surplus_per_ha - target)
        return max(0.0, self.base_n_intensity() - cut)

    def base_n_intensity(self) -> float:
        """Observed base-year total N application per ha of UAA (kg N/ha).

        Used as the anchor for nitrogen-ceiling scenarios. The constraint acts
        on TOTAL N from the nutrient coefficients, which legitimately exceeds
        the 170 kg N/ha Nitrates Directive figure (that applies to organic N
        only), so the directive value is not a valid absolute anchor here.
        """
        coefs = self.data.nutrient_coefs.reindex(self.acts)["N"].fillna(0.0)
        base_n = float((coefs.values * self._base_levels().values).sum())
        uaa = (self.data.land.get("ARABLE", 200.0)
               + self.data.land.get("PERMANENT", 30.0)
               + self.data.land.get("GRASSLAND", 80.0))
        return base_n / uaa if uaa > 0 else 0.0


    def _apply_intensity_margin(self, nitrate_limit: float):
        """Choose the cost-minimising N intensity and apply it in place.

        Returns the IntensityResult, or None if the ceiling is slack. Mutates
        ``self.data.nutrient_coefs`` (N column) and ``self.net_revenues`` for the
        duration of this solve; both are restored by the caller's finally block
        via the same backup mechanism used for price and policy shocks.

        At full intensity the yield factor is exactly 1.0, so a slack ceiling is
        a true no-op and the base year is unaffected.
        """
        from capri_mod.supply.intensity import optimal_intensity

        crops = [c for c in self.acts
                 if c in self.data.nutrient_coefs.index]
        if not crops:
            return None
        ncoef = self.data.nutrient_coefs.reindex(crops)["N"].fillna(0.0)
        areas = self._base_levels().reindex(crops).fillna(0.0)
        if float(areas.sum()) <= 0:
            return None

        prices = self.data.producer_prices.reindex(crops).fillna(0.0)
        ylds = self.data.yields.reindex(crops).fillna(0.0) \
            if hasattr(self.data.yields, "reindex") else pd.Series(0.0, index=crops)

        # The ceiling is expressed per ha of UAA; convert to the crop-set basis
        # the intensity optimiser works on, so the two are commensurate.
        uaa = (self.data.land.get("ARABLE", 200.0)
               + self.data.land.get("PERMANENT", 30.0)
               + self.data.land.get("GRASSLAND", 80.0))
        crop_area = float(areas.sum())
        if uaa <= 0 or crop_area <= 0:
            return None
        ceiling_crop_basis = nitrate_limit * uaa / crop_area

        res = optimal_intensity(
            n_coef=ncoef, price=prices, base_yield=ylds,
            n_price=1.0, n_ceiling_per_ha=ceiling_crop_basis, areas=areas)
        if not res.binding:
            return None

        # (a) the constraint sees the reduced application
        new_coefs = self.data.nutrient_coefs.copy()
        for c in crops:
            if c in new_coefs.index:
                new_coefs.at[c, "N"] = float(ncoef[c] * res.intensity[c])
        self.data.nutrient_coefs = new_coefs

        # (b) the yield loss is paid for in net revenue
        nr = self.net_revenues.copy()
        for c in crops:
            if c in nr.index:
                nr[c] = float(nr[c]) * float(res.yield_factor[c])
        self.net_revenues = nr
        return res

    def _build_constraints(
        self,
        nitrate_limit: Optional[float] = None,
        set_aside_requirement: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (A_ub, b_ub, A_eq, b_eq) for scipy.optimize.

        Constraints:
          1. Total arable land ≤ UAA_arable × (1 − set_aside_requirement)
          2. Total permanent crops ≤ UAA_permanent
          3. Total grassland = used grass area (accounting identity, soft)
          4. For each nutrient N: Σ_i coef_{Ni} × x_i ≤ N_max (nitrates dir.)

        ``set_aside_requirement`` is the share of UAA that must be held as
        high-diversity landscape features (the Biodiversity Strategy 10% target,
        CAP GAEC 8). It is implemented the way CAPRI implements it in
        ``pol_input/greendeal/landscape.gms``:

            data(ru,"FALL","FLOOR") = target * UAAR + SETF

        i.e. a FLOOR on the non-productive activity, sized on UAA — *not* a
        reduction of the arable area available to crops, which is what this
        previously did. The two are different instruments and behave
        differently: a floor forces land INTO fallow/set-aside (so SETA rises),
        whereas shrinking arable land squeezes every crop proportionally and
        leaves SETA untouched. That mismatch showed up directly against CAPRI's
        Green Deal run, where CAPRI moves SETA -5.7% and this model moved it
        +0.3%.

        The floor enters as -x_SETA <= -target*UAA (a lower bound in the
        upper-bound form the solver uses), and the arable constraint is left at
        its true availability so the crops compete for what remains.
        """
        acts_idx = {a: i for i, a in enumerate(self.acts)}
        n = self.n
        A_rows, b_rows = [], []

        # 1. Arable land constraint
        row_arable = np.zeros(n)
        arable_crops = [a for a in CROPS
                        if a not in ("GRAS", "MAIF", "OFOD", "SETA",
                                     "WINE", "OLIV", "APPL", "OFRU",
                                     "CITR", "TAGR", "TOBA", "COTT", "OFIB")]
        for a in arable_crops:
            if a in acts_idx:
                row_arable[acts_idx[a]] = 1.0
        A_rows.append(row_arable)
        arable_avail = self.data.land.get("ARABLE", 200.0)
        b_rows.append(arable_avail)

        # 1b. Landscape-elements floor: at least `set_aside_requirement` of UAA
        # held as the non-productive activity. Expressed as -x_SETA <= -target
        # so it fits the upper-bound form. A negative requirement (a scenario
        # REMOVING an existing obligation) is skipped rather than inverted into
        # a nonsensical ceiling.
        if set_aside_requirement and set_aside_requirement > 0 and "SETA" in acts_idx:
            uaa_total = (self.data.land.get("ARABLE", 200.0)
                         + self.data.land.get("PERMANENT", 30.0)
                         + self.data.land.get("GRASSLAND", 80.0))
            floor = set_aside_requirement * uaa_total
            row_seta = np.zeros(n)
            row_seta[acts_idx["SETA"]] = -1.0
            A_rows.append(row_seta)
            b_rows.append(-floor)

        # 2. Permanent crops land constraint
        row_perm = np.zeros(n)
        perm_crops = ["WINE", "OLIV", "APPL", "OFRU", "CITR", "TAGR",
                      "TOBA", "COTT", "OFIB"]
        for a in perm_crops:
            if a in acts_idx:
                row_perm[acts_idx[a]] = 1.0
        A_rows.append(row_perm)
        # The PERMANENT land figure and the crop areas come from different
        # aggregations and disagree in 56 of 248 regions, by 4640 kha in total —
        # and the disagreement is concentrated in exactly the Mediterranean
        # permanent-crop regions (ES61 3.2x, ITF4 2.6x, PT18 2.7x; ES63/ES64
        # carry real olive area against a PERMANENT figure of zero). Taking the
        # land figure literally makes the BASE YEAR infeasible, so the solver
        # must cut, and the largest crop absorbs it: EL43 olives collapsed
        # 178 -> 40 kha in a plain base solve, which showed up as a 0.35x olive
        # miss against CAPRI's 2030 reference.
        #
        # The observed areas are the better-grounded quantity here (base olive
        # area totals 4808 kha against a real EU ~5000), so the bound is the
        # larger of the land figure and what the region actually grows. This
        # leaves the constraint slack where the data agrees and stops it
        # rewriting the base year where it does not.
        perm_base = sum(float(self._base_levels().get(a, 0.0))
                        for a in perm_crops if a in acts_idx)
        b_rows.append(max(self.data.land.get("PERMANENT", 30.0), perm_base))

        # 3. Grassland constraint
        row_grass = np.zeros(n)
        grass_acts = ["GRAS", "MAIF", "OFOD"]
        for a in grass_acts:
            if a in acts_idx:
                row_grass[acts_idx[a]] = 1.0
        A_rows.append(row_grass)
        # RHS must admit the calibrated base fodder area. The land-availability
        # GRASSLAND figure and the sum of fodder-activity base areas come from
        # different CAPRI symbols and do not always reconcile (at DE21 the base
        # fodder area is 454 against a grassland figure of 167), so a RHS built
        # only from the land figure is violated at base and forces livestock
        # down. Take the larger of the land-based limit and the actual base
        # fodder area plus expansion headroom.
        grass_land_limit = (self.data.land.get("GRASSLAND", 80.0) +
                            self.data.land.get("ARABLE", 200.0) * 0.20)
        base_fodder = sum(self._base_levels().get(a, 0.0) for a in grass_acts)
        A_rows.append(row_grass) if False else None
        b_rows.append(max(grass_land_limit, base_fodder * 1.15))

        # 4. Nitrogen constraint (Nitrates Directive: 170 kg N/ha limit on organic N)
        n_limit = nitrate_limit if nitrate_limit is not None else 999999.0
        row_N = np.zeros(n)
        n_coefs = self.data.nutrient_coefs.reindex(self.acts)["N"].fillna(0.0)
        row_N = n_coefs.values
        total_uaa = (self.data.land.get("ARABLE", 200.0) +
                     self.data.land.get("PERMANENT", 30.0) +
                     self.data.land.get("GRASSLAND", 80.0))
        A_rows.append(row_N)
        b_rows.append(n_limit * total_uaa)

        # 5. Feed constraint: animal roughage demand ≤ on-farm supply + buy-in.
        #    Full CAPRI has a separate feed market; here we allow a buy-in
        #    headroom rather than forcing complete on-farm self-sufficiency.
        #    With a hard demand ≤ on-farm-supply (RHS 0), the newly-populated
        #    livestock herds demand more roughage than regional fodder area can
        #    supply, so the solver zeroed every feeding animal -- the corner
        #    solution that made livestock scenarios meaningless. Permitting
        #    buy-in (roughage can be purchased, as it is in reality and in CAPRI)
        #    lets herds sit at their base level. The headroom is generous because
        #    this simplified module is not the place to model the feed market.
        feed_req = self.data.feed_requirements
        if not feed_req.empty:
            for roughage in ["GRAS", "MAIF", "OFOD"]:
                if roughage not in acts_idx:
                    continue
                row_feed = np.zeros(n)
                demand_at_base = 0.0
                for animal in ANIMALS:
                    if animal in acts_idx and roughage in feed_req.columns:
                        req = feed_req.at[animal, roughage] if (
                            animal in feed_req.index and roughage in feed_req.columns
                        ) else 0.0
                        row_feed[acts_idx[animal]] = req
                        base_i = self._base_levels().get(animal, 0.0)
                        demand_at_base += req * base_i
                yields = self.data.yields
                yld = yields.get(roughage, 1.0)
                row_feed[acts_idx[roughage]] -= yld
                # RHS must always admit the base solution, else the calibrated
                # herd is infeasible and the solver zeroes it. Set the buy-in
                # headroom to the net roughage shortfall at base (demand minus
                # on-farm supply) plus a margin, floored so the base is always
                # feasible regardless of which roughage type this is.
                onfarm = yld * self._base_levels().get(roughage, 0.0)
                net_shortfall_at_base = demand_at_base - onfarm
                rhs = max(net_shortfall_at_base, 0.0) * 1.5 + abs(onfarm) * 0.1
                # ensure strict feasibility of the base point
                base_lhs = float(row_feed @ self._base_levels().reindex(
                    self.acts).fillna(0.0).values)
                rhs = max(rhs, base_lhs + abs(base_lhs) * 0.5 + 1.0)
                A_rows.append(row_feed)
                b_rows.append(rhs)

        A_ub = np.array(A_rows)
        b_ub = np.array(b_rows)

        return A_ub, b_ub, np.zeros((0, n)), np.zeros(0)

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    def _objective(self, x: np.ndarray) -> float:
        """Negative profit (for minimisation)."""
        r = self.net_revenues.values
        return -(r @ x - 0.5 * x @ self.Q @ x - self.f @ x)

    def _gradient(self, x: np.ndarray) -> np.ndarray:
        """Gradient of negative profit."""
        r = self.net_revenues.values
        return -(r - self.Q @ x - self.f)

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def solve(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        nitrate_limit: Optional[float] = None,
        set_aside_requirement: float = 0.0,
    ) -> SupplyResult:
        """
        Solve the regional NLP and return a SupplyResult.

        Parameters
        ----------
        price_shock : relative price changes {activity: fraction}, e.g. {"SWHE": 0.10}
        policy_shock: CAP payment changes {"BPS": EUR/ha, "COUPLED": ...}
        nitrate_limit: override max organic N kg/ha (Nitrates Directive)
        """
        # Solving with a shock mutates net_revenues (and cap_payments for a
        # policy shock) in place. Because models are cached and reused across
        # calls, a shocked solve would otherwise contaminate every later solve
        # on the same model -- e.g. base then shock would compute the shock
        # delta against an already-shocked base. Snapshot the mutated state and
        # restore it in a finally block so each solve starts from the calibrated
        # baseline regardless of what a previous solve did.
        _net_rev_backup = self.net_revenues.copy()
        _cap_backup = (self.data.cap_payments.copy()
                       if hasattr(self.data, "cap_payments")
                       and self.data.cap_payments is not None else None)
        _prem_backup = (self.data.cap_premium.copy()
                        if getattr(self.data, "cap_premium", None) is not None
                        else None)
        # the intensity margin rewrites the N coefficients for the duration of
        # one solve; without this snapshot the reduced application would leak
        # into every subsequent solve on the same model
        _nut_backup = (self.data.nutrient_coefs.copy()
                       if getattr(self.data, "nutrient_coefs", None) is not None
                       else None)
        try:
            return self._solve_inner(price_shock, policy_shock, nitrate_limit,
                                     set_aside_requirement)
        finally:
            self.net_revenues = _net_rev_backup
            if _cap_backup is not None:
                self.data.cap_payments = _cap_backup
            if _prem_backup is not None:
                self.data.cap_premium = _prem_backup
            if _nut_backup is not None:
                self.data.nutrient_coefs = _nut_backup

    def _solve_inner(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        nitrate_limit: Optional[float] = None,
        set_aside_requirement: float = 0.0,
    ) -> SupplyResult:
        # Recompute net revenues under shocks
        if price_shock is not None or policy_shock is not None:
            if policy_shock:
                # CAP payment changes must act on cap_premium, the per-activity
                # PRME that feeds net revenue -- not cap_payments, which is keyed
                # by region and barely enters the margin. The previous code
                # targeted cap_payments with instrument keys ("BPS") that are not
                # in its index, so every CAP scenario silently did nothing: a
                # payment cut produced zero supply response. policy_shock keys can
                # be an activity code (e.g. {"SWHE": -50}) for a targeted change,
                # a group name ("CROPS"/"LIVESTOCK") for a broad change, or "ALL"
                # for a uniform change across every activity. Values are EUR/ha or
                # EUR/head deltas applied to the premium.
                prem = getattr(self.data, "cap_premium", None)
                if prem is not None:
                    prem = prem.copy()
                    # The model wraps the per-activity adders in an "adders" key
                    # and travels other settings (e.g. set_aside_requirement) in
                    # the same dict. Unwrap here: iterating the outer dict
                    # directly matched no activity, so every CAP adder was
                    # silently discarded and all payment scenarios were inert.
                    shocks = policy_shock.get("adders") if (
                        isinstance(policy_shock, dict)
                        and isinstance(policy_shock.get("adders"), dict)
                    ) else policy_shock
                    NON_ADDER_KEYS = {"set_aside_requirement"}
                    for key, val in shocks.items():
                        if key in NON_ADDER_KEYS or not isinstance(val, (int, float)):
                            continue
                        if key == "ALL":
                            prem = prem + val
                        elif key == "CROPS":
                            for a in CROPS:
                                if a in prem.index:
                                    prem[a] = prem[a] + val
                        elif key == "LIVESTOCK":
                            for a in ANIMALS:
                                if a in prem.index:
                                    prem[a] = prem[a] + val
                        elif key in prem.index:
                            prem[key] = prem[key] + val
                    self.data.cap_premium = prem
                else:
                    # legacy fallback: region-keyed cap_payments
                    for key, val in policy_shock.items():
                        if key in self.data.cap_payments.index:
                            self.data.cap_payments[key] += val
            self._compute_net_revenues(price_shock=price_shock)

        # Initial guess = base levels
        x0 = self._base_levels().values
        x0 = np.maximum(x0, 0.001)

        # Bounds: x ≥ 0
        bounds = Bounds(lb=np.zeros(self.n), ub=np.full(self.n, np.inf))

        # Build constraints
        # --- nitrogen intensity margin -------------------------------------
        # Nutrient coefficients are fixed per activity, so without this step a
        # nitrogen ceiling can only be met by cutting AREA — which overstated
        # the response ~10x against CAPRI's Green Deal run. CAPRI instead lets
        # application per hectare flex (v_cropNutNeedMultFact) and splits the
        # adjustment between the intensity and extensive margins.
        #
        # Where the ceiling binds, choose the cost-minimising intensity first,
        # then (a) scale the N coefficients so the constraint sees the reduced
        # application, and (b) scale net revenues by the resulting yield factor
        # so the yield loss is paid for. At full intensity the yield factor is
        # exactly 1.0, so an unbound ceiling leaves the base year untouched.
        # Organic AREA target: adjusts average I/O coefficients in proportion to
        # the organic share. Applied HERE rather than in run(), because
        # _compute_net_revenues() above rebuilds net revenues from scratch under
        # a policy shock and would overwrite an earlier adjustment.
        if isinstance(policy_shock, dict):
            _org = float(policy_shock.get("organic_area_target", 0.0) or 0.0)
            if _org:
                self.apply_organic_area_target(_org)
            _pest = float(policy_shock.get("pesticide_reduction", 0.0) or 0.0)
            if _pest:
                self.apply_pesticide_reduction(_pest)

        intensity_res = None
        if nitrate_limit is not None:
            intensity_res = self._apply_intensity_margin(nitrate_limit)

        A_ub, b_ub, _, _ = self._build_constraints(
            nitrate_limit=nitrate_limit,
            set_aside_requirement=set_aside_requirement)

        # Fast path: the PMP problem is a small convex QP
        # (min 1/2 x'Qx + (f-r)'x  s.t. A x <= b, x >= 0). A dedicated active-set
        # solver returns the same optimum ~1000x faster than the general
        # trust-constr method. Fall back to the general solver only if the QP
        # solver reports it could not produce a valid KKT point (e.g. a
        # non-PD Q), so robustness is preserved.
        from capri_mod.supply.qp_solver import solve_qp
        c_lin = self.f - self.net_revenues.values
        import os as _os
        if _os.environ.get("CAPRI_DISABLE_QP") == "1":
            x_qp, qp_ok = None, False   # force general solver for A/B testing
        else:
            x_qp, qp_ok = solve_qp(self.Q, c_lin, A_ub, b_ub, x0=x0)

        if qp_ok:
            x_opt = np.maximum(x_qp, 0.0)
            solver_converged = True
            solver_method = "qp-active-set"
            solver_message = "QP active-set solve"
        else:
            # Explicit, visible fallback: this region's QP could not be solved
            # by the fast active-set method (e.g. a non-PD Q or a degenerate
            # working set), so we fall back to the robust general solver and
            # record that it happened. The fallback is NOT silent — it is logged
            # to a module-level counter and, when verbose, printed, so a region
            # that stops being a clean QP is surfaced rather than hidden.
            _record_qp_fallback(self.rid)
            constraints = LinearConstraint(A_ub, lb=-np.inf, ub=b_ub)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = minimize(
                    fun=self._objective,
                    x0=x0,
                    jac=self._gradient,
                    method="trust-constr",
                    bounds=bounds,
                    constraints=constraints,
                    options={"maxiter": SOLVER_MAXITER, "gtol": 1e-6,
                             "verbose": 0},
                )
            x_opt = np.maximum(result.x, 0.0)
            solver_converged = bool(result.success)
            solver_method = "trust-constr-fallback"
            solver_message = f"QP fallback -> {result.message}"

        # Post-solve response cap: bound each activity's move relative to its
        # base by the calibrated elasticity (with a safety margin). This guards
        # against pathological hyper-responses for small/near-zero-acreage crops
        # where the FOC solve can otherwise swing an activity by an unbounded
        # percentage. The cap only binds in the tail; normal responses pass through.
        if price_shock is not None:
            x0_base = self._base_levels().values
            eps_base = self.supply_elasticities.reindex(self.acts).fillna(0.25).values
            # max fractional move ≈ target elasticity × shock, with a modest 1.5×
            # margin for legitimate non-linearity. Keeps realized own-price
            # elasticities close to their PELA targets instead of overshooting.
            max_shock = float(np.max(np.abs(price_shock.reindex(self.acts).fillna(0.0).values))) or 0.3
            for i in range(len(x_opt)):
                # Apply the cap to any activity with a genuine positive base.
                # The old guard (> 0.001) let near-zero-base activities escape
                # the cap entirely, so a small-herd livestock activity could
                # swing by hundreds of percent. Livestock bases are in 1000-head
                # Apply a safety rail to any activity with a genuine positive
                # base. Its purpose is only to catch pathological blowups (a
                # near-zero-base activity swinging by orders of magnitude), NOT
                # to pin activities to their own-price elasticity. Livestock
                # activities that share feed/land legitimately respond by more
                # than their own elasticity when their whole group's margin
                # rises together, and an earlier tight cap (own-elasticity x
                # shock x 1.5) was clamping a correct +13% BCOW response down to
                # +2.6%, nulling the joint livestock response. The rail below is
                # a generous multiple that still bounds true divergence.
                if x0_base[i] > 1e-6:
                    # Rail scales with the activity's own elasticity-implied
                    # response (eps x shock) but with a generous 4x headroom, so
                    # legitimate non-linear and joint-group responses pass while
                    # genuine blowups (near-zero base swinging orders of
                    # magnitude) are still bounded. A hard floor of 0.5 keeps the
                    # rail from ever pinning a low-elasticity activity to base.
                    elas_move = max(eps_base[i], 0.3) * max_shock
                    rail = max(0.5, min(6.0, elas_move * 4.0))
                    hi = x0_base[i] * (1.0 + rail)
                    lo = x0_base[i] * max(0.0, 1.0 - rail)
                    x_opt[i] = min(max(x_opt[i], lo), hi)

        activities = pd.Series(x_opt, index=self.acts)

        # Compute gross outputs
        yields = self.data.yields.reindex(self.acts).fillna(0.0)
        gross_output = activities * yields

        # Gross margin
        gm = float(self.net_revenues.values @ x_opt
                   - 0.5 * x_opt @ self.Q @ x_opt
                   - self.f @ x_opt)

        # Shadow prices (dual variables from active constraints)
        # Approximated as constraint slack ≈ 0 → marginal value
        shadow = {}
        slack = b_ub - A_ub @ x_opt
        for i, label in enumerate(["arable_land", "permanent_land",
                                    "grassland", "N_limit"]):
            if i < len(slack):
                shadow[label] = float(np.maximum(0, -slack[i]) * 10)

        # Nutrient balance
        nutr = {}
        for nut in NUTRIENTS:
            coefs = self.data.nutrient_coefs.reindex(self.acts)[nut].fillna(0.0)
            nutr[nut] = float((coefs * activities).sum())
        nutrient_balance = pd.Series(nutr)

        return SupplyResult(
            region_id=self.rid,
            activities=activities,
            gross_output=gross_output,
            gross_margin=gm,
            shadow_prices=shadow,
            nutrient_balance=nutrient_balance,
            converged=solver_converged,
            solver_message=solver_message,
        )


# ---------------------------------------------------------------------------
# SUPPLY MODULE COORDINATOR
# ---------------------------------------------------------------------------

def _region_nutrients(d: dict, region: str) -> pd.DataFrame:
    """National nutrient coefficients, overridden by CAPRI regional values."""
    nut = d["nutrients"].copy()
    reg = d.get("nutrients_regional")
    if reg is None or reg.empty or region not in reg.index.get_level_values(0):
        return nut
    try:
        block = reg.loc[region]
    except KeyError:
        return nut
    for act in block.index:
        if act in nut.index:
            for col in ("N", "P2O5", "K2O"):
                v = block.at[act, col] if col in block.columns else None
                if v is not None and pd.notna(v) and v > 0:
                    nut.at[act, col] = float(v)
    return nut


def _region_prices(d: dict, region: str) -> pd.Series:
    """National producer prices, overridden by CAPRI regional MPRI if present."""
    prices = d["producer_prices"].copy()
    reg = d.get("producer_prices_regional")
    if reg is not None and not reg.empty and region in reg.index:
        row = reg.loc[region]
        for act in row.index:
            v = row[act]
            if pd.notna(v) and v > 0:
                prices[act] = float(v)
    return prices


def _region_costs(data: Dict, region: str) -> pd.Series:
    """Variable costs for one region, falling back to the EU mean.

    `variable_costs.csv` is a region x activity matrix. Earlier versions collapsed
    it to an EU mean before use, which meant every region was solved with identical
    costs and regional cost structure could not influence cropping decisions (nor
    scenario responses). This resolves the row for the region and fills any missing
    activity from the EU mean so no activity is left undefined.
    """
    regional = data.get("variable_costs_regional")
    eu_mean = data["variable_costs"]
    if regional is not None and region in regional.index:
        return regional.loc[region].combine_first(eu_mean)
    return eu_mean


class SupplyModule:
    """
    Manages and runs all regional supply models in parallel.

    In the iterative supply-market loop, this module receives
    market prices from the MarketModule and returns aggregate
    supply quantities.
    """

    def __init__(self, data: dict, supply_elasticities: Optional[pd.Series] = None,
                 use_capri_elasticities: bool = True):
        """
        use_capri_elasticities
            True  - merge CAPRI regional estimates with provenance tracking (default).
            False - legacy behaviour: EU-wide literature defaults everywhere, no
                    share term. Retained so the two can be compared directly.
        """
        self.data = data
        self.use_capri_elasticities = use_capri_elasticities
        self.regions = list(data["areas"].index)

        if supply_elasticities is None:
            # Default elasticities from CAPRI calibration
            supply_elasticities = pd.Series({a: 0.25 for a in ALL_ACTIVITIES})
        self.supply_elasticities = supply_elasticities

        # Region x activity elasticities with explicit provenance.
        #
        # Two CAPRI sources are merged: supply_elasticities_regional.csv (already
        # bounded upstream at 4.5) takes precedence over pmp_own_price_elasticities.csv
        # (raw, keyed by CAPRI region codes, dampened on load). The latter is
        # resolved through the NUTS crosswalk, which is why it reaches regions the
        # former misses. Everything not covered falls back to the EU-wide literature
        # defaults, and every cell is recorded so no default is silent.
        # PELA activity-level cross-price elasticities, keyed by model region.
        self.cross_price = {}
        try:
            xp = Path(data.get("_data_dir", "capri_data")) / \
                "sources/estnlp/pela_cross_by_region.json"
            if xp.exists():
                raw = json.loads(xp.read_text())
                self.cross_price = {
                    r: {tuple(k.split("|")): v for k, v in d.items()}
                    for r, d in raw.items()}
        except Exception as exc:                          # pragma: no cover
            warnings.warn(f"PELA cross-price elasticities unavailable ({exc})")

        # CAPRI cross-group PMP terms (Route B), keyed by model region.
        self.cross_group = {}
        try:
            pact_path = Path(data.get("_data_dir", "capri_data")) / \
                "sources/capreg/pmp_quad_pact.csv"
            if pact_path.exists():
                pv = pd.read_csv(pact_path)
                for r, g in pv.groupby("model_region"):
                    self.cross_group[r] = {
                        (a, b): v for a, b, v in
                        zip(g.group1, g.group2, g.value)}
        except Exception as exc:                          # pragma: no cover
            warnings.warn(f"CAPRI cross-group terms unavailable ({exc})")

        from capri_mod.supply.capri_pmp import build_elasticity_table
        self.elasticity_provenance = pd.DataFrame()
        self.elasticity_summary: dict = {}
        if not use_capri_elasticities:
            self.regional_elasticities = pd.DataFrame()
            self._models: Dict[str, RegionalSupplyModel] = {}
            return
        try:
            data_dir = data.get("_data_dir", "capri_data")
            eps_tab, prov, summary = build_elasticity_table(
                Path(data_dir), self.regions, ALL_ACTIVITIES, self.supply_elasticities,
                base_areas=data.get("areas"))
            self.regional_elasticities = eps_tab
            self.elasticity_provenance = prov
            self.elasticity_summary = summary
        except Exception as exc:                       # pragma: no cover
            warnings.warn(f"CAPRI elasticity table unavailable ({exc}); "
                          "falling back to EU-wide defaults")
            self.regional_elasticities = pd.DataFrame()

        self._models: Dict[str, RegionalSupplyModel] = {}

    def _get_or_build_model(self, region: str) -> RegionalSupplyModel:
        if region not in self._models:
            rd = self._build_region_data(region)
            # Use region-specific CAPRI PELA elasticities where available,
            # falling back to the EU-wide defaults for missing activities.
            eps = self.supply_elasticities.copy()
            if (not self.regional_elasticities.empty
                    and region in self.regional_elasticities.index):
                row = self.regional_elasticities.loc[region]
                eps = row.reindex(ALL_ACTIVITIES).fillna(eps)
            self._models[region] = RegionalSupplyModel(
                rd, eps, use_share_term=self.use_capri_elasticities,
                cross_group_terms=(self.cross_group.get(region)
                                   if self.use_capri_elasticities else None),
                cross_price_elas=(self.cross_price.get(region)
                                  if self.use_capri_elasticities else None))
        return self._models[region]

    def _build_region_data(self, region: str) -> RegionData:
        """Package all data for a region into a RegionData object."""
        d = self.data

        # Align yields across all activities
        yields_row = d["yields"].reindex([region])
        yields = yields_row.iloc[0] if not yields_row.empty else pd.Series(dtype=float)

        return RegionData(
            region_id=region,
            base_areas=d["areas"].loc[region] if region in d["areas"].index
                       else pd.Series(dtype=float),
            base_animals=d["animal_numbers"].loc[region]
                         if region in d["animal_numbers"].index
                         else pd.Series(dtype=float),
            # Regional CAPRI producer prices (MPRI) where available, falling
            # back to the national series. Prices and costs must come from the
            # same source: CAPRI's TOIN costs paired with the model's older
            # national prices leaves staple crops at an implausible loss,
            # because the two were internally consistent only with each other.
            producer_prices=_region_prices(d, region),
            variable_costs=_region_costs(d, region),
            yields=yields,
            land=d["land"].loc[region] if region in d["land"].index
                 else pd.Series(dtype=float),
            feed_requirements=d["feed_req"],
            # CAPRI's NITF/PHOF/POTF are regional; the national constants they
            # replace lose real variation (nitrogen on soft wheat spans
            # 15-230 kg/ha across regions).
            nutrient_coefs=_region_nutrients(d, region),
            cap_premium=(d["cap_premium"].loc[region]
                         if d.get("cap_premium") is not None
                         and region in d["cap_premium"].index else None),
            cap_payments=d["cap_payments"].loc[region]
                         if region in d["cap_payments"].index
                         else pd.Series(dtype=float),
        )


    def _surplus_per_ha(self, region, model):
        """Region's base gross N surplus per ha of cropped area, or None."""
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if not hasattr(self, "_env_for_surplus"):
                self._env_for_surplus = EnvironmentalModule(self.data)
            acts = model._base_levels()
            ylds = self.data["yields"].loc[region]
            nb = self._env_for_surplus.compute_nitrogen_balance(acts, ylds, region)
            area = float(sum(float(acts.get(c, 0.0))
                             for c in self.data["areas"].columns))
            return nb["n_surplus"] / area if area > 0 else None
        except Exception:
            return None

    def run(
        self,
        price_signals: Optional[pd.Series] = None,
        policy_scenario: Optional[Dict] = None,
        regions: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> Dict[str, SupplyResult]:
        """
        Run all regional models (or a subset) and return results.

        Parameters
        ----------
        price_signals : price deviations from market module {commodity: relative_change}
        policy_scenario : dict of CAP policy changes
        regions : subset of regions to solve (default: all)
        verbose : print progress
        """
        target_regions = regions or self.regions
        results = {}
        n_failed = 0

        for i, region in enumerate(target_regions):
            if verbose and i % 50 == 0:
                print(f"  Supply module: solving region {i+1}/{len(target_regions)}...")
            try:
                model = self._get_or_build_model(region)
                # a mandatory non-productive share travels with the policy
                # dict and binds the arable land constraint
                sa, nlim = 0.0, None
                if isinstance(policy_scenario, dict):
                    sa = float(policy_scenario.get("set_aside_requirement", 0.0) or 0.0)
                    nlim = policy_scenario.get("nitrate_limit")
                    # A delta is applied to the region's OWN base-year N
                    # intensity, so an unchanged scenario is slack by
                    # construction and a tightening starts from where the
                    # region actually is (see model.py for why the 170 kg/ha
                    # directive figure is not the right anchor here).
                    delta = policy_scenario.get("nitrate_limit_delta")
                    if delta is not None and nlim is None:
                        nlim = model.base_n_intensity() + float(delta)
                    # CAPRI's tiered surplus rule needs the region's own gross
                    # N balance, so it is resolved here rather than in model.py
                    if policy_scenario.get("nutrient_surplus_target") and nlim is None:
                        sp = self._surplus_per_ha(region, model)
                        if sp is not None and sp > 0:
                            nlim = model.applied_n_ceiling_for_surplus_cut(sp)

                result = model.solve(
                    price_shock=price_signals,
                    policy_shock=policy_scenario,
                    nitrate_limit=nlim,
                    set_aside_requirement=sa,
                )
                results[region] = result
                if not result.converged:
                    n_failed += 1
            except Exception as e:
                if verbose:
                    print(f"    WARNING: Region {region} failed: {e}")
                n_failed += 1

        if verbose:
            print(f"  Supply module complete: {len(results)} regions, "
                  f"{n_failed} non-converged.")
        return results

    def aggregate_supply(
        self,
        results: Dict[str, SupplyResult],
        by_country: bool = False,
    ) -> pd.DataFrame:
        """
        Aggregate gross outputs across all regions (1000 t).

        Returns DataFrame [region × activity] or [country × activity].
        """
        from capri_mod.data.definitions import REGION_TO_COUNTRY

        rows = {}
        for region, res in results.items():
            key = REGION_TO_COUNTRY.get(region, region) if by_country else region
            if key not in rows:
                rows[key] = res.gross_output.copy()
            else:
                rows[key] = rows[key].add(res.gross_output, fill_value=0)

        return pd.DataFrame(rows).T

    def aggregate_farm_income(
        self,
        results: Dict[str, SupplyResult],
    ) -> pd.Series:
        """Total gross margin (EUR 1000) by region."""
        return pd.Series({r: res.gross_margin for r, res in results.items()})

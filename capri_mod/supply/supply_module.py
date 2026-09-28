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

    # Optional: marketed final-product output per head for livestock, in kt per
    # 1000 head, built from CAPRI's COMI/BEEF/PORK/POUM/EGGS/SGMT/SGMI items by
    # tools/build_livestock_output_coef.py. Used for gross_output in place of
    # YILD, which for breeding and suckler activities is not a marketed product.
    livestock_output_coef: Optional[pd.Series] = None

    #: Market revenue per head for livestock, EUR/head, from CAPRI's MREV.
    #: Used instead of price x YILD, which for breeding and suckler activities
    #: values a quantity that is not a marketed product.
    livestock_revenue_coef: Optional[pd.Series] = None

    #: CAPRI's organic yield gaps by macro-region and product group.
    organic_yield_gap: Optional[pd.DataFrame] = None

    #: Low- and high-intensity dairy yields (CAPRI DCOL / DCOH), the bounds of
    #: the livestock intensity margin.
    livestock_intensity_bounds: Optional[pd.Series] = None


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

        # GRAS is already on a dry-matter tonnage basis: the conversion from
        # CAPRI's fresh-matter kg/ha happens once at load time, in
        # loaders._reconcile_grass_yield_units.
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

        # CAPRI's own market revenue per head (MREV), where available, replaces
        # price x yield for livestock. For crops the two are identical (wheat in
        # DE11: 135.6 EUR/t x 6.15 t/ha = 833.7 = MREV), but for breeding and
        # suckler activities YILD is not a marketed product - suckler cows carry
        # a YILD of 422.6 against 21.8 of beef - so a revenue built from it
        # values the wrong quantity. That is why gross_margin was dominated by
        # pigs and barely moved under policy.
        rev_coef = getattr(self.data, "livestock_revenue_coef", None)

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
            revenue = price * yld
            if act in ANIMALS and rev_coef is not None and act in rev_coef.index \
                    and pd.notna(rev_coef[act]) and float(rev_coef[act]) > 0:
                revenue = float(rev_coef[act])
                if price_shock is not None:
                    revenue *= 1.0 + float(price_shock.get(act, 0.0))

            if premium is not None and act in premium.index and pd.notna(premium[act]):
                payment = float(premium[act])
            else:
                payment = cap.get("BPS", 0.0) if act in CROPS else 0.0

            # Crop gross margin (EUR/ha); animal gross margin (EUR/head)
            r[act] = revenue - cost + payment

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
    #: CAPRI's country -> PESETA macro-region mapping for organic yield gaps
    #: (gams/inputs/load_organic_yieldgap.gms).
    PESETA_REGION = {
        "BE": "CEN", "LU": "CEN", "DE": "CEN", "NL": "CEN", "PL": "CEN",
        "AT": "CES", "CZ": "CES", "FR": "CES", "HU": "CES", "RO": "CES",
        "SK": "CES",
        "DK": "NE", "EE": "NE", "FI": "NE", "LT": "NE", "LV": "NE",
        "SE": "NE", "NO": "NE",
        "BG": "SE", "CY": "SE", "ES": "SE", "EL": "SE", "HR": "SE",
        "IT": "SE", "MT": "SE", "PT": "SE", "SI": "SE",
        "IE": "UK_IR",
    }

    #: CAPRI's crop -> yield-gap product group (same source).
    YIELD_GAP_GROUP = {
        "SWHE": "wheat", "DWHE": "wheat",
        "RYEM": "cereals", "BARL": "cereals", "OATS": "cereals",
        "OCER": "cereals", "PARI": "cereals",
        "CORN": "maize", "MAIF": "maize",
        "RAPE": "oilseeds", "SUNF": "oilseeds", "SOYA": "oilseeds",
        "OOIL": "oilseeds",
        "GRAS": "grass", "OFOD": "grass",
        "TOMA": "vegetables", "POTA": "vegetables", "OVEG": "vegetables",
        "APPL": "fruits", "OFRU": "fruits", "CITR": "fruits",
        "TAGR": "nonfruit_perm", "WINE": "nonfruit_perm", "OLIV": "nonfruit_perm",
    }

    #: CAPRI raises other inputs by 100% on converted area (JRC121368). The
    #: old flat ORGANIC_COST_PREMIUM of 0.15 applied to TOTAL cost, which both
    #: understated horticulture (other inputs are 30-48% of its cost) and
    #: ignored the fertiliser and plant-protection savings that make organic
    #: arable cropping cheaper, not dearer.
    ORGANIC_OTHER_COST_RISE = 1.00

    #: EU organic area already in place, subtracted from the target to give the
    #: share that actually CONVERTS. CAPRI sets this explicitly:
    #: p_organicAreaTarget("EU27yr19") = 0.25 - 0.10 in
    #: gams/pol_input/greendeal/load_organic_targets.gms, i.e. a 15 percentage
    #: point shock, not 25. This model applied the full target as if every
    #: hectare converted, nearly double CAPRI's shock, which is why oilseeds
    #: (1.43x) and permanent crops (1.57x) overshot CAPRI's published results.
    #: CAPRI breaks the 15 points down by member state from Eurostat organic
    #: areas; that breakdown is not held here, so its EU figure is used
    #: uniformly and the simplification recorded.
    ORGANIC_BASELINE_SHARE = 0.10

    #: Organic share of utilised agricultural area by country, from Eurostat
    #: org_cropar as published in its 2019 release (2018 for Slovenia). CAPRI
    #: breaks its 15-point EU shock down by member state from the same source,
    #: in R code this project does not hold, so the published per-country
    #: figures are used where Eurostat names them and ORGANIC_BASELINE_SHARE
    #: applies elsewhere. Coverage is partial BY DESIGN and stated rather than
    #: filled in by guesswork: the countries below are those Eurostat lists
    #: explicitly, and they include the ones that matter most here - Italy and
    #: Austria are far along and hold much of the EU's permanent-crop area, so
    #: a uniform 10% baseline made them convert roughly twice as much land as
    #: they should.
    ORGANIC_BASELINE_BY_COUNTRY = {
        "AT": 0.253, "EE": 0.223, "SE": 0.204, "CZ": 0.152, "IT": 0.152,
        "LV": 0.148, "FI": 0.135, "SI": 0.100, "NL": 0.037, "PL": 0.035,
        "RO": 0.029, "BG": 0.023, "IE": 0.016, "MT": 0.005,
    }

    def _organic_baseline(self) -> float:
        """Organic share already in place in this region's country."""
        reg = str(getattr(self.data, "region_id", "") or "")
        return self.ORGANIC_BASELINE_BY_COUNTRY.get(
            reg[:2], self.ORGANIC_BASELINE_SHARE)

    #: Share of the measured organic yield gap NOT attributable to the loss of
    #: plant protection. CAPRI applies this factor ONLY in its endogenous
    #: pesticide variant (pest_disagg==on), where the plant-protection yield
    #: effect is solved. Kept here for that case; not applied by default.
    ORGANIC_GAP_PESTICIDE_SHARE = 0.45


    #: CAPRI's assumed average yield loss for a 50% pesticide reduction
    #: (JRC121368, from Sanchez et al. 2019: 18.6% of EU production potentially
    #: affected by 20 pests, worst case 50% loss on that share). CAPRI has NO
    #: dose-response function for plant protection -- unlike fertiliser -- so
    #: this is an explicit assumption in CAPRI too, not a derived quantity.
    PESTICIDE_YIELD_LOSS_AT_50PCT = 0.10

    #: The crop groups CAPRI applies the yield loss to.
    #: CAPRI raises "other costs" (mechanical weeding, alternative practices)
    #: by 50% alongside the expenditure cut - conventional_io.gms is called
    #: with the other-cost change set equal to the plant-protection reduction.
    #:
    #: This was previously ZERO, because "other costs" is CAPRI's own INPO
    #: category and this model had no equivalent, so the only available base
    #: was the plant-protection share - where a 50% rise cancels the 50%
    #: saving exactly, an artefact rather than a result. OTHER_COST_SHARE now
    #: carries INPO from all 27 member-state dumps, so the shock can be applied
    #: to the right base and the constant restored to CAPRI's value.
    PESTICIDE_OTHER_COST_RISE = 0.50

    PESTICIDE_AFFECTED = (
        # CORN is grain maize in this activity set; "MAIZ" (used here before)
        # is not an activity, so the pesticide target silently skipped it.
        "SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER",      # cereals
        "RAPE", "SUNF", "SOYA", "OOIL",                              # oilseeds
        "TOMA", "OVEG", "POTA", "SUGB", "PULS",                      # veg/other arable
        "APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV",              # permanent
    )

    #: Livestock activities whose gross-output unit is not established. Their
    #: gross_output is reported as NaN rather than as a number that looks
    #: plausible and is not. DCOW is excluded because it verifies against real
    #: EU milk output (142,000 kt against ~155,000); every other animal activity
    #: fails that check by a factor no single rescaling explains.
    UNVERIFIED_OUTPUT_UNITS = ("BULL", "LAYS", "BROI", "CALV", "SHGP",
                               "HFRS", "BCOW", "PIGS", "OANI")

    #: Share of total input cost that CAPRI books as "other inputs" (INPO),
    #: area-weighted over all 27 member-state capreg dumps. This is the category
    #: the Farm-to-Fork scenarios raise: +50 per cent under the pesticide target
    #: and +100 per cent under organic conversion (JRC121368).
    #:
    #: The spread is the point. Permanent and horticultural crops carry far more
    #: of their cost here than cereals do - table grapes 48, wine 41, fruit
    #: 30-34, tomatoes 30 per cent, against wheat 9 and durum 5 - so CAPRI's
    #: other-cost shock bites about four times harder on permanents. This model
    #: previously applied the rise to the PLANT-PROTECTION share instead, where
    #: it cancelled the expenditure saving almost exactly and left the cost
    #: channel a no-op. That is the main reason permanent crops under-responded.
    OTHER_COST_SHARE = {
        "APPL": 0.304,
        "BARL": 0.124,
        "CITR": 0.318,
        "CORN": 0.140,
        "COTT": 0.199,
        "DWHE": 0.053,
        "GRAS": 0.104,
        "MAIF": 0.144,
        "OATS": 0.098,
        "OCER": 0.063,
        "OFOD": 0.122,
        "OFRU": 0.343,
        "OLIV": 0.080,
        "OOIL": 0.113,
        "OVEG": 0.215,
        "PARI": 0.067,
        "POTA": 0.403,
        "PULS": 0.116,
        "RAPE": 0.154,
        "RYEM": 0.088,
        "SOYA": 0.108,
        "SUGB": 0.104,
        "SUNF": 0.129,
        "SWHE": 0.093,
        "TAGR": 0.478,
        "TOBA": 0.247,
        "TOMA": 0.297,
        "WINE": 0.407,
    }

    #: Share of total input cost that is fertiliser (CAPRI FERT), same basis.
    #: Organic conversion sets mineral fertiliser to zero, so this is a cost
    #: SAVING that partly offsets the other-cost rise - heavily for arable
    #: crops (wheat 42, maize 44 per cent) and barely at all for fruit (1).
    FERT_COST_SHARE = {
        "APPL": 0.024,
        "BARL": 0.367,
        "CITR": 0.067,
        "CORN": 0.443,
        "COTT": 0.265,
        "DWHE": 0.471,
        "GRAS": 0.591,
        "MAIF": 0.487,
        "OATS": 0.371,
        "OCER": 0.399,
        "OFOD": 0.521,
        "OFRU": 0.024,
        "OLIV": 0.131,
        "OOIL": 0.342,
        "OVEG": 0.051,
        "PARI": 0.621,
        "POTA": 0.075,
        "PULS": 0.356,
        "RAPE": 0.291,
        "RYEM": 0.313,
        "SETA": 1.000,
        "SOYA": 0.509,
        "SUGB": 0.488,
        "SUNF": 0.333,
        "SWHE": 0.416,
        "TAGR": 0.013,
        "TOBA": 0.188,
        "TOMA": 0.109,
        "WINE": 0.026,
    }

    #: Plant-protection cost as a share of total input cost, by crop.
    #: Derived from CAPRI data for ALL 27 member states: PESTOTAL (active
    #: ingredient, g/ha, from each res_17<CC> dump) times the national unit
    #: value UVAB.PLAP (EUR/kg, from coco), over TOIN, area-weighted.
    #:
    #: These replace shares derived from Spain and Italy alone, which were
    #: understated roughly threefold: wheat 5.7 per cent against 17.6 here,
    #: apples 7.3 against 17.6. The external check is decisive - applied to
    #: the base year, the old shares implied 3.57 bn EUR of EU
    #: plant-protection spending against a real market of 11-12 bn, while
    #: these imply 10.78 bn. CAPRI's own documentation had hinted at this:
    #: its Table 1 shows soft wheat plant protection at about 11.5 per cent
    #: of input cost, roughly twice the old figure.
    PPP_COST_SHARE = {
        "APPL": 0.176,
        "BARL": 0.134,
        "CITR": 0.112,
        "CORN": 0.053,
        "COTT": 0.085,
        "DWHE": 0.116,
        "GRAS": 0.031,
        "MAIF": 0.083,
        "OATS": 0.036,
        "OCER": 0.101,
        "OFOD": 0.035,
        "OFRU": 0.177,
        "OLIV": 0.249,
        "OOIL": 0.077,
        "OVEG": 0.088,
        "PARI": 0.011,
        "POTA": 0.051,
        "PULS": 0.281,
        "RAPE": 0.066,
        "RYEM": 0.112,
        "SOYA": 0.043,
        "SUGB": 0.168,
        "SUNF": 0.062,
        "SWHE": 0.176,
        "TAGR": 0.013,
        "TOBA": 0.029,
        "TOMA": 0.023,
        "WINE": 0.084,
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
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        for a in self.acts:
            if a not in self.PESTICIDE_AFFECTED:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            # The yield loss must reach BOTH the objective and the reported
            # yields. It used to change net revenue only, so it steered what
            # farmers grew but left gross_output computed on unshocked yields:
            # EU cereal PRODUCTION fell 6% where CAPRI reports 15%, even though
            # our cereal AREA fell 5.9% against CAPRI's 4%. The area response
            # was never the problem; the yield effect was missing from the
            # output. CAPRI reports production, so this is what is compared.
            new_ylds[a] = y * (1.0 - loss)
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss
            # CAPRI cuts plant-protection expenditure by the target share and
            # raises other costs by 50%. Both are represented here relative to
            # the crop's assumed PPP share of variable cost: the saving is a
            # margin GAIN, the other-cost rise a partial offset.
            c = float(self.data.variable_costs.get(a, 0.0))
            ppp = self.PPP_COST_SHARE.get(a)
            if ppp and c > 0:
                nr[a] = float(nr.get(a, 0.0)) + c * ppp * reduction
            # CAPRI raises its OTHER INPUTS category by 50% at the 50% target.
            # This used to be applied to the plant-protection share, where it
            # cancelled the saving almost exactly and made the cost channel a
            # no-op. Other inputs are 48% of cost for table grapes and 41% for
            # wine but only 9% for wheat, so the shock is what makes CAPRI's
            # permanent crops respond far more than its cereals.
            other = self.OTHER_COST_SHARE.get(a)
            if other and c > 0:
                nr[a] = float(nr.get(a, 0.0)) - (
                    c * other * self.PESTICIDE_OTHER_COST_RISE * (reduction / 0.50))
        self.data.yields = new_ylds
        self.net_revenues = nr


    #: Short-run yield response to a change in the crop's own price. CAPRI's
    #: supply model determines yields "exogenously by trend analysis ... and
    #: updated depending on price changes against the baseline" (documentation
    #: ch. 5, two-stage decision process: stage one sets input coefficients per
    #: hectare for given yields, stage two the activity mix). Without this the
    #: model has a pure extensive margin for price shocks -- area moves, yield
    #: does not -- which understates supply response and overstates the area
    #: change needed to deliver it.
    #:
    #: 0.15 is a short-run own-price yield elasticity from the agronomic and
    #: econometric literature (typically 0.1-0.3; intensification through
    #: fertiliser, protection and management responds within a season, variety
    #: and structure do not). It is an ASSUMPTION, exposed here rather than
    #: buried, and is NOT tuned to any comparison.
    YIELD_PRICE_ELASTICITY = 0.15

    def apply_yield_price_response(self, price_shock: pd.Series) -> None:
        """Let yields respond to own-price changes, as CAPRI's stage one does.

        yield_new = yield_base * (1 + price_change) ** YIELD_PRICE_ELASTICITY

        At an unchanged price the factor is exactly 1.0, so the base year is
        reproduced bit-for-bit and PMP calibration is untouched -- the same
        identity that protects the nitrogen intensity margin.

        Net revenue is rebuilt from the adjusted yields, so the price effect
        enters once through quantity and once through the yield, which is what
        a two-stage decision implies. Mutates net_revenues and data.yields for
        one solve; the caller's finally block restores both.
        """
        if price_shock is None:
            return
        eps = float(self.YIELD_PRICE_ELASTICITY)
        if eps <= 0:
            return

        prices = self.data.producer_prices
        ylds = self.data.yields
        if not hasattr(ylds, "copy"):
            return
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        for a in self.acts:
            if a not in CROPS:
                continue
            dp = float(price_shock.get(a, 0.0)) if hasattr(price_shock, "get") else 0.0
            if dp == 0.0:
                continue
            # a price fall below -100% is not meaningful; clamp the base
            factor = max(1.0 + dp, 0.01) ** eps
            y0 = float(ylds.get(a, 0.0))
            if y0 <= 0:
                continue
            new_ylds[a] = y0 * factor
            p = float(prices.get(a, 0.0)) * (1.0 + dp)
            # the extra revenue from the yield change alone
            nr[a] = float(nr.get(a, 0.0)) + p * y0 * (factor - 1.0)
        self.data.yields = new_ylds
        self.net_revenues = nr


    def _organic_yield_gap(self, activity: str) -> float:
        """Organic yield gap for one activity in this region, as a fraction.

        Falls back to ORGANIC_YIELD_GAP where CAPRI has no estimate for that
        region and product (its own code borrows the Central-European value in
        that case; the flat default is used here and recorded rather than
        silently substituting a different region's number).
        """
        table = getattr(self.data, "organic_yield_gap", None)
        group = self.YIELD_GAP_GROUP.get(activity)
        reg_id = getattr(self.data, "region_id", "") or getattr(self, "region", "")
        region = self.PESETA_REGION.get(str(reg_id)[:2])
        if table is not None and group and region is not None:
            try:
                v = table.at[region, group]
            except Exception:
                v = None
            if v is not None and v == v:
                return abs(float(v)) / 100.0
        return self.ORGANIC_YIELD_GAP

    def apply_organic_area_target(self, share: float,
                                  pesticide_active: bool = False) -> None:
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

        prices = self.data.producer_prices
        ylds = self.data.yields
        new_ylds = ylds.copy()
        costs = self.data.variable_costs
        nr = self.net_revenues.copy()
        converted = max(0.0, float(share) - self._organic_baseline())
        for a in self.acts:
            if a not in CROPS:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            c = float(costs.get(a, 0.0))
            if p <= 0 or y <= 0:
                continue
            # CAPRI's organic conversion is three cost changes, not one flat
            # premium: other inputs DOUBLE, mineral fertiliser goes to zero and
            # plant protection goes to zero (JRC121368). The balance differs
            # sharply by crop - wheat saves 42% of cost on fertiliser and pays
            # only 9% more on other inputs, so it gets CHEAPER, while apples
            # save 1% and pay 30% more. A flat premium hid that entirely.
            # CAPRI's organic yield gaps are FADN-based estimates by macro-region
            # and product group (JRC Seville for the SUPREMA project, loaded in
            # gams/pol_input/greendeal/organic_area.gms). They differ sharply
            # from the flat 20% used before and from each other: in Southern
            # Europe fruits lose 22.5% and olives and vines 11.6%, while in
            # Central Europe fruits lose 51.3% and cereals 42.9%.
            gap = self._organic_yield_gap(a)
            if pesticide_active:
                # CAPRI scales the organic yield gap by 0.45 when the pesticide
                # effect is modelled separately, because 55% of the measured
                # organic gap is attributed to the loss of plant protection and
                # would otherwise be counted twice (organic_area.gms, and the
                # same 0.45 in capreg/inputs/pest_cor.gms). Applying the full
                # gap alongside our own pesticide yield loss overstated cereals
                # and oilseeds (1.22 and 1.25 of CAPRI).
                gap *= self.ORGANIC_GAP_PESTICIDE_SHARE
                # CAPRI converts the DISTANCE from the existing organic area to the
            # target, not the whole target.
            yield_factor = 1.0 - gap * converted
            other = self.OTHER_COST_SHARE.get(a, 0.0)
            fert = self.FERT_COST_SHARE.get(a, 0.0)
            ppp = self.PPP_COST_SHARE.get(a, 0.0)
            cost_change = c * converted * (
                other * self.ORGANIC_OTHER_COST_RISE - fert - ppp)
            # As with the pesticide instrument, the yield gap must reach the
            # REPORTED yields too, not only the objective. CAPRI reports
            # PRODUCTION, and a yield gap that never lands in yields is
            # invisible there: EU cereal production fell 6% here against
            # CAPRI's 15%, while cereal AREA fell 5.9% against CAPRI's 4%.
            new_ylds[a] = y * yield_factor
            delta = (p * y * (yield_factor - 1.0)) - cost_change
            nr[a] = float(nr.get(a, 0.0)) + delta
        self.data.yields = new_ylds
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
        from capri_mod.supply.intensity import (optimal_intensity,
                                                 dairy_intensity_response)

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

        # (c) LIVESTOCK INTENSITY MARGIN. A nitrogen ceiling should let dairy
        # extensify, not only shrink: CAPRI carries every dairy herd as a low-
        # and a high-intensity variant (DCOL/DCOH) precisely so the herd can
        # move between them under a nutrient target. Without this the only
        # livestock margin is the number of animals.
        #
        # The pressure is the same intensity cut the crops face, so a slack
        # ceiling leaves dairy untouched and the base year is reproduced
        # exactly. Yield, milk revenue and manure nitrogen move together.
        bounds = getattr(self.data, "livestock_intensity_bounds", None)
        if bounds is not None and "DCOW" in self.acts:
            # remember the base-intensity yield so gross_output can scale the
            # per-head coefficient by however far the herd has extensified
            if getattr(self, "_dairy_yield_base", None) is None:
                self._dairy_yield_base = float(self.data.yields.get("DCOW", 0.0))
            try:
                low = float(bounds.get("DCOW_low", 0.0))
                high = float(bounds.get("DCOW_high", 0.0))
            except (TypeError, ValueError):
                low = high = 0.0
            pressure = float(np.clip(1.0 - np.mean(res.intensity.values), 0.0, 1.0))
            y0 = float(self.data.yields.get("DCOW", 0.0))
            y1 = dairy_intensity_response(y0, low, high, pressure)
            if y1 > 0 and y0 > 0 and y1 != y0:
                factor = y1 / y0
                new_y = self.data.yields.copy()
                new_y["DCOW"] = y1
                self.data.yields = new_y
                nr = self.net_revenues.copy()
                if "DCOW" in nr.index:
                    nr["DCOW"] = float(nr["DCOW"]) * factor
                self.net_revenues = nr
                try:
                    res.livestock_intensity = factor
                except Exception:
                    pass          # result object may be frozen; the effect is applied regardless
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
        # The ARABLE land figure and the crop areas come from different
        # aggregations and disagree in 54 of 248 regions, by 9,960 kha in total,
        # with ratios up to 12.7x (LT02, PL81, PL84, PL91, BG31, BG33). Taking
        # the land figure literally makes the BASE YEAR infeasible, so the solver
        # must cut: those regions lost most or all of their cereals in a plain
        # base solve, and the 9,976 kha the solve shed matched the 9,960 kha of
        # excess almost exactly. EU wheat came out 19,857 kha against a base of
        # 22,095 and a real EU figure of ~22,000.
        #
        # Same treatment as the PERMANENT bound below: the bound is the larger of
        # the land figure and what the region actually grows, so the constraint
        # stays slack where the two sources agree and stops rewriting the base
        # year where they do not.
        arable_base = sum(float(self._base_levels().get(a, 0.0))
                          for a in arable_crops if a in acts_idx)
        arable_avail = max(self.data.land.get("ARABLE", 200.0), arable_base)
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
        # SNAPSHOT EVERYTHING MUTABLE, rather than enumerating fields.
        #
        # A solve may rewrite several pieces of self.data for its own duration:
        # cap_payments and cap_premium (policy adders), nutrient_coefs (the
        # nitrogen intensity margin), yields (the yield-price response). The
        # previous version listed those fields one by one, and that list fell
        # behind TWICE -- nutrient_coefs leaked until the intensity margin was
        # traced, and yields leaked again when the yield-price response was
        # added. Each leak is silent: the altered value simply persists into
        # every later solve on the same model.
        #
        # Enumerating what to restore puts the burden on whoever adds the next
        # mutation to remember this block. Snapshotting every restorable
        # attribute removes that burden: a new mutation is covered the moment it
        # is written. The cost is copying a handful of small pandas objects per
        # solve, which is negligible beside the QP itself.
        _RESTORABLE = ("cap_payments", "cap_premium", "nutrient_coefs",
                       "yields", "producer_prices", "variable_costs", "land")
        _backup = {}
        for _f in _RESTORABLE:
            _v = getattr(self.data, _f, None)
            if _v is not None and hasattr(_v, "copy"):
                _backup[_f] = _v.copy()

        try:
            return self._solve_inner(price_shock, policy_shock, nitrate_limit,
                                     set_aside_requirement)
        finally:
            self.net_revenues = _net_rev_backup
            for _f, _v in _backup.items():
                setattr(self.data, _f, _v)

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
            # CAPRI's stage-one yield response: yields move with own price
            # against the baseline, not just area. Applied after the net-revenue
            # rebuild so it is not overwritten by it.
            if price_shock is not None:
                self.apply_yield_price_response(price_shock)

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
            _pest = float(policy_shock.get("pesticide_reduction", 0.0) or 0.0)
            if _org:
                # CAPRI scales the organic yield gap by 0.45 when the pesticide
                # yield effect is modelled separately, because 55% of the
                # measured organic gap is attributed to the loss of plant
                # protection and would otherwise be counted twice
                # (organic_area.gms; the same 0.45 in capreg/inputs/pest_cor.gms).
                # This model DOES apply its own pesticide yield loss, so the
                # factor belongs here. An earlier version rejected it after
                # testing on AREA - the wrong metric, since CAPRI reports
                # PRODUCTION. On production the double count is plain: without
                # the factor, EU cereals fall 18.6% against CAPRI's 15%,
                # oilseeds 27.7% against 15% and permanent crops 22.7%
                # against 12%.
                self.apply_organic_area_target(_org, pesticide_active=bool(_pest))
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
            x_qp_feasible = x_opt.copy()
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

            # The rail is applied AFTER the solve, so it can push the solution
            # off constraints the QP had satisfied. It did: under any price
            # shock, a 10% set-aside requirement was silently cut back to 1.5x
            # the base level (FR10: floor 56.2 kha, QP solution 56.2, reported
            # 24.7 = 16.5 x 1.5). Because price shocks only arise from the
            # second outer iteration onward, every CONVERGED policy run had its
            # land constraints quietly relaxed, while single-iteration runs
            # looked correct - which is why the EU set-aside came to 9.9 Mha
            # against a 15.6 Mha requirement.
            #
            # The rail's purpose is to bound pathological blowups, not to
            # overrule policy. If clamping breaks feasibility, the constraint
            # wins and the QP solution stands.
            if A_ub is not None and len(b_ub):
                if np.max(A_ub @ x_opt - b_ub) > 1e-6:
                    x_opt = x_qp_feasible.copy()

        activities = pd.Series(x_opt, index=self.acts)

        # Compute gross outputs.
        #
        # GRAS yield is FRESH MATTER in kg/ha (~36,000), not t/ha like every
        # other crop, so a raw activities x yields product put grass output a
        # thousandfold too high -- 4,540,503 kt of grass for a single region,
        # which silently dominates any sum across activities. This is the same
        # fresh-matter artifact already fixed in the nitrogen balance, the
        # fertiliser module and the income module; this is the fourth place it
        # surfaced. Converted here to a dry-matter tonnage basis so gross_output
        # is in 1000 t throughout, as its type annotation states.
        # GRAS is already dry-matter tonnes (converted at load time).
        yields = self.data.yields.reindex(self.acts).fillna(0.0)
        gross_output = activities * yields

        # Livestock output comes from CAPRI's FINAL-PRODUCT coefficients, not
        # YILD. For breeding and suckler activities CAPRI's YILD measures
        # offspring or liveweight rather than a marketed product (suckler cows
        # 422.6 of YILD against 21.8 of beef; sows 19,917 against 50.6 of pork),
        # so level x YILD was not a tonnage of anything saleable. The
        # coefficients (tools/build_livestock_output_coef.py) sum CAPRI's
        # COMI/BEEF/PORK/POUM/EGGS/SGMT/SGMI items and reproduce real 2017 EU
        # production to within 0.94-1.08 by product.
        #
        # An animal activity with no coefficient for this region is reported
        # as NaN, not as level x YILD: refusing to report an unestablished
        # quantity is safer than reporting it wrongly.
        _coef = getattr(self.data, "livestock_output_coef", None)
        for _a in ANIMALS:
            if _a not in gross_output.index:
                continue
            _c = (float(_coef.get(_a)) if _coef is not None
                  and _a in _coef.index and pd.notna(_coef.get(_a)) else None)
            # The output coefficient is per head at BASE intensity. Where the
            # livestock intensity margin has moved the yield — dairy extensifying
            # under a nutrient ceiling — the reported product must move with it,
            # or the extensification would steer the solve while leaving output
            # unchanged, which is the failure the crop yield shocks had.
            if _c is not None and _a == "DCOW":
                _y0 = getattr(self, "_dairy_yield_base", None)
                _y1 = float(self.data.yields.get("DCOW", 0.0))
                if _y0 and _y1 > 0 and _y0 > 0:
                    _c *= _y1 / _y0
            gross_output[_a] = (float(activities.get(_a, 0.0)) * _c
                                if _c is not None else float("nan"))

        # Gross margin
        # Reported gross margin is net revenue x activity levels. The PMP
        # quadratic and linear terms are a CALIBRATION DEVICE - they exist to
        # make the base year optimal - not economic costs, and including them
        # made this field meaningless: for DE11 it returned 55,531,046 where
        # the margin is 428,136 thousand EUR, because the quadratic term alone
        # is over a hundred times the linear one. That is why farm income used
        # to read as barely moving under policies that visibly changed land use.
        gm = float(self.net_revenues.reindex(self.acts).fillna(0.0).values @ x_opt)

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
            livestock_output_coef=(
                d["livestock_output_coef"].loc[region]
                if d.get("livestock_output_coef") is not None
                and region in d["livestock_output_coef"].index else None),
            organic_yield_gap=d.get("organic_yield_gap"),
            livestock_intensity_bounds=(
                d["livestock_intensity_bounds"].loc[region]
                if d.get("livestock_intensity_bounds") is not None
                and region in d["livestock_intensity_bounds"].index else None),
            livestock_revenue_coef=(
                d["livestock_revenue_coef"].loc[region]
                if d.get("livestock_revenue_coef") is not None
                and region in d["livestock_revenue_coef"].index else None),
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

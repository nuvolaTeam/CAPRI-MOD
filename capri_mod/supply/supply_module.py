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
import multiprocessing
import os
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
from capri_mod.params import param, param_table
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

#: CAPRI's fixed production activities (sets.gms FACT: MFCACT = OOIL, OIND; OANI), held at their data level
FIXED_ACTIVITIES = ("OOIL", "OIND", "OANI")

#: CAPRI p_OverFertMarkUp (envind/ghgMiti.gms): corrects the over-fertilisation factor
#: for the additive need factor and manure availability
OVERFERT_MARKUP = param("OVERFERT_MARKUP")
_OVERFERT = None
_OVERFERT_WARNED = False


def overfert_factor(region: str):
    """CAPRI's over-fertilisation factor x = v_cropNutNeedMultFact(ru, NITF, "T") for a model
    region (capri_data/2017/environment/crop_nut_need_mult_fact_2030.csv, built by
    tools/build_overfert_factors.py from CAPRI's priFertDist results), or None when the data
    is not available - then CAPRI's limits on the fertiliser technologies (Tot_MitFert_ and the
    regional maximum shares) cannot be applied, which is warned once."""
    global _OVERFERT, _OVERFERT_WARNED
    if _OVERFERT is None:
        _OVERFERT = {}
        f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "crop_nut_need_mult_fact_2030.csv"
        if f.exists():
            for r in pd.read_csv(f).itertuples(index=False):
                _OVERFERT[str(r.region)] = float(r.x)
    x = _OVERFERT.get(region)
    if x is None and not _OVERFERT_WARNED:
        warnings.warn("CAPRI over-fertilisation factors (crop_nut_need_mult_fact_2030.csv) missing: "
                      "fertiliser technologies are not limited by over-fertilisation (CAPRI Tot_MitFert_)")
        _OVERFERT_WARNED = True
    return x


_ACTIVE_TECH = None
_YANI = None


#: CAPRI p_fertEffCor (envind/ghgMiti.gms)
P_FERT_EFF_COR = param("P_FERT_EFF_COR")
_FERT_OPT = None


def fert_option_table() -> dict:
    """{model region: [row]} of CAPRI's fertiliser options (fert_options_jul15.csv)."""
    global _FERT_OPT
    if _FERT_OPT is None:
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "fert_options_jul15.csv"
        _FERT_OPT = {}
        if f.exists():
            for r in pd.read_csv(f).itertuples(index=False):
                _FERT_OPT.setdefault(r.region, []).append(r)
        else:
            import warnings as _w
            _w.warn("fert_options_jul15.csv missing: no fertiliser-efficiency options")
    return _FERT_OPT


def young_animal_table() -> dict:
    """CAPRI's young-animal coefficients per model region (calves, young cattle, cows)."""
    global _YANI
    if _YANI is None:
        import json as _json
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "supply" / "young_animals_2017.json"
        _YANI = _json.load(open(f))["regions"] if f.exists() else {}
    return _YANI


def active_technologies():
    """CAPRI's active mitigation technologies of the Green Deal reference (activeTech,
    capri_data/2017/abatement/active_technologies.csv, tools/build_active_technologies.py), or
    None when the file is missing (then every option with data is available, with a warning)."""
    global _ACTIVE_TECH
    if _ACTIVE_TECH is None:
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "active_technologies.csv"
        if f.exists():
            _ACTIVE_TECH = set(pd.read_csv(f)["technology"].str.upper())
        else:
            import warnings as _w
            _w.warn("active_technologies.csv missing: all mitigation options with data are available")
            _ACTIVE_TECH = set()
    return _ACTIVE_TECH or None


def fert_efficiency_cap(region: str):
    """Largest total efficiency gain E = sum share x NMIN CAPRI allows (Tot_MitFert_):
    1 + E <= max(x + 0.1, 1). None when x is unknown."""
    x = overfert_factor(region)
    return None if x is None else max(x + OVERFERT_MARKUP, 1.0) - 1.0


def _csv_dict(rel: str, col: str) -> Dict[str, float]:
    """{key: value} of one column of a capri_data CSV (first column the key), NaN rows left out - CAPRI's tables the
    supply model reads at import (project rule: inputs in CSV)."""
    f = Path(__file__).resolve().parents[2] / "capri_data" / rel
    s = pd.read_csv(f, index_col=0)[col].dropna()
    return {str(k): float(v) for k, v in s.items()}


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
    #: value of final products per head (no young animals), CAPRI quantities x UVAG; used where
    #: CAPRI's MREV counts young-animal sales (sows: MREV = piglets)
    livestock_product_value_coef: Optional[pd.Series] = None
    livestock_product_value_by_market_coef: Optional[pd.Series] = None
    #: young-animal value factors {good: factor} (CAPRI's 2030 prices in the projected baseline)
    young_value_factor: Optional[dict] = None
    #: CAPRI's grassland split (share_ext, yield_ext_rel, yield_int_rel, q_ext, q_int), Sprint 7a
    grass_intensity: Optional[pd.Series] = None
    #: CAPRI's dairy split DCOL/DCOH (share_low, d<item>_rel, q_low, q_high), Sprint 7b
    dairy_intensity: Optional[pd.Series] = None
    #: CAPRI's bull and heifer splits {animal: Series} (BULL/BULH, HEIL/HEIH), Sprint 7c
    cattle_intensity: Optional[dict] = None
    genetics_effects: Optional[dict] = None
    #: CAPRI's histosols: organic-soil shares, emission factors, fallowing cost terms
    histosol: Optional[pd.Series] = None
    #: CAPRI's plant-protection (plap), other-input (inpo) and fertiliser (fert) cost, EUR/ha by crop
    input_costs_ha: Optional[pd.DataFrame] = None
    #: CAPRI's catch crops (catc_share_2030, catc_cost_eur_ha, biofix_t_n_ha) and winter cover shares by crop
    cover_crops: Optional[pd.Series] = None
    winter_cover_share: Optional[pd.DataFrame] = None
    livestock_cost_coef: Optional[pd.Series] = None
    livestock_output_value_coef: Optional[pd.Series] = None
    livestock_premium_coef: Optional[pd.Series] = None     # CAPRI PRME per model head
    livestock_feed_coef: Optional[pd.Series] = None
    fodder_balance: Optional[dict] = None
    land_market: Optional[dict] = None

    #: CAPRI's organic yield gaps by macro-region and product group.
    organic_yield_gap: Optional[pd.DataFrame] = None

    #: Low- and high-intensity dairy yields (CAPRI DCOL / DCOH), the bounds of
    #: the livestock intensity margin.
    livestock_intensity_bounds: Optional[pd.Series] = None

    #: CAPRI's Green Deal targets for this region's member state: extra
    #: landscape land (points of UAA) and organic conversion (points of arable,
    #: grassland and permanent-crop area).
    landscape_target_pp: Optional[float] = None
    #: CAPRI's land rent for this region's country, EUR/ha
    land_rent: Optional[float] = None
    organic_targets_pp: Optional[pd.Series] = None


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
            # The LOWER bound reaches further. The clamp was added for the upper
            # tail (near-zero bases with explosive curvature stopped the
            # solver). Large activities with small per-unit revenue - poultry:
            # tens of millions of places at ~12 EUR each - calibrate legitimately
            # low; at 1e-4 x median both broilers and hens were lifted to the
            # same floor, ~150x their calibrated curvature, and stopped
            # responding to prices and feed costs.
            lo = med * 1e-7
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


    #: livestock costs from CAPRI's regional total inputs / model heads
    #: (livestock_cost_coef.csv). OFF until revenue is switched to CAPRI's total
    #: output (TOOU) at the same time: with market revenue (MREV), which leaves
    #: out the calves breeders produce, suckler cows would show -1,134% margins.
    use_livestock_cost_coef = True

    #: FEEDING INSIDE THE SUPPLY MODEL, as CAPRI (docs/FEED_IN_SUPPLY.md): each region's
    #: problem solved as one conic program with total-feed variables (Clarabel).
    #: OFF until validated in scenarios.
    use_feed_in_supply = True
    #: CAPRI's land balances without slack for ARAC, FRUN and GRAS (LandBalNoSlak_)
    land_no_slack = False

    def _techs_inside(self) -> bool:
        """CAPRI's ammonia technologies are decision variables of the regional conic model
        (feeding inside on, technologies on, rations available)."""
        return bool(getattr(type(self), "use_feed_in_supply", False) and getattr(self, "use_manure_techs", False)
                    and (getattr(self, "feed_rations", None) or {}))

    def _market_revenue_change(self, act, mrev, price_shock) -> float:
        """Revenue change of one head from market price changes: quantity x price change, product
        by product, from the value of the animal's final products (CAPRI quantities x UVAG; a dairy
        cow's milk moves with the milk price and her cull-cow beef with the beef price). Young
        animals are not in it: they move with their own prices (young-animal markets). CAPRI's MREV
        cannot serve here, because its content differs by activity: for activities that only raise
        young animals it is their sales (sows, raised calves, replacement heifers), for suckler cows
        a quarter of their beef. Falls back to MREV x the activity's own price change."""
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        own = SupplyModule.ACTIVITY_PRICE_SOURCE.get(act)
        if pv is not None:
            parts = {k.split(".", 1)[1]: float(v) for k, v in pv.items()
                     if k.startswith(act + ".") and pd.notna(v) and float(v) != 0.0}
            if parts:
                return sum(v * float(price_shock.get(m, price_shock.get(act, 0.0) if m == own else 0.0))
                           for m, v in parts.items())
        return mrev * float(price_shock.get(act, 0.0))

    #: young-animal price ratios {good: price / base price}, set by the supply module per run
    yani_price_ratio = None

    def _young_animal_coefs(self) -> dict:
        """{good: {"produce": {act: per head}, "use": {act: per head}, "value_eur_head": v}} for this
        region (capri_data/2017/supply/young_animals_2017.json, tools/build_young_animals.py)."""
        rec = young_animal_table().get(self.data.region_id, {})
        fac = getattr(self.data, "young_value_factor", None) or {}
        if not fac:
            return rec
        return {g: {**r, "value_eur_head": float(r.get("value_eur_head", 0.0) or 0.0) * float(fac.get(g, 1.0))}
                for g, r in rec.items()}

    def _apply_young_animal_prices(self):
        ratio = getattr(self, "yani_price_ratio", None) or {}
        if not ratio:
            return
        for g, rec in self._young_animal_coefs().items():
            r_ = float(ratio.get(g, 1.0))
            if r_ == 1.0:
                continue
            v = float(rec.get("value_eur_head", 0.0) or 0.0)
            for a in set(rec.get("produce", {})) | set(rec.get("use", {})):
                if a in self.net_revenues.index:
                    n = float(rec.get("produce", {}).get(a, 0.0)) - float(rec.get("use", {}).get(a, 0.0))
                    self.net_revenues[a] = float(self.net_revenues[a]) + (r_ - 1.0) * v * n

    def _mctx(self):
        """CAPRI's crop nutrient balance terms for this solve: {"man_d": manure N per activity unit, "nmin": crops'
        base mineral N per ha, "ybase": base yields}, from the N target's row when the scenario has one, else from
        the context SupplyModule sets for every EU solve (CAPRI's NUTNED_ and manure market are in every run,
        Sprint 9k); None when neither is there."""
        srow = getattr(self, "_surplus_row", None)
        if srow is not None and len(srow) > 6:
            mrow = srow[6]
            man_d = mrow[0] if mrow is not None and hasattr(mrow[0], "get") else None
            if man_d is not None:
                return {"man_d": man_d, "nmin": srow[2], "ybase": srow[4]}
        ctx = getattr(self, "_manure_ctx", None)
        return ctx if ctx and ctx.get("man_d") is not None else None

    @staticmethod
    def _ef_mineral_n2o() -> float:
        """t CO2-eq per t of mineral N in the accounts' soil N2O (direct + volatilised share x indirect)."""
        from capri_mod.environmental.environmental_module import (EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT,
                                                                  GWP_N2O)
        return (EF_SOIL_N2O_DIRECT + 0.10 * EF_SOIL_N2O_INDIRECT) * 44.0 / 28.0 * GWP_N2O

    @staticmethod
    def _ef_nh3_n2o() -> float:
        """t CO2-eq per t of NH3-N volatilised from manure (the accounts' N2O_IND, CAPRI N2OAMM)."""
        from capri_mod.environmental.environmental_module import EF_SOIL_N2O_INDIRECT, GWP_N2O
        return EF_SOIL_N2O_INDIRECT * 44.0 / 28.0 * GWP_N2O

    def _crop_mineral_now(self) -> dict:
        """Crops' mineral N per ha at this solve (kg N/ha): base rate x fertiliser intensity x sqrt(current / base
        yield), the same terms the N row uses (`_mineral_row`), for the fertiliser options without an N row."""
        ctx = self._mctx() or {}
        ybase = ctx.get("ybase")
        mint = getattr(self, "_n_intensity", {}) or {}
        ycur = self.data.yields
        out = {}
        for a, v in (ctx.get("nmin") or {}).items():
            if a not in CROPS or a not in self.acts or not float(v or 0.0) > 0:
                continue
            _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
            _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
            _r = (_yc / _y0) ** 0.5 if (_y0 > 0 and _yc > 0) else 1.0
            r_ = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
            if r_ > 0:
                out[a] = r_
        return out

    def _fert_tax_terms(self, ft) -> dict:
        """CAPRI's emission tax on mineral N and the fertiliser options (Sprint 9l), in the conic's 1000 EUR:
        "m" per t of mineral N (the accounts' soil N2O, direct + volatilised x indirect); "h" per unit of adopted area
        (1000 ha) per kg N/ha of need, by option. The accounts (EnvironmentalModule.fert_side_factors) count an option
        with CAPRI's literature side effects (p_litRevFertTechs: nitrification inhibitors) at (1 - lit) x (1 + NMIN)
        of the plain factor per kg of N under it, i.e. its N saving does not lower its N2O and the literature effect
        does: "h" gives back the saving's first-order tax (ef x NMIN) and charges - (ef_dir x lit_N2O + ef_vol x
        lit_NH3). Options without side-effect data lower N2O with the mineral N they save, through "m". REGISTERED:
        linearised at no adoption."""
        from capri_mod.environmental.environmental_module import (EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT,
                                                                  GWP_N2O)
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        k = 44.0 / 28.0 * GWP_N2O
        ef_d, ef_v = EF_SOIL_N2O_DIRECT * k, 0.10 * EF_SOIL_N2O_INDIRECT * k
        h = []
        for (nm_, nmin_, a_, b_, smx_) in ft:
            l2 = fert_side_value(self.data.region_id, str(nm_).upper(), "N2OSYN")
            l3 = fert_side_value(self.data.region_id, str(nm_).upper(), "NH3SYN")
            if l2 is None or l3 is None:
                h.append(0.0)
            else:
                h.append(tax * ((ef_d + ef_v) * float(nmin_) - (ef_d * float(l2) + ef_v * float(l3))) / 1000.0)
        return {"m": tax * (ef_d + ef_v) / 1000.0, "h": h}

    def _amm_context(self):
        """(technology blocks per animal, manure N per unit, CAPRI NH3 share, substitution) or None."""
        techs = self._manure_techs()
        _mc = self._mctx()
        man_d = _mc["man_d"] if _mc else None
        env_ = getattr(self, "_env_for_surplus", None)
        if not techs or man_d is None or env_ is None:
            return None
        try:
            _sb = env_._substitution(self.data.region_id)
            sub = float(_sb[0]) if _sb else 0.0
            nh3 = (env_._nh3_factors().get(self.data.region_id) or {}).get("manure_share", {})
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"manure technologies skipped for {self.data.region_id}: {_exc!r}")
            return None
        return techs, man_d, nh3, sub

    @staticmethod
    def _amm_scale(subs, mN, f):
        """N (t per activity unit of the sub-activity) per unit of the loss fraction: CAPRI's
        NH3 share of excreted N (its 2030 run, which embodies the base shares) over the loss
        the cascade gives at the base shares, so the accounts match at base."""
        from capri_mod.supply import ammonia_techs as _at
        L0 = sum(s["w"] * s["mrel"] * _at.loss(s, _at.initial(s)) for s in subs)
        return (mN * f / L0) if L0 > 0 else 0.0

    def _tech_list(self):
        """Ammonia technologies for the conic model (CAPRI v_Miti): one entry per sub-activity
        and option. The loss cascade couples the two groups (N reaching the field); the N saved
        per unit of share is linearised at the shares of the previous solve (successive
        linearisation across outer iterations; at convergence CAPRI's relation holds)."""
        from capri_mod.supply import ammonia_techs as _at
        ctx = self._amm_context()
        if ctx is None:
            return []
        techs, man_d, nh3, sub = ctx
        last = getattr(self, "_amm_last", None) or {}
        # CAPRI's emission tax on the options (ghgTax; its v_CO2EquEmis follows v_Miti): per unit of M (share x
        # sub-activity unit), the manure N2O change through the loss cascade (the accounts' finite difference,
        # ghg_tax.ghg_coefficients "mtech", per head) less the indirect N2O of the NH3 kept and the soil N2O of the
        # mineral N it displaces (sub x N kept); kt CO2-eq per unit -> x tax = 1000 EUR, the objective's unit
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        mtc = ((getattr(self, "ghg_coef", None) or {}).get("mtech") or {}) if tax > 0 else {}
        ef_n, ef_m = (self._ef_nh3_n2o(), self._ef_mineral_n2o()) if tax > 0 else (0.0, 0.0)
        out = []
        for a, subs in techs.items():
            mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
            if a not in self.acts or mN <= 0 or f <= 0:
                continue
            sc = self._amm_scale(subs, mN, f)
            for s in subs:
                sh = last.get((a, s["key"])) or _at.initial(s)
                d = _at.marginal(s, sh)
                npl = sc * s["mrel"]
                # N saved per unit of the sub-activity at the linearisation point, relative to the base shares (exact
                # cascade): with it the conic model's relief is the TANGENT of CAPRI's cascade at that point,
                # rel0 + ret x (share - share there), so at a converged point the N saved is CAPRI's exactly (before,
                # ret x (share - base share) left out the cross term of the two option groups: the NLP check,
                # tools/nlp_check, found CAPRI's N balance violated by 8-365 t N in the five regions checked)
                rel0 = npl * (_at.loss(s, _at.initial(s)) - _at.loss(s, sh))
                first = True
                for t in s["techs"]:
                    if t["slope"] is None or t["max"] <= 0:
                        continue
                    ret = max(0.0, -npl * d[t["tech"]])
                    # manure N2O through the cascade (the accounts' slope at the base shares, like every emission
                    # coefficient of the tax); the N kept is priced on its own (gn per t N kept) with the cascade's
                    # tangent, as the N row (K8: it was ret x (share - base share), K1's error)
                    g = tax * float(mtc.get((a, t["tech"]), 0.0) or 0.0) if tax > 0 else 0.0
                    gn = tax * (ef_n + sub * ef_m) / 1000.0 if tax > 0 else 0.0
                    out.append(dict(act=a, tech=t["tech"], key=s["key"], grp=(a, s["key"], t["group"]),
                                    w=s["w"], s0=t["ini"], smax=t["max"], slope=t["slope"], th=t["th"],
                                    ret=ret, sub=sub, stock=s["stock"], ghg=g, ghg_n=gn,
                                    s_lin=float(sh.get(t["tech"], t["ini"])), rel0=(rel0 if first else 0.0)))
                    first = False
        return out

    def _feed_conic_solve(self, Q, c, A, b, x_start):
        """Solve the regional problem with feeding inside (feed_conic), or None."""
        rats = getattr(self, "feed_rations", None) or {}
        self._last_feed_dm = None                  # never carry a previous solve's feed
        self._last_feed_t = None
        self._conic_ok = False
        if not getattr(type(self), "use_feed_in_supply", False) or not rats:
            return None
        from capri_mod.supply.feed_conic import solve_regional_conic
        lab = list(getattr(self, "_row_labels", []) or [])
        fod = {l.replace("fodder_", ""): k for k, l in enumerate(lab)
               if l.startswith("fodder_") and not l.endswith("_band") and k < A.shape[0]}
        fv = {f: float(v.get("value_eur_t", 0.0)) for f, v in (getattr(self.data, "fodder_balance", None) or {}).items()}
        # scaling: activities by their BASE levels (fixed, so each region's feed block is
        # built once and cached), auxiliaries by the current starting point
        xb = np.maximum(np.asarray(x_start, float), 0.0).copy()
        _n = len(self.acts)
        xb[:_n] = np.maximum(self._base_levels().reindex(list(self.acts)).fillna(0.0).values, 0.0)
        # CAPRI's ammonia technologies inside (v_Miti), when the region has an N row. Three
        # cases emulate CONOPT, which stays at the calibrated shares unless moving pays:
        # no N row -> technologies left out (shares at s0); N row binding -> included;
        # N row slack (dual ~0) -> re-solved without them (shares at s0).
        n_row = lab.index("N_balance") if "N_balance" in lab and lab.index("N_balance") < A.shape[0] else None
        # CAPRI's mineral fertiliser cap (mineRedu): fertiliser technologies save mineral N on that row too
        m_row = lab.index("mineral_N") if "mineral_N" in lab and lab.index("mineral_N") < A.shape[0] else None
        # (with only the mineral cap, its row carries them: manure N kept from ammonia losses displaces mineral N)
        # CAPRI's emission tax prices the options' emissions (ghgTax): with it, they are in every EU solve; without a
        # nitrogen row or the tax, CAPRI's calibration (thresh) keeps them at their base shares, so they are left out
        _taxed = float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0 and self._mctx() is not None
        techs = self._tech_list() if ((n_row is not None or m_row is not None or _taxed) and self._techs_inside()) else []
        fert = None
        if (n_row is not None or m_row is not None or _taxed) and self._techs_inside():
            _sr = getattr(self, "_surplus_row", None)
            _tl = _sr[5] if (_sr is not None and len(_sr) > 5) else \
                ((getattr(self, "_mineral_cap", None) or {}).get("techs") or [])  # same list as the external rule
            if not _tl and _taxed:
                _tl = (self._mctx() or {}).get("techs") or []
            _ft = [(nm_, nmin_, a_, b_, smx_) for (nm_, nmin_, a_, b_, s0_, smx_) in _tl]
            _mr = (getattr(self, "_mineral_row", {}) or {}) if n_row is not None else {}
            if not _mr:
                _mr = getattr(self, "_mineral_row_m", {}) or {}
            if not _mr and _taxed:
                _mr = self._crop_mineral_now()
            _cr = [(list(self.acts).index(c_), v_) for c_, v_ in _mr.items() if c_ in self.acts and v_ > 0]
            if _ft and _cr:
                fert = {"crops": _cr, "techs": _ft, "ecap": fert_efficiency_cap(self.data.region_id)}
                if float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0:
                    fert["tax"] = self._fert_tax_terms(_ft)
        # CAPRI's inhibitor on manure inside (capri-mod-proto): with an N row or the emission tax
        mni = None; _nip = None
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        if self._ni_inside() and (n_row is not None or float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0):
            _nip = self._manure_inhibitor_params()
            if _nip is not None:
                _al = list(self.acts)
                mni = {"w": [(_al.index(a_), float(m_)) for a_, m_ in _nip["man_d"].items()
                             if a_ in self.acts and float(m_ or 0.0) > 0],
                       "eff": _nip["sub"] * _nip["nman"], "smax": _nip["smax"], "S0": _nip["S0"],
                       "slope": _nip["slope"], "vtax": _nip["v_tax"]}
        try:
            _rx = getattr(self, "_dairy_req_extra", None)
            _rx = _rx if (_rx and max(c_ for a_ in _rx for c_, _ in _rx[a_]) < Q.shape[0]) else None
            _fg = self._ghg_feed_cost()
            os.environ["CAPRI_POLISH_TAG"] = self.data.region_id
            y, F, zA, info = solve_regional_conic(Q, c, A, b, list(self.acts), rats, fod, x_base=xb,
                                                  prices=getattr(self, "feed_prices", None),
                                                  techs=techs or None, fert=fert, n_row=n_row, req_extra=_rx,
                                                  m_row=m_row, feed_ghg=_fg, mni=mni)
            _rows_nm = [r_ for r_ in (n_row, m_row) if r_ is not None]
            if (techs or fert) and not _taxed and _rows_nm and info.get("status") in ("Solved", "AlmostSolved", "Solved (IPOPT polish)") \
                    and all(float(zA[r_]) <= 1e-9 for r_ in _rows_nm):
                y, F, zA, info = solve_regional_conic(Q, c, A, b, list(self.acts), rats, fod, x_base=xb,
                                                      prices=getattr(self, "feed_prices", None), req_extra=_rx,
                                                      feed_ghg=_fg)
                techs = []; fert = None; mni = None
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"feed-in-supply solve failed for {self.data.region_id}: {_exc!r}")
            return None
        if info.get("status") not in ("Solved", "AlmostSolved", "Solved (IPOPT polish)"):
            # K3 (docs/KNOWN_ISSUES.md): the caller falls back to the problem without feeding inside and without
            # technologies - a different model; say so instead of switching silently
            import warnings as _w
            _w.warn(f"conic solve {info.get('status')} for {self.data.region_id} after {info.get('iterations')} "
                    f"iterations: region solved without feeding inside and technologies", RuntimeWarning)
            self._conic_failed = str(info.get("status"))
            return None
        self._last_feed = F
        self._last_conic_duals = zA
        self._conic_ok = True
        self._conic_failed = None
        self._conic_status = str(info.get("status"))
        self._last_req_duals = info.get("req_duals") or {}
        if mni is not None:
            _T, _W = float(info.get("mni_T", 0.0)), float(info.get("mni_W", 0.0))
            _sh = min(max(_T / _W, 0.0), _nip["smax"]) if _W > 1e-12 else 0.0
            if _sh > 1e-9:
                for a_, m_ in _nip["man_d"].items():
                    m_ = float(m_ or 0.0)
                    if m_ > 0 and a_ in self.acts:
                        self._manure_ni_relief[a_] = _nip["sub"] * _nip["nman"] * _sh * m_
                        if a_ in _nip["app_nh3"]:
                            self._manure_ni_nh3[a_] = _sh * _nip["app_nh3"][a_]
                self._manure_ni_share = _sh
        # fertiliser technologies inside: regional shares and per-crop fertiliser factors
        self._fert_inside_factor = {}
        self._fert_inside_weight = {}
        if fert:
            acts_l = list(self.acts); area = 0.0; hsum = {}
            for col, nc in fert["crops"]:
                a_c = float(y[col]); area += a_c
                if a_c > 0 and nc > 0:
                    self._fert_inside_factor[acts_l[col]] = float(info["fert_m"].get(col, nc * a_c)) / (nc * a_c)
                    self._fert_inside_weight[acts_l[col]] = nc * a_c
            for (col, name), h_ in info.get("fert_H", {}).items():
                hsum[name] = hsum.get(name, 0.0) + h_
            self._fert_tech_shares = {k: v / area for k, v in hsum.items()} if area > 0 else {}
        if float(getattr(self, "_manure_ni_share", 0.0) or 0.0) > 0:
            self._fert_tech_shares = dict(getattr(self, "_fert_tech_shares", None) or {})
            self._fert_tech_shares["NITR_INH_MAN"] = float(self._manure_ni_share)
        # technology results for the accounts: shares per sub-activity from M / (w x), then
        # relief and NH3 saved per activity unit from the exact loss cascade
        if self._techs_inside():
            Mv = info.get("tech_M", {}) if techs else {}
            acts_l = list(self.acts)
            sh = {}
            for t in techs:
                x_a = float(y[acts_l.index(t["act"])])
                if x_a > 0 and t["w"] > 0:
                    sh.setdefault((t["act"], t["key"]), {})[t["tech"]] = \
                        float(Mv.get((t["act"], t["key"], t["tech"]), t["s0"] * t["w"] * x_a)) / (t["w"] * x_a)
            self._amm_record(sh)
        # dry matter (t) per animal and feed group, for CAPRI's feed-based cattle enteric
        # CH4 (GWPCH4ENT_): flexible feeds from F, fixed feeds at base per head x herd;
        # F and per-head kg x 1000 heads are both in t
        acts_ = list(self.acts); dm = {}; ft = {}
        for a, r in rats.items():
            if a not in acts_:
                continue
            herd = float(y[acts_.index(a)])
            for j, f in enumerate(r.feeds):
                amt = F.get((a, f)) if r.flex[j] else float(r.x0[j]) * herd
                if amt is not None and amt > 0:
                    dm.setdefault(a, {})[f] = float(amt) * float(r.dm[j])
                    ft.setdefault(a, {})[f] = float(amt)
        self._last_feed_dm = dm
        self._last_feed_t = ft
        return y
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
        # Livestock: CAPRI's market revenue per head (MREV), the SAME value the
        # margin calculation uses. price x yield is wrong for most animals -
        # their output units are unverified (UNVERIFIED_OUTPUT_UNITS): a pig
        # came to ~2,180 EUR/head, about twenty times too much, and a broiler
        # place ~1,430. The curvature is proportional to this revenue, so every
        # price or feed-cost change was damped by the same factor: a 26% cut in
        # the pig margin moved pigs by 0.24%, broilers by 0.01%. Base levels are
        # unaffected - calibration reproduces them whatever the curvature.
        _rev = getattr(self.data, "livestock_revenue_coef", None)
        # with CAPRI's margin basis (TOOU - TOIN) the curvature uses the same total output
        # value TOOU: with market revenue MREV, suckler cows (MREV 68 vs TOOU 620 EUR/head in
        # Duesseldorf, the rest calves) responded about nine times too strongly to any change
        # in their margin (a 35% calf price rise: +40% suckler cows in low-N-price regions)
        _ov = getattr(self.data, "livestock_output_value_coef", None) \
            if getattr(type(self), "use_livestock_cost_coef", False) else None
        gross = {}
        for a in self.acts:
            if a in ANIMALS and _ov is not None and a in _ov.index \
                    and pd.notna(_ov[a]) and float(_ov[a]) > 0:
                gross[a] = float(_ov[a])
                continue
            if a in ANIMALS and _rev is not None and a in _rev.index \
                    and pd.notna(_rev[a]) and float(_rev[a]) > 0:
                gross[a] = float(_rev[a])
                continue
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
        # FODDER BALANCE carries a positive shadow price at base, as in CAPRI:
        # f = r - Q x0 - A_f' lambda0 (lambda0 = CAPRI's unit value of the
        # fodder), so the base is optimal with the balance binding and its dual
        # equal to lambda0 - fodder crops earn it, animals pay it (two-way).
        for row, lam0, _b, _lab in self._fodder_rows():
            self.f = self.f - row * lam0

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _base_levels(self) -> pd.Series:
        # Called ~80 times per solve, rebuilding the same Series each time (11%
        # of run time in a profile). Base areas and herds are never modified in
        # place, so the result is cached - keyed on the identity of the two
        # inputs so it refreshes if either is replaced, and returned as a copy
        # so no caller can alter the cached value.
        key = (id(self.data.base_areas), id(self.data.base_animals))
        cached = getattr(self, "_base_levels_cache", None)
        if cached is None or cached[0] != key:
            crop_levels   = self.data.base_areas.reindex(CROPS).fillna(0.0)
            animal_levels = self.data.base_animals.reindex(ANIMALS).fillna(0.0)
            cached = (key, pd.concat([crop_levels, animal_levels]).reindex(self.acts).fillna(0.0))
            self._base_levels_cache = cached
        return cached[1].copy()

    #: broiler birds produced per census place and year (CAPRI 2030 reference)
    BROILER_BIRDS_PER_PLACE = param("BROILER_BIRDS_PER_PLACE")
    #: protein-rich feed is priced by the CAKE markets (crushing Stage 3): a cake
    #: price index weighted by CAPRI's EU cake feed use (2017 FAO_agg BAS), at
    #: CAPRI's base world prices. Replaces the soybean-meal PROXY (0.89 x the
    #: soybean price). Values read from the data files on first use.
    _CAKE_INDEX = None

    @classmethod
    def _cake_index(cls):
        """(weights, base prices) of the protein-feed cake index."""
        if cls._CAKE_INDEX is None:
            w, p = {}, {}
            try:
                import json
                from pathlib import Path
                root = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"
                b = json.load(open(root / "capri_oilseed_products_baseline.json"))["balances"]
                wp = pd.read_csv(root / "world_prices.csv").set_index("commodity")["price"]
                for c in ("SOYC", "RAPC", "SUNC"):
                    fe = float(b.get(f"EU27|{c}", {}).get("feed", 0.0))
                    if fe > 0 and c in wp.index:
                        w[c], p[c] = fe, float(wp[c])
            except Exception:
                w, p = {}, {}
            cls._CAKE_INDEX = (w, p)
        return cls._CAKE_INDEX

    def _protein_feed_cost_change(self, q, price_shock) -> float:
        """Cost change of q tonnes of protein-rich feed under the cake prices."""
        w, p = self._cake_index()
        ws = sum(w.values())
        if q <= 0 or ws <= 0:
            return 0.0
        return q * sum((w[c] / ws) * p[c] * float(price_shock.get(c, 0.0)) for c in w)
    #: EU feed use per cereal, CAPRI 2030 reference (FEDM, kt): the weights of
    #: the feed-cereal price change (other cereals include rye and oats)
    FEED_CEREAL_MIX = _csv_dict("2017/feed/feed_cereal_mix_2030.csv", "fedm_kt")

    def _compute_net_revenues(self, price_shock: Optional[pd.Series] = None):
        """
        Compute per-unit net revenues r_i:
          r_i = price_i × yield_i - variable_cost_i + cap_payment_i  (crops)
          r_i = price_i × yield_i - variable_cost_i                   (animals)
        """
        self._price_shock_now = price_shock
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
            # LIVESTOCK COSTS on the same basis as livestock revenue: CAPRI's
            # regional total inputs (LEVL x TOIN) / the model's head count
            # (livestock_cost_coef.csv). The per-head TOIN in variable_costs is
            # on CAPRI's activity-level basis, which differs from the model's
            # heads several-fold for bulls and heifers.
            _cc = getattr(self.data, "livestock_cost_coef", None)
            if getattr(type(self), "use_livestock_cost_coef", False) and act in ANIMALS \
                    and _cc is not None and act in _cc.index \
                    and pd.notna(_cc[act]) and float(_cc[act]) > 0:
                cost = float(_cc[act])
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
                # with CAPRI's margin basis (switch below): total output TOOU
                _ov = getattr(self.data, "livestock_output_value_coef", None)
                if getattr(type(self), "use_livestock_cost_coef", False) and _ov is not None \
                        and act in _ov.index and pd.notna(_ov[act]) and float(_ov[act]) > 0:
                    revenue = float(_ov[act])
                    # a commodity price moves the market part (MREV) only; young animals
                    # (the rest of TOOU) move with their own prices (young-animal markets)
                    if price_shock is not None:
                        revenue += self._market_revenue_change(act, float(rev_coef[act]), price_shock)
                elif price_shock is not None:
                    revenue *= 1.0 + float(price_shock.get(act, 0.0))

            _pc = getattr(self.data, "livestock_premium_coef", None)
            if act in ANIMALS and getattr(type(self), "use_livestock_cost_coef", False) and _pc is not None \
                    and act in _pc.index and pd.notna(_pc[act]):
                # CAPRI's premiums on the model's head basis, like revenue and costs
                # (livestock_premium_coef.csv: LEVL x PRME of CAPRI's activities / model
                # heads). Looking PRME up by the model's names left suckler cows, heifers,
                # calves, sheep, pigs and poultry without premiums.
                payment = float(_pc[act])
            elif premium is not None and act in premium.index and pd.notna(premium[act]):
                payment = float(premium[act])
            else:
                # no CAPRI premium (PRME) for the activity: none. The fallback was cap_payments.csv's BPS,
                # the loader's random generator written to disk (docs/SYNTHETIC_DATA_AUDIT.md)
                payment = 0.0

            # FEED COSTS follow feed prices. Animal margins were revenue minus a
            # FIXED variable cost, so dearer cereals never reached livestock:
            # under Farm-to-Fork (cereals +14%) poultry changed by exactly 0.0%
            # against CAPRI's -16%. The change in cost per head is the animal's
            # purchased cereal ration (t/head, feed_requirements.csv) times the
            # change in each cereal's price. Base costs already include feed, so
            # at base nothing changes. Protein meals (SOYM, RAPM, SUFM) are not
            # priced in this market and are left out.
            _rs = getattr(self, "ration_state", None)
            if act in ANIMALS and _rs and act in _rs and not getattr(type(self), "use_feed_in_supply", False):
                # EU RATION CHOICE (docs/FEED_RATION.md): the feed-cost change per
                # head comes from the ration chosen at the current feed prices
                cost += float(_rs[act].get("dcost", 0.0))
            elif act in ANIMALS and price_shock is not None:
                # FEED COSTS follow feed prices. Feed per head is CAPRI's 2017
                # regional total for the activity divided by this model's herd
                # (livestock_feed_coef.csv), so units and vintage match the
                # herds; the old feed table used CAPRI per-UNIT values on
                # census-stock herds (bulls 0.47 t of cereals per head against
                # 1.89, pigs 0.91 against 0.45).
                #  - cereals and protein-rich feed: the member state's CAPRI bulk
                #    price index (feedBlkPrice_, CES over the bulk's products) on
                #    the bulk's base price level (cereal mix at CAPRI's 2030 EU
                #    feed weights, cake index); before the first bulk prices,
                #    the mix and cake price changes themselves;
                #  - energy-rich feed: no market here, price unchanged.
                fc = getattr(self.data, "livestock_feed_coef", None)
                qc = float(fc.get(f"{act}_cereals", float("nan"))) if fc is not None else float("nan")
                qp = float(fc.get(f"{act}_protein", float("nan"))) if fc is not None else float("nan")
                if qc == qc:
                    wsum = sum(self.FEED_CEREAL_MIX.values())
                    _fbr = getattr(self, "feed_bulk_ratio", None) or {}
                    if "FCER" in _fbr:
                        lvl = sum((w / wsum) * float(self.data.producer_prices.get(feed, 0.0))
                                  for feed, w in self.FEED_CEREAL_MIX.items())
                        cost += qc * lvl * (float(_fbr["FCER"]) - 1.0)
                    else:
                        for feed, w in self.FEED_CEREAL_MIX.items():
                            p0 = float(self.data.producer_prices.get(feed, 0.0))
                            cost += qc * (w / wsum) * p0 * float(price_shock.get(feed, 0.0))
                    if qp == qp and qp > 0:
                        if "FPRO" in _fbr:
                            w_, p_ = self._cake_index()
                            ws_ = sum(w_.values()) or 1.0
                            cost += qp * sum((w_[c] / ws_) * p_[c] for c in w_) * (float(_fbr["FPRO"]) - 1.0)
                        else:
                            cost += self._protein_feed_cost_change(qp, price_shock)
                else:
                    fr = getattr(self.data, "feed_requirements", None)
                    if fr is not None and len(fr) and act in fr.index:
                        mult = self.BROILER_BIRDS_PER_PLACE if act == "BROI" else 1.0
                        for feed in ("SWHE", "BARL", "CORN", "OCER"):
                            if feed in fr.columns:
                                q = float(fr.at[act, feed]) * mult
                                if q > 0:
                                    p0 = float(self.data.producer_prices.get(feed, 0.0))
                                    cost += q * p0 * float(price_shock.get(feed, 0.0))
                        if "SOYM" in fr.columns:
                            q = float(fr.at[act, "SOYM"]) * mult
                            if q > 0:
                                cost += self._protein_feed_cost_change(q, price_shock)
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
    ORGANIC_YIELD_GAP = param("ORGANIC_YIELD_GAP")
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
    ORGANIC_OTHER_COST_RISE = param("ORGANIC_OTHER_COST_RISE")

    #: EU organic area already in place, subtracted from the target to give the
    #: share that actually CONVERTS. CAPRI sets this explicitly:
    #: p_organicAreaTarget("EU27yr19") = 0.25 - 0.10 in
    #: gams/pol_input/greendeal/load_organic_targets.gms, i.e. a 15 percentage
    #: point shock, not 25. This model applied the full target as if every
    #: hectare converted, nearly double CAPRI's shock, which is why oilseeds
    #: (1.43x) and permanent crops (1.57x) overshot CAPRI's published results.
    #: CAPRI breaks the 15 points down by member state and crop group from Eurostat
    #: organic areas (organic_targets.gdx, organic_targets_UAA.gdx); that breakdown is
    #: loaded (organic_targets_ms.csv) and used for every EU region. This EU figure
    #: is only the fallback for a region without it.
    ORGANIC_BASELINE_SHARE = param("ORGANIC_BASELINE_SHARE")

    #: Crops occupying PERMANENT land - the same set the land data is built
    #: with in tools/build_capri_base.py. Everything else except grass is arable.
    PERMANENT_LAND_CROPS = ("WINE", "OLIV", "APPL", "OFRU", "CITR", "TAGR")

    def _organic_baseline(self) -> float:
        """EU organic share already in place (CAPRI load_organic_targets.gms: the EU target is
        0.25 - 0.10). Only a fallback: every EU member state has CAPRI's own percentage-point
        targets (organic_targets_ms.csv), which already net out its existing organic area; CAPRI
        applies them uniformly to the member state's regions. (A per-country table of 2018-2019
        Eurostat shares used here before CAPRI's targets were loaded was no longer reached for any
        EU region and has been removed.)"""
        return self.ORGANIC_BASELINE_SHARE

    #: CAPRI's assumed average yield loss for a 50% pesticide reduction
    #: (JRC121368, from Sanchez et al. 2019: 18.6% of EU production potentially
    #: affected by 20 pests, worst case 50% loss on that share). CAPRI has NO
    #: dose-response function for plant protection -- unlike fertiliser -- so
    #: this is an explicit assumption in CAPRI too, not a derived quantity.
    PESTICIDE_YIELD_LOSS_AT_50PCT = param("PESTICIDE_YIELD_LOSS_AT_50PCT")

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
    PESTICIDE_OTHER_COST_RISE = param("PESTICIDE_OTHER_COST_RISE")

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
    OTHER_COST_SHARE = _csv_dict("2017/supply/crop_cost_shares.csv", "other_cost_share")

    #: Share of total input cost that is fertiliser (CAPRI FERT), same basis.
    #: Organic conversion sets mineral fertiliser to zero, so this is a cost
    #: SAVING that partly offsets the other-cost rise - heavily for arable
    #: crops (wheat 42, maize 44 per cent) and barely at all for fruit (1).
    FERT_COST_SHARE = _csv_dict("2017/supply/crop_cost_shares.csv", "fert_cost_share")

    #: FALLBACK ONLY (since October 2026): the pesticide and organic instruments use CAPRI's
    #: regional PLAP, INPO and FERT costs per ha (data.input_costs_ha); these EU-wide shares
    #: serve crops CAPRI does not grow in a region. The same applies to OTHER_COST_SHARE and
    #: FERT_COST_SHARE above.
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
    PPP_COST_SHARE = _csv_dict("2017/supply/crop_cost_shares.csv", "ppp_cost_share")

    def _input_cost(self, a: str, item: str, share_table: dict) -> float:
        """EUR/ha of input `item` ('plap', 'inpo', 'fert') for crop a: CAPRI's regional cost
        (tools/build_plant_protection_cost.py), else the EU-wide share of input cost times the
        crop's input cost (REGISTERED fallback, crops CAPRI does not grow in the region)."""
        t = getattr(self.data, "input_costs_ha", None)
        col = item + "_eur_ha"
        if t is not None:
            # the region's table as a plain dict, built once per table (scalar pandas lookups were ~10% of a run)
            memo = self.__dict__.get("_input_cost_memo")
            if memo is None or memo[0] is not t:
                memo = (t, {(r, c_): float(v) for r, row in t.to_dict("index").items() for c_, v in row.items()
                            if isinstance(v, (int, float)) and v == v})
                self._input_cost_memo = memo
            v = memo[1].get((a, col))
            if v is not None:
                return v
        c = float(self.data.variable_costs.get(a, 0.0))
        return c * float(share_table.get(a, 0.0) or 0.0) if c > 0 else 0.0

    def apply_pesticide_reduction(self, reduction: float,
                                  organic_share: Optional[float] = None) -> None:
        """Apply the Farm-to-Fork pesticide target as CAPRI does (pol_input/greendeal/conventional_io.gms).

        Four shocks on the conventional area of every crop, in EU regions: plant protection (PLAP)
        cut by the remaining target, other inputs (INPO) +50% at the 50% target, a yield loss, and a
        minimum catch-crop area (pesticide cut / 2, see _cover_crop_requirement). PLAP and INPO are
        CAPRI's own costs per ha by region and crop (data.input_costs_ha,
        tools/build_plant_protection_cost.py); EU-wide shares remain only as fallback.

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
        # CAPRI applies the pesticide target to the CONVENTIONAL area only
        # (pol_input/greendeal/conventional_io.gms). The 50% cut is a TOTAL
        # target: organic conversion already delivers part of it, since organic
        # hectares use no plant protection, and only the REMAINING cut is made on
        # conventional land, so the overall reduction stays 50%. The yield loss
        # and the rise in other inputs likewise fall on the conventional share.
        # Applying all three to every hectare double-counted wherever organic and
        # pesticide instruments combine; it made oilseed area fall 12-13% under
        # Farm-to-Fork against the ~5% implied by CAPRI's figures.
        _targets = getattr(self.data, "organic_targets_pp", None)
        _org_default = (max(0.0, float(organic_share) - self._organic_baseline())
                        if organic_share else 0.0)
        for a in self.acts:
            if a not in self.PESTICIDE_AFFECTED:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            o = (self._organic_converted(a, organic_share, _targets, _org_default)
                 if organic_share else 0.0)
            o = min(max(o, 0.0), 0.99)
            conv = 1.0 - o
            ppp_cut = max(0.0, float(reduction) - o)      # remaining target, whole crop
            # The yield loss must reach BOTH the objective and the reported
            # yields. It used to change net revenue only, so it steered what
            # farmers grew but left gross_output computed on unshocked yields:
            # EU cereal PRODUCTION fell 6% where CAPRI reports 15%, even though
            # our cereal AREA fell 5.9% against CAPRI's 4%. The area response
            # was never the problem; the yield effect was missing from the
            # output. CAPRI reports production, so this is what is compared.
            new_ylds[a] = y * (1.0 - loss * conv)
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss * conv
            # CAPRI cuts plant-protection expenditure by the target share and
            # raises other costs by 50%. Both are represented here relative to
            # the crop's assumed PPP share of variable cost: the saving is a
            # margin GAIN, the other-cost rise a partial offset.
            # CAPRI's PLAP row of the crop in this region (EUR/ha), cut by the remaining target
            nr[a] = float(nr.get(a, 0.0)) + self._input_cost(a, "plap", self.PPP_COST_SHARE) * ppp_cut
            # CAPRI raises its OTHER INPUTS category by 50% at the 50% target.
            # This used to be applied to the plant-protection share, where it
            # cancelled the saving almost exactly and made the cost channel a
            # no-op. Other inputs are 48% of cost for table grapes and 41% for
            # wine but only 9% for wheat, so the shock is what makes CAPRI's
            # permanent crops respond far more than its cereals.
            nr[a] = float(nr.get(a, 0.0)) - (
                self._input_cost(a, "inpo", self.OTHER_COST_SHARE)
                * self.PESTICIDE_OTHER_COST_RISE * (reduction / 0.50) * conv)
        self.data.yields = new_ylds
        self.net_revenues = nr
        self._cover_crop_requirement(float(reduction), organic_share)

    def _crop_mineral_rate(self, a: str) -> float:
        """The crop's base mineral N application (kg N/ha; the environmental module's rate): the part of its
        balance coefficient that CAPRI's fertiliser technologies act on. Its unit coefficient also carries its
        share of the manure- and residue-covered need, which the animals' manure and the residues displace; at the
        base those cancel over the region. (Until Sprint 9e the technologies scaled the whole unit coefficient,
        which saved on the manure-covered need as well: ~40% more mineral N saved in the rows than in the accounts,
        Upper Bavaria wheat 108 against 77 kg N/ha.)"""
        env_ = getattr(self, "_env_for_surplus", None)
        if env_ is None:
            return 0.0
        try:
            return float(env_._base_mineral_rate(self.data.region_id, a))
        except Exception:
            return 0.0

    def _cover_n_increment(self) -> float:
        """N (t) from the catch crops added by the Farm-to-Fork requirement: increment (1000 ha)
        x CAPRI's BioFix (t N per ha) x 1000."""
        cv = getattr(self, "_cover", None)
        return float(cv["delta"]) * float(cv["biofix"]) * 1000.0 if cv else 0.0

    def _cover_crop_requirement(self, reduction: float, organic_share) -> None:
        """CAPRI's minimum catch-crop area under the Farm-to-Fork targets (e_minCoverCrops).

        pol_input/greendeal/organic_io.gms (coverCrop 50%) and conventional_io.gms (coverCrop =
        pesticide cut / 2, on the remaining target): with o the region's organic area target and
        r the pesticide cut (shares),
            minimum CATC = [0.5 o + 0.5 max(0, r - o)] x (UAAR - sum_c crop_c x winter cover share_c)
                           + baseline CATC
        CAPRI subtracts the area under winter cover with p_winterCoverShare0, the shares as given
        (NUTS2 entries for Austria and a few German regions only); elsewhere nothing is subtracted
        and the requirement exceeds the area that can carry a catch crop (its own winterCover_ row,
        with the filled shares) in 100 regions, an infeasible pair. REGISTERED: the filled shares
        (NUTS2 <- member state <- EU, define_greening_limits.gms) in both, and the requirement capped
        at that potential area at base. Sets self._cover: requirement and increment (1000 ha),
        UAAR, catch-crop N per ha and cost per ha."""
        cc = getattr(self.data, "cover_crops", None)
        wcs = getattr(self.data, "winter_cover_share", None)
        if cc is None or wcs is None or reduction <= 0:
            return
        base = self._base_levels()
        uaa = float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c in base.index))
        if uaa <= 0:
            return
        covered = sum(float(base.get(c, 0.0) or 0.0) * float(wcs.at[c, "share"])
                      for c in wcs.index if c in base.index)
        targets = getattr(self.data, "organic_targets_pp", None)
        o = 0.0
        if organic_share:
            v = targets.get("uaa_pp") if (targets is not None and hasattr(targets, "get")) else None
            o = (float(v) / 100.0 * max(0.0, (100.0 * float(organic_share) - 12.0) / 13.0) if v is not None and not pd.isna(v)
                 else max(0.0, float(organic_share) - self._organic_baseline()))
        f = 0.5 * o + 0.5 * max(0.0, reduction - o)
        c0 = float(cc.get("catc_share_2030", 0.0) or 0.0) * uaa
        pot = max(0.0, uaa - covered)
        req = min(f * pot + c0, max(pot, c0))
        bf = cc.get("biofix_t_n_ha")
        self._cover = {"req": req, "delta": max(0.0, req - c0), "base": c0, "uaa": uaa, "potential": pot,
                       "biofix": float(bf) if bf is not None and not pd.isna(bf) else 0.0,
                       "cost": float(cc.get("catc_cost_eur_ha", 0.0) or 0.0)}


    #: Yield response to a change in the crop's own price, CAPRI's: yields "updated depending on price changes
    #: against the baseline" (supply/endog_yields.gms: yield x (price / last price) ** p_yieldElas), with
    #: p_yieldElas from supply/yield_elas.gms - cereals 0.3, oilseeds 0.2, potatoes 0.2, no other crop
    #: (capri_data/2017/supply/yield_price_elasticity.csv). It was 0.15 for every crop, a literature value.
    @staticmethod
    def yield_price_elasticity() -> Dict[str, float]:
        global _YIELD_ELAS
        if _YIELD_ELAS is None:
            f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "supply" / "yield_price_elasticity.csv"
            _YIELD_ELAS = {r.crop: float(r.elasticity) for r in pd.read_csv(f).itertuples()}
        return _YIELD_ELAS

    def apply_yield_price_response(self, price_shock: pd.Series) -> None:
        """Let yields respond to own-price changes, as CAPRI's stage one does.

        yield_new = yield_base * (1 + price_change) ** elasticity (CAPRI's, per crop)

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
        elas = self.yield_price_elasticity()

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
            eps = float(elas.get(a, 0.0))
            if dp == 0.0 or eps <= 0:
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
        _m = self.__dict__.get("_oyg_memo")                  # per table: the lookup ran ~170k times per run
        if _m is None or _m[0] is not table:
            _m = (table, {})
            self._oyg_memo = _m
        if activity in _m[1]:
            return _m[1][activity]
        _m[1][activity] = v_ = self._organic_yield_gap_uncached(activity, table)
        return v_

    def _organic_yield_gap_uncached(self, activity: str, table) -> float:
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


    def _organic_converted(self, activity: str, share: float, targets,
                           default: float) -> float:
        """Share of this activity's area that converts to organic.

        CAPRI does not move every member state to 25%. It burden-shares the EU's
        15-point shock (25% target minus 10% existing) across member states and
        crop groups: gams/pol_input/greendeal/organic_targets.gdx gives the extra
        points for arable land, permanent grassland and permanent crops, per
        member state, and those weight to exactly 15.0 points EU-wide. France
        converts 45.6% of its permanent crops, Austria 5.0%; Austria, already
        past 25%, still converts 7.5 points of UAA where a distance-to-25% rule
        gave it nothing.

        The requested share scales the ambition (0.25 = CAPRI's full target).
        Falls back to the member state's UAA-wide figure, then to the
        distance-to-target rule, where a crop group has no entry.
        """
        if targets is None:
            return default
        if activity in self.PERMANENT_LAND_CROPS:
            col = "permanent_pp"
        elif activity == "GRAS":
            col = "grassland_pp"
        else:
            col = "arable_pp"
        val = targets.get(col) if hasattr(targets, "get") else None
        if val is None or pd.isna(val):
            val = targets.get("uaa_pp") if hasattr(targets, "get") else None
        if val is None or pd.isna(val):
            return default
        # CAPRI scales its targets to the requested ambition as (orgTarg - 12) / (25 - 12)
        # (load_organic_targets.gms; orgTarg in %), exactly 1 at the 25% target
        scale = max(0.0, (100.0 * float(share) - 12.0) / (25.0 - 12.0))
        return max(0.0, min(1.0, float(val) / 100.0 * scale))

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
        converted_default = max(0.0, float(share) - self._organic_baseline())
        _org = getattr(self.data, "organic_targets_pp", None)
        for a in self.acts:
            converted = self._organic_converted(a, share, _org, converted_default)
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
            # NO 0.45 discount here. CAPRI's organic_area.gms scales the organic
            # yield gap by 0.45 ONLY when %pest_disagg% is on - a mode in which
            # the pesticide yield effect is endogenous (v_yldPestFac). The
            # Farm-to-Fork study used the other mode: an explicit 10% yield loss
            # (pesticides.gms argument), in which the organic gap applies IN
            # FULL to organic land. This model had mixed the two. The discount
            # once offset a double count, while the pesticide loss also fell on
            # organic hectares; since the pesticide target applies to
            # conventional land only, it discounted organic land a second time
            # and understated the cereal yield loss (cereal area matched CAPRI,
            # yields fell 8% against 11%).
                # CAPRI converts the DISTANCE from the existing organic area to the
            # target, not the whole target.
            yield_factor = 1.0 - gap * converted
            cost_change = converted * (
                self._input_cost(a, "inpo", self.OTHER_COST_SHARE) * self.ORGANIC_OTHER_COST_RISE
                - self._input_cost(a, "fert", self.FERT_COST_SHARE)
                - self._input_cost(a, "plap", self.PPP_COST_SHARE))
            # As with the pesticide instrument, the yield gap must reach the
            # REPORTED yields too, not only the objective. CAPRI reports
            # PRODUCTION, and a yield gap that never lands in yields is
            # invisible there: EU cereal production fell 6% here against
            # CAPRI's 15%, while cereal AREA fell 5.9% against CAPRI's 4%.
            new_ylds[a] = y * yield_factor
            delta = (p * y * (yield_factor - 1.0)) - cost_change
            nr[a] = float(nr.get(a, 0.0)) + delta
            # Converted land uses NO mineral fertiliser (CAPRI's
            # organic_minfert_redu.gms). Only its COST was removed here, so in
            # the nitrogen balance and the environmental accounts organic land
            # still spread full mineral N. The mineral-N factor travels the
            # same path as the fertiliser technologies (multiplied with them).
            if converted > 0:
                self._n_intensity = getattr(self, "_n_intensity", {}) or {}
                self._n_intensity[a] = self._n_intensity.get(a, 1.0) * max(0.0, 1.0 - converted)
                nc_ = self.data.nutrient_coefs
                if a in nc_.index and "N" in nc_.columns:
                    nc_ = nc_.copy()
                    nc_.at[a, "N"] = float(nc_.at[a, "N"]) * max(0.0, 1.0 - converted)
                    self.data.nutrient_coefs = nc_
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


    #: CAPRI's ammonia technologies adopted under the N shadow price (switch)
    use_manure_techs = False

    def _manure_techs(self):
        """CAPRI's ammonia technologies for this region: {animal: [sub-activity block]}
        (capri_data/2017/abatement/ammonia/ammonia_tech_model.csv, capri_mod/supply/ammonia_techs.py)."""
        from pathlib import Path as _P
        from capri_mod.supply import ammonia_techs as _at
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia" / "ammonia_tech_model.csv"
        return _at.load(f).get(self.data.region_id, {})

    def _amm_record(self, shares: dict):
        """Accounts for given shares {(animal, sub): {tech: share}} (missing: base shares):
        N relief and NH3 saved per activity unit, extra cost per unit, reported shares (share
        of the animal's units) and the shares for the next linearisation."""
        from capri_mod.supply import ammonia_techs as _at
        self._animal_n_relief, self._animal_nh3_saved, self._manure_tech_shares = {}, {}, {}
        self._amm_cost = {}
        if not getattr(self, "use_manure_techs", False):
            return
        ctx = self._amm_context()
        if ctx is None:               # no N balance this solve: base shares, for reporting
            for a, subs in self._manure_techs().items():
                if a in self.acts:
                    for s in subs:
                        for t in s["techs"]:
                            k = (a, t["tech"])
                            self._manure_tech_shares[k] = self._manure_tech_shares.get(k, 0.0) + s["w"] * t["ini"]
            return
        techs, man_d, nh3, sub = ctx
        last = {}
        for a, subs in techs.items():
            mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
            if a not in self.acts or mN <= 0 or f <= 0:
                continue
            sc = self._amm_scale(subs, mN, f)
            saved = cost = 0.0
            for s in subs:
                ini = _at.initial(s)
                sh = dict(ini); sh.update(shares.get((a, s["key"]), {}))
                last[(a, s["key"])] = sh
                saved += s["w"] * sc * s["mrel"] * (_at.loss(s, ini) - _at.loss(s, sh))
                cost += s["w"] * s["stock"] * _at.cost(s, sh)
                for t in s["techs"]:
                    k = (a, t["tech"])
                    self._manure_tech_shares[k] = self._manure_tech_shares.get(k, 0.0) + s["w"] * sh[t["tech"]]
            if abs(saved) > 0:
                self._animal_n_relief[a] = sub * saved
                self._animal_nh3_saved[a] = saved
            self._amm_cost[a] = cost
        self._amm_last = last

    def _apply_manure_techs(self, lam: float):
        """CAPRI's ammonia technologies, adopted under the N shadow price
        (docs/MITIGATION_IN_SUPPLY.md; CAPRI ammo_tech.gms + supply_model.gms).

        Per sub-activity, shares from CAPRI's first-order conditions (ammonia_techs.choose):
        marginal cost thresh + slope (s - ini) (CAPRI's calibrated kappa2 + gamma), marginal
        benefit lam x substitution factor x N saved per unit of share through the loss
        cascade; manure-management options share one limit (TotMit_, NH3MAN), application
        options another (NH3APP). Effects: the animal's N-row coefficient falls by sub x N
        saved; the extra cost per unit comes off its margin. At lam = 0 the base shares are
        recorded (for reporting)."""
        if self._techs_inside():
            return          # decided inside the regional conic model: keep its results
        from capri_mod.supply import ammonia_techs as _at
        if not getattr(self, "use_manure_techs", False):
            self._animal_n_relief, self._animal_nh3_saved, self._manure_tech_shares = {}, {}, {}
            return
        ctx = self._amm_context()
        shares = {}
        if ctx is not None and lam and lam > 0:
            techs, man_d, nh3, sub = ctx
            for a, subs in techs.items():
                mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
                if a not in self.acts or mN <= 0 or f <= 0:
                    continue
                sc = self._amm_scale(subs, mN, f)
                for s in subs:
                    shares[(a, s["key"])] = _at.choose(s, lam * sub, sc * s["mrel"])
        self._amm_record(shares)
        for a, c in (getattr(self, "_amm_cost", None) or {}).items():
            if c and a in self.net_revenues.index:
                self.net_revenues[a] = float(self.net_revenues[a]) - c

    def _apply_manure_inhibitor(self, lam: float):
        """CAPRI's nitrification inhibitors on applied manure (target N2OMAN, envind/ghgMiti.gms):
        manure N counts x (1 + share x NMAN) in the crop nutrient balance (NUTNED_), so the same
        crop need is met with less mineral N. NMAN as NMIN from QEmitt; restricted where
        over-fertilisation is low relative to the manure availability factor a (restMitFert):
        NMAN = 0 if x + 0.1 <= a, ((x + 0.1)/a - 1) ** 1.1 where smaller. Maximum share = 1 - the
        grazing share of manure N. Cost per tonne of manure N (GHG_Mit_Cost_: x v_ManureNPK),
        calibrated as the other options without farm-size curves (relSubs 1.2/0.2). Value per t
        of manure N: N-balance price x a x NMAN (the mineral N it replaces). Its share is separate
        from the mineral-fertiliser options (TotMitFertMan_), outside Tot_MitFert_.
        REGISTERED: the crop-need floor on mineral N keeps a x manure without the gain."""
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        if self._ni_inside():
            return                       # decided inside the regional conic model (capri-mod-proto)
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        lam = float(lam or 0.0)
        if not getattr(self, "use_manure_techs", False) or (lam <= 0 and tax <= 0):
            return
        P = self._manure_inhibitor_params()
        if P is None:
            return
        sub, nman, smax, S0, slope, app_nh3, v_tax, man_d = (P[k] for k in (
            "sub", "nman", "smax", "S0", "slope", "app_nh3", "v_tax", "man_d"))
        v = 1000.0 * lam * sub * nman + v_tax                # EUR per t of manure N
        sh = min(max((v - S0) / slope, 0.0), smax)
        if sh <= 0:
            return
        c_t = S0 * sh + 0.5 * slope * sh * sh               # EUR per t of manure N
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0)
            if mN <= 0:
                continue
            self._manure_ni_relief[a] = sub * nman * sh * mN
            if a in self.net_revenues.index:
                # option cost; under the emission tax the tax saved per head at this share (the animal's own
                # coefficient is taken at no adoption) - the N value reaches the animal through the N row instead
                self.net_revenues[a] = float(self.net_revenues[a]) - (c_t - v_tax * sh) * mN / 1000.0
            if a in app_nh3:
                self._manure_ni_nh3[a] = sh * app_nh3[a]      # t NH3-N per activity unit
        self._manure_ni_share = sh

    #: capri-mod-proto: inhibitors on manure as a decision of the regional conic model (no N-price search)
    ni_inside_model = True

    def _ni_inside(self) -> bool:
        return bool(getattr(type(self), "ni_inside_model", False) and self._techs_inside())

    def _manure_inhibitor_params(self):
        """The parameters of CAPRI's inhibitor on manure for this region (see _apply_manure_inhibitor), or None:
        sub, nman, smax, S0, slope (EUR per t of manure N), app_nh3 (t NH3-N per activity unit at full adoption),
        v_tax (EUR per t of manure N treated), man_d (t manure N per activity unit)."""
        if not getattr(self, "use_manure_techs", False):
            return None
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        # national entry (fert_options_jul15.csv is keyed by CAPRI codes)
        _ms = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR"}.get(self.data.region_id[:2], self.data.region_id[:2]) + "000000"
        ni = next((t for t in fert_option_table().get(_ms, []) if str(t.option).upper() == "NITR_INH"), None)
        act_ = active_technologies()
        if ni is None or (act_ is not None and "NITR_INH" not in act_):
            return
        ctx = self._amm_context()
        if ctx is None:
            return
        techs, man_d, nh3, sub = ctx
        if sub <= 0:
            return
        q0, k1 = float(ni.QEmitt_noc), float(ni.costParLin)
        q = 0.9 * q0            # ghgMiti.gms l. 110: QEmitt(NITR_INH) = 0.9 x QEmitt(NOC), also for N2OMAN
        if not (q > 0 and q0 > q and k1 > 0):
            return
        nman = (q0 / q - 1.0) ** P_FERT_EFF_COR
        x = overfert_factor(self.data.region_id)
        if x is not None:
            cap = x + OVERFERT_MARKUP
            if cap <= sub:
                return
            if cap < (nman ** (1.0 / P_FERT_EFF_COR) + 1.0) * sub:
                nman = (cap / sub - 1.0) ** P_FERT_EFF_COR
        # maximum share: manure N not dropped on pasture (grazing shares of the ammonia data)
        base = self._base_levels()
        tot = graz = 0.0
        for a, subs in techs.items():
            if a not in self.acts:
                continue
            mn = float(man_d.get(a, 0.0) or 0.0) * float(base.get(a, 0.0) or 0.0)
            g = sum(s_["w"] * s_["g"] for s_ in subs)
            tot += mn; graz += mn * g
        smax = 1.0 - graz / tot if tot > 0 else 0.0
        if smax <= 0:
            return
        S0, slope = 0.2 * k1, k1 * (1.2 - 0.2) / smax
        # application NH3 side effect (ghgMiti.gms l. 557-563, p_litRevFertTechs NH3APP): on
        # treated manure the application emission factor is (1 - lit) x (1 + NMAN) times
        # NOC's; base = the cascade's application loss at the ammonia options' latest shares
        from capri_mod.supply import ammonia_techs as _at
        lit = fert_side_value(self.data.region_id, "NITR_INH_MAN", "NH3APP")
        f_app = ((1.0 - lit) * (1.0 + nman) - 1.0) if lit is not None else 0.0
        last = getattr(self, "_amm_last", None) or {}
        app_nh3 = {}                                         # t NH3-N per activity unit at full adoption
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0)
            if mN > 0 and f_app and a in techs and float(nh3.get(a, 0.0) or 0.0) > 0:
                subs = techs[a]
                sc = self._amm_scale(subs, mN, float(nh3[a]))
                app = sum(s_["w"] * sc * s_["mrel"] * _at.app_loss(s_, last.get((a, s_["key"]), _at.initial(s_)))
                          for s_ in subs)
                app_nh3[a] = f_app * app
        v_tax = self._manure_inhibitor_tax_value(tax, sub, nman, man_d, app_nh3, base) if tax > 0 else 0.0
        return {"sub": sub, "nman": nman, "smax": smax, "S0": S0, "slope": slope, "app_nh3": app_nh3,
                "v_tax": v_tax, "man_d": man_d}

    def _manure_inhibitor_tax_value(self, tax, sub, nman, man_d, app_nh3, base) -> float:
        """CAPRI's emission tax on inhibitors on manure (Sprint 9m): EUR per t of manure N treated, the tax on the
        emissions it saves, as the accounts count them - (1) the mineral N it displaces (sub x NMAN per t) at the soil
        N2O factor; (2) application N2O x CAPRI's literature effect N2OAPP (EnvironmentalModule: fa x (1 - share x
        lit)), from the animals' application factor per t of excreted N; less (3) the indirect N2O of the extra
        application NH3 (NH3APP). Weighted over the region's animals by their base manure N (REGISTERED: weights and the
        ammonia cascade multiplier on application N2O held at base)."""
        from capri_mod.environmental.environmental_module import EF_SOIL_N2O_INDIRECT, GWP_N2O
        env_ = getattr(self, "_env_for_surplus", None)
        k = 44.0 / 28.0 * GWP_N2O
        v = sub * nman * self._ef_mineral_n2o()
        lit2 = fert_side_value(self.data.region_id, "NITR_INH_MAN", "N2OAPP")
        tot = n2o = nh3x = 0.0
        for a in self.acts:
            mN = float(man_d.get(a, 0.0) or 0.0); x = float(base.get(a, 0.0) or 0.0)
            if mN <= 0 or x <= 0:
                continue
            tot += mN * x
            nh3x += float(app_nh3.get(a, 0.0)) * x
            if lit2 and env_ is not None:
                try:
                    mf = env_._manure_n2o_factor(self.data.region_id, a)
                    ex = float(env_._n_excretion(self.data.region_id, a))          # kg N per head = t per 1000 heads
                except Exception:
                    mf, ex = None, 0.0
                if mf is not None:
                    n2o += float(mf[1]) * ex * x
        if tot <= 0:
            return 0.0
        v += (float(lit2 or 0.0) * n2o / tot) * k
        v -= (nh3x / tot) * EF_SOIL_N2O_INDIRECT * k
        return tax * v

    #: kg N excreted per kg nitrate fed (CAPRI line_nitr.gms: +0.42% of DM intake at 1.5%)
    NITR_N_EXCR = param("NITR_N_EXCR")

    def _nitrate_extra(self) -> dict:
        """Extra N excretion from nitrate in the ration, t N per activity unit
        (1000 heads): 0.28 kg N per kg nitrate per head."""
        rs = getattr(self, "ration_state", None) or {}
        return {a: self.NITR_N_EXCR * float(v.get("nitr_kg", 0.0))
                for a, v in rs.items() if isinstance(v, dict) and float(v.get("nitr_kg", 0.0)) > 0}

    def _nitrate_row_term(self, a) -> float:
        """Extra manure N enters the balance like any manure: (1 - substitution)."""
        ex = self._nitrate_extra().get(a, 0.0)
        if ex <= 0:
            return 0.0
        env_ = getattr(self, "_env_for_surplus", None)
        try:
            sub = float(env_._substitution(self.data.region_id)[0]) if env_ is not None else 0.0
        except Exception:
            sub = 0.0
        return (1.0 - sub) * ex

    def _apply_balance_price(self, lam: float):
        """Fertiliser response to the nitrogen-balance price, as CAPRI models it.

        CAPRI's supply model has NO nitrogen yield response: crop yields are
        exogenous shifts (capmod/shift_yields.gms). It meets a nitrogen target
        partly through FERTILISER-EFFICIENCY TECHNOLOGIES - precision farming,
        variable-rate application, nitrification inhibitors, timing - which let
        the same crop need be met with less purchased fertiliser: in its crop
        nutrient balance mineral N counts x (1 + SUM_tech share x NMIN).
        JRC121368 states the GNB target was met 'with nitrogen mitigation
        technologies made available to farmers'.

        Shares follow CAPRI's first-order conditions per tonne of crop N need (the basis of
        CAPRI's cost of these options): marginal cost S0 + slope (s - s0) (CAPRI's calibration,
        _fert_techs) against the value lam x NMIN / (1 + E)^2 of the mineral N saved, with the
        options' shares summing to at most 1 (TotMit_) and CAPRI's Tot_MitFert_ cap on E.
        Mineral N per ha then falls by (1 + E0) / (1 + E) for every fertilised crop. YIELDS DO
        NOT CHANGE; each crop bears the extra cost in proportion to its N need.

        (This replaced a Mitscherlich intensity response that cut fertiliser
        THROUGH yield loss - not CAPRI's mechanism - under which crops carried too
        much of the adjustment: cereals 1.28x, oilseeds 1.42x CAPRI, herds too
        little.)
        """
        # keep factors already set this solve (organic land: no mineral N)
        self._n_intensity = getattr(self, "_n_intensity", {}) or {}
        if self._techs_inside():
            # decided inside the regional conic model: keep its results (a reset here, after
            # the last solve, erased the reported shares). Inhibitors on manure are not in the
            # conic block: decided here at the current N price, as outside
            self._apply_manure_inhibitor(lam)
            return None
        self._fert_tech_shares = {}
        self._apply_manure_techs(lam)
        self._apply_manure_inhibitor(lam)
        srow = getattr(self, "_surplus_row", None)
        _mc = getattr(self, "_mineral_cap", None) or {}
        techs = srow[5] if (srow is not None and len(srow) > 5) else (_mc.get("techs") or [])
        if not lam or lam <= 0 or not techs:
            return None
        nmin_ha = srow[2] if (srow is not None and len(srow) > 2) else (_mc.get("nmin") or {})
        base = self._base_levels()
        crops = [c for c in CROPS if c in self.acts and float(nmin_ha.get(c, 0.0)) > 0]
        if not crops:
            return None
        e0 = sum(nm * s0 for _, nm, _, _, s0, _ in techs)
        lam_t = 1000.0 * float(lam)          # EUR per t N (lam: kEUR/t)

        # CAPRI's choice per tonne of crop N need: min sum_t [S0 (s - s0) + 0.5 slope (s - s0)^2]
        # + lam / (1 + E), E = sum s NMIN, 0 <= s <= smax, sum s <= 1 (TotMit_), and Tot_MitFert_
        # E <= cap. First-order conditions: s_t = s0 + (lam NMIN_t / (1 + E)^2 - S0_t - mu_cap
        # NMIN_t - mu) / slope_t; E solved as a fixed point (the right side falls in E).
        def _at(E, mu_cap):
            def sh(mu):
                return {nm_: min(max(s0_ + (lam_t * nm / (1.0 + E) ** 2 - S0_ - mu_cap * nm - mu) / sl_, 0.0), smx)
                        for nm_, nm, S0_, sl_, s0_, smx in techs}
            o = sh(0.0)
            if sum(o.values()) > 1.0:
                lo, hi = 0.0, lam_t + max(t_[3] for t_ in techs)
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    lo, hi = (mid, hi) if sum(sh(mid).values()) > 1.0 else (lo, mid)
                o = sh(hi)
            return o

        def _solve(mu_cap):
            lo, hi = 0.0, sum(nm * smx for _, nm, _, _, _, smx in techs)
            for _ in range(60):                           # E = g(E), g decreasing
                mid = 0.5 * (lo + hi)
                g = sum(v * nm for (nm_, nm, *_r), v in zip(techs, _at(mid, mu_cap).values()))
                lo, hi = (mid, hi) if g > mid else (lo, mid)
            return _at(hi, mu_cap)

        sh = _solve(0.0)
        cap = fert_efficiency_cap(self.data.region_id)
        E = sum(sh[nm_] * nm for nm_, nm, *_r in techs)
        if cap is not None and E > cap + 1e-12:
            lo, hi = 0.0, lam_t * max(1.0, max(nm for _, nm, *_r in techs))
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                o = _solve(mid)
                lo, hi = (mid, hi) if sum(o[nm_] * nm for nm_, nm, *_r in techs) > cap else (lo, mid)
            sh = _solve(hi)
        e = sum(sh[nm_] * nm for nm_, nm, *_r in techs)
        f = (1.0 + e0) / (1.0 + e)
        if f >= 1.0 - 1e-9:
            return None
        # extra cost per t of need (EUR), charged per ha in proportion to each crop's need
        c_t = sum(S0_ * (sh[nm_] - s0_) + 0.5 * sl_ * (sh[nm_] - s0_) ** 2 for nm_, nm, S0_, sl_, s0_, smx in techs)
        nc = self.data.nutrient_coefs.copy()
        for c in crops:
            if c in nc.index and "N" in nc.columns:
                nc.at[c, "N"] = float(nc.at[c, "N"]) * f
            self._n_intensity[c] = self._n_intensity.get(c, 1.0) * f
            if c in self.net_revenues.index:
                need_t_ha = self._crop_mineral_rate(c) * (1.0 + e0) / 1000.0
                self.net_revenues[c] = float(self.net_revenues[c]) - c_t * need_t_ha
        # the same factor on the manure and residue credits (environmental module, "__credit__")
        self._n_intensity["__credit__"] = self._n_intensity.get("__credit__", 1.0) * f
        shares = {k: (v,) for k, v in sh.items()}
        self.data.nutrient_coefs = nc
        self._fert_tech_shares.update({k: v[0] for k, v in shares.items()})
        return self._n_intensity

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

    #: free land types of CAPRI's land market (artificial land held fixed)
    LAND_TYPES = ("ARAC", "GRAS", "FRUN", "FORE", "OLND")

    _FERT_ALLOC_CACHE = {}
    #: CAPRI's fertiliser allocation (manure replaces mineral N). OFF by default:
    #: on its own it makes herd cuts LESS effective per head (each head cut
    #: relieves only the unavailable share of its manure), so the N target needs
    #: more heads, as CAPRI's substitution implies; CAPRI's relief comes from
    #: the manure market that substitution enables. To be switched on together
    #: with the national manure pool (stage 2).
    use_fert_allocation = False
    #: national manure market through the allocation (stage 2); requires
    #: use_fert_allocation
    use_manure_pool = False
    #: CAPRI's crop nutrient balance terms for every EU solve (Sprint 9k): manure N per unit, crops' base
    #: mineral N per ha, base yields - set by SupplyModule before each solve (None outside the EU)
    _manure_ctx = None
    #: CAPRI's surplus per hectare of CURRENT farmland (vs base farmland)
    surplus_per_current_ha = False

    def _fert_params_raw(self):
        """(manure availability, mineral N price kEUR/t) without the allocation switch."""
        flag = getattr(self, "use_fert_allocation", False)
        try:
            self.use_fert_allocation = True
            return self._fert_alloc_params()
        finally:
            self.use_fert_allocation = flag

    def _fert_alloc_params(self):
        """(manure availability, mineral N price kEUR/t N) for this region, from
        CAPRI's reference allocation and its 2017 national UVAG of NITF."""
        if not getattr(self, "use_fert_allocation", False):
            return None, None
        reg = getattr(getattr(self, "data", None), "region_id", None)
        c = RegionalSupplyModel._FERT_ALLOC_CACHE
        if not c:
            from pathlib import Path as _P
            root = _P(__file__).resolve().parents[2] / "capri_data" / "2017"
            try:
                fs = pd.read_csv(root / "environment" / "fertiliser_substitution_2030.csv").set_index("region")
                c["av"] = fs["manure_availability"].to_dict()
            except Exception:
                c["av"] = {}
            try:
                fp = pd.read_csv(root / "supply" / "mineral_n_price.csv").set_index("country")
                c["pf"] = (fp["eur_per_t_n"] / 1000.0).to_dict()
            except Exception:
                c["pf"] = {}
        a = c["av"].get(reg)
        p = c["pf"].get(str(reg)[:2]) if reg else None
        a = float(a) if a is not None and a == a else None
        return a, (float(p) if p is not None else None)

    def _land_augment(self, A_ub, b_ub, c_lin, x0):
        """Augment the regional QP with CAPRI's land market (LandMarket_,
        trustee-land variant): land-type areas L as variables, cost 1/2 L'Q L
        (p_pmpQuadLandTypes) with constants making the base areas optimal; land
        rows become  activities - land <= base limit - base land, i.e. exactly
        the current rows at base; total land <= base total; grassland >= (1 -
        allowance) x base (CAPRI Green Deal default allowance 0%). Returns None
        where the region has no land-market data."""
        self._need_row = None
        self._nrow_land = None
        lm = getattr(self.data, "land_market", None)
        if not lm or "quad" not in lm:
            return None
        labels = list(getattr(self, "_row_labels", []))
        LTall = ["ARAC", "GRAS", "FRUN", "FORE", "OLND", "ARTIF"]
        keep = [LTall.index(t) for t in self.LAND_TYPES]
        Qf = np.array(lm["quad"], dtype=float)[np.ix_(keep, keep)]
        # UNITS: CAPRI's land-market terms are per HECTARE, the model's land
        # variables in 1000 ha - hence x 1000. Verified: with observed land
        # rents the matrix then implies an arable land-supply elasticity of
        # median 0.062 (10th 0.010, 90th 0.334), the range of CAPRI's priors;
        # unscaled it implied a median of 62 and land converted far too easily.
        Qf = 1000.0 * 0.5 * (Qf + Qf.T) + 1e-9 * np.eye(len(keep))
        L0 = np.array([float(lm["base_kha"].get(t, 0.0)) for t in self.LAND_TYPES])
        n, k = len(x0), len(keep)
        Qa = np.zeros((n + k, n + k)); Qa[:n, :n] = self.Q; Qa[n:, n:] = Qf
        ca = np.concatenate([c_lin, -Qf @ L0])
        Aa = np.hstack([A_ub, np.zeros((A_ub.shape[0], k))]); ba = b_ub.astype(float).copy()
        li = {t: j for j, t in enumerate(self.LAND_TYPES)}
        rowmap = {"arable_land": [(li["ARAC"], 1.0)],
                  # CAPRI LandBalNoSlak_(GRAS): grassland activities = grassland. Arable fodder
                  # (MAIF, OFOD) sits on ARABLE land, in the arable row; see _build_constraints
                  "grassland": ([(li["GRAS"], 1.0)] if getattr(type(self), "land_no_slack", False)
                                else [(li["GRAS"], 1.0), (li["ARAC"], 0.2)]),
                  "permanent_land": [(li["FRUN"], 1.0)]}
        rows = []
        for lab, coeffs in rowmap.items():
            if lab not in labels:
                continue
            i = labels.index(lab)
            const = float(b_ub[i]) - sum(cf * L0[j] for j, cf in coeffs)
            for j, cf in coeffs:
                Aa[i, n + j] -= cf
            ba[i] = const
            rows.append((i, coeffs, const))
        if not rows:
            return None
        # BASE SHADOW PRICES of the land rows, so the land market is in balance
        # at base WITH them (a land row binding at base otherwise makes extra
        # land look valuable and the base shifts). Recovered once, at the first
        # (baseline) call, from the ordinary QP's OWN solution x*: multipliers of
        # the rows and non-negativity bounds active at x*, by NNLS on
        # Q x* + c + A_act' mu - I_bnd' nu = 0. Estimating them at the base DATA
        # instead (not the solution) produced spurious prices - up to 163 kha of
        # base shift. If the ordinary QP fails, the land market is not used.
        mu0 = getattr(self, "_land_mu0", None)
        if mu0 is None:
            from scipy.optimize import nnls
            from capri_mod.supply.qp_solver import solve_qp
            xs, oks = solve_qp(self.Q, c_lin, A_ub, b_ub, x0=x0)
            if not oks:
                self._land_mu0 = {"__failed__": 1.0}
                return None
            tol = lambda v: 1e-7 * max(1.0, abs(float(v)))
            act = [i for i in range(A_ub.shape[0]) if A_ub[i] @ xs >= b_ub[i] - tol(b_ub[i])]
            bnd = [j for j in range(n) if xs[j] <= 1e-9]
            M = np.hstack([A_ub[act].T if act else np.zeros((n, 0)), -np.eye(n)[:, bnd]])
            g = -(self.Q @ xs + c_lin)
            mu0 = {}
            if M.shape[1]:
                sc = np.maximum(np.abs(M).max(axis=0), 1e-12)
                mu, rn = nnls(M / sc, g, maxiter=50 * M.shape[1])
                mu = mu / sc
                mu0 = {labels[i]: float(mu[jj]) for jj, i in enumerate(act) if i < len(labels)}
                mu0["__residual__"] = float(rn) / max(1.0, float(np.linalg.norm(g)))
            self._land_mu0 = mu0
        if "__failed__" in mu0:
            return None
        for lab, coeffs in rowmap.items():
            m_ = float(mu0.get(lab, 0.0))
            for j, cf in coeffs:
                ca[n + j] += m_ * cf
        # ---- SURPLUS PER HECTARE OF CURRENT LAND (CAPRI e_SURTOTHa, e_EXCRET:
        # divided by sum(landTypesNoSlak, v_actLevl)). With it, a region gains
        # nothing per hectare by giving up farmland, and expanding it costs land
        # (land market). Limit = target per ha x (ARAC + GRAS + FRUN), as a
        # deviation from base land - identical at base.
        if "N_balance" in labels and getattr(self, "surplus_per_current_ha", False):
            i_nb_ = labels.index("N_balance")
            base_area_ = float(sum(v for a_, v in self._base_levels().items() if a_ in CROPS))
            if base_area_ > 0:
                tgt_ = float(ba[i_nb_]) / base_area_
                lt_ = [t for t in ("ARAC", "GRAS", "FRUN") if t in li]
                for t in lt_:
                    Aa[i_nb_, n + li[t]] -= tgt_
                ba[i_nb_] -= tgt_ * float(sum(L0[li[t]] for t in lt_))
                # for a relaxed target (_relax_n_target): the land columns and base land
                self._nrow_land = ([n + li[t] for t in lt_], float(sum(L0[li[t]] for t in lt_)), tgt_)
        # ---- FERTILISER ALLOCATION (CAPRI supply_model.gms NUTNED_): manure
        # REPLACES mineral fertiliser. Mineral N becomes a variable M >= crop need
        # - availability x manure applied (>= 0). Crops' CURRENT mineral N is
        # base mineral N x fertiliser intensity x sqrt(current/base yield) - the
        # same terms the N row already applies (a first version used the BASE
        # amount and double-counted, turning crops into N sinks: pigs fell more,
        # not less). Crop need = current mineral N + manure-covered need (spread
        # by uptake, so the row returns exactly the base mineral N at base). The
        # N row takes M instead of crops' current mineral N; fertiliser is charged
        # on M at CAPRI's price (UVAG NITF) with the per-ha charge added back;
        # constants shift by the allocation row's base dual (= that price).
        k_extra = 0
        if "N_balance" in labels:
            srow = getattr(self, "_surplus_row", None)
            nmin = srow[2] if srow is not None and len(srow) > 3 else None
            upt = srow[3] if srow is not None and len(srow) > 3 else None
            ybase = srow[4] if srow is not None and len(srow) > 4 else None
            bser = srow[0] if srow is not None else None
            a_av, pf = self._fert_alloc_params()
            if nmin and upt and bser is not None and a_av and pf:
                i_nb = labels.index("N_balance")
                mint = getattr(self, "_n_intensity", {}) or {}
                ycur = self.data.yields
                xb = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                nm0 = np.array([float(nmin.get(a, 0.0)) if a in CROPS else 0.0 for a in self.acts])
                nmc = nm0.copy()
                for i, a in enumerate(self.acts):
                    if a in CROPS and nm0[i] > 0:
                        f_ = float(mint.get(a, 1.0))
                        if ybase is not None and hasattr(ybase, "get"):
                            y0 = float(ybase.get(a, 0.0)); yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                            if y0 > 0 and yc > 0:
                                f_ *= (yc / y0) ** 0.5
                        nmc[i] = nm0[i] * f_
                up = np.array([float(upt.get(a, 0.0)) if a in CROPS else 0.0 for a in self.acts])
                e = np.array([max(0.0, float(bser.get(a, 0.0))) if a in ANIMALS else 0.0 for a in self.acts])
                man0, w, m0 = float(e @ xb), float(up @ xb), float(nm0 @ xb)
                if w > 0 and m0 > 0:
                    u = a_av * man0 * up / w
                    cols = Aa.shape[1]
                    Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = 1e-9
                    Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                    Aa[i_nb, :n] -= nmc
                    Aa[i_nb, -1] = 1.0
                    req = np.zeros(cols + 1); req[:n] = nmc + u - a_av * e; req[-1] = -1.0
                    Aa = np.vstack([Aa, req]); ba = np.concatenate([ba, [1e-9 * max(1.0, m0)]])
                    ca = np.concatenate([ca, [pf]])
                    ca[:n] = ca[:n] - pf * (nmc + u) + pf * a_av * e
                    self._alloc_m0 = float(nmc @ np.maximum(x0, 0.0))
                    self._alloc_row = Aa.shape[0] - 1
                    k_extra = 1
                    # CAPRI's catch crops (NUTNED_ l. 1076, e_BIOFIX): their N is an input of the
                    # balance and supplies crop need, so mineral N may fall by as much
                    dbf = self._cover_n_increment()
                    if dbf > 0:
                        ba[i_nb] -= dbf
                        ba[self._alloc_row] += dbf
        alloc_k = k_extra
        self._alloc_cols = alloc_k
        self._pool_cols = []
        # ---- NATIONAL MANURE MARKET (CAPRI e_costMTrade, manuremarket/*). The
        # balance ALREADY makes manure replace mineral N linearly (availability
        # a, CAPRI fertiliser_substitution): the animals' row terms are about
        # (1 - a) x manure. Traded manure enters the same way: N row -(1 - a)
        # per t exported, +(1 - a) per t imported; objective: exporters pay the
        # pool price + the fertiliser they must now buy (a x p_f), importers
        # receive the pool price + the fertiliser they save. (A first version
        # used the full manure amount and no saving - pool prices of EUR
        # 58-98/kg; a second added a fertiliser allocation that counted
        # substitution twice.) Manure-application row +-1; CAPRI's quadratic
        # cost; exports <= manure produced. REGISTERED: (1 - a) also where
        # mineral N sits at its floor (strictly 1 there).
        # Sprint 9k: in EVERY EU solve with manure trade on (CAPRI: e_netMTrade, e_costMTrade are in every run), not
        # only under the N target; the N row takes the trade only where it exists. OBJECTIVE: the pool price alone
        # (+ the emission tax). CAPRI's cost constants are calibrated from the base duals (define_manure_trade_costs.gms
        # FINALIZE) so the base trade is optimal; with a fixed fertiliser price the fertiliser saved or bought per t
        # traded (sub x p_f) is part of what that calibration absorbs, and a deviation from the base trade is driven
        # by the change in manure's value (N target, crop-need row, tax) - the sub x p_f terms of the first version
        # made importers pay up to EUR 0.9/kg N at base and shifted every pool's price by the region's own sub x p_f.
        pool_k = 0
        _mc = self._mctx()
        if _mc is not None and getattr(self, "use_manure_pool", False):
            a_av, pf = self._fert_params_raw()
            man_d = _mc["man_d"]
            if a_av is not None and man_d is not None:
                i_nb = labels.index("N_balance") if "N_balance" in labels else None
                xb = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                e = np.array([float(man_d.get(a, 0.0)) for a in self.acts])
                man0 = float(e @ xb)
                # the balance's own substitution factor (availability / mineral
                # efficiency, not availability alone), and the FLOOR: where the
                # region's mineral N is already zero, manure cannot displace any
                # more of it - traded manure then counts in full and carries no
                # fertiliser cost or saving (West Flanders, Antwerp)
                sub = 0.0
                env_ = getattr(self, "_env_for_surplus", None)
                if env_ is not None:
                    try:
                        sub = float(env_._substitution(self.data.region_id)[0])
                        cur = {a: float(v) for a, v in zip(self.acts, np.maximum(x0, 0.0))}
                        nb_now = env_.compute_nitrogen_balance(cur, self.data.yields, self.data.region_id)
                        if float(nb_now.get("n_mineral_input", 1.0)) <= 1e-6:
                            sub = 0.0
                    except Exception as _exc:
                        import warnings as _w
                        _w.warn(f"manure market: substitution factor unavailable for "
                                f"{self.data.region_id} ({_exc!r}); using availability")
                        sub = float(a_av)
                if man0 > 1e-6:
                    pp = float(getattr(self, "manure_pool_price", 0.0) or 0.0)
                    slope = 0.05 / (man0 / 100.0)
                    i_ma = labels.index("manure_application") if "manure_application" in labels else None
                    # emission tax: the mineral N bought (export) or saved (import), sub x the accounts' soil N2O
                    # factor per t N (kt CO2-eq x EUR/t = 1000 EUR)
                    g_ = float(getattr(self, "ghg_tax", 0.0) or 0.0) * sub * self._ef_mineral_n2o() / 1000.0
                    pcols = []
                    for sign in (-1.0, +1.0):                  # -1 export, +1 import
                        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = slope
                        ca = np.concatenate([ca, [(pp + g_) if sign < 0 else (-pp - g_)]])
                        Aa = np.hstack([Aa, np.zeros((Aa.shape[0], 1))])
                        if i_nb is not None:
                            Aa[i_nb, -1] = sign * (1.0 - sub)
                        if i_ma is not None:
                            Aa[i_ma, -1] = sign
                        if "mineral_N" in labels:
                            # mineral N: exported manure must be replaced (+sub), imported manure displaces it
                            Aa[labels.index("mineral_N"), -1] = -sign * sub
                        pcols.append(Aa.shape[1] - 1)
                    capr = np.zeros(Aa.shape[1]); capr[:n] = -e; capr[pcols[0]] = 1.0
                    Aa = np.vstack([Aa, capr]); ba = np.concatenate([ba, [0.0]])
                    self._pool_cols = pcols
                    self._manure_supply0 = man0
                    self._pool_manure_vec = e.copy()
                    self._pool_avail = sub
                    pool_k = 2
        # ---- MANURE WITHIN CROP NEED (CAPRI supply_model.gms fertDistExcr_ +
        # NUTNED_, an EQUALITY with mineral N >= 0; its over-application term is
        # commented out): a region can hold only as much manure as its crops can
        # use at their availability. As a row: mineral N still required >= 0,
        #   sum crops (current need x area) - sub x (manure + imports - exports) >= 0.
        # Without it importers absorbed unlimited paid manure and cut crops to
        # make room (cereal area -31% in importing regions). Regions already
        # beyond it at base are held at their base deficit. REGISTERED: applied
        # where the N target applies (CAPRI: always).
        # Sprint 9k: in every EU solve (CAPRI's NUTNED_ is in every run), not only under the N target
        _mc = self._mctx()
        if _mc is not None:
            nmin, ybase, man_d = _mc.get("nmin"), _mc.get("ybase"), _mc.get("man_d")
            env_ = getattr(self, "_env_for_surplus", None)
            if nmin and man_d is not None and env_ is not None:
                try:
                    sub_n = float(env_._substitution(self.data.region_id)[0])
                except Exception as _exc:
                    import warnings as _w
                    _w.warn(f"crop-need limit skipped for {self.data.region_id}: {_exc!r}")
                    sub_n = None
                if sub_n:
                    mint = getattr(self, "_n_intensity", {}) or {}
                    ycur = self.data.yields
                    need = np.zeros(n)
                    for j, a in enumerate(self.acts):
                        if a in CROPS:
                            v = float(nmin.get(a, 0.0)) * float(mint.get(a, 1.0))
                            if ybase is not None and hasattr(ybase, "get"):
                                y0 = float(ybase.get(a, 0.0)); yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                                if y0 > 0 and yc > 0:
                                    v *= (yc / y0) ** 0.5
                            need[j] = v
                    man = np.array([float(man_d.get(a, 0.0)) for a in self.acts])
                    cap = np.zeros(Aa.shape[1]); cap[:n] = -need + sub_n * man
                    pc_ = getattr(self, "_pool_cols", []) or []
                    if len(pc_) == 2:
                        cap[pc_[0]] = -sub_n; cap[pc_[1]] = +sub_n
                    xb_ = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                    v0 = float(cap[:n] @ xb_)
                    Aa = np.vstack([Aa, cap]); ba = np.concatenate([ba, [max(0.0, v0) + 1e-9 * max(1.0, float(need @ xb_))
                                                                         - self._cover_n_increment()]])
                    self._need_row = Aa.shape[0] - 1
        k_extra = alloc_k + pool_k
        tot = np.zeros(n + k + k_extra); tot[n:n + k] = 1.0
        allow = float(getattr(self, "grassland_allowance", 0.0))
        grs = np.zeros(n + k + k_extra); grs[n + li["GRAS"]] = -1.0
        # TOTAL LAND IS CONSERVED (CAPRI's land-use balance: the land types add up to the region's
        # area). As an upper bound only, land leaving farming could vanish: under the nitrogen target
        # Brittany's land types fell from 2,328 to 1,495 kha, forest included. Now land leaving
        # farming goes to forest and other land, at the land market's own transformation costs.
        Aa = np.vstack([Aa, tot, -tot, grs])
        ba = np.concatenate([ba, [L0.sum() + 1e-9], [-L0.sum() + 1e-9 * max(1.0, L0.sum())],
                             [-(1.0 - allow) * L0[li["GRAS"]] + 1e-9]])
        # CAPRI LandBalNoSlak_ (supply_model.gms): for arable crops (ARAC), fruit and
        # nurseries (FRUN) and grassland (GRAS) the crops using a land type EQUAL the land
        # type's area - no idle land. Land leaves agriculture only through the land market
        # (its quadratic costs), never for free. As inequalities the rows let livestock
        # regions under the nitrogen target idle a third or more of their farmland (Ireland,
        # the Netherlands, Lombardy: -40 to -55%) against CAPRI's EU farmland +3%.
        # The equality holds at the BASE USE of each land type: the model's land data carry idle
        # land (availability above the crops' base area), which CAPRI's data do not, so the row
        # is  crops - land = base crops - base land,  i.e. a change in crops equals a change in
        # the land type. Holding it at the availability instead (an earlier version) forced the
        # base itself to fill or release idle land: the 2030 baseline never settled (land
        # updates of 0.004-0.006 for 25 iterations).
        if getattr(type(self), "land_no_slack", False):
            extra_r, extra_b = [], []
            xb_ = np.concatenate([np.maximum(np.asarray(x0, dtype=float), 0.0), L0])
            for i, coeffs, const in rows:
                scale = float(np.abs(Aa[i]).max()) if Aa[i].any() else 1.0
                # (never above the row's own limit: base crops exceed some regions' land data by
                # rounding, 0.002 kha in Brittany, and the pair of rows was then infeasible)
                used = min(float(Aa[i, :n + k] @ xb_), float(const))
                extra_r.append(-Aa[i].copy()); extra_b.append(-used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale)
            if extra_r:
                Aa = np.vstack([Aa] + extra_r); ba = np.concatenate([ba, extra_b])
        self._land_types_used = list(self.LAND_TYPES)
        start = np.concatenate([x0, L0] + ([np.array([getattr(self, "_alloc_m0", 0.0)])] if alloc_k else [])
                               + ([np.zeros(pool_k)] if pool_k else []))
        Qa, ca, Aa, ba, start = self._grass_intensity_column(Qa, ca, Aa, ba, start, labels, n, alloc_k)
        Qa, ca, Aa, ba, start = self._dairy_intensity_column(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._histosol_columns(Qa, ca, Aa, ba, start, labels, n)
        return Qa, ca, Aa, ba, start, rows

    #: CAPRI's two grassland activities (extensive GRAE, intensive GRAI) represented by the area
    #: moved from intensive to extensive grassland, z (docs/COUPLING_SPRINTS.md, Sprint 7a)
    use_grass_intensity = True

    def _grass_intensity_column(self, Qa, ca, Aa, ba, start, labels, n, alloc_k):
        """Append CAPRI's grassland-intensity choice as one column z (1000 ha moved from GRAI to
        GRAE; GRAE = s0 x GRAS + z, GRAI = (1 - s0) x GRAS - z, so z = 0 is the base split):
          - N balance row: the balance change of a hectare of GRAE over one of GRAI
            (EnvironmentalModule.grass_intensity_delta, the accounts' own function);
          - grass fodder rows: production changes by u x (yield_ext - yield_int) / mean yield;
          - crop-need limit (manure within need): the mineral-rate change;
          - 0 <= GRAE, GRAI: -z - s0 GRAS <= 0, z - (1 - s0) GRAS <= 0;
          - PMP: (q_ext + q_int) z^2 / 2 (CAPRI's p_pmpQuadTechn of GRAE and GRAI), linear term
            from the base duals of the rows z enters, so z = 0 is optimal at base (as CAPRI's
            PMP calibration makes the base split optimal)."""
        self._grass_col = None
        if not getattr(type(self), "use_grass_intensity", False) or "GRAS" not in self.acts or alloc_k:
            return Qa, ca, Aa, ba, start
        gi = getattr(self.data, "grass_intensity", None)
        env_ = getattr(self, "_env_for_surplus", None)
        if gi is None or env_ is None or not hasattr(gi, "get") or not (gi.get("q_ext", 0) > 0):
            return Qa, ca, Aa, ba, start
        dl = env_.grass_intensity_delta(self.data.region_id)
        if not dl:
            return Qa, ca, Aa, ba, start
        jg = list(self.acts).index("GRAS")
        s0 = float(gi["share_ext"]); dy = float(gi["yield_ext_rel"]) - float(gi["yield_int_rel"])
        col = np.zeros(Aa.shape[0])
        if "N_balance" in labels:
            col[labels.index("N_balance")] = float(dl.get("n_surplus", 0.0))
        for i, lab in enumerate(labels):
            if lab.startswith("fodder_") and i < Aa.shape[0] and Aa[i, jg] != 0.0:
                # GRAS's own coefficient is -u (row) or +u (band); production change u x dy per ha
                col[i] = Aa[i, jg] * dy
        nr = getattr(self, "_need_row", None)
        if nr is not None and nr < Aa.shape[0]:
            col[nr] = -float(dl.get("mineral_rate", 0.0))
        # LINEAR TERM: calibrated so that z = 0 is optimal in the base problem (CAPRI's PMP
        # calibration makes the base split of GRAE and GRAI optimal): c_z = - sum_i mu_i A_iz with
        # mu the duals of the rows z enters, from the region's first (baseline) solve, which is
        # made WITHOUT the column. Later solves carry the column with the stored term.
        cz = getattr(self, "_grass_cz", None)
        if cz is None:
            self._grass_pending_col = col
            self._grass_col = None
            return Qa, ca, Aa, ba, start
        self._grass_pending_col = None
        Aa = np.hstack([Aa, col[:, None]])
        lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[jg] = -s0
        hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[jg] = -(1.0 - s0)
        Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
        qz = float(gi["q_ext"]) + float(gi["q_int"])
        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = qz
        ca = np.concatenate([ca, [cz + self._ghg_cost('grass')]])
        start = np.concatenate([start, [0.0]])
        self._grass_col = Aa.shape[1] - 1
        return Qa, ca, Aa, ba, start

    use_dairy_intensity = True

    def _dairy_intensity_column(self, Qa, ca, Aa, ba, start, labels, n):
        """CAPRI's two-intensity cattle activities: dairy cows (DCOL/DCOH, Sprint 7b), then fattening
        bulls (BULL/BULH) and heifers (HEIL/HEIH) (Sprint 7c)."""
        Qa, ca, Aa, ba, start = self._dairy_column_only(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._cattle_columns(Qa, ca, Aa, ba, start, labels, n)
        return self._genetics_columns(Qa, ca, Aa, ba, start, labels, n)

    def _split_pending(self) -> bool:
        return (getattr(self, "_dairy_pending", None) is not None or bool(getattr(self, "_cattle_pending", None))
                or bool(getattr(self, "_genet_pending", None)))

    def _split_record(self, y) -> None:
        """z of the dairy, bull and heifer splits from a solution vector."""
        _dc = getattr(self, "_dairy_col", None)
        self._last_dairy_z = float(y[_dc]) if _dc is not None and _dc < len(y) else 0.0
        self._last_cattle_z = {a: float(y[c]) for a, c in (getattr(self, "_cattle_cols", None) or {}).items() if c < len(y)}
        self._last_genet_z = {k: max(0.0, float(y[c])) for k, c in (getattr(self, "_genet_cols", None) or {}).items() if c < len(y)}

    #: CAPRI's low/high-intensity fattening bulls and heifers (Sprint 7c, tools/build_cattle_intensity.py)
    use_cattle_intensity = True

    def _cattle_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """One column z per fattening animal (BULL: CAPRI's BULL/BULH; HFRS: HEIL/HEIH), 1000 stalls
        moved from the high- to the low-intensity activity, as the dairy split: manure-driven rows x
        (MANN per stall, low - high) / average; the feed block's requirement rows (feeding inside);
        bounds low = s_low X + z >= 0, high = s_high X - z >= 0; PMP from CAPRI's own terms (q_z);
        linear term from the base duals, plus the CHANGES under the scenario: beef revenue (beef per
        stall, low - high) and the young animals bought (one per animal fattened: a short cycle
        turns over more animals per stall) at the young-animal price change."""
        self._cattle_cols = {}
        tab = getattr(self.data, "cattle_intensity", None)
        if not getattr(type(self), "use_cattle_intensity", False) or not tab \
                or not getattr(type(self), "use_feed_in_supply", False):
            return Qa, ca, Aa, ba, start
        cz_all = getattr(self, "_cattle_cz", None) or {}
        pending = {}
        rows_ = [labels.index(l) for l in ("N_balance", "manure_application") if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        yr = getattr(self, "yani_price_ratio", None) or {}
        ycoef = self._young_animal_coefs() if yr else {}
        for a, di in tab.items():
            if a not in self.acts:
                continue
            r = (getattr(self, "feed_rations", None) or {}).get(a)
            if r is None or not (float(di.get("q_z", 0) or 0) > 0):
                continue
            j = list(self.acts).index(a)
            col = np.zeros(Aa.shape[0])
            for i in rows_:
                col[i] = float(Aa[i, j]) * float(di["dmann_rel"])
            req = {"E": float(r.E) * float(di["denne_rel"]), "P": float(r.P) * float(di["dcrpr_rel"]),
                   "DMIN": float(r.DMIN) * float(di["ddrmn_rel"])}
            if np.isfinite(float(r.DMAX)):
                req["DMAX"] = float(r.DMAX) * float(di["ddrmx_rel"])
            if a not in cz_all:
                pending[a] = (col, req)
                continue
            Aa = np.hstack([Aa, col[:, None]])
            lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[j] = -float(di["share_low"])
            hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(di["share_high"])
            Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
            Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(di["q_z"])
            dv = 0.0
            if ps is not None and pv is not None and hasattr(pv, "get"):
                bv = pv.get(f"{a}.BEEF")
                if bv is not None and pd.notna(bv):
                    dv += float(di["dbeef_rel"]) * float(bv) * float(ps.get("BEEF", ps.get(a, 0.0)) or 0.0)
            for g, rec in ycoef.items():                          # young animals bought per stall
                u = float(rec.get("use", {}).get(a, 0.0) or 0.0)
                if u:
                    dv -= float(di["dyoung_rel"]) * u * float(rec.get("value_eur_head", 0.0) or 0.0) * (float(yr.get(g, 1.0)) - 1.0)
            ca = np.concatenate([ca, [cz_all[a] - dv + self._ghg_cost('cattle', a)]])
            start = np.concatenate([start, [0.0]])
            self._cattle_cols[a] = Aa.shape[1] - 1
            rx = dict(getattr(self, "_dairy_req_extra", None) or {})
            rx[a] = list(rx.get(a, [])) + [(Aa.shape[1] - 1, req)]
            self._dairy_req_extra = rx
        self._cattle_pending = pending or None
        return Qa, ca, Aa, ba, start

    def _cattle_calibrate_from_duals(self, duals):
        pend = getattr(self, "_cattle_pending", None)
        if not pend:
            return
        rd = getattr(self, "_last_req_duals", None) or {}
        cz = dict(getattr(self, "_cattle_cz", None) or {})
        if duals is not None and rd:
            sgn = {"DMAX": -1.0}
            for a, (col, req) in pend.items():
                if len(duals) >= len(col):
                    cz[a] = -(float(np.asarray(duals[:len(col)], float) @ col)
                              + sum(float(rd.get((a, lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._cattle_cz = cz
        self._cattle_pending = None

    #: CAPRI's cattle genomics (envind/breeding.gms): higher milk yield (dairy cows) and lower energy need
    #: (non-dairy ruminants), adopted inside the supply model (docs/MITIGATION_IN_SUPPLY.md)
    use_genetics = True

    def _genetics_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """One column g per region, animal and option (1000 heads adopting), CAPRI's breeding options and its
        low-nitrogen feeding (lowNFeed, Sprint 9g):
          - manure-driven rows (N balance, manure application, crop-need limit, mineral-N allocation):
            the animal's own coefficient x d_mann_rel;
          - the animal's requirement rows in the feed block: requirement x d_ener / d_crpr / d_drmn / d_drmx
            (feeding inside only);
          - 0 <= g <= eligible share x the animal's level (CAPRI MaxShare 1, IniShare 0);
          - cost (CAPRI GHG_Mit_Cost_ with breeding.gms's / low_n_feed.gms's calibration): linear term from the
            base duals plus relSubs0 x costParLin, so the option is not adopted at base (CAPRI: s = 0 optimal with a
            subsidy of relSubs0 x cost); quadratic gamma = max(floor c, c (relSubs1 - relSubs0)) per unit of the
            share (floor 0.2 breeding, 0.05 low-N feed), i.e. gamma / eligible heads at base per head adopting (CAPRI subtracts the drop of the option's marginal value
            between its ini and max calibration runs; here that drop is the supply model's own curvature,
            so it is not subtracted twice: REGISTERED);
          - milk revenue of the extra milk under the current milk price change (genet_yld)."""
        self._genet_cols = {}
        tab = getattr(self.data, "genetics_effects", None)
        if not getattr(type(self), "use_genetics", False) or not tab \
                or not getattr(type(self), "use_feed_in_supply", False):
            return Qa, ca, Aa, ba, start
        cal = getattr(self, "_genet_cz", None) or {}
        pend = {}
        rows_ = [labels.index(l) for l in ("N_balance", "manure_application") if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        base = self._base_levels()
        # the options' rows as plain dicts, once per table (Series lookups here were a visible share of each solve)
        _gm = self.__dict__.get("_genet_rows_memo")
        if _gm is None or _gm[0] is not tab:
            _gm = (tab, {k: (v.to_dict() if hasattr(v, "to_dict") else dict(v)) for k, v in tab.items()})
            self._genet_rows_memo = _gm
        for (a, opt), e in _gm[1].items():
            if a not in self.acts:
                continue
            r = (getattr(self, "feed_rations", None) or {}).get(a)
            L0 = float(base.get(a, 0.0) or 0.0)
            c = float(e.get("cost_eur_head", 0.0) or 0.0)
            if r is None or L0 <= 1e-6 or c <= 0 or not (float(e.get("elig_share", 0.0) or 0.0) > 0):
                continue
            j = list(self.acts).index(a)
            col = np.zeros(Aa.shape[0])
            for i in rows_:
                col[i] = float(Aa[i, j]) * float(e["d_mann_rel"])
            req = {"E": float(r.E) * float(e["d_ener_rel"]), "P": float(r.P) * float(e["d_crpr_rel"])}
            if float(e.get("d_drmn_rel", 0.0) or 0.0):
                req["DMIN"] = float(r.DMIN) * float(e["d_drmn_rel"])
            if float(e.get("d_drmx_rel", 0.0) or 0.0) and np.isfinite(float(r.DMAX)):
                req["DMAX"] = float(r.DMAX) * float(e["d_drmx_rel"])
            if (a, opt) not in cal:
                pend[(a, opt)] = (col, req)
                continue
            r0, r1 = float(e["relsubs0"]), float(e["relsubs1"])
            # pmpParsqr = max(floor x c, c (relSubs1 - relSubs0)) per unit of the share of the eligible heads
            # (breeding.gms floor 0.2; low_n_feed.gms 0.05); per head adopting: / (eligible heads at base)
            gf = float(e["gamma_floor"]) if ("gamma_floor" in e and pd.notna(e["gamma_floor"])) else 0.2
            gamma = max(gf * c, c * (r1 - r0))
            el_ = max(float(e["elig_share"]), 1e-6)
            Aa = np.hstack([Aa, col[:, None]])
            lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0
            hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(e["elig_share"])
            Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
            Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = gamma / (L0 * el_)
            dv = 0.0
            dmr = float(e.get("d_milk_rel", 0.0) or 0.0)
            if dmr and ps is not None and pv is not None and hasattr(pv, "get"):
                mv = pv.get(f"{a}.MILK")
                if mv is not None and pd.notna(mv):
                    dv = dmr * float(mv) * float(ps.get("MILK", ps.get(a, 0.0)) or 0.0)
            ca = np.concatenate([ca, [cal[(a, opt)] + r0 * c - dv + self._ghg_cost('genet', (a, opt))]])
            start = np.concatenate([start, [0.0]])
            self._genet_cols[(a, opt)] = Aa.shape[1] - 1
            rx = dict(getattr(self, "_dairy_req_extra", None) or {})
            rx[a] = list(rx.get(a, [])) + [(Aa.shape[1] - 1, req)]
            self._dairy_req_extra = rx
        self._genet_pending = pend or None
        return Qa, ca, Aa, ba, start

    def _genetics_calibrate_from_duals(self, duals):
        """c_g = - (sum_i mu_i A_ig + the animal's requirement duals x the requirement changes) at base."""
        pend = getattr(self, "_genet_pending", None)
        if not pend:
            return
        rd = getattr(self, "_last_req_duals", None) or {}
        cz = dict(getattr(self, "_genet_cz", None) or {})
        if duals is not None and rd:
            sgn = {"DMAX": -1.0}
            for (a, opt), (col, req) in pend.items():
                if len(duals) >= len(col):
                    cz[(a, opt)] = -(float(np.asarray(duals[:len(col)], float) @ col)
                                     + sum(float(rd.get((a, lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._genet_cz = cz
        self._genet_pending = None

    def _dairy_column_only(self, Qa, ca, Aa, ba, start, labels, n):
        """Append CAPRI's dairy split as one column z (1000 heads moved from DCOH to DCOL; DCOL =
        s0 x DCOW + z, DCOH = (1 - s0) x DCOW - z, so z = 0 is the base split), Sprint 7b:
          - rows driven by manure N (N balance, manure application, crop-need limit, mineral-N
            allocation): DCOW's own coefficient x (MANN_DCOL - MANN_DCOH) / MANN_DCOW;
          - the cows' requirement rows in the conic feed block (energy, protein, dry-matter
            limits): DCOW's requirement x the relative change (req_extra; feeding inside only);
          - 0 <= DCOL, DCOH; PMP (q_DCOL + q_DCOH) z^2 / 2 (CAPRI's p_pmpQuadTechn);
          - linear term from the base duals (z = 0 optimal at base), plus the milk revenue change
            under the current milk price (milk per head (COMI_DCOL - COMI_DCOH) / COMI_DCOW).
        Calves, cull-cow beef and replacements are the same for both activities (CAPRI res_17)."""
        self._dairy_col = None
        self._dairy_req_extra = None
        if not getattr(type(self), "use_dairy_intensity", False) or "DCOW" not in self.acts:
            return Qa, ca, Aa, ba, start
        di = getattr(self.data, "dairy_intensity", None)
        r = (getattr(self, "feed_rations", None) or {}).get("DCOW")
        if di is None or r is None or not getattr(type(self), "use_feed_in_supply", False) \
                or not hasattr(di, "get") or not (float(di.get("q_low", 0) or 0) > 0):
            return Qa, ca, Aa, ba, start
        jd = list(self.acts).index("DCOW")
        s0 = float(di["share_low"]); dm = float(di["dmann_rel"])
        col = np.zeros(Aa.shape[0])
        rows_ = [labels.index(l) for l in ("N_balance", "manure_application") if l in labels]
        for extra in ("_need_row", "_alloc_row"):
            k = getattr(self, extra, None)
            if k is not None and k < Aa.shape[0] and k not in rows_ and (extra != "_alloc_row" or getattr(self, "_alloc_cols", 0)):
                rows_.append(k)
        for i in rows_:
            col[i] = float(Aa[i, jd]) * dm
        req = {"E": float(r.E) * float(di["denne_rel"]), "P": float(r.P) * float(di["dcrpr_rel"]),
               "DMIN": float(r.DMIN) * float(di["ddrmn_rel"])}
        if np.isfinite(float(r.DMAX)):
            req["DMAX"] = float(r.DMAX) * float(di["ddrmx_rel"])
        cz = getattr(self, "_dairy_cz", None)
        if cz is None:
            self._dairy_pending = (col, req)
            return Qa, ca, Aa, ba, start
        self._dairy_pending = None
        Aa = np.hstack([Aa, col[:, None]])
        lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[jd] = -s0
        hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[jd] = -(1.0 - s0)
        Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(di["q_low"]) + float(di["q_high"])
        # milk revenue of the change under the current milk price (EUR per head = 1000 EUR per 1000 heads)
        ps = getattr(self, "_price_shock_now", None)
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        dmilk = 0.0
        if ps is not None and pv is not None and hasattr(pv, "get"):
            mv = pv.get("DCOW.MILK")
            if mv is not None and pd.notna(mv):
                dmilk = float(di["dcomi_rel"]) * float(mv) * float(ps.get("MILK", ps.get("DCOW", 0.0)) or 0.0)
        ca = np.concatenate([ca, [cz - dmilk + self._ghg_cost('dairy')]])
        start = np.concatenate([start, [0.0]])
        self._dairy_col = Aa.shape[1] - 1
        self._dairy_req_extra = {"DCOW": [(self._dairy_col, req)]}
        return Qa, ca, Aa, ba, start

    use_histosol_fallow = True
    HISTOSOL_CLASSES = (("crop", "arable_land"), ("grass", "grassland"))

    # ------------------------------------------------------------------------------------------
    # CAPRI's emission tax (ghgTax, Sprint 9i; capri_mod/supply/ghg_tax.py): EUR per t CO2-eq times each
    # column's emission per unit at the baseline; set by CAPRIModel (ghg_tax, ghg_coef) for EU regions
    # ------------------------------------------------------------------------------------------
    def _ghg_cost(self, kind, key=None) -> float:
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co:
            return 0.0
        v = co.get(kind)
        if key is not None:
            v = (v or {}).get(key, 0.0)
        return tax * float(v or 0.0)

    def _apply_ghg_tax(self) -> None:
        """Activities: net revenue - tax x emission per ha or head (CAPRI's objective term)."""
        # net revenues not rebuilt since the last application (same object): take that one back first
        prev = getattr(self, "_ghg_applied", None)
        if prev and getattr(self, "_ghg_nr_obj", None) is self.net_revenues:
            for a, d in prev.items():
                self.net_revenues[a] = float(self.net_revenues[a]) + d
        self._ghg_applied = {}
        self._ghg_nr_obj = self.net_revenues
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co:
            return
        for a, e in (co.get("act") or {}).items():
            if a in self.net_revenues.index:
                d = tax * float(e)
                self.net_revenues[a] = float(self.net_revenues[a]) - d
                self._ghg_applied[a] = d

    def _ghg_feed_cost(self):
        """Flexible feeds: tax x emission per t fed, in the conic objective's EUR/kg units ({(animal, feed)})."""
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        co = getattr(self, "ghg_coef", None)
        if tax <= 0 or not co or not co.get("feed"):
            return None
        return {k: tax * float(e) / 1000.0 for k, e in co["feed"].items()}

    def _histosol_base_area(self, cls):
        base = self._base_levels()
        if cls == "crop":
            return float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c != "GRAS" and c in base.index))
        return float(base.get("GRAS", 0.0) or 0.0)

    def _histosol_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """CAPRI's histosol fallowing (no_histosols.gms, idleHisto_), one column per class: F = 1000 ha of
        histosol cropland (iHisCr) or grassland (iHisGr) idled. It still occupies its land (arable or
        grassland row +1); 0 <= F <= MaxShare x share x base area of the class (base area fixed:
        REGISTERED); cost CAPRI's curvature 0.5 pmpParSqr F^2 / H per ha of histosol area H; linear term
        from the base dual of the land row (F = 0 optimal at base, CAPRI's IniShare 0), so fallowing
        rises where the land rent falls - CAPRI's calibration does the same with its own rent in
        costsaving0. Its N2O (and CO2, CH4) on the idled area stop (QEmitt = 1 - p_ghgTechHisto = 0)."""
        self._hist_cols = {}
        h = getattr(self.data, "histosol", None)
        if not getattr(type(self), "use_histosol_fallow", False) or h is None or not hasattr(h, "get"):
            return Qa, ca, Aa, ba, start
        cal = getattr(self, "_hist_cal", None)
        pend = {}
        for cls, row_lab in self.HISTOSOL_CLASSES:
            sqr, sh, mx = h.get(f"pmp_sqr_{cls}"), float(h.get(f"share_{cls}", 0.0) or 0.0), h.get(f"maxshare_{cls}")
            if row_lab not in labels or sqr is None or pd.isna(sqr) or not (float(sqr) > 0) or sh <= 0 or mx is None or pd.isna(mx):
                continue
            H = sh * self._histosol_base_area(cls)
            if H <= 1e-6:
                continue
            col = np.zeros(Aa.shape[0]); col[labels.index(row_lab)] = 1.0
            if cal is None or cls not in cal:
                pend[cls] = col
                continue
            Aa = np.hstack([Aa, col[:, None]])
            up = np.zeros(Aa.shape[1]); up[-1] = 1.0
            Aa = np.vstack([Aa, up]); ba = np.concatenate([ba, [float(mx) * H]])
            Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(sqr) / H
            ca = np.concatenate([ca, [cal[cls] + self._ghg_cost('hist', cls)]])
            start = np.concatenate([start, [0.0]])
            self._hist_cols[cls] = Aa.shape[1] - 1
        self._hist_pending = pend or None
        return Qa, ca, Aa, ba, start

    def _histosol_calibrate_from_duals(self, duals):
        pend = getattr(self, "_hist_pending", None)
        if not pend:
            return
        cal = dict(getattr(self, "_hist_cal", None) or {})
        if duals is not None:
            for cls, col in pend.items():
                if len(duals) >= len(col):
                    cal[cls] = -float(np.asarray(duals[:len(col)], float) @ col)
        self._hist_cal = cal
        self._hist_pending = None

    def _dairy_calibrate_from_duals(self, duals):
        """After the first (baseline) solve without the column: c_z = - (sum_i mu_i A_iz + sum over the
        cows' requirement rows of their dual x the requirement change)."""
        self._cattle_calibrate_from_duals(duals)
        self._genetics_calibrate_from_duals(duals)
        pend = getattr(self, "_dairy_pending", None)
        if pend is None:
            return
        col, req = pend
        rd = getattr(self, "_last_req_duals", None) or {}
        if duals is not None and len(duals) >= len(col) and rd:
            sgn = {"DMAX": -1.0}
            self._dairy_cz = -(float(np.asarray(duals[:len(col)], float) @ col)
                               + sum(float(rd.get(("DCOW", lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._dairy_pending = None

    def _grass_calibrate_from_duals(self, duals):
        """After the first (baseline) solve without the column: c_z = - sum_i mu_i A_iz."""
        col = getattr(self, "_grass_pending_col", None)
        if col is None:
            return
        if duals is not None and len(duals) >= len(col):
            self._grass_cz = -float(np.asarray(duals[:len(col)], float) @ col)
        self._grass_pending_col = None

    def _fodder_rows(self):
        """CAPRI-consistent fodder balance rows (non-tradable fodder, SUPBAL_):
        sum_animals use_t_head x heads - u x area_crop <= 0, exact at base.
        Returns [(row, base value EUR/t, rhs, label)]."""
        fb = getattr(self.data, "fodder_balance", None) or {}
        acts_idx = {a: i for i, a in enumerate(self.acts)}
        x0 = self._base_levels().reindex(self.acts).fillna(0.0).values
        out = []
        for feed, rec in fb.items():
            crop = rec.get("crop")
            if crop not in acts_idx:
                continue
            row = np.zeros(len(self.acts))
            _rs = getattr(self, "ration_state", None) or {}
            for a, t in rec.get("use_t_head", {}).items():
                if a in acts_idx:
                    xr = (_rs.get(a) or {}).get("x", {})
                    row[acts_idx[a]] = float(xr[feed]) / 1000.0 if feed in xr else float(t)
            if not row.any():
                continue
            row[acts_idx[crop]] = -float(rec["u_t_per_ha"])
            scale = float(np.abs(row) @ np.abs(x0)) or 1.0
            rhs = max(0.0, float(row @ x0)) + 1e-9 * scale      # exact at base
            out.append((row, float(rec.get("value_eur_t", 0.0)), rhs, "fodder_" + feed))
        return out

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
        self._fall_floor = 0.0          # CAPRI data(ru,"FALL","FLOOR"), set by the landscape rule below
        # one label per row, appended with it, so a shadow price is always
        # reported under the constraint it belongs to
        self._row_labels = []

        # 1. Arable land constraint
        #
        # Every activity that occupies ARABLE land must be in this row, including
        # fodder on arable land (MAIF, OFOD) and fallow / set-aside (SETA). All
        # three used to be left out, with two consequences:
        #   - the right-hand side (arable land) counted the fodder area while the
        #     sum did not, so the row carried ~14 Mha of built-in slack and could
        #     never bind: the arable shadow price was zero in every region;
        #   - a landscape-feature floor on SETA grew set-aside out of nothing,
        #     without displacing a single crop. In CAPRI fallow competes for
        #     arable land, which is where its -9% cereal-area effect under
        #     Farm-to-Fork comes from; here cereals kept their land and fell only
        #     9.8% against CAPRI's 15%, with the cereal price already matching.
        row_arable = np.zeros(n)
        # One classification for both rows, the same one the land data is built
        # with (tools/build_capri_base.py PERMANENT_CROPS): tobacco, cotton and
        # other fibre are ANNUAL crops on arable land. They used to sit in the
        # permanent row while the land data counted them as arable, so each row
        # was measured against land built on a different definition.
        arable_crops = [a for a in CROPS
                        if a not in ("GRAS",) + self.PERMANENT_LAND_CROPS]
        for a in arable_crops:
            if a in acts_idx:
                row_arable[acts_idx[a]] = 1.0
        A_rows.append(row_arable)
        self._row_labels.append("arable_land")
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
        # arable land INCLUDING fallow, now that SETA is in the row
        _land_arable = (float(self.data.land.get("ARABLE", 200.0))
                        + float(self.data.land.get("FALLOW", 0.0) or 0.0))
        arable_avail = max(_land_arable, arable_base) * (1.0 + getattr(self, "_land_expansion", 0.0))
        b_rows.append(arable_avail)

        # 1b. Landscape-elements floor: at least `set_aside_requirement` of UAA
        # held as the non-productive activity. Expressed as -x_SETA <= -target
        # so it fits the upper-bound form. A negative requirement (a scenario
        # REMOVING an existing obligation) is skipped rather than inverted into
        # a nonsensical ceiling.
        if set_aside_requirement and set_aside_requirement > 0 and "SETA" in acts_idx:
            uaa_total = (self.data.land.get("ARABLE", 200.0)
                         + self.data.land.get("PERMANENT", 30.0)
                         + self.data.land.get("GRASSLAND", 80.0)
                         + (self.data.land.get("FALLOW", 0.0) or 0.0))
            _pp = getattr(self.data, "landscape_target_pp", None)
            if _pp is not None:
                # CAPRI's own rule (pol_input/greendeal/landscape.gms):
                #   FALL.FLOOR = lndscpTarg/10 * p_setAsideTarget * UAAR + SETF
                # p_setAsideTarget is the member state's MISSING share - points
                # of UAA still needed to reach 10%, net of fallow and of the
                # landscape elements LUCAS already records - and the existing
                # set-aside is added on top. A member state with no entry is
                # already at the target. The requested share scales the
                # ambition exactly as CAPRI's lndscpTarg does (10% = full).
                _seta0 = float(self._base_levels().get("SETA", 0.0))
                floor = (set_aside_requirement / 0.10) * (_pp / 100.0) * uaa_total + _seta0
            else:
                floor = set_aside_requirement * uaa_total
            self._fall_floor = float(floor)
            row_seta = np.zeros(n)
            row_seta[acts_idx["SETA"]] = -1.0
            A_rows.append(row_seta)
            self._row_labels.append("landscape_floor")
            b_rows.append(-floor)

        # 2. Permanent crops land constraint
        row_perm = np.zeros(n)
        perm_crops = list(self.PERMANENT_LAND_CROPS)
        for a in perm_crops:
            if a in acts_idx:
                row_perm[acts_idx[a]] = 1.0
        A_rows.append(row_perm)
        self._row_labels.append("permanent_land")
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
        # Under CAPRI's land rules (LandBalNoSlak_) the row is CAPRI's grassland balance: the
        # grassland activity (CAPRI's GRAE + GRAI) equals the grassland area. Maize and other
        # fodder are ARABLE crops (CAPRI MAIF, OFAR, ROOF) and are already in the arable row. The
        # row below - fodder on grassland plus a fifth of arable land - is the model's own soft
        # limit; held as an equality it fixed arable fodder at its base area plus a fifth of any
        # arable change, so regions under the N target could not replace fertilised fodder leys
        # (Ostra Mellansverige: 69 kha at 49 kg N/ha surplus, unchanged at an N price of
        # EUR 332/kg) and had to keep the cattle eating them.
        if getattr(type(self), "land_no_slack", False):
            grass_acts = ["GRAS"]
        for a in grass_acts:
            if a in acts_idx:
                row_grass[acts_idx[a]] = 1.0
        A_rows.append(row_grass)
        self._row_labels.append("grassland")
        # RHS must admit the calibrated base fodder area. The land-availability
        # GRASSLAND figure and the sum of fodder-activity base areas come from
        # different CAPRI symbols and do not always reconcile (at DE21 the base
        # fodder area is 454 against a grassland figure of 167), so a RHS built
        # only from the land figure is violated at base and forces livestock
        # down. Take the larger of the land-based limit and the actual base
        # fodder area plus expansion headroom.
        grass_land_limit = (self.data.land.get("GRASSLAND", 80.0) +
                            (0.0 if grass_acts == ["GRAS"] else self.data.land.get("ARABLE", 200.0) * 0.20))
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
        self._row_labels.append("N_limit")
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
        # REPLACED where CAPRI-consistent data exist: the hard fodder balance
        # (docs/FODDER_BALANCE.md) - fodder is non-tradable in CAPRI. The loose
        # 'buy-in' version below remains only as a fallback; it needed generous
        # headroom because its old per-unit coefficients were inconsistent.
        fodder_rows = self._fodder_rows()
        x0b = self._base_levels().reindex(self.acts).fillna(0.0).values
        for row, _lam, rhs, lab in fodder_rows:
            A_rows.append(row)
            self._row_labels.append(lab)
            b_rows.append(rhs)
            # CAPRI's SUPBAL_ for non-tradable fodder is an EQUALITY (production
            # net of losses = use). The solver takes inequalities only, so the
            # other side is a narrow band: production may exceed use by at most
            # 0.1% of base use. Slack at base (the base cannot move); the two rows
            # never bind together, so no degenerate working set.
            use0 = float(np.clip(row, 0.0, None) @ x0b)
            if not getattr(self, "fodder_band", True):
                continue
            A_rows.append(-row)
            self._row_labels.append(lab + "_band")
            b_rows.append(-(rhs - 1e-9 * max(1.0, use0)) + 1e-3 * max(1.0, use0))
        feed_req = self.data.feed_requirements
        if not feed_req.empty and not fodder_rows:
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
                self._row_labels.append("feed")
                b_rows.append(rhs)

        # Gross nitrogen balance (JRC121368's binding GNB restriction): surplus per
        # ha of farmland <= the tiered target, i.e.
        #   sum_a (s_a - target * [a is a crop]) * x_a <= 0
        # with s_a each activity's own contribution to the balance.
        srow = getattr(self, "_surplus_row", None)
        if srow is not None:
            coefs, target = srow[0], srow[1]
            nmin = srow[2] if len(srow) > 2 else {}
            upt = srow[3] if len(srow) > 3 else {}
            ybase = srow[4] if len(srow) > 4 else None
            mint = getattr(self, "_n_intensity", {}) or {}
            ycur = self.data.yields
            row_B = np.zeros(n)
            self._mineral_row = {}
            _env_now = getattr(self, "_env_for_surplus", None)
            for i, a in enumerate(self.acts):
                sa = float(coefs.get(a, 0.0))
                if not self._techs_inside():
                    sa -= float((getattr(self, "_animal_n_relief", None) or {}).get(a, 0.0))   # manure technologies
                sa -= float((getattr(self, "_manure_ni_relief", None) or {}).get(a, 0.0))      # inhibitors on manure
                sa += self._nitrate_row_term(a)                                             # nitrate N excretion
                _exact = None
                _fcr = float(mint.get("__credit__", 1.0))
                if _env_now is not None and (a in CROPS or _fcr != 1.0):
                    try:
                        _mi = {"__credit__": _fcr}
                        if a in mint:
                            _mi[a] = float(mint[a])
                        _exact = float(_env_now.unit_nitrogen_balance(
                            a, ycur, self.data.region_id, _mi)["n_surplus"])
                    except Exception:
                        _exact = None
                if _exact is not None and a not in CROPS:
                    sa += _exact - float(coefs.get(a, 0.0))     # manure credit at the technology factor
                    _exact = None
                if _exact is not None:
                    # THE CROP'S OWN BALANCE AT THIS SOLVE'S YIELDS AND FERTILISER INTENSITY,
                    # from the same function as the reported accounts (it is linear in
                    # activity levels): removal, residues, fixation, need-scaled mineral N
                    # and the residue and manure credits all move with yield exactly as
                    # reported. The term-by-term adjustments below covered removal and
                    # mineral need only; with CAPRI's balance (residues, fixation per
                    # tonne) the constraint and the accounts drifted apart and the EU
                    # surplus fell 28% against a 36% target.
                    row_B[i] = sa - float(coefs.get(a, 0.0)) + _exact
                    if float(nmin.get(a, 0.0)) > 0:
                        _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
                        _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                        _r = (_yc / _y0) ** 0.5 if (_y0 > 0 and _yc > 0) else 1.0
                        self._mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
                    continue
                if a in mint:                       # less fertiliser applied
                    sa -= float(nmin.get(a, 0.0)) * (1.0 - mint[a])
                # Uptake at THIS solve's yields - after fertiliser intensity,
                # pesticide and organic yield effects - as CAPRI's balance does.
                # With base-year uptake the constraint believed the target was
                # met while the true balance fell only half as far (Farm-to-Fork
                # EU surplus -16% against a target cut of about a third).
                if a in CROPS and ybase is not None:
                    y0 = float(ybase.get(a, 0.0)) if hasattr(ybase, "get") else 0.0
                    if y0 > 0:
                        yc = float(ycur.get(a, y0)) if hasattr(ycur, "get") else y0
                        sa += float(upt.get(a, 0.0)) * (1.0 - yc / y0)
                        # crop NEED follows yield (CAPRI NUTNED_: x sqrt(yield)),
                        # and so does the mineral N it calls for - exactly as the
                        # environmental accounts compute it. Without this term the
                        # constraint saw more fertiliser than the accounts after
                        # yield losses, demanded extra cuts, and the surplus fell
                        # past its target (Farm-to-Fork -45% vs CAPRI's -34%).
                        if yc > 0:
                            sa += (float(nmin.get(a, 0.0)) * float(mint.get(a, 1.0))
                                   * ((yc / y0) ** 0.5 - 1.0))
                if a in CROPS and float(nmin.get(a, 0.0)) > 0:
                    # mineral part of the coefficient (for CAPRI's fertiliser technologies
                    # inside the conic model): nmin x intensity x sqrt(yield / base yield)
                    _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
                    _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                    _r = (_yc / _y0) ** 0.5 if (_y0 > 0 and _yc > 0) else 1.0
                    self._mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
                row_B[i] = sa
            # A REGIONAL CAP: the tiered per-ha target times BASE farmland. With
            # current farmland as the denominator, land expansion diluted the
            # surplus: in North Brabant the target made land worth ~28,000 EUR/ha,
            # the land market expanded farmland to its 15% cap, the target went
            # slack, and the nitrogen and land loops pulled against each other
            # without settling. The required cut in kg N is unchanged; buying
            # land no longer meets it.
            base_area = float(sum(v for a, v in self._base_levels().items() if a in CROPS))
            A_rows.append(row_B)
            b_rows.append(float(target) * base_area)
            self._row_labels.append("N_balance")
            # manure must be spread on land: manure N <= limit x land in use
            mrow = srow[6] if len(srow) > 6 else None
            if mrow is not None:
                man, lim = mrow
                row_M = np.zeros(n)
                for i, a in enumerate(self.acts):
                    if a in man:
                        row_M[i] = float(man[a])
                    elif a in CROPS:
                        row_M[i] = -float(lim)
                A_rows.append(row_M)
                b_rows.append(0.0)
                self._row_labels.append("manure_application")

        # CAPRI's mineral fertiliser reduction (Green Deal mineRedu; pol_input/greendeal/minfert_redu_*.gms):
        #   "20"    e_synNMax: mineral N per ha of current land <= baseline mineral N per ha x (1 - r)
        #   "NNcrp" nMax_ with the "f2f" regulation of the inner fertiliser model: mineral N to each crop group per
        #           ha <= cap_g (baseline x (1 - r), CAPRI's exemptions). The inner model can move manure and crop
        #           residues between groups, so the binding condition on the regional model is the sum over the groups:
        #           mineral N to the capped groups <= sum_g cap_g x area_g.
        # As a row: sum_a (capped share_a x m_a - kappa_a) x_a + m_animals x_animals <= catch-crop N, m_a the
        # activity's mineral N from the environmental module's own balance (linear in activity levels, at this
        # solve's yields and fertiliser factors, as the N_balance row), kappa_a = sum_g share_ag x cap_g (kg/ha).
        mcap = getattr(self, "_mineral_cap", None)
        _env_m = getattr(self, "_env_for_surplus", None)
        if mcap is not None and _env_m is not None:
            mint = getattr(self, "_n_intensity", {}) or {}
            ycur = self.data.yields
            _fcr = float(mint.get("__credit__", 1.0))
            nmin_m = mcap.get("nmin") or {}
            ybase_m = mcap.get("ybase")
            row_m = np.zeros(n)
            mrow_parts = {}
            for i, a in enumerate(self.acts):
                _mi = {"__credit__": _fcr}
                if a in mint:
                    _mi[a] = float(mint[a])
                try:
                    m_a = float(_env_m.unit_nitrogen_balance(a, ycur, self.data.region_id, _mi)["n_mineral_input"])
                except Exception:
                    m_a = 0.0
                if a in CROPS:
                    row_m[i] = float(mcap["capped_share"].get(a, 0.0)) * m_a - float(mcap["kappa"].get(a, 0.0))
                    if float(nmin_m.get(a, 0.0)) > 0:
                        _y0 = float(ybase_m.get(a, 0.0)) if (ybase_m is not None and hasattr(ybase_m, "get")) else 0.0
                        _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                        _r = (_yc / _y0) ** 0.5 if (_y0 > 0 and _yc > 0) else 1.0
                        mrow_parts[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r \
                            * float(mcap["capped_share"].get(a, 0.0))
                else:
                    row_m[i] = m_a
            A_rows.append(row_m)
            b_rows.append(float(self._cover_n_increment()))
            self._row_labels.append("mineral_N")
            # crops' mineral part, for CAPRI's fertiliser technologies inside the conic model
            self._mineral_row_m = mrow_parts

        # CAPRI winterCover_: the catch crops need land not already under winter cover,
        #   sum_c crop_c x winter cover share_c <= UAAR - CATC + FALL.FLOOR  (UAAR: the region's data, fixed)
        # CAPRI adds the landscape rule's fallow floor (supply_model.gms l. 1987: "in case fallow land is
        # expanded only to meet the set aside target, take out from the calculation, otherwise we can
        # easily end up with negative values and infeasibilities"). Without it, where the floor fills
        # most of the arable land (Tyrol, Bolzano: floor 22 kha on 14 kha of arable land) the floor and
        # the catch-crop minimum could not both hold: the land-market solve failed and the fallback
        # emptied the region's grassland and herds.
        _cv = getattr(self, "_cover", None)
        wcs_ = getattr(self.data, "winter_cover_share", None)
        if _cv and _cv.get("delta", 0.0) > 0 and wcs_ is not None:
            row_W = np.array([float(wcs_.at[a, "share"]) if a in wcs_.index else 0.0 for a in self.acts])
            if row_W.any():
                A_rows.append(row_W)
                b_rows.append(_cv["uaa"] - _cv["req"] + float(getattr(self, "_fall_floor", 0.0) or 0.0)
                              + 1e-9 * max(1.0, _cv["uaa"]))
                self._row_labels.append("winter_cover")

        # CAPRI's FIXED activities (sets.gms FACT = MFCACT + OANI: other oilseeds, other industrial crops, other
        # animals): not endogenous, v_actLevl.FX at the data level (supply/prep_sim.gms l. 250); CAPRI has no
        # market for their products either (arm_sets.gms nonXX_CROPS)
        _x0f = self._base_levels()
        for i, a in enumerate(self.acts):
            if a in FIXED_ACTIVITIES:
                v = max(float(_x0f.get(a, 0.0)), 0.0)
                tol = 1e-7 * max(v, 1e-3)
                for sg in (1.0, -1.0):
                    row_f = np.zeros(n)
                    row_f[i] = sg
                    A_rows.append(row_f)
                    b_rows.append(sg * v + tol)
                    self._row_labels.append(f"fixed_{a}_{'up' if sg > 0 else 'lo'}")

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


    #: Elasticity of agricultural land supply with respect to the land rent.
    #: CAPRI's EU regions do not use its 0.05 market-model default; their land
    #: supply comes from agricultural land competing with forest (Allen
    #: elasticity of transformation -1) and other land (-3) in its land-use
    #: nest (supply/declare_calibration_models_for_land_supply.gms). Weighted by
    #: indicative rent shares (forest ~13% of land rents, other land ~1%), that
    #: gives 1 x 0.13 + 3 x 0.01 ~ 0.15. The rent shares are an approximation.
    LAND_SUPPLY_ELASTICITY = param("LAND_SUPPLY_ELASTICITY")
    LAND_EXPANSION_CAP = param("LAND_EXPANSION_CAP")

    def solve(self, *args, land_expansion: float = 0.0, surplus_row=None,
              n_balance_price: float = 0.0, mineral_cap=None, **kwargs):
        """Solve, letting agricultural land respond to the land rent.

        CAPRI has a land market: when a policy makes land scarce its value rises
        and agricultural area expands, absorbing other land (Farm-to-Fork: EU
        UAA +3% in JRC121368, Figure 5). With area fixed, a landscape floor had
        to take every hectare from crops, and the least profitable - oilseeds -
        lost about three times CAPRI's share of area.

        The model's own base land value is a few EUR/ha, because PMP
        calibration folds land rent into each crop's terms; CAPRI keeps rent
        explicit. So the signal is the INCREASE in land's shadow
        value against CAPRI's rent:  dL/L = elasticity x d(lambda) / rent.

        STATELESS. ``land_expansion`` is the expansion to use for this solve;
        the result carries ``land_expansion_next`` (a damped update) and
        ``land_update``. The supply module holds each region's expansion and
        passes it in on the next outer iteration, so the land market converges
        together with prices with ONE solve per region per iteration. An earlier
        version kept the expansion on the model itself, and a plain solve after
        shocked solves drifted (test_solve_leaves_no_state_behind).
        """
        e = float(land_expansion or 0.0)
        rent = getattr(self.data, "land_rent", None)
        active = bool(self.LAND_SUPPLY_ELASTICITY) and bool(rent) and rent > 0
        if active and getattr(self, "_lambda0", None) is None:
            # land's value at base: a property of the base problem, cached
            self._land_expansion = 0.0
            _yr, self.yani_price_ratio = getattr(self, "yani_price_ratio", None), None   # base problem
            try:
                self._lambda0 = float(self._solve_once().shadow_prices.get("arable_land", 0.0))
            finally:
                self.yani_price_ratio = _yr
        self._land_expansion = e
        self.landscape_shortfall = 0.0          # reset on every solve
        self.balance_shortfall = 0.0
        self._surplus_row = surplus_row         # held for THIS solve only
        self._mineral_cap = mineral_cap         # CAPRI's mineral fertiliser reduction, THIS solve only
        self._mineral_row_m = {}
        self._last_manure_trade = (0.0, 0.0)
        self._last_mineral_n = None
        self._nbal_price = float(n_balance_price or 0.0)
        self._n_intensity = {}
        self._land_solution = None              # set by this solve when the land market is used
        self._land_market_failed = False
        self._n_target_relaxed = False
        self._last_cattle_z = {}
        self._conic_failed = None
        self._conic_status = None
        try:
            res = self._solve_once(*args, **kwargs)
        finally:
            self._land_expansion = 0.0
            self._surplus_row = None
            self._mineral_cap = None
            self._nbal_price = 0.0
        res.n_intensity = dict(getattr(self, "_n_intensity", {}) or {})
        res.fert_tech_shares = dict(getattr(self, "_fert_tech_shares", {}) or {})   # before the reset below
        # K3: the final conic solve failed and the region was solved without feeding inside and technologies
        res.conic_failed = getattr(self, "_conic_failed", None)
        res.conic_status = getattr(self, "_conic_status", None)       # Solved / AlmostSolved / Solved (IPOPT polish)
        self._n_intensity = {}
        self._fert_tech_shares = {}
        res.landscape_shortfall = float(getattr(self, "landscape_shortfall", 0.0))
        res.balance_shortfall = float(getattr(self, "balance_shortfall", 0.0))
        self.landscape_shortfall = 0.0
        self.balance_shortfall = 0.0
        res.land_expansion = e
        res.land_target = e
        res.land_expansion_next = 0.0
        res.land_update = 0.0
        # ONE land-supply mechanism, as in CAPRI: where the land market solved this region (land
        # types as variables with CAPRI's transformation costs), it IS the land supply; the
        # rent-elasticity expansion below is the fallback for regions without land-market data.
        # Running both counted land supply twice, and with CAPRI's no-idle-land rule the
        # expansion no longer moved the solution while its target kept moving, so the land loop
        # never settled (updates of 0.3-0.6 between iterations).
        if active and getattr(self, "_land_solution", None) and getattr(type(self), "land_no_slack", False):
            active = False
        if active:
            lam = float(res.shadow_prices.get("arable_land", 0.0))
            target = self.LAND_SUPPLY_ELASTICITY * max(0.0, lam - self._lambda0) / rent
            res.land_target = min(target, self.LAND_EXPANSION_CAP)
            # a damped step, used when no earlier point is available; the
            # supply module replaces it with a secant step across iterations
            e_next = min(e + 0.5 * (res.land_target - e), self.LAND_EXPANSION_CAP)
            res.land_expansion_next = e_next if e_next >= 1e-6 else 0.0
            res.land_update = abs(res.land_expansion_next - e)
        return res

    def _solve_once(
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

    def _fit_balance_target(self, A_ub, b_ub, c_lin, x0):
        """Relax the nitrogen-balance target where the region cannot reach it.

        JRC121368, footnote 3 to its targets table: 'the reduction is relaxed
        in a limited number of regions where the model is infeasible'. Some
        regions must cut their surplus by over 80% under the tiered rule (North
        Brabant: 417 -> 75 kg N/ha), and with every crop at minimum fertiliser
        intensity no allocation reaches it. The target is set to the lowest
        surplus the region CAN reach, found exactly by a linear program, and the
        gap is recorded as balance_shortfall (kg N per ha of farmland above the
        target). Only reached when the solver fails and a balance row exists.
        """
        from capri_mod.supply.qp_solver import solve_qp
        self.balance_shortfall = 0.0
        labels = getattr(self, "_row_labels", [])
        if "N_balance" not in labels:
            return None, False, b_ub
        k = labels.index("N_balance")
        try:
            from scipy.optimize import linprog
            others = [i for i in range(len(b_ub)) if i != k]
            lp = linprog(A_ub[k], A_ub=A_ub[others], b_ub=b_ub[others],
                         bounds=[(0, None)] * len(self.acts), method="highs")
        except Exception:
            return None, False, b_ub
        if lp.status != 0:
            return None, False, b_ub
        least = float(lp.fun)                     # lowest reachable row value
        if least <= float(b_ub[k]):
            return None, False, b_ub              # not what makes it infeasible
        x_start = np.maximum(np.asarray(lp.x, dtype=float), 0.0)
        crop_area = float(sum(x_start[i] for i, a in enumerate(self.acts) if a in CROPS)) or 1.0
        for slack in (1e-3, 1e-2, 5e-2):
            b_fit = b_ub.copy()
            b_fit[k] = least + slack * max(abs(least), 1.0)
            x_qp, ok = solve_qp(self.Q, c_lin, A_ub, b_fit, x0=x_start)
            if not ok:
                x_qp, ok = solve_qp(self.Q, c_lin, A_ub, b_fit, x0=x0)
            if ok:
                self.balance_shortfall = (float(b_fit[k]) - float(b_ub[k])) / crop_area
                return x_qp, ok, b_fit
        return None, False, b_ub

    def _relax_n_target(self, Qa, ca, Aa, ba, ya0):
        """JRC121368 (sect. 4.3.4, p. 23): regions where the tiered nitrogen target "generated
        infeasibilities in the model" had their reduction "set at the EU average (36%)". The
        report names no regions and the model takes the nine highest baseline surpluses up front
        (SupplyModule.JRC_CAPPED_N_REGIONS); this applies the same rule to any OTHER region whose
        target proves infeasible in the land-market problem - in the model these are Dutch regions
        that IMPORT manure in CAPRI's 2030 reference (52-123 kg N/ha, held fixed without the
        manure market). The target per hectare becomes the region's base surplus x (1 - 36%); with
        the target per current hectare (e_SURTOTHa) its land terms move with it. Records
        balance_shortfall (kg N/ha relaxed) and n_target_relaxed. Returns (y, ok, Aa, ba)."""
        labels = list(getattr(self, "_row_labels", []))
        srow = getattr(self, "_surplus_row", None)
        if "N_balance" not in labels or srow is None or len(srow) < 8 or srow[7] is None:
            return None, False, Aa, ba
        T = float(srow[1]); T2 = float(srow[7]) * (1.0 - SupplyModule.JRC_CAPPED_CUT)
        if not T2 > T + 1e-9:
            return None, False, Aa, ba
        k = labels.index("N_balance")
        A2, b2 = Aa.copy(), ba.copy()
        base_area = float(sum(v for a_, v in self._base_levels().items() if a_ in CROPS))
        nl = getattr(self, "_nrow_land", None)
        if nl:
            cols, L0sum, tgt = nl
            for c_ in cols:
                A2[k, c_] *= T2 / tgt
            b2[k] += (T2 - T) * (base_area - L0sum)
        else:
            b2[k] += (T2 - T) * base_area
        from capri_mod.supply.qp_solver import solve_qp
        self._last_conic_duals = None
        y = self._feed_conic_solve(Qa, ca, A2, b2, ya0)
        ok = y is not None
        if not ok:
            y, ok = solve_qp(Qa, ca, A2, b2, x0=ya0)
        if not ok:
            return None, False, Aa, ba
        self.balance_shortfall = T2 - T
        self._n_target_relaxed = True
        return y, True, A2, b2

    def _fit_aug_row(self, Qa, ca, Aa, ba, ya0, label):
        """Relax one row of the LAND-MARKET problem to the closest value the region can reach.

        The land-market counterpart of _fit_landscape_floor and _fit_balance_target. When the
        land-market problem had no solution, the solve used to drop to the plain problem, where
        land may idle and the land types are fixed - silently leaving CAPRI's land rules (no idle
        land, land supply through the land market) in exactly the regions where they bind: North
        Brabant's neighbour Zeeland halved its herds and grassland under the N target alone. Here
        the row (landscape floor: -SETA <= -floor; N balance: surplus <= target) is set to the
        lowest value a linear program over the land-market rows can reach, plus a small margin,
        and the QP is solved again. JRC121368: 'the reduction is relaxed in a limited number of
        regions where the model is infeasible'. Records landscape_shortfall (1000 ha of set-aside)
        or balance_shortfall (kg N per ha of farmland)."""
        labels = list(getattr(self, "_row_labels", []))
        if label not in labels:
            return None, False, ba
        k = labels.index(label)
        from scipy.optimize import linprog
        from capri_mod.supply.qp_solver import solve_qp
        others = [i for i in range(len(ba)) if i != k]
        try:
            lp = linprog(Aa[k], A_ub=Aa[others], b_ub=ba[others], bounds=[(0, None)] * Aa.shape[1], method="highs")
        except Exception:
            return None, False, ba
        if lp.status != 0:
            return None, False, ba
        least = float(lp.fun)
        if least <= float(ba[k]):
            return None, False, ba                # not this row that makes it infeasible
        y_start = np.maximum(np.asarray(lp.x, dtype=float), 0.0)
        n_ = self.n
        area = float(sum(y_start[i] for i, a in enumerate(self.acts) if a in CROPS)) or 1.0
        for slack in (1e-3, 1e-2, 5e-2):
            b_fit = ba.copy()
            b_fit[k] = least + slack * max(abs(least), 1.0)
            self._last_conic_duals = None
            y = self._feed_conic_solve(Qa, ca, Aa, b_fit, y_start)
            ok = y is not None
            if not ok:
                y, ok = solve_qp(Qa, ca, Aa, b_fit, x0=y_start)
            if ok:
                if label == "landscape_floor":
                    self.landscape_shortfall = float(b_fit[k]) - float(ba[k])
                else:
                    self.balance_shortfall = (float(b_fit[k]) - float(ba[k])) / area
                return y, True, b_fit
        return None, False, ba

    def _fit_landscape_floor(self, A_ub, b_ub, c_lin, x0):
        """Meet as much of the landscape floor as the region's land allows.

        The floor is sized on TOTAL farmland, grassland included (CAPRI's rule),
        but set-aside can only sit on ARABLE land here. In regions with little
        arable land - Corsica, the Alpine regions of Italy and Austria, several
        Greek regions - the requirement does not fit and the problem has NO
        feasible solution: the general fallback then spent ~8 s per region
        (79% of a Farm-to-Fork run) and returned a point violating the
        constraints by up to 3.2 units, which the model used. CAPRI avoids this
        because grassland can convert to arable and landscape elements can sit
        on grassland; this model does not represent either. So the floor is
        capped at the most set-aside the region can physically hold, found
        exactly by a linear program, and the unmet part is recorded in
        landscape_shortfall. Only reached when the solver fails and a floor row
        exists; every feasible problem is untouched.
        """
        from capri_mod.supply.qp_solver import solve_qp
        self.landscape_shortfall = 0.0
        labels = getattr(self, "_row_labels", [])
        if "landscape_floor" not in labels or "SETA" not in list(self.acts):
            return None, False, b_ub
        k = labels.index("landscape_floor")
        j = list(self.acts).index("SETA")
        try:
            from scipy.optimize import linprog
            others = [i for i in range(len(b_ub)) if i != k]
            cobj = np.zeros(len(self.acts)); cobj[j] = -1.0
            lp = linprog(cobj, A_ub=A_ub[others], b_ub=b_ub[others],
                         bounds=[(0, None)] * len(self.acts), method="highs")
        except Exception:
            return None, False, b_ub
        if lp.status != 0:
            return None, False, b_ub
        floor = -float(b_ub[k])
        most = float(lp.x[j])
        if most >= floor:
            return None, False, b_ub          # the floor is not what binds
        # fit the floor just inside the land limit; if the fitted problem sits
        # so close to the limit that the solver's clipping check trips, step a
        # little further inside (Salzburg needed this)
        # the LP's point satisfies every fitted constraint: a feasible start,
        # which keeps the active-set solver from cycling (Salzburg did)
        x_start = np.maximum(np.asarray(lp.x, dtype=float), 0.0)
        for share in (0.999, 0.99, 0.97):
            b_fit = b_ub.copy()
            b_fit[k] = -share * most
            x_qp, ok = solve_qp(self.Q, c_lin, A_ub, b_fit, x0=x_start)
            if not ok:
                x_qp, ok = solve_qp(self.Q, c_lin, A_ub, b_fit, x0=x0)
            if ok:
                self.landscape_shortfall = floor - share * most
                return x_qp, ok, b_fit
        return None, False, b_ub

    def _solve_inner(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        nitrate_limit: Optional[float] = None,
        set_aside_requirement: float = 0.0,
    ) -> SupplyResult:
        self._cover = None              # catch-crop requirement: set by the pesticide/organic targets
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
                    NON_ADDER_KEYS = {"set_aside_requirement", "premium_factor_regional"}
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
                    # REGIONAL PREMIUM FACTORS {region: {activity: factor}} (premium_factor_regional):
                    # a CAPRI premium experiment by region and activity (e.g. coupled support
                    # removed, tools/run_vcs_2030.py); crops via cap_premium, animals via
                    # livestock_premium_coef (their premium basis on the model's heads)
                    _rf = (policy_shock.get("premium_factor_regional") or {}).get(
                        getattr(self.data, "region_id", None)) if isinstance(policy_shock, dict) else None
                    if _rf:
                        for a, f in _rf.items():
                            if a in prem.index and pd.notna(prem[a]):
                                prem[a] = prem[a] * float(f)
                        _lp = getattr(self.data, "livestock_premium_coef", None)
                        if _lp is not None:
                            _lp = _lp.copy()
                            for a, f in _rf.items():
                                if a in _lp.index and pd.notna(_lp[a]):
                                    _lp[a] = _lp[a] * float(f)
                            self.data.livestock_premium_coef = _lp
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
                self.apply_pesticide_reduction(_pest, organic_share=_org or None)

        # CAPRI's young-animal markets (arm/market_model.gms yaniMarket_; supply_model.gms
        # INPANI_ / SUPBAL_): calves, young cattle and replacement cows are outputs of some
        # cattle activities and inputs of others, sold and bought at prices cleared in the
        # market loop (CAPRIModel._update_young_animal_prices). Only the CHANGE from the base
        # price enters: (ratio - 1) x base value x (output - input) per head.
        self._apply_young_animal_prices()
        # CAPRI's emission tax on the activities (ghgTax; zero unless the scenario sets one)
        self._apply_ghg_tax()

        intensity_res = None
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        if nitrate_limit is not None:
            intensity_res = self._apply_intensity_margin(nitrate_limit)
        elif getattr(self, "_nbal_price", 0.0):
            self._apply_balance_price(self._nbal_price)
        else:
            # no N price: ammonia technologies at their base shares (resets any relief left
            # from an earlier solve; records the shares for reporting)
            self._apply_manure_techs(0.0)
            # inhibitors on manure under CAPRI's emission tax (Sprint 9m; without a tax they stay at zero)
            self._apply_manure_inhibitor(0.0)

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
        # only set on the QP path; the fallback path must not read it unset
        # (it used to, and a failed QP crashed the region instead of falling back)
        x_qp_feasible = None
        if _os.environ.get("CAPRI_DISABLE_QP") == "1":
            x_qp, qp_ok = None, False   # force general solver for A/B testing
        else:
            aug = self._land_augment(A_ub, b_ub, c_lin, x0) if getattr(self, "use_land_market", False) else None
            if aug is not None:
                # CAPRI LAND MARKET: land-type areas as variables (see _land_augment)
                Qa, ca, Aa, ba, ya0, rows = aug
                self._last_conic_duals = None
                _yc = self._feed_conic_solve(Qa, ca, Aa, ba, ya0)
                if _yc is not None:
                    y, qp_ok = _yc, True
                else:
                    y, qp_ok = solve_qp(Qa, ca, Aa, ba, x0=ya0)
                if not qp_ok:
                    from capri_mod.supply.qp_solver import solve_qp_ldp
                    yl, okl = solve_qp_ldp(Qa, ca, Aa, ba)
                    if okl:
                        yp, okp = solve_qp(Qa, ca, Aa, ba, x0=yl)
                        y = yp if okp else yl
                        qp_ok = float(np.max(Aa @ y - ba)) <= 1e-7 * max(1.0, float(np.max(np.abs(ba))))
                if not qp_ok:
                    # an unreachable landscape floor or N target, relaxed INSIDE the land-market
                    # problem (CAPRI's land rules stay in force); see _fit_aug_row
                    # Only the landscape floor: maximising set-aside is its natural relaxation. For the
                    # N balance the least reachable surplus is an extreme corner (Zeeland moved 95 of its
                    # 111 kha of arable land to forest) and the region keeps the plain-path fallback;
                    # result.land_market_failed records it.
                    for _lab_fit in ("landscape_floor",):
                        y_f, ok_f, ba = self._fit_aug_row(Qa, ca, Aa, ba, ya0, _lab_fit)
                        if ok_f:
                            y, qp_ok = y_f, True
                            break
                if not qp_ok:
                    # JRC121368's rule for regions where the N target is infeasible: the EU-average cut
                    y_f, ok_f, Aa, ba = self._relax_n_target(Qa, ca, Aa, ba, ya0)
                    if ok_f:
                        y, qp_ok = y_f, True
                self._land_market_failed = not qp_ok
                if qp_ok:
                    n_ = len(x0); x_qp = y[:n_]
                    _nl = len(getattr(self, "_land_types_used", []))
                    self._last_land = dict(zip(getattr(self, "_land_types_used", []), y[n_:n_ + _nl]))
                    self._last_mineral_n = float(y[n_ + _nl]) if getattr(self, "_alloc_cols", 0) else None
                    _pc = getattr(self, "_pool_cols", []) or []
                    self._last_manure_trade = (float(y[_pc[0]]), float(y[_pc[1]])) if len(_pc) == 2 else (0.0, 0.0)
                    self._last_aug = (Qa, ca, Aa, ba, y)
                    _gc = getattr(self, "_grass_col", None)
                    self._last_grass_z = float(y[_gc]) if _gc is not None and _gc < len(y) else 0.0
                    self._split_record(y)
                    if getattr(self, "_grass_pending_col", None) is not None:
                        from capri_mod.supply import qp_solver as _QPS_
                        _du = getattr(self, "_last_conic_duals", None)
                        self._grass_calibrate_from_duals(_du if _du is not None else _QPS_.LAST_DUALS)
                    if self._split_pending():
                        self._dairy_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                    self._last_hist_fallow = {c_: float(y[j_]) for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items() if j_ < len(y)}
                    if getattr(self, "_hist_pending", None):
                        from capri_mod.supply import qp_solver as _QPS_
                        _du = getattr(self, "_last_conic_duals", None)
                        self._histosol_calibrate_from_duals(_du if _du is not None else _QPS_.LAST_DUALS)
                    # land rows' limits at the solved land areas, so the shadow
                    # prices computed below see the right slack
                    b_ub = b_ub.copy()
                    for i, coeffs, const in rows:
                        b_ub[i] = const + sum(cf * float(y[n_ + k]) for k, cf in coeffs)
                    self._land_solution = dict(zip(self._land_types_used, y[n_:].tolist()))
            else:
                self._last_conic_duals = None
                self._last_grass_z = 0.0
                self._last_dairy_z = 0.0
                self._last_cattle_z = {}
                self._last_genet_z = {}
                # CAPRI's grassland and dairy splits on the plain path too (regions without
                # land-market data: Ireland, Berlin, Hamburg, ...)
                _n0 = len(x0)
                self._need_row = None
                self._alloc_cols = 0
                _lab = list(getattr(self, "_row_labels", []))
                Qg, cg, Ag, bg, sg = self._grass_intensity_column(
                    self.Q, c_lin, A_ub, b_ub, np.asarray(x0, float), _lab, _n0, 0)
                Qg, cg, Ag, bg, sg = self._dairy_intensity_column(Qg, cg, Ag, bg, sg, _lab, _n0)
                Qg, cg, Ag, bg, sg = self._histosol_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
                self._last_hist_fallow = {}
                _yc = None
                if getattr(self, "_grass_col", None) is not None or getattr(self, "_dairy_col", None) is not None \
                        or getattr(self, "_cattle_cols", None) or getattr(self, "_hist_cols", None):
                    _yg = self._feed_conic_solve(Qg, cg, Ag, bg, sg)
                    if _yg is None:
                        _yg, _okg = solve_qp(Qg, cg, Ag, bg, x0=sg)
                        _yg = _yg if _okg else None
                    if _yg is not None:
                        if getattr(self, "_grass_col", None) is not None:
                            self._last_grass_z = float(_yg[self._grass_col])
                        self._split_record(_yg)
                        _yc = _yg[:_n0]
                        if getattr(self, "_grass_pending_col", None) is not None:
                            self._grass_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                        if self._split_pending():
                            self._dairy_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                        self._last_hist_fallow = {c_: float(_yg[j_]) for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items()}
                        if getattr(self, "_hist_pending", None):
                            self._histosol_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                if _yc is None:
                    self._dairy_req_extra = None
                    _yc = self._feed_conic_solve(self.Q, c_lin, A_ub, b_ub, x0)
                    if _yc is not None and getattr(self, "_grass_pending_col", None) is not None:
                        self._grass_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                    if _yc is not None and self._split_pending():
                        self._dairy_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                    if _yc is not None and getattr(self, "_hist_pending", None):
                        self._histosol_calibrate_from_duals(getattr(self, "_last_conic_duals", None))
                if _yc is not None:
                    x_qp, qp_ok = _yc, True
                else:
                    x_qp, qp_ok = solve_qp(self.Q, c_lin, A_ub, b_ub, x0=x0)
                # record the plain problem as the land-market path records its own
                # (_last_aug), so the conic feed model can be built on either path
                self._last_plain = (self.Q, c_lin.copy(), A_ub.copy(), b_ub.copy(), x_qp.copy() if x_qp is not None else None)
            if not qp_ok:
                x_qp, qp_ok, b_ub = self._fit_landscape_floor(A_ub, b_ub, c_lin, x0)
            if not qp_ok:
                x_qp, qp_ok, b_ub = self._fit_balance_target(A_ub, b_ub, c_lin, x0)
            if not qp_ok:
                # EXACT solver before the slow general one. The heuristic active-
                # set loop can fail on FEASIBLE problems ('iteration limit'); the
                # least-distance/NNLS method is exact and finite. The QP has a
                # unique optimum (Q positive definite), so on captured Farm-to-Fork
                # failures it matched the trust-constr fallback in 29 of 30 cases
                # (to 1e-6 of the objective) and found a 3.5% better optimum in the
                # 30th, where trust-constr stopped short - ~0.5 ms instead of ~1 s.
                # Polished by the active-set loop warm-started at its solution;
                # accepted only if feasible. Infeasible problems return not-ok and
                # continue down the existing path unchanged.
                from capri_mod.supply.qp_solver import solve_qp_ldp
                x_l, ok_l = solve_qp_ldp(self.Q, c_lin, A_ub, b_ub)
                if ok_l:
                    x_p, ok_p = solve_qp(self.Q, c_lin, A_ub, b_ub, x0=x_l)
                    x_c = x_p if ok_p else x_l
                    tol_b = 1e-7 * max(1.0, float(np.max(np.abs(b_ub)))) if b_ub.size else 0.0
                    if not b_ub.size or float(np.max(A_ub @ x_c - b_ub)) <= tol_b:
                        x_qp, qp_ok = x_c, True

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
        # NOT under a nitrogen-balance target. The rail clamps each activity to
        # +-50% (or more) of base after the solve; it was meant for blow-ups of
        # tiny activities under price shocks. Under the nitrogen target it
        # (1) overrode the policy response - North Brabant's dairy herd sat at
        # exactly -50.0%, the rail, against an optimum near -69% - and (2) left
        # the shadow prices computed at the clamped, non-optimal point, where the
        # balance looked slack: its price read zero and the nitrogen loop chased
        # it down, so the region adopted no technologies. The policy constraint
        # is what bounds the response there.
        if price_shock is not None and getattr(self, "_surplus_row", None) is None:
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
                if np.max(A_ub @ x_opt - b_ub) > 1e-6 and x_qp_feasible is not None:
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
            # CAPRI's dairy split (Sprint 7b): z heads at DCOL instead of DCOH change milk by
            # (COMI_DCOL - COMI_DCOH) / COMI_DCOW per head (cull-cow beef, ~1% of the tonnage, is
            # the same for both and is scaled with it: REGISTERED)
            if _c is not None and _a == "DCOW":
                _dz = float(getattr(self, "_last_dairy_z", 0.0) or 0.0)
                _di = getattr(self.data, "dairy_intensity", None)
                if _dz and _di is not None:
                    gross_output[_a] += _dz * _c * float(_di["dcomi_rel"])
            # bulls and heifers (Sprint 7c): beef per stall, low - high, over the animal's average
            _cz_ = (getattr(self, "_last_cattle_z", None) or {}).get(_a)
            _ct_ = (getattr(self.data, "cattle_intensity", None) or {}).get(_a)
            if _c is not None and _cz_ and _ct_ is not None:
                gross_output[_a] += float(_cz_) * _c * float(_ct_["dbeef_rel"])
            # cattle genomics (breeding.gms genet_yld): g cows adopting give d_milk_rel more milk each
            for (_ga, _go), _gz in (getattr(self, "_last_genet_z", None) or {}).items():
                _ge = (getattr(self.data, "genetics_effects", None) or {}).get((_ga, _go))
                if _ga == _a and _c is not None and _gz and _ge is not None and float(_ge.get("d_milk_rel", 0.0) or 0.0):
                    gross_output[_a] += float(_gz) * _c * float(_ge["d_milk_rel"])

        # Gross margin
        # Reported gross margin is net revenue x activity levels. The PMP
        # quadratic and linear terms are a CALIBRATION DEVICE - they exist to
        # make the base year optimal - not economic costs, and including them
        # made this field meaningless: for DE11 it returned 55,531,046 where
        # the margin is 428,136 thousand EUR, because the quadratic term alone
        # is over a hundred times the linear one. That is why farm income used
        # to read as barely moving under policies that visibly changed land use.
        gm = float(self.net_revenues.reindex(self.acts).fillna(0.0).values @ x_opt)

        # Shadow prices: REAL dual variables, from the optimality conditions.
        # The solver minimises 1/2 x'Qx + c'x subject to A x <= b, x >= 0. On the
        # activities that are positive, Qx + c + A_act' mu = 0 over the binding
        # rows, which is solved for the multipliers mu >= 0 (objective units per
        # unit of the constrained quantity - EUR per ha for land).
        #
        # This used to be max(0, -slack) * 10: non-zero only when a constraint
        # was VIOLATED, so a binding constraint always read zero. The project's
        # early finding that 'the arable shadow price is zero in all 248 regions'
        # - used to rule land out as the binding channel - measured nothing.
        shadow = {}
        slack = b_ub - A_ub @ x_opt
        try:
            act_rows = np.where(np.abs(slack) <= 1e-6 * np.maximum(1.0, np.abs(b_ub)))[0]
            free = np.where(x_opt > 1e-9)[0]
            mu = np.zeros(len(b_ub))
            if len(act_rows) and len(free):
                grad = (self.Q @ x_opt + c_lin)[free]
                At = A_ub[np.ix_(act_rows, free)].T
                sol, *_ = np.linalg.lstsq(At, -grad, rcond=None)
                mu[act_rows] = np.maximum(sol, 0.0)
        except Exception:
            mu = np.zeros(len(b_ub))
        # FEEDING INSIDE (conic, Clarabel): the solver's own multipliers ARE the shadow
        # prices - re-detecting binding rows from an interior-point solution is
        # unreliable (inner N-price loops then ran long)
        _zc = getattr(self, "_last_conic_duals", None)
        if _zc is not None and getattr(type(self), "use_feed_in_supply", False):
            mu = np.zeros(len(b_ub)); k_ = min(len(b_ub), len(_zc))
            mu[:k_] = np.maximum(np.asarray(_zc[:k_], float), 0.0)
        labels = getattr(self, "_row_labels", [])
        for i, label in enumerate(labels):
            if i < len(mu) and label != "feed":
                shadow[label] = shadow.get(label, 0.0) + float(mu[i])

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



#: Eurostat country codes where they differ from the model's region prefixes.
_MS_ALIAS = {"GR": "EL", "UK": "UK"}


def _ms_code(region: str) -> str:
    return _MS_ALIAS.get(str(region)[:2], str(region)[:2])


def _ms_row(table, region):
    """A member state's row of a per-MS table, or None."""
    if table is None:
        return None
    ms = _ms_code(region)
    return table.loc[ms] if ms in table.index else None


def _ms_value(table, region, column):
    """A member state's value; 0.0 when the MS is absent (CAPRI's convention for
    landscape: a member state with no entry is already at the target)."""
    if table is None:
        return None
    ms = _ms_code(region)
    if ms in table.index and pd.notna(table.at[ms, column]):
        return float(table.at[ms, column])
    return 0.0


class SupplyModule:
    """
    Manages and runs all regional supply models in parallel.

    In the iterative supply-market loop, this module receives
    market prices from the MarketModule and returns aggregate
    supply quantities.
    """


    #: JRC121368 sect. 4.3.4: the nine regions with the highest baseline gross
    #: nitrogen balance (high animal numbers) had their reduction target set to
    #: the EU average cut, 36%, because the tiered target was infeasible there.
    JRC_CAPPED_N_REGIONS = int(param("JRC_CAPPED_N_REGIONS"))
    JRC_CAPPED_CUT = param("JRC_CAPPED_CUT")

    def _jrc_capped_regions(self, cs) -> set:
        """The nine regions with the highest CAPRI baseline N surplus per ha."""
        got = getattr(self, "_jrc_capped_cache", None)
        if got is None:
            try:
                col = cs["surplus_kg_n_per_ha"].dropna()
                got = set(col.sort_values(ascending=False).index[: self.JRC_CAPPED_N_REGIONS])
            except Exception:
                got = set()
            # sensitivity only (tools/run_f2f_2030.py --capped-regions): the report does not
            # name the nine regions; '+A,B' adds to them, 'A,B' replaces them
            ov = str(getattr(self, "jrc_capped_override", "") or "")
            if ov:
                extra = {x.strip() for x in ov.lstrip("+").split(",") if x.strip()}
                got = (got | extra) if ov.startswith("+") else extra
            self._jrc_capped_cache = got
        return got
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

    def set_genetics_effects(self, table: Optional[dict], settings_key: tuple) -> None:
        """Cattle genomics at the run's technology settings (capri_mod/policy/endotech.py). Each regional model
        keeps its genomics calibration (the linear cost terms taken from the base duals) per settings, so a
        scenario compared with the baseline of the same settings uses the calibration of that baseline."""
        self.data["genetics_effects"] = table
        self.genetics_key = settings_key
        for region, m in self._models.items():
            store = m.__dict__.setdefault("_genet_cz_store", {})
            old = m.__dict__.get("_genet_key")
            if old == settings_key:
                continue
            if old is not None:
                store[old] = getattr(m, "_genet_cz", None)
            m.data.genetics_effects = (table or {}).get(region)
            m._genet_cz = store.get(settings_key)
            m._genet_pending = None
            m._last_genet_z = {}
            m._genet_key = settings_key

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
            self._models[region]._genet_key = getattr(self, "genetics_key", None)
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
            land_rent=(float(d["land_rent_regional"].at[region, "rent_eur_per_ha"])
                       if d.get("land_rent_regional") is not None
                       and region in d["land_rent_regional"].index else None),
            landscape_target_pp=_ms_value(d.get("landscape_targets_ms"), region,
                                          "landscape_pp"),
            organic_targets_pp=_ms_row(d.get("organic_targets_ms"), region),
            livestock_intensity_bounds=(
                d["livestock_intensity_bounds"].loc[region]
                if d.get("livestock_intensity_bounds") is not None
                and region in d["livestock_intensity_bounds"].index else None),
            livestock_revenue_coef=(
                d["livestock_revenue_coef"].loc[region]
                if d.get("livestock_revenue_coef") is not None
                and region in d["livestock_revenue_coef"].index else None),
            livestock_product_value_coef=(
                d["livestock_product_value_coef"].loc[region]
                if d.get("livestock_product_value_coef") is not None
                and region in d["livestock_product_value_coef"].index else None),
            young_value_factor=(d.get("young_animal_value_factor") or {}).get(region),
            input_costs_ha=(d.get("plant_protection_cost") or {}).get(region),
            cover_crops=(d["cover_crops"].loc[region] if d.get("cover_crops") is not None
                         and region in d["cover_crops"].index else None),
            winter_cover_share=(d.get("winter_cover_share") or {}).get(region),
            grass_intensity=(d["grass_intensity"].loc[region]
                             if d.get("grass_intensity") is not None
                             and region in d["grass_intensity"].index else None),
            histosol=(d["histosol"].loc[region] if d.get("histosol") is not None
                      and region in d["histosol"].index else None),
            dairy_intensity=(d["dairy_intensity"].loc[region]
                             if d.get("dairy_intensity") is not None
                             and region in d["dairy_intensity"].index else None),
            cattle_intensity=(d.get("cattle_intensity") or {}).get(region),
            genetics_effects=(d.get("genetics_effects") or {}).get(region),
            livestock_product_value_by_market_coef=(
                d["livestock_product_value_by_market_coef"].loc[region]
                if d.get("livestock_product_value_by_market_coef") is not None
                and region in d["livestock_product_value_by_market_coef"].index else None),
            livestock_cost_coef=(
                d["livestock_cost_coef"].loc[region]
                if d.get("livestock_cost_coef") is not None
                and region in d["livestock_cost_coef"].index else None),
            livestock_output_value_coef=(
                d["livestock_output_value_coef"].loc[region]
                if d.get("livestock_output_value_coef") is not None
                and region in d["livestock_output_value_coef"].index else None),
            livestock_premium_coef=(
                d["livestock_premium_coef"].loc[region]
                if d.get("livestock_premium_coef") is not None
                and region in d["livestock_premium_coef"].index else None),
            fodder_balance=(d.get("fodder_balance") or {}).get(region),
            land_market=(d.get("land_market") or {}).get(region),
            livestock_feed_coef=(
                d["livestock_feed_coef"].loc[region]
                if d.get("livestock_feed_coef") is not None
                and region in d["livestock_feed_coef"].index else None),
        )


    #: CAPRI's exponent in othImpact.NMIN (envind/ghgMiti.gms, p_fertEffCor)
    FERT_EFF_COR = P_FERT_EFF_COR

    _FERT_JUL15 = None

    def _fert_techs(self, region):
        """CAPRI's fertiliser-efficiency options for this region (cropMiti, target N2OSYN).

        Data: CAPRI's miti_data_jul15 (the Green Deal runs' mitigation data,
        capri_data/2017/abatement/fert_options_jul15.csv, tools/build_fert_options_jul15.py);
        national entries, regional for VRT_SRUC (farm-size cost curve). Only CAPRI's active
        options (active_technologies.csv). Returns [(option, NMIN, S0, slope, s0, smax)], costs in
        EUR per TONNE of crop N need (GHG_Mit_Cost_ multiplies by mineral N x (1 + E)).

        envind/ghgMiti.gms:
          NMIN = (QEmitt(NOC) / QEmitt(option) - 1) ** p_fertEffCor; for NITR_INH QEmitt is set to
          0.9 x QEmitt(NOC) (l. 110) and, restMitFert on, NMIN <= (x + 0.1 - 1) ** p_fertEffCor
          (0 where x + 0.1 <= 1);
          regional maximum shares for options other than NITR_INH where crop need lies above
          precision farming's level (formula below);
          calibration: options without farm-size curves relSubs1/relSubs0 = 1.2/0.2, or 0.8/0 where
          the regional maximum share is below 1; slope = costParLin (relSubs1 - relSubs0) /
          (MaxShare - IniShare); VRT_SRUC keeps its data curvature costParSqr + pmpParSqr and relSubs0
          (0 where x + 0.1 - 1 <= NMIN(precfarm) and MaxShare < 1). S0 = relSubs0 x costParLin.
        The fertiliser-price curvature CAPRI carries both in pmpParSqr and in the endogenous
        fertiliser cost cancels at the calibration points and is left out on both sides (REGISTERED)."""
        cls = type(self)
        if cls._FERT_JUL15 is None:
            from pathlib import Path as _P
            import json as _json
            root = _P(__file__).resolve().parents[2] / "capri_data"
            f = root / "2017" / "abatement" / "fert_options_jul15.csv"
            tab = pd.read_csv(f) if f.exists() else pd.DataFrame()
            c8 = _json.load(open(root / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]
            to8 = {}
            for k, lst in c8.items():
                if not k.endswith("000000"):
                    for n2 in lst:
                        to8.setdefault(n2, k)
            # the shared map (tools/build_region_map.py: correspondence fixes, NUTS splits and merges)
            _rm = root / "shared" / "region_capri_map.csv"
            if _rm.exists():
                for _r in pd.read_csv(_rm, dtype=str).fillna("").itertuples(index=False):
                    if _r.capri_region:
                        to8[_r.region] = _r.capri_region
            cls._FERT_JUL15 = ({(r.region, str(r.option).upper()): r for r in tab.itertuples(index=False)}, to8)
        tab, to8 = cls._FERT_JUL15
        msc = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR"}.get(region[:2], region[:2]) + "000000"
        r8 = to8.get(region)
        act_ = active_technologies()
        x = overfert_factor(region)
        xm = (x + OVERFERT_MARKUP) if x is not None else None
        def q_of(opt, reg=None):
            rr = tab.get((reg, opt)) if reg else None
            rr = rr if rr is not None else tab.get((msc, opt))
            return rr
        pf = q_of("PRECFARM")
        q0 = float(pf.QEmitt_noc) if pf is not None and pf.QEmitt_noc == pf.QEmitt_noc else None
        qp = float(pf.QEmitt) if pf is not None else None
        out = []
        opts = {o for (r_, o) in tab if r_ == msc}
        for name in sorted(opts):
            if act_ is not None and name not in act_:
                continue
            sd = name in ("VRT_SRUC", "VRT_KTBL")
            rr = q_of(name, r8 if sd else None)
            if rr is None or q0 is None:
                continue
            k1 = float(rr.costParLin) if rr.costParLin == rr.costParLin else 0.0
            q = float(rr.QEmitt) if rr.QEmitt == rr.QEmitt else None
            if name == "NITR_INH":
                q = 0.9 * q0                                       # ghgMiti.gms l. 110
            if not k1 > 0 or q is None or not (0 < q < q0):
                continue
            nmin = (q0 / q - 1.0) ** self.FERT_EFF_COR
            s0 = float(rr.IniShare) if rr.IniShare == rr.IniShare else 0.0
            smax = float(rr.MaxShare) if rr.MaxShare == rr.MaxShare else 0.0
            if smax <= 0 and sd:
                nat = tab.get((msc, name))
                smax = float(nat.MaxShare) if nat is not None and nat.MaxShare == nat.MaxShare else 0.0
            if name == "NITR_INH" and xm is not None:             # restMitFert: NI cannot go below need
                if xm <= 1.0:
                    nmin = 0.0
                elif xm < nmin ** (1.0 / self.FERT_EFF_COR) + 1.0:
                    nmin = (xm - 1.0) ** self.FERT_EFF_COR
            if name != "NITR_INH" and xm is not None and xm > 1.0 and qp is not None:
                e_need = q0 / xm
                if e_need > qp:
                    smax = min(smax, (q0 - min(q0, q + e_need - qp)) / (q0 - q))
            smax = max(smax, 0.0)
            if smax <= s0 or nmin <= 0:
                continue
            if sd:
                slope = float(rr.costParSqr if rr.costParSqr == rr.costParSqr else 0.0) \
                    + float(rr.pmpParSqr if rr.pmpParSqr == rr.pmpParSqr else 0.0)
                rs0 = float(rr.relSubs0) if rr.relSubs0 == rr.relSubs0 else 0.0
                nmin_pf = (q0 / qp - 1.0) ** self.FERT_EFF_COR if qp else 0.0
                if xm is not None and xm - 1.0 <= nmin_pf and smax < 1.0:
                    rs0 = 0.0
                if slope <= 0:
                    continue
                out.append((name, nmin, rs0 * k1, slope, s0, smax))
            else:
                rs1, rs0 = (0.8, 0.0) if (smax < 1.0 and name != "NITR_INH") else (1.2, 0.2)
                out.append((name, nmin, rs0 * k1, k1 * (rs1 - rs0) / (smax - s0), s0, smax))
        return out

    #: Nitrates Directive limit on manure N, kg N per ha (91/676/EEC)
    MANURE_LIMIT = param("MANURE_LIMIT")

    def _manure_limit(self, region, model):
        """Manure N per head and the region's manure-application limit.

        Manure has to be spread on land. Without this link a region under a
        nitrogen cap could keep its animals and abandon its fields - North
        Brabant dropped ALL cropland, since removing a hectare removes its
        fertiliser and uptake and so cuts the surplus. CAPRI's fertiliser
        allocation forces each region's manure onto its crops, and the Nitrates
        Directive caps it at 170 kg N/ha, with derogations above that. The limit
        here is 170 kg N/ha or the region's own base level where higher, so it
        cannot bind at base. Manure N per 1000 head is the environmental module's
        own (organic N input for one unit of each animal).
        """
        try:
            if not hasattr(self, "_env_for_surplus"):
                from capri_mod.environmental.environmental_module import EnvironmentalModule
                self._env_for_surplus = EnvironmentalModule(self.data)
                self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
            ylds = self.data["yields"].loc[region]
            man = {}
            for a in model.acts:
                if a in CROPS:
                    continue
                nb = self._env_for_surplus.unit_nitrogen_balance(a, ylds, region)
                v = float(nb.get("n_organic_input", 0.0))
                if v > 0:
                    man[a] = v
            if not man:
                return None
            base = model._base_levels()
            land = sum(float(base.get(c, 0.0)) for c in CROPS)
            if land <= 0:
                return None
            base_rate = sum(man[a] * float(base.get(a, 0.0)) for a in man) / land
            return (man, max(self.MANURE_LIMIT, base_rate * 1.001))
        except Exception:
            return None

    #: CAPRI's baseline calibration (Sprint 9p): at most this many correction rounds per baseline run
    BASE_CAL_ROUNDS = int(param("BASE_CAL_ROUNDS"))
    FODDER_ACTS = ("GRAS", "MAIF", "OFOD", "ROOF")

    def calibrate_to_base(self, results: dict, reset: bool = False) -> float:
        """CAPRI's calibration of the supply models to the baseline (CAPMOD calibrates its PMP terms so that the
        baseline year's solution reproduces the projected activity levels): per region, the linear cost terms move by
        Q (x - x_target), the shift that makes the target optimal when the constraints' duals stay put, with the
        target the region's projected levels (the model's base levels). Returns the largest remaining drift, relative
        to the target (activities of at least 1 unit), before this round's correction; 0 once the rounds are used."""
        if reset:
            self._base_cal_round = 0
        rnd = int(getattr(self, "_base_cal_round", 0) or 0)
        worst = 0.0
        if rnd >= self.BASE_CAL_ROUNDS:
            return 0.0
        for region, res in (results or {}).items():
            mo = self._models.get(region)
            if mo is None or getattr(mo, "Q", None) is None or getattr(mo, "f", None) is None:
                continue
            acts = list(mo.acts)
            xb = np.maximum(mo._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
            act = getattr(res, "activities", None)
            if act is None:
                continue
            xs = np.asarray(pd.Series(act).reindex(acts).fillna(0.0).values, float)
            if not np.all(np.isfinite(xs)):
                continue
            d = xs - xb
            # fodder crops are held by the fodder balances (CAPRI's fodder equality): their level follows the herds'
            # fodder use, so their cost terms are not shifted (a shift there would do nothing while the balance binds
            # and act at once when a scenario loosens it)
            for j_, a_ in enumerate(acts):
                if a_ in self.FODDER_ACTS:
                    d[j_] = 0.0
            big = xb >= 1.0
            if big.any():
                worst = max(worst, float(np.max(np.abs(d[big]) / xb[big])))
            mo.f = np.asarray(mo.f, float) + np.asarray(mo.Q, float) @ d
            mo._base_cal_shift = np.asarray(getattr(mo, "_base_cal_shift", np.zeros(len(acts))), float) \
                + np.asarray(mo.Q, float) @ d
        self._base_cal_round = rnd + 1
        prev = getattr(self, "_base_cal_drift", None) if rnd > 0 else None
        self._base_cal_drift = worst
        # what the linear terms cannot move (activities held by the fodder balances and the feed rows) leaves the
        # largest drift unchanged round after round: stop correcting once a round gains less than 5%
        if prev is not None and worst > 0.95 * prev:
            self._base_cal_round = self.BASE_CAL_ROUNDS
            return 0.0
        return worst

    #: CAPRI's crop nutrient balance (NUTNED_, fertDistExcr_) and manure market in every EU solve, not only under
    #: the N target (Sprint 9k)
    use_nutned_always = True

    def _manure_context(self, region, model):
        """{"man_d", "nmin", "ybase"} for the regional model's crop-need row, manure trade columns and ammonia options
        (CAPRI has them in every run), or None outside the EU (msNoEU) or when the switch is off."""
        if not getattr(self, "use_nutned_always", True) or region[:2] in self.NON_EU_PREFIXES:
            return None
        cache = self.__dict__.setdefault("_mctx_cache", {})
        ck = (region, bool(getattr(self, "manure_trade_on", True)))
        if ck not in cache:
            ml = self._manure_limit(region, model)
            bc = self._balance_coefs(region, model)
            cache[ck] = None if (ml is None or bc is None) else \
                {"man_d": ml[0], "nmin": bc[1], "ybase": self.data["yields"].loc[region]}
        if cache[ck] is None:
            return None
        try:
            _ft = self._fert_techs(region) if float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0 else []   # emission tax
        except Exception:
            _ft = []
        return {**cache[ck], "techs": _ft}

    def _balance_coefs(self, region, model):
        """Each activity's contribution to the gross N balance, per unit.

        Evaluated with the environmental module's own balance on ONE unit of
        each activity (it is linear in activity levels), so the constraint and
        the reported surplus cannot disagree. Crops: fertiliser + fixation +
        deposition - uptake per ha; animals: manure N net of what leaves in
        products, per 1000 head. Base-year yields.
        """
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if not hasattr(self, "_env_for_surplus"):
                self._env_for_surplus = EnvironmentalModule(self.data)
                self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
            cache = getattr(self, "_balance_cache", {})
            ck = (region, bool(getattr(self, "manure_trade_on", True)))    # the base trade counts only with trade on
            if ck in cache:
                return cache[ck]
            ylds = self.data["yields"].loc[region]
            out, nmin, upt = {}, {}, {}
            for a in model.acts:
                nb = self._env_for_surplus.unit_nitrogen_balance(a, ylds, region)
                out[a] = float(nb["n_surplus"])
                nmin[a] = float(nb.get("n_mineral_input", 0.0))
                upt[a] = float(nb.get("n_crop_uptake", 0.0))
            ser = (pd.Series(out).reindex(model.acts).fillna(0.0), nmin, upt)
            cache[ck] = ser
            self._balance_cache = cache
            return ser
        except Exception:
            return None

    def _surplus_per_ha(self, region, model):
        """Region's base gross N surplus per ha of cropped area, or None."""
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if not hasattr(self, "_env_for_surplus"):
                self._env_for_surplus = EnvironmentalModule(self.data)
                self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
            acts = model._base_levels()
            ylds = self.data["yields"].loc[region]
            nb = self._env_for_surplus.compute_nitrogen_balance(acts, ylds, region)
            area = float(sum(float(acts.get(c, 0.0))
                             for c in self.data["areas"].columns))
            return nb["n_surplus"] / area if area > 0 else None
        except Exception:
            return None

    def _mineral_cap_spec(self, region, model, mineral_redu):
        """CAPRI's mineral fertiliser reduction for one region (Green Deal mineRedu), from the region's baseline
        (CAPRI: p_baselineDataout, the baseline's own results; here the calibrated base point, as the surplus
        target): {"kind", "reduction", "kappa": {crop: cap kg N/ha}, "capped_share": {crop: share of its area in
        capped groups}, "base_mineral", "group_caps", "limcres", "base_alloc", "nmin", "ybase", "techs"} or None.

        "20" (minfert_redu_uaa.gms): one cap per ha of land, baseline mineral N / baseline land x (1 - r).
        "NNcrp" (minfert_redu_by_crop.gms): per crop group from the baseline's allocation by CAPRI's inner
        fertiliser model (capri_mod.fert.inner_fert_dist), with CAPRI's exemptions."""
        from capri_mod.fert.inner_fert_dist import InnerFertDist, parse_mineral_redu
        kind, r = parse_mineral_redu(mineral_redu)
        if kind is None:
            return None
        cache = self.__dict__.setdefault("_mcap_cache", {})
        key = (region, kind, r)
        if key in cache:
            return cache[key]
        spec = None
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if getattr(self, "_env_for_surplus", None) is None:
                self._env_for_surplus = EnvironmentalModule(self.data)
                self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
            env = self._env_for_surplus
            base = model._base_levels()
            ylds = self.data["yields"].loc[region]
            nb = env.compute_nitrogen_balance(base, ylds, region)
            crops = {c: float(base.get(c, 0.0)) for c in CROPS if float(base.get(c, 0.0)) > 0}
            A_b = sum(crops.values())
            M_b = float(nb["n_mineral_input"])
            bc = self._balance_coefs(region, model)
            spec = dict(kind=kind, reduction=r, base_mineral=M_b, nmin=(bc[1] if bc is not None else {}),
                        ybase=ylds, techs=self._fert_techs(region), group_caps=None, limcres=None, base_alloc=None)
            uaa = {c: (1.0 - r) * M_b / A_b for c in CROPS} if A_b > 0 else {}
            spec["kappa"], spec["capped_share"] = uaa, {c: 1.0 for c in CROPS}
            if kind == "crp":
                inner = self.__dict__.get("_inner_fert")
                if inner is None:
                    inner = self._inner_fert = InnerFertDist()
                av = float(env._residue_availability(region)[0] or 0.0)
                alloc = inner.allocate(region, crops, M_b, float(nb.get("n_manure_applied", 0.0)),
                                       float(nb.get("n_residue_pool", 0.0)), av)
                if alloc is None or not alloc["converged"]:
                    import warnings as _w
                    _w.warn(f"mineral fertiliser cap by crop: no inner-model allocation for {region}; the UAA-wide "
                            f"cap (minfert_redu_uaa.gms) applies instead")
                    spec["kind"] = "uaa"
                else:
                    caps = inner.mineral_caps(region, alloc, r)
                    sh = inner.crop_shares(region)
                    spec["kappa"] = {c: sum(w * caps[g] for g, w in sh.get(c, {}).items() if g in caps) for c in CROPS}
                    spec["capped_share"] = {c: sum(w for g, w in sh.get(c, {}).items() if g in caps) for c in CROPS}
                    spec.update(group_caps=caps, limcres=inner.limcres_caps(region, alloc), base_alloc=alloc)
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"mineral fertiliser cap skipped for {region}: {_exc!r}")
            spec = None
        cache[key] = spec
        return spec

    #: supply regions outside the EU, where EU policy instruments do not apply
    NON_EU_PREFIXES = frozenset({"NO"})
    EU_POLICY_KEYS = frozenset({"set_aside_requirement", "nutrient_surplus_target", "surplus_rule", "surplus_cut",
                                "mineral_redu",
                                "pesticide_reduction",
                                "organic_area_target", "nitrate_limit_delta", "nitrate_limit"})

    #: tolerance on the nitrogen-balance price, EUR per kg N: absolute + relative
    NBAL_TOL_ABS = 0.01
    NBAL_TOL_REL = 1e-3
    #: at most this many solves per region and iteration to find its N price
    NBAL_INNER_MAX = 16
    #: land steps per outer iteration, and the land change (share of farmland)
    #: below which a region's land counts as settled
    LAND_INNER_MAX = 6
    LAND_TOL = 1e-4

    def _next_nbal(self, region, used: float, dual: float) -> float:
        """Next nitrogen-balance price for a region: a BRACKETED fixed point.

        The price we pass in sets fertiliser intensity; the solve then reports
        the balance constraint's own shadow price. The answer is where the two
        agree. Plain damping oscillated (North Brabant: 190 -> 95 -> ... -> 3 ->
        188): a high price cuts fertiliser so far the constraint goes slack and
        reports zero, then it binds again. The reported price falls as the
        price passed in rises, so dual > used means the answer lies above, and
        dual < used below. Each region keeps that interval and bisects inside it;
        until an upper end is known, it steps to the reported price.
        """
        br = getattr(self, "_nbal_bracket", {})
        lo, hi = br.get(region, (0.0, float("inf")))
        g = dual - used
        # At the answer, stay there: once the reported price matches the one
        # used (to a cent per kg N plus 0.1%), a secant step only amplifies
        # rounding noise and a bracket end left over from early iterations,
        # when prices and land were different, threw regions away from it.
        if abs(g) <= self.NBAL_TOL_ABS + self.NBAL_TOL_REL * abs(used):
            return used
        if g > 0:
            lo = max(lo, used)
        else:
            hi = min(hi, used)
        # SECANT inside the bracket (bisection alone halved the error per
        # iteration and needed 20+ outer iterations); bisect when the secant
        # would leave it, and step to the reported price while no upper end
        # is known yet
        prev = getattr(self, "_nbal_prev", {}).get(region)
        nxt = None
        if prev is not None and abs(g - prev[1]) > 1e-12 and abs(used - prev[0]) > 1e-12:
            nxt = used - g * (used - prev[0]) / (g - prev[1])
        if nxt is None or not (lo < nxt < hi):
            if hi == float("inf"):
                nxt = max(dual, 2.0 * used, 1e-3)
            else:
                nxt = 0.5 * (lo + hi)
        self._nbal_prev = getattr(self, "_nbal_prev", {})
        self._nbal_prev[region] = (used, g)
        br[region] = (lo, hi)
        self._nbal_bracket = br
        return max(0.0, nxt)

    def _next_land(self, region, result) -> float:
        """Next land expansion for a region: a SECANT step on g(e) = target(e) - e.

        A damped step oscillated where land rents are low and the response is
        steep (SK01 swung between ~4.5% and ~9% without settling). The secant
        uses this region's previous iterate; when two iterates straddle the
        answer it lands between them, so it cannot keep swinging.
        """
        e = float(getattr(result, "land_expansion", 0.0))
        g = float(getattr(result, "land_target", e)) - e
        prev = getattr(self, "_land_prev", {}).get(region)
        cap = getattr(result, "land_cap", None) or 0.15
        # BRACKET. g(e) falls as land expands, so g > 0 means the answer lies
        # above e and g < 0 below. Each region keeps that interval; a secant
        # step that would leave it is replaced by bisection, which converges
        # even where g jumps - as it does where the landscape floor is fitted
        # to the land and moves with it (the outer loop hit 15 iterations with
        # land updates of 0.03-0.13 while prices had long settled).
        lo, hi = getattr(self, "_land_bracket", {}).get(region, (0.0, cap))
        if g > 0:
            lo = max(lo, e)
        else:
            hi = min(hi, e)
        if hi < lo:
            lo, hi = hi, lo
        if prev is not None and abs(g - prev[1]) > 1e-9 and abs(e - prev[0]) > 1e-12:
            e_new = e - g * (e - prev[0]) / (g - prev[1])
        else:
            e_new = e + 0.5 * g
        if not (lo < e_new < hi) and hi - lo > 1e-9:
            e_new = 0.5 * (lo + hi)
        e_new = min(max(e_new, 0.0), cap)
        if e_new < 1e-6:
            e_new = 0.0
        self._land_prev = getattr(self, "_land_prev", {})
        self._land_prev[region] = (e, g)
        self._land_bracket = getattr(self, "_land_bracket", {})
        self._land_bracket[region] = (lo, hi)
        result.land_expansion_next = e_new
        result.land_update = abs(e_new - e)
        return e_new

    #: The market whose price each activity earns, where the codes differ.
    #: The market-to-farm price signal is keyed by MARKET COMMODITY, but margins
    #: and the yield-price response look it up by ACTIVITY: without this map no
    #: animal ever saw a meat, milk or egg price change (the +7% pork price under
    #: Farm-to-Fork never reached pig farmers), and rye and oats never saw the
    #: other-cereals price.
    ACTIVITY_PRICE_SOURCE = {
        "DCOW": "MILK",
        "BULL": "BEEF", "BCOW": "BEEF", "HFRS": "BEEF", "CALV": "BEEF",
        "PIGS": "PORK", "PIGF": "PORK",
        "BROI": "POUL", "LAYS": "EGGS", "SHGP": "SHGM",
        "RYEM": "OCER", "OATS": "OCER",
    }

    def _activity_signals(self, price_signals):
        """Add activity-keyed entries to a commodity-keyed price signal."""
        if price_signals is None:
            return None
        sig = price_signals.copy()
        for act, comm in self.ACTIVITY_PRICE_SOURCE.items():
            if act not in sig.index and comm in sig.index:
                sig[act] = float(sig[comm])
        return sig

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
        price_signals = self._activity_signals(price_signals)
        target_regions = regions or self.regions
        results = {}
        n_failed = 0

        self.max_land_update = 0.0
        # A new run (no price signal yet) starts from base land and no nitrogen
        # price - reset ONCE, here. These resets used to sit inside the region
        # loop, so on a run's first iteration every region wiped the land state,
        # secant memory and bracket of all regions before it: only the last
        # region kept them, and every other region lost an iteration.
        if price_signals is None or not hasattr(self, "_land_state"):
            self._land_state, self._land_prev, self._land_bracket = {}, {}, {}
            self._nbal_state, self._nbal_bracket, self._nbal_prev = {}, {}, {}
        _pol_all = policy_scenario
        target_regions = list(target_regions)
        n_regions = len(target_regions)
        for i, (region, result, failed, lu_r, kind) in enumerate(
                self._solve_regions(target_regions, _pol_all, price_signals, verbose)):
            if verbose and i % 50 == 0:
                print(f"  Supply module: solved region {i+1}/{n_regions}...")
            n_failed += failed
            if result is None:
                continue
            results[region] = result
            # merged in the regions' order, so the trace is the same with any number of workers
            if lu_r > getattr(self, "max_land_update", 0.0):
                self.max_land_region = (region, kind)
            self.max_land_update = max(getattr(self, "max_land_update", 0.0), lu_r)

        if verbose:
            print(f"  Supply module complete: {len(results)} regions, "
                  f"{n_failed} non-converged.")
        return results

    def _solve_region(self, region, _pol_all, price_signals, verbose=False):
        """One region's solves within an outer iteration (land and nitrogen-price inner loops, CAPRI's regional
        supply model at fixed market prices). Returns (region, result or None, failed 0/1, land/N-price update,
        which loop). Reads the module's current signals and writes only this region's entries of the land and
        nitrogen-price state and of the caches, so regions can be solved in any order or in parallel (run)."""
        # EU policy instruments apply to EU member states only: CAPRI's Green Deal files restrict
        # the surplus target (surptot.gms), organic targets (organic_area.gms), pesticide cuts
        # (conventional_io.gms) to EU27yr19 and take landscape targets for EU regions; Norway is
        # in the model's supply regions but not in the EU
        policy_scenario = _pol_all
        if isinstance(_pol_all, dict) and region[:2] in self.NON_EU_PREFIXES:
            policy_scenario = {k: v for k, v in _pol_all.items() if k not in self.EU_POLICY_KEYS}
        try:
            model = self._get_or_build_model(region)
            # a mandatory non-productive share travels with the policy
            # dict and binds the arable land constraint
            sa, nlim, surplus_row = 0.0, None, None
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
                    # JRC121368: a BINDING RESTRICTION ON THE GROSS NITROGEN
                    # BALANCE, at the tiered target per hectare. Imposed on
                    # the balance itself - fertiliser, manure, fixation and
                    # deposition minus uptake - not on applied nitrogen: a
                    # cap on applied N let cheap crop adjustments do work that
                    # on the true balance falls on livestock (herds moved
                    # -0.1 to -1% against CAPRI's -10 to -18%).
                    bc = self._balance_coefs(region, model)
                    sp = self._surplus_per_ha(region, model)
                    _rule = str(policy_scenario.get("surplus_rule", "star3") or "star3")
                    if bc is not None and sp is not None and sp > 0 and _rule == "star3":
                        # CAPRI star 3.0 surptot.gms: data(srnuts2,"SURTOT","MAXS") = baseline surplus per ha
                        # x (1 - surpRedu/100), every EU NUTS2 region alike (relaxations only from 2090)
                        target = sp * (1.0 - float(policy_scenario.get("surplus_cut", 0.5) or 0.5))
                        surplus_row = (bc[0], target, bc[1], bc[2],
                                       self.data["yields"].loc[region],
                                       self._fert_techs(region),
                                       self._manure_limit(region, model),
                                       sp)
                    elif bc is not None and sp is not None and sp > 0:
                        # The REQUIRED CUT comes from CAPRI's own baseline
                        # surplus (its surptot.gms input), via the tiered
                        # rule, as the same PERCENTAGE of the surplus. This model's base
                        # surplus is lower than CAPRI's, above all in
                        # livestock regions (Brittany 80 vs 176 kg/ha), and
                        # the steep tiered rule turned that into cuts up to
                        # four times too small - herds then hardly needed
                        # to move. Unreachable cuts are relaxed (shortfall).
                        target = model.tiered_surplus_target(sp)
                        cs = self.data.get("capri_baseline_surplus")
                        if cs is not None and region in cs.index:
                            sp_c = float(cs.at[region, "surplus_kg_n_per_ha"])
                            if sp_c == sp_c and sp_c > 0:
                                # CAPRI's PERCENTAGE cut, applied to this
                                # model's surplus. Imposing CAPRI's cut in
                                # kg/ha instead could exceed this model's
                                # whole surplus (Brittany: a 101 kg/ha cut
                                # against an 80 kg/ha surplus) and forced
                                # herds down ~58% - an artefact of mixing
                                # two differently composed balances.
                                target = sp * model.tiered_surplus_target(sp_c) / sp_c
                                # JRC121368 (EUR 30317 EN, sect. 4.3.4, p. 23): "the
                                # target for nine regions with high GNB values in the
                                # baseline associated with high animal numbers generated
                                # infeasibilities in the model ... the reduction target
                                # for these regions were set at the EU average (36%)".
                                # The nine = highest CAPRI baseline surplus per ha.
                                # Without this cap those regions faced 76-88% cuts:
                                # extreme N shadow prices, pig overshoot, high manure
                                # prices and importers trading crops for manure fees.
                                if region in self._jrc_capped_regions(cs):
                                    target = sp * (1.0 - self.JRC_CAPPED_CUT)
                        surplus_row = (bc[0], target, bc[1], bc[2],
                                       self.data["yields"].loc[region],
                                       self._fert_techs(region),
                                       self._manure_limit(region, model),
                                       sp)

            # CAPRI's mineral fertiliser reduction (mineRedu), EU27 only (minfert_redu_*.gms)
            mcap = None
            if isinstance(policy_scenario, dict) and str(policy_scenario.get("mineral_redu", "00") or "00") != "00":
                mcap = self._mineral_cap_spec(region, model, policy_scenario.get("mineral_redu"))
            # each region's land expansion and balance price are held HERE,
            # not on the model; they are reset once per run, before the loop
            # Land and the nitrogen-balance price are both settled WITHIN the
            # iteration, at fixed market prices: each depends only on this
            # region's own shadow prices. Carried across outer iterations,
            # their brackets went stale as market prices moved, and 12 regions
            # kept the loop open on land after the nitrogen price had settled.
            e_land = self._land_state.get(region, 0.0)
            nb_used = getattr(self, "_nbal_state", {}).get(region, 0.0) if surplus_row else 0.0
            self._land_bracket = getattr(self, "_land_bracket", {})
            self._land_prev = getattr(self, "_land_prev", {})
            self._land_bracket.pop(region, None)
            self._land_prev.pop(region, None)
            e_next = e_land
            n_metric = 0.0
            # CAPRI prices raw milk per member state (its dairies' fat and protein balances, raw milk not
            # traded): the region's milk price is the EU signal plus its member state's departure from the
            # EU average (MarketModule.dairy_block, CAPRIModel)
            _ps_r = price_signals
            _mdev = getattr(self, "milk_price_dev_ms", None) or {}
            if _mdev and price_signals is not None and "MILK" in price_signals.index:
                _msr = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}.get(region[:2], region[:2]) + "000000"
                _dv = float(_mdev.get(_msr, 0.0))
                if _dv:
                    _ps_r = price_signals.copy()
                    _ps_r["MILK"] = float(price_signals["MILK"]) + _dv
                    if "DCOW" in _ps_r.index:
                        _ps_r["DCOW"] = float(_ps_r["MILK"])
            for _land_it in range(self.LAND_INNER_MAX):
                solve_kw = dict(
                    land_expansion=e_land,
                    price_shock=_ps_r,
                    policy_shock=policy_scenario,
                    nitrate_limit=nlim,
                    set_aside_requirement=sa,
                    surplus_row=surplus_row,
                    mineral_cap=mcap,
                )
                model.ration_state = (getattr(self, "ration_state", None) or {}).get(region)
                model.use_land_market = getattr(self, "use_land_market", False)
                model.grassland_allowance = getattr(self, "grassland_allowance", 0.0)
                model.manure_pool_price = (getattr(self, "manure_pool_price", None) or {}).get(region[:2], 0.0)
                model.yani_price_ratio = getattr(self, "yani_price_ratio", None)
                model.feed_rations = (getattr(self, "feed_rations", None) or {}).get(region)
                model.feed_prices = (getattr(self, "feed_prices", None) or {}).get(region)
                # CAPRI's feed bulk prices of the region's member state (feedBlkPrice_, CAPRIModel)
                _ms = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}.get(region[:2], region[:2]) + "000000"
                model.feed_bulk_ratio = {b: x for (m, b), x in (getattr(self, "feed_bulk_ratio", None) or {}).items()
                                         if m == _ms}
                # CAPRI's emission tax (ghgTax): EU regions only (msNoEU excluded), CAPRIModel sets it
                model.ghg_tax = float(getattr(self, "ghg_tax", 0.0) or 0.0) if not region.startswith("NO") else 0.0
                model.ghg_coef = (getattr(self, "ghg_coef", None) or {}).get(region)
                # the regional model needs the environmental module for the
                # balance's substitution factor (manure market, crop-need
                # limit); it lived only on the supply module, so the
                # regional calls failed and fell back silently
                if getattr(self, "_env_for_surplus", None) is None:
                    from capri_mod.environmental.environmental_module import EnvironmentalModule
                    self._env_for_surplus = EnvironmentalModule(self.data)
                    self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
                model._env_for_surplus = self._env_for_surplus
                # CAPRI's crop nutrient balance and manure market in every EU solve (Sprint 9k)
                model._manure_ctx = self._manure_context(region, model)
                result = model.solve(n_balance_price=nb_used, **solve_kw)
                # manure market: hand the region's endogenous manure trade and allocated
                # mineral N to the environmental accounting (else the reported N balance
                # recomputes them from herds and fixed rates and misses the trade)
                result.manure_trade = tuple(getattr(model, "_last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
                result.mineral_n_alloc = getattr(model, "_last_mineral_n", None)
                result.manure_availability = getattr(model, "_pool_avail", 0.0)
                result.animal_n_relief = _merge_relief(model)
                result.manure_ni_nh3 = dict(getattr(model, "_manure_ni_nh3", None) or {})
                result.cover_crops = dict(getattr(model, "_cover", None) or {})
                result.animal_nh3_saved = dict(getattr(model, "_animal_nh3_saved", None) or {})
                result.manure_tech_shares = dict(getattr(model, "_manure_tech_shares", None) or {})
                result.grass_ext_shift = float(getattr(model, "_last_grass_z", 0.0) or 0.0)
                result.dairy_low_shift = float(getattr(model, "_last_dairy_z", 0.0) or 0.0)
                result.cattle_shift = dict(getattr(model, "_last_cattle_z", None) or {})
                result.genetics_shift = dict(getattr(model, "_last_genet_z", None) or {})
                result.histosol_fallow = dict(getattr(model, "_last_hist_fallow", None) or {})
                _ls = getattr(model, "_land_solution", None) or {}
                result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model, "_land_types_used", []) if t_ in _ls}
                result.land_market_failed = bool(getattr(model, "_land_market_failed", False))
                result.n_target_relaxed = bool(getattr(model, "_n_target_relaxed", False))
                if surplus_row and model._ni_inside() and getattr(model, "_conic_ok", False):
                    # capri-mod-proto: nothing in the regional model depends on the N price any more
                    # (fertiliser and ammonia technologies and the inhibitor on manure are all decided
                    # inside the conic model), so the target is a plain constraint, as in CAPRI's NLP:
                    # one solve, and its dual is the N-balance price (reporting)
                    nb_used = max(float(result.shadow_prices.get("N_balance", 0.0)), 0.0)
                    self._nbal_state[region] = nb_used
                    n_metric = 0.0
                elif surplus_row:
                    # nitrogen-balance price: a fresh bracket at this land level
                    self._nbal_bracket[region] = (0.0, float("inf"))
                    self._nbal_prev.pop(region, None)
                    for _ in range(self.NBAL_INNER_MAX):
                        dual = float(result.shadow_prices.get("N_balance", 0.0))
                        nb_next = self._next_nbal(region, nb_used, dual)
                        if nb_next == nb_used:
                            break
                        nb_used = nb_next
                        result = model.solve(n_balance_price=nb_used, **solve_kw)
                    self._nbal_state[region] = nb_used
                    # settled when the price matches what the constraint
                    # reports, or - at a kink, where it jumps from positive to
                    # zero - when the bracket around it is within tolerance
                    lo, hi = self._nbal_bracket.get(region, (0.0, float("inf")))
                    gap = abs(float(result.shadow_prices.get("N_balance", 0.0)) - nb_used)
                    tol = self.NBAL_TOL_ABS + self.NBAL_TOL_REL * abs(nb_used)
                    n_metric = 1e-3 * min(gap, hi - lo) / tol
                e_next = self._next_land(region, result)
                if abs(e_next - e_land) <= self.LAND_TOL:
                    break
                e_land = e_next
            # Attach the regional model's FINAL state to the result stored: the
            # inner N-price loop re-solves and returns new result objects, so
            # fields set after the first solve were lost (technologies are only
            # adopted once the N price is positive, i.e. after the first solve).
            try:
                result.manure_trade = tuple(getattr(model, "_last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
                result.mineral_n_alloc = getattr(model, "_last_mineral_n", None)
                result.manure_availability = getattr(model, "_pool_avail", 0.0)
                result.animal_n_relief = _merge_relief(model)
                result.manure_ni_nh3 = dict(getattr(model, "_manure_ni_nh3", None) or {})
                result.cover_crops = dict(getattr(model, "_cover", None) or {})
                result.animal_nh3_saved = dict(getattr(model, "_animal_nh3_saved", None) or {})
                result.manure_tech_shares = dict(getattr(model, "_manure_tech_shares", None) or {})
                result.grass_ext_shift = float(getattr(model, "_last_grass_z", 0.0) or 0.0)
                result.dairy_low_shift = float(getattr(model, "_last_dairy_z", 0.0) or 0.0)
                result.cattle_shift = dict(getattr(model, "_last_cattle_z", None) or {})
                result.genetics_shift = dict(getattr(model, "_last_genet_z", None) or {})
                result.histosol_fallow = dict(getattr(model, "_last_hist_fallow", None) or {})
                _ls = getattr(model, "_land_solution", None) or {}
                result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model, "_land_types_used", []) if t_ in _ls}
                result.land_market_failed = bool(getattr(model, "_land_market_failed", False))
                result.n_target_relaxed = bool(getattr(model, "_n_target_relaxed", False))
                result.nitrate_n_extra = model._nitrate_extra()
                # CAPRI's mineral fertiliser reduction: the regulations of the inner fertiliser model (reporting)
                result.mineral_cap = ({k: mcap[k] for k in ("kind", "reduction", "base_mineral", "group_caps",
                                                            "limcres")} if mcap else None)
                result.feed_dm = (dict(getattr(model, "_last_feed_dm", None) or {})
                                  if getattr(model, "_last_conic_duals", None) is not None else None)
                result.feed_t = (dict(getattr(model, "_last_feed_t", None) or {})
                                 if getattr(model, "_last_conic_duals", None) is not None else None)
                # fertiliser technologies inside: each crop's reported intensity includes its
                # inside factor m_c / (n_c area_c) (reporting only; the N row never sees it)
                _ff = getattr(model, "_fert_inside_factor", None) or {}
                if _ff and getattr(model, "_last_conic_duals", None) is not None:
                    _ni = dict(getattr(result, "n_intensity", None) or {})
                    for _c, _f in _ff.items():
                        _ni[_c] = float(_ni.get(_c, 1.0)) * float(_f)
                    result.n_intensity = _ni
                if not getattr(result, "fert_tech_shares", None):
                    result.fert_tech_shares = dict(getattr(model, "_fert_tech_shares", None) or {})
                # the options' N saving (CAPRI othImpact NMIN), for their emission side effects
                if result.fert_tech_shares:
                    try:
                        result.fert_nmin = {o_[0]: float(o_[1]) for o_ in self._fert_techs(region)}
                    except Exception:
                        result.fert_nmin = {}
                result.nitrate_share = {a: float(v.get("nitr_share", 0.0))
                                        for a, v in (getattr(model, "ration_state", None) or {}).items()
                                        if isinstance(v, dict) and float(v.get("nitr_share", 0.0)) > 0}
                # regions without substitution data (Berlin: almost no farmland) return
                # None - never let that drop the region
                try:
                    _sb = model._env_for_surplus._substitution(region) if getattr(model, "_env_for_surplus", None) is not None else None
                    result.n_substitution = float(_sb[0]) if _sb else 0.0
                except Exception:
                    result.n_substitution = 0.0
            except AttributeError:
                pass
            self._land_state[region] = e_next
            _lu_r = max(n_metric, float(getattr(result, "land_update", 0.0)))
            # which loop keeps the region open (outer-loop trace)
            _kind = "N price" if n_metric >= float(getattr(result, "land_update", 0.0)) else "land"
            return region, result, (0 if result.converged else 1), _lu_r, _kind
        except Exception as e:
            if verbose:
                print(f"    WARNING: Region {region} failed: {e}")
            return region, None, 1, 0.0, None

    #: worker processes for the regional solves: None = the machine's cores (CAPRI_WORKERS overrides), 1 = in this
    #: process. CAPRI solves its regional models one after another (or in parallel GAMS grid jobs); they are
    #: independent at given market prices, so the results do not depend on the number of workers
    n_workers: Optional[int] = None
    #: regional state carried between iterations, and the region-keyed caches, sent back from the workers
    _PAR_STATE = ("_land_state", "_land_prev", "_land_bracket", "_nbal_state", "_nbal_bracket", "_nbal_prev")
    _PAR_CACHES = ("_mctx_cache", "_balance_cache", "_mcap_cache")

    def workers(self, n_regions: int) -> int:
        """Number of worker processes for n_regions regional solves."""
        n = self.n_workers
        if n is None:
            env = os.environ.get("CAPRI_WORKERS", "").strip()
            if env:
                n = int(env)
            else:
                try:
                    n = len(os.sched_getaffinity(0))
                except AttributeError:
                    n = os.cpu_count() or 1
        n = max(1, min(int(n), n_regions - 1))     # the first region is always solved here (below)
        if n > 1 and "fork" not in multiprocessing.get_all_start_methods():
            n = 1                                  # the workers inherit the module's state by fork
        return n

    def _solve_regions(self, regions, _pol_all, price_signals, verbose=False):
        """The regions' solves in the regions' order, in this process or across worker processes.

        The workers are forked for each call, so they start from this module's current state (prices, rations,
        tax, the regional models and their land and nitrogen-price state); each returns its region's result,
        model and state, which replace this process's copies. The first region is solved here first, so the
        data files read on first use are loaded once, before the fork, not in every worker."""
        nw = self.workers(len(regions))
        if nw <= 1:
            for r in regions:
                yield self._solve_region(r, _pol_all, price_signals, verbose)
            return
        yield self._solve_region(regions[0], _pol_all, price_signals, verbose)
        if getattr(self, "_env_for_surplus", None) is None:       # shared by all regional models
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            self._env_for_surplus = EnvironmentalModule(self.data)
            self._env_for_surplus.set_manure_trade(getattr(self, "manure_trade_on", True))
        cs = self.data.get("capri_baseline_surplus")
        if cs is not None:
            self._jrc_capped_regions(cs)
        rest = list(regions[1:])
        global _PAR_CTX
        _PAR_CTX = (self, _pol_all, price_signals, verbose)
        try:
            with multiprocessing.get_context("fork").Pool(nw) as pool:
                for out, model, state, caches in pool.imap(_par_solve_region, rest, chunksize=1):
                    region = out[0]
                    if model is not None:
                        model._env_for_surplus = self._env_for_surplus
                        self._models[region] = model
                    for name in self._PAR_STATE:
                        d = self.__dict__.setdefault(name, {})
                        if name in state:
                            d[region] = state[name]
                        else:
                            d.pop(region, None)
                    for name, new in caches.items():
                        self.__dict__.setdefault(name, {}).update(new)
                    yield out
        finally:
            _PAR_CTX = None

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


_PAR_CTX = None


def _par_solve_region(region):
    """Worker process: one region's solves (SupplyModule._solve_region) with the state forked from the parent;
    returns the result, the regional model (without the shared environmental module), the region's land and
    nitrogen-price state and the cache entries it added."""
    sm, pol, ps, verbose = _PAR_CTX
    before = {n: set(sm.__dict__.get(n) or ()) for n in sm._PAR_CACHES}
    out = sm._solve_region(region, pol, ps, verbose)
    model = sm._models.get(region)
    if model is not None:
        model.__dict__.pop("_env_for_surplus", None)     # this process's copy, re-attached in the parent
    state = {n: sm.__dict__[n][region] for n in sm._PAR_STATE if region in (sm.__dict__.get(n) or {})}
    caches = {n: {k: v for k, v in (sm.__dict__.get(n) or {}).items() if k not in before[n]} for n in sm._PAR_CACHES}
    return out, model, state, caches


def _merge_relief(model) -> dict:
    """N relief per activity unit for the accounts: ammonia technologies + inhibitors on manure."""
    out = dict(getattr(model, "_animal_n_relief", None) or {})
    for a, v in (getattr(model, "_manure_ni_relief", None) or {}).items():
        out[a] = out.get(a, 0.0) + float(v)
    return out


_FERT_SIDE_TAB = None
_YIELD_ELAS = None


def fert_side_value(region: str, tech: str, item: str):
    """CAPRI's literature-review side effect (p_litRevFertTechs) for a model region, or None
    (capri_data/2017/abatement/fert_side_effects.csv, tools/build_fert_side_effects.py)."""
    global _FERT_SIDE_TAB
    if _FERT_SIDE_TAB is None:
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "fert_side_effects.csv"
        _FERT_SIDE_TAB = ({(r.region, r.technology, r.item): float(r.value) for r in pd.read_csv(f).itertuples()}
                          if f.exists() else {})
    return _FERT_SIDE_TAB.get((region, tech, item))

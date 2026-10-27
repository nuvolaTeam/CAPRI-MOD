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
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import json
import multiprocessing
import os
import warnings
from pathlib import Path

from capri_mod.supply.capri_pmp import (
    ELAS_CAP, share_term, ARABLE_ACTIVITIES, EPRD_TO_GRP,
)
from capri_mod.params import param, param_table
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS,
)
from capri_mod.data.definitions import MS_CODE, capri_ms
from capri_mod.csvio import read_csv


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

#: CAPRI's fixed production activities, held at their data level (supply/prep_sim.gms l. 250: v_actLevl.FX for FACT;
#: sets.gms l. 2317 FACT = MFCACT + OANI, l. 131 MFCACT = OOIL, OIND, FallGr, NURS, FLOW, OCRO, NECR). NURS, FLOW and
#: OCRO were endogenous here until 23 October 2026 (found by the proxy audit: they had no CAPRI elasticity)
FIXED_ACTIVITIES = ("OOIL", "OIND", "NURS", "FLOW", "OCRO", "OANI")
#: an activity whose level at the calibration point is at most this (1000 ha / 1000 head) has no level: CAPRI has no
#: variable for it (v_actLevl exists where p_technFact(..,"LEVL",..) is set); the bounds hold it at zero
#: (setting supply.absent_activities_fixed) and the rules that refer to it (CAP greening) leave it out
ABSENT_LEVEL = 1e-8

#: CAPRI p_OverFertMarkUp (envind/ghgMiti.gms): corrects the over-fertilisation factor
#: for the additive need factor and manure availability
OVERFERT_MARKUP = param("OVERFERT_MARKUP")
_OVERFERT = None
_OVERFERT_WARNED = False


def overfert_factor(region: str):
    """CAPRI's over-fertilisation factor x = v_cropNutNeedMultFact(ru, NITF, "T") for a model
    region (capri_data/2017/environment/crop_nut_need_mult_fact_2030.csv, built by
    tools/build/build_overfert_factors.py from CAPRI's priFertDist results), or None when the data
    is not available - then CAPRI's limits on the fertiliser technologies (Tot_MitFert_ and the
    regional maximum shares) cannot be applied, which is warned once."""
    global _OVERFERT, _OVERFERT_WARNED
    if _OVERFERT is None:
        _OVERFERT = {}
        f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "crop_nut_need_mult_fact_2030.csv"
        if f.exists():
            for r in read_csv(f).itertuples(index=False):
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
            for r in read_csv(f).itertuples(index=False):
                _FERT_OPT.setdefault(r.region, []).append(r)
        else:
            import warnings as _w
            _w.warn("fert_options_jul15.csv missing: no fertiliser-efficiency options")
    return _FERT_OPT


def _spec_fingerprint(spec, **extra) -> str:
    """A digest of a regional NLP's calibration problem (every array, number and label of the spec, and the base
    point): two calibrations of equal digests solve the same problem."""
    import hashlib
    h = hashlib.sha1()

    def feed(o):
        if isinstance(o, np.ndarray):
            a = np.ascontiguousarray(o)
            h.update(str((a.dtype.str, a.shape)).encode()); h.update(a.tobytes())
        elif isinstance(o, (pd.Series, pd.DataFrame)):
            feed(o.to_numpy()); feed(list(map(str, o.index)))
            if isinstance(o, pd.DataFrame):
                feed(list(map(str, o.columns)))
        elif isinstance(o, dict):
            h.update(b"{")
            for k in sorted(o, key=repr):
                h.update(repr(k).encode()); feed(o[k])
            h.update(b"}")
        elif isinstance(o, (list, tuple, set, frozenset)):
            h.update(b"[")
            for x in (sorted(o, key=repr) if isinstance(o, (set, frozenset)) else o):
                feed(x)
            h.update(b"]")
        elif isinstance(o, (float, np.floating)):
            h.update(np.float64(o).tobytes())
        else:
            h.update(repr(o).encode())
    feed(spec); feed(extra)
    return h.hexdigest()


def young_animal_table() -> dict:
    """CAPRI's young-animal coefficients per model region (calves, young cattle, cows, piglets, lambs): pooled across the
    sexes (young_animals_2017.json, the default) or per sex as CAPRI's balances (young_animals_by_sex_2017.json) with
    the cattle member splits (RegionalSupplyModel.use_cattle_member_splits; tools/build/build_young_animals.py)."""
    global _YANI
    by_sex = bool(getattr(RegionalSupplyModel, "use_cattle_member_splits", False))
    if _YANI is None or _YANI[0] != by_sex:
        import json as _json
        from pathlib import Path as _P
        name = "young_animals_by_sex_2017.json" if by_sex else "young_animals_2017.json"
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "supply" / name
        _YANI = (by_sex, _json.load(open(f))["regions"] if f.exists() else {})
    return _YANI[1]


def active_technologies():
    """CAPRI's active mitigation technologies of the Green Deal reference (activeTech,
    capri_data/2017/abatement/active_technologies.csv, tools/build/build_active_technologies.py), or
    None when the file is missing (then every option with data is available, with a warning)."""
    global _ACTIVE_TECH
    if _ACTIVE_TECH is None:
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "active_technologies.csv"
        if f.exists():
            _ACTIVE_TECH = set(read_csv(f)["technology"].str.upper())
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
    s = read_csv(f, index_col=0)[col].dropna()
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
    # tools/build/build_livestock_output_coef.py. Used for gross_output in place of
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
    #: CAPRI's input costs the Green Deal targets change (build_plant_protection_cost.py): plap, inpo, fert, eful
    #: (EUR/ha by crop) and inpo_toin_share (animals)
    input_costs_ha: Optional[pd.DataFrame] = None
    #: the simulation year (the projection's market year; None: the base year)
    sim_year: Optional[int] = None
    #: CAPRI's catch crops (catc_share_2030, catc_cost_eur_ha, biofix_t_n_ha) and winter cover shares by crop
    cover_crops: Optional[pd.Series] = None
    winter_cover_share: Optional[pd.DataFrame] = None
    livestock_cost_coef: Optional[pd.Series] = None
    livestock_output_value_coef: Optional[pd.Series] = None
    livestock_premium_coef: Optional[pd.Series] = None     # CAPRI PRME per model head
    capri_level_ratio: Optional[pd.Series] = None          # model herd units per CAPRI LEVL unit (activity bounds)
    livestock_feed_coef: Optional[pd.Series] = None
    fodder_balance: Optional[dict] = None
    land_market: Optional[dict] = None
    #: CAPRI's land rents (EUR/ha) by land type, {"ARAC", "FRUN", "GRAS"}, at the market year's calibration point
    land_rents: Optional[dict] = None
    #: CAPRI's 2030 PMP matrix of the crops, {(act_i, act_j): g} (K61); Q_ij = g / sqrt(x_i x_j) at the base levels
    pmp_capri: Optional[dict] = None
    #: activities with a level but no CAPRI calibration (no CAPRI PMP term and no CAPRI elasticity): held at their
    #: level, as CAPRI holds activities it does not calibrate (23 October 2026: before, literature elasticities)
    uncalibrated: Optional[frozenset] = None

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

    #: off-diagonal structure: "capri" (CAPRI's crop groups only) or "none" (diagonal only; see calibrate)
    CROSS_TERMS = setting("supply.pmp_cross_terms")

    def __init__(self, activities: List[str], supply_elasticities: pd.Series,
                 share_terms: Optional[pd.Series] = None,
                 cross_group_terms: Optional[dict] = None,
                 cross_price_elas: Optional[dict] = None,
                 capri_g: Optional[dict] = None):
        self.activities = activities
        # CAPRI's 2030 PMP matrix of the crops (K61), {(act_i, act_j): g}: replaces the elasticity-calibrated block
        self.capri_g = capri_g or {}
        self.n_capri_acts = 0
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
        x0 = base_levels.reindex(self.activities).values.astype(float)
        if not np.all(np.isfinite(x0)):
            raise ValueError("PMP calibration: base levels missing for "
                             + ", ".join(a for a, v in zip(self.activities, x0) if not np.isfinite(v)))
        r  = net_revenues.reindex(self.activities).fillna(0.0).values

        if shadow_prices_lp is None:
            # no resource duals given: the base is a first-order point of the activities' own terms (the land rents
            # enter as the land rows' multipliers, CAPRI's calibration rents; before 23 October 2026 a proxy of 1% of
            # net revenue, at least 1, stood in here - no proxies)
            lam = np.zeros(n)
        else:
            lam = shadow_prices_lp.reindex(self.activities).fillna(0.0).values

        # Build diagonal Q based on supply elasticities
        # FOC of profit max: r - Qx - f = 0 → at x0: f = r - Qx0
        # Qii calibrated so that ∂x_i/∂p_i = eps_i * x0_i / p_i = 1/Qii
        # no literature defaults (23 October 2026): an activity without a CAPRI elasticity (NaN) gets the inert
        # curvature 1 below and is held at its level (RegionalSupplyData.uncalibrated) unless CAPRI's PMP terms cover it
        eps = self.supply_elasticities.reindex(self.activities).values.astype(float)
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
        denom = eps_capped * x0_guard * st          # CAPRI's share term, 1 - 0.2 sqrt(share) >= 0.8
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

        # Off-diagonal terms for substitution effects: CAPRI's own cross-group terms (p_pmpQuadPact) and PELA
        # cross-price elasticities, capped at rho_base x sqrt(Q_ii Q_jj)
        rho_base = 0.05
        pact = self.cross_group_terms          # {(grp1, grp2): value} or {}
        n_real = 0
        # CAPRI's structure (supply_model.gms QUADRA_ with GRPLEVL_, p_useCropSpecificQMatrix 0): cross terms only
        # through the crop groups' levels (EPRD_TO_GRP: CERE, CER2, OILS, OARA, FARA), so only between two crops that
        # are both in a group; "for fruits & vegetables, permanent crops, grassland and the animal sectors, only
        # diagonal terms" (CAPRI documentation, ch. 5). Before 21 October 2026 every other pair carried a uniform term
        # (0.05 / (n - 1) x sqrt(Q_ii Q_jj)) and PELA cross terms outside the groups (all 312 permanent-crop pairs of
        # ES61): capri-mod's, not CAPRI's (removed 27 October 2026). The linear terms are computed after
        # (f = r - Q x0 - lambda), so the base still calibrates.
        # CROSS_TERMS: "capri" (default) or "none" (diagonal only: CAPRI's decomposition experiment, 2008
        # documentation sect. 7.3, tools/check/pmp_cross_term_check.py)
        mode = str(getattr(type(self), "CROSS_TERMS", "capri"))
        # With CAPRI's own PMP terms (pmp_source capri2030 or recipe, below) the covered crops take CAPRI's matrix,
        # cross terms included, and a crop CAPRI has no terms for in the region has none in CAPRI's QUADRA_ either:
        # no cross terms are built here. Until 23 October 2026 such crops of one group kept a PELA cross elasticity or
        # a scaled p_pmpQuadPact term capped at 0.05 (5 pairs in DEA5, EL65, ITH4, PT16 and PT17; PROXY_AUDIT S065).
        skip_cross = bool(self.capri_g)
        for i in range(n):
            if mode == "none" or skip_cross:
                break
            gi = EPRD_TO_GRP.get(self.activities[i])
            for j in range(i + 1, n):
                gj = EPRD_TO_GRP.get(self.activities[j])
                if not (gi and gj):
                    continue
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
                    continue                       # no group term for the pair: none in CAPRI's QUADRA_ either
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

        # CAPRI's own PMP matrix of the crops at its 2030 baseline calibration (pmp_source "capri2030", K61): technology
        # terms and the crop groups' terms on the groups' levels (QUADRA_ / GRPLEVL_), collapsed to the model's activities
        # and territory (tools/build/build_pmp_capri_2030.py). It replaces the elasticity-calibrated block of the crops it
        # covers, cross terms included; activities it does not cover (animals, crops CAPRI has no terms for in the
        # region) keep theirs, with no cross terms to the covered ones. Scaled to the model region's base levels,
        # Q_ij = g_ij / sqrt(x_i x_j): the region's relative response equals CAPRI's for its territory. The linear
        # terms below are recalibrated, so the base is reproduced.
        if self.capri_g:
            cov = [i for i, a in enumerate(self.activities)
                   if (a, a) in self.capri_g and x0[i] > 1e-3 and self.capri_g[(a, a)] > 0]
            if cov:
                Q[cov, :] = 0.0
                Q[:, cov] = 0.0
                for i in cov:
                    for j in cov:
                        g = self.capri_g.get((self.activities[i], self.activities[j]))
                        if g is not None:
                            Q[i, j] = g / np.sqrt(x0[i] * x0[j])
                Q[np.ix_(cov, cov)] = 0.5 * (Q[np.ix_(cov, cov)] + Q[np.ix_(cov, cov)].T)
            self.n_capri_acts = len(cov)

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
    #: (livestock_cost_coef.csv), with revenue on CAPRI's total output (TOOU): with market revenue (MREV), which
    #: leaves out the calves breeders produce, suckler cows would show -1,134% margins.
    #: a warm-started NLP solution more than this much (relative) worse than the last iteration's objective is checked
    #: against the solves from the previous point and the standard start (KNOWN_ISSUES K75)
    nlp_warm_check = setting("supply.nlp_warm_check")

    #: CAPRI's land market and the grassland allowance (capri_mod/settings: supply.*)
    use_land_market = setting("supply.use_land_market")
    grassland_allowance = setting("supply.grassland_allowance")
    #: fodder band rows (setting supply.fodder_band)
    fodder_band = setting("supply.fodder_band")

    def _land_of(self, kind: str) -> float:
        """The region's land of a type (1000 ha; capri_data land_availability.csv, CAPRI's data). Missing data stop the
        run (no fallback: the former 200 / 30 / 80 kha stand-ins were never reached and are gone, 23 October 2026)."""
        land = getattr(self.data, "land", None)
        v = land.get(kind) if land is not None else None
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = float("nan")
        if not np.isfinite(v):
            raise ValueError(f"{self.data.region_id}: no {kind} land in land_availability.csv")
        return v

    def _techs_inside(self) -> bool:
        """CAPRI's ammonia technologies are decision variables of the regional model (technologies on, rations
        available)."""
        return bool(getattr(self, "feed_rations", None) or {})

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
        region (capri_data/2017/supply/young_animals_2017.json, tools/build/build_young_animals.py)."""
        rec = young_animal_table().get(self.data.region_id, {})
        fac = getattr(self.data, "young_value_factor", None) or {}
        if not fac:
            return rec
        return {g: {**r, "value_eur_head": float(r.get("value_eur_head", 0.0) or 0.0) * float(fac.get(g, 1.0))}
                for g, r in rec.items()}

    #: compute each region's response to the young-animal prices from its solved NLP (K65): None (default) with the
    #: cattle member splits only (CAPRIModel.use_yani_exact); True / False force it
    yani_exact_response = setting("young_animals.use_exact", tri_state)

    def young_animal_columns(self, cols, goods=None):
        """(goods, n, v): the net young-animal production per unit of each column of the regional QP (n, columns x
        goods: produce - use of the activities; for the cattle splits' columns z, (produce x dprod, with the member
        splits) - use x duse (dyoung for the pooled goods)), and the value per head v (EUR, with the market year's value
        factor) - exactly as the young-animal prices enter the objective (_apply_young_animal_prices, _cattle_columns)
        and the balances (CAPRIModel._young_animal_balance)."""
        coefs = self._young_animal_coefs()
        goods = sorted(coefs) if goods is None else list(goods)
        ct = getattr(self.data, "cattle_intensity", None) or {}
        ms = bool(getattr(type(self), "use_cattle_member_splits", False))
        n = np.zeros((len(cols), len(goods))); v = np.zeros(len(goods))
        idx = {c_: j for j, c_ in enumerate(cols)}
        for gi, g in enumerate(goods):
            rec = coefs.get(g) or {}
            v[gi] = float(rec.get("value_eur_head", 0.0) or 0.0)
            pr, us = rec.get("produce", {}) or {}, rec.get("use", {}) or {}
            for a in set(pr) | set(us):
                if a in idx:
                    n[idx[a], gi] += float(pr.get(a, 0.0) or 0.0) - float(us.get(a, 0.0) or 0.0)
            for j, lab in enumerate(cols):
                if not str(lab).startswith("cattle_z_"):
                    continue
                key = str(lab)[len("cattle_z_"):]
                di = ct.get(key)
                if di is None:
                    continue
                a_ = key.split(":")[0]
                cu = float(us.get(a_, 0.0) or 0.0)
                if cu:
                    du = di.get(f"duse_{g}_rel") if ms else None
                    du = float(di["dyoung_rel"]) if du is None or du != du else float(du)
                    n[j, gi] -= cu * du
                cp = float(pr.get(a_, 0.0) or 0.0) if ms else 0.0
                dp = di.get(f"dprod_{g}_rel")
                if cp and dp is not None and dp == dp:
                    n[j, gi] += cp * float(dp)
        return goods, n, v

    def _yani_response(self, nlp, res, cols):
        """{"goods", "dnet"}: dnet[g', g] = the change of the region's net young-animal balance of g' (1000 head) per
        unit change of the price ratio of g, from the solved NLP's sensitivity (CapriRegionalNLP.response) - the
        Jacobian of the young-animal markets' price update, constraints included."""
        goods, n, v = self.young_animal_columns(cols[:nlp.n0])
        if not len(goods) or not np.any(n):
            return None
        dy = nlp.response(res, -n * v[None, :])
        return {"goods": goods, "dnet": n.T @ dy}

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

    def _ef_mineral_lea(self) -> float:
        """t CO2-eq per t of mineral N bought in the indirect N2O of its runoff and leaching (CAPRI GWPN2OLEA_ a and c,
        capri_mod/supply/n_leaching.py): (RunTot_NETF + (1 - GasRunTot_NETF - EXPPRD/IMPORT) x L) x EF5 x 44/28, at the
        leaching share of CAPRI's Green Deal reference (REGISTERED: the options' effect on the share is in the accounts,
        not in this coefficient); 0 without CAPRI's data."""
        c_ = self.__dict__.get("_ef_lea_cache")
        if c_ is None:
            from capri_mod.supply import n_cascade as _nc, n_leaching as _nl
            from capri_mod.environmental.environmental_module import GWP_N2O
            rs = _nl.capri_region(self.data.region_id)
            d = _nl.load().get(rs) if rs else None
            g = _nc.load()[1].get(rs, {}) if rs else {}
            c_ = 0.0
            if d and d.get("exp_imp") is not None:
                L = d.get("leach_ini") if d.get("leach_ini") is not None else (d.get("leach_base") or 0.0)
                nf = _nc.netf(g, float(g.get("run_surf", 0.0)))
                c_ = max(0.0, nf["RunTot"] + (1.0 - nf["GasRunTot"] - float(d["exp_imp"])) * float(L)) \
                    * _nl.EF5 * 44.0 / 28.0 * GWP_N2O
            self._ef_lea_cache = c_
        return c_

    @staticmethod
    def _ef_nh3_n2o() -> float:
        """t CO2-eq per t of NH3-N volatilised from manure (the accounts' N2O_IND, CAPRI N2OAMM)."""
        from capri_mod.environmental.environmental_module import EF_SOIL_N2O_INDIRECT, GWP_N2O
        return EF_SOIL_N2O_INDIRECT * 44.0 / 28.0 * GWP_N2O

    def _need_yf(self, a, y0, yc, nut: str = "N") -> float:
        """The crop's nutrient need per ha at yield yc relative to its base yield y0, CAPRI's rule
        (capri_mod.fert.npk.need_yield_factor: the main-output part linear in the yield, the straw part with the
        scenario's yields before the price response)."""
        from capri_mod.fert.npk import need_yield_factor
        pf = float((getattr(self, "_yield_price_factor", None) or {}).get(a, 1.0))
        ys = float(yc) / pf if pf > 0 else None
        return need_yield_factor(self.data.region_id, a, float(y0), float(yc), ys, nut)

    def _yields_scen_now(self):
        """The crops' current yields without this solve's price response (the scenario's shifted yields), for the
        environmental accounts' need factors; None without a price response."""
        pf = getattr(self, "_yield_price_factor", None) or {}
        if not pf or not hasattr(self.data.yields, "get"):
            return None
        return {a: float(self.data.yields.get(a)) / f for a, f in pf.items()
                if f > 0 and self.data.yields.get(a) is not None}

    def _crop_mineral_now(self) -> dict:
        """Crops' mineral N per ha at this solve (kg N/ha): base rate x fertiliser intensity x CAPRI's need factor
        of the yield (`_need_yf`), the same terms the N row uses (`_mineral_row`), for the fertiliser options without
        an N row."""
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
            _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
            r_ = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
            if r_ > 0:
                out[a] = r_
        return out

    def _fert_tax_terms(self, ft) -> dict:
        """CAPRI's emission tax on mineral N and the fertiliser options (Sprint 9l), in the regional model's 1000 EUR:
        "m" per t of mineral N (the accounts' soil N2O, direct + volatilised x indirect, and the indirect N2O of its
        runoff and leaching, _ef_mineral_lea); "h" per unit of adopted area
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
        return {"m": tax * (ef_d + ef_v + self._ef_mineral_lea()) / 1000.0, "h": h}

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
        if subs and all(_at.cascade_data(s) is not None for s in subs):
            # CAPRI's full cascade (n_cascade.py) gives CAPRI's losses per unit of excreted N as they are (checked
            # against its Green Deal reference run): the N per unit of the loss fraction is the manure N itself
            return mN
        L0 = sum(s["w"] * s["mrel"] * _at.loss(s, _at.initial(s)) for s in subs)
        return (mN * f / L0) if L0 > 0 else 0.0

    # K63: the ammonia options are held at their base shares in a regional NLP solve without a policy incentive on N
    # (no N-surplus row, no mineral cap, no emission tax), and re-solved so where the N-surplus row is slack

    def _amm_incentive(self, labels) -> bool:
        return ("N_balance" in labels or "mineral_N" in labels
                or float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0)

    def _tech_list(self):
        """Ammonia technologies for the regional model (CAPRI v_Miti): one entry per sub-activity
        and option. The loss cascade couples the two groups (N reaching the field); the N saved
        per unit of share is linearised at the shares of the previous solve (successive
        linearisation across outer iterations; at convergence CAPRI's relation holds)."""
        from capri_mod.supply import ammonia_techs as _at
        ctx = self._amm_context()
        if ctx is None:
            return []
        techs, man_d, nh3, sub = ctx
        wc0, wc1 = self._winter_cover_shares()
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
                d = _at.marginal(s, sh, wc1)
                npl = sc * s["mrel"]
                # N saved per unit of the sub-activity at the linearisation point, relative to the base shares (exact
                # cascade): with it the regional model's relief is the TANGENT of CAPRI's cascade at that point,
                # rel0 + ret x (share - share there), so at a converged point the N saved is CAPRI's exactly (before,
                # ret x (share - base share) left out the cross term of the two option groups: the NLP check,
                # tools/nlp_check, found CAPRI's N balance violated by 8-365 t N in the five regions checked)
                rel0 = npl * (_at.loss(s, _at.initial(s), wc0) - _at.loss(s, sh, wc1))
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


    def _npk_spec(self, n_cols, x_start, A=None, labels=None):
        """CAPRI's crop nutrient balance of this region for the NLP form (capri_regional_nlp, block "fertilisation";
        data capri_mod/fert/npk.py): per nutrient (N, P, K) the crop groups with their need, permanent crops' own
        residues and the inner model's priors, the manure applied and the arable residue pool as linear functions of
        the columns, CAPRI's efficiencies, availability (endogenous for N: fert/endoManAvail.gms) and unit value.
        Need per ha: CAPRI's 2030 need (NITF/PHOF/POTF) x CAPRI's need factor of the yield (_need_yf, per nutrient)
        x kappa, kappa the region's need
        factor that closes NUTNED_ at base with the base mineral use (CAPRI's v_cropNutNeedMultFact, calibrated in
        the base and fixed in simulation; here one per region and nutrient). None outside CAPRI's EU data."""
        from capri_mod.fert.npk import NPKData, NUTRIENTS, PERM_NGRP, endo_slope
        from capri_mod.fert.inner_fert_dist import FERT_POST_ACCURACY
        env_ = getattr(self, "_env_for_surplus", None)
        if env_ is None:
            return None
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        inner = env_.__dict__.get("_inner_fert")
        if inner is None:
            inner = env_._inner_fert = InnerFertDist()
        rid = self.data.region_id
        cr = inner.capri_region(rid)
        if cr is None:
            return None
        D = NPKData.get()
        acts = list(self.acts); n = len(acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        yb = env_._cached_row("yields", rid) or {}
        ycur = self.data.yields
        sqn = {nut_: {} for nut_ in NUTRIENTS}      # CAPRI's need factor of the yield, per nutrient (_need_yf)
        for a in acts:
            if a in CROPS:
                y0 = float(yb.get(a, 0.0) or 0.0); yc = float(ycur.get(a, y0) or 0.0) if hasattr(ycur, "get") else y0
                for nut_ in NUTRIENTS:
                    sqn[nut_][a] = self._need_yf(a, y0, yc, nut_) if (y0 > 0 and yc > 0) else 1.0
        shares = D.crop_shares(cr)
        # manure N applied per unit of each column: the environmental accounts' own (excreted less housing and storage
        # losses, net of the base trade shares, imports per ha of crops), as the inner model reads it
        mint = dict(getattr(self, "_n_intensity", {}) or {})
        unitsN = {a: env_.unit_nitrogen_balance(a, ycur, rid, {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")},
                                           yields_scen=self._yields_scen_now())
                  for a in acts}
        eN = np.array([float(unitsN[a].get("n_manure_applied", 0.0)) for a in acts])
        pool = [int(p_) for p_ in (getattr(self, "_pool_cols", None) or []) if int(p_) < n_cols]
        lt = list(getattr(self, "_land_types_used", None) or [])
        land_cols = [n + lt.index(t) for t in ("ARAC", "GRAS", "FRUN") if t in lt and n + lt.index(t) < n_cols] \
            if len(lt) and n + len(lt) <= n_cols else []
        crop_cols = [j for j, a in enumerate(acts) if a in CROPS]
        land0 = float(sum(xb[j] for j in crop_cols)) if not land_cols else \
            float(sum(np.asarray(x_start, float)[j] for j in land_cols))
        kap = self.__dict__.setdefault("_npk_kappa", {})
        out = {"capri_region": cr, "nutrients": {}, "land_cols": land_cols, "crop_cols": crop_cols}
        # the split columns: the grassland split moves area from CAPRI's GRAI to GRAE (z = GRAE - base GRAE, each of the
        # two half the grassland at base), so the GRAS groups' need changes by z x (need GRAE - need GRAI); the animal
        # split and option columns change their animal's manure in the proportion their manure coefficient bears to the
        # animal's (the manure-application row, else its N row), which reaches ManureNPK_
        colsl = self._aug_col_labels(n_cols)
        j_gz = colsl.index("grass_z") if "grass_z" in colsl else None
        man_split = []
        if A is not None and labels is not None:
            ref_row = next((labels.index(l_) for l_ in ("manure_application", "N_balance") if l_ in labels), None)
            if ref_row is not None:
                for j, lab in enumerate(colsl):
                    a_ = None
                    if lab == "dairy_z":
                        a_ = "DCOW"
                    elif lab.startswith("cattle_z_"):
                        a_ = lab[len("cattle_z_"):].split(":")[0]
                    elif lab.startswith("genet_z_"):
                        a_ = lab[len("genet_z_"):].split("_")[0]
                    if a_ in acts and float(A[ref_row, acts.index(a_)]) != 0.0:
                        man_split.append((j, a_, float(A[ref_row, j]) / float(A[ref_row, acts.index(a_)])))
        for nut in NUTRIENTS:
            sq = sqn[nut]
            R = D.region(cr, nut); P = D.priors(cr, nut)
            if R is None or P is None:
                continue
            eff = float(R.mine_eff) if R.mine_eff == R.mine_eff else 1.0
            g0 = float(R.excr_avail) if R.excr_avail == R.excr_avail else 0.0
            gc = float(R.cres_avail) if R.cres_avail == R.cres_avail else 0.0
            need = np.zeros(n); own = np.zeros(n); poolc = np.zeros(n); mine0 = np.zeros(n)
            for j, a in enumerate(acts):
                if a not in CROPS:
                    continue
                need[j] = D.crop_coef(cr, nut, a, "need_kg_ha")
                own[j] = D.crop_coef(cr, nut, a, "own_kg_ha")
                poolc[j] = D.crop_coef(cr, nut, a, "pool_kg_ha")
                mine0[j] = float(env_._base_mineral_rate(rid, a)) if nut == "N" else D.crop_coef(cr, nut, a, "mine_kg_ha")
            if nut == "N":
                man = eN.copy()
            else:
                # manure P2O5 / K2O per head (CAPRI 2017 totals / the model's herds), applied in the region in the
                # proportion CAPRI's 2030 reference applies it (net of the base net exports, ManureNPK_)
                man = np.array([D.manure_per_head(rid, nut, a) if a in ANIMALS else 0.0 for a in acts])
                # with manure trade off nothing leaves the region: all manure P / K applied, as for N
                if bool(getattr(getattr(self, "_env_for_surplus", None), "manure_trade_on", True)):
                    man = man * self._npk_applied_ratio(cr, nut)
            # kappa: NUTNED_ summed over the groups at base (all flows interior), the need net of the permanent
            # crops' own residues scaled together (REGISTERED: CAPRI's multiplier is on the need alone; with the model's
            # base levels and CAPRI's 2030 coefficients, scaling the need alone left the permanent groups' own residues
            # above their need in some regions, where NUTNED_ has no solution with positive flows):
            #   kappa x (need0 - gc x own0) = eff x M0 + g0 x E0 + gc x C0
            key = (cr, nut)
            if key not in kap:
                need0 = float(need @ xb); M0 = float(mine0 @ xb); E0 = float(man @ xb)
                C0 = float(poolc @ xb); O0 = float(own @ xb)
                net0 = need0 - gc * O0
                kap[key] = (eff * M0 + g0 * E0 + gc * C0) / net0 if net0 > 0 else 1.0
                kap[(key, "base")] = dict(need0=need0, M0=M0, E0=E0, C0=C0, O0=O0, land0=land0)
            k = kap[key]
            base = kap[(key, "base")]
            m0E = 1000.0 * base["E0"] / base["land0"] / 1000.0 if base["land0"] > 0 else 0.0   # kg/ha (t / kha)
            groups = []
            for gname, row in P.iterrows():
                crops = [(j, float(shares.get(acts[j], {}).get(gname, 0.0))) for j in crop_cols
                         if float(shares.get(acts[j], {}).get(gname, 0.0)) > 0]
                Aref = sum(sh * xb[j] for j, sh in crops)
                if Aref <= 1e-6:
                    continue
                perm = gname in PERM_NGRP
                modes = {}
                acc = {}
                ov = (getattr(self, "_npk_prior_override", None) or {}).get(nut)
                for s_, colname in (("MINE", "mine_kg_ha"), ("EXCR", "excr_kg_ha"), ("CRES", "cres_kg_ha")):
                    v_ = float(row[colname]) if row[colname] == row[colname] else 0.0
                    if ov is not None:
                        v_ = float(ov.get((gname, s_), 0.0)) / Aref        # the region's own calibrated posterior
                    if v_ > 0 and not (s_ == "CRES" and perm):
                        modes[s_] = v_ * Aref                               # t
                        acc[s_] = float(row["accuracy"]) if ov is None else FERT_POST_ACCURACY
                if not modes:
                    continue
                needl = [(j, sh * k * need[j] * sq.get(acts[j], 1.0)) for j, sh in crops if need[j] > 0]
                if j_gz is not None and "GRAS" in acts:
                    sh_g = float(shares.get("GRAS", {}).get(gname, 0.0))
                    dn = D.crop_coef(cr, nut, "GRAE", "need_kg_ha") - D.crop_coef(cr, nut, "GRAI", "need_kg_ha")
                    if sh_g > 0 and dn != 0.0:
                        needl.append((j_gz, sh_g * k * dn * sq.get("GRAS", 1.0)))
                groups.append({"g": gname, "perm": perm, "acc": acc, "modes": modes, "crops": crops,
                               "need": needl,
                               "own": [(j, sh * k * own[j]) for j, sh in crops if perm and own[j] > 0], "Aref": Aref})
            if not groups:
                continue
            # coverage check: the groups' need and own residues at base against the region's (kappa's) totals
            cov_need = sum(sum(v * xb[j] / sq.get(acts[j], 1.0) for j, v in g_["need"] if j < n) for g_ in groups)
            cov_own = sum(sum(v * xb[j] for j, v in g_["own"]) for g_ in groups)
            self.__dict__.setdefault("_npk_cov", {})[nut] = (cov_need, k * base["need0"], cov_own, base["O0"])
            Ecols = [(j, float(man[j])) for j in range(n) if man[j] != 0.0]
            if nut == "N":
                Ecols += [(j, float(man[acts.index(a_)]) * r_) for j, a_, r_ in man_split if man[acts.index(a_)] * r_ != 0.0]
            if pool and nut == "N" and len(pool) == 2:
                Ecols += [(pool[0], -1.0), (pool[1], 1.0)]
            elif pool and len(pool) == 2:
                # traded manure carries P and K in the region's manure proportions (REGISTERED: CAPRI trades MANP and
                # MANK as products of their own)
                rN = float(eN @ xb); rX = float(man @ xb)
                f_ = rX / rN if rN > 0 else 0.0
                Ecols += [(pool[0], -f_), (pool[1], f_)]
            out["nutrients"][nut] = {
                "groups": groups, "E": Ecols, "C": [(j, float(poolc[j])) for j in range(n) if poolc[j] > 0],
                "eff": eff, "g0": g0, "gc": gc, "slope": endo_slope(g0, m0E, nut), "m0E": m0E,
                "price": float(R.uvag_eur_t) if R.uvag_eur_t == R.uvag_eur_t else 0.0, "kappa": k,
                "M0": base["M0"]}
        out["dual_bound"] = float(getattr(self, "_npk_dual_bound", 10.0) or 10.0)
        return out if out["nutrients"] else None

    #: CAPRI's CAP 2014-2020 greening in the NLP form (permGrasGreening_, ecoSetAside_, cropDivGreening_), as in
    #: CAPRI's 2030 reference (pol_input/cap_after_2014/ref.gms)
    cap_greening = setting("supply.cap_greening")
    #: annual crops (sets.gms annualCrops) of the model and their crop-diversification groups (cropDivGrps: each
    #: annual crop alone, MAIS = grain and silage maize, OSET = set-aside and fallow)
    CROPDIV_GROUPS = {"SWHE": "SWHE", "DWHE": "DWHE", "RYEM": "RYEM", "BARL": "BARL", "OATS": "OATS", "OCER": "OCER",
                      "PARI": "PARI", "RAPE": "RAPE", "SUNF": "SUNF", "SOYA": "SOYA", "OOIL": "OOIL", "OIND": "OIND",
                      "FLOW": "FLOW", "PULS": "PULS", "POTA": "POTA", "SUGB": "SUGB", "TEXT": "TEXT", "TOBA": "TOBA",
                      "TOMA": "TOMA", "OVEG": "OVEG", "OFOD": "OFOD", "CORN": "MAIS", "MAIF": "MAIS", "SETA": "OSET"}

    @staticmethod
    def _npk_base_alloc(nlp0, npk, yb):
        """The fertilisation block's N allocation at the calibration point, per ha of each group (kg/ha), with the
        base purchases and land: the baseline allocation the Green Deal caps are taken from."""
        if not npk or "N" not in (npk.get("nutrients") or {}) or not nlp0.fert:
            return None
        fo = nlp0.fert_outputs(nlp0.cal_point)
        o = fo["N"]
        yb = np.asarray(yb, float)
        per_ha_nut = {}
        for nut, d_ in npk["nutrients"].items():
            if nut not in fo:
                continue
            ar = {g_["g"]: float(sum(sh * yb[j] for j, sh in g_["crops"])) for g_ in d_["groups"]}
            per_ha_nut[nut] = {(g, s_): v / ar[g] for (g, s_), v in fo[nut]["flows"].items() if ar.get(g, 0.0) > 0}
        area = {g_["g"]: float(sum(sh * yb[j] for j, sh in g_["crops"])) for g_ in npk["nutrients"]["N"]["groups"]}
        per_ha = per_ha_nut["N"]
        lc = npk.get("land_cols") or npk.get("crop_cols") or []
        return {"per_ha": per_ha, "per_ha_nut": per_ha_nut, "area": area, "capri_region": npk.get("capri_region"),
                "purchase": o["purchase"], "land": float(sum(yb[j] for j in lc))}

    #: CAPRI organic_minfert_redu.gms: groups below 0.01 t/ha of mineral N at baseline keep the baseline as maximum
    ORGANIC_SMALL_MINE_KG_HA = 10.0
    #: CAPRI organic_minfert_redu.gms: limCres maximum = 1.2 x the baseline's residues per ha (all nutrients)
    ORGANIC_LIMCRES_FACTOR = 1.2

    def _npk_organic_cap(self, npk):
        """CAPRI's organic area target on the fertilisation block (pol_input/greendeal/organic_area.gms ->
        organic_minfert_redu.gms, 'region_and_crop'): each crop group's mineral N per ha at most its baseline
        allocation x (1 - the group's organic conversion), as CAPRI's "f2f" regulation (beta density, mode 0.75 x max,
        accuracy 0.25); groups below 10 kg/ha at baseline capped at the baseline; "limCres" on residues for every
        nutrient at 1.2 x the baseline per ha (mode at the baseline, accuracy 10). The group's conversion is its crops'
        (capri-mod's organic targets per member state and crop class, the shares the I/O changes use), weighted by base
        area. Returns {nutrient: {(group, source): (max kg/ha, beta1, beta2)}} or {} without an organic target."""
        conv = getattr(self, "_organic_conv", None) or {}
        base = getattr(self, "_nlp_base_alloc", None)
        if not conv or base is None:
            return {}
        from capri_mod.fert.inner_fert_dist import beta_regulation
        acts = list(self.acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        b1, b2 = beta_regulation(0.25, 0.75)
        out = {}
        dN = (npk.get("nutrients") or {}).get("N")
        if dN is not None:
            regs = {}
            for g_ in dN["groups"]:
                g = g_["g"]
                v = float(base["per_ha"].get((g, "MINE"), 0.0))
                if v <= 0:
                    continue
                w = sum(sh * xb[j] for j, sh in g_["crops"])
                share_conv = 1.0 - (sum(sh * xb[j] * float(conv.get(acts[j], 1.0)) for j, sh in g_["crops"]) / w
                                    if w > 0 else 1.0)
                mx = v if v < self.ORGANIC_SMALL_MINE_KG_HA else v * (1.0 - max(share_conv, 0.0))
                regs[(g, "MINE")] = (mx, b1, b2)
            out["N"] = regs
        f = self.ORGANIC_LIMCRES_FACTOR
        for nut, per in (base.get("per_ha_nut") or {}).items():
            if nut not in (npk.get("nutrients") or {}):
                continue
            r_ = out.setdefault(nut, {})
            for (g, s_), v in per.items():
                if s_ == "CRES" and v > 0:
                    c1 = (1.0 / f) * 10.0 + 1.0
                    r_[(g, "CRES")] = (v * f, c1, 10.0 + 2.0 - c1)
        return out

    def _npk_mineral_cap(self, npk):
        """The Green Deal's mineral N reduction (self._mineral_cap) on the fertilisation block: "crp" - CAPRI's "f2f"
        regulation on each capped group's mineral flow (max per ha = the base allocation per ha x (1 - r), CAPRI's
        exemptions; beta density mode 0.75 x max, accuracy 0.25) and "limCres" on residues; "uaa" - purchases <=
        base mineral N per ha of land x (1 - r) x current land. The base allocation is this model's own (the
        fertilisation block at the calibration point), as CAPRI takes its baseline's."""
        mc = getattr(self, "_mineral_cap", None) or {}
        d = (npk.get("nutrients") or {}).get("N")
        base = getattr(self, "_nlp_base_alloc", None)
        if not mc or d is None or base is None:
            return
        r = float(mc.get("reduction", 0.0) or 0.0)
        if mc.get("kind") == "crp":
            from capri_mod.fert.inner_fert_dist import beta_regulation
            env_ = getattr(self, "_env_for_surplus", None)
            inner = env_.__dict__.get("_inner_fert") if env_ is not None else None
            if inner is None:
                return
            caps = inner.mineral_caps(self.data.region_id, base, r)
            lim = inner.limcres_caps(self.data.region_id, base)
            b1, b2 = beta_regulation(0.25, 0.75)
            regs = {(g, "MINE"): (float(v), b1, b2) for g, v in caps.items() if v > 0}
            for g, (mx, racc, msh) in lim.items():
                c1 = float(msh) * float(racc) + 1.0
                regs[(g, "CRES")] = (float(mx), c1, float(racc) + 2.0 - c1)
            d["regs"] = regs
            self._nlp_group_caps = caps
            # limCres for every nutrient (minfert_redu_by_crop.gms sets it over FNUT)
            for nut_, per_ in (base.get("per_ha_nut") or {}).items():
                d_ = (npk.get("nutrients") or {}).get(nut_)
                if nut_ == "N" or d_ is None:
                    continue
                rg_ = dict(d_.get("regs") or {})
                for g, (mx, racc, msh) in inner.limcres_caps(self.data.region_id, dict(base, per_ha=per_)).items():
                    c1 = float(msh) * float(racc) + 1.0
                    rg_[(g, "CRES")] = (float(mx), c1, float(racc) + 2.0 - c1)
                d_["regs"] = rg_
        else:
            land0 = float(base.get("land", 0.0) or 0.0)
            if land0 > 0:
                d["synNMax"] = (1.0 - r) * float(base["purchase"]) / land0

    #: IPOPT's tolerance for the regional NLP solves: run state, set by CAPRIModel.run every outer iteration from the
    #: setting outer_loop.nlp_tol_final
    nlp_tol = 1e-8
    _CATC_OPT = None

    def _catc_spec(self):
        """The winter cover option of this region for the NLP form ({"uaa", "m0", "lb", "ub", "k1", "lin", "sqr",
        "biofix", "row", "rhs"}), or None (switch off, outside the EU, no data). UAAR: the region's base crop area
        (CAPRI's data UAAR, fixed); lb: the Farm-to-Fork requirement's share (e_minCoverCrops), set by the caller in
        the simulation; the winterCover_ row: sum_c winter cover share_c x crop_c + m x UAAR <= UAAR + fallow floor
        (supply_model.gms l. 1979-1992), its right-hand side at least the base point's (REGISTERED: CAPRI's MaxShare
        is from CAPRI's crop levels, the row from the model's)."""
        if self.data.region_id[:2] in SupplyModule.NON_EU_PREFIXES:
            return None
        if type(self)._CATC_OPT is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "mitigation" / "winter_cover_option.csv"
            type(self)._CATC_OPT = read_csv(f).set_index("region") if f.exists() else pd.DataFrame()
        opt = type(self)._CATC_OPT
        cc = getattr(self.data, "cover_crops", None)
        wcs = getattr(self.data, "winter_cover_share", None)
        reg = self.data.region_id
        if reg not in opt.index or cc is None or wcs is None or str(opt.at[reg, "case"]) == "none":
            return None
        base = self._base_levels()
        uaa = float(sum(float(base.get(c, 0.0) or 0.0) for c in CROPS if c in base.index))
        if uaa <= 0:
            return None
        bf = cc.get("biofix_t_n_ha")
        bf = float(bf) if bf is not None and not pd.isna(bf) else 0.0
        m0 = float(opt.at[reg, "ini_share"])
        row = [(j, float(wcs.at[a, "share"])) for j, a in enumerate(self.acts) if a in wcs.index and float(wcs.at[a, "share"]) > 0]
        cov0 = sum(float(base.get(self.acts[j], 0.0) or 0.0) * s for j, s in row)
        rhs = max(uaa + float(getattr(self, "_fall_floor", 0.0) or 0.0), cov0 + m0 * uaa)
        return {"uaa": uaa, "m0": m0, "lb": 0.0, "ub": max(float(opt.at[reg, "max_share"]), m0),
                "k1": float(opt.at[reg, "cost_lin_eur_ha"]), "lin": float(opt.at[reg, "pmp_lin"]),
                "sqr": float(opt.at[reg, "pmp_sqr"]), "biofix": bf, "row": row, "rhs": rhs,
                "potential": max(0.0, uaa - cov0)}

    def _nlp_abatement_spec(self, labels):
        """CAPRI's abatement options for the NLP form (ghgAbatement; capri-mod: the manure techniques with feeding inside):
        the ammonia options with their loss cascade, the fertiliser options (regional shares) on the crops' mineral N,
        the nitrification inhibitor on manure. {} where off."""
        out = {}
        if not self._techs_inside():
            return out
        _cs = self._catc_spec()
        if _cs is not None:
            out["catc"] = _cs
        ctx = self._amm_context()
        techs = self._tech_list()
        if ctx is not None and techs:
            subs, man_d, nh3, sub = ctx
            sc = {a: self._amm_scale(ss, float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0))
                  for a, ss in subs.items() if a in self.acts}
            out["amm"] = {"techs": techs, "subs": subs, "sc": sc, "wc": self._winter_cover_shares()}
        _tl = getattr(self, "_fert_techs_all", None) or []
        if _tl:
            ft = [(nm_, nmin_, a_, b_, smx_) for (nm_, nmin_, a_, b_, s0_, smx_) in _tl]
            mr = self._crop_mineral_now()
            cr = [(list(self.acts).index(c_), v_) for c_, v_ in mr.items() if c_ in self.acts and v_ > 0]
            if ft and cr:
                out["fert_tech"] = {"crops": cr, "techs": ft, "ecap": fert_efficiency_cap(self.data.region_id)}
        if self._ni_inside():
            nip = self._manure_inhibitor_params()
            if nip is not None:
                al = list(self.acts)
                out["mni"] = {"w": [(al.index(a_), float(m_)) for a_, m_ in nip["man_d"].items()
                                    if a_ in self.acts and float(m_ or 0.0) > 0],
                              "nman": float(nip["nman"]), "smax": nip["smax"], "S0": nip["S0"], "slope": nip["slope"],
                              "vtax": nip["v_tax"]}
                self._nlp_nip = nip
        return out

    def _nlp_tax_terms(self, tax, c, abat):
        """CAPRI's emission tax (ghgTax) in the NLP form, where mineral N is the fertilisation block's purchases
        (v_netPutQuant(NITF)): the soil N2O of mineral N is taxed on the purchases, so every term of the former conic form
        that priced mineral N through a fixed substitution comes out. The activities' own coefficients (ghg_tax.py, finite
        differences of the accounts at the baseline) need no change: the baseline of the NLP form hands the accounts its
        purchases (mineral_n_alloc), which they hold fixed, so those coefficients carry no mineral N2O.
          purchases        tax x (direct + volatilised x indirect) per t N; with the nitrification inhibitor the
                           accounts' side-effect factor on its share of mineral N
          manure trade     the export and import columns lose the tax on the mineral N they were taken to move
          ammonia options  their manure N2O through the cascade and the indirect N2O of the NH3
                           they keep; not the mineral N it displaces (purchases)
          inhibitor on manure  the tax value per t of manure N treated without the mineral N it displaces
        Returns (ghg_min for the NLP spec, c)."""
        from capri_mod.environmental.environmental_module import (EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT,
                                                                  GWP_N2O)
        k = 44.0 / 28.0 * GWP_N2O
        ef_d, ef_v = EF_SOIL_N2O_DIRECT * k, 0.10 * EF_SOIL_N2O_INDIRECT * k
        out = {"d": tax * ef_d / 1000.0, "v": tax * ef_v / 1000.0, "nitr": None,
               "l": tax * self._ef_mineral_lea() / 1000.0}
        l2 = fert_side_value(self.data.region_id, "NITR_INH", "N2OSYN")
        l3 = fert_side_value(self.data.region_id, "NITR_INH", "NH3SYN")
        if l2 is not None and l3 is not None:
            out["nitr"] = (float(l2), float(l3))
        c = np.asarray(c, float).copy()
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            g_ = tax * float(getattr(self, "_pool_avail", 0.0) or 0.0) * (self._ef_mineral_n2o() + self._ef_mineral_lea()) \
                / 1000.0
            if pc[0] < len(c):
                c[pc[0]] -= g_                       # export: paid the mineral N it was taken to buy
            if pc[1] < len(c):
                c[pc[1]] += g_                       # import: credited the mineral N it was taken to save
        if abat.get("amm"):
            abat["amm"]["tax_nh3"] = tax * self._ef_nh3_n2o() / 1000.0
        nip = getattr(self, "_nlp_nip", None)
        if abat.get("mni") and nip is not None:
            abat["mni"]["vtax"] = float(abat["mni"]["vtax"]) - tax * float(nip["sub"]) * float(nip["nman"]) \
                * self._ef_mineral_n2o()
        return out, c

    def _n_row_mineral_parts(self, A, labels):
        """The mineral-N parts of the N_balance row's coefficients (t mineral N per unit of each column), from the
        environmental accounts' own unit balances (n_mineral_input) as the row is built from them: activities their
        unit balance's, manure exports and imports -/+ the substitution factor, the grassland split its delta, the
        dairy, cattle and option columns their animal's in proportion to their manure coefficient."""
        env_ = getattr(self, "_env_for_surplus", None)
        i_nb = labels.index("N_balance")
        mp = np.zeros(A.shape[1])
        if env_ is None:
            return mp
        rid = self.data.region_id
        ycur = self.data.yields
        mint = dict(getattr(self, "_n_intensity", {}) or {})
        acts = list(self.acts)
        unit = {}
        for j, a in enumerate(acts):
            mi = {k_: v_ for k_, v_ in mint.items() if k_ in (a, "__credit__")}
            unit[a] = float(env_.unit_nitrogen_balance(a, ycur, rid, mi, yields_scen=self._yields_scen_now())
                            .get("n_mineral_input", 0.0))
            mp[j] = unit[a]
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            sub = float(getattr(self, "_pool_avail", 0.0) or 0.0)
            if pc[0] < A.shape[1]:
                mp[pc[0]] = sub                 # export: the row has -(1 - sub): -1 organic, +sub mineral
            if pc[1] < A.shape[1]:
                mp[pc[1]] = -sub
        gc = getattr(self, "_grass_col", None)
        if gc is not None and gc < A.shape[1]:
            d = env_.grass_intensity_delta(rid) or {}
            mp[gc] = float(d.get("n_mineral_input", 0.0))
        cols = self._aug_col_labels(A.shape[1])
        for j, lab in enumerate(cols):
            a = None
            if lab == "dairy_z":
                a = "DCOW"
            elif lab.startswith("cattle_z_"):
                a = lab[len("cattle_z_"):].split(":")[0]
            elif lab.startswith("genet_z_"):
                a = lab[len("genet_z_"):].split("_")[0]
            if a in acts:
                ja = acts.index(a)
                if A[i_nb, ja] != 0:
                    mp[j] = unit[a] * float(A[i_nb, j]) / float(A[i_nb, ja])
        return mp

    def _cap_rules_spec(self):
        """CAPRI's greening rules of this region (policy/define_greening_limits.gms with
        scen/Premiums/Greening/cap_2013_2020_greening.gms; data tools/build/build_cap_greening.py):
          permGras     grassland >= its base area; its dual at calibration CAPRI's |arable rent - grassland rent|
          ecoSetAside  sum(crops but grassland) x r / (1 - r) <= sum(EFA activities x weight)  (r = 5%, efabasis
                       UAAR; weights FALL/VSET (SETA) 1, PULS 0.7, OFAR 0.7 x legume share, catch crops 0.3 where the
                       winter cover option is in the NLP; ISET 0, GSET/TSET none: CAPRI's 2017 and 2030 data have no
                       area under them, so SETA = FALL + VSET at weight 1)
          cropDiv      Shannon index of the annual crop groups >= its base value
        Where the base does not meet the ecological set-aside rule (the model's base data, not CAPRI's calibrated
        base), the rule is held at the base's own value (REGISTERED)."""
        if not getattr(type(self), "cap_greening", False):
            return None
        import pandas as _pd
        from pathlib import Path as _P
        cache = type(self).__dict__.get("_CAPG")
        if cache is None:
            root = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "policy"
            st = read_csv(root / "cap_greening_2013_2020.csv")
            fl = read_csv(root / "cap_greening_fleg_ms.csv").set_index("ms")["fleg_share"].to_dict()
            cache = ({(r.item, r.key): float(r.value) for r in st.itertuples(index=False)}, fl)
            type(self)._CAPG = cache
        st, fleg = cache
        acts = list(self.acts)
        xb = np.maximum(self._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
        out = {}
        if st.get(("active", "permGras")) and "GRAS" in acts:
            j = acts.index("GRAS")
            # only where grassland has a level: below the threshold of the activity bounds (an activity without a
            # level, held at zero, _build_constraints) CAPRI has no grassland variable and no rule; with a base of
            # 3.5e-11 kha (EL63, 2030) the rule asked for grass the bounds forbid and the NLP was infeasible (K69)
            if xb[j] > ABSENT_LEVEL:
                out["permGras"] = {"row": [(j, -1.0)], "rhs": -xb[j] * (1 - 1e-9), "scale": xb[j]}
                # the rule's dual at the calibration point, CAPRI's assumption (supply/prep_cal.gms l. 118-131):
                # p_dualGreening = -|rent of arable land - rent of grassland|, charged to GRAE and GRAI in the
                # calibration's linear terms (EUR/ha; CapriRegionalNLP.calibrate fixes the row's multiplier at it)
                _r = getattr(self.data, "land_rents", None)
                if _r is not None and hasattr(_r, "get"):
                    ra, rg = _r.get("ARAC"), _r.get("GRAS")
                    if ra is not None and rg is not None and ra == ra and rg == rg:
                        out["permGras"]["cal_dual"] = abs(float(ra) - float(rg))
        if st.get(("active", "ecoSetAside")):
            r = st.get(("setaside_rate_pct", "ARAB"), 0.0) / 100.0
            ms = self.data.region_id[:2]
            ms = MS_CODE.get(ms, ms)
            ofar = 1.0
            env_ = getattr(self, "_env_for_surplus", None)
            try:
                from capri_mod.fert.npk import NPKData
                cr = env_._inner_fert.capri_region(self.data.region_id) if env_ is not None and \
                    env_.__dict__.get("_inner_fert") is not None else None
                if cr is not None:
                    ofar = float(NPKData.get().crop_shares(cr).get("OFOD", {}).get("OFAR", 1.0))
            except Exception:
                pass
            w = {"SETA": st.get(("weight", "FALL"), 0.0), "PULS": st.get(("weight", "PULS"), 0.0),
                 "OFOD": st.get(("weight", "OFAR"), 0.0) * float(fleg.get(ms, 0.0)) * ofar}
            row = []
            for j, a in enumerate(acts):
                if a in CROPS and a != "GRAS":
                    row.append((j, r / (1.0 - r) - w.get(a, 0.0)))
            v0 = sum(c_ * xb[j] for j, c_ in row)
            sc_ = max(1.0, sum(abs(c_) * xb[j] for j, c_ in row))
            # catch crops count at CAPRI's weight (setaEco includes CATC, p_DPgreeningWeight 0.3) where the NLP form
            # chooses them (the winter cover option: share m of UAAR, CapriRegionalNLP adds - w x UAAR x m to the row)
            wc = st.get(("weight", "CATC"), 0.0)
            cs_ = self._catc_spec() if wc > 0 else None
            if cs_ is not None:
                v0 -= wc * float(cs_["uaa"]) * float(cs_["m0"])
            out["ecoSetAside"] = {"row": row, "rhs": max(0.0, v0) + 1e-9 * sc_, "scale": sc_, "base_gap": v0,
                                  "catc_w": wc if cs_ is not None else 0.0}
        if st.get(("active", "cropDiv")):
            grp = {}
            for j, a in enumerate(acts):
                g = self.CROPDIV_GROUPS.get(a)
                if g is not None:
                    grp.setdefault(g, []).append((j, 1.0))
            X = [sum(xb[j] for j, _ in gp) + 1e-6 for gp in grp.values()]
            T = sum(X)
            if T > 0 and len(X) > 1:
                H0 = -sum(x / T * np.log(x / T) for x in X)
                # with the Biodiversity Strategy's fallow floor F, CAPRI lowers the limit to avoid infeasibility
                # (pol_input/greendeal/landscape.gms l. 75-90, as coded there: F added to every group and to the
                # annual area): H0 = min(H0, - sum_g (X_g + F)/(T + F) log((X_g + F)/(T + F)))
                F = float(getattr(self, "_fall_floor", 0.0) or 0.0)
                if F > 0:
                    H0 = min(H0, -sum((x + F) / (T + F) * np.log((x + F) / (T + F)) for x in X))
                out["cropDiv"] = {"groups": list(grp.values()), "H0": H0 * (1 - 1e-9)}
        return out or None

    def _npk_recalibrate_priors(self, spec, nuts, yb) -> bool:
        """CAPRI's fertiliser calibration (fert/ferttrm_years.gms, as capri_mod.fert.inner_fert_dist.calibrate) for
        the nutrients whose block has no solution at the base: blanket priors per crop group - the group's need at
        base (net of the permanent crops' own residues, at least 10% of the need) split equally over its sources
        (mineral, manure, and residues for arable groups), half of grassland's mineral prior moved to manure, accuracy
        2 (residues 5) - and their posterior at the base's levels, which becomes the region's simulation prior
        (accuracy 1). Returns whether every nutrient got one."""
        from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
        from capri_mod.fert.inner_fert_dist import (FERT_CAL_PRIOR_ACCURACY, FERT_CAL_CRES_ACCURACY,
                                                    FERT_CAL_MIN_NEED_SHARE, FERT_CAL_GRAS_MINE_TO_EXCR)
        import copy as _cp
        sp = dict(spec)
        npk = _cp.deepcopy(spec["npk"])
        yb = np.asarray(yb, float)
        for nut in nuts:
            d = npk["nutrients"][nut]
            for g_ in d["groups"]:
                nd = sum(v * yb[j] for j, v in g_["need"])
                ow = sum(v * yb[j] for j, v in g_["own"]) * float(d["gc"]) if g_["perm"] else 0.0
                R = max(FERT_CAL_MIN_NEED_SHARE * nd, nd - ow)
                k = 2.0 if g_["perm"] else 3.0
                m = R / k
                modes = {"MINE": m, "EXCR": m}
                if not g_["perm"]:
                    modes["CRES"] = m
                if g_["g"] == "GRAS":
                    modes["EXCR"] += FERT_CAL_GRAS_MINE_TO_EXCR * modes["MINE"]
                    modes["MINE"] *= 1.0 - FERT_CAL_GRAS_MINE_TO_EXCR
                g_["modes"] = {s_: max(v, 1e-6) for s_, v in modes.items()}
                g_["acc"] = {"MINE": FERT_CAL_PRIOR_ACCURACY, "EXCR": FERT_CAL_PRIOR_ACCURACY,
                             "CRES": FERT_CAL_CRES_ACCURACY}
        sp["npk"] = npk
        tmp = CapriRegionalNLP(sp)
        x, failed = tmp.fert_at(tmp.start(yb))
        ok = True
        ov = dict(getattr(self, "_npk_prior_override", None) or {})
        out = tmp.fert_outputs(x)
        for nut in nuts:
            if nut in failed:
                ok = False
                continue
            ov[nut] = dict(out[nut]["flows"])
        self._npk_prior_override = ov
        self._npk_prior_recalibrated = sorted(set(getattr(self, "_npk_prior_recalibrated", []) or []) | set(ov))
        return ok

    def _npk_applied_ratio(self, cr, nut):
        """CAPRI 2030: manure P/K applied in the region (net of net exports) per unit excreted (fertDistExcr_ /
        EXCRET), from the extract of tools/build/build_npk_balance_2030.py."""
        c = type(self).__dict__.get("_NPK_APPL")
        if c is None:
            import pandas as _pd
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "sources" / "environment" / "npk_dataout_2030.csv.xz"
            s = read_csv(f, keep_default_na=False)
            s = s[(s.item == "") & (s.row.isin(["EXCRET", "MTRADE"]))]
            v = {(t.region, t.row, t.col): float(t.value) for t in s.itertuples(index=False)}
            c = {}
            for (r, row, col), x in v.items():
                if row == "EXCRET" and x > 0:
                    c[(r, {"PHOF": "P", "POTF": "K", "NITF": "N"}[col])] = max(0.0, 1.0 - v.get((r, "MTRADE", col), 0.0) / x)
            type(self)._NPK_APPL = c
        return c.get((cr, nut), c.get((cr[:2] + "000000", nut), 1.0))

    def _aug_col_labels(self, n_cols):
        """One label per column of the regional problem: activities, land types, the mineral-N allocation column,
        manure exports and imports, the split and option columns, histosol fallow."""
        lab = list(self.acts)
        n = len(lab)
        extra = {}
        lt = list(getattr(self, "_land_types_used", None) or [])
        if lt and n + len(lt) <= n_cols and getattr(self, "_last_aug_cols", None) != "plain":
            for k_, t in enumerate(lt):
                extra[n + k_] = "land_" + t
            if getattr(self, "_alloc_cols", 0):
                extra[n + len(lt)] = "alloc_mineral_N"
        pc = getattr(self, "_pool_cols", None) or []
        if len(pc) == 2:
            extra[int(pc[0])] = "manure_export"; extra[int(pc[1])] = "manure_import"
        if getattr(self, "_grass_col", None) is not None:
            extra[int(self._grass_col)] = "grass_z"
        if getattr(self, "_dairy_col", None) is not None:
            extra[int(self._dairy_col)] = "dairy_z"
        for a_, j_ in (getattr(self, "_cattle_cols", None) or {}).items():
            extra[int(j_)] = f"cattle_z_{a_}"
        for (a_, o_), j_ in (getattr(self, "_genet_cols", None) or {}).items():
            extra[int(j_)] = f"genet_z_{a_}_{o_}"
        for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items():
            extra[int(j_)] = f"hist_{c_}"
        out = lab + [extra.get(j, f"col{j}") for j in range(n, n_cols)]
        return out

    @staticmethod
    def _nlp_mine_fingerprint(npk):
        """The mineral-N caps of the fertilisation block (MINE regulations) as a hashable key; None without any."""
        if npk is None:
            return None
        items = sorted((nut, repr(k_), round(float(v_[0]), 9)) for nut, d_ in npk["nutrients"].items()
                       for k_, v_ in (d_.get("regs") or {}).items() if k_[1] == "MINE")
        return hash(tuple(items)) if items else None

    def _nlp_relax_spec(self, spec, kind, groups=None, wide=True):
        """The spec with a relaxation of the mineral caps. "duals": the inner model's duals widened to +-1000 (REGISTERED,
        CAPRI's own workaround is a slack). "caps": the crop groups in `groups` exempted as CAPRI exempts groups in
        minfert_redu_by_crop.gms (p_checkSmallMine: the group's cap at factor x its baseline mineral N per ha, "no
        backsliding"; factor fertiliser.exempt_cap_factor, CAPRI's 1.0 for its small groups), with the duals widened
        when `wide`. groups None: every capped group."""
        import copy as _cp
        sp_ = dict(spec, npk=_cp.deepcopy(spec["npk"]))
        if kind == "duals" or wide:
            sp_["npk"]["dual_bound"] = float(_settings().get("fertiliser.npk_dual_bound_wide"))
        if kind == "caps":
            base_ = (getattr(self, "_nlp_base_alloc", None) or {}).get("per_ha") or {}
            f_ = float(_settings().get("fertiliser.exempt_cap_factor"))
            rg_ = sp_["npk"]["nutrients"]["N"].get("regs") or {}
            for k_ in list(rg_):
                if k_[1] == "MINE" and (groups is None or k_[0] in groups):
                    rg_[k_] = (max(float(rg_[k_][0]), f_ * float(base_.get(k_, 0.0))),) + tuple(rg_[k_][1:])
        return sp_

    @staticmethod
    def _nlp_cap_shortfall(spec, x):
        """The mineral-capped crop groups ordered by how far their N need is out of reach at the levels x (t N):
        need - own residues - (mineral efficiency x cap + manure availability x the manure flow's upper bound + residue
        availability x the residue flow's upper bound), the flows' bounds 1000 x their prior modes as CAPRI's
        (supply/prep_sim.gms). A positive value: the group cannot meet its need under its cap whatever the rest of the
        region does. Returns [(group, shortfall)], largest first."""
        d = ((spec.get("npk") or {}).get("nutrients") or {}).get("N")
        if d is None:
            return []
        x = np.asarray(x, float)
        lin = lambda pairs: float(sum(float(v) * x[int(j)] for j, v in pairs if int(j) < len(x)))
        regs = d.get("regs") or {}
        out = []
        for g_ in d["groups"]:
            k_ = (g_["g"], "MINE")
            if k_ not in regs:
                continue
            need = lin(g_["need"])
            if g_.get("perm") and g_.get("own"):
                need -= float(d["gc"]) * lin(g_["own"])
            area = lin(g_["crops"])
            sup = float(d["eff"]) * float(regs[k_][0]) * area
            m_ = g_.get("modes") or {}
            sup += float(d["g0"]) * 1000.0 * float(m_.get("EXCR", 0.0))
            sup += float(d["gc"]) * 1000.0 * float(m_.get("CRES", 0.0))
            out.append((g_["g"], need - sup))
        return sorted(out, key=lambda t: -t[1])

    def _capri_nlp_solve(self, Q, c, A, b, x_start):
        """The regional problem in CAPRI's form (capri_regional_nlp.CapriRegionalNLP), solved with IPOPT from the
        region's previous solution (CAPRI's CONOPT starts from the last solution; then without the duals, then cold from
        the caller's start). Returns the columns' solution, or None on failure (the caller's relaxations follow; on its
        last attempt, _nlp_accept_last, IPOPT's last point is returned and recorded in _nlp_fallback_log, the run's
        metadata["nlp_fallback"])."""
        self._n_solves = int(getattr(self, "_n_solves", 0) or 0) + 1
        self._wc_solved = None; self._cover_solved = None
        self._yani_dnet = None
        from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
        rats = getattr(self, "feed_rations", None) or {}
        self._fd_model = None
        lab_row = list(getattr(self, "_row_labels", []) or [])
        labels = list(getattr(self, "_aug_labels", None) or [])
        if len(labels) != A.shape[0]:
            labels = lab_row if len(lab_row) == A.shape[0] else None
        if labels is None:
            raise RuntimeError(f"{self.data.region_id}: no row labels for the {A.shape[0]} rows of the regional problem")
        fod = {l.replace("fodder_", ""): k for k, l in enumerate(labels)
               if l.startswith("fodder_") and not l.endswith("_band")}
        n = len(self.acts)
        xb = np.maximum(np.asarray(x_start, float), 0.0).copy()
        xb[:n] = np.maximum(self._base_levels().reindex(list(self.acts)).fillna(0.0).values, 0.0)
        _rx = getattr(self, "_dairy_req_extra", None)
        _rx = _rx if (_rx and max(c_ for a_ in _rx for c_, _ in _rx[a_]) < Q.shape[0]) else None
        c = np.asarray(c, float).copy()
        npk = self._npk_spec(Q.shape[0], x_start, A, labels)
        drop = []
        if npk is not None:
            # CAPRI's fertilisation replaces the regional crop-need row (an approximation of NUTNED_) and
            # the fertiliser cost per ha: mineral N, P and K are bought at CAPRI's unit value (v_netPutQuant(FNUT))
            drop = ["crop_need"]
            oc_ = getattr(self, "_organic_conv", None) or {}
            for j, a in enumerate(self.acts):
                if a in CROPS:
                    # (on converted land the organic I/O change already took the fertiliser cost out: only the
                    # conventional share's is left in c)
                    c[j] -= float(self._input_cost(a, "fert", self.FERT_COST_SHARE)) * float(oc_.get(a, 1.0))
        abat = self._nlp_abatement_spec(labels) if npk is not None else {}
        if npk is not None:
            # capri-mod's manure-application limit and mineral-N allocation row are not CAPRI's
            drop += ["manure_application", "alloc_mineral_N"]
        tax_ = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        ghg_min = None
        if tax_ > 0 and npk is not None:
            ghg_min, c = self._nlp_tax_terms(tax_, c, abat)
        spec = dict(Q=Q, c=c, A=A, b=b, labels=labels, acts=list(self.acts), rations=rats, fodder=fod, x_base=xb,
                    prices=getattr(self, "feed_prices", None), req_extra=_rx, feed_ghg=self._ghg_feed_cost(),
                    npk=npk, drop_labels=drop, cap_rules=self._cap_rules_spec(), ghg_min=ghg_min,
                    land_rent_rows=dict(getattr(self, "_land_rent_rows", None) or {}), **abat)
        if npk is not None and getattr(self, "_alloc_cols", 0):
            spec["fix_cols"] = {n + len(getattr(self, "_land_types_used", [])): 0.0}
        self._last_feed_dm = None
        self._last_feed_t = None
        self._nlp_ok = False
        # CAPRI's calibration: the base is a first-order point of the model it is simulated with. Once per region, at
        # the first solve (the baseline's base point and prices); the linear terms are kept by column and feed
        cols = self._aug_col_labels(Q.shape[0])
        cal = getattr(self, "_nlp_cal", None)
        _late = ("grass_z", "dairy_z", "cattle_z_", "genet_z_", "hist_")
        if cal is not None and cal.get("cols") is not None and \
                any(l_.startswith(_late) for l_ in set(cols) - set(cal["cols"])):
            if os.environ.get("CAPRI_TRACE_RECAL"):
                print("RECAL", self.data.region_id, sorted(set(cols) - set(cal["cols"]))[:6], flush=True)
            # the split and histosol columns enter after the region's first solve (their linear terms come from that
            # solve's duals, at the baseline's prices): calibrate again, so that the base is a first-order point
            # of the problem with them
            cal = None
        try:
            # the scenario's policy rows are not part of the base the model is calibrated at (CAPRI calibrates in its
            # baseline)
            pol_rows = [l_ for l_ in ("N_balance", "mineral_N", "landscape_floor", "winter_cover") if l_ in labels]
            spec_sim = spec
            spec = dict(spec_sim, drop_labels=list(drop) + pol_rows)
            _fp = None
            if self.__dict__.pop("_nlp_cal_check", False) or cal is None:
                _fp = _spec_fingerprint(spec, yb_n=np.asarray(x_start, float), xb=xb[:n])
                if cal is not None and cal.get("fp") != _fp:
                    cal = None              # made on another calibration problem (a baseline checks it, see run)
            if cal is None:
                nlp0 = CapriRegionalNLP(spec)
                yb = np.asarray(x_start, float).copy()
                yb[:n] = xb[:n]
                out = nlp0.calibrate(yb)
                if not out.get("ok") and out.get("fert_failed") and npk is not None:
                    # CAPRI's priors (its 2030 posterior per ha) admit no allocation at this model's base: CAPRI's
                    # fertiliser calibration at this base instead (blanket priors, posterior at the base's own levels),
                    # as CAPRI recalibrates whenever its baseline changes
                    if self._npk_recalibrate_priors(spec, out["fert_failed"], yb):
                        npk = self._npk_spec(Q.shape[0], x_start, A, labels)
                        spec["npk"] = npk
                        nlp0 = CapriRegionalNLP(spec)
                        out = nlp0.calibrate(yb)
                if not out.get("ok") and out.get("fert_failed") and npk is not None:
                    # CAPRI bounds the inner model's duals at +-10 to help its solver (set_fert_priors.gms: "limit the
                    # dual values to reasonable range"); groups with tiny areas can need more at the model's base
                    # (CAPRI's own workaround there is a slack on the partial derivative, v_fertDistPartialSlack).
                    # Widened for this region (REGISTERED, recorded as npk_dual_bound)
                    self._npk_dual_bound = float(_settings().get("fertiliser.npk_dual_bound_wide"))
                    npk = self._npk_spec(Q.shape[0], x_start, A, labels)
                    spec["npk"] = npk
                    nlp0 = CapriRegionalNLP(spec)
                    out = nlp0.calibrate(yb)
                if out.get("ok"):
                    cal = {"dq": {cols[j]: float(v) for j, v in enumerate(out["dq"]) if v != 0.0},
                           "dcnst": dict(out["dcnst"]), "dabat": dict(out.get("dabat") or {}),
                           "residual": out["residual"],
                           "purchase0": {k_: v_["purchase"] for k_, v_ in nlp0.fert_outputs(nlp0.cal_point).items()},
                           "base_alloc": self._npk_base_alloc(nlp0, npk, yb),
                           "obj0": float(nlp0.f_obj(nlp0.cal_point)), "cols": list(cols)}
                else:
                    cal = {"dq": {}, "dcnst": {}, "failed": out.get("why")}
                    import warnings as _w
                    _w.warn(f"NLP calibration failed for {self.data.region_id}: {out.get('why')}", RuntimeWarning)
                cal["fp"] = _fp
                self._nlp_cal = cal
                self._nlp_base_alloc = cal.get("base_alloc")
            # the simulation's spec: the policy rows back, in CAPRI's terms where the NLP form writes them
            spec = dict(spec_sim, npk=spec.get("npk"))
            npk = spec["npk"]
            if spec.get("amm") and not self._amm_incentive(labels):
                # K63: without a policy incentive on N (no N-surplus row, no mineral cap, no emission tax) CAPRI's
                # options stay at their calibrated shares (CONOPT starts at the calibrated point, a first-order point
                # after costsavings0); IPOPT's interior start left that point along the options' joint direction
                spec["amm"] = dict(spec["amm"], fixed=True)
            if spec.get("catc"):
                # the Farm-to-Fork catch-crop requirement (e_minCoverCrops) as the option's lower bound; the option
                # carries the winterCover_ row itself
                _cv = getattr(self, "_cover", None)
                if _cv and float(_cv.get("uaa", 0.0) or 0.0) > 0:
                    _lb = float(_cv["req"]) / float(spec["catc"]["uaa"])
                    spec["catc"] = dict(spec["catc"], lb=_lb, ub=max(float(spec["catc"]["ub"]), _lb))
                spec["drop_labels"] = list(spec["drop_labels"]) + ["winter_cover"]
            if npk is not None:
                import copy as _cp
                npk = _cp.deepcopy(npk)
                spec["npk"] = npk
                # CAPRI's organic area target: the inner model's "f2f" and "limCres" regulations by crop group
                # (organic_minfert_redu.gms), set before the mineral fertiliser reduction, which keeps the more
                # stringent of the two (minfert_redu_by_crop.gms: min(); its limCres replaces the organic one)
                org_regs = self._npk_organic_cap(npk)
                if "mineral_N" in labels:
                    # CAPRI's mineral fertiliser reduction in its own terms: the inner model's regulations by crop
                    # group (minfert_redu_by_crop.gms) or e_synNMax (minfert_redu_uaa.gms); the summed row goes
                    self._npk_mineral_cap(npk)
                    spec["drop_labels"] = list(spec["drop_labels"]) + ["mineral_N"]
                for nut_, rg in org_regs.items():
                    d_ = npk["nutrients"].get(nut_)
                    if d_ is None:
                        continue
                    cur = dict(d_.get("regs") or {})
                    for k_, v_ in rg.items():
                        if k_ not in cur:
                            cur[k_] = v_
                        elif k_[1] == "MINE" and v_[0] < cur[k_][0]:
                            cur[k_] = v_
                    d_["regs"] = cur
                if "N_balance" in labels:
                    # the N-surplus target with the mineral N of the fertilisation block (CAPRI SURTOT_REST_ /
                    # e_SURTOTHa): the row's linear mineral parts out, the purchases in
                    npk["n_rows"] = [("N_balance", self._n_row_mineral_parts(A, labels))]
                    if spec.get("catc"):
                        # the requirement's catch-crop N was put on the row as a constant; the
                        # NLP form's catch-crop share carries it (catc_n), so the constant is taken back out
                        npk["n_rows_rhs_add"] = {"N_balance": float(getattr(self, "_cover_dbf_nb", 0.0) or 0.0)}
                    spec["drop_labels"] = list(spec["drop_labels"]) + ["N_balance"]
            if cal is not None:
                spec["dq"] = np.array([cal["dq"].get(l_, 0.0) for l_ in cols])
                spec["dcnst"] = cal["dcnst"]
                spec["dabat"] = cal.get("dabat") or {}
            # a relaxation once needed under these mineral caps is kept for the rest of the scenario (CAPRI's
            # exemptions are set once, before its solves, not by iteration); without this the region switched between
            # the relaxed and the strict problem from one outer iteration to the next
            _fp = self._nlp_mine_fingerprint(npk)
            _keep = getattr(self, "_nlp_relax_keep", None)
            if _fp is not None and _keep is not None and _keep[0] == _fp:
                spec0 = spec
                spec = self._nlp_relax_spec(spec, _keep[1], *(_keep[2:4] if len(_keep) > 2 else ()))
                npk = spec["npk"]
            else:
                _keep = None
                spec0 = spec
            nlp = CapriRegionalNLP(spec)
            if os.environ.get("CAPRI_NLP_DUMP"):
                import pickle as _pk
                _pk.dump(dict(spec=spec, x_start=np.asarray(x_start, float), cols=cols, cal=cal),
                         open(os.path.join(os.environ["CAPRI_NLP_DUMP"], f"{self.data.region_id}.pkl"), "wb"))
        except Exception as _exc:
            import warnings as _w
            if os.environ.get("CAPRI_TRACE_NLP_BUILD"):            # diagnostics: the build's traceback
                import traceback as _tb
                _tb.print_exc()
            _w.warn(f"NLP build failed for {self.data.region_id}: {_exc!r}")
            return None
        # warm start: the previous solution where the problem has the same columns, else the caller's start with the
        # base ration
        prev = getattr(self, "_nlp_prev", None)
        gk = nlp.graph_key()
        shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
        starts = []
        if prev is not None and len(prev) == 4 and prev[2] == shape:
            xw = nlp.inside_regulations(np.clip(prev[1], nlp.lbx, nlp.ubx))
            if prev[0] == gk:
                starts.append(("warm", xw, prev[3]))       # IPOPT's warm start from the last primal-dual point
            starts.append(("prev", xw, None))
        starts.append(("start", nlp.start(np.asarray(x_start, float)), None))
        res = None
        kinds = []
        _tol = float(getattr(type(self), "nlp_tol", 1e-8))
        _tried = []
        for kind, xs, lam_ in starts:
            res = nlp.solve(xs, lam=lam_, tol=_tol)
            kinds.append(kind)
            _tried.append((kind, res["status"], float(res["f"]), int(res["iterations"] or 0)))
            if res["success"] or res["status"] in ("Solved_To_Acceptable_Level",):
                break
        _f_prev = getattr(self, "_nlp_prev_f", None)
        if (kinds and kinds[-1] == "warm" and _f_prev is not None
                and float(res["f"]) > _f_prev + float(getattr(type(self), "nlp_warm_check", 0.01)) * abs(_f_prev)):
            # a warm start (IPOPT from the previous primal-dual point, small barrier) can end at a worse stationary
            # point of the non-convex per-head feeding and stay there in every later iteration (Brittany, Farm-to-Fork
            # 2030: livestock at their lower bounds, objective 9% worse, "Solve_Succeeded"; KNOWN_ISSUES K75). Where
            # its objective is more than nlp_warm_check (relative) worse than the last iteration's, the region is also
            # solved from the previous point and from the standard start, and the lowest objective is kept.
            for kind, xs, lam_ in [s_ for s_ in starts if s_[0] != "warm"]:
                r_ = nlp.solve(xs, lam=lam_, tol=_tol)
                _tried.append((kind, r_["status"], float(r_["f"]), int(r_["iterations"] or 0)))
                if (r_["success"] or r_["status"] in ("Solved_To_Acceptable_Level",)) and float(r_["f"]) < float(res["f"]):
                    res = r_
                    kinds.append("checked:" + kind)
        _ok = lambda r_: r_["success"] or r_["status"] in ("Solved_To_Acceptable_Level",)
        _lab = lambda k_: ((k_[1] if k_[1] == "duals" else "caps:" + "+".join(k_[2]) + (",duals" if k_[3] else ""))
                           if k_ is not None else None)
        self._nlp_relaxed = _lab(_keep)
        _order = ("duals", "caps")
        # a kept exemption that no longer suffices is extended (the next group), not dropped
        _todo = (_order[_order.index(_keep[1]) + 1:] or ("caps",)) if _keep is not None else _order
        if not _ok(res) and _fp is not None and _todo:
            # the Green Deal's mineral caps (organic target, mineRedu) as CAPRI's regulations can leave a crop group's
            # need out of reach (e.g. a permanent-crop group with a high organic target, its mineral N cut by the
            # converted share, and a manure prior near zero). CAPRI's runs hit this and exempt the groups concerned by
            # region and group (minfert_redu_by_crop.gms, p_checkSmallMine: cap at 1.0-1.2 x baseline). REGISTERED:
            # first the duals widened to +-1000; then the groups exempted one at a time, those whose need is out of
            # reach first (_nlp_cap_shortfall), at fertiliser.exempt_cap_factor x baseline, with CAPRI's duals and
            # then the widened ones; recorded as nlp_relaxed ("caps:GROUP+...")
            def _try(sp_):
                try:
                    nlp_ = CapriRegionalNLP(sp_)
                    return nlp_, nlp_.solve(nlp_.start(np.asarray(x_start, float)))
                except Exception:
                    return None, None
            for kind_ in _todo:
                found = None
                if kind_ == "duals":
                    sp_ = self._nlp_relax_spec(spec0, "duals")
                    nlp_, res_ = _try(sp_)
                    if res_ is not None and _ok(res_):
                        found = (nlp_, res_, sp_, (_fp, "duals"))
                else:
                    ex_ = list(_keep[2]) if (_keep is not None and _keep[1] == "caps") else []
                    cand = [g for g, _ in self._nlp_cap_shortfall(spec0, x_start) if g not in ex_]
                    n_kept = len(ex_)
                    for g in cand:
                        ex_.append(g)
                        for wide_ in (False, True):
                            sp_ = self._nlp_relax_spec(spec0, "caps", tuple(ex_), wide_)
                            nlp_, res_ = _try(sp_)
                            if res_ is not None and _ok(res_):
                                found = (nlp_, res_, sp_, (_fp, "caps", tuple(ex_), wide_))
                                break
                        if found:
                            break
                    if found:
                        # the smallest set: a group added on the way is dropped again where the rest suffices
                        wide_ = found[3][3]
                        for g in list(ex_[n_kept:-1]):
                            trial = tuple(x for x in ex_ if x != g)
                            sp_ = self._nlp_relax_spec(spec0, "caps", trial, wide_)
                            nlp_, res_ = _try(sp_)
                            if res_ is not None and _ok(res_):
                                ex_ = list(trial)
                                found = (nlp_, res_, sp_, (_fp, "caps", trial, wide_))
                if found:
                    nlp, res, sp_, k_ = found[0], found[1], found[2], found[3]
                    npk, spec = sp_["npk"], sp_         # later re-solves (amm-fixed) keep the relaxation
                    gk = nlp.graph_key()
                    shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
                    self._nlp_relax_keep = k_
                    self._nlp_relaxed = _lab(k_)
                    kinds.append(self._nlp_relaxed)
                    break
        self._nlp_times = (getattr(nlp, "build_s", 0.0), getattr(nlp, "solve_s", 0.0))
        _nonopt = None
        if not _ok(res):
            import warnings as _w
            _w.warn(f"NLP solve {res['status']} for {self.data.region_id} after {res['iterations']} iterations",
                    RuntimeWarning)
            self._nlp_failed = "nlp:" + str(res["status"])
            if not getattr(self, "_nlp_accept_last", False) or res.get("x") is None:
                return None
            # the caller's last attempt: CAPRI carries on with a non-optimal solve and records it (supply/simu_supply.gms,
            # p_INFES); IPOPT's last point is kept, recorded in the run's metadata (nlp_fallback) and warned about
            _nonopt = str(res["status"])
            self._nlp_nonoptimal = _nonopt
            _w.warn(f"{self.data.region_id}: IPOPT's last point kept ({_nonopt}, non-optimal), as CAPRI keeps a "
                    f"non-optimal solve", RuntimeWarning)
        _am = spec.get("amm")
        if (_nonopt is None and _am and not _am.get("fixed")
                and "N_balance" in labels and "mineral_N" not in labels
                and not float(getattr(self, "ghg_tax", 0.0) or 0.0) > 0):
            # the N-surplus row slack (dual ~0): the options at their base shares (CONOPT stays at
            # the calibrated shares unless moving pays through the policy row)
            _zA = nlp.outputs(res)[2]
            if float(_zA[labels.index("N_balance")]) <= 1e-9:
                try:
                    spec_f = dict(spec, amm=dict(_am, fixed=True))
                    nlp_f = CapriRegionalNLP(spec_f)
                    res_f = nlp_f.solve(np.clip(res["x"], nlp_f.lbx, nlp_f.ubx), tol=_tol)
                    if _ok(res_f):
                        nlp, res, spec = nlp_f, res_f, spec_f
                        gk = nlp.graph_key()
                        shape = (nlp.n0, tuple(k[:2] for k in nlp.feeds), len(nlp.lbx))
                        kinds.append("amm-fixed")
                except Exception:
                    pass
        self._nlp_prev = (gk, res["x"], shape, (res["lam_x"], res["lam_g"]))
        self._nlp_prev_f = float(res["f"])
        # the starts tried and the last one's IPOPT iterations (diagnostics of the outer loop, model.trace_outer)
        self._nlp_path = ("/".join(kinds), int(res["iterations"]))
        if os.environ.get("CAPRI_NLP_DUMP") and self.data.region_id in os.environ.get("CAPRI_NLP_TRACE", "").split(","):
            # diagnostics only: every solve of the traced regions, with the previous point, the starts tried and the
            # point kept (CAPRI_NLP_TRACE=FRH0,...; KNOWN_ISSUES K75)
            import pickle as _pk
            _fn = os.path.join(os.environ["CAPRI_NLP_DUMP"], f"{self.data.region_id}.trace.pkl")
            _rec = dict(spec=spec, prev=prev, tried=_tried, kinds=list(kinds), x=np.asarray(res["x"], float).copy(),
                        status=res["status"], f=float(res["f"]))
            with open(_fn, "ab") as _fh:
                _pk.dump(_rec, _fh)
        y, F, zA, info = nlp.outputs(res)
        self._nlp_y = np.asarray(y, float).ravel().copy()
        self._nlp_cols = list(cols)
        # the young-animal markets' price update: this solution's response to the young-animal prices (K65)
        self._yani_dnet = None
        _ye = getattr(type(self), "yani_exact_response", None)
        if _ye is None:
            _ye = bool(getattr(type(self), "use_cattle_member_splits", False))
        if _ye and getattr(self, "yani_price_ratio", None):
            try:
                self._yani_dnet = self._yani_response(nlp, res, list(cols))
            except Exception as _exc:                       # the caller falls back to the PMP terms' response
                if os.environ.get("CAPRI_TRACE_YANI"):
                    print("YANI response failed", self.data.region_id, repr(_exc), flush=True)
                self._yani_dnet = None
        self._last_npk = nlp.fert_outputs(res["x"]) if nlp.fert else None
        ab = nlp.abatement_outputs(res["x"]) if getattr(nlp, "abat", None) else {}
        self._nlp_abatement = ab
        if "catc" in ab:
            # the winter cover share chosen, for the cascade's accounts and the supply result (cover_crops)
            _c = spec["catc"]
            self._wc_solved = float(ab["catc"])
            self._cover_solved = {"req": self._wc_solved * _c["uaa"], "uaa": _c["uaa"], "base": _c["m0"] * _c["uaa"],
                                  "delta": (self._wc_solved - _c["m0"]) * _c["uaa"], "biofix": _c["biofix"],
                                  "share": self._wc_solved, "lb_share": float(_c.get("lb", 0.0)),
                                  "max_share": float(_c["ub"]), "endogenous": True,
                                  "potential": float(_c.get("potential", 0.0))}
        if self._last_npk:
            for nut, o_ in self._last_npk.items():
                gs = {g_["g"]: g_ for g_ in npk["nutrients"][nut]["groups"]}
                yv = np.asarray(nlp.f_y(res["x"])).ravel()
                o_["area"] = {g: float(sum(sh * yv[j] for j, sh in gs[g]["crops"])) for g in gs}
            if "N" in self._last_npk:
                # the allocation the regional model solved, for the accounts' report (fert_dist)
                self._fd_model = {"capri_region": npk["capri_region"], "flows": self._last_npk["N"]["flows"],
                                  "area": self._last_npk["N"]["area"], "converged": True}
        self._last_feed = F
        self._last_duals = zA
        # the columns' reduced costs at the NLP solution (IPOPT's bound multipliers, per unit of the column): the
        # manure pools read the trade columns' from here, as their duals through the A rows miss the fertilisation
        # block (manure applied reaches NUTNED_ and the purchases)
        self._nlp_rc = -np.asarray(res["lam_x"][:nlp.n0], float) / np.asarray(nlp.sc, float)
        self._nlp_ok = _nonopt is None
        if _nonopt is None:
            self._nlp_failed = None
        else:
            if getattr(self, "_nlp_fallback_log", None) is None:
                self._nlp_fallback_log = []
            self._nlp_fallback_log.append(f"nlp:{_nonopt} -> IPOPT's last point kept (non-optimal, as CAPRI)")
        self._nlp_status = str(info.get("status"))
        self._last_req_duals = info.get("req_duals") or {}
        self._manure_ni_relief, self._manure_ni_nh3, self._manure_ni_share = {}, {}, 0.0
        self._fert_inside_factor = {}
        self._fert_inside_weight = {}
        self._fert_tech_shares = {}
        if self._techs_inside():
            # the options' shares for the accounts (relief and NH3 saved per head from CAPRI's cascade)
            sh = {}
            for (a_, key_, tech_), v_ in (ab.get("amm") or {}).items():
                sh.setdefault((a_, key_), {})[tech_] = float(v_)
            self._amm_record(sh)
        if ab.get("fert"):
            self._fert_tech_shares = {k_: float(v_) for k_, v_ in ab["fert"].items()}
        if ab.get("mni") is not None and getattr(self, "_nlp_nip", None):
            _sh = float(ab["mni"]); _nip = self._nlp_nip
            if _sh > 1e-9:
                for a_, m_ in _nip["man_d"].items():
                    m_ = float(m_ or 0.0)
                    if m_ > 0 and a_ in self.acts:
                        self._manure_ni_relief[a_] = _nip["sub"] * _nip["nman"] * _sh * m_
                        if a_ in _nip["app_nh3"]:
                            self._manure_ni_nh3[a_] = _sh * _nip["app_nh3"][a_]
                self._manure_ni_share = _sh
                self._fert_tech_shares = dict(getattr(self, "_fert_tech_shares", None) or {})
                self._fert_tech_shares["NITR_INH_MAN"] = _sh
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

    def _nlp_solve(self, Q, c, A, b, x_start):
        """Solve the regional problem in CAPRI's form (_capri_nlp_solve, IPOPT), or None. With _nlp_try_n_relax set by
        the caller, a failure is marked "n_target" (_nlp_fb_last), and the caller retries at JRC121368's relaxed N
        target; with _nlp_accept_last set (the caller's last attempt), IPOPT's last point is kept, as CAPRI carries on
        with a non-optimal solve (supply/simu_supply.gms, widen_bounds.gms; p_INFES)."""
        self._last_npk = None
        self._nlp_rc = None
        self._last_feed_dm = None                  # never carry a previous solve's feed
        self._last_feed_t = None
        self._nlp_ok = False
        self._nlp_fb_last = False
        y = self._capri_nlp_solve(Q, c, A, b, x_start)
        if y is None and getattr(self, "_nlp_try_n_relax", False):
            self._nlp_fb_last = "n_target"
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
        _ov = getattr(self.data, "livestock_output_value_coef", None)
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
            if a in ANIMALS:
                # no stand-in from price x yield in guessed units (removed 23 October 2026): CAPRI's output value
                if float(self._base_levels().get(a, 0.0)) > 1e-8:
                    raise ValueError(f"{self.data.region_id} {a}: no CAPRI output value per head (TOOU / MREV)")
                gross[a] = 0.0
                continue
            gross[a] = prices_ser.get(a, 0.0) * yields_ser.get(a, 0.0)
        gross_rev = pd.Series(gross)
        self._gross_rev = gross_rev          # the curvature's revenue basis (diagnostics: tools/check/pmp_elasticity_target_check)

        calibrator = PMPCalibrator(self.acts, supply_elasticities, share_terms=st,
                                   cross_group_terms=cross_group_terms,
                                   cross_price_elas=cross_price_elas,
                                   capri_g=getattr(self.data, "pmp_capri", None))
        self.Q, self.f = calibrator.calibrate(
            base_levels=self._base_levels(),
            net_revenues=self.net_revenues,
            gross_revenues=gross_rev,
        )
        self.n_capri_pmp_acts = calibrator.n_capri_acts
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
                wp = read_csv(root / "world_prices.csv").set_index("commodity")["price"]
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

        # (The livestock yield-unit factors that turned price x YILD into EUR per head - 1e-3 for most animals, a
        # mass proxy for eggs - were removed 23 October 2026: animals take CAPRI's output value per head, TOOU / MREV,
        # below; one without it stops the run.)
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
            cost    = costs.get(act, 0.0)
            # LIVESTOCK COSTS on the same basis as livestock revenue: CAPRI's
            # regional total inputs (LEVL x TOIN) / the model's head count
            # (livestock_cost_coef.csv). The per-head TOIN in variable_costs is
            # on CAPRI's activity-level basis, which differs from the model's
            # heads several-fold for bulls and heifers.
            _cc = getattr(self.data, "livestock_cost_coef", None)
            if act in ANIMALS and _cc is not None and act in _cc.index \
                    and pd.notna(_cc[act]) and float(_cc[act]) > 0:
                cost = float(_cc[act])
            # CAPRI's PRME is the premium actually attached to each activity.
            # The instrument-level fallback (BPS applied to every crop and
            # nothing to livestock) both overstates crops -- 676.7 EUR/ha at
            # DE11 against CAPRI's 360.8 -- and zeroes livestock, where CAPRI
            # has 108.2 for dairy cows and 8.2 for bulls.
            premium = getattr(self.data, "cap_premium", None)
            revenue = price * yld
            _ov = getattr(self.data, "livestock_output_value_coef", None)
            _tou = (float(_ov[act]) if act in ANIMALS and _ov is not None and act in _ov.index
                    and pd.notna(_ov[act]) and float(_ov[act]) > 0 else None)
            _mrev = (float(rev_coef[act]) if act in ANIMALS and rev_coef is not None and act in rev_coef.index
                     and pd.notna(rev_coef[act]) else None)
            # CAPRI books no market revenue (MREV) for some activities in some regions (milk sheep and goats in the
            # Netherlands, Denmark and Sweden: no milk, output TOOU only): GAMS reads the absent item as 0
            if _mrev is None and _tou is not None:
                _mrev = 0.0
            if act in ANIMALS and not (_mrev is not None and (_mrev > 0 or _tou is not None)):
                if float(self._base_levels().get(act, 0.0)) > 1e-8:
                    raise ValueError(f"{self.data.region_id} {act}: no CAPRI output value per head (TOOU / MREV)")
                revenue = 0.0
            if _mrev is not None and (_mrev > 0 or _tou is not None):
                revenue = _mrev
                # with CAPRI's margin basis (switch below): total output TOOU
                if _tou is not None:
                    revenue = _tou
                    # a commodity price moves the market part (MREV) only; young animals
                    # (the rest of TOOU) move with their own prices (young-animal markets)
                    if price_shock is not None and _mrev > 0:
                        revenue += self._market_revenue_change(act, _mrev, price_shock)
                elif price_shock is not None:
                    revenue *= 1.0 + float(price_shock.get(act, 0.0))

            _pc = getattr(self.data, "livestock_premium_coef", None)
            if act in ANIMALS and _pc is not None \
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
            # at base nothing changes. Protein feed (oilseed cakes, CAPRI's SOYC,
            # RAPC, SUNC) is priced through the FPRO bulk or, without it, the
            # soya cake row of feed_requirements.csv (_protein_feed_cost_change).
            if act in ANIMALS and price_shock is not None and act not in (getattr(self, "feed_rations", None) or {}):
                # With feeding inside the regional model (a ration for the animal) the feed is
                # bought in the model at its current prices (QUADRF_ in capri_regional_nlp.py, the base
                # ration's cost taken out of the linear term), as CAPRI costs feed once (supply_model.gms QUADRF_); the
                # change below would count it twice (audit S1, fixed 24 October 2026). It applies where the animal's
                # feeding is not in the model.
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
                        for feed in ("SWHE", "BARL", "CORN", "RYEM", "OATS", "OCER"):
                            if feed in fr.columns:
                                q = float(fr.at[act, feed]) * mult
                                if q > 0:
                                    p0 = float(self.data.producer_prices.get(feed, 0.0))
                                    cost += q * p0 * float(price_shock.get(feed, 0.0))
                        if "SOYC" in fr.columns:
                            q = float(fr.at[act, "SOYC"]) * mult
                            if q > 0:
                                cost += self._protein_feed_cost_change(q, price_shock)
            # Crop gross margin (EUR/ha); animal gross margin (EUR/head)
            r[act] = revenue - cost + payment

        self.net_revenues = pd.Series(r)

    # ------------------------------------------------------------------
    # Constraint matrix
    # ------------------------------------------------------------------


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
        "TAGR": "nonfruit_perm", "WINE": "nonfruit_perm", "OLIV": "nonfruit_perm", "TABO": "nonfruit_perm",
    }

    #: CAPRI's organicCrops (pol_input/greendeal/load_organic_targets.gms l. 201-233; CERE_COLS and OILS_COLS from
    #: global/fromimpact/sets.gms), in model codes (MAIZ = CORN, TWIN = WINE): the crops whose own organic target
    #: tops up other inputs (organic_io.gms) and, where grouped, lowers yields (organic_area.gms). Grassland, fodder,
    #: other oilseeds and the minor crops are not organic crops: only the regional plant-protection and other-input
    #: changes reach them.
    ORGANIC_CROPS = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER", "PARI", "RAPE", "SUNF", "SOYA",
                     "TOMA", "POTA", "OVEG", "PULS", "SUGB", "TEXT", "TOBA",
                     "APPL", "OFRU", "CITR", "TAGR", "TABO", "WINE", "OLIV")
    #: p_organicAreaTargetCrops of each organic crop: its NGRP group's target (ngrp_to_organicCrops, l. 240-258, and
    #: crops_to_ngrp, l. 148-165: the arable groups take Eurostat's arable target, PERM the permanent-crop target, VEGE
    #: the UAA target, l. 187); organic crops in no group (PARI, TEXT, TOBA) take the UAA target (l. 269-271)
    ORGANIC_CROP_TARGET = {**{a: "arable_pp" for a in ("SWHE", "DWHE", "BARL", "CORN", "RYEM", "OCER", "OATS", "RAPE",
                                                       "SUNF", "SOYA", "PULS", "SUGB", "POTA")},
                           **{a: "permanent_pp" for a in ("APPL", "OFRU", "CITR", "TAGR", "TABO", "WINE", "OLIV")},
                           **{a: "uaa_pp" for a in ("TOMA", "OVEG", "PARI", "TEXT", "TOBA")}}
    #: organic crops whose yield takes the organic yield gap: in an NGRP group (organic_area.gms l. 191-193 rescales by
    #: the group's target, so PARI, TEXT, TOBA get none) and with a gap estimate (pact2yieldGap,
    #: inputs/load_organic_yieldgap.gms l. 93-140: none for PULS, SUGB)
    ORGANIC_YIELD_GAP_CROPS = ("SWHE", "DWHE", "CORN", "RYEM", "BARL", "OATS", "OCER", "RAPE", "SUNF", "SOYA",
                               "TOMA", "POTA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "WINE", "OLIV")
    #: CAPRI-ERROR-FIX (setting supply.greendeal_inputs_keep_tech_change): define_inputs.gms l. 66-73 applies a
    #: scenario's regional input change as (1 + change) x the input-saving progress TF_I only when the global
    #: scenAugmentsTechChange is on. organic_io.gms l. 94 and conventional_io.gms l. 171 set it on, but
    #: conventional_io.gms l. 361 sets it off at compile time in its other branch, which comes later in the file, so
    #: the Green Deal runs replace the progress instead of multiplying it (CAPRI's own notes, l. 176 and
    #: greendeal_scenarios.gms l. 137-138, call the off setting an oversight). false: CAPRI's code as written.
    greendeal_inputs_keep_tech_change = setting("supply.greendeal_inputs_keep_tech_change")
    #: CAPRI-ERROR-FIX (setting supply.organic_topup_at_fuel_cost): organic_io.gms l. 107-115 tops up other inputs
    #: of each organic crop by its EFUL coefficient x 2 x its organic target, "assuming that costs for EFUL+SERI would
    #: double", but adds the fuel coefficient to the INPO coefficient, so it is valued at INPO's unit value instead of
    #: fuel's. true: valued at the fuel cost; false: CAPRI's code as written.
    organic_topup_at_fuel_cost = setting("supply.organic_topup_at_fuel_cost")

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
    #: with in tools/build/build_capri_base.py. Everything else except grass is arable.
    PERMANENT_LAND_CROPS = ("WINE", "OLIV", "TABO", "APPL", "OFRU", "CITR", "TAGR")

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

    #: The crops the pesticide yield loss reaches (the jrc121368 rule only; CAPRI star 3.0 calls conventional_io.gms
    #: with the yield shock off).
    PESTICIDE_AFFECTED = (
        # CORN is grain maize in this activity set; "MAIZ" (used here before)
        # is not an activity, so the pesticide target silently skipped it.
        "SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER",      # cereals
        "RAPE", "SUNF", "SOYA", "OOIL",                              # oilseeds
        "TOMA", "OVEG", "POTA", "SUGB", "PULS",                      # veg/other arable
        "APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV", "TABO",      # permanent
    )

    #: Livestock activities whose gross-output unit is not established. Their
    #: gross_output is reported as NaN rather than as a number that looks
    #: plausible and is not. DCOW is excluded because it verifies against real
    #: EU milk output (142,000 kt against ~155,000); every other animal activity
    #: fails that check by a factor no single rescaling explains.
    UNVERIFIED_OUTPUT_UNITS = ("BULL", "LAYS", "BROI", "CALV", "SHGM", "SHGF",
                               "HFRS", "BCOW", "PIGS", "OANI")

    #: Share of total input cost that is fertiliser (CAPRI FERT, EU-wide, all 27 member states' 2017 data;
    #: tools/build/build_crop_cost_shares.py): FALLBACK for the fertiliser cost per ha of a crop CAPRI does not grow
    #: in the region (the regional rows of plant_protection_cost.csv serve the others).
    FERT_COST_SHARE = _csv_dict("2017/supply/crop_cost_shares.csv", "fert_cost_share")

    def _input_cost(self, a: str, item: str, share_table: dict) -> float:
        """EUR/ha of input `item` (used for 'fert') for crop a: CAPRI's regional cost
        (tools/build/build_plant_protection_cost.py), else the EU-wide share of input cost times the
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
                                  organic_share: Optional[float] = None, yield_loss: bool = True) -> None:
        """Apply the Farm-to-Fork pesticide target as CAPRI does (pol_input/greendeal/conventional_io.gms).

        Here: the yield loss on the conventional area of the affected crops (the jrc121368 rule; CAPRI star 3.0
        calls conventional_io.gms with the yield shock off) and the minimum catch-crop area (pesticide cut / 2, see
        _cover_crop_requirement). The plant-protection and other-input changes are regional and are set together
        with the organic target's in _apply_greendeal_input_changes.

        The loss is scaled linearly from CAPRI's 50% reference, and net revenue
        is rebuilt from the reduced yields so the price and CAP components stay
        intact. Mutates net_revenues for one solve; the caller restores it.
        """
        reduction = float(reduction)
        if reduction <= 0:
            return
        # yield_loss False: CAPRI star 3.0's Green Deal group (pesticides.gms: the yield shock 'off')
        loss = self.PESTICIDE_YIELD_LOSS_AT_50PCT * (reduction / 0.50) if yield_loss else 0.0
        # (a cap of the loss at 0.90 was removed 23 October 2026: unsourced and never reached - the loss is at most
        # 0.20, at a 100% cut)

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
            # The yield loss must reach BOTH the objective and the reported
            # yields. It used to change net revenue only, so it steered what
            # farmers grew but left gross_output computed on unshocked yields:
            # EU cereal PRODUCTION fell 6% where CAPRI reports 15%, even though
            # our cereal AREA fell 5.9% against CAPRI's 4%. The area response
            # was never the problem; the yield effect was missing from the
            # output. CAPRI reports production, so this is what is compared.
            new_ylds[a] = y * (1.0 - loss * conv)
            nr[a] = float(nr.get(a, 0.0)) - p * y * loss * conv
        # plant protection and other inputs: CAPRI's regional input changes, set with the organic target's in
        # _apply_greendeal_input_changes (24 October 2026; before, per crop on the conventional share: KNOWN_ISSUES K74 S3/S4)
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
            _YIELD_ELAS = {r.crop: float(r.elasticity) for r in read_csv(f).itertuples()}
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
        # the price response's factor per crop: CAPRI's straw yield (and so the straw part of the nutrient need)
        # follows the scenario's yield shifts but not this response (supply/endog_yields.gms; need_yield_factor)
        pf = {}
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
            pf[a] = factor
            p = float(prices.get(a, 0.0)) * (1.0 + dp)
            # the extra revenue from the yield change alone
            nr[a] = float(nr.get(a, 0.0)) + p * y0 * (factor - 1.0)
        self.data.yields = new_ylds
        self.net_revenues = nr
        self._yield_price_factor = pf


    def _organic_yield_gap(self, activity: str) -> float:
        """Organic yield gap for one activity in this region, as a fraction: CAPRI's estimate for the region's PESETA
        macro-region and the product group, else the Central-European (CEN) one, as CAPRI borrows it
        (organic_area.gms l. 176-181; e.g. maize in NE and UK_IR). Before 24 October 2026 a flat 20% from the
        literature (ORGANIC_YIELD_GAP) took CEN's place."""
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
        if table is None or not group or region is None:
            return 0.0
        for reg_ in (region, "CEN"):
            v = table.at[reg_, group] if (reg_ in table.index and group in table.columns) else None
            if v is not None and pd.notna(v):
                return abs(float(v)) / 100.0
        return 0.0


    @staticmethod
    def _organic_target_scale(share: float) -> float:
        """CAPRI's scaling of its targets to the requested ambition, (orgTarg - 12) / (25 - 12)
        (load_organic_targets.gms l. 175, 183; orgTarg in %): exactly 1 at the 25% target."""
        return max(0.0, (100.0 * float(share) - 12.0) / (25.0 - 12.0))

    def _organic_region_target(self, share: float) -> float:
        """p_organicAreaTarget(ru): the member state's UAA target (organic_targets_uaa.gdx) scaled to the ambition.
        A region without CAPRI's targets (outside the EU) takes the EU distance-to-target fallback, as
        _organic_converted does."""
        t = getattr(self.data, "organic_targets_pp", None)
        v = t.get("uaa_pp") if (t is not None and hasattr(t, "get")) else None
        if v is None or pd.isna(v):
            return max(0.0, float(share) - self._organic_baseline())
        return max(0.0, min(1.0, float(v) / 100.0 * self._organic_target_scale(share)))

    def _organic_crop_target(self, activity: str, share: float) -> float:
        """p_organicAreaTargetCrops(ru, crop) of CAPRI's organic crops (0 for the other crops): the target of the
        crop's NGRP group (ORGANIC_CROP_TARGET). A member state with no value for the group in CAPRI's
        organic_targets.gdx gets 0, as in CAPRI (Portugal: no arable or permanent-crop entry; Ireland: no permanent,
        Malta: no grassland)."""
        col = self.ORGANIC_CROP_TARGET.get(activity)
        if col is None:
            return 0.0
        t = getattr(self.data, "organic_targets_pp", None)
        if t is None or not hasattr(t, "get"):
            return max(0.0, float(share) - self._organic_baseline())
        v = t.get(col)
        if v is None or pd.isna(v):
            return 0.0
        return max(0.0, min(1.0, float(v) / 100.0 * self._organic_target_scale(share)))

    def _input_row(self, activity: str, col: str) -> Optional[float]:
        """CAPRI's cost row of this region and activity (data.input_costs_ha, build_plant_protection_cost.py), or
        None where CAPRI has none."""
        t = getattr(self.data, "input_costs_ha", None)
        if t is None or activity not in t.index or col not in t.columns:
            return None
        v = t.at[activity, col]
        return float(v) if pd.notna(v) else None

    def _greendeal_tech_progress(self) -> float:
        """CAPRI's input-saving progress of the simulation year, TF_I = 1 - 0.005 x (Y - BAS)
        (capmod/define_inputs.gms l. 66)."""
        base = int(str(_settings().get("run.base_year")))
        sim = int(getattr(self.data, "sim_year", None) or base)
        return 1.0 - 0.005 * (sim - base)

    def _apply_greendeal_input_changes(self, organic_share: float, pesticide_reduction: float) -> None:
        """CAPRI's plant-protection (PLAP) and other-input (INPO) changes of the Green Deal organic and pesticide
        targets, in an EU region.

        CAPRI sets them as one regional percentage change per input (DATA(ru, "GROF", I, "percentageChange")) that
        define_inputs.gms l. 70-73 applies to the coefficient of EVERY activity (animals' other inputs included), and
        tops up the organic crops' other inputs:
          organic_io.gms l. 74      PLAP: -100 x o_R  (o_R the region's UAA target)
          organic_io.gms l. 111-115 INPO of each organic crop + EFUL x 2 x its crop target (the top-up)
          conventional_io.gms l. 90-275 (with organic targets) or l. 276-463 (without), when o_R < r:
                                    PLAP: -r overall (the remaining target on the conventional area plus the organic
                                    part); INPO: +otherCostChange x remaining / r = +(r - o_R), pesticides.gms passing
                                    otherCostChange = r
        r is the pesticide reduction. The scenario coefficient is (base + top-up) x (1 + change) x TF_I with
        CAPRI-ERROR-FIX greendeal_inputs_keep_tech_change, or (base + top-up) x (1 + change) without TF_I as CAPRI's
        code runs (see the setting); the baseline's is base x TF_I. The model's costs are CAPRI's 2017 coefficients
        valued at 2017 unit values (REGISTERED: CAPRI changes its simulation-year coefficients; their yield-dependent
        part follows the yields in _apply_yield_input_costs, at these changes' TF_I).
        """
        r = max(0.0, float(pesticide_reduction or 0.0))
        o_R = self._organic_region_target(organic_share) if organic_share else 0.0
        pc_plap = -o_R if o_R > 0 else 0.0
        pc_inpo = 0.0
        if r > 0 and o_R < r:
            pc_plap = -r
            pc_inpo = r - o_R
        tf = self._greendeal_tech_progress()
        keep_tf = bool(getattr(type(self), "greendeal_inputs_keep_tech_change", True))

        def delta(base: float, topup: float, pc: float) -> float:
            # change of the cost against the baseline (base x TF_I); TF_I is replaced only where CAPRI sets a change
            if pc == 0.0:
                return tf * topup
            return (base + topup) * (1.0 + pc) * (tf if keep_tf else 1.0) - base * tf

        topup_col = "eful_eur_ha" if getattr(type(self), "organic_topup_at_fuel_cost", True) else "eful_inpo_eur_ha"
        nr = self.net_revenues.copy()
        self._greendeal_inputs = {"o_R": o_R, "pc_plap": pc_plap, "pc_inpo": pc_inpo, "tf": tf, "keep_tf": keep_tf}
        for a in self.acts:
            d = 0.0
            if a in ANIMALS:
                sh = self._input_row(a, "inpo_toin_share")
                if sh is not None and pc_inpo != 0.0:
                    d = delta(sh * self._animal_cost_per_head(a), 0.0, pc_inpo)
            else:
                plap = self._input_row(a, "plap_eur_ha")
                inpo = self._input_row(a, "inpo_eur_ha")
                if plap is not None and pc_plap != 0.0:
                    d += delta(plap, 0.0, pc_plap)
                if inpo is not None:
                    o_a = self._organic_crop_target(a, organic_share) if organic_share else 0.0
                    eful = self._input_row(a, topup_col) or 0.0
                    topup = 2.0 * o_a * eful
                    if topup or pc_inpo:
                        d += delta(inpo, topup, pc_inpo)
            if d:
                nr[a] = float(nr.get(a, 0.0)) - d
        self.net_revenues = nr

    def _apply_yield_input_costs(self) -> None:
        """The crops' input costs follow their yields, as CAPRI's define_inputs.gms sets the coefficient of a directly
        yield-dependent input (sets.gms IY: seed, plant protection, repairs, energy, irrigation, other inputs,
        services) to BAS x (1 - f + f x G) x TF_I, G the yield growth since the base year (bounded 0.5-1.5) and f
        CAPRI's p_inputDemandFactor. CAPRI re-runs it after the scenario's yield shifts (capmod/shift_yields.gms) and
        after each price-driven yield update (supply/endog_yields.gms), so against the 2030 reference the cost per ha
        moves by
            sum_i f_i x cost_i x G x TF_I x (rho - 1),   rho = yield now / reference yield
        (build_plant_protection_cost.py: yd_rest, yd_plap, yd_inpo per ha; TF_I with the Green Deal changes of PLAP
        and INPO, _apply_greendeal_input_changes). Fertiliser is not in IY: it follows the crops' need
        (need_yield_factor). REGISTERED: the model's costs are CAPRI's 2017 coefficients (no yield-growth or TF_I term
        in the baseline cost); the change above is CAPRI's derivative at its 2030 reference."""
        y0s, yc = getattr(self, "_yields_solve0", None), self.data.yields
        if y0s is None or not hasattr(yc, "get") or not hasattr(y0s, "get"):
            return
        tf = self._greendeal_tech_progress()
        gi = getattr(self, "_greendeal_inputs", None) or {}
        keep = bool(gi.get("keep_tf", True))
        tf_of = lambda pc: tf if not pc else (1.0 + pc) * (tf if keep else 1.0)
        tf_p, tf_i = tf_of(float(gi.get("pc_plap", 0.0) or 0.0)), tf_of(float(gi.get("pc_inpo", 0.0) or 0.0))
        nr = None
        for a in self.acts:
            if a not in CROPS:
                continue
            y0, y = float(y0s.get(a, 0.0) or 0.0), float(yc.get(a, 0.0) or 0.0)
            if not (y0 > 0 and y > 0) or y == y0:
                continue
            k = ((self._input_row(a, "yd_rest_eur_ha") or 0.0) * tf + (self._input_row(a, "yd_plap_eur_ha") or 0.0) * tf_p
                 + (self._input_row(a, "yd_inpo_eur_ha") or 0.0) * tf_i)
            if k:
                g = self._input_row(a, "yield_growth") or 1.0
                # CAPRI's bounds on the yield growth: G x rho within 0.5-1.5
                d = (min(1.5, max(0.5, g * y / y0)) - g) / g if g > 0 else (y / y0 - 1.0)
                if nr is None:
                    nr = self.net_revenues.copy()
                nr[a] = float(nr.get(a, 0.0)) - k * d
        if nr is not None:
            self.net_revenues = nr

    def _animal_cost_per_head(self, act: str) -> float:
        """The model's input cost per head of an animal activity, as _compute_net_revenues uses it: CAPRI's
        LEVL x TOIN per model head (livestock_cost_coef) where that is on, else the per-head TOIN."""
        _cc = getattr(self.data, "livestock_cost_coef", None)
        if _cc is not None and act in _cc.index \
                and pd.notna(_cc[act]) and float(_cc[act]) > 0:
            return float(_cc[act])
        return float(self.data.variable_costs.get(act, 0.0))

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

    def apply_organic_area_target(self, share: float) -> None:
        """Adjust average I/O coefficients for an organic AREA target (CAPRI pol_input/greendeal/organic_area.gms,
        organic_io.gms '100' 'off' 'off' '50').

        CAPRI does not track organic and conventional activities separately but adjusts the average coefficients of
        a region in proportion to its organic targets (p_organicAreaTarget for the region's UAA,
        p_organicAreaTargetCrops for the organic crops). Here: the organic yield gap of the organic crops
        (organic_area.gms PART III) and the fertiliser saving on converted land. Plant protection (-100% x the UAA
        target, every crop) and other inputs (the organic crops' top-up) are set in _apply_greendeal_input_changes,
        together with the pesticide target's changes, since CAPRI applies both through one regional input factor.

        Mutates net_revenues for the duration of one solve; the caller's finally block restores it.
        """
        share = float(share)
        if share <= 0:
            return

        prices = self.data.producer_prices
        ylds = self.data.yields
        new_ylds = ylds.copy()
        nr = self.net_revenues.copy()
        converted_default = max(0.0, float(share) - self._organic_baseline())
        _org = getattr(self.data, "organic_targets_pp", None)
        for a in self.acts:
            converted = self._organic_converted(a, share, _org, converted_default)
            if a not in CROPS:
                continue
            p = float(prices.get(a, 0.0))
            y = float(ylds.get(a, 0.0)) if hasattr(ylds, "get") else 0.0
            if p <= 0 or y <= 0:
                continue
            # CAPRI's organic yield gaps are FADN-based estimates by macro-region and product group (JRC Seville for
            # the SUPREMA project, loaded in organic_area.gms): e.g. Southern Europe fruits 22.5%, olives and vines
            # 11.6%; Central Europe fruits 51.3%, cereals 42.9%.
            # the organic yield gap (organic_area.gms PART III, l. 176-199): organic crops in an NGRP group with a gap
            # estimate, scaled by the crop's organic target (before 24 October 2026: every crop with a gap group,
            # grassland, fodder and other oilseeds included, at the arable / grassland / permanent target)
            # No 0.45 discount: organic_area.gms applies it only with %pest_disagg% on (an endogenous pesticide yield
            # response, v_yldPestFac), which the Farm-to-Fork set-up does not use.
            o_y = self._organic_crop_target(a, share) if a in self.ORGANIC_YIELD_GAP_CROPS else 0.0
            gap = self._organic_yield_gap(a) if o_y > 0 else 0.0
            yield_factor = 1.0 - gap * o_y
            # the fertiliser saving on converted land (its cost leaves the objective here; in the NLP form the
            # conventional share's cost is replaced by the priced purchases). Plant protection and other inputs:
            # _apply_greendeal_input_changes (CAPRI's regional changes and the organic crops' top-up)
            cost_change = -converted * self._input_cost(a, "fert", self.FERT_COST_SHARE)
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
                # the conventional share alone, for CAPRI's minimum mineral share (NUTMIN_: 0 on organic land)
                self._organic_conv = getattr(self, "_organic_conv", {}) or {}
                self._organic_conv[a] = self._organic_conv.get(a, 1.0) * max(0.0, 1.0 - converted)
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
        uaa = (self._land_of("ARABLE")
               + self._land_of("PERMANENT")
               + self._land_of("GRASSLAND"))
        return base_n / uaa if uaa > 0 else 0.0


    def _manure_techs(self):
        """CAPRI's ammonia technologies for this region: {animal: [sub-activity block]}
        (capri_data/2017/abatement/ammonia/ammonia_tech_model.csv, capri_mod/supply/ammonia_techs.py)."""
        from pathlib import Path as _P
        from capri_mod.supply import ammonia_techs as _at
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia" / "ammonia_tech_model.csv"
        techs = _at.load(f).get(self.data.region_id, {})
        # Cost basis (KNOWN_ISSUES K63): CAPRI prices the options per animal place, places = v_actLevl x DAYS / 365
        # (GHG_Mit_Cost_), and stock_factor is DAYS / 365 per unit of CAPRI's activity level. The model's animal units
        # are its own heads (capri_level_ratio = model heads per CAPRI level unit: fattening pigs ~0.5, bulls ~0.4,
        # heifers ~0.2, poultry 250-1000), while the N an option saves is per model head (manure N per head). Places
        # per model head are therefore stock_factor / ratio; before 21 October 2026 the cost used stock_factor per
        # model head, so per unit of N saved the options of those animals cost ratio x CAPRI's (fattening pigs about
        # half, poultry 250-1000 times). Copies: _at.load's table is shared.
        rat = getattr(self.data, "capri_level_ratio", None)
        if techs and rat is not None:
            out = {}
            for a, subs in techs.items():
                r_ = rat.get(a) if hasattr(rat, "get") else None
                r_ = float(r_) if r_ is not None and r_ == r_ and float(r_) > 0 else 1.0
                out[a] = [dict(s_, stock=float(s_["stock"]) / r_) for s_ in subs] if r_ != 1.0 else subs
            return out
        return techs

    def _winter_cover_shares(self):
        """(base, current) winter cover share of the region, CAPRI's v_Miti(CATC, WinterCov): the 2030 catch-crop share
        (cover_crops.csv catc_share_2030, CAPRI's value) and, under the Farm-to-Fork catch-crop requirement, the required
        area over UAAR (self._cover)."""
        cc = getattr(self.data, "cover_crops", None)
        w0 = 0.0
        if cc is not None and hasattr(cc, "get"):
            v = cc.get("catc_share_2030")
            w0 = float(v) if v is not None and not pd.isna(v) else 0.0
        if getattr(self, "_wc_solved", None) is not None:
            return w0, float(self._wc_solved)                     # chosen in the NLP form
        cv = getattr(self, "_cover", None)
        w1 = float(cv["req"]) / float(cv["uaa"]) if cv and float(cv.get("uaa", 0.0) or 0.0) > 0 else w0
        return w0, w1

    def _amm_record(self, shares: dict):
        """Accounts for given shares {(animal, sub): {tech: share}} (missing: base shares):
        N relief and NH3 saved per activity unit, extra cost per unit, reported shares (share
        of the animal's units) and the shares for the next linearisation."""
        from capri_mod.supply import ammonia_techs as _at
        self._animal_n_relief, self._animal_nh3_saved, self._manure_tech_shares = {}, {}, {}
        self._animal_n_kept = {}
        self._amm_cost = {}
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
        wc0, wc1 = self._winter_cover_shares()
        last = {}
        for a, subs in techs.items():
            mN, f = float(man_d.get(a, 0.0) or 0.0), float(nh3.get(a, 0.0) or 0.0)
            if a not in self.acts or mN <= 0 or f <= 0:
                continue
            sc = self._amm_scale(subs, mN, f)
            saved = cost = nh3s = 0.0
            for s in subs:
                ini = _at.initial(s)
                sh = dict(ini); sh.update(shares.get((a, s["key"]), {}))
                last[(a, s["key"])] = sh
                # N kept in the manure (CAPRI's GasRunTot through the cascade) and the NH3 part of it
                saved += s["w"] * sc * s["mrel"] * (_at.loss(s, ini, wc0) - _at.loss(s, sh, wc1))
                nh3s += s["w"] * sc * s["mrel"] * (_at.nh3(s, ini, wc0) - _at.nh3(s, sh, wc1))
                cost += s["w"] * s["stock"] * _at.cost(s, sh)
                for t in s["techs"]:
                    k = (a, t["tech"])
                    self._manure_tech_shares[k] = self._manure_tech_shares.get(k, 0.0) + s["w"] * sh[t["tech"]]
            if abs(saved) > 0 or abs(nh3s) > 0:
                self._animal_n_relief[a] = sub * saved
                self._animal_n_kept[a] = saved
                self._animal_nh3_saved[a] = nh3s
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
            return          # decided inside the regional model: keep its results
        from capri_mod.supply import ammonia_techs as _at
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
            return                       # decided inside the regional model
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        lam = float(lam or 0.0)
        if lam <= 0 and tax <= 0:
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

    def _ni_inside(self) -> bool:
        """Inhibitors on manure as a decision of the regional model (no N-price search)."""
        return self._techs_inside()

    def _manure_inhibitor_params(self):
        """The parameters of CAPRI's inhibitor on manure for this region (see _apply_manure_inhibitor), or None:
        sub, nman, smax, S0, slope (EUR per t of manure N), app_nh3 (t NH3-N per activity unit at full adoption),
        v_tax (EUR per t of manure N treated), man_d (t manure N per activity unit)."""
        tax = float(getattr(self, "ghg_tax", 0.0) or 0.0)
        # national entry (fert_options_jul15.csv is keyed by CAPRI codes)
        _ms = capri_ms(self.data.region_id)
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
                app = sum(s_["w"] * sc * s_["mrel"] * _at.app_loss(s_, last.get((a, s_["key"]), _at.initial(s_)),
                                                                    self._winter_cover_shares()[1])
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
            # decided inside the regional model: keep its results (a reset here, after
            # the last solve, erased the reported shares; the inhibitor on manure is inside too,
            # _apply_manure_inhibitor returns at once)
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
        uaa = (self._land_of("ARABLE")
               + self._land_of("PERMANENT")
               + self._land_of("GRASSLAND"))
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
                fs = read_csv(root / "environment" / "fertiliser_substitution_2030.csv").set_index("region")
                c["av"] = fs["manure_availability"].to_dict()
            except Exception:
                c["av"] = {}
            try:
                fp = read_csv(root / "supply" / "mineral_n_price.csv").set_index("country")
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
                  "grassland": [(li["GRAS"], 1.0)],
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
        # CAPRI takes the land rents as given in its calibration (supply/cal_land_nests.gms, prep_cal.gms l. 125-156):
        # at the 2030 calibration point the land market is balanced at CAPRI's rents, not at the model's recovered
        # duals (docs/LAND_RENT_CALIBRATION_PLAN.md)
        # Every land type with a level in CAPRI's region has a positive calibration rent (tools/build/build_land_rents.py
        # applies cal_land_nests.gms l. 204-226 where CAPRI's reported D_AREA is not positive). Before 23 October 2026
        # the base dual recovered from the model's own QP solution stood in at 2017 and for those cells at 2030; that QP
        # carried a 1% shadow-price proxy and a 15% grassland headroom (no proxies: removed). A land type without a
        # CAPRI rent has no level in CAPRI's region: rent 0.
        _rents = getattr(self.data, "land_rents", None)
        if _rents is None:
            raise ValueError(f"{self.data.region_id}: no CAPRI land rents for the land market (land_rents_<year>.csv)")
        _rlab = {"arable_land": "ARAC", "permanent_land": "FRUN", "grassland": "GRAS"}
        self._land_rent_rows = {}
        for lab, coeffs in rowmap.items():
            t_ = _rlab.get(lab)
            m_ = float(_rents.get(t_, 0.0)) if _rents.get(t_, 0.0) == _rents.get(t_, 0.0) else 0.0
            self._land_rent_rows[lab] = m_
            for j, cf in coeffs:
                ca[n + j] += m_ * cf
            # the activities' side of the same calibration (CAPRI's FOC at the calibration point, prep_cal.gms /
            # cal_land_nests.gms: revenue - cost - PMP marginal - land rent x land use = 0): the land row's dual at
            # the base is the rent, so the activities' linear terms carry it. Without this the rent was charged by
            # the land market but not in the activities' calibration, and the plain path (no NLP calibration) lost
            # 8-11% of its crops at base (KNOWN_ISSUES K68); the NLP form recalibrates its linear terms at the base
            # and absorbed the difference
            if lab in labels and m_:
                ca[:n] -= m_ * np.asarray(A_ub[labels.index(lab), :n], dtype=float)
        # ---- SURPLUS PER HECTARE OF CURRENT LAND (CAPRI e_SURTOTHa, e_EXCRET:
        # divided by sum(landTypesNoSlak, v_actLevl)). With it, a region gains
        # nothing per hectare by giving up farmland, and expanding it costs land
        # (land market). Limit = target per ha x (ARAC + GRAS + FRUN), as a
        # deviation from base land - identical at base.
        if "N_balance" in labels:
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
        # base mineral N x fertiliser intensity x need factor of the yield (_need_yf) - the
        # same terms the N row already applies (a first version used the BASE
        # amount and double-counted, turning crops into N sinks: pigs fell more,
        # not less). Crop need = current mineral N + manure-covered need (spread
        # by uptake, so the row returns exactly the base mineral N at base). The
        # N row takes M instead of crops' current mineral N; fertiliser is charged
        # on M at CAPRI's price (UVAG NITF) with the per-ha charge added back;
        # constants shift by the allocation row's base dual (= that price).
        k_extra = 0
        self._cover_dbf_nb = 0.0
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
                                f_ *= self._need_yf(a, y0, yc)
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
                    labels.append("alloc_mineral_N")
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
                        self._cover_dbf_nb = dbf          # (the NLP form's chosen catch crops replace it)
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
                        nb_now = env_.compute_nitrogen_balance(cur, self.data.yields, self.data.region_id,
                                                               yields_scen=self._yields_scen_now())
                        if float(nb_now.get("n_mineral_input", 1.0)) <= 1e-6:
                            sub = 0.0
                    except Exception as _exc:
                        import warnings as _w
                        _w.warn(f"manure market: substitution factor unavailable for "
                                f"{self.data.region_id} ({_exc!r}); using availability")
                        sub = float(a_av)
                if man0 > 1e-6:
                    pp = float(getattr(self, "manure_pool_price", 0.0) or 0.0)
                    # CAPRI supply/define_manure_trade_costs.gms l. 66-71: p_manureBuyCostSlope = 50 / (GROF / 100), EUR
                    # 50 per t N for each 1% of the region's manure N supply traded. man0 is in t N (kg N per unit x
                    # 1000 units) and the objective in EUR 1000, so CAPRI's 50 is 0.05 here (supply.manure_pool_slope)
                    slope = float(_settings().get("supply.manure_pool_slope")) / (man0 / 100.0)
                    i_ma = labels.index("manure_application") if "manure_application" in labels else None
                    # emission tax: the mineral N bought (export) or saved (import), sub x the accounts' soil N2O
                    # factor and the indirect N2O of its runoff and leaching per t N (kt CO2-eq x EUR/t = 1000 EUR);
                    # the NLP form takes exactly this term out again (_nlp_tax_terms), mineral N being endogenous there
                    g_ = float(getattr(self, "ghg_tax", 0.0) or 0.0) * sub \
                        * (self._ef_mineral_n2o() + self._ef_mineral_lea()) / 1000.0
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
                    labels.append("manure_export_cap")
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
                                    v *= self._need_yf(a, y0, yc)
                            need[j] = v
                    man = np.array([float(man_d.get(a, 0.0)) for a in self.acts])
                    # the nitrate additive's extra manure N displaces mineral N like any manure (the accounts:
                    # mineral - sub x extra); on the N row it was, on this row not (K9)
                    _nx = self._nitrate_extra()
                    man_now = man + np.array([float(_nx.get(a, 0.0)) for a in self.acts])
                    cap = np.zeros(Aa.shape[1]); cap[:n] = -need + sub_n * man_now
                    pc_ = getattr(self, "_pool_cols", []) or []
                    if len(pc_) == 2:
                        cap[pc_[0]] = -sub_n; cap[pc_[1]] = +sub_n
                    xb_ = np.maximum(self._base_levels().reindex(self.acts).fillna(0.0).values, 0.0)
                    v0 = float(cap[:n] @ xb_)
                    Aa = np.vstack([Aa, cap]); ba = np.concatenate([ba, [max(0.0, v0) + 1e-9 * max(1.0, float(need @ xb_))
                                                                         - self._cover_n_increment()]])
                    self._need_row = Aa.shape[0] - 1
                    labels.append("crop_need")
        k_extra = alloc_k + pool_k
        tot = np.zeros(n + k + k_extra); tot[n:n + k] = 1.0
        allow = float(getattr(self, "grassland_allowance", 0.0))
        grs = np.zeros(n + k + k_extra); grs[n + li["GRAS"]] = -1.0
        # TOTAL LAND IS CONSERVED (CAPRI's land-use balance: the land types add up to the region's
        # area). As an upper bound only, land leaving farming could vanish: under the nitrogen target
        # Brittany's land types fell from 2,328 to 1,495 kha, forest included. Now land leaving
        # farming goes to forest and other land, at the land market's own transformation costs.
        Aa = np.vstack([Aa, tot, -tot, grs])
        labels.extend(["land_total_up", "land_total_lo", "grassland_floor"])
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
        extra_r, extra_b = [], []
        xb_ = np.concatenate([np.maximum(np.asarray(x0, dtype=float), 0.0), L0])
        for i, coeffs, const in rows:
            scale = float(np.abs(Aa[i]).max()) if Aa[i].any() else 1.0
            # (never above the row's own limit: base crops exceed some regions' land data by
            # rounding, 0.002 kha in Brittany, and the pair of rows was then infeasible)
            used = min(float(Aa[i, :n + k] @ xb_), float(const))
            extra_r.append(-Aa[i].copy()); extra_b.append(-used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale)
            # the upper row at the base use too: an equality, as CAPRI's LandBalNoSlak_. The grassland row kept the
            # land data's headroom above the base use (IE04 173 kha, NL13 6.5 kha): grass could grow onto it at no
            # land cost, and the base had no land rent for grass (its row slack, the lower row binding)
            ba[i] = used + 1e-7 * max(1.0, abs(used)) + 1e-9 * scale
        if extra_r:
            Aa = np.vstack([Aa] + extra_r); ba = np.concatenate([ba, extra_b])
            labels.extend([labels[i] + "_lo" for i, _c, _k in rows])
        self._land_types_used = list(self.LAND_TYPES)
        start = np.concatenate([x0, L0] + ([np.array([getattr(self, "_alloc_m0", 0.0)])] if alloc_k else [])
                               + ([np.zeros(pool_k)] if pool_k else []))
        Qa, ca, Aa, ba, start = self._grass_intensity_column(Qa, ca, Aa, ba, start, labels, n, alloc_k)
        Qa, ca, Aa, ba, start = self._dairy_intensity_column(Qa, ca, Aa, ba, start, labels, n)
        Qa, ca, Aa, ba, start = self._histosol_columns(Qa, ca, Aa, ba, start, labels, n)
        self._aug_labels = labels              # one label per row of the augmented problem (the NLP form reads them)
        self._last_aug_A, self._last_aug_b = Aa, ba
        return Qa, ca, Aa, ba, start, rows

    # CAPRI's two grassland activities (extensive GRAE, intensive GRAI) represented by the area
    # moved from intensive to extensive grassland, z (docs/COUPLING_SPRINTS.md, Sprint 7a)

    #: activities without a level at the calibration point held at zero by a bound row, as CAPRI (no v_actLevl without
    #: p_technFact). OFF: tried 22 October 2026, it made the NLP form fail or relax mineral caps in Greek and Bulgarian
    #: regions under Farm-to-Fork (fixed columns at zero degenerate the fertiliser block); absent_output_cleared instead
    absent_activities_fixed = setting("supply.absent_activities_fixed")
    # K64: the solver's residue on activities without a base level (|level| <= 1e-4, 0.1 ha or head) is reported as
    # zero, so no output arises where CAPRI has no variable (Norway's 6e-6 kt of tobacco had kept the market from
    # converging); CAPRI's bounds on endogenous activity levels, 0.1 to 10 x the simulation's data level
    # (set_supply_bounds.gms), always apply

    def _grass_intensity_column(self, Qa, ca, Aa, ba, start, labels, n, alloc_k):
        """Append CAPRI's grassland-intensity choice as one column z (1000 ha moved from GRAI to
        GRAE; GRAE = s0 x GRAS + z, GRAI = (1 - s0) x GRAS - z, so z = 0 is the base split):
          - N balance row: the balance change of a hectare of GRAE over one of GRAI
            (EnvironmentalModule.grass_intensity_delta, the accounts' own function);
          - grass fodder rows: production changes by u x (yield_ext - yield_int) / mean yield;
          - crop-need limit (manure within need): the change in the unit balance's mineral N (K19) and in CAPRI's
            minimum mineral share x need (K9);
          - 0 <= GRAE, GRAI: -z - s0 GRAS <= 0, z - (1 - s0) GRAS <= 0;
          - PMP: (q_ext + q_int) z^2 / 2 (CAPRI's p_pmpQuadTechn of GRAE and GRAI), linear term
            from the base duals of the rows z enters, so z = 0 is optimal at base (as CAPRI's
            PMP calibration makes the base split optimal)."""
        self._grass_col = None
        if "GRAS" not in self.acts or alloc_k:
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
            # the change in the unit balance's mineral N, the quantity every crop carries on this row and the accounts
            # apply (K19: it was the plain fertiliser rate, -3.65 against -39.9 t per 1000 ha in AT32; the model then
            # saw mineral N at its floor while the accounts went to -461 t); and CAPRI's NUTMIN_ floor moves with the
            # need of a hectare of GRAE over one of GRAI (K9)
            col[nr] = -float(dl.get("n_mineral_input", dl.get("mineral_rate", 0.0)))
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
        labels.extend(["grass_z_lo", "grass_z_hi"])
        qz = float(gi["q_ext"]) + float(gi["q_int"])
        Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = qz
        ca = np.concatenate([ca, [cz + self._ghg_cost('grass')]])
        start = np.concatenate([start, [0.0]])
        self._grass_col = Aa.shape[1] - 1
        return Qa, ca, Aa, ba, start

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

    # CAPRI's low/high-intensity fattening bulls and heifers (Sprint 7c, tools/build/build_cattle_intensity.py)

    #: CAPRI's cattle activities inside the model's animals (tools/build/build_cattle_intensity.py SPLITS): key -> (the CAPRI
    #: activity that gains the stalls z, the one that gives them up); splits of one animal giving up the same activity
    #: share its curvature (cross term) and its bound
    CATTLE_SPLIT_MEMBERS = {"BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH"), "HFRS:rep": ("HEIR", "HEIH"),
                            "CALV:male": ("CAMF", "CAMR"), "CALV:female": ("CAFF", "CAFR"), "CALV:sex": ("CAMR", "CAFR")}
    #: the splits that give CAPRI's replacement heifers and calves their own levels, with the young-animal markets per
    #: sex (22 October 2026). OFF by default: with them the Farm-to-Fork 2030 run's young-animal markets did not converge
    #: (KNOWN_ISSUES K65; runs r89-r92). False keeps only the intensity pairs (Sprint 7c), the pooled young-animal
    #: markets and the animals' herd terms of that grouping - the validated state of runs r86 / r87
    use_cattle_member_splits = setting("supply.use_cattle_member_splits")

    def _cattle_columns(self, Qa, ca, Aa, ba, start, labels, n):
        """One column z per split of a cattle animal into CAPRI's activities (1000 stalls moved from one CAPRI
        activity to another, CATTLE_SPLIT_MEMBERS): the intensity pairs (BULL: BULL/BULH; HFRS: HEIL/HEIH, Sprint 7c),
        the replacement heifers (HFRS:rep, HEIR against HEIH) and the calves (CALV:male CAMF against CAMR, CALV:female
        CAFF against CAFR). As the dairy split: manure-driven rows x (MANN per stall, a - b) / average; the feed
        block's requirement rows (feeding inside); bounds a = s_a X + z >= 0 and b = s_b X - (sum of the z taking from
        b) >= 0; PMP from CAPRI's own terms (q_z; splits taking from the same activity share its term q_b as their
        cross term); linear term from the base duals, plus the CHANGES under the scenario: beef revenue (beef per
        stall, a - b), the young animals bought (calves, young cattle) and sold (young cattle from raising calves,
        replacement cows from HEIR) at the young-animal price changes."""
        self._cattle_cols = {}
        tab = getattr(self.data, "cattle_intensity", None)
        if not tab:
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
        members = type(self).CATTLE_SPLIT_MEMBERS
        member_splits = getattr(type(self), "use_cattle_member_splits", True)
        placed = {}                                               # animal -> [(key, column, row, animal column)]
        for key, di in tab.items():
            a = key.split(":")[0]
            if a not in self.acts or key not in members or (":" in key and not member_splits):
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
            if key not in cz_all:
                pending[key] = (col, req)
                continue
            Aa = np.hstack([Aa, col[:, None]])
            if not member_splits:
                # the intensity pair alone (Sprint 7c), rows in the order of the validated runs r86 / r87: bounds
                # low = s_low X + z >= 0, high = s_high X - z >= 0 right after the column, term q_z
                lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0; lo[j] = -float(di["share_low"])
                hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(di["share_high"])
                Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
                labels.extend([f"cattle_z_{a}_lo", f"cattle_z_{a}_hi"])
                Qa = np.pad(Qa, ((0, 1), (0, 1))); Qa[-1, -1] = float(di["q_z"])
            else:
                Qa = np.pad(Qa, ((0, 1), (0, 1)))                # the split block is set below, per animal
                placed.setdefault(a, []).append((key, Aa.shape[1] - 1, di, j))
            dv = 0.0
            if ps is not None and pv is not None and hasattr(pv, "get"):
                bv = pv.get(f"{a}.BEEF")
                if bv is not None and pd.notna(bv):
                    dv += float(di["dbeef_rel"]) * float(bv) * float(ps.get("BEEF", ps.get(a, 0.0)) or 0.0)
            for g, rec in ycoef.items():                          # young animals bought and sold per stall
                chg = float(rec.get("value_eur_head", 0.0) or 0.0) * (float(yr.get(g, 1.0)) - 1.0)
                if not chg:
                    continue
                u = float(rec.get("use", {}).get(a, 0.0) or 0.0)
                if u:
                    du = di.get(f"duse_{g}_rel")
                    du = float(di["dyoung_rel"]) if du is None or du != du else float(du)
                    # (the product in the order of the validated runs r86 / r87)
                    dv -= du * u * float(rec.get("value_eur_head", 0.0) or 0.0) * (float(yr.get(g, 1.0)) - 1.0)
                p_ = float(rec.get("produce", {}).get(a, 0.0) or 0.0) if member_splits else 0.0
                dp = di.get(f"dprod_{g}_rel")
                if p_ and dp is not None and dp == dp and float(dp):
                    dv += float(dp) * p_ * chg
            ca = np.concatenate([ca, [cz_all[key] - dv + self._ghg_cost('cattle', key)]])
            start = np.concatenate([start, [0.0]])
            self._cattle_cols[key] = Aa.shape[1] - 1
            rx = dict(getattr(self, "_dairy_req_extra", None) or {})
            rx[a] = list(rx.get(a, [])) + [(Aa.shape[1] - 1, req)]
            self._dairy_req_extra = rx
        # per animal: CAPRI's activities x_m = s_m X + sum_k E_mk z_k (E_mk = +1 if split k moves stalls into m,
        # -1 out of m); bounds x_m >= 0, one row per activity; PMP block in z: E' diag(q_m) E (q_m: the activity's term
        # per model stall, q_b for the activity giving up stalls, q_z - q_b for the one gaining them)
        for a, lst in placed.items():
            qm, sm = {}, {}
            for key, c_, di, j in lst:
                ma, mb = members[key]
                qb = float(di.get("q_b", 0.0) or 0.0)
                qm.setdefault(mb, qb); qm.setdefault(ma, max(float(di["q_z"]) - qb, 0.0))
                sm.setdefault(ma, float(di["share_low"])); sm.setdefault(mb, float(di["share_high"]))
            for m in sorted(sm):
                row = np.zeros(Aa.shape[1]); row[lst[0][3]] = -sm[m]
                for key, c_, di, j in lst:
                    ma, mb = members[key]
                    row[c_] -= 1.0 if m == ma else (-1.0 if m == mb else 0.0)
                Aa = np.vstack([Aa, row]); ba = np.concatenate([ba, [1e-9]])
                labels.append(f"cattle_{a}_{m}_lo")
            for key1, c1, d1, _ in lst:
                for key2, c2, d2, _ in lst:
                    v_ = 0.0
                    for m, q_ in qm.items():
                        e1 = 1.0 if m == members[key1][0] else (-1.0 if m == members[key1][1] else 0.0)
                        e2 = 1.0 if m == members[key2][0] else (-1.0 if m == members[key2][1] else 0.0)
                        v_ += e1 * e2 * q_
                    Qa[c1, c2] = v_
        self._cattle_pending = pending or None
        return Qa, ca, Aa, ba, start

    @classmethod
    def cattle_split_hessian(cls, tab, keys):
        """The PMP block of the cattle splits keys (the columns of _cattle_columns): E' diag(q_m) E per animal, zero
        between animals; for the young-animal markets' anticipation of the splits' response (CAPRIModel)."""
        members = cls.CATTLE_SPLIT_MEMBERS
        keys = [k for k in keys if k in members and k in (tab or {})]
        H = np.zeros((len(keys), len(keys)))
        qm = {}
        for k in keys:
            a, (ma, mb) = k.split(":")[0], members[k]
            qb = float(tab[k].get("q_b", 0.0) or 0.0)
            qm.setdefault((a, mb), qb); qm.setdefault((a, ma), max(float(tab[k]["q_z"]) - qb, 0.0))
        for i, k1 in enumerate(keys):
            for j, k2 in enumerate(keys):
                a1, a2 = k1.split(":")[0], k2.split(":")[0]
                if a1 != a2:
                    continue
                v = 0.0
                for (a, m), q in qm.items():
                    if a != a1:
                        continue
                    e1 = 1.0 if m == members[k1][0] else (-1.0 if m == members[k1][1] else 0.0)
                    e2 = 1.0 if m == members[k2][0] else (-1.0 if m == members[k2][1] else 0.0)
                    v += e1 * e2 * q
                H[i, j] = v
        return keys, H

    def _cattle_calibrate_from_duals(self, duals):
        pend = getattr(self, "_cattle_pending", None)
        if not pend:
            return
        rd = getattr(self, "_last_req_duals", None) or {}
        cz = dict(getattr(self, "_cattle_cz", None) or {})
        if duals is not None and rd:
            sgn = {"DMAX": -1.0}
            for key, (col, req) in pend.items():
                a = key.split(":")[0]
                if len(duals) >= len(col):
                    cz[key] = -(float(np.asarray(duals[:len(col)], float) @ col)
                                + sum(float(rd.get((a, lab), 0.0)) * sgn.get(lab, 1.0) * v for lab, v in req.items()))
        self._cattle_cz = cz
        self._cattle_pending = None

    # CAPRI's cattle genomics (envind/breeding.gms): higher milk yield (dairy cows) and lower energy need
    # (non-dairy ruminants), adopted inside the supply model (docs/MITIGATION_IN_SUPPLY.md)
    # the animal options' PMP slope net of CAPRI's cost-saving drop between its ini and max calibration runs
    # (breeding.gms l. 447-458; K67 F2)

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
            subsidy of relSubs0 x cost); quadratic gamma = max(floor c, c (relSubs1 - relSubs0) - (costsaving0 -
            costsaving1)) per unit of the share (floor 0.2 breeding, 0.05 low-N feed, 0.1 supplements), i.e.
            gamma / eligible heads at base per head adopting; the cost-saving drop is CAPRI's, from its ini and max
            calibration runs (column dsav);
          - milk revenue of the extra milk under the current milk price change (genet_yld)."""
        self._genet_cols = {}
        tab = getattr(self.data, "genetics_effects", None)
        if not tab:
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
            # pmpParsqr = max(floor x c, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) per unit of the share
            # of the eligible heads (breeding.gms l. 447-458, floor 0.2; low_n_feed.gms 0.05; line_nitr.gms 0.1);
            # per head adopting: / (eligible heads at base). costsaving0 - costsaving1: the drop of the option's
            # marginal value between CAPRI's ini and max calibration runs (dsav, EUR per model head;
            # tools/lib/_capri_costsavings.py), taken out of the planned slope as CAPRI does (K67 F2)
            gf = float(e["gamma_floor"]) if ("gamma_floor" in e and pd.notna(e["gamma_floor"])) else 0.2
            ds_ = float(e.get("dsav", 0.0) or 0.0)
            gamma = max(gf * c, c * (r1 - r0) - (ds_ if np.isfinite(ds_) else 0.0))
            el_ = max(float(e["elig_share"]), 1e-6)
            Aa = np.hstack([Aa, col[:, None]])
            lo = np.zeros(Aa.shape[1]); lo[-1] = -1.0
            hi = np.zeros(Aa.shape[1]); hi[-1] = 1.0; hi[j] = -float(e["elig_share"])
            Aa = np.vstack([Aa, lo, hi]); ba = np.concatenate([ba, [1e-9, 1e-9]])
            labels.extend([f"genet_z_{a}_{opt}_lo", f"genet_z_{a}_{opt}_hi"])
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
          - the cows' requirement rows in the feed block (energy, protein, dry-matter
            limits): DCOW's requirement x the relative change (req_extra; feeding inside only);
          - 0 <= DCOL, DCOH; PMP (q_DCOL + q_DCOH) z^2 / 2 (CAPRI's p_pmpQuadTechn);
          - linear term from the base duals (z = 0 optimal at base), plus the milk revenue change
            under the current milk price (milk per head (COMI_DCOL - COMI_DCOH) / COMI_DCOW).
        Calves, cull-cow beef and replacements are the same for both activities (CAPRI res_17)."""
        self._dairy_col = None
        self._dairy_req_extra = None
        if "DCOW" not in self.acts:
            return Qa, ca, Aa, ba, start
        di = getattr(self.data, "dairy_intensity", None)
        r = (getattr(self, "feed_rations", None) or {}).get("DCOW")
        if di is None or r is None or not hasattr(di, "get") or not (float(di.get("q_low", 0) or 0) > 0):
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
        labels.extend(["dairy_z_lo", "dairy_z_hi"])
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
        """Flexible feeds: tax x emission per t fed, in the regional objective's EUR/kg units ({(animal, feed)})."""
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
        if h is None or not hasattr(h, "get"):
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
            if row_lab + "_lo" in labels:
                # the land row is an equality (CAPRI LandBalNoSlak_: the crops and the idled histosol area together
                # equal the land type): with F on the upper row alone, crops + F <= land <= crops held F at zero
                # wherever the pair is tight (arable and permanent land always) - no histosol was ever fallowed
                col[labels.index(row_lab + "_lo")] = -1.0
            if "landscape_floor" in labels:
                # idled histosols count towards the Biodiversity Strategy's set-aside and landscape target
                # (supply_model.gms e_setaLandscape_: setaFallow includes iHisCr and iHisGr)
                col[labels.index("landscape_floor")] = -1.0
            if cal is None or cls not in cal:
                pend[cls] = col
                continue
            Aa = np.hstack([Aa, col[:, None]])
            up = np.zeros(Aa.shape[1]); up[-1] = 1.0
            Aa = np.vstack([Aa, up]); ba = np.concatenate([ba, [float(mx) * H]])
            labels.append(f"hist_{cls}_up")
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
            row_b = np.zeros(len(self.acts))
            _rs = getattr(self, "ration_state", None) or {}
            _fr = getattr(self, "feed_rations", None) or {}
            for a, t in rec.get("use_t_head", {}).items():
                if a in acts_idx:
                    xr = (_rs.get(a) or {}).get("x", {})
                    row[acts_idx[a]] = float(xr[feed]) / 1000.0 if feed in xr else float(t)
                    # the BASE ration's use per head, for the base gap below (CAPRI's baseline fodder balance)
                    r_ = _fr.get(a)
                    if r_ is not None and feed in list(r_.feeds):
                        row_b[acts_idx[a]] = float(r_.x0[list(r_.feeds).index(feed)]) / 1000.0
                    else:
                        row_b[acts_idx[a]] = row[acts_idx[a]]
            if not row.any():
                continue
            row[acts_idx[crop]] = -float(rec["u_t_per_ha"])
            row_b[acts_idx[crop]] = row[acts_idx[crop]]
            scale = float(np.abs(row) @ np.abs(x0)) or 1.0
            # exact at base in both directions (K36): where the projected herds' fodder use and the projected fodder
            # output differ (use below output in FI1D, ITF5, ITG1...), the gap at base is carried as a constant, as
            # CAPRI's baseline holds its fodder balances. Before, rhs = max(0, gap): with use below output the band row
            # forced the fodder area down to the use, and the no-idle-land rule put the freed land on cereals
            # The gap is the BASE's: base rations x base herds (K46). It was taken with the current ration state, so
            # the balance's right-hand side moved with the rations every iteration - with feeding inside the regional
            # models (animal cells of this row replaced by the feed columns) a fodder balance that loosened or tightened
            # with the last solution's feeding; before, with the ration chosen outside the models at current prices.
            rhs = float(row_b @ x0) + 1e-9 * scale
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
        # with (tools/build/build_capri_base.py PERMANENT_CROPS): tobacco, cotton and
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
        _land_arable = (float(self._land_of("ARABLE"))
                        + self._land_of("FALLOW"))
        arable_avail = max(_land_arable, arable_base)
        b_rows.append(arable_avail)

        # 1b. Landscape-elements floor: at least `set_aside_requirement` of UAA
        # held as the non-productive activity. Expressed as -x_SETA <= -target
        # so it fits the upper-bound form. A negative requirement (a scenario
        # REMOVING an existing obligation) is skipped rather than inverted into
        # a nonsensical ceiling.
        if set_aside_requirement and set_aside_requirement > 0 and "SETA" in acts_idx:
            uaa_total = (self._land_of("ARABLE")
                         + self._land_of("PERMANENT")
                         + self._land_of("GRASSLAND")
                         + self._land_of("FALLOW"))
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
        b_rows.append(max(self._land_of("PERMANENT"), perm_base))

        # 3. Grassland constraint
        row_grass = np.zeros(n)
        # CAPRI's land rules (LandBalNoSlak_): the row is CAPRI's grassland balance, the grassland activity (CAPRI's
        # GRAE + GRAI) equals the grassland area. Maize and other fodder are ARABLE crops (CAPRI MAIF, OFAR, ROOF) and
        # are already in the arable row. (The model's earlier row - fodder on grassland plus a fifth of arable land -
        # fixed arable fodder at its base area plus a fifth of any arable change: regions under the N target could not
        # replace fertilised fodder leys.)
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
        # (23 October 2026, no proxies: the former limit took a fifth of arable land on top with the land rules off and
        # 15% headroom above the base fodder area, neither CAPRI's; CAPRI's grassland balance is the grassland area,
        # LandBalNoSlak_. The larger of the land figure and the base area stays, as for the other land rows)
        grass_land_limit = self._land_of("GRASSLAND")
        base_fodder = sum(self._base_levels().get(a, 0.0) for a in grass_acts)
        b_rows.append(max(grass_land_limit, base_fodder))

        # 4. Nitrogen constraint (Nitrates Directive: 170 kg N/ha limit on organic N)
        n_limit = nitrate_limit if nitrate_limit is not None else 999999.0
        row_N = np.zeros(n)
        n_coefs = self.data.nutrient_coefs.reindex(self.acts)["N"].fillna(0.0)
        row_N = n_coefs.values
        total_uaa = (self._land_of("ARABLE") +
                     self._land_of("PERMANENT") +
                     self._land_of("GRASSLAND"))
        # only with a nitrate limit: without one the row was a placeholder (999999 kg N/ha x UAA, ~2e9) that never binds
        # and spoiled the conditioning of the regional problem (K15: Clarabel left IE05 AlmostSolved / stalled)
        if nitrate_limit is not None:
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
        # (The roughage "buy-in" rows that stood in where the fodder balance had no data - headroom 1.5 x the base
        # shortfall plus 0.1 x on-farm supply - were removed 23 October 2026: every region with herds has CAPRI's fodder
        # balance; one without it stops the run.)
        if not fodder_rows and any(float(self._base_levels().get(a_, 0.0)) > 1e-8 for a_ in ANIMALS
                                   if a_ in acts_idx and a_ not in FIXED_ACTIVITIES):
            raise ValueError(f"{self.data.region_id}: herds without CAPRI's fodder balance (fodder_balance_2017.json)")

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
                            a, ycur, self.data.region_id, _mi, yields_scen=self._yields_scen_now())["n_surplus"])
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
                        _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
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
                        # crop NEED follows yield (CAPRI fertned.gms, _need_yf),
                        # and so does the mineral N it calls for - exactly as the
                        # environmental accounts compute it. Without this term the
                        # constraint saw more fertiliser than the accounts after
                        # yield losses, demanded extra cuts, and the surplus fell
                        # past its target (Farm-to-Fork -45% vs CAPRI's -34%).
                        if yc > 0:
                            sa += (float(nmin.get(a, 0.0)) * float(mint.get(a, 1.0))
                                   * (self._need_yf(a, y0, yc) - 1.0))
                if a in CROPS and float(nmin.get(a, 0.0)) > 0:
                    # mineral part of the coefficient (for CAPRI's fertiliser technologies
                    # inside the regional model): nmin x intensity x need factor of the yield (_need_yf)
                    _y0 = float(ybase.get(a, 0.0)) if (ybase is not None and hasattr(ybase, "get")) else 0.0
                    _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                    _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
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
                    m_a = float(_env_m.unit_nitrogen_balance(a, ycur, self.data.region_id, _mi,
                                                             yields_scen=self._yields_scen_now())["n_mineral_input"])
                except Exception:
                    m_a = 0.0
                if a in CROPS:
                    row_m[i] = float(mcap["capped_share"].get(a, 0.0)) * m_a - float(mcap["kappa"].get(a, 0.0))
                    if float(nmin_m.get(a, 0.0)) > 0:
                        _y0 = float(ybase_m.get(a, 0.0)) if (ybase_m is not None and hasattr(ybase_m, "get")) else 0.0
                        _yc = float(ycur.get(a, _y0)) if hasattr(ycur, "get") else _y0
                        _r = self._need_yf(a, _y0, _yc) if (_y0 > 0 and _yc > 0) else 1.0
                        mrow_parts[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r \
                            * float(mcap["capped_share"].get(a, 0.0))
                else:
                    row_m[i] = m_a
            A_rows.append(row_m)
            b_rows.append(float(self._cover_n_increment()))
            self._row_labels.append("mineral_N")
            # crops' mineral part, for CAPRI's fertiliser technologies inside the regional model
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
        _unc = getattr(self.data, "uncalibrated", None) or frozenset()
        for i, a in enumerate(self.acts):
            if a in FIXED_ACTIVITIES or (a in _unc and float(_x0f.get(a, 0.0)) > 1e-8):
                v = max(float(_x0f.get(a, 0.0)), 0.0)
                tol = 1e-7 * max(v, 1e-3)
                for sg in (1.0, -1.0):
                    row_f = np.zeros(n)
                    row_f[i] = sg
                    A_rows.append(row_f)
                    b_rows.append(sg * v + tol)
                    self._row_labels.append(f"fixed_{a}_{'up' if sg > 0 else 'lo'}")

        # CAPRI's bounds on the endogenous activities (supply/set_supply_bounds.gms, applied in every simulation by
        # prep_sim.gms): LO = max(0.1 x level, 1e-8), UP = max(10 x level, level + 100), level = the data level of the
        # simulation (here the region's base). Without them an activity could leave its calibration range entirely
        # (K27: Dutch fattening sheep 10 -> 2,923 thousand head, dairy cows to 0 under Farm-to-Fork). CAPRI's own
        # exemption: set-aside (VSET 1e-6 .. 1e5; the model's SETA). The additive 100 is in CAPRI's units: 1000 ha
        # (crops, as the model) or 1000 head of CAPRI's activity (LEVL), converted to the model's herd units by
        # CAPRI's LEVL per model head in 2017 (capri_level_ratio.csv: poultry in thousand head against CAPRI's million,
        # fattening sheep, bulls and heifers counted as census stock against CAPRI's activity level).
        _lr = getattr(self.data, "capri_level_ratio", None)
        for i, a in enumerate(self.acts):
            if (a in FIXED_ACTIVITIES or (a in _unc and float(_x0f.get(a, 0.0)) > 1e-8) or a == "SETA"
                    or (a not in CROPS and a not in ANIMALS)):
                continue
            v = float(_x0f.get(a, 0.0))
            if not v > ABSENT_LEVEL:
                # CAPRI has no variable for an activity without a level at the calibration point (v_actLevl exists
                # only where p_technFact(..,"LEVL",..) is set, i.e. where the data have a level): held at zero
                # (K64: Norway's regions produced 6e-6 kt of tobacco from the solver's interior, which no trade
                # flow could take, and the market's residual stalled at 3e-6)
                if getattr(type(self), "absent_activities_fixed", False):
                    row_u = np.zeros(n); row_u[i] = 1.0
                    A_rows.append(row_u); b_rows.append(0.0); self._row_labels.append(f"bound_{a}_absent")
                continue
            k_ = (float(_lr[a]) if a in ANIMALS and _lr is not None and a in _lr.index and pd.notna(_lr[a])
                  and float(_lr[a]) > 0 else 1.0)
            add = 100.0 * k_
            hi, lo = max(10.0 * v, v + add), max(0.1 * v, 1e-8)
            row_u = np.zeros(n); row_u[i] = 1.0
            A_rows.append(row_u); b_rows.append(hi); self._row_labels.append(f"bound_{a}_up")
            row_l = np.zeros(n); row_l[i] = -1.0
            A_rows.append(row_l); b_rows.append(-lo); self._row_labels.append(f"bound_{a}_lo")

        A_ub = np.array(A_rows)
        b_ub = np.array(b_rows)

        return A_ub, b_ub, np.zeros((0, n)), np.zeros(0)

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------


    def solve(self, *args, surplus_row=None, n_balance_price: float = 0.0, mineral_cap=None, **kwargs):
        """Solve the regional model once at the given prices.

        Agricultural land responds to its value only through CAPRI's land market (_land_augment: land types
        as variables with CAPRI's p_pmpQuadLandTypes and calibration rents). Where the region has no land-market
        data or the land market fails, its land is fixed, as in CAPRI without the land market. Until 23 October 2026
        a rent-elasticity expansion (elasticity 0.15, cap 15%, both approximations) stood in there; it was a proxy
        and was removed (docs/design/PROXY_AUDIT.md S149, S410, S411).

        STATELESS: everything set for this solve is reset before returning (test_solve_leaves_no_state_behind).
        """
        self.landscape_shortfall = 0.0          # reset on every solve
        self.balance_shortfall = 0.0
        self._surplus_row = surplus_row         # held for THIS solve only
        self._mineral_cap = mineral_cap         # CAPRI's mineral fertiliser reduction, THIS solve only
        self._mineral_row_m = {}
        self._last_manure_trade = (0.0, 0.0)
        self._last_mineral_n = None
        self._nbal_price = float(n_balance_price or 0.0)
        self._n_intensity = {}
        self._organic_conv = {}
        self._land_solution = None              # set by this solve when the land market is used
        self._n_target_relaxed = False
        self._last_cattle_z = {}
        self._nlp_failed = None
        self._nlp_status = None
        self._nlp_nonoptimal = None             # IPOPT's last point kept on the last attempt (as CAPRI), THIS solve only
        # the price shock the split and genetics columns value their products at: set by THIS solve's net revenues
        # (_compute_net_revenues, called only with a shock); a plain solve after a shocked one kept the old shock there
        self._price_shock_now = None
        self._yield_price_factor = {}           # the price response's yield factor per crop, THIS solve only
        try:
            res = self._solve_once(*args, **kwargs)
        finally:
            self._surplus_row = None
            self._mineral_cap = None
            self._nbal_price = 0.0
        res.n_intensity = dict(getattr(self, "_n_intensity", {}) or {})
        res.yield_price_factor = dict(getattr(self, "_yield_price_factor", {}) or {})
        self._yield_price_factor = {}
        res.organic_conv = dict(getattr(self, "_organic_conv", {}) or {})   # conventional share per crop (accounts: organic area)
        res.fert_tech_shares = dict(getattr(self, "_fert_tech_shares", {}) or {})   # before the reset below
        # IPOPT's last point kept on the last attempt (non-optimal, as CAPRI; _nlp_last_point): IPOPT's status, else None
        res.nlp_nonoptimal = getattr(self, "_nlp_nonoptimal", None)
        # CAPRI's crop-group allocation as the regional model solved it (inner model at its totals, or the coupled NLP)
        res.fert_dist_model = getattr(self, "_fd_model", None)
        try:
            _bl = self._base_levels()
            res.fert_dist_mode_crops = {a: float(_bl.get(a, 0.0)) for a in CROPS if float(_bl.get(a, 0.0)) > 0}
        except Exception:
            res.fert_dist_mode_crops = None
        self._n_intensity = {}
        self._fert_tech_shares = {}
        res.landscape_shortfall = float(getattr(self, "landscape_shortfall", 0.0))
        res.balance_shortfall = float(getattr(self, "balance_shortfall", 0.0))
        self.landscape_shortfall = 0.0
        self.balance_shortfall = 0.0
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

        self._yields_solve0 = _backup.get("yields")    # the calibrated yields (the 2030 reference), THIS solve only
        self._greendeal_inputs = {}                     # set by _apply_greendeal_input_changes for THIS solve
        try:
            return self._solve_inner(price_shock, policy_shock, nitrate_limit,
                                     set_aside_requirement)
        finally:
            self._yields_solve0 = None
            self.net_revenues = _net_rev_backup
            for _f, _v in _backup.items():
                setattr(self.data, _f, _v)

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
        self._last_duals = None
        y = self._nlp_solve(Qa, ca, A2, b2, ya0)
        if y is None:
            return None, False, Aa, ba
        self.balance_shortfall = T2 - T
        self._n_target_relaxed = True
        self._n_relax_sticky = self._n_relax_key()
        return y, True, A2, b2

    def _n_relax_key(self):
        """The scenario's N target for this region (tiered target, base surplus): identifies the setting the
        JRC121368 relaxation belongs to; None without an N target."""
        srow = getattr(self, "_surplus_row", None)
        if srow is None or len(srow) < 8 or srow[7] is None:
            return None
        return (round(float(srow[1]), 9), round(float(srow[7]), 9))

    def _fit_aug_row(self, Qa, ca, Aa, ba, ya0, label):
        """Relax one row of the regional problem (with the land market or without it) to the closest value the region
        can reach.

        (Until 26 October 2026 the plain problem had its own fits on the QP without feeding.) When the
        land-market problem had no solution, the solve used to drop to the plain problem, where
        land may idle and the land types are fixed - silently leaving CAPRI's land rules (no idle
        land, land supply through the land market) in exactly the regions where they bind: North
        Brabant's neighbour Zeeland halved its herds and grassland under the N target alone. Here
        the row (landscape floor: -SETA <= -floor; N balance: surplus <= target) is set to the
        lowest value a linear program over the problem's rows can reach, plus a small margin,
        and the regional model is solved again. JRC121368: 'the reduction is relaxed in a limited number of
        regions where the model is infeasible'. Records landscape_shortfall (1000 ha of set-aside)
        or balance_shortfall (kg N per ha of farmland)."""
        labels = list(getattr(self, "_row_labels", []))
        if label not in labels:
            return None, False, ba
        k = labels.index(label)
        from scipy.optimize import linprog
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
        # the linear program sees the problem's linear rows only; CAPRI's form has more (feeding, fertilisation), so the
        # floor is relaxed further in steps until the regional model solves (as CAPRI's widen_bounds.gms widens its
        # bounds step by step), from the region's own start and from the linear program's point
        for slack in (1e-3, 1e-2, 5e-2, 0.1, 0.25, 0.5):
            b_fit = ba.copy()
            b_fit[k] = least + slack * max(abs(least), 1.0)
            y = None
            for start in (ya0, y_start):
                self._last_duals = None
                y = self._nlp_solve(Qa, ca, Aa, b_fit, start)
                if y is not None:
                    break
            if y is not None:
                if label == "landscape_floor":
                    self.landscape_shortfall = float(b_fit[k]) - float(ba[k])
                else:
                    self.balance_shortfall = (float(b_fit[k]) - float(ba[k])) / area
                return y, True, b_fit
        return None, False, ba

    def _nlp_last_point(self, Q, c, A, b, x_start):
        """The caller's last attempt: CAPRI's form solved again with IPOPT's last point kept where it fails, as CAPRI
        carries on with a non-optimal solve (supply/simu_supply.gms, widen_bounds.gms; p_INFES), recorded in the run's
        metadata (nlp_fallback). Only where the NLP cannot be built at all is there nothing to keep: the run stops, as
        CAPRI aborts on an execution error."""
        self._nlp_accept_last = True
        try:
            y = self._nlp_solve(Q, c, A, b, x_start)
        finally:
            self._nlp_accept_last = False
        if y is None:
            raise RuntimeError(f"{self.data.region_id}: the regional model in CAPRI's form could not be built or solved "
                               f"({getattr(self, '_nlp_failed', None) or 'NLP build failed'})")
        return y

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
                    # removed, tools/run/run_vcs_2030.py); crops via cap_premium, animals via
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
                # the organic yield gap applies in full (no 0.45 factor: CAPRI uses it only with
                # pest_disagg on, an endogenous pesticide yield response; see apply_organic_area_target)
                self.apply_organic_area_target(_org)
            if _pest:
                _prule = str(policy_shock.get("pesticide_rule", "jrc121368") or "jrc121368")
                self.apply_pesticide_reduction(_pest, organic_share=_org or None, yield_loss=(_prule == "jrc121368"))
            if _org or _pest:
                # CAPRI's regional plant-protection and other-input changes of both targets (define_inputs.gms)
                self._apply_greendeal_input_changes(_org, _pest)
        # CAPRI's yield-dependent inputs (define_inputs.gms, re-run after the scenario's yield shifts and after each
        # price-driven yield update): the crops' input costs follow their yields
        self._apply_yield_input_costs()

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

        # The regional model in CAPRI's form, solved by IPOPT (_nlp_solve). Where a solve fails, CAPRI re-solves with
        # widened bounds and then carries on with the non-optimal solution, recorded (supply/simu_supply.gms,
        # widen_bounds.gms: p_INFES): here JRC121368's relaxed N target and the landscape floor fitted to the reachable
        # set-aside are tried, then IPOPT's last point at the region's own problem is kept and recorded (_nlp_last_point)
        c_lin = self.f - self.net_revenues.values
        aug = self._land_augment(A_ub, b_ub, c_lin, x0) if getattr(self, "use_land_market", False) else None
        if aug is not None:
            # CAPRI LAND MARKET: land-type areas as variables (see _land_augment)
            Qa, ca, Aa, ba, ya0, rows = aug
            self._last_duals = None
            # JRC121368 sect. 4.3.4: where the tiered N target is infeasible the region's cut is the EU average
            # (36%) - a setting of the scenario for that region, so once found in this scenario (same target)
            # the region starts from it instead of failing the tiered target again at every iteration
            _yc = None
            _rk = self._n_relax_key()
            if _rk is not None and getattr(self, "_n_relax_sticky", None) == _rk:
                y_f, ok_f, Aa_r, ba_r = self._relax_n_target(Qa, ca, Aa, ba, ya0)
                if ok_f and getattr(self, "_nlp_failed", None) is None:
                    _yc, Aa, ba = y_f, Aa_r, ba_r
            if _yc is None:
                # where CAPRI's form fails at the tiered N target, JRC121368's rule for regions whose target
                # "generated infeasibilities in the model" (the EU-average cut, 36%) is tried
                self._nlp_try_n_relax = _rk is not None
                try:
                    _yc = self._nlp_solve(Qa, ca, Aa, ba, ya0)
                finally:
                    self._nlp_try_n_relax = False
                if _yc is None and getattr(self, "_nlp_fb_last", False) == "n_target":
                    _st0 = getattr(self, "_nlp_failed", None) or "NLP build failed"
                    y_f, ok_f, Aa_r, ba_r = self._relax_n_target(Qa, ca, Aa, ba, ya0)
                    if getattr(self, "_nlp_fallback_log", None) is None:
                        self._nlp_fallback_log = []
                    if ok_f:
                        _yc, Aa, ba = y_f, Aa_r, ba_r
                        self._nlp_fallback_log.append(f"{_st0} at the tiered N target -> CAPRI's form at "
                                                      f"JRC121368's relaxed target (36%)")
                    else:
                        self._n_target_relaxed = False
                        self._n_relax_sticky = None
                        self.balance_shortfall = 0.0
            if _yc is None:
                # an unreachable landscape floor, relaxed INSIDE the land-market problem (CAPRI's land rules stay in
                # force); see _fit_aug_row
                y_f, ok_f, b_fit = self._fit_aug_row(Qa, ca, Aa, ba, ya0, "landscape_floor")
                if ok_f:
                    _yc, ba = y_f, b_fit
            if _yc is None:
                _yc = self._nlp_last_point(Qa, ca, Aa, ba, ya0)
            y = _yc
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
                self._grass_calibrate_from_duals(getattr(self, "_last_duals", None))
            if self._split_pending():
                self._dairy_calibrate_from_duals(getattr(self, "_last_duals", None))
            self._last_hist_fallow = {c_: float(y[j_]) for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items() if j_ < len(y)}
            if getattr(self, "_hist_pending", None):
                self._histosol_calibrate_from_duals(getattr(self, "_last_duals", None))
            # land rows' limits at the solved land areas, so the shadow
            # prices computed below see the right slack
            b_ub = b_ub.copy()
            for i, coeffs, const in rows:
                b_ub[i] = const + sum(cf * float(y[n_ + k]) for k, cf in coeffs)
            self._land_solution = dict(zip(self._land_types_used, y[n_:].tolist()))
        else:
            self._last_duals = None
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
            self._aug_labels = _lab
            self._last_hist_fallow = {}
            _yc = None
            _cols = (getattr(self, "_grass_col", None) is not None or getattr(self, "_dairy_col", None) is not None
                     or getattr(self, "_cattle_cols", None) or getattr(self, "_hist_cols", None))
            if _cols:
                _yg = self._nlp_solve(Qg, cg, Ag, bg, sg)
                if _yg is None:
                    # an unreachable landscape floor (Corsica, Alpine regions without the land market: the floor is
                    # sized on total farmland, set-aside sits on arable land), fitted as on the land-market path
                    _yg, _okf, _bf = self._fit_aug_row(Qg, cg, Ag, bg, sg, "landscape_floor")
                    if not _okf:
                        _yg = self._nlp_last_point(Qg, cg, Ag, bg, sg)
                    else:
                        b_ub = b_ub.copy(); b_ub[:len(b_ub)] = _bf[:len(b_ub)]
                if getattr(self, "_grass_col", None) is not None:
                    self._last_grass_z = float(_yg[self._grass_col])
                self._split_record(_yg)
                _yc = _yg[:_n0]
                if getattr(self, "_grass_pending_col", None) is not None:
                    self._grass_calibrate_from_duals(getattr(self, "_last_duals", None))
                if self._split_pending():
                    self._dairy_calibrate_from_duals(getattr(self, "_last_duals", None))
                self._last_hist_fallow = {c_: float(_yg[j_]) for c_, j_ in (getattr(self, "_hist_cols", None) or {}).items()}
                if getattr(self, "_hist_pending", None):
                    self._histosol_calibrate_from_duals(getattr(self, "_last_duals", None))
            else:
                self._dairy_req_extra = None
                _yc = self._nlp_solve(self.Q, c_lin, A_ub, b_ub, x0)
                if _yc is None:
                    _yc, _okf, _bf = self._fit_aug_row(self.Q, c_lin, A_ub, b_ub, x0, "landscape_floor")
                    if not _okf:
                        _yc = self._nlp_last_point(self.Q, c_lin, A_ub, b_ub, x0)
                    else:
                        b_ub = _bf
                if getattr(self, "_grass_pending_col", None) is not None:
                    self._grass_calibrate_from_duals(getattr(self, "_last_duals", None))
                if self._split_pending():
                    self._dairy_calibrate_from_duals(getattr(self, "_last_duals", None))
                if getattr(self, "_hist_pending", None):
                    self._histosol_calibrate_from_duals(getattr(self, "_last_duals", None))
            x_qp = _yc
            # record the plain problem as the land-market path records its own (_last_aug)
            self._last_plain = (self.Q, c_lin.copy(), A_ub.copy(), b_ub.copy(), x_qp.copy())

        x_opt = np.maximum(x_qp, 0.0)
        solver_converged = getattr(self, "_nlp_nonoptimal", None) is None
        solver_message = f"NLP (CAPRI's form, IPOPT): {getattr(self, '_nlp_status', None)}"

        # (The post-solve "safety rail" that clamped each activity's move to max(0.5, min(6, 4 x max(eps, 0.3) x
        # shock)) of its base was removed 23 October 2026: CAPRI has no such clamp, and its numbers had no source.)

        _b0 = self._base_levels().reindex(list(self.acts)).fillna(0.0).values
        x_opt = np.where((np.abs(_b0) <= 1e-8) & (np.abs(x_opt) <= 1e-4), 0.0, x_opt)
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
        # coefficients (tools/build/build_livestock_output_coef.py) sum CAPRI's
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
            # the cattle splits (bulls and heifers, Sprint 7c; replacement heifers and calves): beef per stall,
            # a - b, over the animal's average, for every split of the animal
            for _k, _cz_ in (getattr(self, "_last_cattle_z", None) or {}).items():
                if _k.split(":")[0] != _a:
                    continue
                _ct_ = (getattr(self.data, "cattle_intensity", None) or {}).get(_k)
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
        # the NLP's own multipliers ARE the shadow prices - re-detecting binding rows from an interior-point solution
        # is unreliable (inner N-price loops then ran long)
        _zc = getattr(self, "_last_duals", None)
        if _zc is not None:
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

    #: "recipe": capri-mod's own terms computed with CAPRI's recipe (tools/build/build_pmp_recipe.py) for the market year (2017
    #: or 2030); at 2030 with CAPRI's 2030 feed slopes and land-type terms (their own calibrations are not ported).
    #: the PMP terms at the 2030 market year: "capri2030" (CAPRI's own terms of its 2030 baseline calibration, K61:
    #: crops' p_pmpQuadTechn and p_pmpQuadPact, animals' herd terms, feed-PMP slopes, land-type terms; the default since
    #: 22 October 2026, the project lead's decision) or "elasticity" (calibrated per activity from CAPRI's supply
    #: elasticities, with CAPRI's crop-group structure for small cross terms). Other years always "elasticity".
    pmp_source = setting("supply.pmp_source")
    #: which of CAPRI's 2030 terms "capri2030" uses: the crops' matrix, the animals' herd terms, the feed-PMP slopes,
    #: the land market's land-type terms (all by default; subsets for diagnosis, run script --pmp-parts)
    pmp_capri_parts = setting("supply.pmp_capri_parts", tuple)
    #: CAPRI's land market, the grassland allowance, the JRC121368 capped regions override (settings supply.*)
    use_land_market = setting("supply.use_land_market")
    grassland_allowance = setting("supply.grassland_allowance")
    jrc_capped_override = setting("supply.jrc_capped_override")

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
            # sensitivity only (tools/run/run_f2f_2030.py --capped-regions): the report does not
            # name the nine regions; '+A,B' adds to them, 'A,B' replaces them
            ov = str(getattr(self, "jrc_capped_override", "") or "")
            if ov:
                extra = {x.strip() for x in ov.lstrip("+").split(",") if x.strip()}
                got = (got | extra) if ov.startswith("+") else extra
            self._jrc_capped_cache = got
        return got
    def __init__(self, data: dict, supply_elasticities: Optional[pd.Series] = None):
        """CAPRI's regional elasticity estimates, with provenance tracking."""
        self.data = data
        self.regions = list(data["areas"].index)

        if supply_elasticities is None:
            # no literature defaults (23 October 2026): CAPRI's own values come from build_elasticity_table below
            supply_elasticities = pd.Series(float("nan"), index=list(ALL_ACTIVITIES))
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
                pv = read_csv(pact_path)
                for r, g in pv.groupby("model_region"):
                    self.cross_group[r] = {
                        (a, b): v for a, b, v in
                        zip(g.group1, g.group2, g.value)}
        except Exception as exc:                          # pragma: no cover
            warnings.warn(f"CAPRI cross-group terms unavailable ({exc})")

        from capri_mod.supply.capri_pmp import build_elasticity_table
        self.elasticity_provenance = pd.DataFrame()
        self.elasticity_summary: dict = {}
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
                # the NLP form's calibration (CAPRI's: the base a first-order point of the model it is simulated with)
                # belongs to the settings too: the genomics columns differ with them. Kept per settings and restored,
                # so a baseline after a run at other settings uses its own calibration, not the other one (found
                # 20 October 2026: after an ghgTechMYld 0.2 run, IE04's default baseline adopted genet_eff for the
                # whole herd)
                cal_store = m.__dict__.setdefault("_nlp_cal_store", {})
                cal_store[old] = (m.__dict__.get("_nlp_cal"), m.__dict__.get("_nlp_base_alloc"))
                m._nlp_cal, m._nlp_base_alloc = cal_store.get(settings_key, (None, None))
            m.data.genetics_effects = (table or {}).get(region)
            m._genet_cz = store.get(settings_key)
            m._genet_pending = None
            m._last_genet_z = {}
            m._genet_key = settings_key

    def _pmp_terms_for(self, d, region):
        """The region's PMP terms in the model's form for pmp_source and the market year: "capri2030" CAPRI's exported
        2030 terms (2030 only), "recipe" capri-mod's own with CAPRI's recipe (2017 or 2030), else None (elasticity
        calibration)."""
        src = str(getattr(self, "pmp_source", "elasticity"))
        yr = int(d.get("market_year", 2017) or 2017)
        if src == "capri2030" and yr == 2030:
            return self._pmp_capri_parts_of((d.get("pmp_capri_2030") or {}).get(region))
        # CAPRI's own terms exist only for its 2030 calibration (pmppar_21730); at 2017 "capri2030" takes CAPRI's
        # recipe at CAPRI's 2017 point, as "recipe" does (23 October 2026: before, the elasticity calibration, which
        # needed literature elasticities where CAPRI has none - no proxies)
        if src == "recipe" or (src == "capri2030" and yr == 2017):
            return self._pmp_capri_parts_of(((d.get("pmp_recipe") or {}).get(yr) or {}).get(region))
        return None

    def _intensity_q_at(self, d, row, cols, part):
        """An intensity split's row with its curvature at the PMP terms' calibration point: at the 2030 market year
        with pmp_source "capri2030" or "recipe" (and `part` among pmp_capri_parts), q_<x> := q_<x>_capri2030 /
        q_<x>_recipe2030 (CAPRI's / the recipe's 2030 p_pmpQuadTechn of the two variants, tools/build/build_intensity_q_2030.py);
        else the base year's terms. The _capri2030 / _recipe2030 entries are removed either way."""
        if row is None:
            return row
        src = str(getattr(self, "pmp_source", "elasticity"))
        yr = int(d.get("market_year", 2017) or 2017)
        sfx = {"capri2030": "_capri2030", "recipe": "_recipe2030"}.get(src) if yr == 2030 else None
        if sfx and part not in tuple(getattr(self, "pmp_capri_parts", ())):
            sfx = None
        out = row.copy()
        if sfx:
            for c in cols:
                v = out.get(c + sfx)
                if v is not None and v == v and float(v) > 0:
                    out[c] = float(v)
        return out.drop([k for k in out.index if str(k).endswith(("_capri2030", "_recipe2030"))])

    def _uncalibrated(self, d, region) -> frozenset:
        """Activities of the region without any CAPRI calibration: the elasticity table has no CAPRI value for them
        (provenance NO_CAPRI_VALUE) and, with CAPRI's or the recipe's PMP terms, no own term either. CAPRI has no
        own-price elasticity for them (e.g. OOIL, OIND in every member state) and no PMP term at the calibration
        point; they are held at their level (no proxies, 23 October 2026: the former literature elasticities)."""
        prov = getattr(self, "elasticity_provenance", None)
        if prov is None or prov.empty or region not in prov.index:
            return frozenset()
        pmp = self._pmp_terms_for(d, region) or {}
        return frozenset(a for a in prov.columns
                         if prov.at[region, a] == "NO_CAPRI_VALUE" and (a, a) not in pmp)

    def _pmp_capri_parts_of(self, g):
        """The region's CAPRI 2030 terms restricted to pmp_capri_parts (crops' matrix, animals' herd terms)."""
        if not g:
            return g
        parts = tuple(getattr(self, "pmp_capri_parts", ()))
        anim = set(ANIMALS)
        return {k: v for k, v in g.items()
                if (("animals" in parts) if k[0] in anim else ("crops" in parts))} or None

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
                rd, eps, use_share_term=True,
                cross_group_terms=self.cross_group.get(region),
                cross_price_elas=self.cross_price.get(region))
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
            sim_year=(int(d["market_year"]) if d.get("market_year") else None),
            cover_crops=(d["cover_crops"].loc[region] if d.get("cover_crops") is not None
                         and region in d["cover_crops"].index else None),
            winter_cover_share=(d.get("winter_cover_share") or {}).get(region),
            grass_intensity=self._intensity_q_at(
                d, d["grass_intensity"].loc[region] if d.get("grass_intensity") is not None
                and region in d["grass_intensity"].index else None, ("q_ext", "q_int"), "crops"),
            histosol=(d["histosol"].loc[region] if d.get("histosol") is not None
                      and region in d["histosol"].index else None),
            dairy_intensity=self._intensity_q_at(
                d, d["dairy_intensity"].loc[region] if d.get("dairy_intensity") is not None
                and region in d["dairy_intensity"].index else None, ("q_low", "q_high"), "animals"),
            cattle_intensity=(lambda ci: {a: self._intensity_q_at(d, s_, ("q_z", "q_b"), "animals") for a, s_ in ci.items()}
                              if ci else ci)((d.get("cattle_intensity") or {}).get(region)),
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
            capri_level_ratio=(
                d["capri_level_ratio"].loc[region]
                if d.get("capri_level_ratio") is not None
                and region in d["capri_level_ratio"].index else None),
            fodder_balance=(d.get("fodder_balance") or {}).get(region),
            # CAPRI's land market of its 2030 baseline calibration with CAPRI's 2030 PMP terms (K61), else the 2017 one
            land_market=((d.get("land_market_2030") or {}).get(region)
                         if int(d.get("market_year", 2017) or 2017) == 2030
                         and str(getattr(self, "pmp_source", "elasticity")) in ("capri2030", "recipe")
                         and "land" in tuple(getattr(self, "pmp_capri_parts", ()))
                         and (d.get("land_market_2030") or {}).get(region)
                         else (d.get("land_market") or {}).get(region)),
            # CAPRI's land rents at the market year's calibration point (tools/build/build_land_rents.py: 2030 reference,
            # 2017 results)
            land_rents=(((d.get("land_rents") or {}).get(int(d.get("market_year", 2017) or 2017)) or {}).get(region)),
            # CAPRI's PMP terms of its 2030 baseline calibration (K61): at the 2030 market year, with pmp_source "capri2030"
            pmp_capri=self._pmp_terms_for(d, region),
            uncalibrated=self._uncalibrated(d, region),
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
        capri_data/2017/abatement/fert_options_jul15.csv, tools/build/build_fert_options_jul15.py);
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
        The slope of the options without farm-size curves carries CAPRI's fertiliser-saving term (ghgMiti.gms
        l. 1016-1035, fert_slope_with_saving): the NLP form's fertilisation block holds the convex saving
        (N(m) = N0 / (1 + nmE m)), which the term offsets so that the base and the maximum share stay stationary."""
        cls = type(self)
        if cls._FERT_JUL15 is None:
            from pathlib import Path as _P
            import json as _json
            root = _P(__file__).resolve().parents[2] / "capri_data"
            f = root / "2017" / "abatement" / "fert_options_jul15.csv"
            tab = read_csv(f) if f.exists() else pd.DataFrame()
            c8 = _json.load(open(root / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]
            to8 = {}
            for k, lst in c8.items():
                if not k.endswith("000000"):
                    for n2 in lst:
                        to8.setdefault(n2, k)
            # the shared map (tools/build/build_region_map.py: correspondence fixes, NUTS splits and merges)
            _rm = root / "shared" / "region_capri_map.csv"
            if _rm.exists():
                for _r in read_csv(_rm, dtype=str).fillna("").itertuples(index=False):
                    if _r.capri_region:
                        to8[_r.region] = _r.capri_region
            cls._FERT_JUL15 = ({(r.region, str(r.option).upper()): r for r in tab.itertuples(index=False)}, to8)
        tab, to8 = cls._FERT_JUL15
        msc = capri_ms(region)
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
                slope = k1 * (rs1 - rs0) / (smax - s0)
                if getattr(type(self), "fert_slope_with_saving", True):
                    # CAPRI's pmpParSqr (envind/ghgMiti.gms l. 1016-1035, the 'alternative approach'): the FOC is zero
                    # at the initial and the maximum share with the fertiliser saving valued at the member state's
                    # NITF price p: + nmE x p x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0), nmE = NMIN + EmiCalmin
                    pf = self._nitf_price_ms(msc)
                    nme = nmin + self._emi_cal_min(region, r8, name)
                    if pf and nme > -1.0 / max(smax, 1e-9):
                        slope += nme * pf * ((1.0 + nme * smax) ** -2 - (1.0 + nme * s0) ** -2) / (smax - s0)
                # CAPRI's curvature can be negative (precision farming, NMIN about 0.5): its total cost with the
                # endogenous fertiliser saving (convex: N(m) = N0 / (1 + nmE m)) has its stationary points at both
                # shares. The NLP form carries the saving through the fertilisation block and takes it as it is
                out.append((name, nmin, rs0 * k1, slope, s0, smax))
        return out

    #: CAPRI's fertiliser-option curvature with the fertiliser saving valued (ghgMiti.gms l. 1016-1035); False: without
    #: (this model before 24 October 2026)
    fert_slope_with_saving = setting("supply.fert_slope_with_saving")

    @staticmethod
    def _nitf_price_ms(ms8):
        """CAPRI's unit value of mineral N of the member state in the simulation year (DATA(ms,"UVAG","NITF","Y"),
        EUR/t; npk_region_2030.csv), or None."""
        from capri_mod.fert.npk import NPKData
        t = NPKData.get().region(ms8, "N") if ms8 else None
        v = getattr(t, "uvag_eur_t", None) if t is not None else None
        return float(v) if v is not None and v == v else None

    def _emi_cal_min(self, region, r8, tech):
        """CAPRI's EmiCalmin of a fertiliser option (envind/ghgMiti.gms l. 936-944): the base mineral N losses
        (p_emiloss of NETF: NH3, NOx, N2O, runoff) x the option's side effects (othImpact NH3SYN, NOXSYN, N2OSYN,
        NO3SRUN), raised to p_fertEffCor with its sign. 0 without side-effect data (CAPRI's literature effects are
        for the nitrification inhibitor)."""
        from capri_mod.supply import n_cascade as _nc
        sv = {it: fert_side_value(region, tech, it) for it in ("NH3SYN", "NOXSYN", "N2OSYN", "NO3SRUN")}
        if all(v is None for v in sv.values()):
            return 0.0
        _, G, _ = _nc.load()
        g = G.get(r8) or G.get(capri_ms(region)) or {}
        if not g:
            return 0.0
        L = _nc.netf(g, float(g.get("run_surf", 0.0)))
        v = (L["NH3"] * (sv["NH3SYN"] or 0.0) + L["NOX"] * (sv["NOXSYN"] or 0.0) + L["N2O"] * (sv["N2OSYN"] or 0.0)
             + L["RunTot"] * (sv["NO3SRUN"] or 0.0))
        return (abs(v) ** self.FERT_EFF_COR) * (1.0 if v >= 0 else -1.0) if v else 0.0

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
    BASE_CAL_ROUNDS = setting("projection.base_cal_rounds")
    #: CAPRI sets.gms l. 5606, FODF / OFAR, GRAS, ROOF, MAIF / (the model's OFOD = CAPRI's OFAR plus ROOF)
    FODDER_ACTS = ("GRAS", "MAIF", "OFOD", "ROOF")

    def calibrate_to_base(self, results: dict, reset: bool = False) -> float:
        """CAPRI's calibration of the supply models to the baseline (CAPMOD calibrates its PMP terms so that the
        baseline year's solution reproduces the projected activity levels): per region, the linear cost terms move by
        Q (x - x_target), the shift that makes the target optimal when the constraints' duals stay put, with the
        target the region's projected levels (the model's base levels). Returns the largest remaining drift, relative
        to the target (activities of at least 1 unit), before this round's correction; 0 once the rounds are used."""
        if reset:
            self._base_cal_round = 0
            self._base_cal_prev = {}
            self._base_cal_stalled = set()
        rnd = int(getattr(self, "_base_cal_round", 0) or 0)
        worst = 0.0
        if rnd >= self.BASE_CAL_ROUNDS:
            return 0.0
        prev_r = getattr(self, "_base_cal_prev", None) or {}
        stalled = getattr(self, "_base_cal_stalled", None) or set()
        for region, res in (results or {}).items():
            if region in stalled:
                continue
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
            w_r = float(np.max(np.abs(d[big]) / xb[big])) if big.any() else 0.0
            # per region: a region whose drift a round does not reduce by 5% is left as it is (what the linear terms
            # cannot move); the others go on (before K36 one stalled region stopped the calibration everywhere)
            if os.environ.get("CAPRI_CAL_DEBUG"):
                _j = int(np.argmax(np.where(big, np.abs(d) / np.maximum(xb, 1e-9), 0.0)))
                print(f"[cal] round {rnd} {region} drift {w_r:.4f} at {acts[_j]} x {xs[_j]:.2f} target {xb[_j]:.2f}", flush=True)
            if rnd > 0 and region in prev_r and w_r > float(_settings().get("projection.base_cal_stall_ratio")) * prev_r[region]:
                stalled.add(region)
                continue
            prev_r[region] = w_r
            worst = max(worst, w_r)
            mo.f = np.asarray(mo.f, float) + np.asarray(mo.Q, float) @ d
            mo._base_cal_shift = np.asarray(getattr(mo, "_base_cal_shift", np.zeros(len(acts))), float) \
                + np.asarray(mo.Q, float) @ d
        self._base_cal_round = rnd + 1
        self._base_cal_prev, self._base_cal_stalled = prev_r, stalled
        self._base_cal_drift = worst
        return worst

    # CAPRI's crop nutrient balance (NUTNED_, fertDistExcr_) and manure market in every EU solve, not only under
    # the N target (Sprint 9k)

    def _manure_context(self, region, model):
        """{"man_d", "nmin", "ybase"} for the regional model's crop-need row, manure trade columns and ammonia options
        (CAPRI has them in every run), or None outside the EU (msNoEU)."""
        if region[:2] in self.NON_EU_PREFIXES:
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
                inner.set_variant(bool(getattr(self, "manure_trade_on", True)))
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
    NBAL_TOL_ABS = setting("supply.nbal_tol_abs")
    NBAL_TOL_REL = setting("supply.nbal_tol_rel")
    #: at most this many solves per region and iteration to find its N price
    NBAL_INNER_MAX = setting("supply.nbal_inner_max")

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

    #: The market whose price each activity earns, where the codes differ.
    #: The market-to-farm price signal is keyed by MARKET COMMODITY, but margins
    #: and the yield-price response look it up by ACTIVITY: without this map no
    #: animal ever saw a meat, milk or egg price change (the +7% pork price under
    #: Farm-to-Fork never reached pig farmers). Rye and oats earn their own market
    #: prices (RYEM, OATS), as in CAPRI.
    ACTIVITY_PRICE_SOURCE = {
        "DCOW": "MILK",
        "BULL": "BEEF", "BCOW": "BEEF", "HFRS": "BEEF", "CALV": "BEEF",
        "PIGS": "PORK", "PIGF": "PORK",
        "BROI": "POUL", "LAYS": "EGGS", "SHGM": "MILK", "SHGF": "SGMT",
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

    def _base_rations(self) -> None:
        """CAPRI's rations and base feed prices for the regional models' feeding block, where no model has set them (a
        SupplyModule used on its own): the same data the model hands over before its first solve
        (CAPRIModel._update_rations, feed.ration.ration_model_for). Without them a regional model has no feeding block,
        which CAPRI's form always has."""
        from capri_mod.feed.ration import ration_model_for, rations_by_region, feed_prices_by_region
        rm = ration_model_for(self.data, None, getattr(self, "pmp_source", "elasticity"),
                              getattr(self, "pmp_capri_parts", ()))
        self.feed_rations = rations_by_region(rm)
        self.feed_prices = feed_prices_by_region(rm, None)

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
        if getattr(self, "feed_rations", None) is None:
            self._base_rations()
        target_regions = regions or self.regions
        results = {}
        n_failed = 0

        self.max_nbal_update = 0.0
        # A new run (no price signal yet) starts from no nitrogen price - reset ONCE, here. These resets used to
        # sit inside the region loop, so on a run's first iteration every region wiped the state, secant memory and
        # bracket of all regions before it: only the last region kept them, and every other region lost an iteration.
        if price_signals is None or not hasattr(self, "_nbal_state"):
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
            if lu_r > getattr(self, "max_nbal_update", 0.0):
                self.max_nbal_region = (region, kind)
            self.max_nbal_update = max(getattr(self, "max_nbal_update", 0.0), lu_r)

        if verbose:
            print(f"  Supply module complete: {len(results)} regions, "
                  f"{n_failed} non-converged.")
        return results

    #: a region's solves within one outer iteration taking longer than this are reported (seconds)
    SLOW_REGION_SECONDS = setting("diagnostics.slow_region_seconds")

    def _solve_region(self, region, _pol_all, price_signals, verbose=False):
        """_solve_region_impl, timed: a slow region is reported with its number of regional solves."""
        import time as _t
        t0 = _t.time()
        mdl = (getattr(self, "_models", None) or {}).get(region)
        n0 = int(getattr(mdl, "_n_solves", 0) or 0) if mdl is not None else 0
        out = self._solve_region_impl(region, _pol_all, price_signals, verbose)
        dt = _t.time() - t0
        if dt > self.SLOW_REGION_SECONDS:
            mdl = (getattr(self, "_models", None) or {}).get(region)
            n1 = int(getattr(mdl, "_n_solves", 0) or 0) if mdl is not None else 0
            import warnings as _w
            _w.warn(f"slow regional solve {region}: {dt:.0f} s, {n1 - n0} solves of the regional model "
                    f"(NLP relaxed: {getattr(mdl, '_nlp_relaxed', None)})", RuntimeWarning)
        return out

    def _solve_region_impl(self, region, _pol_all, price_signals, verbose=False):
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
                        target = sp * (1.0 - float(0.5 if policy_scenario.get("surplus_cut") is None else policy_scenario["surplus_cut"]))
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
            # each region's balance price is held HERE, not on the model; it is reset once per run, before the loop.
            # The nitrogen-balance price is settled WITHIN the iteration, at fixed market prices: it depends only on
            # this region's own shadow prices.
            nb_used = getattr(self, "_nbal_state", {}).get(region, 0.0) if surplus_row else 0.0
            n_metric = 0.0
            # CAPRI prices raw milk per member state (its dairies' fat and protein balances, raw milk not
            # traded): the region's milk price is the EU signal plus its member state's departure from the
            # EU average (MarketModule.dairy_block, CAPRIModel)
            _ps_r = price_signals
            # CAPRI's EU trade blocks: the member state's block price as a departure from the EU signal
            # (CAPRIModel, MarketModule.eu_blocks); activity-keyed entries follow their products
            _bdev = (getattr(self, "price_dev_ms", None) or {})
            if _bdev and price_signals is not None:
                _msb = capri_ms(region)
                _dvs = _bdev.get(_msb)
                if _dvs is not None:
                    _dvs = self._activity_signals(_dvs)
                    _ps_r = price_signals.add(_dvs.reindex(price_signals.index).fillna(0.0))
            _mdev = getattr(self, "milk_price_dev_ms", None) or {}
            if _mdev and price_signals is not None and "MILK" in price_signals.index:
                _msr = capri_ms(region)
                _dv = float(_mdev.get(_msr, 0.0))
                if _dv:
                    _ps_r = _ps_r.copy()
                    _ps_r["MILK"] = float(price_signals["MILK"]) + _dv
                    if "DCOW" in _ps_r.index:
                        _ps_r["DCOW"] = float(_ps_r["MILK"])
            solve_kw = dict(
                price_shock=_ps_r,
                policy_shock=policy_scenario,
                nitrate_limit=nlim,
                set_aside_requirement=sa,
                surplus_row=surplus_row,
                mineral_cap=mcap,
            )
            model.ration_state = (getattr(self, "ration_state", None) or {}).get(region)
            model.manure_pool_price = (getattr(self, "manure_pool_price", None) or {}).get(region[:2], 0.0)
            model.yani_price_ratio = getattr(self, "yani_price_ratio", None)
            _yms = getattr(self, "yani_price_ratio_ms", None) or {}
            if _yms:
                # young-animal prices of the member state's market (CAPRI yaniMarket_ per trade block)
                _msy = capri_ms(region)
                model.yani_price_ratio = _yms.get(_msy, model.yani_price_ratio)
            model.feed_rations = (getattr(self, "feed_rations", None) or {}).get(region)
            model.feed_prices = (getattr(self, "feed_prices", None) or {}).get(region)
            # CAPRI's feed bulk prices of the region's member state (feedBlkPrice_, CAPRIModel)
            _ms = capri_ms(region)
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
            try:
                model._fert_techs_all = self._fert_techs(region)      # CAPRI's fertiliser options (NLP form)
            except Exception:
                model._fert_techs_all = []
            result = model.solve(n_balance_price=nb_used, **solve_kw)
            # manure market: hand the region's endogenous manure trade and allocated
            # mineral N to the environmental accounting (else the reported N balance
            # recomputes them from herds and fixed rates and misses the trade)
            result.manure_trade = tuple(getattr(model, "_last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
            result.mineral_n_alloc = _mineral_n_for_accounts(model)
            result.fert_npk = getattr(model, "_last_npk", None)
            result.manure_availability = getattr(model, "_pool_avail", 0.0)
            result.animal_n_relief = _merge_relief(model)
            result.manure_ni_nh3 = dict(getattr(model, "_manure_ni_nh3", None) or {})
            result.cover_crops = dict(getattr(model, "_cover_solved", None) or getattr(model, "_cover", None) or {})
            result.animal_nh3_saved = dict(getattr(model, "_animal_nh3_saved", None) or {})
            result.animal_n_kept = dict(getattr(model, "_animal_n_kept", None) or {})
            result.manure_tech_shares = dict(getattr(model, "_manure_tech_shares", None) or {})
            result.grass_ext_shift = float(getattr(model, "_last_grass_z", 0.0) or 0.0)
            result.dairy_low_shift = float(getattr(model, "_last_dairy_z", 0.0) or 0.0)
            result.cattle_shift = dict(getattr(model, "_last_cattle_z", None) or {})
            result.yani_dnet = getattr(model, "_yani_dnet", None)
            result.genetics_shift = dict(getattr(model, "_last_genet_z", None) or {})
            result.histosol_fallow = dict(getattr(model, "_last_hist_fallow", None) or {})
            _ls = getattr(model, "_land_solution", None) or {}
            result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model, "_land_types_used", []) if t_ in _ls}
            result.luc = _luc_of(model, result.land_types)
            result.n_target_relaxed = bool(getattr(model, "_n_target_relaxed", False))
            if surplus_row and model._ni_inside() and getattr(model, "_nlp_ok", False):
                # capri-mod-proto: nothing in the regional model depends on the N price any more
                # (fertiliser and ammonia technologies and the inhibitor on manure are all decided
                # inside the regional model), so the target is a plain constraint, as in CAPRI's NLP:
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
            # Attach the regional model's FINAL state to the result stored: the
            # inner N-price loop re-solves and returns new result objects, so
            # fields set after the first solve were lost (technologies are only
            # adopted once the N price is positive, i.e. after the first solve).
            try:
                result.manure_trade = tuple(getattr(model, "_last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
                result.mineral_n_alloc = _mineral_n_for_accounts(model)
                result.fert_npk = getattr(model, "_last_npk", None)
                result.manure_availability = getattr(model, "_pool_avail", 0.0)
                result.animal_n_relief = _merge_relief(model)
                result.manure_ni_nh3 = dict(getattr(model, "_manure_ni_nh3", None) or {})
                result.cover_crops = dict(getattr(model, "_cover_solved", None) or getattr(model, "_cover", None) or {})
                result.animal_nh3_saved = dict(getattr(model, "_animal_nh3_saved", None) or {})
                result.animal_n_kept = dict(getattr(model, "_animal_n_kept", None) or {})
                result.manure_tech_shares = dict(getattr(model, "_manure_tech_shares", None) or {})
                result.grass_ext_shift = float(getattr(model, "_last_grass_z", 0.0) or 0.0)
                result.dairy_low_shift = float(getattr(model, "_last_dairy_z", 0.0) or 0.0)
                result.cattle_shift = dict(getattr(model, "_last_cattle_z", None) or {})
                result.yani_dnet = getattr(model, "_yani_dnet", None)
                result.genetics_shift = dict(getattr(model, "_last_genet_z", None) or {})
                result.histosol_fallow = dict(getattr(model, "_last_hist_fallow", None) or {})
                _ls = getattr(model, "_land_solution", None) or {}
                result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model, "_land_types_used", []) if t_ in _ls}
                result.luc = _luc_of(model, result.land_types)
                result.n_target_relaxed = bool(getattr(model, "_n_target_relaxed", False))
                result.nitrate_n_extra = model._nitrate_extra()
                # CAPRI's mineral fertiliser reduction: the regulations of the inner fertiliser model (reporting)
                result.mineral_cap = ({k: mcap[k] for k in ("kind", "reduction", "base_mineral", "group_caps",
                                                            "limcres")} if mcap else None)
                result.feed_dm = (dict(getattr(model, "_last_feed_dm", None) or {})
                                  if getattr(model, "_last_duals", None) is not None else None)
                result.feed_t = (dict(getattr(model, "_last_feed_t", None) or {})
                                 if getattr(model, "_last_duals", None) is not None else None)
                # fertiliser technologies inside: each crop's reported intensity includes its
                # inside factor m_c / (n_c area_c) (reporting only; the N row never sees it)
                _ff = getattr(model, "_fert_inside_factor", None) or {}
                if _ff and getattr(model, "_last_duals", None) is not None:
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
            return region, result, (0 if result.converged else 1), n_metric, "N price"
        except Exception as e:
            if verbose:
                print(f"    WARNING: Region {region} failed: {e}")
            return region, None, 1, 0.0, None

    #: worker processes for the regional solves: None = the machine's cores (CAPRI_WORKERS overrides), 1 = in this
    #: process. CAPRI solves its regional models one after another (or in parallel GAMS grid jobs); they are
    #: independent at given market prices, so the results do not depend on the number of workers
    n_workers = setting("run.n_workers", lambda v: None if int(v) == 0 else int(v), run_state=True)
    #: regional state carried between iterations, and the region-keyed caches, sent back from the workers
    _PAR_STATE = ("_nbal_state", "_nbal_bracket", "_nbal_prev")
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
        # concurrent.futures, not multiprocessing.Pool: a worker that dies (killed for memory, a crash in a solver
        # library) breaks the executor, which raises, where Pool.imap waits forever for the lost task (two runs at
        # once on 8 GB with two workers each hung that way, 26 October 2026). The regions not yet returned are then
        # solved in this process, with a warning: the results do not depend on the number of workers.
        from concurrent.futures import ProcessPoolExecutor
        from concurrent.futures.process import BrokenProcessPool
        done = set()
        pool = ProcessPoolExecutor(nw, mp_context=multiprocessing.get_context("fork"))
        broken = False
        try:
            try:
                for out, model, state, caches in pool.map(_par_solve_region, rest, chunksize=1):
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
                    done.add(region)
                    yield out
            except BrokenProcessPool as exc:
                # the workers still alive can block for ever writing a result nobody reads any more (seen under
                # coverage, 26 October 2026): kill them before the executor's shutdown waits for them
                broken = True
                _kill_pool_workers(pool)
                left = [r for r in rest if r not in done]
                warnings.warn(f"a worker process of the regional solves died ({exc!r}); the {len(left)} regions "
                              "left are solved in this process", RuntimeWarning, stacklevel=2)
                self.worker_failures = int(getattr(self, "worker_failures", 0) or 0) + 1
                for r in left:
                    yield self._solve_region(r, _pol_all, price_signals, verbose)
        finally:
            _PAR_CTX = None
            if broken:
                pool.shutdown(wait=False, cancel_futures=True)
            else:
                pool.shutdown(wait=True)

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

def _kill_pool_workers(pool) -> None:
    """Kill the worker processes of a broken ProcessPoolExecutor (its private process table; nothing if absent)."""
    for proc in list((getattr(pool, "_processes", None) or {}).values()):
        try:
            proc.kill()
            proc.join(5)
        except Exception:                                     # already gone
            pass


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


def _luc_of(model, land_types):
    """CAPRI's land-use change transitions (capri_mod.environmental.luc) of the region at its solved land types,
    moved from the base land types of the land market; None outside CAPRI's LUC data."""
    try:
        from capri_mod.environmental.luc import LUCModel
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        env_ = getattr(model, "_env_for_surplus", None)
        inner = env_.__dict__.get("_inner_fert") if env_ is not None else None
        if inner is None:
            inner = InnerFertDist()
        cr = inner._map.get(model.data.region_id)
        lm = getattr(model.data, "land_market", None) or {}
        L0 = lm.get("base_kha") or {}
        d = {t: float(land_types.get(t, L0.get(t, 0.0))) - float(L0.get(t, 0.0)) for t in ("ARAC", "FRUN", "GRAS", "FORE", "OLND")
             if t in (land_types or {})}
        return LUCModel.get().solve(cr, d) if cr else None
    except Exception as _exc:
        import warnings as _w
        _w.warn(f"LUC model failed for {model.data.region_id}: {_exc!r}")
        return None


def _mineral_n_for_accounts(model):
    """Mineral N of the region's solution for the environmental accounts: the purchases of the NLP form's
    fertilisation block (CAPRI's v_netPutQuant(NITF)), else the mineral-N allocation column (or None)."""
    npk = getattr(model, "_last_npk", None) or {}
    if "N" in npk:
        return float(npk["N"]["purchase"])
    return getattr(model, "_last_mineral_n", None)


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
    (capri_data/2017/abatement/fert_side_effects.csv, tools/build/build_fert_side_effects.py)."""
    global _FERT_SIDE_TAB
    if _FERT_SIDE_TAB is None:
        from pathlib import Path as _P
        f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "fert_side_effects.csv"
        _FERT_SIDE_TAB = ({(r.region, r.technology, r.item): float(r.value) for r in read_csv(f).itertuples()}
                          if f.exists() else {})
    return _FERT_SIDE_TAB.get((region, tech, item))

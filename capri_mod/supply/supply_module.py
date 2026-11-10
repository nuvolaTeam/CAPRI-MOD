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
import multiprocessing
import os
import warnings
from pathlib import Path

from capri_mod.supply.capri_pmp import (
    share_term, ARABLE_ACTIVITIES,
)
from capri_mod.params import param, param_table
from capri_mod.units import M_N2O, M_N2O_N
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS, ACTIVITY_CLASSES, CROPS_ON_LAND, LAND_MARKET_TYPES, CATTLE_SPLITS,
)
from capri_mod.data.definitions import MS_CODE, capri_ms, IdentityMap, is_eu
from capri_mod.tableio import read_input
from capri_mod.supply import inputs as _inputs


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

#: CAPRI's fixed production activities, held at their data level (supply/prep_sim.gms l. 250: v_actLevl.FX for FACT;
#: sets.gms l. 2317 FACT = MFCACT + OANI, l. 131 MFCACT = OOIL, OIND, FallGr, NURS, FLOW, OCRO, NECR). NURS, FLOW and
#: OCRO were endogenous here until 23 October 2026 (found by the proxy audit: they had no CAPRI elasticity)
FIXED_ACTIVITIES = tuple(a for a, r in ACTIVITY_CLASSES.items() if r["fixed"] == "1")   # model_activity_classes.csv (N6)
#: an activity whose level at the calibration point is at most this (1000 ha / 1000 head) has no level: CAPRI has no
#: variable for it (v_actLevl exists where p_technFact(..,"LEVL",..) is set); the bounds hold it at zero
#: (setting supply.absent_activities_fixed) and the rules that refer to it (CAP greening) leave it out
# (the level: the setting supply.absent_level)

# CAPRI's p_OverFertMarkUp and p_fertEffCor (envind/ghgMiti.gms) and the supply's other parameters are read where they
# are used, through the run's inputs (param(): <data_dir>/codes/model_parameters.csv; refactor stage 3, N1)


def overfert_factor(region: str):
    """CAPRI's over-fertilisation factor x = v_cropNutNeedMultFact(ru, NITF, "T") for a model
    region (capri_data/2030/environment/crop_nut_need_mult_fact_2030.csv, built by
    tools/build/build_overfert_factors.py from CAPRI's priFertDist results). Every unit of the model has one
    (CAPRI's limits on the fertiliser technologies, Tot_MitFert_ and the regional maximum shares, need it): a missing
    file or region is an error (K74, 29 October 2026; before, the limits were dropped with a warning, a fallback no
    unit of the model reached)."""
    def load(inp):
        f = inp.path("crop_nut_need_mult_fact_2030.csv", "environment")
        if not f.exists():
            raise FileNotFoundError(f"CAPRI's over-fertilisation factors missing: {f} (tools/build/build_overfert_factors.py)")
        return {str(r.region): float(r.x) for r in inp.csv(f.name, "environment").itertuples(index=False)}
    x = _inputs.current().cached("overfert", load).get(region)
    if x is None:
        raise KeyError(f"{region}: no CAPRI over-fertilisation factor in crop_nut_need_mult_fact_2030.csv")
    return x






def fert_option_table() -> dict:
    """{model region: [row]} of CAPRI's fertiliser options (fert_options_jul15.csv)."""
    def load(inp):
        out = {}
        for r in inp.csv("fert_options_jul15.csv", "abatement").itertuples(index=False):
            out.setdefault(r.region, []).append(r)
        return out
    return _inputs.current().cached("fert_options", load)


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
    sexes (young_animals_<base year>.csv, the default) or per sex as CAPRI's balances (young_animals_by_sex_<base
    year>.csv) with
    the cattle member splits (RegionalSupplyModel.use_cattle_member_splits; tools/build/build_young_animals.py;
    capri_mod/data/nested_tables.py)."""
    by_sex = bool(getattr(RegionalSupplyModel, "use_cattle_member_splits", False))
    by = _inputs.base_year()                                          # the base year's tables (K52f)
    name = f"young_animals_by_sex_{by}.csv" if by_sex else f"young_animals_{by}.csv"

    def load(inp):
        from capri_mod.data.nested_tables import read_young_animals
        return read_young_animals(inp.path(name, "supply"))
    return _inputs.current().cached(name, load)


def active_technologies():
    """CAPRI's active mitigation technologies of the Green Deal reference (activeTech,
    capri_data/2017/abatement/active_technologies.csv, tools/build/build_active_technologies.py). A missing file is an
    error (K74, 29 October 2026; before, every option with data was made available with a warning)."""
    def load(inp):
        f = inp.path("active_technologies.csv", "abatement")
        if not f.exists():
            raise FileNotFoundError(f"CAPRI's active mitigation technologies missing: {f} "
                                    "(tools/build/build_active_technologies.py)")
        return set(inp.csv(f.name, "abatement")["technology"].str.upper())
    return _inputs.current().cached("active_technologies", load) or None


def fert_efficiency_cap(region: str):
    """Largest total efficiency gain E = sum share x NMIN CAPRI allows (Tot_MitFert_):
    1 + E <= max(x + 0.1, 1). None when x is unknown."""
    x = overfert_factor(region)
    return None if x is None else max(x + param("OVERFERT_MARKUP"), 1.0) - 1.0


def _csv_dict(name: str, where: str, col: str) -> Dict[str, float]:
    """{key: value} of one column of an input CSV of the run (first column the key), NaN rows left out."""
    def load(inp):
        s = inp.csv(name, where, index_col=0)[col].dropna()
        return {str(k): float(v) for k, v in s.items()}
    return _inputs.current().cached(f"{where}/{name}:{col}", load)


class _InputColumn:
    """A class attribute holding one column of an input CSV of the run (_csv_dict), read when first used (it was read
    at import from the fixed capri_data/2017 path until 30 October 2026)."""

    def __init__(self, name: str, where: str, col: str):
        self.name, self.where, self.col = name, where, col

    def __get__(self, obj, owner=None) -> Dict[str, float]:
        return _csv_dict(self.name, self.where, self.col)


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
    #: CAPRI's dairy split DCOL/DCOH (share_low, d<item>_rel, q_low, q_high), Sprint 7b
    dairy_intensity: Optional[pd.Series] = None
    #: CAPRI's bull and heifer splits {animal: Series} (BULL/BULH, HEIL/HEIH), Sprint 7c
    cattle_intensity: Optional[dict] = None
    genetics_effects: Optional[dict] = None
    #: CAPRI's histosols: organic-soil shares, emission factors, fallowing cost terms
    histosol: Optional[pd.Series] = None
    #: CAPRI's crop technologies T1/T2 (S1): per crop with both, the T1 - T2 differences and CAPRI's 2030 technology
    #: block in the mix columns' variables (techn_mix_2030.csv, pmp_capri_2030_mix.csv); with CAPRI's 2030 PMP terms only
    techn_mix: Optional[pd.DataFrame] = None
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
    #: CAPRI's maps to them (inputs/load_organic_yieldgap.gms): member state -> PESETA macro-region (ms2peseta) and
    #: model crop -> product group (pact2yieldGap), organic_yield_gap_regions.csv / _groups.csv
    organic_yield_gap_regions: Optional[dict] = None
    organic_yield_gap_groups: Optional[dict] = None

    #: CAPRI's Green Deal targets for this region's member state: extra
    #: landscape land (points of UAA) and organic conversion (points of arable,
    #: grassland and permanent-crop area).
    landscape_target_pp: Optional[float] = None
    organic_targets_pp: Optional[pd.Series] = None
    #: {CAPRI crop group (NGRP): its organic target class} (organic_ngrp_class.csv)
    organic_ngrp_class: Optional[dict] = None
    #: the Green Deal group's slack on the fertiliser priors' partial derivative (fert_partial_slack.csv): the region's
    #: listed crop groups ("" alone: the tiny-prior rule only); None outside CAPRI's list
    fert_partial_slack: Optional[list] = None


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
    #: CAPRI's obligatory set-aside ISET (1000 ha; SETA_, supply/land.py _obligatory_set_aside): 0 without rates
    iset: float = 0.0


# ---------------------------------------------------------------------------
# PMP CALIBRATION
# ---------------------------------------------------------------------------

def saving_slope(nme: float, value: float, m0: float, m1: float) -> float:
    """CAPRI's saving term of a fertiliser option's curvature (envind/ghgMiti.gms l. 1016-1050): nmE x value x ((1 + nmE
    m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0), the N saved valued at its price (mineral N: the member state's unit value;
    manure N: p_manureShadVal); 0 where it is not defined (m1 <= m0, or 1 + nmE m <= 0)."""
    if not m1 > m0 or 1.0 + nme * m0 <= 0 or 1.0 + nme * m1 <= 0:
        return 0.0
    return nme * value * ((1.0 + nme * m1) ** -2 - (1.0 + nme * m0) ** -2) / (m1 - m0)


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
                 capri_g: Optional[dict] = None):
        self.activities = activities
        # CAPRI's 2030 PMP matrix of the crops (K61), {(act_i, act_j): g}: replaces the elasticity-calibrated block
        self.capri_g = capri_g or {}
        self.n_capri_acts = 0
        self.n = len(activities)
        self.supply_elasticities = supply_elasticities
        # CAPRI's 1 - 0.2*sqrt(share of arable) curvature scaler; None -> 1.0
        self.share_terms = share_terms

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
        eps_capped = np.clip(eps, 1e-4, param("ELAS_CAP"))
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

        # Off-diagonal terms: CAPRI's structure (supply_model.gms QUADRA_ with GRPLEVL_, p_useCropSpecificQMatrix 0) has
        # cross terms only through the crop groups' levels (EPRD_TO_GRP: CERE, CER2, OILS, OARA, FARA); "for fruits &
        # vegetables, permanent crops, grassland and the animal sectors, only diagonal terms" (CAPRI documentation,
        # ch. 5). They come with CAPRI's own PMP terms (capri_g, below: pmp_source capri2030 or recipe). A crop without
        # CAPRI terms in the region has none in CAPRI's QUADRA_ either, so its row here is diagonal. Until 29 October
        # 2026 such crops (and every crop when pmp_capri_parts left out "crops") could take a PELA cross-price
        # elasticity or a scaled p_pmpQuadPact term capped at 0.05 x sqrt(Q_ii Q_jj): capri-mod's, not CAPRI's
        # (PROXY_AUDIT S065; KNOWN_ISSUES K105), removed with the two inputs it read.
        # CROSS_TERMS: "capri" (default) or "none" (diagonal only: CAPRI's decomposition experiment, 2008
        # documentation sect. 7.3, tools/check/pmp_cross_term_check.py): with "none" CAPRI's terms enter diagonal only.
        mode = str(getattr(type(self), "CROSS_TERMS", "capri"))

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
                        if mode == "none" and i != j:
                            continue
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

# refactor stage 3a: the regional model's methods in mixin modules of this package
from capri_mod.supply.livestock import LivestockBlock  # noqa: E402
from capri_mod.supply.state import ModuleStateMixin, RegionalStateMixin  # noqa: E402
from capri_mod.supply import state as _st  # noqa: E402
from capri_mod.supply.fertilisation import FertilisationBlock  # noqa: E402
from capri_mod.supply.abatement import AbatementBlock  # noqa: E402
from capri_mod.supply.policy import PolicyBlock  # noqa: E402
from capri_mod.supply.land import LandBlock  # noqa: E402
from capri_mod.supply.nlp import NLPBlock  # noqa: E402
from capri_mod.supply.techn_mix import TechnMixBlock  # noqa: E402


class RegionalSupplyModel(RegionalStateMixin, LivestockBlock, FertilisationBlock, AbatementBlock, PolicyBlock,
                          LandBlock, NLPBlock, TechnMixBlock):
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

    #: the state a solve leaves for the next one (linearisation points, warm starts, splits, rations, last solutions),
    #: besides the warm-start fields named _nlp*: what the market supply Hessian saves and restores so that every price
    #: shock starts from the baseline's state (model._market_supply_hessian). Found by comparing the model's attributes
    #: before and after a solve (27 October 2026); bookkeeping (res.n_solves) and the shared environmental
    #: module are not state. 2 November 2026 (docs/design/STAGE3_BEHAVIOUR_CHANGES.md, the project lead's decision):
    #: sv.n_relax_sticky added (the JRC121368 relaxation kept for the same N target), ev.ghg_nr_obj taken out (an
    #: identity reference: its deep copy could never match, and the tax's undo never acts across solves)
    SOLVE_STATE = ("ev.amm_cost", "sv.amm_last", "res.animal_n_kept", "ev.animal_n_relief", "res.animal_nh3_saved",
                   "res.cover_solved", "res.fd_model", "res.land_solution", "res.last_aug", "res.last_cattle_z",
                   "res.last_dairy_z", "ev.last_duals", "res.last_feed_dm", "res.last_feed_t", "res.last_genet_z",
                   "res.last_hist_fallow", "res.last_mix_z", "res.last_npk", "ev.last_req_duals",
                   "ev.manure_ni_nh3", "ev.manure_ni_relief", "res.manure_tech_shares", "ev.price_shock_now",
                   "sv.wc_solved", "seen.feed_rations", "sv.n_relax_sticky")
    #: the regional NLP's fields (warm starts, calibration, fallbacks and their diagnostics): what the market supply
    #: Hessian restored by the prefix "_nlp" until 2 November 2026 (refactor stage 3, S0b: the same set, declared). An
    #: entry is an attribute name or, for a field moved into the state objects, its path ("sv.nlp_prev"; S2, S3; both
    #: lists). Every instance attribute named _nlp* must be listed here (test_nlp_state_lists_every_nlp_attribute)
    NLP_STATE = ("ev.nlp_accept_last", "par.nlp_base_alloc", "par.nlp_cal", "seen.nlp_cal_check", "par.nlp_cal_store",
                 "sv.nlp_cols", "ev.nlp_failed", "res.nlp_fallback_log", "ev.nlp_fb_last", "res.nlp_jump",
                 "ev.nlp_mine_small", "ev.nlp_n_target_cause", "ev.nlp_nip", "res.nlp_nonoptimal", "res.nlp_ok",
                 "res.nlp_path", "sv.nlp_prev", "sv.nlp_prev_f", "res.nlp_rc", "sv.nlp_relax_keep", "res.nlp_relaxed",
                 "res.nlp_status", "_nlp_tol_trace", "ev.nlp_try_n_relax", "sv.nlp_y")


    #: livestock costs from CAPRI's regional total inputs / model heads
    #: (livestock_cost_coef.csv), with revenue on CAPRI's total output (TOOU): with market revenue (MREV), which
    #: leaves out the calves breeders produce, suckler cows would show -1,134% margins.
    #: a warm-started NLP solution more than this much (relative) worse than the last iteration's objective is checked
    #: against the solves from the previous point and the standard start (KNOWN_ISSUES K75)
    nlp_warm_check = setting("supply.nlp_warm_check")
    #: a solution whose levels jump by more than this between outer iterations is checked against the other starts (K79)
    nlp_jump_check = setting("supply.nlp_jump_check")
    #: the relative objective gain another start's solution needs to replace it in that check (K79)
    nlp_jump_gain = setting("supply.nlp_jump_gain")

    #: CAPRI's land market and the grassland allowance (capri_mod/settings: supply.*)
    use_land_market = setting("supply.use_land_market")
    grassland_allowance = setting("supply.grassland_allowance")


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


    #: compute each region's response to the young-animal prices from its solved NLP (K65): None (default) with the
    #: cattle member splits only (CAPRIModel.use_yani_exact); True / False force it
    yani_exact_response = setting("young_animals.use_exact", tri_state)


    # K63: the ammonia options are held at their base shares in a regional NLP solve without a policy incentive on N
    # (no N-surplus row, no mineral cap, no emission tax), and re-solved so where the N-surplus row is slack


    #: CAPRI's CAP 2014-2020 greening in the NLP form (permGrasGreening_, ecoSetAside_, cropDivGreening_), as in
    #: CAPRI's 2030 reference (pol_input/cap_after_2014/ref.gms)
    cap_greening = setting("supply.cap_greening")
    #: annual crops (sets.gms annualCrops) of the model and their crop-diversification groups (cropDivGrps: each
    #: annual crop alone, MAIS = grain and silage maize, OSET = set-aside and fallow)
    CROPDIV_GROUPS = {a: r["cropdiv_group"] for a, r in ACTIVITY_CLASSES.items() if r["cropdiv_group"]}   # N6


    # CAPRI organic_minfert_redu.gms: the small-mineral-N threshold of 0.01 t/ha and the limCres maximum of 1.2 x the
    # baseline's residues are the parameters ORGANIC_SMALL_MINE_KG_HA and ORGANIC_LIMCRES_FACTOR (refactor stage 3, N2)


    #: IPOPT's tolerance for the regional NLP solves: run state, set by CAPRIModel.run every outer iteration from the
    #: setting outer_loop.nlp_tol_final (its value when the module is loaded until then)
    nlp_tol = float(_settings().get("outer_loop.nlp_tol_final"))


    def __init__(self, region_data: RegionData, supply_elasticities: pd.Series,
                 use_share_term: bool = True):
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
        # their output units were unverified then: a pig
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
        self._gross_rev = gross_rev          # the curvature's revenue basis of the activities CAPRI's terms do not cover

        calibrator = PMPCalibrator(self.acts, supply_elasticities, share_terms=st,
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
        cached = getattr(self.par, "base_levels_cache", None)
        if cached is None or cached[0] != key:
            crop_levels   = self.data.base_areas.reindex(CROPS).fillna(0.0)
            animal_levels = self.data.base_animals.reindex(ANIMALS).fillna(0.0)
            cached = (key, pd.concat([crop_levels, animal_levels]).reindex(self.acts).fillna(0.0))
            self.par.base_levels_cache = cached
        return cached[1].copy()

    #: protein-rich feed is priced by the CAKE markets (crushing Stage 3): a cake
    #: price index weighted by CAPRI's EU cake feed use (2017 FAO_agg BAS), at
    #: CAPRI's base world prices. Replaces the soybean-meal PROXY (0.89 x the
    #: soybean price). Values read from the data files on first use.


    #: EU feed use per cereal, CAPRI 2030 reference (FEDM, kt): the weights of
    #: the feed-cereal price change (other cereals include rye and oats)
    FEED_CEREAL_MIX = _InputColumn("feed_cereal_mix_2030.csv", "feed", "fedm_kt")

    def _compute_net_revenues(self, price_shock: Optional[pd.Series] = None):
        """
        Compute per-unit net revenues r_i:
          r_i = price_i × yield_i - variable_cost_i + cap_payment_i  (crops)
          r_i = price_i × yield_i - variable_cost_i                   (animals)
        """
        self.ev.price_shock_now = price_shock
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
        prem = {}
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
            if not np.isfinite(float(cost)):
                # no CAPRI input cost for an activity the region does not have (its level is fixed at 0, as CAPRI keeps
                # an activity without base level out of its model): none. Until 27 October 2026 the per-head animal
                # columns of variable_costs.csv held values of unknown origin here (written by no builder)
                if float(self._base_levels().get(act, 0.0)) > 1e-8:
                    raise ValueError(f"{self.data.region_id} {act}: no CAPRI input cost")
                cost = 0.0
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
            # purchased cereal ration (t/head, livestock_feed_coef.csv) times the
            # change in each cereal's price. Base costs already include feed, so
            # at base nothing changes. Protein feed (oilseed cakes, CAPRI's SOYC,
            # RAPC, SUNC) is priced through the FPRO bulk or, without it, the
            # cake price changes (_protein_feed_cost_change).
            if act in ANIMALS and price_shock is not None and act not in (getattr(self.seen, "feed_rations", None) or {}):
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
                    _fbr = getattr(self.seen, "feed_bulk_ratio", None) or {}
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
                # (no feed coefficient: CAPRI has no herd of the animal in the region at base, so no feed and no
                # feed cost change; the national feed table that stood here as a fallback, feed_requirements.csv, had
                # no builder and was removed on 29 October 2026, KNOWN_ISSUES K99)
            # Crop gross margin (EUR/ha); animal gross margin (EUR/head)
            r[act] = revenue - cost + payment
            prem[act] = payment

        self.net_revenues = pd.Series(r)
        #: the premium part of each net revenue (CAPRI's PRME per ha or head), for income reports (capri_mod/income)
        self.premiums = pd.Series(prem, dtype=float)

    # ------------------------------------------------------------------
    # Constraint matrix
    # ------------------------------------------------------------------


    #: CAPRI's organic crops (organicCrops, pol_input/greendeal/load_organic_targets.gms l. 201-233) and the target of
    #: each (p_organicAreaTargetCrops: its NGRP group's, arable_pp, permanent_pp or uaa_pp; l. 148-165, 187, 240-258,
    #: 269-271): the crops whose own organic target tops up other inputs (organic_io.gms) and, where grouped, lowers
    #: yields (organic_area.gms); grassland, fodder, other oilseeds and the minor crops are not organic crops. The
    #: organic crops whose yield takes the organic yield gap (in an NGRP group and in pact2yieldGap,
    #: inputs/load_organic_yieldgap.gms l. 93-140). Both from capri_data/codes/model_activity_classes.csv (N6; the
    #: organic module's sets are not among the sim_ini sets, so the rows cite the GAMS lines)
    ORGANIC_CROP_TARGET = {a: r["organic_target"] for a, r in ACTIVITY_CLASSES.items() if r["organic_target"]}
    ORGANIC_YIELD_GAP_CROPS = tuple(a for a in CROPS if ACTIVITY_CLASSES[a]["organic_yield_gap"] == "1")
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
    #: is only the fallback for a region without it (the parameter ORGANIC_BASELINE_SHARE, read where used).

    #: Crops occupying PERMANENT land - the same set the land data is built
    #: with in tools/build/build_capri_base.py. Everything else except grass is arable.
    PERMANENT_LAND_CROPS = CROPS_ON_LAND["FRUN"]         # capri_data/codes/model_activity_classes.csv (N6)


    #: CAPRI's assumed average yield loss for a 50% pesticide reduction
    #: (JRC121368, from Sanchez et al. 2019: 18.6% of EU production potentially
    #: affected by 20 pests, worst case 50% loss on that share). CAPRI has NO
    #: dose-response function for plant protection -- unlike fertiliser -- so
    #: this is an explicit assumption in CAPRI too, not a derived quantity (the parameter
    #: PESTICIDE_YIELD_LOSS_AT_50PCT, read where used).

    #: The crops the pesticide yield loss reaches (the jrc121368 rule only; CAPRI star 3.0 calls conventional_io.gms
    #: with the yield shock off): CAPRI's pesticideCrops, every crop activity MCACT but the idled histosols
    #: (pol_input/greendeal/conventional_io.gms l. 51-53). K74 (S11), 29 October 2026: a list of 23 crops without
    #: source before (rice, tobacco, textiles, nurseries, flowers, other crops and industrial crops left out). The loss
    #: acts through the yield of a crop with a producer price; the fodder crops (grass, fodder maize, other fodder,
    #: CAPRI's shift of their output coefficients) and set-aside are not reached (REGISTERED: their yields enter the
    #: fodder balances from CAPRI's data, not from the yields this rule moves)
    PESTICIDE_AFFECTED = tuple(c for c in CROPS if ACTIVITY_CLASSES[c]["pesticide"] == "1")   # classes table (N6)

    #: Share of total input cost that is fertiliser (CAPRI FERT, EU-wide, all 27 member states' 2017 data;
    #: tools/build/build_crop_cost_shares.py): FALLBACK for the fertiliser cost per ha of a crop CAPRI does not grow
    #: in the region (the regional rows of plant_protection_cost.csv serve the others).
    FERT_COST_SHARE = _InputColumn("crop_cost_shares.csv", "supply", "fert_cost_share")


    # kg N excreted per kg nitrate fed (CAPRI line_nitr.gms: +0.42% of DM intake at 1.5%): the parameter NITR_N_EXCR,
    # read where used


    #: free land types of CAPRI's land market (artificial land held fixed)
    LAND_TYPES = tuple(LAND_MARKET_TYPES)                # capri_data/codes/model_land_types.csv (N6)

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


    #: activities without a level at the calibration point held at zero by a bound row, as CAPRI (no v_actLevl without
    #: p_technFact). OFF: tried 22 October 2026, it made the NLP form fail or relax mineral caps in Greek and Bulgarian
    #: regions under Farm-to-Fork (fixed columns at zero degenerate the fertiliser block); absent_output_cleared instead
    absent_activities_fixed = setting("supply.absent_activities_fixed")
    # K64: the solver's residue on activities without a base level (|level| <= 1e-4, 0.1 ha or head) is reported as
    # zero, so no output arises where CAPRI has no variable (Norway's 6e-6 kt of tobacco had kept the market from
    # converging); CAPRI's bounds on endogenous activity levels, 0.1 to 10 x the simulation's data level
    # (set_supply_bounds.gms), always apply


    # CAPRI's low/high-intensity fattening bulls and heifers (Sprint 7c, tools/build/build_cattle_intensity.py)

    #: CAPRI's cattle activities inside the model's animals (tools/build/build_cattle_intensity.py SPLITS): key -> (the CAPRI
    #: activity that gains the stalls z, the one that gives them up); splits of one animal giving up the same activity
    #: share its curvature (cross term) and its bound
    CATTLE_SPLIT_MEMBERS = dict(CATTLE_SPLITS)          # capri_data/codes/model_cattle_splits.csv (N6)
    #: the splits that give CAPRI's replacement heifers and calves their own levels, with the young-animal markets per
    #: sex (22 October 2026). OFF by default: with them the Farm-to-Fork 2030 run's young-animal markets did not converge
    #: (KNOWN_ISSUES K65; runs r89-r92). False keeps only the intensity pairs (Sprint 7c), the pooled young-animal
    #: markets and the animals' herd terms of that grouping - the validated state of runs r86 / r87
    use_cattle_member_splits = setting("supply.use_cattle_member_splits")


    # CAPRI's cattle genomics (envind/breeding.gms): higher milk yield (dairy cows) and lower energy need
    # (non-dairy ruminants), adopted inside the supply model (docs/MITIGATION_IN_SUPPLY.md)
    # the animal options' PMP slope net of CAPRI's cost-saving drop between its ini and max calibration runs
    # (breeding.gms l. 447-458; K67 F2)


    #: the model's two classes of CAPRI's histosol options and the land row each acts on: the histosol data's column
    #: suffix (pmp_sqr_crop, share_grass, ...) and the model's own constraint row label, both internal names of the
    #: model, so kept in the code (refactor stage 3, N6)
    HISTOSOL_CLASSES = (("crop", "arable_land"), ("grass", "grassland"))


    def _build_constraints(
        self,
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
        self.ev.fall_floor = 0.0          # CAPRI data(ru,"FALL","FLOOR"), set by the landscape rule below
        # one label per row, appended with it, so a shadow price is always
        # reported under the constraint it belongs to
        self.ev.row_labels = []

        # 1. Arable land constraint
        #
        # Every activity that occupies ARABLE land must be in this row, including
        # fodder on arable land (MAIF, OFAR, ROOF) and fallow / set-aside (VSET, FALL). All
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
                        if a not in CROPS_ON_LAND["GRAS"] + self.PERMANENT_LAND_CROPS]
        for a in arable_crops:
            if a in acts_idx:
                row_arable[acts_idx[a]] = 1.0
        A_rows.append(row_arable)
        self.ev.row_labels.append("arable_land")
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
        # the set-aside activities of CAPRI's e_setaLandscape (setaFallow: VSET and FALL; ISET, GSET, TSET have no
        # area in CAPRI's 2017 and 2030 data); one activity, SETA = VSET + FALL, until S2 (7 November 2026)
        _seta_acts = [a for a in ("VSET", "FALL") if a in acts_idx]
        if set_aside_requirement and set_aside_requirement > 0 and _seta_acts:
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
                _seta0 = sum(float(self._base_levels().get(a, 0.0)) for a in _seta_acts)   # CAPRI's SETF
                floor = (set_aside_requirement / 0.10) * (_pp / 100.0) * uaa_total + _seta0
            else:
                floor = set_aside_requirement * uaa_total
            self.ev.fall_floor = float(floor)
            row_seta = np.zeros(n)
            for a in _seta_acts:
                row_seta[acts_idx[a]] = -1.0
            A_rows.append(row_seta)
            self.ev.row_labels.append("landscape_floor")
            b_rows.append(-floor)

        # 2. Permanent crops land constraint
        row_perm = np.zeros(n)
        perm_crops = list(self.PERMANENT_LAND_CROPS)
        for a in perm_crops:
            if a in acts_idx:
                row_perm[acts_idx[a]] = 1.0
        A_rows.append(row_perm)
        self.ev.row_labels.append("permanent_land")
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
        # GRAE + GRAI, the model's own activities since S2, 7 November 2026) equals the grassland area. Maize and other fodder are ARABLE crops (CAPRI MAIF, OFAR, ROOF) and
        # are already in the arable row. (The model's earlier row - fodder on grassland plus a fifth of arable land -
        # fixed arable fodder at its base area plus a fifth of any arable change: regions under the N target could not
        # replace fertilised fodder leys.)
        grass_acts = list(CROPS_ON_LAND["GRAS"])
        for a in grass_acts:
            if a in acts_idx:
                row_grass[acts_idx[a]] = 1.0
        A_rows.append(row_grass)
        self.ev.row_labels.append("grassland")
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

        # (4. the legacy nitrate-limit row on total applied N, not CAPRI's, was retired on 27 October 2026, K33: nitrogen
        # limits are CAPRI's N-balance target)

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
        for row, _lam, rhs, lab in fodder_rows:
            A_rows.append(row)
            self.ev.row_labels.append(lab)
            b_rows.append(rhs)
            # CAPRI's SUPBAL_ for non-tradable fodder is an EQUALITY (production net of losses = use): the NLP form
            # builds it with the feed columns (capri_regional_nlp). The conic form's other side, a "_band" row with the
            # previous solve's fodder per head, was dropped from the NLP form on 26 October 2026 (K75) and is no longer
            # built (27 October 2026: the same solution to the last digit in six regions, baseline and Farm-to-Fork)
        # (The roughage "buy-in" rows that stood in where the fodder balance had no data - headroom 1.5 x the base
        # shortfall plus 0.1 x on-farm supply - were removed 23 October 2026: every region with herds has CAPRI's fodder
        # balance; one without it stops the run.)
        if not fodder_rows and any(float(self._base_levels().get(a_, 0.0)) > 1e-8 for a_ in ANIMALS
                                   if a_ in acts_idx and a_ not in FIXED_ACTIVITIES):
            raise ValueError(f"{self.data.region_id}: herds without CAPRI's fodder balance (fodder_balance_<base year>.csv)")

        # Gross nitrogen balance (JRC121368's binding GNB restriction): surplus per
        # ha of farmland <= the tiered target, i.e.
        #   sum_a (s_a - target * [a is a crop]) * x_a <= 0
        # with s_a each activity's own contribution to the balance.
        srow = getattr(self.ev, "surplus_row", None)
        if srow is not None:
            coefs, target = srow[0], srow[1]
            nmin = srow[2] if len(srow) > 2 else {}
            upt = srow[3] if len(srow) > 3 else {}
            ybase = srow[4] if len(srow) > 4 else None
            mint = getattr(self.ev, "n_intensity", {}) or {}
            ycur = self.data.yields
            row_B = np.zeros(n)
            self.ev.mineral_row = {}
            _env_now = getattr(self.seen, "env_for_surplus", None)
            for i, a in enumerate(self.acts):
                sa = float(coefs.get(a, 0.0))
                if not self._techs_inside():
                    sa -= float((getattr(self.ev, "animal_n_relief", None) or {}).get(a, 0.0))   # manure technologies
                sa -= float((getattr(self.ev, "manure_ni_relief", None) or {}).get(a, 0.0))      # inhibitors on manure
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
                        self.ev.mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
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
                    self.ev.mineral_row[a] = self._crop_mineral_rate(a) * float(mint.get(a, 1.0)) * _r
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
            self.ev.row_labels.append("N_balance")
            # (a row "manure_application", manure N <= 170 kg N/ha x crop land, stood here until 29 October 2026:
            # capri-mod's, not CAPRI's - CAPRI's default runs tie manure to land through the crop nutrient balance
            # NUTNED_, fertDistExcr_ and ManureNPK_ with manure trade, which the NLP form ports, and apply the Nitrates
            # Directive's cap only in NDman, off in its Green Deal runs; KNOWN_ISSUES K105)

        # CAPRI's mineral fertiliser reduction (Green Deal mineRedu; pol_input/greendeal/minfert_redu_*.gms):
        #   "20"    e_synNMax: mineral N per ha of current land <= baseline mineral N per ha x (1 - r)
        #   "NNcrp" nMax_ with the "f2f" regulation of the inner fertiliser model: mineral N to each crop group per
        #           ha <= cap_g (baseline x (1 - r), CAPRI's exemptions). The inner model can move manure and crop
        #           residues between groups, so the binding condition on the regional model is the sum over the groups:
        #           mineral N to the capped groups <= sum_g cap_g x area_g.
        # As a row: sum_a (capped share_a x m_a - kappa_a) x_a + m_animals x_animals <= catch-crop N, m_a the
        # activity's mineral N from the environmental module's own balance (linear in activity levels, at this
        # solve's yields and fertiliser factors, as the N_balance row), kappa_a = sum_g share_ag x cap_g (kg/ha).
        mcap = getattr(self.ev, "mineral_cap", None)
        _env_m = getattr(self.seen, "env_for_surplus", None)
        if mcap is not None and _env_m is not None:
            mint = getattr(self.ev, "n_intensity", {}) or {}
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
            self.ev.row_labels.append("mineral_N")

        # CAPRI winterCover_: the catch crops need land not already under winter cover,
        #   sum_c crop_c x winter cover share_c <= UAAR - CATC + FALL.FLOOR  (UAAR: the region's data, fixed)
        # CAPRI adds the landscape rule's fallow floor (supply_model.gms l. 1987: "in case fallow land is
        # expanded only to meet the set aside target, take out from the calculation, otherwise we can
        # easily end up with negative values and infeasibilities"). Without it, where the floor fills
        # most of the arable land (Tyrol, Bolzano: floor 22 kha on 14 kha of arable land) the floor and
        # the catch-crop minimum could not both hold: the land-market solve failed and the fallback
        # emptied the region's grassland and herds.
        _cv = getattr(self.ev, "cover", None)
        wcs_ = getattr(self.data, "winter_cover_share", None)
        if _cv and _cv.get("delta", 0.0) > 0 and wcs_ is not None:
            row_W = np.array([float(wcs_.at[a, "share"]) if a in wcs_.index else 0.0 for a in self.acts])
            if row_W.any():
                A_rows.append(row_W)
                b_rows.append(_cv["uaa"] - _cv["req"] + float(getattr(self.ev, "fall_floor", 0.0) or 0.0)
                              + 1e-9 * max(1.0, _cv["uaa"]))
                self.ev.row_labels.append("winter_cover")

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
                    self.ev.row_labels.append(f"fixed_{a}_{'up' if sg > 0 else 'lo'}")

        # CAPRI's bounds on the endogenous activities (supply/set_supply_bounds.gms, applied in every simulation by
        # prep_sim.gms): LO = max(0.1 x level, 1e-8), UP = max(10 x level, level + 100), level = the data level of the
        # simulation (here the region's base). Without them an activity could leave its calibration range entirely
        # (K27: Dutch fattening sheep 10 -> 2,923 thousand head, dairy cows to 0 under Farm-to-Fork). CAPRI's own
        # exemption: voluntary set-aside (VSET 1e-6 .. 1e5, set_supply_bounds.gms l. 42-43; FALL takes the rule, as in
        # CAPRI; until S2, 7 November 2026, the model's SETA = VSET + FALL was exempt). The additive 100 is in CAPRI's units: 1000 ha
        # (crops, as the model) or 1000 head of CAPRI's activity (LEVL), converted to the model's herd units by
        # CAPRI's LEVL per model head in 2017 (capri_level_ratio.csv: poultry in thousand head against CAPRI's million,
        # fattening sheep, bulls and heifers counted as census stock against CAPRI's activity level).
        _lr = getattr(self.data, "capri_level_ratio", None)
        for i, a in enumerate(self.acts):
            if (a in FIXED_ACTIVITIES or (a in _unc and float(_x0f.get(a, 0.0)) > 1e-8) or a == "VSET"
                    or (a not in CROPS and a not in ANIMALS)):
                continue
            v = float(_x0f.get(a, 0.0))
            if not v > float(_settings().get("supply.absent_level")):
                # CAPRI has no variable for an activity without a level at the calibration point (v_actLevl exists
                # only where p_technFact(..,"LEVL",..) is set, i.e. where the data have a level): held at zero
                # (K64: Norway's regions produced 6e-6 kt of tobacco from the solver's interior, which no trade
                # flow could take, and the market's residual stalled at 3e-6)
                if getattr(type(self), "absent_activities_fixed", False):
                    row_u = np.zeros(n); row_u[i] = 1.0
                    A_rows.append(row_u); b_rows.append(0.0); self.ev.row_labels.append(f"bound_{a}_absent")
                continue
            k_ = (float(_lr[a]) if a in ANIMALS and _lr is not None and a in _lr.index and pd.notna(_lr[a])
                  and float(_lr[a]) > 0 else 1.0)
            add = 100.0 * k_
            hi, lo = max(10.0 * v, v + add), max(0.1 * v, 1e-8)
            row_u = np.zeros(n); row_u[i] = 1.0
            A_rows.append(row_u); b_rows.append(hi); self.ev.row_labels.append(f"bound_{a}_up")
            row_l = np.zeros(n); row_l[i] = -1.0
            A_rows.append(row_l); b_rows.append(-lo); self.ev.row_labels.append(f"bound_{a}_lo")

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
        self.balance_shortfall = 0.0
        self.ev.surplus_row = surplus_row         # held for THIS solve only
        self.ev.mineral_cap = mineral_cap         # CAPRI's mineral fertiliser reduction, THIS solve only
        self.res.last_manure_trade = (0.0, 0.0)
        self.res.last_manure_trade_pk = {}
        self.res.last_mineral_n = None
        self.ev.nbal_price = float(n_balance_price or 0.0)
        self.ev.n_intensity = {}
        self.ev.organic_conv = {}
        self.ev.organic_group_target = {}
        self.res.land_solution = None              # set by this solve when the land market is used
        self.res.n_target_relaxed = False
        self.res.last_cattle_z = {}
        self.ev.nlp_failed = None
        self.res.nlp_status = None
        self.res.nlp_nonoptimal = None             # IPOPT's last point kept on the last attempt (as CAPRI), THIS solve only
        # the price shock the split and genetics columns value their products at: set by THIS solve's net revenues
        # (_compute_net_revenues, called only with a shock); a plain solve after a shocked one kept the old shock there
        self.ev.price_shock_now = None
        self.ev.yield_price_factor = {}           # the price response's yield factor per crop, THIS solve only
        try:
            res = self._solve_once(*args, **kwargs)
        finally:
            self.ev.surplus_row = None
            self.ev.mineral_cap = None
            self.ev.nbal_price = 0.0
        res.n_intensity = dict(getattr(self.ev, "n_intensity", {}) or {})
        res.yield_price_factor = dict(getattr(self.ev, "yield_price_factor", {}) or {})
        self.ev.yield_price_factor = {}
        res.organic_conv = dict(getattr(self.ev, "organic_conv", {}) or {})   # conventional share per crop (accounts: organic area)
        res.fert_tech_shares = dict(getattr(self.res, "fert_tech_shares", {}) or {})   # before the reset below
        # IPOPT's last point kept on the last attempt (non-optimal, as CAPRI; _nlp_last_point): IPOPT's status, else None
        res.nlp_nonoptimal = getattr(self.res, "nlp_nonoptimal", None)
        # CAPRI's crop-group allocation as the regional model solved it (inner model at its totals, or the coupled NLP)
        res.fert_dist_model = getattr(self.res, "fd_model", None)
        try:
            _bl = self._base_levels()
            res.fert_dist_mode_crops = {a: float(_bl.get(a, 0.0)) for a in CROPS if float(_bl.get(a, 0.0)) > 0}
        except Exception:
            res.fert_dist_mode_crops = None
        self.ev.n_intensity = {}
        self.res.fert_tech_shares = {}
        res.balance_shortfall = float(getattr(self, "balance_shortfall", 0.0))
        self.balance_shortfall = 0.0
        return res

    def _solve_once(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        set_aside_requirement: float = 0.0,
    ) -> SupplyResult:
        """
        Solve the regional NLP and return a SupplyResult.

        Parameters
        ----------
        price_shock : relative price changes {activity: fraction}, e.g. {"SWHE": 0.10}
        policy_shock: CAP payment changes {"BPS": EUR/ha, "COUPLED": ...}
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

        self.ev.yields_solve0 = _backup.get("yields")    # the calibrated yields (the 2030 reference), THIS solve only
        self.ev.greendeal_inputs = {}                     # set by _apply_greendeal_input_changes for THIS solve
        try:
            return self._solve_inner(price_shock, policy_shock, set_aside_requirement)
        finally:
            self.ev.yields_solve0 = None
            self.net_revenues = _net_rev_backup
            for _f, _v in _backup.items():
                setattr(self.data, _f, _v)


    def _solve_inner(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        set_aside_requirement: float = 0.0,
    ) -> SupplyResult:
        self.ev.cover = None              # catch-crop requirement: set by the pesticide/organic targets
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
        self.ev.greendeal_crop_delta = {}
        # CAPRI's Green Deal group (set_fert_priors.gms, %scenarioGroup%==greendeal): the fertiliser priors' partial
        # derivative has a slack in the listed regions
        self.ev.fert_partial_slack = bool(isinstance(policy_shock, dict) and policy_shock.get("greendeal_group"))
        # CAPRI's obligatory set-aside rates of this region's arable activities (percent; SETA_, land.py)
        self.ev.set_aside_rates = dict(((policy_shock.get("set_aside_rates") or {}) if isinstance(policy_shock, dict)
                                        else {}).get(self.data.region_id) or {})
        if self.ev.set_aside_rates and (getattr(self.data, "land_market", None) or {}).get("quad") is None:
            import warnings as _w
            _w.warn(f"{self.data.region_id}: obligatory set-aside rates given, but the region has no land market "
                    f"(CAPRI's arable land balance): not applied")
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

        self.ev.manure_ni_relief, self.ev.manure_ni_nh3 = {}, {}
        if getattr(self.ev, "nbal_price", 0.0):
            self._apply_balance_price(self.ev.nbal_price)
        else:
            # no N price: ammonia technologies at their base shares (resets any relief left
            # from an earlier solve; records the shares for reporting)
            self._apply_manure_techs(0.0)
            # inhibitors on manure under CAPRI's emission tax (Sprint 9m; without a tax they stay at zero)
            self._apply_manure_inhibitor(0.0)

        A_ub, b_ub, _, _ = self._build_constraints(
            set_aside_requirement=set_aside_requirement)

        # The regional model in CAPRI's form, solved by IPOPT (_nlp_solve). Where a solve fails, CAPRI re-solves with
        # widened bounds and then carries on with the non-optimal solution, recorded (supply/simu_supply.gms,
        # widen_bounds.gms: p_INFES): here JRC121368's relaxed N target is tried, then IPOPT's last point at the region's
        # own problem is kept and recorded (_nlp_last_point); the landscape floor is kept as CAPRI keeps it (K84)
        c_lin = self.f - self.net_revenues.values
        aug = self._land_augment(A_ub, b_ub, c_lin, x0) if getattr(self, "use_land_market", False) else None
        if aug is not None:
            # CAPRI LAND MARKET: land-type areas as variables (see _land_augment)
            Qa, ca, Aa, ba, ya0, rows = aug
            self.ev.last_duals = None
            # JRC121368 sect. 4.3.4: where the tiered N target is infeasible the region's cut is the EU average
            # (36%) - a setting of the scenario for that region, so once found in this scenario (same target)
            # the region starts from it instead of failing the tiered target again at every iteration
            _yc = None
            _rk = self._n_relax_key()
            if _rk is not None and getattr(self.sv, "n_relax_sticky", None) == _rk:
                y_f, ok_f, Aa_r, ba_r = self._relax_n_target(Qa, ca, Aa, ba, ya0)
                if ok_f and getattr(self.ev, "nlp_failed", None) is None:
                    _yc, Aa, ba = y_f, Aa_r, ba_r
            if _yc is None:
                # where CAPRI's form fails at the tiered N target, JRC121368's rule for regions whose target
                # "generated infeasibilities in the model" (the EU-average cut, 36%) is tried
                self.ev.nlp_try_n_relax = _rk is not None
                try:
                    _yc = self._nlp_solve(Qa, ca, Aa, ba, ya0)
                finally:
                    self.ev.nlp_try_n_relax = False
                if _yc is None and getattr(self.ev, "nlp_fb_last", False) == "n_target":
                    _st0 = getattr(self.ev, "nlp_failed", None) or "NLP build failed"
                    _cause = bool(_st.pop(self.ev, "nlp_n_target_cause", False))
                    y_f, ok_f, Aa_r, ba_r = self._relax_n_target(Qa, ca, Aa, ba, ya0)
                    if getattr(self.res, "nlp_fallback_log", None) is None:
                        self.res.nlp_fallback_log = []
                    if ok_f:
                        _yc, Aa, ba = y_f, Aa_r, ba_r
                        self.res.nlp_fallback_log.append(f"{_st0} at the tiered N target -> CAPRI's form at "
                                                      f"JRC121368's relaxed target (36%)"
                                                      + (" (feasible without the target: no cap exempted first, K89)"
                                                         if _cause else ""))
                    else:
                        self.res.n_target_relaxed = False
                        self.sv.n_relax_sticky = None
                        self.balance_shortfall = 0.0
            if _yc is None:
                # CAPRI keeps the landscape floor (e_setaLandscape) and every other row as they are and carries on with
                # the solver's last point (K84: until 27 October 2026 an unreachable floor was lowered here)
                self._note_floor_failure()
                _yc = self._nlp_last_point(Qa, ca, Aa, ba, ya0)
            y = _yc
            n_ = len(x0); x_qp = y[:n_]
            _nl = len(getattr(self.ev, "land_types_used", []))
            self.res.last_mineral_n = float(y[n_ + _nl]) if getattr(self.ev, "alloc_cols", 0) else None
            _pc = getattr(self.ev, "pool_cols", []) or []
            self.res.last_manure_trade = (float(y[_pc[0]]), float(y[_pc[1]])) if len(_pc) == 2 else (0.0, 0.0)
            self.res.last_manure_trade_pk = {nut_: (float(y[c_[0]]), float(y[c_[1]]))
                                          for nut_, c_ in (getattr(self.ev, "pool_cols_pk", None) or {}).items()
                                          if len(c_) == 2 and max(c_) < len(y)}
            self.res.last_aug = (Qa, ca, Aa, ba, y)
            self._split_record(y)
            self._mix_record(y)
            if self._split_pending():
                self._dairy_calibrate_from_duals(getattr(self.ev, "last_duals", None))
            self.res.last_hist_fallow = {c_: float(y[j_]) for c_, j_ in (getattr(self.ev, "hist_cols", None) or {}).items() if j_ < len(y)}
            if getattr(self.par, "hist_pending", None):
                self._histosol_calibrate_from_duals(getattr(self.ev, "last_duals", None))
            # land rows' limits at the solved land areas, so the shadow
            # prices computed below see the right slack
            b_ub = b_ub.copy()
            for i, coeffs, const in rows:
                b_ub[i] = const + sum(cf * float(y[n_ + k]) for k, cf in coeffs)
            self.res.land_solution = dict(zip(self.ev.land_types_used, y[n_:].tolist()))
        else:
            self.ev.last_duals = None
            self.res.last_dairy_z = 0.0
            self.res.last_cattle_z = {}
            self.res.last_genet_z = {}
            self.res.last_mix_z = {}
            # CAPRI's dairy splits on the plain path too (regions without land-market data: Ireland, Berlin, Hamburg,
            # ...; the grassland split was a column too until S2, 7 November 2026)
            _n0 = len(x0)
            self.ev.need_row = None
            self.ev.alloc_cols = 0
            _lab = list(getattr(self.ev, "row_labels", []))
            Qg, cg, Ag, bg, sg = self._dairy_intensity_column(
                self.Q, c_lin, A_ub, b_ub, np.asarray(x0, float), _lab, _n0)
            Qg, cg, Ag, bg, sg = self._histosol_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
            Qg, cg, Ag, bg, sg = self._mix_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
            self.ev.aug_labels = _lab
            self.res.last_hist_fallow = {}
            _yc = None
            _cols = (getattr(self.ev, "dairy_col", None) is not None
                     or getattr(self.ev, "cattle_cols", None) or getattr(self.ev, "hist_cols", None)
                     or getattr(self.ev, "mix_cols", None))
            if _cols:
                _yg = self._nlp_solve(Qg, cg, Ag, bg, sg)
                if _yg is None:
                    # as on the land-market path: the floor kept, the solver's last point (K84)
                    self._note_floor_failure()
                    _yg = self._nlp_last_point(Qg, cg, Ag, bg, sg)
                self._split_record(_yg)
                self._mix_record(_yg)
                _yc = _yg[:_n0]
                if self._split_pending():
                    self._dairy_calibrate_from_duals(getattr(self.ev, "last_duals", None))
                self.res.last_hist_fallow = {c_: float(_yg[j_]) for c_, j_ in (getattr(self.ev, "hist_cols", None) or {}).items()}
                if getattr(self.par, "hist_pending", None):
                    self._histosol_calibrate_from_duals(getattr(self.ev, "last_duals", None))
            else:
                self.ev.dairy_req_extra = None
                _yc = self._nlp_solve(self.Q, c_lin, A_ub, b_ub, x0)
                if _yc is None:
                    self._note_floor_failure()
                    _yc = self._nlp_last_point(self.Q, c_lin, A_ub, b_ub, x0)
                if self._split_pending():
                    self._dairy_calibrate_from_duals(getattr(self.ev, "last_duals", None))
                if getattr(self.par, "hist_pending", None):
                    self._histosol_calibrate_from_duals(getattr(self.ev, "last_duals", None))
            x_qp = _yc
            # record the plain problem as the land-market path records its own (res.last_aug)
            self.res.last_plain = (self.Q, c_lin.copy(), A_ub.copy(), b_ub.copy(), x_qp.copy())

        x_opt = np.maximum(x_qp, 0.0)
        solver_converged = getattr(self.res, "nlp_nonoptimal", None) is None
        solver_message = f"NLP (CAPRI's form, IPOPT): {getattr(self.res, 'nlp_status', None)}"

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
        # CAPRI's technologies (S1): z ha moved from T2 to T1 add yield_diff x yield each (T1 = X/2 + z at
        # yield (1 + d/2), T2 = X/2 - z at (1 - d/2))
        _tm = getattr(self.data, "techn_mix", None)
        for _a, _z in (getattr(self.res, "last_mix_z", None) or {}).items():
            gross_output[_a] = float(gross_output[_a]) + float(_tm.at[_a, "yield_diff"]) * float(yields[_a]) * _z

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
            # The output coefficient is per head at base intensity; the dairy split below moves milk with the
            # low-yield cows (a scaling by a dairy yield base, never set since 3a264a2, removed in refactor stage 3)
            # no output coefficient: unknown (NaN) where the activity has a level, none where it has none (other
            # animals, OANI, held at 0 in every region, read NaN until 27 October 2026)
            _lv = float(activities.get(_a, 0.0))
            gross_output[_a] = (_lv * _c if _c is not None else (float("nan") if abs(_lv) > 1e-12 else 0.0))
            # CAPRI's dairy split (Sprint 7b): z heads at DCOL instead of DCOH change milk by
            # (COMI_DCOL - COMI_DCOH) / COMI_DCOW per head (cull-cow beef, ~1% of the tonnage, is
            # the same for both and is scaled with it: REGISTERED)
            if _c is not None and _a == "DCOW":
                _dz = float(getattr(self.res, "last_dairy_z", 0.0) or 0.0)
                _di = getattr(self.data, "dairy_intensity", None)
                if _dz and _di is not None:
                    gross_output[_a] += _dz * _c * float(_di["dcomi_rel"])
            # the cattle splits (bulls and heifers, Sprint 7c; replacement heifers and calves): beef per stall,
            # a - b, over the animal's average, for every split of the animal
            for _k, _cz_ in (getattr(self.res, "last_cattle_z", None) or {}).items():
                if _k.split(":")[0] != _a:
                    continue
                _ct_ = (getattr(self.data, "cattle_intensity", None) or {}).get(_k)
                if _c is not None and _cz_ and _ct_ is not None:
                    gross_output[_a] += float(_cz_) * _c * float(_ct_["dbeef_rel"])
            # cattle genomics (breeding.gms genet_yld): g cows adopting give d_milk_rel more milk each
            for (_ga, _go), _gz in (getattr(self.res, "last_genet_z", None) or {}).items():
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
        # the technologies' net revenue difference on the area moved to T1 (S1; the linear term is minus it)
        gm += sum(float(getattr(self.ev, "mix_dnr", {}).get(_a, 0.0)) * _z
                  for _a, _z in (getattr(self.res, "last_mix_z", None) or {}).items())

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
        _zc = getattr(self.ev, "last_duals", None)
        if _zc is not None:
            mu = np.zeros(len(b_ub)); k_ = min(len(b_ub), len(_zc))
            mu[:k_] = np.maximum(np.asarray(_zc[:k_], float), 0.0)
        labels = getattr(self.ev, "row_labels", [])
        for i, label in enumerate(labels):
            if i < len(mu) and label != "feed":
                shadow[label] = shadow.get(label, 0.0) + float(mu[i])

        # Nutrient balance
        nutr = {}
        for nut in NUTRIENTS:
            coefs = self.data.nutrient_coefs.reindex(self.acts)[nut].fillna(0.0)
            nutr[nut] = float((coefs * activities).sum())
        nutrient_balance = pd.Series(nutr)
        _sv = getattr(self.ev, "seta_obl_vec", None)
        _iset = (float(np.asarray(_sv, float) @ activities.reindex(self.acts[:len(_sv)]).fillna(0.0).values)
                 if _sv is not None else 0.0)

        return SupplyResult(
            region_id=self.rid,
            activities=activities,
            gross_output=gross_output,
            gross_margin=gm,
            shadow_prices=shadow,
            nutrient_balance=nutrient_balance,
            converged=solver_converged,
            solver_message=solver_message,
            iset=_iset,
        )


# ---------------------------------------------------------------------------
# SUPPLY MODULE COORDINATOR
# ---------------------------------------------------------------------------

def _region_nutrients(d: dict, region: str) -> pd.DataFrame:
    """CAPRI's fertiliser coefficients of the region's crops (NITF, PHOF, POTF; nutrient_coefs_regional.csv), crops
    CAPRI has nowhere in the member state left out (no fertiliser). Until 29 October 2026 a national table without
    builder (nutrient_coefs.csv) under them, which OFOD (OFAR and ROOF since S2), SETA (VSET and FALL since S2) and WINE kept in every region (KNOWN_ISSUES K100)."""
    reg = d["nutrients_regional"]
    if region not in reg.index.get_level_values(0):
        return pd.DataFrame(columns=["N", "P2O5", "K2O"], dtype=float)
    return reg.loc[region].astype(float).copy()


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


def _ms_code(region: str) -> str:
    """The region's country as the per-country tables key it (NUTS-0: BE, LU, IE, EL; definitions.country_of). The
    alias table that stood here ({"GR": "EL", "UK": "UK"}) reached no region: country_of gives EL for Greece, and UK
    mapped to itself (refactor stage 3, N6)."""
    from capri_mod.data.definitions import country_of
    return country_of(region)


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


class SupplyModule(ModuleStateMixin):
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
    #: 22 October 2026, the project lead's decision); at 2017 CAPRI's recipe at CAPRI's 2017 point. "elasticity"
    #: (calibrated per activity from CAPRI's supply elasticities) was removed on 28 October 2026 (audit S13).
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
    #: the EU average cut, 36%, because the tiered target was infeasible there (the parameters JRC_CAPPED_N_REGIONS,
    #: JRC_CAPPED_CUT, read where used).

    def _jrc_capped_regions(self, cs) -> set:
        """The nine regions with the highest CAPRI baseline N surplus per ha."""
        got = getattr(self.par, "jrc_capped_cache", None)
        if got is None:
            try:
                col = cs["surplus_kg_n_per_ha"].dropna()
                got = set(col.sort_values(ascending=False).index[: int(param("JRC_CAPPED_N_REGIONS"))])
            except Exception:
                got = set()
            # sensitivity only (tools/run/run_f2f_2030.py --capped-regions): the report does not
            # name the nine regions; '+A,B' adds to them, 'A,B' replaces them
            ov = str(getattr(self, "jrc_capped_override", "") or "")
            if ov:
                extra = {x.strip() for x in ov.lstrip("+").split(",") if x.strip()}
                got = (got | extra) if ov.startswith("+") else extra
            self.par.jrc_capped_cache = got
        return got
    def __init__(self, data: dict, supply_elasticities: Optional[pd.Series] = None,
                 inputs: Optional["_inputs.SupplyInputs"] = None):
        """CAPRI's regional elasticity estimates, with provenance tracking. inputs: the run's data directory and base
        year (capri_mod/supply/inputs.py; the repository's data and 2017 by default), made the supply code's inputs."""
        self.data = data
        self.inputs = _inputs.use(inputs if inputs is not None else _inputs.SupplyInputs())
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
        from capri_mod.supply.capri_pmp import build_elasticity_table
        self.elasticity_provenance = pd.DataFrame()
        self.elasticity_summary: dict = {}
        eps_tab, prov, summary = build_elasticity_table(
            self.inputs.root, self.regions, ALL_ACTIVITIES, self.supply_elasticities,
            base_areas=data.get("areas"), base_year=self.inputs.base_year, inputs=self.inputs)
        self.regional_elasticities = eps_tab
        self.elasticity_provenance = prov
        self.elasticity_summary = summary

        self._models: Dict[str, RegionalSupplyModel] = {}

    def set_mitigation_scope(self, settings) -> None:
        """CAPRI's switches that extend an EU mitigation option to every supply region (capri_mod/policy/endotech.py):
        %fallowInAllRmssup% for histosol fallowing (no_histosols.gms rmssup_histo), %winterCovInAllRmssup% for the
        winter cover (cover_crops.gms)."""
        fal, wc = float(settings["fallowInAllRmssup"]) > 0, float(settings["winterCovInAllRmssup"]) > 0
        for m in self._models.values():
            m.seen.fallow_in_all_rmssup = fal
            m.seen.wintercov_in_all_rmssup = wc

    def set_genetics_effects(self, table: Optional[dict], settings_key: tuple) -> None:
        """Cattle genomics at the run's technology settings (capri_mod/policy/endotech.py). Each regional model
        keeps its genomics calibration (the linear cost terms taken from the base duals) per settings, so a
        scenario compared with the baseline of the same settings uses the calibration of that baseline."""
        self.data["genetics_effects"] = table
        self.par.genetics_key = settings_key
        for region, m in self._models.items():
            store = _st.setdefault(m.par, "genet_cz_store", {})
            old = getattr(m.par, "genet_key", None)
            if old == settings_key:
                continue
            if old is not None:
                store[old] = getattr(m.par, "genet_cz", None)
                # the NLP form's calibration (CAPRI's: the base a first-order point of the model it is simulated with)
                # belongs to the settings too: the genomics columns differ with them. Kept per settings and restored,
                # so a baseline after a run at other settings uses its own calibration, not the other one (found
                # 20 October 2026: after an ghgTechMYld 0.2 run, IE04's default baseline adopted genet_eff for the
                # whole herd)
                cal_store = _st.setdefault(m.par, "nlp_cal_store", {})
                cal_store[old] = (getattr(m.par, "nlp_cal", None), getattr(m.par, "nlp_base_alloc", None))
                m.par.nlp_cal, m.par.nlp_base_alloc = cal_store.get(settings_key, (None, None))
            m.data.genetics_effects = (table or {}).get(region)
            m.par.genet_cz = store.get(settings_key)
            m.par.genet_pending = None
            m.res.last_genet_z = {}
            m.par.genet_key = settings_key

    def _pmp_terms_for(self, d, region):
        """The region's PMP terms in the model's form for pmp_source and the market year: "capri2030" CAPRI's exported
        2030 terms (2030; at 2017 CAPRI's recipe at CAPRI's 2017 point), "recipe" capri-mod's own with CAPRI's recipe
        (2017 or 2030). The elasticity calibration ("elasticity") was removed on 28 October 2026 (audit S13)."""
        src = str(getattr(self, "pmp_source", "capri2030"))
        if src not in ("capri2030", "recipe"):
            raise ValueError(f"supply.pmp_source {src!r}: 'capri2030' or 'recipe' (the elasticity calibration was "
                             "removed on 28 October 2026, audit S13)")
        yr = _inputs.market_year(d)
        if src == "capri2030" and yr == 2030:
            return self._pmp_capri_parts_of((d.get("pmp_capri_2030") or {}).get(region))
        # CAPRI's own terms exist only for its 2030 calibration (pmppar_21730); at 2017 "capri2030" takes CAPRI's
        # recipe at CAPRI's 2017 point, as "recipe" does (23 October 2026: before, the elasticity calibration, which
        # needed literature elasticities where CAPRI has none - no proxies)
        if src == "recipe" or (src == "capri2030" and yr == int(_inputs.base_year())):
            return self._pmp_capri_parts_of(((d.get("pmp_recipe") or {}).get(yr) or {}).get(region))
        return None

    def _intensity_q_at(self, d, row, cols, part):
        """An intensity split's row with its curvature at the PMP terms' calibration point: at the 2030 market year
        with pmp_source "capri2030" or "recipe" (and `part` among pmp_capri_parts), q_<x> := q_<x>_capri2030 /
        q_<x>_recipe2030 (CAPRI's / the recipe's 2030 p_pmpQuadTechn of the two variants, tools/build/build_intensity_q_2030.py);
        else the base year's terms. The _capri2030 / _recipe2030 entries are removed either way."""
        if row is None:
            return row
        src = str(getattr(self, "pmp_source", "capri2030"))
        yr = _inputs.market_year(d)
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
        """Activities of the region held at their level: those of the parts calibrated with PMP terms (pmp_capri_parts:
        crops, animals) without a positive own term at the calibration point, and those without any CAPRI value (no
        elasticity, no term: OOIL, OIND in every member state). CAPRI calibrates every activity with a level; where
        its calibration has no term for an activity of the model region (its level there zero or negligible: tobacco,
        pulses in the Netherlands, durum wheat at 2030, 71 cells and at most 2% of an activity's EU level, r166), the
        activity is held, as CAPRI holds what it does not calibrate. Until 28 October 2026 those cells took a curvature
        from their CAPRI elasticity (the elasticity calibration, audit S13)."""
        pmp = self._pmp_terms_for(d, region) or {}
        parts = tuple(getattr(self, "pmp_capri_parts", ()))
        anim = set(ANIMALS)
        held = {a for a in ALL_ACTIVITIES
                if (("animals" in parts) if a in anim else ("crops" in parts)) and not float(pmp.get((a, a), 0.0) or 0.0) > 0}
        prov = getattr(self, "elasticity_provenance", None)
        if prov is not None and not prov.empty and region in prov.index:
            held |= {a for a in prov.columns if prov.at[region, a] == "NO_CAPRI_VALUE" and (a, a) not in pmp}
        return frozenset(held)

    def _techn_mix_for(self, d, region):
        """The region's crop technologies (S1) where its crops take CAPRI's 2030 PMP terms (pmp_source "capri2030" at the
        2030 market year, "crops" among pmp_capri_parts): the mix terms are that calibration's; None otherwise."""
        if str(getattr(self, "pmp_source", "capri2030")) != "capri2030" or _inputs.market_year(d) != 2030:
            return None
        if "crops" not in tuple(getattr(self, "pmp_capri_parts", ())):
            return None
        return (d.get("techn_mix") or {}).get(region)

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
            self._models[region] = RegionalSupplyModel(rd, eps, use_share_term=True)
            self._models[region].par.genet_key = getattr(self.par, "genetics_key", None)
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
            organic_yield_gap_regions=d.get("organic_yield_gap_regions"),
            organic_yield_gap_groups=d.get("organic_yield_gap_groups"),
            landscape_target_pp=_ms_value(d.get("landscape_targets_ms"), region,
                                          "landscape_pp"),
            organic_targets_pp=_ms_row(d.get("organic_targets_ms"), region),
            fert_partial_slack=(d.get("fert_partial_slack") or {}).get(region),
            organic_ngrp_class=(dict(zip(d["organic_ngrp_class"].index, d["organic_ngrp_class"].target))
                                if d.get("organic_ngrp_class") is not None else None),
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
                         if _inputs.market_year(d) == 2030
                         and str(getattr(self, "pmp_source", "capri2030")) in ("capri2030", "recipe")
                         and "land" in tuple(getattr(self, "pmp_capri_parts", ()))
                         and (d.get("land_market_2030") or {}).get(region)
                         else (d.get("land_market") or {}).get(region)),
            # CAPRI's land rents at the market year's calibration point (tools/build/build_land_rents.py: 2030 reference,
            # 2017 results)
            land_rents=(((d.get("land_rents") or {}).get(_inputs.market_year(d)) or {}).get(region)),
            # CAPRI's PMP terms of its 2030 baseline calibration (K61): at the 2030 market year, with pmp_source "capri2030"
            pmp_capri=self._pmp_terms_for(d, region),
            techn_mix=self._techn_mix_for(d, region),
            uncalibrated=self._uncalibrated(d, region),
            livestock_feed_coef=(
                d["livestock_feed_coef"].loc[region]
                if d.get("livestock_feed_coef") is not None
                and region in d["livestock_feed_coef"].index else None),
        )


    # CAPRI's exponent in othImpact.NMIN (envind/ghgMiti.gms, p_fertEffCor): the parameter P_FERT_EFF_COR


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
        def load(inp):
            tab = inp.csv("fert_options_jul15.csv", "abatement")
            to8 = IdentityMap()        # the model's regions are CAPRI's units: each its own CAPRI region
            return ({(r.region, str(r.option).upper()): r for r in tab.itertuples(index=False)}, to8)
        tab, to8 = _inputs.current().cached("fert_options_by_option", load)
        msc = capri_ms(region)
        r8 = to8.get(region)
        act_ = active_technologies()
        x = overfert_factor(region)
        xm = (x + param("OVERFERT_MARKUP")) if x is not None else None
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
                q = param("NITR_INH_EMISSION_FACTOR") * q0         # ghgMiti.gms l. 110
            if not k1 > 0 or q is None or not (0 < q < q0):
                continue
            nmin = (q0 / q - 1.0) ** param("P_FERT_EFF_COR")
            s0 = float(rr.IniShare) if rr.IniShare == rr.IniShare else 0.0
            smax = float(rr.MaxShare) if rr.MaxShare == rr.MaxShare else 0.0
            if smax <= 0 and sd:
                nat = tab.get((msc, name))
                smax = float(nat.MaxShare) if nat is not None and nat.MaxShare == nat.MaxShare else 0.0
            if name == "NITR_INH" and xm is not None:             # restMitFert: NI cannot go below need
                if xm <= 1.0:
                    nmin = 0.0
                elif xm < nmin ** (1.0 / param("P_FERT_EFF_COR")) + 1.0:
                    nmin = (xm - 1.0) ** param("P_FERT_EFF_COR")
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
                nmin_pf = (q0 / qp - 1.0) ** param("P_FERT_EFF_COR") if qp else 0.0
                if xm is not None and xm - 1.0 <= nmin_pf and smax < 1.0:
                    rs0 = 0.0
                if slope <= 0:
                    continue
                out.append((name, nmin, rs0 * k1, slope, s0, smax))
            else:
                rs1, rs0 = ((param("MITI_RELSUBS1_ADOPTED"), 0.0) if (smax < 1.0 and name != "NITR_INH")
                            else (param("MITI_RELSUBS1"), param("MITI_RELSUBS0")))
                slope = k1 * (rs1 - rs0) / (smax - s0)
                if getattr(type(self), "fert_slope_with_saving", True):
                    # CAPRI's pmpParSqr (envind/ghgMiti.gms l. 1016-1035, the 'alternative approach'): the FOC is zero
                    # at the initial and the maximum share with the fertiliser saving valued at the member state's
                    # NITF price p: + nmE x p x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0), nmE = NMIN + EmiCalmin
                    pf = self._nitf_price_ms(msc)
                    nme = nmin + self._emi_cal_min(region, r8, name)
                    if pf:
                        slope += saving_slope(nme, pf, s0, smax)
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
        return (abs(v) ** param("P_FERT_EFF_COR")) * (1.0 if v >= 0 else -1.0) if v else 0.0

    def _manure_per_head(self, region, model):
        """Manure N per activity unit of the region's animals ({animal: the environmental module's organic N input
        of one unit}), the coefficients of CAPRI's ManureNPK_ / NUTNED_ terms; None when the region has no animal with
        manure. Until 29 October 2026 this was _manure_limit, which also returned a manure-application limit (170 kg
        N/ha or 1.001 x the base rate) for a row of capri-mod's own, removed (KNOWN_ISSUES K105), and returned None on
        any error, which dropped the manure terms without a word: an error now stops the solve."""
        if not hasattr(self.par, "env_for_surplus"):
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            self.par.env_for_surplus = EnvironmentalModule(self.data)
            self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
        ylds = self.data["yields"].loc[region]
        man = {}
        for a in model.acts:
            if a in CROPS:
                continue
            nb = self.par.env_for_surplus.unit_nitrogen_balance(a, ylds, region)
            v = float(nb.get("n_organic_input", 0.0))
            if v > 0:
                man[a] = v
        return man or None

    #: CAPRI's baseline calibration (Sprint 9p): at most this many correction rounds per baseline run
    BASE_CAL_ROUNDS = setting("projection.base_cal_rounds")
    #: CAPRI sets.gms l. 5606, FODF / OFAR, GRAS, ROOF, MAIF / (OFAR and ROOF the model's own since S2, 7 November 2026)
    FODDER_ACTS = tuple(a for a, r in ACTIVITY_CLASSES.items() if r["fodder"] == "1")   # model_activity_classes.csv (N6;
    # CAPRI's FODCRP: GRAS, MAIF, OFAR, ROOF)

    def calibrate_to_base(self, results: dict, reset: bool = False) -> float:
        """CAPRI's calibration of the supply models to the baseline (CAPMOD calibrates its PMP terms so that the
        baseline year's solution reproduces the projected activity levels): per region, the linear cost terms move by
        Q (x - x_target), the shift that makes the target optimal when the constraints' duals stay put, with the
        target the region's projected levels (the model's base levels). Returns the largest remaining drift, relative
        to the target (activities of at least 1 unit), before this round's correction; 0 once the rounds are used."""
        if reset:
            self.sv.base_cal_round = 0
            self.sv.base_cal_prev = {}
            self.sv.base_cal_stalled = set()
        rnd = int(getattr(self.sv, "base_cal_round", 0) or 0)
        worst = 0.0
        if rnd >= self.BASE_CAL_ROUNDS:
            return 0.0
        prev_r = getattr(self.sv, "base_cal_prev", None) or {}
        stalled = getattr(self.sv, "base_cal_stalled", None) or set()
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
            # A drift above the tolerance after a round that found the region within it is new drift (the prices moved
            # since), not a correction that failed: the region is corrected, not left (K120: in S7's "capri" the
            # baseline's first round finds every region at its target, so the next round's drift, 4% for Dresden's
            # pulses, stalled every region and the baseline stopped uncorrected)
            _tol_cal = float(_settings().get("projection.base_cal_tol"))
            if (rnd > 0 and region in prev_r
                    and w_r > float(_settings().get("projection.base_cal_stall_ratio")) * prev_r[region]
                    and not (prev_r[region] <= _tol_cal < w_r)):
                stalled.add(region)
                continue
            prev_r[region] = w_r
            worst = max(worst, w_r)
            mo.f = np.asarray(mo.f, float) + np.asarray(mo.Q, float) @ d
            mo.par.base_cal_shift = np.asarray(getattr(mo.par, "base_cal_shift", np.zeros(len(acts))), float) \
                + np.asarray(mo.Q, float) @ d
        self.sv.base_cal_round = rnd + 1
        self.sv.base_cal_prev, self.sv.base_cal_stalled = prev_r, stalled
        return worst

    # CAPRI's crop nutrient balance (NUTNED_, fertDistExcr_) and manure market in every EU solve, not only under
    # the N target (Sprint 9k)

    def _manure_context(self, region, model):
        """{"man_d", "nmin", "ybase"} for the regional model's crop-need row, manure trade columns and ammonia options
        (CAPRI has them in every run), or None outside the EU (msNoEU)."""
        if not is_eu(region):
            return None
        cache = _st.setdefault(self.par, "mctx_cache", {})
        ck = (region, bool(getattr(self.seen, "manure_trade_on", True)))
        if ck not in cache:
            man = self._manure_per_head(region, model)
            bc = self._balance_coefs(region, model)
            cache[ck] = None if (man is None or bc is None) else \
                {"man_d": man, "nmin": bc[1], "ybase": self.data["yields"].loc[region]}
        if cache[ck] is None:
            return None
        try:
            _ft = self._fert_techs(region) if float(getattr(self.seen, "ghg_tax", 0.0) or 0.0) > 0 else []   # emission tax
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
            if not hasattr(self.par, "env_for_surplus"):
                self.par.env_for_surplus = EnvironmentalModule(self.data)
                self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
            cache = getattr(self.par, "balance_cache", {})
            ck = (region, bool(getattr(self.seen, "manure_trade_on", True)))    # the base trade counts only with trade on
            if ck in cache:
                return cache[ck]
            ylds = self.data["yields"].loc[region]
            out, nmin, upt = {}, {}, {}
            for a in model.acts:
                nb = self.par.env_for_surplus.unit_nitrogen_balance(a, ylds, region)
                out[a] = float(nb["n_surplus"])
                nmin[a] = float(nb.get("n_mineral_input", 0.0))
                upt[a] = float(nb.get("n_crop_uptake", 0.0))
            ser = (pd.Series(out).reindex(model.acts).fillna(0.0), nmin, upt)
            cache[ck] = ser
            self.par.balance_cache = cache
            return ser
        except Exception:
            return None

    def _surplus_per_ha(self, region, model):
        """Region's base gross N surplus per ha of cropped area, or None."""
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if not hasattr(self.par, "env_for_surplus"):
                self.par.env_for_surplus = EnvironmentalModule(self.data)
                self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
            acts = model._base_levels()
            ylds = self.data["yields"].loc[region]
            nb = self.par.env_for_surplus.compute_nitrogen_balance(acts, ylds, region)
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
        cache = _st.setdefault(self.par, "mcap_cache", {})
        key = (region, kind, r)
        if key in cache:
            return cache[key]
        spec = None
        try:
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            if getattr(self.par, "env_for_surplus", None) is None:
                self.par.env_for_surplus = EnvironmentalModule(self.data)
                self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
            env = self.par.env_for_surplus
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
                inner.set_variant(bool(getattr(self.seen, "manure_trade_on", True)))
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

    #: the EU policy instruments, which do not apply to supply regions outside the EU (definitions.is_eu)
    EU_POLICY_KEYS = frozenset({"set_aside_requirement", "nutrient_surplus_target", "surplus_rule", "surplus_cut",
                                "mineral_redu",
                                "pesticide_reduction",
                                "organic_area_target"})

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
        br = getattr(self.sv, "nbal_bracket", {})
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
        prev = getattr(self.sv, "nbal_prev", {}).get(region)
        nxt = None
        if prev is not None and abs(g - prev[1]) > 1e-12 and abs(used - prev[0]) > 1e-12:
            nxt = used - g * (used - prev[0]) / (g - prev[1])
        if nxt is None or not (lo < nxt < hi):
            if hi == float("inf"):
                nxt = max(dual, 2.0 * used, 1e-3)
            else:
                nxt = 0.5 * (lo + hi)
        self.sv.nbal_prev = getattr(self.sv, "nbal_prev", {})
        self.sv.nbal_prev[region] = (used, g)
        br[region] = (lo, hi)
        self.sv.nbal_bracket = br
        return max(0.0, nxt)

    #: The market whose price each activity earns, where the codes differ.
    #: The market-to-farm price signal is keyed by MARKET COMMODITY, but margins
    #: and the yield-price response look it up by ACTIVITY: without this map no
    #: animal ever saw a meat, milk or egg price change (the +7% pork price under
    #: Farm-to-Fork never reached pig farmers). Rye and oats earn their own market
    #: prices (RYEM, OATS), as in CAPRI.
    ACTIVITY_PRICE_SOURCE = {a: r["price_source"] for a, r in ACTIVITY_CLASSES.items() if r["price_source"]}   # N6

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
        rm = ration_model_for(self.data, None, getattr(self, "pmp_source", "capri2030"),
                              getattr(self, "pmp_capri_parts", ()))
        self.seen.feed_rations = rations_by_region(rm)
        self.seen.feed_prices = feed_prices_by_region(rm, None)

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
        if getattr(self.seen, "feed_rations", None) is None:
            self._base_rations()
        target_regions = regions or self.regions
        results = {}
        n_failed = 0

        self.res.max_nbal_update = 0.0
        # A new run (no price signal yet) starts from no nitrogen price - reset ONCE, here. These resets used to
        # sit inside the region loop, so on a run's first iteration every region wiped the state, secant memory and
        # bracket of all regions before it: only the last region kept them, and every other region lost an iteration.
        if price_signals is None or not hasattr(self.sv, "nbal_state"):
            self.sv.nbal_state, self.sv.nbal_bracket, self.sv.nbal_prev = {}, {}, {}
        _pol_all = policy_scenario
        target_regions = list(target_regions)
        n_regions = len(target_regions)
        for i, (region, result, failed, lu_r, kind) in enumerate(
                self._solve_regions(target_regions, _pol_all, price_signals, verbose)):
            if verbose and i % int(_settings().get("diagnostics.progress_every_regions")) == 0:
                print(f"  Supply module: solved region {i+1}/{n_regions}...")
            n_failed += failed
            if result is None:
                continue
            results[region] = result
            # merged in the regions' order, so the trace is the same with any number of workers
            if lu_r > getattr(self.res, "max_nbal_update", 0.0):
                self.res.max_nbal_region = (region, kind)
            self.res.max_nbal_update = max(getattr(self.res, "max_nbal_update", 0.0), lu_r)

        if verbose:
            print(f"  Supply module complete: {len(results)} regions, "
                  f"{n_failed} non-converged.")
        return results

    #: a region's solves within one outer iteration taking longer than this are reported (seconds)
    SLOW_REGION_SECONDS = setting("diagnostics.slow_region_seconds")

    def _solve_region(self, region, _pol_all, price_signals, verbose=False):
        """_solve_region_impl, timed: a slow region is reported with its number of regional solves.

        With _hess_probe set (the market supply Hessian, model._market_supply_hessian), the region's first IPOPT solve
        is fingerprinted (capri_regional_nlp.problem_fingerprint: problem, start, multipliers, options): "record" keeps
        the digest of the base solve; "compare" stops the region before that solve where the digest is the base's (the
        price shock does not reach the region: its solves would repeat the base's exactly, IPOPT being deterministic)
        and returns the base result; "verify" solves anyway and records where the result differs from the base's."""
        mode = getattr(self.seen, "hess_probe", None)
        if mode is None:
            return self._solve_region_timed(region, _pol_all, price_signals, verbose)
        from capri_mod.supply import capri_regional_nlp as _crn
        first = {"fp": None}

        def probe(fp):
            if first["fp"] is not None:
                return
            first["fp"] = fp
            if mode == "record":
                _st.setdefault(self.res, "hess_fp", {})[region] = fp
            elif mode == "compare" and fp == (getattr(self.res, "hess_fp", None) or {}).get(region):
                raise _InputsUnchanged()
        _crn.SOLVE_PROBE = probe
        try:
            out = self._solve_region_timed(region, _pol_all, price_signals, verbose)
        except _InputsUnchanged:
            import copy as _cp
            base = _cp.copy(self.seen.hess_base_res[region])
            base.hess_unchanged = True
            return region, base, 0, 0.0, "unchanged"
        finally:
            _crn.SOLVE_PROBE = None
        if mode == "verify" and first["fp"] is not None \
                and first["fp"] == (getattr(self.res, "hess_fp", None) or {}).get(region) and out[1] is not None:
            b, r = self.seen.hess_base_res[region], out[1]
            same = all(pd.Series(getattr(r, k_)).equals(pd.Series(getattr(b, k_)))
                       for k_ in ("activities", "gross_output") if hasattr(b, k_))
            _st.setdefault(self.res, "hess_verify", {})[(getattr(self.seen, "hess_shock", ""), region)] = same
        return out

    def _solve_region_timed(self, region, _pol_all, price_signals, verbose=False):
        import time as _t
        t0 = _t.time()
        mdl = (getattr(self, "_models", None) or {}).get(region)
        n0 = int(getattr(mdl.res, "n_solves", 0) or 0) if mdl is not None else 0
        out = self._solve_region_impl(region, _pol_all, price_signals, verbose)
        dt = _t.time() - t0
        if dt > self.SLOW_REGION_SECONDS:
            mdl = (getattr(self, "_models", None) or {}).get(region)
            n1 = int(getattr(mdl.res, "n_solves", 0) or 0) if mdl is not None else 0
            import warnings as _w
            _w.warn(f"slow regional solve {region}: {dt:.0f} s, {n1 - n0} solves of the regional model "
                    f"(NLP relaxed: {getattr(mdl.res, 'nlp_relaxed', None)})", RuntimeWarning)
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
        if isinstance(_pol_all, dict) and not is_eu(region):
            policy_scenario = {k: v for k, v in _pol_all.items() if k not in self.EU_POLICY_KEYS}
        try:
            model = self._get_or_build_model(region)
            # a mandatory non-productive share travels with the policy
            # dict and binds the arable land constraint
            sa, surplus_row = 0.0, None
            if isinstance(policy_scenario, dict):
                sa = float(policy_scenario.get("set_aside_requirement", 0.0) or 0.0)
                # CAPRI's tiered surplus rule needs the region's own gross
                # N balance, so it is resolved here rather than in model.py
                if policy_scenario.get("nutrient_surplus_target"):
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
                                       self._manure_per_head(region, model),
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
                                    target = sp * (1.0 - param("JRC_CAPPED_CUT"))
                        surplus_row = (bc[0], target, bc[1], bc[2],
                                       self.data["yields"].loc[region],
                                       self._fert_techs(region),
                                       self._manure_per_head(region, model),
                                       sp)

            # CAPRI's mineral fertiliser reduction (mineRedu), EU27 only (minfert_redu_*.gms)
            mcap = None
            if isinstance(policy_scenario, dict) and str(policy_scenario.get("mineral_redu", "00") or "00") != "00":
                mcap = self._mineral_cap_spec(region, model, policy_scenario.get("mineral_redu"))
            # each region's balance price is held HERE, not on the model; it is reset once per run, before the loop.
            # The nitrogen-balance price is settled WITHIN the iteration, at fixed market prices: it depends only on
            # this region's own shadow prices.
            nb_used = getattr(self.sv, "nbal_state", {}).get(region, 0.0) if surplus_row else 0.0
            n_metric = 0.0
            # CAPRI prices raw milk per member state (its dairies' fat and protein balances, raw milk not
            # traded): the region's milk price is the EU signal plus its member state's departure from the
            # EU average (MarketModule.dairy_block, CAPRIModel)
            _ps_r = price_signals
            # CAPRI's EU trade blocks: the member state's block price as a departure from the EU signal
            # (CAPRIModel, MarketModule._ms_block_map); activity-keyed entries follow their products
            _bdev = (getattr(self.seen, "price_dev_ms", None) or {})
            if _bdev and price_signals is not None:
                _msb = capri_ms(region)
                _dvs = _bdev.get(_msb)
                if _dvs is not None:
                    _dvs = self._activity_signals(_dvs)
                    _ps_r = price_signals.add(_dvs.reindex(price_signals.index).fillna(0.0))
            _mdev = getattr(self.seen, "milk_price_dev_ms", None) or {}
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
                set_aside_requirement=sa,
                surplus_row=surplus_row,
                mineral_cap=mcap,
            )
            model.seen.ration_state = (getattr(self.seen, "ration_state", None) or {}).get(region)
            model.seen.manure_pool_price = (getattr(self.seen, "manure_pool_price", None) or {}).get(region[:2], 0.0)
            model.seen.manure_pool_price_pk = {nut_: float(((getattr(self.seen, "manure_pool_price_pk", None) or {}).get(nut_) or {})
                                                      .get(region[:2], 0.0)) for nut_ in ("P", "K")}
            model.seen.yani_price_ratio = getattr(self.seen, "yani_price_ratio", None)
            _yms = getattr(self.seen, "yani_price_ratio_ms", None) or {}
            if _yms:
                # young-animal prices of the member state's market (CAPRI yaniMarket_ per trade block)
                _msy = capri_ms(region)
                model.seen.yani_price_ratio = _yms.get(_msy, model.seen.yani_price_ratio)
            model.seen.feed_rations = (getattr(self.seen, "feed_rations", None) or {}).get(region)
            model.seen.feed_prices = (getattr(self.seen, "feed_prices", None) or {}).get(region)
            # CAPRI's feed bulk prices of the region's member state (feedBlkPrice_, CAPRIModel)
            _ms = capri_ms(region)
            model.seen.feed_bulk_ratio = {b: x for (m, b), x in (getattr(self.seen, "feed_bulk_ratio", None) or {}).items()
                                     if m == _ms}
            # CAPRI's emission tax (ghgTax): EU regions only (msNoEU excluded), CAPRIModel sets it
            model.seen.ghg_tax = float(getattr(self.seen, "ghg_tax", 0.0) or 0.0) if is_eu(region) else 0.0
            model.seen.ghg_coef = (getattr(self.seen, "ghg_coef", None) or {}).get(region)
            # the regional model needs the environmental module for the
            # balance's substitution factor (manure market, crop-need
            # limit); it lived only on the supply module, so the
            # regional calls failed and fell back silently
            if getattr(self.par, "env_for_surplus", None) is None:
                from capri_mod.environmental.environmental_module import EnvironmentalModule
                self.par.env_for_surplus = EnvironmentalModule(self.data)
                self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
            model.seen.env_for_surplus = self.par.env_for_surplus
            # CAPRI's crop nutrient balance and manure market in every EU solve (Sprint 9k)
            model.seen.manure_ctx = self._manure_context(region, model)
            try:
                model.seen.fert_techs_all = self._fert_techs(region)      # CAPRI's fertiliser options (NLP form)
            except Exception:
                model.seen.fert_techs_all = []
            result = model.solve(n_balance_price=nb_used, **solve_kw)
            # manure market: hand the region's endogenous manure trade and allocated
            # mineral N to the environmental accounting (else the reported N balance
            # recomputes them from herds and fixed rates and misses the trade)
            result.manure_trade = tuple(getattr(model.res, "last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
            result.manure_trade_pk = dict(getattr(model.res, "last_manure_trade_pk", None) or {})
            result.mineral_n_alloc = _mineral_n_for_accounts(model)
            result.fert_npk = getattr(model.res, "last_npk", None)
            result.manure_availability = getattr(model.ev, "pool_avail", 0.0)
            result.animal_n_relief = _merge_relief(model)
            result.manure_ni_nh3 = dict(getattr(model.ev, "manure_ni_nh3", None) or {})
            result.cover_crops = dict(getattr(model.res, "cover_solved", None) or getattr(model.ev, "cover", None) or {})
            result.animal_nh3_saved = dict(getattr(model.res, "animal_nh3_saved", None) or {})
            result.animal_n_kept = dict(getattr(model.res, "animal_n_kept", None) or {})
            result.manure_tech_shares = dict(getattr(model.res, "manure_tech_shares", None) or {})
            result.dairy_low_shift = float(getattr(model.res, "last_dairy_z", 0.0) or 0.0)
            result.cattle_shift = dict(getattr(model.res, "last_cattle_z", None) or {})
            result.yani_dnet = getattr(model.res, "yani_dnet", None)
            result.genetics_shift = dict(getattr(model.res, "last_genet_z", None) or {})
            result.histosol_fallow = dict(getattr(model.res, "last_hist_fallow", None) or {})
            result.technology_mix = dict(getattr(model.res, "last_mix_z", None) or {})
            _ls = getattr(model.res, "land_solution", None) or {}
            result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model.ev, "land_types_used", []) if t_ in _ls}
            result.luc = _luc_of(model, result.land_types)
            result.n_target_relaxed = bool(getattr(model.res, "n_target_relaxed", False))
            if surplus_row and model._ni_inside() and getattr(model.res, "nlp_ok", False):
                # capri-mod-proto: nothing in the regional model depends on the N price any more
                # (fertiliser and ammonia technologies and the inhibitor on manure are all decided
                # inside the regional model), so the target is a plain constraint, as in CAPRI's NLP:
                # one solve, and its dual is the N-balance price (reporting)
                nb_used = max(float(result.shadow_prices.get("N_balance", 0.0)), 0.0)
                self.sv.nbal_state[region] = nb_used
                n_metric = 0.0
            elif surplus_row:
                # nitrogen-balance price: a fresh bracket at this land level
                self.sv.nbal_bracket[region] = (0.0, float("inf"))
                self.sv.nbal_prev.pop(region, None)
                for _ in range(self.NBAL_INNER_MAX):
                    dual = float(result.shadow_prices.get("N_balance", 0.0))
                    nb_next = self._next_nbal(region, nb_used, dual)
                    if nb_next == nb_used:
                        break
                    nb_used = nb_next
                    result = model.solve(n_balance_price=nb_used, **solve_kw)
                self.sv.nbal_state[region] = nb_used
                # settled when the price matches what the constraint
                # reports, or - at a kink, where it jumps from positive to
                # zero - when the bracket around it is within tolerance
                lo, hi = self.sv.nbal_bracket.get(region, (0.0, float("inf")))
                gap = abs(float(result.shadow_prices.get("N_balance", 0.0)) - nb_used)
                tol = self.NBAL_TOL_ABS + self.NBAL_TOL_REL * abs(nb_used)
                n_metric = 1e-3 * min(gap, hi - lo) / tol
            # Attach the regional model's FINAL state to the result stored: the
            # inner N-price loop re-solves and returns new result objects, so
            # fields set after the first solve were lost (technologies are only
            # adopted once the N price is positive, i.e. after the first solve).
            try:
                result.manure_trade = tuple(getattr(model.res, "last_manure_trade", (0.0, 0.0)) or (0.0, 0.0))
                result.manure_trade_pk = dict(getattr(model.res, "last_manure_trade_pk", None) or {})
                result.mineral_n_alloc = _mineral_n_for_accounts(model)
                result.fert_npk = getattr(model.res, "last_npk", None)
                result.manure_availability = getattr(model.ev, "pool_avail", 0.0)
                result.animal_n_relief = _merge_relief(model)
                result.manure_ni_nh3 = dict(getattr(model.ev, "manure_ni_nh3", None) or {})
                result.cover_crops = dict(getattr(model.res, "cover_solved", None) or getattr(model.ev, "cover", None) or {})
                result.animal_nh3_saved = dict(getattr(model.res, "animal_nh3_saved", None) or {})
                result.animal_n_kept = dict(getattr(model.res, "animal_n_kept", None) or {})
                result.manure_tech_shares = dict(getattr(model.res, "manure_tech_shares", None) or {})
                result.dairy_low_shift = float(getattr(model.res, "last_dairy_z", 0.0) or 0.0)
                result.cattle_shift = dict(getattr(model.res, "last_cattle_z", None) or {})
                result.yani_dnet = getattr(model.res, "yani_dnet", None)
                result.genetics_shift = dict(getattr(model.res, "last_genet_z", None) or {})
                result.histosol_fallow = dict(getattr(model.res, "last_hist_fallow", None) or {})
                result.technology_mix = dict(getattr(model.res, "last_mix_z", None) or {})
                _ls = getattr(model.res, "land_solution", None) or {}
                result.land_types = {t_: float(_ls[t_]) for t_ in getattr(model.ev, "land_types_used", []) if t_ in _ls}
                result.luc = _luc_of(model, result.land_types)
                result.n_target_relaxed = bool(getattr(model.res, "n_target_relaxed", False))
                result.nitrate_n_extra = model._nitrate_extra()
                # CAPRI's mineral fertiliser reduction: the regulations of the inner fertiliser model (reporting)
                result.mineral_cap = ({k: mcap[k] for k in ("kind", "reduction", "base_mineral", "group_caps",
                                                            "limcres")} if mcap else None)
                result.feed_dm = (dict(getattr(model.res, "last_feed_dm", None) or {})
                                  if getattr(model.ev, "last_duals", None) is not None else None)
                result.feed_t = (dict(getattr(model.res, "last_feed_t", None) or {})
                                 if getattr(model.ev, "last_duals", None) is not None else None)
                # fertiliser technologies inside: each crop's reported intensity includes its
                # inside factor m_c / (n_c area_c) (reporting only; the N row never sees it)
                _ff = getattr(model.res, "fert_inside_factor", None) or {}
                if _ff and getattr(model.ev, "last_duals", None) is not None:
                    _ni = dict(getattr(result, "n_intensity", None) or {})
                    for _c, _f in _ff.items():
                        _ni[_c] = float(_ni.get(_c, 1.0)) * float(_f)
                    result.n_intensity = _ni
                if not getattr(result, "fert_tech_shares", None):
                    result.fert_tech_shares = dict(getattr(model.res, "fert_tech_shares", None) or {})
                # the options' N saving (CAPRI othImpact NMIN), for their emission side effects
                if result.fert_tech_shares:
                    try:
                        result.fert_nmin = {o_[0]: float(o_[1]) for o_ in self._fert_techs(region)}
                    except Exception:
                        result.fert_nmin = {}
                result.nitrate_share = {a: float(v.get("nitr_share", 0.0))
                                        for a, v in (getattr(model.seen, "ration_state", None) or {}).items()
                                        if isinstance(v, dict) and float(v.get("nitr_share", 0.0)) > 0}
                # regions without substitution data (Berlin: almost no farmland) return
                # None - never let that drop the region
                try:
                    _sb = model.seen.env_for_surplus._substitution(region) if getattr(model.seen, "env_for_surplus", None) is not None else None
                    result.n_substitution = float(_sb[0]) if _sb else 0.0
                except Exception:
                    result.n_substitution = 0.0
            except AttributeError:
                pass
            return region, result, (0 if result.converged else 1), n_metric, "N price"
        except Exception as e:
            # a region whose solve raises stops the run (28 October 2026): an exception here is a fault of the code
            # or the data, not a solver outcome (non-optimal and failed solves are handled inside the solve). Until
            # then the region was dropped with a warning and the run went on, and could report convergence without
            # it (a mini-EU run of 20 units solved Norway's alone and "converged"); no reference run ever dropped one
            raise RuntimeError(f"region {region}: the regional solve raised {e!r}") from e

    #: worker processes for the regional solves: None = the machine's cores (CAPRI_WORKERS overrides), 1 = in this
    #: process. CAPRI solves its regional models one after another (or in parallel GAMS grid jobs); they are
    #: independent at given market prices, so the results do not depend on the number of workers
    n_workers = setting("run.n_workers", lambda v: None if int(v) == 0 else int(v), run_state=True)
    #: regional state carried between iterations, and the region-keyed caches, sent back from the workers
    _PAR_STATE = ("sv.nbal_state", "sv.nbal_bracket", "sv.nbal_prev")       # paths in the state objects (stage 3, S10a)
    _PAR_CACHES = ("par.mctx_cache", "par.balance_cache", "par.mcap_cache", "res.hess_fp", "res.hess_verify")

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
        from capri_mod.utils import ipopt_library as _il
        if _il.active():
            # an IPOPT with OpenMP (supply.nlp_ipopt_library): one thread in a process that forks workers, the threads
            # to the workers (a process that ran OpenMP on several threads hangs its forked children: ipopt_library)
            _il.for_parent(nw, self.workers(10 ** 9))
        if nw <= 1:
            for r in regions:
                yield self._solve_region(r, _pol_all, price_signals, verbose)
            return
        yield self._solve_region(regions[0], _pol_all, price_signals, verbose)
        if getattr(self.par, "env_for_surplus", None) is None:       # shared by all regional models
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            self.par.env_for_surplus = EnvironmentalModule(self.data)
            self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
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
                        model.seen.env_for_surplus = self.par.env_for_surplus
                        self._models[region] = model
                    for name in self._PAR_STATE:
                        d = _st.setdefault_path(self, name, {})
                        if name in state:
                            d[region] = state[name]
                        else:
                            d.pop(region, None)
                    for name, new in caches.items():
                        _st.setdefault_path(self, name, {}).update(new)
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
                self.res.worker_failures = int(getattr(self.res, "worker_failures", 0) or 0) + 1
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


class _InputsUnchanged(BaseException):
    """A region's first solve has the base's inputs (SupplyModule._solve_region, probe "compare"). BaseException, so the
    regional model's handlers of solver failures (except Exception) let it through."""


def _par_solve_region(region):
    """Worker process: one region's solves (SupplyModule._solve_region) with the state forked from the parent;
    returns the result, the regional model (without the shared environmental module), the region's land and
    nitrogen-price state and the cache entries it added."""
    sm, pol, ps, verbose = _PAR_CTX
    from capri_mod.utils import ipopt_library as _il
    _il.for_worker()                                     # supply.nlp_omp_threads (nothing without an OpenMP IPOPT)
    before = {n: set(_st.get_path_or(sm, n) or ()) for n in sm._PAR_CACHES}
    out = sm._solve_region(region, pol, ps, verbose)
    model = sm._models.get(region)
    if model is not None:
        _st.pop(model.seen, "env_for_surplus", None)     # this process's copy, re-attached in the parent
    state = {n: _st.get_path(sm, n)[region] for n in sm._PAR_STATE if region in (_st.get_path_or(sm, n) or {})}
    caches = {n: {k: v for k, v in (_st.get_path_or(sm, n) or {}).items() if k not in before[n]} for n in sm._PAR_CACHES}
    return out, model, state, caches


def _luc_of(model, land_types):
    """CAPRI's land-use change transitions (capri_mod.environmental.luc) of the region at its solved land types,
    moved from the base land types of the land market; None outside CAPRI's LUC data."""
    try:
        from capri_mod.environmental.luc import LUCModel
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        env_ = getattr(model.seen, "env_for_surplus", None)
        inner = getattr(env_.par, "inner_fert", None) if env_ is not None else None
        if inner is None:
            inner = InnerFertDist()
        cr = model.data.region_id              # the model's regions are CAPRI's units
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
    npk = getattr(model.res, "last_npk", None) or {}
    if "N" in npk:
        return float(npk["N"]["purchase"])
    return getattr(model.res, "last_mineral_n", None)


def _merge_relief(model) -> dict:
    """N relief per activity unit for the accounts: ammonia technologies + inhibitors on manure."""
    out = dict(getattr(model.ev, "animal_n_relief", None) or {})
    for a, v in (getattr(model.ev, "manure_ni_relief", None) or {}).items():
        out[a] = out.get(a, 0.0) + float(v)
    return out




def fert_side_value(region: str, tech: str, item: str):
    """CAPRI's literature-review side effect (p_litRevFertTechs) for a model region, or None
    (capri_data/2017/abatement/fert_side_effects.csv, tools/build/build_fert_side_effects.py)."""
    def load(inp):
        tab = inp.csv("fert_side_effects.csv", "abatement")
        return {(r.region, r.technology, r.item): float(r.value) for r in tab.itertuples()}
    return _inputs.current().cached("fert_side_effects", load).get((region, tech, item))


# refactor stage 3a: the mixin modules' methods see this module's names (capri_mod/utils/mixins.py)
from capri_mod.utils.mixins import inject_names as _inject_names  # noqa: E402
_inject_names(globals(), ["capri_mod.supply." + _m for _m in ("livestock", "fertilisation", "abatement", "policy",
                                                              "land", "nlp", "techn_mix")])

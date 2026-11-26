r"""The PMP calibrator of the regional models (moved from capri_mod/supply/supply_module.py as it was, 26 November
2026).
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
from capri_mod.market.equations.set_prices import DATA_UVAG_Y
from capri_mod.supply.equations.greendeal.landscape import DATA_FALL_FLOOR
from capri_mod.supply.equations.greendeal.surptot import data_SURTOT_MAXS
from capri_mod.supply.equations.set_supply_bounds import v_actLevl_up_FALL
from capri_mod.supply.equations.ghgmiti import (
    p_ghgMiti_othImpact_EmiCalmin, p_ghgMiti_pmpParsqr, p_ghgMiti_pmpParsqr_saving, p_ghgMiti_relSubs)




# ---------------------------------------------------------------------------
# PMP CALIBRATION
# ---------------------------------------------------------------------------

#: CAPRI's saving term of a fertiliser option's curvature, (nmE, value, m0, m1) (envind/ghgMiti.gms l. 1029-1045;
#: capri_mod/supply/equations/ghgmiti.py p_ghgMiti_pmpParsqr_saving; the mixins call it by this name)
saving_slope = p_ghgMiti_pmpParsqr_saving


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

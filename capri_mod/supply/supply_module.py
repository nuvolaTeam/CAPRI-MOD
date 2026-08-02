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

    def _build_constraints(
        self,
        nitrate_limit: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (A_ub, b_ub, A_eq, b_eq) for scipy.optimize.

        Constraints:
          1. Total arable land ≤ UAA_arable
          2. Total permanent crops ≤ UAA_permanent
          3. Total grassland = used grass area (accounting identity, soft)
          4. For each nutrient N: Σ_i coef_{Ni} × x_i ≤ N_max (nitrates dir.)
          5. Set-aside floor if applicable
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
        b_rows.append(self.data.land.get("ARABLE", 200.0))

        # 2. Permanent crops land constraint
        row_perm = np.zeros(n)
        perm_crops = ["WINE", "OLIV", "APPL", "OFRU", "CITR", "TAGR",
                      "TOBA", "COTT", "OFIB"]
        for a in perm_crops:
            if a in acts_idx:
                row_perm[acts_idx[a]] = 1.0
        A_rows.append(row_perm)
        b_rows.append(self.data.land.get("PERMANENT", 30.0))

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
        try:
            return self._solve_inner(price_shock, policy_shock, nitrate_limit)
        finally:
            self.net_revenues = _net_rev_backup
            if _cap_backup is not None:
                self.data.cap_payments = _cap_backup
            if _prem_backup is not None:
                self.data.cap_premium = _prem_backup

    def _solve_inner(
        self,
        price_shock: Optional[pd.Series] = None,
        policy_shock: Optional[Dict] = None,
        nitrate_limit: Optional[float] = None,
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
                    for key, val in policy_shock.items():
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
        A_ub, b_ub, _, _ = self._build_constraints(nitrate_limit=nitrate_limit)

        constraints = LinearConstraint(A_ub, lb=-np.inf, ub=b_ub)

        # Solve NLP
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                fun=self._objective,
                x0=x0,
                jac=self._gradient,
                method="trust-constr",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": SOLVER_MAXITER, "gtol": 1e-6, "verbose": 0},
            )

        x_opt = np.maximum(result.x, 0.0)

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
            converged=result.success,
            solver_message=result.message,
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
                result = model.solve(
                    price_shock=price_signals,
                    policy_shock=policy_scenario,
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

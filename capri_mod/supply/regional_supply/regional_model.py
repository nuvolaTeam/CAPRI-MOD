r"""The regional supply model's class: its settings, constructor and price helpers, composed of its blocks (moved from
capri_mod/supply/supply_module.py as it was, 26 November 2026; the net revenues, constraints and solve in
net_revenues.py, constraints.py, solve.py).
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

#: the class, set by capri_mod/supply/supply_module.py where it is defined (an import here would be circular)
SupplyModule = None


from capri_mod.supply.regional_supply.pmp_calibrator import PMPCalibrator  # noqa: E402
from capri_mod.supply.regional_supply.tables import RegionData, _InputColumn  # noqa: E402


# ---------------------------------------------------------------------------
# REGIONAL NLP MODEL
# ---------------------------------------------------------------------------

# the refactor's split into block mixins: the regional model's methods in mixin modules of this package
from capri_mod.supply.livestock import LivestockBlock  # noqa: E402
from capri_mod.supply.state import ModuleStateMixin, RegionalStateMixin  # noqa: E402
from capri_mod.supply import state as _st  # noqa: E402
from capri_mod.supply.fertilisation import FertilisationBlock  # noqa: E402
from capri_mod.supply.abatement import AbatementBlock  # noqa: E402
from capri_mod.supply.policy import PolicyBlock  # noqa: E402
from capri_mod.supply.land import LandBlock  # noqa: E402
from capri_mod.supply.nlp import NLPBlock  # noqa: E402
from capri_mod.supply.techn_mix import TechnMixBlock  # noqa: E402
# the blocks moved out of the class (26 November 2026)
from capri_mod.supply.regional_supply.net_revenues import NetRevenuesBlock  # noqa: E402
from capri_mod.supply.regional_supply.constraints import ConstraintsBlock  # noqa: E402
from capri_mod.supply.regional_supply.solve import SolveBlock  # noqa: E402


class RegionalSupplyModel(NetRevenuesBlock, ConstraintsBlock, SolveBlock, RegionalStateMixin, LivestockBlock, FertilisationBlock, AbatementBlock, PolicyBlock,
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
    #: module are not state. 2 November 2026 (docs/dev/REFACTOR_BEHAVIOUR_CHANGES.md, the project lead's decision):
    #: sv.n_relax_sticky added (the JRC121368 relaxation kept for the same N target), ev.ghg_nr_obj taken out (an
    #: identity reference: its deep copy could never match, and the tax's undo never acts across solves)
    SOLVE_STATE = ("ev.amm_cost", "sv.amm_last", "res.animal_n_kept", "ev.animal_n_relief", "res.animal_nh3_saved",
                   "res.cover_solved", "res.fd_model", "res.land_solution", "res.last_aug", "res.last_cattle_z",
                   "res.last_dairy_z", "ev.last_duals", "res.last_feed_dm", "res.last_feed_t", "res.last_feed_price",
                   "res.last_feed_lin", "res.last_genet_z",
                   "res.last_hist_fallow", "res.last_mix_z", "res.last_npk", "ev.last_req_duals",
                   "ev.manure_ni_nh3", "ev.manure_ni_relief", "res.manure_tech_shares", "res.amm_subs",
                   "ev.price_shock_now",
                   "sv.wc_solved", "seen.feed_rations", "sv.n_relax_sticky")
    #: a solve's outputs the coupling reads from the model itself after the supply side (not from the solve's result):
    #: the manure pools' columns, bounds and vectors and the manure value (coupling/manure.py). The market supply
    #: Hessian restores them after its shocks too (24 November 2026, KNOWN_ISSUES K198): its last shock's manure value
    #: was left for the baseline's manure pool market, so a run that measured the Hessian ended its baseline about
    #: 1e-12 from one that read it from the cache (1e-5 after the Green Deal scenario). Not inputs of a solve: restoring
    #: them before each shock leaves the shocks as they were
    COUPLING_READS = ("res.manure_value", "res.pool_manure_vec", "res.pool_manure_vec_pk", "res.pool_manure_x0",
                      "ev.pool_cols", "ev.pool_cols_pk", "ev.pool_lb")
    #: the regional NLP's fields (warm starts, calibration, fallbacks and their diagnostics): what the market supply
    #: Hessian restored by the prefix "_nlp" until 2 November 2026 (the refactor of the supply's parameters and state: the same set, declared). An
    #: entry is an attribute name or, for a field moved into the state objects, its path ("sv.nlp_prev"; both
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


    def _pt(self, act, comm) -> float:
        """CAPRI's factor on the market's relative price change for this output (price_transmission; 1 where none):
        its unit value moves by the market price's absolute change (arm/set_prices.gms l. 43-89; K169)."""
        t = getattr(self.data, "price_transmission", None)
        return float(t.get((act, comm), 1.0)) if t else 1.0

    def _transmit_crops(self, price_shock):
        """The price shock with each crop's relative change on its unit value: the market's x CAPRI's factor (K169)."""
        t = getattr(self.data, "price_transmission", None)
        if price_shock is None or not t:
            return price_shock
        ps = price_shock.copy()
        for (a, c), f in t.items():
            if a == c and a in ps.index and a in CROPS:
                ps[a] = DATA_UVAG_Y(float(ps[a]), float(f))           # set_prices.gms l. 44-47
        return ps

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
                return sum(v * self._pt(act, m) * float(price_shock.get(m, price_shock.get(act, 0.0) if m == own else 0.0))
                           for m, v in parts.items())
        return mrev * self._pt(act, own) * float(price_shock.get(act, 0.0))

    #: CAPRI's other animals (OANI): one output per unit of their level (CAPRI's LEVL, an index), YILD x UVAG as a
    #: crop's (yields.csv, producer_prices_regional.csv), their inputs TOIN per unit (variable_costs.csv) and their
    #: premium PRME per unit (cap_premium_activity.csv); no feed, held at their data level (FACT, supply/prep_sim.gms l.
    #: 250-251; KNOWN_ISSUES K207)
    OTHER_ANIMALS = ("OANI",)

    def _solve_prices(self) -> pd.Series:
        """The crops' producer prices of this solve, as _compute_net_revenues forms their revenue: the data's price x
        (1 + the solve's transmitted price change, ev.price_shock_now). The Green Deal's yield changes are valued at
        them, as CAPRI values the yields at the solution's prices (KNOWN_ISSUES K209; before 26 November 2026 the
        organic yield gap and the pesticide loss took the data's price)."""
        prices = self.data.producer_prices
        ps = getattr(self.ev, "price_shock_now", None)
        if ps is None:
            return prices
        return prices * (1 + ps.reindex(prices.index).fillna(0))

    def _nr_item(self, act, side, item, per_unit, kg=None, uv=None) -> None:
        """Record a change of an activity's net revenue per unit made within the solve after _compute_net_revenues, by
        item, for the economic accounts by item (income I2, capri_mod/income/eaa.py): side "O" an output's change (the
        net revenue moves by per_unit, a quantity change kg per unit at the unit value uv in EUR per t where given),
        side "I" an input's change (the net revenue moves by -per_unit). Kept in ev.nr_items for this solve."""
        if not per_unit:
            return
        if getattr(self.ev, "nr_items", None) is None:
            self.ev.nr_items = {}
        self.ev.nr_items.setdefault(act, []).append((side, item, float(per_unit), kg, uv))

    def _output_items(self, act, revenue, price, yld, tou, mrev, price_shock) -> list:
        """The revenue per ha or head by output item, as _compute_net_revenues forms it: [(item, quantity per unit in kg or
        None, unit value in EUR per t or None, value per unit in EUR)], the values adding up to the revenue. A crop: its
        product, yield x price. An animal with CAPRI's output value per head (TOOU): its market products' values per
        head with their price changes (_market_revenue_change) and the rest of TOOU (the young animals and the other
        outputs, OTHER_O: one item); without it, its own product. Recorded for the economic accounts by item (income I2,
        capri_mod/income/eaa.py)."""
        if act not in ANIMALS:
            return [(act, float(yld) * 1000.0, float(price), float(revenue))]
        own = SupplyModule.ACTIVITY_PRICE_SOURCE.get(act) or act
        pv = getattr(self.data, "livestock_product_value_by_market_coef", None)
        parts = ({k.split(".", 1)[1]: float(v) for k, v in pv.items()
                  if k.startswith(act + ".") and pd.notna(v) and float(v) != 0.0} if pv is not None else {})
        if tou is None or not parts:
            return [(own, None, None, float(revenue))]
        items = []
        for m_, v in parts.items():
            sh = 0.0 if price_shock is None or not mrev > 0 else float(
                price_shock.get(m_, price_shock.get(act, 0.0) if m_ == own else 0.0))
            items.append((m_, None, None, v * (1.0 + self._pt(act, m_) * sh)))
        items.append(("OTHER_O", None, None, float(revenue) - sum(v_ for *_, v_ in items)))
        return items


    #: compute each region's response to the young-animal prices from its solved NLP (K65): None (default) with the
    #: cattle member splits only (CAPRIModel.use_yani_exact); True / False force it
    yani_exact_response = setting("young_animals.use_exact", tri_state)


    # K63: the ammonia options are held at their base shares in a regional NLP solve without a policy incentive on N
    # (no N-surplus row, no mineral cap, no emission tax), and re-solved so where the N-surplus row is slack


    #: CAPRI's CAP 2014-2020 greening in the NLP form (permGrasGreening_, ecoSetAside_, cropDivGreening_), as in
    #: CAPRI's 2030 reference (pol_input/cap_after_2014/ref.gms); ecoSetAside_ and cropDivGreening_ only with
    #: env_const (K187)
    cap_greening = setting("supply.cap_greening")
    #: CAPRI's greening rows ecoSetAside_ and cropDivGreening_ (setting supply.env_const; KNOWN_ISSUES K187): CAPRI star
    #: 3.0 lists both without a condition (supply/supply_model_e_list_linear.gms l. 231-232). On: as CAPRI's 2030
    #: reference and Green Deal step solve (their marginals are in the results, reports/margcr.gms l. 321-326,
    #: reports/greening.gms); the July 2026 release lists them only with %envConst% on (its l. 235-236), which the Green
    #: Deal step does not set ("$exit" at l. 398 of pol_input/greendeal/refpol_endotech_all_sup.gms, before
    #: "$setglobal envConst on", l. 408). Off: without both rows.
    env_const = setting("supply.env_const")
    # CAPRI's endogenous entitlement limit (policy/def_endCut.gms, K136)
    entitlement_limit = setting("supply.entitlement_limit")
    #: annual crops (sets.gms annualCrops) of the model and their crop-diversification groups (cropDivGrps: each
    #: annual crop alone, MAIS = grain and silage maize, OSET = set-aside and fallow)
    CROPDIV_GROUPS = {a: r["cropdiv_group"] for a, r in ACTIVITY_CLASSES.items() if r["cropdiv_group"]}


    # CAPRI organic_minfert_redu.gms: the small-mineral-N threshold of 0.01 t/ha and the limCres maximum of 1.2 x the
    # baseline's residues are the parameters ORGANIC_SMALL_MINE_KG_HA and ORGANIC_LIMCRES_FACTOR


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
            if a in ANIMALS and a not in self.OTHER_ANIMALS:
                # no stand-in from price x yield in guessed units (removed 23 October 2026): CAPRI's output value
                # (the other animals, OTHER_ANIMALS, have theirs as YILD x UVAG per unit of CAPRI's level, below)
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

    #: protein-rich feed is priced by the CAKE markets: a cake
    #: price index weighted by CAPRI's EU cake feed use (2017 FAO_agg BAS), at
    #: CAPRI's base world prices. Replaces the soybean-meal PROXY (0.89 x the
    #: soybean price). Values read from the data files on first use.


    #: EU feed use per cereal, CAPRI 2030 reference (FEDM, kt): the weights of
    #: the feed-cereal price change (other cereals include rye and oats)
    FEED_CEREAL_MIX = _InputColumn("feed_cereal_mix_2030.csv", "feed", "fedm_kt")


# the parts that name the class in their code (the young-animal tables' sex split, tables.young_animal_table) get it
# here, where it is defined: an import there would be circular
from capri_mod.supply.regional_supply import tables as _tables  # noqa: E402
_tables.RegionalSupplyModel = RegionalSupplyModel

r"""The regional model's solve: its starts, retries and relaxations (moved from capri_mod/supply/supply_module.py as
they were, 26 November 2026).
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
from capri_mod.supply import state as _st  # noqa: E402


from capri_mod.supply.regional_supply.tables import SupplyResult  # noqa: E402


class SolveBlock:
    """RegionalSupplyModel's solve, _solve_once and _solve_inner."""

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
        and was removed (docs/dev/PROXY_AUDIT.md S149, S410, S411).

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
        self.ev.pest_change_factor = None         # the pesticide applications' scenario factor, THIS solve only
        self.ev.pest_quota_factor = None          # the quota on their total over the base use, THIS solve only
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
        res.till_shares = dict(getattr(self.res, "till_shares", {}) or {})             # the tillage options' shares
        res.urea_share = getattr(self.res, "urea_share", None)                         # the urea substitution's share
        res.legsh_share = getattr(self.res, "legsh_share", None)                       # the legume share's share
        res.supp_fat = getattr(self.res, "supp_fat", None)                             # the ration fat limit
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
        self.res.till_shares = {}
        self.res.urea_share = None
        self.res.legsh_share = None
        self.res.supp_fat = None
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
        # (livestock_premium_coef: the regional premium factors scale it for the solve; until 13 November 2026 it was
        # not restored, so a factor compounded at every solve, KNOWN_ISSUES K143)
        _RESTORABLE = ("cap_payments", "cap_premium", "nutrient_coefs",
                       "yields", "producer_prices", "variable_costs", "land", "livestock_premium_coef")
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
            # the solve's own net revenues, for the income reports (capri_mod/income: income_parts, eaa), before the
            # restore below takes them back to the state before the solve
            self.res.nr_solve = self.net_revenues.copy()
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
        self.ev.nr_items = {}             # the net revenues' changes by item within this solve (_nr_item)
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
                self.apply_yield_price_response(self.ev.price_shock_now)

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
        self.ev.greendeal_animal_inpo = {}
        # CAPRI's Green Deal group (set_fert_priors.gms, %scenarioGroup%==greendeal): the fertiliser priors' partial
        # derivative has a slack in the listed regions
        self.ev.fert_partial_slack = bool(isinstance(policy_shock, dict) and policy_shock.get("greendeal_group"))
        self.ev.greendeal_group = self.ev.fert_partial_slack
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
            _pmod = bool(getattr(self.data, "pesticides", None))         # the pesticide module (supply.pest_disagg)
            # a scenario's change factor of every pesticide application in an EU region (CAPRI's pol_input/
            # pesticides/pesti_regu50.gms, pesti_ban.gms: DATA(RU, mCact, pestoAgg, "ChangeFactor")); the Green Deal's
            # target sets its own below (conventional_io.gms l. 128-131)
            _cf = float(policy_shock.get("pest_change_factor", 1.0) or 1.0)
            from capri_mod.data.definitions import is_eu as _is_eu
            if _pmod and _cf != 1.0 and _is_eu(self.data.region_id):
                self.ev.pest_change_factor = _cf
            # a quota on the total use, its factor on the base use (pesti_quts50.gms: DATA(RU, "QUTS", "pesTotal",
            # "ChangeFactor"))
            _qf = float(policy_shock.get("pest_quota_factor", 0.0) or 0.0)
            if _pmod and _qf > 0 and _is_eu(self.data.region_id):
                self.ev.pest_quota_factor = _qf
            if _org:
                # the organic yield gap: in full without the pesticide module; x 0.45 with it (organic_area.gms
                # l. 182-186: its pesticide part is the module's yield factor; see apply_organic_area_target)
                self.apply_organic_area_target(_org)
            if _pest:
                _prule = str(policy_shock.get("pesticide_rule", "jrc121368") or "jrc121368")
                # with the module, the yield follows the applications' damage functions: no yield loss here (CAPRI's
                # Green Deal calls conventional_io.gms with the yield shock 'off', pesticides.gms l. 47)
                self.apply_pesticide_reduction(_pest, organic_share=_org or None,
                                               yield_loss=(_prule == "jrc121368" and not _pmod))
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
            # inhibitors on manure under CAPRI's emission tax (the inhibitors on manure under the emission tax; without a tax they stay at zero)
            self._apply_manure_inhibitor(0.0)

        A_ub, b_ub, _, _ = self._build_constraints(
            set_aside_requirement=set_aside_requirement)

        # The regional model in CAPRI's form, solved by IPOPT (_nlp_solve). Where a solve fails, CAPRI re-solves with
        # widened bounds and then carries on with the non-optimal solution, recorded (supply/simu_supply.gms,
        # widen_bounds.gms: p_INFES): here JRC121368's relaxed N target is tried, then IPOPT's last point at the region's
        # own problem is kept and recorded (_nlp_last_point); the landscape floor is kept as CAPRI keeps it (K84)
        from capri_mod.supply.equations.supply_model.objective import QUADRA_lin
        c_lin = QUADRA_lin(self.f, self.net_revenues.values)          # QUADRA_'s linear part less LINEAR_'s
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
            self._entl_record(y)
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
            # ...; the grassland split was a column too until 7 November 2026)
            _n0 = len(x0)
            self.ev.need_row = None
            self.ev.alloc_cols = 0
            _lab = list(getattr(self.ev, "row_labels", []))
            Qg, cg, Ag, bg, sg = self._dairy_intensity_column(
                self.Q, c_lin, A_ub, b_ub, np.asarray(x0, float), _lab, _n0)
            Qg, cg, Ag, bg, sg = self._histosol_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
            Qg, cg, Ag, bg, sg = self._mix_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
            Qg, cg, Ag, bg, sg = self._entitlement_columns(Qg, cg, Ag, bg, sg, _lab, _n0)
            self.ev.aug_labels = _lab
            self.res.last_hist_fallow = {}
            _yc = None
            _cols = (getattr(self.ev, "dairy_col", None) is not None
                     or getattr(self.ev, "cattle_cols", None) or getattr(self.ev, "hist_cols", None)
                     or getattr(self.ev, "mix_cols", None) or getattr(self.ev, "entl_col", None) is not None)
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
                self._entl_record(_yg)
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
        # CAPRI's in-solve yield factors of the crops (the technology mix, the pesticide module's v_yldPestFac): per crop,
        # their summed change of the output and of the fertiliser need over the level (_insolve_factors), CAPRI's
        # SUPBAL_ output x (1 + tf) per technology and x (1 + (v_yldPestFac - 1)); the accounts take them as CAPRI's
        # rows do (environmental_module: techn_fact), not through the yield
        _isf = self._insolve_factors(activities)
        if price_shock is None and not policy_shock and getattr(self.res, "last_pest", None):
            # CAPRI's check of the yield factors after the calibrated model's solve at the base (baseline/check_cal.gms
            # l. 315-324): a warning, the run goes on
            from capri_mod.supply.equations.pesti_test import check_cal_pestiCaliProblems
            _pcp = check_cal_pestiCaliProblems({k_: v_["y"] for k_, v_ in self.res.last_pest.items()})
            if _pcp:
                import warnings as _w
                _w.warn(f"Pesticide calibration had problem cases in {self.data.region_id} after the base solve: "
                        f"{_pcp}", RuntimeWarning)
        for _a, (_tf, _ned) in _isf.items():
            gross_output[_a] = float(gross_output[_a]) * (1.0 + _tf)

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
            if _a not in gross_output.index or _a in self.OTHER_ANIMALS:
                # the other animals: their one output, level x YILD as above (CAPRI's OANI per unit of its level)
                continue
            _c = (float(_coef.get(_a)) if _coef is not None
                  and _a in _coef.index and pd.notna(_coef.get(_a)) else None)
            # The output coefficient is per head at base intensity; the dairy split below moves milk with the
            # low-yield cows (a scaling by a dairy yield base, never set since 3a264a2, removed in the refactor of the supply's parameters and state)
            # no output coefficient: unknown (NaN) where the activity has a level, none where it has none
            _lv = float(activities.get(_a, 0.0))
            gross_output[_a] = (_lv * _c if _c is not None else (float("nan") if abs(_lv) > 1e-12 else 0.0))
            # CAPRI's dairy split: z heads at DCOL instead of DCOH change milk by
            # (COMI_DCOL - COMI_DCOH) / COMI_DCOW per head (cull-cow beef, ~1% of the tonnage, is
            # the same for both and is scaled with it: REGISTERED)
            if _c is not None and _a == "DCOW":
                _dz = float(getattr(self.res, "last_dairy_z", 0.0) or 0.0)
                _di = getattr(self.data, "dairy_intensity", None)
                if _dz and _di is not None:
                    gross_output[_a] += _dz * _c * float(_di["dcomi_rel"])
            # the cattle splits (bulls and heifers, the port of CAPRI's bull and heifer splits; replacement heifers and calves): beef per stall,
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
        # the technologies' net revenue difference on the area moved to T1 (the linear term is minus it)
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

        _res = SupplyResult(
            region_id=self.rid,
            activities=activities,
            gross_output=gross_output,
            gross_margin=gm,
            shadow_prices=shadow,
            nutrient_balance=nutrient_balance,
            converged=solver_converged,
            solver_message=solver_message,
            iset=_iset,
            solver_log=list(getattr(self.res, "solver_log", None) or []),
            fodder_duals=({lab: float(_zc[i]) for i, lab in enumerate(labels)
                          if i < len(_zc) and str(lab).startswith("fodder_")} if _zc is not None else {}),
        )
        _res.insolve_yield = {a: {"tf": float(tf_), "ned": float(ned_)} for a, (tf_, ned_) in _isf.items()}
        return _res

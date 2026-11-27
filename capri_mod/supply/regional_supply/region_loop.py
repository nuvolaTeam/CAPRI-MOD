r"""The supply module's loop over the regions and its process pool (moved from capri_mod/supply/supply_module.py as they
were, 26 November 2026).
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


from capri_mod.supply.regional_supply.tables import SupplyResult, _luc_of, _merge_relief, _mineral_n_for_accounts  # noqa: E402



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




class RegionLoopBlock:
    """SupplyModule's run, the regional solves, the workers and the pool."""

    #: The market whose price each activity earns, where the codes differ.
    #: The market-to-farm price signal is keyed by MARKET COMMODITY, but margins
    #: and the yield-price response look it up by ACTIVITY: without this map no
    #: animal ever saw a meat, milk or egg price change (the +7% pork price under
    #: Farm-to-Fork never reached pig farmers). Rye and oats earn their own market
    #: prices (RYEM, OATS), as in CAPRI.
    ACTIVITY_PRICE_SOURCE = {a: r["price_source"] for a, r in ACTIVITY_CLASSES.items() if r["price_source"]}

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
                        target = data_SURTOT_MAXS(sp, float(0.5 if policy_scenario.get("surplus_cut") is None
                                                            else policy_scenario["surplus_cut"]))
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
            # CAPRI's crop nutrient balance and manure market in every EU solve (the manure and ammonia accounts in every EU solve)
            model.seen.manure_ctx = self._manure_context(region, model)
            try:
                model.seen.fert_techs_all = self._fert_techs(region)      # CAPRI's fertiliser options (NLP form)
            except Exception:
                model.seen.fert_techs_all = []
            # their EmiCalMin (envind/ghgMiti.gms l. 936-944), which GHG_Mit_Cost_'s cost base adds to NMIN (K175)
            model.seen.fert_techs_emical = {o_[0]: float(self._emi_cal_min(region, region, o_[0]))
                                            for o_ in model.seen.fert_techs_all}
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
            result.amm_subs = dict(getattr(model.res, "amm_subs", None) or {})
            result.dairy_low_shift = float(getattr(model.res, "last_dairy_z", 0.0) or 0.0)
            result.cattle_shift = dict(getattr(model.res, "last_cattle_z", None) or {})
            result.yani_dnet = getattr(model.res, "yani_dnet", None)
            result.genetics_shift = dict(getattr(model.res, "last_genet_z", None) or {})
            result.histosol_fallow = dict(getattr(model.res, "last_hist_fallow", None) or {})
            result.entitlements = dict(getattr(model.res, "entl", None) or {})
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
                result.amm_subs = dict(getattr(model.res, "amm_subs", None) or {})
                result.dairy_low_shift = float(getattr(model.res, "last_dairy_z", 0.0) or 0.0)
                result.cattle_shift = dict(getattr(model.res, "last_cattle_z", None) or {})
                result.yani_dnet = getattr(model.res, "yani_dnet", None)
                result.genetics_shift = dict(getattr(model.res, "last_genet_z", None) or {})
                result.histosol_fallow = dict(getattr(model.res, "last_hist_fallow", None) or {})
                result.entitlements = dict(getattr(model.res, "entl", None) or {})
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
                result.feed_price = (dict(getattr(model.res, "last_feed_price", None) or {})
                                     if getattr(model.ev, "last_duals", None) is not None else None)
                result.feed_lin = (dict(getattr(model.res, "last_feed_lin", None) or {})
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
            # CAPRI's income indicators at the solution (reports/calc_inc_indic.gms, sol_simy.gms l. 2586; income I1):
            # the region's income with the solved ration and the mitigation options' items, from the final state
            # attached above
            from capri_mod.income.income_module import IncomeDistributionModule
            result.income = IncomeDistributionModule(getattr(self, "data", None)).income_parts(region, result, self)
            result.gross_margin = float(result.income["MGVA"])
            # CAPRI's gross account by item and its check against the activity-based income (income I2)
            try:
                from capri_mod.income.eaa import eaag_items
                result.eaa = eaag_items(region, result, self, ip=result.income)
            except Exception as exc:
                warnings.warn(f"{region}: the gross account by item could not be computed ({exc!r})")
                result.eaa = None
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
    _PAR_STATE = ("sv.nbal_state", "sv.nbal_bracket", "sv.nbal_prev")       # paths in the state objects
    _PAR_CACHES = ("par.mctx_cache", "par.balance_cache", "par.mcap_cache", "res.hess_fp", "res.hess_verify")

    def workers(self, n_regions: int) -> int:
        """Number of worker processes for n_regions regional solves."""
        n = self.n_workers                         # the setting run.n_workers (0: the machine's cores)
        if n is None:
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
        import capri_mod as _cm
        _cm.warn_if_threads_late()           # NumPy loaded before the thread limits (capri_mod/__init__.py)
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

r"""The supply module's regional N balances and caps between solves (moved from capri_mod/supply/supply_module.py as
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




class NBalancesBlock:
    """SupplyModule's manure context, balance coefficients, surplus, mineral cap and the next N balance price."""

    # CAPRI's crop nutrient balance (NUTNED_, fertDistExcr_) and manure market in every EU solve, not only under
    # the N target (the manure and ammonia accounts in every EU solve)

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

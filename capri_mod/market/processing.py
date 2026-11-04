"""MarketModule: processing demand (the normalised quadratic processing functions and oilseed crushing).

Part of capri_mod.market.market_module.MarketModule (a mixin); moved out of market_module.py on 24 October 2026
without changing the code. CAPRI references are in the methods' docstrings."""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve  # noqa: F401
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple

from capri_mod.params import param, param_table
from capri_mod.settings import setting, current as _settings
from capri_mod.data.definitions import (
    MARKET_COMMODITIES, ALL_TRADE_REGIONS,
)
from capri_mod.data.definitions import MS_CODE
from capri_mod.market.equilibrium import MarketEquilibrium  # noqa: F401
from capri_mod.market.state import MarketStateMixin
from capri_mod.market.processing_ad import crush_function, crush_columns


class ProcessingMixin(MarketStateMixin):
    """MarketModule methods for processing demand (the normalised quadratic processing functions and oilseed crushing)."""


    # ------------------------------------------------------------------
    # Supply and demand responses
    # ------------------------------------------------------------------

    #: seed -> (oil, cake)
    CRUSH_CHAINS = {"RAPE": ("RAPO", "RAPC"), "SUNF": ("SUNO", "SUNC"), "SOYA": ("SOYO", "SOYC")}

    #: CAPRI's processing demand functions (arm/market_model.gms ProcNQ_; tools/build/build_processing_nq.py): oilseed
    #: crushing linear in the crushing margins with CAPRI's Hessian (cross terms among the oilseeds), processing of
    #: the other products linear in the prices (cross terms among the vegetable oils)
    #: products whose processing has its own block: dairy (fixed processing in the dairy block), biofuels (the
    #: biofuel market's non-fuel processing), raw milk
    _PROC_NQ_SKIP = frozenset({"MILK", "BUTR", "SKIM", "CHES", "WHEY", "FRMI", "CREM", "COCM", "WMIO", "CASE",
                               "BIOE", "BIOD"})

    def _proc_nq_params(self) -> dict:
        """CAPRI's processing Hessian summed per model region (the behavioural regions of a region share its prices),
        CAPRI's processing share of use per (region, commodity). {} when the files are absent."""
        cached = getattr(self, "_procnq_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            hh = inp.csv("processing_nq_hessian.csv", keep_default_na=False, na_values=[""])
            bb = inp.csv("processing_nq_base.csv", keep_default_na=False, na_values=[""])

            def mreg(rms, mr):
                if mr == "EU27":
                    return self.eu_region_of_ms(rms) or mr
                return mr
            # ProcNQ_ divides H by the price of the non-agricultural good, DATA(RMS,"PPri","Inpe","CUR")
            inpe_rms = bb.groupby("rms")["inpe"].first().to_dict()
            H, Ha, Hrms = {}, {}, {}
            # per behavioural region, scaled as Ha (H / INPE x ARM1P0 of the price's product): the dairy blocks' processing
            # (audit M9: ProcNQ_ per member state, its change entering FatsProtBal_)
            Harms = {}
            for r in hh.itertuples(index=False):
                R = mreg(r.rms, r.model_region)
                if R not in self.regions or r.x not in self.commodities or r.y not in self.commodities:
                    continue
                inpe = float(inpe_rms[r.rms])
                k = H.setdefault(R, {})
                ka = Ha.setdefault(R, {})
                kr = Hrms.setdefault(R, {}).setdefault(r.rms, {})
                k[(r.x, r.y)] = k.get((r.x, r.y), 0.0) + float(r.h) / inpe
                kr[(r.x, r.y)] = kr.get((r.x, r.y), 0.0) + float(r.h) / inpe
                # ProcNQ_ (market_model.gms l. 1140-1152): H x the change of v_arm1Price in the behavioural region's
                # market region, i.e. H x ARM1P0 x (Armington price ratio - 1)
                ka[(r.x, r.y)] = ka.get((r.x, r.y), 0.0) + float(r.h) / inpe * float(r.arm1p_y)
                kar = Harms.setdefault(r.rms, {})
                kar[(r.x, r.y)] = kar.get((r.x, r.y), 0.0) + float(r.h) / inpe * float(r.arm1p_y)
                if r.x != r.y:
                    kar[(r.y, r.x)] = kar.get((r.y, r.x), 0.0) + float(r.h) / inpe * float(r.arm1p_x)
                    k[(r.y, r.x)] = k.get((r.y, r.x), 0.0) + float(r.h) / inpe
                    kr[(r.y, r.x)] = kr.get((r.y, r.x), 0.0) + float(r.h) / inpe
                    ka[(r.y, r.x)] = ka.get((r.y, r.x), 0.0) + float(r.h) / inpe * float(r.arm1p_x)
            pr, us = {}, {}
            for r in bb.itertuples(index=False):
                R = mreg(r.rms, r.model_region)
                pr[(R, r.commodity)] = pr.get((R, r.commodity), 0.0) + float(r.proc_kt)
                us[(R, r.commodity)] = us.get((R, r.commodity), 0.0) + float(r.use_kt)
            # the share of use CAPRI's processing function carries (ProcNQ_ moves the processing quantity itself); at
            # most the whole use (where CAPRI's data have processing above use); before 23 October 2026 capped at 0.98
            share = {k: min(1.0, pr[k] / us[k]) for k in pr if us.get(k, 0.0) > 0 and pr[k] > 0}
            # crushing per behavioural region (processing_seeds.csv): the seed's base crush, oil and cake yields and
            # producer prices, the seed's Armington price, p_rhoProc
            sd = inp.csv("processing_seeds.csv")
            seeds = {}
            for r in sd.itertuples(index=False):
                R = mreg(r.rms, r.model_region)
                if R not in self.regions:
                    continue
                seeds.setdefault((R, r.seed), []).append(dict(
                    rms=r.rms, q0=float(r.proc_kt), yo0=float(r.prcy_oil), yc0=float(r.prcy_cake),
                    ppo=float(r.ppri_oil), ppc=float(r.ppri_cake), a1=float(r.arm1p_seed), rho=float(r.rho_proc)))
            out = {"H": H, "Ha": Ha, "Hrms": Hrms, "Harms": Harms, "share": share, "seeds": seeds}
        except Exception as exc:
            raise RuntimeError(f"market: the processing functions (ProcNQ_) could not be read ({exc!r})") from exc
        self._procnq_cache = out
        return out

    def _crush_params(self) -> dict:
        """(region, seed) -> base crush, yields, elasticity and base margin terms.

        CAPRI data of the market year (crushing_parameters_<year>.csv, tools/build/build_crushing_parameters.py, from
        CAPRI's market data of that year): crush = the seed's processing PROC, yields = CAPRI's PRCY, elasticity =
        p_ElasProc; with CAPRI's cake production as the crush (the bilateral market's override) the oils' base output
        is CAPRI's (ProcO_; until 30 October 2026 the yields were FAO_agg's base-period ones, K106). Every
        pair takes CAPRI's own yields, as CAPRI's market does: a band that dropped
        five pairs whose yields look implausible (UKR, PAK, ZAF rapeseed, PAK
        soybeans: oil + cake 1.2-1.7 t per t of seed crushed; JAP sunflower) was
        removed 23 October 2026 (no proxies; the numbers had no source).
        """
        # The cache is keyed on what it depends on - the BASE prices (world prices and CAPRI's market prices, the
        # reference levels since 4 November 2026; the aggregate tariffs before) of the oilseed-chain commodities. A plain cache built on first use
        # went stale when that use fell in a run with shifted base prices
        # (a long-lived model then disagreed with a fresh one: the projection
        # null-trajectory test caught a 0.04% difference).
        _cc = [c for c in ("RAPE", "SUNF", "SOYA", "RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")
               if c in self.commodities]
        try:
            _key = (tuple(round(float(self.world_prices_base.get(c, 0.0)), 9) for c in _cc),
                    tuple(map(tuple, self._reference_prices()[_cc].round(9).values.tolist())),
                    tuple(round(float((self.par.eu_aligned_use or {}).get(rg, {}).get(c, 0.0)), 6)
                          for rg in self.EU for c in ("RAPE", "SUNF", "SOYA")))
        except Exception:
            _key = None
        cached = getattr(self, "_crush_cache", None)
        if cached is not None and _key is not None and getattr(self, "_crush_cache_key", None) == _key:
            return cached
        self._crush_cache_key = _key
        out = {}
        _yr = self._market_year()
        _t = self._inp().csv(f"crushing_parameters_{_yr}.csv", keep_default_na=False)
        raw = {f"{x['region']}|{x['seed']}": {k: (float(x[k]) if x[k] != "" else None)
                                              for k in ("crush_kt", "oil_yield", "cake_yield", "elasticity",
                                                        "crush_share_of_use")}
               for x in _t.to_dict("records")}
        base_dom = self.domestic_prices(self.world_prices_base)
        for key, v in raw.items():
            r, s = key.split("|")
            if (r not in self.regions and r != "EU27") or s not in self.CRUSH_CHAINS:
                continue
            yo, yc = float(v["oil_yield"]), float(v["cake_yield"])
            o, c = self.CRUSH_CHAINS[s]
            q0 = float(v["crush_kt"])
            _ov = (self.par.crush_q0_override or {}).get((r, s))
            if _ov is not None:
                q0 = float(_ov)       # bilateral market: CAPRI's cake production of the market year / yield
            if r == "EU27":
                # CAPRI's two trade blocks: the EU parameters for each block, its crush share of seed use from
                # CAPRI's member-state processing and use (eu_ms_balance_2030.csv); base crush = share x the
                # block's aligned seed use (below)
                tb = self._eu_ms_balance()
                for rb in self.EU:
                    k = (rb, s)
                    if k not in tb.index or float(tb.at[k, "use_kt"]) <= 0:
                        continue
                    shb = float(tb.at[k, "proc_kt"]) / float(tb.at[k, "use_kt"])
                    _al = (self.par.eu_aligned_use or {}).get(rb, {})
                    bb = float(_al.get(s, self.par.base_consumption.at[rb, s] if s in self.par.base_consumption.columns else 0.0))
                    if shb <= 0 or bb <= 0:
                        continue
                    ps, po, pc = (float(base_dom.at[rb, x]) for x in (s, o, c))
                    gross = yo * po + yc * pc
                    out[(rb, s)] = dict(q0=shb * bb, yo=yo, yc=yc, eps=float(v["elasticity"]),
                                        m0=gross - ps, gross=max(gross, 1.0))
                continue
            ps, po, pc = (float(base_dom.at[r, x]) for x in (s, o, c))
            gross = yo * po + yc * pc               # CAPRI: seed price + margin
            out[(r, s)] = dict(q0=q0, yo=yo, yc=yc, eps=float(v["elasticity"]),
                               m0=gross - ps, gross=max(gross, 1.0))
        self._crush_cache = out
        return out

    def _align_eu_crush_products(self, base_supply):
        """EU oil and cake base production = EU base crush x yields.

        The EU base crush follows the market's own EU base seed use (CAPRI's
        crush share x that use), so EU oil and cake base production must follow
        it too - otherwise crushing supplies less (or more) than the market was
        calibrated on and base prices move (rapeseed oil +1.1% once the EU seed
        rows were put on CAPRI's FAO_agg basis).
        """
        cp = self._crush_params()
        tot = {}
        for (r, s), p in cp.items():
            if r not in self.EU:
                continue
            o, c = self.CRUSH_CHAINS[s]
            tot[(r, o)] = tot.get((r, o), 0.0) + p["q0"] * p["yo"]
            tot[(r, c)] = tot.get((r, c), 0.0) + p["q0"] * p["yc"]
        for (r, prod), v in tot.items():
            if prod in self.par.base_production.columns and v > 0:
                self.par.base_production.at[r, prod] = v
                if prod in base_supply.columns and r in base_supply.index:
                    base_supply.at[r, prod] = v
        return base_supply

    def _crush_state(self, dom_prices, detail: Optional[dict] = None) -> dict:
        """Crush and oil and cake output per (region, seed) at the given prices (CAPRI ProcMargO_, ProcNQ_,
        ProcFudge_, ProcO_, procYield_; market_model.gms l. 1118-1176, 1480-1520).

        Per behavioural region of the model region: the crushing margin of each seed is - ARM1P(seed) x its Armington
        price ratio + the oil's and the cake's PPRI x their producer price ratio x their CET yield; the crush moves
        from its base by the processing Hessian (cross terms among the oilseeds) times the change of the margins,
        made positive by ProcFudge_; output = crush x the CET yields. The price ratios are dom_prices over the base
        price levels (dom0): the seed's Armington ratio, the oil's and cake's producer price ratio (the caller sets
        their levels so; MarketModule._bilateral_eval). The model region's base crush (q0, CAPRI's, or the EU's
        aligned to the supply models) is spread over its behavioural regions by CAPRI's crush; a region-seed without a
        CAPRI Hessian term keeps its base crush (CAPRI: no processing function, constant processing).
        Returns {(region, seed): (crush, oil output, cake output)}. detail (a dict, for the welfare report): filled
        with {(region, seed, behavioural region): (base crush, crush change before ProcFudge_, margin change)}."""
        cp = self._crush_params()
        pq = self._proc_nq_params() or {}
        # the block's CasADi function (step G2e, processing_ad.py; until 31 October 2026 the same equations here in
        # Python with the CET yields of _cet_yields and _proc_fudge, both removed), rebuilt when the parameters change
        blk = getattr(self, "_crush_block", None)
        if blk is None or blk[0] is not cp or blk[1] is not pq:
            fn, regions, pairs, keys = crush_function(cp, pq.get("seeds", {}), pq.get("Hrms", {}), self.CRUSH_CHAINS)
            blk = self._crush_block = (cp, pq, fn, regions, pairs, keys)
        _, _, fn, regions, pairs, keys = blk
        if not pairs:
            return {}
        d0 = self._dom0()
        _ri = {r: i for i, r in enumerate(dom_prices.index)}
        _ci = {c: j for j, c in enumerate(dom_prices.columns)}
        _v = dom_prices.values
        _d0 = d0.reindex(index=dom_prices.index, columns=dom_prices.columns).values
        ratio = lambda r, x: float(_v[_ri[r], _ci[x]]) / float(_d0[_ri[r], _ci[x]]) if float(_d0[_ri[r], _ci[x]]) > 0 else 1.0
        cols = crush_columns(self.CRUSH_CHAINS)
        # the ratios the pairs with CAPRI entries use (a region's row is read only there; others: 1, unused)
        _used = {r for (r, s_) in pairs if pq.get("seeds", {}).get((r, s_))}
        rat = np.array([[ratio(r, x) if r in _used else 1.0 for x in cols] for r in regions], dtype=float)
        o_, d_ = fn(rat)
        o_, d_ = np.asarray(o_), np.asarray(d_)
        if detail is not None:
            for kk, key in enumerate(keys):
                r, s, rms = key
                e = next(x for x in pq["seeds"][(r, s)] if x["rms"] == rms)
                k = cp[(r, s)]["q0"] / sum(x["q0"] for x in pq["seeds"][(r, s)])
                detail[key] = (k * e["q0"], float(d_[kk, 0]), float(d_[kk, 1]))
        return {pr: (float(o_[n, 0]), float(o_[n, 1]), float(o_[n, 2])) for n, pr in enumerate(pairs)}

    def crush_quantities(self, dom_prices) -> dict:
        """Crush per (region, seed) at the given prices (_crush_state)."""
        return {k: v[0] for k, v in self._crush_state(dom_prices).items()}

    #: crushing products: their own-price supply response is the crushing margin's
    _CRUSH_PRODUCTS = ("RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")

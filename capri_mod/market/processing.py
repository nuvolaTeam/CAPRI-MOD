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


class ProcessingMixin:
    """MarketModule methods for processing demand (the normalised quadratic processing functions and oilseed crushing)."""


    # ------------------------------------------------------------------
    # Supply and demand responses
    # ------------------------------------------------------------------

    #: seed -> (oil, cake)
    CRUSH_CHAINS = {"RAPE": ("RAPO", "RAPC"), "SUNF": ("SUNO", "SUNC"), "SOYA": ("SOYO", "SOYC")}

    #: CAPRI's processing demand functions (arm/market_model.gms ProcNQ_; tools/build/build_processing_nq.py): oilseed
    #: crushing linear in the crushing margins with CAPRI's Hessian (cross terms among the oilseeds), processing of
    #: the other products linear in the prices (cross terms among the vegetable oils). False: the earlier own-margin
    #: crushing elasticity and own-price response of processing.
    processing_nq = setting("market.processing_nq")
    #: products whose processing has its own block: dairy (fixed processing in the dairy block), biofuels (the
    #: biofuel market's non-fuel processing), raw milk
    _PROC_NQ_SKIP = frozenset({"MILK", "BUTR", "SKIM", "CHES", "WHEY", "FRMI", "CREM", "COCM", "WMIO", "CASE",
                               "BIOE", "BIOD"})

    def _proc_nq_params(self) -> dict:
        """CAPRI's processing Hessian summed per model region (the behavioural regions of a region share its prices),
        CAPRI's processing share of use per (region, commodity). {} when off or the files are absent."""
        if not self.processing_nq:
            return {}
        cached = getattr(self, "_procnq_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            hh = inp.csv("processing_nq_hessian.csv", keep_default_na=False, na_values=[""])
            bb = inp.csv("processing_nq_base.csv", keep_default_na=False, na_values=[""])

            def mreg(rms, mr):
                if mr == "EU27" and self.eu_blocks:
                    return self.eu_region_of_ms(rms) or mr
                return mr
            # ProcNQ_ divides H by the price of the non-agricultural good, DATA(RMS,"PPri","Inpe","CUR")
            inpe_rms = bb.groupby("rms")["inpe"].first().to_dict()
            H, Ha, Hrms = {}, {}, {}
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
                if r.x != r.y:
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
            out = {"H": H, "Ha": Ha, "Hrms": Hrms, "share": share, "seeds": seeds}
        except Exception as exc:
            raise RuntimeError(f"market: the processing functions (ProcNQ_) could not be read ({exc!r})") from exc
        self._procnq_cache = out
        return out

    def _crush_params(self) -> dict:
        """(region, seed) -> base crush, yields, elasticity and base margin terms.

        CAPRI data (crushing_parameters.csv, tools/build/build_crushing_parameters.py): crush = the seed's industrial use,
        yields = oil and cake production / crush, elasticity = p_ElasProc. Every
        pair takes CAPRI's own yields, as CAPRI's market does: a band that dropped
        five pairs whose yields look implausible (UKR, PAK, ZAF rapeseed, PAK
        soybeans: oil + cake 1.2-1.7 t per t of seed crushed; JPN sunflower) was
        removed 23 October 2026 (no proxies; the numbers had no source).
        """
        # The cache is keyed on what it depends on - the BASE prices and tariffs
        # of the oilseed-chain commodities. A plain cache built on first use
        # went stale when that use fell in a run with shifted base prices
        # (a long-lived model then disagreed with a fresh one: the projection
        # null-trajectory test caught a 0.04% difference).
        _cc = [c for c in ("RAPE", "SUNF", "SOYA", "RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")
               if c in self.commodities]
        try:
            _key = (tuple(round(float(self.world_prices_base.get(c, 0.0)), 9) for c in _cc),
                    tuple(map(tuple, self.tariffs.reindex(columns=_cc).fillna(0.0).round(9).values.tolist())),
                    tuple(round(float((getattr(self, "_eu_aligned_use", None) or {}).get(rg, {}).get(c, 0.0)), 6)
                          for rg in self.EU for c in ("RAPE", "SUNF", "SOYA")))
        except Exception:
            _key = None
        cached = getattr(self, "_crush_cache", None)
        if cached is not None and _key is not None and getattr(self, "_crush_cache_key", None) == _key:
            return cached
        self._crush_cache_key = _key
        out = {}
        _t = self._inp().csv("crushing_parameters.csv", keep_default_na=False)
        raw = {f"{x['region']}|{x['seed']}": {k: (float(x[k]) if x[k] != "" else None)
                                              for k in ("crush_kt", "oil_yield", "cake_yield", "elasticity",
                                                        "crush_share_of_use")}
               for x in _t.to_dict("records")}
        base_dom = self.domestic_prices(self.world_prices_base)
        for key, v in raw.items():
            r, s = key.split("|")
            if (r not in self.regions and not (r == "EU27" and self.eu_blocks)) or s not in self.CRUSH_CHAINS:
                continue
            yo, yc = float(v["oil_yield"]), float(v["cake_yield"])
            o, c = self.CRUSH_CHAINS[s]
            q0 = float(v["crush_kt"])
            _ov = (getattr(self, "_crush_q0_override", None) or {}).get((r, s))
            if _ov is not None:
                q0 = float(_ov)       # bilateral market: CAPRI's cake production of the market year / yield
            if r == "EU27" and self.eu_blocks:
                # CAPRI's two trade blocks: the EU parameters for each block, its crush share of seed use from
                # CAPRI's member-state processing and use (eu_ms_balance_2030.csv); base crush = share x the
                # block's aligned seed use (below)
                tb = self._eu_ms_balance()
                for rb in self.EU:
                    k = (rb, s)
                    if k not in tb.index or float(tb.at[k, "use_kt"]) <= 0:
                        continue
                    shb = float(tb.at[k, "proc_kt"]) / float(tb.at[k, "use_kt"])
                    _al = (getattr(self, "_eu_aligned_use", None) or {}).get(rb, {})
                    bb = float(_al.get(s, self.base_consumption.at[rb, s] if s in self.base_consumption.columns else 0.0))
                    if shb <= 0 or bb <= 0:
                        continue
                    ps, po, pc = (float(base_dom.at[rb, x]) for x in (s, o, c))
                    gross = yo * po + yc * pc
                    out[(rb, s)] = dict(q0=shb * bb, yo=yo, yc=yc, eps=float(v["elasticity"]),
                                        m0=gross - ps, gross=max(gross, 1.0))
                continue
            if r == "EU27":
                # EU base crush = CAPRI's crush SHARE of EU seed use x the
                # market's own EU base seed use. With all regions modelled
                # this equals CAPRI's crush exactly; with a subset it scales
                # consistently (on 12 regions EU rapeseed use is 581 kt -
                # a fixed 20,955 kt crush made non-crush use negative).
                share = float(v.get("crush_share_of_use") or 0.0)
                # the ALIGNED EU seed use: base_consumption is later divided
                # by the calibration factor (EU exemption), which shifted the
                # base crush after calibration and moved base prices
                _al = (getattr(self, "_eu_aligned_use", None) or {}).get("EU27", {})
                b = float(_al.get(s, self.base_consumption.at["EU27", s] if s in self.base_consumption.columns else 0.0))
                if share > 0 and b > 0:
                    q0 = share * b
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
            if prod in self.base_production.columns and v > 0:
                self.base_production.at[r, prod] = v
                if prod in base_supply.columns and r in base_supply.index:
                    base_supply.at[r, prod] = v
        return base_supply

    @staticmethod
    def _cet_yields(e: dict, ro: float, rc: float):
        """Oil and cake yields of one behavioural region at producer price ratios ro (oil) and rc (cake) to the
        calibration point (CAPRI procYield_, market_model.gms l. 1480-1520): each yield is its calibration value times
        the CET term (relative price ratio)^p_rhoProc, both corrected by half of the mass-balance error; the two
        equations solved together (closed form)."""
        po, pc = e["ppo"] * ro, e["ppc"] * rc
        lo = np.log(((po + 1e-3) / (e["ppo"] + 1e-3)) / ((pc + 1e-3) / (e["ppc"] + 1e-3)))
        Ao = e["yo0"] * np.exp(e["rho"] * lo)
        Ac = e["yc0"] * np.exp(-e["rho"] * lo)
        S0 = e["yo0"] + e["yc0"]
        T = (Ao + Ac + S0) / 2.0
        return Ao + (S0 - T) / 2.0, Ac + (S0 - T) / 2.0

    @staticmethod
    def _proc_fudge(q: float, q0: float) -> float:
        """CAPRI ProcFudge_ (market_model.gms l. 1158-1163): v_procQuant = -ncpcm(-q, 0, z) + 1e-11 with
        z = 0.01 x min(1000, max(1e-11, PROC0)), i.e. a smooth max(q, 0) (ncpcm(x, y, z) = x - z ln(1 + exp((x - y)/z)))."""
        z = 0.01 * min(1000.0, max(1e-11, float(q0)))
        return float(q + z * np.logaddexp(0.0, -q / z) + 1e-11)

    def _crush_state(self, dom_prices) -> dict:
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
        Returns {(region, seed): (crush, oil output, cake output)}."""
        cp = self._crush_params()
        pq = self._proc_nq_params() or {}
        seeds = pq.get("seeds", {})
        Hrms = pq.get("Hrms", {})
        d0 = self._dom0()
        _ri = {r: i for i, r in enumerate(dom_prices.index)}
        _ci = {c: j for j, c in enumerate(dom_prices.columns)}
        _v = dom_prices.values
        _d0 = d0.reindex(index=dom_prices.index, columns=dom_prices.columns).values
        ratio = lambda r, x: float(_v[_ri[r], _ci[x]]) / float(_d0[_ri[r], _ci[x]]) if float(_d0[_ri[r], _ci[x]]) > 0 else 1.0
        out = {}
        for (r, s), p in cp.items():
            o, c = self.CRUSH_CHAINS[s]
            ents = seeds.get((r, s), [])
            if not ents:
                out[(r, s)] = (p["q0"], p["q0"] * p["yo"], p["q0"] * p["yc"])
                continue
            k = p["q0"] / sum(e["q0"] for e in ents)          # the model region's base crush over CAPRI's
            crush = oil = cake = oil0 = cake0 = 0.0
            for e in ents:
                Hr = Hrms.get(r, {}).get(e["rms"], {})
                q = k * e["q0"]
                for y in self.CRUSH_CHAINS:
                    h = Hr.get((s, y), 0.0)
                    if h == 0.0:
                        continue
                    ey = next((x for x in seeds.get((r, y), []) if x["rms"] == e["rms"]), None)
                    if ey is None:
                        continue
                    oy, cy = self.CRUSH_CHAINS[y]
                    yo, yc = self._cet_yields(ey, ratio(r, oy), ratio(r, cy))
                    m = -ey["a1"] * ratio(r, y) + ey["ppo"] * ratio(r, oy) * yo + ey["ppc"] * ratio(r, cy) * yc
                    m0 = -ey["a1"] + ey["ppo"] * ey["yo0"] + ey["ppc"] * ey["yc0"]
                    q += h * (m - m0)
                q = self._proc_fudge(q, k * e["q0"])
                yo, yc = self._cet_yields(e, ratio(r, o), ratio(r, c))
                crush += q
                oil += q * yo
                cake += q * yc
                oil0 += k * e["q0"] * e["yo0"]
                cake0 += k * e["q0"] * e["yc0"]
            # output in the model region's base (crush x its yields), moved by CAPRI's per-region output change
            out[(r, s)] = (crush, p["q0"] * p["yo"] * (oil / oil0 if oil0 > 0 else 1.0),
                           p["q0"] * p["yc"] * (cake / cake0 if cake0 > 0 else 1.0))
        return out

    def crush_quantities(self, dom_prices) -> dict:
        """Crush per (region, seed) at the given prices (_crush_state)."""
        return {k: v[0] for k, v in self._crush_state(dom_prices).items()}

    #: crushing products: their own-price supply response is the crushing margin's
    _CRUSH_PRODUCTS = ("RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC")

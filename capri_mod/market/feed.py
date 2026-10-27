"""MarketModule: feed demand (the EU feed bulks per member state, the residual feeds FENI and FPRI, non-EU feed demand).

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


class FeedMixin(MarketStateMixin):
    """MarketModule methods for feed demand (the EU feed bulks per member state, the residual feeds FENI and FPRI, non-EU feed demand)."""


    def _feed_bulk_params(self) -> dict:
        """CAPRI's feed bulks of the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_;
        tools/build/build_feed_bulks.py): per (member state, bulk) the products' model commodities, 2030 feed quantities,
        value shares and the substitution elasticity; the feed share of EU use per commodity and the EU feed
        totals. {} when the files are absent."""
        cached = getattr(self, "_fbulk_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            f = inp.csv("feed_bulks_eu.csv", keep_default_na=False)
            sh = inp.csv("feed_bulks_eu_share.csv")
            bulks = {}
            for (ms, b), g in f.groupby(["ms", "bulk"], sort=True):
                q0 = g["feed_kt"].astype(float).values
                v0 = q0 * g["arm1p"].astype(float).values
                comm = [c if c in self.commodities else "" for c in g["commodity"].astype(str)]
                bulks[(ms, b)] = dict(comm=comm, q0=q0, s=v0 / v0.sum(), rho=float(g["rho"].iloc[0]))
            feed0, feed0_reg = {}, {r: {} for r in self.EU}
            for (ms, b), d in bulks.items():
                reg = self.eu_region_of_ms(ms)
                for c, q in zip(d["comm"], d["q0"]):
                    if c:
                        feed0[c] = feed0.get(c, 0.0) + float(q)
                        if reg in feed0_reg:
                            feed0_reg[reg][c] = feed0_reg[reg].get(c, 0.0) + float(q)
            share = {str(r.commodity): float(r.share) for r in sh.itertuples()
                     if r.commodity in self.commodities and r.commodity in feed0}
            # per EU market region: the region's feed over its use, the EU use (file) split by CAPRI's member-state
            # use (eu_split); one EU region: the file's share
            use_eu = {str(r.commodity): float(r.use_kt) for r in sh.itertuples()}
            share_reg = {}
            for reg in self.EU:
                share_reg[reg] = {}
                for c, sh_ in share.items():
                    if not self.eu_blocks:
                        share_reg[reg][c] = sh_
                        continue
                    u = use_eu.get(c, 0.0) * self.eu_split(c)[reg]
                    f = feed0_reg[reg].get(c, 0.0)
                    if u > 0 and f > 0:
                        share_reg[reg][c] = min(1.0, f / u)
            out = {"bulks": bulks, "feed0": feed0, "share": share, "feed0_reg": feed0_reg,
                   "share_reg": share_reg} if bulks else {}
            # Norway's bulks (CAPRI's feedBlkPrice_, feedShareEqu_ hold for every NUTS0 with supply models, RMSSUP):
            # its supply models' bulk price indices at its own market's prices, and its feed demand per product
            # following its herds, in its own market region NOR (KNOWN_ISSUES K56; not part of the EU's feed demand).
            # The feed share of Norway's use per commodity: CAPRI's 2030 feed over its use (HCOM + FEDM + INDM + BIOF
            # + LOSM + PRCM, feed_bulks_no.csv use_kt), as the EU's (feed_bulks_eu_share.csv)
            if out and inp.exists("feed_bulks_no.csv"):
                pno, f0s, u0s, ms_reg = {}, {}, {}, {v: k for k, v in self.SUP_NONEU_MS.items()}
                tno = inp.csv("feed_bulks_no.csv", keep_default_na=False)
                for (ms, b), g in tno.groupby(["ms", "bulk"], sort=True):
                    q0 = g["feed_kt"].astype(float).values
                    v0 = q0 * g["arm1p"].astype(float).values
                    comm = [c if c in self.commodities else "" for c in g["commodity"].astype(str)]
                    pno[(ms, b)] = dict(comm=comm, q0=q0, s=v0 / v0.sum(), rho=float(g["rho"].iloc[0]))
                    rg = ms_reg.get(ms)
                    uk = g["use_kt"].astype(float).values if "use_kt" in g.columns else np.zeros(len(g))
                    for c, q, u in zip(comm, q0, uk):
                        if c and rg is not None:
                            f0s.setdefault(rg, {})[c] = f0s.setdefault(rg, {}).get(c, 0.0) + float(q)
                            u0s.setdefault(rg, {})[c] = u0s.setdefault(rg, {}).get(c, 0.0) + float(u)
                out["bulks_sup"] = pno
                out["feed0_sup"] = f0s
                out["share_sup"] = {rg: {c: min(1.0, q / u0s[rg][c]) for c, q in f0.items() if u0s[rg].get(c, 0.0) > 0}
                                    for rg, f0 in f0s.items()}
        except Exception as exc:
            raise RuntimeError(f"market: the EU feed bulk inputs could not be read ({exc!r})") from exc
        self._fbulk_cache = out
        return out

    def feed_bulk_price_ratio(self, ms: str, bulk: str, price_ratio: Dict[str, float]) -> float:
        """CAPRI's bulk price index (feedBlkPrice_) of a member state relative to the reference:
        (sum_i s_i (p_i / p_i0)^(1 - rho))^(1 / (1 - rho)), s_i the reference value shares; products without a
        model market at the reference price. 1 where the member state has no such bulk."""
        fb = self._feed_bulk_params()
        d = (fb.get("bulks") or {}).get((ms, bulk)) or (fb.get("bulks_sup") or {}).get((ms, bulk))
        if d is None:
            return 1.0
        r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
        rho = d["rho"]
        return float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))

    def eu_feed_use(self, price_ratio: Dict[str, float], region: Optional[str] = None) -> Dict[str, float]:
        """EU feed use per model commodity (kt) from the member states' bulks at the EU price ratios (CAPRI
        feedShareEqu_): q_i = q_i0 x (B / B0) x (P_B / p_i)^rho with prices relative to the reference; B / B0 from
        the supply models (_feed_bulk_index, 1 before any supply result). region: only the member states of that
        EU market region (their block's prices)."""
        fb = self._feed_bulk_params()
        bix = getattr(self, "_feed_bulk_index", None) or {}
        out = {}
        for (ms, b), d in (fb.get("bulks") or {}).items():
            if region is not None and self.eu_region_of_ms(ms) != region:
                continue
            r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
            rho = d["rho"]
            pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
            q = d["q0"] * float(bix.get((ms, b), 1.0)) * (pb / r) ** rho
            for c, x in zip(d["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def sup_feed_use(self, region: str, price_ratio: Dict[str, float]) -> Dict[str, float]:
        """Feed use per model commodity (kt) of a non-EU market region with supply models (Norway) from its bulks
        at its price ratios (CAPRI feedShareEqu_, as eu_feed_use): q_i = q_i0 x (B / B0) x (P_B / p_i)^rho, B / B0
        from its supply models (_feed_bulk_index)."""
        fb = self._feed_bulk_params()
        bix = getattr(self, "_feed_bulk_index", None) or {}
        ms0 = self.SUP_NONEU_MS.get(region)
        out = {}
        for (ms, b), d in (fb.get("bulks_sup") or {}).items():
            if ms != ms0:
                continue
            r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
            rho = d["rho"]
            pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
            q = d["q0"] * float(bix.get((ms, b), 1.0)) * (pb / r) ** rho
            for c, x in zip(d["comm"], q):
                if c:
                    out[c] = out.get(c, 0.0) + float(x)
        return out

    def _feed_byproduct_params(self) -> dict:
        """CAPRI's residual feeds (MaprFeed_; tools/build/build_feed_byproducts.py): per product the EU's 2030 output and
        its parent commodities' weights in the parents' food and processing use (food) or biofuel processing.
        {"products": {product: {"prod0": kt, "parts": [(commodity, use, weight)]}}, "parents": set} or {}."""
        cached = getattr(self, "_fbyp_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            t = self._inp().csv("feed_byproducts.csv")
            prods = {}
            for p, g in t.groupby("product"):
                if p not in self.commodities:
                    continue
                ws = float(g["weight"].sum())                 # renormalised (the file's weights are rounded)
                prods[p] = {"prod0": float(g["prod0_kt"].iloc[0]),
                            "parts": [(str(r.commodity), str(r.use), float(r.weight) / ws) for r in g.itertuples()]}
                # per EU market region: output split by CAPRI's member-state production of the residual feed; the
                # parents' weights from the region's own food + processing (biofuel processing) use of each parent
                reg = {}
                for rg, f in self.eu_split(p, "prod_kt").items():
                    if not self.eu_blocks:
                        reg[rg] = {"prod0": prods[p]["prod0"], "parts": prods[p]["parts"]}
                        continue
                    parts = []
                    for r_ in g.itertuples():
                        it = ("biof_kt",) if str(r_.use) == "biofuel" else ("hcon_kt", "proc_kt")
                        tb = self._eu_ms_balance()
                        k = (rg, str(r_.commodity))
                        vb = sum(float(tb.at[k, x]) for x in it) if k in tb.index else 0.0
                        parts.append((str(r_.commodity), str(r_.use), vb))
                    tot = sum(x for _, _, x in parts)
                    reg[rg] = {"prod0": prods[p]["prod0"] * f,
                               "parts": [(c, u, x / tot) for c, u, x in parts] if tot > 0 else prods[p]["parts"]}
                prods[p]["reg"] = reg
            if prods:
                out = {"products": prods,
                       "parents": {c for d in prods.values() for c, _, _ in d["parts"] if c in self.commodities}}
        except Exception as exc:
            raise RuntimeError(f"market: the residual feed inputs could not be read ({exc!r})") from exc
        self._fbyp_cache = out
        return out

    def eu_feed_byproduct_output(self, region: Optional[str] = None) -> Dict[str, float]:
        """EU output of the residual feeds (CAPRI MaprFeed_): prod0 x sum over the parents of weight x the
        parent's current food response (food and processing use) or biofuel feedstock use relative to the
        reference, from the last demand evaluation (1 before any). region: one EU market region (default: the
        first; with one EU region, the EU)."""
        region = region or self.EU[0]
        fp = self._feed_byproduct_params()
        fr = (self.ev.eu_food_ratio or {}).get(region, {})
        br = (self.ev.eu_biof_ratio or {}).get(region, {})
        out = {}
        for p, d in (fp.get("products") or {}).items():
            dr = (d.get("reg") or {}).get(region, d)
            x = sum(w * float((br if use == "biofuel" else fr).get(c, 1.0)) for c, use, w in dr["parts"])
            out[p] = dr["prod0"] * x
        return out

    def _apply_feed_byproduct_supply(self, S: pd.DataFrame) -> None:
        for reg in self.EU:
            if reg not in S.index:
                continue
            for p, q in self.eu_feed_byproduct_output(reg).items():
                if p in S.columns:
                    S.at[reg, p] = max(0.0, q)

    def _feed_demand_params(self) -> dict:
        """(region, feed commodity) -> feed share and p_ElasFeed elasticities (non-EU)."""
        cached = getattr(self, "_fdp_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            for key, v in self._inp().json("feed_demand_nonEU.json")["parameters"].items():
                r, c = key.split("|")
                if r in self.regions and r not in self.EU and r != "EU27" and c in self.commodities:
                    out[(r, c)] = {"feed_share": float(v["feed_share"]),
                                   "elasticities": {k: float(x) for k, x in v["elasticities"].items() if k in self.commodities}}
        except Exception as exc:
            raise RuntimeError(f"market: the non-EU feed demand inputs could not be read ({exc!r})") from exc
        self._fdp_cache = out
        return out

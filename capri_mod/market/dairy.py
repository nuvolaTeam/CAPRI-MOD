"""MarketModule: the dairy block (raw milk to the nine dairy products by fat and protein; EU member states and the non-EU dairy regions).

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


class DairyMixin:
    """MarketModule methods for the dairy block (raw milk to the nine dairy products by fat and protein; EU member states and the non-EU dairy regions)."""


    # ------------------------------------------------------------------
    # DAIRY PROCESSING (CAPRI arm/market_model.gms DairyNQ_, ProcMargM_, FatsProtBal_)
    # ------------------------------------------------------------------
    #: CAPRI dairy product -> market commodity. CAPRI trades all nine products of its dairy block bilaterally
    #: (Sprint 9f; until then fresh milk products, cream, concentrated milk, whole milk powder and casein cleared
    #: inside each block with fixed extra-regional trade)
    DAIRY_TRADED = {"BUTT": "BUTR", "SMIP": "SKIM", "CHES": "CHES", "WHEP": "WHEY", "FRMI": "FRMI", "CREM": "CREM",
                    "COCM": "COCM", "WMIO": "WMIO", "CASE": "CASE"}
    DAIRY_PRODUCTS = ("BUTT", "SMIP", "CHES", "FRMI", "CREM", "COCM", "WMIO", "CASE", "WHEP")
    #: products cleared inside a block (none since Sprint 9f; the block's algebra keeps the option)
    DAIRY_DOMESTIC = ()

    #: CAPRI's dairy processing in the market (docs/DAIRY_PROCESSING.md): on, as in CAPRI, where the dairy
    #: block is part of the market model (no switch). Since Sprint 9f all nine dairy products are traded and raw
    #: milk, fat and protein are priced per member state. False: dairy products as fixed CAPRI yields of milk.
    use_dairy_block = setting("market.use_dairy_block")

    def _dairy_algebra(self, tables):
        """CAPRI's dairy block as linear algebra for a set of regions that share price RATIOS.

        tables: iterable of (gi, H, milksup): gi = the region's rows indexed by item (the nine products and
        MILK with q_kt, proc_kt, fats_pct, prot_pct, price; INPE, FATS, PROT with their prices), H = {(row, col):
        h} its symmetric Hessian with the MILK row reversed, milksup = its raw milk supply slope
        (p_hessNQSupp MILK, or None where raw milk supply comes from outside: the EU's supply models).
        With z = (rho_k - 1 for the nine products, rho_MILK - 1, phi_fat - 1, phi_prot - 1):
            dm_s = Mm_s z  (ProcMargM_),  dQ_s = H_s dm_s / INPE_s = G_s z  (DairyNQ_),
        G = sum_s G_s; the fat and protein rows of FatsProtBal_; SM = raw milk supply per unit z_MILK."""
        items = list(self.DAIRY_PRODUCTS) + ["MILK"]
        ix = {k: i for i, k in enumerate(items)}
        nz = len(items) + 2
        iF, iP, iM = len(items), len(items) + 1, ix["MILK"]
        G = np.zeros((len(items), nz)); rowF = np.zeros(nz); rowP = np.zeros(nz)
        Q0 = np.zeros(len(items)); proc0 = np.zeros(len(items)); PQ = np.zeros(len(items)); SM = 0.0
        for gi, Hd, msup in tables:
            if "MILK" not in gi.index:
                continue
            inpe = float(gi.at["INPE", "price"]); pf0 = float(gi.at["FATS", "price"])
            pp0 = float(gi.at["PROT", "price"])
            Mm = np.zeros((len(items), nz)); f = np.zeros(len(items)); r = np.zeros(len(items))
            for k in items:
                if k not in gi.index or not float(gi.at[k, "q_kt"]) > 0:
                    continue
                i = ix[k]
                f[i], r[i] = float(gi.at[k, "fats_pct"]), float(gi.at[k, "prot_pct"])
                Mm[i, i] = float(gi.at[k, "price"])
                Mm[i, iF] = -f[i] * pf0
                Mm[i, iP] = -r[i] * pp0
                Q0[i] += float(gi.at[k, "q_kt"])
                PQ[i] += float(gi.at[k, "q_kt"]) * float(gi.at[k, "price"])
                pc = gi.at[k, "proc_kt"]
                proc0[i] += float(pc) if pd.notna(pc) else 0.0
            H = np.zeros((len(items), len(items)))
            for (rw, cl), h in Hd.items():
                if rw in ix and cl in ix:
                    H[ix[rw], ix[cl]] = float(h)
            Gs = H @ Mm / inpe
            G += Gs
            sgn = -np.ones(len(items)); sgn[iM] = 1.0                 # milk in, products out
            rowF += (sgn * f) @ Gs
            rowP += (sgn * r) @ Gs
            if msup is not None:
                SM += float(msup) * float(gi.at["MILK", "price"]) / inpe
        P9 = list(self.DAIRY_PRODUCTS)
        return dict(items=items, ix=ix, G=G, rowF=rowF, rowP=rowP, Q0=Q0, proc0=proc0, iF=iF, iP=iP, iM=iM,
                    dom=[ix[k] for k in self.DAIRY_DOMESTIC if Q0[ix[k]] > 0], SM=SM,
                    p9=np.array([PQ[ix[k]] / Q0[ix[k]] if Q0[ix[k]] > 0 else 1.0 for k in P9]))

    def _dairy_params(self) -> dict:
        """The EU dairy block (tools/build/build_dairy_processing.py): CAPRI's three equations (DairyNQ_, ProcMargM_,
        FatsProtBal_) with one block per member state, raw milk, fat and protein priced per member state as in
        CAPRI, the nine products at their EU market region's prices and traded bilaterally; raw milk delivered
        from the EU supply models; food demand among the nine products with CAPRI's own and cross elasticities;
        feed demand through the FMIL block."""
        if not self.use_dairy_block:
            return {}
        cached = getattr(self, "_dairy_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            dp = inp.csv("dairy_processing.csv")
            hh = inp.csv("dairy_hessian.csv")
            bal = inp.csv("dairy_eu_balance.csv").set_index("product")
            tables = [(g.set_index("item"), {(e.row, e.col): e.h for e in hh[hh.ms == ms].itertuples()}, None)
                      for ms, g in dp.groupby("ms")]
            out = self._dairy_algebra(tables)
            # CAPRI clears raw milk, milk fat and protein per member state (FatsProtBal_, ProcMargM_, DairyNQ_ per
            # RMS; raw milk is not traded): one block per member state, the products at their EU prices
            out["ms"] = {ms: self._dairy_algebra([tb]) for ms, tb in zip([m for m, _ in dp.groupby("ms")], tables)}
            out["ms"] = {ms: a for ms, a in out["ms"].items() if a["Q0"][a["iM"]] > 0}
            P9 = list(self.DAIRY_PRODUCTS)
            Em = np.zeros((9, 9))
            if inp.exists("dairy_eu_demand_elas.csv"):
                for r_ in inp.csv("dairy_eu_demand_elas.csv").itertuples():
                    if r_.row in P9 and r_.col in P9:
                        Em[P9.index(r_.row), P9.index(r_.col)] = float(r_.elas)
            else:
                for k in self.DAIRY_DOMESTIC:
                    Em[P9.index(k), P9.index(k)] = float(bal.at[k, "eta_hcom"])
            out.update(E=Em, hc9=np.array([float(bal.at[k, "hcom_kt"]) for k in P9]),
                       fd9=np.array([float(bal.at[k, "fedm_kt"]) for k in P9]),
                       cons9={k: float(bal.at[k, "prod_kt"] - bal.at[k, "proc_kt"] + bal.at[k, "net_imports_kt"]) for k in P9},
                       net_imports0={k: float(bal.at[k, "net_imports_kt"]) for k in P9})
            # per EU market region: output and processing of its member states' blocks; food and feed use and total
            # use the EU's split by CAPRI's member-state human consumption, feed and use; net imports the rest
            reg = {}
            for rg in self.EU:
                if not self.eu_blocks:
                    reg[rg] = dict(Q0=out["Q0"], proc0=out["proc0"], hc9=out["hc9"], fd9=out["fd9"],
                                   cons9=out["cons9"], net_imports0=out["net_imports0"])
                    continue
                mss = [ms for ms in out["ms"] if self.eu_region_of_ms(ms) == rg]
                Q0 = sum((out["ms"][ms]["Q0"] for ms in mss), np.zeros_like(out["Q0"]))
                pr0 = sum((out["ms"][ms]["proc0"] for ms in mss), np.zeros_like(out["proc0"]))
                cm = {k: self.DAIRY_TRADED[k] for k in P9}
                hc = np.array([out["hc9"][i] * self.eu_split(cm[k], "hcon_kt")[rg] for i, k in enumerate(P9)])
                fd = np.array([out["fd9"][i] * self.eu_split(cm[k], "feed_kt")[rg] for i, k in enumerate(P9)])
                cons = {k: out["cons9"][k] * self.eu_split(cm[k], "use_kt")[rg] for k in P9}
                ix = out["ix"]
                ni = {k: cons[k] - float(Q0[ix[k]] - pr0[ix[k]]) for k in P9}
                reg[rg] = dict(Q0=Q0, proc0=pr0, hc9=hc, fd9=fd, cons9=cons, net_imports0=ni)
            out["reg"] = reg
        except Exception as exc:
            raise RuntimeError(f"market: the EU dairy block inputs could not be read ({exc!r})") from exc
        self._dairy_cache = out
        return out

    def _dairy_world_params(self) -> dict:
        """CAPRI's dairy block for the non-EU trade regions (dairy Stage 4, tools/build/build_dairy_world_blocks.py):
        {trade region: params}, CAPRI's market regions of the trade region sharing price ratios; raw milk from
        CAPRI's own supply function (p_hessNQSupp MILK); food demand among the nine products with the
        regions' p_ElasDem weighted by food use; feed use of the products at CAPRI's level (FMIL index 1: the
        model has no non-EU herds), with the CES price term; extra-regional trade of the five non-traded
        products fixed."""
        if not self.use_dairy_block:
            return {}
        cached = getattr(self, "_dairy_world_cache", None)
        if cached is not None:
            return cached
        out = {}
        try:
            inp = self._inp()
            wp = inp.csv("dairy_world_processing.csv")
            hh = inp.csv("dairy_world_hessian.csv")
            ee = inp.csv("dairy_world_demand_elas.csv")
            P9 = list(self.DAIRY_PRODUCTS)
            for tr, gt in wp.groupby("trade_region"):
                if tr not in self.regions or tr == "EU27":
                    continue
                tables, hc, fd = [], np.zeros(9), np.zeros(9)
                Enum, Ew = np.zeros((9, 9)), np.zeros(9)
                for rms, g in gt.groupby("rms"):
                    gi = g.set_index("item")
                    ms_ = float(gi.at["MILKSUP", "price"]) if "MILKSUP" in gi.index else 0.0
                    tables.append((gi, {(e.row, e.col): e.h for e in hh[hh.rms == rms].itertuples()}, ms_))
                    for k in P9:
                        if k in gi.index:
                            h_ = float(gi.at[k, "hcon_kt"] or 0.0); hc[P9.index(k)] += h_
                            fd[P9.index(k)] += float(gi.at[k, "feed_kt"] or 0.0)
                            if h_ > 0:
                                Ew[P9.index(k)] += h_
                                for e in ee[(ee.rms == rms) & (ee.row == k)].itertuples():
                                    if e.col in P9:
                                        Enum[P9.index(k), P9.index(e.col)] += h_ * float(e.elas)
                prm = self._dairy_algebra(tables)
                E = np.where(Ew[:, None] > 0, Enum / np.maximum(Ew[:, None], 1e-12), 0.0)
                prm.update(E=E, hc9=hc, fd9=fd)
                if prm["Q0"][prm["iM"]] > 0 and prm["SM"] > 0:
                    out[tr] = prm
        except Exception as exc:
            raise RuntimeError(f"market: the non-EU dairy block inputs could not be read ({exc!r})") from exc
        self._dairy_world_cache = out
        return out

    def _dairy_solve(self, dp, traded_ratio, milk_ratio=None, fi=1.0, key="EU27"):
        """Solve one dairy block. Unknowns: fat, protein and raw milk price ratios, and the prices of the products
        that clear inside the block (DAIRY_DOMESTIC; none since Sprint 9f: all nine products are traded
        bilaterally, so their prices are given and this set is empty). Equations: fat and protein balances
        (FatsProtBal_); raw milk: dairies' demand = milk delivered (milk_ratio given: the EU) or = CAPRI's raw milk
        supply function (milk_ratio None); for a product clearing inside the block: supply - fixed processing +
        fixed extra-regional net imports = food demand (own and cross p_ElasDem) + feed demand (FMIL index x CES
        0.5)."""
        G, n = dp["G"], len(dp["items"]) + 2
        iF, iP, iM, dom = dp["iF"], dp["iP"], dp["iM"], dp["dom"]
        unk = [iF, iP, iM] + dom
        zt = np.zeros(n)
        for k, rho in traded_ratio.items():
            if k in dp["ix"]:
                zt[dp["ix"][k]] = float(rho) - 1.0
        mrow = G[iM].copy()
        if milk_ratio is None:
            mrow[iM] -= dp["SM"]                                       # supply moves with the milk price
            mrhs = 0.0
        else:
            mrhs = dp["Q0"][iM] * (float(milk_ratio) - 1.0)
        A = np.vstack([dp["rowF"], dp["rowP"], mrow, G[dom]])
        rhs0 = np.concatenate([[0.0, 0.0, mrhs], np.zeros(len(dom))])
        Au, c = A[:, unk], A @ zt
        nd = len(dom)
        P9 = list(self.DAIRY_PRODUCTS)
        dpos = [P9.index(dp["items"][i]) for i in dom]          # EU-cleared products the block produces
        rho_t = np.array([float(traded_ratio.get(k, 1.0)) for k in P9])

        def demand_change(ud):
            rho = rho_t.copy()
            rho[dpos] = np.maximum(1.0 + ud, 0.05)
            food = np.exp(dp["E"] @ np.log(rho))
            feed = self.dairy_feed_factor(rho, dp, fi)
            return (dp["hc9"] * (food - 1.0) + dp["fd9"] * (feed - 1.0))[dpos]

        cache = getattr(self, "_dairy_u_all", None)
        if cache is None:
            cache = self._dairy_u_all = {}
        u = cache.get(key)
        u = np.zeros(len(unk)) if u is None or len(u) != len(unk) else u.copy()
        for _ in range(60):
            dem = demand_change(u[3:])
            F = Au @ u + c - rhs0 - np.concatenate([np.zeros(3), dem])
            J = Au.copy()
            for q in range(nd):
                du = np.zeros(nd); du[q] = 1e-6
                J[3:, 3 + q] -= (demand_change(u[3:] + du) - dem) / 1e-6
            step = np.linalg.solve(J, -F)
            u = u + step
            if float(np.max(np.abs(step))) < 1e-12:
                break
        cache[key] = u
        z = zt.copy(); z[unk] = u
        Q = dp["Q0"] + G @ z
        items = dp["items"]
        res = {"price_ratio": {**{k: 1.0 + z[dp["ix"][k]] for k in items}, "FATS": 1.0 + z[iF], "PROT": 1.0 + z[iP]},
               "production": {k: float(Q[dp["ix"][k]]) for k in items},
               "production0": {k: float(dp["Q0"][dp["ix"][k]]) for k in items},
               "market_supply": {self.DAIRY_TRADED[k]: float(Q[dp["ix"][k]] - dp["proc0"][dp["ix"][k]])
                                 for k in self.DAIRY_TRADED},
               "market_supply0": {self.DAIRY_TRADED[k]: float(dp["Q0"][dp["ix"][k]] - dp["proc0"][dp["ix"][k]])
                                  for k in self.DAIRY_TRADED},
               "fmil_index": float(fi),
               "residual": float(np.max(np.abs(Au @ u + c - rhs0 - np.concatenate([np.zeros(3), demand_change(u[3:])]))))}
        if milk_ratio is None:
            res["milk_supply_ratio"] = 1.0 + dp["SM"] * z[iM] / dp["Q0"][iM]
        return res

    @staticmethod
    def _dairy_solve_ms(prm, zt, milk_ratio):
        """One member state's block with every product at its (EU) market price: the fat and protein balances
        (FatsProtBal_) and dairies' milk demand = milk delivered (DairyNQ_ for MILK) give the member state's
        fat, protein and raw milk prices; returns the full z (price ratios - 1)."""
        iF, iP, iM = prm["iF"], prm["iP"], prm["iM"]
        unk = [iF, iP, iM]
        A = np.vstack([prm["rowF"], prm["rowP"], prm["G"][iM]])
        rhs = np.array([0.0, 0.0, prm["Q0"][iM] * (float(milk_ratio) - 1.0)])
        u = np.linalg.solve(A[:, unk], rhs - A @ zt)
        z = zt.copy(); z[unk] = u
        return z

    @staticmethod
    def _dairy_solve_ms_resp(prm, zt, mr_base, k, L_seen):
        """_dairy_solve_ms with the member state's raw milk supply responding to its own milk price (audit M5):
        delivered (relative to base) = mr_base + k x (milk price ratio - L_seen), k the supply response per unit of
        price level over base delivery; the dairies' demand equals it (DairyNQ_ = ProdNQ_ MILK)."""
        iF, iP, iM = prm["iF"], prm["iP"], prm["iM"]
        unk = [iF, iP, iM]
        Q0 = float(prm["Q0"][iM])
        mrow = prm["G"][iM].copy()
        mrow[iM] -= Q0 * float(k)
        A = np.vstack([prm["rowF"], prm["rowP"], mrow])
        rhs = np.array([0.0, 0.0, Q0 * (float(mr_base) - 1.0) + Q0 * float(k) * (1.0 - float(L_seen))])
        u = np.linalg.solve(A[:, unk], rhs - A @ zt)
        z = zt.copy(); z[unk] = u
        return z

    def dairy_block(self, traded_ratio: Dict[str, float], milk_ratio, milk_resp=None) -> Optional[dict]:
        """The EU dairy block at given EU prices of the dairy products (relative to base, CAPRI codes) and raw milk
        delivered relative to base: per member state ({ms: ratio}, CAPRI: each member state's dairies process its
        own milk at its own fat, protein and raw milk prices) or, as a single number, the same in all.
        milk_resp {ms: (delivered at the seen price, response k, seen price level)}: raw milk delivered responds to
        the member state's milk price (_dairy_solve_ms_resp, audit M5)."""
        dp = self._dairy_params()
        if not dp:
            return None
        if getattr(self, "_dairy_u", "unset") is None:                 # callers reset the start point
            (getattr(self, "_dairy_u_all", None) or {}).pop("EU27", None)
            self._dairy_u = "unset"
        items = dp["items"]
        n = len(items) + 2
        # traded_ratio: {product: ratio} for every member state, or {EU market region: {product: ratio}}
        per_reg = bool(traded_ratio) and all(isinstance(v, dict) for v in traded_ratio.values())

        def _zt(tr):
            z_ = np.zeros(n)
            for k, rho in tr.items():
                if k in dp["ix"]:
                    z_[dp["ix"][k]] = float(rho) - 1.0
            return z_
        zts = {rg: _zt(traded_ratio.get(rg, {}) if per_reg else traded_ratio) for rg in self.EU}
        zt = zts[self.EU[0]]
        Q = np.zeros(len(items)); Q0 = np.zeros(len(items)); proc0 = np.zeros(len(items))
        Qr = {rg: np.zeros(len(items)) for rg in self.EU}
        vm = vf = vp = vm0 = vf0 = vp0 = 0.0
        vmr = {rg: [0.0, 0.0] for rg in self.EU}
        msr = {}
        for ms, prm in dp["ms"].items():
            rg = self.eu_region_of_ms(ms) or self.EU[0]
            mr = float(milk_ratio.get(ms, 1.0)) if isinstance(milk_ratio, dict) else float(milk_ratio)
            if milk_resp and ms in milk_resp:
                mb, k_, Ls_ = milk_resp[ms]
                z = self._dairy_solve_ms_resp(prm, zts[rg], mb, k_, Ls_)
                mr = float(mb) + float(k_) * (1.0 + float(z[prm["iM"]]) - float(Ls_))
            else:
                z = self._dairy_solve_ms(prm, zts[rg], mr)
            q_ = prm["Q0"] + prm["G"] @ z
            Q += q_
            Qr[rg] += q_
            Q0 += prm["Q0"]; proc0 += prm["proc0"]
            msr[ms] = {"MILK": 1.0 + z[prm["iM"]], "FATS": 1.0 + z[prm["iF"]], "PROT": 1.0 + z[prm["iP"]],
                       "milk_delivered": mr}
            # EU aggregates for reporting: weights = the member state's base raw milk (fat, protein in it)
            w = prm["Q0"][prm["iM"]]
            vm += w * msr[ms]["MILK"]; vm0 += w
            vf += w * msr[ms]["FATS"]; vp += w * msr[ms]["PROT"]
            vmr[rg][0] += w * msr[ms]["MILK"]; vmr[rg][1] += w
        ix = dp["ix"]
        rgp = dp.get("reg") or {}
        res = {"price_ratio": {**{k: (1.0 + zt[ix[k]]) for k in items if k != "MILK"},
                               "MILK": vm / vm0, "FATS": vf / vm0, "PROT": vp / vm0},
               "milk_price_ratio_reg": {rg: (v[0] / v[1] if v[1] > 0 else 1.0) for rg, v in vmr.items()},
               "market_supply_reg": {rg: {self.DAIRY_TRADED[k]: float(Qr[rg][ix[k]] - rgp[rg]["proc0"][ix[k]])
                                          for k in self.DAIRY_TRADED} for rg in self.EU if rg in rgp},
               "ms_price_ratio": msr,
               "production": {k: float(Q[ix[k]]) for k in items},
               "production0": {k: float(Q0[ix[k]]) for k in items},
               "market_supply": {self.DAIRY_TRADED[k]: float(Q[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "market_supply0": {self.DAIRY_TRADED[k]: float(Q0[ix[k]] - proc0[ix[k]]) for k in self.DAIRY_TRADED},
               "fmil_index": float(getattr(self, "_fmil_index", 1.0) or 1.0), "residual": 0.0}
        return res

    #: model country -> CAPRI member state of the dairy block
    _DAIRY_MS = MS_CODE

    def _milk_by_ms(self, exogenous_supply) -> Dict[str, float]:
        """Raw milk delivered per CAPRI member state from the supply models' rows (one per country)."""
        out = {}
        if exogenous_supply is None or "MILK" not in exogenous_supply.columns:
            return out
        for c, v in exogenous_supply["MILK"].items():
            ms = self._DAIRY_MS.get(str(c)[:2], str(c)[:2]) + "000000"
            out[ms] = out.get(ms, 0.0) + float(v)
        return out

    #: CES substitution among the products fed (CAPRI arm/market1.gms p_rhoFeed(RMSSUP,"FMIL") = 0.5)
    RHO_FMIL = param("RHO_FMIL")

    def dairy_feed_factor(self, rho, dp=None, fi=None) -> np.ndarray:
        """Feed use of each dairy product relative to base: FMIL block (calves' milk feed now / base)
        x (CES price index / own price)^0.5, value shares from CAPRI's 2030 feed use at base prices."""
        dp = dp if dp is not None else self._dairy_params()
        fd = dp["fd9"]
        rho = np.asarray(rho, float)
        v = fd * dp["p9"]
        w = v / v.sum() if v.sum() > 0 else np.ones_like(fd) / len(fd)
        sg = self.RHO_FMIL
        pb = float((w * rho ** (1.0 - sg)).sum()) ** (1.0 / (1.0 - sg))
        fi = float(getattr(self, "_fmil_index", 1.0) or 1.0) if fi is None else float(fi)
        return fi * (pb / rho) ** sg

    def _dairy_eu_prices(self, world_prices) -> Dict[str, float]:
        """EU prices of the traded dairy products relative to base, as the dairy block sees them: the
        wedge price x the current EU Armington premium (lagged within an outer iteration). With two EU market
        regions (bilateral market): {region: {product: ratio}}."""
        dom = self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))
        d0 = getattr(self, "_dom0_cache", None)
        if d0 is None:
            d0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = d0
        bl = getattr(self, "_bilat_ratio_now", None)
        if bl is not None and self.eu_blocks:
            return {rg: {k: float(bl.at[rg, c]) if (c in bl.columns and rg in bl.index) else 1.0
                         for k, c in self.DAIRY_TRADED.items()} for rg in self.EU}
        if self.eu_blocks:
            return {rg: {k: 1.0 for k in self.DAIRY_TRADED} for rg in self.EU}
        if bl is not None and "EU27" in bl.index:
            return {k: float(bl.at["EU27", c]) if c in bl.columns else 1.0 for k, c in self.DAIRY_TRADED.items()}
        prem = getattr(self, "eu_premium", None) if getattr(self, "_eu_base_supply", None) is not None else None
        out = {}
        for k, c in self.DAIRY_TRADED.items():
            b = float(d0.at["EU27", c])
            pr = float(prem.get(c, 1.0)) if prem is not None else 1.0
            out[k] = float(dom.at["EU27", c]) / b * pr if b > 0 else 1.0
        return out

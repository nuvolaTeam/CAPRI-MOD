"""MarketModule: supply outside the supply models (non-EU own-price supply response).

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


class SupplyMixin(MarketStateMixin):
    """MarketModule methods for supply outside the supply models (non-EU own-price supply response)."""


    def _region_supply_elas(self, regions, cols, el) -> np.ndarray:
        """regions x cols own-price supply elasticities: CAPRI's per non-EU region (capri_data/2017/market/
        supply_elas_region.csv), else 0 - where CAPRI has no p_elasSupp for a region and product its supply Hessian
        p_hessNQSupp has no term (arm/market1.gms), so the supply does not respond to the price. Until 23 October 2026
        those cells took the product's EU median or the Armington eps column (no CAPRI source; PROXY_AUDIT S176
        note). The processed products' supply is set by their blocks (crushing, dairy, biofuels) where CAPRI has
        them. EU rows: el (their supply comes from the supply models)."""
        key = (tuple(regions), tuple(cols), tuple(np.round(el.reindex(cols).to_numpy(dtype=float), 12)))
        cache = getattr(self, "_reg_elas_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        EV = np.tile(el.reindex(cols).to_numpy(dtype=float), (len(regions), 1))
        eu_ = set(self.EU)
        for i_, r_ in enumerate(regions):
            if r_ not in eu_:
                EV[i_, :] = 0.0
        ri = {r: i for i, r in enumerate(regions)}
        ci = {c: j for j, c in enumerate(cols)}
        for r_, c_, e_ in self._inp().csv("supply_elas_region.csv")[["region", "commodity", "elasticity"]].itertuples(index=False):
            if r_ in ri and c_ in ci and r_ not in eu_:
                EV[ri[r_], ci[c_]] = float(e_)
        self._reg_elas_cache = (key, EV)
        return EV


    def supply_response(
        self,
        world_prices: pd.Series,
        exogenous_supply: Optional[pd.DataFrame] = None,
        region_ratio: Optional[pd.DataFrame] = None,
        crush_dom: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Supply quantities by region and commodity (1000 t).
        If exogenous_supply is given (from supply module, one row per country), use it for EU27 (or the EU
        market regions) and, for Norway's rows, for its own market region NOR (SUP_NONEU_REGIONS).
        Otherwise, apply supply elasticity to price signal.

        region_ratio (bilateral market): each region's own market price relative to base, region x commodity; the
        supply elasticity then applies to the region's own price, the EU's supply-module output is
        anticipated against the EU price farmers last saw, and crushing and the dairy blocks see the
        regional prices (crush_dom: the price levels the crushers face).
        """
        # the supply models' output: the EU's countries, and the non-EU market regions with supply models (Norway)
        self.ev.dairy_m5_now = None
        exo_all = exogenous_supply
        exogenous_supply, exo_sup = self._split_supply(exo_all)
        self.ev.sup_active = set(exo_sup)
        sup_cols = {}
        if exogenous_supply is not None:
            # Only override the EU27 row with the supply-module output; keep
            # all other trade regions (USA, BRA, CHN, ROW, ...) at their
            # calibrated base production. Otherwise global supply collapses to
            # the EU subset and excess demand explodes.
            supply = self.par.base_production.copy()
            _ex = (self.eu_rows(exogenous_supply) if self.eu_blocks
                   else pd.DataFrame([exogenous_supply.sum(axis=0)], index=["EU27"]))
            # Norway (CAPRI RMSSUP outside the EU, K56): its market supply is its supply models' output, as the EU's
            for reg, ser in exo_sup.items():
                if reg not in supply.index:
                    continue
                for comm, v in ser.items():
                    if comm in supply.columns and float(v) > 1e-6:
                        supply.at[reg, comm] = float(v)
                        sup_cols.setdefault(reg, set()).add(comm)
            for comm in exogenous_supply.columns:
                if comm not in supply.columns:
                    continue
                for reg in self.EU:
                    eu_val = float(_ex.at[reg, comm]) if reg in _ex.index else 0.0
                    # 1e-6 (1 kg): solver noise in regions that do not grow the product is not supply. In a run on a
                    # subset of regions (tests) a product none of them grows came back as 1e-15 and replaced the EU's
                    # base supply, and the EU price ran to 1e7 (K16)
                    if eu_val > 1e-6 and reg in supply.index:
                        supply.at[reg, comm] = eu_val
        else:
            supply = self.par.base_production.copy()

        # Own-price supply elasticities from CAPRI's calibrated market model
        # (elas1717 p_elasSupp, EU medians). These replace the crop-oriented
        # Armington eps column, which stood in a blanket 0.15-0.25 for every
        # commodity -- including livestock, where CAPRI's real values are
        # 0.55-0.76. Commodities not in the file keep the eps fallback.
        real_supply = getattr(self, "_real_supply_elas", None)
        if real_supply is None:
            # CAPRI's EU p_elasSupp (a missing file stops: no silent fallback, 23 October 2026)
            real_supply = self._inp().json("supply_elas_eu_all.json", "sources/arm")
            self._real_supply_elas = real_supply

        if "eps" not in self.armington.columns:            # no stand-in (removed 23 October 2026: 0.25)
            raise ValueError("armington_params.csv has no eps column")
        eps = self.armington["eps"]

        # Vectorised over commodities; arithmetic unchanged.
        ratio = pd.Series({
            c: float(world_prices.get(c, self.world_prices_base[c]))
               / max(float(self.world_prices_base[c]), 0.01)
            for c in self.commodities})
        el = pd.Series({
            c: (float(real_supply[c]) if c in real_supply else float(eps[c]))
            for c in self.commodities})
        cols = [c for c in self.commodities if c in supply.columns]
        # each non-EU region's own-price elasticity from CAPRI's market model (p_elasSupp "CAL" of its CAPRI regions,
        # production-weighted; tools/build/build_supply_elas_nonEU.py; KNOWN_ISSUES K54-3), 0 where CAPRI has none
        # (_region_supply_elas); the per-product value above only for the EU rows (their supply comes from the supply
        # models)
        EV = self._region_supply_elas(list(supply.index), cols, el)
        self._welf_supply_EV = (list(supply.index), cols, EV)        # the welfare report (market/welfare.py)
        if region_ratio is None:
            fac = ratio.reindex(cols).to_numpy(dtype=float)[None, :] ** EV
            supply[cols] = np.maximum(supply[cols].to_numpy(dtype=float) * fac, 0.0)
            self._eu_market_supply_nq(supply, cols, lambda reg_: ratio.reindex(cols).to_numpy(dtype=float))
        else:
            # in arrays (pandas arithmetic here was a sizeable share of each market evaluation; same values)
            rr = region_ratio.reindex(index=supply.index, columns=cols).to_numpy(dtype=float)
            rr = np.maximum(np.where(np.isnan(rr), 1.0, rr), 1e-6)
            ev = el.reindex(cols).to_numpy(dtype=float)
            fac = rr ** EV
            # the EU market regions' supply before the price response (the supply models' latest output): EU27, or
            # each of CAPRI's two trade blocks
            s_exo_eu = ({r_: supply.loc[r_, cols].astype(float).copy() for r_ in self.EU if r_ in supply.index}
                        if exogenous_supply is not None else None)
            _sv_eu = {}
            seen_all = self.seen.eu_price_seen
            for reg in self.EU:
                if reg not in supply.index:
                    continue
                ie_ = list(supply.index).index(reg)
                # the price the supply models last saw: one Series (EU), or regions x commodities (EU market regions)
                seen = (seen_all.loc[reg] if isinstance(seen_all, pd.DataFrame) and reg in seen_all.index
                        else (seen_all if isinstance(seen_all, pd.Series) else None))
                sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
                      if seen is not None else np.ones(len(cols)))
                # products the EU supplies through CAPRI's market supply function, not a supply-model activity
                # (other vegetable oils): their EU supply responds to the EU price against base, not against the
                # price the supply models last saw (that anticipation would vanish at convergence and hold them at base)
                for j, c in enumerate(cols):
                    if c in self.EU_MARKET_SUPPLY:
                        sv[j] = 1.0
                fac[ie_] = (rr[ie_] / sv) ** ev
                _sv_eu[reg] = sv
            # the non-EU market regions with supply models (Norway): the products of their supply models are
            # anticipated against the prices those models last saw (own market's prices), with the region's own
            # CAPRI elasticity (p_elasSupp of NO000000, supply_elas_region.csv); the products without a supply-model
            # activity (fish, ...) keep CAPRI's market supply function at the region's price against base
            seen_sup = self.seen.sup_price_seen or {}
            _sv_sup = {}
            for reg, sc_ in sup_cols.items():
                i_ = list(supply.index).index(reg)
                seen = seen_sup.get(reg)
                sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
                      if seen is not None else np.ones(len(cols)))
                _sv_sup[reg] = sv
                for j, c in enumerate(cols):
                    if c in sc_:
                        fac[i_, j] = (rr[i_, j] / sv[j]) ** EV[i_, j]
            s_exo_sup = {reg: supply.loc[reg, cols].astype(float).copy() for reg in sup_cols}
            supply[cols] = np.maximum(supply[cols].to_numpy(dtype=float) * fac, 0.0)
            self._eu_market_supply_nq(supply, cols, lambda reg_: rr[list(supply.index).index(reg_)])
            # CAPRI's market supply function for the supply models' products (arm/market_model.gms ProdNQ_, the
            # Hessian measured on the supply models at the baseline, model._market_supply_hessian): linear in the
            # prices, through the supply models' latest output at the prices they saw
            # (arm/simu_calibration_to_supply.gms:360-368), with the cross-price terms; it replaces the own-price
            # anticipation for those products
            # one Hessian for EU27, or one per trade block (the sum of its member states', CAPRIModel._split_hessian)
            _hs = self.par.supply_hessian or {}
            _hreg = {"EU27": _hs.get("eu")} if not self.eu_blocks else dict(_hs.get("blocks") or {})
            _hcache = getattr(self, "_hess_cache", None)
            if not isinstance(_hcache, dict):
                _hcache = {}
            for reg_, H in _hreg.items():
                if H is None or s_exo_eu is None or not len(H) or reg_ not in s_exo_eu or reg_ not in _sv_eu:
                    continue
                ie_ = list(supply.index).index(reg_)
                ck = (id(H), tuple(cols), tuple(exogenous_supply.columns))
                hc = _hcache.get(reg_)
                if hc is None or hc[0] != ck:
                    ex_cols = set(exogenous_supply.columns)
                    xs = [x for x in H.index if x in cols and x in ex_cols]
                    hc = (ck, xs, [cols.index(x) for x in xs],
                          H.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float))
                    _hcache[reg_] = hc
                _, xs, xj, Hm = hc
                if xs:
                    s0 = s_exo_eu[reg_].to_numpy(dtype=float)[xj]
                    dP_ = self._nq_price_change(rr[ie_] - _sv_eu[reg_], cols)
                    mt = self._milk_terms(cols, xs, H) if (reg_ == "EU27" and not self.eu_blocks) else None
                    if mt is None:
                        q = s0 + Hm @ dP_ + self._yani_clear(reg_, H, xs, cols, dP_)
                    else:
                        q = s0 + Hm @ dP_ + self._milk_and_yani_clear(reg_, H, xs, cols, dP_, mt, world_prices,
                                                                      exogenous_supply)
                    keep = s0 > 1e-6
                    vals = supply.loc[reg_, cols].to_numpy(dtype=float).copy()
                    vals[np.asarray(xj)[keep]] = np.maximum(q[keep], 0.0)
                    supply.loc[reg_, cols] = vals
            self._hess_cache = _hcache
            # the same market supply function for Norway's supply models (its own Hessian, measured on its models)
            for reg, Hs in ((self.par.supply_hessian or {}).get("sup") or {}).items():
                if reg not in sup_cols or Hs is None or not len(Hs):
                    continue
                i_ = list(supply.index).index(reg)
                xs = [x for x in Hs.index if x in cols and x in sup_cols[reg]]
                if not xs:
                    continue
                xj = [cols.index(x) for x in xs]
                Hm = Hs.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float)
                s0 = s_exo_sup[reg].to_numpy(dtype=float)[xj]
                dP_ = self._nq_price_change(rr[i_] - _sv_sup[reg], cols)
                q = s0 + Hm @ dP_ + self._yani_clear(reg, Hs, xs, cols, dP_)
                keep = s0 > 1e-6
                vals = supply.loc[reg, cols].to_numpy(dtype=float).copy()
                vals[np.asarray(xj)[keep]] = np.maximum(q[keep], 0.0)
                supply.loc[reg, cols] = vals
        # CRUSHING: oil and cake supply = crush x the CET yields (CAPRI ProcO_, procYield_; _crush_state)
        cp = self._crush_params()
        if cp:
            _cpn = self.ev.crush_prices_now
            cst = self._crush_state(_cpn if _cpn is not None else (crush_dom if crush_dom is not None else
                                    self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))))
            done = set()
            for (r, s), (q, qo, qc) in cst.items():
                o, c = self.CRUSH_CHAINS[s]
                for prod, v in ((o, qo), (c, qc)):
                    if prod in supply.columns:
                        if (r, prod) not in done:
                            supply.at[r, prod] = 0.0
                            done.add((r, prod))
                        supply.at[r, prod] += v
        # DAIRY (CAPRI DairyNQ_, ProcMargM_, FatsProtBal_): EU raw milk is delivered to dairies, not
        # traded on the world milk market; the EU supply of butter, skimmed milk powder, cheese and
        # whey comes from the dairy block at the EU product prices and the milk delivered.
        if self._dairy_params() and all(r in supply.index for r in self.EU):
            if exogenous_supply is not None and "MILK" in exogenous_supply.columns and len(exogenous_supply):
                Sr = ({r: float(v) for r, v in self.eu_rows(exogenous_supply[["MILK"]])["MILK"].items()} if self.eu_blocks
                      else {"EU27": float(exogenous_supply["MILK"].sum())})
            else:
                Sr = {r: float(self.par.base_production.at[r, "MILK"]) for r in self.EU}
            S = sum(Sr.values())
            S0 = float(self.par.dairy_S0 or S)
            _m0 = self.par.dairy_S0_ms or {}
            _m = self._milk_by_ms(exogenous_supply)
            _mr = ({ms: (_m[ms] / q0 if (q0 > 0 and ms in _m) else 1.0) for ms, q0 in _m0.items()} if (_m0 and _m)
                   else (S / S0 if S0 > 0 else 1.0))
            _m5 = self.ev.dairy_m5_now
            if _m5 is not None:
                # the block solved with the member states' raw milk responding to their prices (audit M5,
                # _milk_and_yani_clear): raw milk delivered as it responded
                res = _m5
                self.ev.dairy_m5_now = None
                Sr = {"EU27": float(Sr["EU27"]) + float(self.ev.milk_dq_now or 0.0)}
            else:
                res = self.dairy_block(self._dairy_eu_prices(world_prices), _mr)
            if res is not None:
                for r in self.EU:
                    supply.at[r, "MILK"] = Sr[r]
                    for c, q in (res["market_supply_reg"].get(r) or {}).items():
                        if c in supply.columns:
                            supply.at[r, c] = max(0.0, q)
                self.ev.eu_milk_supply_now = dict(Sr)
                self.ev.dairy_last = res
        # NON-EU DAIRY (dairy Stage 4): each trade region's butter, SMP, cheese and whey from CAPRI's dairy
        # block with CAPRI's raw milk supply function, at the region's domestic prices; the market's base
        # quantities move with the block's relative change (the flat per-product elasticity is replaced)
        wpar = self._dairy_world_params()
        if wpar:
            dom = self.domestic_prices(world_prices, getattr(self, "_trade_scenario_now", None))
            d0 = getattr(self, "_dom0_cache", None)
            if d0 is None:
                d0 = self.domestic_prices(self.world_prices_base)
                self._dom0_cache = d0
            wl = {}
            self.ev.sup_milk_now = {}
            self.ev.world_milk_now = {}
            for r, prm in wpar.items():
                if r not in supply.index:
                    continue
                if region_ratio is not None:
                    tr = {k: float(region_ratio.at[r, c]) if c in region_ratio.columns else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                else:
                    tr = {k: float(dom.at[r, c]) / float(d0.at[r, c]) if float(d0.at[r, c]) > 0 else 1.0
                          for k, c in self.DAIRY_TRADED.items()}
                # Norway (RMSSUP): raw milk delivered from its supply models (CAPRI market_model.gms ProdNQ_ NOTE2:
                # milk production in RMSSUP is covered by the supply models), its block's FMIL index from its herds;
                # the other regions: CAPRI's raw milk supply function
                mr_ = None
                m0_ = (self.par.sup_milk0 or {}).get(r)
                if r in exo_sup and "MILK" in exo_sup[r].index and m0_:
                    m_now = float(exo_sup[r]["MILK"])
                    mr_ = m_now / m0_
                    supply.at[r, "MILK"] = m_now
                    self.ev.sup_milk_now[r] = m_now
                fi_ = float((self.seen.fmil_index_sup or {}).get(r, 1.0)) if mr_ is not None else 1.0
                res_r = self._dairy_solve(prm, tr, mr_, fi_, r)
                wl[r] = res_r
                if mr_ is None and "MILK" in supply.columns and "milk_supply_ratio" in res_r:
                    # raw milk is not traded (CAPRI): the region's milk supply function (ProdNQ_ MILK) against its
                    # dairies' demand (DairyNQ_), both inside its dairy block; the market row carries the block's
                    # quantity as supply and use (audit M11, 24 October 2026)
                    q_ = float(self.par.base_production.at[r, "MILK"]) * float(res_r["milk_supply_ratio"])
                    supply.at[r, "MILK"] = q_
                    self.ev.world_milk_now[r] = q_
                for c, q in res_r["market_supply"].items():
                    q0 = res_r["market_supply0"][c]
                    if c in supply.columns and q0 > 1e-9:
                        supply.at[r, c] = max(0.0, float(self.par.base_production.at[r, c]) * q / q0)
            self.ev.dairy_world_last = wl
        if "MILK" in supply.columns:
            # raw milk in a region without supply models or a dairy block: no market of its own in CAPRI's data,
            # kept at its base (no world raw-milk market, audit M11)
            _wm = self.ev.world_milk_now or {}
            for r in supply.index:
                if r not in self.EU and r not in self.SUP and r not in _wm:
                    supply.at[r, "MILK"] = float(self.par.base_production.at[r, "MILK"])
        # BIOFUELS (CAPRI SupplyBiof_, MaprBiof_, prodQuantBiofBy_): each region's biofuel output is the sum over
        # its CAPRI market regions of first-generation output from the processing margin plus the fixed
        # non-agricultural, second-generation and exogenous output; without endogenous biofuel markets, the
        # reference output (first generation x biofuel_output_scale). DDGS comes from the ethanol plants' cereal
        # feedstocks in both cases (CAPRI keeps DDGS a market product without BIOF_M too).
        bm = self._biofuel_market_params()
        bp = self._biofuel_params()
        if bm or bp:
            d0 = self._dom0()
            par = None
            if crush_dom is not None:
                par = (crush_dom.reindex(index=d0.index, columns=d0.columns) / d0.where(d0 > 0)).fillna(1.0)
            st = self.biofuel_state(region_ratio, par)
            self.ev.biof_state = st
            for (reg, fuel), q0 in (bm.get("prod0") or {}).items():
                if reg in supply.index and fuel in supply.columns:
                    supply.at[reg, fuel] = st["prod"].get((reg, fuel), q0)
            if "DDGS" in supply.columns:
                for reg, q in st["ddgs"].items():
                    if reg in supply.index:
                        supply.at[reg, "DDGS"] = q
        return supply
    #: prices the market's supply functions take as the supply models saw them: raw milk (the EU's and Norway's raw milk
    #: is priced by their dairy blocks and its supply is the supply models' within a market solve, audit M5; its ratio
    #: in the trade system is the pooled world ratio, not the dairy price). Taken at the models' price, a 0.1 gap
    #: (+11% dairy price against a world ratio of 1) moved calves and lambs supply through the Hessian's milk column
    #: and held the young-animal markets off their balance (K75)
    NQ_PRICE_AS_SEEN = ("MILK",)

    #: CAPRI's raw milk inside the market (audit M5): each member state's raw milk supply follows its own milk price
    #: (ProdNQ_ MILK with p_hessNQSupp, the measured Hessian's member-state rows and columns) against its dairies'
    #: demand (DairyNQ_) in the dairy block, and its milk price moves the other products' and the young animals'
    #: supply (the Hessian's MILK column per member state; the member states' milk prices their models saw: seen.milk_seen_ms)

    def _milk_terms(self, cols, xs, H):
        """The member states' raw milk terms of the market supply Hessian (supply_hessian["ms"], per country summed
        to CAPRI's member state of the dairy block): {"ms": [...], "h": own response (kt per unit of price level),
        "row": member state x cols (MILK's response to the products' prices), "rowY": member state x young-animal
        goods, "col": xs x member state (the products' response to the member state's milk price), "colY": young
        goods x member state, "goods": young-animal goods}; None without data."""
        if not self.seen.milk_seen_ms or not self._dairy_params():
            return None
        hs = (self.par.supply_hessian or {}).get("ms") or {}
        if not hs:
            return None
        st = (self.seen.yani_state or {}).get("EU27") or {}
        goods = [g for g in (st.get("goods") or []) if ("YANI:" + g) in H.index and ("YANI:" + g) in H.columns]
        ck = (id(hs), tuple(cols), tuple(xs), tuple(goods))
        c_ = getattr(self, "_milk_terms_cache", None)
        if c_ is not None and c_[0] == ck:
            return c_[1]
        sup_of = getattr(self, "sup_region_of_country", lambda c: None)
        agg = {}
        for cc, h in hs.items():
            if sup_of(cc) is not None or "MILK" not in h.columns or "MILK" not in h.index:
                continue
            ms = self._DAIRY_MS.get(str(cc)[:2], str(cc)[:2]) + "000000"
            agg[ms] = h if ms not in agg else agg[ms].add(h, fill_value=0.0)
        mss = sorted(m for m in agg if m in self._dairy_params().get("ms", {}))
        if not mss:
            return None
        yi = ["YANI:" + g for g in goods]
        out = {"ms": mss, "goods": goods,
               "h": np.array([float(agg[m].at["MILK", "MILK"]) for m in mss]),
               "row": np.array([agg[m].reindex(columns=cols).loc["MILK"].fillna(0.0).to_numpy(dtype=float) for m in mss]),
               "rowY": np.array([agg[m].reindex(columns=yi).loc["MILK"].fillna(0.0).to_numpy(dtype=float) for m in mss])
               if yi else np.zeros((len(mss), 0)),
               "col": np.array([agg[m].reindex(index=list(xs))["MILK"].fillna(0.0).to_numpy(dtype=float) for m in mss]).T,
               "colY": np.array([agg[m].reindex(index=yi)["MILK"].fillna(0.0).to_numpy(dtype=float) for m in mss]).T
               if yi else np.zeros((0, len(mss)))}
        # the products' rows take MILK's own response through the member states' milk (MILK's row is replaced by the
        # dairy block's delivered milk, supply_response)
        out["col"][[i for i, x in enumerate(xs) if x == "MILK"], :] = 0.0
        out["row"][:, [j for j, c in enumerate(cols) if c == "MILK"]] = 0.0
        self._milk_terms_cache = (ck, out)
        return out

    def _milk_and_yani_clear(self, reg, H, xs, cols, dP, mt, world_prices, exogenous_supply):
        """The EU's young-animal markets (_yani_clear) and the member states' raw milk (dairy_block with the milk
        response) cleared together at the current product prices: the milk prices move the young animals' supply and
        the young-animal prices the milk supply (CAPRI's ProdNQ_ with p_hessNQSupp, solved jointly in its market
        model); a few rounds of the two linear clearings. Returns the products' supply change from both (rows xs)
        and keeps the dairy block's solution for supply_response (ev.dairy_m5_now)."""
        mss = mt["ms"]
        Ls = np.array([float(self.seen.milk_seen_ms.get(m, 1.0)) for m in mss])
        _m0 = self.par.dairy_S0_ms or {}
        _m = self._milk_by_ms(exogenous_supply)
        q0 = np.array([float(_m0.get(m, 0.0)) for m in mss])
        mr0 = np.array([(_m.get(m, 0.0) / q0[i]) if q0[i] > 0 else 1.0 for i, m in enumerate(mss)])
        # every member state's delivered milk as the dairy section sets it; the responding ones below
        mr_all = {m_: (_m[m_] / q_ if (q_ > 0 and m_ in _m) else 1.0) for m_, q_ in _m0.items()}
        tr = self._dairy_eu_prices(world_prices)
        st = (self.seen.yani_state or {}).get(reg) or {}
        r_seen = np.array([float(st.get("seen", {}).get(g, 1.0)) for g in mt["goods"]])
        dL = np.zeros(len(mss))
        dY = np.zeros(len(mt["goods"]))
        res = None
        for _ in range(4):
            ey = mt["colY"] @ dL if len(mt["goods"]) else 0.0
            yq = self._yani_clear(reg, H, xs, cols, dP, extra_y=ey)
            if len(mt["goods"]):
                rn = (self.ev.yani_market_now or {}).get(reg) or {}
                dY = np.array([float(rn.get(g, r_seen[k])) for k, g in enumerate(mt["goods"])]) - r_seen
            a = mt["row"] @ np.asarray(dP, float) + (mt["rowY"] @ dY if len(mt["goods"]) else 0.0)
            resp = {m: (mr0[i] + (a[i] / q0[i] if q0[i] > 0 else 0.0), (mt["h"][i] / q0[i] if q0[i] > 0 else 0.0), Ls[i])
                    for i, m in enumerate(mss)}
            res = self.dairy_block(tr, {**mr_all, **{m: v[0] for m, v in resp.items()}}, milk_resp=resp)
            if res is None:
                return yq
            dL_new = np.array([float(res["ms_price_ratio"][m]["MILK"]) - Ls[i] for i, m in enumerate(mss)])
            done = float(np.max(np.abs(dL_new - dL))) < 1e-10
            dL = dL_new
            if done:
                break
        self.ev.dairy_m5_now = res
        # raw milk delivered against the supply models' (kt): the milk row of the market carries it
        self.ev.milk_dq_now = float(sum((float(res["ms_price_ratio"][m]["milk_delivered"]) - mr0[i]) * q0[i]
                                      for i, m in enumerate(mss)))
        return yq + mt["col"] @ dL

    def _eu_market_supply_nq_params(self) -> dict:
        """CAPRI's market supply functions of the EU products no supply model produces (EU_MARKET_SUPPLY: other
        vegetable oils, the fish products; ProdNQ_, tools/build/build_eu_market_supply_nq.py), summed per EU market
        region: {region: {(x, y): kt per unit change of y's price ratio}}."""
        c = getattr(self, "_eu_msnq_cache", None)
        if c is not None:
            return c
        out: dict = {}
        for r in self._inp().csv("eu_market_supply_nq.csv").itertuples(index=False):
            rg = (self.eu_region_of_ms(r.ms) if self.eu_blocks else "EU27") or "EU27"
            d = out.setdefault(rg, {})
            d[(r.x, r.y)] = d.get((r.x, r.y), 0.0) + float(r.h_ratio)
        self._eu_msnq_cache = out
        return out

    def _eu_market_supply_nq(self, supply, cols, ratio_of):
        """The EU supply of EU_MARKET_SUPPLY as CAPRI's ProdNQ_ (audit, programme step D): per EU market region, base
        supply + sum_y h_xy x (y's price ratio - 1), h in kt per unit of price ratio (CAPRI's p_hessNQSupp x PPRI0 /
        INPE); the constant is not recalibrated (no supply model produces these products). It replaces the EU median
        elasticity against base (p_elasSupp) these products took before 28 October 2026."""
        P = self._eu_market_supply_nq_params()
        ci = {c: j for j, c in enumerate(cols)}
        for rg, terms in P.items():
            if rg not in supply.index:
                continue
            r_ = ratio_of(rg)
            for x in self.EU_MARKET_SUPPLY:
                if x not in ci or x not in supply.columns:
                    continue
                q0 = float(self.par.base_production.at[rg, x]) if x in self.par.base_production.columns else 0.0
                if q0 <= 0:
                    continue
                dq = sum(h * (float(r_[ci[y]]) - 1.0) for (x_, y), h in terms.items() if x_ == x and y in ci)
                supply.at[rg, x] = max(q0 + dq, 0.0)

    def _nq_price_change(self, dP, cols):
        """The price changes the market's supply functions respond to (relative to the prices the supply models saw),
        with NQ_PRICE_AS_SEEN at zero."""
        dP = np.array(dP, dtype=float, copy=True)
        for c in self.NQ_PRICE_AS_SEEN:
            if c in cols:
                dP[cols.index(c)] = 0.0
        return dP

    def _yani_clear(self, reg, H, xs, cols, dP, extra_y=0.0):
        """CAPRI's yaniMarket_ inside the market (arm/market_model.gms l. 1579-1603): the market region's net supply of
        each young-animal good, a normalised-quadratic function of all prices (p_hessNQSupp rows xxOmYani) recalibrated
        to the supply models' latest solution (simu_calibration_to_supply.gms l. 360-368), equals its reference; the
        young-animal prices clearing it at the current product prices are solved here and their effect on the products'
        supply (the Hessian's young-animal columns) is returned for the rows xs. The prices are kept in
        ev.yani_market_now for the next supply solve. Returns 0 where no young-animal market is cleared here."""
        st = (self.seen.yani_state or {}).get(reg)
        if not st or H is None:
            return 0.0
        goods = [g for g in st["goods"] if ("YANI:" + g) in H.index and ("YANI:" + g) in H.columns]
        if not goods:
            return 0.0
        cache = self.__dict__.setdefault("_yani_hcache", {})
        ck = (reg, id(H), tuple(cols), tuple(xs), tuple(goods))
        mats = cache.get(ck)
        if mats is None:
            yi = ["YANI:" + g for g in goods]
            mats = (H.reindex(index=yi, columns=cols).fillna(0.0).to_numpy(dtype=float),
                    H.reindex(index=yi, columns=yi).fillna(0.0).to_numpy(dtype=float),
                    H.reindex(index=list(xs), columns=yi).fillna(0.0).to_numpy(dtype=float))
            cache.clear()
            cache[ck] = mats
        H_YP, H_YY, H_PY = mats
        n_now = np.array([float(st["net"].get(g, 0.0)) for g in goods])
        ref = np.array([float(st["ref"].get(g, 0.0)) for g in goods])
        r_seen = np.array([float(st["seen"].get(g, 1.0)) for g in goods])
        # extra_y: the young animals' supply change from the member states' milk prices (_milk_and_yani_clear)
        rhs = ref - n_now - H_YP @ np.asarray(dP, float) - extra_y
        dr = np.linalg.lstsq(H_YY, rhs, rcond=None)[0]
        lo, hi = st.get("bounds", (-50.0, 50.0))
        r = np.clip(r_seen + dr, lo, hi)
        self.ev.setdefault("yani_market_now", {})[reg] = dict(zip(goods, (float(v) for v in r)))
        return H_PY @ (r - r_seen)

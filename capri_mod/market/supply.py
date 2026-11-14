"""MarketModule: supply outside the supply models (the non-EU market supply functions).

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
from capri_mod.data.definitions import MS_CODE, EU_MS_BLOCK as _EU_MS, capri_ms
from capri_mod.market.equilibrium import MarketEquilibrium  # noqa: F401
from capri_mod.market.state import MarketStateMixin


class SupplyMixin(MarketStateMixin):
    """MarketModule methods for supply outside the supply models (non-EU market supply functions)."""

    #: the non-EU market regions' supply as CAPRI's ProdNQ_ (own and cross-price terms, p_hessNQSupp; true, CAPRI's
    #: form) or one own-price constant elasticity per product (false, until 29 October 2026)
    noneu_supply_nq = setting("market.noneu_supply_nq")
    sup_milk_in_market = setting("market.sup_milk_in_market")
    #: CAPRI's market land block outside the EU (LandSupplyMNL_, LndSupplyEqualsDemand_, rentFromProdpriceLand_;
    #: arm/market_model.gms l. 1696-1790): the rents of TCRP, FODFAL, FRUN clear each non-EU region's land market
    #: (true, CAPRI's form) or are held at calibration (false, until 4 November 2026)
    noneu_land_market = setting("market.noneu_land_market")
    #: CAPRI's land-use-change estimation outside the EU (luc_market; capri_mod/market/luc.py), reported with the
    #: market's solution
    luc_market = setting("market.luc_market")
    #: CAPRI's agricultural land types of the market (xx1Land / luAgrMrk, arm/arm_sets.gms)
    MARKET_LAND = ("TCRP", "FODFAL", "FRUN")


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
        If exogenous_supply is given (from supply module, one row per country), use it for the EU's market
        regions (CAPRI's two blocks) and, for Norway's rows, for its own market region NO000000 (SUP_NONEU_REGIONS).
        Otherwise, apply supply elasticity to price signal.

        region_ratio (bilateral market): each region's own market price relative to base, region x commodity; the
        supply elasticity then applies to the region's own price, the EU's supply-module output is
        anticipated against the EU price farmers last saw, and crushing and the dairy blocks see the
        regional prices (crush_dom: the price levels the crushers face).
        """
        # the supply models' output: the EU's countries, and the non-EU market regions with supply models (Norway)
        self.ev.dairy_m5_now = None
        # Norway's raw milk terms are set by this evaluation's market supply functions (_sup_milk_terms) or not at all
        self.ev.sup_milk_terms = None
        self.ev.sup_milk_cross = None
        exo_all = exogenous_supply
        exogenous_supply, exo_sup = self._split_supply(exo_all)
        self.ev.sup_active = set(exo_sup)
        sup_cols = {}
        if exogenous_supply is not None:
            # Only override the EU blocks' rows with the supply-module output; keep
            # all other trade regions (USA, BRA, CHN, ROW, ...) at their
            # calibrated base production. Otherwise global supply collapses to
            # the EU subset and excess demand explodes.
            supply = self.par.base_production.copy()
            _ex = self.eu_rows(exogenous_supply)
            # Norway (CAPRI RMSSUP outside the EU, K56): its market supply is its supply models' output, as the EU's
            for reg, ser in exo_sup.items():
                if reg not in supply.index:
                    continue
                for comm, v in ser.items():
                    if comm in supply.columns and float(v) > 1e-6:
                        supply.at[reg, comm] = float(v)
                        sup_cols.setdefault(reg, set()).add(comm)
            _xr = self._eu_excluded_rows()
            for comm in exogenous_supply.columns:
                if comm not in supply.columns:
                    continue
                for reg in self.EU:
                    eu_val = float(_ex.at[reg, comm]) if reg in _ex.index else 0.0
                    # 1e-6 (1 kg): solver noise in regions that do not grow the product is not supply. In a run on a
                    # subset of regions (tests) a product none of them grows came back as 1e-15 and replaced the EU's
                    # base supply, and the EU price ran to 1e7 (K16). With the units outside the run supplied by
                    # their member states' market supply functions (K83, added below) the solved units' output is
                    # their part, whatever its size, wherever the EU's units produce the product
                    x_val = (float(_xr.at[reg, comm]) if (_xr is not None and reg in _xr.index
                                                          and comm in _xr.columns) else 0.0)
                    if reg in supply.index and (eu_val > 1e-6 or (_xr is not None and eu_val + x_val > 1e-6)):
                        supply.at[reg, comm] = eu_val
        else:
            supply = self.par.base_production.copy()

        # Own-price supply elasticities of the EU rows: CAPRI's calibrated market model (elas1717 p_elasSupp), the
        # median over the model's 27 member states per market commodity (supply_elas_eu.csv,
        # tools/build/build_capri_supply_elas_market.py; until 29 October 2026 over CAPRI's EU28 with four products
        # under CAPRI's codes, which were never found: KNOWN_ISSUES K101). A missing file stops.
        real_supply = getattr(self, "_real_supply_elas", None)
        if real_supply is None:
            _se = self._inp().csv("supply_elas_eu.csv")
            real_supply = {str(c): float(v) for c, v in zip(_se.commodity, _se.elasticity)}
            self._real_supply_elas = real_supply


        # Vectorised over commodities; arithmetic unchanged.
        ratio = pd.Series({
            c: float(world_prices.get(c, self.world_prices_base[c]))
               / max(float(self.world_prices_base[c]), 0.01)
            for c in self.commodities})
        # a product without CAPRI's EU p_elasSupp gets no own-price anticipation in the EU rows: its EU supply is set
        # below by CAPRI's market supply function (the measured Hessian), crushing, the dairy block, the biofuel block
        # or the residual feeds' MaprFeed_, or the EU produces none of it (palm oil, coffee, tea, cocoa). Until 29
        # October 2026 the eps column of armington_params.csv stood here (values of no recorded source): doubling it
        # left a mini-EU run identical to the last digit, so it acted on no result (KNOWN_ISSUES K72)
        el = pd.Series({c: (float(real_supply[c]) if c in real_supply else 0.0) for c in self.commodities})
        cols = [c for c in self.commodities if c in supply.columns]
        # each non-EU region's own-price elasticity from CAPRI's market model (p_elasSupp "CAL" of its CAPRI regions,
        # production-weighted; tools/build/build_supply_elas_nonEU.py; KNOWN_ISSUES K54-3), 0 where CAPRI has none
        # (_region_supply_elas); the per-product value above only for the EU rows (their supply comes from the supply
        # models)
        EV = self._region_supply_elas(list(supply.index), cols, el)
        if self.noneu_supply_nq:
            # CAPRI's market supply functions outside the EU (ProdNQ_ with its cross-price terms,
            # _noneu_market_supply_nq, applied below): no own-price elasticity on the non-EU rows; a product without
            # a ProdNQ_ row in CAPRI's Hessian keeps its base, as in CAPRI. Norway's supply-model products keep
            # their anticipation (replaced by its measured Hessian below)
            EV = EV.copy()
            eu_ = set(self.EU)
            for i_, r_ in enumerate(supply.index):
                if r_ in eu_:
                    continue
                sc_ = sup_cols.get(r_, set())
                for j_, c_ in enumerate(cols):
                    if c_ not in sc_:
                        EV[i_, j_] = 0.0
        self._welf_supply_EV = (list(supply.index), cols, EV)        # the welfare report (market/welfare.py)
        self._welf_noneu_nq = {}

        def _ratio_row(reg_):
            # the region's price ratios over cols (the bilateral market's own ratios, else the world ratios)
            if region_ratio is None or reg_ not in region_ratio.index:
                return ratio.reindex(cols).to_numpy(dtype=float)
            v_ = region_ratio.loc[reg_].reindex(cols).to_numpy(dtype=float)
            return np.maximum(np.where(np.isnan(v_), 1.0, v_), 1e-6)
        from capri_mod.market.supply_ad import anticipation_function
        if region_ratio is None:
            # the own-price response, written once in CasADi (market step G2b, supply_ad.anticipation_function)
            _S = supply[cols].to_numpy(dtype=float)
            supply[cols] = np.asarray(anticipation_function(*_S.shape)(
                _S, np.tile(ratio.reindex(cols).to_numpy(dtype=float), (_S.shape[0], 1)), np.ones_like(_S), EV))
            self._eu_market_supply_nq(supply, cols, lambda reg_: ratio.reindex(cols).to_numpy(dtype=float))
            self._add_eu_excluded(supply, cols, lambda reg_: ratio.reindex(cols).to_numpy(dtype=float))
        else:
            # in arrays (pandas arithmetic here was a sizeable share of each market evaluation; same values)
            rr = region_ratio.reindex(index=supply.index, columns=cols).to_numpy(dtype=float)
            rr = np.maximum(np.where(np.isnan(rr), 1.0, rr), 1e-6)
            ev = el.reindex(cols).to_numpy(dtype=float)
            # the own-price response (rr / SV)^E, SV the prices the supply models saw (1 for the other rows)
            E_, SV_ = EV.copy(), np.ones_like(rr)
            # the EU market regions' supply before the price response (the supply models' latest output): each of
            # CAPRI's two trade blocks
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
                E_[ie_], SV_[ie_] = ev, sv
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
                        SV_[i_, j] = sv[j]
            s_exo_sup = {reg: supply.loc[reg, cols].astype(float).copy() for reg in sup_cols}
            # written once in CasADi (market step G2b, supply_ad.anticipation_function)
            supply[cols] = np.asarray(anticipation_function(*rr.shape)(supply[cols].to_numpy(dtype=float), rr, SV_, E_))
            self._eu_market_supply_nq(supply, cols, lambda reg_: rr[list(supply.index).index(reg_)])
            # CAPRI's market supply function for the supply models' products (arm/market_model.gms ProdNQ_, the
            # Hessian measured on the supply models at the baseline, model._market_supply_hessian): linear in the
            # prices, through the supply models' latest output at the prices they saw
            # (arm/simu_calibration_to_supply.gms:360-368), with the cross-price terms; it replaces the own-price
            # anticipation for those products
            # one Hessian per EU block (the sum of its member states', CAPRIModel._split_hessian)
            _hs = self.par.supply_hessian or {}
            _hreg = dict(_hs.get("blocks") or {})
            _hcache = getattr(self, "_hess_cache", None)
            if not isinstance(_hcache, dict):
                _hcache = {}
            # per EU market region (each trade block): its Hessian's rows, the supply models' output and the
            # price change against what they saw
            items_ = {}
            for reg_, H in _hreg.items():
                if H is None or s_exo_eu is None or not len(H) or reg_ not in s_exo_eu or reg_ not in _sv_eu:
                    continue
                ie_ = list(supply.index).index(reg_)
                ck = (id(H), tuple(cols), tuple(exogenous_supply.columns))
                hc = _hcache.get(reg_)
                if hc is None or hc[0] != ck:
                    ex_cols = set(exogenous_supply.columns)
                    xs = [x for x in H.index if x in cols and x in ex_cols]
                    Hm_ = H.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float)
                    hc = (ck, xs, [cols.index(x) for x in xs], Hm_, self._hess_fn(f"hess_{reg_}", Hm_))
                    _hcache[reg_] = hc
                _, xs, xj, Hm, _hf = hc
                if xs:
                    s0 = s_exo_eu[reg_].to_numpy(dtype=float)[xj]
                    dP_ = self._nq_price_change(rr[ie_] - _sv_eu[reg_], cols)
                    items_[reg_] = (H, xs, xj, _hf, s0, dP_, self._milk_terms(cols, xs, H, reg_))
            # the member states' raw milk inside the market (audit M5) with the young-animal markets, cleared together:
            # once over all EU market regions (the dairy block is one solve over the member states, each at its own
            # region's prices; CAPRI's trade blocks as its one EU, 29 October 2026)
            if items_ and all(it_[6] is not None for it_ in items_.values()):
                extra_ = self._milk_and_yani_clear_all(
                    {reg_: (it_[0], it_[1], it_[5], it_[6]) for reg_, it_ in items_.items()}, cols, world_prices,
                    exogenous_supply, ratio_of=lambda reg_: rr[list(supply.index).index(reg_)])
            else:
                extra_ = {reg_: self._yani_clear(reg_, it_[0], it_[1], cols, it_[5]) for reg_, it_ in items_.items()}
            for reg_, (H, xs, xj, _hf, s0, dP_, mt) in items_.items():
                # CAPRI's ProdNQ_ with the measured Hessian, written once in CasADi (market step G2b, supply_ad.py)
                q = np.asarray(_hf(s0, dP_, np.broadcast_to(np.asarray(extra_[reg_], float), s0.shape))[0]).ravel()
                keep = s0 > 1e-6
                vals = supply.loc[reg_, cols].to_numpy(dtype=float).copy()
                vals[np.asarray(xj)[keep]] = q[keep]
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
                _hf = self._hess_fn(f"hess_{reg}", Hm)
                s0 = s_exo_sup[reg].to_numpy(dtype=float)[xj]
                dP_ = self._nq_price_change(rr[i_] - _sv_sup[reg], cols)
                mk_ = self._sup_milk_terms(reg, Hs, cols, xs, _sv_sup[reg])
                # CAPRI's ProdNQ_ with the measured Hessian, written once in CasADi (market step G2b, supply_ad.py); the
                # floor at 0 applies to the rows kept below, as before
                _q = lambda dp_: [np.asarray(v_).ravel() for v_ in _hf(s0, dp_, np.broadcast_to(
                    np.asarray(self._yani_clear(reg, Hs, xs, cols, dp_), float), s0.shape))]
                if mk_ is not None:
                    # Norway's raw milk inside the market (step F; CAPRI simu_calibration_to_supply.gms l. 423-427):
                    # the MILK row without the milk price (its own term is in the dairy block, _sup_milk_delivered),
                    # then every row with the milk price change from the dairy block's latest price
                    iM_ = xs.index("MILK")
                    q_nm, q_nm_raw = _q(dP_)
                    self.ev.sup_milk_cross[reg] = float(q_nm_raw[iM_] - s0[iM_])
                    dP_[cols.index("MILK")] = mk_["dL"]
                    q = _q(dP_)[0]
                    q[iM_] = q_nm[iM_]
                else:
                    q = _q(dP_)[0]
                keep = s0 > 1e-6
                vals = supply.loc[reg, cols].to_numpy(dtype=float).copy()
                vals[np.asarray(xj)[keep]] = q[keep]
                supply.loc[reg, cols] = vals
            # the EU's units outside a run on a subset (K83): their member states' market supply functions
            self._add_eu_excluded(supply, cols, lambda reg_: rr[list(supply.index).index(reg_)])
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
                Sr = {r: float(v) for r, v in self.eu_rows(exogenous_supply[["MILK"]])["MILK"].items()}
            else:
                Sr = None
            # the EU's units outside a run on a subset (K83): their raw milk at its base, moved by their member
            # states' ProdNQ_ of MILK in the dairy block (_excluded_milk_resp); with no EU unit in the run, theirs alone
            _xr_m = self._eu_excluded_rows()
            if Sr is None:
                Sr = ({r: 0.0 for r in self.EU} if (_xr_m is not None and "MILK" in _xr_m.columns)
                      else {r: float(self.par.base_production.at[r, "MILK"]) for r in self.EU})
            if _xr_m is not None and "MILK" in _xr_m.columns:
                Sr = {r_: float(v_) + (float(_xr_m.at[r_, "MILK"]) if r_ in _xr_m.index else 0.0)
                      for r_, v_ in Sr.items()}
            S = sum(Sr.values())
            S0 = float(self.par.dairy_S0 or S)
            _m0 = self.par.dairy_S0_ms or {}
            _m = self._milk_by_ms(self._with_eu_excluded(exogenous_supply))
            _mr = ({ms: (_m[ms] / q0 if (q0 > 0 and ms in _m) else 1.0) for ms, q0 in _m0.items()} if (_m0 and _m)
                   else (S / S0 if S0 > 0 else 1.0))
            _m5 = self.ev.dairy_m5_now
            if _m5 is not None:
                # the block solved with the member states' raw milk responding to their prices (audit M5,
                # _milk_and_yani_clear_all): raw milk delivered as it responded
                res = _m5
                self.ev.dairy_m5_now = None
                _dq = self.ev.milk_dq_now or {}
                Sr = {r_: float(Sr[r_]) + float(_dq.get(r_, 0.0)) for r_ in Sr}
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
                # Norway (RMSSUP): raw milk from its supply models, moved inside the market by its raw milk supply
                # function (ProdNQ_ MILK re-anchored to the models' milk, simu_calibration_to_supply.gms l. 423-427;
                # market.sup_milk_in_market; off: fixed at the models'), its block's FMIL index from its herds; the
                # other regions: CAPRI's raw milk supply function
                mr_ = None
                m0_ = (self.par.sup_milk0 or {}).get(r)
                if r in exo_sup and "MILK" in exo_sup[r].index and m0_:
                    m_now = float(exo_sup[r]["MILK"])
                    mr_ = m_now / m0_
                    supply.at[r, "MILK"] = m_now
                    self.ev.sup_milk_now[r] = m_now
                fi_ = float((self.seen.fmil_index_sup or {}).get(r, 1.0)) if mr_ is not None else 1.0
                # CAPRI's raw milk supply function (ProdNQ_ MILK) with its cross-price terms: the shift from the
                # other products' prices (the block holds the own-price term)
                m_sh = self._noneu_milk_shift(r, cols, _ratio_row(r)) if (mr_ is None and self.noneu_supply_nq) else {}
                sm_ = self._sup_milk_delivered(r, prm, m_now, m0_) if mr_ is not None else None
                if sm_ is not None:
                    # Norway: the milk its supply models deliver, moved by its own milk price and the other prices
                    # (the market supply Hessian's MILK row), against its dairies' demand inside its block
                    prm_, shift_ = sm_
                    res_r = self._dairy_solve(prm_, tr, None, fi_, milk_shift=shift_)
                    q_ = m0_ * float(res_r["milk_supply_ratio"])
                    supply.at[r, "MILK"] = q_
                    self.ev.sup_milk_now[r] = q_
                else:
                    res_r = self._dairy_solve(prm, tr, mr_, fi_, milk_shift=sum(m_sh.values()))
                res_r["milk_shift_rms"] = m_sh
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
        if self.noneu_supply_nq:
            # the non-EU regions' market supply functions, at the regions' prices and their dairies' raw milk price
            _wl = self.ev.dairy_world_last or {}
            _wp = self._dairy_world_params() or {}

            def _milk_ratio(reg_):
                res_ = _wl.get(reg_)
                if not res_ or reg_ not in _wp:
                    return 1.0
                return 1.0 + float(res_["z"][_wp[reg_]["iM"]])
            self._noneu_market_supply_nq(supply, cols, _ratio_row, _milk_ratio, sup_cols)
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

    def _milk_terms(self, cols, xs, H, reg):
        """The member states' raw milk terms of the market supply Hessian (supply_hessian["ms"], per country summed
        to CAPRI's member state of the dairy block), for the member states of the EU market region reg (one of
        CAPRI's trade blocks): {"ms": [...], "h": own response (kt per unit of price level),
        "row": member state x cols (MILK's response to the products' prices), "rowY": member state x young-animal
        goods, "col": xs x member state (the products' response to the member state's milk price), "colY": young
        goods x member state, "goods": young-animal goods}; None without data."""
        if not self.seen.milk_seen_ms or not self._dairy_params():
            return None
        hs = (self.par.supply_hessian or {}).get("ms") or {}
        if not hs:
            return None
        st = (self.seen.yani_state or {}).get(reg) or {}
        goods = [g for g in (st.get("goods") or []) if ("YANI:" + g) in H.index and ("YANI:" + g) in H.columns]
        ck = (id(hs), tuple(cols), tuple(xs), tuple(goods), reg)
        cache_ = self.__dict__.setdefault("_milk_terms_cache_reg", {})
        c_ = cache_.get(reg)
        if c_ is not None and c_[0] == ck:
            return c_[1]
        sup_of = getattr(self, "sup_region_of_country", lambda c: None)
        agg = {}
        for cc, h in hs.items():
            if sup_of(cc) is not None or "MILK" not in h.columns or "MILK" not in h.index:
                continue
            ms = self._DAIRY_MS.get(str(cc)[:2], str(cc)[:2]) + "000000"
            agg[ms] = h if ms not in agg else agg[ms].add(h, fill_value=0.0)
        mss = sorted(m for m in agg if m in self._dairy_params().get("ms", {})
                     and (self.eu_region_of_ms(m) or self.EU[0]) == reg)
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
        cache_[reg] = (ck, out)
        return out

    def _excluded_milk_resp(self, cols, ratio_of, m0) -> dict:
        """K83: the raw milk of the EU's units outside a run on a subset, per member state, as CAPRI's ProdNQ_ of MILK
        moves it (eu_market_supply_nq.csv): delivered = x (1 + (sum_{y != MILK} h_My (y's ratio - 1) + h_MM (L - 1)) /
        CAPRI's MILK production at the calibration point), x the units' base raw milk, L the member state's raw milk
        price ratio; as the dairy block's form (constant at the price level Ls, slope per unit of L - Ls) relative to
        the member state's base delivered milk m0: {ms: (constant at L = 1, slope)}. Empty where the run has every
        unit."""
        xb = self.seen.eu_excluded_base
        if xb is None or "MILK" not in xb.columns:
            return {}
        terms, q0 = self._eu_ms_supply_nq()
        ci = {c: j for j, c in enumerate(cols)}
        xm: dict = {}
        for cc, v in xb["MILK"].items():
            ms = capri_ms(cc)
            xm[ms] = xm.get(ms, 0.0) + float(v)
        out = {}
        for ms, x in xm.items():
            base = float(m0.get(ms, 0.0))
            pc = float(q0.get(ms, {}).get("MILK", 0.0))
            if not (x > 0 and base > 0):
                continue
            if not pc > 0:
                out[ms] = (x / base, 0.0)
                continue
            reg = self.eu_region_of_ms(ms)
            r_ = ratio_of(reg) if (ratio_of is not None and reg is not None) else None
            t_ms = terms.get(ms, {})
            cross = (sum(h * (float(r_[ci[y]]) - 1.0) for (x_, y), h in t_ms.items()
                         if x_ == "MILK" and y != "MILK" and y in ci) if r_ is not None else 0.0)
            hmm = float(t_ms.get(("MILK", "MILK"), 0.0))
            out[ms] = (x / base * (1.0 + cross / pc), x * hmm / (pc * base))
        return out

    def _milk_and_yani_clear_all(self, regs, cols, world_prices, exogenous_supply, ratio_of=None):
        """The young-animal markets (_yani_clear) and the member states' raw milk (dairy_block with the milk response)
        cleared together at the current product prices, over every EU market region at once (CAPRI's two trade
        blocks): the milk prices move the young animals' supply and the young-animal prices the milk supply
        (CAPRI's ProdNQ_ with p_hessNQSupp, solved jointly in its market model); a few rounds of the two linear
        clearings, the dairy block solved once per round over all member states, each at its own region's prices.
        regs {region: (H, xs, dP, mt)}. Returns {region: the products' supply change from both (rows xs)} and keeps
        the dairy block's solution for supply_response (ev.dairy_m5_now; ev.milk_dq_now per region)."""
        _m0 = self.par.dairy_S0_ms or {}
        # with the base raw milk of the EU's units outside a run on a subset (K83), as the base dairy_S0_ms has it
        _m = self._milk_by_ms(self._with_eu_excluded(exogenous_supply))
        _xb_ = self.seen.eu_excluded_base
        _xbm = self._milk_by_ms(_xb_) if _xb_ is not None else {}
        xr_milk = self._excluded_milk_resp(cols, ratio_of, _m0)
        mr_all = {m_: (_m[m_] / q_ if (q_ > 0 and m_ in _m) else 1.0) for m_, q_ in _m0.items()}
        tr = self._dairy_eu_prices(world_prices)
        S = {}
        for reg, (H, xs, dP, mt) in regs.items():
            mss = mt["ms"]
            q0 = np.array([float(_m0.get(m, 0.0)) for m in mss])
            st = (self.seen.yani_state or {}).get(reg) or {}
            S[reg] = dict(mss=mss, q0=q0,
                          Ls=np.array([float(self.seen.milk_seen_ms.get(m, 1.0)) for m in mss]),
                          mr0=np.array([(_m.get(m, 0.0) / q0[i]) if q0[i] > 0 else 1.0 for i, m in enumerate(mss)]),
                          r_seen=np.array([float(st.get("seen", {}).get(g, 1.0)) for g in mt["goods"]]),
                          dL=np.zeros(len(mss)), dY=np.zeros(len(mt["goods"])), yq=0.0)
        res = None
        for _ in range(4):
            resp = {}
            for reg, (H, xs, dP, mt) in regs.items():
                s_ = S[reg]
                ey = mt["colY"] @ s_["dL"] if len(mt["goods"]) else 0.0
                s_["yq"] = self._yani_clear(reg, H, xs, cols, dP, extra_y=ey)
                if len(mt["goods"]):
                    rn = (self.ev.yani_market_now or {}).get(reg) or {}
                    s_["dY"] = np.array([float(rn.get(g, s_["r_seen"][k])) for k, g in enumerate(mt["goods"])]) \
                        - s_["r_seen"]
                a = mt["row"] @ np.asarray(dP, float) + (mt["rowY"] @ s_["dY"] if len(mt["goods"]) else 0.0)
                for i, m in enumerate(s_["mss"]):
                    q0i = s_["q0"][i]
                    resp[m] = (s_["mr0"][i] + (a[i] / q0i if q0i > 0 else 0.0), (mt["h"][i] / q0i if q0i > 0 else 0.0),
                               s_["Ls"][i])
            # the raw milk of the EU's units outside a run on a subset (K83): CAPRI's ProdNQ_ of MILK of their member
            # state, in the block's form (delivered at the seen price Ls, slope); their base share, in mr0 and mr_all,
            # replaced by it
            for m, (c1, k1) in xr_milk.items():
                xs_ = _xbm.get(m, 0.0) / float(_m0[m]) if float(_m0.get(m, 0.0)) > 0 else 0.0
                if m in resp:
                    mb, kk, Ls_ = resp[m]
                    resp[m] = (mb - xs_ + c1 + k1 * (Ls_ - 1.0), kk + k1, Ls_)
                else:
                    resp[m] = (c1, k1, 1.0)
            res = self.dairy_block(tr, {**mr_all, **{m: v[0] for m, v in resp.items()}}, milk_resp=resp)
            if res is None:
                return {reg: S[reg]["yq"] for reg in regs}
            done = True
            for reg in regs:
                s_ = S[reg]
                dL_new = np.array([float(res["ms_price_ratio"][m]["MILK"]) - s_["Ls"][i]
                                   for i, m in enumerate(s_["mss"])])
                done = done and float(np.max(np.abs(dL_new - s_["dL"]))) < 1e-10 if len(dL_new) else done
                s_["dL"] = dL_new
            if done:
                break
        self.ev.dairy_m5_now = res
        # raw milk delivered against the supply models' (kt) per EU market region: the milk row of the market carries it
        self.ev.milk_dq_now = {reg: float(sum((float(res["ms_price_ratio"][m]["milk_delivered"]) - S[reg]["mr0"][i])
                                              * S[reg]["q0"][i] for i, m in enumerate(S[reg]["mss"])))
                               for reg in regs}
        # the member states with only units outside the run (K83): their raw milk's change from its base
        _inS = {m for reg in regs for m in S[reg]["mss"]}
        for m in xr_milk:
            if m in _inS:
                continue
            rg_ = self.eu_region_of_ms(m)
            if rg_ in self.ev.milk_dq_now:
                self.ev.milk_dq_now[rg_] += (float(res["ms_price_ratio"][m]["milk_delivered"])
                                             - float(mr_all.get(m, 1.0))) * float(_m0.get(m, 0.0))
        return {reg: S[reg]["yq"] + regs[reg][3]["col"] @ S[reg]["dL"] for reg in regs}

    def _with_eu_excluded(self, exogenous_supply):
        """The supply models' rows per country with the base output of the EU's units outside the run added (K83);
        the rows themselves where the run has every unit."""
        xb = self.seen.eu_excluded_base
        if xb is None or exogenous_supply is None:
            return exogenous_supply
        return exogenous_supply.add(xb.reindex(columns=exogenous_supply.columns).fillna(0.0), fill_value=0.0)

    def _eu_excluded_rows(self):
        """The base output of the EU's units outside the run per EU market region (each trade block) and
        market commodity (K83); None where the run has every unit."""
        xb = self.seen.eu_excluded_base
        if xb is None:
            return None
        return self.eu_rows(xb)

    def _eu_ms_supply_nq(self):
        """CAPRI's market supply functions of the EU member states, every product (ProdNQ_,
        tools/build/build_eu_market_supply_nq.py): ({ms: {(x, y): kt per unit of y's price ratio}}, {ms: {x: CAPRI's
        production at the calibration point}})."""
        c = getattr(self, "_eu_ms_nq_cache", None)
        if c is not None:
            return c
        terms: dict = {}
        for r in self._inp().csv("eu_market_supply_nq.csv", keep_default_na=False).itertuples(index=False):
            if r.ms in _EU_MS and r.y:
                d = terms.setdefault(r.ms, {})
                d[(r.x, r.y)] = d.get((r.x, r.y), 0.0) + float(r.h_ratio)
        q0: dict = {}
        for r in self._inp().csv("eu_market_supply_base.csv").itertuples(index=False):
            if r.ms in _EU_MS:
                q0.setdefault(r.ms, {})[r.x] = q0.get(r.ms, {}).get(r.x, 0.0) + float(r.prod_cal)
        self._eu_ms_nq_cache = (terms, q0)
        return self._eu_ms_nq_cache

    #: products whose EU supply the market's own blocks set (raw milk and the dairy products: the dairy block; oils and
    #: cakes: crushing) or that CAPRI's member-state functions already supply for the whole EU (EU_MARKET_SUPPLY): not
    #: in the excluded units' term (K83)
    def _excluded_skip(self) -> frozenset:
        sk = set(self.EU_MARKET_SUPPLY) | {"MILK"} | set(self.DAIRY_TRADED.values())
        for o, c in self.CRUSH_CHAINS.values():
            sk |= {o, c}
        return frozenset(sk)

    def _add_eu_excluded(self, supply, cols, ratio_of) -> None:
        """KNOWN_ISSUES K83: the EU's supply from its units outside a run on a subset, added to each EU market region:
        per member state and product, those units' base output moved as CAPRI's ProdNQ_ of the member state moves it,
        q = base x (1 + sum_y h_xy (y's price ratio - 1) / CAPRI's production at the calibration point). CAPRI keeps a
        country switched off in the market with its ProdNQ_ (it leaves RMSSUP, capmod/create_sim_ini_gdx.gms l. 73);
        the price ratio is the member state's EU market region's against base. Nothing where the run has every unit."""
        xb = self.seen.eu_excluded_base
        if xb is None:
            return
        terms, q0 = self._eu_ms_supply_nq()
        ci = {c: j for j, c in enumerate(cols)}
        skip = self._excluded_skip()
        add: dict = {}
        for cc, row in xb.iterrows():
            ms = capri_ms(cc)
            reg = self.eu_region_of_ms(ms)
            if reg is None or reg not in supply.index:
                continue
            r_ = ratio_of(reg)
            t_ms, q_ms = terms.get(ms, {}), q0.get(ms, {})
            for x, b in row.items():
                b = float(b)
                if not b > 0 or x not in ci or x in skip:
                    continue
                qc = float(q_ms.get(x, 0.0))
                rel = (sum(h * (float(r_[ci[y]]) - 1.0) for (x_, y), h in t_ms.items() if x_ == x and y in ci) / qc
                       if qc > 0 else 0.0)
                add[(reg, x)] = add.get((reg, x), 0.0) + max(b * (1.0 + rel), 0.0)
        for (reg, x), v in add.items():
            supply.at[reg, x] = float(supply.at[reg, x]) + v

    def _eu_market_supply_nq_params(self) -> dict:
        """CAPRI's market supply functions of the EU products no supply model produces (EU_MARKET_SUPPLY: other
        vegetable oils, the fish products; ProdNQ_, tools/build/build_eu_market_supply_nq.py), summed per EU market
        region: {region: {(x, y): kt per unit change of y's price ratio}}."""
        c = getattr(self, "_eu_msnq_cache", None)
        if c is not None:
            return c
        out: dict = {}
        for r in self._inp().csv("eu_market_supply_nq.csv", keep_default_na=False).itertuples(index=False):
            # the EU's member states only: until 31 October 2026 the file held Norway too, whose terms this line put
            # into EU27 (Norway's own function is in noneu_market_supply_nq.csv); a column without a model price (y
            # empty) is held
            rg = self.eu_region_of_ms(r.ms) if r.ms in _EU_MS else None
            if rg is None or not r.y or r.x not in self.EU_MARKET_SUPPLY:
                continue
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
            # CAPRI's ProdNQ_ written once in CasADi (market step G2b, capri_mod/market/supply_ad.py); raw milk as a
            # price ratio of the market (its column here), as before the move
            fr = self._nq_rows(("eu", rg), terms, lambda t_: {x: {y: h for (x_, y), h in t_.items() if x_ == x}
                                                              for x in self.EU_MARKET_SUPPLY}, cols, None)
            if fr is None:
                continue
            f, rows, _rms = fr
            r_ = np.asarray(ratio_of(rg), dtype=float)
            q0 = self._nq_q0(rg, rows)
            q, _dq = f(q0, r_, float(r_[ci["MILK"]]) if "MILK" in ci else 1.0, np.zeros(0), np.zeros(len(rows)))
            q = np.asarray(q).ravel()
            for i, x in enumerate(rows):
                if x in supply.columns and q0[i] > 0:
                    supply.at[rg, x] = float(q[i])

    def _noneu_nq_params(self) -> dict:
        """CAPRI's market supply functions of the non-EU market regions (arm/market_model.gms ProdNQ_; KNOWN_ISSUES
        K54-3; tools/build/build_noneu_market_supply_nq.py), summed over each trade region's CAPRI regions:
        {trade region: {"rows": {x: {y: h}}, "milk": {y: h}}}, h in kt per unit change of y's price ratio (CAPRI's
        p_hessNQSupp x (PPRI0_y - support_y) / INPE, the support per tonne of PPri_: Switzerland's PSEd, K146). "rows": the market products' supply, y over the market products and raw milk;
        "milk": per CAPRI region, the raw milk supply's terms in the other prices (its own term is the dairy block's).
        "fede": {CAPRI region: {x: h}} and "milk_fede": {CAPRI region: h}, the terms in the region's own feed energy
        price FEDE (CAPRI's FeedBal_, audit M3: one price per CAPRI region, so kept per region). Columns without a model
        price (the land rents TCRP, FRUN, FODFAL) are not in the file's model columns: held at their calibration value
        (registered)."""
        c = getattr(self, "_noneu_nq_cache", None)
        if c is not None:
            return c
        out: dict = {}
        eu_ = set(self.EU)
        land = set(self.MARKET_LAND)
        for t in self._inp().csv("noneu_market_supply_nq.csv").itertuples(index=False):
            y = t.y if isinstance(t.y, str) else ""
            if not y or t.trade_region not in self.regions or t.trade_region in eu_:
                continue
            if y in land or t.x in land:
                continue                          # the land market's rows and columns (_noneu_land_params)
            d = out.setdefault(t.trade_region, {"rows": {}, "milk": {}, "fede": {}, "milk_fede": {}})
            if y == "FEDE":
                if t.x == "MILK":
                    d["milk_fede"][t.rms] = d["milk_fede"].get(t.rms, 0.0) + float(t.h_ratio)
                else:
                    f_ = d["fede"].setdefault(t.rms, {})
                    f_[t.x] = f_.get(t.x, 0.0) + float(t.h_ratio)
                continue
            if t.x == "MILK":
                if y != "MILK":
                    m_ = d["milk"].setdefault(t.rms, {})
                    m_[y] = m_.get(y, 0.0) + float(t.h_ratio)
            else:
                r_ = d["rows"].setdefault(t.x, {})
                r_[y] = r_.get(y, 0.0) + float(t.h_ratio)
        self._noneu_nq_cache = out
        return out

    def _noneu_milk_shift(self, reg, cols, r_) -> dict:
        """The change of the raw milk supply of each of the region's CAPRI regions from the prices of the other
        products (ProdNQ_ MILK's cross-price terms), kt; the dairy block adds the own-price term."""
        prm = self._noneu_nq_params().get(reg) or {}
        terms = prm.get("milk") or {}
        ci = {c: j for j, c in enumerate(cols)}
        out = {rms: float(sum(h * (float(r_[ci[y]]) - 1.0) for y, h in t.items() if y in ci))
               for rms, t in terms.items()}
        fede = self.ev.fede_now or {}
        for rms, h in (prm.get("milk_fede") or {}).items():
            out[rms] = out.get(rms, 0.0) + h * (float(fede.get(rms, 1.0)) - 1.0)     # FEDE (audit M3)
        for rms, dq in self._noneu_land_shift(reg, by_rms=True).get("MILK", {}).items():
            out[rms] = out.get(rms, 0.0) + dq                                        # the land rents (stage 7)
        return out

    # ------------------------------------------------------------------
    # CAPRI's market land block outside the EU (stage 7 of the market move; arm/market_model.gms l. 1529-1572,
    # 1696-1790)
    # ------------------------------------------------------------------
    def _noneu_land_params(self) -> dict:
        """Per non-EU CAPRI region with a land market (tools/build/build_noneu_market_supply_nq.py
        build_land_market): {rms: {"tr": trade region, "lu": the MNL's land types, "free": indexes of the free rents
        (TCRP, FODFAL, FRUN), "alu", "B" (p_bLu, per EUR/ha), "avail" (ARTO - INLW, 1000 ha), "rent0", "L0" (the free
        types' land at calibration), "H" (free x free: the land demand rows' rent terms, p_hessNQSupp / INPE, 1000 ha
        per EUR/ha; the rows' sign turned as arm/market1.gms l. 593), "rows" ({lu: {y: h_ratio}}: the land demand's
        terms in the model prices, MILK and FEDE), "prod" ({x: {lu: h / INPE}}: the products' and raw milk's terms in
        the rents)}. {} with market.noneu_land_market off."""
        c = getattr(self, "_noneu_land_cache", None)
        if c is not None:
            return c
        out: dict = {}
        if not (self.noneu_land_market and self.noneu_supply_nq):
            self._noneu_land_cache = out
            return out
        inp = self._inp()
        eu_ = set(self.EU)
        lm = inp.csv("noneu_land_market.csv", keep_default_na=False)
        for rms, g in lm.groupby("rms", sort=True):
            tr = str(g.trade_region.iloc[0])
            if tr not in self.regions or tr in eu_:
                continue
            g = g.set_index("lu")
            lus = [u for u in ("FORE", "ARTIF", "OLND") + self.MARKET_LAND if u in g.index]
            free = [i for i, u in enumerate(lus) if int(g.at[u, "endogenous"]) == 1]
            out[rms] = {"tr": tr, "lu": lus, "free": free, "alu": g.loc[lus, "alu"].to_numpy(dtype=float),
                        "B": np.zeros((len(lus), len(lus))), "avail": float(g.avail_kha.iloc[0]),
                        "rent0": g.loc[lus, "rent"].to_numpy(dtype=float),
                        "L0": np.array([float(g.at[lus[i], "land_kha"]) for i in free]),
                        "H": np.zeros((len(free), len(free))), "rows": {lus[i]: {} for i in free}, "prod": {}}
        for t in inp.csv("noneu_land_mnl.csv", keep_default_na=False).itertuples(index=False):
            d = out.get(t.rms)
            if d is not None and t.lu in d["lu"] and t.lu1 in d["lu"]:
                d["B"][d["lu"].index(t.lu), d["lu"].index(t.lu1)] = float(t.b)
        land = set(self.MARKET_LAND)
        for t in inp.csv("noneu_market_supply_nq.csv", keep_default_na=False).itertuples(index=False):
            d = out.get(t.rms)
            if d is None or not t.y:
                continue
            fl = [d["lu"][i] for i in d["free"]]
            if t.x in land:
                if t.x not in fl:
                    continue
                if t.y in land:
                    if t.y in fl:
                        d["H"][fl.index(t.x), fl.index(t.y)] += float(t.h) / float(t.inpe)
                else:
                    d["rows"][t.x][t.y] = d["rows"][t.x].get(t.y, 0.0) + float(t.h_ratio)
            elif t.y in fl:
                p_ = d["prod"].setdefault(t.x, {})
                p_[t.y] = p_.get(t.y, 0.0) + float(t.h) / float(t.inpe)
        self._noneu_land_cache = out
        return out

    def noneu_land_solve(self, ratio: pd.DataFrame, milk_ratio: Optional[dict] = None,
                         fede: Optional[dict] = None, start: Optional[dict] = None) -> dict:
        """The rents of the non-EU land markets at the market's prices: per CAPRI region the free rents r (TCRP,
        FODFAL, FRUN) at which the MNL land supply equals the land demand of ProdNQ_,

            (ARTO - INLW) exp(aLU_l + sum_k bLu_lk r_k) / sum_m exp(aLU_m + sum_k bLu_mk r_k)
                = L0_l + sum_y h_ly (price ratio_y - 1) + sum_k H_lk (r_k - r0_k)          (l free),

        LandSupplyMNL_ = LndSupplyEqualsDemand_ with ProdNQ_'s land rows (arm/market_model.gms l. 1543-1572, 1696-1745;
        the rents of FORE, ARTIF, OLND fixed; rent = producer price + PSEd, rentFromProdpriceLand_, so the change of the
        rent is the change of the land's producer price). Newton's method on the three rents from start (the latest
        solution) or the calibration point. ratio: the trade regions' producer price ratios (regions x commodities);
        milk_ratio: {trade region: raw milk price ratio}; fede: {CAPRI region: FEDE ratio}. Returns {rms: the change
        of the free rents from calibration (EUR/ha), in the order of params["free"]}."""
        P = self._noneu_land_params()
        mr = milk_ratio or {}
        fe = fede or {}
        st = start or {}
        out = {}
        for rms, d in P.items():
            tr = d["tr"]
            if tr not in ratio.index or not d["free"]:
                continue
            ra = ratio.loc[tr]
            fl = [d["lu"][i] for i in d["free"]]
            base = d["L0"].copy()
            for i, u in enumerate(fl):
                v = 0.0
                for y, h in d["rows"][u].items():
                    if y == "FEDE":
                        v += h * (float(fe.get(rms, 1.0)) - 1.0)
                    elif y == "MILK":
                        v += h * (float(mr.get(tr, 1.0)) - 1.0)
                    elif y in ra.index:
                        v += h * (float(ra[y]) - 1.0)
                base[i] += v
            fr = np.asarray(d["free"])
            dr = np.array(st.get(rms, np.zeros(len(fr))), dtype=float)
            scale = np.maximum(d["L0"], 1.0)
            # the land block's equations written once in CasADi (market step G2b, supply_ad.land_residual_function),
            # with their exact Jacobian; this Newton is the solver until the market NLP (G3) takes the rents as unknowns
            lf = self.__dict__.setdefault("_land_fn_cache", {}).get(rms)
            if lf is None or lf[0] is not d:
                from capri_mod.market.supply_ad import land_residual_function
                lf = (d, land_residual_function(f"land_{rms}", d))
                self._land_fn_cache[rms] = lf

            def F(dr_):
                Fv, J = lf[1](dr_, base)
                return np.asarray(Fv).ravel(), np.asarray(J).reshape(len(fr), len(fr))
            Fv, J = F(dr)
            _stall_tol = float(_settings().get("market.land_stall_tol"))
            for _ in range(100):
                if np.max(np.abs(Fv) / scale) < 1e-13:
                    break
                step = np.linalg.solve(J, -Fv)
                t = 1.0
                n0 = np.max(np.abs(Fv) / scale)
                while True:
                    F1, J1 = F(dr + t * step)
                    if np.max(np.abs(F1) / scale) < n0 or t < 1e-6:
                        break
                    t *= 0.5
                dr, Fv, J = dr + t * step, F1, J1
            else:
                # the 1e-13 target not met in 100 steps: accepted where the residual is within market.land_stall_tol
                # (round-off: the line search no longer reduces it), else the run stops
                if not np.max(np.abs(Fv) / scale) < _stall_tol:
                    raise RuntimeError(f"market: the land market of {rms} did not clear (residual {np.max(np.abs(Fv)):.3g})")
            out[rms] = dr
        return out

    def land_by_type(self, land: Optional[dict]) -> Optional[dict]:
        """{rms: change of the free rents} (noneu_land_solve) as {rms: {land type: EUR/ha}}; None for None."""
        if not land:
            return None
        P = self._noneu_land_params()
        return {rms: dict(zip([P[rms]["lu"][i] for i in P[rms]["free"]], (float(x) for x in v)))
                for rms, v in land.items() if rms in P}

    def _noneu_land_shift(self, reg, by_rms: bool = False) -> dict:
        """The change of the supply of the trade region's products from its CAPRI regions' land rents (ProdNQ_'s
        terms in the rents, kt): {x: kt}, or {x: {rms: kt}} with by_rms."""
        land = self.ev.land_now or {}
        out: dict = {}
        for rms, d in self._noneu_land_params().items():
            if d["tr"] != reg or rms not in land:
                continue
            fl = [d["lu"][i] for i in d["free"]]
            dr = dict(zip(fl, land[rms]))
            for x, t in d["prod"].items():
                v = sum(h * dr.get(u, 0.0) for u, h in t.items())
                if by_rms:
                    out.setdefault(x, {})[rms] = out.get(x, {}).get(rms, 0.0) + v
                else:
                    out[x] = out.get(x, 0.0) + v
        return out

    def _noneu_market_supply_nq(self, supply, cols, ratio_of, milk_ratio_of, sup_cols):
        """The non-EU market regions' supply of the market products as CAPRI's ProdNQ_ (market audit step D, K54-3):
        base supply + sum_y h_xy x (y's price ratio - 1), y over the products' prices and the region's raw milk price
        (its dairy block's). The constant is CAPRI's calibration point, the market's base (no supply model to
        recalibrate to). Norway's supply-model products are its supply models' (left as they are). Replaces the
        own-price constant-elasticity function of each product (market.noneu_supply_nq = false)."""
        P = self._noneu_nq_params()
        for reg, d in P.items():
            if reg not in supply.index:
                continue
            # CAPRI's ProdNQ_ written once in CasADi (market step G2b, capri_mod/market/supply_ad.py)
            fr = self._nq_rows(("noneu", reg), d["rows"], None, cols, d.get("fede") or {})
            if fr is None:
                continue
            f, rows, rms = fr
            skip = sup_cols.get(reg, set())
            fede = self.ev.fede_now or {}                      # each CAPRI region's feed energy price (audit M3)
            rec = self._welf_noneu_nq.setdefault(reg, {})
            lshift = self._noneu_land_shift(reg)
            q0 = self._nq_q0(reg, rows)
            q, dq = f(q0, np.asarray(ratio_of(reg), dtype=float), float(milk_ratio_of(reg)),
                      np.array([float(fede.get(s_, 1.0)) for s_ in rms]),
                      np.array([float(lshift.get(x, 0.0)) for x in rows]))
            q, dq = np.asarray(q).ravel(), np.asarray(dq).ravel()
            for i, x in enumerate(rows):
                if x in skip or x not in supply.columns or not q0[i] > 0:
                    continue
                supply.at[reg, x] = float(q[i])
                rec[x] = (float(q0[i]), float(dq[i]))

    def _nq_rows(self, key, src, regroup, cols, fede_terms):
        """The compiled ProdNQ_ function of one market region (supply_ad.nq_rows_function), cached per region, its
        parameter object (src, the cached parameters) and the column list: (Function, rows, CAPRI regions of the feed
        energy prices) or None when the region has no row. regroup: src to {x: {y: h}} (None: src is that)."""
        from capri_mod.market.supply_ad import build_rows, nq_rows_function
        cache = self.__dict__.setdefault("_nq_rows_cache", {})
        ck = (id(src), tuple(cols))
        hit = cache.get(key)
        if hit is None or hit[0] != ck:
            a = build_rows(regroup(src) if regroup is not None else src, cols, fede_terms)
            f = (nq_rows_function(f"prodnq_{key[0]}_{key[1]}", len(cols), a["H"], a["hm"], a["HF"])
                 if a["rows"] else None)
            hit = (ck, f, a["rows"], a["rms"])
            cache[key] = hit
        return None if hit[1] is None else (hit[1], hit[2], hit[3])

    def _hess_fn(self, name, Hm):
        """The compiled ProdNQ_ of a measured Hessian (supply_ad.hess_rows_function), cached on the matrix's values."""
        from capri_mod.market.supply_ad import hess_rows_function
        cache = self.__dict__.setdefault("_hess_fn_cache", {})
        key = (name, Hm.shape, hash(Hm.tobytes()))
        f = cache.get(key)
        if f is None:
            f = hess_rows_function(name, Hm)
            cache[key] = f
        return f

    def _nq_q0(self, reg, rows) -> np.ndarray:
        """The market's base supply of the rows (the constant of ProdNQ_), 0 where the product has no column."""
        bp = self.par.base_production
        return np.array([float(bp.at[reg, x]) if x in bp.columns else 0.0 for x in rows])

    def _sup_milk_terms(self, reg, Hs, cols, xs, sv):
        """Norway's raw milk in the market (market.sup_milk_in_market, step F): CAPRI keeps ProdNQ_ MILK of the
        regions with supply models in the market, its constant re-anchored to the models' milk
        (arm/simu_calibration_to_supply.gms l. 198-201, 423-427: v_prodQuant MILK not fixed, bounds 0.1 to 10 x the
        level). Returns {"k": the Hessian's own milk term (kt per unit of price level), "L": the milk price level the
        region's models saw, "dL": the milk price change the products respond to (the region's dairy-block price of
        the latest evaluation against L)}, or None (switch off, no MILK row and column, no milk in the models)."""
        if not self.sup_milk_in_market or "MILK" not in xs or "MILK" not in cols or "MILK" not in Hs.columns:
            return None
        k = float(Hs.at["MILK", "MILK"])
        if not k > 0:
            return None
        L = float(sv[cols.index("MILK")])
        prev = (((self.ev.dairy_world_last or {}).get(reg) or {}).get("price_ratio") or {}).get("MILK")
        t = {"k": k, "L": L, "dL": (float(prev) - L) if prev is not None else 0.0}
        self.ev.setdefault("sup_milk_terms", {})[reg] = t
        self.ev.setdefault("sup_milk_cross", {})
        return t

    def _sup_milk_delivered(self, reg, prm, m_now, m0):
        """Norway's dairy block with its raw milk supply function (_sup_milk_terms): delivered = m_now + k x (milk
        price level - L) + the MILK row's response to the other prices (ev.sup_milk_cross); in the block's units (its
        base delivery Q0 against the models' base m0): the slope SM = k Q0 / m0 per unit of z_M (milk price ratio - 1)
        and the shift Q0 (m_now / m0 - 1) + Q0 / m0 (k (1 - L) + cross). Returns (block parameters with SM, shift) or
        None."""
        t = (self.ev.sup_milk_terms or {}).get(reg)
        if t is None or not m0:
            return None
        Q0 = float(prm["Q0"][prm["iM"]])
        cross = float((self.ev.sup_milk_cross or {}).get(reg, 0.0))
        prm_ = dict(prm)
        prm_["SM"] = t["k"] * Q0 / m0
        shift = Q0 * (m_now / m0 - 1.0) + Q0 / m0 * (t["k"] * (1.0 - t["L"]) + cross)
        return prm_, shift

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
        hit = cache.get(ck)
        if hit is None or hit[0] is not H:
            # yaniMarket_ in CasADi (supply_ad.yani_function, step G2g), rebuilt when the Hessian or the rows change
            # (the region's former entries dropped)
            from capri_mod.market.supply_ad import yani_function
            for k_ in [k_ for k_ in cache if k_[0] == reg]:
                del cache[k_]
            yi = ["YANI:" + g for g in goods]
            hit = cache[ck] = (H, yani_function(
                f"yani_{len(goods)}", H.reindex(index=yi, columns=cols).fillna(0.0).to_numpy(dtype=float),
                H.reindex(index=yi, columns=yi).fillna(0.0).to_numpy(dtype=float),
                H.reindex(index=list(xs), columns=yi).fillna(0.0).to_numpy(dtype=float)))
        f = hit[1]
        n_now = np.array([float(st["net"].get(g, 0.0)) for g in goods])
        ref = np.array([float(st["ref"].get(g, 0.0)) for g in goods])
        r_seen = np.array([float(st["seen"].get(g, 1.0)) for g in goods])
        # extra_y: the young animals' supply change from the member states' milk prices (_milk_and_yani_clear_all)
        ex = np.broadcast_to(np.asarray(extra_y, float), n_now.shape)
        dP = np.asarray(dP, float)
        z = np.zeros(len(goods))
        res0, J, _ = f(z, n_now, ref, dP, ex, z)
        # the clearing prices: linear in dr, least squares where H_YY is singular (as before G2g)
        dr = np.linalg.lstsq(np.asarray(J, float), -np.asarray(res0, float).ravel(), rcond=None)[0]
        lo, hi = st.get("bounds", (-50.0, 50.0))
        r = np.clip(r_seen + dr, lo, hi)
        self.ev.setdefault("yani_market_now", {})[reg] = dict(zip(goods, (float(v) for v in r)))
        return np.asarray(f(z, n_now, ref, dP, ex, r - r_seen)[2], float).ravel()

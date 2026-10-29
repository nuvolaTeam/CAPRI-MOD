"""MarketModule: the bilateral market solve (calibration of the bilateral system, the Newton/Anderson loop, tariff-rate quotas).

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


class BilateralSolveMixin(MarketStateMixin):
    """MarketModule methods for the bilateral market solve (calibration of the bilateral system, the Newton/Anderson loop, tariff-rate quotas)."""

    #: acceleration of the bilateral market's outer steps (_solve_bilateral): "anderson" (Anderson mixing over the last
    #: MARKET_AA_MEMORY steps of the fixed-point map log r -> log new; CAPRI's group and full-system stages serve the
    #: same purpose: the cross-product links a product-by-product step sees only between steps) or None (damped steps
    #: alone). Same equations and stopping rule (every relative residual < tol): the path changes, not the equilibrium.
    market_acceleration = setting("market.acceleration")
    MARKET_AA_MEMORY = setting("market.aa_memory")

    def _bilateral_raw(self):
        """Uncalibrated bilateral systems for the market year (data['market_year'], else 2017)."""
        from capri_mod.market.bilateral import BilateralCommodity
        inp = self._inp()
        year = int(self.data.get("market_year", 2017) or 2017)
        cached = getattr(self, "_bilat_raw_cache", None)
        if cached is not None and cached[0] == year:
            return cached[1]
        sfx = "_eu2" if self.eu_blocks else ""          # CAPRI's two EU trade blocks (build_bilateral_market --eu-blocks)
        if not inp.exists(f"bilateral_flows_{year}{sfx}.csv"):
            year = 2017
        if not inp.exists(f"bilateral_flows_{year}{sfx}.csv"):
            self._bilat_raw_cache = (year, {})
            return {}
        fl = inp.csv(f"bilateral_flows_{year}{sfx}.csv")
        rg = inp.csv(f"bilateral_regions_{year}{sfx}.csv")
        rho = inp.csv("armington_rho.csv").set_index("commodity")
        R = list(self.regions)
        ix = {r: i for i, r in enumerate(R)}
        n = len(R)
        out = {}
        for c, g in fl.groupby("commodity"):
            if c not in self.commodities:
                continue
            X0, a, b, a0, tc = (np.zeros((n, n)) for _ in range(5))
            if "tc" not in g.columns:
                raise ValueError(f"bilateral_flows_{year}{sfx}.csv has no transport cost column tc: rerun "
                                 "tools/build/build_bilateral_market.py")
            for t in g.itertuples(index=False):
                i, j = ix.get(t.importer), ix.get(t.exporter)
                if i is None or j is None:
                    continue
                X0[i, j] += t.q_kt
                if i != j:
                    a[i, j], b[i, j], a0[i, j], tc[i, j] = t.a, t.b, t.a0, t.tc
            pm = rg[rg.commodity == c].set_index("region")["pmrk"]
            Pd0 = np.array([float(pm.get(r, np.nan)) for r in R])
            fill = float(np.nanmedian(Pd0)) if np.isfinite(Pd0).any() else 1.0
            Pd0 = np.where(np.isfinite(Pd0) & (Pd0 > 0), Pd0, fill)
            out[c] = BilateralCommodity(c, R, X0, a, b, a0, Pd0,
                                        float(rho.at[c, "rho1"]) if c in rho.index else 8.0,
                                        float(rho.at[c, "rho2"]) if c in rho.index else 10.0, tc=tc)
        # EU tariff-rate quotas (tools/build/build_bilateral_market.py build_trq)
        if inp.exists(f"bilateral_trq_{year}.csv") and all(r in ix for r in self.EU):
            tq = inp.csv(f"bilateral_trq_{year}.csv")
            rows = [ix[r] for r in self.EU]                # the EU's quotas: imports of every EU market region
            for c, g in tq.groupby("commodity"):
                sc = out.get(c)
                if sc is None:
                    continue
                Q, gap, sh = np.zeros(n), np.zeros(n), np.zeros(n)
                for t in g.itertuples(index=False):
                    j = ix.get(t.exporter)
                    if j is None or float(sc.X0[rows, j].sum()) <= 0:
                        continue
                    Q[j], gap[j] = t.quota_kt, t.gap_eur_t
                    sh[j] = min(1.0, float(t.imports_kt) / float(sc.X0[rows, j].sum()))
                if (Q > 0).any():
                    sc.trq_row = rows[0] if len(rows) == 1 else rows
                    sc.trq_Q, sc.trq_gap, sc.trq_share = Q, gap, sh
                    sc.trq_offset = np.zeros(n)
        self._bilat_raw_cache = (year, out)
        return out

    def _tariff_adds(self, trade_scenario) -> dict:
        """{commodity: [(importer rows, points of ad valorem tariff added)]} of a trade scenario
        {"tariff_change": {region: {commodity: points}}} (PolicyScenario.tariff_changes). A region is a market region
        of the model, or "EU" / "EU27" for the EU's external tariff (its trade blocks' rows together)."""
        tc_ = (trade_scenario or {}).get("tariff_change") or {}
        R = list(self.regions)
        out = {}
        for reg, changes in tc_.items():
            if reg in ("EU", "EU27", "EU27yr19") or reg in self.EU:
                rows = [R.index(x) for x in self.EU if x in R]
            elif reg in R:
                rows = [R.index(reg)]
            else:
                raise ValueError(f"tariff change for {reg!r}: not a market region of the model")
            for comm, pts in (changes or {}).items():
                out.setdefault(comm, []).append((rows, float(pts)))
        return out

    def _eu_rows_ix(self):
        """Row index of the EU market region (one), or the list of the EU trade blocks' rows (None: no EU)."""
        R = list(self.regions)
        rows = [R.index(r) for r in self.EU if r in R]
        if not rows:
            return None
        return rows[0] if len(rows) == 1 else rows

    def _bilateral_ratio_frame(self, value=1.0) -> pd.DataFrame:
        return pd.DataFrame(value, index=list(self.regions), columns=list(self.commodities), dtype=float)

    def _dom0(self) -> pd.DataFrame:
        d0 = getattr(self, "_dom0_cache", None)
        if d0 is None:
            d0 = self.domestic_prices(self.world_prices_base)
            self._dom0_cache = d0
        return d0

    def _bilateral_calibrate(self, exogenous_supply) -> None:
        """Base of the bilateral market at the model's own supply (CAPRI's flows kept, domestic sales absorb
        the difference), demand calibration 1 for bilateral commodities, the world clearing calibration for
        the pooled ones (raw milk, other oilseeds)."""
        import copy as _copy
        raw = self._bilateral_raw()
        R = list(self.regions)
        # non-EU base production of the bilateral commodities: CAPRI's (domestic sales + exports)
        for c, sysc in raw.items():
            prod = sysc.X0.sum(axis=0)
            for i, r in enumerate(R):
                if r not in self.EU:
                    self.par.base_production.at[r, c] = float(prod[i])
        # non-EU crushing at CAPRI's cake production of the market year
        over = {}
        for (r, sd), prm in (self._crush_params() or {}).items():
            if r in self.EU:
                continue
            o, ck = self.CRUSH_CHAINS[sd]
            # the cake, or the oil where CAPRI records no cake from the crush (BGD soybeans, THA sunflower)
            for prod_, y_ in ((ck, prm["yc"]), (o, prm["yo"])):
                if prod_ in raw and y_ > 0:
                    q = float(self.par.base_production.at[r, prod_]) / y_
                    if q > 0:
                        over[(r, sd)] = q
                    break
        self.par.crush_q0_override = over
        self._crush_cache = None
        self.par.demand_cal = pd.Series(1.0, index=self.commodities)
        exo_eu, exo_sup = self._split_supply(exogenous_supply)
        base_supply = self._align_eu_base_balance(exo_eu.sum(axis=0), exo_eu) \
            if exogenous_supply is not None else None
        self._align_sup_base(exo_sup)
        if base_supply is not None:
            self._align_eu_crush_products(base_supply)
        one = self._bilateral_ratio_frame()
        dom0 = self._dom0()
        sysd = {}
        for _pass in range(2):
            S = self.supply_response(self.world_prices_base, exogenous_supply, region_ratio=one, crush_dom=dom0)
            sysd = {}
            for c, sysc in raw.items():
                sc = _copy.deepcopy(sysc)
                sc.calibrate(S[c].reindex(R).fillna(0.0).values)
                sysd[c] = sc
                for i, r in enumerate(R):
                    self.par.base_consumption.at[r, c] = float(sc.D0[i])
                if c in self.CRUSH_CHAINS:
                    if self.par.eu_aligned_use is None:
                        self.par.eu_aligned_use = {}
                    for _rg in self.EU:
                        self.par.eu_aligned_use.setdefault(_rg, {})[c] = float(sc.D0[R.index(_rg)])
            self._crush_cache = None
            if base_supply is not None:
                self._align_eu_crush_products(base_supply)
        # the demand functions carry terms that are not 1 at the calibration point (EU feed use follows the
        # current herds, crushing, biofuels): base consumption is rescaled so that use at the reference prices
        # is exactly the closure's D0
        for _k in range(4):
            Dt = self.demand_response(dom0, self.world_prices_base)
            worst = 0.0
            for c, sc in sysd.items():
                for i, r in enumerate(R):
                    d = float(Dt.at[r, c])
                    if d > 1e-9 and sc.D0[i] > 0:
                        f = float(sc.D0[i]) / d
                        worst = max(worst, abs(f - 1.0))
                        self.par.base_consumption.at[r, c] = float(self.par.base_consumption.at[r, c]) * f
            if worst < 1e-12:
                break
        # pooled commodities: non-EU demand calibrated so the world clears at base (EU use set by alignment)
        pooled = [c for c in self.commodities if c not in sysd]
        S = self.supply_response(self.world_prices_base, exogenous_supply, region_ratio=one, crush_dom=dom0)
        D = self.demand_response(dom0, self.world_prices_base)
        # the regions whose use is set by the supply models (the EU; Norway with its supply models, whose raw milk
        # goes to its own dairies) keep it; the others' use is calibrated so that the world clears
        fixed = list(self.EU) + [r for r in self.SUP if r in exo_sup]
        others = [r for r in R if r not in fixed]
        cal = pd.Series(1.0, index=self.commodities)
        # where the bounds [0.2, 5] (not CAPRI's: PROXY_AUDIT S185) bind: {commodity: unbounded factor}; and the
        # bilateral systems' export-share caps (S192). Recorded for the runs' metadata and warned
        self.calibration_bound_hits = {"non_eu_use": {}, "export_share": {
            c: list(sc.export_cap_hits) for c, sc in sysd.items() if getattr(sc, "export_cap_hits", None)}}
        for c in pooled:
            s_all, d_eu, d_oth = float(S[c].sum()), float(D.loc[fixed, c].sum()), float(D.loc[others, c].sum())
            if d_oth > 1.0 and s_all - d_eu > 1.0:
                _raw = (s_all - d_eu) / d_oth
                cal[c] = min(5.0, max(0.2, _raw))
                if cal[c] != _raw:
                    self.calibration_bound_hits["non_eu_use"][c] = _raw
            if cal[c] != 1.0:
                for _rg in fixed:
                    self.par.base_consumption.at[_rg, c] /= float(cal[c])
        self.par.demand_cal = cal
        _h = self.calibration_bound_hits
        if _h["non_eu_use"] or _h["export_share"]:
            import warnings as _w
            _w.warn(f"market calibration bounds reached: non-EU use factor outside [0.2, 5] for "
                    f"{sorted(_h['non_eu_use'])}; export share above 0.98 for {sorted(_h['export_share'])}",
                    RuntimeWarning)
        for sc in sysd.values():
            if sc.trq_row is not None:
                sc.trq_offset = np.zeros(len(R))
        self.par.bilat = sysd
        self.sv.bilat_last_r = None
        self.sv.bilat_local_el = None

    def _bilateral_eval(self, r: pd.DataFrame, exogenous_supply, trade_scenario=None):
        """Full model response at producer price ratios r: supply, demand, consumer price ratios, residuals."""
        sysd = self.par.bilat
        dom0 = self._dom0()
        PAr = r.copy()
        pcache = {}
        tadd = self._tariff_adds(trade_scenario)
        for c, sc in sysd.items():
            rc = r[c].values
            p = sc.import_prices(rc, tadd.get(c))
            _, _, PA, _ = sc.prices(rc, p)
            PAr[c] = PA / sc.PA0
            pcache[c] = p
        dp = dom0.reindex(index=r.index, columns=r.columns) * PAr
        world = self.world_prices_base * self._bilateral_world_index(r)
        self.ev.bilat_ratio_now = r
        # CAPRI's crushing margin (ProcMargO_, arm/market_model.gms): the seed at its Armington price (v_Arm1Price),
        # oil and cake at their producer prices (v_prodPrice); KNOWN_ISSUES K54-4
        cpd = dp
        if self.CRUSH_CHAINS:
            cpd = dp.copy()
            _oc = sorted({x for oc in self.CRUSH_CHAINS.values() for x in oc if x in r.columns})
            d0r = dom0.reindex(index=r.index, columns=_oc)
            cpd[_oc] = d0r * r[_oc]
        self.ev.crush_prices_now = cpd
        try:
            S = self.supply_response(world, exogenous_supply, region_ratio=r, crush_dom=dp)
            D = self.demand_response(dp, world)
        finally:
            self.ev.crush_prices_now = None
        self._apply_feed_byproduct_supply(S)
        F = {}
        for c, sc in sysd.items():
            F[c] = sc.residual(S[c].values, D[c].values, r[c].values, pcache[c])
        for c in r.columns:
            if c not in sysd:
                F[c] = np.array([float(S[c].sum()) - float(D[c].sum())])
        return S, D, PAr, F, pcache

    def _bilateral_world_index(self, r: pd.DataFrame) -> pd.Series:
        """World price index per commodity: exporters' price ratios weighted by their base exports (bilateral
        commodities); the pooled commodities' common ratio."""
        out = pd.Series(1.0, index=self.commodities)
        sysd = self.par.bilat or {}
        for c in self.commodities:
            if c in sysd:
                sc = sysd[c]
                e = (sc.X0 * sc._off).sum(axis=0)
                if e.sum() > 0:
                    out[c] = float((e * r[c].values).sum() / e.sum())
            else:
                out[c] = float(r[c].iloc[0])
        return out

    def _bilateral_local_el(self, r, exogenous_supply, trade_scenario):
        """Own-price response of supply and of total use per region and commodity (log-log), measured once
        per calibration by a uniform 1% price change of each commodity."""
        S0, D0, PA0, _, _ = self._bilateral_eval(r, exogenous_supply, trade_scenario)
        es = pd.DataFrame(0.0, index=r.index, columns=r.columns)
        ed = pd.DataFrame(0.0, index=r.index, columns=r.columns)
        h = 0.01
        for c in r.columns:
            r1 = r.copy()
            r1[c] = r1[c] * (1 + h)
            S1, D1, PA1, _, _ = self._bilateral_eval(r1, exogenous_supply, trade_scenario)
            with np.errstate(divide="ignore", invalid="ignore"):
                es[c] = np.where(S0[c] > 1e-6, np.log(np.maximum(S1[c], 1e-12) / S0[c]) / np.log(1 + h), 0.0)
                dpa = np.log(PA1[c] / PA0[c])
                ed[c] = np.where((D0[c] > 1e-6) & (np.abs(dpa) > 1e-9),
                                 np.log(np.maximum(D1[c], 1e-12) / D0[c]) / np.where(np.abs(dpa) > 1e-9, dpa, 1.0), 0.0)
        return es.clip(-0.5, 5.0).fillna(0.0), ed.clip(-5.0, 0.5).fillna(0.0)

    #: the trade systems' Newton keeps its Jacobian while the residual keeps falling fast (chord steps)
    TRADE_CHORD = setting("market.trade_chord")

    def _bilateral_inner(self, sc, Sk, Dk, rk, PAk, es, ed, tadd):
        """Exact solve of one commodity's trade system with supply and use log-linear around the current
        point: S_i = Sk_i (r_i / rk_i)^es_i, D_i = Dk_i (PA_i / PAk_i)^ed_i."""
        act = np.where(sc.S0 > 1e-6)[0]
        if len(act) == 0:
            return rk
        scale = np.maximum(sc.S0[act] + sc.D0[act], 1.0)

        def G(z):
            r = rk.copy()
            r[act] = np.exp(z)
            p = sc.import_prices(r, tadd)
            pre = sc.prices(r, p)                       # computed once, reused by the flows
            PA = pre[2]
            S = Sk * (r / rk) ** es
            D = Dk * (PA / PAk) ** ed
            return sc.residual(S, D, r, p, pre=pre)[act] / scale

        z = np.log(rk[act])
        if bool(_settings().get("market.exact_jacobian")):
            # step G1: the same residual and its exact Jacobian from CasADi (capri_mod/market/trade_ad.py)
            from capri_mod.market.trade_ad import trade_function, import_price_matrices
            Am, Bm = import_price_matrices(sc, tadd)
            fn = trade_function(sc, act)
            pars = [Am, Bm, Sk, Dk, rk, PAk, es, ed, scale]

            def GJ(zz):
                g_, J_ = fn(zz, *pars)
                return np.asarray(g_, float).ravel(), np.asarray(J_, float)
            g, J = GJ(z)
            for _ in range(60):
                nrm = float(np.max(np.abs(g)))
                if nrm < 1e-12:
                    break
                try:
                    dz = np.linalg.solve(J, -g)
                except np.linalg.LinAlgError:
                    dz = np.linalg.lstsq(J, -g, rcond=None)[0]
                dz = np.clip(dz, -0.5, 0.5)
                t, ok = 1.0, False
                while t > 1e-3:
                    g1, J1 = GJ(z + t * dz)
                    if float(np.max(np.abs(g1))) < nrm:
                        ok = True
                        break
                    t *= 0.5
                z = z + t * dz
                g, J = (g1, J1) if ok else GJ(z)
            out = rk.copy()
            out[act] = np.exp(z)
            return out
        g = G(z)
        J = None
        prev = None
        for _ in range(60):
            nrm = float(np.max(np.abs(g)))
            if nrm < 1e-12:
                break
            # Newton with a finite-difference Jacobian, kept while it keeps the residual falling fast (chord steps:
            # a fresh Jacobian costs one evaluation per region; same root and tolerance)
            if J is None or prev is None or nrm > 0.25 * prev or not self.TRADE_CHORD:
                m = len(z)
                J = np.empty((m, m))
                h = 1e-6
                for k in range(m):
                    zk = z.copy(); zk[k] += h
                    J[:, k] = (G(zk) - g) / h
            try:
                dz = np.linalg.solve(J, -g)
            except np.linalg.LinAlgError:
                dz = np.linalg.lstsq(J, -g, rcond=None)[0]
            dz = np.clip(dz, -0.5, 0.5)
            t = 1.0
            while t > 1e-3:
                g1 = G(z + t * dz)
                if float(np.max(np.abs(g1))) < nrm:
                    break
                t *= 0.5
            prev = nrm
            z = z + t * dz
            g = G(z)
        out = rk.copy()
        out[act] = np.exp(z)
        return out

    #: scenario change of the EU's tariff-rate quota volumes, {commodity: change in 1000 t} (PolicyScenario.
    #: trq_volume_changes, set by CAPRIModel.run; empty in a baseline run)
    trq_volume_changes: dict = {}

    def _apply_trq_volumes(self, sysd) -> None:
        """Set each EU tariff-rate quota to its base volume plus the scenario's change: a commodity's change (1000 t)
        is spread over its quotas (one per exporter, CAPRI's bilateral TrqNT) in proportion to their base volumes.
        The base fill, at which the base tariff regime is calibrated, stays at the base quotas (trq_Q0)."""
        ch = dict(getattr(self, "trq_volume_changes", None) or {})
        for c, sc in (sysd or {}).items():
            if getattr(sc, "trq_row", None) is None or sc.trq_Q is None:
                continue
            if sc.trq_Q0 is None:
                sc.trq_Q0 = sc.trq_Q.copy()
            tot = float(sc.trq_Q0.sum())
            d = float(ch.get(c, 0.0))
            sc.trq_Q = sc.trq_Q0 * max(0.0, 1.0 + d / tot) if (tot > 0 and d) else sc.trq_Q0.copy()

    def trq_commodities(self) -> list:
        """Commodities with an EU tariff-rate quota in CAPRI's bilateral data for the market year."""
        return sorted(c for c, sc in (self._bilateral_raw() or {}).items() if getattr(sc, "trq_row", None) is not None)

    def _solve_bilateral(self, exogenous_supply, trade_scenario=None, tol=None, max_outer=None, verbose=False):
        """CAPRI's market: successive linearisation - the full model response (supply module output anticipated,
        crushing, dairy blocks, feed and biofuel demand) is re-evaluated each step, and each commodity's trade
        system solved exactly with supply and use log-linear around that point."""
        _st = _settings()                                   # market.* : tolerance, rounds, damping, step clip
        if tol is None:
            tol = float(_st.get("market.tol"))
        if max_outer is None:
            max_outer = int(_st.get("market.max_iter"))
        _sclip = tuple(_st.get("market.step_clip"))
        # BASELINE RUN (no EU base recorded yet): the market is calibrated at THIS supply, prices stay at the
        # reference - CAPRI's reference run is a calibrated equilibrium at its reference prices. Each outer
        # iteration of the baseline recalibrates, so the calibration a scenario inherits is the one at the
        # converged baseline supply. Scenario runs keep it frozen.
        if self.seen.eu_base_supply is None or self.par.demand_cal_frozen is None:
            self._bilateral_calibrate(exogenous_supply)
            self._apply_trq_volumes(self.par.bilat)
            self.par.demand_cal_frozen = self.par.demand_cal.copy()
            r = self._bilateral_ratio_frame()
            S, D, PAr, F, pc = self._bilateral_eval(r, exogenous_supply, trade_scenario)
            def _sz(c):
                if c in self.par.bilat:
                    return np.maximum(self.par.bilat[c].S0 + self.par.bilat[c].D0, 1.0)
                return np.array([max(float(S[c].sum()), 1.0)])
            self._bilat_base_resid = {c: float(np.max(np.abs(F[c] / _sz(c)))) for c in F}
            self._bilat_err = max(self._bilat_base_resid.values())
            self.sv.bilat_last_r = r.copy()
            return r, S, D, PAr, pc, True, 0
        self.par.demand_cal = self.par.demand_cal_frozen.copy()
        sysd = self.par.bilat
        self._apply_trq_volumes(sysd)
        R = list(self.regions)
        tadd = self._tariff_adds(trade_scenario)
        r = self._bilateral_ratio_frame()
        last = self.sv.bilat_last_r
        if last is not None:
            r = last.reindex(index=r.index, columns=r.columns).fillna(1.0)
        if self.sv.bilat_local_el is None:
            self.sv.bilat_local_el = self._bilateral_local_el(self._bilateral_ratio_frame(), exogenous_supply, trade_scenario)
        es, ed = self.sv.bilat_local_el

        def size(c):
            if c in sysd:
                return np.maximum(sysd[c].S0 + sysd[c].D0, 1.0)
            return np.array([max(float(self.par.base_production[c].sum()), 1.0)])

        prev = np.inf
        damp = 1.0
        converged = False
        aa = getattr(self, "market_acceleration", None) == "anderson"
        aa_z, aa_g = [], []                                  # history: log r and log new (the map's value)
        for it in range(max_outer):
            S, D, PAr, F, pc = self._bilateral_eval(r, exogenous_supply, trade_scenario)
            errs = {c: float(np.max(np.abs(F[c] / size(c)))) for c in F}
            err = max(errs.values())
            self._bilat_errs = errs
            if getattr(self, "_debug_trace", None) is not None:
                self._debug_trace.append((it, err, max(errs, key=errs.get), damp))
            if verbose:
                print(f"  bilateral market iter {it}: max rel residual {err:.2e}")
            # EU tariff-rate quotas: the out-of-quota tariff follows the fill of each quota at the current
            # flows (lagged by one step, damped)
            trq_moved = 0.0
            for c, sc in sysd.items():
                if sc.trq_row is None:
                    continue
                X, _ = sc.flows(D[c].values, r[c].values, pc[c])
                old_off = sc.trq_offset.copy()
                sc.trq_solve(X, pc[c])
                trq_moved = max(trq_moved, float(np.max(np.abs(sc.trq_offset - old_off) / np.maximum(float(np.min(sc.Pd0[sc._rows()])), 1.0))))
            if err < tol and trq_moved < tol:
                converged = True
                break
            prev_err = prev                                  # the previous step's residual (Anderson restart test)
            if err > prev * _st.get("market.damping_increase_threshold"):
                damp = max(_st.get("market.damping_min"), damp * _st.get("market.damping_down"))
            elif damp < 1.0 and err < prev * _st.get("market.damping_recover_threshold"):
                # the step came back under control: lengthen it again (a damping halved once stayed halved for the
                # rest of the solve, and the dairy products then crept to the tolerance in 40+ steps)
                damp = min(1.0, damp * _st.get("market.damping_up"))
            prev = err
            new = r.copy()
            for c in r.columns:
                if c in sysd:
                    rk = r[c].values
                    new[c] = self._bilateral_inner(sysd[c], S[c].values, D[c].values, rk, PAr[c].values * sysd[c].PA0,
                                                   es[c].values, ed[c].values, tadd.get(c))
                else:
                    # pooled market: one price ratio for all regions
                    s_, d_ = float(S[c].sum()), float(D[c].sum())
                    e_s = float((S[c] * es[c]).sum() / max(s_, 1e-9))
                    e_d = float((D[c] * ed[c]).sum() / max(d_, 1e-9))
                    if s_ > 0 and d_ > 0 and (e_s - e_d) > 1e-6:
                        new[c] = r[c] * (d_ / s_) ** (1.0 / (e_s - e_d))
            if aa:
                z = np.log(r.to_numpy(dtype=float)).ravel()
                g = np.log(np.maximum(new.to_numpy(dtype=float), 1e-300)).ravel()
                if err > prev_err * 0.999 or not np.all(np.isfinite(g)):
                    aa_z, aa_g = [], []                      # the residual did not fall: restart from a damped step
                aa_z.append(z); aa_g.append(g)
                aa_z, aa_g = aa_z[-(self.MARKET_AA_MEMORY + 1):], aa_g[-(self.MARKET_AA_MEMORY + 1):]
                f = g - z
                if len(aa_z) > 1:
                    F = np.column_stack([(aa_g[i + 1] - aa_z[i + 1]) - (aa_g[i] - aa_z[i]) for i in range(len(aa_z) - 1)])
                    Gd = np.column_stack([aa_g[i + 1] - aa_g[i] for i in range(len(aa_z) - 1)])
                    gam = np.linalg.lstsq(F, f, rcond=None)[0]
                    zn = g - Gd @ gam
                else:
                    zn = z + damp * f
                step = np.clip(zn - z, np.log(_sclip[0]), np.log(_sclip[1]))
                r = pd.DataFrame(np.exp(z + step).reshape(r.shape), index=r.index, columns=r.columns)
            else:
                r = r * (new / r).clip(lower=_sclip[0], upper=_sclip[1]) ** damp
        self.sv.bilat_last_r = r.copy()
        self._bilat_err = err
        return r, S, D, PAr, pc, converged, it + 1

    def _solve_bilateral_equilibrium(self, exogenous_supply, trade_scenario, verbose=False, max_outer=60) -> MarketEquilibrium:
        r, S, D, PAr, pc, converged, iters = self._solve_bilateral(exogenous_supply, trade_scenario, verbose=verbose,
                                                                    max_outer=max_outer)
        if not converged:
            # never silent: the market's balances are not met (largest relative residual and its product)
            import warnings as _w
            errs = getattr(self, "_bilat_errs", {}) or {}
            worst = max(errs, key=errs.get) if errs else "-"
            _w.warn(f"bilateral market did not converge in {iters} steps: largest relative residual "
                    f"{float(getattr(self, '_bilat_err', float('nan'))):.2e} ({worst})", RuntimeWarning)
        sysd = self.par.bilat
        # CAPRI's welfare report (market/welfare.py) at the solution, at the prices the market's functions saw
        welfare = self._capri_welfare(r, PAr, S, D, pc)
        # RAW MILK with the dairy block: the EU milk price is the block's (fat and protein values of the products
        # less margins); raw milk is not traded, so it replaces the pooled market's ratio for the EU
        # world index from the market's own ratios, BEFORE the EU's raw milk takes the dairy block's price: for a
        # pooled product the index is the first region's ratio, and EU27 is the first region, so the reported world
        # raw milk price was the EU dairy block's (K17; the EU price signal itself was right: premium x world)
        widx = self._bilateral_world_index(r)
        _dl = self.ev.dairy_last
        if self._dairy_params() and _dl is not None and "MILK" in r.columns and all(x in r.index for x in self.EU):
            r = r.copy()
            for _rg in self.EU:
                r.at[_rg, "MILK"] = float((_dl.get("milk_price_ratio_reg") or {}).get(_rg, _dl["price_ratio"]["MILK"]))
        # Norway's raw milk: its dairy block's price (raw milk is not traded; CAPRI ProcMargM_ per RMS)
        _wl = self.ev.dairy_world_last or {}
        for _rg in self.SUP:
            if _rg in (self.ev.sup_milk_now or {}) and _rg in _wl and "MILK" in r.columns:
                r = r.copy()
                r.at[_rg, "MILK"] = float(_wl[_rg]["price_ratio"]["MILK"])
        # the other regions with a dairy block: raw milk is cleared inside the block (ProdNQ_ MILK against
        # DairyNQ_, audit M11), so its price is the block's
        for _rg in (self.ev.world_milk_now or {}):
            if _rg in _wl and _rg in r.index and "MILK" in r.columns:
                r = r.copy()
                r.at[_rg, "MILK"] = float(_wl[_rg]["price_ratio"]["MILK"])
        #: producer price ratios (to base) of the non-EU market regions with supply models: the prices their
        #: supply models see (CAPRIModel; K56)
        self.sup_price_ratio = r.loc[[x for x in self.SUP if x in r.index]].copy()
        world = self.world_prices_base * widx
        dom0 = self._dom0()
        reported = dom0.reindex(index=r.index, columns=r.columns) * r
        wedge = dom0.reindex(index=r.index, columns=r.columns) * widx
        # the EU price farmers see: premium over the world index (model.py: signal = world ratio x premium); with two
        # EU market regions, per region (eu_premium_reg) and the production-weighted EU average (eu_premium)
        self.eu_premium_reg = pd.DataFrame({_rg: (r.loc[_rg] / widx).reindex(self.commodities).fillna(1.0)
                                            for _rg in self.EU}).T
        if self.eu_blocks:
            _w = S.loc[list(self.EU)].reindex(columns=self.commodities).fillna(0.0)
            _ws = _w.sum(axis=0)
            _avg = (self.eu_premium_reg * _w).sum(axis=0) / _ws.where(_ws > 0, 1.0)
            self.eu_premium = _avg.where(_ws > 0, self.eu_premium_reg.mean(axis=0))
        else:
            self.eu_premium = self.eu_premium_reg.loc["EU27"]
        self.ev.bilat_ratio_now = r
        idx = pd.MultiIndex.from_product([self.regions, self.regions], names=["exporter", "importer"])
        flows = pd.DataFrame(0.0, index=idx, columns=self.commodities)
        for c, sc in sysd.items():
            X, _ = sc.flows(D[c].values, r[c].values, pc[c])
            for i, imp in enumerate(self.regions):
                for j, exp in enumerate(self.regions):
                    if i != j and X[i, j] > 0:
                        flows.at[(exp, imp), c] = X[i, j]
        biof = None
        if self._biofuel_params() and all(x in reported.index for x in self.EU):
            _pr = {_rg: {c: float(PAr.at[_rg, c]) for c in self._biofuel_params()["share"] if c in PAr.columns}
                   for _rg in self.EU}
            biof = self.biofuel_feedstock_use(_pr if self.eu_blocks else _pr["EU27"])
            # biofuel markets: output, use and prices of every region (BIOF_M); first-generation output and the
            # processing margin (producer price over feedstock cost) of every EU member state
            st = self.ev.biof_state if self.biofuel_endogenous() else None
            biof["endogenous"] = st is not None
            if "DDGS" in S.columns:
                biof["ddgs"] = {"production": {r_: float(S.at[r_, "DDGS"]) for r_ in S.index},
                                "use": {r_: float(D.at[r_, "DDGS"]) for r_ in D.index},
                                "price_ratio": {r_: float(x_) for r_, x_ in r["DDGS"].items()}}
            bm = self._biofuel_market_params()
            if bm:
                biof["markets"] = {fuel: {"production": {r: float(S.at[r, fuel]) for r in S.index},
                                          "use": {r: float(D.at[r, fuel]) for r in D.index},
                                          "price_ratio": {r: float(r_) for r, r_ in r[fuel].items()}}
                                   for fuel in self.BIOFUELS if fuel in S.columns}
                if st is not None:
                    biof["member_states"] = {
                        f"{ms}|{fuel}": {"first_generation": float(st["X"].get((ms, fuel), d["x0_kt"])),
                                         "first_generation0": float(d["x0_kt"]),
                                         "margin": (float(d["ppri"]) * float(r.at[d["region"], fuel]) / st["mub"][(ms, fuel)]
                                                    if (ms, fuel) in st["mub"] else None),
                                         "margin0": float(d["pr0"]) or None}
                        for (ms, fuel), d in bm["rows"].items() if d["region"] in self.EU}
        if self.eu_blocks:
            S, D, reported, wedge, flows, world = self._with_eu_aggregate(S, D, reported, wedge, flows, world, dom0)
            if biof is not None:
                for k in ("markets",):
                    for fuel, v in (biof.get(k) or {}).items():
                        for it in ("production", "use"):
                            v[it]["EU27"] = sum(v[it].get(x, 0.0) for x in self.EU)
                        v["price_ratio"]["EU27"] = float(reported.at["EU27", fuel] / dom0.loc[list(self.EU), fuel].mean()) \
                            if fuel in reported.columns else 1.0
        return MarketEquilibrium(
            dairy=self.ev.dairy_last if self._dairy_params() else None,
            biofuel=biof, world_prices=world, domestic_prices=reported, wedge_prices=wedge,
            production=S, consumption=D, trade_flows=flows, net_exports=S.subtract(D, fill_value=0),
            welfare=welfare, excess_demand=(D.drop(index="EU27", errors="ignore").sum()
                                            - S.drop(index="EU27", errors="ignore").sum()) if self.eu_blocks
            else D.sum() - S.sum(), converged=converged, iterations=iters)

    def _with_eu_aggregate(self, S, D, reported, wedge, flows, world, dom0):
        """Two EU market regions: an EU27 reporting row (CAPRI's EU27yr19 aggregate) appended to production, use,
        prices and flows - quantities summed, prices the production-weighted average of the blocks' (use-weighted
        where the EU produces none). The market's own regions are unchanged; the row is for reporting and for the
        callers that read the EU as a whole."""
        eu = list(self.EU)
        S = S.copy(); D = D.copy(); reported = reported.copy(); wedge = wedge.copy()
        S.loc["EU27"] = S.loc[eu].sum(axis=0)
        D.loc["EU27"] = D.loc[eu].sum(axis=0)
        w = S.loc[eu].where(S.loc[eu].sum(axis=0) > 0, D.loc[eu], axis=1).reindex(columns=reported.columns).fillna(0.0)
        ws = w.sum(axis=0)
        for fr in (reported, wedge):
            avg = (fr.loc[eu] * w).sum(axis=0) / ws.where(ws > 0, 1.0)
            fr.loc["EU27"] = avg.where(ws > 0, fr.loc[eu].mean(axis=0))
        # flows: extra-EU flows of the aggregate (intra-EU flows between the blocks are not EU trade)
        fl = flows.copy()
        add = {}
        for (exp, imp), row in flows.iterrows():
            e_eu, i_eu = exp in eu, imp in eu
            if e_eu and i_eu:
                continue
            if e_eu or i_eu:
                key = ("EU27" if e_eu else exp, "EU27" if i_eu else imp)
                add[key] = add.get(key, 0.0) + row
        if add:
            extra = pd.DataFrame(add).T
            extra.index = pd.MultiIndex.from_tuples(extra.index, names=fl.index.names)
            fl = pd.concat([fl, extra])
        return S, D, reported, wedge, fl, world

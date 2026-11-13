"""CAPRI's bilateral market for one commodity (arm/market_model.gms, simulation model m_globmarket).

Per market region i (the model's trade regions) and product:

  SupBalM_          S_i = DS_i + sum_k X_ki                      own good: domestic sales + exports
  impPrice_         p_ij = a_ij r_j + b_ij                        import price from exporter j: CAPRI's
                                                                  (Fob + TCost)(1 + ad valorem) + specific,
                                                                  aggregated at the base composition, with the
                                                                  exporter's market price moving by r_j
  arm2 (CES rho2)   PM_i = [sum_j beta_ij p_ij^(1-s2)]^(1/(1-s2)),  X_ij = M_i beta_ij (PM_i / p_ij)^s2
  arm1 (CES rho1)   PA_i = [dd_i Pd_i^(1-s1) + dm_i PM_i^(1-s1)]^(1/(1-s1)),
                    DS_i = D_i dd_i (PA_i / Pd_i)^s1,  M_i = D_i dm_i (PA_i / PM_i)^s1
  ArmBal1_          D_i = total use at the consumer (Armington) price PA_i

with Pd_i = Pd0_i r_i the region's market price. Share parameters are calibrated so that base flows and base
prices are reproduced exactly (the price indices equal the value-weighted base prices). CAPRI's second nest
carries "commitment" terms (p_arm2Commit, augmented CES); the plain CES is used here (REGISTERED).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from capri_mod.params import param, param_table


@dataclass
class BilateralCommodity:
    name: str
    regions: List[str]
    X0: np.ndarray          # n x n, importer x exporter, diagonal = domestic sales (1000 t)
    a: np.ndarray           # n x n exporter-price part of the import price (EUR/t at r = 1)
    b: np.ndarray           # n x n fixed part (transport, specific tariffs, TRQ effects)
    a0: np.ndarray          # n x n exporter price without ad valorem tariff
    Pd0: np.ndarray         # n market prices (EUR/t)
    s1: float
    s2: float
    # calibrated
    beta: Optional[np.ndarray] = None
    dd: Optional[np.ndarray] = None
    dm: Optional[np.ndarray] = None
    PM0: Optional[np.ndarray] = None
    PA0: Optional[np.ndarray] = None
    S0: Optional[np.ndarray] = None
    D0: Optional[np.ndarray] = None
    #: n x n transport cost of each flow (EUR/t, CAPRI TCost): with a0 r the base of an ad valorem tariff change
    tc: Optional[np.ndarray] = None

    def calibrate(self, S0: np.ndarray) -> None:
        """Closure at the model's own base supply S0: CAPRI's trade flows are kept, domestic sales absorb the
        difference between the model's production and CAPRI's (DS0 = S0 - exports). Where a region's CAPRI exports
        exceed its base supply S0 they are scaled down to S0 (no domestic sales): with CAPRI's market data of the
        market year (crushing, biofuels: K106) this happens only for the rows set by the supply models (step F,
        DEPARTURES_FROM_CAPRI.md), not in CAPRI's own non-EU data, where exports never exceed production. Until
        30 October 2026 exports were capped at 0.98 of S0 everywhere (PROXY_AUDIT S192), which also forced 2% domestic
        sales on the regions that export nearly all of their production in CAPRI's data (Indonesia's coffee 99.99%)."""
        n = len(self.regions)
        X = self.X0.copy()
        off = ~np.eye(n, dtype=bool)
        # regions whose CAPRI exports exceed the model's base supply by more than rounding: (region, exports /
        # supply), recorded for the runs' metadata and warned
        self.export_cap_hits = []
        for j in range(n):
            e = float(X[off[:, j], j].sum())
            s0 = max(float(S0[j]), 0.0)
            if e > s0:
                if e > s0 * (1.0 + 1e-6):
                    self.export_cap_hits.append((self.regions[j], e / s0 if s0 > 0 else float("inf")))
                X[off[:, j], j] *= (s0 / e) if e > 0 else 0.0
        E = np.array([X[off[:, j], j].sum() for j in range(n)])
        DS = np.maximum(S0 - E, 0.0)
        X[np.arange(n), np.arange(n)] = DS
        self.X0 = X
        M = (X * off).sum(axis=1)
        self.S0 = DS + E
        self.D0 = DS + M
        p0 = self.a + self.b
        P = np.where(off, p0, self.Pd0[None, :] * np.eye(n))
        with np.errstate(divide="ignore", invalid="ignore"):
            PM0 = np.where(M > 0, (X * off * P).sum(axis=1) / np.where(M > 0, M, 1.0), 1.0)
            PA0 = np.where(self.D0 > 0, (DS * self.Pd0 + M * PM0) / np.where(self.D0 > 0, self.D0, 1.0), self.Pd0)
            self.beta = np.where(off & (X > 0), (X / np.where(M > 0, M, 1.0)[:, None])
                                 * (P / PM0[:, None]) ** self.s2, 0.0)
            self.dd = np.where(self.D0 > 0, DS / np.where(self.D0 > 0, self.D0, 1.0) * (self.Pd0 / PA0) ** self.s1, 0.0)
            self.dm = np.where(self.D0 > 0, M / np.where(self.D0 > 0, self.D0, 1.0) * (PM0 / PA0) ** self.s1, 0.0)
        self.PM0, self.PA0 = PM0, PA0
        self._off = off
        self._has_imp = M > 0
        self._has_dom = DS > 0

    # CAPRI's bilateral tariff-rate quotas (arm/market_model.gms trqSigmoidFunc_, tarSpec_, tarAdval_; stage 4 of the
    # market move, docs/design/PORTS_STAGE4.md): one per pair of policy blocks (importer RMTP, exporter RMTP), filled
    # by the flows between their market regions (TradeFlowsAgg_). Each is a dict: rows, cols (the importer's and the
    # exporter's market regions), Q (TrqNT, 1000 t), Q0 (its base volume), dta (TaMFN - TaPref, points), dts
    # (TsMFN - TsPref, EUR/t), importer, exporter. Its sigmoid moves the flows' tariffs from the preferential to the MFN
    # rates: tarAdVal = TaPref + dta sigma, tarSpec = TsPref + dts sigma, the ad valorem on the exporter's current
    # market price plus the transport cost (impPrice_). The base import prices are CAPRI's (a, b at the base fill's
    # sigma0); trq_offset (n x n, EUR/t) carries the change: (a0 r + tc) dta/100 (sigma - sigma0) + dts (sigma - sigma0).
    # Until 4 November 2026 the EU's quotas only, one per model exporter, with a price gap frozen at the base (DEP-34,
    # DEP-35, DEP-36).
    trq_quotas: Optional[list] = None
    trq_sigma: Optional[np.ndarray] = None
    trq_sigma0: Optional[np.ndarray] = None
    trq_offset: Optional[np.ndarray] = None
    #: CAPRI p_trqSigmoidSlope = 200 on (imports - 0.97 quota) / quota: the tariff moves from in- to
    #: out-of-quota within about +-3% of the quota (arm/market_model.gms trqSigmoidFunc_)
    TRQ_SLOPE = param("TRQ_SLOPE")
    #: the quota fill at the sigmoid's midpoint (CAPRI trqSigmoidFunc_, arm/market_model.gms l. 3272-3284)
    TRQ_FILL_MID = 0.97
    #: overflow clip of the sigmoid's argument (numerical)
    TRQ_ARG_CLIP = 60.0
    #: trq_solve's trials on the quota's own cells (_TrqCells; the same values as the full matrices, faster); False
    #: computes every trial on the full matrices (the reference the test compares with)
    TRQ_CELLS = True

    #: CAPRI's global (erga omnes) quotas of the importers (TRQImports_, tarAdValW_, tarSpecW_; stage 5 with stage 4):
    #: dicts rows (the importer's market regions), Q, Q0, ta_pref, dta, ts_pref, dts, cover (n x n bool: the flows that
    #: pay the global rates, from exporters without a bilateral quota and without free trade), bil (indices of the
    #: bilateral quotas of the same importer, whose overfill enters the global imports and whose rate is the smaller of
    #: the two), has_ta, has_ts (the global quota switches that rate: one of its two values above eps)
    trq_globals: Optional[list] = None
    trq_sigmaW: Optional[np.ndarray] = None
    trq_sigmaW0: Optional[np.ndarray] = None

    @property
    def trq_row(self):
        """The importer rows under a quota (None without quotas): kept for the callers that only ask whether a
        commodity has quotas."""
        if not (self.trq_quotas or self.trq_globals):
            return None
        return sorted({int(i) for q in (self.trq_quotas or []) + (self.trq_globals or []) for i in q["rows"]})

    def _sig(self, f):
        return 1.0 / (1.0 + np.exp(-np.clip(self.TRQ_SLOPE * (f - self.TRQ_FILL_MID), -self.TRQ_ARG_CLIP,
                                            self.TRQ_ARG_CLIP)))

    @staticmethod
    def ncpcm(x, y, z):
        """GAMS's ncpCM(x, y, Z) = x - Z ln(1 + exp((x - y) / Z)), Chen and Mangasarian's smoothed min(x, y)."""
        return x - z * np.logaddexp(0.0, (x - y) / z)

    def trq_fill(self, X: np.ndarray, q: dict) -> float:
        """A bilateral quota's imports (TradeFlowsAgg_): the flows from its exporter's to its importer's regions."""
        return float(X[np.ix_(q["rows"], q["cols"])].sum())

    def trq_global_imports(self, X: np.ndarray, g: dict) -> float:
        """A global quota's imports (TRQImports_): the flows of the exporters without a bilateral quota and the
        overfill of the bilateral ones, -ncpcm(-(fill - TrqNT), 0, 1E-3 TrqNT)."""
        tot = float(X[g["cover"]].sum())
        for k in g["bil"]:
            q = self.trq_quotas[k]
            tot += float(-self.ncpcm(-(self.trq_fill(X, q) - q["Q"]), 0.0, 1e-3 * q["Q"]))
        return tot

    def _trq_rates(self, sB: np.ndarray, sW: np.ndarray):
        """The ad valorem (points) and specific (EUR/t) rates of every flow under a quota regime at the sigmas, as
        (ta, ts, mask) n x n; flows without a moving rate are nan (their base tariff holds)."""
        n = len(self.regions)
        ta, ts = np.full((n, n), np.nan), np.full((n, n), np.nan)
        for m, g in enumerate(self.trq_globals or ()):
            ix = g["cover"]
            if g["has_ta"]:
                ta[ix] = g["ta_pref"] + g["dta"] * sW[m]
            if g["has_ts"]:
                ts[ix] = g["ts_pref"] + g["dts"] * sW[m]
        for k, q in enumerate(self.trq_quotas or ()):
            if q["regime"] == "entry_price":
                continue
            ixq = np.ix_(q["rows"], q["cols"])
            tb = q["ta_pref"] + q["dta"] * sB[k]
            sb = q["ts_pref"] + q["dts"] * sB[k]
            g = self.trq_globals[q["glob"]] if q.get("glob") is not None else None
            if g is not None and g["has_ta"]:
                tw = g["ta_pref"] + g["dta"] * sW[q["glob"]]
                tb = self.ncpcm(tw, tb, max(1e-2, 1e-3 * abs(q["dta"])))
            if g is not None and g["has_ts"]:
                tw = g["ts_pref"] + g["dts"] * sW[q["glob"]]
                sb = self.ncpcm(tw, sb, max(1e-5, 1e-7 * abs(q["dts"])))
            if q["dta"] != 0 or (g is not None and g["has_ta"]):
                ta[ixq] = tb
            if q["dts"] != 0 or (g is not None and g["has_ts"]):
                ts[ixq] = sb
        return ta, ts

    def trq_base(self) -> None:
        """Every quota's sigma at the base flows (the calibration point, at the base volumes), the rates there and no
        offset."""
        n = len(self.regions)
        self._trq_hist = None
        self._trq_bracket = None
        self.trq_gap = 0.0
        self.trq_offset = np.zeros((n, n))
        if not (self.trq_quotas or self.trq_globals):
            self.trq_sigma = self.trq_sigma0 = self.trq_sigmaW = self.trq_sigmaW0 = None
            return
        sB = np.array([float(self._sig(self.trq_fill(self.X0, q) / q["Q0"])) if q["Q0"] > 0 else 0.0
                       for q in (self.trq_quotas or ())])
        Q = [q["Q"] for q in (self.trq_quotas or ())]
        for q in (self.trq_quotas or ()):
            q["Q"] = q["Q0"]
        sW = np.array([float(self._sig(self.trq_global_imports(self.X0, g) / g["Q0"])) if g["Q0"] > 0 else 0.0
                       for g in (self.trq_globals or ())])
        for q, v in zip(self.trq_quotas or (), Q):
            q["Q"] = v
        self.trq_sigma0, self.trq_sigma = sB, sB.copy()
        self.trq_sigmaW0, self.trq_sigmaW = sW, sW.copy()
        self._trq_ta0, self._trq_ts0 = self._trq_rates(sB, sW)

    def _trq_off(self, r: np.ndarray, sB: np.ndarray, sW: np.ndarray) -> np.ndarray:
        """The import prices' change from the base rates: (a0 r + tc) (ta - ta0) / 100 + (ts - ts0)."""
        ta, ts = self._trq_rates(sB, sW)
        tc = self.tc if self.tc is not None else np.zeros_like(self.a0)
        base = self.a0 * r[None, :] + tc
        off = np.where(np.isnan(ta), 0.0, base * (ta - np.nan_to_num(self._trq_ta0)) / 100.0)
        sp = np.where(np.isnan(ts), 0.0, ts - np.nan_to_num(self._trq_ts0))
        if self.border:
            sp = np.where(self.border["kind"] == 2, 0.0, sp)   # a levy replaces the specific tariff (border_spec)
        return off + sp

    def trq_sigmas(self) -> np.ndarray:
        """All the quotas' sigmas, bilateral then global (for the solve's convergence test)."""
        parts = [x for x in (self.trq_sigma, self.trq_sigmaW) if x is not None and len(x)]
        return np.concatenate(parts) if parts else np.zeros(0)

    def trq_sigma_change(self, old: np.ndarray) -> float:
        """The largest move of a quota's sigma since `old` (dimensionless, as the solve's tolerance): CAPRI's
        simultaneous solve stops on the residuals of trqSigmoidFunc_ and TRQImports_, which are in sigma's terms."""
        now = self.trq_sigmas()
        mv = float(np.max(np.abs(now - old))) if len(now) and len(old) == len(now) else 0.0
        # with the bracketing of trq_solve the move can be a fraction of the gap: the gap counts
        return max(mv, float(getattr(self, "trq_gap", 0.0) or 0.0))

    def trq_set_offsets(self, r: np.ndarray) -> None:
        """trq_offset from the quotas' current sigmas at the exporters' price ratios r."""
        self.trq_offset = self._trq_off(r, self.trq_sigma, self.trq_sigmaW)

    def trq_active(self) -> tuple:
        """The quotas with a volume, (bilateral indices, global indices): the unknowns of the joint solve."""
        return ([k for k, q in enumerate(self.trq_quotas or ()) if q["Q"] > 0],
                [m for m, g in enumerate(self.trq_globals or ()) if g["Q"] > 0])

    def trq_arguments(self, X: np.ndarray, act: Optional[tuple] = None) -> np.ndarray:
        """The sigmoid's argument of each active quota at the flows X (importer x exporter), CAPRI's trqSigmoidFunc_:
        clip(slope (fill / Q - 0.97)), fill the quota's imports (TradeFlowsAgg_ for a bilateral quota, TRQImports_ for
        a global one), bilateral first."""
        bil, glo = self.trq_active() if act is None else act
        f = [self.trq_fill(X, self.trq_quotas[k]) / self.trq_quotas[k]["Q"] for k in bil]
        f += [self.trq_global_imports(X, self.trq_globals[m]) / self.trq_globals[m]["Q"] for m in glo]
        return np.clip(self.TRQ_SLOPE * (np.asarray(f, float) - self.TRQ_FILL_MID), -self.TRQ_ARG_CLIP,
                       self.TRQ_ARG_CLIP)

    def trq_equation_gap(self, X: np.ndarray) -> float:
        """CAPRI's trqSigmoidFunc_ residual at the flows X and the current sigmas: max |sigma - Sigmoid(argument)| over
        the active quotas (0 without quotas)."""
        if not (self.trq_quotas or self.trq_globals) or self.trq_sigma is None:
            return 0.0
        bil, glo = self.trq_active()
        if not (bil or glo):
            return 0.0
        sW = np.asarray(self.trq_sigmaW if self.trq_sigmaW is not None else np.zeros(0), float)
        s = np.concatenate([np.asarray(self.trq_sigma, float)[bil], sW[glo]])
        return float(np.max(np.abs(s - 1.0 / (1.0 + np.exp(-self.trq_arguments(X, (bil, glo)))))))

    def trq_solve(self, X: np.ndarray, p: np.ndarray, r: Optional[np.ndarray] = None,
                  D: Optional[np.ndarray] = None) -> None:
        """Every quota's sigma consistent with its flows (Gauss-Seidel over the quotas, the bilateral ones first, then
        the global ones): sigma = Sigmoid(slope / Q (imports(sigma) - 0.97 Q)), the imports at the importers' Armington
        response to the moved import prices at the total use D (both nests: the other imports and the domestic sales
        shift too); without D the flows' own response, X (p / (p + off(sigma) - off_now))^s2. Bisection on sigma in
        [0, 1], so the steep CAPRI sigmoid is solved without oscillating. Then the offsets at the price ratios r."""
        if not (self.trq_quotas or self.trq_globals):
            return
        r = np.ones(len(self.regions)) if r is None else np.asarray(r, dtype=float)
        if self.trq_sigma is None:
            self.trq_base()
        sB, sW = self.trq_sigma.copy(), self.trq_sigmaW.copy()
        old = np.concatenate([sB, sW]) if len(sW) else sB.copy()
        off_now = self.trq_offset if self.trq_offset is not None else np.zeros_like(p)

        def Xat(off):
            if D is not None:
                return self.flows(D, r, np.maximum(p + off - off_now, 1e-9))[0]
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(X > 0, X * (p / np.maximum(p + off - off_now, 1e-6)) ** self.s2, X)

        def bisect(fn):
            lo, hi = 0.0, 1.0
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                if fn(mid) > 0:
                    hi = mid
                else:
                    lo = mid
            return 0.5 * (lo + hi)

        # Without D (every caller in the solves) a trial sigma of one quota moves only the rates of the cells that quota
        # (or, for a global quota, it and its nested bilateral quotas) writes last, and the fill sums only its own cells:
        # the trial computes those cells alone (_TrqCells), the same element operations in the same order as the full
        # matrices, so the same values bit for bit; with D the flows of all regions respond, and the full form is kept
        fast = D is None and self.TRQ_CELLS
        for k, q in enumerate(self.trq_quotas or ()):
            if q["Q"] <= 0:
                continue
            if fast:
                cells = _TrqCells(self, r, p, X, off_now, sB, sW)
                hB = cells.bilateral_trial(k)
            else:
                def hB(s, k=k, q=q):
                    b = sB.copy(); b[k] = s
                    return s - float(self._sig(self.trq_fill(Xat(self._trq_off(r, b, sW)), q) / q["Q"]))
            sB[k] = bisect(hB)
        for m, g in enumerate(self.trq_globals or ()):
            if g["Q"] <= 0:
                continue
            if fast:
                cells = _TrqCells(self, r, p, X, off_now, sB, sW)
                hW = cells.global_trial(m)
            else:
                def hW(s, m=m, g=g):
                    w = sW.copy(); w[m] = s
                    return s - float(self._sig(self.trq_global_imports(Xat(self._trq_off(r, sB, w)), g) / g["Q"]))
            sW[m] = bisect(hW)
        # Aitken's extrapolation where a quota's sigma converges linearly (the outer fixed point with the market,
        # slow at the sigmoid's steep part: a contraction of about 0.96 per step near 97% fill): three moves in one
        # direction shrinking by a steady factor rho in [0.5, 0.99] are extrapolated by rho / (1 - rho) times the
        # last move, at most 0.05 of sigma and within [0, 1]
        new = np.concatenate([sB, sW]) if len(sW) else sB.copy()
        # A bracketing root search per quota across the market's steps, where a quota's fixed point is crossed: two
        # quotas of one importer can flip in turn, each solved full at the other's fill with the prices of the step
        # (the EU's sugar quotas from AFR_REST, India and South Africa in the full Farm-to-Fork: sigma 0 -> 1 -> 0 at
        # every step, the out-of-quota tariff 661 EUR/t switched on and off, 100 steps without convergence, 5 November
        # 2026). g = Sigmoid(fill) - sigma, the fill at the step's prices with the quota's sigma as it was, falls as
        # sigma rises (a higher out-of-quota rate, less imports); the full step sigma + g is taken until g changes sign,
        # then the regula falsi point of the bracket (Illinois: the end kept twice has its g halved). CAPRI solves the
        # quotas and the prices in one system (trqSigmoidFunc_, TRQImports_ in m_globMarket), so it has no such loop;
        # this changes the path to the fixed point, not the equations. trq_gap, max |g|, is CAPRI's trqSigmoidFunc_
        # residual and the solve's convergence measure (trq_sigma_change)
        g = new - old
        nq = len(g)
        br = getattr(self, "_trq_bracket", None)
        if br is None or len(br["lo_s"]) != nq or "run" not in br:
            br = {k: np.full(nq, np.nan) for k in ("lo_s", "lo_g", "hi_s", "hi_g")}
            br["side"] = np.zeros(nq)
            br["run"] = np.zeros(nq)
        for k in range(nq):
            if abs(g[k]) <= 1e-12:
                continue
            s_ = 1 if g[k] > 0 else -1
            br["run"][k] = br["run"][k] + 1 if br["side"][k] == s_ else 1
            # the prices move on with the market's steps, so g is not one function of sigma: an end the search has not
            # come back to in 4 steps is dropped (the full step again), else the Illinois halving would hold sigma at it
            if br["run"][k] > 4:
                for e in (("hi_s", "hi_g") if s_ == 1 else ("lo_s", "lo_g")):
                    br[e][k] = np.nan
                br["run"][k] = 1
            if s_ == 1:                                  # sigma below its fixed point
                br["lo_s"][k], br["lo_g"][k] = old[k], g[k]
                if br["side"][k] == 1 and not np.isnan(br["hi_g"][k]):
                    br["hi_g"][k] *= 0.5                 # Illinois: the other end kept twice
            else:
                br["hi_s"][k], br["hi_g"][k] = old[k], g[k]
                if br["side"][k] == -1 and not np.isnan(br["lo_g"][k]):
                    br["lo_g"][k] *= 0.5
            br["side"][k] = s_
            if not (np.isnan(br["lo_s"][k]) or np.isnan(br["hi_s"][k])):
                if br["lo_s"][k] >= br["hi_s"][k]:       # a stale end (the prices moved on): keep the newest only
                    if g[k] > 0:
                        br["hi_s"][k] = br["hi_g"][k] = np.nan
                    else:
                        br["lo_s"][k] = br["lo_g"][k] = np.nan
                else:
                    lo_s, lo_g, hi_s, hi_g = br["lo_s"][k], br["lo_g"][k], br["hi_s"][k], br["hi_g"][k]
                    new[k] = lo_s + lo_g * (hi_s - lo_s) / (lo_g - hi_g)
        self._trq_bracket = br
        self.trq_gap = float(np.max(np.abs(g))) if nq else 0.0
        hist = getattr(self, "_trq_hist", None)
        hist = [] if hist is None or len(hist[-1]) != len(new) else hist
        hist.append(new.copy())
        if len(hist) >= 4:
            d1, d2, d3 = hist[-3] - hist[-4], hist[-2] - hist[-3], hist[-1] - hist[-2]
            with np.errstate(divide="ignore", invalid="ignore"):
                rho = np.where(np.abs(d2) > 0, d3 / d2, 0.0)
                rho0 = np.where(np.abs(d1) > 0, d2 / d1, 0.0)
            ok = ((np.sign(d1) == np.sign(d2)) & (np.sign(d2) == np.sign(d3)) & (rho >= 0.5) & (rho <= 0.99)
                  & (np.abs(rho - rho0) < 0.05) & (np.abs(d3) > 0)
                  & (np.isnan(br["lo_s"]) | np.isnan(br["hi_s"])))   # not where the root is bracketed
            if ok.any():
                with np.errstate(divide="ignore", invalid="ignore"):  # rho = 1 where not ok (masked below)
                    jump = np.clip(d3 * rho / (1.0 - rho), -0.05, 0.05)
                new = np.where(ok, np.clip(new + jump, 0.0, 1.0), new)
                hist = [new.copy()]
        self._trq_hist = hist[-4:]
        nb = len(sB)
        self.trq_sigma, self.trq_sigmaW = new[:nb], new[nb:]
        self.trq_set_offsets(r)

    #: CAPRI's border measures replacing the specific tariff (stage 6, docs/design/PORTS_STAGE4.md): a dict of n x n
    #: arrays over the flows they apply to: kind (1 entry price, 2 flexible levy, 0 none), price (TriggerP or
    #: MinBordP), tars (the bound specific rate DATA TARS, or the quota's TsPref under the entry price), fac
    #: (p_entryPriceFac), pref (PrefTrigPrice: the entry price of an unlimited preference, or the low end of a quota's),
    #: quota (the index of the flow's bilateral quota under the entry price system, -1 none); S0, the specific part at
    #: the base, set by border_base()
    border: Optional[dict] = None

    def border_spec(self, r: np.ndarray, sig: Optional[tuple] = None) -> np.ndarray:
        """The specific tariff of the flows under a border measure (EUR/t; 0 elsewhere) at the exporters' ratios r (and the
        quotas' sigmas sig = (bilateral, global), default the current ones):
        entry price (EntryPriceDriver_, tarSpecIfEntryPrice_, prefTriggerPrice_): driver d = (E 0.95 - (Pmrk + TC)) /
        TriggerP x fac, tariff = exp(min(0, d)) / (1 + 20 exp(-|d|)) x (TARS or TsPref), E = TriggerP, or PrefTrigPrice
        for an unlimited preference, or PrefTrigPrice + (TriggerP - PrefTrigPrice) sigma under the quota; flexible levy
        (FlexLevyNotCut_, FlexLevy_): ncpcm(-ncpcm(-(MinBordP - (Pmrk + TC)), 0, Z), TARS, Z), Z = 1E-3 MinBordP."""
        b = self.border
        out = np.zeros((len(self.regions), len(self.regions)))
        if not b:
            return out
        sB, sW = (self.trq_sigma, self.trq_sigmaW) if sig is None else sig
        tc = self.tc if self.tc is not None else np.zeros_like(self.a0)
        cif = self.a0 * r[None, :] + tc
        # CAPRI defines the measures per pair of policy blocks (v_marketPrice(RMTP1) + v_transpCost(RMTP, RMTP1),
        # TransportCostsAgg_: the CIF price weighted by the pair's base flows), the same for every flow of the pair
        grp = b.get("pairs")
        if grp:
            cif = cif.copy()
            for ii, jj, w in grp:
                cif[np.ix_(ii, jj)] = float((w * cif[np.ix_(ii, jj)]).sum() / w.sum())
        k = b["kind"]
        en = k == 1
        if en.any():
            E = np.where(b["pref"] > 0, b["pref"], b["price"])
            for qi in np.unique(b["quota"][en & (b["quota"] >= 0)]):
                m = en & (b["quota"] == qi)
                s_ = float(sB[int(qi)]) if sB is not None else 0.0
                E = np.where(m, b["pref"] + (b["price"] - b["pref"]) * s_, E)
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                d = (E * 0.95 - cif) / np.where(b["price"] > 0, b["price"], 1.0) * b["fac"]
                g = np.exp(np.minimum(0.0, d)) / (1.0 + 20.0 * np.exp(-np.abs(d)))
            out = np.where(en, g * b["tars"], out)
        lv = k == 2
        if lv.any():
            # the levy is cut at the flow's specific tariff: the bound rate, or the quota's current rate (v_tarSpec)
            tars = b["tars"]
            if sB is not None and (self.trq_quotas or self.trq_globals):
                _, ts = self._trq_rates(sB, sW)
                tars = np.where(np.isnan(ts), tars, ts)
            z = 1e-3 * np.where(b["price"] > 0, b["price"], 1.0)
            notcut = -self.ncpcm(-(b["price"] - cif), 0.0, z)
            out = np.where(lv, self.ncpcm(notcut, tars, z), out)
        return out

    def border_base(self) -> None:
        """The border measures' specific part at the base (r = 1, the quotas at their base sigma)."""
        if self.border:
            self.border["S0"] = self.border_spec(np.ones(len(self.regions)))

    def import_prices(self, r: np.ndarray, tariff_adds=None, sig: Optional[tuple] = None) -> np.ndarray:
        """Import prices p_ij at the exporters' price ratios r. tariff_adds: [(importer rows, points of ad valorem
        tariff added)], CAPRI impPrice_ (arm/market_model.gms l. 2849-2882): the ad valorem tariff applies to the
        exporter's market price plus the transport cost; flows between the rows of one importer (the EU's trade
        blocks) carry none. sig = (bilateral, global sigmas): the quotas' rates at these sigmas and at r (the joint
        solve's trial point, _bilateral_inner_trq); without it the stored offsets and the current sigmas."""
        p = self.a * r[None, :] + self.b
        if sig is not None and (self.trq_quotas or self.trq_globals):
            p = p + self._trq_off(np.asarray(r, dtype=float), sig[0], sig[1])
        elif (self.trq_quotas or self.trq_globals) and self.trq_offset is not None:
            p = p + self.trq_offset
        if self.border and "S0" in self.border:
            p = p + (self.border_spec(np.asarray(r, dtype=float), sig) - self.border["S0"])
        for importer, pts in (tariff_adds or ()):
            if not pts:
                continue
            imp = np.atleast_1d(np.asarray(importer, dtype=int))
            ext = ~np.isin(np.arange(len(r)), imp)
            tc = self.tc if self.tc is not None else np.zeros_like(self.a0)
            for i_ in imp:
                p[i_] = p[i_] + np.where(ext, self.a0[i_] * r + tc[i_], 0.0) * float(pts) / 100.0
        return p

    def prices(self, r: np.ndarray, p: Optional[np.ndarray] = None):
        """(Pd, PM, PA) at producer price ratios r."""
        if p is None:
            p = self.import_prices(r)
        Pd = self.Pd0 * r
        s1, s2 = self.s1, self.s2
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            pm = np.where(self.beta > 0, self.beta * np.maximum(p, 1e-9) ** (1.0 - s2), 0.0).sum(axis=1)
            PM = np.where(self._has_imp, pm ** (1.0 / (1.0 - s2)), self.PM0)
            pa = (np.where(self._has_dom, self.dd * Pd ** (1.0 - s1), 0.0)
                  + np.where(self._has_imp, self.dm * PM ** (1.0 - s1), 0.0))
            PA = np.where(self._has_dom | self._has_imp, pa ** (1.0 / (1.0 - s1)), self.PA0)
        return Pd, PM, PA, p

    def flows(self, D: np.ndarray, r: np.ndarray, p: Optional[np.ndarray] = None, pre=None):
        """Domestic sales and bilateral imports at total use D and producer price ratios r: (X, PA). pre: the
        (Pd, PM, PA, p) of prices(r, p) when the caller has them already (same values, computed once)."""
        Pd, PM, PA, p = pre if pre is not None else self.prices(r, p)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            DS = np.where(self._has_dom, D * self.dd * (PA / Pd) ** self.s1, 0.0)
            M = np.where(self._has_imp, D * self.dm * (PA / PM) ** self.s1, 0.0)
            X = np.where(self.beta > 0, M[:, None] * self.beta * (PM[:, None] / np.maximum(p, 1e-9)) ** self.s2, 0.0)
        X[np.arange(len(D)), np.arange(len(D))] = DS
        return X, PA

    def residual(self, S: np.ndarray, D: np.ndarray, r: np.ndarray, p: Optional[np.ndarray] = None,
                 pre=None) -> np.ndarray:
        """Supply balance of every region's own good: S - DS - exports (1000 t)."""
        X, _ = self.flows(D, r, p, pre=pre)
        return S - X.sum(axis=0)


class _TrqCells:
    """One quota's trial in trq_solve on the cells it needs (without total use D): its own cells for a bilateral quota
    (TradeFlowsAgg_), the cover and the nested bilateral quotas' cells for a global one (TRQImports_). The rates of a
    cell come from the quota that writes it last in _trq_rates (globals first, then the bilateral quotas in order; a
    structure, not a value, so mapped once), and only the cells whose writer moves with the trial sigma are recomputed;
    the others keep the rates at the current sigmas. Every element operation is _trq_off's and Xat's, in the same
    order, on arrays laid out as the full matrices' extracts (X[np.ix_(rows, cols)], X[cover]), so the sums and the
    trial values are the full form's."""

    _G = 1_000_000                                       # a global quota's writer code: _G + its index

    def __init__(self, sc: "BilateralCommodity", r: np.ndarray, p: np.ndarray, X: np.ndarray, off_now: np.ndarray,
                 sB: np.ndarray, sW: np.ndarray):
        self.sc, self.sB, self.sW = sc, sB, sW
        self.p, self.X, self.off_now = p, X, off_now
        self.ta, self.ts = sc._trq_rates(sB, sW)          # every cell's rates at the current sigmas
        tc = sc.tc if sc.tc is not None else np.zeros_like(sc.a0)
        self.base = sc.a0 * r[None, :] + tc
        self.ta0n, self.ts0n = np.nan_to_num(sc._trq_ta0), np.nan_to_num(sc._trq_ts0)
        self.kind2 = (sc.border["kind"] == 2) if sc.border else None
        n = len(sc.regions)
        wa, ws = np.full((n, n), -1, dtype=np.int64), np.full((n, n), -1, dtype=np.int64)
        glob = sc.trq_globals or ()
        for m, g in enumerate(glob):
            if g["has_ta"]:
                wa[g["cover"]] = self._G + m
            if g["has_ts"]:
                ws[g["cover"]] = self._G + m
        for k, q in enumerate(sc.trq_quotas or ()):
            if q["regime"] == "entry_price":
                continue
            ixq = np.ix_(q["rows"], q["cols"])
            g = glob[q["glob"]] if q.get("glob") is not None else None
            if q["dta"] != 0 or (g is not None and g["has_ta"]):
                wa[ixq] = k
            if q["dts"] != 0 or (g is not None and g["has_ts"]):
                ws[ixq] = k
        self.wa, self.ws = wa, ws

    def _bil_rates(self, k: int, sb_k, sw_g):
        """_trq_rates' (tb, sb) of bilateral quota k at its sigma sb_k and its global quota's sigma sw_g."""
        q = self.sc.trq_quotas[k]
        tb = q["ta_pref"] + q["dta"] * sb_k
        sb = q["ts_pref"] + q["dts"] * sb_k
        g = self.sc.trq_globals[q["glob"]] if q.get("glob") is not None else None
        if g is not None and g["has_ta"]:
            tw = g["ta_pref"] + g["dta"] * sw_g
            tb = self.sc.ncpcm(tw, tb, max(1e-2, 1e-3 * abs(q["dta"])))
        if g is not None and g["has_ts"]:
            tw = g["ts_pref"] + g["dts"] * sw_g
            sb = self.sc.ncpcm(tw, sb, max(1e-5, 1e-7 * abs(q["dts"])))
        return tb, sb

    def _cells(self, I) -> tuple:
        """The constant inputs of _xat on the cells I, extracted once per quota's bisection."""
        return (self.base[I], self.ta0n[I], self.ts0n[I], None if self.kind2 is None else self.kind2[I],
                self.X[I], self.p[I], self.off_now[I])

    def _xat(self, C: tuple, ta_c: np.ndarray, ts_c: np.ndarray) -> np.ndarray:
        """_trq_off then Xat on the cells C (_cells)."""
        base, ta0n, ts0n, kind2, Xc, pc, onow = C
        off = np.where(np.isnan(ta_c), 0.0, base * (ta_c - ta0n) / 100.0)
        sp = np.where(np.isnan(ts_c), 0.0, ts_c - ts0n)
        if kind2 is not None:
            sp = np.where(kind2, 0.0, sp)
        off = off + sp
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(Xc > 0, Xc * (pc / np.maximum(pc + off - onow, 1e-6)) ** self.sc.s2, Xc)

    def bilateral_trial(self, k: int):
        """h(s) = s - Sigmoid(fill / Q) of bilateral quota k at the trial sigma s."""
        sc, q = self.sc, self.sc.trq_quotas[k]
        I = np.ix_(q["rows"], q["cols"])
        own_a, own_s = self.wa[I] == k, self.ws[I] == k
        ta_k, ts_k = self.ta[I], self.ts[I]
        C = self._cells(I)
        gi = q.get("glob")
        sw_g = self.sW[gi] if gi is not None else None

        def h(s):
            tb, sb = self._bil_rates(k, s, sw_g)
            fill = float(self._xat(C, np.where(own_a, tb, ta_k), np.where(own_s, sb, ts_k)).sum())
            return s - float(sc._sig(fill / q["Q"]))
        return h

    def global_trial(self, m: int):
        """h(s) = s - Sigmoid(imports / Q) of global quota m at the trial sigma s: the cover's flows and the nested
        bilateral quotas' overfill, -ncpcm(-(fill - Q), 0, 1E-3 Q) (trq_global_imports)."""
        sc, g = self.sc, self.sc.trq_globals[m]
        kids = [k for k, q in enumerate(sc.trq_quotas or ())
                if q.get("glob") == m and q["regime"] != "entry_price"]
        sets = [g["cover"]] + [np.ix_(sc.trq_quotas[k]["rows"], sc.trq_quotas[k]["cols"]) for k in g["bil"]]
        pre = []
        for I in sets:
            wa_I, ws_I = self.wa[I], self.ws[I]
            km = [(k, ma, ms) for k, ma, ms in ((k, wa_I == k, ws_I == k) for k in kids) if ma.any() or ms.any()]
            pre.append((self._cells(I), self.ta[I], self.ts[I], wa_I == self._G + m, ws_I == self._G + m, km))

        def rates(s, ta_c, ts_c, own_a, own_s, kid_masks):
            if g["has_ta"]:
                ta_c = np.where(own_a, g["ta_pref"] + g["dta"] * s, ta_c)
            if g["has_ts"]:
                ts_c = np.where(own_s, g["ts_pref"] + g["dts"] * s, ts_c)
            for k, ma, ms in kid_masks:
                tb, sb = self._bil_rates(k, self.sB[k], s)
                ta_c = np.where(ma, tb, ta_c)
                ts_c = np.where(ms, sb, ts_c)
            return ta_c, ts_c

        def h(s):
            I, ta_c, ts_c, oa, os_, km = pre[0]
            tot = float(self._xat(I, *rates(s, ta_c, ts_c, oa, os_, km)).sum())
            for k, (I, ta_c, ts_c, oa, os_, km) in zip(g["bil"], pre[1:]):
                q = sc.trq_quotas[k]
                fk = float(self._xat(I, *rates(s, ta_c, ts_c, oa, os_, km)).sum())
                tot += float(-sc.ncpcm(-(fk - q["Q"]), 0.0, 1e-3 * q["Q"]))
            return s - float(sc._sig(tot / g["Q"]))
        return h

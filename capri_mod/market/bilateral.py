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

    @property
    def trq_row(self):
        """The importer rows under a quota (None without quotas): kept for the callers that only ask whether a
        commodity has quotas."""
        if not self.trq_quotas:
            return None
        return sorted({int(i) for q in self.trq_quotas for i in q["rows"]})

    def _sig(self, f):
        return 1.0 / (1.0 + np.exp(-np.clip(self.TRQ_SLOPE * (f - self.TRQ_FILL_MID), -self.TRQ_ARG_CLIP,
                                            self.TRQ_ARG_CLIP)))

    def trq_fill(self, X: np.ndarray, q: dict) -> float:
        """The quota's imports (TradeFlowsAgg_): the flows from its exporter's to its importer's market regions."""
        return float(X[np.ix_(q["rows"], q["cols"])].sum())

    def trq_unit(self, r: np.ndarray, q: dict) -> np.ndarray:
        """d p / d sigma of the quota's flows (EUR/t per unit of sigma): (a0 r + tc) dta / 100 + dts."""
        tc = self.tc if self.tc is not None else np.zeros_like(self.a0)
        base = self.a0[np.ix_(q["rows"], q["cols"])] * r[None, q["cols"]] + tc[np.ix_(q["rows"], q["cols"])]
        return base * q["dta"] / 100.0 + q["dts"]

    def trq_base(self) -> None:
        """Each quota's sigma at the base flows (the calibration point, at the base volume) and no offset."""
        n = len(self.regions)
        self.trq_offset = np.zeros((n, n))
        if not self.trq_quotas:
            self.trq_sigma = self.trq_sigma0 = None
            return
        s0 = np.array([float(self._sig(self.trq_fill(self.X0, q) / q["Q0"])) if q["Q0"] > 0 else 0.0
                       for q in self.trq_quotas])
        self.trq_sigma0, self.trq_sigma = s0, s0.copy()

    def trq_set_offsets(self, r: np.ndarray) -> None:
        """trq_offset from the quotas' current sigma at the exporters' price ratios r."""
        n = len(self.regions)
        off = np.zeros((n, n))
        for k, q in enumerate(self.trq_quotas or ()):
            off[np.ix_(q["rows"], q["cols"])] = self.trq_unit(r, q) * (self.trq_sigma[k] - self.trq_sigma0[k])
        self.trq_offset = off

    def trq_solve(self, X: np.ndarray, p: np.ndarray, r: Optional[np.ndarray] = None) -> None:
        """Each quota's sigma consistent with its own flows: sigma = Sigmoid(slope / Q (fill(sigma) - 0.97 Q)), with
        the flows' local response to their own import prices, X (p / (p + d (sigma - sigma_now)))^s2 (other prices
        held); bisection on sigma in [0, 1], so the steep CAPRI sigmoid is solved without oscillating. Then the
        offsets at the price ratios r (ones if not given)."""
        if not self.trq_quotas:
            return
        r = np.ones(len(self.regions)) if r is None else np.asarray(r, dtype=float)
        if self.trq_sigma is None:
            self.trq_base()
        new = self.trq_sigma.copy()
        for k, q in enumerate(self.trq_quotas):
            if q["Q"] <= 0:
                new[k] = 1.0
                continue
            ix = np.ix_(q["rows"], q["cols"])
            x, pp, d = X[ix], p[ix], self.trq_unit(r, q)
            live = (x > 0) & (pp > 0)
            if not live.any():
                new[k] = float(self._sig(0.0))
                continue
            sc = float(self.trq_sigma[k])

            def h(s):
                xo = (x[live] * (pp[live] / np.maximum(pp[live] + d[live] * (s - sc), 1e-6)) ** self.s2).sum()
                return s - float(self._sig(xo / q["Q"]))

            lo, hi = 0.0, 1.0
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if h(mid) > 0:
                    hi = mid
                else:
                    lo = mid
            new[k] = 0.5 * (lo + hi)
        self.trq_sigma = new
        self.trq_set_offsets(r)

    def import_prices(self, r: np.ndarray, tariff_adds=None) -> np.ndarray:
        """Import prices p_ij at the exporters' price ratios r. tariff_adds: [(importer rows, points of ad valorem
        tariff added)], CAPRI impPrice_ (arm/market_model.gms l. 2849-2882): the ad valorem tariff applies to the
        exporter's market price plus the transport cost; flows between the rows of one importer (the EU's trade
        blocks) carry none."""
        p = self.a * r[None, :] + self.b
        if self.trq_quotas and self.trq_offset is not None:
            p = p + self.trq_offset
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

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

    def calibrate(self, S0: np.ndarray, max_export_share: float = 0.98) -> None:
        """Closure at the model's own base supply S0: CAPRI's trade flows are kept, domestic sales absorb the
        difference between the model's production and CAPRI's (DS0 = S0 - exports); where a region would
        export more than max_export_share of its production its exports are scaled down."""
        n = len(self.regions)
        X = self.X0.copy()
        off = ~np.eye(n, dtype=bool)
        # regions whose CAPRI exports exceed the cap on the model's base supply: (region, exports / supply). Recorded
        # so the runs show whether the 0.98 (not CAPRI's: PROXY_AUDIT S192) is ever reached
        self.export_cap_hits = []
        for j in range(n):
            e = float(X[off[:, j], j].sum())
            cap = max_export_share * max(float(S0[j]), 0.0)
            if e > cap:
                self.export_cap_hits.append((self.regions[j], e / float(S0[j]) if float(S0[j]) > 0 else float("inf")))
                f = cap / e if e > 0 else 0.0
                X[off[:, j], j] *= f
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

    # EU tariff-rate quotas (CAPRI TRQ regime, bilateral TrqNT): importer row (or rows: the EU's quotas are filled
    # by the imports of both EU trade blocks), per exporter quota (1000 t), out-of-quota minus in-quota price gap
    # (EUR/t), share of the flow under the quota regime at base
    trq_row: Optional[object] = None
    trq_Q: Optional[np.ndarray] = None
    trq_gap: Optional[np.ndarray] = None
    trq_share: Optional[np.ndarray] = None
    trq_offset: Optional[np.ndarray] = None
    #: base quotas (1000 t) when a scenario changes the quota volumes (MarketModule._apply_trq_volumes); the base
    #: fill, at which the base tariff regime is calibrated, is taken at these
    trq_Q0: Optional[np.ndarray] = None
    #: CAPRI p_trqSigmoidSlope = 200 on (imports - 0.97 quota) / quota: the tariff moves from in- to
    #: out-of-quota within about +-3% of the quota (arm/market_model.gms trqSigmoidFunc_)
    TRQ_SLOPE = param("TRQ_SLOPE")

    def _rows(self) -> np.ndarray:
        return np.atleast_1d(np.asarray(self.trq_row, dtype=int))

    def _sig(self, f):
        return 1.0 / (1.0 + np.exp(-np.clip(self.TRQ_SLOPE * (f - 0.97), -60, 60)))

    def trq_solve(self, X: np.ndarray, p: np.ndarray) -> None:
        """Set each quota's offset consistent with its own flow: o = gap (sig(fill(X(o))) - sig(fill0)), with the
        flow's local response to its own import price X(o) = X (p / (p + o - o_cur))^s2 (other prices held);
        bisection, so the steep CAPRI sigmoid is solved without oscillating."""
        if self.trq_row is None:
            return
        rows = self._rows()
        new = self.trq_offset.copy()
        for j in np.where(self.trq_Q > 0)[0]:
            xj = float(X[rows, j].sum())
            pj = float((X[rows, j] * p[rows, j]).sum() / xj) if xj > 0 else float(p[rows[0], j])
            oc, g = float(self.trq_offset[j]), float(self.trq_gap[j])
            if xj <= 0 or pj <= 0 or g <= 0:
                continue
            k = self.trq_share[j] / self.trq_Q[j]
            Qb = float(self.trq_Q0[j]) if self.trq_Q0 is not None else float(self.trq_Q[j])
            s0 = self._sig(self.trq_share[j] / Qb * float(self.X0[rows, j].sum())) if Qb > 0 else 0.0

            def h(o):
                xo = xj * (pj / max(pj + o - oc, 1e-6)) ** self.s2
                return o - g * (self._sig(k * xo) - s0)

            lo, hi = -g * s0 - 1e-9, g * (1.0 - s0) + 1e-9
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if h(mid) > 0:
                    hi = mid
                else:
                    lo = mid
            new[j] = 0.5 * (lo + hi)
        self.trq_offset = new

    def import_prices(self, r: np.ndarray, tariff_adds=None) -> np.ndarray:
        """Import prices p_ij at the exporters' price ratios r. tariff_adds: [(importer rows, points of ad valorem
        tariff added)], CAPRI impPrice_ (arm/market_model.gms l. 2849-2882): the ad valorem tariff applies to the
        exporter's market price plus the transport cost; flows between the rows of one importer (the EU's trade
        blocks) carry none."""
        p = self.a * r[None, :] + self.b
        if self.trq_row is not None and self.trq_offset is not None:
            rows = self._rows()
            p[rows] = p[rows] + self.trq_offset[None, :]
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

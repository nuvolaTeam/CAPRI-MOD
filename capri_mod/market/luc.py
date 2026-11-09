"""CAPRI's land-use-change estimation in the market model outside the EU (luc_market; arm/market_model.gms l. 1918-1990,
arm/define_land_params.gms l. 763-1100, arm/prep_market.gms l. 141-180).

For each non-EU market region with CAPRI's market land block (the regions without supply models), the land of the
market's land types (LandSupplyMNL_'s FORE, ARTIF, OLND, TCRP, FODFAL, FRUN, and INLW) is linked to CAPRI's six UNFCCC
land classes c by LinkLuWithShares_, v_land(c) = sum_k p_shFstInSecMrk(c, k) v_land(k) (GRAS and TGRS shares of
FODFAL first, CROP = TCRP + TGRS + FRUN, GRSLND = GRAS + a share of OLND, WETLND = INLW + a share of OLND, RESLND = a
share of OLND). The 36 transitions x_j (lucpos, from class f(j) to class t(j); annual on the off-diagonal, totals on the
diagonal) solve CAPRI's square system

    luClassInitial_:  sum_{j: f(j) = c} a_j x_j = initial land of c        (a_j: p_lucAnnualFac, 1 on the diagonal)
    luClassFinal_:    sum_{j: t(j) = c} a_j x_j = v_land(c)
    FocLUC_ with derivativeOfGammaLUC_:  -beta_j + (alpha_j - 1) / x_j + mu_t(j) + lambda_f(j) = 0

(v_derivativeOfLogDensSlakMrkt fixed at 0; CAPRI's FOC carries the duals without the annual factor, and so does this
port). So x_j = (alpha_j - 1) / (beta_j - mu_t(j) - lambda_f(j)), and the balances are the gradient of the convex
function Phi(mu, lambda) = - sum_j a_j (alpha_j - 1) log(beta_j - mu_t(j) - lambda_f(j)) - mu.F - lambda.I, whose
minimum (Newton with a backtracking line search) is CAPRI's solution. The duals are determined up to a common shift
(mu + k, lambda - k), and one balance is implied by the others (the land total), so the first initial-class dual is
held at 0.

The block does not feed back on the market's prices or quantities in capri-mod: in CAPRI it does only through the
LULUCF cost of land use change (v_glucCostPerHa in the land rents, lulucf_market, with a carbon price on LULUCF),
which is not ported. Every transition of sim_ini_21730 has a gamma prior (no normal or spike densities).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from capri_mod.settings import current as _settings

#: CAPRI's UNFCCC land classes (luClass), in CAPRI's order
LU_CLASSES = ("FORE", "ARTIF", "CROP", "WETLND", "GRSLND", "RESLND")


@dataclass
class LucParams:
    """Per region: pos (the transitions), From and To (classes x transitions, 0/1), fac (annual factors), alpha,
    beta, lower, level_cal (CAPRI's CAL transitions), initial (per class), inlw, shares {target: {source: share}}."""
    regions: dict = field(default_factory=dict)

    @classmethod
    def from_frames(cls, priors: pd.DataFrame, classes: pd.DataFrame, shares: pd.DataFrame) -> "LucParams":
        out = {}
        for r, g in priors.groupby("rms", sort=True):
            pos = list(g.lucpos)
            cl = classes[classes.rms == r].set_index("luclass")
            sh: dict = {}
            for t in shares[shares.rms == r].itertuples(index=False):
                sh.setdefault(t.target, {})[t.source] = float(t.share)
            out[r] = {"pos": pos,
                      "From": np.array([[1.0 if f == c else 0.0 for f in g.from_class] for c in LU_CLASSES]),
                      "To": np.array([[1.0 if f == c else 0.0 for f in g.to_class] for c in LU_CLASSES]),
                      "fac": g.annual_factor.to_numpy(float), "alpha": g.alpha.to_numpy(float),
                      "beta": g.beta.to_numpy(float), "lower": g.lower.to_numpy(float),
                      "level_cal": g.level_cal.to_numpy(float),
                      "initial": np.array([float(cl.at[c, "initial_kha"]) if c in cl.index else 0.0
                                           for c in LU_CLASSES]),
                      "inlw": float(cl.inlw_kha.iloc[0]) if len(cl) else 0.0, "shares": sh}
        return cls(out)


def final_classes(d: dict, land: dict) -> dict:
    """LinkLuWithShares_: the final land per class from the market's land types (land: {FORE, ARTIF, OLND, TCRP,
    FODFAL, FRUN: 1000 ha}; INLW the region's, fixed). GRAS and TGRS are FODFAL's shares; the classes sum the shares
    of FORE, ARTIF, FRUN, TGRS, TCRP, GRAS, INLW and OLND."""
    sh = d["shares"]
    lv = dict(land)
    lv["INLW"] = d["inlw"]
    for k in ("GRAS", "TGRS"):
        lv[k] = sum(s * float(lv.get(src, 0.0)) for src, s in sh.get(k, {}).items())
    return {c: sum(s * float(lv.get(src, 0.0)) for src, s in sh.get(c, {}).items()) for c in LU_CLASSES}


def solve_region(d: dict, final: dict, max_iter: int | None = None, tol: float | None = None):
    """CAPRI's transitions at the final land per class (final_classes): (x, info) with info the iterations, the
    largest balance residual (1000 ha) and the duals (mu per final class, lambda per initial class). Newton's
    iterations and its tolerance (relative to the largest initial class) are the settings market.luc_max_iter and
    market.luc_tol unless given."""
    st = _settings()
    max_iter = int(st.get("market.luc_max_iter")) if max_iter is None else max_iter
    tol = float(st.get("market.luc_tol")) if tol is None else tol
    To, Fr, fac, al, be = d["To"], d["From"], d["fac"], d["alpha"], d["beta"]
    F = np.array([float(final[c]) for c in LU_CLASSES])
    I = d["initial"]
    if abs(F.sum() - I.sum()) > 1e-6 * max(1.0, I.sum()):
        raise ValueError(f"luc_market: final land {F.sum():.6f} against initial {I.sum():.6f}: the balances cannot "
                         f"both hold")
    A = np.vstack([To, Fr])
    keep = np.r_[0:6, 7:12]                          # lambda of the first class held at 0 (the duals' common shift)
    b = np.concatenate([F, I])
    z = np.zeros(12)
    # start: the duals that put each transition at CAPRI's calibration level where it has one (least squares)
    x0 = np.maximum(d["level_cal"], d["lower"])
    s0 = be - (al - 1.0) / x0
    z[keep] = np.linalg.lstsq(A.T[:, keep], s0, rcond=None)[0]

    def x_of(z_):
        den = be - A.T @ z_
        return (al - 1.0) / den, den

    def phi(z_):
        den = be - A.T @ z_
        if np.any(den <= 0.0):
            return np.inf
        return float(-np.sum(fac * (al - 1.0) * np.log(den)) - z_ @ b)

    if not np.isfinite(phi(z)):
        z = np.zeros(12)
    scale = max(1.0, float(np.max(I)))
    it = 0
    for it in range(1, max_iter + 1):
        x, _ = x_of(z)
        g = A @ (fac * x) - b
        if np.max(np.abs(g[keep])) < tol * scale:
            break
        W = fac * x * x / (al - 1.0)
        H = (A[keep] * W) @ A[keep].T
        dz = np.zeros(12)
        dz[keep] = -np.linalg.solve(H, g[keep])
        t, f0, slope = 1.0, phi(z), float(g @ dz)
        while phi(z + t * dz) > f0 + 1e-4 * t * slope and t > 1e-12:
            t *= 0.5
        z = z + t * dz
    x, _ = x_of(z)
    res = float(np.max(np.abs(A @ (fac * x) - b)))
    return x, {"iterations": it, "residual": res, "mu": z[:6], "lambda": z[6:]}


class LucMixin:
    """The market's land-use-change report outside the EU (luc_market): MarketModule.noneu_luc at the market's land
    solution."""

    def _luc_params(self) -> LucParams | None:
        c = getattr(self, "_luc_cache", None)
        if c is not None:
            return c or None
        inp = self._inp()
        frames = [inp.csv(n, required=False, keep_default_na=False)
                  for n in ("luc_market_priors.csv", "luc_market_classes.csv", "luc_market_shares.csv")]
        self._luc_cache = LucParams.from_frames(*frames) if all(f is not None for f in frames) else False
        return self._luc_cache or None

    def noneu_land_levels(self, land: dict | None) -> dict:
        """{rms: {land type: 1000 ha}} of the non-EU land markets at the free rents' change land ({rms: array},
        noneu_land_solve; None or a missing region: the calibration point): LandSupplyMNL_'s six types."""
        P = self._noneu_land_params()
        out = {}
        for rms, d in P.items():
            rent = np.asarray(d["rent0"], float).copy()
            dr = (land or {}).get(rms)
            if dr is not None:
                for k, i in enumerate(d["free"]):
                    rent[i] += float(dr[k])
            z = np.asarray(d["alu"], float) + np.asarray(d["B"], float) @ rent
            e = np.exp(z - z.max())
            out[rms] = dict(zip(d["lu"], (float(v) for v in d["avail"] * e / e.sum())))
        return out

    def noneu_luc(self, land: dict | None) -> dict:
        """{rms: {"classes": {class: final 1000 ha}, "transitions": {lucpos: 1000 ha (annual off the diagonal)}}} at
        the market's land solution; {} without the land block or the priors."""
        prm = self._luc_params()
        if prm is None:
            return {}
        out = {}
        for rms, lv in self.noneu_land_levels(land).items():
            d = prm.regions.get(rms)
            if d is None:
                continue
            fin = final_classes(d, lv)
            x, info = solve_region(d, fin)
            if info["residual"] > float(_settings().get("market.luc_accept_tol")) * max(1.0, float(np.max(d["initial"]))):
                raise RuntimeError(f"market: the land-use change of {rms} did not solve (residual {info['residual']:.3g})")
            out[rms] = {"classes": {c: float(v) for c, v in fin.items()},
                        "transitions": dict(zip(d["pos"], (float(v) for v in x)))}
        return out

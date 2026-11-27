r"""The regional NLP's feed terms: the N loss cascade, CasADi evaluation helpers, the feeds' scale and the calibration
of the feed terms (moved from capri_mod/supply/capri_regional_nlp.py as they were, 26 November 2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings


def _cascade_loss(sub, sh):
    """CAPRI's NH3 loss per unit of excreted N (ammonia_techs.loss) with symbolic shares: sh {tech: expr}."""
    def stage(rH, rS):
        hm = 1.0 - sub["g"]
        h = hm * sub["fH"] * (1.0 - rH)
        s = (hm - h) * sub["fS"] * (1.0 - rS)
        return h + s, hm - h - s
    RA = 0
    for t in sub["techs"]:
        if t["group"] == "APP":
            RA = RA + sh[t["tech"]] * t["rA"]
    man = [t for t in sub["techs"] if t["group"] == "MAN"]
    noc = 1.0
    for t in man:
        noc = noc - sh[t["tech"]]
    L0, P0 = stage(0.0, 0.0)
    L, P = noc * L0, noc * P0
    for t in man:
        l_, p_ = stage(t["rH"], t["rS"])
        L = L + sh[t["tech"]] * l_
        P = P + sh[t["tech"]] * p_
    return sub["g"] * sub["fG"] + L + P * sub["fA"] * (1.0 - RA)


class _AtP:
    """A CasADi function of (x, p) evaluated at the model's parameter values: f(x)."""

    def __init__(self, f, p):
        self.f, self.p = f, p

    def __call__(self, x):
        return self.f(x, self.p)


def ca_eval(expr, X, x, p=None, pval=None):
    import casadi as ca
    if p is None:
        return ca.Function("e", [X], [expr])(x)
    return ca.Function("e", [X, p], [expr])(x, pval)


def _feed_scale(r, j):
    """Scale of a per-head feed variable (kg/head): its base amount, or 1% of the base dry matter intake in this feed's
    units where the base ration does not use it."""
    x0 = float(r.x0[j])
    if x0 > 0:
        return x0
    D0 = float(r.dm @ r.x0)
    return max(0.01 * D0 / max(float(r.dm[j]), 1e-6), 1e-6)


def foc_fb_mode() -> str:
    """fertiliser.foc_lower_bound_complementarity: "fallback", "always" or "off" (DEP-49; a switch true/false until 16
    November 2026, "always"/"off" now)."""
    v = str(_settings().get("fertiliser.foc_lower_bound_complementarity")).strip().lower()
    if v not in ("fallback", "always", "off"):
        raise ValueError(f"fertiliser.foc_lower_bound_complementarity: {v!r} (fallback, always or off)")
    return v


def calibrate_feed_terms(r, fodder=()):
    """CNST of each flexible feed so that the base ration solves CAPRI's simulation feeding problem (REQSE_ only).

    Returns (cnst_new, lam {"E": .., "P": ..}, delta) with delta = cnst_new - r.cnst. Prices at base: the ration's p0
    (for fodder the base value, the expected dual of its balance)."""
    fl = np.asarray(r.flex, bool)
    g = np.where(fl, r.p0 + r.cnst + r.slope * r.x0, 0.0)
    pos = fl & (r.x0 > 0)
    lam = {"E": 0.0, "P": 0.0}
    cols, keys = [], []
    for k, v, R in (("E", r.e, float(r.e @ r.x0)), ("P", r.cp, float(r.cp @ r.x0))):
        if R > 0:
            cols.append(v); keys.append(k)
    delta = np.zeros(len(r.feeds))
    if pos.any() and cols:
        M = np.array(cols).T[pos]
        if not getattr(r, "lam", None):
            # the ration's requirements were below the base supply (not binding: its terms give the feeds no marginal
            # value). CAPRI simulates with the requirement trimmed to the base supply, which binds: the requirement
            # duals are then the fit of the feeds' base prices on their contents (non-negative), as feed/ration.py
            # does for a binding requirement
            from scipy.optimize import nnls
            sc_ = np.maximum(np.abs(M).max(axis=0), 1e-12)
            sol, _ = nnls(M / sc_, r.p0[pos])
            sol = sol / sc_
        else:
            sol, *_ = np.linalg.lstsq(M, g[pos], rcond=None)
        lam.update(dict(zip(keys, sol.tolist())))
    shadow = lam["E"] * r.e + lam["P"] * r.cp
    delta[pos] = shadow[pos] - g[pos]
    zero = fl & ~(r.x0 > 0)
    # feeds not used at base: reduced cost g - shadow >= 0 (keep the ration's own term where it already is)
    delta[zero] = np.maximum(shadow[zero] - g[zero], 0.0)
    return r.cnst + delta, lam, delta

"""The first step of the port of CAPRI's bounds, their widening and the fudge equations (docs/dev/MARKET_BOUNDS_PLAN.md): CAPRI's bounds on the market model's variables at the start of a
market solve (arm/set_start_val.gms), for the unknowns of the whole-market system's lifted form (market_system_ad.market_system(...,
lifted=True)).

CAPRI's factors (arm/market_model.gms l. 322-326): P_lowLimitFactQuant 1e-5, p_uppLimitFactQuant 1e3,
P_lowLimitFactPrice 0.1, p_uppLimitFactPrice 10. Per unknown, with L its level at the start (the previous solve's
solution, as CAPRI's .L):

  r_c   v_marketPrice(RM, c) / PMrk: 0.1 x PMrk to 10 x PMrk (set_start_val.gms l. 527-528; the bound is on the
        calibration point's DATA PMrk, so the ratio's is 0.1 to 10); a region without a market price in CAPRI's data
        (pmrk_data false) has its price fixed (CAPRI: v_marketPrice.fx = 0, l. 525)
  sB/sW the quotas' sigmas: 0 to 1 (a sigmoid's range)
  PA    v_arm1Price(RM, c): 0.1 x L to max(1000, L) x 10 (l. 754-755, L in EUR/t); fixed where the region has no
        Armington quantity (v_arm1Price.FX = DATA arm1P where v_arm1Quant.L is 0, l. 756): the ratio held at its start
  D     v_arm1Quant(RM, c): min(1e-6, L x 1e-5) to max(1, L) x 1e3 (l. 418-419); fixed at 0 where L is 0 (l. 408)
  S     v_prodQuant(RM, c): CAPRI bounds it per behavioural region (RMS) and sums the bounds to the market region
        (l. 101-108, 148-149): here on the market region's own level, max(1e-8, min(1e-6, |L| x 1e-5)) to
        max(1, |L|) x 1e3 (the sum over CAPRI's RMS differs by the per-region minima: at most n_RMS x 1e-6 below and
        1e3 per RMS of less than 1 kt above; to be replaced by the RMS sum where the model holds the RMS levels); a
        negative level: -max(1, L) x 1e3 (l. 105-106; the young animals are not market commodities here)
  L     the lifted processing and non-EU feed cells (market_system(..., lift_use=True), layout["lift_cells"], each
        with its calibration-point level b): processing v_procQuant b x 1e-5 to max(1, b) x 1e3 (l. 34-35), fixed at
        its level where that is at most 0.1 (l. 37); feed v_feedQuant max(1e-10, min(1e-8, b x 1e-5)) to
        max(1, b) x 1e3 (l. 181-182). CAPRI bounds them per behavioural region: here per market region's cell, as S
  other the young-animal prices, the dairy blocks' unknowns, FEDE, the non-EU rents: open here (CAPRI's bounds on
        them in a later step)

capri_start_bounds(mm, lay, x0) -> (lbx, ubx) over the lifted system's unknowns (x0 = market_x0(mm, lay)).
widen(mm, lay, x, lb, ub, lam) -> (lb, ub, n): CAPRI's widen_bounds.gms FULL (the port's third step) for the unknowns at a bound
    whose multiplier (lam, IPOPT's lam_x of a least-infeasibility solve) is not zero, per variable family:
      r   v_marketPrice (l. 428-436): lower max(1e-7, 0.2 x lower, 1e-4 x PMrk), upper max((PMrk + 1) x 100,
          (upper + 1) x 5), in price ratios
      PA  v_arm1Price (l. 350-360): lower max(1e-8 x arm1P, 1e-8, 0.2 x lower), upper min((arm1P + 1) x 100,
          (upper + 1) x 5), arm1P CAPRI's calibration point (PA0)
      D   v_arm1Quant (l. 263-284): lower max(1e-12, 0.1 x lower) (with the marginal; max(1e-11, 0.1 x lower) for
          every unknown at its lower bound, l. 269-272), upper min(10 x upper, 1e8), fixed at its lower bound where
          that is at 1e-11 or below
      S   v_prodQuant (l. 47-52, 82-86): lower L - 10 x max(10, the calibration level, |L|) (negative: the market
          region's fudge row, ProdFudge_, step 4), upper 1000 x |upper|
      L   processing v_procQuant (l. 125-138): lower L - 10 x max(10, b, |L|) (negative: ProcFudge_), upper 1000 x
          upper; non-EU feed v_feedQuant (l. 192-200): lower lower - 100 x max(1, b, |L|) (FeedFudge_), upper
          min(1e6, 10 x upper)
    n the number of bounds moved.
"""
from __future__ import annotations

import numpy as np

#: CAPRI's factors, arm/market_model.gms l. 322-326
LOW_QUANT, UPP_QUANT = 1e-5, 1e3
LOW_PRICE, UPP_PRICE = 0.10, 10.0


def capri_start_bounds(mm, lay, x0) -> tuple:
    """(lbx, ubx) for the lifted system's unknowns: CAPRI's bounds of set_start_val.gms (see the module's docstring)
    at the start levels x0."""
    if not lay.get("lifted"):
        raise ValueError("capri_start_bounds: the lifted system's layout is needed (market_system(..., lifted=True))")
    x0 = np.asarray(x0, float)
    lb, ub = np.full(x0.size, -np.inf), np.full(x0.size, np.inf)
    sysd = mm.par.bilat
    regions, cols = list(lay["regions"]), list(lay["cols"])
    nR, nC = len(regions), len(cols)
    bcols = [c for c in cols if c in sysd]
    o = 0
    for name, n in lay["x"]:
        sl = slice(o, o + n)
        v = x0[sl]
        if name.startswith("r_"):
            sc = sysd[name[2:]]
            has = np.asarray(sc.pmrk_data, bool) if sc.pmrk_data is not None else np.ones(n, bool)
            lb[sl] = np.where(has, LOW_PRICE, v)
            ub[sl] = np.where(has, UPP_PRICE, v)
        elif name.startswith("sB_") or name.startswith("sW_"):
            lb[sl], ub[sl] = 0.0, 1.0
        elif name == "PA":
            # column-blocks of the bilateral commodities in the system's order, regions within
            pa = np.empty(n)
            pa0 = np.empty(n)
            has_q = np.empty(n, bool)
            D0 = _block(x0, lay, "D").reshape(nC, nR).T          # S and D are stored column by column
            for k, c in enumerate(bcols):
                sc = sysd[c]
                pa0[k * nR:(k + 1) * nR] = np.asarray(sc.PA0, float)
                has_q[k * nR:(k + 1) * nR] = D0[:, cols.index(c)] > 0
            pa[:] = v * pa0                                        # EUR/t
            lo = LOW_PRICE * pa
            hi = np.maximum(1000.0, pa) * UPP_PRICE
            lb[sl] = np.where(has_q, lo / pa0, v)
            ub[sl] = np.where(has_q, hi / pa0, v)
        elif name == "D":
            lb[sl] = np.where(v > 0, np.minimum(1e-6, v * LOW_QUANT), 0.0)
            ub[sl] = np.where(v > 0, np.maximum(1.0, v) * UPP_QUANT, 0.0)
        elif name == "S":
            a = np.abs(v)
            lo = np.where(v != 0, np.maximum(1e-8, np.minimum(1e-6, a * LOW_QUANT)), 0.0)
            hi = np.where(v != 0, np.maximum(1.0, v) * UPP_QUANT, 0.0)
            lb[sl] = np.where(v < 0, -np.maximum(1.0, v) * UPP_QUANT, lo)
            ub[sl] = hi
        elif name == "L":
            kind, b = _lift_kinds(lay)
            proc = kind == "proc"
            lo = np.where(proc, b * LOW_QUANT, np.maximum(1e-10, np.minimum(1e-8, b * LOW_QUANT)))
            hi = np.maximum(1.0, b) * UPP_QUANT
            fix = proc & (v <= 0.1)
            lb[sl], ub[sl] = np.where(fix, v, lo), np.where(fix, v, hi)
        o += n
    return lb, ub


def _lift_kinds(lay) -> tuple:
    """(kind, base level) arrays of the lifted processing and feed cells (layout["lift_cells"])."""
    lc = list(lay.get("lift_cells") or ())
    return (np.array([c[0] for c in lc], dtype=object), np.array([float(c[3]) for c in lc], float))


def _block(x, lay, name) -> np.ndarray:
    """The entries of x of the unknowns `name` (lay["x"])."""
    o = 0
    for nm, n in lay["x"]:
        if nm == name:
            return np.asarray(x, float)[o:o + n]
        o += n
    raise KeyError(name)


def violated(lay, x, lb, ub, tol=0.0) -> list:
    """The unknowns of x outside [lb - tol, ub + tol]: [(block name, index in the block, value, lb, ub)]."""
    x = np.asarray(x, float)
    out = []
    o = 0
    for nm, n in lay["x"]:
        for i in np.nonzero((x[o:o + n] < lb[o:o + n] - tol) | (x[o:o + n] > ub[o:o + n] + tol))[0]:
            out.append((nm, int(i), float(x[o + i]), float(lb[o + i]), float(ub[o + i])))
        o += n
    return out


def _at(x, b, tol):
    """x at the bound b: within tol x max(1, |b|) (IPOPT's solution lies on a bound to its tolerance)."""
    return np.isfinite(b) & (np.abs(x - b) <= tol * np.maximum(1.0, np.abs(b)))


def widen(mm, lay, x, lb, ub, lam, tol=1e-6, base=None) -> tuple:
    """CAPRI's widening of the bounds that hold the solve (see the module's docstring): (lb, ub, n moved). lam: the
    unknowns' bound multipliers (IPOPT's lam_x: negative at a lower bound, positive at an upper one); base: the
    unknowns' calibration-point values (x0 of the calibration; default x) for S's rule."""
    x, lam = np.asarray(x, float), np.asarray(lam, float)
    lb, ub = np.array(lb, float), np.array(ub, float)
    base = x if base is None else np.asarray(base, float)
    sysd = mm.par.bilat
    regions, cols = list(lay["regions"]), list(lay["cols"])
    nR = len(regions)
    bcols = [c for c in cols if c in sysd]
    moved = 0
    o = 0
    for name, n in lay["x"]:
        sl = slice(o, o + n)
        xs, l_, u_, m_ = x[sl], lb[sl], ub[sl], lam[sl]
        free = l_ != u_
        at_lo = _at(xs, l_, tol) & free
        at_up = _at(xs, u_, tol) & free
        mk = np.abs(m_) > 0
        new_l, new_u = l_.copy(), u_.copy()
        if name.startswith("r_"):
            pd0 = np.asarray(sysd[name[2:]].Pd0, float)
            lo_lev, up_lev = l_ * pd0, u_ * pd0
            new_l = np.where(at_lo & mk, np.maximum.reduce([np.full(n, 1e-7), 0.2 * lo_lev, 1e-4 * pd0]) / pd0, l_)
            new_u = np.where(at_up & mk, np.maximum((pd0 + 1.0) * 100.0, (up_lev + 1.0) * 5.0) / pd0, u_)
        elif name == "PA":
            pa0 = np.concatenate([np.asarray(sysd[c].PA0, float) for c in bcols]) if bcols else np.zeros(0)
            lo_lev, up_lev = l_ * pa0, u_ * pa0
            new_l = np.where(at_lo & mk, np.maximum.reduce([pa0 * 1e-8, np.full(n, 1e-8), 0.2 * lo_lev]) / pa0, l_)
            new_u = np.where(at_up & mk, np.minimum((pa0 + 1.0) * 100.0, (up_lev + 1.0) * 5.0) / pa0, u_)
        elif name == "D":
            new_l = np.where(at_lo & mk, np.maximum(1e-12, 0.1 * l_), l_)
            new_l = np.where(at_lo & ~mk, np.maximum(1e-11, 0.1 * l_), new_l)
            new_u = np.where(at_up & mk, np.minimum(10.0 * u_, 1e8), u_)
            fix = at_lo & mk & (l_ <= 1e-11)
            new_l, new_u = np.where(fix, l_, new_l), np.where(fix, l_, new_u)
        elif name == "S":
            b = base[sl]
            new_l = np.where(at_lo & mk, xs - 10.0 * np.maximum.reduce([np.full(n, 10.0), np.abs(b), np.abs(xs)]),
                             l_)
            new_u = np.where(at_up & mk, np.abs(u_) * 1000.0, u_)
        elif name == "L":
            kind, b = _lift_kinds(lay)
            proc = kind == "proc"
            a = np.abs(xs)
            lo_p = xs - 10.0 * np.maximum.reduce([np.full(n, 10.0), np.abs(b), a])
            lo_f = l_ - 100.0 * np.maximum.reduce([np.ones(n), np.abs(b), a])
            new_l = np.where(at_lo & mk, np.where(proc, lo_p, lo_f), l_)
            new_u = np.where(at_up & mk, np.where(proc, 1000.0 * u_, np.minimum(1e6, 10.0 * u_)), u_)
        moved += int(np.sum(new_l != l_) + np.sum(new_u != u_))
        lb[sl], ub[sl] = new_l, new_u
        o += n
    del nR
    return lb, ub, moved


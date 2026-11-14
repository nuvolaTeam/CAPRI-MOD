"""G3.2d: the market's use side as one CasADi function of the system's unknowns.

`MarketModule.demand_response` composes the use per region and commodity (CAPRI's ArmBal1_: human consumption + feed +
processing + biofuel processing, raw milk delivered, the biofuels' own use) from the blocks' CasADi functions (G2b-G2g)
called on numbers. `use_function(mm)` composes the same blocks, in the same order and with the same floors, on symbols:

    D = use(PR, RB, fede, milk, biofX, ddgs)

  PR     [nR x nC] the Armington price ratios (demand_response's PR)
  RB     [nR x nC] the producer price ratios r (the EU feed bulks' response within the market, feedBlk_; the oil and
         cake prices of the crushing margin)
  fede   [n_rms]   the non-EU behavioural regions' feed energy price ratios (FeedBal_; their order: rms)
  milk   [n_milk]  raw milk delivered to the dairies of the market regions that have one (milk_regs: the EU market
         regions, Norway, the other regions with a dairy block): quantities of the supply side
  biofX  [n_grp]   each biofuel feedstock group's first-generation output (the supply side's biofuel block)
  ddgs   [n_dreg]  the DDGS producer price ratio of each region with feedstock groups

The calibration state of the market solve (the supply models' latest results: the seen prices, the bulks' indices, the
FMIL index; the demand calibration) enters as constants, as CAPRI's parameters within a market solve. Which raw milk
rows are overridden and whether the biofuel markets are endogenous is read from the module when the function is built
(the solve's settings and data, not its unknowns), and so is whether FeedNQ_ applies (as demand_response: only when the
module holds FEDE, ev.fede_now, i.e. inside a bilateral evaluation).

`use_inputs(mm)` reads the numbers of the module's latest evaluation; `use_function(mm)(*use_inputs(mm))` equals that
evaluation's use (tools/check/g3_use_residuals.py at captured solves).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def _sx_matrix(ca, cells: Dict[Tuple[int, int], object], base: np.ndarray):
    """An SX matrix with the numbers of base and the expressions of cells."""
    M = ca.SX(ca.DM(base))
    for (i, j), v in cells.items():
        M[i, j] = v
    return M


def use_function(mm):
    """(Function, layout) of the use side at the module's current calibration state; layout holds the inputs' orders
    (rms, milk_regs, groups, ddgs_regs) and the flags read from the module."""
    import casadi as ca
    from capri_mod.market.biofuel_ad import demand_function, feed_group_function, proc_function

    regions, comms = list(mm.regions), list(mm.commodities)
    R = {r: i for i, r in enumerate(regions)}
    Cc = {c: j for j, c in enumerate(comms)}
    nR, nC = len(regions), len(comms)
    PR = ca.SX.sym("PR", nR, nC)
    RB = ca.SX.sym("RB", nR, nC)

    # the calibrated base use and its components (demand_response)
    cal = np.array([float(mm._demand_cal_factor(c)) for c in comms])
    Bv = mm.par.base_consumption.reindex(index=regions, columns=comms).fillna(0.0).to_numpy(dtype=float)
    D0 = Bv * cal[None, :]
    H0, F0, P0, Bf0 = (np.zeros((nR, nC)) for _ in range(4))
    for (r, c), s in mm._use_components().items():
        i, j = R.get(r), Cc.get(c)
        if i is None or j is None:
            continue
        H0[i, j], F0[i, j], P0[i, j], Bf0[i, j] = (D0[i, j] * s[x] for x in ("hcon", "feed", "proc", "biof"))
    FIX = D0 - H0 - F0 - P0 - Bf0
    H: Dict[Tuple[int, int], object] = {}
    F: Dict[Tuple[int, int], object] = {}
    P: Dict[Tuple[int, int], object] = {}
    Bf: Dict[Tuple[int, int], object] = {}

    # HUMAN CONSUMPTION: CAPRI's GL system (gl_food_ratio, its block function and commitments after the re-fit)
    prm = mm._gl_params()
    if prm:
        key = getattr(mm, "_gl_refit_key", None)
        if key is None or key.shape != D0.shape or not np.array_equal(key, D0):
            mm._gl_refit(D0)
            mm._gl_refit_key = D0.copy()
        from capri_mod.market.demand_ad import gl_block_function
        fn, cells, _ = gl_block_function(prm["groups"], regions, nC)
        dcat = np.concatenate([e["d"] for mr in prm["groups"] for e in prm["groups"][mr]])
        h = fn(PR, 1.0, ca.DM(dcat))[0]
        num = {c: h[k] for k, c in enumerate(cells)}
        for (mr, j), v0 in prm["x0"].items():
            i = R[mr]
            if v0 > 0 and H0[i, j] > 0:
                H[(i, j)] = H0[i, j] * (num.get((i, j), 0.0) / v0)

    # FEED: non-EU FeedNQ_ (with FEDE), p_ElasFeed elsewhere, the EU's and Norway's bulks, the FMIL block
    fb = mm._feed_bulk_params()
    fdp = mm._feed_demand_params()
    nfp = mm._noneu_feed_params() if mm.noneu_feed_nq else {"rms": {}, "totals": {}}
    rms = [s for s, d in nfp["rms"].items() if d.get("tr") in R]
    fede = ca.SX.sym("fede", len(rms))
    dairy_fed = set(mm.DAIRY_TRADED.values())
    fnq_regs = set()
    if mm.noneu_feed_nq and nfp["rms"] and mm.ev.fede_now is not None:
        from capri_mod.market.feed_ad import feednq_arrays, feednq_function
        fnq_regs = {d.get("tr") for d in nfp["rms"].values()}
        dF: Dict[tuple, object] = {}
        for k, s in enumerate(rms):
            d = nfp["rms"][s]
            a = feednq_arrays(d, comms)
            if not a["rows"]:
                continue
            dq = feednq_function(f"feednq_{s}", a, nC)(PR[R[d["tr"]], :].T, fede[k])
            for n, xm in enumerate(a["xm"]):
                dF[(d["tr"], xm)] = dF.get((d["tr"], xm), 0.0) + dq[n]
        for (r, c), v in dF.items():
            tot = nfp["totals"].get((r, c), 0.0)
            i, j = R.get(r), Cc.get(c)
            if tot > 0 and i is not None and j is not None and F0[i, j] > 0 and c not in dairy_fed:
                F[(i, j)] = F0[i, j] * ca.fmax(0.0, 1.0 + v / tot)
    for (r, c), p_ in (fdp or {}).items():
        i, j = R.get(r), Cc.get(c)
        if i is None or j is None or F0[i, j] <= 0:
            continue
        if r in fnq_regs and c not in dairy_fed:
            continue
        ft = 1.0
        for jn, e in p_["elasticities"].items():
            jj = Cc.get(jn)
            if jj is not None:
                ft = ft * PR[i, jj] ** e
        F[(i, j)] = F0[i, j] * ft
    seen = mm.seen.eu_price_seen
    bix = mm.seen.feed_bulk_index or {}
    eu_feed: Dict[str, Dict[str, object]] = {}
    E = mm._feed_bulk_elas() if (fb and mm.feed_bulk_in_market) else {}
    for reg in mm.EU:
        ie = R.get(reg)
        if ie is None or not fb:
            continue
        sv_reg = seen.loc[reg] if (hasattr(seen, "loc") and hasattr(seen, "index") and reg in seen.index) else None
        feed: Dict[str, object] = {}
        for (ms, b), d in (fb.get("bulks") or {}).items():
            if mm.eu_region_of_ms(ms) != reg:
                continue
            k = float(bix.get((ms, b), 1.0))
            el = E.get((ms, b))
            if el is not None:
                ys, ff = mm._feedblk_factor_fn(el)
                rv = ca.vertcat(*[RB[ie, Cc[y]] if y in Cc else ca.SX(1.0) for y in ys])
                sv = np.array([float(sv_reg.get(y, 1.0)) if sv_reg is not None else 1.0 for y in ys])
                w = np.array([1.0 if (y in Cc and s_ > 0) else 0.0 for y, s_ in zip(ys, sv)])
                k = k * ff(rv, sv, w)
            rr = ca.vertcat(*[PR[ie, Cc[c]] if (c and c in Cc and c in fb["feed0"]) else ca.SX(1.0)
                              for c in d["comm"]])
            q = mm._feedblk_fn(d)(rr, k)[1]
            for n, c in enumerate(d["comm"]):
                if c:
                    feed[c] = feed.get(c, 0.0) + q[n]
        eu_feed[reg] = feed
        f0r = fb["feed0_reg"].get(reg, {})
        for c, q in feed.items():
            j = Cc.get(c)
            f0 = float(f0r.get(c, 0.0))
            if j is not None and f0 > 0 and F0[ie, j] > 0:
                F[(ie, j)] = F0[ie, j] * q / f0
    sup_feed: Dict[str, Dict[str, object]] = {}
    for reg in mm.SUP:
        i = R.get(reg)
        if i is None or not fb or reg not in (mm.ev.sup_active or ()):
            continue
        f0r = (fb.get("feed0_sup") or {}).get(reg, {})
        ms0 = mm.SUP_NONEU_MS.get(reg, ())
        feed = {}
        for (ms, b), d in (fb.get("bulks_sup") or {}).items():
            if ms not in ms0:
                continue
            rr = ca.vertcat(*[PR[i, Cc[c]] if (c and c in Cc and c in f0r) else ca.SX(1.0) for c in d["comm"]])
            q = mm._feedblk_fn(d)(rr, float(bix.get((ms, b), 1.0)))[1]
            for n, c in enumerate(d["comm"]):
                if c:
                    feed[c] = feed.get(c, 0.0) + q[n]
        sup_feed[reg] = feed
        for c, q in feed.items():
            j = Cc.get(c)
            f0 = float(f0r.get(c, 0.0))
            if j is not None and f0 > 0 and F0[i, j] > 0 and c not in dairy_fed:
                F[(i, j)] = F0[i, j] * q / f0
    P9 = list(mm.DAIRY_PRODUCTS)

    def fmil(rho, dp, fi):
        """dairy_feed_factor on symbols: fi x (CES price index / own price)^0.5."""
        fd = dp["fd9"]
        v = fd * dp["p9"]
        w = v / v.sum() if v.sum() > 0 else np.ones_like(fd) / len(fd)
        sg = mm.RHO_FMIL
        pb = sum(float(w[k]) * rho[k] ** (1.0 - sg) for k in range(len(P9))) ** (1.0 / (1.0 - sg))
        return [fi * (pb / rho[k]) ** sg for k in range(len(P9))]
    if mm._dairy_params():
        dl = mm.ev.dairy_last or {}
        fi = float(mm.seen.fmil_index or 1.0)
        for reg in mm.EU:
            ie = R.get(reg)
            if ie is None:
                continue
            rho = [ca.fmax(PR[ie, Cc[mm.DAIRY_TRADED[k]]], 0.05) if mm.DAIRY_TRADED[k] in Cc
                   else max(float((dl.get("price_ratio") or {}).get(k, 1.0)), 0.05) for k in P9]
            fe = fmil(rho, mm._dairy_params(), fi)
            fn_ = eu_feed.get(reg) or {}
            f0_ = (fb or {}).get("feed0_reg", {}).get(reg, {}) if fb else {}
            for kk, k in enumerate(P9):
                c = mm.DAIRY_TRADED[k]
                j = Cc.get(c)
                if j is None or F0[ie, j] <= 0:
                    continue
                f = fn_[c] / float(f0_[c]) if (c in fn_ and float(f0_.get(c, 0.0)) > 0) else fe[kk]
                F[(ie, j)] = F0[ie, j] * f
    for reg, prm_ in (mm._dairy_world_params() or {}).items():
        i = R.get(reg)
        if i is None:
            continue
        rho = [ca.fmax(PR[i, Cc[mm.DAIRY_TRADED[k]]], 0.05) if mm.DAIRY_TRADED[k] in Cc else 1.0 for k in P9]
        fe = fmil(rho, prm_, 1.0)
        fs = sup_feed.get(reg)
        if fs:
            f0s = (fb.get("feed0_sup") or {}).get(reg, {})
            for k, c in mm.DAIRY_TRADED.items():
                if c in fs and float(f0s.get(c, 0.0)) > 0:
                    fe[P9.index(k)] = fs[c] / float(f0s[c])
        for kk, k in enumerate(P9):
            j = Cc.get(mm.DAIRY_TRADED[k])
            if j is not None and F0[i, j] > 0:
                F[(i, j)] = F0[i, j] * fe[kk]

    # PROCESSING: crushing (the seed at its Armington ratio, oil and cake at their producer ratios) and ProcNQ_
    cp = mm._crush_params()
    if cp:
        from capri_mod.market.processing_ad import crush_columns, crush_function
        pq = mm._proc_nq_params() or {}
        fn, cregs, pairs, _ = crush_function(cp, pq.get("seeds", {}), pq.get("Hrms", {}), mm.CRUSH_CHAINS)
        if pairs:
            d0 = mm._dom0().reindex(index=regions, columns=comms).to_numpy(dtype=float)
            seeds = set(mm.CRUSH_CHAINS)
            used = {r for (r, s_) in pairs if pq.get("seeds", {}).get((r, s_))}
            rows = []
            for r in cregs:
                i = R.get(r)
                row = []
                for x in crush_columns(mm.CRUSH_CHAINS):
                    j = Cc.get(x)
                    if r not in used or i is None or j is None or not d0[i, j] > 0:
                        row.append(ca.SX(1.0))
                    else:
                        row.append(PR[i, j] if x in seeds else RB[i, j])
                rows.append(ca.horzcat(*row))
            out = fn(ca.vertcat(*rows))[0]
            for n, (r, sd) in enumerate(pairs):
                i, j = R.get(r), Cc.get(sd)
                if i is None or j is None:
                    continue
                P[(i, j)] = ca.fmax(0.0, P0[i, j] + (out[n, 0] - cp[(r, sd)]["q0"]))
    pq = mm._proc_nq_params()
    if pq:
        from capri_mod.market.processing_ad import proc_nq_function
        fn, cells = proc_nq_function(pq, regions, comms, set(mm.CRUSH_CHAINS) | set(mm._PROC_NQ_SKIP),
                                     set(mm.CRUSH_CHAINS))
        if cells:
            p0c = np.array([P0[i, j] for i, j in cells], dtype=float)
            pc = fn(PR, ca.DM(p0c))
            for k, (i, j) in enumerate(cells):
                if p0c[k] > 0:
                    P[(i, j)] = pc[k]

    # BIOFUEL PROCESSING: the feedstock CES at the groups' first-generation output and the DDGS price
    bp = mm._biofuel_params()
    groups = list(bp.get("groups", [])) if bp else []
    biofX = ca.SX.sym("biofX", len(groups))
    dregs = sorted({g["region"] for g in groups if g["region"] in R})
    ddgs = ca.SX.sym("ddgs", len(dregs))
    if bp:
        bq: Dict[Tuple[str, str], object] = {}
        for n, g in enumerate(groups):
            reg = g["region"]
            i = R.get(reg)
            if i is None:
                continue
            ff = feed_group_function(f"biof_feed_{n}", g)
            rr = ca.vertcat(*[PR[i, Cc[c]] if (c and c in Cc) else ca.SX(1.0) for c in g["comm"]])
            q = ff(rr, biofX[n], ddgs[dregs.index(reg)])[0]
            for k, c in enumerate(g["comm"]):
                if c:
                    bq[(reg, c)] = bq.get((reg, c), 0.0) + q[k]
        for (reg, c), q in bq.items():
            i, j = R.get(reg), Cc.get(c)
            q0 = bp["q0_reg"].get((reg, c), 0.0)
            if i is None or j is None or q0 <= 0 or Bf0[i, j] <= 0:
                continue
            Bf[(i, j)] = Bf0[i, j] * q / q0

    D = (ca.DM(FIX) + _sx_matrix(ca, H, H0) + _sx_matrix(ca, F, F0) + _sx_matrix(ca, P, P0)
         + _sx_matrix(ca, Bf, Bf0))

    # RAW MILK delivered to the dairies (quantities of the supply side)
    milk_regs: List[str] = []
    jm = Cc.get("MILK")
    if jm is not None:
        if mm._dairy_params() and mm.ev.eu_milk_supply_now:
            milk_regs += [r for r in mm.EU if r in R]
        milk_regs += [r for r in mm.SUP if r in R and r in (mm.ev.sup_milk_now or {})]
    n_eu_sup = len(milk_regs)
    if jm is not None:
        milk_regs += [r for r in (mm.ev.world_milk_now or {}) if r in R]
    milk = ca.SX.sym("milk", len(milk_regs))
    for k, r in enumerate(milk_regs):
        i = R[r]
        if k < n_eu_sup:
            D[i, jm] = milk[k]
        else:
            D[i, jm] = D0[i, jm] + (milk[k] - float(mm.par.base_production.at[r, "MILK"]))

    # BIOFUELS' OWN USE: biofDemShare_, biofDem_ and their non-fuel processing at the Armington ratio
    bm = mm._biofuel_market_params()
    endo = bool(bm) and mm.biofuel_endogenous()
    if bm:
        rows = bm.get("rows", {})
        mand = float(1.0 if getattr(mm, "biofuel_mandate", None) is None else mm.biofuel_mandate)
        f_dem, f_proc = demand_function(), proc_function()
        use: Dict[tuple, object] = {}
        proc: Dict[tuple, object] = {}
        if endo:
            for (ms, fuel), d in rows.items():
                reg = d["region"]
                i, j = R.get(reg), Cc.get(fuel)
                ra = PR[i, j] if (i is not None and j is not None) else ca.SX(1.0)
                u = float(d["biof_kt"])
                if float(d["dem_slope"]) != 0.0 and float(d["fossil_cpri"]) > 0:
                    quts = float(d["quts"]) * (mand if d["mandate_region"] else 1.0)
                    u = f_dem(ra, float(d["cpri"]), float(d["arm1p"]), quts,
                              *(float(d[k]) for k in ("dem_max", "dem_slope", "fossil_cpri", "dem_turn", "hcon_kt",
                                                      "oil_eq_fossil", "oil_eq")))
                use[(reg, fuel)] = use.get((reg, fuel), 0.0) + u
                pc = float(d["proc_kt"])
                if pc > 0 and float(d["proc_hess"]) != 0.0 and float(d["inpe"]) > 0:
                    pc = f_proc(ra, pc, float(d["proc_hess"]), float(d["arm1p"]), float(d["inpe"]))
                proc[(reg, fuel)] = proc.get((reg, fuel), 0.0) + pc
        for (reg, fuel), u0 in bm["use0"].items():
            i, j = R.get(reg), Cc.get(fuel)
            if i is None or j is None:
                continue
            if endo:
                p0 = float(bm["proc0"].get((reg, fuel), 0.0))
                D[i, j] = ca.fmax(0.0, D0[i, j] - u0 - p0 + use.get((reg, fuel), u0) + proc.get((reg, fuel), p0))
            else:
                D[i, j] = D0[i, j]
    D = ca.fmax(D, 0.0)
    f = ca.Function("use", [PR, RB, fede, milk, biofX, ddgs], [D], ["PR", "RB", "fede", "milk", "biofX", "ddgs"],
                    ["D"])
    return f, {"rms": rms, "milk_regs": milk_regs, "n_eu_sup": n_eu_sup, "groups": groups, "ddgs_regs": dregs}


def use_inputs(mm, layout: dict) -> list:
    """The function's inputs at the module's latest evaluation (its ev state): PR, the producer ratios r, FEDE, the
    raw milk delivered, the biofuel groups' output, the DDGS ratios."""
    PR = np.asarray(mm._welfare_eval["PR"], float)
    rb = mm.ev.bilat_ratio_now.reindex(index=list(mm.regions), columns=list(mm.commodities)).fillna(1.0)
    fe = mm.ev.fede_now or {}
    fede = np.array([float(fe.get(s, 1.0)) for s in layout["rms"]])
    ms_now, sup_now, wm = mm.ev.eu_milk_supply_now, mm.ev.sup_milk_now or {}, mm.ev.world_milk_now or {}
    milk = []
    for k, r in enumerate(layout["milk_regs"]):
        if k < layout["n_eu_sup"]:
            if r in mm.EU:
                milk.append(float(ms_now.get(r, 0.0) if isinstance(ms_now, dict) else ms_now))
            else:
                milk.append(float(sup_now[r]))
        else:
            milk.append(float(wm[r]))
    st = mm.ev.biof_state or {}
    biofX = np.array([float(mm._biofuel_x(g)) for g in layout["groups"]])
    ddgs = np.array([float((st.get("ddgs_ratio") or {}).get(r, 1.0)) for r in layout["ddgs_regs"]])
    return [PR, rb.to_numpy(dtype=float), fede, np.array(milk), biofX, ddgs]

"""G3.2c/e: the market's supply side as one CasADi function of the system's unknowns, with the equations of the blocks
the default solve solves inside each evaluation.

`MarketModule.supply_response` (bilateral market, the supply models' output given) composes the supply per region and
commodity from the blocks' CasADi functions called on numbers, and solves three blocks on the way: the young-animal
markets and the member states' raw milk in alternating rounds (`_milk_and_yani_clear_all`), the other regions' dairy
blocks (`_dairy_solve`). Here their prices are unknowns and their equations outputs:

    (S, res_yani, res_dairy_eu, res_dairy_w, biofX) = supply(PA, RR, ry, uE, uW, fede, dr)

  PA    [nR x nC]  the Armington price ratios (the crushers' seed price, the biofuel feedstocks)
  RR    [nR x nC]  the producer price ratios r (the region_ratio of supply_response)
  ry    [n_y]      the young-animal prices of the EU market regions (their goods in seen.yani_state order)
  uE    [3 n_ms]   each member state's dairy block unknowns (fat, protein, raw milk price ratio - 1)
  uW    [3 n_w]    the other regions' dairy blocks' unknowns
  fede  [n_rms]    the non-EU behavioural regions' feed energy price ratios (use_ad's order)
  dr    [n_dr]     the non-EU land markets' free rents' change (EUR/ha; the land block's order)

  S            [nR x nC] the supply, without the EU's residual feeds (MaprFeed_, set after the use side:
               `_apply_feed_byproduct_supply`; an equation of the assembled system)
  res_yani     yaniMarket_ of each EU market region (kt)
  res_dairy_eu FatsProtBal_ and DairyNQ_ = ProdNQ_ MILK of each member state (the dairy block's residuals)
  res_dairy_w  the same for the other regions' dairy blocks
  biofX        each biofuel feedstock group's first-generation output (use_ad's input)

The supply models' latest output and the calibration state (seen prices, Hessians) are constants, as CAPRI's parameters
within a market solve. Norway (the non-EU market regions with supply models, K56) as the default solve composes it,
with one difference: its rows respond to its dairy block's current milk price (the default solve: the previous
evaluation's, DEP-29); its raw milk row takes the same young-animal prices as its other rows (CAPRI's one set; the
default solve too since 14 November 2026). Not covered: the member states' raw milk price floor (MILK_PRICE_FLOOR, a bound in G3); the young-animal prices' bounds (st["bounds"], the
same). `supply_inputs(mm, layout)` reads the unknowns at the module's latest evaluation; at a solve's equilibrium the
outputs equal its supply and the residuals vanish up to the default solve's own tolerances
(tools/check/g3_supply_system.py).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np


def supply_system(mm, exogenous_supply):
    """(Function, layout) of the supply side at the module's current calibration state and the supply models' output
    exogenous_supply (one row per country, as MarketModule.solve takes it)."""
    import casadi as ca
    from capri_mod.market.supply_ad import anticipation_function, yani_function

    if exogenous_supply is None:
        raise NotImplementedError("supply_system: the supply models' output is needed (the market without them is "
                                  "the elasticity form)")
    exo_eu, exo_sup = mm._split_supply(exogenous_supply)
    base = mm.par.base_production
    regions = list(base.index)
    comms = list(mm.commodities)
    cols = [c for c in comms if c in base.columns]
    R = {r: i for i, r in enumerate(regions)}
    ci = {c: j for j, c in enumerate(cols)}
    nR, nC = len(regions), len(cols)
    PA = ca.SX.sym("PA", nR, nC)
    RR = ca.SX.sym("RR", nR, nC)
    rr = ca.fmax(RR, 1e-6)

    # the supply models' output on the EU rows (supply_response before the price response)
    S0 = base.reindex(columns=cols).to_numpy(dtype=float).copy()
    sup_cols: Dict[str, set] = {}
    for reg, ser in exo_sup.items():
        if reg not in R:
            continue
        for comm, v in ser.items():
            if comm in ci and float(v) > 1e-6:
                S0[R[reg], ci[comm]] = float(v)
                sup_cols.setdefault(reg, set()).add(comm)
    ex = mm.eu_rows(exo_eu)
    xr = mm._eu_excluded_rows()
    for c in exo_eu.columns:
        if c not in ci:
            continue
        for reg in mm.EU:
            v = float(ex.at[reg, c]) if reg in ex.index else 0.0
            x = float(xr.at[reg, c]) if (xr is not None and reg in xr.index and c in xr.columns) else 0.0
            if reg in R and (v > 1e-6 or (xr is not None and v + x > 1e-6)):
                S0[R[reg], ci[c]] = v
    s_exo_eu = {reg: S0[R[reg]].copy() for reg in mm.EU if reg in R}
    s_exo_sup = {reg: S0[R[reg]].copy() for reg in sup_cols}

    # the own-price anticipation (supply models' rows against the prices they saw; ProdNQ_ outside the EU: 0)
    real = getattr(mm, "_real_supply_elas", None)
    if real is None:
        _se = mm._inp().csv("supply_elas_eu.csv")
        real = {str(c): float(v) for c, v in zip(_se.commodity, _se.elasticity)}
    import pandas as pd
    el = pd.Series({c: (float(real[c]) if c in real else 0.0) for c in comms})
    EV = mm._region_supply_elas(regions, cols, el)
    if mm.noneu_supply_nq:
        EV = EV.copy()
        for i_, r_ in enumerate(regions):
            if r_ in mm.EU:
                continue
            sc_ = sup_cols.get(r_, set())
            for j_, c_ in enumerate(cols):
                if c_ not in sc_:
                    EV[i_, j_] = 0.0
    ev = el.reindex(cols).to_numpy(dtype=float)
    E_, SV_ = EV.copy(), np.ones((nR, nC))
    sv_eu = {}
    seen_all = mm.seen.eu_price_seen
    for reg in mm.EU:
        if reg not in R:
            continue
        seen = (seen_all.loc[reg] if isinstance(seen_all, pd.DataFrame) and reg in seen_all.index
                else (seen_all if isinstance(seen_all, pd.Series) else None))
        sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
              if seen is not None else np.ones(nC))
        for j, c in enumerate(cols):
            if c in mm.EU_MARKET_SUPPLY:
                sv[j] = 1.0
        E_[R[reg]], SV_[R[reg]] = ev, sv
        sv_eu[reg] = sv
    seen_sup = mm.seen.sup_price_seen or {}
    sv_sup = {}
    for reg, sc_ in sup_cols.items():
        seen = seen_sup.get(reg)
        sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
              if seen is not None else np.ones(nC))
        sv_sup[reg] = sv
        for j, c in enumerate(cols):
            if c in sc_:
                SV_[R[reg], j] = sv[j]
    Smat = anticipation_function(nR, nC)(ca.DM(S0), rr, ca.DM(SV_), ca.DM(E_))
    S = [[Smat[i, j] for j in range(nC)] for i in range(nR)]

    # the EU's products no supply model produces (EU_MARKET_SUPPLY): CAPRI's ProdNQ_ against base
    for rg, terms in mm._eu_market_supply_nq_params().items():
        if rg not in R:
            continue
        fr = mm._nq_rows(("eu", rg), terms, lambda t_: {x: {y: h for (x_, y), h in t_.items() if x_ == x}
                                                         for x in mm.EU_MARKET_SUPPLY}, cols, None)
        if fr is None:
            continue
        f, rows, _ = fr
        r_ = rr[R[rg], :].T
        q0 = mm._nq_q0(rg, rows)
        q = f(ca.DM(q0), r_, r_[ci["MILK"]] if "MILK" in ci else 1.0, ca.DM.zeros(0), ca.DM.zeros(len(rows)))[0]
        for k, x in enumerate(rows):
            if x in ci and q0[k] > 0:
                S[R[rg]][ci[x]] = q[k]

    # the EU blocks' ProdNQ_ with the measured Hessian, the young-animal markets and the member states' raw milk
    hs_blocks = dict(((mm.par.supply_hessian or {}).get("blocks") or {}))
    items = {}
    for reg, H in hs_blocks.items():
        if H is None or not len(H) or reg not in s_exo_eu or reg not in sv_eu:
            continue
        ex_cols = set(exogenous_supply.columns)
        xs = [x for x in H.index if x in ci and x in ex_cols]
        if not xs:
            continue
        xj = [ci[x] for x in xs]
        Hm = H.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float)
        dsv = ca.DM(sv_eu[reg])
        dP = rr[R[reg], :].T - dsv
        for c in mm.NQ_PRICE_AS_SEEN:
            if c in ci:
                dP[ci[c]] = 0.0
        items[reg] = dict(H=H, xs=xs, xj=xj, Hm=Hm, s0=s_exo_eu[reg][xj], dP=dP,
                          mt=mm._milk_terms(cols, xs, H, reg))
    milk_path = bool(items) and all(it["mt"] is not None for it in items.values())

    # the young-animal prices (unknowns) and each region's market
    ylay: List[tuple] = []
    for reg, it in items.items():
        st = (mm.seen.yani_state or {}).get(reg)
        if not st:
            continue
        goods = [g for g in st["goods"] if ("YANI:" + g) in it["H"].index and ("YANI:" + g) in it["H"].columns]
        if goods:
            ylay.append((reg, goods))
    hs_sup = {reg: Hs for reg, Hs in (((mm.par.supply_hessian or {}).get("sup") or {}).items())
              if reg in sup_cols and Hs is not None and len(Hs)
              and [x for x in Hs.index if x in ci and x in sup_cols[reg]]}
    for reg, Hs in hs_sup.items():
        st = (mm.seen.yani_state or {}).get(reg)
        goods = ([g for g in st["goods"] if ("YANI:" + g) in Hs.index and ("YANI:" + g) in Hs.columns]
                 if st else [])
        if goods:
            ylay.append((reg, goods))
    ny = sum(len(g) for _, g in ylay)
    ry = ca.SX.sym("ry", ny)
    yoff, o = {}, 0
    for reg, goods in ylay:
        yoff[reg] = (o, goods)
        o += len(goods)

    # the member states' dairy unknowns
    dp = mm._dairy_params() or {}
    ms_list = list((dp.get("ms") or {}))
    uE = ca.SX.sym("uE", 3 * len(ms_list))

    def zM_ms(m):
        return uE[3 * ms_list.index(m) + 2]

    res_y = []
    extra = {}
    for reg, it in items.items():
        H, xs, dP, mt = it["H"], it["xs"], it["dP"], it["mt"]
        eff = ca.SX.zeros(len(xs))
        dL = None
        if milk_path and mt is not None and len(mt["ms"]):
            Ls = np.array([float(mm.seen.milk_seen_ms.get(m, 1.0)) for m in mt["ms"]])
            dL = ca.vertcat(*[zM_ms(m) + 1.0 - Ls[k] for k, m in enumerate(mt["ms"])])
            it["dL"], it["Ls"] = dL, Ls
        if reg in yoff:
            o_, goods = yoff[reg]
            st = mm.seen.yani_state[reg]
            yi = ["YANI:" + g for g in goods]
            fy = yani_function(f"yani_{reg}", H.reindex(index=yi, columns=cols).fillna(0.0).to_numpy(dtype=float),
                               H.reindex(index=yi, columns=yi).fillna(0.0).to_numpy(dtype=float),
                               H.reindex(index=list(xs), columns=yi).fillna(0.0).to_numpy(dtype=float))
            r_seen = np.array([float(st["seen"].get(g, 1.0)) for g in goods])
            net = np.array([float(st["net"].get(g, 0.0)) for g in goods])
            ref = np.array([float(st["ref"].get(g, 0.0)) for g in goods])
            dy = ry[o_:o_ + len(goods)] - ca.DM(r_seen)
            ey = ca.SX.zeros(len(goods))
            if dL is not None and len(mt["goods"]):
                eyv = ca.mtimes(ca.DM(mt["colY"]), dL)
                ey = ca.vertcat(*[eyv[mt["goods"].index(g)] if g in mt["goods"] else ca.SX(0.0) for g in goods])
            out = fy(dy, ca.DM(net), ca.DM(ref), dP, ey, dy)
            res_y.append(out[0])
            eff = out[2]
            it["dY"] = (goods, dy)
        if dL is not None:
            eff = eff + ca.mtimes(ca.DM(mt["col"]), dL)
        extra[reg] = eff

    # the EU blocks' rows
    for reg, it in items.items():
        q = mm._hess_fn(f"hess_{reg}", it["Hm"])(ca.DM(it["s0"]), it["dP"], extra[reg])[0]
        for k, j in enumerate(it["xj"]):
            if it["s0"][k] > 1e-6:
                S[R[reg]][j] = q[k]

    # NORWAY (the non-EU market regions with supply models, K56): its measured Hessian's rows against the prices its
    # models saw, its young-animal market, its raw milk inside its dairy block (_sup_milk_terms; the milk price change
    # its rows respond to is its dairy block's current one here, the previous evaluation's in the default solve)
    wpar = mm._dairy_world_params() or {}
    wl = [r for r in wpar if r in R]
    uW = ca.SX.sym("uW", 3 * len(wl))
    sup_milk = {}
    for reg, Hs in hs_sup.items():
        i_ = R[reg]
        xs = [x for x in Hs.index if x in ci and x in sup_cols[reg]]
        xj = [ci[x] for x in xs]
        Hm = Hs.reindex(index=xs, columns=cols).fillna(0.0).to_numpy(dtype=float)
        s0 = s_exo_sup[reg][xj]
        dP = rr[i_, :].T - ca.DM(sv_sup[reg])
        for c in mm.NQ_PRICE_AS_SEEN:
            if c in ci:
                dP[ci[c]] = 0.0
        mk = None
        if mm.sup_milk_in_market and "MILK" in xs and "MILK" in ci and "MILK" in Hs.columns:
            k = float(Hs.at["MILK", "MILK"])
            if k > 0:
                L = float(sv_sup[reg][ci["MILK"]])
                mk = {"k": k, "L": L, "dL": (uW[3 * wl.index(reg) + 2] + 1.0 - L) if reg in wl else ca.SX(0.0)}
        yfn = None
        if reg in yoff:
            o_, goods = yoff[reg]
            st = mm.seen.yani_state[reg]
            yi = ["YANI:" + g for g in goods]
            H_YP = Hs.reindex(index=yi, columns=cols).fillna(0.0).to_numpy(dtype=float)
            H_YY = Hs.reindex(index=yi, columns=yi).fillna(0.0).to_numpy(dtype=float)
            H_PY = Hs.reindex(index=list(xs), columns=yi).fillna(0.0).to_numpy(dtype=float)
            r_seen = np.array([float(st["seen"].get(g, 1.0)) for g in goods])
            net = np.array([float(st["net"].get(g, 0.0)) for g in goods])
            ref = np.array([float(st["ref"].get(g, 0.0)) for g in goods])
            yfn = (H_YP, H_YY, H_PY, net, ref, ry[o_:o_ + len(goods)] - ca.DM(r_seen))

        def rows_at(dPv):
            """The rows at the price change dPv with the young-animal prices ry, and their markets' residual."""
            if yfn is None:
                return s0 + ca.mtimes(ca.DM(Hm), dPv), None
            H_YP, H_YY, H_PY, net, ref, dy = yfn
            res = ca.DM(net) + ca.mtimes(ca.DM(H_YP), dPv) + ca.mtimes(ca.DM(H_YY), dy) - ca.DM(ref)
            return s0 + ca.mtimes(ca.DM(Hm), dPv) + ca.mtimes(ca.DM(H_PY), dy), res
        if mk is not None:
            iM_ = xs.index("MILK")
            dP1 = ca.SX(dP)
            dP1[ci["MILK"]] = mk["dL"]
            qraw, res = rows_at(dP1)
            # the MILK row without its own milk price term, at the same young-animal prices (one set, as CAPRI)
            qraw0, _ = rows_at(dP)
            cross = qraw0[iM_] - s0[iM_]
            q = ca.fmax(qraw, 0.0)
            q[iM_] = ca.fmax(qraw0[iM_], 0.0)
            sup_milk[reg] = dict(mk, cross=cross)
        else:
            qraw, res = rows_at(dP)
            q = ca.fmax(qraw, 0.0)
        if res is not None:
            res_y.append(res)
        for k_, j in enumerate(xj):
            if s0[k_] > 1e-6:
                S[i_][j] = q[k_]

    # K83: the EU's units outside a run on a subset, moved by their member states' ProdNQ_
    xb = mm.seen.eu_excluded_base
    if xb is not None:
        from capri_mod.data.definitions import capri_ms
        terms, q0m = mm._eu_ms_supply_nq()
        skip = mm._excluded_skip()
        add: Dict[tuple, object] = {}
        for cc, row in xb.iterrows():
            ms = capri_ms(cc)
            reg = mm.eu_region_of_ms(ms)
            if reg is None or reg not in R:
                continue
            r_ = rr[R[reg], :]
            t_ms, q_ms = terms.get(ms, {}), q0m.get(ms, {})
            for x, b in row.items():
                b = float(b)
                if not b > 0 or x not in ci or x in skip:
                    continue
                qc = float(q_ms.get(x, 0.0))
                rel = 0.0
                if qc > 0:
                    rel = sum((h * (r_[ci[y]] - 1.0) for (x_, y), h in t_ms.items() if x_ == x and y in ci),
                              ca.SX(0.0)) / qc
                add[(reg, x)] = add.get((reg, x), 0.0) + ca.fmax(b * (1.0 + rel), 0.0)
        for (reg, x), v in add.items():
            S[R[reg]][ci[x]] = S[R[reg]][ci[x]] + v

    # CRUSHING: oil and cake output (ProcO_, procYield_) at the seeds' Armington and the oil's and cake's producer
    # ratios
    cp = mm._crush_params()
    if cp:
        from capri_mod.market.processing_ad import crush_columns, crush_function
        pq = mm._proc_nq_params() or {}
        fn, cregs, pairs, _ = crush_function(cp, pq.get("seeds", {}), pq.get("Hrms", {}), mm.CRUSH_CHAINS)
        if pairs:
            d0 = mm._dom0().reindex(index=regions, columns=cols).to_numpy(dtype=float)
            seeds = set(mm.CRUSH_CHAINS)
            used = {r for (r, s_) in pairs if pq.get("seeds", {}).get((r, s_))}
            rows_ = []
            for r in cregs:
                i = R.get(r)
                rows_.append(ca.horzcat(*[
                    (PA[i, ci[x]] if x in seeds else RR[i, ci[x]])
                    if (r in used and i is not None and x in ci and d0[i, ci[x]] > 0) else ca.SX(1.0)
                    for x in crush_columns(mm.CRUSH_CHAINS)]))
            out = fn(ca.vertcat(*rows_))[0]
            done = set()
            for n, (r, s) in enumerate(pairs):
                o_, c_ = mm.CRUSH_CHAINS[s]
                if r not in R:
                    continue
                for prod, k in ((o_, 1), (c_, 2)):
                    if prod in ci:
                        if (r, prod) not in done:
                            S[R[r]][ci[prod]] = ca.SX(0.0)
                            done.add((r, prod))
                        S[R[r]][ci[prod]] = S[R[r]][ci[prod]] + out[n, k]

    # the EU DAIRY blocks: each member state at its region's producer ratios, raw milk delivered responding to its price
    res_E = []
    if dp and all(r in R for r in mm.EU):
        fnE = mm._dairy_fn  # per member state's parameters
        _m0 = mm.par.dairy_S0_ms or {}
        _m = mm._milk_by_ms(mm._with_eu_excluded(exogenous_supply))
        mr_all = {m_: (_m[m_] / q_ if (q_ > 0 and m_ in _m) else 1.0) for m_, q_ in _m0.items()}
        resp = {}
        if milk_path:
            _xb_ = mm.seen.eu_excluded_base
            _xbm = mm._milk_by_ms(_xb_) if _xb_ is not None else {}
            xr_milk = _excluded_milk_resp_sx(mm, ca, cols, ci, rr, R, _m0)
            for reg, it in items.items():
                mt = it["mt"]
                q0 = np.array([float(_m0.get(m, 0.0)) for m in mt["ms"]])
                mr0 = np.array([(_m.get(m, 0.0) / q0[i]) if q0[i] > 0 else 1.0 for i, m in enumerate(mt["ms"])])
                a = ca.mtimes(ca.DM(mt["row"]), it["dP"])
                if len(mt["goods"]) and "dY" in it:
                    goods, dy = it["dY"]
                    dY = ca.vertcat(*[dy[goods.index(g)] if g in goods else ca.SX(0.0) for g in mt["goods"]])
                    a = a + ca.mtimes(ca.DM(mt["rowY"]), dY)
                for i, m in enumerate(mt["ms"]):
                    resp[m] = [mr0[i] + (a[i] / q0[i] if q0[i] > 0 else 0.0), (mt["h"][i] / q0[i] if q0[i] > 0
                                                                              else 0.0), it["Ls"][i], reg, mr0[i],
                               q0[i]]
            for m, (c1, k1) in xr_milk.items():
                xs_ = _xbm.get(m, 0.0) / float(_m0[m]) if float(_m0.get(m, 0.0)) > 0 else 0.0
                if m in resp:
                    resp[m][0] = resp[m][0] - xs_ + c1 + k1 * (resp[m][2] - 1.0)
                    resp[m][1] = resp[m][1] + k1
                else:
                    resp[m] = [c1, k1, 1.0, None, None, None]
        zts = {}
        for rg in mm.EU:
            z_ = [ca.SX(0.0)] * (len(dp["items"]) + 2)
            for k, c in mm.DAIRY_TRADED.items():
                if k in dp["ix"]:
                    z_[dp["ix"][k]] = (RR[R[rg], ci[c]] if c in ci else ca.SX(1.0)) - 1.0
            zts[rg] = ca.vertcat(*z_)
        msupp = {rg: {c: ca.SX(0.0) for c in mm.DAIRY_TRADED.values()} for rg in mm.EU}
        rgp = dp.get("reg") or {}
        milk_dq = {rg: ca.SX(0.0) for rg in mm.EU}
        in_items = {m for it in items.values() for m in (it["mt"]["ms"] if it["mt"] else [])}
        for ms, prm in dp["ms"].items():
            rg = mm.eu_region_of_ms(ms) or mm.EU[0]
            Q0M = float(prm["Q0"][prm["iM"]])
            u = uE[3 * ms_list.index(ms): 3 * ms_list.index(ms) + 3]
            f = fnE(prm)
            if ms in resp:
                mb, k_, Ls_ = resp[ms][0], resp[ms][1], resp[ms][2]
                args = (Q0M * k_, Q0M * (mb - 1.0) + Q0M * k_ * (1.0 - Ls_), 0.0, 0.0)
                delivered = mb + k_ * (1.0 + u[2] - Ls_)
            else:
                mr = float(mr_all.get(ms, 1.0))
                args = (0.0, Q0M * (mr - 1.0), 0.0, 0.0)
                delivered = None
            res, _, z, q, dproc = f(zts[rg], u, *args)
            res_E.append(res)
            for k, c in mm.DAIRY_TRADED.items():
                if k in dp["ix"]:
                    msupp[rg][c] = msupp[rg][c] + q[dp["ix"][k]] - dproc[dp["ix"][k]]
            if delivered is not None:
                if ms in in_items:
                    r_ = resp[ms]
                    milk_dq[r_[3]] = milk_dq[r_[3]] + (delivered - r_[4]) * r_[5]
                elif float(_m0.get(ms, 0.0)) > 0:
                    rg_ = mm.eu_region_of_ms(ms)
                    if rg_ in milk_dq:
                        milk_dq[rg_] = milk_dq[rg_] + (delivered - float(mr_all.get(ms, 1.0))) * float(_m0[ms])
        # raw milk delivered per EU market region: the supply models' (with the K83 units') plus the response
        Sr = ({r: float(v) for r, v in mm.eu_rows(exo_eu[["MILK"]])["MILK"].items()} if "MILK" in exo_eu.columns
              else {r: 0.0 for r in mm.EU})
        if xr is not None and "MILK" in xr.columns:
            Sr = {r_: float(v_) + (float(xr.at[r_, "MILK"]) if r_ in xr.index else 0.0) for r_, v_ in Sr.items()}
        for rg in mm.EU:
            if "MILK" in ci:
                S[R[rg]][ci["MILK"]] = Sr.get(rg, 0.0) + (milk_dq[rg] if milk_path else 0.0)
            for c in mm.DAIRY_TRADED.values():
                if c in ci and rg in rgp:
                    k = [k_ for k_, c_ in mm.DAIRY_TRADED.items() if c_ == c][0]
                    S[R[rg]][ci[c]] = ca.fmax(0.0, msupp[rg][c] - float(rgp[rg]["proc0"][dp["ix"][k]]))

    # the other regions' DAIRY blocks: raw milk from CAPRI's supply function inside the block
    res_W = []
    nfp = mm._noneu_feed_params() if mm.noneu_feed_nq else {"rms": {}}
    frms = [s for s, d in nfp["rms"].items() if d.get("tr") in R]
    fede = ca.SX.sym("fede", len(frms))

    def fede_of(s):
        return fede[frms.index(s)] if s in frms else ca.SX(1.0)
    LP = mm._noneu_land_params()
    lrms = list(LP)
    dr = ca.SX.sym("dr", sum(len(LP[s]["free"]) for s in lrms))
    loff, o = {}, 0
    for s in lrms:
        loff[s] = o
        o += len(LP[s]["free"])

    def land_shift(reg, by_rms=False):
        out: dict = {}
        for s, d in LP.items():
            if d["tr"] != reg:
                continue
            fl = [d["lu"][i] for i in d["free"]]
            drs = {u: dr[loff[s] + k] for k, u in enumerate(fl)}
            for x, t in d["prod"].items():
                v = sum((h * drs[u] for u, h in t.items() if u in drs), ca.SX(0.0))
                if by_rms:
                    out.setdefault(x, {})[s] = out.get(x, {}).get(s, 0.0) + v
                else:
                    out[x] = out.get(x, 0.0) + v
        return out
    nqp = mm._noneu_nq_params()
    milkW = {}
    for n, r in enumerate(wl):
        prm = wpar[r]
        i = R[r]
        if prm["dom"]:
            raise NotImplementedError("supply_system: dairy blocks with DAIRY_DOMESTIC")
        z_ = [ca.SX(0.0)] * (len(prm["items"]) + 2)
        for k, c in mm.DAIRY_TRADED.items():
            if k in prm["ix"]:
                z_[prm["ix"][k]] = (RR[i, ci[c]] if c in ci else ca.SX(1.0)) - 1.0
        u = uW[3 * n: 3 * n + 3]
        iM = prm["iM"]
        Q0M = float(prm["Q0"][iM])
        m0_ = (mm.par.sup_milk0 or {}).get(r)
        if r in exo_sup and "MILK" in exo_sup[r].index and m0_:
            # Norway: the milk its supply models deliver, moved by its milk price and the other prices inside its
            # block (_sup_milk_delivered), or fixed at the models' (no milk terms)
            m_now = float(exo_sup[r]["MILK"])
            t = sup_milk.get(r)
            if t is not None:
                SM_ = t["k"] * Q0M / m0_
                shift = Q0M * (m_now / m0_ - 1.0) + Q0M / m0_ * (t["k"] * (1.0 - t["L"]) + t["cross"])
                res, _, z, q, dproc = mm._dairy_fn(prm)(ca.vertcat(*z_), u, SM_, shift, 0.0, 0.0)
                milk_q = m0_ * (1.0 + (SM_ * z[iM] + shift) / Q0M)
            else:
                res, _, z, q, dproc = mm._dairy_fn(prm)(ca.vertcat(*z_), u, 0.0, Q0M * (m_now / m0_ - 1.0), 0.0,
                                                         0.0)
                milk_q = ca.SX(m_now)
            res_W.append(res)
            milkW[r] = 1.0 + u[2]
            if "MILK" in ci:
                S[i][ci["MILK"]] = milk_q
            for k, c in mm.DAIRY_TRADED.items():
                ik = prm["ix"][k]
                q0 = float(prm["Q0"][ik] - prm["proc0"][ik])
                if c in ci and q0 > 1e-9:
                    S[i][ci[c]] = ca.fmax(0.0, float(base.at[r, c]) * (q[ik] - prm["proc0"][ik] - dproc[ik]) / q0)
            continue
        shift = ca.SX(0.0)
        if mm.noneu_supply_nq:
            d_ = nqp.get(r) or {}
            for s, t in (d_.get("milk") or {}).items():
                shift = shift + sum((h * (rr[i, ci[y]] - 1.0) for y, h in t.items() if y in ci), ca.SX(0.0))
            for s, h in (d_.get("milk_fede") or {}).items():
                shift = shift + h * (fede_of(s) - 1.0)
            for s, v in land_shift(r, by_rms=True).get("MILK", {}).items():
                shift = shift + v
        res, _, z, q, dproc = mm._dairy_fn(prm)(ca.vertcat(*z_), u, float(prm["SM"]), shift, 0.0, 0.0)
        res_W.append(res)
        milkW[r] = 1.0 + u[2]
        if "MILK" in ci:
            S[i][ci["MILK"]] = float(base.at[r, "MILK"]) * (1.0 + (float(prm["SM"]) * z[iM] + shift)
                                                           / float(prm["Q0"][iM]))
        for k, c in mm.DAIRY_TRADED.items():
            ik = prm["ix"][k]
            q0 = float(prm["Q0"][ik] - prm["proc0"][ik])
            if c in ci and q0 > 1e-9:
                S[i][ci[c]] = ca.fmax(0.0, float(base.at[r, c]) * (q[ik] - prm["proc0"][ik] - dproc[ik]) / q0)

    # the non-EU regions' ProdNQ_ (prices, their dairy block's raw milk price, FEDE, the land rents)
    if mm.noneu_supply_nq:
        for reg, d in nqp.items():
            if reg not in R:
                continue
            fr = mm._nq_rows(("noneu", reg), d["rows"], None, cols, d.get("fede") or {})
            if fr is None:
                continue
            f, rows, rms_f = fr
            q0 = mm._nq_q0(reg, rows)
            ls = land_shift(reg)
            q = f(ca.DM(q0), rr[R[reg], :].T, milkW.get(reg, ca.SX(1.0)),
                  ca.vertcat(*[fede_of(s) for s in rms_f]) if rms_f else ca.DM.zeros(0),
                  ca.vertcat(*[ls.get(x, ca.SX(0.0)) for x in rows]))[0]
            skip = sup_cols.get(reg, set())
            for k, x in enumerate(rows):
                if x in ci and q0[k] > 0 and x not in skip:
                    S[R[reg]][ci[x]] = q[k]
    if "MILK" in ci:
        for r in regions:
            if r not in mm.EU and r not in mm.SUP and r not in milkW:
                S[R[r]][ci["MILK"]] = ca.SX(float(base.at[r, "MILK"]))

    # BIOFUELS: SupplyBiof_ at the processing margin, MaprBiof_, DDGS from the ethanol plants' cereal feedstocks
    bm, bp = mm._biofuel_market_params(), mm._biofuel_params()
    groups = list((bp or {}).get("groups", []))
    biofX = []
    if bm or bp:
        from capri_mod.market.biofuel_ad import feed_group_function, supply_function
        d0 = mm._dom0().reindex(index=regions, columns=cols).to_numpy(dtype=float)
        endo = mm.biofuel_endogenous()
        scale = mm.biofuel_output_scale or {}
        rows_b = bm.get("rows", {}) if bm else {}
        f_sup = supply_function()
        has_dd = "DDGS" in ci

        def aratio(reg, c):
            i = R.get(reg)
            if i is None or not c or c not in ci or not d0[i, ci[c]] > 0:
                return ca.SX(1.0)
            return PA[i, ci[c]]
        X, ddgs = {}, {}
        for n, g in enumerate(groups):
            reg, key = g["region"], (g["ms"], g["fuel"])
            dd = RR[R[reg], ci["DDGS"]] if (has_dd and reg in R) else ca.SX(1.0)
            ff = feed_group_function(f"biof_feed_s{n}", g)
            q1, mub = ff(ca.vertcat(*[aratio(reg, c) if c else ca.SX(1.0) for c in g["comm"]]), 1.0, dd)
            x = ca.SX(g["X0"] * float(scale.get(g["fuel"], 1.0)))
            dd_ = rows_b.get(key)
            if endo and dd_ is not None and float(dd_["pr0"]) > 0:
                rb = RR[R[reg], ci[g["fuel"]]] if (reg in R and g["fuel"] in ci) else ca.SX(1.0)
                x = f_sup(rb, mub, *(float(dd_[k]) for k in ("ppri", "sup_scale", "sup_alfa", "sup_beta",
                                                              "sup_slope", "sup_turn")))
            X[key] = x
            ddgs[reg] = ddgs.get(reg, 0.0) + ca.dot(q1 * x, ca.DM(np.asarray(g["prcby"], float)
                                                                  * np.asarray(g["ddgs"], float)))
        prod: dict = {}
        for (ms, fuel), d in rows_b.items():
            reg = d["region"]
            x = X.get((ms, fuel), ca.SX(float(d["x0_kt"]) * (1.0 if endo else float(scale.get(fuel, 1.0)))))
            prod[(reg, fuel)] = prod.get((reg, fuel), 0.0) + x + float(d["fixed_kt"])
        for (reg, fuel), q0 in ((bm or {}).get("prod0") or {}).items():
            if reg in R and fuel in ci:
                S[R[reg]][ci[fuel]] = prod.get((reg, fuel), ca.SX(q0))
        if has_dd:
            for reg, q in ddgs.items():
                if reg in R:
                    S[R[reg]][ci["DDGS"]] = q
        biofX = [X.get((g["ms"], g["fuel"]), ca.SX(g["X0"])) for g in groups]

    Sx = ca.vertcat(*[ca.horzcat(*row) for row in S])
    outs = [Sx, ca.vertcat(*res_y) if res_y else ca.SX(0, 1), ca.vertcat(*res_E) if res_E else ca.SX(0, 1),
            ca.vertcat(*res_W) if res_W else ca.SX(0, 1), ca.vertcat(*biofX) if biofX else ca.SX(0, 1)]
    f = ca.Function("supply_system", [PA, RR, ry, uE, uW, fede, dr], outs,
                    ["PA", "RR", "ry", "uE", "uW", "fede", "dr"],
                    ["S", "res_yani", "res_dairy_eu", "res_dairy_w", "biofX"])
    return f, {"regions": regions, "cols": cols, "ylay": ylay, "ms": ms_list, "wl": wl, "rms": frms, "lrms": lrms,
               "milk_path": milk_path}


def _excluded_milk_resp_sx(mm, ca, cols, ci, rr, R, m0) -> dict:
    """SupplyMixin._excluded_milk_resp on symbols: {ms: (constant at L = 1, slope)} of the K83 units' raw milk."""
    xb = mm.seen.eu_excluded_base
    if xb is None or "MILK" not in xb.columns:
        return {}
    from capri_mod.data.definitions import capri_ms
    terms, q0 = mm._eu_ms_supply_nq()
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
        reg = mm.eu_region_of_ms(ms)
        t_ms = terms.get(ms, {})
        cross = ca.SX(0.0)
        if reg is not None and reg in R:
            cross = sum((h * (rr[R[reg], ci[y]] - 1.0) for (x_, y), h in t_ms.items()
                         if x_ == "MILK" and y != "MILK" and y in ci), ca.SX(0.0))
        hmm = float(t_ms.get(("MILK", "MILK"), 0.0))
        out[ms] = (x / base * (1.0 + cross / pc), x * hmm / (pc * base))
    return out


def supply_inputs(mm, layout: dict, PA: np.ndarray) -> list:
    """The unknowns at the module's latest evaluation: PA (given: the evaluation's Armington ratios), r, the
    young-animal prices, the member states' and the other regions' dairy block unknowns, FEDE, the rents."""
    regions, cols = layout["regions"], layout["cols"]
    RR = mm.ev.bilat_ratio_now.reindex(index=regions, columns=cols).fillna(1.0).to_numpy(dtype=float)
    ym = mm.ev.yani_market_now or {}
    st = mm.seen.yani_state or {}
    # where the module holds none (before a solve's first evaluation): the default solve's starting points (the
    # young-animal prices the supply models saw, the dairy blocks at their base, FEDE 1, the rents at calibration)
    ry = np.array([float((ym.get(reg) or {}).get(g, st[reg]["seen"].get(g, 1.0))) for reg, goods in layout["ylay"]
                   for g in goods])
    dl = mm.ev.dairy_last or {}
    dp = mm._dairy_params() or {}
    uE = []
    for ms in layout["ms"]:
        prm = dp["ms"][ms]
        z = (dl.get("ms_z") or {}).get(ms)
        uE += ([float(z[prm["iF"]]), float(z[prm["iP"]]), float(z[prm["iM"]])] if z is not None else [0.0] * 3)
    wp = mm._dairy_world_params() or {}
    wl_ = mm.ev.dairy_world_last or {}
    uW = []
    for r in layout["wl"]:
        z = (wl_.get(r) or {}).get("z")
        uW += ([float(z[wp[r]["iF"]]), float(z[wp[r]["iP"]]), float(z[wp[r]["iM"]])] if z is not None else [0.0] * 3)
    fe = mm.ev.fede_now or {}
    fede = np.array([float(fe.get(s, 1.0)) for s in layout["rms"]])
    land = mm.ev.land_now or {}
    LP = mm._noneu_land_params()
    dr = np.concatenate([np.asarray(land.get(s, np.zeros(len(LP[s]["free"]))), float) for s in layout["lrms"]]) \
        if layout["lrms"] else np.zeros(0)
    return [PA, RR, ry, np.array(uE), np.array(uW), fede, dr]

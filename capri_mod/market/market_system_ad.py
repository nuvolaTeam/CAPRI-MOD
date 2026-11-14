"""G3.2e: the market as one system of equations F(x) = 0 in CasADi, assembled from the blocks of G3.2a-d.

Unknowns x (in this order; `layout["x"]` names each slice):
  r      the producer price ratios of every bilateral commodity, per region (sc.regions' order, the commodities in
         par.bilat's order)
  sB/sW  the sigmas of the active tariff-rate quotas (bilateral, then global, per commodity)
  ry     the young-animal prices of the EU market regions and Norway (supply_system_ad)
  uE     the member states' dairy block unknowns (fat, protein, raw milk price ratio - 1)
  uW     the other regions' dairy block unknowns
  fede   the non-EU behavioural regions' feed energy price ratios
  dr     the non-EU land markets' free rents' change (EUR/ha)

Equations F (same order and sizes):
  bal    every bilateral commodity's supply balance per region (SupBalM_; trade_system_ad, supply and use from the
         blocks: supply_system_ad, use_ad, the EU's residual feeds from the use); for a region without production
         of the commodity, CAPRI's PMrk_ instead (BilateralCommodity.pmrk_cells)
  trq    the active quotas' sigmoid equations
  yani   yaniMarket_ of the EU market regions and Norway
  dairyE FatsProtBal_, DairyNQ_ = ProdNQ_ MILK per member state
  dairyW the same per other region with a dairy block
  feed   FeedBal_ per non-EU behavioural region (feed_ad.fedebal_function; the energy fed less the energy needed)
  land   LandSupplyMNL_ = LndSupplyEqualsDemand_ per non-EU land market and free land type (supply_ad.
         land_residual_function)

Square by construction (each unknown block has its equation block of the same size). The pooled commodities (raw
milk: not traded, CAPRI) keep their ratio at the default solve's; their world balance is returned as `pooled` (raw
milk: supply and use are the same quantity in every region, so it is zero identically; checked).

Not covered: a trade scenario's tariff additions (import_prices_ad has none yet); see supply_system_ad and use_ad for
their own limits. `market_x0(mm, layout)` reads x at the module's latest evaluation (a solve's equilibrium after a
solve).
"""
from __future__ import annotations

import numpy as np


def market_system(mm, exogenous_supply, trade_scenario=None, lifted: bool = False, slope=None):
    """(Function x -> (F, pooled, S, D), layout, x, F). lifted: the Armington ratios of the bilateral commodities,
    the supply and the use are unknowns of their own with their defining equations (CAPRI's form: v_arm1Price,
    v_prodQuant, v_arm1Quant), appended to x and F as PA, S, D and PAdef, Sdef, Ddef; the Jacobian is then sparse
    (each region's use depends on its own prices, each Armington ratio on its commodity's prices). slope: a CasADi
    symbol for the quotas' sigmoid slope (CAPRI's p_trqSigmoidSlope) in F, for a continuation on it; None: the
    constant TRQ_SLOPE."""
    import casadi as ca
    from capri_mod.market.supply_system_ad import supply_system
    from capri_mod.market.trade_system_ad import active_quotas, trade_system_function
    from capri_mod.market.use_ad import use_function

    if any(v is not None for v in (mm._tariff_adds(trade_scenario) or {}).values()):
        raise NotImplementedError("market_system: the scenario's tariff additions are not in import_prices_ad yet")
    sf, sl = supply_system(mm, exogenous_supply)
    uf, ul = use_function(mm)
    regions, cols = sl["regions"], sl["cols"]
    if list(mm.commodities) != cols or list(mm.regions) != regions:
        raise NotImplementedError("market_system: supply rows or columns differ from the market's")
    R = {r: i for i, r in enumerate(regions)}
    ci = {c: j for j, c in enumerate(cols)}
    nR, nC = len(regions), len(cols)
    sysd = mm.par.bilat or {}
    r0 = mm.sv.bilat_last_r
    d0 = mm._dom0().reindex(index=regions, columns=cols).to_numpy(dtype=float)
    if not (d0 > 0).all():
        raise NotImplementedError("market_system: a region-commodity without a positive base price (demand_response's "
                                  "fallback price)")

    xs, names = [], []

    def unk(name, n):
        v = ca.SX.sym(name, n)
        xs.append(v)
        names.append((name, n))
        return v
    rB = {c: unk("r_" + c, len(sc.regions)) for c, sc in sysd.items()}
    for c, sc in sysd.items():
        if list(sc.regions) != regions:
            raise NotImplementedError(f"market_system: {c}'s regions differ from the market's")
    sig = {}
    for c, sc in sysd.items():
        bil, glo = active_quotas(sc)
        nb, ng = len(sc.trq_quotas or ()), len(sc.trq_globals or ())
        sB0 = np.asarray(sc.trq_sigma if sc.trq_sigma is not None else np.zeros(nb), float)
        sW0 = np.asarray(sc.trq_sigmaW if sc.trq_sigmaW is not None else np.zeros(ng), float)
        sB, sW = ca.SX(ca.DM(sB0)), ca.SX(ca.DM(sW0))
        if bil:
            u = unk("sB_" + c, len(bil))
            for k, i in enumerate(bil):
                sB[i] = u[k]
        if glo:
            u = unk("sW_" + c, len(glo))
            for k, i in enumerate(glo):
                sW[i] = u[k]
        sig[c] = (sB, sW, bil, glo)
    ry = unk("ry", sum(len(g) for _, g in sl["ylay"]))
    uE = unk("uE", 3 * len(sl["ms"]))
    uW = unk("uW", 3 * len(sl["wl"]))
    fede = unk("fede", len(sl["rms"]))
    dr = unk("dr", sum(len(mm._noneu_land_params()[s]["free"]) for s in sl["lrms"]))
    if ul["rms"] != sl["rms"]:
        raise NotImplementedError("market_system: the use and supply sides' FEDE regions differ")

    # the price matrix: bilateral commodities' unknowns, the pooled ones at the default solve's ratio
    RR = ca.SX(nR, nC)
    for j, c in enumerate(cols):
        if c in rB:
            RR[:, j] = rB[c]
        else:
            RR[:, j] = ca.DM(r0[c].reindex(regions).fillna(1.0).to_numpy(dtype=float))
    # lifted: the Armington ratios, supply and use as unknowns (their values from the substituted functions)
    bcols = [ci[c] for c in sysd]
    if lifted:
        PAu = unk("PA", nR * len(bcols))
        Su = unk("S", nR * nC)
        Du = unk("D", nR * nC)
        Sv = ca.reshape(Su, nR, nC)
        Dv = ca.reshape(Du, nR, nC)

    # the Armington ratios from each commodity's trade block (its prices at r and the quotas' sigmas; supply and use
    # weight an aggregate exporter block's average market price in the border measures, MarketPriceAgg_: the lifted
    # form's unknowns, the substituted form the latest evaluation's, mpagg_SD)
    PA = ca.SX(RR)
    tf0 = {c: trade_system_function(sc, slope_input=slope is not None) for c, sc in sysd.items()}
    tf = {c: ((lambda *a, _f=f: _f(*a, slope)) if slope is not None else f) for c, f in tf0.items()}
    for c, sc in sysd.items():
        sB, sW, _, _ = sig[c]
        if lifted:
            Sw, Dw = Sv[:, ci[c]], Dv[:, ci[c]]
        else:
            sd = sc.mpagg_SD if sc.mpagg_SD is not None else (np.zeros(nR), np.zeros(nR))
            Sw, Dw = ca.DM(sd[0]), ca.DM(sd[1])
        PA[:, ci[c]] = tf[c](rB[c], sB, sW, Sw, Dw)[3]
    PA_fun = PA
    if lifted:
        PA = ca.SX(RR)
        for k, j in enumerate(bcols):
            PA[:, j] = PAu[k * nR:(k + 1) * nR]

    # supply, use, and the residual feeds that follow the use
    S, res_y, res_E, res_W, biofX = sf(PA, RR, ry, uE, uW, fede, dr)
    S_in = Sv if lifted else S
    milk = ca.vertcat(*[S_in[R[r], ci["MILK"]] for r in ul["milk_regs"]]) if ul["milk_regs"] else ca.DM.zeros(0)
    ddgs = (ca.vertcat(*[RR[R[g], ci["DDGS"]] if "DDGS" in ci else 1.0 for g in ul["ddgs_regs"]])
            if ul["ddgs_regs"] else ca.DM.zeros(0))
    D, byp = uf(PA, RR, fede, milk, biofX, ddgs)
    S = ca.SX(S)
    for k, (reg, p) in enumerate(ul["byp_cells"]):
        if p in ci:
            S[R[reg], ci[p]] = byp[k]
    S_sub, D_sub = S, D
    if lifted:
        lift_eqs = [("PAdef", ca.vertcat(*[PA[:, j] - PA_fun[:, j] for j in bcols])),
                    ("Sdef", ca.reshape(Sv - S, nR * nC, 1)), ("Ddef", ca.reshape(Dv - D, nR * nC, 1))]
        S, D = Sv, Dv

    # the trade blocks' equations
    bal, trq = [], []
    for c, sc in sysd.items():
        sB, sW, bil, glo = sig[c]
        out = tf[c](rB[c], sB, sW, S[:, ci[c]], D[:, ci[c]])
        b_ = out[0]
        m = sc.pmrk_cells()
        if m.any():
            # CAPRI's PMrk_ (arm/market_model.gms l. 3074-3080) in place of the empty balance of a region without
            # production: market price = Armington price + the calibrated margin Pd0 - PA0 (BilateralCommodity.
            # pmrk_cells; the default solve sets these prices in _bilateral_eval, with a floor at 1e-3 not written here)
            pa0, pd0 = np.asarray(sc.PA0, float), np.asarray(sc.Pd0, float)
            b_ = ca.vertcat(*[(rB[c][i] - (PA[i, ci[c]] * pa0[i] + pd0[i] - pa0[i]) / pd0[i]) if m[i] else b_[i]
                              for i in range(len(sc.regions))])
        bal.append(b_)
        if bil or glo:
            trq.append(out[1])
    pooled = ca.vertcat(*[ca.sum1(S[:, ci[c]] - D[:, ci[c]]) for c in cols if c not in sysd]) \
        if any(c not in sysd for c in cols) else ca.SX(0, 1)

    # FeedBal_ per behavioural region: the Armington and producer ratios of its trade region, its dairy block's raw
    # milk price, its land rents' change
    nfp = mm._noneu_feed_params()
    LP = mm._noneu_land_params()
    loff, o = {}, 0
    for s in sl["lrms"]:
        loff[s] = o
        o += len(LP[s]["free"])
    wl = sl["wl"]

    def milk_of(tr):
        return (1.0 + uW[3 * wl.index(tr) + 2]) if tr in wl else ca.SX(1.0)

    def rent(s, u):
        if s not in loff:
            return ca.SX(0.0)
        fl = [LP[s]["lu"][i] for i in LP[s]["free"]]
        return dr[loff[s] + fl.index(u)] if u in fl else ca.SX(0.0)
    feed = []
    for k, s in enumerate(sl["rms"]):
        d = nfp["rms"][s]
        tr = d["tr"]
        f, lts = mm._fedebal_fn(s, d, cols)
        lr = ca.vertcat(*[rent(s, u) for u in lts]) if lts else ca.DM.zeros(0)
        feed.append(f(PA[R[tr], :].T, RR[R[tr], :].T, milk_of(tr), lr, fede[k])[1])
    # the land markets
    land = []
    from capri_mod.market.supply_ad import land_residual_function
    for s in sl["lrms"]:
        d = LP[s]
        tr = d["tr"]
        fl = [d["lu"][i] for i in d["free"]]
        base = []
        for i, u in enumerate(fl):
            v = ca.SX(float(d["L0"][i]))
            for y, h in d["rows"][u].items():
                if y == "FEDE":
                    v = v + h * ((fede[sl["rms"].index(s)] if s in sl["rms"] else 1.0) - 1.0)
                elif y == "MILK":
                    v = v + h * (milk_of(tr) - 1.0)
                elif y in ci:
                    v = v + h * (RR[R[tr], ci[y]] - 1.0)
            base.append(v)
        lf = land_residual_function(f"land_{s}", d)
        land.append(lf(dr[loff[s]: loff[s] + len(fl)], ca.vertcat(*base))[0])

    def cat(v):
        return ca.vertcat(*v) if v else ca.SX(0, 1)
    eqs = [("bal", cat(bal)), ("trq", cat(trq)), ("yani", res_y), ("dairyE", res_E), ("dairyW", res_W),
           ("feed", cat(feed)), ("land", cat(land))] + (lift_eqs if lifted else [])
    x = ca.vertcat(*xs)
    F = ca.vertcat(*[e for _, e in eqs])
    fn = ca.Function("market_system", [x] + ([slope] if slope is not None else []), [F, pooled, S, D],
                     ["x"] + (["slope"] if slope is not None else []), ["F", "pooled", "S", "D"])
    lay = dict(sl, x=names, eqs=[(n, int(e.shape[0])) for n, e in eqs], n_x=int(x.shape[0]), n_F=int(F.shape[0]),
               sig=sig, byp_cells=ul["byp_cells"], milk_regs=ul["milk_regs"], lifted=lifted)
    if lifted:
        # the lifted unknowns' values at given base unknowns: the substituted system's PA, S and D
        nb = int(sum(n for nm, n in names if nm not in ("PA", "S", "D")))
        sub = ca.Function("lift", [x], [ca.vertcat(*[PA_fun[:, j] for j in bcols]), ca.reshape(S_sub, nR * nC, 1),
                                        ca.reshape(D_sub, nR * nC, 1)])
        lay["lift"] = (sub, nb, nR * len(bcols), nR * nC)
    return fn, lay, x, F


def market_x0(mm, layout) -> np.ndarray:
    """x at the module's latest evaluation: r (sv.bilat_last_r), the quotas' sigmas, the young-animal prices, the
    dairy blocks' unknowns, FEDE, the rents."""
    from capri_mod.market.supply_system_ad import supply_inputs
    r = mm.sv.bilat_last_r
    out = []
    sysd = mm.par.bilat or {}
    for name, n in layout["x"]:
        if name.startswith("r_"):
            c = name[2:]
            out.append(r[c].reindex(list(sysd[c].regions)).to_numpy(dtype=float))
        elif name.startswith("sB_") or name.startswith("sW_"):
            c = name[3:]
            sc = sysd[c]
            _, _, bil, glo = layout["sig"][c]
            if name.startswith("sB_"):
                out.append(np.asarray(sc.trq_sigma, float)[bil])
            else:
                out.append(np.asarray(sc.trq_sigmaW, float)[glo])
    rest = supply_inputs(mm, layout, np.ones((len(layout["regions"]), len(layout["cols"]))))[2:]
    out += [np.asarray(v, float).ravel() for v in rest]
    xb = np.concatenate(out)
    if not layout.get("lifted"):
        return xb
    sub, nb, npa, ns = layout["lift"]
    # in turn: the Armington ratios from the base unknowns, the supply at those ratios, the use at both
    full = np.concatenate([xb, np.zeros(npa + 2 * ns)])
    full[nb:nb + npa] = np.asarray(sub(full)[0], float).ravel()
    full[nb + npa:nb + npa + ns] = np.asarray(sub(full)[1], float).ravel()
    full[nb + npa + ns:] = np.asarray(sub(full)[2], float).ravel()
    return full

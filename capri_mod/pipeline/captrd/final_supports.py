"""The supports of CAPTRD's first estimation as define_stats_and_supports.gms leaves them (stored as support1, l. 675):
the trend supports adjusted to the biofuel expert supports, overwritten by the expert supports, the crop areas scaled
to UAAR, the trade supports made consistent with the other market balance supports.

  captrd/define_stats_and_supports.gms
    l. 589-598   per ex-ante year outside ExAnteD, adjust_to_biof_supports.gms on "support" (biof_adjust)
    l. 600-605   the support of every position with an Expert = the Expert (overwrite)
    l. 608-610   (STCM's dummy nObs of the young animals: a data flag for the estimation, not ported here)
    l. 618-622   the crop areas' supports (MCACT.LEVL above 1e-12) scaled to close 67% of their gap to UAAR's (mcact_scale)
    l. 627       adjust_trade_supports.gms (adjust_trade; its oils block is off: OILS_ADJ is set empty, l. 48-49)
    l. 631-633   the member states' sugar beet trade (expert_support.sugb_trade)
    l. 646-663   wVarErr of the expert positions from their trust level, and the DOMM components' raised (wvarerr)
    l. 673-675   support1 = support
  captrd/adjust_to_biof_supports.gms (with %use_KWS_supports% off, captrd.gms l. 173)
    l. 20-21     MSest: the member states with a BIOF expert support of a feedstock above 2e-13 in the year
    l. 27-49     P_PrdAdj (the share of a biofuel change met by production), P_LowLim, P_UppLim
    l. 56        "series": the supports before the adjustment
    l. 61-156    the feedstocks' GROF, MAPR, DOMM; the oilseeds' PRCM, GROF, DOMM; the cakes' MAPR; the crops' LEVL
    l. 159-236   sugar: MAPR.SUGA above the quota, BIOF.SUGA's Expert deleted without MAPR.SUGA observations, PRCM,
                 GROF and the shifted positions of SUGB, LOSM.SUGB, DOMM.SUGB, SUGB.LEVL

GAMS's semantics kept: an assignment's right side reads the values from before the statement; a zero deletes; the
parameters P_PrdAdj and P_LowLim keep their values between the years of the loop (only MSest's are assigned). The two files' statements are
named functions quoting their GAMS in capri_mod/pipeline/captrd/equations/adjust_to_biof_supports.py and
adjust_trade_supports.py; biof_adjust and adjust_trade keep the loops, the conditions and the order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from capri_mod.pipeline.captrd.equations import adjust_to_biof_supports as AB
from capri_mod.pipeline.captrd.equations import adjust_trade_supports as AT

K3 = Tuple[str, str, str]
K4 = Tuple[str, str, str, int]

#: adjust_to_biof_supports.gms l. 151, 165: the thresholds of "an increase" and of "an expert support"
TINY = 1.E-13
#: l. 151: the lower limits' yearly decline in the condition of the crops' LEVL
LOW_DECLINE = 0.98
#: define_stats_and_supports.gms l. 618-622: the share of the gap to UAAR closed, and the smallest area scaled
UAAR_SHARE = 0.67
MCACT_MIN = 1.E-12
#: adjust_trade_supports.gms l. 142-143, 150-151: the gross trade above which IMPT and EXPT are rescaled
TRADE_MIN = 1.E-6
#: define_stats_and_supports.gms l. 646-663: wVarErr = (max(0.1, |Expert|) x 0.05 / 3 x 10 / TrustLevl)^2; the DOMM
#: components' x 10, between trust levels 1 and 1e-4
WVAR_FLOOR = 0.1
WVAR_CV = 0.05
WVAR_SIGMAS = 3.0
WVAR_SCALE = 10.0
DOMM_WVAR_FACTOR = 10.0
DOMM_TRUST_HIGH = 1.0
DOMM_TRUST_LOW = 1.E-4


@dataclass
class Sets:
    biostock: List[str]
    biostock_oilp: List[str]
    oseeds: List[str]
    seco: List[str]
    grcu: List[str]
    cropo: List[str]
    prcd: List[Tuple[str, str]]                 # (product, raw product)
    sed_to_oil: List[Tuple[str, str]]
    oil_to_cak: List[Tuple[str, str]]
    bio_prcd: List[Tuple[str, str]]             # (biofuel, feedstock)
    pact_to_y: List[Tuple[str, str]]
    shift_sugb: List[str]
    dompos: List[str]
    mcact: List[str]
    s_colsest: List[str]
    s_rowsest: List[str]
    proc_yields: Dict[str, float] = field(default_factory=dict)


def _put(d: Dict, k, v: float) -> None:
    if v:
        d[k] = v
    else:
        d.pop(k, None)


def biof_adjust(R: Dict[K4, float], expert: Dict[K4, float], *, y: int, ms: Iterable[str], S: Sets,
                basm: Dict[K3, float], bast: Dict[K3, float], bas: Dict[K3, float], nobs: Set[K3],
                quts: Dict[K4, float], prcy: Dict[K4, float], lst_dgagri: int, fst_exante: int, bas_year: int,
                bast_year: int, prd_adj: Dict[Tuple[str, str], float], low_lim: Dict[Tuple[str, str], float],
                upp_lim: Dict[Tuple[str, str], float]) -> None:
    """adjust_to_biof_supports.gms for the ex-ante year y, in place on R (the supports adjusted: "support" here,
    "DGAgri1" in define_eu_supports.gms) and expert (BIOF.SUGA, l. 175). quts: QUTS.SUGA's p_data per (region, col, row,
    year); prcy: the supports holding PRCY.SUGA ("support"). prd_adj, low_lim, upp_lim: P_PrdAdj, P_LowLim, P_UppLim per
    (region, row), kept between calls as GAMS keeps the parameters."""
    bstock = list(S.biostock)
    msest = [r for r in ms if AB.MSest([expert.get((r, "BIOF", b, y), 0.0) for b in bstock])]       # l. 20-21
    if not msest:
        return
    seed_of = {}                                                # PRCD(bioStockOilP, O): the seeds of the oil stocks
    oilp = set(S.biostock_oilp)
    for p, o in S.prcd:
        if p in oilp:
            seed_of.setdefault(o, []).append(p)
    biod = {b for f, b in S.bio_prcd if f == "BIOD"}
    s2o: Dict[str, List[str]] = {}
    for sd, o in S.sed_to_oil:
        s2o.setdefault(sd, []).append(o)
    o2c = list(S.oil_to_cak)
    bm = lambda r, c, w: basm.get((r, c, w), 0.0)          # noqa: E731  P_Result(..., exAnte or %lst_dgagri%, "BASM")
    g = lambda r, c, w: R.get((r, c, w, y), 0.0)           # noqa: E731
    n = y - bas_year                                                    # OrdT(ExAnte) - OrdT("BAS")
    dec = LOW_DECLINE ** n
    for r in msest:                                                                       # l. 27-49
        for b in bstock:
            gr, mp, im = bm(r, "GROF", b), bm(r, "MAPR", b), bm(r, "IMPT", b)
            if gr + mp + im:
                prd_adj[(r, b)] = AB.P_PrdAdj_bioStock(gr, mp, im)
            low_lim[(r, b)] = AB.P_LowLim_bioStock()
        for o in seed_of:
            gr, im = bm(r, "GROF", o), bm(r, "IMPT", o)
            if gr + im:
                prd_adj[(r, o)] = AB.P_PrdAdj_oils(gr, im)
            low_lim[(r, o)] = AB.P_LowLim_oils()
        prd_adj[(r, "SUGB")] = AB.P_PrdAdj_sugar()
        prd_adj[(r, "SUGA")] = AB.P_PrdAdj_sugar()
        low_lim[(r, "SUGB")] = AB.P_LowLim_SUGB()
        for o in S.oseeds:
            upp_lim[(r, o)] = AB.P_UppLim_oseeds()
    cols, rows = set(S.s_colsest), set(S.s_rowsest)
    msset = set(msest)
    series = {k: AB.P_Result_series(v) for k, v in R.items()                               # l. 56
              if k[3] == y and k[0] in msset and k[1] in cols and k[2] in rows}
    sr = lambda r, c, w: series.get((r, c, w, y), 0.0)     # noqa: E731
    pa = lambda r, w: prd_adj.get((r, w), 0.0)             # noqa: E731
    lo = lambda r, w: low_lim.get((r, w), 0.0)             # noqa: E731
    ex = lambda r, c, w: expert.get((r, c, w, y), 0.0)     # noqa: E731

    def stmt(updates):
        for k, v in updates.items():
            _put(R, k, v)
    for c in ("GROF", "MAPR"):                                                             # l. 61-73
        stmt({(r, c, b, y): AB.P_Result_GROF_MAPR_bioStock(g(r, c, b), bm(r, c, b), lo(r, b), n, ex(r, "BIOF", b),
                                                           g(r, "BIOF", b), pa(r, b))
              for r in msest for b in bstock if g(r, c, b)})
    if fst_exante is not None:                                                             # l. 78-81
        stmt({(r, c, b, fst_exante): AB.P_Result_Fst_exAnte(R[(r, c, b, fst_exante)], bm(r, c, b))
              for r in msest for c in ("GROF", "MAPR") for b in bstock if R.get((r, c, b, fst_exante))})
    stmt({(r, "DOMM", b, y): AB.P_Result_DOMM_bioStock(g(r, "DOMM", b), bm(r, "DOMM", b), lo(r, b), ex(r, "BIOF", b),
                                                       g(r, "BIOF", b))
          for r in msest for b in bstock if g(r, "DOMM", b)})                              # l. 86-91
    oils = {sd: [o for o in s2o.get(sd, []) if o in biod] for sd in S.oseeds}               # SED_TO_OIL $ BIO_PRCD(BIOD)
    py = S.proc_yields
    stmt({(r, "PRCM", sd, y): AB.P_Result_PRCM_Oseeds(g(r, "PRCM", sd), bm(r, "PRCM", sd), lo(r, sd), n,
                                                      [(g(r, "MAPR", o), sr(r, "MAPR", o), py[o]) for o in oils[sd]])
          for r in msest for sd in S.oseeds if sum(g(r, "MAPR", o) for o in oils[sd]) and g(r, "PRCM", sd)})  # l. 96-105
    up = {}
    for r in msest:                                                                        # l. 109-122
        for sd in S.oseeds:
            if oils[sd] and g(r, "PRCM", sd) and g(r, "GROF", sd) and bm(r, "GROF", sd):
                up[(r, "GROF", sd, y)] = AB.P_Result_GROF_Oseeds(
                    g(r, "GROF", sd), bast.get((r, "GROF", sd), 0.0), bm(r, "GROF", sd), upp_lim.get((r, sd), 0.0),
                    y - bast_year, n, lo(r, sd), g(r, "PRCM", sd), sr(r, "PRCM", sd), pa(r, sd))
    stmt(up)
    stmt({(r, "DOMM", sd, y): AB.P_Result_DOMM_Oseeds(g(r, "DOMM", sd), g(r, "PRCM", sd), sr(r, "PRCM", sd))
          for r in msest for sd in S.oseeds if oils[sd] and g(r, "DOMM", sd)})            # l. 127-131
    up = {}
    for r in msest:                                                                        # l. 136-144
        for sc in S.seco:
            trip = [(o, sd) for o, c in o2c if c == sc for sd in S.oseeds if o in oils[sd]]
            if not sum(g(r, "PRCM", sd) for o, sd in trip):
                continue
            up[(r, "MAPR", sc, y)] = AB.P_Result_MAPR_SECO(
                g(r, "MAPR", sc), bm(r, "MAPR", sc), [lo(r, o) for o, c in o2c if c == sc], n,
                [(g(r, "PRCM", sd), sr(r, "PRCM", sd)) for o, sd in trip], py.get(sc, 0.0))
    stmt(up)
    outs: Dict[str, List[str]] = {}
    cropo = set(S.cropo)
    for a, o in S.pact_to_y:
        if a in set(S.grcu) and o in cropo:
            outs.setdefault(a, []).append(o)
    up = {}
    for r in msest:                                                                        # l. 149-156
        for a, os_ in outs.items():
            if (sum(g(r, "GROF", o) - bm(r, "GROF", o) * lo(r, o) * dec for o in os_) > TINY
                    and g(r, a, "LEVL") and sum(sr(r, "GROF", o) for o in os_)):
                up[(r, a, "LEVL", y)] = AB.P_Result_LEVL_GRCU(g(r, a, "LEVL"), [g(r, "GROF", o) for o in os_],
                                                              [sr(r, "GROF", o) for o in os_])
    stmt(up)
    stmt({(r, "MAPR", "SUGA", y): AB.P_Result_MAPR_SUGA(g(r, "MAPR", "SUGA"), quts.get((r, "QUTS", "SUGA", y), 0.0),
                                                        g(r, "INDM", "SUGA"), ex(r, "BIOF", "SUGA"))
          for r in msest if quts.get((r, "QUTS", "SUGA", y), 0.0) > 0 and g(r, "MAPR", "SUGA")
          and (r, "MAPR", "SUGA") in nobs and ex(r, "BIOF", "SUGA") > TINY})               # l. 162-172
    for r in msest:                                                                        # l. 175
        if (r, "MAPR", "SUGA") not in nobs:
            _put(expert, (r, "BIOF", "SUGA", y), AB.P_Result_BIOF_SUGA_Expert())
    stmt({(r, "PRCM", "SUGB", y): AB.P_Result_PRCM_SUGB(g(r, "PRCM", "SUGB"), bm(r, "PRCM", "SUGB"), lo(r, "SUGB"), n,
                                                        g(r, "MAPR", "SUGA"), sr(r, "MAPR", "SUGA"),
                                                        prcy.get((r, "PRCY", "SUGA", y), 0.0))
          for r in msest if g(r, "PRCM", "SUGB") and g(r, "MAPR", "SUGA")})                # l. 179-186
    stmt({(r, "GROF", "SUGB", y): AB.P_Result_GROF_SUGB(g(r, "GROF", "SUGB"), bm(r, "GROF", "SUGB"), lo(r, "SUGB"), n,
                                                        g(r, "PRCM", "SUGB"), sr(r, "PRCM", "SUGB"), pa(r, "SUGB"))
          for r in msest if g(r, "GROF", "SUGB") and g(r, "PRCM", "SUGB")})                # l. 191-197
    stmt({(r, c, "SUGB", y): AB.P_Result_ShiftSugbPos(bm(r, c, "SUGB"), g(r, "GROF", "SUGB"), bm(r, "GROF", "SUGB"))
          for r in msest if g(r, "GROF", "SUGB") and bm(r, "GROF", "SUGB") for c in S.shift_sugb})   # l. 202-207
    stmt({(r, "LOSM", "SUGB", y): AB.P_Result_LOSM_SUGB(bas.get((r, "LOSM", "SUGB"), 0.0), g(r, "GROF", "SUGB"),
                                                        bas[(r, "GROF", "SUGB")])
          for r in msest if g(r, "GROF", "SUGB") and bas.get((r, "GROF", "SUGB"))})       # l. 212-216
    stmt({(r, "DOMM", "SUGB", y): AB.P_Result_DOMM_SUGB(g(r, "DOMM", "SUGB"), [g(r, c, "SUGB") for c in S.dompos],
                                                        [sr(r, c, "SUGB") for c in S.dompos])
          for r in msest if g(r, "DOMM", "SUGB")})                                         # l. 221-225
    stmt({(r, "SUGB", "LEVL", y): AB.P_Result_LEVL_SUGB(g(r, "SUGB", "LEVL"), g(r, "GROF", "SUGB"),
                                                        sr(r, "GROF", "SUGB"))
          for r in msest if g(r, "SUGB", "LEVL") and sr(r, "GROF", "SUGB")})              # l. 230-234


def overwrite(R: Dict[K4, float], expert: Dict[K4, float], *, rest: Iterable[str], s_colsest: Iterable[str],
              s_rowsest: Iterable[str], exante: Sequence[int]) -> None:
    """define_stats_and_supports.gms l. 600-605, in place."""
    rest, cols, rows, yrs = set(rest), set(s_colsest), set(s_rowsest), set(exante)
    for k, v in expert.items():
        if k[0] in rest and k[1] in cols and k[2] in rows and k[3] in yrs and v:
            R[k] = v


def mcact_scale(R: Dict[K4, float], *, rest: Iterable[str], mcact: Iterable[str], exante: Sequence[int]) -> None:
    """l. 618-622, in place: the areas' supports times (0.67 UAAR + 0.33 sum of the areas) / sum of the areas."""
    mc = list(mcact)
    for r in rest:
        for y in exante:
            u = R.get((r, "UAAR", "LEVL", y), 0.0)
            if not u:
                continue
            tot = sum(R.get((r, a, "LEVL", y), 0.0) for a in mc)
            f = (UAAR_SHARE * u + (1 - UAAR_SHARE) * tot) / tot if tot else None
            for a in mc:
                v = R.get((r, a, "LEVL", y), 0.0)
                if v > MCACT_MIN:
                    _put(R, (r, a, "LEVL", y), v * f)


def adjust_trade(R: Dict[K4, float], expert: Dict[K4, float], *, ms: Iterable[str], s_rowsest: Iterable[str],
                 exante: Sequence[int], basm: Dict[K3, float], dompos: Iterable[str]) -> None:
    """adjust_trade_supports.gms (its OILS_ADJ block off), in place: NTRD = production - domestic use where IMPT or EXPT
    has a support, then IMPT and EXPT rescaled to the new NTRD and kept non-negative."""
    dp = list(dompos)
    for r in ms:
        for w in s_rowsest:
            for y in exante:
                g = lambda c: R.get((r, c, w, y), 0.0)                        # noqa: E731
                e = lambda c: expert.get((r, c, w, y), 0.0)                   # noqa: E731
                im, xp = g("IMPT"), g("EXPT")
                if (im or xp) and (g("GROF") or g("MAPR") or im):                             # l. 29-45
                    _put(R, (r, "NTRD", w, y), AT.P_Result_NTRD_Support(
                        g("GROF"), g("MAPR"), g("DOMM"), [g(c) for c in dp], [e(c) for c in dp], e("DOMM")))
                si, sx = AT.P_Result_trade_series(g("IMPT")), AT.P_Result_trade_series(g("EXPT"))   # l. 134-135
                sn = AT.P_Result_NTRD_series(sx, si) if (g("NTRD") and (si or sx)) else 0.0   # l. 136-139
                if si + sx > TRADE_MIN:                                                        # l. 142-155
                    ni = AT.P_Result_IMPT_Support(si, sx, g("NTRD"), sn)
                    nx = AT.P_Result_EXPT_Support(si, sx, g("NTRD"), sn)
                    _put(R, (r, "IMPT", w, y), ni)
                    _put(R, (r, "EXPT", w, y), nx)
                i2, x2 = g("IMPT"), g("EXPT")
                if sn or i2 or x2:                                                             # l. 161-172
                    a = AT.P_Result_IMPT_series(basm.get((r, "IMPT", w), 0.0), i2, x2)
                    b = AT.P_Result_EXPT_series(basm.get((r, "EXPT", w), 0.0), x2, i2)
                else:
                    a = b = AT.P_Result_trade_series_reset()                                   # l. 157-158
                _put(R, (r, "IMPT", w, y), AT.P_Result_trade_Support(a))                       # l. 174-175
                _put(R, (r, "EXPT", w, y), AT.P_Result_trade_Support(b))


def wvarerr(expert: Dict[K4, float], trust: Dict[K4, float]) -> Dict[K4, float]:
    """define_stats_and_supports.gms l. 646-650: wVarErr of the positions with a TrustLevl."""
    return {k: (max(WVAR_FLOOR, abs(expert.get(k, 0.0))) * WVAR_CV / WVAR_SIGMAS * (WVAR_SCALE / t)) ** 2
            for k, t in trust.items() if t}


def domm_wvarerr(w: Dict[K4, float], R: Dict[K4, float], externals: Sequence[Dict[K4, float]], *, ms: Iterable[str],
                 s_colsest: Iterable[str], s_rowsest: Iterable[str], exante: Sequence[int],
                 dompos: Iterable[str]) -> None:
    """l. 655-663, in place on w: the domestic use components with a support but no external one (DGAgri1, Expert,
    Longrun1) where DOMM has one get wVarErr x 10, between those of trust levels 1 and 1e-4."""
    cols = [c for c in s_colsest if c in set(dompos)]
    has = lambda k: any(d.get(k) for d in externals)                         # noqa: E731
    up = {}
    for r in ms:
        for c in cols:
            for row in s_rowsest:
                for y in exante:
                    k = (r, c, row, y)
                    s = R.get(k, 0.0)
                    if s and not has(k) and has((r, "DOMM", row, y)):
                        up[k] = min(max(w.get(k, 0.0) * DOMM_WVAR_FACTOR,
                                        (s * WVAR_CV / WVAR_SIGMAS * (WVAR_SCALE / DOMM_TRUST_HIGH)) ** 2),
                                    (s * WVAR_CV / WVAR_SIGMAS * (WVAR_SCALE / DOMM_TRUST_LOW)) ** 2)
    for k, v in up.items():
        _put(w, k, v)

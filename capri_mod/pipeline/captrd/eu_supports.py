"""CAPTRD's supports after the first estimation (Solve1): DG AGRI's information brought into the member states' supports,
for one ex-ante year (captrd/define_eu_supports.gms, CAPRI star 3.0; captrd.gms l. 1064-1072, between Solve1 and
Solve2 of the ex-ante loop).

  l. 43-45     Step2: Solve1's results (input here: CAPTRD's stored step2 of the member states)
  l. 63-191    beyond %lst_dgagri%: DGAgri1 extrapolated from Step3 by a logistic from its growth rate between the
               midpoint of Fst_exAnte and Sec_exAnte and %lst_dgagri% (approach 3; approaches 1 and 2 are in $ontext),
               also stored as Extrap
  l. 214-223   Step2 summed to the EU aggregates with DGAgri1, over the members without their own DGAgri1
  l. 238-262   the members' DGAgri1 where missing: their Step2 scaled by the aggregate's DGAgri1/Step2; HERD = LEVL of
               the 365-day animals
  l. 271-343   beyond %phaseInYr% in a run beyond %lst_dgagri%: DGAgri1 merged with the long-run supports (Longrun1),
               the DOMM components, CERE and OILS, the milk yield kept rising; Extrap; Longrun1 copied to DGAgri1
  l. 355-364   UAAR's DGAgri1 within [BAST x 0.998^(t - BAST), BAST] (BASM where no BAST)
  l. 368-376   the aggregates' DGAgri1 recalculated (for display)
  l. 387       adjust_to_biof_supports.gms on DGAgri1 (final_supports.biof_adjust)
  l. 400-509   the supports from DGAgri1 where there is no expert support: market balances, PRCI, LEVL, HERD, prices,
               TOOU, yields; EAAG deleted with DG AGRI's UVAG and GROF (%aglinkTightLink% off: l. 413-469 not active)
  l. 518-536   NTRD implied by the other market balance supports
  l. 540-558   DDGS: the aggregates' net exports reduced by 90%, spread by the members' shares of GROF.FPRO
  l. 565-604   IMPT and EXPT made consistent with NTRD, non-negative
  l. 608       the sugar beet trade back to the expert supports
  l. 613-617   EAAG deleted with an expert price and a quota
  l. 624-629   the crop areas scaled to close 67% of their gap to UAAR
  l. 641-684   young pigs, chickens and lambs from the activities with external supports
  l. 689-706   (cattle trust levels with p_globiomTightLink: only for CAPTRD's "animalChange" application)
  l. 710-711   market balance supports non-negative
  l. 719-864   the trust levels of DG AGRI's supports
  l. 869-881   DGAgri and DGAgri1 beyond %lst_dgagri% deleted, and DGAgri1 where neither the member nor its EU part has
               DGAgri
  l. 883-895   wVarErr from the trust levels; IMPT and EXPT x 25 with an NTRD support

GAMS's semantics kept: an assignment's right side reads the values from before the statement; a zero deletes; the
statements run on the ex-ante year y (the loop's exAnte). The inputs are the positions of P_Result as dictionaries
{(region, col, row, year): value}, changed in place.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from capri_mod.pipeline.captrd import final_supports as F

K3 = Tuple[str, str, str]
K4 = Tuple[str, str, str, int]

#: captrd.gms l. 336-337: the logistic's minimum and maximum relative to %lst_dgagri% (l. 127-184)
EXTRAP_MIN = 0.75
EXTRAP_MAX = 2.0 - EXTRAP_MIN
#: l. 151-152: Step3 above which the growth rate is computed
EXTRAP_TINY = 1.E-4
#: l. 280: the year the long-run weight reaches p_longWgt
WGT_YEAR = 2050
#: l. 316: the yearly growth of the milk yield kept at least
MILK_GROWTH = 0.0025
#: l. 364: UAAR's yearly decline at the lower bound
UAAR_DECLINE = 0.998
#: l. 241: the aggregates' Step2 above which the members are scaled (GAMS's eps, taken as zero)
EPS = 0.0
#: l. 549: the share of the aggregates' DDGS net exports removed
DDGS_SHARE = 0.9
#: l. 555: FEDM.DDGS kept at least 0.1 above zero by the NTRD correction
DDGS_FEDM_MIN = 0.1
#: l. 573, 581: the gross trade above which IMPT and EXPT are rescaled; l. 592: their floor as a share of BASM
TRADE_MIN = 1.E-6
#: l. 646: thousand heads to 1000 t
PER_1000 = 1000.
#: l. 722-731: DG AGRI's trust level, +1 for GROF, MAPR, DOMM, HCOM, +2 for the meats, -2 for SGMI
TRUST_DG = 5.
TRUST_DG_POS = 1.
TRUST_DG_MEAT = 2.
TRUST_DG_SGMI = 2.
#: l. 742-747: an aggregate's only, +1 for GROF, MAPR, DOMM
TRUST_AGG = 3.
TRUST_AGG_POS = 1.
#: l. 757: IMPT, EXPT, NTRD, LEVL
TRUST_TRADE = 5.
#: l. 770: CERE and OILS levels
TRUST_GROUPS = 1.
#: l. 778-780: the animals' levels: 5 - (3 + 1.5 where HERD was copied from LEVL) where extrapolated
TRUST_ANIMAL = 5.
TRUST_ANIMAL_EXTRAP = 3.
TRUST_ANIMAL_HERD = 1.5
#: l. 784: the animals not using young cows (PACT_TO_IO(MAACT, "ICOW")) 2 lower
TRUST_NO_ICOW = 2.
#: l. 793, 816: the trust level divided by 5 (EXPE with an expert price and a quota; GROF with a quota on a product)
TRUST_QUOTA_DIV = 5.
#: l. 815: from this year
QUOTA_YEAR = 2006
#: l. 803: yields 3, milk yields 3 + 4
TRUST_YIELD = 3.
TRUST_YIELD_COMI = 4.
#: l. 833-835: beyond %lst_dgagri% x (1 + 0.8 x share of the way to 2050), at most 10
TRUST_MAX = 10.
TRUST_LONG = 0.8
#: l. 850, 857, 864: prices 3, an aggregate's 0.5, UVAD 0.3
TRUST_UVAG = 3.
TRUST_UVAG_AGG = 0.5
TRUST_UVAD = 0.3
#: l. 895: IMPT and EXPT's standard deviation x 5 with an NTRD support
TRADE_SD_FACTOR = 5.
#: captrd.gms l. 559 and 946-948: the row and columns out of S_RowsEst and S_ColsEst before S_RowsEst1 and S_ColsEst1
#: are taken (prep_data_for_estimation.gms l. 25, captrd.gms l. 949), the sets define_eu_supports.gms l. 38-39 restores
ROWS_OUT = ("LABT",)
COLS_OUT = ("QUTS", "QUTA", "QUTB")
#: sets_captrd.gms l. 537: the positions with external supports
EXTERNAL = ("dgagri1", "expert", "longrun1")


@dataclass
class Sets:
    ms: List[str]
    rmaggsup: List[str]                      # rmAggSup, CAPTRD's instance (sets.gms l. 8524-8527, sets_captrd.gms l. 184,
                                             # baseline/aglink2023dgAgri_mappings.gms l. 36-37)
    ms_to_agg: List[Tuple[str, str]]         # MS_TO_RMSAGG = MAP_RR(EUAllAgg, MS) (sets_captrd.gms l. 196-197)
    euparts: List[str]                       # EUparts (baseline/aglink2023dgAgri_mappings.gms l. 41-44)
    cur_europ_agg: List[str]                 # CurEuropAgg (captrd.gms l. 646-655)
    s_colsest: List[str]
    s_rowsest: List[str]
    mrkbalee: List[str]
    dompos: List[str]
    pric: List[str]                          # PRIC (baseline/load_aglink2023dgAgri.gms l. 19: UVAG)
    pact_to_y: List[Tuple[str, str]]
    pact_to_io: List[Tuple[str, str]]
    maact: List[str]
    mcact: List[str]
    cact: List[str]
    grpc: List[str]
    grpr: List[str]
    cropc_to_g: List[Tuple[str, str]]        # (crop, group)
    rows_to_g: List[Tuple[str, str]]         # (row, group)
    aact_365: List[str]                      # AACTwith365days (sets_captrd.gms l. 466)
    meas: List[str]                          # R_T_OAGG("MEAS", rows)
    tradeest: List[str]
    secod: List[str]
    prcd: List[Tuple[str, str]]              # PRCD(SECOD, rows)
    dcow: List[str]                          # DCOW (DCOL, DCOH)
    biof: F.Sets = None                      # the sets of adjust_to_biof_supports.gms


@dataclass
class Years:
    lst_dgagri: int
    lst_exante: int
    phase_in: int                            # %phaseInYr% (captrd.gms l. 166)
    fst_exante: int
    sec_exante: Optional[int]
    lst_expostt: int
    before: Dict[int, int]                   # BeFore(exAnte, exAnte - 1)
    bas_year: int
    bast_year: int
    bast_ord: float                          # OrdT("BAST")
    fst_for_biof: int                        # adjust_to_biof_supports.gms's Fst_exAnte
    long_wgt: float = 0.9                    # longrun_supports.gms l. 90 p_longWgt
    long_exp: float = 0.7                    # l. 93 p_longExp


@dataclass
class Pos:
    """P_Result's positions used here, {(region, col, row, year): value}."""
    step2: Dict[K4, float]
    step3: Dict[K4, float]
    dgagri: Dict[K4, float]
    dgagri1: Dict[K4, float]
    support: Dict[K4, float]
    support1: Dict[K4, float]
    expert: Dict[K4, float]
    trust: Dict[K4, float]
    wvar: Dict[K4, float]
    longrun: Dict[K4, float] = field(default_factory=dict)
    longrun1: Dict[K4, float] = field(default_factory=dict)
    extrap: Dict[K4, float] = field(default_factory=dict)
    quts: Dict[K4, float] = field(default_factory=dict)      # P_Result(.., "QUTS", .., exAnte, "p_data")


def est_sets(s_colsest, s_rowsest) -> Tuple[List[str], List[str]]:
    """S_ColsEst1 and S_RowsEst1 from the transcribed S_ColsEst and S_RowsEst (ROWS_OUT, COLS_OUT)."""
    return [c for c in s_colsest if c not in COLS_OUT], [w for w in s_rowsest if w not in ROWS_OUT]


def _put(d: Dict, k, v: float) -> None:
    if v:
        d[k] = v
    else:
        d.pop(k, None)


def _assign(d: Dict, new: Dict) -> None:
    """A statement's results written after its right sides were read."""
    for k, v in new.items():
        _put(d, k, v)


def _sigmoid(x: float) -> float:
    return 1. / (1. + math.exp(-x))


def eu_supports(P: Pos, y: int, S: Sets, T: Years, *, bast: Dict[K3, float], basm: Dict[K3, float],
                bas: Dict[K3, float], nobs: Set[K3], prd_adj: Dict, low_lim: Dict, upp_lim: Dict) -> None:
    """define_eu_supports.gms for the ex-ante year y, in place on P."""
    ms, msset = list(S.ms), set(S.ms)
    cols, rows = list(S.s_colsest), list(S.s_rowsest)
    colset, rowset = set(cols), set(rows)
    mrk = [c for c in S.mrkbalee]
    sup_set, cur_set, parts = set(S.rmaggsup), set(S.cur_europ_agg), set(S.euparts)
    all_of: Dict[str, List[str]] = {}                                    # MS_TO_RMSAGG(m, *)
    mem_of: Dict[str, List[str]] = {}
    for m, a in S.ms_to_agg:
        if m in msset:
            all_of.setdefault(m, []).append(a)
            mem_of.setdefault(a, []).append(m)
    aggs_of = {m: [a for a in v if a in sup_set] for m, v in all_of.items()}   # MS_TO_RMSAGG(m, rmAggSup)
    aggs = [a for a in S.rmaggsup if a in mem_of]
    L = T.lst_dgagri
    g = lambda d, r, c, w, t=y: d.get((r, c, w, t), 0.0)              # noqa: E731
    keys_y = lambda d: [k for k in d if k[3] == y]                     # noqa: E731

    # ---- l. 63-191: beyond %lst_dgagri%, DGAgri1 extrapolated from Step3
    if y > L:
        ends = [t for t in (T.fst_exante, T.sec_exante) if t is not None]
        sp_t = sum(ends) / len(ends)                                     # OrdT("StartpointExtrap")

        def cond(r, c, w):                                               # l. 73-76, 174-177
            v = g(P.dgagri1, r, c, w, L)
            if c in ("PRCI", "INDM") and w == "MAIZ":
                v += sum(g(P.dgagri1, a, "PRCI", "MAIZ", L) for a in all_of.get(r, []) if a in cur_set)
            return v
        cand = {(r, c, w) for (r, c, w, t) in P.dgagri1 if t == L and r in msset and c in colset and w in rowset}
        cand |= {(r, c, "MAIZ") for r in ms for c in ("PRCI", "INDM") if c in colset and "MAIZ" in rowset}
        new = {}
        for (r, c, w) in cand:
            if not cond(r, c, w):
                continue
            s3 = [g(P.step3, r, c, w, t) for t in ends]
            s0 = sum(s3) / len(s3) if sum(s3) else 0.0                   # l. 72-81
            sl = g(P.step3, r, c, w, L)
            bsy = 0.0
            if c != "NTRD" and s0 > EXTRAP_TINY and sl > EXTRAP_TINY:    # l. 149-165
                gr = (sl / s0) ** (1. / (L - sp_t)) - 1.
                bsy = gr / (1 - EXTRAP_MIN) / (1 - (1 - EXTRAP_MIN) / (EXTRAP_MAX - EXTRAP_MIN))
            f = (EXTRAP_MIN + (EXTRAP_MAX - EXTRAP_MIN) * _sigmoid(bsy * (y - L))) if bsy else 1.
            new[(r, c, w, y)] = sl * f                                   # l. 170-184
        _assign(P.dgagri1, new)
        _set_extrap(P, y, msset, colset, rowset)                         # l. 189

    # ---- l. 214-223: Step2 of the aggregates where they have DGAgri1, over the members without their own
    st2_agg: Dict[K3, float] = {}
    for a in aggs:
        for c in mrk:
            for w in rows:
                if g(P.dgagri1, a, c, w):
                    st2_agg[(a, c, w)] = sum(g(P.step2, m, c, w) for m in mem_of[a] if not g(P.dgagri1, m, c, w))
        for c in cols:
            if g(P.dgagri1, a, c, "LEVL"):
                st2_agg[(a, c, "LEVL")] = sum(g(P.step2, m, c, "LEVL") for m in mem_of[a]
                                              if not g(P.dgagri1, m, c, "LEVL"))
    sa = lambda a, c, w: st2_agg.get((a, c, w), 0.0)                    # noqa: E731

    # ---- l. 238-262: the members' DGAgri1 from their aggregates'
    new = {}
    for m in ms:
        for c in mrk:
            for w in rows:
                if g(P.dgagri1, m, c, w):
                    continue
                f = sum(g(P.dgagri1, a, c, w) / sa(a, c, w) for a in aggs_of.get(m, []) if sa(a, c, w) > EPS)
                new[(m, c, w, y)] = g(P.step2, m, c, w) * f
    _assign(P.dgagri1, new)
    new = {}
    for m in ms:
        for c in cols:
            if g(P.dgagri1, m, c, "LEVL"):
                continue
            f = sum(g(P.dgagri1, a, c, "LEVL") / sa(a, c, "LEVL") for a in aggs_of.get(m, []) if sa(a, c, "LEVL"))
            new[(m, c, "LEVL", y)] = g(P.step2, m, c, "LEVL") * f
    _assign(P.dgagri1, new)
    _assign(P.dgagri1, {(m, c, "HERD", y): g(P.dgagri1, m, c, "LEVL") for m in ms for c in cols
                        if c in set(S.aact_365) and not g(P.dgagri1, m, c, "HERD") and g(P.dgagri1, m, c, "LEVL")})

    # ---- l. 271-343: the long-run merge
    if T.lst_exante > L and y > T.phase_in:
        wt = ((min(WGT_YEAR, y) - T.phase_in) / (WGT_YEAR - T.phase_in)) ** T.long_exp * T.long_wgt
        _assign(P.longrun1, {(r, c, w, y): g(P.longrun, r, c, w) * wt + g(P.dgagri1, r, c, w) * (1 - wt)
                             for (r, c, w, t) in list(P.longrun) if t == y and r in msset and c in colset
                             and w in rowset and g(P.dgagri1, r, c, w)})
        new = {}
        for m in ms:                                                     # l. 291-298
            for c in S.dompos:
                if c not in colset:
                    continue
                for w in rows:
                    if (g(P.longrun1, m, "DOMM", w) and g(P.dgagri1, m, "DOMM", w) and g(P.dgagri1, m, c, w)
                            and not g(P.longrun1, m, c, w)):
                        new[(m, c, w, y)] = g(P.longrun1, m, "DOMM", w) * g(P.dgagri1, m, c, w) / g(P.dgagri1, m, "DOMM", w)
        _assign(P.longrun1, new)
        if y > L:                                                        # l. 303-309
            grp = {"CERE", "OILS"}
            _assign(P.longrun1, {(m, gc, "LEVL", y): sum(g(P.longrun1, m, cc, "LEVL") for cc, gg in S.cropc_to_g
                                                          if gg == gc)
                                 for m in ms for gc in S.grpc if gc in grp})
            _assign(P.longrun1, {(m, c, gr, y): sum(g(P.longrun1, m, c, rr) for rr, gg in S.rows_to_g
                                                     if gg == gr and rr in rowset)
                                 for m in ms for c in mrk for gr in S.grpr if gr in grp})
            prev = T.before.get(y)                                       # l. 314-318
            new = {}
            for m in ms:
                for d in S.dcow:
                    v = g(P.longrun1, m, d, "COMI")
                    if v:
                        b = (g(P.step3, m, d, "COMI", prev) * (1 + MILK_GROWTH) ** (y - prev)
                             if prev is not None and prev > T.lst_expostt else 0.0)
                        new[(m, d, "COMI", y)] = max(b, v)
            _assign(P.longrun1, new)
        if y >= L:                                                       # l. 331-332
            _set_extrap(P, y, msset, colset, rowset)
        _assign(P.dgagri1, {k: v for k, v in P.longrun1.items()          # l. 335-341
                            if k[3] == y and k[0] in msset and k[1] in colset and k[2] in rowset and v})

    # ---- l. 355-364: UAAR's DGAgri1 within the estimation's bounds
    new = {}
    for m in ms:
        b = bast.get((m, "UAAR", "LEVL"), 0.0) or basm.get((m, "UAAR", "LEVL"), 0.0)
        v = g(P.dgagri1, m, "UAAR", "LEVL")
        if b and v:                     # the exponent: OrdT(exAnte) - OrdT("BAST") (OrdT("BAST") is never zero)
            new[(m, "UAAR", "LEVL", y)] = max(min(b, v), b * UAAR_DECLINE ** (y - T.bast_ord))
    _assign(P.dgagri1, new)

    # ---- l. 368-376: the aggregates' DGAgri1 (for display)
    new = {}
    for a in aggs:
        for c in mrk:
            for w in rows:
                v = g(P.dgagri1, a, c, w) + sum(g(P.dgagri1, m, c, w) for m in mem_of[a] if g(P.dgagri, m, c, w))
                new[(a, c, w, y)] = v
        for c in cols:
            new[(a, c, "LEVL", y)] = g(P.dgagri1, a, c, "LEVL") + sum(g(P.dgagri1, m, c, "LEVL") for m in mem_of[a]
                                                                       if g(P.dgagri, m, c, "LEVL"))
    _assign(P.dgagri1, new)

    # ---- l. 387: adjust_to_biof_supports.gms on DGAgri1
    F.biof_adjust(P.dgagri1, P.expert, y=y, ms=ms, S=S.biof, basm=basm, bast=bast, bas=bas, nobs=nobs, quts=P.quts,
                  prcy=P.support, lst_dgagri=L, fst_exante=T.fst_for_biof, bas_year=T.bas_year,
                  bast_year=T.bast_year, prd_adj=prd_adj, low_lim=low_lim, upp_lim=upp_lim)

    # ---- l. 400-509: the supports from DGAgri1
    E = lambda r, c, w: g(P.expert, r, c, w)                            # noqa: E731
    D1 = lambda r, c, w: g(P.dgagri1, r, c, w)                          # noqa: E731
    _assign(P.support, {(m, c, w, y): D1(m, c, w) for m in ms for c in mrk for w in rows
                        if not (E(m, c, w) or c == "NTRD") and D1(m, c, w)})
    _assign(P.support, {(m, "PRCI", w, y): D1(m, "PRCI", w) for m in ms for w in rows
                        if not E(m, "PRCI", w) and D1(m, "PRCI", w)})
    _assign(P.support, {(m, c, "LEVL", y): D1(m, c, "LEVL") for m in ms for c in cols
                        if not E(m, c, "LEVL") and D1(m, c, "LEVL")})
    _assign(P.support, {(m, c, "HERD", y): D1(m, c, "HERD") for m in ms for c in cols
                        if not E(m, c, "HERD") and D1(m, c, "HERD")})
    _assign(P.support, {(m, c, w, y): D1(m, c, w) for m in ms for c in S.pric for w in rows
                        if D1(m, c, w) and not E(m, c, w)})
    _assign(P.support, {(m, c, "TOOU", y): D1(m, c, "TOOU") for m in ms for c in cols
                        if D1(m, c, "TOOU") and not E(m, c, "TOOU")})
    pty = [(a, o) for a, o in S.pact_to_y if a in colset and o in rowset]
    _assign(P.support, {(m, a, o, y): D1(m, a, o) for m in ms for a, o in pty if D1(m, a, o) and not E(m, a, o)})
    _assign(P.support, {(m, "EAAG", w, y): 0.0 for m in ms for w in rows
                        if D1(m, "UVAG", w) and D1(m, "GROF", w) and not E(m, "EAAG", w)})

    # ---- l. 518-536: NTRD implied
    sp = lambda r, c, w: g(P.support, r, c, w)                          # noqa: E731
    dompos = [c for c in S.dompos]
    new = {}
    for m in ms:
        for w in rows:
            if not ((sp(m, "IMPT", w) or sp(m, "EXPT", w)) and (sp(m, "GROF", w) or sp(m, "MAPR", w))):
                continue
            ext_dom = sum(D1(m, c, w) + E(m, c, w) for c in dompos)
            v = sp(m, "GROF", w) + (sp(m, "MAPR", w) if not sp(m, "GROF", w) else 0.0)
            if D1(m, "DOMM", w) and not ext_dom:
                v -= sp(m, "DOMM", w)
            if (not D1(m, "DOMM", w)) or ext_dom:
                v -= sum(sp(m, c, w) for c in dompos)
            new[(m, "NTRD", w, y)] = v
    _assign(P.support, new)

    # ---- l. 540-558: DDGS
    s2 = lambda r, c, w: g(P.step2, r, c, w)                            # noqa: E731
    agg_ntrd = {a: sum(s2(m, "NTRD", "DDGS") for m in mem_of[a]) for a in aggs}
    agg_fpro = {a: sum(s2(m, "GROF", "FPRO") for m in mem_of[a]) for a in aggs}
    new = {}
    for m in ms:
        den = sum(agg_fpro[a] for a in aggs_of.get(m, []) if a in agg_fpro)
        if den:
            new[(m, "NTRD", "DDGS", y)] = (s2(m, "NTRD", "DDGS") - DDGS_SHARE * sum(agg_ntrd[a] for a in aggs_of[m]
                                                                                   if a in agg_ntrd)
                                           * s2(m, "GROF", "FPRO") / den)
    _assign(P.support, new)
    s1 = lambda r, c, w: g(P.support1, r, c, w)                         # noqa: E731
    _assign(P.support, {(m, "FEDM", "DDGS", y): s1(m, "FEDM", "DDGS") - min(
        s1(m, "FEDM", "DDGS") - DDGS_FEDM_MIN, sp(m, "NTRD", "DDGS") - s1(m, "NTRD", "DDGS"))
        for m in ms if s1(m, "FEDM", "DDGS")})
    _assign(P.support, {(m, "DOMM", "DDGS", y): sp(m, "FEDM", "DDGS") for m in ms if sp(m, "FEDM", "DDGS")})

    # ---- l. 565-604: IMPT and EXPT consistent with NTRD
    for m in ms:
        for w in rows:
            im, ex = sp(m, "IMPT", w), sp(m, "EXPT", w)
            nt_old = (ex - im) if (im or ex) else 0.0
            nt = sp(m, "NTRD", w)
            gross = ex + im
            im1, ex1 = im, ex
            if gross > TRADE_MIN:
                im1 = im * (1. - (nt - nt_old) / gross)
                ex1 = ex * (1. + (nt - nt_old) / gross)
            if nt_old:
                im2 = max(TRADE_MIN * basm.get((m, "IMPT", w), 0.0), im1) + max(0., -ex1)
                ex2 = max(TRADE_MIN * basm.get((m, "EXPT", w), 0.0), ex1) + max(0., -im1)
            else:
                im2 = ex2 = 0.0
            _put(P.support, (m, "IMPT", w, y), im2)
            _put(P.support, (m, "EXPT", w, y), ex2)

    # ---- l. 608: the sugar beet trade
    for m in ms:
        for c in S.tradeest:
            _put(P.support, (m, c, "SUGB", y), E(m, c, "SUGB"))

    # ---- l. 613-617: EAAG with an expert price and a quota
    prc_of: Dict[str, List[str]] = {}
    for sd, w in S.prcd:
        if sd in set(S.secod):
            prc_of.setdefault(w, []).append(sd)
    q = lambda r, w: g(P.quts, r, "QUTS", w)                            # noqa: E731
    _assign(P.support, {(m, "EAAG", w, y): 0.0 for m in ms for w in rows
                        if E(m, "UVAG", w) and (sum(q(m, sd) for sd in prc_of.get(w, []) if sd in rowset) or q(m, w))})

    # ---- l. 624-629: the crop areas scaled to close 67% of the gap to UAAR
    mc = [c for c in S.mcact]
    new = {}
    for m in ms:
        tot = sum(sp(m, c, "LEVL") for c in mc)
        ua = sp(m, "UAAR", "LEVL")
        if not ua:
            continue
        for c in cols:
            if c in set(mc) and sp(m, c, "LEVL"):
                new[(m, c, "LEVL", y)] = sp(m, c, "LEVL") * (F.UAAR_SHARE * ua + (1 - F.UAAR_SHARE) * tot) / tot
    _assign(P.support, new)

    # ---- l. 641-684: young animals
    ext = lambda r, c, w: sum(g(getattr(P, n), r, c, w) for n in EXTERNAL)   # noqa: E731
    for yi, ya, a1, a2 in (("IPIG", "YPIG", "SOWS", "PIGF"), ("ICHI", "YCHI", "HENS", "POUF"),
                           ("ILAM", "YLAM", "SHGM", "SHGF")):
        new = {}
        for m in ms:
            if ext(m, "GROF", yi) == 0. and (ext(m, a1, "LEVL") or ext(m, a2, "LEVL")):
                new[(m, "GROF", yi, y)] = (sp(m, a1, "LEVL") * sp(m, a1, yi) + sp(m, a2, "LEVL") * sp(m, a2, yi)) / PER_1000
        _assign(P.support, new)
        _assign(P.support, {(m, "GROF", ya, y): sp(m, "GROF", yi) for m in ms
                            if ext(m, "GROF", ya) == 0. and (ext(m, a1, "LEVL") or ext(m, a2, "LEVL"))})

    # ---- l. 710-711: non-negative market balance supports
    _assign(P.support, {(m, c, w, y): max(0., sp(m, c, w)) for m in ms for c in mrk if c != "NTRD" for w in rows
                        if sp(m, c, w)})

    # ---- l. 719-864: trust levels (%aglinkTightLink% off; l. 838-843, with p_globiomTightLink, not active)
    TL = P.trust
    tl = lambda r, c, w: g(TL, r, c, w)                                 # noqa: E731
    DG = lambda r, c, w: g(P.dgagri, r, c, w)                           # noqa: E731
    meas = set(S.meas)
    dom = [(m, c, w) for m in ms for c in cols for w in rows]
    _assign(TL, {(m, c, w, y): TRUST_DG + TRUST_DG_POS * (c in ("GROF", "MAPR", "DOMM", "HCOM"))
                 + TRUST_DG_MEAT * (w in meas) - TRUST_DG_SGMI * (w.upper() == "SGMI")
                 for (m, c, w) in dom if DG(m, c, w) and D1(m, c, w) == sp(m, c, w)})                   # l. 719-731
    _assign(TL, {(m, c, w, y): TRUST_AGG + TRUST_AGG_POS * (c in ("GROF", "MAPR", "DOMM"))
                 - TRUST_DG_SGMI * (w.upper() == "SGMI")
                 for (m, c, w) in dom
                 if not DG(m, c, w) and D1(m, c, w) and not E(m, c, w) and D1(m, c, w) == sp(m, c, w)})  # l. 735-749
    _assign(TL, {(m, c, w, y): TRUST_TRADE for (m, c, w) in dom                                       # l. 752-761
                 if D1(m, c, w) and not E(m, c, w) and (c in ("IMPT", "EXPT", "NTRD") or w == "LEVL")})
    _assign(TL, {(m, c, "LEVL", y): TRUST_GROUPS for m in ms for c in ("CERE", "OILS")               # l. 767-770
                 if c in colset and D1(m, c, "LEVL") and not E(m, c, "LEVL")})
    icow = {a for a, i in S.pact_to_io if i == "ICOW"}
    new = {}
    for m in ms:                                                         # l. 774-785
        for c in S.maact:
            d = D1(m, c, "LEVL")
            if d and d == sp(m, c, "LEVL"):
                ex_ = d == g(P.extrap, m, c, "LEVL")
                new[(m, c, "LEVL", y)] = (TRUST_ANIMAL - (TRUST_ANIMAL_EXTRAP + TRUST_ANIMAL_HERD
                                                          * (D1(m, c, "HERD") == d)) * ex_
                                          - TRUST_NO_ICOW * (c not in icow))
    _assign(TL, new)
    _assign(TL, {(m, "EXPE", w, y): tl(m, "EXPE", w) / TRUST_QUOTA_DIV for m in ms for w in rows       # l. 791-793
                 if E(m, "UVAG", w) and q(m, w)})
    _assign(TL, {(m, a, o, y): TRUST_YIELD + TRUST_YIELD_COMI * (o == "COMI") for m in ms for a, o in pty  # l. 798-803
                 if D1(m, a, o) == sp(m, a, o) and sp(m, a, o)})
    if y >= QUOTA_YEAR:                                                  # l. 809-816
        _assign(TL, {(m, "GROF", w, y): tl(m, "GROF", w) / TRUST_QUOTA_DIV for m in ms for w in rows
                     if sum(q(m, sd) for sd in prc_of.get(w, []) if sd in rowset)
                     and D1(m, "GROF", w) == sp(m, "GROF", w) and D1(m, "GROF", w)})
    if y > L:                                                            # l. 829-835
        share = (min(WGT_YEAR, y) - L) / (WGT_YEAR - L)
        _assign(TL, {(m, c, w, y): min(TRUST_MAX, tl(m, c, w) * (1 + TRUST_LONG * share)) for (m, c, w) in dom
                     if D1(m, c, w) and g(P.longrun1, m, c, w) and not E(m, c, w)})
    _assign(TL, {(m, "UVAG", w, y): TRUST_UVAG for m in ms for w in rows                              # l. 847-850
                 if DG(m, "UVAG", w) and D1(m, "UVAG", w) == sp(m, "UVAG", w)})
    _assign(TL, {(m, "UVAG", w, y): TRUST_UVAG_AGG for m in ms for w in rows                          # l. 853-857
                 if not DG(m, "UVAG", w) and D1(m, "UVAG", w) and D1(m, "UVAG", w) == sp(m, "UVAG", w)})
    _assign(TL, {(m, "UVAD", w, y): TRUST_UVAD for m in ms for w in rows                              # l. 862-864
                 if D1(m, "UVAD", w) == sp(m, "UVAD", w)})

    # ---- l. 869-881: DGAgri and DGAgri1 deleted
    if y > L:
        for k in keys_y(P.dgagri):
            if k[0] in msset and k[1] in colset and k[2] in rowset and P.dgagri1.get(k):
                del P.dgagri[k]
        for k in keys_y(P.dgagri1):
            if k[0] in msset and k[1] in colset and k[2] in rowset:
                del P.dgagri1[k]
    for k in keys_y(P.dgagri1):
        r, c, w, _ = k
        if r in msset and c in colset and w in rowset and not (
                DG(r, c, w) or sum(DG(a, c, w) for a in all_of.get(r, []) if a in parts)):
            del P.dgagri1[k]

    # ---- l. 883-895: wVarErr
    _assign(P.wvar, {(m, c, w, y): (max(F.WVAR_FLOOR, abs(sp(m, c, w))) * F.WVAR_CV / F.WVAR_SIGMAS
                                    * (F.WVAR_SCALE / tl(m, c, w))) ** 2
                     for (m, c, w) in dom if not E(m, c, w) and tl(m, c, w)})
    for c in ("IMPT", "EXPT"):
        _assign(P.wvar, {(m, c, w, y): g(P.wvar, m, c, w) * TRADE_SD_FACTOR ** 2 for m in ms for w in rows
                         if sp(m, "NTRD", w)})


def _set_extrap(P: Pos, y: int, msset, colset, rowset) -> None:
    """P_Result(MS, S_ColsEst, S_RowsEst, ExAnte, "Extrap") = the DGAgri1 (l. 189, 331-332)."""
    for k in [k for k in P.extrap if k[3] == y and k[0] in msset and k[1] in colset and k[2] in rowset]:
        del P.extrap[k]
    for k, v in P.dgagri1.items():
        if k[3] == y and k[0] in msset and k[1] in colset and k[2] in rowset and v:
            P.extrap[k] = v

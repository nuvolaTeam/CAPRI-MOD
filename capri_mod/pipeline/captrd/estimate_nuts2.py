"""CAPTRD-MOD stage 3: the NUTS 2 estimation m_trendNT2 (CAPRI star 3.0, captrd/estimate_nuts2.gms with
captrd/equations.gms l. 909-912): the NUTS 2 regions of one member state estimated together, under the member state's
own result (fixed).

This module holds the equations (stage 3, first part). The model statement:

  AREAB_, LANDUSEB_, OSET_, GROF_, REQS_, GRPLVL_, STRA_, LU_, SplitFix_   per region, as estimate_ms.residuals has
                                                                         them; REQS_'s feed contents are the member
                                                                         state's (SUM(MAP_RR(MSEst, Rest), p_data(MSEst,
                                                                         ReqsT, Feed, "BASM")), l. 522-535): the
                                                                         regional points carry them (regional_basm)
  MSGROF_ (l. 182-195), MSLEVL_ (l. 199-210), MSLANDUSE_ (l. 218-224), MSFEEDI_ (l. 230-240)
                                                                         the regions add up to the member state
  MSlosfFoddo_ (l. 474-485)                                              each region's fodder losses at the member
                                                                         state's loss rate
  MSindmMaif_ (l. 490-495)                                               the regions' INDM of fodder maize add up to the
                                                                         member state's (Germany's biogas maize)
  EFED_ (l. 500-507)                                                     fodder feed = production - losses - INDM
  SSQS_ (l. 803-878) with CARD(Rest) > 1: each term weighted by its region's share of the activity levels (BASM)

The member state is out of the estimation (estimate_nuts2.gms l. 72): its values are the constants ms_V (its result,
CAPTRD's estP). GROF_'s condition for CARD(Rest) > 1 (l. 159-160: at least one region with GROF data) holds where the
member state's GROF_ would. A residual is lhs - rhs, as in estimate_ms.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Tuple

from capri_mod.pipeline.captrd import estimate_ms as E

K2 = Tuple[str, str]
K3 = Tuple[str, str, str]
INF = float("inf")
#: equations.gms l. 909-912: m_trendNT2's blocks that estimate_ms.residuals has
SHARED_BLOCKS = ("AREAB_", "LANDUSEB_", "OSET_", "GROF_", "REQS_", "GRPLVL_", "STRA_", "LU_", "SplitFix_")
#: l. 230-240: MSFEEDI_'s scaling (10 kg per head, in t)
FEED_SCALE, PER_1000 = 10.0, 0.001
#: l. 820-833: the regional weight's floor and its regularisation
WEIGHT_FLOOR, WEIGHT_EPS = 0.001, 1.0e-5
#: MSLANDUSE_'s land uses (l. 219)
MS_LANDUSE = ("FORE", "ARTIF")


def regional_basm(region_basm: Dict[K2, float], ms_basm: Dict[K2, float], S: E.Sets) -> Dict[K2, float]:
    """The region's BASM with the member state's feed contents (ReqsT x FEED), which REQS_ takes (l. 535)."""
    feedc = lambda k: k[0] in S.reqst and k[1] in S.feed                                   # noqa: E731
    return {**{k: v for k, v in region_basm.items() if not feedc(k)}, **{k: v for k, v in ms_basm.items() if feedc(k)}}


def residuals(points: Dict[str, E.Point], ms_nobs: set, ms_V: Dict[K2, float], S: E.Sets, foddi: Iterable[str],
              rset: Iterable[str], split_acts_lo: Iterable[str], var: Optional[Callable] = None,
              levels: Optional[Dict[str, Dict[K2, float]]] = None, ex_feed: Iterable[K2] = ()) \
        -> List[Tuple[str, tuple, str, object]]:
    """m_trendNT2's equations for the regions of one member state. points: {region: its Point} (V the values at which to
    evaluate, nobs, the data, lo / up its bounds); ms_nobs, ms_V: the member state's observed positions and fixed values;
    var: None (residuals at the points' V) or var(region, col, row) -> symbol; levels: {region: V_EstV.L} for the
    domains estimate_ms takes from levels; ex_feed: the member state's (MPACT, FEED) taken out (EX_FEED)."""
    regs = sorted(points)
    V = (lambda r, c, w: points[r].V.get((c, w), 0.0)) if var is None else var
    n = lambda r, c, w: (c, w) in points[r].nobs                                           # noqa: E731
    nm = lambda c, w: (c, w) in ms_nobs                                                    # noqa: E731
    M = lambda c, w: ms_V.get((c, w), 0.0)                                                 # noqa: E731
    lo = lambda r, k: points[r].lo.get(k, 0.0)                                             # noqa: E731
    up = lambda r, k: points[r].up.get(k, INF)                                             # noqa: E731
    out: List[Tuple[str, tuple, str, object]] = []
    add = lambda name, idx, sense, x: out.append((name, idx, sense, float(x) if var is None else x))   # noqa: E731
    # the shared blocks, region by region
    for r in regs:
        vr = None if var is None else (lambda c, w, r=r: var(r, c, w))
        for name, idx, sense, x in E.residuals(points[r], S, var=vr, level=(levels or {}).get(r)):
            if name in SHARED_BLOCKS:
                out.append((name, (r,) + tuple(idx), sense, x))
    feed, foddi = set(S.feed), set(foddi)
    rset, sal, exf = set(rset), set(split_acts_lo), set(ex_feed)
    # MSGROF_ (l. 182-195)
    for w in sorted(S.rows_est):
        if w == "STRA" or w in feed or w in S.grpr or not nm("GROF", w):
            continue
        if not any(n(r, a, "LEVL") and lo(r, (a, w)) != up(r, (a, w)) for r in regs
                   for a, o in S.pact_to_io if o == w and a in S.mpact):
            continue
        add("MSGROF_", (w,), "E", sum(V(r, "GROF", w) for r in regs if n(r, "GROF", w)) - M("GROF", w))
    # MSLEVL_ (l. 199-210)
    for a in sorted(S.mpact):
        if nm(a, "LEVL") and a not in rset and a in S.cols_est and a not in sal and regs:
            add("MSLEVL_", (a,), "E", sum(V(r, a, "LEVL") for r in regs if n(r, a, "LEVL")) - M(a, "LEVL"))
    # MSLANDUSE_ (l. 218-224)
    for c in MS_LANDUSE:
        if c in S.cols_est and nm(c, "LEVL") and regs:
            add("MSLANDUSE_", (c,), "E", sum(V(r, c, "LEVL") for r in regs if n(r, c, "LEVL")) - M(c, "LEVL"))
    # MSFEEDI_ (l. 230-240)
    for a in sorted(S.mpact):
        for f in sorted(feed - foddi):
            if not nm(a, f) or (a, f) in exf:
                continue
            rr = [r for r in regs if n(r, a, "LEVL") and n(r, a, f)]
            if not rr:
                continue
            lhs = sum(V(r, a, "LEVL") * V(r, a, f) * PER_1000 for r in rr) \
                + sum(V(r, a, "LEVL") * FEED_SCALE * PER_1000 for r in regs if n(r, a, "LEVL"))
            add("MSFEEDI_", (a, f), "E", lhs - M(a, "LEVL") * (M(a, f) + FEED_SCALE) * PER_1000)
    foddo = sorted({o for f, o in S.feed_to_o if f in foddi})
    for r in regs:
        for o in foddo:
            # MSlosfFoddo_ (l. 474-485): the member state's loss rate (its estP)
            if n(r, "GROF", o) and o != "STRA":
                rate = M("LOSF", o) / M("GROF", o) if M("GROF", o) else 0.0
                add("MSlosfFoddo_", (r, o), "E", V(r, "LOSF", o) - V(r, "GROF", o) * rate)
            # EFED_ (l. 500-507; ex_endofodderUse is empty outside the farm types)
            fs = [f for f, oo in S.feed_to_o if oo == o]
            if any(n(r, "GROF", f) for f in fs) and n(r, "GROF", o):
                lhs = V(r, "GROF", o) - V(r, "LOSF", o) * n(r, "LOSF", o) - V(r, "INDM", o) * n(r, "INDM", o)
                add("EFED_", (r, o), "E", lhs - sum(V(r, "GROF", f) for f in fs if n(r, "GROF", f)))
    # MSindmMaif_ (l. 490-495)
    if nm("INDM", "MAIF") and any(n(r, "INDM", "MAIF") for r in regs):
        add("MSindmMaif_", (), "E", sum(V(r, "INDM", "MAIF") for r in regs if n(r, "INDM", "MAIF")) - M("INDM", "MAIF"))
    return out


def objective(points: Dict[str, E.Point], S: E.Sets, var: Callable, wvar: Dict[str, Dict[K2, float]],
              basm_levl: Dict[str, Dict[str, float]]):
    """SSQS_ (l. 803-878) for CARD(Rest) > 1: each region's squared deviations from its supports over their standard
    errors, as estimate_ms.objective, weighted by the region's share: for an activity column its LEVL BASM over the
    regions' (each + 1e-5), for any other column the summed LEVL BASM of the activities producing or using the row
    (PACT_TO_IO) over the regions'; at least 0.001; over the same sum at 10% of the supports, plus 1. basm_levl:
    {region: {activity: p_data(region, activity, "LEVL", "BASM")}}. var(region, col, row)."""
    regs = sorted(points)
    io = {}
    for a, w in S.pact_to_io:
        if a in S.mpact:
            io.setdefault(w, []).append(a)
    act_tot = {a: sum(basm_levl.get(r, {}).get(a, 0.0) + WEIGHT_EPS for r in regs) for a in S.mpact}
    row_b = lambda r, w: sum(basm_levl.get(r, {}).get(a, 0.0) for a in io.get(w, ()))      # noqa: E731

    def weight(r, c, w):
        # a row no activity produces or uses: (0 + 1e-5) / (the regions x 1e-5) = 1 / CARD(Rest)
        if c in S.mpact:
            return max(WEIGHT_FLOOR, (basm_levl.get(r, {}).get(c, 0.0) + WEIGHT_EPS) / act_tot[c])
        return max(WEIGHT_FLOOR, (row_b(r, w) + WEIGHT_EPS) / sum(row_b(q, w) + WEIGHT_EPS for q in regs))

    num, den = 0.0, 1.0
    for r in regs:
        p, wv = points[r], wvar.get(r, {})
        for k, sv in sorted(p.support.items()):
            if not sv or not wv.get(k, 0.0) or k[0] not in S.cols_est or k[1] not in S.rows_est:
                continue
            if p.lo.get(k, -INF) == p.up.get(k, INF):
                continue
            sig = max(wv[k] ** 0.5, E.WEIGHT_STD_ERR * sv) + E.SSQ_EPS
            g = weight(r, *k)
            num = num + ((var(r, *k) - sv) / sig) ** 2 * g * E.SSQ_WEIGHT
            den += (E.SSQ_SCALE_DEV * sv / sig) ** 2 * g
        # l. 838-842: STCM of the young animals pulled to zero in the years without data (unweighted)
        if not p.exante_d:
            for o in sorted(S.oyani):
                sg = p.support.get(("GROF", o), 0.0)
                if ("STCM", o) in p.nobs and sg:
                    num = num + (var(r, "STCM", o) / max(E.STCM_SCALE * sg, E.SSQ_EPS)) ** 2 * E.SSQ_WEIGHT
    return num / den

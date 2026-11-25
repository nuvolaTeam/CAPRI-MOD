"""CAPTRD-MOD: the NUTS 2 estimation m_trendNT2 (CAPRI star 3.0, captrd/estimate_nuts2.gms with
captrd/equations.gms l. 909-912): the NUTS 2 regions of one member state estimated together, under the member state's
own result (fixed).

This module holds the equations (the first part of its port). The model statement:

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

import dataclasses
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import casadi as ca
import numpy as np

from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import estimate_nlp as NLP
from capri_mod.pipeline.captrd.equations import equations as EQ
from capri_mod.pipeline.captrd.equations import est_nuts2_grid as GR
from capri_mod.pipeline.captrd.equations import est_nuts2_grid_openbound as OB
from capri_mod.pipeline.captrd.equations import estimate_nuts2 as NB
from capri_mod.pipeline.captrd.equations import nuts2 as NT
from capri_mod.settings import current as current_settings

K2 = Tuple[str, str]
K3 = Tuple[str, str, str]
INF = float("inf")
#: equations.gms l. 909-912: m_trendNT2's blocks that estimate_ms.residuals has
SHARED_BLOCKS = ("AREAB_", "LANDUSEB_", "OSET_", "GROF_", "REQS_", "GRPLVL_", "STRA_", "LU_", "SplitFix_")
#: kg to t (rem_tiny's production from the levels)
PER_1000 = 0.001
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
        add("MSGROF_", (w,), "E", NT.MSGROF_((V(r, "GROF", w) for r in regs if n(r, "GROF", w)), M("GROF", w)))
    # MSLEVL_ (l. 199-210)
    for a in sorted(S.mpact):
        if nm(a, "LEVL") and a not in rset and a in S.cols_est and a not in sal and regs:
            add("MSLEVL_", (a,), "E", NT.MSLEVL_((V(r, a, "LEVL") for r in regs if n(r, a, "LEVL")), M(a, "LEVL")))
    # MSLANDUSE_ (l. 218-224)
    for c in MS_LANDUSE:
        if c in S.cols_est and nm(c, "LEVL") and regs:
            add("MSLANDUSE_", (c,), "E", NT.MSLANDUSE_((V(r, c, "LEVL") for r in regs if n(r, c, "LEVL")),
                                                       M(c, "LEVL")))
    # MSFEEDI_ (l. 230-240)
    for a in sorted(S.mpact):
        for f in sorted(feed - foddi):
            if not nm(a, f) or (a, f) in exf:
                continue
            rr = [r for r in regs if n(r, a, "LEVL") and n(r, a, f)]
            if not rr:
                continue
            add("MSFEEDI_", (a, f), "E", NT.MSFEEDI_(((V(r, a, "LEVL"), V(r, a, f)) for r in rr),
                                                     (V(r, a, "LEVL") for r in regs if n(r, a, "LEVL")),
                                                     M(a, "LEVL"), M(a, f)))
    foddo = sorted({o for f, o in S.feed_to_o if f in foddi})
    for r in regs:
        for o in foddo:
            # MSlosfFoddo_ (l. 474-485): the member state's loss rate (its estP)
            if n(r, "GROF", o) and o != "STRA":
                add("MSlosfFoddo_", (r, o), "E", NT.MSlosfFoddo_(V(r, "LOSF", o), V(r, "GROF", o), M("LOSF", o),
                                                                 M("GROF", o)))
            # EFED_ (l. 500-508; ex_endofodderUse is empty outside the farm types)
            fs = [f for f, oo in S.feed_to_o if oo == o]
            if any(n(r, "GROF", f) for f in fs) and n(r, "GROF", o):
                add("EFED_", (r, o), "E", NT.EFED_(V(r, "GROF", o), V(r, "LOSF", o), n(r, "LOSF", o), V(r, "INDM", o),
                                                   n(r, "INDM", o), (V(r, "GROF", f) for f in fs if n(r, "GROF", f))))
    # MSindmMaif_ (l. 490-495)
    if nm("INDM", "MAIF") and any(n(r, "INDM", "MAIF") for r in regs):
        add("MSindmMaif_", (), "E", NT.MSindmMaif_((V(r, "INDM", "MAIF") for r in regs if n(r, "INDM", "MAIF")),
                                                   M("INDM", "MAIF")))
    return out


def objective(points: Dict[str, E.Point], S: E.Sets, var: Callable, wvar: Dict[str, Dict[K2, float]],
              basm_levl: Dict[str, Dict[str, float]]):
    """SSQS_ (l. 801-875; equations.SSQS_) for CARD(Rest) > 1: each region's squared deviations from its supports over their standard
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

    def terms():
        for r in regs:
            p, wv = points[r], wvar.get(r, {})
            for k, sv in sorted(p.support.items()):
                if not sv or not wv.get(k, 0.0) or k[0] not in S.cols_est or k[1] not in S.rows_est:
                    continue
                if p.lo.get(k, -INF) == p.up.get(k, INF):
                    continue
                yield var(r, *k), sv, wv[k], weight(r, *k)
            # l. 838-841: STCM of the young animals pulled to zero in the years without data (unweighted)
            if not p.exante_d:
                for o in sorted(S.oyani):
                    sg = p.support.get(("GROF", o), 0.0)
                    if ("STCM", o) in p.nobs and sg:
                        yield var(r, "STCM", o), sg
    return EQ.SSQS_(terms())


# --- the bounds (estimate_nuts2.gms l. 86-400; the statements in equations/estimate_nuts2.py) -----------------
#: l. 192-220: the meat and egg outputs almost fixed at the national change
MEAT_EGGS = ("PORK", "BEEF", "POUM", "SGMT", "EGGS")
#: l. 273-274: COMF and SGMF besides losfFromCoco2
LOSF_EXTRA = ("COMF", "SGMF")
#: l. 294-311: sugar beet's quota shares from 2006; the regional expert's above a trust level of 4
SUGB_FROM, SUGB_TRUST = 2006, 4.0


def nuts2_bound_sets(B: EB.BoundSets, ms: str, landuse_arto: Iterable[str]) -> EB.BoundSets:
    """B with estimate_nuts2.gms's S_ColsEst and S_RowsEst (l. 31-48; INDM for Germany, l. 55)."""
    cols = set(B.mpact) | set(B.grpc) | set(landuse_arto) | {"GROF", "LU", "UAAR", "ARTO", "LOSF"}
    if ms == "DE000000":
        cols.add("INDM")
    rows = {o for a, o in B.pact_to_o if a in B.mpact}
    rows |= {i for a, i in B.pact_to_i if a in B.maact and a not in B.fix_yai and i in B.iyani}
    rows |= set(B.feed) | set(B.reqst) | {"LEVL"}
    return dataclasses.replace(B, cols_est=cols, rows_est=rows)


def bounds(regions: Dict[str, EB.BoundData], B: EB.BoundSets, eff: float, ms_step3: Dict[K2, float],
           ms_pd: Callable, ms_estp: Dict[K2, float], losf_coco2: Iterable[str], fodf_map: Iterable[Tuple[str, str]],
           cropc_to_g: Iterable[Tuple[str, str]],
           regional_expert: Optional[Dict[str, Dict[K2, float]]] = None,
           regional_trust: Optional[Dict[str, Dict[K2, float]]] = None):
    """lo, up per region ({region: {(col, row): bound}}) and the observation flags estimate_nuts2.gms adds
    ({region: set of (col, row)}): fix_est.gms for each region (estimate_bounds.bounds with region_of set and B's
    S_ColsEst / S_RowsEst those of l. 31-48), then l. 92-400. ms_step3: the member state's result (relative
    requirements, as the bounds); ms_pd: its p_data; ms_estp: its estP (the fodder loss rates); losf_coco2: the products
    whose losses COCO2 sets (load_coco1_data.gms l. 84-85); fodf_map: FEED_TO_O pairs (FODDI, FODDO); cropc_to_g:
    CROPC_TO_G pairs (crop, crop group);
    regional_expert / regional_trust: the regions' Expert supports and trust levels (P_Result "Expert",
    p_ExpertSupprt "TrustLevl"). The statements' arithmetic is in capri_mod/pipeline/captrd/equations/estimate_nuts2.py,
    each function quoting its GAMS; this function holds their domains and their order. The lines cited below are
    estimate_nuts2.gms's."""
    out_lo, out_up, add_nobs = {}, {}, {}
    fodf_map = sorted(set(fodf_map))
    c2g = sorted((c, g) for c, g in set(cropc_to_g) if c in B.mcact)

    for r, d in sorted(regions.items()):
        lo, up = EB.bounds(d, B, eff)
        LO = lambda k: lo.get(k, -INF)                                                     # noqa: E731
        UP = lambda k: up.get(k, INF)                                                      # noqa: E731
        rng = lambda k: UP(k) - LO(k) if (UP(k) < INF or LO(k) > -INF) else INF            # noqa: E731
        pd = d.pd
        nobs = lambda c, w: pd(c, w, "nObs") != 0                                          # noqa: E731
        R = lambda rp, c, w: d.res.get(rp, {}).get((c, w), 0.0)                             # noqa: E731
        M3 = lambda c, w: ms_step3.get((c, w), 0.0)                                         # noqa: E731
        nyr = d.year - d.ord_bas
        new_nobs = set()
        chg = lambda c, w: (M3(c, w), ms_pd(c, w, "BASM"), pd(c, w, "BASM"))               # noqa: E731

        cols, rows = sorted(B.cols_est), sorted(B.rows_est)

        # l. 92-125: activity levels
        for c in cols:
            k = (c, "LEVL")
            if pd(c, "LEVL", "BASM") and rng(k) and ms_pd(c, "LEVL", "BASM"):
                up[k] = NB.V_EstV_up_LEVL(*chg(c, "LEVL"), nyr)
        for g in sorted(B.grpc):
            if pd(g, "LEVL", "BASM"):
                up[(g, "LEVL")] = NB.V_EstV_up_GRPC([UP((c, "LEVL")) for c, gg in c2g if gg == g and nobs(c, "LEVL")])
        for c in cols:
            k = (c, "LEVL")
            if pd(c, "LEVL", "BASM") and rng(k) and R("Expert", c, "LEVL"):
                up[k] = NB.V_EstV_up_LEVL_expert(UP(k), R("Expert", c, "LEVL"))
        for c in cols:
            k = (c, "LEVL")
            if pd(c, "LEVL", "BASM") and rng(k) and ms_pd(c, "LEVL", "BASM"):
                lo[k] = NB.V_EstV_lo_LEVL(*chg(c, "LEVL"), nyr)
        for c in cols:
            k = (c, "LEVL")
            if pd(c, "LEVL", "BASM") and rng(k) and R("Expert", c, "LEVL"):
                lo[k] = NB.V_EstV_lo_LEVL_expert(LO(k), R("Expert", c, "LEVL"))
        for g in sorted(B.grpc):
            if pd(g, "LEVL", "BASM"):
                lo[(g, "LEVL")] = NB.V_EstV_lo_GRPC([LO((c, "LEVL")) for c, gg in c2g if gg == g and nobs(c, "LEVL")])
        io = {(a, w) for a, w in B.pact_to_io if a in B.mpact}
        feed = set(B.feed)

        # l. 131-143: the coefficients' upper bounds
        for a, w in sorted(io):
            if w in B.rows_est and ms_pd(a, w, "BASM") and pd(a, w, "BASM") and w not in feed and w != "STRA":
                k = (a, w)
                up[k] = NB.V_EstV_up_IO(LO(k), UP(k), *chg(a, w), nyr)

        # l. 145-155: straw feed
        for a in sorted(B.maact):
            if (ms_pd(a, "FSTR", "BAS") or M3(a, "FSTR")) and pd("GROF", "STRA", "BAS"):
                new_nobs.add((a, "FSTR"))
                lo_f, up_f = NB.V_EstV_FSTR(ms_pd(a, "FSTR", "BAS"), M3(a, "FSTR"), pd(a, "FSTR", "BAS"), UP((a, "FSTR")))
                up[(a, "FSTR")] = up_f
                lo[(a, "FSTR")] = lo_f

        # l. 160-165: the coefficients' lower bounds
        for a, w in sorted(io):
            if w in B.rows_est and ms_pd(a, w, "BASM") and pd(a, w, "BASM") and w not in feed:
                k = (a, w)
                lo[k] = NB.V_EstV_lo_IO(LO(k), UP(k), *chg(a, w))

        # l. 169-177: NoYieldDrop yields
        for a, w in sorted(B.pact_to_y):
            if a in B.mpact and a in B.noyielddrop and w in B.rows_est and ms_pd(a, w, "BASM") and pd(a, w, "BASM"):
                lo[(a, w)], up[(a, w)] = NB.V_EstV_NoYieldDrop(*chg(a, w), nyr)
        nob = lambda c, w: nobs(c, w) or (c, w) in new_nobs                                 # noqa: E731

        # l. 182-187
        for a in sorted(B.mpact):
            for w in rows:
                k = (a, w)
                if ms_pd(a, w, "BASM") > 0 and nob(a, w):
                    lo[k] = NB.V_EstV_lo_floor(LO(k))
            for f in sorted(feed):
                if ms_pd(a, f, "BAS") > 0 and not pd(a, f, "BAS"):
                    lo[(a, f)] = NB.V_EstV_lo_zero()
            for w in rows:
                if M3(a, w) == 0:
                    lo[(a, w)] = NB.V_EstV_lo_zero()

        # l. 192-220: meat and eggs
        for a in sorted(B.maact):
            for o in MEAT_EGGS:
                if nob(a, o):
                    lo[(a, o)], up[(a, o)] = NB.V_EstV_MEAT_EGGS(*chg(a, o))

        # l. 222-225
        for a in sorted(B.mpact):
            for w in rows:
                if ms_pd(a, w, "BASM") > 0 and M3(a, w) and nob(a, w):
                    lo[(a, w)] = NB.V_EstV_lo_floor(LO((a, w)))

        # l. 229-230: inputs and levels fixed where the member state has no level
        for a in sorted(B.mpact):
            if not M3(a, "LEVL"):
                for w in rows:
                    if nob(a, w):
                        lo[(a, w)] = up[(a, w)] = NB.V_EstV_fx_no_ms_level()

        # l. 234-253: production from the levels' and coefficients' bounds
        for w in rows:
            acts = [a for a, ww in io if ww == w and nob(a, w) and nob(a, "LEVL")]
            if not acts:
                continue
            lo[("GROF", w)], up[("GROF", w)] = NB.V_EstV_GROF(
                [(LO((a, "LEVL")), UP((a, "LEVL")), LO((a, w)), UP((a, w))) for a in sorted(acts)])

        # l. 260-268: fodder production and use linked
        fi_s = sorted({fi for fi, _fo in fodf_map})
        fo_s = sorted({fo for _fi, fo in fodf_map})
        for fi in fi_s:
            up[("GROF", fi)] = NB.V_EstV_up_GROF_fodder(UP(("GROF", fi)),
                                                        [UP(("GROF", fo)) for ii, fo in fodf_map if ii == fi])
        for fo in fo_s:
            up[("GROF", fo)] = NB.V_EstV_up_GROF_fodder(UP(("GROF", fo)),
                                                        [UP(("GROF", fi)) for fi, oo in fodf_map if oo == fo])
        for fi in fi_s:
            lo[("GROF", fi)] = NB.V_EstV_lo_GROF_fodder(LO(("GROF", fi)),
                                                        [LO(("GROF", fo)) for ii, fo in fodf_map if ii == fi])
        for fo in fo_s:
            lo[("GROF", fo)] = NB.V_EstV_lo_GROF_fodder(LO(("GROF", fo)),
                                                        [LO(("GROF", fi)) for fi, oo in fodf_map if oo == fo])

        # l. 273-285: fodder losses at the national loss rate (the member state's estP)
        for x in sorted(set(losf_coco2) | set(LOSF_EXTRA)):
            ms_lg = (ms_estp.get(("LOSF", x), 0.0), ms_estp.get(("GROF", x), 0.0))
            if LO(("GROF", x)) > 0:
                lo[("LOSF", x)] = NB.V_EstV_lo_LOSF(LO(("GROF", x)), *ms_lg)
            if 0 < UP(("GROF", x)) < INF:
                up[("LOSF", x)] = NB.V_EstV_up_LOSF(UP(("GROF", x)), *ms_lg)

        # l. 290-345: sugar beet (the quota shares; the expert levels' rule not ported: it needs p_ExpertSupprt
        # "Absolute", not in the stored results)
        mq = (d.ms_res or {}).get("p_data", {}).get(("QUTS", "SUGB"), 0.0)
        if mq and nob("GROF", "SUGB") and d.year >= SUGB_FROM:
            ex = (regional_expert or {}).get(r, {}).get(("GROF", "SUGB"), 0.0)
            tl = (regional_trust or {}).get(r, {}).get(("GROF", "SUGB"), 0.0)
            lo_s, up_s = NB.V_EstV_GROF_SUGB(R("p_data", "QUTS", "SUGB"), M3("GROF", "SUGB"), mq, ex, tl)
            up[("GROF", "SUGB")] = up_s
            lo[("GROF", "SUGB")] = lo_s
            yl = NB.V_EstV_l_SUGB_SUGB(LO(("SUGB", "SUGB")), UP(("SUGB", "SUGB")))
            if nob("SUGB", "LEVL") and yl and abs(yl) < INF:
                lo_l, up_l = NB.V_EstV_SUGB_LEVL(LO(("GROF", "SUGB")), UP(("GROF", "SUGB")), yl)
                up[("SUGB", "LEVL")] = up_l
                lo[("SUGB", "LEVL")] = lo_l
            if (regional_trust or {}).get(r, {}).get(("SUGB", "SUGB"), 0.0) > SUGB_TRUST:
                raise NotImplementedError(f"estimate_nuts2.gms l. 336-345 for {r}: the expert sugar beet yield "
                                          f"(p_ExpertSupprt 'Absolute') is not in the port")

        # l. 350-366: ARTIF
        mb = ms_pd("ARTIF", "LEVL", "BASM")
        if mb:
            first, second = NB.V_EstV_lo_ARTIF(pd("ARTIF", "LEVL", "BASM"), M3("ARTIF", "LEVL"), mb,
                                               pd("ARTO", "LEVL", "BASM"), pd("INLW", "LEVL", "BASM"),
                                               LO(("UAAR", "LEVL")))
            lo[("ARTIF", "LEVL")] = first
            lo[("ARTIF", "LEVL")] = second

        # l. 368-369: again
        for a in sorted(B.mpact):
            if not M3(a, "LEVL"):
                for w in rows:
                    if nob(a, w):
                        lo[(a, w)] = up[(a, w)] = NB.V_EstV_fx_no_ms_level()

        # l. 377-380: the expert bounds as a last resort
        for k, v in d.res.get("expertlo", {}).items():
            if v and k[0] in B.cols_est and k[1] in B.rows_est:
                lo[k] = NB.V_EstV_expert(v)
        for k, v in d.res.get("expertup", {}).items():
            if v and k[0] in B.cols_est and k[1] in B.rows_est:
                up[k] = NB.V_EstV_expert(v)

        # l. 398-400: LOSF.STRA with data, free above zero
        new_nobs.add(("LOSF", "STRA"))
        lo[("LOSF", "STRA")], up[("LOSF", "STRA")] = NB.V_EstV_LOSF_STRA()
        out_lo[r], out_up[r], add_nobs[r] = lo, up, new_nobs
    return out_lo, out_up, add_nobs


# --- the solve (estimate_nuts2.gms l. 404-430) and its retries (est_nuts2_grid.gms, est_Nuts2_grid_openbound.gms) -----
#: est_nuts2_grid.gms l. 37: the tries with opened bounds before the estimation stops: setting captrd.nuts2_max_tries
#: openbound l. 40-43: after 60 tries the feed coefficients the member-state feed balance blocks are fixed at the support
FEED_FIX_TRIES = 60
#: l. 81-113: from 30 tries the lower bounds of the NoYieldDrop yields are opened too
NYD_OPEN_TRIES = 30
#: l. 118-124: below 25 tries the requirement functions' bounds within [min(0.1, up), 10]
REQS_TRIES = 25
#: l. 132-181: activity levels opened after 10 tries (UAAR after 20); the floor 1e-5, dropped to zero after 20 tries
LEVL_TRIES_OPEN, UAAR_TRIES_OPEN, LEVL_OPEN_FLOOR = 10, 20, 1.0e-5
#: est_nuts2_grid.gms l. 57-106: sugar beet and milk production opened after 3 tries
PROD_OPEN_TRIES = 3
#: est_nuts2_grid.gms l. 121: the set-aside activities' lower level bounds below 0.01 to zero
RSET_LO_MIN = 0.01


def _open_bounds(n, r, d, B, lo_, up_, x, at_lo, at_up, mx, reqs_m, feed_m, ms_V, nobs, support, losf_coco2,
                 lo_all, up_all, regs):
    """est_Nuts2_grid_openbound.gms for region r after the n-th failed solve (nRepeatedSolves = n). x: the levels of the
    solve; at_lo / at_up: the positions at a bound with a nonzero multiplier; mx: those with a nonzero multiplier;
    reqs_m: (activity, requirement) with REQS_'s multiplier nonzero; feed_m: the member state's (activity, feed) with
    MSFEEDI_'s nonzero; lo_all / up_all: {region: bounds} (the levels' sums over the regions). The statements'
    arithmetic is in capri_mod/pipeline/captrd/equations/est_nuts2_grid_openbound.py."""
    pd = d.pd
    LO = lambda k: lo_.get(k, -INF)                                                        # noqa: E731
    UP = lambda k: up_.get(k, INF)                                                         # noqa: E731
    ob = lambda c, w: (c, w) in nobs                                                       # noqa: E731
    M3 = lambda c, w: ms_V.get((c, w), 0.0)                                                # noqa: E731
    feed, reqst = set(B.feed), set(B.reqst)
    io = set(B.pact_to_io)

    def fx(k, v):
        lo_[k] = up_[k] = v

    # l. 40-54: the feed the member state's feed balance blocks
    for a, f in sorted(feed_m):
        if a in B.mpact and ob(a, f):
            if n > FEED_FIX_TRIES:
                fx((a, f), OB.V_EstV_fx_FEED(support.get((a, f), 0.0)))
            if LO((a, f)) == UP((a, f)):
                up_[(a, f)] = OB.V_EstV_up_FEED_fixed(LO((a, f)))

    # l. 58-79: the coefficients' upper bounds
    for a in sorted(B.mpact):
        for w in sorted(B.rows_est):
            k = (a, w)
            if not ob(a, w) or not ((a, w) in io or w in reqst) or k not in mx:
                continue
            if k in at_up or (w in reqst and (a, w) in reqs_m):
                up_[k] = OB.V_EstV_up_coef(UP(k))

    # l. 81-113: the coefficients' lower bounds
    for a in sorted(B.mpact):
        for w in sorted(B.rows_est):
            k = (a, w)
            if not ob(a, w) or not ((a, w) in io or w in reqst) or k not in mx:
                continue
            y = (a, w) in B.pact_to_y
            if not (n > NYD_OPEN_TRIES or not y or a not in B.noyielddrop or w == "COMI"):
                continue
            if k in at_lo or (w in reqst and (a, w) in reqs_m):
                lo_[k] = OB.V_EstV_lo_coef(LO(k), pd(a, w, "BASM"), w in reqst, y, w in feed)

    # l. 118-124: the requirement functions
    if n < REQS_TRIES:
        for a in sorted(B.mpact):
            for w in sorted(reqst):
                if ob(a, w):
                    lo_[(a, w)], up_[(a, w)] = OB.V_EstV_REQST(LO((a, w)), UP((a, w)))

    # l. 132-151: the activity levels
    cols = sorted(B.cols_est)
    for c in cols:
        k = (c, "LEVL")
        if ob(c, "LEVL") and k in mx and n > LEVL_TRIES_OPEN and k in at_up:
            up_[k] = OB.V_EstV_up_LEVL_open(UP(k))
    for c in cols:
        k = (c, "LEVL")
        if ob(c, "LEVL") and k in mx and n > LEVL_TRIES_OPEN and (c != "UAAR" or n > UAAR_TRIES_OPEN) and k in at_lo:
            lo_[k] = OB.V_EstV_lo_LEVL_open(LO(k), c == "UAAR")

    # l. 153-156: the levels' floor
    for c in cols:
        k = (c, "LEVL")
        if ob(c, "LEVL"):
            lo_[k] = OB.V_EstV_lo_LEVL_floor(LO(k), UP(k))

    # l. 160-174: the regions' level bounds against the member state's level
    for c in cols:
        k = (c, "LEVL")
        if not ob(c, "LEVL"):
            continue
        slo = sum(lo_all[q].get(k, -INF) for q in regs if lo_all[q].get(k, -INF) != 0)
        if M3(c, "LEVL") < slo:
            lo_[k] = OB.V_EstV_lo_LEVL_ms(LO(k), M3(c, "LEVL"), len(regs))
        sup_ = sum(up_all[q].get(k, INF) for q in regs if up_all[q].get(k, INF) != 0)
        if M3(c, "LEVL") > sup_:
            up_[k] = OB.V_EstV_up_LEVL_ms(UP(k), M3(c, "LEVL"), len(regs))

    # l. 178-181: the floor dropped after 20 tries
    for c in cols:
        k = (c, "LEVL")
        if LO(k) == LEVL_OPEN_FLOOR and n > UAAR_TRIES_OPEN and ob(c, "LEVL"):
            lo_[k] = OB.V_EstV_lo_LEVL_zero()

    # l. 186-199: production opened where blocking
    rows = sorted(B.rows_est)
    for w in rows:
        k = ("GROF", w)
        if ob("GROF", w) and k in mx and k in at_up:
            up_[k] = OB.V_EstV_up_GROF_open(UP(k))
        if ob("GROF", w) and k in mx and k in at_lo:
            lo_[k] = OB.V_EstV_lo_GROF_open(LO(k))

    # l. 204-237: production at least the levels' and coefficients' range where not blocking
    for w in rows:
        k = ("GROF", w)
        acts = [a for a in sorted(B.mpact) if (a, w) in io and ob(a, w) and ob(a, "LEVL")]
        if not ob("GROF", w) or k in mx or not acts:
            continue
        lo_[k], up_[k] = OB.V_EstV_GROF_range(LO(k), UP(k), [(LO((a, "LEVL")), UP((a, "LEVL")), LO((a, w)), UP((a, w)))
                                                             for a in acts])

    # l. 243-253: fodder production and use linked
    fpairs = sorted((i, o) for i, o in B.feed_to_o if i in B.foddi)
    for i in sorted({i for i, _o in fpairs}):
        if ob("GROF", i):
            up_[("GROF", i)] = OB.V_EstV_up_GROF_fodder(UP(("GROF", i)), [UP(("GROF", o)) for ii, o in fpairs if ii == i])
    for o in sorted({o for _i, o in fpairs}):
        if ob("GROF", o):
            up_[("GROF", o)] = OB.V_EstV_up_GROF_fodder(UP(("GROF", o)), [UP(("GROF", i)) for i, oo in fpairs if oo == o])
    for i in sorted({i for i, _o in fpairs}):
        if ob("GROF", i):
            lo_[("GROF", i)] = OB.V_EstV_lo_GROF_fodder(LO(("GROF", i)), [LO(("GROF", o)) for ii, o in fpairs if ii == i])
    for o in sorted({o for _i, o in fpairs}):
        if ob("GROF", o):
            lo_[("GROF", o)] = OB.V_EstV_lo_GROF_fodder(LO(("GROF", o)), [LO(("GROF", i)) for i, oo in fpairs if oo == o])

    # l. 255-261: the young animals at 1000 per 1000 heads; nothing where the member state has no level
    for a, i in sorted(B.pact_to_i):
        if a in B.fix_yai and i in B.iyani and ob(a, "LEVL"):
            fx((a, i), OB.V_EstV_fx_young_animals())
    for a, o in sorted(B.pact_to_o):
        if a in B.fix_yao and o in B.oyani and ob(a, "LEVL"):
            fx((a, o), OB.V_EstV_fx_young_animals())
    for a in sorted(B.mpact):
        if not M3(a, "LEVL"):
            for w in rows:
                if ob(a, w):
                    fx((a, w), OB.V_EstV_fx_no_ms_level())

    # l. 265-276: fodder losses at the member state's rate
    rng = lambda k: UP(k) - LO(k)                                                          # noqa: E731
    for o in sorted(losf_coco2):
        ms_lg = (ms_V.get(("LOSF", o), 0.0), ms_V.get(("GROF", o), 0.0))
        kg = ("GROF", o)
        if LO(kg) >= 0 and rng(kg) > 0:
            lo_[("LOSF", o)] = OB.V_EstV_lo_LOSF(LO(kg), *ms_lg)
        if 0 <= UP(kg) < INF and rng(kg) > 0:
            up_[("LOSF", o)] = OB.V_EstV_up_LOSF(UP(kg), *ms_lg)

    # l. 281-292: the fixed land, ARTIF
    for c in ("ARTO", "INLW", "KITC"):
        fx((c, "LEVL"), OB.V_EstV_fx_land(pd(c, "LEVL", "BASM")))
    mb = d.ms_pd("ARTIF", "LEVL", "BASM")
    if mb:
        lo_[("ARTIF", "LEVL")] = OB.V_EstV_lo_ARTIF(pd("ARTIF", "LEVL", "BASM"), M3("ARTIF", "LEVL"), mb,
                                                    pd("ARTO", "LEVL", "BASM"), pd("INLW", "LEVL", "BASM"),
                                                    LO(("UAAR", "LEVL")))


def _grid_again(n, r, d, B, lo_, up_, x, at_lo, at_up, mx, nobs, support, ms_V):
    """est_nuts2_grid.gms l. 42-121 after the bounds are opened: comi_bounds.gms, release_comi_yields.gms, the sugar beet
    and milk production, LOSF.STRA free, the set-aside levels' floor. x is updated where CAPTRD sets levels. The
    statements' arithmetic is in capri_mod/pipeline/captrd/equations/est_nuts2_grid.py (comi_bounds.py for
    comi_bounds.gms; release_comi_yields.gms is estimate_nlp._release_comi's)."""
    pd, res, t = d.pd, d.res, d.year
    R = lambda rp, c, w: res.get(rp, {}).get((c, w), 0.0)                                  # noqa: E731
    ob = lambda c, w: (c, w) in nobs                                                       # noqa: E731
    LO = lambda k: lo_.get(k, -INF)                                                        # noqa: E731
    UP = lambda k: up_.get(k, INF)                                                         # noqa: E731

    def fx(k, v):
        lo_[k] = up_[k] = v

    EB._comi(d, B, lo_, up_, LO, UP, ob, pd, R, lambda c, w: R("Support", c, w), fx, t)
    NLP._release_comi(n, B, lo_, up_, ob, at_lo, at_up)

    # l. 53-69: the sugar beet yield's level mid-range; sugar beet production opened after 3 tries
    if ob("SUGB", "SUGB"):
        x[("SUGB", "SUGB")] = GR.V_EstV_l_SUGB_SUGB(LO(("SUGB", "SUGB")), UP(("SUGB", "SUGB")))
    k = ("GROF", "SUGB")
    if x.get(("SUGB", "SUGB")) and ob(*k) and n > PROD_OPEN_TRIES and k in mx:
        if k in at_lo:
            lo_[k] = GR.V_EstV_lo_GROF_tries(LO(k), n)
        if k in at_up:
            up_[k] = GR.V_EstV_up_GROF_tries(UP(k), n)

    # l. 71-94: sugar beet production at the quota share, its area from production over the yield
    mq = (d.ms_res or {}).get("p_data", {}).get(("QUTS", "SUGB"), 0.0)
    yl = x.get(("SUGB", "SUGB"), 0.0)
    if mq and t >= SUGB_FROM and yl and ob("GROF", "SUGB"):
        x[k] = GR.V_EstV_l_GROF_SUGB(R("p_data", "QUTS", "SUGB"), ms_V.get(k, 0.0), mq)
    if mq and t >= SUGB_FROM and yl and ob("SUGB", "LEVL"):
        lo_l, up_l, l_l = GR.V_EstV_SUGB_LEVL(LO(k), UP(k), x.get(k, 0.0), yl)
        up_[("SUGB", "LEVL")] = up_l
        lo_[("SUGB", "LEVL")] = lo_l
        x[("SUGB", "LEVL")] = l_l

    # l. 96-106: milk production opened after 3 tries
    k = ("GROF", "COMI")
    if ob(*k) and n > PROD_OPEN_TRIES and k in mx:
        if k in at_lo:
            lo_[k] = GR.V_EstV_lo_GROF_tries(LO(k), n)
        if k in at_up:
            up_[k] = GR.V_EstV_up_GROF_tries(UP(k), n)

    # l. 109-110, 121
    lo_[("LOSF", "STRA")], up_[("LOSF", "STRA")] = GR.V_EstV_LOSF_STRA()
    for a in sorted(B.rset):
        if LO((a, "LEVL")) < RSET_LO_MIN:
            lo_[(a, "LEVL")] = GR.V_EstV_lo_RSET()


def _phase1_ipopt(ph1, x, gv, lb, ub, lbg, ubg, m, nk, regs, log):
    """The least-infeasibility problem solved by IPOPT from the infeasible solve's point (captrd.nlp_infeasible_marginals
    = "phase1", as estimate_nlp.solve)."""
    p1 = ph1(x0=np.concatenate([x, np.maximum(gv - ubg, 0.0), np.maximum(lbg - gv, 0.0)]),
             lbx=np.concatenate([lb, np.zeros(2 * m)]), ubx=np.concatenate([ub, np.full(2 * m, INF)]),
             lbg=lbg, ubg=ubg, p=np.concatenate([x, np.maximum(1.0, np.abs(x))]))
    if ph1.stats()["return_status"] in NLP.SOLVER_ERRORS:
        raise RuntimeError(f"m_trendNT2 {regs}: phase 1 solver error {ph1.stats()['return_status']}")
    z = np.array(p1["x"]).ravel()
    log.append(f"    phase 1: {ph1.stats()['return_status']}, sum of infeasibilities {float(p1['f']):.3e}")
    return z[:nk], np.array(p1["lam_x"]).ravel()[:nk], np.array(p1["lam_g"]).ravel()

def solve(points: Dict[str, E.Point], D: Dict[str, EB.BoundData], B: EB.BoundSets, ms_nobs: set,
          ms_V: Dict[K2, float], S: E.Sets, split_acts_lo: Iterable[str], wvar: Dict[str, Dict[K2, float]],
          basm_levl: Dict[str, Dict[str, float]], losf_coco2: Iterable[str],
          start: Optional[Dict[str, Dict[K2, float]]] = None, opts: Optional[dict] = None,
          log: Optional[List[str]] = None) -> NLP.Result:
    """m_trendNT2 for the regions of one member state with est_nuts2_grid.gms's retries: after an infeasible solve the
    bounds are opened (est_Nuts2_grid_openbound.gms, comi_bounds.gms, release_comi_yields.gms, the sugar beet and milk
    production) and the model solved again, up to captrd.nuts2_max_tries times.

    points: {region: Point} with the support (relative requirements), the data (nobs, with the flags bounds adds) and
    lo / up (bounds); D: {region: BoundData} (region_of set); B, S: the NUTS 2 sets (nuts2_bound_sets); wvar: {region:
    wVarErr}; basm_levl: {region: {activity: LEVL BASM}}; losf_coco2: losfFromCoco2 with COMF and SGMF; start: {region:
    estP} (none: the supports, l. 383-391). The result's keys are (region, col, row).

    Departures (the solver), as estimate_nlp.solve: IPOPT; a bound is binding within captrd.nlp_at_bound_tol with a
    multiplier beyond captrd.nlp_marginal_tol, taken from the least-infeasibility problem after an infeasible solve; a
    position in no equation and not in the objective is held at its start. CONOPT's 'iterusd eq 0' conditions and its
    'feasible but not optimal' retries (l. 200-215) have no IPOPT counterpart and are not ported."""
    o = dict(NLP._settings())
    o.update(opts or {})
    max_tries = int(o["nuts2_max_tries"] if "nuts2_max_tries" in o else current_settings().get("captrd.nuts2_max_tries"))
    regs = sorted(points)
    start = start or {}
    log = log if log is not None else []
    keys: List[K3] = []
    idx: Dict[K3, int] = {}
    syms = []

    def var(r, c, w):
        k = (r, c, w)
        if k not in idx:
            idx[k] = len(keys)
            keys.append(k)
            syms.append(ca.SX.sym(f"{r}.{c}.{w}"))
        return syms[idx[k]]

    # l. 383-391: the levels of the positions with data: estP if the region has one, else the support
    level = {r: (dict(start[r]) if start.get(r) else
                 {k: v for k, v in points[r].support.items() if k in points[r].nobs}) for r in regs}
    lo_r = {r: dict(points[r].lo) for r in regs}
    up_r = {r: dict(points[r].up) for r in regs}

    # the model: the bounds enter the equations' conditions only through MSGROF_ (a coefficient not fixed), which the
    # initial bounds decide; the variables' bounds change between tries, the model does not
    res = residuals(points, ms_nobs, ms_V, S, B.foddi, B.rset, split_acts_lo, var=var, levels=level)
    f = objective(points, S, var, wvar, basm_levl)
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    keys = [keys[i] for i in order]
    syms = [syms[i] for i in order]
    X = ca.vertcat(*syms)
    G = ca.vertcat(*[q[3] for q in res])
    m = int(G.shape[0])
    lbg = np.array([0.0 if q[2] in "EG" else -INF for q in res])
    ubg = np.array([0.0 if q[2] in "EL" else INF for q in res])
    gfun = ca.Function("g", [X], [G])
    dep = np.array(ca.which_depends(G, X, 1, False), dtype=bool) | np.array(ca.which_depends(f, X, 1, False), dtype=bool)

    ipopt = {"ipopt.print_level": 0, "print_time": 0, "ipopt.tol": float(o["nlp_tol"]),
             "ipopt.max_iter": int(o["nlp_max_iter"]), "ipopt.fixed_variable_treatment": "make_constraint"}
    solver = ca.nlpsol("m_trendNT2", "ipopt", {"x": X, "f": f, "g": G}, ipopt)
    slp = str(o["nlp_infeasible_marginals"]) == "slp"
    jfun = ca.Function("J", [X], [ca.jacobian(G, X)]) if slp else None
    sp, sn = ca.SX.sym("sp", m), ca.SX.sym("sn", m)
    xh, xsc = ca.SX.sym("xhat", X.shape[0]), ca.SX.sym("xscale", X.shape[0])
    f1 = ca.sum1(sp) + ca.sum1(sn) + float(o["nlp_phase1_proximity"]) * ca.sumsqr((X - xh) / xsc)
    ph1 = ca.nlpsol("m_trendNT2_phase1", "ipopt",
                    {"x": ca.vertcat(X, sp, sn), "p": ca.vertcat(xh, xsc), "f": f1, "g": G - sp + sn}, ipopt)

    # the equations whose multipliers open bounds: REQS_ (region, activity, requirement), MSFEEDI_ (activity, feed)
    reqs_i = [(i, q[1]) for i, q in enumerate(res) if q[0] == "REQS_"]
    feed_i = [(i, q[1]) for i, q in enumerate(res) if q[0] == "MSFEEDI_"]
    tol_at, tol_m = float(o["nlp_at_bound_tol"]), float(o["nlp_marginal_tol"])

    x0 = np.array([level[r].get((c, w), 0.0) for r, c, w in keys])
    status, sol = "", None
    for n in range(max_tries + 1):
        lb = np.array([lo_r[r].get((c, w), -INF) for r, c, w in keys])
        ub = np.array([up_r[r].get((c, w), INF) for r, c, w in keys])
        xs = np.clip(x0, np.where(np.isfinite(lb), lb, -1e30), np.where(np.isfinite(ub), ub, 1e30))
        lb, ub = np.where(dep, lb, xs), np.where(dep, ub, xs)
        sol = solver(x0=xs, lbx=lb, ubx=ub, lbg=lbg, ubg=ubg)
        x = np.array(sol["x"]).ravel()
        gv = np.array(gfun(x)).ravel()
        viol = float(np.maximum(np.maximum(lbg - gv, gv - ubg), 0.0).max()) if m else 0.0
        status = solver.stats()["return_status"]
        log.append(f"try {n}: {status}, max. infeasibility {viol:.2e}, SSQ {float(sol['f']):.6g}")
        if status in NLP.SOLVER_ERRORS:
            raise RuntimeError(f"m_trendNT2 {regs}: solver error {status} at try {n}")
        ok = viol <= float(o["nlp_tolinfeas"]) and status in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
        if ok or n == max_tries:
            break

        # the least-infeasibility point and its multipliers
        nk = len(keys)
        x_ip, use_slp = x, slp
        if slp:
            # CONOPT's phase 1 from the solve's start (estimate_nlp.phase1_slp), polished, the marginals at a vertex
            x, f1, its = NLP.phase1_slp(gfun, jfun, xs, lb, ub, lbg, ubg, int(o["nlp_phase1_slp_max_iter"]),
                                        float(o["nlp_phase1_slp_radius"]), trace=o.get("slp_trace"))
            log.append(f"    phase 1 (SLP): {its} iterations, sum of infeasibilities {f1:.3e}")
            # CONOPT goes on to optimise from a feasible phase-1 point: solved again from it, the bounds unchanged
            if NLP._max_violation(np.array(gfun(x)).ravel(), lbg, ubg) <= float(o["nlp_tolinfeas"]):
                sol = solver(x0=x, lbx=lb, ubx=ub, lbg=lbg, ubg=ubg)
                x2 = np.array(sol["x"]).ravel()
                viol2 = NLP._max_violation(np.array(gfun(x2)).ravel(), lbg, ubg)
                status = solver.stats()["return_status"]
                log.append(f"    from the feasible phase-1 point: {status}, max. infeasibility {viol2:.2e}")
                ok = viol2 <= float(o["nlp_tolinfeas"]) and status in ("Solve_Succeeded", "Solved_To_Acceptable_Level")
                if ok:
                    break
                # as estimate_nlp.solve: IPOPT cannot optimise from it, the IPOPT phase 1 for this try
                x, use_slp = x_ip, False
                log.append("    phase 1: feasible but not solvable from it: the IPOPT phase 1 for this try")
        if use_slp:
            x_slp = x
            x, lam, lam_g = _phase1_ipopt(ph1, x, np.array(gfun(x)).ravel(), lb, ub, lbg, ubg, m, nk, regs, log)
            if NLP._infeasibility(np.array(gfun(x)).ravel(), lbg, ubg) > f1:
                x = x_slp
                log.append("    phase 1: the SLP point kept")
            lam, lam_g = NLP.phase1_marginals(gfun, jfun, x, lb, ub, lbg, ubg, tol_at)
        else:
            x, lam, lam_g = _phase1_ipopt(ph1, x, np.array(gfun(x)).ravel(), lb, ub, lbg, ubg, m, nk, regs, log)
        at_lo, at_up = NLP._binding(keys, x, lam, lb, ub, tol_at, tol_m)
        mx = {k for i, k in enumerate(keys) if abs(lam[i]) > tol_m and lb[i] != ub[i]}
        feed_m = {ix for i, ix in feed_i if abs(lam_g[i]) > tol_m}

        # the bounds opened region by region (CAPTRD's statements run over all Rest at once: the level sums of
        # l. 118-133 see the bounds before this try's openings)
        lo_prev = {r: dict(lo_r[r]) for r in regs}
        up_prev = {r: dict(up_r[r]) for r in regs}
        xr = {r: {} for r in regs}
        for i, (r, c, w) in enumerate(keys):
            xr[r][(c, w)] = float(x[i])
        for r in regs:
            pick = lambda dct: {(c, w): v for (rr, c, w), v in dct.items() if rr == r}     # noqa: E731
            alo, aup = pick(at_lo), pick(at_up)
            mr = {(c, w) for rr, c, w in mx if rr == r}
            reqs_m = {(ix[1], ix[2]) for i, ix in reqs_i if ix[0] == r and abs(lam_g[i]) > tol_m}
            _open_bounds(n, r, D[r], B, lo_r[r], up_r[r], xr[r], alo, aup, mr, reqs_m, feed_m, ms_V, points[r].nobs,
                         points[r].support, losf_coco2, lo_prev, up_prev, regs)
            _grid_again(n, r, D[r], B, lo_r[r], up_r[r], xr[r], alo, aup, mr, points[r].nobs, points[r].support, ms_V)

        # the next solve starts at this one's levels (no estP of the year for the regions)
        x0 = np.array([xr[r].get((c, w), 0.0) for r, c, w in keys])

    x = np.array(sol["x"]).ravel()
    lo_ = {(r, c, w): v for r in regs for (c, w), v in lo_r[r].items()}
    up_ = {(r, c, w): v for r in regs for (c, w), v in up_r[r].items()}
    return NLP.Result({k: float(x[i]) for i, k in enumerate(keys)}, float(sol["f"]), ok, n + 1, status, lo_, up_)


# --- rem_tiny.gms (included by estimate_nuts2.gms after storing the regions' step3) --------------------------------------
#: l. 19-20: activity levels at or below 1e-6 are removed
TINY_LEVL = 1.0e-6
#: l. 35-38: fodder losses recomputed where the fodder production changed by more than 0.1%; the denominator's guard
LOSF_CHANGE, LOSF_EPS = 0.001, 1.0e-8


def rem_tiny(step3: Dict[K2, float], nobs: set, S: E.Sets, foddi: Iterable[str], aact: Iterable[str],
             grpr: Iterable[str], rows_lab: Iterable[str], outputs: Iterable[str], ms_estp: Dict[K2, float]) \
        -> Dict[K2, float]:
    """rem_tiny.gms for one region: tiny levels and their coefficients removed, production recomputed from levels and
    coefficients, fodder losses at the member state's loss rate where fodder production changed, losses not above
    production, fodder deliveries re-aggregated, fodder feed removed where none is delivered. step3: the region's result
    (P_Result "Step3", only positions with data); nobs: its observed positions; S: the NUTS 2 sets; ms_estp: the
    member state's estP (the loss rates); foddi: FODDI (FODDO are their FEED_TO_O outputs)."""
    s = dict(step3)
    n = lambda c, w: (c, w) in nobs                                                        # noqa: E731
    g = lambda c, w: s.get((c, w), 0.0)                                                    # noqa: E731
    mpact = sorted(S.mpact)

    # l. 19-20: tiny levels
    for a in mpact:
        if n(a, "LEVL") and g(a, "LEVL") <= TINY_LEVL:
            s[(a, "LEVL")] = 0.0

    # l. 24-25: the coefficients of a removed level
    for a in mpact:
        if not g(a, "LEVL"):
            for w in sorted(S.rows_est):
                if n(a, w):
                    s[(a, w)] = 0.0

    # l. 29-34: production from levels and coefficients (FODDO's before kept)
    foddi = set(foddi)
    fodd_pairs = sorted((i, o) for i, o in S.feed_to_o if i in foddi)
    foddo = sorted({o for _i, o in fodd_pairs})
    before = {o: g("GROF", o) for o in foddo}
    skip = set(grpr) | set(rows_lab)
    for w in sorted(S.rows_est):
        if n("GROF", w) and w not in skip:
            s[("GROF", w)] = sum(g(a, w) * g(a, "LEVL") for a, o in sorted(S.pact_to_io)
                                 if o == w and a in mpact and n(a, w) and n(a, "LEVL")) * PER_1000

    # l. 35-41: fodder losses at the member state's rate where fodder production changed
    for o in foddo:
        if o == "STRA" or not n("GROF", o):
            continue
        if abs(before[o] - g("GROF", o)) / (before[o] + LOSF_EPS) > LOSF_CHANGE:
            m_g = ms_estp.get(("GROF", o), 0.0)
            rate = ms_estp.get(("LOSF", o), 0.0) / m_g if m_g else 0.0
            s[("LOSF", o)] = g("GROF", o) * rate

    # l. 45-46: losses not above production
    for o in sorted(set(outputs)):
        if ("LOSF", o) in s or ("GROF", o) in s:
            s[("LOSF", o)] = min(g("GROF", o), g("LOSF", o))

    # l. 52-53: fodder deliveries
    for i in sorted({i for i, _o in fodd_pairs}):
        s[("GROF", i)] = sum(g("GROF", o) - g("LOSF", o) for ii, o in fodd_pairs if ii == i)

    # l. 57: no fodder feed without fodder delivered
    for a in sorted(set(aact)):
        for i in sorted({i for i, _o in fodd_pairs}):
            if not g("GROF", i) and (a, i) in s:
                s[(a, i)] = 0.0
    return {k: v for k, v in s.items() if v or k in step3}

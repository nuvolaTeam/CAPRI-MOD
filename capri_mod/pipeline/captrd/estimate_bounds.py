"""The bounds of CAPTRD's member-state estimation m_trendMS for one member state and ex-ante year: estimate_ms.gms
l. 53-68 (the standard bounds), captrd/fix_est.gms (with comi_bounds.gms and biofuel_bounds.gms, which it includes),
then estimate_ms.gms l. 78-162 (CAPRI star 3.0), in CAPTRD's order of statements; the bound-widening of infeasible
solves (estimate_ms.gms l. 222-420) is not part of it. Each statement's arithmetic is a named function quoting its GAMS
in capri_mod/pipeline/captrd/equations (estimate_ms.py, fix_est.py, comi_bounds.py, biofuel_bounds.py); bounds()
holds the statements' domains, the loops over the sets and their order.

V_EstV is a free variable (equations.gms l. 28-32): a position no statement bounds keeps (-inf, +inf). The requirement
rows (ReqsT) are in the estimation's relative form (estimate_ms.requirements_relative), as their supports.

Inputs (CAPTRD's symbols, for the member state):
  pd(col, row, stat)  p_data's statistics: nObs, BAS, BASM, BAST, BSY, Const, Slope (and BASM of DRMN, DRMX,
                      N_EXPT, EDAYS)
  res[respos]         P_Result of the year: Support, coco, Expert, expertlo, expertup, p_data (the exogenous series)
  prev                the ex-ante year before (BeFore), its estP and Step3, and whether it is an ExAnteD year
  the time ordinals   OrdT of the year, BAS, BAST (Lst_exPostT - 1), Lst_exAnte, Fst_exAnte, Lst_exPostT, %lst_dgagri%
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Set, Tuple

from capri_mod.csvio import read_csv
from capri_mod.pipeline.captrd.equations import biofuel_bounds as BF
from capri_mod.pipeline.captrd.equations import comi_bounds as CB
from capri_mod.pipeline.captrd.equations import estimate_ms as EM
from capri_mod.pipeline.captrd.equations import fix_est as FE

K2 = Tuple[str, str]
INF = float("inf")

#: captrd.gms l. 289: p_refMlkYld, comi_bounds.gms's reference milk yield
REF_MILK_YIELD = 7000.0
#: captrd.gms l. 356-362: processing yields of the oilseeds (cake and oil), Proc_Yields
PROC_YIELDS = {"SOYC": 0.80, "SOYO": 0.18, "RAPC": 0.60, "RAPO": 0.40, "SUNC": 0.55, "SUNO": 0.45}


@dataclass
class BoundSets:
    """The sets of the bound statements (sets.gms, sets_captrd.gms)."""
    mpact: Set[str]
    maact: Set[str]
    mcact: Set[str]
    cact: Set[str]
    grpc: Set[str]
    grpr: Set[str]
    cols_est: Set[str]
    rows_est: Set[str]
    pact_to_io: Set[K2]
    pact_to_y: Set[K2]
    pact_to_o: Set[K2]
    pact_to_i: Set[K2]
    oyani: Set[str]
    iyani: Set[str]
    feed: Set[str]
    foddi: Set[str]
    feed_to_o: Set[K2]
    reqst: Set[str]
    reqste: Set[str]
    breed_act: Set[str]
    cows_act: Set[str]
    noyielddrop: Set[str]
    crops_max_yields: Set[str]
    cere: Set[str]
    fixyield: Set[str]
    fix_yai: Set[str]
    fix_yao: Set[str]
    aact365: Set[str]
    grsact: Set[str]
    meat: Set[str]
    mlkcnt: Set[str]
    mlkseco: Set[str]
    seco: Set[str]
    seco_biof: Set[str]
    bio_stock: Set[str]
    mrkbalee: Set[str]
    rset: Set[str]
    dact_to_pact: Set[K2]
    o: Set[str]                             # O, the outputs
    uaar_acts: Set[str]                     # P_T_ActAgg(., "UAAR")
    reqfcnlim: Dict[Tuple[str, str, str], float] = field(default_factory=dict)


def read_bound_sets(sets_dir: Path = None, dat_dir: Path = None) -> BoundSets:
    """BoundSets from capri_data/pipeline/captrd/sets (build_captrd_sets.py) and dat/agriprod_p_reqfcnlim.csv."""
    from capri_mod.pipeline.captrd import estimate_ms as _E
    from capri_mod.pipeline.captrd import prepare as _P
    sets_dir = _P.SETS_DIR if sets_dir is None else sets_dir
    dat_dir = _P.DAT_DIR if dat_dir is None else dat_dir
    S = _E.read_sets(sets_dir)

    def one(n):
        return _E.OSet(read_csv(sets_dir / f"{n}.csv", keep_default_na=False, dtype=str).d0)

    def two(n):
        d = read_csv(sets_dir / f"{n}.csv", keep_default_na=False, dtype=str)
        return _E.OSet(zip(d.d0, d.d1))
    agg = two("p_t_actagg")
    rl = read_csv(dat_dir / "agriprod_p_reqfcnlim.csv", keep_default_na=False)
    return BoundSets(mpact=S.mpact, maact=S.maact, mcact=S.mcact, cact=one("cact"), grpc=S.grpc, grpr=S.grpr,
                     cols_est=S.cols_est, rows_est=S.rows_est, pact_to_io=S.pact_to_io, pact_to_y=S.pact_to_y,
                     pact_to_o=S.pact_to_o, pact_to_i=S.pact_to_i, oyani=S.oyani, iyani=S.iyani, feed=S.feed,
                     foddi=one("foddi"), feed_to_o=S.feed_to_o, reqst=S.reqst, reqste=one("reqste"),
                     breed_act=S.breed_act, cows_act=one("cowsact"), noyielddrop=one("noyielddrop"),
                     crops_max_yields=one("cropswithmaximumyields"), cere=one("cere"), fixyield=one("fixyield"),
                     fix_yai=one("fix_yai"), fix_yao=one("fix_yao"), aact365=one("aactwith365days"),
                     grsact=one("grsact"), meat=S.meat, mlkcnt=S.mlkcnt, mlkseco=S.mlkseco, seco=one("seco"),
                     seco_biof=S.seco_biof, bio_stock=S.bio_stock, mrkbalee=S.mrkbalee, rset=S.rset,
                     dact_to_pact=two("dact_to_pact"), o=one("o"),
                     uaar_acts=_E.OSet(a for a, g in agg if g == "UAAR"),
                     reqfcnlim={(a, w, b): float(v) for a, w, b, v in zip(rl.act, rl.row, rl.bound, rl.value)})


@dataclass
class BoundData:
    ms: str
    year: int
    pd: Callable[[str, str, str], float]
    res: Dict[str, Dict[K2, float]]
    ord_bas: int
    ord_bast: int
    lst_exante: int
    fst_exante: int
    lst_expostt: int
    lst_dgagri: int
    exante_d: bool
    west: bool                              # MS_TO_RMSAGG(MS, CurEUWestAgg)
    east: bool                              # MS_TO_RMSAGG(MS, CurEUEastAgg)
    wba7: bool = False                      # R_NUTS0_WBA7
    bur: bool = False                       # R_NUTS0_BUR
    eu28: bool = True                       # MAP_RR("EU028000", MS)
    setr_west: float = 0.0                  # SUM(GRCU, p_data(CurEUWestAgg, GRCU, "SETR", year))
    prev: Optional[int] = None              # BeFore(year, prev)
    prev_exante_d: bool = False
    estp_prev: Dict[K2, float] = field(default_factory=dict)
    step3_prev: Dict[K2, float] = field(default_factory=dict)
    const_slope: Dict[K2, float] = field(default_factory=dict)   # Const + Slope of the requirements (nonzero)
    nuts2_with_data: Dict[str, int] = field(default_factory=dict)  # activity -> its NUTS2 regions with LEVL data
    # a NUTS 2 region of the member state region_of (estimate_nuts2.gms includes fix_est.gms for Rest = the regions):
    # its member state's p_data and P_Result of the year, which comi_bounds.gms reads as MS; None for a member state
    region_of: Optional[str] = None
    ms_pd: Optional[Callable[[str, str, str], float]] = None
    ms_res: Optional[Dict[str, Dict[K2, float]]] = None


def bounds(d: BoundData, B: BoundSets, eff: float, artif_as_coded: Optional[bool] = None):
    """lo, up: {(col, row): bound} of every position a statement bounds (others free). eff: the requirement
    functions' feeding efficiency factor of the year (0.998^(year - 2000)). artif_as_coded (setting
    captrd.artif_upper_bound_as_coded; FIX-7): ARTIF's upper bound with fix_est.gms l. 810's parenthesis as coded
    (the year as the exponent) or, the default, as its comment states it (the years since the base). The statements'
    arithmetic is in capri_mod/pipeline/captrd/equations (estimate_ms.py, fix_est.py, comi_bounds.py,
    biofuel_bounds.py), each function quoting its GAMS; this function holds their domains and their order."""
    if artif_as_coded is None:
        from capri_mod.settings import current as _settings
        artif_as_coded = bool(_settings().get("captrd.artif_upper_bound_as_coded"))
    lo: Dict[K2, float] = {}
    up: Dict[K2, float] = {}
    LO = lambda k: lo.get(k, -INF)                                         # noqa: E731
    UP = lambda k: up.get(k, INF)                                          # noqa: E731
    pd = d.pd
    n = lambda c, w: pd(c, w, "nObs") != 0                                  # noqa: E731
    R = lambda rp, c, w: d.res.get(rp, {}).get((c, w), 0.0)                 # noqa: E731
    sup = lambda c, w: R("Support", c, w)                                  # noqa: E731
    coco = lambda c, w: R("coco", c, w) != 0                                # noqa: E731
    t = d.year
    exante_t = not d.exante_d
    span_bas = d.lst_exante - d.ord_bas
    x_bas = max(d.ord_bas + 1, t) - d.ord_bas          # MAX(OrdT("BAS")+1, OrdT(ExAnte)) - OrdT("BAS")

    def fx(k, v):
        lo[k] = v
        up[k] = v

    def bast_or_basm(c, w):
        b = pd(c, w, "BAST")
        return (b, d.ord_bast) if b else (pd(c, w, "BASM"), d.ord_bas)

    cols, rows = B.cols_est, B.rows_est
    posn = [(c, w) for c in sorted(cols) for w in sorted(rows)]
    # --- estimate_ms.gms l. 53-68 (the member state's estimation only)
    for c, w in (posn if d.region_of is None else ()):
        if n(c, w):
            up[(c, w)] = EM.V_EstV_up_std()
        s_ = sup(c, w)
        if n(c, w) or s_:
            lo[(c, w)] = EM.V_EstV_lo_std(c, w, s_, pd("CSSP", w, "BASM"), pd(c, "OCRO", "BASM"), pd(c, "OANI", "BASM"),
                                          pd("OCRO", w, "BASM"), pd("OANI", w, "BASM"))
    # --- fix_est.gms l. 25-63: input and output coefficients
    if exante_t:
        for a in sorted(B.mpact & cols):
            for w in sorted(rows):
                if (a, w) not in B.pact_to_io or not n(a, w) or coco(a, w):
                    continue
                base, ref = bast_or_basm(a, w)
                lo[(a, w)], up[(a, w)] = FE.V_EstV_IO(base, t - ref, d.lst_exante - ref, w, a in B.uaar_acts)
        # l. 70-74: young animals, with expert levels up to 2020
        for a in sorted(B.mpact):
            if R("Expert", a, "LEVL") and t <= 2020:
                for o in sorted(B.oyani):
                    _rescale(lo, up, (a, o), FE.V_EstV_OYANI_expert)
        # l. 79-86: cows' young animal inputs
        for a in sorted(B.cows_act):
            if R("BASM", a, "LEVL") and (R("BASM", "GROF", "ICOW") + R("BASM", "GROF", "YCOW")):
                for i in sorted(B.iyani):
                    _rescale(lo, up, (a, i), FE.V_EstV_IYANI_cows)
    # l. 90-96: slaughter weights of the breeding animals
    for a in sorted(B.breed_act):
        if n(a, "SLGW") and not coco(a, "SLGW"):
            lo[(a, "SLGW")], up[(a, "SLGW")] = FE.V_EstV_SLGW(pd(a, "SLGW", "BASM"), t - d.ord_bas)
    # l. 101-142: feed coefficients
    for a in sorted(B.maact & cols):
        drmn, drmx = pd(a, "DRMN", "BASM"), pd(a, "DRMX", "BASM")
        for f in sorted(B.feed):
            if not n(a, f) or (a, f) not in B.pact_to_io:
                continue
            lo[(a, f)], up[(a, f)] = FE.V_EstV_FEED(pd(a, f, "BASM"), drmn, drmx, t - d.ord_bas)
        for f in sorted(B.foddi):
            if not n(a, f) or (a, f) not in B.pact_to_io:
                continue
            outs = [(R("coco", "GROF", o), R("BASM", "GROF", o)) for ff, o in B.feed_to_o if ff == f]
            lo[(a, f)], up[(a, f)] = FE.V_EstV_FODDI(pd(a, f, "BASM"), drmn, drmx, t - d.ord_bas, outs)
    # l. 144-167: requirements (relative)
    for a in sorted(B.maact):
        if not n(a, "LEVL"):
            continue
        for r_ in sorted(B.reqst):
            if not d.const_slope.get((a, r_), 0.0):
                continue
            lo[(a, r_)], up[(a, r_)] = FE.V_EstV_ReqsT(sup(a, r_))
        for r_ in sorted(B.reqste):
            if d.const_slope.get((a, r_), 0.0):
                lo[(a, r_)] = FE.V_EstV_lo_ReqsTE(sup(a, r_))
        if d.const_slope.get((a, "CRPR"), 0.0):
            v = FE.V_EstV_lo_CRPR(LO((a, "CRPR")), pd(a, "N_EXPT", "BASM"), pd(a, "CRPR", "Const"),
                                  pd(a, "CRPR", "Slope"), [sup(a, o) for aa, o in B.pact_to_y if aa == a and n(a, o)],
                                  eff)
            if v is not None:
                lo[(a, "CRPR")] = v
        for r_ in sorted(B.reqste):
            if d.const_slope.get((a, r_), 0.0):
                up[(a, r_)] = FE.V_EstV_up_ReqsTE(LO((a, r_)))
    # l. 171-191: yields not below the base year's
    for a in sorted(B.noyielddrop & cols):
        for w in sorted(rows):
            if (a, w) not in B.pact_to_y or not n(a, w) or coco(a, w):
                continue
            if d.prev is not None:
                pv = pd(a, w, "BASM") if d.prev_exante_d else d.estp_prev.get((a, w), 0.0)
            else:
                pv = 0.0
            lo[(a, w)], up[(a, w)] = FE.V_EstV_NoYieldDrop(pd(a, w, "BASM"), ("GRAS", a) in B.dact_to_pact,
                                                           t - d.ord_bas, pv, UP((a, w)))
    # l. 196-200: GLOBIOM yields (p_globiomTightLink empty): none
    # l. 206-234: pork and poultry growth in the EU
    maxf = FE.p_data_GROF_maxFacPerY(d.ms, n("GROF", "PORK"), n("GROF", "POUF"), d.west, d.east)
    if exante_t:
        for w, fct in sorted(maxf.items()):
            base, ref = bast_or_basm("GROF", w)
            up[("GROF", w)] = FE.V_EstV_up_GROF_maxFac(UP(("GROF", w)), base, fct, t - ref)
    # l. 238-256: producer prices
    for w in sorted(rows):
        if not n("UVAG", w) or coco("UVAG", w):
            continue
        b = FE.V_EstV_UVAG(pd("UVAG", w, "BASM"), pd("UVAG", w, "BAS"), t - d.ord_bas, w, w in B.grpr)
        if b is not None:
            lo[("UVAG", w)], up[("UVAG", w)] = b
    # l. 261-264: GLOBIOM food intake: none; l. 269-279: food intake
    if exante_t:
        for w in sorted(rows):
            if n("INHA", w) and w not in B.grpr and not R("coco", "INHA", w):
                lo[("INHA", w)], up[("INHA", w)] = FE.V_EstV_INHA(pd("INHA", w, "BAST"), pd("INHA", w, "BASM"),
                                                                  t - d.ord_bast, t - d.ord_bas)
        # l. 284-292: foodSh
        for w in sorted(rows):
            if n("foodSh", w) and not R("coco", "foodSh", w):
                base, ref = bast_or_basm("foodSh", w)
                lo[("foodSh", w)], up[("foodSh", w)] = FE.V_EstV_foodSh(base, t - ref)
    # l. 300-318: meats and cereals
    for g in ("MEAS", "CERE"):
        if n("INHA", g) and not coco("HCOM", g):
            lo_g, up_g = FE.V_EstV_INHA_MEAS_CERE(g, pd("INHA", g, "BASM"), t - d.ord_bas)
            up[("INHA", g)] = up_g
            lo[("INHA", g)] = lo_g
    # l. 322-323: biofuels
    for s in sorted(B.seco_biof):
        if n("INHA", s):
            lo_s, up_s = FE.V_EstV_INHA_seco_bioF()
            up[("INHA", s)] = up_s
            lo[("INHA", s)] = lo_s
    # l. 328-339: human consumption from the food intake and the population
    pop = R("p_data", "INHA", "LEVL")
    for w in sorted(rows):
        if n("INHA", w):
            up[("HCOM", w)], up[("DOMM", w)], lo[("HCOM", w)] = FE.V_EstV_HCOM(UP(("INHA", w)), LO(("INHA", w)), pop)
    # l. 344-381: areas, depending on the crop share
    for c in sorted(cols):
        if not ((c in B.cact) or (c in B.grpc)) or coco(c, "LEVL") or not n(c, "LEVL"):
            continue
        land = pd("UAAR", "LEVL", "BASM") - (0.0 if c in ("GRAE", "GRAI") else pd("GRAS", "LEVL", "BASM"))
        if not land > 0:
            continue
        lo_c, up_c = FE.V_EstV_LEVL_crops(pd(c, "LEVL", "BASM"), land, t, d.ord_bas, span_bas)
        up[(c, "LEVL")] = up_c
        lo[(c, "LEVL")] = lo_c
    # l. 390-401: permanent grassland
    if d.eu28:
        for c in sorted(B.grsact):
            if not coco(c, "LEVL") and n(c, "LEVL"):
                lo[(c, "LEVL")] = FE.V_EstV_lo_GRSACT(LO((c, "LEVL")), pd(c, "LEVL", "BAST"), pd(c, "LEVL", "BASM"))
    # l. 408-507: herds
    for a in sorted(B.maact):
        if pd(a, "LEVL", "BASM"):
            lo[(a, "LEVL")] = FE.V_EstV_lo_MAACT(pd(a, "LEVL", "BASM"))
    minp, maxp, mint, maxt = FE.p_data_LEVL_facs([a for a in sorted(B.maact) if not coco(a, "LEVL") and n(a, "LEVL")],
                                                 d.ms, n("PIGF", "LEVL"), n("POUF", "LEVL"), d.west, d.east)
    if exante_t:
        tb, tt = d.ord_bas, d.ord_bast
        for a in sorted(B.maact):
            k = (a, "LEVL")
            bt, bs = pd(a, "LEVL", "BAST"), pd(a, "LEVL", "BAS")
            if a in maxp:
                up[k] = FE.V_EstV_up_MAACT_LEVL(UP(k), bt, bs, maxp[a], maxt.get(a, 0.0), t - tt, t - tb,
                                                d.lst_exante - tt, d.lst_exante - tb)
            if a in minp:
                lo[k] = FE.V_EstV_lo_MAACT_LEVL(LO(k), bt, bs, minp[a], mint.get(a, 0.0), t - tt, t - tb,
                                                d.lst_exante - tt, d.lst_exante - tb)
    # l. 512-521: wine planting rights (RESY: the simulation years)
    v = FE.V_EstV_up_TWIN(d.ms, pd("TWIN", "LEVL", "BASM"))
    if v is not None:
        up[("TWIN", "LEVL")] = v
    # l. 525-528: other oils
    if not coco("OOIL", "LEVL") and n("OOIL", "LEVL"):
        up[("OOIL", "LEVL")] = FE.V_EstV_up_OOIL(pd("OOIL", "LEVL", "BASM"), t - d.ord_bas)
    # l. 534-542: young animals' coefficients, fixed yields, 365 days
    for a in sorted(B.fix_yai):
        if n(a, "LEVL"):
            for aa, i in B.pact_to_i:
                if aa == a and i in B.iyani:
                    fx((a, i), FE.V_EstV_fx_young_animals())
    for a in sorted(B.fix_yao):
        if n(a, "LEVL"):
            for aa, o in B.pact_to_o:
                if aa == a and o in B.oyani:
                    fx((a, o), FE.V_EstV_fx_young_animals())
    for c in sorted(B.fixyield):
        for w in sorted(B.o):
            if n(c, w):
                fx((c, w), FE.V_EstV_fx_FixYield(pd(c, w, "BAS")))
    for a in sorted(B.aact365):
        if n(a, "DAYS"):
            fx((a, "DAYS"), FE.V_EstV_fx_DAYS())
    # l. 547-548: straw
    for c in sorted(B.cere):
        if n(c, "STRA"):
            lo_s, up_s = FE.V_EstV_STRA()
            up[(c, "STRA")] = up_s
            lo[(c, "STRA")] = lo_s
    # l. 553-559: maximum yields from the ex-post data (ExAnteD years)
    if d.exante_d:
        for a in sorted(B.crops_max_yields):
            for aa, w in B.pact_to_y:
                if aa != a or not n(a, w) or not (pd(a, w, "BAST") or pd(a, w, "BSY")):
                    continue
                up[(a, w)] = FE.V_EstV_up_max_yields(UP((a, w)), pd(a, w, "BAST"), pd(a, w, "BSY"))
    # l. 565-646: physical limits
    for a in sorted(B.cere):
        for aa, w in B.pact_to_y:
            if aa == a and w in rows and n(a, w):
                up[(a, w)] = FE.V_EstV_up_CERE(UP((a, w)))
    for k in [("MAIF", "MAIF"), ("POTA", "POTA"), ("SUGB", "SUGB"), ("ROOF", "ROOF")]:
        if n(*k):
            up[k] = FE.V_EstV_up_physical(k, pd(k[0], k[1], "BASM"), UP(k))
    if n("GRAI", "GRAS"):
        up[("GRAI", "GRAS")] = FE.V_EstV_up_GRAS("GRAI", False, pd("GRAI", "GRAS", "BASM"), UP(("GRAS", "GRAS")))
    if n("GRAE", "GRAS"):
        up[("GRAE", "GRAS")] = FE.V_EstV_up_GRAS("GRAE", False, pd("GRAS", "GRAS", "BASM"), UP(("GRAS", "GRAS")))
    if d.ms == "NL000000":
        if n("GRAI", "GRAS"):
            up[("GRAI", "GRAS")] = FE.V_EstV_up_GRAS("GRAI", True, pd("GRAI", "GRAS", "BASM"), UP(("GRAS", "GRAS")))
        if n("GRAE", "GRAS"):
            up[("GRAE", "GRAS")] = FE.V_EstV_up_GRAS("GRAE", True, pd("GRAE", "GRAS", "BASM"), UP(("GRAS", "GRAS")))
    for k in [("OFAR", "OFAR"), ("TOBA", "TOBA"), ("CITR", "CITR"), ("TAGR", "TAGR"), ("APPL", "APPL"),
              ("TWIN", "TWIN"), ("OLIV", "OLIV"), ("OVEG", "OVEG"), ("OFRU", "OFRU"), ("TEXT", "TEXT"),
              ("TABO", "TABO")]:
        if n(*k):
            up[k] = FE.V_EstV_up_physical(k, pd(k[0], k[1], "BASM"), UP(k))
    for a in sorted(B.crops_max_yields):
        for aa, w in B.pact_to_y:
            if aa == a and n(a, w):
                lo[(a, w)] = FE.V_EstV_lo_max_yields(LO((a, w)), UP((a, w)))
    # l. 655-664: meat yields (%FixExogenFactGlobiom% off)
    for a in sorted(B.maact):
        for m in sorted(B.meat):
            if n(a, m) and not coco(a, m):
                lo[(a, m)], up[(a, m)] = FE.V_EstV_MEAT(pd(a, m, "BASM"), x_bas, span_bas)
        # l. 666-672: days
        if n(a, "DAYS") and not coco(a, "DAYS"):
            lo[(a, "DAYS")], up[(a, "DAYS")] = FE.V_EstV_DAYS(pd(a, "DAYS", "BASM"), x_bas, span_bas)
    # l. 675-679: the requirement functions' limits
    for (a, w, bd), v in sorted(B.reqfcnlim.items()):
        if a in B.maact and w in rows and n(a, "LEVL") and v:
            nb = FE.V_EstV_reqfcnlim(bd, LO((a, w)), UP((a, w)), v)
            if bd == "lo":
                lo[(a, w)] = nb
            elif bd == "up":
                up[(a, w)] = nb
    for a in sorted(B.maact & B.aact365):
        fx((a, "DAYS"), FE.V_EstV_fx_DAYS())
    # l. 681-691: milk contents
    for m in sorted(B.mlkcnt):
        for s in sorted(B.mlkseco):
            if n(m, s):
                lo[(m, s)], up[(m, s)] = FE.V_EstV_MLKSECO(pd(m, s, "BASM"), x_bas, span_bas)
        for w in ("MILK", "BUTT", "SMIP"):
            if n(m, w):
                fx((m, w), FE.V_EstV_fx_MLKCNT(pd(m, w, "BASM")))
    # l. 693-705: processing yields
    for s in sorted(B.seco):
        if n("PRCY", s):
            lo[("PRCY", s)], up[("PRCY", s)] = FE.V_EstV_PRCY(pd("PRCY", s, "BASM"), PROC_YIELDS.get(s))
    if n("PRCY", "MILK"):
        fx(("PRCY", "MILK"), FE.V_EstV_fx_PRCY_MILK(pd("PRCY", "MILK", "BASM")))
    for s in sorted(B.mlkseco):
        if n("PRCY", s):
            lo[("PRCY", s)], up[("PRCY", s)] = FE.V_EstV_PRCY_MLKSECO(pd("PRCY", s, "BASM"))
    # l. 707-711: stock changes of young animals
    for o in sorted(B.oyani):
        cows = pd("DCOW", "LEVL", "BASM") + pd("SCOW", "LEVL", "BASM") if o == "YCOW" else 0.0
        up[("STCM", o)] = FE.V_EstV_up_STCM([pd(a, "LEVL", "BASM") for a, oo in B.pact_to_o
                                             if oo == o and a in B.mpact], cows)
    # l. 713-723: market balance positions at least 1e-8
    for e in sorted(B.mrkbalee):
        for w in sorted(rows):
            k = (e, w)
            if k in lo and lo[k] >= 0 and lo[k] != UP(k) and n(e, w):
                lo[k] = FE.V_EstV_lo_MrkBalee(e, lo[k])
    for o in sorted(B.oyani):
        lo[("STCM", o)] = FE.V_EstV_lo_STCM(UP(("STCM", o)))
    for w in sorted(rows):
        lo_n, up_n = FE.V_EstV_NTRD()
        up[("NTRD", w)] = up_n
        lo[("NTRD", w)] = lo_n
    for w in sorted(rows):
        if n("INTP", w):
            lo[("INTP", w)], up[("INTP", w)] = FE.V_EstV_INTP(sup("INTP", w))
    # l. 740-756: labour
    mins, maxs = R("p_data", "MINS", "LABO"), R("p_data", "MAXS", "LABO")
    for w in ("LABO", "LABN", "LABH"):
        b = pd("GROF", w, "BASM")
        if b:
            lo[("GROF", w)], up[("GROF", w)] = FE.V_EstV_GROF_labour(w, b, mins, maxs)
    # l. 764-780: expert supports inside a +/- 10% corridor
    for c, w in posn:
        e = R("Expert", c, w)
        if e and e == sup(c, w) and LO((c, w)) != UP((c, w)) and n(c, w):
            lo[(c, w)], up[(c, w)] = FE.V_EstV_expert_corridor(LO((c, w)), UP((c, w)), e)
    # l. 785-795: UAAR
    if not coco("UAAR", "LEVL"):
        lo_u, up_u = FE.V_EstV_UAAR(pd("UAAR", "LEVL", "BASM"), t - d.ord_bas)
        up[("UAAR", "LEVL")] = up_u
        lo[("UAAR", "LEVL")] = lo_u
    # l. 805-816: artificial land (v_estV(MSEst, "ARTIF") $ Rest(MSEst): the member state's), total area, inland
    # waters, kitchen gardens
    if d.region_of is None:
        lo[("ARTIF", "LEVL")], up[("ARTIF", "LEVL")] = FE.V_EstV_ARTIF(
            pd("ARTIF", "LEVL", "BASM"), n("ARTIF", "LEVL"), UP(("ARTIF", "LEVL")), t, d.ord_bas, artif_as_coded)
    for c in ("ARTO", "INLW", "KITC"):
        fx((c, "LEVL"), FE.V_EstV_fx_land(pd(c, "LEVL", "BASM")))
    # l. 822: set-aside
    if not d.setr_west:
        for r_ in sorted(B.rset):
            fx((r_, "LEVL"), FE.V_EstV_fx_RSET())
    # l. 827-834: zero in COCO and near-zero supports
    if d.exante_d:
        for c, w in posn:
            s_ = sup(c, w)
            if (s_ and w not in ("COMI", "SUGA") and abs(s_) < 1e-12 and abs(R("coco", c, w)) < 1e-12
                    and R("p_data", c, w)):
                fx((c, w), FE.V_EstV_fx_tiny_support())
    _comi(d, B, lo, up, LO, UP, n, pd, R, sup, fx, t)
    _biofuel(d, B, lo, up, UP, n, R, fx)
    # l. 849-851: sugar beet without production
    if LO(("GROF", "SUGB")) == 0:
        lo[("SUGB", "LEVL")] = FE.V_EstV_lo_SUGB()
        lo[("EAAG", "SUGB")] = FE.V_EstV_lo_SUGB()
    if UP(("GROF", "SUGB")) == 0:
        lo[("SUGB", "TOOU")] = FE.V_EstV_lo_SUGB()
    if d.region_of is not None:
        return lo, up                                # the rest is estimate_ms.gms's (estimate_nuts2.gms has its own)
    # --- estimate_ms.gms l. 78-82: activity levels at least 1e-5 x the number of the member state's NUTS2 regions
    # with data, the upper at least 1.1 x the lower
    for a in sorted(B.mpact):
        if n(a, "LEVL"):
            new_lo, new_up = EM.V_EstV_MPACT_LEVL(LO((a, "LEVL")), UP((a, "LEVL")), d.nuts2_with_data.get(a, 0))
            if new_lo is not None:
                lo[(a, "LEVL")] = new_lo
            up[(a, "LEVL")] = new_up
    # l. 103-125: sugar beets (QUTS), population
    quts = R("p_data", "QUTS", "SUGB")
    if pd("QUTS", "SUGB", "BASM") and t >= 2006:
        lo[("GROF", "SUGB")] = EM.V_EstV_lo_GROF_SUGB(LO(("GROF", "SUGB")), quts)
    fx(("INHA", "LEVL"), EM.V_EstV_fx_INHA_LEVL(pop))
    if not R("p_data", "QUTS", "SUGA"):
        for k in (("SUGB", "LEVL"), ("SUGB", "TOOU"), ("GROF", "SUGB"), ("EXPT", "SUGB"), ("DOMM", "SUGB"),
                  ("MAPR", "SUGA")):
            lo[k] = EM.V_EstV_lo_sugar_quota()
    # l. 159-162: expert bounds as a last resort (l. 127-154, aglinkTightLink, off)
    for k, v in d.res.get("expertlo", {}).items():
        if v and k[0] in cols and k[1] in rows:
            lo[k] = EM.V_EstV_expert(v)
    for k, v in d.res.get("expertup", {}).items():
        if v and k[0] in cols and k[1] in rows:
            up[k] = EM.V_EstV_expert(v)
    return lo, up


def _rescale(lo, up, k, fn):
    """Rescale the bounds of k that are set (fn returns None for one that is not)."""
    nl, nu = fn(lo.get(k), up.get(k))
    if nl is not None:
        lo[k] = nl
    if nu is not None:
        up[k] = nu


def _comi(d, B, lo, up, LO, UP, n, pd, R, sup, fx, t):
    """comi_bounds.gms (fix_est.gms l. 840)."""
    if R("p_data", "QUTA", "COMI"):
        fx(("PRCM", "COMI"), CB.V_EstV_fx_quotas(R("p_data", "QUTA", "COMI")))
    if R("p_data", "QUTB", "COMI"):
        fx(("HCOM", "COMI"), CB.V_EstV_fx_quotas(R("p_data", "QUTB", "COMI")))

    def bb(c, w):
        b = pd(c, w, "BAST")
        return (b, d.ord_bast) if b else (pd(c, w, "BASM"), d.ord_bas)
    if n("LOSF", "COMI") and not R("expertup", "LOSF", "COMI") and not R("p_data", "LOSF", "COMI"):
        b, ref = bb("LOSF", "COMI")
        up[("LOSF", "COMI")] = CB.V_EstV_up_LOSF_COMI(b, t - ref)
    if n("LOSF", "COMI") and not R("expertlo", "LOSF", "COMI") and not R("p_data", "LOSF", "COMI"):
        b, ref = bb("LOSF", "COMI")
        lo[("LOSF", "COMI")] = CB.V_EstV_lo_LOSF_COMI(b, t - ref)
    if (not R("p_data", "QUTA", "COMI") and not R("p_data", "PRCM", "COMI") and (d.wba7 or d.bur)
            and n("PRCM", "COMI")):
        pb, _ = bb("PRCM", "COMI")
        pbr = d.ord_bast if pd("PRCM", "COMI", "BAST") else d.ord_bas
        lo[("PRCM", "COMI")], up[("PRCM", "COMI")] = CB.V_EstV_PRCM_COMI(
            pb, pbr, pd("LOSF", "COMI", "BAST") + pd("FEDM", "COMI", "BAST"),
            pd("LOSF", "COMI", "BASM") + pd("FEDM", "COMI", "BASM"), t, d.ord_bast, d.ord_bas)
    if (not R("p_data", "QUTB", "COMI") and not R("p_data", "HCOM", "COMI") and d.wba7
            and pd("HCOM", "COMI", "BASM")):
        b, ref = bb("HCOM", "COMI")
        lo[("HCOM", "COMI")], up[("HCOM", "COMI")] = CB.V_EstV_HCOM_COMI(b, t - ref)
    # the member state's p_data and P_Result (MS in l. 124-186; the region's own where Rest is the member state)
    MPD = d.ms_pd or pd
    MR = (lambda rp, c, w: (d.ms_res or {}).get(rp, {}).get((c, w), 0.0)) if d.ms_res is not None else R  # noqa: E731

    def mbb(c, w):
        b = MPD(c, w, "BAST")
        return (b, d.ord_bast) if b else (MPD(c, w, "BASM"), d.ord_bas)
    # DCOW's milk yield (the member state's p_data BASM, BAST): the weighted mean of DCOL and DCOH
    dcow = {}
    for st in ("BASM", "BAST"):
        dcow[st] = CB.P_DATA_DCOW_COMI(MPD("DCOL", "COMI", st), MPD("DCOL", "LEVL", st), MPD("DCOH", "COMI", st),
                                       MPD("DCOH", "LEVL", st), MPD("DCOW", "COMI", st))
    dy, dref = (dcow["BAST"], d.ord_bast) if dcow["BAST"] else (dcow["BASM"], d.ord_bas)
    late = max(0, 2050 - d.lst_exante) / (2050 - d.lst_dgagri)
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI") or MR("p_data", c, "COMI") or not MPD(c, "COMI", "BASM"):
            continue
        b, _ = mbb(c, "COMI")
        up[(c, "COMI")], lo[(c, "COMI")] = CB.V_EstV_COMI(
            pd(c, "COMI", "BASM"), b, MPD(c, "COMI", "BASM"), dy, REF_MILK_YIELD, late, t - dref,
            R("expertup", c, "COMI"), R("expertlo", c, "COMI"))
        # the member state's own (SUM(MAP_RR(MS, Rest), 1) GT 1) only with NUTS2 regions in Rest: not at MS level
    # l. 249-268: the member state's Expert equal to its Support: the corridor +-5% of the support (member state),
    # +-10% (a region)
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI"):
            continue
        s_ = sup(c, "COMI")
        if MR("Expert", c, "COMI") == MR("Support", c, "COMI") and LO((c, "COMI")) != UP((c, "COMI")) and s_:
            lo[(c, "COMI")], up[(c, "COMI")] = CB.V_EstV_COMI_corridor(LO((c, "COMI")), UP((c, "COMI")), s_,
                                                                       d.region_of is None)
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI"):
            continue
        if t > d.fst_exante + 2 and LO((c, "COMI")) > 0:
            later = d.prev is not None and d.prev > d.lst_expostt
            nl, nu = CB.V_EstV_COMI_prev(LO((c, "COMI")), UP((c, "COMI")),
                                         d.step3_prev.get((c, "COMI"), 0.0) if later else None,
                                         d.region_of is None, t - d.prev if later else 0)
            lo[(c, "COMI")] = nl
            if nu is not None:
                up[(c, "COMI")] = nu


def _biofuel(d, B, lo, up, UP, n, R, fx):
    """biofuel_bounds.gms (fix_est.gms l. 845)."""
    S_ = lambda c, w: R("Support", c, w)                                     # noqa: E731
    for b in sorted(B.bio_stock):
        if n("PRCB", b):
            lo[("PRCB", b)], up[("PRCB", b)] = BF.V_EstV_PRCB("PRCB", S_("PRCB", b))
        if n("PRCBY", b):
            lo[("PRCBY", b)], up[("PRCBY", b)] = BF.V_EstV_PRCB("PRCBY", S_("PRCBY", b))
        if n("BIOF", b):
            lo[("BIOF", b)], up[("BIOF", b)] = BF.V_EstV_BIOF_bioStock(S_("BIOF", b))
    if UP(("GROF", "SUGB")) == 0:
        lo[("BIOF", "SUGA")] = BF.V_EstV_lo_BIOF_SUGA()
    for s in sorted(B.seco_biof):
        for c in ("MAPR", "BIOF", "INDM", "SECG", "NAGR", "UVAD"):
            if n(c, s):
                lo[(c, s)], up[(c, s)] = BF.V_EstV_SECO_BIOF(c, S_(c, s))
        if not n("NAGR", s):
            fx(("NAGR", s), BF.V_EstV_fx_NAGR_SECG())
        if not n("SECG", s):
            fx(("SECG", s), BF.V_EstV_fx_NAGR_SECG())
    if n("NECR", "LEVL"):
        lo[("NECR", "LEVL")], up[("NECR", "LEVL")] = BF.V_EstV_NECR(S_("NECR", "LEVL"))
        lo[("NECR", "OCRO")], up[("NECR", "OCRO")] = BF.V_EstV_NECR(S_("NECR", "OCRO"))
    for (c, w), v in sorted(d.res.get("Support", {}).items()):
        if v and abs(v) <= 1e-14 and (c in ("BIOF", "PRCB", "PRCBY") or w in ("BIOE", "BIOD", "DDGS")):
            fx((c, w), BF.V_EstV_fx_BIOF_tiny())
    if S_("BIOF", "CERE") < 1e-13:
        fx(("BIOF", "CERE"), BF.V_EstV_fx_BIOF_CERE_MAPR_BIOE())
    if S_("MAPR", "BIOE") < 1e-13:
        fx(("MAPR", "BIOE"), BF.V_EstV_fx_BIOF_CERE_MAPR_BIOE())

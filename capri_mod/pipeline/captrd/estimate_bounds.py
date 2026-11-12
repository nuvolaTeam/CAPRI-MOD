"""The bounds of CAPTRD's member-state estimation m_trendMS for one member state and ex-ante year: estimate_ms.gms
l. 53-67 (the standard bounds), captrd/fix_est.gms (with comi_bounds.gms and biofuel_bounds.gms, which it includes),
then estimate_ms.gms l. 71-121 (CAPRI star 3.0), in CAPTRD's order of statements; the bound-widening of infeasible
solves (estimate_ms.gms l. 222-420) is not part of it.

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

K2 = Tuple[str, str]
INF = float("inf")

#: estimate_ms.gms l. 53-55: the standard upper bound; l. 60-67: the lower bound, 1% of the support
STD_UP = 1.0e9
LO_SUPPORT_SHARE = 0.01
#: captrd.gms l. 289
REF_MILK_YIELD = 7000.0
#: captrd.gms l. 356-362: processing yields of the oilseeds (cake and oil)
PROC_YIELDS = {"SOYC": 0.80, "SOYO": 0.18, "RAPC": 0.60, "RAPO": 0.40, "SUNC": 0.55, "SUNO": 0.45}
#: fix_est.gms l. 512-521: CMO wine, the planting rights (1000 ha above the base)
WINE_PLANTING = {"DE000000": 1.534, "EL000000": 1.098, "ES000000": 17.355, "FR000000": 13.565, "IT000000": 12.933,
                 "BL000000": 0.018, "AT000000": 0.737, "PT000000": 3.760}
#: fix_est.gms l. 565-646: physical upper limits of yields (kg per ha; GRAS of GRAI and GRAE, NL's own)
MAX_YIELDS = {("MAIF", "MAIF"): 90000.0, ("POTA", "POTA"): 55000.0, ("SUGB", "SUGB"): 90000.0,
              ("ROOF", "ROOF"): 110000.0, ("OFAR", "OFAR"): 90000.0, ("TOBA", "TOBA"): 4500.0,
              ("CITR", "CITR"): 30000.0, ("TAGR", "TAGR"): 30000.0, ("APPL", "APPL"): 100000.0,
              ("TWIN", "TWIN"): 20000.0, ("OLIV", "OLIV"): 4500.0, ("OVEG", "OVEG"): 60000.0,
              ("OFRU", "OFRU"): 110000.0, ("TEXT", "TEXT"): 11000.0, ("TABO", "TABO"): 11000.0}
CERE_MAX_YIELD = 15000.0
GRAS_MAX = {"GRAI": 80000.0, "GRAE": 40000.0}
GRAS_MAX_NL = {"GRAI": 160000.0, "GRAE": 80000.0}
#: fix_est.gms l. 547: straw yields free up to 30 t
STRA_MAX = 30000.0


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


def bounds(d: BoundData, B: BoundSets, eff: float, artif_as_coded: Optional[bool] = None):
    """lo, up: {(col, row): bound} of every position a statement bounds (others free). eff: the requirement
    functions' feeding efficiency factor of the year (0.998^(year - 2000)). artif_as_coded (setting
    captrd.artif_upper_bound_as_coded; FIX-7): ARTIF's upper bound with fix_est.gms l. 810's parenthesis as coded
    (the year as the exponent) or, the default, as its comment states it (the years since the base)."""
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

    def fx(k, v):
        lo[k] = v
        up[k] = v

    def bast_or_basm(c, w):
        b = pd(c, w, "BAST")
        return (b, d.ord_bast) if b else (pd(c, w, "BASM"), d.ord_bas)

    def ramp(frac):
        """(MAX(OrdT("BAS")+1, OrdT(t)) - OrdT("BAS")) / (OrdT("lst_exAnte") - OrdT("BAS")) times frac"""
        return frac * (max(d.ord_bas + 1, t) - d.ord_bas) / span_bas

    cols, rows = B.cols_est, B.rows_est
    posn = [(c, w) for c in sorted(cols) for w in sorted(rows)]
    # --- estimate_ms.gms l. 53-67
    for c, w in posn:
        if n(c, w):
            up[(c, w)] = STD_UP
        s_ = sup(c, w)
        if n(c, w) or s_:
            extra = 0.0
            if c == "CSSP" and pd("CSSP", w, "BASM") < 0:
                extra += pd("CSSP", w, "BASM")
            if w == "OCRO" and pd(c, "OCRO", "BASM") < 0:
                extra += pd(c, "OCRO", "BASM")
            if w == "OANI" and pd(c, "OANI", "BASM") < 0:
                extra += pd(c, "OANI", "BASM")
            if c == "OCRO" and pd("OCRO", w, "BASM") < 0:
                extra += pd("OCRO", w, "BASM")
            if c == "OANI" and pd("OANI", w, "BASM") < 0:
                extra += pd("OANI", w, "BASM")
            lo[(c, w)] = max(s_ * LO_SUPPORT_SHARE, extra)
    # --- fix_est.gms l. 25-63: input and output coefficients, 2.5% a year, at most x% to Lst_exAnte
    if exante_t:
        for a in sorted(B.mpact & cols):
            for w in sorted(rows):
                if (a, w) not in B.pact_to_io or not n(a, w) or coco(a, w):
                    continue
                # the GLOBIOM yield condition holds: p_globiomTightLink is empty (0 - 0 > -0.025 x years)
                base, ref = bast_or_basm(a, w)
                yrs = t - ref
                frac = yrs / (d.lst_exante - ref)
                lo_share = 0.3 - (0.2 if w in ("YCAM", "YCAF", "SGMI") else 0.0)
                lo[(a, w)] = base * max(0.975 ** yrs, 1 - lo_share * frac - (1.0 if w == "YCHI" else 0.0))
                up_share = 0.3 - (0.2 if w in ("YCAM", "YCAF") else 0.0)
                deact = 10.0 if (a in B.uaar_acts or w in ("YCHI", "SGMI")) else 0.0
                up[(a, w)] = base * min(1.025 ** yrs, 1 + up_share * frac + deact)
        # l. 70-74: young animals, with expert levels up to 2020
        for a in sorted(B.mpact):
            if R("Expert", a, "LEVL") and t <= 2020:
                for o in sorted(B.oyani):
                    if (a, o) in lo:
                        lo[(a, o)] *= 0.5
                    if (a, o) in up:
                        up[(a, o)] *= 1.5
        # l. 79-86: cows' young animal inputs
        for a in sorted(B.cows_act):
            if R("BASM", a, "LEVL") and (R("BASM", "GROF", "ICOW") + R("BASM", "GROF", "YCOW")):
                for i in sorted(B.iyani):
                    if (a, i) in lo:
                        lo[(a, i)] *= 0.9
                    if (a, i) in up:
                        up[(a, i)] *= 1.1
    # l. 90-96: slaughter weights of the breeding animals
    for a in sorted(B.breed_act):
        if n(a, "SLGW") and not coco(a, "SLGW"):
            b = pd(a, "SLGW", "BASM")
            lo[(a, "SLGW")] = b * 0.995 ** (t - d.ord_bas)
            up[(a, "SLGW")] = b * 1.005 ** (t - d.ord_bas)
    # l. 101-142: feed coefficients
    for a in sorted(B.maact & cols):
        dr = (pd(a, "DRMN", "BASM") - pd(a, "DRMX", "BASM")) / 2 * 0.01
        for f in sorted(B.feed):
            if not n(a, f) or (a, f) not in B.pact_to_io:
                continue
            b = pd(a, f, "BASM")
            lo[(a, f)] = max(0.0, b - dr) * 0.90 ** (t - d.ord_bas)
            up[(a, f)] = (b + dr) * 1.10 ** (t - d.ord_bas)
        for f in sorted(B.foddi):
            if not n(a, f) or (a, f) not in B.pact_to_io:
                continue
            b = pd(a, f, "BASM")
            ratio = 0.0
            for ff, o in B.feed_to_o:
                if ff != f:
                    continue
                cc, bb = R("coco", "GROF", o), R("BASM", "GROF", o)
                ratio += (cc / bb) if (cc and bb) else 1.0
            r_lo, r_up = 2 * ratio, 0.5 * ratio
            lo[(a, f)] = max(0.0, b - dr) * min(0.95 ** (t - d.ord_bas), r_lo)
            up[(a, f)] = (b + dr) * max(1.05 ** (t - d.ord_bas), r_up)
    # l. 144-167: requirements (relative)
    for a in sorted(B.maact):
        if not n(a, "LEVL"):
            continue
        for r_ in sorted(B.reqst):
            if not d.const_slope.get((a, r_), 0.0):
                continue
            lo[(a, r_)] = sup(a, r_) * 0.5
            up[(a, r_)] = sup(a, r_) * 1.5
        for r_ in sorted(B.reqste):
            if d.const_slope.get((a, r_), 0.0):
                lo[(a, r_)] = sup(a, r_) * 0.98
        if d.const_slope.get((a, "CRPR"), 0.0):
            k = pd(a, "CRPR", "Const") + pd(a, "CRPR", "Slope") * sum(
                sup(a, o) for aa, o in B.pact_to_y if aa == a and n(a, o))
            if k:
                lo[(a, "CRPR")] = max(LO((a, "CRPR")), pd(a, "N_EXPT", "BASM") * 1.5 / k * eff)
        for r_ in sorted(B.reqste):
            if d.const_slope.get((a, r_), 0.0):
                up[(a, r_)] = LO((a, r_)) / 0.98 * 1.02
    # l. 171-191: yields not below the base year's
    for a in sorted(B.noyielddrop & cols):
        for w in sorted(rows):
            if (a, w) not in B.pact_to_y or not n(a, w) or coco(a, w):
                continue
            g = 0.002 if ("GRAS", a) in B.dact_to_pact else 0.0
            lo[(a, w)] = pd(a, w, "BASM") * (1.0025 - g) ** (t - d.ord_bas)
            if d.prev is not None:
                pv = pd(a, w, "BASM") if d.prev_exante_d else d.estp_prev.get((a, w), 0.0)
                lo[(a, w)] = max(lo[(a, w)], pv)
            else:
                lo[(a, w)] = max(lo[(a, w)], 0.0)
            up[(a, w)] = max(LO((a, w)) * 1.01, UP((a, w)))
    # l. 196-200: GLOBIOM yields (p_globiomTightLink empty): none
    # l. 206-234: pork and poultry growth in the EU
    maxf = {}
    if n("GROF", "PORK") and d.west:
        maxf["PORK"] = 1.01
    if d.ms == "NL000000":
        maxf["PORK"] = 1.0025
    if d.ms == "DK000000":
        maxf["PORK"] = 1.005
    if n("GROF", "POUF") and d.west:
        maxf["POUF"] = 1.015
    if n("GROF", "PORK") and d.east:
        maxf["PORK"] = 1.015
    if n("GROF", "POUF") and d.east:
        maxf["POUF"] = 1.02
    if exante_t:
        for w, fct in sorted(maxf.items()):
            base, ref = bast_or_basm("GROF", w)
            up[("GROF", w)] = min(UP(("GROF", w)), base * fct ** (t - ref))
    # l. 238-256: producer prices, 2% a year (5% for OCRO, OANI, MILK)
    for w in sorted(rows):
        if not n("UVAG", w) or coco("UVAG", w):
            continue
        if w in ("OCRO", "OANI", "MILK"):
            hi, lw = 1.05, 0.95
        elif w not in B.grpr:
            hi, lw = 1.02, 0.98
        else:
            continue
        up[("UVAG", w)] = max(pd("UVAG", w, "BASM"), pd("UVAG", w, "BAS")) * hi ** (t - d.ord_bas)
        lo[("UVAG", w)] = min(pd("UVAG", w, "BASM"), pd("UVAG", w, "BAS")) * lw ** (t - d.ord_bas)
    # l. 261-264: GLOBIOM food intake: none; l. 269-279: food intake, 2% a year. As GAMS reads the statement,
    #   p_data(BAST) * 0.98**(t - BAST) $ (BAST) + p_data(BASM) * 0.98**(t - BAS) $ (not BAST),
    # the second $ conditions the exponent only (it binds to the operand before it), so where BAST exists the
    # second term is BASM x 0.98^0 = BASM: the bounds are BAST x 0.98^n + BASM and BAST x 1.02^n + BASM, about
    # twice the intended ones. Kept as coded: CAPTRD's stored bounds show it in every country and year (CAPRI-ERROR,
    # not fixed: the bounds CAPTRD then widens are these)
    if exante_t:
        for w in sorted(rows):
            if n("INHA", w) and w not in B.grpr and not R("coco", "INHA", w):
                bt, bm = pd("INHA", w, "BAST"), pd("INHA", w, "BASM")
                e2 = 0 if bt else (t - d.ord_bas)
                lo[("INHA", w)] = (bt * 0.98 ** (t - d.ord_bast) if bt else 0.0) + bm * 0.98 ** e2
                up[("INHA", w)] = (bt * 1.02 ** (t - d.ord_bast) if bt else 0.0) + bm * 1.02 ** e2
        # l. 284-292: foodSh
        for w in sorted(rows):
            if n("foodSh", w) and not R("coco", "foodSh", w):
                base, ref = bast_or_basm("foodSh", w)
                lo[("foodSh", w)] = base * 0.998 ** (t - ref)
                up[("foodSh", w)] = base * 1.002 ** (t - ref)
    # l. 300-318: meats and cereals
    for g, (hi, lw) in (("MEAS", (1.01, 0.99)), ("CERE", (1.006, 0.994))):
        if n("INHA", g) and not coco("HCOM", g):
            up[("INHA", g)] = pd("INHA", g, "BASM") * hi ** (t - d.ord_bas)
            lo[("INHA", g)] = pd("INHA", g, "BASM") * lw ** (t - d.ord_bas)
    # l. 322-323: biofuels
    for s in sorted(B.seco_biof):
        if n("INHA", s):
            up[("INHA", s)] = INF
            lo[("INHA", s)] = 0.0
    # l. 328-339: human consumption from the food intake and the population
    pop = R("p_data", "INHA", "LEVL")
    for w in sorted(rows):
        if n("INHA", w):
            up[("HCOM", w)] = UP(("INHA", w)) * pop * 0.001 * 1000.0
            up[("DOMM", w)] = max(UP(("HCOM", w)), STD_UP)
            lo[("HCOM", w)] = LO(("INHA", w)) * pop * 0.001 / 1000.0
    # l. 344-381: areas, depending on the crop share
    for c in sorted(cols):
        if not ((c in B.cact) or (c in B.grpc)) or coco(c, "LEVL") or not n(c, "LEVL"):
            continue
        land = pd("UAAR", "LEVL", "BASM") - (0.0 if c in ("GRAE", "GRAI") else pd("GRAS", "LEVL", "BASM"))
        if not land > 0:
            continue
        b = pd(c, "LEVL", "BASM")
        dev = (b / land) ** 0.25 / 4 * land * max(0.2, (max(d.ord_bas + 1, t) - d.ord_bas) / span_bas)
        up[(c, "LEVL")] = max(b + 0.1, b + dev)
        lo[(c, "LEVL")] = max(1.0e-5, b - dev)
    # l. 390-401: permanent grassland
    if d.eu28:
        for c in sorted(B.grsact):
            if not coco(c, "LEVL") and n(c, "LEVL"):
                b = pd(c, "LEVL", "BAST") * 0.98 + (pd(c, "LEVL", "BASM") * 0.98 if not pd(c, "LEVL", "BAST") else 0.0)
                lo[(c, "LEVL")] = max(LO((c, "LEVL")), b)
    # l. 408-507: herds
    for a in sorted(B.maact):
        if pd(a, "LEVL", "BASM"):
            lo[(a, "LEVL")] = pd(a, "LEVL", "BASM") * 0.2
    minp, maxp, mint, maxt = {}, {}, {}, {}
    for a in sorted(B.maact):
        if not coco(a, "LEVL") and n(a, "LEVL"):
            minp[a], maxp[a], mint[a], maxt[a] = 0.9, 1.05, 0.2, 4.0
    if n("PIGF", "LEVL") and d.west:
        minp["PIGF"] = 0.98
        maxp["PIGF"] = 1.01
    if d.ms == "NL000000":
        maxp["PIGF"] = 1.0025
    if d.ms == "DK000000":
        maxp["PIGF"] = 1.005
    if n("POUF", "LEVL") and d.west:
        maxp["POUF"] = 1.015
    if n("PIGF", "LEVL") and d.east:
        maxp["PIGF"] = 1.015
    if n("POUF", "LEVL") and d.east:
        maxp["POUF"] = 1.02
    if n("PIGF", "LEVL") and d.west:
        maxt["PIGF"] = 1.4
    if n("POUF", "LEVL") and d.west:
        maxt["POUF"] = 1.7
    if n("PIGF", "LEVL") and d.east:
        maxt["PIGF"] = 1.7
    if n("POUF", "LEVL") and d.east:
        maxt["POUF"] = 2.3
    if exante_t:
        tb, tt = d.ord_bas, d.ord_bast
        for a in sorted(B.maact):
            k = (a, "LEVL")
            bt, bs = pd(a, "LEVL", "BAST"), pd(a, "LEVL", "BAS")
            if a in maxp:
                mt = maxt.get(a, 0.0)
                up[k] = min(UP(k), max(bt * maxp[a] ** (t - tt), bs * maxp[a] ** (t - tb)),
                            max(bt * (1 + (mt - 1) * (t - tt) / (d.lst_exante - tt)),
                                bs * (1 + (mt - 1) * (t - tb) / (d.lst_exante - tb))))
            if a in minp:
                mt = mint.get(a, 0.0)
                cand = [LO(k), min(bt * minp[a] ** (t - tt), bs * minp[a] ** (t - tb)),
                        min(bt * (1 + (mt - 1) * (t - tt) / (d.lst_exante - tt)),
                            bs * (1 + (mt - 1) * (t - tb) / (d.lst_exante - tb)))]
                if not bt:
                    cand += [bs * minp[a] ** (t - tb), bs * (1 + (mt - 1) * (t - tb) / (d.lst_exante - tb))]
                else:
                    cand += [0.0, 0.0]
                lo[k] = max(cand)
    # l. 512-521: wine planting rights (RESY: the simulation years)
    if d.ms in WINE_PLANTING:
        up[("TWIN", "LEVL")] = pd("TWIN", "LEVL", "BASM") + WINE_PLANTING[d.ms]
    # l. 525-528: other oils
    if not coco("OOIL", "LEVL") and n("OOIL", "LEVL"):
        up[("OOIL", "LEVL")] = pd("OOIL", "LEVL", "BASM") * 1.01 ** (t - d.ord_bas)
    # l. 534-542: young animals' coefficients, fixed yields, 365 days
    for a in sorted(B.fix_yai):
        if n(a, "LEVL"):
            for aa, i in B.pact_to_i:
                if aa == a and i in B.iyani:
                    fx((a, i), 1000.0)
    for a in sorted(B.fix_yao):
        if n(a, "LEVL"):
            for aa, o in B.pact_to_o:
                if aa == a and o in B.oyani:
                    fx((a, o), 1000.0)
    for c in sorted(B.fixyield):
        for w in sorted(B.o):
            if n(c, w):
                fx((c, w), pd(c, w, "BAS"))
    for a in sorted(B.aact365):
        if n(a, "DAYS"):
            fx((a, "DAYS"), 365.0)
    # l. 547-548: straw
    for c in sorted(B.cere):
        if n(c, "STRA"):
            up[(c, "STRA")] = STRA_MAX
            lo[(c, "STRA")] = 0.0
    # l. 553-559: maximum yields from the ex-post data (ExAnteD years)
    if d.exante_d:
        for a in sorted(B.crops_max_yields):
            for aa, w in B.pact_to_y:
                if aa != a or not n(a, w) or not (pd(a, w, "BAST") or pd(a, w, "BSY")):
                    continue
                up[(a, w)] = min(UP((a, w)), 1.5 * max(pd(a, w, "BAST"), pd(a, w, "BSY")))
    # l. 565-646: physical limits
    for a in sorted(B.cere):
        for aa, w in B.pact_to_y:
            if aa == a and w in rows and n(a, w):
                up[(a, w)] = min(CERE_MAX_YIELD, UP((a, w)))
    _phys(("MAIF", "MAIF"), n, pd, up, UP)
    _phys(("POTA", "POTA"), n, pd, up, UP)
    _phys(("SUGB", "SUGB"), n, pd, up, UP)
    _phys(("ROOF", "ROOF"), n, pd, up, UP)
    if n("GRAI", "GRAS"):
        up[("GRAI", "GRAS")] = max(pd("GRAI", "GRAS", "BASM"), min(GRAS_MAX["GRAI"], UP(("GRAS", "GRAS"))))
    if n("GRAE", "GRAS"):
        up[("GRAE", "GRAS")] = max(pd("GRAS", "GRAS", "BASM"), min(GRAS_MAX["GRAE"], UP(("GRAS", "GRAS"))))
    if d.ms == "NL000000":
        if n("GRAI", "GRAS"):
            up[("GRAI", "GRAS")] = max(pd("GRAI", "GRAS", "BASM"), min(GRAS_MAX_NL["GRAI"], UP(("GRAS", "GRAS"))))
        if n("GRAE", "GRAS"):
            up[("GRAE", "GRAS")] = max(pd("GRAE", "GRAS", "BASM"), min(GRAS_MAX_NL["GRAE"], UP(("GRAS", "GRAS"))))
    for k in [("OFAR", "OFAR"), ("TOBA", "TOBA"), ("CITR", "CITR"), ("TAGR", "TAGR"), ("APPL", "APPL"),
              ("TWIN", "TWIN"), ("OLIV", "OLIV"), ("OVEG", "OVEG"), ("OFRU", "OFRU"), ("TEXT", "TEXT"),
              ("TABO", "TABO")]:
        _phys(k, n, pd, up, UP)
    for a in sorted(B.crops_max_yields):
        for aa, w in B.pact_to_y:
            if aa == a and n(a, w):
                lo[(a, w)] = min(LO((a, w)), UP((a, w)) * 0.9)
    # l. 655-664: meat yields (%FixExogenFactGlobiom% off)
    for a in sorted(B.maact):
        for m in sorted(B.meat):
            if n(a, m) and not coco(a, m):
                lo[(a, m)] = pd(a, m, "BASM") * (1.0 - ramp(0.20))
                up[(a, m)] = pd(a, m, "BASM") * (1.0 + ramp(0.20))
        # l. 666-672: days
        if n(a, "DAYS") and not coco(a, "DAYS"):
            lo[(a, "DAYS")] = pd(a, "DAYS", "BASM") * (1.0 - ramp(0.30))
            up[(a, "DAYS")] = pd(a, "DAYS", "BASM") * (1.0 + ramp(0.30))
    # l. 675-679: the requirement functions' limits
    for (a, w, bd), v in sorted(B.reqfcnlim.items()):
        if a in B.maact and w in rows and n(a, "LEVL") and v:
            if bd == "lo":
                lo[(a, w)] = max(LO((a, w)), v)
            elif bd == "up":
                up[(a, w)] = min(UP((a, w)), v)
    for a in sorted(B.maact & B.aact365):
        fx((a, "DAYS"), 365.0)
    # l. 681-691: milk contents
    for m in sorted(B.mlkcnt):
        for s in sorted(B.mlkseco):
            if n(m, s):
                lo[(m, s)] = pd(m, s, "BASM") * (1.0 - ramp(0.20))
                up[(m, s)] = pd(m, s, "BASM") * (1.0 + ramp(0.20))
        for w in ("MILK", "BUTT", "SMIP"):
            if n(m, w):
                fx((m, w), pd(m, w, "BASM"))
    # l. 693-705: processing yields
    for s in sorted(B.seco):
        if n("PRCY", s):
            lo[("PRCY", s)] = pd("PRCY", s, "BASM") * 0.99
            up[("PRCY", s)] = pd("PRCY", s, "BASM") * 1.01
            if s in PROC_YIELDS:
                py = PROC_YIELDS[s]
                lo[("PRCY", s)] = min(max(py * 0.90, pd("PRCY", s, "BASM") * 0.99), py)
                up[("PRCY", s)] = max(min(py * 1.1, pd("PRCY", s, "BASM") * 1.01), py)
    if n("PRCY", "MILK"):
        fx(("PRCY", "MILK"), pd("PRCY", "MILK", "BASM"))
    for s in sorted(B.mlkseco):
        if n("PRCY", s):
            lo[("PRCY", s)] = pd("PRCY", s, "BASM") * 0.50
            up[("PRCY", s)] = pd("PRCY", s, "BASM") * 1.50
    # l. 707-711: stock changes of young animals
    for o in sorted(B.oyani):
        tot = 0.0
        for a, oo in B.pact_to_o:
            if oo == o and a in B.mpact:
                tot += pd(a, "LEVL", "BASM") + (pd("DCOW", "LEVL", "BASM") + pd("SCOW", "LEVL", "BASM")
                                                if o == "YCOW" else 0.0)
        up[("STCM", o)] = 0.2 * abs(tot)
    # l. 713-723: market balance positions at least 1e-8
    for e in sorted(B.mrkbalee):
        for w in sorted(rows):
            k = (e, w)
            if k in lo and lo[k] >= 0 and lo[k] != UP(k) and n(e, w):
                keep = lo[k] if e not in ("SEDM", "SEDF", "LOSM", "LOSF") else 0.0
                lo[k] = max(keep, 1.0e-8)
    for o in sorted(B.oyani):
        lo[("STCM", o)] = -UP(("STCM", o))
    for w in sorted(rows):
        up[("NTRD", w)] = INF
        lo[("NTRD", w)] = -INF
    for w in sorted(rows):
        if n("INTP", w):
            lo[("INTP", w)] = -abs(sup("INTP", w)) * 2
            up[("INTP", w)] = abs(sup("INTP", w)) * 2
    # l. 740-756: labour
    mins, maxs = R("p_data", "MINS", "LABO"), R("p_data", "MAXS", "LABO")
    for w, dl, du in (("LABO", -0.05, 0.05), ("LABN", -0.05, 0.05), ("LABH", 0.0, 0.0)):
        b = pd("GROF", w, "BASM")
        if b:
            lo[("GROF", w)] = max(0.0, b * (mins + dl))
            up[("GROF", w)] = b * (maxs + du)
    # l. 764-780: expert supports inside a +/- 10% corridor
    for c, w in posn:
        e = R("Expert", c, w)
        if e and e == sup(c, w) and LO((c, w)) != UP((c, w)) and n(c, w):
            lo[(c, w)] = min(LO((c, w)), 0.9 * e)
            up[(c, w)] = max(UP((c, w)), 1.1 * e)
    # l. 785-795: UAAR
    if not coco("UAAR", "LEVL"):
        up[("UAAR", "LEVL")] = pd("UAAR", "LEVL", "BASM")
        lo[("UAAR", "LEVL")] = pd("UAAR", "LEVL", "BASM") * 0.998 ** (t - d.ord_bas)
    # l. 805-816: artificial land, total area, inland waters, kitchen gardens
    lo[("ARTIF", "LEVL")] = pd("ARTIF", "LEVL", "BASM") if n("ARTIF", "LEVL") else 0.0
    # l. 810 reads 1.02**(OrdT(ExAnte)) - OrdT("BAS"): the year as the exponent (CAPRI-ERROR, a misplaced parenthesis;
    # FIX-7). Fixed (the default), 1.02**(OrdT(ExAnte) - OrdT("BAS")) as the comment's "max. 2% increase per year"; the
    # max with the previous bound kept, as coded, so where that is the standard 1e9 the bound stays 1e9
    la = LO(("ARTIF", "LEVL"))
    cap = la * 1.02 ** t - d.ord_bas if artif_as_coded else la * 1.02 ** (t - d.ord_bas)
    up[("ARTIF", "LEVL")] = max(cap, UP(("ARTIF", "LEVL")))
    for c in ("ARTO", "INLW", "KITC"):
        fx((c, "LEVL"), pd(c, "LEVL", "BASM"))
    # l. 822: set-aside
    if not d.setr_west:
        for r_ in sorted(B.rset):
            fx((r_, "LEVL"), 0.0)
    # l. 827-834: zero in COCO and near-zero supports
    if d.exante_d:
        for c, w in posn:
            s_ = sup(c, w)
            if (s_ and w not in ("COMI", "SUGA") and abs(s_) < 1e-12 and abs(R("coco", c, w)) < 1e-12
                    and R("p_data", c, w)):
                fx((c, w), 0.0)
    _comi(d, B, lo, up, LO, UP, n, pd, R, sup, fx, t)
    _biofuel(d, B, lo, up, UP, n, R, fx)
    # l. 849-851: sugar beet without production
    if LO(("GROF", "SUGB")) == 0:
        lo[("SUGB", "LEVL")] = 0.0
        lo[("EAAG", "SUGB")] = 0.0
    if UP(("GROF", "SUGB")) == 0:
        lo[("SUGB", "TOOU")] = 0.0
    # --- estimate_ms.gms l. 71-76: activity levels at least 1e-5 x the number of the member state's NUTS2 regions
    # with data, the upper at least 1.1 x the lower
    for a in sorted(B.mpact):
        if n(a, "LEVL"):
            if LO((a, "LEVL")) != 0:
                lo[(a, "LEVL")] = max(1.0e-5 * d.nuts2_with_data.get(a, 0), LO((a, "LEVL")))
            up[(a, "LEVL")] = max(LO((a, "LEVL")) * 1.1, UP((a, "LEVL")))
    # l. 102-121: sugar beets (QUTS), population
    quts = R("p_data", "QUTS", "SUGB")
    if pd("QUTS", "SUGB", "BASM") and t >= 2006:
        lo[("GROF", "SUGB")] = min(LO(("GROF", "SUGB")), quts)
    fx(("INHA", "LEVL"), pop)
    if not R("p_data", "QUTS", "SUGA"):
        for k in (("SUGB", "LEVL"), ("SUGB", "TOOU"), ("GROF", "SUGB"), ("EXPT", "SUGB"), ("DOMM", "SUGB"),
                  ("MAPR", "SUGA")):
            lo[k] = 0.0
    # l. 146-151: expert bounds as a last resort
    for k, v in d.res.get("expertlo", {}).items():
        if v and k[0] in cols and k[1] in rows:
            lo[k] = v
    for k, v in d.res.get("expertup", {}).items():
        if v and k[0] in cols and k[1] in rows:
            up[k] = v
    return lo, up


def _phys(k, n, pd, up, UP):
    if n(*k):
        up[k] = max(pd(k[0], k[1], "BASM"), min(MAX_YIELDS[k], UP(k)))


def _comi(d, B, lo, up, LO, UP, n, pd, R, sup, fx, t):
    """comi_bounds.gms (fix_est.gms l. 840)."""
    if R("p_data", "QUTA", "COMI"):
        fx(("PRCM", "COMI"), R("p_data", "QUTA", "COMI"))
    if R("p_data", "QUTB", "COMI"):
        fx(("HCOM", "COMI"), R("p_data", "QUTB", "COMI"))

    def bb(c, w):
        b = pd(c, w, "BAST")
        return (b, d.ord_bast) if b else (pd(c, w, "BASM"), d.ord_bas)
    if n("LOSF", "COMI") and not R("expertup", "LOSF", "COMI") and not R("p_data", "LOSF", "COMI"):
        b, ref = bb("LOSF", "COMI")
        up[("LOSF", "COMI")] = max(2.0e-8, b * (1 - 0.02) ** max(0, t - ref))
    if n("LOSF", "COMI") and not R("expertlo", "LOSF", "COMI") and not R("p_data", "LOSF", "COMI"):
        b, ref = bb("LOSF", "COMI")
        lo[("LOSF", "COMI")] = b * (1 - 0.04) ** max(0, t - ref)
    if (not R("p_data", "QUTA", "COMI") and not R("p_data", "PRCM", "COMI") and (d.wba7 or d.bur)
            and n("PRCM", "COMI")):
        pb, _ = bb("PRCM", "COMI")
        lfb = pd("LOSF", "COMI", "BAST") + pd("FEDM", "COMI", "BAST")
        if lfb:
            lf, ref = lfb, d.ord_bast
        else:
            lf, ref = pd("LOSF", "COMI", "BASM") + pd("FEDM", "COMI", "BASM"), d.ord_bas
        lf = max(2.0e-8, lf)
        lo[("PRCM", "COMI")] = pb + lf * (1.0 - (1.0 - 0.02) ** (t - ref)) * 0.3
        pbr = d.ord_bast if pd("PRCM", "COMI", "BAST") else d.ord_bas
        up[("PRCM", "COMI")] = max(pb + lf * (1.0 - (1.0 - 0.02) ** (t - ref)) * 0.6, pb * 1.04 ** (t - pbr))
    if (not R("p_data", "QUTB", "COMI") and not R("p_data", "HCOM", "COMI") and d.wba7
            and pd("HCOM", "COMI", "BASM")):
        b, ref = bb("HCOM", "COMI")
        lo[("HCOM", "COMI")] = max(2.0e-8, b) * (1 - 0.01) ** (t - ref)
        up[("HCOM", "COMI")] = max(2.0e-8, b) * (1 + 0.01) ** (t - ref)
    # DCOW's milk yield (p_data BASM, BAST): the weighted mean of DCOL and DCOH
    dcow = {}
    for st in ("BASM", "BAST"):
        lv = pd("DCOL", "LEVL", st) + pd("DCOH", "LEVL", st)
        dcow[st] = ((pd("DCOL", "COMI", st) * pd("DCOL", "LEVL", st) + pd("DCOH", "COMI", st) * pd("DCOH", "LEVL", st))
                    / lv) if lv else pd("DCOW", "COMI", st)
    dy, dref = (dcow["BAST"], d.ord_bast) if dcow["BAST"] else (dcow["BASM"], d.ord_bas)
    late = max(0, 2050 - d.lst_exante) / (2050 - d.lst_dgagri)
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI") or R("p_data", c, "COMI") or not pd(c, "COMI", "BASM"):
            continue
        b, _ = bb(c, "COMI")
        base = pd(c, "COMI", "BASM") * b / pd(c, "COMI", "BASM")
        gap = (REF_MILK_YIELD - dy) / REF_MILK_YIELD
        if R("expertup", c, "COMI"):
            up[(c, "COMI")] = R("expertup", c, "COMI")
        else:
            up[(c, "COMI")] = base * (1 + (0.0125 + 0.0075 * gap + 0.0075 * late)) ** (t - dref)
        if R("expertlo", c, "COMI"):
            lo[(c, "COMI")] = R("expertlo", c, "COMI")
        else:
            lo[(c, "COMI")] = base * (1 + (0.0025 + 0.0075 * gap - 0.0025 * late)) ** (t - dref)
        # the member state's own (SUM(MAP_RR(MS, Rest), 1) GT 1) only with NUTS2 regions in Rest: not at MS level
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI"):
            continue
        e, s_ = R("Expert", c, "COMI"), sup(c, "COMI")
        if e == s_ and LO((c, "COMI")) != UP((c, "COMI")) and s_:
            lo[(c, "COMI")] = min(LO((c, "COMI")), 0.95 * s_)
            up[(c, "COMI")] = max(UP((c, "COMI")), 1.05 * s_)
    for c in sorted(B.cols_est):
        if (c, "COMI") not in B.pact_to_y or not n(c, "COMI"):
            continue
        if t > d.fst_exante + 2 and LO((c, "COMI")) > 0:
            prev = (d.step3_prev.get((c, "COMI"), 0.0) * 1.0025 ** (t - d.prev)
                    if d.prev is not None and d.prev > d.lst_expostt else 0.0)
            lo[(c, "COMI")] = max(prev, LO((c, "COMI")))
            if LO((c, "COMI")) != UP((c, "COMI")):
                up[(c, "COMI")] = max(UP((c, "COMI")), LO((c, "COMI")) * 1.1)


def _biofuel(d, B, lo, up, UP, n, R, fx):
    """biofuel_bounds.gms (fix_est.gms l. 845)."""
    S_ = lambda c, w: R("Support", c, w)                                     # noqa: E731
    for b in sorted(B.bio_stock):
        if n("PRCB", b):
            lo[("PRCB", b)] = S_("PRCB", b) * 0.999
            up[("PRCB", b)] = S_("PRCB", b) * 1.001
        if n("PRCBY", b):
            lo[("PRCBY", b)] = S_("PRCBY", b)
            up[("PRCBY", b)] = S_("PRCBY", b)
        if n("BIOF", b):
            lo[("BIOF", b)] = S_("BIOF", b) * 0.8
            up[("BIOF", b)] = S_("BIOF", b) * 1.2
    if UP(("GROF", "SUGB")) == 0:
        lo[("BIOF", "SUGA")] = 0.0
    for s in sorted(B.seco_biof):
        for c, fl, fu in (("MAPR", 0.95, 1.05), ("BIOF", 0.9999, 1.05), ("INDM", 0.95, 1.05), ("SECG", 0.99, 1.01),
                          ("NAGR", 0.95, 1.05), ("UVAD", 0.95, 1.05)):
            if n(c, s):
                lo[(c, s)] = S_(c, s) * fl
                up[(c, s)] = S_(c, s) * fu
        if not n("NAGR", s):
            fx(("NAGR", s), 0.0)
        if not n("SECG", s):
            fx(("SECG", s), 0.0)
    if n("NECR", "LEVL"):
        lo[("NECR", "LEVL")] = S_("NECR", "LEVL") * 0.95
        up[("NECR", "LEVL")] = S_("NECR", "LEVL") * 1.05
        lo[("NECR", "OCRO")] = S_("NECR", "OCRO") * 0.95
        up[("NECR", "OCRO")] = S_("NECR", "OCRO") * 1.05
    for (c, w), v in sorted(d.res.get("Support", {}).items()):
        if v and abs(v) <= 1e-14 and (c in ("BIOF", "PRCB", "PRCBY") or w in ("BIOE", "BIOD", "DDGS")):
            fx((c, w), 0.0)
    if S_("BIOF", "CERE") < 1e-13:
        fx(("BIOF", "CERE"), 0.0)
    if S_("MAPR", "BIOE") < 1e-13:
        fx(("MAPR", "BIOE"), 0.0)

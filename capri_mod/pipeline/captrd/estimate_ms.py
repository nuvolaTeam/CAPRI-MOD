"""CAPTRD's constrained estimation of a member state, the NLP m_trendMS (captrd/equations.gms, captrd/estimate_ms.gms,
CAPRI star 3.0; captrd.gms l. 1058-1060, Solve1 and Solve2 of the ex-ante loop): for one member state and ex-ante year,
the values V_EstV(MS, col, row, t) closest to the supports (the weighted squared deviations SSQ) that meet the
consistency equations below.

This module holds the equations (stage 2e, first part): `residuals` evaluates each of m_trendMS's equations
(equations.gms l. 896-902) at a point, with the domain conditions of equations.gms, for one member state (CAPTRD's
Rest and MSEst are the member state alone in estimate_ms.gms l. 41-46, so CARD(Rest) = 1 and the EU000000 exclusions
do not apply). A residual is lhs - rhs: zero for =E=, at most zero for =L=, at least zero for =G=.

Inputs (captrd's own symbols): V, the point {(col, row): value} (V_EstV; zero where not given, as a GAMS level);
nobs, the positions with data (p_data(MS, col, row, "nObs") nonzero); bas, basm, const, slope (p_data's "BAS", "BASM",
"Const", "Slope"); pdata, P_Result's "p_data" of the year (the exogenous series: INHA.LEVL, QUTS.SUGA, the SETR rates);
coco, the positions with a COCO value in the year (P_Result's "coco"); support, the supports (P_Result's "Support");
lo, up, the variables' bounds (V_EstV.LO, .UP; their equality takes some equations out, l. 184-186, 400-402, 573,
598-599, 607-608); the sets (Sets) and the year.

GAMS's semantics kept: a sum over an empty set is zero; a $-condition on a term drops it; V_EstV of a position not in
the model is zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from capri_mod.csvio import read_csv
from capri_mod.pipeline.captrd import requirements as _RQ

K2 = Tuple[str, str]

#: equations.gms l. 617-630: SEED_ keeps 5% of production above seed and on-farm losses
SEED_SHARE = 0.95
#: l. 637-708: PosUp_ and PosLo_, the band around the base year's seed and loss rates
POS_UP_FAC = 0.8
POS_UP_ADD = -0.1
POS_LO_FAC = 1.2
POS_LO_ADD = 0.1
#: l. 521-530: feeding efficiency, 0.2% a year since 2000 (without p_globiomTightLink, empty in the reference run);
#: the same factor as the requirement functions' (requirements.py)
REQS_EFF = _RQ.EFFICIENCY
REQS_YEAR0 = _RQ.EFFICIENCY_FROM
#: l. 588-593: Dailyup_, BULF's daily growth at most 0.4 kg plus 0.0016 per kg of live weight
DAILY_BASE = 0.4
DAILY_SLOPE = 0.0016
#: l. 295-308: ethanol beets give vinasse, with 10% of the energy of molasses: the molasses of the ethanol beets is
#: cut by 90%
MOLA_VINASSE = 0.9
#: days per year (HERD_ l. 598-603, NUTBAL_ l. 740-746)
DAYS_YEAR = 365
#: SSQS_ (l. 801-878): the standard error's floor relative to the support, the objective's weight, the deviation
#: (10% of the support) of the scaling term, the STCM pull's scale (5% of GROF's support) and the floors
WEIGHT_STD_ERR = 0.005
SSQ_WEIGHT = 1000.0
SSQ_SCALE_DEV = 0.10
STCM_SCALE = 0.05
SSQ_EPS = 1.0e-5


@dataclass
class Sets:
    """CAPTRD's sets used by m_trendMS's equations (sets.gms, sets_captrd.gms); pairs as (d0, d1)."""
    cols_est: Set[str]            # S_ColsEst (= S_ColsEst1 in estimate_ms.gms l. 50)
    rows_est: Set[str]            # S_RowsEst (= S_RowsEst1)
    mcact: Set[str]
    mpact: Set[str]
    maact: Set[str]
    arbact: Set[str]
    rset: Set[str]
    landuse_arto: Set[str]        # LandUseARTO
    pact_to_io: Set[K2]
    pact_to_y: Set[K2]
    pact_to_o: Set[K2]
    pact_to_i: Set[K2]
    grpr: Set[str]
    grpc: Set[str]
    rows_lab: Set[str]
    rows_to_g: Set[K2]            # ROWS_TO_G(row, group)
    cropc_to_g: Set[K2]           # CROPC_TO_G(crop, group)
    secod: Set[str]
    prcd: Set[K2]                 # PRCD(secondary, primary)
    resimp: Set[str]
    resimp_t_o: Set[K2]           # RESIMP_T_O(by-product, primary)
    mlkcnt: Set[str]
    mlkseco: Set[str]
    feed: Set[str]
    feed_to_o: Set[K2]            # FEED_TO_O(feed, product)
    oyani: Set[str]
    iyani: Set[str]
    o_to_yani: Set[K2]            # O_TO_YANI(young animal, input)
    breed_act: Set[str]
    meat: Set[str]
    bulf: Set[str]
    split_acts_lo: Set[str]
    lo_to_hi: Set[K2]
    mrkbale: Set[str]             # MrkBalE (the market balance positions)
    mrkbalee: Set[str]            # MrkBaleE (those of MBALGRP_)
    reqst: Set[str]
    ncnc: Set[str]
    mlko: Set[str]
    dompos: Set[str]
    fuel_rows: Set[str]
    oseco: Set[str]
    stock_to_by: Set[K2]          # STOCK_TO_BY(stock, by-product)
    bio_stock: Set[str]
    seco_biof: Set[str]
    stock_to_fuel: Set[K2]        # STOCK_TO_FUEL(stock, fuel)
    poul: Set[str]                # the activities of P_T_ActAgg(., "POUL")
    lu_units: Dict[str, float] = field(default_factory=dict)        # p_LUUnits
    carcass_share: Dict[str, float] = field(default_factory=dict)   # p_carcassShare
    start_wgt: Dict[str, float] = field(default_factory=dict)       # p_startWgt
    ncnc_cont: Dict[K2, float] = field(default_factory=dict)        # p_NCNC_CONT(row, ncnc)


@dataclass
class Point:
    """One member state's estimation data in one ex-ante year (see the module's docstring)."""
    V: Dict[K2, float]
    nobs: Set[K2]
    bas: Dict[K2, float]
    basm: Dict[K2, float]
    const: Dict[K2, float]
    slope: Dict[K2, float]
    pdata: Dict[K2, float]
    coco: Set[K2]
    support: Dict[K2, float]
    lo: Dict[K2, float]
    up: Dict[K2, float]
    year: int
    exante_d: bool = False        # the year is an ex-ante year with observed data (ExAnteD)


INF = float("inf")

class OSet(dict):
    """A set iterated in sorted order (a dict of its members), so the equations' sums and the NLP built from them do
    not depend on Python's hash order (PYTHONHASHSEED)."""

    def __init__(self, items=()):
        super().__init__((k, None) for k in sorted(set(items)))

    def __and__(self, other):
        return OSet(k for k in self if k in other)

    def __or__(self, other):
        return OSet(list(self) + list(other))

    def __sub__(self, other):
        return OSet(k for k in self if k not in other)


#: Sets fields read from capri_data/pipeline/captrd/sets/<file>.csv (tools/build/build_captrd_sets.py)
_SET_FILES = {"cols_est": "s_colsest", "rows_est": "s_rowsest", "landuse_arto": "landusearto",
              "breed_act": "breedact", "split_acts_lo": "splitactslo", "bio_stock": "biostock"}


def read_sets(sets_dir: Path = None, params_dir: Path = None, dat_dir: Path = None) -> Sets:
    """The estimation's sets and parameters: capri_data/pipeline/captrd/sets (build_captrd_sets.py), params
    (build_captrd_estimation_params.py) and dat/p_luunits.csv (build_captrd_dat.py)."""
    from capri_mod.pipeline.captrd import prepare as _P
    sets_dir = _P.SETS_DIR if sets_dir is None else sets_dir
    params_dir = sets_dir.parent / "params" if params_dir is None else params_dir
    dat_dir = _P.DAT_DIR if dat_dir is None else dat_dir
    kw = {}
    for f in Sets.__dataclass_fields__.values():
        if f.name in ("lu_units", "carcass_share", "start_wgt", "ncnc_cont", "poul"):
            continue
        d = read_csv(sets_dir / f"{_SET_FILES.get(f.name, f.name)}.csv", keep_default_na=False,
                     dtype=str)
        kw[f.name] = OSet(zip(d.d0, d.d1)) if "d1" in d.columns else OSet(d.d0)
    agg = read_csv(sets_dir / "p_t_actagg.csv", keep_default_na=False, dtype=str)
    kw["poul"] = OSet(a for a, g in zip(agg.d0, agg.d1) if g == "POUL")
    lu = read_csv(dat_dir / "p_luunits.csv", keep_default_na=False)
    kw["lu_units"] = dict(zip(lu.act, lu.value.astype(float)))
    for name, fn in (("carcass_share", "carcass_share"), ("start_wgt", "start_wgt")):
        d = read_csv(params_dir / f"{fn}.csv", keep_default_na=False)
        kw[name] = dict(zip(d.d0, d.value.astype(float)))
    d = read_csv(params_dir / "ncnc_cont.csv", keep_default_na=False)
    kw["ncnc_cont"] = dict(zip(zip(d.d0, d.d1), d.value.astype(float)))
    return Sets(**kw)


def residuals(p: Point, S: Sets, var=None, level: Dict[K2, float] = None) -> List[Tuple[str, tuple, str, object]]:
    """Each equation of m_trendMS at p: (name, index, sense, lhs - rhs); sense "E", "L" or "G".

    var: None (the residuals at p.V) or a function (col, row) -> the variable's symbol (e.g. casadi SX), for the NLP;
    level: V_EstV.L where the equations' domains use it (DDGS_, BIOF_: the start point; default p.V)."""
    V = (lambda c, w: p.V.get((c, w), 0.0)) if var is None else var   # noqa: E731
    L = (lambda c, w: (p.V if level is None else level).get((c, w), 0.0))   # noqa: E731
    n = lambda c, w: (c, w) in p.nobs                            # noqa: E731
    bas = lambda c, w: p.bas.get((c, w), 0.0)                    # noqa: E731
    lo = lambda c, w: p.lo.get((c, w), 0.0)                      # noqa: E731
    up = lambda c, w: p.up.get((c, w), INF)                      # noqa: E731
    out: List[Tuple[str, tuple, str, float]] = []
    add = lambda name, idx, sense, r: out.append((name, idx, sense, float(r) if var is None else r))   # noqa: E731
    rows = sorted(S.rows_est)
    cols = sorted(S.cols_est)

    # AREAB_ (l. 107-112), LANDUSEB_ (l. 116-121)
    if any(m in S.cols_est for m in S.mcact):
        add("AREAB_", (), "E", sum(V(m, "LEVL") for m in S.mcact if n(m, "LEVL")) - V("UAAR", "LEVL"))
    if any(m in S.cols_est for m in S.landuse_arto):
        add("LANDUSEB_", (), "E", sum(V(m, "LEVL") for m in S.landuse_arto if n(m, "LEVL")) - V("ARTO", "LEVL"))
    # STRA_ (l. 125-133)
    for m in sorted(S.mcact):
        ys = [o for a, o in S.pact_to_y if a == m]
        if (sum(bas(m, o) for o in ys) and n(m, "LEVL") and n(m, "STRA") and (m, "STRA") in S.pact_to_o
                and m in S.cols_est):
            add("STRA_", (m,), "E", V(m, "STRA") - sum(V(m, o) * bas(m, "STRA") / bas(m, o) for o in ys if bas(m, o)))
    # OSET_ (l. 141-147): the set-aside rates are P_Result's p_data of the year
    if any(m in S.cols_est and n(m, "LEVL") and p.pdata.get((m, "SETR"), 0.0) for m in S.mcact):
        lhs = 0.0
        for a in S.arbact:
            if n(a, "LEVL"):
                sr = p.pdata.get((a, "SETR"), 0.0)
                lhs += V(a, "LEVL") * 0.01 * sr / (1.0 - 0.01 * sr)
        add("OSET_", (), "E", lhs - sum(V(r, "LEVL") for r in S.rset))
    # GROF_ (l. 151-165)
    for w in rows:
        acts = [a for a, o in S.pact_to_io if o == w and a in S.mpact]
        if n("GROF", w) and w not in S.grpr and w not in S.rows_lab and acts:
            add("GROF_", (w,), "E", sum(V(a, w) * V(a, "LEVL") for a in acts if n(a, w) and n(a, "LEVL")) * 0.001
                - V("GROF", w))
    # LABO_ (l. 172-176)
    if n("GROF", "LABO"):
        add("LABO_", (), "E", V("GROF", "LABH") + V("GROF", "LABN") - V("GROF", "LABO"))
    # MAPR_ (l. 286-309)
    for s in sorted(S.secod):
        if not n("MAPR", s):
            continue
        rhs = sum(V("PRCM", w) * V("PRCY", s) for sd, w in S.prcd
                  if sd == s and w in S.rows_est and n("PRCM", w) and n("PRCY", s))
        if s == "MOLA" and lo("PRCY", "SUGA") > 0:
            rhs -= V("BIOF", "SUGA") / V("PRCY", "SUGA") * V("PRCY", "MOLA") * MOLA_VINASSE
        add("MAPR_", (s,), "E", V("MAPR", s) - rhs)
    # SugaQuot_ (l. 311-322), SugaMinBiof_ (l. 326-331), MaizMinIndm_ (l. 337-341)
    q = p.pdata.get(("QUTS", "SUGA"), 0.0)
    if q and ("MAPR", "SUGA") not in p.coco:
        rhs = q + sum(V(c, "SUGA") for c in ("INDM", "BIOF", "LOSM") if n(c, "SUGA"))
        add("SugaQuot_", (), "L", V("MAPR", "SUGA") - rhs)
    if n("BIOF", "SUGA") and ("MAPR", "SUGA") not in p.coco:
        add("SugaMinBiof_", (), "G", V("MAPR", "SUGA") - V("BIOF", "SUGA"))
    if n("PRCI", "MAIZ"):
        add("MaizMinIndm_", (), "G", V("INDM", "MAIZ") - V("PRCI", "MAIZ"))
    # MaprByFeed_ (l. 346-368)
    for b in sorted(S.resimp):
        if not n("MAPR", b):
            continue
        ws = [w for bb, w in S.resimp_t_o if bb == b]
        num = sum(V("HCOM", w) * n("HCOM", w) + V("PRCM", w) * n("PRCM", w) + V("INDM", w) * n("INDM", w)
                  + V("BIOF", w) * (n("BIOF", w) and w == "SUGA") for w in ws)
        den = sum(bas("HCOM", w) + bas("PRCM", w) + bas("INDM", w) + bas("BIOF", w) * (w == "SUGA") for w in ws)
        add("MaprByFeed_", (b,), "E", V("MAPR", b) - bas("MAPR", b) * num / den)
    # MLKCNT_ (l. 373-380)
    for m in sorted(S.mlkcnt):
        if n(m, "MILK"):
            rhs = sum((V("MAPR", s) - V("PRCM", s) * n("PRCM", s)) * V(m, s) for s in S.mlkseco
                      if n("MAPR", s) and n(m, s))
            add("MLKCNT_", (m,), "E", V("PRCM", "MILK") * V(m, "MILK") - rhs)
    # EAAG_ (l. 385-390)
    for w in rows:
        if n("EAAG", w) and n("UVAG", w) and n("GROF", w):
            add("EAAG_", (w,), "E", V("EAAG", w) - V("UVAG", w) * V("GROF", w) * 0.001)
    # REVE_ (l. 394-403)
    for a in sorted(S.mpact):
        u = up(a, "LEVL")
        if u > 0 and u < INF and n(a, "TOOU"):
            add("REVE_", (a,), "E", V(a, "TOOU") - sum(V(a, w) * V("UVAG", w) for aa, w in S.pact_to_o
                                                        if aa == a and w in S.rows_est and n(a, w) and n("UVAG", w))
                * 0.001)
    # UVAD_ (l. 407-412), UVADfuel_ (l. 416-421)
    for w in rows:
        if n("CSSP", w) and n("UVAD", w) and n("UVAG", w):
            add("UVAD_", (w,), "E", V("UVAD", w) - V("UVAG", w) - V("CSSP", w))
        if n("CTAX", w) and n("UVAD", w) and n("UVAG", w):
            add("UVADfuel_", (w,), "E", V("UVAD", w) - V("UVAG", w) - V("CTAX", w))
    # EXPE_ (l. 426-433), EXPETOT_ (l. 438-442)
    inha = p.pdata.get(("INHA", "LEVL"), 0.0)
    for w in rows:
        if n("EXPE", w) and n("UVAD", w) and n("HCOM", w) and w != "LEVL":
            add("EXPE_", (w,), "E", V("EXPE", w) - V("UVAD", w) * V("HCOM", w) / inha)
    if n("EXPE", "LEVL"):
        add("EXPETOT_", (), "E", V("EXPE", "LEVL") - sum(V("EXPE", w) for w in rows
                                                       if w != "LEVL" and w not in S.grpr and n("EXPE", w)))
    # FEED_ (l. 446-451)
    for f in sorted(S.feed):
        ws = [w for ff, w in S.feed_to_o if ff == f]
        if any(n("FEDM", w) for w in ws) and n("GROF", f):
            add("FEED_", (f,), "E", V("GROF", f) - sum(V("FEDM", w) for w in ws if w in S.rows_est and n("FEDM", w)))
    # DDGS_ (l. 455-459)
    st = [o for o, b in S.stock_to_by if b == "DDGS" and o in S.oseco]
    if any(n("BIOF", o) and L("PRCBY", o) for o in st):
        add("DDGS_", (), "E", V("MAPR", "DDGS") - sum(V("BIOF", o) * V("PRCBY", o) for o in st
                                                     if n("BIOF", o) and L("PRCBY", o)))
    # BIOF_ (l. 464-472)
    for s in sorted(S.seco_biof):
        st = [b for b, f in S.stock_to_fuel if f == s and b in S.bio_stock]
        if any(n("BIOF", b) and L("PRCB", b) for b in st):
            add("BIOF_", (s,), "E", V("MAPR", s) - V("NAGR", s) - V("SECG", s)
                - sum(V("BIOF", b) * V("PRCB", b) for b in st if n("BIOF", b) and n("PRCB", b)))
    # REQS_ (l. 522-540): the feed contents of the member state (MSEst is the member state)
    eff = REQS_EFF ** (p.year - REQS_YEAR0)
    for a in sorted(S.maact):
        for r_ in sorted(S.reqst):
            k = p.const.get((a, r_), 0.0) + p.slope.get((a, r_), 0.0)
            if not (k and a in S.cols_est and up(a, r_) != 0 and n(a, "LEVL")):
                continue
            yo = sum(V(a, o) for aa, o in S.pact_to_y if aa == a and n(a, o))
            lhs = (p.const.get((a, r_), 0.0) + p.slope.get((a, r_), 0.0) * yo) * eff * V(a, r_)
            rhs = sum(V(a, f) * p.basm.get((r_, f), 0.0) for f in S.feed if n(a, f))
            add("REQS_", (a, r_), "E", lhs - rhs)
    # LU_ (l. 545-549)
    if any(n(a, "LEVL") for a in S.maact):
        add("LU_", (), "E", V("LU", "LEVL") - sum(V(a, "LEVL") * S.lu_units.get(a, 0.0) for a in S.maact
                                                  if n(a, "LEVL")) / V("UAAR", "LEVL"))
    # OYANI_ (l. 553-561)
    for o in sorted(S.oyani):
        if n("GROF", o):
            add("OYANI_", (o,), "E", V("GROF", o) - V("STCM", o) * (o not in ("YCAM", "YCAF"))
                - sum(V("GROF", i) for oo, i in S.o_to_yani if oo == o and i in S.iyani and n("GROF", i)))
    # SlgwFem_ (l. 566-569)
    for b in sorted(S.breed_act):
        if n(b, "SLGW"):
            add("SlgwFem_", (b,), "E", V(b, "SLGW") * sum(V(b, i) for bb, i in S.pact_to_i if bb == b and i in S.iyani)
                - sum(V(b, m) for bb, m in S.pact_to_o if bb == b and m in S.meat) * 1000)
    # FinalWgt_ (l. 573-583), Dailyup_ (l. 588-593)
    for c in cols:
        cs = S.carcass_share.get(c, 0.0)
        ms = [m for a, m in S.pact_to_y if a == c and m in S.meat]
        if lo(c, "DAYS") != up(c, "DAYS") and any(n("GROF", m) for m in ms) and cs:
            g = 1.0 if c in S.poul else 0.001
            add("FinalWgt_", (c,), "E", sum(V(c, m) for m in ms) / cs
                - (S.start_wgt.get(c, 0.0) + V(c, "DAILY") * g * (V(c, "DAYS") - p.basm.get((c, "EDAYS"), 0.0))))
    if n("GROF", "BEEF"):
        for b in sorted(S.bulf):
            cs = S.carcass_share.get(b, 0.0)
            add("Dailyup_", (b,), "L", V(b, "DAILY") / 1000 - (DAILY_BASE + V(b, "BEEF") / cs * DAILY_SLOPE))
    # HERD_ (l. 598-603), SplitFix_ (l. 607-612)
    for a in sorted(S.maact):
        if lo(a, "HERD") != up(a, "HERD") and n(a, "HERD") and n(a, "LEVL"):
            add("HERD_", (a,), "E", V(a, "HERD") - V(a, "LEVL") * V(a, "DAYS") / DAYS_YEAR)
    for c in cols:
        if lo(c, "LEVL") != up(c, "LEVL") and n(c, "LEVL") and c in S.split_acts_lo:
            add("SplitFix_", (c,), "E", V(c, "LEVL") - sum(V(h, "LEVL") for lw, h in S.lo_to_hi if lw == c))
    # SEED_ (l. 617-630)
    for w in rows:
        if n("GROF", w) and (n("SEDM", w) or n("SEDF", w) or n("LOSF", w)) and w not in S.grpr:
            add("SEED_", (w,), "G", V("GROF", w) * SEED_SHARE * n("GROF", w)
                - sum(V(c, w) for c in ("SEDM", "SEDF", "LOSF") if n(c, w)))
    # PosUp_ (l. 637-662), PosLo_ (l. 664-708)
    for c in cols:
        if c not in ("SEDM", "SEDF", "LOSF", "LOSM"):
            continue
        for w in rows:
            if not n(c, w) or w in S.grpr:
                continue
            if c == "LOSM":
                on = (bas("MAPR", w) + bas("GROF", w) + bas("IMPT", w)) and not p.exante_d
                on_lo = ((bas("MAPR", w) * (not bas("GROF", w)) + bas("GROF", w) + bas("IMPT", w))
                         and not p.exante_d)
            else:
                on = on_lo = bas("GROF", w) and (c != "LOSF" or w not in ("COMI", "SGMI", "BEEF"))
            if c == "LOSM":
                qv = (V("GROF", w) * n("GROF", w) + V("MAPR", w) * ((not n("GROF", w)) and n("MAPR", w))
                      + V("IMPT", w) * n("IMPT", w))
                qb = (bas("GROF", w) * n("GROF", w) + bas("MAPR", w) * ((not n("GROF", w)) and n("MAPR", w))
                      + bas("IMPT", w) * n("IMPT", w))
            else:
                qv, qb = V("GROF", w), bas("GROF", w)
            if on:
                add("PosUp_", (c, w), "G", V(c, w) - (qv * bas(c, w) / qb * POS_UP_FAC + POS_UP_ADD))
            if on_lo:
                add("PosLo_", (c, w), "L", V(c, w) - (qv * bas(c, w) / qb * POS_LO_FAC + POS_LO_ADD))
    # MBAL_ (l. 714-736)
    uses = ("FEDM", "SEDM", "SEDF", "INDM", "PRCM", "BIOF", "HCOM", "LOSM", "LOSF", "EXPT", "INTP")
    for w in rows:
        if (any(n(e, w) for e in S.mrkbale if e not in ("GROF", "MAPR")) and w not in S.grpr
                and w not in S.reqst):
            res = (V("GROF", w) * n("GROF", w) + V("MAPR", w) * ((not n("GROF", w)) and n("MAPR", w))
                   + V("IMPT", w) * n("IMPT", w)) - sum(V(c, w) for c in uses if n(c, w))
            add("MBAL_", (w,), "E", res)
    # NUTBAL_ (l. 740-746)
    for k in sorted(S.ncnc):
        if n(k, "INCE"):
            add("NUTBAL_", (k,), "E", V(k, "INCE") * DAYS_YEAR
                - sum(V("INHA", w) * S.ncnc_cont.get((w, k), 0.0) for w in rows if n("INHA", w)))
    # HCOM_ (l. 750-755)
    for w in rows:
        if n("HCOM", w) and n("INHA", w) and w != "LEVL":
            add("HCOM_", (w,), "E", (V("HCOM", w) + V("LOSF", w) * (w in S.mlko)) * V("foodSh", w)
                - V("INHA", w) * inha * 0.001)
    # DOMM_ (l. 759-766), NTRD_ (l. 770-778)
    for w in rows:
        if ((p.support.get(("DOMM", w), 0.0) or n("DOMM", w)
             or any(p.support.get((d, w), 0.0) or n(d, w) for d in S.dompos)) and w not in S.fuel_rows):
            add("DOMM_", (w,), "E", V("DOMM", w) - sum(V(d, w) for d in S.dompos if n(d, w)))
        if p.support.get(("NTRD", w), 0.0) and (n("EXPT", w) or n("IMPT", w)):
            add("NTRD_", (w,), "E", V("NTRD", w) - V("EXPT", w) * n("EXPT", w) + V("IMPT", w) * n("IMPT", w))
    # MBALGRP_ (l. 782-788), GRPLVL_ (l. 792-798)
    for e in sorted(S.mrkbalee):
        for g in sorted(S.grpr):
            ws = [w for w, gg in S.rows_to_g if gg == g and n(e, w)]
            if len(ws) > 1 and n(e, g):
                add("MBALGRP_", (e, g), "E", V(e, g) - sum(V(e, w) for w in ws))
    for g in sorted(S.grpc):
        ms = [m for m, gg in S.cropc_to_g if gg == g and m in S.mcact and n(m, "LEVL")]
        if len(ms) > 1 and n(g, "LEVL"):
            add("GRPLVL_", (g,), "E", V(g, "LEVL") - sum(V(m, "LEVL") for m in ms))
    return out


def requirement_factor(p: Point, S: Sets, V: Dict[K2, float], a: str, r_: str) -> float:
    """The requirement function of REQS_ (equations.gms l. 521-530): (Const + Slope x main output) x feeding efficiency.
    In the estimation V_EstV(MAACT, ReqsT) is the requirement relative to it; CAPTRD stores the absolute requirement,
    this factor times the variable (captrd.gms l. 1195-1216, after the estimation)."""
    k = p.const.get((a, r_), 0.0) + p.slope.get((a, r_), 0.0) * sum(
        V.get((a, o), 0.0) for aa, o in S.pact_to_y if aa == a and (a, o) in p.nobs)
    return k * REQS_EFF ** (p.year - REQS_YEAR0)


def requirements_relative(p: Point, S: Sets, V: Dict[K2, float]) -> Dict[K2, float]:
    """V with the requirements as stored by CAPTRD (absolute; captrd.gms l. 1205-1216, where Const + Slope is nonzero,
    the column estimated, with a BASM requirement and a herd) turned back into the estimation's relative ones."""
    out = dict(V)
    for a in S.maact:
        if a not in S.cols_est or (a, "LEVL") not in p.nobs:
            continue
        for r_ in S.reqst:
            if (p.const.get((a, r_), 0.0) + p.slope.get((a, r_), 0.0)) and p.basm.get((a, r_), 0.0) and (a, r_) in V:
                f = requirement_factor(p, S, V, a, r_)
                if f:
                    out[(a, r_)] = V[(a, r_)] / f
    return out


def from_stored(p: Point, S: Sets, V: Dict[K2, float]) -> Dict[K2, float]:
    """The estimation's values from CAPTRD's stored step2 (P_Result "Step2", after its reporting): the requirements
    relative again (requirements_relative), DOMM the estimation's, which the reporting keeps as DEMD
    (aggreg_and_report.gms l. 293-294: DEMD = DOMM, then DOMM = the sum of all DOMPOS)."""
    out = requirements_relative(p, S, V)
    for (c, w), v in V.items():
        if c == "DEMD":
            out[("DOMM", w)] = v
    return out


#: equations whose stored terms CAPTRD's reporting overwrites after the estimation, so they cannot be checked at the
#: stored step2: name -> (rows or None for all, reason)
REPORTED = {
    "OYANI_": (None, "STCM(OYANI) is not stored in step2 (estimate_ms.gms l. 454-457 keep it in estP only)"),
    "HCOM_": ("OAGG", "INHA of the product groups is the members' sum (aggreg_and_report.gms l. 216)"),
    "HCOM_HFCS": (("HFCS",), "HCOM and MAPR of HFCS are recomputed (aggreg_and_report.gms l. 70-80)"),
    "HCOM_MLKO": (("COMI", "SGMI"), "LOSF of the milks enters without a data condition (l. 754): a free variable "
                                    "where there are no data, not stored"),
    "FinalWgt_": (None, "for an activity without data its terms are free variables (V_EstV is a free variable, "
                        "equations.gms l. 28-32), not stored (estimate_ms.gms l. 454-457)"),
}


def checkable(name: str, idx: tuple, oagg: Set[str], stored: bool = True, nobs: Set[K2] = frozenset(),
              mlko: Set[str] = frozenset()) -> bool:
    """False for the equations whose terms the stored step2 does not hold as estimated (REPORTED); nobs: the positions
    with data."""
    if not stored:
        return True
    if name == "FinalWgt_" and (idx[0], "LEVL") not in nobs:
        return False
    if name == "HCOM_" and idx and ("LOSF", idx[0]) not in nobs and idx[0] in mlko:
        return False
    if name == "OYANI_" and idx and idx[0] not in ("YCAM", "YCAF"):
        return False
    if name == "HCOM_" and idx and idx[0] in oagg:
        return False
    if name in ("HCOM_", "MBAL_", "DOMM_", "MAPR_") and idx and idx[0] == "HFCS":
        return False
    return True


def objective(p: Point, S: Sets, var, wvar: Dict[K2, float], lo: Dict[K2, float], up: Dict[K2, float],
              exante_t: bool):
    """SSQS_ (equations.gms l. 803-878) for one member state (CARD(Rest) = 1, so every weight is 1): the squared
    deviations from the supports over their standard errors, max(sqrt(wVarErr), 0.005 x support) + 1e-5, times 1000,
    plus STCM of the young animals pulled to zero in the years without data (ExAnteT), over the same sum at 10% of
    the supports plus 1. The terms: the positions with a support, a wVarErr and lo != up. lo, up: the bounds (INF
    where none)."""
    num, den = 0.0, 1.0
    for k, sv in sorted(p.support.items()):
        if not sv or not wvar.get(k, 0.0) or k[0] not in S.cols_est or k[1] not in S.rows_est:
            continue
        if lo.get(k, -INF) == up.get(k, INF):
            continue
        sig = max(wvar[k] ** 0.5, WEIGHT_STD_ERR * sv) + SSQ_EPS
        num = num + ((var(*k) - sv) / sig) ** 2 * SSQ_WEIGHT
        den += (SSQ_SCALE_DEV * sv / sig) ** 2
    if exante_t:
        for o in sorted(S.oyani):
            sg = p.support.get(("GROF", o), 0.0)
            if ("STCM", o) in p.nobs and sg:
                num = num + (var("STCM", o) / max(STCM_SCALE * sg, SSQ_EPS)) ** 2 * SSQ_WEIGHT
    return num / den


def violations(res: Iterable[Tuple[str, tuple, str, float]], tol: float, scale: Dict = None):
    """The residuals beyond tol: equalities off by more than tol, inequalities violated by more than tol."""
    bad = []
    for name, idx, sense, r in res:
        if (sense == "E" and abs(r) > tol) or (sense == "L" and r > tol) or (sense == "G" and r < -tol):
            bad.append((name, idx, sense, r))
    return bad

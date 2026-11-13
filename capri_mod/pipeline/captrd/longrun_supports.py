"""CAPTRD's expert supports from the long-run sources (captrd/longrun_supports.gms, included by captrd/expert_support.gms
l. 786; CAPRI star 3.0), with %GlobiomAact% and %FixExogenFactGlobiom% off and the long-run selection %SelecScen% a
setting (captrd.longrun_scenario).

In GAMS's order (line numbers of longrun_supports.gms):
  l. 43-69     B2000: the 1999-2001 mean of p_data for the price, demand, production and processing columns, the levels,
               herds, feed requirements, milk processing and the yields of single-activity outputs; stored on the
               ex-ante years where the series has nObs
  l. 100-185   the scenario's change factors (p_longRunInfoAll of longrun_info_fac_%reg_agg%.gdx), 2000 = 1, World's
               rape and sunflower prices as soya's; the bright and cv50 corrections; market balance positions of
               sugar dropped where biofuel takes more than 80%
  l. 196-305   Longrun of the long-run years: levels, production, yields, market production, prices (with p_infl),
               demand, milk processing, human consumption from GLOBIOM's shares
  l. 307-354   linear interpolation, kept on yearsCur (ex post only 2000, BAS, BAST and INHA), scaled to BAST
  l. 362-389   INHA.LEVL p_data (macro.py)
  l. 427-431   HCOM.SUGA: the support per head, within 0.8-1.2 times the base year's, as Absolute
  l. 446-545   the national PercentChange merged with Longrun from %phaseInYr% (Longrun1); Longrun1 as Absolute where
               nothing else is given (trust 1 or 5; FORE +3, OLND +1)

In the reference run the selected scenario (globiom_eu_bright_s0_2023+REFERENCE+REFERENCE) is not in the long-run
file, so p_longrunInfo is empty and only B2000, INHA and HCOM.SUGA act (CAPTRD's results hold no Longrun records).
A statement whose right side reads the parameter it assigns takes the values from before it, as GAMS does.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set, Tuple

K3 = Tuple[str, str, str]
K4 = Tuple[str, str, str, int]

#: l. 39: the years of the base of the long-run change factors
B2000_YEARS = (1999, 2000, 2001)
#: l. 85-93: the long-run years, the weight of the long-run sources in 2050 and the exponent of its increase
LONG_YEARS = (2000, 2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2085)
LONG_WGT = 0.9
LONG_EXP = 0.7
#: l. 485, 493: Ireland's lower weight (Food Harvest 2020)
IR_LESS = 0.2
#: l. 482: the year by which the long-run weight is reached
WGT_YEAR = 2050
#: l. 185: biofuel's share of sugar demand above which the sugar balance information is dropped
BIOF_SHARE_MAX = 0.8
#: l. 212-221: the long-run base kept only if at least a tenth of CAPRI's
DATA_MIN_SHARE = 0.1
#: l. 345: the scaling factor applies where the long-run value is above 1% of BAST (BASM)
FAC_MIN = 1.e-2
#: l. 428: HCOM.SUGA per head within these factors of the base year's
SUGA_LO = 0.8
SUGA_UP = 1.2
#: l. 535-544: trust levels of Longrun1 as Absolute
TRUST_LOW = 1.0
TRUST_MID = 5.0
TRUST_FORE = 3.0
TRUST_OLND = 1.0
TINY_LEVL = 0.1
#: the bri2 and cv50 corrections (l. 155-182)
BRIGHT = "GLOBIOM_EU_BRIGHT_S0_2023+REFERENCE+REFERENCE"
CV50 = "GLOBIOM_EU_EUCLIMIT6_S2_50CV"
BRIGHT_FROM = 2030
CV50_FROM = 2040


@dataclass
class Context:
    ms: Sequence[str]
    msincl: Sequence[str]
    pdata: Dict[K4, float]                     # p_data of the calendar years
    nobs: Set[K3]
    basm: Dict[K3, float]
    bast: Dict[K3, float]                      # P_DATA(..., "BAST")
    s_colsest: Iterable[str]
    s_rowsest: Iterable[str]
    pact: Iterable[str]
    req_feed: Iterable[str]
    reqst: Iterable[str]
    pact_to_y: Iterable[Tuple[str, str]]
    pact_to_o: Iterable[Tuple[str, str]]
    mrkbalee: Iterable[str]
    mlk_pro: Iterable[str]
    cows_act: Iterable[str]
    exante: Sequence[int]
    exantet: Sequence[int]
    expostt: Sequence[int]
    years_cur: Sequence[int]
    base_year: int
    bast_year: int
    lst_expost: int
    lst_exante: int
    lst_dgagri: int
    phase_in: int
    infl: float                                # p_infl (captrd.gms l. 327)
    support: Dict[K4, float]                   # the supports before the expert supports
    dgagri1: Dict[K4, float]
    map_rr: Iterable[Tuple[str, str]]
    cur_europ_agg: Iterable[str]
    inha: Dict[Tuple[str, int], float]         # INHA.LEVL p_data of the years (macro.inha_pdata)
    scenario: str = ""                         # %SelecScen%; "" = the setting captrd.longrun_scenario
    longrun_info_all: Dict[Tuple[str, str, str, str, str, object], float] = field(default_factory=dict)


@dataclass
class Result:
    b2000: Dict[K4, float] = field(default_factory=dict)       # p_result(..., ExAnte, "B2000")
    longrun: Dict[K4, float] = field(default_factory=dict)
    longrun1: Dict[K4, float] = field(default_factory=dict)


def read_info(dat_dir) -> Dict[Tuple[str, str, str, str, str, object], float]:
    """p_longRunInfoAll(region, col, row, info, scenario, year or "B2000") of tools/build/build_captrd_longrun.py."""
    import csv
    from pathlib import Path
    out = {}
    with open(Path(dat_dir) / "longrun_p_longruninfoall.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            y = r["year"]
            out[(r["region"], r["col"], r["row"], r["info"], r["scenario"], int(y) if y.isdigit() else y)] = \
                float(r["value"])
    return out


def info_source(dat_dir, scenario: str = "") -> Dict[Tuple[str, str, str, str, str, object], float]:
    """p_longRunInfoAll as the setting captrd.longrun_from_globiom chooses: the long-run file's records (read_info) or
    CAPRI's conversion of the selection's GLOBIOM-EU file (globiom.longrun_info_all, on the external sources'
    Parquet: capri_sources/dat_parquet)."""
    from pathlib import Path
    from capri_mod.settings import current as _settings
    if not bool(_settings().get("captrd.longrun_from_globiom")):
        return read_info(dat_dir)
    from capri_mod.external_paths import SOURCES
    from capri_mod.pipeline.captrd import globiom as GL
    from capri_mod.pipeline.captrd import prepare as P
    pq = SOURCES / "dat_parquet"
    return GL.longrun_info_all(
        scenario or str(_settings().get("captrd.longrun_scenario")), sets_dir=P.SETS_DIR / "globiom",
        capri_sets_dir=P.SETS_DIR / "globiom", dat_dir=Path(dat_dir), globiom_root=pq / "global",
        capreg_root=pq / "capreg", datamarket=pq / "global" / "fao_agg_17_defaulta" / "p_dataMarket.parquet",
        worldpop=pq / "arm" / "allpop" / "worldPop.parquet")


def _ofrom_one_pact(pact: Iterable[str], pact_to_o: Iterable[Tuple[str, str]]) -> Set[str]:
    """sets_captrd.gms l. 278-283: outputs of one production activity, COMI and GRAS."""
    pa = set(pact)
    n: Dict[str, int] = {}
    for a, o in pact_to_o:
        if a in pa:
            n[o] = n.get(o, 0) + 1
    return {o for o, k in n.items() if k == 1} | {"COMI", "GRAS"}


def supports(S, X: Context) -> Result:
    """The file's changes to S (national_supports.Expert: Absolute, PercentChange, TrustLevl), in place."""
    out = Result()
    ms = list(X.ms)
    exante = list(X.exante)
    pact, reqf, reqst = set(X.pact), set(X.req_feed), set(X.reqst)
    pty = set(X.pact_to_y)
    ofrom = _ofrom_one_pact(X.pact, X.pact_to_o)
    run = X.lst_exante >= X.lst_dgagri
    # ---- l. 43-69: B2000
    b2: Dict[K3, float] = {}
    if run:
        acc: Dict[K3, List[float]] = {}
        for (r, c, w, y), v in X.pdata.items():
            if y in B2000_YEARS and v and r in set(ms) and (
                    c in ("UVAG", "DOMM", "GROF", "MAPR", "HCOM") or w in ("LEVL", "HERD")
                    or (w in reqf and c in pact) or w in reqst or (w in ("MILK", "COMI") and c == "PRCM")
                    or ((c, w) in pty and w in ofrom)):
                acc.setdefault((r, c, w), []).append(v)
        b2 = {k: sum(v) / len(v) for k, v in acc.items()}
    cols, rows = set(X.s_colsest), set(X.s_rowsest)
    for k, v in b2.items():
        if k in X.nobs and k[1] in cols and k[2] in rows:
            for y in exante:
                out.b2000[(*k, y)] = v
    if not run:
        return out
    # ---- l. 100-119: the scenario's information
    if not X.scenario:
        from capri_mod.settings import current as _settings
        X.scenario = str(_settings().get("captrd.longrun_scenario"))
    scen = X.scenario.upper()
    info: Dict[Tuple[str, str, str, str, object], float] = {}
    for (r, c, w, i, sc, y), v in X.longrun_info_all.items():
        if sc.upper() == scen and v and (r in set(ms) or r.upper() == "WORLD") and (
                y in LONG_YEARS or (i == "share" and y == "B2000")):
            info[(r, c, w, i, y)] = v
    for (r, c, w) in {(k[0], k[1], k[2]) for k in info if k[3] == "factorB2000"}:
        info[(r, c, w, "factorB2000", 2000)] = 1.0
    world = [r for r in {k[0] for k in info} if r.upper() == "WORLD"]
    for wr in world:
        for y in LONG_YEARS:
            for o in ("RAPE", "SUNF"):
                v = info.get((wr, "UVAP", "SOYA", "factorB2000", y), 0.0)
                if v:
                    info[(wr, "UVAP", o, "factorB2000", y)] = v
                else:
                    info.pop((wr, "UVAP", o, "factorB2000", y), None)

    def f(r, c, w, y, i="factorB2000"):
        return info.get((r, c, w, i, y), 0.0)
    # ---- l. 155-182: corrections of the bright and cv50 scenarios
    if scen in (BRIGHT, CV50):
        y0 = BRIGHT_FROM if scen == BRIGHT else CV50_FROM
        for r in [r for r in X.msincl if r == "PL000000"]:
            for w in ("SGMT", "SGMI"):
                for y in LONG_YEARS:
                    if y > y0 and f(r, "PROD", w, y0):
                        info[(r, "PROD", w, "factorB2000", y)] = f(r, "PROD", w, y0)
    if scen == BRIGHT:
        for r in [r for r in X.msincl if r in ("NO000000", "CY000000", "MT000000")]:
            if f(r, "DOMM", "EGGS", BRIGHT_FROM):
                for y in LONG_YEARS:
                    if y > BRIGHT_FROM:
                        v = f(r, "PROD", "EGGS", BRIGHT_FROM) * f(r, "DOMM", "EGGS", y) / f(r, "DOMM", "EGGS", BRIGHT_FROM)
                        if v:
                            info[(r, "PROD", "EGGS", "factorB2000", y)] = v
                        else:
                            info.pop((r, "PROD", "EGGS", "factorB2000", y), None)
    # l. 185, on the values before it
    drop = [(r, y) for r in ms for y in LONG_YEARS if f(r, "BIOF", "SUGA", y, "share") > BIOF_SHARE_MAX]
    mrk = set(X.mrkbalee)
    for k in [k for k in info if k[2] == "SUGA" and k[1] in mrk and (k[0], k[4]) in set(drop)]:
        info.pop(k, None)

    data0 = {(r, c, w): v for (r, c, w, i, sc, y), v in X.longrun_info_all.items()
             if i == "data" and y == "B2000" and sc.upper() == scen}

    def data_b2000(r, c, w):
        return data0.get((r, c, w), 0.0)
    # ---- l. 196-305: Longrun of the long-run years
    L: Dict[K4, float] = {}

    def put(k, v):
        if v:
            L[k] = v
        else:
            L.pop(k, None)
    bm = X.basm
    for r in ms:
        for y in LONG_YEARS:
            for (rr, c, w) in [k for k in bm if k[0] == r and k[2] == "LEVL"]:          # l. 196-200
                if not bm.get((r, c, "HERD")):
                    put((r, c, "LEVL", y), f(r, c, "LEVL", y) * b2.get((r, c, "LEVL"), 0.0))
            for (rr, c, w) in [k for k in bm if k[0] == r and k[1] == "GROF"]:          # l. 202-207
                if w not in ("IHEI", "YHEI"):
                    put((r, "GROF", w, y), f(r, "PROD", w, y) * b2.get((r, "GROF", w), 0.0))
    for k in list(L):                                                                   # l. 212-221
        r, c, w, y = k
        if w == "LEVL" and c != "INHA" and data_b2000(r, c, "LEVL") and \
                DATA_MIN_SHARE * b2.get((r, c, "LEVL"), 0.0) > data_b2000(r, c, "LEVL"):
            put(k, 0.0)
        if c == "GROF" and data_b2000(r, "PROD", w) and DATA_MIN_SHARE * b2.get((r, "GROF", w), 0.0) > \
                data_b2000(r, "PROD", w):
            put(k, 0.0)
    for r in ms:                                                                        # l. 228-236
        for (c, w) in pty:
            if w not in ofrom or bm.get((r, c, "HERD")):
                continue
            for y in LONG_YEARS:
                if f(r, "PROD", w, y) and f(r, c, "LEVL", y) and L.get((r, "GROF", w, y)):
                    put((r, c, w, y), f(r, "PROD", w, y) / f(r, c, "LEVL", y) * b2.get((r, c, w), 0.0))
    for r in ms:                                                                        # l. 277-305
        keys = [k for k in bm if k[0] == r]
        for y in LONG_YEARS:
            for (rr, c, w) in keys:
                if c == "MAPR":
                    put((r, "MAPR", w, y), f(r, "PROD", w, y) * b2.get((r, "MAPR", w), 0.0))
                elif c == "UVAG":
                    put((r, "UVAG", w, y), f(r, "UVAP", w, y) * b2.get((r, "UVAG", w), 0.0)
                        * X.infl ** (y - X.base_year))
                elif c == "DOMM":
                    put((r, "DOMM", w, y), f(r, "DOMM", w, y) * b2.get((r, "DOMM", w), 0.0))
            if bm.get((r, "UVAG", "COMI")):
                put((r, "UVAG", "COMI", y), f(r, "UVAP", "MILK", y) * b2.get((r, "UVAG", "COMI"), 0.0)
                    * X.infl ** (y - X.base_year))
            for w in ("MILK", "COMI"):
                put((r, "PRCM", w, y), f(r, "PROD", w, y) * b2.get((r, "PRCM", w), 0.0))
            for w in {k[2] for k in info if k[0] == r and k[1] == "HCOM" and k[3] == "share" and k[4] == "B2000"}:
                put((r, "HCOM", w, y), f(r, "HCOM", w, y, "share") / f(r, "HCOM", w, "B2000", "share")
                    * f(r, "DOMM", w, y) * b2.get((r, "HCOM", w), 0.0))
    # ---- l. 311-354: interpolation, clean-up, scaling to BAST
    with_gc = [y for y in LONG_YEARS if any(L.get((r, "GROF", "COMI", y)) for r in ms)]
    if with_gc:
        last = max(with_gc)
        fill_base = {y for y in exante if y > X.lst_expost} | {X.base_year, X.bast_year}
        series = {k[:3] for k in L}
        for i, ly in enumerate(LONG_YEARS):
            if ly > last or i + 1 >= len(LONG_YEARS):
                break
            nx = LONG_YEARS[i + 1]
            fill = [y for y in fill_base if ly < y < nx]
            for s3 in series:
                for y in fill:
                    put((*s3, y), L.get((*s3, ly), 0.0) + (y - ly) * (L.get((*s3, nx), 0.0) - L.get((*s3, ly), 0.0))
                        / (nx - ly))
    cur, expt = set(X.years_cur), set(X.expostt)
    for k in list(L):
        r, c, w, y = k
        if y not in cur:
            put(k, 0.0)
        elif y in expt and not (y in (2000, X.bast_year, X.base_year) or (c == "INHA" and w == "LEVL")):
            put(k, 0.0)
    for s3 in {k[:3] for k in L}:
        bt = X.bast.get(s3, 0.0)
        ref = bt if bt else bm.get(s3, 0.0)
        v = L.get((*s3, X.bast_year), 0.0) if bt else L.get((*s3, X.base_year), 0.0)
        if v > FAC_MIN * abs(ref):
            fac = ref / v
            for k in [k for k in L if k[:3] == s3]:
                L[k] *= fac
    out.longrun = dict(L)
    # ---- l. 427-431: HCOM.SUGA per head
    for r in ms:
        b, ib = bm.get((r, "HCOM", "SUGA"), 0.0), bm.get((r, "INHA", "LEVL"), 0.0)
        for y in X.exantet:
            s = X.support.get((r, "HCOM", "SUGA", y), 0.0)
            if s:
                ih = X.inha.get((r, y), 0.0)
                v = max(SUGA_LO, min(SUGA_UP, s / ih / (b / ib))) * (b / ib) * ih
                S.put(S.ab, (r, "HCOM", "SUGA", y), v)
    # ---- l. 446-458: the national PercentChange as a preliminary Expert where Longrun is given
    E: Dict[K4, float] = {}
    if X.lst_exante > X.lst_dgagri:
        for k, p in S.pc.items():
            r, c, w, y = k
            if r in set(ms) and y in set(exante) and L.get((r, c, w, WGT_YEAR)) and y >= X.phase_in:
                v = (1 + p / 100) * bm.get((r, c, w), 0.0)
                if v:
                    E[k] = v
    for k in list(E):
        r, c, w, y = k
        if y == X.lst_dgagri:
            for y2 in exante:
                if y2 > X.lst_dgagri and not E.get((r, c, w, y2)):
                    E[(r, c, w, y2)] = E[k]
    # ---- l. 466-494: Longrun1
    mpc = set(X.mlk_pro) | {"COMI"}
    span = WGT_YEAR - X.phase_in
    L1: Dict[K4, float] = {}
    for k, lv in L.items():
        r, c, w, y = k
        if y in set(exante) and y > X.phase_in and r in set(ms) and not (w in mpc and r == "IR000000"):
            wt = ((min(WGT_YEAR, y) - X.phase_in) / span) ** LONG_EXP * (LONG_WGT - IR_LESS * (r == "IR000000"))
            base = E.get(k) or X.support.get(k, 0.0)
            v = lv * wt + base * (1 - wt)
            if v:
                L1[k] = v
    out.longrun1 = L1
    # ---- l. 497-511
    for k in list(E):
        if L1.get(k) and bm.get(k[:3]):
            S.put(S.pc, k, L1[k] / bm[k[:3]] * 100. - 100.)
    # ---- l. 516-545: Longrun1 as Absolute where nothing else is given
    wba = {b for a, b in X.map_rr if a == "WBA"}
    agg_of: Dict[str, List[str]] = {}
    for a, b in X.map_rr:
        if a in set(X.cur_europ_agg):
            agg_of.setdefault(b, []).append(a)
    L_ = X.lst_dgagri
    for k, v in L1.items():
        r, c, w, y = k
        if c not in cols or w not in rows or y not in set(exante):
            continue
        own = X.dgagri1.get((r, c, w, L_), 0.0)
        dg = own or sum(X.dgagri1.get((a, c, w, L_), 0.0) for a in agg_of.get(r, []))
        if (S.ab.get(k) or S.pc.get(k) or dg or r in wba or r == "TUR" or X.lst_exante <= L_ or y <= X.phase_in):
            continue
        S.put(S.ab, k, v)
        low = (c, w) in pty or w in mpc or (w == "LEVL" and v < TINY_LEVL)
        S.put(S.tr, k, (TRUST_LOW if low else TRUST_MID) + TRUST_FORE * (c == "FORE") + TRUST_OLND * (c == "OLND"))
    return out

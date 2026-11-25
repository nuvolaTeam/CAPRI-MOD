"""CAPRI's conversion of GLOBIOM-EU's projections into long-run change factors for CAPRI's regions and codes:
p_globiomInfo by region, column, row, information (data, factorB2000, share), scenario and year.

  global/convert_globiom.gms (--GlobiomVersion=Globiom_EU; the branch selected for the GLOBIOM-EU files of 2023-2025,
  tools/build/build_captrd_globiom_sets.py)
    l. 1200-1249  the mapping of CAPRI's regions to GLOBIOM's countries (through FAO's codes, globiom_to_fao_reg.gms)
                  and regions (REGION58_COUNTRY_MAP) (region_map); CAPRI's FAORegions_map as global/fao_codes_new.gms
                  leaves it outside CAPMOD (with the trade aggregates, l. 559)
    l. 1305-1618  GLOBIOM's data of the scenario on one parameter p_GLOBIOM (collect): population and GDP; trade,
                  prices, processing (without the oils going to FAME), demand, supply, feed of GLOBIOM's regions;
                  herds, crop areas and land use of its countries summed to its regions; ALMILK, the processing
                  products as production, DDGS from the ethanol processes
    l. 1700-1760  the years kept, the mapping to CAPRI's columns and rows (prices weighted by production) (mapped)
    l. 1872-2006  B2000 = 2000; sugar from cane and beet (SUGA); DOMM; the young heifers; 'data'; the world price;
                  factorB2000 = year / B2000; the macro factors of the market regions from their parts; NECR; the
                  demand and trade shares (factors)
    l. 2017-2145  the change factors from B2000 to the base year 2017 from CAPREG's time series (member states) and
                  the global database (p_dataMarket, the other regions), population from p_worldPop; the land use
                  shares; GDP's factor in real terms (base_factors)
  global/create_longrun_info.gms l. 91-102: the CAPREG time series' UVAP of the base years filled from 2002 with
  UVAD + PRII's growth; PROD = GROF (MAPR for the secondary products) where missing, p_dataMarket's PROD = MAPR
  (prepare_capreg, prepare_datamarket)

CAPRI's GAMS statements with arithmetic are quoted by the functions that compute them, in
capri_mod/pipeline/captrd/equations/convert_globiom.py and create_longrun_info.py; the functions here keep the loops,
the records' grouping, the filters and the set statements (the region mapping, the years kept), and call them.

GAMS's semantics kept: execute_load drops the records outside a parameter's declared domain (the scenario's macroScen,
bioEnScen, IEAscen; longYr; CROPTECH); labels compare without case (all upper case here); an assignment's right side
reads the values from before the statement; a zero deletes.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import pandas as pd

from capri_mod.pipeline.captrd.equations import convert_globiom as GE
from capri_mod.pipeline.captrd.equations import create_longrun_info as CL

#: the calendar year of B2000 (CAPRI's calyea: the average of 1999-2001) and GLOBIOM's projection years
B2000_YEAR = 2000
#: l. 1702-1708: the years after it are kept only where GLOBIOM projects milk production that far
HORIZON_CHECK = 2050

U = str.upper


def _one(path: Path) -> List[str]:
    with open(path, newline="") as fh:
        return [U(r["d0"]) for r in csv.DictReader(fh)]


def _tuples(path: Path) -> List[Tuple[str, ...]]:
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        n = sum(1 for h in hdr if h.startswith("d"))
        return [tuple(U(x) for x in row[:n]) for row in r]


@dataclass
class Sets:
    """convert_globiom.gms's own sets and CAPRI's it uses (sets/globiom, tools/build/build_captrd_globiom_sets.py)."""
    longyr: List[str]
    longyrsel: List[str]
    longyrselwo00: List[str]
    procpr: Set[str]
    globiomrows: Set[str]
    vegoil: Set[str]
    globiom_to_rows: List[Tuple[str, str]]
    globiomcols: Set[str]
    globiommacro: Set[str]
    macro: List[str]
    globiom_to_cols: List[Tuple[str, str]]
    demposdis: List[str]
    tradepos: List[str]
    mrkpos: List[str]
    faoregmap: List[Tuple[str, str, str]]
    rmall: List[str]
    rw: Set[str]
    rm: Set[str]
    rms: Set[str]
    rw_to_rm: List[Tuple[str, str]]
    rms_to_rm: List[Tuple[str, str]]
    nuts0: List[str]
    msall: Set[str]
    euallagg: Set[str]
    faoregions: Set[str]
    faoregions_map: List[Tuple[str, str]]
    secom: Set[str]
    landusearto: Set[str]


def read_sets(globiom_dir: Path, capri_dir: Path) -> Sets:
    g = lambda n: _one(globiom_dir / f"{n}.csv")         # noqa: E731
    t = lambda n: _tuples(globiom_dir / f"{n}.csv")      # noqa: E731
    c = lambda n: _one(capri_dir / f"{n.lower()}.csv")           # noqa: E731
    ct = lambda n: _tuples(capri_dir / f"{n.lower()}.csv")       # noqa: E731
    return Sets(
        longyr=g("longyr"), longyrsel=g("longyrsel"), longyrselwo00=g("longyrselwo00"), procpr=set(g("procpr")),
        globiomrows=set(g("globiomrows")), vegoil=set(g("vegoil")), globiom_to_rows=t("globiom_to_rows"),
        globiomcols=set(g("globiomcols")), globiommacro=set(g("globiommacro")), macro=g("macro"),
        globiom_to_cols=t("globiom_to_cols"), demposdis=g("demposdis"), tradepos=g("tradepos"), mrkpos=g("mrkpos"),
        faoregmap=t("longtext_globiom_faoregmap"), rmall=c("RMall"), rw=set(c("RW")), rm=set(c("RM")),
        rms=set(c("RMS")), rw_to_rm=ct("RW_TO_RM"), rms_to_rm=ct("RMS_TO_RM"), nuts0=c("NUTS0"),
        msall=set(c("MSALL")), euallagg=set(c("EUAllAgg")), faoregions=set(c("FAORegions")),
        faoregions_map=ct("FAORegions_map"), secom=set(c("SECOM")), landusearto=set(c("LandUseARTO")))


#: convert_globiom.gms l. 1213-1218: FAO codes added to CAPRI's FAORegions_map
FAO_ADDED = [("BL000000", "255"), ("BL000000", "256"), ("CS000000", "186"), ("MO000000", "186"),
             ("KO000000", "186"), ("WBA", "186")]
#: l. 655-658: the processes making FAME from vegetable oils
TO_FAME = {"SOYOTOFAME", "RAPOTOFAME", "SUNOTOFAME", "PLMOTOFAME"}
#: l. 1908: the young heifers, following HEIR's LEVL
YOUNG_HEIF = ["IHEI", "YHEI"]
#: l. 1900-1903: the rows whose DOMM is their production
DOMM_IS_PROD = {"COMI", "SGMI", "SUGB"}


@dataclass
class Globiom:
    """The GLOBIOM file's symbols convert_globiom.gms reads (labels in upper case, values per record)."""
    region58: List[str]
    allcountry: List[str]
    region58_country_map: List[Tuple[str, str]]
    animal: Set[str]
    eu_crop: Set[str]
    alllc_type: Set[str]
    aezclass: Set[str]
    scenyear: List[str]
    tables: Dict[str, pd.DataFrame]


CROPTECH = {"HI", "LI", "SS", "IR_BASIN", "IR_FURROW", "IR_DRIP", "IR_SPRINK", "FERTRITILLCONV", "FERTRITILLREDU",
            "FERTRITILLMINI"}                            # l. 461-463 (loadCroptech off)
#: the parameters read (l. 1305-1324)
TABLES = ["MACROSCEN_DATA", "Trade_Compare", "Price_Compare2", "Process_Compare2", "DemQuantity_Compare",
          "SupQuantity_Compare", "FeedQuantity_Compare", "ProcessData", "LIVE_COMPARE", "ACR_COMPARE", "Land_Compare2",
          "Perennial_COMPARE"]


def read_globiom(parquet_dir: Path) -> Globiom:
    """The GLOBIOM file converted to Parquet (tools/build/convert_capri_gdx.py)."""
    def sym(n):
        d = pd.read_parquet(parquet_dir / f"{n}.parquet")
        for c in d.columns:
            if c.startswith("d"):
                d[c] = d[c].astype(str).str.upper()
        return d
    one = lambda n: sym(n).d1.tolist()                    # noqa: E731
    m = sym("REGION58_COUNTRY_MAP")
    tabs = {n: sym(n) for n in TABLES}
    eu_crop = set(one("EU_CROP")) | {"LIGHERBA"}           # l. 575-591
    return Globiom(region58=one("REGION58"), allcountry=one("ALLCOUNTRY"),
                   region58_country_map=list(zip(m.d1, m.d2)), animal=set(one("ANIMAL")), eu_crop=eu_crop,
                   alllc_type=set(one("allLC_TYPE")), aezclass=set(one("AEZCLASS")) | {"AEZ_ANY"},
                   scenyear=one("ScenYear"), tables=tabs)


def region_map(S: Sets, G: Globiom) -> Set[Tuple[str, str]]:
    """l. 1220-1243: rmAll_to_GLOBIOM(RMALL, GLOBIOMregion)."""
    fmap = set(S.faoregions_map)
    # global/fao_codes_new.gms l. 559 (not in the run's FAORegions_map: CAPMOD's fao_codes_new.gms exits at l. 554):
    # the trade aggregates mapped to the FAO codes of their market regions' parts
    parts = defaultdict(set)
    for rms, rm in S.rms_to_rm:
        parts[rm].add(rms)
    by_reg = defaultdict(set)
    for r, f in fmap:
        by_reg[r].add(f)
    for rw, rm in S.rw_to_rm:
        if rw in S.rw:
            for rms in parts.get(rm, ()):
                fmap |= {(rw, f) for f in by_reg.get(rms, ())}
    fmap |= set(FAO_ADDED)                                                         # l. 1213-1218
    # the lines cited below are convert_globiom.gms's
    by_fao = defaultdict(set)
    for r, f in fmap:
        by_fao[f].add(r)
    countries = set(G.allcountry)
    out = set()
    rmall = set(S.rmall)
    for _, c, f in S.faoregmap:                                                   # l. 1224-1227
        if c in countries and f in S.faoregions:
            for r in by_fao.get(f, ()):
                if r in rmall:
                    out.add((r, c))
    for ragg, c in G.region58_country_map:                                         # l. 1228-1229
        for r in sorted(r for r, cc in out if cc == c):
            out.add((r, ragg))
    out.discard(("RSA", "USAREG"))                                                 # l. 1236
    return {(r, g) for r, g in out if not (r in S.rw and r not in S.euallagg and r != "EU")}   # l. 1239-1243


def _sums(records):
    """The records' (key, value) summed per key (GE.p_GLOBIOM_compare_sum), the keys in the order of their first
    record."""
    acc = defaultdict(list)
    for k, v in records:
        acc[k].append(v)
    return {k: GE.p_GLOBIOM_compare_sum(vs) for k, vs in acc.items()}


def _scen_filter(d: pd.DataFrame, cols: Sequence[str], scen: Tuple[str, str, str]) -> pd.DataFrame:
    m, b, i = cols
    return d[(d[m] == scen[0]) & (d[b] == scen[1]) & (d[i] == scen[2])]


def collect(G: Globiom, S: Sets, scen: Tuple[str, str, str], longyr: Sequence[str]) -> Dict[Tuple[str, str, str, str], float]:
    """l. 1358-1618: p_GLOBIOM(GLOBIOMregion, item, item, year) of the scenario (macroScen, bioEnScen, IEAscen)."""
    years = set(G.scenyear) & set(longyr)
    T = G.tables
    ragg, country = set(G.region58), set(G.allcountry)
    sup = _scen_filter(T["SupQuantity_Compare"], ["d4", "d5", "d6"], scen)
    if not len(sup[(sup.d3 == "LEVEL") & sup.d2.isin(ragg) & sup.d7.isin(years)]):          # l. 1358-1359
        raise ValueError(f"no supply in GLOBIOM's regions for the scenario {scen}")
    P: Dict[Tuple[str, str, str, str], float] = {}

    def put(k, v):
        if v:
            P[k] = v
        else:
            P.pop(k, None)
    mac = T["MACROSCEN_DATA"]
    mac = mac[(mac.d1 == scen[0]) & mac.d4.isin(set(longyr))]
    md = {(r, it, y): v for r, it, y, v in zip(mac.d2, mac.d3, mac.d4, mac.value)}
    pm: Dict[Tuple[str, str, str], float] = {}                                    # p_MACRO(region, item, year)
    for (r, it, y), v in md.items():                                              # l. 1364-1365
        if it in ("POP", "GDP") and v:
            pm[(r, it, y)] = GE.p_MACRO(v)
    for r in ragg:                                                                 # l. 1377-1381
        for y in longyr:
            if pm.get((r, "POP", y)):
                pm[(r, "POP", y)] = GE.p_MACRO_POP_1000(pm[(r, "POP", y)])
            if not pm.get((r, "GDP", y)):
                v = GE.p_MACRO_GDP_RelChng(md.get((r, "GDPPCAP_RELCHNG", y), 0.0), md.get((r, "POP_RELCHNG", y), 0.0))
                if v:
                    pm[(r, "GDP", y)] = v
            if not pm.get((r, "POP", y)):
                v = GE.p_MACRO(md.get((r, "POP_RELCHNG", y), 0.0))
                if v:
                    pm[(r, "POP", y)] = v

    def level(d, item, reg, y, dims):
        d = _scen_filter(d, dims, scen)
        d = d[(d[reg].isin(ragg)) & (d[y].isin(years))]
        return d
    tr = level(T["Trade_Compare"], "d1", "d2", "d8", ["d5", "d6", "d7"])
    tr = tr[tr.d3.isin(ragg) & (tr.d4 == "LEVEL")]
    trade = _sums(((b, a, it, y), v) for it, a, b, y, v in zip(tr.d1, tr.d2, tr.d3, tr.d8, tr.value))
    #                                                                              l. 1385-1387: TRADE(item, r2, r1)
    pr = level(T["Price_Compare2"], "d1", "d2", "d6", ["d3", "d4", "d5"])
    price = _sums(((r, it, y), v) for it, r, y, v in zip(pr.d1, pr.d2, pr.d6, pr.value))     # l. 1390-1392
    pc = level(T["Process_Compare2"], "d3", "d1", "d7", ["d4", "d5", "d6"])
    proc = _sums(((r, it, y), v) for r, p, it, y, v in zip(pc.d1, pc.d2, pc.d3, pc.d7, pc.value)   # l. 1394-1400
                 if not (p in TO_FAME and it in S.vegoil))
    q = {}
    for n in ("DemQuantity_Compare", "SupQuantity_Compare", "FeedQuantity_Compare"):   # l. 1402-1412
        d = level(T[n], "d1", "d2", "d7", ["d4", "d5", "d6"])
        d = d[d.d3 == "LEVEL"]
        q[n] = _sums(((r, it, y), v) for it, r, y, v in zip(d.d1, d.d2, d.d7, d.value))
    lv = _scen_filter(T["LIVE_COMPARE"], ["d9", "d10", "d11"], scen)
    lv = lv[lv.d1.isin(country) & lv.d8.isin(G.animal) & lv.d12.isin(years) & (lv.d3 == "ALTI_ANY")
            & (lv.d4 == "SLP_ANY") & (lv.d5 == "SOIL_ANY") & lv.d6.isin(G.aezclass)]
    any_ = defaultdict(list)
    notany = defaultdict(list)
    for c, cr, aez, a, y, v in zip(lv.d1, lv.d2, lv.d6, lv.d8, lv.d12, lv.value):   # l. 1451-1458
        if aez == "AEZ_ANY":
            if cr == "ANYCOLROW":
                any_[(c, a, y)].append(v)
        else:
            notany[(c, a, y)].append(v)
    live = {}
    for k in sorted(set(any_) | set(notany)):
        v = GE.p_LIVESTOCK(any_.get(k, []), notany.get(k, []))
        if v:
            live[k] = v
    ac = _scen_filter(T["ACR_COMPARE"], ["d9", "d10", "d11"], scen)
    ac = ac[ac.d1.isin(country) & ac.d7.isin(G.eu_crop) & ac.d8.isin(CROPTECH) & ac.d12.isin(years)
            & (ac.d3 == "ALTI_ANY") & (ac.d4 == "SLP_ANY") & (ac.d5 == "SOIL_ANY") & ac.d6.isin(G.aezclass)]
    crop = _sums(((c, cp, y), v) for c, cp, y, v in zip(ac.d1, ac.d7, ac.d12, ac.value))   # l. 1460-1462
    ln = _scen_filter(T["Land_Compare2"], ["d8", "d9", "d10"], scen)
    ln = ln[ln.d1.isin(country) & ln.d7.isin(G.alllc_type) & ln.d11.isin(years) & (ln.d3 == "ALTI_ANY")
            & (ln.d4 == "SLP_ANY") & (ln.d5 == "SOIL_ANY") & ln.d6.isin(G.aezclass)]
    land = _sums(((c, lc, y), v) for c, lc, y, v in zip(ln.d1, ln.d7, ln.d11, ln.value))   # l. 1464-1466
    pe = _scen_filter(T["Perennial_COMPARE"], ["d7", "d8", "d9"], scen)
    pe = pe[pe.d10.isin(years) & (pe.d3 == "ALTI_ANY") & (pe.d4 == "SLP_ANY") & (pe.d5 == "SOIL_ANY")
            & pe.d6.isin(G.aezclass)]
    peren = defaultdict(list)
    for c, y, v in zip(pe.d1, pe.d10, pe.value):                                  # l. 1469-1471 (any region)
        peren[(c, "LIGHERBA", y)].append(v)
    for k, vs in peren.items():
        crop[k] = GE.p_CROP_AREA_ligherba(crop.get(k, 0.0), vs)
    members = defaultdict(list)
    for ra, c in G.region58_country_map:
        members[ra].append(c)

    def up(d):                                                                     # l. 1474-1479
        out = dict(d)
        for k in [k for k in out if k[0] in ragg]:
            out.pop(k)
        acc = defaultdict(list)
        for ra, cs in members.items():
            cs = set(cs)
            for (c, it, y), v in d.items():
                if c in cs:
                    acc[(ra, it, y)].append(v)
        out.update({k: v for k, v in ((k, GE.p_GLOBIOM_ragg(vs)) for k, vs in acc.items()) if v})
        return out
    live, crop, land = up(live), up(crop), up(land)
    gcols, grows = S.globiomcols, S.globiomrows
    for (r, lc, y), v in land.items():                                             # l. 1586
        if r in ragg and lc in gcols:
            put((r, lc, "LEVEL", y), GE.p_GLOBIOM(v))
    for (r, it, y), v in pm.items():                                               # l. 1588-1589
        if it in S.globiommacro:
            put((r, it, "LEVEL", y), GE.p_GLOBIOM(v))
    for (r, a, y), v in live.items():                                              # l. 1590
        if r in ragg and a in gcols:
            put((r, a, "LEVEL", y), GE.p_GLOBIOM(v))
    for (r, cp, y), v in crop.items():                                             # l. 1591
        if r in ragg and cp in gcols:
            put((r, cp, "LEVEL", y), GE.p_GLOBIOM(v))
    for (r, it, y), v in price.items():                                            # l. 1592
        if it in grows:
            put((r, "PRICE", it, y), GE.p_GLOBIOM(v))
    for (r, it, y), v in q["SupQuantity_Compare"].items():                         # l. 1593
        if it in grows:
            put((r, "PRODQ", it, y), GE.p_GLOBIOM(v))
    for (r, it, y), v in q["DemQuantity_Compare"].items():                         # l. 1594
        if it in grows:
            put((r, "DN", it, y), GE.p_GLOBIOM(v))
    ex, im = defaultdict(list), defaultdict(list)
    for (a, b, it, y), v in trade.items():                                         # l. 1595-1596
        if it in grows:
            ex[(b, it, y)].append(v)
            im[(a, it, y)].append(v)
    for (r, it, y), vs in ex.items():
        put((r, "EXPTA", it, y), GE.p_GLOBIOM_trade(vs))
    for (r, it, y), vs in im.items():
        put((r, "IMPTA", it, y), GE.p_GLOBIOM_trade(vs))
    for (r, it, y), v in proc.items():                                             # l. 1597
        if it in grows:
            put((r, "BIOM", it, y), GE.p_GLOBIOM(v))
    for (r, it, y), v in q["FeedQuantity_Compare"].items():                        # l. 1598
        if it in grows:
            put((r, "FTN", it, y), GE.p_GLOBIOM(v))
    for r in ragg:
        for y in sorted(years):                                                    # l. 1599-1606
            put((r, "PRODQ", "ALMILK", y), GE.p_GLOBIOM_ALMILK(P.get((r, "PRODQ", "BVMILK", y), 0.0),
                                                               P.get((r, "PRODQ", "SGMILK", y), 0.0)))
            for it in sorted(S.procpr):
                if it in grows:
                    put((r, "PRODQ", it, y), GE.p_GLOBIOM(P.get((r, "BIOM", it, y), 0.0)))
                put((r, "BIOM", it, y), GE.p_GLOBIOM_BIOM_PROCPR())
    pdat = T["ProcessData"]
    pdd = {(r, p, it): v for r, p, it, v in zip(pdat.d1, pdat.d2, pdat.d3, pdat.value)}
    for r in ragg:
        for y in sorted(years):
            put((r, "PRODQ", "CORN_DG", y), GE.p_GLOBIOM_DG(P.get((r, "BIOM", "CORN", y), 0.0),
                                                            pdd.get((r, "CORNTOETHOL", "CORN_DG"), 0.0)))
            put((r, "PRODQ", "WHEA_DG", y), GE.p_GLOBIOM_DG(P.get((r, "BIOM", "WHEA", y), 0.0),
                                                            pdd.get((r, "WHEATOETHOL", "WHEA_DG"), 0.0)))
    return P


def _calyea(y: str) -> int:
    return B2000_YEAR if y == "B2000" else int(y)


def mapped(P: Dict[Tuple[str, str, str, str], float], S: Sets, rmap: Set[Tuple[str, str]], ragg: Iterable[str]):
    """l. 1700-1760: (p_GLOBIOMmapped(RMALL, col, row, year), the years longYrSel, longYrSelWo00)."""
    ragg = set(ragg)
    sel, wo = list(S.longyrsel), list(S.longyrselwo00)
    milk_years = {y for (r, c, w, y), v in P.items() if r in ragg and c == "PRODQ" and w == "ALMILK" and v}
    trim = lambda ys: [y for y in ys if not (_calyea(y) > HORIZON_CHECK and not any(_calyea(z) >= _calyea(y) for z in milk_years))]  # noqa: E731,E501
    sel, wo = trim(sel), trim(wo)                                                  # l. 1702-1709
    gcm = {g for g, c in S.globiom_to_cols}
    grm = {g for g, w in S.globiom_to_rows}
    regs = defaultdict(list)
    for r, g in sorted(rmap):
        if g in ragg:
            regs[r].append(g)
    selset = set(sel)
    byk = defaultdict(float)
    for (g, c, w, y), v in P.items():
        if g in ragg and c in gcm and w in grm and y in selset:
            byk[(g, c, w, y)] = v
    MC: Dict[Tuple[str, str, str, str], float] = {}
    rmall = [r for r in S.rmall if regs.get(r)]
    by_g = defaultdict(list)
    for (g, c, w, y), v in byk.items():
        by_g[g].append((c, w, y, v))
    g2c = defaultdict(list)
    for g, c in S.globiom_to_cols:
        g2c[g].append(c)
    for r in rmall:                                                                # l. 1741-1760
        gs = regs[r]
        acc = defaultdict(list)
        for ga in gs:
            for c2, w2, y2, v in by_g.get(ga, ()):
                for col in g2c[c2]:
                    if col != "UVAP":                                              # l. 1744
                        acc[(col, w2, y2)].append(v)
        for k, vs in acc.items():
            v = GE.p_GLOBIOMmappedCols(vs)
            if v:
                MC[(r, *k)] = v
        pq = defaultdict(list)                                                     # l. 1748-1755
        for ga in gs:
            for w in sorted(grm):
                for y in sel:
                    q = P.get((ga, "PRODQ", w, y), 0.0)
                    if q:
                        pq[(w, y)].append((P.get((ga, "PRICE", w, y), 0.0), q))
        for (w, y), pairs in pq.items():
            d = 0.0
            for _, q in pairs:
                d += q
            if d:
                v = GE.p_GLOBIOMmappedCols_UVAP(pairs)
                if v:
                    MC[(r, "UVAP", w, y)] = v
                else:
                    MC.pop((r, "UVAP", w, y), None)
    g2w = defaultdict(list)
    for g, w in S.globiom_to_rows:
        g2w[g].append(w)
    Ml: Dict[Tuple[str, str, str, str], List[float]] = defaultdict(list)
    for (r, c, gw, y), v in MC.items():                                            # l. 1757-1759
        for w in g2w[gw]:
            Ml[(r, c, w, y)].append(v)
    M = {k: GE.p_GLOBIOMmappedCols(vs) for k, vs in Ml.items()}
    return {k: v for k, v in M.items() if v}, sel, wo


def factors(M: Dict[Tuple[str, str, str, str], float], S: Sets, scen_name: str, sel: Sequence[str],
            wo: Sequence[str]) -> Tuple[Dict[Tuple[str, str, str, str, str, str], float], Dict]:
    """l. 1872-2006: (p_globiomInfo, p_GLOBIOMmapped as changed)."""
    M = dict(M)

    def put(d, k, v):
        if v:
            d[k] = v
        else:
            d.pop(k, None)
    for k in [k for k in M if k[3] == "2000"]:                                     # l. 1872-1874
        M[(k[0], k[1], k[2], "B2000")] = GE.p_GLOBIOMmapped_B2000(M.pop(k))
    regs = {k[0] for k in M}
    cols_m = {c for g, c in S.globiom_to_cols} | {"DOMM"}
    rows_m = {w for g, w in S.globiom_to_rows}
    for r in sorted(regs):
        for y in sel:
            for c in S.mrkpos:                                                     # l. 1884-1889
                put(M, (r, c, "SUGA", y), GE.p_GLOBIOMmapped_SUGA(M.get((r, c, "SUGA", y), 0.0),
                                                                  M.get((r, c, "SUGB", y), 0.0)))
                if c != "PROD":
                    put(M, (r, c, "SUGB", y), GE.p_GLOBIOMmapped_removed())
            for w in sorted(rows_m):                                               # l. 1894-1903
                put(M, (r, "DOMM", w, y), GE.p_GLOBIOMmapped_DOMM(M.get((r, "HCOM", w, y), 0.0),
                                                                  M.get((r, "BIOF", w, y), 0.0),
                                                                  M.get((r, "FEDM", w, y), 0.0)))
            for w in sorted(DOMM_IS_PROD):
                if w in rows_m:
                    put(M, (r, "DOMM", w, y), GE.p_GLOBIOMmapped_DOMM_PROD(M.get((r, "PROD", w, y), 0.0)))
            for w in YOUNG_HEIF:                                                   # l. 1908-1911
                put(M, (r, "PROD", w, y), GE.p_GLOBIOMmapped_DOMM_PROD(M.get((r, "HEIR", "LEVL", y), 0.0)))
    rows_m |= set(YOUNG_HEIF)
    selset = set(sel)
    I: Dict[Tuple[str, str, str, str, str, str], float] = {}
    for (r, c, w, y), v in M.items():                                              # l. 1913-1914
        if c in cols_m and w in rows_m and y in selset and v:
            I[(r, c, w, "DATA", scen_name, y)] = GE.p_GLOBIOMmapped_B2000(v)
    world = [rm for rw, rm in S.rw_to_rm if rw == "WORLD"]
    for w in sorted(rows_m):                                                       # l. 1919-1927
        for y in sel:
            den = sum(M.get((rm, "PROD", w, y), 0.0) + M.get((rm, "DOMM", w, y), 0.0) for rm in world)
            if den:
                put(M, ("WORLD", "UVAP", w, y), GE.p_GLOBIOMmapped_World_UVAP(
                    [(M.get((rm, "UVAP", w, y), 0.0), M.get((rm, "PROD", w, y), 0.0), M.get((rm, "DOMM", w, y), 0.0))
                     for rm in world]))
    nonempty = {(c, w) for (r, c, w, y), v in M.items() if c in cols_m and w in rows_m and y in selset and v}
    for r in S.rmall:                                                              # l. 1938-1956
        for (c, w) in sorted(nonempty):
            if c == "BIOF":
                continue
            b = M.get((r, c, w, "B2000"), 0.0)
            for y in wo:
                v = M.get((r, c, w, y), 0.0)
                k = (r, c, w, "FACTORB2000", scen_name, y)
                if b > 0:
                    put(I, k, GE.p_globiomInfo_factorB2000(v, b))
                elif v <= 0 and not I.get(k) and (r in S.rm or r in S.rms or r in S.rw):
                    I[k] = GE.p_globiomInfo_factorB2000_one()
    parts = defaultdict(list)
    for rms, rm in S.rms_to_rm:
        parts[rm].append(rms)
    for rm in sorted(S.rm):                                                        # l. 1969-1973
        for c in S.macro:
            for y in wo:
                k = (rm, c, "LEVL", "FACTORB2000", scen_name, y)
                vs = [I.get((p, c, "LEVL", "FACTORB2000", scen_name, y), 0.0) for p in parts.get(rm, [])]
                n = sum(1 for v in vs if v)
                if not I.get(k) and n:
                    put(I, k, GE.p_globiomInfo_factorB2000_RM(vs))
    for k in [k for k in I if k[1] == "NECR" and k[3] == "FACTORB2000"]:          # l. 1976
        put(I, k, GE.p_GLOBIOMmapped_removed())
    for (r, c, w, y), v in list(M.items()):                                        # l. 1989-2006
        if y not in selset:
            continue
        if c == "DOMM" and v:
            for d in S.demposdis:
                put(I, (r, d, w, "SHARE", scen_name, y), GE.p_globiomInfo_share_DemPosDis(M.get((r, d, w, y), 0.0), v))
    for k in [k for k in I if k[1] in set(S.demposdis) and k[3] == "FACTORB2000"]:
        put(I, k, GE.p_GLOBIOMmapped_removed())
    for r in sorted(regs):
        for w in sorted({k[2] for k in M if k[0] == r}):
            for y in sel:
                den = M.get((r, "DOMM", w, y), 0.0) + M.get((r, "PROD", w, y), 0.0)
                if den:
                    for t in S.tradepos:
                        put(I, (r, t, w, "SHARE", scen_name, y), GE.p_globiomInfo_share_TradePos(
                            M.get((r, t, w, y), 0.0), M.get((r, "DOMM", w, y), 0.0), M.get((r, "PROD", w, y), 0.0)))
    for k in [k for k in I if k[1] in set(S.tradepos) and k[3] == "FACTORB2000"]:
        put(I, k, GE.p_GLOBIOMmapped_removed())
    return I, M


def prepare_capreg(capreg: Dict[Tuple[str, str, str, str], float], secom: Set[str], base_years: Sequence[str]) -> None:
    """create_longrun_info.gms l. 91-102, in place on P_capregData(NUTS0, col, row, year)."""
    rows_by = defaultdict(set)
    for (r, c, w, y) in capreg:
        rows_by[r].add(w)
    up = {}
    for r, ws in rows_by.items():                                                  # l. 91-95
        for w in ws:
            d02 = capreg.get((r, "UVAD", w, "2002"), 0.0) + capreg.get((r, "PRII", w, "2002"), 0.0)
            if not d02:
                continue
            for y in base_years:
                if not capreg.get((r, "UVAP", w, y)):
                    v = CL.P_capregData_UVAP(capreg.get((r, "UVAP", w, "2002"), 0.0),
                                             capreg.get((r, "UVAD", w, y), 0.0), capreg.get((r, "PRII", w, y), 0.0),
                                             d02)
                    if v:
                        up[(r, "UVAP", w, y)] = v
    capreg.update(up)
    up = {}
    for (r, c, w, y), v in capreg.items():                                        # l. 100-102
        if (c == "GROF" and w not in secom) or (c == "MAPR" and w in secom):
            if not capreg.get((r, "PROD", w, y)) and v:
                up[(r, "PROD", w, y)] = CL.P_capregData_PROD(v)
    capreg.update(up)


def prepare_datamarket(dm: Dict[Tuple[str, str, str, str], float]) -> None:
    """create_longrun_info.gms l. 98: p_dataMarket's PROD = MAPR where missing, in place."""
    up = {(r, "PROD", w, y): CL.p_dataMarket_PROD(v) for (r, c, w, y), v in dm.items()
          if c == "MAPR" and v and not dm.get((r, "PROD", w, y))}
    dm.update(up)


def base_factors(I: Dict, S: Sets, scen_name: str, wo: Sequence[str], capreg: Dict, datamarket: Dict,
                 worldpop: Dict[Tuple[str, str], float], base_year: str = "2017",
                 base_years: Sequence[str] = ("2016", "2017", "2018")) -> Dict:
    """l. 2017-2145, in place on I (p_globiomInfo): the factor of the base year relative to B2000."""
    fac = {k: v for k, v in I.items() if k[3] == "FACTORB2000" and k[5] in set(wo) and v}
    proj_cols = {k[1] for k in fac} - {"UVAP"}                                      # l. 2025-2031
    proj_rows = {k[2] for k in fac} - {"YILD", "HSTY"}
    proj_cr = {(k[1], k[2]) for k in fac}
    nuts0 = set(S.nuts0)
    B: Dict[Tuple[str, str, str, str], float] = {}
    for bas in ("B2000", base_year):                                               # l. 2042-2104
        cur = ["1999", "2000", "2001"] if bas == "B2000" else list(base_years)
        for r in sorted(nuts0):
            for (c, w) in sorted(proj_cr):
                if c in proj_cols and w in proj_rows:                              # l. 2053-2055
                    v = GE.p_baseDat_mean([capreg.get((r, c, w, y), 0.0) for y in cur])
                    if v:
                        B[(r, c, w, bas)] = v
            for c in sorted(proj_cols):                                            # l. 2058-2061
                lv = sum(capreg.get((r, c, "LEVL", y), 0.0) for y in cur)
                if lv:
                    v = GE.p_baseDat_YILD([capreg.get((r, c, "YILD", y), 0.0) for y in cur],
                                          [capreg.get((r, c, "LEVL", y), 0.0) for y in cur])
                    if v:
                        B[(r, c, "YILD", bas)] = v
            for w in sorted(proj_rows):                                            # l. 2064-2067
                v = GE.p_baseDat_UVAP([capreg.get((r, "UVAP", w, y), 0.0) for y in cur],
                                      [capreg.get((r, "GROF", w, y), 0.0) for y in cur])
                if v:
                    B[(r, "UVAP", w, bas)] = v
        if bas == "B2000":                                                         # l. 2075-2080
            for (r, c, w, y), v in list(datamarket.items()):
                if y == "2000" and v and (r not in nuts0 or c == "GDP") and (c, w) in proj_cr and c in proj_cols \
                        and w in proj_rows and not datamarket.get((r, c, w, "1999")):
                    datamarket[(r, c, w, "1999")] = GE.p_dataMarket_1999(v)
        gdp_gap = [r for r in S.rmall if 0 < sum(1 for y in cur if datamarket.get((r, "GDP", "LEVL", y))) < 3
                   and ("GDP", "LEVL") in proj_cr]
        if gdp_gap:                                                                # l. 2083-2093
            raise ValueError(f"convert_globiom.gms l. 2093: dataMarketGap for GDP in {gdp_gap}")
        rmall = set(S.rmall)
        ok = lambda r, c, w: ((r not in nuts0 or c == "GDP") and c in proj_cols and w in proj_rows    # noqa: E731
                              and (c, w) in proj_cr and r in rmall)
        acc = defaultdict(list)
        for (r, c, w, y), v in datamarket.items():                                 # l. 2096-2098
            if y in cur and ok(r, c, w):
                acc[(r, c, w, bas)].append(v)
        for k in [k for k in B if k[3] == bas and ok(k[0], k[1], k[2]) and k not in acc]:
            B.pop(k)
        for k, vs in acc.items():
            v = GE.p_baseDat_dataMarket(vs)
            if v:
                B[k] = v
            else:
                B.pop(k, None)
        for r in S.rmall:                                                          # l. 2102
            v = GE.p_baseDat_mean([worldpop.get((y, r), 0.0) for y in cur])
            if v:
                B[(r, "INHA", "LEVL", bas)] = v
            else:
                B.pop((r, "INHA", "LEVL", bas), None)
    proj_cols |= {"UVAP"}                                                          # l. 2111-2112
    proj_rows |= {"YILD"}
    for c in sorted(S.landusearto):                                                # l. 2125-2126
        for r in S.msall:
            d = I.get((r, c, "LEVL", "DATA", scen_name, "B2000"), 0.0)
            v = GE.p_globiomInfo_share_landuse(d, B.get((r, c, "LEVL", "B2000"), 0.0))
            k = (r, c, "LEVL", "SHARE", scen_name, "B2000")
            if v:
                I[k] = v
            else:
                I.pop(k, None)
    has = {(k[0], k[1], k[2]) for k in fac}
    for (r, c, w) in sorted(has):                                                  # l. 2131-2140
        if c in proj_cols and w in proj_rows:
            b0, b1 = B.get((r, c, w, "B2000"), 0.0), B.get((r, c, w, base_year), 0.0)
            I[(r, c, w, "FACTORB2000", scen_name, base_year)] = GE.p_globiomInfo_factorB2000_BAS(b1, b0)
    for k in [k for k in I if k[1] == "GDP" and k[2] == "LEVL" and k[3] == "FACTORB2000" and k[5] == base_year]:
        I[k] = GE.p_globiomInfo_GDP_real(I[k], int(base_year) - B2000_YEAR)                # l. 2144-2145
    return B


def read_scenarios(dat_dir: Path) -> Dict[str, Tuple[str, Tuple[str, str, str]]]:
    """globiom_scenarios.csv: {SCENARIO (upper case): (GLOBIOM file, (macroScen, bioEnScen, IEAscen))}."""
    with open(Path(dat_dir) / "globiom_scenarios.csv", newline="") as fh:
        return {U(r["scenario"]): (r["file"], (U(r["macro_scen"]), U(r["bioen_scen"]), U(r["iea_scen"])))
                for r in csv.DictReader(fh)}


#: the labels of p_longRunInfoAll's info as GAMS writes them (create_longrun_info.gms l. 50-53)
INFO = {"DATA": "data", "FACTORB2000": "factorB2000", "SHARE": "share"}


def longrun_info_all(scenario: str, *, sets_dir: Path, capri_sets_dir: Path, dat_dir: Path, globiom_root: Path,
                     capreg_root: Path, datamarket: Path, worldpop: Path, base_year: str = "2017",
                     base_years: Sequence[str] = ("2016", "2017", "2018")):
    """create_longrun_info.gms with convert_globiom.gms for one GLOBIOM-EU selection: p_longRunInfoAll(region, col,
    row, info, scenario, year) in longrun_supports.read_info's form (years as int, "B2000"). globiom_root: the GLOBIOM
    files as Parquet (one folder per file); capreg_root: CAPREG's res_time_series_<BAS><CC> as Parquet; datamarket:
    p_dataMarket.parquet of the global database; worldpop: worldPop.parquet of arm/allpop."""
    sc = read_scenarios(dat_dir)
    if U(scenario) not in sc:
        raise ValueError(f"{scenario}: not a GLOBIOM-EU selection of convert_globiom.gms ({sorted(sc)})")
    file, scen = sc[U(scenario)]
    S = read_sets(sets_dir, capri_sets_dir)
    G = read_globiom(Path(globiom_root) / file)
    rmap = region_map(S, G)
    P = collect(G, S, scen, S.longyr)
    M, sel, wo = mapped(P, S, rmap, G.region58)
    I, _ = factors(M, S, U(scenario), sel, wo)
    cap: Dict[Tuple[str, str, str, str], float] = {}
    for r in S.nuts0:                                    # create_longrun_info.gms l. 66-70: res_time_series_<BAS><CC>
        f = Path(capreg_root) / f"res_time_series_{base_year[2:]}{r[:2]}" / "DATA1.parquet"
        if not f.exists():
            raise FileNotFoundError(f)
        d = pd.read_parquet(f, columns=["d1", "d2", "d3", "d4", "value"])
        d = d[(d.d1.str.upper() == r) & d.d4.str.isdigit() & d.value.notna() & (d.value != 0)]
        cap.update({(r, U(c), U(w), y): float(v) for c, w, y, v in zip(d.d2, d.d3, d.d4, d.value)})
    prepare_capreg(cap, S.secom, base_years)
    dm = pd.read_parquet(datamarket)
    dm = dm[dm.value.notna() & (dm.value != 0)]
    dmd = {(U(a), U(b), U(c), y): float(v) for a, b, c, y, v in zip(dm.d1, dm.d2, dm.d3, dm.d4, dm.value)}
    prepare_datamarket(dmd)
    wp = pd.read_parquet(worldpop)
    wpd = {(y, U(r)): float(v) for y, r, v in zip(wp.d1, wp.d2, wp.value) if v == v}
    base_factors(I, S, U(scenario), wo, cap, dmd, wpd, base_year, base_years)
    out = {}
    for (r, c, w, i, s, y), v in I.items():
        out[(r, c, w, INFO[i], scenario, int(y) if y.isdigit() else y)] = v
    for k in [k for k in out if k[0] == "TAW"]:                                     # create_longrun_info.gms l. 200
        out.pop(k)
    for (r, c, w, i, s, y), v in list(out.items()):
        if r == "CHN":
            out[("TAW", c, w, i, s, y)] = v
    return out

"""CAPTRD's Aglink-COSIMO load (baseline/load_aglink2023dgAgri.gms, captrd.gms l. 593; CAPRI star 3.0): the DG AGRI
medium-term outlook mapped to CAPRI's positions for the European regions (EU27 and its two parts EU014000 and
EU013000, the United Kingdom, Norway, the Western Balkans, Turkey), stored by CAPTRD as p_result(..., "DGAgri").

In GAMS's order (line numbers of load_aglink2023dgAgri.gms):
  l. 50-167   the data cube p_dbvar of aglink2023dgAgri_oriEUdata.gdx, its biofuel production by feedstock rebooked as in
              Aglink 2020 (p_aglinkOri), fish (FH) from AGLINK2019dgagri_oridata.gdx (l. 206-211)
  l. 213-465  #2 the European regions' data (p_aglink): irregular entries (NA, UNDF) dropped with their whole row and
              year; EU27 totals completed from its parts; food use, whey powder, coarse grains, oilseeds, wheat, sugar
              beet, raw milk, beef feed, biofuels, fossil fuels, molasses, meals, oils; domestic use; net trade and
              stock changes
  l. 466-845  biofuels: quantities to 1000 t, the implicit feedstock yields, the parts' production by feedstock, the
              shares of the EU's two parts (from CAPTRD's p_data at this point, l. 594-640), demand, net trade, prices
              (to EUR per toe), fossil fuels
  l. 860-1058 #3 the mapping to CAPRI (p_aglinkTrd): direct links, macro variables (l. 885-898; the detailed macro
              data p_aglinkMacro of l. 899-1058 are a separate output, not ported here), areas, yields, cows, sugar for
              biofuels, the balance positions with CAPRI's base-year shares, special cases, prices
  l. 1395-1410 #4 the store: p_result(..., "DGAgri") without NA, the EU's imports and exports removed, negatives 0
              (NTRD kept)

GAMS's semantics kept: an assignment covers its whole domain (a tuple whose right-hand side is 0 is deleted), with
$-conditions on the left restricting it; a 0 is an absent record; NA propagates through arithmetic. The GAMS NA is
represented by float('nan'); after l. 229 no NA is left in the European regions' data (the irregular entries are
dropped there), NA remains only where p_aglinkOri is read again (exchange rates, l. 794 and 1355).

CAPTRD's p_data at this point (l. 594-640: CAPREG's years and the base-year values BASM, read before COCO) comes in as
`pdata`, long (region, col, row, t, value); BasYrsT (l. 594-610) from its UAAR years.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "aglink2023dgAgri"
GSETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets"
NA = float("nan")

#: l. 44-47
COEF_HFCS = {"SUGA": 0.92, "MAIZ": 0.60}
#: l. 72-160: biofuel production by feedstock booked in Aglink 2022 (product, measure) and back to 2020's booking
BOOKING_2022_ET = ["MA", "MOL", "OCG", "RI", "RT", "SBE", "SCA", "WT", "ARES", "ECR", "FRES", "MSW", "OTHW"]
BOOKING_2022_BD = ["SL", "VL", "PL", "RL", "SFL", "OVL", "JA", "ARES", "ECR", "FRES", "MSW", "OTHW", "WLF"]
#: l. 272-273, 296
OCG = ["BA", "OC", "RY", "OT", "SO"]
CG = ["MA"] + OCG
WT = ["WTS", "WTD"]
#: l. 707-710
BIO_SRC = ["QP..VL", "QP..NAGR", "QP..SEC", "QP..SBE", "QP..SCA", "QP..WT", "QP..CG", "QP..MOL", "QP..RT", "QP..RI"]
#: l. 682-683: second-generation shares of the EU's old member states (PRIMES-based estimates, as coded)
SECG_SHARE_E14 = {"BD": 0.85, "ET": 0.50}
#: l. 1088: dairy cow activities; l. 1094: beet to sugar
DCOWS = ["DCOW", "DCOH", "DCOL"]
BEET_TO_SUGAR = 0.16
#: l. 1380-1385: biofuel prices are taken at 85% of Aglink's producer price
BIOF_UVAG_FACTOR = 0.85


def _set(name: str, ncol: Optional[int] = None) -> List[Tuple[str, ...]]:
    # the builders write a set under the name its declaration gives (GAMS names are case-insensitive)
    by = {x.stem.lower(): x for x in SETS.glob("*.csv")}
    f = by.get(name.lower(), GSETS / f"{name.lower()}.csv")
    d = pd.read_csv(f, keep_default_na=False, dtype=str)
    cols = [c for c in d.columns if c.startswith("d")]
    return [tuple(r) for r in d[cols].itertuples(index=False)]


def _s1(name: str) -> List[str]:
    return [m[0] for m in _set(name)]


def _ref_set(ref: Path, name: str) -> List[Tuple[str, ...]]:
    d = pd.read_csv(ref / f"{name}.csv", keep_default_na=False, dtype=str)
    cols = [c for c in d.columns if c.startswith("d")]
    return [tuple(r) for r in d[cols].itertuples(index=False)]


class P4(dict):
    """A GAMS parameter over four labels, sparse: a missing key is 0; setting 0 deletes (as GAMS stores no zero)."""

    def g(self, *k) -> float:
        return dict.get(self, k, 0.0)

    def put(self, k, v) -> None:
        if v == 0.0:
            self.pop(k, None)
        else:
            self[k] = v


def _nz(v: float) -> bool:
    """GAMS's truth of a value: nonzero, NA included."""
    return v != 0.0 or math.isnan(v)


def _max0(v: float) -> float:
    return v if math.isnan(v) else max(0.0, v)


def _assign(p: P4, keys: Iterable[tuple], f) -> None:
    """p(k) = f(k) for every k of the domain (GAMS assignment: zero results delete)."""
    out = [(k, f(k)) for k in keys]
    for k, v in out:
        p.put(k, v)


class Sets:
    """The sets the load reads, from the builders' CSVs (tools/build/build_captrd_aglink_sets.py, build_captrd_sets.py)
    and CAPRI's global sets (capri_sources/reference/sets/simini_21730)."""

    def __init__(self, ref: Path):
        self.agEurop = _s1("agEurop")
        self.agEUreg = _s1("agEUreg")
        self.agEUparts = _s1("agEUparts")
        self.agRegs = _s1("agRegs")
        self.agCols = _s1("agCols")
        self.agRows = _s1("agRows")
        self.agYears = _s1("agYears")
        self.aglinkYears = _s1("aglinkYears")
        self.aglinkRegions = _s1("CCC")
        self.aglinkCols = _s1("aglinkCols")
        self.summable = set(_s1("agColsSummable"))
        self.agBioF = _s1("agBioF")
        self.agFosF = _s1("agFosF")
        self.agFuels = _s1("agFuels")
        self.agPrim = _s1("agPrim")
        self.agPri = ["PP", "MAR", "CP", "TAX", "TSP"]                       # l. 192
        self.bioColsQ = _s1("aglinkBioColsQ")
        self.rows_agg = _set("agRowsAggregate_map")
        self.cols_bio = _set("aglinkCols_bioMap")
        self.act_map = _set("aglinkAct_map")
        self.reg_map = _set("aglinkRegions_map")
        self.cols_map = _set("aglinkCols_map")
        self.rows_map = _set("aglinkRows_map")
        self.cols_mapped = set(_s1("aglinkColsMapped"))
        self.rows_mapped = set(_s1("aglinkRowsMapped"))
        self.colsMappedAglink = set(_s1("ColsMappedAglink"))
        self.rowsMappedAglink = set(_s1("RowsMappedAglink"))
        self.europReg = _s1("EuropReg")
        self.EUreg = _s1("EUreg")
        self.EUparts = _s1("EUparts")
        g = lambda n: [m[0] for m in _ref_set(ref, n)]                       # noqa: E731
        self.biofuels = g("BIOFUELS") if (ref / "BIOFUELS.csv").exists() else ["BIOE", "BIOD"]
        self.fosfuels = g("FOSFUELS") if (ref / "FOSFUELS.csv").exists() else ["DISL", "GASL"]
        self.fuels = g("FUELS") if (ref / "FUELS.csv").exists() else self.biofuels + self.fosfuels
        self.reu14 = g("REU14")
        self.reu13 = g("REU11") + [m for m in g("REU02") if m not in set(g("REU11"))]   # sets_captrd.gms l. 190-191
        self.ms = g("MS")
        self.seco_biof = g("SECO_BIOF")
        self.years = g("YEARS")
        self.cols = _s1("cols")              # CAPRI's cols and rows with the mappings' additions (XR, OILM, ...)
        self.rows = _s1("rows")
        self.balPos = g("BALPOS") if (ref / "BALPOS.csv").exists() else []
        self.rows_to_g = _set("ROWS_TO_G")                                    # CAPTRD's own (build_captrd_sets.py)
        self.cropc_to_g = _set("CROPC_TO_G")
        self.sed_to_cak = _ref_set(ref, "SED_TO_CAK") if (ref / "SED_TO_CAK.csv").exists() else []
        self.sed_to_oil = _ref_set(ref, "SED_TO_OIL") if (ref / "SED_TO_OIL.csv").exists() else []
        self.qcposA = ["FOA", "FE", "BF", "CR", "SWG", "OU", "FU", "DEL", "QP..DS"]      # l. 189
        self.qcandposA = set(["QC"] + self.qcposA)
        self.foposA = ["FOI", "WST..HHLD"]                                    # l. 183
        self.foaposA = ["FO", "WST..DIST"]                                    # l. 186

    def europ_of(self, er: str) -> List[str]:
        return [b for a, b in self.reg_map if a == er and b in set(self.agEurop)]


def read_aglink(gdx_dir: Path, fish_dir: Path, sets: Sets) -> P4:
    """p_aglinkOri (l. 50-211): Aglink 2023's cube, rebooked, with Aglink 2019's fish."""
    v = pd.read_parquet(gdx_dir / "p_dbvar.parquet")
    val = v["value"].astype(float).where(v["special"].fillna("").eq(""), NA)
    db: Dict[tuple, float] = {}
    for c, p, m, y, x in zip(v.d1, v.d2, v.d3, v.d4, val):
        db[(c, p, m, y)] = x
    booked = {(p, "QP..ET") for p in BOOKING_2022_ET} | {(p, "QP..BD") for p in BOOKING_2022_BD}
    ori = P4()
    for (c, p, m, y), x in db.items():                                        # l. 162
        if (p, m) not in booked:
            ori.put((c, m, p, y), x)
    acc: Dict[tuple, float] = defaultdict(float)
    for (c, p, m, y), x in db.items():                                        # l. 164-165
        if (p, m) in booked:
            fuel = m.split("..")[1]
            acc[(c, f"QP..{p}", fuel, y)] += x
    for k, x in acc.items():
        if not _nz(ori.g(*k)):
            ori.put(k, x)
    f = pd.read_parquet(fish_dir / "p_aglinkOri.parquet")                   # l. 206-211
    f = f[f.d3 == "FH"]
    regs, cols, yrs = set(sets.aglinkRegions), set(sets.aglinkCols), set(sets.aglinkYears)
    fv = f["value"].astype(float).where(f["special"].fillna("").eq(""), NA)
    for r, c, y, x in zip(f.d1, f.d2, f.d4, fv):
        if r in regs and c in cols and y in yrs and _nz(x):
            ori.put((r, c, "FH", y), x)
    return ori


def _bast_years(pdata: pd.DataFrame, ms: Iterable[str]) -> List[str]:
    """BasYrsT (l. 594-610): the last ex-post year from CAPREG's UAAR (any member state), BAST the year before it,
    BasYrsT the three years around BAST (CAPTRD's years are consecutive)."""
    u = pdata[(pdata["col"] == "UAAR") & (pdata["row"] == "LEVL") & pdata["region"].isin(set(ms))
              & pdata["t"].astype(str).str.fullmatch(r"\d{4}") & (pdata["value"] != 0)]
    last = max(int(t) for t in u["t"])
    bast = last - 1
    return [str(y) for y in (bast - 1, bast, bast + 1)]


def eu_data(ori: P4, sets: Sets, pdata: pd.DataFrame, density: Dict[str, float], oilequ: Dict[str, float]):
    """p_aglink (l. 213-845) and the BAST values written to p_data (l. 622-631). Returns (p_aglink, bast)."""
    S = sets
    eur, yrs = set(S.agEurop), set(S.agYears)
    cols, rows = set(S.agCols), set(S.agRows)
    p = P4()
    # l. 223-236
    irregular = set()
    for (r, c, w, y), v in ori.items():
        if r in eur and c in cols and w in rows and y in yrs and math.isnan(v):
            irregular.add((r, w, y))
    for (r, c, w, y), v in ori.items():
        if r in eur and c in cols and w in rows and y in yrs and (r, w, y) not in irregular:
            p.put((r, c, w, y), _max0(v) if c in S.qcandposA else v)
    # l. 239-240 (NewBiofuelModule on)
    for y in S.agYears:
        xr = ori.g("EUN", "XR", "ME", y)
        for b in S.agBioF:
            p.put(("WLD", "XP", b, y), ori.g("WLD", "XP", b, y) * xr)
        p.put(("WLD", "XP", "OIL", y), ori.g("WLD", "XP", "OIL", y) * xr)

    def keys_of(regs, cs, ws, ys=S.agYears):
        rs, cs_, ws_, ys_ = set(regs), set(cs), set(ws), set(ys)
        return [k for k in p if k[0] in rs and k[1] in cs_ and k[2] in ws_ and k[3] in ys_]

    def sum_parts(c, w, y):
        return sum(p.g(e, c, w, y) for e in S.agEUparts)

    summ = [c for c in S.summable]
    # l. 246-247
    for (r, c, w, y) in {(("EUN",) + k[1:]) for k in keys_of(S.agEUparts, summ, S.agRows)}:
        if not _nz(p.g(r, c, w, y)):
            p.put((r, c, w, y), sum_parts(c, w, y))
    # l. 250-255 (FOA, every agRegs region with data: the European ones)
    for r in S.agEurop:
        for w in S.agRows:
            for y in S.agYears:
                qc = p.g(r, "QC", w, y)
                if math.isnan(qc):
                    continue
                foa, fo = p.g(r, "FOA", w, y), p.g(r, "FO", w, y)
                v = foa + (sum(p.g(r, c, w, y) for c in S.foaposA) if not _nz(foa) else 0.0) \
                    + ((sum(p.g(r, c, w, y) for c in S.foposA) + p.g(r, "WST..DIST", w, y))
                       if (not _nz(foa) and not _nz(fo)) else 0.0)
                p.put((r, "FOA", w, y), v)
    # l. 261-266 (whey powder)
    for e in S.agEUparts:
        for y in S.agYears:
            qp, qpe = p.g(e, "QP", "WYP", y), p.g("EUN", "QP", "WYP", y)
            if math.isnan(qp) or math.isnan(qpe):
                continue
            cond = (qp * qpe != 0) and (p.g(e, "QC", "WYP", y) == 0)
            p.put((e, "QC", "WYP", y), p.g("EUN", "QC", "WYP", y) * (qp / qpe) if cond else 0.0)
    # l. 281-282 (coarse grains for the EU regions; every summable measure)
    for r in S.agEUreg:
        for c in summ:
            for y in S.agYears:
                p.put((r, c, "CG", y), sum(p.g(r, c, g, y) for g in CG))
    non_eu = [r for r in S.agEurop if r not in set(S.agEUreg)]
    # l. 286, 289-290, 301-302 (the other European regions: the aggregate copied to its members)

    def copy_rows(src, dst_rows, regs, cset):
        for r in regs:
            for c in cset:
                for y in S.agYears:
                    v = p.g(r, c, src, y)
                    for d in dst_rows:
                        p.put((r, c, d, y), v)
    copy_rows("OCG", OCG, non_eu, S.agCols)
    copy_rows("OOS", ["RP"], non_eu, S.agCols)
    copy_rows("OOS", ["SF"], non_eu, S.agCols)
    # l. 297-298 (wheat, EUN from its parts)
    for (r, c, w, y) in {(("EUN",) + k[1:]) for k in keys_of(S.agEUparts, summ, WT)}:
        if not _nz(p.g(r, c, w, y)):
            p.put((r, c, w, y), sum_parts(c, w, y))
    # l. 301-302 (WT where missing)
    for r in S.agEurop:
        for c in summ:
            for y in S.agYears:
                if not _nz(p.g(r, c, "WT", y)):
                    p.put((r, c, "WT", y), sum(p.g(r, c, w, y) for w in WT))
    copy_rows("WT", WT, non_eu, S.agCols)                                    # l. 306
    # l. 310-315 (sugar beet)
    for r in S.agEurop:
        for y in S.agYears:
            p.put((r, "QC", "SBE", y), p.g(r, "QP", "SBE", y))
            p.put((r, "OU", "SBE", y), p.g(r, "QC", "SBE", y) - p.g(r, "BF", "SBE", y))
    # l. 320-341 (raw milk)
    for r in S.agEurop:
        for y in S.agYears:
            p.put((r, "QC", "MK", y), p.g(r, "QP", "MK", y))
        if r == "EUN":
            continue
        for y in S.agYears:
            if not _nz(p.g(r, "FU", "MK", y)):
                p.put((r, "FU", "MK", y), p.g(r, "FE", "MK", y) + p.g(r, "OU", "MK", y) + p.g(r, "QP..DS", "MK", y))
        for y in S.agYears:
            if _nz(p.g(r, "FU", "MK", y)) and (p.g(r, "FE", "MK", y) + p.g(r, "OU", "MK", y)
                                               + p.g(r, "QP..DS", "MK", y)) == 0:
                p.put((r, "FE", "MK", y), p.g(r, "FU", "MK", y))
        for y in S.agYears:
            if not _nz(p.g(r, "DEL", "MK", y)):
                p.put((r, "DEL", "MK", y), p.g(r, "QC", "MK", y) - p.g(r, "FU", "MK", y))
    for (r, c, w, y) in {(("EUN",) + k[1:]) for k in keys_of(S.agEUparts, summ, ["MK"])}:   # l. 343-344
        if not _nz(p.g(r, c, w, y)):
            p.put((r, c, w, y), sum_parts(c, w, y))
    # l. 348 (beef feed), l. 352-356 (biofuels), l. 359 (fossil fuels)
    for r in S.agEurop:
        for y in S.agYears:
            p.put((r, "FE", "BV", y), 0.0)
            for b in S.agBioF:
                p.put((r, "BF", b, y), p.g(r, "QC", b, y) - p.g(r, "OU", b, y))
                p.put((r, "FU", b, y), 0.0)
            for f in S.agFosF:
                p.put((r, "FO", f, y), p.g(r, "QC", f, y))
    # l. 364-365 (molasses)
    for r in S.agEurop:
        for y in S.agYears:
            if not _nz(p.g(r, "OU", "MOL", y)):
                p.put((r, "OU", "MOL", y), _max0(p.g(r, "QC", "MOL", y) - sum(p.g(r, c, "MOL", y) for c in S.qcposA)))
    om = [b for a, b in S.rows_agg if a == "OM"]
    for e in S.agEUparts:                                                     # l. 373-374, 379-381
        for y in S.agYears:
            if not _nz(p.g(e, "FE", "OM", y)):
                p.put((e, "FE", "OM", y), sum(p.g(e, "FE", w, y) for w in om))
            p.put((e, "FO", "OL", y), p.g(e, "QC", "OL", y) - p.g(e, "BF", "OL", y) - p.g(e, "OU", "OL", y))
    # l. 389-392 (FO = QC where QC has no breakdown)
    for r in S.agEUreg:
        for w in S.agRows:
            for y in S.agYears:
                qc = p.g(r, "QC", w, y)
                if _nz(qc) and not _nz(sum(p.g(r, c, w, y) for c in S.qcposA)):
                    p.put((r, "FO", w, y), qc)
    # l. 403-405 (QC recalculated)
    for r in S.agEurop:
        for w in S.agRows:
            for y in S.agYears:
                p.put((r, "QC", w, y), sum(p.g(r, c, w, y) for c in S.qcposA)
                      - (p.g(r, "FU", w, y) if w == "MK" else 0.0))
    # l. 426-433 (net trade)
    for r in S.agEurop:
        for w in S.agRows:
            for y in S.agYears:
                ex, im = p.g(r, "EX", w, y), p.g(r, "IM", w, y)
                if ex + im > 0:
                    p.put((r, "NT", w, y), ex - im)
        for b in S.agBioF:
            for y in S.agYears:
                if _nz(p.g(r, "QC", b, y)):
                    p.put((r, "NT", b, y), p.g(r, "QP", b, y) - p.g(r, "QC", b, y))
    # l. 439-446 (stock changes)
    for r in S.agEurop:
        for w in S.agRows:
            for y in S.agYears:
                if _nz(p.g(r, "QP", w, y)) and _nz(p.g(r, "QC", w, y)):
                    p.put((r, "VST", w, y), p.g(r, "QP", w, y) - p.g(r, "QC", w, y) - p.g(r, "NT", w, y))
                if abs(p.g(r, "VST", w, y)) <= 1e-3:
                    p.put((r, "VST", w, y), 0.0)
    for e in S.agEUparts:                                                     # l. 450-463
        for w in S.agRows:
            for y in S.agYears:
                if _nz(p.g("EUN", "VST", w, y)):
                    den = p.g("EUN", "QP", w, y) + p.g("EUN", "QC", w, y)
                    p.put((e, "VST", w, y), p.g("EUN", "VST", w, y) * (p.g(e, "QP", w, y) + p.g(e, "QC", w, y))
                          / den if den > 0 else 0.0)
            for y in S.agYears:
                s_ = p.g(e, "QP", w, y) + p.g(e, "QC", w, y)
                p.put((e, "NT", w, y), (p.g(e, "QP", w, y) - p.g(e, "QC", w, y) - p.g(e, "VST", w, y))
                      if s_ > 0 else 0.0)
    # l. 484-492 (quantities to 1000 t)
    bio_d = {b: sum(density.get(x, 0.0) for x, a in S.rows_map if a == b and x in S.biofuels) for b in S.agBioF}
    fos_d = {f: sum(density.get(x, 0.0) for x, a in S.rows_map if a == f and x in S.fosfuels) for f in S.agFosF}
    bio_o = {b: sum(oilequ.get(x, 0.0) for x, a in S.rows_map if a == b and x in S.biofuels) for b in S.agBioF}
    fos_o = {f: sum(oilequ.get(x, 0.0) for x, a in S.rows_map if a == f and x in S.fosfuels) for f in S.agFosF}
    for r in S.agEurop:
        for y in S.agYears:
            for b in S.agBioF:
                for c in S.bioColsQ:
                    v = p.g(r, c, b, y)
                    if _nz(v):
                        p.put((r, c, b, y), v * bio_d[b])
            for f in S.agFosF:
                for c in ("QC", "FO"):
                    v = p.g(r, c, f, y)
                    if _nz(v):
                        p.put((r, c, f, y), v * fos_d[f])
    # l. 497-532 (implicit biofuel yields)
    yld: Dict[tuple, float] = {}

    def by(src, fuel, col, y):
        bf = p.g("EUN", "BF", src, y)
        return p.g("EUN", col, fuel, y) / bf if _nz(bf) else None
    cg_rows = [b for a, b in S.rows_agg if a == "CG"]
    for y in S.agYears:
        for src, fuel in (("WT", "ET"), ("MA", "ET"), ("OCG", "ET")):
            v = by(src, fuel, f"QP..{src}", y)
            if v is not None:
                yld[(src, fuel, y)] = v
    for r in S.agRegs:
        for y in S.agYears:
            if not _nz(p.g(r, "BF", "CG", y)):
                p.put((r, "BF", "CG", y), sum(p.g(r, "BF", w, y) for w in cg_rows))
            if not _nz(p.g(r, "QP..CG", "ET", y)):
                p.put((r, "QP..CG", "ET", y), p.g(r, "QP..MA", "ET", y) + p.g(r, "QP..OCG", "ET", y))
    for y in S.agYears:
        v = by("CG", "ET", "QP..CG", y)
        if v is not None:
            yld[("CG", "ET", y)] = v
        if not _nz(yld.get(("CG", "ET", y), 0.0)):
            yld[("CG", "ET", y)] = yld.get(("WT", "ET", y), 0.0)
        for src, fuel in (("SBE", "ET"), ("VL", "BD")):
            v = by(src, fuel, f"QP..{src}", y)
            if v is not None:
                yld[(src, fuel, y)] = v
        yld[("WTS", "ET", y)] = yld.get(("WT", "ET", y), 0.0)
    p.bfyld = yld                         # p_BFyld (feedstock, fuel, year): read by the biofuel trends (biofuel_trends.py)
    for r in S.agEurop:                                                       # l. 540-550
        for y in S.agYears:
            if r != "EUN":
                p.put((r, "QP..WT", "ET", y), p.g(r, "BF", "WT", y) * yld.get(("WT", "ET", y), 0.0))
            p.put((r, "QP..WTS", "ET", y), p.g(r, "BF", "WT", y) * yld.get(("WTS", "ET", y), 0.0))
            if r != "EUN":
                p.put((r, "QP..CG", "ET", y), p.g(r, "BF", "CG", y) * yld.get(("CG", "ET", y), 0.0))
                p.put((r, "QP..SBE", "ET", y), p.g(r, "BF", "SBE", y) * yld.get(("SBE", "ET", y), 0.0))
                p.put((r, "QP..VL", "BD", y), p.g(r, "BF", "VL", y) * yld.get(("VL", "BD", y), 0.0))
    # l. 594-640 (BAST of CAPTRD's p_data; the EU parts' shares)
    basyrst = _bast_years(pdata, S.ms)
    pd_ = pdata.set_index(["region", "col", "row", "t"])["value"]
    pdd = pd_.to_dict()

    def pv(r, c, w, t):
        return float(pdd.get((r, c, w, t), 0.0))
    bast = {}
    for m in S.ms:
        for c in ("NAGR", "DOMM"):
            for w in S.seco_biof:
                n = sum(1 for t in basyrst if abs(pv(m, c, w, t)) >= 1e-12)
                if n:
                    bast[(m, c, w)] = sum(pv(m, c, w, t) for t in basyrst) / n

    def bv(m, c, w):
        return bast.get((m, c, w), 0.0)
    reu14, reu13 = S.reu14, S.reu13

    def share(c, w, f):
        a = sum(f(m, c, w) for m in reu14)
        b = sum(f(m, c, w) for m in reu13)
        return a / (a + b) if (a + b) != 0 else 0.0
    nagr = {("E14", "ET"): share("NAGR", "BIOE", bv), ("E14", "BD"): share("NAGR", "BIOD", bv)}
    for b in S.agBioF:
        nagr[("NMS", b)] = 1 - nagr.get(("E14", b), 0.0)
    secg = {("E14", b): SECG_SHARE_E14[b] for b in SECG_SHARE_E14}
    for b in S.agBioF:
        secg[("NMS", b)] = 1 - secg.get(("E14", b), 0.0)
    dem = {("E14", "ET"): share("DOMM", "BIOE", bv), ("E14", "BD"): share("DOMM", "BIOD", bv)}
    for b in S.agBioF:
        dem[("NMS", b)] = 1 - dem.get(("E14", b), 0.0)
    ores = [c for a, c in S.cols_bio if a == "bioORES"]
    for r in S.agEurop:                                                       # l. 688-700
        for b in S.agBioF:
            for y in S.agYears:
                if not _nz(p.g(r, "QP..NAGR", b, y)):
                    p.put((r, "QP..NAGR", b, y), sum(p.g(r, c, b, y) for c in ores))
    for e in S.agEUparts:
        for b in S.agBioF:
            for y in S.agYears:
                if _nz(p.g("EUN", "QP..NAGR", b, y)):
                    p.put((e, "QP..NAGR", b, y), p.g("EUN", "QP..NAGR", b, y) * nagr.get((e, b), 0.0))
    for r in S.agEurop:
        for b in S.agBioF:
            for y in S.agYears:
                if not _nz(p.g(r, "QP..SEC", b, y)):
                    p.put((r, "QP..SEC", b, y), p.g(r, "QP..ARES", b, y) + p.g(r, "QP..ECR", b, y))
    for e in S.agEUparts:
        for b in S.agBioF:
            for y in S.agYears:
                if _nz(p.g("EUN", "QP..SEC", b, y)):
                    p.put((e, "QP..SEC", b, y), p.g("EUN", "QP..SEC", b, y) * secg.get((e, b), 0.0))
    for r in S.agEurop:                                                       # l. 714-715
        for b in S.agBioF:
            for y in S.agYears:
                p.put((r, "QP", b, y), sum(p.g(r, c, b, y) for c in BIO_SRC))
    # l. 720-728 (EUN's biofuel demand extended by the self-sufficiency of the years within 5)
    yrs_i = {y: int(y) for y in S.agYears}
    upd = {}
    for b in S.agBioF:
        for y in S.aglinkYears:
            if y not in yrs_i or _nz(p.g("EUN", "QC", b, y)):
                continue
            near = [z for z in S.agYears if abs(int(y) - yrs_i[z]) <= 5 and _nz(p.g("EUN", "QP", b, z))
                    and _nz(p.g("EUN", "QC", b, z))]
            sqp = sum(p.g("EUN", "QP", b, z) for z in near)
            if near and _nz(sqp):
                upd[("EUN", "QC", b, y)] = p.g("EUN", "QP", b, y) * sum(p.g("EUN", "QC", b, z) for z in near) / sqp
    for k, v in upd.items():
        p.put(k, v)
    for e in S.agEUparts:                                                     # l. 730-731
        for b in S.agBioF:
            for y in S.agYears:
                p.put((e, "QC", b, y), p.g("EUN", "QC", b, y) * dem.get((e, b), 0.0))
    for r in S.agEurop:                                                       # l. 734
        for b in S.agBioF:
            for y in S.agYears:
                p.put((r, "NT", b, y), p.g(r, "QP", b, y) - p.g(r, "QC", b, y))
    for e in S.agEUparts:                                                     # l. 737-738
        for b in S.agBioF:
            for y in S.agYears:
                qe = p.g("EUN", "QC", b, y)
                p.put((e, "OU", b, y), p.g("EUN", "OU", b, y) * p.g(e, "QC", b, y) / qe if _nz(qe) else 0.0)
    for r in S.agEurop:                                                       # l. 740
        for b in S.agBioF:
            for y in S.agYears:
                p.put((r, "BF", b, y), p.g(r, "QC", b, y) - p.g(r, "OU", b, y))
    # l. 745-756 (fossil fuels' demand shares from the base year)
    for f, w in (("DIE", "DISL"), ("GAS", "GASL")):
        a = sum(pv(m, "DOMM", w, "BASM") for m in reu14)
        b_ = sum(pv(m, "DOMM", w, "BASM") for m in reu13)
        dem[("E14", f)] = a / (a + b_)
    for f in S.agFosF:
        dem[("NMS", f)] = 1 - dem[("E14", f)]
    for e in S.agEUparts:
        for f in S.agFosF:
            for y in S.agYears:
                p.put((e, "QC", f, y), p.g("EUN", "QC", f, y) * dem[(e, f)])
    # l. 790-822 (prices, NewBiofuelModule on)
    for r in S.agEurop:
        for y in S.agYears:
            xr = ori.g(r, "XR", "ME", y)
            if _nz(xr):
                for c in S.agPri:
                    for f in S.agFuels:
                        v = p.g(r, c, f, y)
                        p.put((r, c, f, y), v * ori.g("EUN", "XR", "ME", y) / xr)
        for y in S.agYears:
            for c in S.agPri:
                for b in S.agBioF:
                    p.put((r, c, b, y), p.g(r, c, b, y) * 10 / bio_d[b] / bio_o[b])
    for y in S.agYears:
        for b in S.agBioF:
            p.put(("WLD", "XP", b, y), p.g("WLD", "XP", b, y) * 10 / bio_d[b] / bio_o[b])
    for r in S.agEurop:
        for y in S.agYears:
            for c in S.agPri:
                for f in S.agFosF:
                    p.put((r, c, f, y), p.g(r, c, f, y) * 10 / fos_d[f] / fos_o[f])
            for f in S.agFosF:
                p.put((r, "PP", f, y), p.g(r, "CP", f, y) - p.g(r, "TAX", f, y))
    for y in S.agYears:
        p.put(("WLD", "XP", "OIL", y), p.g("WLD", "XP", "OIL", y) * 10 / density["CRDO"])
    for e in S.agEUparts:
        for y in S.agYears:
            for c in S.agPri:
                for f in S.agFuels:
                    p.put((e, c, f, y), p.g("EUN", c, f, y))
    return p, bast


def to_capri(p: P4, ori: P4, sets: Sets, pdata: pd.DataFrame) -> P4:
    """p_aglinkTrd (l. 860-1390, without the detailed macro data of l. 899-1058): Aglink's data on CAPRI's regions,
    columns and rows."""
    S = sets
    T = P4()
    eurr = S.europReg
    emap = {er: S.europ_of(er) for er in eurr}
    rmap: Dict[str, List[str]] = defaultdict(list)          # aglinkRows_map(rows, agRows)
    agr = set(S.agRows)
    for a, b in S.rows_map:
        if b in agr:
            rmap[a].append(b)
    cmap: Dict[str, List[str]] = defaultdict(list)
    for a, b in S.cols_map:
        cmap[a].append(b)

    def sag(er, c, w, y):
        return sum(p.g(a, c, w, y) for a in emap[er])
    # l. 876-878 (direct links)
    for er in eurr:
        for col in S.colsMappedAglink:
            ac = [c for c in cmap.get(col, []) if c in S.cols_mapped]
            if not ac:
                continue
            for row in S.rowsMappedAglink:
                ar = [w for x, w in S.rows_map if x == row and w in S.rows_mapped]
                if not ar:
                    continue
                for y in S.agYears:
                    T.put((er, col, row, y), sum(p.g(a, c, w, y) for a in emap[er] for c in ac for w in ar))
    # l. 885-898 (macro variables)
    for er in eurr:
        for y in S.agYears:
            T.put((er, "INHA", "LEVL", y), sag(er, "POP", "ME", y))
    for e in ("E14", "NMS"):
        for y in S.agYears:
            if not _nz(p.g(e, "XR", "ME", y)):
                p.put((e, "XR", "ME", y), p.g("EUN", "XR", "ME", y))
    for er in eurr:
        for y in S.agYears:
            T.put((er, "XR", "LEVL", y), sag(er, "XR", "ME", y))
            T.put((er, "GDPI", "LEVL", y), sag(er, "GDPI", "ME", y))
    # l. 1063-1083 (areas, yields, cows)
    amap: Dict[str, List[str]] = defaultdict(list)
    for a, b in S.act_map:                                  # aglinkAct_map(cols, agRows)
        if b in agr:
            amap[a].append(b)
    for er in eurr:
        for col, ar in amap.items():
            if emap[er]:
                for y in S.agYears:
                    T.put((er, col, "LEVL", y), sum(p.g(a, "AH", w, y) for a in emap[er] for w in ar))
        for col in S.cols:
            ar = amap.get(col, [])
            for y in S.agYears:
                T.put((er, col, "YILD", y), sum(1000 * p.g(a, "YLD", w, y) for a in emap[er] for w in ar))
        for y in S.agYears:
            for d in DCOWS:
                T.put((er, d, "LEVL", y), sag(er, "CI", "MK", y))
            T.put((er, "SCOW", "LEVL", y), sag(er, "CI", "BV", y))
            T.put((er, "BIOF", "SUGA", y), BEET_TO_SUGAR * sag(er, "BF", "SBE", y))   # l. 1093-1094
    # base-year shares of CAPRI's member states (l. 1103-1176)
    pdd = pdata[pdata["t"] == "BASM"].set_index(["region", "col", "row"])["value"].to_dict()
    ms_of = {er: [m for m, a in S.reg_map if m in set(S.ms) and a in set(emap[er])] for er in eurr}

    def bsum(er, cs, w):
        return sum(float(pdd.get((m, c, w), 0.0)) for m in ms_of[er] for c in cs)

    def shares(er, cs, tot_cs):
        out = {}
        for w in S.rowsMappedAglink:
            den = bsum(er, tot_cs, w)
            if den != 0:
                for c in cs:
                    out[(c, w)] = bsum(er, [c], w) / den
        return out
    prim = defaultdict(list)
    for a, b in S.rows_map:
        if b in set(S.agPrim):
            prim[a].append(b)
    for er in eurr:                                                           # l. 1103-1106
        for row, ar in prim.items():
            for y in S.agYears:
                T.put((er, "GROF", row, y), sum(p.g(a, "QP", w, y) for a in emap[er] for w in ar))
    colsGrof, colsInd, colsHcom = ["SEDF", "LOSF"], ["PRCM", "INDM"], ["HCOM", "SEDM", "LOSM"]
    for er in eurr:                                                           # l. 1110-1116
        sh = shares(er, colsGrof, ["GROF"])
        for (c, w), s_ in sh.items():
            if _nz(s_):
                for y in S.agYears:
                    T.put((er, c, w, y), s_ * T.g(er, "GROF", w, y))

    def eu27_sum(cs):
        keys = {(c, w, y) for (r, c, w, y) in list(T) if r in set(S.EUparts) and c in set(cs)}
        old = [k for k in T if k[0] == "EU27yr19" and k[1] in set(cs)]
        for k in old:
            T.put(k, 0.0)
        for c, w, y in keys:
            T.put(("EU27yr19", c, w, y), sum(T.g(e, c, w, y) for e in S.EUparts))
    eu27_sum(colsGrof)
    for er in eurr:                                                           # l. 1130-1144
        sh = shares(er, colsInd, colsInd)
        for c in colsInd:
            for k in [k for k in T if k[0] == er and k[1] == c]:
                T.put(k, 0.0)
            for row, ar in rmap.items():
                s_ = sh.get((c, row), 0.0)
                if not s_:
                    continue
                for y in S.agYears:
                    T.put((er, c, row, y), sum(s_ * (p.g(a, "CR", w, y) + p.g(a, "DEL", w, y) + p.g(a, "SWG", w, y)
                                                     + p.g(a, "OU", w, y)) for a in emap[er] for w in ar))
    eu27_sum(colsInd)
    for er in eurr:                                                           # l. 1148-1150
        for y in S.agYears:
            T.put((er, "INDM", "BIOE", y), sag(er, "OU", "ET", y))
            T.put((er, "LOSM", "BIOE", y), 0.0)
    for er in eurr:                                                           # l. 1155-1166 (parallel assignment)
        sh = shares(er, colsHcom, colsHcom)
        hcom = {(w, y): T.g(er, "HCOM", w, y) for (r, c, w, y) in list(T) if r == er and c == "HCOM"}
        for c in colsHcom:
            for k in [k for k in T if k[0] == er and k[1] == c]:
                T.put(k, 0.0)
        for c in colsHcom:
            for row, ar in rmap.items():
                s_ = sh.get((c, row), 0.0)
                if not s_ or not emap[er]:
                    continue
                n = len(emap[er]) * len(ar)
                for y in S.agYears:
                    T.put((er, c, row, y), n * s_ * hcom.get((row, y), 0.0))
    eu27_sum(colsHcom)
    # l. 1172-1186 (DOMM with STCM; negative DOMM)
    for er in eurr:
        for w in S.rows:
            for y in S.agYears:
                d, st = T.g(er, "DOMM", w, y), T.g(er, "STCM", w, y)
                if d + st < 0:
                    for c in ("HCOM", "DOMM"):
                        T.put((er, c, w, y), T.g(er, c, w, y) - (d + st) + 1e-6)
        for w in S.rows:
            for y in S.agYears:
                T.put((er, "DOMM", w, y), T.g(er, "DOMM", w, y) + T.g(er, "STCM", w, y))
    neg = [k for k, v in T.items() if k[1] == "DOMM" and v < 0]
    if neg:
        raise ValueError(f"DOMM negative after the stock change (load_aglink2023dgAgri.gms l. 1184): {neg[:5]}")
    # l. 1193-1196 (cakes and oils outside the EU)
    cakes = {b for a, b in S.sed_to_cak}
    oils = {b for a, b in S.sed_to_oil}
    for er in [r for r in eurr if r not in set(S.EUreg)]:
        for c in S.cols:
            for y in S.agYears:
                vm, vo = T.g(er, c, "OILM", y), T.g(er, c, "OILO", y)
                for w in cakes:
                    T.put((er, c, w, y), vm)
                for w in oils:
                    T.put((er, c, w, y), vo)
    # l. 1199-1218 (raw milk, milk)
    for er in eurr:
        for y in S.agYears:
            T.put((er, "GROF", "COMI", y), sag(er, "QP", "MK", y))
            T.put((er, "LOSF", "COMI", y), sag(er, "FE", "MK", y))
            T.put((er, "HCOM", "COMI", y), sum(p.g(a, "OU", "MK", y) + p.g(a, "QP..DS", "MK", y) for a in emap[er]))
            T.put((er, "PRCM", "COMI", y), sag(er, "DEL", "MK", y))
            T.put((er, "DOMM", "COMI", y), T.g(er, "PRCM", "COMI", y) + T.g(er, "HCOM", "COMI", y))
        for k in [k for k in T if k[0] == er and k[2] == "MILK"]:
            T.put(k, 0.0)
        for y in S.agYears:
            T.put((er, "MAPR", "MILK", y), T.g(er, "PRCM", "COMI", y))
            T.put((er, "DOMM", "MILK", y), T.g(er, "MAPR", "MILK", y))
            T.put((er, "PRCM", "MILK", y), T.g(er, "DOMM", "MILK", y))
    # l. 1223-1258 (biofuels by source)
    for er in eurr:
        for y in S.agYears:
            for c, src, f, w in (("NAGR", "QP..NAGR", "ET", "BIOE"), ("NAGR", "QP..NAGR", "BD", "BIOD"),
                                 ("SECG", "QP..SEC", "ET", "BIOE"), ("SECG", "QP..SEC", "BD", "BIOD"),
                                 ("bioeWhea", "QP..WT", "ET", "BIOE"), ("bioECgra", "QP..CG", "ET", "BIOE"),
                                 ("bioeSuga", "QP..SBE", "ET", "BIOE"), ("bioDOilP", "QP..VL", "BD", "BIOD")):
                T.put((er, c, w, y), sag(er, src, f, y))
            T.put((er, "bioeExog", "BIOE", y), max(0.0, T.g(er, "QP", "BIOE", y) - T.g(er, "bioeWhea", "BIOE", y)
                                                   - T.g(er, "bioECgra", "BIOE", y) - T.g(er, "bioeSuga", "BIOE", y)
                                                   - T.g(er, "NAGR", "BIOE", y) - T.g(er, "SECG", "BIOE", y)))
            T.put((er, "biodExog", "BIOD", y), max(0.0, T.g(er, "QP", "BIOD", y) - T.g(er, "bioDOilP", "BIOD", y)
                                                   - T.g(er, "NAGR", "BIOD", y) - T.g(er, "SECG", "BIOD", y)))
    # l. 1262-1279 (CERE, OILS, WHEA)
    rtg, ctg = S.rows_to_g, S.cropc_to_g
    for er in eurr:
        for g in ("CERE", "OILS"):
            mem = [a for a, b in rtg if b == g]
            cmem = [a for a, b in ctg if b == g]
            for y in S.agYears:
                for bp in S.balPos:
                    if not _nz(T.g(er, bp, g, y)):
                        T.put((er, bp, g, y), sum(T.g(er, bp, w, y) for w in mem))
                if not _nz(T.g(er, g, "LEVL", y)):
                    T.put((er, g, "LEVL", y), sum(T.g(er, c, "LEVL", y) for c in cmem))
        for y in S.agYears:
            for bp in S.balPos:
                if not _nz(T.g(er, bp, "WHEA", y)):
                    T.put((er, bp, "WHEA", y), T.g(er, bp, "SWHE", y) + T.g(er, bp, "DWHE", y))
            if not _nz(T.g(er, "WHEA", "LEVL", y)):
                T.put((er, "WHEA", "LEVL", y), T.g(er, "SWHE", "LEVL", y) + T.g(er, "DWHE", "LEVL", y))
    # l. 1284-1289 (HFCS)
    for er in eurr:
        for y in S.agYears:
            T.put((er, "HCOS", "HFCS", y), sag(er, "FO..SHR", "HFCS", y))
            T.put((er, "S1COM", "HFCS", y), sum(p.g(a, "QP", "HFCS", y) / p.g(a, "QC", "HFCS", y)
                                                 for a in emap[er] if _nz(p.g(a, "QC", "HFCS", y))))
    # l. 1323-1335 (prices: UVAG)
    for er in eurr:
        for row in S.rows:
            ar = rmap.get(row, [])
            for y in S.agYears:
                if er not in set(S.EUreg):
                    if _nz(sum(ori.g(a, "XR", "ME", y) for a in emap[er])):
                        T.put((er, "UVAG", row, y), sum(p.g(a, "PP", w, y) * ori.g("EUN", "XR", "ME", y)
                                                        / ori.g(a, "XR", "ME", y) for a in emap[er] for w in ar))
                else:
                    T.put((er, "UVAG", row, y), sum(p.g(a, "PP", w, y) for a in emap[er] for w in ar))
        for y in S.agYears:
            T.put((er, "UVAG", "PARI", y), T.g(er, "UVAG", "RICE", y))
            T.put((er, "UVAG", "RICE", y), 0.0)
    # l. 1340-1365 (biofuel prices and taxes)
    for er in eurr:
        for y in S.agYears:
            for w in S.biofuels:
                ab = [b for b in rmap.get(w, []) if b in set(S.agBioF)]
                T.put((er, "PROCMARG", w, y), sum(p.g(a, "MAR", b, y) for a in emap[er] for b in ab))
                T.put((er, "UVAG", w, y), sum(p.g(a, "PP", b, y) for a in emap[er] for b in ab) * BIOF_UVAG_FACTOR)
                T.put((er, "UVAP", w, y), sum(p.g(a, "PP", b, y) for a in emap[er] for b in ab))
                T.put((er, "TARS", w, y), sum(p.g(a, "TSP", b, y) for a in emap[er] for b in ab))
                T.put((er, "TARV", w, y), sum(p.g(a, "TAV", b, y) for a in emap[er] for b in ab) * 100)
            for w in S.fuels:
                af = [b for b in rmap.get(w, []) if b in set(S.agFuels)]
                T.put((er, "CTAX", w, y), sum(p.g(a, "TAX", b, y) for a in emap[er] for b in af))
                T.put((er, "UVAD", w, y), sum(p.g(a, "CP", b, y) for a in emap[er] for b in af))
            for w in S.fosfuels:
                af = [b for b in rmap.get(w, []) if b in set(S.agFosF)]
                T.put((er, "UVAP", w, y), sum(p.g(a, "CP", b, y) - p.g(a, "TAX", b, y) for a in emap[er] for b in af))
    # l. 1370-1374 (DDGS)
    for er in eurr:
        for y in S.agYears:
            v = 0.0
            for a in emap[er]:
                q = p.g(a, "QP", "DDG", y) + p.g(a, "QP", "CGF", y)
                if _nz(q):
                    v += (p.g(a, "PP", "DDG", y) * p.g(a, "QP", "DDG", y) + p.g(a, "PP", "CGF", y)
                          * p.g(a, "QP", "CGF", y)) / q
            T.put((er, "UVAG", "DDGS", y), v)
    return T


def dgagri(T: P4, sets: Sets) -> pd.DataFrame:
    """p_result(..., "DGAgri") (l. 1395-1404): no NA, the EU's EXPT and IMPT removed, negatives 0 except NTRD."""
    eur, eu = set(sets.europReg), set(sets.EUreg)
    cols, rws = {x.upper() for x in sets.cols}, {x.upper() for x in sets.rows}
    rows = []
    for (r, c, w, y), v in T.items():
        # p_result(EuropReg, cols, rows, years): GDPI, HCOS, chkBalC, ... are not CAPRI columns and are not stored
        if r not in eur or math.isnan(v) or c.upper() not in cols or w.upper() not in rws:
            continue
        if r in eu and c in ("EXPT", "IMPT"):
            continue
        if c != "NTRD":
            v = max(0.0, v)
        if v != 0.0:
            rows.append((r, c, w, y, v))
    return pd.DataFrame(rows, columns=["region", "col", "row", "t", "value"])


def run(gdx_dir: Path, fish_dir: Path, ref_sets: Path, pdata: pd.DataFrame, density: Dict[str, float],
        oilequ: Dict[str, float]):
    """The Aglink stage: (p_result DGAgri as a long table, p_aglink, the BAST values written to p_data)."""
    sets = Sets(ref_sets)
    ori = read_aglink(gdx_dir, fish_dir, sets)
    p, bast = eu_data(ori, sets, pdata, density, oilequ)
    T = to_capri(p, ori, sets, pdata)
    return dgagri(T, sets), p, bast

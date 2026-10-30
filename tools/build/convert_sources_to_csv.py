"""The CSV conversion of the source files that were not CSV (the project lead's decision, 30 October 2026: "Input data
must be in .csv format").

The originals are read from the repository's history, `git show 6d25163:<path>` (BASE below): they were deleted from
the tree once converted, so the conversion is reproducible from any clone. Each original is converted faithfully:
every record and every value as the file writes it (the number text as written; repr(float) where the reader returns
a parsed number: Excel cells, the parse of minfert_redu_by_crop.gms), GAMS labels in the case the file writes them
(the builders that upper-case them still do), one CSV per symbol, named after CAPRI's symbol. From CAPRI's GAMS code
files only the statements the builders read are converted, by the extraction the builders used before (moved here
unchanged); the CSV declarations (capri_data/schema/34_sources_csv.sql) cite the file and lines.

  gdxdump text (gams_text.gdxdump_symbols)
    envind/fao_landuse_2000_P.txt                      -> envind/fao_landuse_2000_P.csv
    envind/ipcc_wetlands_p_emifacOrganicSoil_ori.txt   -> envind/ipcc_wetlands_p_emifacOrganicSoil_ori.csv
    envind/orgsoil_share_p_orgsoilori.txt              -> envind/orgsoil_share_p_orgsoilori.csv
    ghgtech/LitRevFertTech_p_litRevFertTechs.txt       -> ghgtech/LitRevFertTech_p_litRevFertTechs_all.csv
    ghgtech/miti_data_jul15_p_ghgMiti.txt              -> ghgtech/miti_data_jul15_p_ghgMiti.csv (the dump's sets
                                                          allMitiTech, mitiTech_map, mitiTarget, mitiInfo: read by no
                                                          code, not written)
    water/cropwat.gms                                  -> water/cropwat_p_cropwatReq.csv
    water/irrishare.gms                                -> water/irrishare_p_irriShare.csv
  CAPRI's data include files (gams_text.parameter_records, table_records)
    capri_dat/biofuel/biofuel_technology_params.gms    -> ..._{p_ExtrRates, p_ByProduct}.csv (p_secgConv, p_oilEqu,
                                                          p_density: read by no code, not written)
    capri_dat/coco/milk_quota_dat.gms                  -> milk_quota_dat_p_MQuotaDat.csv
    capri_dat/policy/livestock_units.gms               -> livestock_units_p_LUUnits.csv
    capri_dat/policy/smal_pshar.gms                    -> smal_pshar_p_smallProdShare.csv
    capri_dat/policy/wintercovershare.gms              -> wintercovershare_p_winterCoverShare0.csv (capri_gams/
                                                          wintercovershare.gms was the same file, byte for byte)
  CAPRI's GAMS code, the statements the builders read
    capri_gams/baseline/labour_ageline.gms             -> labour_ageline_p_minLabourPerAct.csv
    capri_gams/pol_input/mquota_update.gms             -> mquota_update_PMQuotaReg.csv
    capri_gams/envind/gascoeff.gms                     -> gascoeff_p_nutContCropOutput_STRA.csv
    capri_gams/fert/fertpar.gms                        -> fertpar_{MAXF, doubleMaxf, p_nfixRate_gras,
                                                          p_nitrFact_RALL_GRAE_BioFix}.csv
    capri_gams/inputs/yieldIY.gms                      -> yieldIY_p_inputDemandFactor.csv
    policy/minfert_redu_by_crop.gms                    -> minfert_redu_by_crop_{p_checkSmallMine, limCres}.csv
  Excel
    capri_star/nutrient_cont_usda_export.xlsx          -> capri_star/nutrient_cont_usda_p_nutrientCont.csv
    nuts/NUTS2021.xlsx                                 -> nuts/nuts2016_2021.csv ('Changes detailed NUTS 2016-2021')
    nuts/NUTS2013-NUTS2016__1_.xlsx                    -> nuts/nuts2013_2016.csv
    nuts/NUTS2021-NUTS2024.xlsx                        -> nuts/nuts2024.csv, nuts2021_2024.csv
    nuts2013_2016, nuts2016_2021, nuts2021_2024 and nuts2024 existed before without a writer and are read
    (build_nuts2024_reporting.py, a test); they are written as they were (their columns, CRLF line ends; nuts2016_2021
    and nuts2021_2024 with the labels stripped of surrounding white space). Not converted, removed at the project lead's request
    (30 October 2026: read by no code; they remain in git history and in the project lead's uploads): the other
    sheets of these workbooks and the workbooks NUTS_2010_-_NUTS_2013.xls and NUTS2024-NUTS2027.xlsx.
  JSON
    eu_tariff_provenance.json                          -> eu_tariff_provenance.csv (one row per commodity)
  (Removed without conversion, read by no code, at the project lead's request: capri_trade_regions_2017.json and
  jrc121368/{published_results.json, scenario_specification.json, jrc121368_report_text.txt}.)
  (world_price_provenance.json was written by tools/build/build_world_prices.py, not converted here; since 30 October
  2026 the source of each world price is summarised in capri_data/schema/02_provenance_notes.sql.)

Paths are under capri_data/sources. Running the converter again rewrites the same bytes.

    python tools/build/convert_sources_to_csv.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "lib")]
from gams_text import gdxdump_symbols, parameter_records, read_text, table_records  # noqa: E402

#: the commit that holds the originals (origin/dev before the conversion)
BASE = "6d25163"
SRC = "capri_data/sources"


def original(rel: str) -> bytes:
    """The original file capri_data/sources/<rel> as committed in BASE."""
    return subprocess.run(["git", "show", f"{BASE}:{SRC}/{rel}"], cwd=ROOT, check=True, capture_output=True).stdout


def write(rel: str, header, rows, crlf: bool = False) -> None:
    """capri_data/sources/<rel>: the header and the rows (text) as CSV, UTF-8."""
    p = ROOT / SRC / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n" if crlf else "\n")
    w.writerow(header)
    n = 0
    for r in rows:
        if len(r) != len(header):
            raise ValueError(f"{rel}: {len(header)} columns expected, row {r!r}")
        w.writerow(r)
        n += 1
    data = buf.getvalue().encode("utf-8")
    if not p.exists() or p.read_bytes() != data:
        p.write_bytes(data)
    print(f"{rel}: {n} records")


# --- gdxdump text --------------------------------------------------------------------------------------------------

#: original -> {symbol: (CSV, columns)}; every symbol of the dump is converted
GDXDUMP = {
    "envind/fao_landuse_2000_P.txt": {
        "P": ("envind/fao_landuse_2000_P.csv", ["fao_code", "climate_zone", "land_use", "value"])},
    "envind/ipcc_wetlands_p_emifacOrganicSoil_ori.txt": {
        "p_emifacOrganicSoil_ori": ("envind/ipcc_wetlands_p_emifacOrganicSoil_ori.csv",
                                    ["gas", "land_use", "climate_zone", "value"])},
    "envind/orgsoil_share_p_orgsoilori.txt": {
        "p_OrgSoilOri": ("envind/orgsoil_share_p_orgsoilori.csv", ["region", "item", "value"])},
    "ghgtech/LitRevFertTech_p_litRevFertTechs.txt": {
        "p_litRevFertTechs": ("ghgtech/LitRevFertTech_p_litRevFertTechs_all.csv",
                              ["region", "technology", "activity", "system", "item", "value"])},
    "ghgtech/miti_data_jul15_p_ghgMiti.txt": {
        "p_ghgMiti": ("ghgtech/miti_data_jul15_p_ghgMiti.csv",
                      ["region", "activity", "technology", "target", "info", "value"]),
        # the dump's sets, read by no code (the project lead's rule: only what a builder or the model reads)
        "allMitiTech": None, "mitiTech_map": None, "mitiTarget": None, "mitiInfo": None},
    "water/cropwat.gms": {
        "p_cropwatReq": ("water/cropwat_p_cropwatReq.csv", ["region", "crop", "item", "value"])},
    "water/irrishare.gms": {
        "p_irriShare": ("water/irrishare_p_irriShare.csv", ["region", "item", "type", "year", "value"])},
}


def convert_gdxdumps() -> None:
    for rel, symbols in GDXDUMP.items():
        found = gdxdump_symbols(read_text(original(rel), "cp1252"), rel)
        if sorted(s[1] for s in found) != sorted(symbols):
            raise ValueError(f"{rel}: symbols {[s[1] for s in found]}, expected {sorted(symbols)}")
        for kind, name, dims, _desc, recs in found:
            if symbols[name] is None:
                continue
            out, cols = symbols[name]
            if kind.lower() == "set" and not any(r[-1] for r in recs):
                recs = [r[:-1] for r in recs]                     # a set without element texts: the keys only
            write(out, cols, recs)


# --- CAPRI's data include files ------------------------------------------------------------------------------------

#: original -> [(symbol, kind, row dims, CSV, columns)]
GAMS_DATA = {
    "capri_dat/biofuel/biofuel_technology_params.gms": [
        ("p_ExtrRates", "parameter", 2, "capri_dat/biofuel/biofuel_technology_params_p_ExtrRates.csv",
         ["fuel", "stock", "value"]),
        ("p_ByProduct", "parameter", 2, "capri_dat/biofuel/biofuel_technology_params_p_ByProduct.csv",
         ["byproduct", "stock", "value"]),
        ],
    "capri_dat/coco/milk_quota_dat.gms": [
        ("p_MQuotaDat", "table", 2, "capri_dat/coco/milk_quota_dat_p_MQuotaDat.csv",
         ["region", "info", "year", "value"])],
    "capri_dat/policy/livestock_units.gms": [
        ("p_LUUnits", "parameter", 1, "capri_dat/policy/livestock_units_p_LUUnits.csv", ["act", "value"])],
    "capri_dat/policy/smal_pshar.gms": [
        ("p_smallProdShare", "table", 1, "capri_dat/policy/smal_pshar_p_smallProdShare.csv",
         ["year", "region", "value"])],
    "capri_dat/policy/wintercovershare.gms": [
        ("p_winterCoverShare0", "parameter", 2, "capri_dat/policy/wintercovershare_p_winterCoverShare0.csv",
         ["region", "act", "value"])],
    "capri_gams/baseline/labour_ageline.gms": [
        ("p_minLabourPerAct", "parameter", 1, "capri_gams/baseline/labour_ageline_p_minLabourPerAct.csv",
         ["act", "value"])],
    "capri_gams/pol_input/mquota_update.gms": [
        ("PMQuotaReg", "table", 2, "capri_gams/pol_input/mquota_update_PMQuotaReg.csv",
         ["region", "info", "year", "value"])],
}


def convert_gams_data() -> None:
    if original("capri_gams/wintercovershare.gms") != original("capri_dat/policy/wintercovershare.gms"):
        raise ValueError("capri_gams/wintercovershare.gms differs from capri_dat/policy/wintercovershare.gms")
    for rel, stmts in GAMS_DATA.items():
        text = read_text(original(rel))
        for name, kind, dims, out, cols in stmts:
            recs = (parameter_records(text, name, dims, rel) if kind == "parameter"
                    else table_records(text, name, dims, rel))
            write(out, cols, recs)


# --- CAPRI's GAMS code: the statements the builders read -----------------------------------------------------------

def straw_content(txt: str):
    """envind/gascoeff.gms, TABLE p_nutContCropOutput, row STRA: (nutrient, value text) for NITF, PHOF, POTF (the
    extraction of tools/build/build_npk_balance_2030.py)."""
    blk = txt[txt.index("TABLE p_nutContCropOutput"):]
    m = re.search(r"^\s*STRA\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", blk, re.M)
    return list(zip(("NITF", "PHOF", "POTF"), m.groups()))


def need_bounds(txt: str):
    """fert/fertpar.gms: MAXF("NITF"|"PHOF"|"POTF") = v; MAXF(FNUT) = MAXF(FNUT) * s; set doubleMaxf(PACT) / ... /
    (the extraction of tools/build/build_npk_balance_2030.py): ([(nutrient, v, s)], [activity])."""
    mx = re.findall(r'^\s*MAXF\("(NITF|PHOF|POTF)"\)\s*=\s*([\d.]+)\s*;', txt, re.M)
    sc = re.search(r"^\s*MAXF\(FNUT\)\s*=\s*MAXF\(FNUT\)\s*\*\s*([\d.]+)\s*;", txt, re.M).group(1)
    dbl = re.search(r"set doubleMaxf\(PACT\)[^/]*/([^/]*)/", txt).group(1)
    return [(k, v, sc) for k, v in mx], [c.strip() for c in dbl.split(",") if c.strip()]


def nfix_rates(txt: str):
    """fert/fertpar.gms p_nfixRate_gras(RALL) and p_nitrFact("RALL", "GRAE", "BioFix") (the extraction of
    tools/lib/_capri_digest.py): ([(region, value text)], value text)."""
    m = re.search(r"PARAMETER p_nfixRate_gras\(RALL\)[^/]*/(.*?)/;", txt, re.S)
    rates = re.findall(r"(\w+)\s+([\d.]+)", m.group(1))
    g = re.search(r"RALL\.GRAE\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)", txt)
    return rates, g.group(1)


def input_demand_factors(txt: str):
    """inputs/yieldIY.gms TABLE p_inputDemandFactor: [(activity, input, value text)], each number under the column
    header nearest to it (the extraction of tools/build/build_plant_protection_cost.py)."""
    lines = txt.splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith("TABLE p_inputDemandFactor"))
    head, f = None, {}
    for l in lines[i0 + 1:]:
        if l.strip() == ";" or l.strip().startswith(";"):
            break
        if not l.strip() or l.lstrip().startswith("*"):
            continue
        if head is None:
            head = [(m.start(), m.group()) for m in re.finditer(r"[A-Z]+", l)]
            continue
        act = l.split()[0]
        for m in re.finditer(r"\d+\.?\d*", l[len(act):]):
            pos = m.start() + len(act)
            col = min(head, key=lambda h: abs(h[0] - pos))[1]      # the column header nearest the number
            f[(act, col)] = m.group()
    return [(a, c, v) for (a, c), v in f.items()]


def parse_minfert(text: str):
    """pol_input/greendeal/minfert_redu_by_crop.gms: the listed exemptions p_checkSmallMine(ru, NGRP) = factor x
    p_minfertBaseline and the limCres relaxations, each with its simulation-year condition (the parse of
    tools/build/build_mineral_redu_rules.py)."""
    year, oth, skip = [None], [False], False
    exm, lim = [], []
    stmt = ""
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("$ontext"):
            skip = True
            continue
        if low.startswith("$offtext"):
            skip = False
            continue
        if skip or line.startswith("*"):
            continue
        m = re.match(r"\$ifthene\.\S+\s+%simy%>(\d+)", line, re.I)
        if m:
            year.append(int(m.group(1)))
            continue
        if re.match(r"\$iftheni\.oth\S*\s+%othPol%==high", line, re.I):
            oth.append(True)
            continue
        m = re.match(r"\$endif\.(\S+)", line, re.I)
        if m:
            (oth if m.group(1).lower().startswith("oth") else year).pop()
            continue
        # limCres relaxations: $ife %simy%>YYYY  +.5 $ (sameas(ru,"X") $ sameas(ngrp,"Y"))
        m = re.match(r'\$ife\s+%simy%>(\d+)\s+\+\s*([0-9.]+)\s*\$\s*\(sameas\(ru,"([A-Z0-9]+)"\)\s*\$\s*sameas\(ngrp,"([A-Z]+)"\)\)',
                     line, re.I)
        if m:
            lim.append(dict(capri_region=m.group(3), ngrp=m.group(4), add=float(m.group(2)), after_year=int(m.group(1))))
            continue
        if line.startswith("p_checkSmallMine(ru,NGRP)") or stmt:
            stmt += " " + line
            if not stmt.rstrip().endswith(";"):
                continue
            s, stmt = stmt, ""
            r = re.search(r'sameas\(ru,"([A-Z0-9]+)"\)', s)
            if r is None:
                continue
            f = re.search(r"=\s*([0-9.]*)\s*\*?\s*p_minfertBaseline", s)
            fac = float(f.group(1)) if f and f.group(1) not in ("", ".") else 1.0
            for g in re.findall(r'sameas\(ngrp,"([A-Z]+)"\)', s, re.I):
                exm.append(dict(capri_region=r.group(1), ngrp=g.upper(), factor=fac,
                                after_year=year[-1] if year[-1] is not None else 0, othpol_high=int(oth[-1])))
    return pd.DataFrame(exm), pd.DataFrame(lim)


def _write_frame(rel: str, df: pd.DataFrame) -> None:
    """A parsed table as pandas writes it (floats as repr)."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    rows = list(csv.reader(io.StringIO(buf.getvalue())))
    write(rel, rows[0], rows[1:])


def convert_gams_code() -> None:
    txt = read_text(original("capri_gams/envind/gascoeff.gms"), "utf-8")
    write("capri_gams/envind/gascoeff_p_nutContCropOutput_STRA.csv", ["output", "nutrient", "value"],
          [("STRA", k, v) for k, v in straw_content(txt)])
    txt = read_text(original("capri_gams/fert/fertpar.gms"), "utf-8")
    maxf, dbl = need_bounds(txt)
    write("capri_gams/fert/fertpar_MAXF.csv", ["nutrient", "value", "multiplier"], maxf)
    write("capri_gams/fert/fertpar_doubleMaxf.csv", ["activity"], [(a,) for a in dbl])
    rates, grae = nfix_rates(txt)
    write("capri_gams/fert/fertpar_p_nfixRate_gras.csv", ["region", "value"], rates)
    write("capri_gams/fert/fertpar_p_nitrFact_RALL_GRAE_BioFix.csv", ["region", "activity", "factor", "value"],
          [("RALL", "GRAE", "BioFix", grae)])
    txt = read_text(original("capri_gams/inputs/yieldIY.gms"), "utf-8")
    write("capri_gams/inputs/yieldIY_p_inputDemandFactor.csv", ["activity", "input", "value"],
          input_demand_factors(txt))
    exm, lim = parse_minfert(read_text(original("policy/minfert_redu_by_crop.gms"), "utf-8"))
    _write_frame("policy/minfert_redu_by_crop_p_checkSmallMine.csv", exm)
    _write_frame("policy/minfert_redu_by_crop_limCres.csv", lim)


# --- Excel ---------------------------------------------------------------------------------------------------------

def _cell(v, strip: bool = False) -> str:
    """A cell as text: empty for none, an integral number without decimals, a float as repr."""
    if v is None:
        return ""
    if isinstance(v, float):
        v = int(v) if v.is_integer() else v
        v = repr(v) if isinstance(v, float) else str(v)
    v = str(v)
    return v.strip() if strip else v


def _sheets(rel: str):
    """{sheet name: rows (tuples of cell values)} of a workbook."""
    data = original(rel)
    if rel.endswith(".xls"):
        import xlrd
        wb = xlrd.open_workbook(file_contents=data)
        return {s.name: [tuple(None if c == "" else c for c in s.row_values(i)) for i in range(s.nrows)]
                for s in wb.sheets()}
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    return {ws.title: list(ws.iter_rows(values_only=True)) for ws in wb.worksheets}


def _named(rows, header_row: int, cols, key_cols, strip=False):
    """The rows after header_row with a value in one of key_cols (indices), the columns cols (indices) as text."""
    return [[_cell(r[c] if c < len(r) else None, strip) for c in cols] for r in rows[header_row + 1:]
            if any(c < len(r) and r[c] not in (None, "") for c in key_cols)]


def convert_excel() -> None:
    rows = _sheets("capri_star/nutrient_cont_usda_export.xlsx")["p_nutrientCont"]
    write("capri_star/nutrient_cont_usda_p_nutrientCont.csv", ["product", "item", "value"],
          [[_cell(v) for v in r] for r in rows])
    # NUTS 2013 -> 2016 (nuts2013_2016.csv as committed before)
    sh = _sheets("nuts/NUTS2013-NUTS2016__1_.xlsx")
    write("nuts/nuts2013_2016.csv", ["code_2013", "code_2016", "country", "level1", "level2", "level3", "change"],
          _named(sh["NUTS2013-NUTS2016"], 1, range(1, 8), (1, 2)), crlf=True)
    # NUTS 2021 (classification) and 2016 -> 2021 (nuts2016_2021.csv as committed before)
    sh = _sheets("nuts/NUTS2021.xlsx")
    write("nuts/nuts2016_2021.csv", ["code_2016", "code_2021", "country", "level1", "level2", "level3",
                                     "change_codes", "change_comments"],
          _named(sh["Changes detailed NUTS 2016-2021"], 0, range(8), (0, 1), strip=True), crlf=True)
    # NUTS 2024 (classification) and 2021 -> 2024 (nuts2024.csv and nuts2021_2024.csv as committed before)
    sh = _sheets("nuts/NUTS2021-NUTS2024.xlsx")
    write("nuts/nuts2024.csv", ["country", "code", "label", "level"], _named(sh["NUTS2024"], 0, range(4), (1,)),
          crlf=True)
    write("nuts/nuts2021_2024.csv", ["country", "code_2021", "code_2024", "level1", "level2", "level3", "change"],
          _named(sh["NUTS2021- NUTS2024"], 0, range(1, 8), (2, 3), strip=True), crlf=True)


# --- JSON ----------------------------------------------------------------------------------------------------------

def _json(rel: str):
    """A JSON file with its numbers as the text it writes them in."""
    return json.loads(original(rel).decode("utf-8"), parse_float=str, parse_int=str, parse_constant=str)


def _text(v) -> str:
    return "" if v is None else "true" if v is True else "false" if v is False else str(v)


def convert_json() -> None:
    d = _json("eu_tariff_provenance.json")
    rows = d["rows"]
    fields = []
    for v in rows.values():
        fields += [k for k in v if k not in fields]
    write("eu_tariff_provenance.csv", ["commodity"] + fields,
          [[c] + [_text(v.get(k)) for k in fields] for c, v in rows.items()])


def main() -> None:
    convert_gdxdumps()
    convert_gams_data()
    convert_gams_code()
    convert_excel()
    convert_json()


if __name__ == "__main__":
    main()

"""The inputs of the Aglink load's macro data p_aglinkMacro (baseline/load_aglink2023dgAgri.gms l. 905-1068; CAPTRD
reads its population in captrd/longrun_supports.gms l. 362-376), as CSV.

Sources (the project lead's CAPRI installation, docs/EXTERNAL_SOURCES.md):
  dat/baseline/aglink2023macro.xlsx      sheet for_gams, A2:D5600 (l. 913, 924): ctrCode, variable, year, value, the EU
                                         countries' Aglink macro data p_aglinkMacroEU; the rows of POP and GDPR kept
                                         (the two the file reads, l. 985-1001)
  dat/baseline/data_SSPV3_update.gdx     SSP_data (l. 959), converted by tools/build/convert_capri_gdx.py
                                         (dat_parquet/baseline/data_SSPV3_update/SSP_DATA): SSP2's population (IIASA)
                                         and GDP (OECD), the two the file reads (l. 965-1014)
  dat/global/reg_mappings.xlsx           Sheet1: GlobiomCountry (Y2:Y250, l. 931), GlobiomCountry_FAOreg (Y2:Z250,
                                         l. 939; with Taiwan.214, l. 943), FAOreg_AGLINKregions (R2:S250, l. 948) and
                                         ISO_FAOreg (U2:V250: the range of global/iso_to_fao_regions.gms's $CALL; GAMS
                                         loads ISO_FAOreg.gdx, written from it; with PSE.299, l. 23)
  dat/arm/allpop.gdx                     WorldPop(year, region) (captrd.gms l. 614: the UN population, the fallback of
                                         longrun_supports.gms l. 386-389), converted by convert_capri_gdx.py
                                         (dat_parquet/arm/allpop/worldPop)
Output: capri_data/pipeline/captrd/sets/macro/<set>.csv (d0, d1), capri_data/pipeline/captrd/dat/macro_p_aglinkmacroeu.csv,
macro_ssp_data.csv, macro_worldpop.csv.

    python tools/build/build_captrd_macro.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES                                  # noqa: E402

MACRO = SOURCES / "dat_local" / "baseline" / "aglink2023macro.xlsx"
MAPS = SOURCES / "dat_local" / "global" / "reg_mappings.xlsx"
SSP = SOURCES / "dat_parquet" / "baseline" / "data_SSPV3_update" / "SSP_DATA.parquet"
WPOP = SOURCES / "dat_parquet" / "arm" / "allpop" / "worldPop.parquet"
OUT_SETS = ROOT / "capri_data" / "pipeline" / "captrd" / "sets" / "macro"
OUT_DAT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
#: the macro variables the file reads (l. 985-1001: POP, GDPR; l. 965-968, 1007-1014: SSP POP of IIASA, GDP of OECD)
MACRO_VARS = ("POP", "GDPR")
SSP_KEEP = (("IIASA", "SSP2", "POP"), ("OECD", "SSP2", "GDP"))
#: Sheet1's columns (0-based) and rows (Y2:Z250 etc.)
COL_R, COL_S, COL_U, COL_V, COL_Y, COL_Z = 17, 18, 20, 21, 24, 25
FIRST_ROW, LAST_ROW = 2, 250
#: l. 943 and global/iso_to_fao_regions.gms l. 23: members the files add by hand
EXTRA_GLOBIOM_FAO = [("Taiwan", "214")]
EXTRA_ISO_FAO = [("PSE", "299")]


def _write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} records")


def _label(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def main() -> None:
    import openpyxl
    import pandas as pd
    wb = openpyxl.load_workbook(MACRO, read_only=True, data_only=True)
    rows = []
    for r in wb["for_gams"].iter_rows(min_row=2, max_row=5600, max_col=4, values_only=True):
        if r[0] and r[1] in MACRO_VARS and r[3] is not None and float(r[3]):
            rows.append((_label(r[0]), r[1], int(_label(r[2])), repr(float(r[3]))))
    _write(OUT_DAT / "macro_p_aglinkmacroeu.csv", ["ctrcode", "var", "year", "value"], rows)
    wb = openpyxl.load_workbook(MAPS, read_only=True, data_only=True)
    ws = wb["Sheet1"]
    one, two = {}, {"globiomcountry_faoreg": [], "faoreg_aglinkregions": [], "iso_faoreg": []}
    one["globiomcountry"] = []
    for r in ws.iter_rows(min_row=FIRST_ROW, max_row=LAST_ROW, values_only=True):
        y, z = _label(r[COL_Y]), _label(r[COL_Z])
        if y:
            one["globiomcountry"].append((y,))
            if z:
                two["globiomcountry_faoreg"].append((y, z))
        if _label(r[COL_R]) and _label(r[COL_S]):
            two["faoreg_aglinkregions"].append((_label(r[COL_R]), _label(r[COL_S])))
        if _label(r[COL_U]) and _label(r[COL_V]):
            two["iso_faoreg"].append((_label(r[COL_U]), _label(r[COL_V])))
    two["globiomcountry_faoreg"] += EXTRA_GLOBIOM_FAO
    two["iso_faoreg"] += EXTRA_ISO_FAO
    for n, m in one.items():                                   # a set holds each member once
        _write(OUT_SETS / f"{n}.csv", ["d0"], sorted(set(m), key=m.index))
    for n, m in two.items():
        _write(OUT_SETS / f"{n}.csv", ["d0", "d1"], sorted(set(m), key=m.index))
    d = pd.read_parquet(SSP)
    if d["special"].fillna("").ne("").any():
        raise ValueError(f"{SSP}: special values")
    keep = pd.Series(False, index=d.index)
    for a, b, c in SSP_KEEP:
        keep |= (d.d1 == a) & (d.d2 == b) & (d.d3 == c)
    d = d[keep]
    _write(OUT_DAT / "macro_ssp_data.csv", ["source", "ssp", "var", "country", "year", "value"],
           [(a, b, c, e, int(f), repr(float(v))) for a, b, c, e, f, v in zip(d.d1, d.d2, d.d3, d.d4, d.d5, d.value)])
    w = pd.read_parquet(WPOP)
    if w["special"].fillna("").ne("").any():
        raise ValueError(f"{WPOP}: special values")
    w = w[pd.to_numeric(w.d1, errors="coerce").notna()]
    _write(OUT_DAT / "macro_worldpop.csv", ["year", "region", "value"],
           [(int(y), r.upper(), repr(float(v))) for y, r, v in zip(w.d1, w.d2, w.value) if float(v)])


if __name__ == "__main__":
    main()

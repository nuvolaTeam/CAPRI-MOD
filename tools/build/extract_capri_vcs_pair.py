"""CAPRI's voluntary-coupled-support experiment, 2030: the reference and the run without VCS.

Two CAPRI capmod runs from the project lead's installation, identical settings (META compared:
only the scenario differs; both with the new manure trade module on):

  res_2_1730cap_after_2014_refdefaultA.gdx                                      cap_after_2014\\ref
  res_2_1730cap_after_2014_without_voluntary_coupled_support_0_1_MMOndefaultA   ...\\without_voluntary_coupled_support
      (pol_input/cap_after_2014/without_voluntary_coupled_support.gms: voluntaryCoupledSupportFile
       = void.gms, BPS convergence and greening as in the reference)

Kept, year 2030 (current prices, as CAPRI stores them):
  supply rows  (region, activity, item)  item in LEVL, PRME (PROD, YILD at EU and member-state level); regions EU27yr19, member
               states and NUTS2 (CAPRI 8-character codes)
  market rows  (region, product, item)   item in UVAP, UVAG, MAPR, HCON, IMPT, EXPT; EU27yr19 and
               member states (CAPRI stores them as region.''.item.product)

Output: capri_data/validation/coupled_support_2030/capri_vcs_effect.csv.xz
        (region, activity, item, ref, novcs, pct_change)

    python tools/build/extract_capri_vcs_pair.py REF.gdx NOVCS.csv [--lib-dir /home/claude/work/gdxlib]
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SUP_ITEMS = {"LEVL", "PRME", "PROD", "YILD"}
MKT_ITEMS = {"UVAP", "UVAG", "MAPR", "HCON", "IMPT", "EXPT"}
REG = re.compile(r"^(EU27yr19|[A-Z]{2}[0-9A-Z]{6})$")
EU_MS = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT",
         "LT", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}


def _keep(r, q, a, i):
    if q != "" or not REG.match(r) or not (r == "EU27yr19" or r[:2] in EU_MS):
        return None
    if i in SUP_ITEMS:
        # PROD and YILD at EU and member-state level only (NUTS2 rows unused; package size)
        if i in ("PROD", "YILD") and not (r == "EU27yr19" or r.endswith("000000")):
            return None
        return (r, a, i)
    if a in MKT_ITEMS and (r == "EU27yr19" or r.endswith("000000")):
        return (r, i, a)                     # market row: item and product swapped in CAPRI
    return None


def read_gdx(path, lib):
    from gams.core import gdx
    h = gdx.new_gdxHandle_tp()
    ok, msg = gdx.gdxCreateD(h, lib, gdx.GMS_SSSIZE)
    if not ok:
        raise SystemExit(msg)
    gdx.gdxOpenRead(h, str(path))
    _, idx = gdx.gdxFindSymbol(h, "dataOut")
    _, nrec = gdx.gdxDataReadStrStart(h, idx)
    out = {}
    for _ in range(nrec):
        ok, k, v, _ = gdx.gdxDataReadStr(h)
        if not ok:
            break
        if k[4] != "2030":
            continue
        key = _keep(k[0], k[1], k[2], k[3])
        if key:
            out[key] = float(v[gdx.GMS_VAL_LEVEL])
    gdx.gdxDataReadDone(h); gdx.gdxClose(h)
    return out


def read_dump(path):
    pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\.'2030'\s+([-0-9.Ee+]+)")
    out = {}
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                key = _keep(m.group(1), m.group(2), m.group(3), m.group(4))
                if key:
                    out[key] = float(m.group(5))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_gdx", type=Path)
    ap.add_argument("novcs_dump", type=Path)
    ap.add_argument("--lib-dir", default="/home/claude/work/gdxlib")
    a = ap.parse_args()
    ref = read_gdx(a.ref_gdx, a.lib_dir)
    nov = read_dump(a.novcs_dump)
    keys = sorted(set(ref) | set(nov))
    df = pd.DataFrame([(r, act, it, ref.get((r, act, it)), nov.get((r, act, it))) for (r, act, it) in keys],
                      columns=["region", "activity", "item", "ref", "novcs"])
    df["pct_change"] = 100.0 * (df["novcs"] / df["ref"] - 1.0)
    df.loc[~(df["ref"].abs() > 1e-9), "pct_change"] = float("nan")
    dest = ROOT / "capri_data" / "validation" / "coupled_support_2030"
    dest.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest / "capri_vcs_effect.csv.xz", index=False, float_format="%.6g")
    eu = df[(df.region == "EU27yr19") & (df.item == "LEVL")].set_index("activity")["pct_change"].dropna()
    print(f"wrote capri_vcs_effect.csv.xz: {len(df)} rows ({len(ref)} ref, {len(nov)} without VCS)")
    print("EU27 levels, % change:", eu.reindex(["DCOL", "DCOH", "SCOW", "BULL", "BULH", "HEIL", "HEIH", "SHGM", "SHGF",
                                               "SOYA", "PULS", "SUGB", "DWHE", "TOMA", "GRAS"]).round(1).dropna().to_dict())


if __name__ == "__main__":
    main()

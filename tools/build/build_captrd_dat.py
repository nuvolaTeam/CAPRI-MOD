"""CAPRI's data include files that CAPTRD reads, as CSV for CAPTRD-MOD.

Sources (CAPRI star 3.0 dat folder, from the project lead's installation, kept unchanged in
capri_data/sources/capri_dat/):
  policy/livestock_units.gms             p_LUUnits(act)              livestock units per head (prep_data_for_estimation
                                                                     .gms l. 160-162, the stocking density LU)
  biofuel/biofuel_technology_params.gms  p_ExtrRates(fuel, stock)    biofuel per ton of feedstock (load_coco1_data.gms
                                                                     l. 524-537, the default biostocks)
                                         p_ByProduct(byprod, stock)  by-product per ton of feedstock (l. 545-548, DDGS)
  coco/milk_quota_dat.gms                p_MQuotaDat(MS, info, year) milk quotas, deliveries and direct sales (DG AGRI)
  policy/smal_pshar.gms                  p_smallProdShare(year, MS)  small producers' share outside compulsory set-aside
and from CAPRI's code (capri_data/sources/capri_gams):
  pol_input/mquota_update.gms            PMQuotaReg(MS, QUTtot, year) total milk quotas 2004-2014 (1000 t)
  baseline/labour_ageline.gms            p_minLabourPerAct(act)      minimum labour per activity unit (h, 2008)
and CAPRI's sugar quota GDX input_load_sugar_quotas.gdx (capri_data/sources/capri_dat/sugar, README there):
  p_SQuotas, p_PPSQRenounce, p_PPSQCBuyBack (p_PPSQWithdraw: no records)
and CAPRI's farm holders' age lines dat/baseline/ageline.gdx AGELINE(region, age, year) from the parquet mirror of
CAPRI's dat folder (ageline.parquet: uni_0 region, uni_1 age, uni_2 year; the year label "ageline" kept as it is,
CAPTRD reads only the years of its YEARS set), read by baseline/labour_ageline.gms (captrd.gms l. 902)
CAPTRD includes livestock_units from policy/rd_static.gms or the policy sets, the biofuel parameters at captrd.gms
l. 340-341 (%NewBiofuelModule% = ON), the quota and set-aside data in captrd/captrd_policy.gms.

GAMS labels are case-insensitive: they are written in upper case ("BioE" is BIOE).

Output: capri_data/pipeline/captrd/dat/{p_luunits, p_extrrates, p_byproduct, p_mquotadat, p_mquotareg,
p_smallprodshare, p_squotas, p_ppsqrenounce, p_ppsqcbuyback, p_minlabourperact, ageline}.csv

    python tools/build/build_captrd_dat.py [--ageline AGELINE.parquet]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "capri_dat"
GAMS = ROOT / "capri_data" / "sources" / "capri_gams"
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
AGELINE = Path(os.environ.get("CAPRI_WORK", "/home/claude/work")) / "hf_capri" / "dat" / "baseline" / "ageline" / "ageline.parquet"


def parameter_list(path: Path, name: str, dim: int):
    """The records of `parameter name(...) "text" / k1.k2 value ... /;` (comment lines starting with * skipped)."""
    text = path.read_text(encoding="latin-1")
    m = re.search(rf"parameter\s+{name}\s*(?:\([^)]*\))?[^/]*/(.*?)/\s*;", text, flags=re.I | re.S)
    if not m:
        raise KeyError(f"{name} not in {path}")
    out = []
    for ln in m.group(1).splitlines():
        if not ln.strip() or ln.lstrip().startswith("*"):
            continue
        s = re.sub(r"\s*\.\s*", ".", ln.strip())           # "BioD .RAPO" -> "BioD.RAPO"
        parts = s.split()
        if len(parts) != 2:
            raise ValueError(f"{path}: {name}: unreadable line {ln!r}")
        keys = parts[0].upper().split(".")
        if len(keys) != dim:
            raise ValueError(f"{path}: {name}: {dim} keys expected in {ln!r}")
        out.append((*keys, float(parts[1])))
    if len({r[:-1] for r in out}) != len(out):
        raise ValueError(f"{path}: {name}: duplicate keys")
    return out


def table(path: Path, name: str, row_dims: int):
    """The records of `Table name(...) "text"` (GAMS table: a header line of column labels, then rows of a label of
    row_dims parts joined by dots and numbers in the columns they overlap). Returns (row keys..., column, value)."""
    lines = path.read_text(encoding="latin-1").splitlines()
    k = next(i for i, ln in enumerate(lines) if re.match(rf"\s*table\s+{name}\s*\(", ln, flags=re.I))
    i = k + 1
    while not lines[i].strip() or lines[i].lstrip().startswith("*"):
        i += 1
    head = lines[i]
    cols = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", head)]
    out = []
    for ln in lines[i + 1:]:
        s = ln.rstrip()
        if s.strip() == ";" or s.strip().endswith(";") and not re.search(r"\d", s):
            break
        if not s.strip() or s.lstrip().startswith("*"):
            continue
        toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", s)]
        label, j = "", 0
        while j < len(toks):
            label += toks[j][2]
            j += 1
            if label.count(".") >= row_dims - 1 and not label.endswith(".") and not (
                    j < len(toks) and toks[j][2].startswith(".")):
                break
        keys = [x.strip().upper() for x in label.split(".")]
        if len(keys) != row_dims:
            raise ValueError(f"{path}: {name}: unreadable row label in {ln!r}")
        for a, b, v in toks[j:]:
            ov = [(min(b, ce) - max(a, cs), cn) for cs, ce, cn in cols]
            best = max(ov)
            if best[0] <= 0:
                raise ValueError(f"{path}: {name}: value {v!r} under no column in {ln!r}")
            out.append((*keys, best[1].upper(), float(v)))
    return out


def _write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow((*r[:-1], repr(r[-1])))
    print(f"{name}.csv: {len(rows)} records")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ageline", type=Path, default=AGELINE)
    a = ap.parse_args()
    _write("p_luunits", ["act", "value"], parameter_list(SRC / "policy" / "livestock_units.gms", "p_LUUnits", 1))
    bio = SRC / "biofuel" / "biofuel_technology_params.gms"
    _write("p_extrrates", ["fuel", "stock", "value"], parameter_list(bio, "p_ExtrRates", 2))
    _write("p_byproduct", ["byproduct", "stock", "value"], parameter_list(bio, "p_ByProduct", 2))
    _write("p_mquotadat", ["region", "info", "year", "value"],
           table(SRC / "coco" / "milk_quota_dat.gms", "p_MQuotaDat", 2))
    _write("p_mquotareg", ["region", "info", "year", "value"],
           table(GAMS / "pol_input" / "mquota_update.gms", "PMQuotaReg", 2))
    _write("p_smallprodshare", ["year", "region", "value"],
           table(SRC / "policy" / "smal_pshar.gms", "p_smallProdShare", 1))
    for f, hdr in (("p_SQuotas", ["region", "quota", "year", "value"]), ("p_PPSQRenounce", ["region", "year", "value"]),
                   ("p_PPSQCBuyBack", ["region", "year", "value"])):
        with open(SRC / "sugar" / f"{f}.csv") as fh:
            rd = list(csv.reader(fh))
        if rd[0] != hdr:
            raise ValueError(f"{f}.csv: columns {rd[0]}, expected {hdr}")
        _write(f.lower(), hdr, [(*r[:-1], float(r[-1])) for r in rd[1:]])
    _write("p_minlabourperact", ["act", "value"],
           parameter_list(GAMS / "baseline" / "labour_ageline.gms", "p_minLabourPerAct", 1))
    import pandas as pd
    ag = pd.read_parquet(a.ageline)
    _write("ageline", ["region", "age", "year", "value"],
           [(str(r.uni_0).upper(), str(r.uni_1).upper(), str(r.uni_2).upper(), float(r.value))
            for r in ag.itertuples(index=False)])


if __name__ == "__main__":
    main()

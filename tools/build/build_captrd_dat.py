"""CAPRI's data include files that CAPTRD reads, as CSV for CAPTRD-MOD.

Sources (CAPRI star 3.0 dat folder, from the project lead's installation, converted to CSV by
tools/build/convert_sources_to_csv.py, capri_data/sources/capri_dat/):
  policy/livestock_units_p_LUUnits.csv   p_LUUnits(act)              livestock units per head (prep_data_for_estimation
                                                                     .gms l. 160-162, the stocking density LU)
  biofuel/biofuel_technology_params_p_ExtrRates.csv  p_ExtrRates(fuel, stock)  biofuel per ton of feedstock
                                         (load_coco1_data.gms l. 524-537, the default biostocks)
  biofuel/biofuel_technology_params_p_ByProduct.csv  p_ByProduct(byprod, stock)  by-product per ton of feedstock
                                         (l. 545-548, DDGS)
  coco/milk_quota_dat_p_MQuotaDat.csv    p_MQuotaDat(MS, info, year) milk quotas, deliveries and direct sales (DG AGRI)
  policy/smal_pshar_p_smallProdShare.csv p_smallProdShare(year, MS)  small producers' share outside compulsory set-aside
and from CAPRI's code (capri_data/sources/capri_gams, the same converter):
  pol_input/mquota_update_PMQuotaReg.csv PMQuotaReg(MS, QUTtot, year) total milk quotas 2004-2014 (1000 t)
  baseline/labour_ageline_p_minLabourPerAct.csv  p_minLabourPerAct(act)  minimum labour per activity unit (h, 2008)
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "capri_dat"
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"
AGELINE = Path(os.environ.get("CAPRI_WORK", "/home/claude/work")) / "hf_capri" / "dat" / "baseline" / "ageline" / "ageline.parquet"


def _records(rel: str, cols, upper: int):
    """The records of a converted source (capri_data/sources/<rel>, tools/build/convert_sources_to_csv.py): the
    first `upper` columns upper-cased (GAMS labels are case-insensitive), the value as float."""
    with open(ROOT / "capri_data" / "sources" / rel, newline="", encoding="utf-8") as fh:
        rd = list(csv.reader(fh))
    if rd[0] != cols:
        raise ValueError(f"{rel}: columns {rd[0]}, expected {cols}")
    return [(*(k.upper() for k in r[:upper]), *r[upper:-1], float(r[-1])) for r in rd[1:]]


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
    _write("p_luunits", ["act", "value"],
           _records("capri_dat/policy/livestock_units_p_LUUnits.csv", ["act", "value"], 1))
    bio = "capri_dat/biofuel/biofuel_technology_params_"
    _write("p_extrrates", ["fuel", "stock", "value"], _records(bio + "p_ExtrRates.csv", ["fuel", "stock", "value"], 2))
    _write("p_byproduct", ["byproduct", "stock", "value"],
           _records(bio + "p_ByProduct.csv", ["byproduct", "stock", "value"], 2))
    _write("p_mquotadat", ["region", "info", "year", "value"],
           _records("capri_dat/coco/milk_quota_dat_p_MQuotaDat.csv", ["region", "info", "year", "value"], 3))
    _write("p_mquotareg", ["region", "info", "year", "value"],
           _records("capri_gams/pol_input/mquota_update_PMQuotaReg.csv", ["region", "info", "year", "value"], 3))
    _write("p_smallprodshare", ["year", "region", "value"],
           _records("capri_dat/policy/smal_pshar_p_smallProdShare.csv", ["year", "region", "value"], 2))
    for f, hdr in (("p_SQuotas", ["region", "quota", "year", "value"]), ("p_PPSQRenounce", ["region", "year", "value"]),
                   ("p_PPSQCBuyBack", ["region", "year", "value"])):
        with open(SRC / "sugar" / f"{f}.csv") as fh:
            rd = list(csv.reader(fh))
        if rd[0] != hdr:
            raise ValueError(f"{f}.csv: columns {rd[0]}, expected {hdr}")
        _write(f.lower(), hdr, [(*r[:-1], float(r[-1])) for r in rd[1:]])
    _write("p_minlabourperact", ["act", "value"],
           _records("capri_gams/baseline/labour_ageline_p_minLabourPerAct.csv", ["act", "value"], 1))
    import pandas as pd
    ag = pd.read_parquet(a.ageline)
    _write("ageline", ["region", "age", "year", "value"],
           [(str(r.uni_0).upper(), str(r.uni_1).upper(), str(r.uni_2).upper(), float(r.value))
            for r in ag.itertuples(index=False)])


if __name__ == "__main__":
    main()

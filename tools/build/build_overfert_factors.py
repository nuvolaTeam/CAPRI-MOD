"""CAPRI's over-fertilisation factor per region (v_cropNutNeedMultFact, NITF, "T").

Source: CAPRI's fertiliser-distribution results, results\\fert\\priFertDist_<MS>1730*.gdx,
symbol p_CropNutNeedMultFact(ru, FNUT, A, year), dumped with gdxdump to text, e.g.

    for %f in (priFertDist_*1730*.gdx) do gdxdump "%f" symb=p_CropNutNeedMultFact >> multfact_1730.txt

In simulation CAPRI fixes v_cropNutNeedMultFact at p_cropNutNeedMultFact(ru, FNUT, A,
fertDistPriorYear = simulation year) (capmod/load_fert_baseline.gms, supply/prep_sim.gms).
It bounds the fertiliser-efficiency technologies (envind/ghgMiti.gms with restMitFert on,
p_OverFertMarkUp = 0.1; supply/supply_model.gms Tot_MitFert_):
    1 + sum_t share_t x NMIN_t <= max(x + 0.1, 1)
and lowers each option's maximum share where crop need lies above precision farming's level.

Output: capri_data/2017/environment/crop_nut_need_mult_fact_2030.csv
        (region = model NUTS 2 code, capri_region, x); model regions without a regional CAPRI
        entry take their country's value (the model's registered national fallback).
Usage:  python tools/build/build_overfert_factors.py <dump file> [<dump file> ...] [--year 2030]
"""
import argparse
import csv
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "2017" / "environment" / "crop_nut_need_mult_fact_2030.csv"
LINE = re.compile(r"^\s*'([^']+)'\.'([^']+)'\.'([^']+)'\.'([^']+)'\s+([-+0-9.eE]+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--year", default="2030")
    a = ap.parse_args()
    x = {}
    for f in a.dumps:
        for line in open(f, encoding="latin-1"):
            m = LINE.match(line)
            if m and m.group(2).upper() == "NITF" and m.group(3).upper() == "T" and m.group(4) == a.year:
                x[m.group(1)] = float(m.group(5))
    if not x:
        raise SystemExit("no p_CropNutNeedMultFact(ru,'NITF','T','%s') records found" % a.year)
    c8 = json.load(open(ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    rows, have = [], set()
    for r8, nuts in c8.items():
        if r8 in x and not r8.endswith("000000"):
            for n2 in nuts:
                rows.append([n2, r8, x[r8]]); have.add(n2)
    for reg in mr.model_regions():
        if reg in have:
            continue
        nc = mr.national_code(reg)
        if nc in x:                               # national entry (single-region country or fallback)
            rows.append([reg, nc, x[nc]]); have.add(reg)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["region", "capri_region", "x"]); w.writerows(sorted(rows))
    vals = [r[2] for r in rows]
    print(f"{len(x)} CAPRI codes read; {len(rows)} model regions written to {OUT.name}; "
          f"x median {sorted(vals)[len(vals) // 2]:.3f}, min {min(vals):.3f}, max {max(vals):.3f}; "
          f"x + 0.1 <= 1 (no technology saving allowed) in {sum(1 for v in vals if v + 0.1 <= 1)} regions")


if __name__ == "__main__":
    main()

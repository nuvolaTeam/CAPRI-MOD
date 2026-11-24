"""CAPRI's 2030 final-product output per model head, per model region, animal and product (register DEP-13, step 2):
the quantities the model's animals produce at the 2030 market year.

CAPRI's simulation reads each animal activity's outputs of the simulation year per unit of its level, DATA(r, act,
COMI | BEEF | PORK | POUM | EGGS | SGMT | SGMI, "Y") (sim_ini_21730; the 2030 baseline the model's 2030 base is taken
from, res_2_1730greendeal_refdefaulta, reports the same values in dataOut at 2030: tools/lib/paths.BASELINE_REF), and
its supply model multiplies them by the activity levels. The model took the 2017 quantities per head x f, the
projected over the base yield of the animal (capri_mod/projection/projection_module.py _project_livestock; the dairy
cows' cull beef unchanged): exact for an animal's main output (milk, the fattening pigs' pork), not for its second
outputs (the dairy cows' cull beef, the sows' pork) nor for the cattle's beef, whose 2030 yield is not its beef per
head (2030 base totals against CAPRI's at the median: dairy cows' beef 1.000, 10-90% 0.955-1.051; bulls' 1.000,
0.937-1.089; suckler cows' 1.013, 0.924-1.066; sows' pork 1.049, 0.976-1.128; 23 November 2026).

As the 2017 coefficients (tools/build/build_livestock_output_coef.py build_product_quantities): CAPRI's regional total
of each final product (LEVL x item, summed over CAPRI's activities of the model animal, kt) over the model's head count
of the animal, per territory group (build_livestock_output_coef.per_head, the member state's row where a model region
has no regional row); here CAPRI's 2030 levels and outputs over the model's 2030 base heads (the 2017 heads x the 2030
reference trajectory's herd factor, as the projection projects them: tools/build/build_young_animals_2030.herds_2030),
as the manure coefficients of 2030 (tools/build/build_livestock_manure_2030.py, K179). So the model's 2030 base
production of each product is CAPRI's 2030 production. CAPRI's activities: DCOL, DCOH (dairy cows), SCOW (suckler
cows), BULL, BULH (bulls), HEIL, HEIH, HEIR (heifers), CAMF, CAFF, CAMR, CAFR (calves), SOWS, PIGF, HENS, POUF, SHGM,
SHGF; DCOW, BULF and HEIF are the sums of their intensity variants in dataOut and are not read.

Output (as the 2017 file livestock_output_by_product_coef.csv: model region x "ANIMAL.PRODUCT", kt per 1000 head;
empty where the model has no such animal or CAPRI no such output)
  capri_data/baselines/capri_greendeal_ref/1730/supply/livestock_output_by_product_coef_2030.csv

    python tools/build/build_livestock_output_2030.py [--ref ZIP]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "livestock_output_by_product_coef_2030.csv"
#: CAPRI's 2030 animal activities -> the model's animals (as tools/build/build_livestock_manure_2030.MAP)
MAP = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
       "HEIL": "HFRS", "HEIH": "HFRS", "HEIR": "HFRS", "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
       "SOWS": "PIGS", "PIGF": "PIGF", "HENS": "LAYS", "POUF": "BROI", "SHGM": "SHGM", "SHGF": "SHGF"}
_ROW = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z_]+)'\.'2030'\s+([^,\s]+)")


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "build" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _num(tok: str) -> float:
    t = tok.strip().upper()
    return 0.0 if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF") else float(tok)


def capri_2030(ref: Path, products) -> dict:
    """{(CAPRI region, model animal, product): sum over the animal's CAPRI activities of LEVL x DATA(product), kt} of
    the 2030 baseline's dataOut (LEVL in 1000 head, the products in kg per head; poultry per 1000 head in million head,
    the same product)."""
    acts = "|".join(MAP)
    txt = grep(rf"^'[A-Z]{{2}}[A-Z0-9]{{6}}'\.''\.'({acts})'\.'(LEVL|{'|'.join(products)})'\.'2030'", str(ref))
    v = defaultdict(dict)
    for line in txt.splitlines():
        m = _ROW.match(line)
        if m:
            v[(m.group(1), m.group(2))][m.group(3)] = _num(m.group(4))
    totals = defaultdict(float)
    for (r, a), d in v.items():
        lv = d.get("LEVL", 0.0)
        for p in products:
            if lv and d.get(p):
                totals[(r, MAP[a], p)] += lv * d[p] / 1000.0
    return totals


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", type=Path, default=BASELINE_REF, help="CAPRI's 2030 baseline (dataOut listing, zip)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    B = _tool("build_livestock_output_coef")
    Y = _tool("build_young_animals_2030")
    products = B.FINAL_PRODUCTS
    totals = capri_2030(args.ref, products)
    herds = Y.herds_2030()
    cols = {}
    for p in products:
        coef = B.per_head({(r, a): x for (r, a, p_), x in totals.items() if p_ == p}, herds)
        for a in coef.columns:
            if coef[a].fillna(0.0).abs().sum() > 0:
                cols[f"{a}.{p}"] = coef[a]
    out = pd.DataFrame(cols).sort_index(axis=1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out)
    # check: the model's 2030 base heads x the coefficients against CAPRI's 2030 production, per member state and
    # product (CAPRI's member-state row where it has one, else the sum of its regional rows)
    worst, n = 0.0, 0
    for col in out.columns:
        a, p = col.split(".", 1)
        for ms in sorted({r[:2] for r in out.index}):
            regs = [r for r in out.index if r[:2] == ms]
            mod = sum(float(herds.at[r, a]) * float(out.at[r, col]) for r in regs
                      if a in herds.columns and out.at[r, col] == out.at[r, col])
            nat = totals.get((f"{ms}000000", a, p))
            if nat is None:
                nat = sum(x for (r_, a_, p_), x in totals.items() if r_[:2] == ms and not r_.endswith("000000")
                          and a_ == a and p_ == p)
            if nat and nat > 1e-6:
                worst, n = max(worst, abs(mod / nat - 1.0)), n + 1
    print(f"wrote {args.out}: {out.notna().sum().sum()} coefficients in {len(out.columns)} columns; the model's 2030 "
          f"heads x coefficient against CAPRI's 2030 production of {n} member state x product cells: worst {worst:.2e}")


if __name__ == "__main__":
    main()

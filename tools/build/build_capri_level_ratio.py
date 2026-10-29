"""Model herd units per unit of CAPRI's activity level (LEVL), per model region and animal (K27).

CAPRI's bounds on activity levels (supply/set_supply_bounds.gms) are UP = max(10 x level, level + 100), with the
level and the 100 in CAPRI's units (LEVL: 1000 head of the activity; poultry in million). The model's animal
activities are census herds (animal_numbers.csv), whose units differ from CAPRI's LEVL several-fold for some animals
(fattening sheep SHGF: CAPRI's LEVL counts fattened lambs, the model's herd the census stock; poultry: thousand head
against CAPRI's million; bulls and heifers). The additive 100 is converted with this ratio:

    ratio(region, animal) = model base herd / CAPRI 2017 LEVL of the animal's CAPRI activities

per group of CAPRI and model regions covering the same territory (tools/lib/_model_regions.py), the member state's ratio
where the group has no regional CAPRI rows. Activities map as in tools/build/build_livestock_output_coef.py.

Source: CAPRI's 2017 results res_17<MS> (LEVL); the model's herds as loaded (animal_numbers.csv, poultry in thousand head).
Output: capri_data/2017/supply/capri_level_ratio.csv (region x animal)

    python tools/build/build_capri_level_ratio.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from build_livestock_output_coef import CAPRI_TO_MODEL
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9]{4})'\.'LEVL'\.'Y'\s+([-\d.Ee+]+)")
    lev = defaultdict(float)                                  # (CAPRI code, model animal) -> LEVL
    for p in sorted(glob.glob(str(a.dump_dir / "res_17*.txt"))):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m and m.group(2) in CAPRI_TO_MODEL:
                lev[(m.group(1), CAPRI_TO_MODEL[m.group(2)])] += float(m.group(3))
    # the herds as the model loads them (poultry converted to thousand head, loaders._reconcile_poultry_units)
    sys.path.insert(0, str(ROOT))
    # only the herds' loader (the same table as load_all_data's, checked 29 October 2026): the whole data load made this
    # builder read about 80 model inputs, its own output and the yields among them (a cycle in the data pipeline)
    from capri_mod.data.loaders import load_regional_animal_numbers
    herds = load_regional_animal_numbers(str(ROOT / "capri_data"))
    animals = sorted(set(CAPRI_TO_MODEL.values()) & set(herds.columns))
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    _c2g, groups = mr.capri_groups(list(herds.index))
    out = pd.DataFrame(float("nan"), index=herds.index, columns=animals)
    src = defaultdict(int)
    for codes, regs in groups.values():
        regs = [r for r in regs if r in herds.index]
        for an in animals:
            L = sum(lev.get((c, an), 0.0) for c in codes if mr.regional_row(c))
            H = float(herds.loc[regs, an].fillna(0.0).sum())
            if L > 0 and H > 0:
                for r in regs:
                    out.at[r, an] = H / L
                src["regional"] += 1
    for r in herds.index:
        nat = mr.national_code(r)
        regs = [x for x in herds.index if mr.national_code(x) == nat]
        for an in animals:
            if pd.isna(out.at[r, an]):
                L = lev.get((nat, an), 0.0)
                H = float(herds.loc[regs, an].fillna(0.0).sum())
                if L > 0 and H > 0:
                    out.at[r, an] = H / L
                    src["national"] += 1
    dest = ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv"
    out.to_csv(dest)
    print(f"wrote {dest.relative_to(ROOT)}: {dict(src)}; median ratio "
          + ", ".join(f"{an} {out[an].median():.3g}" for an in animals))


if __name__ == "__main__":
    main()

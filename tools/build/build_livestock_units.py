"""CAPRI's livestock units per model head (capri_data/2017/supply/livestock_units.csv), for reporting adoption shares
weighted as CAPRI reports them (its Table 17-type shares weight the herds by livestock units, LEVW; e.g. envind/
RedLvst.gms l. 163-171 uses sum(maact, data(ru, maact, "levw", "y"))).

Per model region and animal: CAPRI's LEVW over its LEVL summed over the animal's CAPRI members (2017 results, res_17*
dumps, item 'Y'; regional row, else the national one), divided by capri_level_ratio (model heads per CAPRI level
unit), so model heads x lu_per_head = CAPRI's livestock units. Output: region x animal, as capri_level_ratio.csv. Members as tools/build/build_labour_setaside.py.

    python tools/build/build_livestock_units.py
"""
from __future__ import annotations

import glob
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DUMPS = Path("/home/claude/work/capreg")
ANIMALS = {"DCOW": ("DCOL", "DCOH"), "BCOW": ("SCOW",), "BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR"),
           "CALV": ("CAMF", "CAFF", "CAMR", "CAFR"), "PIGS": ("SOWS",), "PIGF": ("PIGF",), "LAYS": ("HENS",),
           "BROI": ("POUF",), "SHGM": ("SHGM",), "SHGF": ("SHGF",), "OANI": ("OANI",)}
ACTS = {c for v in ANIMALS.values() for c in v}


def main() -> None:
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(LEVL|LEVW)'\.'Y'\s+([-\d.Ee+]+)")
    d = defaultdict(dict)
    for f in glob.glob(str(DUMPS / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m and m.group(2) in ACTS:
                d[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    ratio = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0)
    rows = []
    for reg in mr.model_regions():
        for an, mem in ANIMALS.items():
            for c in (to_c8.get(reg), mr.national_code(reg)):
                if not c or c not in d:
                    continue
                L = sum(d[c].get((x, "LEVL"), 0.0) for x in mem)
                W = sum(d[c].get((x, "LEVW"), 0.0) for x in mem)
                if L > 0 and W > 0:
                    r_ = ratio.at[reg, an] if reg in ratio.index and an in ratio.columns else None
                    if r_ is not None and r_ == r_ and float(r_) > 0:
                        rows.append(dict(region=reg, animal=an, lu_per_head=W / L / float(r_), capri_region=c))
                    break
    out = pd.DataFrame(rows)
    # region x animal, as capri_level_ratio.csv (empty: no CAPRI herd in the region or its member state)
    wide = out.pivot(index="region", columns="animal", values="lu_per_head").sort_index()
    wide.index.name = None
    wide.to_csv(ROOT / "capri_data" / "2017" / "supply" / "livestock_units.csv", float_format="%.6g")
    nat = int((out.capri_region.str[2:] == "000000").sum())
    print(f"livestock_units.csv: {wide.shape[0]} regions x {wide.shape[1]} animals, {len(out)} values "
          f"({nat} from the member-state row); median LU per model head "
          f"{out.groupby('animal').lu_per_head.median().round(3).to_dict()}")


if __name__ == "__main__":
    main()

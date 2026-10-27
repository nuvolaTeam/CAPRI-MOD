"""CAPRI's animal yields per model head: the animal columns of capri_data/2017/supply/yields.csv.

Per model region and animal: CAPRI's YILD level-weighted over the animal's CAPRI members (2017 results, res_17* dumps,
item 'Y'; the region's row, else its member state's, as tools/build/build_livestock_units.py), divided by 1000 and by
capri_level_ratio (model heads per CAPRI level unit), so the value is CAPRI's YILD per model head in thousands of
CAPRI's unit: t of milk per dairy cow, t of meat per fattened animal; for sows (piglets) and hens (eggs) CAPRI's own
output unit / 1000. Members as tools/build/build_livestock_units.py.

Until 23 October 2026 the animal columns held values from an earlier extraction in two unit clusters (kg and t per
head), and the loader rescaled the smaller cluster by the ratio of the two medians (loaders._reconcile_animal_yield_units,
removed with this builder: PROXY_AUDIT S269).

    python tools/build/build_animal_yields.py [--check]
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DUMPS = Path("/home/claude/work/capreg")
YIELDS = ROOT / "capri_data" / "2017" / "supply" / "yields.csv"
ANIMALS = {"DCOW": ("DCOL", "DCOH"), "BCOW": ("SCOW",), "BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR"),
           "CALV": ("CAMF", "CAFF", "CAMR", "CAFR"), "PIGS": ("SOWS",), "PIGF": ("PIGF",), "LAYS": ("HENS",),
           "BROI": ("POUF",), "SHGM": ("SHGM",), "SHGF": ("SHGF",), "OANI": ("OANI",)}
ACTS = {c for v in ANIMALS.values() for c in v}


def read() -> dict:
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'(LEVL|YILD)'\.'Y'\s+([-\d.Ee+]+)")
    d = defaultdict(dict)
    for f in glob.glob(str(DUMPS / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m and m.group(2) in ACTS:
                d[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return d


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = read()
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    ratio = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0)
    rows = []
    for reg in mr.model_regions():
        for an, mem in ANIMALS.items():
            for c in (to_c8.get(reg), mr.national_code(reg)):
                if not c or c not in d:
                    continue
                L = sum(d[c].get((x, "LEVL"), 0.0) for x in mem)
                Y = sum(d[c].get((x, "LEVL"), 0.0) * d[c].get((x, "YILD"), 0.0) for x in mem)
                if L > 0 and Y > 0:
                    r_ = ratio.at[reg, an] if reg in ratio.index and an in ratio.columns else 1.0
                    r_ = float(r_) if r_ == r_ and float(r_) > 0 else 1.0       # OANI: no ratio column, CAPRI's unit
                    rows.append(dict(region=reg, animal=an, yild=Y / L / 1000.0 / r_, capri_region=c))
                    break
    out = pd.DataFrame(rows)
    wide = out.pivot(index="region", columns="animal", values="yild")
    return wide, out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with the animal columns now in yields.csv, write nothing")
    a = ap.parse_args()
    wide, out = build()
    y = _read_csv(YIELDS, index_col=0)
    cols = [c for c in ANIMALS if c in y.columns]
    if a.check:
        for c in cols:
            old = y[c]; new = wide[c].reindex(y.index) if c in wide.columns else pd.Series(float("nan"), index=y.index)
            m = (old > 0) & (new > 0)
            r = (old[m] / new[m])
            print(f"{c}: {int(m.sum())} cells, old/new ratio median {r.median():.4g} (min {r.min():.4g}, max {r.max():.4g}); "
                  f"old>0 & new missing {int(((old > 0) & ~(new > 0)).sum())}, new>0 & old 0 {int((~(old > 0) & (new > 0)).sum())}")
        return
    # the other columns are written back as read (text), so a parse/format round trip cannot move their last digit
    ys = _read_csv(YIELDS, index_col=0, dtype=str, keep_default_na=False)
    for c in cols:
        v = wide[c].reindex(ys.index).fillna(0.0) if c in wide.columns else pd.Series(0.0, index=ys.index)
        ys[c] = [repr(float(x)) for x in v]
    ys.to_csv(YIELDS)
    nat = int((out.capri_region.str[2:] == "000000").sum())
    print(f"yields.csv: animal columns {cols} rebuilt from CAPRI YILD, {len(out)} values ({nat} from the member-state row)")


if __name__ == "__main__":
    main()

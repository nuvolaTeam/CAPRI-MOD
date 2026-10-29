"""CAPRI's two sheep-and-goat activities, SHGM (milk) and SHGF (fattening): their input cost per head and their EU
producer prices, the columns and rows no other builder writes.

Kept from tools/build/build_shg_split.py (the one-time split of the census SHGO into SHGM and SHGF, October 2026),
retired on 29 October 2026: its herd split and its reruns of other builders had nothing left to do (a rebuild of the
chain without it reproduced every file), but these two computations were the only writers of their cells. Their method
is unchanged:

  capri_data/2017/supply/variable_costs.csv   SHGM, SHGF: CAPRI's TOIN level-weighted over the region's CAPRI group
      (tools/lib/_model_regions.capri_groups; the member state's row where the group has no regional rows), 2017
      results (res_17*.txt dumps, item 'Y'); the other columns written back as read
  capri_data/2017/market/producer_prices.csv  rows SHGM, SHGF: CAPREG's regional producer prices
      (sources/capreg/capreg_producer_prices.csv) herd-weighted over the units (animal_numbers.csv); the other rows
      written back as read

To be merged into the tables' single owners (docs/design/DATA_PIPELINE_DOIT.md, one writer per table).

    python tools/build/build_sheep_goat_inputs.py [--dump-dir /home/claude/work/capreg]
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
S = ROOT / "capri_data" / "2017" / "supply"


def costs(dump: Path):
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    v = defaultdict(dict)
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'(SHGM|SHGF)'\.'(LEVL|YILD|TOIN)'\.'Y'\s+([-\d.Ee+]+)")
    for p in sorted(glob.glob(str(dump / "res_17*.txt"))):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                v[(m.group(1), m.group(2))][m.group(3)] = float(m.group(4))
    herds = _read_csv(S / "animal_numbers.csv", index_col=0)
    _c2g, groups = mr.capri_groups(list(herds.index))

    def weighted(codes, act, item):
        num = den = 0.0
        for c in codes:
            d = v.get((c, act), {})
            if d.get("LEVL", 0) > 0:                     # an absent item is 0 (GAMS): milk sheep without milk
                num += d["LEVL"] * d.get(item, 0.0); den += d["LEVL"]
        return num / den if den > 0 else None

    t = _read_csv(S / "variable_costs.csv", index_col=0)
    for act in ("SHGM", "SHGF"):
        col = pd.Series(float("nan"), index=t.index)
        for codes, regs in groups.values():
            x = weighted([c for c in codes if mr.regional_row(c)], act, "TOIN")
            if x is not None:
                for r in regs:
                    if r in col.index:
                        col[r] = x
        for r in col.index[col.isna()]:
            x = weighted([mr.national_code(r)], act, "TOIN")
            if x is not None:
                col[r] = x
        t[act] = col
    t.to_csv(S / "variable_costs.csv")
    print(f"variable_costs.csv: SHGM median {t['SHGM'].median():.2f}, SHGF median {t['SHGF'].median():.2f} (TOIN)")
    return herds


def prices(herds):
    pp = _read_csv(ROOT / "capri_data" / "2017" / "market" / "producer_prices.csv", index_col=0)
    cp = _read_csv(ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv", index_col=0)
    for act in ("SHGM", "SHGF"):
        w = herds[act].reindex(cp.index).fillna(0.0)
        x = cp[act].where(cp[act] > 0)
        ok = x.notna() & (w > 0)
        pp.loc[act, pp.columns[0]] = float((x[ok] * w[ok]).sum() / w[ok].sum())
    pp.to_csv(ROOT / "capri_data" / "2017" / "market" / "producer_prices.csv")
    print("producer_prices.csv:", pp.loc[["SHGM", "SHGF"]].iloc[:, 0].to_dict())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    a = ap.parse_args()
    prices(costs(Path(a.dump_dir)))


if __name__ == "__main__":
    main()

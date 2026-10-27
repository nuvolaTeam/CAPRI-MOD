"""Compare a region-keyed data file rebuilt on CAPRI's regional units with the same file on the old NUTS-2016 regions.

For the regions whose CAPRI unit was theirs alone (relation one-to-one in the old shared/region_capri_map.csv: a rename
or the same code), the rebuilt row under the CAPRI code must equal the old row: the builders read the same CAPRI row.
Rows of split, merged or national regions are listed separately (their old values were shares or copies of the CAPRI
unit's; the new values are the unit's own). Columns the new file lacks or leaves empty where the old one had a value
are reported.

    python tools/check/compare_rekeyed.py capri_data/2017/supply/yields.csv [--old-ref next] [--tol 1e-9]
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def old_frame(path: str, ref: str, **kw) -> pd.DataFrame:
    txt = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(txt), float_precision="round_trip", **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--old-ref", default="next")
    ap.add_argument("--tol", type=float, default=1e-9, help="relative tolerance for 'equal'")
    ap.add_argument("--index-col", default="0", help="index column(s), comma-separated positions or names")
    a = ap.parse_args()
    ic = [int(x) if x.isdigit() else x for x in a.index_col.split(",")]
    ic = ic[0] if len(ic) == 1 else ic
    old = old_frame(a.path, a.old_ref, index_col=ic)
    new = pd.read_csv(ROOT / a.path, index_col=ic, float_precision="round_trip")
    rmap = old_frame("capri_data/shared/region_capri_map.csv", a.old_ref, dtype=str).fillna("")
    one = {r.region: r.capri_region for r in rmap.itertuples() if r.relation == "one-to-one"}
    lvl = 0 if not isinstance(old.index, pd.MultiIndex) else 0

    def region_of(ix):
        return ix if not isinstance(ix, tuple) else ix[lvl]

    def rekey(ix):
        if isinstance(ix, tuple):
            return (one.get(ix[0], None),) + ix[1:]
        return one.get(ix, None)

    o = old.copy()
    o.index = [rekey(i) for i in old.index]
    o = o[[i is not None and (not isinstance(i, tuple) or i[0] is not None) for i in o.index]]
    if isinstance(old.index, pd.MultiIndex):
        o.index = pd.MultiIndex.from_tuples(o.index, names=old.index.names)
    cols = [c for c in o.columns if c in new.columns]
    miss_cols = [c for c in o.columns if c not in new.columns]
    common = o.index.intersection(new.index)
    print(f"{a.path}: old {old.shape}, new {new.shape}; one-to-one rows compared {len(common)} of {len(o)}")
    if miss_cols:
        print(f"  columns missing in the new file: {miss_cols}")
    num = [c for c in cols if pd.api.types.is_numeric_dtype(o[c]) and pd.api.types.is_numeric_dtype(new[c])]
    oth = [c for c in cols if c not in num]
    bad = 0
    for c in num:
        x = o.loc[common, c].astype(float)
        y = new.loc[common, c].astype(float)
        lost = x.notna() & y.isna()
        both = x.notna() & y.notna()
        d = (x[both] - y[both]).abs() / np.maximum(x[both].abs(), 1e-12)
        nd = int((d > a.tol).sum())
        if lost.any() or nd:
            bad += 1
            worst = d.idxmax() if len(d) else None
            print(f"  {c}: {nd} differ (max rel {float(d.max()) if len(d) else 0:.3g} at {worst}: "
                  f"{x.get(worst)} -> {y.get(worst)}), {int(lost.sum())} lost {list(x.index[lost])[:5]}")
    for c in oth:
        x, y = o.loc[common, c].astype(str), new.loc[common, c].astype(str)
        nd = int((x != y).sum())
        if nd:
            bad += 1
            print(f"  {c} (text): {nd} differ, e.g. {list(zip(x[x != y][:3], y[x != y][:3]))}")
    print(f"  {len(num) + len(oth) - bad} of {len(num) + len(oth)} columns equal on the one-to-one rows")
    rest = sorted({region_of(i) for i in old.index} - set(one))
    print(f"  old regions not one-to-one ({len(rest)}): {rest}")
    newr = sorted({region_of(i) for i in new.index} - set(one.values()))
    print(f"  new units without a one-to-one old region ({len(newr)}): {newr}")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)

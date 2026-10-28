"""Print a Parquet table as text, or the difference of two.

    python tools/check/show_table.py FILE.parquet                 the table as CSV, full precision (git textconv)
    python tools/check/show_table.py OLD.parquet NEW.parquet      cells that differ: index, column, old, new

For readable git diffs of Parquet files (.gitattributes declares `*.parquet diff=parquet`), once per clone:

    git config diff.parquet.textconv "python tools/check/show_table.py"

Floats are printed with repr (the shortest text that reads back exactly), so a change in the last digit shows.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd


def _text(df: pd.DataFrame) -> str:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].map(lambda v: "" if pd.isna(v) else repr(float(v)))
    return out.to_csv()


def _diff(a: pd.DataFrame, b: pd.DataFrame) -> str:
    lines = []
    if list(a.columns) != list(b.columns):
        lines.append(f"columns: -{sorted(set(a.columns) - set(b.columns))} +{sorted(set(b.columns) - set(a.columns))}")
    gone, new = a.index.difference(b.index), b.index.difference(a.index)
    if len(gone) or len(new):
        lines.append(f"rows: -{list(gone)[:20]} +{list(new)[:20]}")
    idx = a.index.intersection(b.index)
    for c in [c for c in a.columns if c in b.columns]:
        x, y = a.loc[idx, c], b.loc[idx, c]
        if pd.api.types.is_float_dtype(x) and pd.api.types.is_float_dtype(y):
            neq = ~((x == y) | (x.isna() & y.isna()))
        else:
            neq = x.astype(str) != y.astype(str)
        for i in np.flatnonzero(neq.to_numpy()):
            lines.append(f"{idx[i]!r}\t{c}\t{x.iloc[i]!r}\t{y.iloc[i]!r}")
    return "\n".join(lines) + ("\n" if lines else "")


def main(argv):
    if len(argv) == 1:
        sys.stdout.write(_text(pd.read_parquet(argv[0])))
    elif len(argv) == 2:
        sys.stdout.write(_diff(pd.read_parquet(argv[0]), pd.read_parquet(argv[1])))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

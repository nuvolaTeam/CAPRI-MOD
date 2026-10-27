"""Reading and writing the model's builder-written inputs as Parquet (the project lead's decision, 27 October 2026).

Every model input that a builder in tools/build writes is stored as Parquet: float64 values are kept bit for bit, the
column types travel with the file, and no parser setting can lose a digit. Sources (capri_data/sources: CAPRI,
Eurostat and FAO extracts) and supplied or hand-maintained tables stay CSV (capri_mod/csvio.py), and so do the
validation tables.

A table is stored as its CSV would be read without an index (every column a column, the types pandas infers), so that
read_input gives what read_csv gives for the options the model uses (index_col, usecols, nrows, dtype); write_table
keeps a frame's own index when a builder writes one. tools/check/show_table.py prints a table, or the difference of
two, as text; with .gitattributes and `git config diff.parquet.textconv "python tools/check/show_table.py"` git shows Parquet changes as
text diffs.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

#: the Parquet settings of every written input: the file depends on the data only (no wall-clock metadata), so a
#: builder that reproduces its values reproduces its file
_WRITE = dict(engine="pyarrow", compression="zstd", index=None)


def read_table(path) -> pd.DataFrame:
    """A builder-written input (Parquet) as written."""
    p = Path(path)
    if p.suffix != ".parquet":
        raise ValueError(f"{p}: model inputs written by builders are Parquet (capri_mod/tableio.py)")
    return pd.read_parquet(p, engine="pyarrow")


def write_table(df: pd.DataFrame, path) -> None:
    """Write a builder output as Parquet, its index included (named or default)."""
    p = Path(path)
    if p.suffix != ".parquet":
        raise ValueError(f"{p}: model inputs written by builders are Parquet (capri_mod/tableio.py)")
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, **_WRITE)


def read_input(path, **kw) -> pd.DataFrame:
    """A model input, CSV (capri_mod/csvio.read_csv) or Parquet, by the file's suffix: for Parquet the read options the
    model uses are applied as read_csv applies them (index_col, usecols, nrows, dtype); any other option is refused
    rather than ignored."""
    p = Path(path)
    if p.suffix != ".parquet":
        from capri_mod.csvio import read_csv
        return read_csv(p, **kw)
    allowed = {"index_col", "usecols", "nrows", "dtype"}
    other = set(kw) - allowed
    if other:
        raise ValueError(f"{p.name}: read options {sorted(other)} have no Parquet equivalent here")
    df = pd.read_parquet(p, engine="pyarrow")
    if df.index.name is not None or not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()                     # a table written with its index: back to columns, as in a CSV
    usecols = kw.get("usecols")
    if usecols is not None:
        cols = [df.columns[c] if isinstance(c, int) else c for c in usecols]
        df = df[[c for c in df.columns if c in cols]]
    if kw.get("nrows") is not None:
        df = df.iloc[: int(kw["nrows"])]
    dt = kw.get("dtype")
    if dt is not None:
        df = df.astype(dt if isinstance(dt, dict) else {c: dt for c in df.columns})
    ic = kw.get("index_col")
    if ic is not None and ic is not False:
        keys = ic if isinstance(ic, (list, tuple)) else [ic]
        df = df.set_index([df.columns[k] if isinstance(k, int) else k for k in keys])
        # a CSV whose index column has no header reads with an unnamed index: the same here
        df.index.names = [None if (isinstance(n, str) and n.startswith("Unnamed: ")) else n for n in df.index.names]
    return df

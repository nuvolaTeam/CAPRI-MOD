"""Reading and writing the model's builder-written inputs as Parquet (the project lead's decision, 27 October 2026).

Every model input that a builder in tools/build writes is stored as Parquet: float64 values are kept bit for bit, the
column types travel with the file, and no parser setting can lose a digit. Sources (capri_data/sources: CAPRI,
Eurostat and FAO extracts) and supplied or hand-maintained tables stay CSV (capri_mod/csvio.py), and so do the
validation tables.

The index is stored as the file's index (pandas metadata), so a table reads back as it was written: same index and
names, same columns and dtypes. tools/check/show_table.py prints a table, or the difference of two, as text; with
.gitattributes and `git config diff.parquet.textconv "python tools/check/show_table.py"` git shows Parquet changes as
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

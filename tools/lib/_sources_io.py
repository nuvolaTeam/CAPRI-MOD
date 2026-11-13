"""capri_data/sources as Parquet (the data layout's step (c): docs/design/DATA_LAYOUT.md section 5 item 5, the project
lead's decision of 6 November 2026).

The files under capri_data/sources (raw/: CAPRI's and the other publishers' files converted one to one; intermediate/:
the builders' work tables) are Parquet; the model's inputs (2017/, 2030/, codes/, scenarios/) stay CSV, and the model
reads nothing under sources/. Every builder reads and writes them through this module:

- write_source(df, path, **to_csv_options): the table the builder's CSV would hold, i.e. the frame written as CSV text
  with the builder's own options (index, columns, float_format, ...) and read back exactly (capri_mod/csvio.read_csv,
  floats to the last digit), stored with capri_mod/tableio.write_table's fixed settings (zstd, no wall-clock
  metadata), so that a builder that reproduces its values reproduces the file's bytes for a given pyarrow version. A
  file converted from its CSV and the same file rebuilt are therefore the same table by construction.
- read_source(path, **read_csv_options): the table as read_csv(CSV, float_precision="round_trip") gave it: values to
  the last bit, the same column types (checked for every file at the conversion, tools/build/convert_sources_to_parquet.py).
  The options read_input applies on Parquet (usecols, nrows, dtype, index_col) are applied there; any other read_csv
  option (keep_default_na, na_values, converters, chunksize, ...) is applied by reading the table's CSV text, which
  differs from the original text only in how numbers are printed (1 against 1.0, 1E-5 against 1e-05): a reader that
  compares numbers as text must read them as numbers.
A path may be given with its former CSV name (.csv, .csv.xz, .csv.gz): it is mapped to the .parquet beside it.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv  # noqa: E402
from capri_mod.tableio import read_input, write_table  # noqa: E402

SOURCES_DIR = ROOT / "capri_data" / "sources"
CSV_SUFFIXES = (".csv.xz", ".csv.gz", ".csv")
#: read_csv options read_input applies itself on Parquet, and options without effect on a Parquet table
_NATIVE = {"usecols", "nrows", "dtype", "index_col"}
_DROPPED = {"float_precision", "compression", "encoding", "low_memory"}


def parquet_path(path) -> Path:
    """The Parquet file of a source given by its Parquet or former CSV name."""
    p = Path(path)
    for s in CSV_SUFFIXES:
        if p.name.endswith(s):
            return p.with_name(p.name[: -len(s)] + ".parquet")
    if p.suffix != ".parquet":
        raise ValueError(f"{p}: not a table name (.parquet, or a former .csv / .csv.xz / .csv.gz)")
    return p


def read_source(path, **kw) -> pd.DataFrame:
    """A table of capri_data/sources (module docstring)."""
    p = parquet_path(path)
    for k in _DROPPED:
        kw.pop(k, None)
    if not (set(kw) - _NATIVE):
        return read_input(p, **kw)
    # an option Parquet has no equivalent of: through the table's CSV text
    if "chunksize" in kw or "iterator" in kw:
        raise ValueError(f"{p.name}: read the table whole (read_source) instead of in chunks")
    buf = io.StringIO()
    read_input(p).to_csv(buf, index=False)
    buf.seek(0)
    return read_csv(buf, **kw)


def write_source(df: pd.DataFrame, path, **to_csv_kw) -> Path:
    """Write a builder's table under capri_data/sources as Parquet (module docstring); returns the path written."""
    p = parquet_path(path)
    for k in ("compression", "encoding", "lineterminator", "line_terminator"):
        to_csv_kw.pop(k, None)
    buf = io.StringIO()
    df.to_csv(buf, **to_csv_kw)
    buf.seek(0)
    t = read_csv(buf)
    write_table(t, p)
    return p


def write_source_text(text: str, path) -> Path:
    """Write a CSV text as the table under capri_data/sources it holds (read exactly, as write_source)."""
    p = parquet_path(path)
    write_table(read_csv(io.StringIO(text)), p)
    return p


def source_records(path):
    """The rows of a source table as dicts of strings, as csv.DictReader gave them from its CSV (empty cells "")."""
    t = read_source(path, dtype=str, keep_default_na=False)
    return t.to_dict("records")

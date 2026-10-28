"""Parquet inputs, step 3: the builder-written model inputs from CSV to Parquet (the project lead's decision, 27 October
2026; capri_mod/tableio.py).

Input: a census of the files the builders write (tools/check/reproduce_builders.py REPORT.csv: one row per builder and
file, every file a builder writes). Converted: the files under capri_data that are model inputs, i.e. not sources
(capri_data/sources: CAPRI, Eurostat, FAO extracts, which stay CSV) and not validation tables (capri_data/validation).

Each CSV is read exactly (capri_mod/csvio.read_csv, no index: every column a column, the types pandas infers) and
written next to it as Parquet (tableio.write_table, same name with .parquet for .csv, .csv.xz, .csv.gz). The conversion
is checked before the CSV is removed:
  1. read_input(Parquet) equals read_csv(CSV) exactly: values to the last bit, column names, types, row order;
  2. read with dtype=str (as a loader may) both give the same strings: a column whose CSV text is not what its parsed
     values print (codes with leading zeros, "1.0" against "1") is reported and the file is not converted.
A file that fails either check stays CSV and is listed.

    python tools/build/convert_inputs_to_parquet.py CENSUS.csv [--dry-run] [--report OUT.csv]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv  # noqa: E402
from capri_mod.tableio import read_input, write_table  # noqa: E402

KEEP_CSV = ("capri_data/sources/", "capri_data/validation/")
SUFFIXES = (".csv.xz", ".csv.gz", ".csv")


def parquet_name(rel: str) -> str | None:
    for s in SUFFIXES:
        if rel.endswith(s):
            return rel[: -len(s)] + ".parquet"
    return None


def inputs_of(census: Path) -> list[str]:
    files = set()
    with open(census, newline="") as f:
        for r in csv.DictReader(f):
            rel = (r.get("file") or "").strip()
            if rel.startswith("capri_data/") and not rel.startswith(KEEP_CSV) and parquet_name(rel):
                files.add(rel)
    return sorted(files)


def convert(rel: str, dry: bool) -> tuple[str, str]:
    src = ROOT / rel
    if not src.exists():
        return "absent", ""
    dst = ROOT / parquet_name(rel)
    if dst.exists():
        return "parquet exists", str(dst.relative_to(ROOT))
    a = read_csv(src)
    write_table(a, dst)                  # removed again if a check fails
    try:
        b = read_input(dst)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        sa, sb = read_csv(src, dtype=str, keep_default_na=False), read_input(dst, dtype=str)
        sb = sb.where(b.notna(), "")
        bad = [c for c in sa.columns if not sa[c].equals(sb[c].astype(str))]
        if bad:
            raise AssertionError(f"text differs from the parsed values in {bad[:5]}")
    except AssertionError as e:
        dst.unlink()
        return "kept CSV", str(e).splitlines()[0][:200]
    if dry:
        dst.unlink()
        return "would convert", ""
    src.unlink()
    return "converted", str(dst.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("census")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default="")
    a = ap.parse_args()
    rows = [(rel, *convert(rel, a.dry_run)) for rel in inputs_of(Path(a.census))]
    for r in rows:
        print(*r, sep="  |  ")
    if a.report:
        with open(a.report, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["file", "status", "detail"])
            w.writerows(rows)
    n = {}
    for _, s, _ in rows:
        n[s] = n.get(s, 0) + 1
    print(n)


if __name__ == "__main__":
    main()

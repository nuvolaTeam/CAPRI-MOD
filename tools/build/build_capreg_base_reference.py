"""CAPRI's CAPREG base-year data (CAPTRD's DATA2) as CSV, one file per country.

Source: CAPREG's base-year results res_17<CC>.gdx, symbol DATA2(rall, cols, rows, "Y"), from the project lead's CAPRI
installation, either as the GDX files (read with the GDX library, --gdxlib or CAPRI_GDXLIB) or as text dumps
res_17<CC>.txt (a GAMS parameter listing "'region'.'col'.'row'.'Y' value,"; uploaded as res_17zip.zip and single
files). CAPTRD reads this symbol from %results_in%\\capreg\\res_%BAS%<MS.tl:2>.gdx (the first two characters of the
country code: TU for TUR) and copies it to p_data(..., "BASM") (captrd.gms l. 528-580). <CC> is that file code.

The dumps carry 15 significant digits (the GDX files 17): parity with CAPTRD is to about 1e-14 relative for countries
taken from a dump. A country present in both forms is taken from the GDX file.

Output (CAPRI's own data: read-only reference, read by the tests and the parity runs, never by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/capreg_base/17/<CC>.csv.gz    region, col, row, t, value, eps   (t = Y)

Zeros: a record listed as Eps is written with value 0 and eps = 1; a record not listed is absent.

    python tools/build/build_capreg_base_reference.py --src DIR_OR_ZIP [--src DIR ...] [--gdxlib DIR]
"""
from __future__ import annotations

import argparse
import csv
import os
import gzip
import re
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_reference" / "capreg_base" / "17"
REC = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\s+(\S+?),?\s*$")


def _records(path: Path):
    head = True
    for ln in open(path, encoding="utf-8", errors="strict"):
        s = ln.strip()
        if not s:
            continue
        if head:
            if s.startswith("Parameter DATA2("):
                head = False
                continue
            raise ValueError(f"{path}: expected the listing of DATA2, found {s[:60]!r}")
        if s == "/;":
            return
        last = s.endswith("/;")                          # the last record closes the listing on its own line
        if last:
            s = s[:-2].rstrip()
        m = REC.match(s)
        if not m:
            raise ValueError(f"{path}: unreadable line {s[:80]!r}")
        r, c, w, t, v = m.groups()
        if v.lower() == "eps":
            yield r, c, w, t, 0.0, 1
        elif v.upper() in ("NA", "UNDF", "+INF", "-INF", "INF"):
            raise ValueError(f"{path}: special value {v} at {(r, c, w, t)}")
        else:
            yield r, c, w, t, float(v), 0
        if last:
            return
    raise ValueError(f"{path}: the listing does not end with '/;'")


def _gdx_records(path: Path, gdxlib: str):
    import gams.core.gdx as g

    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, gdxlib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(f"GDX library not loaded from {gdxlib}: {msg}")
    if not g.gdxOpenRead(h, str(path))[0]:
        raise RuntimeError(f"cannot open {path}")
    ok, idx = g.gdxFindSymbol(h, "DATA2")
    if not ok or g.gdxSymbolInfo(h, idx)[2] != 4:
        raise KeyError(f"{path}: no 4-dimensional symbol DATA2")
    sv = g.doubleArray(g.GMS_SVIDX_MAX)
    g.gdxGetSpecialValues(h, sv)
    eps, undf, na = sv[g.GMS_SVIDX_EPS], sv[g.GMS_SVIDX_UNDEF], sv[g.GMS_SVIDX_NA]
    _, n = g.gdxDataReadStrStart(h, idx)
    for _ in range(n):
        _, keys, vals, _ = g.gdxDataReadStr(h)
        v = vals[g.GMS_VAL_LEVEL]
        if v == eps:
            yield (*keys, 0.0, 1)
        elif v in (undf, na):
            raise ValueError(f"{path}: special value {v} at {keys}")
        else:
            yield (*keys, v, 0)
    g.gdxClose(h)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, action="append", help="folder or zip with res_17<CC>.gdx or .txt")
    ap.add_argument("--gdxlib", default=os.environ.get("CAPRI_GDXLIB", ""))
    args = ap.parse_args()
    tmps, found = [], {}
    for src in map(Path, args.src):
        if src.suffix == ".zip":
            tmp = tempfile.TemporaryDirectory()
            tmps.append(tmp)
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp.name)
            files = sorted(Path(tmp.name).rglob("res_17*.*"))
        else:
            files = sorted(src.glob("res_17*.*"))
        for f in files:
            if f.suffix.lower() not in (".txt", ".gdx"):
                continue
            cc = f.stem[len("res_17"):]
            if cc not in found or f.suffix.lower() == ".gdx":
                found[cc] = f
    if not found:
        raise SystemExit(f"no res_17*.gdx or .txt in {args.src}")
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for cc, f in sorted(found.items()):
        out = OUT / f"{cc}.csv.gz"
        recs = _gdx_records(f, args.gdxlib) if f.suffix.lower() == ".gdx" else _records(f)
        n = 0
        with gzip.open(out, "wt", newline="", compresslevel=6) as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["region", "col", "row", "t", "value", "eps"])
            for r in recs:
                w.writerow((*r[:4], repr(r[4]), r[5]))
                n += 1
        total += n
        print(f"{cc}: {n} records from {f.name} -> {out.relative_to(ROOT)}")
    print(f"{len(found)} files, {total} records")
    for t in tmps:
        t.cleanup()


if __name__ == "__main__":
    main()

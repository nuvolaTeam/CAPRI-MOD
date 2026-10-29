"""CAPRI's CAPREG base-year data (CAPTRD's DATA2) as CSV, one file per country.

Source: text dumps of CAPREG's base-year results res_17<MS>.gdx, symbol DATA2(rall, cols, rows, "Y"), from the
project lead's CAPRI installation (uploaded as res_17zip.zip and single files: res_17<CC>.txt, a GAMS parameter listing
"'region'.'col'.'row'.'Y' value,"). CAPTRD reads this symbol from %results_in%\\capreg\\res_%BAS%<MS>.gdx and copies it
to p_data(..., "BASM") (captrd.gms l. 528-580).

The dumps carry 15 significant digits (the GDX files 17): parity with CAPTRD is to about 1e-14 relative.

Output (CAPRI's own data: read-only reference, read by the tests and the parity runs, never by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/capreg_base/17/<CC>.csv.gz    region, col, row, t, value, eps   (t = Y)

Zeros: a record listed as Eps is written with value 0 and eps = 1; a record not listed is absent.

    python tools/build/build_capreg_base_reference.py --src DIR_OR_ZIP
"""
from __future__ import annotations

import argparse
import csv
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="folder with res_17<CC>.txt or the uploaded zip")
    args = ap.parse_args()
    src = Path(args.src)
    tmp = None
    if src.suffix == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp.name)
        files = sorted(Path(tmp.name).rglob("res_17*.txt"))
    else:
        files = sorted(src.glob("res_17*.txt"))
    if not files:
        raise SystemExit(f"no res_17*.txt in {src}")
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in files:
        cc = f.stem[len("res_17"):]
        out = OUT / f"{cc}.csv.gz"
        n = 0
        with gzip.open(out, "wt", newline="", compresslevel=6) as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["region", "col", "row", "t", "value", "eps"])
            for r in _records(f):
                w.writerow((*r[:4], repr(r[4]), r[5]))
                n += 1
        total += n
        print(f"{cc}: {n} records -> {out.relative_to(ROOT)}")
    print(f"{len(files)} files, {total} records")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()

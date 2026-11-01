"""CAPRI's COCO output (coco2_output.gdx, symbol DATA2) as CSV: CAPTRD's input for the recent years.

Source: a text listing of the symbol DATA2(rall, cocoItem, cols, rows, t) of %results_in%\\coco\\coco2_output.gdx from
the project lead's CAPRI installation (uploaded as coco2.zip: coco2.csv, a GAMS parameter listing
"'region'.'item'.'col'.'row'.'t' value,", cocoItem = INI, COCO1, COCO2). CAPTRD loads it as dataMS
(captrd/load_coco1_data.gms l. 24) for the ex-post years after CAPREG's series (ExAnteD), the biofuels and the
nowcasts.

The listing carries 15 significant digits (the GDX file 17).

Output (CAPRI's own data: read-only reference, read by the tests and the parity runs, never by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/coco2/17/coco2_output.csv.gz    region, item, col, row, t, value, eps

Zeros: a record listed as Eps is written with value 0 and eps = 1; a record not listed is absent.

    python tools/build/build_coco2_reference.py --src coco2.zip|coco2.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_reference" / "coco2" / "17" / "coco2_output.csv.gz"
REC = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\s+(\S+?)\s*,?$")


def _records(lines):
    head = True
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if head:
            if s.startswith("Parameter DATA2("):
                head = False
                continue
            raise ValueError(f"expected the listing of DATA2, found {s[:60]!r}")
        if s == "/;":
            return
        last = s.endswith("/;")
        if last:
            s = s[:-2].rstrip()
        m = REC.match(s)
        if not m:
            raise ValueError(f"unreadable line {s[:80]!r}")
        *keys, v = m.groups()
        if v.lower() == "eps":
            yield (*keys, 0.0, 1)
        elif v.upper() in ("NA", "UNDF", "+INF", "-INF", "INF"):
            raise ValueError(f"special value {v} at {keys}")
        else:
            yield (*keys, float(v), 0)
        if last:
            return
    raise ValueError("the listing does not end with '/;'")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="coco2.zip (holding coco2.csv) or coco2.csv")
    args = ap.parse_args()
    src = Path(args.src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    zf = zipfile.ZipFile(src) if src.suffix == ".zip" else None
    raw = zf.open("coco2.csv") if zf else open(src, "rb")
    n = 0
    with io.TextIOWrapper(raw, encoding="utf-8") as lines, gzip.open(OUT, "wt", newline="", compresslevel=6) as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "item", "col", "row", "t", "value", "eps"])
        for r in _records(lines):
            w.writerow((*r[:5], repr(r[5]), r[6]))
            n += 1
    print(f"{n} records -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

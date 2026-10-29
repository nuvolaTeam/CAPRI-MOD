"""Symbols of CAPRI's global database fao_agg_17_defaulta.gdx as CSV, for CAPTRD-MOD.

Source: a text listing of %results_in%\\global\\fao_agg_17_defaulta.gdx from the project lead's CAPRI installation
(uploaded as FAO_agg_17_defaulta.zip: FAO_agg_17_defaulta.csv, GAMS parameter listings
"Parameter name(*,...) text /" followed by "'k1'.'k2'... value," records). CAPTRD loads p_biofuelData and
p_aglinkGrowthFactor from it (captrd/load_coco1_data.gms l. 358-360).

The listing carries 15 significant digits (the GDX file 17).

Output (CAPRI's own data: read-only reference, read by the tests and the parity runs, never by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/fao_agg/17/<symbol>.csv.gz    d0, d1, ..., value, eps

Zeros: a record listed as Eps is written with value 0 and eps = 1; a record not listed is absent.

    python tools/build/build_fao_agg_reference.py --src FAO_agg_17_defaulta.zip [--symbols p_biofuelData ...]
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
OUT = ROOT / "capri_reference" / "fao_agg" / "17"
HEAD = re.compile(r"^Parameter\s+(\w+)\(([^)]*)\)")
KEY = re.compile(r"'([^']*)'")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--symbols", nargs="+", default=["p_biofuelData", "p_aglinkGrowthFactor"])
    args = ap.parse_args()
    src = Path(args.src)
    want = {s.lower(): s for s in args.symbols}
    OUT.mkdir(parents=True, exist_ok=True)
    zf = zipfile.ZipFile(src) if src.suffix == ".zip" else None
    raw = zf.open(zf.namelist()[0]) if zf else open(src, "rb")
    done = set()
    cur = fh = w = None
    dim = n = 0
    with io.TextIOWrapper(raw, encoding="utf-8") as lines:
        for ln in lines:
            s = ln.strip()
            if cur is None:
                m = HEAD.match(s)
                if m and m.group(1).lower() in want and m.group(1).lower() not in done:
                    cur, dim, n = m.group(1), len(m.group(2).split(",")), 0
                    fh = gzip.open(OUT / f"{want[cur.lower()]}.csv.gz", "wt", newline="", compresslevel=6)
                    w = csv.writer(fh, lineterminator="\n")
                    w.writerow([f"d{k}" for k in range(dim)] + ["value", "eps"])
                continue
            if not s:
                continue
            end = s.endswith("/;")
            if end:
                s = s[:-2].rstrip()
            if s:
                keys = KEY.findall(s)
                v = s[s.rfind("'") + 1:].strip().rstrip(",").strip()
                if len(keys) != dim or not v:
                    raise ValueError(f"{cur}: unreadable line {s[:80]!r}")
                if v.lower() == "eps":
                    w.writerow(keys + ["0.0", 1])
                elif v.upper() in ("NA", "UNDF", "+INF", "-INF", "INF"):
                    raise ValueError(f"{cur}: special value {v} at {keys}")
                else:
                    w.writerow(keys + [repr(float(v)), 0])
                n += 1
            if end:
                fh.close()
                print(f"{cur}: {n} records -> {(OUT / (want[cur.lower()] + '.csv.gz')).relative_to(ROOT)}")
                done.add(cur.lower())
                cur = None
                if done == set(want):
                    break
    missing = set(want) - done
    if missing:
        raise SystemExit(f"symbols not found or not closed: {sorted(want[m] for m in missing)}")


if __name__ == "__main__":
    main()

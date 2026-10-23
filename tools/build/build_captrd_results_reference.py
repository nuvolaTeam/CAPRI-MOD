"""CAPRI's CAPTRD results (p_result) as CSV, one file per result position, for the CAPTRD-MOD parity tests.

Source: the project lead's CAPRI installation, %results_out%\\baseline\\results_<BAS><SIM>....gdx (uploaded as
results_1770.gdx: base year 2017, last simulation year 2070), written by captrd.gms l. 1325-1383 with
p_result(rall, cols, rows, t, respos) (respos: sets_captrd.gms l. 493-531; CAPTRD_MAP.md section 6).

Output (CAPRI's own data: read-only reference for the tests and parity runs, never read by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/captrd_results/<tag>/<respos>.csv.gz     region, col, row, t, value, eps
  capri_reference/captrd_results/<tag>/respos_counts.csv   records per result position (all positions)
  capri_reference/captrd_results/<tag>/settings.csv        the SETTINGS symbol of the file

Only the positions named with --keep are written (default: the Step 1 and Step 2 ones); Eps is written as 0 with
eps = 1, an absent record stays absent.

    python tools/build/build_captrd_results_reference.py --src results_1770.gdx --tag 1770 [--keep Step1 Support ...]
"""
from __future__ import annotations

import argparse
import csv
import gzip
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GDXLIB = "/home/claude/work/gdxlib"
KEEP = ["Step1", "Support", "Support1", "wVarErr", "CoefVarErr", "DATA", "p_data", "BASM", "BAST", "BSY", "coco",
        "Expert", "TrustLevl", "DGAgri", "DGAgri1", "step2", "step3", "series", "lo", "up", "nObs"]


def _open(path: Path, gdxlib: str):
    import gams.core.gdx as g
    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, gdxlib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(f"GDX library not loaded from {gdxlib}: {msg}")
    if not g.gdxOpenRead(h, str(path))[0]:
        raise RuntimeError(f"cannot open {path}")
    sv = g.doubleArray(g.GMS_SVIDX_MAX)
    g.gdxGetSpecialValues(h, sv)
    return g, h, sv[g.GMS_SVIDX_EPS]


def _records(g, h, eps, sym):
    ok, idx = g.gdxFindSymbol(h, sym)
    if not ok:
        raise KeyError(sym)
    _, n = g.gdxDataReadStrStart(h, idx)
    for _ in range(n):
        _, keys, vals, _ = g.gdxDataReadStr(h)
        v = vals[g.GMS_VAL_LEVEL]
        yield keys, (0.0, 1) if v == eps else (v, 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--keep", nargs="*", default=KEEP)
    ap.add_argument("--gdxlib", default=DEFAULT_GDXLIB)
    args = ap.parse_args()
    out = ROOT / "capri_reference" / "captrd_results" / args.tag
    out.mkdir(parents=True, exist_ok=True)
    keep = {k.lower(): k for k in args.keep}
    g, h, eps = _open(Path(args.src), args.gdxlib)
    writers, files, counts = {}, [], Counter()
    for keys, (v, e) in _records(g, h, eps, "p_result"):
        rp = keys[4]
        counts[rp] += 1
        k = rp.lower()
        if k not in keep:
            continue
        if k not in writers:
            fh = gzip.open(out / f"{rp}.csv.gz", "wt", newline="", compresslevel=6)
            files.append(fh)
            writers[k] = csv.writer(fh, lineterminator="\n")
            writers[k].writerow(["region", "col", "row", "t", "value", "eps"])
        writers[k].writerow((keys[0], keys[1], keys[2], keys[3], repr(v), e))
    for fh in files:
        fh.close()
    with open(out / "respos_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["respos", "records", "written"])
        for rp, n in sorted(counts.items()):
            w.writerow([rp, n, int(rp.lower() in keep)])
    with open(out / "settings.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["d0", "d1", "d2", "text"])
        ok, idx = g.gdxFindSymbol(h, "SETTINGS")
        _, n = g.gdxDataReadStrStart(h, idx)
        for _ in range(n):
            _, keys, vals, _ = g.gdxDataReadStr(h)
            _, txt, _ = g.gdxGetElemText(h, int(vals[g.GMS_VAL_LEVEL])) if vals[g.GMS_VAL_LEVEL] else (0, "", 0)
            w.writerow([*keys, txt])
    g.gdxClose(h)
    print(f"{sum(counts.values())} records; written: {sorted(k for k in counts if k.lower() in keep)} -> {out}")


if __name__ == "__main__":
    main()

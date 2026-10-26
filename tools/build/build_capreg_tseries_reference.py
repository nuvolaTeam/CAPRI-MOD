"""CAPRI's CAPREG time series (CAPTRD's core input) as CSV, one file per country.

Source: the project lead's CAPRI installation, folder Capreg_tseries (uploaded as Capreg_tseries.zip, 36 files
<CC>_17.gdx). Each file holds the symbol DATA(rall, cols, rows, t) with t = 1984..2018 plus the statistics
BAS, BASM, CUR, MEAN, TRD and Y, for the country, its NUTS2 regions and some EU aggregates.

This is what CAPTRD reads as DATA1 from %results_in%\\capreg\\res_time_series_%BAS%<MS>.gdx
(captrd.gms l. 486-505; written by capreg/store_time_series.gms l. 46). CAPTRD copies only the year entries into
p_data (captrd.gms l. 504); the non-year entries are kept here unchanged so the file is a complete copy of DATA.

Output (CAPRI's own data: read-only reference, read by the tests and the parity runs, never by the model;
docs/design/CAPTRD_MOD.md section 6):
  capri_reference/capreg_tseries/17/<CC>.csv.gz    region, col, row, t, value

Zeros and missing values: a record stored as GAMS Eps (an explicit zero) is written with value 0 and eps = 1;
a record not stored in the GDX is absent from the CSV. CAPRI itself treats both as zero; the distinction is kept
for the zero/missing fix of CAPTRD_MOD.md section 8.3.

    python tools/build/build_capreg_tseries_reference.py --src DIR_OR_ZIP [--gdxlib DIR]
"""
from __future__ import annotations

import os
import argparse
import csv
import gzip
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_reference" / "capreg_tseries" / "17"
# folder of libgdxcclib64.so (README section 3): --gdxlib or the environment variable CAPRI_GDXLIB
DEFAULT_GDXLIB = os.environ.get("CAPRI_GDXLIB", "")


def _read_data(path: Path, gdxlib: str):
    import gams.core.gdx as g

    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, gdxlib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(f"GDX library not loaded from {gdxlib}: {msg}")
    if not g.gdxOpenRead(h, str(path))[0]:
        raise RuntimeError(f"cannot open {path}")
    ok, idx = g.gdxFindSymbol(h, "DATA")
    if not ok:
        raise KeyError(f"{path}: no symbol DATA")
    _, name, dim, _ = g.gdxSymbolInfo(h, idx)
    if dim != 4:
        raise ValueError(f"{path}: DATA has {dim} dimensions, expected 4")
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
    ap.add_argument("--src", required=True, help="folder with <CC>_17.gdx or the uploaded zip")
    ap.add_argument("--gdxlib", default=DEFAULT_GDXLIB)
    args = ap.parse_args()
    src = Path(args.src)
    tmp = None
    if src.suffix == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp.name)
        files = sorted(Path(tmp.name).rglob("*_17.gdx"))
    else:
        files = sorted(src.glob("*_17.gdx"))
    if not files:
        raise SystemExit(f"no *_17.gdx in {src}")
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in files:
        cc = f.stem.split("_")[0]
        out = OUT / f"{cc}.csv.gz"
        n = 0
        with gzip.open(out, "wt", newline="", compresslevel=6) as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["region", "col", "row", "t", "value", "eps"])
            for r in _read_data(f, args.gdxlib):
                w.writerow((r[0], r[1], r[2], r[3], repr(r[4]), r[5]))
                n += 1
        total += n
        print(f"{cc}: {n} records -> {out.relative_to(ROOT)}")
    print(f"{len(files)} files, {total} records")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()

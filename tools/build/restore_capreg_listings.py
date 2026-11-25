"""CAPREG's 2017 listings capri_sources/capreg/res_17<CC>.txt, which 43 builders read, written again from CAPREG's GDX
files capri_sources/results/capreg/res_17<CC>.gdx (the project lead's res_17.zip of 25 November 2026, 35 countries).

The listings the builders were built from are no longer on this machine: gdxdump's output of these GDX files
(tools/gams/dump_capreg_explicit.gms: gdxdump res_17<CC>.gdx symb=DATA2, capri_export/DATA2_<CC>.txt, which
capreg/res_17<CC>.txt linked to; res_17zip.zip, capri_export_zip.zip). They were GAMS parameter listings of
DATA2(region, col, row, "Y") with 15 significant digits: a "Parameter DATA2(" line,
one "'region'.'col'.'row'.'Y' value," line per record, Eps for a zero listed, the last record closed by "/;"
(tools/build/build_capreg_base_reference.py reads that form). They are written here in that form, the values at 15
significant digits ("%.15g"), so that the builders read the values they were built from. Moving the builders to the
GDX's full precision is left to the builders' reorganisation (the project lead, 25 November 2026).

--check compares every value written with CAPRI's reference capri_sources/reference/capreg_base/17/<CC>.csv.gz
(build_capreg_base_reference.py: from the old listings for 26 countries and Spain's GUI export, from the GDX for 8): the
same records, Eps alike, every value equal as read back.

    python tools/build/restore_capreg_listings.py [--check] [--gdxlib DIR]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "build")]
from paths import SOURCES  # noqa: E402

GDX = SOURCES / "results" / "capreg"
OUT = SOURCES / "capreg"
BASE = SOURCES / "reference" / "capreg_base" / "17"


def gdx_records(path: Path, gdxlib: str) -> list:
    """DATA2's records of the GDX file in its order: (region, col, row, t, value, eps)."""
    import build_capreg_base_reference as bcr
    return list(bcr._gdx_records(path, gdxlib))


def write_listing(recs: list, out: Path) -> None:
    """The listing in GAMS's form, the values at 15 significant digits."""
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("Parameter DATA2(*,*,*,*) /\n")
        for i, (r, c, w, t, v, e) in enumerate(recs):
            val = "Eps" if e else f"{v:.15g}"
            end = " /;" if i == len(recs) - 1 else ","
            fh.write(f"'{r}'.'{c}'.'{w}'.'{t}' {val}{end}\n")
        if not recs:
            fh.write("/;\n")
    if out.is_symlink() or out.exists():
        out.unlink()
    tmp.rename(out)


def check(cc: str, out: Path) -> tuple:
    """The listing read back (build_capreg_base_reference._records) against capreg_base: records, Eps and values at
    15 significant digits (capreg_base has 17 for the countries it took from the GDX). Returns (the differences or "",
    whether capreg_base's values are equal without rounding)."""
    import build_capreg_base_reference as bcr
    mine = list(bcr._records(out))
    with gzip.open(BASE / f"{cc}.csv.gz", "rt", newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        ref = [(r, c, w, t, float(v), int(e)) for r, c, w, t, v, e in rd]
    if len(mine) != len(ref):
        return f"{len(mine)} records, capreg_base {len(ref)}", False
    a, b = sorted(mine), sorted(ref)
    exact = a == b
    b15 = [(r, c, w, t, float(f"{v:.15g}"), e) for r, c, w, t, v, e in b]
    bad = [(x, y) for x, y in zip(a, b15) if x != y]
    return (f"{len(bad)} records differ at 15 digits, e.g. {bad[:2]}" if bad else ""), exact


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--gdxlib", default=os.environ.get("CAPRI_GDXLIB", ""))
    a = ap.parse_args()
    if not a.gdxlib:
        raise SystemExit("the GDX library's folder: --gdxlib or CAPRI_GDXLIB")
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(GDX.glob("res_17*.gdx"))
    if not files:
        raise SystemExit(f"no res_17*.gdx in {GDX}")
    problems = 0
    for f in files:
        cc = f.stem[len("res_17"):]
        recs = gdx_records(f, a.gdxlib)
        out = OUT / f"res_17{cc}.txt"
        write_listing(recs, out)
        msg, exact = check(cc, out) if a.check else ("", False)
        problems += bool(msg)
        verdict = msg or ("equal" if exact else "equal at 15 digits")
        tail = f"; against capreg_base: {verdict}" if a.check else ""
        print(f"{out.relative_to(SOURCES)}: {len(recs)} records{tail}")
    if problems:
        raise SystemExit(f"{problems} countries differ from capreg_base")


if __name__ == "__main__":
    main()

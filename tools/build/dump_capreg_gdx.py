"""CAPREG's 2017 base results (res_17<CC>.gdx, symbol DATA2) written as the text dumps the builders read
(res_17<CC>.txt in gdxdump's form: 'region'.'col'.'row'.'Y' value, EPS as Eps; KNOWN_ISSUES scoping of the UK, Turkey
and the Western Balkans, docs: noneu_supply_regions_scoping).

The EU's and Norway's dumps were made with GAMS's gdxdump on the project lead's installation; this writes the same form
with GAMS's GDX library (gams.core.gdx), numbers at 15 significant digits as gdxdump prints them, so the builders'
parsers read both alike. Check: --check DUMP.txt compares a dump of the same file record by record.

    python tools/build/dump_capreg_gdx.py GDX... --out DIR [--gdxlib DIR] [--check DUMP.txt]
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def dump(path: Path, out: Path, gdxlib: str, symbol: str = "DATA2") -> int:
    import gams.core.gdx as g
    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, gdxlib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(f"GDX library not loaded from {gdxlib!r}: {msg}")
    try:
        if not g.gdxOpenRead(h, str(path))[0]:
            raise RuntimeError(f"cannot open {path}")
        ok, idx = g.gdxFindSymbol(h, symbol)
        if not ok:
            raise KeyError(f"{path}: no symbol {symbol}")
        _, _, dim, _ = g.gdxSymbolInfo(h, idx)
        sv = g.doubleArray(g.GMS_SVIDX_MAX)
        g.gdxGetSpecialValues(h, sv)
        eps, undf, na = sv[g.GMS_SVIDX_EPS], sv[g.GMS_SVIDX_UNDEF], sv[g.GMS_SVIDX_NA]
        _, n = g.gdxDataReadStrStart(h, idx)
        lines = []
        for _ in range(n):
            _, keys, vals, _ = g.gdxDataReadStr(h)
            v = vals[g.GMS_VAL_LEVEL]
            txt = "Eps" if v == eps else "UNDF" if v == undf else "NA" if v == na else format(v, ".15g")
            lines.append(".".join(f"'{k}'" for k in keys[:dim]) + " " + txt)
        g.gdxDataReadDone(h)
        g.gdxClose(h)
    finally:
        g.gdxFree(h)
    with open(out, "w") as f:
        f.write(f"\nParameter {symbol}({','.join('*' * dim)}) /\n")
        f.write(",\n".join(lines) + " /;\n")
    return n


def records(path: Path) -> dict:
    rx = re.compile(r"^('[^ ]+') (\S+?)[,]?\s*(/;)?$")
    out = {}
    for line in open(path, errors="ignore"):
        m = rx.match(line.strip())
        if m:
            v = m.group(2).rstrip(",")
            out[m.group(1)] = 0.0 if v.lower() == "eps" else float(v)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gdx", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gdxlib", default=os.environ.get("CAPRI_GDXLIB", ""))
    ap.add_argument("--check", type=Path, help="a gdxdump of the first file, to compare record by record")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for p in a.gdx:
        dest = a.out / (p.stem + ".txt")
        n = dump(p, dest, a.gdxlib)
        print(f"{dest}: {n} records")
    if a.check:
        mine, ref = records(a.out / (a.gdx[0].stem + ".txt")), records(a.check)
        diff = [k for k in ref if k not in mine or abs(mine[k] - ref[k]) > 1e-12 * max(1.0, abs(ref[k]))]
        print(f"check against {a.check.name}: {len(ref)} records, {len(set(mine) - set(ref))} extra, {len(diff)} differing")


if __name__ == "__main__":
    main()

"""Dump one symbol of a GDX file to CSV without a GAMS installation.

Uses the GDX API's shared library (libgdxcclib64.so, built from GAMS' open-source gdx repository)
through the low-level bindings of the `gamsapi` package. Output columns: the symbol's index
positions dim1..dimN and value (level for parameters; level and marginal for variables/equations;
the element text for sets).

    python tools/build/gdx_dump_symbol.py FILE.gdx SYMBOL OUT.csv [--lib-dir /home/claude/work/gdxlib]
    python tools/build/gdx_dump_symbol.py FILE.gdx --list            (symbols in the file)
"""
from __future__ import annotations
import argparse, csv, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gdx")
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--lib-dir", default="/home/claude/work/gdxlib")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--filter", default="", help="keep records whose dim1..dimN contain all these comma-separated labels")
    ap.add_argument("--nonzero", action="store_true", help="skip records whose level and marginal are both 0")
    a = ap.parse_args()
    from gams.core import gdx
    h = gdx.new_gdxHandle_tp()
    ok, msg = gdx.gdxCreateD(h, a.lib_dir, gdx.GMS_SSSIZE)
    if not ok:
        sys.exit(f"cannot load GDX library from {a.lib_dir}: {msg}")
    ok, err = gdx.gdxOpenRead(h, a.gdx)
    if not ok:
        sys.exit(f"cannot open {a.gdx} (error {err})")
    _, nsym, _ = gdx.gdxSystemInfo(h)
    if a.list or not a.symbol:
        for i in range(1, nsym + 1):
            _, name, dim, typ = gdx.gdxSymbolInfo(h, i)
            _, nrec, _, text = gdx.gdxSymbolInfoX(h, i)
            print(f"{name}\tdim={dim}\ttype={typ}\trecords={nrec}\t{text}")
        return
    ok, idx = gdx.gdxFindSymbol(h, a.symbol)
    if not ok:
        sys.exit(f"symbol {a.symbol} not in {a.gdx}")
    _, name, dim, typ = gdx.gdxSymbolInfo(h, idx)
    ok, nrec = gdx.gdxDataReadStrStart(h, idx)
    keep = [x for x in a.filter.split(",") if x]
    n = 0
    with open(a.out, "w", newline="", encoding="utf-8", errors="replace") as fh:
        w = csv.writer(fh)
        w.writerow([f"dim{i + 1}" for i in range(dim)] + ["level", "marginal"])
        for _ in range(nrec):
            ok, keys, vals, _ = gdx.gdxDataReadStr(h)
            if not ok:
                break
            if keep and not all(k in keys for k in keep):
                continue
            if a.nonzero and typ != gdx.GMS_DT_SET and vals[gdx.GMS_VAL_LEVEL] == 0 and vals[gdx.GMS_VAL_MARGINAL] == 0:
                continue
            if typ == gdx.GMS_DT_SET:          # sets: the element's explanatory text
                txt = ""
                ti = int(vals[gdx.GMS_VAL_LEVEL])
                if ti:
                    r_ = gdx.gdxGetElemText(h, ti)
                    txt = r_[1] if r_[0] else ""
                w.writerow(list(keys) + [txt, ""])
            else:
                w.writerow(list(keys) + [vals[gdx.GMS_VAL_LEVEL], vals[gdx.GMS_VAL_MARGINAL]])
            n += 1
    gdx.gdxDataReadDone(h)
    gdx.gdxClose(h)
    print(f"{name}: {n} of {nrec} records -> {a.out}")


if __name__ == "__main__":
    main()

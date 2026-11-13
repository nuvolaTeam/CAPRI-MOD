"""CAPRI's GDX files as Parquet, one file per symbol: the converter of the published source set (docs/design/
MODEL_CONTENT_PLAN.md section 12b, step 1; layout of 4 November 2026: capri/results/<CAPRI run or file>/<symbol>).

Without a GAMS installation: GAMS's open-source GDX library (capri_sources/gdxlib, README section 3) through the
gamsapi bindings. Every record of every symbol, lossless:
  - the index positions as text columns d1..dN, as GDX stores them (the case as written);
  - parameters: value; variables and equations: level, marginal, lower, upper, scale; sets: text (the element text);
  - GAMS's special values: EPS as 0.0, +INF/-INF as inf/-inf, NA and UNDF as NaN, each also named in the text column
    special ("value:EPS", "level:EPS;marginal:+INF", ...; empty for an ordinary record), so the GDX's values are
    recoverable exactly;
  - labels and texts as text: bytes that are not UTF-8 (CAPRI's files are written on Windows: "ö" as the byte 0xF6)
    decoded as Latin-1, which maps every byte, so no byte is lost; their number per symbol in _symbols.csv
    (latin1_strings);
  - the symbol's type, dimension, domain names, explanatory text and record count, and the source file's name and
    SHA-256, in the Parquet file's metadata (key "capri_gdx", JSON).
Records are written in the GDX's order, in batches (a symbol of millions of records in bounded memory).

    python tools/build/convert_capri_gdx.py FILE.gdx OUT_DIR [--symbols S1,S2] [--lib-dir DIR]
Writes OUT_DIR/<symbol>.parquet for each symbol and OUT_DIR/_symbols.csv (symbol, type, dim, records, text,
latin1_strings).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402

BATCH = 500_000
TYPES = {0: "set", 1: "parameter", 2: "variable", 3: "equation", 4: "alias"}


def _text(s: str, count: list) -> str:
    """A GDX string as text: the library's bytes that are not UTF-8 come back as surrogates, decoded here as Latin-1."""
    try:
        s.encode("utf-8")
        return s
    except UnicodeEncodeError:
        count[0] += 1
        return s.encode("utf-8", "surrogateescape").decode("latin-1")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def convert(gdx_path: Path, out: Path, lib: str, symbols=None) -> list:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import gams.core.gdx as g
    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, lib, g.GMS_SSSIZE)
    if not ok:
        raise SystemExit(f"GDX library not loaded from {lib}: {msg}")
    if not g.gdxOpenRead(h, str(gdx_path))[0]:
        raise SystemExit(f"cannot open {gdx_path}")
    sv = g.doubleArray(g.GMS_SVIDX_MAX)
    g.gdxGetSpecialValues(h, sv)
    special = {sv[g.GMS_SVIDX_EPS]: ("EPS", 0.0), sv[g.GMS_SVIDX_PINF]: ("+INF", float("inf")),
               sv[g.GMS_SVIDX_MINF]: ("-INF", float("-inf")), sv[g.GMS_SVIDX_NA]: ("NA", float("nan")),
               sv[g.GMS_SVIDX_UNDEF]: ("UNDF", float("nan"))}
    src = {"file": gdx_path.name, "sha256": sha256(gdx_path)}
    out.mkdir(parents=True, exist_ok=True)
    _, nsym, _ = g.gdxSystemInfo(h)
    listing = []
    for i in range(1, nsym + 1):
        _, name, dim, typ = g.gdxSymbolInfo(h, i)
        _, nrec, _, text = g.gdxSymbolInfoX(h, i)
        if symbols and name not in symbols:
            continue
        kind = TYPES.get(typ, str(typ))
        n_l1 = [0]
        text = _text(text, n_l1)
        doms = [_text(x, n_l1) for x in g.gdxSymbolGetDomainX(h, i)[1]] if dim else []
        dcols = [f"d{k + 1}" for k in range(dim)]
        if kind == "parameter":
            fields = [("value", g.GMS_VAL_LEVEL)]
        elif kind in ("variable", "equation"):
            fields = [("level", g.GMS_VAL_LEVEL), ("marginal", g.GMS_VAL_MARGINAL), ("lower", g.GMS_VAL_LOWER),
                      ("upper", g.GMS_VAL_UPPER), ("scale", g.GMS_VAL_SCALE)]
        else:
            fields = []
        schema = pa.schema([(c, pa.string()) for c in dcols] + [(f, pa.float64()) for f, _ in fields]
                           + ([("text", pa.string())] if kind in ("set", "alias") else []) + [("special", pa.string())])
        meta = {"symbol": name, "type": kind, "dim": dim, "domains": doms, "text": text, "records": nrec, "source": src}
        schema = schema.with_metadata({"capri_gdx": json.dumps(meta)})
        w = pq.ParquetWriter(str(out / f"{name}.parquet"), schema, compression="zstd")
        cols = {c: [] for c in schema.names}

        def flush():
            if cols["special"]:
                w.write_table(pa.table(cols, schema=schema))
            for c in cols:
                cols[c].clear()
        n = 0
        if nrec:
            g.gdxDataReadStrStart(h, i)
            for _ in range(nrec):
                ok, keys, vals, afdim = g.gdxDataReadStr(h)
                if not ok:
                    break
                for c, k in zip(dcols, keys):
                    cols[c].append(_text(k, n_l1))
                sp = []
                for f, pos in fields:
                    v = vals[pos]
                    if v in special:
                        lab, v = special[v]
                        sp.append(f"{f}:{lab}")
                    cols[f].append(float(v))
                if kind in ("set", "alias"):
                    t = int(vals[g.GMS_VAL_LEVEL])
                    cols["text"].append(_text(g.gdxGetElemText(h, t)[1], n_l1) if t else "")
                cols["special"].append(";".join(sp))
                n += 1
                if len(cols["special"]) >= BATCH:
                    flush()
            g.gdxDataReadDone(h)
        flush()
        w.close()
        if n != nrec:
            raise SystemExit(f"{gdx_path.name} {name}: {n} records read of {nrec}")
        listing.append((name, kind, dim, nrec, text, n_l1[0]))
    g.gdxClose(h)
    g.gdxFree(h)
    with open(out / "_symbols.csv", "w", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["symbol", "type", "dim", "records", "text", "latin1_strings"])
        wr.writerows(listing)
    return listing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gdx", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--symbols", default="")
    ap.add_argument("--lib-dir", default=os.environ.get("CAPRI_GDXLIB", str(SOURCES / "gdxlib")))
    a = ap.parse_args()
    syms = set(s for s in a.symbols.split(",") if s) or None
    lst = convert(a.gdx, a.out, a.lib_dir, syms)
    print(f"{a.gdx.name}: {len(lst)} symbols, {sum(x[3] for x in lst)} records -> {a.out}")


if __name__ == "__main__":
    main()

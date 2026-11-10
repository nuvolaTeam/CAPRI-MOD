"""Check tools/build/convert_capri_gdx.py's Parquet files against their GDX file, record by record: every symbol's
records in the GDX's order, the index labels (Latin-1 where not UTF-8, as the converter decodes them), the values
(bit for bit; EPS, +INF, -INF, NA and UNDF through the special column) and the sets' texts; the record counts and the
source's SHA-256 in the metadata. Reads both in batches (bounded memory).

    python tools/check/check_capri_gdx_parquet.py FILE.gdx PARQUET_DIR [--lib-dir DIR]
Exit status 1 at the first difference (printed).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import SOURCES  # noqa: E402
from convert_capri_gdx import TYPES, _text, sha256  # noqa: E402


def check(gdx_path: Path, pdir: Path, lib: str) -> int:
    import pyarrow.parquet as pq
    import gams.core.gdx as g
    h = g.new_gdxHandle_tp()
    g.gdxCreateD(h, lib, g.GMS_SSSIZE)
    g.gdxOpenRead(h, str(gdx_path))
    sv = g.doubleArray(g.GMS_SVIDX_MAX)
    g.gdxGetSpecialValues(h, sv)
    spec = {sv[g.GMS_SVIDX_EPS]: "EPS", sv[g.GMS_SVIDX_PINF]: "+INF", sv[g.GMS_SVIDX_MINF]: "-INF",
            sv[g.GMS_SVIDX_NA]: "NA", sv[g.GMS_SVIDX_UNDEF]: "UNDF"}
    back = {"EPS": 0.0, "+INF": math.inf, "-INF": -math.inf}
    digest = sha256(gdx_path)
    _, nsym, _ = g.gdxSystemInfo(h)
    total = 0
    for i in range(1, nsym + 1):
        _, name, dim, typ = g.gdxSymbolInfo(h, i)
        _, nrec, _, _ = g.gdxSymbolInfoX(h, i)
        kind = TYPES.get(typ, str(typ))
        f = pdir / f"{name}.parquet"
        pf = pq.ParquetFile(str(f))
        meta = json.loads(pf.schema_arrow.metadata[b"capri_gdx"])
        if meta["records"] != nrec or pf.metadata.num_rows != nrec or meta["source"]["sha256"] != digest:
            print(f"{name}: records {nrec} in the GDX, {pf.metadata.num_rows} in {f.name} (metadata {meta['records']}),"
                  f" or another source file")
            return 1
        fields = (["value"] if kind == "parameter" else ["level", "marginal", "lower", "upper", "scale"]
                  if kind in ("variable", "equation") else [])
        pos = {"value": g.GMS_VAL_LEVEL, "level": g.GMS_VAL_LEVEL, "marginal": g.GMS_VAL_MARGINAL,
               "lower": g.GMS_VAL_LOWER, "upper": g.GMS_VAL_UPPER, "scale": g.GMS_VAL_SCALE}
        if nrec:
            g.gdxDataReadStrStart(h, i)
        r = 0
        for batch in pf.iter_batches(batch_size=200_000):
            b = batch.to_pydict()
            for j in range(batch.num_rows):
                _, keys, vals, _ = g.gdxDataReadStr(h)
                cnt = [0]
                if [_text(k, cnt) for k in keys] != [b[f"d{k + 1}"][j] for k in range(dim)]:
                    print(f"{name} record {r}: labels {keys} against {[b[f'd{k + 1}'][j] for k in range(dim)]}")
                    return 1
                sp = dict(x.split(":") for x in b["special"][j].split(";") if x)
                for fld in fields:
                    v, p = vals[pos[fld]], b[fld][j]
                    if v in spec:
                        ok = sp.get(fld) == spec[v] and ((math.isnan(p)) if spec[v] in ("NA", "UNDF")
                                                         else p == back[spec[v]])
                    else:
                        ok = fld not in sp and float(v).hex() == float(p).hex()
                    if not ok:
                        print(f"{name} record {r} {fld}: {v} in the GDX, {p} ({sp.get(fld, '')}) in the Parquet")
                        return 1
                if kind in ("set", "alias"):
                    t = int(vals[g.GMS_VAL_LEVEL])
                    if (_text(g.gdxGetElemText(h, t)[1], cnt) if t else "") != b["text"][j]:
                        print(f"{name} record {r}: element text differs")
                        return 1
                r += 1
        if nrec:
            g.gdxDataReadDone(h)
        total += r
    g.gdxClose(h)
    g.gdxFree(h)
    print(f"{gdx_path.name}: {nsym} symbols, {total} records, identical to {pdir}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gdx", type=Path)
    ap.add_argument("pdir", type=Path)
    ap.add_argument("--lib-dir", default=os.environ.get("CAPRI_GDXLIB", str(SOURCES / "gdxlib")))
    a = ap.parse_args()
    sys.exit(check(a.gdx, a.pdir, a.lib_dir))


if __name__ == "__main__":
    main()

"""CAPRI's sets as instantiated in a CAPMOD run, as CSV: one file per set.

Source: a CAPMOD restart file from the project lead's installation (uploaded as sim_ini_21730.gdx: the endotech
Green Deal 2030 run with base year 2017, written at the simulation start). It holds 1,972 sets, those of CAPRI's
global sets.gms and of the modules loaded in that run, with that run's compile-time switches ($ifi) applied.

Output (CAPRI's own data, read-only; docs/design/CAPTRD_MOD.md section 6):
  capri_reference/sets/<tag>/<SET>.csv      d0, d1, ..., text (one row per element / tuple)
  capri_reference/sets/<tag>/_index.csv     set, dim, records, description

Sets defined only inside CAPTRD (sets_captrd.gms: DOMPOS, GRPC, MrkBaleE, breedAct, ...) are not in a CAPMOD file;
they are ported from sets_captrd.gms separately.

    python tools/build/build_capri_sets_reference.py --src sim_ini_21730.gdx --tag simini_21730
"""
from __future__ import annotations

import os
import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# folder of libgdxcclib64.so (README section 3): --gdxlib or the environment variable CAPRI_GDXLIB
DEFAULT_GDXLIB = os.environ.get("CAPRI_GDXLIB", "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--gdxlib", default=DEFAULT_GDXLIB)
    args = ap.parse_args()
    import gams.core.gdx as g
    out = ROOT / "capri_reference" / "sets" / args.tag
    out.mkdir(parents=True, exist_ok=True)
    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, args.gdxlib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(msg)
    if not g.gdxOpenRead(h, args.src)[0]:
        raise RuntimeError(f"cannot open {args.src}")
    _, nsym, _ = g.gdxSystemInfo(h)
    index = []
    seen = set()
    for i in range(1, nsym + 1):
        _, name, dim, typ = g.gdxSymbolInfo(h, i)
        if typ != g.GMS_DT_SET:
            continue
        _, cnt, _, txt = g.gdxSymbolInfoX(h, i)
        fname = re.sub(r"[^A-Za-z0-9_]", "_", name)
        if fname.lower() in seen:                       # case-insensitive file systems
            fname = f"{fname}__{i}"
        seen.add(fname.lower())
        _, n = g.gdxDataReadStrStart(h, i)
        with open(out / f"{fname}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow([f"d{k}" for k in range(dim)] + ["text"])
            for _ in range(n):
                _, keys, vals, _ = g.gdxDataReadStr(h)
                t = ""
                if vals[g.GMS_VAL_LEVEL]:
                    _, t, _ = g.gdxGetElemText(h, int(vals[g.GMS_VAL_LEVEL]))
                # GDX texts are Latin-1 in CAPRI's files: decode the escaped bytes
                fix = lambda x: (x.encode("utf-8", "surrogateescape").decode("latin-1")
                                 if isinstance(x, str) and any("\udc80" <= ch <= "\udcff" for ch in x) else x)
                w.writerow([fix(k) for k in keys] + [fix(t)])
        index.append((name, fname, dim, n, txt))
    g.gdxClose(h)
    with open(out / "_index.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["set", "file", "dim", "records", "description"])
        w.writerows(index)
    print(f"{len(index)} sets -> {out}")


if __name__ == "__main__":
    main()

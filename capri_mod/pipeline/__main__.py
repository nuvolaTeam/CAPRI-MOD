"""Command line of the data pipeline.

    python -m capri_mod.pipeline fetch --provider eurostat --dataset apro_cpsh1 [--filter geo=AT,BE] [--start 2000]
    python -m capri_mod.pipeline fetch --all [--provider eurostat]      every "available" row of the catalogue
    python -m capri_mod.pipeline list                                    the catalogue
    python -m capri_mod.pipeline manifest [--verify]                     downloads made; --verify checks checksums
    python -m capri_mod.pipeline export --provider eurostat --dataset apro_cpsh1 --out FILE.csv

The store's location: CAPRI_PIPELINE_STORE, else the setting pipeline.store_dir, else capri_data/pipeline/store.
"""
from __future__ import annotations

import argparse
import sys


def _filters(items):
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        vals = [x for x in v.split(",") if x]
        out[k.strip()] = vals if len(vals) > 1 else vals[0]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m capri_mod.pipeline", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--provider")
    f.add_argument("--dataset")
    f.add_argument("--filter", action="append", help="dimension=code[,code...]")
    f.add_argument("--start", type=int)
    f.add_argument("--end", type=int)
    f.add_argument("--all", action="store_true")
    sub.add_parser("list")
    mf = sub.add_parser("manifest")
    mf.add_argument("--verify", action="store_true")
    ex = sub.add_parser("export")
    ex.add_argument("--provider", required=True)
    ex.add_argument("--dataset", required=True)
    ex.add_argument("--stage", default="raw")
    ex.add_argument("--out", required=True)
    ex.add_argument("--all-downloads", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        from capri_mod.pipeline.fetch import fetch, fetch_catalogue
        if a.all:
            res = fetch_catalogue(a.provider, a.dataset)
        else:
            if not (a.provider and a.dataset):
                ap.error("fetch needs --provider and --dataset, or --all")
            res = [fetch(a.provider, a.dataset, _filters(a.filter), a.start, a.end)]
        for r in res:
            print(f"{r.provider}/{r.dataset}: {r.rows} rows, download {r.download_id}, table version {r.table_version}")
    elif a.cmd == "list":
        from capri_mod.pipeline import catalogue
        for e in catalogue.load():
            print(f"{e.provider:9s} {e.dataset:22s} {e.status:20s} {e.capri_items}")
    elif a.cmd == "manifest":
        from capri_mod.pipeline import manifest
        for m in manifest.read():
            ok = ("" if not a.verify else (" checksum ok" if manifest.verify(m) else " CHECKSUM MISMATCH"))
            print(f"{m['download_id']} {m['rows']} rows {m['provider_updated']}{ok}")
    elif a.cmd == "export":
        from capri_mod.pipeline import store
        print(store.export_csv(a.stage, a.provider, a.dataset, a.out, a.all_downloads))
    return 0


if __name__ == "__main__":
    sys.exit(main())

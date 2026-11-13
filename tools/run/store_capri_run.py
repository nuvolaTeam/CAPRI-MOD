"""Store a pair of CAPRI's own runs (a reference and a scenario run from it) in a results store, beside the model's runs
and in the same layout (capri_mod/io_results.py: write_capri_run, capri_rows), so that a run of the model and CAPRI's
are compared on the CAPRI codes in one table.

Each result file's DATAOUT (every record) is read through tools/build/convert_capri_gdx.py (lossless; EPS as 0.0,
+INF as inf) and stored as one partition; the runs' records carry CAPRI's result names, and each run's definition is
the fingerprint of its file (name, SHA-256) and of its META's items for the task "Run scenario with market model"
(date, user, GAMS version, scenario description and every GUI setting, as CAPRI writes them).

    python tools/run/store_capri_run.py REF.gdx SCEN.gdx --reference NAME --scenario NAME [--root DIR] [--note TEXT]
(default root: the setting run.results_dir)
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "build"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

TASK = "Run scenario with market model"


def meta_items(gdx: Path, lib: str) -> dict:
    """META's items of the task TASK (the first region's: they repeat per region), as {item: text}."""
    import gams.core.gdx as g
    h = g.new_gdxHandle_tp()
    g.gdxCreateD(h, lib, g.GMS_SSSIZE)
    g.gdxOpenRead(h, str(gdx))
    ok, idx = g.gdxFindSymbol(h, "META")
    out, first = {}, None
    if ok:
        _, n = g.gdxDataReadStrStart(h, idx)
        for _ in range(n):
            _, k, v, _ = g.gdxDataReadStr(h)
            first = first or k[0]
            if k[0] == first and k[1] == TASK and k[2] == TASK:
                t = int(v[g.GMS_VAL_LEVEL])
                out[k[3]] = g.gdxGetElemText(h, t)[1] if t else ""
        g.gdxDataReadDone(h)
    g.gdxClose(h)
    g.gdxFree(h)
    return out


def main():
    import pandas as pd
    from convert_capri_gdx import convert, sha256
    from paths import SOURCES
    from capri_mod import io_results as R
    from capri_mod.settings import current as _settings
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref_gdx", type=Path)
    ap.add_argument("scen_gdx", type=Path)
    ap.add_argument("--reference", required=True, help="the reference's scenario name (CAPRI's)")
    ap.add_argument("--scenario", required=True, help="the scenario's name (CAPRI's)")
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--lib-dir", default=str(SOURCES / "gdxlib"))
    a = ap.parse_args()
    root = a.root or Path(_settings().get("run.results_dir"))
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    tmp = tempfile.TemporaryDirectory()
    parts, src = [], []
    for f in (a.ref_gdx, a.scen_gdx):
        meta = meta_items(f, a.lib_dir)
        by = int(str(meta.get("Base year", "")).split()[0])
        d = Path(tmp.name) / f.stem
        convert(f, d, a.lib_dir, {"dataOut"})
        pf = d / "dataOut.parquet"
        labels = set(pc.unique(pq.read_table(pf, columns=["d5"]).column("d5")).to_pylist())
        if "BAS" in labels and str(by) in labels:
            raise SystemExit(f"{f.name}: DATAOUT has the year labels BAS and {by}")

        def part(pf=pf, by=by):
            for b in pq.ParquetFile(pf).iter_batches(batch_size=500_000):
                yield R.capri_rows(b.to_pandas(), by)
        parts.append(part)
        src.append({"file": f.name, "sha256": sha256(f), "meta": meta})
        print(f"{f.name}: {pq.ParquetFile(pf).metadata.num_rows} DATAOUT records, years {sorted(labels)}, base year "
              f"{by}, {meta.get('Date and time', '')}", flush=True)
    rows = parts
    rec = R.write_capri_run(rows[0], rows[1], scenario=a.scenario, reference=a.reference, ref_source=src[0],
                            scen_source=src[1], root=root, note=a.note,
                            names={"reference_result_name": a.ref_gdx.stem, "result_name": a.scen_gdx.stem},
                            tmpdir=tmp.name)
    print(f"{'already stored' if rec.get('duplicate') else 'stored'}: {rec['kind']} {rec['scenario']} {rec['run_id'][:12]}"
          f" (reference {rec['reference_run_id'][:12]}), {rec['rows']} rows -> {root}")
    for rid in (rec["reference_run_id"], rec["run_id"]):
        print(rid[:12], "id verified" if R.verify_run(root, rid) else "ID MISMATCH")


if __name__ == "__main__":
    main()

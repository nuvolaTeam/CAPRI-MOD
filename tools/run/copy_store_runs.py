"""Copy scenario runs, with their references, from one results store to another of the same layout
(capri_mod/io_results.py), e.g. a run copy's local store into a clone of the published store.

    python tools/run/copy_store_runs.py SRC_STORE DST_STORE RUN_ID [RUN_ID ...]

RUN_ID: a scenario run's id or a unique prefix of it (12 characters, as RUNS.csv shows). For each run, oldest first:
its reference (unless DST already has that run id) and the scenario: their rows of long, summary and iterations,
their records of runs (seq renumbered after DST's last, every other field as in SRC: the run ids, fingerprints,
created times, names and notes are the run's own), the scenario's metadata folder (meta/<run id>/). A run already in
DST (the same id) is not copied again. Then RUNS.csv is rewritten (io_results.write_catalogue) and every copied id is
recomputed from DST's tables alone (io_results.verify_run); the copy stops with an error if one does not match. SRC is
only read.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from capri_mod import io_results as IO  # noqa: E402


def _rows(root: Path, table: str, run_id: str) -> pd.DataFrame:
    return IO._rows_of(root, table, run_id)


def _append(root: Path, table: str, df: pd.DataFrame, merge: bool = True):
    import pyarrow as pa
    from deltalake import write_deltalake
    if not len(df):
        return
    write_deltalake(str(root / table), pa.Table.from_pandas(df, preserve_index=False), mode="append",
                    **({"schema_mode": "merge"} if merge else {}))


def _resolve(runs: pd.DataFrame, rid: str) -> pd.Series:
    m = runs[runs["run_id"].astype(str).str.startswith(rid)]
    if len(m) != 1:
        raise SystemExit(f"{rid}: {len(m)} runs match in the source store")
    rec = m.iloc[0]
    if rec["kind"] != "scenario":
        raise SystemExit(f"{rid}: a {rec['kind']} run; give the scenario run (its reference comes with it)")
    return rec


def copy_runs(src: Path, dst: Path, ids) -> list:
    src, dst = Path(src), Path(dst)
    sr = IO._runs(src)
    recs = sorted((_resolve(sr, i) for i in ids), key=lambda r: int(r["seq"]))
    copied = []
    for rec in recs:
        dr = IO._runs(dst)
        have = set(dr["run_id"])
        if rec["run_id"] in have:
            print(f"{rec['run_id'][:12]} {rec['result_name']}: already in the destination")
            continue
        seq = int(dr["seq"].max()) + 1 if len(dr) else 0
        out = []
        ref_id = str(rec["reference_run_id"] or "")
        if ref_id and ref_id not in have:
            ref = sr[sr["run_id"] == ref_id]
            if len(ref) != 1:
                raise SystemExit(f"{rec['run_id'][:12]}: its reference {ref_id[:12]} is not in the source store")
            for t in ("long", "summary", "iterations"):
                _append(dst, t, _rows(src, t, ref_id))
            r = ref.iloc[0].to_dict()
            r["seq"] = seq
            out.append(r)
            copied.append(ref_id)
        for t in ("long", "summary", "iterations"):
            _append(dst, t, _rows(src, t, rec["run_id"]))
        r = rec.to_dict()
        r["seq"] = seq + len(out)
        out.append(r)
        _append(dst, "runs", pd.DataFrame(out)[list(IO.RUNS_COLUMNS)])
        ms, md = IO.meta_dir(src, rec["run_id"]), IO.meta_dir(dst, rec["run_id"])
        if ms.exists():
            shutil.copytree(ms, md, dirs_exist_ok=True)
        copied.append(rec["run_id"])
        print(f"{rec['run_id'][:12]} {rec['result_name']} copied (reference {ref_id[:12]}"
              f"{', copied' if len(out) == 2 else ', already there'})")
    IO.write_catalogue(dst)
    for rid in copied:
        if not IO.verify_run(dst, rid):
            raise SystemExit(f"{rid[:12]}: its id does not match its rows and record in the destination")
        print(f"{rid[:12]}: id recomputed from the destination's tables: matches")
    return copied


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("run_ids", nargs="+")
    a = ap.parse_args()
    copy_runs(Path(a.src), Path(a.dst), a.run_ids)

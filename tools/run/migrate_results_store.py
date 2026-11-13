"""Convert a results store of the layout before 7 November 2026 (tables partitioned by scenario and run id, run ids
"<date>T<time>-<commit>", meta/<scenario>/<run id>/) to the current one (capri_mod/io_results.py: each run under the
SHA-256 of its results and its definition, unpartitioned tables, meta/<run id>/).

    python tools/run/migrate_results_store.py OLD_STORE NEW_STORE [--into] [--run OLD_RUN_ID ...]

NEW_STORE must not exist, unless --into: then the runs are added to that store of the current layout (a run already
there, the same id, is stored once). --run converts only the scenario runs of those old ids. Every scenario run of
OLD_STORE (or of --run) is written again with io_results.write_run, oldest first:
its rows, its reference's rows, the summary and iteration records, its metadata (meta.json, settings.toml,
manifest.json) and its record's creation time. The reference keeps its stored fingerprint (reference_fingerprint);
what the scenario adds (scenario_parts) is taken from its metadata as the run script takes it (the overrides on the
command line, the scenario files read). Then each converted run is checked against the old store: the same rows
(their digests), the same records, the same metadata, and its run id recomputed (io_results.verify_run). The old
store is only read. Prints old id -> new id for every run.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from deltalake import DeltaTable  # noqa: E402

from capri_mod import io_results as IO  # noqa: E402


def _old_rows(old: Path, table: str, scenario: str, run_id: str) -> pd.DataFrame:
    p = old / table
    if not p.exists():
        return pd.DataFrame()
    return DeltaTable(str(p)).to_pandas(filters=[("scenario", "=", scenario), ("run_id", "=", run_id)])


def _old_record(old: Path, table: str, scenario: str, run_id: str):
    df = _old_rows(old, table, scenario, run_id)
    return IO.decode_record(df[list(IO.RECORD_COLUMNS)].reset_index(drop=True)) if len(df) else None


def _points(df: pd.DataFrame, point: str) -> pd.DataFrame:
    return df.drop(columns=["scenario", "run_id"]).assign(point=point)


def migrate(old: Path, new: Path, into: bool = False, only: tuple = ()) -> list:
    if new.exists() and not into:
        raise SystemExit(f"{new} exists: give a new folder (or --into to add to it)")
    if into and not (new / "runs").is_dir():
        raise SystemExit(f"{new} is not a results store (no runs table)")
    runs = DeltaTable(str(old / "runs")).to_pandas()
    refs = runs[runs["kind"] == "reference"].set_index(["scenario", "run_id"])
    sel = runs[runs["kind"] == "scenario"]
    if only:
        missing = set(only) - set(sel["run_id"])
        if missing:
            raise SystemExit(f"not scenario runs of {old}: {sorted(missing)}")
        sel = sel[sel["run_id"].isin(only)]
    out = []
    for rec in sel.sort_values("seq").to_dict("records"):
        s, rid, ref, ref_id = rec["scenario"], rec["run_id"], rec["reference"], rec["reference_run_id"]
        base = _old_rows(old, "long", ref, ref_id)
        scen = _old_rows(old, "long", s, rid)
        md_old = old / "meta" / s / rid
        meta = json.loads((md_old / "meta.json").read_text()) if (md_old / "meta.json").is_file() else {}
        man = meta.get("run_manifest") or {}
        sparts = {"overrides": meta.get("scenario_overrides") or {},
                  "inputs": {k: v for k, v in (man.get("inputs") or {}).items()
                             if k.startswith("capri_data/scenarios/")}}
        it = (_old_record(old, "iterations", ref, ref_id), _old_record(old, "iterations", s, rid))
        year = int(scen["year"].iloc[0])
        fp_ref = str(refs.loc[(ref, ref_id), "fingerprint"])
        new_rec = IO.write_run(_points(base, "base"), _points(scen, "scen"), scenario=s, reference=ref, year=year,
                               fingerprint_parts={"commit": (man.get("git") or {}).get("commit") or ""},
                               reference_fingerprint=fp_ref, scenario_parts=sparts, meta=meta, root=new,
                               summary=_old_record(old, "summary", s, rid),
                               iterations=it if it != (None, None) else None, created=str(rec["created"]))
        md_new = IO.meta_dir(new, new_rec["run_id"])
        for f in ("settings.toml", "manifest.json"):
            if (md_old / f).is_file():
                shutil.copy2(md_old / f, md_new / f)
        out.append((s, rid, new_rec["run_id"], ref_id, new_rec["reference_run_id"]))
    return out


def _same(x, y) -> bool:
    """Two decoded records equal, a missing value equal to a missing value (NaN != NaN for ==), types kept."""
    import math
    import numpy as np
    if type(x) is not type(y):
        return False
    if isinstance(x, dict):
        return list(x) == list(y) and all(_same(x[k], y[k]) for k in x)
    if isinstance(x, (list, tuple)):
        return len(x) == len(y) and all(_same(u, v) for u, v in zip(x, y))
    if isinstance(x, np.ndarray):
        return x.shape == y.shape and bool(np.array_equal(x, y, equal_nan=True))
    if isinstance(x, float) and math.isnan(x):
        return math.isnan(y)
    return x == y


def check(old: Path, new: Path, pairs: list) -> list:
    """The converted runs against the old store: rows, records, metadata, run ids."""
    bad = []
    for s, rid, nid, ref_id, nref in pairs:
        rec = IO._runs(new).set_index("run_id").loc[nid]
        for (sc, o_id, n_id) in ((rec["reference"], ref_id, nref), (s, rid, nid)):
            a = _old_rows(old, "long", sc, o_id).drop(columns=["scenario", "run_id"])
            b = IO.read_partition(new, sc, n_id)
            if IO.rows_digest(a) != IO.rows_digest(b) or len(a) != len(b):
                bad.append(f"{sc} {o_id}: rows differ")
            if not IO.verify_run(new, n_id):
                bad.append(f"{sc} {n_id}: run id not recomputed")
            if not _same(_old_record(old, "iterations", sc, o_id), IO._record(new, "iterations", sc, n_id)):
                bad.append(f"{sc} {o_id}: iterations differ")
        if not _same(_old_record(old, "summary", s, rid), IO._record(new, "summary", s, nid)):
            bad.append(f"{s} {rid}: summary differs")
        for f in ("meta.json", "settings.toml", "manifest.json"):
            fo, fn = old / "meta" / s / rid / f, IO.meta_dir(new, nid) / f
            if fo.is_file() and (not fn.is_file() or (json.loads(fo.read_text()) != json.loads(fn.read_text())
                                                      if f.endswith(".json") else fo.read_text() != fn.read_text())):
                bad.append(f"{s} {rid}: {f} differs")
    return bad


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--into", action="store_true")
    ap.add_argument("--run", nargs="+", default=())
    a = ap.parse_args()
    old, new = Path(a.old), Path(a.new)
    pairs = migrate(old, new, a.into, tuple(a.run))
    for s, rid, nid, ref_id, nref in pairs:
        print(f"{s}: {rid} -> {nid}  (reference {ref_id} -> {nref})")
    bad = check(old, new, pairs)
    print("check:", "every run identical, every id recomputed" if not bad else f"{len(bad)} problems")
    for b in bad:
        print("  " + b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

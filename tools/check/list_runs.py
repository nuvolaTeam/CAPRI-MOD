"""The runs of a results store, as CAPRI names its result files (capri_mod/io_results.catalogue: results/RUNS.csv).

    python tools/check/list_runs.py [ROOT] [--scenario S] [--series S] [--label L] [--rewrite]
    python tools/check/list_runs.py [ROOT] --run RUN_ID_PREFIX          # one run: its record (run_record.csv)
    python tools/check/list_runs.py [ROOT] --solves RUN_ID_PREFIX       # its regional solves per iteration (p_INFES)

ROOT: the store (default: the setting run.results_dir). --rewrite rewrites ROOT/RUNS.csv from the store (a store
written before 9 November 2026 has none). --solves: per outer iteration of the baseline and of the scenario, the
regions solved, those whose solve was not optimal (IPOPT's last point kept, as CAPRI keeps a non-optimal solve) and
IPOPT's statuses; recorded for runs from 9 November 2026 on.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from capri_mod import io_results as IO  # noqa: E402


def _root(arg: str) -> Path:
    if arg:
        return Path(arg)
    from capri_mod.settings import defaults
    rd = str(defaults().get("run.results_dir") or "")
    if not rd:
        sys.exit("no store given and the setting run.results_dir is empty")
    return Path(rd) if Path(rd).is_absolute() else ROOT / rd


def _one(runs: pd.DataFrame, prefix: str) -> dict:
    r = runs[runs["run_id"].astype(str).str.startswith(prefix)]
    if len(r) != 1:
        sys.exit(f"run id prefix {prefix}: {len(r)} runs")
    return r.iloc[0].to_dict()


def solves(root: Path, rec: dict) -> pd.DataFrame:
    """Per iteration of the run's baseline and scenario: regions solved, non-optimal solves, IPOPT's statuses."""
    rows = []
    for point, rid, name in (("baseline", rec["reference_run_id"], rec["reference"]),
                             ("scenario", rec["run_id"], rec["scenario"])):
        hist = IO._record(root, "iterations", name, rid) or []
        for h in hist:
            st = h.get("solve_status")
            if st is None:
                continue
            bad = sorted(r for r, v in st.items() if not v.get("optimal", True))
            rows.append({"point": point, "it": h.get("it"), "regions": len(st), "non_optimal": len(bad),
                         "statuses": "; ".join(f"{k} {n}" for k, n in Counter(v.get("status", "") for v in
                                                                              st.values()).most_common()),
                         "regions_non_optimal": ",".join(bad)})
    return pd.DataFrame(rows, columns=["point", "it", "regions", "non_optimal", "statuses", "regions_non_optimal"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default="")
    ap.add_argument("--scenario", default="", help="the runs of a scenario (its name or short name; a substring)")
    ap.add_argument("--series", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--run", default="", help="one run's record (run_record.csv), by a prefix of its run id")
    ap.add_argument("--solves", default="", help="one run's regional solves per iteration, by a prefix of its run id")
    ap.add_argument("--rewrite", action="store_true", help="rewrite ROOT/RUNS.csv from the store")
    a = ap.parse_args()
    root = _root(a.root)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 80)
    if a.run or a.solves:
        rec = _one(IO._runs(root), a.run or a.solves)
        if rec["kind"] != "scenario":
            sys.exit(f"{rec['run_id'][:12]} is a reference; its scenario's record holds the run")
        if a.run:
            f = IO.meta_dir(root, rec["run_id"]) / "run_record.csv"
            if f.exists():
                print(pd.read_csv(f, keep_default_na=False).to_string(index=False))
            else:
                meta = json.loads((IO.meta_dir(root, rec["run_id"]) / "meta.json").read_text())
                c = IO.catalogue(root)
                c = c[c["run_id"] == str(rec["run_id"])[:12]]
                if len(c) == 1:                       # the name and status the catalogue gives it
                    rec.update(result_name=c.iloc[0]["result_name"], status=c.iloc[0]["status"])
                print("(no run_record.csv: a run stored before 9 November 2026; built from meta.json)")
                print(IO.run_record(meta, rec).to_string(index=False))
        else:
            s = solves(root, rec)
            print(s.to_string(index=False) if len(s) else "no solve status recorded (a run stored before "
                                                          "9 November 2026)")
        return
    c = IO.catalogue(root)
    if a.rewrite:
        print(f"written {IO.write_catalogue(root)}")
    if a.scenario:
        c = c[c["scenario"].str.contains(a.scenario, regex=False) | c["result_name"].str.contains(a.scenario,
                                                                                                   regex=False)]
    if a.series:
        c = c[c["series"] == a.series]
    if a.label:
        c = c[c["label"] == a.label]
    print(c.drop(columns=["reference_run_id"]).to_string(index=False))


if __name__ == "__main__":
    main()

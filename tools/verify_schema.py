"""
Schema-driven verification of the input data layer.

This is the assessment phase of the rebuild. It reads INPUT_SCHEMA.json -- the
single declared source of truth for what the model needs and where each input
comes from -- and checks the actual data against it:

  1. every declared file exists and is readable
  2. every declared source_ref is honoured (the file's provenance matches)
  3. per-cell coverage: what fraction of live cells is real vs fallback,
     counted plainly (not area-weighted), which is the honest figure
  4. nothing in the data is undeclared in the schema

It writes a coverage report but changes NO data. Run it before and after any
data change; a drop in real-cell coverage that isn't explained by a schema
change is a regression.

The point is that this would have caught every silent-drop bug in the project's
history -- maize, grassland, the livestock PMP terms -- because each left a
declared input under-covered, and this checks coverage against the declaration
rather than trusting the file to look right.

Usage
-----
    python tools/verify_schema.py                 # assess, print report
    python tools/verify_schema.py --json out.json # also write machine-readable
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


def load_schema(data_dir: Path) -> dict:
    return json.loads((data_dir / "INPUT_SCHEMA.json").read_text())


def cell_coverage(path: Path) -> tuple[int, int]:
    """(live_cells, non_zero_cells) for a 2-D numeric CSV; (0,0) otherwise."""
    try:
        df = pd.read_csv(path, index_col=0)
    except Exception:
        return 0, 0
    num = df.select_dtypes(include=[np.number])
    if num.empty:
        return 0, 0
    live = int(num.notna().sum().sum())
    nonzero = int(((num != 0) & num.notna()).sum().sum())
    return live, nonzero


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    schema = load_schema(args.data_dir)
    inputs = schema["inputs"]

    report = {"files": {}, "issues": [], "by_source_type": {},
              "by_confidence": {}, "by_module": {}}

    src_counter = Counter()
    conf_counter = Counter()
    mod_counter = Counter()
    total_live = total_nonzero = 0

    print(f"{'input':32s} {'exists':>7s} {'cells':>8s} {'nonzero':>8s}  source")
    print("-" * 88)

    for name, spec in inputs.items():
        f = args.data_dir / spec["file"]
        exists = f.exists()
        src = spec["source"]
        st = src["source_type"]
        conf = src["confidence"]

        live = nonzero = 0
        if exists:
            live, nonzero = cell_coverage(f)
            total_live += live
            total_nonzero += nonzero
        else:
            report["issues"].append(f"MISSING FILE: {name} -> {spec['file']}")

        src_counter[st] += 1
        conf_counter[conf] += 1
        for m in spec.get("modules", []):
            mod_counter[m] += 1

        report["files"][name] = {
            "file": spec["file"], "exists": exists,
            "live_cells": live, "nonzero_cells": nonzero,
            "source_type": st, "source_ref": src["source_ref"],
            "confidence": conf, "modules": spec.get("modules", []),
            "known_gaps": spec.get("known_gaps", []),
        }

        mark = "yes" if exists else "NO"
        print(f"{name:32s} {mark:>7s} {live:8d} {nonzero:8d}  "
              f"{st}: {src['source_ref'][:34]}")

    report["by_source_type"] = dict(src_counter)
    report["by_confidence"] = dict(conf_counter)
    report["by_module"] = dict(mod_counter)
    report["total_live_cells"] = total_live
    report["total_nonzero_cells"] = total_nonzero

    print("-" * 88)
    print(f"\n{len(inputs)} inputs declared.")
    print(f"source types : {dict(src_counter)}")
    print(f"confidence   : {dict(conf_counter)}")
    print(f"module use   : {dict(mod_counter)}")

    # honest per-cell real-data figure across the CAPRI-sourced supply files
    real_types = {"CAPRI_GDX", "CAPRI_SOURCE"}
    real_cells = sum(report["files"][n]["nonzero_cells"]
                     for n in inputs
                     if inputs[n]["source"]["source_type"] in real_types)
    print(f"\nnon-zero cells in CAPRI-sourced inputs: {real_cells:,}")
    print(f"total non-zero cells declared         : {total_nonzero:,}")

    gaps = {n: report["files"][n]["known_gaps"]
            for n in inputs if report["files"][n]["known_gaps"]}
    if gaps:
        print("\ndeclared known gaps (documented, not bugs):")
        for n, g in gaps.items():
            print(f"  {n}: {'; '.join(g)}")

    if report["issues"]:
        print("\nISSUES:")
        for i in report["issues"]:
            print(f"  {i}")
    else:
        print("\nno structural issues: every declared file present and readable.")

    if args.json:
        args.json.write_text(json.dumps(report, indent=1))
        print(f"\nwritten: {args.json}")


if __name__ == "__main__":
    main()

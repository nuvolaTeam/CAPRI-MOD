"""The data pipeline's declaration from a builder trace: tools/pipeline/builders.json, read by dodo.py (doit).

tools/check/reproduce_builders.py --trace TRACE.json runs every builder of its list under strace and records the files
each opens. This script turns that record into one entry per builder invocation:

  task      unique task name (the builder, with its arguments where it is invoked more than once)
  builder   tools/build/<builder>.py
  args      its arguments, CAPRI's uploads and work folders as $UP and $WORK (CAPRI_UPLOADS, CAPRI_WORK)
  inputs    the repository files it reads (data under capri_data, settings), its own outputs left out
  code      the Python files of the repository it runs
  external  the files outside the repository it reads (CAPRI's exports and dumps), as $UP / $WORK paths
  outputs   the repository files it writes

and stops where the declaration could not be a pipeline: a file with two writers, or a cycle (a builder depending,
through the files, on its own output). The order is not written: doit derives it from inputs and outputs.

    python tools/check/make_pipeline.py TRACE.json           # writes tools/pipeline/builders.json
    python tools/check/make_pipeline.py TRACE.json --check   # reports, writes nothing
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "pipeline" / "builders.json"
UP = os.environ.get("CAPRI_UPLOADS", "/mnt/user-data/uploads")
WORK = os.environ.get("CAPRI_WORK", "/home/claude/work")
#: the repository's git store: a builder reading the repository's history (convert_sources_to_csv, git show) reads it;
#: those objects are the repository, not an external source
GIT_DIR = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()


def placeholder(p: str) -> str:
    return p.replace(UP, "$UP").replace(WORK, "$WORK")


def build(trace: dict) -> tuple[list, list]:
    names = collections.Counter(k.split()[0] for k in trace)
    tasks, problems = [], []
    for key, d in trace.items():
        parts = key.split()
        builder, args = parts[0], parts[1:]
        name = builder if names[builder] == 1 else builder + ":" + "_".join(
            a.replace("$UP/", "").replace("$WORK/", "").replace("/", ".").lstrip("-") for a in args)[:80]
        outs = sorted(set(d["writes"]) | set(d["rewrites"]))
        ins = sorted(set(d["reads"]) - set(outs))
        # a builder's own temporary files (tempfile) are not sources
        # nor is the repository's git store
        ext = [x for x in d["external"] if not x.startswith(tempfile.gettempdir().rstrip("/") + "/")
               and not (GIT_DIR and x.startswith(GIT_DIR.rstrip("/") + "/"))]
        tasks.append({"task": name, "builder": builder, "args": args, "inputs": ins,
                      "code": sorted(d["code"]), "external": sorted(placeholder(x) for x in ext),
                      "outputs": outs})
    writers = collections.defaultdict(list)
    for t in tasks:
        for f in t["outputs"]:
            writers[f].append(t["task"])
    for f, w in sorted(writers.items()):
        if len(w) > 1:
            problems.append(f"two writers of {f}: {w}")
    # cycles: Tarjan over task -> task edges (writer of an input -> reader)
    by = {t["task"]: t for t in tasks}
    G = collections.defaultdict(set)
    for t in tasks:
        for f in t["inputs"]:
            for w in writers.get(f, ()):
                if w != t["task"]:
                    G[w].add(t["task"])
    idx, low, st, on, comps, c = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(10000)

    def visit(v):
        idx[v] = low[v] = c[0]; c[0] += 1; st.append(v); on.add(v)
        for w in G[v]:
            if w not in idx:
                visit(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            comps.append(comp)
    for v in by:
        if v not in idx:
            visit(v)
    for comp in comps:
        if len(comp) > 1:
            via = sorted({f for a in comp for b in comp if a != b for f in by[b]["inputs"] if a in writers.get(f, ())})
            problems.append(f"cycle of {len(comp)} tasks {sorted(comp)} through {via}")
    return tasks, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    tasks, problems = build(json.load(open(a.trace)))
    n_in = sum(len(t["inputs"]) for t in tasks)
    print(f"{len(tasks)} tasks, {n_in} repository inputs, {sum(len(t['outputs']) for t in tasks)} outputs; "
          f"{len(problems)} problems")
    for p in problems:
        print("  " + p)
    if problems:
        sys.exit(1)
    if not a.check:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"_doc": "the data pipeline, one entry per builder invocation; generated by "
                                   "tools/check/make_pipeline.py from a builder trace; read by dodo.py",
                                   "tasks": tasks}, indent=1) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

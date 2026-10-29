"""The data rebuilt from blank with doit: every builder output removed, the pipeline run, the result compared with git.

A rebuild over the committed files cannot show a cell that no builder writes (a builder that reads a table before
writing it keeps such a cell as it was; docs/design/DATA_PIPELINE_DOIT.md, "How a rebuild is checked"). Here every
output of the pipeline (tools/pipeline/builders.json) whose builder can run (its CAPRI sources present) is deleted
first, so each file must come from its builder and the files it reads; then `doit` runs the pipeline in its own
order, and git compares each file with the committed one, byte for byte.

Run on a clean checkout (the outputs are deleted and rewritten in place):

    python tools/check/rebuild_from_blank.py [--keep-db]

Exit 0 when every file is reproduced; otherwise the files that differ or are missing are listed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "pipeline" / "builders.json"
UP = os.environ.get("CAPRI_UPLOADS", "/mnt/user-data/uploads")
WORK = os.environ.get("CAPRI_WORK", "/home/claude/work")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-db", action="store_true", help="keep doit's state file (.doit.db) instead of starting anew")
    a = ap.parse_args()
    if git("status", "--porcelain", "--untracked-files=no").strip():
        sys.exit("the working tree has changes: run on a clean checkout")
    tasks = json.loads(PIPELINE.read_text())["tasks"]
    exp = lambda x: x.replace("$UP", UP).replace("$WORK", WORK)  # noqa: E731
    runnable = [t for t in tasks
                if all(Path(exp(x)).exists() for x in t["external"] + [a[6:] for a in t["args"] if a.startswith("unzip:")])]
    skipped = [t["task"] for t in tasks if t not in runnable]
    outs = sorted({f for t in runnable for f in t["outputs"]})
    for f in outs:
        (ROOT / f).unlink(missing_ok=True)
    print(f"{len(outs)} outputs of {len(runnable)} tasks removed; {len(skipped)} tasks without their sources: {skipped}")
    if not a.keep_db:
        for p in ROOT.glob(".doit.db*"):
            p.unlink()
    r = subprocess.run([sys.executable, "-m", "doit", "-f", str(ROOT / "dodo.py"), "--dir", str(ROOT), "build"],
                       cwd=ROOT)
    changed = [ln for ln in git("status", "--porcelain", "--untracked-files=all", "--", "capri_data").splitlines()]
    missing = [f for f in outs if not (ROOT / f).exists()]
    print(f"doit exit {r.returncode}; {len(outs) - len(missing)} of {len(outs)} outputs rebuilt; "
          f"{len(changed)} paths under capri_data differ from git")
    for ln in changed[:50]:
        print("  " + ln)
    sys.exit(0 if r.returncode == 0 and not changed and not missing else 1)


if __name__ == "__main__":
    main()

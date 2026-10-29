"""The data pipeline of capri-mod as doit tasks (docs/design/DATA_PIPELINE_DOIT.md).

Every model input under capri_data is written by exactly one builder (tools/build/*.py). tools/pipeline/builders.json
declares, per builder invocation, the files it reads and writes (generated from a traced run by
tools/check/make_pipeline.py); doit derives the order from them, reruns a builder only when one of its inputs, its
code or a CAPRI source it reads has changed (by content, md5) and refuses two writers of one file. The last task checks
the data against their declarations (capri_data/schema, tools/check/validate_data.py).

    doit list                 # the tasks
    doit                      # bring every output up to date, then check the data
    doit build:build_tariffs_2017   # one builder (and what it needs)
    doit forget; doit         # rerun everything (with the outputs emptied first: the rebuild from blank)

CAPRI's exports and dumps live outside the repository: $UP (CAPRI_UPLOADS, default /mnt/user-data/uploads) and $WORK
(CAPRI_WORK, default /home/claude/work). A builder whose external source is missing here is reported and not run.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UP = os.environ.get("CAPRI_UPLOADS", "/mnt/user-data/uploads")
WORK = os.environ.get("CAPRI_WORK", "/home/claude/work")
PIPELINE = ROOT / "tools" / "pipeline" / "builders.json"

DOIT_CONFIG = {"check_file_uptodate": "md5", "default_tasks": ["build", "validate"], "verbosity": 1}


def _expand(s: str) -> str:
    return s.replace("$UP", UP).replace("$WORK", WORK)


def _tasks():
    return json.loads(PIPELINE.read_text())["tasks"]


def _run(cmd):
    """Run a builder; an argument "unzip:Z" stands for the files of zip Z, extracted to a temporary folder (as
    tools/check/reproduce_builders.py runs it)."""
    with tempfile.TemporaryDirectory(prefix="dodo_") as tmp:
        full = []
        for a in cmd:
            if a.startswith("unzip:"):
                with zipfile.ZipFile(a[6:]) as z:
                    z.extractall(tmp)
                    full += sorted(str(Path(tmp) / n) for n in z.namelist() if not n.endswith("/"))
            else:
                full.append(a)
        return subprocess.run(full, cwd=ROOT).returncode == 0


def task_build():
    """One task per builder invocation (tools/pipeline/builders.json)."""
    for t in _tasks():
        args = [_expand(a) for a in t["args"]]
        zips = [a[6:] for a in args if a.startswith("unzip:")]
        ext = [_expand(x) for x in t["external"]] + zips
        missing = [x for x in ext if not Path(x).exists()]
        deps = [str(ROOT / f) for f in t["inputs"] + t["code"]] + [x for x in ext if Path(x).is_file()]
        cmd = [sys.executable, str(ROOT / "tools" / "build" / f"{t['builder']}.py")] + args
        if missing:
            yield {"name": t["task"], "actions": [f"echo 'skipped {t['task']}: missing {missing[0]}' >&2"],
                   "file_dep": [d for d in deps if Path(d).exists()], "uptodate": [False], "verbosity": 2}
            continue
        yield {"name": t["task"], "actions": [(_run, [cmd])], "file_dep": deps,
               "targets": [str(ROOT / f) for f in t["outputs"]], "verbosity": 1}


def task_validate():
    """The data against their declarations (types, keys, references, ranges, rules)."""
    decl = sorted((ROOT / "capri_data" / "schema").glob("*.sql"))
    outs = sorted({str(ROOT / f) for t in _tasks() for f in t["outputs"]})
    return {"actions": [[sys.executable, str(ROOT / "tools" / "check" / "validate_data.py")]],
            "file_dep": [str(p) for p in decl] + [o for o in outs if o.endswith(".csv")],
            "verbosity": 2}

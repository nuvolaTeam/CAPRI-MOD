"""The run manifest: what a run was computed from (the project lead's decision of 29 October 2026).

A run's result records the code (the git commit, the branch and the files that differ from the commit), the settings
(written by the run script beside it), the software (Python and the numerical libraries) and every input file the run
read, each with its SHA-256 and size, so that two results can be traced to their exact inputs. Beyond CAPRI (its runs
record their settings in the GUI's batch file, not the data's state); it changes no result.

Which files: every file opened for reading by the run's own process through Python (an audit hook on "open": pandas'
CSV reader, json, the CSV and Parquet helpers, which also note their Parquet reads, opened by pyarrow outside Python)
and the files noted with note_read. Not recorded: files that only a worker process opens (the regional solves run in
worker processes; their inputs are the main process's, sent to them), the Python code itself (the commit and the
changed files stand for it), and the system's files.

    from capri_mod import run_manifest
    run_manifest.start()                  # before the data are read
    ...
    meta["run_manifest"] = run_manifest.finish()
"""
from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SKIP_SUFFIX = (".py", ".pyc", ".pyo", ".so", ".pth", ".dist-info", ".egg-info", ".typed")
_SKIP_PREFIX = tuple(str(Path(p)) for p in {sys.prefix, sys.base_prefix, sys.exec_prefix}) + (
    "/usr", "/proc", "/sys", "/dev", "/etc", "/lib", "/opt/conda", "/root/.cache")

_state = {"active": False, "hooked": False, "reads": {}, "t0": None}


def _wanted(path: str) -> bool:
    if not path or path.endswith(_SKIP_SUFFIX) or "__pycache__" in path or "/.git/" in path:
        return False
    if path.startswith(_SKIP_PREFIX) and not path.startswith(str(ROOT)):
        return False
    return True


def _hook(event, args):
    if event != "open" or not _state["active"]:
        return
    try:
        path, mode = args[0], args[1]
        if isinstance(path, int):
            return
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if mode is not None and any(c in str(mode) for c in "wax+"):
            return
        if mode is None and len(args) > 2 and isinstance(args[2], int) and args[2] & (os.O_WRONLY | os.O_RDWR):
            return
        p = os.path.abspath(str(path))
        if _wanted(p) and os.path.isfile(p):
            _state["reads"].setdefault(p, None)
    except Exception:                                                    # an audit hook must never raise
        pass


def start() -> None:
    """Begin recording the files the run reads (once per process; the hook stays, recording only while active)."""
    if not _state["hooked"]:
        sys.addaudithook(_hook)
        _state["hooked"] = True
    _state["reads"] = {}
    _state["active"] = True
    _state["t0"] = time.time()


def note_read(path) -> None:
    """Record a file read outside Python's open (Parquet through pyarrow)."""
    if _state["active"]:
        p = os.path.abspath(str(path))
        if _wanted(p):
            _state["reads"].setdefault(p, None)


def _git(*a) -> str:
    try:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def _sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _versions() -> dict:
    out = {"python": platform.python_version()}
    for m in ("numpy", "pandas", "scipy", "casadi", "pyarrow", "duckdb"):
        mod = sys.modules.get(m)
        if mod is not None:
            out[m] = getattr(mod, "__version__", "")
    return out


def finish() -> dict:
    """Stop recording; the manifest: code, software, environment and the inputs read (path, SHA-256, bytes)."""
    _state["active"] = False
    inputs, external = {}, {}
    for p in sorted(_state["reads"]):
        if not os.path.isfile(p):
            continue
        rec = {"sha256": _sha256(p), "bytes": os.path.getsize(p)}
        try:
            inputs[str(Path(p).relative_to(ROOT))] = rec
        except ValueError:
            external[p] = rec
    status = [ln for ln in _git("status", "--porcelain").splitlines() if ln.strip()]
    return {
        "created": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "seconds_recorded": round(time.time() - (_state["t0"] or time.time())),
        "git": {"commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                "data_tree": _git("rev-parse", "HEAD:capri_data"), "changed_files": status},
        "software": _versions(),
        "environment": {"platform": platform.platform(), "cpus": os.cpu_count(),
                        **{k: os.environ.get(k) for k in ("CAPRI_WORKERS", "PYTHONHASHSEED") if k in os.environ}},
        "command": list(sys.argv),
        "inputs": inputs,
        "external_inputs": external,
    }


def compare(a: dict, b: dict) -> dict:
    """What differs between two manifests: commit, changed files, software, and the inputs by hash."""
    ia, ib = a.get("inputs") or {}, b.get("inputs") or {}
    return {
        "commit": (a.get("git", {}).get("commit"), b.get("git", {}).get("commit")),
        "changed_files": (a.get("git", {}).get("changed_files"), b.get("git", {}).get("changed_files")),
        "software": {k: (a.get("software", {}).get(k), b.get("software", {}).get(k))
                     for k in set(a.get("software", {})) | set(b.get("software", {}))
                     if a.get("software", {}).get(k) != b.get("software", {}).get(k)},
        "inputs_only_first": sorted(set(ia) - set(ib)),
        "inputs_only_second": sorted(set(ib) - set(ia)),
        "inputs_differ": sorted(k for k in set(ia) & set(ib) if ia[k]["sha256"] != ib[k]["sha256"]),
    }

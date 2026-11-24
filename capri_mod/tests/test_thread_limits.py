"""The BLAS and OpenMP thread limits (capri_mod/__init__.py THREAD_LIMITS; KNOWN_ISSUES K198): the regional solves
fork one worker per core, and without the limits each worker's OpenBLAS started one thread per core (7 threads in a
forked worker after a BLAS call on 4 cores, the run about twice as long). Each check runs in a fresh process, as the
libraries read the variables when they load."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")


def _py(code, **env):
    e = {k: v for k, v in os.environ.items() if k not in VARS}
    e.update(env, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-W", "always", "-c", code], capture_output=True, text=True, env=e,
                          cwd=str(ROOT), timeout=120)


def test_importing_capri_mod_sets_one_thread_and_keeps_the_users_setting():
    r = _py("import os, capri_mod; print(','.join(os.environ[v] for v in capri_mod.THREAD_LIMITS))")
    assert r.stdout.strip() == "1,1,1", r.stderr
    r = _py("import os, capri_mod; print(os.environ['OPENBLAS_NUM_THREADS'])", OPENBLAS_NUM_THREADS="3")
    assert r.stdout.strip() == "3", r.stderr


def test_numpy_imported_first_is_warned():
    r = _py("import numpy, capri_mod")
    assert "NumPy was imported before capri_mod" in r.stderr
    assert "NumPy was imported before" not in _py("import capri_mod, numpy").stderr


def test_a_forked_worker_runs_its_blas_on_one_thread():
    if not hasattr(os, "fork") or not os.path.isdir("/proc/self/task"):
        import pytest
        pytest.skip("needs fork and /proc")
    code = ("import os, capri_mod, numpy as np\n"
            "a = np.random.rand(1000, 1000)\n"
            "pid = os.fork()\n"
            "if pid == 0:\n"
            "    (a @ a).sum(); print(len(os.listdir('/proc/self/task')), flush=True); os._exit(0)\n"
            "os.waitpid(pid, 0)\n")
    r = _py(code)
    assert r.stdout.strip() == "1", (r.stdout, r.stderr)

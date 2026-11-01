"""supply.nlp_ipopt_library and supply.nlp_omp_threads (capri_mod/supply/ipopt_library.py; register BEYOND-11).

Without a built library: the setting's checks and the detection of other OpenMP runtimes. With one (the environment
variable CAPRI_TEST_IPOPT_LIBRARY names an IPOPT with SPRAL in OpenMP, tools/solvers/build_ipopt_spral_omp.py): in a
fresh process, the library is loaded in place of CasADi's, SPRAL solves on two threads with the optimum of CasADi's
MUMPS, a forked worker solves after a one-thread parent, and a parent that ran two threads refuses to fork.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from capri_mod import settings
from capri_mod.supply import ipopt_library as il

ROOT = Path(__file__).resolve().parents[2]

MAPS = """\
7f00-7f01 r-xp 00000000 08:01 1 /usr/lib/x86_64-linux-gnu/libgomp.so.1.0.0
7f02-7f03 r-xp 00000000 08:01 2 /site-packages/casadi/libgomp-870cb1d0.so.1.0.0
7f04-7f05 r-xp 00000000 08:01 3 /site-packages/torch/lib/libomp.so
7f06-7f07 r-xp 00000000 08:01 4 /opt/intel/lib/libiomp5.so
7f08-7f09 r-xp 00000000 08:01 5 /usr/lib/x86_64-linux-gnu/libgfortran.so.5.0.0
7f0a-7f0b rw-p 00000000 00:00 0 [heap]
"""


def test_other_openmp_runtimes_found_and_own_left_out():
    found = il.other_openmp_runtimes(MAPS, own="/usr/lib/x86_64-linux-gnu/libgomp.so.1.0.0")
    assert found == ["/opt/intel/lib/libiomp5.so", "/site-packages/casadi/libgomp-870cb1d0.so.1.0.0",
                     "/site-packages/torch/lib/libomp.so"]


def test_defaults_keep_casadis_ipopt():
    d = settings.defaults()
    assert d.get("supply.nlp_ipopt_library") == ""
    assert d.get("supply.nlp_omp_threads") == 1


def test_a_missing_library_stops_before_any_solve(tmp_path):
    from capri_mod.supply.capri_regional_nlp import linear_solver_options
    with settings.override({"supply.nlp_ipopt_library": str(tmp_path / "libipopt.so.3"),
                            "supply.nlp_linear_solver": "spral"}):
        with pytest.raises(FileNotFoundError, match="build_ipopt_spral_omp"):
            linear_solver_options()


CHILD = textwrap.dedent(r"""
    import json, os, sys, multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    sys.path.insert(0, sys.argv[2])
    lib = sys.argv[1]
    from capri_mod import settings
    from capri_mod.supply import ipopt_library as il
    out = {}
    with settings.override({"supply.nlp_ipopt_library": lib, "supply.nlp_linear_solver": "spral",
                            "supply.nlp_omp_threads": 2}):
        from capri_mod.supply.capri_regional_nlp import linear_solver_options
        opts = linear_solver_options()
        import casadi as ca
        out["loaded"] = il.loaded()
        out["ipopt_files"] = il._ipopt_in_process()
        out["others"] = il.other_openmp_runtimes()
        # a small convex QP with a known optimum: min sum (x - c)^2 + x' A x, s.t. sum x = 1, x >= 0
        n = 300
        x = ca.MX.sym("x", n)
        c = ca.DM([((i * 37) % 11) / 10.0 for i in range(n)])
        f = ca.sumsqr(x - c) + 0.1 * ca.sumsqr(x[1:] - x[:-1])
        S = ca.nlpsol("S", "ipopt", {"x": x, "f": f, "g": ca.sum1(x)},
                      {"print_time": 0, "ipopt.print_level": 0, "ipopt.tol": 1e-10, **opts})
        def solve():
            r = S(x0=0, lbg=1, ubg=1, lbx=0)
            return float(r["f"]), S.stats()["return_status"]
        il.for_parent(2, 2)                         # a parent that forks: one thread
        out["parent"] = solve()
        def child(_):
            il.for_worker()
            return solve() + (il.threads(),)
        with ProcessPoolExecutor(2, mp_context=mp.get_context("fork")) as ex:
            out["children"] = list(ex.map(child, range(2), timeout=120))
        il.for_parent(1, 1)                         # no workers: the threads here
        out["threads_parent"] = il.threads()
        out["threaded"] = solve()
        try:
            il.for_parent(2, 2)
            out["refused"] = False
        except RuntimeError:
            out["refused"] = True
    print("RESULT " + json.dumps(out))
""")


@pytest.mark.skipif(not os.environ.get("CAPRI_TEST_IPOPT_LIBRARY"),
                    reason="CAPRI_TEST_IPOPT_LIBRARY (an IPOPT with SPRAL in OpenMP) not set")
def test_the_openmp_ipopt_in_a_fresh_process(tmp_path):
    import json
    lib = os.environ["CAPRI_TEST_IPOPT_LIBRARY"]
    script = tmp_path / "child.py"
    script.write_text(CHILD)
    env = {k: v for k, v in os.environ.items() if not k.startswith("OMP_")}
    p = subprocess.run([sys.executable, str(script), lib, str(ROOT)], capture_output=True, text=True, timeout=600,
                       env=env)
    line = [ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")]
    assert line, p.stdout + p.stderr
    out = json.loads(line[0][7:])
    assert [os.path.realpath(f) for f in out["ipopt_files"]] == [os.path.realpath(lib)]   # not CasADi's
    assert out["others"] == []
    f0, st0 = out["parent"]
    assert st0 == "Solve_Succeeded"
    for f, st, n in out["children"]:
        assert st == "Solve_Succeeded" and n == 2 and abs(f - f0) <= 1e-9 * max(1.0, abs(f0))
    assert out["threads_parent"] == 2
    assert out["threaded"][1] == "Solve_Succeeded" and abs(out["threaded"][0] - f0) <= 1e-9 * max(1.0, abs(f0))
    assert out["refused"] is True
    # the same problem with CasADi's IPOPT and MUMPS, in this process
    import casadi as ca
    n = 300
    x = ca.MX.sym("x", n)
    c = ca.DM([((i * 37) % 11) / 10.0 for i in range(n)])
    f = ca.sumsqr(x - c) + 0.1 * ca.sumsqr(x[1:] - x[:-1])
    S = ca.nlpsol("S", "ipopt", {"x": x, "f": f, "g": ca.sum1(x)},
                  {"print_time": 0, "ipopt.print_level": 0, "ipopt.tol": 1e-10})
    fm = float(S(x0=0, lbg=1, ubg=1, lbx=0)["f"])
    assert abs(fm - f0) <= 1e-8 * max(1.0, abs(fm))


def test_spral_with_casadis_own_ipopt_in_a_fresh_process(tmp_path):
    """SPRAL with CasADi's own IPOPT (no library of its own): the OpenMP environment is prepared before CasADi's
    plugin loads; with PyPI's CasADi (no OpenMP in its IPOPT) no runtime is attached and the thread calls do nothing."""
    import json
    script = tmp_path / "builtin.py"
    script.write_text(textwrap.dedent(r'''
        import json, os, sys
        sys.path.insert(0, sys.argv[1])
        from capri_mod import settings
        from capri_mod.supply import ipopt_library as il
        with settings.override({"supply.nlp_linear_solver": "spral"}):
            from capri_mod.supply.capri_regional_nlp import linear_solver_options
            opts = linear_solver_options()
            import casadi as ca
            x = ca.MX.sym("x", 3)
            S = ca.nlpsol("S", "ipopt", {"x": x, "f": ca.sumsqr(x - 1)}, {"print_time": 0, "ipopt.print_level": 0, **opts})
            r = S(x0=0)
            il.for_parent(2, 2)
            casadi_gomp = [f for f in il._mapped() if os.path.basename(f).startswith("libgomp")
                           and "casadi" in f and "libuno" not in f]
            print("RESULT " + json.dumps({"active": il.active(), "env": os.environ.get("OMP_CANCELLATION"),
                                          "status": S.stats()["return_status"], "gomp": il._OWN_GOMP,
                                          "casadi_gomp": casadi_gomp}))
    '''))
    env = {k: v for k, v in os.environ.items() if not k.startswith("OMP_")}
    p = subprocess.run([sys.executable, str(script), str(ROOT)], capture_output=True, text=True, timeout=300, env=env)
    line = [ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")]
    assert line, p.stdout + p.stderr
    out = json.loads(line[0][7:])
    assert out["active"] is True and out["env"] == "TRUE" and out["status"] == "Solve_Succeeded"
    if not out["casadi_gomp"]:                       # PyPI's CasADi: no OpenMP in its IPOPT
        assert out["gomp"] is None

"""Run capri_mod/tests without pytest (the sandbox has no internet to install it).

Provides a minimal pytest stand-in for what the tests use - session-scoped fixtures and
pytest.raises - discovers the test functions, splits them across parallel worker processes
and reports every failure with its traceback. Replaces the serial runner that needed an
external pytest shim on the path (lost with /tmp on sandbox resets).

Usage:  python tools/run_tests.py [--parts 4] [-k substring]
Exit code 0 when all selected tests pass.
"""
import argparse
import contextlib
import importlib
import inspect
import json
import subprocess
import sys
import time
import traceback
import types
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _install_pytest_standin():
    if "pytest" in sys.modules:
        return
    # the stand-in even when pytest is installed: this runner resolves the fixtures itself (a real pytest
    # fixture is not a plain function in pytest >= 8.4); python -m pytest runs the same tests with pytest
    m = types.ModuleType("pytest")

    def fixture(*args, **kwargs):
        def mark(fn):
            fn._is_fixture = True
            return fn
        if args and callable(args[0]):
            return mark(args[0])
        return mark

    @contextlib.contextmanager
    def raises(exc, *a, **k):
        try:
            yield
        except exc:
            return
        raise AssertionError(f"DID NOT RAISE {exc!r}")

    m.fixture = fixture
    m.raises = raises
    m.main = lambda *a, **k: 0
    sys.modules["pytest"] = m


def _collect(selector=None):
    _install_pytest_standin()
    sys.path.insert(0, str(ROOT))
    mod = importlib.import_module("capri_mod.tests.test_capri")
    tests = [(n, f) for n, f in inspect.getmembers(mod, inspect.isfunction)
             if n.startswith("test_") and f.__module__ == mod.__name__]
    tests.sort(key=lambda nf: inspect.getsourcelines(nf[1])[1])
    if selector:
        tests = [t for t in tests if selector in t[0]]
    fixtures = {n: getattr(f, "__wrapped__", f) for n, f in inspect.getmembers(mod, inspect.isfunction)
                if getattr(f, "_is_fixture", False)}
    return tests, fixtures


def _worker(part, parts, selector):
    warnings.filterwarnings("ignore")
    tests, fixtures = _collect(selector)
    cache, out = {}, []
    for i, (name, fn) in enumerate(tests):
        if i % parts != part:
            continue
        t0 = time.time()
        try:
            kwargs = {}
            for p in inspect.signature(fn).parameters:
                if p not in cache:
                    cache[p] = fixtures[p]()
                kwargs[p] = cache[p]
            fn(**kwargs)
            out.append({"test": name, "ok": True, "s": round(time.time() - t0, 1)})
        except Exception:
            out.append({"test": name, "ok": False, "s": round(time.time() - t0, 1),
                        "tb": traceback.format_exc()[-1500:]})
    print("@@RESULT@@" + json.dumps(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", type=int, default=4)
    ap.add_argument("-k", default=None)
    ap.add_argument("--worker", type=int, default=None)
    a = ap.parse_args()
    if a.worker is not None:
        _worker(a.worker, a.parts, a.k)
        return 0
    t0 = time.time()
    procs = [subprocess.Popen([sys.executable, __file__, "--worker", str(p), "--parts", str(a.parts)]
                              + (["-k", a.k] if a.k else []), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, cwd=str(ROOT)) for p in range(a.parts)]
    results = []
    for p in procs:
        stdout, _ = p.communicate()
        line = next((l for l in stdout.splitlines() if l.startswith("@@RESULT@@")), None)
        if line is None:
            results.append({"test": f"<worker crashed, exit {p.returncode}>", "ok": False, "s": 0, "tb": stdout[-1500:]})
        else:
            results += json.loads(line[len("@@RESULT@@"):])
    fails = [r for r in results if not r["ok"]]
    for r in fails:
        print(f"FAIL {r['test']}\n{r.get('tb', '')}\n")
    print(f"{len(results) - len(fails)}/{len(results)} passed in {time.time() - t0:.0f} s ({a.parts} parallel parts)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

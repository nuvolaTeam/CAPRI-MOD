"""Another IPOPT library under CasADi's IPOPT interface (supply.nlp_ipopt_library), and its OpenMP threads
(supply.nlp_omp_threads). Not CAPRI's (CAPRI solves with CONOPT in GAMS); register BEYOND-11.

The use: IPOPT with SPRAL's OpenMP factorisation (tools/solvers/build_ipopt_spral_omp.py). CasADi's wheel builds SPRAL
without OpenMP (CasADi 3.8.1's CMakeLists.txt: --disable-openmp; no reason given there), so its IPOPT factorises on one
thread with SPRAL.

How the library is used. CasADi's interface plugin (libcasadi_nlpsol_ipopt.so) needs libipopt.so.3 and looks for it
next to itself (RPATH $ORIGIN). A library of the same soname already in the process is the one the dynamic linker uses,
so the library named here is loaded (RTLD_GLOBAL) before the process's first IPOPT solve, and CasADi's plugin is then
loaded against it. Once CasADi's own libipopt is in the process it is too late: that raises here. The library is
loaded in the process that starts the run, so the supply model's forked workers inherit it.

OpenMP inside the model's process structure (what makes a wheel's OpenMP awkward, measured or read here):

- SPRAL's factorisation fails without OpenMP cancellation (SSIDS flag -53, ssids.f90 l. 1448-1452), which the GNU
  OpenMP runtime reads from OMP_CANCELLATION when it is loaded: set here before the library is loaded, and checked
  after (an OpenMP runtime loaded earlier by another library would have read the environment already).
- OMP_PROC_BIND: SPRAL warns without it (flag 50, a warning, ssids.f90 l. 1454) but every worker process would bind its
  threads to the same first cores; left to the environment (not set here).
- fork: the supply model forks its workers (supply_module.SupplyModule._solve_regions). A process that has run an
  OpenMP parallel region with more than one thread leaves its children hung at their first parallel region (GNU
  libgomp; checked 31 October 2026 with a two-thread region before a fork: the children hung, with one thread they ran).
  So a process that forks solves with one thread, and the threads go to the workers: set_threads below, called with the
  worker count by SupplyModule (the starting process: supply.nlp_omp_threads only where it runs without workers).
- BLAS inside SPRAL: the build's OpenBLAS uses the same OpenMP runtime (USE_OPENMP=1), so BLAS called inside SPRAL's
  threads runs on the calling thread.
- other OpenMP runtimes and runtime libraries in the process (wheels vendor their own: CasADi's libgomp-870cb1d0 for
  its Uno plugin, libgfortran copies in numpy, scipy and CasADi; scikit-learn or PyTorch would bring theirs, an MKL
  numpy Intel's libiomp5, which also answers to GNU's GOMP_ entry points). The model's process has no OpenMP runtime
  today (checked 31 October 2026: numpy, scipy, pandas, pyarrow, CasADi with its IPOPT); this library brings the
  system's GNU libgomp.so.1 and libgfortran.so.5. Three guards:
  (1) the build hides the symbols of its static OpenBLAS, METIS 5 and SPRAL (--exclude-libs): nothing else binds to
      them (CasADi's MUMPS uses its own METIS 4 under the same METIS_ names);
  (2) the library is loaded RTLD_LOCAL: its symbols stay out of the process's global scope. Not RTLD_DEEPBIND (which
      CasADi uses for HSL libraries, its IPOPT patch to IpLibraryLoader.cpp): under it the GNU OpenMP runtime loaded
      with the library did not see the environment (omp_get_cancellation 0 with OMP_CANCELLATION=TRUE set before the
      process started; 1 without DEEPBIND; checked 1 November 2026). Its calls to GOMP_* and omp_* are bound to
      libgomp's versioned symbols (GOMP_4.0, OMP_4.0, ...); a runtime in the global scope (LD_PRELOAD, or a library
      loaded RTLD_GLOBAL) could still take them, which the check of cancellation below and (3) would show;
  (3) the other OpenMP runtimes in the process are reported (other_openmp_runtimes): each has its own threads, which
      set_threads does not control, and the fork rule above holds for them too.
"""
from __future__ import annotations

import ctypes
import os
import re
import warnings
from pathlib import Path
from typing import Optional

_LOADED: Optional[str] = None
_GOMP = None
_OWN_GOMP: Optional[str] = None
_THREADS = 1
_THREADED_PARENT = False


#: the file names of OpenMP runtimes (GNU, LLVM, Intel; a wheel's vendored copy carries a hash: libgomp-870cb1d0.so)
_OMP_RUNTIMES = re.compile(r"^lib(gomp|omp|iomp5|iomp|kmp)([-.].*)?\.so")


def _mapped(maps: Optional[str] = None) -> list:
    """The files mapped into this process (Linux: /proc/self/maps; elsewhere nothing is known)."""
    try:
        if maps is None:
            with open("/proc/self/maps", encoding="utf-8", errors="replace") as fh:
                maps = fh.read()
    except OSError:
        return []
    return sorted({ln.split()[-1] for ln in maps.splitlines() if "/" in ln and len(ln.split()) >= 6})


def _ipopt_in_process() -> list:
    """The libipopt files mapped into this process."""
    return [f for f in _mapped() if os.path.basename(f).startswith("libipopt.so")]


def other_openmp_runtimes(maps: Optional[str] = None, own: Optional[str] = None) -> list:
    """The OpenMP runtimes in the process other than the library's own (own: its libgomp's path)."""
    own_ = os.path.realpath(own) if own else (os.path.realpath(_OWN_GOMP) if _OWN_GOMP else None)
    return [f for f in _mapped(maps) if _OMP_RUNTIMES.match(os.path.basename(f))
            and os.path.realpath(f) != own_]


def resolve(path: str) -> Path:
    """The library's path: absolute, or relative to the repository root (where pyproject.toml is)."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        root = next((q for q in Path(__file__).resolve().parents if (q / "pyproject.toml").exists()), Path.cwd())
        p = root / p
    return p.resolve()


def ensure_loaded(path: str) -> None:
    """Load the IPOPT library at path (once per process) before CasADi's IPOPT interface is loaded."""
    global _LOADED, _GOMP, _OWN_GOMP
    p = str(resolve(path))
    if _LOADED == p:
        return
    if _LOADED is not None:
        raise RuntimeError(f"supply.nlp_ipopt_library: {_LOADED} is loaded in this process; {p} cannot replace it")
    if not os.path.isfile(p):
        raise FileNotFoundError(f"supply.nlp_ipopt_library = {path!r}: no file {p} "
                                f"(tools/solvers/build_ipopt_spral_omp.py builds it)")
    present = [f for f in _ipopt_in_process() if os.path.realpath(f) != os.path.realpath(p)]
    if present:
        raise RuntimeError(f"supply.nlp_ipopt_library = {path!r}: another IPOPT is already loaded in this process "
                           f"({', '.join(present)}); the setting has to be in force before the first IPOPT solve")
    os.environ.setdefault("OMP_CANCELLATION", "TRUE")
    before = set(_mapped())
    ctypes.CDLL(p, mode=ctypes.RTLD_LOCAL)
    _LOADED = p
    # its OpenMP runtime: the GNU libgomp.so.1 mapped with it (or found already in the process under that name)
    gomp = [f for f in _mapped() if os.path.basename(f).startswith("libgomp.so")]
    new = [f for f in gomp if f not in before]
    _OWN_GOMP = (new or gomp or [None])[0]
    _GOMP = ctypes.CDLL(_OWN_GOMP) if _OWN_GOMP else None       # None: an IPOPT without OpenMP
    others = other_openmp_runtimes()
    if others:
        warnings.warn("supply.nlp_ipopt_library: other OpenMP runtimes in this process (" + ", ".join(others) +
                      "): they keep their own threads, which supply.nlp_omp_threads does not set, and a process that "
                      "ran their parallel regions on several threads would hang its forked workers likewise",
                      RuntimeWarning, stacklevel=2)
    if _GOMP is not None:
        if not _GOMP.omp_get_cancellation():
            raise RuntimeError("OpenMP cancellation is off in this process (OMP_CANCELLATION="
                               f"{os.environ.get('OMP_CANCELLATION')!r}, or an OpenMP runtime loaded before the "
                               "IPOPT library read it): SPRAL's factorisation needs it (OMP_CANCELLATION=TRUE)")
        _GOMP.omp_set_num_threads(1)


def loaded() -> Optional[str]:
    return _LOADED


def set_threads(n: int) -> None:
    """This process's OpenMP threads for the linear solver (one where no OpenMP runtime is loaded: nothing to do)."""
    global _THREADS
    _THREADS = max(1, int(n))
    if _GOMP is not None:
        _GOMP.omp_set_num_threads(_THREADS)


def threads() -> int:
    return _THREADS


def for_parent(workers: int, configured: int) -> None:
    """The starting process before a regional pass with `workers` workers: one thread where it forks (now or in a
    later pass: `configured` is the worker setting), else supply.nlp_omp_threads. A process that has used more than
    one thread may not fork: raises (the hang it would cause is silent)."""
    global _THREADED_PARENT
    if _GOMP is None:
        return
    if workers > 1:
        if _THREADED_PARENT:
            raise RuntimeError("the process has run OpenMP with more than one thread and would now fork workers, "
                               "whose OpenMP would hang (GNU libgomp): run.n_workers / CAPRI_WORKERS = 1 or "
                               "supply.nlp_omp_threads = 1")
        set_threads(1)
        return
    from capri_mod.settings import current as _settings
    n = int(_settings().get("supply.nlp_omp_threads"))
    if configured > 1 or n <= 1:
        set_threads(1)
    else:
        set_threads(n)
        _THREADED_PARENT = True


def for_worker() -> None:
    """A forked worker process: supply.nlp_omp_threads."""
    if _GOMP is None:
        return
    from capri_mod.settings import current as _settings
    set_threads(int(_settings().get("supply.nlp_omp_threads")))

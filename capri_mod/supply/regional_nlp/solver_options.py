r"""The regional NLP's solver caches, the problem's fingerprint and the linear solver's options (moved from
capri_mod/supply/capri_regional_nlp.py as they were, 26 November 2026).
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import numpy as np

from capri_mod.settings import current as _settings   # the numerical settings




#: IPOPT solvers by the structure of the problem (SOLVER CACHE). Every data value of the model enters its CasADi graph
#: as a parameter, so two builds with the same structure (columns, rows, feeds, groups, options) give the same graph
#: whatever the numbers; the graph's serialisation is the key. A data value left as a constant only costs a cache miss,
#: never a wrong solve. The cache is per process: the regional solves' worker processes are forked for each round
#: of solves, so it serves the solves of a region within a round and, run in one process, across rounds. Least recently
#: used entries go beyond CAPRI_NLP_CACHE (default 64; about 6 MB each). (Sending the workers' solvers back to the main
#: process was tried: the full run ran out of memory.)
_SOLVERS: "OrderedDict[tuple, object]" = OrderedDict()
#: the Lagrangian's Hessian and the rows' Jacobian per graph, for CapriRegionalNLP.response
_SENS: "OrderedDict[str, tuple]" = OrderedDict()
#: the objective's blocks per graph, for CapriRegionalNLP.objective_parts (built once per structure, as the solvers)
_BLOCKS: "OrderedDict[str, object]" = OrderedDict()
# IPOPT's iteration limits, tolerances and CPU guard, and the solver cache size, are settings
# (capri_mod/settings/defaults.toml [supply] nlp_*, [run] nlp_cache_size)
CACHE_STATS = {"hit": 0, "miss": 0}


#: the KKT step's functions per graph (the Lagrangian's gradient's and the rows' directional derivatives in p)
_KKT: "OrderedDict[str, tuple]" = OrderedDict()


def _feed_hash(h, o, depth=0):
    """Everything in o that a solve can read, in a fixed order, into the hash h: arrays by dtype, shape and bytes,
    floats exactly, containers in order (dicts and sets sorted by key), objects by their attributes."""
    if depth > 12:
        h.update(b"<deep>")
        return
    if o is None or isinstance(o, (bool, int, str, bytes)):
        h.update(repr((type(o).__name__, o)).encode())
    elif isinstance(o, float):
        h.update(b"f" + np.float64(o).tobytes())
    elif isinstance(o, np.generic):
        h.update(repr(o.dtype).encode() + np.asarray(o).tobytes())
    elif isinstance(o, np.ndarray):
        a = np.ascontiguousarray(o)
        if a.dtype == object:
            h.update(b"objarr" + repr(a.shape).encode())
            for v in a.ravel():
                _feed_hash(h, v, depth + 1)
        else:
            h.update(repr((a.dtype.str, a.shape)).encode() + a.tobytes())
    elif isinstance(o, (list, tuple)):
        h.update(b"(" + str(len(o)).encode())
        for v in o:
            _feed_hash(h, v, depth + 1)
        h.update(b")")
    elif isinstance(o, dict):
        h.update(b"{" + str(len(o)).encode())
        for k in sorted(o, key=repr):
            h.update(repr(k).encode())
            _feed_hash(h, o[k], depth + 1)
        h.update(b"}")
    elif isinstance(o, (set, frozenset)):
        _feed_hash(h, sorted(o, key=repr), depth + 1)
    elif type(o).__name__ == "DM" and hasattr(o, "full"):          # CasADi numbers
        _feed_hash(h, np.asarray(o.full()), depth + 1)
    elif hasattr(o, "to_numpy") and hasattr(o, "index"):          # pandas
        _feed_hash(h, (type(o).__name__, list(o.index), list(getattr(o, "columns", [])), o.to_numpy()), depth + 1)
    elif hasattr(o, "__dict__"):
        h.update(type(o).__qualname__.encode())
        _feed_hash(h, vars(o), depth + 1)
    else:
        h.update(repr(o).encode())                                  # (a CasADi object: its printed expression)


def problem_fingerprint(spec, kw, opts) -> str:
    """A digest of one IPOPT solve's inputs: the problem specification, the start, bounds, parameters and warm-start
    multipliers, and the options. Two solves with the same digest give the same result (IPOPT is deterministic)."""
    import hashlib
    h = hashlib.sha256()
    _feed_hash(h, spec)
    _feed_hash(h, kw)
    _feed_hash(h, opts)
    return h.hexdigest()


def linear_solver_options() -> dict:
    """IPOPT's linear solver options from supply.nlp_linear_solver / supply.nlp_hsllib, for every IPOPT solve of the
    model. MUMPS (the default) adds no option, so its solver objects and cache keys are those of before the setting; an
    HSL solver needs its library, and a missing one stops here rather than IPOPT failing in every region (IPOPT returns
    Invalid_Option, which the regional fallbacks would treat as a failed solve)."""
    from capri_mod.settings import current as _settings
    lib_ = str(_settings().get("supply.nlp_ipopt_library") or "").strip()
    if lib_:
        # another IPOPT library (an IPOPT with SPRAL in OpenMP), loaded before the first IPOPT solve of the process
        # and its OpenMP set up (capri_mod/utils/ipopt_library.py)
        from capri_mod.utils import ipopt_library as _il
        _il.ensure_loaded(lib_)
    ls = str(_settings().get("supply.nlp_linear_solver")).strip().lower()
    if ls == "mumps":
        if lib_:
            raise ValueError(f"supply.nlp_ipopt_library = {lib_!r} is an IPOPT without MUMPS "
                             "(tools/solvers/build_ipopt_spral_omp.py): supply.nlp_linear_solver = \"spral\"")
        return {}
    if ls == "spral":
        # SPRAL (BSD licence) is part of CasADi's IPOPT. CasADi 3.8.1 builds it without OpenMP: libipopt carries
        # SPRAL's omp_* stubs and no OpenMP runtime, so it runs on one thread (checked 30 October 2026); SPRAL in
        # OpenMP comes with supply.nlp_ipopt_library or with a CasADi built with it (its environment and threads:
        # ipopt_library.py). Until 31 October 2026 this set OMP_CANCELLATION, OMP_PROC_BIND and OMP_NUM_THREADS here,
        # which PyPI's CasADi does not read (no OpenMP runtime)
        if not lib_:
            from capri_mod.utils import ipopt_library as _il
            _il.prepare_builtin()
        return {"ipopt.linear_solver": "spral"}
    if ls not in ("ma27", "ma57", "ma77", "ma86", "ma97"):
        raise ValueError(f"supply.nlp_linear_solver = {ls!r}: mumps, spral, ma27, ma57, ma77, ma86 or ma97")
    lib = str(_settings().get("supply.nlp_hsllib")).strip()
    if not lib or not os.path.isfile(lib):
        raise FileNotFoundError(f"supply.nlp_linear_solver = {ls!r} needs the HSL library: supply.nlp_hsllib = {lib!r}")
    # CoinHSL is compiled with OpenMP (MA86, MA97, and the BLAS it may carry): its OpenMP runtime starts when IPOPT
    # first loads the library and reads OMP_NUM_THREADS then. The regional solves fork worker processes, and GNU
    # OpenMP hangs a forked child of a process that has run on several threads (capri_mod/utils/ipopt_library.py), so
    # one thread unless the user set the variable (2 November 2026, with MA27 the project lead's solver for his runs;
    # since 24 November 2026 capri_mod/__init__.py sets it on import, with OpenBLAS's and MKL's, so this is a fallback)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    return {"ipopt.linear_solver": ls, "ipopt.hsllib": lib}


def _cache_max():
    """Solver objects kept: the setting run.nlp_cache_size."""
    from capri_mod.settings import current as _settings
    return int(_settings().get("run.nlp_cache_size"))

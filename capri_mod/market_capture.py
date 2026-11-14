"""G3.1 (docs/design/G3_SYSTEM.md): one market solve written to <folder>/market_NNN.pkl for
tools/check/replay_market.py (on with diagnostics.capture_market_dir; MarketModule._solve_captured).

Written: the module before the solve (its whole state: par, sv, seen, ev, data, caches), the solve's arguments, the
run's settings, and after it the equilibrium and the module's warm-start state (sv). The module's attributes are stored
once each by content (<folder>/blobs/<sha256>.pkl, referenced from the module's pickle as persistent ids): the data and
the blocks' caches do not change between solves. Outside capri_mod/market, whose modules read and write no files.
"""
from __future__ import annotations

import hashlib
import io
import pickle
from pathlib import Path


def capture_solve(module, folder, args: dict, settings, solve):
    """Pickle the module, run solve() (the default market solve), write market_NNN.pkl; the solve's equilibrium."""
    d = Path(folder)
    (d / "blobs").mkdir(parents=True, exist_ok=True)
    ids = {}
    for v in vars(module).values():
        if v is None or isinstance(v, (bool, int, float, str)):
            continue
        b = pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
        h = hashlib.sha256(b).hexdigest()
        f = d / "blobs" / f"{h}.pkl"
        if not f.exists():
            f.write_bytes(b)
        ids[id(v)] = h

    class _P(pickle.Pickler):
        def persistent_id(self, obj):
            return ids.get(id(obj))
    buf = io.BytesIO()
    _P(buf, protocol=pickle.HIGHEST_PROTOCOL).dump(module)
    eq = solve()
    n = len(list(d.glob("market_*.pkl")))
    with open(d / f"market_{n:03d}.pkl", "wb") as fh:
        pickle.dump({"module": buf.getvalue(), "args": args, "settings": settings, "result": eq, "sv_after": module.sv},
                    fh, protocol=pickle.HIGHEST_PROTOCOL)
    return eq

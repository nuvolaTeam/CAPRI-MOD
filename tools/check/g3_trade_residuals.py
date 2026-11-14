"""G3.2b at the default solve's solutions: the trade system in CAPRI's form (capri_mod/market/trade_system_ad.py)
evaluated at each captured market solve's equilibrium (G3.1 captures, diagnostics.capture_market_dir).

Each capture is replayed (tools/check/replay_market.py) so the module holds its state after the solve (the quotas'
sigmas included); the trade system is then evaluated at the solve's price ratios (sv.bilat_last_r), its supply and
use (the equilibrium's production and consumption) and the quotas' sigmas. Reported per solve: the largest balance
residual relative to the market's scale (S0 + D0, as the default solve's convergence test), and the largest quota
equation residual. The default solve stops at market.tol (1e-7) on the balances; its quotas are solved with the
prices (market.trq_joint).

    python tools/check/g3_trade_residuals.py runs/capture [--files market_000.pkl,...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "check"))


def residuals(path: Path) -> dict:
    from replay_market import load_module
    from capri_mod.settings import override
    from capri_mod.market.trade_system_ad import active_quotas, trade_system_function
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        eq = mm.solve(**rec["args"])
    r_all = mm.sv.bilat_last_r
    worst_bal, worst_trq, where = 0.0, 0.0, None
    for c, sc in (mm.par.bilat or {}).items():
        regs = list(sc.regions)
        r = r_all[c].reindex(regs).to_numpy(dtype=float)
        S = eq.production[c].reindex(regs).fillna(0.0).to_numpy(dtype=float)
        D = eq.consumption[c].reindex(regs).fillna(0.0).to_numpy(dtype=float)
        sB = np.asarray(sc.trq_sigma if sc.trq_sigma is not None else np.zeros(0), float)
        sW = np.asarray(sc.trq_sigmaW if sc.trq_sigmaW is not None else np.zeros(0), float)
        out = trade_system_function(sc)(r, sB, sW, S, D)
        bal = np.asarray(out[0]).ravel() / np.maximum(sc.S0 + sc.D0, 1.0)
        b = float(np.max(np.abs(bal))) if len(bal) else 0.0
        if b > worst_bal:
            worst_bal, where = b, (c, regs[int(np.argmax(np.abs(bal)))])
        bil, glo = active_quotas(sc)
        if bil or glo:
            worst_trq = max(worst_trq, float(np.max(np.abs(np.asarray(out[1]).ravel()))))
    return {"balance": worst_bal, "at": where, "quotas": worst_trq, "converged": bool(eq.converged)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        r = residuals(f)
        print(f"{f.name}: balance {r['balance']:.2e} at {r['at']}, quota equations {r['quotas']:.2e}, "
              f"converged {r['converged']}", flush=True)


if __name__ == "__main__":
    main()

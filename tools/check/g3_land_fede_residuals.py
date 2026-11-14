"""G3.2c, the non-EU land and feed energy block: CAPRI's land markets (LandSupplyMNL_ = LndSupplyEqualsDemand_) and
FeedBal_ evaluated simultaneously at the default solve's solutions.

The default solve's evaluation solves the land rents and the feed energy prices FEDE in turn until both settle, but
with each region's raw milk price of the PREVIOUS evaluation (the dairy blocks are solved later, inside the supply
response; G3_MARKET_INVENTORY.md, the default solve's lags). In G3 the milk price is an unknown of the same system. This
check takes each captured solve's equilibrium (replayed) and solves the land markets and FeedBal_ again at its prices
with the CURRENT dairy blocks' milk prices; the differences against the solve's own rents and FEDE are what the lag
leaves at the equilibrium (zero for a region whose milk price did not move in the last evaluation).

    python tools/check/g3_land_fede_residuals.py runs/capture [--files market_000.pkl,...]
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


def check(path: Path) -> dict:
    from replay_market import load_module
    from capri_mod.settings import override
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        mm.solve(**rec["args"])
        r = mm.sv.bilat_last_r
        # the Armington price ratios at r, as _bilateral_eval computes them
        PAr = r.copy()
        for c, sc in (mm.par.bilat or {}).items():
            rc = r[c].values
            p = sc.import_prices(rc, mm._tariff_adds(rec["args"].get("trade_scenario")).get(c))
            _, _, PA, _ = sc.prices(rc, p)
            PAr[c] = PA / sc.PA0
        wl, wp = mm.ev.dairy_world_last or {}, mm._dairy_world_params() or {}
        mr_now = {g: 1.0 + float(v["z"][wp[g]["iM"]]) for g, v in wl.items() if g in wp and "z" in v}
        land0, fede0 = mm.ev.land_now or {}, mm.ev.fede_now or {}
        land = mm.noneu_land_solve(r, mr_now, fede0, start=land0) if land0 else {}
        fede = mm.noneu_fede(PAr, r, mr_now, mm.land_by_type(land0 or None)) if fede0 else {}
    dl = max(((float(np.max(np.abs(np.asarray(v) - np.asarray(land0[k])))), k) for k, v in land.items() if k in land0),
             default=(0.0, None))
    df = max(((abs(v - fede0.get(k, 1.0)), k) for k, v in fede.items()), default=(0.0, None))
    return {"rents": dl, "fede": df, "regions": (len(land), len(fede))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        res = check(f)
        print(f"{f.name}: {res['regions'][0]} land markets, {res['regions'][1]} feed balances; largest rent change "
              f"{res['rents'][0]:.3e} EUR/ha ({res['rents'][1]}), largest FEDE ratio change {res['fede'][0]:.3e} "
              f"({res['fede'][1]})", flush=True)


if __name__ == "__main__":
    main()

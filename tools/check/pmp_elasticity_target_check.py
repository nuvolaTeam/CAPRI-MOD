"""Does the elasticity calibration deliver its own target elasticities? (question of 22 October 2026, K61)

PMPCalibrator sets each activity's own term from a target elasticity, Q_ii = revenue / (target x level x share term),
the target being CAPRI's estimated (crops) or market-level (animals) elasticity. The whole regional model adds its other
constraints (land, feed, nitrogen, requirements, CAPRI's crop-group allocation, ...). This check measures, for one
member state's regions at the 2030 baseline, the realised own-price elasticity of each activity's LEVEL (area or herd)
to its product price (+/- shock, all other prices fixed, no market feedback), and compares it with
  target     the elasticity the calibration received (level-weighted over the regions)
  implied    revenue / (Q_ii x level), what the PMP term alone gives with the other activities fixed
with the model's default terms ("elasticity") and with CAPRI's 2030 terms ("capri2030").

    python tools/check/pmp_elasticity_target_check.py [--ms AT] [--shock 0.05]
"""
from __future__ import annotations
import argparse, contextlib, io, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

ACTS = ["SWHE", "BARL", "RYEM", "CORN", "RAPE", "SUGB", "POTA", "DCOW", "BCOW", "BULL", "PIGF", "PIGS", "LAYS", "BROI",
        "SHGF"]


def measure(pmp: str, ms: str, shock: float) -> pd.DataFrame:
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    from capri_mod import settings as _S
    _S.activate(_S.current().replace({"supply.pmp_source": pmp}))
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    traj = BaselineTrajectory.from_file(str(ROOT / "capri_data" / "trajectories" / "capri_ref_2030.json"))
    pmod = ProjectionModule(m, traj, capri_prices_dir=str(ROOT / "capri_data" / "trajectories"))
    data, _ = pmod.project_data(2030)
    pm = pmod._model_for(data)
    regions = [r for r in pm.data["areas"].index if r.startswith(ms)]
    src = SupplyModule.ACTIVITY_PRICE_SOURCE
    rows = {}
    with contextlib.redirect_stdout(io.StringIO()):
        b = pm.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
        pol = getattr(pm, "_last_spol", None)
        for a in ACTS:
            key = src.get(a, a)
            lev = []
            for s in (shock, -shock):
                res = pm.supply_module.run(price_signals=pd.Series({key: s}), policy_scenario=pol, regions=regions)
                lev.append(sum(float(res[r].activities.get(a, 0.0)) for r in regions))
            x0 = sum(float(b["supply"][r].activities.get(a, 0.0)) for r in regions)
            if x0 <= 1e-6:
                continue
            realised = (lev[0] - lev[1]) / (lev[0] + lev[1]) / shock
            tgt, imp, w = 0.0, 0.0, 0.0
            for r in regions:
                mo = pm.supply_module._models[r]
                i = list(mo.acts).index(a)
                xr = float(mo._base_levels().get(a, 0.0))
                if xr <= 1e-6:
                    continue
                e = float(mo.supply_elasticities.get(a, np.nan))
                rev = float(getattr(mo, "_gross_rev", pd.Series(dtype=float)).get(a, np.nan))
                q = float(mo.Q[i, i])
                tgt += xr * e
                if rev == rev and q > 0:
                    imp += xr * rev / (q * xr)
                w += xr
            rows[a] = {"target": tgt / w if w else np.nan, "implied by Q": imp / w if w else np.nan,
                       "realised": realised}
    return pd.DataFrame(rows).T


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="AT")
    ap.add_argument("--shock", type=float, default=0.05)
    a = ap.parse_args()
    e = measure("elasticity", a.ms, a.shock)
    c = measure("capri2030", a.ms, a.shock)
    tab = pd.concat({"our terms": e, "CAPRI 2030 terms": c[["implied by Q", "realised"]]}, axis=1)
    print(f"{a.ms}, 2030 baseline: own-price elasticity of each activity's level (area or herd) to its product price")
    print(tab.round(2).to_string())


if __name__ == "__main__":
    main()

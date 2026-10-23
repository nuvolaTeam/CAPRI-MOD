"""The crops' response with CAPRI's own 2030 PMP terms against the elasticity-calibrated ones (KNOWN_ISSUES K61).

At the 2030 baseline (CAPRI's 2030 reference trajectory and prices), the regional supply models of a few regions are
solved at base prices and with one product group's prices raised (no market feedback), with the crops' PMP matrix
  elasticity  calibrated per activity from CAPRI's supply elasticities (the model's default), and
  capri2030   CAPRI's own terms of its 2030 baseline calibration (p_pmpQuadTechn, p_pmpQuadPact; SupplyModule.pmp_source).
Reported: each crop group's area change (%), summed over the regions, per shock and PMP matrix; and the base drift.

    python tools/check/pmp_capri2030_check.py [--regions DE11,FRH0,ITC4,PL41,ES41,AT11] [--shock 0.10] [--out FILE]
"""
from __future__ import annotations
import argparse, contextlib, io, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd

GROUPS = {"cereals": ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER", "PARI"],
          "oilseeds": ["RAPE", "SUNF", "SOYA", "OOIL"],
          "other arable": ["PULS", "POTA", "SUGB", "TEXT", "TOBA", "OCRO", "OIND", "NURS", "FLOW"],
          "fodder on arable": ["MAIF", "OFOD"], "vegetables": ["TOMA", "OVEG"],
          "permanent crops": ["APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV", "TABO"],
          "grassland": ["GRAS"], "fallow / set-aside": ["SETA"]}
SHOCKS = {"cereals": ["SWHE", "DWHE", "BARL", "RYEM", "OATS", "CORN", "OCER", "PARI"],
          "oilseeds": ["RAPE", "SUNF", "SOYA"], "wheat": ["SWHE"], "maize": ["CORN"]}


def run(pmp: str, regions, shock: float) -> dict:
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    from capri_mod import settings as _S
    _S.activate(_S.current().replace({"supply.pmp_source": pmp}))
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    traj = BaselineTrajectory.from_file(str(ROOT / "capri_data" / "trajectories" / "capri_ref_2030.json"))
    pmod = ProjectionModule(m, traj, capri_prices_dir=str(ROOT / "capri_data" / "trajectories"))
    data, _ = pmod.project_data(2030)
    pm = pmod._model_for(data)
    out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        b = pm.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
        sig0 = getattr(pm, "_last_price_signal", None)
        for name, prods in SHOCKS.items():
            sig = pd.Series({c: shock for c in prods})
            s = pm.supply_module.run(price_signals=sig, policy_scenario=getattr(pm, "_last_spol", None), regions=regions)
            rows = {}
            for g, acts in GROUPS.items():
                a0 = sum(float(b["supply"][r].activities.get(a, 0.0)) for r in regions for a in acts)
                a1 = sum(float(s[r].activities.get(a, 0.0)) for r in regions for a in acts)
                rows[g] = 100.0 * (a1 / a0 - 1.0) if a0 > 1e-9 else float("nan")
            out[name] = pd.Series(rows)
    n_cov = {r: getattr(pm.supply_module._models.get(r), "n_capri_pmp_acts", 0) for r in regions}
    drift = (pm.metadata if hasattr(pm, "metadata") else {}).get("base_calibration_drift") if hasattr(pm, "metadata") else None
    return {"resp": pd.concat(out, axis=1), "covered": n_cov, "drift": drift}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="DE11,FRH0,ITC4,PL41,ES41,AT11")
    ap.add_argument("--shock", type=float, default=0.10)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    regions = a.regions.split(",")
    res = {p: run(p, regions, a.shock) for p in ("elasticity", "capri2030")}
    tab = pd.concat({p: r["resp"] for p, r in res.items()}, axis=1)
    print(f"Regional models at the 2030 baseline, +{a.shock:.0%} on one product group's prices (no market feedback);"
          f" % change of each crop group's area, summed over {', '.join(regions)}")
    print(tab.round(2).to_string())
    print("crops with CAPRI's terms per region:", res["capri2030"]["covered"])
    if a.out:
        tab.to_csv(a.out)


if __name__ == "__main__":
    main()

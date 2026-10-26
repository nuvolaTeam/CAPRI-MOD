"""Own-price supply elasticities of a member state's crops, from the model's regional supply models, against CAPRI's.

CAPRI measures its supply models' elasticities by perturbing the prices one product at a time in the supply models
(capmod: supply_elas_<NTS><BAS><SIM><MS>.gdx, p_ElasSupp(MS, product, price, 'CAL'); the project lead's files are for
2020, supply_elas_2_1720<MS>defaulta). Here the same experiment on the model's regional supply models at its 2030
baseline, with the crops' PMP matrix calibrated from elasticities ("elasticity") and with CAPRI's own 2030 terms
("capri2030", KNOWN_ISSUES K61): each product's price +/- shock (central difference), all other prices fixed, no market
feedback; the member state's production (gross output) summed over its regions.

The CAPRI values are for 2020, not 2030: a guide to magnitudes, not a target to match.

    python tools/check/pmp_supply_elas_check.py [--ms DE] [--shock 0.05] [--products SWHE,BARL,RYEM,CORN,RAPE,SUGB,POTA]
"""
from __future__ import annotations
import argparse, contextlib, io, re, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
sys.path.insert(0, str(ROOT))
import pandas as pd

CAPRI_CODE = {"CORN": "MAIZ", "WINE": "TWIN"}


def capri_elas(ms: str, products) -> pd.Series:
    cc = MS_CODE.get(ms, ms)
    cands = [Path(d) / f"supply_elas_2_1720{cc}defaulta.txt" for d in
             ("/mnt/user-data/uploads", "/home/claude/work/up/supelas")]      # the second: the REMAINING zip unpacked
    f = next((c for c in cands if c.exists()), cands[0])
    out = {}
    if not f.exists():
        return pd.Series(out, dtype=float)
    cc = MS_CODE.get(ms, ms)
    for line in open(f, errors="ignore"):
        m = re.match(rf"^'{cc}000000'\.'([A-Z]+)'\.'\1'\.'CAL'\s+([-\d.Ee+]+)", line)
        if m:
            out[m.group(1)] = float(m.group(2))
    return pd.Series({p: out.get(CAPRI_CODE.get(p, p), float("nan")) for p in products})


def model_elas(pmp: str, ms: str, products, shock: float) -> pd.Series:
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
    out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        pm.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
        pol = getattr(pm, "_last_spol", None)
        for p in products:
            q = []
            for s in (shock, -shock):
                res = pm.supply_module.run(price_signals=pd.Series({p: s}), policy_scenario=pol, regions=regions)
                q.append(sum(float(res[r].gross_output.get(p, 0.0)) for r in regions))
            out[p] = (q[0] - q[1]) / (q[0] + q[1]) / shock if (q[0] + q[1]) > 0 else float("nan")
    return pd.Series(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="DE")
    ap.add_argument("--shock", type=float, default=0.05)
    ap.add_argument("--products", default="SWHE,BARL,RYEM,CORN,RAPE,SUGB,POTA")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    prods = a.products.split(",")
    tab = pd.DataFrame({"elasticity": model_elas("elasticity", a.ms, prods, a.shock),
                        "capri2030": model_elas("capri2030", a.ms, prods, a.shock),
                        "CAPRI 2020": capri_elas(a.ms, prods)})
    print(f"{a.ms}: own-price supply elasticities of the crops (production), model at its 2030 baseline vs CAPRI's 2020")
    print(tab.round(2).to_string())
    if a.out:
        tab.to_csv(a.out)


if __name__ == "__main__":
    main()

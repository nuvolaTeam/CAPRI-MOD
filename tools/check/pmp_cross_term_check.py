"""How much the PMP cross terms matter: CAPRI's decomposition experiment (2008 documentation sect. 7.3, item 4: "the PMP
cross terms between crop groups, only leaving the diagonal terms while recalibrating the linear term").

For a set of regions, the regional supply models are solved at base prices and at a price shock (default: +20% on the
cereals), with two structures of the PMP matrix (PMPCalibrator.CROSS_TERMS):
  capri     cross terms only between crops of CAPRI's crop groups (QUADRA_ with GRPLEVL_), the default
  none      diagonal only (CAPRI's decomposition variant)
The linear terms are recalibrated in each case, so the base is reproduced in both. Reported: the response of each
activity group to the shock (% change of area or herd, summed over the regions), per structure.

    python tools/check/pmp_cross_term_check.py [--shock 0.20] [--regions DE11,FRH0,ITC4,PL41,ES41,IE04] [--out FILE]
"""
from __future__ import annotations
import argparse, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd

GROUPS = {
    "cereals": ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER", "PARI"],
    "oilseeds": ["RAPE", "SUNF", "SOYA"],
    "other arable": ["PULS", "POTA", "SUGB", "TEXT", "TOBA", "OCRO", "OIND", "NURS", "FLOW"],
    "fodder on arable": ["MAIF", "ROOF", "OFOD"],
    "vegetables": ["TOMA", "OVEG"],
    "permanent crops": ["APPL", "OFRU", "CITR", "TAGR", "WINE", "OLIV", "TABO"],
    "grassland": ["GRAS"],
    "fallow / set-aside": ["SETA"],
    "cattle": ["DCOW", "BCOW", "BULL", "HFRS", "CALV"],
    "pigs and poultry": ["PIGF", "PIGS", "LAYS", "BROI"],
    "sheep and goats": ["SHGM", "SHGF"],
}
SHOCKED = ["SWHE", "DWHE", "BARL", "RYEM", "OATS", "CORN", "OCER"]


def run(mode: str, regions, shock: float) -> pd.DataFrame:
    from capri_mod.model import CAPRIModel
    from capri_mod import settings as _S
    import contextlib, io
    _S.activate(_S.current().replace({"supply.pmp_cross_terms": mode}))
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    with contextlib.redirect_stdout(io.StringIO()):
        b = m.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
        # the regional models alone at the shocked prices (no market feedback), with the baseline's policy settings
        sig = pd.Series({c: shock for c in SHOCKED})
        s = m.supply_module.run(price_signals=sig, policy_scenario=getattr(m, "_last_spol", None), regions=regions)
    rows = {}
    for g, acts in GROUPS.items():
        a0 = sum(float(b["supply"][r].activities.get(a, 0.0)) for r in regions for a in acts)
        a1 = sum(float(s[r].activities.get(a, 0.0)) for r in regions for a in acts)
        rows[g] = 100.0 * (a1 / a0 - 1.0) if a0 > 1e-9 else float("nan")
    return pd.Series(rows, name=mode)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shock", type=float, default=0.20)
    ap.add_argument("--regions", default="DE11,FRH0,ITC4,PL41,ES41,IE04")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    regions = a.regions.split(",")
    df = pd.concat([run(mode, regions, a.shock) for mode in ("capri", "none")], axis=1)
    print(f"Regional models at +{a.shock:.0%} on the cereal prices (no market feedback), % change summed over {', '.join(regions)}")
    print(df.round(2).to_string())
    if a.out:
        df.to_csv(a.out)


if __name__ == "__main__":
    main()

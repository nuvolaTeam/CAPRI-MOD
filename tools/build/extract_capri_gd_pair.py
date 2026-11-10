"""CAPRI's Green Deal 2030 step against its reference: the scenario's effect, for comparison with capri-mod's
greendeal2030 run (capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md).

Two CAPRI capmod runs from the project lead's installation (10 November 2026, GAMS 53.3):

  res_2_1730greendeal_refdefaulta.gdx      the reference. Its dataOut equals the shipped baseline the model is
                                           calibrated to (res_2_1730greendeal_refdefaulta.zip, tools/lib/paths.py
                                           BASELINE_REF) in all 891,502 records of the member states and EU27yr19
                                           in 2030, to the 15 digits of the dump (largest relative difference 5e-15)
  res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx
                                           pol_input/greendeal/greendeal_scenarios.gms with landscape elements 8%,
                                           organic 18%, pesticides -20%, mineral fertiliser 13crp, N surplus -30%
                                           (META of the run; the model's scenario folder
                                           capri_data/scenarios/greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00)

Kept, year 2030, as tools/build/extract_capri_vcs_pair.py keeps the coupled-support pair (its selection, _keep):
supply rows (region, activity, item) with item LEVL, PRME (and PROD, YILD at EU and member-state level) for EU27yr19,
the member states and their NUTS 2 regions; market rows (region, item, product) with UVAP, UVAG, MAPR, HCON, IMPT,
EXPT at EU and member-state level.

Output: capri_data/validation/greendeal_2030/capri_gd_effect.csv.xz (region, activity, item, ref, scen, pct_change)

    python tools/build/extract_capri_gd_pair.py [REF.gdx SCEN.gdx] [--lib-dir DIR]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import EXPORTS, SOURCES  # noqa: E402
from extract_capri_vcs_pair import read_gdx  # noqa: E402  (the same selection as the coupled-support pair)

REF = EXPORTS / "res_2_1730greendeal_refdefaulta.gdx"
SCEN = EXPORTS / "res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx"
OUT = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_effect.csv.xz"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_gdx", type=Path, nargs="?", default=REF)
    ap.add_argument("scen_gdx", type=Path, nargs="?", default=SCEN)
    ap.add_argument("--lib-dir", default=os.environ.get("CAPRI_GDXLIB", str(SOURCES / "gdxlib")))
    a = ap.parse_args()
    ref = read_gdx(a.ref_gdx, a.lib_dir)
    scen = read_gdx(a.scen_gdx, a.lib_dir)
    keys = sorted(set(ref) | set(scen))
    df = pd.DataFrame([(r, act, it, ref.get((r, act, it)), scen.get((r, act, it))) for (r, act, it) in keys],
                      columns=["region", "activity", "item", "ref", "scen"])
    df["pct_change"] = 100.0 * (df["scen"] / df["ref"] - 1.0)
    df.loc[~(df["ref"].abs() > 1e-9), "pct_change"] = float("nan")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    eu = df[(df.region == "EU27yr19") & (df.item == "LEVL")].set_index("activity")["pct_change"].dropna()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df)} rows ({len(ref)} reference, {len(scen)} scenario)")
    print("EU27 levels, % change:", eu.reindex(["SWHE", "DWHE", "BARL", "MAIZ", "RAPE", "PULS", "FALL", "GRAE", "GRAI",
                                               "DCOL", "SCOW", "PIGF", "SHGM"]).round(1).dropna().to_dict())


if __name__ == "__main__":
    main()

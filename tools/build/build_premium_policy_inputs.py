"""CAPRI's inputs of policy/policy.gms that are not premium declarations (the premium module, P2b), from the sim_ini
restart file's extract (tools/build/build_simini_reference.py):

  capri_data/<base year>/policy/premium_entitlement_weights.csv  region, activity, scheme, weight, eps
        p_EntlWght1: the share of an activity's level that holds entitlements of a scheme (the rural development
        measures' eligible shares, the Agenda 2000 animal schemes'); eps = 1 where CAPRI writes EPS (weight 0 and
        not replaced by a higher level's: policy.gms l. 211-217, 406-409)
  capri_data/<base year>/policy/premium_settings.csv   item, value, source
        ntslvl (re-aggregate the declared premiums to NUTS 1 and the member states, policy.gms l. 381, 389) and
        p_AggregNUTS2 (the farm-type runs, 0 in CAPMOD's NUTS 2 runs)

The livestock units of the application type per livestock unit are CAPRI's dat/policy/livestock_units.gms, already
in capri_data/pipeline/captrd/dat/p_luunits.csv (build_captrd_dat.py; equal to sim_ini's p_LUUnits). The premium
modification factors (p_premModifFact) are written with P2c: in the 2030 restart file they are set only for the
Agenda 2000 animal schemes, which have no premium in 2030.

    python tools/build/build_premium_policy_inputs.py [--simini DIR] [--base-year 2017]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import REFERENCE  # noqa: E402

sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simini", type=Path, default=REFERENCE / "simini" / "simini_21730")
    ap.add_argument("--base-year", default="2017")
    a = ap.parse_args()

    out = ROOT / "capri_data" / a.base_year / "policy"
    out.mkdir(parents=True, exist_ok=True)

    w = read_csv(a.simini / "p_EntlWght1.csv.gz", keep_default_na=False)
    w = w.rename(columns={"d0": "region", "d1": "activity", "d2": "scheme", "value": "weight"})
    w = w[["region", "activity", "scheme", "weight", "eps"]]
    if w.duplicated(["region", "activity", "scheme"]).any():
        raise SystemExit("p_EntlWght1: a weight written twice")
    to_csv(w.sort_values(["region", "activity", "scheme"]).reset_index(drop=True),
           out / "premium_entitlement_weights.csv", index=False)

    rows = []
    for sym in ("ntslvl", "p_AggregNUTS2"):
        v = read_csv(a.simini / f"{sym}.csv.gz", keep_default_na=False)
        if len(v) != 1:
            raise SystemExit(f"{sym}: {len(v)} records, one expected")
        rows.append((sym, float(v.value.iloc[0]), f"sim_ini_21730 {sym}"))
    to_csv(pd.DataFrame(rows, columns=["item", "value", "source"]), out / "premium_settings.csv", index=False)
    print(f"premium policy inputs: {len(w)} entitlement weights ({int(w.eps.sum())} EPS), "
          + ", ".join(f"{i} {v:g}" for i, v, _ in rows))


if __name__ == "__main__":
    main()

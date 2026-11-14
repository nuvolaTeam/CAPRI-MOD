"""A Green Deal 2030 run of the model against CAPRI's Green Deal 2030 step (capri_data/validation/greendeal_2030/
capri_gd_effect.csv, tools/build/extract_capri_gd_pair.py): % changes from the reference, EU27 and per member
state, for the activity levels and the EU27 producer prices.

Only % changes are compared: the model counts some herds in other units than CAPRI's activity levels (fattening pigs,
bulls, heifers, fattening sheep, poultry: capri_level_ratio.csv, KNOWN_ISSUES K63), so their levels differ by
definition; where the units are the same (dairy cows, sows, breeding sheep) the model's 2030 base equals CAPRI's.

  activities   the model's activity <- the CAPRI activities summed (DATAOUT's DCOW is CAPRI's total of DCOL and DCOH)
  prices       the model's EU market price change (the run's "prices": scen / base - 1) against CAPRI's EU27yr19 UVAP
EU27 = CAPRI's EU27yr19; the model's EU: its regions outside Norway (NO..), as the run script sums them.

    python tools/check/compare_capri_gd.py RUN.pkl [--ms] [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TABLE = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_effect.csv"

#: the model's activities and the CAPRI activities whose levels they compare with (BASELINE_REPRODUCTION.md)
ACTIVITIES = {
    "SWHE": ["SWHE"], "DWHE": ["DWHE"], "BARL": ["BARL"], "CORN": ["MAIZ"], "RYEM": ["RYEM"], "OATS": ["OATS"],
    "OCER": ["OCER"], "RAPE": ["RAPE"], "SUNF": ["SUNF"], "SOYA": ["SOYA"], "PULS": ["PULS"], "POTA": ["POTA"],
    "SUGB": ["SUGB"], "MAIF": ["MAIF"], "OFAR": ["OFAR"], "GRAE": ["GRAE"], "GRAI": ["GRAI"], "FALL": ["FALL"],
    "VSET": ["VSET"], "OLIV": ["OLIV"], "WINE": ["TWIN"], "OVEG": ["OVEG"], "TOMA": ["TOMA"], "APPL": ["APPL"],
    "DCOW": ["DCOW"], "BCOW": ["SCOW"], "BULL": ["BULL", "BULH"], "HFRS": ["HEIL", "HEIH", "HEIR"],
    "CALV": ["CAMF", "CAFF", "CAMR", "CAFR"], "PIGF": ["PIGF"], "PIGS": ["SOWS"], "SHGM": ["SHGM"], "SHGF": ["SHGF"],
    "LAYS": ["HENS"], "BROI": ["POUF"]}
#: the model's market products and CAPRI's
PRICES = {"SWHE": "SWHE", "BARL": "BARL", "CORN": "MAIZ", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER",
          "RAPE": "RAPE", "SUNF": "SUNF", "SOYA": "SOYA", "PULS": "PULS", "POTA": "POTA", "TOMA": "TOMA",
          "OVEG": "OVEG", "APPL": "APPL", "OLIV": "OLIV", "BEEF": "BEEF", "PORK": "PORK", "POUL": "POUM",
          "SGMT": "SGMT", "EGGS": "EGGS", "MILK": "MILK", "RAPC": "RAPC", "SOYC": "SOYC"}


def capri_effect() -> pd.DataFrame:
    from capri_mod.csvio import read_csv
    return read_csv(TABLE, keep_default_na=False, na_values=[""])


def activity_table(run: dict, capri: pd.DataFrame, by_ms: bool = False) -> pd.DataFrame:
    """% change of each activity, CAPRI's and the model's, EU27 (and per member state with by_ms)."""
    lev = capri[capri["item"] == "LEVL"]
    rows = []
    groups = [("EU27", "EU27yr19", None)]
    if by_ms:
        ar = run.get("act_regional")
        if ar is not None:
            ms = sorted({str(r)[:2] for r in ar[0] if not str(r).startswith("NO")})
            groups += [(m, f"{m}000000", m) for m in ms]
    for label, creg, prefix in groups:
        c = lev[lev["region"] == creg].set_index("activity")
        if prefix is None:
            mb, ms_ = run["act"]
        else:
            b, s = run["act_regional"]                 # {region: {activity: level}}, reference and scenario
            mb = pd.DataFrame({r: v for r, v in b.items() if str(r).startswith(prefix)}).T.sum().to_dict()
            ms_ = pd.DataFrame({r: v for r, v in s.items() if str(r).startswith(prefix)}).T.sum().to_dict()
        for a, cc in ACTIVITIES.items():
            cr = c.reindex(cc)
            ref, scen = cr["ref"].sum(), cr["scen"].sum()
            if not (ref > 0) or not (mb.get(a, 0) > 0):
                continue
            rows.append((label, a, 100 * (scen / ref - 1), 100 * (ms_.get(a, 0) / mb[a] - 1)))
    t = pd.DataFrame(rows, columns=["region", "activity", "capri_pct", "model_pct"])
    t["gap_pts"] = t["model_pct"] - t["capri_pct"]
    return t


def price_table(run: dict, capri: pd.DataFrame) -> pd.DataFrame:
    """EU price % changes: CAPRI's EU27yr19 UVAP and the model's market price."""
    u = capri[(capri["region"] == "EU27yr19") & (capri["item"] == "UVAP")].set_index("activity")
    p = run["prices"]
    rows = [(m, 100 * (u.at[c, "scen"] / u.at[c, "ref"] - 1), 100 * float(p[m])) for m, c in PRICES.items()
            if c in u.index and m in p and u.at[c, "ref"]]
    t = pd.DataFrame(rows, columns=["product", "capri_pct", "model_pct"])
    t["gap_pts"] = t["model_pct"] - t["capri_pct"]
    return t


def main():
    from capri_mod.io_results import load_run
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--ms", action="store_true", help="also per member state")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    run = load_run(a.run)
    capri = capri_effect()
    act = activity_table(run, capri, a.ms)
    pr = price_table(run, capri)
    pd.set_option("display.width", 160)
    eu = act[act.region == "EU27"].set_index("activity")
    print("EU27 activity levels, % change from the reference\n" + eu.round(1).to_string())
    print(f"  mean absolute gap {eu.gap_pts.abs().mean():.1f} points; same sign {np.mean(np.sign(eu.capri_pct.round(1)) == np.sign(eu.model_pct.round(1))):.0%}")
    print("\nEU27 producer prices, % change\n" + pr.set_index("product").round(1).to_string())
    print(f"  mean absolute gap {pr.gap_pts.abs().mean():.1f} points; model / CAPRI (median ratio) "
          f"{np.nanmedian((pr.model_pct / pr.capri_pct.where(pr.capri_pct.abs() > 1)).to_numpy(float)):.2f}"
          " (products with a CAPRI change above 1%)")
    if a.ms:
        g = act[act.region != "EU27"].groupby("region").gap_pts.apply(lambda x: x.abs().median()).sort_values()
        print("\nmember states, median absolute gap over the activities (points; a median, as small activities give "
              "large % changes): " + ", ".join(f"{k} {v:.1f}" for k, v in g.items()))
    if a.csv:
        pd.concat([act.assign(kind="activity"), pr.rename(columns={"product": "activity"}).assign(region="EU27",
                   kind="price")]).to_csv(a.csv, index=False)


if __name__ == "__main__":
    main()

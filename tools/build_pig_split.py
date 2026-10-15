"""Split the model's single pig activity into CAPRI's two: sows and fattening pigs (Sprint 5).

CAPRI (supply_model.gms, sets.gms) has SOWS (a sow with her piglets up to 20 kg; output: piglets YPIG,
cull-sow pork, manure) and PIGF (pig fattening; input: one piglet IPIG per pig; output: pork, manure),
linked by piglet markets (arm/market_model.gms yaniMarket_, YPIG). The model kept every pig in PIGS.
Now PIGS = sows and PIGF = fattening pigs, as `definitions.ANIMALS` already describes them.

Herds (census stock, 1000 head, animal_numbers.csv): PIGS := breeding sows (SOWS column);
PIGF := all pigs - sows (fattening and young pigs). Where the census has no pigs at all (Norway's
regions list sows only), both stay zero, as before.

Then every per-head table is rebuilt with CAPRI's activities mapped one to one (SOWS -> PIGS,
PIGF -> PIGF), by the existing builders, each verified beforehand to reproduce the current files exactly:
output, revenue (MREV), output value (TOOU), cost (TOIN), premium (PRME), manure N (MANN), feed
(FCER/FPRO/FENE), the ration file, NH3 factors, the ammonia technology model, young-animal flows
(now with the piglet balance) and the fodder balance.

Usage: python tools/build_pig_split.py [--dump-dir /home/claude/work/capreg]
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def split_herds():
    f = ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv"
    a = pd.read_csv(f, index_col=0)
    if "SOWS" not in a.columns:
        print("animal_numbers.csv already split (no SOWS column)")
        return
    tot, sows = a["PIGS"].fillna(0.0), a["SOWS"].fillna(0.0)
    has = tot > 0
    a["PIGF"] = (tot - sows).clip(lower=0.0).where(has, 0.0)
    a["PIGS"] = sows.where(has, 0.0)
    a = a.drop(columns=["SOWS"])
    cols = [c for c in a.columns if c != "PIGF"]
    a = a[cols[:cols.index("PIGS") + 1] + ["PIGF"] + cols[cols.index("PIGS") + 1:]]
    a.to_csv(f)
    print(f"animal_numbers.csv: PIGS = sows {a['PIGS'].sum():.0f}, PIGF = fattening {a['PIGF'].sum():.0f} (1000 head)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    a = ap.parse_args()
    dump = Path(a.dump_dir)
    split_herds()
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
    import build_livestock_output_coef as B
    D = ROOT / "capri_data" / "2017"
    B.build(dump).to_csv(D / "supply" / "livestock_output_coef.csv")
    for item, dest in (("MREV", "supply/livestock_revenue_coef.csv"), ("TOIN", "supply/livestock_cost_coef.csv"),
                       ("TOOU", "supply/livestock_output_value_coef.csv"), ("MANN", "environment/livestock_manure_n_coef.csv")):
        B.build(dump, item).to_csv(D / dest)
    # value of final products only (no young animals): a sow's CAPRI MREV is her piglet sales
    # (DE94: 24.0 piglets x EUR 25.43 = 610.9 = MREV), so a pork price must move only her cull-sow
    # pork (EUR 90), piglets moving with the piglet price
    B.build(dump, "FINAL_VALUE").to_csv(D / "supply" / "livestock_product_value_coef.csv")
    B.build_product_values_by_market(dump).to_csv(D / "supply" / "livestock_product_value_by_market_coef.csv")
    feed = []
    for item, suf in (("FCER", "cereals"), ("FPRO", "protein"), ("FENE", "energy")):
        t = B.build(dump, item) / 1000.0                       # kg -> t per head
        feed.append(t.rename(columns=lambda c: f"{c}_{suf}"))
    pd.concat(feed, axis=1).to_csv(D / "feed" / "livestock_feed_coef.csv")
    py = sys.executable
    for cmd in (["tools/build_livestock_premium_coef.py", str(dump)], ["tools/build_feed_ration.py", "--dump-dir", str(dump)],
                ["tools/build_nh3_factors.py"], ["tools/build_ammonia_tech_model.py"],
                ["tools/build_young_animals.py", "--dump-dir", str(dump)], ["tools/build_fodder_balance.py"]):
        r = subprocess.run([py] + cmd, cwd=ROOT, capture_output=True, text=True)
        print(cmd[0], "->", (r.stdout.strip().splitlines() or ["(no output)"])[-1], r.stderr.strip()[-300:] if r.returncode else "")


if __name__ == "__main__":
    main()

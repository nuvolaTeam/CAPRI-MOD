"""EU-wide shares of plant protection, other inputs and fertiliser in a crop's input cost, from CAPRI's 2017 results (K31).

The supply module's fallback for crops CAPRI does not grow in a region (OTHER_COST_SHARE, FERT_COST_SHARE,
PPP_COST_SHARE; the pesticide and organic instruments use CAPRI's regional costs per ha, plant_protection_cost.csv,
everywhere else). Over CAPRI's NUTS2 regions of the 27 member states, weighted by CAPRI's 2017 activity levels:

    ppp_cost_share   = sum L x PLAP x UVAG.PLAP / 1000 / sum L x TOIN   (PLAP: g of active ingredient per ha;
                                                                       UVAG.PLAP: EUR per kg, regional)
    other_cost_share = sum L x INPO / sum L x TOIN
    fert_cost_share  = sum L x FERT / sum L x TOIN

the per-ha items as tools/build/build_plant_protection_cost.py reads them, the model crops as CAPRI activities summed
(tools/build/build_capri_base.CROP_MAP). The file had no builder; its values
were close to this method for most crops but not for olives for oil (plant protection 0.249 against 0.422) and
cotton.

Source: CAPRI 2017 results res_17<MS>.txt (LEVL, PLAP, INPO, FERT, TOIN per activity; UVAG.PLAP per region).
Output: capri_data/2017/supply/crop_cost_shares.csv (crop, other_cost_share, fert_cost_share, ppp_cost_share);
the set-aside row (no input cost in CAPRI) is kept as it was.

    python tools/build/build_crop_cost_shares.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "capri_data" / "2017" / "supply" / "crop_cost_shares.csv"
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'(PLAP|INPO|FERT|TOIN|LEVL)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
EU27 = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
        "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    v = defaultdict(dict)
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m and m.group(1)[:2] in EU27 and not m.group(1).endswith("000000"):
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    sp = importlib.util.spec_from_file_location("base", ROOT / "tools" / "build" / "build_capri_base.py")
    base = importlib.util.module_from_spec(sp); sp.loader.exec_module(base)
    crops = {c: acts for c, acts in base.CROP_MAP.items() if c != "SETA"}
    tot = defaultdict(lambda: defaultdict(float))
    for reg, d in v.items():
        uv = d.get(("UVAG", "PLAP"), 0.0)
        for col, acts in crops.items():
            for act in acts:
                L, T = d.get((act, "LEVL"), 0.0), d.get((act, "TOIN"), 0.0)
                if L <= 0 or T <= 0:
                    continue
                t = tot[col]
                t["toin"] += L * T
                t["ppp"] += L * d.get((act, "PLAP"), 0.0) * uv / 1000.0
                t["other"] += L * d.get((act, "INPO"), 0.0)
                t["fert"] += L * d.get((act, "FERT"), 0.0)
    old = pd.read_csv(DEST, index_col=0)
    new = pd.DataFrame({c: {"other_cost_share": t["other"] / t["toin"], "fert_cost_share": t["fert"] / t["toin"],
                            "ppp_cost_share": t["ppp"] / t["toin"]} for c, t in tot.items() if t["toin"] > 0}).T
    new = new.round(3)
    if "SETA" in old.index:
        new.loc["SETA"] = old.loc["SETA"]
    new = new.sort_index()
    new.index.name = "crop"
    new[["other_cost_share", "fert_cost_share", "ppp_cost_share"]].to_csv(DEST)
    cmp = old.join(new, rsuffix="_new", how="outer")
    print(f"wrote {DEST.relative_to(ROOT)}: {len(new)} crops")
    print(cmp.to_string())


if __name__ == "__main__":
    main()

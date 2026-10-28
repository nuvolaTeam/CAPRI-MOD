"""Build CAPRI's manure-pool trade costs (manuremarket/define_manure_market_structure.gms).

One pool per country; every pair connected. Distance between pools = distance
between their centre NUTS-2 regions (rManPool_centre) from CAPRI's
nuts2_center_distance (metres / 1000). Trade cost per t fresh manure =
1 EUR loading + 0.18 EUR/t/km x distance (Van der Straeten et al. 2010), per t
pure nutrient = that / mean nutrient content 7.97% (cattle 4.95, pigs 6.91,
poultry 15.89, other 4.14) x 100. CAPRI inflates the haul cost from its base to
the simulation year; kept at 0.18 here (REGISTERED).

    python tools/build/build_manure_pool_costs.py --dist nuts2_center_distance.csv
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
GMS = Path("/home/claude/work/allgms/gams/manuremarket/define_manure_market_structure.gms")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", type=Path, default=Path("/home/claude/work/nuts2_center_distance.csv"))
    args = ap.parse_args()
    txt = GMS.read_text(errors="ignore").replace("\r", "")
    blk = txt[txt.index("set rManPool_centre(rall,rall)"):]
    blk = blk[blk.index("/") + 1: blk.index("/", blk.index("/") + 1)]
    centre = {m.group(1)[:2]: m.group(2) for m in re.finditer(r"([A-Z]{2}000000)\.([A-Z0-9]{8})", blk)}
    dist = {}
    for r in csv.reader(open(args.dist, encoding="utf-8-sig")):
        if len(r) >= 3 and r[0] != "Dim1":
            try:
                dist[(r[0], r[1])] = float(r[2]) / 1000.0
            except ValueError:
                pass
    content = (4.95 + 6.91 + 15.89 + 4.14) / 4.0
    pools = sorted(centre)
    out = {}
    for a in pools:
        for b in pools:
            if a == b:
                continue
            km = dist.get((centre[a], centre[b])) or dist.get((centre[b], centre[a]))
            if km:
                out[f"{a}|{b}"] = {"km": km,
                                   "eur_per_t_n": (1.0 + 0.18 * km) / content * 100.0}
    dest = _ROOT / "capri_data" / "2017" / "environment" / "manure_pool_costs.json"
    dest.write_text(json.dumps({"_source": "CAPRI define_manure_market_structure.gms (rManPool_centre, p_mPoolTradeCost) with "
                                "nuts2_center_distance.gdx (supplied by the project lead)",
                                "_units": "km; EUR per t N", "centre": centre, "pairs": out}, indent=1))
    print(f"wrote {dest}: {len(centre)} pools, {len(out)} connected pairs")


if __name__ == "__main__":
    main()

"""CAPRI's market supply elasticities p_elasSupp at its 2017 calibration (elas1717defaulta.gdx) and their EU medians
(KNOWN_ISSUES K101).

    capri_data/sources/arm/capri_supply_elas_market_1717.csv   region, prod, wrt, value
        every record of p_elasSupp(region, prod, wrt, 'CAL') of the gdxdump p_elasSupp.txt, in its order; read by
        capri_mod/supply/capri_pmp.py (the livestock elasticities of the elasticity-calibrated PMP)
    capri_data/sources/arm/supply_elas_eu_all.json             {product: elasticity}
        the median over CAPRI's EU member states of the own-price p_elasSupp per product, rounded to 3 decimals, keyed
        by CAPRI's code but MAIZ, POUM, WHEA (the model's CORN, POUL, SWHE); read by capri_mod/market/supply.py (the EU
        rows' own-price anticipation)

The JSON is built as it was committed, which had no builder until 29 October 2026; three of its choices are recorded
in K101, not changed here: the member states are CAPRI's EU28 (the UK included, the model's EU is 27), the key set has
INPE (the price index of the non-agricultural good) and four products under CAPRI's codes the market never looks up
(OLIO, RICE, SUGA, TWIN: the model's OLIV, PARI, SUGR, WINE, whose EU supply is set by other blocks).

    python tools/build/build_capri_supply_elas_market.py [--src p_elasSupp.txt]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("/mnt/user-data/uploads/p_elasSupp.txt")
OUT = ROOT / "capri_data" / "sources" / "arm"
REC = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'CAL'\s+([^,\s]+)")
#: CAPRI's EU28 member states of the 2017 calibration (sets.gms NUTS0_EU15 + NUTS0_EU10 + BG, RO, HR)
EU28 = ("AT000000", "BG000000", "BL000000", "CY000000", "CZ000000", "DE000000", "DK000000", "EE000000", "EL000000",
        "ES000000", "FI000000", "FR000000", "HR000000", "HU000000", "IR000000", "IT000000", "LT000000", "LV000000",
        "MT000000", "NL000000", "PL000000", "PT000000", "RO000000", "SE000000", "SI000000", "SK000000", "UK000000")
#: the JSON's three renamed keys (CAPRI code -> model code)
RENAME = {"MAIZ": "CORN", "POUM": "POUL", "WHEA": "SWHE"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC)
    a = ap.parse_args()
    recs = []
    for line in open(a.src, errors="ignore"):
        m = REC.match(line)
        if m:
            recs.append((m.group(1), m.group(2), m.group(3), repr(float(m.group(4)))))
    with open(OUT / "capri_supply_elas_market_1717.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "prod", "wrt", "value"])
        w.writerows(recs)
    own = defaultdict(list)
    for r, p, q, v in recs:
        if p == q and r in EU28:
            own[p].append(float(v))
    med = {RENAME.get(p, p): round(statistics.median(own[p]), 3) for p in sorted(own)}
    (OUT / "supply_elas_eu_all.json").write_text(json.dumps(med, indent=1))
    print(f"capri_supply_elas_market_1717.csv: {len(recs)} records; supply_elas_eu_all.json: {len(med)} products")


if __name__ == "__main__":
    main()

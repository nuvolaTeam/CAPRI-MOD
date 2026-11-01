"""CAPRI's market supply elasticities p_elasSupp at its 2017 calibration (elas1717defaulta.gdx) and their EU medians
(KNOWN_ISSUES K101).

    capri_data/sources/arm/capri_supply_elas_market_1717.csv   region, prod, wrt, value
        every record of p_elasSupp(region, prod, wrt, 'CAL') of the gdxdump p_elasSupp.txt, in its order; read by
        capri_mod/supply/capri_pmp.py (the livestock elasticities of the elasticity-calibrated PMP)
    capri_data/2017/market/supply_elas_eu.csv                  commodity, capri_code, elasticity, member_states
        per market commodity of the model (codes/model_commodities.csv, its CAPRI code), the median over the
        model's EU member states (those of CAPRI's EU trade blocks, shared/eu_market_blocks.csv: 26, BL =
        Belgium and Luxembourg) of the own-price p_elasSupp, where at least one has it; read by
        capri_mod/market/supply.py (the EU rows' own-price anticipation)

Until 29 October 2026 the EU medians were supply_elas_eu_all.json (no builder until that day): over CAPRI's EU28 (the
UK included), rounded to 3 decimals, keyed by CAPRI's code for OLIO, RICE, SUGA, TWIN (the model's OLIV, PARI, SUGR,
WINE never found them) and with INPE, the price index of the non-agricultural good. Replaced at the project lead's
decision of 29 October 2026 (the model's 27 member states and the model's codes).

    python tools/build/build_capri_supply_elas_market.py [--src p_elasSupp.txt]
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS  # noqa: E402  CAPRI's EU member states (shared/eu_market_blocks.csv)

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("/mnt/user-data/uploads/p_elasSupp.txt")
OUT = ROOT / "capri_data" / "sources" / "arm"
REC = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'CAL'\s+([^,\s]+)")


def eu_member_states() -> set:
    """CAPRI's EU member states: those of its EU trade blocks (shared/eu_market_blocks.csv)."""
    return set(EU_MS)


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
    eu = eu_member_states()
    own = defaultdict(dict)
    for r, p, q, v in recs:
        if p == q and r in eu:
            own[p][r] = float(v)
    with open(ROOT / "capri_data" / "codes" / "model_commodities.csv", newline="") as f:
        comm = [(r["code"], r["capri_code"]) for r in csv.DictReader(f)]
    rows = [(c, cc, repr(statistics.median(own[cc].values())), len(own[cc])) for c, cc in comm if own.get(cc)]
    with open(ROOT / "capri_data" / "2017" / "market" / "supply_elas_eu.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["commodity", "capri_code", "elasticity", "member_states"])
        w.writerows(rows)
    print(f"capri_supply_elas_market_1717.csv: {len(recs)} records; supply_elas_eu.csv: {len(rows)} commodities "
          f"(of {len(comm)}) over {len(eu)} member states")

if __name__ == "__main__":
    main()

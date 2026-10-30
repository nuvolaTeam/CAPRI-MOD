"""The EU's feed use of the oilseed cakes in the base period: the weights of the supply models' protein-feed cake index
(RegionalSupplyModel._cake_index; KNOWN_ISSUES K101).

    capri_data/2017/market/eu_cake_feed_bas.csv   product, feed_kt

feed_kt = sum over CAPRI's EU member states of p_dataMarket(MS, 'FEDM', cake, 'BAS') / 1000 (tonnes to 1000 t), cakes
RAPC, SUNC, SOYC, from CAPRI's FAO_agg market data (fao_agg_17_datamarket.txt, the export the market builders read).
The member states: those of CAPRI's EU trade blocks, shared/eu_market_blocks.csv (26, BL =
Belgium and Luxembourg). Until 29 October 2026 the weights were read from capri_oilseed_products_baseline.json, a file
without builder whose other contents no code read (removed).

    python tools/build/build_eu_cake_feed.py [--src FILE]
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS  # noqa: E402  CAPRI's EU member states (shared/eu_market_blocks.csv)

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt")
OUT = ROOT / "capri_data" / "2017" / "market" / "eu_cake_feed_bas.csv"
CAKES = ("RAPC", "SUNC", "SOYC")


def eu_member_states() -> list[str]:
    """CAPRI's EU member states: those of its EU trade blocks (shared/eu_market_blocks.csv)."""
    return sorted(EU_MS)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC)
    a = ap.parse_args()
    ms = eu_member_states()
    pat = re.compile(r"^'(" + "|".join(ms) + r")'\.'FEDM'\.'(" + "|".join(CAKES) + r")'\.'BAS'\s+([-\d.Ee+]+)")
    tot, seen = defaultdict(float), defaultdict(set)
    for line in open(a.src, errors="ignore"):
        m = pat.match(line)
        if m:
            tot[m.group(2)] += float(m.group(3)) / 1000.0
            seen[m.group(2)].add(m.group(1))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["product", "feed_kt"])
        for c in CAKES:
            w.writerow([c, repr(tot[c])])
    print(f"{OUT.name}: " + ", ".join(f"{c} {tot[c]:.2f} kt ({len(seen[c])} member states)" for c in CAKES)
          + f" of {len(ms)}")


if __name__ == "__main__":
    main()

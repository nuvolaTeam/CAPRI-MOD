"""The EU's trade blocks of CAPRI's market (market step E, eu_blocks): member state -> block, from CAPRI's region
aggregation file (KNOWN_ISSUES K101).

    capri_data/shared/eu_market_blocks.csv   ms, block, source

Rows: section 4 of gams/aggregation/defaultA.agg (one line per old region: code, name & new region & flag), the
member states mapped to EU_WEST or EU_EAST, in the file's order. Norway is added to EU_WEST: capri-mod's routing of its
supply models into the one-region EU market (CAPRI: its own market region NO000000; registered in
docs/DEPARTURES_FROM_CAPRI.md), not CAPRI's. Until 29 October 2026 the file had no builder.

    python tools/build/build_eu_market_blocks.py [--agg FILE]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGG = Path("/home/claude/work/allgms/gams/aggregation/defaultA.agg")
OUT = ROOT / "capri_data" / "shared" / "eu_market_blocks.csv"
BLOCKS = ("EU_WEST", "EU_EAST")
SOURCE = "gams/aggregation/defaultA.agg"
#: capri-mod's own row (not CAPRI's): Norway's supply models feed the EU market (registered)
NORWAY = ("NO000000", "EU_WEST", "capri-mod: Norway has supply models and feeds the EU market, as in the one-region EU "
                                 "(CAPRI: own market region NO000000; registered)")


def section4(path: Path) -> list[tuple[str, str]]:
    """(old region, new region) of the aggregation file's section 4."""
    lines = path.read_text(errors="ignore").splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().lower().startswith("! section 4"))
    seps = [i for i in range(start, len(lines)) if lines[i].strip().startswith("= = =")]
    out = []
    for l in lines[seps[0] + 1:seps[1]]:
        if not l.strip() or l.lstrip().startswith(("!", "*")):
            continue
        parts = [p.strip() for p in l.split("&")]
        m = re.match(r"(\S+)", parts[0])
        if m and len(parts) >= 2:
            out.append((m.group(1), parts[1]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agg", type=Path, default=AGG)
    a = ap.parse_args()
    rows = [(r, b, SOURCE) for r, b in section4(a.agg) if b in BLOCKS]
    if not rows:
        raise SystemExit(f"no member state mapped to {BLOCKS} in {a.agg}")
    rows.append(NORWAY)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ms", "block", "source"])
        w.writerows(rows)
    print(f"{OUT.name}: {len(rows) - 1} member states from {a.agg.name}, plus Norway (capri-mod)")


if __name__ == "__main__":
    main()

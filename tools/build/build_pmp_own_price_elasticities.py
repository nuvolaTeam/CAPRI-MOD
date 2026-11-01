"""CAPRI's estimated own-price elasticities of the crops per CAPRI region, raw (KNOWN_ISSUES K101): the
elasticity-calibrated PMP's PMP_CAPRI source (docs/PMP_ELASTICITY_WIRING.md; bounded on load by
capri_pmp.dampen_elasticity), not the default PMP (CAPRI's 2030 terms).

    capri_data/2017/supply/pmp_own_price_elasticities.csv   region, crop, own_price_elas

PELA(region, crop, crop, year) of dat/estnlp/results.gdx (the gdxdump estnlp_PELA.txt that
tools/build/ingest_pela_gtap.py reads) at the latest year with a value, 2005 (PELA's last) where it has one (2,259
pairs) and an earlier year otherwise (116 pairs, as the file held them: BL310000 OFAR from 2001), every CAPRI region,
CAPRI's codes, in the dump's order of the pairs. Until 29 October 2026 the file had no builder (the same values at 16
significant digits). REGISTERED: CAPRI's own slope forecast reads PELA at 2004 (forecast_activity_slopes.gms, see
tools/build/build_pmp_recipe.py); this file's year rule is the committed file's, kept.

    python tools/build/build_pmp_own_price_elasticities.py [--dump-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DUMPS = Path("/home/claude/work/inputs/estnlp")
OUT = ROOT / "capri_data" / "2017" / "supply" / "pmp_own_price_elasticities.csv"
YEAR = "2005"
REC = re.compile(r"^'([^']+)'\.'([^']+)'\.'([^']+)'\.'(\d{4})'\s+([-\d.Ee+]+)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump-dir", type=Path, default=DUMPS)
    a = ap.parse_args()
    best: dict = {}                     # (region, crop) -> (year, value), the latest year up to YEAR
    for line in open(a.dump_dir / "estnlp_PELA.txt", errors="replace"):
        m = REC.match(line)
        if m and m.group(2) == m.group(3) and m.group(4) <= YEAR:
            k, y, v = (m.group(1), m.group(2)), m.group(4), float(m.group(5))
            if k not in best or y >= best[k][0]:
                if k in best and y == best[k][0] and v != best[k][1]:
                    raise SystemExit(f"PELA{k} {y}: two different values")
                best[k] = (y, v)
    vals = {k: v for k, (_, v) in best.items()}
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "crop", "own_price_elas"])
        for (r, c), v in vals.items():
            w.writerow([r, c, repr(v)])
    print(f"{OUT.name}: {len(vals)} region-crop pairs, {len({r for r, _ in vals})} CAPRI regions")


if __name__ == "__main__":
    main()

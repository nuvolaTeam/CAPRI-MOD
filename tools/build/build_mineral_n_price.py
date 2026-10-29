"""CAPRI's 2017 unit value of mineral N fertiliser per country (KNOWN_ISSUES K101): the fertiliser allocation's N price
(RegionalSupplyModel.use_fert_allocation).

    capri_data/2017/supply/mineral_n_price.csv   country, capri_code, eur_per_t_n

eur_per_t_n = UVAG of NITF of the member state's national row (res_17<MS>.txt: '<MS>000000'.'UVAG'.'NITF'.'Y', EUR per
t of N). Rows: the NUTS country prefixes of shared/capri_member_state_codes.csv whose CAPRI member state has a dump,
ordered by CAPRI code; where a prefix equals its CAPRI code (EL) the alias (GR) is left out, otherwise every prefix of
the code is a row (BE and LU for BL, IE for IR). Until 29 October 2026 the file had no builder (the same values
rounded to 2 decimals).

    python tools/build/build_mineral_n_price.py [dump dir, default /home/claude/work/capreg]
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "2017" / "supply" / "mineral_n_price.csv"


def main(dump_dir: Path) -> None:
    with open(ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv", newline="") as f:
        codes = [(r["nuts_prefix"], r["capri_ms"]) for r in csv.DictReader(f)]
    rows = []
    for ms in sorted({c for _, c in codes}):
        dump = dump_dir / f"res_17{ms[:2]}.txt"
        if not dump.exists():
            continue
        pat = re.compile(r"^'" + ms + r"'\.'UVAG'\.'NITF'\.'Y'\s+([-\d.Ee+]+)")
        v = next((float(m.group(1)) for m in map(pat.match, open(dump, errors="ignore")) if m), None)
        if v is None:
            raise SystemExit(f"{dump.name}: no UVAG of NITF for {ms}")
        prefixes = [p for p, c in codes if c == ms]
        if ms[:2] in prefixes:
            prefixes = [ms[:2]]
        rows += [(p, ms[:2], repr(v)) for p in prefixes]
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["country", "capri_code", "eur_per_t_n"])
        w.writerows(rows)
    print(f"{OUT.name}: {len(rows)} countries")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))

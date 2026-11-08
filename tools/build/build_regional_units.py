"""The model's regions: CAPRI's regional units (RU) of its supply models, under CAPRI's codes: the EU27, Norway, the
United Kingdom, Turkey and the Western Balkans (250 units, as CAPRI's Green Deal 2030 run). Which countries outside the
EU a run solves is the setting run.supply_countries_outside_eu (capri_mod.data.definitions.sup_noneu).

CAPRI solves one supply model per regional unit: RU(SRNUTS2) $ SUM(MAP_RR(MS, SRNUTS2), 1) (capmod/
define_regional_sets.gms l. 230; SRNUTS2 in sets.gms l. 7803): the NUTS-2 units of each member state, and one unit for
each member state without regional detail (DK, EE, LT, LV, SI, CY, MT, HR), whose code is the member state's own
(DK000000). Units without agriculture (urbanNUTS: BL100000, DE300000, DE500000, DE600000, ES630000, ES640000,
AT130000) carry no results and are not units of a run.

Source: the units of CAPRI's Green Deal 2030 run (sources/intermediate/capri_res/gd2030_endotech_ini_nbalance.parquet, CAPRI's own
results): a code ending in 000000 is a member state total, kept as a unit only where the member state has no other
code. Member states: capri_data/shared/capri_member_state_codes.csv, a unit's member state as
tools/lib/_model_regions.national_code gives it (TR100000 -> TUR, Turkey's code in sets.gms, MAP_RR TUR.SET.R_TUR).
With --dump-dir (one or more folders), each unit is checked to have CAPRI 2017 activity levels in the res_17<MS>.txt
dumps.

Output: capri_data/shared/regional_units.csv (region, capri_ms, country): country is the unit's NUTS-0 country, the
key the model aggregates regions by (aggregate_supply(by_country=True), mapped to CAPRI's member state by MS_CODE):
CAPRI's member state read back through capri_member_state_codes.csv, except BL400000, Luxembourg (sets.gms l. 6126),
in CAPRI's member state BL with Belgium. (CAPRI's own prefixes are not used as country keys: IR, Ireland in CAPRI, is
Iran among ISO country codes.)

    python tools/build/build_regional_units.py [--dump-dir capri_sources/capreg]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
from _model_regions import EU_MS, national_code  # noqa: E402  (shared/eu_market_blocks.csv, capri_member_state_codes.csv)

SRC = ROOT / "capri_data" / "sources" / "intermediate" / "capri_res" / "gd2030_endotech_ini_nbalance.parquet"
MS_FILE = ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv"
DEST = ROOT / "capri_data" / "shared" / "regional_units.csv"
CODE = re.compile(r"^[A-Z]{2}[A-Z0-9]{6}$")


#: CAPRI unit -> NUTS-0 country where CAPRI's member state holds two countries (sets.gms l. 6126)
COUNTRY_OF_UNIT = {"BL400000": "LU"}


def units() -> list[tuple[str, str, str]]:
    with open(MS_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    ms = {r["capri_ms"] for r in rows}
    # CAPRI member state -> NUTS-0 country: the file's first prefix per member state (BL: BE, LU; EL: EL, GR)
    ctry = {}
    for r in rows:
        ctry.setdefault(r["capri_ms"], r["nuts_prefix"])
    codes = set()
    for r in source_records(SRC):
        if CODE.match(r["region"]):
            codes.add(r["region"])
    by_ms = defaultdict(set)
    for c in codes:
        m = national_code(c)
        if m in ms:
            by_ms[m].add(c)
    out = []
    for m in sorted(by_ms):
        sub = sorted(c for c in by_ms[m] if c != m and not c.endswith("000000"))
        out += [(c, m, COUNTRY_OF_UNIT.get(c, ctry[m])) for c in (sub or [m])]
    return out


def check(rows, dumps: list[Path]):
    """Each unit has CAPRI 2017 activity levels (LEVL) in its member state's dump."""
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'[A-Za-z0-9_]+'\.'LEVL'\.'Y'\s+")
    seen = set()
    for p in sorted(x for d in dumps for x in d.glob("res_17*.txt")):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                seen.add(m.group(1))
    miss = [r for r, _, _ in rows if r not in seen]
    print(f"dump check: {len(rows) - len(miss)} of {len(rows)} units with 2017 levels; without: {miss}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, nargs="+", default=None)
    a = ap.parse_args()
    rows = units()
    with open(DEST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "capri_ms", "country"])
        w.writerows(rows)
    n = defaultdict(int)
    for _, m, _ in rows:
        n["EU27" if m in EU_MS else m] += 1
    print(f"wrote {DEST.relative_to(ROOT)}: {len(rows)} units: " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())))
    if a.dump_dir:
        check(rows, a.dump_dir)


if __name__ == "__main__":
    main()

"""The model's regions: CAPRI's regional units (RU) of the EU27 and Norway, under CAPRI's 8-character codes.

CAPRI solves one supply model per regional unit: RU(SRNUTS2) $ SUM(MAP_RR(MS, SRNUTS2), 1) (capmod/
define_regional_sets.gms l. 230; SRNUTS2 in sets.gms l. 7803): the NUTS-2 units of each member state, and one unit for
each member state without regional detail (DK, EE, LT, LV, SI, CY, MT, HR), whose code is the member state's own
(DK000000). Units without agriculture (urbanNUTS: BL100000, DE300000, DE500000, DE600000, ES630000, ES640000,
AT130000) carry no results and are not units of a run.

Source: the units of CAPRI's Green Deal 2030 run (sources/capri_res/gd2030_endotech_ini_nbalance.csv, CAPRI's own
results): a code ending in 000000 is a member state total, kept as a unit only where the member state has no other
code. Member states: capri_data/shared/capri_member_state_codes.csv (the EU27 and Norway; the UK, Turkey and the
Western Balkans are not modelled yet). With --dump-dir, each unit is checked to have CAPRI 2017 activity levels in
the res_17<MS>.txt dumps.

Output: capri_data/shared/regional_units.csv (region, capri_ms, country): country is the unit's NUTS-0 country, the
key the model aggregates regions by (aggregate_supply(by_country=True), mapped to CAPRI's member state by MS_CODE):
CAPRI's member state read back through capri_member_state_codes.csv, except BL400000, Luxembourg (sets.gms l. 6126),
in CAPRI's member state BL with Belgium. (CAPRI's own prefixes are not used as country keys: IR, Ireland in CAPRI, is
Iran among the market's ISO country codes, capri_mod.data.definitions.TRADE_REGIONS.)

    python tools/build/build_regional_units.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "capri_res" / "gd2030_endotech_ini_nbalance.csv"
MS_FILE = ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv"
DEST = ROOT / "capri_data" / "shared" / "regional_units.csv"
CODE = re.compile(r"^[A-Z]{2}[A-Z0-9]{6}$")


#: CAPRI unit -> NUTS-0 country where CAPRI's member state holds two countries (sets.gms l. 6126)
COUNTRY_OF_UNIT = {"BL400000": "LU"}


def units() -> list[tuple[str, str, str]]:
    with open(MS_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    ms = {r["capri_ms"] for r in rows if r["capri_ms"] != "UK000000"}
    # CAPRI member state -> NUTS-0 country: the file's first prefix per member state (BL: BE, LU; EL: EL, GR)
    ctry = {}
    for r in rows:
        ctry.setdefault(r["capri_ms"], r["nuts_prefix"])
    codes = set()
    with open(SRC, newline="") as f:
        for r in csv.DictReader(f):
            if CODE.match(r["region"]):
                codes.add(r["region"])
    by_ms = defaultdict(set)
    for c in codes:
        if c[:2] + "000000" in ms:
            by_ms[c[:2] + "000000"].add(c)
    out = []
    for m in sorted(by_ms):
        sub = sorted(c for c in by_ms[m] if c != m)
        out += [(c, m, COUNTRY_OF_UNIT.get(c, ctry[m])) for c in (sub or [m])]
    return out


def check(rows, dump: Path):
    """Each unit has CAPRI 2017 activity levels (LEVL) in its member state's dump."""
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'[A-Za-z0-9_]+'\.'LEVL'\.'Y'\s+")
    seen = set()
    for p in sorted(dump.glob("res_17*.txt")):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                seen.add(m.group(1))
    miss = [r for r, _, _ in rows if r not in seen]
    print(f"dump check: {len(rows) - len(miss)} of {len(rows)} units with 2017 levels; without: {miss}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=None)
    a = ap.parse_args()
    rows = units()
    with open(DEST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "capri_ms", "country"])
        w.writerows(rows)
    n = defaultdict(int)
    for _, m, _ in rows:
        n[m[:2]] += 1
    print(f"wrote {DEST.relative_to(ROOT)}: {len(rows)} units ({sum(v for k, v in n.items() if k != 'NO')} EU27, "
          f"{n['NO']} Norway)")
    if a.dump_dir:
        check(rows, a.dump_dir)


if __name__ == "__main__":
    main()

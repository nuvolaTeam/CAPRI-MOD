"""CAPRI's EU27 activity levels, 2017 (CAPREG) and 2030 (CAPRI's Green Deal reference), for the baseline check.

tools/check/compare_baseline_capri.py compares the model's 2030 baseline with CAPRI star 3.0's own 2030 reference
(levels, market balances, prices) and the livestock growth 2017-2030. Until 29 October 2026 its two level files had no
builder (they arrived with the repository's first commit; KNOWN_ISSUES K103); this builder reproduces both exactly
(2030: every value as written; 2017: equal to the four decimals the old file kept).

  capri_data/validation/capri_eu27_levels_2030_ref.csv   act, val: dataOut('EU27yr19', '', act, 'LEVL', '2030') of the
      market model's output of CAPRI's Green Deal reference with the 2017 base (markmarket_greendeal_1730et_base_1717,
      GAMS text listing), in the listing's order; left out are the policy accounts the same symbol holds under LEVL
      (the budget items bud*, the PSE items PSE_*, the WTO boxes BlueBox, GreenBox, DeMinimis), which are not
      activity levels
  capri_data/validation/capri_eu27_levels_2017_capreg.csv   act, val: the sum over the 27 member states of CAPREG's
      base-year levels DATA2('<MS>000000', act, 'LEVL', 'Y') (res_17<CC>.txt dumps; Norway left out) for the
      livestock activities the check compares as growth: BULF, HEIF, HEIR, PIGF, POUF, SOWS, HENS

Levels in CAPRI's units (1000 ha, 1000 head; hens and poultry 1000 of the model's unit: compare_baseline_capri.py).

    python tools/build/build_capri_eu27_levels.py MARKMARKET.txt CAPREG_DUMP_DIR
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "validation"
#: CAPREG's livestock activities whose growth 2017-2030 the check compares (compare_baseline_capri.py)
ACTS_2017 = ["BULF", "HEIF", "HEIR", "PIGF", "POUF", "SOWS", "HENS"]
#: the policy accounts dataOut holds under LEVL for the EU aggregate: not activity levels
POLICY_ACCOUNT = re.compile(r"^(bud.*|PSE_.*|BlueBox|GreenBox|DeMinimis)$")
EU27 = ["AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
        "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]    # CAPREG's dump codes: 26 files, BL = Belgium-Luxembourg


def levels_2030(listing: Path):
    pat = re.compile(r"^'EU27yr19'\.''\.'([^']+)'\.'LEVL'\.'2030' ([^,\s]+)")
    out = []
    with open(listing, encoding="latin-1") as fh:
        for line in fh:
            if not line.startswith("'EU27yr19'.''."):
                continue
            m = pat.match(line)
            if m and not POLICY_ACCOUNT.match(m.group(1)):
                out.append((m.group(1), float(m.group(2))))
    return out


def levels_2017(dump_dir: Path):
    tot = {a: 0.0 for a in ACTS_2017}
    pat = re.compile(r"^'([A-Z]{2})000000'\.'([A-Z]+)'\.'LEVL'\.'Y' ([^,\s]+)")
    for cc in EU27:
        with open(dump_dir / f"res_17{cc}.txt", encoding="latin-1") as fh:
            for line in fh:
                m = pat.match(line)
                if m and m.group(2) in tot:
                    tot[m.group(2)] += float(m.group(3))
    return [(a, tot[a]) for a in ACTS_2017]


def _write(path: Path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("act,val\n")
        for a, v in rows:
            fh.write(f"{a},{v!r}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markmarket", type=Path)
    ap.add_argument("capreg_dir", type=Path)
    a = ap.parse_args()
    r30 = levels_2030(a.markmarket)
    r17 = levels_2017(a.capreg_dir)
    _write(OUT / "capri_eu27_levels_2030_ref.csv", r30)
    _write(OUT / "capri_eu27_levels_2017_capreg.csv", r17)
    print(f"{len(r30)} EU27 levels 2030, {len(r17)} EU27 levels 2017 -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

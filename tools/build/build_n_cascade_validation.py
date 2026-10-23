"""CAPRI's per-head nitrogen losses and option shares from its Green Deal reference run with endogenous technologies
(res_2_1730greendeal_refpol_endotech_all_inidefaulta, ghgAbatement on), for the check of the N loss cascade
(capri_mod/supply/n_cascade.py; test_n_cascade_reproduces_capri).

Input: the run's result dump in GAMS text form ('REGION'.'KEY'.'COL'.'ROW'.'2030' value), path as the first argument
(default /mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv). Regions: DE110000,
NL220000, PL220000, DK000000 (others as further arguments).
Output: capri_data/validation/n_cascade_capri_gd2030.csv (region, key, col, row, value) with the animal activities'
MANN and loss rows (NH3/NOX/N2O at grazing, MAN, APP; GASANI, RUNANI), the option shares (key SHARE) and the
regional mineral-fertiliser rows (MINFER, NH3MIN, GASMIN, RUNMIN; NITF), and anaerobic digestion's MaxShare, cost and
revenue per head (tools/build/build_ad_option.py; test_ad_option_reproduces_capri).
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "validation" / "n_cascade_capri_gd2030.csv"
ROWS = {"MANN", "DAYS", "NH3GRA", "NOXGRA", "N2OGRA", "NH3MAN", "NOXMAN", "N2OMAN", "NH3APP", "NOXAPP", "N2OAPP", "GASANI",
        "RUNANI"}
REG_ROWS = {"MINFER", "NH3MIN", "GASMIN", "RUNMIN"}


def main(src, regions):
    pat = re.compile(r"'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\.'2030'\s+(\S+)")
    regs = tuple(f"'{r}'." for r in regions)
    out = []
    with open(src) as fh:
        for line in fh:
            if not line.startswith(regs):
                continue
            m = pat.match(line)
            if not m:
                continue
            reg, key, col, row, v = m.groups()
            try:
                v = float(v.rstrip(","))
            except ValueError:
                continue
            if (key == "" and row in ROWS) or key == "SHARE" or (key == "" and col in REG_ROWS and row == "NITF") \
                    or (key in ("MaxShare", "cost", "revenue") and row == "AD_AnCh"):
                out.append([reg, key, col, row, v])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "key", "col", "row", "value"])
        w.writerows(out)
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"
    regs = sys.argv[2:] or ["DE110000", "NL220000", "PL220000", "DK000000"]
    print(len(main(src, regs)), "rows ->", OUT)

"""CAPRI's land-use change (LUC) transition model data (supply/supply_model.gms e_landTypes_to_LUclass,
e_luClassInitial, e_luClassFinal, e_FocLUC, e_derivativeOfGammaLUC; supply/prep_sim_luc.gms), from CAPRI's 2030
reference results (res_2_1730greendeal_refdefaulta, dataOut).

Per CAPRI region the dump carries the land types (ARAC, FRUN, GRAS, FORE, OLND, ARTIF, INLW, ARTO), the land-use
classes (CROP, FORE, ARTIF, GRSLND, WETLND, RESLND), the initial classes (INIxxx) and the 36 transitions (xxxyyy, per
year for changes, xxxxxx remaining) of CAPRI's solution. This builder checks CAPRI's identities:
  e_landTypes_to_LUclass  CROP = ARAC + FRUN; GRSLND = GRAS + shG OLND; WETLND = INLW + shW OLND; RESLND = shR OLND
  e_luClassInitial        sum_to T x f = INIxxx      (f = years per step for changes, 1 for remaining)
  e_luClassFinal          sum_from T x f = class
and records the step length f each region's solution implies (p_lucAnnualFac_sup).

Output: capri_data/2017/environment/luc_2030.csv  (capri_region, item, value): land types, classes, initial classes,
transitions, the OLND shares shG/shW/shR and the step length f.

    python tools/build/build_luc_2030.py [--dump res_2_1730greendeal_refdefaulta.zip]
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "2017" / "environment" / "luc_2030.csv"
CLS = {"CRP": "CROP", "FOR": "FORE", "ART": "ARTIF", "GRS": "GRSLND", "WET": "WETLND", "RES": "RESLND"}
LT = ("ARAC", "FRUN", "GRAS", "FORE", "OLND", "ARTIF", "INLW", "ARTO")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip"))
    a = ap.parse_args()
    trans = [i + j for i in CLS for j in CLS]
    ini = ["INI" + k for k in CLS]
    rows_ = "|".join(list(LT) + list(CLS.values()) + trans + ini)
    pat = rf"^'[A-Z0-9]+'\.''\.'({rows_})'\.'LEVL'\.'2030'"
    p1 = subprocess.Popen(["unzip", "-p", str(a.dump)], stdout=subprocess.PIPE)
    out = subprocess.run(["grep", "-E", pat], stdin=p1.stdout, capture_output=True, text=True).stdout
    rx = re.compile(r"^'([A-Z0-9]+)'\.''\.'([A-Za-z]+)'\.'LEVL'\.'2030'\s+([-\d.Ee+]+)")
    v = {}
    for line in out.splitlines():
        m = rx.match(line)
        if m:
            v[(m.group(1), m.group(2))] = float(m.group(3))
    regions = sorted({r for r, _ in v if len(r) == 8})
    rows = []
    worst_i = worst_f = worst_c = 0.0
    fs = []
    for r in regions:
        g = lambda k: v.get((r, k), 0.0)
        if g("ARTO") <= 0 or g("OLND") <= 0:
            continue
        # step length f from the initial-class identities: INI_i = T_ii + f sum_{j != i} T_ij
        num = den = 0.0
        for i in CLS:
            ch = sum(g(i + j) for j in CLS if j != i)
            num += (g("INI" + i) - g(i + i)) * ch
            den += ch * ch
        f = num / den if den > 0 else 1.0
        fs.append(f)
        for i in CLS:
            lhs = g(i + i) + f * sum(g(i + j) for j in CLS if j != i)
            worst_i = max(worst_i, abs(lhs - g("INI" + i)) / max(1.0, g("INI" + i)))
            lhs = g(i + i) + f * sum(g(j + i) for j in CLS if j != i)
            worst_f = max(worst_f, abs(lhs - g(CLS[i])) / max(1.0, g(CLS[i])))
        olnd = g("OLND")
        shR = g("RESLND") / olnd
        shW = (g("WETLND") - g("INLW")) / olnd
        shG = 1.0 - shR - shW
        worst_c = max(worst_c, abs(g("ARAC") + g("FRUN") - g("CROP")) / max(1.0, g("CROP")),
                      abs(g("GRAS") + shG * olnd - g("GRSLND")) / max(1.0, g("GRSLND")))
        for k in list(LT) + list(CLS.values()) + trans + ini:
            rows.append(dict(capri_region=r, item=k, value=g(k)))
        for k, x in (("shG", shG), ("shW", shW), ("shR", shR), ("step", f)):
            rows.append(dict(capri_region=r, item=k, value=x))
    pd.DataFrame(rows).to_csv(OUT, index=False, float_format="%.10g")
    print(f"{OUT.relative_to(ROOT)}: {len(regions)} regions; step length median {np.median(fs):.3f} "
          f"(min {min(fs):.3f}, max {max(fs):.3f})")
    print(f"identities: initial classes worst {worst_i:.2e}, final classes worst {worst_f:.2e}, "
          f"land types -> classes worst {worst_c:.2e}")


if __name__ == "__main__":
    main()

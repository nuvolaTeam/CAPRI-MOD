"""CAPRI's CAP 2014-2020 greening (the policy of CAPRI's 2030 reference, pol_input/cap_after_2014/ref.gms ->
scen/Premiums/Greening/cap_2013_2020_greening.gms -> policy/define_greening_limits.gms), for the regional supply model
in CAPRI's form (supply_model.gms permGrasGreening_, ecoSetAside_, cropDivGreening_).

Outputs (capri_data/2017/policy/):
  cap_greening_2013_2020.csv  the policy file's settings, one row per item: active measures (permGras, cropDiv,
                              ecoSetAside), the ecological set-aside rate (greening_setasiderate, % of the arable
                              activities' area, efabasis UAAR: all crops but grassland), the weights of the activities
                              counting as ecological focus area (p_DPgreeningWeight: VSET, FALL 1, PULS 0.7, OFAR 0.7 x
                              its legume share, CATC 0.3, ISET 0)
  cap_greening_fleg_ms.csv    legume share of other arable fodder per member state (DATA(MS,"FLEG") = FPEG.LEVL /
                              OFAR.LEVL of the base year, define_greening_limits.gms), from the CAPREG dumps

    python tools/build/build_cap_greening.py [--capreg-dir /home/claude/work/capreg]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
POL = ROOT / "capri_data" / "2017" / "policy"

#: scen/Premiums/Greening/cap_2013_2020_greening.gms (star 3.0), as written there
SETTINGS = [
    ("active", "permGras", 1.0), ("active", "cropDiv", 1.0), ("active", "ecoSetAside", 1.0),
    ("setaside_rate_pct", "ARAB", 5.0),
    ("weight", "ISET", 0.0), ("weight", "OFAR", 0.7), ("weight", "VSET", 1.0), ("weight", "FALL", 1.0),
    ("weight", "PULS", 0.7), ("weight", "CATC", 0.3),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capreg-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    POL.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(SETTINGS, columns=["item", "key", "value"]).assign(
        source="star 3.0 scen/Premiums/Greening/cap_2013_2020_greening.gms").to_csv(
        POL / "cap_greening_2013_2020.csv", index=False)
    rx = re.compile(r"^'([A-Z]{2})000000'\.'(FPEG|OFAR)'\.'LEVL'\.'Y'\s+([-\d.Ee+]+)")
    rows = []
    for f in sorted(a.capreg_dir.glob("res_17*.txt")):
        v = {}
        with open(f, errors="ignore") as fh:
            for line in fh:
                m = rx.match(line)
                if m:
                    v[m.group(2)] = float(m.group(3))
                    ms = m.group(1)
        if "OFAR" in v and v["OFAR"] > 0:
            rows.append(dict(ms=ms, fpeg_kha=v.get("FPEG", 0.0), ofar_kha=v["OFAR"],
                             fleg_share=v.get("FPEG", 0.0) / v["OFAR"]))
    t = pd.DataFrame(rows)
    t.to_csv(POL / "cap_greening_fleg_ms.csv", index=False, float_format="%.8g")
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()

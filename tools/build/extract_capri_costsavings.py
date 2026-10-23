"""CAPRI's mitigation calibration runs: levels and marginals of v_Miti (costsavings_ini / _max).

CAPRI calibrates the cost functions of its breeding, low-N feed, feed supplement (linseed, nitrate,
3-NOP; line_nitr.gms), histosol fallowing, winter cover and tillage options on the marginal values of the implementation shares in two supply-only runs
(%ghgTechCali% = ini: options at their initial shares, = max: at their maximum shares), stored as
%results_in%\\envind\\costsavings_<ini|max>_<NTSLVL><BAS><SIM><miti_data_type>.gdx and loaded by
envind/breeding.gms, low_n_feed.gms, no_histosols.gms, cover_crops.gms, tillage.gms:
    costsaving0 (ini) / costsaving1 (max) = v_Miti.m / (LEVL x DAYS/365)   (per activity unit)

Input: gdxdump of the project lead's costsavings_ini_21730_jul15.gdx and costsavings_max_21730_jul15.gdx
(2030, jul15 mitigation data). Kept: v_Miti records of the options other than NOC with a level or a
marginal, EU regions (CAPRI 8-character codes).

Output: capri_data/sources/ghgtech/capri_costsavings_2030.csv
        (region, activity, technology, target, run, level, marginal)

    python tools/build/extract_capri_costsavings.py INI.csv MAX.csv
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PAT = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\.(L|M)\s+(\S+?),?\s*$")


def _num(v):
    """GAMS values: Eps is zero; +Inf/-Inf/NA are not values (None)."""
    v = v.strip().rstrip(",")
    if v.upper() == "EPS":
        return 0.0
    try:
        return float(v)
    except ValueError:
        return None


TECHS = {"GENET_YLD", "GENET_EFF", "GENET_REP", "LOWNFEED", "FALLOW", "WINTERCOV", "CONSTILL", "NOTILL", "LEGSH",
         # feed supplements (envind/line_nitr.gms; Sprint 9g): the totals carry costs and maximum shares
         "LINE_TOT", "NITR_TOT", "3NOP_TOT"}


def read(path, run):
    rec = {}
    in_v = False
    with open(path, errors="ignore") as fh:
        for line in fh:
            if line.startswith("positive Variable v_Miti") or line.startswith("Variable v_Miti"):
                in_v = True
                continue
            if in_v and (line.startswith("/;") or line.startswith("free ") or line.startswith("positive Variable")):
                break
            if not in_v:
                continue
            m = PAT.match(line)
            if not m:
                continue
            reg, act, tech, tgt, att, val = m.groups()
            if tech.upper() not in TECHS:
                continue
            k = (reg, act, tech, tgt, run)
            d = rec.setdefault(k, {"level": 0.0, "marginal": 0.0})
            x = _num(val)
            if x is not None:
                d["level" if att == "L" else "marginal"] = x
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ini", type=Path)
    ap.add_argument("max", type=Path)
    a = ap.parse_args()
    rows = []
    for path, run in ((a.ini, "ini"), (a.max, "max")):
        for (reg, act, tech, tgt, r), d in read(path, run).items():
            rows.append((reg, act, tech, tgt, r, d["level"], d["marginal"]))
    out = pd.DataFrame(rows, columns=["region", "activity", "technology", "target", "run", "level", "marginal"])
    dest = ROOT / "capri_data" / "sources" / "ghgtech" / "capri_costsavings_2030.csv"
    out.to_csv(dest, index=False, float_format="%.8g")
    print(f"wrote {dest.name}: {len(out)} rows")
    print(out.groupby(["technology", "target", "run"]).agg(n=("level", "size"), level_med=("level", "median"),
                                                          marg_med=("marginal", "median")).to_string())


if __name__ == "__main__":
    main()

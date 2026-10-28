"""How close does capri-mod's port of CAPRI's PMP recipe (tools/build/build_pmp_recipe.py --year 2030) come to CAPRI's own
2030 terms (the project lead's export, tools/build/build_pmp_2030.py)?

Compared per CAPRI region: each activity's curvature on its level (technologies collapsed, c = 1 / (1' Qt^-1 1)) and
each crop group's terms. Reported: the ratio recipe / CAPRI by activity (median and 10th / 90th percentile over the
regions, share of regions within 5%) and for the group terms.

With --year 2017 the recipe's 2017 terms are compared with CAPRI's base-year (CAPREG) terms of the model's regions
(capri_data/sources/capreg/pmp_quad_techn.csv: the first technology's diagonal term, Q(T1, T1) or Q(T, T); the group
terms pmp_quad_pact.csv).

    python tools/check/pmp_recipe_check.py [--year 2030|2017] [--out FILE]
"""
from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "baseline_pmp"


def collapsed(t: pd.DataFrame) -> pd.Series:
    out = {}
    for (r, a), blk in t.groupby(["region", "activity"]):
        techs = sorted(set(blk.tech1) | set(blk.tech2))
        Q = np.zeros((len(techs), len(techs)))
        for x in blk.itertuples():
            Q[techs.index(x.tech1), techs.index(x.tech2)] = x.value
        one = np.ones(len(techs))
        try:
            v = float(one @ np.linalg.solve(Q, one))
        except np.linalg.LinAlgError:
            continue
        if v > 0:
            out[(r, a)] = 1.0 / v
    return pd.Series(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2030)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    if a.year == 2017:
        check_2017(a)
        return
    ex = collapsed(_read_csv(SRC / "pmp_quad_techn_2030.csv"))
    rc = collapsed(_read_csv(SRC / f"recipe_{a.year}_quad_techn.csv"))
    j = pd.concat({"capri": ex, "recipe": rc}, axis=1).dropna()
    j["ratio"] = j.recipe / j.capri
    j.index.names = ["region", "activity"]
    g = j.groupby(level="activity")["ratio"]
    tab = pd.DataFrame({"regions": g.size(), "median": g.median(), "p10": g.quantile(0.1), "p90": g.quantile(0.9),
                        "within 5%": g.apply(lambda s: float(((s - 1).abs() < 0.05).mean()))})
    print("activity curvature, recipe / CAPRI's 2030 term")
    print(tab.round(3).to_string())
    print(f"all activities: {len(j)} region x activity pairs, within 5%: {((j.ratio - 1).abs() < 0.05).mean():.1%}, "
          f"within 20%: {((j.ratio - 1).abs() < 0.2).mean():.1%}")
    pe = _read_csv(SRC / "pmp_quad_pact_2030.csv").set_index(["region", "group1", "group2"])["value"]
    pr = _read_csv(SRC / f"recipe_{a.year}_quad_pact.csv").set_index(["region", "group1", "group2"])["value"]
    k = pd.concat({"capri": pe, "recipe": pr}, axis=1).dropna()
    d = k[k.index.get_level_values(1) == k.index.get_level_values(2)]
    rr = d.recipe / d.capri
    print(f"group diagonal terms: {len(d)}, ratio median {rr.median():.3f}, within 5%: {((rr - 1).abs() < 0.05).mean():.1%}; "
          f"all group terms: max abs difference / diagonal scale "
          f"{((k.recipe - k.capri).abs() / d.capri.abs().median()).max():.3f}")
    if a.out:
        j.to_csv(a.out)


def check_2017(a) -> None:
    cap = _read_csv(ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_techn.csv")
    rec = _read_csv(SRC / "recipe_2017_quad_techn.csv")
    rec = rec[(rec.tech1 == rec.tech2) & rec.tech1.isin(["T1", "T"])].drop_duplicates(["region", "activity"]).copy()
    rec["model_region"] = rec.region            # the model's regions are CAPRI's units since 27 October 2026
    j = cap.merge(rec, on=["model_region", "activity"], suffixes=("_capri", "_recipe"))
    j["ratio"] = j.value_recipe / j.value_capri
    g = j.groupby("activity")["ratio"]
    tab = pd.DataFrame({"regions": g.size(), "median": g.median(), "p10": g.quantile(0.1), "p90": g.quantile(0.9),
                        "within 5%": g.apply(lambda s: float(((s - 1).abs() < 0.05).mean()))})
    print("2017: first technology's term, recipe / CAPRI's CAPREG term (model regions named as CAPRI's)")
    print(tab.round(3).to_string())
    print(f"all: {len(j)} pairs, within 5%: {((j.ratio - 1).abs() < 0.05).mean():.1%}, "
          f"within 20%: {((j.ratio - 1).abs() < 0.2).mean():.1%}")
    cp = _read_csv(ROOT / "capri_data" / "sources" / "capreg" / "pmp_quad_pact.csv")
    rp = _read_csv(SRC / "recipe_2017_quad_pact.csv")
    rp["model_region"] = rp.region
    k = cp.merge(rp, on=["model_region", "group1", "group2"])
    rr = k.value_y / k.value_x
    print(f"group terms: {len(k)}, within 5%: {((rr - 1).abs() < 0.05).mean():.1%}")
    if a.out:
        j.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()

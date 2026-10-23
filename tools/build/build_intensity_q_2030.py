"""CAPRI's 2030 PMP terms of the intensity variants, per model region, for the model's intensity splits (K61).

The model's intensity splits (dairy DCOL / DCOH, fattening bulls BULL / BULH, heifers HEIL / HEIH, grassland
GRAE / GRAI; tools/build/build_dairy_intensity.py, build_cattle_intensity.py, build_grass_intensity.py) take their
curvature from CAPRI's own diagonal terms p_pmpQuadTechn of the two variants. Those builders read CAPRI's base-year
terms (capri_data/sources/capreg/pmp_quad_techn.csv: the first technology's diagonal per model region). This tool
writes the same file format from the terms at the 2030 calibration point, so the builders can add the 2030 curvature
beside the base year's:

  capri2030   CAPRI's exported 2030 terms (capri_data/sources/baseline_pmp/pmp_quad_techn_2030.csv, the project
              lead's export of pmppar_21730<CC>defaulta.gdx)
  recipe2030  capri-mod's own 2030 terms by CAPRI's recipe (recipe_2030_quad_techn.csv, tools/build/build_pmp_recipe.py)

Term: the activity's curvature on its level, its technology block collapsed (c = 1 / (1' Qt^-1 1): Q(T, T) of a
single-technology activity, as the animals and grassland; the set-aside and fodder crops have two).
Model regions: CAPRI's codes through capri_data/shared/nuts_crosswalk.json (aliases, then resolved), as
ingest_pmp_terms.py; a CAPRI code mapping to several model regions gives each the same term (the base-year file's
rule: the term of the CAPRI region the model region is named for).

Output: capri_data/sources/baseline_pmp/intensity_q_<tag>.csv (model_region, activity, value)

    python tools/build/build_intensity_q_2030.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "baseline_pmp"
ACTS = ("DCOL", "DCOH", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAMF", "CAFF", "CAMR", "CAFR", "GRAE", "GRAI",
        "VSET", "FALL", "ROOF", "OFAR")
FILES = {"capri2030": SRC / "pmp_quad_techn_2030.csv", "recipe2030": SRC / "recipe_2030_quad_techn.csv",
         # the base year's terms with both technologies (CAPREG's file keeps one diagonal term per activity): the
         # recipe's 2017 terms, for the set-aside split's base-year weights (tools/build/build_labour_setaside.py)
         "recipe2017": SRC / "recipe_2017_quad_techn.csv"}


def crosswalk() -> dict:
    cw = json.loads((ROOT / "capri_data" / "shared" / "nuts_crosswalk.json").read_text())
    rev = {}
    for model_region, codes in cw.get("aliases", {}).items():
        for c in codes:
            rev.setdefault(c, model_region)
    for model_region, c in cw["resolved"].items():
        rev.setdefault(c, model_region)
    return rev


def build(path: Path, rev: dict) -> pd.DataFrame:
    import numpy as np
    t = pd.read_csv(path)
    t = t[t.activity.isin(ACTS)]
    # one term per CAPRI region and activity on its level: the technology block collapsed, c = 1 / (1' Qt^-1 1)
    # (Q(T, T) for one technology; for fallow, whose T2 carries no term, Q(T1, T1)); the animals and grassland
    # have one technology, the set-aside and fodder crops two
    rows = []
    for (r, a), blk in t.groupby(["region", "activity"]):
        techs = sorted(set(blk.tech1) | set(blk.tech2))
        Q = np.zeros((len(techs), len(techs)))
        for x in blk.itertuples():
            Q[techs.index(x.tech1), techs.index(x.tech2)] = x.value
        keep = [i for i in range(len(techs)) if Q[i, i] > 0]
        if not keep:
            continue
        Qk = Q[np.ix_(keep, keep)]
        try:
            v = float(np.ones(len(keep)) @ np.linalg.solve(Qk, np.ones(len(keep))))
        except np.linalg.LinAlgError:
            continue
        if v > 0:
            rows.append((r, a, 1.0 / v))
    t = pd.DataFrame(rows, columns=["region", "activity", "value"])
    t = t.assign(model_region=t.region.map(rev)).dropna(subset=["model_region"])
    t = t.drop_duplicates(["model_region", "activity"], keep="last")
    return t[["model_region", "activity", "value"]].sort_values(["model_region", "activity"])


def main() -> None:
    rev = crosswalk()
    for tag, path in FILES.items():
        if not path.exists():
            print(f"{tag}: {path.name} missing, skipped")
            continue
        d = build(path, rev)
        out = SRC / f"intensity_q_{tag}.csv"
        d.to_csv(out, index=False, float_format="%.10g")
        print(f"wrote {out.name}: {len(d)} rows, {d.model_region.nunique()} model regions, "
              f"activities {sorted(d.activity.unique())}")


if __name__ == "__main__":
    main()

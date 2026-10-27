"""CAPRI's 2030 PMP terms of the animal activities, as herd curvature per model region and animal (K61, item 1).

CAPRI's animal activities carry one PMP term each at the 2030 baseline calibration, p_pmpQuadTechn(r, act, 'T', 'T')
(supply/supply_model.gms QUADRA_: 1/2 x_act^2 q_act; no cross terms between animals). The model's animals sum CAPRI's
activities (tools/build/build_livestock_output_coef.CAPRI_TO_MODEL):

  DCOW = DCOL + DCOH     BULL = BULL + BULH     HFRS = HEIL + HEIH + HEIR     BCOW = SCOW
  CALV = CAMF + CAFF + CAMR + CAFR     PIGS = SOWS     PIGF = PIGF     LAYS = HENS     BROI = POUF
  SHGM = SHGM     SHGF = SHGF

Herd curvature in CAPRI's level units, per CAPRI region:
  - activities the model gives their own levels by split columns z (DCOL/DCOH, BULL/BULH, HEIL/HEIH/HEIR, CAMF/CAMR,
    CAFF/CAFR; harmonic of the terms, below; for a pair:)
    (tools/build/build_dairy_intensity.py, build_cattle_intensity.py): with the split free, the pair's level costs
    1/2 c X^2, c = q_low q_high / (q_low + q_high) (the Schur complement of the pair's terms in the herd and the split,
    whatever the split's base share);
  - the other members in fixed proportions (the model's per-head coefficients are fixed mixes): h = sum_j q_j s_j^2,
    s_j = the member's share of the animal's CAPRI level (a pair counts as one member with its c).
Territories with several CAPRI regions (tools/lib/_model_regions.capri_groups, Norway as tools/build/build_capri_base): the herd
responses add up, h = 1 / sum_c (1 / h_c) on the summed levels X.
Written as g = h X / r (X the territory's CAPRI 2030 level of the animal's activities, r = capri_level_ratio, the model's
heads per CAPRI level unit); at runtime Q = g / x with the model region's base herd x, as for the crops
(PMPCalibrator: Q_ij = g_ij / sqrt(x_i x_j)). For a region holding the share w of its territory, x = w r X and
Q = h / (w r^2): the elasticity of CAPRI's territory, with the model's revenue per head (CAPRI's per level unit / r).
(The first version wrote g = h X^2, which made the herds 100-25000 times too steep: corrected the same night.)

The splits' own curvature (q_low, q_high, q_z in dairy_intensity.csv, cattle_intensity.csv) takes the 2030 terms at the
2030 market year (q_<x>_capri2030 / _recipe2030, tools/build/build_intensity_q_2030.py).

Sources: capri_data/sources/baseline_pmp/pmp_quad_techn_2030.csv (tools/build/build_pmp_2030.py); CAPRI 2030 levels LEVL of
res_2_1730greendeal_refpol_endotech_all_inidefaulta. Output: capri_data/2017/supply/pmp_capri_2030_animals.csv
(region, animal, g, x_capri, level_ratio, capri_regions)

    python tools/build/build_animal_pmp_capri_2030.py [--ref FILE]
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "baseline_pmp" / "pmp_quad_techn_2030.csv"
OUT = ROOT / "capri_data" / "2017" / "supply" / "pmp_capri_2030_animals.csv"
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
#: model animal -> members; a tuple is an intensity pair whose split the model carries
#: tuples: activities the model gives their own levels inside the animal (split columns), whose herd curvature is the
#: harmonic 1 / sum(1 / q_j) of their terms (the Schur complement for a pair).
#: MEMBERS (default, the model's default): the intensity pairs only (DCOL/DCOH, BULL/BULH, HEIL/HEIH); HEIR and the
#: calves enter as single activities. MEMBERS_SPLITS (--splits, written to <stem>_animals_members.csv): the heifers'
#: three (HEIL, HEIH and the replacement heifers HEIR) and the calves per sex (fattening against raising), for the
#: model's cattle member splits (RegionalSupplyModel.use_cattle_member_splits, off by default since 22 October 2026:
#: the young-animal markets per sex did not converge yet, KNOWN_ISSUES K65)
MEMBERS = {"DCOW": [("DCOL", "DCOH")], "BULL": [("BULL", "BULH")], "HFRS": [("HEIL", "HEIH"), "HEIR"],
           "BCOW": ["SCOW"], "CALV": ["CAMF", "CAFF", "CAMR", "CAFR"], "PIGS": ["SOWS"], "PIGF": ["PIGF"],
           "LAYS": ["HENS"], "BROI": ["POUF"], "SHGM": ["SHGM"], "SHGF": ["SHGF"]}
MEMBERS_SPLITS = {"DCOW": [("DCOL", "DCOH")], "BULL": [("BULL", "BULH")], "HFRS": [("HEIL", "HEIH", "HEIR")],
           "BCOW": ["SCOW"], "CALV": [("CAMF", "CAMR"), ("CAFF", "CAFR")], "PIGS": ["SOWS"], "PIGF": ["PIGF"],
           "LAYS": ["HENS"], "BROI": ["POUF"], "SHGM": ["SHGM"], "SHGF": ["SHGF"]}
ACTS = sorted({a for M in (MEMBERS, MEMBERS_SPLITS) for ms in M.values() for m in ms
               for a in (m if isinstance(m, tuple) else (m,))})



def levels_2017_dumps(acts) -> dict:
    """{CAPRI code: {activity: LEVL}} of CAPRI's 2017 results (res_17<MS>.txt), activities in acts, level > 0."""
    import glob
    out = defaultdict(dict)
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'LEVL'\.'Y'\s+([-\d.Ee+]+)")
    for f in glob.glob("/home/claude/work/capreg/res_17*.txt"):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m and m.group(2) in acts and float(m.group(3)) > 0:
                out[m.group(1)].setdefault(m.group(2), float(m.group(3)))
    return out

def ref_levels(ref: Path) -> dict:
    pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({'|'.join(ACTS)})'\.'LEVL'\.'2030'"
    txt = subprocess.run(["grep", "-E", pat, str(ref)], capture_output=True, text=True).stdout
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z]+)'\.'LEVL'\.'2030'\s+([-\d.Ee+]+)")
    out = defaultdict(dict)
    for line in txt.splitlines():
        m = rx.match(line)
        if m and float(m.group(3)) > 0:
            out[m.group(1)][m.group(2)] = float(m.group(3))
    return out


def herd_curvature(q: dict, lev: dict, members) -> tuple:
    """(h, X) of one CAPRI region for one model animal, or (None, X) without usable terms."""
    parts = []                                         # (curvature, level) per member
    for m in members:
        if isinstance(m, tuple):
            L = sum(lev.get(x, 0.0) for x in m)
            if L <= 0:
                continue
            qs = [q.get(x) for x in m if lev.get(x, 0.0) > 0]
            if qs and all(qq and qq > 0 for qq in qs):
                parts.append((1.0 / sum(1.0 / qq for qq in qs), L))    # harmonic (the pair's Schur complement)
            elif any(qq and qq > 0 for qq in qs):     # members without a term: those with one
                parts.append((1.0 / sum(1.0 / qq for qq in qs if qq and qq > 0), L))
            else:
                return None, L
        else:
            L = lev.get(m, 0.0)
            if L <= 0:
                continue
            if not (q.get(m) and q[m] > 0):
                return None, L
            parts.append((q[m], L))
    X = sum(L for _, L in parts)
    if X <= 0:
        return None, 0.0
    return sum(c * (L / X) ** 2 for c, L in parts), X


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--techn", type=Path, default=None,
                    help="CAPRI-format technology terms (default: CAPRI's 2030 export, pmp_quad_techn_2030.csv); e.g. "
                         "recipe_2017_quad_techn.csv of tools/build/build_pmp_recipe.py")
    ap.add_argument("--year", type=int, choices=(2017, 2030), default=2030,
                    help="levels of the calibration point: 2030 CAPRI's 2030 reference, 2017 CAPRI's 2017 results")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--splits", action="store_true",
                    help="the cattle member splits' grouping (MEMBERS_SPLITS); default output name <stem>_animals_members.csv")
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import _model_regions as mr
    t = _read_csv(a.techn or SRC)
    t = t[(t.tech1 == "T") & (t.tech2 == "T") & t.activity.isin(ACTS)]
    Q = defaultdict(dict)
    for r in t.itertuples():
        Q[r.region][r.activity] = float(r.value)
    lev = ref_levels(a.ref) if a.year == 2030 else levels_2017_dumps(set(ACTS))
    OUT = a.out or (ROOT / "capri_data" / "2017" / "supply" / "pmp_capri_2030_animals.csv")
    if a.splits and a.out is None:
        OUT = OUT.with_name(OUT.stem + "_members.csv")
    members_of = MEMBERS_SPLITS if a.splits else MEMBERS
    regions = mr.model_regions()
    _c2g, groups = mr.capri_groups(regions)
    covered = {r for _, (_, rs) in groups.items() for r in rs}
    nat = defaultdict(set)
    for r in regions:
        if r not in covered:
            nat[mr.national_code(r)].add(r)
    territory = [(sorted(cs), sorted(rs)) for _, (cs, rs) in groups.items()] + \
                [([c], sorted(rs)) for c, rs in nat.items() if rs]
    ratio = _read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0)
    rows, missing = [], defaultdict(list)
    for cs, rs in territory:
        for animal, members in members_of.items():
            inv, X, used = 0.0, 0.0, []
            ok = True
            for c in cs:
                h, Xc = herd_curvature(Q.get(c, {}), lev.get(c, {}), members)
                if Xc <= 0:
                    continue
                if h is None:
                    ok = False
                    break
                inv += 1.0 / h
                X += Xc
                used.append(c)
            if not ok or inv <= 0 or X <= 0:
                if any(lev.get(c, {}).get(x) for c in cs for x in ACTS):
                    missing[animal].append(",".join(rs))
                continue
            h = 1.0 / inv
            for r in rs:
                rr = float(ratio.at[r, animal]) if r in ratio.index and animal in ratio.columns else float("nan")
                if not (rr == rr and rr > 0):
                    missing[animal].append(r)
                    continue
                rows.append((r, animal, h * X / rr, X, rr, " ".join(used)))
    df = pd.DataFrame(rows, columns=["region", "animal", "g", "x_capri", "level_ratio", "capri_regions"])
    df.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(df)} region x animal entries, {df.region.nunique()} regions; "
          f"territories without terms: { {k: len(v) for k, v in missing.items()} }")


if __name__ == "__main__":
    main()

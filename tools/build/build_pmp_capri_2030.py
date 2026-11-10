"""CAPRI's 2030 PMP matrix of the crop activities, per model region (KNOWN_ISSUES K61, decision 5a.5).

CAPRI's PMP terms (supply/supply_model.gms QUADRA_ l. 5284, GRPLEVL_ l. 4892; p_useCropSpecificQMatrix = 0):

    PMP cost = sum_act,a  p_pmpCnst x_a
             + 1/2 sum_act sum_a,a1 x_act,a x_act,a1 p_pmpQuadTechn(act, a, a1)          (technology terms)
             + 1/2 sum_grp,grp1 L_grp L_grp1 p_pmpQuadPact(grp, grp1)                      (group terms)
    L_grp = sum of the levels of the group's crops (EPRD_TO_GRP: CERE, CER2, OILS, OARA, FARA)

The model has one activity per crop where CAPRI has two technologies (T1 high-yield, T2 low-yield, capmod.gms
l. 246), and some model activities sum several CAPRI ones (GRAS = GRAE + GRAI, SETA = VSET + FALL; OFOD = OFAR + ROOF until S2, 7 November 2026).
Its curvature on the model's activity levels is derived exactly for a quadratic cost whose linear terms adjust:
  1. technologies: the cost of a crop's level X split optimally over its technologies is 1/2 c X^2 with
     c = 1 / (1' Qt^-1 1) (Qt the crop's technology block; c = Qt for a crop with one technology T);
  2. the CAPRI region's Hessian on its crops: H = diag(c) + E P E' (E the crops' group indicator, P the group terms,
     symmetric from CAPRI's upper-triangular storage);
  3. aggregation to model activities and territory groups (tools/lib/_model_regions.capri_groups: CAPRI and model regions
     covering the same territory; else the member state): the response of a sum is the sum of the responses, so
     H_model = (sum over CAPRI regions of A H^-1 A')^-1, A mapping CAPRI crops to model activities.
Written as g_ij = H_model,ij x sqrt(X_i X_j), with X the group's CAPRI 2030 levels (EUR per ha for a 100% change of the
levels). At runtime Q_ij = g_ij / sqrt(x_i x_j) with the model region's own base levels x: a region that is a part of
CAPRI's territory group gets the curvature of its share, so each region's relative response equals the group's.

Animals keep the model's elasticity-calibrated terms (CAPRI's animal terms include intensity variants DCOL/DCOH,
BULL/BULH and CAPRI's feed PMP terms, a separate step).

Sources: capri_data/sources/intermediate/baseline_pmp/pmp_quad_techn_2030.parquet, pmp_quad_pact_2030.parquet (tools/build/build_pmp_2030.py,
exported from the project lead's CAPRI 2030 baseline calibration); CAPRI 2030 levels LEVL from the 2030 Green Deal
baseline the model's trajectory is built from (res_2_1730greendeal_refdefaulta, tools/lib/paths.BASELINE_REF): with
the model's base at those levels, Q = H there, CAPRI's own curvature (its calibration run refpol_endotech_all_ini until
9 November 2026, when the base moved to the Green Deal baseline).
Outputs: capri_data/2030/supply/pmp_capri_2030_mix.csv (S1's mix columns, mix_terms; the default run only) and
capri_data/2030/supply/pmp_capri_2030.csv (region, act_i, act_j, g, x_i, x_j, capri_regions); g in the
model's 2017 money: CAPRI's 2030 terms over CAPRI's inflation to 2030 (tools/lib/_money.deflator, the deflator the
2030 prices take; KNOWN_ISSUES K108, 31 October 2026: before, in CAPRI's 2030 money)

    python tools/build/build_pmp_capri_2030.py [--ref FILE]
"""
from __future__ import annotations
import argparse, re, sys
from collections import defaultdict
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import SOURCES, BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp"
OUT = ROOT / "capri_data" / "2030" / "supply" / "pmp_capri_2030.csv"
REF = BASELINE_REF
#: the mix columns' PMP terms (S1): g_xx_extra (Q_XX - c) X^2 to add to the crop's diagonal, g_xz and g_zz, per model
#: region and crop with both technologies, in the convention of OUT (g = Q x X^2 at CAPRI's 2030 level x, the model's
#: 2017 money)
OUT_MIX = ROOT / "capri_data" / "2030" / "supply" / "pmp_capri_2030_mix.csv"

#: CAPRI's EPRD_TO_GRP (gams/sets.gms l. 2918) and group order (storage of p_pmpQuadPact)
CAPRI_GRP = {"SWHE": "CERE", "DWHE": "CERE", "RYEM": "CERE", "BARL": "CERE", "OATS": "CERE",
             "MAIZ": "CER2", "OCER": "CER2", "PARI": "CER2", "RAPE": "OILS", "SUNF": "OILS", "SOYA": "OILS",
             "PULS": "OARA", "POTA": "OARA", "SUGB": "OARA", "MAIF": "FARA", "ROOF": "FARA", "OFAR": "FARA"}
#: model crop -> CAPRI activities with PMP terms (tools/build/build_capri_base.CROP_MAP; GRAS and SETA by their
#: CAPRI components that carry terms: GRAS = GRAE + GRAI, SETA = VSET + FALL)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
MODEL_TO_CAPRI = dict(_MC.CROP_MAP_CAPMOD)
CAPRI_TO_MODEL = {c: m for m, cs in MODEL_TO_CAPRI.items() for c in cs}



def levels_2017_dumps(acts) -> dict:
    """{CAPRI code: {activity: LEVL}} of CAPRI's 2017 results (res_17<MS>.txt), activities in acts, level > 0."""
    import glob
    out = defaultdict(dict)
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'LEVL'\.'Y'\s+([-\d.Ee+]+)")
    for f in glob.glob(str(SOURCES / "capreg/res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = rx.match(line)
            if m and m.group(2) in acts and float(m.group(3)) > 0:
                out[m.group(1)].setdefault(m.group(2), float(m.group(3)))
    return out

def ref_levels(ref: Path) -> dict:
    acts = "|".join(sorted(CAPRI_TO_MODEL))
    pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({acts})'\.'LEVL'\.'2030'"
    txt = grep(pat, str(ref))
    rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'LEVL'\.'2030'\s+([-\d.Ee+]+)")
    out = defaultdict(dict)
    for line in txt.splitlines():
        m = rx.match(line)
        if m and float(m.group(3)) > 0:
            out[m.group(1)][m.group(2)] = float(m.group(3))
    return out


def capri_hessian(region: str, techn: pd.DataFrame, pact: pd.DataFrame, levels: dict):
    """(crops, H) of one CAPRI region on its crops' levels (technologies collapsed), crops with a level > 0."""
    t = techn[techn.region == region]
    c = {}
    for act, blk in t.groupby("activity"):
        if act not in CAPRI_TO_MODEL or levels.get(act, 0.0) <= 0:
            continue
        techs = sorted(set(blk.tech1) | set(blk.tech2))
        Qt = np.zeros((len(techs), len(techs)))
        for r in blk.itertuples():
            Qt[techs.index(r.tech1), techs.index(r.tech2)] = r.value
        one = np.ones(len(techs))
        try:
            v = float(one @ np.linalg.solve(Qt, one))
        except np.linalg.LinAlgError:
            continue
        if v > 0:
            c[act] = 1.0 / v
    crops = sorted(c)
    n = len(crops)
    H = np.diag([c[a] for a in crops])
    P = {}
    for r in pact[pact.region == region].itertuples():
        P[(r.group1, r.group2)] = P[(r.group2, r.group1)] = r.value
    for i, a in enumerate(crops):
        for j, b in enumerate(crops):
            ga, gb = CAPRI_GRP.get(a), CAPRI_GRP.get(b)
            if ga and gb and (ga, gb) in P:
                H[i, j] += P[(ga, gb)]
    return crops, H


def mix_terms(region: str, techn: pd.DataFrame) -> dict:
    """{CAPRI crop: (Q_XX - c, Q_Xz, Q_zz)} of one CAPRI region's crops with both technologies: CAPRI's 2x2 block Qt
    in the mix columns' variables (X, z), x_T1 = X/2 + z, x_T2 = X/2 - z (S1, docs/design/S1_MIX_COLUMNS.md section 2):
    M' Qt M with M = [[1/2, 1], [1/2, -1]]; c = 1 / (1' Qt^-1 1), the crop's curvature in capri_hessian (the Schur
    complement Q_XX - Q_Xz^2 / Q_zz, checked here)."""
    out = {}
    M = np.array([[0.5, 1.0], [0.5, -1.0]])
    t = techn[(techn.region == region) & techn.tech1.isin(["T1", "T2"]) & techn.tech2.isin(["T1", "T2"])]
    for act, blk in t.groupby("activity"):
        if set(blk.tech1) | set(blk.tech2) != {"T1", "T2"}:
            continue
        Qt = np.zeros((2, 2))
        for r in blk.itertuples():
            Qt[int(r.tech1[1]) - 1, int(r.tech2[1]) - 1] = r.value
        Qt = np.where(Qt == 0.0, Qt.T, Qt)                     # CAPRI stores one triangle of the symmetric block
        Q = M.T @ Qt @ M
        c = 1.0 / float(np.ones(2) @ np.linalg.solve(Qt, np.ones(2)))
        assert abs(Q[0, 0] - Q[0, 1] ** 2 / Q[1, 1] - c) <= 1e-9 * abs(c), (region, act)
        out[act] = (Q[0, 1] ** 2 / Q[1, 1], Q[0, 1], Q[1, 1])   # Q_XX - c exactly (0 for a symmetric block)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--techn", type=Path, default=None,
                    help="CAPRI-format technology terms (default: CAPRI's 2030 export, pmp_quad_techn_2030.parquet); e.g. "
                         "recipe_2017_quad_techn.parquet of tools/build/build_pmp_recipe.py")
    ap.add_argument("--year", type=int, choices=(2017, 2030), default=2030,
                    help="levels of the calibration point: 2030 CAPRI's 2030 reference, 2017 CAPRI's 2017 results")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import _model_regions as mr
    import _money
    # CAPRI's terms of the year's calibration are in its money of that year; the model's in 2017 money (K108)
    money = _money.deflator(a.year)
    ap_t = a.techn or SRC / "pmp_quad_techn_2030.parquet"
    techn = read_source(ap_t)
    pact = read_source(Path(str(ap_t).replace("_quad_techn", "_quad_pact")))
    lev = ref_levels(a.ref) if a.year == 2030 else levels_2017_dumps(set(CAPRI_TO_MODEL))
    OUT = a.out or (ROOT / "capri_data" / "2030" / "supply" / "pmp_capri_2030.csv")
    regions = mr.model_regions()
    code_to_group, groups = mr.capri_groups(regions)
    covered = {r for _, (_, rs) in groups.items() for r in rs}
    # model regions outside every regional group: their member state's CAPRI region (national rows, e.g. DK, CY)
    nat = defaultdict(set)
    for r in regions:
        if r not in covered:
            nat[mr.national_code(r)].add(r)
    territory = [(sorted(cs), sorted(rs)) for _, (cs, rs) in groups.items()] + \
                [([c], sorted(rs)) for c, rs in nat.items() if rs]
    have = set(techn.region)
    rows, n_groups, n_pd_fail, missing, mix_rows = [], 0, 0, [], []
    for cs, rs in territory:
        cs = [c for c in cs if c in have and c in lev]
        if not cs:
            missing.append(",".join(rs))
            continue
        macts = sorted({CAPRI_TO_MODEL[x] for c in cs for x in lev[c] if x in CAPRI_TO_MODEL})
        Hinv = np.zeros((len(macts), len(macts)))
        X = np.zeros(len(macts))
        ok = False
        for c in cs:
            crops, H = capri_hessian(c, techn, pact, lev[c])
            if not crops:
                continue
            if np.min(np.linalg.eigvalsh(0.5 * (H + H.T))) <= 0:
                n_pd_fail += 1
                continue
            A = np.zeros((len(macts), len(crops)))
            for j, x in enumerate(crops):
                A[macts.index(CAPRI_TO_MODEL[x]), j] = 1.0
                X[macts.index(CAPRI_TO_MODEL[x])] += lev[c][x]
            Hinv += A @ np.linalg.solve(H, A.T)
            ok = True
        if not ok:
            missing.append(",".join(rs))
            continue
        keep = [i for i in range(len(macts)) if Hinv[i, i] > 0 and X[i] > 0]
        Hm = np.linalg.inv(Hinv[np.ix_(keep, keep)])
        Hm = 0.5 * (Hm + Hm.T)
        n_groups += 1
        if len(cs) == 1:
            # the mix columns' terms (S1): one CAPRI region per model region (all 250 since S2), the crop's 2030 level
            # as the scale (g = Q x X^2, the convention of g below)
            for act, (dxx, xz, zz) in mix_terms(cs[0], techn).items():
                if act in CAPRI_TO_MODEL and lev[cs[0]].get(act, 0.0) > 0:
                    X2 = lev[cs[0]][act] ** 2
                    for r in rs:
                        mix_rows.append((r, CAPRI_TO_MODEL[act], dxx * X2 / money, xz * X2 / money, zz * X2 / money,
                                         lev[cs[0]][act], cs[0]))
        for r in rs:
            for ii, i in enumerate(keep):
                for jj, j in enumerate(keep):
                    if abs(Hm[ii, jj]) < 1e-12:
                        continue
                    rows.append((r, macts[i], macts[j], Hm[ii, jj] * np.sqrt(X[i] * X[j]) / money, X[i], X[j],
                                 " ".join(cs)))
    df = pd.DataFrame(rows, columns=["region", "act_i", "act_j", "g", "x_i", "x_j", "capri_regions"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    if a.out is None and a.techn is None and a.year == 2030:
        mx = pd.DataFrame(mix_rows, columns=["region", "activity", "g_xx_extra", "g_xz", "g_zz", "x", "capri_region"])
        mx.to_csv(OUT_MIX, index=False)
        print(f"{OUT_MIX.name}: {len(mx)} region x crop with both technologies, {mx.region.nunique()} model regions")
    print(f"{OUT.name}: {df.region.nunique()} model regions from {n_groups} territory groups, {len(df)} entries; "
          f"CAPRI regions with a non-positive-definite matrix skipped: {n_pd_fail}; without terms: {missing}")


if __name__ == "__main__":
    main()

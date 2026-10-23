"""CAPRI's 2030 PMP matrix of the crop activities, per model region (KNOWN_ISSUES K61, decision 5a.5).

CAPRI's PMP terms (supply/supply_model.gms QUADRA_ l. 5284, GRPLEVL_ l. 4892; p_useCropSpecificQMatrix = 0):

    PMP cost = sum_act,a  p_pmpCnst x_a
             + 1/2 sum_act sum_a,a1 x_act,a x_act,a1 p_pmpQuadTechn(act, a, a1)          (technology terms)
             + 1/2 sum_grp,grp1 L_grp L_grp1 p_pmpQuadPact(grp, grp1)                      (group terms)
    L_grp = sum of the levels of the group's crops (EPRD_TO_GRP: CERE, CER2, OILS, OARA, FARA)

The model has one activity per crop where CAPRI has two technologies (T1 high-yield, T2 low-yield, capmod.gms
l. 246), and some model activities sum several CAPRI ones (OFOD = OFAR + ROOF, GRAS = GRAE + GRAI, SETA = VSET + FALL).
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

Sources: capri_data/sources/baseline_pmp/pmp_quad_techn_2030.csv, pmp_quad_pact_2030.csv (tools/build/build_pmp_2030.py,
exported from the project lead's CAPRI 2030 baseline calibration); CAPRI 2030 levels LEVL from the 2030 reference
the model's trajectory is built from (res_2_1730greendeal_refpol_endotech_all_inidefaulta).
Output: capri_data/2017/supply/pmp_capri_2030.csv (region, act_i, act_j, g, x_i, x_j, capri_regions)

    python tools/build/build_pmp_capri_2030.py [--ref FILE]
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "baseline_pmp"
OUT = ROOT / "capri_data" / "2017" / "supply" / "pmp_capri_2030.csv"
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")

#: CAPRI's EPRD_TO_GRP (gams/sets.gms l. 2918) and group order (storage of p_pmpQuadPact)
CAPRI_GRP = {"SWHE": "CERE", "DWHE": "CERE", "RYEM": "CERE", "BARL": "CERE", "OATS": "CERE",
             "MAIZ": "CER2", "OCER": "CER2", "PARI": "CER2", "RAPE": "OILS", "SUNF": "OILS", "SOYA": "OILS",
             "PULS": "OARA", "POTA": "OARA", "SUGB": "OARA", "MAIF": "FARA", "ROOF": "FARA", "OFAR": "FARA"}
#: model crop -> CAPRI activities with PMP terms (tools/build/build_capri_base.CROP_MAP; GRAS and SETA by their
#: CAPRI components that carry terms: GRAS = GRAE + GRAI, SETA = VSET + FALL)
MODEL_TO_CAPRI = {"SWHE": ("SWHE",), "DWHE": ("DWHE",), "RYEM": ("RYEM",), "BARL": ("BARL",), "OATS": ("OATS",),
                  "CORN": ("MAIZ",), "OCER": ("OCER",), "PARI": ("PARI",), "PULS": ("PULS",), "OCRO": ("OCRO",),
                  "OIND": ("OIND",), "NURS": ("NURS",), "FLOW": ("FLOW",), "SUGB": ("SUGB",), "POTA": ("POTA",),
                  "TOMA": ("TOMA",), "OVEG": ("OVEG",), "APPL": ("APPL",), "OFRU": ("OFRU",), "CITR": ("CITR",),
                  "TAGR": ("TAGR",), "WINE": ("TWIN",), "OLIV": ("OLIV",), "TABO": ("TABO",), "TOBA": ("TOBA",),
                  "TEXT": ("TEXT",), "MAIF": ("MAIF",), "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",),
                  "OOIL": ("OOIL",), "OFOD": ("OFAR", "ROOF"), "GRAS": ("GRAE", "GRAI"), "SETA": ("VSET", "FALL")}
CAPRI_TO_MODEL = {c: m for m, cs in MODEL_TO_CAPRI.items() for c in cs}



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
    acts = "|".join(sorted(CAPRI_TO_MODEL))
    pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({acts})'\.'LEVL'\.'2030'"
    txt = subprocess.run(["grep", "-E", pat, str(ref)], capture_output=True, text=True).stdout
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--techn", type=Path, default=None,
                    help="CAPRI-format technology terms (default: CAPRI's 2030 export, pmp_quad_techn_2030.csv); e.g. "
                         "recipe_2017_quad_techn.csv of tools/build/build_pmp_recipe.py")
    ap.add_argument("--year", type=int, choices=(2017, 2030), default=2030,
                    help="levels of the calibration point: 2030 CAPRI's 2030 reference, 2017 CAPRI's 2017 results")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import _model_regions as mr
    ap_t = a.techn or SRC / "pmp_quad_techn_2030.csv"
    techn = pd.read_csv(ap_t)
    pact = pd.read_csv(Path(str(ap_t).replace("_quad_techn", "_quad_pact")))
    lev = ref_levels(a.ref) if a.year == 2030 else levels_2017_dumps(set(CAPRI_TO_MODEL))
    OUT = a.out or (ROOT / "capri_data" / "2017" / "supply" / "pmp_capri_2030.csv")
    regions = mr.model_regions()
    code_to_group, groups = mr.capri_groups(regions)
    covered = {r for _, (_, rs) in groups.items() for r in rs}
    # model regions outside every regional group: their member state's CAPRI region (national rows, e.g. DK, CY)
    nat = defaultdict(set)
    for r in regions:
        if r not in covered:
            nat[mr.national_code(r)].add(r)
    # Norway: NO01, NO03, NO04, NO05 (NUTS 2016) against CAPRI's NO08, NO09, NO0A (NUTS 2021), one territory as in
    # tools/build/build_capri_base.py (NORWAY_PARENTS / NORWAY_CHILDREN)
    import build_capri_base as bcb
    no_children = sorted(r for r in bcb.NORWAY_CHILDREN if r in regions)
    for r in no_children:
        nat.get(mr.national_code(r), set()).discard(r)
    territory = [(sorted(cs), sorted(rs)) for _, (cs, rs) in groups.items()] + \
                [([c], sorted(rs)) for c, rs in nat.items() if rs] + \
                ([(list(bcb.NORWAY_PARENTS), no_children)] if no_children else [])
    have = set(techn.region)
    rows, n_groups, n_pd_fail, missing = [], 0, 0, []
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
        for r in rs:
            for ii, i in enumerate(keep):
                for jj, j in enumerate(keep):
                    if abs(Hm[ii, jj]) < 1e-12:
                        continue
                    rows.append((r, macts[i], macts[j], Hm[ii, jj] * np.sqrt(X[i] * X[j]), X[i], X[j], " ".join(cs)))
    df = pd.DataFrame(rows, columns=["region", "act_i", "act_j", "g", "x_i", "x_j", "capri_regions"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, float_format="%.10g")
    print(f"{OUT.name}: {df.region.nunique()} model regions from {n_groups} territory groups, {len(df)} entries; "
          f"CAPRI regions with a non-positive-definite matrix skipped: {n_pd_fail}; without terms: {missing}")


if __name__ == "__main__":
    main()

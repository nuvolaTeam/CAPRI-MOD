"""Reproduce CAPRI's ammonia-technology cost curves (envind/ammo_tech.gms, l. ~1180-1535).

For each CAPRI region, animal activity, manure system and technology with a farm-size cost
curve (MitiTechAmmOpt: LowEmHous, CovStorLow, CovStorHigh, AirPur), statement by statement:

 1. holdings by size class (p_holdLSU; CAPRI splits 100_500 into 100_200 = 1/4, 200_500 = 3/4)
 2. heads per holding = heads / holdings (dairy and non-dairy cattle pooled)
 3. investment per animal = cif + civ / heads per holding; for storage covers the fixed part
    scales with stored volume: cif * storage months / 12 * MANN / kgN per m3 * 365 / DAYS
 4. operating cost = investment * fixed operating share + sum(extra input demand * national price)
    (from the UN-annualised investment, as in CAPRI)
 5. investment annualised: * (1+r)^lt * r / ((1+r)^lt - 1), r = 0.035
 6. average cost from each size class upward (head-weighted), and the same for operating cost
    alone (the lower bound)
 7. CAPRI's regression m_CostAmm: averCost(c) = alpha + accumShare(c) * beta, least squares
    weighted by head shares, alpha >= operating-cost lower bound of the largest class (h500)

Regional storage months = max(national, Nitrates-Directive minimum inside/outside vulnerable
zones weighted by the region's zone share). Animal categories without a farm-size curve
(HENS, POUF, SHGF, SHGM) are costed at h500 only and get no regression (CAPRI does the same).

SIMPLIFICATION (registered): where a region has no heads data, CAPRI falls back to its NUTS-1
parent; this builder falls back to the national figures.

Output: capri_data/2017/abatement/ammonia/ammonia_cost_curves.csv
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "ammonia"
C = D / "costs"

FS = ["0_5", "5_10", "10_15", "15_20", "20_50", "50_100", "100_200", "200_500", "h500"]
TECH_OPT = ["LowEmHous", "CovStorLow", "CovStorHigh", "AirPur"]
STORE = {"CovStorHigh", "CovStorLow"}
SYSTEMS = ["Liquid", "Solid"]
# map_animCat (ammo_tech.gms) and map_animals_all (prep_farm_size_data_for_miti.gms)
ANIM_CAT = {"DCOL": "DCow", "DCOH": "DCow", "BULL": "OCat", "BULH": "OCat", "HEIL": "OCat", "HEIH": "OCat",
            "HEIR": "OCat", "SCOW": "OCat", "CAMR": "OCat", "CAFR": "OCat", "CAMF": "OCat", "CAFF": "OCat",
            "PIGF": "Pigs", "SOWS": "Pigs", "HENS": "Hens", "POUF": "Pouf", "SHGF": "ShGt", "SHGM": "ShGt"}
AD_ACT = {"DCOL": "DAIRY", "DCOH": "DAIRY", "BULL": "NDAIRY", "BULH": "NDAIRY", "HEIL": "NDAIRY",
          "HEIH": "NDAIRY", "HEIR": "NDAIRY", "SCOW": "NDAIRY", "CAMR": "NDAIRY", "CAFR": "NDAIRY",
          "CAMF": "NDAIRY", "CAFF": "NDAIRY", "PIGF": "SWIN", "SOWS": "SWIN", "HENS": "HENS",
          "POUF": "POUF", "SHGM": "SHEEP", "SHGF": "SHEEP"}
NO_OPT = {"HENS", "POUF", "SHGF", "SHGM"}
R = 0.035


def _lc(s):
    return s.lower()


def load():
    inv = pd.read_csv(C / "p_invCoeff.csv")
    INV = {(r.technology, _lc(r.animal_cat), _lc(r.manure_system), r.coefficient): r.value for r in inv.itertuples()}
    add = pd.read_csv(C / "p_addDemand.csv")
    ADD = defaultdict(dict)
    for r in add.itertuples():
        ADD[(r.technology, _lc(r.animal_cat), _lc(r.manure_system))][r.input] = r.value
    # CAPRI's unit for hens and other poultry is 1000 animals, while tables A1 and A6 are per animal: ammo_tech.gms
    # multiplies the investment cif of housing and air purification (l. 153-157; storage covers are costed from manure
    # per 1000 animals already) and every extra input demand (l. 640-643) by 1000 for those two categories. Missing here
    # until 21 October 2026 (KNOWN_ISSUES K63)
    for k in list(INV):
        if k[1] in ("hens", "pouf") and k[3] == "cif" and k[0] in ("LowEmHous", "AirPur"):
            INV[k] = INV[k] * 1000.0
    for k, d in ADD.items():
        if k[1] in ("hens", "pouf"):
            for i in list(d):
                d[i] = d[i] * 1000.0
    fop = pd.read_csv(C / "p_fixedOpCost.csv")
    FOP = {(r.technology, _lc(r.animal_cat), _lc(r.manure_system)): r.value for r in fop.itertuples()}
    ic = pd.read_csv(C / "p_inputCost.csv")
    PRICE = defaultdict(dict)
    for r in ic.itertuples():
        PRICE[r.country][r.item] = r.value
    st = pd.read_csv(C / "p_storTime.csv")
    STOR = {(r.region, _lc(r.manure_system), _lc(r.animal_cat)): r.value for r in st.itertuples()}
    mn = pd.read_csv(C / "p_minStorCapND.csv")
    MIN = {(r.region, _lc(r.manure_system), r.nvz, _lc(r.animal_cat)): r.value for r in mn.itertuples()}
    kg = pd.read_csv(C / "p_kgNPerM3.csv")
    KGN = {(r.activity, _lc(r.manure_system)): r.value for r in kg.itertuples()}
    nvz = pd.read_csv(D / "p_nvzShare_lu.csv").set_index("region")["value"].to_dict()
    hd = pd.read_csv(D / "p_Heads.csv")
    HEADS = defaultdict(dict)
    for r in hd.itertuples():
        HEADS[(r.region, r.ad_activity)][r.size_class] = r.value
    hl = pd.read_csv(D / "p_holdLSU.csv")
    HOLD = defaultdict(dict)
    for r in hl.itertuples():
        g = r.animal_group.upper()
        if r.size_class == "100_500":
            HOLD[(r.region, g)]["100_200"] = HOLD[(r.region, g)].get("100_200", 0) + r.value / 4
            HOLD[(r.region, g)]["200_500"] = HOLD[(r.region, g)].get("200_500", 0) + r.value * 3 / 4
        else:
            HOLD[(r.region, g)][r.size_class] = HOLD[(r.region, g)].get(r.size_class, 0) + r.value
    md = pd.read_csv(D / "capri_mann_days_2030.csv")
    MD = {(r.region, r.activity, r.item): r.value for r in md.itertuples()}
    return INV, ADD, FOP, PRICE, STOR, MIN, KGN, nvz, HEADS, HOLD, MD


def nat(region):
    return region[:2] + "000000"


def stor_months(region, sysm, cat, STOR, MIN, nvz):
    n = STOR.get((nat(region), sysm, cat), 0.0)
    mi = MIN.get((region, sysm, "inNVZ", cat)); mo = MIN.get((region, sysm, "outNVZ", cat))
    if mi is None:
        mi = n
    if mo is None:
        mo = n
    s = float(nvz.get(region, 0.0))
    return max(n, mi * s + mo * (1 - s))


def heads_for(region, ad, HEADS):
    h = HEADS.get((region, ad))
    if not h or not sum(h.values()):
        h = HEADS.get((nat(region), ad), {})          # registered: national, not NUTS-1, fallback
    return h


def regress(share, accum, cost, lb):
    """min sum share*(a + accum*b - cost)^2  s.t. a >= lb  (CAPRI m_CostAmm)."""
    w = np.asarray(share); x = np.asarray(accum); y = np.asarray(cost)
    W = w.sum()
    if W <= 0:
        return None
    xm, ym = (w * x).sum() / W, (w * y).sum() / W
    sxx = (w * (x - xm) ** 2).sum()
    b = ((w * (x - xm) * (y - ym)).sum() / sxx) if sxx > 0 else 0.0
    a = ym - b * xm
    if a < lb:                                          # bound binds: a = lb, refit b
        a = lb
        sx2 = (w * x * x).sum()
        b = ((w * x * (y - a)).sum() / sx2) if sx2 > 0 else 0.0
    return a, b


def build():
    INV, ADD, FOP, PRICE, STOR, MIN, KGN, nvz, HEADS, HOLD, MD = load()
    regions = sorted({k[0] for k in MD if not k[0].endswith("000000") or k[0][:2] in ("MT", "CY", "LU", "EE", "LV", "SI")})
    out = []
    for rs in regions:
        price = PRICE.get(nat(rs), {})
        for act, cat in ANIM_CAT.items():
            if act in NO_OPT:
                continue
            ad = AD_ACT[act]
            heads = heads_for(rs, ad, HEADS)
            if ad in ("DAIRY", "NDAIRY"):
                hd_ = heads_for(rs, "DAIRY", HEADS); hn_ = heads_for(rs, "NDAIRY", HEADS)
                hold = HOLD.get((rs, ad)) or HOLD.get((nat(rs), ad), {})
                hph = {c: (hd_.get(c, 0) + hn_.get(c, 0)) / hold[c] for c in FS if hold.get(c)}
            else:
                hold = HOLD.get((rs, ad)) or HOLD.get((nat(rs), ad), {})
                hph = {c: heads.get(c, 0) / hold[c] for c in FS if hold.get(c)}
            tot = sum(heads.get(c, 0) for c in FS)
            if tot <= 0:
                continue
            mann, days = MD.get((rs, act, "MANN")), MD.get((rs, act, "DAYS"))
            for sysm in ("liquid", "solid"):
                for tech in TECH_OPT:
                    cl = (tech, cat.lower(), sysm)
                    if (tech, cat.lower(), sysm, "cif") not in INV:
                        continue
                    cif, civ, lt = (INV.get((tech, cat.lower(), sysm, k), 0.0) for k in ("cif", "civ", "lt"))
                    inv, op = {}, {}
                    for c in FS:
                        if not hph.get(c):
                            continue
                        if tech in STORE:
                            kg = KGN.get((act, sysm))
                            if not (kg and mann and days):
                                continue
                            fixed = cif * stor_months(rs, sysm, cat.lower(), STOR, MIN, nvz) / 12 * mann / kg * 365 / days
                        else:
                            fixed = cif
                        inv[c] = fixed + civ / hph[c]
                    for c, v in inv.items():
                        op[c] = v * FOP.get(cl, 0.0) + sum(q * price.get(k, 0.0) for k, q in ADD.get(cl, {}).items())
                    if lt and ((1 + R) ** lt - 1):
                        f = (1 + R) ** lt * R / ((1 + R) ** lt - 1)
                        inv = {c: v * f for c, v in inv.items()}
                    cls = [c for c in FS if c in inv and heads.get(c, 0) > 0]
                    if not cls:
                        continue
                    share, accum, acc, lbs = [], [], [], {}
                    for i, c in enumerate(FS):
                        if c not in inv:
                            continue
                        up = [c2 for c2 in FS[i:] if c2 in inv]
                        hu = sum(heads.get(c2, 0) for c2 in up)
                        if hu <= 0:
                            continue
                        share.append(heads.get(c, 0) / tot)
                        accum.append(hu / tot)
                        acc.append(sum((inv[c2] + op[c2]) * heads.get(c2, 0) for c2 in up) / hu)
                        lbs[c] = sum(op[c2] * heads.get(c2, 0) for c2 in up) / hu
                    lb = lbs.get("h500", min(lbs.values()) if lbs else 0.0)
                    res = regress(share, accum, acc, lb)
                    if res is None:
                        continue
                    a, b = res
                    out.append([rs, act, sysm.capitalize(), tech, a, b, lb, len(acc), tot])
    with open(D / "ammonia_cost_curves.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "activity", "manure_system", "technology", "alpha", "beta", "lower_bound", "n_classes", "heads"])
        w.writerows(out)
    return out


if __name__ == "__main__":
    rows = build()
    print(len(rows), "cost curves")

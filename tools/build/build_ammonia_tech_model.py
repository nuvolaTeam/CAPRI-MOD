"""CAPRI's ammonia technologies for the model: calibrated cost curves and NH3 effects per
model region, animal category and CAPRI sub-activity.

Inputs (capri_data/2017/abatement/ammonia): ammonia_technologies.csv and
ammonia_technology_effects.csv (build_ammonia_technologies.py, CAPRI p_ghgMiti entries),
p_litRevAmmoTechsAdd.csv (acidification effect), capri_mann_days_2030.csv (LEVL, DAYS, MANN),
FracEmHouse/Storage/Appl/Grazing.csv (MITERRA loss fractions), nuts_version_correspondence.json.

What CAPRI does and this builder reproduces (envind/ammo_tech.gms, supply/supply_model.gms):

* Groups (map_tech_gas, TotMit_): housing and storage options (LowEmHous, CovStorHigh,
  CovStorLow, AirPur, ManAcid and the combinations AirPurCovHigh - pigs and poultry -
  and AirPurCovLow - pigs) are ALTERNATIVE manure systems of one target, NH3MAN: their
  shares plus 'no control' sum to 1. Application options (AmmAppLE, AmmAppHE) form NH3APP.
  Initial shares of a group are scaled to sum <= 1 (l. 2142).
* Combinations (l. 2096-2111): costs added, maximum = the smaller one, initial share =
  product; housing effect of AirPur, storage effect of the cover.
* Effects (HOUSN_, STORN_ and the application equation): each option cuts the NH3 loss of
  its stage by its othImpact: rH (housing), rS (storage; LowEmHous also -80% at storage,
  l. 2233; acidification from the literature review, p_litRevAmmoTechsAdd), rA (application).
  The losses cascade: N lost at housing never reaches storage, and so on.
* Cost per animal place (GHG_Mit_Cost_): (kappa1 + beta) s + 1/2 (kappa2 + gamma) s^2 with
  CAPRI's calibration (l. 2860-3340, sensFac = 1, RespShareVersion = yes):
    MaxIncrease = max(1e-4, (m1 - m0) / m1);
    relative subsidy needed for m1 (relSubs1) and for early adopters (relSubs0):
      m0 > 0, kappa1 > 0: 0.8 MaxIncrease, 0      m0 > 0, kappa1 < 0: -0.2 MaxIncrease, 0
      m0 = 0, kappa1 > 0: 1.2, 0.2                m0 = 0, kappa1 < 0: -0.5, -0.1
    S = relSubs x kappa1;
    application options, options of animals without farm-size cost curves (HENS, POUF,
    SHGF, SHGM) and acidification: gamma = (S1 - S0) / (m1 - m0) - kappa2;
    other manure-management options (farm-size curves, VERSION B): m_zero = (S1 - S0) /
    kappa2 + m0 (0 if kappa2 = 0); outside [mlo, mup] = [max(0.5 m1, 1.1 m0), min(1.5 m1, 1)]
    gamma = (S1 - S0) / (bound - m0) - kappa2, else gamma = 0;
    beta from the first-order condition at m0 with subsidy S0.
  Written relative to the base: marginal cost of share s = S0 + slope (s - m0), slope =
  kappa2 + gamma, so the base share is optimal and an option with m0 = 0 needs a benefit
  above S0 before any adoption. The base savings (costsavings0) are netted out as in CAPRI.

Output: capri_data/2017/abatement/ammonia/ammonia_tech_model.csv, one row per model region,
animal, sub-activity (CAPRI region|activity) and option:
  weight        the sub-activity's share of the model animal's units (heads, LEVL)
  stock_factor  animal places per unit = DAYS / 365 (CAPRI: costs per place)
  mann_rel      the sub-activity's manure N per unit relative to the animal's (weighting)
  group         MAN or APP;  kappa1, slope, thresh (= S0), ini, max;  rH, rS, rA
  g, fG, fH, fS, fA   grazing share of excreted N, NH3 loss fractions at grazing, housing,
                      storage and application (MITERRA, liquid/solid weighted)
REGISTERED: other N gases are not subtracted in the cascade; RAINS liquid shares of 2020.
"""
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
MODEL_ANIMAL = {"DCOL": "DCOW", "DCOH": "DCOW", "BULL": "BULL", "BULH": "BULL", "HEIL": "HFRS", "HEIH": "HFRS",
                "HEIR": "HFRS", "SCOW": "BCOW", "CAMR": "CALV", "CAFR": "CALV", "CAMF": "CALV", "CAFF": "CALV",
                "PIGF": "PIGF", "SOWS": "PIGS", "HENS": "LAYS", "POUF": "BROI", "SHGF": "SHGF", "SHGM": "SHGM"}
MITT = {"DCOL": ("DAICOW_L", "DAICOW_S"), "DCOH": ("DAICOW_L", "DAICOW_S")}
for _a in ("SCOW", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAMR", "CAFR", "CAFF", "CAMF"):
    MITT[_a] = ("OCOW_L", "OCOW_S")
for _a in ("PIGF", "SOWS"):
    MITT[_a] = ("PIGS_L", "PIGS_S")
MITT.update({"HENS": (None, "LAYHENS"), "POUF": (None, "OPOUL"), "SHGF": (None, "SHEGOA"), "SHGM": (None, "SHEGOA")})
NO_OPT = {"HENS", "POUF", "SHGF", "SHGM"}                     # aniNoOpt (l. 1304)
SWINPOUL = {"PIGF", "SOWS", "HENS", "POUF"}
SWIN = {"PIGF", "SOWS"}
MAN = ["LowEmHous", "CovStorHigh", "CovStorLow", "AirPur", "ManAcid", "ManStorCon", "CovStorLowCon"]
APP = ["AmmAppLE", "AmmAppHE"]
MM_OPT_CURVES = {"LowEmHous", "CovStorHigh", "CovStorLow", "CovStorLowCon", "AirPur", "AirPurCovHigh", "AirPurCovLow",
                 "AirPurCovLowC"}  # MitiTechAmmMM (ammo_tech.gms l. 48-59)


def calibrate(tech, act, k1, k2, m0, m1):
    """CAPRI's slope (kappa2 + gamma) and early-adopter subsidy S0 (ammo_tech.gms)."""
    if m1 <= m0 or k1 == 0:
        return None, 0.0
    mi = max(1e-4, (m1 - m0) / m1)
    if m0 > 0:
        rs1, rs0 = (0.8 * mi, 0.0) if k1 > 0 else (-0.2 * mi, 0.0)
    else:
        rs1, rs0 = (1.2, 0.2) if k1 > 0 else (-0.5, -0.1)
    S1, S0 = rs1 * k1, rs0 * k1
    if tech not in MM_OPT_CURVES or act in NO_OPT:            # application, acidification, aniNoOpt
        slope = (S1 - S0) / (m1 - m0)
    else:                                                     # farm-size curves, VERSION B
        mzero = (S1 - S0) / k2 + m0 if k2 else 0.0
        mup, mlo = min(1.5 * m1, 1.0), max(0.5 * m1, 1.1 * m0)
        if mzero > mup and mup - m0 > 0:
            slope = (S1 - S0) / (mup - m0)
        elif mzero < mlo and mlo - m0 != 0:
            slope = (S1 - S0) / (mlo - m0)
        else:
            slope = k2
    return (slope if slope > 0 else None), S0


def _ad_options():
    f = D / "ad_option.csv"
    if not f.exists():
        return {}
    return {(r["region"], r["activity"]): r for r in csv.DictReader(open(f))}


def main():
    global AD
    AD = _ad_options()
    t = _read_csv(D / "ammonia_technologies.csv")
    eff = _read_csv(D / "ammonia_technology_effects.csv")
    E = {(r.region, r.activity, r.technology, r.item): r.reduction for r in eff.itertuples()}
    lit = _read_csv(D / "p_litRevAmmoTechsAdd.csv")
    LIT = {(r.region, r.activity): r.value for r in lit.itertuples()
           if r.technology == "ManAcid" and r.item == "NH3STO" and r.manure_system.upper() == "LIQUID"}
    md = _read_csv(D / "capri_mann_days_2030.csv")
    M = {(r.region, r.activity, r.item): r.value for r in md.itertuples()}
    fr = {}
    for f, k, scale in (("FracEmHouse", "H", 100.0), ("FracEmStorage", "S", 1.0), ("FracEmAppl", "A", 1.0)):
        x = _read_csv(D / f"{f}.csv")
        for r in x[x.gas.str.upper() == "NH3"].itertuples():
            fr[(r.region, r.animal_mitt, k)] = r.value / scale
    gz = _read_csv(D / "FracEmGrazing.csv")
    for r in gz[gz.item.str.upper() == "NH3"].itertuples():
        fr[(r.region, r.animal_mitt, "G")] = r.value / 100.0
    c8 = json.load(open(ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]

    def losses(ctry, act, tl):
        lq, sd = MITT[act]
        out = {}
        for k in ("G", "H", "S", "A"):
            vL = fr.get((ctry, lq, k), 0.0) if lq else 0.0
            vS = fr.get((ctry, sd, k), 0.0)
            out[k] = vL * tl + vS * (1 - tl) if lq else vS
        return out

    # ---- per CAPRI region x activity: options with calibration and effects ----
    subs = defaultdict(dict)                              # (rs, act) -> {tech: dict}
    meta = {}
    for r in t.itertuples():
        if r.activity not in MODEL_ANIMAL or pd.isna(r.CostParLin):
            continue
        ctry = r.region[:2] + "000000"
        meta[(r.region, r.activity)] = (r.liquid_share, r.grazing_share, losses(ctry, r.activity, r.liquid_share))
        # CovStorLowCon: the effects of max(CovStorLow, ManStorCon), ManStorCon having none on the gases (l. 2263)
        te = "CovStorLow" if r.technology == "CovStorLowCon" else r.technology
        rH = E.get((r.region, r.activity, te, "NH3HOU"), 0.0)
        rS = E.get((r.region, r.activity, te, "NH3STO"), 0.0)
        rA = E.get((r.region, r.activity, te, "NH3APP"), 0.0)
        if r.technology == "ManAcid":
            rS = float(LIT.get((r.region, r.activity), LIT.get((ctry, r.activity), 0.0)))
        subs[(r.region, r.activity)][r.technology] = dict(
            k1=float(r.CostParLin), k2=float(r.CostParSqr or 0.0) if not pd.isna(r.CostParSqr) else 0.0,
            ini=float(r.IniShare), max=float(r.MaxShare), rH=rH, rS=rS, rA=rA,
            group="APP" if r.technology in APP else "MAN")
    for (rs, act), d in subs.items():
        # combinations (l. 2096-2111)
        for combo, cover, anis in (("AirPurCovHigh", "CovStorHigh", SWINPOUL), ("AirPurCovLow", "CovStorLow", SWIN)):
            if act in anis and "AirPur" in d and cover in d:
                a, c = d["AirPur"], d[cover]
                d[combo] = dict(k1=a["k1"] + c["k1"], k2=a["k2"] + c["k2"], ini=a["ini"] * c["ini"],
                                max=min(a["max"], c["max"]), rH=a["rH"], rS=c["rS"], rA=0.0, group="MAN")
                msc = d.get("ManStorCon", {}).get("k1", 0.0)
                if combo == "AirPurCovHigh" and act not in SWIN:
                    # CovStorHigh's cost carries the concrete basin (endoLeach, build_ammonia_technologies.endo_leach);
                    # CAPRI adds it to AirPurCovHigh for pigs only (l. 2131-2133)
                    d[combo]["k1"] -= msc
                if combo == "AirPurCovLow":
                    # AirPurCovLowC: AirPurCovLow on a concrete basin (l. 2127-2129, 2134-2135, 2262)
                    o = dict(d[combo]); o["k1"] = o["k1"] + msc
                    d["AirPurCovLowC"] = o
        # initial shares of a group sum <= 1 (l. 2142); maximum >= initial (l. 2152)
        for grp in ("MAN", "APP"):
            tot = sum(o["ini"] for o in d.values() if o["group"] == grp)
            if tot > 1:
                for o in d.values():
                    if o["group"] == grp:
                        o["ini"] /= tot
        for tech, o in d.items():
            o["max"] = max(o["max"], o["ini"])
            o["slope"], o["S0"] = calibrate(tech, act, o["k1"], o["k2"], o["ini"], o["max"])

    # ---- to model regions (regional entries, then the national fallback) ----
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    by_reg = defaultdict(list)
    # CAPRI regions -> model regions through the shared groups (splits, merges, renamed regions)
    _c2g, _groups = mr.capri_groups(mr.model_regions())
    for (rs, act) in subs:
        if rs.endswith("000000") or rs not in _c2g:
            continue
        for n2 in sorted(_groups[_c2g[rs]][1]):
            by_reg[n2].append((rs, act))
    nat = defaultdict(list)
    for (rs, act) in subs:
        if rs.endswith("000000"):
            nat[rs].append((rs, act))
    for reg in mr.model_regions():
        if reg not in by_reg and mr.national_code(reg) in nat:
            by_reg[reg] = list(nat[mr.national_code(reg)])
    rows = []
    for reg, keys in sorted(by_reg.items()):
        lev = defaultdict(float); mann = defaultdict(float)
        for rs, act in keys:
            L = M.get((rs, act, "LEVL")) or 0.0
            lev[MODEL_ANIMAL[act]] += L
            mann[MODEL_ANIMAL[act]] += L * (M.get((rs, act, "MANN")) or 0.0)
        for rs, act in sorted(keys):
            cat = MODEL_ANIMAL[act]
            L, days, mn = (M.get((rs, act, k)) or 0.0 for k in ("LEVL", "DAYS", "MANN"))
            if L <= 0 or days <= 0 or lev[cat] <= 0:
                continue
            tl, g, fl = meta[(rs, act)]
            mrel = mn / (mann[cat] / lev[cat]) if mann[cat] > 0 else 1.0
            for tech, o in sorted(subs[(rs, act)].items()):
                if o["slope"] is None and o["ini"] <= 0:
                    continue
                rows.append([reg, cat, f"{rs}|{act}", round(L / lev[cat], 6), round(days / 365.0, 6), round(mrel, 6),
                             tech, o["group"], round(o["k1"], 6),
                             "" if o["slope"] is None else round(o["slope"], 6), round(o["S0"], 6),
                             round(o["ini"], 6), round(o["max"], 6), round(o["rH"], 6), round(o["rS"], 6), round(o["rA"], 6),
                             round(g, 6), round(fl["G"], 6), round(fl["H"], 6), round(fl["S"], 6), round(fl["A"], 6), "", ""])
            # anaerobic digestion (tools/build/build_ad_option.py): its own target CH4MAN (NOC + AD = 1, TotMit_), share as
            # CAPRI reports it (v L (1 - G)); cost per place thresh (s - s0) + 1/2 slope (s - s0)^2 at 2030 prices;
            # its N effects act through the cascade (n_cascade_effects.csv), its CH4 factor in the accounts
            o = AD.get((rs, act))
            if o is not None and float(o["max"]) > 0 and float(o["slope"]) > 0:
                rows.append([reg, cat, f"{rs}|{act}", round(L / lev[cat], 6), round(days / 365.0, 6), round(mrel, 6),
                             "AD_AnCh", "AD", round(float(o["costParLin"]), 6), round(float(o["slope"]), 6),
                             round(float(o["thresh"]), 6), round(float(o["ini"]), 6), round(float(o["max"]), 6),
                             0.0, 0.0, 0.0, round(g, 6), round(fl["G"], 6), round(fl["H"], 6), round(fl["S"], 6),
                             round(fl["A"], 6), round(float(o["lg"]), 9), round(float(o["r_ch4"]), 9)])
    with open(D / "ammonia_tech_model.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "animal", "sub", "weight", "stock_factor", "mann_rel", "technology", "group", "kappa1",
                    "slope", "thresh", "ini", "max", "rH", "rS", "rA", "g", "fG", "fH", "fS", "fA", "lg", "r_ch4"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = main()
    print(len(rows), "rows,", len({r[0] for r in rows}), "model regions")

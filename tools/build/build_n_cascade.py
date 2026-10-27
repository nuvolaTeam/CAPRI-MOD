"""CAPRI's nitrogen loss factors of the supply model's N cascade (p_Nemidat, ghgAbatement on) from the MITERRA /
literature-review inputs (docs/N_CASCADE_SPEC.md has every formula with its GAMS file and line).

CAPRI (capmod, ghgAbatement on, endoLeach on, ammoLitRev on, ScenYear 2020 for SIMY > 2010) solves the loss cascade
inside the regional supply model (supply/supply_model.gms GRAZN_, HOUSN_, STORN_, RUNHOUSN_, RUNSURFN_, APPLN_,
RUNTOTNETF_, GASTOTNETF_, LEACHN_) with these factors, the UNABATED fractions (envind/ammo_tech.gms l. 1911-1958);
the options' effects enter the equations through v_Miti x p_ghgMiti. Factors:

per CAPRI region (member-state values for every NUTS2 region of the state, R_RAGG) and animal activity (MAACT):
  tsl        liquid share, bNumAniRAINS 2020: liquid / (liquid + solid) heads (ammo.gms l. 710-737)
  tsg        N excreted at grazing: (1 - HD/365) (1 - Et/100), RCEmissions of the solid MITERRA type; poultry 0
             (ammo.gms l. 604-613)
  graz_NH3, graz_NOX, graz_N2O   loss at grazing: FracEmGrazing / 100, N2O first / 0.8 and x (1 - NH3 - NOX)
             (ammo.gms l. 619-636)
  hous_NH3, hous_NOX, hous_N2O   housing, FracEmHouse / 100, liquid / solid by tsl (ammo_tech.gms l. 1911-1913; N2O
             raw, HOUSN_ takes NH3 + NOX off itself)
  stor_NH3, stor_NOX, stor_N2    storage, FracEmStorage (fractions; no N2O data) (l. 1915-1917)
  appl_NH3, appl_NOX, appl_N2O   application, FracEmAppl (fractions) (l. 1925-1927)
  run_hous   runoff from housing and storage: factRunStor(normal, othStor) / 100 by tsl (l. 1937-1941)
per CAPRI region (NUTS2):
  run_surf   runoff from the surface, rLFrest LFsurface / 100 (ammo.gms l. 647, 657; animals and mineral N alike)
  leach      leaching share of the soil surplus, rLFrest LFsoil (no / 100; endoLeach on, ammo.gms l. 673-677)
  netf_NH3, netf_NOX, netf_N2O   mineral fertiliser: sum over fertiliser types of NN_CorrFertFactDeviation (2020; CAPRI
             overwrites FracUseFert with it, ammo.gms l. 531, 535) x EmFracFert; N2O raw (ammo.gms l. 943-958,
             ammo_tech.gms l. 1930-1933)

CAPRI's own fixes of rLFrest (ammo.gms l. 310-316): BL400000 and DEE30000 (-> DEE00000) written in the code, ES120000
the mean of ES110000 and ES130000. Regions without rLFrest (as in CAPRI: ES700000, PT200000, PT300000) get no runoff
from the surface and no leaching. Norway: CAPRI reads mirror files absent here; not built (REGISTERED).

Output: capri_data/2017/abatement/ammonia/n_cascade_factors.csv (region, activity, factor, value) and
n_cascade_region.csv (region, factor, value).
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"

# MITERRA types of CAPRI's animal activities (ammo_tech.gms map_ani_liquid / map_ani_solid, l. 1704-1750)
CATTLE = ("SCOW", "BULL", "BULH", "BULF", "HEIL", "HEIH", "HEIF", "HEIR", "CAMF", "CAFF", "CAMR", "CAFR")
MITT = {a: ("DAICOW_L", "DAICOW_S") for a in ("DCOL", "DCOH", "DCOW")}
MITT.update({a: ("OCOW_L", "OCOW_S") for a in CATTLE})
MITT.update({a: ("PIGS_L", "PIGS_S") for a in ("PIGF", "SOWS")})
MITT.update({"HENS": (None, "LAYHENS"), "POUF": (None, "OPOUL"), "SHGF": (None, "SHEGOA"), "SHGM": (None, "SHEGOA")})
POULTRY = {"HENS", "POUF"}
# grazing types (atGrazingExtra, sets_miterra.gms l. 475-485): the solid type is taken (ammo.gms l. 604-636)
GRAZ_TYPES = {"DAICOW_S", "OCOW_S", "PIGS_S", "SHEGOA", "HORSES"}
SCEN_YEAR = 2020
# rLFrest rows written in CAPRI's code (ammo.gms l. 310-316)
RLF_FIX = {"BL400000": {"LFsurface": 6.850057, "LFsoil": 0.292021, "LFNmin": 8.237927},
           "DEE00000": {"LFsurface": 2.214541, "LFsoil": 0.135434, "LFNmin": 7.714014}}   # DEE30000 -> DEE00000


def _tab(name, keys, val="value", upper=None):
    t = _read_csv(D / f"{name}.csv")
    out = {}
    for r in t.itertuples(index=False):
        k = tuple(str(getattr(r, c)).upper() if c == upper else getattr(r, c) for c in keys)
        out[k] = float(getattr(r, val))
    return out


SWINPOUL = {"PIGF", "SOWS", "HENS", "POUF"}
SWIN = {"PIGF", "SOWS"}
APPLIC_CAT = {"DCOL": "dcow", "DCOH": "dcow", "PIGF": "pigs", "SOWS": "pigs", "HENS": "hens", "POUF": "pouf",
              "SHGF": "shgt", "SHGM": "shgt"}
# storage type and cover class of the options (ammo_tech.gms map_tech_stor, map_techCov)
TECH_STOR = {"ManStorCon": ("concrStor", "normal"), "LowEmHous": ("concrStor", "LowEm"),
             "CovStorLowCon": ("concrStor", "LowEm"), "AirPurCovLowC": ("concrStor", "LowEm"),
             "CovStorHigh": ("concrStor", "HighEm"), "AirPurCovHigh": ("concrStor", "HighEm"),
             "CovStorLow": ("othStor", "LowEm"), "AirPurCovLow": ("othStor", "LowEm")}
GAS_ITEMS = [f"{g}{s}" for s in ("HOU", "STO", "APP") for g in ("NH3", "NOX", "N2O", "N2")]


def _effects(pairs, _unused, rows_a, frs):
    """The options' othImpact on the cascade (envind/ammo_tech.gms l. 2208-2345) per CAPRI region and activity:
    the gases at housing, storage and application (ammonia_technology_effects.parquet, CAPRI's p_reducEm* and
    p_reducControlStrategies weighted by liquid share and applicability), the combinations (AirPurCov* = AirPur +
    cover for pigs and poultry, l. 2252-2255; AirPurCovLowC = AirPurCovLow, CovStorLowCon = max(CovStorLow, ManStorCon),
    l. 2262-2264), acidification and anaerobic digestion from the literature review (p_litRevAmmoTechsAdd, liquid;
    l. 2305-2324), runoff from housing and storage no3runh (l. 2268-2281) and from application no3mrun (l. 2285-2291).
    Anaerobic digestion: the literature value as it stands, for a share defined as CAPRI reports it (v_Miti x liquid
    share x (1 - grazing share), sol_simy.gms l. 990-992; CAPRI's v_Miti takes the effect rescaled by that factor,
    l. 2330-2345: the same per head; docs/AD_SPEC.md)."""
    F = defaultdict(dict)
    for r in rows_a:
        F[(r[0], r[1])][r[2]] = r[3]
    E = defaultdict(dict)
    for r in pd.read_parquet(D / "ammonia_technology_effects.parquet").itertuples():
        E[(r.region, r.activity)][(r.technology, r.item)] = float(r.reduction)
    LIT = defaultdict(dict)
    for r in _read_csv(D / "p_litRevAmmoTechsAdd.csv").itertuples():
        LIT[(r.region, r.activity)][(r.technology.upper(), r.manure_system.upper(), r.item.upper())] = float(r.value)
    AP = {(r.country, r.animal_cat.lower(), r.manure_system.lower(), r.technology): float(r.value) / 100.0
          for r in _read_csv(D / "costs" / "p_applic.csv").itertuples()}
    out = []
    for reg, act in pairs:
        f = F.get((reg, act))
        if f is None:
            continue
        tl, ms = f["tsl"], reg[:2] + "000000"
        e = dict(E.get((reg, act)) or E.get((ms, act)) or {})
        for it in GAS_ITEMS:
            if act in SWINPOUL:
                e[("AirPurCovHigh", it)] = e.get(("AirPur", it), 0.0) + e.get(("CovStorHigh", it), 0.0)
            if act in SWIN:
                e[("AirPurCovLow", it)] = e.get(("AirPur", it), 0.0) + e.get(("CovStorLow", it), 0.0)
                e[("AirPurCovLowC", it)] = e[("AirPurCovLow", it)]
            e[("CovStorLowCon", it)] = max(e.get(("CovStorLow", it), 0.0), e.get(("ManStorCon", it), 0.0))
        lit = LIT.get((reg, act)) or LIT.get((ms, act)) or {}
        for it in ("NH3STO", "NOXSTO", "N2OHOU"):
            if ("MANACID", "LIQUID", it) in lit:
                e[("ManAcid", it)] = lit[("MANACID", "LIQUID", it)]
        for it in ("N2OHOU", "NH3STO", "NOXSTO", "N2OAPP"):
            if ("AD_ANCH", "LIQUID", it) in lit:
                e[("AD_AnCh", it)] = lit[("AD_ANCH", "LIQUID", it)]
        L0, S0 = frs[("LIQUID", "normal", "othStor")], frs[("SOLID", "normal", "othStor")]
        for t, (st, cv) in TECH_STOR.items():
            if t.startswith("AirPurCov"):
                continue
            e[(t, "no3runh")] = ((L0 - frs.get(("LIQUID", cv, st), 0.0)) / L0 * tl
                                 + (S0 - frs.get(("SOLID", cv, st), 0.0)) / S0 * (1.0 - tl))
        if act in SWINPOUL:
            e[("AirPurCovHigh", "no3runh")] = e[("CovStorHigh", "no3runh")]
        if act in SWIN:
            e[("AirPurCovLow", "no3runh")] = e[("CovStorLow", "no3runh")]
            e[("AirPurCovLowC", "no3runh")] = max(e[("AirPurCovLow", "no3runh")], e[("ManStorCon", "no3runh")])
        cat = APPLIC_CAT.get(act, "ocat")
        for t in ("AmmAppLE", "AmmAppHE"):
            aL, aS = AP.get((ms, cat, "liquid", t), 0.0), AP.get((ms, cat, "solid", t), 0.0)
            den = tl * aL + (1.0 - tl) * aS
            if den > 0:
                for it in ("NO3MRUN", "NO3MLEA"):
                    v = (lit.get((t.upper(), "LIQUID", it), 0.0) * tl * aL
                         + lit.get((t.upper(), "SOLID", it), 0.0) * (1.0 - tl) * aS) / den
                    if v:
                        e[(t, it.lower())] = v
        for (t, it), v in sorted(e.items()):
            if v and (it in GAS_ITEMS or it in ("no3runh", "no3mrun", "no3mlea")):
                out.append([reg, act, t, it, round(float(v), 12)])
    return out


def build():
    rc = _tab("RCEmissions", ("region", "animal_mitt", "item"))
    fg = _tab("FracEmGrazing", ("region", "animal_mitt", "item"), upper="item")
    fh = _tab("FracEmHouse", ("region", "animal_mitt", "gas"), upper="gas")
    fs = _tab("FracEmStorage", ("region", "animal_mitt", "gas"), upper="gas")
    fa = _tab("FracEmAppl", ("region", "animal_mitt", "gas"), upper="gas")
    ef = _tab("EmFracFert", ("region", "gas", "fertiliser"), upper="gas")
    nn = _tab("NN_CorrFertFactDeviation", ("region", "fertiliser", "year"))
    bn = _tab("bNumAniRAINS", ("region", "animal_mitt", "year"))
    rs_ = _read_csv(D / "p_factRunStor.csv")
    frs = {(r.manure_system.upper(), r.tech_class, r.storage_type): float(r.value) for r in rs_.itertuples()}
    rlf = defaultdict(dict)
    for r in _read_csv(D / "rLFRest.csv").itertuples():
        rlf[r.region][r.item] = float(r.value)
    for k, v in RLF_FIX.items():
        rlf[k].update(v)
    for it in ("LFsurface", "LFsoil", "LFNmin"):
        if it not in rlf.get("ES120000", {}) and it in rlf.get("ES110000", {}) and it in rlf.get("ES130000", {}):
            rlf["ES120000"][it] = 0.5 * (rlf["ES110000"][it] + rlf["ES130000"][it])
    md = _read_csv(D / "capri_mann_days_2030.csv")
    pairs = sorted({(r.region, r.activity) for r in md.itertuples() if r.item == "LEVL" and r.activity in MITT})

    rows_a, rows_r = [], []
    ms_seen = set()
    regions = sorted({r for r, _ in pairs})
    for reg, act in pairs:
        ms = reg[:2] + "000000"
        lq, sd = MITT[act]
        L = bn.get((ms, lq, SCEN_YEAR), 0.0) if lq else 0.0
        S = bn.get((ms, sd, SCEN_YEAR), 0.0) if lq else 0.0
        tsl = L / (L + S) if lq and (L + S) != 0 else 0.0
        if act in POULTRY or sd not in GRAZ_TYPES:
            tsg = 0.0
        else:
            tsg = (1.0 - rc.get((ms, sd, "HD"), 0.0) / 365.0) * (1.0 - rc.get((ms, sd, "Et"), 0.0) / 100.0)
        f = {"tsl": tsl, "tsg": tsg}
        gN = {g: (fg.get((ms, sd, g), 0.0) / 100.0 if sd in GRAZ_TYPES else 0.0) for g in ("NH3", "NOX")}
        gN2O = (fg.get((ms, sd, "N2O"), 0.0) / 0.8 / 100.0 if sd in GRAZ_TYPES else 0.0) * (1.0 - gN["NH3"] - gN["NOX"])
        f.update({"graz_NH3": gN["NH3"], "graz_NOX": gN["NOX"], "graz_N2O": gN2O})

        def mix(tab, g, scale):
            vS = tab.get((ms, sd, g), 0.0) / scale
            if not lq:
                return vS
            return tab.get((ms, lq, g), 0.0) / scale * tsl + vS * (1.0 - tsl)
        for g in ("NH3", "NOX", "N2O"):
            f[f"hous_{g}"] = mix(fh, g, 100.0)
            f[f"appl_{g}"] = mix(fa, g, 1.0)
        for g in ("NH3", "NOX", "N2"):
            f[f"stor_{g}"] = mix(fs, g, 1.0)
        f["run_hous"] = (frs[("LIQUID", "normal", "othStor")] / 100.0 * tsl
                         + frs[("SOLID", "normal", "othStor")] / 100.0 * (1.0 - tsl))
        for k, v in f.items():
            rows_a.append([reg, act, k, round(v, 12)])
        ms_seen.add(ms)
    for reg in regions:
        ms = reg[:2] + "000000"
        r_ = rlf.get(reg, {})
        out = {}
        if "LFsurface" in r_:
            out["run_surf"] = r_["LFsurface"] / 100.0
        if "LFsoil" in r_:
            out["leach"] = max(0.0, r_["LFsoil"])
        # (zeros are absent from CAPRI's GDX dumps: a type missing where the other is present has share 0)
        share = {ft: nn.get((ms, ft, SCEN_YEAR)) for ft in ("Ureum", "Other")}
        if any(v is not None for v in share.values()):
            share = {ft: (v or 0.0) for ft, v in share.items()}
            for g in ("NH3", "NOX", "N2O"):
                out[f"netf_{g}"] = sum(share[ft] * ef.get((ms, g, ft), 0.0) for ft in share)
        for k, v in out.items():
            rows_r.append([reg, k, round(v, 12)])
    rows_e = _effects(pairs, {(r[0], r[1]): None for r in rows_a}, rows_a, frs)
    for reg in regions:
        ms = reg[:2] + "000000"
        share = {ft: nn.get((ms, ft, SCEN_YEAR)) for ft in ("Ureum", "Other")}
        if any(v is not None for v in share.values()) and (ms, "NH3", "Ureum") in ef:
            # urea substitution (ammo_tech.gms l. 2352-2361): othImpact nh3syn = EF(urea) - EF(other), maximum share
            # the urea share
            rows_r.append([reg, "urea_eff", round(ef[(ms, "NH3", "Ureum")] - ef.get((ms, "NH3", "Other"), 0.0), 12)])
            rows_r.append([reg, "urea_max", round(share["Ureum"] or 0.0, 12)])
    with open(D / "n_cascade_effects.csv", "w", newline="") as fh_:
        w = csv.writer(fh_)
        w.writerow(["region", "activity", "technology", "item", "value"])
        w.writerows(rows_e)
    with open(D / "n_cascade_factors.csv", "w", newline="") as fh_:
        w = csv.writer(fh_)
        w.writerow(["region", "activity", "factor", "value"])
        w.writerows(rows_a)
    with open(D / "n_cascade_region.csv", "w", newline="") as fh_:
        w = csv.writer(fh_)
        w.writerow(["region", "factor", "value"])
        w.writerows(rows_r)
    return rows_a, rows_r


if __name__ == "__main__":
    a, r = build()
    print(len(a), "activity factors,", len(r), "regional factors,", len({x[0] for x in r}), "regions")
    miss = sorted({x[0] for x in a} - {x[0] for x in r if x[1] == "run_surf"})
    print("regions without run_surf:", miss)
    miss = sorted({x[0] for x in a} - {x[0] for x in r if x[1] == "netf_NH3"})
    print("regions without netf factors:", miss)

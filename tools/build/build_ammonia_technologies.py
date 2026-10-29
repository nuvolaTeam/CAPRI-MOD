"""Assemble CAPRI's ammonia-option entries of p_ghgMiti (envind/ammo_tech.gms l. ~1960-2070).

Per CAPRI region and animal activity, for LowEmHous, CovStorLow, CovStorHigh, AirPur (manure
management, target NH3MAN), AmmAppLE, AmmAppHE (application, NH3APP) and ManAcid:

  CostParLin, CostParSqr - farm-size curves (build_ammonia_cost_curves.py) weighted over manure
      systems by liquid share x applicability (p_helpDenom); CostParSqr = 2 beta (CAPRI's
      kappa2). Animals without size curves (HENS, POUF, SHGF, SHGM): cost at the largest class.
      Application: operating cost per m3 spread (grassland/arable rates) at h500, net of grazing.
      Acidification: 10.82 EUR per m3 of stored manure (Reis et al. 2015), net of grazing.
  IniShare   - MITERRA control strategies for 2020 (p_controlStrategies), weighted by liquid
      and solid shares, / 100; acidification 0.
  Applic     - applicability share (p_applic / 100), the upper limit of adoption.

Liquid share: RAINS projections (bNumAniRAINS), CAPRI's default path (STORGRAZINV off); the
projections end in 2020, so 2020 is used (REGISTERED). Grazing share: (1 - HD/365)(1 - Et/100)
(RCEmissions, solid types). Concrete storage (ManStorCon) needs CAPRI's endoLeach switch, which
is off in the simulation settings, so it is not built.

Output: capri_data/2017/abatement/ammonia/ammonia_technologies.csv
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
C = D / "costs"
_spec = importlib.util.spec_from_file_location("cc", ROOT / "tools" / "build" / "build_ammonia_cost_curves.py")
cc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cc)

MM = ["LowEmHous", "CovStorLow", "CovStorHigh", "AirPur"]
APP = ["AmmAppLE", "AmmAppHE"]
TECH_MITT = {"LowEmHous": "SA", "CovStorLow": "CS_low", "CovStorHigh": "CS_high",
             "AmmAppLE": "LNA_low", "AmmAppHE": "LNA_high"}
TARGET = {**{t: "NH3MAN" for t in MM}, **{t: "NH3APP" for t in APP}, "ManAcid": "NH3MAN"}
# MITERRA categories (map_ani_liquid / map_ani_solid in ammo_tech.gms)
MITT = {"DCOL": ("DAICOW_L", "DAICOW_S"), "DCOH": ("DAICOW_L", "DAICOW_S")}
for a in ("SCOW", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAMR", "CAFR", "CAFF", "CAMF"):
    MITT[a] = ("OCOW_L", "OCOW_S")
for a in ("PIGF", "SOWS"):
    MITT[a] = ("PIGS_L", "PIGS_S")
MITT.update({"HENS": (None, "LAYHENS"), "POUF": (None, "OPOUL"), "SHGF": (None, "SHEGOA"), "SHGM": (None, "SHEGOA")})
RAINS_YEAR = "2020"
# map_techCat (l. 1663), map_tech_tag (l. ~1640), map_gas_tag (l. 1759)
TECH_CLASS = {"LowEmHous": "LOWEM", "AirPur": "HIGHEM", "CovStorLow": "LOWEM", "CovStorHigh": "HIGHEM",
              "AmmAppLE": "LOWEM", "AmmAppHE": "HIGHEM"}
HOUSING = {"LowEmHous", "AirPur"}
STORAGE = {"CovStorLow", "CovStorHigh"}
TAGS = {"LowEmHous": ("NH3HOU", "NOXHOU", "N2HOU", "N2OHOU", "CH4MAN"),
        "AirPur": ("NH3HOU",),
        "CovStorHigh": ("NH3STO", "NOXSTO", "N2OSTO", "N2STO", "CH4MAN"),
        "CovStorLow": ("NH3STO", "NOXSTO", "N2OSTO", "N2STO", "CH4MAN"),
        "AmmAppHE": ("NH3APP", "NOXAPP", "N2OAPP", "N2APP"),
        "AmmAppLE": ("NH3APP", "NOXAPP", "N2OAPP", "N2APP")}
GAS_OF = {"NH3HOU": "NH3", "NH3STO": "NH3", "NH3APP": "NH3", "NOXHOU": "NOX", "NOXSTO": "NOX", "NOXAPP": "NOX",
          "N2OHOU": "N2O", "N2OSTO": "N2O", "N2OAPP": "N2O", "N2HOU": "N2", "N2STO": "N2", "N2APP": "N2", "CH4MAN": "CH4"}


def build():
    INV, ADD, FOP, PRICE, STOR, MIN, KGN, nvz, HEADS, HOLD, MD = cc.load()
    curves = pd.read_parquet(D / "ammonia_cost_curves.parquet")
    CUR = {(r.region, r.activity, r.manure_system.lower(), r.technology): (r.alpha, r.beta) for r in curves.itertuples()}
    rains = _read_csv(D / "bNumAniRAINS.csv", dtype={"year": str})
    RN = {(r.region, r.animal_mitt): r.value for r in rains[rains.year == RAINS_YEAR].itertuples()}
    rce = _read_csv(D / "RCEmissions.csv")
    RCE = {(r.region, r.animal_mitt, r.item): r.value for r in rce.itertuples()}
    cs = _read_csv(D / "ControlStrategies.csv", dtype={"item": str})
    CS = {(r.region, r.animal_mitt, r.strategy): r.value for r in cs[cs["item"] == "2020"].itertuples()}
    ap = _read_csv(C / "p_applic.csv")
    AP = {(r.country, r.animal_cat.lower(), r.manure_system.lower(), r.technology): r.value / 100 for r in ap.itertuples()}
    ca = _read_csv(C / "p_costParAppl.csv")
    CA = {(r.technology, r.animal_cat.lower(), r.manure_system.lower(), r.coefficient): r.value for r in ca.itertuples()}
    U = lambda x: str(x).upper()
    rh = _read_csv(D / "reducEmHouse.csv")
    RH = {(r.region, U(r.animal_mitt), U(r.gas), U(r.tech_class)): r.value for r in rh.itertuples()}
    rsx = _read_csv(D / "reducEmStorage.csv")
    RS = {(r.region, U(r.animal_mitt), U(r.gas), U(r.tech_class)): r.value for r in rsx.itertuples()}
    rc = _read_csv(D / "reducControlStrategies.csv")
    RC = {(r.region, U(r.animal_mitt), U(r.strategy), U(r.item)): r.value for r in rc.itertuples()}
    gl = _read_csv(C / "p_sharGL.csv")
    GL = {(r.country, r.manure_system.lower(), r.animal_cat.lower()): r.value for r in gl.itertuples()}

    def liquid_share(ctry, act):
        lq, sd = MITT[act]
        if lq is None:
            return 0.0
        L, S = RN.get((ctry, lq), 0.0), RN.get((ctry, sd), 0.0)
        return L / (L + S) if (L + S) > 0 else 0.0

    def grazing(ctry, act):
        sd = MITT[act][1]
        hd, et = RCE.get((ctry, sd, "HD")), RCE.get((ctry, sd, "Et"))
        if hd is None:
            return 0.0
        return max(0.0, (1 - hd / 365.0) * (1 - (et or 0.0) / 100.0))

    def h500_cost(rs, act, sysm, tech):
        """investment (annualised) + operating cost at the largest class, no size term."""
        cat = cc.ANIM_CAT[act].lower()
        if (tech, cat, sysm, "cif") not in INV:
            return None
        cif, lt = INV[(tech, cat, sysm, "cif")], INV.get((tech, cat, sysm, "lt"), 0.0)
        if tech in cc.STORE:
            mann, days, kg = MD.get((rs, act, "MANN")), MD.get((rs, act, "DAYS")), KGN.get((act, sysm))
            if not (mann and days and kg):
                return None
            cif = cif * cc.stor_months(rs, sysm, cat, STOR, MIN, nvz) / 12 * mann / kg * 365 / days
        op = cif * FOP.get((tech, cat, sysm), 0.0) + sum(q * PRICE.get(cc.nat(rs), {}).get(k, 0.0)
                                                         for k, q in ADD.get((tech, cat, sysm), {}).items())
        f = (1 + cc.R) ** lt * cc.R / ((1 + cc.R) ** lt - 1) if lt else 1.0
        return cif * f + op

    regions = sorted({k[0] for k in MD})
    out, effects = [], []
    for rs in regions:
        ctry = cc.nat(rs)
        for act in cc.ANIM_CAT:
            if (rs, act, "MANN") not in MD:
                continue
            cat = cc.ANIM_CAT[act].lower()
            tl = liquid_share(ctry, act); ts = 1 - tl; gz = grazing(ctry, act)
            mann, days = MD.get((rs, act, "MANN")), MD.get((rs, act, "DAYS"))
            for tech in MM + APP + ["ManAcid"]:
                apL, apS = AP.get((ctry, cat, "liquid", tech), 0.0), AP.get((ctry, cat, "solid", tech), 0.0)
                den = tl * apL + ts * apS
                lin = sqr = None
                if tech in MM and den > 0:
                    if act in cc.NO_OPT:
                        cL, cS = h500_cost(rs, act, "liquid", tech), h500_cost(rs, act, "solid", tech)
                        lin = ((cL or 0) * tl * apL + (cS or 0) * ts * apS) / den
                        sqr = 0.0
                    else:
                        aL, bL = CUR.get((rs, act, "liquid", tech), (0.0, 0.0))
                        aS, bS = CUR.get((rs, act, "solid", tech), (0.0, 0.0))
                        lin = (aL * tl * apL + aS * ts * apS) / den
                        sqr = 2 * (bL * tl * apL + bS * ts * apS) / den
                elif tech in APP and den > 0 and days:
                    def app_op(sysm):
                        kg = KGN.get((act, sysm))
                        if not kg:
                            return 0.0
                        g = GL.get((ctry, sysm, cat), 0.0)
                        rate = CA.get((tech, cat, sysm, "CFMG"), 0.0) * g + CA.get((tech, cat, sysm, "CFMA"), 0.0) * (1 - g)
                        return rate * mann / kg * 365 / days * (1 - gz)
                    lin = (app_op("liquid") * tl * apL + app_op("solid") * ts * apS) / den
                    sqr = 0.0
                elif tech == "ManAcid" and days and KGN.get((act, "liquid")):
                    lin = mann / KGN[(act, "liquid")] * 365 / days * 10.82 * (1 - gz)
                    sqr = 0.0
                if tech == "ManAcid":
                    ini = 0.0
                elif tech in TECH_MITT:
                    lq, sd = MITT[act]
                    m = TECH_MITT[tech]
                    ini = ((CS.get((ctry, lq, m), 0.0) if lq else 0.0) * tl + CS.get((ctry, sd, m), 0.0) * ts) / 100
                else:
                    ini = 0.0                                   # AirPur: zero at the start (CAPRI)
                if lin is None and ini == 0.0:
                    continue
                # MAXIMUM SHARE (l. 2078-2088): applicability over manure systems;
                # acidification: liquid share; never below the initial share (l. 2150)
                mx = tl if tech == "ManAcid" else tl * apL + ts * apS
                mx = max(mx, ini)
                # MAIN EFFECT qemitt (l. 2157-2190): remaining NH3 relative to no
                # technology (= 1), MITERRA reductions by technology class
                lq, sd = MITT[act]; cls = TECH_CLASS.get(tech)
                qe, side = None, {}
                if tech == "ManAcid":
                    qe = 0.28                                         # -72% (l. 2189)
                elif den > 0 and cls:
                    if tech in HOUSING or tech in STORAGE:
                        tab = RH if tech in HOUSING else RS
                        def stage(gas, remaining):
                            vL = tab.get((ctry, lq, gas, cls), 0.0) if lq else 0.0
                            vS = tab.get((ctry, sd, gas, cls), 0.0)
                            if remaining:
                                return ((100 - vL) / 100 * tl * apL + (100 - vS) / 100 * ts * apS) / den
                            return (vL / 100 * tl * apL + vS / 100 * ts * apS) / den
                        qe = stage("NH3", True)
                        for item in TAGS.get(tech, ()):
                            side[item] = stage(GAS_OF[item], False)
                    elif tech in APP:
                        def app(gas, remaining):
                            vL = RC.get((ctry, "LIQUID", gas, cls), 0.0); vS = RC.get((ctry, "SOLID", gas, cls), 0.0)
                            if remaining:
                                return ((1 - vL) * tl * apL + (1 - vS) * ts * apS) / den
                            return (vL * tl * apL + vS * ts * apS) / den
                        qe = app("NH3", True)
                        for item in TAGS.get(tech, ()):
                            side[item] = app(GAS_OF[item], False)
                if tech == "LowEmHous":
                    side["NH3STO"] = 0.8                              # l. 2233
                if "N2OSTO" in side:                                  # l. 2236-2237: N2O at housing level
                    side["N2OHOU"] = side.pop("N2OSTO")
                for item, val in side.items():
                    effects.append([rs, act, tech, item, val])
                out.append([rs, act, tech, TARGET[tech], lin if lin is not None else "", sqr if sqr is not None else "",
                            ini, mx, "" if qe is None else qe,
                            den, tl, gz])
    out = endo_leach(out, MD, KGN, STOR, MIN, nvz, AP)
    with open(D / "ammonia_technologies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "activity", "technology", "target", "CostParLin", "CostParSqr", "IniShare",
                    "MaxShare", "qemitt", "applicability", "liquid_share", "grazing_share"])
        w.writerows(out)
    # a builder intermediate (read by build_n_cascade, build_ammonia_tech_model, build_manure_n2o): Parquet
    pd.DataFrame(effects, columns=["region", "activity", "technology", "item", "reduction"]).to_parquet(
        D / "ammonia_technology_effects.parquet", index=False)
    return out


# Nitrates Directive: regions (member state, NUTS1 or NUTS2) requiring covered storage (envind/ammo_tech.gms l. 2400-2434)
STOR_COVER = {("BL200000", "inNVZ", "liquid"), ("BL200000", "inNVZ", "solid"), ("BL300000", "inNVZ", "liquid"),
              ("CY000000", "inNVZ", "solid"), ("DK000000", "inNVZ", "solid"), ("DK000000", "inNVZ", "liquid"),
              ("EE000000", "inNVZ", "liquid"), ("EE000000", "inNVZ", "solid"), ("FI100000", "inNVZ", "liquid"),
              ("FI100000", "inNVZ", "solid"), ("DE000000", "inNVZ", "solid"), ("IT110000", "inNVZ", "liquid"),
              ("IT110000", "inNVZ", "solid"), ("LT000000", "inNVZ", "liquid"), ("LT000000", "inNVZ", "solid"),
              ("MT000000", "inNVZ", "liquid"), ("MT000000", "inNVZ", "solid"), ("NL000000", "inNVZ", "liquid"),
              ("NL000000", "inNVZ", "solid"), ("PL000000", "inNVZ", "liquid"), ("PL000000", "inNVZ", "solid"),
              ("RO000000", "inNVZ", "liquid"), ("SK000000", "inNVZ", "liquid"), ("SK000000", "inNVZ", "solid"),
              ("ES530000", "inNVZ", "liquid"), ("ES530000", "inNVZ", "solid")}
SWIN = {"PIGF", "SOWS"}
#: CAPRI's code raises the initial covered-storage shares to the Nitrates Directive's minimum (p_helpManStor); its Green
#: Deal reference run with endogenous technologies does not show it (PL22 DCOL: ManStorCon 0.5525, CovStorHigh 0.1225, no
#: CovStorLowCon, where the code would move 0.1575 to CovStorLowCon; NL22 PIGF likewise) while every other initial share
#: of the four regions checked is reproduced. Off, as CAPRI's results have it (REGISTERED, KNOWN_ISSUES)
APPLY_ENV_COVER = False


def endo_leach(out, MD, KGN, STOR, MIN, nvz, AP):
    """CAPRI's options with endoLeach on (capmod's default, capmod/set_global_variables.gms l. 55; envind/ammo_tech.gms):
    the concrete storage basin ManStorCon and its combination with a low-efficiency cover CovStorLowCon.
      ManStorCon  CostParLin = sum over manure systems of storage months / 12 x manure m3 per place (MANN / kg N per
                  m3 x 365 / DAYS) x system share x 1.5 EUR (liquid) or 1 EUR (solid) per m3 and year (l. 2018-2025);
                  IniShare = p_fracStorType of concrete storage by system share (l. 2049-2052); MaxShare 1 (l. 2085);
                  qemitt 1 (no NH3 effect, l. 2206)
      CovStorLowCon  CostParLin = CovStorLow's + ManStorCon's, CostParSqr and MaxShare CovStorLow's (l. 2086, 2115-2118)
      LowEmHous, CovStorHigh  CostParLin + ManStorCon's (they always come with a concrete basin, l. 2120-2126)
      initial shares (l. 2054-2067): CovStorLowCon = CovStorLow x ManStorCon; CovStorLow less that; ManStorCon =
                  max(0, ManStorCon (1 - CovStorLowCon - CovStorLow) - CovStorHigh - LowEmHous)
      the Nitrates Directive's covered storage (p_envConst CovStorLow, l. 2596-2621) and the adjustment of the initial
                  shares to it (p_helpManStor, l. 2676-2709)
    (The pigs' combinations AirPurCovLowC / AirPurCovHigh with the basin's cost: tools/build/build_ammonia_tech_model.py.)
    Rows: [region, activity, technology, target, lin, sqr, ini, max, qemitt, applicability, liquid share, grazing]."""
    fst = _read_csv(D / "p_fracStorType.csv")
    FST = {(r.region, r.manure_system.upper(), r.storage_type): float(r.value) for r in fst.itertuples()}
    by = {}
    for r in out:
        by.setdefault((r[0], r[1]), {})[r[2]] = r
    res = []
    for (rs, act), d in by.items():
        any_ = next(iter(d.values()))
        tl, gz = float(any_[10]), float(any_[11])
        ctry = cc.nat(rs)
        cat = cc.ANIM_CAT[act].lower()
        mann, days = MD.get((rs, act, "MANN")), MD.get((rs, act, "DAYS"))
        lin = 0.0
        if mann and days:
            for sysm, sh, eur in (("liquid", tl, 1.5), ("solid", 1.0 - tl, 1.0)):
                kg = KGN.get((act, sysm))
                if kg:
                    lin += cc.stor_months(rs, sysm, cat, STOR, MIN, nvz) / 12 * mann / kg * 365 / days * sh * eur
        ini0 = FST.get((ctry, "LIQUID", "concrStor"), 0.0) * tl + FST.get((ctry, "SOLID", "concrStor"), 0.0) * (1 - tl)
        g = lambda t, k: float(d[t][k]) if t in d and d[t][k] not in ("", None) else 0.0
        csl_ini, csh_ini, leh_ini = g("CovStorLow", 6), g("CovStorHigh", 6), g("LowEmHous", 6)
        cslc_ini = csl_ini * ini0
        csl_ini -= cslc_ini
        msc_ini = max(0.0, ini0 * (1 - cslc_ini - csl_ini) - csh_ini - leh_ini)
        if "CovStorLow" in d:
            r = list(d["CovStorLow"])
            r[6] = csl_ini
            d["CovStorLow"] = r
            c = list(d["CovStorLow"])
            c[2] = "CovStorLowCon"
            c[4] = (float(r[4]) if r[4] != "" else 0.0) + lin
            c[6] = cslc_ini
            d["CovStorLowCon"] = c
        for t in ("LowEmHous", "CovStorHigh"):
            if t in d and d[t][4] != "":
                r = list(d[t]); r[4] = float(r[4]) + lin; d[t] = r
        if lin > 0 or msc_ini > 0:
            d["ManStorCon"] = [rs, act, "ManStorCon", "NH3MAN", lin, 0.0, msc_ini, 1.0, 1.0, 1.0,
                               tl, gz]
        # the Nitrates Directive's covered storage: minimum share and the initial shares (l. 2596-2621, 2676-2709)
        env = _env_cov(rs, act, tl, ctry, cat, nvz, AP) if APPLY_ENV_COVER else 0.0
        tot = sum(g(t, 6) for t in ("CovStorLow", "CovStorLowCon", "CovStorHigh", "LowEmHous"))
        if env > tot and "ManStorCon" in d and "CovStorLowCon" in d:
            h = min(float(d["ManStorCon"][6]), env - tot)
            if h > 0:
                c = list(d["CovStorLowCon"]); c[6] = float(c[6]) + h; c[7] = max(float(c[7]), float(c[6]))
                d["CovStorLowCon"] = c
                m = list(d["ManStorCon"]); m[6] = float(m[6]) - h; d["ManStorCon"] = m
        tot = sum(g(t, 6) for t in ("CovStorLow", "CovStorLowCon", "CovStorHigh", "LowEmHous"))
        if env > tot and "CovStorLow" in d:
            r = list(d["CovStorLow"])
            r[6] = env - g("CovStorLowCon", 6) - g("CovStorHigh", 6) - g("LowEmHous", 6)
            r[7] = max(float(r[7]), float(r[6]))
            d["CovStorLow"] = r
        res.extend(d.values())
    return res


def _env_cov(rs, act, tl, ctry, cat, nvz, AP):
    """p_envConst(ru, maact, CovStorLow): covered storage the Nitrates Directive requires, by NVZ share (l. 2596-2621):
    the region's own entry, else its NUTS1, else its member state."""
    nv = float(nvz.get(rs, 0.0))
    aL, aS = AP.get((ctry, cat, "liquid", "CovStorLow"), 0.0), AP.get((ctry, cat, "solid", "CovStorLow"), 0.0)
    for key in (rs, rs[:3] + "00000", ctry):
        if any((key, z, m) in STOR_COVER for z in ("inNVZ", "outNVZ") for m in ("liquid", "solid")):
            v = 0.0
            for z, w in (("inNVZ", nv), ("outNVZ", 1.0 - nv)):
                v += w * ((tl * aL if (key, z, "liquid") in STOR_COVER else 0.0)
                          + ((1 - tl) * aS if (key, z, "solid") in STOR_COVER else 0.0))
            if v:
                if ctry == "MT000000" and act in ("SHGM", "SHGF"):
                    v = tl * aL
                return v
    return 0.0


if __name__ == "__main__":
    print(len(build()), "technology entries")

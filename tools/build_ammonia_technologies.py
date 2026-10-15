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

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
C = D / "costs"
_spec = importlib.util.spec_from_file_location("cc", ROOT / "tools" / "build_ammonia_cost_curves.py")
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
    curves = pd.read_csv(D / "ammonia_cost_curves.csv")
    CUR = {(r.region, r.activity, r.manure_system.lower(), r.technology): (r.alpha, r.beta) for r in curves.itertuples()}
    rains = pd.read_csv(D / "bNumAniRAINS.csv", dtype={"year": str})
    RN = {(r.region, r.animal_mitt): r.value for r in rains[rains.year == RAINS_YEAR].itertuples()}
    rce = pd.read_csv(D / "RCEmissions.csv")
    RCE = {(r.region, r.animal_mitt, r.item): r.value for r in rce.itertuples()}
    cs = pd.read_csv(D / "ControlStrategies.csv", dtype={"item": str})
    CS = {(r.region, r.animal_mitt, r.strategy): r.value for r in cs[cs["item"] == "2020"].itertuples()}
    ap = pd.read_csv(C / "p_applic.csv")
    AP = {(r.country, r.animal_cat.lower(), r.manure_system.lower(), r.technology): r.value / 100 for r in ap.itertuples()}
    ca = pd.read_csv(C / "p_costParAppl.csv")
    CA = {(r.technology, r.animal_cat.lower(), r.manure_system.lower(), r.coefficient): r.value for r in ca.itertuples()}
    U = lambda x: str(x).upper()
    rh = pd.read_csv(D / "reducEmHouse.csv")
    RH = {(r.region, U(r.animal_mitt), U(r.gas), U(r.tech_class)): r.value for r in rh.itertuples()}
    rsx = pd.read_csv(D / "reducEmStorage.csv")
    RS = {(r.region, U(r.animal_mitt), U(r.gas), U(r.tech_class)): r.value for r in rsx.itertuples()}
    rc = pd.read_csv(D / "reducControlStrategies.csv")
    RC = {(r.region, U(r.animal_mitt), U(r.strategy), U(r.item)): r.value for r in rc.itertuples()}
    gl = pd.read_csv(C / "p_sharGL.csv")
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
                    effects.append([rs, act, tech, item, round(val, 6)])
                out.append([rs, act, tech, TARGET[tech], lin if lin is not None else "", sqr if sqr is not None else "",
                            round(ini, 6), round(mx, 6), "" if qe is None else round(qe, 6),
                            round(den, 6), round(tl, 6), round(gz, 6)])
    with open(D / "ammonia_technologies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "activity", "technology", "target", "CostParLin", "CostParSqr", "IniShare",
                    "MaxShare", "qemitt", "applicability", "liquid_share", "grazing_share"])
        w.writerows(out)
    with open(D / "ammonia_technology_effects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "activity", "technology", "item", "reduction"])
        w.writerows(effects)
    return out


if __name__ == "__main__":
    print(len(build()), "technology entries")

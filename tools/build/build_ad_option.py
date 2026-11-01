"""CAPRI's anaerobic digestion option AD_AnCh (envind/ad_data_and_cali.gms, %ad_type% = anch; docs/AD_SPEC.md) per
CAPRI region and animal activity, for the supply models.

CAPRI's variable v_Miti(AD_AnCh, CH4MAN) is the share of the housed liquid manure that is digested; every per-head
parameter is multiplied by L (1 - G) (liquid share x (1 - grazing share), l. 747-765), and CAPRI reports the share as
v L (1 - G) (sol_simy.gms l. 990-992). capri-mod works with the REPORTED share s = v L (1 - G): the options' N effects
(n_cascade_effects.csv, AD_AnCh) act as literature value x s, and

  cost per animal place  = Subs0 / LG x (s - s0) + 1/2 (costParSqr + pmpParSqr) / LG^2 x (s - s0)^2   (+ constant)
  (CAPRI's calibrated GHG_Mit_Cost_ term (costParLin + pmpParLin - revenue) v + 1/2 (costParSqr + pmpParSqr) v^2, whose
  first-order condition at the initial share leaves the marginal cost Subs0 + (costParSqr + pmpParSqr)(v - v0))
  manure CH4 factor      = 1 - (s / LG) (1 - QE_AD / QE_NOC)   (supply_model.gms GWPCH4MAN_, MC_GHG_Miti_Factor)

Items (ad_data_and_cali.gms lines):
  heads by farm-size class: the region's own, else per class NUTS1 if it has the class, else NUTS0 (l. 405-409); farm
    size per class cleaned and filled the same way (l. 417-422)
  energy ECH4 = VSER 365 B0 sum_c sh_c (1 - 0.02 - MCF_nc,c 0.25) 0.85 (1 - 0.03) 0.6557 55 277.8 / 1000 (l. 459-463)
  cost per head CAD = kW (alpha ln(kW sf) + beta) (CRF(r, 15) + 0.05), kW = ECH4 0.36 / 7000; r = 0.035 (ammo_tech.gms
    l. 1203 re-declares p_r /0.035/, which GAMS applies before this file's 0.05: CAPRI's results reproduce with 0.035)
  cumulative shares and costs by class, the line through the two largest classes (or 200_500 and 100_200), RU falling
    back to MS without heads there (l. 479-562): INDEP = costParLin, 2 SLOPE = costParSqr; MaxShare = heads in farms
    of 200 LSU and more / all (l. 490)
  IniShare = MitiShar0 SharLiq HousShar / (L (1 - G)) (l. 440-454, 603-613), 0 where MitiShar0 is 0
  revenue = ECH4 (0.4 0.3 P_heat + 0.36 (1 - 0.12) P_elec), GAINS prices of the country's L farms (l. 642-661)
  QE_AD / QE_NOC from the climate cells' MCF (l. 676-737; member-state level as the supply model uses it)
  L (1 - G) scaling, CAPRI's calibration (relSubs cases l. 816-925, Version B l. 1105-1160), CAPRI's inflation 1.019^13
  (l. 1175-1177) taken back out: the model works in 2017 money (KNOWN_ISSUES K108)

VSER: pigs CAPRI's table (AD_basedata p_VSER), as CAPRI's own fallback gives them; cattle CAPRI computes from the
feed, energy and requirement data of the run (l. 49-116), not in hand: the table value is used and recorded as
vser_source = "table" (REGISTERED, docs/AD_SPEC.md; CAPRI's run dump p_VSER will replace it).

Output: capri_data/2017/abatement/ammonia/ad_option.csv
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import importlib.util as _ilu
_sp_mr = _ilu.spec_from_file_location("_mr", Path(__file__).resolve().parents[2] / "tools" / "lib" / "_model_regions.py")
_mr = _ilu.module_from_spec(_sp_mr); _sp_mr.loader.exec_module(_mr)

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "capri_data" / "sources" / "capri_dat" / "ghgtech"
A = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
CLIM = ROOT / "capri_data" / "2017" / "environment" / "climate_zones.csv"

FS = ["0_5", "5_10", "10_15", "15_20", "20_50", "50_100", "100_200", "200_500", "h500"]
SIZE = {"0_5": (0, 5), "5_10": (5, 10), "10_15": (10, 15), "15_20": (15, 20), "20_50": (20, 50),
        "50_100": (50, 100), "100_200": (100, 200), "200_500": (200, 500), "h500": (500, None)}   # p_sizeControl
ADACT = {"DCOL": "DAIRY", "DCOH": "DAIRY", "BULL": "NDAIRY", "BULH": "NDAIRY", "HEIL": "NDAIRY", "HEIH": "NDAIRY",
         "HEIR": "NDAIRY", "SCOW": "NDAIRY", "CAMR": "NDAIRY", "CAFR": "NDAIRY", "CAMF": "NDAIRY", "CAFF": "NDAIRY",
         "PIGF": "SWIN", "SOWS": "SWIN"}                                                              # map_animals
GAINSACT = {"DCOL": "DL_L", "DCOH": "DL_L", "PIGF": "PL_L", "SOWS": "PL_L"}                           # map_gainsact1
#: CAPRI's map from its member states to GAINS countries (map_gainsCount, ad_data_and_cali.gms l. 158-187; the Western
#: Balkans and Turkey take Croatia's, CROA), read from CAPRI's code: member state -> GAINS country
GMS = Path("/home/claude/work/allgms/gams/envind/ad_data_and_cali.gms")
_sp_gt = _ilu.spec_from_file_location("_gt", Path(__file__).resolve().parents[2] / "tools" / "lib" / "gams_text.py")
_gt = _ilu.module_from_spec(_sp_gt); _sp_gt.loader.exec_module(_gt)
GAINSC = {ms: gc for gc, ms in _gt.set_pairs(_gt.read_text(GMS), "map_gainsCount")}
# p_MCF (l. 324-345): nocrustcover, solid, pasture by climate cell
MCF = {10: (0.17, 0.02, 0.01), 11: (0.19, 0.02, 0.01), 12: (0.20, 0.02, 0.01), 13: (0.22, 0.02, 0.01),
       14: (0.25, 0.02, 0.01), 15: (0.27, 0.04, 0.015), 16: (0.29, 0.04, 0.015), 17: (0.32, 0.04, 0.015),
       18: (0.35, 0.04, 0.015), 19: (0.39, 0.04, 0.015), 20: (0.42, 0.04, 0.015), 21: (0.46, 0.04, 0.015),
       22: (0.50, 0.04, 0.015), 23: (0.55, 0.04, 0.015), 24: (0.60, 0.04, 0.015), 25: (0.65, 0.04, 0.015),
       26: (0.71, 0.05, 0.02), 27: (0.78, 0.05, 0.02), 28: (0.80, 0.05, 0.02)}
P_R, P_T, ALPHA, BETA, COP, ENGH = 0.035, 15, -1009.332, 10381.16, 0.05, 7000.0
PRE_CO2, PRE_CH4, MCF_DIG, LEAK, DENS, ECONT, ECONV = 0.02, 0.25, 0.85, 0.03, 0.6557, 55.0, 277.8
EF_HEAT, EH_SOLD, EF_ELEC, EL_USED, PR_ELEC, PR_HEAT = 0.4, 0.3, 0.36, 0.12, 0.10, 0.03
# CAPRI inflates the option's money terms from the base year to 2030 (p_infl ** (2030 - 2017), l. 1175-1177); the
# model works in 2017 money and divides the 2030 terms by the same index (tools/lib/_money.deflator; KNOWN_ISSUES
# K108, 31 October 2026: before, the terms stayed in CAPRI's 2030 money): the net factor is 1 to rounding
_sp_my = _ilu.spec_from_file_location("_money", Path(__file__).resolve().parents[2] / "tools" / "lib" / "_money.py")
_money = _ilu.module_from_spec(_sp_my); _sp_my.loader.exec_module(_money)
INFL = 1.019 ** 13 / _money.deflator(2030)
SENS = 1.0                                              # %sensFac% (refpol_endotech_all_sup.gms l. 243)


def _rd(f):
    with open(f) as h:
        return list(csv.DictReader(h))


def _nat(r):
    return r[:2] + "000000"


def _n1(r):
    return r[:3] + "00000"


def load():
    heads = defaultdict(dict)
    for r in _rd(G / "AD_basedata_p_Heads.csv"):
        heads[(r["dim1"], r["dim2"])][r["dim3"]] = float(r["level"])
    sf = defaultdict(dict)
    for r in _rd(G / "AD_basedata_p_sf.csv"):
        sf[r["dim1"]][r["dim2"]] = float(r["level"])
    p2 = lambda f: {(r["dim1"], r["dim2"]): float(r["level"]) for r in _rd(G / f)}
    gains = {(r["dim1"], r["dim2"], r["dim3"]): float(r["level"]) for r in _rd(G / "gains_ad_p_gainsdata.csv")}
    clim = defaultdict(dict)
    for r in _rd(CLIM):
        if r["zone"].isdigit():
            clim[r["region"]][int(r["zone"])] = float(r["pct"])
    nem = defaultdict(dict)
    for r in _rd(A / "n_cascade_factors.csv"):
        nem[(r["region"], r["activity"])][r["factor"]] = float(r["value"])
    return (heads, sf, p2("AD_basedata_p_MitiShar0.csv"), p2("AD_basedata_p_SharLiq.csv"),
            p2("AD_basedata_p_HousShar.csv"), p2("AD_basedata_p_VSER.csv"), p2("AD_basedata_p_B0.csv"), gains, clim, nem)


def build():
    heads, sf, mitishar0, sharliq, housshar, vser, b0, gains, clim, nem = load()

    def heads_reg(rs, ad):
        if rs == _nat(rs) or heads.get((rs, ad)):
            return dict(heads.get((rs, ad), {}))
        n1, n0 = heads.get((_n1(rs), ad), {}), heads.get((_nat(rs), ad), {})
        return {c: (n1[c] if n1.get(c) else n0.get(c, 0.0)) for c in FS}

    def clean(d):
        out = {}
        for c, v in d.items():
            lo, up = SIZE[c]
            if (up is not None and v > up and c != "h500") or v < lo:
                continue
            out[c] = v
        return out

    def sf_reg(rs):
        own = clean(sf.get(rs, {}))
        if own:
            return own
        n1, n0 = clean(sf.get(_n1(rs), {})), clean(sf.get(_nat(rs), {}))
        return {c: (n1[c] if n1.get(c) else n0.get(c, 0.0)) for c in FS if (n1.get(c) or n0.get(c))}

    def climate(rs):
        c = clim.get(rs) or clim.get(_nat(rs)) or {10: 100.0}
        return {k: v / 100.0 for k, v in c.items()}

    def ech4(vs, b0v, cl):
        f = sum(sh * (1 - PRE_CO2 - MCF[c][0] * PRE_CH4) for c, sh in cl.items())
        return vs * 365 * 1 * b0v * f * MCF_DIG * (1 - LEAK) * DENS * ECONT * ECONV / 1000

    def cad(e, s):
        kw = e * EF_ELEC / ENGH
        crf = P_R / (1 - 1 / (1 + P_R) ** P_T)
        return kw * (ALPHA * math.log(kw * s) + BETA) * (crf + COP)

    def curve(rs, ad, e):
        h, s = heads_reg(rs, ad), sf_reg(rs)
        tot = sum(h.values())
        if tot <= 0:
            return None
        acs, acc = {}, {}
        for i, c in enumerate(FS):
            up = FS[i:]
            hh = sum(h.get(k, 0.0) for k in up)
            if hh:
                acs[c] = hh / tot
                acc[c] = sum(cad(e, s[k]) * h.get(k, 0.0) for k in up if s.get(k)) / hh
        p1, p2 = ("h500", "200_500") if h.get("h500") else ("200_500", "100_200")
        if p1 not in acs or p2 not in acs or acs[p2] == acs[p1]:
            return None
        sl = (acc[p2] - acc[p1]) / (acs[p2] - acs[p1])
        mx = (h.get("200_500", 0.0) + h.get("h500", 0.0)) / tot
        return sl, acc[p1] - sl * acs[p1], mx

    # the regional units' own rows (a fixed list of an older CAPRI had LU000000, not a unit, and missed HR000000; K86)
    pairs = sorted({k for k in nem if k[1] in ADACT and _mr.regional_row(k[0])})
    rows = []
    for rs, act in pairs:
        ms, ad = _nat(rs), ADACT[act]
        f = nem[(rs, act)]
        L, Gz = f.get("tsl", 0.0), f.get("tsg", 0.0)
        lg = L * (1.0 - Gz)
        if lg <= 0:
            continue
        cl = climate(rs)
        vs = vser.get((ms, ad))
        if vs is None:
            continue
        b0v = b0.get(("EU000000", ad))
        e = ech4(vs, b0v, cl)
        # the cost curve: the region's own heads (or the per-class fallback); RU without heads in the two largest
        # classes takes its member state's line (l. 510-517)
        cv = curve(rs, ad, e)
        hreg = heads_reg(rs, ad)
        if cv is None or (not hreg.get("h500") and not hreg.get("200_500")):
            cv = curve(ms, ad, ech4(vs, b0v, climate(ms))) or cv
        if cv is None:
            continue
        slope_raw, indep_raw, mx_v = cv
        m0 = mitishar0.get((rs, ad), mitishar0.get((_n1(rs), ad), mitishar0.get((ms, ad), 0.0)))
        hs = housshar.get((ms, ad), 1.0 if ad == "SWIN" else 0.0)
        ini_v = m0 * sharliq.get((ms, ad), 0.0) * hs / lg if m0 else 0.0
        gc = GAINSC.get(_mr.national_code(rs))
        ga = GAINSACT.get(act, "OL_L")
        elec = gains.get((gc, ga, "eprice_ind")) or PR_ELEC
        heat = 0.5 * gains.get((gc, ga, "eprice_agr"), 0.0) or PR_HEAT
        rev_raw = e * (EF_HEAT * EH_SOLD * heat + EF_ELEC * (1 - EL_USED) * elec)
        # QE_AD / QE_NOC at member-state level (L, G and climate of the member state)
        clm = climate(ms)
        mnc = sum(sh * MCF[c][0] for c, sh in clm.items())
        msol = sum(sh * MCF[c][1] for c, sh in clm.items())
        mpas = sum(sh * MCF[c][2] for c, sh in clm.items())
        Sl = 1.0 - L
        qn = mnc * (1 - Gz) * L + msol * (1 - Gz) * Sl + mpas * Gz
        qa = ((mnc * PRE_CH4 + (1 - PRE_CO2 - mnc * PRE_CH4) * MCF_DIG * LEAK) * (1 - Gz) * L
              + msol * (1 - Gz) * Sl + mpas * Gz)
        r_ch4 = qa / qn if qn > 0 else 1.0
        # L (1 - G) scaling (l. 747-765), costParSqr = 2 SLOPE (l. 629)
        cpl, cps, rev = indep_raw * lg, 2.0 * slope_raw * lg, rev_raw * lg
        mx = mx_v
        # calibration (l. 816-925, Version B l. 1105-1160)
        rs1 = rs0 = 0.0
        if ini_v > 0:
            mi = max(1e-4, (mx - ini_v) / mx) if mx > 0 else 1e-4
            if cpl > 0 and rev == 0:
                rs1 = 0.8 * SENS * mi
            if cpl < 0 or rev > 0:
                rs1 = (-0.2 * (cpl < 0) + 0.2 * (rev * cpl > 0)) * SENS * mi
        else:
            if cpl > 0:
                rs1, rs0 = 1.2 * SENS, 0.2 * SENS
            if cpl < 0 or rev > 0:
                rs1 = (-0.5 * (cpl < 0) + 0.5 * (rev * cpl > 0)) * SENS
                rs0 = (-0.1 * (cpl < 0) + 0.1 * (rev * cpl > 0)) * SENS
        S1, S0 = rs1 * cpl, rs0 * cpl
        pmp_sqr = 0.0
        if cps:
            mzero = (S1 - S0) / cps + ini_v
            mup, mlo = min(1.5 * mx, 1.0), max(0.5 * mx, 1.1 * ini_v)
            if mzero > mup and mup - ini_v:
                pmp_sqr = (S1 - S0) / (mup - ini_v) - cps
            elif mzero < mlo and mlo - ini_v:
                pmp_sqr = (S1 - S0) / (mlo - ini_v) - cps
        k2 = (cps + pmp_sqr) * INFL
        rows.append([rs, act, lg, ini_v * lg, mx * lg, r_ch4,
                     cpl * INFL, cps * INFL, rev * INFL, pmp_sqr * INFL,
                     S0 * INFL / lg, k2 / (lg * lg), vs,
                     "table" if ad != "SWIN" else "table (CAPRI's own fallback)"])
    with open(A / "ad_option.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "activity", "lg", "ini", "max", "r_ch4", "costParLin", "costParSqr", "revenue",
                    "pmpParSqr", "thresh", "slope", "vser", "vser_source"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    print(len(rows), "rows,", len({r[0] for r in rows}), "regions")
    for r in rows:
        if r[0] in ("DE110000", "DK000000") and r[1] in ("DCOL", "PIGF"):
            print(r)

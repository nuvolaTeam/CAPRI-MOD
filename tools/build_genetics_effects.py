"""CAPRI's cattle genomics options per model region and animal (envind/breeding.gms).

genet_yld - dairy cows with higher milk yields (MRUMI producing COMI: the model's DCOW):
  TOP     = mean projected 2030 milk yield of DK, PT, SE, FI (CAPRI's trends; per DCOL / DCOH)
  gain    = ghgTechMYld x min(Y x (1 - curb), max(0, TOP - Y)); curbs HR 0.6, LT 0.6, KO 0.6, SI 0.2, PL 0.2
            ghgTechMYld = 0.2 (CAPRI's endotech references of the JRC121368 era, pol_input/ecampa/
            refpol_endotech_set14_ini.gms; the 2030 Green Deal file in this installation sets 0, but
            JRC121368 Table 17 shows the option adopted on 15% of dairy cows)
  requirements recomputed for the new yield with breeding.gms's own functions (fat 4%, live weight 600 kg):
      energy  NEL + NEM + NEP + NEA:  NEL = (0.4 x 4 + 1.47) x milk, NEM = 600^0.75 x 0.386 x 365,
              NEP = 0.10 NEM, NEA = 0.17 NEM x (365 - HD)/365 x (1 - Et/100)   (MITERRA HD, Et)
      protein CRPR = (14 x 4 + 28)/1000 x milk + (117 + 0.6 x 600)/1000 x 365 + 1.3 x 42
      dry matter DRMN = (0.0185 x 600 + 0.305 x FCM) x 305 + 0.0185 x 600 x 60, FCM = milk / 305;
              DRMX = 1.2 DRMN
      manure N  = CRPR / 6 - N exports (milk 0.0054 kg N / kg)  -> change per cow = (0.084/6 - 0.0054) x gain
  impacts = new / old - 1 (as breeding.gms against p_animReqLit); the manure change is taken relative to the
  model's own manure N per cow
  cost    costParLin = max(20, 0.1 x gain x UVAG(COMI) / 1000) EUR per cow
genet_eff - non-dairy ruminants with lower energy need (MRUMI not producing COMI, not HEIR, not SHGM):
  energy -ghgTechFEff (0.1), protein -0.5 x 0.1, manure N = CRPR change x (MANN + N exports) / MANN with
  N exports in beef (0.022 / 0.54 kg N per kg carcass) and sheep and goat meat (same factor);
  cost max(2, 0.05 x annual feed cost per place x 0.1); eligible share of the model animal: HFRS only its
  fattening heifers HEIF (not HEIR, cattle_intensity share_low + share_high), SHGP only SHGF (res_17 levels)
Calibration terms (breeding.gms Part 2): relSubs1 = 1.2 (cost > 0), relSubs0 = 0.01 (genet_yld) / 0.10
(genet_eff), IniShare 0, MaxShare 1.

The technology parameters ghgTechMYld and ghgTechFEff are SCENARIO SETTINGS in CAPRI (pol_input/greendeal/
refpol_endotech_all_sup.gms: "$if not SETGLOBAL ghgTechMYld $SETGLOBAL ghgTechMYld 0", ghgTechFEff 0.1), loaded
by the scenario configuration for the reference and the policy run alike. Every effect above is linear in its
parameter and the cost is max(floor, linear term), so the table is written PER UNIT of the parameter and the
model scales it with the run's settings (capri_mod/policy/endotech.py); an option whose parameter is 0 does not
exist (breeding.gms: genet_yld only $ p_ghgTechMYld, genet_eff only $ p_ghgTechFEff).

Output: capri_data/2017/abatement/mitigation/genetics_effects.csv
  region, animal, option, tech_param, elig_share, d_milk_rel, d_ener_rel, d_crpr_rel, d_drmn_rel, d_drmx_rel,
  d_mann_rel (per unit of tech_param), cost_floor, cost_per_unit (EUR per head; cost = max(floor, per_unit x
  parameter)), relsubs0, relsubs1

    python tools/build_genetics_effects.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
A = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
CURB = {"HR": 0.6, "LT": 0.6, "KO": 0.6, "SI": 0.2, "PL": 0.2}
NEM = 600 ** 0.75 * 0.386 * 365
NEL_KG = 0.4 * 4.0 + 1.47
CRPR_KG, CRPR_FIX = (14 * 4.0 + 28) / 1000, (117 + 0.6 * 600) / 1000 * 365 + 1.3 * 42
DRMN_KG, DRMN_FIX = 0.305, 0.0185 * 600 * 305 + 0.0185 * 600 * 60
N_KG_MILK = CRPR_KG / 6.0 - 0.0054
EFF_ANIMALS = ("BULL", "BCOW", "CALV", "HFRS", "SHGP")
MEAT = {"BULL": "BEEF", "BCOW": "BEEF", "CALV": "BEEF", "HFRS": "BEEF", "SHGP": "SGMT"}
CTRY = {"IE": "IR", "GR": "EL", "BE": "BL", "LU": "BL"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()

    t = pd.read_csv(M / "trends_milk_yield_1730.csv")
    Y = {(r.region, r.activity): float(r.milk_yield_kg) for r in t.itertuples()}
    top = {x: sum(Y.get((c, x), 0.0) for c in ("DK000000", "PT000000", "SE000000", "FI000000")) / 4 for x in ("DCOL", "DCOH")}
    md = pd.read_csv(A / "capri_mann_days_2030.csv")
    L = {(r.region, r.activity): float(r.value) for r in md[md.item == "LEVL"].itertuples()}
    rce = pd.read_csv(A / "RCEmissions.csv")
    R = {(r.region, r.animal_mitt, r.item): r.value for r in rce.itertuples()}
    uv = pd.read_csv(ROOT / "capri_data" / "sources" / "capri_baseline" / "capri_uvag_store_1730.csv")
    UV = {(r.region, r.product): float(r.uvag_2030) for r in uv.itertuples()}
    mann = pd.read_csv(ROOT / "capri_data" / "2017" / "environment" / "livestock_manure_n_coef.csv", index_col=0)
    prod = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "livestock_output_by_product_coef.csv", index_col=0)
    ci = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "cattle_intensity.csv")
    heif = {r.region: float(r.share_low) + float(r.share_high) for r in ci[ci.animal == "HFRS"].itertuples()}
    rations = json.load(open(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.json"))["regions"]
    # sheep and goats: SHGF share of SHGM + SHGF (res_17 levels)
    lev = defaultdict(dict)
    pat = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(SHGM|SHGF)'\.'LEVL'\.'Y'\s+([-\d.Ee+]+)")
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = pat.match(line)
            if m:
                lev[m.group(1)][m.group(2)] = float(m.group(3))

    def shgf_share(c8, ms):
        for c in (c8, ms):
            d = lev.get(c)
            if d and (d.get("SHGM", 0) + d.get("SHGF", 0)) > 0:
                return d.get("SHGF", 0.0) / (d.get("SHGM", 0.0) + d.get("SHGF", 0.0))
        return None

    def milk_gain(c8):
        num = den = y0 = 0.0
        for x in ("DCOL", "DCOH"):
            y, lv = Y.get((c8, x)), L.get((c8, x), 0.0)
            if not y or not lv:
                continue
            g = min(y * (1 - CURB.get(c8[:2], 0.0)), max(0.0, top[x] - y))
            num += lv * g; y0 += lv * y; den += lv
        return (y0 / den, num / den) if den > 0 else None

    rows = []
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg, ms)
        ctry = CTRY.get(reg[:2], reg[:2]) + "000000"
        # genet_yld
        mg = milk_gain(c8) or milk_gain(ms)
        mn = float(mann.at[reg, "DCOW"]) if reg in mann.index and pd.notna(mann.at[reg, "DCOW"]) else 0.0
        if mg and mn > 0:
            y, g = mg
            hd, et = R.get((ctry, "DAICOW_L", "HD"), 365.0), R.get((ctry, "DAICOW_L", "Et"), 0.0) or 0.0
            nea = 0.17 * NEM * max(0.0, 365 - hd) / 365 * (1 - et / 100)
            E = NEL_KG * y + 1.1 * NEM + nea
            uvc = UV.get((ms, "COMI"), 0.0)
            rows.append(dict(region=reg, animal="DCOW", option="genet_yld", tech_param="ghgTechMYld", elig_share=1.0,
                             d_milk_rel=g / y, d_ener_rel=NEL_KG * g / E,
                             d_crpr_rel=CRPR_KG * g / (CRPR_KG * y + CRPR_FIX),
                             d_drmn_rel=DRMN_KG * g / (DRMN_KG * y + DRMN_FIX),
                             d_drmx_rel=DRMN_KG * g / (DRMN_KG * y + DRMN_FIX),
                             d_mann_rel=N_KG_MILK * g / mn,
                             cost_floor=20.0, cost_per_unit=0.1 * g * uvc / 1000.0, relsubs0=0.01, relsubs1=1.2))
        # genet_eff
        for an in EFF_ANIMALS:
            if reg not in mann.index or an not in mann.columns or not (float(mann.at[reg, an] or 0) > 0):
                continue
            el = 1.0
            if an == "HFRS":
                el = heif.get(reg)
            elif an == "SHGP":
                el = shgf_share(c8, ms)
            if not el:
                continue
            mt = f"{an}.{MEAT[an]}"
            meat_t = float(prod.at[reg, mt]) if (reg in prod.index and mt in prod.columns and pd.notna(prod.at[reg, mt])) else 0.0
            expt = meat_t * 1000 * 0.022 / 0.54                   # kg N per head
            mN = float(mann.at[reg, an])
            rr = (rations.get(reg) or {}).get(an)
            fc = sum(float(rr["ration"][f]) * float(rr["price"][f]) for f in rr["ration"]) if rr else 0.0
            rows.append(dict(region=reg, animal=an, option="genet_eff", tech_param="ghgTechFEff", elig_share=el,
                             d_milk_rel=0.0, d_ener_rel=-1.0, d_crpr_rel=-0.5, d_drmn_rel=0.0, d_drmx_rel=0.0,
                             d_mann_rel=-0.5 * (mN + expt) / mN,
                             cost_floor=2.0, cost_per_unit=0.05 * fc, relsubs0=0.10, relsubs1=1.2))
    out = pd.DataFrame(rows)
    out.to_csv(M / "genetics_effects.csv", index=False, float_format="%.6g")
    y = out[out.option == "genet_yld"]; e = out[out.option == "genet_eff"]
    print(f"genet_yld per unit of ghgTechMYld: {len(y)} regions; milk +{y.d_milk_rel.median():.1%} (median, max "
          f"{y.d_milk_rel.max():.1%}); at 0.2: milk +{0.2 * y.d_milk_rel.median():.1%}, cost median EUR "
          f"{(y.cost_per_unit * 0.2).clip(lower=20).median():.0f}/cow")
    print(f"genet_eff per unit of ghgTechFEff: {len(e)} region-animals; manure N {e.d_mann_rel.median():+.1%} (median); "
          f"at 0.1 cost median EUR {(e.cost_per_unit * 0.1).clip(lower=2).median():.1f}/head; eligible HFRS "
          f"{e[e.animal=='HFRS'].elig_share.median():.2f}, "
          f"SHGP {e[e.animal=='SHGP'].elig_share.median():.2f}")


if __name__ == "__main__":
    main()

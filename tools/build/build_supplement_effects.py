"""CAPRI's feed supplements linseed and nitrate per model region and animal (envind/line_nitr.gms; Sprint 9g).

star 3.0's Green Deal reference technology file switches the supplements on (pol_input/greendeal/
refpol_endotech_all_sup.gms: ghgTechLineNitr 1 includes envind/line_nitr.gms; ghgTechActiveFeed LINE, NITR, AComLN,
3NOP, LowNFeed). CAPRI's definitions, per cattle activity in the EU member states (ms_LiNi):

  dosage   ShrOfDM: linseed 5% of dry-matter intake as fat; nitrate 1.5% of DM (replacement heifers HEIR 1%)
  linseed  supplies nutrients like a feed (supply_model.gms REQSE_ / REQSN_): fresh matter = DRMA x days x ShrOfDM x
           share / TotFAT, TotFAT = rapeseed fat x dry matter (fedcof.dat EU.DCOL.RAPE: EE 40.5, DM 89.9, the
           values line_nitr.gms names), times the OOIL nutrient row of p_nutCont (energy ENNE, crude protein CRPR,
           dry matter DRMA, which counts against the minimum and the maximum dry-matter intake)
  nitrate  replaces crude protein: CRPR requirement - DRMA x days x share x 0.0154 x ShrOfDM x 100
  CH4ENT   linseed -5% per point of fat in DM (-25%), nitrate -10% per point of nitrate (-15%, HEIR -10%);
           combined (AComLN) multiplicative; p_mitiEffFac(2030) = 1
  cost     GHG_Mit_Cost_: costParLin x DRMA x days / 1000 x ShrOfDM per head adopting; costParLin linseed
           674 x 89.9 / 40.5 EUR per t fat, nitrate 873 EUR per t (2017 money: CAPRI inflates these from the base
           year, the model stays in 2017 money), halved for the cost savings (line_nitr.gms l. 357)
  shares   MaxShare = the level of CAPRI's maximum calibration run (+2e-6; it already carries the dairy 10/12 months,
           the 50% of other cattle, the stable days (1 - grazing share) and the fat-balance correction); IniShare 0
  calib.   relSubs0 0.05, relSubs1 1.2 (costParLin > 0), pmpParsqr = max(0.1 |c|, c (relSubs1 - relSubs0) -
           (costsaving0 - costsaving1)) / MaxShare (the drop from CAPRI's two runs, column dsav per model head:
           tools/lib/_capri_costsavings.py)

DRMA (CAPRI's dry-matter intake per head and day of the requirement functions) is not in the results; the model
uses CAPRI's own estimate from breeding.gms: DRMN + (|DRMX| - DRMN) / 4, here per model head and year from the
ration requirements (DMIN, DMAX). Per model animal the CAPRI activities are aggregated with weights LEVL x MaxShare
(res_17, as lownfeed_effects.csv): DCOW = DCOL + DCOH, BCOW = SCOW, BULL = BULL + BULH, HFRS = HEIL + HEIH + HEIR,
CALV = CAMF + CAFF + CAMR + CAFR.

Not carried (REGISTERED): CAPRI's soft constraint on total fat in the ration (SupplementPerc_, which needs the fat
of every feed: p_digestPar is not among the inputs; its effect on the maximum shares is in the max-run levels); 3-NOP,
whose only effect is on enteric CH4 (no cost saving: its calibration marginals are Eps and CAPRI's maximum run leaves
it at 1e-6), so without an emission price in the supply model its optimal share is zero in CAPRI's calibration.

Output: capri_data/2017/abatement/mitigation/supplement_effects.csv, the schema of genetics_effects.csv (options
LINE_Tot and Nitr_Tot, tech_param ghgTechLineNitr, a switch: param_switch 1) plus ch4ent_rel, the change of enteric
CH4 per head adopting, and shr_of_dm.

    python tools/build/build_supplement_effects.py
"""
from __future__ import annotations
import importlib.util, json
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
LEV = ROOT / "capri_data" / "sources" / "envind" / "res17_mann_crpr_expt.csv"
MAP = {"DCOW": ("DCOL", "DCOH"), "BCOW": ("SCOW",), "BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR"),
       "CALV": ("CAMF", "CAFF", "CAMR", "CAFR")}
#: line_nitr.gms: ShrOfDM, CH4ENT change per unit of ShrOfDM (x100 points), halved costParLin (EUR per t)
OPT = {"LINE_Tot": dict(shr=0.05, ch4=-0.05 * 100, cost=0.5 * 674 * 89.9 / 40.5),
       "Nitr_Tot": dict(shr=0.015, ch4=-0.1 * 100, cost=0.5 * 873.0)}
SHR_HEIR_NITR = 0.01
#: fedcof.dat EU.DCOL.RAPE (line_nitr.gms l. 202): ether extract and dry matter, % - linseed taken as rapeseed
RAPE_EE, RAPE_DM = 40.5, 89.9


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    lv = pd.read_csv(LEV)
    L = {(r.region, r.activity): float(r.value) for r in lv[lv["item"] == "LEVL"].itertuples()}
    cs = pd.read_csv(ROOT / "capri_data" / "sources" / "ghgtech" / "capri_costsavings_2030.csv")
    cs = cs[(cs.run == "max") & cs.technology.isin(list(OPT))]
    MX = {(r.region, r.activity, r.technology): float(r.level) for r in cs.itertuples() if pd.notna(r.level)}
    nut = pd.read_csv(M / "p_nutCont.csv")
    ooil = {r.nutrient: float(r.value) for r in nut[nut.feed == "OOIL"].itertuples()}
    tot_fat = RAPE_EE / 100.0 * RAPE_DM / 100.0
    rations = json.load(open(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.json"))["regions"]

    rows, nskip = [], 0
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg, ms)
        rr = rations.get(reg) or {}
        for an, acts in MAP.items():
            ra = rr.get(an)
            if not ra:
                continue
            req = ra["req"]
            E, P, DMIN = float(req.get("ENNE", 0)), float(req.get("CRPR", 0)), float(req.get("DMIN", 0))
            DMAX = float(req.get("DMAX", 0) or 0)
            if E <= 0 or P <= 0 or DMIN <= 0:
                continue
            drma = DMIN + (max(DMAX, DMIN) - DMIN) / 4.0          # breeding.gms: kg DM per head and year
            for opt, o in OPT.items():
                wall = wsum = 0.0
                shr = 0.0
                for x in acts:
                    lvl = L.get((c8, x)) or L.get((ms, x)) or 0.0
                    if lvl <= 0:
                        continue
                    wall += lvl
                    mx = MX.get((c8, x, opt), MX.get((ms, x, opt)))
                    if mx is None or mx <= 2e-6:
                        continue
                    mx = min(1.0, mx + 2e-6)
                    s_ = SHR_HEIR_NITR if (opt == "Nitr_Tot" and x == "HEIR") else o["shr"]
                    wsum += lvl * mx
                    shr += lvl * mx * s_
                if wsum <= 0 or wall <= 0:
                    nskip += 1
                    continue
                shr /= wsum
                d = dict(region=reg, animal=an, option=opt, tech_param="ghgTechLineNitr", param_switch=1,
                         elig_share=wsum / wall, d_milk_rel=0.0, d_ener_rel=0.0, d_crpr_rel=0.0, d_drmn_rel=0.0,
                         d_drmx_rel=0.0, d_mann_rel=0.0, cost_floor=0.0,
                         cost_per_unit=o["cost"] * drma / 1000.0 * shr,
                         relsubs0=0.05, relsubs1=1.2, gamma_floor=0.1,
                         ch4ent_rel=o["ch4"] * shr, shr_of_dm=shr)
                if opt == "Nitr_Tot":
                    d["d_crpr_rel"] = -drma * 0.0154 * shr * 100.0 / P
                else:
                    fm = drma * shr / tot_fat                       # kg linseed (fresh matter) per head and year
                    d["d_ener_rel"] = -fm * ooil["ENNE"] / E
                    d["d_crpr_rel"] = -fm * ooil["CRPR"] / P
                    d["d_drmn_rel"] = -fm * ooil["DRMA"] / DMIN
                    if DMAX > 0:
                        d["d_drmx_rel"] = -fm * ooil["DRMA"] / DMAX
                rows.append(d)
    out = pd.DataFrame(rows)
    # CAPRI's cost-saving drop between its ini and max calibration runs (line_nitr.gms l. 289-332 with breeding.gms's
    # formula), EUR per model head adopting (ghgTechLineNitr a switch)
    import sys as _sys; _sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from _capri_costsavings import costsaving_drop
    ds = {o_: costsaving_drop(MAP, o_) for o_ in OPT}
    out["dsav"] = [ds[r.option].get((r.region, r.animal), float("nan")) for r in out.itertuples()]
    out.to_csv(M / "supplement_effects.csv", index=False, float_format="%.6g")
    g = out.groupby(["option", "animal"]).agg(n=("region", "size"), elig=("elig_share", "median"),
                                             ener=("d_ener_rel", "median"), crpr=("d_crpr_rel", "median"),
                                             cost=("cost_per_unit", "median"), ch4=("ch4ent_rel", "median"))
    print(f"supplement_effects.csv: {len(out)} region-animal-options ({nskip} without CAPRI maximum shares)")
    print(g.round(3).to_string())


if __name__ == "__main__":
    main()

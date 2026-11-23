"""CAPRI's feed supplements linseed, nitrate and 3-NOP per model region and animal (envind/line_nitr.gms; the port of CAPRI's feed options).

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

The requirements are CAPRI's of the simulation year, per activity: p_animReq(RU, act, "T", DRMA | ENNE | CRPR | DRMN |
DRMX) of sim_ini_21730 (CAPRI's 2030 simulation loads them from it, capmod/load_sim_ini_gdx.gms l. 100-111, as for
the low-N feed, KNOWN_ISSUES K194), per head and day; the dosage, the cost and the effects relative to the
requirements are computed per activity with them (the days cancel in the ratios; the cost per head and year is
x 365, a model head being a place on the census, K180). Until 23 November 2026 the intake was breeding.gms's estimate
DRMN + (|DRMX| - DRMN) / 4 from the model's 2017 ration requirements (register DEP-53). Per model animal the CAPRI
activities are aggregated with weights LEVL x MaxShare (res_17, as lownfeed_effects.csv): DCOW = DCOL + DCOH,
BCOW = SCOW, BULL = BULL + BULH, HFRS = HEIL + HEIH + HEIR, CALV = CAMF + CAFF + CAMR + CAFR. dm_intake: the model
animal's dry-matter intake per head and year, 365 x CAPRI's DRMA of its activities weighted by their places on the
census at 2030 (DATA LEVL x DAYS / 365 at Y), the intake of the ration fat limit SupplementPerc_
(abatement._supp_fat_spec).

3-NOP (since 29 October 2026, KNOWN_ISSUES K93; nop_rows below): dairy and suckler cows, 0.09% of dry matter, enteric
CH4 cut by CAPRI's formula in the ration's fibre and fat (tools/lib/_capri_digest.py from CAPRI's digestibility
table, tools/build/build_digestibility_table.py), no cost saving and no effect on the requirements; without an
emission price its share stays 0 (CAPRI's calibration: its marginals are 0 in both calibration runs).

Output: capri_data/2017/abatement/mitigation/supplement_effects.csv, the schema of genetics_effects.csv (options
LINE_Tot, Nitr_Tot and 3NOP_Tot, tech_param ghgTechLineNitr, a switch: param_switch 1) plus ch4ent_rel, the change of enteric
CH4 per head adopting, shr_of_dm and dm_intake.

    python tools/build/build_supplement_effects.py
"""
from __future__ import annotations
import importlib.util
from collections import defaultdict
import sys
from pathlib import Path

import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import REFERENCE, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
LEV = ROOT / "capri_data" / "sources" / "intermediate" / "envind" / "res17_mann_crpr_expt.parquet"
#: CAPRI's 2017 regional results (CAPREG text dumps res_17<MS>.txt): the rations and feed data 3-NOP's effect needs
DUMPS = SOURCES / "capreg"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
sys.path.insert(0, str(ROOT))
#: CAPRI's 2030 simulation data (tools/build/build_simini_reference.py): p_animReq and DATA
SIMINI = REFERENCE / "simini" / "simini_21730"
MAP = {a: _MC.ANIMALS[a] for a in ("DCOW", "BCOW", "BULL", "HFRS", "CALV")}
#: line_nitr.gms: ShrOfDM, CH4ENT change per unit of ShrOfDM (x100 points), halved costParLin (EUR per t)
OPT = {"LINE_Tot": dict(shr=0.05, ch4=-0.05 * 100, cost=0.5 * 674 * 89.9 / 40.5),
       "Nitr_Tot": dict(shr=0.015, ch4=-0.1 * 100, cost=0.5 * 873.0)}
SHR_HEIR_NITR = 0.01
#: fedcof.dat EU.DCOL.RAPE (line_nitr.gms l. 202): ether extract and dry matter, % - linseed taken as rapeseed
RAPE_EE, RAPE_DM = 40.5, 89.9


#: 3-NOP (line_nitr.gms l. 58-61): the dairy cows (DACT_TO_PACT DCOW: DCOL, DCOH) and the suckler cows (SCOW)
NOP_MAP = {a: _MC.ANIMALS[a] for a in ("DCOW", "BCOW")}
#: 0.09% of dry matter as Bovaer10 (l. 86); 17,500 EUR per t of Bovaer10 in 2022 money, deflated to 2017 with CAPRI's
#: general inflation 1.019 (l. 217-221; the model in 2017 money as the other supplements), not halved (l. 357)
NOP_SHR, NOP_COST, NOP_DAYS = 0.0009, 17500.0 / 1.019 ** (2022 - 2017), 305.0 / 365.0


def capri_req_2030(acts):
    """CAPRI's 2030 requirements and places per regional unit and activity: ({(unit, act): {item: value per head and
    day}} of sim_ini_21730's p_animReq at "T" (DRMA, ENNE, CRPR, DRMN, DRMX), {(unit, act): LEVL x DAYS / 365} of its
    DATA at Y, the places on the census)."""
    import gzip as _gz
    import csv as _csv
    acts = set(acts)
    R = defaultdict(dict)
    with _gz.open(SIMINI / "p_animReq.csv.gz", "rt", newline="") as fh:
        for r in _csv.DictReader(fh):
            if r["d1"] in acts and r["d2"] == "T" and r["d3"] in ("DRMA", "ENNE", "CRPR", "DRMN", "DRMX"):
                R[(r["d0"], r["d1"])][r["d3"]] = float(r["value"])
    LD = defaultdict(dict)
    with _gz.open(SIMINI / "DATA.csv.gz", "rt", newline="") as fh:
        for r in _csv.DictReader(fh):
            if r["d1"] in acts and r["d2"] in ("LEVL", "DAYS") and r["d3"] == "Y":
                LD[(r["d0"], r["d1"])][r["d2"]] = float(r["value"])
    places = {k: v.get("LEVL", 0.0) * v.get("DAYS", 0.0) / 365.0 for k, v in LD.items()}
    return dict(R), places


def dm_intake(c8, members, R, places):
    """The model animal's dry-matter intake per head and year: 365 x CAPRI's 2030 DRMA of its activities weighted by
    their places on the census (a model head is a place, K180); None without CAPRI's intake."""
    w = [(places.get((c8, x), 0.0), R.get((c8, x), {}).get("DRMA", 0.0)) for x in members]
    sw = sum(h for h, d in w if d > 0)
    return 365.0 * sum(h * d for h, d in w if d > 0) / sw if sw > 0 else None


def nop_rows(mr, to_c8, L, rations, R, places):
    """3-NOP per model region and animal (KNOWN_ISSUES K93; envind/line_nitr.gms):

      MaxShare  (1 - GRAZ) x 305/365 of the member state (the stable days of the milking period; GRAZ CAPRI's grazing
                share, envind/ammo.gms l. 604-613, as build_ammonia_technologies.grazing), not lowered by the maximum
                calibration run (l. 340-343 exclude 3NOP);
      CH4ENT    x (1 - (32.36 + 0.282 (dose - 70.5) - 0.915 (NDF - 32.9) - 3.08 (FAT - 4.2)) / 100) per head adopting,
                dose 90 mg of active substance per kg DM, NDF and FAT the member state's ration (tools/lib/_capri_digest.py,
                envind/digestibility.gms; l. 124-134), p_mitiEffFac 1;
      cost      GHG_Mit_Cost_: costParLin x DRMA x days / 1000 x ShrOfDM per head adopting; no cost saving (CAPRI's
                calibration marginals are 0), relSubs0 0.05, relSubs1 1.2, floor 0.1 (l. 375-430).
    Member states of the EU only (ms_LiNi, l. 25). The CAPRI activities are aggregated with weights LEVL x MaxShare."""
    import csv as _csv
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools" / "lib"))
    _sys.path.insert(0, str(ROOT / "tools" / "build"))
    import _capri_digest as G
    from build_ammonia_technologies import graz_share
    codes = ROOT / "capri_data" / "codes" / "capri"
    f2o = [(r["feed"], r["row"]) for r in _csv.DictReader(open(codes / "FEED_TO_O.csv"))]
    ms_ru = defaultdict(list)
    for r in _csv.DictReader(open(codes / "MS_RU.csv")):
        ms_ru[r["ms"]].append(r["ru"])
    # CAPRI's ms_LiNi: the EU's member states (its EU trade blocks, tools/lib/_model_regions.EU_MS; until 4 November
    # 2026 every member state of regional_units.csv but Norway, which took in the UK, Turkey and the Western Balkans
    # once their units were listed)
    eu_ms = set(mr.EU_MS)
    acts = sorted({x for v in NOP_MAP.values() for x in v})
    comp, mx = {}, {}
    for ms in sorted(eu_ms):
        dump = DUMPS / f"res_17{ms[:2]}.txt"
        g = lambda act, ms=ms: graz_share(ms, act)
        comp[ms] = G.ration_ndf_fat(dump, ms, ms_ru.get(ms, []), f2o, acts, g)
        for act in acts:
            mx[(ms, act)] = (1.0 - g(act)) * NOP_DAYS
    rows = []
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        if ms not in eu_ms:
            continue
        c8 = to_c8.get(reg, ms)
        ra = (rations.get(reg) or {})
        for an, mem in NOP_MAP.items():
            r_ = ra.get(an)
            if not r_:
                continue
            wall = wsum = ch4 = cost = 0.0
            for x in mem:
                lvl = L.get((c8, x)) or L.get((ms, x)) or 0.0
                if lvl <= 0:
                    continue
                wall += lvl
                m_ = mx.get((ms, x), 0.0)
                nf = comp.get(ms, {}).get(x)
                drma = R.get((c8, x), {}).get("DRMA", 0.0)          # CAPRI's 2030 intake per head and day
                if m_ <= 0 or nf is None or drma <= 0:
                    continue
                wsum += lvl * m_
                ch4 += lvl * m_ * G.nop_ch4_rel(*nf, NOP_SHR)
                cost += lvl * m_ * NOP_COST * drma * 365.0 / 1000.0 * NOP_SHR
            if wsum <= 0 or wall <= 0:
                continue
            rows.append(dict(region=reg, animal=an, option="3NOP_Tot", tech_param="ghgTechLineNitr", param_switch=1,
                             elig_share=wsum / wall, d_milk_rel=0.0, d_ener_rel=0.0, d_crpr_rel=0.0, d_drmn_rel=0.0,
                             d_drmx_rel=0.0, d_mann_rel=0.0, cost_floor=0.0,
                             cost_per_unit=cost / wsum, relsubs0=0.05, relsubs1=1.2,
                             gamma_floor=0.1, ch4ent_rel=ch4 / wsum, shr_of_dm=NOP_SHR,
                             dm_intake=dm_intake(c8, mem, R, places)))
    return rows


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    lv = read_source(LEV)
    L = {(r.region, r.activity): float(r.value) for r in lv[lv["item"] == "LEVL"].itertuples()}
    cs = read_source(ROOT / "capri_data" / "sources" / "intermediate" / "ghgtech" / "capri_costsavings_2030.parquet")
    cs = cs[(cs.run == "max") & cs.technology.isin(list(OPT))]
    MX = {(r.region, r.activity, r.technology): float(r.level) for r in cs.itertuples() if pd.notna(r.level)}
    nut = _read_csv(M / "p_nutCont.csv")
    ooil = {r.nutrient: float(r.value) for r in nut[nut.feed == "OOIL"].itertuples()}
    tot_fat = RAPE_EE / 100.0 * RAPE_DM / 100.0
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.nested_tables import read_feed_rations
    rations = read_feed_rations(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv")
    R, places = capri_req_2030({x for v in MAP.values() for x in v})

    rows, nskip = [], 0
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg, ms)
        rr = rations.get(reg) or {}
        for an, acts in MAP.items():
            ra = rr.get(an)
            if not ra:
                continue
            dmi = dm_intake(c8, acts, R, places)
            for opt, o in OPT.items():
                wall = wsum = 0.0
                acc = defaultdict(float)
                for x in acts:
                    lvl = L.get((c8, x)) or L.get((ms, x)) or 0.0
                    if lvl <= 0:
                        continue
                    wall += lvl
                    mx = MX.get((c8, x, opt), MX.get((ms, x, opt)))
                    q = R.get((c8, x), {})
                    if mx is None or mx <= 2e-6 or not (q.get("DRMA", 0) > 0 and q.get("ENNE", 0) > 0
                                                         and q.get("CRPR", 0) > 0 and q.get("DRMN", 0) > 0):
                        continue
                    mx = min(1.0, mx + 2e-6)
                    s_ = SHR_HEIR_NITR if (opt == "Nitr_Tot" and x == "HEIR") else o["shr"]
                    w = lvl * mx
                    wsum += w
                    # per activity, CAPRI's 2030 requirements per head and day (supply_model.gms REQSE_ / REQSN_,
                    # GHG_Mit_Cost_; line_nitr.gms)
                    acc["shr"] += w * s_
                    acc["cost"] += w * o["cost"] * q["DRMA"] * 365.0 / 1000.0 * s_      # per head and year
                    if opt == "Nitr_Tot":
                        acc["crpr"] += w * -q["DRMA"] * 0.0154 * s_ * 100.0 / q["CRPR"]
                    else:
                        fm = q["DRMA"] * s_ / tot_fat                   # kg linseed (fresh matter) per head and day
                        acc["ener"] += w * -fm * ooil["ENNE"] / q["ENNE"]
                        acc["crpr"] += w * -fm * ooil["CRPR"] / q["CRPR"]
                        acc["drmn"] += w * -fm * ooil["DRMA"] / q["DRMN"]
                        if abs(q.get("DRMX", 0.0)) > 0:
                            acc["drmx"] += w * -fm * ooil["DRMA"] / abs(q["DRMX"])
                if wsum <= 0 or wall <= 0:
                    nskip += 1
                    continue
                shr = acc["shr"] / wsum
                d = dict(region=reg, animal=an, option=opt, tech_param="ghgTechLineNitr", param_switch=1,
                         elig_share=wsum / wall, d_milk_rel=0.0, d_ener_rel=acc["ener"] / wsum,
                         d_crpr_rel=acc["crpr"] / wsum, d_drmn_rel=acc["drmn"] / wsum, d_drmx_rel=acc["drmx"] / wsum,
                         d_mann_rel=0.0, cost_floor=0.0, cost_per_unit=acc["cost"] / wsum,
                         relsubs0=0.05, relsubs1=1.2, gamma_floor=0.1,
                         ch4ent_rel=o["ch4"] * shr, shr_of_dm=shr, dm_intake=dmi)
                rows.append(d)
    rows += nop_rows(mr, to_c8, L, rations, R, places)
    out = pd.DataFrame(rows)
    # CAPRI's cost-saving drop between its ini and max calibration runs (line_nitr.gms l. 289-332 with breeding.gms's
    # formula), EUR per model head adopting (ghgTechLineNitr a switch)
    import sys as _sys; _sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from _capri_costsavings import costsaving_drop
    ds = {o_: costsaving_drop(MAP, o_) for o_ in OPT}
    ds["3NOP_Tot"] = costsaving_drop(NOP_MAP, "3NOP_tot")
    out["dsav"] = [ds[r.option].get((r.region, r.animal), float("nan")) for r in out.itertuples()]
    out.to_csv(M / "supplement_effects.csv", index=False)
    g = out.groupby(["option", "animal"]).agg(n=("region", "size"), elig=("elig_share", "median"),
                                             ener=("d_ener_rel", "median"), crpr=("d_crpr_rel", "median"),
                                             cost=("cost_per_unit", "median"), ch4=("ch4ent_rel", "median"))
    print(f"supplement_effects.csv: {len(out)} region-animal-options ({nskip} without CAPRI maximum shares)")
    print(g.round(3).to_string())


if __name__ == "__main__":
    main()

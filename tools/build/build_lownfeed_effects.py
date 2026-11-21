"""CAPRI's low-nitrogen feeding option per model region and animal (envind/low_n_feed.gms; the port of CAPRI's feed options).

star 3.0's Green Deal reference technology file sets ghgTechLowNFeed = 1 (pol_input/greendeal/refpol_endotech_all_sup.gms,
as the JRC121368-era ecampa references): the option exists for every animal whose ration carries more crude protein
than the requirement function asks (p_animReq > p_animReqLit). CAPRI's definitions (low_n_feed.gms):

  excess  e_C = p_animReq / p_animReqLit - 1 for crude protein (CRPR), e_E the same for energy (ENNE), at the
          simulation year: CAPRI's simulation loads p_animReq, p_animReqLit and p_animExcrProtCorrFact from its
          sim_ini file (capmod/load_sim_ini_gdx.gms l. 100-111; capmod.gms l. 1054-1076 leaves its own requirement
          block deactivated, "$iftheni.alwaysDeactivated %baseline%==offtext"), where create_sim_ini_gdx.gms
          (l. 423-427) wrote them after the 2030 baseline's feed calibration (baseline/adjust.gms, the fedtrm files):
          sim_ini_21730's p_animReq, p_animReqLit (CRPR, ENNE) and p_animExcrProtCorrFact (KNOWN_ISSUES K194)
  cut     p_LowNFeedCut = 0.15 x max(0, e_C) / (1 + 0.5 max(0, e_E)) x ghgTechLowNFeed      (EU regions, e_C > 0;
          l. 88-96)
  effects crude protein (and lysine) requirement x (1 - cut x share); manure N x (1 - cut x (MANN + CRPR_EXPT) /
          MANN x share) (the protein not fed is not excreted; CRPR_EXPT = N leaving in products; l. 98-120), with
          the simulation year's DATA: sim_ini_21730's MANN (at BAS, which CAPRI's 2030 MANN equals, K179) and
          CRPR_EXPT at Y
  cost    costParLin = feed cost per place and year x 0.06 x cut / max(0.001, p_animExcrProtCorrFact - 1 - cut)
          (l. 129-142), p_animExcrProtCorrFact sim_ini_21730's (the 2030 trend and feed calibration in it)
  shares  MaxShare: monogastrics 1, dairy cows 1 - grazing share, other ruminants 0.5 x (1 - grazing share), capped
          at the level of CAPRI's max calibration run (+2e-6) - taken directly from that run
          (costsavings_max, capri_costsavings_2030.parquet); IniShare 0; relSubs0 0.2, relSubs1 0.8;
          pmpParsqr = max(0.05 |c|, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) / (MaxShare - IniShare)
          (costsaving0 - costsaving1 from CAPRI's two runs, column dsav per model head: tools/lib/_capri_costsavings.py)

Model animals aggregate CAPRI's activities (weights: CAPRI's 2030 levels, sim_ini_21730 DATA LEVL at Y):
DCOW = DCOL + DCOH, BCOW = SCOW, BULL = BULL + BULH, HFRS = HEIL + HEIH + HEIR, CALV = CAMF + CAFF + CAMR + CAFR,
PIGF, PIGS = SOWS, BROI = POUF, LAYS = HENS, SHGM, SHGF as CAPRI. Feed cost per head from the model's own base
rations (as genet_eff; not CAPRI's 2030 DATA feed x UVAG: a difference kept, K194).

Until 21 November 2026 the excess was CAPREG's 2017 correction factors (reqrel, p_animReqCorrFac1) with the trend
0.998^13 on the excretion factor, and MANN, CRPR_EXPT and the weights res_17's 2017 data (K194).

Output: capri_data/2017/abatement/mitigation/lownfeed_effects.csv, the schema of genetics_effects.csv (option
lowNFeed, tech_param ghgTechLowNFeed; d_crpr_rel and d_mann_rel per unit of the parameter; cost_per_unit = the cost
at ghgTechLowNFeed = 1, star 3.0's value - the cost is not linear in the parameter: REGISTERED). Also writes
capri_data/sources/intermediate/envind/res17_mann_crpr_expt.parquet (res_17's LEVL, MANN, CRPR_EXPT) for
build_supplement_effects.py.

    python tools/build/build_lownfeed_effects.py [--dump-dir capri_sources/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re
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
SRC = ROOT / "capri_data" / "sources" / "intermediate" / "envind"
LEV = SRC / "res17_mann_crpr_expt.parquet"            # res_17's data, for build_supplement_effects.py
SIMINI = REFERENCE / "simini" / "simini_21730"          # tools/build/build_simini_reference.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
MAP = {a: _MC.ANIMALS[a] for a in ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "PIGF", "PIGS", "BROI", "LAYS", "SHGM", "SHGF")}
CAPRI_ACTS = sorted({x for v in MAP.values() for x in v})


def extract(dump_dir: Path):
    """res_17's LEVL, MANN and CRPR_EXPT of the animals (build_supplement_effects.py's weights and data)."""
    files = glob.glob(str(dump_dir / "res_17*.txt"))
    if files:
        pat = re.compile(r"^'([A-Z0-9]{8})'\.'(" + "|".join(CAPRI_ACTS) + r")'\.'(LEVL|MANN|CRPR_EXPT)'\.'Y'\s+([-\d.Ee+]+)")
        rows = []
        for f in files:
            for line in open(f, errors="ignore"):
                m = pat.match(line)
                if m:
                    rows.append(dict(region=m.group(1), activity=m.group(2), item=m.group(3), value=float(m.group(4))))
        write_source(pd.DataFrame(rows).drop_duplicates(["region", "activity", "item"]), LEV, index=False)
        print(f"res_17 LEVL, MANN, CRPR_EXPT: {len(rows)} rows -> {LEV.relative_to(ROOT)}")


def _simini(symbol: str) -> dict:
    """sim_ini_21730's parameter as {(d0, ..., dn): value} (tools/build/build_simini_reference.py; Eps as 0)."""
    path = SIMINI / f"{symbol}.csv.gz"
    assert path.is_file(), (f"{path} missing: python tools/build/build_simini_reference.py --src sim_ini_21730.gdx "
                            "--tag simini_21730")
    t = pd.read_csv(path, dtype=str, keep_default_na=False)
    dims = [c for c in t.columns if c.startswith("d")]
    return {tuple(r[:-1]): float(r[-1]) for r in t[dims + ["value"]].itertuples(index=False)}


def lowNFeed_cut(animReq_CRPR, animReqLit_CRPR, animReq_ENNE, animReqLit_ENNE, ghgTechLowNFeed=1.0):
    """low_n_feed.gms l. 88-96:

    p_LowNFeedCUT(RU,MAACT,A)  $ (p_animReqLit(RU,MAACT,A,"CRPR") and p_animReqLit(RU,MAACT,A,"ENNE") and p_animReq(RU,MAACT,A,"CRPR")
    $ifi not %LowNFeedInAllRmssup%==on and (not SUM(RU_MS(RU,MSnoEU),1))
                                       and (p_animReqLit(RU,MAACT,A,"CRPR") LT p_animReq(RU,MAACT,A,"CRPR")))
          = (0.15 + (0.15-0.15) $ SUM(MAP_RR(NEWMS,RU),1))
                         * MAX(0,p_animReq(RU,MAACT,A,"CRPR")/p_animReqLit(RU,MAACT,A,"CRPR")-1)
            / (1+ 0.5 * MAX(0,p_animReq(RU,MAACT,A,"ENNE")/p_animReqLit(RU,MAACT,A,"ENNE")-1) )
                         * p_ghgTechLowNFeed

    None where the option does not exist (the EU condition is the caller's)."""
    if not (animReqLit_CRPR and animReqLit_ENNE and animReq_CRPR) or not animReqLit_CRPR < animReq_CRPR:
        return None
    eC = max(0.0, animReq_CRPR / animReqLit_CRPR - 1.0)
    eE = max(0.0, animReq_ENNE / animReqLit_ENNE - 1.0)
    return 0.15 * eC / (1.0 + 0.5 * eE) * ghgTechLowNFeed


def lowNFeed_MANN(p_ghgMiti_CRPR, MANN, CRPR_EXPT):
    """low_n_feed.gms l. 117-120:

    p_ghgMiti(RU,MAACT,"lowNFeed","othImpact","MANN") $ DATA(RU,MAACT,"MANN","Y")
          = p_ghgMiti(RU,MAACT,"lowNFeed","othImpact","CRPR")
          * (DATA(RU,MAACT,"MANN","Y") + DATA(RU,MAACT,"CRPR_EXPT","Y"))
          / DATA(RU,MAACT,"MANN","Y") ;"""
    return p_ghgMiti_CRPR * (MANN + CRPR_EXPT) / MANN


def lowNFeed_costParLin_factor(p_ghgMiti_CRPR, p_animExcrProtCorrFact, p_mitiEffFac=1.0):
    """low_n_feed.gms l. 129-142, the factor on the feed cost per place and year (the cost is that cost times it):

    p_ghgMiti(RU,MAACT,"lowNFeed","N2Oexcr","costParLin") $ SUM(RU_MS(RU,MS),DATA(MS,MAACT,"DAYS","Y"))
          = MAX(0.,SUM(FEED,DATA(RU,MAACT,FEED,"Y")
                           *SUM(RU_MS(RU,MS),DATA(MS,"UVAG",FEED,"Y")/(DATA(MS,MAACT,"DAYS","Y")/365)))*0.001)
           *   .06
           * (-p_ghgMiti(RU,MAACT,"lowNFeed","othImpact","CRPR"))
           / p_mitiEffFac("lowNFeed","%SIMY%")
           / MAX(.001,p_animExcrProtCorrFact(RU,MAACT,"T","Y")-1
                     + p_ghgMiti(RU,MAACT,"lowNFeed","othImpact","CRPR")
                     / p_mitiEffFac("lowNFeed","%SIMY%") )"""
    return 0.06 * (-p_ghgMiti_CRPR) / p_mitiEffFac / max(0.001, p_animExcrProtCorrFact - 1.0 + p_ghgMiti_CRPR / p_mitiEffFac)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    a = ap.parse_args()
    extract(a.dump_dir)
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    # CAPRI's simulation-year inputs of low_n_feed.gms, from sim_ini_21730 (the docstring)
    R, L = _simini("p_animReq"), _simini("p_animReqLit")
    X = _simini("p_animExcrProtCorrFact")
    DATA = _simini("DATA")
    acts = set(CAPRI_ACTS)
    REQ = {(k[0], k[1], k[3]): v for k, v in R.items() if k[1] in acts and k[2] == "T" and k[3] in ("CRPR", "ENNE")}
    LIT = {(k[0], k[1], k[3]): v for k, v in L.items() if k[1] in acts and k[2] == "T" and k[3] in ("CRPR", "ENNE")}
    EXC = {(k[0], k[1]): v for k, v in X.items() if k[1] in acts and k[2] == "T" and k[3] == "Y"}
    D = {}
    for (r, c, i, t), v in DATA.items():
        if c in acts and ((i in ("LEVL", "CRPR_EXPT") and t == "Y") or (i == "MANN" and t == "BAS")):
            D[(r, c, i)] = v
    cs = read_source(ROOT / "capri_data" / "sources" / "intermediate" / "ghgtech" / "capri_costsavings_2030.parquet")
    cs = cs[cs.technology.str.lower() == "lownfeed"]
    MX = {(r.region, r.activity): float(r.level) for r in cs[cs.run == "max"].itertuples() if pd.notna(r.level)}
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.nested_tables import read_feed_rations
    rations = read_feed_rations(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv")
    NON_EU = ("AL", "BA", "CS", "KO", "MK", "MO", "TU", "UK", "NO")        # low_n_feed.gms l. 89: not MSnoEU

    def get(d, keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    rows, nskip = [], 0
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg, ms)
        if ms[:2] in NON_EU:
            continue
        rr = rations.get(reg) or {}
        for an, acts_m in MAP.items():
            num = defaultdict(float)
            w = 0.0
            for x in acts_m:
                lvl = get(D, [(c8, x, "LEVL"), (ms, x, "LEVL")]) or 0.0
                keys = [(c8, x), (ms, x)]
                cut = lowNFeed_cut(get(REQ, [k + ("CRPR",) for k in keys]), get(LIT, [k + ("CRPR",) for k in keys]),
                                   get(REQ, [k + ("ENNE",) for k in keys]), get(LIT, [k + ("ENNE",) for k in keys]))
                mann = get(D, [(c8, x, "MANN"), (ms, x, "MANN")])
                expt = get(D, [(c8, x, "CRPR_EXPT"), (ms, x, "CRPR_EXPT")]) or 0.0
                excr = get(EXC, keys)
                mx = get(MX, keys)
                if lvl <= 0 or not cut or not mann or mann <= 0 or excr is None or mx is None:
                    continue
                w += lvl
                num["cut"] += lvl * cut
                num["mann"] += lvl * -lowNFeed_MANN(-cut, mann, expt)
                num["costfac"] += lvl * lowNFeed_costParLin_factor(-cut, excr)
                num["elig"] += lvl * min(1.0, mx + 2e-6)
            ra = rr.get(an)
            if w <= 0 or not ra:
                nskip += 1
                continue
            fc = sum(float(ra["ration"][f]) * float(ra["price"][f]) for f in ra["ration"])
            rows.append(dict(region=reg, animal=an, option="lowNFeed", tech_param="ghgTechLowNFeed",
                             elig_share=num["elig"] / w, d_milk_rel=0.0, d_ener_rel=0.0,
                             d_crpr_rel=-num["cut"] / w, d_drmn_rel=0.0, d_drmx_rel=0.0,
                             d_mann_rel=-num["mann"] / w, cost_floor=0.0, cost_per_unit=fc * num["costfac"] / w,
                             relsubs0=0.2, relsubs1=0.8, gamma_floor=0.05))
    out = pd.DataFrame(rows)
    # CAPRI's cost-saving drop between its ini and max calibration runs (low_n_feed.gms l. 265-272), EUR per model
    # head adopting per unit of the parameter (the runs are at the 2030 reference's ghgTechLowNFeed 1)
    import sys as _sys; _sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from _capri_costsavings import costsaving_drop
    ds = costsaving_drop(MAP, "lowNFeed")
    out["dsav"] = [ds.get((r.region, r.animal), float("nan")) for r in out.itertuples()]
    out.to_csv(M / "lownfeed_effects.csv", index=False)
    g = out.groupby("animal").agg(n=("region", "size"), crpr=("d_crpr_rel", "median"), mann=("d_mann_rel", "median"),
                                  elig=("elig_share", "median"), cost=("cost_per_unit", "median"))
    print(f"lownfeed_effects.csv: {len(out)} region-animals ({nskip} without data)")
    print(g.round(3).to_string())


if __name__ == "__main__":
    main()

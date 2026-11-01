"""CAPRI's low-nitrogen feeding option per model region and animal (envind/low_n_feed.gms; Sprint 9g).

star 3.0's Green Deal reference technology file sets ghgTechLowNFeed = 1 (pol_input/greendeal/refpol_endotech_all_sup.gms,
as the JRC121368-era ecampa references): the option exists for every animal whose ration carries more crude protein
than the requirement function asks (p_animReq > p_animReqLit). CAPRI's definitions (low_n_feed.gms):

  excess  e_C = p_animReq / p_animReqLit - 1 for crude protein (CRPR), e_E the same for energy (ENNE)
          = CAPRI's requirement correction factors p_animReqCorrFac (capmod/load_feed.gms loads them from the reqrel
            results as p_animReqCorrFac1; capri_data/sources/envind/anim_req_corr_2017.csv)
  cut     p_LowNFeedCut = 0.15 x max(0, e_C) / (1 + 0.5 max(0, e_E)) x ghgTechLowNFeed      (EU regions, e_C > 0)
  effects crude protein (and lysine) requirement x (1 - cut x share); manure N x (1 - cut x (MANN + CRPR_EXPT) /
          MANN x share) (the protein not fed is not excreted; CRPR_EXPT = N leaving in products)
  cost    costParLin = feed cost per place and year x 0.06 x cut / max(0.001, p_animExcrProtCorrFact - 1 - cut),
          p_animExcrProtCorrFact = (1 + e_C) x 0.998^(SIMY - BAS) (capmod/def_requirements.gms)
  shares  MaxShare: monogastrics 1, dairy cows 1 - grazing share, other ruminants 0.5 x (1 - grazing share), capped
          at the level of CAPRI's max calibration run (+2e-6) - taken directly from that run
          (costsavings_max, capri_costsavings_2030.csv); IniShare 0; relSubs0 0.2, relSubs1 0.8;
          pmpParsqr = max(0.05 |c|, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) / (MaxShare - IniShare)
          (costsaving0 - costsaving1 from CAPRI's two runs, column dsav per model head: tools/lib/_capri_costsavings.py)

Model animals aggregate CAPRI's activities (weights: CAPRI's 2017 levels, res_17): DCOW = DCOL + DCOH, BCOW = SCOW,
BULL = BULL + BULH, HFRS = HEIL + HEIH + HEIR, CALV = CAMF + CAFF + CAMR + CAFR, PIGF, PIGS = SOWS, BROI = POUF,
LAYS = HENS, SHGM, SHGF as CAPRI. Feed cost per head from the model's own base rations (as genet_eff).

Output: capri_data/2017/abatement/mitigation/lownfeed_effects.csv, the schema of genetics_effects.csv (option
lowNFeed, tech_param ghgTechLowNFeed; d_crpr_rel and d_mann_rel per unit of the parameter; cost_per_unit = the cost
at ghgTechLowNFeed = 1, star 3.0's value - the cost is not linear in the parameter: REGISTERED)

    python tools/build/build_lownfeed_effects.py [--anim-req /mnt/user-data/uploads/animReq_SK.zip]
                                           [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, io, json, re, zipfile
from collections import defaultdict
import sys
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
SRC = ROOT / "capri_data" / "sources" / "envind"
CORR = SRC / "anim_req_corr_2017.csv"
LEV = SRC / "res17_mann_crpr_expt.csv"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import _model_codes as _MC  # noqa: E402  the model's activities and their CAPRI activities (codes/model_activities.csv)
MAP = {a: _MC.ANIMALS[a] for a in ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "PIGF", "PIGS", "BROI", "LAYS", "SHGM", "SHGF")}
CAPRI_ACTS = sorted({x for v in MAP.values() for x in v})
YEARS = 2030 - 2017


def extract(zpath: Path, dump_dir: Path):
    if zpath.exists():
        pat = re.compile(r"^'([A-Z0-9]{8})'\.'([A-Z]+)'\.'T'\.'(CRPR|ENNE)'\s+([-\d.Ee+]+)")
        rows = []
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():
                if not n.startswith("animReq_"):
                    continue
                for line in io.TextIOWrapper(z.open(n), errors="ignore"):
                    m = pat.match(line)
                    if m and m.group(2) in CAPRI_ACTS:
                        rows.append(dict(region=m.group(1), activity=m.group(2), item=m.group(3), value=float(m.group(4))))
        SRC.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(CORR, index=False)
        print(f"p_animReqCorrFac1: {len(rows)} rows -> {CORR.relative_to(ROOT)}")
    files = glob.glob(str(dump_dir / "res_17*.txt"))
    if files:
        pat = re.compile(r"^'([A-Z0-9]{8})'\.'(" + "|".join(CAPRI_ACTS) + r")'\.'(LEVL|MANN|CRPR_EXPT)'\.'Y'\s+([-\d.Ee+]+)")
        rows = []
        for f in files:
            for line in open(f, errors="ignore"):
                m = pat.match(line)
                if m:
                    rows.append(dict(region=m.group(1), activity=m.group(2), item=m.group(3), value=float(m.group(4))))
        pd.DataFrame(rows).drop_duplicates(["region", "activity", "item"]).to_csv(LEV, index=False)
        print(f"res_17 LEVL, MANN, CRPR_EXPT: {len(rows)} rows -> {LEV.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anim-req", type=Path, default=Path("/mnt/user-data/uploads/animReq_SK.zip"))
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    a = ap.parse_args()
    extract(a.anim_req, a.dump_dir)
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    cr = _read_csv(CORR)
    C = {(r.region, r.activity, r.item): float(r.value) for r in cr.itertuples()}
    lv = _read_csv(LEV)
    D = {(r.region, r.activity, r.item): float(r.value) for r in lv.itertuples()}
    cs = _read_csv(ROOT / "capri_data" / "sources" / "ghgtech" / "capri_costsavings_2030.csv")
    cs = cs[cs.technology.str.lower() == "lownfeed"]
    MX = {(r.region, r.activity): float(r.level) for r in cs[cs.run == "max"].itertuples() if pd.notna(r.level)}
    rations = json.load(open(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.json"))["regions"]
    eu = {r for r in {k[0] for k in C} if r[:2] not in ("AL", "BA", "CS", "KO", "MK", "MO", "TU", "UK", "NO")}

    def get(d, keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    rows, nskip = [], 0
    for reg in mr.model_regions():
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg, ms)
        if ms not in eu:
            continue
        rr = rations.get(reg) or {}
        for an, acts in MAP.items():
            num = defaultdict(float)
            w = 0.0
            for x in acts:
                lvl = get(D, [(c8, x, "LEVL"), (ms, x, "LEVL")]) or 0.0
                eC = get(C, [(c8, x, "CRPR"), (ms, x, "CRPR")])
                eE = get(C, [(c8, x, "ENNE"), (ms, x, "ENNE")]) or 0.0
                mann = get(D, [(c8, x, "MANN"), (ms, x, "MANN")])
                expt = get(D, [(c8, x, "CRPR_EXPT"), (ms, x, "CRPR_EXPT")]) or 0.0
                mx = get(MX, [(c8, x), (ms, x)])
                if lvl <= 0 or eC is None or eC <= 0 or not mann or mann <= 0 or mx is None:
                    continue
                cut = 0.15 * eC / (1.0 + 0.5 * max(0.0, eE))
                excr = (1.0 + eC) * 0.998 ** YEARS
                w += lvl
                num["cut"] += lvl * cut
                num["mann"] += lvl * cut * (mann + expt) / mann
                num["costfac"] += lvl * 0.06 * cut / max(0.001, excr - 1.0 - cut)
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

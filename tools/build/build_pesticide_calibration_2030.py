"""CAPRI's pesticide calibration at the simulation year 2030 (supply/cal_pesti.gms, 5_aggregates stage; the port
capri_mod/supply/equations/cal_pesti.py): per region, crop and technology the yield's value without damage and the
marginal fertiliser cost of the avoided yield loss; per aggregate the application per ha, the price-damage ratio and,
with --calibrate, the damage function's terms and the yield factor without damage.

Inputs, each CAPRI's own (claude/pesticide_p1_audit_2026-11-27.md):
  the applications and their unit values   capri_data/2017/supply/pesticides_2017.csv, pesticide_prices_2017.csv
                                           (CAPREG's base). The applications of the simulation year by
                                           capmod/define_inputs.gms l. 107-112 (the yield growth, the aggregates with
                                           PLAP's demand factor, inputs/yieldIY.gms l. 98-101, the input-saving
                                           progress). The price DATA(RUNR, "UVAG", pestoAgg, "Y") is the member
                                           state's base value x CAPRI's inflation (inflation_and_trend_interpolation.gms
                                           l. 71-72; the regions take it by baseline/fedtrm_prep.gms l. 94-95)
  the maximum damage                       capri_data/2017/supply/pesticide_max_damage_2017.csv (CAPREG's p_pestPar)
  yields, the fertilisers' prices          sim_ini_21730's DATA at "Y" (the reference export; kept extract
                                           capri_data/sources/raw/capri/results/sim_ini_21730/pesticide_cal_items.parquet);
                                           the fertilisers' member-state UVAG x CAPRI's inflation to 2030
                                           (inflation_and_trend_interpolation.gms l. 71-72)
  the outputs' prices                      as the baseline has them when its supply calibration runs (prices()): a
                                           market output's base unit value moved by its market's calibrated producer
                                           price (arm/set_prices.gms with "BAS", arm/prep_market.gms l. 1248-1250;
                                           sim_ini_21730's PPRI at "BAS" and "CAL"), any other output's x CAPRI's
                                           inflation; the regions' by baseline/fedtrm_prep.gms l. 94-101. Not
                                           sim_ini_21730's UVAG at "Y", which are a simulation's start prices
  the on-farm share's items                sim_ini_21730's DATA at "TRD", the trend values the baseline's "CUR" starts
                                           from (supply/def_start_value_and_data.gms l. 29-38; the seed bought, SEDM,
                                           has no value at "Y")
  the technology factors                   capri_data/sources/intermediate/technology/techn_fact_2030.parquet; the
                                           nutrients' by fert/fertned.gms (capri_mod/supply/equations/fertned.py); the
                                           aggregates' the general inputs' +-0.25 (intens/techf.gms l. 92-93: with the
                                           module on PACT_TO_I(PACT, pesModDis) = PACT_TO_I(PACT, "PLAP"), sets.gms
                                           l. 5365-5368)
  DATA(crop, FNUT | FOUT, "Y")             fert/fertned.gms rerun on the year's data (capri_mod/fert/npk.py
                                           fertned_at_yields; capri_crop_fertned_parts_2030.csv, with the straw's
                                           losses and production at "TRD", as the baseline has them), the fixation rate
                                           capri_crop_n_coefs_2030.csv, the deposition n_deposition_regional.csv
  the fertiliser calibration's levels      v_cropNutNeedMultFact per technology (sim_ini_21730; kept extract
                                           crop_nut_need_mult_fact_techn.parquet); the residues' availability net of the
                                           N2O loss and the mineral fertiliser's efficiency (npk_region_2030.csv
                                           cres_avail, mine_eff: CAPRI's 2030 reference)
  p_nitrFact(RUNR, "ALL", "DEFR")          CAPRI's soil factor of the N need (fert/fertpar.gms l. 246, from CAPREG's
                                           fert_out, which is not at hand): recovered from CAPRI's 2030 reference, the
                                           reported need of each crop group over its crops' need (NUTNED_'s left side;
                                           tools/build/build_npk_balance_2030.py add_share_parts), N over P2O5 in the
                                           same group; the groups of a region agree within 2e-7 (defr())

Outputs (capri_data/baselines/capri_greendeal_ref/1730/supply/)
  pesticide_margins_2030.csv   region, activity, technology, no_damage_yld, marg_cost_nitf, marg_cost_phof,
                               marg_cost_potf, marg_cost_ferc (EUR per ha), negative_margin
  pesticide_par_2030.csv       region, activity, item, technology, appl_per_ha (kg per ha), max_damage, uvag,
                               price_damage_ratio, slop_fudg, endogenous_start; with --calibrate also slop_lin,
                               slop_expo, expon, endogenous, power_infes, cur_damage, CAPRI's test of the
                               calibration (pesti_test(): appl_cal, appl_choke) and, on the item YILD,
                               no_damage_fac and yld_pest_fac_cal

    python tools/build/build_pesticide_calibration_2030.py [--calibrate] [--regions DK000000,...]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
sys.path.insert(0, str(ROOT))
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)

SIMINI = REFERENCE / "simini" / "simini_21730"
RAW = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730"
EXTRACT, MULT = RAW / "pesticide_cal_items.parquet", RAW / "crop_nut_need_mult_fact_techn.parquet"
BASE = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730"
OUT = BASE / "supply"
FNUT = {"NITF": "N", "PHOF": "P", "POTF": "K"}
FOUT = {"NITF": "MANN", "PHOF": "MANP", "POTF": "MANK"}
BALANCE = ("GROF", "SEDF", "SEDM", "LOSF")
#: the technology factor of an input bought (intens/techf.gms l. 92-93), the pesticide aggregates' with the module on
TECHF_INPUT = {"T1": 0.25, "T2": -0.25, "T": 0.0}
_read = lambda p, **kw: pd.read_csv(p, keep_default_na=False, float_precision="round_trip", low_memory=False, **kw)  # noqa: E731


def sets() -> dict:
    from capri_mod.data.definitions import capri_pairs, capri_set
    oms = set(_read(REFERENCE / "sets" / "simini_21730" / "OMS.csv").d0) if (REFERENCE / "sets").exists() else None
    if oms is not None:
        write_source(pd.DataFrame({"code": sorted(oms)}), RAW / "oms.parquet", index=False)
    oms = set(read_source(RAW / "oms.parquet", keep_default_na=False).code)
    mcact = tuple(capri_set("MCACT"))
    p2o = defaultdict(list)
    for a, o in capri_pairs("PACT_TO_O"):
        if a in mcact and o in oms:
            p2o[a].append(o)
    p2y = defaultdict(list)
    for a, o in capri_pairs("PACT_TO_Y"):
        if a in mcact:
            p2y[a].append(o)
    return {"PACT_TO_Y": dict(p2y), "CAP_TO_TRD": dict(capri_pairs("CAP_TO_TRD")), "MARR": set(capri_set("MARR")),
            "MCACT": mcact, "OMS": oms, "PACT_TO_O": dict(p2o), "aggs": tuple(capri_set("pesTSAgg")),
            "FODDO": set(capri_set("FODDO"))}


def items(S: dict) -> pd.DataFrame:
    """sim_ini_21730's DATA at "Y" for the calibration (region, col, row, value): the crops' levels and outputs, the
    outputs' and the fertilisers' unit values, the outputs' balance items of the on-farm share; written to the kept
    extract where the reference export is at hand, read from it otherwise."""
    f = SIMINI / "DATA.csv.gz"
    if f.exists():
        t = _read(f, dtype={"d0": str, "d1": str, "d2": str, "d3": str})
        y = t.d3 == "Y"
        crop = y & t.d1.isin(S["MCACT"]) & (t.d2.isin(S["OMS"]) | (t.d2 == "LEVL"))
        uvag = y & (t.d1 == "UVAG") & (t.d2.isin(S["OMS"]) | t.d2.isin(tuple(FNUT)))
        bal = y & t.d1.isin(BALANCE) & t.d2.isin(S["OMS"])
        # the outputs' base year unit values, the markets' producer prices at the base and at the calibration point, and
        # the rice items of the paddy's price (prices(): arm/set_prices.gms, fedtrm_prep.gms l. 94-101)
        fod = (t.d3 == "BAS") & (t.d1 == "UVAG") & (t.d2.isin(S["FODDO"]) | t.d2.isin(S["OMS"]))
        fod = fod | ((t.d1 == "PPRI") & t.d3.isin(("BAS", "CAL")))
        fod = fod | ((t.d3 == "BAS") & (((t.d1 == "MAPR") & (t.d2 == "RICE")) | ((t.d1 == "GROF") & (t.d2 == "PARI"))))
        # the on-farm share's items at the trend
        fod = fod | ((t.d3 == "TRD") & t.d1.isin(BALANCE) & t.d2.isin(S["OMS"]))
        # the crops' base levels and the main outputs' yields of both years (market outputs or not), for the yield growth (define_inputs.gms l. 80-82)
        y2 = {(a_, o) for a_, os_ in S["PACT_TO_Y"].items() for o in os_}
        bas = t.d3.isin(("BAS", "Y")) & t.d1.isin(S["MCACT"])
        bas = bas & ((t.d2 == "LEVL") | pd.Series([k in y2 for k in zip(t.d1, t.d2)], index=t.index))
        t = t[crop | uvag | bal | fod | bas][["d0", "d1", "d2", "d3", "value"]]
        t.columns = ["region", "col", "row", "year", "value"]
        t = t.sort_values(["region", "col", "row", "year"], ignore_index=True)
        RAW.mkdir(parents=True, exist_ok=True)
        write_source(t, EXTRACT, index=False)
    return read_source(EXTRACT, keep_default_na=False, dtype={"region": str, "col": str, "row": str, "year": str})


def mult_fact() -> dict:
    """{(region, FNUT, technology): v_cropNutNeedMultFact.l} of sim_ini_21730, kept as an extract."""
    f = SIMINI / "v_cropNutNeedMultFact.csv.gz"
    if f.exists():
        t = _read(f)[["d0", "d1", "d2", "level"]]
        t.columns = ["region", "fnut", "technology", "mult"]
        write_source(t.sort_values(["region", "fnut", "technology"], ignore_index=True), MULT, index=False)
    t = read_source(MULT, keep_default_na=False)
    return {(r, f_, a): float(m) for r, f_, a, m in zip(t.region, t.fnut, t.technology, t["mult"])}


def defr() -> dict:
    """{region: p_nitrFact(region, "ALL", "DEFR")} from CAPRI's 2030 reference (the module's docstring): per crop group
    the factor K of add_share_parts for N over the same for P2O5 (the technologies' mix cancels: the nutrients share the
    technology factors, fert/fertned.gms l. 339-340), the median over the region's groups; the largest spread between
    a region's groups is returned too."""
    import build_npk_balance_2030 as B
    src = read_source(B.SRC, keep_default_na=False)
    v = {(r.region, r.item, r.row, r.col): r.value for r in src.itertuples(index=False)}
    nf = B.need_factors()
    fp_ = _read(B.ENV / "capri_crop_fertned_parts_2030.csv", usecols=["capri_region", "crop", "o_hp"])
    with_data = {(r_, c_) for r_, c_, o_ in zip(fp_.capri_region, fp_.crop, fp_.o_hp) if o_ > 0}
    out, spread = {}, 0.0
    for r in sorted({r for r in src.region if len(r) == 8}):
        lev = {c: v.get((r, "", c, "LEVL"), 0.0) for c in B.ELEM}
        lev = {c: x for c, x in lev.items() if x > 0}
        K = {}
        for col in ("NITF", "PHOF"):
            if (r, col) not in nf:
                continue
            f = lambda item, c: v.get((r, item, c, col), 0.0)  # noqa: E731
            for g_ in {B.ngrp(c) for c in lev}:
                cs_ = [c for c in lev if B.ngrp(c) == g_]
                own_ = {c: lev[c] * v.get((r, "", c, col), 0.0) for c in cs_ if (r, c) in with_data}
                ap = B.add_share_parts(sum(f("nutNed_lhs", c) for c in cs_), sum(f("nutNed_retention", c) for c in cs_),
                                       sum(f("nutNed_biofix", c) for c in cs_),
                                       sum(w / B.NUTNED_sqrtTerm(c) for c, w in own_.items()), sum(own_.values()),
                                       sum(lev[c] for c in own_), *nf[(r, col)])
                if ap:
                    K[(g_, col)] = ap[0]
        # the groups whose technologies' mix is the calibration point's (every crop at T, or at T1 and T2 by halves:
        # K of P2O5 1 or 0.5 (sqrt(1.2) x 1.2 + sqrt(0.8) x 0.8)); a group mixing both kinds is left out
        mix = 0.5 * (np.sqrt(1.2) * 1.2 + np.sqrt(0.8) * 0.8)
        d = [K[(g_, "NITF")] / kp for (g_, col), kp in K.items()
             if col == "PHOF" and (g_, "NITF") in K and (abs(kp - 1.0) < 1e-6 or abs(kp - mix) < 1e-5)]
        if d:
            out[r] = float(np.median(d))
            spread = max(spread, (max(d) - min(d)) / out[r])
    return out, spread


def pesti_test(p: pd.DataFrame) -> pd.DataFrame:
    """CAPRI's test of the calibration (supply/cal_pesti.gms l. 517-561; capri_mod/supply/equations/pesti_test.py) on
    the calibrated cells: appl_cal, the applications the farmer chooses at the calibration point (CAPRI's
    ApplPerHaCal), appl_choke at the price that would end the use at the prior elasticity (ApplPerHa2), and on the
    item YILD yld_pest_fac_cal, the yield factor at appl_cal, which CAPRI flags where it is off 1 by more than 1e-4."""
    from capri_mod.supply.equations import pesti_test as PT
    p = p.copy()
    num = lambda c: pd.to_numeric(p[c], errors="coerce").fillna(0.0).to_numpy()  # noqa: E731
    cell = (p["item"] != "YILD").to_numpy()
    cols = [num(c) for c in ("appl_per_ha", "price_damage_ratio", "slop_lin", "slop_expo", "expon", "endogenous")]
    ti = PT.p_pestiEla_testincrease()
    cal = np.full(len(p), np.nan)
    choke = np.full(len(p), np.nan)
    for k in np.flatnonzero(cell):
        args = [c[k] for c in cols]
        cal[k], choke[k] = PT.m_pestiTest_cell(*args), PT.m_pestiTest_cell(*args, testincrease=ti)
    p["appl_cal"], p["appl_choke"] = cal, choke
    mxd, sl, se, ex = num("max_damage"), cols[2], cols[3], cols[4]
    by = defaultdict(list)
    for k in np.flatnonzero(cell):
        by[(p.region.iat[k], p.activity.iat[k], p.technology.iat[k])].append((mxd[k], cal[k], sl[k], se[k], ex[k]))
    ndf = num("no_damage_fac")
    y = np.full(len(p), np.nan)
    for k in np.flatnonzero(~cell):
        y[k] = PT.yldPestFac_(ndf[k], by.get((p.region.iat[k], p.activity.iat[k], p.technology.iat[k]), ()))
    p["yld_pest_fac_cal"] = y
    yy = y[~cell]
    endo = cell & (cols[5] > 0)
    print(f"the calibration's test: {int((~cell).sum())} crop-technologies, yield factor at the calibration point "
          f"within 1e-4 of 1 in {int((~np.array([PT.pestiCaliProblems_map(v) for v in yy])).sum())} "
          f"(largest difference {np.abs(yy - 1).max():.2e}); endogenous cells {int(endo.sum())}: application back "
          f"within 1e-4 in {int((np.abs(cal[endo] / cols[0][endo] - 1) <= 1e-4).sum())}, within 1% in "
          f"{int((np.abs(cal[endo] / cols[0][endo] - 1) <= 1e-2).sum())}; at the test price 0 in "
          f"{int((choke[endo] == 0).sum())}, median share of the observed application left "
          f"{np.median(choke[endo] / cols[0][endo]):.3f}")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-only", action="store_true", help="CAPRI's test on the calibrated file, rewritten with it")
    ap.add_argument("--calibrate", action="store_true", help="solve the power calibration too (IPOPT, a cell at a time)")
    ap.add_argument("--regions", default="")
    a = ap.parse_args()
    if a.test_only:
        pesti_test(_read(OUT / "pesticide_par_2030.csv")).to_csv(OUT / "pesticide_par_2030.csv", index=False,
                                                                 float_format="%.17g")
        return
    from capri_mod.coupling.equations.inflation_and_trend_interpolation import DATA_UVAG_IO_SIMY, p_inflationFactor
    from capri_mod.data.definitions import capri_ms
    from capri_mod.fert import npk
    from capri_mod.supply.equations import cal_pesti as CP
    from capri_mod.supply.equations import fertned as FN
    from capri_mod.supply.equations.pmp import p_onFarmShare
    from capri_mod.market.equations import set_prices as SP
    S = sets()
    t = items(S)
    D = {(r, c, w): float(x) for r, c, w, y_, x in zip(t.region, t.col, t.row, t.year, t.value) if y_ == "Y"}
    UVAG_BAS = {(r, w): float(x) for r, c, w, y_, x in zip(t.region, t.col, t.row, t.year, t.value)
                if y_ == "BAS" and c == "UVAG"}
    D_BAS = {(r, c, w): float(x) for r, c, w, y_, x in zip(t.region, t.col, t.row, t.year, t.value)
             if y_ == "BAS" and c != "UVAG"}
    D_TRD = {(r, c, w): float(x) for r, c, w, y_, x in zip(t.region, t.col, t.row, t.year, t.value) if y_ == "TRD"}
    PPRI_CAL = {(r, w): float(x) for r, c, w, y_, x in zip(t.region, t.col, t.row, t.year, t.value)
                if y_ == "CAL" and c == "PPRI"}
    # the applications of the simulation year (capmod/define_inputs.gms l. 107-112): the aggregates take PLAP's
    # demand factor with the module on (inputs/yieldIY.gms l. 98-101)
    from capri_mod.supply.equations.define_inputs import DATA_IY_Y, TF_I, TF_I_trend, p_yieldGrowth
    from _sources_io import source_records
    IDF = {r_["activity"]: float(r_["value"]) for r_ in source_records(
        ROOT / "capri_data" / "sources" / "raw" / "capri" / "gams" / "inputs" / "yieldIY_p_inputDemandFactor.parquet")
        if r_["input"] == "PLAP"}
    TFI = TF_I(TF_I_trend(0.005, 2030, 2017))

    def appl_Y(r, c, i):
        ys = [(D.get((r, c, o), 0.0), D_BAS.get((r, c, o), 0.0)) for o in S["PACT_TO_Y"].get(c, ())]
        G = p_yieldGrowth([y for y, _ in ys], [b for _, b in ys], D_BAS.get((r, c, "LEVL"), 0.0))
        return DATA_IY_Y(APP.get((r, c, i), 0.0), IDF.get(c, 1.0), G, TFI) or 0.0

    mf = mult_fact()
    DEFR, spread = defr()
    print(f"DEFR recovered for {len(DEFR)} regions; largest spread between a region's crop groups {spread:.1e}")
    assert spread < 1e-6, spread
    infl = p_inflationFactor(1.019, 2030, 2017)                 # CAPRI's p_infl (pol_input/agenda.gms l. 46)
    tf = pd.read_parquet(ROOT / "capri_data" / "sources" / "intermediate" / "technology" / "techn_fact_2030.parquet")
    TF = {(r, c, w, a_): float(x) for r, c, w, a_, x in zip(tf.region, tf.activity, tf.row, tf.tech, tf.value)}
    nr = _read(BASE / "environment" / "npk_region_2030.csv")
    nr = nr[nr.level == "ru"]
    NR = {(r, n): (float(me), float(ca)) for r, n, me, ca in zip(nr.capri_region, nr.nutrient, nr.mine_eff, nr.cres_avail)}
    nc = _read(BASE / "environment" / "capri_crop_n_coefs_2030.csv")
    BIOFIX = {(r, c): float(b or 0.0) for r, c, b in zip(nc.capri_region, nc.crop, nc.biofix_rate)}
    dep = _read(ROOT / "capri_data" / "2017" / "environment" / "n_deposition_regional.csv")
    DEP = dict(zip(dep.region, dep.deposition_kg_n_per_ha.astype(float)))
    pa = _read(ROOT / "capri_data" / "2017" / "supply" / "pesticides_2017.csv")
    APP = {(r, c, i): float(g) for r, c, i, g in zip(pa.region, pa.activity, pa["item"], pa.g_ha)}
    pp = _read(ROOT / "capri_data" / "2017" / "supply" / "pesticide_prices_2017.csv")
    PRICE = {(r, i): float(u) for r, i, u in zip(pp.region, pp["item"], pp.uvag) if u != ""}
    md = _read(ROOT / "capri_data" / "2017" / "supply" / "pesticide_max_damage_2017.csv")
    MAXD = {(r, c, i, a_): float(x) for r, c, i, a_, x in zip(md.region, md.activity, md["item"], md.technology,
                                                               md.max_damage)}
    from capri_mod.data.definitions import CAPRI_TO_MODEL_ACTIVITY as MODEL_CROP
    regions = sorted({r for (r, n) in NR} & {r for (r, c, w) in D if w == "LEVL"})
    if a.regions:
        regions = [r for r in regions if r in set(a.regions.split(","))]

    def on_farm(r, ms, o):
        """p_onFarmShare at the baseline's first step: the items at "CUR", which start from the trend values."""
        if o == "STRA":
            return p_onFarmShare(o, 0, 0, 0, 0, D_TRD.get((r, "LOSF", "STRA"), 0.0), D_TRD.get((r, "GROF", "STRA"), 0.0))
        return p_onFarmShare(o, D_TRD.get((ms, "SEDF", o), 0.0), D_TRD.get((ms, "SEDM", o), 0.0),
                             D_TRD.get((ms, "LOSF", o), 0.0), D_TRD.get((ms, "GROF", o), 0.0))

    def uvag_ms(ms, o):
        """DATA(MS, "UVAG", o, "Y") when the baseline's supply calibration runs: arm/set_prices.gms with "BAS" for the
        outputs that follow a market (capri_mod/market/equations/set_prices.py), the base value x inflation for any
        other (inflation_and_trend_interpolation.gms l. 71-72); None without a base value."""
        b = UVAG_BAS.get((ms, o), 0.0)
        pb = lambda x: (D_BAS.get((ms, "PPRI", x), 0.0), PPRI_CAL.get((ms, x), 0.0))  # noqa: E731  (the base, the calibrated)
        v = None
        if o == "DWHE":
            v = SP.DATA_UVAG_DWHE_Y(b, pb("WHEA")[1], pb("WHEA")[0])
        elif o == "PARI":
            v = SP.DATA_UVAG_PARI_Y(b, pb("RICE")[1], pb("RICE")[0], D_BAS.get((ms, "MAPR", "RICE"), 0.0),
                                    D_BAS.get((ms, "GROF", "PARI"), 0.0))
        elif o == "OLIV":
            v = SP.DATA_UVAG_OLIV_Y(b, pb("OLIO")[1], pb("OLIO")[0])
        elif o in S["MARR"] and o in S["CAP_TO_TRD"]:
            x = S["CAP_TO_TRD"][o]
            v = SP.DATA_UVAG_MARR_Y(b, pb(x)[1], pb(x)[0])
        if v is None:
            v = DATA_UVAG_IO_SIMY(b, infl) if b else None
        return v

    def uvag(r, ms, o):
        """DATA(RUNR, "UVAG", o, "Y") as the baseline has it when cal_pesti.gms runs (baseline/fedtrm_prep.gms
        l. 94-101, included by capmod/def_fert_and_requirements.gms): a fodder output's (FODDO) the region's base year
        value moved as its member state's, Y over BAS; any other output's its member state's (CAPRI's condition, the
        region's GROF above eps, holds for a crop with a level and a yield; the regions have no value of their own at
        "Y"). Without a base value of the member state: sim_ini_21730's value at "Y"."""
        m = uvag_ms(ms, o)
        if m is None:
            return D.get((r, "UVAG", o)) or D.get((ms, "UVAG", o), 0.0)
        if o in S["FODDO"]:
            return m / UVAG_BAS[(ms, o)] * UVAG_BAS.get((r, o), 0.0)
        return m

    i_losf, i_grof = npk.FERTNED_PARTS.index("losf_stra"), npk.FERTNED_PARTS.index("grof_stra")

    def fertned(r, crop, nut):
        """(DATA(crop, FNUT, "Y"), DATA(crop, FOUT, "Y")) by fert/fertned.gms as the baseline has them when its supply
        calibration runs: the straw left on the field (l. 279-285) with the region's straw losses and production of the
        trend, not the simulation's start values the model's own data hold. None without CAPRI's data for the crop."""
        parts = npk._fertned_parts(r, nut, crop)
        if parts is None:
            return None
        if (r, "GROF", "STRA") in D_TRD:
            parts = list(parts)
            parts[i_losf], parts[i_grof] = D_TRD.get((r, "LOSF", "STRA"), 0.0), D_TRD[(r, "GROF", "STRA")]
        return npk.fertned_at_yields(*parts, 1.0, 1.0, AtmDep=DEP.get(r, 0.0) if nut == "N" else 0.0, nitrogen=nut == "N")

    def pest_uvag(r, ms, i):
        """DATA(RUNR, "UVAG", pestoAgg, "Y"): the member state's base value x inflation (the region's own base value
        where the member state has none)."""
        return DATA_UVAG_IO_SIMY(PRICE.get((ms, i)) or PRICE.get((r, i), 0.0), infl)

    mrows, prows = [], []
    for r in regions:
        ms = capri_ms(r)
        for c in S["MCACT"]:
            levl = D.get((r, c, "LEVL"), 0.0)
            techs = [a_ for a_ in ("T", "T1", "T2") if TF.get((r, c, "LEVL", a_), 0.0)]
            if not levl or not techs:
                continue
            for a_ in techs:
                tl = TF[(r, c, "LEVL", a_)]
                # the yield's value without damage (l. 168-175); sugar beet's p_emr (sugar/adjQuot.gms) is not ported:
                # its UVAG stands in, which moves nothing kept (sugar beet is set exogenous, l. 476, and takes the
                # linear form, whose terms do not read the price-damage ratio)
                outs = [(D.get((r, c, o), 0.0), uvag(r, ms, o), TF.get((r, c, o, a_), 0.0), on_farm(r, ms, o))
                        for o in S["PACT_TO_O"].get(c, ())]
                ndy = CP.p_pestPar_NoDamageYld(outs, tl, levl)
                mc = {}
                if ndy:
                    for f_, n_ in FNUT.items():
                        # (the nutrient data's crops under the model's names: CORN for MAIZ, WINE for TWIN)
                        fy = fertned(r, MODEL_CROP.get(c, c), n_)
                        if fy is None or (r, n_) not in NR:
                            mc[f_] = 0.0
                            continue
                        d_fnut, d_fout = fy
                        me, ca = NR[(r, n_)]
                        t_y = TF.get((r, c, "Yield", a_), 0.0)
                        t_f = FN.p_technFact_FNUT(t_y) - 1.0  # the nutrient's factor is the yield's (fertned.gms l. 206-207)
                        dd = DEP.get(r, 0.0) if n_ == "N" else 0.0
                        t_o = (FN.p_technFact_MANN(t_f, d_fout, dd) if n_ == "N" else TF.get((r, c, FOUT[f_], a_), 0.0))
                        t_o = 0.0 if t_o is None else t_o
                        # cres_avail is CAPRI's v_nutAvailFactCRes x (1 - v_emiLoss(NETF, N2O, GasTot)); mine_eff its
                        # 1 - v_emiLoss(NETF, N, GasRunTot): the two losses passed as 0 with the factors folded in
                        v_ = CP.p_pestPar_margCostYld(
                            f_, d_fnut, mf.get((r, f_, a_), mf.get((r, f_, "T"), 1.0)), t_f, t_y,
                            [(t_o, d_fout - dd, ca)], DATA_UVAG_IO_SIMY(D.get((ms, "UVAG", f_), 0.0), infl),
                            bioFix=BIOFIX.get((r, c), 0.0), defr=DEFR.get(r, 1.0), crop=c)
                        mc[f_] = v_ / me if n_ == "N" else v_
                ferc = sum(mc.values())
                neg = CP.p_negMargWoPesti(ferc, ndy) if ndy else False
                mrows.append((r, c, a_, ndy, mc.get("NITF", 0.0), mc.get("PHOF", 0.0), mc.get("POTF", 0.0), ferc, int(neg)))
                cells = {}
                for i in S["aggs"]:
                    app = CP.p_pestPar_ApplPerHa(appl_Y(r, c, i), TECHF_INPUT[a_], tl, levl)
                    if not app:
                        continue
                    mxd = MAXD.get((r, c, i, a_), 0.0)
                    pdr, endo = CP.p_pestPar_priceDamagRatio(pest_uvag(r, ms, i), ndy, ferc, mxd, neg) if ndy else (0.0, 0)
                    sf, endo = CP.p_pestPar_slopFudg(app, pdr, endo)
                    cells[i] = dict(ApplPerHa=app, maxDamage=mxd, priceDamagRatio=pdr, SlopFudg=sf, endogenous=endo,
                                    endogenous_start=endo)
                for i, d in cells.items():
                    d["technFact_LEVL"] = tl
                    prows.append((r, c, i, a_, d))
    m = pd.DataFrame(mrows, columns=["region", "activity", "technology", "no_damage_yld", "marg_cost_nitf",
                                     "marg_cost_phof", "marg_cost_potf", "marg_cost_ferc", "negative_margin"])
    if a.calibrate:
        # CAPRI's loop, each cell its own NLP (cal_pesti.gms l. 322-405; DEP-59)
        cal = {(r, c, i, a_): (d["ApplPerHa"], d["priceDamagRatio"]) for r, c, i, a_, d in prows if d["priceDamagRatio"]}
        res = CP.m_pestiCaliPower_loop(cal)
        for r, c, i, a_, d in prows:
            if (r, c, i, a_) in res:
                d.update(res[(r, c, i, a_)])
                d["powerDamageFac"] = CP.p_pestPar_powerDamageFac(d["SlopLin"], d["SlopExpo"], d["Expon"],
                                                                 d["ApplPerHa"], d["technFact_LEVL"])
            if c == "SUGB":
                d["endogenous"] = 0                                  # l. 476
        # the choice of form needs the technologies of a (region, crop, aggregate) together (PowerUtility, l. 478-484)
        by = defaultdict(list)
        for r, c, i, a_, d in prows:
            by[(r, c, i)].append(d)
        for ds in by.values():
            for d in ds:
                d["PowerUtility"] = CP.p_pestPar_PowerUtility(ds, d["endogenous"], d.get("powerPriceEla", 0.0))
            for d in ds:
                CP.choose_form(d)
        ndf = defaultdict(lambda: ([], []))
        for r, c, i, a_, d in prows:
            ndf[(r, c, a_)][0].append(d["curDamage"])
            ndf[(r, c, a_)][1].append(d["ApplPerHa"])
    rows = []
    for r, c, i, a_, d in prows:
        row = dict(region=r, activity=c, item=i, technology=a_, appl_per_ha=d["ApplPerHa"], max_damage=d["maxDamage"],
                   uvag=pest_uvag(r, capri_ms(r), i),
                   price_damage_ratio=d["priceDamagRatio"], slop_fudg=d["SlopFudg"] if not a.calibrate else
                   (1.0 / d["ApplPerHa"]), endogenous_start=d["endogenous_start"])
        if a.calibrate:
            row.update(slop_lin=d.get("SlopLin", 0.0), slop_expo=d.get("SlopExpo", 0.0) if d.get("Expon") else 0.0,
                       expon=d.get("Expon", 0.0), endogenous=d["endogenous"],  # kept by the linear cells too
                       power_infes=d.get("powerInfes", 0), cur_damage=d["curDamage"], no_damage_fac="")
        rows.append(row)
    if a.calibrate:
        for (r, c, a_), (dm, aps) in sorted(ndf.items()):
            rows.append(dict(region=r, activity=c, item="YILD", technology=a_, appl_per_ha="", max_damage="",
                             uvag="", price_damage_ratio="", slop_fudg="", endogenous_start="", slop_lin="", slop_expo="",
                             expon="", endogenous="", power_infes="", cur_damage="",
                             no_damage_fac=CP.p_pestPar_NoDamageFac(dm, aps)))
    p = pd.DataFrame(rows)
    if a.calibrate:
        p = pesti_test(p)
    if not a.regions:
        OUT.mkdir(parents=True, exist_ok=True)
        m.to_csv(OUT / "pesticide_margins_2030.csv", index=False, float_format="%.17g")
        p.to_csv(OUT / "pesticide_par_2030.csv", index=False, float_format="%.17g")
    w = m[m.no_damage_yld > 0]
    sh = (w.marg_cost_ferc / w.no_damage_yld)
    print(f"{len(regions)} regions; margins {len(m)} rows ({len(w)} with a yield value); FERC over the yield's value: "
          f"median {sh.median():.3f}, 5%-95% {sh.quantile(0.05):.3f} to {sh.quantile(0.95):.3f}; negative margins "
          f"{int(m.negative_margin.sum())}; cells {len(p)}; with a price-damage ratio "
          f"{int((pd.to_numeric(p.price_damage_ratio, errors='coerce') > 0).sum())}; endogenous at the start "
          f"{int((pd.to_numeric(p.endogenous_start, errors='coerce') > 0).sum())}")
    if a.regions:
        print(m.to_string(max_rows=60))
        print(p.head(40).to_string())


if __name__ == "__main__":
    main()

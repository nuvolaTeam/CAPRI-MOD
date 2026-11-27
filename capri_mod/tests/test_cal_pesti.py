"""The port of CAPRI's pesticide calibration (supply/cal_pesti.gms, 5_aggregates stage; capri_mod/supply/equations/
cal_pesti.py) against CAPREG's own 2017 results, p_pestPar of capreg/pmppar_17<CC>.gdx (the file the baseline's
create_sim_ini_gdx.gms l. 400-410 loads; claude/pesticide_p1_audit_2026-11-27.md): a cell kept with the power form
recalibrated from the price-damage ratio CAPREG's own solution implies (its first-order condition pestiOptimal_),
the linear cells' slope, the yield factor without damage. Needs capri_sources (skipped without)."""
import math
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from capri_mod.external_paths import SOURCES
from capri_mod.supply.equations import cal_pesti as CP

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
CAPREG = SOURCES / "results" / "capreg"
AGGS = ("PESTOF", "PESTOG", "PESTOH", "PESTOI", "PESTOO")


def _cells(cc):
    from _gdx import read_symbol
    out = defaultdict(dict)
    for r, c, it, a, item, v in read_symbol(CAPREG / f"pmppar_17{cc}.gdx", "p_pestPar"):
        out[(r, c, it, a)][item] = float(v)
    return out


needs = pytest.mark.skipif(not (CAPREG / "pmppar_17AT.gdx").exists(),
                           reason="CAPREG's pmppar_17<CC>.gdx not in capri_sources/results/capreg")


@needs
def test_the_power_calibration_reproduces_capregs_2017_terms():
    """Austria: all 645 cells of the power form recalibrated within 1e-4 (SlopLin, SlopExpo, Expon); Denmark: 63 of
    its 68, the others another optimum of the same non-convex problem (26-27 November 2026, all 35 countries:
    22,236 of 22,395 cells within 1e-4; of the rest 60 at another optimum of the same objective, 88 at a lower one
    here, 11 at a lower one in CAPREG's)."""
    for cc, need in (("AT", 645), ("DK", 63)):
        ref, cal = {}, {}
        for key, d in _cells(cc).items():
            ap = d.get("ApplPerHa", 0.0)
            if key[2] == "YILD" or not ap or not d.get("Expon"):
                continue
            sl, se, ex = d["SlopLin"], d["SlopExpo"], d["Expon"]
            cal[key], ref[key] = (ap, sl - se * ex * ap ** (ex - 1)), d
        res = CP.m_pestiCaliPower_loop(cal)
        same = sum(max(abs(res[k][x] - d[x]) / max(abs(d[x]), 1e-9) for x in ("SlopLin", "SlopExpo", "Expon")) <= 1e-4
                   for k, d in ref.items())
        assert same >= need, (cc, same)


@needs
def test_the_linear_fall_back_and_the_yield_factor_without_damage_are_capregs():
    """Denmark: every linear cell's slope 1 / ApplPerHa (SlopFudg copied to SlopLin, cal_pesti.gms l. 502-503) and
    every NoDamageFac 1 + the sum of the aggregates' current damage (l. 505-515), within 1e-12."""
    cells = _cells("DK")
    n_lin = n_ndf = 0
    for key, d in cells.items():
        ap = d.get("ApplPerHa", 0.0)
        if key[2] != "YILD" and ap and not d.get("Expon") and d.get("SlopLin"):
            assert d["SlopLin"] == pytest.approx(1.0 / ap, rel=1e-12)
            n_lin += 1
    for (r, c, it, a), d in cells.items():
        if it != "YILD" or "NoDamageFac" not in d:
            continue
        dmg, aps = [], []
        for agg in AGGS:
            e = cells.get((r, c, agg, a), {})
            ap = e.get("ApplPerHa", 0.0)
            aps.append(ap)
            if not ap or not e.get("maxDamage"):
                continue
            e = dict(e, PowerUtility=1.0 if e.get("Expon") else 0.0,
                     SlopFudg=0.0 if e.get("Expon") else e.get("SlopLin", 0.0))
            if e.get("Expon"):
                e["powerDamageFac"] = CP.p_pestPar_powerDamageFac(e["SlopLin"], e["SlopExpo"], e["Expon"], ap)
            dmg.append(CP.choose_form(e)["curDamage"])
        assert CP.p_pestPar_NoDamageFac(dmg, aps) == pytest.approx(d["NoDamageFac"], rel=1e-12)
        n_ndf += 1
    assert n_lin > 100 and n_ndf > 40, (n_lin, n_ndf)
    assert not math.isnan(sum(d.get("NoDamageFac", 0.0) for d in cells.values()))


BASELINE = SOURCES / "results" / "baseline"
PAR_2030 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "pesticide_par_2030.csv"
needs_2030 = pytest.mark.skipif(not (BASELINE / "pmppar_21730AT.gdx").exists() and
                                not (BASELINE / "pmppar_21730ATdefaulta.gdx").exists(),
                                reason="CAPRI's pmppar_21730<CC>.gdx not in capri_sources/results/baseline")


@needs_2030
def test_the_2030_calibration_inputs_and_terms_are_capris():
    """Austria and Denmark against CAPRI's own 2030 calibration (p_pestPar of baseline/pmppar_21730<CC>): the same
    cells; the application per ha (capmod/define_inputs.gms l. 107-112) and the maximum damage within 1e-9; the
    endogenous flag and the form in every cell; the price-damage ratio CAPRI's terms imply at the application (its
    first-order condition) within 1e-5 of ours, which rests on the baseline's prices (arm/set_prices.gms with "BAS"),
    the inflated pesticide price, the on-farm share and the straw items of the trend; the calibrated terms within
    1e-4 in at least 92% of the two countries' power cells (636 of 685; Austria has 47 of the 207 cells that differ
    in all 35 countries, where 23,163 of 23,370 agree, 27 November 2026: a non-convex problem, solved cell by cell
    with IPOPT here and by region with CONOPT in CAPRI)."""
    import csv
    from _gdx import read_symbol
    ours = {}
    with open(PAR_2030, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["region"][:2] in ("AT", "DK") and r["item"] != "YILD":
                ours[(r["region"], r["activity"], r["item"], r["technology"])] = r
    capri = defaultdict(dict)
    for cc in ("AT", "DK"):
        f = next(p for p in (BASELINE / f"pmppar_21730{cc}.gdx", BASELINE / f"pmppar_21730{cc}defaulta.gdx") if p.exists())
        for r, c, it, a, item, v in read_symbol(f, "p_pestPar"):
            if it != "YILD":
                capri[(r, c, it, a)][item] = float(v)
    capri = {k: d for k, d in capri.items() if d.get("ApplPerHa")}
    assert set(capri) == set(ours) and len(ours) > 1500
    power = close = 0
    for k, d in capri.items():
        o = {x: float(v or 0.0) for x, v in ours[k].items() if x not in ("region", "activity", "item", "technology")}
        assert math.isclose(o["appl_per_ha"], d["ApplPerHa"], rel_tol=1e-9), k
        assert math.isclose(o["max_damage"], d.get("maxDamage", 0.0), rel_tol=1e-9, abs_tol=1e-15), k
        assert bool(o["endogenous"]) == bool(d.get("endogenous")), k
        assert bool(o["expon"]) == bool(d.get("Expon")), k
        if d.get("Expon"):
            power += 1
            implied = d["SlopLin"] - d["SlopExpo"] * d["Expon"] * d["ApplPerHa"] ** (d["Expon"] - 1.0)
            assert math.isclose(o["price_damage_ratio"], implied, rel_tol=1e-5), k
            close += all(math.isclose(o[a_], d[b_], rel_tol=1e-4) for a_, b_ in
                         (("slop_lin", "SlopLin"), ("slop_expo", "SlopExpo"), ("expon", "Expon")))
        else:
            assert math.isclose(o["slop_lin"], d["SlopLin"], rel_tol=1e-9), k
    assert power > 500 and close >= 0.92 * power, (power, close)


def test_the_unit_values_of_the_baseline_follow_capris_statements():
    """arm/set_prices.gms as levels (%1 = "BAS" in a baseline): the absolute change of the market's price, half of
    wheat's relative change for durum wheat, milled rice per paddy for paddy rice, olive oil for olives; None without
    the market's price at the reference point; the market's price itself without a unit value there."""
    from capri_mod.market.equations import set_prices as SP
    assert SP.DATA_UVAG_MARR_Y(150.0, 195.0, 151.0) == 194.0
    assert SP.DATA_UVAG_MARR_Y(0.0, 195.0, 151.0) == 195.0 and SP.DATA_UVAG_MARR_Y(150.0, 195.0, 0.0) is None
    assert math.isclose(SP.DATA_UVAG_DWHE_Y(200.0, 180.0, 150.0), 200.0 * 1.1) and SP.DATA_UVAG_DWHE_Y(200.0, 180.0, 0) is None
    assert math.isclose(SP.DATA_UVAG_PARI_Y(300.0, 340.0, 300.0, 60.0, 100.0), 324.0)
    assert SP.DATA_UVAG_PARI_Y(300.0, 340.0, 300.0, 60.0, 0.0) is None
    assert SP.DATA_UVAG_OLIV_Y(1300.0, 2400.0, 2000.0) == 1700.0 and SP.DATA_UVAG_OLIV_Y(1300.0, 2400.0, 0.0) is None


def test_capris_test_of_the_calibration_returns_the_observed_point():
    """m_pestiTest (supply/cal_pesti.gms l. 517-561; capri_mod/supply/equations/pesti_test.py): with terms that meet
    the first-order condition at the observed application the farmer's optimum is that application and the yield
    factor 1; an exogenous cell keeps its application; the linear fall-back returns it within its smoothing; a price
    above the slope ends the use; and, on the calibrated 2030 file, the yield factor is within 1e-4 of 1 in all but
    5 of 11,873 crop-technologies (largest difference 2e-4)."""
    import csv
    from capri_mod.supply.equations import pesti_test as PT
    a0, pdr, se, ex = 2.0, 0.3, 0.05, 2.5
    sl = pdr + se * ex * a0 ** (ex - 1.0)                       # pestiOptimal_ at a0
    assert abs(CP.pestiOptimal_(a0, pdr, sl, se, ex)) < 1e-12
    assert math.isclose(PT.m_pestiTest_cell(a0, pdr, sl, se, ex, 1), a0, rel_tol=1e-12)
    assert PT.m_pestiTest_cell(a0, pdr, sl, se, ex, 0) == a0
    assert PT.m_pestiTest_cell(a0, pdr, sl, se, ex, 1, testincrease=10.0) == 0.0 and sl < pdr * 11
    assert 0 < PT.m_pestiTest_cell(a0, pdr, sl, se, ex, 1, testincrease=0.5) < a0
    assert math.isclose(PT.p_pestiEla_testincrease(), 1 / 0.3)
    lin = PT.m_pestiTest_cell(a0, 0.3, 1 / a0, 0.0, 0.0, 1)
    assert abs(lin / a0 - 1) < 1e-3 and PT.m_pestiTest_cell(a0, 0.3, 1 / a0, 0.0, 0.0, 1, testincrease=1.0) == 0.0
    mxd = 0.2
    ndf = 1.0 + mxd * PT.damage_share(a0, sl, se, ex)
    assert math.isclose(PT.yldPestFac_(ndf, [(mxd, a0, sl, se, ex)]), 1.0) and not PT.pestiCaliProblems_map(1.00005)
    assert PT.pestiCaliProblems_map(0.9998)
    with open(PAR_2030, newline="") as fh:
        y = [float(r["yld_pest_fac_cal"]) for r in csv.DictReader(fh) if r["item"] == "YILD"]
    assert len(y) == 11873 and sum(PT.pestiCaliProblems_map(v) for v in y) == 5 and max(abs(v - 1) for v in y) < 2.1e-4

"""CAPRI's pesticide module in the supply model (supply/supply_model.gms yldPestFac_, pestiUse_, pestiTot_; setting
supply.pest_disagg; the plan PESTICIDE_P4_PLAN.md in the developer notes): the region's data and the switch."""
import csv
from pathlib import Path

import pytest

from capri_mod.data import loaders as L
from capri_mod.settings import override
from capri_mod.supply.regional_supply.region_build import RegionBuildBlock

ROOT = Path(__file__).resolve().parents[2]
PAR_2030 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "pesticide_par_2030.csv"


def test_the_region_reads_the_calibrated_pesticide_cells():
    """The loader's tables (loaders._pesticide_tables) carry each region's calibrated cells and NoDamageFac as written
    in pesticide_par_2030.csv; the region takes them with supply.pest_disagg "agg5" at the 2030 market year, none
    with "none" (CAPRI's default, pestDisaggStage none); "agg5" without CAPRI's two technologies stops."""
    from capri_mod.tableio import read_input
    t = L._pesticide_tables(read_input(PAR_2030, index_col=0))
    with open(PAR_2030, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["region"] == "AT120000"]
    at = t["AT120000"]
    cells = [r for r in rows if r["item"] != "YILD"]
    assert len(at["cells"]) == len(cells) > 100
    for r in cells:
        c = at["cells"].loc[(r["activity"], r["item"], r["technology"])]
        for k in L.PESTICIDE_CELL_COLUMNS:
            assert c[k] == pytest.approx(float(r[k] or 0.0), rel=1e-15, abs=0.0), (r["activity"], r["item"], k)
    ylds = {(r["activity"], r["technology"]): float(r["no_damage_fac"]) for r in rows if r["item"] == "YILD"}
    assert at["no_damage_fac"] == ylds and all(0.9 < v < 1.2 for v in ylds.values())
    d = {"pesticides": t, "market_year": 2030}
    b = RegionBuildBlock._pesticides_for
    assert b(None, d, "AT120000") is None                                 # the default "none"
    with override({"supply.pest_disagg": "agg5"}):
        assert b(None, d, "AT120000") is at
        with override({"supply.crop_technologies": False}), pytest.raises(ValueError):
            b(None, d, "AT120000")
        with pytest.raises(ValueError):
            b(None, {"pesticides": t, "market_year": 2017}, "AT120000")


def test_the_in_solve_yield_factors_sum_capris_technologies():
    """insolve_yield_factors: a crop's output and need factors over its technologies, (1 + s_T d) x_T (1 + (y_T - 1))
    summed over X (SUPBAL_, NUTNED_); with the yield factors at 1 the technology mix's own change, yield_diff x z / X
    (as the gross output had it: X x y + yield_diff x y x z); SURTOT_pestTerms the residues', removal's and fixation's
    changes, res x dev_MANN + (fix - rem) x dev_NITF."""
    from capri_mod.supply.equations.supply_model.pesticides import SURTOT_pestTerms, insolve_yield_factors
    X, z, yd, nd = 100.0, 10.0, 0.4, 0.59
    tf, ned = insolve_yield_factors(X, {"T1": X / 2 + z, "T2": X / 2 - z}, {"T1": 1.0, "T2": 1.0}, yd, nd)
    assert tf == pytest.approx(yd * z / X, abs=1e-15) and ned == pytest.approx(1 + nd * z / X, abs=1e-15)
    y = {"T1": 0.97, "T2": 1.02}
    tf, ned = insolve_yield_factors(X, {"T1": 60.0, "T2": 40.0}, y, yd, nd)
    assert 1 + tf == pytest.approx((1.2 * 60 * 0.97 + 0.8 * 40 * 1.02) / X, abs=1e-15)
    assert ned == pytest.approx(((1 + nd / 2) * 60 * 0.97 + (1 - nd / 2) * 40 * 1.02) / X, abs=1e-15)
    tf, ned = insolve_yield_factors(X, {"T": X}, {"T": 0.95}, 0.0, 0.0)          # one technology
    assert tf == pytest.approx(-0.05, abs=1e-15) and ned == pytest.approx(0.95, abs=1e-15)
    assert SURTOT_pestTerms(30.0, 120.0, 5.0, 2.0, -1.5) == pytest.approx(30 * 2 + (5 - 120) * -1.5, abs=1e-12)


def test_the_tax_coefficient_of_the_yield_factor_moves_the_output_and_the_factor_together():
    """ghg_tax.pest_yield_coefficients: per crop of the module, the accounts' tax base moved by a step of the crop's
    in-solve factor with its output moved the same (the realised yield over the factor stays the data's yield), per
    1000 ha; none with the module off. LINEAR_carbonTax_pestYield: the tax x that coefficient x the yield change."""
    import copy
    from types import SimpleNamespace
    import pandas as pd
    from capri_mod.supply.ghg_tax import pest_yield_coefficients
    from capri_mod.supply.equations.supply_model.objective import LINEAR_carbonTax_pestYield
    res = SimpleNamespace(activities=pd.Series({"SWHE": 200.0, "BARL": 0.0}),
                          gross_output=pd.Series({"SWHE": 1600.0, "BARL": 0.0}),
                          insolve_yield={"SWHE": {"tf": 0.02, "ned": 1.03}, "BARL": {"tf": 0.0, "ned": 1.0}})
    seen = []

    def diff(mutate, h):
        r1 = copy.copy(res)
        mutate(r1, h)
        seen.append((r1.insolve_yield["SWHE"]["tf"], float(r1.gross_output["SWHE"])))
        # a tax base linear in the residues, which follow the in-solve factor: 3 kt CO2-eq per unit of (1 + tf)
        return 3.0 * ((1.0 + r1.insolve_yield["SWHE"]["tf"]) - 1.02) / h
    assert pest_yield_coefficients(res, diff) == {}                       # supply.pest_disagg "none"
    with override({"supply.pest_disagg": "agg5"}):
        co = pest_yield_coefficients(res, diff)
    assert set(co) == {"SWHE"} and co["SWHE"] == pytest.approx(3.0 / 200.0, rel=1e-12)
    tf1, go1 = seen[-1]
    assert tf1 == pytest.approx(0.03) and go1 == pytest.approx(1600.0 * 1.03 / 1.02, rel=1e-12)
    assert res.insolve_yield["SWHE"]["tf"] == 0.02 and res.gross_output["SWHE"] == 1600.0    # the baseline untouched
    assert LINEAR_carbonTax_pestYield(50.0 * co["SWHE"], -4.0) == pytest.approx(-50.0 * 3.0 / 200.0 * 4.0)


def test_the_green_deals_factor_on_the_applications_and_the_quota_are_capris_code():
    """With the pesticide module: the Green Deal's factor on every application, (1 + PLAP's total change) x (1 + the
    organic target's), as conventional_io.gms, organic_io.gms and define_inputs.gms run; the quota QUTS = factor x
    GROF (define_inputs.gms l. 141-157); the organic yield gap x 0.45 (organic_area.gms l. 182-186)."""
    from capri_mod.supply.equations.define_inputs import DATA_QUTS_pesTotal
    from capri_mod.supply.equations.greendeal.conventional_io import (DATA_GROF_percentageChange,
                                                                       pest_change_factor_greendeal)
    from capri_mod.supply.equations.greendeal.organic_area import DATA_Yild_percentageChange
    from capri_mod.supply.equations.greendeal.organic_io import DATA_GROF_PLAP_percentageChange
    pc_plap, _ = DATA_GROF_percentageChange(0.20, 0.10)
    assert pc_plap == pytest.approx(-0.20)
    f = pest_change_factor_greendeal(pc_plap, DATA_GROF_PLAP_percentageChange(0.10))
    assert f == pytest.approx(0.8 * 0.9, abs=1e-15)
    assert pest_change_factor_greendeal(-0.20, 0.0) == pytest.approx(0.8, abs=1e-15)     # no organic target
    assert DATA_QUTS_pesTotal(120.0, 0.5) == pytest.approx(60.0)
    assert DATA_Yild_percentageChange(-20.0, None) == pytest.approx(0.20)
    assert DATA_Yild_percentageChange(-20.0, None, pest_disagg=True) == pytest.approx(0.09)


def test_the_yield_factors_are_one_at_the_calibration_point():
    """CAPRI's check of the calibration (baseline/check_cal.gms l. 36-45, 315-324; pesti_test.check_cal_pestiCaliProblems)
    on the data of every region: at the applications per ha of the calibration, the supply model's yield factor
    yldPestFac_ is 1 within 1e-4 in every crop-technology with NoDamageFac (NoDamageFac = 1 + the current damage,
    cal_pesti.gms l. 505-512). So the fertiliser calibration's base (fertilisation.py's need multiplier) sees the yield
    factor at 1, as CAPRI's fert/ferttrm_cor_tj.gms l. 438 fixes it."""
    from collections import defaultdict
    from capri_mod.supply.equations.pesti_test import check_cal_pestiCaliProblems, yldPestFac_
    cells, ndf = defaultdict(list), {}
    with open(PAR_2030, newline="") as fh:
        for r in csv.DictReader(fh):
            k = (r["region"], r["activity"], r["technology"])
            if r["item"] == "YILD":
                ndf[k] = float(r["no_damage_fac"])
            else:
                cells[k].append(tuple(float(r[c]) for c in ("max_damage", "appl_per_ha", "slop_lin", "slop_expo",
                                                             "expon")))
    y = {k: yldPestFac_(ndf[k], cells[k]) for k in ndf}
    assert len(y) > 11000
    assert check_cal_pestiCaliProblems(y) == []

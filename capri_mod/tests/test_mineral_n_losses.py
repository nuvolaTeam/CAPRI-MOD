"""CAPRI's mineral N losses as functions of the fertiliser options in NUTNED_ (supply/supply_model.gms GASTOTNETF_,
RUNTOTNETF_, GASRUNTOTNETF_, l. 3335-3394; NUTNED_ l. 1143, 1196) and the 2030 base mineral N rates."""
import numpy as np
import pytest


def _netf_inputs(region):
    from capri_mod.params import param
    from capri_mod.supply import n_cascade as _nc
    from capri_mod.supply.supply_module import fert_side_table
    g = _nc.load()[1][region]
    lit = {}
    for (r_, t_, i_), v in fert_side_table().items():
        if r_ == region and i_ in ("NH3SYN", "NOXSYN", "N2OSYN", "NO3SRUN"):
            lit.setdefault(t_, {})[i_] = v
    return {"fr": {k: g[k] for k in ("netf_NH3", "netf_NOX", "netf_N2O")}, "run_surf": g["run_surf"],
            "wc_red": float(param("WINTERCOV_NO3_REDUCTION")), "lit": lit}


def test_mineral_losses_follow_the_inhibitor_as_capri():
    """BG02 in CAPRI's Green Deal 2030 run (res_greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00_21730, a check):
    the nitrification inhibitor's shares on N2OSYN and N2OSYN2 sum to 0.368137 and v_emiLoss(BG020000, NETF, N,
    GasRunTot) is 0.158282 (GASTOT 0.055206, RUNTOT 0.103076; winter cover held at 1e-6 there, tillage's runoff effect
    commented out). The model's data and CAPRI's othImpact = 1 - (1 - lit)(1 + NMIN) give the same."""
    from capri_mod.supply.equations.supply_model import n_flow as _nf
    nf = _netf_inputs("BG020000")
    lit, nm = nf["lit"]["NITR_INH"], 0.0794329065172083       # NMIN of the inhibitor (p_ghgMiti othImpact NMIN)
    imp = {k: 1.0 - (1.0 - lit[k]) * (1.0 + nm) for k in lit}
    assert imp["N2OSYN"] == pytest.approx(0.177485, abs=2e-6) and imp["NH3SYN"] == pytest.approx(-0.141992, abs=2e-6)
    assert imp["NOXSYN"] == pytest.approx(0.180056, abs=2e-6) and imp["NO3SRUN"] == pytest.approx(0.471094, abs=2e-5)
    s = 0.350969 + 0.017168
    L = _nf.netf(nf["fr"], nf["run_surf"], fert_syn={"NH3": s * imp["NH3SYN"], "NOX": s * imp["NOXSYN"],
                                                   "N2O": s * imp["N2OSYN"]}, m_run=1.0 - s * imp["NO3SRUN"])
    assert L["NH3"] + L["NOX"] + L["N2O"] == pytest.approx(0.055206, abs=2e-6)
    assert L["RunTot"] == pytest.approx(0.103076, abs=2e-6)
    assert L["GasRunTot"] == pytest.approx(0.158282, abs=3e-6)


def test_nutned_efficiencies_move_with_the_options_from_the_base():
    """The regional NLP's NUTNED_ efficiencies (CapriRegionalNLP._netf_eff): exactly the base ones at the base point
    (options at 0, winter cover at its base share), the mineral one rising with the inhibitor's share as CAPRI's
    GasRunTot falls, and the residues' following the N2O loss (l. 1196)."""
    import casadi as ca
    from capri_mod.supply.equations.supply_model import n_flow as _nf
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nf = _netf_inputs("BG020000")
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    phi = ca.SX.sym("phi"); m = ca.SX.sym("m")
    nlp._fert_phi = {"NITR_INH": (phi, 0.0794329065172083), "PRECFARM": (ca.SX.sym("pf"), 0.535)}
    nlp._catc_m = m
    nlp.spec = {"catc": {"m0": 0.05}}
    d = {"eff": 0.8211318441931801, "gc": 0.8215043875020958, "netf": nf}
    effM, effC = nlp._netf_eff(d)
    f = ca.Function("f", [phi, m], [effM, effC])
    e0 = [float(v) for v in f(0.0, 0.05)]
    assert e0[0] == pytest.approx(d["eff"], abs=1e-15) and e0[1] == pytest.approx(d["gc"], abs=1e-15)
    # without winter cover (CAPRI's run held it at 1e-6): CAPRI's GasRunTot falls from the no-option value to 0.158282
    nlp.spec = {"catc": {"m0": 0.0}}
    effM0, _ = nlp._netf_eff(d)
    g0 = _nf.netf(nf["fr"], nf["run_surf"])["GasRunTot"]
    e1 = float(ca.Function("g", [phi, m], [effM0])(0.368137, 0.0))
    assert e1 - d["eff"] == pytest.approx(g0 - 0.158282, abs=5e-6)
    assert float(f(0.368137, 0.05)[1]) > e0[1]
    # more winter cover cuts the mineral N's runoff (RUNTOTNETF_): efficiency up
    assert float(f(0.0, 0.2)[0]) > e0[0]


def test_base_mineral_n_from_capris_2030_reference():
    """The base mineral N per ha of a crop is CAPRI's 2030 reference flow (npk_crop_coefs_2030.csv, N mine_kg_ha), whose
    sum over the region's crops is CAPRI's purchases (npk_region_2030.csv mine_kt; RO05 78.7 kt where CAPRI's 2017
    rates on the 2030 levels gave 61 kt); the setting that chose the 2017 NMIN table is retired."""
    import pandas as pd
    from pathlib import Path
    DATA_DIR = Path(__file__).resolve().parents[2] / "capri_data"
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.settings import current
    assert "environment.base_mineral_n" not in current()
    B = DATA_DIR / "baselines" / "capri_greendeal_ref" / "1730" / "environment"
    c = pd.read_csv(B / "npk_crop_coefs_2030.csv")
    c = c[(c.nutrient == "N") & (c.capri_region == "RO050000")]
    tot = float((c.mine_kg_ha.fillna(0) * c.levl_kha).sum()) / 1000.0      # kg/ha x kha = t; kt
    reg = pd.read_csv(B / "npk_region_2030.csv")
    mine_kt = float(reg[(reg.capri_region == "RO050000") & (reg.nutrient == "N")].mine_kt.iloc[0])
    assert tot == pytest.approx(mine_kt, rel=1e-6)
    em = EnvironmentalModule({"mineral_n_regional": pd.read_csv(DATA_DIR / "2017" / "supply" / "nutrients_regional.csv",
                                                                index_col=0)})
    assert em._base_mineral_rate("RO050000", "SWHE") == pytest.approx(float(c[c.model_crop == "SWHE"].mine_kg_ha.iloc[0]))

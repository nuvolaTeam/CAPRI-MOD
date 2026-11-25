"""CAPRI's conservation and no tillage options (envind/tillage.gms; tools/build/build_tillage_options.py,
capri_mod/supply/equations/tillage.py, CapriRegionalNLP's tillage block)."""
import numpy as np
import pandas as pd
import pytest

from capri_mod.supply.equations.tillage import (
    p_tillageCover_shares, IniShare_till, MaxIncrease_till, relSubs_till, Subs_till, pmpParsqr_till, pmpParlin_till)


def test_tillage_calibration_cases():
    """tillage.gms l. 664-750: the relative subsidies by the sign of kappa = costParLin - costsaving0 and whether the
    initial share is positive (cropyld 1, the Green Deal's NoYieldEffect 1)."""
    # case 2: kappa < 0, IniShare > 0 -> relSubs1 = -0.2 MaxIncrease, relSubs0 0
    mi = MaxIncrease_till(1.0, 0.2)
    assert mi == pytest.approx(0.8)
    assert relSubs_till(-21.0, 0.0, 0.2, mi) == (0.0, pytest.approx(-0.16), 2)
    # case 1: kappa > 0, IniShare > 0 -> 0.8 MaxIncrease
    assert relSubs_till(10.0, -5.0, 0.2, mi)[1:] == (pytest.approx(0.64), 1)
    # case 4: kappa < 0, costParLin < 0, IniShare 0 -> relSubs1 -0.5, relSubs0 -0.1
    assert relSubs_till(-44.0, -0.3, 0.0, 1.0) == (pytest.approx(-0.1), pytest.approx(-0.5), 4)
    # case 3: kappa > 0 with costParLin < 0 (a large endogenous cost), IniShare 0 -> 1.2 and 0.2
    assert relSubs_till(-5.0, -20.0, 0.0, 1.0) == (pytest.approx(0.2), pytest.approx(1.2), 3)
    # Subs: x max(kappa, |costParLin|) where kappa > 0, x costParLin where kappa < 0 (l. 765-773)
    assert Subs_till(-0.16, -21.0, 0.0) == pytest.approx(3.36)
    assert Subs_till(0.64, 10.0, -5.0) == pytest.approx(9.6)
    assert Subs_till(0.2, -5.0, -20.0) == pytest.approx(0.2 * 15.0)
    # gamma = (Subs1 - Subs0) / (MaxShare - IniShare), beta = Subs0 - costParLin + costsaving0 - gamma m0 (l. 825-842)
    g = pmpParsqr_till(0.0, 3.36, 1.0, 0.2)
    assert g == pytest.approx(4.2)
    assert pmpParlin_till(0.0, -21.0, 0.0, g, 0.2) == pytest.approx(21.0 - 0.84)


def test_tillage_initial_shares_are_the_normalised_survey():
    """tillage.gms l. 316-329, 363-367: the survey's ConvTill, ConsTill and NoTill made shares; noc 1 - the options."""
    sh = p_tillageCover_shares({"ConvTill": 0.879349483313569, "ConsTill": 0.107004912756226,
                                "NoTill": 0.0134931390818228, "WinterCrop": 0.4})
    ini = IniShare_till(sh)
    assert ini["ConsTill"] == pytest.approx(0.107004912756226 / (0.879349483313569 + 0.107004912756226 + 0.0134931390818228))
    assert ini["noc"] == pytest.approx(1.0 - ini["ConsTill"] - ini["NoTill"])
    assert IniShare_till(p_tillageCover_shares({"ConvTill": -1.0}))["noc"] == 1.0


def test_tillage_options_table_is_capris():
    """The built table (capri_data/2017/abatement/mitigation/tillage_options.csv): the initial shares are the levels of
    CAPRI's ini calibration run (capri_costsavings_2030.parquet, v_Miti.l, 452 cells within 2e-6), DE210000's NoTill
    parameters by CAPRI's formulas (case 2)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    t = pd.read_csv(root / "capri_data" / "2017" / "abatement" / "mitigation" / "tillage_options.csv",
                    float_precision="round_trip")
    sav = pd.read_parquet(root / "capri_data" / "sources" / "intermediate" / "ghgtech" / "capri_costsavings_2030.parquet")
    lv = sav[(sav["run"] == "ini") & sav["technology"].isin(["ConsTill", "NoTill"])].set_index(
        ["region", "technology"])["level"]
    d = (t.set_index(["region", "technology"])["ini_share"] - lv).dropna().abs()
    assert len(d) == 452 and d.max() < 1e-5
    r = t[(t["region"] == "DE210000") & (t["technology"] == "NoTill")].iloc[0]
    assert r["till_region"] == "Center" and r["n2osyn"] == pytest.approx(-0.12) and r["case"] == 2
    assert r["cost_lin_eur_ha"] == pytest.approx(64 - 93 - 15)
    assert r["relsubs1"] == pytest.approx(-0.2 * (1.0 - r["ini_share"]))
    assert r["pmp_sqr"] == pytest.approx(0.2 * 44.0)
    assert r["pmp_lin"] == pytest.approx(44.0 + r["costsaving0_eur_ha"] - r["pmp_sqr"] * r["ini_share"])
    assert r["no3mlea"] == pytest.approx(-0.38 * r["tillset_share"])


def test_tillage_block_in_the_regional_nlp():
    """CapriRegionalNLP's tillage block: GHG_Mit_Cost_ on the tillage area (supply_model.gms l. 5077-5080), TotMit_ with
    no control, the options' start at their initial shares, NoTill's othImpact on the N2O of mineral N (GASTOTNETF_,
    l. 3392-3393) from the initial shares."""
    import casadi as ca
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    nlp.xb = np.array([300.0, 100.0, 50.0])
    X0 = ca.SX.sym("x", 3)
    techs = [{"name": "ConsTill", "m0": 0.1967, "ub": 1.0, "k1": -21.0, "lin": 20.174, "sqr": 4.2, "subs0": 0.0,
              "n2osyn": 0.0},
             {"name": "NoTill", "m0": 0.009, "ub": 1.0, "k1": -44.0, "lin": 43.572, "sqr": 8.8, "subs0": 0.0,
              "n2osyn": -0.12}]
    g_rows, lbg, ubg, lbx, ubx = [], [], [], [], []
    X, obj = nlp._abatement_block({"till": {"cols": [0, 1], "techs": techs}}, X0, X0, 0, g_rows, lbg, ubg, lbx, ubx)
    assert nlp.abat["till"]["off"] == 3 and nlp.abat["till"]["area0"] == pytest.approx(400.0)
    assert ubg == [1.0] and lbx == [0.0, 0.0] and ubx == [1.0, 1.0]
    x = np.array([300.0, 100.0, 50.0, 0.25, 0.05])
    L = 400.0
    f = ca.Function("f", [X], [obj])
    want = L * ((-21.0 + 20.174) * 0.25 + 2.1 * 0.25 ** 2 + (-44.0 + 43.572) * 0.05 + 4.4 * 0.05 ** 2)
    assert float(f(x)) == pytest.approx(want, rel=1e-12)
    row = ca.Function("g", [X], [g_rows[0]])
    assert float(row(x)) == pytest.approx(0.3)
    n2o_now, n2o_0 = nlp._till_n2o
    assert float(ca.Function("t", [X], [n2o_now])(x)) == pytest.approx(-0.12 * 0.05)
    assert n2o_0 == pytest.approx(-0.12 * 0.009)
    nlp.X = X; nlp.n0 = 3; nlp.sc = np.ones(3); nlp.feeds = []; nlp.fert = None
    nlp.lbx = np.array([0.0, 0.0, 0.0] + lbx); nlp.ubx = np.array([np.inf] * 3 + ubx)
    assert np.allclose(nlp.start(np.array([300.0, 100.0, 50.0]))[3:], [0.1967, 0.009])


def test_tillage_effects_in_the_accounts():
    """The accounts take the tillage options' effects at their shares against the initial shares: LEACHN_'s second
    factor (supply_model.gms l. 3416-3425; n_flow.LEACHN_B2) and the direct N2O of mineral N (GASTOTNETF_)."""
    from types import SimpleNamespace
    from capri_mod.environmental.nitrogen import NitrogenBlock
    from capri_mod.supply.equations.supply_model.n_flow import LEACHN_B2
    nb = NitrogenBlock.__new__(NitrogenBlock)
    t = pd.read_csv(__import__("pathlib").Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement"
                    / "mitigation" / "tillage_options.csv", float_precision="round_trip")
    r = t[(t["region"] == "DE210000")].set_index("technology")
    e = nb.till_effects("DE210000", SimpleNamespace(till_shares={"NoTill": 0.1, "ConsTill": float(r.at["ConsTill", "ini_share"])}))
    m0 = float(r.at["NoTill", "ini_share"])
    assert e["n2o"][0] == pytest.approx(-0.12 * m0) and e["n2o"][1] == pytest.approx(-0.12 * 0.1)
    assert e["mlea"][1] == pytest.approx(float(r.at["NoTill", "no3mlea"]) * 0.1)
    assert nb.till_effects("DE210000", SimpleNamespace(till_shares={})) is None
    # B2: 1 - nminSh x slea - nmanSh x mlea; NoTill raises the leaching (othImpact < 0)
    assert LEACHN_B2(0.6, 0.3, e["slea"][1], e["mlea"][1]) > LEACHN_B2(0.6, 0.3, e["slea"][0], e["mlea"][0])

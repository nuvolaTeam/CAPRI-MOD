"""CAPRI's producer surplus at a region's solution (income I3): the regional NLP's objective by part
(CapriRegionalNLP.objective_parts) and its PMP terms in CAPRI's categories (IncomeDistributionModule.producer_surplus;
reports/sol_simy.gms l. 2578-2595, capmod/report_supply_model.gms l. 207-220), by hand."""
import numpy as np
import pytest


def test_the_objective_parts_of_a_regional_qp():
    """A two-crop regional problem with one land row and no feeding or blocks: the linear parts are q0 x y, the
    quadratic 0.5 y (Q y), and they add up to IPOPT's objective."""
    from capri_mod.supply import capri_regional_nlp as C
    Q = np.array([[2.0, 0.5], [0.5, 1.0]])
    c = np.array([-10.0, -8.0])
    spec = dict(Q=Q, c=c, A=np.array([[1.0, 1.0]]), b=np.array([10.0]), labels=["arable_land"], acts=["SWHE", "BARL"],
                x_base=np.array([3.0, 4.0]))
    N = C.CapriRegionalNLP(spec)
    r = N.solve(N.start(np.array([3.0, 4.0])), tol=1e-10)
    assert r["success"]
    p = N.objective_parts(r["x"])
    y = np.asarray(p["y"], float)
    assert y == pytest.approx([24.0 / 7.0, 44.0 / 7.0], rel=1e-7)        # the land row binds: y1 + y2 = 10
    assert p["lin"] == pytest.approx(c * y)
    assert p["quad"] == pytest.approx(0.5 * y * (Q @ y))
    assert p["feed_price"] == p["feed_ghg"] == p["feed_pmp"] == p["blocks"] == 0.0
    assert p["obj"] == pytest.approx(float(r["f"]), rel=1e-12)
    assert abs(p["residual"]) < 1e-9


def _region():
    """A hand-built region at the base year (the margins' own cost basis): a crop with a fertiliser cost and an
    emission tax, a fodder crop, a herd whose feed the NLP charges, a technology mix column, a dairy split column, a
    land column, a manure trade column and a fixed activity (other oilseeds, CAPRI's FACT)."""
    import pandas as pd
    from types import SimpleNamespace
    cols = ["SWHE", "GRAI", "DCOW", "land_ARAC", "mix_SWHE", "dairy_z", "manure_export", "OOIL"]
    y = np.array([100.0, 20.0, 10.0, 130.0, 2.0, -0.5, 3.0, 5.0])
    q0 = np.array([-200.0, 400.0, -900.0, 50.0, -30.0, 15.0, 4.0, -50.0])
    quad = np.array([30.0, 10.0, 5.0, 60.0, 1.0, 0.2, 0.0, 2.0])
    op = {"cols": cols, "y": y, "q0": q0, "lin": q0 * y, "quad": quad, "feed_price": 9000.0, "feed_ghg": 0.0,
          "feed_pmp": -700.0, "blocks": 2500.0, "obj": 0.0, "residual": 0.0,
          "lin_adj": {"fert": np.array([100.0, 50.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0]),
                      "tax": np.array([3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])},
          "feed_lin": {"DCOW": 800.0}, "split_lin": {5: (120.0, 2.0)}, "mix_cols": {"SWHE": 4}}
    m = SimpleNamespace(net_revenues=pd.Series({"SWHE": 600.0, "GRAI": 300.0, "DCOW": 1500.0, "OOIL": 300.0}),
                        premiums=pd.Series({"SWHE": 200.0, "GRAI": 100.0, "DCOW": 100.0}),
                        revenues=pd.Series({"SWHE": 1500.0, "GRAI": 900.0, "DCOW": 3000.0}),
                        ev=SimpleNamespace(ghg_applied={"SWHE": 5.0}, mix_dnr={"SWHE": 40.0}),
                        res=SimpleNamespace(obj_parts=op), seen=SimpleNamespace(feed_rations={}))
    return m, op


def test_the_producer_surplus_of_a_region():
    """Each column's linear PMP term is q0 + its gain in CAPRI's LINEAR_: the crop's margin without the tax on its
    net revenue (5) and without its fertiliser cost (100), less its emission taxes (5 + 3); the fodder crop's margin
    without its fodder output (900); the herd's margin without the feed the NLP charges (800); the mix column's T1 - T2
    net revenue without its fertiliser cost (10); the split column's emission tax only. The land column is the land
    market's, the manure trade column none of them. The fixed activity has no PMP terms in CAPRI: its column's terms
    are kept apart (obj_fixed), its margin in LINEAR_act."""
    from capri_mod.income.income_module import IncomeDistributionModule as I
    m, op = _region()
    L = {"SWHE": (600.0 + 5.0) + 100.0 - (5.0 + 3.0), "GRAI": 300.0 + 50.0 - 900.0, "DCOW": 1500.0 + 800.0,
         "mix_SWHE": 40.0 + 10.0, "dairy_z": -2.0}
    y = dict(zip(op["cols"], op["y"]))
    pmp = sum(op["lin"][j] + L[c] * y[c] + op["quad"][j] for j, c in enumerate(op["cols"]) if c in L)
    out = I(None).producer_surplus("FR810000", m, 50000.0, toin={})
    assert out["obj_fixed"] == pytest.approx(-50.0 * 5.0 + 300.0 * 5.0 + 2.0)
    assert out["PMPLevl"] == pytest.approx(-pmp)
    assert out["PMPFeed"] == pytest.approx(700.0)
    assert out["PMPLandTrans"] == pytest.approx(-(50.0 * 130.0 + 60.0))
    assert out["agProdSurplus"] == pytest.approx(50000.0 - pmp + 700.0 - (50.0 * 130.0 + 60.0))
    assert out["LINEAR_act"] == pytest.approx(sum(L[c] * y[c] for c in L) + 300.0 * 5.0)
    assert out["obj_other"] == pytest.approx(4.0 * 3.0)
    assert out["OBJE"] == 0.0 and out["obj_blocks"] == 2500.0
    assert out["pmp_col"] == pytest.approx({c: float(op["q0"][j]) + L[c] for j, c in enumerate(op["cols"]) if c in L})
    # the identity the parts give (CAPRI's: agProdSurplus = OBJE + GHG_Mit_Cost + (MGVA - v_linObjePart)) with the
    # objective of the parts
    obj = float(np.sum(op["lin"]) + np.sum(op["quad"]) + op["feed_price"] + op["feed_ghg"] + op["feed_pmp"]
                + op["blocks"])
    op["obj"] = obj
    out = I(None).producer_surplus("FR810000", m, 50000.0, toin={})
    assert out["agProdSurplus"] - out["OBJE"] == pytest.approx(
        50000.0 - out["LINEAR_act"] + out["obj_other"] + out["feed_price"] + out["feed_ghg"] + out["obj_blocks"]
        + out["obj_fixed"])
    # no NLP parts, or the herds' feed in the "toin" form: no producer surplus
    m.res.obj_parts = None
    assert I(None).producer_surplus("FR810000", m, 50000.0, toin={}) is None


def test_the_income_leaves_the_emission_tax_out():
    """CAPRI's MGVA holds no emission tax (calc_inc_indic.gms l. 30-49): the tax a scenario puts on the net revenues
    (ev.ghg_applied) is added back, to the solve's own net revenues where the model keeps them (res.nr_solve)."""
    import pandas as pd
    from types import SimpleNamespace
    from capri_mod.income.income_module import IncomeDistributionModule as I
    m = SimpleNamespace(net_revenues=pd.Series({"SWHE": 600.0, "DCOW": 1500.0}),
                        ev=SimpleNamespace(ghg_applied={"DCOW": 40.0}))
    assert I.untaxed_net_revenues(m).to_dict() == {"SWHE": 600.0, "DCOW": 1540.0}
    m.ev.ghg_applied = {}
    assert I.untaxed_net_revenues(m) is m.net_revenues
    # after a solve: the solve's own net revenues (res.nr_solve), not net_revenues, which the solve restores to their
    # state before it; the tax recorded at that solve added back
    m.res = SimpleNamespace(nr_solve=pd.Series({"SWHE": 650.0, "DCOW": 1460.0}))
    m.ev.ghg_applied = {"DCOW": 40.0}
    assert I.untaxed_net_revenues(m).to_dict() == {"SWHE": 650.0, "DCOW": 1500.0}


def test_the_producer_surplus_at_the_years_coefficients(monkeypatch):
    """At the 2030 market year a crop's gain in LINEAR_ takes CAPRI's inputs at the year's coefficients (crop_toin_y's
    TOIN at "Y" less the NPK need's value, crop_npk_y) in place of the margin's base cost without its fertilisers: the
    PMP term moves by the difference of the two cost bases (DEP-55)."""
    from capri_mod.income.income_module import IncomeDistributionModule as I
    m, op = _region()
    monkeypatch.setattr(I, "crop_npk_y", staticmethod(lambda region, m_: {"SWHE": 250.0}))
    base = I(None).producer_surplus("FR810000", m, 50000.0, toin={})
    toin = {"SWHE": (1400.0, 1300.0)}                       # (the margin's cost c0, CAPRI's TOIN at "Y")
    out = I(None).producer_surplus("FR810000", m, 50000.0, toin=toin)
    # LIN: nr + ga + c0 - (TOIN_Y - NPK_Y) - tax, against nr + ga + fert - tax at the base year
    d = (1400.0 - (1300.0 - 250.0)) - 100.0
    assert out["pmp_col"]["SWHE"] - base["pmp_col"]["SWHE"] == pytest.approx(d)
    assert out["PMPLevl"] - base["PMPLevl"] == pytest.approx(-d * 100.0)
    assert out["pmp_col"]["GRAI"] == pytest.approx(base["pmp_col"]["GRAI"])

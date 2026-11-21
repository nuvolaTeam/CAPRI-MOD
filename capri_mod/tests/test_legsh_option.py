"""CAPRI's increased legume share in temporary grassland (LegSh; envind/leg_share.gms;
tools/build/build_legsh_option.py, capri_mod/supply/equations/leg_share.py, CapriRegionalNLP's legume share block)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.supply.equations.leg_share import (
    othImpact_BioFix_LegSh_full, LegSh_costPar, othImpact_BioFix_LegSh, NUTNED_LegSh_needShare)
from capri_mod.supply.equations.fertpar import p_nitrFact_BioFix

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "legsh_option.csv"


def test_legsh_statements_are_capris():
    """leg_share.gms l. 33-36, 40-42, 45-47: Germany (grassland rate 0.08, fodder legume share 0.4253, the legumes'
    rate 0.75): F = 0.15 x (1 - s) + 0.75 s, othImpact = F / BF - 1 with BF = fertpar.gms's OFAR rate; 0 where the
    grassland rate is at least 0.15; the costs on the temporary grassland part (1 - s); NUTNED_'s share of OFAR's need
    D b o k / (D (1 - b) k + a)."""
    g, s, f = 0.08, 0.4253322170298865, 0.75
    full = othImpact_BioFix_LegSh_full(g, s, f)
    assert full == pytest.approx(0.15 * (1 - s) + 0.75 * s)
    bf = p_nitrFact_BioFix("OFAR", 0.0, g, s, f, 0.05)
    o = othImpact_BioFix_LegSh(full, bf)
    assert o == pytest.approx(full / (g * (1 - s) + f * s) - 1) and o == pytest.approx(0.1102, abs=1e-4)
    assert othImpact_BioFix_LegSh(othImpact_BioFix_LegSh_full(0.17, 0.879, f),
                                  p_nitrFact_BioFix("OFAR", 0.0, 0.17, 0.879, f, 0.05)) == pytest.approx(0.0, abs=1e-15)
    assert LegSh_costPar(46.666667, s) == pytest.approx(46.666667 * (1 - s))
    D, b, k, a = 282.1169, 0.364973, 1.0, 3.8724
    sh = NUTNED_LegSh_needShare(D, b, o, k, a)
    assert sh == pytest.approx(D * b * o * k / (D * (1 - b) * k + a))
    # the need at v: (D (1 - b (1 + o v)) k + a) = need(0) (1 - share v)
    v = 0.37
    assert (D * (1 - b * (1 + o * v)) * k + a) == pytest.approx((D * (1 - b) * k + a) * (1 - sh * v))


def test_legsh_table():
    """The built table: Germany's DE21 row from CAPRI's miti_data_jul15 and sim_ini data by the statements; the cost
    in the model's money (CAPRI's inflation to 2030 and the deflator cancel, p_infl^13 = deflator(2030)); no row where
    the option has no effect (EL, HU, IT: grassland rate at least 0.15)."""
    t = pd.read_csv(TABLE, float_precision="round_trip").set_index("region")
    r = t.loc["DE210000"]
    miti = pd.read_parquet(ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "scen" / "ghgtech"
                           / "miti_data_jul15_p_ghgMiti.parquet")
    m = miti[(miti["region"] == "DE000000") & (miti["technology"] == "LegSh")].set_index("info")["value"]
    assert r["cost_lin_eur_ha"] == pytest.approx(float(m["costParLin"]) * (1 - r["fleg_share"]), rel=1e-9)
    assert r["pmp_sqr"] == pytest.approx(float(m["pmpParSqr"]) * (1 - r["fleg_share"]), rel=1e-9)
    assert r["cost_lin_eur_ha"] + r["pmp_lin"] == pytest.approx(r["subs0"], rel=1e-9)
    assert r["need_share"] == pytest.approx(NUTNED_LegSh_needShare(
        r["data_nitf_ofar"], r["biofix_ofar"], r["othimpact_biofix"], r["mult_fact_nitf"], r["add_fact_nitf"]))
    assert not t["ms"].isin(["EL000000", "HU000000", "IT000000"]).any()
    assert (t["othimpact_biofix"] > 0).all() and (t["max_share"] == 1.0).all()


def test_legsh_block_in_the_regional_nlp():
    """CapriRegionalNLP's legume share block: the share between 0 and MaxShare, TotMit_ with no control, the cost on
    OFAR's level (GHG_Mit_Cost_'s OFAR base, l. 5058-5059), the terms for NUTNED_ and the N-surplus row; only with the
    N block."""
    import casadi as ca
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    nlp.xb = np.array([50.0])
    X0 = ca.SX.sym("x", 1)
    ls = {"col": 0, "mix": None, "m1": 1.0, "oi": 0.11, "need_share": 0.062, "fix": 103.0, "ydiff": 0.4,
          "c1": 1.34, "c2": 20.1, "subs0": 1.34, "x0": 50.0}
    g_rows, lbg, ubg, lbx, ubx = [], [], [], [], []
    X, obj = nlp._abatement_block({"legsh": ls, "npk": {"nutrients": {"N": {}}}}, X0, X0, 0, g_rows, lbg, ubg, lbx, ubx)
    assert nlp.abat["legsh"]["off"] == 1 and lbx == [0.0] and ubx == [1.0] and ubg == [1.0]
    f = ca.Function("c", [X], [obj])
    assert float(f([50.0, 0.3])) == pytest.approx(50.0 * (1.34 * 0.3 + 0.5 * 20.1 * 0.09))
    assert nlp._legsh["cols"] == {0} and nlp._legsh["need_share"] == 0.062
    from capri_mod.supply.equations.supply_model.nutrients import NUTNED_legSh
    from capri_mod.supply.equations.supply_model.n_surplus import e_BIOFIX_legSh
    assert NUTNED_legSh(100.0, 40.0, 0.062, 0.5) == pytest.approx(100.0 - 40.0 * 0.062 * 0.5)
    assert e_BIOFIX_legSh(5.15, 0.11, 0.5) == pytest.approx(5.15 * 0.11 * 0.5)
    nlp2 = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp2._pv = nlp._pv; nlp2.xb = nlp.xb
    nlp2._abatement_block({"legsh": ls}, X0, X0, 0, [], [], [], [], [])
    assert "legsh" not in nlp2.abat and nlp2._legsh is None


def test_legsh_in_the_accounts():
    """The accounts take the share's othImpact (NitrogenBlock.legsh_effect); none without a share or a row."""
    from types import SimpleNamespace
    from capri_mod.environmental.nitrogen import NitrogenBlock
    nb = NitrogenBlock.__new__(NitrogenBlock)
    v, o = nb.legsh_effect("DE210000", SimpleNamespace(legsh_share=0.25))
    assert v == 0.25 and o == pytest.approx(0.1102, abs=1e-4)
    assert nb.legsh_effect("DE210000", SimpleNamespace(legsh_share=None)) == (0.0, 0.0)
    assert nb.legsh_effect("IT200000", SimpleNamespace(legsh_share=0.5)) == (0.0, 0.0)

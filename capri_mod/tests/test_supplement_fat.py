"""CAPRI's limit of the ration's fat with linseed (SupplementPerc_, supply/supply_model.gms l. 608-633; the feed bulks' fat
from envind/digestibility.gms and envind/line_nitr.gms: tools/build/build_supplement_fat.py; the NLP's block:
CapriRegionalNLP._supplement_fat_block)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.supply.equations.digestibility import (
    p_DryMatterContent, p_nfixRate_gras_digest, p_digestPar_GRAS, p_digestPar_OFAR, p_digestPar_FAT, p_digestPar_shFEED,
    p_digestPar_FEED)
from capri_mod.supply.equations.line_nitr import p_emisFeed_TotFAT_FEED
from capri_mod.supply.equations.supply_model.feeding import SupplementPerc_
from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_supplementSlack

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"


def test_digestibility_and_fat_statements_are_capris():
    """digestibility.gms l. 31-33, 44-45, 49-60, 200-232; line_nitr.gms l. 175-176."""
    assert p_DryMatterContent(0.0, 0.88) == 0.88 and p_DryMatterContent(0.22, 0.88) == 0.22
    assert p_nfixRate_gras_digest(0.0) == 0.05 and p_nfixRate_gras_digest(0.9) == 0.75
    n, g = 0.06, 0.3
    k = n / 0.75
    m = lambda a, b: (1 - k) * a + k * b
    assert p_digestPar_GRAS(g, n, 2.7, 2.5, 2.4, 2.2, 2.5, 2.0) == pytest.approx(
        g * m(2.7, 2.5) + (1 - g) * (0.5 * m(2.4, 2.2) + 0.5 * m(2.5, 2.0)))
    assert p_digestPar_OFAR(2.5, 2.2, 2.0, 0.4) == pytest.approx(2.5 * 0.6 + 0.4 * 2.1)
    assert p_digestPar_FAT(40.5, None) == 39.5 and p_digestPar_FAT(0.7, 0.3) == 0.3
    sh = [p_digestPar_shFEED(w, 30.0) for w in (10.0, 20.0)]
    assert sh == [pytest.approx(1 / 3), pytest.approx(2 / 3)] and p_digestPar_shFEED(1.0, 0.0) == 0.0
    assert p_digestPar_FEED([2.2, 3.2], sh) == pytest.approx(2.2 / 3 + 3.2 * 2 / 3)
    assert p_emisFeed_TotFAT_FEED(3.2, 0.28) == pytest.approx(0.032 * 0.28) and p_emisFeed_TotFAT_FEED(3.2, 0.0) == 0.0


def test_supplement_fat_table():
    """supplement_fat.csv: every animal with linseed has its ration's feeds; the dry-matter contents (CAPRI's at the
    simulation's data) are the rations' (2017);
    TotFAT = EE x DM / 100; the bulks differ between the dairy cows and the other cattle only in grass and other
    fodder (the grazing share)."""
    from capri_mod.data.nested_tables import read_feed_rations
    t = pd.read_csv(M / "supplement_fat.csv", float_precision="round_trip")
    s = pd.read_csv(M / "supplement_effects.csv")
    lin = set(map(tuple, s.loc[s.option == "LINE_Tot", ["region", "animal"]].values))
    assert set(map(tuple, t[["region", "animal"]].drop_duplicates().values)) == lin
    R = read_feed_rations(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv")
    for r in t.sample(400, random_state=0).itertuples():
        assert r.dm_content == pytest.approx(R[r.region][r.animal]["content"][r.feed]["DRMA"], rel=1e-12)
    assert np.allclose(t.tot_fat, t.ee * t.dm_content / 100.0, rtol=1e-12, atol=0.0)
    w = t.pivot_table(index=["region", "feed"], columns="animal", values="ee")
    other = w[["BCOW", "BULL", "HFRS", "CALV"]].dropna()
    assert np.allclose(other.max(axis=1), other.min(axis=1), rtol=1e-12)
    d = (w["DCOW"] - w["BCOW"]).abs().dropna()
    assert (d[d > 1e-9].index.get_level_values("feed").isin(["FGRA", "FOFA"])).all()


def test_supplement_perc_row_and_penalty():
    """The total form is CAPRI's row times X / X0 with v = z / X; the penalty 999999 v^2 X D / 1000 s = 999999 z^2 / X
    D / 1000 s."""
    fat, D, sh, z, X, X0, p, s = 230.0, 6500.0, 0.05, 30.0, 110.0, 100.0, 0.05, 0.004
    capri = (fat + D * sh * z / X) / D - (p + s)
    assert SupplementPerc_(fat, 1.0 / D, sh, z, X, 1.0 / X0, p, s) == pytest.approx(capri * X / X0)
    assert GHG_Mit_Cost_supplementSlack(z * z / X, D, s) == pytest.approx(999999.0 * (z / X) ** 2 * X * D / 1000.0 * s)


def test_supplement_fat_block_in_the_regional_nlp():
    """CapriRegionalNLP._supplement_fat_block: per animal with linseed the percentage in [0, 0.05] and the slack >= 0,
    the row equal to 0, the penalty in the objective; the start puts the percentage and slack where the row holds."""
    import casadi as ca
    from types import SimpleNamespace
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._psyms, nlp._pvals = [], []
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    r = SimpleNamespace(feeds=["FGRA", "FCER", "FMIL"], flex=np.array([True, True, False]),
                        x0=np.array([15000.0, 1000.0, 50.0]))
    nlp.feeds = [("DCOW", "FGRA", r, 0, 1000.0), ("DCOW", "FCER", r, 1, 100.0)]
    nlp.n0, nlp.nf = 2, 2
    nlp.act_idx = {"DCOW": 0}
    nlp.xb = np.array([100.0, 0.0])
    nlp.sc = np.array([100.0, 1.0])
    Z = ca.SX.sym("z", 2)
    U = ca.SX.sym("u", 2)
    nlp._fhv = U * ca.DM([1000.0, 100.0])
    y = Z * ca.DM([100.0, 1.0])
    X0 = ca.vertcat(Z, U)
    tf = {"FGRA": 0.0055, "FCER": 0.028, "FMIL": 0.002}
    spec = {"rations": {"DCOW": r}, "supp_fat": {"DCOW": {"col": 1, "shr": 0.05, "D": 6500.0, "fat": tf}}}
    g, lbg, ubg, lbx, ubx = [], [], [], [], []
    X, obj = nlp._supplement_fat_block(spec, X0, y, 0, g, lbg, ubg, lbx, ubx)
    assert int(X.shape[0]) == 6 and lbx == [0.0, 0.0] and ubx == [0.05, np.inf] and lbg == [0.0] and ubg == [0.0]
    f = ca.Function("f", [X], [ca.vertcat(*g), obj])
    fat_h = 15000 * 0.0055 + 1000 * 0.028 + 50 * 0.002
    F0 = fat_h / 6500.0
    # at base (z = 0): the row holds with p = F0, s = 0, no penalty
    gv, ov = f([1.0, 0.0, 15.0, 10.0, F0, 0.0])
    assert abs(float(gv)) < 1e-12 and float(ov) == 0.0
    # 30 thousand head adopting, the herd at 100: the share F0 + 0.05 x 0.3; with p at 0.05 the slack takes the rest
    Fz = F0 + 0.05 * 0.3
    gv, ov = f([1.0, 30.0, 15.0, 10.0, 0.05, Fz - 0.05])
    assert abs(float(gv)) < 1e-12
    assert float(ov) == pytest.approx(999999.0 * 30.0 ** 2 / 100.0 * 6.5 * (Fz - 0.05))
    assert nlp.supplement_fat_share(np.array([1.0, 30.0, 15.0, 10.0, 0.0, 0.0]), "DCOW") == pytest.approx(Fz)

"""CAPRI's urea substitution (UreaSubst; envind/ammo_tech.gms; tools/build/build_urea_subst_option.py,
capri_mod/supply/equations/ammo_tech.py, CapriRegionalNLP's urea block)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.supply.equations.ammo_tech import (
    MaxShare_UreaSubst, othImpact_NH3SYN_UreaSubst, costParLin_UreaSubst, relSubs_ammTech, Subs_ammTech,
    pmpParsqr_UreaSubst, pmpParlin_UreaSubst)

ROOT = Path(__file__).resolve().parents[2]


def test_urea_subst_parameters_are_capris_formulas():
    """ammo_tech.gms l. 2353-2375: MaxShare the urea share, othImpact the NH3 factors' difference, the cost the other
    fertilisers' price over urea's; case 3 (cost > 0, IniShare 0): relSubs 0.2 / 1.2, pmpParSqr = (Subs1 - Subs0) /
    MaxShare, pmpParLin = Subs0 - costParLin, so the linear cost at zero is Subs0 (l. 3041-3047, 3100-3107)."""
    assert MaxShare_UreaSubst(0.158) == 0.158
    assert othImpact_NH3SYN_UreaSubst(0.15, 0.015) == pytest.approx(0.135)
    k = costParLin_UreaSubst(900.0, 0.158, 0.842, 1.019, 10)
    assert k == pytest.approx((900.0 - 289.0 * 60.0 / 28.0 * 1.019 ** 10) / 0.842)
    r0, r1, case = relSubs_ammTech(k, 0.0, 0.0, 1.0)
    assert (r0, r1, case) == (0.2, 1.2, 3)
    s0, s1 = Subs_ammTech(r0, k), Subs_ammTech(r1, k)
    g = pmpParsqr_UreaSubst(s0, s1, 0.158, 0.0)
    assert g == pytest.approx(k / 0.158)
    assert k + pmpParlin_UreaSubst(0.0, k, s0, g, 0.0) == pytest.approx(s0)
    # case 4: a negative cost
    assert relSubs_ammTech(-100.0, 0.0, 0.0, 1.0) == (-0.1, -0.5, 4)


def test_urea_subst_table():
    """The built table: Germany's row by the formulas, in the model's money (CAPRI's base-year figure over the 2030
    deflator: CAPRI does not inflate this cost, ammo_tech.gms l. 3355-3358)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from _money import deflator
    t = pd.read_csv(ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "urea_subst_option.csv",
                    float_precision="round_trip").set_index("ms")
    fu = pd.read_csv(ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "FracUseFert.csv").pivot_table(
        index="region", columns="fertiliser", values="value")
    pr = pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "mineral_n_price.csv").set_index("capri_code")["eur_per_t_n"]
    r = t.loc["DE000000"]
    k = costParLin_UreaSubst(float(pr["DE"]), fu.at["DE000000", "Ureum"], fu.at["DE000000", "Other"], 1.019, 10)
    assert r["cost_lin_eur_t"] == pytest.approx(k / deflator(2030))
    assert r["max_share"] == pytest.approx(0.158) and r["case"] == 3
    assert r["cost_lin_eur_t"] + r["pmp_lin"] == pytest.approx(r["subs0"])


def test_urea_block_in_the_regional_nlp():
    """CapriRegionalNLP's urea block: the share between 0 and MaxShare, TotMit_ with no control, the cost pending for the
    purchases (GHG_Mit_Cost_'s UreaSubst base, l. 5063), the NH3 term for the loss cascade; only with the N block."""
    import casadi as ca
    from capri_mod.supply.capri_regional_nlp import CapriRegionalNLP
    nlp = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp._pv = lambda v: ca.DM(float(v)) if np.ndim(v) == 0 else ca.DM(np.asarray(v, float))
    nlp.xb = np.array([300.0])
    X0 = ca.SX.sym("x", 1)
    us = {"m1": 0.158, "eff": 0.135, "c1": 22.1, "c2": 700.0, "subs0": 22.1}
    g_rows, lbg, ubg, lbx, ubx = [], [], [], [], []
    X, obj = nlp._abatement_block({"urea": us, "npk": {"nutrients": {"N": {}}}}, X0, X0, 0, g_rows, lbg, ubg, lbx, ubx)
    assert nlp.abat["urea"]["off"] == 1 and lbx == [0.0] and ubx == [0.158] and ubg == [1.0]
    f = ca.Function("c", [X], [nlp._urea_pending])
    assert float(f([300.0, 0.1])) == pytest.approx(22.1 * 0.1 + 350.0 * 0.01)
    from capri_mod.supply.equations.supply_model.mitigation import GHG_Mit_Cost_ureaSubst
    assert GHG_Mit_Cost_ureaSubst(5000.0, 1e-3, 2.0) == pytest.approx(10.0)
    # without the N fertilisation block: no column (its cost base and its effect are there)
    nlp2 = CapriRegionalNLP.__new__(CapriRegionalNLP)
    nlp2._pv = nlp._pv; nlp2.xb = nlp.xb
    X2, _ = nlp2._abatement_block({"urea": us}, X0, X0, 0, [], [], [], [], [])
    assert "urea" not in nlp2.abat and nlp2._urea is None


def test_urea_subst_in_the_accounts():
    """The accounts take the share: the NH3 of mineral N x (1 - v x othImpact), CO2 from urea x (urea share - v) / urea
    share (NitrogenBlock.urea_effect)."""
    from types import SimpleNamespace
    from capri_mod.environmental.nitrogen import NitrogenBlock
    nb = NitrogenBlock.__new__(NitrogenBlock)
    v, e = nb.urea_effect("DE210000", SimpleNamespace(urea_share=0.05))
    assert v == 0.05 and e == pytest.approx(0.135, abs=1e-9)
    assert nb.urea_effect("DE210000", SimpleNamespace(urea_share=None)) == (0.0, 0.0)
    assert nb.urea_effect("DE210000", SimpleNamespace(), frac=True) == pytest.approx(0.158)

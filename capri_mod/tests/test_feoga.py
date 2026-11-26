"""CAPRI's premium outlays per product and their budgets at the solution (income I4; capri_mod/income/feoga.py,
reports/feoga.gms l. 62-162, policy/policy_sets.gms l. 1582-1593), by hand."""
from types import SimpleNamespace

import pandas as pd
import pytest

SCH = ["DPPIL1", "DPRD_LFA", "DPRD_N2K", "DPAE", "DPNAT"]


def _shares(rows, out=True):
    cols = ["region", "activity", "capri_region"] + (["output"] if out else []) + SCH
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols).fillna(0.0)


def _case():
    """Two units of a member state: soft wheat in both (with a technology mix column in the first), heifers whose
    CAPRI members have two main outputs, fallow land with a premium, barley without one."""
    m1 = SimpleNamespace(premiums=pd.Series({"SWHE": 300.0, "HFRS": 50.0, "FALL": 200.0}),
                         ev=SimpleNamespace(mix_parts={"SWHE": {"PRME": 6.0}}))
    m2 = SimpleNamespace(premiums=pd.Series({"SWHE": 280.0, "BARL": 0.0}), ev=SimpleNamespace(mix_parts={}))
    res = {"DE110000": SimpleNamespace(activities=pd.Series({"SWHE": 100.0, "HFRS": 10.0, "FALL": 20.0}),
                                       technology_mix={"SWHE": 5.0}),
           "DE120000": SimpleNamespace(activities=pd.Series({"SWHE": 50.0, "BARL": 40.0}), technology_mix={})}
    sm = SimpleNamespace(_models={"DE110000": m1, "DE120000": m2})
    data = {"premium_output_shares_2030": _shares([
                ("DE110000", "SWHE", "DE110000", "SWHE", 0.9, 0, 0, 0.1, 0),
                ("DE110000", "HFRS", "DE110000", "BEEF", 0.6, 0, 0, 0, 0),
                ("DE110000", "HFRS", "DE110000", "YCOW", 0.3, 0, 0, 0, 0.1),
                ("DE120000", "SWHE", "DE120000", "SWHE", 1.0, 0, 0, 0, 0)]),
            "premium_scheme_shares_2030": _shares([("DE110000", "FALL", "DE110000", 0.5, 0, 0, 0.5, 0)], out=False)}
    return res, sm, data


def test_the_premium_outlays_per_product():
    """FEOP: each activity's premium (with the mix column's difference, 6 EUR/ha on 5 000 ha) x level to its main
    outputs by CAPRI's shares; the fallow land's premium spread over the crops with a premium by area (the barley
    without one not counted). The budgets: Pillar I to budPil1, Pillar II half to budPil2 and half to budNAT, the
    national payments to budNAT; the idle land's budget per 1000 ha of the crops with the budget's premium, spread over
    the crops with a premium, as CAPRI's statements are written (l. 115-116 and 156-159)."""
    from capri_mod.income.feoga import feop_by_product
    res, sm, data = _case()
    t = feop_by_product(res, sm, data)
    assert set(t.index) == {("DE000000", "SWHE"), ("DE000000", "BEEF"), ("DE000000", "YCOW")}
    sw = t.loc[("DE000000", "SWHE")]
    p11 = 300.0 + 6.0 * 5.0 / 100.0
    assert sw["FEOP"] == pytest.approx((p11 * 100 + 280.0 * 50) / 1000 + 150 * (0.001 * 200.0 * 20 / 150))
    assert sw["budPil1"] == pytest.approx((p11 * 0.9 * 100 + 280.0 * 50) / 1000 + 150 * (0.001 * 100.0 * 20 / 150))
    assert sw["budPil2"] == pytest.approx(p11 * 0.05 * 100 / 1000 + 150 * (0.001 * 50.0 * 20 / 100))
    assert sw["budNAT"] == pytest.approx(sw["budPil2"])
    assert sw["budRestEU"] == pytest.approx(0.0)
    assert sw["budEU"] == pytest.approx((p11 * 0.95 * 100 + 280.0 * 50) / 1000 + 150 * (0.001 * 150.0 * 20 / 150))
    assert t.loc[("DE000000", "BEEF")].to_dict() == pytest.approx(
        {"FEOP": 0.3, "budEU": 0.3, "budPil1": 0.3, "budPil2": 0.0, "budNAT": 0.0, "budRestEU": 0.0})
    assert t.loc[("DE000000", "YCOW")].to_dict() == pytest.approx(
        {"FEOP": 0.2, "budEU": 0.15, "budPil1": 0.15, "budPil2": 0.0, "budNAT": 0.05, "budRestEU": 0.0})
    # without CAPRI's shares: an empty table
    assert feop_by_product(res, sm, {}).empty


def test_the_budget_shares_of_a_payment():
    """p_budToPsdPay (policy_sets.gms l. 1582-1593) by the payment's scheme aggregate."""
    from capri_mod.coupling.equations.feoga import p_budToPsdPay
    assert p_budToPsdPay("DPPIL1") == {"budPil1": 1.0, "budPil2": 0.0, "budNAT": 0.0, "budRestEU": 0.0, "budEU": 1.0}
    assert p_budToPsdPay("DPPIL2") == {"budPil1": 0.0, "budPil2": 0.5, "budNAT": 0.5, "budRestEU": 0.0, "budEU": 0.5}
    assert p_budToPsdPay("DPNAT") == {"budPil1": 0.0, "budPil2": 0.0, "budNAT": 1.0, "budRestEU": 0.0, "budEU": 0.0}

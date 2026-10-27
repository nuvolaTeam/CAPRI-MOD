"""Irrigation water-demand indicator (capri_mod/water) and farm-income report (capri_mod/income) on CAPRI's units."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.csvio import read_csv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "capri_data"


@pytest.fixture(scope="module")
def data():
    from capri_mod.data.loaders import load_all_data
    return load_all_data(str(DATA_DIR))


def test_irrigation_table_adds_up_to_fss_irrigated_area(data):
    t = read_csv(DATA_DIR / "2017" / "environment" / "irrigation_2017.csv")
    assert set(t.region) == set(data["areas"].index) - {"IR010000", "IR020000"}   # no Irish share in CAPRI's data
    assert (t[t.activity == "PARI"].irrigated_share == 1.0).all()
    assert t.irrigated_share.between(0.001, 1.0).all()
    assert not t.activity.isin(["GRAS", "RYEM", "OATS", "OCER", "TOBA"]).any()      # not irrigable in CAPRI
    # the irrigable crops' irrigated area = the unit's IRR2 share x its UAA, within [rice + 0.001 x the rest, all of them]
    areas = data["areas"]
    for r, g in t.groupby("region"):
        a = areas.loc[r, list(g.activity)]
        irr = float(g.irr2_share.iloc[0]) * float(areas.loc[r].sum())
        rice = float(a.get("PARI", 0.0))
        lo, hi = rice + 0.001 * (float(a.sum()) - rice), float(a.sum())
        got = float((g.irrigated_share.to_numpy() * a.to_numpy()).sum())
        assert got == pytest.approx(min(max(irr, lo), hi), rel=1e-9, abs=1e-12), r

def test_water_demand_geography(data):
    from capri_mod.water import WaterDemandModule
    res = WaterDemandModule(data).compute()
    df = res.by_region
    assert res.n_regions_covered == 213                        # 221 units without Ireland (2) and Norway (6)
    south = df[df.index.str[:2].isin(["ES", "IT", "EL", "PT"])].water_demand_Mm3.sum()
    assert south / res.total_demand_Mm3 > 0.7                 # irrigation concentrates in the Mediterranean
    assert df.loc["ES610000", "water_demand_m3_per_ha"] > 3 * df.loc["DE110000", "water_demand_m3_per_ha"]
    assert set(res.notes["regions_without_irrigation_data"]) == {"IR010000", "IR020000"}
    # solved areas move the indicator: doubling every area doubles the requirement
    from types import SimpleNamespace
    sr = {r: SimpleNamespace(activities=2.0 * data["areas"].loc[r]) for r in ["ES610000", "IT400000"]}
    r2 = WaterDemandModule(data).compute(sr)
    for r in sr:
        assert r2.by_region.at[r, "water_demand_Mm3"] == pytest.approx(2.0 * df.at[r, "water_demand_Mm3"], rel=1e-12)


@pytest.mark.slow
def test_income_is_capris_mgva_sum(data):
    """Farm income = sum of (revenue - input cost + premium) x level (CAPRI's ProfitAgr over MGVA); the policy
    module's payments are reported beside it, not added (until 27 October 2026 premiums were counted twice)."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
    from capri_mod.income import IncomeDistributionModule
    regs = ["DE110000", "ES610000", "IR010000"]
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    sr = sm.run(price_signals=None, regions=regs)
    cap = PolicyModule(data, PolicyScenario(name="BASELINE")).payments.compute_payments_by_region(
        data["cap_payments"], data["land"])
    res = IncomeDistributionModule(data).compute(sr, sm, cap)
    for r in regs:
        m, lev = sm._models[r], sr[r].activities
        inc = sum(float(m.net_revenues[a]) * float(lev.get(a, 0.0)) for a in m.net_revenues.index)
        sup = sum(float(m.premiums.get(a, 0.0)) * float(lev.get(a, 0.0)) for a in m.net_revenues.index)
        row = res.by_region.loc[r]
        assert row.farm_income == pytest.approx(inc, rel=1e-12)
        assert row.public_support == pytest.approx(sup, rel=1e-12)
        assert row.market_income == pytest.approx(inc - sup, rel=1e-9)
        assert row.cap_payments_policy == pytest.approx(float(cap.at[r, "total_payments"]), rel=1e-12)
        assert 0.0 < row.support_share < 1.0
    assert 0.0 <= res.income_gini <= 1.0 and 0.0 <= res.payment_gini <= 1.0

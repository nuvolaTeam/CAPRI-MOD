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
    t = t[t.region.isin(data["areas"].index)]                  # the run's units (data: the default countries' only)
    # no Irish, Bosnian or Serbian share in the data
    assert set(t.region) == set(data["areas"].index) - {"IR010000", "IR020000", "BA000000", "CS000000"}
    assert (t[t.activity == "PARI"].irrigated_share == 1.0).all()
    assert t.irrigated_share.between(0.001, 1.0).all()
    assert not t.activity.isin(["GRAE", "GRAI", "RYEM", "OATS", "OCER", "TOBA"]).any()      # not irrigable in CAPRI
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
    from capri_mod.data.definitions import is_eu
    assert sum(1 for r in df.index if is_eu(r)) == 213        # the EU's 215 units without Ireland's two
    south = df[df.index.str[:2].isin(["ES", "IT", "EL", "PT"])].water_demand_Mm3.sum()
    assert south / res.total_demand_Mm3 > 0.7                 # irrigation concentrates in the Mediterranean
    assert df.loc["ES610000", "water_demand_m3_per_ha"] > 3 * df.loc["DE110000", "water_demand_m3_per_ha"]
    assert set(res.notes["regions_without_irrigation_data"]) == {"IR010000", "IR020000", "BA000000", "CS000000"}
    # solved areas move the indicator: doubling every area doubles the requirement
    from types import SimpleNamespace
    sr = {r: SimpleNamespace(activities=2.0 * data["areas"].loc[r]) for r in ["ES610000", "IT400000"]}
    r2 = WaterDemandModule(data).compute(sr)
    for r in sr:
        assert r2.by_region.at[r, "water_demand_Mm3"] == pytest.approx(2.0 * df.at[r, "water_demand_Mm3"], rel=1e-12)


@pytest.mark.slow
def test_income_is_capris_mgva_sum(data):
    """Farm income = CAPRI's activity-based income at the solution (income I1, AGGT): the activities' margins x levels
    with the technology mix's, less the change of the herds' feed (the solved ration against the feed the margins
    carry), less the mitigation options' cost plus their revenue; the premiums x levels its public support. The
    region's income is set by the regional solve (SupplyResult.income, gross_margin its MGVA). The policy module's
    payments are reported beside it, not added (until 27 October 2026 premiums were counted twice)."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
    from capri_mod.income import IncomeDistributionModule
    regs = ["DE110000", "ES610000", "IR010000"]
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    sr = sm.run(price_signals=None, regions=regs)
    cap = PolicyModule(data, PolicyScenario(name="BASELINE")).payments.compute_payments_by_region(
        data["cap_payments"], data["land"])
    im = IncomeDistributionModule(data)
    res = im.compute(sr, sm, cap)
    for r in regs:
        m, lev = sm._models[r], sr[r].activities
        mz = dict(sr[r].technology_mix or {})
        dnr = dict(getattr(m.ev, "mix_dnr", None) or {})
        mi = im.mitigation_items(r, sr[r], sm)
        inc = (sum(float(m.net_revenues[a]) * float(lev.get(a, 0.0)) for a in m.net_revenues.index)
               + sum(float(dnr.get(a, 0.0)) * z for a, z in mz.items())
               - im.feed_term(sr[r]) - mi["mitiI"] + mi["mitiO"])
        sup = (sum(float(m.premiums.get(a, 0.0)) * float(lev.get(a, 0.0)) for a in m.net_revenues.index)
               + sum(float(m.data.techn_mix.at[a, "prem_diff_share"]) * float(m.premiums.get(a, 0.0)) * z
                     for a, z in mz.items() if a in m.data.techn_mix.index))
        row = res.by_region.loc[r]
        assert row.farm_income == pytest.approx(inc, rel=1e-12)
        assert sr[r].gross_margin == pytest.approx(inc, rel=1e-12)
        assert mi["mitiI"] > 0
        assert row.public_support == pytest.approx(sup, rel=1e-12)
        assert row.market_income == pytest.approx(inc - sup, rel=1e-9)
        assert row.cap_payments_policy == pytest.approx(float(cap.at[r, "total_payments"]), rel=1e-12)
        assert 0.0 < row.public_support < row.farm_income


@pytest.mark.slow
def test_the_producer_surplus_at_the_regional_solution(data):
    """CAPRI's producer surplus at the regional solution (income I3, IncomeDistributionModule.producer_surplus): the
    regional NLP's objective by part adds up to IPOPT's objective; each activity's linear PMP term on the income's cost
    basis is the supply model's PMP constant f, less the land rents its land use carries (land._land_augment), plus
    the NLP calibration's dq, less the fodder crops' fodder output (CAPRI's LINEAR_ does not sell it) and, at the
    2030 market year, less the crops' cost difference to CAPRI's TOIN at the year's coefficients (DEP-55); and
    agProdSurplus is MGVA plus the three PMP terms."""
    from capri_mod.data.definitions import CROPS
    from capri_mod.income import IncomeDistributionModule as I
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    regs = ["DE110000", "ES610000", "IR010000"]
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    sr = sm.run(price_signals=None, regions=regs)
    for r in regs:
        m, ip = sm._models[r], sr[r].income
        assert "agProdSurplus" in ip, r
        assert abs(ip["obj_residual"]) <= 1e-7 * max(1.0, abs(ip["OBJE"])), r
        assert ip["agProdSurplus"] == pytest.approx(ip["MGVA"] + ip["PMPLevl"] + ip["PMPFeed"] + ip["PMPLandTrans"],
                                                    rel=1e-12)
        lab = list(m.ev.row_labels)
        A = np.asarray(m.res.last_aug[2], float) if getattr(m.res, "last_aug", None) is not None else None
        rents = dict(getattr(m.ev, "land_rent_rows", None) or {})
        dq = dict((getattr(m.par, "nlp_cal", None) or {}).get("dq") or {})
        toin, npk = I.crop_toin_y(r, m), I.crop_npk_y(r, m)
        fert = np.asarray(m.ev.nlp_lin_adj["fert"], float)
        acts = list(m.acts)
        n_checked = 0
        for j, a in enumerate(acts):
            if a not in ip["pmp_col"] or float(sr[r].activities.get(a, 0.0)) <= 0:
                continue
            want = float(m.f[j]) + float(dq.get(a, 0.0))
            if A is not None:
                want -= sum(v * float(A[lab.index(k), j]) for k, v in rents.items() if k in lab and v)
            if a in SupplyModule.FODDER_ACTS:
                want -= float(m.revenues[a])
            if a in CROPS and a in toin:
                want -= (toin[a][1] - npk[a]) - (toin[a][0] - fert[j])
            assert ip["pmp_col"][a] == pytest.approx(want, rel=1e-9, abs=1e-6 * max(1.0, abs(want))), (r, a)
            n_checked += 1
        assert n_checked > 10, r

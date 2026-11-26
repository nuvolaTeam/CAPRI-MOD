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
    carry), plus the crops' residues' nutrients (DATA_TOOU_FOUT, KNOWN_ISSUES K212), with the fodder crops' output at
    CAPRI's UVAG(FODDO) in place of the margin's (K213), less the mitigation options' cost plus their revenue; the
    premiums x levels its public support. The
    region's income is set by the regional solve (SupplyResult.income, gross_margin its MGVA). The policy module's
    payments are reported beside it, not added (until 27 October 2026 premiums were counted twice)."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
    from capri_mod.income import IncomeDistributionModule
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
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
        fo, fom = IncomeDistributionModule.crop_residue_nutrients(m)
        assert fo, r
        res_ = (sum(DATA_TOOU_FOUT([q for q, _ in d.values()], [u for _, u in d.values()]) * float(lev.get(a, 0.0))
                    for a, d in fo.items())
                + sum(DATA_TOOU_FOUT(list(d.values()), [fo[a][k][1] for k in d]) * float(mz.get(a, 0.0))
                      for a, d in fom.items()))
        assert res_ > 0
        fod = IncomeDistributionModule.crop_fodder_output(r, m)
        mp = dict(getattr(m.ev, "mix_parts", None) or {})
        fodd_ = (sum((t_ - v_) * float(lev.get(a, 0.0)) for a, (t_, v_, _p, _s) in fod.items())
                 + sum(float(mp[a]["O"][3]) * (fod[a][0] / fod[a][1] - 1.0) * z for a, z in mz.items()
                       if a in fod and a in mp))
        inc = (sum(float(m.net_revenues[a]) * float(lev.get(a, 0.0)) for a in m.net_revenues.index)
               + sum(float(dnr.get(a, 0.0)) * z for a, z in mz.items())
               - im.feed_term(sr[r]) - mi["mitiI"] + mi["mitiO"] + res_ + fodd_)
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


@pytest.fixture(scope="module")
def solved3(data):
    """The base year's regional solutions of three units (SupplyModule at base prices): the supply module, its
    results and the units."""
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    regs = ["DE110000", "ES610000", "IR010000"]
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    return sm, sm.run(price_signals=None, regions=regs), regs


@pytest.mark.slow
def test_the_producer_surplus_at_the_regional_solution(solved3):
    """CAPRI's producer surplus at the regional solution (income I3, IncomeDistributionModule.producer_surplus): the
    regional NLP's objective by part adds up to IPOPT's objective; each activity's linear PMP term on the income's cost
    basis is the supply model's PMP constant f, less the land rents its land use carries (land._land_augment), plus
    the NLP calibration's dq, less the fodder crops' fodder output (CAPRI's LINEAR_ does not sell it) and, at the
    2030 market year, less the crops' cost difference to CAPRI's TOIN at the year's coefficients (DEP-55); and
    agProdSurplus is MGVA plus the three PMP terms."""
    from capri_mod.data.definitions import CROPS
    from capri_mod.income import IncomeDistributionModule as I
    from capri_mod.supply.supply_module import SupplyModule
    sm, sr, regs = solved3
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


@pytest.mark.slow
def test_the_gross_account_by_item_at_the_regional_solution(solved3):
    """CAPRI's gross account by item at the regional solution (income I2, SupplyResult.eaa; reports/sol_simy.gms
    l. 2549-2566): the revenue by output item adds up to each activity's revenue; TOOU - TOIN + PRME is MGVA; each
    crop product's value is its GROF (1000 t) x its price (a fodder crop's in fresh matter at CAPRI's UVAG(FODDO),
    K213); and MGVA equals I1's AGGT but for the input cost table's
    items at the member state's UVAP against TOIN at the regional UVAG (about 1e-5 relative to a herd's input cost);
    the accounts at producer and basic prices hold the regional model's fertiliser purchases and the premiums (I2b)."""
    from capri_mod.data.definitions import CROPS
    from capri_mod.income import IncomeDistributionModule as I
    sm, sr, regs = solved3
    for r in regs:
        m, e = sm._models[r], sr[r].eaa
        assert e is not None, r
        fod = I.crop_fodder_output(r, m)
        for a, it in m.output_items.items():
            assert sum(v for *_, v in it) == pytest.approx(float(m.revenues[a]), rel=1e-12, abs=1e-9), (r, a)
        assert e["MGVA"] == pytest.approx(e["TOOU"] - e["TOIN"] + e["PRME"], rel=1e-12)
        assert e["PRME"] == pytest.approx(sr[r].income["PRME"] / 1000.0, rel=1e-12)
        assert abs(e["DIFF"]) <= 1e-5 * abs(e["AGGT"]), r
        # income I2b: the purchases at the solution (kt) at the member state's UVAP of the base year, the premiums
        pu = e["purchases"].set_index("item")
        npk = sr[r].fert_npk
        assert pu.at["NITF", "NETF"] == pytest.approx(npk["N"]["purchase"] / 1000.0, rel=1e-12)
        assert pu.at["NITF", "NETF"] > 0
        assert e["EAAP"]["TOIN"] == pytest.approx(float(pu.EAAP.sum()), rel=1e-12)
        assert e["EAAP"]["PRME"] == pytest.approx(e["PRME"], rel=1e-12)
        assert e["EAAP"]["MGVA"] == pytest.approx(e["PRME"] - e["EAAP"]["TOIN"], rel=1e-12)
        it = e["items"].set_index(["side", "item"])
        L = sr[r].activities
        for a in CROPS:
            if ("O", a) in it.index and float(L.get(a, 0.0)) > 0 and not (sr[r].technology_mix or {}).get(a):
                kg, uv, v = m.output_items[a][0][1:4]
                if a in fod:
                    # a fodder crop's in fresh matter at UVAG(FODDO), K213, CAPRI's unit (income I2c)
                    from capri_mod.coupling.equations.sol_simy import DATA_UVAG_FODDO
                    assert it.loc[("O", a), "UVAG"] == pytest.approx(DATA_UVAG_FODDO(fod[a][2], fod[a][3]), rel=1e-12)
                    assert it.loc[("O", a), "EAAG"] == pytest.approx(
                        0.001 * v * I.fodder_output_ratio(fod[a]) * float(L[a]), rel=1e-12), (r, a)
                    continue
                assert it.loc[("O", a), "GROF"] == pytest.approx(0.001 * kg * float(L[a]), rel=1e-12), (r, a)
                assert it.loc[("O", a), "EAAG"] == pytest.approx(it.loc[("O", a), "GROF"] * uv / 1000.0, rel=1e-12)


@pytest.mark.slow
def test_the_crops_residue_nutrients_at_the_regional_solution(solved3):
    """K212: the regional model's nutrient block records each crop's residues' nutrients at the solve's yields
    (DATA(crop, MANN | MANP | MANK): the residue pool's per ha, unscaled, or a permanent crop's own; at the base yields
    npk_crop_coefs_2030.csv's) with the member state's unit value of the output (npk_region_2030.csv
    fout_uvag_eur_t); the income's MGVA of a crop holds their value (DATA_TOOU_FOUT) and the account books them as
    the outputs MANN, MANP, MANK."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
    from capri_mod.fert.npk import NPKData
    from capri_mod.income import IncomeDistributionModule as I
    D = NPKData.get()
    sm, sr, regs = solved3
    for r in regs:
        m = sm._models[r]
        fo, _fom = I.crop_residue_nutrients(m)
        assert fo, r
        cr = D.capri_region(r)
        a = "SWHE"
        q, uv = fo[a]["MANN"]
        R = D.region(cr, "N")
        assert uv == pytest.approx(float(R.fout_uvag_eur_t), rel=1e-12)
        assert q == pytest.approx(D.crop_coef(cr, "N", a, "pool_kg_ha") / float(R.pool_scale), rel=1e-9), r
        it = sr[r].eaa["items"].set_index(["side", "item"])
        L = float(sr[r].activities[a])
        mann = sum(float(d["MANN"][0]) * float(sr[r].activities.get(c, 0.0)) for c, d in fo.items() if "MANN" in d)
        z = sr[r].technology_mix or {}
        _f, fom = I.crop_residue_nutrients(m)
        mann += sum(float(d.get("MANN", 0.0)) * float(z.get(c, 0.0)) for c, d in fom.items())
        assert it.loc[("O", "MANN"), "GROF"] == pytest.approx(0.001 * mann, rel=1e-12), r
        t_ha = DATA_TOOU_FOUT([v[0] for v in fo[a].values()], [v[1] for v in fo[a].values()])
        assert t_ha > 0 and L > 0


def test_the_fodder_crops_output_at_capris_uvag_foddo(solved3):
    """K213: a fodder crop's output at the solution is CAPRI's UVAG(FODDO) = PSHW x (1 - p_onFarmShare) per t produced
    (reports/sol_simy.gms l. 753), p_onFarmShare the member state's (SEDF + SEDM + LOSF) / GROF of CAPRI's data
    (supply/pmp.gms l. 41-49; fodder_onfarm_share_<year>.csv); the income's MGVA of the crop holds it in place of the
    margin's output at its producer price, and the account's output item is the same value."""
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
    from capri_mod.data.definitions import capri_ms
    from capri_mod.income import IncomeDistributionModule as I
    from capri_mod.projection.prices import FODDER_PRODUCT
    from capri_mod.supply import inputs as _inputs
    t = _inputs.current().csv(f"fodder_onfarm_share_{_inputs.current().base_year}.csv", "feed")
    share = {(str(a), str(b)): float(c) for a, b, c in zip(t.ms, t["product"], t.onfarm_share)}
    g = _inputs.current().csv("grass_dm_content.csv", "supply").set_index("region")["drma"]
    sm, sr, regs = solved3
    n = 0
    for r in regs:
        m = sm._models[r]
        fod = I.crop_fodder_output(r, m)
        assert fod, r
        it = sr[r].eaa["items"].set_index(["side", "item"])
        for c, (tou, rev, pshw, s) in fod.items():
            assert s == share.get((capri_ms(r), FODDER_PRODUCT.get(c, c)), 0.0)
            assert rev == pytest.approx(float(m.revenues[c]), rel=1e-12)
            y_ = float(m.data.yields[c])
            assert rev == pytest.approx(y_ * float(m.data.producer_prices[c]), rel=1e-12)   # the margin's output
            dm = float(g[r]) if FODDER_PRODUCT[c] == "GRAS" else 1.0                       # CAPRI's YILD, fresh
            assert tou == pytest.approx(y_ / dm * pshw * (1.0 - s), rel=1e-9), (r, c)
            # at the base year CAPRI's form is the margin's output to within 11% (crop_fodder_output's docstring)
            assert 0.85 < tou / rev < 1.12, (r, c)
            L = float(sr[r].activities.get(c, 0.0))
            if L > 0 and not (sr[r].technology_mix or {}).get(c):
                v = sr[r].income["MGVA_act"][c]
                assert it.loc[("O", c), "EAAG"] == pytest.approx(tou * L / 1000.0, rel=1e-9), (r, c)
                if c not in I.crop_toin_y(r, m):          # the margin with the residues and the fodder (DATA_MGVA)
                    d_ = I.crop_residue_nutrients(m)[0].get(c) or {}
                    t_ = DATA_TOOU_FOUT([q for q, _ in d_.values()], [u for _, u in d_.values()])
                    assert v == pytest.approx(float(m.net_revenues[c]) + t_ + tou - rev, rel=1e-12), (r, c)
                    n += 1
    assert n > 3


def test_DATA_UVAG_FODDO_and_p_onFarmShare_at_capris_2030_reference():
    """CAPRI's 2030 reference (sim_ini_21730, dataOut: a check only): Denmark's other arable fodder, p_onFarmShare
    (SEDF + SEDM + LOSF) / GROF = 0.62389 at 2030 (fodder_onfarm_share_2030.csv) and PSHW 49.6941 give UVAG(OFAR) =
    18.690, CAPRI's 18.69; the straw's form 0.9 LOSF / GROF of the region."""
    import pandas as pd
    from pathlib import Path
    from capri_mod.coupling.equations.sol_simy import DATA_UVAG_FODDO
    from capri_mod.supply.equations.pmp import p_onFarmShare
    root = Path(__file__).resolve().parents[2] / "capri_data"
    t = pd.read_csv(root / "baselines" / "capri_greendeal_ref" / "1730" / "feed" / "fodder_onfarm_share_2030.csv")
    s = float(t[(t.ms == "DK000000") & (t["product"] == "OFAR")].onfarm_share.iloc[0])
    assert s == pytest.approx(0.62389, abs=5e-6)
    assert DATA_UVAG_FODDO(49.6941, s) == pytest.approx(18.69, abs=5e-3)
    assert DATA_UVAG_FODDO(49.6941, s, FODDMARKUP=1.0) == pytest.approx(DATA_UVAG_FODDO(49.6941, s) + 1.0)
    assert p_onFarmShare("OFAR", 1.0, 2.0, 3.0, 12.0) == pytest.approx(0.5)
    assert p_onFarmShare("OFAR", 1.0, 2.0, 3.0, 0.0) == 0.0
    assert p_onFarmShare("STRA", 9.0, 9.0, 9.0, 9.0, LOSF_STRA_RS=2.0, GROF_STRA_RS=10.0) == pytest.approx(0.18)
    assert ((t.onfarm_share >= 0) & (t.onfarm_share < 1)).all()


@pytest.mark.slow
def test_the_income_and_the_account_at_a_shocked_solution(data):
    """After a solve with a price shock and the Green Deal's organic and pesticide targets the income takes the
    solve's own net revenues (res.nr_solve: the solve restores net_revenues to their state before it), and the gross
    account by item holds the solve's changes of the margins (the yields' changes, the input changes: ev.nr_items), so
    it equals the activity-based income but for the input cost table's unit values (as at the base)."""
    from capri_mod.data.definitions import CROPS
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    r = "DE110000"
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    # twice at base: the regional NLP is calibrated at its second solve (test_capri.py
    # test_solve_leaves_no_state_behind), so the shocked solve below responds to its shock
    sm.run(price_signals=None, regions=[r])
    sm.run(price_signals=None, regions=[r])
    m = sm._models[r]
    a0 = m.res.nr_solve.copy()
    ps = pd.Series(0.0, index=m.net_revenues.index)
    ps[[a for a in ("SWHE", "BARL", "MILK", "DCOW") if a in ps.index]] = 0.2
    sr = sm.run(price_signals=ps, policy_scenario={"organic_area_target": 0.25, "pesticide_reduction": 0.5},
                regions=[r])
    ip, e = sr[r].income, sr[r].eaa
    nr = m.res.nr_solve
    assert not np.allclose(nr.values, m.net_revenues.values)            # the solve's margins are not the restored ones
    assert float(nr["SWHE"]) > float(a0["SWHE"])                          # the price shock is in them
    from capri_mod.coupling.equations.calc_inc_indic import DATA_TOOU_FOUT
    from capri_mod.income import IncomeDistributionModule as I
    toin = I.crop_toin_y(r, m)
    fo, _fom = I.crop_residue_nutrients(m)
    fod = I.crop_fodder_output(r, m)
    n_crops = 0
    for a, v in ip["MGVA_act"].items():
        if a in CROPS and a not in toin:            # a crop's MGVA is its margin at the solve with its residues (DATA_MGVA)
            t_ = DATA_TOOU_FOUT([q for q, _ in (fo.get(a) or {}).values()], [u for _, u in (fo.get(a) or {}).values()])
            f_ = fod[a][0] - fod[a][1] if a in fod else 0.0      # and a fodder crop's output at UVAG(FODDO) (K213)
            assert v == pytest.approx(float(nr[a]) + t_ + f_, rel=1e-12), a
            n_crops += 1
    assert n_crops > 5
    assert e["MGVA"] == pytest.approx(e["TOOU"] - e["TOIN"] + e["PRME"], rel=1e-12)
    assert abs(e["DIFF"]) <= 1e-5 * abs(e["AGGT"]), e["DIFF"]
    assert max(abs(v) for v in e["DIFF_act"].values()) <= 1e-5 * abs(e["AGGT"])


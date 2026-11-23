"""NUTNED_'s additive need factor (register DEP-10 item 1b): CAPRI fixes v_cropNutNeedMultFact and
v_cropNutNeedAddFact in simulation (supply/prep_sim.gms l. 30-31), and fert/fertned.gms moves DATA(crop, FNUT) alone,
so the part of the need that v_cropNutNeedAddFact carries does not follow the yields (supply/supply_model.gms
l. 1095-1125; capri_mod/supply/equations/supply_model/nutrients.py NUTNED_needYieldFactor; the data's add_share,
tools/build/build_npk_balance_2030.py)."""
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.supply.equations.supply_model.nutrients import NUTNED_needYieldFactor

ROOT = Path(__file__).resolve().parents[2]
COEFS = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "npk_crop_coefs_2030.csv"
FACTORS = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "sim_ini_21730" / "crop_nut_need_factors_2030.parquet"
LEGSH = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "legsh_option.csv"


def test_the_need_factor_holds_the_additive_part():
    """need(y) / need(y0) = (1 - s) r + s, r = DATA(crop, FNUT)'s factor of the yields, s the additive part's share:
    the base unchanged, the whole need moving without an additive part, none moving when it is all additive, and no
    need without DATA (the SQRT term's $ condition takes the additive part too)."""
    assert NUTNED_needYieldFactor(1.0, 0.04) == pytest.approx(1.0)
    assert NUTNED_needYieldFactor(0.9, 0.0) == pytest.approx(0.9)
    assert NUTNED_needYieldFactor(0.9, 1.0) == pytest.approx(1.0)
    assert NUTNED_needYieldFactor(0.9, 0.04) == pytest.approx(0.96 * 0.9 + 0.04)
    assert NUTNED_needYieldFactor(0.0, 0.04) == 0.0
    # CAPRI's lhs per ha: (D x (1 - b) x k + a) x Q, D moved by r
    D, b, k, a, Q = 180.0, 0.0, 0.95, 4.7, 0.98
    s = a * Q / ((D * (1 - b) * k + a) * Q)
    r = 1.08
    assert ((r * D * (1 - b) * k + a) * Q) / ((D * (1 - b) * k + a) * Q) == pytest.approx(NUTNED_needYieldFactor(r, s))


def test_the_additive_share_in_the_data():
    """The data's add_share: CAPRI's v_cropNutNeedAddFact x DEFR x SQRT(...) x (1 + p_technFact) over the crop's need per
    ha at CAPRI's solution. The need factors are sim_ini_21730's (the same as the legume share's table, built from sim_ini
    on its own). The factor Q = add_share x need / add, over the grassland split's SQRT(1 +- 0.2), is CAPRI's DEFR x the
    mean technology's terms: for P and K (no DEFR) 1.015 for every arable crop and 1 for grassland in every region, so
    mean technology's terms: for P and K (no DEFR) 1 for grassland, 1.015038 (= SQRT(1.0303), not traced to its
    p_technFact) for the cereals, oilseeds, root crops, fodder and the permanent crops in every region, and between the
    two where a group mixes crops with and without it (vegetables, industrial crops: the group's factor, within 1.5% of
    each crop's additive part); for N DEFR on top. No additive part without a need (fallow, set-aside: K185)."""
    f = pd.read_parquet(FACTORS)
    assert len(f) == 750 and set(f.fnut) == {"NITF", "PHOF", "POTF"}
    ls = pd.read_csv(LEGSH, float_precision="round_trip").set_index("region")
    fn = f[f.fnut == "NITF"].set_index("region")
    common = ls.index.intersection(fn.index)
    assert len(common) > 100
    assert (fn.loc[common, "mult"] - ls.loc[common, "mult_fact_nitf"]).abs().max() < 1e-9
    assert (fn.loc[common, "add"] - ls.loc[common, "add_fact_nitf"]).abs().max() < 1e-9
    c = pd.read_csv(COEFS, float_precision="round_trip")
    assert c.add_share.notna().all() and (c.add_share < 0.6).all() and (c.add_share > -0.01).all()
    assert (c[c.model_crop.isin(["FALL", "VSET"])].add_share == 0.0).all()
    fnut = {"N": "NITF", "P": "PHOF", "K": "POTF"}
    add = {(r, n): v for r, n, v in zip(f.region, f.fnut, f["add"])}
    w = c[(c.need_kg_ha > 10) & (c.add_share > 0)]
    w = w[[(r, fnut[n]) in add and add[(r, fnut[n])] > 0.1 for r, n in zip(w.capri_region, w.nutrient)]].copy()
    g = {"GRAI": 1.2 ** 0.5, "GRAE": 0.8 ** 0.5}
    w["Q"] = [s * nd / add[(r, fnut[n])] / g.get(m, 1.0)
              for s, nd, r, n, m in zip(w.add_share, w.need_kg_ha, w.capri_region, w.nutrient, w.model_crop)]
    pk = w[w.nutrient != "N"]
    gras = pk.model_crop.isin(["GRAE", "GRAI"])
    assert len(pk) > 10000 and gras.sum() > 900
    assert (pk[gras].Q - 1.0).abs().max() < 1e-9
    one = pk.model_crop.isin(["SWHE", "BARL", "CORN", "RAPE", "SUGB", "POTA", "OFAR", "MAIF", "APPL", "WINE"])
    assert one.sum() > 4000 and (pk[one].Q - 1.015038).abs().max() < 1e-5
    assert pk.Q.between(1.0 - 1e-9, 1.01505).all()
    assert w[w.nutrient == "N"].Q.between(0.7, 1.05).all()
    # Picardie (FR22) soft wheat: the additive part a few percent of the need
    sw = c[(c.capri_region == "FR220000") & (c.model_crop == "SWHE")].set_index("nutrient").add_share
    assert 0.0 < sw["N"] < 0.1

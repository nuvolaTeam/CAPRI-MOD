"""CAPRI's crop technologies as mix columns (docs/dev/CROP_TECHNOLOGY_MIX_COLUMNS.md): the data and the PMP transform."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SUP = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply"      # the 2030 files (DATA_LAYOUT step (b))


def _read(name):
    return pd.read_csv(SUP / name, float_precision="round_trip")


def test_mix_tables_cover_the_same_crops_and_carry_capri_factors():
    tm, pm = _read("techn_mix_2030.csv"), _read("pmp_capri_2030_mix.csv")
    assert set(zip(tm.region, tm.activity)) == set(zip(pm.region, pm.activity))
    # one row per region and crop with both technologies in CAPRI's PMP data (5,417 at 2030)
    assert len(tm) == 5417 and not tm.duplicated(["region", "activity"]).any()
    # FALL has its T2 in 24 regions only (the decision of 7 November 2026: a column only there)
    assert (tm.activity == "FALL").sum() == 24
    crops = tm[tm.yield_diff != 0]
    assert np.allclose(crops.yield_diff, 0.4)
    g = lambda y: math.sqrt(1 + y) * (1 + y)                    # NUTNED_: SQRT(1 + y) x (1 + y)
    assert np.allclose(crops.need_diff, (g(0.2) - g(-0.2)) / ((g(0.2) + g(-0.2)) / 2))
    # 0 where CAPRI's data have no such input for the crop (techf.gms sets the factor on PACT_TO_I only)
    assert set(crops.plap_diff.round(12)) <= {0.0, 0.8} and set(crops.inpo_diff.round(12)) <= {0.0, 0.5}
    assert (crops.plap_diff == 0.8).mean() > 0.9
    # T1 gets less of the technology-differentiated premiums (rd_logic.gms: -0.5 / +0.5, N2K -1 / +1)
    assert (tm.prem_diff_share <= 0).all() and (tm.prem_diff_share >= -2).all()
    assert (tm.rest_cost_diff_eur_ha >= 0).all()
    # the crop residues' N, P2O5, K2O move with the yield (p_technFact MANN, MANP, MANK +-0.2; K181), 0 where CAPRI's
    # data give the crop no such factor
    for c in ("mann_diff", "manp_diff", "mank_diff"):
        assert set(crops[c].round(12)) <= {0.0, 0.4} and (crops[c] == 0.4).mean() > 0.95, c
    assert (pm.g_zz >= 0).all() and (pm.g_xx_extra >= 0).all()


def test_mix_pmp_terms_reproduce_the_collapsed_curvature():
    """The mix columns' PMP block is CAPRI's technology block in (X, z): X's curvature with z optimised out (the
    Schur complement) is the collapsed curvature the model uses without the columns."""
    spec = importlib.util.spec_from_file_location("bpc", ROOT / "tools" / "build" / "build_pmp_capri_2030.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from capri_mod.tests._sources import read_source
    techn = read_source(ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "pmp_quad_techn_2030.parquet",
                        float_precision="round_trip")
    n = 0
    for region in ("DE110000", "FR240000", "RO040000", "ES610000"):
        terms = mod.mix_terms(region, techn)          # asserts the Schur identity per crop
        t = techn[(techn.region == region) & techn.tech1.isin(["T1", "T2"])]
        for act, (dxx, xz, zz) in terms.items():
            b = t[t.activity == act]
            Qt = np.zeros((2, 2))
            for r in b.itertuples():
                Qt[int(r.tech1[1]) - 1, int(r.tech2[1]) - 1] = r.value
            Qt = np.where(Qt == 0.0, Qt.T, Qt)
            c = 1.0 / float(np.ones(2) @ np.linalg.solve(Qt, np.ones(2)))
            QXX = (Qt[0, 0] + 2 * Qt[0, 1] + Qt[1, 1]) / 4
            assert abs((QXX - c) - dxx) <= 1e-9 * abs(c)
            assert math.isclose(zz, Qt[0, 0] - 2 * Qt[0, 1] + Qt[1, 1], rel_tol=1e-12)
            assert math.isclose(xz, (Qt[0, 0] - Qt[1, 1]) / 2, rel_tol=1e-12, abs_tol=1e-12)
            n += 1
    assert n > 50


@pytest.fixture(scope="module")
def es42_greendeal():
    """ES42 alone, the Green Deal 2030 step from CAPRI's 2030 reference: (the projection's result, the region's
    supply model after the scenario's solve)."""
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import BaselineTrajectory, ProjectionModule
    from capri_mod.data.inputs import trajectories_dir
    from capri_mod.policy.endotech import effective
    from capri_mod.scenarios import definition
    R = "ES420000"
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    traj = BaselineTrajectory.from_file(str(ROOT / "capri_data" / "scenarios" / "capri_ref_2030"))
    pmod = ProjectionModule(m, traj, capri_prices_dir=str(trajectories_dir(ROOT / "capri_data", 2030)))
    scen = definition.to_policy_scenario(definition.load("greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00"))
    scen.endotech = effective(scen.endotech)
    res = pmod.run(policy_scenario=scen, years=[2030], regions=[R])
    return res, (getattr(pmod, "_last_projected_model", None) or m).supply_module._models[R]


@pytest.mark.slow
def test_mix_columns_move_to_the_low_yield_technology(es42_greendeal):
    """The mix column z of a crop (x_T1 = X/2 + z, x_T2 = X/2 - z) is bounded by its two rows alone, -X/2 <= z <= X/2:
    z < 0 is the shift to CAPRI's low-yield technology T2, the Green Deal's main lever on the crops' N need (CAPRI's ES42
    reference -> Green Deal: N need per ha -42% grass, -23% rape, -11% maize). Until 15 November 2026 the regional NLP's
    default lower bound 0 held every z at or above the calibration point (KNOWN_ISSUES K155); in Castilla-La Mancha
    the Green Deal then left sunflower and pulses at their 0.1 x base floor (CAPRI +15% and +24%). ES42 alone, the
    Green Deal 2030 step from CAPRI's 2030 reference."""
    R = "ES420000"
    res, rm = es42_greendeal
    z = dict(getattr(rm.res, "last_mix_z", None) or {})
    assert z and min(z.values()) < -1.0, z                       # thousand ha moved from T1 to T2
    base, scn = (res.baseline[2030]["supply"][R].activities, res.scenario[2030]["supply"][R].activities)
    for a in ("SUNF", "PULS", "BARL"):                           # CAPRI: +15%, +24%, -1%
        assert float(scn[a]) > 0.6 * float(base[a]), (a, float(base[a]), float(scn[a]))


@pytest.mark.slow
def test_residue_pool_follows_the_technology_mix(es42_greendeal):
    """CAPRI's residue pool (fertDistCres_, supply_model.gms l. 1049-1085) distributes the residues of every crop and
    technology, v_actLevl(c, A) x DATA(c, MANN) x (1 + p_technFact(c, MANN, A)), with +-0.2 for T1 and T2 (MANP, MANK
    for P2O5 and K2O): a crop's mix column z (ha moved from T2 to T1) brings 0.4 x its residues per ha. Until K181
    (18 November 2026) the model's pool had the crops' columns alone, so under the Green Deal (z < 0) its crops kept
    the residue N CAPRI's lose with the shift to T2 (ES42 at CAPRI's prices: 2.6 kt N). At the Green Deal's solution
    the residues the NLP distributes equal the crops' residues at their mean technology, plus the catch crops' N."""
    R = "ES420000"
    res, rm = es42_greendeal
    z = dict(getattr(rm.res, "last_mix_z", None) or {})
    scn = res.scenario[2030]["supply"][R].activities
    tm = pd.read_csv(SUP / "techn_mix_2030.csv", float_precision="round_trip")
    tm = tm[tm.region == R].set_index("activity")
    co = pd.read_csv(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment"
                     / "npk_crop_coefs_2030.csv", float_precision="round_trip")
    co = co[co.capri_region == R]
    cover = dict(getattr(rm.res, "cover_solved", None) or {})
    npk = rm.res.last_npk
    for nut, col in (("N", "mann_diff"), ("P", "manp_diff"), ("K", "mank_diff")):
        pool = co[co.nutrient == nut].set_index("model_crop").pool_kg_ha
        crops = float(sum(float(scn.get(a, 0.0)) * float(v) for a, v in pool.items() if v > 0))        # t
        mix = float(sum(z[a] * float(tm.at[a, col]) * float(pool[a]) for a in z if a in pool.index and pool[a] > 0))
        catch = 1000.0 * float(cover["delta"]) * float(cover["biofix"]) if nut == "N" else 0.0
        dist = sum(v for (g, s), v in npk[nut]["flows"].items() if s == "CRES")
        assert mix < -0.01 * crops, (nut, mix, crops)        # the shift to T2 takes residues out
        assert math.isclose(dist, crops + mix + catch, rel_tol=1e-6), (nut, dist, crops, mix, catch)

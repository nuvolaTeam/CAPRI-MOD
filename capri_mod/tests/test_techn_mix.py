"""S1, CAPRI's crop technologies as mix columns (docs/design/S1_MIX_COLUMNS.md): the data and the PMP transform."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SUP = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "2017_2030" / "supply"      # the 2030 files (DATA_LAYOUT step (b))


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

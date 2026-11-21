"""The animals' herd PMP terms in the model's heads (tools/build/build_animal_pmp_capri_2030.py; KNOWN_ISSUES K173)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def _builder():
    spec = importlib.util.spec_from_file_location("build_animal_pmp_capri_2030",
                                                  ROOT / "tools" / "build" / "build_animal_pmp_capri_2030.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bull_and_heifer_terms_convert_with_the_ratios_own_capri_level():
    """CAPRI's PMP terms sit on its model activities (BULL, BULH; HEIL, HEIH, HEIR), the model's heads per CAPRI level
    (capri_level_ratio.csv) on its database activities BULF and HEIF + HEIR, whose levels are not the members' sum
    (DE21 2030: BULF 40.4 against BULL + BULH 66.1 thousand). The term per head converts with that level over the
    members': g = h X / (r f), f = BULF / (BULL + BULH); 1 for an animal whose ratio is on its own members."""
    mod = _builder()
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    import _money
    t = pd.read_parquet(ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp" / "pmp_quad_techn_2030.parquet")
    t = t[(t.region == "DE210000") & (t.tech1 == "T") & (t.tech2 == "T")]
    Q = {r.activity: float(r.value) for r in t.itertuples()}
    k = pd.read_parquet(ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refdefaulta"
                        / "capri_ref_levl_yild_2030_2017.parquet")
    k = k[(k.capri_region == "DE210000") & (k.item == "LEVL") & (k.year.astype(str) == "2030")]
    lv = {r.activity: float(r.value) for r in k.itertuples()}
    g = pd.read_csv(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply"
                    / "pmp_capri_2030_animals_members.csv").set_index(["region", "animal"])
    money = _money.deflator(2030)
    for animal, basis in mod.BASIS.items():
        h, X = mod.herd_curvature(Q, lv, mod.MEMBERS_SPLITS[animal])
        f = sum(lv[b] for b in basis) / X
        row = g.loc[("DE210000", animal)]
        assert abs(float(row["x_capri"]) - X) < 1e-9 * X
        assert abs(float(row["g"]) - h * X / (float(row["level_ratio"]) * f) / money) < 1e-9 * float(row["g"])
        assert f < 0.9                                   # BULF 0.61, HEIF + HEIR 0.70 of the members' level
    h, X = mod.herd_curvature(Q, lv, mod.MEMBERS_SPLITS["DCOW"])
    row = g.loc[("DE210000", "DCOW")]
    assert abs(float(row["g"]) - h * X / float(row["level_ratio"]) / money) < 1e-9 * float(row["g"])

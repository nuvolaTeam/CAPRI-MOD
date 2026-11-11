"""CAPRI's conversion of GLOBIOM-EU's projections into long-run change factors (capri_mod/pipeline/captrd/globiom.py:
global/convert_globiom.gms, GLOBIOM-EU branch, and global/create_longrun_info.gms), run on GLOBIOM-EU's EUCLIMIT6 file
(GLOBIOM-EU_EUCLIMIT6_S2_50CV.gdx) and compared with CAPRI's results of that file: p_globiomInfo of
results/global/GLOBIOM_EU_longrun_defaulta.gdx and p_longRunInfoAll of longrun_info_fac_defaulta.gdx (its scenario
GLOBIOM_EU_EUCLIMIT6_S2_50CV). With the settings of the GLOBIOM-EU files of 2023-2025 the EUCLIMIT6 and Brightspace
branches of convert_globiom.gms are the same but for the input file and the scenario lines (l. 277-286), so this
also checks the conversion of the Brightspace file.

Results on 11 November 2026: the same 452,241 records as p_longRunInfoAll, and 447,390 as p_globiomInfo without Taiwan (TAW,
replaced by China's records in p_longRunInfoAll, create_longrun_info.gms l. 200); all equal but 128 of the base year 2017's change factors from B2000 (90 of population, INHA.LEVL;
38 of DOMM, all Switzerland's), which come from CAPRI's global database and UN population, not from GLOBIOM:
our files of those (fao_agg_17_defaulta, allpop) are not the versions that run used (e.g. Portugal's population
1999-2001 to 2016-2018: ours 1.0097, the run's 0.9993; Switzerland has no DOMM in our p_dataMarket).
"""
from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE, SOURCES
from capri_mod.pipeline.captrd import globiom as GL
from capri_mod.pipeline.captrd import prepare as P

DAT = P.SETS_DIR.parent / "dat"
PQ = SOURCES / "dat_parquet"
EU6 = "GLOBIOM_EU_EUCLIMIT6_S2_50CV"
need = pytest.mark.skipif(not ((PQ / "global" / "GLOBIOM-EU_EUCLIMIT6_S2_50CV").exists()
                               and (PQ / "capreg" / "res_time_series_17AT").exists()
                               and (REFERENCE / "globiom" / "GLOBIOM_EU_longrun_defaulta").exists()),
                          reason="GLOBIOM-EU, CAPREG time series or CAPRI's conversion not converted to Parquet")


def _ref(path, scenario=None):
    r = pd.read_parquet(path)
    if scenario:
        r = r[r.d5.str.upper() == scenario.upper()]
    return {(a.upper(), b.upper(), c.upper(), d.upper(), f.upper()): v
            for a, b, c, d, f, v in zip(r.d1, r.d2, r.d3, r.d4, r.d6, r.value)}


@pytest.mark.slow
@need
def test_globiom_conversion_equals_capris():
    out = GL.longrun_info_all(EU6, sets_dir=P.SETS_DIR / "globiom", capri_sets_dir=P.SETS_DIR / "globiom",
                              dat_dir=DAT, globiom_root=PQ / "global", capreg_root=PQ / "capreg",
                              datamarket=PQ / "global" / "fao_agg_17_defaulta" / "p_dataMarket.parquet",
                              worldpop=PQ / "arm" / "allpop" / "worldPop.parquet")
    mine = {(r, c, w, i.upper(), str(y)): v for (r, c, w, i, s, y), v in out.items()}
    for name, ref in (("p_longRunInfoAll", _ref(PQ / "global" / "longrun_info_fac_defaulta" / "p_longRunInfoAll.parquet",
                                                 EU6)),
                      ("p_globiomInfo", _ref(REFERENCE / "globiom" / "GLOBIOM_EU_longrun_defaulta" /
                                             "p_globiomInfo.parquet"))):
        if name == "p_globiomInfo":                            # TAW: its own conversion, replaced by CHN's after it
            ref = {k: v for k, v in ref.items() if k[0] != "TAW"}
        m = {k: v for k, v in mine.items() if name == "p_longRunInfoAll" or k[0] != "TAW"}
        keys = set(m) | set(ref)
        bad = [k for k in keys if abs(m.get(k, 0.0) - ref.get(k, 0.0)) > 1e-6 * max(abs(ref.get(k, 0.0)), 1e-9)]
        print(name, len(keys), "equal", len(keys) - len(bad), Counter((k[1], k[3], k[4]) for k in bad).most_common(5))
        assert len(keys) > 447000 and set(m) == set(ref)
        assert all(k[3] == "FACTORB2000" and k[4] == "2017" and k[1] in ("INHA", "DOMM") for k in bad)
        assert len(bad) <= 130


@pytest.mark.slow
@need
def test_brightspace_conversion_runs():
    """The reference run's selection (no CAPRI conversion of it to compare with): the conversion runs and gives the
    long-run factors longrun_supports.gms reads (the member states' production factors among them)."""
    sc = "globiom_eu_bright_s0_2023+REFERENCE+REFERENCE"
    out = GL.longrun_info_all(sc, sets_dir=P.SETS_DIR / "globiom", capri_sets_dir=P.SETS_DIR / "globiom",
                              dat_dir=DAT, globiom_root=PQ / "global", capreg_root=PQ / "capreg",
                              datamarket=PQ / "global" / "fao_agg_17_defaulta" / "p_dataMarket.parquet",
                              worldpop=PQ / "arm" / "allpop" / "worldPop.parquet")
    n = Counter(i for (r, c, w, i, s, y) in out)
    print(sc, len(out), dict(n))
    assert {s for (r, c, w, i, s, y) in out} == {sc}
    assert len(out) > 400000 and n["factorB2000"] > 150000
    assert out.get(("DE000000", "PROD", "SWHE", "factorB2000", sc, 2030), 0.0) > 0

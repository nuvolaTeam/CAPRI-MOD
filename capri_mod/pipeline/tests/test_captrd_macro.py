"""The population path of CAPTRD (capri_mod/pipeline/captrd/macro.py: baseline/load_aglink2023dgAgri.gms l. 905-1068,
captrd/longrun_supports.gms l. 368-389) on Aglink 2023's macro data, SSP2 and the UN population, compared with
INHA.LEVL of CAPTRD's stored P_Data in the years after BAST.

Results on 11 November 2026: all 350 values (the 35 regions, 2019 and the ex-ante years from 2020) equal to CAPTRD's.
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE, SOURCES
from capri_mod.pipeline.captrd import aglink as A
from capri_mod.pipeline.captrd import macro as M
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import timesets as TS

R = REFERENCE / "captrd_results" / "1770"
G = REFERENCE / "sets" / "simini_21730"
SP = SOURCES / "dat_parquet" / "baseline"
DAT = P.SETS_DIR.parent / "dat"
EXANTE = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
need = pytest.mark.skipif(not ((R / "P_Data.csv.gz").exists() and (SP / "aglink2023dgAgri_oriEUdata").exists()),
                          reason="CAPRI reference files not built")


@pytest.mark.slow
@need
def test_population_equals_captrds():
    s = P.read_sets()
    T = TS.build(1984, 2070, EXANTE, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    AS = A.Sets(G)
    ori = A.read_aglink(SP / "aglink2023dgAgri_oriEUdata", SP / "AGLINK2019dgagri_oridata", AS)
    pop = {(k[0], int(k[3])): v for k, v in ori.items() if k[1] == "POP" and k[2] == "ME" and str(k[3]).isdigit()
           and v == v}
    sets, mac, ssp = M.read_inputs(P.SETS_DIR, DAT)
    fao = pd.read_csv(G / "FAORegions_map.csv", dtype=str, keep_default_na=False)
    years = list(range(1984, 2071))
    m = M.inha(sets, mac, ssp, aglink_pop=pop, ag_eu_regs=AS.agEUreg, ag_years=[int(y) for y in AS.agYears],
               years=years, lst_dgagri=T.lst_dgagri, last_sim_year=2070, fao_map=list(zip(fao.d0, fao.d1)),
               base_year=2017)
    pdd = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    inha = pdd[(pdd.col == "INHA") & (pdd.row == "LEVL")]
    basm = dict(zip(inha[inha.t == "BASM"].region, inha[inha.t == "BASM"].value))
    wp = pd.read_csv(DAT / "macro_worldpop.csv")
    ms = list(s.ms)
    out = M.inha_pdata(m, ms=ms, basm=basm, years_cur=[y for y in years if y in set(T.expostt) | set(T.exante)],
                       bast_year=T.lst_expostt - 1, exante=T.exante,
                       world_pop={(y, r): v for y, r, v in zip(wp.year, wp.region, wp.value)}, basy=2017)
    ref = inha[inha.t.str.isdigit() & inha.region.isin(ms)]
    ref = ref[ref.t.astype(int) > T.lst_expostt - 1]
    c = pd.DataFrame({"ref": ref.value.values, "mine": [out.get((r, int(t)), 0.0) for r, t in
                                                       zip(ref.region, ref.t)]}, index=list(zip(ref.region, ref.t)))
    c["ok"] = (c.mine - c.ref).abs() <= 1e-6 * c.ref.abs()
    print(len(c), int(c.ok.sum()))
    print(c[~c.ok].head(30).to_string())
    assert len(c) > 300 and c.ok.all()

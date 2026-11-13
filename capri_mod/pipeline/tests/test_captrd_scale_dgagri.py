"""Parity of CAPTRD's scaling of the DG AGRI baseline (capri_mod/pipeline/captrd/scale_dgagri.py;
captrd/scale_DG_AGRI_baseline.gms) with CAPTRD's own results_1770, chained to the Aglink stage
(test_captrd_aglink.py's DGAgri) and on CAPTRD's stored P_Data as p_data.

Two inputs differ from CAPTRD's state at this point, as its own results show:
  - the population INHA.LEVL after CAPREG's years (2019 on) is in the stored P_Data but not yet in p_data here: CAPTRD's
    HCOM.LEVL of DGAgri (l. 170-174, per-head consumption x population) exists only for 2000-2018; the later years
    are written to the stored position by define_stats_and_supports.gms l. 97. The test drops them from the input.
  - a few p_data values used for BAST/BAST2 differ from the stored P_Data (removed or changed by a later stage, not
    traced): the factors CAPTRD applied imply them (residuals below).

Compared (10 November 2026):
  - DGAgri as this stage leaves it (the yields moved to the products, BAST, BAST2, the EU parts' net of their members,
    human consumption): every record equal but 2 (HCOM.HFCS BAST2 of the EU parts: the p_data base), once the later
    stages' writes are left out (the region EU and DEMD: aggreg_and_report.gms; the growth rates "grate":
    expert_support.gms l. 443-461; the YILD rows: not written by this file, not traced);
  - DGAgri1 of the years define_EU_supports.gms does not rewrite (it rewrites the member states' and the EU parts'
    ex-ante years, l. 86-450), the reporting aggregates left out (aggreg_and_report.gms l. 94, 102, EU013000
    among them): the member states
    and Norway, Turkey and the UK equal but 57 records (NO000000 EXPT.BUTT, which the stored P_Data lacks; HCOM.HFCS
    of TUR and UK000000, whose factor implies a 2018 value the stored P_Data lacks); the EU part EU014000 equal
    but the (column, row) groups whose ratio to CAPTRD's is constant in every year (the factor's base,
    p_data's BAST2, differs) and their DOMM (recomputed from the components, l. 430-433).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import scale_dgagri as S
from capri_mod.pipeline.captrd import timesets as TS
from capri_mod.pipeline.tests.test_captrd_aglink import dgagri, need  # noqa: F401  (the Aglink stage's fixture)

R = REFERENCE / "captrd_results" / "1770"
G = REFERENCE / "sets" / "simini_21730"
K = ["region", "col", "row", "t"]
EXANTE = ["2018", "2020", "2025", "2030", "2035", "2040", "2045", "2050", "2060", "2070"]
EU_PARTS = {"EU014000"}
#: aggreg_and_report.gms l. 49-52 and 94, 102 rewrite the reporting aggregates' DGAgri1 as their members' sum: rMEU,
#: WBA and %EU_EASTBUR%, which is EU013000 here (its ex-post DGAgri1 is absent from CAPTRD's results: its members
#: have none in those years)
AGGS = {"EU", "EU_EAST", "EU_WEST", "EU27YR19", "EU013000"}


def _frame(p):
    d = pd.DataFrame([(*k, v) for k, v in p.items()], columns=K + ["value"])
    for k in K:
        d[k] = d[k].astype(str).str.upper()
    return d


def _ref(name):
    d = pd.read_csv(R / f"{name}.csv.gz", dtype={"t": str})
    for k in K:
        d[k] = d[k].astype(str).str.upper()
    return d


@pytest.fixture(scope="module")
def scaled(dgagri):  # noqa: F811
    s = P.read_sets()
    sd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str).d0   # noqa: E731
    pdata = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    pdata = pdata[pdata.region.isin(set(s.ms))]
    yr = pd.to_numeric(pdata.t, errors="coerce")
    pdata = pdata[~((pdata.col == "INHA") & (pdata.row == "LEVL") & (yr > 2018))]
    resy = [int(y) for y in EXANTE]
    T = TS.build(1984, 2070, resy, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019),
                 expostt_extra=[2019])
    rto = pd.read_csv(G / "R_T_OAGG.csv", keep_default_na=False, dtype=str)
    return S.scale(pdata, dgagri, ms=s.ms, ragg=["EU014000", "EU013000"], top=["EU27yr19"], west=["EU014000"],
                   map_rr=s.map_rr, pact=pd.read_csv(G / "PACT.csv", keep_default_na=False, dtype=str).d0,
                   pact_to_y=s.pact_to_y, cols_est=s.s_colsest, rows_est=s.s_rowsest, mrkbalee=sd("mrkbalee"),
                   dompos=sd("dompos"), fuels=sd("fuels"), meas=rto[rto.d0 == "MEAS"].d1,
                   basyrst=T.basyrst, exante=T.exante, years_cur=T.years_cur, years=range(1984, 2071))


def _merge(mine, ref):
    m = mine.merge(ref[K + ["value"]], on=K, how="outer", suffixes=("", "_ref"), indicator=True)
    m = m.fillna({"value": 0.0, "value_ref": 0.0})
    m["ok"] = (m.value - m.value_ref).abs() <= 1e-6 * m.value_ref.abs().clip(lower=1e-6)
    return m


@pytest.mark.slow
@need
def test_dgagri_as_the_scaling_leaves_it(scaled):
    _, D, _ = scaled
    m = _merge(_frame(D), _ref("DGAgri"))
    m = m[(m.region != "EU") & (m.col != "DEMD") & (m.t != "GRATE") & (m.row != "YILD")]
    assert len(m) > 120_000                                          # 123,918 on 10 November 2026
    bad = m[~m.ok]
    assert set(zip(bad.region, bad.col, bad.row, bad.t)) <= {("EU013000", "HCOM", "HFCS", "BAST2"),
                                                             ("EU014000", "HCOM", "HFCS", "BAST2")}


@pytest.mark.slow
@need
def test_dgagri1_of_the_years_define_eu_supports_leaves(scaled):
    D1, _, _ = scaled
    m = _merge(_frame(D1), _ref("DGAgri1"))
    m = m[~m.t.isin(EXANTE) & ~m.region.isin(AGGS) & (m.col != "DEMD") & (m.row != "YILD")]
    ms = m[~m.region.isin(EU_PARTS)]
    assert len(ms) > 20_000
    bad = ms[~ms.ok]
    assert set(zip(bad.region, bad.col, bad.row)) <= {("NO000000", "EXPT", "BUTT"), ("TUR", "HCOM", "HFCS"),
                                                      ("UK000000", "HCOM", "HFCS")}
    eu = m[m.region.isin(EU_PARTS)]
    bad = eu[~eu.ok & (eu._merge == "both")].assign(ratio=lambda d: d.value_ref / d.value)
    spread = bad.groupby(["region", "col", "row"]).ratio.agg(lambda r: r.max() / r.min() - 1)
    assert (spread[spread.index.get_level_values("col") != "DOMM"] < 1e-9).all()
    assert (eu.ok | (eu._merge == "both")).all()                     # nothing missing on either side
    assert eu.ok.sum() > 3_000                                        # 3,189 of 3,527 on 10 November 2026

"""CAPTRD's expert supports as a whole, the years after 2018 (2018 is COCO's, test_captrd_coco_supports.py): the
ported sources chained in expert_support.gms's order (its own rules, the biofuel trends, DG AGRI's dairy data,
Eurostat's recent production, the national experts, the long-run sources), its end (the herd floor, TOOU) and
define_stats_and_supports.gms's storage (Expert from Absolute and PercentChange, HCOM.COMI, BIOF.SUGA without
production, the sugar beet trade, TrustLevl); compared with CAPTRD's Expert and TrustLevl of the member states.

Results on 11 November 2026: of the 39,567 positions of the member states in the years after 2018 (DEMD, the
reporting's copy of DOMM, and the positions the reporting adds without a trust level left out), 39,485 equal in value
and trust level. The other 82 are a later stage's or not in the stored results:
  - define_EU_supports.gms (stage 2f): the trust levels of NO000000's and TUR's market positions with DG AGRI targets
    (72) and its tiny BIOF.SUGA defaults of NO000000 and SI000000 (6);
  - CS000000's DOMM.COMI (4), whose support CAPTRD stores only as the reporting re-aggregate.
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import dairy_supports as D
from capri_mod.pipeline.captrd import expert_support as XS
from capri_mod.pipeline.captrd import longrun_supports as LR
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need, _ref, G, DAT)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401

K = ["region", "col", "row", "t"]


@pytest.mark.slow
@need
def test_expert_supports_equal_captrds(state, population, result):  # noqa: F811
    S0, prior, nat, X, s = state
    S = copy.deepcopy(S0)
    g = lambda n: pd.read_csv(G / f"{n}.csv", keep_default_na=False).d0.str.upper().tolist()   # noqa: E731
    d = _ref("data")
    nobs = set(map(tuple, d[d.t == "nObs"][["region", "col", "row"]].values))
    pto = pd.read_csv(G / "PACT_TO_O.csv", keep_default_na=False)
    C = LR.Context(
        ms=X.ms, msincl=X.ms, pdata=X.pdata, nobs=nobs, basm=X.basm, bast=X.bast, s_colsest=s.s_colsest,
        s_rowsest=s.s_rowsest, pact=g("PACT"), req_feed=g("REQ_FEED"),
        reqst=pd.read_csv(P.SETS_DIR / "reqst.csv").d0.tolist(), pact_to_y=X.pact_to_y,
        pact_to_o=list(zip(pto.d0.str.upper(), pto.d1.str.upper())),
        mrkbalee=pd.read_csv(P.SETS_DIR / "mrkbalee.csv").d0.tolist(), mlk_pro=g("MLKPRO"),
        cows_act=["DCOL", "DCOH", "SCOW"], exante=X.exante, exantet=X.exantet, expostt=X.expostt,
        years_cur=sorted(set(X.expostt) | set(X.exante)), base_year=X.base_year, bast_year=X.bast_year,
        lst_expost=X.lst_expost, lst_exante=X.lst_exante, lst_dgagri=X.lst_dgagri, phase_in=2025, infl=1.019,
        support=X.support, dgagri1=X.dgagri1, map_rr=X.map_rr, cur_europ_agg=["EU014000", "EU013000", "EU27yr19"],
        inha=population, longrun_info_all=LR.read_info(DAT))
    lr = LR.supports(S, C)
    sup = dict(X.support)
    XS.herd_floor(sup, ms=X.ms, maact=s.maact, bas=X.bas, bast=X.bast, exantet=X.exantet, base_year=X.base_year,
                  bast_year=X.bast_year, lst_exante=X.lst_exante)
    XS.toou(S, support=sup, basm=X.basm, ms=X.ms, s_colsest=s.s_colsest, exante=X.exante, pact_to_y=X.pact_to_y,
            longrun1=lr.longrun1)
    XS.check_duplicates(S)
    rest = list(X.ms)
    E = XS.expert(S, basm=X.basm, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, rest=rest)
    share = result[1]                                                          # define_stats l. 510-519
    H = D.hcom_expert(share, {(r, c, w, str(y)): v for (r, c, w, y), v in E.items() if c == "GROF" and w == "COMI"},
                      {(r, c, w, str(y)): v for (r, c, w, y), v in sup.items() if c == "GROF" and w == "COMI"},
                      rest, X.exantet)
    for (r, c, w, y), (v, t) in H.items():
        if v:
            E[(r, c, w, int(y))] = v
        S.put(S.tr, (r, c, w, int(y)), t)
    XS.biof_suga(E, rest=rest, exante=X.exante, exanted=[y for y in X.exante if y not in set(X.exantet)], nobs=nobs)
    XS.sugb_trade(E, sup, ms=X.ms, exante=X.exante, bast=X.bast, basm=X.basm)
    TL = XS.trust(E, coco_trust={}, expert_trust=S.tr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, rest=rest)
    yrs, msset = set(X.exantet), set(X.ms)
    ex, tl = _ref("Expert"), _ref("TrustLevl")
    RE = {(r, c, w, int(t)): v for r, c, w, t, v in zip(ex.region, ex.col, ex.row, ex.t, ex.value)
          if t.isdigit() and int(t) in yrs and r in msset and c != "DEMD"}
    RT = {(r, c, w, int(t)): v for r, c, w, t, v in zip(tl.region, tl.col, tl.row, tl.t, tl.value)
          if t.isdigit() and int(t) in yrs and r in msset}
    mine = {k: v for k, v in E.items() if k[0] in msset and k[3] in yrs}
    RE = {k: v for k, v in RE.items() if k in RT or k in mine}       # the reporting's derived positions left out
    rows = []
    for k in set(mine) | set(RE):
        a, b = mine.get(k, 0.0), RE.get(k, 0.0)
        okv = abs(a - b) <= 1e-6 * max(abs(b), 1e-9)
        okt = abs(TL.get(k, 0.0) - RT.get(k, 0.0)) < 1e-9 if (a and b) else True
        rows.append((*k, a, b, TL.get(k, 0.0), RT.get(k, 0.0), okv and okt))
    m = pd.DataFrame(rows, columns=K + ["mine", "ref", "tm", "tr", "ok"])
    bad = m[~m.ok]
    later = (m.region.isin(["NO000000", "TUR"]) & (m.mine != 0) & ((m.mine - m.ref).abs() <= 1e-6 * m.ref.abs())) | (
        (m.col == "BIOF") & (m.row == "SUGA") & (m.ref.abs() < 1e-12)) | (
        (m.region == "CS000000") & (m.col == "DOMM"))
    print("expert supports:", len(m), "equal", int(m.ok.sum()), "| a later stage's or not stored:",
          int((~m.ok & later).sum()), "| other:", int((~m.ok & ~later).sum()))
    print(bad[~later.loc[bad.index]].head(20).to_string())
    assert len(m) > 39500 and int(m.ok.sum()) > 39450 and int((~m.ok).sum()) < 90
    assert int((~m.ok & ~later).sum()) == 0

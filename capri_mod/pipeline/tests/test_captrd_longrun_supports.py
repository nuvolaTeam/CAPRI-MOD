"""CAPTRD's long-run supports (capri_mod/pipeline/captrd/longrun_supports.py; captrd/longrun_supports.gms) after the
national supports (the state of test_captrd_national_supports.py), with the long-run selection of the reference run
(globiom_eu_bright_s0_2023+REFERENCE+REFERENCE, absent from longrun_info_fac_defaulta.gdx) and the population path of
macro.py; compared with CAPTRD's stored B2000, Expert and TrustLevl.

Results on 11 November 2026: no Longrun or Longrun1 records, as in CAPTRD's results; all 158,370 B2000 values (the
member states' series with nObs, on the ex-ante years; DEMD, the reporting's copy of DOMM, left out) equal; the file
changes only HCOM.SUGA (315 Absolute supports), all equal to CAPTRD's Expert.
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import longrun_supports as LR
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need, _ref, G, DAT)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401


@pytest.mark.slow
@need
def test_longrun_supports_equal_captrds(state, population):  # noqa: F811
    S0, prior, nat, X, s = state
    S = copy.deepcopy(S0)
    g = lambda n: pd.read_csv(G / f"{n}.csv", keep_default_na=False).d0.str.upper().tolist()   # noqa: E731
    d = _ref("data")
    pto = pd.read_csv(G / "PACT_TO_O.csv", keep_default_na=False)
    C = LR.Context(
        ms=X.ms, msincl=X.ms, pdata=X.pdata, nobs=set(map(tuple, d[d.t == "nObs"][["region", "col", "row"]].values)),
        basm=X.basm, bast=X.bast, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, pact=g("PACT"), req_feed=g("REQ_FEED"),
        reqst=pd.read_csv(P.SETS_DIR / "reqst.csv").d0.tolist(), pact_to_y=X.pact_to_y,
        pact_to_o=list(zip(pto.d0.str.upper(), pto.d1.str.upper())),
        mrkbalee=pd.read_csv(P.SETS_DIR / "mrkbalee.csv").d0.tolist(), mlk_pro=g("MLKPRO"),
        cows_act=["DCOL", "DCOH", "SCOW"], exante=X.exante, exantet=X.exantet, expostt=X.expostt,
        years_cur=sorted(set(X.expostt) | set(X.exante)), base_year=X.base_year, bast_year=X.bast_year,
        lst_expost=X.lst_expost, lst_exante=X.lst_exante, lst_dgagri=X.lst_dgagri, phase_in=2025, infl=1.019,
        support=X.support, dgagri1=X.dgagri1, map_rr=X.map_rr, cur_europ_agg=["EU014000", "EU013000", "EU27yr19"],
        inha=population, longrun_info_all=LR.read_info(DAT))
    res = LR.supports(S, C)
    assert not res.longrun and not res.longrun1
    ref = _ref("B2000")
    ref = ref[ref.t.str.isdigit() & (ref.col != "DEMD")]
    R = {(r, c, w, int(t)): v for r, c, w, t, v in zip(ref.region, ref.col, ref.row, ref.t, ref.value)}
    bad = [k for k in set(R) | set(res.b2000) if abs(R.get(k, 0) - res.b2000.get(k, 0)) > 1e-6 * max(abs(R.get(k, 0)),
                                                                                                    1e-9)]
    assert len(R) > 150000 and not bad, bad[:5]
    changed = {k for d0, d1 in ((S0.ab, S.ab), (S0.pc, S.pc), (S0.tr, S.tr)) for k in set(d0) | set(d1)
               if d0.get(k) != d1.get(k)}
    assert {(k[1], k[2]) for k in changed} == {("HCOM", "SUGA")}
    ex = _ref("Expert")
    E = {(r, c, w, int(t)): v for r, c, w, t, v in zip(ex.region, ex.col, ex.row, ex.t, ex.value) if t.isdigit()}
    bad = [k for k in changed if abs(S.ab.get(k, 0.0) - E.get(k, 0.0)) > 1e-6 * abs(E.get(k, 1.0))]
    assert len(changed) > 300 and not bad, bad[:5]

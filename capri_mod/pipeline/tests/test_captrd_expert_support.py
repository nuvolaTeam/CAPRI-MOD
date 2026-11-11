"""CAPTRD's expert supports as a whole, the years after 2018 (2018 is COCO's, test_captrd_coco_supports.py): the
ported sources chained in expert_support.gms's order (its own rules, the biofuel trends, DG AGRI's dairy data,
Eurostat's recent production, the national experts, the long-run sources), its end (the herd floor, TOOU) and
define_stats_and_supports.gms's storage (Expert from Absolute and PercentChange, HCOM.COMI, BIOF.SUGA without
production, the sugar beet trade, TrustLevl); compared with CAPTRD's Expert and TrustLevl of the member states.

Results on 11 November 2026: of the 39,567 positions of the member states in the years after 2018 (DEMD, the
reporting's copy of DOMM, and the positions the reporting adds without a trust level left out), 39,495 equal in value
and trust level. The other 72 are define_EU_supports.gms's (stage 2f): the trust levels of NO000000's and TUR's market
positions with DG AGRI targets, which it sets again (l. 719-760).

test_support1_equal_captrds: the supports as define_stats_and_supports.gms leaves them (support1) against CAPTRD's; see
its docstring.
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import dairy_supports as D
from capri_mod.pipeline.captrd import expert_support as XS
from capri_mod.pipeline.captrd import final_supports as F
from capri_mod.pipeline.captrd import longrun_supports as LR
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.tests.test_captrd_national_supports import (  # noqa: F401
    state, dgagri, aglink_p, scaled, result, need, _ref, G, DAT)
from capri_mod.pipeline.tests.test_captrd_macro import population  # noqa: F401

K = ["region", "col", "row", "t"]
REQST = {"ENNE", "CRPR", "FILG", "FICT", "FISM", "FISF"}            # sets_captrd.gms l. 456


@pytest.fixture(scope="module")
def assembled(state, population, result):  # noqa: F811
    """Every ported source of the expert supports chained, then define_stats_and_supports.gms l. 485-633: (E: Expert,
    TL: TrustLevl, sup: the supports as support1, X, s, nobs)."""
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
    rd = lambda n: pd.read_csv(P.SETS_DIR / f"{n}.csv", keep_default_na=False)    # noqa: E731
    one = lambda n: rd(n).d0.tolist()                                            # noqa: E731
    two = lambda n: list(zip(rd(n).d0, rd(n).d1))                                # noqa: E731
    py = pd.read_csv(DAT / "biofuel_proc_yields.csv")
    FS = F.Sets(biostock=one("biostock"), biostock_oilp=one("biostockoilp"), oseeds=one("oseeds"), seco=one("seco"),
                grcu=one("grcu"), cropo=one("cropo"), prcd=two("prcd"), sed_to_oil=two("sed_to_oil"),
                oil_to_cak=two("oil_to_cak"), bio_prcd=two("bio_prcd"), pact_to_y=list(X.pact_to_y),
                shift_sugb=one("shiftsugbpos"), dompos=one("dompos"), mcact=one("mcact"), s_colsest=s.s_colsest,
                s_rowsest=s.s_rowsest, proc_yields=dict(zip(py.row, py.value)))
    exanted = [2018]                                                                       # T.exanted
    pa, ll, ul = {}, {}, {}
    for y in X.exante:                                                         # define_stats l. 589-598
        if y in exanted:
            continue
        F.biof_adjust(sup, E, y=y, ms=X.ms, S=FS, basm=X.basm, bast=X.bast, bas=X.bas, nobs=nobs, quts=X.pdata,
                      prcy=sup, lst_dgagri=X.lst_dgagri, fst_exante=min(X.exante), bas_year=X.base_year,
                      bast_year=X.bast_year, prd_adj=pa, low_lim=ll, upp_lim=ul)
    F.overwrite(sup, E, rest=rest, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, exante=X.exante)
    F.mcact_scale(sup, rest=rest, mcact=FS.mcact, exante=X.exante)
    F.adjust_trade(sup, E, ms=X.ms, s_rowsest=s.s_rowsest, exante=X.exante, basm=X.basm, dompos=FS.dompos)
    XS.sugb_trade(E, sup, ms=X.ms, exante=X.exante, bast=X.bast, basm=X.basm)
    TL = XS.trust(E, coco_trust={}, expert_trust=S.tr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, rest=rest)
    return E, TL, sup, X, s, nobs


@pytest.mark.slow
@need
def test_expert_supports_equal_captrds(assembled):
    E, TL, sup, X, s, nobs = assembled
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
    later = m.region.isin(["NO000000", "TUR"]) & (m.mine != 0) & ((m.mine - m.ref).abs() <= 1e-6 * m.ref.abs())
    print("expert supports:", len(m), "equal", int(m.ok.sum()), "| a later stage's or not stored:",
          int((~m.ok & later).sum()), "| other:", int((~m.ok & ~later).sum()))
    print(bad[~later.loc[bad.index]].head(20).to_string())
    assert len(m) > 39500 and int(m.ok.sum()) > 39450 and int((~m.ok).sum()) < 80
    assert int((~m.ok & ~later).sum()) == 0


@pytest.mark.slow
@need
def test_support1_equal_captrds(assembled):
    """The supports define_stats_and_supports.gms leaves (support1, l. 675) of the member states after 2018: the trend
    supports (with the reporting's DOMM undone in the stored Step1, captrd_pre_expert.py), DG AGRI's prices (l. 355),
    the biofuel adjustment, the expert overwrite, the areas scaled to UAAR and the trade adjustment (final_supports.py).

    Results on 11 November 2026: of 474,390 positions, 441,600 equal. 32,750 are rewritten after this stage (YILD and
    the requirement rows, captrd.gms l. 1190-1215; HFCS, aggreg_and_report.gms l. 70-81) or cannot be rebuilt from the
    stored Step1 (the product groups' UVAG, INHA, UVAD, CSSP: the reporting's, l. 214-223). The other 40 are open: the
    prices of the fossil fuels (UVAG of DISL, GASL) of NO000000, EL000000, IR000000 and UK000000 in 2020-2040, which
    our DGAgri1 holds and CAPTRD's support1 does not (its stored DGAgri1 of these years is rewritten by stage 2f, so
    it cannot tell which is right)."""
    E, TL, sup, X, s, nobs = assembled
    yrs, msset = set(X.exantet), set(X.ms)
    cols, rows = set(s.s_colsest), set(s.s_rowsest)
    s1 = _ref("support1")
    ref = {(r, c, w, int(t)): v for r, c, w, t, v in zip(s1.region, s1.col, s1.row, s1.t, s1.value)
           if t.isdigit() and int(t) in yrs and r in msset and c in cols}
    mine = {k: v for k, v in sup.items() if k[0] in msset and k[3] in yrs and k[1] in cols and k[2] in rows}
    rows_ = [(*k, mine.get(k, 0.0), ref.get(k, 0.0)) for k in set(mine) | set(ref)]
    m = pd.DataFrame(rows_, columns=K + ["mine", "ref"])
    m["ok"] = (m.mine - m.ref).abs() <= 1e-6 * m.ref.abs().clip(lower=1e-6)
    # not this stage's: captrd.gms l. 1190-1215 rewrite support1's yields (YILD, the sum of the outputs) and turns the
    # requirement rows into absolute amounts after the estimation (stage 4); aggreg_and_report.gms l. 70-81 sets the
    # isoglucose rows (HFCS); the stored Step1 of the price, consumption and expenditure rows of the product groups
    # (UVAG, INHA, UVAD, CSSP of OAGG) is the reporting's (l. 214-223), so their supports cannot be rebuilt from it
    oagg = ["CERE", "OILS", "INDU", "VEGE", "FRUI", "FORA", "MEAS"]
    later = m.row.isin(["YILD", "HFCS"] + sorted(REQST)) | (m.col.isin(["UVAG", "INHA", "UVAD", "CSSP"])
                                                             & m.row.isin(oagg))
    bad = m[~m.ok & ~later]
    print("support1:", len(m), "equal", int(m.ok.sum()), "| stage 4 or not rebuildable:", int((~m.ok & later).sum()),
          "| other:", len(bad))
    print(bad.assign(pos=bad.col + "." + bad.row).groupby("pos").size().sort_values(ascending=False).head(30).to_string())
    print(bad.head(30).to_string())
    assert len(m) > 450000 and int(m.ok.sum()) > 441000
    assert bad.col.eq("UVAG").all() and bad.row.isin(["DISL", "GASL"]).all() and len(bad) <= 40

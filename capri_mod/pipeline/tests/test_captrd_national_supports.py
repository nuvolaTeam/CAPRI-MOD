"""CAPTRD's national expert supports (capri_mod/pipeline/captrd/national_supports.py; captrd/national_supports.gms)
on the p_ExpertSupprt the earlier ported sources leave, in expert_support.gms's order (its own rules, the biofuel
trends, DG AGRI's dairy data, Eurostat's recent production), with CAPTRD's BASM, BAST, BAS, p_data and DGAgri1 and the
supports before the expert supports (supports.py on CAPTRD's Step1 and statistics: CAPTRD stores the support only
after the expert supports have overwritten it, define_stats_and_supports.gms l. 597); compared with CAPTRD's Expert
(Absolute, else (1 + PercentChange/100) x BASM) and TrustLevl (10 where no source sets one, l. 637-645) of the
positions this file changes.

Results on 11 November 2026: of 6,829 positions changed in the years after 2018, 6,701 equal to CAPTRD's in value and
trust level; the other 128 are accounted for by a later stage or by the stored results:
  - the trust levels of NO000000's and TUR's market positions with DG AGRI targets, which define_EU_supports.gms
    (l. 719-833) sets again;
  - CS000000's DOMM.COMI, whose support CAPTRD's results hold only as the reporting re-aggregate;
  - BL400000's dairy herds (HERD), whose BASM is not among CAPTRD's stored results.
longrun_supports.gms runs after this file and is not ported yet; the PercentChange positions this file leaves are
equal to CAPTRD's nonetheless (that file merges long-run information only where it has some).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import agriprod_supports as A
from capri_mod.pipeline.captrd import expert_rules as XR
from capri_mod.pipeline.captrd import national_supports as N
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import supports as SU
from capri_mod.pipeline.tests.test_captrd_aglink import dgagri, need, aglink_p  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_scale_dgagri import scaled, EXANTE  # noqa: F401
from capri_mod.pipeline.tests import test_captrd_biofuel_trends as TB
from capri_mod.pipeline.tests.test_captrd_dairy_supports import result  # noqa: F401  (the dairy supports)

R = REFERENCE / "captrd_results" / "1770"
G = REFERENCE / "sets" / "simini_21730"
DAT = P.SETS_DIR.parent / "dat"
K = ["region", "col", "row", "t"]


def _ref(name):
    return pd.read_csv(R / f"{name}.csv.gz", dtype={"t": str})


def _kv(df, with_t=True):
    if with_t:
        return {(r, c, w, int(y)): v for r, c, w, y, v in zip(df.region, df.col, df.row, df.t, df.value)}
    return {(r, c, w): v for r, c, w, v in zip(df.region, df.col, df.row, df.value)}


def _pre_expert_supports(years):
    """define_stats_and_supports.gms l. 186-330 on CAPTRD's Step1 and statistics (test_captrd_supports.py)."""
    st = _ref("data").pivot_table(index=["region", "col", "row"], columns="t", values="value",
                                  aggfunc="first").fillna(0.0)
    st = st[st.nObs > 0]
    s1 = _ref("step1")
    S1 = s1[s1.t.isin([str(y) for y in years])].pivot_table(index=["region", "col", "row"], columns="t",
                                                             values="value", aggfunc="first")
    S1.columns = [int(c) for c in S1.columns]
    p = _ref("P_Data")
    p = p[p.t.str.fullmatch(r"\d{4}")]
    yl = p[p.t.astype(int).between(2011, 2018)].pivot_table(index=["region", "col", "row"], columns="t",
                                                             values="value", aggfunc="first").fillna(0.0)
    pty = set(map(tuple, pd.read_csv(G / "PACT_TO_Y.csv")[["d0", "d1"]].values))
    yidx = [i for i in yl.index if (i[1], i[2]) in pty]
    levbas = pd.Series({i: st.at[(i[0], i[1], "LEVL"), "BAS"] if (i[0], i[1], "LEVL") in st.index else 0.0
                        for i in yidx})
    bsy = SU.best_three_yields(levbas, yl.loc[yidx], range(2011, 2019), st["BAS"])
    bm, bt = _ref("BASM"), _ref("BAST")
    bm = bm[bm.t == "2030"].set_index(["region", "col", "row"]).value
    bt = bt[bt.t == "2030"].set_index(["region", "col", "row"]).value
    inp = pd.DataFrame({"nobs": st.nObs, "wr2": st.wR2, "wave": st.WAve, "wvar": st.wVar, "wvarerr": 0.0,
                        "basm": bm.reindex(st.index).fillna(0.0), "bast": bt.reindex(st.index).fillna(0.0),
                        "bas": st.BAS})
    inp["bsy"] = bsy.reindex(inp.index).fillna(0.0)
    sets = SU.SupportSets(pact_to_y=pty, mcact=set(_g("MCACT")), no_yield_drop=set(
        pd.read_csv(P.SETS_DIR / "noyielddrop.csv").d0), breed_act={"DCOL", "DCOH", "SCOW", "SHGM", "SOWS", "HENS"},
        grs_act=set(_g("GRSACT")), reqst={"ENNE", "CRPR", "FILG", "FICT", "FISM", "FISF"}, feed=set(_g("FEED")),
        mpact=set(_g("MPACT")))
    sup, _ = SU.supports(inp, S1, years, 2017, 2018, sets)
    st = sup.stack()
    return {(r, c, w, int(y)): float(v) for (r, c, w, y), v in st.items() if v and v == v}


def _g(name):
    return pd.read_csv(G / f"{name}.csv", keep_default_na=False).d0.str.upper().tolist()


@pytest.fixture(scope="module")
def state(dgagri, scaled, aglink_p, result):  # noqa: F811
    s = P.read_sets()
    S = N.Expert()

    def merge(d):
        for (r, c, w, y), (a, t) in d.items():
            k = (r, c, w, int(y))
            S.put(S.ab, k, a)
            S.put(S.tr, k, t)
    # expert_support.gms l. 1-340: CAPRI's own rules
    sup = _ref("support")
    bm, bt = _ref("BASM"), _ref("BAST")
    pdata = _ref("P_Data")
    breed = pd.read_csv(P.SETS_DIR / "breedact.csv", keep_default_na=False, dtype=str).d0.tolist()
    resy = [int(y) for y in EXANTE]

    def kvs(df, with_t=True):
        return {((r, c, w, y) if with_t else (r, c, w)): v
                for r, c, w, y, v in zip(df.region, df.col, df.row, df.t.astype(str), df.value)}
    merge(XR.rules(ms=s.ms, ms_no_eu=pd.read_csv(G / "MSnoEU.csv", keep_default_na=False).d0, exante=resy,
                   bas_year=2017, support=kvs(sup[sup.region.isin(set(s.ms))]), basm=kvs(bm[bm.t == "2030"], False),
                   bast=kvs(bt[bt.t == "2018"], False), pdata_years=kvs(pdata[pdata.row == "INCE"]),
                   dgagri=kvs(dgagri), dgagri1=dict(scaled[0]),
                   ms_to_agg=[(b, a) for a, b in s.map_rr if a in ("EU014000", "EU013000", "EU27yr19")],
                   europ_aggs=["EU014000", "EU013000", "EU27yr19"], breed_act=breed,
                   ncnc=["N_CAL", "N_FAT", "N_PRO"], coef_hfcs={"SUGA": 0.92, "MAIZ": 0.60}))
    # l. 114: the biofuel trends
    res, T = TB.run(aglink_p)
    merge(res.expert)
    # l. 365-768: DG AGRI's dairy data
    merge(result[0])
    # l. 771: Eurostat's recent production, on the state so far
    I = A.read_inputs(P.SETS_DIR, DAT)
    meat = set(pd.read_csv(P.SETS_DIR / "meat.csv", dtype=str).d0)
    pty = list(s.pact_to_y)
    meat_act = sorted({a for a, m in pty if m in meat and a in set(s.maact)})
    pdy = pdata[pdata.t.str.isdigit()]
    pd_all = _kv(pdy)
    runr = list(s.ms) + (["BL400000"] if "BL000000" in s.ms else [])
    bm70 = _kv(bm[bm.t == "2070"], False)
    d = _ref("data")
    ag = A.supports(I, runr=runr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, exante=T.exante, exantet=T.exantet,
                    base_year=2017, lst_expostt=T.lst_expostt, basm=bm70, pdata=pd_all,
                    bast=_kv(d[d.t == "BAST"], False), dcow=["DCOL", "DCOH"], meat_act=meat_act, pact_to_y=pty,
                    prior=dict(S.ab))
    for k, v in ag.absolute.items():
        S.put(S.ab, k, v)
    for k, v in ag.trust.items():
        S.put(S.tr, k, v)
    for k in ag.no_percent:
        S.put(S.pc, k, 0.0)
    for k, (a, b) in ag.bounds.items():
        S.put(S.lo, k, a or 0.0)
        S.put(S.up, k, b or 0.0)
    prior = N.Expert(dict(S.ab), dict(S.pc), dict(S.tr), dict(S.lo), dict(S.up))
    X = N.Context(
        ms=list(s.ms), runr=runr, nuts0=_g("NUTS0"), nuts0_and_2=_g("NUTS0_and_2"),
        nt2est=sorted({b for a, b in s.map_rr if a in set(s.ms) and b in set(s.nt2ext)}), nt2=s.srnuts2,
        map_rr=s.map_rr,
        s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, cact=s.cact, maact=s.maact, oiyani=_g("OIYANI"),
        pact_to_y=pty, p_t_actagg=s.p_t_actagg, exante=T.exante, exantet=T.exantet, expostt=T.expostt,
        basyrsm=T.basyrsm, base_year=2017, bast_year=T.lst_expostt - 1, lst_expost=T.lst_expost,
        lst_expostt=T.lst_expostt, lst_exante=max(T.exante), lst_dgagri=T.lst_dgagri,
        support={**_kv(sup[sup.t.str.isdigit()]), **_pre_expert_supports(list(T.exante))}, basm=bm70, bast=_kv(d[d.t == "BAST"], False),
        bas=_kv(d[d.t == "BAS"], False), pdata=pd_all, dgagri1={(r, c, w, int(y)): v for (r, c, w, y), v in
                                                              dict(scaled[0]).items()},
        years=list(range(1984, 2071)))
    nat = N.supports(S, N.read_inputs(P.SETS_DIR, DAT), X)
    return S, prior, nat, X, s


def _expert(S, X, s):
    """define_stats_and_supports.gms l. 485-500: Absolute, else (1 + PercentChange/100) x BASM, on S_ColsEst x S_RowsEst."""
    cols, rows = set(s.s_colsest), set(s.s_rowsest)
    out = {}
    for k in set(S.ab) | set(S.pc):
        if k[1] in cols and k[2] in rows:
            v = S.ab.get(k) or (1 + S.pc.get(k, 0.0) / 100) * X.basm.get(k[:3], 0.0) * bool(S.pc.get(k))
            if v:
                out[k] = v
    return out


@pytest.mark.slow
@need
def test_national_supports_equal_captrds(state):
    S, prior, nat, X, s = state
    E, E0 = _expert(S, X, s), _expert(prior, X, s)
    changed = {k for k in set(E) | set(E0) | set(S.tr) | set(prior.tr)
               if E.get(k) != E0.get(k) or S.tr.get(k) != prior.tr.get(k)}
    mine = pd.DataFrame([(*k[:3], str(k[3]), E.get(k, 0.0), S.tr.get(k, 0.0) or 10.0 * bool(E.get(k)))
                         for k in changed if k[3] in set(X.exantet)], columns=K + ["abs", "trust"])
    ex, tl = _ref("Expert"), _ref("TrustLevl").rename(columns={"value": "tref"})
    m = mine.merge(ex[K + ["value"]], on=K, how="left").merge(tl[K + ["tref"]], on=K, how="left").fillna(0.0)
    m["ok"] = (m["abs"] - m.value).abs() <= 1e-6 * m.value.abs().clip(lower=1e-6)
    m["tok"] = ((m.trust - m.tref).abs() < 1e-9) | ((m["abs"] == 0) & (m.value == 0))
    dg1 = {k[:3] for k in X.dgagri1}
    eu_supports = m.region.isin(["NO000000", "TUR"]) & m.ok & ~m.tok & [(r, c, w) in dg1 for r, c, w in
                                                                          zip(m.region, m.col, m.row)]
    domm = (m.region == "CS000000") & (m.col == "DOMM")
    no_basm = [(r, c, w) not in X.basm and E.get((r, c, w, int(t))) is None for r, c, w, t in
               zip(m.region, m.col, m.row, m.t)]
    known = eu_supports | domm | pd.Series(no_basm, index=m.index)
    rest = m[~known]
    print("national: changed", len(m), "compared", len(rest), "equal values", int(rest.ok.sum()), "equal trust",
          int(rest.tok.sum()), "| set again later or not in the stored results:", int(known.sum()))
    assert len(m) > 6000 and len(rest) > 6500
    assert rest.ok.all() and rest.tok.all()
    assert int(known.sum()) < 150

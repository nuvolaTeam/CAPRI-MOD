"""CAPTRD's supports before the expert supports overwrite them, for the tests of the expert-support stages: CAPTRD
stores "support" only after define_stats_and_supports.gms l. 597 has replaced it by the Expert, so the sources that
read the support (expert_support.gms and the files it includes) are given supports.py's on CAPTRD's Step1 and
statistics (define_stats_and_supports.gms l. 186-330, test_captrd_supports.py)."""
from __future__ import annotations

import functools

import pandas as pd

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import supports as SU

R = REFERENCE / "captrd_results" / "1770"
G = REFERENCE / "sets" / "simini_21730"


def _ref(name):
    return pd.read_csv(R / f"{name}.csv.gz", dtype={"t": str})


def _g(name):
    return pd.read_csv(G / f"{name}.csv", keep_default_na=False).d0.str.upper().tolist()


def _reqfcnlim():
    """p_reqFcnLim (feed/feed_decl.gms l. 284-310) as {(col, row): (lo, up)}, from its CSV (agriprod_supports' input)."""
    d = pd.read_csv(P.SETS_DIR.parent / "dat" / "agriprod_p_reqfcnlim.csv")
    out = {}
    for a, w, b, v in zip(d.act, d.row, d.bound, d.value):
        lo, up = out.get((a, w), (None, None))
        out[(a, w)] = (v, up) if b == "lo" else (lo, v)
    return out


@functools.lru_cache(maxsize=2)
def pre_expert_supports(years: tuple):
    """define_stats_and_supports.gms l. 186-330 on CAPTRD's Step1 and statistics (test_captrd_supports.py)."""
    st = _ref("data").pivot_table(index=["region", "col", "row"], columns="t", values="value",
                                  aggfunc="first").fillna(0.0)
    st = st[st.nObs > 0]
    s1 = _ref("step1")
    # aggreg_and_report.gms l. 293-294: the stored Step1's DOMM is the reporting's sum of the domestic use positions;
    # its DEMD holds the estimation's DOMM (copied before), and no DEMD means the estimation had no DOMM
    s1 = pd.concat([s1[s1.col != "DOMM"].loc[lambda x: x.col != "DEMD"],
                    s1[s1.col == "DEMD"].assign(col="DOMM")])
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
        mpact=set(_g("MPACT")), reqfcnlim=_reqfcnlim())
    sup, _ = SU.supports(inp, S1, years, 2017, 2018, sets)
    st = sup.stack()
    return {(r, c, w, int(y)): float(v) for (r, c, w, y), v in st.items() if v and v == v}

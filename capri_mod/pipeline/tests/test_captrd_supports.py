"""Parity of CAPTRD's Step-1 supports (capri_mod/pipeline/captrd/supports.py) with CAPTRD's own support1 in 2030
(capri_reference/captrd_results/1770): the support rules applied to CAPTRD's own Step1, statistics and base values.

Excluded: series with external information (expert, COCO, trust level, DG AGRI entries), NTRD and DOMM (reporting
re-aggregates), crop areas (rescaled to UAAR afterwards, define_stats_and_supports.gms l. 618-622) and the
requirement rows. 99.77% equal on 23 October 2026; the rest are trade positions that adjust_trade_supports.gms
changes later.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.pipeline.captrd import supports as SU

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "capri_reference" / "captrd_results" / "1770"
SETS = ROOT / "capri_reference" / "sets" / "simini_21730"


@pytest.mark.slow
@pytest.mark.skipif(not (R / "support1.csv.gz").exists() or not SETS.exists(), reason="CAPRI reference files not built")
def test_step1_supports_match_captrd():

    st=pd.read_csv(R/"data.csv.gz").pivot_table(index=["region","col","row"],columns="t",values="value",aggfunc="first").fillna(0.0)
    st=st[st.nObs>0]
    def rd(f, t=None):
        d=pd.read_csv(R/f,dtype={"t":str}); 
        return d
    s1=rd("step1.csv.gz"); 
    years=[2018,2020,2025,2030,2035,2040,2045,2050,2060,2070]
    S1=s1[s1.t.isin([str(y) for y in years])].pivot_table(index=["region","col","row"],columns="t",values="value",aggfunc="first")
    S1.columns=[int(c) for c in S1.columns]
    p=rd("P_Data.csv.gz"); p=p[p.t.str.fullmatch(r"\d{4}")]
    yl=p[p.t.astype(int).between(2011,2018)].pivot_table(index=["region","col","row"],columns="t",values="value",aggfunc="first").fillna(0.0)
    pty=set(map(tuple,pd.read_csv(SETS/"PACT_TO_Y.csv")[["d0","d1"]].values))
    mcact=set(pd.read_csv(SETS/"MCACT.csv").d0); grs=set(pd.read_csv(SETS/"GRSACT.csv").d0); mpact=set(pd.read_csv(SETS/"MPACT.csv").d0)
    feed=set(pd.read_csv(SETS/"FEED.csv").d0)
    C=ROOT / 'capri_data' / 'pipeline' / 'captrd' / 'sets'
    nyd=set(pd.read_csv(C/"noyielddrop.csv").d0)
    yidx=[i for i in yl.index if (i[1],i[2]) in pty]
    levbas=pd.Series({i: st.at[(i[0],i[1],"LEVL"),"BAS"] if (i[0],i[1],"LEVL") in st.index else 0.0 for i in yidx})
    bsy=SU.best_three_yields(levbas, yl.loc[yidx], range(2011,2019), st["BAS"])
    bm=rd("BASM.csv.gz"); bm=bm[bm.t=="2030"].set_index(["region","col","row"]).value
    bt=rd("BAST.csv.gz"); bt=bt[bt.t=="2030"].set_index(["region","col","row"]).value
    inp=pd.DataFrame({"nobs":st.nObs,"wr2":st.wR2,"wave":st.WAve,"wvar":st.wVar,"wvarerr":0.0,"basm":bm.reindex(st.index).fillna(0.0),"bast":bt.reindex(st.index).fillna(0.0),"bas":st.BAS})
    inp["bsy"]=bsy.reindex(inp.index).fillna(0.0)
    sets=SU.SupportSets(pact_to_y=pty,mcact=mcact,no_yield_drop=nyd,breed_act={"DCOL","DCOH","SCOW","SHGM","SOWS","HENS"},
        grs_act=grs,reqst={"ENNE","CRPR","FILG","FICT","FISM","FISF"},feed=feed,mpact=mpact)
    sup,_=SU.supports(inp,S1,years,2017,2018,sets)
    ref=rd("support1.csv.gz"); ref=ref[ref.t=="2030"].set_index(["region","col","row"]).value
    ex=set()
    for f in ["Expert.csv.gz","TrustLevl.csv.gz","COCO.csv.gz","DGAgri1.csv.gz","DGAgri.csv.gz"]:
        e=rd(f); ex|=set(map(tuple,e[["region","col","row"]].drop_duplicates().values))
    idx=sup.index
    cols=idx.get_level_values(1); rows=idx.get_level_values(2)
    m=~idx.isin(list(ex)) & ~cols.isin(["NTRD","DOMM"]) & ~((rows=="LEVL")&cols.isin(list(mcact))) & ~rows.isin(list(sets.reqst))
    c=pd.DataFrame({"ours":sup[2030][m],"ref":ref.reindex(idx[m])}).dropna()
    ok=np.isclose(c.ours,c.ref,rtol=1e-6,atol=1e-9)
    ok = np.isclose(c.ours, c.ref, rtol=1e-6, atol=1e-9)
    assert len(c) > 40000
    assert ok.mean() > 0.997, c[~ok].head(20)

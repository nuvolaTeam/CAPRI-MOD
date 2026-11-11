"""Parity of CAPTRD's expert supports from DG AGRI's dairy data (capri_mod/pipeline/captrd/dairy_supports.py;
captrd/expert_support.gms l. 365-760) with CAPTRD's Expert and TrustLevl, chained to the Aglink and scaling stages
(their DGAgri) and on CAPTRD's stored supports, BASM and P_Data.

Results on 11 November 2026:
  - the EU parts EU014000, EU013000 and A_EU_WEST/EAST (this stage's checking output): every ex-ante position equal;
  - the regions' dairy positions after 2020 (DCOL/DCOH LEVL, HERD, COMI; GROF, DOMM, EAAG, PRCM .COMI; MAPR.MILK)
    that no later source rewrites: 1,090 records, all values and trust levels equal. Not comparable: 2020
    (agriprod_supports.gms sets it from Eurostat's recent data, trust 9.02/3.02), the eight countries whose dairy
    supports national_supports.gms rewrites, and the positions a later source gives its own trust level (7.01 ...);
  - the share HCOM/GROF of raw milk: every ex-post value of support1 equal; HCOM.COMI's expert support derived from it
    (define_stats_and_supports.gms l. 510-519) equal in its 233 comparable records (positive share and a GROF.COMI
    expert support).
The reference uses %Aglink% aglink2023dgAgri, so %lst_dgagri% is 2040 (captrd.gms l. 248): CAPTRD's stored Aglink
growth rates (DGAgri "grate") are 2015-2040's.
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import dairy_supports as D
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import timesets as TS
from capri_mod.pipeline.tests.test_captrd_aglink import dgagri, need  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_scale_dgagri import scaled, EXANTE  # noqa: F401
from capri_mod.pipeline.tests.captrd_pre_expert import pre_expert_supports

R = REFERENCE / "captrd_results" / "1770"
DAT = P.SETS_DIR.parent / "dat"
K = ["region", "col", "row", "t"]


def _kv(df, with_t=True):
    return {((r, c, w, y) if with_t else (r, c, w)): v
            for r, c, w, y, v in zip(df.region, df.col, df.row, df.t.astype(str), df.value)}


def _tables():
    out = {}
    for n in D.TABLES:
        d = pd.read_csv(DAT / f"dairy_{n}.csv", keep_default_na=False)
        out[n] = {(a, int(y)): v for a, y, v in zip(d.ms_agri, d.year, d.value)}
    return out


@pytest.fixture(scope="module")
def result(scaled):  # noqa: F811
    s = P.read_sets()
    resy = [int(y) for y in EXANTE]
    T = TS.build(1984, 2070, resy, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019),
                 expostt_extra=[2019])
    sup = pd.read_csv(R / "support.csv.gz", dtype={"t": str})
    bm = pd.read_csv(R / "BASM.csv.gz", dtype={"t": str})
    pdata = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    pdata = pdata[pdata.col.isin(["GROF", "HCOM", "DCOL", "DCOH"]) & pdata.row.isin(["COMI", "LEVL"])]
    m2 = pd.read_csv(DAT / "dairy_ms_agri_to_ms.csv", keep_default_na=False)
    rc = pd.read_csv(DAT / "p_recentmlkyld.csv", keep_default_na=False, dtype={"year": str})
    rc = rc[rc.year.str.upper() == "Y"]
    runr = list(s.ms) + (["BL400000"] if "BL000000" in s.ms else [])
    tr = {}
    # the supports when expert_support.gms runs: the trend supports, not the stored ones the expert supports overwrote
    support = {**_kv(sup), **{(r, c, w, str(y)): v for (r, c, w, y), v in pre_expert_supports(tuple(T.exante)).items()}}
    dg = {k: v for k, v in scaled[1].items()} if isinstance(scaled[1], dict) else _kv(scaled[1])
    E, share = D.dairy(runr=runr, ms=s.ms, ms_no_eu28=s.msnoeu28, dcow=["DCOL", "DCOH"], base_year=2017,
                       exante_t=T.exantet, expost=T.expost, expostt=T.expostt, years_cur=T.years_cur, sim_years=resy,
                       fst_exante=T.fst_exante, lst_exante=max(T.exante), lst_dgagri=T.lst_dgagri, tables=_tables(),
                       ms_agri_to_ms=list(zip(m2.ms_agri, m2.region)), recent=dict(zip(rc.region, rc.value)),
                       basm=_kv(bm[bm.t == "2070"], False), support=support, pdata=_kv(pdata), dgagri=dg,
                       map_rr=s.map_rr, europ_aggs=["EU014000", "EU013000", "EU27yr19"],
                       sub_aggs=["EU014000", "EU013000"], eu13="EU013000", eu14="EU014000", west="A_EU_WEST",
                       east="A_EU_EAST", trace=tr)
    return E, share, T, s, sup, tr


def _compare(E, years):
    mine = pd.DataFrame([(*k, a, t) for k, (a, t) in E.items()], columns=K + ["abs", "trust"])
    mine = mine[mine.t.isin([str(y) for y in years])]
    ex = pd.read_csv(R / "Expert.csv.gz", dtype={"t": str})
    tl = pd.read_csv(R / "TrustLevl.csv.gz", dtype={"t": str}).rename(columns={"value": "tref"})
    m = mine.merge(ex[K + ["value"]], on=K, how="left").merge(tl[K + ["tref"]], on=K, how="left")
    m = m.fillna({"value": 0.0, "tref": 0.0})
    m["ok"] = (m["abs"] - m.value).abs() <= 1e-6 * m.value.abs().clip(lower=1e-6)
    m["tok"] = (m.trust - m.tref).abs() < 1e-9
    m["pos"] = m.col + "." + m.row
    return m


#: national_supports.gms rewrites these countries' dairy supports after this stage (as percent changes: AT l. 276,
#: CZ l. 1382, SK l. 1334, UK l. 870, MT l. 1196, EL l. 531-545; CY l. 892, SI l. 1271)
NATIONAL = {"AT000000", "CZ000000", "SK000000", "UK000000", "MT000000", "EL000000", "CY000000", "SI000000"}
#: CAPTRD's trust levels of later sources: national_supports.gms (7.01, 8.01, 9.01, 10.01) and agriprod_supports.gms
#: (9.02, 3.02: 2020, recent Eurostat data)
LATER_TRUST = {7.01, 8.01, 9.01, 10.01, 9.02, 3.02}


@pytest.mark.slow
@need
def test_dairy_supports_equal_captrds(result):
    E, share, T, s, sup, tr = result
    m = _compare(E, T.exante)
    agg = m.region.isin(["EU014000", "EU013000", "A_EU_WEST", "A_EU_EAST"])
    m = m[agg | m.t.astype(int).isin(T.exantet)]        # 2018 (ExAnteD) of the regions: COCO's supports, not these
    agg = agg[m.index]
    later = m.tref.round(6).isin(LATER_TRUST)
    # the EU parts' and A_EU_WEST/EAST's positions are this stage's checking output: every ex-ante year equal
    a = m[agg]
    assert len(a) > 150 and a.ok.all() and set(a.region) == {"EU014000", "EU013000", "A_EU_WEST", "A_EU_EAST"}
    # the regions' positions after 2020 that no later source rewrites
    r = m[~agg & (m.t.astype(int) > D.LST_DAITAR) & ~m.region.isin(NATIONAL) & ~later]
    g = r.groupby("pos").agg(n=("ok", "size"), ok=("ok", "sum"), tok=("tok", "sum"))
    assert (g.ok == g.n).all() and (g.tok == g.n).all()
    assert set(g.index) == {"DCOL.LEVL", "DCOL.HERD", "DCOL.COMI", "DCOH.LEVL", "DCOH.HERD", "DCOH.COMI", "GROF.COMI",
                            "DOMM.COMI", "EAAG.COMI", "PRCM.COMI", "MAPR.MILK"} and len(r) > 1000
    # the rest: 2020 (agriprod_supports.gms rewrites it from Eurostat), the countries above, or a later source's trust
    rest = m[~agg & ~m.index.isin(r.index)]
    assert ((rest.t == "2020") | rest.region.isin(NATIONAL) | rest.tref.round(6).isin(LATER_TRUST)).all(), \
        rest[~((rest.t == "2020") | rest.region.isin(NATIONAL) | rest.tref.round(6).isin(LATER_TRUST))].head(20)


@pytest.mark.slow
@need
def test_dairy_hcom_share_equal_captrds(result):
    """The share HCOM/GROF of raw milk: its ex-post years against CAPTRD's support1 (define_stats_and_supports.gms
    l. 522 deletes the ex-ante ones), the ex-ante ones through HCOM.COMI's expert support (l. 510-519) on CAPTRD's
    GROF.COMI expert and trend supports."""
    E, share, T, s, sup, tr = result
    s1 = pd.read_csv(R / "support1.csv.gz", dtype={"t": str})
    s1 = s1[s1.col.str.upper() == "SHARE"]
    ref = {(a, int(t)): v for a, t, v in zip(s1.region, s1.t, s1.value)}
    mine = {k: v for k, v in share.items() if k[1] not in set(T.exantet)}
    assert set(mine) == set(ref) and len(ref) > 900
    assert all(abs(mine[k] - ref[k]) <= 1e-9 * max(abs(ref[k]), 1e-9) for k in ref)
    ex = pd.read_csv(R / "Expert.csv.gz", dtype={"t": str})
    tl = pd.read_csv(R / "TrustLevl.csv.gz", dtype={"t": str})
    gx = ex[(ex.col == "GROF") & (ex.row == "COMI")]
    H = D.hcom_expert(share, _kv(gx), _kv(sup[(sup.col == "GROF") & (sup.row == "COMI")]), s.ms, T.exantet)
    he = _kv(ex[(ex.col == "HCOM") & (ex.row == "COMI")])
    ht = _kv(tl[(tl.col == "HCOM") & (tl.row == "COMI")])
    # compared where the share is positive (with no share CAPTRD's trust level 1 has no support to belong to) and
    # GROF.COMI has an expert support: Turkey and the Western Balkans have none, and CAPTRD's stored trend support is
    # the final one, which stages after define_stats_and_supports.gms change
    has = set(zip(gx.region, gx.t))
    keys = [k for k in H if share.get((k[0], int(k[3])), 0.0) > 0 and (k[0], k[3]) in has]
    bad = [k for k in keys if abs(H[k][0] - he.get(k, 0.0)) > 1e-6 * max(abs(he.get(k, 0.0)), 1e-6)
           or abs(H[k][1] - ht.get(k, 0.0)) >= 1e-9]
    assert len(keys) > 200 and not bad, bad[:10]
    assert {k[0] for k in H if share.get((k[0], int(k[3])), 0.0) > 0 and (k[0], k[3]) not in has} <= set(s.msnoeu28) - {"UK000000"}


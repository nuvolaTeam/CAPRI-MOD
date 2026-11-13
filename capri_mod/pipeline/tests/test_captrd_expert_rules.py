"""Parity of CAPTRD's own expert rules (capri_mod/pipeline/captrd/expert_rules.py; captrd/expert_support.gms) with
CAPTRD's Expert and TrustLevl of the ex-ante years after 2018 (2018 is COCO's, test_captrd_coco_supports.py), chained
to the Aglink and scaling stages and on CAPTRD's stored supports, BASM and BAST.

Results on 10 November 2026, per rule (records; equal values; equal trust levels):
  NTRD.FRMI 315/315/315; UAAR.LEVL 315/315/315; UVAG.SUGA 234/234/234; UVAG.SUGB 234/234/234; FEDM.SUGA 153/153/153;
  FEDM.SUGB 171/171/171; LOSM.SUGA 54/54/54; LOSM.SUGB 189/189/189; N_CAL, N_FAT, N_PRO .INCE 315/315/315 each;
  the breeding animals' SLGW 1,890/1,890/1,890; SHGM.SGMI 261/261/252 (9 trust levels 9.01 in CAPTRD's: a later
  source's); IMPT.SUGB 216/36/216 and EXPT.SUGB 117/0/117 (values a later source sets: not yet ported).
  Isoglucose (PRCI.MAIZ, INDM.MAIZ, l. 206-250) gives nothing, as in CAPTRD: its HFCS share HCOS is not a CAPRI column,
  so CAPTRD's DGAgri holds none (load_aglink2023dgAgri.gms l. 1395) and CAPTRD's Expert has PRCI.MAIZ only for 2018.
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import expert_rules as X
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.tests.test_captrd_aglink import dgagri, need  # noqa: F401
from capri_mod.pipeline.tests.test_captrd_scale_dgagri import scaled, EXANTE  # noqa: F401

R = REFERENCE / "captrd_results" / "1770"
G = REFERENCE / "sets" / "simini_21730"
K = ["region", "col", "row", "t"]


def _kv(df, with_t=True):
    return {((r, c, w, y) if with_t else (r, c, w)): v
            for r, c, w, y, v in zip(df.region, df.col, df.row, df.t.astype(str), df.value)}


@pytest.mark.slow
@need
def test_expert_rules_equal_captrds(dgagri, scaled):  # noqa: F811
    s = P.read_sets()
    D1 = scaled[0]
    sup = pd.read_csv(R / "support.csv.gz", dtype={"t": str})
    bm = pd.read_csv(R / "BASM.csv.gz", dtype={"t": str})
    bt = pd.read_csv(R / "BAST.csv.gz", dtype={"t": str})
    pdata = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    breed = pd.read_csv(P.SETS_DIR / "breedact.csv", keep_default_na=False, dtype=str).d0.tolist()
    resy = [int(y) for y in EXANTE]
    E = X.rules(ms=s.ms, ms_no_eu=pd.read_csv(G / "MSnoEU.csv", keep_default_na=False).d0, exante=resy, bas_year=2017,
                support=_kv(sup[sup.region.isin(set(s.ms))]), basm=_kv(bm[bm.t == "2030"], False),
                bast=_kv(bt[bt.t == "2018"], False), pdata_years=_kv(pdata[pdata.row == "INCE"]),
                dgagri=_kv(dgagri), dgagri1=dict(D1),
                ms_to_agg=[(b, a) for a, b in s.map_rr if a in ("EU014000", "EU013000", "EU27yr19")],
                europ_aggs=["EU014000", "EU013000", "EU27yr19"], breed_act=breed, ncnc=["N_CAL", "N_FAT", "N_PRO"],
                coef_hfcs={"SUGA": 0.92, "MAIZ": 0.60})
    mine = pd.DataFrame([(*k, a, t) for k, (a, t) in E.items()], columns=K + ["abs", "trust"])
    ex = pd.read_csv(R / "Expert.csv.gz", dtype={"t": str})
    tl = pd.read_csv(R / "TrustLevl.csv.gz", dtype={"t": str}).rename(columns={"value": "tref"})
    m = mine.merge(ex[K + ["value"]], on=K, how="left").merge(tl[K + ["tref"]], on=K, how="left")
    m = m[m.t != "2018"].fillna({"value": 0.0, "tref": 0.0})
    m["ok"] = (m["abs"] - m.value).abs() <= 1e-6 * m.value.abs().clip(lower=1e-6)
    m["tok"] = (m.trust - m.tref).abs() < 1e-9
    m["rule"] = m.col.where(~(m.col.isin(breed) & (m.row == "SLGW")), "breed") + "." + m.row
    g = m.groupby("rule").agg(n=("ok", "size"), ok=("ok", "sum"), tok=("tok", "sum"))
    exact = ["NTRD.FRMI", "UAAR.LEVL", "UVAG.SUGA", "UVAG.SUGB", "FEDM.SUGA", "FEDM.SUGB", "LOSM.SUGA", "LOSM.SUGB",
             "N_CAL.INCE", "N_FAT.INCE", "N_PRO.INCE", "breed.SLGW"]
    for r in exact:
        assert g.loc[r, "n"] > 50 and g.loc[r, "ok"] == g.loc[r, "n"] and g.loc[r, "tok"] == g.loc[r, "n"], r
    assert g.loc["SHGM.SGMI", "ok"] == g.loc["SHGM.SGMI", "n"]
    assert not m.col.isin(["PRCI", "INDM"]).any()                          # isoglucose: none, as in CAPTRD
    assert set(g.index) - set(exact) <= {"SHGM.SGMI", "IMPT.SUGB", "EXPT.SUGB"}

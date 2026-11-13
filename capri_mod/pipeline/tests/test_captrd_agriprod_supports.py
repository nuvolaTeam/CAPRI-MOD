"""Parity of CAPTRD's supports from Eurostat's recent production (capri_mod/pipeline/captrd/agriprod_supports.py;
captrd/agriprod_supports.gms) with CAPTRD's Expert and TrustLevl of 2020, on CAPTRD's stored P_Data, data (BAST) and
BASM.

Results on 11 November 2026: the 2020 herds, levels and milk yields of the target animal activities and the member
states' cow milk, every value and trust level equal to CAPTRD's but those a later source sets: national_supports.gms
(its trust levels end in .01; Greece's dairy yields x 0.9 and fattening pigs) and the positions this file deletes for
want of recent data that a later source fills. The bounds (expertLo, expertUp) are not in CAPTRD's stored results.
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import agriprod_supports as A
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import timesets as TS

R = REFERENCE / "captrd_results" / "1770"
DAT = P.SETS_DIR.parent / "dat"
K = ["region", "col", "row", "t"]
EXANTE = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
need = pytest.mark.skipif(not (R / "Expert.csv.gz").exists(), reason="CAPRI reference files not built")


def _ref(name):
    return pd.read_csv(R / f"{name}.csv.gz", dtype={"t": str})


@pytest.fixture(scope="module")
def result():
    s = P.read_sets()
    T = TS.build(1984, 2070, EXANTE, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    I = A.read_inputs(P.SETS_DIR, DAT)
    meat = set(pd.read_csv(P.SETS_DIR / "meat.csv", dtype=str).d0)
    pty = list(s.pact_to_y)
    meat_act = sorted({a for a, m in pty if m in meat and a in set(s.maact)})
    cols = set(I.one("agriprodaact")) | {"DCOL", "DCOH", "GROF"} | set(meat_act)
    pdd = _ref("P_Data")
    pdd = pdd[pdd.t.str.isdigit() & pdd.col.isin(cols)]
    pdata = {(r, c, w, int(t)): v for r, c, w, t, v in zip(pdd.region, pdd.col, pdd.row, pdd.t, pdd.value)}
    d = _ref("data")
    d = d[(d.t == "BAST") & d.col.isin(cols)]
    bm = _ref("BASM")
    bm = bm[bm.t == "2070"]
    runr = list(s.ms) + (["BL400000"] if "BL000000" in s.ms else [])
    res = A.supports(I, runr=runr, s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, exante=T.exante,
                     exantet=T.exantet, base_year=2017, lst_expostt=T.lst_expostt,
                     basm={(r, c, w): v for r, c, w, v in zip(bm.region, bm.col, bm.row, bm.value)}, pdata=pdata,
                     bast={(r, c, w): v for r, c, w, v in zip(d.region, d.col, d.row, d.value)}, dcow=["DCOL", "DCOH"],
                     meat_act=meat_act, pact_to_y=pty, prior={})
    return res


#: national_supports.gms's own rules for Greece after this file: dairy yields x 0.9 (l. 531-534), the fattening pigs'
#: herd (l. 549-559)
EL_NATIONAL = {"DCOL.COMI", "DCOH.COMI", "PIGF.HERD"}


@pytest.mark.slow
@need
def test_agriprod_supports_equal_captrds(result):
    mine = pd.DataFrame([(*k[:3], str(k[3]), v, result.trust.get(k, 0.0)) for k, v in result.absolute.items()
                         if k[3] == 2020], columns=K + ["abs", "trust"])
    ex, tl = _ref("Expert"), _ref("TrustLevl").rename(columns={"value": "tref"})
    m = mine.merge(ex[K + ["value"]], on=K, how="left").merge(tl[K + ["tref"]], on=K, how="left").fillna(0.0)
    m["ok"] = (m["abs"] - m.value).abs() <= 1e-6 * m.value.abs().clip(lower=1e-6)
    m["tok"] = (m.trust - m.tref).abs() < 1e-9
    m["pos"] = m.col + "." + m.row
    # later sources: national_supports.gms's trust levels end in .01 (and its Greek rules); a position this file
    # deletes (no recent data) may get a later source's support
    national = ((m.tref * 100).round().astype(int) % 100 == 1) | ((m.region == "EL000000") & m.pos.isin(EL_NATIONAL))
    refilled = (m["abs"] == 0) & ((m.value != 0) | (m.tref != 0))
    rest = m[~national & ~refilled]
    assert len(m) > 1150 and len(rest) > 1050 and rest.ok.all() and rest.tok.all()
    assert int(national.sum()) < 100 and int(refilled.sum()) < 100
    # the PercentChange supports deleted: those of every position this file trusts (l. 420-421, 485-487)
    assert result.no_percent == set(result.trust)

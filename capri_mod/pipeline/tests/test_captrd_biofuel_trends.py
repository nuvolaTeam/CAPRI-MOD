"""Parity of CAPTRD's biofuel trends (capri_mod/pipeline/captrd/biofuel_trends.py; biofuel/biofuel_trends.gms) with
CAPTRD's Expert and TrustLevl of the years after 2018, chained to the Aglink stage (p_aglink, p_BFyld) and on CAPTRD's
stored P_Data, data (nObs), BASM and Step 1.

Results on 11 November 2026, the years 2020-2070, the positions this file writes, over CAPTRD's estimated columns and
rows: all 28,798 values equal, and the trust levels as CAPTRD stores them (the expert's, else 10, where a value exists:
define_stats_and_supports.gms l. 637-645), but for two later stages' changes: the sugar feedstock where sugar production
has no nObs, removed by adjust_to_biof_supports.gms l. 177 (define_stats_and_supports.gms l. 597); EPS levels of the new
energy crops after %phaseInYr%, given trust 1 by longrun_supports.gms l. 530-544.
Found on the way: GAMS evaluates an assignment's right side on the values from before the statement (the cereal and
sugar shares, l. 536-543: Germany's sugar feedstock in 2020 is 192.464 so, 180.813 with the values already written);
the reference run did not apply %constBionergy% (settings captrd.const_bioenergy); p_data's INHA.LEVL after 2018 is
not yet there (no fuel use per inhabitant, no EXPD of fuels in CAPTRD's results).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import biofuel_trends as B
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import timesets as TS
from capri_mod.pipeline.tests.test_captrd_aglink import A, aglink_p, dgagri, need  # noqa: F401

R = REFERENCE / "captrd_results" / "1770"
DAT = P.SETS_DIR.parent / "dat"
K = ["region", "col", "row", "t"]
EXANTE = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]


def _one(name):
    return pd.read_csv(P.SETS_DIR / f"{name}.csv", keep_default_na=False, dtype=str).d0.str.upper().tolist()


def _ref(name):
    return pd.read_csv(R / f"{name}.csv.gz", dtype={"t": str})


def run(aglink, const_bio=False):
    s = P.read_sets()
    T = TS.build(1984, 2070, EXANTE, 2017, TS.lst_dgagri_for("aglink2023dgAgri"), uaar_years_any=range(1984, 2019),
                 uaar_years_all=range(1995, 2019), expostt_extra=[2019])
    biostock = _one("biostock")
    bio_rows = {"BIOD", "BIOE", "DISL", "GASL", "CRDO", "DDGS"} | set(biostock)
    pdd = _ref("P_Data")
    pdd = pdd[pdd.t.str.isdigit() & (pdd.row.isin(bio_rows) | ((pdd.col == "INHA") & (pdd.row == "LEVL")))]
    # INHA.LEVL after CAPREG's years is not yet in p_data at this point (test_captrd_scale_dgagri.py)
    pdd = pdd[~((pdd.col == "INHA") & (pdd.t.astype(int) > 2018))]
    pdata = {(r, c, w, int(t)): v for r, c, w, t, v in zip(pdd.region, pdd.col, pdd.row, pdd.t, pdd.value)}
    d = _ref("data")
    nobs = {(r, c, w) for r, c, w in zip(*[d[d.t == "nObs"][k] for k in ("region", "col", "row")])}
    bm = _ref("BASM")
    bm = bm[bm.t == "2070"]
    basm = {(r, c, w): v for r, c, w, v in zip(bm.region, bm.col, bm.row, bm.value)}
    src = A.ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "biofuel" / "biofuel_technology_params_"
    dens = pd.read_parquet(f"{src}p_density.parquet").set_index("fuel").value.astype(float).to_dict()
    oil = pd.read_parquet(f"{src}p_oilEqu.parquet").set_index("fuel").value.astype(float).to_dict()
    ex = pd.read_csv(DAT / "p_extrrates.csv")
    bp = pd.read_csv(DAT / "p_byproduct.csv")
    ms = list(s.ms)
    nt2 = sorted({b for a, b in s.map_rr if a in set(ms) and b in set(s.nt2ext)})
    res = B.trends(
        B.read_inputs(P.SETS_DIR, DAT), ms=ms, msincl=ms, msall=s.msall, nt2est=nt2, years=range(1984, 2071),
        expostt=T.expostt, exante=T.exante, exantet=T.exantet, lst_dgagri=T.lst_dgagri, basy=2017, pdata=pdata,
        nobs=nobs, basm=basm, step1={}, aglink=dict(aglink), bfyld=aglink.bfyld,
        extr_rates={(f, st): v for f, st, v in zip(ex.fuel, ex.stock, ex.value)},
        byproduct={(b, st): v for b, st, v in zip(bp.byproduct, bp.stock, bp.value)},
        oilequ={k.upper(): v for k, v in oil.items()}, density={k.upper(): v for k, v in dens.items()},
        s_colsest=s.s_colsest, s_rowsest=s.s_rowsest, map_rr=s.map_rr, seco_biof=_one("seco_biof"),
        fossil_fuels=["GASL", "DISL"], fuels=_one("fuels"), biostock=biostock, biostock_oilp=_one("biostockoilp"),
        stock_to_fuel=[tuple(x) for x in pd.read_csv(P.SETS_DIR / "stock_to_fuel.csv", dtype=str)[["d0", "d1"]].values],
        stock_to_by=[tuple(x) for x in pd.read_csv(P.SETS_DIR / "stock_to_by.csv", dtype=str)[["d0", "d1"]].values],
        bio_by=_one("bio_by"), cere=_one("cere"), balpos=_one("balpos"), const_bio=const_bio)
    res.regions = ms + nt2
    return res, T


def compare(res, T):
    """The years after 2018. CAPTRD stores the estimated columns and rows (S_ColsEst x S_RowsEst), with a trust level only
    where the expert support is nonzero or EPS: the expert's own, else 10 (define_stats_and_supports.gms l. 637-645)."""
    s = P.read_sets()
    ce, re_ = set(s.s_colsest), set(s.s_rowsest)
    rows = []
    for (r, c, w, y), (a, t) in res.expert.items():
        if y in set(T.exantet) and c in ce and w in re_:
            has = a != 0.0 or (r, c, w, y) in res.eps
            rows.append((r, c, w, str(y), a, (t or 10.0) if has else 0.0, (r, c, w, y) in res.eps))
    mine = pd.DataFrame(rows, columns=K + ["abs", "trust", "eps_m"])
    ex, tl = _ref("Expert"), _ref("TrustLevl").rename(columns={"value": "tref"})
    m = mine.merge(ex[K + ["value", "eps"]], on=K, how="outer").merge(tl[K + ["tref"]], on=K, how="left")
    m = m[m.t.isin([str(y) for y in T.exantet]) & m.region.isin(set(res.regions))]
    m = m.fillna({"abs": 0.0, "trust": 0.0, "value": 0.0, "tref": 0.0, "eps": 0}).infer_objects()
    m["eps_m"] = m.eps_m.fillna(False).astype(bool)
    m["ok"] = (m["abs"] - m.value).abs() <= 1e-6 * m.value.abs().clip(lower=1e-6)
    m["tok"] = (m.trust - m.tref).abs() < 1e-9
    m["pos"] = m.col + "." + m.row
    return m


@pytest.mark.slow
@need
def test_biofuel_trends_equal_captrds(aglink_p):  # noqa: F811
    res, T = run(aglink_p, False)
    m = compare(res, T)
    nobs = set(zip(*[_ref("data").query("t == 'nObs'")[k] for k in ("region", "col", "row")]))
    # removed later: the sugar feedstock where sugar production has no nObs (define_stats_and_supports.gms l. 597,
    # adjust_to_biof_supports.gms l. 177); EPS levels after %phaseInYr% take longrun_supports.gms's trust 1 (l. 530-544)
    later = ((m.pos == "BIOF.SUGA") & ~pd.Series([(r, "MAPR", "SUGA") in nobs for r in m.region], index=m.index))
    eps_lr = (m.pos == "NECR.LEVL") & m.eps_m & (m.tref == 1.0)
    mine = m[m.pos.isin(set(m[m["abs"] != 0].pos))]       # the positions this file writes
    k = mine[~later[mine.index]]
    assert len(k) > 28000 and k.ok.all()
    assert k[~eps_lr[k.index]].tok.all()
    assert int(eps_lr.sum()) < 40 and int(later.sum()) < 100

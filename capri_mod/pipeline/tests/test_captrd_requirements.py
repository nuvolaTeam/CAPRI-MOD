"""Parity of CAPTRD's animal requirement functions (capri_mod/pipeline/captrd/requirements.py) with CAPTRD's own
Const, Slope and Step1 (capri_sources/reference/captrd_results/1770), on CAPTRD's own inputs to the step: its stored
p_data of the ex-post years (P_Data), the base values (BASM, in 2030), the animals' LEVL nObs and the feeds' energy and
protein contents (respos data).

Results on 10 November 2026:
  - energy and protein (ENNE, CRPR), 9,672 series: the fitted base-year requirement Const + Slope x yields' BASM equals
    CAPTRD's in every series; Const and Slope themselves in 9,429. The other 243 are regressions on a constant yield
    (the young animals' YBUL, YHEI, YCOW at 1000 heads per head): Sxx is zero up to rounding, so the split between
    Const and Slope is rounding noise that depends on the order of the sums, and only the fit is determined;
  - fibre and dry matter (FILG, FICT, FISM, FISF): CAPTRD's results do not store the feeds' contents of these, so the
    scaling to the base-year feed (step 3) cannot be recomputed here; the regression is checked by the scale-free
    identity Const0 x Slope_ref = Const_ref x Slope0 (818 series with a slope, 4 of them a slope of rounding size);
  - Step1 (define_stats_and_supports.gms l. 86-93) from CAPTRD's Const, Slope and yields' Step1: equal in every one of
    the 1,726 series CAPTRD stores (almost all national; largest relative difference 2.7e-13).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd import requirements as RQ

R = REFERENCE / "captrd_results" / "1770"
EXPOST = range(1984, 2019)          # ExPost of the reference run: CAPREG's years with UAAR (timesets, test_captrd_step1)
need = pytest.mark.skipif(not (R / "P_Data.csv.gz").exists(), reason="CAPRI reference files not built")


def _eq(a, b, rel=1e-6):
    return (a - b).abs() <= rel * b.abs().clip(lower=1e-9)


@pytest.fixture(scope="module")
def ref():
    sets = P.read_sets()
    cols = set(sets.maact) | set(sets.reqst)

    def rd(f):
        d = pd.read_csv(R / f, dtype={"t": str})
        return d[d.col.isin(cols)]
    pdat = rd("P_Data.csv.gz")
    pdat = pdat[pdat.t.str.fullmatch(r"\d{4}")]
    bm = rd("BASM.csv.gz")
    bm = bm[bm.t == "2030"].assign(t="BASM")
    da = rd("data.csv.gz")
    p = pd.concat([pdat, bm, da[(da.t == "nObs") & (da.row == "LEVL")],
                   da[(da.t == "BASM") & da.col.isin(sets.reqst)]], ignore_index=True)[["region", "col", "row", "t", "value"]]
    co = RQ.coefficients(p, sets, EXPOST, zeros_as_missing=True)
    cr = da[da.t.isin(["Const", "Slope"])].pivot_table(index=RQ.KEYS, columns="t", values="value",
                                                       aggfunc="first").fillna(0.0)
    J = co.join(cr, rsuffix="_ref", how="outer").fillna(0.0)
    J = J[(J[["Const", "Slope", "Const_ref", "Slope_ref"]] != 0).any(axis=1)]
    ys = {}
    for a, o in sets.pact_to_y:
        ys.setdefault(a, set()).add(o)
    bmi = bm.set_index(RQ.KEYS).value
    J["ybasm"] = [sum(bmi.get((r, a, o), 0.0) for o in ys.get(a, ())) for r, a, _ in J.index]
    return sets, J


@pytest.mark.slow
@need
def test_energy_and_protein_requirements_match_captrd(ref):
    _, J = ref
    X = J[J.index.get_level_values("row").isin(["ENNE", "CRPR"])]
    fit_ref = X.Const_ref + X.Slope_ref * X.ybasm
    assert len(X) > 9000
    assert _eq(X.BASM, fit_ref).all()
    coef = _eq(X.Const, X.Const_ref) & _eq(X.Slope, X.Slope_ref)
    assert coef.mean() > 0.97


@pytest.mark.slow
@need
def test_fibre_and_dry_matter_regressions_match_captrd_up_to_the_feed_scaling(ref):
    _, J = ref
    F = J[~J.index.get_level_values("row").isin(["ENNE", "CRPR"]) & (J.Slope_ref.abs() > 1e-9)]
    assert len(F) > 800
    assert _eq(F.Const0 * F.Slope_ref, F.Const_ref * F.Slope0).all()


@pytest.mark.slow
@need
def test_requirement_step1_matches_captrd(ref):
    sets, J = ref
    s1 = pd.read_csv(R / "step1.csv.gz", dtype={"t": str})
    s1 = s1[s1.col.isin(sets.maact) & s1.t.str.fullmatch(r"\d{4}")]
    S = s1.pivot_table(index=RQ.KEYS, columns="t", values="value", aggfunc="first")
    S = S[[c for c in S.columns if int(c) >= 2018]]
    co = J[["Const_ref", "Slope_ref"]].rename(columns={"Const_ref": "Const", "Slope_ref": "Slope"})
    co = co[(co != 0).any(axis=1)]
    req = S[S.index.get_level_values("row").isin(sets.reqst)]
    nobs = pd.Series(1.0, index=req.index)
    out = RQ.step1(co, nobs, S, sets)
    common = out.index.intersection(req.index)
    assert len(common) > 1700           # CAPTRD stores the requirements' Step1 for the countries (and a few NUTS 2)
    a, b = out.loc[common, req.columns].to_numpy(float), req.loc[common].to_numpy(float)
    m = ~np.isnan(b)
    assert np.allclose(a[m], b[m], rtol=1e-9, atol=1e-9)


def test_a_region_without_observed_herd_loses_its_requirement_coefficients():
    """prep_requirement_estimation.gms l. 61-71: the feed scaling factor is 0 where the animal's LEVL has no nObs, and
    Const, Slope and the requirement's BASM become 0 (as coded)."""
    sets = P.CaptrdSets(ms=["DK000000"], map_rr={("DK000000", "DK000000"), ("DK000000", "DK010000")}, urbannuts=set(),
                        srnuts2={"DK010000"}, s_colsest=set(), s_rowsest=set(), cols_load=set(), rows_load=set(),
                        reqsc=set(), secom=set(), landusearto=set(), quotas=set(), bio_cols=set(), biorepcols=set(),
                        seco_biof=set(), mpact={"DCOL"}, maact={"DCOL"}, pact_to_io=set(), pact_to_i=set(), iyani=set(),
                        fix_yai=set(), rmaggsup=set(), rms_to_rm=set(), feed={"FGRA"}, pact_to_y={("DCOL", "COMI")},
                        reqst={"ENNE"})
    rows = [("DK000000", "DCOL", "COMI", str(t), 5000.0 + 50 * i) for i, t in enumerate(EXPOST)]
    rows += [("DK000000", "DCOL", "ENNE", str(t), 20000.0 + 150 * i) for i, t in enumerate(EXPOST)]
    rows += [(r, "DCOL", "LEVL", "BASM", 100.0) for r in ("DK000000", "DK010000")]
    rows += [(r, "DCOL", "COMI", "BASM", 7000.0) for r in ("DK000000", "DK010000")]
    rows += [(r, "DCOL", "FGRA", "BASM", 5000.0) for r in ("DK000000", "DK010000")]
    rows += [("DK000000", "DCOL", "LEVL", "nObs", 35.0), ("DK000000", "ENNE", "FGRA", "BASM", 9.0)]
    p = pd.DataFrame(rows, columns=["region", "col", "row", "t", "value"])
    co = RQ.coefficients(p, sets, EXPOST, zeros_as_missing=True)
    dk, reg = co.loc[("DK000000", "DCOL", "ENNE")], co.loc[("DK010000", "DCOL", "ENNE")]
    assert dk.Slope0 == pytest.approx(3.0) and dk.Const0 == pytest.approx(5000.0)
    assert dk.BASM == pytest.approx(45000.0)                     # the base-year ration's energy, 5000 x 9
    assert reg.Slope0 == pytest.approx(3.0) and reg.Const0 == 0.0   # Const copied only where LEVL has nObs
    assert reg.scale == 0.0 and reg.Const == reg.Slope == reg.BASM == 0.0

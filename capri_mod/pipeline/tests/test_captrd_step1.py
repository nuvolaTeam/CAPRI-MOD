"""Tests of CAPTRD Step 1 (capri_mod/pipeline/captrd/step1.py).

The closed-form WLS of estimate_trends.gms is checked against an independent weighted least squares (numpy lstsq)
at every grid point; the GAMS domain rules for short series are checked case by case; one test runs on CAPRI's own
CAPREG time series when the reference CSV is present (capri_reference/, built by
tools/build/build_capreg_tseries_reference.py).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from capri_mod.pipeline.captrd import step1 as s1

YEARS = list(range(1984, 2019))
W = s1.trend_variable(YEARS, 1984)
REF = Path(__file__).resolve().parents[3] / "capri_reference" / "capreg_tseries" / "17"


def _lstsq_fit(x, w, grid):
    """Independent fit: for each c, WLS of x on (1, t^c) with weights t; the c of least wESS (first on ties)."""
    m = np.isfinite(x) & (x != 0)                 # observations: neither NaN nor (CAPRI) zero
    best = None
    for k, c in enumerate(grid):
        X = np.column_stack([np.ones(m.sum()), w[m] ** c])
        sw = np.sqrt(w[m])
        coef, *_ = np.linalg.lstsq(X * sw[:, None], x[m] * sw, rcond=None)
        wess = float((((x[m] - X @ coef) ** 2) * w[m]).sum())
        if best is None or wess < best[0] - 1e-12 * max(1.0, best[0]):
            best = (wess, coef[0], coef[1], c, k)
    return best


def test_trend_variable_starts_at_one_tenth():
    assert W[0] == pytest.approx(0.1)
    assert s1.trend_variable([2017], 1984)[0] == pytest.approx(3.4)


def test_grid_matches_gams():
    g = s1.c_grid(0.02, 1.2, 30)
    assert g[0] == pytest.approx(0.02) and g[-1] == pytest.approx(1.2)
    assert g[1] - g[0] == pytest.approx((1.2 - 0.02) / 29)


def test_closed_form_equals_independent_wls():
    rng = np.random.default_rng(7)
    grid = s1.c_grid(0.02, 1.2, 30)
    x = np.empty((40, len(YEARS)))
    for i in range(40):
        a, b, c = rng.uniform(50, 500), rng.uniform(-30, 80), rng.uniform(0.05, 1.15)
        x[i] = a + b * W ** c + rng.normal(0, 8, len(YEARS))
    x[3, :10] = 0.0                       # a series starting later
    x[5, [4, 9, 20]] = 0.0                # gaps
    pre = s1.prestats(x, W, zeros_as_missing=True)
    f = s1.fit(x, W, pre.nobs, grid, as_coded=True, zeros_as_missing=True)
    for i in range(len(x)):
        wess, a, b, c, k = _lstsq_fit(x[i], W, grid)
        assert f.k_opt[i] == k
        assert f.c[i] == pytest.approx(c)
        assert f.a[i] == pytest.approx(a, rel=1e-8, abs=1e-6)
        assert f.b[i] == pytest.approx(b, rel=1e-8, abs=1e-6)
        assert f.wess[i] == pytest.approx(wess, rel=1e-8)


def test_prestats_weighted_mean_and_variance():
    x = np.full(len(YEARS), np.nan)            # missing years: NaN
    x[-5:] = [10, 12, 11, 13, 14]
    pre = s1.prestats(x, W)
    w = W[-5:]
    m = (x[-5:] * w).sum() / w.sum()
    assert pre.nobs[0] == 5 and pre.nw[0] == pytest.approx(w.sum())
    assert pre.wave[0] == pytest.approx(m)
    assert pre.wvar[0] == pytest.approx(((x[-5:] - m) ** 2 * w).sum() / (w.sum() - 1))


def test_three_or_four_observations_linear_when_fixed():
    x = np.full(len(YEARS), np.nan)            # missing years: NaN
    x[-3:] = [100.0, 104.0, 107.0]
    pre = s1.prestats(x, W)
    f = s1.fit(x, W, pre.nobs, as_coded=False)
    wess, a, b, c, _ = _lstsq_fit(x, W, [1.0])
    assert f.c[0] == 1.0 and f.a[0] == pytest.approx(a) and f.b[0] == pytest.approx(b)


def test_three_or_four_observations_as_coded_fall_to_zero():
    """As coded, the zeroed grid points 2..30 win the minimum: a = b = c = 0 unless c = 1 fits exactly."""
    x = np.full(len(YEARS), np.nan)            # missing years: NaN
    x[-3:] = [100.0, 104.0, 107.0]
    pre = s1.prestats(x, W)
    f = s1.fit(x, W, pre.nobs, as_coded=True)
    assert (f.a[0], f.b[0], f.c[0], f.k_opt[0]) == (0.0, 0.0, 0.0, 1)
    # an exact straight line: wESS at c = 1 is (numerically) zero; the first point is kept only if exactly zero
    y = np.full(len(YEARS), np.nan)            # missing years: NaN
    y[-3:] = 5.0
    f2 = s1.fit(y, W, s1.prestats(y, W).nobs, as_coded=True)
    assert f2.k_opt[0] in (0, 1)


def test_one_or_two_observations():
    x = np.full(len(YEARS), np.nan)            # missing years: NaN
    x[-2:] = [10.0, 14.0]
    pre = s1.prestats(x, W)
    fixed = s1.fit(x, W, pre.nobs, as_coded=False)
    m = (x[-2:] * W[-2:]).sum() / W[-2:].sum()
    assert fixed.a[0] == pytest.approx(m) and fixed.b[0] == 0.0 and fixed.c[0] == 0.0
    coded = s1.fit(x, W, pre.nobs, as_coded=True)
    assert coded.a[0] == 0.0                     # the zeroed second grid point wins
    one = np.full(len(YEARS), np.nan)            # missing years: NaN
    one[-1] = 7.0                                # a single observation fits exactly: kept either way
    assert s1.fit(one, W, s1.prestats(one, W, zeros_as_missing=True).nobs, as_coded=True,
                  zeros_as_missing=True).a[0] == pytest.approx(7.0)


def test_error_variance_and_r2_rules():
    x = np.full((2, len(YEARS)), np.nan)
    x[0, -2:] = [10.0, 14.0]
    x[1] = 50.0                                   # constant: wVar = 0 -> wR2 = 1
    r = s1.run(x, YEARS, [2030], first_year=1984, as_coded=False)
    assert r.wvarerr[0] == pytest.approx(0.25 * r.pre.wave[0] ** 2)
    assert r.pre.wvar[1] == 0.0 and r.wr2[1] == 1.0
    assert r.wr2[0] == 1.0                        # nObs = 2: wVar not assigned -> 1


def test_zeros_and_missing_values():
    """Register FIX-8: CAPRI reads a zero as missing (zeros_as_missing = true); the fix counts a recorded zero."""
    x = np.full(len(YEARS), np.nan)
    x[-6:] = [3.0, 0.0, 4.0, 5.0, 0.0, 6.0]
    capri = s1.prestats(x, W, zeros_as_missing=True)
    fixed = s1.prestats(x, W, zeros_as_missing=False)
    assert capri.nobs[0] == 4 and fixed.nobs[0] == 6
    assert fixed.wave[0] < capri.wave[0]                  # the two zeros enter the weighted mean
    # without recorded zeros (NaN for the missing years) the two agree
    y = np.where(x == 0.0, np.nan, x)
    r_c = s1.run(y, YEARS, [2030], first_year=1984, zeros_as_missing=True)
    r_f = s1.run(y, YEARS, [2030], first_year=1984, zeros_as_missing=False)
    assert np.array_equal(r_c.step1, r_f.step1) and np.array_equal(r_c.wvarerr, r_f.wvarerr)


@pytest.mark.skipif(not (REF / "AT.csv.gz").exists(), reason="CAPRI reference time series not built")
def test_runs_on_capri_capreg_series():
    import pandas as pd
    d = pd.read_csv(REF / "AT.csv.gz", dtype={"t": str})
    d = d[d.t.str.fullmatch(r"\d{4}") & (d.region == "AT000000") & (d.row == "YILD")]
    wide = d.pivot_table(index="col", columns="t", values="value", aggfunc="first").reindex(
        columns=[str(y) for y in YEARS])                    # absent: NaN, missing
    r = s1.run(wide.to_numpy(), YEARS, [2030], first_year=1984)
    ok = r.pre.nobs > 4
    assert ok.sum() > 10
    assert np.isfinite(r.step1[ok]).all()
    assert ((r.fit.c[ok] >= 0.02 - 1e-12) & (r.fit.c[ok] <= 1.2 + 1e-12)).all()


# --- parity with CAPTRD's own Step 1 (capri_reference/captrd_results/1770, tools/build/build_captrd_results_reference.py)

RES = Path(__file__).resolve().parents[3] / "capri_reference" / "captrd_results" / "1770"


def _parity_frame():
    """Our Step 1 on CAPTRD's own estimation data p_result(..., 'p_data') against its statistics and Step1."""
    import pandas as pd
    st = pd.read_csv(RES / "data.csv.gz").pivot_table(index=["region", "col", "row"], columns="t", values="value",
                                                       aggfunc="first").fillna(0.0)
    pdat = pd.read_csv(RES / "P_Data.csv.gz", dtype={"t": str})
    pdat = pdat[pdat.t.str.fullmatch(r"\d{4}")]
    # ExPostT: years with UAAR in any country (captrd.gms l. 721-722); p_data carries projections after them
    u = pdat[(pdat.col == "UAAR") & (pdat.row == "LEVL") & pdat.region.str.endswith("000000") & (pdat.value != 0)]
    years = sorted(int(t) for t in u.t.unique())
    # the ex-post years end where the CAPREG/COCO data end: the first gap in the UAAR years ends them
    expost = [years[0]]
    for y in years[1:]:
        if y != expost[-1] + 1:
            break
        expost.append(y)
    x = pdat[pdat.t.astype(int).isin(expost)].pivot_table(index=["region", "col", "row"], columns="t",
                                                          values="value", aggfunc="first")
    x = x.reindex(columns=[str(y) for y in expost]).fillna(0.0)
    x = x[x.index.isin(st.index)]
    ref = st.reindex(x.index)
    r = s1.run(x.to_numpy(), expost, [2030], nobs=ref.nObs.to_numpy(), first_year=1984, as_coded=True,
               zeros_as_missing=True)
    s = pd.read_csv(RES / "step1.csv.gz", dtype={"t": str})
    s = s[s.t == "2030"]
    s1ref = s.set_index(["region", "col", "row"]).value
    # DOMM is re-aggregated from its components in every reported position, the estimated one kept under DEMD
    # (aggreg_and_report.gms l. 293-294); NTRD is overwritten with EXPT - IMPT (l. 296) and not kept
    demd = s[s.col == "DEMD"].assign(col="DOMM").set_index(["region", "col", "row"]).value
    out = pd.DataFrame({"nobs_ref": ref.nObs, "nobs": (x.to_numpy() != 0).sum(axis=1), "wave_ref": ref.WAve,
                        "wave": r.pre.wave, "wr2_ref": ref.wR2, "wr2": r.wr2, "s1": r.step1[:, 0],
                        "s1_ref": s1ref.reindex(x.index).fillna(0.0)}, index=x.index)
    m = out.index.get_level_values(1) == "DOMM"
    out.loc[m, "s1_ref"] = demd.reindex(out.index[m]).fillna(0.0).to_numpy()
    return out, expost


@pytest.mark.slow
@pytest.mark.skipif(not (RES / "P_Data.csv.gz").exists(), reason="CAPTRD reference results not built")
def test_parity_with_captrd_step1():
    out, expost = _parity_frame()
    assert (expost[0], expost[-1]) == (1984, 2019)
    c = out[(out.nobs_ref > 0) & (out.nobs == out.nobs_ref) & (out.index.get_level_values(1) != "NTRD")]
    assert len(c) > 90000
    assert np.isclose(c.wave, c.wave_ref, rtol=1e-7, atol=1e-9).mean() > 0.999
    assert np.isclose(c.wr2, c.wr2_ref, rtol=1e-7, atol=1e-9).mean() > 0.998
    # Step 1 at 2030: equal for 99.78% (23 October 2026); the rest are product groups and NUTS2 land items that
    # CAPTRD recomputes after Step 1
    assert np.isclose(c.s1, c.s1_ref, rtol=1e-7, atol=1e-9).mean() > 0.997
    # CAPRI's code for 2-4 observations (the minimum over the zeroed grid points): Step 1 = 0
    short = c[c.nobs.between(2, 4)]
    assert len(short) > 50 and (short.s1_ref == 0).mean() > 0.98 and (short.s1 == short.s1_ref).mean() > 0.98


def test_time_sets_of_the_reference_configuration():
    """Base 2017, CAPREG to 2018, COCO 2019, simulation years 2018-2070, %lst_dgagri% 2030 (results_1770.gdx)."""
    from capri_mod.pipeline.captrd import timesets as ts
    resy = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
    T = ts.build(1984, 2070, resy, 2017, 2030, uaar_years_any=range(1984, 2019), uaar_years_all=range(1995, 2019),
                 expostt_extra=[2019], basyrs5_halfwidth=3)
    assert T.years_est == [1985, 1990, 1995, 2000] + resy           # CAPTRD's Step1 years in results_1770.gdx
    assert (T.expostt[0], T.expostt[-1], T.lst_expost) == (1984, 2019, 2018)
    assert (T.fst_exante, T.sec_exante, T.startpoint_extrap) == (2018, 2020, 2019.0)
    assert T.bast == 2018 and T.basyrst == [2017, 2018, 2019]
    assert T.basyrs5 == [2014, 2015, 2016, 2017, 2018]               # "5 years": ExPost ends at BAS + 1
    assert T.basyrsm == [2016, 2017, 2018] and T.eightlst == list(range(2011, 2019))
    assert T.exanted == [2018] and T.all_last_expost == 2017 and T.before[0] == (2018, 2017)
    assert T.p_trend[1984] == pytest.approx(0.1)

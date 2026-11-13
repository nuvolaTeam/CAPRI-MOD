"""Tests of the equations of CAPTRD's member-state estimation m_trendMS (capri_mod/pipeline/captrd/estimate_ms.py).

Each equation of equations.gms is evaluated at CAPTRD's own solution, step2 of the reference run results_1770
(capri_sources/reference/captrd_results/1770, tools/build/build_captrd_results_reference.py): its residual must be
zero (at most zero, at least zero for the inequalities). The stored step2 is the estimation's solution after CAPTRD's
reporting, which estimate_ms.from_stored undoes (the requirements back to their relative form, DOMM from DEMD); the
equations whose terms the reporting overwrites or that hold free variables CAPTRD does not store are left out
(estimate_ms.REPORTED, checkable). The feed contents of the fibre and fill requirements and the empty days (p_data
BASM of FILG, FICT, FISM, FISF and EDAYS), which the reference does not hold, are those of the port's own data
preparation (prepare.load_basm, tested against CAPTRD's in test_captrd_prepare.py).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.csvio import read_csv
from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import prepare as P

RES = REFERENCE / "captrd_results" / "1770"
TS_DIR, BASE_DIR = REFERENCE / "capreg_tseries" / "17", REFERENCE / "capreg_base" / "17"
OAGG = REFERENCE / "sets" / "simini_21730" / "OAGG.csv"
#: the reference run's ex-ante years with data (ExAnteD = ExAnte and ExPostT, captrd.gms l. 761-762): 2018
EXANTE_D_LAST = 2019
TOL = 1e-3

needs_reference = pytest.mark.skipif(
    not all(f.exists() for f in [RES / "step2.csv.gz", RES / "data.csv.gz", OAGG, TS_DIR / "DK.csv.gz"]),
    reason="CAPTRD reference results not present (capri_sources/reference)")


def _by_year(name, ms, years):
    d = read_csv(RES / f"{name}.csv.gz", dtype={"t": str}, keep_default_na=False)
    d = d[(d.region == ms) & d.t.isin(years)]
    return {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}


def _prepared_basm(ms):
    """The port's BASM of the fill and fibre contents and of EDAYS (prepare_run.py pass 1)."""
    s = P.read_sets()
    years = list(range(1984, 2019))
    cc = ms[:2]
    raw = P.read_series(TS_DIR / f"{cc}.csv.gz", s, years)
    p = P.load_basm(P.load_fixes(raw, s), read_csv(BASE_DIR / f"{cc}.csv.gz", keep_default_na=False), s)
    p = p[(p.region == ms) & (p.t == "BASM")]
    return {(c, w): float(v) for c, w, v in zip(p.col, p.row, p.value)
            if c in ("FILG", "FICT", "FISM", "FISF") or w == "EDAYS"}


def _check(ms, years):
    S = E.read_sets()
    oagg = set(read_csv(OAGG, keep_default_na=False).d0)
    d = read_csv(RES / "data.csv.gz", dtype={"t": str}, keep_default_na=False)
    d = d[d.region == ms]
    data = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}
    nobs = {k for k, v in data.get("nObs", {}).items() if v}
    tabs = {n: _by_year(n, ms, years) for n in ("step2", "P_Data", "COCO", "support", "Lo", "up", "BASM")}
    prep = _prepared_basm(ms)
    n_eq, bad = 0, []
    for y in years:
        basm = dict(prep)
        basm.update(data.get("BASM", {}))
        basm.update(tabs["BASM"].get(y, {}))
        kw = dict(nobs=nobs, bas=data.get("BAS", {}), basm=basm, const=data.get("Const", {}),
                  slope=data.get("Slope", {}), pdata=tabs["P_Data"].get(y, {}), coco=set(tabs["COCO"].get(y, {})),
                  support=tabs["support"].get(y, {}), lo=tabs["Lo"].get(y, {}), up=tabs["up"].get(y, {}),
                  year=int(y), exante_d=int(y) <= EXANTE_D_LAST)
        st = tabs["step2"][y]
        V = E.from_stored(E.Point(V=st, **kw), S, st)
        res = [r for r in E.residuals(E.Point(V=V, **kw), S)
               if E.checkable(r[0], r[1], oagg, nobs=nobs, mlko=S.mlko)]
        n_eq += len(res)
        bad += [(y,) + b for b in E.violations(res, TOL)]
    return n_eq, bad


@needs_reference
def test_denmark_equations_hold_at_captrds_step2():
    n_eq, bad = _check("DK000000", ["2018", "2020", "2025", "2030", "2040", "2050"])
    assert n_eq > 4000
    assert not bad, bad[:10]


@pytest.mark.slow
@needs_reference
@pytest.mark.parametrize("ms", ["AT000000", "ES000000", "IT000000", "NL000000", "PL000000", "NO000000"])
def test_more_countries_equations_hold_at_captrds_step2(ms):
    n_eq, bad = _check(ms, ["2018", "2030", "2050"])
    assert n_eq > 1500
    assert not bad, bad[:10]


def test_requirements_relative_inverts_captrds_reporting():
    """captrd.gms l. 1205-1218: stored = (Const + Slope x main output) x 0.998^(year - 2000) x relative."""
    S = E.read_sets()
    p = E.Point(V={}, nobs={("DCOH", "LEVL"), ("DCOH", "COMI")}, bas={}, basm={("DCOH", "ENNE"): 50000.0},
                const={("DCOH", "ENNE"): 24000.0}, slope={("DCOH", "ENNE"): 3.5}, pdata={}, coco=set(), support={},
                lo={}, up={}, year=2030)
    rel = 1.03
    stored = {("DCOH", "COMI"): 12000.0}
    stored[("DCOH", "ENNE")] = (24000.0 + 3.5 * 12000.0) * 0.998 ** 30 * rel
    out = E.requirements_relative(p, S, stored)
    assert out[("DCOH", "ENNE")] == pytest.approx(rel)
    assert out[("DCOH", "COMI")] == 12000.0


def test_reqs_residual_and_inequality_senses():
    S = E.read_sets()
    p = E.Point(V={("DCOH", "ENNE"): 1.0, ("DCOH", "COMI"): 10000.0, ("DCOH", "FGRA"): 3000.0,
                   ("DCOH", "LEVL"): 100.0, ("UAAR", "LEVL"): 2600.0},
                nobs={("DCOH", "LEVL"), ("DCOH", "COMI"), ("DCOH", "FGRA")}, bas={},
                basm={("ENNE", "FGRA"): 6.0}, const={("DCOH", "ENNE"): 10000.0}, slope={("DCOH", "ENNE"): 1.0},
                pdata={}, coco=set(), support={}, lo={}, up={}, year=2000)
    r = {(n, i): v for n, i, s_, v in E.residuals(p, S)}
    # (10000 + 1 x 10000) x 1 x 1.0 - 3000 x 6
    assert r[("REQS_", ("DCOH", "ENNE"))] == pytest.approx(20000.0 - 18000.0)
    assert E.violations([("X", (), "L", -1.0), ("Y", (), "G", 1.0), ("Z", (), "E", 0.0)], 1e-9) == []
    assert len(E.violations([("X", (), "L", 1.0), ("Y", (), "G", -1.0)], 1e-9)) == 2


def test_symbolic_variables_give_the_same_residuals():
    """residuals(var=...) builds the NLP's constraints: at the point they equal the numeric residuals."""
    ca = pytest.importorskip("casadi")
    S = E.read_sets()
    V = {("DCOH", "ENNE"): 1.02, ("DCOH", "COMI"): 9000.0, ("DCOH", "FGRA"): 3000.0, ("DCOH", "LEVL"): 100.0,
         ("DCOH", "HERD"): 99.0, ("DCOH", "DAYS"): 365.0, ("UAAR", "LEVL"): 2600.0, ("LU", "LEVL"): 0.05}
    p = E.Point(V=V, nobs={("DCOH", "LEVL"), ("DCOH", "COMI"), ("DCOH", "FGRA"), ("DCOH", "HERD")}, bas={},
                basm={("ENNE", "FGRA"): 6.0}, const={("DCOH", "ENNE"): 10000.0}, slope={("DCOH", "ENNE"): 1.0},
                pdata={}, coco=set(), support={}, lo={("DCOH", "HERD"): 0.0}, up={}, year=2010)
    syms = {}

    def var(c, w):
        return syms.setdefault((c, w), ca.SX.sym(f"{c}.{w}"))

    num = E.residuals(p, S)
    sym = E.residuals(p, S, var=var)
    assert [(n, i, s_) for n, i, s_, _ in num] == [(n, i, s_) for n, i, s_, _ in sym]
    keys = list(syms)
    f = ca.Function("g", [ca.vertcat(*[syms[k] for k in keys])], [ca.vertcat(*[r[3] for r in sym])])
    vals = [float(x) for x in f([V.get(k, 0.0) for k in keys]).full().ravel()]
    assert vals == pytest.approx([r[3] for r in num])

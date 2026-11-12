"""Tests of the bounds of CAPTRD's member-state estimation (capri_mod/pipeline/captrd/estimate_bounds.py, fix_est.gms).

CAPTRD stores the bounds of its second solve (Solve2: P_Result "lo", "up", clean_tiny.gms l. 303-317, in absolute
requirements, captrd.gms l. 1205-1218); with Solve2's supports, CAPTRD's P_Result of the year and the port's own
prepared p_data (prepare_run.py, tested in test_captrd_prepare.py) the port gives them. A bound GAMS does not store
(zero, or infinite) is zero but for NTRD, free (fix_est.gms l. 727-728).

Checked 12 November 2026 on DK, AT, FR, PL, ES in 2020, 2030, 2050: of 47,172 bounds 45,983 equal CAPTRD's. The
food intake's (INHA, fix_est.gms l. 269-279) as GAMS reads them: the second term's $ conditions only its exponent, so
where BAST exists the bounds are BAST x 0.98^n + BASM and BAST x 1.02^n + BASM (CAPRI-ERROR, kept as coded).

Open: CAPTRD's stored bounds are those after its bound-widening of infeasible solves (estimate_ms.gms l. 222-420: the
lower bounds of the positions at a binding bound times 0.1, the upper ones times 1.9, the processing yields' upper
bounds at least 1.1 times the lower, the calories by small steps; estimate_nlp.py): this is most of the 1,189 others,
in INHA's lower bounds (widened, in every country and year), foodSh, PRCY, INCE and a few rows of EXPE, CSSP, HCOM,
DOMM, MAPR, LOSF, UVAD, UVAG and the trade positions (OPEN_COLS); the rest, a few yields bounded by the previous
year's estimate (NoYieldDrop, l. 183-185: CAPTRD's estP there is its Solve2 result, here its Step3, cleaned of tiny
values) and, in 2020, one animal's bounds at 0.1 and 1.9 times the port's (widened).
"""
from __future__ import annotations

import collections
import math

import pandas as pd
import pytest

from capri_mod.csvio import read_csv
from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import prepare as P

RES = REFERENCE / "captrd_results" / "1770"
#: the reference run's time ordinals (captrd.gms l. 700-765; timesets.py): BAS 2017, Lst_exPostT 2019 (ExAnteD 2019),
#: BAST 2018, Fst_exAnte 2018, Lst_exAnte 2070, %lst_dgagri% 2040 (aglink2023dgAgri)
ORD = dict(ord_bas=2017, ord_bast=2018, lst_exante=2070, fst_exante=2018, lst_expostt=2019, lst_dgagri=2040)
RESY = [2018, 2020, 2025, 2030, 2035, 2040, 2045, 2050, 2060, 2070]
OPEN_COLS = {"INHA", "HCOM", "foodSh", "PRCY", "N_CAL", "N_PRO", "EXPE", "CSSP", "DOMM", "MAPR", "LOSF", "UVAD",
             "UVAG", "EXPT", "IMPT"}
WBA7 = {"AL000000", "MK000000", "CS000000", "MO000000", "HR000000", "BA000000", "KO000000"}

needs_reference = pytest.mark.skipif(
    not (RES / "Lo.csv.gz").exists() or not (REFERENCE / "capreg_tseries" / "17" / "DK.csv.gz").exists(),
    reason="CAPTRD reference results not present (capri_sources/reference)")


def _by_year(name, ms, years):
    d = read_csv(RES / f"{name}.csv.gz", dtype={"t": str}, keep_default_na=False)
    d = d[(d.region == ms) & d.t.isin([str(y) for y in years])]
    return {int(t): dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}


def _case(ms, year, prepared):
    """(ours lo, up), (CAPTRD's lo, up) on the positions with data or a support, the requirements relative; and the
    BoundData (D) and the point's keywords (kw) for the solve."""
    S = E.read_sets()
    B = EB.read_bound_sets()
    d = read_csv(RES / "data.csv.gz", dtype={"t": str}, keep_default_na=False)
    regs = set(d.region)
    mp = set(zip(*[read_csv(P.SETS_DIR / "map_rr.csv", dtype=str).get(c) for c in ("d0", "d1")]))
    n2 = {r for a, r in mp if a == ms and r != ms and r in regs}
    q = d[d.region.isin(n2) & (d.t == "nObs") & (d.row == "LEVL") & (d.value != 0)]
    nuts2 = q.groupby("col").region.nunique().to_dict()
    d = d[d.region == ms]
    data = {t: dict(zip(zip(g.col, g.row), g.value.astype(float))) for t, g in d.groupby("t")}
    pp = prepared[prepared.region == ms]
    prep = {(c, w, t): float(v) for c, w, t, v in zip(pp.col, pp.row, pp.t, pp.value)}
    prev = {RESY[i]: RESY[i - 1] for i in range(1, len(RESY))}.get(year)
    res = {k: _by_year(f, ms, [year]).get(year, {}) for k, f in
           [("Support", "support"), ("coco", "COCO"), ("Expert", "Expert"), ("expertlo", "expertLo"),
            ("expertup", "expertUp"), ("p_data", "P_Data"), ("BASM", "BASM")]}

    def pd_(c, w, st):
        if st == "BASM":
            return prep.get((c, w, "BASM"), data.get("BASM", {}).get((c, w), 0.0))
        if st in data:
            return data[st].get((c, w), 0.0)
        return prep.get((c, w, st), 0.0)
    nobs = {k for k, v in data.get("nObs", {}).items() if v}
    kw = dict(nobs=nobs, bas=data.get("BAS", {}), basm={}, const=data.get("Const", {}), slope=data.get("Slope", {}),
              pdata=res["p_data"], coco=set(res["coco"]), lo={}, up={}, year=year, exante_d=year <= ORD["lst_expostt"])
    kw["basm"].update(data.get("BASM", {}))              # the feed contents (ReqsT x FEED)
    for a in S.maact:
        for r_ in S.reqst:
            kw["basm"][(a, r_)] = pd_(a, r_, "BASM")
    sup_abs = res["Support"]
    res["Support"] = E.requirements_relative(E.Point(V=sup_abs, support=sup_abs, **kw), S, sup_abs)
    cs = {(a, r_): data.get("Const", {}).get((a, r_), 0.0) + data.get("Slope", {}).get((a, r_), 0.0)
          for a in S.maact for r_ in S.reqst}
    st3 = _by_year("step3", ms, [prev]).get(prev, {}) if prev else {}
    D = EB.BoundData(ms=ms, year=year, pd=pd_, res=res, exante_d=year <= ORD["lst_expostt"],
                     west=("EU014000", ms) in mp, east=("EU013000", ms) in mp, wba7=ms in WBA7,
                     bur=ms in {"BG000000", "RO000000"}, prev=prev, prev_exante_d=prev is not None and prev <= 2019,
                     estp_prev=st3, step3_prev=st3, const_slope={k: v for k, v in cs.items() if v},
                     nuts2_with_data=nuts2, **ORD)
    lo, up = EB.bounds(D, B, E.REQS_EFF ** (year - E.REQS_YEAR0))
    L0, U0 = _by_year("Lo", ms, [year]).get(year, {}), _by_year("up", ms, [year]).get(year, {})
    Lr = E.requirements_relative(E.Point(V=L0, support={}, **kw), S, L0)
    Ur = E.requirements_relative(E.Point(V=U0, support={}, **kw), S, U0)
    pos = sorted(k for k in set(sup_abs) | nobs if k[0] in S.cols_est and k[1] in S.rows_est)
    return pos, (lo, up), (Lr, Ur), (D, kw, sup_abs)


def _diff(pos, ours, ref, free):
    bad = []
    for k in pos:
        r = ref.get(k, free if k[0] == "NTRD" else 0.0)
        o = ours.get(k, free)
        if r == o or (math.isfinite(r) and math.isfinite(o) and abs(r - o) <= 1e-6 * max(1.0, abs(r))):
            continue
        bad.append((k, o, r))
    return bad


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    from capri_mod.pipeline.captrd import prepare_run as PR
    out = tmp_path_factory.mktemp("prep")
    PR.main(["--out", str(out), "--countries", "DK", "AT"])
    return pd.concat([pd.read_parquet(out / "DK.parquet"), pd.read_parquet(out / "AT.parquet")], ignore_index=True)


@pytest.mark.slow
@needs_reference
@pytest.mark.parametrize("ms,year", [("DK000000", 2030), ("AT000000", 2030), ("DK000000", 2050)])
def test_solve2_bounds_equal_captrds(prepared, ms, year):
    pos, (lo, up), (Lr, Ur), _ = _case(ms, year, prepared)
    inf = float("inf")
    for name, ours, ref, free in (("lo", lo, Lr, -inf), ("up", up, Ur, inf)):
        bad = _diff(pos, ours, ref, free)
        settled = [b for b in bad if b[0][0] not in OPEN_COLS]
        # outside the open columns: a handful of yields bounded by the previous year's estimate (NoYieldDrop,
        # l. 183-185: estP of the year before, CAPTRD's Solve2 result there, Step3 here, cleaned of tiny values)
        assert len(settled) <= 8, (name, settled[:10])
        n_bad = collections.Counter(b[0][0] for b in bad)
        assert len(bad) <= 0.045 * len(pos), (name, len(bad), n_bad)
        assert not [b for b in bad if b[0][1] == "LEVL" and b[0][0] in E.read_sets().mpact], name


def test_share_rule_of_areas():
    """fix_est.gms l. 344-381: an area may move by (share)^0.25 / 4 of the land in the last year, at least 20%."""
    B = EB.read_bound_sets()
    vals = {("UAAR", "LEVL", "BASM"): 2000.0, ("GRAS", "LEVL", "BASM"): 0.0, ("SWHE", "LEVL", "BASM"): 500.0,
            ("SWHE", "LEVL", "nObs"): 30.0}
    d = EB.BoundData(ms="XX000000", year=2030, pd=lambda c, w, s: vals.get((c, w, s), 0.0), res={}, exante_d=False,
                     west=False, east=False, **ORD)
    lo, up = EB.bounds(d, B, 1.0)
    dev = (500.0 / 2000.0) ** 0.25 / 4 * 2000.0 * max(0.2, 13 / 53)
    assert up[("SWHE", "LEVL")] == pytest.approx(max(500.0 + 0.1, 500.0 + dev))
    assert lo[("SWHE", "LEVL")] == pytest.approx(500.0 - dev)
    assert lo[("NTRD", "SWHE")] == -float("inf") and up[("NTRD", "SWHE")] == float("inf")

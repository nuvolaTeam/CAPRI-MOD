"""m_trendNT2 (capri_mod/pipeline/captrd/estimate_nuts2.py) against CAPTRD's stored NUTS 2 results (CAPTRD's reference run,
capri_sources/reference/captrd_results): the equations at CAPTRD's result, the bounds of estimate_nuts2.gms against its
stored ones, and the solve with est_nuts2_grid.gms's retries against its step3, for Ireland's two regions."""
import collections
import dataclasses
import math

import pandas as pd
import pytest

from capri_mod.csvio import read_csv
from capri_mod.pipeline.captrd import estimate_bounds as EB
from capri_mod.pipeline.captrd import estimate_ms as E
from capri_mod.pipeline.captrd import estimate_nuts2 as N2
from capri_mod.pipeline.captrd import prepare as _P
from capri_mod.pipeline.tests import test_captrd_estimate_bounds as TB
from capri_mod.pipeline.tests import test_captrd_estimate_ms as TM
from capri_mod.pipeline.tests.test_captrd_estimate_bounds import needs_reference


@pytest.fixture(scope="module")
def prepared_ir(tmp_path_factory):
    from capri_mod.pipeline.captrd import prepare_run as PR
    out = tmp_path_factory.mktemp("prep_ir")
    PR.main(["--out", str(out), "--countries", "IR"])
    return pd.read_parquet(out / "IR.parquet")


@pytest.mark.slow
@needs_reference
def test_ireland_2030_regions_meet_m_trendnt2_at_captrds_result(prepared_ir):
    S = E.read_sets()
    B = EB.read_bound_sets()
    ms, y = "IR000000", 2030
    regs = sorted(r for r in prepared_ir.region.unique() if r != ms)
    assert regs == ["IR010000", "IR020000"]
    _, _, _, (Dm, kwm, sup_m) = TB._case(ms, y, prepared_ir)
    bm = dict(TM._prepared_basm(ms))
    bm.update(kwm["basm"])
    bm.update(TB._by_year("BASM", ms, [y]).get(y, {}))
    st3_m = TB._by_year("step3", ms, [y]).get(y, {})
    ms_V = E.from_stored(E.Point(V=st3_m, support=sup_m, **{**kwm, "basm": bm, "lo": {}, "up": {}}), S, st3_m)
    points = {}
    for r in regs:
        _, _, (Lr, Ur), (D, kw, sup_abs) = TB._case(r, y, prepared_ir)
        kw = {**kw, "basm": N2.regional_basm(kw["basm"], bm, S)}
        st3 = TB._by_year("step3", r, [y]).get(y, {})
        V = E.from_stored(E.Point(V=st3, support=sup_abs, **{**kw, "lo": {}, "up": {}}), S, st3)
        # CAPTRD stores no zero (bound or level): an input or output coefficient with neither bound nor level stored is
        # fixed at zero (e.g. the regions' young-animal inputs BULH.IBUL, with data, at 1000 in Ireland's own result),
        # so MSGROF_'s condition (a coefficient not fixed, l. 182-186) sees it as CAPTRD did
        Uf = dict(Ur)
        for a, w in S.pact_to_io:
            k = (a, w)
            if k not in Lr and k not in Ur and not st3.get(k):
                Uf[k] = 0.0
        points[r] = E.Point(V=V, support=D.res["Support"], **{**kw, "lo": Lr, "up": Uf})
    rd = lambda n: set(read_csv(_P.SETS_DIR / f"{n}.csv", keep_default_na=False, dtype=str).d0)  # noqa: E731
    res = N2.residuals(points, kwm["nobs"], ms_V, S, B.foddi, rd("rset"), rd("splitactslo"))
    blocks = collections.Counter(x[0] for x in res)
    print("m_trendNT2 Ireland 2030:", dict(blocks))
    # every block of the model statement is generated but OSET_ (no set-aside rate in Ireland's 2030 data) and
    # Germany's MSindmMaif_; 12 November 2026: 448 equations, all within 1e-3
    assert set(blocks) == (set(N2.SHARED_BLOCKS) - {"OSET_"}) | {"MSGROF_", "MSLEVL_", "MSLANDUSE_", "MSFEEDI_",
                                                                 "MSlosfFoddo_", "EFED_"}
    bad = E.violations(res, 1e-3)
    assert not bad, bad[:10]


INF = float("inf")


def _sets_of(name):
    return read_csv(_P.SETS_DIR / f"{name}.csv", keep_default_na=False, dtype=str)


def _regional_case(ms, y, prepared):
    """The inputs of estimate_nuts2.bounds and solve for the regions of ms in year y, from CAPTRD's stored results; and
    CAPTRD's stored bounds (Lo, up) and step3 of each region."""
    S, B = E.read_sets(), EB.read_bound_sets()
    one = lambda n: set(_sets_of(n).d0)                                                    # noqa: E731
    B2 = N2.nuts2_bound_sets(B, ms, one("landusearto"))
    S2 = dataclasses.replace(S, cols_est=B2.cols_est, rows_est=B2.rows_est)

    _, _, _, (Dm, kwm, sup_m) = TB._case(ms, y, prepared)
    bm = dict(TM._prepared_basm(ms))
    bm.update(kwm["basm"])
    bm.update(TB._by_year("BASM", ms, [y]).get(y, {}))
    st3_m = TB._by_year("step3", ms, [y]).get(y, {})
    ms_V = E.from_stored(E.Point(V=st3_m, support=sup_m, **{**kwm, "basm": bm, "lo": {}, "up": {}}), S, st3_m)

    regs = sorted(r for r in prepared.region.unique() if r != ms)
    D, kws, ref, wv, bl = {}, {}, {}, {}, {}
    for r in regs:
        _, _, _, (Dr, kw, sup_abs) = TB._case(r, y, prepared)
        D[r] = dataclasses.replace(Dr, region_of=ms, ms_pd=Dm.pd, ms_res=Dm.res, nuts2_with_data={})
        kws[r] = {**kw, "basm": N2.regional_basm(kw["basm"], bm, S)}
        st3 = TB._by_year("step3", r, [y]).get(y, {})
        ref[r] = dict(lo=TB._by_year("Lo", r, [y]).get(y, {}), up=TB._by_year("up", r, [y]).get(y, {}),
                      step3=E.from_stored(E.Point(V=st3, support=sup_abs, **{**kws[r], "lo": {}, "up": {}}), S, st3))
        wv[r] = TB._by_year("wVarErr", r, [y]).get(y, {})
        bl[r] = {a: Dr.pd(a, "LEVL", "BASM") for a in S.mpact}

    cor = one("corfeedlosf")
    losf = {o for i, o in B.feed_to_o if i in cor} & one("cropo")
    fodf = {(i, o) for i, o in B.feed_to_o if i in B.foddi}
    c2g = set(zip(_sets_of("cropc_to_g").d0, _sets_of("cropc_to_g").d1))
    lo, up, addn = N2.bounds(D, B2, E.REQS_EFF ** (y - E.REQS_YEAR0), ms_V, Dm.pd, ms_V, losf, fodf, c2g)
    points = {r: E.Point(V={}, support=D[r].res["Support"],
                         **{**kws[r], "nobs": set(kws[r]["nobs"]) | addn[r], "lo": lo[r], "up": up[r]}) for r in regs}
    return dict(S2=S2, B2=B2, D=D, points=points, ms_nobs=kwm["nobs"], ms_V=ms_V, wvar=wv, basm_levl=bl,
                losf=losf | set(N2.LOSF_EXTRA), ref=ref, split_acts_lo=one("splitactslo"))


def _bounds_off(c, r, lo, up):
    """The positions with data (the requirements apart: CAPTRD stores them absolute) whose bounds differ from CAPTRD's
    stored ones. A bound CAPTRD does not store is zero or infinite (the GDX keeps neither)."""
    S2, nobs, ref = c["S2"], c["points"][r].nobs, c["ref"][r]
    bad = []
    for k in sorted(nobs):
        if k[1] in S2.reqst or k[0] not in S2.cols_est or k[1] not in S2.rows_est:
            continue
        for ours, stored in ((lo.get(k, -INF), ref["lo"]), (up.get(k, INF), ref["up"])):
            if k in stored:
                ok = math.isfinite(ours) and abs(ours - stored[k]) <= 1e-6 * max(1.0, abs(stored[k]))
            else:
                ok = ours == 0 or math.isinf(ours)
            if not ok:
                bad.append((k, ours, stored.get(k)))
    return bad


def _share_near(c, r, x, tol):
    """The share of the region's positions with data in CAPTRD's step3 that the port's result meets within tol
    (relative, at least 1 absolute)."""
    st3, nobs, S2 = c["ref"][r]["step3"], c["points"][r].nobs, c["S2"]
    held = [k for k in sorted(st3) if k in nobs and k[0] in S2.cols_est and k[1] in S2.rows_est]
    return sum(abs(x.get(k, 0.0) - st3[k]) <= tol * max(abs(st3[k]), 1.0) for k in held) / len(held)


def _solve(c):
    return N2.solve(c["points"], c["D"], c["B2"], c["ms_nobs"], c["ms_V"], c["S2"], c["split_acts_lo"], c["wvar"],
                    c["basm_levl"], c["losf"])


@pytest.mark.slow
@needs_reference
def test_ireland_2030_regional_bounds_and_solve_meet_captrds(prepared_ir):
    """Solved by CAPTRD at its first try: estimate_nuts2.gms's bounds are CAPTRD's stored ones on every position with
    data, and the solve meets CAPTRD's step3 (12 November 2026: all positions within 2%, 99.7% and 100% within 0.5%)."""
    c = _regional_case("IR000000", 2030, prepared_ir)
    for r, p in sorted(c["points"].items()):
        assert not _bounds_off(c, r, p.lo, p.up), (r, _bounds_off(c, r, p.lo, p.up)[:10])
    res = _solve(c)
    assert res.feasible and res.tries == 1, res.status
    for r in sorted(c["points"]):
        x = {(c_, w): v for (rr, c_, w), v in res.x.items() if rr == r}
        assert _share_near(c, r, x, 0.02) >= 0.999, r
        assert _share_near(c, r, x, 0.005) >= 0.99, r

        # rem_tiny.gms on the stored positions (those with data) keeps the result
        one = lambda n: set(_sets_of(n).d0)                                                # noqa: E731
        nobs = c["points"][r].nobs
        st = N2.rem_tiny({k: v for k, v in x.items() if k in nobs}, nobs, c["S2"], c["B2"].foddi, one("aact"),
                         one("grpr"), one("rows_lab"), one("o"), c["ms_V"])
        assert _share_near(c, r, st, 0.02) >= 0.999, r


@pytest.mark.slow
@needs_reference
def test_ireland_2050_regional_retries_reach_captrds_result(prepared_ir):
    """Infeasible at the first try (CAPTRD's stored bounds are those after its retries: the young animals fixed at 1000
    as est_Nuts2_grid_openbound.gms l. 255-258 sets them): one retry; the final bounds differ from CAPTRD's on at most 5
    positions per region (which bounds open depends on the infeasible point), the result within 2% of CAPTRD's step3 on
    at least 98% of the positions. 13 November 2026, the SLP phase 1 (captrd.nlp_infeasible_marginals = "slp"): 4 and
    2 bounds off, 99.4% and 98.6% within 2% (the IPOPT phase 1: 3 and 2, 98.9%)."""
    c = _regional_case("IR000000", 2050, prepared_ir)
    res = _solve(c)
    assert res.feasible and res.tries > 1, res.status
    for r in sorted(c["points"]):
        lo = {k[1:]: v for k, v in res.lo.items() if k[0] == r}
        up = {k[1:]: v for k, v in res.up.items() if k[0] == r}
        assert len(_bounds_off(c, r, lo, up)) <= 5, (r, _bounds_off(c, r, lo, up))
        x = {(c_, w): v for (rr, c_, w), v in res.x.items() if rr == r}
        assert _share_near(c, r, x, 0.02) >= 0.98, r

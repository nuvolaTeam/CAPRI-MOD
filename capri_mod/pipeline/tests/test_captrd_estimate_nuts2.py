"""m_trendNT2's equations (capri_mod/pipeline/captrd/estimate_nuts2.py) at CAPTRD's stored NUTS 2 results: Ireland's two
regions in 2030 under Ireland's result (CAPTRD's reference run, capri_sources/reference/captrd_results)."""
import collections

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

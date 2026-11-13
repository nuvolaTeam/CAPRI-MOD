"""Parity of CAPTRD's Aglink-COSIMO stage (capri_mod/pipeline/captrd/aglink.py; baseline/load_aglink2023dgAgri.gms)
with CAPTRD's own p_result(..., "DGAgri") (capri_sources/reference/captrd_results/1770/DGAgri), on CAPTRD's p_data at
this point: CAPREG's years and base-year values of every country (prepare_run step 1; captrd.gms l. 486-580).

CAPTRD's stored DGAgri is the position at the end of the run; the later stages that write to it are left out of the
comparison, each with the line that writes it:
  - the region EU and the column DEMD (= DOMM): aggreg_and_report.gms l. 50, 89-98 and 293
  - the yields moved to the products, (activity, its output): scale_DG_AGRI_baseline.gms l. 59-64
  - the BAST, BAST2 and growth-rate entries (t not a year): scale_DG_AGRI_baseline.gms l. 69-72 and later
  - the EU aggregates' UVAG where Aglink has none, taken from EU_WEST (EU014000): scale_DG_AGRI_baseline.gms l. 86-88
    (checked: all 122 such records equal EU014000's)
  - HCOM.LEVL of the European regions (19 years each, the CAPREG years): human consumption from the per-head data and
    the population, scale_DG_AGRI_baseline.gms l. 170-174 (reproduced in test_captrd_scale_dgagri.py)

Results on 10 November 2026: 123,133 compared records; every record present in both equal (relative 1e-6, in fact to
round-off); 217 records only in CAPTRD's (the UVAG and HCOM.LEVL above, before they were excluded); 1 only here (EU014000
NTRD SUGB 2016, -1.5e-11: a balance closing at round-off that GAMS stores as 0).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE, SOURCES
from capri_mod.pipeline.captrd import aglink as A

R = REFERENCE / "captrd_results" / "1770"
TS, BASE = REFERENCE / "capreg_tseries" / "17", REFERENCE / "capreg_base" / "17"
SP = SOURCES / "dat_parquet" / "baseline"
need = pytest.mark.skipif(not ((R / "DGAgri.csv.gz").exists() and (SP / "aglink2023dgAgri_oriEUdata").exists()
                               and TS.exists() and BASE.exists()), reason="CAPRI reference files not built")
K = ["region", "col", "row", "t"]


@pytest.fixture(scope="module")
def dgagri():
    from capri_mod.csvio import read_csv
    from capri_mod.pipeline.captrd import prepare as P
    from capri_mod.pipeline.captrd import prepare_run as PR
    s = P.read_sets()
    parts = []
    for m in s.ms:
        f1, f2 = TS / f"{PR._cc(m)}.csv.gz", BASE / f"{PR._cc_base(m)}.csv.gz"
        p = P.load_basm(P.load_fixes(P.read_series(f1, s, range(1984, 2020)), s),
                        read_csv(f2, keep_default_na=False), s)
        parts.append(p[p.region == m][["region", "col", "row", "t", "value"]])
    pdata = pd.concat(parts, ignore_index=True)
    src = A.ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "biofuel" / "biofuel_technology_params_"
    dens = pd.read_parquet(f"{src}p_density.parquet").set_index("fuel").value.astype(float).to_dict()
    oil = pd.read_parquet(f"{src}p_oilEqu.parquet").set_index("fuel").value.astype(float).to_dict()
    dg, p, _ = A.run(SP / "aglink2023dgAgri_oriEUdata", SP / "AGLINK2019dgagri_oridata",
                     REFERENCE / "sets" / "simini_21730", pdata, dens, oil)
    _STAGE["p_aglink"] = p                       # p_aglink with p_BFyld (fixture aglink_p)
    return dg


#: the stage's other results of the module's run, for the fixtures below
_STAGE: dict = {}


@pytest.fixture(scope="module")
def aglink_p(dgagri):
    """The Aglink stage's p_aglink (with p_BFyld as .bfyld), from dgagri's run."""
    return _STAGE["p_aglink"]


@pytest.mark.slow
@need
def test_aglink_stage_equals_captrds_dgagri(dgagri):
    dg = dgagri.copy()
    ref = pd.read_csv(R / "DGAgri.csv.gz", dtype={"t": str})
    for d in (dg, ref):
        for k in K:
            d[k] = d[k].astype(str).str.upper()                  # GAMS labels are case-insensitive (bioEWhea)
    pty = pd.read_csv(A.GSETS / "pact_to_y.csv", dtype=str)
    pty = set(zip(pty.iloc[:, 0].str.upper(), pty.iloc[:, 1].str.upper()))
    later = ((ref.region == "EU") | (ref.col == "DEMD") | ~ref.t.str.fullmatch(r"\d{4}")
             | pd.Series([(c, r) in pty for c, r in zip(ref.col, ref.row)], index=ref.index)
             | ((ref.col == "HCOM") & (ref.row == "LEVL")))
    ref = ref[~later]
    m = dg.merge(ref[K + ["value"]], on=K, how="outer", suffixes=("", "_ref"), indicator=True)
    both = m[m._merge == "both"]
    assert len(m) > 120_000
    assert ((both.value - both.value_ref).abs() <= 1e-6 * both.value_ref.abs().clip(lower=1e-6)).all()
    only_ref = m[m._merge == "right_only"]
    west = ref[(ref.region == "EU014000") & (ref.col == "UVAG")].set_index(["row", "t"]).value
    from_west = (only_ref.col == "UVAG") & only_ref.region.isin(["EU013000", "EU27YR19"]) & pd.Series(
        [abs(west.get((r, t), float("nan")) - v) <= 1e-9 * abs(v) for r, t, v in
         zip(only_ref.row, only_ref.t, only_ref.value_ref)], index=only_ref.index, dtype=bool)
    assert from_west.all(), only_ref[~from_west].head()
    only_here = m[m._merge == "left_only"]
    assert (only_here.value.abs() < 1e-9).all(), only_here.head()

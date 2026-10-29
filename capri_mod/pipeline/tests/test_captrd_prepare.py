"""CAPTRD's data preparation (capri_mod/pipeline/captrd/prepare.py) against CAPTRD's own estimation data.

The reference is CAPTRD's p_data as its results file stores it (capri_reference/captrd_results/1770/P_Data.csv.gz),
for the ex-post years of the series CAPTRD estimated (data position nObs > 0), from CAPREG's time series of the same
run (capri_reference/capreg_tseries/17). Denmark is one file without NUTS 2 regions; the parity of the regional rules
waits for the full run.

Records the stages not yet ported change, excluded by rule (docs/design/CAPTRD_MOD.md section 12.2):
  - reporting: aggreg_and_report.gms writes the product aggregates (OAGG rows of the market balance, UVAG, INHA, UVAD;
    l. 203-220) and the activity aggregates' TOOU into the same p_data position, after the estimation;
  - policy (captrd_policy.gms): the quotas;
  - not traced: VSET.LEVL of 1991-2005, which CAPTRD's p_data has at values with one decimal (8.2 for 1994 against
    CAPREG's 8.3599...; no CAPTRD statement found that sets it, and COCO has no VSET for these years), and therefore
    UAAR.LEVL, which sums the crop activities, and LU.LEVL, livestock units per UAAR, in those years;
  - the COCO nowcasts and biofuel data (load_coco1_data.gms, from coco2_output.gdx): the biofuel columns and rows,
    the fuels, and isoglucose (HFCS) in the last CAPREG year, which COCO revises;
For the base year (BASM, compared with CAPTRD's BASM position, which carries p_data's BASM to every ex-ante year,
define_stats_and_supports.gms l. 55-57), further:
  - the animal requirements (REQST rows of the animals), which prep_requirement_estimation.gms converts;
  - the labour rows LABF and LABP of the activities (captrd.gms l. 1265-1290 and the labour agelines);
  - DOMM of the products with biofuel use (DOMM sums BIOF, which the COCO stage changes).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.pipeline.captrd import prepare as P

ROOT = Path(__file__).resolve().parents[3]
TS = ROOT / "capri_reference" / "capreg_tseries" / "17"
BASE = ROOT / "capri_reference" / "capreg_base" / "17"
RES = ROOT / "capri_reference" / "captrd_results" / "1770"
BASE_YEAR = 2017                                              # the reference run's base year (settings.csv)

BIOFUEL_COLS = {"BIOF", "PRCB", "PRCBY", "NAGR", "SECG"}       # load_coco1_data.gms l. 321-372, 490-520
FUELS = {"GASL", "DISL"}                                      # the fossil fuels of load_coco1_data.gms l. 352


def _pending(df: pd.DataFrame, s: P.CaptrdSets, oagg: set) -> pd.Series:
    col, row = df["col"], df["row"]
    reporting = (row.isin(oagg) & col.isin(s.mrkbalee | {"UVAG", "INHA", "UVAD"})) | ((row == "TOOU") & ~col.isin(s.mpact))
    policy = col.isin(s.quotas)
    untraced = _vset_dependent(df)
    coco = (col.isin(BIOFUEL_COLS) | row.isin(s.seco_biof | FUELS | {"DDGS"})
            | ((df["t"] == str(BASE_YEAR + 1)) & (row == "HFCS")))
    return reporting | policy | untraced | coco


def _vset_dependent(df: pd.DataFrame) -> pd.Series:
    """VSET.LEVL, and UAAR.LEVL (the crops' sum) and LU.LEVL (livestock units per UAAR) in the years where VSET.LEVL
    differs from CAPTRD's (not traced; see the module docstring)."""
    if "_merge" not in df.columns:
        return df["col"] == "VSET"
    v = df[(df["col"] == "VSET") & (df["row"] == "LEVL")]
    bad = v[(v["_merge"] != "both") | ((v["value"] - v["value_ref"]).abs() > 1e-9 * v["value_ref"].abs())]
    years = set(bad["t"])
    lev = (df["row"] == "LEVL") & df["col"].isin({"UAAR", "LU"}) & df["t"].isin(years)
    return (df["col"] == "VSET") | lev


def _reference(s: P.CaptrdSets, region: str, ex) -> pd.DataFrame:
    ref = pd.concat(c[c.region == region] for c in
                    pd.read_csv(RES / "P_Data.csv.gz", dtype={"t": str}, chunksize=1_000_000))
    ref = ref[ref.t.str.isdigit() & (ref.eps == 0) & ref.col.isin(s.s_colsest) & ref.row.isin(s.s_rowsest)
              & (ref.col + ref.row != "INHALEVL")]          # population: external forecast, nObs = 0 (l. 184-185)
    return ref[ref.t.astype(int).isin(ex)]


def _compare(prepared: pd.DataFrame, s: P.CaptrdSets, region: str, ex, exclude=None) -> pd.DataFrame:
    oagg = set(pd.read_csv(ROOT / "capri_reference" / "sets" / "simini_21730" / "OAGG.csv", keep_default_na=False).d0)
    nobs = pd.read_csv(RES / "data.csv.gz")
    nobs = nobs[(nobs.t == "nObs") & (nobs.value > 0) & (nobs.region == region)][["region", "col", "row"]]
    mine = prepared.merge(nobs, on=["region", "col", "row"])
    m = mine.merge(_reference(s, region, ex)[P.KEYS + ["value"]], on=P.KEYS, how="outer", suffixes=("", "_ref"),
                   indicator=True)
    m = m[~_pending(m, s, oagg)]
    if exclude is not None:
        m = m[~exclude(m)]
    return m


def _prepare_one(s: P.CaptrdSets, raw: pd.DataFrame, ex, uvad_added=None) -> pd.DataFrame:
    a = P.stage_a(raw, s)
    if uvad_added is not None:
        a = pd.concat([a, uvad_added[uvad_added.region.isin(set(a.region))]], ignore_index=True)
    a = P.labour_household(P.clean_regions(a, s, ex))
    return P.prep_for_estimation(a, s, ex, [y for y in ex if abs(y - BASE_YEAR) <= 3],
                                 [y for y in ex if abs(y - BASE_YEAR) <= 1], range(1984, 2019))


def _assert_equal(m: pd.DataFrame, n_min: int) -> None:
    both = m[m._merge == "both"]
    rel = (both.value - both.value_ref).abs() / both.value_ref.abs()
    assert len(both) > n_min
    assert (m._merge != "both").sum() == 0, m[m._merge != "both"].head(20).to_string()
    assert (rel < 1e-9).all(), both[rel >= 1e-9].head(20).to_string()


@pytest.mark.skipif(not ((TS / "DK.csv.gz").exists() and (RES / "P_Data.csv.gz").exists()),
                    reason="CAPRI reference files not built")
def test_denmark_prepared_data_equals_captrds():
    """Denmark alone: the UVAD that Denmark lacks comes from the other countries of its market aggregate
    (fill_uvad), so those records and what is computed from them (CSSP, EXPE) are left to the next test."""
    s = P.read_sets()
    raw = P.read_series(TS / "DK.csv.gz", s, range(1984, 2019))
    ex = P.expost_years(raw, s.ms)
    a = P.stage_a(raw, s)
    own = a[a.col == "UVAD"]
    own = set(zip(own.row, own.t))
    lacking_t = {t for t in map(str, ex) if any((r, t) not in own for r in s.o)}

    def _from_peers(m):
        k = pd.Series([(r, t) not in own for r, t in zip(m.row, m.t)], index=m.index)
        return ((m.col.isin({"UVAD", "CSSP", "EXPE"}) & k)
                | ((m.col == "EXPE") & (m.row == "LEVL") & m.t.isin(lacking_t)))
    _assert_equal(_compare(_prepare_one(s, raw, ex), s, "DK000000", ex, _from_peers), 40_000)


@pytest.mark.skipif(not ((TS / "DK.csv.gz").exists() and (BASE / "DK.csv.gz").exists()
                         and (RES / "BASM.csv.gz").exists()), reason="CAPRI reference files not built")
def test_denmark_base_year_equals_captrds():
    s = P.read_sets()
    oagg = set(pd.read_csv(ROOT / "capri_reference" / "sets" / "simini_21730" / "OAGG.csv", keep_default_na=False).d0)
    raw = P.read_series(TS / "DK.csv.gz", s, range(1984, 2019))
    ex = P.expost_years(raw, s.ms)
    d2 = pd.read_csv(BASE / "DK.csv.gz", keep_default_na=False)
    a = P.stage_a(raw, s, d2)
    a = P.labour_household(P.clean_regions(a, s, ex))
    a = P.prep_for_estimation(a, s, ex, [y for y in ex if abs(y - BASE_YEAR) <= 3],
                              [y for y in ex if abs(y - BASE_YEAR) <= 1], range(1984, 2019))
    mine = a[(a.t == "BASM") & (a.region == "DK000000")]
    nobs = pd.read_csv(RES / "data.csv.gz")
    nobs = nobs[(nobs.t == "nObs") & (nobs.value > 0) & (nobs.region == "DK000000")][["region", "col", "row"]]
    ref = pd.concat(c[(c.region == "DK000000") & (c.t == "2030")] for c in
                    pd.read_csv(RES / "BASM.csv.gz", dtype={"t": str}, chunksize=1_000_000))
    ref = ref[(ref.eps == 0) & ref.col.isin(s.s_colsest) & ref.row.isin(s.s_rowsest)
              & (ref.col + ref.row != "INHALEVL")]
    keys = ["region", "col", "row"]
    m = mine.merge(nobs, on=keys)[keys + ["value"]].merge(ref[keys + ["value"]], on=keys, how="outer",
                                                          suffixes=("", "_ref"), indicator=True)
    m["t"] = "BASM"
    biof = set(ref[ref.col == "BIOF"].row)
    later = ((m.col.isin(s.aact) & m.row.isin(set(pd.read_csv(P.SETS_DIR / "reqst.csv").d0)))
             | (m.col.isin(s.mpact) & m.row.isin({"LABF", "LABP"}))
             | ((m.col == "DOMM") & m.row.isin(biof)))
    _assert_equal(m[~(_pending(m, s, oagg) | later)], 1_200)


@pytest.mark.slow
@pytest.mark.skipif(not ((TS / "DK.csv.gz").exists() and (RES / "P_Data.csv.gz").exists()),
                    reason="CAPRI reference files not built")
def test_denmark_with_the_uvad_of_its_market_aggregate():
    """Denmark with the UVAD averaged over the countries of its market aggregates (A_EU_WEST: read their files)."""
    s = P.read_sets()
    peers = sorted(r for a in s.rmaggsup for (a2, r) in s.map_rr if a2 == a and "DK000000" in s.members(a)
                   and r in set(s.ms))
    uv, ua, raw_dk = [], [], None
    for r in peers:
        raw = P.read_series(TS / f"{r[:2]}.csv.gz", s, range(1984, 2019))
        ua.append(raw[(raw.col == "UAAR") & (raw.row == "LEVL")])
        a = P.stage_a(raw, s)
        uv.append(a[a.col == "UVAD"])
        if r == "DK000000":
            raw_dk = raw
    ex = P.expost_years(raw_dk, s.ms)
    added = P.fill_uvad(pd.concat(uv, ignore_index=True), s, ex)
    _assert_equal(_compare(_prepare_one(s, raw_dk, ex, added), s, "DK000000", ex), 40_000)


def test_uvad_average_is_parallel_and_portugal_fills_the_east():
    s = P.read_sets()
    # three western countries of one market aggregate: two with UVAD, one without; one eastern country without
    west = sorted(s.members("A_EU_WEST") & set(s.ms))[:3]
    east = "BG000000"
    uv = pd.DataFrame([(west[0], "SWHE", "2010", 100.0), (west[1], "SWHE", "2010", 200.0),
                       ("PT000000", "SWHE", "2010", 300.0)], columns=["region", "row", "t", "value"])
    add = P.fill_uvad(uv, s, [2010]).set_index("region")["value"]
    peers = sorted(s.members("A_EU_WEST") & set(s.ms))
    have = {west[0]: 100.0, west[1]: 200.0, "PT000000": 300.0}
    # the average over the aggregate's countries with a value (each counted once: A_EU_WEST only)
    assert add[west[2]] == pytest.approx(sum(have[r] for r in peers if r in have) / sum(r in have for r in peers))
    # BG has no western peer: A_EU_EAST and EU013000 have no UVAD, so Portugal's (EU_EAST and BUR) is taken
    assert add[east] == pytest.approx(300.0)


COCO = ROOT / "capri_reference" / "coco2" / "17" / "coco2_output.csv.gz"
BIOFUEL = ROOT / "capri_reference" / "fao_agg" / "17" / "p_biofuelData.csv.gz"


@pytest.mark.slow
@pytest.mark.skipif(not all(f.exists() for f in (TS / "DK.csv.gz", BASE / "DK.csv.gz", COCO, BIOFUEL,
                                                 RES / "P_Data.csv.gz")), reason="CAPRI reference files not built")
def test_denmark_with_the_coco_data(tmp_path):
    """Denmark through every ported stage (prepare_run.run), the COCO data and the policy data included: the years
    1984-2019 (2019 from COCO) equal CAPTRD's p_data, leaving out the reporting overwrites and what needs the other
    countries (the near-zero biofuel flags some other country's COCO data sets, l. 337 and 346; the UVAD averages).
    The quotas and set-aside rates, which CAPTRD stores whatever their observations (define_stats_and_supports.gms
    l. 149-150), are compared in every year, the ex-ante years included."""
    from capri_mod.pipeline.captrd import prepare_run as R
    s = P.read_sets()
    out = R.run(["DK000000"], s, BASE_YEAR, 1984, 2019, TS, BASE, COCO, BIOFUEL, tmp_path)
    a = pd.read_parquet(out["DK000000"])
    a = a[a.t != "BASM"]
    ex = sorted({int(t) for t in a.t})
    oagg = set(pd.read_csv(ROOT / "capri_reference" / "sets" / "simini_21730" / "OAGG.csv", keep_default_na=False).d0)
    nobs = pd.read_csv(RES / "data.csv.gz")
    nobs = nobs[(nobs.t == "nObs") & (nobs.value > 0) & (nobs.region == "DK000000")][["region", "col", "row"]]
    m = a.merge(nobs, on=["region", "col", "row"]).merge(_reference(s, "DK000000", ex)[P.KEYS + ["value"]], on=P.KEYS,
                                                          how="outer", suffixes=("", "_ref"), indicator=True)
    col, row, t = m["col"], m["row"], m["t"]
    reporting = (row.isin(oagg) & col.isin(s.mrkbalee | {"UVAG", "INHA", "UVAD"})) | ((row == "TOOU") & ~col.isin(s.mpact))
    policy = _vset_dependent(m)
    near_zero = m["value_ref"].fillna(0).abs().le(1e-13) & m["value"].fillna(0).abs().le(1e-13)
    peers = col.isin({"UVAD", "CSSP"}) & (m._merge == "right_only")
    hfcs = (row == "HFCS") & (t == "2018")
    # not traced yet: CAPTRD's p_data has the fossil fuels' UVAG in 2019, which COCO does not carry (load_coco1_data.gms
    # l. 352 copies COCO's UVAP, absent for 2019); presumably a later stage
    fuel_2019 = (col == "UVAG") & row.isin(s.fosfuels) & (t == "2019") & (m._merge == "right_only")
    m = m[~(reporting | policy | near_zero | peers | hfcs | fuel_2019)]
    _assert_equal(m, 42_000)
    # the quotas and set-aside rates in every year (captrd_policy.gms)
    a = pd.read_parquet(out["DK000000"])
    a = a[(a.t != "BASM") & (a.region == "DK000000") & (a.col.isin(s.quotas) | (a.row == "SETR"))]
    ref = pd.concat(c[c.region == "DK000000"] for c in
                    pd.read_csv(RES / "P_Data.csv.gz", dtype={"t": str}, chunksize=1_000_000))
    ref = ref[ref.t.str.isdigit() & (ref.eps == 0) & (ref.col.isin(s.quotas) | (ref.row == "SETR"))]
    q = a.merge(ref[P.KEYS + ["value"]], on=P.KEYS, how="outer", suffixes=("", "_ref"), indicator=True)
    _assert_equal(q, 150)

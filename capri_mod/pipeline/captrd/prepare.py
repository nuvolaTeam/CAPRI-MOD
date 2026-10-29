"""CAPTRD's data preparation: CAPREG's time series to the estimation data p_data (CAPRI star 3.0).

Ported in CAPTRD's order from captrd.gms l. 486-898 (load, cleaning) so that Step 1 (step1.py) can run from CAPREG's
own time series instead of CAPTRD's prepared data. The parity reference is CAPTRD's p_data as its results file stores it
(p_result(..., "p_data"), written by define_stats_and_supports.gms l. 138-150 after prep_data_for_estimation.gms;
capri_reference/captrd_results/<run>/P_Data.csv.gz).

p_data is held long (region, col, row, t, value), t a calendar year as text or BASM. GAMS semantics kept:
  - a zero is no record (an assignment of 0 deletes), and a $-condition on a value is true where the value is nonzero;
  - EPS records are not loaded (EPS is zero in arithmetic and, as treated here, in conditions; the reference files mark
    them in their eps column and the parity check leaves them out);
  - an indexed assignment is parallel: the right-hand side is evaluated on the values before the statement (GAMS user's
    guide, "Data Manipulations with Parameters": "a copy of the symbols on the right hand side is installed before the
    assignment is carried out"), which matters for the area rescaling and the UVAD average below.

Stages (each a function, with the GAMS lines it ports):
  load               captrd.gms l. 418-478, 504   the CAPREG series of the regions in estimation, COLS_LOAD x ROWS_LOAD
  load_fixes         captrd.gms l. 509-517        GROF of the secondary products to 0; land uses rescaled to ARTO
  load_basm          captrd.gms l. 528-580        CAPREG's base-year data (DATA2) as BASM
  check_and_cor      check_and_cor_capreg.gms     EPS sugar quotas (not loaded); no biofuel in Norway; ARTIF of BASM
  delete_unestimated captrd.gms l. 833-839        series not estimated deleted
  delete_early_years captrd.gms l. 841-850        EU_EAST and Germany before 1992, BUR and WBA before 1995
  fill_uvad          captrd.gms l. 852-860        UVAD averaged over the market aggregates; Portugal's for EU_EAST/BUR
  clean_regions      captrd.gms l. 862-888        regions never estimated; the NUTS 2 rows reduced
  labour_household   captrd.gms l. 897-898        LABH = LABO - LABN
  prep_for_estimation prep_data_for_estimation.gms l. 15-162
The COCO nowcasts (load_coco1_data.gms, l. 715), the policy data (captrd_policy.gms) and the labour agelines follow as
they are ported (docs/design/CAPTRD_MOD.md section 12.2).
The COCO stage is in coco.py; prepare_run.py runs every stage over the country files in CAPTRD's order (fill_uvad and the
COCO flags need every country).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SETS_DIR = ROOT / "capri_data" / "pipeline" / "captrd" / "sets"
DAT_DIR = ROOT / "capri_data" / "pipeline" / "captrd" / "dat"


def read_dat(path: Path = DAT_DIR) -> Dict[str, Dict]:
    """CAPRI's data include files CAPTRD reads (tools/build/build_captrd_dat.py): luunits {act: LU per head},
    extr_rates {(fuel, stock): t/t}, byproduct {(byproduct, stock): t/t}."""
    lu = pd.read_csv(path / "p_luunits.csv", keep_default_na=False)
    er = pd.read_csv(path / "p_extrrates.csv", keep_default_na=False)
    bp = pd.read_csv(path / "p_byproduct.csv", keep_default_na=False)
    return {"luunits": dict(zip(lu.act, lu.value)),
            "extr_rates": {(f, s_): v for f, s_, v in zip(er.fuel, er.stock, er.value)},
            "byproduct": {(b, s_): v for b, s_, v in zip(bp.byproduct, bp.stock, bp.value)}}
KEYS = ["region", "col", "row", "t"]


@dataclass
class CaptrdSets:
    """The sets the preparation reads (capri_data/pipeline/captrd/sets, tools/build/build_captrd_sets.py)."""
    ms: List[str]                        # MS = sets.rmssup, in CAPRI's order (sets_captrd.gms l. 54-56)
    map_rr: Set[Tuple[str, str]]
    urbannuts: Set[str]
    srnuts2: Set[str]                    # NT2 is its alias (l. 69)
    s_colsest: Set[str]
    s_rowsest: Set[str]
    cols_load: Set[str]
    rows_load: Set[str]
    reqsc: Set[str]
    secom: Set[str]
    landusearto: Set[str]
    quotas: Set[str]
    bio_cols: Set[str]
    biorepcols: Set[str]
    seco_biof: Set[str]
    mpact: Set[str]
    maact: Set[str]
    pact_to_io: Set[Tuple[str, str]]
    pact_to_i: Set[Tuple[str, str]]
    iyani: Set[str]
    fix_yai: Set[str]
    rmaggsup: Set[str]
    rms_to_rm: Set[Tuple[str, str]]
    # read by prep_for_estimation
    ncnc: Set[str] = field(default_factory=set)
    fout: Set[str] = field(default_factory=set)
    oyani_rows: Set[str] = field(default_factory=set)
    mcact: Set[str] = field(default_factory=set)
    cact: Set[str] = field(default_factory=set)
    seco: Set[str] = field(default_factory=set)
    o: Set[str] = field(default_factory=set)
    feed: Set[str] = field(default_factory=set)
    aact: Set[str] = field(default_factory=set)
    oyani: Set[str] = field(default_factory=set)
    # read by coco.py (load_coco1_data.gms)
    corfeedlosf: Set[str] = field(default_factory=set)
    cropo: Set[str] = field(default_factory=set)
    domm_set: Set[str] = field(default_factory=set)
    splitacts: Set[str] = field(default_factory=set)
    dact: Set[str] = field(default_factory=set)
    dmpact: Set[str] = field(default_factory=set)
    msnoeu28: Set[str] = field(default_factory=set)
    fuel_rows: Set[str] = field(default_factory=set)
    biofuels: Set[str] = field(default_factory=set)
    fosfuels: Set[str] = field(default_factory=set)
    fuels: Set[str] = field(default_factory=set)
    biostock: Set[str] = field(default_factory=set)
    prcd: Set[Tuple[str, str]] = field(default_factory=set)
    feed_to_o: Set[Tuple[str, str]] = field(default_factory=set)
    dact_to_pact: Set[Tuple[str, str]] = field(default_factory=set)
    p_t_actagg: Set[Tuple[str, str]] = field(default_factory=set)
    stock_to_fuel: Set[Tuple[str, str]] = field(default_factory=set)
    stock_to_by: Set[Tuple[str, str]] = field(default_factory=set)
    mrkbale: Set[str] = field(default_factory=set)
    mrkbalee: Set[str] = field(default_factory=set)
    dompos: Set[str] = field(default_factory=set)
    breedact: Set[str] = field(default_factory=set)
    meat: Set[str] = field(default_factory=set)
    grpr: Set[str] = field(default_factory=set)
    grpc: Set[str] = field(default_factory=set)
    pact_to_o: Set[Tuple[str, str]] = field(default_factory=set)
    pact_to_y: Set[Tuple[str, str]] = field(default_factory=set)
    cropc_to_g: Set[Tuple[str, str]] = field(default_factory=set)
    rows_to_g: Set[Tuple[str, str]] = field(default_factory=set)

    @property
    def nt2ext(self) -> Set[str]:
        """NT2ext = NT2 + urbanNUTS (sets_captrd.gms l. 76-78)."""
        return self.srnuts2 | self.urbannuts

    @property
    def rest(self) -> Set[str]:
        """Rest = MS + NT2ext at the load (sets_captrd.gms l. 159-161)."""
        return set(self.ms) | self.nt2ext

    def members(self, agg: str) -> Set[str]:
        return {r for a, r in self.map_rr if a == agg}


def read_sets(path: Path = SETS_DIR) -> CaptrdSets:
    def one(n):
        return list(pd.read_csv(path / f"{n}.csv", keep_default_na=False).d0)

    def two(n):
        d = pd.read_csv(path / f"{n}.csv", keep_default_na=False)
        return set(zip(d.d0, d.d1))

    names1 = ["urbannuts", "srnuts2", "s_colsest", "s_rowsest", "cols_load", "rows_load", "reqsc", "secom",
              "landusearto", "quotas", "bio_cols", "biorepcols", "seco_biof", "mpact", "maact", "iyani", "fix_yai",
              "rmaggsup", "ncnc", "fout", "oyani_rows", "mcact", "cact", "seco", "o", "feed", "mrkbale", "mrkbalee",
              "dompos", "breedact", "meat", "grpr", "grpc", "aact", "oyani", "corfeedlosf", "cropo", "domm_set",
              "splitacts", "dact", "dmpact", "msnoeu28", "fuel_rows", "biofuels", "fosfuels", "fuels", "biostock"]
    names2 = ["map_rr", "pact_to_io", "pact_to_i", "rms_to_rm", "pact_to_o", "pact_to_y", "cropc_to_g", "rows_to_g",
              "prcd", "feed_to_o", "dact_to_pact", "p_t_actagg", "stock_to_fuel", "stock_to_by"]
    return CaptrdSets(ms=one("ms"), **{n: two(n) for n in names2}, **{n: set(one(n)) for n in names1})


def _year(t: pd.Series) -> pd.Series:
    return pd.to_numeric(t, errors="coerce")


def _assign(df: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """The records of new replace those with the same key; a zero value deletes."""
    new = new[KEYS + ["value"]]
    k_new = pd.MultiIndex.from_frame(new[KEYS])
    keep = ~pd.MultiIndex.from_frame(df[KEYS]).isin(k_new)
    return pd.concat([df[keep], new[new["value"] != 0]], ignore_index=True)


# --- stages ------------------------------------------------------------------------------------------------------
def load(series: pd.DataFrame, sets: CaptrdSets, years: Iterable[int]) -> pd.DataFrame:
    """captrd.gms l. 504: p_data(NUTS0_and_2ext, COLS_LOAD, ROWS_LOAD, Years) $ Rest = DATA1. series: CAPREG's time
    series (region, col, row, t, value[, eps]); only the calendar years of Years are loaded (BASM and the other keys of
    the file are read by the base-year stage)."""
    yrs = {str(int(y)) for y in years}
    s = series[series["region"].isin(sets.rest) & series["col"].isin(sets.cols_load)
               & series["row"].isin(sets.rows_load) & series["t"].astype(str).isin(yrs)]
    if "eps" in s.columns:
        s = s[s["eps"] == 0]
    s = s[KEYS + ["value"]].copy()
    s["t"] = s["t"].astype(str)
    return s[s["value"] != 0].reset_index(drop=True)


def load_fixes(p: pd.DataFrame, sets: CaptrdSets) -> pd.DataFrame:
    """captrd.gms l. 511: GROF of the secondary products (SECOM) to 0 (CAPTRD books agricultural output on GROF, other
    output on MAPR). l. 514-516: where the nonnegative land uses of ARTO sum to a nonzero and ARTO is nonzero, each land
    use is max(0, value) * ARTO / that sum (parallel: the sum is the one before the statement)."""
    p = p[~((p["col"] == "GROF") & p["row"].isin(sets.secom))]
    lu_m = p["col"].isin(sets.landusearto) & (p["row"] == "LEVL")
    lu = p[lu_m]
    if lu.empty:
        return p.reset_index(drop=True)
    pos = lu.assign(v=lu["value"].clip(lower=0.0)).groupby(["region", "t"])["v"].sum()
    arto = p[(p["col"] == "ARTO") & (p["row"] == "LEVL")].set_index(["region", "t"])["value"]
    f = pd.concat([pos.rename("pos"), arto.rename("arto")], axis=1).dropna()
    f = f[(f["pos"] != 0) & (f["arto"] != 0)]
    lu = lu.join((f["arto"] / f["pos"]).rename("f"), on=["region", "t"])
    lu = lu[lu["f"].notna()]
    lu = lu.assign(value=lu["value"].clip(lower=0.0) * lu["f"])
    return _assign(p, lu)


def load_basm(p: pd.DataFrame, data2: pd.DataFrame, sets: CaptrdSets) -> pd.DataFrame:
    """captrd.gms l. 549-580: CAPREG's base-year data DATA2(., ., ., "Y") as BASM.

    - every S_ColsEst (with HOLD) or REQSC column and S_RowsEst (with LABT) row of the regions in estimation, l. 552-559;
    - the check that every region in estimation has UAAR (but the urban regions) and ARTO, l. 565-568 (here: the regions
      of the file);
    - GROF of the secondary products to 0; N_EXPT and SETR of the S_ColsEst; STCM of the young animals; EDAYS, and
      DRMN and DRMX times DAYS, of the animals (AACT), l. 572-579.
    data2: region, col, row, t (= Y), value[, eps]."""
    d = data2[data2["region"].isin(sets.rest)]
    if "eps" in d.columns:
        d = d[d["eps"] == 0]
    d = d[d["value"] != 0]
    v = d.set_index(["region", "col", "row"])["value"]
    cols = sets.s_colsest | {"HOLD"} | sets.reqsc
    rows = sets.s_rowsest | {"LABT"}
    basm = d[d["col"].isin(cols) & d["row"].isin(rows)][["region", "col", "row", "value"]]
    regions = sorted(set(d["region"]))
    have = set(zip(basm["region"], basm["col"], basm["row"]))
    empty = [r for r in regions if ((r, "UAAR", "LEVL") not in have and r not in sets.urbannuts)
             or (r, "ARTO", "LEVL") not in have]
    if empty:
        raise ValueError(f"missing base year data for agricultural or total area: {empty} (captrd.gms l. 565-568)")
    basm = basm[~((basm["col"] == "GROF") & basm["row"].isin(sets.seco))]
    extra = d[(d["col"].isin(sets.s_colsest) & d["row"].isin({"N_EXPT", "SETR"}))
              | ((d["col"] == "STCM") & d["row"].isin(sets.oyani))
              | (d["col"].isin(sets.aact) & (d["row"] == "EDAYS"))][["region", "col", "row", "value"]]
    days = d[d["col"].isin(sets.aact) & (d["row"] == "DAYS")].set_index(["region", "col"])["value"]
    dr = d[d["col"].isin(sets.aact) & d["row"].isin({"DRMN", "DRMX"})].copy()
    dr["value"] = dr["value"] * [days.get((r, c), 0.0) for r, c in zip(dr["region"], dr["col"])]
    out = pd.concat([basm, extra, dr[["region", "col", "row", "value"]]], ignore_index=True)
    out = out.drop_duplicates(["region", "col", "row"], keep="last")
    out["t"] = "BASM"
    del v
    p = p[p["t"] != "BASM"]
    return pd.concat([p, out[KEYS + ["value"]][out["value"] != 0]], ignore_index=True)


def check_and_cor(p: pd.DataFrame, sets: CaptrdSets, msincl: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """check_and_cor_capreg.gms, on the years and BASM: l. 27-28, the EPS sugar quotas set to 0 (EPS is not loaded:
    nothing left to do); l. 32-33, Norway produces no biofuel (BIO_COLS and bioRepCols on SECO_BIOF to 0); l. 35-39,
    ARTIF.LEVL of BASM of each country in the run (MSINCL, default every MS) is the sum over its NUTS 2 and urban
    regions (MAP_RR; a country without NUTS 2 regions maps to itself)."""
    m = (p["region"] == "NO000000") & p["col"].isin(sets.bio_cols | sets.biorepcols) & p["row"].isin(sets.seco_biof)
    p = p[~m]
    incl = set(sets.ms if msincl is None else msincl)
    sub = {(a, r) for a, r in sets.map_rr if a in incl and r in sets.nt2ext}
    art = p[(p["col"] == "ARTIF") & (p["row"] == "LEVL") & (p["t"] == "BASM")].set_index("region")["value"]
    here = set(p["region"])
    new = []
    for c in sorted(incl & here):
        new.append((c, "ARTIF", "LEVL", "BASM", float(sum(art.get(r, 0.0) for a, r in sub if a == c))))
    if not new:
        return p.reset_index(drop=True)
    return _assign(p, pd.DataFrame(new, columns=KEYS + ["value"]))


def delete_unestimated(p: pd.DataFrame, sets: CaptrdSets) -> pd.DataFrame:
    """captrd.gms l. 833-839: the years of every series outside S_ColsEst + REQSC, S_RowsEst or Rest deleted."""
    m = p["col"].isin(sets.s_colsest | sets.reqsc) & p["row"].isin(sets.s_rowsest) & p["region"].isin(sets.rest)
    return p[m | _year(p["t"]).isna()].reset_index(drop=True)


def delete_early_years(p: pd.DataFrame, sets: CaptrdSets) -> pd.DataFrame:
    """captrd.gms l. 841-850: the countries of EU_EAST before 1992, of BUR and WBA (RMS_TO_RM) before 1995, Germany before
    1992 (countries only: their NUTS 2 regions keep their years)."""
    ms = set(sets.ms)
    y = _year(p["t"])
    east = sets.members("EU_EAST") & ms
    later = (sets.members("BUR") | {r for r, rm in sets.rms_to_rm if rm == "WBA"}) & ms
    drop = ((p["region"].isin(east) & (y < 1992)) | (p["region"].isin(later) & (y < 1995))
            | ((p["region"] == "DE000000") & (y < 1992)))
    return p[~drop].reset_index(drop=True)


def fill_uvad(uvad: pd.DataFrame, sets: CaptrdSets, expostt: Iterable[int]) -> pd.DataFrame:
    """captrd.gms l. 852-860, on the UVAD records of every country (region, row, t, value), after the deletions above.

    Where a country has no UVAD for a row and ex-post year, it takes the average of the nonzero UVAD of the countries in
    its market aggregates (rmAggSup; a country in two aggregates counts once per aggregate, as the sum over
    MAP_RR(rmAggSup, RMS) does), from the values before the statement. Then the countries of EU_EAST still without UVAD
    take Portugal's, then those of BUR. Returns the UVAD records added (region, col, row, t, value)."""
    ms = list(sets.ms)
    msset = set(ms)
    exp = {str(int(t)) for t in expostt}
    u = uvad[uvad["region"].isin(msset) & uvad["t"].astype(str).isin(exp) & (uvad["value"] != 0)]
    cur: Dict[Tuple[str, str, str], float] = {(r, rw, str(t)): v for r, rw, t, v in
                                              zip(u["region"], u["row"], u["t"], u["value"])}
    pairs = {(a, r) for a, r in sets.map_rr if a in sets.rmaggsup}
    peers: Dict[str, List[str]] = {}
    for m in ms:
        aggs = [a for a, r in pairs if r == m]
        peers[m] = [r for a in aggs for (a2, r) in pairs if a2 == a and r in msset]
    keys = {(rw, t) for (_r, rw, t) in cur}
    added = {}
    for m in ms:
        if not peers[m]:
            continue
        for rw, t in keys:
            if (m, rw, t) in cur:
                continue
            vals = [cur.get((r, rw, t), 0.0) for r in peers[m]]
            s, n = sum(vals), sum(1 for v in vals if v != 0)
            if s != 0 and n:
                added[(m, rw, t)] = s / n
    cur.update(added)                     # parallel: the averages above saw only the values before the statement
    for agg in ("EU_EAST", "BUR"):
        new = {}
        for m in ms:
            if m not in sets.members(agg):
                continue
            for rw, t in keys:
                v = cur.get(("PT000000", rw, t), 0.0)
                if (m, rw, t) not in cur and v != 0:
                    new[(m, rw, t)] = v
        cur.update(new)
        added.update(new)
    if not added:
        return pd.DataFrame(columns=KEYS + ["value"])
    return pd.DataFrame([(r, "UVAD", rw, t, v) for (r, rw, t), v in added.items()], columns=KEYS + ["value"])


def clean_regions(p: pd.DataFrame, sets: CaptrdSets, expost: Iterable[int]) -> pd.DataFrame:
    """captrd.gms l. 862-888.

    - RDel: the NT2ext regions no country maps (MAP_RR(MS, .)); their ex-post years (ExPost) deleted (BASM: base-year
      stage).
    - l. 872-876 (the columns of NT2ext other than the activities, land use, GROF and ARTO): as coded, the condition
      NOT SUM(SAMEAS(MS,NT2),1) has NT2 uncontrolled, so the sum runs over both MS and NT2 and counts the countries that
      are their own NUTS 2 region; that count is nonzero in CAPRI's sets, so the statement deletes nothing. Kept as
      coded (CAPTRD's p_data keeps, e.g., UVAG of the NUTS 2 regions).
    - the activities of the NUTS 2 regions that are not countries keep only their inputs and outputs (PACT_TO_IO) and
      LEVL; the young-animal inputs (IYANI) of the animal activities and of GROF are deleted where no animal activity
      without fixed young-animal coefficients (FIX_YAI) takes that input.
    """
    ms = set(sets.ms)
    exp = {str(int(t)) for t in expost}
    rdel = {r for r in sets.nt2ext if not any((m, r) in sets.map_rr for m in ms)}
    p = p[~(p["region"].isin(rdel) & (p["t"].isin(exp) | (p["t"] == "BASM")))]
    yrs = _year(p["t"]).notna()
    if sum(1 for m in ms if m in sets.srnuts2) == 0:              # the GAMS condition, should the sets change
        keep = (p["col"].isin(sets.mpact | sets.landusearto | {"GROF", "ARTO"}) | ~p["region"].isin(sets.nt2ext)
                | p["region"].isin(ms) | ~yrs)
        p = p[keep]
    yrs = _year(p["t"]).notna()
    nt2 = p["region"].isin(sets.srnuts2) & ~p["region"].isin(ms) & yrs
    act = p["col"].isin(sets.mpact)
    io = pd.Series([(c, r) in sets.pact_to_io for c, r in zip(p["col"], p["row"])], index=p.index, dtype=bool)
    p = p[~(nt2 & act & ~io & (p["row"] != "LEVL"))]
    takers = {i for a, i in sets.pact_to_i if i in sets.iyani and a in sets.maact and a not in sets.fix_yai}
    nt2 = p["region"].isin(sets.srnuts2) & ~p["region"].isin(ms) & _year(p["t"]).notna()
    yani = p["row"].isin(sets.iyani - takers) & (p["col"].isin(sets.maact) | (p["col"] == "GROF"))
    return p[~(nt2 & yani)].reset_index(drop=True)


def labour_household(p: pd.DataFrame) -> pd.DataFrame:
    """captrd.gms l. 897-898: p_data(Rest, "GROF", "LABH", YEARS and BASM) = LABO - LABN (a zero deletes)."""
    lab = p[(p["col"] == "GROF") & p["row"].isin(["LABO", "LABN"])]
    old = (p["col"] == "GROF") & (p["row"] == "LABH")
    if lab.empty:
        return p[~old].reset_index(drop=True)
    w = lab.pivot_table(index=["region", "t"], columns="row", values="value", aggfunc="sum").fillna(0.0)
    h = (w.get("LABO", 0.0) - w.get("LABN", 0.0)).rename("value").reset_index()
    h["col"], h["row"] = "GROF", "LABH"
    return pd.concat([p[~old], h[h["value"] != 0][KEYS + ["value"]]], ignore_index=True)


# --- driver ------------------------------------------------------------------------------------------------------
def read_series(path: Path, sets: CaptrdSets, years: Iterable[int], chunk: int = 2_000_000) -> pd.DataFrame:
    """One CAPREG time-series file (the layout of capri_reference/capreg_tseries/<tag>/<CC>.csv.gz), loaded as `load`
    does, read in chunks."""
    years = list(years)
    parts = [load(c, sets, years)
             for c in pd.read_csv(path, chunksize=chunk, dtype={"t": str}, keep_default_na=False)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=KEYS + ["value"])


def stage_a(series: pd.DataFrame, sets: CaptrdSets, data2: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """The stages up to the deletions, on one country's files as loaded (time series; base year, if given), without
    the COCO stage, which comes between load_basm and check_and_cor (prepare_run.py runs it)."""
    p = load_fixes(series, sets)
    if data2 is not None:
        p = load_basm(p, data2, sets)
    p = check_and_cor(p, sets)
    p = delete_unestimated(p, sets)
    return delete_early_years(p, sets)


def expost_years(uaar: pd.DataFrame, ms: Iterable[str]) -> List[int]:
    """captrd.gms l. 673 and 722: ExPost (ExPostT) = the years with UAAR LEVL for some country. Without the COCO
    nowcasts (not yet ported) the two coincide."""
    u = uaar[uaar["region"].isin(set(ms)) & (uaar["col"] == "UAAR") & (uaar["row"] == "LEVL") & (uaar["value"] != 0)]
    return sorted({int(t) for t in u["t"] if str(t).isdigit()})


# --- prep_data_for_estimation.gms -----------------------------------------------------------------------------------
class Wide:
    """p_data as one Series per (col, row) on the common index (region, t); an absent series is zero."""

    def __init__(self, p: pd.DataFrame):
        self.idx = pd.MultiIndex.from_frame(p[["region", "t"]].drop_duplicates().sort_values(["region", "t"]))
        self.s: Dict[Tuple[str, str], pd.Series] = {}
        for (c, r), g in p.groupby(["col", "row"], sort=False):
            self.s[(c, r)] = g.set_index(["region", "t"])["value"].reindex(self.idx, fill_value=0.0)
        self.zero = pd.Series(0.0, index=self.idx)
        reg = self.idx.get_level_values("region")
        t = self.idx.get_level_values("t")
        self.region, self.t = pd.Series(reg, index=self.idx), pd.Series(t, index=self.idx)

    def __call__(self, c: str, r: str) -> pd.Series:
        return self.s.get((c, r), self.zero)

    def keys(self, cols=None, rows=None) -> List[Tuple[str, str]]:
        return [k for k in self.s if (cols is None or k[0] in cols) and (rows is None or k[1] in rows)]

    def put(self, c: str, r: str, v: pd.Series, where: Optional[pd.Series] = None) -> None:
        """p_data(c, r) $ where = v: where None assigns on the whole index (a zero deletes)."""
        if where is not None:
            v = v.where(where, self(c, r))
        if (v != 0).any():
            self.s[(c, r)] = v.astype(float)
        else:
            self.s.pop((c, r), None)

    def drop(self, c: str, r: str, where: pd.Series) -> None:
        if (c, r) in self.s:
            self.put(c, r, self.zero, where)

    def long(self) -> pd.DataFrame:
        parts = []
        for (c, r), v in self.s.items():
            v = v[v != 0]
            if len(v):
                d = v.rename("value").reset_index()
                d["col"], d["row"] = c, r
                parts.append(d)
        if not parts:
            return pd.DataFrame(columns=KEYS + ["value"])
        return pd.concat(parts, ignore_index=True)[KEYS + ["value"]]


def prep_for_estimation(p: pd.DataFrame, sets: CaptrdSets, expostt: Iterable[int], basyrs5: Iterable[int],
                        basyrsm: Iterable[int], years: Iterable[int], luunits: Optional[Dict[str, float]] = None
                        ) -> pd.DataFrame:
    """captrd/prep_data_for_estimation.gms l. 22-162, the statements on the years and BASM (the statistics nObs, nW,
    wAve, wVar of l. 164-198 and the base-year values of l. 205-252 are Step 1's, step1.py). Rest is MS + NT2ext; BASM
    records are treated where present (the base-year stage adds them). Every statement is an indexed assignment
    (parallel), but for the sugar price loop of l. 34-39, which is a GAMS loop over the years (sequential).

    luunits: CAPRI's livestock units p_LUUnits (dat/policy/livestock_units.gms; read_dat() when not given)."""
    if luunits is None:
        luunits = read_dat()["luunits"]
    w = Wide(p)
    ms = set(sets.ms)
    is_ms = w.region.isin(ms)
    exp = {str(int(y)) for y in expostt}
    yrs = {str(int(y)) for y in years}
    b5 = {str(int(y)) for y in basyrs5}
    bm = {str(int(y)) for y in basyrsm}
    t_exp = w.t.isin(exp)
    t_yrs = w.t.isin(yrs)
    t_yb = t_yrs | (w.t == "BASM")
    one = pd.Series(1.0, index=w.idx)

    # l. 26-28: the sugar administrative price (PADM) where a sugar quota exists
    q = w("QUTS", "SUGA") != 0
    padm = w("PADM", "SUGA")
    padm = padm.where(~(is_ms & t_exp & q), 631.0)
    padm = padm.where(~(is_ms & (w.t == "2008") & q), 541.5)
    padm = padm.where(~(is_ms & t_exp & q & (pd.to_numeric(w.t, errors="coerce") >= 2009)), 404.4)
    w.put("PADM", "SUGA", padm)
    # l. 34-39: a loop over the ex-post years (sequential): the sugar price carried forward with the change of PADM
    for y in sorted(int(v) for v in exp):
        uv, pa = w("UVAG", "SUGA"), w("PADM", "SUGA")
        prev = {(r, str(y - 1)): (uv.get((r, str(y - 1)), 0.0), pa.get((r, str(y - 1)), 0.0)) for r in ms}
        new = uv.copy()
        for r in ms:
            if (r, str(y)) not in new.index:
                continue
            u1, p1 = prev[(r, str(y - 1))] if (r, str(y - 1)) in uv.index else (0.0, 0.0)
            if new[(r, str(y))] == 0 and u1 != 0 and p1 != 0:
                new[(r, str(y))] = pa[(r, str(y))] + (u1 - p1)
        w.put("UVAG", "SUGA", new)
    # l. 41-43: BASM sugar price, MAPR-weighted over BASYRSM
    if (w.t == "BASM").any():
        _basm_weighted(w, "UVAG", "SUGA", ("MAPR", "SUGA"), bm, is_ms)

    # l. 46-55: series CAPTRD does not use
    for o in sets.o:
        w.drop("MAPR", o, t_yrs & (w("GROF", o) != 0))
    for k in w.keys(rows={"CATT"}):
        w.drop(*k, where=t_yrs)
    for k in w.keys(cols={"UAAR"}):
        w.drop(*k, where=t_yrs)
    for k in w.keys(rows=sets.fout):
        w.drop(*k, where=t_yrs)
    for k in w.keys(cols=sets.ncnc):
        if k[1] != "INCE":
            w.drop(*k, where=t_yb)
    w.drop("LOSF", "ICOW", t_yrs)
    # l. 59-63: feed rows only on GROF; market balances of products without production or imports around the base year
    for k in w.keys(cols=sets.mrkbalee - {"GROF"}, rows=sets.feed):
        w.drop(*k, where=t_yrs)
    in5 = w.t.isin(b5)

    def _b5sum(c1, c2, r):
        v = (w(c1, r) + w(c2, r)).where(in5, 0.0)
        return v.groupby(level="region").transform("sum")
    none_o = {o: _b5sum("GROF", "IMPT", o) == 0 for o in sets.o}
    for k in w.keys(cols=sets.mrkbale, rows=sets.o):
        w.drop(*k, where=t_yrs & none_o[k[1]])
    none_s = {s_: _b5sum("MAPR", "IMPT", s_) == 0 for s_ in sets.seco}
    for k in w.keys(cols=sets.mrkbale, rows=sets.seco):
        w.drop(*k, where=t_yrs & none_s[k[1]])
    for s_ in sets.seco:
        w.drop("PRCY", s_, t_yrs & (w("MAPR", s_) == 0))

    # l. 81: UAAR from the crop activities; l. 83-86: the crop groups' areas
    w.put("UAAR", "LEVL", sum((w(c, "LEVL") for c in sets.mcact), w.zero), where=t_exp)
    for g in sets.grpc:
        mem = [c for c, g2 in sets.cropc_to_g if g2 == g and c in sets.cact]
        tot = sum((w(c, "LEVL") for c in mem), w.zero)
        w.put(g, "LEVL", tot, where=t_exp | (w.t == "BASM"))
    # l. 88-96: slaughter weight of the female breeding animals
    for b in sorted(sets.breedact):
        yani = sum((w(b, i) for a, i in sets.pact_to_i if a == b and i in sets.iyani), w.zero)
        meat = sum((w(b, m) for a, m in sets.pact_to_o if a == b and m in sets.meat), w.zero)
        cond = t_exp & (yani != 0) & (w(b, "LEVL") != 0)
        w.put(b, "SLGW", (meat / yani.where(yani != 0, 1.0)) * 1000.0, where=cond)
        if (w.t == "BASM").any():
            _basm_mean(w, b, "SLGW", bm)
    # l. 99-136: the outliers of SHGM.SLGW in the base years
    sl = w("SHGM", "SLGW")
    n = (sl != 0) & t_exp
    mean = (sl.where(n, 0.0).groupby(level="region").transform("sum")
            / n.groupby(level="region").transform("sum").where(lambda v: v != 0, 1.0))
    mean = mean.where(n.groupby(level="region").transform("any"), 0.0)
    inbm = w.t.isin(bm)
    sl = sl.where(~(inbm & (mean > 0) & (sl < 0.15 * mean)), mean)
    flag = inbm & ((sl > 6.0 * mean) | (sl < 0.167 * mean))
    if (w.t == "BASM").any():
        _shgm_basm(w, sl, flag, inbm)
    for k in w.keys(rows={"ILAM", "YLAM"}):
        w.drop(*k, where=flag)
    w.put("SHGM", "SLGW", sl.where(~flag, 0.0))

    # l. 140-145: unit values and production values
    for r in sets.s_rowsest:
        g, e = w("GROF", r), w("EAAG", r)
        w.put("UVAG", r, e / g.where(g != 0, 1.0) * 1000.0, where=t_yb & (g != 0) & (e != 0))
    for r in sets.s_rowsest:
        w.put("EAAG", r, w("UVAG", r) * w("GROF", r) * 0.001, where=t_yb)
    # l. 147-148: market balances of the product groups (countries)
    for c in sets.mrkbalee:
        for g in sets.grpr:
            mem = [r for r, g2 in sets.rows_to_g if g2 == g]
            w.put(c, g, sum((w(c, r) for r in mem), w.zero), where=is_ms & t_yb)
    # l. 150-156: DOMM as the sum of the domestic uses of at least 1e-12
    rows_all = {k[1] for k in w.s}
    for r in sorted(rows_all):
        dsum = sum((w(c, r).where(w(c, r) >= 1e-12, 0.0) for c in sets.dompos), w.zero)
        dm = w("DOMM", r)
        cond = is_ms & t_yb & (((dsum != 0) & (dm != 0)) | ((dm < 0) & (r not in sets.oyani_rows)))
        if cond.any():
            w.put("DOMM", r, dsum, where=cond)
    # l. 157-160: unit values of the groups
    for g in sets.grpr:
        gr = w("GROF", g)
        w.put("UVAG", g, w("EAAG", g) / gr.where(gr != 0, 1.0) * 1000.0, where=t_yb & (gr != 0))
        hc = w("HCOM", g)
        w.put("UVAD", g, w("EXPE", g) / hc.where(hc != 0, 1.0) * 1000.0, where=is_ms & t_yb & (hc != 0))
    # l. 161-162: the activities' output value
    for a in sets.mpact:
        tot = sum((w(a, r) * w("UVAG", r) for a2, r in sets.pact_to_o if a2 == a and r in sets.s_rowsest), w.zero)
        w.put(a, "TOOU", tot * 0.001, where=is_ms & t_yb)
    # l. 163-165: net trade
    for r in sets.s_rowsest:
        w.put("NTRD", r, w("EXPT", r) - w("IMPT", r), where=is_ms & t_yb)
    # l. 169-172: per capita consumption of cereals and meat, food shares
    for g in ("CERE", "MEAS"):
        mem = [r for r, g2 in sets.rows_to_g if g2 == g]
        w.put("INHA", g, sum((w("INHA", r) for r in mem), w.zero), where=is_ms & t_yb)
    w.put("foodSh", "CERE", w("foodSh", "SWHE"), where=is_ms & t_yb)
    w.put("foodSh", "MEAS", w("foodSh", "BEEF"), where=is_ms & t_yb)
    # l. 173-178: consumer subsidy equivalent and expenditure per head
    rows_all = {k[1] for k in w.s}
    for r in sorted(rows_all):
        ud, ug = w("UVAD", r), w("UVAG", r)
        w.put("CSSP", r, ud - ug, where=is_ms & t_yb & (ud != 0) & (ug != 0))
    inha = w("INHA", "LEVL")
    for r in sorted(rows_all):
        hc = w("HCOM", r)
        cond = is_ms & t_yb & (hc != 0) & (inha != 0)
        if cond.any():
            w.put("EXPE", r, w("UVAD", r) * hc / inha.where(inha != 0, 1.0), where=cond)
    tot = sum((w("EXPE", r) for r in {k[1] for k in w.keys(cols={"EXPE"})} if r != "LEVL" and r not in sets.grpr),
              w.zero)
    w.put("EXPE", "LEVL", tot, where=is_ms & t_yb)
    # l. 160-162: stocking density, livestock units per hectare of UAAR
    ua = w("UAAR", "LEVL")
    lus = sum((w(a, "LEVL") * float(luunits.get(a, 0.0)) for a in sorted(sets.maact)), w.zero)
    w.put("LU", "LEVL", lus / ua.where(ua != 0, 1.0), where=t_yb & (ua != 0))
    return w.long()


def _basm_weighted(w: Wide, c: str, r: str, weight: Tuple[str, str], bm: Set[str], mask: pd.Series) -> None:
    """p_data(c, r, BASM) $ SUM(BASYRSM, weight) = SUM(BASYRSM, value * weight) / SUM(BASYRSM, weight)."""
    inb = w.t.isin(bm)
    wt = w(*weight).where(inb, 0.0)
    num = (w(c, r) * wt).groupby(level="region").sum()
    den = wt.groupby(level="region").sum()
    val = (num / den.where(den != 0, 1.0)).where(den != 0, 0.0)
    v = pd.Series(w.region.map(val).fillna(0.0).values, index=w.idx)
    w.put(c, r, v, where=mask & (w.t == "BASM") & (pd.Series(w.region.map(den).fillna(0.0).values, index=w.idx) != 0))


def _basm_mean(w: Wide, c: str, r: str, bm: Set[str]) -> None:
    """p_data(c, r, BASM) $ (a nonzero value in BASYRSM) = the mean of the nonzero BASYRSM values."""
    v = w(c, r)
    nz = w.t.isin(bm) & (v != 0)
    s = v.where(nz, 0.0).groupby(level="region").sum()
    n = nz.groupby(level="region").sum()
    m = pd.Series(w.region.map((s / n.where(n != 0, 1.0)).where(n != 0, 0.0)).values, index=w.idx)
    has = pd.Series(w.region.map(n).values, index=w.idx) != 0
    w.put(c, r, m, where=has & (w.t == "BASM"))


def _shgm_basm(w: Wide, sl: pd.Series, flag: pd.Series, inbm: pd.Series) -> None:
    """prep_data_for_estimation.gms l. 120-131: BASM of SHGM.SLGW and of the ILAM and YLAM rows recomputed over the base
    years not flagged as outliers, where some base year is flagged."""
    any_flag = flag.groupby(level="region").transform("any")
    ok = inbm & ~flag
    n = ok.groupby(level="region").transform("sum")
    basm = w.t == "BASM"
    region_flagged = pd.Series(w.region.map(any_flag.groupby(level="region").first()).values, index=w.idx)
    n_r = pd.Series(w.region.map(n.groupby(level="region").first()).values, index=w.idx)

    def _avg(v):
        s = v.where(ok, 0.0).groupby(level="region").sum()
        return pd.Series(w.region.map(s).values, index=w.idx) / n_r.where(n_r != 0, 1.0)
    cond = basm & region_flagged & (w("SHGM", "SLGW") != 0)
    targets = [("SHGM", "SLGW")] + w.keys(rows={"ILAM", "YLAM"})
    vals = {k: _avg(sl if k == ("SHGM", "SLGW") else w(*k)) for k in targets}
    for k in targets:
        w.put(*k, vals[k], where=cond)

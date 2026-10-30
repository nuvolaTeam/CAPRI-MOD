"""CAPTRD's statistics of the prepared series and the base-year positions (captrd/prep_data_for_estimation.gms l. 205-320,
CAPRI star 3.0), on one country's prepared p_data (prepare_run's output: the country and its NUTS 2 regions).

For every estimated series (S_ColsEst x S_RowsEst) of every region (Rest; CAPTRD's farm types EstTypes are not ported,
so their statements are left out):
  nObs, nW       the ex-post years ExPostT with an observation, and the sum of their trend values p_trend (l. 209-210);
                 0 where the series has no base-period value BASM, unless it is a COCO biofuel column or row
                 (bioColsCoco, bioRowsCoco, load_coco1_data.gms l. 316-317; l. 214-218), and for INHA.LEVL and DOMM of
                 the young animals (l. 221-227)
  WAve, wVar     the weighted mean (l. 233-234) and variance (l. 241-246; step1.prestats)
  BAS            the mean of the nonzero values of the base years BASYRS5 (l. 254-258); for an activity's
                 inputs and outputs (PACT_TO_IO) the mean weighted by the activity's levels (l. 263-264), wherever the
                 activity has a level BAS
  feed           an animal's feed input coefficients (MAACT x FEED, l. 274-297): BASM at most 1e-4 deleted, and where the
                 country has none; where the country has one and the animal is estimated (LEVL nObs), nObs = 1, BAS =
                 the region's BASM, else (none of its own) 0.001 x the country's (also as BASM); GROF's feed with nObs 1
                 and BAS = BASM where some animal has it (l. 302-305)
  BSY            max(the mean of the three highest distinct yields of the last eight ex-post years EIGHTLST, BAS) of the
                 crops' and animals' yields (PACT_TO_Y), where the activity has a level BAS (l. 309-325)

Returns p_data with the positions nObs, nW, WAve, wVar, BAS, BSY added (as t values) and the feed BASM changed.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from capri_mod.pipeline.captrd.coco import BIO_COLS_COCO, BIO_ROWS_COCO
from capri_mod.pipeline.captrd.prepare import CaptrdSets
from capri_mod.pipeline.captrd.step1 import prestats, trend_variable

KEYS = ["region", "col", "row"]


def _gmax(values: np.ndarray) -> float:
    """GAMS SMAX: -INF over an empty set."""
    return float(values.max()) if values.size else -np.inf


def bsy(yields: np.ndarray, bas: float) -> float:
    """l. 309-325 for one series: yields over EIGHTLST (zeros included, as GAMS's SMAX runs over the set)."""
    first = _gmax(yields)
    if not first:                                                   # l. 321: BSY $ "1"
        return 0.0
    second = _gmax(yields[yields != first])
    third = _gmax(yields[(yields != first) & (yields != second)])
    return max((first + second + third) / 3.0, bas)


def statistics(p: pd.DataFrame, sets: CaptrdSets, expostt: Iterable[int], basyrs5: Iterable[int],
               eightlst: Iterable[int], first_year: Optional[int] = None) -> pd.DataFrame:
    ex = [str(int(y)) for y in expostt]
    b5 = [str(int(y)) for y in basyrs5]
    e8 = [str(int(y)) for y in eightlst]
    w = trend_variable([int(y) for y in ex], first_year)
    p = p.copy()
    wide = p.pivot_table(index=KEYS, columns="t", values="value", aggfunc="first")
    for c in set(ex) | set(b5) | set(e8) | {"BASM"}:
        if c not in wide.columns:
            wide[c] = np.nan
    wide = wide.fillna(0.0)
    est = wide[wide.index.get_level_values("col").isin(sets.s_colsest)
               & wide.index.get_level_values("row").isin(sets.s_rowsest)]
    X = est[ex].to_numpy(float)
    obs = X != 0.0
    nobs = obs.sum(axis=1).astype(float)
    nw = (obs * w).sum(axis=1)
    cols = est.index.get_level_values("col")
    rows = est.index.get_level_values("row")
    keep = (est["BASM"].to_numpy() != 0.0) | cols.isin(BIO_COLS_COCO) | rows.isin(BIO_ROWS_COCO)   # l. 214-218
    zero = ~keep | ((cols == "INHA") & (rows == "LEVL")) | ((cols == "DOMM") & rows.isin(sets.oyani))  # l. 221-227
    nobs = np.where(zero, 0.0, nobs)
    nw = np.where(zero, 0.0, nw)
    pre = prestats(X, w, nobs, nw)
    st = pd.DataFrame({"nObs": pre.nobs, "nW": pre.nw, "WAve": pre.wave, "wVar": pre.wvar}, index=est.index)
    # l. 254-258: BAS $ nObs = the mean of the nonzero BASYRS5 values
    B5 = est[b5].to_numpy(float)
    nb = (B5 != 0.0).sum(axis=1)
    st["BAS"] = np.where((st["nObs"].to_numpy() != 0) & (nb > 0), B5.sum(axis=1) / np.maximum(nb, 1), 0.0)
    # l. 263-264: an activity's inputs and outputs weighted by its levels, where its LEVL has a BAS
    levl_bas = st["BAS"].xs("LEVL", level="row", drop_level=False) if "LEVL" in set(rows) else None
    io = {(a, r) for a, r in sets.pact_to_io}
    lev = wide.xs("LEVL", level="row")[b5] if "LEVL" in set(wide.index.get_level_values("row")) else None
    new_bas = {}
    for k in st.index:
        reg, a, r = k
        if a not in sets.mpact or a not in sets.s_colsest or (a, r) not in io:
            continue
        lb = levl_bas.get((reg, a, "LEVL"), 0.0) if levl_bas is not None else 0.0
        if not lb:
            continue
        lv = lev.loc[(reg, a)].to_numpy(float)
        den = lv.sum()
        new_bas[k] = float((est.loc[k, b5].to_numpy(float) * lv).sum() / den) if den else np.nan
    for k, v in new_bas.items():
        st.at[k, "BAS"] = v                                         # (a zero level sum: GAMS division by zero)
    # l. 274-297: the feed input coefficients of the animals
    basm = wide["BASM"].copy()
    ms_of = {r: m for m, r in sets.map_rr if m in set(sets.ms)}
    feed_keys = [k for k in wide.index if k[1] in sets.maact and k[2] in sets.feed]
    for k in feed_keys:                                             # l. 274: BASM <= 1e-4 deleted
        if basm[k] <= 1e-4:
            basm[k] = 0.0
    ms_basm = {(ms_of.get(reg), a, f): basm[(reg, a, f)] for reg, a, f in feed_keys if ms_of.get(reg) == reg}

    def ms_val(reg, a, f):
        return ms_basm.get((ms_of.get(reg), a, f), 0.0)
    for k in feed_keys:                                             # l. 275: none in the country
        if not ms_val(*k):
            basm[k] = 0.0
    for k in feed_keys:
        reg, a, f = k
        mv = ms_val(reg, a, f)
        if not mv:
            continue
        lv_nobs = st["nObs"].get((reg, a, "LEVL"), 0.0)
        if k not in st.index:
            st.loc[k] = 0.0
        if lv_nobs:
            st.at[k, "nObs"] = 1.0                                  # l. 278
        st.at[k, "BAS"] = basm[k]                                   # l. 279
        if st.at[k, "nObs"] and not st.at[k, "BAS"]:
            st.at[k, "BAS"] = mv * 0.001                            # l. 280-281
        if st.at[k, "nObs"] and not basm[k]:
            basm[k] = mv * 0.001                                    # l. 282-283
    # l. 302-305: GROF's feed
    feed_nobs = st[st.index.get_level_values("col").isin(sets.maact)
                   & st.index.get_level_values("row").isin(sets.feed)]["nObs"]
    with_animal = {(reg, f) for (reg, a, f), v in feed_nobs.items() if v}
    for reg, f in sorted(with_animal):
        k = (reg, "GROF", f)
        if k not in st.index:
            st.loc[k] = 0.0
        if not st.at[k, "nObs"]:
            st.at[k, "nObs"] = 1.0
        if not st.at[k, "BAS"]:
            st.at[k, "BAS"] = basm.get(k, 0.0)
    # l. 309-325: BSY of the yields
    pty = {(a, r) for a, r in sets.pact_to_y} if hasattr(sets, "pact_to_y") else set()
    st["BSY"] = 0.0
    for k in st.index:
        reg, a, r = k
        if a in sets.mpact and a in sets.s_colsest and (a, r) in pty and st["BAS"].get((reg, a, "LEVL"), 0.0):
            st.at[k, "BSY"] = bsy(wide.loc[k, e8].to_numpy(float), float(st.at[k, "BAS"]))
    # back to p_data: the positions, and the feed BASM
    long = st.reset_index().melt(id_vars=KEYS, var_name="t", value_name="value")
    long = long[long["value"] != 0.0]
    changed = basm[basm != wide["BASM"]]
    p = p[~(p["t"].isin(["nObs", "nW", "WAve", "wVar", "BAS", "BSY"]))]
    if len(changed):
        idx = pd.MultiIndex.from_frame(p[KEYS])
        drop = (p["t"] == "BASM").to_numpy() & idx.isin(changed.index)
        p = p[~drop]
        add = changed[changed != 0.0].reset_index()
        add.columns = KEYS + ["value"]
        add["t"] = "BASM"
        long = pd.concat([long, add], ignore_index=True)
    for c in p.columns:
        if c not in long.columns:
            long[c] = 0 if c == "eps" else None
    return pd.concat([p, long[p.columns]], ignore_index=True)

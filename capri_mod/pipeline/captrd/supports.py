"""CAPTRD's supports from Step 1: the prior of each series in each ex-ante year, before the external information.

Ported from define_stats_and_supports.gms l. 186-330 (CAPRI star 3.0), with BSY from prep_data_for_estimation.gms
l. 300-317. The external supports that follow (COCO nowcasts, expert and DG AGRI information, the trust levels,
l. 380-676, and adjust_trade_supports.gms) are not part of this module.

A series is (region, col, row). Inputs per series (a DataFrame indexed by series): nobs, wr2, wave, wvarerr (Step 1,
capri_mod.pipeline.captrd.step1), basm, bast (0 where absent), bas, bsy; Step1 per ex-ante year (a DataFrame with the
years as columns). B is BAST where it is nonzero, else BASM (l. 195-212).

    yields:      the (activity, output) pairs of PACT_TO_Y (main output = yield row); crops: MCACT
    no_yield_drop, breed_act, grs_act: sets_captrd.gms / sets.gms (capri_data/pipeline/captrd/sets)
    reqfcnlim:   {(col, row): (lo, up)} feed/feed_decl.gms l. 284-310
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd


@dataclass
class SupportSets:
    pact_to_y: Set[Tuple[str, str]]
    mcact: Set[str]
    no_yield_drop: Set[str]
    breed_act: Set[str]
    grs_act: Set[str]
    reqst: Set[str]
    feed: Set[str]
    mpact: Set[str]
    reqfcnlim: Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]] = field(default_factory=dict)


def best_three_yields(levels_bas: pd.Series, yields: pd.DataFrame, eightlst: Sequence[int],
                      bas: pd.Series) -> pd.Series:
    """BSY: max(mean of the three highest distinct yields of the last eight ex-post years, BAS)
    (prep_data_for_estimation.gms l. 300-317; "distinct": the second and third SMAX exclude values equal to the
    first and second). yields: series x years (0 = missing); levels_bas: the activity's LEVL BAS per series."""
    cols = [str(y) for y in eightlst if str(y) in yields.columns]
    out = {}
    for idx, row in yields[cols].iterrows():
        if not levels_bas.get(idx, 0.0):
            continue
        v = row.to_numpy(dtype=float)
        v = v[v != 0.0]
        if v.size == 0:
            continue
        first = v.max()
        rest = v[v != first]
        second = rest.max() if rest.size else 0.0
        rest2 = rest[rest != second]
        third = rest2.max() if rest2.size else 0.0
        out[idx] = max((first + second + third) / 3.0, float(bas.get(idx, 0.0)))
    return pd.Series(out, dtype=float)


def supports(st: pd.DataFrame, step1: pd.DataFrame, years: Sequence[int], bas_year: int, bast_year: int,
             sets: SupportSets) -> Tuple[pd.DataFrame, pd.Series]:
    """Supports per series and ex-ante year (DataFrame, years as columns) and the stored error variance."""
    idx = st.index
    cols = idx.get_level_values(1)
    rows = idx.get_level_values(2)
    n = st["nobs"].to_numpy(float)
    wr2 = st["wr2"].to_numpy(float)
    basm = st["basm"].to_numpy(float)
    bast = st["bast"].to_numpy(float)
    B = np.where(bast != 0.0, bast, basm)
    has = n != 0.0
    out = {}
    for t in years:
        s1 = step1[t].reindex(idx).fillna(0.0).to_numpy(float)
        dt = np.where(bast != 0.0, t - bast_year, t - bas_year)
        S = np.full(len(idx), np.nan)
        # l. 195-199: NTRD
        ntrd = has & (cols == "NTRD")
        S[ntrd] = (B * (1.0 - wr2) + s1 * wr2)[ntrd]
        # l. 203-212: all others, at least 0.001 x B (1 x B for CSSP with a negative base)
        oth = has & (cols != "NTRD")
        floor = B * np.where((cols == "CSSP") & (basm < 0.0), 1.0, 0.001)
        S[oth] = np.maximum(floor, B * (1.0 - wr2) + s1 * wr2)[oth]
        # l. 217-221: crop yields with BSY and sqrt(wR2)
        isy = np.array([(c, r) in sets.pact_to_y for c, r in zip(cols, rows)])
        cy = has & isy & np.isin(cols, list(sets.mcact))
        bsy = st["bsy"].to_numpy(float)
        sq = np.sqrt(np.clip(wr2, 0.0, None))
        S[cy] = np.maximum(B * 0.001, bsy * (1.0 - sq) + s1 * sq)[cy]
        # l. 226-238: yields within 2.5 % a year of B
        y_ = has & isy
        S[y_] = np.maximum(np.minimum(S, B * 1.025 ** dt), B * 0.975 ** dt)[y_]
        # l. 242-246: no yield drop below B
        nyd = has & isy & np.isin(cols, list(sets.no_yield_drop))
        S[nyd] = np.maximum(S, B)[nyd]
        # l. 252-266: breeding animals' slaughter weight within 0.2 % a year of BASM (p_useBAST = 0)
        br = has & (rows == "SLGW") & np.isin(cols, list(sets.breed_act))
        d0 = t - bas_year
        S[br] = np.maximum(np.minimum(S, basm * 1.002 ** d0), basm * 0.998 ** d0)[br]
        # l. 272-281: UAAR at most B, at least B x 0.998^(t - BAST) (the global BAST year)
        ua = (cols == "UAAR") & (rows == "LEVL") & (B != 0.0) & ~np.isnan(S) & (S != 0.0)
        S[ua] = np.maximum(np.minimum(B, S), B * 0.998 ** (t - bast_year))[ua]
        # l. 285-286: grassland at least 0.9 x BASM (no nObs condition)
        gr = (rows == "LEVL") & np.isin(cols, list(sets.grs_act))
        S[gr] = np.maximum(basm * 0.9, np.nan_to_num(S))[gr]
        # l. 290-293: DAYS / DAILY within the requirement functions' limits, where the activity has observations
        for (c, r), (lo, up) in sets.reqfcnlim.items():
            m = (cols == c) & (rows == r)
            if not m.any():
                continue
            lev = st.reindex(pd.MultiIndex.from_arrays([idx.get_level_values(0)[m], [c] * int(m.sum()),
                                                        ["LEVL"] * int(m.sum())]))["nobs"].fillna(0.0).to_numpy()
            mm = np.where(m)[0][lev != 0.0]
            if lo is not None:
                S[mm] = np.maximum(np.nan_to_num(S[mm]), 0.99 * lo)
            if up is not None:
                S[mm] = np.minimum(S[mm], 1.01 * up)
        # l. 298-301: feed input coefficients at BASM (0.1 x the member state's BASM where missing: not ported here,
        # the regional rows need the member-state values)
        fe = has & np.isin(cols, list(sets.mpact)) & np.isin(rows, list(sets.feed))
        S[fe] = basm[fe]
        # l. 312-313: GROF of the feed aggregates at BASM where the series has no variance
        wvar = st["wvar"].to_numpy(float) if "wvar" in st.columns else np.zeros(len(idx))
        gf = has & (cols == "GROF") & np.isin(rows, list(sets.feed)) & (wvar == 0.0)
        S[gf] = basm[gf]
        # l. 318-319: requirement scalers
        rq = np.isin(rows, list(sets.reqst)) & has & (st.get("const", 0) + st.get("slope", 0) != 0) \
            if "const" in st.columns else np.zeros(len(idx), bool)
        S[rq] = 1.0
        out[t] = S
    sup = pd.DataFrame(out, index=idx)
    # l. 327-329: the stored error variance, with its floor 0.05 x |wAve| (a level against a variance; CAPTRD_MOD.md
    # section 12.4) except for requirements and feed
    no_floor = np.isin(rows, list(sets.reqst)) | np.isin(rows, list(sets.feed))
    wv = np.where(no_floor, st["wvarerr"].to_numpy(float),
                  np.maximum(np.abs(st["wave"].to_numpy(float)) * 0.05, st["wvarerr"].to_numpy(float)))
    return sup, pd.Series(np.where(has, wv, np.nan), index=idx)

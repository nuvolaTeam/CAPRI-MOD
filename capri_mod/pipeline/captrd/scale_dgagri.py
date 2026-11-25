"""CAPTRD's scaling of the DG AGRI baseline to CAPRI's base period (captrd/scale_DG_AGRI_baseline.gms, captrd.gms l. 954;
CAPRI star 3.0): the Aglink stage's p_result(..., "DGAgri") (aglink.py) to p_result(..., "DGAgri1"), the relative
changes of the outlook applied to CAPRI's own values of the base period BAST (the three years around the second-last
ex-post year, BasYrsT).

In GAMS's order (line numbers of scale_DG_AGRI_baseline.gms):
  l. 35-46    the regions: the member states and the EU's two parts (RaggEst: the Aglink EU aggregates without the top
              aggregate EU27)
  l. 52-77    BAST of p_data (nonzero years) and of DGAgri, the yields first moved to their products
  l. 88-158   prices (UVAG) and yields: DGAgri1 = p_data's BAST x DGAgri / DGAgri's BAST, from the member state's own
              outlook, else from its EU part's, else from the EU27's
  l. 165-283  market balances: tiny values removed, human consumption from per-head consumption and for meats and eggs
              from DOMM, the EU parts' p_data where missing summed from their members, non-negativity, the BAST2
              averages (only the years where both have data) and the scaling; COMI from GROF
  l. 290-350  activity levels, as the balances
  l. 355-420  biofuels and fuels of the EU parts: the factor where it lies in (0, 2), else the difference added
  l. 430-433  DOMM of the EU parts recalculated from its positions (DOMPOS)
  l. 441-461  seed and losses removed from DGAgri1; the EU27's DGAgri1 deleted

The p_data written here (the regions' BAST, the EU parts' years and BAST2) is returned with the results, as GAMS keeps
it in p_data. Each statement's arithmetic is a named function quoting its GAMS in
capri_mod/pipeline/captrd/equations/scale_DG_AGRI_baseline.py. GAMS's semantics as in aglink.py (P4: 0 is an absent record).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

from capri_mod.pipeline.captrd.aglink import P4, _nz
from capri_mod.pipeline.captrd.equations import scale_DG_AGRI_baseline as SG

#: l. 162-163: market balance values at or below this are deleted
TINY = 1e-10


def _p4(df: pd.DataFrame) -> P4:
    out = P4()
    for r, c, w, t, v in zip(df["region"], df["col"], df["row"], df["t"].astype(str), df["value"].astype(float)):
        out.put((r, c, w, t), v)
    return out


def scale(pdata: pd.DataFrame, dgagri: pd.DataFrame, *, ms: Iterable[str], ragg: Sequence[str], top: Sequence[str],
          west: Sequence[str], map_rr: Iterable[Tuple[str, str]], pact: Iterable[str],
          pact_to_y: Iterable[Tuple[str, str]], cols_est: Iterable[str], rows_est: Iterable[str],
          mrkbalee: Iterable[str], dompos: Iterable[str], fuels: Iterable[str], meas: Iterable[str],
          basyrst: Sequence[int], exante: Sequence[int], years_cur: Sequence[int], years: Sequence[int]):
    """(DGAgri1, DGAgri as modified here, p_data as modified here), each a P4 keyed (region, col, row, t)."""
    P, D, D1 = _p4(pdata), _p4(dgagri), P4()
    ms, ragg, top, west = list(ms), list(ragg), list(top), list(west)
    rest = ms + ragg
    europ = ragg + top                                                   # CurEuropAgg (l. 644-652)
    members: Dict[str, List[str]] = {}
    for a, b in map_rr:
        if b in set(ms):
            members.setdefault(a, []).append(b)
    cols_est, rows_est = set(cols_est), set(rows_est)
    pact = set(pact)
    pty = [(c, o) for c, o in pact_to_y if c in pact and c in cols_est and o in rows_est]
    mrk = [c for c in mrkbalee]
    bas = [str(y) for y in basyrst]
    ex = [str(y) for y in exante]
    ycur = [str(y) for y in years_cur]
    yrs = [str(y) for y in years]

    def keys(src: P4, regs, cs=None, ws=None, ts=None):
        regs = set(regs)
        return [k for k in src if k[0] in regs and (cs is None or k[1] in cs) and (ws is None or k[2] in ws)
                and (ts is None or k[3] in ts)]
    # l. 53-57: p_data's BAST
    for (r, c, w) in sorted({k[:3] for k in keys(P, rest, cols_est, rows_est, set(bas))}):
        v = SG.P_Data_BAST([P.g(r, c, w, y) for y in bas])
        if v is not None:
            P.put((r, c, w, "BAST"), v)
    # l. 62-66: the yields moved to their products
    for r in rest:
        for c, o in pty:
            for y in yrs:
                if not _nz(D.g(r, c, o, y)) and _nz(D.g(r, c, "YILD", y)):
                    D.put((r, c, o, y), SG.P_Result_DgAgri_yield(D.g(r, c, "YILD", y)))
    # l. 69-72: DGAgri's BAST

    def dg_bast(regs, cs, ws):
        for (r, c, w) in sorted({k[:3] for k in keys(D, regs, cs, ws, set(bas))}):
            v = SG.p_result_BAST_DGAgri([D.g(r, c, w, y) for y in bas])
            if v is not None:
                D.put((r, c, w, "BAST"), v)
    dg_bast(rest, cols_est, rows_est)
    # l. 86-94: the EU aggregates' prices where missing from EU_WEST, and their BAST
    for r in europ:
        for w in rows_est:
            for y in yrs:
                if not _nz(D.g(r, "UVAG", w, y)):
                    D.put((r, "UVAG", w, y), SG.p_result_UVAG_EU([D.g(x, "UVAG", w, y) for x in west]))
    dg_bast(europ, {"UVAG"}, rows_est)
    # l. 98-128: prices (Pric = UVAG; PADM is not in Pric)
    for (r, c, w) in sorted({k[:3] for k in keys(D, rest, {"UVAG"}, rows_est) if k[3] == "BAST"}):
        for y in ex:
            D1.put((r, c, w, y), SG.p_result_DGAgri1(P.g(r, c, w, "BAST"), D.g(r, c, w, y), D.g(r, c, w, "BAST")))
    for agg in ragg + top:                                               # l. 108-115, then l. 121-128
        for w in rows_est:
            if not _nz(D.g(agg, "UVAG", w, "BAST")):
                continue
            for m in members.get(agg, []):
                for y in ex:
                    if not _nz(D1.g(m, "UVAG", w, y)):
                        D1.put((m, "UVAG", w, y), SG.p_result_DGAgri1(P.g(m, "UVAG", w, "BAST"), D.g(agg, "UVAG", w, y),
                                                                      D.g(agg, "UVAG", w, "BAST")))
    # l. 135-150: yields
    for r in rest:
        for c, o in pty:
            if _nz(D.g(r, c, o, "BAST")):
                for y in yrs:
                    D1.put((r, c, o, y), SG.p_result_DGAgri1(P.g(r, c, o, "BAST"), D.g(r, c, o, y), D.g(r, c, o, "BAST")))
    for agg in ragg:
        for c, o in pty:
            if not _nz(D.g(agg, c, o, "BAST")):
                continue
            for m in members.get(agg, []):
                for y in yrs:
                    if not _nz(D1.g(m, c, o, y)):
                        D1.put((m, c, o, y), SG.p_result_DGAgri1(P.g(m, c, o, "BAST"), D.g(agg, c, o, y),
                                                                 D.g(agg, c, o, "BAST")))
    # l. 162-163: tiny market balance values
    for k in keys(D, rest, set(mrk)):
        if k[3] in set(yrs) and abs(D[k]) <= TINY:
            D.put(k, SG.p_result_MrkBalee_tiny())
    # l. 170-182: human consumption
    for r in rest:
        for w in rows_est:
            for y in ycur:
                if _nz(D.g(r, "INHA", w, y)) and not _nz(D.g(r, "HCOM", w, y)):
                    D.put((r, "HCOM", w, y), SG.p_result_HCOM_INHA(D.g(r, "INHA", w, y),
                                                                   [P.g(m, "INHA", "LEVL", y) for m in members.get(r, [])]))
        for w in [x for x in rows_est if x in set(meas) or x == "EGGS"]:
            for y in ycur:
                if _nz(D.g(r, "DOMM", w, y)) and not _nz(D.g(r, "HCOM", w, y)):
                    D.put((r, "HCOM", w, y), SG.p_result_HCOM_DOMM(D.g(r, "DOMM", w, y)))

    def agg_pdata(c, w):
        """l. 208-211 / 302-305: the EU part's p_data where missing, from its members without their own DGAgri."""
        for agg in ragg:
            if not any(_nz(D.g(agg, c, w, y)) for y in ex):
                continue
            for y in ycur:
                if not _nz(P.g(agg, c, w, y)):
                    P.put((agg, c, w, y), SG.p_data_RaggEst([P.g(m, c, w, y) for m in members.get(agg, [])
                                                             if not _nz(D.g(m, c, w, y))]))

    def bast2(c, w):
        """l. 229-243 / 314-328: the BAST2 averages over the years where both have data."""
        for agg in ragg:
            both = [y for y in bas if _nz(P.g(agg, c, w, y)) and _nz(D.g(agg, c, w, y))]
            if both:
                P.put((agg, c, w, "BAST2"), SG.BAST2([P.g(agg, c, w, y) for y in bas if _nz(D.g(agg, c, w, y))],
                                                     len(both)))
                D.put((agg, c, w, "BAST2"), SG.BAST2([D.g(agg, c, w, y) for y in bas if _nz(P.g(agg, c, w, y))],
                                                     len(both)))
    # l. 208-286: market balances
    for c in mrk:
        for w in rows_est:
            agg_pdata(c, w)
    for agg in ragg:                                                     # l. 213-216
        for c in mrk:
            for w in rows_est:
                for y in ycur:
                    v = D.g(agg, c, w, y)
                    if _nz(v):
                        D.put((agg, c, w, y), SG.p_result_RaggEst_net(v, [D.g(m, c, w, y) for m in members.get(agg, [])]))
    for k in keys(D, rest, set(mrk) - {"INTP", "NTRD"}, rows_est, set(ycur)):     # l. 221-223
        D.put(k, SG.p_result_nonneg(D[k]))
    for c in mrk:
        for w in rows_est:
            bast2(c, w)
    for agg in ragg:                                                     # l. 250-257
        for c in mrk:
            if c == "NTRD":
                continue
            for w in rows_est:
                pb, db = P.g(agg, c, w, "BAST2"), D.g(agg, c, w, "BAST2")
                if _nz(pb) and _nz(db):
                    for y in ycur:
                        if _nz(D.g(agg, c, w, y)):
                            D1.put((agg, c, w, y), SG.p_result_DGAgri1_BAST2(D.g(agg, c, w, y), pb, db))
        for c in ("DOMM", "PRCM"):                                       # l. 264-272 (COMI from GROF)
            if c not in set(mrk):
                continue
            pb, gb = P.g(agg, c, "COMI", "BAST2"), D.g(agg, "GROF", "COMI", "BAST2")
            if _nz(pb) and _nz(gb):
                for y in ycur:
                    if not _nz(D.g(agg, c, "COMI", y)) and _nz(D.g(agg, "GROF", "COMI", y)):
                        D1.put((agg, c, "COMI", y), SG.p_result_COMI_DGAgri1(D.g(agg, "GROF", "COMI", y), pb, gb))
    for m in ms:                                                         # l. 279-286
        for c in mrk:
            if c == "NTRD":
                continue
            for w in rows_est:
                pb, db = P.g(m, c, w, "BAST"), D.g(m, c, w, "BAST")
                if _nz(pb) and _nz(db):
                    for y in ycur:
                        if _nz(D.g(m, c, w, y)):
                            D1.put((m, c, w, y), SG.p_result_DGAgri1_BAST2(D.g(m, c, w, y), pb, db))
    # l. 302-350: activity levels
    for c in cols_est:
        agg_pdata(c, "LEVL")
    for agg in ragg:                                                     # l. 307-309
        for c in cols_est:
            for y in ycur:
                D.put((agg, c, "LEVL", y), SG.p_result_RaggEst_LEVL_net(
                    D.g(agg, c, "LEVL", y), [D.g(m, c, "LEVL", y) for m in members.get(agg, [])]))
    for c in cols_est:
        bast2(c, "LEVL")
    for agg in ragg:                                                     # l. 333-339
        for c in cols_est:
            pb, db = P.g(agg, c, "LEVL", "BAST2"), D.g(agg, c, "LEVL", "BAST2")
            if _nz(pb) and _nz(db):
                for y in ycur:
                    if _nz(D.g(agg, c, "LEVL", y)):
                        D1.put((agg, c, "LEVL", y), SG.p_result_DGAgri1_BAST2(D.g(agg, c, "LEVL", y), pb, db))
    for m in ms:                                                         # l. 344-350
        for c in cols_est:
            pb, db = P.g(m, c, "LEVL", "BAST"), D.g(m, c, "LEVL", "BAST")
            if _nz(pb) and _nz(db):
                for y in ycur:
                    if _nz(D.g(m, c, "LEVL", y)):
                        D1.put((m, c, "LEVL", y), SG.p_result_DGAgri1_BAST2(D.g(m, c, "LEVL", y), pb, db))

    # l. 364-420: biofuels and fuels of the EU parts
    def biof(agg, c, w):
        pb, db = P.g(agg, c, w, "BAST2"), D.g(agg, c, w, "BAST2")
        if not _nz(db):
            return
        for y in ycur:
            v = D.g(agg, c, w, y)
            if not _nz(v):
                continue
            D1.put((agg, c, w, y), SG.p_result_DGAgri1_biofuels(v, pb, db))
    for agg in ragg:
        for c in mrk:
            for w in fuels:
                biof(agg, c, w)
        for w in rows_est:
            biof(agg, "BIOF", w)
        for w in rows_est:                                               # l. 429-432
            s_ = {y: SG.p_result_DOMM_DGAgri1([D1.g(agg, c, w, y) for c in dompos]) for y in ycur}
            for y in ycur:
                if _nz(s_[y]) and _nz(D1.g(agg, "DOMM", w, y)):
                    D1.put((agg, "DOMM", w, y), s_[y])
    # l. 443-464
    for k in [k for k in D1 if k[0] in set(rest) and k[1] in ("SEDF", "SEDM", "LOSF", "LOSM") and k[3] in set(ycur)]:
        D1.put(k, SG.p_result_DGAgri1_removed())
    for k in [k for k in D1 if k[0] in set(top) and k[1] in cols_est and k[2] in rows_est and k[3] in set(ycur)]:
        D1.put(k, SG.p_result_DGAgri1_removed())
    return D1, D, P

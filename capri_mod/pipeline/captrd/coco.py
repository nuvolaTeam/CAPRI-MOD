"""CAPTRD's use of the COCO data (captrd/load_coco1_data.gms, CAPRI star 3.0, %NewBiofuelModule% = ON).

COCO's output (coco2_output.gdx, symbol DATA2 loaded as dataMS; item COCO1) extends CAPREG's series to the years
after them (ExAnteD, 2019 in the reference run), supplies the biofuel series of every year, and marks positions with
near-zero flags. The GDX's other items (INI, COCO2) are read by CAPTRD only to be zeroed (l. 63): not used here.

Order, as load_coco1_data.gms, in three parts:
  prepare_country  l. 41-233 on one country's COCO data (dataMS): UVAD removed, usable years (COCO UAAR), MAPR
                   without the raw product's PRCM, HERD, LOSF/FEDM/NETF/DOMM of the fodder and cereals, MAPR from
                   NETF, the 1e-13 flags of ExAnteD, BASM as the BASYRSM mean, the split activities and set-aside
                   series, VSET, UVAG from UVAP, LEVL and GROF without NUTS 2 data, the GROF-only flags removed
  bio_flags        the "some country has data" conditions of l. 337 and 346, over every country's prepared data
  apply_country    l. 250-561 on p_data: the years after CAPREG's series from COCO (factor or difference to BASM),
                   LEVL/GROF consistency, the biofuel positions from COCO, the non-EU countries' biofuel data from
                   fao_agg (p_biofuelData), biofuel prices and conversion factors, the near-zero biofuel defaults,
                   the years without COCO UAAR emptied, HCOM of the fuels
Not ported: p_result_MSnoEU (l. 422-497), Aglink expert supports of the non-EU countries for Step 2 (belongs to the
expert supports); p_data of the market aggregates (l. 553-554), which no estimated series of the regions reads.

The default biostocks (l. 524-537) and DDGS (l. 545-548) use CAPRI's extraction rates P_ExtrRates and by-product
coefficients p_ByProduct (dat/biofuel/biofuel_technology_params.gms, captrd.gms l. 340-341; prepare.read_dat()):
without them (extr=None) these three statements are skipped and reported in the returned list.

GAMS semantics as in prepare.py: a zero is no record; assignments are parallel; EPS is not loaded.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from capri_mod.pipeline.captrd.prepare import KEYS, CaptrdSets, Wide, _year

# load_coco1_data.gms, transcribed
COLS_NO_COCO = {"LOSF", "LOSM", "SEDM", "SEDF"}                                         # l. 29
DEL_COCO_COLS = {"UVAD"}                                                               # l. 37-42
BIO_COLS_COCO = {"BIOF", "PRCB", "PRCBY"}                                             # l. 316
BIO_ROWS_COCO = {"BIOD", "BIOE", "DISL", "GASL", "CRDO", "DDGS"}                       # l. 317
POTENTIAL_STOCKS = ["SWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "RAPO", "SUNO", "SOYO", "PLMO", "SUGA", "TWIN"]
ROWS_LOAD_PLUS = {"CERE"}                                                              # l. 20
EXPOST_BIO_FROM = 2002                                                                 # l. 326: years after 2002
DEFAULTS_FROM = 2000                                                                   # l. 503-548: 2000 on, and BASM


class Series:
    """One country's COCO1 data: a Series per (col, row) over t (years as text, BASM)."""

    def __init__(self, d: pd.DataFrame, ts: List[str]):
        self.idx = pd.Index(ts, name="t")
        self.s: Dict[Tuple[str, str], pd.Series] = {}
        for (c, r), g in d.groupby(["col", "row"], sort=False):
            self.s[(c, r)] = g.set_index("t")["value"].reindex(self.idx, fill_value=0.0)
        self.zero = pd.Series(0.0, index=self.idx)
        self.t = pd.Series(self.idx, index=self.idx)

    def __call__(self, c, r):
        return self.s.get((c, r), self.zero)

    def put(self, c, r, v, where=None):
        if where is not None:
            v = v.where(where, self(c, r))
        if (v != 0).any():
            self.s[(c, r)] = v.astype(float)
        else:
            self.s.pop((c, r), None)

    def keys(self, cols=None, rows=None):
        return [k for k in list(self.s) if (cols is None or k[0] in cols) and (rows is None or k[1] in rows)]


def exante_d(coco: pd.DataFrame, ms: Iterable[str], expost: Iterable[int], years: Iterable[int]) -> List[int]:
    """l. 49: ExAnteD = the years outside ExPost with COCO1 UAAR for some country."""
    u = coco[(coco["item"].str.upper() == "COCO1") & (coco["col"] == "UAAR") & (coco["row"] == "LEVL")
             & coco["region"].isin(set(ms)) & (coco["value"] != 0)]
    ys = {int(t) for t in u["t"] if str(t).isdigit()}
    return sorted(y for y in ys if y in set(years) and y not in set(expost))


def prepare_country(coco: pd.DataFrame, p: pd.DataFrame, ms: str, sets: CaptrdSets, expost: Iterable[int],
                    exanted: Iterable[int], years: Iterable[int], basyrs5: Iterable[int], basyrsm: Iterable[int]
                    ) -> Tuple[Series, Set[str]]:
    """load_coco1_data.gms l. 37-247 for the country ms. coco: its COCO data (region, item, col, row, t, value[, eps]);
    p: its p_data so far (years and BASM, its NUTS 2 regions included). Returns the prepared COCO1 data and the usable
    years."""
    yrs = [str(int(y)) for y in years]
    exp = {str(int(y)) for y in expost}
    exd = {str(int(y)) for y in exanted}
    expt = exp | exd                                                   # l. 53-54: ExPostT
    b5 = {str(int(y)) for y in basyrs5}
    bm = {str(int(y)) for y in basyrsm}
    c = coco[(coco["region"] == ms) & (coco["item"].str.upper() == "COCO1")]
    if "eps" in c.columns:
        c = c[c["eps"] == 0]
    c = c[c["t"].astype(str).isin(set(yrs))]
    d = Series(c.assign(t=c["t"].astype(str)), yrs + ["BASM"])
    t = d.t
    is_y = t.isin(set(yrs))
    rows_load = sets.rows_load | ROWS_LOAD_PLUS
    pw = Wide(p) if len(p) else None

    def pv(col, row, tt, region=ms):
        if pw is None:
            return 0.0
        return float(pw(col, row).get((region, tt), 0.0))

    def pb(col, row):
        return pv(col, row, "BASM")

    # l. 43: UVAD of COCO removed
    for k in d.keys(cols=DEL_COCO_COLS):
        d.put(*k, d.zero, where=is_y)
    # l. 57-63: usable years have COCO UAAR; the others emptied
    usable = {tt for tt in yrs if d("UAAR", "LEVL").get(tt, 0.0) != 0}
    us = t.isin(usable)
    for k in d.keys():
        d.put(*k, d.zero, where=is_y & ~us)
    # l. 66-67: no MAPR where a raw product has no PRCM (milk excepted)
    raws: Dict[str, List[str]] = {}
    for out, raw in sets.prcd:
        raws.setdefault(out, []).append(raw)
    for k in d.keys(cols={"MAPR"}):
        r = k[1]
        if r == "MILK" or r not in raws:
            continue
        miss = sum(((d("PRCM", r1) == 0).astype(float) for r1 in raws[r]), d.zero)
        d.put(*k, d.zero, where=is_y & (miss > 0))
    # l. 70-74: HERD from LEVL and DAYS
    for a in sorted(sets.aact):
        h, dy, lv = d(a, "HERD"), d(a, "DAYS"), d(a, "LEVL")
        d.put(a, "HERD", lv * dy / 365.0, where=is_y & (h == 0) & (dy != 0) & (lv != 0))
    # l. 79-108: losses, feed, net feed and domestic use of the fodder and cereals COCO2 modifies
    lf = sorted({o for f, o in sets.feed_to_o if f in sets.corfeedlosf and o in sets.cropo})
    in_expt = t.isin(expt)
    for o in lf:
        g = d("GROF", o)
        gb, lb = pb("GROF", o), pb("LOSF", o)
        if gb != 0:
            d.put("LOSF", o, g * lb / gb, where=in_expt & (g != 0))
        neg = ["SEDM", "SEDF", "INDM", "PRCM", "BIOF", "HCOM", "LOSM", "LOSF", "EXPT", "STCM"]
        fedm = (g + d("IMPT", o) - sum((d(x, o) for x in neg), d.zero)).clip(lower=0.0)
        d.put("FEDM", o, fedm, where=in_expt & (g != 0))
        netf = (g - d("SEDF", o) - d("LOSF", o)).clip(lower=0.0)
        d.put("NETF", o, netf, where=in_expt & (g != 0))
        domm = sum((d(x, o) for x in sets.domm_set), d.zero).clip(lower=0.0)
        d.put("DOMM", o, domm, where=in_expt & (g != 0))
    # l. 112-120: MAPR from NETF where p_data has MAPR around the base year
    for (cc, r) in d.keys(cols={"NETF"}, rows=rows_load):
        if sum(pv("MAPR", r, tt) for tt in b5) == 0:
            continue
        d.put("MAPR", r, d("NETF", r), where=in_expt & (d("MAPR", r) == 0) & (d("NETF", r) != 0))
    # l. 124-140: near-zero flags in ExAnteD
    in_exd = t.isin(exd) & us
    total = {k: float(v[is_y].sum()) for k, v in d.s.items()}
    for cc in sorted(sets.mrkbalee - COLS_NO_COCO):
        for r in sorted({k[1] for k in d.keys(cols={cc})} & rows_load - {"OANI", "OCRO"}):
            if total.get((cc, r), 0.0) != 0:
                d.put(cc, r, pd.Series(1e-13, index=d.idx), where=in_exd & (d(cc, r) == 0))
    for cc in sorted({k[0] for k in d.keys(rows={"LEVL"})} & sets.cols_load - {"OANI", "OCRO"}):
        if total.get((cc, "LEVL"), 0.0) != 0:
            d.put(cc, "LEVL", pd.Series(1e-13, index=d.idx), where=in_exd & (d(cc, "LEVL") == 0))
    # l. 144-148: BASM as the mean of the nonzero BASYRSM years

    def _basm(keys):
        for k in keys:
            v = d(*k)
            nz = v[v.index.isin(bm) & (v != 0)]
            if len(nz):
                d.put(*k, pd.Series(float(nz.sum()) / len(nz), index=d.idx), where=(t == "BASM"))
    _basm([k for k in d.keys(cols=sets.cols_load, rows=rows_load)])
    # l. 157-175: the split activities from their aggregate (DACT)
    parts: Dict[str, List[str]] = {}
    for da, pa in sets.dact_to_pact:
        parts.setdefault(pa, []).append(da)
    for sa in sorted(sets.splitacts):
        dacts = parts.get(sa, [])
        rows_ = {k[1] for k in d.keys(cols=set(dacts))} & rows_load
        for r in sorted(rows_):
            dsum = sum((d(x, r) for x in dacts), d.zero)
            db = float(dsum.get("BASM", 0.0))
            pB = pb(sa, r)
            if db == 0 or pB == 0:
                continue
            safe = (pB < 2 * db) and (pB > 0)
            if safe:
                val = dsum * (pB / db)
            else:
                val = (dsum + pB - db).clip(lower=1e-12) if (db + pB) > 1e-12 else d.zero
            d.put(sa, r, val, where=is_y & (d(sa, r) == 0) & us)
    # l. 179-183: the set-aside components from FALL
    setf = sorted(a for a, g in sets.p_t_actagg if g == "SETF")
    fall_rows = {k[1] for k in d.keys(cols={"FALL"})} & rows_load
    new = {}
    for cc in setf:
        for r in sorted(fall_rows):
            fb = float(d("FALL", r).get("BASM", 0.0))
            pB = pb(cc, r)
            if fb == 0 or pB == 0:
                continue
            new[(cc, r)] = d("FALL", r) / fb * pB
    for (cc, r), v in new.items():                                       # parallel: FALL itself is a component
        d.put(cc, r, v, where=is_y & us)
    # l. 190-193: VSET not above its base in ExAnteD
    vb = pb("VSET", "LEVL")
    if vb != 0:
        v = d("VSET", "LEVL")
        d.put("VSET", "LEVL", v.clip(upper=vb), where=is_y & us & t.isin(exd) & (v != 0))
    # l. 198-203: UVAG from the change of UVAP
    for (cc, r) in d.keys(cols={"UVAP"}, rows=rows_load):
        ub = float(d("UVAP", r).get("BASM", 0.0))
        pB = pb("UVAG", r)
        if ub == 0 or pB == 0 or sum(pv("UVAG", r, tt) for tt in b5) == 0:
            continue
        d.put("UVAG", r, d("UVAP", r) / ub * pB, where=is_y & us)
    # l. 208-217: BASM again for the split and set-aside activities and UVAG
    _basm([k for k in d.keys(cols=sets.mpact & (sets.dmpact | set(setf)), rows=rows_load)])
    _basm([k for k in d.keys(cols={"UVAG"}, rows=rows_load)])
    # l. 222-233: no recent GROF and LEVL where the NUTS 2 regions have none (countries with NUTS 2 regions)
    subs = {r for a, r in sets.map_rr if a == ms and r in sets.srnuts2}
    if len(subs) > 1:
        late = is_y & us & ~t.isin(exp)
        for (cc, o) in d.keys(cols={"GROF"}, rows=sets.o):
            if not any(pv("GROF", o, tt, r) for r in subs for tt in bm):
                d.put(cc, o, d.zero, where=late)
        for (a, r_) in d.keys(cols=sets.mpact, rows={"LEVL"}):
            if not any(pv(a, "LEVL", tt, r) for r in subs for tt in bm):
                d.put(a, r_, d.zero, where=late)
    # l. 239-247: the flags of positions other than GROF removed where GROF is given (as coded: the inner sum tests the
    # position itself, so every position at most 1e-12 goes)
    g_all = {r: d("GROF", r) for r in {k[1] for k in d.keys(cols={"GROF"})}}
    for (cc, r) in d.keys(cols=sets.mrkbalee - COLS_NO_COCO - {"GROF"}, rows=rows_load):
        if total.get((cc, r), 0.0) == 0 or r not in g_all:
            continue
        v = d(cc, r)
        d.put(cc, r, d.zero, where=t.isin(exd) & us & (v <= 1e-12) & (g_all[r] > 1e-12))
    # l. 330-334: HCOM of the biofuels rebooked to BIOF (on the ExPostT years and BASM)
    etb = t.isin(expt) | (t == "BASM")
    for b in sorted(sets.biofuels):
        hc = d("HCOM", b)
        d.put("BIOF", b, d("BIOF", b) + hc, where=etb & (hc != 0))
        d.put("HCOM", b, d.zero, where=etb)
    return d, usable


def bio_flags(prepared: Dict[str, Series], expostt: Iterable[int]) -> Set[Tuple[str, str]]:
    """The (col, row) of the biofuel positions some country's COCO data has in an ExPostT year after 2002 (l. 326,
    337, 346)."""
    out = set()
    ys = {str(int(y)) for y in expostt if int(y) > EXPOST_BIO_FROM}
    for d in prepared.values():
        bio = d.t.isin(ys)
        for (c, r), v in d.s.items():
            if (c in BIO_COLS_COCO or r in BIO_ROWS_COCO) and (v[bio.values] != 0).any():
                out.add((c, r))
    return out


def apply_country(p: pd.DataFrame, d: Series, usable: Set[str], ms: str, sets: CaptrdSets, expost: Iterable[int],
                  exanted: Iterable[int], years: Iterable[int], basyrsm: Iterable[int], flags: Set[Tuple[str, str]],
                  biofuel: Optional[pd.DataFrame] = None, extr: Optional[Dict[str, pd.DataFrame]] = None
                  ) -> Tuple[pd.DataFrame, List[str]]:
    """load_coco1_data.gms l. 250-556 on the country's p_data. biofuel: fao_agg's p_biofuelData (d0 region, d1 col,
    d2 row, d3 t, value); extr: {"extr_rates": P_ExtrRates, "byproduct": p_ByProduct}, or None. Returns p_data and
    the statements skipped."""
    skipped: List[str] = []
    w = Wide(p)
    yrs = [str(int(y)) for y in years]
    exp = {str(int(y)) for y in expost}
    expt = exp | {str(int(y)) for y in exanted}
    bm = {str(int(y)) for y in basyrsm}
    # the country's region index must hold the COCO years (2019) and BASM
    need = sorted({tt for tt in d.idx if tt in set(yrs) or tt == "BASM"})
    have = set(w.idx)
    extra = [(ms, tt) for tt in need if (ms, tt) not in have]
    if extra:
        w = _extend(w, extra)
    reg_ms = w.region == ms
    tt_ = w.t
    is_y = tt_.isin(set(yrs))
    late = reg_ms & is_y & ~tt_.isin(exp) & tt_.isin(usable)
    rows_load = sets.rows_load | ROWS_LOAD_PLUS

    def dv(c, r):
        """d(c, r) on w's index (for the country; zero elsewhere)."""
        v = d(c, r)
        return pd.Series(np.where(reg_ms, tt_.map(v).fillna(0.0), 0.0), index=w.idx)

    # l. 253-284: the years after CAPREG's series from COCO, with a factor or a difference to BASM
    for (c, r) in d.keys(cols=sets.cols_load, rows=rows_load):
        dd = dv(c, r)
        db = float(d(c, r).get("BASM", 0.0))
        pB = float(w(c, r).get((ms, "BASM"), 0.0))
        if not (db != 0 or pB == 0):
            continue
        if pB > 0 and pB < 2 * db:
            val = dd * (pB / db)
        else:
            s_ = dd + pB
            diff = dd + pB - db
            val = pd.Series(np.where(s_ < 0, diff, np.where(s_ < 1e-13, 0.0, np.maximum(1e-13, diff))), index=w.idx)
        w.put(c, r, val, where=late & (dd != 0))
    # l. 290-295: GROF only with some producing activity; l. 299-302: EAAG with GROF's 1e-13
    acts_of: Dict[str, List[str]] = {}
    for a, o in sets.pact_to_o:
        if a in sets.mpact:
            acts_of.setdefault(o, []).append(a)
    for o in sorted(sets.o):
        g = w("GROF", o)
        acts = acts_of.get(o, [])
        some = sum(((w(a, "LEVL") > 2e-13).astype(float) for a in acts), w.zero)
        anyl = sum(((w(a, "LEVL") != 0).astype(float) for a in acts), w.zero)
        w.put("GROF", o, pd.Series(np.where(anyl > 0, 1e-13, 0.0), index=w.idx), where=late & (some == 0) & (g > 1e-13))
    for o in sorted(sets.o):
        w.put("EAAG", o, pd.Series(1e-13, index=w.idx), where=late & (w("GROF", o) == 1e-13))
    # l. 304-310: LEVL only with some output (set-aside excepted)
    setf = {a for a, g in sets.p_t_actagg if g == "SETF"}
    outs_of: Dict[str, List[str]] = {}
    for a, o in sets.pact_to_o:
        outs_of.setdefault(a, []).append(o)
    for a in sorted(sets.mpact - setf):
        lv = w(a, "LEVL")
        outs = outs_of.get(a, [])
        some = sum(((w("GROF", o) > 2e-13).astype(float) for o in outs), w.zero)
        anyg = sum(((w("GROF", o) != 0).astype(float) for o in outs), w.zero)
        w.put(a, "LEVL", pd.Series(np.where(anyg > 0, 1e-13, 0.0), index=w.idx), where=late & (some == 0) & (lv > 1e-13))
    # l. 335-352: the biofuel positions from COCO, on ExPostT and BASM (over every year: the ex-post data replaced)
    etb = reg_ms & (tt_.isin(expt) | (tt_ == "BASM"))
    bio_y = etb & (_year(tt_) > EXPOST_BIO_FROM)
    uaar = dv("UAAR", "LEVL") != 0
    for c in sorted(BIO_COLS_COCO):
        for r in sorted(rows_load):
            dd = dv(c, r)
            flag = (c, r) in flags and c not in {"PRCB", "PRCBY"}
            if not (dd != 0).any() and not flag and (c, r) not in w.s:
                continue
            add = pd.Series(np.where((dd == 0) & bio_y & uaar & flag, 1e-13, 0.0), index=w.idx)
            w.put(c, r, dd + add, where=etb)
    for c in sorted(sets.cols_load - {"UVAD"}):
        for r in sorted(BIO_ROWS_COCO):
            dd = dv(c, r)
            flag = (c, r) in flags
            if not (dd != 0).any() and not flag and (c, r) not in w.s:
                continue
            add = pd.Series(np.where((dd == 0) & bio_y & uaar & flag, 1e-13, 0.0), index=w.idx)
            w.put(c, r, dd + add, where=etb)
    for r in sorted(sets.fuels):
        w.put("UVAG", r, dv("UVAP", r), where=etb)
    # l. 356-420: fao_agg's biofuel data (%NewBiofuelModule% = ON)
    if biofuel is not None:
        bf = biofuel[biofuel["d0"] == ms]
        if "eps" in bf.columns:
            bf = bf[bf["eps"] == 0]
        bfs: Dict[Tuple[str, str], Dict[str, float]] = {}
        for c, r, t_, v in zip(bf["d1"], bf["d2"], bf["d3"], bf["value"]):
            bfs.setdefault((c, r), {})[str(t_)] = float(v)
        if ms in sets.msnoeu28:                                           # l. 364-365: EXOG to NAGR
            for b in sets.biofuels:
                ex = bfs.get(("EXOG", b), {})
                if ex:
                    na = bfs.setdefault(("NAGR", b), {})
                    for t_, v in ex.items():
                        na[t_] = na.get(t_, 0.0) + v

        def bv(c, r):
            m = bfs.get((c, r), {})
            return pd.Series(np.where(reg_ms, tt_.map(m).fillna(0.0), 0.0), index=w.idx)
        if ms in sets.msnoeu28:
            keys = {k for k in bfs if k[0] in BIO_COLS_COCO or k[1] in BIO_ROWS_COCO} | \
                   {k for k in w.s if k[0] in BIO_COLS_COCO or k[1] in BIO_ROWS_COCO}
            for k in sorted(keys):
                w.put(*k, bv(*k), where=etb & (w(*k).abs() <= 1e-13))
            for r in sorted(sets.fosfuels):
                w.put("UVAD", r, w("CPRI", r), where=etb & (w("UVAD", r).abs() <= 1e-13))
            basm = reg_ms & (tt_ == "BASM")
            inbm = tt_.isin(bm)
            for k in sorted(k for k in w.s if k[0] in BIO_COLS_COCO or k[1] in BIO_ROWS_COCO):
                v = w(*k)
                nz = v[(reg_ms & inbm & (v != 0)).values]
                if len(nz):
                    w.put(*k, pd.Series(float(nz.sum()) / len(nz), index=w.idx), where=basm & (v.abs() <= 1e-13))
        for b in sorted(sets.biofuels):
            pp = bv("PPRI", b)
            w.put("UVAG", b, pp, where=etb & (w("UVAG", b).abs() <= 1e-13) & (pp != 0))
            pm = bv("PMRK", b)
            w.put("UVAP", b, pm, where=etb & (w("UVAP", b).abs() <= 1e-13) & (pm != 0))
            up = w("UVAP", b)
            w.put("UVAD", b, up + w("CTAX", b), where=etb & (w("UVAD", b) == 0) & (up != 0))
        for s_ in sorted(sets.biostock):
            for c in ("PRCB", "PRCBY"):
                v = bv(c, s_)
                w.put(c, s_, v, where=etb & (w(c, s_) <= 1e-13) & (v != 0))
        for c in ("UVAG", "UVAP"):
            w.put(c, "GLYC", bv(c, "GLYC"), where=etb & (w(c, "GLYC") <= 1e-13))
    else:
        skipped.append("l. 356-420 (fao_agg p_biofuelData not given)")
    # l. 501-521: minimum biofuel positions from 2000 and in BASM
    dflt = reg_ms & ((_year(tt_) >= DEFAULTS_FROM) | (tt_ == "BASM")) & (tt_.isin(expt) | (tt_ == "BASM"))
    for r in sorted(sets.seco_biof):
        w.put("NAGR", r, pd.Series(1e-15, index=w.idx), where=dflt & (w("NAGR", r) == 0))
    for r in sorted(sets.seco_biof):
        w.put("MAPR", r, pd.Series(1e-14, index=w.idx), where=dflt & (w("MAPR", r) == 0))
    for r in sorted(sets.seco_biof):
        cond = dflt & (w("MAPR", r) < 1e-13) & (w("IMPT", r) < 1e-13)
        w.put("DOMM", r, pd.Series(1e-14, index=w.idx), where=cond & (w("DOMM", r) == 0))
        w.put("BIOF", r, pd.Series(1e-14, index=w.idx), where=cond & (w("BIOF", r) == 0))
    # l. 524-537: default biostocks; l. 545-548: DDGS (need P_ExtrRates and p_ByProduct)
    stocks_of = {f: [s_ for s_, f2 in sets.stock_to_fuel if f2 == f and s_ in POTENTIAL_STOCKS] for f in ("BIOE", "BIOD")}
    if extr is not None:
        er = extr["extr_rates"]
        for f, s_ in (("BIOE", "SWHE"), ("BIOD", "RAPO")):
            used = sum((w("BIOF", x) for x in stocks_of[f]), w.zero)
            rate = float(er.get((f, s_), 0.0))
            cond = dflt & (used < 1e-12) & (w("MAPR", f) < 1e-12) & (w("DOMM", s_) != 0)
            w.put("BIOF", s_, w("MAPR", f) / rate, where=cond)
    else:
        skipped.append("l. 524-537 default biostocks SWHE and RAPO (P_ExtrRates not given)")
    for s_ in POTENTIAL_STOCKS:
        w.put("BIOF", s_, pd.Series(1e-14, index=w.idx),
              where=dflt & (w("BIOF", s_) == 0) & (w("DOMM", s_) != 0))
    if extr is not None:
        byp = extr["byproduct"]
        used = sum((w("BIOF", x) for x in stocks_of["BIOE"]), w.zero)
        ddgs = sum((w("BIOF", s_) * float(byp.get(("DDGS", s_), 0.0))
                    for s_, b in sets.stock_to_by if b == "DDGS" and s_ in POTENTIAL_STOCKS), w.zero)
        w.put("MAPR", "DDGS", ddgs, where=dflt & (used < 1e-12) & (w("MAPR", "DDGS") == 0))
    else:
        skipped.append("l. 545-548 DDGS from the default biostocks (p_ByProduct not given)")
    # l. 551: the years without COCO UAAR emptied (but the population)
    gone = reg_ms & is_y & ~tt_.isin(usable)
    for k in list(w.s):
        if k != ("INHA", "LEVL"):
            w.put(*k, w.zero, where=gone)
    # l. 555: GROF of the secondary products; l. 558: HCOM of the fuels = DOMM (every region in estimation)
    for r in sorted(sets.secom):
        w.put("GROF", r, w.zero, where=is_y)
    for r in sorted(sets.fuel_rows):
        w.put("HCOM", r, w("DOMM", r), where=is_y)
    return w.long(), skipped


def _extend(w: Wide, extra: List[Tuple[str, str]]) -> Wide:
    """w with further (region, t) index entries (zeros)."""
    idx = w.idx.append(pd.MultiIndex.from_tuples(extra, names=["region", "t"])).sort_values()
    w.idx = idx
    w.s = {k: v.reindex(idx, fill_value=0.0) for k, v in w.s.items()}
    w.zero = pd.Series(0.0, index=idx)
    w.region = pd.Series(idx.get_level_values("region"), index=idx)
    w.t = pd.Series(idx.get_level_values("t"), index=idx)
    return w

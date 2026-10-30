"""CAPTRD's policy data (captrd/captrd_policy.gms, CAPRI star 3.0): milk and sugar quotas and set-aside rates in p_data.

Runs after LABH (captrd.gms l. 906) and before prep_data_for_estimation.gms, on the years of the run (YEARS: from
%FirstYear% to the last simulation year, so the quotas reach the ex-ante years) and BASM. Parts, in the file's order:

  milk_quotas      pol_input/mquota_update.gms (batinclude Years ORDT p_data BASM) and the expiry
                   (%mlkQutExpiry% 2009, captrd.gms l. 116): QUTA, QUTB, QUTS of COMI in the ex-ante years, BASM
  sugar_quotas     sugar/load_quotas.gms, policy/reformsugarquotas.gms (batinclude years p_data): QUTA, QUTB, QUTS of
                   SUGA in every year; the near-zero quotas of the EU members without one; none from 2017 under an
                   Aglink version without sugar quotas (noSugQuotaAglinkVersion)
  sugar_beet       captrd_policy.gms l. 61-108: the near-zero quotas of MSnoSugb; QUTS of SUGB from SUGA; its
                   distribution to the NUTS 2 regions
  set_aside        captrd_policy.gms l. 158-202: compulsory set-aside rates (SETR) of the arable crops
Data (tools/build/build_captrd_dat.py): p_MQuotaDat (dat/coco/milk_quota_dat.gms), PMQuotaReg (mquota_update.gms),
p_SQuotas, p_PPSQRenounce, p_PPSQCBuyBack (input_load_sugar_quotas.gdx; p_PPSQWithdraw has no records),
p_smallProdShare (dat/policy/smal_pshar.gms).

GAMS semantics as in prepare.py (a zero is no record; assignments parallel; loops sequential).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

import numpy as np
import pandas as pd

from capri_mod.csvio import read_csv

from capri_mod.pipeline.captrd.prepare import DAT_DIR, KEYS, CaptrdSets, Wide, _year

# captrd_policy.gms l. 46-59, transcribed
MS_NO_SUGB = ["IR000000", "CY000000", "EE000000", "LV000000", "MT000000", "SI000000", "BG000000", "MK000000",
              "MO000000", "BA000000", "KO000000", "NO000000"]
# mquota_update.gms l. 112-124: delivery quota factor 1 for these countries; MT the mean of 1 and its own
QDELFAC_ONE = ["AT000000", "DE000000", "FR000000", "FI000000", "UK000000", "SE000000", "IT000000", "CY000000",
               "CZ000000", "HU000000", "PL000000"]


def read_policy_dat(path=DAT_DIR) -> Dict[str, pd.DataFrame]:
    out = {}
    for n in ("p_mquotadat", "p_mquotareg", "p_smallprodshare", "p_squotas", "p_ppsqrenounce", "p_ppsqcbuyback"):
        out[n] = read_csv(path / f"{n}.csv", keep_default_na=False, dtype={"year": str})
    return out


def _years(ys) -> List[str]:
    return [str(int(y)) for y in ys]


def milk_quotas(w: Wide, ms: Iterable[str], dat: Dict[str, pd.DataFrame], years: Iterable[int],
                exante: Iterable[int], basyrsm: Iterable[int], lst_expost: int, expiry: int = 2009) -> None:
    """pol_input/mquota_update.gms with %1 = Years, %3 = p_data, %4 = BASM; then captrd_policy.gms l. 28 (expiry)."""
    ys = _years(years)
    exa = _years(exante)
    bm = _years(basyrsm)
    md = dat["p_mquotadat"]
    q: Dict[tuple, float] = {(r, i.upper(), y): v for r, i, y, v in zip(md["region"], md["info"], md["year"], md["value"])}
    for i in {k[1] for k in q}:                       # l. 31: BL000000 = BE + LU
        for y in {k[2] for k in q}:
            v = q.get(("BE000000", i, y), 0.0) + q.get(("LU000000", i, y), 0.0)
            if v:
                q[("BL000000", i, y)] = v
    reg = dat["p_mquotareg"]
    tot = {(r, y): v * 1000.0 for r, i, y, v in zip(reg["region"], reg["info"], reg["year"], reg["value"]) if i.upper() == "QUTTOT"}
    ms = list(ms)
    pp: Dict[tuple, float] = {}
    for m in ms:
        for y in ys:
            t = tot.get((m, y), 0.0)
            if int(y) < 2004:                             # l. 70-71
                t = q.get((m, "QUTDEL", y), 0.0) + q.get((m, "QUTDIR", y), 0.0)
            pp[(m, "QTOT", y)] = t
            den = q.get((m, "QUTDEL", y), 0.0) + q.get((m, "QUTDIR", y), 0.0)
            if den:
                pp[(m, "QDEL", y)] = q.get((m, "QUTDEL", y), 0.0) * t / den
                pp[(m, "QDIR", y)] = q.get((m, "QUTDIR", y), 0.0) * t / den
            pp[(m, "DELI", y)] = q.get((m, "DELIVS", y), 0.0)
            pp[(m, "DIRS", y)] = q.get((m, "DSTOTL", y), 0.0)
        for typ in ("QDEL", "QDIR", "QTOT", "DELI", "DIRS"):   # l. 88-89: BASM as the mean of the nonzero base years
            v = [pp.get((m, typ, y), 0.0) for y in bm]
            nz = [x for x in v if x]
            if nz:
                pp[(m, typ, "BASM")] = sum(v) / len(nz)
    for m in ms:
        reg_m = w.region == m
        qb = pp.get((m, "QTOT", "BASM"), 0.0)
        db, lb = pp.get((m, "QDEL", "BASM"), 0.0), pp.get((m, "DELI", "BASM"), 0.0)
        fac = db / lb if (db and lb) else 0.0              # l. 108-110
        if m in QDELFAC_ONE:
            fac = 1.0
        if m == "MT000000" and lb:
            fac = 1.0 + (db / lb - 1.0) / 2.0
        prcm_b = float(w("PRCM", "COMI").get((m, "BASM"), 0.0))
        hcom_b = float(w("HCOM", "COMI").get((m, "BASM"), 0.0))
        for y in exa:
            if (m, y) not in set(w.idx):
                continue
            qt = pp.get((m, "QTOT", y), 0.0)
            if qt and prcm_b:                              # l. 126-136
                f = fac if int(y) > lst_expost else 1.0
                v = prcm_b * (qt / qb) * f if qb else qt / 1000.0 * prcm_b / (hcom_b + prcm_b)
                w.put("QUTA", "COMI", _point(w, m, y, v), where=(reg_m & (w.t == y)))
            if qt and hcom_b:                              # l. 138-145
                v = hcom_b * qt / qb if qb else qt / 1000.0 * hcom_b / (hcom_b + prcm_b)
                w.put("QUTB", "COMI", _point(w, m, y, v), where=(reg_m & (w.t == y)))
    # l. 150-151: BASM of the quotas as the mean of the nonzero base years; l. 154: QUTS = QUTA + QUTB ex ante
    inbm = w.t.isin(bm)
    for c in ("QUTS", "QUTA", "QUTB"):
        v = w(c, "COMI")
        nz = (v != 0) & inbm & w.region.isin(ms)
        s = v.where(nz, 0.0).groupby(level="region").sum()
        n = nz.groupby(level="region").sum()
        mean = pd.Series(w.region.map((s / n.where(n != 0, 1.0)).where(n != 0, 0.0)).fillna(0.0).values, index=w.idx)
        has = pd.Series(w.region.map(n).fillna(0).values, index=w.idx) != 0
        w.put(c, "COMI", mean, where=w.region.isin(ms) & (w.t == "BASM") & has)
    in_exa = w.t.isin(exa) & w.region.isin(ms)
    w.put("QUTS", "COMI", w("QUTA", "COMI") + w("QUTB", "COMI"), where=in_exa)
    # captrd_policy.gms l. 28: no milk quotas after %mlkQutExpiry%
    late = in_exa & (_year(w.t) > expiry)
    for c in ("QUTS", "QUTA", "QUTB"):
        w.drop(c, "COMI", late)


def _point(w: Wide, m: str, y: str, v: float) -> pd.Series:
    return pd.Series(np.where((w.region == m) & (w.t == y), v, 0.0), index=w.idx)


def sugar_quotas(w: Wide, sets: CaptrdSets, dat: Dict[str, pd.DataFrame], years: Iterable[int],
                 aglink: str, map_rrt_eu: Set[tuple], expost_mode: bool = False) -> None:
    """sugar/load_quotas.gms and policy/reformsugarquotas.gms (%workStep% not "Build database"; %expost% off unless
    expost_mode): p_data(MSALL, quotas, "SUGA", years)."""
    ys = [int(y) for y in years]
    sq = dat["p_squotas"]
    q: Dict[tuple, float] = {(r, c.upper(), int(y)): v for r, c, y, v in zip(sq.region, sq.quota, sq.year, sq.value)}
    regs = sorted({k[0] for k in q})
    qts = ["QUTA", "QUTB", "QUTS"]
    # load_quotas.gms l. 39: the years before 1999 take 1999's
    for r in regs:
        for c in qts:
            for y in ys:
                if y < 1999:
                    v = q.get((r, c, 1999), 0.0)
                    if v:
                        q[(r, c, y)] = v
                    else:
                        q.pop((r, c, y), None)
    # l. 41-43: a loop over SIMYY up to the last year (sequential): a missing year takes the year before's
    last = max(ys)
    for y in range(1941, last + 1):
        for r in regs:
            for c in qts:
                if not q.get((r, c, y), 0.0) and q.get((r, c, y - 1), 0.0):
                    q[(r, c, y)] = q[(r, c, y - 1)]
    for r in regs:                                         # l. 45: QUTS = QUTA + QUTB
        for y in ys:
            v = q.get((r, "QUTA", y), 0.0) + q.get((r, "QUTB", y), 0.0)
            q[(r, "QUTS", y)] = v
    # reformsugarquotas.gms l. 64-66 (SIMYY from 2006: B quota into A, B at 0.001; QUTS on the years of the run)
    for r in regs:
        for y in range(1940, 2101):
            if y >= 2006:
                a = q.get((r, "QUTA", y), 0.0) + q.get((r, "QUTB", y), 0.0)
                q[(r, "QUTA", y)] = a
                if a:
                    q[(r, "QUTB", y)] = 0.001
        for y in ys:
            q[(r, "QUTS", y)] = q.get((r, "QUTA", y), 0.0) + q.get((r, "QUTB", y), 0.0)
    ren = dat["p_ppsqrenounce"]
    bb = dat["p_ppsqcbuyback"]
    ren_d = {(r, int(y)): v for r, y, v in zip(ren.region, ren.year, ren.value)}
    bb_d = {(r, int(y)): v for r, y, v in zip(bb.region, bb.year, bb.value)}
    msall = sorted(sets.msall)
    new: Dict[tuple, float] = {}
    for y in ys:                                           # l. 68-77: a loop over the years (renunciation cumulated)
        for r in msall:
            qs = q.get((r, "QUTS", y), 0.0)
            if not qs:
                continue
            renounce = sum(v for (rr, yy), v in ren_d.items() if rr == r and yy <= y)
            buyback = sum(v for (rr, yy), v in bb_d.items() if rr == r and yy <= y)
            withdraw = 0.0                                 # p_PPSQWithdraw: no records
            for c in qts:
                new[(r, c, y)] = max(0.0001, q.get((r, c, y), 0.0) + (buyback - renounce - withdraw)
                                     * q.get((r, c, y), 0.0) / qs)
    # l. 80-83 (%workStep% not "Build database"): quotas of at most 1 near zero for EU members, else none
    for r in msall:
        for c in qts:
            for y in ys:
                v = new.get((r, c, y), 0.0)
                if v <= 1:
                    new[(r, c, y)] = 1e-6 if ("EU", r, str(y)) in map_rrt_eu else 0.0
    # l. 85-90: no sugar quotas from 2017 under an Aglink version without them
    if not expost_mode and aglink in sets.nosugquotaaglinkversion:
        for k in list(new):
            if k[2] >= 2017:
                new[k] = 0.0
    # write p_data(MSALL, quotas, "SUGA", years): every year of the run is assigned (a zero deletes)
    here = set(w.region)
    for c in qts:
        vals = {(r, str(y)): v for (r, cc, y), v in new.items() if cc == c and r in here}
        v = pd.Series([vals.get(k, 0.0) for k in w.idx], index=w.idx)
        w.put(c, "SUGA", v, where=w.region.isin(set(msall)) & w.t.isin(set(map(str, ys))))


def sugar_beet(w: Wide, sets: CaptrdSets, ms: Iterable[str], years: Iterable[int], exantet: Iterable[int]) -> None:
    """captrd_policy.gms l. 61-108."""
    ms = list(ms)
    ys = set(_years(years))
    ext = set(_years(exantet))
    # l. 61: near-zero sugar quotas in the ex-ante years without data for the countries not to grow beet
    for c in sorted(sets.quotas):
        w.put(c, "SUGA", pd.Series(1e-6, index=w.idx),
              where=w.region.isin(MS_NO_SUGB) & w.t.isin(ext) & (w(c, "SUGA") == 0))
    # l. 63-67: QUTS of SUGB from SUGA (the base year's ratio, else the sugar yield PRCY)
    is_ms = w.region.isin(ms)
    t_y = w.t.isin(ys)
    sb = _region_value(w, "QUTS", "SUGB", "BASM")
    sa = _region_value(w, "QUTS", "SUGA", "BASM")
    py = _region_value(w, "PRCY", "SUGA", "BASM")
    qa = w("QUTS", "SUGA")
    new = (qa * sb / sa.where(sa != 0, 1.0)).where(sa != 0, 0.0)
    new = new.where(sa != 0, (qa / py.where(py != 0, 1.0)).where(py != 0, 0.0))
    w.put("QUTS", "SUGB", new, where=is_ms & t_y & ((sa != 0) | (py != 0)))
    # l. 69-93: the NUTS 2 regions' beet quotas, by their base quotas or else their base beet production
    cur = w("QUTS", "SUGB").copy()
    grb = w("GROF", "SUGB")
    for m in ms:
        mv = cur[(w.region == m).values]
        if not (mv[mv.index.get_level_values("t").isin(ys)] != 0).any():
            continue
        runr = {r for a, r in sets.map_rr if a == m and r in sets.srnuts2 and r != m}
        if not runr:
            continue
        mb = float(cur.get((m, "BASM"), 0.0))
        rb = {r: float(cur.get((r, "BASM"), 0.0)) for r in runr}
        srb = sum(rb.values())
        mg = float(grb.get((m, "BASM"), 0.0))
        for y in sorted(ys):
            my = float(cur.get((m, y), 0.0))
            if not my:
                continue
            for r in runr:
                if (r, y) not in cur.index:
                    continue
                if mb and rb[r]:
                    cur[(r, y)] = rb[r] / srb * my
                elif not rb[r] and mg:
                    cur[(r, y)] = my * float(grb.get((r, "BASM"), 0.0)) / mg
    w.put("QUTS", "SUGB", cur, where=t_y)


def set_aside(w: Wide, sets: CaptrdSets, ms: Iterable[str], dat: Dict[str, pd.DataFrame], exante: Iterable[int],
              years_cur: Iterable[int], base_year: int) -> None:
    """captrd_policy.gms l. 158-202. The EU-15 rate (CurEUWestAgg, EU015000) is 10 in the base year and in the
    ex-ante years, 0 after 2007; the regions' ex-ante rates follow it with their small producers' shares; the EU-12's
    and Croatia's are their aggregate's, 0 after 2007 and 2012; the set-aside activities carry no rate."""
    ms = list(ms)
    exa = [int(y) for y in exante]
    sp = dat["p_smallprodshare"]
    share = {(str(y), r): v for y, r, v in zip(sp.year, sp.region, sp.value)}
    for y in exa:                                          # l. 172
        for r in ms:
            if not share.get((str(y), r)):
                share[(str(y), r)] = share.get(("2009", r), 0.0)
    eu15 = {str(base_year): 10.0}
    for y in exa:
        eu15[str(y)] = 0.0 if y > 2007 else 10.0
    eu12 = {str(y): 0.0 for y in exa}
    by = str(base_year)
    t_exa = w.t.isin(set(map(str, exa)))
    members = {}
    for a, r in sets.map_rr:
        if a in ms:
            members.setdefault(r, set()).add(a)
    for c in sorted(sets.grcu):
        cur = w(c, "SETR")
        new = cur.copy()
        for (reg, t), v0 in cur.items():
            if t not in eu15 or t == by or not eu15.get(t) or reg not in members:
                continue
            base = float(cur.get((reg, "BASM"), 0.0))
            if not base:
                continue
            mss = members[reg]
            num = eu15[t] * sum(1.0 - min(share.get((by, m), 0.0), share.get((t, m), 0.0)) for m in mss)
            num *= sum(float(cur.get((m, "BASM"), 0.0)) for m in mss)
            den = eu15[by] * sum(1.0 - share.get((by, m), 0.0) for m in mss)
            new[(reg, t)] = min(eu15[t], num / den) if den else eu15[t]
        w.put(c, "SETR", new, where=t_exa)
        # l. 187-189: the EU-12 members and their regions, Croatia after 2012
        eu12m = {r for a, r in sets.map_rr if a == "EU012000"} & set(ms)
        sub = w.region.isin(eu12m) | w.region.map(lambda r: bool(members.get(r, set()) & eu12m)).astype(bool)
        w.put(c, "SETR", pd.Series(0.0, index=w.idx), where=t_exa & sub)
        w.put(c, "SETR", pd.Series(0.0, index=w.idx), where=t_exa & (w.region == "HR000000") & (_year(w.t) > 2012))
    yc = w.t.isin(set(map(str, years_cur)))
    for c in sorted(sets.rset | {"VSET", "NONF", "OSET"}):  # l. 195-200
        w.drop(c, "SETR", yc)


def _region_value(w: Wide, c: str, r: str, t: str) -> pd.Series:
    v = w(c, r)
    m = {reg: float(v.get((reg, t), 0.0)) for reg in set(w.region)}
    return pd.Series(w.region.map(m).fillna(0.0).values, index=w.idx)


def apply(p: pd.DataFrame, sets: CaptrdSets, ms: Iterable[str], years: Iterable[int], exante: Iterable[int],
          exantet: Iterable[int], years_cur: Iterable[int], basyrsm: Iterable[int], lst_expost: int, base_year: int,
          aglink: str, dat: Optional[Dict[str, pd.DataFrame]] = None, expiry: int = 2009) -> pd.DataFrame:
    """captrd_policy.gms on p_data (one country's file: the country and its NUTS 2 regions). years: YEARS of the run
    (to the last simulation year); the index gets every year of the run for the country."""
    dat = read_policy_dat() if dat is None else dat
    ms = [m for m in ms if m in set(p["region"])]
    have = set(zip(p["region"], p["t"]))
    extra = [(r, str(int(y))) for r in sorted(set(p["region"])) for y in years if (r, str(int(y))) not in have]
    w = Wide(p)
    if extra:
        from capri_mod.pipeline.captrd.coco import _extend
        w = _extend(w, extra)
    rrt = {(a, r, y) for a, r, y in sets.map_rrt if a == "EU"}
    milk_quotas(w, ms, dat, years, exante, basyrsm, lst_expost, expiry)
    sugar_quotas(w, sets, dat, years, aglink, rrt)
    sugar_beet(w, sets, ms, years, exantet)
    set_aside(w, sets, ms, dat, exante, years_cur, base_year)
    return w.long()

"""CAPTRD's supports for the short run from Eurostat's recent production statistics (captrd/agriprod_supports.gms,
included by captrd/expert_support.gms l. 771; CAPRI star 3.0).

In GAMS's order (line numbers of agriprod_supports.gms):
  l. 211-246  p_AgriProd (dat/coco/Agri_Prod.gdx) of the years %BaseYear%-1 to 2020, if an ex-ante year is before 2020;
              Sweden's sheep and goats from 2018 removed; 2018, 2019, 2020 filled with the year before
  l. 248-306  derived series: other cattle, fattening pigs, sheep and goats, Malta's milk, cow milk, milk yields
  l. 331-386  three-year means around the base years (facyr: %BaseYear%, 2018), and the factors fac2018, fac2019,
              fac2020 (the year's data over the base mean); an activity without its own takes its group's (agriprod1, else
              agriprod2)
  l. 396-499  for 2020 (an ex-ante year without data, ExAnteT): the herds and levels of the target animal activities
              (BASM x the 2020 factor on the %BaseYear% mean, else p_data of 2018 x the factor on 2018), trust 9.02
              (3.02 for values up to 1); bounds for days and daily growth and meat yields of the fattening activities,
              1% bounds for the dairy herds; the dairy yields and cow milk production
  l. 505-611  the same for 2019 and l. 614-697 for 2018 with the crop levels, each only if that year is an ExAnteT year
              (not in the reference run: 2019 is no simulation year, 2018 has COCO's data)
  l. 701-704  where a 2020 support exists: 2017 at BASM, 2016 at p_data (the file's literal years: %BaseYear% and the
              year before here, the same in the reference run)
The PercentChange supports of the earlier sources this file deletes are returned as positions (Result.no_percent).

A statement whose right side reads the parameter it assigns takes the values from before the statement (the means
around the base years, l. 333-337), as GAMS does (found in the biofuel trends, biofuel_trends.py).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: l. 290-292: Malta's milk series of 2017 shifted by one position
MT_SHIFT_YEAR = 2017
#: l. 304-305: yields in kg from 1000 t and 1000 heads
KG_PER_T = 1000.0
#: l. 333-337: three years around each base year
MEAN_YEARS = 3
#: the last year of p_AgriProd's nowcasts (l. 211, 224)
LAST_NOWCAST = 2020
#: Sweden's sheep and goats removed from 2018 (l. 233)
SE_SHGT_FROM = 2018
#: l. 236-246: the years filled with the year before
FILL_YEARS = [2018, 2019, 2020]
#: l. 407-411, 468-474: the fallback base year (p_data of 2018 x the factor on 2018)
NOWCAST_BASE = 2018
#: l. 413-418: trust levels, by the value's size
TRUST_HIGH = 9.02
TRUST_LOW = 3.02
TRUST_LIMIT = 1.0
#: l. 423-443: bounds of days and daily growth (x the last ex-post year) and of meat yields
DAYS_LO = 0.7
DAYS_UP = 1.5
#: l. 446-454: the dairy herds' bounds
HERD_LO = 0.99
HERD_UP = 1.01

K4 = Tuple[str, str, str, int]


def _csv(path: Path) -> List[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


@dataclass
class Inputs:
    sets: Dict[str, List[Tuple[str, ...]]]
    agriprod: Dict[Tuple[str, str, str, int], float]
    reqfcnlim: Dict[Tuple[str, str, str], float]

    def one(self, name: str) -> List[str]:
        return [x[0] for x in self.sets[name]]


def read_inputs(sets_dir: Path, dat_dir: Path) -> Inputs:
    sets = {}
    for p in sorted((sets_dir / "agriprod").glob("*.csv")):
        rows = _csv(p)
        cols = [c for c in rows[0] if c.startswith("d")]
        sets[p.stem] = [tuple(r[c].upper() for c in cols) for r in rows]
    ap = {(r["ms_agriprod"], r["agriprod"], r["item"], int(r["year"])): float(r["value"])
          for r in _csv(dat_dir / "agriprod_p_agriprod.csv")}
    lim = {(r["act"].upper(), r["row"].upper(), r["bound"].lower()): float(r["value"])
           for r in _csv(dat_dir / "agriprod_p_reqfcnlim.csv")}
    return Inputs(sets, ap, lim)


@dataclass
class Result:
    absolute: Dict[K4, float] = field(default_factory=dict)        # assignments; 0 deletes an earlier stage's value
    trust: Dict[K4, float] = field(default_factory=dict)
    bounds: Dict[K4, Tuple[Optional[float], Optional[float]]] = field(default_factory=dict)   # expertLo, expertUp
    #: the positions whose PercentChange supports of the earlier sources (DG AGRI, national experts) this file deletes
    #: (l. 420-421, 485-487: Eurostat preferred)
    no_percent: Set[K4] = field(default_factory=set)


def supports(I: Inputs, *, runr: Sequence[str], s_colsest: Iterable[str], s_rowsest: Iterable[str],
             exante: Sequence[int],
             exantet: Sequence[int], base_year: int, lst_expostt: int, basm: Dict[Tuple[str, str, str], float],
             pdata: Dict[K4, float], bast: Dict[Tuple[str, str, str], float], dcow: Iterable[str],
             meat_act: Iterable[str], pact_to_y: Iterable[Tuple[str, str]], prior: Dict[K4, float]) -> Result:
    """The supports. basm: BASM per (region, col, row); pdata: p_data of the years; bast: p_data's BAST; dcow: the
    dairy cow activities (P_T_ActAgg(., "DCOW")); meat_act: meatAct; prior: p_ExpertSupprt's Absolute before this file
    (the earlier sources), for the "not yet assigned" tests and l. 701-704."""
    out = Result()
    if not any(y < LAST_NOWCAST for y in exante):                          # l. 224
        return out
    one = I.one
    yr = list(range(base_year - 1, LAST_NOWCAST + 1))                      # yrAgriProd
    facyr = [int(x) for x in one("facyr")]
    msag = one("msagriprod")
    aps = one("agriprod")
    items = one("itemagriprod")
    P: Dict[Tuple[str, str, str, int], float] = {}
    for (m, a, i, y), v in I.agriprod.items():
        if y in yr or y in facyr or any(abs(y - f) <= 1 for f in facyr):
            P[(m, a, i, y)] = v

    def g(*k):
        return P.get(k, 0.0)

    def put(k, v):
        if v:
            P[k] = v
        else:
            P.pop(k, None)
    for a in one("shepgoat"):                                              # l. 233
        for i in items:
            for y in yr:
                if y >= SE_SHGT_FROM:
                    put(("SE000", a, i, y), 0.0)
    for y in FILL_YEARS:                                                   # l. 236-246
        for k in [k for k in list(P) if k[3] == y - 1]:
            m, a, i, _ = k
            if not g(m, a, i, y):
                put((m, a, i, y), g(m, a, i, y - 1))
    for m in msag:                                                         # l. 248-285
        for y in yr:
            c, d, cv = g(m, "CATA", "SUR4", y), g(m, "DCOW", "SUR4", y), g(m, "CALV", "SUR4", y)
            put((m, "ADNONDAI", "SUR4", y), (c - d - cv) if (c and d and cv) else 0.0)
        for y in yr:
            a, b = g(m, "PIGL20", "SUR4", y), g(m, "PIGF50", "SUR4", y)
            put((m, "PIGF", "SUR4", y), (a + b) if (a and b) else 0.0)
        for y in yr:
            if not g(m, "PIGF", "SUR4", y):
                ps, p0, bo, so = (g(m, x, "SUR4", y) for x in ("PIGS", "PIGL00", "BOAR", "SOWS"))
                put((m, "PIGF", "SUR4", y), (ps - p0 - bo - so) if (ps and p0 and so) else 0.0)
        for y in yr:
            a, b = g(m, "SHEPS", "SUR4", y), g(m, "GOATS", "SUR4", y)
            put((m, "SHGT", "SUR4", y), (a + b) if (a and b) else 0.0)
        for y in yr:
            a, b = g(m, "SHEP", "SUR4", y), g(m, "GOAT", "SUR4", y)
            put((m, "SHGM", "SUR4", y), (a + b) if (a and b) else 0.0)
    put(("MT000", "GROF", "GMLK", MT_SHIFT_YEAR), g("MT000", "GROF", "EMLK", MT_SHIFT_YEAR))    # l. 290-292
    put(("MT000", "GROF", "EMLK", MT_SHIFT_YEAR), g("MT000", "GROF", "CMLK", MT_SHIFT_YEAR))
    put(("MT000", "GROF", "CMLK", MT_SHIFT_YEAR), g("MT000", "GROF", "RMLK", MT_SHIFT_YEAR))
    for m in msag:                                                         # l. 294-306
        any_e = any(g(m, "GROF", "EMLK", y) for y in yr)
        any_g = any(g(m, "GROF", "GMLK", y) for y in yr)
        for y in yr:
            if (not g(m, "GROF", "CMLK", y) and g(m, "GROF", "RMLK", y)
                    and (g(m, "GROF", "EMLK", y) or not any_e) and (g(m, "GROF", "GMLK", y) or not any_g)):
                put((m, "GROF", "CMLK", y), g(m, "GROF", "RMLK", y) - g(m, "GROF", "EMLK", y) - g(m, "GROF", "GMLK", y))
        for y in yr:
            if g(m, "DCOW", "SUR4", y):
                put((m, "YILD", "CMLK", y), g(m, "GROF", "CMLK", y) / g(m, "DCOW", "SUR4", y) * KG_PER_T)
    snap = dict(P)                                                         # l. 333-337, on the values before it
    for m in msag:
        for a in aps:
            for i in items:
                for f in facyr:
                    win = [y for y in yr if abs(y - f) <= 1]
                    if sum(1 for y in win if snap.get((m, a, i, y), 0.0)) == MEAN_YEARS:
                        put((m, a, i, f), sum(snap.get((m, a, i, y), 0.0) for y in win) / MEAN_YEARS)
    a2i: Dict[str, List[str]] = {}
    for a, i in I.sets["agriprod_to_item"]:
        a2i.setdefault(a, []).append(i)
    for fy in sorted(FILL_YEARS, reverse=True):                            # l. 341-364
        fac = f"FAC{fy}"
        for m in msag:
            for a in aps:
                for f in facyr:
                    den = sum(g(m, a, i, f) for i in a2i.get(a, []))
                    if den:
                        put((m, a, fac, f), sum(g(m, a, i, fy) for i in a2i.get(a, [])) / den)
    c2a: Dict[str, List[str]] = {}
    for c, a in I.sets["cols_to_agriprod"]:
        c2a.setdefault(c, []).append(a)
    g1, g2 = set(one("agriprod1")), set(one("agriprod2"))
    for fac in [f"FAC{y}" for y in sorted(FILL_YEARS, reverse=True)]:      # l. 368-386
        for grp in (g1, g2):
            for m in msag:
                for c in one("agriprodaact"):
                    for f in facyr:
                        if not g(m, c, fac, f):
                            put((m, c, fac, f), sum(g(m, a, fac, f) for a in c2a.get(c, []) if a in grp))
    agmap = I.sets["msagriprod_map"]
    of_r: Dict[str, List[str]] = {}
    for a, r in agmap:
        of_r.setdefault(r, []).append(a)
    E = dict(prior)
    pd_ = lambda r, c, w, y: float(pdata.get((r, c, w, y), 0.0))         # noqa: E731

    def assign(k, v):
        out.absolute[k] = v
        if v:
            E[k] = v
        else:
            E.pop(k, None)
    dcow = set(dcow)
    hl = ["HERD", "LEVL"]
    for y in [y for y in sorted(FILL_YEARS, reverse=True) if y in exantet and y != NOWCAST_BASE]:   # l. 396-611
        fac = f"FAC{y}"
        for r in runr:
            for c in one("agriprodaact"):
                for w in hl:
                    if basm.get((r, c, w), 0.0):
                        assign((r, c, w, y), sum(g(a, c, fac, base_year) for a in of_r.get(r, [])) * basm[(r, c, w)])
                for w in hl:
                    if pd_(r, c, w, NOWCAST_BASE) and not E.get((r, c, w, y), 0.0):
                        assign((r, c, w, y), sum(g(a, c, fac, NOWCAST_BASE) for a in of_r.get(r, []))
                               * pd_(r, c, w, NOWCAST_BASE))
                for w in hl:
                    v = E.get((r, c, w, y), 0.0)
                    if v:
                        out.trust[(r, c, w, y)] = TRUST_HIGH if v > TRUST_LIMIT else TRUST_LOW
                        out.no_percent.add((r, c, w, y))
        _bounds(out, I, E, runr, y, lst_expostt, pd_, bast, meat_act, pact_to_y, dcow, hl)
        cs = [c for c in s_colsest if c in dcow or c == "GROF"]
        for r in runr:
            for c in cs:
                src = "YILD" if c in dcow else "GROF"
                if basm.get((r, c, "COMI"), 0.0):
                    assign((r, c, "COMI", y), sum(g(a, src, fac, base_year) for a in of_r.get(r, []))
                           * basm[(r, c, "COMI")])
                if pd_(r, c, "COMI", NOWCAST_BASE) and not E.get((r, c, "COMI", y), 0.0):
                    assign((r, c, "COMI", y), sum(g(a, src, fac, NOWCAST_BASE) for a in of_r.get(r, []))
                           * pd_(r, c, "COMI", NOWCAST_BASE))
                v = E.get((r, c, "COMI", y), 0.0)
                if v:
                    out.trust[(r, c, "COMI", y)] = TRUST_HIGH if v > TRUST_LIMIT else TRUST_LOW
                    out.no_percent.add((r, c, "COMI", y))
            if E.get((r, "GROF", "COMI", y), 0.0):
                v = E[(r, "GROF", "COMI", y)]
                out.bounds[(r, "GROF", "COMI", y)] = (v * HERD_LO, v * HERD_UP)
    if NOWCAST_BASE in exantet:
        raise NotImplementedError("agriprod supports for 2018 (l. 614-697) are not ported: 2018 is no ExAnteT year in "
                                  "the reference run")
    cols_est, rows_est = set(s_colsest), set(s_rowsest)
    for (r, c, w, y), v in list(E.items()):                                # l. 701-704
        if y == LAST_NOWCAST and v and r in set(runr) and c in cols_est and w in rows_est:
            assign((r, c, w, base_year), basm.get((r, c, w), 0.0))
            assign((r, c, w, base_year - 1), pd_(r, c, w, base_year - 1))
    return out


def _bounds(out, I, E, runr, y, lst, pd_, bast, meat_act, pact_to_y, dcow, hl):
    """l. 423-454: the fattening activities' days, daily growth and meat yields; the dairy herds' 1% bounds."""
    meat_of: Dict[str, List[str]] = {}
    for a, m in pact_to_y:
        meat_of.setdefault(a, []).append(m)
    for r in runr:
        for a in meat_act:
            if not E.get((r, a, "HERD", y), 0.0):
                continue
            for w in ("DAYS", "DAILY"):
                lo = max(DAYS_LO * pd_(r, a, w, lst), I.reqfcnlim.get((a, w, "lo"), 0.0))
                up = min(DAYS_UP * pd_(r, a, w, lst), I.reqfcnlim.get((a, w, "up"), 0.0))
                out.bounds[(r, a, w, y)] = (lo, up)
            for m in meat_of.get(a, []):
                p, b = pd_(r, a, m, lst), bast.get((r, a, m), 0.0)
                if p and b:
                    out.bounds[(r, a, m, y)] = (DAYS_LO * min(p, b), DAYS_UP * max(p, b))
        for c in dcow:
            for w in hl:
                v = E.get((r, c, w, y), 0.0)
                if v:
                    out.bounds[(r, c, w, y)] = (v * HERD_LO, v * HERD_UP)

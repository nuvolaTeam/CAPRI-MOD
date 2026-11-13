"""CAPTRD's expert supports from DG AGRI's dairy data (captrd/expert_support.gms l. 365-760; CAPRI star 3.0), active
with %useAgriInfo% on, as in the reference run: its long-run selection globiom_eu_bright_s0_2023 switches it on
(l. 361). Also the step of define_stats_and_supports.gms (l. 510-519) that turns the share of direct sales into human
consumption's expert support HCOM.COMI.

In GAMS's order (line numbers of expert_support.gms):
  l. 372-431  up to %lst_daitar% (2020), for runr (the member states and BL400000) and the years exanteT1 (ExAnteT,
              2015, 2020): the dairy cows' levels and herds, milk production GROF, DOMM and the value EAAG, deliveries
              PRCM and the cows' yields at their BASM of %lastSimulationYear% x the change of DG AGRI's table
              (p_nrCows, p_cowMilkProd, p_milkDeliveries, p_dairyCowYield) from its 2016-2018 mean, summed over the
              table's countries mapped to the region (ms_agri_TO_MS); EAAG also x the milk price's support over its BASM;
              Poland's yields first recomputed from production and cows
  l. 434-436  expertdairy_map: the dairy cow activities' LEVL, HERD, COMI; GROF, DOMM, EAAG, PRCM, EXPE of COMI
  l. 442-545  growth rates beyond 2020 (if the last ex-ante year is after 2020): (1) the 2015-2020 growth; (2) shifted
              by the yield's distance from 8,000 kg (+0.01 x for yields, -0.01 x for levels and herds, not in IR, MT);
              (3) for yields averaged 70:30 with the recent growth p_recentMlkYld(region, "Y"); (3a) the EU
              parts' (CurEUSubAgg) mean of the member states' rates, weighted by BASM's levels; Aglink's 2015-%lst_dgagri%
              growth for the member states and EU parts (DGAgri); the regions with one (the UK, Norway, Turkey) take it;
              the EU countries' rates x Aglink's growth of their EU part over the parts' mean; the EU parts' Aglink
              levels, yields and milk production stored as checking output (CAPTRD's Expert holds them)
  l. 547-565  p_maxmin, the corridor's adjustment (Ireland, BL400000, the EU13 and EU14 member states, Denmark)
  l. 567-597  the dampened extrapolation after 2020, a logistic between min and max of the 2020 value
              (p_exTrapMinMax 0.75/1.25), min lowered by 0.1 and the span widened by 0.2 for the dairy cow activities,
              both narrowed by p_maxmin
  l. 604-609  milk production recomputed from the extrapolated yields and levels
  l. 615-664  checking output: the ex-post years from p_data, the A_EU_WEST/EAST aggregates for YearsCur
  l. 667-683  DOMM and PRCM of raw milk changing as milk production; MAPR.MILK = PRCM.COMI + PRCM.SGMI's support
  l. 685-710  trust levels 8, 3 for EAAG, MAPR, PRCM, DOMM, x 0.99 (1.01 for milk production in 15 countries) a year
              after 2020; EXPE.COMI 0.1
  l. 712-757  the share of direct sales HCOM/GROF of raw milk ("share" of support1): the EU aggregates' from DGAgri,
              the member states' ex-post from p_data, the EU member states' ex-ante as their EU aggregates' change from
              the last ex-post year and kept after %lst_dgagri%, the others' (MSnoEU28) from the trend supports, not
              allowed to rise from one simulation year to the next

As coded, kept: the EU parts' mean growth rate (3a) sums over every member state of every CurEuropAgg (EU014000,
EU013000 and EU27yr19), the same for both parts; the member states' ex-ante share sums the changes of every
CurEuropAgg a member state belongs to.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: %lst_daitar% (captrd.gms l. 261): the last year of DG AGRI's dairy data
LST_DAITAR = 2020
#: l. 380, 442-449: the first year of the growth rate (1)
GRATE_FROM = 2015
#: l. 376: years around the base year for the tables' base (yrbas)
YRBAS_HALF = 1
#: l. 424, 609: yields in kg from 1000 t and 1000 heads; milk production in 1000 t from kg and 1000 heads
KG_PER_T = 1000.0
#: l. 439-440: p_exTrapMinMax
EXTRAP_MIN = 0.75
EXTRAP_MAX = 2 - EXTRAP_MIN
#: l. 567-597: the dairy cow activities' corridor: min lowered and span widened
DCOW_MIN_SHIFT = 0.1
DCOW_SPAN_SHIFT = 0.2
#: l. 444-445, 458, 482, 669-670: smallest value a growth rate's end points need
MIN_ABS = 1e-4
#: l. 457-466: reference yield and the growth rate's shift per relative distance from it
REF_YIELD = 8000.0
YIELD_SHIFT = 0.01
#: l. 485-487: weight of the recent yield growth
RECENT_WEIGHT = 0.3
#: l. 551-565: p_maxmin
MAXMIN_IR = 0.2
MAXMIN_BL4 = -0.2
MAXMIN_EU13_COMI = -0.1
MAXMIN_EU13_LEVL = 0.1
MAXMIN_EU14_COMI = 0.1
MAXMIN_EU14_LEVL = -0.2
MAXMIN_DK_LEVL = 0.1
#: l. 689-710: trust levels
TRUST_DAIRY = 8.0
TRUST_LESS = 5.0
TRUST_DECAY = 0.99
TRUST_GROW = 0.02
TRUST_EXPE = 0.1
#: define_stats_and_supports.gms l. 517-519: HCOM.COMI's trust, and the share it needs
TRUST_HCOM = 5.0
TRUST_HCOM_LOW = 1.0
SHARE_MIN = 1e-4
#: l. 691-705: the regions whose milk production's trust grows after 2020
STABLE = ["HR000000", "IR000000", "RO000000", "LT000000", "LV000000", "HU000000", "SI000000", "SK000000", "IT000000",
          "MT000000", "PT000000", "FR000000", "SE000000", "FI000000", "TUR"]
TABLES = ["p_nrcows", "p_cowmilkprod", "p_milkdeliveries", "p_dairycowyield"]

Key = Tuple[str, str, str, str]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _set(d, k, v):
    if v:
        d[k] = v
    else:
        d.pop(k, None)


def dairy(*, runr: Sequence[str], ms: Sequence[str], ms_no_eu28: Iterable[str], dcow: Sequence[str], base_year: int,
          exante_t: Sequence[int], expost: Sequence[int], expostt: Sequence[int], years_cur: Sequence[int],
          sim_years: Sequence[int], fst_exante: int, lst_exante: int, lst_dgagri: int,
          tables: Dict[str, Dict[Tuple[str, int], float]], ms_agri_to_ms: Iterable[Tuple[str, str]],
          recent: Dict[str, float], basm: Dict[Tuple[str, str, str], float], support: Dict[Key, float],
          pdata: Dict[Key, float], dgagri: Dict[Key, float], map_rr: Iterable[Tuple[str, str]],
          europ_aggs: Sequence[str], sub_aggs: Sequence[str], eu13: str, eu14: str, west: str, east: str,
          trace: Optional[dict] = None):
    """(p_ExpertSupprt {(region, col, row, year): (Absolute, TrustLevl)}, support1's share {(region, year): share}).

    tables: DG AGRI's dairy tables {name in TABLES: {(ms_agri, year): value}}; recent: p_recentMlkYld(region, "Y");
    basm: p_result(..., %lastSimulationYear%, "BASM") per (region, col, row); support: p_result(..., "support");
    pdata: p_data; dgagri: p_result(..., "DGAgri") (Aglink's, as the scaling leaves it); map_rr: (aggregate, member),
    with its diagonal; europ_aggs, sub_aggs: CurEuropAgg, CurEUSubAgg; eu13, eu14: the EU parts p_maxmin names; west,
    east: the A_EU_WEST/EAST aggregates. Years are str in the keys of support, pdata and dgagri. trace, if given, receives
    the growth rates: grate (as extrapolated), eu_grate (the EU parts' mean) and dg_grate (Aglink's)."""
    E: Dict[Key, List[float]] = {}
    dcow = list(dcow)
    runr = list(runr)
    mrr = set(map_rr)
    ms_set = set(ms)

    def members(agg):
        return [m for m in ms if (agg, m) in mrr]
    m2a = {m: [a for a in europ_aggs if (a, m) in mrr] for m in ms}         # MS_TO_RMSAGG(ms, CurEuropAgg)

    def ab(r, c, w, y):
        return E.get((r, c, w, str(y)), [0.0, 0.0])[0]

    def put(r, c, w, y, v):
        k = (r, c, w, str(y))
        if v:
            E.setdefault(k, [0.0, 0.0])[0] = v
        elif k in E:
            E[k][0] = 0.0
    years_t1 = sorted(set(exante_t) | {GRATE_FROM, LST_DAITAR})              # l. 377-381
    yrbas = list(range(base_year - YRBAS_HALF, base_year + YRBAS_HALF + 1))
    tabs = {n: dict(tables[n]) for n in TABLES}
    for (a, y), c in tables["p_cowmilkprod"].items():                      # l. 424
        if a == "PL" and tabs["p_nrcows"].get((a, y), 0.0):
            tabs["p_dairycowyield"][(a, y)] = c / tabs["p_nrcows"][(a, y)] * KG_PER_T
    agri_of: Dict[str, List[str]] = {}
    for a, m in ms_agri_to_ms:
        agri_of.setdefault(m, []).append(a)
    bas_of = {n: {a: sum(t.get((a, y), 0.0) for y in yrbas) / len(yrbas) for a in {k[0] for k in t}}
              for n, t in tabs.items()}

    def change(n, r, y):
        return sum(tabs[n].get((a, y), 0.0) / bas_of[n][a] for a in agri_of.get(r, []) if bas_of[n].get(a, 0.0))
    early = [y for y in years_t1 if y <= LST_DAITAR]
    for r in runr:                                                          # l. 387-431
        for y in early:
            for c in dcow:
                for w in ("LEVL", "HERD"):
                    if basm.get((r, c, w), 0.0):
                        put(r, c, w, y, change("p_nrcows", r, y) * basm[(r, c, w)])
            for c in ("GROF", "DOMM", "EAAG"):
                if basm.get((r, c, "COMI"), 0.0):
                    put(r, c, "COMI", y, change("p_cowmilkprod", r, y) * basm[(r, c, "COMI")])
        for y in years_t1:
            if basm.get((r, "UVAG", "COMI"), 0.0) and ab(r, "EAAG", "COMI", y):
                s = support.get((r, "UVAG", "COMI", str(y)), 0.0) or support.get((r, "UVAG", "COMI", str(LST_DAITAR)), 0.0)
                put(r, "EAAG", "COMI", y, ab(r, "EAAG", "COMI", y) * s / basm[(r, "UVAG", "COMI")])
        for y in early:
            if basm.get((r, "PRCM", "COMI"), 0.0):
                put(r, "PRCM", "COMI", y, change("p_milkdeliveries", r, y) * basm[(r, "PRCM", "COMI")])
            for c in dcow:
                if basm.get((r, c, "COMI"), 0.0):
                    put(r, c, "COMI", y, change("p_dairycowyield", r, y) * basm[(r, c, "COMI")])
    dmap = [(c, w) for c in dcow for w in ("LEVL", "HERD", "COMI")] + [(c, "COMI") for c in
                                                                       ("GROF", "DOMM", "EAAG", "PRCM", "EXPE")]
    late = lst_exante > LST_DAITAR
    lc = [(c, w) for c in dcow for w in ("LEVL", "COMI")]
    grate: Dict[Tuple[str, str, str], float] = {}
    if late:
        for r in runr:                                                      # (1)
            for c, w in dmap:
                a0, a1 = ab(r, c, w, GRATE_FROM), ab(r, c, w, LST_DAITAR)
                if a0 > MIN_ABS and a1 > MIN_ABS:
                    grate[(r, c, w)] = (a1 / a0) ** (1 / (LST_DAITAR - GRATE_FROM)) - 1
        for r in runr:                                                      # (2)
            yld = 0.5 * sum(ab(r, c, "COMI", LST_DAITAR) for c in dcow)
            for c, w in dmap:
                if c in dcow and ab(r, c, w, LST_DAITAR) > MIN_ABS:
                    k = YIELD_SHIFT if w == "COMI" else (
                        -YIELD_SHIFT if r not in ("IR000000", "MT000000") else 0.0)
                    grate[(r, c, w)] = grate.get((r, c, w), 0.0) + (REF_YIELD - yld) / REF_YIELD * k
        for r in runr:                                                      # (3)
            for c in dcow:
                if ab(r, c, "COMI", LST_DAITAR) > MIN_ABS:
                    grate[(r, c, "COMI")] = (1 - RECENT_WEIGHT) * grate.get((r, c, "COMI"), 0.0) \
                        + RECENT_WEIGHT * recent.get(r, 0.0)
        pairs = [m for m in ms for _ in m2a[m]]                             # (3a)
        eu_g: Dict[Tuple[str, str, str], float] = {}
        for c, w in lc:
            den = sum(basm.get((m, c, "LEVL"), 0.0) for m in pairs)
            if den:
                v = sum(grate.get((m, c, w), 0.0) * basm.get((m, c, "LEVL"), 0.0) for m in pairs) / den
                for a in sub_aggs:
                    eu_g[(a, c, w)] = v
        dg_g: Dict[Tuple[str, str, str], float] = {}
        for r in list(ms) + list(sub_aggs):
            for c, w in lc:
                d0 = dgagri.get((r, c, w, str(GRATE_FROM)), 0.0)
                if d0:
                    dg_g[(r, c, w)] = (dgagri.get((r, c, w, str(lst_dgagri)), 0.0) / d0) \
                        ** (1 / (lst_dgagri - GRATE_FROM)) - 1
        for r in runr:
            for c, w in lc:
                if dg_g.get((r, c, w), 0.0):
                    grate[(r, c, w)] = dg_g[(r, c, w)]
        for r in runr:
            for c, w in lc:
                subs = [a for m in ms if (m, r) in mrr for a in m2a[m] if a in sub_aggs]
                if sum(eu_g.get((a, c, w), 0.0) for a in subs):
                    grate[(r, c, w)] = grate.get((r, c, w), 0.0) * sum(
                        dg_g.get((a, c, w), 0.0) / eu_g[(a, c, w)] for a in subs)
        for a in sub_aggs:
            for y in years_cur:
                for c, w in lc + [("GROF", "COMI")]:
                    put(a, c, w, y, dgagri.get((a, c, w, str(y)), 0.0))
    if trace is not None:
        trace["grate"] = grate
        trace["eu_grate"] = eu_g if late else {}
        trace["dg_grate"] = dg_g if late else {}
    maxmin: Dict[Tuple[str, str, str], float] = {}                          # (4), gpar l. 567-580
    for c, w in dmap:
        maxmin[("IR000000", c, w)] = MAXMIN_IR
        maxmin[("BL400000", c, w)] = MAXMIN_BL4
    for m in ms:
        for c, w in dmap:
            if (eu13, m) in mrr and w == "COMI":
                maxmin[(m, c, w)] = MAXMIN_EU13_COMI if m != "EE000000" else 0.0
            if (eu13, m) in mrr and w == "LEVL":
                maxmin[(m, c, w)] = MAXMIN_EU13_LEVL
            if (eu14, m) in mrr and w == "COMI":
                maxmin[(m, c, w)] = MAXMIN_EU14_COMI
            if (eu14, m) in mrr and w == "LEVL":
                maxmin[(m, c, w)] = MAXMIN_EU14_LEVL
            if m == "DK000000" and w == "LEVL":
                maxmin[(m, c, w)] = MAXMIN_DK_LEVL
    after = [y for y in exante_t if y > LST_DAITAR]
    for (r, c, w), g in list(grate.items()):                                # (5)
        if r not in runr or not g:
            continue
        d = c in dcow
        mm = maxmin.get((r, c, w), 0.0)
        lo = 1 - EXTRAP_MIN + (DCOW_MIN_SHIFT if d else 0.0) - mm
        span = EXTRAP_MAX - EXTRAP_MIN + (DCOW_SPAN_SHIFT if d else 0.0) - 2 * mm
        gpar = g / lo / (1 - lo / span)
        base = ab(r, c, w, LST_DAITAR)
        for y in after:
            f = (EXTRAP_MIN - (DCOW_MIN_SHIFT if d else 0.0) + mm + span * _sigmoid(gpar * (y - LST_DAITAR))) \
                if gpar else 1.0
            put(r, c, w, y, base * f)
    for r in runr:                                                          # l. 604-609
        for y in after:
            if sum(ab(r, c, "COMI", y) for c in dcow):
                put(r, "GROF", "COMI", y, sum(ab(r, c, "COMI", y) * ab(r, c, "LEVL", y) for c in dcow) / KG_PER_T)
    if late:                                                                # l. 615-664
        for r in runr:
            for y in expost:
                put(r, "GROF", "COMI", y, pdata.get((r, "GROF", "COMI", str(y)), 0.0))
                for c, w in lc:
                    put(r, c, w, y, pdata.get((r, c, w, str(y)), 0.0))
        for agg in (west, east):
            mem = members(agg)
            for y in years_cur:
                for c in dcow:
                    lv = sum(ab(m, c, "LEVL", y) for m in mem)
                    if lv:
                        put(agg, c, "COMI", y, sum(ab(m, c, "COMI", y) * ab(m, c, "LEVL", y) for m in mem) / lv)
                for c in dcow:
                    put(agg, c, "LEVL", y, sum(ab(m, c, "LEVL", y) for m in mem))
                put(agg, "GROF", "COMI", y, sum(ab(m, "GROF", "COMI", y) for m in mem))
    for m in ms:                                                            # l. 667-683
        g20 = ab(m, "GROF", "COMI", LST_DAITAR)
        for c in ("DOMM", "PRCM"):
            b20 = ab(m, c, "COMI", LST_DAITAR)
            if b20 > MIN_ABS and g20 > MIN_ABS:
                for y in after:
                    put(m, c, "COMI", y, b20 * ab(m, "GROF", "COMI", y) / g20)
        for y in exante_t:
            if ab(m, "PRCM", "COMI", y):
                put(m, "MAPR", "MILK", y, ab(m, "PRCM", "COMI", y) + support.get((m, "PRCM", "SGMI", str(y)), 0.0))
    stable = {r for r in runr for s in STABLE if (s, r) in mrr}
    for r in runr:                                                          # l. 685-710
        for c, w in dmap + [("MAPR", "MILK")]:
            for y in exante_t:
                if ab(r, c, w, y):
                    base = TRUST_DAIRY - (TRUST_LESS if c in ("EAAG", "MAPR", "PRCM", "DOMM") else 0.0)
                    f = TRUST_DECAY + (TRUST_GROW if (c, w) == ("GROF", "COMI") and r in stable else 0.0)
                    E[(r, c, w, str(y))][1] = base * f ** max(0, y - LST_DAITAR)
        for y in exante_t:
            if ab(r, "EXPE", "COMI", y):
                E[(r, "EXPE", "COMI", str(y))][1] = TRUST_EXPE
    share: Dict[Tuple[str, int], float] = {}                                # l. 712-757
    for a in europ_aggs:
        for y in years_cur:
            g = dgagri.get((a, "GROF", "COMI", str(y)), 0.0)
            if g:
                _set(share, (a, y), dgagri.get((a, "HCOM", "COMI", str(y)), 0.0) / g)
    for m in ms:
        for y in expostt:
            g = pdata.get((m, "GROF", "COMI", str(y)), 0.0)
            if g:
                _set(share, (m, y), pdata.get((m, "HCOM", "COMI", str(y)), 0.0) / g)
    lst = max(expostt)
    for m in ms:
        for y in exante_t:
            if sum(share.get((a, y), 0.0) for a in m2a[m]):
                _set(share, (m, y), share.get((m, lst), 0.0)
                     * sum(share.get((a, y), 0.0) / share[(a, lst)] for a in m2a[m]))
        for y in exante_t:
            if y > lst_dgagri and m2a[m]:
                _set(share, (m, y), share.get((m, lst_dgagri), 0.0))
    noeu = [m for m in ms_no_eu28 if m in ms_set]
    for m in noeu:
        for y in exante_t:
            g = support.get((m, "GROF", "COMI", str(y)), 0.0)
            if g:
                _set(share, (m, y), support.get((m, "HCOM", "COMI", str(y)), 0.0) / g)
    sim = sorted(sim_years)
    for i, y in enumerate(sim):                                             # loop(simulationYear): the lag in that set
        if i == 0 or y <= fst_exante:
            continue
        for m in noeu:
            cur, prev = share.get((m, y), 0.0), share.get((m, sim[i - 1]), 0.0)
            if cur > prev or not cur:
                _set(share, (m, y), prev)
    return {k: (v[0], v[1]) for k, v in E.items() if v[0] or v[1]}, share


def hcom_expert(share: Dict[Tuple[str, int], float], expert: Dict[Key, float], support: Dict[Key, float],
                rest: Iterable[str], exante_t: Sequence[int]) -> Dict[Key, Tuple[float, float]]:
    """define_stats_and_supports.gms l. 510-519: HCOM.COMI's expert support = share x GROF.COMI's expert support (its
    trend support where it has none), trust 5 where the share is above 0.0001 and 1 elsewhere (every region and ex-ante
    year: GAMS assigns the trust level without a condition). expert: p_result(..., "expert") of GROF.COMI."""
    out: Dict[Key, Tuple[float, float]] = {}
    for r in rest:
        for y in exante_t:
            s = share.get((r, y), 0.0)
            g = expert.get((r, "GROF", "COMI", str(y)), 0.0) or support.get((r, "GROF", "COMI", str(y)), 0.0)
            out[(r, "HCOM", "COMI", str(y))] = (s * g, TRUST_HCOM if s > SHARE_MIN else TRUST_HCOM_LOW)
    return out

"""CAPTRD's own expert rules (captrd/expert_support.gms, CAPRI star 3.0), the parts written in that file; its included
sources (biofuel trends, DG AGRI's dairy data, Eurostat's recent production, national experts, the long-run
projections) are separate stages. Each support is an absolute value with a trust level, p_ExpertSupprt(region, col,
row, year, "Absolute" | "TrustLevl"), for the ex-ante years.

In GAMS's order (line numbers of expert_support.gms):
  l. 51-52    fresh milk products' net trade NTRD.FRMI: 0.1 (trust 10)
  l. 64-104   sugar, for the EU's member states (MS without msNoEU): white sugar's price UVAG.SUGA 404.4 from 2009
              (trust 10); sugar beet's price UVAG.SUGB 26.29 + 75.94 x the molasses yield PRCY.MOLA's support x 0.5
              (trust 10); the beet and sugar balance positions IMPT, FEDM, LOSM, EXPT of SUGB and FEDM, LOSM of SUGA at
              their base-year values (trust 8)
  l. 132-176  per-head nutrient intake (N_CAL, N_FAT, N_PRO .INCE): the base-year value plus the EU mean's 2000-2010
              annual increase, declining linearly to zero by 2050 and smaller where a country's intake is above the EU
              mean (convergence factor 4); trust 10, fat 7; expert bounds 0.99/1.01 in ExAnteT (not stored here)
  l. 206-250  isoglucose: the maize processed to HFCS (PRCI.MAIZ) of the EU aggregates from DG AGRI's sugar
              consumption, HFCS's share of sweeteners and its self-sufficiency; to the member states half by maize
              production and half by sugar consumption shares (BAST, else BASM), trust 9; INDM.MAIZ at 1.05 x PRCI.MAIZ
              where it has no support, trust 5
  l. 299-322  UAAR.LEVL (trust 10), the breeding animals' slaughter weights SLGW (trust 8) and sheep milk yield
              SHGM.SGMI (trust 5) at their supports, where no expert has set them

As coded, kept: the isoglucose shares' denominators sum the member states of every EU aggregate a country belongs to
(EU014000 and EU27yr19 both), so a member state's share is over the two (l. 222-225); the EU mean of the nutrient
intake divides by every member state, those without data included (l. 135, 139).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

#: l. 51-52
FRMI_NTRD = 0.1
TRUST_FRMI = 10.0
#: l. 64-73: white sugar's price from 2009 (EUR/t)
SUGA_PRICE = 404.4
SUGAR_FROM = 2009
#: l. 74-86: beet price = 26.29 + 75.94 x molasses yield x 0.5 (EUR/t)
SUGB_PRICE = 26.29
MOLA_PRICE = 75.94
MOLA_SHARE = 0.5
TRUST_SUGAR_PRICE = 10.0
TRUST_SUGAR_BALANCE = 8.0
#: l. 145-171: the nutrient trend's horizon, convergence factor and trust levels
NUTRIENT_HORIZON = 2050
CONVERGENCE = 4.0
TRUST_NUTRIENT = 10.0
TRUST_FAT = 7.0
#: l. 216: share of HFCS allocated by maize production (the rest by sugar consumption)
HFCS_PROD_SHARE = 0.5
TRUST_PRCI = 9.0
INDM_OVER_PRCI = 1.05
TRUST_INDM = 5.0
#: l. 299-322
TRUST_UAAR = 10.0
TRUST_SLGW = 8.0
TRUST_SGMI = 5.0


def rules(*, ms: Sequence[str], ms_no_eu: Iterable[str], exante: Sequence[int], bas_year: int,
          support: Dict[Tuple[str, str, str, str], float], basm: Dict[Tuple[str, str, str], float],
          bast: Dict[Tuple[str, str, str], float], pdata_years: Dict[Tuple[str, str, str, str], float],
          dgagri: Dict[Tuple[str, str, str, str], float], dgagri1: Dict[Tuple[str, str, str, str], float],
          ms_to_agg: Iterable[Tuple[str, str]], europ_aggs: Iterable[str], breed_act: Iterable[str],
          ncnc: Iterable[str], coef_hfcs: Dict[str, float]) -> Dict[Tuple[str, str, str, str], Tuple[float, float]]:
    """{(region, col, row, year): (Absolute, TrustLevl)} of this file's rules, in GAMS's order (later rules see the
    earlier ones). support: p_result(..., year, "support"); basm, bast: p_data's BASM and BAST per (region, col, row)
    (p_result(..., ExAnte, "BASM"/"BAST") repeat them over the ex-ante years); pdata_years: p_data of the calendar
    years (for the nutrient means); dgagri, dgagri1: the DG AGRI positions (aglink.py, scale_dgagri.py)."""
    E: Dict[Tuple[str, str, str, str], List[float]] = {}
    ex = [str(y) for y in exante]

    def put(r, c, w, y, a=None, t=None):
        e = E.setdefault((r, c, w, y), [0.0, 0.0])
        if a is not None:
            e[0] = a
        if t is not None:
            e[1] = t

    def ab(r, c, w, y):
        return E.get((r, c, w, y), [0.0, 0.0])[0]

    def tr(r, c, w, y):
        return E.get((r, c, w, y), [0.0, 0.0])[1]
    for m in ms:                                                           # l. 51-52
        for y in ex:
            put(m, "NTRD", "FRMI", y, FRMI_NTRD, TRUST_FRMI)
    no_eu = set(ms_no_eu)
    for m in [x for x in ms if x not in no_eu]:                            # l. 64-104
        for y in ex:
            if int(y) >= SUGAR_FROM:
                put(m, "UVAG", "SUGA", y, SUGA_PRICE, TRUST_SUGAR_PRICE)
                put(m, "UVAG", "SUGB", y, SUGB_PRICE + MOLA_PRICE * support.get((m, "PRCY", "MOLA", y), 0.0) * MOLA_SHARE,
                    TRUST_SUGAR_PRICE)
        for y in ex:
            for c, w, cond in (("IMPT", "SUGB", ("DOMM", "SUGB")), ("FEDM", "SUGB", ("DOMM", "SUGB")),
                               ("LOSM", "SUGB", ("DOMM", "SUGB")), ("EXPT", "SUGB", ("GROF", "SUGB")),
                               ("FEDM", "SUGA", ("DOMM", "SUGA")), ("LOSM", "SUGA", ("DOMM", "SUGA"))):
                if basm.get((m, *cond), 0.0):
                    put(m, c, w, y, basm.get((m, c, w), 0.0))
        for y in ex:
            for c, w in (("IMPT", "SUGB"), ("FEDM", "SUGB"), ("LOSM", "SUGB"), ("EXPT", "SUGB"), ("FEDM", "SUGA"),
                         ("LOSM", "SUGA")):
                if ab(m, c, w, y):
                    put(m, c, w, y, t=TRUST_SUGAR_BALANCE)
    # l. 132-176: nutrient intake
    ncnc = list(ncnc)

    def mean(m, n, centre):
        yrs = [str(y) for y in (centre - 1, centre, centre + 1)]
        num = sum(pdata_years.get((m, n, "INCE", y), 0.0) for y in yrs)
        k = sum(1 for y in yrs if pdata_years.get((m, n, "INCE", y), 0.0))
        return num / k if k else 0.0
    for n in ncnc:
        m00 = {m: mean(m, n, 2000) for m in ms}
        m10 = {m: mean(m, n, 2010) for m in ms}
        eu00, eu10 = sum(m00.values()) / len(ms), sum(m10.values()) / len(ms)
        inc = (eu10 - eu00) / 10 if eu00 else 0.0
        for m in ms:
            b = basm.get((m, n, "INCE"), 0.0)
            if not b:
                continue
            for y in ex:
                t = min(NUTRIENT_HORIZON, int(y)) - bas_year
                v = b + inc * t * (1 - 0.5 * t / (NUTRIENT_HORIZON - bas_year)) * (1 + CONVERGENCE * (eu10 - b) / eu10)
                put(m, n, "INCE", y, v)
                if v:
                    put(m, n, "INCE", y, t=TRUST_FAT if n == "N_FAT" else TRUST_NUTRIENT)
    # l. 206-250: isoglucose
    aggs = list(europ_aggs)
    m2a: Dict[str, List[str]] = {}
    for m, a in ms_to_agg:
        if a in set(aggs):
            m2a.setdefault(m, []).append(a)
    a2m: Dict[str, List[str]] = {}
    for m, lst in m2a.items():
        for a in lst:
            a2m.setdefault(a, []).append(m)
    prci = {}
    for r in list(ms) + aggs:
        for y in ex:
            hcos = dgagri.get((r, "HCOS", "HFCS", y), 0.0)
            prci[(r, y)] = (dgagri1.get((r, "HCOM", "SUGA", y), 0.0) * coef_hfcs["SUGA"] * hcos / (1 - hcos)
                            * dgagri.get((r, "S1COM", "HFCS", y), 0.0) / coef_hfcs["MAIZ"])

    def alloc(m, y, base):
        tot = sum(prci.get((a, y), 0.0) for a in m2a.get(m, []))
        peers = [m1 for a in m2a.get(m, []) for m1 in a2m.get(a, [])]
        dg = sum(base.get((m1, "GROF", "MAIZ"), 0.0) for m1 in peers)
        ds = sum(base.get((m1, "HCOM", "SUGA"), 0.0) for m1 in peers)
        g, s_ = base.get((m, "GROF", "MAIZ"), 0.0), base.get((m, "HCOM", "SUGA"), 0.0)
        return tot * (HFCS_PROD_SHARE * (g / dg if dg else 0.0) + (1 - HFCS_PROD_SHARE) * (s_ / ds if ds else 0.0))
    for m in ms:
        if not m2a.get(m):
            continue
        for y in ex:
            if bast.get((m, "GROF", "MAIZ"), 0.0) or bast.get((m, "HCOM", "SUGA"), 0.0):
                put(m, "PRCI", "MAIZ", y, alloc(m, y, bast))
            if not ab(m, "PRCI", "MAIZ", y) and (basm.get((m, "GROF", "MAIZ"), 0.0) or basm.get((m, "HCOM", "SUGA"), 0.0)):
                put(m, "PRCI", "MAIZ", y, alloc(m, y, basm))
    for m in ms:
        for y in ex:
            if ab(m, "PRCI", "MAIZ", y):
                put(m, "PRCI", "MAIZ", y, t=TRUST_PRCI)
                if not support.get((m, "INDM", "MAIZ", y), 0.0):
                    put(m, "INDM", "MAIZ", y, INDM_OVER_PRCI * ab(m, "PRCI", "MAIZ", y))
            if ab(m, "INDM", "MAIZ", y):
                put(m, "INDM", "MAIZ", y, t=TRUST_INDM)
    # l. 299-322
    for m in ms:
        for y in ex:
            for c, w, trust in [("UAAR", "LEVL", TRUST_UAAR)] + [(b, "SLGW", TRUST_SLGW) for b in breed_act] \
                    + [("SHGM", "SGMI", TRUST_SGMI)]:
                if not ab(m, c, w, y):
                    put(m, c, w, y, support.get((m, c, w, y), 0.0))
                if ab(m, c, w, y) and not tr(m, c, w, y):
                    put(m, c, w, y, t=trust)
    return {k: (v[0], v[1]) for k, v in E.items() if v[0] or v[1]}

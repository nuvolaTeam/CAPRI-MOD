"""CAPTRD's own expert rules (captrd/expert_support.gms, CAPRI star 3.0), the parts written in that file; its included
sources (biofuel trends, DG AGRI's dairy data, Eurostat's recent production, national experts, the long-run
projections) are separate stages. Each support is an absolute value with a trust level, p_ExpertSupprt(region, col,
row, year, "Absolute" | "TrustLevl"), for the ex-ante years.

In GAMS's order (line numbers of expert_support.gms; each statement's arithmetic is a named function quoting its GAMS
in capri_mod/pipeline/captrd/equations/expert_support.py):
  l. 53-54    fresh milk products' net trade NTRD.FRMI: 0.1 (trust 10)
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

from capri_mod.pipeline.captrd.equations import expert_support as XE

#: l. 70-73, 83-86: the sugar prices' supports from this year
SUGAR_FROM = 2009


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
    for m in ms:                                                           # l. 53-54
        for y in ex:
            put(m, "NTRD", "FRMI", y, XE.p_ExpertSupprt_NTRD_FRMI(), XE.p_ExpertSupprt_NTRD_FRMI_trustlevl())
    no_eu = set(ms_no_eu)
    for m in [x for x in ms if x not in no_eu]:                            # l. 64-104
        for y in ex:
            if int(y) >= SUGAR_FROM:
                put(m, "UVAG", "SUGA", y, XE.p_ExpertSupprt_uvag_suga(), XE.p_ExpertSupprt_uvag_trustlevl())
                put(m, "UVAG", "SUGB", y, XE.p_ExpertSupprt_uvag_sugb(support.get((m, "PRCY", "MOLA", y), 0.0)),
                    XE.p_ExpertSupprt_uvag_trustlevl())
        for y in ex:
            for c, w, cond in (("IMPT", "SUGB", ("DOMM", "SUGB")), ("FEDM", "SUGB", ("DOMM", "SUGB")),
                               ("LOSM", "SUGB", ("DOMM", "SUGB")), ("EXPT", "SUGB", ("GROF", "SUGB")),
                               ("FEDM", "SUGA", ("DOMM", "SUGA")), ("LOSM", "SUGA", ("DOMM", "SUGA"))):
                if basm.get((m, *cond), 0.0):
                    put(m, c, w, y, XE.p_ExpertSupprt_sugar_balance(basm.get((m, c, w), 0.0)))
        for y in ex:
            for c, w in (("IMPT", "SUGB"), ("FEDM", "SUGB"), ("LOSM", "SUGB"), ("EXPT", "SUGB"), ("FEDM", "SUGA"),
                         ("LOSM", "SUGA")):
                if ab(m, c, w, y):
                    put(m, c, w, y, t=XE.p_ExpertSupprt_sugar_balance_trustLevl())
    # l. 164-198: nutrient intake
    ncnc = list(ncnc)

    def mean(m, n, centre):
        yrs = [str(y) for y in (centre - 1, centre, centre + 1)]
        return XE.p_nutrientEU_mean([pdata_years.get((m, n, "INCE", y), 0.0) for y in yrs])
    for n in ncnc:
        m00 = {m: mean(m, n, 2000) for m in ms}
        m10 = {m: mean(m, n, 2010) for m in ms}
        eu00, eu10 = XE.p_nutrientEU_EU(list(m00.values()), len(ms)), XE.p_nutrientEU_EU(list(m10.values()), len(ms))
        inc = XE.p_nutrientEU_increase(eu10, eu00) if eu00 else 0.0
        for m in ms:
            b = basm.get((m, n, "INCE"), 0.0)
            if not b:
                continue
            for y in ex:
                v = XE.p_ExpertSupprt_INCE(b, inc, int(y), bas_year, eu10)
                put(m, n, "INCE", y, v)
                if v:
                    put(m, n, "INCE", y, t=XE.p_ExpertSupprt_INCE_trustLevl(n == "N_FAT"))
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
            prci[(r, y)] = XE.P_Result_PRCI_MAIZ_DGAgri1(dgagri1.get((r, "HCOM", "SUGA", y), 0.0), coef_hfcs["SUGA"],
                                                         hcos, dgagri.get((r, "S1COM", "HFCS", y), 0.0),
                                                         coef_hfcs["MAIZ"])
    prod = XE.p_coefHFCS_PROD()                                         # l. 222

    def alloc(m, y, base):                                              # l. 224-248
        peers = [m1 for a in m2a.get(m, []) for m1 in a2m.get(a, [])]
        return XE.p_ExpertSupprt_PRCI_MAIZ([prci.get((a, y), 0.0) for a in m2a.get(m, [])], prod,
                                           base.get((m, "GROF", "MAIZ"), 0.0),
                                           [base.get((m1, "GROF", "MAIZ"), 0.0) for m1 in peers],
                                           base.get((m, "HCOM", "SUGA"), 0.0),
                                           [base.get((m1, "HCOM", "SUGA"), 0.0) for m1 in peers])
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
                put(m, "PRCI", "MAIZ", y, t=XE.p_ExpertSupprt_PRCI_MAIZ_trustLevl())
                if not support.get((m, "INDM", "MAIZ", y), 0.0):
                    put(m, "INDM", "MAIZ", y, XE.p_ExpertSupprt_INDM_MAIZ(ab(m, "PRCI", "MAIZ", y)))
            if ab(m, "INDM", "MAIZ", y):
                put(m, "INDM", "MAIZ", y, t=XE.p_ExpertSupprt_INDM_MAIZ_trustLevl())
    # l. 310-338
    for m in ms:
        for y in ex:
            for c, w, trust in [("UAAR", "LEVL", XE.p_ExpertSupprt_UAAR_TRustlevl)] \
                    + [(b, "SLGW", XE.p_ExpertSupprt_SLGW_TRustlevl) for b in breed_act] \
                    + [("SHGM", "SGMI", XE.p_ExpertSupprt_SGMI_TRustlevl)]:
                if not ab(m, c, w, y):
                    put(m, c, w, y, XE.p_ExpertSupprt_from_Support(support.get((m, c, w, y), 0.0)))
                if ab(m, c, w, y) and not tr(m, c, w, y):
                    put(m, c, w, y, t=trust())
    return {k: (v[0], v[1]) for k, v in E.items() if v[0] or v[1]}

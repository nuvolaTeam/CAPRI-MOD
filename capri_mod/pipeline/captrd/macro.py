"""The population of the Aglink load's macro data p_aglinkMacro(region, "INHA", year) (baseline/load_aglink2023dgAgri.gms
l. 905-1068), which CAPTRD's long-run supports put on p_data (captrd/longrun_supports.gms l. 362-389).

In GAMS's order (line numbers of load_aglink2023dgAgri.gms):
  l. 965         the GLOBIOM countries' population of 2000: SSP2 (IIASA)
  l. 982-985     the Aglink years without one: 2000's x the Aglink region's POP (p_aglinkOri ..ME) over its 2000 value,
                 through FAOreg_AGMacroreg (the FAO regions' Aglink regions other than the EU ones, l. 955)
  l. 994-997     the rest: 2000's x the EU country's Aglink macro POP (aglink2023macro.xlsx, ctrCode) over its 2000
                 value (FAOreg_AGMacroreg's countries, ISO_FAOreg, l. 956)
  l. 1006-1009   after %lst_dgagri%: the value of %lst_dgagri% x SSP2's change from %lst_dgagri%
  l. 1035-1046   the years between the SSP years 2025, 2030, ..., before %lastSimulationYear%: linear
  l. 1051-1052   summed to the CAPRI regions over GlobiomCountry_FAOreg and FAORegions_map
  l. 1064-1067   "BAS": the mean of the nonzero values within a year of %BaseYear%
Not here: GDP (l. 966-1014, not read by CAPTRD); Venezuela's and Taiwan's 2000 values from fao_agg's
p_mediumTermData (l. 973-976, 1018-1029: no CAPRI region of CAPTRD's), so Taiwan has no 2000 value here.

And longrun_supports.gms l. 368-389: INHA.LEVL p_data of the years after BAST = p_aglinkMacro(year) /
p_aglinkMacro("BAS") x BASM; where none, the UN population (WorldPop) of the year over its base-year mean x BASM
(the long-run sources' INHA and p_globiomTightLink, l. 371-376, add nothing: the first is empty in the reference run,
the second zero for the ex-ante years, captrd.gms l. 317).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: l. 965, 984: the base year of the growth factors
B2000 = 2000
#: l. 1035: the SSP years (steps of 5 from 2025 to 2100)
SSP_FIRST = 2025
SSP_STEP = 5
SSP_LAST = 2100
#: l. 965, 1007: the population source
SSP_SOURCE = "IIASA"
SSP_SCEN = "SSP2"


def _csv(path: Path) -> List[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def read_inputs(sets_dir: Path, dat_dir: Path):
    """(sets, macro_eu, ssp): the mappings, p_aglinkMacroEU(ctrCode, var, year), SSP_data(source, ssp, var, country,
    year)."""
    sets = {}
    for p in sorted((sets_dir / "macro").glob("*.csv")):
        rows = _csv(p)
        cols = [c for c in rows[0] if c.startswith("d")]
        sets[p.stem] = [tuple(r[c] for c in cols) for r in rows]
    macro = {(r["ctrcode"], r["var"], int(r["year"])): float(r["value"])
             for r in _csv(dat_dir / "macro_p_aglinkmacroeu.csv")}
    ssp = {(r["source"], r["ssp"], r["var"], r["country"], int(r["year"])): float(r["value"])
           for r in _csv(dat_dir / "macro_ssp_data.csv")}
    return sets, macro, ssp


def inha(sets, macro_eu: Dict[Tuple[str, str, int], float], ssp: Dict[tuple, float], *,
         aglink_pop: Dict[Tuple[str, int], float], ag_eu_regs: Iterable[str], ag_years: Sequence[int],
         years: Sequence[int], lst_dgagri: int, last_sim_year: int, fao_map: Iterable[Tuple[str, str]],
         base_year: int) -> Dict[Tuple[str, object], float]:
    """p_aglinkMacro(region, "INHA", year or "BAS"). aglink_pop: p_aglinkOri(region, "POP", "ME", year);
    fao_map: FAORegions_map(region, FAO region)."""
    gc = [c for (c,) in sets["globiomcountry"]]
    gc_taw = gc + ["Taiwan"]
    g2f: Dict[str, List[str]] = {}
    for c, f in sets["globiomcountry_faoreg"]:
        g2f.setdefault(c, []).append(f)
    ageu = set(ag_eu_regs)
    f2ag: Dict[str, List[str]] = {}                                    # FAOreg_AGMacroreg, Aglink regions (l. 955)
    for f, a in sets["faoreg_aglinkregions"]:
        if a not in ageu:
            f2ag.setdefault(f, []).append(a)
    f2ctr: Dict[str, List[str]] = {}                                   # FAOreg_AGMacroreg, countries (l. 956)
    ctrs = {k[0] for k in macro_eu}
    for iso, f in sets["iso_faoreg"]:
        if iso in ctrs:
            f2ctr.setdefault(f, []).append(iso)

    def sp(c, y):
        return ssp.get((SSP_SOURCE, SSP_SCEN, "POP", c, y), 0.0)
    P: Dict[Tuple[str, int], float] = {}

    def put(k, v):
        if v:
            P[k] = v
        else:
            P.pop(k, None)
    for c in gc:                                                                    # l. 965
        put((c, B2000), sp(c, B2000))
    for c in gc_taw:                                                                # l. 982-985
        for y in ag_years:
            if not P.get((c, y)):
                s = sum(aglink_pop.get((a, y), 0.0) / aglink_pop[(a, B2000)]
                        for f in g2f.get(c, []) for a in f2ag.get(f, []) if aglink_pop.get((a, B2000)))
                put((c, y), P.get((c, B2000), 0.0) * s)
    for c in gc:                                                                    # l. 994-997
        for y in ag_years:
            if not P.get((c, y)):
                s = sum(macro_eu.get((k, "POP", y), 0.0) / macro_eu[(k, "POP", B2000)]
                        for f in g2f.get(c, []) for k in f2ctr.get(f, []) if macro_eu.get((k, "POP", B2000)))
                put((c, y), P.get((c, B2000), 0.0) * s)
    for c in gc:                                                                    # l. 1006-1009
        if sp(c, lst_dgagri):
            for y in years:
                if y > lst_dgagri:
                    put((c, y), P.get((c, lst_dgagri), 0.0) * sp(c, y) / sp(c, lst_dgagri))
    sspy = list(range(SSP_FIRST, SSP_LAST + 1, SSP_STEP))
    for i, s in enumerate(sspy[:-1]):                                               # l. 1038-1046
        if s >= last_sim_year:
            break
        nxt = sspy[i + 1]
        for c in gc_taw:
            if any(P.get((c, t)) for t in sspy):
                for y in years:
                    if s < y < nxt:
                        put((c, y), P.get((c, s), 0.0) + (y - s) * (P.get((c, nxt), 0.0) - P.get((c, s), 0.0))
                            / (nxt - s))
    f2r: Dict[str, List[str]] = {}
    for r, f in fao_map:
        f2r.setdefault(f, []).append(r)
    out: Dict[Tuple[str, object], float] = {}
    for c in gc_taw:                                                                # l. 1051-1052
        for f in g2f.get(c, []):
            for r in f2r.get(f, []):
                for (cc, y), v in P.items():
                    if cc == c:
                        out[(r, y)] = out.get((r, y), 0.0) + v
    regs = {r for r, _ in out}
    for r in regs:                                                                  # l. 1064-1067
        vals = [out[(r, y)] for y in range(base_year - 1, base_year + 2) if out.get((r, y))]
        if vals:
            out[(r, "BAS")] = sum(vals) / len(vals)
    return out


def inha_pdata(macro: Dict[Tuple[str, object], float], *, ms: Iterable[str], basm: Dict[str, float],
               years_cur: Iterable[int], bast_year: int, exante: Iterable[int],
               world_pop: Optional[Dict[Tuple[int, str], float]] = None, basy: Optional[int] = None):
    """longrun_supports.gms l. 368-389: INHA.LEVL p_data per (region, year). basm: INHA.LEVL BASM per region;
    world_pop: WorldPop(year, region) for the fallback; basy: BASY (%BaseYear%)."""
    out: Dict[Tuple[str, int], float] = {}
    cur = set(years_cur)
    for r in ms:
        b, m0 = basm.get(r, 0.0), macro.get((r, "BAS"), 0.0)
        for y in cur:
            if y > bast_year and macro.get((r, y)) and m0 and b:
                out[(r, y)] = macro[(r, y)] / m0 * b
    if world_pop is not None:                                                       # l. 386-389
        for r in ms:
            w0 = world_pop.get((basy, r), 0.0)
            for y in exante:
                if not out.get((r, y)) and w0:
                    v = basm.get(r, 0.0) * world_pop.get((y, r), 0.0) / w0
                    if v:
                        out[(r, y)] = v
    return out

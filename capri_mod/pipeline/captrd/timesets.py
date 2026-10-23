"""CAPTRD's time sets (captrd.gms l. 203-271, 665-812).

All years are calendar years; OrdT(t) = t for the years (captrd.gms l. 266). The ex-post years come from the data:
ExPost = years with UAAR in some country of CAPREG's time series (l. 673), ExPostT = the same after the COCO
nowcasts are added (l. 721-722, load_coco1_data.gms). The other sets follow from them, the simulation years (RESY,
the GUI's choice) and %BaseYear% / %lst_dgagri%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from capri_mod.settings import current as _settings


@dataclass
class TimeSets:
    years: List[int]                 # YEARS = %FirstYear% .. %lastSimulationYear%
    bas: int                         # %BaseYear%
    lst_dgagri: int                  # %lst_dgagri%
    expost: List[int]                # ExPost
    expostt: List[int]               # ExPostT
    lst_expost: int
    lst_expostt: int
    exante: List[int]                # ExAnte (RESY plus Fst/Sec_exAnte)
    fst_exante: Optional[int]
    sec_exante: Optional[int]
    startpoint_extrap: Optional[float]
    exanted: List[int]               # ex-ante years with ex-post data (nowcasting)
    exantet: List[int]               # ex-ante years without data
    basyrs5: List[int]
    basyrsm: List[int]
    eightlst: List[int]
    bast: int                        # OrdT("BAST"): the centre of the last three ExPostT years
    basyrst: List[int]
    all_last_expost: Optional[int]
    before: List[Tuple[int, int]]    # BeFore(t, t-1) over ExAnte, the first ex-ante year after all_last_expost
    years_cur: List[int]
    years_est: List[int]
    p_trend: Dict[int, float] = field(default_factory=dict)


def build(first_year: int, last_year: int, resy: Iterable[int], base_year: int, lst_dgagri: int,
          uaar_years_any: Iterable[int], uaar_years_all: Iterable[int], expostt_extra: Iterable[int] = (),
          basyrs5_halfwidth: Optional[int] = None) -> TimeSets:
    """The time sets of one CAPTRD run.

    uaar_years_any: years with UAAR.LEVL in at least one country (ExPost, l. 673);
    uaar_years_all: years with UAAR.LEVL in every country (all_last_expost, l. 777);
    expostt_extra: further years with COCO data (ExAnteD source, load_coco1_data.gms l. 54-59);
    basyrs5_halfwidth: BASYRS5 = {|t - BAS| <= h}; CAPRI's h is 3, seven years under the name "5"
    (l. 703; setting captrd.basyrs5_halfwidth).
    """
    h = int(_settings().get("captrd.basyrs5_halfwidth") if basyrs5_halfwidth is None else basyrs5_halfwidth)
    years = list(range(first_year, last_year + 1))
    resy = sorted(int(y) for y in resy)
    if lst_dgagri not in resy and last_year > lst_dgagri:          # l. 251-254
        raise ValueError(f"the year {lst_dgagri} (%lst_dgagri%) must be a simulation year for projections to {last_year}")
    exante: Set[int] = set(resy)                                    # l. 255
    expost = sorted(y for y in set(uaar_years_any) if y in years)  # l. 673
    lst_expost = max(expost)
    expostt = sorted(set(expost) | {y for y in expostt_extra if y in years})   # l. 721-722
    lst_expostt = max(expostt)
    lst_exante = max(exante)
    # l. 733-737
    fst = min(exante)
    fst_exante = fst if (fst in expostt or lst_exante <= lst_dgagri) else None
    if fst_exante is None:
        fst_exante = lst_expost + 1
    # l. 742-751
    sec_exante = None
    if lst_exante > lst_dgagri:
        cand = [y for y in exante if y != fst_exante and (y in expostt or y <= fst_exante + 2)]
        sec_exante = max(cand) if cand else fst_exante + 2
    exante.add(fst_exante)
    if sec_exante is not None:
        exante.add(sec_exante)
    startpoint = None
    if lst_exante > lst_dgagri:                                     # l. 755-757
        pts = [fst_exante] + ([sec_exante] if sec_exante is not None else [])
        startpoint = sum(pts) / len(pts)
    exanted = sorted(y for y in exante if y in expostt)             # l. 760-761
    bast = lst_expostt - 1                                          # l. 764
    basyrst = [y for y in years if abs(bast - y) <= 1]              # l. 768
    exantet = sorted(y for y in exante if y not in exanted)         # l. 775
    basyrs5 = [y for y in expost if abs(y - base_year) <= h]        # l. 703
    basyrsm = [y for y in expost if abs(y - base_year) <= 1]        # l. 704
    eightlst = [y for y in expost if lst_expost - y <= 7]           # l. 705
    complete = sorted(y for y in set(uaar_years_all) if y < fst_exante)   # l. 783-785
    all_last = max(complete) if complete else None
    ex_sorted = sorted(exante | ({all_last} if all_last is not None else set()))
    before = [(ex_sorted[i], ex_sorted[i - 1]) for i in range(1, len(ex_sorted))]   # l. 788-790
    years_cur = sorted(set(expostt) | exante)                       # l. 798-799
    years_est = sorted({1985, 1990, 1995, 2000} | exante)           # l. 806-810
    p_trend = {y: (y - first_year + 1) / 10.0 for y in years}       # l. 271
    return TimeSets(years, base_year, lst_dgagri, expost, expostt, lst_expost, lst_expostt, sorted(exante),
                    fst_exante, sec_exante, startpoint, exanted, exantet, basyrs5, basyrsm, eightlst, bast, basyrst,
                    all_last, before, years_cur, years_est, p_trend)

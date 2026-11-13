"""CAPTRD-MOD: copy_labour_biofuel_on_presult.gms (CAPRI star 3.0, captrd/, included by captrdfrm.gms l. 778) for one
member state: the positions of step3 that are not estimated but derived from it.

  l. 22-24   the activities' labour coefficients (MPACT x ILAB, BASM); GROF's labour BASM = sum over MPACT of coefficient x
             LEVL BASM x 0.001
  l. 29      GROF.LABP's BASM = GROF.LABT - GROF.LABF
  l. 31-40   step3: GROF.LABP by GROF.LABN's step3 over its BASM, GROF.LABT by GROF.LABO's, GROF.LABF = LABT - LABP
  l. 44-50   step1: GROF.ILAB = sum over MPACT of the coefficient x the activity's LEVL step3 x 0.001; each activity's
             ILAB = coefficient x GROF.ILAB step3 / step1 (where step1 is nonzero)
  l. 54      LABT = LABF + LABP per activity
  l. 58-59   the fossil fuels' positions: the expert supports where there are any
  l. 63-64   INHA.LEVL: p_data

For a member state Rest = MS (MAP_RR(MS, MS)): the sums over MAP_RR are its own values. The levels are absolute
(the requirement rows relative as the estimation's: the copies do not touch them).
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, Tuple

K2 = Tuple[str, str]
ILAB = ("LABT", "LABF", "LABP")
#: l. 24, 45: labour hours per 1000 units
PER_1000 = 0.001


def copy(step3: Dict[K2, float], basm: Callable[[str, str], float], mpact: Iterable[str], pact: Iterable[str],
         fossil_fuels: Iterable[str], expert: Dict[K2, float], inha_pdata: float) -> Dict[K2, float]:
    """step3 with the derived positions of copy_labour_biofuel_on_presult.gms. basm(c, w): p_data(MS, c, w, "BASM");
    expert: the Expert supports; inha_pdata: p_result(MS, "INHA", "LEVL", year, "p_data") (0: not copied)."""
    s = dict(step3)
    mpact, pact = sorted(set(mpact)), sorted(set(pact))
    b = {("GROF", w): sum(basm(a, w) * basm(a, "LEVL") for a in mpact) * PER_1000 for w in ILAB}       # l. 24
    b[("GROF", "LABP")] = b[("GROF", "LABT")] - b[("GROF", "LABF")]                                  # l. 29
    labn, labo = basm("GROF", "LABN"), basm("GROF", "LABO")
    s[("GROF", "LABP")] = b[("GROF", "LABP")] * (s.get(("GROF", "LABN"), 0.0) / labn if labn else 0.0)   # l. 31-33
    s[("GROF", "LABT")] = b[("GROF", "LABT")] * (s.get(("GROF", "LABO"), 0.0) / labo if labo else 0.0)   # l. 35-37
    s[("GROF", "LABF")] = s[("GROF", "LABT")] - s[("GROF", "LABP")]                                  # l. 39
    step1 = {w: sum(basm(a, w) * s.get((a, "LEVL"), 0.0) for a in mpact) * PER_1000 for w in ILAB}  # l. 44-45
    for a in pact:                                                                                  # l. 49-50
        for w in ILAB:
            if step1[w]:
                s[(a, w)] = basm(a, w) * s[("GROF", w)] / step1[w]
    for a in pact:                                                                                  # l. 54
        s[(a, "LABT")] = s.get((a, "LABF"), 0.0) + s.get((a, "LABP"), 0.0)
    for (c, w), v in sorted(expert.items()):                                                         # l. 58-59
        if w in set(fossil_fuels) and v:
            s[(c, w)] = v
    if inha_pdata:                                                                                  # l. 63-64
        s[("INHA", "LEVL")] = inha_pdata
    return s

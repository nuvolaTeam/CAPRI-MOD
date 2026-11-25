"""CAPTRD-MOD: copy_labour_biofuel_on_presult.gms (CAPRI star 3.0, captrd/, included by captrdfrm.gms l. 778) for one
member state: the positions of step3 that are not estimated but derived from it.

  l. 23-25   the activities' labour coefficients (MPACT x ILAB, BASM); GROF's labour BASM = sum over MPACT of coefficient x
             LEVL BASM x 0.001
  l. 30      GROF.LABP's BASM = GROF.LABT - GROF.LABF
  l. 32-40   step3: GROF.LABP by GROF.LABN's step3 over its BASM, GROF.LABT by GROF.LABO's, GROF.LABF = LABT - LABP
  l. 44-50   step1: GROF.ILAB = sum over MPACT of the coefficient x the activity's LEVL step3 x 0.001; each activity's
             ILAB = coefficient x GROF.ILAB step3 / step1 (where step1 is nonzero)
  l. 54      LABT = LABF + LABP per activity
  l. 58-59   the fossil fuels' positions: the expert supports where there are any
  l. 63-64   INHA.LEVL: p_data

For a member state Rest = MS (MAP_RR(MS, MS)): the sums over MAP_RR are its own values. The levels are absolute
(the requirement rows relative as the estimation's: the copies do not touch them). l. 68-69 (the SERIES position) is
the reporting's. Each statement's arithmetic is a named function in capri_mod/pipeline/captrd/equations/
copy_labour_biofuel_on_presult.py.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, Tuple

from capri_mod.pipeline.captrd.equations import copy_labour_biofuel_on_presult as CL

K2 = Tuple[str, str]
ILAB = ("LABT", "LABF", "LABP")


def copy(step3: Dict[K2, float], basm: Callable[[str, str], float], mpact: Iterable[str], pact: Iterable[str],
         fossil_fuels: Iterable[str], expert: Dict[K2, float], inha_pdata: float) -> Dict[K2, float]:
    """step3 with the derived positions of copy_labour_biofuel_on_presult.gms. basm(c, w): p_data(MS, c, w, "BASM");
    expert: the Expert supports; inha_pdata: p_result(MS, "INHA", "LEVL", year, "p_data") (0: not copied). The
    statements' arithmetic is in capri_mod/pipeline/captrd/equations/copy_labour_biofuel_on_presult.py."""
    s = dict(step3)
    mpact, pact = sorted(set(mpact)), sorted(set(pact))
    b = {("GROF", w): CL.p_data_GROF_ILAB_BASM([(basm(a, w), basm(a, "LEVL")) for a in mpact]) for w in ILAB}  # l. 25
    b[("GROF", "LABP")] = CL.p_data_GROF_LABP_BASM(b[("GROF", "LABT")], b[("GROF", "LABF")])          # l. 30
    labn, labo = basm("GROF", "LABN"), basm("GROF", "LABO")
    s[("GROF", "LABP")] = CL.p_result_GROF_LABP_Step3(b[("GROF", "LABP")], s.get(("GROF", "LABN"), 0.0), labn)  # l. 32-34
    s[("GROF", "LABT")] = CL.p_result_GROF_LABT_Step3(b[("GROF", "LABT")], s.get(("GROF", "LABO"), 0.0), labo)  # l. 36-38
    s[("GROF", "LABF")] = CL.p_result_GROF_LABF_Step3(s[("GROF", "LABT")], s[("GROF", "LABP")])      # l. 40
    step1 = {w: CL.p_result_GROF_ILAB_Step1([(basm(a, w), s.get((a, "LEVL"), 0.0)) for a in mpact])
             for w in ILAB}                                                                        # l. 44-45
    for a in pact:                                                                                  # l. 49-50
        for w in ILAB:
            if step1[w]:
                s[(a, w)] = CL.p_result_PACT_ILAB_Step3(basm(a, w), s[("GROF", w)], step1[w])
    for a in pact:                                                                                  # l. 54
        s[(a, "LABT")] = CL.p_result_PACT_LABT_Step3(s.get((a, "LABF"), 0.0), s.get((a, "LABP"), 0.0))
    for (c, w), v in sorted(expert.items()):                                                         # l. 58-59
        if w in set(fossil_fuels) and v:
            s[(c, w)] = CL.p_result_fossilFuels_Step3(v)
    if inha_pdata:                                                                                  # l. 63-64
        s[("INHA", "LEVL")] = CL.p_result_INHA_LEVL_Step3(inha_pdata)
    return s

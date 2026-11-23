r"""CAPRI's welfare report (reports/welfare.gms, star 3.0): the agricultural profit of the supply models' regions
(ProfitAgr), which the income report computes (capri_mod/income/income_module.py IncomeDistributionModule).

The market's welfare (capri_mod/market/welfare.py) and the coupling's supply welfare (coupling/reporting.py) port more
of welfare.gms (block A4).
"""
from __future__ import annotations


def p_welfareRes_ProfitAgr(MGVA, LEVL):
    r"""p_welfareRes(RMSSUP, "ProfitAgr"): the agricultural profit, sum over the activities of their gross value added per
    unit (MGVA, the model's net revenue per ha or head) times their levels (sequences in the same order).

    CAPRI's GAMS (reports/welfare.gms l. 448-449):

           p_welfareRes(RMSSUP,"ProfitAgr",XX1,"%SIMY%")
              = SUM(PACT_TO_XX(MPACT,XX1), DATA(RMSSUP,MPACT,"MGVA","%SIMY%") * DATA(RMSSUP,MPACT,"LEVL","%SIMY%")*0.001);

    In this project's notation: ProfitAgr = sum_a MGVA_a L_a. Departures from CAPRI: the units (EUR 1000 from EUR per ha
    or head and 1000 ha or heads; CAPRI's x 0.001 to million EUR); CAPRI's outputs and inputs not assigned to activities
    (l. 451-456: EAAG of the outputs and inputs no activity produces or uses, NECR, ARES, LRES, SERI, mitiI, RQUO, SERO,
    NASA, mitiO) not added; the technology mix's net revenue added by the caller (supply/techn_mix.py)."""
    return float(sum(m * l_ for m, l_ in zip(MGVA, LEVL)))

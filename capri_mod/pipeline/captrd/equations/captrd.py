r"""CAPTRD's statements of captrd.gms (CAPRI star 3.0) with arithmetic that the data preparation ports: the land uses
scaled to ARTO, the base year's diet bounds, the household labour, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/prepare.py (load_fixes, load_basm,
labour_household) holds the selections, the conditions and the order, and calls them with pandas Series; the
arithmetic is the port's, so the data are unchanged. captrd.gms's other statements in the port are set and time-set
definitions (timesets.py), DataFrame selections that delete (prepare.py) and the requirements' conversion after the
estimation (l. 1206-1217, estimate_ms.requirement_factor, the estimation's).
"""
from __future__ import annotations


def p_data_LanduseARTO(value, arto, positive_sum):
    r"""p_data(Rest, LanduseARTO, "LEVL", Years): the land uses (not below zero) scaled to sum to ARTO.

    positive_sum: the nonnegative land uses' sum (pandas Series aligned with value).

    CAPRI's GAMS (captrd.gms l. 514-516):

            p_data(Rest,LanduseARTO,"LEVL",Years) $ (SUM(LanduseARTO1,MAX(0,p_data(REst,LanduseARTO1,"LEVL",Years))) $ p_data(REst,"ARTO","LEVL",Years))
                = MAX(0,p_data(REst,LanduseARTO,"LEVL",Years)) * p_data(REst,"ARTO","LEVL",Years)
                / SUM(LanduseARTO1,MAX(0,p_data(REst,LanduseARTO1,"LEVL",Years)));

    Departures from CAPRI: the port multiplies by ARTO's share, CAPRI by ARTO and then divides (the last digit may differ); the domain condition
    in the caller (prepare.load_fixes)."""
    return value.clip(lower=0.0) * (arto / positive_sum)


def p_data_DRMN_DRMX_BASM(value, days):
    r"""p_data(Rest, AACT, "DRMN" / "DRMX", "BASM"): the daily dry matter bound times the days.

    CAPRI's GAMS (captrd.gms l. 579-579):

            p_data(Rest,AACT,"DRMN","BASM")         = DATA2(Rest,AACT,"DRMN","Y") * DATA2(Rest,AACT,"DAYS","Y");

    CAPRI's GAMS (captrd.gms l. 580-580):

            p_data(Rest,AACT,"DRMX","BASM")         = DATA2(Rest,AACT,"DRMX","Y") * DATA2(Rest,AACT,"DAYS","Y");

    Departures from CAPRI: none in the arithmetic; the selection in the caller (prepare.load_basm)."""
    return value * days


def p_data_LABH(labo, labn):
    r"""p_data(Rest, "GROF", "LABH", YEARS and BASM): the household labour, total less hired.

    CAPRI's GAMS (captrd.gms l. 897-897):

            p_data(Rest,"GROF","LABH",YEARS)  = p_data(Rest,"GROF","LABO",YEARS) - p_data(Rest,"GROF","LABN",YEARS);

    CAPRI's GAMS (captrd.gms l. 898-898):

            p_data(Rest,"GROF","LABH","BASM") = p_data(Rest,"GROF","LABO","BASM") - p_data(Rest,"GROF","LABN","BASM");

    Departures from CAPRI: none in the arithmetic; the selection in the caller (prepare.labour_household)."""
    return labo - labn

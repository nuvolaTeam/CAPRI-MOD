r"""CAPTRD's statements of captrd/copy_labour_biofuel_on_presult.gms (CAPRI star 3.0): the positions of the result
(Step3) not estimated but derived from it, labour from the activity levels, the fossil fuels and the population, as
named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/step3_copies.py (copy) holds the loops over the
activities and the conditions and calls them; the arithmetic is the port's, so the results are unchanged. For a member
state Rest = MS (MAP_RR(MS, MS)): the sums over MAP_RR are its own values.
"""
from __future__ import annotations


def p_data_GROF_ILAB_BASM(terms):
    r"""p_data(Rest, "GROF", ILAB, "BASM"): labour (LABT, LABF, LABP) of the base year from the activities' coefficients
    and levels, in 1000 hours.

    terms: (p_data(a, ILAB, "BASM"), p_data(a, "LEVL", "BASM")) of the activities MPACT, in the caller's order.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 25-25):

            p_data(rEst,"GROF",ILAB,"BASM") = SUM(MPACT, p_data(rEst,MPACT,ILAB,"BASM") * p_data(rEst,MPACT,"LEVL","BASM")) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return sum(coef * levl for coef, levl in terms) * 0.001


def p_data_GROF_LABP_BASM(labt, labf):
    r"""p_data(Rest, "GROF", "LABP", "BASM"): paid labour, total less family labour.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 30-30):

           p_data(rEst,"GROF","LABP","BASM") = p_data(rEst,"GROF","LABT","BASM") -  p_data(rEst,"GROF","LABF","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return labt - labf


def p_result_GROF_LABP_Step3(labp_basm, labn_step3, labn_basm):
    r"""p_result(Rest, "GROF", "LABP", exAnte, "Step3"): paid labour at the trend of LABN (its Step3 over its BASM).

    labp_basm: p_data(., "GROF", "LABP", "BASM"); labn_step3, labn_basm: GROF.LABN's Step3 and BASM (no trend where
    the BASM is zero).

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 32-34):

           p_result(rEst,"GROF","LABP",exAnte,"Step3")
              = p_data(rEst,"GROF","LABP","BASM") * SUM(MAP_RR(MS,rEst) $ p_data(MS,"GROF","LABN","BASM") ,
                                                                 p_result(MS,"GROF","LABN",exAnte,"Step3")/p_data(MS,"GROF","LABN","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return labp_basm * (labn_step3 / labn_basm if labn_basm else 0.0)


def p_result_GROF_LABT_Step3(labt_basm, labo_step3, labo_basm):
    r"""p_result(Rest, "GROF", "LABT", exAnte, "Step3"): total labour at the trend of LABO (its Step3 over its BASM).

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 36-38):

           p_result(rEst,"GROF","LABT",exAnte,"Step3")
              = p_data(rEst,"GROF","LABT","BASM") * SUM(MAP_RR(MS,rEst) $ p_data(MS,"GROF","LABO","BASM"),
                                                                 p_result(MS,"GROF","LABO",exAnte,"Step3")/p_data(MS,"GROF","LABO","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return labt_basm * (labo_step3 / labo_basm if labo_basm else 0.0)


def p_result_GROF_LABF_Step3(labt, labp):
    r"""p_result(Rest, "GROF", "LABF", exAnte, "Step3"): family labour, total less paid labour.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 40-40):

           p_result(rEst,"GROF","LABF",exAnte,"Step3") = p_result(rEst,"GROF","LABT",exAnte,"Step3") - p_result(rEst,"GROF","LABP",exAnte,"Step3");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return labt - labp


def p_result_GROF_ILAB_Step1(terms):
    r"""p_result(Rest, "GROF", ILAB, exAnte, "Step1"): labour at the base year's coefficients and the result's levels.

    terms: (p_data(a, ILAB, "BASM"), p_result(a, "LEVL", "Step3")) of the activities MPACT, in the caller's order.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 44-45):

           p_result(rEst,"GROF",ILAB,exAnte,"Step1")
              =  SUM(MPACT, p_data(rEst,MPACT,ILAB,"BASM") * p_result(rEst,MPACT,"LEVL",exAnte,"Step3")) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return sum(coef * levl for coef, levl in terms) * 0.001


def p_result_PACT_ILAB_Step3(coef, grof_step3, grof_step1):
    r"""p_result(Rest, PACT, ILAB, exAnte, "Step3"): an activity's labour coefficient scaled so that the activities'
    labour adds up to GROF's (where Step1 is nonzero).

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 49-50):

           p_result(rEst,PACT,ILAB,exAnte,"Step3") $ p_result(rEst,"GROF",ILAB,exAnte,"Step1")
              =  p_data(rEst,PACT,ILAB,"BASM") * p_result(rEst,"GROF",ILAB,exAnte,"Step3")/p_result(rEst,"GROF",ILAB,exAnte,"Step1");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return coef * grof_step3 / grof_step1


def p_result_PACT_LABT_Step3(labf, labp):
    r"""p_result(Rest, PACT, "LABT", exAnte, "Step3"): an activity's total labour, family plus paid.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 54-54):

           p_result(rEst,PACT,"LABT",exAnte,"Step3") = p_result(rEst,PACT,"LABF",exAnte,"Step3") + p_result(rEst,PACT,"LABP",exAnte,"Step3");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return labf + labp


def p_result_fossilFuels_Step3(expert):
    r"""p_result(Rest, cols, fossilFuels, exAnte, "Step3"): the fossil fuels' positions at the expert supports.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 58-59):

           p_result(rEst,cols,fossilFuels,exAnte,"Step3") $  p_result(rEst,cols,fossilFuels,exAnte,"Expert")
                                                          =  p_result(rEst,cols,fossilFuels,exAnte,"Expert");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return expert


def p_result_INHA_LEVL_Step3(pdata):
    r"""p_result(Rest, "INHA", "LEVL", exAnte, "Step3"): the population, the exogenous series.

    CAPRI's GAMS (captrd/copy_labour_biofuel_on_presult.gms l. 63-64):

           p_result(rEst,"INHA","LEVL",exAnte,"Step3") $  p_result(rEst,"INHA","LEVL",exAnte,"p_data")
                                                       =  p_result(rEst,"INHA","LEVL",exAnte,"p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (step3_copies.copy)."""
    return pdata

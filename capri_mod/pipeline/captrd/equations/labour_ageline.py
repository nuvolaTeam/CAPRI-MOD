r"""CAPTRD's statements of baseline/labour_ageline.gms (CAPRI star 3.0, included at captrd.gms l. 902): the bounds on
agricultural labour from the farm holders' age lines and the activities' minimum labour, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol and its position). capri_mod/pipeline/captrd/labour.py (ageline_bounds,
labour_bounds) holds the loops over the countries, the survey years and the ex-ante years, the data and the
conditions, and calls them; the arithmetic is the port's, so the bounds are unchanged.
"""
from __future__ import annotations


def AGELINE_GROF_SRNUTS1(ageline):
    r"""AGELINE(SRNUTS1, "GROF", YEARS): a NUTS 1 region's holders of working age (25-65) in a survey year.

    ageline: the age line's records (region, age, year, value) of the NUTS 1 regions, the working ages and the
    years. Returns the sums by (region, year) (pandas' groupby sum, as the port had it).

    CAPRI's GAMS (baseline/labour_ageline.gms l. 33-33):

        AGELINE(SRNUTS1,"GROF",YEARS) = SUM(W_AGE, AGELINE(SRNUTS1,W_AGE,YEARS));

    Departures from CAPRI: the sum is pandas' (its own summation of the ages, as the port had it); the selection of the NUTS 1 regions, the ages and
    the years in the caller (labour.ageline_bounds)."""
    return ageline.groupby(["region", "year"])["value"].sum()


def AGELINE_GROF_MS(regional):
    r"""AGELINE(MS, "GROF", YEARS): a country's holders of working age, its NUTS 1 regions' summed.

    regional: the NUTS 1 regions' AGELINE_GROF_SRNUTS1 of the year, in the caller's order.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 35-35):

        AGELINE(MS,"GROF",YEARS)      = SUM(MAP_RR(MS,SRNUTS1), AGELINE(SRNUTS1,"GROF",YEARS));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    total = 0.0
    for v in regional:
        total = total + float(v)
    return total


def AGELINE_ANUAL_CHANGE(grof0, grof1, span):
    r"""AGELINE(MS, "ANUAL_CHANGE", survey year): the annual change rate of the holders between a survey year and the
    next (1993-1995, 1995-1997, 1997-2000, 2000-2003, 2003-2012, 2012-2015).

    grof0, grof1: AGELINE(MS, "GROF", ...) of the two survey years (grof0 nonzero); span: the years between them.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 39-55):

        AGELINE(MS,"ANUAL_CHANGE","1993") $ AGELINE(MS,"GROF","1993")
         =  (AGELINE(MS,"GROF","1995") / AGELINE(MS,"GROF","1993")) ** (1/2);

        AGELINE(MS,"ANUAL_CHANGE","1995") $ AGELINE(MS,"GROF","1995")
         =  (AGELINE(MS,"GROF","1997") / AGELINE(MS,"GROF","1995")) ** (1/2);

        AGELINE(MS,"ANUAL_CHANGE","1997") $ AGELINE(MS,"GROF","1997")
         =  (AGELINE(MS,"GROF","2000") / AGELINE(MS,"GROF","1997")) ** (1/3);

        AGELINE(MS,"ANUAL_CHANGE","2000") $ AGELINE(MS,"GROF","2000")
         =  (AGELINE(MS,"GROF","2003") / AGELINE(MS,"GROF","2000")) ** (1/3);

        AGELINE(MS,"ANUAL_CHANGE","2003") $ AGELINE(MS,"GROF","2003")
         =  (AGELINE(MS,"GROF","2012") / AGELINE(MS,"GROF","2003")) ** (1/9);

        AGELINE(MS,"ANUAL_CHANGE","2012") $ AGELINE(MS,"GROF","2012")
         =  (AGELINE(MS,"GROF","2015") / AGELINE(MS,"GROF","2012")) ** (1/3);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return (grof1 / grof0) ** (1.0 / span)


def AGELINE_ANUAL_CHANGE_fill(previous):
    r"""AGELINE(MS, "ANUAL_CHANGE", YEARS) where the year has none: the year before's (sequentially, a LOOP).

    CAPRI's GAMS (baseline/labour_ageline.gms l. 59-60):

        LOOP((MS,YEARS) $ (NOT AGELINE(MS,"ANUAL_CHANGE",YEARS)),
          AGELINE(MS,"ANUAL_CHANGE",YEARS) = AGELINE(MS,"ANUAL_CHANGE",YEARS-1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return previous


def AGELINE_EXPT_CHANGE(changes):
    r"""AGELINE(MS, "EXPT_CHANGE", EXANTE): the expected change of labour, the product of the annual change rates from
    the base year to the year before the ex-ante year.

    changes: the annual change rates of those years, in order.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 66-66):

        AGELINE(MS,"EXPT_CHANGE",EXANTE) = PROD(YEARS $ (ORDT(YEARS) GE ORDT("BAS") AND ORDT(YEARS) LT ORDT(EXANTE)), AGELINE(MS,"ANUAL_CHANGE",YEARS));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    v = 1.0
    for x in changes:
        v *= x
    return v


def AGELINE_MIN_CHANGE(expt, others):
    r"""AGELINE(MS, "MIN_CHANGE", EXANTE): at least the smallest expected change of any country with one - 0.05, the
    own - 0.1, and 0.

    expt: the country's EXPT_CHANGE; others: the nonzero EXPT_CHANGE of all countries (SMIN over an empty set is +INF
    in GAMS, so without any the bound is +inf).

    CAPRI's GAMS (baseline/labour_ageline.gms l. 74-76):

        AGELINE(MS,"MIN_CHANGE",EXANTE) = MAX( SMIN(MS1 $ AGELINE(MS1,"EXPT_CHANGE",EXANTE), AGELINE(MS1,"EXPT_CHANGE",EXANTE)) - 0.05,
                                               AGELINE(MS,"EXPT_CHANGE",EXANTE) - 0.1,
                                               0 );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return max(min(others) - 0.05, expt - 0.1, 0.0) if others else float("inf")


def AGELINE_MAX_CHANGE(expt, smax):
    r"""AGELINE(MS, "MAX_CHANGE", EXANTE): at most the largest expected change of any country + 0.05, the own + 0.1
    (where the country has one), and 1.

    expt: the country's EXPT_CHANGE; smax: the largest of all countries'.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 80-87):

        AGELINE(MS,"MAX_CHANGE",EXANTE) $ AGELINE(MS,"EXPT_CHANGE",EXANTE)
                                        = MIN( SMAX(MS1, AGELINE(MS1,"EXPT_CHANGE",EXANTE)) + 0.05,
                                               AGELINE(MS,"EXPT_CHANGE",EXANTE) + 0.1,
                                               1 );

        AGELINE(MS,"MAX_CHANGE",EXANTE) $ (NOT AGELINE(MS,"EXPT_CHANGE",EXANTE))
                                        = MIN( SMAX(MS1, AGELINE(MS1,"EXPT_CHANGE",EXANTE)) + 0.05,
                                               1 );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return min(smax + 0.05, expt + 0.1, 1.0) if expt else min(smax + 0.05, 1.0)


def p_labourPerAct_MinRequirement_BASM(min_value, labt):
    r"""p_labourPerAct(MS, MPACT, "LABT", "BASM", "MinRequirement"): an activity's minimum labour requirement, the
    smaller of the minimum (p_minLabourPerAct, h per unit, 2008) and 75% of it plus 25% of the country's own LABT.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 175-175):

        p_labourPerAct(MS,MPACT,"LABT","BASM","MinRequirement") = MIN(p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA"), 0.75 * p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA") + 0.25 * p_labourPerAct(MS,MPACT,"LABT","BASM","DATA"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return min(min_value, 0.75 * min_value + 0.25 * labt)


def p_labourPerAct_MinRequirement(req_basm, n):
    r"""p_labourPerAct(MS, MPACT, "LABT", EXANTE, "MinRequirement"): the base year's minimum requirement, 0.5% less a
    year of technical progress.

    req_basm: p_labourPerAct_MinRequirement_BASM; n: the years from the base year to the year before the ex-ante
    year.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 177-177):

        p_labourPerAct(MS,MPACT,"LABT",EXANTE,"MinRequirement") = p_labourPerAct(MS,MPACT,"LABT","BASM","MinRequirement") * PROD(YEARS $ (ORDT(YEARS) GE ORDT("BAS") AND ORDT(YEARS) LT ORDT(EXANTE)), 0.995);

    Departures from CAPRI: CAPRI's PROD of 0.995 over the years is the port's 0.995 ** n (it may differ in the last digit); the domain condition in the
    caller (labour.labour_bounds)."""
    return req_basm * 0.995 ** n


def p_labourPerAct_GROF_MinRequirement(terms):
    r"""p_labourPerAct(MS, "GROF", "LABT", EXANTE, "MinRequirement"): the country's minimum labour at its base levels,
    in 1000 hours.

    terms: (p_labourPerAct_MinRequirement, P_DATA(MS, MPACT, "LEVL", "BASM")) of the activities, in the caller's
    order.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 183-183):

        p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") = SUM(MPACT, p_labourPerAct(MS,MPACT,"LABT",EXANTE,"MinRequirement") * P_DATA(MS,MPACT,"LEVL","BASM") * 0.001);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return sum(req * levl * 0.001 for req, levl in terms)


def p_labourPerAct_fromAct(req, grof_basm):
    r"""p_labourPerAct(MS, "GROF", "LABT", EXANTE, "MIN_fromAct" / "MAX_fromAct"): the minimum labour over the base
    labour, x 0.9 and x 1.5 (EXPT_fromAct, x 1, the port does not keep). Returns (min, max), zeros where the base is
    zero.

    CAPRI's GAMS (baseline/labour_ageline.gms l. 186-189):

        p_labourPerAct(MS,"GROF","LABT",EXANTE,"EXPT_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA");
        * define min and max to account for uncertainty
        p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA") * 0.9;
        p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA") * 1.5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    if not grof_basm:
        return 0.0, 0.0
    return req / grof_basm * 0.9, req / grof_basm * 1.5


def p_labourPerAct_CHANGE(from_ageline, from_act):
    r"""p_labourPerAct(MS, "GROF", "LABT", EXANTE, "MIN_CHANGE" / "MAX_CHANGE"): the larger of the age lines' and the
    activities' bound (P_DATA(MS, "MINS" / "MAXS", "LABO", EXANTE), l. 204-205).

    CAPRI's GAMS (baseline/labour_ageline.gms l. 198-199):

        p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_CHANGE") = MAX(p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAgeline"),p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAct"));
        p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_CHANGE") = MAX(p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAgeline"),p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAct"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (labour.ageline_bounds / labour_bounds)."""
    return max(from_ageline, from_act)

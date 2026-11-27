r"""CAPRI's update of the yield-dependent input coefficients (capmod/define_inputs.gms, star 3.0): the input-saving
progress TF_I with a scenario's percentage changes (l. 66, 70-73), the main output's yield growth p_yieldGrowth
(l. 80-82, 96-97, 101-102) and the coefficients of the directly yield-dependent inputs IY (l. 107-112). capmod.gms
runs it for every main activity in the simulation (l. 772, with MPACT), after the scenario's yield shifts; it is how
the Green Deal's plant-protection and other-input changes (pol_input/greendeal/organic_io.gms, conventional_io.gms,
as DATA(RS, "GROF", I, "percentageChange")) reach the coefficients (KNOWN_ISSUES DEP-21).

O_HP's update from the same file (l. 89-92) is fertned.py O_HP_yieldGrowth.
"""
from __future__ import annotations


def TF_I_trend(progress: float, year: int, base_year: int) -> float:
    r"""TF_I(RS, IY, "T") before a scenario's change: the input-saving progress, 0.5% a year (progress:
    INPUT_SAVING_PROGRESS) from the base year to the simulation year.

    CAPRI's GAMS (capmod/define_inputs.gms l. 64-66):

        *       --- 0.5 % input saving technical progress per year
        *
                TF_I(RS,IY,"T") = 1. -0.005 * (CALYEA("Y")-CALYEA("BAS"));

    In this project's notation: TF_I = 1 - 0.005 (Y - BAS). Departures from CAPRI: none (block A5; the caller passed
    it to TF_I before)."""
    return 1.0 - progress * (year - base_year)


def TF_I(TF_I_trend: float, percentageChange: float = 0.0, scenAugmentsTechChange: bool = True) -> float:
    r"""TF_I(RS, IY, "T"): the factor on a yield-dependent input's coefficient for the simulation year.

    CAPRI's GAMS (capmod/define_inputs.gms l. 66, 70-73):

            TF_I(RS,IY,"T") = 1. -0.005 * (CALYEA("Y")-CALYEA("BAS"));
    *
    *       --- using given input value
    *
            TF_I(RS,IY,"T") $ DATA(RS,"GROF",IY,"percentageChange")

    $ifi not %scenAugmentsTechChange%==on  = (1. + DATA(RS,"GROF",IY,"percentageChange")/100);
    $ifi     %scenAugmentsTechChange%==on  = (1. + DATA(RS,"GROF",IY,"percentageChange")/100)*TF_I(RS,IY,"T");

    In this project's notation: TF_I = 1 - 0.005 (Y - BAS) (TF_I_trend, the caller's), and where the scenario sets a
    change pc (a fraction here, CAPRI's percentage / 100) TF_I = (1 + pc) TF_I_trend, or (1 + pc) alone where CAPRI's
    code drops the trend's factor (scenAugmentsTechChange off: the Green Deal's conventional_io.gms, FIX-5;
    supply.greendeal_inputs_keep_tech_change keeps it, the default). Departures from CAPRI: none (FIX-5 is a setting)."""
    pc = float(percentageChange or 0.0)
    if not pc:
        return float(TF_I_trend)
    return (1.0 + pc) * (float(TF_I_trend) if scenAugmentsTechChange else 1.0)


def p_yieldGrowth(yield_Y, yield_BAS, LEVL_BAS: float, bounded: bool = True) -> float:
    r"""p_yieldGrowth(RS, act): the activity's main-output yield growth from the base year to the simulation year.

    CAPRI's GAMS (capmod/define_inputs.gms l. 80-82, 96-97, 101-102):

            p_yieldGrowth(RS,%pacts%) $ p_dataCopy(RS,%pacts%,"LEVL","BAS")
              = SUM(PACT_TO_Y(%pacts%,curRows) $ p_dataCopy(RS,%pacts%,curRows,"BAS"),
                  p_dataCopy(RS,%pacts%,curRows,"Y")/p_dataCopy(RS,%pacts%,curRows,"BAS") );
            ...
            p_yieldGrowth(RS,%pacts%) $ ((NOT p_yieldGrowth(RS,%pacts%))
                                       $ p_dataCopy(RS,%pacts%,"LEVL","BAS")) = 1.0;
            ...
            p_yieldGrowth(RS,%pacts%) $ p_dataCopy(RS,%pacts%,"LEVL","BAS")
               = MIN(1.5,MAX(0.5,p_yieldGrowth(RS,%pacts%)));

    In this project's notation: G = sum over the activity's main outputs (PACT_TO_Y) of y(Y) / y(BAS), the outputs
    with a base yield; 1 where that sum is 0; within 0.5-1.5. Only for an activity with a base level (else 0, CAPRI's
    unassigned value). yield_Y, yield_BAS: the main outputs' yields, in the same order. bounded False: the value before
    l. 96-102, which O_HP takes (l. 89-92). Departures from CAPRI: none."""
    if not LEVL_BAS:
        return 0.0
    g = sum(float(y) / float(b) for y, b in zip(yield_Y, yield_BAS) if b)
    if not bounded:
        return g
    if not g:
        g = 1.0
    return min(1.5, max(0.5, g))


def DATA_IY_Y(DATA_BAS: float, p_inputDemandFactor: float, p_yieldGrowth: float, TF_I: float) -> float:
    r"""DATA(RS, act, IY, "Y"): a directly yield-dependent input's coefficient in the simulation year.

    CAPRI's GAMS (capmod/define_inputs.gms l. 107-112):

            p_dataCopy(RS,%pacts%,IY,"BAS") = DATA(RS,%pacts%,IY,"BAS");
            DATA(RS,%pacts%,IY,"Y") $ p_dataCopy(RS,%pacts%,IY,"BAS")
                = ( p_dataCopy(RS,%pacts%,IY,"BAS")
                     * (1-p_inputDemandFactor(%pacts%,IY) + p_inputDemandFactor(%pacts%,IY) * p_yieldGrowth(RS,%pacts%)))
                                         * TF_I(RS,IY,"T");

    In this project's notation: x(Y) = x(BAS) (1 - f + f G) TF_I, f CAPRI's p_inputDemandFactor (inputs/yieldIY.gms, 1
    where its table leaves it blank, l. 103), G p_yieldGrowth above, TF_I above. Unchanged (the caller keeps its
    value) where x(BAS) is 0: None. Departures from CAPRI: none."""
    if not DATA_BAS:
        return None
    f = float(p_inputDemandFactor)
    return float(DATA_BAS) * (1.0 - f + f * float(p_yieldGrowth)) * float(TF_I)


def DATA_QUTS_pesTotal(GROF, ChangeFactor):
    r"""DATA(RU, "QUTS", "pesTotal", "Y"): the quota on the region's total pesticide use (t), its change factor on the
    use at the base levels GROF.

    CAPRI's GAMS (capmod/define_inputs.gms l. 141-157):

        *            -- Baseline total pesticide use

                DATA(RU,"GROF","pesTotal","Y")
                  = sum((mCACT,PESTOAGG,A), Data(ru,mCACT,PESTOAGG,"y")*(1+p_technFact(ru,MCACT,pestoAgg,A))*v_actLevl.l(ru,MCACT,A))*.001;

        *               ... is partly used to determine the quota level by region

                DATA(RU,"QUTS","pesTotal","Y") $ DATA(RU,"QUTS","pesTotal","AbsoluteLevel")
                  = DATA(RU,"QUTS","pesTotal","AbsoluteLevel") $ (DATA(RU,"QUTS","pesTotal","AbsoluteLevel") ne eps);

                DATA(RU,"QUTS","pesTotal","Y") $ DATA(RU,"QUTS","pesTotal","AbsoluteChange")
                 = DATA(RU,"GROF","pesTotal","Y")
                 + DATA(RU,"QUTS","pesTotal","AbsoluteChange") $ (DATA(RU,"QUTS","pesTotal","AbsoluteChange") ne eps);


                DATA(RU,"QUTS","pesTotal","Y")  $ DATA(RU,"QUTS","pesTotal","ChangeFactor")
                      = DATA(RU,"GROF","pesTotal","Y") * DATA(RU,"QUTS","pesTotal","ChangeFactor");

    Departures from CAPRI: the change factor only (CAPRI's AbsoluteLevel, AbsoluteChange and PercentageChange forms
    are the same quota written otherwise; the port's scenarios give the factor)."""
    return float(GROF) * float(ChangeFactor)

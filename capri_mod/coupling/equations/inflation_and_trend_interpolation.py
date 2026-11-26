r"""CAPRI's prices at the simulation year for the goods the market part does not cover
(capmod/inflation_and_trend_interpolation.gms, star 3.0): the base year's unit value times the inflation factor.
tools/build/build_npk_balance_2030.py applies them to the nutrients' outputs (MANN, MANP, MANK), whose unit values
the crops' and animals' output value takes (KNOWN_ISSUES K212).
"""
from __future__ import annotations


def p_inflationFactor(p_infl, SIMY, BAS):
    r"""p_inflationFactor(RS), p_inflationFactor(MS): CAPRI's inflation from the base year to the simulation year.

    CAPRI's GAMS (capmod/inflation_and_trend_interpolation.gms l. 22-23):

                p_inflationFactor(RS)            = p_infl**(CALYEA("20%SIM%")-CALYEA("BAS"));
                p_inflationFactor(MS)            = p_infl**(CALYEA("20%SIM%")-CALYEA("BAS"));

    In this project's notation: p_inflationFactor = p_infl ^ (SIMY - BAS), p_infl CAPRI's 1.019 (the model's money
    deflator, tools/lib/_money.py, is the same factor).

    Departures from CAPRI: none."""
    return float(p_infl) ** (int(SIMY) - int(BAS))


def DATA_UVAG_IO_SIMY(UVAG_BAS, p_inflationFactor):
    r"""DATA(MS, "UVAG", IO, SIMY) of a good outside the market part (NOT IOE): its base year unit value moved by
    inflation alone, so constant in the base year's money.

    CAPRI's GAMS (capmod/inflation_and_trend_interpolation.gms l. 67-72):

        *      ----- price for products not covered in market part are base year price times inflation
        *
               DATA(MS,"UVAP",IO,"20%SIM%") $ (NOT IOE(IO)) = DATA(MS,"UVAP",IO,"BAS") * p_inflationFactor(MS);
               DATA(MS,"UVAB",IO,"20%SIM%") $ (NOT IOE(IO)) = DATA(MS,"UVAB",IO,"BAS") * p_inflationFactor(MS);
               DATA(MS,"UVAG",IO,"20%SIM%") $ (NOT IOE(IO)) = DATA(MS,"UVAG",IO,"BAS") * p_inflationFactor(MS);
               DATA(MS,"UVAG",IO,"Y")  $ (NOT IOE(IO)) = DATA(MS,"UVAG",IO,"20%SIM%");

    In this project's notation: UVAG(SIMY) = UVAG(BAS) x p_inflationFactor, in CAPRI's money of the simulation year
    (divided by the money deflator for the model's 2017 money).

    Departures from CAPRI: none (UVAP and UVAB, the purchase and basic prices, are not needed)."""
    return float(UVAG_BAS) * float(p_inflationFactor)

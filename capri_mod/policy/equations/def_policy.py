r"""CAPRI's policy of the year (policy/def_policy.gms, star 3.0): each premium record carried from the last edited year
before it.

capri_mod/policy/cap14_premiums.py (_last) calls it; capri_mod/policy/mtr.py (declarations_of_year) and norway.py
(norway_premiums) apply the same rule in their loops over the records.
"""
from __future__ import annotations


def p_premDataE_last(values, year):
    r"""p_premDataE(editedRegions, year, PSDPAY_T, PSPOS_GRP): a record's value of the last year up to the year that has
    one ({year: value}); None where none has.

    CAPRI's GAMS (policy/def_policy.gms l. 57-62):

             LOOP ( (before(editedYears,editedYears1)),
        $        batinclude 'util\title.gms' "'Set premium scheme details for '" editedYears.tl '" from "' editedYears1.tl
                 p_premDataE(editedRegions,editedYears,PSDPAY_T,PSPOS_GRP) $ (p_premDataE(editedRegions,editedYears1,PSDPAY_T,PSPOS_GRP)
                                                                               $(not p_premDataE(editedRegions,editedYears,PSDPAY_T,PSPOS_GRP)))
                                                                                    = p_premDataE(editedRegions,editedYears1,PSDPAY_T,PSPOS_GRP);
             );

    Departures from CAPRI: the year's value directly (CAPRI's loop over the pairs of edited years, before: the same
    last value)."""
    ys = [y for y in values if y <= year]
    return values[max(ys)] if ys else None

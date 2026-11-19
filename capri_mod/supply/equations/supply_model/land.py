r"""CAPRI's land block (supply/supply_model.gms l. 2376-2534): the land balances of the land types, the land market.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview and departures.

Written so far: the land balances' rows of the regional QP (RegionalSupplyModel._build_constraints: "arable_land",
"permanent_land", "grassland"). With Trustee_land on (CAPRI's 2030 Green Deal step), CAPRI's land types without a
slack are ARAC, FRUN and GRAS (sets.gms l. 3096-3097) and their balance is LandBalNoSlak_: the activities on a land
type equal the land type's level, a variable of the land market. The model's base QP writes the rows with the land
fixed at the data; the land market (supply/land.py _land_augment) makes the land a column.

A porting difference, kept by the move (for the main line; not a departure): the base rows' right-hand side is
max(the land data, the base area of the land type's activities) (LandBal_rhs), which keeps the base year feasible
where the land data and the crop areas come from different aggregations (54 of 248 regions for arable land, 56 for
permanent crops; supply_module's comments); CAPRI's right-hand side is the land type's level alone.
"""
from __future__ import annotations

import numpy as np


def LandBalNoSlak_(n, acts_idx, acts):
    r"""LandBalNoSlak_(r, landTypesNoSlak) (l. 2399-2403), its left-hand side: the activities on the land type
    (landTypes_to_pact), one per unit of their level; the row of the regional QP over its n columns (acts_idx: column
    of each activity; acts: the land type's activities).

    CAPRI's GAMS, LandBalNoSlak_ (l. 2399-2403):

        LandBalNoSlak_(RUNR,landTypesNoSlak)  ..
            SUM( (landTypes_to_pact(landTypesNoSlak,MPACT),A)  $ p_technFact(RUNR,MPACT,"LEVL",A),
                           v_actLevl(RUNR,MPACT,A)) =E= v_actLevl(RUNR,landTypesNoSlak,"T")     ;
    """
    row = np.zeros(n)
    for a in acts:
        if a in acts_idx:
            row[acts_idx[a]] = 1.0
    return row


def LandBal_rhs(land, base_use):
    r"""The base QP's right-hand side of a land balance: max(the land type's data level, the base area of its
    activities). A porting difference (the module's docstring): CAPRI's LandBalNoSlak_ has the land type's level, and
    in its fixed-land form, LandBalSlak_ (l. 2382-2395), the data level with a slack:

         LandBalSlak_(RUNR,landTypesSlak)  $ ((not sameas(landTypesSlak,"ANNC")) or (p_landIsFixed eq 0)) ..
            SUM( (landTypes_to_pact(landTypesSlak,MPACT),A)  $ p_technFact(RUNR,MPACT,"LEVL",A),
                v_actLevl(RUNR,MPACT,A))
              + v_landbalslak(RUNR,landTypesSlak)
            =e=  %data%(RUNR,landTypesSlak,"LEVL","Y") $ (p_landIsFixed eq 1)
               + v_actLevl(RUNR,landTypesSlak,"T")     $ (p_landIsFixed eq 0);
    """
    return max(land, base_use)

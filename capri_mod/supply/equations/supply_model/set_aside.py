r"""CAPRI's set-aside block (supply/supply_model.gms l. 2225-2375): the obligatory and landscape set-aside, the activity
limits, the idled histosols and the minimum cover crops.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview and departures.

Written so far: e_setaLandscape, the Green Deal's landscape floor on the set-aside activities (the regional QP's
"landscape_floor" row, RegionalSupplyModel._build_constraints). The floor itself, DATA(FALL, FLOOR), is set by CAPRI's
policy file (pol_input/greendeal/landscape.gms: lndscpTarg / 10 x p_setAsideTarget x UAAR + the existing set-aside),
which the builder computes. e_minCoverCrops (l. 2368-2370) is the catch crops' lower bound (premiums.py's catcMiti_).

A porting difference, kept by the move: CAPRI writes e_setaLandscape only where the floor exceeds eps; the model writes
the row whenever a set-aside requirement is set, also with a zero floor (the row then reads -x <= 0).
"""
from __future__ import annotations

import numpy as np


def e_setaLandscape(n, acts_idx, setaFallow, floor):
    r"""e_setaLandscape(r) (l. 2326-2332): the set-aside activities (setaFallow: VSET and FALL; ISET, GSET and TSET have
    no area in CAPRI's 2017 and 2030 data) at least the floor DATA(FALL, FLOOR), as the QP's row in the upper-bound form
    -sum x <= -floor over its n columns. Returns (row, rhs).

    CAPRI's GAMS, e_setaLandscape (l. 2326-2332):

        e_setaLandscape(RUNR) $ ((%data%(RUNR,"FALL","FLOOR","Y") gt eps))..
            SUM((setaFallow,A) $ p_technFact(RUNR,setaFallow,"LEVL",A), v_actLevl(RUNR,setaFallow,A))
                =G= %data%(RUNR,"FALL","FLOOR","Y");
    """
    row = np.zeros(n)
    for a in setaFallow:
        row[acts_idx[a]] = -1.0
    return row, -floor

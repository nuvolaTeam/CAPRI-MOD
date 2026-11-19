r"""CAPRI's set-aside block (supply/supply_model.gms l. 2225-2375): the obligatory and landscape set-aside, the activity
limits, the idled histosols and the minimum cover crops.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview and departures.

Written so far: e_setaLandscape, the Green Deal's landscape floor on the set-aside activities (the regional QP's
"landscape_floor" row, RegionalSupplyModel._build_constraints). The floor itself, DATA(FALL, FLOOR), is set by CAPRI's
policy file (pol_input/greendeal/landscape.gms: lndscpTarg / 10 x p_setAsideTarget x UAAR + the existing set-aside),
which the builder computes. e_minCoverCrops (l. 2368-2370) is the catch crops' lower bound (premiums.py's catcMiti_).
idleHisto_: the idled histosols' bound (supply/abatement.py _histosol_columns), the area being the model's column.

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


def idleHisto_(width, land_cols, maxshare, share, H):
    r"""idleHisto_(r, idlHisAct, luClassAgr) (l. 2295-2306) as the bound of the idled histosol area: CAPRI defines the
    area from the option's share, v_actLevl(iHis) = v_Miti x share x the land (x v_landshare(GRAS) for grassland), with
    v_Miti <= MaxShare; the model's column is the area F itself (supply/abatement.py _histosol_columns), so the
    equation becomes F <= MaxShare x share x the land. With the land market (land_cols: the land types' columns, CROP =
    ARAC + FRUN, the productive grassland GRAS; K158) on the current land, F - MaxShare x share x L <= 1e-9 max(1, H);
    without it on the base area, F <= MaxShare x H (H = share x the base area). Returns (row over width columns, the
    last being F, rhs).

    CAPRI's GAMS, idleHisto_ (l. 2295-2306):

     idleHisto_(runr,idlHisAct,luClassAgr) $ p_ghgMiti(RUNR,idlHisAct,"fallow","othImpact",luClassAgr) ..
           v_actLevl(RUNR,idlHisAct,"T")
                =E= v_Miti(RUNR,idlHisAct,"fallow","N2OHIS")
                   *p_ghgMiti(RUNR,idlHisAct,"fallow","othImpact",luClassAgr)
                   *v_actLevl(RUNR,luClassAgr,"T")
                   *( v_landshare(RUNR,"GRAS") $ (    sameas(idlHisAct,"iHisGr"))
                    + 1                        $ (not sameas(idlHisAct,"iHisGr")) )
                   ;
    """
    up = np.zeros(width); up[-1] = 1.0
    if land_cols:
        for j in land_cols:
            up[j] = -float(maxshare) * share
        return up, 1e-9 * max(1.0, H)
    return up, float(maxshare) * H


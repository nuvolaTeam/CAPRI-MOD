r"""CAPRI's fertiliser application limits (supply/supply_model.gms l. 4501-4601, "NOTE: So far not present in supply
model calibration, only used in scenarios"): e_synNMax, the Green Deal's mineral N limit per ha.

Written so far: e_synNMax (pol_input/greendeal/minfert_redu_uaa.gms sets its limit).

CAPRI's GAMS, e_synNMax (l. 4537-4539):

   e_synNMax(RUNR) $ %data%(runr,"MINFER","MAXS","Y") ..

    v_minfert(runr,"NITF") =l= %data%(runr,"MINFER","MAXS","Y")  * 1000;

with v_minfert(NITF) from e_MINFERT (l. 1295-1298): v_minfert x sum(landTypesNoSlak, v_actLevl) x 0.001 =
-v_netPutQuant, the mineral N per ha of the land in kg (n_surplus.py's block).

In this project's notation, per region (P = v_netPutQuant(NITF), the N purchases in t; L the land, the fertilisation
block's land columns, kha; cap the limit in kg/ha, CAPRI's DATA(MINFER, MAXS) x 1000; the model's is the base
purchases per ha x (1 - the reduction), fertilisation.py):

    e_synNMax:  (P - cap x L) / Pscale <= 0

Departures from CAPRI: none in the equation; written on the purchases times the land instead of on v_minfert (the same
inequality for L > 0), scaled by the purchases' scale.
"""
from __future__ import annotations


def e_synNMax(v_netPutQuant, cap, land, inv_Pscale):
    """e_synNMax (l. 4537-4539): the N purchases at most the cap per ha times the land, (P - cap x L) / Pscale <= 0."""
    return (v_netPutQuant - cap * land) * inv_Pscale

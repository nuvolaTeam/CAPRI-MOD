"""CAPRI's idled histosols in the N balance: their deposition (K184).

CAPRI's idled histosols, iHisCr and iHisGr (sets.gms: idlHisAct, a part of MCACT, l. 2175-2177 and 2234-2238; crop
group idlHis, supply/define_ngrp_sets.gms l. 93-94), are crop activities without fertiliser use whose DATA(MANN), the
N from residues and atmospheric deposition per ha, is the region's deposition p_nitrBalance(AtmDep) (CAPRI's Green
Deal run: within 0.15 kg N/ha of ATMOSD / UAAR in all 143 units with idled histosols; DE21 12.52 kg/ha). So the
idled area keeps its deposition in two of CAPRI's equations, both written here as their idled-histosol term:

- the residue pool distributed over the crop groups (fertDistCres_, supply/supply_model.gms l. 1049-1085): the sum over
  the annual crops of v_actLevl x DATA(MANN) x (1 + p_technFact(MANN, A)), idlHis being an annual group;
- the N surplus (e_SURTOTHa, l. 1463-1475): + v_atmosd + v_Cresid, where e_ATMOSD (l. 1381-1389) sums
  v_actLevl x AtmDep over MCACT and e_CRESID (l. 1393-1414) makes v_Cresid + v_atmosd the sum of v_actLevl x MANN
  over MCACT: for an idled hectare MANN = AtmDep, its deposition, and no residues.

The model's histosol columns (supply.abatement._histosol_columns, F = 1000 ha idled) took the land from the crops
without either term, so an idled hectare lost its deposition from the pool and from the surplus (DE21 Green Deal at
CAPRI's prices: deposition -0.30 kt against CAPRI's +0.22).

Units: F in 1000 ha, AtmDep in kg N per ha, the result in t N (kg/ha x 1000 ha / 1000).
Departures from CAPRI: none in the terms; N only (CAPRI's MANP and MANK of the idled histosols are zero).
"""
from __future__ import annotations


def MANN_idlHis(AtmDep: float) -> float:
    """CAPRI's DATA(iHisCr | iHisGr, MANN): N from residues and deposition per ha of an idled histosol = the region's
    deposition per ha, p_nitrBalance(AtmDep) (kg N/ha)."""
    return float(AtmDep)


def fertDistCres_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of fertDistCres_'s right-hand side (supply_model.gms l. 1049-1085):
    v_actLevl(iHis) x DATA(iHis, MANN), t N (v_actLevl in 1000 ha)."""
    return v_actLevl * MANN_idlHis(AtmDep)


def SURTOT_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of the N surplus in t (e_SURTOTHa x UAAR): their e_ATMOSD term, v_actLevl x AtmDep;
    their e_CRESID term, v_actLevl x (MANN - AtmDep), is zero."""
    return v_actLevl * float(AtmDep) + v_actLevl * (MANN_idlHis(AtmDep) - float(AtmDep))

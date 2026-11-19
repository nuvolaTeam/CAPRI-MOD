r"""CAPRI's soil surface N balance (supply/supply_model.gms l. 1389-1483): e_ATMOSD, e_CRESID, e_SURTOTHa.

Written so far: the idled histosols' terms (K184; see nutrients.py for the activities). An idled hectare keeps its
deposition in the N surplus: e_ATMOSD sums v_actLevl x AtmDep over MCACT, and e_CRESID makes v_Cresid + v_atmosd the
sum of v_actLevl x MANN over MCACT; for an idled histosol MANN = AtmDep, its deposition, and no residues.

CAPRI's GAMS, e_ATMOSD (l. 1389-1397), e_CRESID (l. 1401-1422, the optional yield terms of ghgAbatement and
PEST_DISAGG left out here), e_SURTOTHa (l. 1471-1483):

    e_ATMOSD(runr,FNUT)  ..
         v_atmosd(runr,FNUT) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
    + SUM( FOUT_T_N(FOUT,FNUT),
       SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A),
                   v_actLevl(RUNR,MCACT,A)
                   * p_nitrBalance(RUNR,"AtmDep")))
         * 0.001;

    e_CRESID(runr,FNUT)  ..
         (v_Cresid(runr,FNUT) + v_atmosd(runr,fnut))
         * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001
         =e= 0
         + SUM( (FOUT_T_N(FOUT,FNUT),MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A),v_actLevl(RUNR,MCACT,A)
                  *  (%data%(RUNR,MCACT,FOUT,"Y") ... )
                       *(p_technFact(RUNR,MCACT,FOUT,A)+1.)) ... * 0.001;

    e_SURTOTHa(runr,fnut)  ..
       v_nutSurTot(RUNR,FNUT) =E= 0
            + v_minfert(runr,fnut)
            + v_excret(runr,fnut)
            - v_manureNetExportHa(runr,fnut)
            + v_biofix(runr,fnut)
            + v_atmosd(runr,fnut)
            + v_Cresid(runr,fnut)
            - v_expprd(runr,fnut)
    ;

In this project's notation, the idled histosols' part of the region's surplus in t (e_SURTOTHa x UAAR), F in 1000 ha:

    SURTOT_idlHis = F x AtmDep  (their e_ATMOSD term)  +  F x (MANN_idlHis - AtmDep)  (their e_CRESID term, zero)

Departures from CAPRI: none in the terms; the model writes the surplus in t, CAPRI per ha of the land types (the NLP's
N-surplus row is per ha of current land, supply.land).
"""
from __future__ import annotations

from capri_mod.supply.equations.supply_model.nutrients import MANN_idlHis


def SURTOT_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of the N surplus in t (e_SURTOTHa x UAAR): their e_ATMOSD term, v_actLevl x AtmDep;
    their e_CRESID term, v_actLevl x (MANN - AtmDep), is zero."""
    return v_actLevl * float(AtmDep) + v_actLevl * (MANN_idlHis(AtmDep) - float(AtmDep))

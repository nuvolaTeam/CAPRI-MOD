r"""CAPRI's nutrient surplus (supply/supply_model.gms l. 1280-1497 and 1791-1886): the soil surface N balance
(e_ATMOSD, e_CRESID, e_SURTOTHa) and its limit SURTOT_REST_.

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

CAPRI's GAMS, SURTOT_REST_ (l. 1875-1879; the Green Deal's surplus target, pol_input/greendeal/surptot.gms):

    SURTOT_REST_(RUNR) $ (p_envConst(RUNR,"all","all","SURTOT") or %data%(runr,"SURTOT","MAXS","Y"))..

    v_nutSurTot(RUNR,"NITF") =L= ( p_envConst(RUNR,"all","all","SURTOT")
                                 + %data%(runr,"SURTOT","MAXS","Y") $ (not p_envConst(RUNR,"all","all","SURTOT"))) *1000;

In this project's notation, the regional N-surplus row of the NLP (e_SURTOTHa x the land, t; rs the row's scale):

    SURTOT_REST_:  [ sum_j a_j y_j + P + BioFix_catc ] / rs  <=  b / rs

a_j the row's coefficients without their mineral parts (the regional QP's N-surplus row less the mineral N of the
crops, fertilisation.py _n_row_mineral_parts), P = v_netPutQuant(NITF) the purchases (e_MINFERT's v_minfert x the
land), BioFix_catc the catch crops' fixation (e_BIOFIX), b the target x the land (supply.land: per ha of current land,
CAPRI's form).

Departures from CAPRI: none in the restriction; e_SURTOTHa's per-ha terms are written in t over the land (supply.land).
"""
from __future__ import annotations

from capri_mod.supply.equations.supply_model.nutrients import MANN_idlHis


def SURTOT_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of the N surplus in t (e_SURTOTHa x UAAR): their e_ATMOSD term, v_actLevl x AtmDep;
    their e_CRESID term, v_actLevl x (MANN - AtmDep), is zero."""
    return v_actLevl * float(AtmDep) + v_actLevl * (MANN_idlHis(AtmDep) - float(AtmDep))


def SURTOT_REST_(rest, v_netPutQuant, inv_rs, catcBioFix):
    """SURTOT_REST_ with e_SURTOTHa (l. 1875-1879, 1471-1483) as the NLP's scaled row, <= b / rs: the surplus terms
    without the mineral N (scaled, from the regional QP's row), + the purchases / rs, + the catch crops' BioFix (scaled;
    0 without catch crops)."""
    return rest + v_netPutQuant * inv_rs + catcBioFix

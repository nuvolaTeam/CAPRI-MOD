r"""CAPRI's nutrient balances of the crops (supply/supply_model.gms l. 1049-1298): fertDistCres_, NUTNED_.

Written so far: the idled histosols' terms (K184). CAPRI's idled histosols, iHisCr and iHisGr (sets.gms: idlHisAct, a
part of MCACT, l. 2175-2177 and 2234-2238; crop group idlHis, supply/define_ngrp_sets.gms l. 93-94), are crop
activities without fertiliser use whose DATA(MANN), the N from residues and atmospheric deposition per ha, is the
region's deposition p_nitrBalance(AtmDep) (CAPRI's Green Deal run: within 0.15 kg N/ha of ATMOSD / UAAR in all 143
units with idled histosols; DE21 12.52 kg/ha). The model's histosol columns (supply.abatement._histosol_columns,
F = 1000 ha idled) took the land from the crops without their term in the residue pool (DE21 Green Deal at CAPRI's
prices: deposition -0.30 kt against CAPRI's +0.22).

CAPRI's GAMS, fertDistCres_ (l. 1049-1088):

    fertDistCres_(RUNR,FNUT)  ..
       SUM(NGRP $ Sum( (CACT_TO_NGRP(noPermCact,NGRP),a) $ [p_technFact(RUNR,noPermCact,"LEVL",A) and %data%(RUNR,noPermCact,"levl","Y")], 1),
            v_fertDist(RUNR,NGRP,FNUT,"Cres"))
         =E=
          SUM( (noPermCact,A) $  [p_technFact(RUNR,noPermCact,"LEVL",A) and %data%(RUNR,noPermCact,"levl","Y")],
             SUM( FOUT_T_N(FOUT,FNUT),
                v_actLevl(RUNR,noPermCact,A)
                  * (%data%(RUNR,noPermCact,FOUT,"Y")
    $iftheni.till0 %ghgAbatement%==on
                  +  (%data%(RUNR,noPermCact,FOUT,"Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))
                  *  (v_yldMit(RUNR,noPermCact) - 1)
    $endif.till0
    $iftheni.Pes4 %PEST_DISAGG%==ON
                  +  (%data%(RUNR,noPermCact,FOUT,"Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))
                  *  (v_yldPestFac(RUNR,noPermCact,A) - 1) $ v_yldPestFac.range(RUNR,noPermCact,A)
    $endif.Pes4
                   )
                     * (p_technFact(RUNR,noPermCact,FOUT,A)+1.)))
    $iftheni.covC1 %ghgAbatement%==on
         + [(p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"CATC","T") * 1000) $ sameas(FNUT,"NITF")]
    $endif.covC1
    ;

In this project's notation, the idled histosols' term of the right-hand side, t N with F in 1000 ha:

    fertDistCres_idlHis = F x MANN_idlHis,   MANN_idlHis = AtmDep (kg N/ha)

(p_technFact(iHis, MANN, A) = 0: one technology; v_yldMit and v_yldPestFac do not apply to an activity without output.)
Departures from CAPRI: none in the term; N only (CAPRI's MANP and MANK of the idled histosols are zero).
"""
from __future__ import annotations


def MANN_idlHis(AtmDep: float) -> float:
    """CAPRI's DATA(iHisCr | iHisGr, MANN): N from residues and deposition per ha of an idled histosol = the region's
    deposition per ha, p_nitrBalance(AtmDep) (kg N/ha)."""
    return float(AtmDep)


def fertDistCres_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of fertDistCres_'s right-hand side (l. 1049-1088): v_actLevl(iHis) x DATA(iHis, MANN),
    t N (v_actLevl in 1000 ha)."""
    return v_actLevl * MANN_idlHis(AtmDep)

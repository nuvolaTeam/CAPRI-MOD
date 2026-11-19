r"""CAPRI's fertilising block for N, P and K (supply/supply_model.gms l. 870-1279): the three pools a nutrient is
distributed from (fertDistExcr_ with ManureNPK_, fertDistMine_, fertDistCres_) and the crop groups' need balance
NUTNED_. The inner fertiliser model that distributes the pools over the groups is inner_fert.py's block.

CAPRI's GAMS, fertDistExcr_ (l. 878-890):

       fertDistExcr_(RUNR,FNUT)  ..

           SUM(NGRP $ SUM((CACT_TO_NGRP(MCACT,NGRP),A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,MCACT,"levl","Y")), 1),
               v_fertDist(RUNR,NGRP,FNUT,"Excr"))

             =E=
             v_ManureNPK(RUNR,FNUT) $ SUM( (MAACT) $ p_technFact(RUNR,MAACT,"LEVL","T"),1) * 1000;

CAPRI's GAMS, ManureNPK_ (l. 935-955; the manure trade of ManureTradeNew is on in CAPRI's 2030 Green Deal step):

    ManureNPK_(RUNR,FNUT) $ SUM( MAACT $ p_technFact(RUNR,MAACT,"LEVL","T"),1) ..

             v_ManureNPK(RUNR,FNUT)

    $iftheni.ManureTrade  %ManureTrade% == on
             + sum(runr1, v_ManureNPKintraTrade(RUNR,runr1) * p_NPKShareinManure(RUNR,FNUT))
    $endif.ManureTrade

    $iftheni.ManureTradeNew  %ManureTradeNew% == on
            + SUM( FOUT_T_N(FOUT,FNUT), v_manureExports(runr,fout) - v_manureImports(runr,fout))
    $endif.ManureTradeNew

               =E= SUM( FOUT_T_N(FOUT,FNUT),v_manExportOrAppl(RUNR,FOUT));

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

CAPRI's GAMS, fertDistMine_ (l. 1093-1099):

       fertDistMine_(RUNR,FNUT) $ SUM( (CACT_TO_NGRP(MCACT,NGRP),A) $ [p_technFact(RUNR,MCACT,"LEVL",A) and %data%(RUNR,MCACT,"levl","Y")], 1) ..

           SUM(NGRP
                $ SUM((CACT_TO_NGRP(MCACT,NGRP),A) $ [p_technFact(RUNR,MCACT,"LEVL",A) and %data%(RUNR,MCACT,"levl","Y")], 1),
                    v_fertDist(RUNR,NGRP,FNUT,"Mine"))

                =E= -v_netPutQuant(RUNR,FNUT)*1000;

CAPRI's GAMS, NUTNED_ (l. 1103-1220):

       NUTNED_(RUNR,NGRP,FNUT) $ SUM( (CACT_TO_NGRP(MCACT,NGRP),A) $ [p_technFact(RUNR,MCACT,"LEVL",A) and %data%(RUNR,MCACT,"levl","Y")], 1) ..

         SUM( (CACT_TO_NGRP(MCACT,NGRP),A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
            * (%data%(RUNR,MCACT,FNUT,"Y")
    $iftheni.till1 %ghgAbatement%==on
            * v_yldMit(RUNR,MCACT)
    $endif.till1
    $iftheni.Pes5 %PEST_DISAGG%==ON
            * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes5
               * (1-p_nitrFact(RUNR,MCACT,"BioFix") $ SAMEAS(FNUT,"NITF")
    $iftheni.fertn1 %ghgAbatement%==on
               * sum(R_RAGG(RUNR,MSACT),1. + (  p_ghgMiti(MSACT,MCACT,"LegSh","othImpact","BioFix")
                                              * v_Miti(RUNR,MCACT,"LegSh","BioFix")) $ SAMEAS(MCACT,"OFAR"))
    $endif.fertn1
               )
                * v_cropNutNeedMultFact(RUNR,FNUT,A)
                + v_cropNutNeedAddFact(RUNR,FNUT))
               * (p_nitrFact(RUNR,"ALL","DEFR") $ SAMEAS(FNUT,"NITF") + 1 $ (NOT SAMEAS(FNUT,"NITF")))
                                 * SQRT(
                                        [1.+p_technFact(RUNR,MCACT,"Yield",A)
                                            + 0.2 $ SAMEAS(MCACT,"GRAI") - 0.2 $ SAMEAS(MCACT,"GRAE")
                                        ] $ %data%(RUNR,MCACT,FNUT,"Y")
                                       )
                                *(p_technFact(RUNR,MCACT,FNUT,A)+1.)
           ) =E=
          + v_fertDist(RUNR,NGRP,FNUT,"Mine") * (1.-v_emiLoss(RUNR,"NETF","N","GasRunTot") $ SAMEAS(FNUT,"NITF") )
    $iftheni.fertn2 %ghgAbatement%==on
                                              * (1. + ( sum((R_RAGG(RUNR,MSACT),AllTechFert),
                                                           ( v_Miti(RUNR,"cropMiti",AllTechFert,"N2OSYN")
                                                           * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NMIN")
                                                            + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NMIN")
                                                            $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NMIN")))))
    $ifi %calFert%==ON                                + v_fertDist(RUNR,"free",FNUT,"fert_red")
                                                      ) $ SAMEAS(FNUT,"NITF") )
    $endif.fertn2
          + v_fertDist(RUNR,NGRP,FNUT,"Excr")

          * (  SUM( FOUT_T_N(FOUT,FNUT),v_nutAvailFactExcr(RUNR,FOUT))
    $iftheni.dyn2 %endoManAvFact%==on
            +  ( v_ManureNPK(RUNR,FNUT) / sum(landTypesNoSlak, v_actLevl(RUNR,landTypesNoSlak,"T") * 0.001)
               - p_endoManAv(RUNR,"manPerHa",FNUT)) * p_endoManAv(RUNR,"slopeManAv",FNUT)
    $endif.dyn2
            )

    $iftheni.fertman %ghgAbatement%==on
                                              * (1. + ( sum((R_RAGG(RUNR,MSACT),AllTechFert),
                                                           ( v_Miti(RUNR,"cropMiti",AllTechFert,"N2OMAN")
                                                           * (p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NMAN")
                                                            + p_ghgMiti(MSACT,"cropMiti",AllTechFert,"othImpact","NMAN")
                                                            $ (not p_ghgMiti(RUNR,"cropMiti",AllTechFert,"othImpact","NMAN")))))
    $ifi %calFert%==ON                                + v_fertDist(RUNR,"free",FNUT,"fert_red")
                                                      ) $ SAMEAS(FNUT,"NITF") )
    $endif.fertman

          + (v_fertDist(RUNR,NGRP,FNUT,"Cres")
                * SUM( FOUT_T_N(FOUT,FNUT),v_nutAvailFactCRes(RUNR,FOUT))
                   * (1.-v_emiLoss(RUNR,"NETF","N2O","GasTot") $ SAMEAS(FNUT,"NITF") )) $ (NOT PERM_NGRP(NGRP))
          + SUM( (CACT_TO_NGRP(MCACT,NGRP),FOUT_T_N(FOUT,FNUT),A)
                   $ (p_technFact(RUNR,MCACT,"LEVL",A) and PERM_NGRP(NGRP)),
                        v_actLevl(RUNR,MCACT,A)
                         *( %data%(RUNR,MCACT,FOUT,"Y")
    $iftheni.Pes33 %PEST_DISAGG%==ON
                          +( %data%(RUNR,mCact,FOUT,"Y")
                           -(p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))
                          *(v_yldPestFac(RUNR,mCact,A) - 1) $ v_yldPestFac.range(RUNR,mCact,A)
    $endif.Pes33
                          )
                         * (p_technFact(RUNR,MCACT,FOUT,A)+1.)
                         * (1.-v_emiLoss(RUNR,"NETF","N2O","GasTot") $ SAMEAS(FNUT,"NITF") )
                         * v_nutAvailFactCRes(RUNR,FOUT));

In this project's notation, per nutrient n (N, P, K) and crop group g; x_gs the flow of source s (MINE, EXCR, CRES) to
g in t, sc_g the sum of the group's prior modes, the rows' scale:

    NUTNED_(g):      [ sum_c X_c need_cn  -  (sum_c X_c own_cn) eC ] / sc_g
                     - [ eM (1 + sum NMIN v_Miti) x_gMINE + aE (1 + NMAN v_Miti) x_gEXCR + eC x_gCRES ] / sc_g = 0
    fertDistMine_:   (sum_g x_gMINE - P) / Pscale = 0,       P = v_netPutQuant (purchases, t)
    fertDistExcr_:   (sum_g x_gEXCR - E) / sc_EXCR = 0,      E = ManureNPK_'s pool (t)
    fertDistCres_:   (sum_g x_gCRES - C) / sc_CRES = 0,      C = the residue and deposition pool (t)
    ManureNPK_:      E = sum_animals X_a MAN_a (1 - GasRunTot) + base trade + the N the ammonia options keep
    aE (endoManAvFact): v_nutAvailFactExcr + slope (E / land - manPerHa)

need_cn: the crop's need per ha (CAPRI's DATA(crop, FNUT) after fertned.gms, with its yield and technology factors and
the calibrated multiplier; fertilisation.py _npk_spec); own_cn: a permanent crop's own residues and deposition, which
CAPRI puts on the right-hand side and the model subtracts from the need (the same equation); eM = 1 - GasRunTot of
mineral N (RUNTOTNETF_, GASTOTNETF_, GASRUNTOTNETF_ as functions of the options: n_flow's block, written in
capri_regional_nlp.CapriRegionalNLP._netf_eff), eC = v_nutAvailFactCRes x (1 - N2O GasTot), aE = v_nutAvailFactExcr.

In this project's notation, the idled histosols' term of the right-hand side, t N with F in 1000 ha:

    fertDistCres_idlHis = F x MANN_idlHis,   MANN_idlHis = AtmDep (kg N/ha)

(p_technFact(iHis, MANN, A) = 0: one technology; v_yldMit and v_yldPestFac do not apply to an activity without output.)
Departures from CAPRI: none in the term; N only (CAPRI's MANP and MANK of the idled histosols are zero).

Departures from CAPRI: the rows are scaled (by the groups' and pools' prior modes and the purchases' scale); the
pools' $ conditions (a region without animals or crops) are the builder's (a pool without flows has no row).
"""
from __future__ import annotations


def NUTNED_(need, supply, inv_sc):
    """NUTNED_(r, g, n) (l. 1103-1220) as a scaled row, = 0: the group's need less the supply from its flows,
    (need - supply) / sc_g."""
    return need - supply * inv_sc


def NUTNED_ownCres(need, own, availFactCres):
    """NUTNED_'s delivery from a permanent group's own harvest residues and deposition (l. 1206-1219), moved to the
    need side: need - own x v_nutAvailFactCRes x (1 - N2O GasTot)."""
    return need - own * availFactCres


def NUTNED_availFact(source, availFactExcr, availFactMine, availFactCres, other=None, mitiMine=None, mitiExcr=None):
    """The factor of a flow from source MINE, EXCR or CRES in NUTNED_'s right-hand side: (1 - GasRunTot) of mineral N
    x (1 + sum v_Miti NMIN) (the fertiliser options), v_nutAvailFactExcr x (1 + v_Miti NMAN) (the inhibitor on
    manure), v_nutAvailFactCRes x (1 - N2O GasTot); mitiMine and mitiExcr the options' terms (N only), else None."""
    f_ = availFactExcr if source == "EXCR" else (availFactMine if source == "MINE" else availFactCres
                                                 if source == "CRES" else other)
    if source == "MINE" and mitiMine is not None:
        f_ = f_ * (1 + mitiMine)
    if source == "EXCR" and mitiExcr is not None:
        f_ = f_ * (1 + mitiExcr)
    return f_


def NUTNED_supply(factors_flows):
    """NUTNED_'s right-hand side: the sum over the group's flows of factor x v_fertDist (t)."""
    sup = 0
    for f_, x_ in factors_flows:
        sup = sup + f_ * x_
    return sup


def fertDistMine_(pool, v_netPutQuant, inv_Pscale):
    """fertDistMine_ (l. 1093-1099) as a scaled row, = 0: the mineral flows over the groups equal the purchases."""
    return (pool - v_netPutQuant) * inv_Pscale


def fertDistExcr_(pool, v_ManureNPK, inv_sc):
    """fertDistExcr_ (l. 878-890) as a scaled row, = 0: the manure flows over the groups equal ManureNPK_'s pool."""
    return (pool - v_ManureNPK) * inv_sc


def fertDistCres_(pool, Cres, inv_sc):
    """fertDistCres_ (l. 1049-1088) as a scaled row, = 0: the residue flows over the (non-permanent) groups equal the
    residue and deposition pool."""
    return (pool - Cres) * inv_sc


def ManureNPK_trade(v_ManureNPK, baseTrade):
    """ManureNPK_'s manure trade term at the calibration point (v_manureImports - v_manureExports at CAPRI's base,
    a level of the region; K167): added to the pool."""
    return v_ManureNPK + baseTrade


def ManureNPK_ammKept(v_ManureNPK, ammKept):
    """The N the ammonia options keep in the manure (manExportOrAppl_'s (1 - v_emiLoss(GasRunTot)) with the options'
    losses), added to the N pool."""
    return v_ManureNPK + ammKept


def fertDistCres_catc(Cres, catcBioFix):
    """fertDistCres_'s winter cover term (l. 1081-1087): the catch crops' BioFix N, added to the N residue pool."""
    return Cres + catcBioFix


def v_nutAvailFactExcr_endo(availFactExcr, slopeManAv, v_ManureNPK, land, manPerHa):
    """NUTNED_'s manure availability with endoManAvFact on (l. 1176-1184): v_nutAvailFactExcr + (ManureNPK / land -
    p_endoManAv(manPerHa)) x p_endoManAv(slopeManAv)."""
    return availFactExcr + slopeManAv * (v_ManureNPK / land - manPerHa)


def MANN_idlHis(AtmDep: float) -> float:
    """CAPRI's DATA(iHisCr | iHisGr, MANN): N from residues and deposition per ha of an idled histosol = the region's
    deposition per ha, p_nitrBalance(AtmDep) (kg N/ha)."""
    return float(AtmDep)


def fertDistCres_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of fertDistCres_'s right-hand side (l. 1049-1088): v_actLevl(iHis) x DATA(iHis, MANN),
    t N (v_actLevl in 1000 ha)."""
    return v_actLevl * MANN_idlHis(AtmDep)

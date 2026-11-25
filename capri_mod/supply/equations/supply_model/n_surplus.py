r"""CAPRI's nutrient surplus (supply/supply_model.gms l. 1272-1489 and 1791-1886): the soil surface N balance
(e_MINFERT, e_MTRADEHa, e_EXCRET, e_GASRUNANI, e_ATMOSD, e_CRESID, e_EXPPRD, e_BIOFIX, e_SURTOTHa), the input shares
of the N leaching (nminInputSh_, nmanInputSh_) and the surplus's limit SURTOT_REST_.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

CAPRI writes each term per ha of its land types (v_minfert, v_excret, ... in kg N/ha, the land sum(landTypesNoSlak,
v_actLevl) x 0.001 on the left), and e_SURTOTHa sums them. The model writes the terms in t N over the region: the
environmental accounts (capri_mod/environmental/nitrogen.py compute_nitrogen_balance, phosphorus.py for P2O5) sum them
by activity, and the regional QP's N-surplus row takes each activity's balance from the same function
(unit_nitrogen_balance; supply_module._build_constraints "N_balance"), so the row and the accounts compute one
expression. The NLP's row (SURTOT_REST_ below) replaces the row's mineral parts by the purchases (e_MINFERT
substituted: v_minfert x the land = -v_netPutQuant).

In the accounts: e_EXCRET, e_GASRUNANI, e_ATMOSD, e_CRESID, e_EXPPRD and e_BIOFIX below; e_MTRADEHa's two terms, the
base exports and imports (supply.manure_base_trade "capri", K167), stay apart in compute_nitrogen_balance (the excretion
less the exports, the imports); e_SURTOTHa's sum is compute_nitrogen_balance's total inputs less the removal. The
idled histosols' terms (K184; see nutrients.py for the activities): an idled hectare keeps its deposition in the N
surplus, e_ATMOSD summing v_actLevl x AtmDep over MCACT and e_CRESID making v_Cresid + v_atmosd the sum of v_actLevl x
MANN over MCACT; for an idled histosol MANN = AtmDep, its deposition, and no residues (SURTOT_idlHis).

Not written: e_SURSOIkt (l. 1277-1279), e_GASRUNMIN (l. 1346-1355), e_GASRES (l. 1358-1377) and e_SURSOIHa
(l. 1478-1487), CAPRI's soil surplus SURSOI. Its reader in the Green Deal step is NO3LEA_ (l. 3592-3596, the emission
block: the leached N, v_nutSurSoiKt x v_nitrBalance(Leach)); the model computes the leached N by source, each net of
its own losses, as CAPRI's accounts do (envind/gases.gms l. 696-745; supply/n_leaching.py crop_n). SURSOI_REST_
(l. 1858-1862) is empty in the Green Deal step: no SURSOI target (surptot.gms sets DATA(SURTOT, MAXS) only;
p_envConst(SURSOI) is set in envind/envConstraints.gms, read only with envConst on, off in the step).
"""
from __future__ import annotations

from capri_mod.supply.equations.supply_model.nutrients import MANN_idlHis


def e_EXCRET(v_actLevl, MANN):
    r"""e_EXCRET(r, FNUT) (l. 1305-1317) in the accounts: an animal activity's nutrient excretion, v_actLevl x its
    excretion per head (t with v_actLevl in 1000 head, MANN in kg per head; environmental/ghg.py _n_excretion for N,
    fert/npk.py manure_per_head for P2O5).

    CAPRI's GAMS, e_EXCRET (l. 1305-1317):

       e_EXCRET(Runr,FNUT)  ..
             (v_excret(runr,FNUT) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 )
             =e=
         v_ManureNPK(RUNR,FNUT)
        + (v_manureNetExportHa(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001)
    *      --- add gaseous emissions from manure.
    *          Note that GASRUNTOT below includes total gaseous emissions (GASTOT) and total run-off (RUNTOT)
        + (v_gasrunani(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001);

    In this project's notation, for an animal a with level h_a and excretion per head MANN_a:

        e_EXCRET:  EXCRET_a = h_a x MANN_a

    Departures from CAPRI: none in the total. CAPRI writes v_excret as the manure applied (ManureNPK_) plus the net
    exports (e_MTRADEHa) plus the losses in housing and storage (e_GASRUNANI), each a part of the excretion, so the sum
    is the excretion; the model takes the excretion and derives the parts from it (compute_nitrogen_balance's
    n_manure_applied, the trade, n_manure_housing_loss).
    """
    return v_actLevl * MANN


def e_GASRUNANI(v_actLevl, MANN, GasRunTot):
    r"""e_GASRUNANI(r, FNUT) (l. 1322-1343) in the accounts: an animal activity's N lost in housing and storage,
    v_actLevl x its excretion per head x the share lost (CAPRI's v_emiLoss(MAACT, N, GasRunTot); t N).

    CAPRI's GAMS, e_GASRUNANI (l. 1322-1343):

       e_GASRUNANI(runr,FNUT)  ..
        v_gasrunani(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
      + SUM( FOUT_T_N(FOUT,FNUT),
    *
        SUM( MAACT $ p_technFact(RUNR,MAACT,"LEVL","T"),
              v_actLevl(RUNR,MAACT,"T") * %data%(RUNR,MAACT,FOUT,"Y")
                        *(p_technFact(RUNR,MAACT,FOUT,"T")+1.)
                        *(v_emiLoss(RUNR,MAACT,"N","GasRunTot") $ SAMEAS(FOUT,"MANN"))
    $iftheni.gasrunt %ghgAbatement%==on
    *                                          -- considering a possible modification by mitigation option lowNFeed
                       * (1 + v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN")
                            $ SAMEAS(FOUT,"MANN"))
    *                                           -- considering a possible modification by mitigation option rumFedEff
                       * (1 + v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN")
                            $ SAMEAS(FOUT,"MANN"))
    *                                          -- considering a possible modification by mitigation option mlkYld
                       * (1 + v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact",FOUT)
                            $ PACT_TO_Y(MAACT,"COMI"))
    $endif.gasrunt
                * 0.001));

    In this project's notation, for an animal a (g_a the share of its excretion lost before application):

        e_GASRUNANI:  GASRUNANI_a = h_a x MANN_a x g_a

    Departures from CAPRI: the accounts' share g_a is CAPRI's 2030 reference, (GASANI + RUNANI) / MANN by animal
    (manure_housing_losses_2030.csv, environmental/ghg.py _manure_loss_shares), without the options' factors (lowNFeed,
    rumFedEff, mlkYld) and without the cascade's change (the regional NLP's ManureNPK_ has both: n_flow.py).
    """
    return v_actLevl * MANN * GasRunTot


def e_ATMOSD(v_actLevl, AtmDep):
    r"""e_ATMOSD(r, FNUT) (l. 1381-1389) in t N: the land x the deposition per ha p_nitrBalance(AtmDep) (kg N/ha;
    v_actLevl in 1000 ha). The accounts take the region's crop land summed (compute_nitrogen_balance) and the idled
    histosols' levels (SURTOT_idlHis, environmental_module.py).

    CAPRI's GAMS, e_ATMOSD (l. 1381-1389):

       e_ATMOSD(runr,FNUT)  ..
             v_atmosd(runr,FNUT) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
        + SUM( FOUT_T_N(FOUT,FNUT),
           SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A),
                       v_actLevl(RUNR,MCACT,A)
                       * p_nitrBalance(RUNR,"AtmDep")))
             * 0.001;

    In this project's notation (x_c the crops' levels, d the deposition per ha):

        e_ATMOSD:  ATMOSD = (sum_c x_c) x d

    Departures from CAPRI: none (the model sums the land before the product).
    """
    return v_actLevl * AtmDep


def e_CRESID(v_actLevl, CRESID, yldFac):
    r"""e_CRESID(r, FNUT) (l. 1393-1414) for one crop in the accounts: v_actLevl x its residues per ha (MANN less the
    deposition, which e_ATMOSD carries) x the yield factor (t with v_actLevl in 1000 ha, CRESID in kg per ha).

    CAPRI's GAMS, e_CRESID (l. 1393-1414):

       e_CRESID(runr,FNUT)  ..
             (v_Cresid(runr,FNUT) + v_atmosd(runr,fnut))
             * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001
             =e= 0
             + SUM( (FOUT_T_N(FOUT,FNUT),MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A),v_actLevl(RUNR,MCACT,A)
                      *  (%data%(RUNR,MCACT,FOUT,"Y")
    $iftheni.till13 %ghgAbatement%==on
                         +  (%data%(RUNR,mcact,FOUT,"Y")-(p_nitrBalance(RUNR,"AtmDep")+p_nitrBalance(RUNR,"Mineralis"))
                                                        $ sameas(fout,"mann"))
                         *  (v_yldMit(RUNR,MCACT) - 1)
    $endif.till13
    $iftheni.Pes8a %PEST_DISAGG%==ON
                      +  (%data%(RUNR,mCact,FOUT,"Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) $ sameas(fout,"mann"))
                      *  (v_yldPestFac(RUNR,mCact,A) - 1) $ v_yldPestFac.range(RUNR,mCact,A)
    $endif.Pes8a
                         )
                      * (p_technFact(RUNR,MCACT,FOUT,A)+1.)
             )* 0.001
             ;

    In this project's notation, for a crop c with level x_c, residues per ha r_c at the base yield and the yield
    ratio y_c / y0_c:

        e_CRESID:  CRESID_c = x_c x r_c x y_c / y0_c

    Departures from CAPRI: the residues per ha are CAPRI's 2030 reference coefficients (environmental/nitrogen.py
    _capri_crop_n: MANN - AtmDep, scaled to the region's CRESID; PCRD for P2O5), and the whole coefficient moves with the
    yield ratio, where CAPRI scales its part above deposition and mineralisation by v_yldMit (ghgAbatement) and
    v_yldPestFac (PEST_DISAGG).
    """
    return v_actLevl * CRESID * yldFac


def e_EXPPRD(v_actLevl, DATA_FNUT, yldFac):
    r"""e_EXPPRD(r, FNUT) (l. 1417-1434) for one crop in the accounts: v_actLevl x its nutrient removal per ha x the
    yield factor (t with v_actLevl in 1000 ha, DATA_FNUT in kg per ha).

    CAPRI's GAMS, e_EXPPRD (l. 1417-1434):

       e_EXPPRD(runr,FNUT)  ..
             v_expprd(runr,fnut) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
    *
    *        --- deduct nutrient export with harvested material (EXPPRD) and crop residues minus biological fixation (BIOFIX)
    *
           + SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                      * %data%(RUNR,MCACT,FNUT,"Y") * (p_technFact(RUNR,MCACT,FNUT,A)+1.)
    $iftheni.till7 %ghgAbatement%==on
    *        --- mitigation effect on yield considered
                 * v_yldMit(RUNR,MCACT)
    $endif.till7
    $iftheni.Pes10 %PEST_DISAGG%==ON
                      * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes10
                ) * 0.001
           ;

    In this project's notation, for a crop c with level x_c, removal per ha e_c at the base yield and the yield
    ratio y_c / y0_c:

        e_EXPPRD:  EXPPRD_c = x_c x e_c x y_c / y0_c

    The removal per ha is CAPRI's simulation DATA(crop, NITF, "Y"), as fert/fertned.gms rebuilds it in the simulation
    year (capri_mod/supply/equations/fertned.py DATA_FNUT_yield; environmental/nitrogen.py _capri_crop_n, data_nitf of
    capri_crop_n_coefs_2030.csv: the regions' removal is CAPRI's EXPPRD within 0.1%; K191; PRET for P2O5).

    Departures from CAPRI: moved by the yield ratio where CAPRI multiplies by v_yldMit and v_yldPestFac.
    """
    return v_actLevl * DATA_FNUT * yldFac


def e_BIOFIX(v_actLevl, BioFix, yldFac):
    r"""e_BIOFIX(r, FNUT) (l. 1438-1461) for one crop in the accounts: v_actLevl x its biological N fixation per ha x
    the yield factor (t N with v_actLevl in 1000 ha, BioFix in kg N per ha). The catch crops' term,
    p_ghgMiti(CATC, WinterCov, othImpact, BioFix) x v_actLevl(CATC), is nutrients.py fertDistCres_catcBioFix (the same
    product in fertDistCres_), which SURTOT_REST_ takes as catcBioFix.

    CAPRI's GAMS, e_BIOFIX (l. 1438-1461):

       e_BIOFIX(runr,fnut)  ..
             v_biofix(runr,fnut) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
           + (p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"catc","T")) $ SAMEAS(FNUT,"NITF")
           + SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                      * %data%(RUNR,MCACT,FNUT,"Y")
                      * (p_technFact(RUNR,MCACT,FNUT,A)+1.)
    $iftheni.till8 %ghgAbatement%==on
    *                  mitigation effect on yield considered
                     * v_yldMit(RUNR,MCACT)
    $endif.till8
    $iftheni.Pes10a %PEST_DISAGG%==ON
                      * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes10a
                     * (p_nitrFact(RUNR,MCACT,"BioFix") $ SAMEAS(FNUT,"NITF")
    $iftheni.fertn3 %ghgAbatement%==on
                     * sum(R_RAGG(RUNR,MSACT),1. + (  p_ghgMiti(MSACT,MCACT,"LegSh","othImpact","BioFix")
                                                    * v_Miti(RUNR,MCACT,"LegSh","BioFix")) $ SAMEAS(MCACT,"OFAR"))
    $endif.fertn3
                       )
                ) * 0.001
     ;

    In this project's notation, for a crop c with level x_c, fixation per ha f_c at the base yield and the yield ratio
    y_c / y0_c:

        e_BIOFIX:  BIOFIX_c = x_c x f_c x y_c / y0_c

    The fixation per ha is CAPRI's DATA(crop, NITF, "Y") x p_nitrFact(crop, BioFix) of the simulation year
    (capri_mod/supply/equations/fertned.py, fertpar.py p_nitrFact_BioFix: the member state's grassland rate, other arable
    fodder's legume mix; data_nitf x biofix_rate of capri_crop_n_coefs_2030.csv; K191).

    Departures from CAPRI: moved by the yield ratio where CAPRI multiplies by v_yldMit and v_yldPestFac; the LegSh
    option's factor on OFAR is not in the model.
    """
    return v_actLevl * BioFix * yldFac


def e_BIOFIX_legSh(BIOFIX_OFAR, othImpact_BioFix, v_Miti):
    r"""e_BIOFIX's legume share term (l. 1456-1457) for other arable fodder, t N: its fixation at v = 0 x othImpact x v,
    BIOFIX_OFAR = sum over OFAR's technologies of v_actLevl x DATA(NITF) x (1 + p_technFact(NITF, A)) x BioFix
    (e_BIOFIX above), othImpact the member state's (equations/leg_share.py othImpact_BioFix_LegSh), v = v_Miti(OFAR,
    LegSh, BioFix). In the N-surplus row and the accounts' fixation.

    CAPRI's GAMS of e_BIOFIX: e_BIOFIX's docstring. Departures from CAPRI: none."""
    return BIOFIX_OFAR * othImpact_BioFix * v_Miti


def nminInputSh_den(nminKept, ManureNPK, MANN, N2O):
    r"""The N input to the soil that nminInputSh_ and nmanInputSh_ (l. 1789-1851) share out (t N): the mineral N kept
    (-v_netPutQuant(NITF) x (1 - v_emiLoss(NETF, N, GasRunTot))), the manure applied (v_ManureNPK(NITF)), the crops'
    residues and deposition (CAPRI's MANN sum) x (1 - v_emiLoss(NETF, N2O, GasTot)).

    CAPRI's GAMS of the two equations: nminInputSh_'s and nmanInputSh_'s docstrings.

    In this project's notation (M the mineral N, g its GasRunTot share, A the manure applied, R the residues and
    deposition, n the N2O share):

        den = M (1 - g) + A + R (1 - n)

    Departures from CAPRI: the catch crops' BioFix term, p_ghgMiti(CATC, WinterCov, othImpact, BioFix) x
    v_actLevl(CATC), is not in the model's sum (the accounts' leaching, environmental/nitrogen.py leaching).
    """
    return nminKept + ManureNPK + MANN * (1.0 - N2O)


def nminInputSh_(nminKept, den):
    r"""nminInputSh_(r) (l. 1789-1819): v_nminInputSh, the mineral N kept over the N input (nminInputSh_den); 0 without
    input. LEACHN_ weighs the fertiliser options' effect on mineral N with it (n_flow.py LEACHN_B1).

    CAPRI's GAMS, nminInputSh_ (l. 1789-1819):

           nminInputSh_(RUNR) ..
    *
            -v_netPutQuant(RUNR,"NITF") * (1.-v_emiLoss(RUNR,"NETF","N","GasRunTot"))
            =E= v_nminInputSh(RUNR)
    *
    *        --- import by mineral fertiliser minus v_lossQuant as ammonia
    *
           * { -v_netPutQuant(RUNR,"NITF") * (1.-v_emiLoss(RUNR,"NETF","N","GasRunTot"))
    *
    *        --- output of nutrient "at tail" from animals minus Ammonia v_lossQuant
    *
          + v_ManureNPK(RUNR,"NITF")
    *
    *        --- atmospheric deposition and crop residues
    *
          +    SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                      *  (   %data%(RUNR,MCACT,"mann","Y")
                         +  (%data%(RUNR,mcact,"mann","Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")))
                         *  (v_yldMit(RUNR,MCACT) - 1)
    $iftheni.Pes11 %PEST_DISAGG%==ON
                         +  (%data%(RUNR,mCact,"mann","Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")) )
                         *  (v_yldPestFac(RUNR,mCact,A)- 1) $ v_yldPestFac.range(RUNR,mCact,A)
    $endif.Pes11
                         ) * (p_technFact(RUNR,MCACT,"mann",A)+1.)
                  )   * (1.-v_emiLoss(RUNR,"NETF","N2O","GasTot")) * 0.001
    *        --- N imports via biofixation of wintercover crops
           + [p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"CATC","T")]}
    ;

    In this project's notation (nminInputSh_den's): nminSh = M (1 - g) / den.

    Departures from CAPRI: nminInputSh_den's.
    """
    return nminKept / den if den > 0 else 0.0


def nmanInputSh_(ManureNPK, den):
    r"""nmanInputSh_(r) (l. 1821-1851): v_nmanInputSh, the manure applied over the N input (nminInputSh_den); 0 without
    input. LEACHN_ weighs the fertiliser options' effect on manure with it (n_flow.py LEACHN_B1).

    CAPRI's GAMS, nmanInputSh_ (l. 1821-1851):

           nmanInputSh_(RUNR) ..
    *
            v_ManureNPK(RUNR,"NITF")
            =E= v_nmanInputSh(RUNR)
    *
    *        --- import by mineral fertiliser minus v_lossQuant as ammonia
    *
           * { -v_netPutQuant(RUNR,"NITF") * (1.-v_emiLoss(RUNR,"NETF","N","GasRunTot"))
    *
    *        --- output of nutrient "at tail" from animals minus Ammonia v_lossQuant
    *
          + v_ManureNPK(RUNR,"NITF")
    *
    *        --- atmospheric deposition and crop residues
    *
          +    SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                      *  (  %data%(RUNR,MCACT,"mann","Y")
                         +  (%data%(RUNR,mcact,"mann","Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")))
                         *  (v_yldMit(RUNR,MCACT) - 1)
    $iftheni.Pes12 %PEST_DISAGG%==ON
                         +  (%data%(RUNR,mCact,"mann","Y") - (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis")))
                         *  (v_yldPestFac(RUNR,mCact,A) - 1) $ v_yldPestFac.range(RUNR,mCact,A)
    $endif.Pes12
                         ) * (p_technFact(RUNR,MCACT,"mann",A)+1.)
                  )   * (1.-v_emiLoss(RUNR,"NETF","N2O","GasTot")) * 0.001
    *        --- N imports via biofixation of wintercover crops
           + [p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"CATC","T")]}
    ;

    In this project's notation (nminInputSh_den's): nmanSh = A / den.

    Departures from CAPRI: nminInputSh_den's.
    """
    return ManureNPK / den if den > 0 else 0.0


def SURTOT_idlHis(v_actLevl, AtmDep: float):
    """The idled histosols' part of the N surplus in t (e_SURTOTHa x UAAR): their e_ATMOSD term, v_actLevl x AtmDep;
    their e_CRESID term, v_actLevl x (MANN - AtmDep), is zero.

    CAPRI's GAMS of e_ATMOSD and e_CRESID: their functions' docstrings above. e_SURTOTHa (l. 1463-1475):

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
    return e_ATMOSD(v_actLevl, float(AtmDep)) + e_CRESID(v_actLevl, MANN_idlHis(AtmDep) - float(AtmDep), 1.0)


def SURTOT_REST_(rest, v_netPutQuant, inv_rs, catcBioFix):
    """SURTOT_REST_ with e_SURTOTHa (l. 1867-1871, 1463-1475) as the NLP's scaled row, <= b / rs: the surplus terms
    without the mineral N (scaled, from the regional QP's row), + the purchases / rs, + the catch crops' BioFix (scaled;
    0 without catch crops).

    CAPRI's GAMS, SURTOT_REST_ (l. 1867-1871; the Green Deal's surplus target, pol_input/greendeal/surptot.gms):

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
    return rest + v_netPutQuant * inv_rs + catcBioFix

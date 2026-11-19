r"""CAPRI's premiums block (supply/supply_model.gms l. 1887-2026): the CAP's greening and conditionality rows and the
winter cover requirement.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview and departures.

Written so far: the catch crops' rows of the regional NLP (CapriRegionalNLP._abatement_block, ghgAbatement on): the
winter cover requirement (winterCover_), the catch crop area from the option's share (catcMiti_) and the catch crops'
term in the ecological set-aside (ecoSetAside_; its other terms: capri_regional_nlp.py "CAP greening"). The catch
crops' lower bound, e_minCoverCrops (set_aside.py's block, l. 2368-2370), and their upper bound, Tot_soilCov_
(mitigation.py's block), are the share's bounds.

CAPRI's ecoSetAside_ and cropDivGreening_ are in its model only with envConst on (supply_model_e_list_linear.gms
l. 235-236), and envConst is off in the Green Deal step (pol_input/greendeal/refpol_endotech_all_sup.gms: the $exit at
l. 398 comes before its setglobal envConst on at l. 408; the default, capmod/set_global_variables.gms l. 244). The model
writes both rows in its Green Deal runs and in the 2030 reference: a porting gap for the main line (KNOWN_ISSUES K187),
kept by this move (ecoSetAside_catc moves the catch crops' term as it is).

In this project's notation: m the catch crops' share of the UAA (v_Miti(CATC, winterCov, co2seq)), U the region's UAA
(spec catc "uaa"), y the activity levels.

Two porting differences from CAPRI's equations (not departures; KNOWN_ISSUES K186, fixed on the main line; this move
keeps them, the refactor's results staying identical):
1. The catch crop area on the base area: CAPRI's catcMiti_ scales it with the current land (sum over landTypesNoSlak
   of v_actLevl, a variable), and GHG_Mit_Cost_ charges winter cover on v_actLevl(uaaEqu); the model takes the base
   UAA, U, a fixed number (the base crop levels' sum, supply/abatement.py), for the area in winterCover_, the cost, the
   ecoSetAside_ term and the BioFix N in fertDistCres_.
2. winterCover_'s limit: CAPRI's is DATA(UAAR) plus the fallow floor; the model's is max(U + the fallow floor, the base
   cover + m0 U), whose max() is not in CAPRI (it keeps the base point feasible where the data would break the
   inequality).
"""
from __future__ import annotations


def catcMiti_(uaaEqu, v_Miti):
    r"""catcMiti_(r) (l. 2016-2021): the catch crop area, v_actLevl(CATC) = v_Miti(CATC, winterCov, co2seq) x the land
    (1000 ha); the model's land is the base UAA (the departure above).

    CAPRI's GAMS, catcMiti_ (l. 2016-2021):

        catcMiti_(runr) ..
    $ifi      %catcmiti_operator%==g v_actlevl(runr,"CATC","T") =g=
    $ifi  not %catcmiti_operator%==g v_actlevl(runr,"CATC","T") =e=
          v_miti(runr,"CATC","winterCov","co2seq")* sum(landTypesNoSlak, v_actLevl(RUNR,landTypesNoSlak,"T"));
    """
    return uaaEqu * v_Miti


def winterCover_(v_coverCrops, v_actLevl_CATC, inv_uaa):
    r"""winterCover_(r) (l. 1990-2003) as the NLP's row: the regular crops' winter cover plus the catch crops at most
    the UAA (+ the fallow floor), (sum_c p_winterCoverShare(c) v_actLevl(c) + v_actLevl(CATC)) / U <= (UAAR + floor) / U.
    v_coverCrops: the crops' winter cover (the spec's row coefficients on y); v_actLevl_CATC: catcMiti_; inv_uaa: 1 / U.

    CAPRI's GAMS, winterCover_ (l. 1990-2003):

        winterCover_(runr) ..
          %data%(runr,"UAAR","LEVL","Y")  - SUM( (mcact,A) $ p_technFact(runr,mcact,"LEVL",A),
                           v_actLevl(runr,mcact,A) * p_winterCoverShare(runr,mcact))
          + (%data%(RUNR,"FALL","FLOOR","Y") $ (%data%(RUNR,"FALL","FLOOR","Y") gt eps))
                                =G= v_actLevl(runr,"CATC","T") ;
    """
    return (v_coverCrops + v_actLevl_CATC) * inv_uaa


def ecoSetAside_catc(row, weight, v_Miti):
    r"""The catch crops' term of ecoSetAside_(r) (l. 1948-1984): CATC is in setaEco, the eligible side, at CAPRI's
    greening weight p_DPgreeningWeight(CATC); in the NLP's scaled row (the eligible side subtracted), row - weight x m,
    weight = p_DPgreeningWeight(CATC) x U / the row's scale. ecoSetAside_ is empty in CAPRI's Green Deal step (K187,
    the module's docstring).

    CAPRI's GAMS, ecoSetAside_ (l. 1948-1984):

       ecoSetAside_(runr) $  (
                                    p_DPGreeningLimits(runr,"ecoSetAside")
                                  $ %data%(runr,"ARAB","LEVL","Y")) ..
    $iftheni.efabasis2 not %greening_efabasis% == ARAB
        SUM( (arbAct,A) $ (p_technFact(runr,arbAct,"LEVL",A)),
                           v_actLevl(runr,arbAct,A) * 0.01 * p_DPGreeningLimits(runr,"ecoSetAside")
                           /(1.-0.01 * p_DPGreeningLimits(runr,"ecoSetAside")))
    $else.efabasis2
        SUM( (annualCrops,A) $ (p_technFact(runr,annualCrops,"LEVL",A)),
                           v_actLevl(runr,annualCrops,A) * 0.01 * p_DPGreeningLimits(runr,"ecoSetAside")
                           /(1.-0.01 * p_DPGreeningLimits(runr,"ecoSetAside")))
    $endif.efabasis2
          =L=
        SUM( (setaEco,A) $ p_technFact(RUNR,setaEco,"LEVL",A),
              v_actLevl(RUNR,setaEco,A) * p_DPgreeningWeight(runr,setaEco)
              * (1 - (1-DATA(RUNR,"FLEG","LEVL","Y"))$(SAMEAS(setaeco,"OFAR"))) )
             ;
    """
    return row - weight * v_Miti

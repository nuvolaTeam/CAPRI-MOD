r"""CAPRI's methane block (supply/supply_model.gms l. 3044-3188): CH4 from enteric fermentation (GWPCH4ENT_), manure
management (GWPCH4MAN_) and rice (GWPCH4RIC_), and their total (GWPCH4_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

In CAPRI's supply model these are definitional rows, binding only under an emission price or cap. The model computes
them in the accounts after the solve (capri_mod/environmental/ghg.py compute_ghg, environmental_module.py
compute_indicators), and supply/ghg_tax.py takes the emission tax's coefficients from the accounts (the project lead's
decision of 19 November 2026, option A: CAPRI's equations here, called by the accounts and ghg_tax.py). With
debugCO2Equ on (supply_model.gms l. 71, the Green Deal step) CAPRI writes each per activity (GWPCH4ENTaact_,
GWPCH4MANaact_) and sums them over the levels (GWPCH4ENT_, GWPCH4MAN_); the model's accounts do the same per animal.

Not in the model: GWPCH4RIC_ (l. 3161-3169), CH4 from rice: the model has rice (PARI) but no rice CH4 in its accounts
(GHG_TYPES, capri_mod/data/definitions.py); a finding for the main line.

In this project's notation, for an animal a with heads H_a (= 1000 x its level), CAPRI's tier-1 CH4 per head e_a
(EMISCALC, kg; the model's livestock_ch4ent_coef.csv, livestock_ch4man_coef.csv), for cattle its feeds' dry matter
D_f (t) and gross energy GE_f (Mcal per kg DM), the methane conversion Ym:

    GWPCH4ENTaact_  e_a x n_a x s_a                                   (kg per head; n_a the nitrate's factor, s_a the
                                                                       supplements', the options' MC_GHG_Miti_Factor)
                    sum_f D_f 1000 GE_f x 4.1868 Ym / 55.65 / 1e6 x n_a x s_a      (cattle: kt for the herd)
    GWPCH4ENT_      sum_a H_a x GWPCH4ENTaact_a / 1e6                 (kt CH4; x GWP for CO2-eq)
    GWPCH4MAN_      sum_a H_a x e_a / 1e6, x the anaerobic digestion's factor (GWPCH4MAN_miti)

Departures from CAPRI: the cattle's enteric CH4 from the feed mix follows CAPRI's p_emisFeed (envind/gases.gms
l. 367-375) on the feeds' dry matter (the regional NLP's rations, feed_dm); the covers' and low-emission housing's
effects on manure CH4 (CovStorLow, CovStorHigh, AirPurCovLow, AirPurCovHigh, LowEmHous: othImpact CH4MAN) are not in
the accounts; ghg_tax.py writes the enteric factor per t of dry matter in its own order of operations
(GWPCH4ENTaact_feedCoef; the accounts: GWPCH4ENTaact_feed), the same value to rounding.
"""
from __future__ import annotations

from capri_mod.params import param
from capri_mod.units import MJ_PER_MCAL


def GWPCH4ENTaact_(EMISCALC, nitr, supp):
    r"""GWPCH4ENTaact_(r, a, A) (l. 3078-3092) for a non-cattle animal (CAPRI's tier 1): the enteric CH4 per head
    EMISCALC(CH4ENT) (kg) x the options' factors: nitr, the nitrate's (1 - 10% per point of the ration's dry matter,
    NITRATE_CH4_REDUCTION), supp, the supplements' (environmental_module.py supp_ch4).

    CAPRI's GAMS, GWPCH4ENTaact_ (l. 3078-3092):

        GWPCH4ENTaact_(RUNR,MAACT,A)  ..  v_CO2EquEmisAact(RUNR,MAACT,"CH4ENT",A) =E=
    *
                SUM( R_RAGG(RUNR,MSACT) ,
    *                  Cattle depending on endogenous feed mix
                    [  SUM(FEED $ p_maxFeedShare(RUNR,MAACT,A,FEED),
                           p_emisFeed(RUNR,MAACT,A,FEED,"CH4ENT") * v_feedInpCoeff(RUNR,MAACT,A,FEED)) $ (CATACT(MAACT))
    *                  non cattle is calculated according to tier 1
                    +  EMISCALC(RUNR,MAACT,A,"CH4ENT","Y")                                             $ (NOT CATACT(MAACT)) ]
    *                  Influence of non dairy mitigation technologies
                    * [ (MC_GHG_Miti_Factor(MAACT,"CH4ENT") )                  $ (not (sameas(MAACT,"DCOL") or sameas(MAACT,"DCOH")))
    *                  Influence of Mitigation Technologies for Dairy Cattle
                     +  (MC_GHG_Miti_DCow(MAACT,"CH4ENT_3k","CH4ENT") )        $ (    (sameas(MAACT,"DCOL") or sameas(MAACT,"DCOH")))]
    *                  consider a reduction of energy need and emissions by up to 7% for sheep (not element of catAct) by option genet_eff:
                    * [ 1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","ENNE") $ PACT_TO_I(MAACT,"ILAM")]
                                 );
    """
    return EMISCALC * nitr * supp


def GWPCH4ENTaact_feed(kgGE, ym, nitr, supp):
    r"""GWPCH4ENTaact_'s cattle term, sum_f p_emisFeed(f, CH4ENT) x v_feedInpCoeff(f), for the herd (kt CH4): the
    feeds' gross energy kgGE = sum_f D_f x 1000 x GE_f (Mcal; D_f t of dry matter), x 4.1868 MJ per Mcal x Ym / 55.65
    MJ per kg CH4 (CAPRI's p_emisFeed, envind/gases.gms l. 367-375) / 1e6, x the options' factors (GWPCH4ENTaact_'s).
    CAPRI's GAMS: GWPCH4ENTaact_'s docstring."""
    return kgGE * MJ_PER_MCAL * ym / param("MJ_PER_KG_CH4") / 1e6 * nitr * supp


def GWPCH4ENTaact_feedCoef(ym, gwp):
    r"""p_emisFeed(f, CH4ENT) per Mcal of gross energy in CO2-eq, for supply/ghg_tax.py's coefficients per t of dry
    matter (GE_f x this): 4.1868 x Ym / 55.65 x GWP(CH4). CAPRI's GAMS: GWPCH4ENTaact_'s docstring."""
    return MJ_PER_MCAL * ym / param("MJ_PER_KG_CH4") * gwp


def GWPCH4ENT_(heads, aact):
    r"""GWPCH4ENT_(r) (l. 3074-3076) for one animal: heads x GWPCH4ENTaact_ (kg per head) / 1e6, kt CH4 (CAPRI:
    v_actLevl (1000 head) x v_CO2EquEmisAact x 0.001, in CO2-eq; the accounts multiply by GWP(CH4)).

    CAPRI's GAMS, GWPCH4ENT_ (l. 3074-3076):

        GWPCH4ENT_(RUNR)..   v_CO2EquEmis(RUNR,"CH4ENT") =E=
    *
               SUM( (MAACT,A) $ p_technFact(RUNR,MAACT,"LEVL",A), v_actLevl(RUNR,MAACT,A)*v_CO2EquEmisAact(RUNR,MAACT,"CH4ENT",A))*.001;
    """
    return heads * aact / 1e6


def GWPCH4MAN_(heads, EMISCALC):
    r"""GWPCH4MAN_(r) (l. 3134-3136) with GWPCH4MANaact_ (l. 3138-3148) for one animal: heads x CAPRI's manure CH4
    per head EMISCALC(CH4MAN) (kg) / 1e6, kt CH4; the anaerobic digestion's change: GWPCH4MAN_miti.

    CAPRI's GAMS, GWPCH4MAN_ (l. 3134-3136) and GWPCH4MANaact_ (l. 3138-3148):

        GWPCH4MAN_(RUNR)..   v_CO2EquEmis(RUNR,"CH4MAN") =E=
    *
               SUM( (MAACT,A) $ p_technFact(RUNR,MAACT,"LEVL",A), v_actLevl(RUNR,MAACT,A)*v_CO2EquEmisAact(RUNR,MAACT,"CH4MAN",A))*.001;
        GWPCH4MANaact_(RUNR,MAACT,A)  ..  v_CO2EquEmisAact(RUNR,MAACT,"CH4MAN",A) =E=
    *
                 SUM( R_RAGG(RUNR,MSACT) ,
                    EMISCALC(RUNR,MAACT,A,"CH4MAN","Y")
                    * (MC_GHG_Miti_Factor(MAACT,"CH4MAN")           $ (not (sameas(MAACT,"DCOL") or sameas(MAACT,"DCOH")))
                     + MC_GHG_Miti_DCow(MAACT,"CH4MAN_3k","CH4MAN") $ (    (sameas(MAACT,"DCOL") or sameas(MAACT,"DCOH"))))
                    * (1 - p_ghgMiti(RUNR,MAACT,"CovStorLow","othImpact","CH4MAN") * v_Miti(RUNR,MAACT,"CovStorLow","NH3MAN")
                         - p_ghgMiti(RUNR,MAACT,"CovStorHigh","othImpact","CH4MAN") * v_Miti(RUNR,MAACT,"CovStorHigh","NH3MAN")
                         - p_ghgMiti(RUNR,MAACT,"AirPurCovLow","othImpact","CH4MAN") * v_Miti(RUNR,MAACT,"AirPurCovLow","NH3MAN")
                         - p_ghgMiti(RUNR,MAACT,"AirPurCovHigh","othImpact","CH4MAN") * v_Miti(RUNR,MAACT,"AirPurCovHigh","NH3MAN")
                         - p_ghgMiti(RUNR,MAACT,"LowEmHous","othImpact","CH4MAN") * v_Miti(RUNR,MAACT,"LowEmHous","NH3MAN")));
    """
    return heads * EMISCALC / 1e6


def GWPCH4MAN_miti(v_actLevl, EMISCALC, gwp, factor):
    r"""GWPCH4MANaact_'s MC_GHG_Miti_Factor for the anaerobic digestion (AD_AnCh), as the change of the animal's
    manure CH4 in CO2-eq: v_actLevl (1000 head) x 1000 x EMISCALC / 1e6 x GWP x (factor - 1), factor the CH4 at the
    option's share against the base share (environmental/ghg.py _ad_ch4_factor). CAPRI's GAMS: GWPCH4MAN_'s
    docstring."""
    return v_actLevl * 1000.0 * EMISCALC / 1e6 * gwp * (factor - 1.0)

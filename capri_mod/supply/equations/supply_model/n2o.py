r"""CAPRI's N2O block (supply/supply_model.gms l. 3634-3966): N2O from manure (GWPN2OMAN_ with GWPN2OMANaact_,
GWPN2OAPP_, GWPN2OGRA_), mineral fertiliser (GWPN2OSYN_), crop residues (GWPN2OCRO_), volatilised N (GWPN2OAMM_),
histosols (GWPN2OHIS_) and leaching (GWPN2OLEA_), and their total (GWPN2O_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

As the methane block (methane.py): definitional rows in CAPRI's supply model, computed by the model's accounts after
the solve (environmental/ghg.py compute_ghg, environmental_module.py compute_indicators, environmental/nitrogen.py
leaching), whose total supply/ghg_tax.py takes for the emission tax (option A). The emission factors are CAPRI's
GHGEFS (envind/create_rawdat_gascoeff_gdx.gms l. 707-713): EF1A = EF4 = 0.01, EF5 = 0.0075 (the parameters
EF_SOIL_N2O_DIRECT, EF_SOIL_N2O_INDIRECT, EF5_LEACHING_N2O).

Not written: GWPN2O_ (l. 3949-3962), the N2O subtotal; its items enter the accounts' total (GWPTOT_, gwp.py) directly.

In this project's notation (t or kt of N, CO2-eq by x 44/28 x GWP(N2O)):

    GWPN2OMAN_ ...   N_a x (f_man + f_app + f_gra + f_lea)   N_a the animal's excreted N, f CAPRI's shares of the
                                                             stages (Hous + Stor, Appl, Graz; f_lea the housing
                                                             runoff's EF5 part), manure_n2o_factors.csv
    GWPN2OSYN_       M x (n + v)                              M the mineral N, n = v_emiLoss(NETF, N2O, GasTot),
                                                             v = (NH3 + NOx) x EF4: GWPN2OAMM_'s mineral term
    GWPN2OCRO_       R x EF1A                                 R the residues' N (and the catch crops' BioFix)
    GWPN2OAMM_       NH3-N x EF4                              the manure NH3 (the accounts' ammonia)
    GWPN2OHIS_       sum_l x_l e_l - the idled histosols' factor x their area
    GWPN2OLEA_       the leached and run-off N x EF5          (n_leaching.crop_n)

Departures from CAPRI: the manure stages are summed on one item (N2O_MAN) with CAPRI's 2017 shares, the options'
effects applied to it afterwards (environmental_module.py: the cascade's housing and application multipliers, the
inhibitor on manure), without the lowNFeed, genet_eff and genet_yld factors on MANN; GWPN2OAMM_'s manure term takes
NH3 only (CAPRI: NH3 + NOx of each stage); GWPN2OSYN_ and GWPN2OAMM_'s mineral term are one line, rescaled by the
fertiliser options' factors (fert_side_factors); GWPN2OCRO_'s residues are the N balance's CRESID (CAPRI: MANN -
AtmDep - Mineralis, less the burned, fuel and feed shares N2OREGIO); compute_ghg's own soil N2O (IPCC's EF1 and EF4
x FracGASF on the crops' base mineral rates) is replaced in compute_indicators by GWPN2OSYN_ on the balance's mineral
N.
"""
from __future__ import annotations

from capri_mod.units import M_N2O, M_N2O_N, M_NH3, M_NH3_N


def GWPN2OMAN_(N_excr, f):
    r"""GWPN2OMAN_(r) (l. 3663-3665) with GWPN2OMANaact_ (l. 3667-3677), GWPN2OAPP_ (l. 3687-3700), GWPN2OGRA_
    (l. 3704-3717) and the housing runoff's part of GWPN2OLEA_, for one animal: its excreted N (kt) x the sum of CAPRI's
    N2O-N shares of the stages f = (f_man, f_app, f_gra, f_lea) (kt N2O-N).

    CAPRI's GAMS, GWPN2OMAN_ and GWPN2OMANaact_ (l. 3663-3677):

        GWPN2OMAN_(RUNR)..   v_CO2EquEmis(RUNR,"N2OMAN") =E=
    *
               SUM( (MAACT,A) $ p_technFact(RUNR,MAACT,"LEVL",A), v_actLevl(RUNR,MAACT,A)*v_CO2EquEmisAact(RUNR,MAACT,"N2OMAN",A))*.001;
        GWPN2OMANaact_(RUNR,MAACT,A)  ..  v_CO2EquEmisAact(RUNR,MAACT,"N2OMAN",A) =E=
    *
                 SUM( R_RAGG(RUNR,MSACT) ,
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                        (  (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                         * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                         * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN")))
                            * %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * (v_emiloss(RUNR,MAACT,"N2O","Hous") + v_emiloss(RUNR,MAACT,"N2O","Stor"))) * 44/28;

    GWPN2OAPP_ (l. 3687-3700):

        GWPN2OAPP_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OAPP") =E=
    *
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                      * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                      * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                      * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                      *  %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * v_emiloss(RUNR,MAACT,"N2O","Appl")) * 44/28 * 0.001;

    GWPN2OGRA_ (l. 3704-3717):

        GWPN2OGRA_(RUNR) ..
    *
            v_CO2EquEmis(RUNR,"N2OGRA") =E=
    *
               SUM( (MAACT,A) $ ( p_technFact(RUNR,MAACT,"LEVL",A) ),  v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                      * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                      * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                      * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                      *  %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                                   * v_emiloss(RUNR,MAACT,"N2O","Graz")) * 44/28 * 0.001;
    """
    return N_excr * sum(f)


def GWPN2OSYN_(M_kt, n2o, vol, gwp):
    r"""GWPN2OSYN_(r) (l. 3721-3730) with GWPN2OAMM_'s mineral term (l. 3793-3810) in CO2-eq: the mineral N (kt) x
    (the N2O share n + the volatilised share x EF4, v) x 44/28 x GWP(N2O) (environmental/nitrogen.py _mineral_n2o_n:
    the region's MITERRA loss fractions, CAPRI's v_emiLoss(NETF)).

    CAPRI's GAMS, GWPN2OSYN_ (l. 3721-3730):

        GWPN2OSYN_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OSYN") =E=
    *
              - v_netPutQuant(RUNR,"NITF") * v_emiLoss(RUNR,"NETF","N2O","GasTot")
    *          * sum(R_RAGG(RUNR,MSACT),1. + v_Miti(RUNR,"CropMiti","Nitr_inh","N2OSYN") * (p_ghgMiti(RUNR,"cropMiti","Nitr_inh","othImpact","N2OSYN")
    *                                      + p_ghgMiti(MSACT,"cropMiti","Nitr_inh","othImpact","N2OSYN") $ (not p_ghgMiti(RUNR,"cropMiti","Nitr_inh","othImpact","N2OSYN")))
    *                                      + v_Miti(RUNR,"CropMiti","GComVN","N2OSYN") * (p_ghgMiti(RUNR,"cropMiti","GComVN","othImpact","N2OSYN")
    *                                      + p_ghgMiti(MSACT,"cropMiti","GComVN","othImpact","N2OSYN") $ (not p_ghgMiti(RUNR,"cropMiti","GComVN","othImpact","N2OSYN"))))
              * 44/28;
    """
    return M_kt * (n2o + vol) * M_N2O / M_N2O_N * gwp


def GWPN2OCRO_(R_kt, EF1A, gwp):
    r"""GWPN2OCRO_(r) (l. 3735-3757) in CO2-eq: the residues' N (kt; the accounts' n_crop_residues, or the catch crops'
    BioFix) x EF1A x 44/28 x GWP(N2O).

    CAPRI's GAMS, GWPN2OCRO_ (l. 3735-3757):

        GWPN2OCRO_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OCRO") =E=
    *
              [SUM( (MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A)), v_actLevl(RUNR,MCACT,A)
    *$ifi not %CropResi_IDEAG_NG% == on
            * (%data%(RUNR,MCACT,"MANN","Y")-p_nitrBalance(RUNR,"AtmDep") - p_nitrBalance(RUNR,"Mineralis"))
    *      --- mitigation effect on yield considered
            * v_yldMit(RUNR,MCACT)
    $iftheni.Pes13 %PEST_DISAGG%==ON
            * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes13
            * SUM(R_RAGG(RUNR,MSACT), 1 - N2OREGIO(MSACT,"CRBU") - N2OREGIO(MSACT,"CRFU") - N2OREGIO(MSACT,"CRFE")))
    *$ifi %CropResi_IDEAG_NG% == on            * EMISCALC(RS,MCACT,A,"NRESIDN","Y"))
                 * 0.001
    *   --- nitrogen provided by winter cover crops have to be added
             + [p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"CATC","T")]
    *            $ (  p_entlLimit(runr,"DPGREEN","DDGreen","Limit") $ p_DPGreeningLimits(runr,"ecoSetAside") )
                 ] *  GHGEFS("EF1A") * 44/28;
    """
    return R_kt * EF1A * M_N2O / M_N2O_N * gwp


def GWPN2OAMM_(nh3_kt, EF4, gwp):
    r"""GWPN2OAMM_(r) (l. 3793-3810), its manure term in CO2-eq: the manure NH3 (kt NH3) x 14/17 x EF4 x 44/28 x
    GWP(N2O). The mineral term: GWPN2OSYN_.

    CAPRI's GAMS, GWPN2OAMM_ (l. 3793-3810):

        GWPN2OAMM_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OAMM") =E=
    *
              SUM( (MAACT,A) $ (p_technFact(RUNR,MAACT,"LEVL",A)), v_actLevl(RUNR,MAACT,A)
    *                    - consider a possible modification of MANN and hence EMISCALC by mitigation option lowNFeed:
                    * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                    * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                    * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                    *   %data%(RUNR,MAACT,"MANN","Y")* (p_technFact(RUNR,MAACT,"MANN","T")+1.)
                    * (v_emiLoss(RUNR,MAACT,"NH3","Hous") + v_emiLoss(RUNR,MAACT,"NOx","Hous")
                     + v_emiLoss(RUNR,MAACT,"NH3","Stor") + v_emiLoss(RUNR,MAACT,"NOx","Stor")
                     + v_emiLoss(RUNR,MAACT,"NH3","Appl") + v_emiLoss(RUNR,MAACT,"NOx","Appl")
                     + v_emiLoss(RUNR,MAACT,"NH3","Graz") + v_emiLoss(RUNR,MAACT,"NOx","Graz")) * GHGEFS("EF4") * 44/28) * 0.001
              - v_netPutQuant(RUNR,"NITF") * (v_emiLoss(RUNR,"NETF","NH3","GasTot") + v_emiLoss(RUNR,"NETF","NOx","GasTot")) * GHGEFS("EF4") * 44/28;
    """
    return nh3_kt * M_NH3_N / M_NH3 * EF4 * M_N2O / M_N2O_N * gwp


def GWPN2OHIS_(crop_area, n2o_crop, grass_area, n2o_grass):
    r"""GWPN2OHIS_(r) (l. 3815-3832) before the idled histosols, t N2O: the crop and grassland areas (1000 ha) x their
    N2O per ha from drained organic soils (EMISCALC(N2OHIS): the organic-soil share x the climate-weighted IPCC 2013
    factor, tools/build/build_histosol.py); the idled area's: GWPN2OHIS_idle.

    CAPRI's GAMS, GWPN2OHIS_ (l. 3815-3832):

        GWPN2OHIS_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OHIS") =E=
    *
             SUM( (mPact,A)  $ (p_technFact(RUNR,mPact,"LEVL",A) $ P_T_ActAgg(mPact,"UAAR")), v_actLevl(RUNR,mPact,A)
                 *    EMISCALC(RUNR,mPact,A,"N2OHIS","Y")
    *                                           -- possible set aside of histosols
    *                     Current specification without distinction in two variants:
    *                     (1) iHisCr = combinaiton of compulsory rewetting + idling (default specification)
    *                     (2) iHisCr = no rewetting, only idling (specification upto r9954, now only sensitivity run))
    *                     NOTE: The "QEmitt" entry may be set in a policy file >0 (e.g. = 0.5)
                 *(1 - v_Miti(RUNR,"iHisCr","fallow","N2OHIS")*(1-p_ghgMiti(RUNR,"iHisCr","fallow","N2OHIS","QEmitt"))
                       $ (p_ghgMiti(RUNR,"iHisCr","fallow","N2OHIS","MaxShare")   $ (not grsact(mPact)))
                     - v_Miti(RUNR,"IHISGR","fallow","N2OHIS")*(1-p_ghgMiti(RUNR,"iHisGr","fallow","N2OHIS","QEmitt"))
                       $ (p_ghgMiti(RUNR,"IHISGR","fallow","N2OHIS","MaxShare") $ (    grsact(mPact)))
                  )
                 ) * 0.001
                 ;
    """
    return crop_area * n2o_crop + grass_area * n2o_grass


def GWPN2OHIS_idle(F, ef):
    r"""GWPN2OHIS_'s idled histosols (iHisCr, iHisGr, QEmitt = 0 in the Green Deal runs): their area F (1000 ha) x the
    emission factor ef (kg N2O-N per ha) x 0.001 x 44/28, t N2O no longer emitted. CAPRI's GAMS: GWPN2OHIS_'s
    docstring."""
    return F * ef * 0.001 * M_N2O / M_N2O_N


def GWPN2OLEA_(tot, EF5):
    r"""GWPN2OLEA_(r) (l. 3836-3934), N2O-N: the leached and run-off N allocated to the crops (supply/n_leaching.py
    crop_n's sum, t N) x EF5.

    CAPRI's GAMS, GWPN2OLEA_ (l. 3836-3934):

            GWPN2OLEA_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"N2OLEA") =E=
    *         --- a) Runoff from mineral fertilizer application
                - v_netPutQuant(RUNR,"NITF") * v_emiLoss(RUNR,"NETF","N","RunTot")
                * GHGEFS("EF5") * 44/28
    *         --- b) Surface runoff from manure application, grazing and housing (note that runTot = runSurf + runHous and compare with gases.gms)
                + SUM ((MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,MCACT,"LEVL","Y") ), v_actLevl(RUNR,MCACT,A)
                      * p_share_NMAN(RUNR,MCACT,"Y")
                      * SUM( (MAACT,A1) $ (p_technFact(RUNR,MAACT,"LEVL",A1) $ %data%(RUNR,MAACT,"LEVL","Y")),
                                           v_actLevl(RUNR,MAACT,A1) * %data%(RUNR,MAACT,"MANN","Y")
    *                    - consider a possible modification of MANN by mitigation option lowNFeed:
                      * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option rumFedEff
                      * (1+v_Miti(RUNR,MAACT,"genet_eff","rumFedEff")*p_ghgMiti(RUNR,MAACT,"genet_eff","othImpact","MANN"))
    *                    - consider a possible modification by mitigation option mlkYld
                      * (1+v_Miti(RUNR,MAACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MAACT,"genet_yld","othImpact","MANN"))
                      * v_emiLoss(RUNR,MAACT,"N","RunTot")))
                * GHGEFS("EF5") * 44/28 * 0.001
    *         --- c) Leaching from mineral fertilizer application
    *
                - (v_netPutQuant(RUNR,"NITF")
                     * (1 - v_emiLoss(RUNR,"NETF","N","GasRunTot") - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y"))
                     * v_nitrBalance(RUNR,"Leach") ) $ %data%(RUNR,"IMPORT","NITF","Y")
                * GHGEFS("EF5") * 44/28
    *         --- d) Leaching from manure application and grazing
                + SUM ((MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,MCACT,"LEVL","Y") ), v_actLevl(RUNR,MCACT,A)
                      * p_share_NMAN(RUNR,MCACT,"Y")
                      * [SUM( (MAACT,A1) $ (p_technFact(RUNR,MAACT,"LEVL",A1) $ %data%(RUNR,"IMPORT","NITF","Y")),
                                     v_actLevl(RUNR,MAACT,A1) * %data%(RUNR,MAACT,"MANN","Y")
    *                    - consider a possible modification of MANN by mitigation option lowNFeed:
                                     * (1+v_Miti(RUNR,MAACT,"lowNFeed","N2OEXCR")*p_ghgMiti(RUNR,MAACT,"lowNFeed","othImpact","MANN"))
                                     * (1 - v_emiLoss(RUNR,MAACT,"N","GasRunTot") - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y")))
                      - (%data%(RUNR,"MTRADE","NITF","Y") * 1000 * (1 - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y"))) $ %data%(RUNR,"IMPORT","NITF","Y")]
                      * v_nitrBalance(RUNR,"Leach"))
                * GHGEFS("EF5") * 44/28 * 0.001
    *         --- e) Leaching from atmospheric deposition and mineralisation
    *
                + SUM ((MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,"IMPORT","NITF","Y")), v_actLevl(RUNR,MCACT,A)
                      * (p_nitrBalance(RUNR,"AtmDep") + p_nitrBalance(RUNR,"Mineralis"))
                      * (1 - v_emiLoss(RUNR,"NETF","N2O","GasTot")
                           - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y"))
                      * v_nitrBalance(RUNR,"Leach"))
                * GHGEFS("EF5") * 44/28  * 0.001
    *         --- f) Leaching from biological fixation
                + SUM ((MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,"IMPORT","NITF","Y")), v_actLevl(RUNR,MCACT,A)
                      * (%data%(RUNR,MCACT,"NITF","Y") * p_nitrFact(RUNR,MCACT,"BioFix")
    *         --- mitigation effect on yield considered
                      * v_yldMit(RUNR,MCACT)
    $iftheni.Pes15 %PEST_DISAGG%==ON
                      * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes15
                      * sum(R_RAGG(RUNR,MSACT),1. + (p_ghgMiti(MSACT,MCACT,"LegSh","othImpact","BioFix") * v_Miti(RUNR,MCACT,"LegSh","BioFix")) $ SAMEAS(MCACT,"OFAR")))
                      * (1 - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y")) * v_nitrBalance(RUNR,"Leach"))
                * GHGEFS("EF5") * 44/28 * 0.001
    *         --- g) Leaching from crop residues from main crops
                + SUM ((MCACT,A) $ (p_technFact(RUNR,MCACT,"LEVL",A) $ %data%(RUNR,"IMPORT","NITF","Y")), v_actLevl(RUNR,MCACT,A)
                      * (%data%(RUNR,MCACT,"MANN","Y") - p_nitrBalance(RUNR,"AtmDep") - p_nitrBalance(RUNR,"Mineralis"))
    *         --- mitigation effect on yield considered
                      * v_yldMit(RUNR,MCACT)
    $iftheni.Pes16 %PEST_DISAGG%==ON
                      * (1 +(v_yldPestFac(RUNR,mCact,A)-1) $ v_yldPestFac.range(RUNR,mCact,A))
    $endif.Pes16
                      * (1 - v_emiLoss(RUNR,"NETF","N2O","GasTot")
                           - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y")) * v_nitrBalance(RUNR,"Leach"))
                * GHGEFS("EF5") * 44/28 * 0.001
    *         --- h) Leaching from biological fixation and crop residues from winter cover crops
               + (p_ghgMiti(RUNR,"CATC","WinterCov","othImpact","BioFix") * v_actLevl(RUNR,"CATC","T")
                      * (1 - %data%(RUNR,"EXPPRD","NITF","Y") / %data%(RUNR,"IMPORT","NITF","Y")) * v_nitrBalance(RUNR,"Leach")) $ %data%(RUNR,"IMPORT","NITF","Y")
                * GHGEFS("EF5") * 44/28
    ;
    """
    return tot * EF5


def GWPN2OLEA_co2(n2o_n_t, gwp):
    r"""GWPN2OLEA_ in CO2-eq: its N2O-N (t) / 1000 x 44/28 x GWP(N2O), kt. CAPRI's GAMS: GWPN2OLEA_'s docstring."""
    return n2o_n_t / 1000.0 * M_N2O / M_N2O_N * gwp

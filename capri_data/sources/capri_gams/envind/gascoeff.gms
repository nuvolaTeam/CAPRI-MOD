********************************************************************************
$ontext

   CAPRI project

   GAMS file : GASCOEFF.GMS

   @purpose  : (1) set definition and calculation factors to define gas emissions relevant for global warming
               (2) define nutrient contents of crops and crop residuals (except STRA, GRAS, OFAR)
   @author   : I.Perez, P. Witzke, F Weiss
   @module   : ghg_ipcc
   @date     : 22.04.10
   @since    : 01.2004
   @refDoc   :
   @seeAlso  : envind\gases.gms
   @calledBy : capreg.gms, capmod.gms

$offtext
********************************************************************************
$if not setglobal runoveryears $setglobal runoveryears off
***setglobal runoveryears defined in capinv.gms (for the calculation of GHG inventories)

$ifi %runoveryears% == on $goto LabelRunOverYears



 SET GASAGG_TO_GHGS(GASAGG,GHGS) "mapping chemical gas aggregates to individual gases"/
     GCH4.(CH4ENT,CH4MAN,CH4RIC,CH4BUR,CH4HIS),
     GN2O.(N2OMAN,N2OAPP,N2OGRA,N2OSYN,N2OCRO,N2OindMM, N2OindAS,N2OLEA,N2OHIS,N2OBUR,N2OPRD,N2OSOI),
     GCO2.(CO2BIO,CO2SOI,CO2HIS,CO2LIM,CO2BUR,CO2PRD,CO2DIE,CO2UREA)
 /;

 SET PACT_TO_GHGS(PACT,GHGS);
 SET PACT_TO_GAS(PACT,GASROWS);
 SET PROD_TO_GHGS(ROWS,GASCOLS);
 SET FMIN(ROWS) / NITF,PHOF,POTF,CAOF /;

* TIER 1 and 2 Methods (IPCC): Default Factors for Enteric Fermentation Emissions.
*  --- Revised 1996 IPCC Guidelines for National Greenhouse Gas Inventories, 1997
*  --- Good Practice Guidance and Uncertainty Management in National Greenhouse Inventories, 2000

 SET EMISPAR(*) /

   CH4AN      "old CH4 Output of animals kg per animal and year - unknown source,"
   CH4EN      CH4 Output of animals kg per animal and year - Tier 1 IPCC 1997,
   YM         conversion factor of MJ energy into kg of methane - Tier 2 IPCC 2000,
   DE         digestibility default percentage  - Tier 2 IPCC 2000,
   GE         gross energy of feed as MCal per kg of dry matter,
   VSER       Volatile solid Excretion Rates on a dry weight basis,
   CH4MA1     kg CH4 per animal and year from manure - Tier 1 IPCC 1997,
   CH4MAN     kg CH4 per animal and year from manure - Tier 2 IPCC 1997,
   CH4EN1     kg CH4 per animal and year from enteric fermentation - Tier 1 IPCC 1997,
   CH4ENT     kg CH4 per animal and year from enteric fermentation - Tier 2 IPCC 1997,
   N2OMAN     kg N2O per animal and year from manure - Tier 2 IPCC 1997,
   N2OCRO     kg N2O in crop residues per activity - Tier 2 IPCC 1997,
   ASH        ash content in manure in % - Tier 2 IPCC 2000,
   B0         maximum CH4 producing capacity in % of the manure (kg from kg) - Tier 2 IPCC 1997,

   MANAG      manure management system usage of fraction of each AACT manure handled using under a manure system for Western Europe - MS% in IPCC 1997,
   CH4CONV    CH4 conversion factor for each manure management system in climate region "temperate" % - MCFjk in IPCC 1997,
*FW email to PW, 291113: "N2OCONV is not used anymore since introducing the Miterra data"
*   N2OCONV    N2O conversion factor for each manure management system in climate region "temperate" % - EF3S in IPCC 2000,
   Cool       climate temperature under below 15
   Temperate  climate temperature under between 15 and 25
   Warm       climate temperature above 25
   MCFMS      calculation of CH4CONV % x MANAG %, kg CH4 emitted per kg CH4 maximally produced
   EF3S       calculation of N2OCONV % x MANAG % but not pastures,
   EF3G       calculation of N2OCONV % x MANAG % for pastures,

   EF1A       Default emission factor and EF for anorganic Fertilizer application in kg N2O-N per kg N,
   EF1B       Emission factor for organic Fertilizer application in kg N2O-N per kg N,
   EF1C       Emission factor for biological fixation in kg N2O-N per kg N,
   EF2        Emission factor for histosols in kg per ha in kg N2O-N per kg N,
   EF3        Emission factor for grazing animals in kg N2O-N per kg N,
   EF4        Emission factor Deposited NH3+NOX in kg N2O-N per kg N,
   EF5        Emission factor Leached Nitrate in kg N2O-N per kg N,
   EF6        Emission factor for sewage in kg N2O-N per kg N,
   EF7        Emission factor for diesel burning in kg CO2 per l diesel consumed - www.kba.de,
   EF8A       Emission factor for limestone in kg CO2-C per kg CaCO3
   EF8B       Emission factor for dolomite in kg CO2-C per kg CaMg(CO3)2
   EF9        Emission factor for urea in kg CO2-C per kg CO(NH2)2

   GASF       Fraction of mineral fertilizer volatilised - obsolete in CAPRI???,
   GASM       Fraction of organic fertilizer volatilised - obsolete in CAPRI???,
   LEAC       Fraction of total fertilizer leached

   NRET        kg N retained per N intake

   RSCR        Ratio Residue to Crop Product
   CRDM        Dry matter fraction in crop residues (as of 2006 fraction in harvested product)
   CRNI        Nitrogen fraction in crop residues
   CRBU        Fraction of crop residue burned rather than left on the field (FRACBURN in iPCC)
   CRFU        Fraction of crop residue used as fuel
   CRFE        Fraction of crop residue used for animal feeding (returning afterwards to manure)

*New sets for crop residue calculation based on IPCC 2006

  CRag         Above-ground residue dry matter content estimation. Unit t per ha
  CRag_sl      Above-ground residue dry matter content estimation slope. See ipcc for standard deviations
  CRag_ic      Above-ground residue dry matter content estimation intercept. See ipcc for standard deviations
  CRaN         N content of above-ground residues, dry-matter (NAG)
  RCRbgag      Ratio of below-ground residues to above-ground biomass (RBG-BIO)
  CRbN         N content of below-ground residues dry-matter (NBG)
  FracRenew    Fraction of total area under crop that is renewed annually (FracRenew(T))
  FrequMow     Frequency of mowing (relevant for grassland etc)           (corresponds to FracRemove(T))

   PSUC        Plough and seeding unit combination - 2 ha field
   GPSC        Grubber and power harrow seed combination - 2 ha field
   PRCFUEL     Fuel Prices for agricultural diesel fuel in Euro 2000

   NEL         Net energy lactation IPCC
   NEM         Net energy maintenance IPCC
   NEA         Net energy activity IPCC
   NEP         Net energy pregnancy IPCC
   NEG         Net energy growth IPCC
/;


 SET CLIMALL /Cool,Temperate,Warm,10*28/;
 SET CLIM(CLIMALL) /Cool,Temperate,Warm/;
 SET CLIMCELS(CLIMALL) /10*28/;
 SET CLIMCOOL(CLIMALL) /10*14/;
 SET CLIMTEMP(CLIMALL) /15*25/;
 SET CLIMWARM(CLIMALL) /26*28/;

 SET EUGR /EUW,EUE/;
 SET EUGR_TO_MS(EUGR,RALL) /
     EUW.BL000000
          EUW.DK000000
          EUW.DE000000
          EUW.EL000000
          EUW.ES000000
          EUW.FR000000
          EUW.IR000000
          EUW.IT000000
          EUW.NL000000
          EUW.AT000000
          EUW.PT000000
          EUW.SE000000
          EUW.FI000000
          EUW.UK000000
* KMI, added 02/08/11
          EUW.NO000000

          EUW.CY000000
          EUW.MT000000
          EUE.CZ000000
          EUE.EE000000
          EUE.HU000000
          EUE.LT000000
          EUE.LV000000
          EUE.PL000000
          EUE.SI000000
          EUE.SK000000
          EUE.BG000000
          EUE.RO000000

*MoK  added 16.03.18
          EUE.AL000000
          EUE.MK000000
          EUE.CS000000
          EUE.MO000000
          EUE.HR000000
          EUE.BA000000
          EUE.KO000000
          EUE.TUR

          EUW.SET.R_BL
          EUW.SET.R_DE
          EUW.SET.R_EL
          EUW.SET.R_ES
          EUW.SET.R_FR
          EUW.SET.R_IR
          EUW.SET.R_IT
          EUW.SET.R_NL
          EUW.SET.R_AT
          EUW.SET.R_PT
          EUW.SET.R_SE
          EUW.SET.R_FI
          EUW.SET.R_UK
* KMI, added 02/08/11
          EUW.SET.R_NO

          EUE.SET.R_CZ
          EUE.SET.R_HU
          EUE.SET.R_PL
          EUE.SET.R_SK
          EUE.SET.R_BG
          EUE.SET.R_RO
*MoK  added 16.03.18

          EUE.SET.R_TUR
          /
;

SET emisParGdx(emisPar) "raw data on emission parameter to read from gdx" /
        CH4AN,CH4EN,YM,DE,ASH,B0,NRET
/;

SET emisRegGdx "regions filled with raw data on emission parameters from gdx" /
   set.Rall
   set.EUGR
/;

*pw: long texts are missing, might be found in IPCC 2006 vol 4, ch 20
   SET ManSys(*) /Lagoon,Liquid,Solid,Drylot,Pasture,Pit1,Pit2,DaySpread,Digester,Burned,Other/;
*  SET ManSysS(ManSys) /Lagoon,Liquid,Solid,Drylot,Pit1,Pit2,DaySpread,Digester,Burned,Other/;
*  SET ManSysG(ManSys) /Pasture/;
   ALIAS(CLIM,CLIM1);
   ALIAS(CLIMCELS,CLIMCELS1);
   ALIAS(MANSYS,MANSYS1);

SET PEATCAT /UAAR,SARAB,SGRAS/;

set orgSoilInfo "Information from organic soil share file"/
  O_regN2      "Organic soil area from the Harmonized World Soil Database (HWSD, kha)"
  C_regN2      "cropland area (kha)"
  G_regN2      "grassland area (kha)"
  F_regN2      "Other land use/cover (kha)"
  sog_regN2_rk "Share of cropland on organic soil in total cropland based on rk approach"
  soc_regN2_rk "Share of grassland on organic soil in total grassland based on rk approach"
  sof_regN2_rk "Share of other land use on organic soil in total other land based on rk approach"
  /;

* Fraction of N2O emissions
$ontext
SET N2OFRA(EMISPAR) /
         GASF  0.1
         GASM  0.2
         LEAC  0.3
         /;
$offtext



set CropResCalc(*) "Pool different content sets in order to facilitate convertion into tons" /
                STRAN, CRagN, CRbgN, CRagP, CRbgP, CRagK, CRbgK, CRlostN, CRlostP, NRESIDN, NRESIDP
    /;

Parameter
    p_share_N(*,*,*)                                            "Share of total N applied per ha of crop MCACT"
    p_manureAppl(*,*,*)                                         "Manure application to crops in kg per ha"
    p_manureGrazRedist(*,*)                                     "Manure available for p_manureAppl reduction of Grass"
    p_manureAgg(*,*,*)                                          "Aggregates of manure variables"
    p_feedShare(*,*,*)                                          "Share of MCACT main output used for feeding"
    p_runSurfGraz(*,*)                                          "Surface Runoff from grazing by animal activity"
    p_emissDifAbs(*,*)                                          "Absolute Difference between losses from manure application and mineral fertilizer application"
    p_emissDifRel(*,*)                                          "Relative Difference between losses from manure application and mineral fertilizer application"
    p_emFactMinFertPrd(ROWS,ft,GHGS)                            "Gas output per ton of nutrient in mineral fertiliser produced"
    p_gasesOutputPerMinFert(ROWS,GHGS)                          "Gas output per ton of nutrient in mineral fertiliser produced"

    EMISCALC_NI (*,COLS,A,*)                                    "Parameters for global warming emissions calculation from the national inventories 2002"
    p_tier1EmFactManMgt_NI(*,COLS,A,CLIMALL)                    "Manure management emission factors Tier 1 from the national inventories 2002"
    p_manureMgtShare_NI(*,COLS,A,EMISPAR,CLIMALL,ManSys)        "Parameters used to calculate GHGs from manure management from the national inventories 2002"

    EMISCALC (*,COLS,A,*,*)                                       "Parameters for global warming emissions calculation"
    p_tier1EmFactManMgt(*,COLS,A,CLIMALL)                       "Manure management emission factors Tier 1 calculated in CAPRI"
    p_manureMgtShare (*,COLS,A,EMISPAR,CLIMALL,ManSys)          "Parameters used to calculate GHGs from manure management"
$ifi %storgrazInv% == on $ifi %TIMESERIES%==ON    p_manureMgtShareTime (*,COLS,A,ManSys,simyy_ybas)  "Time dependent manure shares pasture/liquid/solid based on NI used to calculate GHGs from manure management"
    GHGEFS(EMISPAR)                                             "Emission factors IPCC"
    p_shareClimZone(*,CLIMALL)                                  "percentage share of regions in climate Zone(cool,temperate,Warm)"

    EMISCALC0 (Rall,COLS,A,emisParGdx)                          "Parameters for global warming emissions calculation - raw data"
    p_tier1EmFactManMgt0(emisRegGdx,COLS,A,CLIMALL)             "Manure management emission factors Tier 1 calculated in CAPRI - raw data"
    p_manureMgtShare0(emisRegGdx,COLS,A,EMISPAR,CLIMALL,ManSys) "Parameters used to calculate GHGs from manure management - raw data"
    GHGEFS0(EMISPAR)                                            "Emission factors IPCC - raw data"
    p_shareClimZone0(Rall,CLIMALL)                              "percentage share of regions in climate Zone(cool,temperate,Warm) - raw data"

    N2OREGIO(*,EMISPAR)                                         "Share residues burned, used as feed and fuel"
    p_nutContCropOutput(O,FNUT)                                 "retention of pure nutrient in kg per t harvested material"
*   Avoiding domain control for easier code in fert\fertned.gms:
    Resid(ROWS,*)                                               "Pure nutrient content of crop residues in kg/ton of harvested material"
    Crop_Resid(*,COLS,FNUT,*)                                   "Replaces Resid(...), pure nutrient content of crop residues in kg/ton of harvested material "
    p_co2EquDieselPerLiter (PACT,EMISPAR)                       "calculation of CO2 emissions from diesel consumption (l/ha)"
    p_dieselPrice (*,EMISPAR)                                   "calculation of fuel energy costs from fuel consumption (l/ha)"

    ipcc11_2(*,EMISPAR)                                         "Raw data for crop residue calculation"
    p_ipcc11_2(*,*)                                             "Parameter for crop residue calculation as defined in IPCC 2006 table 11.2"
    p_fert_inv(RALL,*,*)                                        "Information on fertilizer input of urea and liming";
    ;



OPTION p_manureMgtShare:3:5:1;

***If new data for urea and liming is available generate and updated p_fert_inv value by activating the following include
*$include 'envind\CreateFertilizerInventory.gms'

execute_load "%datdir%\envind\FertilizerDataInventory.gdx" p_fert_inv;



* include data of national inventories
$include 'envind\inventories.gms'
*
 TABLE p_gasesOutputPerMinFert(ROWS,GHGS) "Gas output per ton of nutrient in mineral fertiliser produced"
* kg/t
              CO2PRD      N2OPRD
    NITF      2543.6      11.3
    PHOF       972.7       4.3
    POTF       140.0       0.6
    CAOF         0.0       0.0
 ;

   TABLE p_emFactMinFertPrd(ROWS,ft,GHGS) "Gas output per ton of nutrient in mineral fertiliser produced"
* NITF values derived from Wood, S., Cowie, A. (2004), A review of GHG emission factors for Fertlizer production.
* kg/t
                   CO2PRD      N2OPRD
    NITF.Ureum     4018.9       0.0
    NITF.Other     2438.4       9.0
    PHOF.Ureum      972.7       4.3
    PHOF.Other      972.7       4.3
    POTF.Ureum      140.0       0.6
    POTF.Other      140.0       0.6
    CAOF.Ureum        0.0       0.0
    CAOF.Other        0.0       0.0
 ;
*  --- for calculation of share of burned crop residues (CRBU), share used for fuel (CRFU), share used for animal feeding (CRFE)
***think of renaming this expression

TABLE N2OREGIO(*,EMISPAR)

                    CRBU      CRFU       CRFE

       BL000000     0.0        0.0       0.0
       DK000000     0.0        0.0       0.0
       DE000000     0.0        0.0       0.0
       EL000000     0.10       0.0       0.0
       ES000000     0.10       0.0       0.0
       FR000000     0.0        0.0       0.0
       IR000000     0.0        0.0       0.0
       IT000000     0.10       0.0       0.0
       NL000000     0.0        0.0       0.0
       AT000000     0.0074     0.0       0.0
       PT000000     0.10       0.0       0.0
       SE000000     0.0        0.0       0.0
       FI000000     0.0        0.0       0.0
       UK000000     0.0        0.0       0.0
* KMI, 10/10/12
       NO000000     0.0
        ;

    N2OREGIO(MSALL,"CRBU") $ (NOT (Map_RR("EU015000",MSALL) or SAMEAS(MSall,"NO000000"))) = 0.1;
*
*  reads as: 1 ton of soft wheat corn harvested comprises 20 kg pure nitrogen
*
    TABLE p_nutContCropOutput(O,FNUT) "retention of pure nutrient in kg per t harvested material"

              NITF        PHOF        POTF

   SWHE       20.          8.          6.
   DWHE       23.          8.          7.
   RYEM       16.67        8.          6.
   BARL       16.67        8.          6.
   OATS       18.33        8.          6.
   MAIZ       16.67        8.          5.
   OCER       28.33        8.          6.
   PARI       22.          7.         24.
   STRA        5.          3.         18.
   POTA        3.5         1.4         6.0
   SUGB        1.8         1.0         2.5
*# From hoftor_perfect.xls which corresponds nicely with Miterra
   ROOF        1.8         0.9         5.0
*   ROOF        3.33        0.09        5.0
*#  This was for "Ackerbohnen" in kg/dt not kg/t !
*   PULS        4.1         1.2         1.4
   PULS       41.0        12.0        14.0
   RAPE       33.0        18.0        10.0
   SUNF       28.0        16.0        24.0
   SOYA       58.0        16.0        24.0
   OOIL       30.0        16.0        16.0
   TEXT        3.0         8.0        15.0
   GRAS        4.17        1.5         3.5
   MAIF        3.33        2.0         4.4
*  Landsberger Gemenge, Fresh weight:
   OFAR        6.60        1.75       3.75
   TOMA        2.0         0.7         0.6
   OVEG        2.0         0.7         0.6
   APPL        1.1         0.3         1.6
   CITR        2.0         0.4         1.6
   OFRU        2.0         0.4         1.7
   NURS       15.5         5.5         5.0
   FLOW       65.0        22.0        20.0
   OCRO       15.5         5.5         5.0
   OIND       15.5         5.5         5.0
   OLIV        4.5         1.0         0.5
   TAGR        1.9         1.0         3.1
   TOBA       30.0         4.0        45.0;

   p_nutContCropOutput("TABO",FNUT) = p_nutContCropOutput("OLIV",FNUT) * 5;
   p_nutContCropOutput("TWIN",FNUT) = p_nutContCropOutput("TAGR",FNUT) / 0.65;



Parameter Nindex(*)    "Ratio kg N per ha in main product to kg N per ha in crop residuals" /
*             (From capri\gams\envind\miterra\xlsdata\new_fert.xls )

APPL              2.054988
BARL              2.369686
CITR              2.054988
DWHE              3.019026
FALL              0.000100
FLOW              2.054988
GRAS              2.000000
MAIF              4.911314
MAIZ              1.528672
NONF              0.000100
NURS              2.054988
OATS              2.077312
OCER              2.015988
OCRO              2.054988
OFAR              2.432146
OFRU              3.000000
OIND              1.112545
OLIV              2.054988
OOIL              1.252652
OVEG              1.164725
OWIN              2.054988
PARI              3.019026
POTA              3.125250
PULS              4.974908
RAPE              1.786315
ROOF              1.779998
RYEM              1.790107
SOYA              2.054988
SUGB              0.670224
SUNF              1.786315
SWHE              3.019026
TABO              2.054988
TAGR              2.054988
TEXT              1.112545
TOBA              2.054988
TOMA              3.000000
TWIN              2.054988
/;
***The following calculation is no longer necessary (see updated calculation of crop residues below)
***Generally: Why is NINDEX used to calcualte the values for Resid for all three components of the set fnut??
* --- Straw is a special case, explicit losses are estimated in coco => also special case

   Resid(CROPO,FNUT) $ (NINDEX(CROPO) AND ((NOT SUM(PACT_TO_Y(CERE,CROPO),1.)) OR SAMEAS(CROPO,"MAIZ")))
                                               = p_nutContCropOutput(cropo, fnut) / Nindex(cropo);

*  --- For calculation of CO2 emissions from diesel consumption (l/ha)
*      NOTE: some activities have to be guessed!

TABLE p_co2EquDieselPerLiter (PACT,EMISPAR)

               PSUC      GPSC

      SWHE     87.7      77.1
      DWHE     87.7      77.1
      RYEM
      BARL     79.4      68.9
      OATS
      MAIZ     85.9      76.0
      OCER
      PARI
      RAPE     85.2      74.7
      SUNF     77.5      67.6
      SOYA
      OLIV
      OOIL     80.0      69.5
      PULS
      POTA    137.7     125.2
      SUGB    111.8     101.9
      TOBA
      OIND
      OCRO
      MAIF
      ROOF
      OFAR
      GRAE
      GRAI
   ;


*  --- for calculation of fuel energy costs from fuel consumption (l/ha)
*      NOTE: This should be part of ENER (data reported by EUROSTAT)

TABLE p_dieselPrice (*,EMISPAR)

                   PRCFUEL
       BL000000     30.32
       DK000000     41.72
       DE000000     68.08
       EL000000     62.83
       ES000000     41.35
       FR000000     39.06
       IR000000     43.23
       IT000000     48.85
       NL000000     50.85
       AT000000     64.90
       PT000000     42.09
       SE000000     67.73
       FI000000     35.48
       UK000000     39.25
;

*
*  --- Load global warming potential coefficients and map down to inventory positions
*      Some positions are not (yet?) mapped. They are specifically assigned in the data file.

$include "%datdir%\envind\global_warming_potentials.gms"

*    --- assignment of global warming potentials from aggregates to single items

   p_globWarmPot(GHGS) = SUM( GASAGG_TO_GHGS(GASAGG,GHGS), p_globWarmPot(GASAGG)) ;
   p_globWarmPot(GASREP) = 1 ;

*
*    --- To create the gdx with the raw data (on EMISCALC,p_tier1EmFactManMgt,p_shareClimZone,p_manureMgtShare) activate
*        the following $include. This is quick when running create_sim_ini_gdx.gms with an exit after $include gascoeff.gms
*        and in capmod.gms a $stop after $endif.simini
*
*$include "envind\create_rawdat_gascoeff_gdx.gms"
*$exit
*
$label LabelRunOverYears

   execute_load "%datdir%\envind\rawdat_gascoeff.gdx"  EMISCALC0,p_tier1EmFactManMgt0,p_manureMgtShare0,
                                                       GHGEFS0, ipcc11_2;
   execute_load "%datdir%\envind\climdat_gascoeff.gdx" p_shareClimZone0;

*MoK: assign data to Balkan and Turkey

p_shareClimZone0("TUR",climall)     =p_shareClimZone0("CY000000",climall);
p_shareClimZone0("AL000000",climall)=p_shareClimZone0("IT000000",climall);
p_shareClimZone0("MO000000",climall)=p_shareClimZone0("IT000000",climall);
p_shareClimZone0("BA000000",climall)=p_shareClimZone0("BG000000",climall);
p_shareClimZone0("MK000000",climall)=p_shareClimZone0("BG000000",climall);
p_shareClimZone0("HR000000",climall)=p_shareClimZone0("BG000000",climall);
p_shareClimZone0("CS000000",climall)=p_shareClimZone0("BG000000",climall);
p_shareClimZone0("KO000000",climall)=p_shareClimZone0("BG000000",climall);

   EMISCALC(Rall,COLS,A,emisParGdx,%1)                          = EMISCALC0(Rall,COLS,A,emisParGdx)                             ;
   p_tier1EmFactManMgt(emisRegGdx,COLS,A,CLIMALL)               = p_tier1EmFactManMgt0(emisRegGdx,COLS,A,CLIMALL)               ;
   p_shareClimZone(Rall,CLIMALL)                                = p_shareClimZone0(Rall,CLIMALL)                                ;
   p_manureMgtShare(emisRegGdx,COLS,A,EMISPAR,CLIMALL,ManSys)   = p_manureMgtShare0(emisRegGdx,COLS,A,EMISPAR,CLIMALL,ManSys)   ;
   GHGEFS(EMISPAR)                                              = GHGEFS0(EMISPAR)                                              ;

*    --- completion of climate zone entries
*
   p_shareClimZone(RS,"cool") $ (NOT sum(CLIM,p_shareClimZone(RS,CLIM))) =  100;
   p_shareClimZone(RS,"10") $ (NOT sum(CLIMCELS,p_shareClimZone(RS,CLIMCELS))) =  100;


*    --- calculation of p_tier1EmFactManMgt =Manure management emission factors Tier 1 method (Western Europe) from inital values
*
   p_tier1EmFactManMgt(EUGR,MAACT,"T",CLIMWARM) = p_tier1EmFactManMgt(EUGR,MAACT,"T","Warm");

*  Effects of NH3 abatement technics from Miterra on CH4 emissions (Franz Weiss)

   p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL) $ (SAMEAS(MAACT,"HENS") or SAMEAS(MAACT,"POUF") or SAMEAS(MAACT,"SHGM") or SAMEAS(MAACT,"SHGF"))
                                 = (p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL) + sum(EUGR_TO_MS(EUGR,MS),p_tier1EmFactManMgt(EUGR,MAACT,"T",CLIMALL)) $ (NOT p_tier1EmFactManMgt(MS,MAACT,"T",CLIMALL)))
                                  * (1-p_Nemidat(MS,MAACT,"CH4","LossHous","Solid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Solid"));


*    ---Updated calcualtion of crop residues based on IPCC 2006 guidelines

$iftheni.capinv %runoveryears% == on
$batinclude 'envind\cropresidues.gms' %1
$endif.capinv


*    --- calculation of p_manureMgtShare = Parameter used to calculate GHGs from manure management (IPCC 2006 values for Western and Eastern Europe)
*

   p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMWARM,ManSys) = p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Warm",ManSys);
   p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCOOL,ManSys) $ (NOT p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCOOL,ManSys)) =
                                                            p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Cool",ManSys);
   p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMTEMP,ManSys) $ (NOT p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMTEMP,ManSys)) =
                                                            p_manureMgtShare("EU000000",MAACT,"T","CH4CONV","Temperate",ManSys);

*  Use of RAINS data for management systems and methane conversion factors (Franz Weiss)
*  Shares of management systems (poultry, sheep and goat allocated to solid)


$iftheni %storgrazInv% == on
$iftheni     %TIMESERIES%==ON
*al202102 --> Timeseries of manure shares from UNFCCC inventories already loaded in ammo.gms
*             ---> Shares so far are Liquid+Solid = 1. Convert now shares so that Liquid+Solid+Pasture =1 as required here
   $$setlocal MgtShareTime ON
   p_manureMgtShareTime(MS,MAACT,"T", "Pasture", years) =       p_TypeShare(MS, MAACT, "T", "GRAZ", years);
   p_manureMgtShareTime(MS,MAACT,"T", "Solid", years)   = (1. - p_TypeShare(MS, MAACT, "T", "GRAZ", years)) * p_TypeShare(MS, MAACT, "T", "Solid", years);
   p_manureMgtShareTime(MS,MAACT,"T", "Liquid", years)  = (1. - p_TypeShare(MS, MAACT, "T", "GRAZ", years)) * p_TypeShare(MS, MAACT, "T", "Liquid", years);
   p_manureMgtShareTime(MS,MAACT,"T", "Pasture", "Y")   =       p_TypeShare(MS, MAACT, "T", "GRAZ", "Y");
   p_manureMgtShareTime(MS,MAACT,"T", "Solid", "Y")     = (1. - p_TypeShare(MS, MAACT, "T", "GRAZ", "Y"))   * p_TypeShare(MS, MAACT, "T", "Solid", "Y");
   p_manureMgtShareTime(MS,MAACT,"T", "Liquid", "Y")    = (1. - p_TypeShare(MS, MAACT, "T", "GRAZ", "Y"))   * p_TypeShare(MS, MAACT, "T", "Liquid", "Y");
$else
   $$setlocal MgtShareTime OFF
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Pasture") = p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ");
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Solid")   = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Solid");
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Liquid")  = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Liquid");
$endif
$else
   $$setlocal MgtShareTime OFF
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Pasture") = p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ");
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Solid")   = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Solid");
   p_manureMgtShare(MS,MAACT,"T","MANAG",CLIMALL,"Liquid")  = (1. - p_Nemidat(MS,MAACT,"N","TypeShare","GRAZ")) * p_Nemidat(MS,MAACT,"N","TypeShare","Liquid");
$endif
*  Effects of NH3 abatement technics from Miterra on CH4 emissions
*  fw: due to the endogenous technologies we have to remove the impact of ammonia abatement techs here and apply it in supply_model.gms and gases.gms
*  otherwise we get a double counting
   p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Pasture") = p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Pasture");
   p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid") = (p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid")
                                                    + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Solid") $ (NOT p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Solid")))
*                                                      * (1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Solid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Solid"))
;

   p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")
                                                    = (p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")
                                                    + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMALL,"Liquid") $ (NOT p_manureMgtShare(MS,MAACT,"T","CH4CONV",CLIMALL,"Liquid")))
*                                                      * (1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Liquid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Liquid"))
;

*  The management option and the N2O coefficient factor do not vary with the weather acording to IPCC data (Western Europe data)

   p_manureMgtShare(EUGR,MAACT,"T","MANAG",CLIMALL,MANSYS)    = p_manureMgtShare(EUGR,MAACT,"T","MANAG","Temperate",MANSYS) ;
*FW email to PW, 291113: "N2OCONV is not used anymore since introducing the Miterra data"
*  p_manureMgtShare("EU000000",MAACT,"T","N2OCONV",CLIM,MANSYS) = p_manureMgtShare("EU000000",MAACT,"T","N2OCONV","Temperate",MANSYS);

*   --- copy IPCC calculation factor from standard to all technologies

   p_manureMgtShare("EU000000",MAACT,A,EMISPAR,CLIMALL,MANSYS)     = p_manureMgtShare("EU000000",MAACT,"T",EMISPAR,CLIMALL,MANSYS);
*
   p_manureMgtShare(EUGR,MAACT,A,EMISPAR,CLIMALL,MANSYS)      = p_manureMgtShare(EUGR,MAACT,"T",EMISPAR,CLIMALL,MANSYS);
   p_manureMgtShare(MS,MAACT,A,EMISPAR,CLIMALL,MANSYS)         $ p_technFact(MS,MAACT,"LEVL",A)    = p_manureMgtShare(MS,MAACT,"T",EMISPAR,CLIMALL,MANSYS);


*    --- MCFMS: kg CH4 emitted in relation to kh CH4 maximally produced from manure

   EMISCALC(RU,MAACT,A,"MCFMS",%1) $ p_technFact(RU,MAACT,"LEVL",A)
               = SUM((CLIMCELS,MANSYS,MAP_RR(MS,RU)), (p_shareClimZone(RU,CLIMCELS) + p_shareClimZone(MS,CLIMCELS) $ (NOT sum(CLIMCELS1,p_shareClimZone(RU,CLIMCELS1)))) * 0.01 *
$ifi NOT %MgtShareTime%==ON   (p_manureMgtShare(MS,MAACT,A,"MANAG",CLIMCELS,MANSYS) +
$ifi     %MgtShareTime%==ON   (p_manureMgtShareTime(MS,MAACT,A,MANSYS, %1) +
                                     sum(EUGR_TO_MS(EUGR,MS),p_manureMgtShare(EUGR,MAACT,"T","MANAG",CLIMCELS,MANSYS)) $ (NOT
$ifi NOT %MgtShareTime%==ON                                                         sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIMCELS,MANSYS1)))) *
$ifi     %MgtShareTime%==ON                                                         sum(MANSYS1,p_manureMgtShareTime(MS,MAACT,A,MANSYS1,%1)))) *
                                    (p_manureMgtShare(MS,MAACT,A,"CH4CONV",CLIMCELS,MANSYS) + p_manureMgtShare("EU000000",MAACT,"T","CH4CONV",CLIMCELS,MANSYS)
                                                                                  $ (NOT p_manureMgtShare(MS,MAACT,A,"CH4CONV",CLIMCELS,MANSYS))));

*$stop


$ontext

*    --- EF3S: kg N2O-N emitted in relation to kg N in manure as a function of manure management system
*
*   Changed code for calculation for national inventory data (Franz Weiss)
*  EMISCALC(MS,MAACT,A,"EF3S")  $ p_technFact(MS,MAACT,"LEVL",A)
*               = SUM((CLIM,ManSys) $ (NOT SAMEAS (ManSys,"Pasture")),
*                    (   p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS) $ (SUM((CLIM1,MANSYS1),p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM1,MANSYS1))=1)
*                      +   (p_manureMgtShare("EU000000",MAACT,"T","MANAG",CLIM,MANSYS)* p_shareClimZone(MS,CLIM) * 0.01) $ (NOT (SUM((CLIM1,MANSYS1),p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM1,MANSYS1))=1)))
*                        * (  p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS)
*                           + p_manureMgtShare("EU000000",MAACT,"T","N2OCONV",CLIM,MANSYS) $ (NOT p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS))
*                            )
*                        );


   EMISCALC(MS,MAACT,A,"EF3S")  $ p_technFact(MS,MAACT,"LEVL",A)
               = SUM((CLIM,ManSys) $ (NOT SAMEAS (ManSys,"Pasture")),
                    (   p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS) $ (sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS1))=1)
                      + p_manureMgtShare("EU000000",MAACT,"T","MANAG",CLIM,MANSYS) $ (NOT (sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS1))=1)))
                     * p_shareClimZone(MS,CLIM) * 0.01
                        * (  p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS)
                           + p_manureMgtShare("EU000000",MAACT,"T","N2OCONV",CLIM,MANSYS) $ (NOT p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS))
                            )
                        );

*    --- EF3G: kg N2O-N emitted in relation to kg N in manure as a function of manure management system
*
*   Changed code for calculation for national inventory data (Franz Weiss)
*   EMISCALC(MS,MAACT,A,"EF3G")  $ p_technFact(MS,MAACT,"LEVL",A)
*               = SUM((CLIM,ManSys) $ (SAMEAS (ManSys,"Pasture")),
*                    (   p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS) $ (SUM((CLIM1,MANSYS1),p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM1,MANSYS1))=1)
*                      +   (p_manureMgtShare("EU000000",MAACT,"T","MANAG",CLIM,MANSYS)* p_shareClimZone(MS,CLIM) * 0.01) $ (NOT (SUM((CLIM1,MANSYS1),p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM1,MANSYS1))=1)))
*                        * (  p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS)
*                           + p_manureMgtShare("EU000000",MAACT,"T","N2OCONV",CLIM,MANSYS) $ (NOT p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS))
*                            )
*                        );


   EMISCALC(MS,MAACT,A,"EF3G")  $ p_technFact(MS,MAACT,"LEVL",A)
               = SUM((CLIM,ManSys) $ (SAMEAS (ManSys,"Pasture")),
                    (   p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS) $ (sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS1))=1)
                      + p_manureMgtShare("EU000000",MAACT,"T","MANAG",CLIM,MANSYS) $ (NOT (sum(MANSYS1,p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,MANSYS1))=1)))
                     * p_shareClimZone(MS,CLIM) * 0.01
                        * (  p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS)
                           + p_manureMgtShare("EU000000",MAACT,"T","N2OCONV",CLIM,MANSYS) $ (NOT p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,MANSYS))
                            )
                        );



*   EMISCALC(MS,MAACT,A,"EF3G")  $ p_technFact(MS,MAACT,"LEVL",A)
*               = SUM(CLIM, p_manureMgtShare(MS,MAACT,A,"MANAG",CLIM,"Pasture") * p_shareClimZone(MS,CLIM) * 0.01 * p_manureMgtShare(MS,MAACT,A,"N2OCONV",CLIM,"Pasture"));

$offtext


* CROP-SPECIFIC PARAMETER THAT ARE USED IN THE CALCUATION OF N2O EMISSIONS FROM CROP RESIDUES
* IPCC DEFAULT VALUES IN TABLE 4.17 - IPCC Revised Guidelines 2000 FOR SOME CROP GROUPS
*
* But according to the IPCC document, p 4.82 "It is highly desirable to use country specific data for these values"
* => They are replaced with Miterra-EU data from the NH3 project
*    Furthermore this was the opportunity to revise the p_nutContCropOutput and RESID data in \fert\fertpar.gms for consistency within the code
*
$ontext  (New values following IPCC 2006 are now included in rawdat_gascoeff.gdx
TABLE N2OCROP(ROWS,EMISPAR)

            RSCR      CRDM      CRNI

  SWHE      1.3       0.85      0.0028
  DWHE      1.3       0.85      0.0028
  RYEM      1.6       0.90      0.0048
  BARL      1.2       0.85      0.0043
  OATS      1.3       0.92      0.0070
  MAIZ      1.0       0.78      0.0081
  OCER      1.4       0.88      0.0070
  PARI      1.4       0.85      0.0067
  PULS      2.1       0.83      0.0150
  RAPE      3.0       0.83      0.0150
  POTA      0.4       0.20      0.0110
  SUGB      0.2       0.30      0.0228
;
$offtext



  option kill=p_manureMgtShare,
         kill=EMISCALC0,
         kill=p_tier1EmFactManMgt0,
         kill=p_shareClimZone0,
         kill=p_manureMgtShare0,
         kill=GHGEFS0;




********************************************************************************
$ontext

   CAPRI project

   GAMS file : FERTPAR.GMS

   @purpose  : Definition of different calculation factors
               related to define nutrient retention of crops,
               nutrient content of crop residues

   @module   : fertilizer

   @author   : W. Britz
   @date     : 05.01.10
   @since    : 1999
   @refDoc   :
   @seeAlso  : fert\fertned.gms
   @calledBy : CAPREG.gms
               CAPMOD.gms
               COCO.gms


$offtext
********************************************************************************
*
$if not set DATA $setglobal DATA DATA

*
   PARAMETER  p_residRel "Relation between nutrient content of crop residues to the sum of the nutrient content of crop residues and main harvest product"
              p_cropNeed "N,P,K need per ton of main output"
              p_fertchk  "collects information on the differtn levels for fertilzer consistency";
*
*
$ontext
*
*  reads as: 1 ton of soft wheat corn harvested comprises 20 kg pure nitrogen
*
    TABLE p_nutContCropOutput "retention of nutrients in kg per t harvested material"

              NITF        PHOF        POTF
*
*             pure N      P2O5        K2O
*

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
*   ROOF        1.5         0.09        2.5
*mblz: I replace ROOF and PULS with the values from the same parameter in gams\envind\gascoef.gms 
*       and def_gascoef.gm although 5.0 for K in ROOF seems a bit high compared with SUGB
*# From hoftor_perfect.xls which corresponds nicely with Miterra
   ROOF        1.8         0.9         5.0
*   ROOF        3.33        0.09        5.0
#  This was from "Ackerbohnen" in kg/dt not kg/t !
*   PULS        4.1         1.2         1.4
   PULS       41.0        12.0        14.0
   RAPE       33.0        18.0        10.0
   SUNF       28.0        16.0        24.0
   SOYA       58.0        16.0        24.0
   OOIL       30.0        16.0        16.0

   TEXT        3.0         8.0        15.0
*
   GRAS        4.17        1.5         3.5
   MAIF        3.33        2.0         4.4
*
*  --- Landsberger Gemenge, Fresh weight
*
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

   TABLE Resid "Nutrient content of crop residues remaining on field in kg pure nutrient per ton of harvested material"

              NITF        PHOF        POTF
   SUGB        2.8         0.4         4.1
   ROOF        2.8         0.4         4.1
   POTA        0.4         0.4         0.6
   SUNF       22.0         6.0        60.0
   RAPE       11.0         2.0        33.0
*
*  --- proxy: peas
*
   PULS       25.0         1.3        22.0
   MAIZ        9.0         0.9        16.5;

$offtext

************************************************************************
*
*  Atmospheric Deposition of nitrogen (kg N/ha)
*
*  Source: Eurostat;
*     Jacob Hansen; Nitrogen balances in Agriculture
*     IN: Statistics in focus, Environment and energy, Theme 8-16/2000
*
*  The data of BL is the mean between Belgium and Luxemburg
*  The data of CH is the average of France and Austria
*
*  Responsible: Diti Oudendag, 17 juli 2001
*
*************************************************************************

  TABLE p_nitrBalance(*,*)

              AtmDep
*
   AT000000   20
   BL000000   32
   CZ000000   10
   CY000000   10
   DE000000   10
   DK000000   18
   EE000000   10
   ES000000   6
   FI000000   5
   FR000000   16


   EL000000   7
   HU000000   10
   IR000000   10
   IT000000   12
   LT000000   10
*   LU000000   27
   LV000000   10
   MT000000   10
   NL000000   36
   PL000000   10
   PT000000   3

   SE000000   5
   SI000000   10
   SK000000   10
   UK000000   15
   BG000000   10
   RO000000   10
* assumptions pw, 190207:
   KO000000   10
   HR000000   10
   CS000000   10
   MK000000   10
   MO000000   10
   AL000000   10
   BA000000   10
* assumption pw, 160318:
   TUR        10
* old assumptions:
   NO000000    5
   CH000000   18

   ;

 Parameter p_nitrDeposition(*) "Atmospheric deposition of Nitrogen";
 execute_load "%datDir%\fert\ndep.gdx" p_nitrDeposition=ndep;

 p_nitrBalance(SRNUTS2,"AtmDep") $ p_nitrDeposition(SRNUTS2) = p_nitrDeposition(SRNUTS2);
 p_nitrBalance(SRNUTS2,"AtmDep") $ (NOT p_nitrBalance(SRNUTS2,"AtmDep") and SUM(MAP_RR(NUTS0,SRNUTS2), p_nitrDeposition(NUTS0)))
                                 = SUM(MAP_RR(NUTS0,SRNUTS2), p_nitrDeposition(NUTS0));
 p_nitrBalance(SRNUTS2,"AtmDep") $ (NOT p_nitrBalance(SRNUTS2,"AtmDep")) = SUM(MAP_RR(NUTS0,SRNUTS2), p_nitrBalance(NUTS0,"AtmDep"));



$iftheni %TIMESERIES% == on
  DATA(RS,"UAAR","LEVL","BAS")      = SUM(AYEARS, DATA(RS,"UAAR","LEVL",AYEARS))/CARD(AYEARS);
$endif

 p_nitrBalance(MS,"AtmDep") $ SUM(MAP_RR(MS,SRNUTS2), %data%(SRNUTS2,"UAAR","LEVL","BAS") * p_nitrBalance(SRNUTS2,"AtmDep"))
                                = SUM(MAP_RR(MS,SRNUTS2), %data%(SRNUTS2,"UAAR","LEVL","BAS") * p_nitrBalance(SRNUTS2,"AtmDep"))
                                  / SUM(MAP_RR(MS,SRNUTS2), %data%(SRNUTS2,"UAAR","LEVL","BAS"));

 p_nitrBalance(Types,"AtmDep")   = SUM(types_from_r(types,SRNUTS2), p_nitrBalance(srnuts2,"AtmDep"));

*
*
*  sources:
*
*     AtmDep       Nutrient Flow model
*     BioFix       Shufa Baden Wuerttemberg
*     NITRO        Rivm
*
TABLE p_nitrFact(*,*,NFACT_POS)

               NOM     AtmDep   NITRO  BioFix
  RALL.SWHE   0.82     0.55     0.98
  RALL.RYEM   0.82     0.55     0.98
  RALL.BARL   0.82     0.55     0.98
  RALL.OATS   0.82     0.55     0.98
  RALL.MAIZ   0.75     0.50     0.98
  RALL.RAPE   0.75     0.50     0.98
  RALL.SUNF   0.75     0.50     0.98
  RALL.SOYA   0.75     0.50     0.98     0.75
  RALL.OOIL   0.75     0.50     0.98
  RALL.PULS   0.75     0.50     0.98     0.75
  RALL.POTA   0.75     0.50     0.98
  RALL.SUGB   0.80     0.57     0.98
  RALL.OIND   0.75     0.50     0.98
  RALL.TOMA   0.75     0.50     0.98
  RALL.OVEG   0.75     0.50     0.98
  RALL.APPL   0.75     0.50     0.98
  RALL.OFRU   0.75     0.50     0.98
  RALL.NURS   0.75     0.50     0.98
  RALL.FLOW   0.75     0.50     0.98
  RALL.OCRO   0.75     0.50     0.98
  RALL.MAIF   0.75     0.50     0.98
  RALL.ROOF   0.75     0.58     0.98
  RALL.OFAR   0.75     0.58     0.98     0.05
  RALL.FLEG   0.75     0.58     0.98     0.75
  RALL.GRAE   0.82     0.80     0.98     0.05
  RALL.GRAI   0.82     0.80     0.98     0.05
  RALL.FALL   0.82     0.58     0.98
;

   p_nitrFact(RALL,MCACT,"AtmDep") $ (NOT p_nitrFact(RALL,MCACT,"AtmDep")) = 0.50;

   SET oldGermanNUTS2Regs / DEE10000,DEE20000,DEE30000 /;

   p_nitrFact(RS,MCACT,"NStock") = FERT_OUT(RS,MCACT);
   p_nitrFact(RS,"ALL","DEFR")   = FERT_OUT(RS,"DEFR");
   p_nitrFact(RS,"ALL","DEFR")  $ (NOT p_nitrFact(RS,"ALL","DEFR")) = 1.;
   p_nitrFact(RS,MCACT,"NSTOCK") $ (NOT SUM(MCACT1, p_nitrFact(RS,MCACT1,"NSTOCK"))) = 10;

*
*  ---- re-calculation after old NUTS2 regions in DE vanished for DEE
*
   p_nitrFact("DEE00000",MCACT,"NStock") $(not  p_nitrFact("DEE00000",MCACT,"NStock"))
    = (FERT_OUT("DEE10000",MCACT)   +  FERT_OUT("DEE20000",MCACT)  + FERT_OUT("DEE30000",MCACT))/3;

   p_nitrFact("DEE00000","ALL","DEFR") $(not  p_nitrFact("DEE00000","ALL","DEFR"))
     = (FERT_OUT("DEE10000","DEFR") +  FERT_OUT("DEE20000","DEFR") + FERT_OUT("DEE30000","DEFR"))/3;

   p_nitrFact(RS,MCACT,"BioFix")         =  p_nitrFact("RALL",MCACT,"BioFix");

*
*
* --- Regional N fixation rates of grassland (data from the Animal Change project, Weiss F., based on unpublished data from John Helming, LEI)

PARAMETER p_nfixRate_gras(RALL) Regional N fixation rate for grassland
/
   AT000000   0.06
   BL000000   0.06
   CZ000000   0.14
   CY000000   0.05
   DE000000   0.08
   DK000000   0.14
   EE000000   0.15
   ES000000   0.07
   FI000000   0.05
   FR000000   0.07
   EL000000   0.19
   HU000000   0.17
   IR000000   0.05
   IT000000   0.16
   LT000000   0.12
   LV000000   0.07
   MT000000   0.05
   NL000000   0.05
   PL000000   0.07
   PT000000   0.05
   SE000000   0.11
   SI000000   0.05
   SK000000   0.14
   UK000000   0.05
   BG000000   0.08
   RO000000   0.10
/;

   p_nfixRate_gras(MS) $ (NOT p_nfixRate_gras(MS)) = p_nitrFact("RALL","GRAE","BioFix");

*
*  --- calculate N fixation rate for grass and ofar
*
   p_nitrFact(MS,"OFAR","BioFix") $ p_nfixRate_gras(MS) =  p_nfixRate_gras(MS) * (1.-%data%(MS,"FLEG","LEVL","BAS"))
                                + p_nitrFact("RALL","FLEG","BioFix") *     %data%(MS,"FLEG","LEVL","BAS");

   p_nitrFact(MS,GRSACT,"BioFix") $ p_nfixRate_gras(MS) =  p_nfixRate_gras(MS);

   p_nitrFact(RS,"OFAR","BioFix") $ sum(map_rr(ms,rs),p_nfixRate_gras(ms)) =  sum(map_rr(ms,rs),p_nfixRate_gras(ms) * (1.-%data%(RS,"FLEG","LEVL","BAS"))
                                + p_nitrFact("RALL","FLEG","BioFix") *     %data%(RS,"FLEG","LEVL","BAS"));

   p_nitrFact(RS,GRSACT,"BioFix") $ sum(map_rr(ms,rs),p_nfixRate_gras(ms))  =    sum(map_rr(ms,rs),p_nfixRate_gras(ms));


*
*       for farmtypes in capreg and capmod
*

if (card(types),

*  ---- check before starting ..

   If((not SUM(MAP_RR(MS,types),1)), abort "No mapping available MAP_RR");
   If((not SUM(types_to_r(NUTS2,types),1)), abort "No mapping available for types_to_r");

*  ---- first calulate the NUTS2 DEE figure on the ori data

   FERT_OUT("DEE00000",MCACT) $(not FERT_OUT("DEE00000",MCACT))
      = (FERT_OUT("DEE10000",MCACT) +FERT_OUT("DEE20000",MCACT)+FERT_OUT("DEE30000",MCACT))/3;
   FERT_OUT("DEE00000","DEFR") $(not  FERT_OUT("DEE00000","DEFR"))
     = (FERT_OUT("DEE10000","DEFR") +  FERT_OUT("DEE20000","DEFR") + FERT_OUT("DEE30000","DEFR"))/3;

*  ---- now take over the NSTOCKS into the Types

   p_nitrFact(types,MCACT,"NStock") = SUM(types_to_r(NUTS2,types), FERT_OUT(NUTS2,MCACT));
   p_nitrFact(types,"ALL","DEFR")   = SUM(types_to_r(NUTS2,types), FERT_OUT(NUTS2,"DEFR"));

*  ---- was already set previously, copy from p_nitrFact

   p_nitrFact(types,MCACT,"BioFix") $( not p_nitrFact(types,MCACT,"BioFix")) = p_nitrFact("RALL",MCACT,"BioFix");


*  --- stored only at MS so take from there
   %data%(types,"FLEG","LEVL","BAS") = SUM(MAP_RR(MS,types), %data%(MS,"FLEG","LEVL","BAS"));

*  --- calculate the rest
   p_nitrFact(types,"OFAR","BioFix") $ sum(map_rr(ms,types),p_nfixRate_gras(ms)) =  sum(map_rr(ms,types),p_nfixRate_gras(ms) * (1.-%data%(types,"FLEG","LEVL","BAS"))
                                + p_nitrFact("RALL","FLEG","BioFix") *     %data%(types,"FLEG","LEVL","BAS"));

   p_nitrFact(types,GRSACT,"BioFix") $ sum(map_rr(ms,types),p_nfixRate_gras(ms))  =    sum(map_rr(ms,types),p_nfixRate_gras(ms));
);
*
*  ---------------------------------------------------------------------------------
*
*  Minimum share of need which must be covered by mineral fertiliser. The
*  rest can be covered by organic fertiliser, too.
*
*
   p_minShareMinFert(MS,MCACT,A,FNUT)       = 0.4;
   p_minShareMinFert(MS,MCACT,A,"PHOF")     = 0.2;
   p_minShareMinFert(MS,MCACT,VEGPERM,FNUT) = 0.5;
*
   p_minShareMinFert(MS,GRSACT,A,FNUT)      = 0.05;
   p_minShareMinFert(MS,"OFAR",A,FNUT)      = 0.05;
   p_minShareMinFert(MS,"MAIF",A,FNUT)      = 0.20;
   p_minShareMinFert(MS,"MAIZ",A,FNUT)      = 0.30;
   p_minShareMinFert(MS,"PULS",A,"NITF")    = 0.0;
*
   p_maxShareMinFert(MS,MCACT,A,FNUT)   = 1.00;
*
*  *** special restrictions for ecologic farms
*
   p_minShareMinFert(MS,MCACT,"ECO",FNUT)     = 0.00;
   p_maxShareMinFert(MS,MCACT,"ECO","NITF")   = 0.01;
*
   p_maxShareMinFert(MS,VEGPERM,"ECO","NITF")  = 0.20;

   p_maxShareMinFert(MS,MCACT,"ECO","NITF")
                    $ (SAMEAS(MS,"ES000000") OR SAMEAS(MS,"EL000000") OR SAMEAS(MS,"PT000000")) = 0.10;

   p_maxShareMinFert(MS,VEGPERM,"ECO","NITF") $ (SAMEAS(MS,"ES000000") OR SAMEAS(MS,"EL000000")) = 0.90;

   p_maxShareMinFert(MS,VEGPERM,"ECO","NITF") $ SAMEAS(MS,"PT000000")  = 0.90;

*
*  ---------------------------------------------------------------------------------
*
   PARAMETER MAXF(FNUT) "Maximum input of nutrient for activities without yield dependency"
    / NITF 200., PHOF 160., POTF 140. /;
*
   MAXF("NITF") = 200;
   MAXF("PHOF") = 160;
   MAXF("POTF") = 140;
*
   MAXF(FNUT) = MAXF(FNUT) * 2.0;

   set doubleMaxf(PACT) "Activities for which the above maximum loads are doubled" / GRAE,GRAI,OFAR,MAIF/;

*  Used in digestibility for measure legSh:
*  Option kill = p_nfixRate_gras;

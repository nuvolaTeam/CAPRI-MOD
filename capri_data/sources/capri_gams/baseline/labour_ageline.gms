***********************************************************************
**
**    LABOUR_AGELINE.GMS
**
**    Since: October 07
**    Author: Markus Kempen
**
**    Purpose: Define upper and lower limits for changes in labour
**             force, based on estimated from CAPRI-Dynaspat
**             by NUI (Team Eoghan Garvey)
**
**    Note: no absolute values are taken from agelines,
**          only relative changes
**
**    See also: fix_est.gms
**
**
**    Institute for Food and Resource Economics, University of Bonn
**
***********************************************************************
PARAMETER AGELINE(*,*,*);
PARAMETER p_LabourPerAct;

* execute 'gdxxrw i=%CURDIR%\baseline\ageline.xls o="%CURDIR%\baseline\ageline.gdx" Par=ageline RNG=A1 rdim=2 Cdim=1';
$IF NOT EXIST '..\dat\baseline\ageline.gdx' $ABORT '..\dat\baseline\ageline.gdx' is missing
 execute_load '..\dat\baseline\ageline.gdx' AGELINE;

* age includeted in data base
SET AGE /25*75/;
* age relevant for labour supply (retirement at 65 ?!?) "Working_age"
SET W_AGE /25*65/;

AGELINE(SRNUTS1,"GROF",YEARS) = SUM(W_AGE, AGELINE(SRNUTS1,W_AGE,YEARS));

AGELINE(MS,"GROF",YEARS)      = SUM(MAP_RR(MS,SRNUTS1), AGELINE(SRNUTS1,"GROF",YEARS));

* calculate annual change rates from observation / projection years

AGELINE(MS,"ANUAL_CHANGE","1993") $ AGELINE(MS,"GROF","1993")
 =  (AGELINE(MS,"GROF","1995") / AGELINE(MS,"GROF","1993")) ** (1/2);

AGELINE(MS,"ANUAL_CHANGE","1995") $ AGELINE(MS,"GROF","1995")
 =  (AGELINE(MS,"GROF","1997") / AGELINE(MS,"GROF","1995")) ** (1/2);

AGELINE(MS,"ANUAL_CHANGE","1997") $ AGELINE(MS,"GROF","1997")
 =  (AGELINE(MS,"GROF","2000") / AGELINE(MS,"GROF","1997")) ** (1/3);

AGELINE(MS,"ANUAL_CHANGE","2000") $ AGELINE(MS,"GROF","2000")
 =  (AGELINE(MS,"GROF","2003") / AGELINE(MS,"GROF","2000")) ** (1/3);

AGELINE(MS,"ANUAL_CHANGE","2003") $ AGELINE(MS,"GROF","2003")
 =  (AGELINE(MS,"GROF","2012") / AGELINE(MS,"GROF","2003")) ** (1/9);

AGELINE(MS,"ANUAL_CHANGE","2012") $ AGELINE(MS,"GROF","2012")
 =  (AGELINE(MS,"GROF","2015") / AGELINE(MS,"GROF","2012")) ** (1/3);

* fill up time series

LOOP((MS,YEARS) $ (NOT AGELINE(MS,"ANUAL_CHANGE",YEARS)),
  AGELINE(MS,"ANUAL_CHANGE",YEARS) = AGELINE(MS,"ANUAL_CHANGE",YEARS-1));

*
* --- calculate expectet change of exante years compared to base year
*

AGELINE(MS,"EXPT_CHANGE",EXANTE) = PROD(YEARS $ (ORDT(YEARS) GE ORDT("BAS") AND ORDT(YEARS) LT ORDT(EXANTE)), AGELINE(MS,"ANUAL_CHANGE",YEARS));

*
* --- define bounds for further use in captrd:
*

* minimum: expectet value -10 % or lowest occuring value -5% (when no data for MS)

AGELINE(MS,"MIN_CHANGE",EXANTE) = MAX( SMIN(MS1 $ AGELINE(MS1,"EXPT_CHANGE",EXANTE), AGELINE(MS1,"EXPT_CHANGE",EXANTE)) - 0.05,
                                       AGELINE(MS,"EXPT_CHANGE",EXANTE) - 0.1,
                                       0 );

* maximum: expectet value +10 % or highest occuring value +5% (when no data for MS)

AGELINE(MS,"MAX_CHANGE",EXANTE) $ AGELINE(MS,"EXPT_CHANGE",EXANTE)
                                = MIN( SMAX(MS1, AGELINE(MS1,"EXPT_CHANGE",EXANTE)) + 0.05,
                                       AGELINE(MS,"EXPT_CHANGE",EXANTE) + 0.1,
                                       1 );

AGELINE(MS,"MAX_CHANGE",EXANTE) $ (NOT AGELINE(MS,"EXPT_CHANGE",EXANTE))
                                = MIN( SMAX(MS1, AGELINE(MS1,"EXPT_CHANGE",EXANTE)) + 0.05,
                                       1 );

* declare minimum labour requirement per activity (average of the 5 lowest countries in 2008 after eliminating potential outliers)
* caculation done in dat\minlabourrequiuement.xlsx)

parameter p_minLabourPerAct  /

SWHE     25.5
DWHE     28.1
RYEM     27.2
BARL     25.4
OATS     26.4
MAIZ     44.8
OCER     18
RAPE     24.7
SUNF     22.6
SOYA     41.9
OOIL     18
OIND     21.6
NURS     305.5
FLOW     254.8
OCRO     17.7
MAIF     25.3
ROOF     39
OFAR     18.1
GRAE     15.2
GRAI     15.2
PARI     135.2
OLIV     265.6
PULS     25.9
POTA     43.9
SUGB     44.7
TEXT     64.3
TOBA     291.9
TOMA     250
OVEG     75.4
APPL     253.9
OFRU     95.1
CITR     732.8
TAGR     377.5
TABO     321.7
TWIN     137.2
FALL     13.9
ISET     6.7
GSET     7.3
TSET     7.3
VSET     10.6
DCOL     41.5
DCOH     47.5
BULL     10.5
BULH     10.5
HEIL     9.3
HEIH     9.3
SCOW     25.7
HEIR     5.9
CAMF     13.6
CAFF     13.7
CAMR     11.9
CAFR     12.3
PIGF     1.7
SOWS     14.7
SHGM     2.7
SHGF     2
HENS     78
POUF     107.9
OANI     31.9
/;

* move values to parameter for calculation
p_labourPerAct("MinValue",MPACT,"LABT","2008","DATA") = p_minLabourPerAct(MPACT);

* assume the 2008 value to be applicable in any base year (might have to be reconsidered)
p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA") = p_minLabourPerAct(MPACT);

* copy the actual base year value to parameter for calculation
p_labourPerAct(MS,MPACT,"LABT","BASM","DATA") = P_DATA(MS,MPACT,"LABT","BASM");

*p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA") $ SUM(MS, P_DATA(MS,MPACT,"LABT","BASM")) = SMIN(MS $ P_DATA(MS,MPACT,"LABT","BASM"), P_DATA(MS,MPACT,"LABT","BASM"));
*p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA") $ SUM(MS, P_DATA(MS,MPACT,"LABT","BASM")) = SMIN(MS $ (P_DATA(MS,MPACT,"LABT","BASM") gt p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA")), P_DATA(MS,MPACT,"LABT","BASM"));

* calculate the the country specific minimum requirement

* MK: Note: in several countries the actual labour requirement per activity is quite high compared to activity specific labour requirements from litrature
*           we assume that especially small scle farms often report "full" labour units although the work on the farm is less than ~2000h (some sort of unproductive labour)
*           in the following we want to determine the requirement of productive labour.
*     assumption: The "general" minimum requirment is calculated as an average of the countries with low labour requirement per activity
*                 The country specific minimum is a weigthed avergae of the general minimum (75%) and the actulal value (25%), if the actual value is lower than the average (can happen in some cases) the actual value is maintained

p_labourPerAct(MS,MPACT,"LABT","BASM","MinRequirement") = MIN(p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA"), 0.75 * p_labourPerAct("MinValue",MPACT,"LABT","BASM","DATA") + 0.25 * p_labourPerAct(MS,MPACT,"LABT","BASM","DATA"));
* assume 0.5% less minimum requirement per annum to account for technological progress
p_labourPerAct(MS,MPACT,"LABT",EXANTE,"MinRequirement") = p_labourPerAct(MS,MPACT,"LABT","BASM","MinRequirement") * PROD(YEARS $ (ORDT(YEARS) GE ORDT("BAS") AND ORDT(YEARS) LT ORDT(EXANTE)), 0.995);

* copy total labour in base year
p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = P_DATA(MS,"GROF","LABT","BASM");
*p_labourPerAct(MS,"GROF","LABT","BASM","Check") = SUM(MPACT, P_DATA(MS,MPACT,"LABT","BASM") * P_DATA(MS,MPACT,"LEVL","BASM") * 0.001);
* calculate requirered labour based on assunmed minimum requirement
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") = SUM(MPACT, p_labourPerAct(MS,MPACT,"LABT",EXANTE,"MinRequirement") * P_DATA(MS,MPACT,"LEVL","BASM") * 0.001);

* convert minimum requirement to % of base year value (covenient for further use in captrd)
p_labourPerAct(MS,"GROF","LABT",EXANTE,"EXPT_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA");
* define min and max to account for uncertainty
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA") * 0.9;
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAct") $ p_labourPerAct(MS,"GROF","LABT","BASM","DATA") = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MinRequirement") / p_labourPerAct(MS,"GROF","LABT","BASM","DATA") * 1.5;

* copy coresponding values from agelines
p_labourPerAct(MS,"GROF","LABT",EXANTE,"EXPT_fromAgeline") = AGELINE(MS,"EXPT_CHANGE",EXANTE);
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAgeline") = AGELINE(MS,"MIN_CHANGE",EXANTE);
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAgeline") = AGELINE(MS,"MAX_CHANGE",EXANTE);


* take the max of requirement per activity and ageline for further use
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_CHANGE") = MAX(p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAgeline"),p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_fromAct"));
p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_CHANGE") = MAX(p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAgeline"),p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_fromAct"));



* copy to p_data for further use in captrd
P_DATA(MS,"MAXS","LABO",EXANTE) = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MAX_CHANGE");
P_DATA(MS,"MINS","LABO",EXANTE) = p_labourPerAct(MS,"GROF","LABT",EXANTE,"MIN_CHANGE");







execute_unload "%scrdir%\ageline.gdx", ageline, P_data, p_labourPerAct;;

*bort"";

option kill=AGELINE;
option kill=p_labourPerAct;
option kill=p_minLabourPerAct;



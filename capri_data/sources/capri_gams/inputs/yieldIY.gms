********************************************************************************
$ontext

   CAPRI project

   GAMS file : YIELDIY.GMS

   @purpose  : Define yield dependent part of activity specific input coefficients
               (Parameter p_inputDemandFactor)

   @module   : capreg_inputs

   @author   : W.Britz
   @date     : 02.10.09
   @since    : December 1999
   @refDoc   :
   @seeAlso  :
   @calledBy : capreg.gms
               capmod.gms

$offtext
********************************************************************************
*
*     --- read as follows: p_inputDemandFactor [*100%] of the input at average yields of the
*                          Member state depend linear on yield coefficients
*
*                          The remaining (1.-p_inputDemandFactor [*100%]) are fixed per activity level
*
TABLE p_inputDemandFactor(COLS,rows) "Estimated yield dependent term of linear input demand function"


            SEED     PLAP      IPHA     REPM  REPB     ELEC  EFUL  EGAS  ELUB  SERI    IRRO   INPO

SWHE         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
DWHE         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
BARL         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OATS         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
MAIZ         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
PARI         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OCER         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
RAPE         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
SUNF         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
SOYA         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OOIL         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OLIV         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
PULS         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
POTA         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
SUGB         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
TEXT         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
TOBA         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OIND         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5

TOMA         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OVEG         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
APPL         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OFRU         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
CITR         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
TAGR         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
TABO         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
TWIN         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
NURS         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
FLOW         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OCRO         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5

MAIF         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
ROOF         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
OFAR         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
GRAS         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
GRAE         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
GRAI         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
GSET         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5

SETA         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5
FALL         0.8      0.5                0.2   0.2      0.3   0.3   0.3   0.3   0.1     0.2    0.5

*           SEED     PLAP      IPHA     REPM  REPB     ELEC  EFUL  EGAS  ELUB  SERI    IRRO   INPO

DCOW                            0.8      0.5   0.5      0.3   0.3   0.3   0.3   0.5            0.5
DCOL                            0.8      0.5   0.5      0.3   0.3   0.3   0.3   0.5            0.5
DCOH                            0.8      0.5   0.5      0.3   0.3   0.3   0.3   0.5            0.5
SCOW                            0.8      0.5   0.5      0.3   0.3   0.3   0.3   0.5            0.5
BULF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
BULL                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
BULH                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
HEIF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
HEIL                            0.5      0.5   0.5      0.5   0.5   0.5   0.5   0.5            0.5
HEIH                            0.5      0.5   0.5      0.5   0.5   0.5   0.5   0.5            0.5
CAFF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
CAMF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
CAMR                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
CAFR                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
PIGF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
SOWS                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
SHGM                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
SHGF                            0.8      0.8   0.8      0.8   0.8   0.8   0.8   0.8            0.8
;

$iftheni.Pes28 %PEST_DISAGG%==ON
p_inputDemandFactor(PACT,pesModDis) = p_inputDemandFactor(PACT,"PLAP")  ;
p_inputDemandFactor(PACT,"PLAP")  = 0;
$endif.Pes28
*
p_inputDemandFactor(PACT,IY) $ (NOT p_inputDemandFactor(PACT,IY)) = 1;

$iftheni.w101 %WaterModule%==on
  p_inputDemandFactor(WACT,IY) $ sum(MAP_AA(WAggAct,WACT),p_inputDemandFactor(WAggAct,IY))
    = sum(MAP_AA(WAggAct,WACT),p_inputDemandFactor(WAggAct,IY));
$endif.w101

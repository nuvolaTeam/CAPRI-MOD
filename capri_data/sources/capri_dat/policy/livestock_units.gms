********************************************************************************
$ontext

   CAPRI project

   GAMS file : LIVESTOCK_UNITS.GMS

   @purpose  : Define livestock units per animal and year
               Attention: does not fit the activity definition of CAPRI
               for slaughtering and raising processes where the
               process period might deviate from 1 year

               Taken from: http://epp.eurostat.ec.europa.eu/statistics_explained/index.php/Glossary:LSU (13.06.12)
                    https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Livestock_unit_(LSU) (13.12.21)

   @author   : W.Britz, modified for laying hens and broilers by M. Bielza
   @date     : 13.06.12, 13.12.2021
   @since    :
   @refDoc   :
   @seeAlso  :
   @calledBy : agenda.gms, coco2_feednew.gms and others

$offtext
********************************************************************************
    PARAMETER p_LUUnits(*) "Livestock units" /
*
*    --- Bovine animals under 1 year old
*
        CAMF 0.4
        CAFF 0.4
        CAMR 0.4
        CAFR 0.4
*
*    --- Bovine animals 1 but less than 2 years old
*
        HEIR 0.7
        BULL 0.7
        HEIL 0.7
*
*    --- Female, 2 years and old
*
        HEIH 0.8
*
*    ---  Male, 2 years old and older
*
        BULH 1.0
*
*    ---  Dairy cows
*
        DCOL 1
        DCOH 1
*
*    ---  Other cows, 2 years old and over
*
        SCOW 0.8
*
*    ---  Other pigs
*
        PIGF 0.30
*
*    ---  Breeding sows weighting 50 kg and over
*         plus 10 piglets under 20 kg
*
*         = 0.5 + 10 * 0.027
*
        SOWS 0.77
*
*    ---  Laying hens, multiplied with 1000
*
*        HENS 1.4
        HENS 14
*
*    ---  Broilers, multiplied with 1000
*
*        POUF 0.7
        POUF 7
*
*    ---  Sheep and goat
*
        SHGM 0.1
        SHGF 0.1
    /;

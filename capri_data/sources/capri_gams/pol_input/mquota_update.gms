********************************************************************************
$ontext

   CAPRI project

   GAMS file : MQUOTA_UPDATE.GMS

   @purpose  : Provide data on milk quotas and assign to parameters needed in CAPTRD/CAPMOD
   @author   : P. Witzke, M Kempen, M Adenäuer
   @date     : 28.10.09
   @refDoc   :
   @seeAlso  :
   @calledBy : captrd\captrd_policy.gms
               supply\prep_milk_quotas.gms

$offtext
********************************************************************************


SET MQuotaInfo /
           QUTdel    "Quota for deliveries incl restructuring reserve"
           QUTdir    "Quota for direct sales incl restructuring reserve"
           Delivs    "Deliveries"
           DSTOTL    "Direct sales total"
           QUTtot    "Quota for deliveries and direct sales incl restructuring reserve"
/;


$include '%datdir%\coco\milk_quota_dat.gms'
*
*  Aggregate BL=BE+LU
   p_MQuotaDat("BL000000",MQuotaInfo,simyy) = p_MQuotaDat("BE000000",MQuotaInfo,simyy) + p_MQuotaDat("LU000000",MQuotaInfo,simyy) ;


TABLE PMQuotaReg(*,MQuotaInfo,*) "Total quota from r:\documents\other-eu\oj_dec_281_2004enlarg.pdf and r:\documents\dgagri\hc_proposal2008.pdf (as of 2008)"
*                                    Note: The restructuring reserve is included from 2006 onwards for EU10 and from 2009 onwards for EU02
                           2004      2005      2006      2007      2008      2009      2010      2011      2012      2013      2014
BL000000   .QUTtot       3579.5    3579.5    3597.4    3615.3    3705.8    3742.9    3780.3    3818.1    3856.3    3894.9    3894.9
BG000000   .QUTtot                                      979.0     998.6    1008.6    1018.7    1028.8    1039.1    1049.5    1049.5
CZ000000   .QUTtot       2682.1    2682.1    2737.9    2737.9    2792.7    2820.6    2848.8    2877.3    2906.1    2935.1    2935.1
DK000000   .QUTtot       4455.3    4455.3    4477.6    4499.9    4612.6    4658.7    4705.3    4752.4    4799.9    4847.9    4847.9
DE000000   .QUTtot      27864.8   27864.8   28004.1   28143.5   28847.4   29135.9   29427.3   29721.5   30018.7   30318.9   30318.9
EE000000   .QUTtot        624.5     624.5     646.4     646.4     659.3     665.9     672.5     679.3     686.1     692.9     692.9
IR000000   .QUTtot       5395.8    5395.8    5395.8    5395.8    5503.7    5558.7    5614.3    5670.4    5727.2    5784.4    5784.4
EL000000   .QUTtot        820.5     820.5     820.5     820.5     836.9     845.3     853.7     862.3     870.9     879.6     879.6
ES000000   .QUTtot       6117.0    6117.0    6117.0    6117.0    6239.3    6301.7    6364.7    6428.3    6492.6    6557.6    6557.6
FR000000   .QUTtot      24235.8   24235.8   24357.0   24478.2   25091.3   25342.2   25595.7   25851.6   26110.1   26371.2   26371.2
IT000000   .QUTtot      10530.1   10530.1   10530.1   10530.1   10740.7   10848.1   10956.5   11066.1   11176.8   11288.5   11288.5
CY000000   .QUTtot        145.2     145.2     145.2     145.2     148.1     149.6     151.1     152.6     154.1     155.7     155.7
LV000000   .QUTtot        695.4     695.4     728.6     728.6     743.2     750.7     758.2     765.7     773.4     781.1     781.1
LT000000   .QUTtot       1646.9    1646.9    1704.8    1704.8    1738.9    1756.3    1773.9    1791.6    1809.5    1827.6    1827.6
BL400000   .QUTtot        269.0     269.0     270.4     271.7     278.5     281.3     284.1     287.0     289.9     292.8     292.8
HU000000   .QUTtot       1947.3    1947.3    1990.1    1990.1    2029.9    2050.2    2070.7    2091.4    2112.3    2133.4    2133.4
MT000000   .QUTtot         48.7      48.7      48.7      48.7      49.7      50.2      50.7      51.2      51.7      52.2      52.2
NL000000   .QUTtot      11074.7   11074.7   11130.1   11185.4   11465.6   11580.3   11696.1   11813.1   11931.2   12050.5   12050.5
AT000000   .QUTtot       2749.4    2749.4    2763.1    2776.9    2847.5    2876.0    2904.7    2933.8    2963.1    2992.7    2992.7
PL000000   .QUTtot       8964.0    8964.0    9380.1    9380.1    9567.7    9663.4    9760.1    9857.7    9956.2   10055.8   10055.8
PT000000   .QUTtot       1870.5    1920.5    1929.8    1939.2    1987.5    2007.4    2027.5    2047.7    2068.2    2088.9    2088.9
RO000000   .QUTtot                                     3057.0    3118.1    3149.3    3180.8    3212.6    3244.7    3277.2    3277.2
SI000000   .QUTtot        560.4     560.4     576.6     576.6     588.2     594.1     600.0     606.0     612.1     618.2     618.2
SK000000   .QUTtot       1013.3    1013.3    1040.8    1040.8    1061.6    1072.2    1082.9    1093.8    1104.7    1115.8    1115.8
FI000000   .QUTtot       2407.0    2407.0    2419.0    2431.0    2491.9    2516.9    2542.0    2567.4    2593.1    2619.0    2619.0
SE000000   .QUTtot       3303.0    3303.0    3319.5    3336.0    3419.6    3453.8    3488.3    3523.2    3558.4    3594.0    3594.0
UK000000   .QUTtot      14609.7   14609.7   14682.7   14755.6   15125.2   15276.4   15429.2   15583.5   15739.3   15896.7   15896.7
 ;

    PMquotaReg(MS,"QUTtot",%1) = PMquotaReg(MS,"QUTtot",%1) * 1000;
*
*   As regulation data are missing before 2004, assume older DG AGRI data are fully in line with data from regulation
    PMquotaReg(MS,"QUTtot",%1)  $ (%2(%1) LT %2("2004"))
                          = (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

    PPQuotas(MS,"QTot",%1) = PMquotaReg(MS,"QUTtot",%1);

*   Note: 1993-2007 the quotas are as observed (including the Agenda 2000 increase)
*         2008 includes the 2% expansion from 13.03.2008, so if you do not want that expansion activate:
*    PPQuotas(MS,"QTot",%1)  $ (%2(%1) GT %2("2007")) = PPQuotas(MS,"QTot","2007");

*   Note: 2009-2014 give the quotas from the HC proposal (+1% each year from 2008-2013), so if you do not want the HC, activate:
*pw010410    PPQuotas(MS,"QTot",%1)  $ (%2(%1) GT %2("2008")) = PPQuotas(MS,"QTot","2008");

*   Scale DG Agri data to match exactly with regulation data (has minimal effect)
    PPQuotas(MS,"QDel",%1) $ (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1))
                              = p_MQuotaDat(MS,"QUTDel",%1)*PPQuotas(MS,"QTot",%1)/(p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

    PPQuotas(MS,"QDir",%1) $ (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1))
                              = p_MQuotaDat(MS,"QUTDir",%1)*PPQuotas(MS,"QTot",%1)/(p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

*   Useful to correct for under/overdelivery:
    PPQuotas(MS,"Deli",%1)= p_MQuotaDat(MS,"Delivs",%1);
    PPQuotas(MS,"DirS",%1)= p_MQuotaDat(MS,"DSTotl",%1);

 OPTION KILL = PMquotaReg;
 OPTION KILL = p_MQuotaDat;

*  Official quotas in base year period:
   PPQuotas(MS,PSQTYPE,"BASM") $ SUM(BASYRSM $ PPQuotas(MS,PSQTYPE,BASYRSM),1)
       = SUM(BASYRSM, PPQuotas(MS,PSQTYPE,BASYRSM))/SUM(BASYRSM $ PPQuotas(MS,PSQTYPE,BASYRSM),1);
*
*
*  Default case for operation of quotas is elimination of over/underdelivery...
   PPQuotas(MS,"QdelFac",exAnte_temp) $  (PPQuotas(MS,"QDel","BASM")  AND PPQuotas(MS,"Deli","BASM"))
              = PPQuotas(MS,"Qdel","BASM")/PPQuotas(MS,"Deli","BASM");

* ...but some MS have deviated regularly from their quotas (corressponds to case <structural over/underproduction> in EDIM2008, Table 8)

   PPQuotas(MS,"QdelFac",exAnte_temp)  $ (
                 SAMEAS(MS,"AT000000") Or
                 SAMEAS(MS,"DE000000") Or
                 SAMEAS(MS,"FR000000") Or
                 SAMEAS(MS,"FI000000") Or
                 SAMEAS(MS,"UK000000") Or
                 SAMEAS(MS,"SE000000") Or
                 SAMEAS(MS,"IT000000") Or
                 SAMEAS(MS,"CY000000") Or
                 SAMEAS(MS,"CZ000000") Or
                 SAMEAS(MS,"HU000000") Or
                 SAMEAS(MS,"PL000000")
                 ) = 1.;

*
* ... but in MT there is a large gap between quotas and deliveries ex post => MT is likely to fill quotas partly, but not completely => reassign with factor closer to 1:
   PPQuotas(MS,"QdelFac",exAnte_temp)  $ ( (SAMEAS(MS,"MT000000"))  and PPQuotas(MS,"Deli","BASM"))
                = (1+(PPQuotas(MS,"Qdel","BASM")/PPQuotas(MS,"Deli","BASM")-1.)/2);


********* taking over MS quotas to data array

*
*   Quotas will be assigned separately for deliveries(=PRCM) and direct sales (=HCOM), with special treatment for subsistence (=FEDM+LOSM)
*
*   Let QUTA = quota on deliveries
    %3(MS,"QUTA","COMI",exAnte_temp) $ (PPQuotas(MS,"Qtot",exAnte_temp) and %3(MS,"PRCM","COMI","%4"))
*                start from BASM
              =( %3(MS,"PRCM","COMI","%4")
*                change in total official quotas relative to bas
              * (PPQuotas(MS,"Qtot",exAnte_temp)/PPQuotas(MS,"Qtot","BASM"))
*                factor for correction of over/underderivery in BAS (but no adjustment in expost period)
              * (PPQuotas(MS,"QdelFac",exAnte_temp)  $      (%2(exAnte_temp) GT %2("Lst_Expost"))
                +1.                                  $ (NOT (%2(exAnte_temp) GT %2("Lst_Expost")))))

                              $      PPQuotas(MS,"Qtot","BASM")

              +(PPQuotas(MS,"Qtot",exAnte_temp)/1000
              * %3(MS,"PRCM","COMI","%4")
              /(%3(MS,"HCOM","COMI","%4")+%3(MS,"PRCM","COMI","%4")))

                              $ (NOT PPQuotas(MS,"Qtot","BASM"));
*
*   Let QUTB = quota on direct sales
    %3(MS,"QUTB","COMI",exAnte_temp) $ (PPQuotas(MS,"Qtot",exAnte_temp) and %3(MS,"HCOM","COMI","%4"))
*                  if possible start from BASM
              = (  %3(MS,"HCOM","COMI","%4")
*                  change in total quotas relative to bas
                 * PPQuotas(MS,"Qtot",exAnte_temp)/PPQuotas(MS,"Qtot","BASM"))

                              $      PPQuotas(MS,"Qtot","BASM")
*
              + (  PPQuotas(MS,"Qtot",exAnte_temp)/1000
                 * %3(MS,"HCOM","COMI","%4")
                 /(%3(MS,"HCOM","COMI","%4")+%3(MS,"PRCM","COMI","%4")))

                              $ (NOT PPQuotas(MS,"Qtot","BASM"));
*
*  CAPRI-adjusted quotas in base year period (should be equal to PRCM+HCOM.BAS):
   %3(MS,Quotas,"COMI","BASM")  $ SUM(BASYRSM $ %3(MS,Quotas,"COMI",BASYRSM),1)
       = SUM(BASYRSM, %3(MS,Quotas,"COMI",BASYRSM))/SUM(BASYRSM $ %3(MS,Quotas,"COMI",BASYRSM),1);

   %3(MS,"QUTS","COMI",exAnte_temp) = %3(MS,"QUTA","COMI",exAnte_temp) + %3(MS,"QUTB","COMI",exAnte_temp);
*




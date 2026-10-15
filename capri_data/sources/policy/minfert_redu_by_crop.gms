********************************************************************************
$ontext

   CAPRI project

   GAMS file : minfert_redu_by_crop.gms


   @purpose  : 20 percent synthetic fertilizer reduction target



   @author   : mihaly (old version "greendeal_synfertilizers.gms"), pw
   @date     : Feb 2023
   @since    : February 2021
   @refDoc   :
   @seeAlso  : minfert_redu_uaa.gms, organic_minfert_redu.gms
   @calledBy : greendeal_scenarios.gms


$offtext
********************************************************************************

*   ---   MINERAL FERTILIZER REDUCTION
*
*
*   ---   Reduction target for mineral fertilizer use in relative terms
*         (relative to baseline)
*         Note: Any other reduction targets (say "25crp") require additional lines like this:
*
$ifi %mineRedu%==10crp $setlocal reductionTarget 10
$ifi %mineRedu%==13crp $setlocal reductionTarget 13
$ifi %mineRedu%==15crp $setlocal reductionTarget 15
$ifi %mineRedu%==17crp $setlocal reductionTarget 17
$ifi %mineRedu%==20crp $setlocal reductionTarget 20
$ifi %mineRedu%==25crp $setlocal reductionTarget 25


*
*   ---   mihaly 26/05/21: Activate the code below only for debugging. Conclusions:
*                          1. per hectare application rates are missing for some NGRP groups (VEGE, WHEA...) in p_baselineDataout
*                          2. some aggregates (CERE, PERM, GRAS) contain different elements in the baseline results
*                             than defined by CACT_TO_NGRP (eg NGRP "CERE"={RYEM,OATS,OCER}).
*                          => we need to re-calculate the fertilizer use of the crop groups from the individual activities.
$ontext
parameter p_checkFertDistHa(rall,cols,*);


p_checkFertDistHa(ru,NGRP,"fertDist_mine")       = p_baselineDataout(ru,"fertDist_mine",NGRP,"NITF","%simy%");
p_checkFertDistHa(ru,NGRP,"fertDist_mine_perha") = p_baselineDataout(ru,"fertDist_mine_perha",NGRP,"NITF","%simy%");
*  Shows that VEGE, WHEA ... are missing:
p_checkFertDistHa(ru,NGRP,"missing_perha") $ (p_baselineDataout(ru,"fertDist_mine",NGRP,"NITF","%simy%")
                                                     $ (not p_baselineDataout(ru,"fertDist_mine_perha",NGRP,"NITF","%simy%")))
  = 1;
*  Shows that totals for VEGE, WHEA ... are assigned (but not necessarily in the desired manner):
p_checkFertDistHa(ru,NGRP,"missing_total") $ ((not p_baselineDataout(ru,"fertDist_mine",NGRP,"NITF","%simy%"))
                                                     $ p_baselineDataout(ru,"fertDist_mine_perha",NGRP,"NITF","%simy%"))
  = 1;
*
p_checkFertDistHa(ru,NGRP,"perha_recalc") $  sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%"))
  = p_baselineDataout(ru,"fertDist_mine",NGRP,"NITF","%simy%")
  / sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%")) * 1000;
*  Shows that perha_recalc <> perha_agg for CERE => only perha_agg is usable:
p_checkFertDistHa(ru,NGRP,"perha_agg") $  sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%"))
  = sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"fertDist_mine",MCACT,"NITF","%simy%"))
  / sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%")) * 1000;
$offtext

*
$ifi not defined p_nMaxPerHa option kill=p_nMaxPerHa;
  option p_nMaxPerHa:2:2:1;
*  display "check baseline mineral ferilizer use", p_nMaxPerHa,NGRP;


*
*   ---    mineral fertilizer application per hectare is recalculated for the crop groups from the individual cropping activities
*          (MCACT --> NGRP)
*          because the previous check showed that any other approach gives missing (WHEA, VEGE...) or wrong (CERE) results
*

  parameter p_minfertBaseline(rall,cols,*);

  p_minfertBaseline(ru,NGRP,"MIN") $ sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%"))
    =  sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"fertDist_mine",MCACT,"NITF","%simy%"))
     / sum(CACT_TO_NGRP(MCACT,NGRP), p_baselineDataout(ru,"",MCACT,"LEVL","%simy%"));


*
*   ---    apply reduction target to get absolute bounds on mineral fertiliser appication
*   ---    to avoid numerical issues: apply reduction only on sizeable mineral N-use
*

$ifi not declared p_checkSmallMine parameter p_checkSmallMine(rall, NGRP)  "report small MINE use in basline";
  option kill=p_checkSmallMine;

*          consider any application < 30kg a small and exempt from reduction requirements
  p_checkSmallMine(ru,NGRP) $ (p_minfertBaseline(ru,NGRP,"MIN") lt 0.03)
    = p_minfertBaseline(ru,NGRP,"MIN");

*          Adhoc fixes for unclear infeasibilities: Include regions in "small application group"
*          => no reduction requirement, and only limited backsliding below the specified p_checkSmallMine, derived from baseline:
*          Note1: For unclear reasons these problems with the crop specific limits increased in the July 2024 Catalyse runs
*                 Conclusion: The crop specific application limits via the beta distribution create trouble, so perhaps TJ is right
*                 that this specification is not yet fully operational. Under Catalyse there was no time for detailed fertiliser                                                                   i
*                 research => scenarios were "pushed through" with the adhoc exceptions collected here, knowing that the fertiliser
*                 reduction would be imposed anyway via the surplus constraint => Perhaps the Agora setting (ignoring the fertilser
*                 constraint) was wiser than these painful attempts to reflect this Greendeal element
*          Note2: At the same time earlier problems with infes due to the surplus contraint basically disapeared
$ifthene.min35 %simy%>2035
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES130000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"HU210000") $ (sameas(ngrp,"GRAS") or sameas(ngrp,"MAIZ") or sameas(ngrp,"WHEA")))
    = 1.2* p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DEB20000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DE720000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DEC00000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL620000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL310000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL420000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"AT320000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"BG030000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT510000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT720000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES220000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT910000") $ (sameas(ngrp,"SUGB") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"SE020000") $ (sameas(ngrp,"MAIZ") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"SE020000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"RO070000") $ (sameas(ngrp,"PULS") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$iftheni.oth3 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL610000") $ (sameas(ngrp,"PULS") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT910000") $ (sameas(ngrp,"MAIZ") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$endif.oth3
$endif.min35
$ifthene.min40 %simy%>2040
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"HU230000") $ (  sameas(ngrp,"GRAS") or sameas(ngrp,"MAIZ")
                                                       or sameas(ngrp,"WHEA") or sameas(ngrp,"OFAR")))
    = 1.2* p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"HU220000") $ (sameas(ngrp,"GRAS") or sameas(ngrp,"MAIZ") or sameas(ngrp,"WHEA")))
    = 1.2* p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"HU330000") $ (sameas(ngrp,"GRAS") or sameas(ngrp,"MAIZ") or sameas(ngrp,"WHEA")))
    = 1.2* p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL330000") $ (sameas(ngrp,"PULS") )) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT800000") $ (sameas(ngrp,"PULS") )) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL240000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PT160000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT310000") $ (sameas(ngrp,"BARL") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"BG020000") $ (sameas(ngrp,"SOYA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES510000") $ ( sameas(ngrp,"POTA"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$iftheni.oth4 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES210000") $ (sameas(ngrp,"MAIZ") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL230000") $ ( sameas(ngrp,"POTA"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$endif.oth4
$endif.min40
$ifthene.min45 %simy%>2045
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT310000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PT180000") $ (sameas(ngrp,"PERM") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PT110000") $ (sameas(ngrp,"WHEA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"SE0A0000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DEB10000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DE800000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DE210000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL210000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL330000") $ (sameas(ngrp,"SUNF") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL220000") $ (sameas(ngrp,"MAIZ"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PT150000") $ (sameas(ngrp,"MAIZ"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"CY000000") $ (sameas(ngrp,"OAFC"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"HU230000") $ (sameas(ngrp,"POTA"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$iftheni.oth5 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES300000") $ (sameas(ngrp,"RAPN") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$endif.oth5
$endif.min45
$ifthene.pul %simy%>2020
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT930000") $ ( sameas(ngrp,"PULS"))) = 1.*p_minfertBaseline(ru,NGRP,"MIN");
$endif.pul
$ifthene.min25 %simy%>2025
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL220000") $ ( sameas(ngrp,"OAFC"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL220000") $ ( sameas(ngrp,"OFAR"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL300000") $ ( sameas(ngrp,"MAIF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PT200000") $ ( sameas(ngrp,"SUGB"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES110000") $ (sameas(ngrp,"PULS") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES420000") $ (sameas(ngrp,"POTA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"DE940000") $ (sameas(ngrp,"SOYA") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT310000") $ ( sameas(ngrp,"PERM"))) = 1.2*p_minfertBaseline(ru,NGRP,"MIN");
$iftheni.oth3 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT120000") $ ( sameas(ngrp,"MAIZ"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT310000") $ ( sameas(ngrp,"BARL"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"IT310000") $ ( sameas(ngrp,"GRAS"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$endif.oth3
$endif.min25
$ifthene.min30 %simy%>2030
$iftheni.oth2 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"FR220000") $ ( sameas(ngrp,"SOYA"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"FR250000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
$endif.oth2
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"FR300000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL250000") $ ( sameas(ngrp,"MAIZ"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES430000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL520000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL300000") $ ( sameas(ngrp,"SUNF"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"SE080000") $ (sameas(ngrp,"OAFC") )) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL240000") $ (sameas(ngrp,"RAPN") or sameas(ngrp,"PERM"))) = 1.2*p_minfertBaseline(ru,NGRP,"MIN");
$endif.min30

$ifthene.rapmin4 %simy%>2035
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"SE010000") $ ( sameas(ngrp,"SUGB"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"FR830000") $ ( sameas(ngrp,"POTA"))) = 1.1*p_minfertBaseline(ru,NGRP,"MIN");
* High carbon price + >2030 meant under catalyse diet shift >49%  of EAT Lancet recommendations => strong price increase
* for oilseeds => yields increase => nutneed_ violated with required decline of mineral fertiliser
* However: These difficulties basically disappeared in the July 2024 sims. Unclear why.
$iftheni.oth1 %othPol%==high
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"AT210000") $ ( sameas(ngrp,"SUNF"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL520000") $ (sameas(ngrp,"ROOF") )) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"PL520000") $ (sameas(ngrp,"SOYA") )) = p_minfertBaseline(ru,NGRP,"MIN");
$ontext
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"FI1A0000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"AT210000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (same#as(ru,"BL210000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES530000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES520000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES300000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"ES230000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL130000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL140000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"EL250000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL120000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL130000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL230000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL420000") $ ( sameas(ngrp,"RAPN"))) = p_minfertBaseline(ru,NGRP,"MIN");
  p_checkSmallMine(ru,NGRP) $ (sameas(ru,"NL330000") $ ( sameas(ngrp,"SUNF"))) = p_minfertBaseline(ru,NGRP,"MIN");
$offtext
$endif.oth1
$endif.rapmin4


*
*   --- small mineral fetilizer uses (or defined by adhoc rules from above) are not cut by the reduction target, but we still
*       require that they do not increase beyond the specified limit (no back sliding assumption)
  p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ p_checkSmallMine(ru,NGRP))
    =   p_checkSmallMine(ru,NGRP);


*   --- if p_nMaxPerHa is already set in a previous file (e.g. by organic farming target)
*       then we take the more stringent reduction target (i.e. we use the min() function below)
*
  p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ (not p_checkSmallMine(ru,NGRP)) $ (p_nMaxPerHa(ru,NGRP,"MIN") gt 0))
    =  min( (p_minfertBaseline(ru,NGRP,"MIN") * (1 - %reductionTarget%/100)),
             p_nMaxPerHa(ru,NGRP,"MIN")
                    );

  p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ (not p_checkSmallMine(ru,NGRP)) $ (not p_nMaxPerHa(ru,NGRP,"MIN")))
    =  p_minfertBaseline(ru,NGRP,"MIN") * (1 - %reductionTarget%/100);


*
*   ---    error trapping for the calculatd fertilization limits
*

*  only shock EU-27 countries
  p_nMaxPerHa(rall,NGRP,"MIN") $ (not SUM(R_RAGG(rall1,"EU27yr19"), R_RAGG(rall,rall1))) = 0;



*   --- we implement the crop specific contraints via the beta density rather than fixed bounds:
*       NOTE: This is explained in the X11 deliverable D4, Section 2

  p_priFertDistRegu("f2f",RU,"priMaxPerHa","nitf",ngrp,"y")
  = p_nMaxPerHa(ru,NGRP,"MIN")*1000
  ;

*     Define which fertilizer sources qualify for each regulation
  p_fertDistReguWgt("f2f","mine") = 1;


*     Use the beta prior mechanism to try to prevent CRES from running amok
*     by creating a "regulation" limCres for the application of CRES nutrients
*     that is XX% higher than the baseline situation.

  p_priFertDistRegu("limCres",RU,"priMaxPerHa",FNUT,NGRP,"y")
    = p_priFertDist(ru,"postModePerHa","CRES",FNUT,NGRP,"%simy%") * (1.3
*   Various additional relaxations to cope with infeasilities showing high marginals for the crop residue constraints:
*   These problem cases became more frequent in the sims for results in 40_data_090724 compared to the earlier 39_data_220424
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"SE010000")   $  sameas(ngrp,"SUGB"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"PT200000")   $  sameas(ngrp,"SUGB"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"EL220000")   $  sameas(ngrp,"OFAR"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"HU230000")   $  sameas(ngrp,"OFAR"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"EL300000")   $  sameas(ngrp,"MAIF"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"FR250000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2030                                                  +.5 $ (sameas(ru,"FR250000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2030                                                  +.5 $ (sameas(ru,"FR300000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"IT920000")   $  sameas(ngrp,"SOYA"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"IT910000")   $  sameas(ngrp,"SUGB"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"IT120000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"NL320000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"NL220000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"SE020000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"SE020000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"IT910000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"ES300000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"ES520000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"ES420000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"IT720000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"FR830000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2025                                                  +.5 $ (sameas(ru,"ES300000")   $  sameas(fnut,"PHOF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"RO070000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"PL330000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL510000")   $  sameas(ngrp,"ROOF"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"ES430000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"IT800000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"ES130000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"AT210000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"DEC00000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL620000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL420000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL310000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"AT320000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"DE720000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"EL240000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>20300                                                  +.5 $ (sameas(ru,"ES110000")   $  sameas(ngrp,"RAPN"))
$ife %simy%>2030                                                  +.5 $ (sameas(ru,"PL520000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2030                                                  +.5 $ (sameas(ru,"ES430000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL520000")   $  sameas(ngrp,"SOYA"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"PL610000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2030                                                  +.5 $ (sameas(ru,"EL300000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"ES510000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"EL230000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2040                                                  +.5 $ (sameas(ru,"ES210000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2035                                                  +.5 $ (sameas(ru,"ES220000")   $  sameas(ngrp,"POTA"))
$ife %simy%>20400                                                  +.5 $ (sameas(ru,"EL120000")   $  sameas(ngrp,"POTA"))
$ife %simy%>20400                                                  +.5 $ (sameas(ru,"EL430000")   $  sameas(ngrp,"POTA"))
$ife %simy%>20400                                                  +1. $ (sameas(ru,"EL420000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2040                                                   +.5 $ (sameas(ru,"SE080000")   $  sameas(ngrp,"PULS"))
$ife %simy%>2035                                                   +.5 $ (sameas(ru,"EL250000")   $  sameas(ngrp,"OAFC"))
$ife %simy%>2030                                                   +.5 $ (sameas(ru,"EL250000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2030                                                   +.5 $ (sameas(ru,"SE080000")   $  sameas(ngrp,"OAFC"))
$ife %simy%>2030                                                   +.5 $ (sameas(ru,"FR220000")   $  sameas(ngrp,"SOYA"))
$ife %simy%>2040                                                   +.5 $ (sameas(ru,"BG020000")   $  sameas(ngrp,"SOYA"))
$ife %simy%>2025                                                   +.5 $ (sameas(ru,"DE940000")   $  sameas(ngrp,"SOYA"))
$ife %simy%>2035                                                   +.5 $ (sameas(ru,"DEB20000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2030                                                   +.5 $ (sameas(ru,"EL240000")   $  sameas(ngrp,"RAPN"))
$ife %simy%>2040                                                   +.5 $ (sameas(ru,"IT310000")   $  sameas(ngrp,"RAPN"))
$ife %simy%>2030                                                   +.5 $ (sameas(ru,"IT310000")   $  sameas(ngrp,"BARL"))
$ife %simy%>2025                                                   +.5 $ (sameas(ru,"IT310000")   $  sameas(ngrp,"PERM"))
$ife %simy%>2040                                                   +.5 $ (sameas(ru,"PT160000")   $  sameas(ngrp,"OAFC"))
$ife %simy%>2040                                                   +.5 $ (sameas(ru,"PT160000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                   +.5 $ (sameas(ru,"SE0A0000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2045                                                   +.5 $ (sameas(ru,"DEB10000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                   +.5 $ (sameas(ru,"NL210000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                   +.5 $ (sameas(ru,"DE210000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                   +.5 $ (sameas(ru,"DEB10000")   $  sameas(ngrp,"RAPN"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"DE800000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"IT310000")   $  sameas(ngrp,"SUNF"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"ES530000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"HU230000")   $  sameas(ngrp,"POTA"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"CY000000")   $  sameas(ngrp,"OAFC"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"PT150000")   $  sameas(ngrp,"MAIZ"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"PT110000")   $  sameas(ngrp,"WHEA"))
$ife %simy%>2045                                                  +.5 $ (sameas(ru,"ES300000")   $  sameas(ngrp,"RAPN"))
                                                                  ) ;
p_fertDistReguWgt("limCres","CRES") = 1;

*   ---    clean up
*
  option kill = p_minfertBaseline;



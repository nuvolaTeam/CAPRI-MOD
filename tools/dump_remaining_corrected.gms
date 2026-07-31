$TITLE CAPRI-Python -- corrected dumps for the remaining sources
$ONTEXT

  Corrected against the symbol listings. Two of my earlier guesses were wrong.

  dat\estnlp\results.gdx  holds five symbols, not three:
      VA(*,*,*,*)      free Variable  'Input requirement'
      VB(*,*,*)        free Variable  'PMP Cross-group effects'
      VD(*,*)          free Variable  'PMP Diagonal quadratic effects'
      PELA(*,*,*,*)    Parameter      'Average point price elasticities of crops'
      PELAGRP(*,*,*,*) Parameter      'Average point price elasticities of crop groups'

  VA, VB and VD are VARIABLES, so gdxdump emits .L/.LO/.UP suffixes. That is
  expected; the parser takes the .L level.

  dat\arm\GTP57_134.gdx is the raw GTAP database, not a CAPRI parameter file.
  The Armington elasticities are named:
      esubd(*)   'Elasticity of substitution (M versus D)'   -> rhoArm1
      esubm(*)   'Intra-import elasticity of substitution'   -> rhoArm2
  NOT p_rhoArm1 / p_rhoArm2 as I guessed. Two further parameters are useful:
      eta(*,*)      income elasticity of demand
      epsilon(*,*)  own-price elasticity of demand

  These four are small: esubd and esubm are one line per GTAP sector. The
  whole-file dump you already ran is 143 MB, so the targeted statements below
  are worth having.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 1 -- estnlp: elasticities and estimated PMP terms
*
* PELA is dimensioned region x crop x crop x year, so it is a full CROSS-price
* matrix, not own-price only. The model currently uses own-price elasticities
* and invents the cross effects, so this is the more valuable half.
*
* PELAGRP is the same at crop-group level and pairs with the VB terms.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=PELA output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_PELA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=PELAGRP output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_PELAGRP.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=VD output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_VD.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=VB output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_VB.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=VA output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_VA.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- GTAP Armington elasticities (corrected names)
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=esubd output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\gtap_esubd.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=esubm output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\gtap_esubm.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=etrae output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\gtap_etrae.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=eta output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\gtap_eta.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=epsilon output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\gtap_epsilon.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- bilateral trade flows
*
* The symbol inside this file is Result1, confirmed at
* enerind/capreg_global.gms:30 -- not p_tradeFlows.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\global\trade_flows_ori.gdx symb=Result1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\trade_flows_ori.txt';

*--------------------------------------------------------------------------
* SECTION 4 -- report
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_final.txt"';

$TITLE CAPRI-Python -- dump animal requirement relations from reqrel_17*.gdx
$ONTEXT

  Same explicit form as before: one execute statement per file, no loops.

  Target symbol, confirmed from gams/capreg.gms:2199 --

      execute_unload "...\capreg\reqrel_%BAS%<MS>.gdx"
                     p_animReqCorrFac1,RALL,COLS,ROWS,meta;

  and declared at line 2195 as

      PARAMETER p_animReqCorrFac1(RALL,MAACT,A,REQM);

  So the dimensions are region x animal activity x animal type x
  requirement, which is what feed_requirements.csv needs -- that file is
  currently one of the fully synthetic inputs, and it feeds every livestock
  margin as well as the whole nitrogen balance.

  Output is .txt, not .csv: every .csv your earlier runs produced was 0 bytes
  while the .txt equivalents carried data.

  SECTION 1 is a single cheap statement -- run it alone first. Malta is 32 KB,
  so it returns instantly and shows the real symbol list, in case this
  installation named things differently.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 1 -- symbol listing (run this first, on its own)
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17MT.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_reqrel.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- p_animReqCorrFac1, one statement per member state
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17AL.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_AL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17AT.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_AT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17BA.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_BA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17BG.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_BG.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17BL.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_BL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17CS.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_CS.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17CY.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_CY.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17CZ.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_CZ.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17DE.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_DE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17DK.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_DK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17EE.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_EE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17EL.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_EL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17ES.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_ES.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17FI.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_FI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17FR.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_FR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17HR.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_HR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17HU.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_HU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17IR.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_IR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17IT.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_IT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17KO.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_KO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17LT.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_LT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17LV.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_LV.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17MK.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_MK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17MO.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_MO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17MT.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_MT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17NL.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_NL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17NO.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_NO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17PL.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_PL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17PT.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_PT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17RO.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_RO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17SE.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_SE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17SI.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_SI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17SK.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_SK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17TU.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_TU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\reqrel_17UK.gdx symb=p_animReqCorrFac1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\animReq_UK.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- report
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_reqrel.txt"';

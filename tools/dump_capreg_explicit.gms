$TITLE CAPRI-Python -- explicit gdxdump statements, one per file
$ONTEXT

  No loops. One execute statement per gdx file, in the same form as the
  command that produced coco2.csv.

  Naming confirmed from your capreg directory listing:
     res_17<MS>.gdx      35 files, base year 17
     pmppar_17<MS>.gdx   35 files
     fert_out<MS>.gdx    35 files, NO year prefix
     Turkey is TU here, not TUR

  Output is written as .txt, because the .csv variants in your folder are
  all 0 bytes while the .txt ones carry data. Whatever fails with
  format=csv on this installation does not fail without it.

  SECTION 1 is diagnostic and cheap -- run it first on its own.
  SECTION 2 (DATA2) duplicates ALL_DATA2.txt, which you already have.
  SECTION 3 (PMP terms) is the part that is genuinely missing.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 1 -- symbol listing. Malta is the smallest file (8 KB), so this
* is instant. It reveals the real symbol names inside pmppar before the
* 70 statements below are trusted.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MT.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_pmppar.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17MT.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_res.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- DATA2 from res_17*.gdx
* Already present as ALL_DATA2.txt / out_data2_*.txt from 09/07. Kept only
* so the set is reproducible; skip it if those files are intact.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17AL.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_AL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17AT.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_AT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17BA.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_BA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17BG.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_BG.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17BL.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_BL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17CS.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_CS.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17CY.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_CY.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17CZ.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_CZ.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17DE.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_DE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17DK.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_DK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17EE.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_EE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17EL.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_EL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17ES.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_ES.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17FI.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_FI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17FR.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_FR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17HR.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_HR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17HU.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_HU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17IR.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_IR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17IT.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_IT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17KO.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_KO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17LT.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_LT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17LV.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_LV.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17MK.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_MK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17MO.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_MO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17MT.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_MT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17NL.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_NL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17NO.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_NO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17PL.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_PL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17PT.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_PT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17RO.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_RO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17SE.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_SE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17SI.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_SI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17SK.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_SK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17TU.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_TU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\res_17UK.gdx symb=DATA2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\DATA2_UK.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- PMP quadratic terms from pmppar_17*.gdx
*
* p_pmpQuadTechn is the activity-level diagonal, p_pmpQuadPact the
* group-level term. Together they are CAPRI's Q matrix, which currently
* has no real counterpart in the model at all.
*
* If these come out empty, check _symbols_pmppar.txt from SECTION 1 and
* substitute the correct names.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17AL.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_AL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17AT.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_AT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BA.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_BA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BG.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_BG.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BL.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_BL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CS.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_CS.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CY.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_CY.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CZ.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_CZ.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17DE.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_DE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17DK.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_DK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17EE.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_EE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17EL.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_EL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17ES.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_ES.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17FI.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_FI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17FR.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_FR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17HR.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_HR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17HU.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_HU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17IR.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_IR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17IT.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_IT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17KO.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_KO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17LT.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_LT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17LV.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_LV.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MK.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_MK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MO.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_MO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MT.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_MT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17NL.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_NL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17NO.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_NO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17PL.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_PL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17PT.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_PT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17RO.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_RO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SE.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_SE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SI.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_SI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SK.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_SK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17TU.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_TU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17UK.gdx symb=p_pmpQuadTechn output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadTechn_UK.txt';

execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17AL.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_AL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17AT.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_AT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BA.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_BA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BG.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_BG.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17BL.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_BL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CS.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_CS.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CY.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_CY.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17CZ.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_CZ.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17DE.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_DE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17DK.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_DK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17EE.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_EE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17EL.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_EL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17ES.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_ES.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17FI.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_FI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17FR.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_FR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17HR.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_HR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17HU.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_HU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17IR.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_IR.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17IT.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_IT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17KO.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_KO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17LT.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_LT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17LV.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_LV.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MK.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_MK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MO.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_MO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17MT.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_MT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17NL.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_NL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17NO.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_NO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17PL.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_PL.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17PT.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_PT.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17RO.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_RO.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SE.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_SE.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SI.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_SI.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17SK.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_SK.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17TU.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_TU.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capreg\pmppar_17UK.gdx symb=p_pmpQuadPact output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\quadPact_UK.txt';

*--------------------------------------------------------------------------
* SECTION 4 -- report what was produced
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced.txt"';

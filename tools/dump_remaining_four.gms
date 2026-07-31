$TITLE CAPRI-Python -- dump the four remaining input sources
$ONTEXT

  Same explicit form as before: one execute statement per file, no loops.

  All four locations and symbol names are taken from the GAMS source rather
  than guessed:

    supply elasticities  supply/define_pmp_terms.gms:23
        $if exist '%datdir%\estnlp\results.gdx'
            execute_load '%datdir%\estnlp\results.gdx' VB,VD,p_pelaEst=PELA;
        -> the symbol is PELA, and VB and VD are the PMP terms that come with it.
           NOTE this lives under dat\, not output\results\.

    trade flows          enerind/capreg_global.gms:30
            execute_load "..\dat\global\trade_flows_ori.gdx"
                         p_tradeflowsOri=Result1;
        -> the symbol inside the file is Result1, not p_tradeFlows.

    Armington            dat\arm\GTP57_134.gdx, the GTAP 57-sector aggregation
        -> substitution elasticities. Section 1 will confirm the symbol name.

    world prices         capmod market results, res_*.gdx
        -> these are model OUTPUT, not input data. See the note at the end.

  SECTION 1 lists the symbols in each file. Run it alone first: all four are
  small, it returns in seconds, and it confirms the names before anything
  large is written.

  Output is .txt, since every .csv your earlier runs produced was 0 bytes
  while the .txt equivalents carried data.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 1 -- symbol listings. Run this section on its own first.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_estnlp.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\global\trade_flows_ori.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_tradeflows.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_armington.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\filterTradeFlowsCutoffs.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_armcutoffs.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- supply elasticities and the estimated PMP terms.
*
* PELA is the largest remaining gap in the model: elasticity coverage is
* currently 39.9% by area and arable-only, which makes a price shock put 88%
* of its reallocation into arable land. VB and VD are CAPRI's own estimated
* PMP terms and are worth taking at the same time.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=PELA output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_PELA.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=VB output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_VB.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\estnlp\results.gdx symb=VD output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\estnlp_VD.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- bilateral trade flows.
*
* The model currently carries a 2021 trade matrix inside a 2017 base year, so
* the Armington shares are inconsistent with the supply side. This file should
* let that be put right.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\global\trade_flows_ori.gdx symb=Result1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\trade_flows_ori.txt';

*--------------------------------------------------------------------------
* SECTION 4 -- Armington parameters.
*
* Symbol names are unconfirmed: check _symbols_armington.txt from SECTION 1
* and edit these two lines if they do not match. The whole-file dump on the
* third line is a safe fallback that always works.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=p_rhoArm1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\arm_rhoArm1.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx symb=p_rhoArm2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\arm_rhoArm2.txt';
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\dat\arm\GTP57_134.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\arm_GTP57_134_full.txt';

*--------------------------------------------------------------------------
* SECTION 5 -- report
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_remaining.txt"';

$ONTEXT

  ON WORLD PRICES

  There is no statement for these above, deliberately. World prices are an
  OUTPUT of CAPRI's market module, not an input to it, so they live in the
  capmod results rather than in dat\. Two consequences:

  First, the file name depends on the scenario and settings actually run
  (res_<NTSLVL>_<BAS><SIM>...gdx), so it cannot be written blind. If you have
  a capmod run, send the directory listing of output\results\capmod and the
  right statement can be written for it.

  Second, and more important: the model's base-year fidelity test compares
  its solved prices AGAINST world_prices.csv. If that file is wrong, the test
  confirms the error rather than catching it. This is the one input where the
  main check cannot protect us, which is why it is worth doing properly even
  though the current file looks fine.

$OFFTEXT

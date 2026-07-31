$TITLE CAPRI-Python -- dump the market-side inputs from a capmod run
$ONTEXT

  WHAT TO RUN FIRST
  -----------------
  In the CAPRI GUI: task 'Run scenario' (capmod), base year 2017, with the
  baseline scenario. Any simulation year will do -- the parameters wanted here
  are the calibrated market data, not the scenario outcome. The run writes

      output\results\simini\sim_ini_<NTSLVL><BAS><SIM><MODID>.gdx
      output\results\capmod\res_<NTSLVL>_<BAS><SIM><...>.gdx

  SECTION 0 lists both directories so the actual file names can be read off,
  because they encode the settings used. Run SECTION 0 ALONE FIRST, send
  _dir_simini.txt and _dir_capmod.txt, and the remaining sections can be
  filled in with the real names rather than the placeholders below.

  WHY sim_ini
  -----------
  capmod/load_sim_ini_gdx.gms shows this file carries the calibrated market
  parameters, which is exactly what is missing:

      p_rhoArm1       Armington elasticity, imports vs domestic
      p_rhoArm2       intra-import Armington elasticity
      p_realRhoArm2   the realised value after trimming
      p_tradeFlows    bilateral trade quantities
      p_impPrice      import prices at the border
      p_elasSupp      supply elasticities used by the market model

  These are CAPRI's own calibrated values. The GTAP file examined earlier
  (dat\arm\GTP57_134.gdx) is the raw INPUT to that calibration, not its
  output, which is why its sector-level elasticities did not match the model's
  commodity-level ones.

  ON WORLD PRICES
  ---------------
  p_worldPrices is an intermediate in arm/prepare_market_data.gms and is not
  written to a result file under its own name. It ends up inside DATAOUT in
  the capmod result, keyed by the world-market region. SECTION 3 dumps DATAOUT
  for one member state so the right key can be identified before the full
  file is written -- DATAOUT is large.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 0 -- directory listings. RUN THIS ALONE FIRST.
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_dir_simini.txt"';
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capmod" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_dir_capmod.txt"';

*--------------------------------------------------------------------------
* SECTION 1 -- symbol listing for sim_ini
*
* Replace <SIMINI> below with the real file name from _dir_simini.txt.
*--------------------------------------------------------------------------
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_simini.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- the market parameters, one statement per symbol
*--------------------------------------------------------------------------
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_rhoArm1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_rhoArm1.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_rhoArm2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_rhoArm2.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_realRhoArm2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_realRhoArm2.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_tradeFlows output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_tradeFlows.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_impPrice output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_impPrice.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\<SIMINI>.gdx symb=p_elasSupp output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_elasSupp.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- DATAOUT, for world prices
*
* Replace <RES> with the file name from _dir_capmod.txt. DATAOUT is large, so
* this is worth doing only after the symbol listing confirms the structure.
*--------------------------------------------------------------------------
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capmod\<RES>.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_capmod.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capmod\<RES>.gdx symb=DATAOUT output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\capmod_DATAOUT.txt';

*--------------------------------------------------------------------------
* SECTION 4 -- report
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_market.txt"';

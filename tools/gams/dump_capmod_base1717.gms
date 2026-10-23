$TITLE CAPRI-Python -- market-side inputs from the 2017 base-year capmod result
$ONTEXT

  WHY sim_ini WAS EMPTY
  ---------------------
  Not a failed run. capmod\create_sim_ini_gdx.gms line 569 has the unload
  statement commented out:

    *$ifi not %ghgTechAmmonia%==on execute_unload
    *    '%results_out%\simini\sim_ini_%NTSLVL%%BAS%%SIM%%MODID%.gdx';

  The comment above it explains that it was disabled so parallel scenario runs
  would not collide writing the same file. This version therefore never writes
  sim_ini. SECTION 3 below covers the one-line change if the symbols in it turn
  out to be needed.

  THE FILE WE ACTUALLY WANT
  -------------------------
      res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx

  Reading the naming convention res_<NTSLVL>_<BAS><SIM><scenario><MODID><ResId>:
  BAS=17 and SIM=17, so this is the 2017 base year calibrated against the data
  rather than a projection. Every other file in the directory is SIM=20 through
  50, i.e. 2020-2050 projections, or a member-state slice.

  That is the right vintage for a 2017 base-year model, and it is EU-wide.

  WHAT IS IN IT
  -------------
  capmod unloads DATAOUT, RALL, META and p_INFES. DATAOUT is dimensioned
  (region, region2, cols, rows, year), so the bilateral region pair carries the
  trade flows and the Armington terms (Arm2Commit, Theta, TransitA, TransitB
  are written there by set_and_store_dataout.gms).

  SECTION 1 is the symbol listing and is cheap. Run it alone first: DATAOUT is
  large and it is worth confirming the row keys before dumping it whole.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

*--------------------------------------------------------------------------
* SECTION 1 -- symbol listing of the base-year result. RUN THIS ALONE FIRST.
*--------------------------------------------------------------------------
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capmod\res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_base1717.txt';

*--------------------------------------------------------------------------
* SECTION 2 -- DATAOUT from the base-year result.
*
* Uncomment after SECTION 1 confirms the structure. This carries world prices,
* bilateral trade and the Armington terms, all at the 2017 base year.
*--------------------------------------------------------------------------
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\capmod\res_0_1717cap_after_2014_cal_from_data_caldefaulta.gdx symb=DATAOUT output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\base1717_DATAOUT.txt';

*--------------------------------------------------------------------------
* SECTION 3 -- OPTIONAL: re-enable sim_ini for one run.
*
* Only needed if p_rhoArm1 / p_rhoArm2 / p_realRhoArm2 turn out not to be
* recoverable from DATAOUT. In gams\capmod\create_sim_ini_gdx.gms, remove the
* leading asterisk from line 569 so it reads:
*
*     $ifi not %ghgTechAmmonia%==on execute_unload
*         '%results_out%\simini\sim_ini_%NTSLVL%%BAS%%SIM%%MODID%.gdx';
*
* then re-run capmod ONCE, not in parallel -- the collision the comment warns
* about only arises with simultaneous scenario runs. Restore the asterisk
* afterwards. The file then appears and these statements will work:
*--------------------------------------------------------------------------
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_rhoArm1 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_rhoArm1.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_rhoArm2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_rhoArm2.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_realRhoArm2 output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_realRhoArm2.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_tradeFlows output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_tradeFlows.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_impPrice output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_impPrice.txt';
* execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\simini\sim_ini_01717defaulta.gdx symb=p_elasSupp output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\mkt_p_elasSupp.txt';

*--------------------------------------------------------------------------
* SECTION 4 -- report
*--------------------------------------------------------------------------
execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_market.txt"';

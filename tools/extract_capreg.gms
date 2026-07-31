$TITLE CAPRI-Python -- batch export of capreg results via gdxdump
$ONTEXT

  WHAT THIS DOES
  --------------
  Runs the same gdxdump command you already used for coco2.csv, but loops over
  every member state file in output\results\capreg\.

  HOW TO RUN
  ----------
  1. Open in GAMS Studio, press F9.
  2. STEP 0 below writes a listing of what is actually in your capreg folder to
     capri_export\_filelist.txt. Read that file before running the rest -- the
     pmppar naming in particular varies between CAPRI installations, and the
     base-year prefix may not be 17.
  3. Adjust %bas% and the MS set if the listing disagrees, then run again.

  A NOTE ON PERCENT SIGNS
  -----------------------
  Do not replace the MS loop with a shell wildcard (for %f in (*.gdx)). GAMS
  substitutes %...% at compile time, so the shell variable gets eaten. The
  explicit set below avoids the problem.

  START SMALL
  -----------
  Set onlyOne to 1 for the first run. That dumps Germany only, so the ingest
  path can be verified on one file before 35 are produced. DATA2 is a large
  symbol -- coco2.csv was 453 MB for national data alone, and these are
  regional.

$OFFTEXT

*-------------------------------------------------------------------------
* PATHS -- edit these two lines only
*-------------------------------------------------------------------------
$set capri   C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0
$set bas     17

$set results %capri%\output\results
$set out     %capri%\capri_export

* set to 1 for a single-country test run, 0 for all member states
scalar onlyOne / 1 /;

*-------------------------------------------------------------------------
* Member states. Codes taken from the region keys in coco2.csv, so they
* match CAPRI's own naming (BL = Belgium+Luxembourg, IR = Ireland,
* MO/KO/MK/CS = the Western Balkans set).
*-------------------------------------------------------------------------
set ms 'CAPRI member state codes' /
   AT, BL, BG, CY, CZ, DE, DK, EE, EL, ES, FI, FR, HR, HU, IR, IT
   LT, LV, MT, NL, PL, PT, RO, SE, SI, SK, UK, NO
   AL, BA, CS, KO, MK, MO, TUR
/;

set msRun(ms) 'member states actually processed';
msRun(ms) = yes;
msRun(ms) $ (onlyOne and (not sameas(ms,'DE'))) = no;

file cmd / '' /;
put cmd;

*-------------------------------------------------------------------------
* STEP 0 -- create the output folder and list what is really there
*-------------------------------------------------------------------------
put_utility 'exec' / 'cmd /c if not exist "%out%" mkdir "%out%"';
put_utility 'exec' / 'cmd /c dir /b "%results%\capreg" > "%out%\_filelist.txt"';
put_utility 'exec' / 'cmd /c dir /b "%results%\estnlp" >> "%out%\_filelist.txt"';

*-------------------------------------------------------------------------
* STEP 1 -- DATA2 from capreg results.  HIGHEST PRIORITY.
*
* The master regional cube: region x activity x item x year. This carries YILD
* for livestock as well as crops -- which COCO does not have at all -- and it
* is regional rather than national. This one symbol fixes the yield vintages,
* the missing regional detail, and the livestock yields together.
*-------------------------------------------------------------------------
loop(msRun,
   put_utility 'exec' /
     'gdxdump "%results%\capreg\res_%bas%' msRun.tl:0 '.gdx"'
     ' symb=DATA2 format=csv'
     ' output="%out%\DATA2_' msRun.tl:0 '.csv"';
);

*-------------------------------------------------------------------------
* STEP 2 -- PMP terms.
*
* p_pmpQuadTechn is the activity-level diagonal, p_pmpQuadPact the group-level
* term. Together they are CAPRI's Q matrix directly.
*
* If these produce nothing, check _filelist.txt: the pmppar files often carry a
* result-id or aggregation suffix after the country code, in which case add it
* to the name below.
*-------------------------------------------------------------------------
loop(msRun,
   put_utility 'exec' /
     'gdxdump "%results%\capreg\pmppar_%bas%' msRun.tl:0 '.gdx"'
     ' symb=p_pmpQuadTechn format=csv'
     ' output="%out%\pmpQuadTechn_' msRun.tl:0 '.csv"';

   put_utility 'exec' /
     'gdxdump "%results%\capreg\pmppar_%bas%' msRun.tl:0 '.gdx"'
     ' symb=p_pmpQuadPact format=csv'
     ' output="%out%\pmpQuadPact_' msRun.tl:0 '.csv"';

   put_utility 'exec' /
     'gdxdump "%results%\capreg\pmppar_%bas%' msRun.tl:0 '.gdx"'
     ' symb=p_pmpFeedInpCoeff format=csv'
     ' output="%out%\feedCoeff_' msRun.tl:0 '.csv"';
);

*-------------------------------------------------------------------------
* STEP 3 -- fertiliser output (fills nutrient_coefs, currently synthetic)
*-------------------------------------------------------------------------
loop(msRun,
   put_utility 'exec' /
     'gdxdump "%results%\capreg\fert_out' msRun.tl:0 '.gdx"'
     ' symb=fert_out format=csv'
     ' output="%out%\fertOut_' msRun.tl:0 '.csv"';
);

*-------------------------------------------------------------------------
* STEP 4 -- estnlp elasticities.  Single file, not per member state.
*
* PELA is the econometric supply-elasticity estimate set. The model currently
* has real elasticities for 132 of 248 regions and 14 of 40 activities; this is
* what closes that gap.
*
* If the symbol name is not PELA in your installation, open results.gdx in
* GAMS Studio (double-click) to see the symbol list, and edit below.
*-------------------------------------------------------------------------
put_utility 'exec' /
  'gdxdump "%results%\estnlp\results.gdx" symb=PELA format=csv'
  ' output="%out%\estnlp_PELA.csv"';

*-------------------------------------------------------------------------
* STEP 5 -- report
*-------------------------------------------------------------------------
put_utility 'exec' / 'cmd /c dir /b "%out%" > "%out%\_produced.txt"';

display 'Export finished. Check capri_export\_filelist.txt for what exists,';
display 'and capri_export\_produced.txt for what was written.';

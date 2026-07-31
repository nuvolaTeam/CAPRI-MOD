$TITLE CAPRI-Python -- discover and dump every res_*.gdx in capreg
$ONTEXT

  Finds the res_*.gdx files itself instead of guessing their names, then runs
  the same gdxdump command you used for coco2.csv on each one.

  Open in GAMS Studio, edit the one path below, press F9.

  WHY forfiles AND NOT "for %f in (...)"
  --------------------------------------
  GAMS substitutes %...% at compile time, so a shell FOR loop never survives.
  forfiles uses @ for its variables, which GAMS leaves alone. It also echoes
  @fname already quoted and without the .gdx extension, which is exactly the
  form a GAMS set needs -- a bare res_17DE.gdx would break the set because the
  dot is GAMS's tuple separator.

  Everything happens at compile time ($call, $include) because the file list
  must exist before the set is read.

$OFFTEXT

*--- edit this line only -------------------------------------------------
$set capri  C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0

$set src    %capri%\output\results\capreg
$set out    %capri%\capri_export

*--- 1. discover -------------------------------------------------------------
$call 'cmd /c if not exist "%out%" mkdir "%out%"'
$call 'cmd /c forfiles /p "%src%" /m res_*.gdx /c "cmd /c echo @fname" > "%out%\_reslist.inc" 2>nul'

set resfile 'res_*.gdx files found, without extension' /
$include %out%\_reslist.inc
/;

*--- 2. dump -----------------------------------------------------------------
file cmd / '' /;
put cmd;

loop(resfile,
   put_utility 'exec' /
     'gdxdump "%src%\' resfile.tl:0 '.gdx"'
     ' symb=DATA2 format=csv'
     ' output="%out%\DATA2_' resfile.tl:0 '.csv"';
);

*--- 3. report ---------------------------------------------------------------
put_utility 'exec' / 'cmd /c dir /b "%out%" > "%out%\_produced.txt"';

display resfile;
display 'Files found are listed above. Output is in capri_export\.';

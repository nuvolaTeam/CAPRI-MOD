$ontext
  export_pmp_2030.gms - dump CAPRI star 3.0's 2030 PMP terms for every country in one run (for capri-mod)

  Plain gdxdump, as in the earlier dump scripts: no embedded Python, nothing in the installation is changed.
  Open in GAMS Studio and run (F9).

  1. Every pmppar_21730*.gdx under C:\capri-star3.0\output (normally output\results\baseline\, one file per
     country; written by baseline\fin_cal.gms l. 143, read by capmod\create_sim_ini_gdx.gms l. 491) is dumped
     whole, like:  gdxdump <file>.gdx > <file>.txt
     It contains p_pmpQuadTechn, p_pmpQuadPact, p_pmpCnst, p_pmpQuadLandTypes, p_pmpCnstLandTypes or
     p_pmpLandSupplyTail, p_pmpFeedInpCoeff, p_scaleQuot, META.
  2. If present, CAPRI's econometric estimates behind those terms (supply\define_pmp_terms.gms):
     dat\estnlp\results.gdx, symbols VB, VD, PELA.
  3. files_found.txt lists what was dumped.

  Output: C:\capri-star3.0\pmp_export\  and the zip C:\capri-star3.0\pmp_export.zip  -> upload the zip.
  If your CAPRI folder is elsewhere, change ROOT in the line "set ROOT=..." below.
$offtext

$onEchoV > "C:\capri-star3.0\export_pmp_2030.cmd"
@echo off
set ROOT=C:\capri-star3.0
set OUT=%ROOT%\pmp_export
if not exist "%OUT%" mkdir "%OUT%"
echo PMP files (pmppar_21730*.gdx) under %ROOT%\output: > "%OUT%\files_found.txt"
dir /s /b "%ROOT%\output\pmppar_21730*.gdx" >> "%OUT%\files_found.txt" 2>&1
for /f "delims=" %%f in ('dir /s /b "%ROOT%\output\pmppar_21730*.gdx" 2^>nul') do (
    gdxdump "%%f" > "%OUT%\%%~nf.txt"
)
echo estnlp estimates: >> "%OUT%\files_found.txt"
if exist "%ROOT%\dat\estnlp\results.gdx" (
    echo %ROOT%\dat\estnlp\results.gdx >> "%OUT%\files_found.txt"
    gdxdump "%ROOT%\dat\estnlp\results.gdx" symbols > "%OUT%\estnlp_results_symbols.txt"
    gdxdump "%ROOT%\dat\estnlp\results.gdx" symb=VB   > "%OUT%\estnlp_results_VB.txt"
    gdxdump "%ROOT%\dat\estnlp\results.gdx" symb=VD   > "%OUT%\estnlp_results_VD.txt"
    gdxdump "%ROOT%\dat\estnlp\results.gdx" symb=PELA > "%OUT%\estnlp_results_PELA.txt"
) else (
    echo not found: %ROOT%\dat\estnlp\results.gdx >> "%OUT%\files_found.txt"
)
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%ROOT%\pmp_export.zip' -Force"
$offEcho

execute 'cmd /c "C:\capri-star3.0\export_pmp_2030.cmd"';

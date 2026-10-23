$ontext
  export_capmod_results.gms - dump CAPRI star 3.0's 2030 scenario results (CAPMOD) for capri-mod (KNOWN_ISSUES K13)

  Plain gdxdump, as export_pmp_2030.gms: nothing in the installation is changed. Open in GAMS Studio and run (F9).

  What capri-mod needs: CAPRI's own results of the Farm-to-Fork / Green Deal scenarios run from the 2030 reference,
  in particular the EU dairy market (raw milk and dairy product prices, production, processing, demand, trade).
  K13 (Farm-to-Fork milk price +32% here against CAPRI's +1.5% in JRC121368) cannot be settled without them.

  1. files_found.txt lists every CAPMOD result file for 2030 (res_*1730*.gdx under output\results\capmod).
  2. Each one except the reference run already uploaded (names containing "refpol") is dumped whole, as the
     reference was:  gdxdump <file>.gdx > <file>.txt
  3. The dumps are zipped into C:\capri-star3.0\capmod_export.zip -> upload the zip (or, if it is very large, only
     the dump of the Farm-to-Fork run).

  If your CAPRI folder is elsewhere, change ROOT in the line "set ROOT=..." below.
$offtext

$onEchoV > "C:\capri-star3.0\export_capmod_results.cmd"
@echo off
set ROOT=C:\capri-star3.0
set OUT=%ROOT%\capmod_export
if not exist "%OUT%" mkdir "%OUT%"
echo CAPMOD 2030 result files under %ROOT%\output: > "%OUT%\files_found.txt"
dir /s /b "%ROOT%\output\res_*1730*.gdx" >> "%OUT%\files_found.txt" 2>&1
for /f "delims=" %%f in ('dir /s /b "%ROOT%\output\res_*1730*.gdx" 2^>nul ^| findstr /v /i "refpol"') do (
    gdxdump "%%f" > "%OUT%\%%~nf.txt"
)
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%ROOT%\capmod_export.zip' -Force"
$offEcho

execute 'cmd /c "C:\capri-star3.0\export_capmod_results.cmd"';

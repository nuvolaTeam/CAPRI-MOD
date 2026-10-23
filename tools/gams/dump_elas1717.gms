$TITLE CAPRI-Python -- dump p_elasSupp from the clean base-year GDX
$ONTEXT

  This replaces the Excel export (elas1717defaulta_export.xlsx) with a direct
  GDX read of the same file, the base-year 2017 elasticities:

      output\results\arm\elas1717defaulta.gdx

  p_elasSupp is the market-level supply elasticity matrix. Its own-price
  diagonal came back empty when read from Excel, which is exactly the kind of
  silent misalignment the Excel path produces. Reading the GDX directly avoids
  it. If the diagonal is present here and absent in the Excel, that settles
  whether the Excel export is trustworthy.

  Run this alone. It writes two files: the symbol listing (cheap, confirms
  structure) and p_elasSupp itself.

$OFFTEXT

$call 'cmd /c if not exist "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export" mkdir "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export"'

* symbol listing first -- confirms dimensions and the exact set names
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\arm\elas1717defaulta.gdx > C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_symbols_elas1717.txt';

* the supply elasticities
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\arm\elas1717defaulta.gdx symb=p_elasSupp output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\elas1717_p_elasSupp.txt';

* two companions worth having from the same file, at no extra run cost:
*   p_hessNQSupp -- the Hessian CAPRI actually uses in the supply NQ function
execute 'gdxdump C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\output\results\arm\elas1717defaulta.gdx symb=p_hessNQSupp output=C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\elas1717_p_hessNQSupp.txt';

execute 'cmd /c dir /b "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\elas1717_*.txt" > "C:\Users\DELL\Desktop\CAPRI\star_3.0\capri-star3.0\capri_export\_produced_elas.txt"';

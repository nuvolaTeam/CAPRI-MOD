# capri_reference: CAPRI's own files, for the parity tests

These are CAPRI files from the project lead's installation, converted to CSV. They are read-only and are read only by
the tests and the parity runs, never by the model (docs/design/CAPTRD_MOD.md section 6). One folder is a source of
the data pipeline: `sets/simini_21730`, read by `tools/build/build_code_lists.py` (the code lists of
`capri_data/schema/codes`, 29 October 2026). They are
large, so they are left out of the zip packages. Each folder is rebuilt from the uploaded originals by the tool
named below.

| Folder | Original | Content | Tool |
|---|---|---|---|
| `capreg_tseries/17/<CC>.csv.gz` | `Capreg_tseries/<CC>_17.gdx` (35 files) | CAPREG's time series `DATA(region, col, row, t)`, 1984–2018 plus BAS, BASM, CUR, MEAN, TRD, Y: the input CAPTRD reads as DATA1 (captrd.gms l. 486-505) | `tools/build_capreg_tseries_reference.py --src Capreg_tseries.zip` |
| `capreg_base/17/<CC>.csv.gz` | text dumps `res_17<CC>.txt` of CAPREG's base-year results `res_17<CC>.gdx` (27 files: the 26 EU codes, Belgium and Luxembourg being BL, and Norway; the UK, Turkey and the Western Balkans are missing) | CAPREG's base-year data `DATA2(region, col, row, "Y")`, the input CAPTRD reads as BASM (captrd.gms l. 528-580); 15 significant digits | `tools/build/build_capreg_base_reference.py --src DIR_OR_ZIP` |
| `coco2/17/coco2_output.csv.gz` | text listing `coco2.csv` of COCO's `coco2_output.gdx` (upload coco2.zip) | COCO's `DATA2(region, item, col, row, t)`, items INI, COCO1, COCO2, 1984–2019: what CAPTRD loads as dataMS (load_coco1_data.gms l. 24); 15 significant digits | `tools/build/build_coco2_reference.py --src coco2.zip` |
| `fao_agg/17/<symbol>.csv.gz` | text listing `FAO_agg_17_defaulta.csv` of the global database `fao_agg_17_defaulta.gdx` (upload FAO_agg_17_defaulta.zip) | `p_biofuelData`, `p_aglinkGrowthFactor` (load_coco1_data.gms l. 360); columns d0…dn, value, eps | `tools/build/build_fao_agg_reference.py --src FAO_agg_17_defaulta.zip` |
| `captrd_results/1770/<respos>.csv.gz` | `results_1770.gdx` (base 2017, simulation years 2018–2070) | CAPTRD's `p_result(region, col, row, t, respos)`, one file per result position (Step1, support, support1, wVarErr, step2, step3, series, P_Data, data statistics, …); `respos_counts.csv` lists all positions and `settings.csv` the run settings | `tools/build_captrd_results_reference.py --src results_1770.gdx --tag 1770` |
| `sets/simini_21730/<SET>.csv` | `sim_ini_21730.gdx` (CAPMOD restart file of the endotech Green Deal 2030 run) | the 1,972 CAPRI sets of that run (global sets.gms and loaded modules, with the run's switches applied), one file per set with `_index.csv`; sets defined only in CAPTRD (sets_captrd.gms) are not among them | `tools/build_capri_sets_reference.py --src sim_ini_21730.gdx --tag simini_21730` |

Columns of the data files: `region, col, row, t, value, eps`.
- A record CAPRI stored as Eps (an explicit zero) has value 0 and eps = 1.
- A record CAPRI did not store is absent.

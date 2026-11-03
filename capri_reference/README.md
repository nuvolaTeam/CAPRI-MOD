# capri_reference: CAPRI's own files, for the parity tests

These are CAPRI files from the project lead's installation, converted to CSV. They are read-only and are read only by
the tests and the parity runs, never by the model (docs/design/CAPTRD_MOD.md section 6). Two folders are sources of
the data pipeline: `sets/simini_21730`, read by `tools/build/build_code_lists.py` (the code lists of
`capri_data/codes` and, since 3 November 2026, CAPRI's RMS and RMS_TO_RM in `capri_data/shared`), and
`captrd_results/1770`, read by `tools/build/build_captrd_trajectory.py` (the CAPTRD 2030 scenario). They are
large, so they are left out of the zip packages. Each folder is rebuilt from the uploaded originals by the tool
named below.

| Folder | Original | Content | Tool |
|---|---|---|---|
| `capreg_tseries/17/<CC>.csv.gz` | `Capreg_tseries/<CC>_17.gdx` (35 files) | CAPREG's time series `DATA(region, col, row, t)`, 1984–2018 plus BAS, BASM, CUR, MEAN, TRD, Y: the input CAPTRD reads as DATA1 (captrd.gms l. 486-505) | `tools/build_capreg_tseries_reference.py --src Capreg_tseries.zip` |
| `capreg_base/17/<CC>.csv.gz` | CAPREG's base-year results `res_17<CC>.gdx`: 27 as text dumps `res_17<CC>.txt` (upload res_17zip.zip and single files), 8 as GDX files (UK, TU, AL, MK, CS, MO, BA, KO; uploaded 29 October 2026). <CC> is CAPTRD's file code, the first two characters of the country (TU for TUR) | CAPREG's base-year data `DATA2(region, col, row, "Y")`, the input CAPTRD reads as BASM (captrd.gms l. 528-580); 15 significant digits from the dumps, 17 from the GDX files | `tools/build/build_capreg_base_reference.py --src DIR_OR_ZIP [--src DIR]` |
| `coco2/17/coco2_output.csv.gz` | text listing `coco2.csv` of COCO's `coco2_output.gdx` (upload coco2.zip) | COCO's `DATA2(region, item, col, row, t)`, items INI, COCO1, COCO2, 1984–2019: what CAPTRD loads as dataMS (load_coco1_data.gms l. 24); 15 significant digits | `tools/build/build_coco2_reference.py --src coco2.zip` |
| `fao_agg/17/<symbol>.csv.gz` | text listing `FAO_agg_17_defaulta.csv` of the global database `fao_agg_17_defaulta.gdx` (upload FAO_agg_17_defaulta.zip) | `p_biofuelData`, `p_aglinkGrowthFactor` (load_coco1_data.gms l. 360); columns d0…dn, value, eps | `tools/build/build_fao_agg_reference.py --src FAO_agg_17_defaulta.zip` |
| `captrd_results/1770/<respos>.csv.gz` | `results_1770.gdx` (base 2017, simulation years 2018–2070) | CAPTRD's `p_result(region, col, row, t, respos)`, one file per result position (Step1, support, support1, wVarErr, step2, step3, series, P_Data, data statistics, …); `respos_counts.csv` lists all positions and `settings.csv` the run settings | `tools/build_captrd_results_reference.py --src results_1770.gdx --tag 1770` |
| `sets/simini_21730/<SET>.csv` | `sim_ini_21730.gdx` (CAPMOD restart file of the endotech Green Deal 2030 run) | the 1,972 CAPRI sets of that run (global sets.gms and loaded modules, with the run's switches applied), one file per set with `_index.csv`; sets defined only in CAPTRD (sets_captrd.gms) are not among them | `tools/build_capri_sets_reference.py --src sim_ini_21730.gdx --tag simini_21730` |
| `simini/simini_21730/<symbol>.csv.gz` | `sim_ini_21730.gdx` (the same restart file as `sets/simini_21730`) | CAPRI's calibrated 2030 market state for the move onto CAPRI's market regions and the ports' checks: the 37 symbols listed with their use in `tools/build/simini_reference_symbols.csv` (DATA, the trade flows and prices, TRQs, levies, entry prices, Armington and CES parameters, the GL demand and NQ Hessians, the market variables' levels and bounds), with `_index.csv`; parameters `d0…dn, value, eps`, variables `d0…dn, level, eps, lower, upper, marginal`; +INF/-INF as inf/-inf, NA as nan. `--check sim_ini_21730_1.gdx` found the 37 symbols identical in the second upload (2 November 2026) | `tools/build/build_simini_reference.py --src sim_ini_21730.gdx --tag simini_21730` |

Columns of the data files: `region, col, row, t, value, eps`.
- A record CAPRI stored as Eps (an explicit zero) has value 0 and eps = 1.
- A record CAPRI did not store is absent.

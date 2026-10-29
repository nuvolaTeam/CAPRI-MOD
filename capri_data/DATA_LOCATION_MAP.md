# CAPRI-mod: where the data live in CAPRI (folder, file, symbol)

Status: revised 20 October 2026 against the code. A reference for rebuilding the data or moving to a new base year.
The symbol names are CAPRI's (checked against its GAMS source and the symbol dictionary
`capri_mod/data/capri_symbol_dictionary.json`, 2,429 symbols); the file locations follow CAPRI's folder conventions
and should be confirmed in the installation at hand. Which CAPRI file each shipped input was actually built from is
stated in the builder's docstring (`tools/build_*.py`) and in `DATA_SOURCING_REGISTRY.json`.

Paths use CAPRI's macros: `%RESULTS_OUT%` = the `output/results/` folder, `%results_in%` = the results database,
`%BAS%` = base year, `%MS%` = member state.

## A. Base data: CAPRI's regional results (what the 2017 inputs are built from)

The 2017 regional inputs (areas, yields, prices, costs, premiums, herds' coefficients, feed, fertiliser) come from
CAPRI's capreg results per member state, `res_17<MS>.gdx` (symbol `DATA2`: rows such as LEVL, YILD, MPRI, TOIN,
PRME, NITF/PHOF/POTF, feed use), extracted for all 27 member states (`tools/build/build_capri_base.py`,
`tools/build/build_crop_economics_2017.py`; region map `shared/region_capri_map.csv`).

| Need | Symbol | Location |
|---|---|---|
| regional database (areas, yields, herds, economics) | `DATA2` | `results/capreg/res_%BAS%<MS>.gdx` |
| regional database before estimation | `p_regioData` | `results/capreg/...regio...gdx` |
| market balances and prices (SUA) | `p_dataMarket` | `results/global/fao_agg_%BAS%_<agg>.gdx` (the 2017 file used: `FAO_agg_17_defaulta`) |
| supply-utilisation sheet | `p_sua_final` | `results/fao/faodata.gdx` |

Fills: `base_areas.csv`, `yields.csv`, `variable_costs.csv`, `crop_premium.csv`, the livestock coefficient files,
`livestock_feed_coef.csv`, `capreg_nutrient_coefs.csv` (from DATA2); `world_prices.csv` and the market base balances (from
`p_dataMarket`).

## B. Elasticities and PMP terms (for a full re-base; otherwise keep 2017)

| Model file | Symbol | Location |
|---|---|---|
| `supply_elasticities_regional.csv`, `pmp_own_price_elasticities.csv` | `p_supplyElas` / `p_pelaEst` | supply estimation results (PELA; the shipped file is from estnlp PELA) |
| `sources/capreg/pmp_quad_techn.csv`, `pmp_quad_pact.csv`, `sources/baseline_pmp/pmp_quad_techn_2030.csv` ... | `p_pmpQuadTechn`, `p_pmpQuadPact` and the other PMP terms | pmppar results |
| land market (`land_market_2017.csv`) | `p_pmpQuadLandTypes` | pmppar results |

PMP terms are estimation outputs: a new base needs them re-estimated by CAPRI, not copied; mixing 2017 PMP terms
with newer prices is what the validator's vintage check is meant to catch.

## C. Market model parameters

| Model file | Symbol | Location |
|---|---|---|
| `bilateral_flows_<year>.csv`, `bilateral_regions_<year>.csv`, `bilateral_trq_<year>.csv` | CAPRI's market results of the year | capmod market results (`tools/build/build_bilateral_market.py`) |
| `armington_rho.csv` | `p_rhoArm1`, `p_rhoArm2` | `arm/market1.gms`, `special_ch/market1_ch.gms` |
| biofuel files | `p_bioDat` and the biofuel parameters | `baseline/trace_dataPrep.gdx`, `fao_agg`; calibration as `biofuel/def_biofuel_params.gms` (`tools/build/build_biofuel_market.py`) |
| dairy block | `p_hessNQDairy` and the dairy data | `elas_2_1730` and market results (`tools/build/build_dairy_processing.py`) |

## D. Policy and environment

| Model file | Symbol | Location |
|---|---|---|
| `crop_premium.csv`, `cap_payments.csv` | `DATA2` PRME | capreg results |
| `tariffs.csv` | CAPRI's total protection from bilateral import and FOB prices | 2017 market results (`tools/build/build_tariffs_2017.py`) |
| manure and enteric CH4, CO2 coefficients | CH4MAN, CH4ENT, CO2LIM, urea shares | capreg / envind results (`tools/build/build_ghg_coefs_2017.py`) |
| mitigation options | `p_ghgMiti`, `p_litRevFertTechs`, ammonia technology tables | `dat/scen/ghgtech`, `dat/miterra`, `envind/*.gms` (`tools/build_*` named in `DATA_DICTIONARY.md`) |

`gascoeff_params.json` (`p_gasEmis`, `envind/gascoeff.gms`) and `dairy_processing_params.json` are archived and not
read by the model (`archive/README.md`).

## Confirming a symbol before exporting

```shell
python capri_mod/data/find_symbol.py gdx  path/to/file.gdx      # list the symbols in a GDX
python capri_mod/data/find_symbol.py search yield               # search CAPRI's symbol descriptions
python tools/build/gdx_dump_symbol.py path/to/file.gdx SYMBOL OUT.csv # export (needs gamsapi and GAMS's gdx library)
gdxdump path/to/file.gdx symb=SYMBOL format=csv > OUT.csv       # or with GAMS itself
```

The dimension layout of a symbol (e.g. region × item × year) is known only once it is dumped; expect a reshaping step
to fit the model's format.

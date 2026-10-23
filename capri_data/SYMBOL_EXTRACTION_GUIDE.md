# CAPRI-mod: symbol extraction guide

Status: revised 20 October 2026 against the code. The extraction list below was written to replace two inputs that
were then synthetic (`feed_requirements.csv`, `nutrient_coefs.csv`); both have since been built from CAPRI's capreg
results (`DATA2` of `res_17<MS>`, registry `REAL_CAPRI`), not from the symbols first proposed here. The list is kept
as a reference for a rebuild or a new base year; the folder and file map is `DATA_LOCATION_MAP.md`.

## Finding a symbol

CAPRI's GAMS source declares 2,429 symbols with a one-line description each, collected in
`capri_mod/data/capri_symbol_dictionary.json`:

```shell
python capri_mod/data/find_symbol.py search <keyword>   # search the descriptions
python capri_mod/data/find_symbol.py needs              # the model's inputs and their candidate symbols
python capri_mod/data/find_symbol.py gdx <file.gdx>     # list the symbols in a GDX
```

Match on the description, not on the file name: `nutrient_cont_usda` sounds like fertiliser data but holds USDA food
nutrient contents, and `feed_agri` holds feed use, not feed requirements.

## Extraction list

| Model input | Symbol actually used | Alternatives considered | Export |
|---|---|---|---|
| `feed_requirements.csv` (feed per head) | `DATA2` feed rows of `res_17<MS>` (fresh matter to dry matter) | `p_feedInpCoeff` ("feed input coefficients (fresh matter) by activity"), `v_feedInpCoeff` | `gdxdump res_17<MS>.gdx symb=DATA2 format=csv` |
| `nutrient_coefs.csv` (N, P2O5, K2O per ha) | `DATA2` NITF, PHOF, POTF | `p_FertPerHa` ("fertiliser use per ha for CAPRI regions"), `v_minfert` | as above |
| areas, yields, herds (new base year) | `DATA2` LEVL, YILD, HERD | `p_regioData`, `p_nutsLevl` ("given hectares at NUTS-2 level") | as above |
| prices and market balances (new base year) | `p_dataMarket` in `fao_agg_<BAS>_<agg>.gdx` | – | `gdxdump fao_agg_<BAS>_<agg>.gdx symb=p_dataMarket format=csv` |
| biofuel data | CAPRI's 2030 market results and `biofuel/def_biofuel_params.gms` (`tools/build/build_biofuel_market.py`) | `p_bioDat` ("consolidated biofuel data from AGLINK and FO LICHT"), `p_bioDemPar` | – |

`tools/build/gdx_dump_symbol.py GDX SYMBOL OUT.csv` does the export in Python (needs the `gamsapi` package and GAMS's gdx
library; `--nonzero` keeps non-zero rows only). After adding or replacing a file, run
`python -m capri_mod.data.validate_data capri_data`.

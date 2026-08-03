# CAPRI-mod — Where the Data Lives: Folder / File / Symbol Map

**What you asked for:** for each thing the model needs — roughly *where* the file is in
a CAPRI installation, and *which symbol* it must contain.

Key idea (this makes it manageable): CAPRI does **not** store one symbol per model input.
Most base data lives in a **handful of master multidimensional containers**. Export those
few symbols and everything else is sliced out of them on the Python side. You are chasing
**~6 symbols, not 25.**

Paths use CAPRI's own macros: `%RESULTS_OUT%` = your `output/results/` folder,
`%results_in%` = the results database you unzipped, `%BAS%` = base year, `%reg_agg%` =
region aggregation, `%MS%` = member state.

---

## A. The master containers (get these — they cover most files)

| Symbol | Contains | Folder / GDX file |
|---|---|---|
| **`p_sua_final`** | areas, animal heads, **yields** (supply-utilisation sheet) | `results_in/fao/faodata.gdx` |
| **`p_regioData`** | regional DB (areas, yields, herds, mapped from Eurostat) | `output/results/capreg/…regio…gdx` |
| **`p_dataMarket`** | market balances **+ producer/world prices** (SUA) | `output/results/baseline/trace_dataPrep.gdx` (or `global/fao_agg_<BAS>_<agg>.gdx`) |
| **`p_activityLevel`** | activity levels (1000 ha or heads) — areas + herds | results DB (capreg estimator output) |

Fills: `base_areas.csv`, `yields.csv`, `animal_numbers.csv`, `producer_prices.csv`,
`world_prices.csv`, `fao_market_baseline.json`, `land_availability.csv`.

---

## B. The two SYNTHETIC files — highest priority (get these first)

| Model file | Symbol | Meaning | Folder / GDX |
|---|---|---|---|
| `feed_requirements.csv` | **`p_feedInpCoeff`** | feed input coeff. per head | `restart_in/feed/mefed_<BAS>…gdx` |
| `nutrient_coefs.csv` | **`p_FertPerHa`** | fertiliser use per ha, by region | results DB (fertiliser/envind output) |

These remove the last two synthetic datasets in the model.

---

## C. Elasticities & PMP (for a full re-base; else keep 2017)

| Model file | Symbol | Folder / GDX |
|---|---|---|
| `fao_demand_own_elas_eu.json` | **`p_demandElas`** | `results_in/global/fao_agg_<BAS>_<agg>.gdx` |
| `supply_elasticities_regional.csv`, `pmp_own_price_elasticities.csv` | **`p_supplyElas`** / `p_pelaEst` | results DB (PELA output) |
| `pmp_diagonal_terms.csv`, `pmp_crossgroup_terms.csv`, `input_requirements.csv` | **`p_pmpQuadPact`** + PMP terms | results DB (supply estimation) |

Note: PMP terms are estimation outputs. A new base needs them **re-estimated** by CAPRI,
not just copied — mixing 2017 PMP with newer prices is what the validator blocks.

---

## D. Biofuel (upgrade the module from literature to CAPRI coefficients)

| Need | Symbol | Meaning | Folder / GDX |
|---|---|---|---|
| biofuel conversion/demand | **`p_bioDat`** | "consolidated biofuel data from AGLINK and FO LICHT" | `output/results/baseline/trace_dataPrep.gdx` **and** `global/fao_agg_<BAS>…gdx` |

(The 2017 `fao_agg` you already sent likely contains `p_bioDat` — it was there, just unnamed.)

---

## E. Policy & environment (low priority — current values fine)

| Model file | Symbol | Folder / GDX |
|---|---|---|
| `cap_payments.csv` | `p_premium` / `p_directPay` | policy results |
| `eu_mfn_tariffs.csv` | `p_tariffs` ("ad valorem tariff rates") | policy/market DB |
| `armington_params.csv` | `p_sigma_up` (upper-nest substitution) | market DB |
| `manure_ch4_ef_regional.csv`, `crop_nutrient_export.csv` | `p_emisManure`, `p_cropNutrient` | envind results |
| `gascoeff_params.json` | `p_gasEmis` | envind results |

---

## How to confirm a symbol is in *your* GDX before exporting

```
python capri_mod/data/find_symbol.py gdx  output/results/…/file.gdx   # lists symbols
python capri_mod/data/find_symbol.py search yield                     # search by concept
```
Then export with GAMS:
```
gdxdump  <file>.gdx  symb=<SYMBOL>  format=csv  >  out.csv
```

## Realistic minimum to finish the model
Just **B** (two symbols: `p_feedInpCoeff`, `p_FertPerHa`) makes every model input real.
Add **A + C + D** only if you want a full newer-base rebuild.

## Honest caveat
Symbol names and folder patterns are verified against CAPRI's GAMS source. The exact
*dimension layout* of each symbol (e.g. does `p_sua_final` come out region×item×year?)
I can only confirm once you dump one — there may be a small reshaping step to fit the
model's format. But you'll be extracting the **right** symbol, which was the hard part.

# CAPRI-Python — Symbol Extraction Guide

**Solves the "which data out of hundreds of symbols" problem.** For each model input,
the exact CAPRI symbol, what it means, which GDX holds it, and the command to export it.

Built from CAPRI's own GAMS source: 2,429 symbols mapped to their descriptions
(`capri_symbol_dictionary.json`). Search any topic with:
```
python capri_python/data/find_symbol.py search <keyword>
python capri_python/data/find_symbol.py needs      # the table below
python capri_python/data/find_symbol.py gdx <file>  # list symbols in YOUR gdx
```

---

## The extraction list (priority order)

### 1. Replace synthetic `feed_requirements.csv` — HIGH
- **Symbol:** `p_feedInpCoeff` — *"feed input coefficients (fresh matter) by activity"*
  (or `v_feedInpCoeff` — *"feeding per head and year in kg"*)
- **Where:** your **results** database (capreg/feed build output)
- **Export:** `gdxdump <results>.gdx symb=p_feedInpCoeff format=csv > feed_req.csv`

### 2. Replace synthetic `nutrient_coefs.csv` — HIGH
- **Symbol:** `p_FertPerHa` — *"Fertiliser use per ha for CAPRI regions"*
  (or `v_minfert` — *"N input from mineral fertilizers [kg/ha]"*)
- **Where:** your **results** database (fertiliser/envind output)
- **Export:** `gdxdump <results>.gdx symb=p_FertPerHa format=csv > fert_perha.csv`

### 3. Newer base-year quantities (areas, yields, herds) — for re-base
- **Symbol:** `p_nutsLevl` (*"given hectares at NUTS-2 level"*) or `p_regioData`
- **Where:** `output/results/capreg/…regio…gdx`
- **Export:** `gdxdump <capreg>.gdx symb=p_regioData format=csv > regio.csv`

### 4. Newer base-year prices/balances — for re-base
- **Symbol:** market SUA in `fao_agg` (same file type as the 2017 one already used)
- **Where:** `output/results/global/fao_agg_<BAS>_<regagg>.gdx`
- **Export:** as done for `fao_agg_17` (the four CSV parts + elasticities xlsx)

### 5. Real biofuel coefficients (upgrade the biofuel module) — MEDIUM
- **Symbol:** `p_bioDat` — *"consolidated biofuel data from AGLINK and FO LICHT"*
  (or `p_bioDemPar` — biofuel demand function parameters)
- **Where:** **also inside `fao_agg`** (`%results_in%/global/fao_agg_%BAS%…gdx`) and
  `baseline/trace_dataPrep.gdx`. So a newer `fao_agg` export delivers this too.
- **Export:** `gdxdump fao_agg_<BAS>.gdx symb=p_bioDat format=csv > biodat.csv`

---

## Why this is now easy (it wasn't before)

The hard part was never access — it was that `nutrient_cont_usda` *sounds* like fertiliser
data but is USDA food nutrition, and `feed_agri` *sounds* like feed requirements but is
feed use. The symbol dictionary removes the guessing: it gives CAPRI's own one-line
description for every symbol, so you match on **meaning**, not on a filename that can
mislead. The two synthetic files map cleanly to `p_feedInpCoeff` and `p_FertPerHa`.

## What to do
Export the five symbols above from your STAR 2.8/3.0 **results** database (GAMS
`gdxdump`, or the CAPRI GUI's export), upload the CSVs, and they get wired in — the
validator then confirms vintage consistency before any run. Start with #1 and #2:
those remove the last two synthetic datasets in the model.

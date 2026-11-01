# CAPRI-mod: data acquisition reference

Status: revised 20 October 2026 against the code. How to obtain CAPRI's code, data and results for a rebuild or a
new base year. The access routes (section 2) and the file list (section 3) were recorded in October 2026 from CAPRI's
source tree and documentation and have not been re-checked against capri-model.org since; release names change. The
shipped data do not need any of this: they are in `capri_data/` as CSV and JSON (README section 4 (The data layer)).

## 1. What a rebuild needs

| Need | Why |
|---|---|
| CAPRI's results database of a release (regional results `res_<BAS><MS>`, `fao_agg`, estimation and baseline results) | the builders (`tools/build_*.py`) read dumps of these; a consistent newer base needs CAPRI's own estimation for that year |
| CAPRI's code (`gams/`) | several builders read parameters, sets and literals from the GAMS files (e.g. `arm/market1.gms`, `envind/*.gms`) |
| CAPRI's raw data (`dat/`) | mitigation and MITERRA tables, Nitrates Directive data |

There is no data web service for CAPRI. Its GAMS code contains no data API; the URLs in it are documentation and
source links (wiki pages, a JRC SVN repository, R and GitHub sources). CAPRI is distributed as files: SVN checkouts
and zip downloads.

## 2. Access routes

- **Website downloads**: capri-model.org ("get CAPRI" / getting started) lists releases with a "Code" and a
  "Database" zip each.
- **SVN**: CAPRI installations are managed with SVN (host `svn1.agp.uni-bonn.de`, one path per release tag); developer
  releases need a CAPRI SVN account, requested through the CAPRI network. A checkout gives `dat/`, `gams/` and `GUI/`.

  ```shell
  svn checkout https://svn1.agp.uni-bonn.de/svn/<RELEASE_TAG> capri_src
  ```

- **Registration and network**: full COCO database access follows the procedure on the CAPRI website and may involve
  a specific procedure or a fee; CAPRI training courses are another access path.

## 3. Files by topic (in a CAPRI installation)

Paths relative to the CAPRI system folder. GDX files are exported to CSV with `tools/build/gdx_dump_symbol.py` or GAMS
`gdxdump` (symbols: `DATA_LOCATION_MAP.md`, `SYMBOL_EXTRACTION_GUIDE.md`).

| Data | CAPRI file |
|---|---|
| regional results per member state (DATA2) | `results/capreg/res_<BAS><MS>.gdx` |
| regional database (other base years) | `dat/capreg/p_regiodata2015.gdx`, `p_regiodata2009.gdx`, `update_2019_regiodata.gdx` (`p_regioData`) |
| regional time series | `results/capreg/res_time_series.gdx` |
| market balances and prices | `results/global/fao_agg_<BAS>_<agg>.gdx`; `results/fao/fao_dataMarket.gdx` |
| global raw market data | `results/global/data_market_raw.gdx` |
| AGLINK baseline (incl. biofuels) | `dat/baseline/aglink<year>_oriEUdata.gdx` |
| GHG and energy indicators | `results/envind/GASES.gdx`, `results/enerind/ENER_new.gdx` |
| mitigation options | `dat/scen/ghgtech/` (e.g. `miti_data_jul15`), `dat/miterra/`, `dat/envind/` |

Two files once proposed here for the feed requirements and the fertiliser rates are the wrong data:
`dat/coco/feed_agri.gdx` holds feed use, and `dat/arm/nutrient_cont_usda.gdx` (`p_nutrientCont`) holds food nutrient
contents. The feed per head is CAPRI's DATA2 totals (livestock_feed_coef.csv; `feed_requirements.csv`, without
builder, removed: KNOWN_ISSUES K99); the fertiliser coefficients are CAPRI's DATA2 NITF, PHOF, POTF on the model's crops
(`nutrient_coefs_regional.csv`; the national `nutrient_coefs.csv`, without builder, removed: K100).

## 4. Public sources (not CAPRI)

| Source | What | Use here |
|---|---|---|
| Eurostat (REST/JSON API) | crop and animal production (`apro_cpshr`, `agr_r_animal`), gross nutrient balance | checks (`sources/eurostat/aei_pr_gnb_nitrogen.csv`; Eurostat cattle numbers for region splits) |
| FAOSTAT | producer prices, commodity balances, bilateral trade | not a model input (2021 extracts kept in `sources/fao_2021/`, not read by the model) |
| Scientific Data (2026), nature.com/articles/s41597-026-06919-8 | EU disaggregated CAPRI data (crops, livestock, N; 2000-2018) | not used |

Public data must be reconciled with a CAPRI base (units, codes, vintages) before use; mixing recent public values into
the 2017 base breaks its consistency (`DATA_SOURCING_GUIDE.md`, section 3).

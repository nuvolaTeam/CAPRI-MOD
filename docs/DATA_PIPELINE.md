# Data pipeline: download layer (user guide and provider reference)

This is step 2 of the CAPTRD-MOD work plan (docs/design/CAPTRD_MOD.md, sections 7 and 10). It covers the download
layer: provider adapters, the store, the manifest and the dataset catalogue.

**State on 23 October 2026.**
- Done and tested:
  - the Eurostat and FAOSTAT adapters;
  - the store (raw files and Delta tables);
  - the manifest;
  - the command line.
- The catalogue has its first content: the inputs of CAPRI's COCO, 108 datasets
  (`capri_data/pipeline/catalogue/datasets.toml`, with the mapping notes in `COCO_INPUTS.md` next to it).
- Not yet done:
  - the OECD and DG AGRI adapters;
  - the harmonisation, COCO and CAPREG stages.

The model never imports the pipeline: the pipeline writes files and the model reads files.

## Install

- The download layer needs `requests`, `pandas`, `deltalake` and `pyarrow`, all installed in the workspace.
- `sdmx1` is not needed: Eurostat's SDMX-CSV is plain CSV.

## Use

```
python -m capri_mod.pipeline fetch --provider eurostat --dataset apro_cpsh1 --filter crops=C1110 --filter geo=AT,BE --start 2015
python -m capri_mod.pipeline fetch --provider eurostat --dataset apro_cpsh1      # the whole dataset
python -m capri_mod.pipeline fetch --all                                          # every "available" catalogue row
python -m capri_mod.pipeline list                                                 # the catalogue
python -m capri_mod.pipeline manifest --verify                                    # downloads, checksums re-checked
python -m capri_mod.pipeline export --provider eurostat --dataset apro_cpsh1 --out apro_cpsh1.csv
```

From Python:

```
from capri_mod.pipeline.fetch import fetch
fetch("eurostat", "apro_cpsh1", {"crops": "C1110", "geo": ["AT", "BE"]}, start=2015)
```

## The store

The location is taken from the first of these that is set:
1. the environment variable `CAPRI_PIPELINE_STORE`;
2. the setting `pipeline.store_dir`;
3. `capri_data/pipeline/store`.

The store is not part of the zip packages: the manifest records enough to download the same data again.

| Path | Content |
|---|---|
| `raw/<provider>/<dataset>/<download_id>.<ext>` | the provider's answer as received, never edited |
| `manifest.csv` | one row per download: download_id, provider, dataset, url, query, downloaded_utc, provider_updated, sha256, bytes, rows, licence, raw_path, status |
| `delta/raw/<provider>/<dataset>/` | Delta table of the parsed downloads. Each row carries its download_id, and each write is a table version. `store.latest()` returns the newest download. |

**Missing values and true zeros stay apart.** A confidential or missing cell is kept as NaN with the provider's
flag (Eurostat `c`, `n`, ...), never as 0. A reported 0 stays 0. CAPRI itself treats both as zero; the CAPTRD port
reproduces that through its parity switch.

## The catalogue

`capri_data/pipeline/catalogue/datasets.toml` is configuration, not data. Like the settings layer it is TOML, with
comments and nested filters. It has one `[[dataset]]` table per dataset:

```
[[dataset]]
provider = "eurostat"
dataset = "apro_cpnh1"
filters = { geo = ["AT", "BE"] }     # optional; Eurostat: SDMX dimension ids, FAOSTAT: the CSV's column names
start = 2000                          # optional
status = "available"                  # available | discontinued | replaced_partially | unknown
capri_items = "crop LEVL, GROF, DRMA"
coco_source = "eurostat_raw/agriculture_mapping.gms:1377-1570"
```

- Adding a dataset means adding a table.
- `fetch --all` downloads the rows with status `available`.
- An unknown provider, an unknown key or a malformed filter stops the run, with the entry named.
- Rows of a provider without an adapter yet (faostat, oecd, dgagri) are listed by `fetch --all` as not downloaded.

**Content (23 October 2026): the inputs of CAPRI's COCO.** There are 108 rows: 92 Eurostat, 13 FAOSTAT, 2 DG AGRI,
1 OECD. By status: 81 available, 20 discontinued, 3 partly replaced, 4 unknown.
- Each row cites the CAPRI file and line of its mapping. The active Eurostat mapping is
  `eurostat_raw/agriculture_mapping.gms` (and its siblings), not the older `coco/eurostat_*` copies.
- Every Eurostat code was checked against the live catalogue and API on 23 October 2026. Dimensions come from each
  dataset's structure definition.
- **What the download cannot replace.** For the discontinued tables CAPRI reads a stored copy of an earlier Eurostat
  download: `dat/eurostat_raw/*.csv`, `dat/coco/*` (including `zpa1_march2010.gdx`) and `dat/fao/*`. That copy is
  not in the CAPRI code we hold; it has to come from the CAPRI installation. Discontinued tables include:
  - all market balances (`apro_cpb_*`, `apro_mt_bal`, `apro_mk_bal`, `apro_ec_bal`);
  - the regional `agr_r_*`;
  - `apro_cpp_crop` and `apro_cpp_luse`.
- **Format changes found:**
  - crop measure codes (AR → AR_THS_HA, PR → HPRD_THS_T, MA → MAR_THS_HA, HU → HUMD_PC);
  - the December month code M12 → M11_M12;
  - meat items, inferred and to be checked on data: SL/EL/IL → SLAUGHT/EXP/IMP;
  - the EAA dimension rename (01000 → AM010000, pattern inferred), and the EAA base year 2005 no longer published;
  - HICP tables closed in 2025 (successors prc_hicp_ainr, prc_hicp_iw);
  - absolute output prices end in 2024.

## Providers

### Eurostat (adapter `capri_mod/pipeline/ingest/eurostat.py`)

- **Base URL:** `https://ec.europa.eu/eurostat/api/dissemination` (setting `pipeline.eurostat_api`).
- **Data query:** `{api}/sdmx/2.1/data/{dataset}[/{key}]?format=SDMX-CSV&compressed=true[&startPeriod=Y&endPeriod=Y]`.
- **Key:** one position per dimension in the dataset's order, separated by `.`, with `+` between several codes and
  an empty position for all codes. The order comes from `{api}/sdmx/2.1/datastructure/ESTAT/{dataset}`; the
  adapter builds the key from named filters.
- **Working example** (23 October 2026):
  `.../sdmx/2.1/data/apro_cpsh1/A.C1110..AT+BE?format=SDMX-CSV&startPeriod=2020&endPeriod=2021` returns soft wheat
  areas and production for AT and BE.
- **Answer:** gzip'd CSV with the columns `DATAFLOW, LAST UPDATE, <dimensions>, TIME_PERIOD, OBS_VALUE, OBS_FLAG,
  CONF_STATUS`.
  - A whole dataset comes back in one answer (apro_cpsh1: 2.0 MB gzip'd, 388,674 rows, about 7 s).
  - A malformed key is answered with an XML fault naming the invalid dimension value. The adapter stops on it.
- **Large extractions** are answered asynchronously: an XML message with a key, then `{api}/1.0/async/status/{key}`
  and `{api}/1.0/async/data/{key}`. This follows Eurostat's documentation and has not yet been exercised on a live
  request.
- **Licence:** Commission Decision 2011/833/EU (reuse with acknowledgement), except third-party data.
- **Quirks found:**
  - crop measure codes were renamed in May 2026 (AR → AR_THS_HA);
  - absolute output prices stop at 2024 (the SAIO regulation applies from 2025);
  - regional tables switch to NUTS 2024 codes from 2023;
  - several tables COCO reads were discontinued (CAPTRD_MOD.md section 5).

### FAOSTAT (adapter `capri_mod/pipeline/ingest/faostat.py`)

- **Index:** `https://bulks-faostat.fao.org/production/datasets_E.json` gives every dataset's code, update date and
  zip location. The query API needs registration and is not used.
- **File:** one zip per dataset holding `<name>_E_All_Data_(Normalized).csv`. Its columns are Area Code, Area Code
  (M49), Area, Item Code, Item, Element Code, Element, Year Code, Year, Unit, Value, Flag, Note; the trade matrix has
  reporter and partner codes instead. The file is Latin-1. The M49 codes carry a leading apostrophe, kept as
  received.
- **No server-side filter.** Filters on the CSV's own column names (e.g. `--filter "Area Code=79,106"`) and periods
  are applied while the file is read in chunks of 500,000 rows. Each chunk is written as its own table version, so
  the trade matrix (410 MB zipped, 52 million rows) never sits in memory as a table.
- **Working example** (23 October 2026): `fetch --provider faostat --dataset RL --filter "Area Code=79,106" --start
  2010` gives 1,273 rows of land use for Germany and Italy in 4 s.
- **Licence:** CC BY 4.0.
- **COCO's domains:** QCL, CB, CBH, FBS, FBSH, TM, RL, RP, RFN, PP. CAPRI uses CB + FBS for the balances, not SCL.

### OECD, DG AGRI

Not yet implemented. Their formats are recorded in CAPTRD_MOD.md section 5:
- OECD: SDMX CSV with all six key positions;
- DG AGRI: agridata REST, prices as strings with mixed decimal separators.

## Tests

`capri_mod/pipeline/tests/test_pipeline_download.py`:
- **Offline**, on a stored Eurostat answer: parsing, flags and missing values, key building, store versions and
  latest, manifest checksums, catalogue validation.
- **Live**, run with `CAPRI_ONLINE_TESTS=1 python -m pytest -m online capri_mod/pipeline/tests`: one small Eurostat
  query, to catch renamed codes or moved endpoints.

# capri_data/sources — CAPRI's material for the builders (not read by the model)

The builders (`tools/build`) read this folder; the model does not: its input layers (`capri_mod/data/inputs.py`,
`capri_mod/market/inputs.py`) refuse a `sources/...` location since 3 November 2026. A number the model needs from
here is written by a builder as a model input under `capri_data/<base year>/`, `trajectories/` or `shared/`.

Layout by role (since 6 November 2026; docs/design/DATA_LAYOUT.md, file by file in DATA_LAYOUT_files.csv). Every table
here is Parquet since 8 November 2026 (the data layout's step (c)): each is the table its former CSV held, values to the
last bit, and every builder reads and writes them through `tools/lib/_sources_io.py` (`read_source`, `write_source`);
the model's inputs outside this folder stay CSV. To look at one: `python tools/check/show_table.py <file>`, or
`pandas.read_parquet`.

- **`raw/`**: CAPRI's and others' values unchanged. The path mirrors where the file comes from.
  - `raw/capri/dat/<CAPRI's own dat subfolder>`, `raw/capri/dat_local/...`, `raw/capri/gams/<subfolder>`: CAPRI's
    data and GAMS files converted one to one (`tools/build/convert_sources.py`,
    `extract_capri_dat.py`, `extract_capri_dat_local.py`). E.g. `raw/capri/dat/scen/ghgtech` holds the files of
    CAPRI's `dat/scen/ghgTech` (AD base data, GAINS AD, the fertiliser-technology literature review, miti_data_jul15).
  - `raw/capri/results/<CAPRI file>`: the builders' kept extracts of CAPRI's large result files (the 2030 market dump
    markmarket_greendeal_1730et_base_1717 is 390 MB): the records a builder uses, rows filtered, values unchanged.
    When the CAPRI file is present (`capri_sources/`, outside git: `tools/lib/paths.py`) the builder extracts it again;
    when it is absent the builder reads the kept extract, so the data rebuild without CAPRI's exports and a change in
    CAPRI's numbers shows as a diff of a small file. E.g. `raw/capri/results/markmarket_greendeal_1730et_base_1717/
    bilateral_dataout_2030.parquet` (`tools/build/build_bilateral_market.py`).
  - `raw/capri/capreg`, `raw/capri/capmod`, `raw/capri/capri_baseline`: CAPRI material whose conversion builder is still
    to be written (DATA_LAYOUT.md section 3).
  - `raw/eurostat`, `raw/nuts`: by publisher.
  - `raw/unsourced`: one table with no source (a proxy to resolve, PROXY_AUDIT).
- **`intermediate/<module>/`**: tables the builders compute from the raw files and read again (the PMP recipe and
  its terms, the CAPREG extracts, the P balances, the digestibility table, the cost savings); also some references read
  by the checks and tests.

Each file is declared in `capri_data/schema` (`30_sources.sql`) and checked with the other data
(`capri_mod/data/validate_data.py`); its builder and sources are in `capri_data/schema/01_provenance.sql`.

`fao_2021/` holds only the README recording the FAOSTAT 2021 files removed as orphans (KNOWN_ISSUES K102).

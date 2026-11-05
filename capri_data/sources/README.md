# capri_data/sources — CAPRI's material for the builders (not read by the model)

The builders (`tools/build`) read this folder; the model does not: its input layers (`capri_mod/data/inputs.py`,
`capri_mod/market/inputs.py`) refuse a `sources/...` location since 3 November 2026. A number the model needs from
here is written by a builder as a model input under `capri_data/<base year>/`, `trajectories/` or `shared/`.

Three kinds of file:

1. **Extracts of CAPRI's large files, written by builders.** A builder that reads a large CAPRI export (a market
   dump of 390 MB, a results listing) keeps the records it uses here, compressed. When the export is present
   (`capri_sources/`, outside git: `tools/lib/paths.py`) the builder extracts it again and writes the extract; when it
   is absent the builder reads the committed extract. So the data can be rebuilt without CAPRI's raw exports for
   these builders, and a change in CAPRI's numbers shows as a diff of a small file. Example: `market/
   bilateral_dataout_<year>.csv.xz` (`tools/build/build_bilateral_market.py`).
2. **CAPRI material without a builder**, committed as delivered and read by builders (the anaerobic digestion base
   data under `capri_dat/ghgtech`, the sugar quotas under `capri_dat/sugar`, literature tables under `ghgtech`,
   Eurostat's UAA under `eurostat`).
3. **Reference data for the checks and tests** (CAPRI's 2030 welfare and P balance, capmod's 2017 world reference,
   Eurostat's gross N balance), read by `tools/check` and `capri_mod/tests`, not by builders.

Each file is declared in `capri_data/schema` (`30_sources.sql`) and checked with the other data
(`capri_mod/data/validate_data.py`); its builder and sources are in `capri_data/schema/01_provenance.sql`.

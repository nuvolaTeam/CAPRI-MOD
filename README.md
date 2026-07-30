# CAPRI-Python

A Python implementation of the CAPRI (Common Agricultural Policy Regionalised
Impact) model: a regional PMP supply module over 248 NUTS-2 regions, an
Armington market module, CAP policy instruments and environmental indicators.

This is an independent reimplementation calibrated against data extracted from
CAPRI star-3.0. It is not a release of the CAPRI modelling system.

## Status

| Check | |
|---|---|
| Data validator | 11 pass, 1 warn, 0 fail |
| Base-year market fidelity | 12/12 commodities within 15% |
| Supply convergence (30-region sample) | 30/30 |
| Test suite | 15 passing |

Reproduce with `python tools/run_tests.py` (or `pytest capri_python/tests/`).

## Data provenance

The model's structural inputs are largely real CAPRI data; some behavioural
parameters are not. This is tracked per column, not per file, in
`capri_data/DATA_SOURCING_REGISTRY.json`, because a file-level label previously
concealed 16 synthetic columns inside a file marked `REAL_CAPRI`.

Area-weighted share resting on real CAPRI data:

| Input | Real | Note |
|---|---|---|
| Base areas | 98.2% | four constant placeholders remain |
| CAP payments, land, variable costs | ~100% | |
| Animal numbers | ~99% | |
| Yields | 45.5% | capreg DATA2, 192 of 248 regions |
| Supply elasticities | 40.0% | 132 regions, 14 activities |
| Livestock yields | 0% | see *Known gaps* |

Yield accuracy against an independent COCO2 2017 benchmark: median error 7.3%
across 285 country x activity pairs, 85% within 20%. Before the capreg merge
these were 16.0% and 61%.

Two audit tools keep this honest:

- `tools/detect_synthetic_columns.py` — flags generated columns by their
  statistical signature (constant x lognormal noise, or a flat constant) and
  cross-checks the result against the registry.
- `tools/validate_capreg_yields.py` — benchmarks any candidate yield source
  against an independent CAPRI extraction before it is merged.

## Known gaps

**Livestock yields are entirely synthetic.** Real capreg values for `DCOW`,
`BULL` and `PIGF` are parsed and available in
`capri_data/sources/capreg/capreg_yields.csv`, but are deliberately not merged:
the COCO2 benchmark carries no livestock, so they have no independent
validation. Eight further activities exist in capreg under different names
(`BCOW`/`SCOW`, `LAYS`/`HENS`, `BROI`/`POUF`, `PIGS`/`SOWS`, and the many-to-one
`CALV`, `HFRS`, `SHGP`) and need a documented mapping.

**`GRAS` is unresolved.** capreg reports 410.9 for Germany where COCO2 national
reports 17770 for the same year. The definitions differ between modules; no
conversion is applied until that is documented.

**`OANI` is closed as not obtainable.** In CAPRI it is a share-index
pseudo-activity, not a herd — `LEVL` is exactly 1.0 nationally and the regional
levels sum to 1.0 across NUTS-1. No per-head yield exists to import.

**56 regions** are not covered by capreg, scattered across 15 countries with no
common pattern, suggesting CAPRI models them at coarser resolution.

**Elasticity coverage is asymmetric.** Real estimates exist only for arable
crops, so a price shock concentrates 86.8% of reallocation there. Measured by
`tools/scenario_elasticity_check.py`; a property of the data coverage rather
than of the wiring, but it argues against using the model for policy scenarios
until coverage extends to permanent crops and livestock.

## Layout

```
capri_python/          model code
  supply/              regional PMP, CAPRI dampening and share terms
  market/              Armington market module (EU27 bloc)
  policy/ feed/ environmental/ biofuel/ scenarios/
  data/                loaders, definitions, validator
  tests/
capri_data/            calibration data
  2017/                base-year inputs
  sources/             raw extractions (COCO, capreg, NUTS tables)
  validation/          benchmark reports
  DATA_SOURCING_REGISTRY.json
tools/                 extraction, ingest, merge and audit scripts
```

## Extraction workflow

CAPRI data reaches the model through `gdxdump` listings, not Excel exports — an
earlier Excel path introduced Cyrillic homoglyph corruption, dropped regional
detail, and mixed vintages across cells.

```
tools/dump_capreg_explicit.gms      run in GAMS Studio, dumps res_17*.gdx
tools/dump_reqrel_explicit.gms      animal requirement relations
tools/ingest_capreg_data2.py        parse dumps into model-ready tables
tools/validate_capreg_yields.py     benchmark before merging
tools/merge_capreg_yields.py        country-gated merge with margin guard
```

`tools/build_nuts_crosswalk.py` resolves the model's NUTS-2 codes to CAPRI's
8-character region codes through the full Eurostat correspondence chain
(1995 through 2027), covering 227 of 248 regions.

## Documentation

- `DATA_FIXES.md` — extraction defects found and repaired
- `PMP_ELASTICITY_WIRING.md` — regional elasticity wiring and CAPRI's dampening rule

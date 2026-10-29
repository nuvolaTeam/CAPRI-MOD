# CAPTRD-MOD — data pipeline and baseline projection layer (living design document)

**Status (22 October 2026):**
- Outline agreed.
- State of the art reviewed.
- Data organisation partly agreed.
- Method decisions taken (section 8): CAPTRD defects fixed; recursive dynamics at the largest possible scope; source order for balances and ML candidates agreed.
- Detailed design not yet written; work starts after the current capri-mod package.

**Maintenance rule (project lead, 22 October 2026).** This document always shows the current state. Content that
becomes obsolete or no longer valid is deleted, not kept alongside. The history of decisions lives only in the
decision log (section 11).

**Companions:**
- `docs/design/CAPTRD_MAP.md` (project doc `claude/captrd_map.md`): CAPRI's CAPTRD code mapped with file:line
  citations.
- `docs/design/sota/`: the four state-of-the-art reports.

---

## 0. Pipeline overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 1. Data ingestion                                                                    │
│    Eurostat · DG AGRI · FAOSTAT · OECD-FAO · CAPRI reference data                    │
│    API clients · Raw-file cache (Delta Lake, CSV export) · Metadata · Provenance     │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 2. COCO — Consistent historical database                                             │
│    Missing values · Agricultural balances · Area/yield/production identities ·       │
│    Feed balances                                                                     │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 3. CAPREG — Regionalisation                                                          │
│    National → NUTS-2 · Regional activities · Land use · Livestock ·                  │
│    Technical coefficients                                                            │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 4. CAPTRD-MOD — Baseline projection                                                  │
│    Statistical trends + ML · Forecast uncertainty · Outlook reconciliation ·         │
│    Regional trajectories                                                             │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 5. Baseline calibration                                                              │
│    PMP parameters · Supply behaviour · Market balances · Reference-year consistency  │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 6. CAPRI-MOD economic equilibrium                                                    │
│    Regional supply optimisation ↔ Market module ↔ Price feedback                     │
│    Nonlinear solver · Convergence · Economic and physical constraints                │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 7. Scenario execution — select a mode                                                │
│    ┌───────────────────────────────────┐   ┌───────────────────────────────────┐     │
│    │ Comparative-static                │   │ Recursive-dynamic                 │     │
│    │ Baseline vs F2F in 2030           │   │ Annual baseline vs F2F paths      │     │
│    └───────────────────────────────────┘   └───────────────────────────────────┘     │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ 8. Results, validation and reporting                                                 │
│    Production · Prices · Farm income · Land use · Livestock · Emissions ·            │
│    Scenario differences                                                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Stages 1–4 are the five layers' first four (section 1). Stages 5–6 are the existing capri-mod: its baseline
calibration and its supply–market equilibrium. Stage 7 is layer 5. Stage 8 is the existing reporting and
validation.

The ML part of stage 4 and the recursive-dynamic mode of stage 7 go beyond CAPRI. ML is admitted only through the
back-casting rule (section 8.2); the recursive-dynamic scope is in section 8.4. Comparative static stays the default
(section 1a).

## 1. Architecture (the five layers)

1. **Automatic data download** from Eurostat, DG AGRI, FAOSTAT and OECD-FAO, as a documented user mechanism
   (section 7). Where data are unavailable or discontinued, CAPRI's own stored data come from the project lead's
   CAPRI installation (section 5).
2. **A consistent national database**, like CAPRI's COCO.
3. **Regional breakdown**, like CAPREG.
4. **A baseline projection of our own (CAPTRD-MOD).**
   - The core follows CAPTRD (section 3).
   - ML or statistical alternatives for step 1, beyond CAPRI, admitted only by back-casting (section 8.2).
5. **Scenario modes.**
   - Comparative static, the default, as CAPRI.
   - Recursive dynamic, beyond CAPRI, with the largest possible set of dynamic links (section 8.4). CAPRI has no such mode. The only trace in its GAMS tree is
     `$SETGLOBAL RECDYN OFF` (capreg/set_global_variables.gms:108), marked obsolete.

## 1a. Compatibility with the current model (requirement, 22 October 2026)

The current model state and all the 2030 work stay valid and remain the default. That 2030 work is:
- the 2017 base year;
- CAPRI's 2030 reference trajectory and its prices, premiums, rations and fodder;
- CAPRI's exported 2030 PMP terms and capri-mod's own recipe terms;
- the Farm-to-Fork runs.

The pipeline adds to it; it doesn't replace or change it:
- **New outputs sit beside the current ones.** A new base year goes in its own folder (`capri_data/<year>/`), and
  a CAPTRD-MOD projection is a new trajectory file in the existing trajectory format (e.g.
  `trajectories/captrdmod_<year>.json`). They are selected by an option; the defaults stay `capri_data/2017/` and
  `capri_ref_2030.json`.
- **Changes to existing code are behaviour-neutral.** This includes the prerequisite fix of the hard-wired 2017
  paths. Accepted only if the full test suite passes unchanged and the reference runs reproduce their results with
  the new layer off: Farm-to-Fork 2030 with CAPRI's terms and with the recipe terms, compared through
  `tools/check/compare_runs.py`.
- **The existing projection layer keeps working as is** (section 2). CAPTRD-MOD feeds it through the same
  trajectory schema, so a projection made by CAPTRD-MOD and one taken from CAPRI can be run and compared the same
  way.

## 2. What the projection layer does today (capri_mod/projection)

It is not CAPTRD:
- It takes CAPRI's own 2030 results as a path given from outside. The default is CAPRI's 2030 reference
  (`capri_ref_2030.json`); CAPRI's own CAPTRD output (`captrd_2030.json`) is the alternative.
- It scales the 2017 data along that path, restores the accounting identities with a simplified least-squares step
  (`reconcile.py`), and solves each target year comparative-static.
- It estimates no trends of its own. Nothing is carried from year to year except perennial crop areas.

## 3. How CAPTRD-MOD works, following CAPTRD's code

1. **Trend for each series on its own** (estimate_trends.gms).
   - The curve is x = a + b·t^c, fitted by weighted least squares, with t = year index / 10 and observations
     weighted by t.
   - c is chosen on a 30-point grid from 0.02 to 1.2.
   - Short series get a straight line (3–4 observations) or a weighted mean (2 or fewer).
2. **Starting values (supports)** (define_stats_and_supports.gms).
   - Each series is pulled between its trend and its last-3-year average according to the trend's fit:
     B·(1−wR²) + trend·wR².
   - Crop yields use √wR² and the average of the 3 best yields in the last 8 years.
   - Expert, COCO and Aglink supports get variances from trust levels: (max(0.1,|S|)·0.05/3·10/trust)².
3. **Consistency solve** (model m_trendMS; estimate_ms.gms).
   - One country at a time. The documentation says countries are estimated jointly; the code is the authority.
   - It minimises weighted squared deviations from the supports, subject to about 40 rules: market balances,
     production = yield × level, land, feed and so on.
   - National expert supports enter here.
4. **Second solve of the same model**, adding the EU-level Outlook/Aglink targets (define_EU_supports.gms runs between
   the two solves).
   - The NUTS-2 breakdown happens inside this second solve.
   - The breakdown by farm type is a separate CAPRI program (captrdfrm.gms), left out at first.

**Parity test.** Give CAPTRD-MOD the inputs CAPRI used, and compare its result with `captrd_2030.json`, CAPRI's own
CAPTRD output. The exact list of files needed from the CAPRI installation comes with the detailed design (from
CAPTRD_MAP.md section 2). It includes:
- CAPRI's stored Eurostat download;
- its historical series;
- its Aglink targets;
- the settings file `fortrd.gms`, which is missing from the sources in hand;
- its CAPTRD results.

## 4. State of the art (review of 22 October 2026)

The full reports are in `docs/design/sota/`; every claim in them is tied to a source, and unverified points are
marked. Checked by hand on 22 October 2026:
- recursive dynamic in CAPRI;
- the discontinued Eurostat tables and the coverage of their replacements;
- the renamed Eurostat crop code;
- the DG AGRI API specification.

### 4.1 Baselines in other models (SOTA_BASELINES.md)
- **CAPRI.** No published change to CAPTRD's method after the 2022 documentation; 2024–2026 slides show the same
  steps and trust levels (DG AGRI default 5). It is realigned about once a year to the previous year's EU
  medium-term outlook. 2050 runs blend medium-run supports (Aglink) with long-run ones (GLOBIOM, IMPACT, FAO), the
  long-run weight growing with the horizon.
- **EU Agricultural Outlook 2025-35** (16 Dec 2025).
  - Made with Aglink-Cosimo's EU module, expert review and an October workshop.
  - Published only as a PDF and a dashboard.
  - The OECD-FAO Outlook CSV (SDMX DSD_AGR@DF_OUTLOOK_2026_2035) carries the EU aggregate from the previous
    December's DG AGRI outlook. It is the machine-readable source for the step-3 targets; the vintage is recorded.
- **Aglink-Cosimo** imposes expert views by editing equation residuals by hand ("R-factors"). It is not
  reproducible, so CAPTRD's explicit weighted supports are kept.
- **Aggregates.** CAPRI's step-3 targets are EU15 / EU12; current Aglink uses E14 / NMS13. The mapping from target
  regions to member states is a CSV table.
- **Forecast skill.** USDA and FAPRI baselines lose most predictive value after about 4–5 years (Bora, Katchova &
  Kuethe 2023).
- **No open-source equivalent of CAPTRD** exists apart from CAPRI's GAMS code.
  - Step 2 is close to "constrained forecast reconciliation" (Wickramasuriya et al. 2019; Girolimetto & Di Fonzo
    2024; tools R FoReco and Python hierarchicalforecast).
  - Those handle linear constraints only, not production = yield × level, so they serve as a test check on the
    linear parts.

### 4.2 ML and statistics for step 1 (SOTA_ML_STEP1.md)
- **No benchmark covers our horizon.** Public evidence on yearly series stops at 4–6 years ahead; nothing tests
  10–15. Only our own back-casting can show whether anything beats CAPRI's curve.
- **ML gains on yearly series are small,** and appear only when one model is trained across many series.
  Per-series deep learning has no supporting evidence at about 30 observations.
- **The European yield-ML successes (JRC MARS, CY-Bench) don't transfer:** they use in-season weather and satellite
  data, which don't exist 10 years ahead.
- **Foundation models** (Chronos-2, TimesFM-2.5): whether the test years leaked into their training data can't be
  audited, so exploratory only. Moirai is non-commercial (CC BY-NC 4.0), so excluded.
- **Candidates and protocol:** section 8.2.

### 4.3 Recursive dynamics (SOTA_RECURSIVE_DYNAMIC.md)
- **Who carries what between years.**
  - Aglink, AGMEMOD and FAPRI: recursive through lagged prices or returns, revenue averages and breeding herds.
  - GLOBIOM, IMPACT and MAGNET: recursive comparative statics, carrying land, capital and trade.
  - CAPRI, IFM-CAP and AROPAj: static.
  - No main model has perennial vintages; verified price expectations are backward-looking; yields are exogenous
    trends everywhere.
- **Dynamic PMP literature is thin:** Paris 2001; SILAS-Dyn; SWISSland (with a real ex-post validation); Day's
  recursive LP. The open problem is updating PMP terms over time (Heckelei, Britz & Zhang 2012).
- **CAPRI's own history.**
  - CAPRI-Dynaspat (2004–07) aimed at a recursive CAPRI; no maintained version exists.
  - EXPOST only sets the simulation year equal to the base year; it is not a backcast.
  - Existing lagged pieces: the land-transition path in the supply model, and the COCO cattle herd flow
    (t, t+1, t+2).

## 5. Data sources: state on 22 October 2026 (SOTA_DATA.md, with checks)

- **Reachable from the workspace** (tested with real downloads):
  - Eurostat JSON and SDMX;
  - FAOSTAT bulk files;
  - OECD SDMX (CSV);
  - DG AGRI agridata REST: OpenAPI specification at `https://api.tech.ec.europa.eu/agrifood/v3/api-docs`, 116
    paths, no authentication.

  FAOSTAT's query API is not usable: it needs registration and was not responding. The bulk files carry the same
  data.
- **Discontinued Eurostat tables that CAPRI's COCO reads** (coco/agri_prod_ori_eurostat.gms maps them).
  - Gone: the crop balances `apro_cpb_*` (cereals, oilseeds, fruit and vegetables, potatoes, rice, sugar, wine,
    pulses), the animal-product balances `apro_mt_bal` / `apro_mk_bal` / `apro_ec_bal`, and the regional
    `agr_r_*` tables.
  - Evidence: none is in Eurostat's dataset catalogue (12,271 entries), and the API answers "not found".
  - CAPRI works from a stored copy of an earlier Eurostat bulk download, kept in its own database. That copy is the
    source for those years.
- **Their replacements are partial.**
  - `apro_cbs_cer` and `apro_cbs_oil` cover cereals and oilseeds only, from 2017, under a voluntary ESS agreement.
  - Reporting: 13 signatories plus DE, EE, HR, PT on a voluntary basis. DE covers 2019–2023; the others 2017–2024.
  - Missing in every year: FR, ES, NL, BE, AT, CZ, DK, SE, CY, MT. Eurostat: "a European aggregate and EU crop
    balance can not be calculated".
  - Animal-product balances have no Eurostat successor.
  - The unit values `aact_uv*` are frozen at 2018.
- **Format changes to handle.**
  - Crop measure codes renamed in May 2026 (e.g. AR → AR_THS_HA; checked).
  - Confidential cells come with an empty value and the flag C; breaks are flagged b.
  - Absolute output prices stop at 2024, because the new SAIO regulation applies from 2025. 2025 prices need a
    fallback.
  - DG AGRI prices arrive as strings with mixed decimal separators.
  - OECD queries need all six key positions.
- **NUTS.** Regional tables switch to NUTS 2024 codes from 2023 within the same table, differently per table; NUTS
  2027 is adopted. Recode per dataset and year.
- **Licences.**
  - Eurostat: Commission Decision 2011/833/EU, with exceptions for third-party data.
  - FAO: CC BY 4.0.
  - OECD: to be confirmed.
  - Recorded per series.
- **Tools.**
  - sdmx1 or pysdmx; pandaSDMX is no longer maintained.
  - The Python faostat package fails without an API token.
  - No open project consolidates national and regional data as COCO/CAPREG do.
  - The CAPRI Scientific Data paper (Koeble et al. 2026) publishes 1 km rasters for 2000–2018, not the COCO/CAPREG
    tables.

## 6. Data organisation

**Agreed (22 October 2026):**
- Delta Lake for the internal stages raw → harmonised → coco → capreg → captrd. CSV for the final model inputs, the
  code mappings, and the expert and review tables. Every stage can export to CSV.
  - Test on a 2-million-row table: write 0.6 s vs 21.8 s for gzipped CSV; read 0.21 s vs 1.7 s; one item 0.04 s;
    22 MB vs 30 MB. Each write is a readable version.
  - Costs: the deltalake and pyarrow libraries (Apache-2.0), binary files, and a retention rule for old versions.
- True zeros and missing values are kept apart (status / flag). CAPRI treats zeros as missing; a parity switch
  reproduces that.
- Prerequisite for a new base year: the modules that read `capri_data/2017/` directly must be fixed, without
  changing any result (section 1a).

**Proposed, not separately confirmed:**
- **Stages under `capri_data/pipeline/`:**
  1. catalogue (`datasets.toml`, configuration; code mappings provider → CAPRI, including NUTS versions)
  2. raw (by provider / dataset / download date, with a manifest)
  3. harmonised
  4. coco
  5. capreg
  6. supports (Outlook editions; expert supports with trust levels)
  7. captrd/<run>

  The output is a new base-year folder `capri_data/<year>/`.
- **One table layout,** CAPRI's DATA(region, item, product, year) in long form:
  `region, product, item, year, value, unit, status, source_id, flag`.
- **CAPRI's own files** (stored Eurostat download, historical series, Aglink targets, fortrd.gms, CAPTRD results)
  go in `capri_reference/`. They are read-only and read only by the tests, never by the pipeline.
- **Raw downloads stay out of the zip package;** the manifests let anyone re-download them.

## 7. Data download layer as a user mechanism (requirement, 22 October 2026)

The provider APIs are documented, and the download is a working mechanism for users. Proposal:

- **One entry point, two forms:**
  - a command line, e.g. `python -m capri_mod.pipeline fetch --provider eurostat --dataset apro_cpsh1`, or
    `fetch --all`;
  - the same functions callable from Python.
- **Catalogue-driven.** `catalogue/datasets.toml` (configuration, TOML like the settings) lists provider, dataset code, query, licence and the CAPRI items fed.
  Adding a dataset means adding a row.
- **One adapter per provider,** behind the same interface:
  - Eurostat: SDMX-CSV with flags;
  - FAOSTAT: bulk zips;
  - OECD: SDMX CSV;
  - DG AGRI: REST.

  Each handles paging, retries, rate limits and the provider's "last updated" date. Credentials, if ever needed,
  come from environment variables.
- **Every download** writes the raw file, a manifest row (URL, query, time, provider update date, checksum, licence)
  and a Delta table version.
- **Unknown codes stop the run,** naming the code and the mapping file to update.
- **Documentation** (`docs/DATA_PIPELINE.md`):
  - per provider: base URL, query format with a working example, datasets used, limits, licence, known quirks with
    the date found;
  - a user guide: install, fetch, add a dataset, update a mapping, check a manifest, export to CSV.
- **Tests:**
  - offline, on small stored samples of each format, in the normal suite;
  - live, on request: one small series per provider, to catch renamed codes or moved endpoints.

## 8. Method decisions (22 October 2026)

The project lead decided:
- the CAPTRD defects are fixed;
- the recursive-dynamic mode takes the largest set of dynamic links that data and method allow;
- the source order for market balances and the ML candidates were left to the proposals in 8.1 and 8.2, which the
  project lead then approved.

### 8.1 Market balances: source order (agreed)

As in CAPRI's COCO, the sources are not applied as overrides. Each enters the consistent-database estimation as a
prior with its own weight, and the identities (production + imports = uses + exports + stock change; production =
yield × level) decide the rest. The order below is the order of trust.

1. **Eurostat production statistics,** the anchor with the highest weight: crop production `apro_cpsh1` / `apro_cpnh1`,
   meat, milk and eggs (`apro_mt_*`, `apro_mk_*`, `apro_ec_*`). These are official, complete and current.
2. **Eurostat crop balances `apro_cbs_cer` / `apro_cbs_oil`,** from 2017, where reported: cereals and oilseeds,
   17 member states. This is the official balance method, closest to the old tables.
3. **CAPRI's stored copy of the discontinued Eurostat balances,** for the years they cover, with the same weight as
   2. The overlap years with 1 and 2 are checked, and differences reported.
4. **Trade: FAOSTAT TCL** (built from national customs data) for imports and exports. Eurostat Comext is a later
   option if the product detail requires it.
5. **FAOSTAT supply-use tables (SCL, from 2010; FBS for food use)** for the remaining uses (feed, seed, processing,
   industrial use, losses, food) and for products and countries 2–3 don't cover. Medium weight.
   - Where 3 and FAOSTAT overlap, the systematic difference per country, product and item is measured.
   - If it is stable, FAOSTAT is bias-corrected for the later years. This step goes beyond CAPRI (COCO uses FAO data
     without such a correction) and is reported as such.
6. **Stock changes and items without data** are left to the identities, with weak priors: their own trend, and stock
   changes pulled toward zero over several years.

Every value keeps its source and status, so the share estimated by the identities rather than observed is
reportable per country, product and year.

**Checked against CAPRI's code (23 October 2026; capri_data/pipeline/catalogue/COCO_INPUTS.md).** Two points of the
order above differ from what CAPRI does. They are departures until the project lead decides:
- **Humidity basis of crop production.** CAPRI reads `apro_cpnh1`, national humidity (eurostat_raw/agriculture_mapping.gms
  l. 1377-1570), and does not use `apro_cpsh1`, EU standard humidity. CAPRI's choice is the default; `apro_cpsh1`
  stays as an alternative.
- **FAOSTAT balances.** CAPRI uses the commodity balances CB and the food balance sheets FBS (with CBH and FBSH before
  2013), not SCL (global/load_fao_data_new.gms, prepare_faostat_database.gms). Item 5 follows CAPRI's CB + FBS.
  Whether SCL adds anything can be tested later.

The stored copy of item 3 (`dat/eurostat_raw/*.csv`, `dat/coco/*`, `dat/fao/*`) is not in the CAPRI code we hold.
It has to come from the project lead's CAPRI installation.

### 8.2 ML candidates for step 1 (agreed; beyond CAPRI)

Each candidate gives a prior and a variance by horizon. All feed the unchanged step 2.

- **Tier A (always run):**
  - C0, CAPRI's curve a + b·t^c: the reference;
  - B1, random walk with drift, and B2, linear trend: the benchmarks;
  - S1, damped-trend exponential smoothing;
  - S2, Theta;
  - S4, the combination of C0, S1 and S2 (median).
- **Tier B (run after A works):**
  - S3, a local-linear-trend structural model;
  - H1, a hierarchical Bayesian version of CAPRI's own curve, pooling b and c across regions within a country and
    across countries per item;
  - G1, a pooled LightGBM on differenced, scaled series, one model per horizon band.
- **Tier C (exploratory, reported apart):** Chronos-2 and TimesFM-2.5 (Apache-2.0 weights). Admitted only if a
  leakage probe passes: compare back-cast origins before and after the model's training cut-off.
- **Validation protocol:**
  - expanding-window back-casts from 2003, at least 15 observations per origin, horizons 1–15;
  - metrics: MASE (primary), bias, 80/95% interval coverage, by horizon band 1–5, 6–10, 11–15;
  - a block bootstrap over origin years.
- **Acceptance rule,** per item group (yields, areas, herds, balance items). An alternative replaces C0 only if all
  hold:
  1. it beats C0 after step 2, with the whole 95% confidence interval of relative MASE below 1, at 6–10 and 11–15
     years ahead;
  2. its bias is no worse;
  3. 80% coverage is within ±10 points;
  4. the result survives dropping the earliest and the latest third of the origins.
- **Expected outcome, from the evidence (an expectation, not a result):** S4 (combining CAPRI's curve) is the most
  likely to pass. H1 should help the short series of the newer member states.
- **Related option (beyond CAPRI):** step-2 weights from back-cast error variances by horizon instead of in-sample
  fit. Tested with the same protocol.

### 8.3 CAPTRD defects: fixed (decided)

Each defect gets a fix, and a parity switch reproduces CAPRI's behaviour.
- **Why the switch:** only with CAPRI's behaviour can the parity test against `captrd_2030.json` measure our
  implementation rather than the fixes.
- **Reporting:** the effect of each fix is reported separately, against the parity run.

The defects (details in CAPTRD_MAP.md):
- the upper bound on artificial land, non-binding through a misplaced parenthesis (fix_est.gms:810);
- the error-variance floor comparing a level with a variance: fixed 24 October 2026 as (0.05 × |wAve|)², setting
  `captrd.variance_floor_squared` (section 12.4; docs/DEPARTURES_FROM_CAPRI.md);
- the base-year window labelled "5 years" spanning 7: on inspection (23 October 2026) not a defect where ExPost ends
  at BAS + 1, as in the reference run (BASYRS5 = 2014-2018, five years; section 12.4). Setting
  `captrd.basyrs5_halfwidth` = 3, CAPRI's;
- zeros treated as missing (fixed in the data layer, section 6, and in the estimator);
- series with 2-4 observations get Step1 = 0: the minimum over the trend grid counts the 29 zeroed grid points
  (estimate_trends.gms l. 158-171). Found while porting and confirmed in CAPRI's own output on 23 October 2026
  (section 12.4). Setting `captrd.short_series_grid_as_coded` (docs/DEPARTURES_FROM_CAPRI.md).

Further defects found while porting are handled the same way and added here.

**Solver:** IPOPT, as in the supply model. CAPTRD itself sets none (installation default; CONOPT option files exist).

### 8.4 Recursive dynamics, CAPSIM-DYN: the largest possible set (decided scope; beyond CAPRI)

The module is named **CAPSIM-DYN** (project lead, 23 October 2026). Code: `capri_mod/projection/capsim_dyn/`.


CAPRI's per-year equilibrium is kept. Each link carries a state from year t−1 into year t, has a switch, and is
judged by the backcast.

| # | Link | Data | Status |
|---|---|---|---|
| 1 | Annual driver paths from CAPTRD-MOD (yields, technology, demand, world prices, policy timeline) | CAPTRD-MOD annual output; outlooks are annual | In |
| 2 | Land use carried over, with CAPRI's land-transition probabilities | CAPRI transition matrices; LUCAS / CORINE for checks | In |
| 3 | Partial adjustment of crop and animal activity levels around t−1 (adjustment speed estimated from the regional series; short- and long-run elasticities reported) | CAPREG-like regional series | In |
| 4 | Cattle herd stock-flow: heifers and calves of t−1 limit cows and fattening in t | Eurostat December livestock surveys; CAPRI's young-animal coefficients | In |
| 5 | Breeding herds of pigs, sheep and goats (sows, ewes) lagged one year | Eurostat livestock surveys | In |
| 6 | Price expectations (moving-average or adaptive; naive excluded because of cobweb instability) | Estimated from historical prices and areas | In, as a switch. Default chosen by the backcast |
| 7 | Perennial crops: plantations bear after a non-bearing period; uprooting and planting limited per year; initial age structure from the orchard surveys | Eurostat `orch_*` age-class surveys (2002–2017, checked in the catalogue); vineyard surveys to be checked | In, "vintage-lite" (age classes, not individual vintages) |
| 8 | Soil carbon and histosol dynamics after land-use change (IPCC 20-year transitions) | IPCC default factors; CAPRI's land and histosol data | In, as accounting (no feedback to supply) |
| 9 | Diffusion of the mitigation technologies (adoption limited per year around t−1 shares) | No observed adoption series; limits as scenario settings | In, as a switch with stated assumptions |
| 10 | Capital and investment (stables, machinery) | No mapping of FADN capital to CAPRI activities; no precedent in regional PE models | Out, cannot be supported by data |
| 11 | Structural change (farm exit, size classes) | Needs the farm-type layer, which is left out at first | Out, for now |

First tests:
1. **No-shock run:** it reproduces the comparative-static baseline points.
2. **After a shock with frozen drivers:** the path converges to the comparative-static scenario result.
3. **Backcast** from about 2010 to 2020: RMSE and Theil's U against a no-change forecast, mainly over 1–5 years.

Risks:
- **Adjustment counted twice,** in the trends and in link 3. The adjustment speed is estimated consistently with
  the trend model.
- **Yearly recalibration hiding misspecification.** Shifters are reported and bounded.
- **Run time** grows with the number of years. Each year is warm-started from t−1.

### 8.5 Other options beyond CAPRI (not yet decided)

- Step-2 weights from the step-1 error correlations.
- A stochastic baseline (resampling historical years, as Aglink).
- An expert-review package in CSV.
- Publishing the reconciled database.
- LUCAS / EuroCrops and the JRC subnational crop statistics as extra priors.

## 9. Code organisation (agreed 22 October 2026)

**Today:**
- one package `capri_mod` (the model);
- 156 builder scripts in `tools/` that turn CAPRI extracts into the model's CSV inputs;
- the tests in `capri_mod/tests`;
- no version control: each delivery is a zip.

**Principle: one-way dependency.** The pipeline writes files; the model reads files. The model never imports the
pipeline. This is what keeps the current model and the 2030 work intact (section 1a): with the pipeline absent or
switched off, the model runs exactly as today.

**Layout.** New code goes in a subpackage `capri_mod/pipeline/`, plus the recursive mode (CAPSIM-DYN) in the existing
`capri_mod/projection/`:

```
capri_mod/
├── (existing model packages, unchanged: supply, market, policy, environmental, feed, fert, projection, …)
├── projection/
│   └── capsim_dyn/         CAPSIM-DYN, the recursive-dynamic mode (section 8.4): state carried t−1 → t, one module per link
└── pipeline/
    ├── __main__.py         command line: python -m capri_mod.pipeline fetch | build | project | backtest
    ├── config.py           paths (store location from an environment variable); settings from the settings layer
    │                       (capri_mod/settings: defaults.toml + user overrides, a [pipeline] section)
    ├── store.py            Delta Lake read/write, versions, CSV export
    ├── catalogue.py        datasets.toml and the code mappings; unknown codes stop the run
    ├── manifest.py         provenance of every download
    ├── ingest/             one adapter per provider: eurostat.py, faostat.py, oecd.py, agridata.py, capri_ref.py
    ├── harmonise/          codes, units, NUTS recoding
    ├── coco/               consistent national database (sources as weighted priors, identities)
    ├── capreg/             regional breakdown
    ├── captrd/             step1/ (CAPRI's curve + the ML candidates), supports.py, estimate.py (the NLP),
    │                       eu_supports.py, export.py (writes trajectories in the model's existing format)
    ├── backtest/           the back-casting protocol of section 8.2
    └── tests/              offline tests; live API tests marked "online"
```

**Dependencies stay optional,** as extras in `pyproject.toml`, so installing the model alone is unchanged:
- `pipeline`: deltalake, pyarrow, sdmx1, requests;
- `ml`: statsforecast, lightgbm, pymc;
- `foundation`: chronos-forecasting, timesfm (heavy; exploratory).

**Data:** `capri_data/pipeline/` as in section 6; the large raw store can be relocated through an environment
variable.

**Existing `tools/` builders** stay as they are. A builder is retired only when the pipeline reproduces its output
file. Until then both exist, and the model keeps reading the builder's file.

**Tests:**
- the existing suite stays where it is and must pass unchanged;
- pipeline tests carry markers: `online` for live APIs, run on request; `slow` as today.

**Conventions, as in the current code:**
- every module cites the CAPRI GAMS file and line it ports;
- run settings (switches, tolerances, algorithm choices) live in the settings layer (`capri_mod/settings/defaults.toml`
  with user override files, agreed 23 October 2026); sourced parameters in the parameter CSV; CAPRI structure in
  mapping CSVs; never in code;
- every departure from CAPRI is flagged in the code and in this document.

**Version control.** Deliveries stay as zip packages, as before (decided 22 October 2026). A git home on GitHub
(`nuvolaTeam/capri-mod`) was set up: it is reachable from the workspace, but pushing is not authorised, and the
project lead chose to continue with zips. Each layer is still developed so that the existing tests and the reference
runs pass before it enters a package.

## 10. Work plan

0. Settings layer: done 23 October 2026 (`capri_mod/settings/defaults.toml`; inventory in
   docs/design/SETTINGS_INVENTORY.md; behaviour-neutral, the reference runs reproduced exactly). The pipeline's
   settings get their own section there. Before the pipeline: the proxy removals of docs/design/PROXY_AUDIT.md and the
   switch of the DEPARTURE settings to CAPRI's (docs/DEPARTURES_FROM_CAPRI.md), the project lead's decisions of
   23 October 2026.
1. Detailed design (this document, extended): exact file list from the CAPRI installation, equations, test plan;
   the code layout of section 9. In progress, started with Step 1 (section 12).
2. Data download layer (section 7) with its documentation. In progress since 23 October 2026: the Eurostat adapter,
   the store, the manifest, the command line and the catalogue of COCO's inputs (docs/DATA_PIPELINE.md).
3. COCO-like and CAPREG-like databases (layers 2–3).
4. CAPTRD-MOD (layer 4), with the parity test against `captrd_2030.json`.
5. Scenario modes (layer 5).

## 11. Decision log

| Date | Decision |
|---|---|
| Oct 2026 | Five-layer pipeline agreed as the extension after the CAPRI-parity work. |
| 22 Oct 2026 | Outline agreed, with corrections from the code: recursive dynamic is beyond CAPRI; CAPTRD solves country by country; the NUTS-2 breakdown sits inside the second solve. |
| 22 Oct 2026 | State-of-the-art review done before any design (section 4). |
| 22 Oct 2026 | Data organisation: Delta Lake for the internal stages, CSV for model inputs, mappings and review tables; true zeros and missing values kept apart; the 2017 path fix is a prerequisite (section 6). |
| 22 Oct 2026 | The provider APIs are documented and the download is a working user mechanism (section 7). |
| 22 Oct 2026 | This document is kept current; obsolete or invalid content is deleted. |
| 22 Oct 2026 | Compatibility: the current model state and the 2030 work stay valid and the default; the pipeline only adds, and every change to existing code must reproduce the reference runs (section 1a). |
| 22 Oct 2026 | Decided (project lead): fix the CAPTRD defects (with a parity switch for the parity test); recursive dynamics take the largest possible set of links; the source order for market balances and the ML candidates are left to the proposal in sections 8.1–8.2. |
| 22 Oct 2026 | Sections 8.1 (source order for market balances) and 8.2 (ML candidates, tiers, acceptance rule) approved by the project lead. |
| 22 Oct 2026 | Code organisation agreed (section 9): pipeline in `capri_mod/pipeline/`, recursive mode in `capri_mod/projection/recursive/`, one-way dependency (the model never imports the pipeline), optional extras. |
| 22 Oct 2026 | The repository nuvolaTeam/CAPRI-MOD is the project lead's own, an old version of this work (15 October 2026); not a separate source. Deliveries continue as zip packages; no git workflow for now (push access not authorised). |
| 23 Oct 2026 | Settings layer agreed: one TOML defaults file with sections (run, outer_loop, supply, market, young_animals, endotech, projection; the pipeline gets its own section), user overrides, validation, the effective settings saved with each run; sourced constants stay in the parameter CSV, CAPRI structure in mapping CSVs, scenarios in scenario files, CLI flags as thin wrappers. Built before the pipeline, behaviour-neutral (reference runs reproduced). |
| 23 Oct 2026 | No proxies: every unsourced number is replaced by CAPRI's data or rules, or removed with a loud failure; where data cannot be found, the project lead helps (docs/design/PROXY_AUDIT.md). Settings follow CAPRI's, except corrections of CAPRI code errors (marked CAPRI-ERROR-FIX); every difference is described (docs/DEPARTURES_FROM_CAPRI.md). CAPRI's Pillar II budgets and intervention stocks are to be ported. |
| 23 Oct 2026 | CAPTRD-MOD started with Step 1 (section 12). CAPRI's CAPREG time series and CAPTRD results (results_1770.gdx) are the parity references in `capri_reference/`. The Step-1 estimator is ported and matches CAPTRD for 99.78% of comparable series. The short-series grid error is confirmed and corrected by default (CAPRI-ERROR-FIX, with a parity switch), pending the project lead's confirmation. |
| 24 Oct 2026 | The error-variance floor is corrected to a variance, (0.05 × |wAve|)², by default (CAPRI-ERROR-FIX, parity switch `captrd.variance_floor_squared`). |
| 23 Oct 2026 | The recursive-dynamic module is named CAPSIM-DYN (project lead); code in `capri_mod/projection/capsim_dyn/` (replaces the provisional `projection/recursive/`). |

## 12. Detailed design: Step 1 (work plan step 1, started 23 October 2026)

### 12.1 Inputs in hand

CAPTRD's inputs are listed in CAPTRD_MAP.md section 2. Their state on 23 October 2026:

| # | Input | In hand | Where / next |
|---|---|---|---|
| 1 | CAPREG time series `res_time_series_17<MS>.gdx` | yes. The 35 files of the project lead's `Capreg_tseries` folder: symbol `DATA` (1984–2018 plus BAS, BASM, CUR, MEAN, TRD, Y), country, NUTS2 and some EU aggregates | `capri_reference/capreg_tseries/17/<CC>.csv.gz` (35.3 million records), `tools/build/build_capreg_tseries_reference.py` |
| 2 | CAPREG base year `res_17<MS>.gdx` (DATA2 → BASM) | text dumps for 27 countries (`res_17zip.zip` and single files); missing: UK, TUR, AL, MK, CS, MO, BA, KO | `capri_reference/capreg_base/17/<CC>.csv.gz` (2,370,736 records), `tools/build/build_capreg_base_reference.py` (29 October 2026) |
| 3 | COCO `coco2_output.gdx` (COCO1 nowcasts, ExAnteD years) | `coco2.csv` (upload coco2.zip, a listing of DATA2) | `capri_reference/coco2/17/coco2_output.csv.gz` (7,892,151 records), `tools/build/build_coco2_reference.py`; with fao_agg's `p_biofuelData` (`capri_reference/fao_agg/17`, `tools/build/build_fao_agg_reference.py`) |
| 4 | Aglink (DG AGRI outlook) of the run | no. `baseline.zip` holds older vintages (up to aglink2017OECD) | needed for Steps 2–3, not Step 1; vintage to be read from the results file META |
| 5–11 | population, nutrient contents, long-run info, age line, Agri_Prod, recent milk yields | only the age line (`baseline.zip`, parquet) | needed for the Step-2 expert supports |
| — | CAPTRD's own results `results_1770.gdx` (p_result, all positions) | yes (upload of 23 October 2026: base 2017, simulation years 2018–2070) | `capri_reference/captrd_results/1770/<respos>.csv.gz`, `tools/build/build_captrd_results_reference.py` |

The results file carries CAPTRD's estimation data `p_result(..., years, "p_data")` (stored after the data
preparation, define_stats_and_supports.gms l. 136-137), its statistics under respos `data` (nObs, nW, wAve, wVar,
wR2, BAS, BAST, BSY, Const/Slope of the requirement functions), and every step: Step1, support, support1, wVarErr,
step2, step3, series. Each step of the port can therefore be tested on CAPTRD's own inputs to that step, before the
data preparation is ported.

### 12.2 Step 1: order of the GAMS code and status

| Part | GAMS | Status |
|---|---|---|
| Trend variable, grid on c | captrd.gms l. 203, 271; estimate_trends.gms l. 28, 80-82 | done (`capri_mod/pipeline/captrd/step1.py`) |
| Time sets ExPost, ExPostT, BASYRS5, BASYRSM, EIGHTLST, BAST, YearsEst | captrd.gms l. 665-812 | next (ExPostT: 1984–2019 in the reference run, 2019 from COCO) |
| Data load and cleaning (copy of years, area rescaling, deletion of series not estimated, early years, UVAD fill, regions, LABH) | captrd.gms l. 418-517, 830-898; check_and_cor_capreg.gms | done (`capri_mod/pipeline/captrd/prepare.py`, 29 October 2026), with BASM from DATA2 (l. 528-580) and the ARTIF correction of check_and_cor_capreg.gms. The sets it reads, CAPRI's global ones copied from the reference export and CAPTRD's own transcribed, are written by `tools/build/build_captrd_sets.py` (COLS_LOAD, ROWS_LOAD, MS, NT2, urbanNUTS, rmAggSup with EU013000, MrkBaleE, DOMPOS, breedAct, MEAT, ...). GAMS assignments are parallel (the right-hand side is read before the statement; GAMS user's guide), which the area rescaling and the UVAD average follow |
| Data preparation (sugar prices, aggregates, SLGW, UVAG, DOMM, TOOU, NTRD, LU density) | prep_data_for_estimation.gms l. 15-162 | done but LU (`prep_for_estimation`): LU.LEVL needs CAPRI's livestock units p_LUUnits (dat/policy/livestock_units.gms, not in hand). Check (`test_captrd_prepare.py`): Denmark's prepared years equal CAPTRD's p_data on all 40,000+ compared records (relative 1e-9), leaving out what the stages not yet ported write: the reporting overwrites of the same position (aggreg_and_report.gms l. 203-220), the policy data (captrd_policy.gms: quotas, set-aside), the COCO nowcasts and biofuel data (load_coco1_data.gms, from coco2_output.gdx) and LU. The UVAD that Denmark lacks (other cereals, 1990) is the average over the 11 countries of its market aggregate A_EU_WEST with data (Germany's 1990 deleted first), as in CAPTRD (slow test). Denmark's BASM equals CAPTRD's BASM position on all 1,200+ compared records, leaving out further the animal requirements (prep_requirement_estimation.gms), the activities' LABF and LABP (labour stage) and DOMM of the products with biofuel use |
| COCO data: the years after CAPREG's series (ExAnteD), biofuels, near-zero flags | load_coco1_data.gms (captrd.gms l. 715) | done (`capri_mod/pipeline/captrd/coco.py`; all stages in CAPTRD's order: `prepare_run.py`), 29 October 2026, but: the default biostocks and DDGS (l. 524-548) need CAPRI's P_ExtrRates and p_ByProduct (dat/biofuel/biofuel_technology_params.gms, not in hand) and are skipped with a warning; the Aglink expert supports of the non-EU countries (p_result_MSnoEU, l. 422-497) belong to the expert supports. Check (slow test): Denmark's years 1984-2019 equal CAPTRD's p_data on 42,000+ records, leaving out the stages not ported, the near-zero flags another country's COCO data sets, the UVAD averages and the default biostocks; not traced: the fossil fuels' UVAG of 2019, which CAPTRD's p_data has and COCO does not |
| nObs, nW, wAve, wVar | prep_data_for_estimation.gms l. 205-247 | done |
| BAS, BSY, feed coefficients (nObs forced to 1) | prep_data_for_estimation.gms l. 250-320 | next |
| WLS grid search | estimate_trends.gms | done |
| Step1, wVarErr, wR2 | define_stats_and_supports.gms l. 44-49, 113-132, 177-179 | done |
| Requirement functions (Step1 of ENNE, CRPR, ...) | define_stats_and_supports.gms l. 86-93; prep_requirement_estimation.gms | next |
| Supports from Step 1 | define_stats_and_supports.gms l. 186-330; BSY prep_data_for_estimation.gms l. 300-317 | done (`supports.py`): on CAPTRD's own inputs, 99.77% of 48,788 comparable series equal CAPTRD's support1 in 2030 (`test_captrd_supports.py`); the rest are trade positions adjust_trade_supports.gms changes later. Not yet: the feed coefficients' error variance and member-state fallback, the requirement functions |

### 12.3 Tests

- **Independent check:** the closed form of estimate_trends.gms against a numpy weighted least squares at every grid
  point (40 series, with gaps and late starts). a, b and wESS are equal to 1e-8, and the chosen c is identical.
- **GAMS domain rules:** 1–4 observations, wVar = 0, zeros as missing.
- **Parity with CAPTRD** (`test_parity_with_captrd_step1`, marked slow). Our Step 1 is run on CAPTRD's own estimation
  data (`p_data` positions, ExPostT 1984–2019), with CAPRI's code as written (`as_coded`), on the 96,478 series
  whose observation count equals CAPTRD's:
  - wAve: 99.9% equal;
  - wR2: 99.9% equal;
  - Step1 in 2030: 99.78% equal (relative tolerance 1e-7).

  Excluded from the comparison:
  - NTRD, which the reporting overwrites with EXPT − IMPT (aggreg_and_report.gms l. 296);
  - DOMM, which is re-aggregated from its components, so it is compared with the estimated value CAPTRD keeps under
    DEMD (l. 293-294).

  Not yet traced:
  - the remaining 0.22%: product groups (CERE, MEAS, OILS: UVAG, INHA) and land items of a few NUTS2 regions;
  - about 4,000 series where CAPRI's nObs differs from the count of nonzero years: requirement and feed rows, where
    CAPRI forces nObs = 1. These belong to the parts marked "next".

### 12.4 Found while porting

- **Short series (2–4 observations) get Step1 = 0.** The minimum over the 30 grid points counts the 29 zeroed
  points (estimate_trends.gms l. 160-171). Confirmed in the reference run: 92 of the 93 such series have Step1 = 0.
  - With 2 observations, the support falls to 0.001 × base (wR2 = 1 because wVar is undefined).
  - With 3–4 observations, the trend is ignored (wR2 = 0).

  Corrected by default (CAPRI-ERROR-FIX), with a parity switch; see docs/DEPARTURES_FROM_CAPRI.md.
- **The error variance divides by nW − 1.** nW = Σt over the observed years, with t = 0.1 … 3.6. A series observed
  only in the earliest years can have nW ≤ 1, and then a negative or infinite variance. This is kept as coded: in the
  reference run no series with more than 2 observations has nW ≤ 1 (0 of 143,226).
- **BASYRS5 ("5 years", |t − BAS| ≤ 3)** is restricted to ExPost. CAPREG's series end in 2018 = BAS + 1, so in
  the reference run the window is 2014–2018: five years, as named. The listed defect (section 8.3) is not one in
  this configuration; it spans more than five years only if CAPREG's series reach BAS + 2 or later.
- **Time sets reproduced** (`capri_mod/pipeline/captrd/timesets.py`):
  - YearsEst equals CAPTRD's Step1 years (1985, 1990, 1995, 2000, 2018–2070);
  - ExPostT is 1984–2019 (2019 from COCO);
  - Fst/Sec_exAnte are 2018/2020;
  - BASYRST is 2017–2019.

  BAST equals the mean of the nonzero p_data over BASYRST for 43,857 of 45,408 series. The rest is computed in
  scale_DG_AGRI_baseline.gms, not yet ported.
- **The error-variance floor compares a level with a variance** (define_stats_and_supports.gms l. 327-329):
  wVarErr = max(0.05 × |wAve|, wVarErr). It is in force in CAPRI's own output. Of 7,968 series without
  external information (no expert, COCO, trust-level or DG AGRI entry; not requirements, NTRD or DOMM), the stored
  wVarErr in 2030 matches this formula, computed from our Step 1, for 97.1%. For 1,554 of them (19.5%) the level
  term is the binding one. The remaining 2.9% (e.g. AL EXPT, ×25) come from later rules not yet ported.

  The term is in the units of the series, not squared, so its weight relative to the trend's variance depends on the
  series' unit: a level of 100 gives a "variance" of 5, a level of 0.01 gives 0.0005. That wVarErr is a variance in
  CAPRI's own code is shown by its definition (a sum of squared residuals, l. 118-123), its fall-back for 1-2
  observations (SQR(wAve) × 0.25, l. 130) and its later use as one (sqrt(wVarErr) as a standard deviation,
  define_eu_supports.gms l. 693, 705). Fixed on 24 October 2026 (project lead: "fix the still open"): the floor is
  (0.05 × |wAve|)², a 5% coefficient of variation; `captrd.variance_floor_squared = false` reproduces CAPRI. It has no
  effect until Steps 2-3 are ported; then it changes the weight of about a fifth of the series.
- **The NUTS 2 column filter deletes nothing as coded** (captrd.gms l. 872-876). The statement is meant to keep only
  the activities, land use, GROF and ARTO of the NUTS 2 regions, but its condition NOT SUM(SAMEAS(MS,NT2),1) has NT2
  uncontrolled: the sum runs over MS and NT2 together and counts the 14 countries that are their own NUTS 2 region,
  so the condition is false everywhere. CAPTRD's own p_data is consistent with this: its NUTS 2 regions keep, among
  others, LOSF, UVAG, EAAG and SEDF (266,493 records), which the statement would delete. Ported as coded (`clean_regions`); a fix (the condition per NUTS 2 region,
  as the two following statements have it) is for the project lead to decide, since it removes series from the NUTS 2
  estimation.
- **Reporting overwrites the p_data position.** aggreg_and_report.gms writes the product aggregates (INHA, UVAG, UVAD
  and the market balance of the OAGG rows) and the activity aggregates' TOOU into p_result(..., "p_data") after the
  estimation. CAPTRD's stored INHA.CERE of Denmark before 2005 therefore lacks maize (its INHA.MAIZ has no base-year
  value, so no stored series), while the INHA.CERE CAPTRD estimated includes it. Parity tests on the p_data position
  must leave these records out.
- **DOMM and NTRD in CAPTRD's output** are reporting re-aggregates in every position, Step1 included. A parity test
  must use DEMD for DOMM, and cannot test NTRD's estimated Step1.

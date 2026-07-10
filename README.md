# CAPRI-Python

A Python reimplementation of the core of the **CAPRI** model (Common Agricultural
Policy Regionalised Impact) — a large agro-economic model used for EU agricultural
and environmental policy analysis.

> **Research reimplementation, not an official CAPRI product.** This is an independent
> Python port, not affiliated with or endorsed by the CAPRI network or EuroCARE. See
> [Chapter 1](#1-introduction) for validation status before using results.

---

## Table of contents

1. [Introduction — what this is, goals, and what it can do](#1-introduction)
2. [Input data](#2-input-data)
3. [Requirements and running the model](#3-requirements-and-running-the-model)
4. [Baselines and calibration](#4-baselines-and-calibration)
5. [Scenarios — creation, running, and comparison](#5-scenarios)
6. [Next steps](#6-next-steps)

---

## 1. Introduction

### What this project is

CAPRI-Python reproduces the two-tier structure at the heart of CAPRI:

- a **regional supply** side — Positive Mathematical Programming (PMP) over 248 EU
  NUTS-2 regions, where each region's crop and animal activities respond to prices
  under land and policy constraints, and
- a **global market** — an Armington trade system across 29 world regions that clears
  by iteration, linking EU supply to world prices.

The two are connected in an outer loop: supply reacts to prices, the market re-clears,
and the process repeats until prices and quantities are mutually consistent.

### Scope

- **248** EU NUTS-2 regions
- **29** crop and **11** animal activities
- **32** traded commodities across **29** world trade regions
- **Six modules**: supply, market, policy, environment, feed, biofuel

### Main goals

1. Make CAPRI's core economics available in a transparent, modern, scriptable Python
   codebase that is easy to read, run, and extend.
2. Stay faithful to CAPRI's data and methodology — real CAPRI/FAO inputs, PMP
   calibration, Armington trade — rather than a simplified teaching model.
3. Be honest about what is and isn't validated.

### Achievements

- **Exact base year.** Reproduces CAPRI's 2017 base-year prices for all 12 reference
  commodities at 0% deviation; the market converges.
- **100% real inputs.** Every dataset is real CAPRI or FAO data (23 CAPRI + 4 FAO);
  no synthetic placeholders. A data validator enforces this on every load.
- **All six modules run** end to end.
- **Validated against CAPRI's own numbers** on two independent checks: supply
  elasticities vs CAPRI's estimated PELA values (major cereals within ~10%), and
  relative price structure vs a real CAPRI scenario run (rank correlation **0.998**).

### What it can do

- Run a baseline and inspect regional activity levels, prices, trade, and
  environmental indicators.
- Apply policy or trade shocks (tariffs, CAP payments, set-aside, quotas) and see how
  supply and markets respond.
- Compute environmental outputs (GHG, nitrogen balance, land use) and feed/biofuel
  balances.

### What it is *not* (yet)

Its base year is exact and its behaviour is plausible and structurally validated, but
**scenario shock magnitudes are not yet certified** against CAPRI's own scenario
outputs (see [Chapter 5](#5-scenarios) and `capri_data/validation/`). Treat it as a
faithful, well-calibrated reimplementation — not a drop-in replacement for CAPRI.

---

## 2. Input data

All inputs live under `capri_data/` as CSV files. Every file is real CAPRI or FAO data;
provenance and vintage are tracked in `capri_data/MANIFEST.json` and
`capri_data/DATA_SOURCING_REGISTRY.json`.

### Main data groups

| File(s) | Content | Source | Vintage |
|---------|---------|--------|---------|
| `base_areas.csv`, `yields.csv`, `animal_numbers.csv` | regional activity levels | CAPRI COCO | 2017 |
| `producer_prices.csv`, `world_prices.csv` | prices | CAPRI SUA | 2017 |
| `pmp_diagonal_terms.csv`, `pmp_crossgroup_terms.csv`, `pmp_own_price_elasticities.csv` | PMP calibration | CAPRI estimation | 2017 |
| `supply_elasticities_regional.csv` | regional supply elasticities | CAPRI | 2017 |
| `armington_params.csv`, `trade_flows.csv` | trade system | CAPRI / FAO | 2017 / **2021** |
| `cap_payments.csv`, `eu_mfn_tariffs.csv` | policy | CAPRI / EU | 2017 |
| `nutrient_coefs.csv`, `crop_nutrient_export.csv` | fertiliser N/P2O5/K2O | CAPRI capreg | 2017 |
| `feed_requirements.csv`, `coco_feed_availability_national.csv` | feed | CAPRI capreg | 2017 |
| `manure_ch4_ef_regional.csv`, `climate_zones.csv` | environment | IPCC / CAPRI | 2006 / 2017 |
| `variable_costs.csv`, `input_requirements.csv`, `land_availability.csv` | costs & constraints | CAPRI | 2017 |

### Vintages

The base year is **2017** (quantities, prices, PMP parameters — all mutually
consistent). Bilateral **trade** is refreshed to **2021**. Mixing vintages is guarded:
the validator flags any inconsistency, because a newer base year would require CAPRI to
re-estimate its PMP parameters (a CAPRI-side computation).

### Validate the data

```bash
python capri_python/data/validate_data.py capri_data
```

Checks presence, shape, vintage consistency, economic sanity, non-negativity, and
detects any synthetic data. Expected: `11 pass, 0 warn, 0 fail`.

### Provenance & extraction

Data derived from a CAPRI installation (feed, fertiliser) was extracted from CAPRI's
capreg `DATA2` cube via `gdxdump`; the method and unit conventions are documented in
`capri_data/sources/capri_star/capreg_extracts/`. See `docs/` for acquisition guides.

---

## 3. Requirements and running the model

### Requirements

- Python >= 3.9
- numpy, pandas, scipy (see `requirements.txt`)

### Install

```bash
git clone https://github.com/USERNAME/capri-python.git
cd capri-python
pip install -r requirements.txt      # or: pip install -e ".[dev]"
```

### Run a baseline

```python
from capri_python.model import CAPRIModel

m = CAPRIModel(data_dir="capri_data", verbose=False)

results = m.run(
    scenario="BASELINE",
    regions=list(m.data["areas"].index[:30]),   # use >=30 regions (see note)
    run_environmental=True,
    run_feed=True,
    run_biofuel=True,
    biofuel_mandate=0.065,
)

print(results["market"].world_prices)        # cleared world prices
print(results["supply"]["DE11"].activities)  # activity levels in a region
```

### Key `run()` arguments

| Argument | Meaning |
|----------|---------|
| `scenario` | `"BASELINE"` or a named scenario |
| `custom_scenario` | a `PolicyScenario` object (see Chapter 5) |
| `world_price_shock` | `{commodity: pct}` direct world-price shock |
| `regions` | subset of NUTS-2 regions to solve |
| `run_environmental` / `run_feed` / `run_biofuel` | toggle modules |
| `max_outer_iter`, `market_max_iter` | solver controls |

> **Use a representative region sample (>=30 regions).** A handful of regions gives an
> unrepresentative EU supply base and distorts market calibration. This caused apparent
> price gaps during development that vanished at 30+ regions. For a full run, pass all
> regions.

### Tests

```bash
pytest capri_python/tests/ -v
```

Covers data loading, the validator, base-year fidelity (12/12), supply response signs,
no numerical blow-ups, full-run integration, and the price-structure validation.

---

## 4. Baselines and calibration

### What "baseline" means here

The baseline is the 2017 calibrated equilibrium: the state in which the model exactly
reproduces CAPRI's observed areas, yields, herds, and prices. Every scenario is
measured as a deviation from this baseline.

### PMP calibration (supply side)

The supply module uses **Positive Mathematical Programming** (Howitt 1995), extended
with CAPRI's cross-commodity calibration (Britz & Witzke 2008). In short:

1. Observed base-year activity levels are taken as optimal.
2. A quadratic cost matrix `Q` is recovered so that, at base-year prices, the region's
   profit-maximising choice exactly matches the observed activities.
3. Cross-commodity terms are calibrated so supply elasticities match CAPRI's estimated
   values (`pmp_*` files).

This is why the base year is exact by construction — the calibration *is* the baseline.
The relevant data is pre-computed in `pmp_diagonal_terms.csv`,
`pmp_crossgroup_terms.csv`, and `pmp_own_price_elasticities.csv`.

### Market calibration

The Armington market is recalibrated so that base-year production, consumption, and
trade flows form an equilibrium at CAPRI's base-year prices. Verify with:

```bash
pytest capri_python/tests/test_capri.py::test_base_year_market_fidelity -v
```

### Changing the base year

A newer base year is **not** just newer input files — it requires CAPRI's re-estimated
PMP parameters for that year. Mixing newer prices/quantities onto 2017 PMP terms breaks
calibration (and the validator will flag it). See `docs/DATA_LOCATION_MAP.md` for the
upgrade path.

---

## 5. Scenarios

### Creating a scenario

Scenarios are defined with the `PolicyScenario` dataclass, which captures CAP and trade
policy levers relative to the baseline:

```python
from capri_python.policy.policy_module import PolicyScenario

scen = PolicyScenario(
    name="tariff_liberalisation",
    description="Remove MFN tariffs on cereals",
    tariff_changes={"WORLD": {"SWHE": -100.0, "BARL": -100.0}},  # % change
    biss_rate_change=0.0,
    set_aside_requirement=0.0,
)
```

Available levers include: Pillar I basic income support (`biss_rate_change`), coupled
support, eco-scheme budget share; Pillar II (agri-environment, organic, ANC rates);
trade measures (`tariff_changes`, `trq_volume_changes`); environmental constraints
(`nitrate_limit_change`, `set_aside_requirement`); and historical quotas (`milk_quota`,
`sugar_quota`).

### Running a scenario

```python
baseline = m.run(scenario="BASELINE", regions=regions)
shocked  = m.run(custom_scenario=scen, regions=regions)
```

A direct world-price shock is also available without a full scenario:

```python
m.run(world_price_shock={"SWHE": +0.20}, regions=regions)   # +20% wheat
```

### Comparing results

Compare the two runs on the quantities of interest — prices, activity levels, trade,
environmental indicators:

```python
for c in ["SWHE", "BARL", "RAPE"]:
    p0 = baseline["market"].world_prices[c]
    p1 = shocked["market"].world_prices[c]
    print(f"{c}: {100*(p1-p0)/p0:+.1f}% price change")
```

### Validation status of scenarios

The model's **base year** and **relative price structure** are validated against
CAPRI's own data (see `capri_data/validation/VALIDATION.md`). What is **not yet**
certified is the **magnitude** of a strong policy shock versus CAPRI's own scenario
output — because the available CAPRI scenario runs so far are mild (<1% contrast). To
complete this, run a strong-shock CAPRI scenario and compare; the procedure is in
`capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md`, and the harness in
`capri_python/tests/scenario_validation.py` is ready to consume the numbers.

---

## 6. Next steps

Current priorities, roughly in order of value:

1. **Scenario shock-magnitude validation** — the one substantive gap. Needs a CAPRI
   scenario pair with a strong, clear policy shock (trade liberalisation, payment
   removal). See the guide in `capri_data/validation/`.
2. **Additional modules** — CAPRI has more components that could be added. Highest
   value-per-effort: **water** (irrigation), **energy indicators**, and **sugar**;
   **farm-type disaggregation** is the biggest but most involved. `capdis` (1x1 km
   downscaling) and full CGE/GTAP coupling are deliberately out of scope.
3. **Simultaneous solve** — CAPRI solves supply + market as one system; this uses an
   outer loop. Agreement is exact at the base and close for moderate shocks; a
   simultaneous solve would tighten large-shock behaviour.
4. **Newer base year** — requires CAPRI's re-estimated PMP parameters; makes the model
   newer, not more correct.
5. **Minor-crop calibration** — a few minor crops (e.g. pulses) show weaker elasticity
   agreement and are worth refining.

---

## License

**GPL-3.0-or-later** — see [LICENSE](LICENSE). Matches CAPRI's own licensing.

## Acknowledgements

Built on data and methodology from the CAPRI model (EuroCARE / Bonn University) and
FAOSTAT. CAPRI-Python is an independent reimplementation and not an official CAPRI
release. See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved — the highest-value
contribution is real CAPRI scenario results to complete validation.

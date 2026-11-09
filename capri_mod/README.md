# CAPRI-mod

An AI-assisted, validated Python reimplementation of the **economic logic** of the
**CAPRI** (Common Agricultural Policy Regionalised Impact) model — not a release
of the CAPRI modelling system itself. See the top-level `README.md` for scope,
validation status and fitness for use.

## Structure

```
capri_mod/
├── model.py                   # Top-level CAPRIModel class
├── data/
│   ├── definitions.py         # Commodity sets, 248 NUTS-2 regions, trade regions
│   └── loaders.py             # Data loading (real CSV data; fails loud if absent)
├── supply/
│   └── supply_module.py       # 248 regional NLP models + PMP calibration
├── market/
│   └── market_module.py       # Armington global spatial equilibrium
├── policy/
│   └── policy_module.py       # CAP direct payments, TRQs, intervention
├── environmental/
│   └── environmental_module.py # GHG (IPCC), N balance, biodiversity
├── scenarios/
│   └── scenarios.py           # Built-in scenarios + registry
├── utils/
│   └── utils.py               # Calibration, convergence, reporting
└── tests/
    └── test_capri.py          # Full test suite (9/9 passing)
```

## Quick Start

```python
from capri_mod import CAPRIModel

# Load the real, validated CAPRI data that ships with the repo
model = CAPRIModel(data_dir="capri_data")

# Run baseline
baseline = model.run(scenario="BASELINE")

# Run CAPRI's Farm-to-Fork counterfactual
from capri_mod.policy.greendeal import farm_to_fork_scenario
f2f = model.run(custom_scenario=farm_to_fork_scenario())

# Compare
comparison = model.compare(baseline, f2f)

# Export results
reporter = model.get_reporter(baseline)
reporter.to_excel("results/baseline.xlsx")
reporter.to_csv_folder("results/")
```

> **The model runs on real, validated data or not at all.** `CAPRIModel(data_dir="capri_data")`
> loads the CAPRI-derived inputs that ship with the repository. Calling
> `CAPRIModel()` with no data directory now raises an error rather than silently
> generating synthetic data — a policy model must use validated inputs, never
> fabricated ones. A synthetic path remains only as an explicit opt-in
> (`load_all_data(allow_synthetic=True)`) for isolated testing.

## Available Scenarios

| Name | Description |
|------|-------------|
| `BASELINE` | Calibrated baseline, no policy change |
| `CARBON_TAX_50` | CAPRI's emission tax on agricultural emissions (pol_input/ecampa/carbtax50_endotech_set12.gms) |

Custom scenarios:
```python
from capri_mod.policy.policy_module import PolicyScenario
my_scenario = PolicyScenario(
    name="MY_SCENARIO",
    biss_rate_change=-50,       # EUR/ha cut in direct payments
    nutrient_surplus_target=True,   # CAPRI's tiered N-balance target (JRC121368)
    lfa_budget_change=-0.2,     # CAPRI's LFA budget -20% (premium change by CAPRI's 2030 split by scheme)
)
results = model.run(custom_scenario=my_scenario)
```

World price shocks:
```python
results = model.run(
    scenario="BASELINE",
    world_price_shock={"SWHE": 0.40, "CORN": 0.35}  # +40% wheat, +35% maize
)
```

## Connecting Your Data

The model reads its inputs from `capri_data/` (CSV), built by the builders in `tools/build/` from CAPRI's own files
(capri_data/schema/01_provenance.sql records the builder and the sources of every file). Some of the main ones:

| File | Built by | From | Content |
|------|----------|------|---------|
| `2017/supply/base_areas.csv` | build_capri_base | CAPRI's 2017 base (CAPREG results) | Crop areas [region × crop], 1000 ha |
| `2017/supply/animal_numbers.csv` | build_capri_base | CAPRI's 2017 base (CAPREG results) | Animal numbers [region × animal], 1000 heads |
| `2017/supply/yields.csv` | build_crop_economics_2017 | CAPRI's 2030 reference results and sim_ini_21730 | Yields [region × activity] |
| `2017/supply/variable_costs.csv` | build_crop_economics_2017 | CAPRI's 2030 reference results and sim_ini_21730 | Costs [region × activity], EUR/ha or EUR/head |
| `2017/supply/land_availability.csv` | build_capri_base | CAPRI's 2017 base (CAPREG results) | UAA [region × land type], 1000 ha |
| `2017/market/producer_prices.csv` | build_eu_producer_prices | CAPRI, with unsourced values marked | Producer prices [activity], EUR/t |
| `2017/market/world_prices.csv` | build_world_prices | CAPRI | World prices [commodity], EUR/t |
| `2017/policy/cap_payments.csv` | build_crop_economics_2017 | CAPRI | CAP payment rates [region × type], EUR/ha |

CAPRI's own sources behind these (Eurostat, FAOSTAT, FADN and others) enter through CAPRI's database, not directly.
`capri_data/README.md` and `docs/EXTERNAL_SOURCES.md` describe the layout and CAPRI's material outside git.

```python
model = CAPRIModel(data_dir="path/to/capri_data/")
```

## Mathematical Reference

- **Supply module**: Positive Mathematical Programming (Howitt 1995), regional NLP
- **Market module**: CAPRI's market model (two-level Armington CES, GL food demand, tariff-rate quotas), solved per commodity with Newton steps and Anderson acceleration (DEP-16)
- **Environmental**: IPCC (2019) Tier 1/2 GHG emission factors, OECD N balance
- **Policy**: EU Reg. 2021/2115 (CAP Strategic Plans), WTO schedule TRQs

**Reference**: Britz, W. & Witzke, H.P. (2012). *CAPRI Model Documentation 2012*. University of Bonn.

## Added in October 2026

- `supply/convex_qp.py` — convex quadratic programming for the manure-pool equilibrium:
  Clarabel when installed (`pip install clarabel`), otherwise a built-in interior-point
  method (Mehrotra predictor-corrector).
- `feed/ration.py` — CAPRI's rations per region and animal, the data of the feeding block inside the regional models.
- Supply model: CAPRI's land market (`use_land_market`, on), fodder equality, and the
  optional manure market (`use_manure_market`, off; see `docs/MANURE_MARKET.md`).

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
| `SET_ASIDE_10PCT` | 10% set-aside (CAPRI scen/set_aside/set_aside_10.gms) |
| `CARBON_TAX_50`, `CARBON_TAX_100` | CAPRI's emission tax on agricultural emissions |

Custom scenarios:
```python
from capri_mod.policy.policy_module import PolicyScenario
my_scenario = PolicyScenario(
    name="MY_SCENARIO",
    biss_rate_change=-50,       # EUR/ha cut in direct payments
    nitrate_limit_change=-30,   # stricter N limit
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

Replace or extend the shipped data by placing CSV files in a directory:

| File | Source | Content |
|------|--------|---------|
| `base_areas.csv` | Eurostat `apro_cpsh1` | Crop areas [region × crop], 1000 ha |
| `animal_numbers.csv` | Eurostat `ef_lsk` | Animal numbers [region × animal], 1000 heads |
| `yields.csv` | Eurostat `apro_cpsh1` | Yields [region × activity], t/ha or t/head |
| `producer_prices.csv` | Eurostat `apri_ap_ina` | Prices [activity], EUR/t |
| `variable_costs.csv` | FADN | Costs [activity], EUR/ha or EUR/head |
| `land_availability.csv` | Eurostat `ef_oluaa` | UAA [region × land_type], 1000 ha |
| `world_prices.csv` | FAOSTAT / OECD Outlook | World prices [commodity], EUR/t |
| `trade_flows.csv` | UN COMTRADE / BACI | Flows [(exporter, importer) × commodity], 1000 t |
| `cap_payments.csv` | EU DG-AGRI / IACS | CAP payment rates [region × type], EUR/ha |
| `tariffs.csv` | WTO tariff database | Import tariffs [region × commodity], % |

```python
model = CAPRIModel(data_dir="path/to/your/data/")
```

## Mathematical Reference

- **Supply module**: Positive Mathematical Programming (Howitt 1995), regional NLP
- **Market module**: Armington (1969) CES spatial equilibrium, tatonnement solver
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

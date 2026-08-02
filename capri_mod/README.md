# CAPRI-Python

A Python implementation of the **CAPRI** (Common Agricultural Policy Regionalised Impact) modelling system.

## Structure

```
capri_python/
├── model.py                   # Top-level CAPRIModel class
├── data/
│   ├── definitions.py         # Commodity sets, 248 NUTS-2 regions, trade regions
│   └── loaders.py             # Data loading (CSV or synthetic fallback)
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
from capri_python import CAPRIModel

# Use synthetic data (or pass data_dir= with your CSVs)
model = CAPRIModel()

# Run baseline
baseline = model.run(scenario="BASELINE")

# Run Farm-to-Fork counterfactual
f2f = model.run(scenario="FARM_TO_FORK")

# Compare
comparison = model.compare(baseline, f2f)

# Export results
reporter = model.get_reporter(baseline)
reporter.to_excel("results/baseline.xlsx")
reporter.to_csv_folder("results/")
```

## Available Scenarios

| Name | Description |
|------|-------------|
| `BASELINE` | Calibrated baseline, no policy change |
| `FARM_TO_FORK` | EU F2F targets: organic +25%, fertiliser -20%, N limits |
| `CAP_REFORM_2030` | Flat-rate BISS convergence, stronger eco-schemes |
| `WTO_LIB` | 50% EU tariff cut + TRQ expansion |
| `UKRAINE_SHOCK` | Black Sea trade disruption (cereal/oilseed price shocks) |

Custom scenarios:
```python
from capri_python.policy.policy_module import PolicyScenario
my_scenario = PolicyScenario(
    name="MY_SCENARIO",
    biss_rate_change=-50,       # EUR/ha cut in direct payments
    nitrate_limit_change=-30,   # stricter N limit
    eco_scheme_budget_pct=0.40, # 40% of Pillar I to eco-schemes
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

Replace synthetic data by placing CSV files in a directory:

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

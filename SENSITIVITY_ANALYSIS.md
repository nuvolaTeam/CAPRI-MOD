# Batch and sensitivity runs with capri-mod

*Rewritten 20 October 2026 against the code. capri-mod has no sensitivity module of its own; it has result
persistence (`capri_mod/io_results.py`) and a parameter table, which make batch runs straightforward. The examples
use SALib for the design and the analysis; install it separately (`pip install SALib`).*

## 1. What you can vary

**Policy and run settings** (`PolicyScenario` in capri_mod/policy/policy_module.py; README section 6):

| Lever | Where | Note |
|---|---|---|
| landscape, organic, pesticide, mineral fertiliser, surplus targets | `PolicyScenario` fields or `greendeal_scenario(...)` | CAPRI's Green Deal switches; `greendeal_scenario` accepts only CAPRI's values |
| emission tax | `PolicyScenario.carbon_tax` | EUR/t CO2-eq, EU regions |
| CAP payments | `biss_rate_change`, `coupled_support`, `premium_factor_regional`, `lfa_budget_change`, `ae_budget_change`, `n2k_budget_change` (`eco_scheme_budget_pct` is a reporting split) | |
| tariffs | `tariff_changes` | ad valorem points on EU imports |
| surplus cut, biofuel mandate at 0 | `surplus_cut=0`, `biofuel_mandate=0` | read as given (0 used to be read as the default) |
| biofuel mandate | `PolicyScenario.biofuel_mandate` | factor on the EU and UK mandates (not a `run()` argument) |
| mitigation settings | `PolicyScenario.endotech` or `run(endotech=...)` | `ghgTechMYld`, `ghgTechFEff`, `ghgTechLowNFeed`, `ghgTechLineNitr` |
| world prices | `run(world_price_shock={comm: change})` | a scenario against the unshocked baseline, also under `scenario="BASELINE"` |
| biofuel output (biofuel markets off) | `run(biofuel_output_scale={"BIOE": x, "BIOD": y})` | |
| model parameters | `capri_data/shared/model_parameters.csv` | every constant with its source; edit a copy of the data folder |
| baseline | the trajectory (`capri_data/trajectories/`) | 2030 runs |
| EU tariff-rate quotas | `PolicyScenario.trq_volume_changes` | `{commodity: change in 1000 t}` on CAPRI's quotas, spread over exporters by base volume; a commodity without a CAPRI quota raises an error |

Not levers: `milk_quota` / `sugar_quota` (raise an error) (KNOWN_ISSUES K52).

## 2. Outputs per run

`flatten_outputs(results)` reduces a run to one flat record:

- `price_<comm>`: world prices; `price_EU27_<comm>`, `prod_EU27_<comm>`: the EU's market price (EUR/t) and production
  (1000 t);
- `env_EU_<indicator>`: EU totals of the environmental accounts (`ghg_total`, `ghg_non_co2`, `ghg_enteric`,
  `ghg_manure_ch4`, `ghg_manure_n2o`, `ghg_soil_n2o`, `ghg_leaching_n2o` in kt CO2-eq; `nh3_total` in kt NH3;
  `n_surplus`, `n_mineral_input`, `n_organic_input` in t N);
- `supply_total_gross_margin` (EUR 1000), `supply_n_regions`, `supply_all_converged`;
- `biofuel_*` with `run_biofuel=True`;
- `market_converged`, `market_iterations`, `outer_converged`.

The full results (regional activities, market tables, environmental table) stay available per run.

## 3. Saving runs

```python
from capri_mod.io_results import Experiment, load_experiment

exp = Experiment("my_study", root="outputs", model=model)   # outputs/my_study/
exp.save_run(results, run_id="run_0001", inputs={"carbon_tax": 50})
table = exp.finalise()                                     # outputs/my_study/batch_summary.csv
table = load_experiment("outputs/my_study")                # later, without re-running
```

Layout: `outputs/<experiment>/manifest.json`, `batch_summary.csv` (one row per run: `in_*` inputs and the flat
outputs), `runs/<run_id>/` with `summary.json`, the market tables (`market_world_prices.csv`,
`market_production.csv`, ...), `supply_activities.csv`, `supply_indicators.csv`.

## 4. A batch: an emission-tax sweep

```python
from capri_mod.model import CAPRIModel
from capri_mod.io_results import Experiment
from capri_mod.policy.policy_module import PolicyScenario

model = CAPRIModel(data_dir="capri_data", verbose=False)
exp = Experiment("tax_sweep", model=model)
for tax in (25, 50, 100, 150):
    r = model.run(custom_scenario=PolicyScenario(name=f"TAX{tax}", carbon_tax=tax))
    if not r["metadata"]["outer_converged"]:
        continue                                            # keep only converged runs
    exp.save_run(r, run_id=f"tax_{tax}", inputs={"carbon_tax": tax})
table = exp.finalise()
```

The baseline is solved once (first scenario run) and reused by every later run with the same settings.

## 5. A Sobol design with SALib

```python
import numpy as np
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol
from capri_mod.model import CAPRIModel
from capri_mod.io_results import Experiment, flatten_outputs
from capri_mod.policy.policy_module import PolicyScenario

model = CAPRIModel(data_dir="capri_data", verbose=False)
problem = {"num_vars": 2, "names": ["carbon_tax", "wheat_price_shock"],
           "bounds": [[0.0, 150.0], [-0.30, 0.30]]}
X = sobol_sample.sample(problem, 64)
exp = Experiment("sobol_tax_wheat", model=model)
Y = []
for i, (tax, shock) in enumerate(X):
    r = model.run(custom_scenario=PolicyScenario(name=f"S{i}", carbon_tax=float(tax)),
                  world_price_shock={"SWHE": float(shock)})
    exp.save_run(r, run_id=f"run_{i:05d}", inputs={"carbon_tax": float(tax), "wheat_price_shock": float(shock)})
    Y.append(flatten_outputs(r)["env_EU_ghg_total"])
exp.finalise()
Si = sobol.analyze(problem, np.array(Y))
print("S1:", Si["S1"], "ST:", Si["ST"])
```

## 6. Practical notes

- **Run time.** A 2030 run (projection, baseline and scenario) takes 35-40 minutes on 2 cores in the NLP form; runs on
  the 2017 base have not been timed in the NLP form. Plan the design size accordingly; runs are independent and can be
  spread over machines. The conic form (`CAPRIModel.supply_form = "conic"`) is faster for some scenarios and further
  from CAPRI's form.
- **Region subsets** are for checks, not results: prices are formed on the whole market.
- **Convergence.** Keep only runs with `outer_converged`; an unconverged run overstates quantity responses.
- **Reproducibility.** Start Python with `PYTHONHASHSEED=0`.
- **2030 runs.** Use `ProjectionModule` (README section 10.2 (The projection layer)); each year's baseline is calibrated to the trajectory, then
  the scenario is solved against it. `ProjectionResult.increment[year]` holds the % changes of the flat outputs.

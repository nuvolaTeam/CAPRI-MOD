# CAPRI-mod — Inputs, Outputs, and Sensitivity Analysis

A reference for running sensitivity / uncertainty analysis on CAPRI-mod.

## 1. How many inputs and outputs?

### Inputs — two distinct senses (make sure you mean the right one)

**(a) Data inputs** — the numbers loaded from `capri_data/`:

| Category | Files | Variable columns | Data points |
|----------|------:|-----------------:|------------:|
| supply | 10 | 150 | 145,954 |
| shared (trade) | 1 | 33 | 27,753 |
| policy | 2 | 37 | 1,272 |
| environment | 4 | 10 | 1,359 |
| feed | 2 | 22 | 418 |
| market | 3 | 5 | 173 |
| **Total** | **22** | **257** | **176,929** |

So: **22 input files, 257 variable columns, ~177,000 individual data points.**
For a global sensitivity analysis over *every* data point, the dimensionality is
~177k — usually far too large; you normally pick a **subset** of variables or
scale whole groups (e.g. "yields ±10%").

**(b) Policy / scenario levers** — the 14 fields of `PolicyScenario` plus the
`run()` arguments. These are the natural, low-dimensional "knobs" most sensitivity
studies vary:

| Lever | Type |
|-------|------|
| `biss_rate_change` | Pillar-I basic income support | 
| `coupled_support` | coupled payments per commodity |
| `eco_scheme_budget_pct` | eco-scheme budget share |
| `aecs_rate_change`, `organic_rate_change`, `anc_rate_change` | Pillar-II rates |
| `tariff_changes` | import tariffs per region/commodity |
| `trq_volume_changes` | tariff-rate-quota volumes |
| `nitrate_limit_change` | N limit |
| `set_aside_requirement` | set-aside share |
| `milk_quota`, `sugar_quota` | quotas |
| `run(biofuel_mandate=…)` | biofuel mandate share |
| `run(world_price_shock=…)` | direct world-price shocks per commodity |

**Recommendation:** start sensitivity analysis on group (b) — ~15 interpretable
levers — and optionally a handful of scaled data groups from (a) (yields, costs,
elasticities). That keeps the problem tractable and the results interpretable.

### Outputs

`run()` returns a dict. `flatten_outputs()` reduces each run to **~40 scalar
indicators** (the natural response variables for sensitivity analysis):

- `price_<commodity>` — cleared world price for each of the 32 commodities
- `prod_<commodity>` — production
- `biofuel_bioethanol_kt`, `biofuel_biodiesel_kt`
- `supply_total_gross_margin`
- `market_converged`, `market_iterations`

Full (non-scalar) outputs available per run: regional supply activities (region ×
activity), market prices/production/consumption/trade, feed, environmental
indicators, per-region GHG and nutrient balances.

## 2. Where CAPRI-mod stores output data

`run()` returns results **in memory only** — nothing is written unless you ask.
Use `capri_mod.io_results` to persist them.

Results go to a **git-ignored `outputs/` folder, created relative to the current
working directory**. Run your script from the repo root and you get
`<repo>/outputs/`; run it elsewhere and `outputs/` appears there. To pin the
location explicitly, pass `root=`:

```python
exp = Experiment("my_study", root="/abs/path/to/results", model=m)
```

Layout (see `docs/OUTPUTS.md` for the full description):

```
outputs/<experiment>/
  manifest.json          experiment metadata (base year, run count, timestamps)
  batch_summary.csv      ONE ROW PER RUN: in_* sampled inputs + output indicators
  runs/<run_id>/
    summary.json         scenario, inputs, metadata, scalar outputs
    market_world_prices.csv     market_production.csv
    market_domestic_prices.csv  market_consumption.csv
    market_net_exports.csv      market_trade_flows.csv
    supply_activities.csv       region x activity levels
    supply_indicators.csv       region x gross margin, GHG, nutrient balance
    feed.csv / environmental.csv   (when those modules ran)
```

`batch_summary.csv` is the file a sensitivity analysis actually consumes: the
inputs you sampled (as `in_*` columns) sit alongside every output indicator.

## 3. Running a sensitivity batch

```python
import numpy as np
from capri_mod.model import CAPRIModel
from capri_mod.io_results import Experiment

m = CAPRIModel(data_dir="capri_data", verbose=False)
regions = list(m.data["areas"].index[:30])     # >=30 for representative results
rng = np.random.default_rng(0)

exp = Experiment("sensitivity_biofuel", description="mandate x wheat shock", model=m)

for i in range(200):
    mandate = float(rng.uniform(0.03, 0.20))
    shock   = float(rng.uniform(-0.30, 0.30))
    r = m.run(scenario="BASELINE", regions=regions,
              run_biofuel=True, biofuel_mandate=mandate,
              world_price_shock={"SWHE": shock})
    exp.save_run(r, run_id=f"run_{i:04d}",
                 inputs={"biofuel_mandate": mandate, "wheat_shock": shock})

table = exp.finalise()   # writes outputs/sensitivity_biofuel/batch_summary.csv
```

`batch_summary.csv` has the sampled inputs as `in_*` columns and every output
indicator beside them — ready for any SA library. Re-read it later with
`load_experiment("outputs/sensitivity_biofuel")` without re-running the model.

## 4. Plugging into a sensitivity library (SALib example)

For a variance-based (Sobol) or Morris analysis, sample the inputs, run the model,
and save every run — so the outputs are on disk, not just in memory.

```python
import numpy as np
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol
from capri_mod.model import CAPRIModel
from capri_mod.io_results import Experiment, flatten_outputs

m = CAPRIModel(data_dir="capri_data", verbose=False)
regions = list(m.data["areas"].index[:30])

problem = {
    "num_vars": 2,
    "names": ["biofuel_mandate", "wheat_price_shock"],
    "bounds": [[0.03, 0.20], [-0.30, 0.30]],
}
X = sobol_sample.sample(problem, 256)      # parameter sets to run

exp = Experiment("sobol_biofuel", description="Sobol on mandate x wheat shock", model=m)

Y = []
for i, row in enumerate(X):
    r = m.run(scenario="BASELINE", regions=regions, run_biofuel=True,
              biofuel_mandate=float(row[0]),
              world_price_shock={"SWHE": float(row[1])})
    exp.save_run(r, run_id=f"run_{i:05d}",
                 inputs={"biofuel_mandate": float(row[0]),
                         "wheat_price_shock": float(row[1])})
    Y.append(flatten_outputs(r)["biofuel_bioethanol_kt"])   # chosen response

exp.finalise()                              # writes batch_summary.csv
Si = sobol.analyze(problem, np.array(Y))    # first-order & total indices
print("S1:", Si["S1"], " ST:", Si["ST"])
```

Swap the response (`biofuel_bioethanol_kt`) for any indicator produced by
`flatten_outputs()`, and add levers to `problem` as needed.

**You can also analyse after the fact**, without re-running the model — everything
needed is in `batch_summary.csv`:

```python
from capri_mod.io_results import load_experiment

table = load_experiment("outputs/sobol_biofuel")
table = table[table["market_converged"]]                 # drop non-converged runs
Y = table["biofuel_bioethanol_kt"].to_numpy()
X_cols = ["in_biofuel_mandate", "in_wheat_price_shock"]  # the sampled inputs
```

## 5. Practical notes

- **Use ≥30 regions.** Fewer distorts the EU supply base and the market clearing.
- **Runtime.** A full-region run is ~30 s; a subset is faster. For thousands of
  runs, use a region subset, reduce `market_max_iter`, and/or parallelise
  (each run is independent — the batch loop is embarrassingly parallel).
- **Check convergence.** `market_converged` is saved per run; drop or flag
  non-converged runs before analysing.
- **Reproducibility.** Every run's `summary.json` records the scenario and
  metadata; pass explicit `run_id`s to keep a clean audit trail.
- **Input dimensionality.** Don't try to vary all 177k data points at once —
  choose interpretable levers (Section 1b) or scale whole data groups.

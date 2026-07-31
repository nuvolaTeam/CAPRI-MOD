# CAPRI-Python

An independent Python reimplementation of the economic logic of the **CAPRI**
model (Common Agricultural Policy Regionalised Impact), calibrated and validated
against data extracted from a CAPRI star-3.0 installation.

CAPRI-Python reproduces CAPRI's regional agricultural supply, market, policy,
environmental, feed and biofuel behaviour across **248 NUTS-2 regions (EU27 +
Norway)**, **40 activities** (29 crops, 11 livestock) and **32 market
commodities** — in a few thousand lines of transparent, tested Python rather
than a large GAMS system.

It is **not** a copy, a wrapper, or a release of the CAPRI modelling system. It
is an independent implementation of the same economic methods, built so that
every input is traceable and every scenario result is checkable.

---

## What this model is — and what it is not

CAPRI-Python is a **comparative-static** model. Given a policy or price shock,
it computes how the base-year agricultural economy re-settles into a new
equilibrium. This is a deliberate design choice, and understanding it is
essential to interpreting every result (see
[Differences from CAPRI](#differences-from-capri-and-why-they-are-deliberate)).

The **base year is a parameter, not a fixed assumption.** Inputs are organised
under `capri_data/<base_year>/` and selected via `load_all_data(base_year=...)`,
so the model can be re-based to any year for which CAPRI data has been
extracted. The currently populated and validated base year is **2017**; re-basing
to a newer year requires extracting that year's CAPRI GDX data into a new
`capri_data/<year>/` folder (and, until generalised, updating two hard-coded
`2017/` paths in `capri_python/supply/capri_pmp.py`). Throughout this document,
"2017" refers to the current base year, not a structural limitation.

**It answers:** *"What does this policy, on its own, do to the agricultural
sector?"* — the isolated treatment effect of a policy, uncontaminated by
assumptions about the future.

**It does not answer:** *"What will the sector look like in 2030?"* — that is a
dynamic projection, which requires a baseline trajectory the model deliberately
does not carry.

---

## Status

| Check | Result |
|---|---|
| Data validator | 11 pass, 1 warn, 0 fail |
| Base-year market fidelity | world prices validated against CAPRI `PMRK` |
| Supply convergence | 247 / 248 regions (only Hamburg city-state fails) |
| Test suite | 17 tests, including schema and silent-drop gates |
| Module validation | all 6 modules validated against CAPRI or explicitly bounded |

Reproduce with `python tools/run_tests.py`.

---

## Validation: every module checked against CAPRI's own numbers

The central claim of this project is not that the model runs, but that its
outputs have been **checked against CAPRI's actual data and scenario results**,
module by module. The table below states, for each module, *what* was validated
and *by which method*, so the strength of each claim is explicit.

| Module | Status | How validated |
|---|---|---|
| **Supply — crops** | Validated | Realized own-price elasticities match CAPRI's PELA targets within ~10% |
| **Supply — livestock** | Validated (direction) | Green Deal scenario: reproduces CAPRI's cattle-extensification signal |
| **Policy / CAP** | Validated | Premiums match CAPRI `PRME` exactly; payment mechanism responds by the economically-correct amount |
| **Environment** | Validated | N excretion matches CAPRI `MANN` within ~12%; GHG responds correctly to scenario activity changes |
| **Feed** | Validated (ruminants) | Energy & dry matter match CAPRI within ~10% via IPCC 2006 Eq. 10.6; monogastrics calibrated to CAPRI targets |
| **Market** | Validated | Base prices match CAPRI `PMRK`; scenario supply shocks move prices in CAPRI's direction |
| **Biofuel** | Validated (external) | Output within 10% of observed EU statistics; mandate mechanism linear-consistent |

**Validation methods**, from strongest to supporting:

- **Scenario (method 3):** run the same shock through both models and compare
  responses. Used for supply-livestock, environment (GHG), and market.
- **Coefficient (method 2):** compare our computed value against CAPRI's
  computed value for the same quantity. Used for crops, feed, environment (N),
  CAP mechanism.
- **Input reproduction (method 1):** confirm loaded data matches CAPRI's GDX.
  Used for CAP premiums and throughout the data layer.

### Validation found real bugs — that is the point

Validation was not a formality. **Every single module that was numerically
checked against CAPRI had at least one real bug**, each of which produced
plausible-looking but wrong output until the comparison exposed it:

- crop supply elasticities overshooting their target by 1.6–2.5×
  (calibrated on net revenue where a price shock perturbs gross revenue);
- five separate livestock bugs (herds never reaching the solve, a units error
  making net revenue 1000× too large, feed and grassland constraints zeroing
  all livestock);
- a CAP policy mechanism that silently did nothing (payments keyed by region,
  shocked by instrument name);
- a feed growth-energy term undercounting fattening animals by omitting the
  daily-gain term;
- a market demand calibration that cancelled every supply shock.

All are fixed and documented in `capri_data/DATA_SOURCING_REGISTRY.json`. The
lesson is baked into the test suite: a per-input coverage gate fails loudly if
any declared input silently empties, the failure mode behind several of these
bugs.

---

## Data: real, traceable, and self-protecting

The model's inputs are extracted directly from CAPRI's GDX files — never from
Excel exports, which introduced homoglyph corruption, dropped regional detail,
and silent synthetic fallbacks earlier in development.

- **Provenance is tracked per column, not per file**, in
  `capri_data/DATA_SOURCING_REGISTRY.json` and declared in
  `capri_data/INPUT_SCHEMA.json`. A file-level label once concealed 16 synthetic
  columns inside a file marked real; per-column tracking prevents that.
- **99.4% of live cells are real CAPRI data** (honest per-cell count, not the
  flattering area-weighted figure). The remainder are explicitly labelled —
  non-physical items (cotton, which CAPRI itself carries only as a value, not a
  physical yield), a small number of calibrated cells, and documented gaps.
- **World prices are validated against CAPRI's actual `PMRK`**, correcting nine
  commodities against ground truth — including a long-standing soya error
  (2.85× too high) and cheese, a processed product CAPRI carries no margin for.
- **A declarative schema** (`INPUT_SCHEMA.json`) names every input, its source,
  vintage, and consuming module, and is built to survive a future swap of CAPRI
  GDX inputs for external sources (Eurostat, FADN) as a field edit rather than a
  rewrite.

---

## Architecture

Six modules, each a focused, testable Python component:

```
capri_python/
  supply/         regional PMP supply, 248 NUTS-2 × 40 activities
  market/         Armington market, EU27 bloc × 32 commodities
  policy/         CAP instruments (premiums, coupled/decoupled payments)
  environmental/  nutrient balances, GHG, ammonia, biodiversity indicators
  feed/           animal energy/protein requirements and feed allocation
  biofuel/        biofuel demand and feedstock use
```

The **supply module** uses Positive Mathematical Programming (PMP): a quadratic
cost term is calibrated so the model exactly reproduces the observed 2017
activity levels, then responds to shocks along CAPRI's own supply elasticities.
The **market module** clears EU27 against the rest of the world via an Armington
system with tâtonnement price adjustment.

---

## Differences from CAPRI, and why they are deliberate

CAPRI-Python is not a smaller CAPRI; it is a different tool making different
trade-offs. Each difference below is a considered choice, not a shortfall.

### 1. Comparative-static, not a dynamic projection

**The difference:** CAPRI's published scenarios (e.g. Green Deal 2030) are
dynamic projections — they evolve the whole economy forward from the base year,
compounding baseline yield growth, demand shifts and endogenous technology over
~13 years, *and then* apply policy. CAPRI-Python holds the world at 2017 and
applies only the policy shock.

**Why this is deliberate:** it **isolates the policy effect**. A CAPRI 2030
number blends "what this policy does" with "what 13 years of everything-else
does"; ours reports the first alone. For the question most policy analysis
actually asks — *"what does this policy do?"* — the isolated effect is the
cleaner, more directly useful answer. It also keeps every result traceable to
validated 2017 data, rather than resting on baseline assumptions about a future
that cannot be validated because it has not happened.

**The consequence to understand:** our scenario *magnitudes* are smaller than
CAPRI's projection outputs (e.g. a livestock price rise of a fraction of a
percent where CAPRI 2030 shows tens of percent), because we report the policy
increment without the baseline drift. **The fair comparison is direction and
relative pattern, not absolute level** — and on direction, CAPRI-Python matches
CAPRI.

### 2. EU27 as a single market bloc

**The difference:** the market module treats the EU27 as one Armington bloc
trading against the rest of the world, rather than resolving intra-EU bilateral
trade.

**Why:** it is sufficient for policy questions about EU-vs-world position and
aggregate price formation, and it keeps the market side transparent and fast.
Full bilateral trade is available in the extracted data and can be added if a
use case requires it.

### 3. 248 regions, EU27 + Norway

**The difference:** CAPRI's installation defines 288 NUTS-2 units; CAPRI-Python
covers 248.

**Why:** the 40 not covered are non-EU (Turkey, Western Balkans) and out of
scope by design. Within EU27 + Norway, the two models share essentially the same
NUTS-2 granularity. (CAPRI can further downscale to 1×1 km HSMU units — a
separate spatial layer, not additional economic regions.)

### 4. A few parameters calibrated-to-target rather than first-principles

**The difference:** monogastric (pig/poultry) feed requirements and a small
number of specialty world prices are calibrated to match CAPRI's reported
values rather than derived from CAPRI's underlying formula.

**Why:** where CAPRI's formula and its reported units could not be reconciled
without risk of a compensating error (e.g. monogastric energy is reported per
1000 head for hens but per head for sows), calibrating directly to the validated
target is more honest than shipping an unresolved derivation. These cells are
explicitly labelled *calibrated-to-target* rather than *first-principles*.

---

## Known limitations

Stated plainly, because a defensible model names its limits rather than hiding
them:

- **Scenario magnitudes are policy-increment, not 2030-projection** (see
  difference 1). Compare directions, not levels, against CAPRI's published
  scenarios.
- **Monogastric feed energy and a few specialty world prices are
  calibrated-to-target**, not derived.
- **Biofuel and parts of the market module are validated against external data
  or documented behaviour**, not against a CAPRI scenario run (CAPRI's scenario
  files carry no biofuel variables).
- **One region (Hamburg, DE60) does not converge** — a genuine city-state edge
  case with ~47k ha of farmland, not a systematic failure.
- **The model is comparative-static.** It cannot answer "what will 2030 look
  like." Moving to a dynamic projection would principally require constructing
  and defending a baseline trajectory — a substantial, separate undertaking.

---

## Quick start

```bash
# run the test suite (schema gates, calibration, scenario checks)
python tools/run_tests.py

# validate the data layer
python -c "from capri_python.data.validate_data import validate_data; \
           print(validate_data('capri_data').summary())"

# verify per-cell provenance coverage against the schema
python tools/verify_schema.py
```

Running a scenario (comparative-static) — see
`capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md` for a worked Green
Deal example.

---

## Provenance and reproducibility

- `capri_data/INPUT_SCHEMA.json` — declarative source of truth for every input.
- `capri_data/DATA_SOURCING_REGISTRY.json` — per-dataset provenance, including
  every bug found and fixed during validation.
- `capri_data/validation/` — validation artifacts, including the Green Deal
  comparison (`greendeal_2030/`) and world-price checks against CAPRI `PMRK`.
- `capri_data_snapshot/` — a hashed snapshot of the data layer for verifiable
  restore.

---

## Relationship to CAPRI

CAPRI is developed by the CAPRI Network (see capri-model.org). CAPRI-Python is an
independent reimplementation of its economic methods for research and policy
analysis, calibrated against a CAPRI star-3.0 installation. It reuses CAPRI's
*methods and calibration data*, not its code. Any errors in this
reimplementation are its own and should not be attributed to CAPRI.

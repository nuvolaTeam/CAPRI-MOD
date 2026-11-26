[![Docker](https://github.com/nuvolaTeam/CAPRI-MOD/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/nuvolaTeam/CAPRI-MOD/actions/workflows/docker-publish.yml)
[![Python application](https://github.com/nuvolaTeam/CAPRI-MOD/actions/workflows/python-app.yml/badge.svg)](https://github.com/nuvolaTeam/CAPRI-MOD/actions/workflows/python-app.yml)
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/capri-mod-logo-white.png">
    <img src="docs/assets/capri-mod-logo.png" alt="CAPRI-mod logo" width="480">
  </picture>
</p>

# CAPRI-mod

**An AI-assisted Python reimplementation of the economic logic of the CAPRI model** (Common Agricultural Policy
Regionalised Impact).

CAPRI-mod reproduces CAPRI's regional agricultural supply, market, policy, environmental, feed and biofuel behaviour
across **CAPRI's 250 regional units** (EU27, Norway, the UK, Turkey and the Western Balkans), **49 activities** (37
crops, 12 livestock), **58 market commodities** and **CAPRI's 45 market regions**. Every input is traceable to a
source. Each module's output has been compared with CAPRI's own data or scenario results; §2 and
[docs/FITNESS_FOR_USE.md](docs/FITNESS_FOR_USE.md) say which outputs hold up and which do not.

Each equation cites the CAPRI code it follows and each departure is registered. The code is open Python on CSV inputs,
which carry their provenance and CAPRI's own codes. Every run's settings, result quality and decisions are recorded in
machine-readable form.

The project tests whether a large policy model, CAPRI in this case, can be reimplemented in a form that is
transparent, reusable, reproducible, interoperable and AI-ready (§9). It is a feasibility test and an independent
implementation of CAPRI's *methods and calibration data*, not a copy of its code.

---

## Table of contents

1. [Overview](#1-overview)
2. [The Green Deal and Farm-to-Fork runs against CAPRI](#2-the-green-deal-and-farm-to-fork-runs-against-capri)
3. [Installation & quick start](#3-installation--quick-start)
4. [The data layer](#4-the-data-layer)
5. [Model architecture](#5-model-architecture)
6. [Solvers and our choices](#6-solvers-and-our-choices)
7. [Baselines, scenarios and runs](#7-baselines-scenarios-and-runs)
8. [Validation](#8-validation)
9. [AI readiness, APIs and MCP](#9-ai-readiness-apis-and-mcp)
10. [Differences from CAPRI](#10-differences-from-capri)
11. [Known limitations](#11-known-limitations)
12. [Provenance, relationship to CAPRI, licence](#12-provenance-relationship-to-capri-licence)

---

## 1. Overview

CAPRI-mod is a **partial-equilibrium model of EU agriculture, comparative static per simulation year, with an
optional multi-year projection layer**. Given a policy or price shock, it computes how the agricultural economy of
the simulation year re-settles: how farmers reallocate land and herds, how markets clear, and what the environmental
consequences are.

**It answers:** *"What does this policy, on its own, do to the agricultural sector?"*

- **Separated from baseline drift.** A scenario is solved for the same year as its baseline and from the same
  starting point. In the standard runs both are solved for 2030 on CAPRI's own 2030 baseline, so the change reported
  is the policy's alone; the drift to 2030 is CAPRI's baseline, not the model's.
- **Separated from economy-wide feedbacks.** Labour, capital and GDP effects lie outside the partial-equilibrium
  boundary, the boundary CAPRI draws too. CAPRI reaches economy-wide effects by linking to an external CGE (GTAP, its
  `capri_gtap` and `cgemrk` modules); that link is not implemented here.
- **Not insulated from world markets.** The market carries CAPRI's 45 market regions with Armington substitution, so an
  EU policy moves world prices, which feed back into EU supply. Leakage is modelled, not excluded.

**Caveats.** Nearly all the validation sits on the comparative-static 2030 runs (§2). The projection has been checked
for a single step to 2030 against CAPRI's own 2030 reference (correlation +0.993, total cropped area within 3%, 20 of
23 crops within 25%). Multi-period recursion runs but has no external check: only perennial crop areas are carried
between periods. The trajectory is exogenous, adopted from CAPRI's baseline; CAPRI's own documentation describes
baseline construction as a mix of trend analysis, model runs and expert consultation.

> **Before using a number from this model, read [docs/FITNESS_FOR_USE.md](docs/FITNESS_FOR_USE.md).** Several
> reported fields are sound and several are not, and without a CAPRI installation you have no independent way to
> tell which is which.

**The base year is a parameter.** Inputs are organised under `capri_data/<base_year>/`; the only populated base year
is **2017**, CAPRI star 3.0's. A base year without a data folder stops with an error. Re-basing needs CAPRI's data
steps (COCO, CAPREG, the market database) for the new year, from a newer CAPRI release or from their port in the data
pipeline (`capri_mod/pipeline`).

**What you need.** No CAPRI installation, no GAMS licence and no proprietary solver: the calibrated data ship with
the repository. Re-deriving the validation, or rebuilding the data from CAPRI's exports, needs CAPRI's files
(`docs/EXTERNAL_SOURCES.md`). Positive Mathematical Programming and Armington trade are used without derivation; the
equation book (`docs/equations/`) sets CAPRI's GAMS equations beside their Python form.

### At a glance

| | |
|---|---|
| Regions | CAPRI's 250 regional units (EU27 215, Norway 6, the UK, Turkey and the Western Balkans 29), CAPRI's 8-character codes |
| Activities | 49 (37 crops, 12 livestock) |
| Market commodities | 58 |
| Base year | 2017 (parameterised); scenarios solved in 2030 on CAPRI star 3.0's Green Deal baseline |
| Supply | CAPRI's regional models as non-linear programs with CAPRI's 2030 PMP terms |
| Market | CAPRI's market model as ported, in CAPRI's 45 market regions (the EU as its two blocks): bilateral Armington trade, tariffs, TRQs, entry prices, GL demand, processing, dairy, biofuels, feed bulks, young animals, non-EU land markets |
| Data validator | 934 declared data files (CSV inputs, Parquet sources), 0 violations |
| Test suite | 719 tests, 111 of them slow; the last full run (25 November 2026, 680 tests, one test file per process): 677 passed, 2 skipped, 1 xpassed |
| Full-EU 2030 runs | 4 to 8 minutes per supply-market iteration on 2 cores (Green Deal, 24 November 2026: 12 iterations in 73 minutes), plus about 50 minutes once per new baseline for the market supply Hessian |
| Solvers | IPOPT (CasADi) for the supply models and the manure pool market; the market's fixed point or the whole-market chain (Newton with MKL PARDISO, a continuation, IPOPT); Clarabel (the manure pools' alternative form), HiGHS (linear side problems) (§6) |

---

## 2. The Green Deal and Farm-to-Fork runs against CAPRI

Three CAPRI references, kept apart by whether they are like for like:

| Reference | CAPRI release | Like for like? | Compared by |
|---|---|---|---|
| CAPRI's Green Deal 2030 step against its reference (`greendeal_scenarios.gms`: lnds8 org18 pest20 mine13crp surp30), run by the project lead | star 3.0, base 2017, as the model | yes: same release, baseline and switches | `tools/check/compare_capri_gd.py` on `capri_data/validation/greendeal_2030/capri_gd_effect.csv` (`tools/build/extract_capri_gd_pair.py`) |
| CAPRI's published Farm-to-Fork results (JRC121368) | CAPRI 2020, base 2012, baseline on the OECD-FAO Outlook 2017-2026 | no: another release and baseline | `tools/check/compare_runs.py --capri` |
| CAPRI's 2030 run without voluntary coupled support | star 3.0 | yes | `tools/run/run_vcs_2030.py` on `capri_data/validation/coupled_support_2030/` |

CAPRI's results are used to check, not to tune: no parameter is fitted to them.

### 2.1 Running the pair

```shell
# the Green Deal 2030 step on CAPRI's Green Deal baseline, at the settings of the comparison runs
python tools/run/run_f2f_2030.py runs/gd.pkl --scenario greendeal2030 --settings capri_mod/settings/capri_comparison.toml
python tools/check/compare_capri_gd.py runs/gd.pkl --ms        # EU27 and member states against CAPRI's step
# Farm-to-Fork 2030 with JRC121368's settings (tiered surplus target with its 36% cap, no manure trade, genomics 0.2)
python tools/run/run_f2f_2030.py runs/f2f.pkl --scenario f2f
python tools/check/compare_runs.py runs/f2f.pkl --capri         # the 20 indicators against JRC121368
```

`capri_mod/settings/capri_comparison.toml` runs two of CAPRI's code errors that the model fixes by default as CAPRI
codes them, and values each crop's plant protection in the Green Deal step as CAPRI's step does
(docs/DEPARTURES_FROM_CAPRI.md). A comparison with CAPRI's run then shows the port, not the fixes. On the full-EU
Green Deal run of 19 November 2026, these settings against the defaults gave EU producer prices' mean gap to CAPRI 1.2
against 1.6 points, and member states' activities 4.6 against 5.2. The Farm-to-Fork comparison runs at the defaults:
whether CAPRI's 2020 release had those two errors cannot be checked.

### 2.2 The Green Deal 2030 step against CAPRI star 3.0

The latest full-EU standing check: 23 November 2026 (dev 9867411), `capri_comparison.toml`, 221 units (EU27 and
Norway, the default until 24 November). It converged under CAPRI's stop rule in 29 iterations, with every regional
solve optimal, in 5,856 s on 2 cores (the market supply Hessian from the cache). Run e5aef880da34 (reference
69c929bd1b57) is stored on Hugging Face (nuvolaTeam/capri-mod-results).

**Activities** (EU27, % change from the baseline): mean absolute gap 1.0 points over the 35 activities compared, the
same sign for 91%; the member states' median gaps 1.02 points on average.

| Activity | CAPRI | CAPRI-mod | | Activity | CAPRI | CAPRI-mod |
|---|---:|---:|---|---|---:|---:|
| Soft wheat | −1.9 | −1.8 | | Fallow | +90.9 | +89.0 |
| Durum wheat | −15.3 | −16.8 | | Voluntary set-aside | +79.5 | +75.2 |
| Grain maize | −10.0 | −8.7 | | Extensive grassland | +51.8 | +47.5 |
| Rye | −11.9 | −11.4 | | Intensive grassland | −54.8 | −50.7 |
| Pulses | −0.8 | −3.4 | | Dairy cows | −1.6 | −1.5 |
| Rapeseed | −3.4 | −3.4 | | Suckler cows | −28.8 | −27.8 |
| Fodder maize | +17.3 | +16.1 | | Fattening pigs | −9.2 | −8.6 |
| Other fodder | −28.9 | −29.2 | | Broilers | −8.1 | −7.5 |

**Producer prices** (EU27, % change; CAPRI's member-state market prices weighted by production): mean absolute gap 0.6
points over 23 products; model / CAPRI median ratio 0.97.

| Product | CAPRI | CAPRI-mod | | Product | CAPRI | CAPRI-mod |
|---|---:|---:|---|---|---:|---:|
| Soft wheat | +8.8 | +9.6 | | Beef | +20.0 | +18.2 |
| Barley | +10.8 | +11.5 | | Pork | +12.7 | +11.6 |
| Rye | +14.7 | +15.2 | | Poultry | +13.3 | +12.6 |
| Rapeseed | +8.4 | +8.0 | | Milk | +11.2 | +10.5 |
| Pulses | +2.1 | +2.8 | | Soy cake | −2.5 | −2.3 |

The gap narrowed as CAPRI's form was ported: the activities' mean gap was 3.7 points on 14 November and 3.3 on 15
November (at the defaults), 1.0 on 23 November (at the comparison settings; CHANGELOG.md).

**What remains open:** the dual of the Green Deal's nitrogen target is 0.856 of CAPRI's at the median over 215 units
(FR52 4.90 against 6.20 EUR per kg N, PL52 2.03 against 2.89). CAPRI's dual is recovered from its own results'
marginal terms (reports/margcr.gms; `tools/build/extract_capri_marginal_terms.py`). The grassland split (intensive
−50.7% against −54.8%) goes with it.

**The market alone.** Fed CAPRI's own Green Deal supply, feed demand and supply-side prices
(`tools/check/check_capri_gd_market.py`), the model's market gives the EU's price changes within a median 0.08 points
of CAPRI's (95% within 0.64): beef in EU West +21.1% against +21.7%, pork +12.8 against +12.9, soy cake imports −12.5
against −12.4. At CAPRI's calibration point (CAPRI's dump of its market model) 2,160 prices are within 1.5e-4 and
16,728 trade flows within 1e-3. The market's equations and data reproduce CAPRI's response, so a remaining price gap
comes from what the supply side passes to it.

**The non-EU supply countries.** With CAPRI's supply models for the UK, Turkey and the Western Balkans (the default
since 24 November 2026, 250 units), a Green Deal run capped at 24 iterations brings their activity changes to within
a mean 0.47 points of CAPRI's for Turkey, 1.04 for the UK and 0.67 for the Western Balkans (1.36, 3.64 and 1.63
without their models). The EU27's activity changes moved by at most 0.13 points, its prices' by 0.17.

### 2.3 Farm-to-Fork 2030 against JRC121368

The latest full run at the defaults: 14 November 2026 (dev ffb8a0b), converged in 14 iterations, 4,222 s on 2 cores,
no regional solve non-optimal at the end. Cereal and oilseed price indices are weighted by base production value; EU
prices are the EU's producer prices.

| 2030 Farm-to-Fork, % change | CAPRI-mod | CAPRI (JRC121368) |
|---|---|---|
| Cereal / oilseed / vegetables-and-permanent-crops price | +12.5 / +15.7 / +13.2 | +8.2 / +11.2 / +15.0 |
| Beef / pork / poultry / milk price | +31.4 / +21.2 / +21.9 / +22.4 | +24.1 / +43.0 / +18.0 / +1.1 |
| Dairy cows / beef animals / pigs / poultry / sheep and goats | −3.2 / −20.3 / −13.5 / −10.6 / −10.0 | −10.1 / −17.7 / −14.3 / −16.2 / −9.4 |
| Cereal / oilseed / vegetables-and-permanent-crops production | −16.3 / −12.2 / −13.0 | −15.0 / −15.4 / −12.0 |
| Beef production | −14.4 | −14.2 |
| N surplus / fertiliser N₂O | −32.8 / −40.4 | −33.5 / −40.4 |
| Enteric / manure CH₄ / non-CO₂ GHG | −11.6 / −12.3 / −19.0 | −14.6 / −12.2 / −14.8 |
| Ammonia / manure N₂O | −37.7 / −18.1 | −33.0 / −3.2 |
| Utilised agricultural area | +3.2 | +3.0 |

Mean absolute deviation over the 20 indicators (the table without ammonia, manure N₂O, beef production and the area):
**4.74** points. Against JRC121368's Table 17 the run adopts nitrification inhibitors on 16.5% (CAPRI 18%), precision
farming 25.2% (35%), covered storage 27.0% (34%), low-emission housing 19.1% (12%), air purification 7.9% (10%).

**Since then** (21 November 2026, dev 6eff275, at the settings of `capri_comparison.toml` as at that commit): the
animals' ammonia options hold their initial shares unless the scenario's endogenous-technology switch is on, as in
CAPRI, and JRC121368's switch (ghgTechAmmEndog 1) now reaches every regional model. The mean deviation is 6.45
points: beef price +38.5% (JRC121368 +24.1), pork +30.3 (+43.0), poultry +28.3 (+18.0), milk +26.6 (+1.1), dairy cows
−3.9 (−10.1), N surplus −34.9 (−33.5), ammonia −42.6 (−33.0); covered storage 30.0% (34), air purification 10.0 (10).
The two runs differ in their settings and in 59 inputs, and the changes are not separated. A Farm-to-Fork run at the
defaults on the current code is the next one due.

**Not like for like.** JRC121368 used CAPRI 2020 (base 2012, milk-yield genomics on); the model is built on star 3.0
(base 2017). The largest gaps are the milk price (+22% against +1%), the pork price (+21% against +43%) and the dairy
herd. The model's dairy block carries CAPRI's own parameters (docs/DAIRY_PROCESSING.md); tracing the milk price needs
CAPRI's own Farm-to-Fork results for the dairy chain (`capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md`).
The like-for-like checks are the Green Deal above and the baseline: crop levels per regional unit within a median
0.22% of CAPRI's Green Deal baseline (95% within 1.5%; `tools/check/compare_baseline_capri.py`).

### 2.4 How the instruments are represented

- **Organic target**: the distance from the existing organic area to the target (CAPRI's `0.25 - 0.10`), with FADN
  yield gaps by macro-region and crop, applied in full as in the mode JRC121368 used.
- **Pesticides**: plant-protection expenditure cut, other input costs raised and a yield loss, on the conventional area.
- **Landscape features**: a set-aside floor by member state, kept where it cannot fit, as CAPRI keeps it
  (`e_setaLandscape`); the solver's last point is recorded in the run's `nlp_fallback`.
- **Nutrient target**: a hard limit on the full gross N balance inside the regional models (`SURTOT_REST_`). In the
  Green Deal step it is CAPRI's surpRedu setting. In the Farm-to-Fork run it is JRC121368's tiered schedule (25% of the
  first 50 kg N/ha of surplus, 50% of 50-100, 75% of 100-150, 100% above), with the EU average cut of 36% in the nine
  regions where the tiered cut was infeasible. CAPRI's fertiliser and ammonia options, intensity variants and per-crop
  mineral caps meet it (docs/FERTILISER_ALLOCATION.md, docs/MITIGATION_IN_SUPPLY.md).
- **Land**: CAPRI's land market with its quadratic land terms and calibration rents; land is conserved across all
  arable activities, so a floor displaces crops (docs/LAND_USE_FLEXIBILITY.md).
- **Manure trade**: CAPRI's `manureTradeNew` pool market, on in the Green Deal runs, off in JRC121368's
  (docs/MANURE_MARKET.md). Young cattle clear EU-wide markets as in CAPRI (docs/YOUNG_ANIMALS.md).
- **CAPRI's switchboard**: `greendeal_scenario(lndscpTarg=..., orgTarg=..., pestRedu=..., surpRedu=...)` takes CAPRI's
  settings in CAPRI's units and refuses the options not implemented (`capri_mod/policy/greendeal.py`).

**Run comparisons to convergence.** A single supply-market pass suppresses the price feedback: it moved the
Farm-to-Fork cereal decline by 4 points. An unconverged run raises a `RuntimeWarning` and sets
`metadata["outer_converged"] = False`.

---

## 3. Installation & quick start

Python 3.11 or later (the settings are read with tomllib; the tests are run on 3.13):

```shell
pip install -r requirements.txt        # the model, tests, data pipeline and reference tools
python tools/run/run_tests.py
```

`requirements.txt` holds the model, the tests (pytest, pytest-xdist, coverage), the data pipeline and the
reference-building tools; the same sets are the `dev`, `pipeline` and `tools` extras of `pyproject.toml`. The
reference builders read GDX files through the open-source GDX library (MIT, no GAMS licence), built once:

```shell
git clone https://github.com/GAMS-dev/gdx.git && cd gdx    # built here from commit 9e2a8c8
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DNO_TESTS=ON -DNO_EXAMPLES=ON && cmake --build build --target gdxcclib64
export CAPRI_GDXLIB=$PWD/build                              # or --gdxlib DIR, or capri_sources/gdxlib
```

Or in a container (Debian bookworm, `Dockerfile`):

```shell
docker build -t capri-mod .
docker run --rm capri-mod                                        # the test suite
docker run --rm -v "$PWD/runs:/runs" capri-mod python tools/run/run_f2f_2030.py /runs/f2f.pkl
```

**Running.** The runners (`tools/run/`) fix Python's string-hash seed themselves (without it two runs of one scenario
can differ by about 0.2%); a script of your own that calls `CAPRIModel` should do the same (the first lines of
`tools/run/run_f2f_2030.py`). Nothing is read from the environment: the regional solves' worker processes are a
setting (`--set run.n_workers=2`; 0 every core), which does not change results. A run prints CAPRI's run log
(`run.verbosity`: quiet, capri, detailed, solver, debug) and writes it beside its output, with the step report per
iteration as CSV.

```python
from capri_mod.data.validate_data import validate
from capri_mod.model import CAPRIModel

assert validate(".", verbose=True) == []         # the data against their declarations (DuckDB)
model = CAPRIModel(data_dir="capri_data")
results = model.run(scenario="BASELINE", regions=["DE110000", "FR610000"])   # CAPRI's unit codes
print(results["metadata"])
```

**Parameters.** Every constant the economics and accounting rest on (CAPRI's parameters, IPCC factors as CAPRI uses
them, JRC121368's assumptions) is a row of `capri_data/codes/model_parameters.csv` (value, unit, kind, source,
module), read through `capri_mod/params.py`.

---

## 4. The data layer

```
capri_data/
├── 2017/            the base year: supply/, market/, policy/, environment/, feed/, abatement/ (one per module)
├── baselines/       a baseline's data per base and simulation year (capri_greendeal_ref/1730: CAPRI's 2030
│                    Green Deal baseline)
├── codes/           CAPRI's codes and the model's: regional units, activities, market regions, NUTS crosswalks,
│                    model_parameters.csv, results_items.csv
├── scenarios/       references, trajectories and scenarios as folders (settings.toml + CSV tables)
├── sources/         the builders' material as Parquet (raw/: CAPRI's and others' files one to one; intermediate/);
│                    the model reads nothing here
├── pipeline/        the data pipeline's tables (CAPTRD-MOD's inputs and results)
├── validation/      CAPRI references for checks only (2030 reference, Green Deal pair, coupled support pair)
└── schema/          the declarations of every data file (DuckDB SQL), their provenance, the numbers in the code,
                     schema.json (the same, generated)
```

- **No synthetic data reaches the model**: a missing file or region raises, and a
  test checks that every region with a herd or crops has CAPRI's coefficients.
- **Every data file is declared and its provenance traced.** `capri_data/schema/*.sql` declares each CSV's types, key,
  code lists, ranges and units; `tools/check/validate_data.py` enforces them. `01_provenance.sql`, generated from the
  pipeline's trace (`tools/check/make_provenance.py`), gives each file its nature (CAPRI, publication, external,
  mixed), origins and builder. Of the non-zero cells in the files the model's code names, 99.7% are in files of CAPRI
  origin (2,568,824 of 2,575,938; `tools/check/verify_schema.py`).
- **The numbers held in the code** are listed (`03_code_data.sql`, generated) and classified by where each comes from
  (`04_code_data_status.sql`: a CAPRI gms line, a publication, a unit conversion, a numerical setting).
- **Inputs come from CAPRI's GDX files**, never from Excel exports. CAPRI's raw files are published, converted value for
  value to Parquet, on Hugging Face (nuvolaTeam/capri-mod-raw); `docs/EXTERNAL_SOURCES.md` lists them.

**Rebuilding.** The data are rebuilt with doit (`dodo.py`): each of the 146 builder
invocations is a task with the files it reads and writes, as traced (`tools/pipeline/builders.json`). The rebuild from
blank (`tools/check/rebuild_from_blank.py`) reproduces 380 of the 381 builder-written files byte for byte; the one
difference is a CAPTRD trajectory file the default runs do not use (`capri_data/scenarios/captrd_2030/regional.csv`).

```shell
python -m doit list                          # the tasks
python -m doit                               # bring the data up to date, then check them
python -m capri_mod.data.validate_data       # the declarations' checks
```

---

## 5. Model architecture

<p align="center">
  <img src="docs/architecture.png" alt="CAPRI-mod architecture: data, calibration and scenarios; the supply-market loop; post-equilibrium outputs; projection and tools" width="100%">
</p>

`CAPRIModel.run()` (`capri_mod/model.py`) runs a scenario as CAPRI's CAPMOD does. The baseline is solved first, or
taken from the cache when the same baseline (data, settings, technology switches) was solved before; then the
scenario. Each is a loop: the regional supply models solve (in parallel, warm-started); their production and feed
demand go to the market; the market clears; CAPRI's price forecast (the weighted average of the last steps' prices)
goes back to supply. The young-animal markets, the manure pools, CAPRI's premium cut and the N-balance prices settle
inside the same loop. It stops on CAPRI's stop rule (no more than two items changing by more than 0.05%), at most 99
iterations (CAPRI's %STEPS%). The market is calibrated once per run at CAPRI's 2030 market data, as CAPRI's
`cal_cnst_terms`; the market supply functions' Hessian is measured once per baseline, as CAPRI's
`calibrate_supply.gms`, and cached.

| Module | Lines | What it holds |
|---|---:|---|
| `supply/` | 17,800 | CAPRI's regional model per unit as an NLP, PMP with CAPRI's 2030 terms, land market, feeding, fertilisation and mitigation options inside it |
| `market/` | 13,000 | CAPRI's market model: two-nest Armington trade with CAPRI's policy regimes, GL demand, processing, crushing, dairy, biofuels, feed bulks, young animals, non-EU land |
| `coupling/` | 2,700 | the supply-market exchange: market supply functions and their Hessian, the manure pool market, the stop rule |
| `policy/` | 5,700 | CAPRI's premium modules (CAP 2014-2020 schemes, rural development, the premium cut), Green Deal settings, tariffs |
| `environmental/` | 2,700 | CAPRI's nutrient balances (N, P2O5), its N loss chain, IPCC emission accounting as CAPRI's |
| `feed/` | 8,600 | CAPRI's requirements and rations, its requirement functions and its baseline feed calibration (being ported) |
| `fert/` | 800 | CAPRI's inner fertiliser distribution and nutrient need (fert/fertned.gms) |
| `projection/` | 3,000 | the baseline of a simulation year; the multi-year loop |
| `pipeline/` | 12,000 | the data pipeline and CAPTRD-MOD, CAPRI's trend projection |

The model's code (without tests) is about 74,000 lines of Python. Two reports read the solved regions outside the
run: irrigation water requirement (`capri_mod/water`) and farm income (`capri_mod/income`); results on NUTS 2024
regions: `capri_mod/nuts_reporting`. Welfare follows CAPRI's reports/welfare.gms (docs/WELFARE.md).

**What is CAPRI's method, not a simplification of it:** PMP supply over CAPRI's regional unit × activity structure
with CAPRI's own 2030 terms (`supply.pmp_source = "capri2030"`; the option `"recipe"` builds them with CAPRI's
define_pmp_terms.gms); the Armington market; CAPRI's premiums; CAPRI's requirement rows (`REQSE_`, `REQSN_`,
`MAXSHR_`), the rations chosen in the same optimisation as the herds; CAPRI's `MANN` and IPCC factors as CAPRI uses
them; CAPRI's mitigation options as columns of the supply models with CAPRI's costs and calibration, and its emission
tax inside the same optimisation (`capri_mod/supply/ghg_tax.py`). The supply model's port is mapped in
docs/SUPPLY_MODEL_MAP.md; the market's blocks are described in docs/ARMINGTON_MARKET.md and the files beside it.

**Documentation.** `docs/` holds one file per block (market, supply, feed, fertiliser, manure, environment, scenarios,
welfare), the departure registers (`DEPARTURES_FROM_CAPRI.md`, `CAPRI_DEPARTURES_REGISTER.md`) and the equation book
(`docs/equations/`), the settings with CAPRI's equivalents (`docs/SETTINGS_INVENTORY.md`) and the known issues
(`docs/KNOWN_ISSUES.md`); `CHANGELOG.md` the record of changes. The development notes are kept in a private repository.

---

## 6. Solvers and our choices

CAPRI solves its supply models, market and manure trade with CONOPT in GAMS. CAPRI-mod has no GAMS licence and uses
open solvers. Its NLPs are built in CasADi, which gives them exact first and second derivatives by automatic
differentiation.

| Problem | CAPRI | CAPRI-mod |
|---|---|---|
| Regional supply models (feeding, fertilisation, options; non-convex) | CONOPT | IPOPT, warm-started; a failed solve keeps its last point, as CAPRI keeps a non-optimal one |
| Market (trade, quotas, processing, dairy, biofuels, feed, young animals) | CONOPT | a fixed point, Newton per commodity with Anderson acceleration (default); or the whole system: Newton (MKL PARDISO), a continuation on the quotas' slope, IPOPT |
| Market with CAPRI's bounds (option `market.bounds = "capri"`) | CONOPT, `widen_bounds.gms`, fudge equations | the fixed point, then a semismooth Newton on the bounded system as a mixed complementarity problem |
| Market supply response | supply models re-solved at price shocks | the same: 52 price shocks of 1%, each re-solving the 250 units (2,934 s), cached per baseline |
| Manure trade between pools (`m_mPoolMarket`) | CONOPT | IPOPT; Clarabel for the alternative schedules form |
| CAPTRD's trend estimation | an NLP in GAMS (`m_trendMS`) | IPOPT (CAPTRD-MOD) |
| Small side problems (target fits, the accounts' fertiliser allocation, least squares) | inside CAPRI's models | HiGHS, a tailored Newton, SciPy |

**The regional supply models: IPOPT on CAPRI's own NLP.** The models are non-convex: feed per head times herd size is
bilinear, and the fertiliser allocation and the ammonia losses are non-linear. They are solved as NLPs in CAPRI's
equations; a convex reformulation was tried and dropped, since it was a different, approximate model. IPOPT, like
CONOPT, finds a local optimum; neither guarantees a global one. Our settings (`capri_mod/settings/defaults.toml`,
`[supply]`):

- **Tolerance 1e-10.** The optimum is flat along small, nearly substitutable crops (rye, oats, durum wheat). At 1e-8
  the same baseline solved twice gave levels 3e-5 apart; at 1e-10 1.1e-6, with 5% more iterations and the same run time.
- **Warm starts** from the previous primal-dual point, with the barrier parameter at 1e-6 and the bound pushes at 1e-9,
  so a solve starts where the previous one ended, as CONOPT restarts from its last solution.
- **Linear solver: MUMPS** (bundled with CasADi). SPRAL and HSL's MA27, MA57, MA86 and MA97 are settings; the HSL
  library stays outside the repository, under the user's own licence, as CAPRI's users hold CONOPT's. Measured on the
  regional solves of a mini-EU run (853 solves, 239-521 columns): SPRAL on two OpenMP threads took 1.06 times its
  single-thread time per solve (median), because the systems are too small to share. Parallelism goes across regions
  instead: the 250 independent solves of a pass run in worker processes (fork; on Windows one process).
- **Fallbacks, recorded.** Where a solve fails, the run's fallbacks are tried (JRC121368's relaxed N cut where the
  tiered target is infeasible, relaxed mineral caps), each recorded in the run's metadata (`nlp_fallback`, the solves'
  status as CAPRI's `p_INFES`).

**The market: a system of equations, not an optimisation.** By default each commodity's prices take Newton steps on
its exact derivatives, accelerated by Anderson mixing across commodities. As an option (`market.solver = "chain"`),
the whole market is one system in CAPRI's form: 3,166 unknowns, 2,624 once the empty
balances are removed, 2,621 of which form one strongly connected block, so the market has to be solved at once.
The chain tries Newton, then a continuation on the quotas' sigmoid slope (CAPRI's own way in `trim_trqs.gms`), then
IPOPT. Newton's linear solver was chosen on one factorisation of the market's Jacobian at a solve of a mini-EU run,
and the methods compared on seven supply shocks from CAPRI's base market:

| Linear solver: one factorisation (10,409 rows, 288,023 non-zeros) | Time |
|---|---|
| Intel MKL PARDISO (`pypardiso`) | 1.16 s |
| MUMPS | 4.05 s |
| SciPy SuperLU | 9.13 s |

| Method | Seven shocks (soft wheat ±, milk, beef, cereals, pork, a Farm-to-Fork-like shock) |
|---|---|
| The fixed point (default) | converged on all, 17-26 s |
| Newton (PARDISO, line search) | converged on four, 8-31 s; stalls on three (the quotas' sigmoids) |
| The chain (Newton, continuation, IPOPT) | converged on all, 9-55 s |
| IPOPT (MUMPS) alone | converged on all, 65-206 s; with HSL's MA97, MA57 or MA27 slower than with MUMPS (three shocks) |

Every method that converged gave the fixed point's prices within 2.5e-8. The fixed point stays the default until the
chain's full-run comparison; PARDISO is optional (Intel's free licence), MUMPS taking its place when it is missing.

**The manure pool market** is CAPRI's `m_mPoolMarket` as CAPRI writes it, solved with IPOPT ("using nlp maximizing
v_mPoolBenefits"). Its alternative form, the regions' trade schedules, is convex with many constraints; an active-set
method failed on the full EU, so it goes to Clarabel, an interior-point conic solver.

**Where our choice differs from CAPRI's, and why.** We think open solvers are the better choice for this project: the
model runs anywhere without a licence, and the derivatives are exact. The cost is that results agree with CONOPT's
only to the tolerance of a local optimum: where an optimum is flat, two solvers can stop at different points of it,
which is why the tolerance above is tight. No comparison with CONOPT on the same problem has been made.
`run.verbosity = "solver"` shows IPOPT's iteration log per regional model, as CAPRI's GUI shows GAMS's output.

---

## 7. Baselines, scenarios and runs

**The baseline** is the calibrated equilibrium of the year a scenario is solved in. For 2030 it is CAPRI star 3.0's
Green Deal baseline (res_2_1730greendeal_refdefaulta: levels, yields and land types per region). The supply models
are calibrated to it as CAPMOD calibrates them to a simulation year; the market at CAPRI's 2030 market data. Three
trajectories ship as scenario folders (`capri_data/scenarios/`): `capri_ref_2030` (the default), `captrd_2030`
(CAPRI's trend results) and `null` (no drift).

**Scenarios are data.** A scenario is a folder, `capri_data/scenarios/<name>/settings.toml`, naming its reference and
giving its switches and shocks, with CSV tables beside it (`coupled_support.csv`, `premium_factors.csv`,
`tariff_changes.csv`, `trq_volume_changes.csv`). As CAPRI's scenario files include their reference, a scenario takes
its reference's settings unless it gives its own.

```shell
python -m capri_mod.scenarios list                                   # references, groups, scenarios
python -m capri_mod.scenarios new carbon_tax_80 --reference ref_star3 --dir ~/my_scenarios
# edit ~/my_scenarios/carbon_tax_80/settings.toml: under [scenario.shocks], carbon_tax = 80.0
python -m capri_mod.scenarios check carbon_tax_80 --dir ~/my_scenarios   # every error with its key, no run
python tools/run/run_f2f_2030.py out.pkl --scenario carbon_tax_80 --scenarios-dir ~/my_scenarios
```

In Python:

```python
from capri_mod.policy.greendeal import farm_to_fork_scenario, greendeal_2030_scenario
base = model.run(scenario="BASELINE")
scen = model.run(custom_scenario=greendeal_2030_scenario())
delta = model.compare(base, scen)                         # activity, price and welfare changes
model.run(scenario="BASELINE", world_price_shock={"SWHE": 0.10})   # +10% world wheat price
model.run(scenario="CARBON_TAX_50")    # CAPRI's emission tax (pol_input/ecampa/carbtax50_endotech_set12.gms)
```

Key `run()` arguments: `scenario`, `custom_scenario` (a `PolicyScenario`), `world_price_shock`, `carbon_price`,
`biofuel_markets` (CAPRI's `BIOF_M`), `biofuel_output_scale`, `regions`, `max_outer_iter` (99), `run_environmental`.
Arguments left at None take the run's settings.

**Settings.** Every switch, tolerance, iteration limit and algorithm choice is in `capri_mod/settings/defaults.toml`,
each commented with what it does and CAPRI's equivalent; `docs/SETTINGS_INVENTORY.md` lists them with their
homes. A run writes its effective settings (`OUT.settings.toml`) and a run manifest (`OUT.manifest.json`: the commit,
the software versions, every input file read with its SHA-256).

```python
from capri_mod import settings
s = settings.load(["my_run.toml"], overrides={"supply.pmp_source": "recipe"})   # validated: unknown keys stop
settings.activate(s)
with settings.override({"market.biofuel_markets": False}):    # temporarily, restored on exit
    model.run(...)
```

**The results store.** `tools/run/run_f2f_2030.py` writes each run to `results/` as a Delta Lake table in CAPRI's
DATAOUT layout (region, dim5, cols, rows, year, value), under a run id (the SHA-256 of its results and definition) and
a result name as CAPRI names its result files (`res_2_1730<short name>[_<n>u][_<label>]`). `results/RUNS.csv` lists
every run with its status as CAPRI's p_INFES and META would (`tools/check/list_runs.py`).

```python
from deltalake import DeltaTable
t = DeltaTable("results/long").to_pandas(filters=[("scenario", "=", "farm_to_fork_jrc121368")])
```

**Browsing.** `python capri_gradio/results_browser.py` opens a local, read-only page over one or more stores: runs with
their convergence and settings, a scenario against its baseline as pivot tables and charts, the baseline against
CAPRI's 2030 reference, the Farm-to-Fork against JRC121368, a Green Deal run against CAPRI's (EU27, member states,
regional maps). `python capri_gradio/capri_gui.py` adds a scenario form, a Run tab and an assistant (§9.4).

**The projection layer.** `ProjectionModule(model, traj).run(policy_scenario=..., years=[2030])` solves each year
twice, baseline and scenario, so the policy increment stays apart from baseline drift. The 2030 step is the one with
an external reference; herds are re-optimised each period rather than carried, so multi-period livestock paths are
not meaningful.

---

## 8. Validation

**Methods.** *Scenario*, the strongest: the same shock through both models (§2: the Green Deal step, the coupled
support pair; JRC121368 as a published reference). *Coefficient*: the model's computed value against CAPRI's for the
same quantity (crops, feed, N balance, premiums). *Input reproduction*: loaded data against CAPRI's GDX (premiums, the
data layer).

| Module | How validated |
|---|---|
| Supply, crops | CAPRI's 2030 PMP terms; baseline crop levels within a median 0.22% of CAPRI's baseline; Green Deal activity changes within a mean 1.0 points of CAPRI's step (§2.2) |
| Supply, livestock | Green Deal: suckler cows −27.8% against −28.8%, pigs −8.6% against −9.2%; Farm-to-Fork dairy cows −3% against JRC121368's −10% |
| Policy, payments | premiums equal CAPRI's `PRME`; the 2030 premiums from the ported premium modules (`capri_mod/policy/premiums.py`) |
| Environment | gross N balance on CAPRI's definition (`e_SURTOTHa`), EU items against CAPRI's 2030 reference within 1-7 kg N/ha, regional surplus correlation 0.92; P2O5 balance (docs/P_BALANCE.md) regional correlation 0.99 |
| Feed | CAPRI's requirement rows at CAPRI's base rations; the requirements equal the base rations' supply by construction, no independent check |
| Market | at CAPRI's calibration point prices within 1.5e-4, trade within 1e-3; CAPRI's own Green Deal supply gives its price changes within a median 0.08 points |
| Biofuel | the feedstock CES reproduces CAPRI's 2030 BiofFeedCost in every market region; the biofuel markets reproduce its 2030 output and use |
| Emission tax | CAPRI's ghgTax inside the supply models; no CAPRI tax result in hand to compare with (docs/MITIGATION_IN_SUPPLY.md) |

The 2030 baseline is also checked against the EU agricultural outlook (docs/OUTLOOK_2030_CHECK.md,
`tools/check/compare_outlook_2030.py`). The regression anchors (`capri_data/validation/REGRESSION_ANCHORS.json`,
`tools/check/check_regression.py`) fail when a result moves.

**Fitness for use** — which outputs are sound, which are not, and the reading hazards — is in
[docs/FITNESS_FOR_USE.md](docs/FITNESS_FOR_USE.md), and in machine-readable form in `capri_data/FITNESS_FOR_USE.json`:

```python
from capri_mod.fitness import check, caveats
check("supply.gross_margin").ok                       # True
caveats(["scenario.oilseeds", "activities.WINE"])     # what to report alongside
```

Statuses are `validated`, `use_with_care`, `overstated`, `understated` and `not_supported`; an unrecorded key returns
`unknown`, which means no finding is recorded, not that the output is validated.

---

## 9. AI readiness, APIs and MCP

The question this chapter answers: can CAPRI's methods live in a form that others reuse, reproduce and work on with AI
tools, without losing the traceability to CAPRI? "AI-ready" means usable by two kinds of tool: agents that read, run
and change the code (the model was itself written with an AI coding assistant, under the author's direction and
review), and statistical or machine-learning methods that learn from its inputs or outputs.

### 9.1 Reusability and reproducibility

- **Open and self-contained.** AGPL-3.0, Python, open solvers; no GAMS licence; the calibrated data ship with the code.
- **Parts that work alone.** `SupplyModule` (and each region's `CapriRegionalNLP`, solvable from its own
  specification), `MarketModule` and `EnvironmentalModule` are separate classes; `CAPRIModel` couples them as CAPRI
  does. The coupling is tight by design, so a module alone loses the others' feedbacks.
- **Same inputs, settings and code, same results.** The runners fix the hash seed; every run writes its effective
  settings and the SHA-256 of every input it read; caches are keyed by what they depend on (the market supply Hessian
  by the baseline's solution and the settings that change it); every refactor must reproduce the reference runs.

### 9.2 What a machine can read

- **Declared inputs**: every input a CSV declared in DuckDB SQL (`capri_data/schema`, as JSON in `schema.json`).
- **One settings file**: `capri_mod/settings/defaults.toml`, read through one validated interface;
  `docs/SETTINGS_INVENTORY.csv` lists each setting with CAPRI's equivalent and whether the default is CAPRI's.
- **CAPRI's vocabulary**: `capri_mod/data/capri_symbol_dictionary.json` describes 2,429 symbols of CAPRI's GAMS code.
  The code cites the CAPRI file and lines each equation follows, and the equation functions quote CAPRI's GAMS
  verbatim (`tools/refactor/check_gams_quotes.py` checks the quotes against CAPRI's code).
- **Results that state their quality**: `capri_data/FITNESS_FOR_USE.json`; each run's metadata (convergence, CAPRI's
  stop-rule verdict, the solves that fell back, where the market Hessian came from). A script can reject an unusable
  run instead of reporting it.
- **Registers with stable identifiers**: `docs/CAPRI_DEPARTURES_REGISTER.md` (FIX, KEPT, DEP and BEYOND numbers),
  `docs/DEPARTURES_FROM_CAPRI.md`, `CHANGELOG.md`.
- **Batch outputs for learning methods**: `capri_mod.io_results.Experiment` writes one table of inputs and outputs
  across runs (`batch_summary.csv`), the form an emulator is trained on.

### 9.3 APIs

| Interface | What it gives | Where |
|---|---|---|
| Python API | `CAPRIModel.run`, `compare`, `list_scenarios`; `settings.load/override`; `fitness.check`; `io_results.load_run`, `Experiment` | `capri_mod/` |
| Command line | the runners, the scenario tool (`python -m capri_mod.scenarios list/new/check`), the checks | `tools/run/`, `tools/check/` |
| Results store | Delta Lake tables in CAPRI's DATAOUT layout, read by `deltalake`, polars or DuckDB; the run catalogue as CSV | `results/`, `capri_mod/io_results.py` |
| Data | the declared CSV inputs; CAPRI's raw files as Parquet on Hugging Face (nuvolaTeam/capri-mod-raw); stored runs (nuvolaTeam/capri-mod-results) | `capri_data/`, `docs/EXTERNAL_SOURCES.md` |
| Language models | the GUI's assistant calls any server with the OpenAI chat-completions API and tool calls (hosted providers, local servers, Hugging Face's Inference Providers router) or the Anthropic Messages API with tool use | `capri_gradio/assistant_llm.py` |
| Web | the GUI and results browser (Gradio), also on a Hugging Face Space | `capri_gradio/`, `capri_gradio/SPACE.md` |

There is no network service of the model itself: tools reach it through Python and the command line.

### 9.4 The assistant's tools, and MCP

The GUI's assistant does not touch files, code or the model. It answers with tool calls, which
`capri_gradio/scenario_tools.py` validates against the scenario definition (`capri_mod/scenarios/definition.py`,
pydantic) and the settings, then executes locally. The model's tools are `list_scenarios`, `describe_scenario`,
`make_scenario`, `list_settings`, `list_runs` and `run_summary`, each with a JSON input schema. Only the conversation
and the tools' small results leave the machine. A run is started by the user, never by the language model.

**MCP (Model Context Protocol).** No MCP server ships yet. The tool layer has the shape MCP expects (named tools with
JSON schemas and checked execution), so exposing it as an MCP server would let any MCP client (a desktop assistant, an
IDE agent) list scenarios, write checked scenario folders and read run summaries under the same checks, without the
GUI. This is a proposal, not done. (In the market code, "MCP" means something else: the mixed complementarity form of
the bounded market, §6.)

### 9.5 Rules for AI-assisted changes

- Each equation follows CAPRI's code and documentation, with the GAMS quoted. Where the model departs from CAPRI, the
  departure is registered, explained and switchable back to CAPRI's behaviour; the author decides each one.
- No proxies, synthetic data or hard-coded values unless necessary, and then listed.
- Claims are checked against runs, not asserted. AI tools make mistakes like any developer: a coding error once made
  a full run proceed without CAPRI's market supply function, behind a warning the run script hid (CHANGELOG.md). It
  was found from the run's metadata; such failures are now recorded and tested for.

**Machine learning inside the model:** none. Supply, market and environment come from CAPRI's optimisation and
equilibrium equations. It is considered only for the statistical trends of CAPTRD-MOD, and only if it beats CAPRI's
own estimator in back-casting.

### 9.6 Limits

- **Run time**: 4 to 8 minutes per supply-market iteration on 2 cores, plus about 50 minutes per new baseline for the
  market Hessian. Large ensembles, and emulators trained on them, are expensive.
- **Pickles**: full runs are saved as Python pickles, not a stable exchange format; the results store and
  `Experiment` write tables.
- **The orchestration is still large**: much of the loop is in `capri_mod/model.py`; splitting it is under way.
- **Convergence must be checked**: a tool must read `outer_converged` and `capri_stop` before using a result.

---

## 10. Differences from CAPRI

Three kinds of difference, kept apart:

- **Scope.** The base-year mode and the projection layer; CAPRI's regional units of EU27, Norway and the non-EU supply
  countries; not CAPRI's farm types, grid or recursive-dynamic mode (RECDYN).
- **Corrections of CAPRI's code**, where its effect contradicts CAPRI's own data or stated intent, each with a switch
  back to CAPRI's behaviour (`capri_mod/settings/capri_comparison.toml` sets the ones the comparison runs need).
- **Departures to be switched to CAPRI's setting**, kept for a practical reason recorded at the time
  (docs/DEPARTURES_FROM_CAPRI.md).

The complete index of every departure and of every error found in CAPRI's code, fixed or kept as coded, with its
CAPRI reference, setting and status, is docs/CAPRI_DEPARTURES_REGISTER.md. The corrections that act in the scenarios:

| What | CAPRI's code | CAPRI-mod default | Switch to CAPRI |
|---|---|---|---|
| Anaerobic digestion on dairy cows' manure CH4 | no CH4 effect for dairy cows (envind/ad_data_and_cali.gms l. 588) | the CH4 factor as for the other animals | `environment.ad_dairy_ch4 = "capri"` |
| Low-emission manure application in the leaching share | adds the options' term (supply_model.gms l. 3413), so adoption lowers leaching against CAPRI's own data | subtracted, as the runoff equation does | `environment.ammapp_sign = "capri"` |
| Input-saving progress under the Green Deal's input changes | the change replaces the 2017-2030 progress: inputs 7% too high in 2030 | the change times the progress | `supply.greendeal_inputs_keep_tech_change = false` |
| Organic crops' fuel top-up | valued at the other-inputs price, not the fuel's | valued at the crop's fuel cost | `supply.organic_topup_at_fuel_cost = false` |

They leave the base unchanged. Four more act only in CAPTRD-MOD (listed in the register).

**The EU as CAPRI's two market regions.** EU_WEST and EU_EAST trade bilaterally with each other and the other
regions; trade between member states inside a block is not resolved, as in CAPRI. Member states keep their own raw milk
prices through the dairy block.

**CAPRI's regional units.** 250 units under CAPRI's 8-character codes (`capri_data/codes/regional_units.csv`), each with
its own CAPRI data, following CAPRI's NUTS vintages; Denmark, Estonia, Lithuania, Latvia, Slovenia, Cyprus, Malta and
Croatia are one unit each. The UK, Turkey and the Western Balkans have their supply models in the run by default since
24 November 2026, as in CAPRI's 2030 Green Deal runs (`run.supply_countries_outside_eu`). Results on NUTS 2024 are a
reporting step (`capri_mod/nuts_reporting.to_nuts2024`), not regional detail of their own.

**The market's bounds.** CAPRI's bounds on the market's variables and their widening are ported as an option
(`market.bounds = "capri"`); the default is still the model's own floors until a full-run comparison.

---

## 11. Known limitations

**Open differences from CAPRI's results**, each with the file where it is checked:

- The Green Deal's N-surplus dual at 0.856 of CAPRI's (§2.2; `tools/build/extract_capri_marginal_terms.py`).
- Farm-to-Fork's milk and pork prices against JRC121368 (§2.3; CAPRI's Farm-to-Fork dairy results are asked for,
  `capri_data/validation/HOW_TO_RUN_A_VALIDATION_SCENARIO.md`).
- The reported income is CAPRI's activity-based income at the solution (`capri_mod/income`, register DEP-54) with its
  producer surplus (DEP-55), its gross account by item (EAAG, DEP-56) and the premium outlays per product and budget
  (FEOGA's FEOP, DEP-57), but CAPRI's other animals (OANI) have no level in the model (KNOWN_ISSUES K207: 3.4% of the
  mini-EU baseline's income) and the straw is valued at zero on both sides; the accounts at producer and basic prices
  (EAAP, EAAB) are to be ported.
- The feed chain of the simulation year (CAPRI's baseline feed calibration and its 2030 rations) is being ported
  (`capri_mod/feed/chain.py`); the 2030 rations are CAPRI's solved reference's until then.
- The figures of §2 predate the latest changes (the 250 units, CAPRI's 2030 livestock outputs per head); they are to be
  refreshed from the next converged full-EU pair.

**Reading results:**

- Compare production with CAPRI's published production, not areas.
- Filter near-zero base cells before reading percentage changes: a base of zero gives meaningless percentages.
- Check `metadata["outer_converged"]` before using a result.
- Biofuels and parts of the market are checked against CAPRI's reference data, not against a CAPRI scenario run.

**Scope boundaries, by design:** CAPRI's regional units, not farm types or a grid (downscaling needs FADN and
land-cover data); partial equilibrium, as CAPRI, without its GTAP link; farm income per region, not its distribution;
water demand and biodiversity pressure reported, their outcomes not modelled.

---

## 12. Provenance, relationship to CAPRI, licence

- `capri_data/schema/`: the declarations of every data file with their provenance and checked notes, the numbers held
  in the code, `schema.json`; the files' vintages in `05_file_catalogue.sql`.
- `capri_data/validation/`: the CAPRI references used for checks (`greendeal_2030/`, `coupled_support_2030/`,
  `farm_to_fork_2030/`), `VALIDATION.md`, `REGRESSION_ANCHORS.json`.
- `tools/check/check_doc_coverage.py`: fails if a recorded data decision is not in the user-facing documentation;
  `tools/check/verify_schema.py`, `tools/run/run_tests.py`: the coverage and test gates.
- `tools/build/build_capri_base.py`: rebuilds every region's base data from CAPRI's dumps, the mappings declared in
  one place.

**Relationship to CAPRI.** CAPRI is developed by the CAPRI Network (capri-model.org). CAPRI-mod is an independent
reimplementation of its economic methods for research and policy analysis, calibrated against a CAPRI star 3.0
installation. It reuses CAPRI's *methods and calibration data*, not its code. Any errors in this reimplementation are
its own and should not be attributed to CAPRI. CAPRI itself is available from the
[CAPRI network](https://www.capri-model.org).

**Licence.** CAPRI-mod is free software under the [GNU Affero General Public License, version 3](LICENSE)
(AGPL-3.0-only); under its section 13, a modified version offered to users over a network (the Gradio interface, a
hosted Space) must offer them its source. It is distributed WITHOUT ANY WARRANTY; see the licence. Third-party
packages keep their own licences (e.g. Clarabel, Apache-2.0).

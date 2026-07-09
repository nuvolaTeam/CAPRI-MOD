# CAPRI-Python

A Python reimplementation of the core of the **CAPRI** model (Common Agricultural
Policy Regionalised Impact) — a large agro-economic model used for EU agricultural
and environmental policy analysis.

CAPRI-Python reproduces CAPRI's two-tier structure: a **regional supply** side
(Positive Mathematical Programming over 248 EU NUTS-2 regions) linked to a **global
market** (Armington trade across 29 world regions) that clears by iteration. It
covers 29 crop and 11 animal activities and 32 traded commodities, with six modules:
supply, market, policy, environment, feed, and biofuel.

> **Status: research reimplementation, not an official CAPRI product.**
> This is an independent Python port. It is not affiliated with or endorsed by the
> CAPRI network or EuroCARE. See *Validation status* below for exactly what has and
> has not been verified — please read it before using results.

---

## Validation status (read this first)

CAPRI-Python is **honest about what it is**. Here is the precise state:

| What | Status |
|---|---|
| Base-year prices vs CAPRI's own values | ✅ **Exact** — 12/12 commodities at 0% deviation; market converges |
| Input data | ✅ **Real CAPRI/FAO throughout** (all synthetic inputs replaced) |
| Supply behaviour under shocks | ✅ Correct signs; elasticities near CAPRI's PELA targets; no blow-ups |
| Cross-price substitution | ✅ Correct (a crop price rise pulls land from competitors) |
| All six modules run end to end | ✅ Yes (~35 s full run) |
| **Scenario magnitudes vs real CAPRI** | ❌ **NOT validated** — see below |

**The one limitation that matters:** the model reproduces CAPRI's 2017 base year
exactly and responds to shocks in the right *direction* and roughly the right
*magnitude*, but it has **not** been validated against real CAPRI *scenario outputs*.
Whether it matches CAPRI's magnitudes for a given policy shock (e.g. how far a tariff
change moves prices) is unconfirmed, because that requires CAPRI's own before/after
results, which were not available during development. A validation harness
(`scenario_validation.py`) is built and ready for those numbers.

**Data provenance:** all inputs are now real CAPRI or FAO data. The last two synthetic
inputs (`feed_requirements`, `nutrient_coefs`) were replaced with data extracted from
CAPRI's capreg results (the `DATA2` cube: N/P₂O₅/K₂O fertiliser rates and per-head feed
requirements). Pig and poultry feed use CAPRI's per-head data with the correct poultry unit
convention (million-head basis). The validator confirms 0 synthetic datasets.

In short: a **well-built, fully data-faithful reimplementation with an exact base year,
100% real inputs, and plausible behaviour — not a certified drop-in replacement for
CAPRI (scenario magnitudes remain unvalidated).**

---

## Install

```bash
git clone https://github.com/USERNAME/capri-python.git
cd capri-python
pip install -r requirements.txt        # or: pip install -e .
```

Requires Python ≥ 3.9 and numpy / pandas / scipy.

## Quick start

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

print(results["market"].world_prices)
print(results["supply"]["DE11"].activities)
```

> **Use a representative region sample (≥30 regions).** A handful of regions gives an
> unrepresentative EU supply base and distorts the market calibration. This caused
> apparent price gaps during development that vanished at 30+ regions.

## Validate the data before trusting a run

```bash
python capri_python/data/validate_data.py capri_data
```

Checks file presence, shape, **vintage consistency** (catches mixing 2017/2021 data),
economic sanity, and flags the synthetic inputs.

---

## Modules

| Module | What it does |
|---|---|
| **supply** | Regional PMP: activity levels respond to prices under land & policy constraints |
| **market** | Armington global trade; iterative price clearing; recalibrated so the base is an equilibrium |
| **policy** | CAP direct payments, tariffs, market policy |
| **environment** | GHG (IPCC factors), nitrogen balance, land use |
| **feed** | Feed demand from animal numbers and requirements |
| **biofuel** | Bioethanol/biodiesel from mandates; feedstock demand feeds back to crops |

## Data

- **Base year:** 2017 (quantities, prices, PMP parameters).
- **Trade:** refreshed to 2021 (bilateral flows).
- Live inputs sit at the root of `capri_data/`; provenance extracts in `sources/`;
  superseded files in `archive/`; a 2021 vintage in `fao_2021/`.
- **`MANIFEST.json`** catalogs every live file (source, vintage, units, shape).
- **`DATA_SOURCING_REGISTRY.json`** records each dataset's nature (real CAPRI / real
  FAO / synthetic) and where a better version comes from.

Data provenance is documented honestly: 21 datasets are real CAPRI, 4 are real FAO,
and all synthetic inputs have been replaced with real capreg data.

## Repository layout

```
capri_python/          the model package
  supply/ market/ policy/ environmental/ feed/ biofuel/
  data/                loaders, definitions, validator, sourcing tools
  tests/               test suite + scenario-validation harness
capri_data/            input data (see Data section)
docs/                  extended documentation
```

---

## Limitations & differences from CAPRI

- **Scenario magnitudes not validated** against real CAPRI outputs (the key gap).
- **Solve architecture:** CAPRI solves supply + market as one simultaneous system;
  this uses an outer loop. Results agree at the base; large shocks may differ slightly.
- **Scope:** 32 of CAPRI's ~50 market commodities; no CAPDIS 1×1 km spatial downscaling.
- **Biofuel coefficients** are reality-calibrated (standard agronomic yields tuned to
  observed EU output), not extracted from CAPRI's AGLINK data.
- **Feed requirements** for all animals (incl. pigs/poultry) and all fertiliser data
  are extracted from CAPRI capreg results; feed converted fresh→DM using CAPRI's own per-region dry-matter content (see capreg_extracts/FEED_CONVERSION_NOTES.md).

## Contributing

Issues and pull requests welcome. The highest-value contribution would be **real CAPRI
scenario results** (before/after areas and prices for a policy shock, or a table from a
published CAPRI study) to complete the quantitative validation — see
`scenario_validation.py`.

## License

**GPL-3.0-or-later** — see [LICENSE](LICENSE). This matches CAPRI's own licensing.

## Acknowledgements

Built on data and methodology from the CAPRI model (EuroCARE / Bonn University) and
FAOSTAT. CAPRI-Python is an independent reimplementation and is not an official CAPRI
release.

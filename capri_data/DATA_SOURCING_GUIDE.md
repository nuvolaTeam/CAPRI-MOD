# CAPRI-Python — Data Sourcing Guide

**The single answer to: "which data, which vintage, is it real, and where do I get a better version."**

This guide plus two machine files (`DATA_SOURCING_REGISTRY.json`, `MANIFEST.json`)
and the validator (`validate_data.py`) together resolve the three data questions:
*is it consistent, is any of it synthetic, and where does the best updated set come from.*

---

## 1. The honest current state (run `validate_data.py` to reproduce)

| Nature | Count | Meaning |
|---|---|---|
| REAL_CAPRI | 21 | CAPRI's own numbers (GAMS/GDX/COCO) |
| REAL_FAO | 4 | FAO SUA / trade / balances |
| SYNTHETIC_FALLBACK | **2** | **generated in code — no real file present** |
| Reality-calibrated (in code) | 2 groups | biofuel coeffs, environmental proxies |

**Base year: 2017** for the calibrated core (quantities, prices, PMP terms).
**Trade flows: 2021** (separable, safely refreshed).

---

## 2. The two pieces of LIVE SYNTHETIC data (replace these first)

These have no real file, so `loaders.py` generates them with random noise. They do
**not** affect base-year price validation (market-side), but they do affect the
**feed constraint** and **environmental nitrogen** outputs.

| Dataset | Feeds | Real source to get | Where |
|---|---|---|---|
| `feed_requirements.csv` | supply feed constraint | CAPRI feed intake per head (`p_feedInput` / feedDistribution) | `<capri>/results/` feed GDX |
| `nutrient_coefs.csv` | environmental N-balance, supply nutrient use | CAPRI N/P₂O₅/K₂O application rates (`p_cropNutrient` / NPKtoActivity) | CAPRI envind / capreg results |

Until replaced, treat feed and environmental *magnitudes* as indicative, not validated.

---

## 3. Vintage map — what year each thing is, and the best update

### The clean single-file upgrade (covers many at once)
A newer **CAPRI `fao_agg` GDX** (`fao_agg_19` / `fao_agg_21`) from
`<capri>/results/global/` contains prices + balances + demand elasticities together,
mutually consistent. Exporting it to CSV/XLSX (as done for the 2017 file) updates:
`producer_prices`, `world_prices`, `fao_market_baseline`, `fao_demand_own_elas_eu`.

### Quantities
`base_areas`, `yields`, `animal_numbers`, `land_availability`, `coco_feed_availability`
→ newer **COCO** from `<capri>/results/capreg/`.

### The hard group — PMP terms & elasticities (2017)
`input_requirements`, `pmp_diagonal_terms`, `pmp_crossgroup_terms`,
`pmp_own_price_elasticities`, `supply_elasticities_regional`
→ these are **estimation outputs**. A new base needs them **re-estimated** by
running CAPRI's PMP/PELA estimation for that year — a CAPRI-side task. Reusing 2017
PMP terms with newer prices/quantities is the vintage-mixing the validator now blocks.

### Already current / static
`trade_flows` (2021, done). `gascoeff_params` (IPCC 2006 — update to IPCC 2019 if desired).
`climate_zones` (static).

---

## 4. Where updated data comes from — and the honest caveat about "not in CAPRI folders"

Your instinct is right: **the best data is not always in the CAPRI results folders.**
Three tiers, most-authoritative first:

1. **CAPRI's own results** (`<capri>/results/{global,capreg,...}`) — best for
   consistency, because prices/quantities/PMP were estimated *together*. This is where
   `fao_agg` and COCO live.
2. **Public FAOSTAT** (fao.org/faostat) — best for *currency* (data to 2023/24) and for
   things CAPRI hasn't re-based yet: producer prices, commodity balances, bilateral trade.
   Caveat: FAOSTAT is USD and uses its own item codes (duplicate milk codes 2848/2948!),
   so it needs careful mapping — and mixing its recent prices with a 2017 base breaks
   consistency (the validator will warn).
3. **CAPRI network / JRC / published studies** — for scenario reference outputs (the
   thing needed for behavioural validation) and for methodology. Not raw input data.

**Rule of thumb the validator enforces:** a *full* re-base must move prices + quantities
+ PMP terms to the **same year, from CAPRI's own estimation**. Piecemeal updates from
mixed sources/years are exactly what corrupts the calibration.

---

## 5. How the three tools work together

- **`DATA_SOURCING_REGISTRY.json`** — machine-readable: every dataset's nature, vintage,
  and best real source. The source of truth for this guide.
- **`MANIFEST.json`** — every live file's units, domain, shape.
- **`validate_data.py`** — run it anytime, or `load_all_data(validate=True)`. It checks
  presence, shape, **vintage consistency**, economic sanity, and now **flags live
  synthetic data**. It will not let a vintage-mix or a silent synthetic dataset pass
  unnoticed.

Run `python capri_python/data/validate_data.py capri_data` before trusting any run
after a data change.

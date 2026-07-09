# Contributing to CAPRI-Python

Thanks for your interest. This is a research reimplementation of the CAPRI model,
and contributions that improve its fidelity, coverage, or usability are welcome.

## The single highest-value contribution

**Real CAPRI scenario results** for quantitative validation. The model reproduces
CAPRI's base year exactly but has *not* been validated against CAPRI's scenario
*magnitudes*. If you have access to CAPRI and can export before/after results (areas
and prices for a few commodities under a policy shock), or can point to a published
CAPRI study with a results table, that would let us complete the validation. The
harness is ready in `capri_python/tests/scenario_validation.py`.

## Other valuable contributions

- **Real data for the two synthetic inputs** (`feed_requirements`, `nutrient_coefs`) in
  the correct form — per-head feed intake and N/P₂O₅/K₂O application rates. See
  `capri_data/DATA_SOURCING_REGISTRY.json` for what's needed.
- **A newer base year**, which requires CAPRI's re-estimated PMP parameters (a
  CAPRI-side computation) plus newer COCO quantities and `fao_agg` prices.
- **Wider commodity coverage** (the model covers 32 of CAPRI's ~50 market commodities).
- Bug fixes, tests, and documentation.

## Development setup

```bash
git clone https://github.com/USERNAME/capri-python.git
cd capri-python
pip install -e ".[dev]"
pytest capri_python/tests/ -v
```

## Ground rules

- **Never mix data vintages** without updating the manifest. The validator
  (`capri_python/data/validate_data.py`) enforces vintage consistency; run it before
  submitting data changes.
- **Flag synthetic or calibrated data** honestly in
  `DATA_SOURCING_REGISTRY.json`. The project's credibility rests on not passing off
  approximations as CAPRI's own numbers.
- **Keep the base-year test green** (`test_base_year_market_fidelity`) — 12/12 at 0%
  is the calibration anchor.
- Add a test for any behavioural change.

## License

By contributing you agree that your contributions are licensed under GPL-3.0-or-later.

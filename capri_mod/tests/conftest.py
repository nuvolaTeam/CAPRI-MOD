"""Setups shared by several test modules, built once per test process (pytest-xdist: once per worker) and handed to
each module as a copy, so a module cannot change another's starting point:

- base_market: the market module built from the model's data (MarketModule(load_all_data)), not solved;
- solved_market: the market module of a model after one baseline iteration on DE110000 and FR100000 without the
  market supply functions (market.market_supply_nq off: no Hessian to measure), the state the CasADi block tests
  evaluate their functions at.

Before 13 November 2026 each module built its own (about 100 s each on the CI runner).

The marker no_market_hessian (pyproject.toml) runs a test with market.market_supply_nq off: for a test whose claim is
about a regional-model mechanism (a constraint binds, a column calibrated at base, an account), the market supply
Hessian a baseline measures is machinery the claim does not need, and it was most of such a test's time on the CI
runner (each region set measured its own; the cache key holds the supply code's fingerprint). The market still
clears; the young-animal markets then take the model's own price update (coupling/young_animals.py)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "capri_data"

NO_HESSIAN = {"market.market_supply_nq": False}


@pytest.fixture(autouse=True)
def _no_market_hessian(request, monkeypatch):
    if request.node.get_closest_marker("no_market_hessian") is not None:
        from capri_mod import settings as S
        monkeypatch.setattr(S, "_ACTIVE", S.current().replace(NO_HESSIAN))


@pytest.fixture(scope="session")
def _base_market_once():
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    return MarketModule(load_all_data(DATA_DIR))


@pytest.fixture(scope="module")
def base_market(_base_market_once):
    return copy.deepcopy(_base_market_once)


@pytest.fixture(scope="session")
def _solved_market_once():
    from capri_mod.model import CAPRIModel
    from capri_mod.settings import override
    with override({"market.market_supply_nq": False}):
        m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
        m.run(scenario="BASELINE", regions=["DE110000", "FR100000"], max_outer_iter=1)
    return m.market_module


@pytest.fixture(scope="module")
def solved_market(_solved_market_once):
    return copy.deepcopy(_solved_market_once)

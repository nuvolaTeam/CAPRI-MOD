"""The market's data adapter: the only code of the market package that reads files (docs/design/ARCHITECTURE_REFACTOR.md,
layer "data adapters").

Every input of the market blocks is named here with its location in the data directory:
    <data_dir>/<base_year>/market/<file>   the market's inputs of the base year
    <data_dir>/shared/<file>                cross-vintage mappings (CAPRI's sets)
    <data_dir>/sources/<sub>/<file>         CAPRI exports used as inputs (to be moved to market/, see below)
The data directory and base year are the model's (CAPRIModel(data_dir, base_year)); before 24 October 2026 the blocks
read a fixed capri_data/2017 path next to the package, so another data directory or base year was ignored.

A required file that is missing raises FileNotFoundError naming the file and the builder that writes it. Optional
inputs are marked as such where they are read.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from capri_mod.tableio import read_input

REPO_DATA = Path(__file__).resolve().parents[2] / "capri_data"

#: the builder of each input (tools/build), for the error message of a missing file
BUILDERS = {
    "bilateral_flows_{year}{sfx}.csv": "build_bilateral_market.py",
    "bilateral_regions_{year}{sfx}.csv": "build_bilateral_market.py",
    "armington_rho.csv": "build_bilateral_market.py",
    "biofuel_feedstock.csv": "build_biofuel_market.py",
    "biofuel_use_share.csv": "build_biofuel_market.py",
    "biofuel_market.csv": "build_biofuel_market.py",
    "dairy_processing.csv": "build_dairy_processing.py",
    "dairy_hessian.csv": "build_dairy_processing.py",
    "dairy_eu_balance.csv": "build_dairy_processing.py",
    "dairy_eu_demand_elas.csv": "build_dairy_processing.py",
    "dairy_world_processing.csv": "build_dairy_world_markets.py",
    "dairy_world_hessian.csv": "build_dairy_world_markets.py",
    "dairy_world_demand_elas.csv": "build_dairy_world_markets.py",
    "gl_demand_goods.csv": "build_gl_demand.py",
    "gl_demand_b.csv": "build_gl_demand.py",
    "gl_demand_regions.csv": "build_gl_demand.py",
    "feed_bulks_eu.csv": "build_feed_bulks.py",
    "feed_bulks_eu_share.csv": "build_feed_bulks.py",
    "feed_byproducts.csv": "build_feed_byproducts.py",
    "feed_demand_nonEU.json": "build_feed_demand_nonEU.py",
    "processing_nq_hessian.csv": "build_processing_nq.py",
    "processing_nq_base.csv": "build_processing_nq.py",
    "welfare_base_2030.csv": "build_welfare_base.py",
    "eu_market_supply_nq.csv": "build_eu_market_supply_nq.py",
    "noneu_market_supply_nq.csv": "build_noneu_market_supply_nq.py",
    "crushing_parameters.csv": "build_crushing_parameters.py",
    "supply_elas_region.csv": "build_supply_elas_nonEU.py",
    "eu_ms_balance_2030.csv": "build_eu_ms_balance.py",
    "eu_market_blocks.csv": "(CAPRI's aggregation/defaultA.agg)",
    "rms_to_rm.csv": "build_gl_demand.py",
}


class MarketInputs:
    """Paths and readers of the market's inputs for one data directory and base year."""

    def __init__(self, data_dir: Optional[Path] = None, base_year: str = "2017"):
        self.root = Path(data_dir) if data_dir else REPO_DATA
        self.base_year = str(base_year)

    # -- locations -----------------------------------------------------------------------------------------------
    def path(self, name: str, where: str = "market") -> Path:
        """where: "market" (the base year's market folder), "shared", or "sources/<sub>"."""
        if where == "market":
            return self.root / self.base_year / "market" / name
        if where == "shared":
            return self.root / "shared" / name
        if where.startswith("sources/"):
            return self.root / where / name
        raise ValueError(f"unknown input location {where!r}")

    def exists(self, name: str, where: str = "market") -> bool:
        return self.path(name, where).exists()

    def _require(self, p: Path, name: str) -> None:
        if not p.exists():
            b = next((v for k, v in BUILDERS.items() if k == name or (("{" in k) and name.startswith(k.split("{")[0]))),
                     None)
            raise FileNotFoundError(f"market input {p} is missing" + (f" (written by tools/build/{b})" if b else ""))

    # -- readers -------------------------------------------------------------------------------------------------
    def csv(self, name: str, where: str = "market", required: bool = True, **read_kw) -> Optional[pd.DataFrame]:
        """The table as pandas reads it with read_kw; None for a missing optional input."""
        p = self.path(name, where)
        if not p.exists():
            if required:
                self._require(p, name)
            return None
        return read_input(p, **read_kw)

    def json(self, name: str, where: str = "market", required: bool = True):
        p = self.path(name, where)
        if not p.exists():
            if required:
                self._require(p, name)
            return None
        with open(p) as fh:
            return json.load(fh)

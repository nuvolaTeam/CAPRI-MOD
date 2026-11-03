"""The run's metadata as declared models (refactor stage 5; docs/design/STAGE5_INVENTORY.md §2.3: pydantic for the scenario
definitions and the run metadata, decided 2 November 2026).

The run script (tools/run/run_f2f_2030.py) builds the metadata as a dict, kept in the pickle's "meta"; the long table's
writer (capri_mod/io_results.py write_run) validates it against ResultsMeta before writing meta.json beside the
table. A key the models do not declare, or a value of another type, stops the writing (the pickle is already saved),
so the metadata cannot drift without its declaration changing here. Diagnostic records whose inner structure is the
coupling's own (the stop rule's trace, the jump checks, the price summary) are declared as their containers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HessianRecord(_Strict):
    """One measurement of the market's supply Hessian (capri_mod/coupling/hessian.py; capri_mod/model.py l. 730-736)."""
    source: Literal["cache", "computed", "failed"]
    file: Optional[str] = None
    products: Optional[int] = None
    prices_shocked: Optional[int] = None
    columns_with_response: Optional[int] = None
    seconds: Optional[float] = None
    base_resolve_max_dev_kt: Optional[float] = None
    method: Optional[str] = None
    kkt_ipopt_solves: Optional[int] = None
    regions_skipped: Optional[int] = None
    regions_shocked: Optional[int] = None
    verified: Optional[int] = None
    verify_mismatch: Optional[List[Any]] = None
    at_iteration: Optional[int] = None
    scenario_error: Optional[str] = None
    error: Optional[str] = None


class GitState(_Strict):
    commit: Optional[str] = None
    branch: Optional[str] = None
    data_tree: Optional[str] = None
    changed_files: List[str] = []


class FileHash(_Strict):
    sha256: str
    bytes: int


class RunManifest(_Strict):
    """The code, software and input files of a run (capri_mod/run_manifest.py finish)."""
    created: str
    seconds_recorded: int
    git: GitState
    software: Dict[str, Optional[str]]
    environment: Dict[str, Any]
    command: List[str]
    inputs: Dict[str, FileHash]
    external_inputs: Dict[str, FileHash]


class ResultsMeta(_Strict):
    """The run's metadata (the pickle's "meta"; tools/run/run_f2f_2030.py)."""
    conv: Optional[bool]
    it: Optional[int]
    young_animals: Tuple[Any, Any]
    young_animal_markets: Optional[Dict[str, Any]]
    seconds: int
    options: Dict[str, Any]
    scenario_overrides: Dict[str, Any] = {}
    settings: Dict[str, Dict[str, Any]]
    settings_changed: Dict[str, Any]
    market_supply_hessian: Optional[HessianRecord]
    market_supply_hessian_log: Optional[List[HessianRecord]]
    base_iterations: Optional[int]
    capri_stop: Dict[str, Optional[Dict[str, Any]]]
    nlp_jump_check: Dict[str, Any]
    prices: Optional[Dict[str, Any]]
    nlp_fallback: Dict[str, Dict[str, Any]]
    nor_price_gap: Optional[Any]
    market_calibration_bound_hits: Dict[str, Any]
    pmp_source: Optional[str]
    pmp_capri_parts: Optional[List[str]]
    nlp_relaxed: Dict[str, Any]
    nlp_nonoptimal: Dict[str, List[str]]
    market_converged: Dict[str, bool]
    run_manifest: RunManifest

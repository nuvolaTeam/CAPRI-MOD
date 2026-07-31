"""
Result storage for CAPRI-Python.

The model's run() returns results in memory. This module persists them to a
conventional, git-ignored `outputs/` tree so that runs are reproducible,
auditable, and directly usable for batch / sensitivity analysis.

Layout
------
outputs/                          (git-ignored; created on demand)
  <experiment>/                   a named study, e.g. "sensitivity_biofuel"
    manifest.json                 what/when/model+data version, run count
    runs/
      <run_id>/                   one self-contained model run
        summary.json              scenario, sampled inputs, scalar outputs
        market_world_prices.csv
        market_production.csv
        market_consumption.csv
        market_trade_flows.csv
        supply_activities.csv     region x activity levels
        supply_indicators.csv     region x (gross_margin, ghg, n_balance, ...)
        feed.csv / environmental.csv   (when those modules ran)
    batch_summary.csv             ALL runs, one row each — the analysis table

Typical use
-----------
    exp = Experiment("sensitivity_biofuel")          # -> outputs/sensitivity_biofuel/
    for i, mandate in enumerate(mandates):
        r = model.run(..., biofuel_mandate=mandate)
        exp.save_run(r, run_id=f"run_{i:04d}", inputs={"biofuel_mandate": mandate})
    exp.finalise()                                    # writes batch_summary.csv
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

DEFAULT_OUTPUT_ROOT = "outputs"


# --------------------------------------------------------------------------- #
# Flattening: one run -> one flat record of scalar outputs
# --------------------------------------------------------------------------- #
def flatten_outputs(results: dict) -> dict:
    """Reduce a run to a flat dict of scalar output indicators.

    This is the natural unit for sensitivity analysis: one record per run.
    Keys are prefixed by block, e.g. 'price_SWHE', 'prod_BEEF',
    'biofuel_bioethanol_kt', 'supply_total_gross_margin'.
    """
    out: dict = {}

    mkt = results.get("market")
    if mkt is not None:
        wp = getattr(mkt, "world_prices", None)
        if wp is not None:
            for c, v in dict(wp).items():
                try:
                    out[f"price_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        prod = getattr(mkt, "production", None)
        if prod is not None and hasattr(prod, "items") and not hasattr(prod, "ndim"):
            for c, v in dict(prod).items():
                try:
                    out[f"prod_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        welfare = getattr(mkt, "welfare", None)
        if welfare is not None and not hasattr(welfare, "__len__"):
            try:
                out["market_welfare"] = float(welfare)
            except (TypeError, ValueError):
                pass
        out["market_converged"] = bool(getattr(mkt, "converged", False))
        out["market_iterations"] = int(getattr(mkt, "iterations", 0) or 0)

    bio = results.get("biofuel")
    if bio is not None:
        out["biofuel_bioethanol_kt"] = float(getattr(bio, "bioethanol_kt", 0) or 0)
        out["biofuel_biodiesel_kt"] = float(getattr(bio, "biodiesel_kt", 0) or 0)
        out["biofuel_mandate_share"] = float(getattr(bio, "mandate_share", 0) or 0)

    sup = results.get("supply")
    if isinstance(sup, dict) and sup:
        def _agg(field):
            vals = []
            for r in sup.values():
                v = getattr(r, field, None)
                if v is None:
                    continue
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
            return sum(vals) if vals else None

        for field, name in [("gross_margin", "supply_total_gross_margin"),
                            ("gross_output", "supply_total_gross_output"),
                            ("ghg_emissions", "supply_total_ghg")]:
            v = _agg(field)
            if v is not None:
                out[name] = v
        out["supply_n_regions"] = len(sup)
        out["supply_all_converged"] = all(
            bool(getattr(r, "converged", True)) for r in sup.values()
        )
    return out


# --------------------------------------------------------------------------- #
# Experiment: a named group of runs under outputs/<experiment>/
# --------------------------------------------------------------------------- #
class Experiment:
    """A named group of model runs, stored under outputs/<name>/.

    Parameters
    ----------
    name : str
        Experiment name; becomes the folder under the output root.
    root : str
        Output root (default "outputs", which is git-ignored).
    description : str
        Free text recorded in the experiment manifest.
    """

    def __init__(self, name: str, root: str = DEFAULT_OUTPUT_ROOT,
                 description: str = "", model=None):
        self.name = name
        self.dir = Path(root) / name
        self.runs_dir = self.dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.description = description
        self._records: list[dict] = []

        self.manifest = {
            "experiment": name,
            "description": description,
            "created": datetime.now().isoformat(timespec="seconds"),
            "base_year": getattr(model, "base_year", None) if model else None,
            "n_runs": 0,
        }
        self._write_manifest()

    # -- internals ---------------------------------------------------------- #
    def _write_manifest(self):
        (self.dir / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2, default=str)
        )

    # -- public API --------------------------------------------------------- #
    def save_run(self, results: dict, run_id: Optional[str] = None,
                 inputs: Optional[dict] = None) -> Path:
        """Save one run under runs/<run_id>/ and record it for the batch summary.

        `inputs` should carry the parameter values that produced this run (the
        sensitivity-analysis X); they are stored in summary.json and become
        columns of batch_summary.csv alongside the outputs (the Y).
        """
        run_id = run_id or datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        _write_market(results.get("market"), run_dir)
        _write_supply(results.get("supply"), run_dir)
        for key in ("feed", "environmental", "convergence"):
            v = results.get(key)
            if isinstance(v, pd.DataFrame) and not v.empty:
                v.to_csv(run_dir / f"{key}.csv")

        outputs = flatten_outputs(results)
        summary = {
            "run_id": run_id,
            "scenario": results.get("scenario"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "inputs": inputs or {},
            "metadata": results.get("metadata", {}),
            "outputs": outputs,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

        record = {"run_id": run_id, "scenario": results.get("scenario")}
        record.update({f"in_{k}": v for k, v in (inputs or {}).items()})
        record.update(outputs)
        self._records.append(record)

        self.manifest["n_runs"] = len(self._records)
        self._write_manifest()
        return run_dir

    def finalise(self) -> pd.DataFrame:
        """Write batch_summary.csv (one row per run) and return it.

        This is the table a sensitivity analysis consumes: `in_*` columns are the
        sampled inputs, the rest are output indicators.
        """
        df = self.batch_summary()
        if not df.empty:
            df.to_csv(self.dir / "batch_summary.csv")
        self.manifest["finalised"] = datetime.now().isoformat(timespec="seconds")
        self._write_manifest()
        return df

    def batch_summary(self) -> pd.DataFrame:
        """All runs as one DataFrame (from memory, or re-read from disk)."""
        if self._records:
            return pd.DataFrame(self._records).set_index("run_id")
        return load_experiment(self.dir)


# --------------------------------------------------------------------------- #
# Readers
# --------------------------------------------------------------------------- #
def load_experiment(experiment_dir: str | Path) -> pd.DataFrame:
    """Rebuild an experiment's batch table by reading every run's summary.json."""
    exp = Path(experiment_dir)
    runs = exp / "runs"
    search = runs if runs.exists() else exp
    rows = []
    for sf in sorted(search.glob("*/summary.json")):
        s = json.loads(sf.read_text())
        row = {"run_id": s.get("run_id"), "scenario": s.get("scenario")}
        row.update({f"in_{k}": v for k, v in (s.get("inputs") or {}).items()})
        row.update(s.get("outputs", {}))
        rows.append(row)
    return pd.DataFrame(rows).set_index("run_id") if rows else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Convenience: save a single run without an Experiment
# --------------------------------------------------------------------------- #
def save_results(results: dict, experiment: str = "adhoc",
                 run_id: Optional[str] = None,
                 root: str = DEFAULT_OUTPUT_ROOT,
                 inputs: Optional[dict] = None) -> Path:
    """Save one run to outputs/<experiment>/runs/<run_id>/ (no batch bookkeeping)."""
    exp = Experiment(experiment, root=root)
    return exp.save_run(results, run_id=run_id, inputs=inputs)


# --------------------------------------------------------------------------- #
# Writers for the individual blocks
# --------------------------------------------------------------------------- #
def _write_market(mkt, run_dir: Path):
    if mkt is None:
        return
    for field in ("world_prices", "domestic_prices", "production",
                  "consumption", "net_exports", "trade_flows"):
        val = getattr(mkt, field, None)
        if val is None:
            continue
        try:
            if hasattr(val, "ndim") and val.ndim == 2:
                pd.DataFrame(val).to_csv(run_dir / f"market_{field}.csv")
            else:
                pd.Series(val).to_frame(field).to_csv(run_dir / f"market_{field}.csv")
        except Exception:
            pass


def _write_supply(sup, run_dir: Path):
    """Write region x activity levels, and region x scalar indicators."""
    if not isinstance(sup, dict) or not sup:
        return
    acts = {}
    inds = {}
    for reg, res in sup.items():
        a = getattr(res, "activities", None)
        if a is not None:
            acts[reg] = a
        row = {}
        for f in ("gross_margin", "gross_output", "ghg_emissions", "converged"):
            v = getattr(res, f, None)
            if v is not None and not hasattr(v, "__len__"):
                row[f] = v
        nb = getattr(res, "nutrient_balance", None)
        if isinstance(nb, dict):
            for k, v in nb.items():
                row[f"nutrient_{k}"] = v
        if row:
            inds[reg] = row
    if acts:
        pd.DataFrame(acts).T.to_csv(run_dir / "supply_activities.csv")
    if inds:
        pd.DataFrame(inds).T.to_csv(run_dir / "supply_indicators.csv")

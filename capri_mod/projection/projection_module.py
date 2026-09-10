"""Recursive-dynamic projection — a time loop around the validated core.

What it does
------------
For each target year in the trajectory:

  1. apply the trajectory's cumulative growth factors to the base-year data
     (yields, herds, land, world prices, demand shifters),
  2. **reconcile** the scaled data back onto its accounting identities
     (:mod:`capri_mod.projection.reconcile`),
  3. solve the validated comparative-static core against the projected data,
  4. carry state forward (herds, perennial areas, land allocation) as the next
     period's starting point.

Baseline and policy are kept separate
-------------------------------------
``run()`` solves the trajectory **twice** when a policy scenario is supplied:
once under the baseline policy and once under the scenario. The reported result
carries both, plus their difference. This is the README §10.2 commitment made
concrete: a reader can always see how much of a projected figure is "the world
changing anyway" (baseline drift) versus the policy (the increment). The
increment is the model's validated strength; the drift is an adopted external
assumption, and the two must never be presented as one number.

Correctness gate
----------------
Projecting with the NULL trajectory must reproduce the comparative-static result
exactly. That identity tests the whole machinery — scaling, reconciliation, loop,
state carry-forward — without depending on any forecast being right, and it is
the first thing the test suite checks.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .trajectory import BaselineTrajectory
from .reconcile import reconcile_projected_data, ReconciliationReport


@dataclass
class ProjectionResult:
    """Projection output, with baseline drift and policy increment separated."""

    trajectory: Dict                       # provenance of the driver
    years: List[int]
    baseline: Dict[int, Dict] = field(default_factory=dict)   # year -> results
    scenario: Dict[int, Dict] = field(default_factory=dict)   # year -> results
    increment: Dict[int, Dict] = field(default_factory=dict)  # scenario - baseline
    reconciliation: Dict[int, ReconciliationReport] = field(default_factory=dict)
    notes: Dict = field(default_factory=dict)

    def summary(self) -> Dict:
        return {
            "trajectory": self.trajectory,
            "years": self.years,
            "has_policy_increment": bool(self.increment),
            "reconciliation": {y: r.summary()
                               for y, r in self.reconciliation.items()},
            "interpretation": self.notes.get("interpretation"),
        }


class ProjectionModule:
    """Run the validated core forward along an external baseline trajectory."""

    #: which data blocks each trajectory block scales
    _BLOCK_TARGETS = {
        "yields": "yields",
        "herds": "animal_numbers",
        "land": "land",
        "world_prices": "world_prices",
    }

    def __init__(self, model, trajectory: Optional[BaselineTrajectory] = None):
        """
        Parameters
        ----------
        model : CAPRIModel
            The validated comparative-static model. Its data dict is the base
            year; the projection never mutates it (a deep copy is scaled).
        trajectory : BaselineTrajectory
            The external driver. Defaults to the NULL trajectory, which must
            reproduce the comparative-static result.
        """
        self.model = model
        self.trajectory = trajectory or BaselineTrajectory.null()

    # ------------------------------------------------------------------ apply
    def project_data(self, year: int) -> tuple:
        """Scaled + reconciled data for one target year.

        Returns ``(data, reconciliation_report)``. The base-year data is deep
        copied, never mutated.
        """
        data = copy.deepcopy(self.model.data)
        traj = self.trajectory

        # --- yields: per-activity factors
        if "yields" in data and isinstance(data["yields"], pd.DataFrame):
            y = data["yields"]
            for col in y.columns:
                # per-region factor where the trajectory has it, else the
                # activity-level value
                if traj.regional.get("yields"):
                    for reg in y.index:
                        f = traj.factor("yields", col, year, region=reg)
                        if f != 1.0:
                            y.at[reg, col] = y.at[reg, col] * f
                else:
                    f = traj.factor("yields", col, year)
                    if f != 1.0:
                        y[col] = y[col] * f

        # --- herds: per-animal factors
        if "animal_numbers" in data and isinstance(data["animal_numbers"], pd.DataFrame):
            a = data["animal_numbers"]
            for col in a.columns:
                if traj.regional.get("herds"):
                    for reg in a.index:
                        f = traj.factor("herds", col, year, region=reg)
                        if f != 1.0:
                            a.at[reg, col] = a.at[reg, col] * f
                else:
                    f = traj.factor("herds", col, year)
                    if f != 1.0:
                        a[col] = a[col] * f

        # --- land: per-land-type factors (drives the reconciliation target)
        if "land" in data and isinstance(data["land"], pd.DataFrame):
            L = data["land"]
            for col in L.columns:
                f = traj.factor("land", col, year)
                if f != 1.0:
                    L[col] = L[col] * f

        # --- world prices: per-commodity factors
        if "world_prices" in data and isinstance(data["world_prices"], pd.Series):
            wp = data["world_prices"]
            for idx in wp.index:
                f = traj.factor("world_prices", idx, year)
                if f != 1.0:
                    wp[idx] = wp[idx] * f

        # --- crop areas follow land drift before reconciliation, so the
        #     reconciliation corrects a genuine mismatch rather than an
        #     artefact of leaving areas at base while land moved.
        if "areas" in data and isinstance(data["areas"], pd.DataFrame):
            land_f = traj.factor("land", "_default", year)
            if land_f != 1.0:
                data["areas"] = data["areas"] * land_f

        report = reconcile_projected_data(data, base_data=self.model.data)
        return data, report

    # -------------------------------------------------------------------- run
    def run(self,
            policy_scenario: Optional[str] = None,
            years: Optional[List[int]] = None,
            **run_kwargs) -> ProjectionResult:
        """Solve the core along the trajectory, separating drift from policy.

        Parameters
        ----------
        policy_scenario : str, optional
            If given, each year is solved twice — baseline and scenario — and
            the increment reported. If omitted, only the baseline path is run.
        years : list[int], optional
            Target years; defaults to the trajectory's.
        """
        years = years or list(self.trajectory.target_years)
        result = ProjectionResult(
            trajectory=self.trajectory.provenance(), years=years)

        carried: Optional[Dict] = None
        for year in years:
            data, report = self.project_data(year)
            if carried:
                self._carry_forward(data, carried)
            result.reconciliation[year] = report

            base_res = self._solve(data, scenario="BASELINE", **run_kwargs)
            result.baseline[year] = base_res

            if policy_scenario:
                scen_res = self._solve(data, scenario=policy_scenario, **run_kwargs)
                result.scenario[year] = scen_res
                result.increment[year] = self._difference(base_res, scen_res)

            carried = self._state_from(base_res)

        result.notes["interpretation"] = (
            "Baseline is the adopted external trajectory (drift), NOT a forecast "
            "this model makes; the increment is the policy effect, which is the "
            "validated quantity. Report them separately — never as one number. "
            "A projection is defended by showing which conclusions hold across "
            "plausible trajectories, not by asserting the trajectory is right.")
        result.notes["trajectory_is_null"] = self.trajectory.is_null()
        return result

    # -------------------------------------------------------------- internals
    def _solve(self, data: Dict, scenario: str, **kwargs) -> Dict:
        """Solve the comparative-static core against a projected data set.

        A *fresh* model instance is built from the projected data. The model
        constructs its supply and market modules (and the PMP calibration) at
        construction time, so swapping the data dict on an existing model would
        leave those modules on the base year and silently return base-year
        results for a projected run.
        """
        cls = type(self.model)
        projected_model = cls(
            data=data,
            data_dir=getattr(self.model, "data_dir", None),
            verbose=False,
            base_year=getattr(self.model, "base_year", "2017"),
        )
        return projected_model.run(scenario=scenario, **kwargs)

    @staticmethod
    def _state_from(results: Dict) -> Dict:
        """Extract the state carried into the next period.

        Perennial areas are stocks, not annual decisions — a projection that
        re-optimises an olive grove or an orchard from scratch each period would
        overstate how fast the sector can adjust.

        NOTE: herd sizes are extracted here but are NOT yet applied by
        ``_carry_forward``, which writes perennial crop areas only. Herds are
        therefore re-optimised each period, which overstates livestock
        adjustment speed. Carrying them would mean seeding ``animal_numbers``
        from the previous period's solved levels.
        """
        state = {}
        supply = results.get("supply") if isinstance(results, dict) else None
        if supply:
            state["activities"] = {
                reg: getattr(res, "activities", None) for reg, res in supply.items()}
        return state

    @staticmethod
    def _carry_forward(data: Dict, carried: Dict) -> None:
        """Seed the next period from the previous period's solved state.

        Currently applies PERENNIAL CROP AREAS only. See ``_state_from`` for the
        herd carry-forward that is extracted but not yet applied.
        """
        acts = carried.get("activities") or {}
        areas = data.get("areas")
        if areas is None or not acts:
            return
        PERENNIAL = [c for c in ("APPL", "OFRU", "CITR", "OLIV", "TAGR", "TWIN")
                     if c in areas.columns]
        for reg, series in acts.items():
            if series is None or reg not in areas.index:
                continue
            for crop in PERENNIAL:
                if crop in series.index:
                    areas.at[reg, crop] = float(series[crop])

    @staticmethod
    def _difference(baseline: Dict, scenario: Dict) -> Dict:
        """Scenario minus baseline, for the headline aggregates."""
        diff = {}
        for key in ("total_production", "total_area", "ghg_emissions"):
            b, s = baseline.get(key), scenario.get(key)
            if isinstance(b, (int, float)) and isinstance(s, (int, float)):
                diff[key] = s - b
                diff[f"{key}_pct"] = ((s - b) / b * 100.0) if b else np.nan
        return diff

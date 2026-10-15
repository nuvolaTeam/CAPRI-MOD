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
from capri_mod.params import param, param_table


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


def milk_share_static(tab, cols, region):
    """Share of the first product group in the region's output (value or quantity table), 1.0 without data."""
    if tab is None or region not in tab.index:
        return 1.0
    m = sum(float(tab.at[region, c]) for c in cols[0] if c in tab.columns and pd.notna(tab.at[region, c]))
    o = sum(float(tab.at[region, c]) for c in cols[1] if c in tab.columns and pd.notna(tab.at[region, c]))
    return m / (m + o) if (m + o) > 0 else 1.0


class ProjectionModule:
    """Run the validated core forward along an external baseline trajectory."""

    #: which data blocks each trajectory block scales
    _BLOCK_TARGETS = {
        "yields": "yields",
        "herds": "animal_numbers",
        "land": "land",
        "world_prices": "world_prices",
    }

    def __init__(self, model, trajectory: Optional[BaselineTrajectory] = None,
                 capri_prices_dir: Optional[str] = None):
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
        # CAPRI's 2030 prices and premiums in 2017 money (capri_mod/projection/prices.py);
        # None keeps base-year prices
        self.capri_prices_dir = capri_prices_dir
        self.price_summary = None

    # ------------------------------------------------------------------ apply
    def project_data(self, year: int) -> tuple:
        """Scaled + reconciled data for one target year.

        Returns ``(data, reconciliation_report)``. The base-year data is deep
        copied, never mutated.
        """
        data = copy.deepcopy(self.model.data)
        traj = self.trajectory
        # the market's year: CAPRI's bilateral market of that year where it exists (2030 reference)
        data["market_year"] = int(year)
        # CAPRI's baseline calibration applies where the trajectory moves the data (a null trajectory must return the
        # comparative-static result exactly: the projection layer's correctness gate)
        data["calibrate_baseline"] = any(
            abs(float(v) - 1.0) > 1e-12
            for blk in (list((traj.growth or {}).values()) + [e for r in (traj.regional or {}).values() for e in r.values()])
            for by_year in (blk or {}).values() if isinstance(by_year, dict)
            for yy, v in by_year.items() if str(yy) == str(year))

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
                if traj.regional.get("land"):
                    # per region where the trajectory has it (CAPRI's 2030 reference: capri_ref_2030.json)
                    for reg in L.index:
                        f = traj.factor("land", col, year, region=reg)
                        if f != 1.0:
                            L.at[reg, col] = L.at[reg, col] * f
                else:
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
            # crop areas follow CAPRI's trend projection of each activity's level where the trajectory
            # carries it (CAPTRD projects LEVL for crops and animals alike; its 'herds' block holds them):
            # the reconciliation below then restores each region's cropped-area-to-land ratio, so the crop
            # MIX is CAPRI's trend and the total follows the land
            lv = traj.growth.get("herds", {})
            ar = data["areas"]
            for col in ar.columns:
                if col not in lv and not any(col in (traj.regional.get("herds", {}).get(r) or {}) for r in ar.index[:5]):
                    continue
                for reg in ar.index:
                    f = traj.factor("herds", col, year, region=reg)
                    if f != 1.0 and pd.notna(ar.at[reg, col]):
                        ar.at[reg, col] = ar.at[reg, col] * f

        if self.capri_prices_dir:
            from pathlib import Path
            from .prices import apply_capri_prices_2030
            from capri_mod.supply.supply_module import young_animal_table, RegionalSupplyModel
            self.price_summary = apply_capri_prices_2030(
                data, Path(self.capri_prices_dir), young_animal_table(), RegionalSupplyModel.FEED_CEREAL_MIX,
                cake_index=RegionalSupplyModel._cake_index())

        self._project_livestock(data, self.model.data, year)
        # CAPRI's own 2030 rations and requirements with its 2030 reference (Sprint 9q): factors per region, animal and
        # feed on the 2017 rations (tools/build_ration_trajectory_2030.py); where present they replace the uniform
        # requirement scaling of _project_livestock for that ration
        if str(getattr(traj, "name", "")).startswith("capri_ref") and self.capri_prices_dir:
            from pathlib import Path as _P
            f_ = _P(self.capri_prices_dir) / "capri_ref_ration_2030.csv"
            if f_.exists():
                t_ = pd.read_csv(f_)
                rf = {}
                ghg_f = {}
                for r_ in t_.itertuples(index=False):
                    if str(r_.item).startswith("ghg_"):
                        ghg_f[(r_.region, r_.animal, r_.item[4:])] = float(r_.factor)
                    else:
                        rf.setdefault((r_.region, r_.animal), {})[r_.item] = float(r_.factor)
                data["ration_factor"] = rf
                # CAPRI's 2030 manure and enteric methane per head (CH4MAN, CH4ENT; Sprint 9s): the 2030 / 2017
                # factor on the 2017 per-head coefficients
                for key_, item_ in (("livestock_ch4man_coef", "CH4MAN"), ("livestock_ch4ent_coef", "CH4ENT")):
                    tab_ = data.get(key_)
                    if isinstance(tab_, pd.DataFrame):
                        tab_ = tab_.copy()
                        for (reg_, an_, it_), f in ghg_f.items():
                            if it_ == item_ and reg_ in tab_.index and an_ in tab_.columns and pd.notna(tab_.at[reg_, an_]):
                                tab_.at[reg_, an_] = float(tab_.at[reg_, an_]) * f
                        data[key_] = tab_
            # usable fodder per ha of the fodder balances (FEDM / LEVL of CAPRI's fodder crops, 2030 over 2017)
            f2 = _P(self.capri_prices_dir) / "capri_ref_fodder_2030.csv"
            fb = data.get("fodder_balance")
            if f2.exists() and isinstance(fb, dict):
                uf = {(r_.region, r_.crop): float(r_.factor) for r_ in pd.read_csv(f2).itertuples(index=False)}
                for reg_, feeds_ in fb.items():
                    for feed_, rec_ in (feeds_ or {}).items():
                        k_ = (reg_, rec_.get("crop"))
                        if k_ in uf and "u_t_per_ha" in rec_:
                            rec_["u_t_per_ha"] = float(rec_["u_t_per_ha"]) * uf[k_]
        report = reconcile_projected_data(data, base_data=self.model.data)
        return data, report

    #: animals whose output per head follows their projected yield
    LIVESTOCK_YIELD = ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGP", "PIGS", "PIGF", "LAYS", "BROI")
    #: breeding.gms requirement functions of a 600 kg dairy cow at 4% fat (as tools/build_genetics_effects.py)
    _NEM, _NEL_KG = param("REQ_NEM"), param("REQ_NEL_KG")
    _CRPR_KG, _CRPR_FIX = param("REQ_CRPR_KG"), param("REQ_CRPR_FIX")
    _DRMN_KG, _DRMN_FIX = param("REQ_DRMN_KG"), param("REQ_DRMN_FIX")
    _N_KG_MILK = param("REQ_N_KG_MILK")

    def _project_livestock(self, data: Dict, base: Dict, year: Optional[int] = None) -> None:
        """Livestock output per head, and what it takes, follow the projected yields (CAPRI: the trend
        projection's YILD per head; requirements from its own functions).

        The yields table was scaled, but output per head came from the base-year coefficients, so a 2030 cow
        gave 2017 milk (EU farm milk 10% below CAPRI's 2030 reference with cows 3% above). Per region and
        animal f = projected / base yield scales the output and revenue coefficients per head (dairy cows:
        the milk part only, cull-cow beef unchanged); the ration's requirements scale with f (feed per unit
        of output constant) except for dairy cows, whose energy, protein and dry-matter requirements and manure
        N follow breeding.gms's functions of the milk yield. Stored for the ration model as
        data["ration_scale"] = {(region, animal): (f_energy, f_protein, f_dry_matter)}."""
        Y1, Y0 = data.get("yields"), base.get("yields")
        if not isinstance(Y1, pd.DataFrame) or not isinstance(Y0, pd.DataFrame):
            return
        acts = [a for a in self.LIVESTOCK_YIELD if a in Y1.columns and a in Y0.columns]
        if not acts:
            return
        with np.errstate(divide="ignore", invalid="ignore"):
            F = (Y1[acts] / Y0[acts].reindex(Y1.index)).replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.5, 2.0)
        pv = data.get("livestock_product_value_by_market_coef")
        bp = data.get("livestock_output_by_product_coef")
        # sheep and goats (K12): milk (SGMI) and meat (SGMT) per head follow their own CAPRI yields, SHGP_MILK (SHGM's
        # milk per head) and SHGP_MEAT (SHGF's meat per head); SHGP's aggregate factor is their mix by the region's
        # output value (as the dairy cow's milk part), and the yields table follows it
        prod_f = {}
        if year is not None and "SHGP" in F.columns:
            traj = self.trajectory
            for r in F.index:
                fm = float(np.clip(traj.factor("yields", "SHGP_MILK", year, region=r), 0.5, 2.0))
                ft = float(np.clip(traj.factor("yields", "SHGP_MEAT", year, region=r), 0.5, 2.0))
                if abs(fm - 1.0) < 1e-12 and abs(ft - 1.0) < 1e-12:
                    continue
                prod_f[(r, "SHGP", "SGMI")] = fm
                prod_f[(r, "SHGP", "SGMT")] = ft
                sh = milk_share_static(pv, (("SHGP.SGMI",), ("SHGP.SGMT",)), r)
                F.at[r, "SHGP"] = sh * fm + (1.0 - sh) * ft
                if r in Y1.index and pd.notna(Y0.at[r, "SHGP"] if r in Y0.index else np.nan):
                    Y1.at[r, "SHGP"] = float(Y0.at[r, "SHGP"]) * F.at[r, "SHGP"]
        if bool((F.sub(1.0).abs() < 1e-12).all().all()):
            return

        milk_share = milk_share_static

        def _unused(tab, cols, region):
            if tab is None or region not in tab.index:
                return 1.0
            m = sum(float(tab.at[region, c]) for c in cols[0] if c in tab.columns and pd.notna(tab.at[region, c]))
            o = sum(float(tab.at[region, c]) for c in cols[1] if c in tab.columns and pd.notna(tab.at[region, c]))
            return m / (m + o) if (m + o) > 0 else 1.0

        for key in ("livestock_output_coef", "livestock_revenue_coef", "livestock_product_value_coef",
                    "livestock_output_value_coef"):
            tab = data.get(key)
            if not isinstance(tab, pd.DataFrame):
                continue
            for a in acts:
                if a not in tab.columns:
                    continue
                for r in tab.index.intersection(F.index):
                    f = float(F.at[r, a])
                    if a == "DCOW":
                        sh = (milk_share(bp, (("DCOW.COMI",), ("DCOW.BEEF",)), r) if key == "livestock_output_coef"
                              else milk_share(pv, (("DCOW.MILK",), ("DCOW.BEEF",)), r))
                        f = sh * f + (1.0 - sh)
                    v = tab.at[r, a]
                    if pd.notna(v):
                        tab.at[r, a] = float(v) * f
        for tab in (pv, bp):
            if not isinstance(tab, pd.DataFrame):
                continue
            for col in tab.columns:
                a, prod = col.split(".", 1)
                if a not in acts or (a == "DCOW" and prod == "BEEF"):
                    continue
                idx = tab.index.intersection(F.index)
                if a == "SHGP" and prod_f:
                    for r in idx:
                        f_ = prod_f.get((r, a, prod), float(F.at[r, a]))
                        if pd.notna(tab.at[r, col]):
                            tab.at[r, col] = float(tab.at[r, col]) * f_
                    continue
                tab.loc[idx, col] = tab.loc[idx, col] * F.loc[idx, a]
        scale = {}
        mann = data.get("livestock_manure_n_coef")
        for r in F.index:
            for a in acts:
                f = float(F.at[r, a])
                if abs(f - 1.0) < 1e-12:
                    continue
                if a == "DCOW":
                    y0 = float(Y0.at[r, a]) * 1000.0 if r in Y0.index else 0.0      # t -> kg milk per cow
                    if not y0 > 0:
                        continue
                    y1, g = y0 * f, y0 * (f - 1.0)
                    fe = (self._NEL_KG * y1 + 1.1 * self._NEM) / (self._NEL_KG * y0 + 1.1 * self._NEM)
                    fp = (self._CRPR_KG * y1 + self._CRPR_FIX) / (self._CRPR_KG * y0 + self._CRPR_FIX)
                    fd = (self._DRMN_KG * y1 + self._DRMN_FIX) / (self._DRMN_KG * y0 + self._DRMN_FIX)
                    scale[(r, a)] = (fe, fp, fd)
                    if isinstance(mann, pd.DataFrame) and r in mann.index and a in mann.columns \
                            and pd.notna(mann.at[r, a]) and float(mann.at[r, a]) > 0:
                        mann.at[r, a] = float(mann.at[r, a]) + self._N_KG_MILK * g
                else:
                    scale[(r, a)] = (f, f, f)
        data["ration_scale"] = scale

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

            if policy_scenario is not None and not isinstance(policy_scenario, str):
                # A scenario OBJECT (e.g. greendeal_scenario()): baseline and
                # scenario are solved on the SAME projected model, so the
                # scenario reuses that year's baseline - its EU market base and
                # calibration - instead of building and solving its own again.
                pm = self._model_for(data)
                # the scenario's technology settings hold for its baseline too (CAPRI's scenario file
                # loads the reference technology file: capri_mod/policy/endotech.py)
                _et = dict(getattr(policy_scenario, "endotech", None) or {})
                _et.update(run_kwargs.pop("endotech", None) or {})
                if _et:
                    run_kwargs["endotech"] = _et
                # ... and so does its manure trade setting
                if getattr(policy_scenario, "manure_trade", None) is not None and run_kwargs.get("manure_trade") is None:
                    run_kwargs["manure_trade"] = bool(policy_scenario.manure_trade)
                # ... and its biofuel market setting
                if getattr(policy_scenario, "biofuel_markets", None) is not None and run_kwargs.get("biofuel_markets") is None:
                    run_kwargs["biofuel_markets"] = bool(policy_scenario.biofuel_markets)
                base_res = pm.run(scenario="BASELINE", **run_kwargs)
                result.baseline[year] = base_res
                scen_res = pm.run(custom_scenario=policy_scenario, **run_kwargs)
                result.scenario[year] = scen_res
                result.increment[year] = self._difference(base_res, scen_res)
                carried = self._state_from(base_res)
                continue

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
    def _model_for(self, data: Dict):
        """A fresh model built on a projected data set (see _solve for why)."""
        cls = type(self.model)
        pm = cls(data=data, data_dir=getattr(self.model, "data_dir", None),
                 verbose=False, base_year=getattr(self.model, "base_year", "2017"))
        pm = self._carry_settings(pm)
        self._last_projected_model = pm      # kept for diagnostics (e.g. manure-pool trace)
        return pm

    #: model settings carried to the fresh projected model. Without this, a
    #: switch set on the outer model (use_ration) never reached the model that
    #: runs the projected scenario - a Farm-to-Fork test with the EU ration
    #: "on" ran with it off and looked identical.
    CARRIED_SETTINGS = ("use_ration", "use_land_market", "grassland_allowance", "use_manure_market", "manure_pool_tolerance", "manure_max_outer_iter", "surplus_per_current_ha", "use_manure_techs", "use_nitrate", "qp_solver", "fodder_at_shadow_price", "use_feed_in_supply", "use_young_animal_market", "land_no_slack", "trace_outer", "jrc_capped_override")

    def _carry_settings(self, pm):
        for a in self.CARRIED_SETTINGS:
            if hasattr(self.model, a):
                setattr(pm, a, getattr(self.model, a))
        # market-module switches
        for a in ("use_dairy_block",):
            mm0, mm1 = getattr(self.model, "market_module", None), getattr(pm, "market_module", None)
            if mm0 is not None and mm1 is not None and hasattr(mm0, a):
                setattr(mm1, a, getattr(mm0, a))
        return pm

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
        projected_model = self._carry_settings(projected_model)
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

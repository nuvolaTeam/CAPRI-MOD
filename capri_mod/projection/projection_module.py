"""Multi-year projection — a time loop around the validated core (comparative static per year, as CAPRI;
only perennial areas are carried, along the baseline path).

What it does
------------
For each target year in the trajectory:

  1. apply the trajectory's cumulative growth factors to the base-year data
     (yields, herds, land, world prices, demand shifters),
  2. **reconcile** the scaled data back onto its accounting identities
     (:mod:`capri_mod.projection.reconcile`),
  3. solve the validated comparative-static core against the projected data,
  4. carry state forward (perennial areas only; herds and land allocation are not carried) as the next
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
from .equations.breeding import p_animReqCopy_ENNE_nonlact, p_animReqCopy_NEA_share
from .equations.calc_nexport import CRPR_EXPT_COMI
from .reconcile import reconcile_projected_data, ReconciliationReport
from capri_mod.params import param, param_table
from capri_mod.tableio import read_input


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


def _split_terms_at_year(data: dict, year: int) -> None:
    """The intensity split tables (data["dairy_intensity"], a DataFrame per region; data["cattle_intensity"],
    {region: {key: Series}}) at `year`: each column with a "<column>_<year>" twin takes the twin's value where it has
    one (CAPRI's terms at that year's calibration point; a region without them keeps the base year's); every
    "_<4 digits>" twin column is dropped."""
    import re as _re
    sfx = f"_{year}"
    twin = _re.compile(r".+_\d{4}$")
    di = data.get("dairy_intensity")
    if isinstance(di, pd.DataFrame):
        di = di.copy()
        for c in [c for c in di.columns if str(c).endswith(sfx) and c[: -len(sfx)] in di.columns]:
            di[c[: -len(sfx)]] = di[c].where(di[c].notna(), di[c[: -len(sfx)]])
        data["dairy_intensity"] = di.drop(columns=[c for c in di.columns if twin.match(str(c))
                                                   and not str(c).endswith(("_capri2030", "_recipe2030"))])
    ci = data.get("cattle_intensity")
    if isinstance(ci, dict):
        out = {}
        for r, keys in ci.items():
            out[r] = {}
            for k, row in keys.items():
                row = row.copy()
                for c in [c for c in row.index if str(c).endswith(sfx) and c[: -len(sfx)] in row.index]:
                    if row[c] == row[c]:
                        row[c[: -len(sfx)]] = row[c]
                out[r][k] = row.drop([c for c in row.index if twin.match(str(c))
                                      and not str(c).endswith(("_capri2030", "_recipe2030"))])
        data["cattle_intensity"] = out


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
        # CAPRI's intensity splits (dairy DCOL/DCOH, the cattle pairs) at the year's calibration point: the columns
        # "<column>_<year>" (CAPRI's own terms of that year, tools/build/build_dairy_intensity.py) replace the base
        # year's (9 November 2026)
        _split_terms_at_year(data, int(year))
        # manure N per head: CAPRI's coefficients of the year, which CAPRI computes from the year's herd data before it
        # solves (capmod.gms l. 1090: MANN from the crude-protein requirement, feed/req_or_man_fnc.gms, ported in
        # capri_mod/feed/equations/req_or_man_fnc.py; tools/build/build_livestock_manure_2030.py, K179); the base year's at
        # the base year (manure P2O5 and K2O: capri_mod/fert/npk.manure_coef_table at the run's market year). Until
        # 18 November 2026 the 2017 coefficients at 2030, the dairy cows' raised by 0.0086 kg N per kg of extra milk
        # (breeding.gms; CAPRI's own 2030 dairy coefficient is 6% below its 2017 one in the EU)
        from capri_mod.fert.npk import manure_coef_table
        data["livestock_manure_n_coef"] = manure_coef_table("N", year=int(year)).copy()
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
                    # per region where the trajectory has it (CAPRI's 2030 reference: capri_data/scenarios/capri_ref_2030)
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
            from capri_mod.data.inputs import base_year as _base_year
            # the year's young-animal coefficients (CAPRI's 2030 ones, K178), the base year's for its output values
            self.price_summary = apply_capri_prices_2030(
                data, Path(self.capri_prices_dir), young_animal_table(year=int(year)),
                RegionalSupplyModel.FEED_CEREAL_MIX, cake_index=RegionalSupplyModel._cake_index(),
                young_table_base=young_animal_table(year=getattr(self.model, "base_year", None) or _base_year()))

        self._project_livestock(data, self.model.data, year)
        # the outputs per head of the simulation year where CAPRI's are in the data (2030: register DEP-13 step 2), with
        # CAPRI's 2030 reference as the trajectory, as its rations below: a trend projection (CAPTRD) keeps its own
        # yields, which the outputs per head follow (_project_livestock)
        if str(getattr(traj, "name", "")).startswith("capri_ref"):
            self.SUPBAL_outputsPerHead_Y(data, year, data.get("livestock_output_by_product_coef"),
                                         data.get("livestock_product_value_by_market_coef"))
            self.req_or_man_fnc_CRPR_EXPT_Y(data, year)
        # CAPRI's own 2030 rations and requirements with its 2030 reference (the port of CAPRI's 2030 rations and fodder): factors per region, animal and
        # feed on the 2017 rations (tools/build/build_ration_trajectory_2030.py); where present they replace the uniform
        # requirement scaling of _project_livestock for that ration
        if str(getattr(traj, "name", "")).startswith("capri_ref") and self.capri_prices_dir:
            from pathlib import Path as _P
            f_ = _P(self.capri_prices_dir) / "capri_ref_ration_2030.csv"
            if f_.exists():
                t_ = read_input(f_)
                rf = {}
                ghg_f = {}
                for r_ in t_.itertuples(index=False):
                    if str(r_.item).startswith("ghg_"):
                        ghg_f[(r_.region, r_.animal, r_.item[4:])] = float(r_.factor)
                    else:
                        rf.setdefault((r_.region, r_.animal), {})[r_.item] = float(r_.factor)
                data["ration_factor"] = rf
                # CAPRI's 2030 manure and enteric methane per head (CH4MAN, CH4ENT; the removal of synthetic data): the 2030 / 2017
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
                uf = {(r_.region, r_.crop): float(r_.factor) for r_ in read_input(f2).itertuples(index=False)}
                for reg_, feeds_ in fb.items():
                    for feed_, rec_ in (feeds_ or {}).items():
                        cr_ = rec_.get("crops") or {}
                        for c_ in list(cr_):
                            if (reg_, c_) in uf:
                                cr_[c_] = float(cr_[c_]) * uf[(reg_, c_)]
        # The land reconciliation (the region's 2017 ratio of cropped area to land carried to the projected land) is for
        # a trend projection, whose activity levels and land types are projected apart (CAPTRD). CAPRI's own 2030
        # results (capri_ref_*: CAPMOD's Green Deal baseline) are one consistent solution: CAPRI simulates from them as
        # they are, so they are not rescaled (9 November 2026: until then the rescaling moved them by the change of
        # the ratio, Denmark's crops +4.1% and Croatia's +2.3% above CAPRI's levels, the baseline calibration reproducing
        # the rescaled levels; KNOWN_ISSUES K120). The plausibility checks still run.
        capri_levels = str(getattr(traj, "name", "")).startswith("capri_ref")
        report = reconcile_projected_data(data, base_data=None if capri_levels else self.model.data)
        return data, report

    #: animals whose output per head follows their projected yield
    LIVESTOCK_YIELD = ("DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGM", "SHGF", "PIGS", "PIGF", "LAYS", "BROI")
    #: breeding.gms requirement functions of a 600 kg dairy cow at 4% fat (as tools/build/build_genetics_effects.py)
    _NEM, _NEL_KG = param("REQ_NEM"), param("REQ_NEL_KG")
    _CRPR_KG, _CRPR_FIX = param("REQ_CRPR_KG"), param("REQ_CRPR_FIX")
    _DRMN_KG, _DRMN_FIX = param("REQ_DRMN_KG"), param("REQ_DRMN_FIX")

    @staticmethod
    def _nea_share(data: Dict, region: str) -> float:
        """NEA / NEM of the region's dairy cows: 0.17 (365 - HD)(1 - Et/100) / 365 (envind/breeding.gms l. 190-192:
        projection/equations/breeding.py p_animReqCopy_NEA_share)."""
        from capri_mod.data.definitions import capri_ms
        t = data.get("dairy_grazing_days")
        if t is None:
            raise ValueError("no MITERRA housing days for dairy cows (abatement/ammonia/RCEmissions.csv)")
        ms = capri_ms(region)
        hd = float(t.at[ms, "HD"]) if ms in t.index and "HD" in t.columns and pd.notna(t.at[ms, "HD"]) else 0.0
        et = float(t.at[ms, "Et"]) if ms in t.index and "Et" in t.columns and pd.notna(t.at[ms, "Et"]) else 0.0
        return p_animReqCopy_NEA_share(hd, et)

    def _project_livestock(self, data: Dict, base: Dict, year: Optional[int] = None) -> None:
        """Livestock output per head, and what it takes, follow the projected yields (CAPRI: the trend
        projection's YILD per head; requirements from its own functions).

        The yields table was scaled, but output per head came from the base-year coefficients, so a 2030 cow
        gave 2017 milk (EU farm milk 10% below CAPRI's 2030 reference with cows 3% above). Per region and
        animal f = projected / base yield scales the output and revenue coefficients per head (dairy cows:
        the milk part only, cull-cow beef unchanged); the ration's requirements scale with f (feed per unit
        of output constant) except for dairy cows, whose energy, protein and dry-matter requirements follow
        breeding.gms's functions of the milk yield (manure N per head: CAPRI's of the year, project_data). Stored for the ration model as
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
        # sheep and goats (K12): CAPRI's SHGM YILD is milk per head, SHGF's meat per head. SHGF's output (meat) follows
        # its own factor. SHGM has both outputs: its milk (SGMI) follows SHGM's factor, its meat (lambs and culls, SGMT)
        # SHGF's meat yield factor (CAPRI's 2030 reference has no meat yield of SHGM); SHGM's aggregate factor is their
        # mix by the region's output value (as the dairy cow's milk part), and the yields table keeps CAPRI's milk yield
        prod_f = {}
        if "SHGM" in F.columns:
            for r in F.index:
                fm = float(F.at[r, "SHGM"])
                ft = float(F.at[r, "SHGF"]) if "SHGF" in F.columns else 1.0
                if abs(fm - 1.0) < 1e-12 and abs(ft - 1.0) < 1e-12:
                    continue
                prod_f[(r, "SHGM", "SGMI")] = fm
                prod_f[(r, "SHGM", "MILK")] = fm
                prod_f[(r, "SHGM", "SGMT")] = ft
                sh = milk_share_static(pv, (("SHGM.MILK",), ("SHGM.SGMT",)), r)
                F.at[r, "SHGM"] = sh * fm + (1.0 - sh) * ft
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
                if a == "SHGM" and prod_f:
                    for r in idx:
                        f_ = prod_f.get((r, a, prod), float(F.at[r, a]))
                        if pd.notna(tab.at[r, col]):
                            tab.at[r, col] = float(tab.at[r, col]) * f_
                    continue
                tab.loc[idx, col] = tab.loc[idx, col] * F.loc[idx, a]
        # SHGM's two products follow two factors (milk SHGM's, meat SHGF's): its output is their sum, not its output
        # x the value-weighted factor above (the revenue's; until 24 November 2026 the output's too, up to 15% off the
        # sum of its products at 2030, KNOWN_ISSUES K200)
        if prod_f:
            self.SUPBAL_animalOutputSum(data, bp, {(r, "SHGM") for (r, _a, _p) in prod_f})
        scale = {}
        nexp = data.get("livestock_n_export_coef")
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
                    # energy apart from lactation, CAPRI envind/breeding.gms l. 184-198: maintenance NEM, pregnancy
                    # NEP = 0.10 NEM, activity NEA = 0.17 NEM (365 - HD)(1 - Et/100) / 365 with the member state's
                    # housing days HD and stable share of grazing time Et (p_rcEmissions); where CAPRI has no row the
                    # GAMS zeros give HD = Et = 0 (NEA = 0.17 NEM), as here. Until 23 October 2026: 1.1 NEM (no NEA).
                    # (projection/equations/breeding.py p_animReqCopy_ENNE_nonlact)
                    nem = p_animReqCopy_ENNE_nonlact(self._NEM, self._nea_share(data, r))
                    fe = (self._NEL_KG * y1 + nem) / (self._NEL_KG * y0 + nem)
                    fp = (self._CRPR_KG * y1 + self._CRPR_FIX) / (self._CRPR_KG * y0 + self._CRPR_FIX)
                    fd = (self._DRMN_KG * y1 + self._DRMN_FIX) / (self._DRMN_KG * y0 + self._DRMN_FIX)
                    scale[(r, a)] = (fe, fp, fd)
                    # N in products: CAPRI fert/calc_nexport.gms l. 44, 0.0054 kg N per kg of cow milk (COMI;
                    # projection/equations/calc_nexport.py CRPR_EXPT_COMI)
                    if isinstance(nexp, pd.DataFrame) and r in nexp.index and a in nexp.columns \
                            and pd.notna(nexp.at[r, a]):
                        nexp.at[r, a] = float(nexp.at[r, a]) + CRPR_EXPT_COMI(g)
                else:
                    scale[(r, a)] = (f, f, f)
                    # meat, eggs and young animals per head follow the projected yield (calc_nexport.gms: linear in
                    # the outputs per head)
                    if isinstance(nexp, pd.DataFrame) and r in nexp.index and a in nexp.columns \
                            and pd.notna(nexp.at[r, a]):
                        nexp.at[r, a] = float(nexp.at[r, a]) * f
        data["ration_scale"] = scale

    @staticmethod
    def SUPBAL_outputsPerHead_Y(data: Dict, year: Optional[int], bp, pv) -> None:
        """CAPRI's outputs per head of the simulation year: the final products in SUPBAL_'s total output, v_actLevl x
        DATA(r, act, OMS, "Y") (supply/supply_model.gms l. 4585-4595), at the 2030 market year CAPRI's 2030 production
        over the model's 2030 base heads (livestock_output_by_product_coef_2030.csv, tools/build/
        build_livestock_output_2030.py), in place of the base year's per head x the projected yield factor f
        (_project_livestock; exact for an animal's main output, not for its second outputs and the cattle's beef). So the
        model's 2030 base production of each product is CAPRI's 2030 production. Called by project_data with CAPRI's
        2030 reference as the trajectory (capri_ref, as CAPRI's 2030 rations); a trend projection keeps its own yields. Each product's value per head
        (livestock_product_value_by_market_coef: what its market price moves) follows its quantity, and the animal's
        totals take the change: livestock_output_coef the quantities' (their sum), livestock_product_value_coef,
        livestock_revenue_coef and livestock_output_value_coef the products' value (the young animals' part of the
        revenue and output value unchanged). A cell without CAPRI's 2030 output keeps the projected one. Register DEP-13
        step 2 (23 November 2026; until then all products per head followed f).

        CAPRI's GAMS, supply/supply_model.gms SUPBAL_'s total output (l. 4585-4595; the equation from l. 4551):

                SUM( (MPACT,A) $ (PACT_TO_O(MPACT,OMS) $ p_technFact(RUNR,MPACT,"LEVL",A)),
                    v_actLevl(RUNR,MPACT,A) * (%data%(RUNR,MPACT,OMS,"Y")
        $iftheni.till6 %ghgAbatement%==on
        *      --- mitigation effect on yield considered
                     * v_yldMit(RUNR,MPACT)
        $endif.till6
        *      --- endogenous pesticide use considered
        $iftheni.Pes1 %PEST_DISAGG%==ON
                     * (1 +(v_yldPestFac(RUNR,mPact,A)-1) $ (v_yldPestFac.range(RUNR,mPact,A) $ cact(mpact)))
        $endif.Pes1
                     * (p_technFact(RUNR,MPACT,OMS,A)+1.) * 0.001)
        """
        t = data.get(f"livestock_output_by_product_coef_{year}") if year is not None else None
        if not isinstance(t, pd.DataFrame) or not isinstance(bp, pd.DataFrame):
            return
        from capri_mod.model import CAPRIModel
        mkt = CAPRIModel.LIVESTOCK_PRODUCT_MARKET
        dq, dv = {}, {}
        for col in bp.columns.intersection(t.columns):
            a, prod = col.split(".", 1)
            mcol = f"{a}.{mkt.get(prod, prod)}"
            for r in bp.index.intersection(t.index):
                new, old = t.at[r, col], bp.at[r, col]
                if not (pd.notna(new) and float(new) > 0):
                    continue
                old = float(old) if pd.notna(old) else 0.0
                if old > 0 and isinstance(pv, pd.DataFrame) and mcol in pv.columns and r in pv.index \
                        and pd.notna(pv.at[r, mcol]):
                    v0 = float(pv.at[r, mcol])
                    pv.at[r, mcol] = v0 * float(new) / old
                    dv[(r, a)] = dv.get((r, a), 0.0) + v0 * (float(new) / old - 1.0)
                bp.at[r, col] = float(new)
                dq[(r, a)] = dq.get((r, a), 0.0) + float(new) - old
        ProjectionModule.SUPBAL_animalOutputSum(data, bp, set(dq))
        for key in ("livestock_product_value_coef", "livestock_revenue_coef", "livestock_output_value_coef"):
            tab = data.get(key)
            if not isinstance(tab, pd.DataFrame):
                continue
            for (r, a), x in dv.items():
                if r in tab.index and a in tab.columns and pd.notna(tab.at[r, a]):
                    tab.at[r, a] = float(tab.at[r, a]) + x

    @staticmethod
    def req_or_man_fnc_CRPR_EXPT_Y(data: Dict, year: Optional[int]) -> None:
        r"""CAPRI's N in products per head of the simulation year (data["livestock_n_export_coef"], the report item
        n_animal_products): at the 2030 market year CAPRI's 2030 values, calc_nexport.gms on its 2030 items over the
        model's 2030 base heads (livestock_n_export_coef_2030.csv, tools/build/build_livestock_n_export_2030.py), in
        place of the 2017 per head x the projected yield factor of _project_livestock. CAPRI's simulation recomputes
        them before it solves: capmod.gms l. 1090 includes feed/req_or_man_fnc.gms in its manure mode, which runs
        calc_nexport.gms for "Y" before the manure N (sim_ini_21730's "Y" values are the 2017 ones). A cell without a
        2030 value keeps the projected one. KNOWN_ISSUES K202 (24 November 2026).

        CAPRI's GAMS, feed/req_or_man_fnc.gms (l. 1814-1817 and 1824-1825), the manure mode:

            $iftheni.req12 not %req% ==on
            $batinclude 'util\title.gms' "'Calculating N content in outputs for animal activities'"
            $batinclude 'fert\calc_nexport.gms' '%yr%'
              p_MANN_A(RS,AACT,A,%yr%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A) $ p_crprReq(RS,AACT,A,%yr%))
                = MAX(0,p_crprReq(RS,AACT,A,%yr%) * p_animExcrProtCorrFact(RS,AACT,A,%yr%) / 6.0 - DATA(RS,AACT,"CRPR_EXPT",%yr%));
        """
        t = data.get(f"livestock_n_export_coef_{year}") if year is not None else None
        tab = data.get("livestock_n_export_coef")
        if not isinstance(t, pd.DataFrame) or not isinstance(tab, pd.DataFrame):
            return
        for a in tab.columns.intersection(t.columns):
            for r in tab.index.intersection(t.index):
                v = t.at[r, a]
                if pd.notna(v):
                    tab.at[r, a] = float(v)

    @staticmethod
    def SUPBAL_animalOutputSum(data: Dict, bp, cells) -> None:
        """An animal's output per head (livestock_output_coef, which the market bridge splits into its products at their
        shares, coupling/bridge.py) as the sum of its final products per head, as SUPBAL_'s total output sums
        v_actLevl x DATA(r, act, OMS, "Y") over the products OMS of the activity (supply/supply_model.gms l. 4585-4595,
        quoted at SUPBAL_outputsPerHead_Y); for the (region, animal) cells given. KNOWN_ISSUES K200."""
        tab = data.get("livestock_output_coef")
        if not isinstance(tab, pd.DataFrame) or not isinstance(bp, pd.DataFrame):
            return
        parts = {}
        for c in bp.columns:
            parts.setdefault(c.split(".", 1)[0], []).append(c)
        for (r, a) in cells:
            if r in tab.index and a in tab.columns and r in bp.index and a in parts and pd.notna(tab.at[r, a]):
                tab.at[r, a] = float(sum(float(bp.at[r, c]) for c in parts[a] if pd.notna(bp.at[r, c])))

    # -------------------------------------------------------------------- run
    def run(self,
            policy_scenario=None,                  # a PolicyScenario, a registered scenario name or None
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
                 verbose=False, base_year=getattr(self.model, "base_year", None))
        self._last_projected_model = pm      # kept for diagnostics (e.g. manure-pool trace)
        return pm

    # The fresh projected model reads the same settings as the outer one (capri_mod/settings: one process-wide set),
    # so nothing is carried by hand (the former CARRIED_SETTINGS list lost every switch it did not name, e.g.
    # the GL food demand, the baseline calibration, the NLP tolerances).

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
            base_year=getattr(self.model, "base_year", None),
        )
        self._last_projected_model = projected_model     # kept for diagnostics and tests, as in _model_for
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
        # the crops on permanent land, as the supply model defines them (it used CAPRI's vineyard code TWIN, which
        # the model does not use - its vineyards are WINE - so vineyards were never carried)
        from capri_mod.supply.supply_module import RegionalSupplyModel
        PERENNIAL = [c for c in RegionalSupplyModel.PERMANENT_LAND_CROPS if c in areas.columns]
        for reg, series in acts.items():
            if series is None or reg not in areas.index:
                continue
            for crop in PERENNIAL:
                if crop in series.index:
                    areas.at[reg, crop] = float(series[crop])

    @staticmethod
    def _difference(baseline: Dict, scenario: Dict) -> Dict:
        """The policy increment of a year, scenario against baseline, as % change of the flat outputs both runs
        report (capri_mod.io_results.flatten_outputs: the EU's market production and prices, world prices, EU totals
        of the environmental accounts, the supply models' gross margin). Before 20 October 2026 it looked for keys
        CAPRIModel.run never returns and was always empty."""
        from capri_mod.io_results import flatten_outputs
        b, s = flatten_outputs(baseline), flatten_outputs(scenario)
        diff = {}
        for key, bv in b.items():
            sv = s.get(key)
            if isinstance(bv, bool) or isinstance(sv, bool) or not isinstance(bv, (int, float)) \
                    or not isinstance(sv, (int, float)):
                continue
            diff[f"{key}_pct"] = ((sv - bv) / bv * 100.0) if bv else np.nan
        return diff

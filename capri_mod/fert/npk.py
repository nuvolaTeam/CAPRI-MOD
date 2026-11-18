"""CAPRI's crop nutrient balance for N, P and K, the data of the fertilisation block of the regional supply model in
CAPRI's form (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, fertDistCres_ and the inner fertiliser
distribution model; capri_mod/supply/capri_regional_nlp.py).

Data (tools/build/build_npk_balance_2030.py, from CAPRI's 2030 reference results):
  npk_crop_coefs_2030.csv        per CAPRI region, model crop and nutrient: need, contribution to the arable residue
                                 pool, permanent crops' own residues, CAPRI's mineral flow (kg/ha), and the parts of
                                 the need that follow the main output's yield and the straw yield (need_yield_factor)
  npk_region_2030.csv            per CAPRI region and nutrient: mineral efficiency, manure and residue availability,
                                 CAPRI's unit value (EUR/t)
  fert_dist_priors_npk_2030.csv  the inner model's priors per crop group, source and nutrient (posterior mode per ha)
  livestock_manure_p_coef.csv, livestock_manure_k_coef.csv   manure P2O5 / K2O per model head (kg) at the base year;
                                 at the 2030 market year CAPRI's 2030 ones (livestock_manure_p_coef_2030.csv,
                                 livestock_manure_k_coef_2030.csv, KNOWN_ISSUES K179): manure_coef_table
Crop groups of the model crops: fert_dist_crop_groups_2030.csv (CAPRI's 2030 areas).
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from capri_mod.data.definitions import capri_ms
from capri_mod.params import param

NUTRIENTS = ("N", "P", "K")
#: the manure-per-head table of each nutrient (file stem; CAPRI's MANN, MANP, MANK)
MANURE_TABLES = {"N": "livestock_manure_n_coef", "P": "livestock_manure_p_coef", "K": "livestock_manure_k_coef"}


def manure_coef_table(nut: str, year=None) -> pd.DataFrame:
    """CAPRI's manure N, P2O5 or K2O per model head (kg; model region x model animal, empty where the model has no
    such animal) at a calibration year: the base year's (<stem>.csv: CAPRI's base-year totals over the model's heads,
    tools/build/build_livestock_output_coef.py, build_npk_balance_2030.py) or, at another market year, CAPRI's
    coefficients of that year in the baseline's folder (<stem>_<year>.csv; 2030: tools/build/
    build_livestock_manure_2030.py: CAPRI computes them from the simulation year's rations before it solves,
    capmod.gms l. 1090, KNOWN_ISSUES K179). year: by default the run's (RunInputs.market_year, set by SupplyModule; the
    base year where unset). A year without its table is an error (no fall back to the base year's)."""
    from capri_mod.data import inputs as _inputs
    by = str(_inputs.base_year())
    yr = year if year is not None else getattr(_inputs.current(), "market_year", None)
    yr = str(yr) if yr is not None else by
    name = f"{MANURE_TABLES[nut]}.csv" if yr == by else f"{MANURE_TABLES[nut]}_{yr}.csv"
    return _inputs.current().cached(name, lambda inp: inp.csv(name, "environment", index_col=0))
from capri_mod.fert.inner_fert_dist import SOURCES   # noqa: E402  CAPRI's nutrient sources, one definition
from capri_mod.data.definitions import CAPRI_PERM_NGRP as PERM_NGRP   # noqa: E402  CAPRI's set



def manure_applied_share() -> Dict[tuple, float]:
    """CAPRI's 2030 manure applied in the region per unit excreted, 1 - MTRADE / EXCRET, {(capri_region, nutrient):
    share} for N, P and K (2030/environment/manure_npk_applied_share_2030.csv, tools/build/build_npk_balance_2030.py;
    regions with CAPRI excretion only). One reading for the fertilisation block (SupplyModel._npk_applied_ratio) and the
    P balance (environmental/phosphorus.py); until 3 November 2026 each computed it from the extract under
    capri_data/sources."""
    from capri_mod.data import inputs as _inputs
    cache = _inputs.current().cache
    c = cache.get("npk_applied_ratio")
    if c is None:
        t = _inputs.current().csv("manure_npk_applied_share_2030.csv", "environment")
        c = {(r, n): float(x) for r, n, x in zip(t.capri_region, t.nutrient, t.applied_share)}
        cache["npk_applied_ratio"] = c
    return c


def need_multiplier(supply0: float, need0: float, own0: float, gc: float, perm_groups) -> tuple:
    """The need multiplier of a region and nutrient, calibrated at the base so that NUTNED_ summed over the crop groups
    closes with the base flows (CAPRI's v_cropNutNeedMultFact, fixed in simulation): (kappa, own_scaled).

    CAPRI's form: the multiplier on the need alone, the permanent groups' own residues (and deposition for N) on the
    supply side as they are, kappa x need0 = supply0 + gc x (their own residues), with supply0 = eff x MINE0 + g0 x EXCR0 + gc x CRES0.
    It is used wherever it leaves every permanent group (perm_groups: its base (need, own residues)) a positive need
    for its mineral and manure flows. Where it does not (the model's base supplies less than CAPRI's 2030 relative to
    the need while the grassland's own residues cover most of its need; STRUCTURAL_GAPS_PLAN S3), the need net of
    the own residues is scaled together, kappa x (need0 - gc x own0) = supply0, own_scaled True (REGISTERED, K50
    departure 1; until 31 October 2026 in every region)."""
    if need0 > 0:
        # the own residues on the supply side are the permanent groups' (NUTNED_ rows of PERM_NGRP)
        k = (supply0 + gc * sum(og for _, og in perm_groups)) / need0
        if all(k * ng - gc * og > 0.0 for ng, og in perm_groups if ng > 0):
            return k, False
    net0 = need0 - gc * own0
    return (supply0 / net0 if net0 > 0 else 1.0), True


def endo_slope(g0: float, m0: float, nut: str) -> float:
    """CAPRI's slope of the endogenous availability (fert/endoManAvail.gms) with its two corrections: availability at
    most max(0.999, g0) at zero application, at least min(0.2, g0) at max(300, m0) kg/ha."""
    # the slope of manure N availability on manure N applied per ha of land (0 for P and K), the ceiling at zero
    # application, the floor and the application rate it holds at: parameters ENDO_MAN_AV_* (fert/endoManAvail.gms)
    b = param("ENDO_MAN_AV_SLOPE_N") if nut == "N" else 0.0
    if b == 0.0 or not (m0 > 0):
        return 0.0
    ceil_, floor_, at_ = param("ENDO_MAN_AV_CEILING"), param("ENDO_MAN_AV_FLOOR"), param("ENDO_MAN_AV_FLOOR_KG")
    if g0 - m0 * b > max(ceil_, g0):
        b = (g0 - max(ceil_, g0)) / m0
    top = max(at_, m0) - m0
    if top > 0 and g0 + top * b < min(floor_, g0):
        b = (min(floor_, g0) - g0) / top
    return b


class NPKData:
    _inst = None

    def __init__(self, data_dir: Optional[str] = None):
        from capri_mod.data.inputs import RunInputs, current
        inp = RunInputs(data_dir, current().base_year) if data_dir else current()
        c = inp.csv("npk_crop_coefs_2030.csv", "environment")
        self.has_yield_shares = {"main_share", "straw_share"} <= set(c.columns)
        self.crop = {(r, n): d.set_index("model_crop") for (r, n), d in c.groupby(["capri_region", "nutrient"])}
        g = inp.csv("npk_region_2030.csv", "environment")
        self.reg = {(t.capri_region, t.nutrient): t for t in g.itertuples(index=False)}
        p = inp.csv("fert_dist_priors_npk_2030.csv", "environment")
        self.pri = {(r, n): d.set_index("ngrp") for (r, n), d in p.groupby(["capri_region", "nutrient"])}
        gr = inp.csv("fert_dist_crop_groups_2030.csv", "environment")
        self.groups = {r: d for r, d in gr.groupby("capri_region")}
        w = gr.groupby(["model_crop", "ngrp"]).share.sum()
        tot = w.groupby(level=0).transform("sum")
        self.eu_shares = {}
        for (mc, ng), v in (w / tot).items():
            self.eu_shares.setdefault(mc, {})[ng] = float(v)

    @classmethod
    def get(cls) -> "NPKData":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def crop_shares(self, capri_region: str) -> Dict[str, Dict[str, float]]:
        out = {mc: dict(v) for mc, v in self.eu_shares.items()}
        d = self.groups.get(capri_region)
        if d is not None:
            own = {}
            for t in d.itertuples(index=False):
                own.setdefault(t.model_crop, {})[t.ngrp] = float(t.share)
            out.update(own)
        return out

    def crop_coef(self, capri_region: str, nut: str, crop: str, col: str) -> float:
        """A model crop's coefficient (kg/ha); a crop CAPRI does not grow in the region takes the country's, else 0."""
        cache = self.__dict__.setdefault("_crop_dicts", {})
        for r in (capri_region, capri_ms(capri_region)):
            dd = cache.get((r, nut))
            if dd is None:
                d = self.crop.get((r, nut))
                # the table as {crop: {column: value}}: the same floats, without a pandas lookup per call (12% of a
                # regional problem's build, 27 October 2026)
                dd = cache[(r, nut)] = {} if d is None else d.to_dict("index")
            if crop in dd:
                v = float(dd[crop][col])
                if v == v:
                    return v
        return 0.0

    def capri_region(self, region: str) -> Optional[str]:
        """The CAPRI region of a model region (the region itself: the model's regions are CAPRI's units), else its
        country's when CAPRI's data have it, else None (as InnerFertDist.capri_region)."""
        c = region
        if c is not None and any((c, n) in self.crop for n in NUTRIENTS):
            return c
        cc = capri_ms(region)
        return cc if cc is not None and any((cc, n) in self.crop for n in NUTRIENTS) else None

    def yield_shares(self, capri_region: Optional[str], nut: str, crop: str) -> tuple:
        """(main, straw): the shares of a crop's need per ha that follow the main output's yield and the straw yield
        (fert/fertned.gms; tools/build/build_npk_balance_2030.py); the rest is at fertned's floor or cap and does not
        move. A crop or region without CAPRI data: (1, 0), the rule of a crop without straw."""
        if not self.has_yield_shares:
            raise RuntimeError("npk_crop_coefs_2030.csv has no main_share/straw_share: rerun "
                               "tools/build/build_npk_balance_2030.py")
        if capri_region:
            for r in (capri_region, capri_ms(capri_region)):
                d = self.crop.get((r, nut))
                if d is not None and crop in d.index:
                    m, s_ = float(d.at[crop, "main_share"]), float(d.at[crop, "straw_share"])
                    if m == m and s_ == s_:
                        return m, s_
        return 1.0, 0.0

    def region(self, capri_region: str, nut: str):
        t = self.reg.get((capri_region, nut))
        if t is None:
            t = self.reg.get((capri_ms(capri_region), nut))
        return t

    def priors(self, capri_region: str, nut: str):
        d = self.pri.get((capri_region, nut))
        if d is None:
            d = self.pri.get((capri_ms(capri_region), nut))
        return d

    def manure_per_head(self, region: str, nut: str, animal: str) -> float:
        """Manure P2O5 or K2O per model head of the region's animal (kg) at the run's market year (manure_coef_table);
        0 where the model has no such animal. N: the environmental module's (data["livestock_manure_n_coef"])."""
        if nut not in ("P", "K"):
            raise ValueError(f"manure_per_head: P or K, not {nut!r} (manure N: the environmental module's)")
        t = manure_coef_table(nut)
        if region not in t.index or animal not in t.columns:
            return 0.0
        v = t.at[region, animal]
        return float(v) if pd.notna(v) and v > 0 else 0.0


def grass_need_factor(crop: str) -> float:
    """CAPRI's grassland term in NUTNED_ (supply/supply_model.gms l. 1131-1135): the crop's need times SQRT(1 +
    p_technFact(Yield, A) + 0.2 $ GRAI - 0.2 $ GRAE), for every nutrient the crop has a need of; at the standard
    technology (p_technFact 0) SQRT(1.2) for intensive and SQRT(0.8) for extensive grassland, 1 for the other crops.
    The shift is parameter GRASS_NEED_YIELD_SHIFT. The data's need per ha (npk_crop_coefs_2030.csv) is the crop's own
    NITF/PHOF/POTF, without it (KNOWN_ISSUES K160; until 16 November 2026 GRAE and GRAI took the same need per kg)."""
    if crop not in ("GRAI", "GRAE"):
        return 1.0
    sh = float(param("GRASS_NEED_YIELD_SHIFT"))
    return float(np.sqrt(1.0 + (sh if crop == "GRAI" else -sh)))


def need_yield_factor(region: Optional[str], crop: str, y0: float, y: float, y_scen: Optional[float] = None,
                      nut: str = "N") -> float:
    """A crop's nutrient need per ha at yield y relative to its need at the base yield y0, CAPRI's rule.

    fert/fertned.gms sets the need per ha to MIN(cap, MAX(15, O_HP x need per t of main output + STRA x straw
    content)): the main-output part is linear in the yield (O_HP moves with it: capmod/define_inputs.gms after
    capmod/shift_yields.gms, and again after each yield update in supply/endog_yields.gms); the straw part moves with
    the scenario's yield shifts (shift_yields.gms scales every output of the crop, straw included) but not with the
    price-driven yields (endog_yields.gms updates the main output only). So with m and s the main and straw shares
    of the base need (NPKData.yield_shares; 0 for crops at the floor or cap):
        factor = (1 - m - s) + m x y / y0 + s x y_scen / y0
    y_scen: the yield before the price response (the scenario's shifted yield); None: y (no price response).
    The square root in CAPRI's NUTNED_ (SQRT(1 + p_technFact(yield, A) + 0.2 $ GRAI - 0.2 $ GRAE)) acts on the
    technology variants' yield factor and the grassland split (grass_need_factor, applied to the need itself), not
    on yield changes. A change that would cross the floor or the cap is
    not bounded here (the shares are fixed at the base). region: model or CAPRI region (None: (m, s) = (1, 0))."""
    if not (y0 > 0 and y > 0):
        return 1.0
    D = NPKData.get()
    cr = None
    if region:
        cr = region if any((region, n) in D.crop for n in NUTRIENTS) else D.capri_region(region)
    m, s = D.yield_shares(cr, nut, crop)
    ys = y if (y_scen is None or not y_scen > 0) else float(y_scen)
    return (1.0 - m - s) + m * (y / y0) + s * (ys / y0)

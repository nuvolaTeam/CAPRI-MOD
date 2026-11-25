"""CAPRI's crop nutrient balance for N, P and K, the data of the fertilisation block of the regional supply model in
CAPRI's form (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, fertDistCres_ and the inner fertiliser
distribution model; capri_mod/supply/capri_regional_nlp.py).

Data (tools/build/build_npk_balance_2030.py, from CAPRI's 2030 reference results):
  npk_crop_coefs_2030.csv        per CAPRI region, model crop and nutrient: need, contribution to the arable residue
                                 pool, permanent crops' own residues, CAPRI's mineral flow (kg/ha), and the need's
                                 additive part's share (add_share: v_cropNutNeedAddFact's, which the yields do not move)
  capri_crop_fertned_parts_2030.csv  fert/fertned.gms's arguments per CAPRI region, crop and nutrient in CAPRI's 2030
                                 simulation data (tools/build/build_capri_crop_n_coefs.py), for the need's yield factor
                                 (need_yield_factor)
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

import pandas as pd

from capri_mod.data.definitions import CAPRI_MEMBERS, capri_ms
from capri_mod.params import param
from capri_mod.supply.equations.fertned import FERTNED_PARTS, fertned_at_yields

NUTRIENTS = ("N", "P", "K")
#: CAPRI's nutrient of each (FNUT: NITF, PHOF, POTF)
FNUT_OF = {"N": "NITF", "P": "PHOF", "K": "POTF"}
#: the manure-per-head table of each nutrient (file stem; CAPRI's MANN, MANP, MANK)
MANURE_TABLES = {"N": "livestock_manure_n_coef", "P": "livestock_manure_p_coef", "K": "livestock_manure_k_coef"}


def manure_coef_table(nut: str, year=None) -> pd.DataFrame:
    """CAPRI's manure N, P2O5 or K2O per model head (kg; model region x model animal, empty where the model has no
    such animal) at a calibration year: the base year's (<stem>.csv: CAPRI's base-year totals over the model's heads,
    tools/build/build_livestock_output_coef.py, build_npk_balance_2030.py) or, at another market year, CAPRI's
    coefficients of that year in the baseline's folder (<stem>_<year>.csv; 2030: tools/build/
    build_livestock_manure_2030.py: CAPRI computes them from the simulation year's herd data before it solves,
    capmod.gms l. 1090, feed/req_or_man_fnc.gms, KNOWN_ISSUES K179). year: by default the run's
    (RunInputs.market_year, set by SupplyModule; the base year where unset). A year without its table is an error (no
    fall back to the base year's)."""
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
        self.crop = {(r, n): d.set_index("model_crop") for (r, n), d in c.groupby(["capri_region", "nutrient"])}
        # fertned.gms's arguments, {(CAPRI region, model crop, nutrient): FERTNED_PARTS values} (the model's crops are
        # CAPRI's one to one: CAPRI_MEMBERS)
        fp = inp.csv("capri_crop_fertned_parts_2030.csv", "environment")
        mc = {cs[0]: m for m, cs in CAPRI_MEMBERS.items() if len(cs) == 1}
        nut = {v: k for k, v in FNUT_OF.items()}
        self.fertned_parts = {(t.capri_region, mc.get(t.crop, t.crop), nut[t.nutrient]): tuple(float(getattr(t, k)) for k in FERTNED_PARTS)
                              for t in fp.itertuples(index=False)}
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

    def parts(self, capri_region: Optional[str], nut: str, crop: str) -> Optional[tuple]:
        """fert/fertned.gms's arguments of a crop (FERTNED_PARTS) in the region, else in its member state; None where
        CAPRI's data have none."""
        if capri_region:
            for r in (capri_region, capri_ms(capri_region)):
                v = self.fertned_parts.get((r, crop, nut))
                if v is not None:
                    return v
        return None

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


def need_yield_factor(region: Optional[str], crop: str, y0: float, y: float, y_scen: Optional[float] = None,
                      nut: str = "N") -> float:
    """A crop's nutrient per ha, DATA(crop, NITF | PHOF | POTF), at yield y relative to its value at the base yield y0:
    CAPRI's fert/fertned.gms rerun at the yields (capri_mod/supply/equations/fertned.py fertned_at_yields, on
    fertned's arguments of CAPRI's 2030 simulation data, capri_crop_fertned_parts_2030.csv).

    CAPRI reruns fertned.gms on the shifted yields of the scenario (capmod.gms l. 757, 772, 1084) and after each
    price-driven yield update (supply/endog_yields.gms l. 139, 148): DATA(crop, FNUT) = MIN(MAXF, MAX(15, O_HP x need
    per t of the main output + STRA x the straw's content)) (fert/fertned.gms l. 180-193), with O_HP the main output's
    yield (capmod/define_inputs.gms l. 80-92) and STRA the straw, which the scenario's yield shifts scale
    (capmod/shift_yields.gms l. 45-49) and the price-driven updates leave (endog_yields.gms l. 111-116). So the main
    output's part moves with y, the straw's with y_scen, and a crop at the floor or the cap stays there until the yields
    take it across. The same DATA(crop, FNUT) is NUTNED_'s need, e_EXPPRD's removal and e_BIOFIX's base
    (supply/supply_model.gms l. 1095-1137, 1417-1461), so this factor scales all three (environmental/nitrogen.py).
    The square root in NUTNED_ (SQRT(1 + p_technFact(yield, A) + 0.2 $ GRAI - 0.2 $ GRAE)) acts on the technology
    variants' yield factor and the grassland split (the latter already in the data's need per ha, CAPRI's reported
    2030 need per crop: KNOWN_ISSUES K190), not on yield changes.

    y_scen: the yield before the price response (the scenario's shifted yield); None: y (no price response).
    region: model or CAPRI region (the region's data, else its member state's). A crop or region without CAPRI's data:
    y / y0 (the rule of a crop without straw between the bounds). Until 20 November 2026 the factor was linear in the
    yields, with the main output's and straw's shares of the need taken from CAPRI's reported need (net of fixation,
    K191) and the bounds fixed at the base: legumes were classified at the floor (no response) and fruit, olives and
    textile crops at the floor and potassium at the cap were classified as moving (KNOWN_ISSUES K189)."""
    if not (y0 > 0 and y > 0):
        return 1.0
    parts = _fertned_parts(region, nut, crop)
    if parts is None:
        return y / y0
    ys = y if (y_scen is None or not y_scen > 0) else float(y_scen)
    n0 = fertned_at_yields(*parts, 1.0, 1.0, nitrogen=False)[0]
    if not n0 > 0:
        return 1.0
    return fertned_at_yields(*parts, y / y0, ys / y0, nitrogen=False)[0] / n0


def fout_yield_change(region: Optional[str], crop: str, y0: float, y: float, y_scen: Optional[float] = None,
                      nut: str = "N", AtmDep: float = 0.0) -> Optional[float]:
    """The change of a crop's deliveries to the soil per ha, DATA(crop, MANN | MANP | MANK) (kg/ha: e_CRESID's
    coefficient, supply/supply_model.gms l. 1393-1414), from the base yield y0 to yield y: CAPRI's fert/fertned.gms
    rerun at the yields (fertned_at_yields: the residues' share of the new DATA(crop, FNUT), at most 95% of it, plus
    the straw left, which the scenario's yield shifts move and the price-driven updates do not; as need_yield_factor).
    AtmDep: the region's deposition (kg N/ha; N only, as in CAPRI's MANN). None where CAPRI's data have no arguments
    for the crop (fallow and set-aside, without a main output)."""
    fy = fout_at_yields(region, crop, y0, y, y_scen, nut, AtmDep)
    return None if fy is None else fy[1][1] - fy[0][1]


def fout_at_yields(region: Optional[str], crop: str, y0: float, y: float, y_scen: Optional[float] = None,
                   nut: str = "N", AtmDep: float = 0.0) -> Optional[tuple]:
    """((DATA(crop, FNUT), DATA(crop, FOUT)) at the base yield y0, the same at yield y): fert/fertned.gms rerun at
    the yields (fertned_at_yields), kg/ha. y_scen, AtmDep: as fout_yield_change. None where CAPRI's data have no
    arguments for the crop."""
    parts = _fertned_parts(region, nut, crop)
    if parts is None or not y0 > 0:
        return None
    ys = y if (y_scen is None or not y_scen > 0) else float(y_scen)
    n_ = nut == "N"
    return (fertned_at_yields(*parts, 1.0, 1.0, AtmDep=AtmDep, nitrogen=n_),
            fertned_at_yields(*parts, max(y, 0.0) / y0, ys / y0, AtmDep=AtmDep, nitrogen=n_))


def _fertned_parts(region: Optional[str], nut: str, crop: str) -> Optional[tuple]:
    """fert/fertned.gms's arguments of a crop for a model or CAPRI region (NPKData.parts: the region's, else its
    member state's)."""
    D = NPKData.get()
    cr = None
    if region:
        cr = region if any((region, n) in D.crop for n in NUTRIENTS) else D.capri_region(region)
    return D.parts(cr, nut, crop)

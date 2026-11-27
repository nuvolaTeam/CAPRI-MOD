r"""The supply module's building of each region's data and model, and the calibration to the base (moved from
capri_mod/supply/supply_module.py as they were, 26 November 2026).
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
import multiprocessing
import os
import warnings
from pathlib import Path

from capri_mod.supply.capri_pmp import (
    share_term, ARABLE_ACTIVITIES,
)
from capri_mod.params import param, param_table
from capri_mod.units import M_N2O, M_N2O_N
from capri_mod.settings import setting, tri_state, current as _settings
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, FEED_ITEMS, NUTRIENTS, ACTIVITY_CLASSES, CROPS_ON_LAND, LAND_MARKET_TYPES, CATTLE_SPLITS,
)
from capri_mod.data.definitions import MS_CODE, capri_ms, IdentityMap, is_eu
from capri_mod.tableio import read_input
from capri_mod.supply import inputs as _inputs
from capri_mod.market.equations.set_prices import DATA_UVAG_Y
from capri_mod.supply.equations.greendeal.landscape import DATA_FALL_FLOOR
from capri_mod.supply.equations.greendeal.surptot import data_SURTOT_MAXS
from capri_mod.supply.equations.set_supply_bounds import v_actLevl_up_FALL
from capri_mod.supply.equations.ghgmiti import (
    p_ghgMiti_othImpact_EmiCalmin, p_ghgMiti_pmpParsqr, p_ghgMiti_pmpParsqr_saving, p_ghgMiti_relSubs)


from capri_mod.supply.regional_supply.pmp_calibrator import saving_slope  # noqa: E402
from capri_mod.supply.regional_supply.regional_model import RegionalSupplyModel  # noqa: E402
from capri_mod.supply.regional_supply.tables import RegionData, active_technologies, fert_side_value, overfert_factor  # noqa: E402




# ---------------------------------------------------------------------------
# SUPPLY MODULE COORDINATOR
# ---------------------------------------------------------------------------

def _region_nutrients(d: dict, region: str) -> pd.DataFrame:
    """CAPRI's fertiliser coefficients of the region's crops (NITF, PHOF, POTF; nutrient_coefs_regional.csv), crops
    CAPRI has nowhere in the member state left out (no fertiliser). Until 29 October 2026 a national table without
    builder (nutrient_coefs.csv) under them, which OFOD (OFAR and ROOF since 7 November 2026), SETA (VSET and FALL since 7 November 2026) and WINE kept in every region (KNOWN_ISSUES K100)."""
    reg = d["nutrients_regional"]
    if region not in reg.index.get_level_values(0):
        return pd.DataFrame(columns=["N", "P2O5", "K2O"], dtype=float)
    return reg.loc[region].astype(float).copy()


def _region_prices(d: dict, region: str) -> pd.Series:
    """National producer prices, overridden by CAPRI regional MPRI if present."""
    prices = d["producer_prices"].copy()
    reg = d.get("producer_prices_regional")
    if reg is not None and not reg.empty and region in reg.index:
        row = reg.loc[region]
        for act in row.index:
            v = row[act]
            if pd.notna(v) and v > 0:
                prices[act] = float(v)
    return UVAG_PACT_TO_Y(prices)


def UVAG_PACT_TO_Y(prices: pd.Series) -> pd.Series:
    """An activity whose main output is another model activity's product, and which has no price of its own, takes
    that product's unit value: CAPRI values an activity's outputs at their UVAG (reports/calc_inc_indic.gms TOOU, the
    supply model's revenue through SUPBAL_), and NECR's one output is OCRO (PACT_TO_Y NECR.OCRO, sets.gms l. 5411;
    PACT_TO_O NECR.(OCRO, MANN, MANP, MANK), l. 5221), measured as OCRO in constant prices (l. 136-137). The model
    keys its prices by activity: NECR takes OCRO's (the only model crop whose main output is another model crop's;
    GRAE and GRAI produce GRAS, not a model activity, and keep their own). Returns prices."""
    from capri_mod.data.definitions import CROPS
    for a, o in _pact_to_y().items():
        if a in CROPS and o in CROPS and a != o and o in prices.index and not (a in prices.index and pd.notna(prices[a])
                                                                and prices[a] > 0):
            prices[a] = float(prices[o])
    return prices


def _pact_to_y() -> dict:
    """CAPRI's PACT_TO_Y (capri_data/codes/capri/PACT_TO_Y.csv, build_code_lists): {activity: its main output}."""
    import csv
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "capri_data" / "codes" / "capri" / "PACT_TO_Y.csv"
    with open(p, newline="") as fh:
        return {r["pact"]: r["o"] for r in csv.DictReader(fh)}


def _region_costs(data: Dict, region: str) -> pd.Series:
    """Variable costs for one region, falling back to the EU mean.

    `variable_costs.csv` is a region x activity matrix. Earlier versions collapsed
    it to an EU mean before use, which meant every region was solved with identical
    costs and regional cost structure could not influence cropping decisions (nor
    scenario responses). This resolves the row for the region and fills any missing
    activity from the EU mean so no activity is left undefined.
    """
    regional = data.get("variable_costs_regional")
    eu_mean = data["variable_costs"]
    if regional is not None and region in regional.index:
        return regional.loc[region].combine_first(eu_mean)
    return eu_mean


def _capri_ms_targets(table, geo_map, kind: str, region: str):
    """CAPRI's Green Deal targets of the region (a row of table, keyed by the GDX files' Eurostat codes): the sum over
    the codes CAPRI maps to the region's member state (kind 'landscape': geo_to_ms_landscape; 'organic': geo_to_ms;
    p_setAsideTarget(ms), p_organicAreaTarget(ms) = sum(geo_to_ms(geo, ms), ...), then to NUTS 2 by map_rr). An absent
    record or a member state no code is mapped to gives 0, as CAPRI's sum does: Luxembourg (BL400000) takes Belgium's
    targets, Portugal and the regions outside the EU have none (greendeal_geo_to_ms.csv). None without the table."""
    from capri_mod.data.definitions import capri_ms

    if table is None:
        return None
    if geo_map is None:
        raise ValueError("the Green Deal targets need CAPRI's geo_to_ms maps (greendeal_geo_to_ms.csv)")

    geos = geo_map.index[geo_map[f"{kind}_ms"] == capri_ms(region)]
    return table.reindex(geos).sum(axis=0)


def _landscape_pp(d, region: str):
    """CAPRI's landscape target of the region (p_setAsideTarget, percentage points of UAA), or None without the table."""
    t = _capri_ms_targets(d.get("landscape_targets_ms"), d.get("greendeal_geo_to_ms"), "landscape", region)
    return None if t is None else float(t["landscape_pp"])




class RegionBuildBlock:
    """SupplyModule's region data and models (_build_region_data, _get_or_build_model, the PMP terms, the fertiliser
    options, calibrate_to_base)."""

    def _pmp_terms_for(self, d, region):
        """The region's PMP terms in the model's form for pmp_source and the market year: "capri2030" CAPRI's exported
        2030 terms (2030; at 2017 CAPRI's recipe at CAPRI's 2017 point), "recipe" capri-mod's own with CAPRI's recipe
        (2017 or 2030). The elasticity calibration ("elasticity") was removed on 28 October 2026 (the supply audit's finding S13, ARCHITECTURE_REFACTOR.md section 5.2)."""
        src = str(getattr(self, "pmp_source", "capri2030"))
        if src not in ("capri2030", "recipe"):
            raise ValueError(f"supply.pmp_source {src!r}: 'capri2030' or 'recipe' (the elasticity calibration was "
                             "removed on 28 October 2026; the supply audit's finding S13, ARCHITECTURE_REFACTOR.md section 5.2)")
        yr = _inputs.market_year(d)
        if src == "capri2030" and yr == 2030:
            return self._pmp_capri_parts_of((d.get("pmp_capri_2030") or {}).get(region))
        # CAPRI's own terms exist only for its 2030 calibration (pmppar_21730); at 2017 "capri2030" takes CAPRI's
        # recipe at CAPRI's 2017 point, as "recipe" does (23 October 2026: before, the elasticity calibration, which
        # needed literature elasticities where CAPRI has none - no proxies)
        if src == "recipe" or (src == "capri2030" and yr == int(_inputs.base_year())):
            return self._pmp_capri_parts_of(((d.get("pmp_recipe") or {}).get(yr) or {}).get(region))
        return None

    def _intensity_q_at(self, d, row, cols, part):
        """An intensity split's row with its curvature at the PMP terms' calibration point: at the 2030 market year
        with pmp_source "capri2030" or "recipe" (and `part` among pmp_capri_parts), q_<x> := q_<x>_capri2030 /
        q_<x>_recipe2030 (CAPRI's / the recipe's 2030 p_pmpQuadTechn of the two variants, tools/build/build_intensity_q_2030.py);
        else the base year's terms. The _capri2030 / _recipe2030 entries are removed either way."""
        if row is None:
            return row
        src = str(getattr(self, "pmp_source", "capri2030"))
        yr = _inputs.market_year(d)
        sfx = {"capri2030": "_capri2030", "recipe": "_recipe2030"}.get(src) if yr == 2030 else None
        if sfx and part not in tuple(getattr(self, "pmp_capri_parts", ())):
            sfx = None
        out = row.copy()
        if sfx:
            for c in cols:
                v = out.get(c + sfx)
                if v is not None and v == v and float(v) > 0:
                    out[c] = float(v)
        return out.drop([k for k in out.index if str(k).endswith(("_capri2030", "_recipe2030"))])

    def _uncalibrated(self, d, region) -> frozenset:
        """Activities of the region held at their level: those of the parts calibrated with PMP terms (pmp_capri_parts:
        crops, animals) without a positive own term at the calibration point, and those without any CAPRI value (no
        elasticity, no term: OOIL, OIND in every member state). CAPRI calibrates every activity with a level; where
        its calibration has no term for an activity of the model region, the activity is held. At the 2030 market year
        all such cells are at 0, as CAPRI's, where they have no level and no yield at "Y" and stay at 0 in its reference
        and Green Deal runs (register DEP-23, closed 23 November 2026; capri_mod/tests/test_pmp_held_cells.py; in the run
        of 28 October, r166, 71 cells still had a level, at most 2% of an activity's EU level). Until 28 October 2026 those cells took a curvature
        from their CAPRI elasticity (the elasticity calibration; the supply audit's finding S13, ARCHITECTURE_REFACTOR.md section 5.2)."""
        pmp = self._pmp_terms_for(d, region) or {}
        parts = tuple(getattr(self, "pmp_capri_parts", ()))
        anim = set(ANIMALS)
        held = {a for a in ALL_ACTIVITIES
                if (("animals" in parts) if a in anim else ("crops" in parts)) and not float(pmp.get((a, a), 0.0) or 0.0) > 0}
        prov = getattr(self, "elasticity_provenance", None)
        if prov is not None and not prov.empty and region in prov.index:
            held |= {a for a in prov.columns if prov.at[region, a] == "NO_CAPRI_VALUE" and (a, a) not in pmp}
        return frozenset(held)

    @staticmethod
    def _deposition_kg_ha(d, region):
        """CAPRI's deposition per ha of the region, p_nitrBalance(AtmDep) (n_deposition_regional.csv, the accounts' own
        source), or None without a row."""
        t = d.get("n_deposition_regional")
        if t is None or region not in getattr(t, "index", []):
            return None
        v = float(t.at[region, "deposition_kg_n_per_ha"])
        return v if v == v and v >= 0 else None

    def _price_transmission_for(self, d, region):
        """The region's member state's factors on the market's relative price change (CAPRI's absolute transmission,
        arm/set_prices.gms; K169), at the 2030 market year (the factors are CAPRI's 2030 reference's) with
        supply.price_transmission "capri"; None otherwise (the market's relative change)."""
        if str(_settings().get("supply.price_transmission")) != "capri" or _inputs.market_year(d) != 2030:
            return None
        return (d.get("price_transmission") or {}).get(capri_ms(region))

    def _techn_mix_for(self, d, region):
        """The region's crop technologies where its crops take CAPRI's 2030 PMP terms (pmp_source "capri2030" at the
        2030 market year, "crops" among pmp_capri_parts): the mix terms are that calibration's; None otherwise."""
        if str(getattr(self, "pmp_source", "capri2030")) != "capri2030" or _inputs.market_year(d) != 2030:
            return None
        if "crops" not in tuple(getattr(self, "pmp_capri_parts", ())):
            return None
        return (d.get("techn_mix") or {}).get(region)

    def _pesticides_for(self, d, region):
        """The region's calibrated pesticide cells and NoDamageFac (pesticide_par_2030.csv) with supply.pest_disagg
        "agg5" at the 2030 market year; None with "none". The module works on CAPRI's two technologies: with "agg5"
        and the technologies off (supply.crop_technologies false) the build stops."""
        mode = str(_settings().get("supply.pest_disagg"))
        if mode == "none":
            return None
        if mode != "agg5":
            raise ValueError(f"supply.pest_disagg {mode!r}: 'none' or 'agg5'")
        if _inputs.market_year(d) != 2030:
            raise ValueError("supply.pest_disagg 'agg5' needs the 2030 market year (pesticide_par_2030.csv)")
        if not bool(_settings().get("supply.crop_technologies")):
            raise ValueError("supply.pest_disagg 'agg5' needs CAPRI's two technologies (supply.crop_technologies)")
        t = d.get("pesticides")
        if t is None:
            raise ValueError("supply.pest_disagg 'agg5' needs pesticide_par_2030.csv")
        return t.get(region)

    def _pmp_capri_parts_of(self, g):
        """The region's CAPRI 2030 terms restricted to pmp_capri_parts (crops' matrix, animals' herd terms)."""
        if not g:
            return g
        parts = tuple(getattr(self, "pmp_capri_parts", ()))
        anim = set(ANIMALS)
        return {k: v for k, v in g.items()
                if (("animals" in parts) if k[0] in anim else ("crops" in parts))} or None

    def _get_or_build_model(self, region: str) -> RegionalSupplyModel:
        if region not in self._models:
            rd = self._build_region_data(region)
            # Use region-specific CAPRI PELA elasticities where available,
            # falling back to the EU-wide defaults for missing activities.
            eps = self.supply_elasticities.copy()
            if (not self.regional_elasticities.empty
                    and region in self.regional_elasticities.index):
                row = self.regional_elasticities.loc[region]
                eps = row.reindex(ALL_ACTIVITIES).fillna(eps)
            self._models[region] = RegionalSupplyModel(rd, eps, use_share_term=True)
            self._models[region].par.genet_key = getattr(self.par, "genetics_key", None)
            self._set_mitigation_scope_of(self._models[region])
        return self._models[region]

    def _build_region_data(self, region: str) -> RegionData:
        """Package all data for a region into a RegionData object."""
        d = self.data

        # Align yields across all activities
        yields_row = d["yields"].reindex([region])
        yields = yields_row.iloc[0] if not yields_row.empty else pd.Series(dtype=float)

        return RegionData(
            region_id=region,
            base_areas=d["areas"].loc[region] if region in d["areas"].index
                       else pd.Series(dtype=float),
            base_animals=d["animal_numbers"].loc[region]
                         if region in d["animal_numbers"].index
                         else pd.Series(dtype=float),
            # Regional CAPRI producer prices (MPRI) where available, falling
            # back to the national series. Prices and costs must come from the
            # same source: CAPRI's TOIN costs paired with the model's older
            # national prices leaves staple crops at an implausible loss,
            # because the two were internally consistent only with each other.
            producer_prices=_region_prices(d, region),
            variable_costs=_region_costs(d, region),
            yields=yields,
            land=d["land"].loc[region] if region in d["land"].index
                 else pd.Series(dtype=float),
            # CAPRI's NITF/PHOF/POTF are regional; the national constants they
            # replace lose real variation (nitrogen on soft wheat spans
            # 15-230 kg/ha across regions).
            nutrient_coefs=_region_nutrients(d, region),
            cap_premium=(d["cap_premium"].loc[region]
                         if d.get("cap_premium") is not None
                         and region in d["cap_premium"].index else None),
            cap_payments=d["cap_payments"].loc[region]
                         if region in d["cap_payments"].index
                         else pd.Series(dtype=float),
            livestock_output_coef=(
                d["livestock_output_coef"].loc[region]
                if d.get("livestock_output_coef") is not None
                and region in d["livestock_output_coef"].index else None),
            organic_yield_gap=d.get("organic_yield_gap"),
            organic_yield_gap_regions=d.get("organic_yield_gap_regions"),
            organic_yield_gap_groups=d.get("organic_yield_gap_groups"),
            landscape_target_pp=_landscape_pp(d, region),
            organic_targets_pp=_capri_ms_targets(d.get("organic_targets_ms"), d.get("greendeal_geo_to_ms"), "organic",
                                                 region),
            fert_partial_slack=(d.get("fert_partial_slack") or {}).get(region),
            organic_ngrp_class=(dict(zip(d["organic_ngrp_class"].index, d["organic_ngrp_class"].target))
                                if d.get("organic_ngrp_class") is not None else None),
            livestock_revenue_coef=(
                d["livestock_revenue_coef"].loc[region]
                if d.get("livestock_revenue_coef") is not None
                and region in d["livestock_revenue_coef"].index else None),
            livestock_product_value_coef=(
                d["livestock_product_value_coef"].loc[region]
                if d.get("livestock_product_value_coef") is not None
                and region in d["livestock_product_value_coef"].index else None),
            young_value_factor=(d.get("young_animal_value_factor") or {}).get(region),
            input_costs_ha=(d.get("plant_protection_cost") or {}).get(region),
            plap_capri_step=((d.get("plant_protection_capri_step") or {}).get(region)
                             if _inputs.market_year(d) == 2030 else None),
            input_coefs_2030=((d.get("input_coefs_2030") or {}).get(region)
                              if _inputs.market_year(d) == 2030 else None),
            crop_inputs_2030=((d.get("crop_inputs_2030") or {}).get(region)
                              if _inputs.market_year(d) == 2030 else None),
            sim_year=(int(d["market_year"]) if d.get("market_year") else None),
            cover_crops=(d["cover_crops"].loc[region] if d.get("cover_crops") is not None
                         and region in d["cover_crops"].index else None),
            winter_cover_share=(d.get("winter_cover_share") or {}).get(region),
            histosol=(d["histosol"].loc[region] if d.get("histosol") is not None
                      and region in d["histosol"].index else None),
            n_deposition_kg_ha=self._deposition_kg_ha(d, region),
            dairy_intensity=self._intensity_q_at(
                d, d["dairy_intensity"].loc[region] if d.get("dairy_intensity") is not None
                and region in d["dairy_intensity"].index else None, ("q_low", "q_high"), "animals"),
            cattle_intensity=(lambda ci: {a: self._intensity_q_at(d, s_, ("q_z", "q_b"), "animals") for a, s_ in ci.items()}
                              if ci else ci)((d.get("cattle_intensity") or {}).get(region)),
            genetics_effects=(d.get("genetics_effects") or {}).get(region),
            price_transmission=self._price_transmission_for(d, region),
            livestock_product_value_by_market_coef=(
                d["livestock_product_value_by_market_coef"].loc[region]
                if d.get("livestock_product_value_by_market_coef") is not None
                and region in d["livestock_product_value_by_market_coef"].index else None),
            livestock_cost_coef=(
                d["livestock_cost_coef"].loc[region]
                if d.get("livestock_cost_coef") is not None
                and region in d["livestock_cost_coef"].index else None),
            livestock_input_cost=(d.get("livestock_input_cost") or {}).get(region),
            livestock_output_value_coef=(
                d["livestock_output_value_coef"].loc[region]
                if d.get("livestock_output_value_coef") is not None
                and region in d["livestock_output_value_coef"].index else None),
            livestock_premium_coef=(
                d["livestock_premium_coef"].loc[region]
                if d.get("livestock_premium_coef") is not None
                and region in d["livestock_premium_coef"].index else None),
            capri_level_ratio=(
                d["capri_level_ratio"].loc[region]
                if d.get("capri_level_ratio") is not None
                and region in d["capri_level_ratio"].index else None),
            fodder_balance=(d.get("fodder_balance") or {}).get(region),
            # CAPRI's land market of its 2030 baseline calibration with CAPRI's 2030 PMP terms (K61), else the 2017 one
            land_market=((d.get("land_market_2030") or {}).get(region)
                         if _inputs.market_year(d) == 2030
                         and str(getattr(self, "pmp_source", "capri2030")) in ("capri2030", "recipe")
                         and "land" in tuple(getattr(self, "pmp_capri_parts", ()))
                         and (d.get("land_market_2030") or {}).get(region)
                         else (d.get("land_market") or {}).get(region)),
            # CAPRI's land rents at the market year's calibration point (tools/build/build_land_rents.py: 2030 reference,
            # 2017 results)
            land_rents=(((d.get("land_rents") or {}).get(_inputs.market_year(d)) or {}).get(region)),
            # CAPRI's PMP terms of its 2030 baseline calibration (K61): at the 2030 market year, with pmp_source "capri2030"
            pmp_capri=self._pmp_terms_for(d, region),
            techn_mix=self._techn_mix_for(d, region),
            pesticides=self._pesticides_for(d, region),
            uncalibrated=self._uncalibrated(d, region),
            livestock_feed_coef=(
                d["livestock_feed_coef"].loc[region]
                if d.get("livestock_feed_coef") is not None
                and region in d["livestock_feed_coef"].index else None),
        )


    # CAPRI's exponent in othImpact.NMIN (envind/ghgMiti.gms, p_fertEffCor): the parameter P_FERT_EFF_COR


    def _fert_techs(self, region):
        """CAPRI's fertiliser-efficiency options for this region (cropMiti, target N2OSYN).

        Data: CAPRI's miti_data_jul15 (the Green Deal runs' mitigation data,
        capri_data/2017/abatement/fert_options_jul15.csv, tools/build/build_fert_options_jul15.py);
        national entries, regional for VRT_SRUC (farm-size cost curve). Only CAPRI's active
        options (active_technologies.csv). Returns [(option, NMIN, S0, slope, s0, smax)], costs in
        EUR per TONNE of crop N need (GHG_Mit_Cost_ multiplies by mineral N x (1 + E)).

        envind/ghgMiti.gms:
          NMIN = (QEmitt(NOC) / QEmitt(option) - 1) ** p_fertEffCor; for NITR_INH QEmitt is set to
          0.9 x QEmitt(NOC) (l. 110) and, restMitFert on, NMIN <= (x + 0.1 - 1) ** p_fertEffCor
          (0 where x + 0.1 <= 1);
          regional maximum shares for options other than NITR_INH where crop need lies above
          precision farming's level (formula below);
          calibration: options without farm-size curves relSubs1/relSubs0 = 1.2/0.2, or 0.8/0 where
          the regional maximum share is below 1; slope = costParLin (relSubs1 - relSubs0) /
          (MaxShare - IniShare); VRT_SRUC keeps its data curvature costParSqr + pmpParSqr and relSubs0
          (0 where x + 0.1 - 1 <= NMIN(precfarm) and MaxShare < 1). S0 = relSubs0 x costParLin.
        The slope of the options without farm-size curves carries CAPRI's fertiliser-saving term (ghgMiti.gms
        l. 1016-1035, fert_slope_with_saving): the NLP form's fertilisation block holds the convex saving
        (N(m) = N0 / (1 + nmE m)), which the term offsets so that the base and the maximum share stay stationary."""
        def load(inp):
            tab = inp.csv("fert_options_jul15.csv", "abatement")
            to8 = IdentityMap()        # the model's regions are CAPRI's units: each its own CAPRI region
            return ({(r.region, str(r.option).upper()): r for r in tab.itertuples(index=False)}, to8)
        tab, to8 = _inputs.current().cached("fert_options_by_option", load)
        msc = capri_ms(region)
        r8 = to8.get(region)
        act_ = active_technologies()
        x = overfert_factor(region)
        xm = (x + param("OVERFERT_MARKUP")) if x is not None else None
        def q_of(opt, reg=None):
            rr = tab.get((reg, opt)) if reg else None
            rr = rr if rr is not None else tab.get((msc, opt))
            return rr
        pf = q_of("PRECFARM")
        q0 = float(pf.QEmitt_noc) if pf is not None and pf.QEmitt_noc == pf.QEmitt_noc else None
        qp = float(pf.QEmitt) if pf is not None else None
        out = []
        opts = {o for (r_, o) in tab if r_ == msc}
        for name in sorted(opts):
            if act_ is not None and name not in act_:
                continue
            sd = name in ("VRT_SRUC", "VRT_KTBL")
            rr = q_of(name, r8 if sd else None)
            if rr is None or q0 is None:
                continue
            k1 = float(rr.costParLin) if rr.costParLin == rr.costParLin else 0.0
            q = float(rr.QEmitt) if rr.QEmitt == rr.QEmitt else None
            if name == "NITR_INH":
                q = param("NITR_INH_EMISSION_FACTOR") * q0         # ghgMiti.gms l. 110
            if not k1 > 0 or q is None or not (0 < q < q0):
                continue
            nmin = (q0 / q - 1.0) ** param("P_FERT_EFF_COR")
            s0 = float(rr.IniShare) if rr.IniShare == rr.IniShare else 0.0
            smax = float(rr.MaxShare) if rr.MaxShare == rr.MaxShare else 0.0
            if smax <= 0 and sd:
                nat = tab.get((msc, name))
                smax = float(nat.MaxShare) if nat is not None and nat.MaxShare == nat.MaxShare else 0.0
            if name == "NITR_INH" and xm is not None:             # restMitFert: NI cannot go below need
                if xm <= 1.0:
                    nmin = 0.0
                elif xm < nmin ** (1.0 / param("P_FERT_EFF_COR")) + 1.0:
                    nmin = (xm - 1.0) ** param("P_FERT_EFF_COR")
            if name != "NITR_INH" and xm is not None and xm > 1.0 and qp is not None:
                e_need = q0 / xm
                if e_need > qp:
                    smax = min(smax, (q0 - min(q0, q + e_need - qp)) / (q0 - q))
            smax = max(smax, 0.0)
            if smax <= s0 or nmin <= 0:
                continue
            if sd:
                slope = float(rr.costParSqr if rr.costParSqr == rr.costParSqr else 0.0) \
                    + float(rr.pmpParSqr if rr.pmpParSqr == rr.pmpParSqr else 0.0)
                rs0 = float(rr.relSubs0) if rr.relSubs0 == rr.relSubs0 else 0.0
                nmin_pf = (q0 / qp - 1.0) ** param("P_FERT_EFF_COR") if qp else 0.0
                if xm is not None and xm - 1.0 <= nmin_pf and smax < 1.0:
                    rs0 = 0.0
                if slope <= 0:
                    continue
                out.append((name, nmin, rs0 * k1, slope, s0, smax))
            else:
                rs1, rs0 = p_ghgMiti_relSubs(smax, name == "NITR_INH", param("MITI_RELSUBS1"), param("MITI_RELSUBS0"),
                                             param("MITI_RELSUBS1_ADOPTED"))
                slope = p_ghgMiti_pmpParsqr(k1, rs1, rs0, smax, s0)
                if getattr(type(self), "fert_slope_with_saving", True):
                    # CAPRI's pmpParSqr (envind/ghgMiti.gms l. 1016-1035, the 'alternative approach'): the FOC is zero
                    # at the initial and the maximum share with the fertiliser saving valued at the member state's
                    # NITF price p: + nmE x p x ((1 + nmE m1)^-2 - (1 + nmE m0)^-2) / (m1 - m0), nmE = NMIN + EmiCalmin
                    pf = self._nitf_price_ms(msc)
                    nme = nmin + self._emi_cal_min(region, r8, name)
                    if pf:
                        slope += saving_slope(nme, pf, s0, smax)
                # CAPRI's curvature can be negative (precision farming, NMIN about 0.5): its total cost with the
                # endogenous fertiliser saving (convex: N(m) = N0 / (1 + nmE m)) has its stationary points at both
                # shares. The NLP form carries the saving through the fertilisation block and takes it as it is
                out.append((name, nmin, rs0 * k1, slope, s0, smax))
        return out

    #: CAPRI's fertiliser-option curvature with the fertiliser saving valued (ghgMiti.gms l. 1016-1035); False: without
    #: (this model before 24 October 2026)
    fert_slope_with_saving = setting("supply.fert_slope_with_saving")

    @staticmethod
    def _nitf_price_ms(ms8):
        """CAPRI's unit value of mineral N of the member state in the simulation year (DATA(ms,"UVAG","NITF","Y"),
        EUR/t; npk_region_2030.csv), or None."""
        from capri_mod.fert.npk import NPKData
        t = NPKData.get().region(ms8, "N") if ms8 else None
        v = getattr(t, "uvag_eur_t", None) if t is not None else None
        return float(v) if v is not None and v == v else None

    def _emi_cal_min(self, region, r8, tech):
        """CAPRI's EmiCalmin of a fertiliser option (envind/ghgMiti.gms l. 936-944): the base mineral N losses
        (p_emiloss of NETF: NH3, NOx, N2O, runoff) x the option's side effects (othImpact NH3SYN, NOXSYN, N2OSYN,
        NO3SRUN), raised to p_fertEffCor with its sign. 0 without side-effect data (CAPRI's literature effects are
        for the nitrification inhibitor)."""
        from capri_mod.supply import n_cascade as _nc
        from capri_mod.supply.equations.supply_model import n_flow as _nf
        sv = {it: fert_side_value(region, tech, it) for it in ("NH3SYN", "NOXSYN", "N2OSYN", "NO3SRUN")}
        if all(v is None for v in sv.values()):
            return 0.0
        _, G, _ = _nc.load()
        g = G.get(r8) or G.get(capri_ms(region)) or {}
        if not g:
            return 0.0
        L = _nf.netf(g, float(g.get("run_surf", 0.0)))
        return p_ghgMiti_othImpact_EmiCalmin([L["NH3"], L["NOX"], L["N2O"], L["RunTot"]],
                                             [sv["NH3SYN"], sv["NOXSYN"], sv["N2OSYN"], sv["NO3SRUN"]],
                                             param("P_FERT_EFF_COR"))

    def _manure_per_head(self, region, model):
        """Manure N per activity unit of the region's animals ({animal: the environmental module's organic N input
        of one unit}), the coefficients of CAPRI's ManureNPK_ / NUTNED_ terms; None when the region has no animal with
        manure. Until 29 October 2026 this was _manure_limit, which also returned a manure-application limit (170 kg
        N/ha or 1.001 x the base rate) for a row of capri-mod's own, removed (KNOWN_ISSUES K105), and returned None on
        any error, which dropped the manure terms without a word: an error now stops the solve."""
        if not hasattr(self.par, "env_for_surplus"):
            from capri_mod.environmental.environmental_module import EnvironmentalModule
            self.par.env_for_surplus = EnvironmentalModule(self.data)
            self.par.env_for_surplus.set_manure_trade(getattr(self.seen, "manure_trade_on", True))
        ylds = self.data["yields"].loc[region]
        man = {}
        for a in model.acts:
            if a in CROPS:
                continue
            nb = self.par.env_for_surplus.unit_nitrogen_balance(a, ylds, region)
            v = float(nb.get("n_organic_input", 0.0))
            if v > 0:
                man[a] = v
        return man or None

    #: CAPRI's baseline calibration (the projection layer at CAPRI's reference): at most this many correction rounds per baseline run
    BASE_CAL_ROUNDS = setting("projection.base_cal_rounds")
    #: CAPRI sets.gms l. 5606, FODF / OFAR, GRAS, ROOF, MAIF / (OFAR and ROOF the model's own since 7 November 2026)
    FODDER_ACTS = tuple(a for a, r in ACTIVITY_CLASSES.items() if r["fodder"] == "1")   # model_activity_classes.csv (
    # CAPRI's FODCRP: GRAS, MAIF, OFAR, ROOF)

    def calibrate_to_base(self, results: dict, reset: bool = False) -> float:
        """CAPRI's calibration of the supply models to the baseline (CAPMOD calibrates its PMP terms so that the
        baseline year's solution reproduces the projected activity levels): per region, the linear cost terms move by
        Q (x - x_target), the shift that makes the target optimal when the constraints' duals stay put, with the
        target the region's projected levels (the model's base levels). Returns the largest remaining drift, relative
        to the target (activities of at least 1 unit), before this round's correction; 0 once the rounds are used."""
        if reset:
            self.sv.base_cal_round = 0
            self.sv.base_cal_prev = {}
            self.sv.base_cal_stalled = set()
        rnd = int(getattr(self.sv, "base_cal_round", 0) or 0)
        worst = 0.0
        if rnd >= self.BASE_CAL_ROUNDS:
            return 0.0
        prev_r = getattr(self.sv, "base_cal_prev", None) or {}
        stalled = getattr(self.sv, "base_cal_stalled", None) or set()
        for region, res in (results or {}).items():
            if region in stalled:
                continue
            mo = self._models.get(region)
            if mo is None or getattr(mo, "Q", None) is None or getattr(mo, "f", None) is None:
                continue
            acts = list(mo.acts)
            xb = np.maximum(mo._base_levels().reindex(acts).fillna(0.0).values.astype(float), 0.0)
            act = getattr(res, "activities", None)
            if act is None:
                continue
            xs = np.asarray(pd.Series(act).reindex(acts).fillna(0.0).values, float)
            if not np.all(np.isfinite(xs)):
                continue
            d = xs - xb
            # fodder crops are held by the fodder balances (CAPRI's fodder equality): their level follows the herds'
            # fodder use, so their cost terms are not shifted (a shift there would do nothing while the balance binds
            # and act at once when a scenario loosens it)
            for j_, a_ in enumerate(acts):
                if a_ in self.FODDER_ACTS:
                    d[j_] = 0.0
            big = xb >= 1.0
            w_r = float(np.max(np.abs(d[big]) / xb[big])) if big.any() else 0.0
            # per region: a region whose drift a round does not reduce by 5% is left as it is (what the linear terms
            # cannot move); the others go on (before K36 one stalled region stopped the calibration everywhere)
            if os.environ.get("CAPRI_CAL_DEBUG"):
                _j = int(np.argmax(np.where(big, np.abs(d) / np.maximum(xb, 1e-9), 0.0)))
                print(f"[cal] round {rnd} {region} drift {w_r:.4f} at {acts[_j]} x {xs[_j]:.2f} target {xb[_j]:.2f}", flush=True)
            # A drift above the tolerance after a round that found the region within it is new drift (the prices moved
            # since), not a correction that failed: the region is corrected, not left (K120: in the "capri" coupling form the
            # baseline's first round finds every region at its target, so the next round's drift, 4% for Dresden's
            # pulses, stalled every region and the baseline stopped uncorrected)
            _tol_cal = float(_settings().get("projection.base_cal_tol"))
            if (rnd > 0 and region in prev_r
                    and w_r > float(_settings().get("projection.base_cal_stall_ratio")) * prev_r[region]
                    and not (prev_r[region] <= _tol_cal < w_r)):
                stalled.add(region)
                continue
            prev_r[region] = w_r
            worst = max(worst, w_r)
            mo.f = np.asarray(mo.f, float) + np.asarray(mo.Q, float) @ d
            mo.par.base_cal_shift = np.asarray(getattr(mo.par, "base_cal_shift", np.zeros(len(acts))), float) \
                + np.asarray(mo.Q, float) @ d
        self.sv.base_cal_round = rnd + 1
        self.sv.base_cal_prev, self.sv.base_cal_stalled = prev_r, stalled
        return worst

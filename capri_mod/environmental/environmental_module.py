"""
CAPRI Environmental Module
==========================
Computes environmental indicators from supply module outputs.

Indicators implemented:
  1. GHG emissions (CH4, N2O, CO2) following IPCC Tier 1/2 methodology
  2. Nitrogen balance (inputs - outputs = surplus, a pollution proxy)
  3. Phosphorus balance
  4. Land use indicators (UAA, crop diversity, HNV farmland)
  5. Pesticide use index (simplified)
  6. Ammonia emissions (NH3)
  7. Water use / irrigation demand

References:
  - IPCC (2019) Refinement to the 2006 GL for National GHG Inventories
  - EEA (2020) European Environment Agency nitrogen indicators
  - CAPRI Environmental Module documentation (Pérez-Domínguez et al. 2016)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional

from capri_mod.params import param, param_table
from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, NUTRIENTS, GHG_TYPES,
)


# ---------------------------------------------------------------------------
# IPCC FACTORS AS CAPRI USES THEM (envind/gases.gms; GHGInv/tables2006ipcc.gms)
# ---------------------------------------------------------------------------
# N2O from mineral and residue N: EF1 direct 1%, volatilised share 10% x EF4 1% (gases.gms N2OSYN, N2OCRO)
EF_SOIL_N2O_DIRECT   = param("EF_SOIL_N2O_DIRECT")
EF_SOIL_N2O_INDIRECT = param("EF_SOIL_N2O_INDIRECT")
# global warming potentials, AR4 (UNFCCC reporting, CAPRI p_globWarmPot)
GWP_CH4 = param("GWP_CH4")
GWP_N2O = param("GWP_N2O")
# Every other coefficient of the accounts is CAPRI's own regional data (manure N, manure N2O shares, ammonia
# shares, manure and enteric CH4 per head, liming and urea CO2, crop N, deposition). The IPCC Tier 1 and
# literature tables that stood here as fallbacks were removed (Sprint 9s, docs/SYNTHETIC_DATA_AUDIT.md): a
# region without CAPRI's data now fails loudly instead of taking a generic value.


@dataclass
class EnvironmentalIndicators:
    """Environmental indicators for a region or aggregate.

    The @dataclass decorator had gone missing, so constructing it with its
    fields raised a TypeError - the second of two errors that left every
    model run's environmental table empty.
    """
    region: str

    # GHG (kt CO2-equivalent)
    ghg_enteric: float = 0.0
    ghg_manure_ch4: float = 0.0
    ghg_manure_n2o: float = 0.0
    ghg_soil_n2o: float = 0.0
    ghg_histosol_n2o: float = 0.0
    #: of ghg_manure_n2o: the ammonia technologies' effect against their base shares (direct and
    #: through the loss cascade), kt CO2eq - JRC121368 Table 18 reports the same split
    ghg_manure_n2o_tech: float = 0.0
    ghg_residue_n2o: float = 0.0
    ghg_indirect_n2o: float = 0.0
    ghg_liming: float = 0.0
    ghg_urea: float = 0.0
    #: all items; non-CO2 (CH4 + N2O, JRC121368's "non-CO2 GHG"); CAPRI's GGWP, the emission tax's base
    #: (supply_model.gms GWPTOT_: CH4 + N2O + GCO2, GCO2 = liming only)
    ghg_total: float = 0.0
    ghg_non_co2: float = 0.0
    ghg_ggwp: float = 0.0

    # Nitrogen (kt N)
    n_mineral_input: float = 0.0
    n_organic_input: float = 0.0
    n_fixation: float = 0.0
    n_deposition: float = 0.0
    n_crop_uptake: float = 0.0
    n_animal_products: float = 0.0
    n_surplus: float = 0.0        # Gross N surplus (potential pollution)
    n_use_efficiency: float = 0.0  # NUE = outputs / inputs

    # Phosphorus (kt P2O5)
    p_input: float = 0.0
    p_uptake: float = 0.0
    p_surplus: float = 0.0

    # Ammonia (kt NH3)
    nh3_livestock: float = 0.0
    nh3_soils: float = 0.0
    nh3_total: float = 0.0

    # Land use (1000 ha)
    uaa_total: float = 0.0
    arable_land: float = 0.0
    permanent_crops: float = 0.0
    grassland: float = 0.0
    organic_area: float = 0.0

    # Biodiversity proxy
    shannon_crop_diversity: float = 0.0
    hnv_farmland_pct: float = 0.0     # High Nature Value farmland %

    def to_series(self) -> pd.Series:
        return pd.Series(self.__dict__)


# ---------------------------------------------------------------------------
# ENVIRONMENTAL MODULE
# ---------------------------------------------------------------------------

class EnvironmentalModule:
    """
    Computes environmental indicators from supply module outputs.

    Takes SupplyResult objects and nutrient data, returns
    EnvironmentalIndicators for each region.
    """

    def __init__(self, data: dict, fertilizer_module=None):
        self.data = data
        # Nutrient application rates (kg/ha per crop, N/P2O5/K2O). By default
        # these are CAPRI's loaded p_FertPerHa (data["nutrients"]). If a
        # calibrated FertilizerModule is supplied, its *derived* rates are used
        # instead — the same quantity, re-derived from removal x yield x
        # efficiency, which is what a re-based year (no ready-made file) needs.
        # The env module is agnostic to the source; it just reads application
        # rates, so its nitrogen-balance validation is unaffected by the switch.
        if fertilizer_module is not None:
            # Use the fert module's *derived* rates where it can produce them,
            # falling back to CAPRI's loaded p_FertPerHa for any crop/nutrient
            # the fert module does not cover (e.g. crops outside its calibration
            # set). This preserves the env module's full crop coverage while
            # sourcing application from the derivation wherever possible.
            loaded = data["nutrients"].copy()
            derived = fertilizer_module.per_crop_rates()
            merged = loaded.copy()
            for crop in derived.index:
                for col in derived.columns:
                    if col in merged.columns:
                        val = derived.at[crop, col]
                        # NaN = the fert module flagged this crop/nutrient as
                        # unit-inconsistent (e.g. GRAS); keep the loaded value.
                        if not (isinstance(val, float) and np.isnan(val)):
                            if crop in merged.index:
                                merged.at[crop, col] = val
                            else:
                                merged.loc[crop, col] = val
            self.nutrient_coefs = merged
            self._nutrient_source = "derived (fertilizer module) + loaded fallback"
        else:
            self.nutrient_coefs = data["nutrients"]
            self._nutrient_source = "loaded (CAPRI p_FertPerHa)"

    def _n_excretion(self, region: str, animal: str) -> float:
        cache = self.__dict__.setdefault("_nexc_cache", {})
        k = (region, animal)
        if k not in cache:
            cache[k] = self._n_excretion_uncached(region, animal)
        return cache[k]

    def _n_excretion_uncached(self, region: str, animal: str) -> float:
        """Manure N per head (kg), consistent with this model's herd units.

        First choice: CAPRI's 2017 regional manure N TOTAL for the activity
        divided by this model's herd (livestock_manure_n_coef.csv), built the
        same way as revenue per head. The previous source gave manure per CAPRI
        UNIT (animals fattened per year, 1,000 birds ...), while herds here are
        census stock, so EU totals were off by animal: bulls 0.17, heifers 0.10,
        calves 0.35, broilers 0.08, pigs 1.28, sheep and goats 1.49 of CAPRI's
        - near-cancelling in the EU total (0.93), but in the nitrogen constraint
        it put the burden on pigs and barely touched beef and poultry.
        """
        mc = self.data.get("livestock_manure_n_coef") if hasattr(self, "data") else None
        if mc is not None and region in mc.index and animal in mc.columns:
            import pandas as pd
            v = mc.at[region, animal]
            if pd.notna(v) and v > 0:
                return float(v)
        if mc is None:
            raise RuntimeError("livestock_manure_n_coef.csv is missing (tools/build_pig_split.py)")
        return 0.0          # CAPRI has no such animal in the region (no herd)

    def _ch4_per_head(self, kind: str, region: str, animal: str) -> float:
        """CAPRI's manure ("man") or enteric ("ent") CH4 per model head, kg (CH4MAN / CH4ENT: CAPRI total over the
        region's activities / the census herd; tools/build_ghg_coefs_2017.py; 2030 by CAPRI's reference factors).
        An animal CAPRI gives no such emission (poultry: no enteric CH4) has none."""
        tab = self.data.get("livestock_ch4%s_coef" % kind) if hasattr(self, "data") else None
        if tab is None:
            raise RuntimeError(f"livestock_ch4{kind}_coef.csv is missing (python tools/build_ghg_coefs_2017.py)")
        if region not in tab.index or animal not in tab.columns:
            return 0.0
        v = tab.at[region, animal]
        return float(v) if pd.notna(v) else 0.0

    def _co2_coefs(self, region: str):
        """(CO2 from liming, kg/ha of crop activity; urea share of mineral N), CAPRI's (crop_co2_coef.csv)."""
        tab = self.data.get("crop_co2_coef") if hasattr(self, "data") else None
        if tab is None:
            raise RuntimeError("crop_co2_coef.csv is missing (python tools/build_ghg_coefs_2017.py)")
        if region not in tab.index:
            return 0.0, 0.0
        return float(tab.at[region, "co2lim_kg_ha"]), float(tab.at[region, "urea_share"])

    def compute_ghg(
        self,
        activities: pd.Series,   # activity levels (1000 ha / 1000 heads)
        region: str,
        n_intensity: Optional[Dict[str, float]] = None,
        grass_shift: float = 0.0,
    ) -> Dict[str, float]:
        """
        Compute GHG emissions (kt CO2-eq) for a region. ``grass_shift``: grassland moved from
        intensive to extensive (1000 ha, Sprint 7a), whose fertiliser rate is GRAS's in proportion
        to CAPRI's need of each activity.

        Uses IPCC Tier 1 emission factors with EU-specific adjustments.
        """
        ghg = {g: 0.0 for g in GHG_TYPES}

        # 1. Enteric fermentation (CH4); nitrate in the ration: -10% per point of DM
        _ns = getattr(self, "_nitrate_share_now", None) or {}
        for animal in ANIMALS:
            heads = activities.get(animal, 0.0) * 1000  # convert 1000→heads
            _sf = float(((getattr(self, "_supp_ch4", None) or {}).get(region) or {}).get(animal, 1.0))
            ef    = self._ch4_per_head("ent", region, animal) * max(0.0, 1.0 - 10.0 * float(_ns.get(animal, 0.0))) * _sf
            ch4   = heads * ef / 1e6   # kt CH4
            # CATTLE FROM THE FEED MIX (CAPRI GWPCH4ENT_, envind/gases.gms): sum over feeds of
            # DM (t) x 1000 x GE (Mcal/kg DM) x 4.1868 x Ym / 55.65, in kt (/1e6)
            _fd = (getattr(self, "_feed_dm_now", None) or {}).get(animal)
            _fac = self._enteric_factors().get(animal) if _fd else None
            if _fd and _fac:
                _ctry = {"BE": "BL", "LU": "BL", "IE": "IR", "GR": "EL"}.get(str(getattr(self, "_region_now", ""))[:2],
                                                                        str(getattr(self, "_region_now", ""))[:2]) + "000000"
                _ge = _fac["ge"].get(_ctry) or _fac["ge"].get("EU")
                if _ge:
                    _kg = sum(float(dm_t) * 1000.0 * float(_ge.get(f, _ge.get("_mean", 0.0))) for f, dm_t in _fd.items())
                    ch4 = _kg * 4.1868 * _fac["ym"] / 55.65 / 1e6 * max(0.0, 1.0 - 10.0 * float(_ns.get(animal, 0.0))) * _sf
            ghg["CH4_ENT"] += ch4 * GWP_CH4   # kt CO2-eq

        # 2. Manure management (CH4 + N2O)
        for animal in ANIMALS:
            heads  = activities.get(animal, 0.0) * 1000
            n_excr = self._n_excretion(region, animal) * heads / 1e6  # kt N

            # CH4 from manure
            ef_ch4 = self._ch4_per_head("man", region, animal)
            ghg["CH4_MAN"] += (heads * ef_ch4 / 1e6) * GWP_CH4

            # N2O from manure: CAPRI's shares of manure N lost as N2O-N by stage - housing and
            # storage, application, grazing, leaching (gases.gms N2OMAN, N2OAPP, N2OGRA, N2OLEA;
            # tools/build_manure_n2o.py); the technologies' effects are applied in the accounts.
            # Indirect N2O from volatilised NH3 is its own item (N2O_IND). Without CAPRI's factors
            # for the region and animal: none (no herd; tests check every herd has them).
            _mf = self._manure_n2o_factor(region, animal)
            n2o_n = n_excr * (sum(_mf) if _mf is not None else 0.0)    # kt N2O-N
            n2o   = n2o_n * 44 / 28            # kt N2O
            ghg["N2O_MAN"] += n2o * GWP_N2O

        # 3. Agricultural soils (N2O)
        # N applied to soils = mineral fertiliser + organic (from manure) + fixation
        total_n_applied = 0.0
        for crop in CROPS:
            area = activities.get(crop, 0.0)
            n_rate = self.nutrient_coefs.at[crop, "N"] if (
                crop in self.nutrient_coefs.index and "N" in self.nutrient_coefs.columns
            ) else 0.0
            # fertiliser per ha follows the crop's N intensity (1 = base)
            n_rate = n_rate * float((n_intensity or {}).get(crop, 1.0))
            total_n_applied += area * n_rate / 1e3   # 1000 ha x kg/ha = t; /1e3 -> kt N
            # (was /1e6: soil N2O, liming and urea CO2 came out in Mt while every other gas is in kt,
            # so the GHG total left them out - 83 kt of soil N2O in the EU instead of 83 Mt)

        if grass_shift:
            dl = self.grass_intensity_delta(region) or {}
            r_g = self._base_mineral_rate(region, "GRAS")
            if r_g > 0 and "GRAS" in self.nutrient_coefs.index and "N" in self.nutrient_coefs.columns:
                total_n_applied += (grass_shift * float(self.nutrient_coefs.at["GRAS", "N"])
                                    * float(dl.get("mineral_rate", 0.0)) / r_g / 1e3)
        # Direct N2O from soils
        n2o_soil_n = total_n_applied * EF_SOIL_N2O_DIRECT
        ghg["N2O_SOIL"] += (n2o_soil_n * 44 / 28) * GWP_N2O

        # Indirect N2O (volatilisation path)
        n2o_indirect_n = total_n_applied * 0.10 * EF_SOIL_N2O_INDIRECT
        ghg["N2O_SOIL"] += (n2o_indirect_n * 44 / 28) * GWP_N2O

        # 4. Liming (CO2): CAPRI's coefficient per ha of every crop activity, grassland and fallow included
        # (gases.gms (16): the region's UAAR CO2LIM, kg CO2/ha; tools/build_ghg_coefs_2017.py)
        lim, urea_share = self._co2_coefs(region)
        ghg["CO2_LIME"] = sum(activities.get(c, 0.0) for c in CROPS) * lim / 1e3     # 1000 ha x kg/ha -> kt CO2

        # 5. Urea (CO2): mineral N x the member state's urea share x 44/28 (gases.gms (17)); compute_indicators
        # applies it to the balance's mineral N, as soil N2O
        ghg["CO2_UREA"] = total_n_applied * urea_share * 44.0 / 28.0

        return ghg

    def set_manure_trade(self, on: bool) -> None:
        """CAPRI's manure trade on or off for the run (CAPRIModel; the base trade shares count only when on)."""
        on = bool(on)
        if getattr(self, "manure_trade_on", True) != on:
            self.__dict__.pop("_sub_cache", None)
        self.manure_trade_on = on

    def _substitution(self, region):
        """(marginal availability/efficiency, manure-covered need per ha of crops at base).

        The first term is mineral N replaced per unit of manure N at the margin
        (_manure_marginal_factor, CAPRI's NUTNED_ with its endogenous availability).
        The second term is the base manure N available to crops (after export,
        plus imports) times availability/efficiency, spread per ha of base
        cropland: the part of the crops' need that manure covered at base.
        """
        cache = self.__dict__.setdefault("_sub_cache", {})
        if region in cache:
            return cache[region]
        out = None
        try:
            ratio = self._manure_marginal_factor(region)
            if ratio is not None:
                A = self.data["areas"]; H = self.data.get("animal_numbers")
                area0 = float(sum(float(A.at[region, c]) for c in A.columns if c in CROPS)) if region in A.index else 0.0
                man0 = 0.0
                if H is not None and region in H.index:
                    man0 = sum(float(H.at[region, a]) * self._n_excretion(region, a) for a in H.columns if a in ANIMALS)
                mt = self.data.get("manure_trade") if getattr(self, "manure_trade_on", True) else None
                if mt is not None and region in mt.index:
                    man0 *= max(0.0, 1.0 - float(mt.at[region, "export_share"]))
                    imp_ha = float(mt.at[region, "import_kg_n_per_ha"])
                else:
                    imp_ha = 0.0
                if area0 > 0 and ratio == ratio:
                    out = (ratio, ratio * (man0 / area0 + imp_ha))
        except Exception:
            out = None
        cache[region] = out
        return out

    def _gnb_row(self, region):
        """CAPRI's 2030 balance items for the CAPRI region of a model region (national where the
        region is not separate in CAPRI), from capri_gnb_components_2030.csv, or {}."""
        g = getattr(type(self), "_GNB_TOT", None)
        if g is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv"
            g = pd.read_csv(f).pivot_table(index="capri_region", columns="item", values="kg_n_per_ha") if f.exists() else pd.DataFrame()
            type(self)._GNB_TOT = g
        self._capri_crop_n(region)                         # builds the region map
        r8 = getattr(type(self), "_CROP_N_MAP", {}).get(region)
        if r8 is None or r8 not in g.index:
            r8 = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR"}.get(region[:2], region[:2]) + "000000"
        return g.loc[r8].to_dict() if r8 in g.index else {}

    #: CAPRI's slope of manure availability on manure applied per ha (fert/endoManAvail.gms)
    ENDO_MAN_AV_SLOPE = -0.0015

    def _manure_marginal_factor(self, region):
        """Mineral N replaced per unit of manure N applied, at the margin (CAPRI NUTNED_).

        NUTNED_ is an equality: crop need = mineral x (1 - losses) + manure x availability +
        residues. Manure distribution across crop groups is free, so a change in manure changes
        mineral N by availability / mineral efficiency whatever the minimum-mineral floors of
        individual groups (they bind only when manure grows). With CAPRI's endogenous availability
        (endoManAvFact, on in the Green Deal runs; fert/endoManAvail.gms) availability falls with
        manure per ha: g = g0 + b (m - m0), b = -0.0015 per kg N/ha, flattened so that g stays
        within [min(0.2, g0), max(0.999, g0)] between 0 and max(300, m0) kg/ha. The manure N
        available to crops is m g(m), whose derivative at base is g0 + b m0.
        Data: CAPRI 2030 reference, fertDist_excr / nutNed_excr_unavailable / fertDist_mine /
        nutNed_mine_loss per ha (capri_gnb_components_2030.csv); the earlier table
        (fertiliser_substitution_2030.csv) where those are missing."""
        row = self._gnb_row(region)
        g0 = eff = m0 = None
        try:
            ex = float(row.get("fertDist_excr_perha", float("nan")))
            un = float(row.get("nutNed_excr_unavailable_perha", float("nan")))
            mi = float(row.get("fertDist_mine_perha", float("nan")))
            lo = float(row.get("nutNed_mine_loss_gasRunTot_perha", float("nan")))
            if ex == ex and un == un and ex > 0:
                g0, m0 = 1.0 + un / ex, ex
            if mi == mi and lo == lo and mi > 0:
                eff = 1.0 + lo / mi
        except Exception:
            pass
        fs = self.data.get("fertiliser_substitution") if hasattr(self, "data") else None
        if fs is not None and region in fs.index:
            if g0 is None:
                g0 = float(fs.at[region, "manure_availability"])
            if eff is None:
                eff = float(fs.at[region, "mineral_efficiency"])
        if g0 is None or not eff or eff <= 0:
            return None
        if m0 is None or m0 <= 0:
            return g0 / eff
        b = self.ENDO_MAN_AV_SLOPE
        if g0 - m0 * b > max(0.999, g0):
            b = (g0 - max(0.999, g0)) / m0
        top = max(300.0, m0) - m0
        if top > 0 and g0 + top * b < min(0.2, g0):
            b = (min(0.2, g0) - g0) / top
        return max(g0 + b * m0, 0.0) / eff

    def _cached_row(self, key: str, region: str):
        """One region's row of a data table as a plain dict, cached (or None)."""
        cache = self.__dict__.setdefault("_row_cache", {})
        ck = (key, region)
        if ck not in cache:
            t = self.data.get(key) if hasattr(self, "data") else None
            cache[ck] = (t.loc[region].to_dict()
                         if t is not None and hasattr(t, "index") and region in t.index else None)
        return cache[ck]

    def _ncoef_n(self) -> dict:
        """nutrient_coefs['N'] as a dict, cached."""
        d = self.__dict__.get("_ncoef_n_cache")
        if d is None:
            nc = self.nutrient_coefs
            d = {c: nc.at[c, "N"] for c in nc.index} if "N" in getattr(nc, "columns", []) else {}
            self._ncoef_n_cache = d
        return d

    #: CAPRI crop -> model crop (several CAPRI crops pooled by level)
    _CAPRI_CROP = {"CORN": ("MAIZ",), "WINE": ("TWIN",), "OFIB": ("TEXT",), "GRAS": ("GRAE", "GRAI"),
                   "OFOD": ("OFAR", "ROOF"), "SETA": ("SETA", "FALL", "VSET"), "OLIV": ("OLIV", "TABO")}
    _CROP_N = None

    def _capri_crop_n(self, region):
        """{model crop: (removal, residues, fixation) kg N per ha} for this region from CAPRI's 2030
        reference, each item scaled so the region's totals equal CAPRI's EXPPRD and CRESID."""
        cls = type(self)
        if cls._CROP_N is None:
            import json as _json
            from pathlib import Path as _P
            root = _P(__file__).resolve().parents[2] / "capri_data"
            f = root / "2017" / "environment" / "capri_crop_n_coefs_2030.csv"
            g = root / "2017" / "environment" / "capri_gnb_components_2030.csv"
            cls._CROP_N = {}
            if f.exists() and g.exists():
                t = pd.read_csv(f)
                tot = pd.read_csv(g).pivot_table(index="capri_region", columns="item", values="kg_n_per_ha")
                c8 = _json.load(open(root / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]
                to8 = {}
                for k, lst in c8.items():
                    if not k.endswith("000000"):
                        for n2 in lst:
                            to8.setdefault(n2, k)
                # the shared map (tools/build_region_map.py: correspondence fixes, NUTS splits and merges)
                _rm = root / "shared" / "region_capri_map.csv"
                if _rm.exists():
                    for _r in pd.read_csv(_rm, dtype=str).fillna("").itertuples(index=False):
                        if _r.capri_region:
                            to8[_r.region] = _r.capri_region
                cls._CROP_N_MAP = to8
                for r8, g8 in t.groupby("capri_region"):
                    d = {row.crop: row for row in g8.itertuples(index=False)}
                    if "GRAE" in d or "GRAI" in d:
                        d.pop("GRAS", None)                       # aggregate of GRAE + GRAI
                    lv = sum(float(x.levl) for x in d.values())
                    if r8 not in tot.index or lv <= 0:
                        continue
                    # Removal key per crop: the crop's NITF in CAPRI's results is its need NET of
                    # biological fixation (NUTNED_: retention x (1 - fBNF) x over-fertilisation), while
                    # fixation is fBNF of the gross need (JRC96482, eq. 1: Nbiofix = NITF x LEVL x fBNF,
                    # fBNF 75% for soya and pulses, 5-17% for grass). Gross need = NITF + fixation per ha
                    # (pulses: 52 + 149 kg/ha in Saxony-Anhalt, removal 4x the net figure).
                    def _gross(x):
                        fx = float(x.biofix_t) * 1000.0 / float(x.levl) if (x.biofix_t == x.biofix_t and float(x.levl) > 0) else 0.0
                        return float(x.nitf) + fx
                    sx = sum(float(x.levl) * _gross(x) for x in d.values())
                    # NCRD = "N from crop residues and atmospheric deposition, kg/ha" (sets.gms);
                    # e_CRESID: CRESID + ATMOSD = sum levl x NCRD, so residues = NCRD - deposition
                    dep = float(tot.at[r8, "ATMOSD"]) if "ATMOSD" in tot.columns else 0.0
                    res_ha = lambda x: max(0.0, (float(x.ncrd) if x.ncrd == x.ncrd else 0.0) - dep) \
                        if (x.ncrd == x.ncrd and float(x.ncrd) > 0) else 0.0
                    sr = sum(float(x.levl) * res_ha(x) for x in d.values())
                    uaa = lv
                    ke = float(tot.at[r8, "EXPPRD"]) * uaa / sx if sx > 0 and "EXPPRD" in tot.columns else 1.0
                    kr = float(tot.at[r8, "CRESID"]) * uaa / sr if sr > 0 and "CRESID" in tot.columns else 0.0
                    out = {}
                    from capri_mod.data.definitions import CROPS as _CR
                    for mc in _CR:
                        src = [d[c] for c in cls._CAPRI_CROP.get(mc, (mc,)) if c in d]
                        L = sum(float(x.levl) for x in src)
                        if L <= 0:
                            continue
                        rem = sum(float(x.levl) * _gross(x) for x in src) / L * ke
                        res = sum(float(x.levl) * res_ha(x) for x in src) / L * kr
                        fix = sum((float(x.biofix_t) if x.biofix_t == x.biofix_t else 0.0) for x in src) * 1000.0 / L
                        out[mc] = (rem, res, fix)
                    # CAPRI's two grassland activities on their own (the model's GRAS pools
                    # them; grass_intensity_delta() needs each)
                    for gc in ("GRAE", "GRAI"):
                        if gc in d and float(d[gc].levl) > 0:
                            x = d[gc]
                            out[gc] = (_gross(x) * ke, res_ha(x) * kr,
                                       (float(x.biofix_t) if x.biofix_t == x.biofix_t else 0.0) * 1000.0 / float(x.levl))
                    cls._CROP_N[r8] = out
        to8 = getattr(cls, "_CROP_N_MAP", {})
        r8 = to8.get(region)
        if r8 is None or r8 not in cls._CROP_N:
            nc = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR"}.get(region[:2], region[:2]) + "000000"
            r8 = nc
        res = cls._CROP_N.get(r8)
        ov = self.__dict__.get("_grass_override")
        if ov and res and ov in res:
            res = dict(res); res["GRAS"] = res[ov]
        return res

    #: CAPRI (eq. 5.10, fertiliser distribution): "crop residues can be re-distributed among crop
    #: groups for annual arable crops but not for grassland and permanent crops, where it stays
    #: with the crop that produced it"
    #: crops whose own residues cover their own need, CAPRI's permanent crop groups (supply/define_ngrp_sets.gms
    #: PERM_NGRP: GRAS, and PERM = OLIV, TABO, TAGR, TWIN, CITR, APPL); every other crop draws on the arable residue
    #: pool (fertDistCres_). Other fruit (VEGE in CAPRI) and nurseries (OAFC) were here until Sprint 9e.
    OWN_RESIDUE_CROPS = frozenset({"GRAS", "APPL", "CITR", "TAGR", "WINE", "OLIV"})

    def _base_mineral_rate(self, region, crop):
        """Base mineral N per ha of a crop: CAPRI's regional rate, else the EU table."""
        _regn = self._cached_row("mineral_n_regional", region)
        rate = None
        if _regn is not None and crop in _regn:
            v = _regn[crop]
            if v == v and v > 0:
                rate = float(v)
        if rate is None:
            rate = float(self._ncoef_n().get(crop, 0.0) or 0.0)
        ov = self.__dict__.get("_grass_override")
        if ov and crop == "GRAS":
            # one of CAPRI's grassland activities: the GRAS rate in proportion to its need
            # (removal net of fixation) over the pooled GRAS need
            self.__dict__["_grass_override"] = None
            try:
                cn = self._capri_crop_n(region) or {}
            finally:
                self.__dict__["_grass_override"] = ov
            if ov in cn and "GRAS" in cn:
                w_ov = max(cn[ov][0] - cn[ov][2], 0.0)
                w_g = max(cn["GRAS"][0] - cn["GRAS"][2], 0.0)
                if w_g > 0:
                    rate *= w_ov / w_g
        return rate

    def grass_intensity_delta(self, region, n_intensity=None) -> dict:
        """Balance change (t N per 1000 ha) of moving grassland from CAPRI's intensive activity
        GRAI to its extensive GRAE: the unit balance of a hectare of GRAE minus one of GRAI, each
        with its own CAPRI removal, residues and fixation and its share of the GRAS mineral rate by
        need, at base yield; manure and residue credits keep the base distribution by need.
        Used for the supply model's extensification column and for the accounts, so the two agree."""
        cache = self.__dict__.setdefault("_grass_delta_cache", {})
        key = (region, tuple(sorted((n_intensity or {}).items())))
        if key in cache:
            return cache[key]
        cn = self._capri_crop_n(region) or {}
        if "GRAE" not in cn or "GRAI" not in cn:
            cache[key] = None
            return None
        self._need_base(region); self._residue_availability(region)      # base caches first
        y0 = self._cached_row("yields", region) or {}
        out = {}
        try:
            for gc in ("GRAE", "GRAI"):
                self.__dict__["_grass_override"] = gc
                out[gc] = self.compute_nitrogen_balance({"GRAS": 1.0}, y0, region, n_intensity)
        finally:
            self.__dict__["_grass_override"] = None
        d = {k: float(out["GRAE"].get(k, 0.0)) - float(out["GRAI"].get(k, 0.0))
             for k in out["GRAE"] if isinstance(out["GRAE"].get(k), (int, float))}
        rates = []
        for gc in ("GRAE", "GRAI"):
            self.__dict__["_grass_override"] = gc
            try:
                rates.append(self._base_mineral_rate(region, "GRAS"))
            finally:
                self.__dict__["_grass_override"] = None
        d["mineral_rate"] = rates[0] - rates[1]
        cache[key] = d
        return d

    def _need_weight(self, region, crop):
        """A crop's N need per ha at base yield, the key by which CAPRI distributes manure and
        pooled residues (eq. 5.10: need = retention x (1 - biological-fixation share) x
        over-fertilisation): CAPRI's removal net of fixation; the mineral rate where CAPRI has
        no coefficient."""
        cn = self._capri_crop_n(region)
        if cn and crop in cn:
            return max(float(cn[crop][0]) - float(cn[crop][2]), 0.0)
        return self._base_mineral_rate(region, crop)

    def _need_base(self, region):
        """(base crop need weight M0 = sum of base area x base mineral rate, base cropland A0).

        CAPRI spreads available manure and residue N over crops BY NEED (NUTNED_,
        fertDistExcr_); the base mineral rate is the model's crop-need weight, so a hectare
        of fallow (no need, no fertiliser) receives no manure or residue credit."""
        cache = self.__dict__.setdefault("_need_base_cache", {})
        if region in cache:
            return cache[region]
        M0 = A0 = Ma = 0.0
        A = self.data["areas"] if hasattr(self, "data") else None
        if A is not None and region in A.index:
            for c in CROPS:
                if c in A.columns:
                    a = float(A.at[region, c] or 0.0)
                    if a > 0:
                        A0 += a
                        M0 += a * self._need_weight(region, c)
                        if c not in self.OWN_RESIDUE_CROPS:
                            Ma += a * self._need_weight(region, c)
        cache[region] = (M0, A0, Ma)
        return M0, A0, Ma

    def _residue_availability(self, region):
        """(availability of residue N to crops, base ARABLE residue N per unit of arable crop need)."""
        cache = self.__dict__.setdefault("_res_av_cache", {})
        if region in cache:
            return cache[region]
        av, r0 = 0.0, 0.0
        cn = self._capri_crop_n(region) or {}
        try:
            from pathlib import Path as _P
            g = getattr(type(self), "_GNB_TOT", None)
            if g is None:
                f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv"
                g = pd.read_csv(f).pivot_table(index="capri_region", columns="item", values="kg_n_per_ha")
                type(self)._GNB_TOT = g
            to8 = getattr(type(self), "_CROP_N_MAP", {})
            r8 = to8.get(region)
            if r8 is None or r8 not in g.index:
                r8 = {"GR": "EL", "BE": "BL", "LU": "BL", "IE": "IR"}.get(region[:2], region[:2]) + "000000"
            if r8 in g.index:
                pool = float(g.at[r8, "CRESID"]) + float(g.at[r8, "ATMOSD"])
                lost = -float(g.loc[r8].get("nutNed_cres_unavailable_perha", 0.0) or 0.0) \
                       - float(g.loc[r8].get("nutNed_cres_loss_gasRunTot_perha", 0.0) or 0.0)
                if pool > 0 and lost == lost:
                    av = min(max(1.0 - lost / pool, 0.0), 1.0)
            areas = self.data["areas"].loc[region] if region in self.data["areas"].index else None
            _, _, Ma = self._need_base(region)
            if areas is not None and Ma > 0:
                R = sum(float(areas.get(c, 0.0) or 0.0) * cn[c][1] for c in cn
                        if c not in self.OWN_RESIDUE_CROPS)
                r0 = R / Ma
        except Exception:
            av, r0 = 0.0, 0.0
        cache[region] = (av, r0)
        return av, r0

    def unit_nitrogen_balance(self, activity: str, yields, region: str,
                              n_intensity: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """compute_nitrogen_balance for ONE unit of one activity, memoised. The balance of {a: 1} reads only the
        activity's own yield, its own intensity factor and the "__credit__" factor (plus static data and the manure
        trade setting), so those form the key; the supply models ask for it hundreds of thousands of times per run."""
        y = yields.get(activity) if hasattr(yields, "get") else None
        mi = n_intensity or {}
        key = (region, activity, None if y is None else float(y), mi.get(activity), mi.get("__credit__"),
               bool(getattr(self, "manure_trade_on", True)))
        memo = self.__dict__.setdefault("_unit_nb_memo", {})
        r = memo.get(key)
        if r is None:
            r = self.compute_nitrogen_balance({activity: 1.0}, yields, region, n_intensity)
            memo[key] = r
        return dict(r)

    def compute_nitrogen_balance(
        self,
        activities: pd.Series,
        yields: pd.Series,
        region: str,
        n_intensity: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Compute soil nitrogen balance (OECD/Eurostat methodology).

        N inputs:
          - Mineral fertilizer
          - Organic manure
          - Biological N fixation (legumes)
          - Atmospheric deposition
          - Other organic inputs

        N outputs:
          - Crop N uptake (= yield × N content coefficient)
          - N in animal products

        Surplus = Inputs - Outputs (kg N / ha)
        """
        n = {}

        # --- Inputs ---
        # Mineral fertilizer (from nutrient coefficients × area)
        n_mineral = 0.0
        # CAPRI reports mineral (NMIN) and manure (NMAN) nitrogen separately per
        # activity and region; their EU totals, 9.47 and 5.89 Mt N, match the
        # real ~10.8 and ~7. Regional rates matter: a single EU-wide table gave
        # German regions EU-average fertilisation and a surplus of 14 kg N/ha
        # where Germany's is among Europe's highest.
        _reg_n = self.data.get("mineral_n_regional") if hasattr(self, "data") else None
        _sub = self._substitution(region)
        # fixed per-region data, cached as plain dicts (identical values; pandas
        # row and cell access dominated the cost of this function)
        _ybase = self._cached_row("yields", region)
        _regn = self._cached_row("mineral_n_regional", region)
        _ncN = self._ncoef_n()
        if hasattr(activities, "to_dict"):
            activities = activities.to_dict()
        if hasattr(yields, "to_dict"):
            yields = yields.to_dict()
        n_mineral_plain = 0.0
        n_need_manure_part = 0.0
        n_need_w = 0.0                      # crop need weight: base mineral rate x intensity x sqrt(yield)
        _M0, _A0, _ = self._need_base(region) if _sub is not None else (0.0, 0.0, 0.0)
        _sub_w = (_sub[1] * _A0 / _M0) if (_sub is not None and _M0 > 0) else 0.0
        # Crop factors (n_intensity[crop]) = organic share x technology factor scale the crop's
        # own mineral rate; the parts of need covered by manure and residues scale with the
        # technology factor alone ("__credit__"). Organic land uses no mineral N (CAPRI
        # organic_minfert_redu.gms) but its need is still met by manure and residues, so mineral
        # N falls by the organic share of the MINERAL rate - scaling the whole need cut it by up
        # to twice the mineral actually applied where manure covers most need.
        _fc = float((n_intensity or {}).get("__credit__", 1.0))
        for crop in CROPS:
            area = activities.get(crop, 0.0)
            _m = float((n_intensity or {}).get(crop, 1.0))
            # need grows with the square root of yield (CAPRI NUTNED_)
            _sq = 1.0
            if _sub is not None and area > 0 and _ybase is not None:
                _y0 = float(_ybase.get(crop, 0.0)); _y = float(yields.get(crop, _y0)) if hasattr(yields, "get") else _y0
                if _y0 > 0 and _y > 0:
                    _sq = (_y / _y0) ** 0.5
            rate = self._base_mineral_rate(region, crop) if area > 0 else 0.0
            n_mineral_plain += area * rate * _m
            n_mineral += area * rate * _m * _sq
            _w = self._need_weight(region, crop) if (area > 0 and _sub is not None) else 0.0
            if crop not in self.OWN_RESIDUE_CROPS:
                n_need_w += area * _w * _fc * _sq
            if _sub is not None and area > 0:
                # the manure-covered part of need, spread over crops BY NEED (CAPRI
                # fertDistExcr_): sub[1] per ha of base cropland = sub[1] x A0 / M0 per
                # unit of need; fallow carries none
                n_need_manure_part += area * _w * _fc * _sq * _sub_w

        # Organic N from manure
        n_organic = 0.0
        for animal in ANIMALS:
            # Activity levels are in 1000 head and _n_excretion returns kg N per
            # head per year (DCOW ~105, matching the literature 100-120), so the
            # product is already in the same 1000-kg-N unit as every other term
            # here (deposition is area in 1000 ha x 20 kg/ha). The previous
            # `heads * 1000 ... / 1e6` divided by a further 1000 and left manure
            # N at effectively ZERO in the balance — FR10 showed 0.0 kg N/ha of
            # organic input against a real EU average near 55.
            heads_1000 = activities.get(animal, 0.0)
            n_excr = self._n_excretion(region, animal)
            n_organic += heads_1000 * n_excr
        # MANURE TRADE (CAPRI's manExportOrAppl_): exporting regions keep
        # (1 - export share) of their manure N, importing regions receive
        # manure spread over their cropland. Shares from CAPRI's 2030 reference
        # (tools/build_manure_trade_base.py: 1.2 Mt N traded between regions).
        # only where the run trades manure (CAPRI's manureTradeNew; a scenario setting held for its baseline: without
        # it, as JRC121368's CAPRI, every region keeps all its manure, Sprint 9j)
        _mt = self.data.get("manure_trade") if (hasattr(self, "data") and getattr(self, "manure_trade_on", True)) else None
        _exp_sh, _imp_ha = 0.0, 0.0
        if _mt is not None and region in getattr(_mt, "index", []):
            _exp_sh = float(_mt.at[region, "export_share"])
            _imp_ha = float(_mt.at[region, "import_kg_n_per_ha"])
        n_organic *= max(0.0, 1.0 - _exp_sh)

        # CAPRI's crop removal, crop residues and biological fixation per crop and region
        # (supply_model.gms e_EXPPRD, e_CRESID, e_BIOFIX; 2030 reference coefficients,
        # capri_crop_n_coefs_2030.csv), scaled with the current yield over the model's own
        # base yield (CAPRI multiplies by its yield factors). Replaces the hard-coded N
        # contents per tonne (wheat 20 kg/t, default 10) and fixation rates, which removed
        # 40% more N than CAPRI's net removal and left out the residue input.
        _cn = self._capri_crop_n(region)
        n_residues = 0.0
        _own_need = _own_res = 0.0
        n_crop_uptake_c = n_fix_c = 0.0
        if _cn:
            for crop in CROPS:
                area = activities.get(crop, 0.0)
                co = _cn.get(crop)
                if area <= 0 or co is None:
                    continue
                yr = 1.0
                if _ybase is not None:
                    _y0 = float(_ybase.get(crop, 0.0) or 0.0)
                    _y = float(yields.get(crop, _y0) or 0.0) if hasattr(yields, "get") else _y0
                    if _y0 > 0 and _y >= 0:
                        yr = _y / _y0
                n_crop_uptake_c += area * co[0] * yr
                n_residues += area * co[1] * yr
                if crop in self.OWN_RESIDUE_CROPS:
                    # own residues cover own need: base credit x intensity x sqrt(yield) on the
                    # need side, residues actually left on the credit side
                    _fc_ = float((n_intensity or {}).get("__credit__", 1.0))
                    _own_need += area * co[1] * _fc_ * (yr ** 0.5 if yr > 0 else 0.0)
                    _own_res += area * co[1] * yr
                n_fix_c += area * co[2] * yr

        # Biological N fixation: CAPRI's per crop and region (BIOFIX, _capri_crop_n)
        if not _cn and any(activities.get(c, 0.0) > 0 for c in CROPS):
            raise RuntimeError(f"no CAPRI crop N coefficients for {region} (capri_crop_n_coefs_2030.csv)")
        n_fixation = n_fix_c

        # Atmospheric deposition (~20 kg N/ha/year EU average)
        total_uaa = sum(activities.get(a, 0.0) for a in CROPS)
        # Atmospheric deposition per region from CAPRI's 2030 reference
        # (EMEP-based; median 10 kg N/ha, 1-48 by region), replacing a flat
        # 20 kg N/ha that put EU deposition at 1.8x CAPRI's.
        _dep = self.data.get("n_deposition_regional") if hasattr(self, "data") else None
        _dep_ha = 0.0
        if total_uaa > 0 and (_dep is None or region not in getattr(_dep, "index", [])):
            raise RuntimeError(f"no CAPRI deposition for {region} (n_deposition_regional.csv)")
        if _dep is not None and region in getattr(_dep, "index", []):
            _v = float(_dep.at[region, "deposition_kg_n_per_ha"])
            if _v == _v and _v >= 0:
                _dep_ha = _v
        n_deposition = total_uaa * _dep_ha

        n_manure_import = sum(activities.get(a, 0.0) for a in CROPS) * _imp_ha
        # MINERAL FERTILISER FOLLOWS CROP NEED (CAPRI supply_model.gms NUTNED_):
        # mineral N covers what manure, residues and deposition leave of the
        # crops' need, each net of losses. Linearised around the base: crops
        # carry the share of their need that manure covered at base, and the
        # manure actually available displaces mineral N at
        # availability / efficiency (median 0.44 / 0.91 across CAPRI regions).
        # At base the total equals the previous mineral input exactly. When
        # herds shrink mineral N rises; when cropland shrinks it falls by the
        # crop's full need. A region total is clipped at zero; single-animal
        # unit balances are not - their negative term IS the displacement.
        # Fertiliser technologies raise the efficiency of MINERAL N (CAPRI: mineral x (1 + E)
        # covers what need leaves after manure and residues), so they shrink the mineral N
        # net of those credits: need and credits scale with the same factor ("__credit__", the
        # regional technology factor; the crops' own factors carry it on their mineral rate).
        # Scaling only the need side made a technology save mineral N it never displaced -
        # up to 2x the mineral actually applied where manure and residues cover most need.
        if _sub is not None:
            n_mineral += n_need_manure_part - _fc * _sub[0] * (n_organic + n_manure_import)
            if total_uaa > 0:
                n_mineral = max(n_mineral, 0.0)
        # (after the manure clip: a linear term, so one crop's unit balance carries its own
        # displacement, as an animal's carries its manure's)
        # CROP RESIDUES displace mineral N as manure does (CAPRI NUTNED_: residue and deposition N
        # count towards crop need at their availability, 1 - nutNed_cres_unavailable / (CRESID +
        # ATMOSD), ~0.75). Arable residues are pooled and spread over arable crops by need (at
        # base every arable crop carries the pool's credit in proportion to its need, fallow
        # none); grassland and permanent crops keep their own (CAPRI eq. 5.10). A crop mix or
        # yield that leaves more residues lowers the mineral N needed.
        if _cn and _sub is not None:
            _ar, _r0 = self._residue_availability(region)
            if _ar > 0:
                n_mineral += _ar * (_r0 * n_need_w - _fc * (n_residues - _own_res))   # arable pool
                n_mineral += _ar * (_own_need - _fc * _own_res)                       # grass, permanent
        total_inputs = n_mineral + n_organic + n_fixation + n_deposition + n_manure_import + n_residues

        # --- Outputs ---
        # Crop N uptake: CAPRI's per crop and region (_capri_crop_n)
        n_crop_uptake = n_crop_uptake_c
        # N in livestock products
        n_animal_output = n_organic * 0.25  # ~25% of excreted N is in products

        # GROSS NITROGEN BALANCE outputs are crop and fodder removals only
        # (OECD/Eurostat; CAPRI's land and soil budgets, Koeble et al. 2026,
        # Table 4). Excretion already excludes the N retained in animal
        # products, so subtracting a share of it double-counted - and made every
        # animal look 25% cleaner in the nitrogen constraint. Reported only.
        total_outputs = n_crop_uptake

        # Balance
        surplus = total_inputs - total_outputs
        nue = total_outputs / max(total_inputs, 1.0)

        return {
            "n_mineral_input": n_mineral,
            "n_mineral_plain": n_mineral_plain,
            "n_organic_input": n_organic,
            "n_fixation": n_fixation,
            "n_crop_residues": n_residues,
            "n_deposition": n_deposition,
            "n_crop_uptake": n_crop_uptake,
            "n_animal_products": n_animal_output,
            "n_surplus": surplus,
            "n_use_efficiency": nue,
            # pools of CAPRI's fertiliser distribution (fertDistExcr_, fertDistCres_; inner model): manure N
            # applied in the region (own after export, plus imports), the arable residue pool, own residues of
            # the permanent groups
            "n_manure_applied": n_organic + n_manure_import,
            "n_residue_pool": (n_residues - _own_res) if _cn else 0.0,
            "n_own_residues": _own_res if _cn else 0.0,
        }

    def fert_distribution(self, region, acts, yields, nb, nb_raw, mineral_cap=None) -> Optional[list]:
        """CAPRI's inner fertiliser distribution model for one region (capri_mod.fert.inner_fert_dist): mineral N
        (the balance's), manure N applied (the balance's own manure plus imports, after endogenous trade and the
        herd adjustments) and the arable residue pool, distributed over CAPRI's crop groups; needs at CAPRI's base
        per ha x area x sqrt(yield / base yield) (NUTNED_). With the crop-specific mineral fertiliser reduction the
        "f2f" (mineral N) and "limCres" (residues) regulations apply. Rows: region, capri_region, ngrp, area_kha,
        mine/excr/cres kg_ha, mine_cap_kg_ha, cap_scale (> 1 where the accounts' mineral N exceeds the caps'
        capacity and the caps were scaled to report an allocation), converged."""
        from capri_mod.fert.inner_fert_dist import InnerFertDist
        inner = self.__dict__.get("_inner_fert")
        if inner is None:
            inner = self._inner_fert = InnerFertDist()
        if inner.capri_region(region) is None:
            return None
        if hasattr(acts, "to_dict"):
            acts = acts.to_dict()
        crops = {c: float(acts.get(c, 0.0) or 0.0) for c in CROPS if float(acts.get(c, 0.0) or 0.0) > 0}
        _yb = self._cached_row("yields", region) or {}
        fac = {}
        for c in crops:
            y0 = float(_yb.get(c, 0.0) or 0.0)
            y = float(yields.get(c, y0) or 0.0) if hasattr(yields, "get") else y0
            fac[c] = (y / y0) ** 0.5 if (y0 > 0 and y > 0) else 1.0
        M = float(nb.get("n_mineral_input", 0.0))
        E = float(nb_raw.get("n_manure_applied", 0.0)) + float(nb.get("n_organic_input", 0.0)) \
            - float(nb_raw.get("n_organic_input", 0.0))
        C = float(nb_raw.get("n_residue_pool", 0.0))
        av = float(self._residue_availability(region)[0] or 0.0)
        caps, gcaps = None, {}
        if mineral_cap and mineral_cap.get("group_caps"):
            gcaps = mineral_cap["group_caps"]
            caps = {(g, "MINE"): v for g, v in gcaps.items() if v > 0}
            for g, v in (mineral_cap.get("limcres") or {}).items():
                caps[(g, "CRES")] = v
        out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac, caps=caps)
        cap_scale = 1.0
        if caps and (out is None or not out["converged"]):
            # The supply model holds mineral N at most at the caps' capacity, sum_g cap_g x area_g; the beta
            # densities' support is open (x < cap), so at the capacity itself the regulated mode does not exist,
            # and the accounts' mineral N can exceed the row's by their own adjustments (catch crops, realised
            # yields; ~0.1%). Then the caps are scaled to leave 0.2% room, and the scale is reported.
            ar_ = inner.group_areas(region, crops)
            capa = sum(v * ar_.get(g, 0.0) for (g, s_), v in caps.items() if s_ == "MINE" and not isinstance(v, tuple))
            free = [g for g in ar_ if (g, "MINE") not in caps]
            if capa > 0 and not free:
                cap_scale = max(1.0, M / (0.998 * capa))
                caps2 = {k: (v * cap_scale if (k[1] == "MINE" and not isinstance(v, tuple)) else v) for k, v in caps.items()}
                out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac, caps=caps2)
        if out is None and caps:
            # regulations infeasible at this solution: report the unregulated allocation, flagged
            out = inner.allocate(region, crops, M, E, C, av, crop_factor=fac)
            if out is not None:
                out["converged"] = False
        if out is None:
            return None
        rows = []
        for g, A in out["area"].items():
            ph = {s_: float(out["per_ha"].get((g, s_), 0.0)) for s_ in ("MINE", "EXCR", "CRES")}
            rows.append(dict(region=region, capri_region=out["capri_region"], ngrp=g, area_kha=float(A),
                             mine_kg_ha=ph["MINE"], excr_kg_ha=ph["EXCR"], cres_kg_ha=ph["CRES"],
                             mine_cap_kg_ha=float(gcaps.get(g, float("nan"))) if gcaps else float("nan"),
                             cap_scale=cap_scale, converged=bool(out["converged"])))
        return rows

    def compute_biodiversity_indicators(
        self,
        activities: pd.Series,
        land: pd.Series,
    ) -> Dict[str, float]:
        """
        Shannon crop diversity index and HNV farmland proxy.

        Shannon H' = -Σ p_i × ln(p_i)
        where p_i = share of crop i in total arable area.

        HNV (High Nature Value) farmland is proxied by share of:
          - Permanent grassland
          - Legumes + extensive crops
          - Organic area
        """
        # Shannon diversity
        crop_areas = activities.reindex(CROPS).fillna(0.0)
        total_crop = crop_areas.sum()
        if total_crop > 0:
            shares = crop_areas / total_crop
            shares = shares[shares > 0]
            shannon = -float((shares * np.log(shares)).sum())
        else:
            shannon = 0.0

        # HNV proxy (% of UAA)
        total_uaa = land.sum() if not land.empty else total_crop
        grassland = land.get("GRASSLAND", 0.0)
        legume_area = sum(activities.get(c, 0.0) for c in ["PULS", "SOYA", "GRAS"])
        hnv_area = grassland + legume_area * 0.5
        hnv_pct = 100.0 * hnv_area / max(total_uaa, 1.0)

        return {
            "shannon_crop_diversity": shannon,
            "hnv_farmland_pct": min(100.0, hnv_pct),
        }

    _ENT_CACHE = None

    def _enteric_factors(self) -> dict:
        """{animal: {"ym": Ym, "ge": {country: {feed: GE Mcal/kg DM, "_mean": ...}}}} from
        capri_data/2017/environment/enteric_feed_factors.csv (tools/build_enteric_feed_factors.py)."""
        cls = type(self)
        if cls._ENT_CACHE is None:
            import csv as _csv
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "enteric_feed_factors.csv"
            out = {}
            if f.exists():
                for r in _csv.DictReader(open(f)):
                    if not r["ym"]:
                        continue
                    d = out.setdefault(r["animal"], {"ym": float(r["ym"]), "ge": {}})
                    d["ge"].setdefault(r["country"], {})[r["feed"]] = float(r["ge_mcal_per_kg_dm"])
                for d in out.values():
                    for g in d["ge"].values():
                        g["_mean"] = sum(g.values()) / len(g)
            cls._ENT_CACHE = out
        return cls._ENT_CACHE

    _FERT_SIDE = None

    def fert_side_factors(self, region, shares, nmin) -> Optional[Dict[str, float]]:
        """Emission factor multipliers on mineral N from CAPRI's nitrification-inhibitor side
        effects (capri_data/2017/abatement/fert_side_effects.csv, tools/build_fert_side_effects.py):
        F = 1 - w + w (1 - lit) (1 + NMIN), w = the option's share of mineral N. None when the
        region has no inhibitor adoption."""
        s = float((shares or {}).get("NITR_INH", 0.0) or 0.0)
        if not s > 0:
            return None
        cls = type(self)
        if cls._FERT_SIDE is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "abatement" / "fert_side_effects.csv"
            tab = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["region", "technology", "item", "value"])
            cls._FERT_SIDE = {(r.region, r.technology, r.item): float(r.value) for r in tab.itertuples()}
        tab = cls._FERT_SIDE
        lit = {i: tab.get((region, "NITR_INH", i)) for i in ("N2OSYN", "NH3SYN")}
        if any(v is None for v in lit.values()):
            return None
        nm = float((nmin or {}).get("NITR_INH", 0.0) or 0.0)
        s = min(s, 1.0)
        w = (s / (1.0 + nm)) / (s / (1.0 + nm) + 1.0 - s)
        return {i: 1.0 - w + w * (1.0 - v) * (1.0 + nm) for i, v in lit.items()}

    def _manure_n2o_factor(self, region, animal):
        """(f_man, f_app, f_gra, f_lea), t N2O-N per t of manure N (capri_data/2017/environment/
        manure_n2o_factors.csv), or None."""
        tab = self.__dict__.get("_mn2o_cache")
        if tab is None:
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "manure_n2o_factors.csv"
            tab = ({(r.region, r.animal): (float(r.f_man), float(r.f_app), float(r.f_gra), float(r.f_lea))
                    for r in pd.read_csv(f).itertuples()} if f.exists() else {})
            self._mn2o_cache = tab
        return tab.get((region, animal))

    def _manure_n2o_tech(self, region):
        """{animal: {technology: (r_hou, r_app)}} (manure_n2o_tech.csv) and base shares {animal:
        {technology: share}} (ammonia_tech_model.csv ini, weighted as the supply model reports)."""
        cache = self.__dict__.setdefault("_mn2o_tech_cache", {})
        if region not in cache:
            from pathlib import Path as _P
            d = _P(__file__).resolve().parents[2] / "capri_data" / "2017"
            if "_mn2o_tech_tab" not in self.__dict__:
                f = d / "environment" / "manure_n2o_tech.csv"
                self._mn2o_tech_tab = pd.read_csv(f) if f.exists() else pd.DataFrame(
                    columns=["region", "animal", "technology", "r_hou", "r_app"])
                from capri_mod.supply import ammonia_techs as _at
                self._amm_tm = _at.load(d / "abatement" / "ammonia" / "ammonia_tech_model.csv")
            t = self._mn2o_tech_tab[self._mn2o_tech_tab["region"] == region]
            eff = {}
            for r in t.itertuples():
                eff.setdefault(r.animal, {})[r.technology] = (float(r.r_hou), float(r.r_app))
            s0 = {}
            for a, subs in (self._amm_tm.get(region) or {}).items():
                for sb in subs:
                    for tt in sb["techs"]:
                        s0.setdefault(a, {})[tt["tech"]] = s0.get(a, {}).get(tt["tech"], 0.0) + sb["w"] * tt["ini"]
            cache[region] = (eff, s0)
        return cache[region]

    def _manure_n2o_cascade(self, region, animal, sh, s0):
        """(housing, application) multipliers of manure N2O from the N left after NH3 losses at
        shares sh against the base shares s0, over the animal's CAPRI sub-activities weighted by
        their manure N (ammonia_tech_model.csv; capri_mod/supply/ammonia_techs.stage_n)."""
        from capri_mod.supply import ammonia_techs as _at
        subs = (getattr(self, "_amm_tm", None) or {}).get(region, {}).get(animal) or []
        if not subs:
            return 1.0, 1.0
        full1 = {t: sh.get(t, s0.get(t, 0.0)) for t in set(s0) | set(sh)}
        H1 = F1 = H0 = F0 = 0.0
        for sb in subs:
            w = float(sb["w"]) * float(sb.get("mrel", 1.0) or 1.0)
            h1, f1 = _at.stage_n(sb, full1)
            h0, f0 = _at.stage_n(sb, {t["tech"]: t["ini"] for t in sb["techs"]})
            H1 += w * h1; F1 += w * f1; H0 += w * h0; F0 += w * f0
        return (H1 / H0 if H0 > 0 else 1.0), (F1 / F0 if F0 > 0 else 1.0)

    def _nh3_factors(self) -> dict:
        d = self.__dict__.get("_nh3_fac_cache")
        if d is None:
            import json as _json
            from pathlib import Path as _P
            f = _P(__file__).resolve().parents[2] / "capri_data" / "2017" / "environment" / "nh3_factors_capri.json"
            d = _json.load(open(f))["regions"] if f.exists() else {}
            self._nh3_fac_cache = d
        return d

    def compute_ammonia(
        self,
        activities: pd.Series,
        region: Optional[str] = None,
        mineral_n_kt: Optional[float] = None,
    ) -> Dict[str, float]:
        """Ammonia emissions (kt NH3) from livestock manure and mineral fertiliser.

        ``region`` selects the regional N excretion. It used to be missing from
        the signature while the body referenced it, so every call raised a
        NameError; run_all_regions swallowed the error per region and returned
        an EMPTY environmental table from every model run, silently.
        """
        # CAPRI's AMMONIA ACCOUNTING (replaces the housing-only factors and the
        # "soils = 10% of livestock" proxy): per region, CAPRI's share of each
        # animal's excreted N lost as NH3-N (housing + storage + application +
        # grazing, GNH3/MANN) and the share of mineral N lost (NH3MIN/MINFER),
        # from its 2030 reference run (tools/build_nh3_factors.py). Responds to
        # herds AND to mineral fertiliser - which the proxy could not see.
        fac = self._nh3_factors().get(region) if region else None
        if fac:
            man_n = sum(float(fac["manure_share"].get(a, 0.0))
                        * self._n_excretion(region, a) * activities.get(a, 0.0) * 1000 / 1e6
                        for a in ANIMALS)                                   # kt NH3-N
            min_n = float(fac.get("mineral_share") or 0.0) * float(mineral_n_kt or 0.0)
            return {"nh3_livestock": man_n * 17 / 14, "nh3_soils": min_n * 17 / 14,
                    "nh3_total": (man_n + min_n) * 17 / 14}
        # no CAPRI factors: only where there is no farming (Brussels); anything else fails loudly
        if any(activities.get(a, 0.0) > 0 for a in ANIMALS) or float(mineral_n_kt or 0.0) > 0:
            raise RuntimeError(f"no CAPRI ammonia factors for {region} (tools/build_nh3_factors.py)")
        return {"nh3_livestock": 0.0, "nh3_soils": 0.0, "nh3_total": 0.0}

    def compute_indicators(
        self,
        supply_result,  # SupplyResult
        land: Optional[pd.Series] = None,
    ) -> EnvironmentalIndicators:
        """
        Compute full set of environmental indicators for one region.

        Parameters
        ----------
        supply_result : SupplyResult from supply module
        land          : land availability series for the region
        """
        acts   = supply_result.activities
        region = supply_result.region_id
        # nitrate shares of this region's rations, BEFORE the GHG calculation uses them
        self._nitrate_share_now = dict(getattr(supply_result, "nitrate_share", None) or {})
        # CAPRI's feed supplements (envind/line_nitr.gms; Sprint 9g): enteric CH4 per head of the adopting share
        # x (1 + ch4ent_rel) - linseed -25%, nitrate -15%; both on the same animals (AComLN) multiply, the
        # overlap taken as large as the shares allow (CAPRI's maximum run puts all its linseed on nitrate
        # cows; without an emission price the split is not determined: REGISTERED)
        _supp = {}
        _lvs = getattr(supply_result, "activities", None)
        _gtab_s = (self.data.get("genetics_effects") or {}).get(region) if hasattr(self, "data") else None
        if _gtab_s and _lvs is not None:
            _sh = {}
            for (_ga, _go), _gz in (getattr(supply_result, "genetics_shift", None) or {}).items():
                _e = _gtab_s.get((_ga, _go))
                _h = float(_lvs.get(_ga, 0.0) or 0.0)
                if _e is None or _h <= 0 or not _gz or "ch4ent_rel" not in _e.index or not pd.notna(_e["ch4ent_rel"]):
                    continue
                _sh.setdefault(_ga, []).append((min(1.0, max(0.0, float(_gz) / _h)), float(_e["ch4ent_rel"])))
            for _ga, _l in _sh.items():
                _f = 1.0 + sum(s_ * r_ for s_, r_ in _l)
                if len(_l) == 2:
                    _f += _l[0][1] * _l[1][1] * min(_l[0][0], _l[1][0])
                _supp[_ga] = max(0.0, _f)
        if not hasattr(self, "_supp_ch4"):
            self._supp_ch4 = {}
        self._supp_ch4[region] = _supp
        # feed dry matter per animal (feeding inside the supply model), and the region
        self._feed_dm_now = dict(getattr(supply_result, "feed_dm", None) or {})
        self._region_now = region

        yields = self.data["yields"].loc[region] if region in self.data["yields"].index \
                 else pd.Series(dtype=float)
        # Crop uptake must use the yields of THIS solution, not the base year's:
        # under a scenario, lower fertiliser, pesticide and organic yields lower
        # uptake too. With base yields the accounts counted the fertiliser cut
        # but not the lost uptake, so the reported nitrogen surplus fell far more
        # than it did (Farm-to-Fork: -47.5% against the constraint's own cut).
        # Realised yield = gross output / area, wherever both are positive.
        try:
            go = getattr(supply_result, "gross_output", None)
            ac = getattr(supply_result, "activities", None)
            if go is not None and ac is not None:
                realised = {c: float(go[c]) / float(ac[c]) for c in CROPS
                            if c in go.index and c in ac.index
                            and float(ac[c]) > 1e-9 and float(go[c]) > 0}
                if realised:
                    yields = yields.copy()
                    for c, v in realised.items():
                        yields[c] = v
        except Exception:
            pass

        if land is None:
            land = self.data["land"].loc[region] if region in self.data["land"].index \
                   else pd.Series(dtype=float)

        # GHG
        mint = dict(getattr(supply_result, "n_intensity", {}) or {})
        _gz = float(getattr(supply_result, "grass_ext_shift", 0.0) or 0.0)
        ghg = self.compute_ghg(acts, region, mint, grass_shift=_gz)
        ghg_total = sum(ghg.values())

        # Nitrogen
        nb = self.compute_nitrogen_balance(acts, yields, region, mint)
        _nb_raw = dict(nb)
        # MANURE MARKET (when on): the region's endogenous manure trade and its
        # allocated mineral N (fertiliser allocation) replace the fixed-rule
        # values, so the reported balance is the one the regional model met.
        _mt = getattr(supply_result, "manure_trade", None)
        _ma = getattr(supply_result, "mineral_n_alloc", None)
        if _mt and (abs(_mt[0]) > 0 or abs(_mt[1]) > 0):
            # traded manure, with the balance's own linear substitution:
            # organic +-1, mineral -+a, surplus +-(1 - a) per t (net imports)
            _d = float(_mt[1]) - float(_mt[0])
            _a = float(getattr(supply_result, "manure_availability", 0.0) or 0.0)   # substitution factor used (0 at the floor)
            nb["n_organic_input"] = float(nb["n_organic_input"]) + _d
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _a * _d
            nb["n_surplus"] = float(nb["n_surplus"]) + (1.0 - _a) * _d
        # CAPRI's grassland split (Sprint 7a): the area moved from GRAI to GRAE changes the
        # balance by the same per-ha difference the supply model's N row used
        if _gz:
            _dl = self.grass_intensity_delta(region) or {}
            for _k, _v in _dl.items():
                if _k in nb and isinstance(nb[_k], (int, float)) and _k != "n_use_efficiency":
                    nb[_k] = float(nb[_k]) + _gz * float(_v)
        # CAPRI's dairy split (Sprint 7b): z cows at DCOL instead of DCOH excrete
        # (MANN_DCOL - MANN_DCOH) / MANN_DCOW of a cow's manure N more each - the supply model's
        # manure rows use the same factor. Accounted as k = z x that factor manure-equivalent cows:
        # the balance and manure N2O with and without them (enteric CH4 already follows the cows'
        # feed; manure CH4 per head is left unchanged: REGISTERED)
        _dz = float(getattr(supply_result, "dairy_low_shift", 0.0) or 0.0)
        _dk = 0.0
        _dtab = self.data.get("dairy_intensity") if hasattr(self, "data") else None
        if _dz and _dtab is not None and region in _dtab.index:
            _dk = _dz * float(_dtab.at[region, "dmann_rel"])
        # the bull and heifer splits (Sprint 7c) the same way: z stalls at the low-intensity activity
        # carry (MANN per stall, low - high) / average of the animal's manure N
        _kk = {"DCOW": _dk} if _dk else {}
        _ctab = (self.data.get("cattle_intensity") or {}).get(region) if hasattr(self, "data") else None
        for _a, _z in (getattr(supply_result, "cattle_shift", None) or {}).items():
            if _z and _ctab and _a in _ctab:
                _kk[_a] = float(_z) * float(_ctab[_a]["dmann_rel"])
        # cattle genomics (breeding.gms): g animals adopting excrete d_mann_rel more (genet_yld) or less
        # (genet_eff) manure N each; enteric CH4 follows the animals' feed as for the splits
        _gtab = (self.data.get("genetics_effects") or {}).get(region) if hasattr(self, "data") else None
        for (_ga, _go), _gz in (getattr(supply_result, "genetics_shift", None) or {}).items():
            if _gz and _gtab and (_ga, _go) in _gtab:
                _kk[_ga] = float(_kk.get(_ga, 0.0)) + float(_gz) * float(_gtab[(_ga, _go)]["d_mann_rel"])
        _acts_k = None
        if _kk:
            _acts_k = dict(acts) if isinstance(acts, dict) else acts.copy()
            for _a, _v in _kk.items():
                _acts_k[_a] = float(_acts_k.get(_a, 0.0)) + _v
            _nb_k = self.compute_nitrogen_balance(_acts_k, yields, region, mint)
            _nb_0 = self.compute_nitrogen_balance(acts, yields, region, mint)
            for _k in ("n_organic_input", "n_mineral_input", "n_mineral_plain", "n_surplus"):
                if _k in nb and _k in _nb_k:
                    nb[_k] = float(nb[_k]) + float(_nb_k[_k]) - float(_nb_0[_k])
            _g_k = self.compute_ghg(_acts_k, region, mint, grass_shift=_gz)
            if "N2O_MAN" in ghg:
                ghg["N2O_MAN"] += float(_g_k.get("N2O_MAN", 0.0)) - float(ghg["N2O_MAN"])
        _rel = getattr(supply_result, "animal_n_relief", None) or {}
        self._nh3_saved_last = 0.0                  # per region: never carried over
        self._nitrate_share_now = dict(getattr(supply_result, "nitrate_share", None) or {})
        self._nitrate_nh3_extra = 0.0
        _nx = getattr(supply_result, "nitrate_n_extra", None) or {}
        if _nx:
            # nitrate N excreted: manure like any other (organic +, mineral - sub, surplus + (1 - sub))
            _lv2 = getattr(supply_result, "activities", None)
            if _lv2 is None:
                _lv2 = {}
            _sb = float(getattr(supply_result, "n_substitution", 0.0) or 0.0)
            _dx = sum(float(v) * float(_lv2.get(a, 0.0)) for a, v in _nx.items())
            nb["n_organic_input"] = float(nb["n_organic_input"]) + _dx
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _sb * _dx
            nb["n_surplus"] = float(nb["n_surplus"]) + (1.0 - _sb) * _dx
            _fs = (self._nh3_factors().get(region) or {}).get("manure_share", {}) if region else {}
            self._nitrate_nh3_extra = sum(float(v) * float(_lv2.get(a, 0.0)) * float(_fs.get(a, 0.0)) for a, v in _nx.items())
        if _rel:
            _lv = getattr(supply_result, "activities", None)
            if _lv is None:
                _lv = {}
            _d = sum(float(v) * float(_lv.get(a, 0.0)) for a, v in _rel.items())
            nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _d
            nb["n_surplus"] = float(nb["n_surplus"]) - _d
            self._nh3_saved_last = sum(float(v) * float(_lv.get(a, 0.0))
                                       for a, v in (getattr(supply_result, "animal_nh3_saved", None) or {}).items())
        if _ma is not None:
            _d = float(_ma) - float(nb["n_mineral_input"])
            nb["n_mineral_input"] = float(_ma)
            nb["n_surplus"] = float(nb["n_surplus"]) + _d
        # CAPRI's catch crops added by the Farm-to-Fork requirement (supply model's _cover): their
        # N (BioFix x area) is an input of the balance and supplies crop need; with mineral N
        # allocated in the supply model it is already net of it, else it replaces mineral N here
        _cv = getattr(supply_result, "cover_crops", None) or {}
        _cn = float(_cv.get("delta", 0.0) or 0.0) * float(_cv.get("biofix", 0.0) or 0.0) * 1000.0
        if _cn > 0:
            nb["n_fixation"] = float(nb["n_fixation"]) + _cn
            nb["n_surplus"] = float(nb["n_surplus"]) + _cn
            if _ma is None:
                _r = min(_cn, max(0.0, float(nb["n_mineral_input"])))
                nb["n_mineral_input"] = float(nb["n_mineral_input"]) - _r
                nb["n_surplus"] = float(nb["n_surplus"]) - _r
        # CAPRI's inner fertiliser distribution model (star 3.0 default useInnerFertDistModel): the region's
        # mineral N, manure N applied and arable residue pool distributed over CAPRI's crop groups, with the
        # mineral fertiliser reduction's regulations when the scenario has them (reporting; the regional totals
        # are the balance's own)
        try:
            self._fert_dist_now = self.fert_distribution(region, acts, yields, nb, _nb_raw,
                                                         getattr(supply_result, "mineral_cap", None))
        except Exception as _exc:
            import warnings as _w
            _w.warn(f"inner fertiliser distribution failed for {region}: {_exc!r}")
            self._fert_dist_now = None
        # soil N2O from MINERAL fertiliser (CAPRI N2OSYN; JRC121368's "N2O mineral fertiliser"): the
        # balance's own mineral N (after substitution, yield effects, technologies, catch crops) x
        # (direct + volatilised share x indirect factor). It used to be crops' N coefficients (16.6 Mt N
        # in the EU, mineral and organic) rescaled by the mineral ratio, so manure-borne soil N2O moved
        # with mineral N; manure N2O is N2O_MAN. Crop residues are their own source (CAPRI N2OCRO).
        if "N2O_SOIL" in ghg:
            ghg["N2O_SOIL"] = (max(0.0, float(nb.get("n_mineral_input", 0.0))) / 1000.0
                               * (EF_SOIL_N2O_DIRECT + 0.10 * EF_SOIL_N2O_INDIRECT) * 44.0 / 28.0 * GWP_N2O)
        ghg["N2O_CRO"] = (max(0.0, float(nb.get("n_crop_residues", 0.0) or 0.0)) / 1000.0
                          * EF_SOIL_N2O_DIRECT * 44.0 / 28.0 * GWP_N2O)
        # CO2 from urea on the same mineral N (CAPRI gases.gms (17): NMIN x urea share x 44/28)
        ghg["CO2_UREA"] = (max(0.0, float(nb.get("n_mineral_input", 0.0))) / 1000.0
                           * self._co2_coefs(region)[1] * 44.0 / 28.0)

        # CAPRI's N2O from drained organic soils (gases.gms N2OHIS, agriculture): per ha of the land-use
        # class, its organic-soil share x the climate-weighted IPCC 2013 factor (tools/build_histosol.py),
        # on the area in use; the fallowed histosol area emits nothing (QEmitt = 0 in the Green Deal runs)
        _ht = self.data.get("histosol") if hasattr(self, "data") else None
        if _ht is not None and region in _ht.index:
            _h = _ht.loc[region]
            _fa = getattr(supply_result, "histosol_fallow", None) or {}
            _crop_area = sum(float(acts.get(c, 0.0) or 0.0) for c in CROPS if c != "GRAS")
            _n2o_t = (_crop_area * float(_h.get("n2o_t_ha_crop", 0.0) or 0.0)
                      + float(acts.get("GRAS", 0.0) or 0.0) * float(_h.get("n2o_t_ha_grass", 0.0) or 0.0))
            for _c in ("crop", "grass"):
                _f = float(_fa.get(_c, 0.0) or 0.0)
                if _f > 0:
                    _n2o_t -= _f * float(_h.get(f"ef_n2o_{_c}", 0.0) or 0.0) * 0.001 * 44.0 / 28.0
            ghg["N2O_HIS"] = max(0.0, _n2o_t) * GWP_N2O      # 1000 ha x t N2O/ha = kt N2O -> kt CO2-eq
        # crop-residue N2O of the added catch crops (CAPRI gases.gms N2OCRO: BioFix x area x EF1)
        if _cn > 0:
            ghg["N2O_CRO"] = ghg.get("N2O_CRO", 0.0) + _cn / 1e3 * EF_SOIL_N2O_DIRECT * 44.0 / 28.0 * GWP_N2O   # t N -> kt
        # CAPRI's technology effects on manure N2O (v_emiLoss in gases.gms; manure_n2o_tech.csv):
        # per animal, housing/storage N2O x (1 - sum_t s_t r_hou_t) / (1 - sum_t s0_t r_hou_t) and
        # application N2O likewise with r_app (low-emission spreading raises it), at the regional
        # model's option shares s against CAPRI's initial shares s0; inhibitors on manure cut
        # application N2O by their share x CAPRI's literature effect (N2OAPP; NMAN left out: REGISTERED)
        _ms = getattr(supply_result, "manure_tech_shares", None) or {}
        _n2o_tech = 0.0
        if _ms and region:
            _eff, _s0 = self._manure_n2o_tech(region)
            _sni = float((getattr(supply_result, "fert_tech_shares", None) or {}).get("NITR_INH_MAN", 0.0) or 0.0)
            _lit = 0.0
            if _sni > 0:
                from capri_mod.supply.supply_module import fert_side_value as _fsv
                _lit = float(_fsv(region, "NITR_INH_MAN", "N2OAPP") or 0.0)
            _dm = 0.0
            for a_ in ANIMALS:
                _mf = self._manure_n2o_factor(region, a_)
                x_ = float(acts.get(a_, 0.0) or 0.0)
                if _mf is None or x_ <= 0:
                    continue
                e_ = _eff.get(a_, {})
                sh = {t: v for (aa, t), v in _ms.items() if aa == a_}
                b_ = _s0.get(a_, {})
                h1 = sum(sh.get(t, b_.get(t, 0.0)) * rr[0] for t, rr in e_.items())
                h0 = sum(b_.get(t, 0.0) * rr[0] for t, rr in e_.items())
                p1 = sum(sh.get(t, b_.get(t, 0.0)) * rr[1] for t, rr in e_.items())
                p0 = sum(b_.get(t, 0.0) * rr[1] for t, rr in e_.items())
                fh = (1.0 - h1) / (1.0 - h0) if h0 < 1.0 else 1.0
                fa = ((1.0 - p1) / (1.0 - p0) if p0 < 1.0 else 1.0) * (1.0 - _sni * _lit)
                # CAPRI's loss cascade (HOUSN_, APPLN_): the N2O factors apply to the N LEFT after
                # NH3 losses at the same stage, so NH3 kept by covers, housing or low-emission
                # spreading flows on and raises N2O downstream - JRC121368 Table 18: housing and
                # storage technologies +0.9 Mt CO2eq, application technologies +5.2 Mt
                ch, ca_ = self._manure_n2o_cascade(region, a_, sh, b_)
                fh *= ch
                fa *= ca_
                kt_n = self._n_excretion(region, a_) * x_ * 1000.0 / 1e6
                _dm += kt_n * (_mf[0] * (fh - 1.0) + _mf[1] * (fa - 1.0))
            ghg["N2O_MAN"] = ghg.get("N2O_MAN", 0.0) + _dm * 44.0 / 28.0 * GWP_N2O
            _n2o_tech = _dm * 44.0 / 28.0 * GWP_N2O
        # CAPRI's emission side effects of nitrification inhibitors on mineral N
        # (p_litRevFertTechs, envind/ghgMiti.gms l. 552-555): per kg of N under the option the
        # emission factor is (1 - lit) x (1 + NMIN) times NOC's, NMIN being the option's N saving,
        # already in the mineral input. Weight: the option's share of mineral N (area share s,
        # N per ha lowered by 1 + NMIN). Direct soil N2O takes the N2O factor; the volatilisation
        # path of indirect N2O and mineral NH3 take the NH3 factor.
        f_side = self.fert_side_factors(region, getattr(supply_result, "fert_tech_shares", None),
                                        getattr(supply_result, "fert_nmin", None))
        if f_side and "N2O_SOIL" in ghg:
            _dir = EF_SOIL_N2O_DIRECT / (EF_SOIL_N2O_DIRECT + 0.10 * EF_SOIL_N2O_INDIRECT)
            _old = ghg["N2O_SOIL"]
            ghg["N2O_SOIL"] = _old * (_dir * f_side["N2OSYN"] + (1.0 - _dir) * f_side["NH3SYN"])
        # total after every adjustment of soil N2O (it was summed before the mineral-input
        # rescaling above, so GHG total missed the substitution and yield effects on soil N2O)
        ghg_total = sum(ghg.values())

        # Biodiversity
        bio = self.compute_biodiversity_indicators(acts, land)

        # Ammonia
        nh3 = self.compute_ammonia(_acts_k if _acts_k is not None else acts, region,
                                   mineral_n_kt=float(nb.get("n_mineral_input", 0.0)) / 1000.0)
        if f_side and nh3.get("nh3_soils"):
            nh3 = dict(nh3)
            _d = float(nh3["nh3_soils"]) * (f_side["NH3SYN"] - 1.0)
            nh3["nh3_soils"] = float(nh3["nh3_soils"]) + _d
            nh3["nh3_total"] = float(nh3["nh3_total"]) + _d
        # CAPRI's inhibitors on applied manure raise application NH3 (p_litRevFertTechs NH3APP,
        # supply model's _apply_manure_inhibitor): t NH3-N per activity unit -> kt NH3
        _ni = getattr(supply_result, "manure_ni_nh3", None) or {}
        if _ni:
            _lv3 = getattr(supply_result, "activities", None)
            if _lv3 is None:
                _lv3 = {}
            _d = sum(float(v) * float(_lv3.get(a, 0.0)) for a, v in _ni.items()) / 1000.0 * 17.0 / 14.0
            if _d:
                nh3 = dict(nh3)
                nh3["nh3_livestock"] = float(nh3["nh3_livestock"]) + _d
                nh3["nh3_total"] = float(nh3["nh3_total"]) + _d
        # CAPRI's ammonia technologies: N kept from volatilising (t N) -> kt NH3
        _sv = float(getattr(self, "_nh3_saved_last", 0.0) or 0.0) - float(getattr(self, "_nitrate_nh3_extra", 0.0) or 0.0)
        if _sv != 0:
            _d = _sv / 1000.0 * 17.0 / 14.0
            nh3 = dict(nh3)
            nh3["nh3_livestock"] = max(0.0, float(nh3["nh3_livestock"]) - _d)
            nh3["nh3_total"] = max(0.0, float(nh3["nh3_total"]) - _d)
        # indirect N2O from volatilised manure NH3 (CAPRI N2OAMM: NH3-N x EF4), after every NH3
        # adjustment; the GHG total is summed again with it
        if nh3.get("nh3_livestock"):
            ghg["N2O_IND"] = float(nh3["nh3_livestock"]) * 14.0 / 17.0 * EF_SOIL_N2O_INDIRECT * 44.0 / 28.0 * GWP_N2O
            ghg_total = sum(ghg.values())

        # Land use
        arable = sum(acts.get(c, 0.0) for c in CROPS
                     if c not in ("GRAS","MAIF","OFOD","WINE","OLIV",
                                  "APPL","OFRU","CITR","TAGR","TOBA",
                                  "COTT","OFIB","SETA"))
        perm   = sum(acts.get(c, 0.0) for c in
                     ["WINE","OLIV","APPL","OFRU","CITR","TAGR","TOBA","COTT","OFIB"])
        grass  = sum(acts.get(c, 0.0) for c in ["GRAS","MAIF","OFOD"])

        return EnvironmentalIndicators(
            region=region,
            # GHG
            ghg_enteric=ghg["CH4_ENT"],
            ghg_manure_ch4=ghg["CH4_MAN"],
            ghg_manure_n2o=ghg["N2O_MAN"],
            ghg_soil_n2o=ghg["N2O_SOIL"],
            ghg_histosol_n2o=float(ghg.get("N2O_HIS", 0.0)),
            ghg_manure_n2o_tech=float(_n2o_tech),
            ghg_residue_n2o=float(ghg.get("N2O_CRO", 0.0)),
            ghg_indirect_n2o=float(ghg.get("N2O_IND", 0.0)),
            ghg_liming=ghg["CO2_LIME"],
            ghg_urea=float(ghg.get("CO2_UREA", 0.0)),
            ghg_total=ghg_total,
            ghg_non_co2=ghg_total - float(ghg.get("CO2_LIME", 0.0)) - float(ghg.get("CO2_UREA", 0.0)),
            ghg_ggwp=ghg_total - float(ghg.get("CO2_UREA", 0.0)),
            # Nitrogen
            n_mineral_input=nb["n_mineral_input"],
            n_organic_input=nb["n_organic_input"],
            n_fixation=nb["n_fixation"],
            n_deposition=nb["n_deposition"],
            n_crop_uptake=nb["n_crop_uptake"],
            n_animal_products=nb["n_animal_products"],
            n_surplus=nb["n_surplus"],
            n_use_efficiency=nb["n_use_efficiency"],
            # Ammonia
            nh3_livestock=nh3["nh3_livestock"],
            nh3_soils=nh3["nh3_soils"],
            nh3_total=nh3["nh3_total"],
            # Land
            uaa_total=arable + perm + grass,
            arable_land=arable,
            permanent_crops=perm,
            grassland=grass,
            # Biodiversity
            shannon_crop_diversity=bio["shannon_crop_diversity"],
            hnv_farmland_pct=bio["hnv_farmland_pct"],
        )

    def run_all_regions(
        self,
        supply_results: Dict,  # {region: SupplyResult}
        verbose: bool = False,
    ) -> pd.DataFrame:
        """
        Compute environmental indicators for all regions.
        Returns DataFrame with one row per region.
        """
        rows = []
        fd = []
        for i, (region, result) in enumerate(supply_results.items()):
            if verbose and i % 50 == 0:
                print(f"  Environmental module: region {i+1}/{len(supply_results)}")
            try:
                self._fert_dist_now = None
                ind = self.compute_indicators(result)
                rows.append(ind.to_series())
                fd.extend(self._fert_dist_now or [])
            except Exception as _e:
                import warnings as _w
                _w.warn(f"environmental indicators failed for {region}: {_e!r} - region left out of the table")
                if verbose:
                    print(f"    Warning: {region} environmental calc failed: {e}")

        # CAPRI's inner fertiliser distribution per region and crop group (CAPRIModel.run: results["fert_dist"])
        self.last_fert_dist = pd.DataFrame(fd)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).set_index("region")
        return df

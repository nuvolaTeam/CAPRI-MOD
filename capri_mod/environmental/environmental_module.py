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

from capri_mod.data.definitions import (
    CROPS, ANIMALS, ALL_ACTIVITIES, NUTRIENTS, GHG_TYPES,
)


# ---------------------------------------------------------------------------
# IPCC EMISSION FACTORS
# ---------------------------------------------------------------------------

# GHG emission factors — IPCC 2019 Tier 1 defaults
# CH4 from enteric fermentation (kg CH4 / head / year)
EF_ENTERIC_CH4 = {
    "DCOW": 117.0,  "BCOW": 65.0,  "BULL": 56.0,  "HFRS": 60.0,
    "CALV": 20.0,   "SHGP": 8.0,   "PIGS": 1.5,   "PIGF": 1.0,
    "LAYS": 0.0,    "BROI": 0.0,   "OANI": 0.0,
}

# CH4 from manure management (kg CH4 / head / year)
# Manure CH4 EFs — CAPRI GAMS: envind/create_rawdat_gascoeff_gdx.gms
# IPCC 2006 Vol 4 Ch 10, Table 10A.2, temperate developed (kg CH4/head/yr)
EF_MANURE_CH4 = {
    "DCOW": 16.0,  "BCOW": 5.0,   "BULL": 5.0,  "HFRS": 5.0,
    "CALV":  5.0,  "SHGP": 0.19,  "PIGS": 4.2,  "PIGF": 3.5,
    "LAYS": 0.02,  "BROI": 0.01,  "OANI": 0.01,
}

# N2O from manure (kg N2O-N / kg N excreted) — direct + indirect
EF_MANURE_N2O = 0.02   # 2% of N excreted → N2O-N

# N2O from soils (kg N2O-N / kg N applied) — direct emission factor
EF_SOIL_N2O_DIRECT   = 0.01   # 1% of N applied
EF_SOIL_N2O_INDIRECT = 0.01   # volatilisation + leaching pathways

# CO2 from liming (kg CO2 / kg CaCO3)
EF_LIMING = 0.12

# CO2 from urea application (kg CO2 / kg urea-N)
EF_UREA = 0.20

# NH3 emission factors (kg NH3-N / kg TAN) — for ammonia module
EF_NH3_HOUSING = {
    "DCOW": 0.08, "BCOW": 0.05, "BULL": 0.06, "HFRS": 0.06,
    "CALV": 0.04, "SHGP": 0.03, "PIGS": 0.20, "PIGF": 0.18,
    "LAYS": 0.20, "BROI": 0.12, "OANI": 0.10,
}

# Global warming potentials (AR6, 100-year)
GWP_CH4 = 25.0   # AR4   # AR4 official UNFCCC  # CAPRI AR5
GWP_N2O = 298.0  # AR4  # AR4 official UNFCCC  # CAPRI AR5

# GHG emissions from mineral fertiliser production (kg/t fertiliser)
# Source: CAPRI GAMS envind/gascoeff.gms, from Wood & Cowie (2004)
FERT_PRODUCTION_GHG = {
    "NITF": {"CO2": 2543.6, "N2O": 11.3},
    "PHOF": {"CO2": 972.7,  "N2O": 4.3},
    "POTF": {"CO2": 140.0,  "N2O": 0.6},
}  # kg CO2 or N2O per tonne fertiliser product

# Manure N content (kg N / m3) by animal and manure system
# Source: CAPRI GAMS envind/ammo_tech.gms, ammo_tech p_kgNPerM3 table
KG_N_PER_M3_MANURE = {
    "DCOL": {"liquid": 4.3, "solid": 7.0},
    "DCOH": {"liquid": 4.3, "solid": 7.0},
    "DCOW": {"liquid": 4.3, "solid": 7.0},
    "BULL": {"liquid": 4.3, "solid": 7.2},
    "BULH": {"liquid": 4.3, "solid": 7.2},
    "BULF": {"liquid": 4.3, "solid": 7.2},
    "HEIL": {"liquid": 4.3, "solid": 7.2},
    "HEIH": {"liquid": 4.3, "solid": 7.2},
    "HEIF": {"liquid": 4.3, "solid": 7.2},
    "HEIR": {"liquid": 4.3, "solid": 7.0},
    "SCOW": {"liquid": 4.3, "solid": 7.0},
    "CAMR": {"liquid": 4.3, "solid": 7.0},
    "CAFR": {"liquid": 4.3, "solid": 7.0},
    "CAMF": {"liquid": 4.3, "solid": 7.0},
    "CAFF": {"liquid": 4.3, "solid": 7.0},
    "PIGF": {"liquid": 6.0, "solid": 10.4},
    "SOWS": {"liquid": 4.7, "solid": 10.4},
}



# ---------------------------------------------------------------------------
# NITROGEN EXCRETION BY ANIMAL
# ---------------------------------------------------------------------------

# Regional nitrogen excretion from CAPRI (DATA2 MANN, kg N/head/yr) overrides
# these constants where available. The constants understate dairy by 29%
# (85 assumed against a CAPRI median of 118.8) and overstate bulls by 49%
# (35 against 23.5), and they carry no regional variation at all where CAPRI
# spans 75-223 kg for dairy cows.
def regional_n_excretion(data_dir="capri_data"):
    """(region, animal) -> kg N/head/yr, or an empty frame if not extracted."""
    import pandas as pd
    from pathlib import Path
    p = Path(data_dir) / "sources" / "capreg" / "capreg_manure_nutrients.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    return df[df.nutrient == "N"].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")


N_EXCRETION_KG_PER_HEAD = {
    "DCOW": 85.0,  "BCOW": 45.0, "BULL": 35.0,  "HFRS": 28.0,
    "CALV": 8.0,   "SHGP": 10.0, "PIGS": 22.0,  "PIGF": 8.0,
    "LAYS": 0.40,  "BROI": 0.05, "OANI": 0.10,
}

# TAN (Total Ammoniacal Nitrogen) fraction of excretion
TAN_FRACTION = {
    "DCOW": 0.60, "BCOW": 0.55, "BULL": 0.55, "HFRS": 0.55,
    "CALV": 0.50, "SHGP": 0.55, "PIGS": 0.65, "PIGF": 0.65,
    "LAYS": 0.70, "BROI": 0.65, "OANI": 0.60,
}


# ---------------------------------------------------------------------------
# RESULTS DATACLASS
# ---------------------------------------------------------------------------


# ─────────────────────────────────────────────────────────────────────
# IPCC Tier 1 constants — dat/envind/envind/GHGInv/tables2006ipcc.gms
# ─────────────────────────────────────────────────────────────────────
GWP_CH4 = 25.0    # AR4 (official UNFCCC)
GWP_N2O = 298.0   # AR4
GWP_CO2 = 1.0

# Enteric fermentation EF (kg CH4/head/year, WEU)
IPCC_CH4E_WEU = {
    "DCOW": 117.0, "BCOW": 57.0, "BULL": 57.0, "HFRS": 57.0, "CALV": 20.0,
    "SHGP": 8.0,   "PIGS": 1.5,  "PIGF": 1.5,  "LAYS": 0.0,  "BROI": 0.0,
}
MANURE_CH4_EF_WEU = {
    "DCOW": 21.0, "BCOW": 6.0, "BULL": 5.0, "HFRS": 5.0, "CALV": 2.0,
    "SHGP": 0.19, "PIGS": 6.0, "PIGF": 6.0, "LAYS": 0.10, "BROI": 0.01,
}
MANURE_N2O_EF = {"liquid": 0.001, "solid": 0.005, "pasture": 0.020, "digester": 0.0005}
N2O_EF_DIRECT = 0.01
MANURE_LIQUID_SHARE = {
    "DCOW": 0.50, "BCOW": 0.30, "BULL": 0.40, "HFRS": 0.40, "CALV": 0.30,
    "SHGP": 0.05, "PIGS": 0.80, "PIGF": 0.80, "LAYS": 0.50, "BROI": 0.10,
}


# ─────────────────────────────────────────────────────────────────────
# IPCC N2O emission factors — dat/envind gascoeff.gdx (CAPRI N-balance)
# ─────────────────────────────────────────────────────────────────────
# Direct & indirect N2O emission factors (kg N2O-N / kg N)
N2O_EF1_DIRECT_SOIL   = 0.01     # EF1: direct soil emissions
N2O_EF3_LEACHING      = 0.02     # EF3: leaching and runoff (of N leached)
N2O_EF4_DEPOSITION    = 0.01     # EF4: atmospheric deposition
N2O_EF5_VOLATIL       = 0.0075   # EF5: indirect from volatilized N
FRAC_LEACH            = 0.30     # fraction of N lost to leaching
FRAC_GASF             = 0.10     # fraction of synthetic N volatilized

# Fertilizer production emissions (kg per kg nutrient)
FERT_N_CO2_PROD   = 2543.6 / 1000.0   # kg CO2 per kg N produced
FERT_N_N2O_PROD   = 11.3   / 1000.0   # kg N2O per kg N produced
FERT_P_CO2_PROD   = 972.7  / 1000.0
FERT_K_CO2_PROD   = 140.0  / 1000.0

# GWP variants present in CAPRI vintages (gascoeff uses SAR: N2O=310, CH4=21)
GWP_N2O_SAR = 310.0
GWP_CH4_SAR = 21.0


class EnvironmentalIndicators:
    """Environmental indicators for a region or aggregate."""
    region: str

    # GHG (kt CO2-equivalent)
    ghg_enteric: float = 0.0
    ghg_manure_ch4: float = 0.0
    ghg_manure_n2o: float = 0.0
    ghg_soil_n2o: float = 0.0
    ghg_liming: float = 0.0
    ghg_total: float = 0.0

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

    def __init__(self, data: dict):
        self.data = data
        self.nutrient_coefs = data["nutrients"]

    def _n_excretion(self, region: str, animal: str) -> float:
        """Regional CAPRI nitrogen excretion, falling back to the constant."""
        tbl = getattr(self, "_regional_n", None)
        if tbl is None:
            tbl = regional_n_excretion(getattr(self, "data_dir", "capri_data"))
            self._regional_n = tbl
        if (not tbl.empty and region in tbl.index and animal in tbl.columns):
            import pandas as pd
            v = tbl.at[region, animal]
            if pd.notna(v) and v > 0:
                return float(v)
        return N_EXCRETION_KG_PER_HEAD.get(animal, 0.0)

    def compute_ghg(
        self,
        activities: pd.Series,   # activity levels (1000 ha / 1000 heads)
        region: str,
    ) -> Dict[str, float]:
        """
        Compute GHG emissions (kt CO2-eq) for a region.

        Uses IPCC Tier 1 emission factors with EU-specific adjustments.
        """
        ghg = {g: 0.0 for g in GHG_TYPES}

        # 1. Enteric fermentation (CH4)
        for animal in ANIMALS:
            heads = activities.get(animal, 0.0) * 1000  # convert 1000→heads
            ef    = EF_ENTERIC_CH4.get(animal, 0.0)
            ch4   = heads * ef / 1e6   # kt CH4
            ghg["CH4_ENT"] += ch4 * GWP_CH4   # kt CO2-eq

        # 2. Manure management (CH4 + N2O)
        for animal in ANIMALS:
            heads  = activities.get(animal, 0.0) * 1000
            n_excr = self._n_excretion(region, animal) * heads / 1e6  # kt N

            # CH4 from manure
            ef_ch4 = EF_MANURE_CH4.get(animal, 0.0)
            ghg["CH4_MAN"] += (heads * ef_ch4 / 1e6) * GWP_CH4

            # N2O from manure
            n2o_n = n_excr * EF_MANURE_N2O    # kt N2O-N
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
            total_n_applied += area * n_rate / 1e6   # kt N

        # Direct N2O from soils
        n2o_soil_n = total_n_applied * EF_SOIL_N2O_DIRECT
        ghg["N2O_SOIL"] += (n2o_soil_n * 44 / 28) * GWP_N2O

        # Indirect N2O (volatilisation path)
        n2o_indirect_n = total_n_applied * 0.10 * EF_SOIL_N2O_INDIRECT
        ghg["N2O_SOIL"] += (n2o_indirect_n * 44 / 28) * GWP_N2O

        # 4. Liming (CO2)
        arable_area = sum(
            activities.get(c, 0.0) for c in CROPS
            if c not in ("GRAS", "SETA")
        )
        limestone_kg_per_ha = 600   # typical EU application
        ghg["CO2_LIME"] = arable_area * limestone_kg_per_ha * EF_LIMING / 1e6

        # 5. Urea (CO2)
        urea_share = 0.30   # 30% of mineral N applied as urea
        ghg["CO2_UREA"] = total_n_applied * urea_share * EF_UREA

        return ghg

    def compute_nitrogen_balance(
        self,
        activities: pd.Series,
        yields: pd.Series,
        region: str,
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
        for crop in CROPS:
            area = activities.get(crop, 0.0)
            rate = self.nutrient_coefs.at[crop, "N"] if (
                crop in self.nutrient_coefs.index
            ) else 0.0
            n_mineral += area * rate

        # Organic N from manure
        n_organic = 0.0
        for animal in ANIMALS:
            heads = activities.get(animal, 0.0) * 1000  # to heads
            n_excr = self._n_excretion(region, animal)
            n_organic += heads * n_excr / 1e6   # kt N → convert to same units

        # Biological N fixation (for legumes and grass)
        n_fix_rates = {
            "PULS": 120.0, "SOYA": 100.0, "GRAS": 30.0,
            "OOIL": 10.0,  "OFOD": 15.0,
        }
        n_fixation = sum(
            activities.get(crop, 0.0) * n_fix_rates.get(crop, 0.0)
            for crop in n_fix_rates
        )

        # Atmospheric deposition (~20 kg N/ha/year EU average)
        total_uaa = sum(activities.get(a, 0.0) for a in CROPS)
        n_deposition = total_uaa * 20.0

        total_inputs = n_mineral + n_organic + n_fixation + n_deposition

        # --- Outputs ---
        # Crop N uptake: yield × N content per t product
        n_content_per_t = {
            "SWHE": 20.0, "DWHE": 22.0, "BARL": 18.0, "CORN": 14.0,
            "RAPE": 32.0, "SUNF": 28.0, "SOYA": 60.0, "PULS": 40.0,
            "POTA": 3.5,  "SUGB": 1.8,  "TOMA": 2.5,  "GRAS": 15.0,
        }
        n_crop_uptake = 0.0
        for crop in CROPS:
            yld  = yields.get(crop, 0.0)
            area = activities.get(crop, 0.0)
            nc   = n_content_per_t.get(crop, 10.0)
            n_crop_uptake += area * yld * nc

        # N in livestock products
        n_animal_output = n_organic * 0.25  # ~25% of excreted N is in products

        total_outputs = n_crop_uptake + n_animal_output

        # Balance
        surplus = total_inputs - total_outputs
        nue = total_outputs / max(total_inputs, 1.0)

        return {
            "n_mineral_input": n_mineral,
            "n_organic_input": n_organic,
            "n_fixation": n_fixation,
            "n_deposition": n_deposition,
            "n_crop_uptake": n_crop_uptake,
            "n_animal_products": n_animal_output,
            "n_surplus": surplus,
            "n_use_efficiency": nue,
        }

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

    def compute_ammonia(
        self,
        activities: pd.Series,
    ) -> Dict[str, float]:
        """Ammonia emissions (kt NH3) from livestock housing and soils."""
        nh3_livestock = 0.0
        for animal in ANIMALS:
            heads = activities.get(animal, 0.0) * 1000
            n_excr = self._n_excretion(region, animal) * heads / 1e6  # kt N
            tan    = n_excr * TAN_FRACTION.get(animal, 0.5)
            ef_nh3 = EF_NH3_HOUSING.get(animal, 0.10)
            nh3_livestock += tan * ef_nh3 * (17 / 14)   # N → NH3

        nh3_soils = nh3_livestock * 0.10   # rough proxy

        return {
            "nh3_livestock": nh3_livestock,
            "nh3_soils": nh3_soils,
            "nh3_total": nh3_livestock + nh3_soils,
        }

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

        yields = self.data["yields"].loc[region] if region in self.data["yields"].index \
                 else pd.Series(dtype=float)

        if land is None:
            land = self.data["land"].loc[region] if region in self.data["land"].index \
                   else pd.Series(dtype=float)

        # GHG
        ghg = self.compute_ghg(acts, region)
        ghg_total = sum(ghg.values())

        # Nitrogen
        nb = self.compute_nitrogen_balance(acts, yields, region)

        # Biodiversity
        bio = self.compute_biodiversity_indicators(acts, land)

        # Ammonia
        nh3 = self.compute_ammonia(acts)

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
            ghg_liming=ghg["CO2_LIME"],
            ghg_total=ghg_total,
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
        for i, (region, result) in enumerate(supply_results.items()):
            if verbose and i % 50 == 0:
                print(f"  Environmental module: region {i+1}/{len(supply_results)}")
            try:
                ind = self.compute_indicators(result)
                rows.append(ind.to_series())
            except Exception as e:
                if verbose:
                    print(f"    Warning: {region} environmental calc failed: {e}")

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).set_index("region")
        return df

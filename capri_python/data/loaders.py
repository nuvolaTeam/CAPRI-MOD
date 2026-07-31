"""
Data loaders for CAPRI-Python.

In production use, replace the `load_*` functions with readers
for your actual Eurostat / FADN / FAOSTAT / COMTRADE files.

Data sources to connect:
  - Eurostat NUTS-2 agricultural statistics (ef_ologaa, apro_cpsh1, etc.)
  - FADN (Farm Accountancy Data Network) — farm income, costs
  - FAOSTAT — global production, trade, prices
  - COMTRADE — bilateral trade flows
  - CAPRI own database (available from capri-model.org)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from capri_python.data.definitions import (
    ALL_REGIONS, CROPS, ANIMALS, ALL_ACTIVITIES,
    MARKET_COMMODITIES, ALL_TRADE_REGIONS, NUTRIENTS,
    REGION_TO_COUNTRY, NUTS2_REGIONS, FEED_ITEMS,
)

RNG = np.random.default_rng(42)   # reproducible synthetic data

# Nitrate Vulnerable Zone N limits (kg N/ha) from Nitrates Directive
# Source: CAPRI GAMS envind/envConstraints.gms
NVZ_N_LIMITS_KG_HA = {
    "AT": 0,
    "BL": 0,
    "CZ": 125,
    "CY": 71,
    "DE": 0,
    "DK": 0,
    "EE": 50,
    "ES": 3000,
    "FI": 0,
    "FR": 0,
    "EL": 100,
    "HU": 160,
    "IR": 0,
    "IT": 0,
    "LT": 0,
    "LV": 75,
    "MT": 0,
    "NL": 0,
    "PL": 0,
    "PT": 4000,
    "SE": 0,
    "SI": 0,
    "SK": 80,
    "UK": 6500,
    "BG": 120,
    "RO": 0,
    "HR": 150
}



# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _country_scale(region: str) -> float:
    """Rough scale factor so larger countries get larger values."""
    country = REGION_TO_COUNTRY.get(region, "XX")
    scales = {
        "FR": 1.4, "DE": 1.3, "ES": 1.2, "IT": 1.1, "PL": 1.0,
        "RO": 0.9, "HU": 0.85, "BG": 0.8,  "CZ": 0.8,
        "NL": 0.7, "BE": 0.6, "AT": 0.6,  "DK": 0.65,
        "SE": 0.6, "FI": 0.5, "EL": 0.7,  "PT": 0.65,
        "IE": 0.55,"SK": 0.55,"HR": 0.5,  "SI": 0.4,
        "LT": 0.5, "LV": 0.4, "EE": 0.35,"LU": 0.3,
        "CY": 0.25,"MT": 0.2, "NO": 0.5,
    }
    return scales.get(country, 0.5)


# ---------------------------------------------------------------------------
# Data-file path resolver
# Supports the categorised layout (capri_data/<year>/<category>/file.csv) and,
# as a fallback, a flat layout (capri_data/file.csv). Cross-vintage files such
# as trade live in capri_data/shared/.
# ---------------------------------------------------------------------------
_FILE_CATEGORY = {
    "base_areas.csv": "supply", "yields.csv": "supply", "animal_numbers.csv": "supply",
    "variable_costs.csv": "supply", "input_requirements.csv": "supply",
    "land_availability.csv": "supply", "supply_elasticities_regional.csv": "supply",
    "pmp_diagonal_terms.csv": "supply", "pmp_crossgroup_terms.csv": "supply",
    "pmp_own_price_elasticities.csv": "supply",
    "producer_prices.csv": "market", "world_prices.csv": "market",
    "armington_params.csv": "market",
    "cap_payments.csv": "policy", "eu_mfn_tariffs.csv": "policy", "tariffs.csv": "policy",
    "nutrient_coefs.csv": "environment", "crop_nutrient_export.csv": "environment",
    "manure_ch4_ef_regional.csv": "environment", "climate_zones.csv": "environment",
    "feed_requirements.csv": "feed", "coco_feed_availability_national.csv": "feed",
    # JSON parameter files
    "fao_market_baseline.json": "market",
    "fao_processing_splits.json": "market",
    "fao_demand_own_elas_eu.json": "market",
}
_SHARED_FILES = {"trade_flows.csv": "trade_flows_2017.csv"}

DEFAULT_BASE_YEAR = "2017"


def resolve_data_file(data_dir, filename, base_year=DEFAULT_BASE_YEAR):
    """Return the Path to a data file.

    Order tried: <data_dir>/shared/<file> for cross-vintage files, then
    <data_dir>/<base_year>/<category>/<file>, then a flat <data_dir>/<file>
    fallback. Returns the first existing path; otherwise the categorised path
    (so callers' .exists() checks behave sensibly).
    """
    if data_dir is None:
        return None
    data_dir = Path(data_dir)

    if filename in _SHARED_FILES:
        shared = data_dir / "shared" / _SHARED_FILES[filename]
        if shared.exists():
            return shared
        flat = data_dir / filename
        return flat if flat.exists() else shared

    cat = _FILE_CATEGORY.get(filename)
    if cat:
        categorised = data_dir / base_year / cat / filename
        if categorised.exists():
            return categorised
    flat = data_dir / filename
    if flat.exists():
        return flat
    return (data_dir / base_year / cat / filename) if cat else flat


# ---------------------------------------------------------------------------
# SUPPLY MODULE DATA
# ---------------------------------------------------------------------------

def load_regional_base_areas(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Base crop areas by NUTS-2 region (1000 ha).

    Connect to: Eurostat apro_cpsh1 / ef_ologaa
    Returns: DataFrame [region × crop], values in 1000 ha
    """
    if data_dir and (resolve_data_file(data_dir, "base_areas.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "base_areas.csv"), index_col=0)

    # --- Synthetic fallback with realistic structure ---
    # Typical areas (1000 ha) for an average EU NUTS-2 crop region
    base_areas_template = {
        "SWHE": 45.0,  "DWHE": 8.0,   "RYEM": 5.0,   "BARL": 30.0,
        "OATS": 6.0,   "CORN": 25.0,  "OCER": 4.0,   "POTA": 5.0,
        "SUGB": 8.0,   "SUNF": 12.0,  "RAPE": 18.0,  "SOYA": 6.0,
        "OOIL": 2.0,   "PULS": 4.0,   "TOMA": 3.0,   "OVEG": 6.0,
        "APPL": 2.0,   "OFRU": 3.0,   "CITR": 4.0,   "TAGR": 5.0,
        "WINE": 8.0,   "OLIV": 10.0,  "TOBA": 1.0,   "COTT": 2.0,
        "OFIB": 1.0,   "GRAS": 55.0,  "MAIF": 15.0,  "OFOD": 5.0,
        "SETA": 3.0,
    }

    rows = {}
    for region in ALL_REGIONS:
        scale = _country_scale(region)
        country = REGION_TO_COUNTRY.get(region, "XX")
        n_regions_in_country = len(NUTS2_REGIONS.get(country, [1]))
        noise = RNG.uniform(0.7, 1.3, len(CROPS))
        areas = np.array([base_areas_template.get(c, 0.0) for c in CROPS])
        rows[region] = areas * scale * noise / max(1, n_regions_in_country / 5)

    df = pd.DataFrame(rows, index=CROPS).T
    return df


def load_regional_animal_numbers(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Animal numbers by NUTS-2 region (1000 heads).

    Connect to: Eurostat apro_mt_lspig, apro_mt_lscatl, ef_lsk
    Returns: DataFrame [region × animal]
    """
    if data_dir and (resolve_data_file(data_dir, "animal_numbers.csv")).exists():
        df = pd.read_csv(resolve_data_file(data_dir, "animal_numbers.csv"), index_col=0)
        # CAPRI's herd data uses its own activity codes; the model's ANIMALS set
        # uses aggregate names. Without this map, BCOW/HFRS/SHGP/PIGF/LAYS/BROI
        # silently reindex to zero in the supply base -- the same silent-drop
        # family as the MAIZ/CORN and grassland bugs -- which left livestock
        # activity levels near-zero and made regional livestock scenarios produce
        # meaningless percentage swings.
        HERD_ALIASES = {
            "SCOW": "BCOW",   # suckler cows -> beef cows
            "HEIF": "HFRS",   # heifers
            "SHGO": "SHGP",   # sheep and goats
            "HENS": "LAYS",   # laying hens
            "POUL": "BROI",   # poultry -> broilers
            # PIGF (pig fattening) has no separate herd column; PIGS carries pigs.
            # SOWS stays as-is (breeding sows), COWS is an aggregate kept aside.
        }
        renamed = df.rename(columns=HERD_ALIASES)
        # if both a source and its alias target exist, prefer the aliased CAPRI
        # value only where the target column is absent or zero
        for src, tgt in HERD_ALIASES.items():
            if src in df.columns:
                if tgt not in renamed.columns:
                    renamed[tgt] = df[src]
                else:
                    renamed[tgt] = renamed[tgt].where(
                        renamed[tgt].fillna(0) > 0, df[src])
        return renamed

    base_animals = {
        "DCOW": 25.0, "BCOW": 10.0, "BULL": 8.0,  "HFRS": 12.0,
        "CALV": 15.0, "SHGP": 40.0, "PIGS": 30.0, "PIGF": 80.0,
        "LAYS": 150.0,"BROI": 200.0,"OANI": 20.0,
    }

    rows = {}
    for region in ALL_REGIONS:
        scale = _country_scale(region)
        noise = RNG.uniform(0.6, 1.4, len(ANIMALS))
        nums = np.array([base_animals.get(a, 0.0) for a in ANIMALS])
        rows[region] = nums * scale * noise

    return pd.DataFrame(rows, index=ANIMALS).T


def load_yields(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Crop yields (t/ha) and animal yields (t/head or litre/head) by region.

    Connect to: Eurostat apro_cpsh1 (crops), apro_mk_colm (milk)
    """
    if data_dir and (resolve_data_file(data_dir, "yields.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "yields.csv"), index_col=0)

    base_yields = {   # EU average t/ha (crops) or appropriate units (animals)
        "SWHE": 5.8,  "DWHE": 4.2,  "RYEM": 4.0,  "BARL": 4.8,
        "OATS": 3.6,  "CORN": 7.5,  "OCER": 3.5,  "POTA": 25.0,
        "SUGB": 60.0, "SUNF": 2.0,  "RAPE": 3.0,  "SOYA": 2.5,
        "OOIL": 1.5,  "PULS": 2.5,  "TOMA": 40.0, "OVEG": 18.0,
        "APPL": 18.0, "OFRU": 12.0, "CITR": 20.0, "TAGR": 8.0,
        "WINE": 6.0,  "OLIV": 3.5,  "TOBA": 1.8,  "COTT": 1.2,
        "OFIB": 1.5,  "GRAS": 5.0,  "MAIF": 40.0, "OFOD": 8.0,
        "SETA": 0.0,
        # Animals: dairy (t milk/head), beef/pork/poultry (t carcass/head)
        "DCOW": 7.2,  "BCOW": 0.25, "BULL": 0.32, "HFRS": 0.22,
        "CALV": 0.12, "SHGP": 0.025,"PIGS": 1.8,  "PIGF": 0.095,
        "LAYS": 0.018,"BROI": 0.002,"OANI": 0.003,
    }

    rows = {}
    for region in ALL_REGIONS:
        country = REGION_TO_COUNTRY.get(region, "XX")
        # Northern countries tend to have higher cereal yields
        lat_bonus = 1.1 if country in ("DE", "NL", "DK", "BE", "FR") else 1.0
        noise = RNG.uniform(0.85, 1.15, len(ALL_ACTIVITIES))
        ylds = np.array([base_yields.get(a, 1.0) for a in ALL_ACTIVITIES])
        rows[region] = ylds * lat_bonus * noise

    return pd.DataFrame(rows, index=ALL_ACTIVITIES).T


def load_regional_nutrients(data_dir=None):
    """
    CAPRI regional fertiliser application (DATA2 NITF/PHOF/POTF, kg/ha).

    Returned MultiIndexed by (region, activity) with N / P2O5 / K2O columns.
    """
    import pandas as pd
    from pathlib import Path
    if data_dir is None:
        return None
    p = Path(data_dir) / "sources" / "capreg" / "capreg_nutrient_coefs.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    return df.pivot_table(index=["model_region", "activity"],
                          columns="nutrient", values="value", aggfunc="last")


def load_cap_premium(data_dir=None):
    """CAPRI per-activity CAP premium (DATA2 PRME, EUR/ha or EUR/head)."""
    import pandas as pd
    from pathlib import Path
    if data_dir is None:
        return None
    p = Path(data_dir) / "sources" / "capreg" / "capreg_cap_premium.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, index_col=0)


def load_regional_producer_prices(data_dir=None):
    """
    CAPRI regional producer prices (DATA2 item MPRI, EUR/t), if extracted.

    The national series that preceded this was materially wrong for specialty
    crops -- other vegetables at 30.8 EUR/t against CAPRI's 495.9, tobacco at
    43.8 against 2574.7 -- which is what drove the long-standing validator
    warning about implausible losses on specialty crops.
    """
    import pandas as pd
    from pathlib import Path
    if data_dir is None:
        return pd.DataFrame()
    p = Path(data_dir) / "sources" / "capreg" / "capreg_producer_prices.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, index_col=0)


def load_producer_prices(data_dir: Optional[Path] = None) -> pd.Series:
    """
    Producer prices (EUR/t) at baseline year.

    Connect to: Eurostat apri_ap_ina, FADN prices
    """
    if data_dir and (resolve_data_file(data_dir, "producer_prices.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "producer_prices.csv"),
                           index_col=0).squeeze()

    prices = {
        "SWHE": 175,  "DWHE": 210,  "RYEM": 145,  "BARL": 155,
        "OATS": 140,  "CORN": 170,  "OCER": 145,  "POTA": 120,
        "SUGB": 28,   "SUNF": 340,  "RAPE": 390,  "SOYA": 360,
        "OOIL": 280,  "PULS": 220,  "TOMA": 60,   "OVEG": 280,
        "APPL": 320,  "OFRU": 380,  "CITR": 240,  "TAGR": 420,
        "WINE": 800,  "OLIV": 2800, "TOBA": 1800, "COTT": 350,
        "OFIB": 200,  "GRAS": 40,   "MAIF": 35,   "OFOD": 55,
        "SETA": 0,
        # Animals (EUR per head or EUR/t product)
        "DCOW": 1800, "BCOW": 900,  "BULL": 1400, "HFRS": 900,
        "CALV": 300,  "SHGP": 95,   "PIGS": 380,  "PIGF": 155,
        "LAYS": 12,   "BROI": 2.5,  "OANI": 8,
    }
    return pd.Series(prices)


def load_variable_costs_regional(data_dir: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Full region x activity variable-cost matrix, or None if unavailable.

    The supply model uses this so that regional cost differences actually
    influence cropping decisions. `load_variable_costs` (below) returns the EU
    mean of the same file and is retained for callers that need a single
    representative cost vector (e.g. quick diagnostics, non-regional contexts).
    """
    if data_dir and (resolve_data_file(data_dir, "variable_costs.csv")).exists():
        df = pd.read_csv(resolve_data_file(data_dir, "variable_costs.csv"), index_col=0)
        if df.shape[0] > 50:          # region-level file
            return df
    return None


def load_variable_costs(data_dir: Optional[Path] = None) -> pd.Series:
    """
    Variable production costs (EUR/ha for crops, EUR/head for animals).

    Connect to: FADN SE costs, Eurostat ef_mpric
    """
    if data_dir and (resolve_data_file(data_dir, "variable_costs.csv")).exists():
        df = pd.read_csv(resolve_data_file(data_dir, "variable_costs.csv"), index_col=0)
        # If region-level (rows=NUTS-2), return EU mean per activity
        if df.shape[0] > 50:
            return df.mean()
        return df.squeeze()

    costs = {
        "SWHE": 620,  "DWHE": 700,  "RYEM": 480,  "BARL": 540,
        "OATS": 420,  "CORN": 780,  "OCER": 440,  "POTA": 1800,
        "SUGB": 1100, "SUNF": 420,  "RAPE": 620,  "SOYA": 480,
        "OOIL": 380,  "PULS": 380,  "TOMA": 5500, "OVEG": 3200,
        "APPL": 4200, "OFRU": 3500, "CITR": 3800, "TAGR": 4500,
        "WINE": 6000, "OLIV": 1200, "TOBA": 4200, "COTT": 900,
        "OFIB": 350,  "GRAS": 180,  "MAIF": 580,  "OFOD": 280,
        "SETA": 0,
        "DCOW": 2200, "BCOW": 420,  "BULL": 850,  "HFRS": 480,
        "CALV": 180,  "SHGP": 55,   "PIGS": 320,  "PIGF": 135,
        "LAYS": 8,    "BROI": 1.8,  "OANI": 5,
    }
    return pd.Series(costs)


def load_land_availability(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Available agricultural land by type and region (1000 ha).

    Connect to: Eurostat ef_oluaa, LUCAS land use survey
    """
    if data_dir and (resolve_data_file(data_dir, "land_availability.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "land_availability.csv"), index_col=0)

    rows = {}
    for region in ALL_REGIONS:
        scale = _country_scale(region)
        country = REGION_TO_COUNTRY.get(region, "XX")
        n = len(NUTS2_REGIONS.get(country, [1]))
        base = 250.0 * scale / max(1, n / 5)
        rows[region] = {
            "ARABLE":    base * RNG.uniform(0.8, 1.2),
            "PERMANENT": base * 0.15 * RNG.uniform(0.5, 1.5),
            "GRASSLAND": base * 0.40 * RNG.uniform(0.7, 1.3),
            "FALLOW":    base * 0.03 * RNG.uniform(0.5, 1.5),
            "OTHER_AG":  base * 0.05,
        }
    return pd.DataFrame(rows).T


def load_feed_requirements(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Feed requirements per animal (t DM / head / year).

    Connect to: CAPRI feed module parameters / INRA FEALQ tables
    """
    if data_dir and (resolve_data_file(data_dir, "feed_requirements.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "feed_requirements.csv"), index_col=0)

    import warnings as _w
    _w.warn(
        "feed_requirements: using SYNTHETIC fallback data (no real file present). "
        "This affects feed/environmental outputs, not the price core. "
        "See DATA_SOURCING_REGISTRY.json.",
        stacklevel=2,
    )
    # t DM per head per year × commodity  [SYNTHETIC DATA WARNING]
    req_template = {
        #          SWHE  BARL  CORN  OCER  RAPM  SOYM  SUFM  GRAS  MAIF  OFOD MILK
        "DCOW":  [0.30, 0.20, 0.40, 0.10, 0.08, 0.05, 0.03, 3.50, 1.80, 0.20, 0.0],
        "BCOW":  [0.10, 0.15, 0.20, 0.08, 0.03, 0.02, 0.01, 2.80, 0.80, 0.10, 0.0],
        "BULL":  [0.20, 0.30, 0.50, 0.10, 0.05, 0.04, 0.02, 1.50, 1.20, 0.15, 0.0],
        "HFRS":  [0.15, 0.20, 0.30, 0.08, 0.03, 0.02, 0.01, 2.00, 0.60, 0.10, 0.0],
        "CALV":  [0.05, 0.05, 0.10, 0.02, 0.01, 0.01, 0.00, 0.20, 0.10, 0.03, 0.15],
        "SHGP":  [0.03, 0.04, 0.05, 0.02, 0.01, 0.01, 0.00, 0.40, 0.05, 0.02, 0.0],
        "PIGS":  [0.20, 0.25, 0.30, 0.10, 0.08, 0.10, 0.05, 0.00, 0.00, 0.10, 0.0],
        "PIGF":  [0.10, 0.12, 0.15, 0.05, 0.04, 0.06, 0.03, 0.00, 0.00, 0.05, 0.0],
        "LAYS":  [0.020,0.025,0.030,0.010,0.008,0.010,0.005,0.000,0.000,0.005,0.0],
        "BROI":  [0.002,0.003,0.004,0.001,0.001,0.002,0.001,0.000,0.000,0.001,0.0],
        "OANIИ": [0.005,0.006,0.008,0.002,0.002,0.003,0.001,0.000,0.000,0.001,0.0],
    }
    items = FEED_ITEMS
    df = pd.DataFrame(req_template).T
    df.columns = items
    return df


def load_nutrient_coefficients(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Nutrient use coefficients (kg N/P/K per ha for crops, per head for animals).

    Connect to: Eurostat env_ac_ainah_r2, CAPRI nitrogen module
    """
    if data_dir and (resolve_data_file(data_dir, "nutrient_coefs.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "nutrient_coefs.csv"), index_col=0)

    import warnings as _w
    _w.warn(
        "nutrient_coefs: using SYNTHETIC fallback data (no real file present). "
        "This affects environmental N/P/K outputs, not the price core. "
        "See DATA_SOURCING_REGISTRY.json.",
        stacklevel=2,
    )
    # kg per ha (crops) or per head (animals) — N, P2O5, K2O  [SYNTHETIC DATA WARNING]
    coef_template = {
        "SWHE": [130, 65, 80],  "DWHE": [145, 70, 85],  "RYEM": [90, 45, 70],
        "BARL": [110, 55, 75],  "OATS": [85, 40, 65],   "CORN": [155, 75, 95],
        "OCER": [90, 45, 70],   "POTA": [180, 90, 220],  "SUGB": [140, 60, 180],
        "SUNF": [80, 40, 80],   "RAPE": [175, 75, 90],   "SOYA": [20, 50, 80],
        "OOIL": [70, 35, 60],   "PULS": [15, 40, 70],    "TOMA": [130, 60, 200],
        "OVEG": [110, 55, 180], "APPL": [90, 45, 120],   "OFRU": [85, 40, 110],
        "CITR": [120, 55, 140], "TAGR": [100, 50, 120],  "WINE": [70, 35, 90],
        "OLIV": [60, 30, 70],   "TOBA": [90, 45, 100],   "COTT": [100, 50, 80],
        "OFIB": [60, 30, 50],   "GRAS": [90, 35, 60],    "MAIF": [110, 50, 80],
        "OFOD": [70, 35, 60],   "SETA": [0, 0, 0],
        "DCOW": [85, 30, 15],   "BCOW": [45, 15, 8],     "BULL": [35, 12, 6],
        "HFRS": [28, 10, 5],    "CALV": [8, 3, 1],       "SHGP": [10, 4, 2],
        "PIGS": [22, 9, 4],     "PIGF": [8, 3, 2],       "LAYS": [0.4, 0.2, 0.1],
        "BROI": [0.05, 0.02, 0.01], "OANIИ": [0.1, 0.04, 0.02],
    }
    df = pd.DataFrame(coef_template, index=NUTRIENTS).T
    return df


# ---------------------------------------------------------------------------
# MARKET MODULE DATA
# ---------------------------------------------------------------------------

def load_world_prices(data_dir: Optional[Path] = None) -> pd.Series:
    """
    World reference prices (EUR/t, CIF basis) for market module.

    Connect to: FAOSTAT prices, OECD-FAO Agricultural Outlook
    """
    if data_dir and (resolve_data_file(data_dir, "world_prices.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "world_prices.csv"),
                           index_col=0).squeeze()

    prices = {
        "SWHE": 185,  "DWHE": 220,  "BARL": 160,  "CORN": 175,
        "OCER": 150,  "RAPE": 410,  "SUNF": 360,  "SOYA": 380,
        "OOIL": 290,  "SUGB": 30,   "SUGR": 340,  "POTA": 130,
        "PULS": 230,  "TOMA": 65,   "OVEG": 290,  "APPL": 340,
        "OFRU": 400,  "CITR": 250,  "WINE": 850,  "OLIV": 3000,
        "MILK": 300,  "BUTR": 3200, "SKIM": 2100, "CHES": 3800,
        "WHEY": 650,  "BEEF": 3200, "PORK": 1800, "POUL": 1400,
        "SHGM": 3500, "EGGS": 1200, "FATS": 900,  "OFOD_M": 400,
    }
    return pd.Series(prices)


def load_trade_flows(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Bilateral trade flows (1000 t) between trade regions.

    Connect to: UN COMTRADE, BACI database (CEPII)
    Returns: MultiIndex DataFrame (exporter, importer) × commodity
    """
    if data_dir and (resolve_data_file(data_dir, "trade_flows.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "trade_flows.csv"),
                           index_col=[0, 1])

    regions = ALL_TRADE_REGIONS
    commodities = MARKET_COMMODITIES

    idx = pd.MultiIndex.from_product(
        [regions, regions], names=["exporter", "importer"]
    )
    df = pd.DataFrame(0.0, index=idx, columns=commodities)

    # Synthetic baseline flows — EU exports to ROW, USA exports to EU etc.
    major_flows = [
        ("EU27", "ROW",  {"SWHE": 18000, "BARL": 5000, "CORN": 2000,
                           "BEEF": 280, "PORK": 200, "CHES": 600}),
        ("EU27", "USA",  {"WINE": 1500, "CHES": 200, "OLIV": 150}),
        ("USA",  "EU27", {"SOYA": 8000, "CORN": 3000, "POUL": 200}),
        ("BRA",  "EU27", {"SOYA": 12000,"SOYM": 3000,"POUL": 500}),
        ("ARG",  "EU27", {"SOYA": 5000, "SOYM": 1500,"BEEF": 300}),
        ("NZL",  "EU27", {"BUTR": 180,  "CHES": 120, "SHGM": 200}),
        ("AUS",  "EU27", {"BEEF": 400,  "SWHE": 1000}),
        ("USA",  "ROW",  {"SWHE": 22000,"CORN": 45000,"SOYA": 30000}),
        ("BRA",  "ROW",  {"SOYA": 60000,"POUL": 3000, "BEEF": 1500}),
        ("ARG",  "ROW",  {"SOYA": 40000,"CORN": 20000,"BEEF": 800}),
        ("CHN",  "ROW",  {"PORK": 500,  "OVEG": 2000}),
        ("ROW",  "EU27", {"COTT": 800,  "TOBA": 200, "OFRU": 1500}),
    ]

    for exp, imp, flows in major_flows:
        if (exp, imp) in df.index:
            for comm, val in flows.items():
                if comm in df.columns:
                    df.loc[(exp, imp), comm] = val

    return df


def load_armington_parameters(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Armington elasticities (substitution between domestic and imported goods).

    Based on CAPRI calibrated parameters (Jansson 2007, Britz 2008).
    """
    if data_dir and (resolve_data_file(data_dir, "armington_params.csv")).exists():
        df = pd.read_csv(resolve_data_file(data_dir, "armington_params.csv"), index_col=0)
        return df

    # sigma = Armington substitution elasticity
    # eta   = demand price elasticity
    # eps   = supply price elasticity (from supply module calibration)
    base = {
        "SWHE": {"sigma": 3.9, "eta": -0.2, "eps": 0.3},  # CAPRI GAMS
        "DWHE": {"sigma": 3.9, "eta": -0.18, "eps": 0.25},  # literature
        "BARL": {"sigma": 3.2, "eta": -0.22, "eps": 0.28},  # CAPRI GAMS
        "CORN": {"sigma": 2.7, "eta": -0.2, "eps": 0.32},  # CAPRI GAMS
        "OCER": {"sigma": 2.9, "eta": -0.2, "eps": 0.28},  # CAPRI GAMS
        "RAPE": {"sigma": 3.8, "eta": -0.25, "eps": 0.35},  # CAPRI GAMS
        "SUNF": {"sigma": 3.8, "eta": -0.25, "eps": 0.33},  # CAPRI GAMS
        "SOYA": {"sigma": 2.0, "eta": -0.22, "eps": 0.3},  # CAPRI GAMS
        "OOIL": {"sigma": 3.0, "eta": -0.22, "eps": 0.28},  # literature
        "SUGB": {"sigma": 3.6, "eta": -0.12, "eps": 0.2},  # CAPRI GAMS
        "SUGR": {"sigma": 3.6, "eta": -0.15, "eps": 0.22},  # literature
        "POTA": {"sigma": 2.4, "eta": -0.25, "eps": 0.25},  # CAPRI GAMS
        "PULS": {"sigma": 3.2, "eta": -0.2, "eps": 0.28},  # CAPRI GAMS
        "TOMA": {"sigma": 3.1, "eta": -0.3, "eps": 0.2},  # CAPRI GAMS
        "OVEG": {"sigma": 3.8, "eta": -0.28, "eps": 0.22},  # CAPRI GAMS
        "APPL": {"sigma": 2.8, "eta": -0.3, "eps": 0.25},  # CAPRI GAMS
        "OFRU": {"sigma": 5.1, "eta": -0.28, "eps": 0.22},  # CAPRI GAMS
        "CITR": {"sigma": 4.4, "eta": -0.25, "eps": 0.2},  # CAPRI GAMS
        "WINE": {"sigma": 2.6, "eta": -0.35, "eps": 0.18},  # CAPRI GAMS
        "OLIV": {"sigma": 5.6, "eta": -0.3, "eps": 0.2},  # CAPRI GAMS
        "MILK": {"sigma": 4.0, "eta": -0.15, "eps": 0.25},  # literature
        "BUTR": {"sigma": 2.1, "eta": -0.2, "eps": 0.22},  # CAPRI GAMS
        "SKIM": {"sigma": 3.3, "eta": -0.18, "eps": 0.24},  # CAPRI GAMS
        "CHES": {"sigma": 3.7, "eta": -0.25, "eps": 0.2},  # CAPRI GAMS
        "WHEY": {"sigma": 4.0, "eta": -0.15, "eps": 0.3},  # literature
        "BEEF": {"sigma": 3.5, "eta": -0.4, "eps": 0.15},  # CAPRI GAMS
        "PORK": {"sigma": 6.7, "eta": -0.35, "eps": 0.18},  # CAPRI GAMS
        "POUL": {"sigma": 3.7, "eta": -0.3, "eps": 0.25},  # CAPRI GAMS
        "SHGM": {"sigma": 3.2, "eta": -0.35, "eps": 0.12},  # CAPRI GAMS
        "EGGS": {"sigma": 2.9, "eta": -0.2, "eps": 0.2},  # CAPRI GAMS
        "FATS": {"sigma": 3.0, "eta": -0.2, "eps": 0.22},  # literature
        "OFOD_M": {"sigma": 2.5, "eta": -0.25, "eps": 0.2},  # literature
    }
    return pd.DataFrame(base).T


# ---------------------------------------------------------------------------
# CAP POLICY DATA
# ---------------------------------------------------------------------------

def load_cap_payments(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    CAP direct payment entitlements (EUR/ha) by region.

    Connect to: EU DG-AGRI IACS data, Eurostat agr_r_accts
    """
    if data_dir and (resolve_data_file(data_dir, "cap_payments.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "cap_payments.csv"), index_col=0)

    # Basic Payment Scheme (BPS) / BISS entitlement values
    country_bps = {
        "DE": 280, "FR": 265, "IT": 320, "ES": 210, "PL": 175,
        "NL": 400, "BE": 380, "DK": 310, "SE": 225, "FI": 200,
        "AT": 300, "EL": 420, "PT": 220, "IE": 290, "CZ": 180,
        "HU": 165, "RO": 130, "BG": 125, "SK": 170, "HR": 155,
        "SI": 280, "LT": 145, "LV": 140, "EE": 150, "LU": 350,
        "CY": 330, "MT": 480, "NO": 0,   # Norway outside CAP
    }

    rows = {}
    for region in ALL_REGIONS:
        country = REGION_TO_COUNTRY.get(region, "XX")
        bps = country_bps.get(country, 180)
        rows[region] = {
            "BPS":        bps * RNG.uniform(0.9, 1.1),   # Basic/BISS payment
            "ANC":        85.0 * RNG.uniform(0.5, 1.5),  # Areas of Natural Constraint
            "AES":        50.0 * RNG.uniform(0.0, 2.0),  # Agri-Environment-Climate
            "ORGANIC":    180.0 * RNG.uniform(0.0, 1.5), # Organic farming support
            "COUPLED":    0.0,                             # Coupled support (commodity-specific)
        }
    return pd.DataFrame(rows).T


def load_tariffs(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Import tariffs (ad valorem %) by trade region and commodity.

    Connect to: WTO tariff database, EUR-Lex combined nomenclature
    Returns: DataFrame [region × commodity]
    """
    if data_dir and (resolve_data_file(data_dir, "tariffs.csv")).exists():
        return pd.read_csv(resolve_data_file(data_dir, "tariffs.csv"), index_col=0)

    # EU MFN tariffs (approximate %)
    eu_tariffs = {
        "SWHE": 0.0,  "DWHE": 0.0,  "BARL": 0.0,  "CORN": 0.0,
        "OCER": 0.0,  "RAPE": 0.0,  "SUNF": 0.0,  "SOYA": 0.0,
        "OOIL": 3.2,  "SUGB": 0.0,  "SUGR": 35.0, "POTA": 7.5,
        "PULS": 0.0,  "TOMA": 14.4, "OVEG": 10.2, "APPL": 7.2,
        "OFRU": 5.6,  "CITR": 6.4,  "WINE": 32.0, "OLIV": 7.5,
        "MILK": 0.0,  "BUTR": 82.0, "SKIM": 55.0, "CHES": 40.0,
        "WHEY": 12.0, "BEEF": 65.0, "PORK": 20.0, "POUL": 35.0,
        "SHGM": 52.0, "EGGS": 30.0, "FATS": 12.0, "OFOD_M": 8.0,
    }

    rows = {}
    for region in ALL_TRADE_REGIONS:
        if region == "EU27":
            rows[region] = eu_tariffs
        elif region in ("USA", "CAN", "AUS", "NZL"):
            rows[region] = {k: max(0, v * 0.5 + RNG.uniform(-5, 5))
                            for k, v in eu_tariffs.items()}
        elif region in ("CHN", "IND", "RUS"):
            rows[region] = {k: max(0, v * 0.8 + RNG.uniform(-5, 10))
                            for k, v in eu_tariffs.items()}
        else:
            rows[region] = {k: max(0, v * 0.6 + RNG.uniform(-3, 8))
                            for k, v in eu_tariffs.items()}

    return pd.DataFrame(rows).T


# ---------------------------------------------------------------------------
# CONVENIENCE: LOAD ALL DATA AT ONCE
# ---------------------------------------------------------------------------

def load_all_data(data_dir: Optional[Path] = None, validate: bool = False,
                  base_year: str = DEFAULT_BASE_YEAR) -> dict:
    """Load all baseline datasets, returning a nested dict.

    base_year selects the capri_data/<base_year>/ folder in the categorised
    layout. If validate=True, run the data validator against the manifest first
    and print a short report — a cheap guard against vintage-mixing, missing
    files, and shape drift.
    """
    # Point the resolver at the requested base year for this load.
    global DEFAULT_BASE_YEAR
    _prev_year = DEFAULT_BASE_YEAR
    DEFAULT_BASE_YEAR = base_year
    print("Loading CAPRI baseline data...")
    if validate and data_dir is not None:
        try:
            from capri_python.data.validate_data import validate_data as _vd
            rep = _vd(str(data_dir))
            if rep.n_fail or rep.n_warn:
                print(f"  [data check] {rep.summary()}")
                for name, status, detail in rep.checks:
                    if status != "PASS":
                        print(f"    {status}: {name} — {detail}")
            else:
                print(f"  [data check] {rep.summary()}")
        except Exception as _e:
            print(f"  [data check] skipped: {_e}")
    data = {
        "areas":           load_regional_base_areas(data_dir),
        "animal_numbers":  load_regional_animal_numbers(data_dir),
        "yields":          load_yields(data_dir),
        "producer_prices": load_producer_prices(data_dir),
        "producer_prices_regional": load_regional_producer_prices(data_dir),
        "cap_premium": load_cap_premium(data_dir),
        "nutrients_regional": load_regional_nutrients(data_dir),
        "variable_costs":  load_variable_costs(data_dir),
        "variable_costs_regional": load_variable_costs_regional(data_dir),
        "land":            load_land_availability(data_dir),
        "feed_req":        load_feed_requirements(data_dir),
        "nutrients":       load_nutrient_coefficients(data_dir),
        "world_prices":    load_world_prices(data_dir),
        "trade_flows":     load_trade_flows(data_dir),
        "armington":       load_armington_parameters(data_dir),
        "cap_payments":    load_cap_payments(data_dir),
        "tariffs":         load_tariffs(data_dir),
    }
    print(f"  Loaded data for {len(data['areas'])} regions, "
          f"{len(data['areas'].columns)} crop activities.")
    DEFAULT_BASE_YEAR = _prev_year   # restore module default
    return data


def load_regional_supply_elasticities(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Region-specific own-price supply elasticities from CAPRI PELA matrix.
    Source: estnlp/results.gdx PELA (522,985 econometric estimates).
    Returns DataFrame [region × activity]; NaN where not estimated.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent / 'capri_data'
    f = resolve_data_file(data_dir, "supply_elasticities_regional.csv")
    if f.exists():
        return pd.read_csv(f, index_col=0)
    return pd.DataFrame()


def load_pmp_diagonal_terms(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """PMP diagonal cost terms (VD) from estnlp/results.gdx."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent / 'capri_data'
    f = resolve_data_file(data_dir, "pmp_diagonal_terms.csv")
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()


def load_input_requirements(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Per-hectare input requirement coefficients (VA) from estnlp/results.gdx."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent / 'capri_data'
    f = resolve_data_file(data_dir, "input_requirements.csv")
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()

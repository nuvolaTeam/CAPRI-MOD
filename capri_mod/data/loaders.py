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

import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from capri_mod.data.definitions import (
    ALL_REGIONS, CROPS, ANIMALS, ALL_ACTIVITIES,
    MARKET_COMMODITIES, ALL_TRADE_REGIONS, NUTRIENTS,
    REGION_TO_COUNTRY, NUTS2_REGIONS, FEED_ITEMS,
)
from capri_mod.data.definitions import MS_CODE
from capri_mod.data import land_market_io as _land_market_io
from capri_mod.tableio import read_input





# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Data-file path resolver
# Supports the categorised layout (capri_data/<year>/<category>/file.csv) and,
# as a fallback, a flat layout (capri_data/file.csv). Cross-vintage files such
# as trade live in capri_data/shared/.
# ---------------------------------------------------------------------------
_FILE_CATEGORY = {
    "base_areas.csv": "supply", "yields.csv": "supply", "animal_numbers.csv": "supply",
    "livestock_output_coef.csv": "supply", "nutrients_regional.csv": "supply",
    "livestock_revenue_coef.csv": "supply", "livestock_product_value_coef.csv": "supply", "livestock_product_value_by_market_coef.csv": "supply", "livestock_output_by_product_coef.csv": "supply", "grass_intensity.csv": "supply", "dairy_intensity.csv": "supply", "cattle_intensity.csv": "supply", "genetics_effects.csv": "abatement/mitigation", "lownfeed_effects.csv": "abatement/mitigation", "supplement_effects.csv": "abatement/mitigation", "feed_byproducts.csv": "market", "sugar_processing.csv": "market", "processing_yields.csv": "market", "bilateral_flows_2017.csv": "market", "bilateral_flows_2030.csv": "market", "bilateral_regions_2017.csv": "market", "bilateral_regions_2030.csv": "market", "bilateral_trq_2017.csv": "market", "bilateral_trq_2030.csv": "market", "armington_rho.csv": "market", "world_market_baseline.json": "market", "histosol.csv": "environment", "plant_protection_cost.csv": "supply", "cover_crops.csv": "supply", "winter_cover_share.csv": "supply", "livestock_cost_coef.csv": "supply", "livestock_output_value_coef.csv": "supply", "livestock_premium_coef.csv": "supply", "capri_level_ratio.csv": "supply", "livestock_units.csv": "supply", "land_rents_2017.csv": "supply", "land_rents_2030.csv": "supply", "labour_coef.csv": "supply", "set_aside_split.csv": "supply",
    "livestock_feed_coef.csv": "feed",
    "capri_oilseed_products_baseline.json": "market",
    "biofuel_feedstock.csv": "market", "biofuel_use_share.csv": "market", "biofuel_market.csv": "market", "feed_bulks_eu.csv": "market", "feed_bulks_eu_share.csv": "market", "dairy_processing.csv": "market",
    "dairy_hessian.csv": "market", "dairy_eu_balance.csv": "market", "dairy_eu_demand_elas.csv": "market", "dairy_world_processing.csv": "market", "dairy_world_hessian.csv": "market", "dairy_world_demand_elas.csv": "market", "dairy_world_baseline.json": "market",
    "feed_demand_nonEU.json": "market",
    "feed_ration_2017.json": "feed",
    "fodder_balance_2017.json": "feed",
    "young_animals_2017.json": "supply",   # read by supply_module.young_animal_table
    "mineral_n_price.csv": "supply",       # located for validation; not loaded yet
    "manure_pool_costs.json": "environment",
    "land_market_2017.csv": "supply", "land_market_2030.csv": "supply",
    "land_market_2017_regions.csv": "supply", "land_market_2030_regions.csv": "supply",
    "nh3_factors_capri.json": "environment",
    "landscape_targets_ms.csv": "policy",
    "cap_ceilings_2030.csv": "policy", "premium_scheme_shares_2030.csv": "policy",
    "capri_baseline_surplus_2030.csv": "policy",
    "n_deposition_regional.csv": "environment",
    "manure_trade_2030.csv": "environment",
    "manure_housing_losses_2030.csv": "environment",
    "fertiliser_substitution_2030.csv": "environment",
    "livestock_manure_n_coef.csv": "environment", "livestock_n_export_coef.csv": "environment",
    "livestock_ch4man_coef.csv": "environment", "livestock_ch4ent_coef.csv": "environment",
    "crop_co2_coef.csv": "environment",
    # CAPRI's inner fertiliser distribution model and mineRedu (read by capri_mod.fert.inner_fert_dist)
    "fert_dist_priors_2030.csv": "environment", "fert_dist_crop_groups_2030.csv": "environment",
    "mineral_redu_exemptions.csv": "policy", "mineral_redu_limcres.csv": "policy",
    "organic_targets_ms.csv": "policy",
    # reference data: not loaded by the model, but registered so the
    # validator can resolve and shape-check it like any other input
    "capri_own_price_elasticities.csv": "supply",
    "organic_yield_gap.csv": "policy",
    "variable_costs.csv": "supply",
    "land_availability.csv": "supply", "supply_elasticities_regional.csv": "supply",
    "pmp_capri_2030.csv": "supply", "pmp_capri_2030_animals.csv": "supply",
    "pmp_recipe_2030.csv": "supply", "pmp_recipe_2030_animals.csv": "supply",
    "pmp_recipe_2017.csv": "supply", "pmp_recipe_2017_animals.csv": "supply",
    "pmp_capri_2030_animals_members.csv": "supply", "pmp_recipe_2030_animals_members.csv": "supply",
    "pmp_recipe_2017_animals_members.csv": "supply",
    "pmp_own_price_elasticities.csv": "supply",
    "producer_prices.csv": "market", "world_prices.csv": "market",
    "armington_params.csv": "market",
    "cap_payments.csv": "policy", "crop_premium.csv": "supply", "eu_mfn_tariffs.csv": "policy", "tariffs.csv": "policy",
    "nutrient_coefs.csv": "environment", "crop_nutrient_export.csv": "environment",
    "climate_zones.csv": "environment",
    "feed_requirements.csv": "feed",
    # JSON parameter files
    "fao_market_baseline.json": "market",
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
        return read_input(resolve_data_file(data_dir, "base_areas.csv"), index_col=0)
    raise FileNotFoundError(f"base_areas.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


#: raw animal_numbers.csv uses CAPRI-style names; the model uses these (shared with
#: tools/build_*.py so the names cannot drift apart)
HERD_ALIASES = {
        "SCOW": "BCOW",   # suckler cows -> beef cows
        "HEIF": "HFRS",   # heifers
        # sheep and goats: CAPRI's SHGM (milk) and SHGF (fattening), split from the census SHGO
        # (tools/build/build_shg_split.py)
        "HENS": "LAYS",   # laying hens
        "POUL": "BROI",   # poultry -> broilers
        # PIGS = breeding sows and PIGF = fattening pigs (tools/build_pig_split.py);
        # COWS is an aggregate kept aside.
}


def load_regional_animal_numbers(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Animal numbers by NUTS-2 region (1000 heads).

    Connect to: Eurostat apro_mt_lspig, apro_mt_lscatl, ef_lsk
    Returns: DataFrame [region × animal]
    """
    if data_dir and (resolve_data_file(data_dir, "animal_numbers.csv")).exists():
        df = read_input(resolve_data_file(data_dir, "animal_numbers.csv"), index_col=0)
        # CAPRI's herd data uses its own activity codes; the model's ANIMALS set
        # uses aggregate names. Without this map, BCOW/HFRS/SHGP/PIGF/LAYS/BROI
        # silently reindex to zero in the supply base -- the same silent-drop
        # family as the MAIZ/CORN and grassland bugs -- which left livestock
        # activity levels near-zero and made regional livestock scenarios produce
        # meaningless percentage swings.
        # module-level HERD_ALIASES (shared with the data builders)
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
        return _reconcile_poultry_units(renamed)
    raise FileNotFoundError(f"animal_numbers.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")



#: Grass dry-matter share: CAPRI's DRMA of GRAS (0.22 in every region; capri_data/2017/supply/grass_dm_content.csv,
#: tools/build/build_crop_economics_2017.py), read at load. CAPRI reports GRAS yield as FRESH MATTER; this model works in
#: dry-matter tonnes like every other crop. (It was 0.20; the grass price is built on the same basis, so revenue is
#: CAPRI's MREV either way.)
GRAS_DRY_MATTER_SHARE = None


#: CAPRI reports poultry in MILLION head while every other animal is in
#: thousand head: EU laying hens come to 503 and broilers to 1,474, which are
#: only plausible as millions (real EU laying hens are roughly 370-400 million,
#: broiler places over a billion). Every consumer multiplies a head count by a
#: per-head coefficient assuming thousands, so poultry manure, feed and
#: emissions were understated a thousandfold. Converted once here, so all
#: animal levels are in thousand head.
POULTRY_MILLION_HEAD = ("LAYS", "BROI", "HENS", "POUL")


def _reconcile_poultry_units(herds: pd.DataFrame) -> pd.DataFrame:
    out = herds.copy()
    for col in POULTRY_MILLION_HEAD:
        if col in out.columns:
            out[col] = out[col] * 1000.0
    return out


def _grass_dm_share():
    f = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "supply" / "grass_dm_content.csv"
    return read_input(f, index_col=0)["drma"]


def _reconcile_grass_yield_units(yields: pd.DataFrame) -> pd.DataFrame:
    """Put GRAS on the same dry-matter tonnage basis as every other crop.

    CAPRI reports grass yield as FRESH MATTER in kg/ha (~36,000) while every
    other crop is in t/ha. Converted here, ONCE, at load time.

    It is done here rather than in each consumer because the raw value has
    already caused the same defect FIVE times, in the nitrogen balance, the
    fertiliser module, the income module, `gross_output` and net revenues. Each
    was patched where it surfaced, which fixed the symptom and left the cause:
    every consumer of `yields` was converting independently, and any new
    consumer inherited the bug by default. The failures were severe — grass
    supplied 99.3% of total nitrogen uptake in one case and 99.9% of regional
    gross margin in another, in both cases silently.

    Converting at the source inverts that default: a new consumer now gets the
    right units without knowing this exists.
    """
    if "GRAS" not in yields.columns:
        return yields
    out = yields.copy()
    # a fresh-matter figure is ~36,000 kg/ha; a dry-matter tonnage is single
    # digits, so the threshold distinguishes them without ambiguity and makes
    # the conversion idempotent if applied twice
    mask = out["GRAS"] > 100.0
    if mask.any():
        dm = _grass_dm_share()
        out.loc[mask, "GRAS"] = (out.loc[mask, "GRAS"] / 1000.0
                                 * dm.reindex(out.index[mask]).fillna(float(dm.median())).values)
    return out

def load_yields(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Crop yields (t/ha) and animal yields (CAPRI's YILD per model head / 1000: t of milk or meat per head) by region.
    """
    if data_dir and (resolve_data_file(data_dir, "yields.csv")).exists():
        raw = read_input(resolve_data_file(data_dir, "yields.csv"), index_col=0)
        # animal columns: CAPRI's YILD per model head / 1000 (tools/build/build_animal_yields.py)
        return _reconcile_grass_yield_units(raw)
    raise FileNotFoundError(f"yields.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


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
    df = read_input(p)
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
    base = read_input(p, index_col=0)
    # crops: every region, model codes (tools/build/build_crop_economics_2017.py). The capreg file covers 192 regions in
    # CAPRI's codes, so 56 regions, and fodder, set-aside, wine and fibre everywhere, used to fall back to the
    # random cap_payments.csv
    c = resolve_data_file(data_dir, "crop_premium.csv")
    if c is not None and Path(c).exists():
        crop = read_input(c, index_col=0)
        base = crop.join(base[[k for k in base.columns if k not in crop.columns]], how="left")
    return base


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
    prices = read_input(p, index_col=0)

    # The file carries CAPRI's activity codes for five crops the model names
    # differently, so those columns were never read and the crops silently fell
    # back to the EU-wide price. The same silent-drop family as MAIZ/CORN and
    # the grassland codes.
    #
    # Wine was the damaging case. CAPRI prices it at a median of 1,362 EUR/t
    # (Spain's main wine region at 403); the EU fallback was 95.5, which left
    # wine on a NEGATIVE gross margin in the largest wine regions - Spain -712,
    # Aquitaine -1,413 EUR/ha - where real EU wine margins are strongly
    # positive. An activity sitting at a negative margin responds erratically
    # to any cost shock, which is why wine area fell 11.3% under Farm-to-Fork
    # while olives, correctly priced, stayed flat at -0.1% exactly as CAPRI
    # reports.
    CAPRI_PRICE_ALIASES = {
        "TWIN": ["WINE"],      # table wine
        "OFAR": ["OFOD"],      # fodder on arable land
    }
    for src, targets in CAPRI_PRICE_ALIASES.items():
        if src not in prices.columns:
            continue
        for tgt in targets:
            if tgt not in prices.columns or prices[tgt].isna().all():
                prices[tgt] = prices[src]

    # Where CAPRI has no REGIONAL price, fall back to its NATIONAL one before the
    # EU-wide figure. A missing regional price used to drop straight to the EU
    # average; for wine that meant 95.5 EUR/t in eleven vine-growing regions -
    # 338 kha, including Sicily's 127 kha - where CAPRI's own national prices are
    # 1,362 (Italy), 1,923 (Croatia) and 1,858 (Slovenia). A national price is
    # the same country's own market, so it is a far closer stand-in than the EU.
    nat = _national_capri_prices(data_dir)
    if nat is not None:
        country_alias = MS_CODE
        for col in prices.columns:
            if col not in nat.columns:
                continue
            missing = prices[col].isna()
            if not missing.any():
                continue
            for reg in prices.index[missing]:
                cc = country_alias.get(str(reg)[:2], str(reg)[:2])
                if cc in nat.index and pd.notna(nat.at[cc, col]) and nat.at[cc, col] > 0:
                    prices.at[reg, col] = float(nat.at[cc, col])
    return prices


def _national_capri_prices(data_dir):
    """CAPRI's national market prices (MPRI) by country, if the file is held."""
    import pandas as pd
    from pathlib import Path
    p = Path(data_dir) / "sources" / "capreg" / "capreg_national_prices.csv"
    if not p.exists():
        return None
    return read_input(p, index_col=0)


def load_producer_prices(data_dir: Optional[Path] = None) -> pd.Series:
    """
    Producer prices (EUR/t) at baseline year.

    Connect to: Eurostat apri_ap_ina, FADN prices
    """
    if data_dir and (resolve_data_file(data_dir, "producer_prices.csv")).exists():
        return read_input(resolve_data_file(data_dir, "producer_prices.csv"),
                           index_col=0).squeeze()
    raise FileNotFoundError(f"producer_prices.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_variable_costs_regional(data_dir: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Full region x activity variable-cost matrix, or None if unavailable.

    The supply model uses this so that regional cost differences actually
    influence cropping decisions. `load_variable_costs` (below) returns the EU
    mean of the same file and is retained for callers that need a single
    representative cost vector (e.g. quick diagnostics, non-regional contexts).
    """
    if data_dir and (resolve_data_file(data_dir, "variable_costs.csv")).exists():
        df = read_input(resolve_data_file(data_dir, "variable_costs.csv"), index_col=0)
        if df.shape[0] > 50:          # region-level file
            # CAPRI's own regional input costs (TOIN), as they are. A cap at twice the EU median used to cut
            # permanent and horticultural crops' costs (other fruit in Austria 8,747 EUR/ha against CAPRI's
            # 27,000-37,000) while their revenue stayed CAPRI's, inflating their margins.
            return df
    return None


def load_variable_costs(data_dir: Optional[Path] = None) -> pd.Series:
    """
    Variable production costs (EUR/ha for crops, EUR/head for animals).

    Connect to: FADN SE costs, Eurostat ef_mpric
    """
    if data_dir and (resolve_data_file(data_dir, "variable_costs.csv")).exists():
        df = read_input(resolve_data_file(data_dir, "variable_costs.csv"), index_col=0)
        # If region-level (rows=NUTS-2), return EU mean per activity
        if df.shape[0] > 50:
            return df.mean()
        return df.squeeze()
    raise FileNotFoundError(f"variable_costs.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_land_availability(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Available agricultural land by type and region (1000 ha).

    Connect to: Eurostat ef_oluaa, LUCAS land use survey
    """
    if data_dir and (resolve_data_file(data_dir, "land_availability.csv")).exists():
        return read_input(resolve_data_file(data_dir, "land_availability.csv"), index_col=0)
    raise FileNotFoundError(f"land_availability.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_feed_requirements(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Feed requirements per animal (t DM / head / year).

    Connect to: CAPRI feed module parameters / INRA FEALQ tables
    """
    if data_dir and (resolve_data_file(data_dir, "feed_requirements.csv")).exists():
        return read_input(resolve_data_file(data_dir, "feed_requirements.csv"), index_col=0)
    raise FileNotFoundError(f"feed_requirements.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_nutrient_coefficients(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Nutrient use coefficients (kg N/P/K per ha for crops, per head for animals).

    Connect to: Eurostat env_ac_ainah_r2, CAPRI nitrogen module
    """
    if data_dir and (resolve_data_file(data_dir, "nutrient_coefs.csv")).exists():
        return read_input(resolve_data_file(data_dir, "nutrient_coefs.csv"), index_col=0)
    raise FileNotFoundError(f"nutrient_coefs.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


# ---------------------------------------------------------------------------
# MARKET MODULE DATA
# ---------------------------------------------------------------------------

def load_world_prices(data_dir: Optional[Path] = None) -> pd.Series:
    """
    World reference prices (EUR/t, CIF basis) for market module.

    Connect to: FAOSTAT prices, OECD-FAO Agricultural Outlook
    """
    if data_dir and (resolve_data_file(data_dir, "world_prices.csv")).exists():
        return read_input(resolve_data_file(data_dir, "world_prices.csv"),
                           index_col=0).squeeze()
    raise FileNotFoundError(f"world_prices.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_armington_parameters(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Armington elasticities (substitution between domestic and imported goods).

    Based on CAPRI calibrated parameters (Jansson 2007, Britz 2008).
    """
    if data_dir and (resolve_data_file(data_dir, "armington_params.csv")).exists():
        df = read_input(resolve_data_file(data_dir, "armington_params.csv"), index_col=0)
        return df
    raise FileNotFoundError(f"armington_params.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


# ---------------------------------------------------------------------------
# CAP POLICY DATA
# ---------------------------------------------------------------------------

def load_cap_payments(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    CAP direct payment entitlements (EUR/ha) by region.

    Connect to: EU DG-AGRI IACS data, Eurostat agr_r_accts
    """
    if data_dir and (resolve_data_file(data_dir, "cap_payments.csv")).exists():
        return read_input(resolve_data_file(data_dir, "cap_payments.csv"), index_col=0)
    raise FileNotFoundError(f"cap_payments.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


def load_tariffs(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Import tariffs (ad valorem %) by trade region and commodity.

    Connect to: WTO tariff database, EUR-Lex combined nomenclature
    Returns: DataFrame [region × commodity]
    """
    if data_dir and (resolve_data_file(data_dir, "tariffs.csv")).exists():
        return read_input(resolve_data_file(data_dir, "tariffs.csv"), index_col=0)
    raise FileNotFoundError(f"tariffs.csv not found under {data_dir}: the model runs on CAPRI's data only "
                            f"(the synthetic generator that stood here was removed, Sprint 9s)")


# ---------------------------------------------------------------------------
# CONVENIENCE: LOAD ALL DATA AT ONCE
# ---------------------------------------------------------------------------


def _load_optional_csv(data_dir, filename):
    """Load a region-indexed CSV if present, else None."""
    if not data_dir:
        return None
    path = resolve_data_file(data_dir, filename)
    if path is None or not path.exists():
        return None
    return read_input(path, index_col=0)

def _load_pmp_capri_2030(d: Path, stem: str = "pmp_capri_2030"):
    """{region: {(act_i, act_j): g}} of a set of PMP terms in the model's form: the crops' matrix (<stem>.csv) and the
    animals' herd terms (<stem>_animals.csv, (animal, animal) entries). stem: pmp_capri_2030 (CAPRI's exported 2030
    terms) or pmp_recipe_<year> (capri-mod's own, CAPRI's recipe: tools/build/build_pmp_recipe.py). None without the crops'
    file."""
    f = d / f"{stem}.csv"
    if not f.exists():
        return None
    out = {r: {(a, b): float(v) for a, b, v in zip(g.act_i, g.act_j, g.g)} for r, g in read_input(f).groupby("region")}
    fa = d / f"{stem}_animals.csv"
    # the animals' herd terms grouped for the cattle member splits (HEIL/HEIH/HEIR, the calves per sex) when those are
    # on (RegionalSupplyModel.use_cattle_member_splits, off by default; tools/build/build_animal_pmp_capri_2030.py --splits)
    try:
        from capri_mod.supply.supply_module import RegionalSupplyModel as _RSM
        if getattr(_RSM, "use_cattle_member_splits", False) and (d / f"{stem}_animals_members.csv").exists():
            fa = d / f"{stem}_animals_members.csv"
    except ImportError:
        pass
    if fa.exists():
        for r, a, v in read_input(fa)[["region", "animal", "g"]].itertuples(index=False):
            out.setdefault(r, {})[(a, a)] = float(v)
    return out


def load_all_data(data_dir: Optional[Path] = None, validate: bool = False,
                  base_year: str = DEFAULT_BASE_YEAR) -> dict:
    """Load all baseline datasets, returning a nested dict.

    base_year selects the capri_data/<base_year>/ folder in the categorised
    layout. If validate=True, run the data validator against the manifest first
    and print a short report — a cheap guard against vintage-mixing, missing
    files, and shape drift.

    By design this **fails loudly** when no real data directory is given, rather
    than silently generating synthetic data. A policy tool must run on real,
    validated inputs or not at all: a silent synthetic fallback produces
    plausible-looking but fabricated results, which is the most dangerous failure
    mode for a model whose output informs policy. The synthetic generators were
    removed (Sprint 9s): a missing file raises.
    """
    if data_dir is None:
        raise ValueError(
            "load_all_data requires a real data directory (e.g. "
            "data_dir='capri_data'). Refusing to run on synthetic data: a policy "
            "model must use validated inputs, not fabricated ones."
        )
    # Point the resolver at the requested base year for this load.
    global DEFAULT_BASE_YEAR
    _prev_year = DEFAULT_BASE_YEAR
    DEFAULT_BASE_YEAR = base_year
    print("Loading CAPRI baseline data...")
    if validate and data_dir is not None:
        try:
            from capri_mod.data.validate_data import validate_data as _vd
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
        # CAPRI's labour per activity unit (LABT, LABF, LABP; hours per ha or model head; 2017 and _2030) and its two
        # set-aside activities VSET / FALL (shares, premiums, labour, the split's weight from CAPRI's PMP terms):
        # accounts after the solve (tools/build/build_labour_setaside.py)
        "labour_coef": _load_optional_csv(data_dir, "labour_coef.csv"),
        "set_aside_split": _load_optional_csv(data_dir, "set_aside_split.csv"),
        "animal_numbers":  load_regional_animal_numbers(data_dir),
        "yields":          load_yields(data_dir),
        "producer_prices": load_producer_prices(data_dir),
        "producer_prices_regional": load_regional_producer_prices(data_dir),
        "cap_premium": load_cap_premium(data_dir),
        # Marketed final-product output per head for livestock (kt per 1000
        # head). Built from CAPRI capreg DATA2 by
        # tools/build/build_livestock_output_coef.py; absent -> livestock gross
        # output is reported as NaN rather than from YILD.
        "livestock_output_coef": _load_optional_csv(
            data_dir, "livestock_output_coef.csv"),
        # Mineral nitrogen applied per hectare, by region and crop, from
        # CAPRI's NMIN. Regional rates matter: German grassland gets 44 kg N/ha
        # of mineral nitrogen where the EU average is far lower, and a single
        # EU-wide table made high-fertiliser regions look unfertilised.
        # NOTE: distinct from "nutrients_regional" below, which holds CAPRI's
        # NITF. NITF equals NRET, a nitrogen REQUIREMENT, not an application
        # rate; NMIN is the mineral nitrogen actually applied.
        # Market revenue per head (CAPRI MREV), by region and animal activity.
        "livestock_output_value_coef": _load_optional_csv(data_dir, "livestock_output_value_coef.csv"),
        "livestock_product_value_coef": _load_optional_csv(data_dir, "livestock_product_value_coef.csv"),
        # CAPRI's two grassland activities, GRAE and GRAI (Sprint 7a; tools/build/build_grass_intensity.py)
        # (q_<x>_capri2030 / _recipe2030: the 2030 calibration's curvature, tools/build/build_intensity_q_2030.py; the
        # q_source columns, text, dropped)
        "grass_intensity": (lambda df: df.drop(columns=[c for c in df.columns if c == "capri_region" or c.startswith("q_source")])
                            if df is not None else None)(_load_optional_csv(data_dir, "grass_intensity.csv")),
        # CAPRI's histosols: organic-soil shares, emission factors, fallowing (tools/build/build_histosol.py)
        "histosol": (lambda df: df.drop(columns=[c for c in ("capri_region",) if c in df.columns])
                     if df is not None else None)(_load_optional_csv(data_dir, "histosol.csv")),
        # CAPRI's cattle activities inside the model's animals (tools/build/build_cattle_intensity.py): the low/high-intensity
        # fattening bulls and heifers (Sprint 7c, key = the animal), the replacement heifers ("HFRS:rep") and the
        # fattening / raising calves per sex ("CALV:male", "CALV:female"; 22 October 2026): {region: {key: Series}}
        "cattle_intensity": (lambda df: None if df is None else {
            r: {(row["animal"] if str(row.get("split", "int")) in ("int", "nan") else f"{row['animal']}:{row['split']}"):
                row.drop([c for c in row.index if c in ("animal", "capri_region", "split", "member_low", "member_high")
                          or str(c).startswith("q_source")]).astype(float)
                for _, row in grp.iterrows()}
            for r, grp in df.groupby(level=0)})(_load_optional_csv(data_dir, "cattle_intensity.csv")),
        # CAPRI's cattle genomics (envind/breeding.gms; tools/build/build_genetics_effects.py):
        # {region: {(animal, option): Series}}
        # CAPRI's sugar processing per member state (tools/build/build_sugar_processing.py): {ms: row}
        "sugar_processing": _load_optional_csv(data_dir, "sugar_processing.csv"),
        # per unit of the technology parameter (tech_param: ghgTechMYld / ghgTechFEff, scenario settings in
        # CAPRI); "genetics_effects" is filled at the run's settings (capri_mod/policy/endotech.py)
        "genetics_effects_unit": (lambda df: None if df is None else {
            r: {(row["animal"], row["option"]): pd.concat([
                    row.drop(["animal", "option", "tech_param"], errors="ignore").astype(float),
                    pd.Series({"tech_param": row["tech_param"]}, dtype=object) if "tech_param" in row.index
                    else pd.Series(dtype=object)])
                for _, row in grp.iterrows()}
            for r, grp in df.groupby(level=0)})(
            # CAPRI's breeding options and low-nitrogen feeding (envind/low_n_feed.gms; Sprint 9g,
            # tools/build/build_lownfeed_effects.py) share one table: per-head effects on requirements and manure N
            # and the feed supplements linseed and nitrate (envind/line_nitr.gms; tools/build/build_supplement_effects.py)
            (lambda *ts: (lambda xs: pd.concat(xs) if xs else None)([t for t in ts if t is not None]))(
                _load_optional_csv(data_dir, "genetics_effects.csv"), _load_optional_csv(data_dir, "lownfeed_effects.csv"),
                _load_optional_csv(data_dir, "supplement_effects.csv"))),
        # CAPRI's two dairy activities, DCOL and DCOH (Sprint 7b; tools/build/build_dairy_intensity.py)
        "dairy_intensity": (lambda df: df.drop(columns=[c for c in df.columns if c == "capri_region" or c.startswith("q_source")])
                            if df is not None else None)(_load_optional_csv(data_dir, "dairy_intensity.csv")),
        # CAPRI's winter cover (catch) crops and winter cover shares (tools/build/build_cover_crops.py)
        "cover_crops": (lambda df: df.drop(columns=[c for c in ("capri_region",) if c in df.columns])
                        if df is not None else None)(_load_optional_csv(data_dir, "cover_crops.csv")),
        "winter_cover_share": (lambda df: {r: g.set_index("crop")[["share", "share0"]]
                                           for r, g in df.reset_index().groupby("region")} if df is not None else None)(
            _load_optional_csv(data_dir, "winter_cover_share.csv")),
        # CAPRI's plant-protection, other-input, fertiliser and fuel costs per ha by region and crop, and the
        # animals' other inputs as a share of their input cost (tools/build/build_plant_protection_cost.py): what
        # the pesticide and organic instruments shock
        "plant_protection_cost": (lambda df: {r: g.set_index("activity")[[c for c in (
                                                  "plap_eur_ha", "inpo_eur_ha", "fert_eur_ha", "eful_eur_ha",
                                                  "eful_inpo_eur_ha", "yd_rest_eur_ha", "yd_plap_eur_ha",
                                                  "yd_inpo_eur_ha", "yield_growth", "inpo_toin_share")
                                                  if c in g.columns]]
                                              for r, g in df.reset_index().groupby("region")} if df is not None else None)(
            _load_optional_csv(data_dir, "plant_protection_cost.csv")),
        # the same by product, columns 'ACT.MARKET' (EUR per head): what each market price moves
        "livestock_product_value_by_market_coef": _load_optional_csv(
            data_dir, "livestock_product_value_by_market_coef.csv"),
        # livestock output by CAPRI final product, 'ACT.PRODUCT' (kt per 1000 head; sums to
        # livestock_output_coef): the market bridge splits each animal's output into its products
        "livestock_output_by_product_coef": _load_optional_csv(data_dir, "livestock_output_by_product_coef.csv"),
        "livestock_premium_coef": _load_optional_csv(data_dir, "livestock_premium_coef.csv"),
        # model herd units per unit of CAPRI's LEVL (tools/build/build_capri_level_ratio.py): CAPRI's activity bounds in model units
        "capri_level_ratio": _load_optional_csv(data_dir, "capri_level_ratio.csv"),
        # CAPRI's livestock units per model head (LEVW / LEVL / capri_level_ratio; tools/build/build_livestock_units.py):
        # weights of the reported adoption shares (reporting only)
        "livestock_units": _load_optional_csv(data_dir, "livestock_units.csv"),
        "livestock_cost_coef": _load_optional_csv(data_dir, "livestock_cost_coef.csv"),
        "livestock_revenue_coef": _load_optional_csv(
            data_dir, "livestock_revenue_coef.csv"),
        # CAPRI land market (docs/LAND_USE_FLEXIBILITY.md)
        "land_market": _land_market_io.read(Path(data_dir) / "2017" / "supply" / "land_market_2017"),
        # CAPRI's land market at its 2030 baseline calibration (tools/build/build_land_market.py --year 2030: 2030 land-type levels
        # and p_pmpQuadLandTypes of pmppar_21730); used with SupplyModule.pmp_source "capri2030" at the 2030 market year
        "land_market_2030": _land_market_io.read(Path(data_dir) / "2017" / "supply" / "land_market_2030"),
        # CAPRI's land rents at its calibration points, 2030 and 2017 (tools/build/build_land_rents.py --year;
        # docs/LAND_RENT_CALIBRATION_PLAN.md): {year: {region: {land type: EUR/ha}}}
        "land_rents": {y: (lambda p: {r: {t: float(v) for t, v in (("ARAC", row["rent_arac"]), ("FRUN", row["rent_frun"]),
                                                                   ("GRAS", row["rent_gras"])) if v == v}
                                      for r, row in read_input(p, index_col=0).iterrows()} if p.exists() else None)(
            Path(data_dir) / "2017" / "supply" / f"land_rents_{y}.csv") for y in (2017, 2030)},
        # CAPRI's PMP matrix of the crops at its 2030 baseline calibration, per model region (tools/build/build_pmp_capri_2030.py,
        # KNOWN_ISSUES K61): {region: {(act_i, act_j): g}}, g in EUR/ha per 100% change of the levels
        # and of the animals' herds (tools/build/build_animal_pmp_capri_2030.py, pmp_capri_2030_animals.csv: diagonal only)
        "pmp_capri_2030": _load_pmp_capri_2030(Path(data_dir) / "2017" / "supply"),
        # capri-mod's own terms with CAPRI's recipe (tools/build/build_pmp_recipe.py; SupplyModule.pmp_source "recipe")
        "pmp_recipe": {y: _load_pmp_capri_2030(Path(data_dir) / "2017" / "supply", f"pmp_recipe_{y}") for y in (2017, 2030)},
        # Regional fodder balances (docs/FODDER_BALANCE.md)
        "fodder_balance": (lambda p: __import__("json").load(open(p))["regions"] if p.exists() else None)(
            Path(data_dir) / "2017" / "feed" / "fodder_balance_2017.json"),
        # Feed per head (t): CAPRI 2017 regional FCER/FPRO/FENE totals / herds
        "livestock_feed_coef": _load_optional_csv(
            data_dir, "livestock_feed_coef.csv"),
        # CAPRI's FADN-based organic yield gaps by macro-region and product
        # group (JRC Seville, SUPREMA project), used by the organic instrument.
        "organic_yield_gap": _load_optional_csv(
            data_dir, "organic_yield_gap.csv"),
        # CAPRI's low- and high-intensity dairy yields (DCOL / DCOH), the
        # bounds of the livestock intensity margin.
        # CAPRI's Green Deal targets by member state, from
        # gams/pol_input/greendeal/{landscape,organic}_targets.gdx: the extra
        # landscape land in points of UAA, and the organic conversion in points
        # of arable, grassland and permanent-crop area.
        # CAPRI's own baseline N surplus per ha (2030 reference) - the input to
        # its tiered nitrogen target (pol_input/greendeal/surptot.gms)
        "capri_baseline_surplus": _load_optional_csv(data_dir, "capri_baseline_surplus_2030.csv"),
        # atmospheric N deposition per region, CAPRI 2030 reference (EMEP-based)
        "n_deposition_regional": _load_optional_csv(data_dir, "n_deposition_regional.csv"),
        # manure N trade between regions, CAPRI 2030 reference (MTRADE/EXCRET)
        "manure_trade": _load_optional_csv(data_dir, "manure_trade_2030.csv"),
        # manure N lost in housing and storage per kg excreted, by region and animal, CAPRI 2030 reference
        # ((GASANI + RUNANI) / MANN; fertDistExcr_ distributes what is left; tools/build/build_manure_losses.py)
        "manure_housing_losses": _load_optional_csv(data_dir, "manure_housing_losses_2030.csv"),
        # manure availability and mineral efficiency per region (CAPRI allocation)
        "fertiliser_substitution": _load_optional_csv(data_dir, "fertiliser_substitution_2030.csv"),
        # manure N per head: CAPRI 2017 regional totals / this model's herds
        "livestock_manure_n_coef": _load_optional_csv(data_dir, "livestock_manure_n_coef.csv"),
        # CAPRI's N exported in animal products per model head (CRPR_EXPT, tools/build/build_livestock_n_export_coef.py)
        "livestock_n_export_coef": _load_optional_csv(data_dir, "livestock_n_export_coef.csv"),
        # CAPRI's manure and enteric CH4 per head, CO2 from liming and urea (tools/build/build_ghg_coefs_2017.py)
        "livestock_ch4man_coef": _load_optional_csv(data_dir, "livestock_ch4man_coef.csv"),
        "livestock_ch4ent_coef": _load_optional_csv(data_dir, "livestock_ch4ent_coef.csv"),
        "crop_co2_coef": _load_optional_csv(data_dir, "crop_co2_coef.csv"),
        "landscape_targets_ms": _load_optional_csv(
            data_dir, "landscape_targets_ms.csv"),
        "organic_targets_ms": _load_optional_csv(
            data_dir, "organic_targets_ms.csv"),
        # MITERRA housing days (HD) and share of the grazing time spent in the stable (Et, %) of dairy cows per member
        # state (CAPRI p_rcEmissions(RU,"DAICOW_L",...), abatement/ammonia/RCEmissions.csv): the activity term of the
        # dairy cow's energy requirement (envind/breeding.gms l. 188-191)
        "dairy_grazing_days": (lambda p: (lambda t: t[t.animal_mitt == "DAICOW_L"].pivot(
            index="region", columns="item", values="value"))(read_input(p)) if p is not None and p.exists() else None)(
            Path(data_dir) / "2017" / "abatement" / "ammonia" / "RCEmissions.csv" if data_dir else None),
        # CAPRI's 2030 CAP budgets per premium scheme (CEILVAL, Mio EUR, CAPRI regions) and the split of each model
        # activity's premium over the schemes (PRME by scheme / DPTOTAL); tools/build/build_cap_ceilings_2030.py
        "cap_ceilings_2030": _load_optional_csv(data_dir, "cap_ceilings_2030.csv"),
        "premium_scheme_shares_2030": (lambda p: read_input(p) if p is not None and p.exists() else None)(
            resolve_data_file(data_dir, "premium_scheme_shares_2030.csv")),
        "mineral_n_regional": _load_optional_csv(
            data_dir, "nutrients_regional.csv"),
        "nutrients_regional": load_regional_nutrients(data_dir),
        "variable_costs":  load_variable_costs(data_dir),
        "variable_costs_regional": load_variable_costs_regional(data_dir),
        "land":            load_land_availability(data_dir),
        "feed_req":        load_feed_requirements(data_dir),
        "nutrients":       load_nutrient_coefficients(data_dir),
        "world_prices":    load_world_prices(data_dir),
        "armington":       load_armington_parameters(data_dir),
        "cap_payments":    load_cap_payments(data_dir),
        "tariffs":         load_tariffs(data_dir),
    }
    # cattle genomics at CAPRI star 3.0's default technology settings; CapriModel.run re-scales it to the
    # run's settings (scenario configuration, shared by reference and policy run)
    from capri_mod.policy.endotech import STAR3_DEFAULTS, scale_genetics
    data["genetics_effects"] = scale_genetics(data.get("genetics_effects_unit"), STAR3_DEFAULTS)
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
        return read_input(f, index_col=0)
    return pd.DataFrame()



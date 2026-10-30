"""
CAPRI commodity and region definitions.

Commodities match the ~47 products in CAPRI's market module.
Regions are EU NUTS-2 codes used in the supply module.

Sources:
  - CAPRI commodity list: capri-model.org documentation
  - NUTS-2 codes: Eurostat (2021 classification)
"""

# ---------------------------------------------------------------------------
# COMMODITIES
# ---------------------------------------------------------------------------

# Arable / crop activities (supply module)
CROPS = [
    "SWHE",  # Soft wheat
    "DWHE",  # Durum wheat
    "RYEM",  # Rye and maslin
    "BARL",  # Barley
    "OATS",  # Oats
    "CORN",  # Grain maize
    "OCER",  # Other cereals
    "PARI",  # Paddy rice
    "OCRO",  # Other marketable crops
    "OIND",  # Other industrial crops
    "NURS",  # Nursery plants
    "FLOW",  # Flowers
    "POTA",  # Potatoes
    "SUGB",  # Sugar beet
    "SUNF",  # Sunflower seed
    "RAPE",  # Rape and turnip rape
    "SOYA",  # Soya beans
    "OOIL",  # Other oilseeds
    "PULS",  # Pulses
    "TOMA",  # Tomatoes
    "OVEG",  # Other vegetables
    "APPL",  # Apples and pears
    "OFRU",  # Other fruits
    "CITR",  # Citrus
    "TAGR",  # Table grapes
    "WINE",  # Wine
    "OLIV",  # Olives for oil (CAPRI OLIV; market product: olive oil OLIO, model code OLIV)
    "TABO",  # Table olives (CAPRI TABO, a market product of its own)
    "TOBA",  # Tobacco
    "TEXT",  # Textile crops (CAPRI TEXT: cotton in EL, ES, BG, flax and hemp elsewhere; a market product of its own)
    "GRAS",  # Grass / fodder (permanent grassland)
    "MAIF",  # Maize for forage / silage
    "OFOD",  # Other fodder crops
    "SETA",  # Set-aside
]

# Animal activities
ANIMALS = [
    "DCOW",  # Dairy cows
    "BCOW",  # Beef cows (suckler)
    "BULL",  # Bulls / fattening cattle
    "HFRS",  # Heifers
    "CALV",  # Calves (young animals)
    "SHGM",  # Sheep and goats for milk (CAPRI SHGM)
    "SHGF",  # Sheep and goats for fattening (CAPRI SHGF)
    "PIGS",  # Pigs (breeding sows)
    "PIGF",  # Fattening pigs
    "LAYS",  # Laying hens
    "BROI",  # Broilers
    "OANI",  # Other animals / poultry
]

# Market module commodities (traded goods)
MARKET_COMMODITIES = [
    # cereals as CAPRI's market (arm/arm_sets.gms CERE_DEF): SWHE = wheat (soft + durum), BARL, CORN = maize,
    # RYEM = rye and meslin, OATS, OCER = other cereals, PARI = milled rice
    "SWHE", "BARL", "CORN", "RYEM", "OATS", "OCER", "PARI",
    "RAPE", "SUNF", "SOYA",                    # Oilseeds (other oilseeds, OOIL: no CAPRI market - nonXX_CROPS;
                                                 # a fixed activity, FACT; the pooled world market it had here
                                                 # rested on an invented world total, removed in Sprint 9s)
    # white sugar; sugar beet is processed in the member states (CAPRI: PRCY, beet price follows the sugar
    # price), it has no world market (tools/build/build_sugar_processing.py)
    "SUGR",
    "POTA",                                      # Potatoes
    "PULS",                                      # Pulses
    "TOMA", "OVEG",                              # Vegetables
    "APPL", "OFRU", "CITR", "TAGR",             # Fruits (TAGR table grapes: a CAPRI market, arm_sets CROPS_DEF)
    "TOBA",                                      # Tobacco (a CAPRI market, arm_sets CROPS_DEF)
    "TABO",                                      # Table olives (a CAPRI market, arm_sets CROPS_DEF)
    "TEXT",                                      # Textile crops (a CAPRI market, arm_sets CROPS_DEF)
    "WINE", "OLIV",                              # Wine, olive oil (OLIV = CAPRI's olive oil OLIO)
    "MILK", "BUTR", "SKIM", "CHES", "WHEY",    # Dairy products
    # CAPRI's other dairy products, traded as in CAPRI (Sprint 9f): fresh milk products, cream, concentrated
    # milk, whole milk powder, casein (CAPRI codes)
    "FRMI", "CREM", "COCM", "WMIO", "CASE",
    "BEEF", "PORK", "POUL", "SGMT", "EGGS",    # Livestock products
    # (FATS and OFOD_M, "fats" and "other food", were markets with no supply, no use and invented world
    # totals; CAPRI has no such products - its FATS and PROT are the dairy block's milk fat and protein)
    # oilseed-crushing products (docs/OILSEED_CRUSHING.md): oils and cakes
    "RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC",
    # palm oil and other vegetable oils (CAPRI PLMO, OTHO, arm/arm_sets.gms CROPS_DEF; October 2026): no supply-model
    # activity; supplied by CAPRI's market supply functions (EU: other vegetable oils only)
    "PLMO", "OTHO",
    # fish and the tropical crop products (CAPRI FFIS freshwater fish, SFIS saltwater fish, OAQU other aquatic
    # products, COFF coffee, TEAS tea, COCO cocoa; arm/arm_sets.gms; October 2026): no supply-model activity; supplied
    # by CAPRI's market supply functions (EU: the fish products), demanded as food (GL) and fish as feed (FPRO bulk)
    "FFIS", "SFIS", "OAQU", "COFF", "TEAS", "COCO",
    # biofuels (CAPRI XXBIOF): bio-ethanol and bio-diesel, made from the feedstocks in the market; traded and
    # priced with endogenous biofuel markets (BIOF_M, docs/BIOFUEL_MARKET.md), fixed at the reference without
    "BIOE", "BIOD",
    # distillers' dried grains, the ethanol plants' by-product (CAPRI prodQuantBiofBy_), a traded protein feed
    "DDGS",
    # CAPRI's residual feeds (RESIMP), traded; EU output from milling (FPRI) and sugar processing (FENI) - MaprFeed_
    # (Sprint 9h)
    "FENI", "FPRI",
]

# (PROCESSING_OUTPUTS removed 23 October 2026: read by no model code; the market's processing is MarketModule's
# CRUSH_CHAINS, dairy block and sugar processing, in CAPRI's codes)

# Feed commodities
FEED_ITEMS = [
    "SWHE", "BARL", "CORN", "OCER",        # Grain feeds
    "RAPC", "SOYC", "SUNC",                 # Oilseed cakes (CAPRI's codes)
    "GRAS", "MAIF", "OFOD",                 # Roughages
    "MILK",                                  # Milk for calves
]

# All activities in supply module
ALL_ACTIVITIES = CROPS + ANIMALS

# ---------------------------------------------------------------------------
# REGIONS: CAPRI's regional units of the EU27 and Norway, under CAPRI's 8-character codes (DE110000, FR240000, BL400000,
# DK000000), as CAPRI solves them (RU(SRNUTS2) $ MAP_RR, capmod/define_regional_sets.gms l. 230). Data:
# capri_data/shared/regional_units.csv (tools/build/build_regional_units.py). Until 27 October 2026 the model had 248
# NUTS-2016 regions listed here, mapped to CAPRI's units through crosswalks and split where they did not match
# (docs/design/REGIONAL_UNITS_INVENTORY.md).
# ---------------------------------------------------------------------------
def _load_units():
    import csv
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "capri_data" / "shared" / "regional_units.csv"
    with open(p, newline="") as f:
        return [(r["region"], r["capri_ms"], r["country"]) for r in csv.DictReader(f)]


_UNITS = _load_units()

#: country (NUTS-0: BE, LU, IE, EL, ...) -> its regional units
NUTS2_REGIONS = {}
for _r, _m, _c in _UNITS:
    NUTS2_REGIONS.setdefault(_c, []).append(_r)

class IdentityMap(dict):
    """model region -> CAPRI region: the region itself, the model's regions being CAPRI's units (for code written for
    a lookup table: .get(region) returns the region)."""

    def get(self, key, default=None):
        return key

    def __getitem__(self, key):
        return key

    def __contains__(self, key):
        return True


# Flat list of all regions
ALL_REGIONS = [r for r, _, _ in _UNITS]

# Country membership (NUTS-0; the key of aggregate_supply(by_country=True), mapped to CAPRI's member state by MS_CODE)
REGION_TO_COUNTRY = {r: c for r, _, c in _UNITS}


def country_of(region: str) -> str:
    """The NUTS-0 country of a model region (BE, LU, IE, EL ...), the key of the per-country tables (organic and
    landscape targets, mineral fertiliser prices, PESETA regions). A region's first two characters are CAPRI's member
    state (BL for Belgium and Luxembourg, IR for Ireland), not the country: BL400000 is Luxembourg."""
    return REGION_TO_COUNTRY.get(str(region), str(region)[:2])

# ---------------------------------------------------------------------------
# TRADE REGIONS (market module — 77 countries aggregated to ~40 trade blocks)
# ---------------------------------------------------------------------------

def _shared_rows(name: str) -> list:
    import csv
    from pathlib import Path
    with open(Path(__file__).resolve().parents[2] / "capri_data" / "shared" / name, newline="") as f:
        return list(csv.DictReader(f))


#: CAPRI's EU trade blocks (capri_data/shared/eu_market_blocks.csv, from gams/aggregation/defaultA.agg): member state
#: (CAPRI code) -> block, and the blocks in the file's order (EU_WEST, EU_EAST)
EU_MS_BLOCK = {r["ms"]: r["block"] for r in _shared_rows("eu_market_blocks.csv")}
EU_BLOCKS = tuple(dict.fromkeys(EU_MS_BLOCK.values()))


def _load_trade_regions() -> tuple:
    """The market's trade regions in their order (capri_data/shared/trade_regions.csv, a declared table: trade region,
    CAPRI's region code, the countries). Returns (trade region -> its countries (two-letter codes), CAPRI's region code
    -> trade region). The EU27's countries are those of the regional units whose CAPRI member state is in CAPRI's EU
    trade blocks (EU_MS_BLOCK); ROW holds every CAPRI region the table does not list. The United Kingdom (GBR) and
    the Western Balkans (WBA) are trade regions of their own as in CAPRI since batch 7; Norway (NOR) since K56;
    Egypt, Algeria, Saudi Arabia and Iran, trade regions here without any data until 29 October 2026, fold into ROW
    (KNOWN_ISSUES K45)."""
    regions: dict = {}
    of_capri: dict = {}
    for r in _shared_rows("trade_regions.csv"):
        members = regions.setdefault(r["trade_region"], [])
        if r["country"]:
            members.append(r["country"])
        if r["capri_region"]:
            if of_capri.setdefault(r["capri_region"], r["trade_region"]) != r["trade_region"]:
                raise ValueError(f"trade_regions.csv: {r['capri_region']} in two trade regions")
    if regions.get("EU27", [None]):
        raise ValueError("trade_regions.csv: EU27 must be listed without countries (they come from eu_market_blocks.csv)")
    regions["EU27"] = list(dict.fromkeys(c for _r, m, c in _UNITS if m in EU_MS_BLOCK))
    return regions, of_capri


#: trade region -> its countries; CAPRI's region code (market region or trade block of its market data) -> trade region
TRADE_REGIONS, TRADE_REGION_OF_CAPRI = _load_trade_regions()


def _supply_model_regions_outside_eu() -> dict:
    """The countries outside the EU with supply models (CAPRI's RMSSUP outside the EU): the CAPRI member states of the
    regional units (capri_data/shared/regional_units.csv) that are not in an EU trade block. Returns CAPRI member
    state -> (country code of its units, its trade region: its CAPRI market region, capri_data/shared/rms_to_rm.csv,
    in TRADE_REGION_OF_CAPRI). Like the EU's, their market supply is their supply models' output (KNOWN_ISSUES K56)."""
    rm_of = {r["rms"]: r["rm"] for r in _shared_rows("rms_to_rm.csv")}
    out = {}
    for _r, m, c in _UNITS:
        if m in EU_MS_BLOCK or m in out:
            continue
        rm = rm_of.get(m)
        tr = TRADE_REGION_OF_CAPRI.get(rm) if rm is not None else None
        if tr is None:
            raise ValueError(f"supply-model country {m}: no trade region for its market region {rm} "
                             "(capri_data/shared/rms_to_rm.csv, trade_regions.csv)")
        out[m] = (c, tr)
    return out


#: CAPRI member state -> (country, trade region) of the supply-model countries outside the EU (Norway: NO, NOR)
SUP_NONEU = _supply_model_regions_outside_eu()

ALL_TRADE_REGIONS = list(TRADE_REGIONS.keys())

# ---------------------------------------------------------------------------
# LAND USE TYPES
# ---------------------------------------------------------------------------

LAND_TYPES = [
    "ARABLE",       # Arable land (UAA)
    "PERMANENT",    # Permanent crops (orchards, vineyards, olives)
    "GRASSLAND",    # Permanent grassland
    "FALLOW",       # Fallow land (includes set-aside)
    "OTHER_AG",     # Other agricultural land
]

# ---------------------------------------------------------------------------
# NUTRIENT / ENVIRONMENTAL SETS
# ---------------------------------------------------------------------------

NUTRIENTS = ["N", "P2O5", "K2O"]   # Macro nutrients

GHG_TYPES = [
    "CH4_ENT",   # Enteric fermentation CH4
    "CH4_MAN",   # Manure management CH4
    "N2O_MAN",   # Manure management N2O
    "N2O_SOIL",  # Agricultural soils N2O
    "CO2_LIME",  # Liming CO2
    "CO2_UREA",  # Urea application CO2
]

# ---------------------------------------------------------------------------
# TIME
# ---------------------------------------------------------------------------

# (BASE_YEAR = 2012 and PROJECTION_YEARS removed 23 October 2026: wrong and unused; the base year is 2017, the
# setting run.base_year, and a projection's years come from its trajectory)


# ---------------------------------------------------------------------------
# CAPRI member-state codes (sets.gms NUTS0): Belgium and Luxembourg are one member state in CAPRI (BL000000), Ireland is
# IR000000, Greece EL000000, the United Kingdom UK000000; every other country keeps its NUTS prefix. Data:
# capri_data/shared/capri_member_state_codes.csv. MS_CODE maps a two-letter prefix to CAPRI's (identity where they
# agree, so MS_CODE.get(p, p) works for any prefix); capri_ms(region) gives the 8-character CAPRI member state.
# ---------------------------------------------------------------------------
def _load_ms_codes():
    import csv
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "capri_data" / "shared" / "capri_member_state_codes.csv"
    with open(p, newline="") as f:
        return {r["nuts_prefix"]: r["capri_ms"][:2] for r in csv.DictReader(f)}


MS_CODE = _load_ms_codes()


def capri_ms(region: str) -> str:
    """CAPRI member state of a model region (CAPRI's code) or a country prefix: 'BL210000' -> 'BL000000',
    'IR010000' -> 'IR000000', 'BE' -> 'BL000000'."""
    p = str(region)[:2]
    return MS_CODE.get(p, p) + "000000"

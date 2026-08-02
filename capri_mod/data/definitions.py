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
    "OLIV",  # Olives / olive oil
    "TOBA",  # Tobacco
    "COTT",  # Cotton
    "OFIB",  # Other fibre crops
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
    "SHGP",  # Sheep and goats
    "PIGS",  # Pigs (breeding sows)
    "PIGF",  # Fattening pigs
    "LAYS",  # Laying hens
    "BROI",  # Broilers
    "OANI",  # Other animals / poultry
]

# Market module commodities (traded goods)
MARKET_COMMODITIES = [
    "SWHE", "DWHE", "BARL", "CORN", "OCER",  # Cereals
    "RAPE", "SUNF", "SOYA", "OOIL",            # Oilseeds
    "SUGB", "SUGR",                              # Sugar (beet + refined)
    "POTA",                                      # Potatoes
    "PULS",                                      # Pulses
    "TOMA", "OVEG",                              # Vegetables
    "APPL", "OFRU", "CITR",                     # Fruits
    "WINE", "OLIV",                              # Wine, olive oil
    "MILK", "BUTR", "SKIM", "CHES", "WHEY",    # Dairy products
    "BEEF", "PORK", "POUL", "SHGM", "EGGS",    # Livestock products
    "FATS", "OFOD_M",                            # Fats, other food
]

# Processed / secondary products
PROCESSING_OUTPUTS = {
    "SUGB": ["SUGR"],           # Sugar beet → white sugar
    "RAPE": ["RAPO", "RAPM"],   # Rapeseed → oil + meal
    "SUNF": ["SUFO", "SUFM"],   # Sunflower → oil + meal
    "SOYA": ["SOYO", "SOYM"],   # Soybeans → oil + meal
    "MILK": ["BUTR", "SKIM", "CHES", "WHEY"],
}

# Feed commodities
FEED_ITEMS = [
    "SWHE", "BARL", "CORN", "OCER",        # Grain feeds
    "RAPM", "SOYM", "SUFM",                 # Protein meals
    "GRAS", "MAIF", "OFOD",                 # Roughages
    "MILK",                                  # Milk for calves
]

# All activities in supply module
ALL_ACTIVITIES = CROPS + ANIMALS

# ---------------------------------------------------------------------------
# REGIONS  (EU NUTS-2, Norway, Western Balkans)
# ---------------------------------------------------------------------------

# Selected representative NUTS-2 regions (full list has ~280)
# Organised by member state for data loading convenience
NUTS2_REGIONS = {
    # Germany (DE)
    "DE": [
        "DE11", "DE12", "DE13", "DE14",  # Baden-Württemberg
        "DE21", "DE22", "DE23", "DE24", "DE25", "DE26", "DE27",  # Bavaria
        "DE30",  # Berlin
        "DE40",  # Brandenburg
        "DE50",  # Bremen
        "DE60",  # Hamburg
        "DE71", "DE72", "DE73",  # Hessen
        "DE80",  # Mecklenburg-Vorpommern
        "DE91", "DE92", "DE93", "DE94",  # Lower Saxony
        "DEA1", "DEA2", "DEA3", "DEA4", "DEA5",  # NRW
        "DEB1", "DEB2", "DEB3",  # Rhineland-Palatinate
        "DEC0",  # Saarland
        "DED2", "DED4", "DED5",  # Saxony
        "DEE0",  # Saxony-Anhalt
        "DEF0",  # Schleswig-Holstein
        "DEG0",  # Thuringia
    ],
    # France (FR)
    "FR": [
        "FR10",  # Île-de-France
        "FRB0", "FRC1", "FRC2",  # Centre, Bourgogne, Auvergne
        "FRD1", "FRD2",  # Normandie
        "FRE1", "FRE2",  # Nord
        "FRF1", "FRF2", "FRF3",  # Grand Est
        "FRG0",  # Pays de la Loire
        "FRH0",  # Bretagne
        "FRI1", "FRI2", "FRI3",  # Nouvelle-Aquitaine
        "FRJ1", "FRJ2",  # Occitanie
        "FRK1", "FRK2",  # Auvergne-Rhône-Alpes
        "FRL0",  # Provence-Alpes-Côte d'Azur
        "FRM0",  # Corse
    ],
    # Italy (IT)
    "IT": [
        "ITC1", "ITC2", "ITC3", "ITC4",  # NW Italy
        "ITH1", "ITH2", "ITH3", "ITH4", "ITH5",  # NE Italy
        "ITI1", "ITI2", "ITI3", "ITI4",  # Central Italy
        "ITF1", "ITF2", "ITF3", "ITF4", "ITF5", "ITF6",  # South
        "ITG1", "ITG2",  # Islands
    ],
    # Spain (ES)
    "ES": [
        "ES11", "ES12", "ES13",  # NW Spain
        "ES21", "ES22", "ES23", "ES24",  # NE Spain
        "ES30",  # Madrid
        "ES41", "ES42", "ES43",  # Castile
        "ES51", "ES52", "ES53",  # Catalonia/Valencia
        "ES61", "ES62",  # Andalusia
        "ES63", "ES64",  # Ceuta, Melilla
        "ES70",  # Canarias
    ],
    # Poland (PL)
    "PL": [
        "PL21", "PL22",  # Małopolskie, Śląskie
        "PL31", "PL32", "PL33", "PL34",  # Lubelskie, etc.
        "PL41", "PL42", "PL43",  # Wielkopolskie
        "PL51", "PL52",  # Lower Silesia
        "PL61", "PL62", "PL63",  # Kujawy, Warmia
        "PL71", "PL72",  # Łódź, Świętokrzyskie
        "PL81", "PL82", "PL84",  # Lubelskie
        "PL91", "PL92",  # Mazowieckie
    ],
    # Netherlands (NL)
    "NL": ["NL11", "NL12", "NL13", "NL21", "NL22", "NL23",
            "NL31", "NL32", "NL33", "NL34", "NL41", "NL42"],
    # Belgium (BE)
    "BE": ["BE10", "BE21", "BE22", "BE23", "BE24", "BE25",
            "BE31", "BE32", "BE33", "BE34", "BE35"],
    # Denmark (DK)
    "DK": ["DK01", "DK02", "DK03", "DK04", "DK05"],
    # Sweden (SE)
    "SE": ["SE11", "SE12", "SE21", "SE22", "SE23",
            "SE31", "SE32", "SE33"],
    # Finland (FI)
    "FI": ["FI19", "FI1B", "FI1C", "FI1D", "FI20"],
    # Austria (AT)
    "AT": ["AT11", "AT12", "AT13", "AT21", "AT22",
            "AT31", "AT32", "AT33", "AT34"],
    # Greece (EL)
    "EL": ["EL30", "EL41", "EL42", "EL43", "EL51",
            "EL52", "EL53", "EL54", "EL61", "EL62", "EL63", "EL64", "EL65"],
    # Portugal (PT)
    "PT": ["PT11", "PT15", "PT16", "PT17", "PT18", "PT20", "PT30"],
    # Ireland (IE)
    "IE": ["IE04", "IE05", "IE06"],
    # Czech Republic (CZ)
    "CZ": ["CZ01", "CZ02", "CZ03", "CZ04", "CZ05", "CZ06", "CZ07", "CZ08"],
    # Hungary (HU)
    "HU": ["HU11", "HU12", "HU21", "HU22", "HU23",
            "HU31", "HU32", "HU33"],
    # Romania (RO)
    "RO": ["RO11", "RO12", "RO21", "RO22", "RO31", "RO32",
            "RO41", "RO42"],
    # Bulgaria (BG)
    "BG": ["BG31", "BG32", "BG33", "BG34", "BG41", "BG42"],
    # Slovakia (SK)
    "SK": ["SK01", "SK02", "SK03", "SK04"],
    # Croatia (HR)
    "HR": ["HR03", "HR04", "HR05", "HR06"],
    # Slovenia (SI)
    "SI": ["SI03", "SI04"],
    # Lithuania (LT)
    "LT": ["LT01", "LT02"],
    # Latvia (LV)
    "LV": ["LV00"],
    # Estonia (EE)
    "EE": ["EE00"],
    # Luxembourg (LU)
    "LU": ["LU00"],
    # Cyprus (CY)
    "CY": ["CY00"],
    # Malta (MT)
    "MT": ["MT00"],
    # Norway (NO)
    "NO": ["NO01", "NO02", "NO03", "NO04", "NO05", "NO06", "NO07"],
}

# Flat list of all regions
ALL_REGIONS = [r for regions in NUTS2_REGIONS.values() for r in regions]

# Country membership (for policy aggregation)
REGION_TO_COUNTRY = {
    r: country
    for country, regions in NUTS2_REGIONS.items()
    for r in regions
}

# ---------------------------------------------------------------------------
# TRADE REGIONS (market module — 77 countries aggregated to ~40 trade blocks)
# ---------------------------------------------------------------------------

TRADE_REGIONS = {
    "EU27":  list(NUTS2_REGIONS.keys()) + ["LU", "CY", "MT"],  # handled as one block in market
    "USA":   ["US"],
    "CAN":   ["CA"],
    "BRA":   ["BR"],
    "ARG":   ["AR"],
    "AUS":   ["AU"],
    "NZL":   ["NZ"],
    "CHN":   ["CN"],
    "IND":   ["IN"],
    "RUS":   ["RU"],
    "UKR":   ["UA"],
    "TUR":   ["TR"],
    "MEX":   ["MX"],
    "IDN":   ["ID"],
    "JPN":   ["JP"],
    "KOR":   ["KR"],
    "THA":   ["TH"],
    "VNM":   ["VN"],
    "PAK":   ["PK"],
    "BGD":   ["BD"],
    "NGA":   ["NG"],
    "ZAF":   ["ZA"],
    "ETH":   ["ET"],
    "EGY":   ["EG"],
    "MAR":   ["MA"],
    "DZA":   ["DZ"],
    "SAU":   ["SA"],
    "IRN":   ["IR"],
    "ROW":   ["ROW"],  # Rest of world
}

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

BASE_YEAR = 2012          # CAPRI baseline calibration year
PROJECTION_YEARS = [2030, 2040, 2050]

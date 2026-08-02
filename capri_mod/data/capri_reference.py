"""
CAPRI Reference Constants
=========================
Extracted directly from CAPRI GAMS source (gams.7z).
Source files: arm/arm_sets.gms, sets.gms, envind/*.gms, fert/*.gms

DO NOT EDIT manually — regenerate from GAMS source.
"""

# CAPRI market commodity codes and descriptions (from arm/arm_sets.gms)
CAPRI_COMMODITY_CODES = {
    "OTHO": "Other vegeatable oils",
    "PLMO": "Palm oil",
    "SUNF": "Sunflower",
    "SUGA": "Sugar",
    "TWIN": "Table wine",
    "BIOE": "Bioethanol",
    "BIOD": "Biodiesel",
    "DDGS": "destilled dried grains from bio-ethanol production",
    "POTA": "Potatoes",
    "PULS": "Pulses",
    "APPL": "Apples pears peaches",
    "CITR": "Citrus",
    "OFRU": "Other fruits",
    "OLIO": "Olive oil",
    "OVEG": "Other vegetables",
    "TAGR": "Table grapes",
    "TOBA": "Tobacco",
    "TOMA": "Tomatoes",
    "TEXT": "Textiles",
    "TABO": "Table olives",
    "BEEF": "Beef",
    "PORK": "Pork meat",
    "POUM": "Poultry",
    "SGMT": "Sheep and goat meat",
    "EGGS": "Eggs",
    "FENI": "Energy rich feed (by-products of sugar-beet processing), manioc, cassava etc.",
    "FPRI": "Protein rich feed (by-products of milling and brewing industry)",
    "FRMI": "Fresh milk products",
    "FFIS": "Freshwater fish",
    "SFIS": "Saltwater fish",
    "OAQU": "Other acquatic product"
}

# Armington CES elasticities (from special_ch/market1_ch.gms, arm/market1.gms)
# rhoArm1 = domestic/import substitution; rhoArm2 = bilateral import substitution  
CAPRI_RHOARM1 = {
    "SUGA": 12.0,
    "DDGS": 2.0,
    "TAGR": 0.5,
    "TABO": 0.5,
    "SOYA": 6.0,
    "CHES": 2.0,
    "FRMI": 2.0,
    "OVEG": 1.5,
    "OFRU": 3.0,
    "RICE": 2.0
}
CAPRI_RHOARM2 = {
    "SUGA": 12.0,
    "SOYA": 8.0,
    "CHES": 4.0,
    "FRMI": 4.0,
    "OVEG": 1.5,
    "OFRU": 3.0,
    "RICE": 4.0
}
CAPRI_RHOARM1_DEFAULT = 8.0
CAPRI_RHOARM2_DEFAULT = 10.0

# NVZ N limits by country (kg N/ha, from envind/envConstraints.gms)
CAPRI_NVZ_N_LIMITS = {
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

# Atmospheric N deposition (kg N/ha/yr, from fert/fertpar.gms)
CAPRI_ATM_N_DEP = {}

# N use efficiency factors by crop (from fert/fertpar.gms)
# NOM = fraction of applied mineral N taken up by crop
# AtmDep = proportion of atmospheric N fixed
# NITRO = nitrogen multiplier
CAPRI_N_FACTORS = {
    "SWHE": {
        "NOM": 0.82,
        "AtmDep": 0.55,
        "NITRO": 0.98
    },
    "RYEM": {
        "NOM": 0.82,
        "AtmDep": 0.55,
        "NITRO": 0.98
    },
    "BARL": {
        "NOM": 0.82,
        "AtmDep": 0.55,
        "NITRO": 0.98
    },
    "OATS": {
        "NOM": 0.82,
        "AtmDep": 0.55,
        "NITRO": 0.98
    },
    "MAIZ": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "RAPE": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "SUNF": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "SOYA": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "OOIL": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "PULS": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "POTA": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "SUGB": {
        "NOM": 0.8,
        "AtmDep": 0.57,
        "NITRO": 0.98
    },
    "OIND": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "TOMA": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "OVEG": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "APPL": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "OFRU": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "NURS": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "FLOW": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "OCRO": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "MAIF": {
        "NOM": 0.75,
        "AtmDep": 0.5,
        "NITRO": 0.98
    },
    "ROOF": {
        "NOM": 0.75,
        "AtmDep": 0.58,
        "NITRO": 0.98
    },
    "OFAR": {
        "NOM": 0.75,
        "AtmDep": 0.58,
        "NITRO": 0.98
    },
    "FLEG": {
        "NOM": 0.75,
        "AtmDep": 0.58,
        "NITRO": 0.98
    },
    "GRAE": {
        "NOM": 0.82,
        "AtmDep": 0.8,
        "NITRO": 0.98
    },
    "GRAI": {
        "NOM": 0.82,
        "AtmDep": 0.8,
        "NITRO": 0.98
    },
    "FALL": {
        "NOM": 0.82,
        "AtmDep": 0.58,
        "NITRO": 0.98
    }
}

# IFA fertiliser use (kg N/ha) by country and crop (from fert/fert_capdis_decl.gms)
CAPRI_IFA_FERT = {
    "DE": {
        "BARL": 150.0,
        "DWHE": 102.0,
        "GRAS": 85.0,
        "MAIF": 150.0,
        "MAIZ": 115.0,
        "OATS": 94.3,
        "OCER": 140.0,
        "OFAR": 25.0,
        "PARI": 170.0,
        "POTA": 145.0,
        "PULS": 50.0,
        "RAPE": 165.0,
        "ROOF": 165.0
    },
    "IT": {
        "BARL": 70.0,
        "DWHE": 15.0,
        "GRAS": 85.0,
        "MAIF": 184.0,
        "MAIZ": 95.0,
        "OATS": 8.0,
        "OCER": 110.0,
        "OFAR": 30.0,
        "PARI": 80.0,
        "POTA": 90.0,
        "PULS": 40.0,
        "RAPE": 82.0,
        "ROOF": 110.0
    },
    "NL": {
        "BARL": 85.0,
        "DWHE": 240.0,
        "GRAS": 34.0,
        "MAIF": 44.0,
        "MAIZ": 85.0,
        "OATS": 30.0,
        "OCER": 168.0,
        "OFAR": 20.0,
        "PARI": 180.0,
        "POTA": 108.0,
        "PULS": 190.0,
        "RAPE": 125.0
    },
    "NO": {
        "BARL": 100.0,
        "DWHE": 100.0,
        "GRAS": 96.0,
        "MAIF": 110.0,
        "MAIZ": 100.0,
        "OATS": 110.0,
        "OCER": 118.0,
        "OFAR": 150.0
    },
    "PL": {
        "BARL": 63.4,
        "DWHE": 74.0,
        "GRAS": 32.8,
        "MAIF": 81.8,
        "MAIZ": 81.8,
        "OATS": 43.4,
        "OCER": 62.3,
        "OFAR": 17.5,
        "PARI": 52.3,
        "POTA": 16.7,
        "PULS": 102.4,
        "RAPE": 127.9,
        "ROOF": 27.8,
        "RYEM": 131.8,
        "SOYA": 74.0,
        "SUGB": 74.0,
        "SUNF": 46.2
    },
    "PT": {
        "BARL": 60.0,
        "DWHE": 42.0,
        "GRAS": 80.0,
        "MAIF": 160.0,
        "MAIZ": 60.0,
        "OATS": 80.0,
        "OCER": 100.0,
        "OFAR": 5.0,
        "PARI": 100.0,
        "POTA": 150.0,
        "PULS": 80.0,
        "RAPE": 120.0
    },
    "SK": {
        "BARL": 42.9,
        "DWHE": 60.0,
        "GRAS": 20.3,
        "MAIF": 69.1,
        "MAIZ": 85.8,
        "OATS": 35.9,
        "OCER": 62.4,
        "OFAR": 84.9,
        "PARI": 26.3,
        "POTA": 97.7,
        "PULS": 55.9,
        "RAPE": 57.0,
        "ROOF": 59.1,
        "RYEM": 76.9,
        "SOYA": 75.6,
        "SUGB": 35.1,
        "SUNF": 29.3
    },
    "ES": {
        "BARL": 90.0,
        "DWHE": 39.0,
        "GRAS": 80.0,
        "MAIF": 225.0,
        "MAIZ": 80.0,
        "OATS": 26.6,
        "OCER": 142.0,
        "OFAR": 9.0,
        "PARI": 109.0,
        "POTA": 178.0,
        "PULS": 14.0,
        "RAPE": 95.0,
        "ROOF": 205.0
    },
    "SE": {
        "BARL": 78.0,
        "DWHE": 60.0,
        "GRAS": 68.0,
        "MAIF": 85.0,
        "MAIZ": 83.0,
        "OATS": 110.0,
        "OCER": 100.0,
        "OFAR": 60.0,
        "PARI": 120.0,
        "POTA": 100.0
    },
    "CH": {
        "BARL": 123.0,
        "DWHE": 155.0,
        "GRAS": 45.0,
        "MAIF": 72.0,
        "MAIZ": 160.0,
        "OATS": 111.0,
        "OCER": 62.0,
        "OFAR": 161.0,
        "PARI": 23.0,
        "POTA": 172.0,
        "PULS": 143.0,
        "RAPE": 41.0,
        "ROOF": 164.0
    },
    "UK": {
        "BARL": 118.0,
        "DWHE": 183.0,
        "GRAS": 105.0,
        "MAIF": 52.0,
        "MAIZ": 100.0,
        "OATS": 75.0,
        "OCER": 155.0,
        "OFAR": 5.0,
        "PARI": 185.0,
        "POTA": 100.0,
        "PULS": 50.0,
        "RAPE": 125.0
    },
    "BG": {
        "BARL": 51.7,
        "DWHE": 3.4,
        "GRAS": 16.1,
        "MAIF": 8.4,
        "MAIZ": 11.1,
        "OATS": 60.4,
        "OCER": 11.1
    },
    "EE": {
        "BARL": 71.0,
        "DWHE": 47.0,
        "GRAS": 60.0,
        "MAIF": 41.0,
        "MAIZ": 13.0,
        "OATS": 100.0,
        "OCER": 13.0,
        "OFAR": 86.0,
        "PARI": 100.0,
        "POTA": 70.0
    },
    "LV": {
        "BARL": 43.6,
        "DWHE": 20.0,
        "GRAS": 16.9,
        "MAIF": 20.0,
        "MAIZ": 72.5,
        "OATS": 91.7,
        "OCER": 94.2,
        "OFAR": 76.0,
        "PARI": 80.1,
        "POTA": 20.0,
        "PULS": 0.9,
        "RAPE": 20.0
    },
    "TR": {
        "BARL": 85.3,
        "DWHE": 97.0,
        "GRAS": 53.2,
        "MAIF": 90.5,
        "MAIZ": 71.5,
        "OATS": 98.1,
        "OCER": 96.1,
        "OFAR": 97.9,
        "PARI": 88.3,
        "POTA": 87.3,
        "PULS": 98.6,
        "RAPE": 67.7,
        "ROOF": 71.2
    },
    "AT": {
        "BARL": 98.0,
        "DWHE": 33.0,
        "GRAS": 103.0,
        "MAIF": 69.0,
        "MAIZ": 92.4,
        "OATS": 110.0,
        "OCER": 2.0,
        "OFAR": 107.9,
        "PARI": 85.0,
        "POTA": 45.0,
        "PULS": 115.0,
        "RAPE": 108.0
    },
    "BL": {
        "BARL": 100.0,
        "DWHE": 144.0,
        "GRAS": 80.0,
        "MAIF": 90.0,
        "MAIZ": 61.8,
        "OATS": 155.0,
        "OCER": 20.0,
        "OFAR": 150.0,
        "PARI": 110.0,
        "POTA": 20.0,
        "PULS": 155.0,
        "RAPE": 110.0
    },
    "HR": {
        "BARL": 29.0,
        "DWHE": 118.3,
        "GRAS": 100.1,
        "MAIF": 29.0,
        "MAIZ": 77.6,
        "OATS": 69.3,
        "OCER": 81.7,
        "OFAR": 79.3,
        "PARI": 114.8,
        "POTA": 40.0,
        "PULS": 30.1,
        "RAPE": 100.0,
        "ROOF": 80.4,
        "RYEM": 104.8,
        "SOYA": 125.0,
        "SUGB": 129.9,
        "SUNF": 15.4,
        "SWHE": 107.7
    },
    "CZ": {
        "BARL": 66.1,
        "DWHE": 68.0,
        "GRAS": 13.9,
        "MAIF": 103.0,
        "MAIZ": 83.0,
        "OATS": 43.0,
        "OCER": 70.0,
        "OFAR": 15.3,
        "PARI": 95.5,
        "POTA": 10.0,
        "PULS": 147.0,
        "RAPE": 89.0,
        "ROOF": 70.0,
        "RYEM": 90.0,
        "SOYA": 59.0,
        "SUGB": 106.0,
        "SUNF": 60.7,
        "SWHE": 20.0,
        "TOMA": 128.0
    },
    "DK": {
        "BARL": 78.0,
        "DWHE": 130.0,
        "GRAS": 30.0,
        "MAIF": 80.0,
        "MAIZ": 118.3,
        "OATS": 120.0,
        "OCER": 100.0,
        "OFAR": 100.0,
        "PARI": 70.0,
        "POTA": 150.0,
        "PULS": 140.0
    },
    "FI": {
        "BARL": 72.0,
        "DWHE": 113.0,
        "GRAS": 70.0,
        "MAIF": 70.0,
        "MAIZ": 40.0,
        "OATS": 80.0,
        "OCER": 120.0,
        "OFAR": 85.0,
        "PARI": 80.0
    },
    "FR": {
        "BARL": 120.0,
        "DWHE": 68.0,
        "GRAS": 46.0,
        "MAIF": 170.0,
        "MAIZ": 52.0,
        "OATS": 35.0,
        "OCER": 150.0,
        "OFAR": 155.0,
        "PARI": 145.0,
        "POTA": 130.0,
        "PULS": 80.0,
        "RAPE": 45.0
    },
    "GR": {
        "BARL": 75.0,
        "DWHE": 40.0,
        "GRAS": 80.0,
        "MAIF": 190.0,
        "MAIZ": 85.0,
        "OATS": 200.0,
        "OCER": 40.0,
        "OFAR": 140.0,
        "PARI": 50.0,
        "POTA": 70.0,
        "PULS": 170.0
    },
    "HU": {
        "BARL": 71.5,
        "DWHE": 115.0,
        "GRAS": 133.0,
        "MAIF": 54.0,
        "MAIZ": 105.0,
        "OATS": 52.0,
        "OCER": 63.0,
        "OFAR": 50.0,
        "PARI": 103.0
    },
    "IE": {
        "BARL": 110.0,
        "DWHE": 127.0,
        "GRAS": 96.0,
        "MAIF": 120.0,
        "MAIZ": 120.0,
        "OATS": 150.0,
        "OCER": 180.0,
        "OFAR": 160.0
    },
    "LT": {
        "BARL": 22.0,
        "DWHE": 26.0,
        "GRAS": 16.0,
        "MAIF": 27.0,
        "MAIZ": 11.0,
        "OATS": 21.0,
        "OCER": 57.0,
        "OFAR": 10.0,
        "PARI": 24.0,
        "POTA": 73.0,
        "PULS": 21.0
    }
}

# IPCC CH4 enteric fermentation EFs (kg CH4/head/yr, IPCC 2006 Vol 4 Table 10.10)
CAPRI_CH4_ENTERIC_EF = {
    "DCOW": 117.0,
    "SCOW": 65.0,
    "BULL": 56.0,
    "HEIF": 60.0,
    "CALF": 20.0,
    "SHGM": 8.0,
    "SOWS": 1.5,
    "PIGF": 1.0,
    "HENS": 0.0,
    "POUF": 0.0
}

# IPCC manure CH4 EFs (kg CH4/head/yr, IPCC 2006 Table 10A.2)
CAPRI_CH4_MANURE_EF = {
    "DCOW": 16.0,
    "SCOW": 5.0,
    "BULL": 5.0,
    "HEIF": 5.0,
    "CALF": 5.0,
    "SHGM": 0.19,
    "SOWS": 4.2,
    "PIGF": 3.5,
    "HENS": 0.02,
    "POUF": 0.01
}

# Manure N content (kg N/m3) by animal and system (from envind/ammo_tech.gms)
CAPRI_KG_N_PER_M3 = {
    "DCOL": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "DCOH": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "DCOW": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "BULL": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "BULH": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "BULF": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "HEIL": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "HEIH": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "HEIF": {
        "liquid": 4.3,
        "solid": 7.2
    },
    "HEIR": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "SCOW": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "CAMR": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "CAFR": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "CAMF": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "CAFF": {
        "liquid": 4.3,
        "solid": 7.0
    },
    "PIGF": {
        "liquid": 6.0,
        "solid": 10.4
    },
    "SOWS": {
        "liquid": 4.7,
        "solid": 10.4
    }
}

# GHG from mineral fertiliser production (kg/t, from envind/gascoeff.gms)
CAPRI_FERT_GHG = {
    "NITF": {
        "CO2_kg_per_t": 2543.6,
        "N2O_kg_per_t": 11.3
    },
    "PHOF": {
        "CO2_kg_per_t": 972.7,
        "N2O_kg_per_t": 4.3
    },
    "POTF": {
        "CO2_kg_per_t": 140.0,
        "N2O_kg_per_t": 0.6
    },
    "CAOF": {
        "CO2_kg_per_t": 0.0,
        "N2O_kg_per_t": 0.0
    }
}

# Landscape feature shares by country (%, from envind/landscape.gms, LUCAS survey)
CAPRI_LANDSCAPE = {
    "EU": {
        "Total": 5.64,
        "Woody": 3.19,
        "Grassy": 1.88,
        "Wet": 0.43,
        "Stony": 0.22
    },
    "AT": {
        "Total": 4.4,
        "Woody": 2.63,
        "Grassy": 1.56,
        "Wet": 0.2,
        "Stony": 0.0
    },
    "BL": {
        "Total": 5.56,
        "Woody": 3.08,
        "Grassy": 1.91,
        "Wet": 0.58,
        "Stony": 0.0
    },
    "BG": {
        "Total": 6.22,
        "Woody": 4.51,
        "Grassy": 1.52,
        "Wet": 0.19,
        "Stony": 0.0
    },
    "CY": {
        "Total": 21.1,
        "Woody": 11.9,
        "Grassy": 8.99,
        "Wet": 0.11,
        "Stony": 0.11
    },
    "CZ": {
        "Total": 4.67,
        "Woody": 2.75,
        "Grassy": 1.8,
        "Wet": 0.12,
        "Stony": 0.0
    },
    "DE": {
        "Total": 5.43,
        "Woody": 2.82,
        "Grassy": 1.96,
        "Wet": 0.65,
        "Stony": 0.0
    },
    "DK": {
        "Total": 5.33,
        "Woody": 3.07,
        "Grassy": 1.55,
        "Wet": 0.71,
        "Stony": 0.0
    },
    "EE": {
        "Total": 5.56,
        "Woody": 3.62,
        "Grassy": 1.69,
        "Wet": 0.24,
        "Stony": 0.01
    },
    "EL": {
        "Total": 6.99,
        "Woody": 3.81,
        "Grassy": 2.03,
        "Wet": 0.71,
        "Stony": 0.44
    },
    "ES": {
        "Total": 5.32,
        "Woody": 1.71,
        "Grassy": 2.63,
        "Wet": 0.21,
        "Stony": 0.76
    },
    "FI": {
        "Total": 7.57,
        "Woody": 2.7,
        "Grassy": 2.64,
        "Wet": 2.21,
        "Stony": 0.01
    },
    "FR": {
        "Total": 6.44,
        "Woody": 4.51,
        "Grassy": 1.68,
        "Wet": 0.17,
        "Stony": 0.08
    },
    "HR": {
        "Total": 6.89,
        "Woody": 4.87,
        "Grassy": 1.76,
        "Wet": 0.58,
        "Stony": 0.68
    },
    "HU": {
        "Total": 4.13,
        "Woody": 2.56,
        "Grassy": 1.31,
        "Wet": 0.27,
        "Stony": 0.0
    },
    "IR": {
        "Total": 7.48,
        "Woody": 5.68,
        "Grassy": 0.85,
        "Wet": 0.48,
        "Stony": 0.48
    },
    "IT": {
        "Total": 8.01,
        "Woody": 4.42,
        "Grassy": 3.1,
        "Wet": 0.22,
        "Stony": 0.27
    },
    "LT": {
        "Total": 3.65,
        "Woody": 1.68,
        "Grassy": 1.67,
        "Wet": 0.3,
        "Stony": 0.0
    },
    "LV": {
        "Total": 4.3,
        "Woody": 2.47,
        "Grassy": 1.27,
        "Wet": 0.56,
        "Stony": 0.0
    },
    "MT": {
        "Total": 27.7,
        "Woody": 9.82,
        "Grassy": 6.9,
        "Wet": 0.3,
        "Stony": 10.7
    },
    "NL": {
        "Total": 7.22,
        "Woody": 2.17,
        "Grassy": 1.68,
        "Wet": 3.38,
        "Stony": 0.0
    },
    "PL": {
        "Total": 3.59,
        "Woody": 1.91,
        "Grassy": 1.16,
        "Wet": 0.53,
        "Stony": 0.0
    },
    "PT": {
        "Total": 8.94,
        "Woody": 4.95,
        "Grassy": 2.87,
        "Wet": 0.33,
        "Stony": 0.79
    },
    "RO": {
        "Total": 3.35,
        "Woody": 2.45,
        "Grassy": 0.4,
        "Wet": 0.46,
        "Stony": 0.04
    },
    "SE": {
        "Total": 8.08,
        "Woody": 4.02,
        "Grassy": 3.06,
        "Wet": 0.68,
        "Stony": 0.32
    },
    "SI": {
        "Total": 5.93,
        "Woody": 4.15,
        "Grassy": 1.26,
        "Wet": 0.44,
        "Stony": 0.07
    },
    "SK": {
        "Total": 4.03,
        "Woody": 2.27,
        "Grassy": 1.39,
        "Wet": 0.08,
        "Stony": 0.29
    }
}

# IPCC soil carbon factors by crop type (from envind/ipcc11_2.gms)
CAPRI_CARBON_FACTORS = {
    "OCRO": {
        "crdm": 0.88,
        "CRag_sl": 1.09,
        "CRag_ic": 0.88,
        "CRaN": 0.006
    },
    "PULS": {
        "crdm": 0.91,
        "CRag_sl": 1.13,
        "CRag_ic": 0.85,
        "CRaN": 0.008
    },
    "POTA": {
        "crdm": 0.22,
        "CRag_sl": 0.1,
        "CRag_ic": 1.06,
        "CRaN": 0.019
    },
    "ROOF": {
        "crdm": 0.9,
        "CRag_sl": 0.3,
        "CRag_ic": 0.0,
        "CRaN": 0.015
    },
    "GRAS": {
        "crdm": 0.9,
        "CRag_sl": 0.3,
        "CRag_ic": 0.0,
        "CRaN": 0.025
    },
    "OFAR": {
        "crdm": 0.9,
        "CRag_sl": 0.3,
        "CRag_ic": 0.0,
        "CRaN": 0.015
    },
    "MAIZ": {
        "crdm": 0.87,
        "CRag_sl": 1.03,
        "CRag_ic": 0.61,
        "CRaN": 0.006
    },
    "DWHE": {
        "crdm": 0.89,
        "CRag_sl": 1.61,
        "CRag_ic": 0.4,
        "CRaN": 0.006
    },
    "SWHE": {
        "crdm": 0.89,
        "CRag_sl": 1.29,
        "CRag_ic": 0.75,
        "CRaN": 0.006
    },
    "PARI": {
        "crdm": 0.89,
        "CRag_sl": 0.95,
        "CRag_ic": 2.46,
        "CRaN": 0.007
    },
    "BARL": {
        "crdm": 0.89,
        "CRag_sl": 0.98,
        "CRag_ic": 0.59,
        "CRaN": 0.007
    },
    "OATS": {
        "crdm": 0.89,
        "CRag_sl": 0.91,
        "CRag_ic": 0.89,
        "CRaN": 0.007
    },
    "OCER": {
        "crdm": 0.89,
        "CRag_sl": 0.88,
        "CRag_ic": 1.33,
        "CRaN": 0.007
    },
    "RYEM": {
        "crdm": 0.88,
        "CRag_sl": 1.09,
        "CRag_ic": 0.88,
        "CRaN": 0.005
    },
    "SOYA": {
        "crdm": 0.91,
        "CRag_sl": 0.93,
        "CRag_ic": 1.35,
        "CRaN": 0.008
    }
}

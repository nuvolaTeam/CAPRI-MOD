"""CAPRI's reporting aggregates in its market data and the model's commodity codes for CAPRI's market products: the
constants the market builders share (a module; no outputs since 3 November 2026).

Until then this file was also a builder: it wrote shared/trade_flows_2017.csv, CAPRI's 2017 bilateral ImportQ
(capmod res_0_1717) folded into the model's trade regions, and a report comparing it with FAOSTAT's 2021 matrix
(sources/fao_2021/trade_flows_2021.csv). No code read the matrix (the model's flows are 2017/market/
bilateral_flows_*.csv, tools/build/build_bilateral_market.py), so both files were removed with the market's move onto
CAPRI's regions (docs/design/MARKET_REGIONS_INVENTORY.md stage 1), and its region map (REGION_MAP, trade_region)
gave way to the market's grouping step, tools/lib/_market_regions.py.

  AGGREGATES     CAPRI's reporting sums in its market data, dropped by the builders that read every region (each
                 overlaps the regions it sums: reading it double-counts)
  COMMODITY_MAP  the model's commodity -> CAPRI's market product, where the codes differ (read also by
                 tools/build/build_code_lists.py, which checks it against build_feed_bulks.COMMODITY)
"""
from __future__ import annotations

# Overlapping aggregates. These are supersets of CAPRI's market regions and must be
# dropped, not mapped: including them counts the same trade more than once. A_EU_WEST and A_EU_EAST
# are market regions, listed for the builders that read the EU at its aggregate EU27yr19.
AGGREGATES = {
    # CAPRI REPORTING sums, derived from the data (2026-10): the 44 trading regions
    # (39 behavioural regions + 5 trade-only blocks EU27yr19, URUPAR, WBA, MER_OTH,
    # MED) reproduce ImportQ(World, World) exactly for all 71 traded products, and
    # every code below overshoots when added (checked for all 71 traded products in 2017).
    # The previous hand-made list dropped GENUINE regions (URUPAR, MED, AFR_LDC,
    # AFR_REST, ASOCE_LDC, ASOCE_REST, FSU, REU, MSA_ACP, WBA) and kept "EU" and
    # "AllImporters", double-counting the EU and rest of world.
    "ACP", "AFRICA", "ANZ", "ASIA", "A_EU_EAST", "A_EU_WEST", "AllImporters", "EU", "HI_INC", "LDC", "LDCACP", "MER", "MID_INC", "MS_AM", "NONEU", "NONEU_EU", "N_AM", "World",
}

# model commodity -> CAPRI market commodity
COMMODITY_MAP = {
    "SWHE": "WHEA", "CORN": "MAIZ", "POUL": "POUM",
    "BUTR": "BUTT", "SKIM": "SMIP",
    # added 2026-10, the same renames as the world prices: without them these
    # commodities had NO trade at all in the matrix
    "SUGR": "SUGA", "WINE": "TWIN", "WHEY": "WHEP", "SGMT": "SGMT",
}

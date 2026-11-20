"""CAPRI's arm/market_model.gms (star 3.0, 4,607 lines), one module per block of the file.

Each module holds the equations of one of CAPRI's blocks, as the file's own banners divide it, one function per
equation named as CAPRI's equation (the MODEL statement's spelling), with CAPRI's GAMS statement, its file and lines,
the equation in this project's notation and the departures in the docstrings. The equations of CAPRI's market
simulation model m_globMarket (l. 4243, with m_bevFunctionsMarket, l. 4150), the block each belongs to and whether
CAPRI's 2030 Green Deal step has it: docs/dev/market_equations_inventory.csv (planned_module). A module is added when
its first equation is written.

    module          CAPRI block (arm/market_model.gms)                                              lines
    demand.py       the demand system: GLDemandFS_, GLDemandGS_, GLDemandGis_, XiS_                  816-918
    prices.py       PRICES: CPri_                                                                    2842-3130

The other blocks, by the inventory: feed, dairy, processing, biofuels, supply, land, lulucf, fudging, aggregation,
net_trade, armington, border, intervention, objective (tools/refactor/market_equations_inventory.py BLOCKS).
"""

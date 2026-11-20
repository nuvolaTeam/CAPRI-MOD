"""CAPRI's arm/market_model.gms (star 3.0, 4,607 lines), one module per block of the file.

Each module holds the equations of one of CAPRI's blocks, as the file's own banners divide it, one function per
equation named as CAPRI's equation (the MODEL statement's spelling), with CAPRI's GAMS statement, its file and lines,
the equation in this project's notation and the departures in the docstrings. The equations of CAPRI's market
simulation model m_globMarket (l. 4243, with m_bevFunctionsMarket, l. 4150), the block each belongs to and whether
CAPRI's 2030 Green Deal step has it: docs/dev/market_equations_inventory.csv (planned_module). A module is added when
its first equation is written.

    module          CAPRI block (arm/market_model.gms)                                              lines
    demand.py       the demand system: GLDemandFS_, GLDemandGS_, GLDemandGis_, XiS_                  816-918
    feed.py         feed: feedBlkPrice_, feedBlk_, FeedShareEqu_, FeedNQ_, FeedBal_                   919-1064
    dairy.py        dairy: ProcMargM_, DairyNQ_, FatsProtBal_                                         1065-1114
    processing.py   oilseed processing and the by-products: ProcMargO_, ProcNQ_, ProcFudge_, ProcO_,  1115-1179,
                    procYield_, MaprFeed_                                                            1440-1523
    biofuels.py     biofuels: BiofFeedCost_, BiofFeedCostAgg_, Biof_, ProdBiof_, BiofPriceRel_,       1180-1439
                    SupplyBiof_, biofDemshare_, biofDem_
    supply.py       supply in the market: ProdNQ_ (ProdNQ_hess), yaniMarket_                          1524-1656
    land.py         land: rentFromProdpriceLand_, LandSupplyMNL_, LndSupplyEqualsDemand_,             1657-1995
                    LinkLuWithShares_, luClassFinal_, luClassInitial_, FocLUC_ (derivativeOfGammaLUC_)
    fudging.py      the fudging functions: ProdFudge_ (FeedFudge_ in its form)                       2376-2434
    armington.py    the adding up and the Armington system: SupBalM_, arm2QuantShares_,              2595-2841
                    domSalesShares_, importShares_
    prices.py       PRICES: impPrice_, arm1PriceAgg_, arm2PriceAgg_, CPri_, PMrk_, MarketPriceAgg_    2842-3130

The other blocks, by the inventory: lulucf, aggregation, net_trade, border, intervention, objective
(tools/refactor/market_equations_inventory.py BLOCKS).
"""

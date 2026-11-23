"""CAPRI's market-model equations, one function each, named as CAPRI's equation (or as the equation's term the function
writes), the refactor's second phase (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md).

The layout follows the supply side's (capri_mod/supply/equations/): one module per CAPRI source file, named after it,
and for a large file a sub-package with one module per block of the file (market_model/: CAPRI's arm/market_model.gms,
star 3.0; its __init__ maps each module to its CAPRI block and lines). A module is added when its first equation is
written.

    market_model/   arm/market_model.gms: demand.py (the Generalised Leontief demand system), feed.py (the feed
                    demand), dairy.py (the dairy processing), processing.py (oilseed crushing and the by-products),
                    biofuels.py (the biofuel processing, supply and demand), supply.py (the market's supply
                    functions and the young-animal markets), land.py (the land market and the land-use change outside
                    the EU), fudging.py (the smooth max of the supply cells), armington.py (the supply balance and
                    the Armington nests' quantities), prices.py (the import prices, the Armington price indexes, the
                    consumer price, the market prices of the regions without production and of the policy blocks),
                    border.py (the tariff-rate quotas, the entry prices, the flexible levies)
    cal_armington.py
                    arm/cal_armington.gms: the Armington system's share parameters at the calibration point
                    (the calibration block C1)
    manuremarket/   manuremarket/: declare_manure_market.py (the pool market's surplus, the autarky buffers),
                    simu_manure_market.py (the excess supply's refit, the step-weighted prices; the fall-back manure
                    value and the trade gap, block A4) (the block P)

The third phase's statements (assignments; docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md, blocks A1 and A4):

    welfare.py      reports/welfare.gms: ProfitAgr of the supply models' regions; the GL money metric (CSSP), the
                    processing's and the feed industry's profits
    sol_market.py   reports/sol_market.gms: the biofuel margin, the tariff-rate quotas' rents
    set_start_val.py
                    arm/set_start_val.gms: the processing quantities' and market prices' bounds
    def_biofuel_params.py
                    biofuel/def_biofuel_params.gms: the feedstocks' CES share parameters

Each function's docstring gives CAPRI's GAMS statement, the CAPRI star 3.0 file and lines it follows, the equation in
this project's notation, how the model's quantities map to CAPRI's symbols, and the departures from CAPRI's equation.
The market's systems (capri_mod/market/*_ad.py, bilateral.py, ...) call the functions.
"""

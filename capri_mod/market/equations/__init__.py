"""CAPRI's market-model equations, one function each, named as CAPRI's equation (or as the equation's term the function
writes), the refactor's second phase (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md).

The layout follows the supply side's (capri_mod/supply/equations/): one module per CAPRI source file, named after it,
and for a large file a sub-package with one module per block of the file (market_model/: CAPRI's arm/market_model.gms,
star 3.0; its __init__ maps each module to its CAPRI block and lines). A module is added when its first equation is
written.

    market_model/   arm/market_model.gms: demand.py (the Generalised Leontief demand system), feed.py (the feed
                    demand), dairy.py (the dairy processing), processing.py (oilseed crushing and the by-products),
                    biofuels.py (the biofuel processing, supply and demand), prices.py (the consumer price)

Each function's docstring gives CAPRI's GAMS statement, the CAPRI star 3.0 file and lines it follows, the equation in
this project's notation, how the model's quantities map to CAPRI's symbols, and the departures from CAPRI's equation.
The market's systems (capri_mod/market/*_ad.py, bilateral.py, ...) call the functions.
"""

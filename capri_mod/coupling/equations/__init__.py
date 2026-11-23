"""CAPRI's statements the coupling (the supply-market loop) ports, one module per CAPRI file (the refactor's third
phase, block A4, docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): price_forecast.py (capmod/price_forecast.gms, the stop
rule), define_stepweights.py (capmod/define_stepWeights.gms), simu_calibration_to_supply.py (arm/
simu_calibration_to_supply.gms, the supply models' results passed to the market) and sol_simy.py (reports/
sol_simy.gms, the land owners' profit). The manure market's statements are in capri_mod/market/equations/
manuremarket/simu_manure_market.py (the block P's module).

Each function is named after the symbol CAPRI assigns, quotes CAPRI's GAMS (star 3.0, file and lines), states the
statement in this project's notation and its departures from CAPRI; capri_mod/coupling, capri_mod/utils/capri_stop.py
and capri_mod/market call them.
"""

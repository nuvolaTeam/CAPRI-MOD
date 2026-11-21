"""CAPRI's manure pool market (manuremarket/, star 3.0), one module per CAPRI file (the block P,
docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md): the pool market's equations and its trade links' autarky buffers
(declare_manure_market.py, manuremarket/declare_manure_market.gms) and the simulation's refit of the regions' excess
supply to the supply models and the step-weighted prices (simu_manure_market.py, manuremarket/simu_manure_market.gms).

Written: CAPRIModel._clear_pool_capri (capri_mod/coupling/manure.py), which solves CAPRI's m_mPoolMarket for one
nutrient as a convex QP, and the price sent back to the supply models (_clear_pool). The rows' inventory and what the
model does with each: docs/dev/MARKET_EQUATION_REFACTOR_HANDOFF.md, the block P.
"""

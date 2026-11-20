"""CAPRI's equations, one function each, named as CAPRI's equation (or as the equation's term the function writes).

The layout follows CAPRI's own files: one module per CAPRI source file, named after it, and for a large file a
sub-package with one module per block of the file (supply_model/: CAPRI's supply/supply_model.gms; its __init__ maps
each module to its CAPRI block and lines). A module is added when its first equation is written.

    supply_model/   supply/supply_model.gms: nutrients.py (the pools, NUTNED_), n_surplus.py (the N surplus's terms, the
                    input shares, SURTOT_REST_), inner_fert.py (the inner fertiliser model), n_flow.py (the N loss
                    cascade, the leaching), fert_limits.py (e_synNMax), objective.py (LINEAR_'s terms, QUADRF_, QUADRA_,
                    OBJEQF_), mitigation.py (GHG_Mit_Cost_), feeding.py (REQSE_, FEDUSE_), markets.py (SUPBAL_),
                    premiums.py (the catch crops, the entitlements, the permanent grassland), set_aside.py (the
                    landscape floor, the idled histosols), land.py (the land balances, the land market)
    fertned.py      fert/fertned.gms: DATA_FNUT, the crops' nutrient need (K185, the main line)

Each function's docstring, or its module's, gives CAPRI's GAMS statement and its domain, the CAPRI star 3.0 file and
lines it follows, the equation in this project's notation, how the model's quantities map to CAPRI's symbols, and the
departures from CAPRI's equation. The functions take plain numbers or CasADi expressions alike, so the regional NLP and
the checks evaluate the same code.
"""

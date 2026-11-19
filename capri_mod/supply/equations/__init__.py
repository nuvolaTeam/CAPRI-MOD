"""CAPRI's equations, one function each, named as CAPRI's equation (or as the equation's term the function writes).

The layout follows CAPRI's own files: one module per CAPRI source file, named after it, and for a large file a
sub-package with one module per block of the file (supply_model/: CAPRI's supply/supply_model.gms; its __init__ maps
each module to its CAPRI block and lines). A module is added when its first equation is written.

    supply_model/   supply/supply_model.gms: nutrients.py (fertDistCres_, NUTNED_), n_surplus.py (e_ATMOSD,
                    e_CRESID, e_SURTOTHa), mitigation.py (GHG_Mit_Cost_)

Each function's docstring, or its module's, gives CAPRI's GAMS statement and its domain, the CAPRI star 3.0 file and
lines it follows, the equation in this project's notation, how the model's quantities map to CAPRI's symbols, and the
departures from CAPRI's equation. The functions take plain numbers or CasADi expressions alike, so the regional NLP and
the checks evaluate the same code.
"""

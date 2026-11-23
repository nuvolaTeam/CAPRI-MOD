"""CAPRI's statements the projection layer ports, one module per CAPRI file (the refactor's third phase,
docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): breeding.py (envind/breeding.gms, the dairy cow's energy requirements apart
from lactation), calc_nexport.py (fert/calc_nexport.gms, the N exported with the milk).

Each function is named after the symbol CAPRI assigns, quotes CAPRI's GAMS (star 3.0, file and lines), states the
statement in this project's notation and its departures from CAPRI; capri_mod/projection/projection_module.py calls
them.
"""

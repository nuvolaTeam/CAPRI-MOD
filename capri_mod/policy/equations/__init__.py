"""CAPRI's premium statements the policy layer ports, one module per CAPRI file (the refactor's third phase, block A2,
docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): policy.py (policy/policy.gms, the declared premiums), prmcut.py (policy/
prmcut.gms, the premium cut), aggreg_ppepay.py, implement_bps.py (the BPS's ceilings and convergence), mtr_until2013.py
(pol_input/mtr_until2013.gms's rules), calc_mtr_top.py and calc_mtr.py (the 2003 reform's set-up and budgets),
extend_rd_baseline.py (the rural development budgets), cap_2014_2020.py, cap_2013_2020_transfers.py,
cap_2013_2020_vcs.py and cap_2013_2020_cndp.py (the CAP 2014-2020 ceilings and coupled schemes), def_policy.py,
def_endcut.py, def_no_policy.py (Norway) and nordicaid.py; _gams.py holds GAMS's values (EPS, NA, a $-condition).

Each function is named after the symbol CAPRI assigns, quotes CAPRI's GAMS (star 3.0, file and lines), states the
statement in this project's notation and its departures from CAPRI, and returns the value its statement assigns to one
record (None where the statement's condition leaves the record as it is); the modules of capri_mod/policy and
capri_mod/supply/entitlements.py call them. The literal values (the regulations' tables, mtr_until2013.gms's
declarations) are data read (the project lead, 23 November 2026).
"""

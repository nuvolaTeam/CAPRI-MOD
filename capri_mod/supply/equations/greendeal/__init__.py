"""CAPRI's Green Deal scenario files (pol_input/greendeal/, star 3.0), one module per file (the refactor's third
phase, block A5, docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md): conventional_io.py (the pesticide target), organic_io.py and
organic_area.py (the organic target's input changes and yield gap), load_organic_targets.py (the targets' scaling),
landscape.py (the landscape floor and the crop diversification limit under it), minfert_redu_by_crop.py and
organic_minfert_redu.py (the mineral fertiliser reduction), surptot.py (the nutrient surplus target) and
greendeal_scenarios.py (the winter cover held).

Each function is named after the symbol CAPRI assigns, quotes CAPRI's GAMS (star 3.0, file and lines), states the
statement in this project's notation and its departures from CAPRI; capri_mod/supply (policy.py, supply_module.py,
abatement.py, fertilisation.py, nlp.py) and capri_mod/fert/inner_fert_dist.py call them. The targets themselves and
the exemptions' factors are data read.
"""

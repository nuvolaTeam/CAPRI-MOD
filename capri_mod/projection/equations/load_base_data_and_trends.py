r"""CAPRI's data of a simulation year (capmod/load_base_data_and_trends.gms l. 44-863; CAPRI star 3.0, baseline mode):
the trends, CAPTRD's DATA2 at "Y", corrected and loaded on "TRD"; "Y" = "TRD" where CAPTRD projects the item
(FROM_CAPTRD), "BAS" elsewhere; then the positions CAPRI derives, fills or deletes for the simulation.

The base year's data "BAS" are CAPREG's results with CAPRI's corrections (l. 44-199, base_year_data); the trends are
CAPTRD's (l. 290-863, year_data). One function per CAPRI statement block, in CAPRI's order.

DATA is CAPRI's DATA(region, column, row, position), Data below. GAMS's zero is an absent cell, and setting a cell to
zero deletes it. CAPRI's sets are those of sim_ini_21730 (capri_data/codes/capri, YearSets).

Since 25 November 2026 also l. 711-795: Norway's sheep milk quota, the biofuels and DDGS, the cakes' processing
coefficients, the raw milk's fat and protein, and biofuel/resids.gms (the crop residues and the second-generation
biofuels' sources; its literal parameters in capri_data/2017/supply/biofuel_resids_params.csv).

Not ported, as they set no item of the supply models' activities, feed or fodder:
- l. 298-299 (oats' INTP and INTS) and l. 303-307 (the fuels' rows, calyea);
- l. 396-397 and 402-415 (the biofuel feedstocks);
- l. 520-525 (the inland waters' INLW).

Not ported in the base year's loading: l. 34-43 (the GDX loading itself and its meta information) and l. 65-123 (the
definition of ColsRead and RowsRead: their values are taken from sim_ini_21730's sets, YearSets).

Not ported because their branch is off in CAPRI's 2030 baseline:
- l. 236-261 (farm types), l. 385-393 (%SIM% 06), l. 601-630 (a short-run scenario);
- l. 644-657 (ex post, and BAS = SIM).

The checks that only display (l. 417-434, 568-585) are not ported. The aborts are (check_uaar_trend and
assert_year_data).

Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set

from capri_mod.projection.equations.year_data.data_sets import (  # noqa: E402,F401  the parts (moved as they were)
    Data, OSet, YearSets)
from capri_mod.projection.equations.year_data.base_year import (  # noqa: E402,F401  the parts (moved as they were)
    DATA2_base_deletions, DATA2_base_labour_and_nutrients, DATA_BAS_from_capreg, check_uaar_base, DATA_CERE_HSTY)
from capri_mod.projection.equations.year_data.trends import (  # noqa: E402,F401  the parts (moved as they were)
    DATA2_GROF_FODDI, DATA2_feeds_not_in_base, DATA_TRD_from_trends, DATA_TRD_small_areas, DATA_TRD_GROF_OCRO, DATA_TRD_FALL_invented,
    DATA_TRD_small_quantities, delete_tiny_activity_level, check_uaar_trend, DATA_TRD_young_animals_fixed, FROM_CAPTRD_, DATA_TRD_LOSF_STRA,
    DATA_TRD_LOSF_ratio, DATA_TRD_GROF_FODDI)
from capri_mod.projection.equations.year_data.simulation_year import (  # noqa: E402,F401  the parts (moved as they were)
    DATA_Y_, DATA_Y_UAAR, DATA_young_animal_coefficients, DATA_delete_positions, DATA_MS_feed_balances, DATA_split_activities,
    DATA_delete_after_year, DATA_NO_QUTS_SGMI, DATA_BIOF_PRCB_WHEA, DATA_EXOG_tiny_feedstocks, DATA_FSTG_PROD_biofuels, DATA_DDGS,
    DATA_PRCY_CAK, DATA_MAPR_MLK_small, DATA_FATSPROT_MILK)
from capri_mod.projection.equations.year_data.residues import (  # noqa: E402,F401  the parts (moved as they were)
    ResidsParams, DATA_ARES, _necr_yield, DATA_NECR_LEVL_1_2, DATA_SECG_ARES_bio)
from capri_mod.projection.equations.year_data.checks import (  # noqa: E402,F401  the parts (moved as they were)
    DATA_delete_contents, assert_year_data)


def base_year_data(D: Data, D2b: Data, S: YearSets) -> None:
    """CAPRI's loading of the base year (load_base_data_and_trends.gms l. 44-199, the statements ported) from CAPREG's
    results D2b (CAPREG's DATA2 at "Y"): the base year on "BAS" of D."""
    DATA2_base_deletions(D2b, S)
    DATA2_base_labour_and_nutrients(D2b, S)
    DATA_BAS_from_capreg(D, D2b, S)
    check_uaar_base(D, S)
    DATA_CERE_HSTY(D, D2b, S)


def year_data(D: Data, D2: Data, S: YearSets, check: bool = True, P: ResidsParams = None,
              same_year: bool = False) -> set:
    """CAPRI's sequence of load_base_data_and_trends.gms l. 297-863 for the statements ported (module docstring), on
    D (the base year on "BAS") and D2 (the trends, CAPTRD's DATA2 at "Y"); returns FROM_CAPTRD. P: biofuel/resids.gms's
    parameters (by default from capri_data); same_year: the simulation year is the base year (CALYEA, resids.gms
    l. 81-85; not in CAPRI's 2030 baseline)."""
    P = P or ResidsParams.from_csv()
    DATA2_GROF_FODDI(D2, S)
    DATA2_feeds_not_in_base(D2, D, S)
    DATA_TRD_from_trends(D, D2, S)
    DATA_TRD_small_areas(D, S)
    DATA_TRD_GROF_OCRO(D, S)
    DATA_TRD_FALL_invented(D, S)
    DATA_TRD_small_quantities(D, S)
    delete_tiny_activity_level(D, S, "TRD", 1e-3)
    check_uaar_trend(D, S)
    DATA_TRD_young_animals_fixed(D, S)
    fc = FROM_CAPTRD_(D2, S)
    DATA_TRD_LOSF_STRA(D, S)
    DATA_TRD_LOSF_ratio(D, S)
    DATA_TRD_GROF_FODDI(D, S)
    DATA_Y_(D, S, fc)
    DATA_Y_UAAR(D, S)
    DATA_young_animal_coefficients(D, S)
    DATA_delete_positions(D, S)
    DATA_MS_feed_balances(D, S)
    DATA_split_activities(D, S)
    DATA_delete_after_year(D, S)
    DATA_NO_QUTS_SGMI(D, S)
    DATA_BIOF_PRCB_WHEA(D, S)
    DATA_EXOG_tiny_feedstocks(D, S)
    DATA_FSTG_PROD_biofuels(D, S)
    DATA_DDGS(D, S)
    DATA_PRCY_CAK(D, S)
    DATA_MAPR_MLK_small(D, S)
    DATA_FATSPROT_MILK(D, S)
    DATA_ARES(D, S, P)                      # biofuel/resids.gms, included at l. 795
    DATA_NECR_LEVL_1_2(D, S, P, same_year)
    DATA_SECG_ARES_bio(D, S, P)
    DATA_delete_contents(D, S)
    delete_tiny_activity_level(D, S, "Y", 1e-3)
    if check:
        assert_year_data(D, S)
    return fc

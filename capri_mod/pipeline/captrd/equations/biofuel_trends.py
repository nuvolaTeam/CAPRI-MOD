r"""CAPTRD's statements of biofuel/biofuel_trends.gms (CAPRI star 3.0, included by captrd/expert_support.gms
l. 108 with %NewBiofuelModule% on): PRIMES's biofuel results aggregated, filled and shared out (p_primesResults), and
the expert supports of the biofuel sector built from them (p_expertSupprt's Absolute and TrustLevl, p_data's nObs), as
named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/biofuel_trends.py (trends) holds the loops over the
regions, the positions and the years, the data and the conditions (with the values from before each statement where
its right side reads what it assigns), and calls them; the arithmetic is the port's, so the trends are unchanged.
"""
from __future__ import annotations

from capri_mod.pipeline.captrd.equations.biofuel_trend.primes_results import (  # noqa: E402,F401  the parts (moved as they were)
    p_primesResults, p_primesResults_NTRD, p_primesWithUnits_OILS_kton, p_primesWithUnits_VOIL_ktoe, p_primesResults_BIOF_oil, p_primesResults_SECG_BIOD,
    p_primesResults_SECG_BIOE, p_primesResults_expostT_first_gen, p_primesResults_SECG_BIOE_expostT, p_primesResults_bioeShare_SECG, p_primesResults_bioeShare_stocks, p_primesResults_fossil,
    p_primesResults_CTAX, p_primesResults_CTAX_2015, p_primesResults_BL, p_primesResults_BL_price, p_primesResults_scaleCols, p_primesResults_gap,
    p_primesResults_Fillyears, p_primesResults_bioeShare_SECG_max, p_primesResults_share, p_primesResults_P_DATA, p_primesResults_from_share, p_primesResults_MAPR_BIOE,
    p_primesResults_bioeShare_stocks_MS, p_primesResults_WOIL_Fillyears, p_primesResults_BIOF_VOIL, p_primesResults_NAGR_BIOD, p_primesResults_copy, p_primesResults_DOMM_SECO_BIOF,
    p_primesResults_CERE_BIOE)
from capri_mod.pipeline.captrd.equations.biofuel_trend.sector_supports import (  # noqa: E402,F401  the parts (moved as they were)
    p_expertSupprt_expostT, p_expertSupprt_PRIMES_change, P_expertSupprt_INDM, p_expertSupprt_BIOF_SECO_BIOF, P_expertSupprt_NTRD, P_expertSupprt_NTRD_BASprimes,
    p_expertSupprt_trade_up, p_expertSupprt_trade_down, p_expertSupprt_trade_base, p_expertSupprt_NTRD_BASprimes_removed, p_expertSupprt_SECG, p_expertSupprt_NECR_LEVL,
    p_expertSupprt_NECR_LEVL_EPS, p_expertSupprt_NECR_LEVL_NT2Est, p_expertSupprt_NECR_LEVL_TrustLevl, p_expertSupprt_NECR_OCRO, P_DATA_nObs, P_expertSupprt_NAGR,
    P_expertSupprt_PRCB, P_expertSupprt_PRCBY, P_expertSupprt_PRCB_after_lst_dgagri, P_expertSupprt_PRCBY_after_lst_dgagri, p_expertSupprt_BIOF_TWIN, p_expertSupprt_BIOF_SUGA)
from capri_mod.pipeline.captrd.equations.biofuel_trend.stock_shares import (  # noqa: E402,F401  the parts (moved as they were)
    p_agrFuel, p_stockShare_expostT, p_stockShare_exanteT, p_stockShare_potential, p_stockShare_runBio, p_stockShare_normalised,
    p_expertSupprt_BIOF_runStock)
from capri_mod.pipeline.captrd.equations.biofuel_trend.ddgs import (  # noqa: E402,F401  the parts (moved as they were)
    p_expertSupprt_MAPR_DDGS, p_expertSupprt_FEDM_DDGS, p_expertSupprt_DOMM_DDGS, p_expertSupprt_NTRD_DDGS, p_expertSupprt_IMPT_DDGS, p_expertSupprt_EXPT_DDGS)
from capri_mod.pipeline.captrd.equations.biofuel_trend.small_and_fossil import (  # noqa: E402,F401  the parts (moved as they were)
    p_expertSupprt_BIOF_small, p_expertSupprt_BIOF_tiny, P_expertSupprt_BIOF_CERE, P_expertSupprt_PRCB_tiny, P_expertSupprt_MAPR_BIOE, P_expertSupprt_constBioPos,
    P_expertSupprt_fossil, p_expertSupprt_INHA_fossil)
from capri_mod.pipeline.captrd.equations.biofuel_trend.taxes_prices import (  # noqa: E402,F401  the parts (moved as they were)
    p_taxData_CTAX_2005, p_taxData_CTAX_per_t, P_expertSupprt_CTAX_SECO_BIOF, P_expertSupprt_CTAX_fossil_expostT, P_expertSupprt_CTAX_fossil_exanteT, P_result_UVAG_basy,
    P_result_UVAG_expostT, P_expertSupprt_UVAG_expostT, P_expertSupprt_UVAG_EXANTE, P_expertSupprt_UVAD, P_expertSupprt_per_ton, p_expertSupprt_EXPD)
from capri_mod.pipeline.captrd.equations.biofuel_trend.trust_levels import (  # noqa: E402,F401  the parts (moved as they were)
    P_expertSupprt_TrustLevl_7, P_expertSupprt_TrustLevl_1, p_expertSupprt_TrustLevl_DDGS, p_expertSupprt_NTRD_DDGS_TrustLevl)

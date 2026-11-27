r"""CAPTRD's bound statements of captrd/fix_est.gms (CAPRI star 3.0): the bounds of the member-state and NUTS 2 estimations, as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (the assignments
refactor's style: one function per statement block, named after the bounded symbol, V_EstV.LO / .UP / .FX). The
functions take the numbers the statement reads and return the bound; capri_mod/pipeline/captrd/estimate_bounds.py
(bounds) holds the domain conditions, the loops over the sets and the order of the statements, and calls them. A
bound "before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its
order of operations, so the bounds are unchanged.
"""
from __future__ import annotations

from capri_mod.pipeline.captrd.equations.estimation_bounds.inputs_outputs import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_IO, V_EstV_OYANI_expert, V_EstV_IYANI_cows, V_EstV_SLGW, V_EstV_FEED, V_EstV_FODDI,
    V_EstV_ReqsT, V_EstV_lo_ReqsTE, V_EstV_lo_CRPR, V_EstV_up_ReqsTE, V_EstV_NoYieldDrop)
from capri_mod.pipeline.captrd.equations.estimation_bounds.yields_prices import (  # noqa: E402,F401  the parts (moved as they were)
    p_data_GROF_maxFacPerY, V_EstV_up_GROF_maxFac, V_EstV_UVAG)
from capri_mod.pipeline.captrd.equations.estimation_bounds.consumption import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_INHA, V_EstV_foodSh, V_EstV_INHA_MEAS_CERE, V_EstV_INHA_seco_bioF, V_EstV_HCOM)
from capri_mod.pipeline.captrd.equations.estimation_bounds.activity_levels import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_LEVL_crops, V_EstV_lo_GRSACT, V_EstV_lo_MAACT, p_data_LEVL_facs, V_EstV_up_MAACT_LEVL, V_EstV_lo_MAACT_LEVL,
    V_EstV_up_TWIN, V_EstV_up_OOIL, V_EstV_fx_young_animals, V_EstV_fx_FixYield, V_EstV_fx_DAYS, V_EstV_STRA)
from capri_mod.pipeline.captrd.equations.estimation_bounds.physical_limits import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_up_max_yields, V_EstV_up_CERE, V_EstV_up_physical, V_EstV_up_GRAS, V_EstV_lo_max_yields, V_EstV_MEAT,
    V_EstV_DAYS, V_EstV_reqfcnlim)
from capri_mod.pipeline.captrd.equations.estimation_bounds.dairy_processing import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_MLKSECO, V_EstV_fx_MLKCNT, V_EstV_PRCY, V_EstV_fx_PRCY_MILK, V_EstV_PRCY_MLKSECO, V_EstV_up_STCM,
    V_EstV_lo_MrkBalee, V_EstV_lo_STCM)
from capri_mod.pipeline.captrd.equations.estimation_bounds.markets_land import (  # noqa: E402,F401  the parts (moved as they were)
    V_EstV_NTRD, V_EstV_INTP, V_EstV_GROF_labour, V_EstV_expert_corridor, V_EstV_UAAR, V_EstV_ARTIF,
    V_EstV_fx_land, V_EstV_fx_RSET, V_EstV_fx_tiny_support, V_EstV_lo_SUGB)

r"""CAPTRD's statements of baseline/load_aglink2023dgAgri.gms (CAPRI star 3.0, captrd.gms l. 593): Aglink-COSIMO's
cube rebooked (p_aglinkOri), the European regions' data (p_aglink) and the biofuels' feedstock yields (p_BFyld), the
mapping to CAPRI's regions, columns and rows (p_aglinkTrd) stored as p_result(..., "DGAgri"), and the population of the
macro data (p_SSPAglink, p_aglinkMacro), as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block or repeated form, named after the assigned symbol). capri_mod/pipeline/captrd/aglink.py (read_aglink, eu_data,
to_capri, dgagri) and macro.py (inha) hold the loops over the regions, positions and years, the mappings and the
conditions, and call them; the arithmetic is the port's, so the outlook is unchanged. NA is float('nan'); _nz is GAMS's
truth of a value (nonzero, NA included).
"""
from __future__ import annotations

import math

from capri_mod.pipeline.captrd.equations.aglink2023.cube import (  # noqa: E402,F401  the parts (moved as they were)
    p_aglinkOri, p_aglinkOri_rebooked, p_aglink, p_aglink_WLD_XP, p_aglink_sum, p_aglinkTrd_sum,
    p_aglink_FOA, p_aglink_QC_WYP, p_aglink_copy, p_aglink_difference, p_aglink_FU_MK, p_aglink_removed,
    p_aglink_OU_MOL, p_aglink_FO_OL, p_aglink_QC, p_aglink_VST, p_aglink_VST_parts, p_aglink_NT_parts,
    p_aglink_1000t)
from capri_mod.pipeline.captrd.equations.aglink2023.biofuel_yields import (  # noqa: E402,F401  the parts (moved as they were)
    p_BFyld, p_BFyld_copy, p_aglink_QP_CG, p_aglink_QP_feedstock)
from capri_mod.pipeline.captrd.equations.aglink2023.shares import (  # noqa: E402,F401  the parts (moved as they were)
    P_Data_BAST, p_share_E14, p_share_NMS, p_secgShare_E14, p_aglink_parts_share, p_aglink_QP_SEC,
    p_aglink_QC_EUN, p_aglink_OU_parts, p_aglink_XR, p_aglink_per_toe, p_aglink_XP_OIL)
from capri_mod.pipeline.captrd.equations.aglink2023.mapping import (  # noqa: E402,F401  the parts (moved as they were)
    p_aglinkTrd_sum, p_aglink_XR_parts, p_aglinkTrd_YILD, p_aglinkTrd_BIOF_SUGA, p_domShare, p_aglinkTrd_colsGrof,
    p_aglinkTrd_colsInd, p_aglinkTrd_removed, p_result_DGAgri_EXPT_IMPT, p_aglinkTrd_colsHcom, p_aglinkTrd_DOMM_negative, p_aglinkTrd_plus,
    p_aglinkTrd_copy, p_result_DGAgri, p_aglinkTrd_HCOM_COMI, p_aglinkTrd_Exog, p_aglinkTrd_S1COM, p_aglinkTrd_pric_XR,
    p_aglinkTrd_UVAG_biofuels, p_aglinkTrd_UVAP_fosfuels, p_aglinkTrd_TARV, p_aglinkTrd_DDGS, p_result_DGAgri_max0)
from capri_mod.pipeline.captrd.equations.aglink2023.macro import (  # noqa: E402,F401  the parts (moved as they were)
    p_SSPAglink_INHA_2000, p_SSPAglink_INHA_agYears, p_SSPAglink_INHA_after_lst_dgagri, p_SSPAglink_interpolated, p_aglinkMacro, p_aglinkMacro_BAS,
    _nz, _max0)

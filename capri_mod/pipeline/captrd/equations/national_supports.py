r"""CAPTRD's statements of captrd/national_supports.gms (CAPRI star 3.0, included by expert_support.gms l. 779;
%aglinkTightLink% off, %useAgriInfo% on, %lst_daitar% 2020): the national expert supports, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/national_supports.py (supports) holds the loops over
the regions, the positions and the years, the conditions and the order, and calls them; the arithmetic is the port's,
so the supports are unchanged. trust_nat is p_trustNat (l. 205, 7.01).
"""
from __future__ import annotations

from capri_mod.pipeline.captrd.equations.national_support.general import (  # noqa: E402,F401  the parts (moved as they were)
    p_ExpertSupprt_PercentChange_dairy, p_ExpertSupprt_MILK_from_MAPR, p_natExpert_NECP, p_NatExpert_AVGDAT, p_NatExpert_from_pdata, p_NatExpert_BAS,
    p_ExpertSupprt_Trustlevl_nat, p_ExpertSupprt_Trustlevl_CACT_HERD, p_ExpertSupprt_PercentChange_nat, p_ExpertSupprt_Trustlevl_CACT_yield, p_ExpertSupprt_Absolute_CACT, p_ExpertSupprt_Percentchange_lambs,
    p_ExpertSupprt_TRustlevl_nat_less, p_ExpertSupprt_dairy_PercentChange_removed, p_ExpertSupprt_dairy_Absolute, p_ExpertSupprt_dairy_absolute_removed, p_ExpertSupprt_PercentChange_blend, p_ExpertSupprt_Absolute_Support,
    p_ExpertSupprt_Absolute_base)
from capri_mod.pipeline.captrd.equations.national_support.trust_level_rule import (  # noqa: E402,F401  the parts (moved as they were)
    p_ExpertSupprt_trustlevl_rule)
from capri_mod.pipeline.captrd.equations.national_support.result_bounds import (  # noqa: E402,F401  the parts (moved as they were)
    p_result_expert_bound, p_result_expert_bound_percent, p_result_expertLo_BL4, p_result_expertUp_BL4)
from capri_mod.pipeline.captrd.equations.national_support.dairy import (  # noqa: E402,F401  the parts (moved as they were)
    p_ExpertSupprt_PercentChange_natDCOW, p_ExpertSupprt_PercentChange_natCOMI, p_ExpertSupprt_Absolute_SHGM, p_ExpertSupprt_PercentChange_copy)
from capri_mod.pipeline.captrd.equations.national_support.by_country import (  # noqa: E402,F401  the parts (moved as they were)
    p_ExpertSupprt_AT_PIGF_PORK, p_ExpertSupprt_BL4_herds, p_ExpertSupprt_BL4_GROF_COMI, p_ExpertSupprt_DE_INDM_MAIF, p_ExpertSupprt_NT2_INDM_MAIF, p_ExpertSupprt_EL_COMI,
    p_ExpertSupprt_EL_floor, p_ExpertSupprt_EL_PIGF_HERD, p_ExpertSupprt_EL_TRustlevl, p_ExpertSupprt_IT_PIGF, p_ExpertSupprt_IT_SCOW, p_ExpertSupprt_IT_2025,
    p_ExpertSupprt_PercentChange_support, p_ExpertSupprt_PT_PIGF_PORK, p_ExpertSupprt_PT_SOWS_YPIG, p_ExpertSupprt_PT_GROF_cows, p_ExpertSupprt_CY_PercentChange, p_ExpertSupprt_CY_absolute_removed,
    P_Result_support_CS, p_ExpertSupprt_CS_Absolute, p_ExpertSupprt_BA_POUF, p_ExpertSupprt_EE_COMI, p_ExpertSupprt_RO_MAIF, p_ExpertSupprt_NO_COMI,
    p_ExpertSupprt_NO_mrkKeyPos, p_ExpertSupprt_TUR)

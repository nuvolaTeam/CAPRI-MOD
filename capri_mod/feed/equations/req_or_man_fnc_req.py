r"""CAPRI's animal requirement functions: per head and technology the energy, crude protein, lysine, dry matter, fibre
and intake capacities, the production days, and the feed-share bounds and nutrient densities of the rations
(feed/req_or_man_fnc.gms called with %1 = req, PART I and PART II; CAPRI star 3.0, feed version _pw as in CAPRI's runs,
capmod/set_global_variables.gms l. 125).

CAPRI calls the file in this mode from capmod/def_requirements.gms l. 23 (the simulation year's yields; the baseline's
p_animReqLit is the result, l. 33) and in CAPREG and COCO. In 'req' mode CAPRI's %p_condition% is p_technFact (an
assignment holds where the technology has a share, not where the herd is), and the per-head parameters carry the
technology A (%yr_A% = A); the yields of a technology are the data's times (p_technFact(r, act, output, A) + 1).

One function per CAPRI statement block, in CAPRI's order; ReqState holds CAPRI's symbols of the call as dictionaries;
req_or_man_fnc_req runs the blocks in order. The stocking rate's blocks are the manure mode's (the same statements,
capri_mod/feed/equations/req_or_man_fnc.py DATA_AGGR_YCOW and p_stockingRate). The literal tables of feed/feed_decl.gms
are data (capri_data/2017/feed/req_or_man_params.csv, tools/build/build_req_or_man_params.py).

Departures from CAPRI: none in the functions. The inputs are the caller's (req_or_man_fnc_req's docstring).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set

from capri_mod.feed.equations.requirements.state import (  # noqa: E402,F401  the parts (moved as they were)
    SUBENE, REQSE, FEED, REQSR, REQSC, REQMSE,
    FODDI, fibreRichFeed, ACATTLE, FeedAggr, A_ALL, ReqState,
    _set_req, p_dataCopy_req)
from capri_mod.feed.equations.requirements.dairy_cows import (  # noqa: E402,F401  the parts (moved as they were)
    p_milkFatCont, p_meanLiveWgt_DCOW, p_animProdDays_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW, p_fatCorMilk_DCOW,
    p_animReq_DCOW_energy, p_animReq_DCOW_dry_matter)
from capri_mod.feed.equations.requirements.suckler_cows import (  # noqa: E402,F401  the parts (moved as they were)
    p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_animReq_SCOW, p_femWgt)
from capri_mod.feed.equations.requirements.calves import (  # noqa: E402,F401  the parts (moved as they were)
    _scaled_ms, _final_CALF, p_dailyWgtIncrease_CALF, p_animProdDays_CALF, CALF_light, _crpr_lt150,
    _crpr_gt150, _neg, p_crprReq_CALF_light, p_animReq_CALF_light, CALF_heavy_b1, p_crprReq_CALF_heavy_b1,
    p_animReq_CALF_heavy_b1, CALF_heavy_b2, p_crprReq_CALF_heavy_b2, p_animReq_CALF_heavy_b2, CALR_weaning, CALR_80_150,
    CALR_last, CALR_last_requirements)
from capri_mod.feed.equations.requirements.bulls_heifers import (  # noqa: E402,F401  the parts (moved as they were)
    BULF_growth, BULF_requirements, HEIF_growth, HEIF_requirements, HEIR_growth, HEIR_requirements)
from capri_mod.feed.equations.requirements.pigs import (  # noqa: E402,F401  the parts (moved as they were)
    SOWS_requirements, SwitchLiveWgt, PIGF_requirements)
from capri_mod.feed.equations.requirements.poultry import (  # noqa: E402,F401  the parts (moved as they were)
    HENS_requirements, POUF_requirements)
from capri_mod.feed.equations.requirements.sheep_goats import (  # noqa: E402,F401  the parts (moved as they were)
    SHGM_growth, SHGM_crude_protein, SHGM_requirements, SHGF_requirements, DATA_OANI_FOUT)
from capri_mod.feed.equations.requirements.requirement_rows import (  # noqa: E402,F401  the parts (moved as they were)
    _techs_all, p_animReq_CRPR, p_animReq_erase, p_animReq_signs, p_animReq_ENNE, p_animReq_per_day,
    p_animReq_DRMA, p_animReqSubEne)
from capri_mod.feed.equations.requirements.feed_shares import (  # noqa: E402,F401  the parts (moved as they were)
    _shares, feed_shares_defaults, p_maxFeedShare_FOTH, p_totEnneFromFibreRichFeed, p_minFeedShare_fibre, feed_shares_special,
    p_NutContFeed_and_aggregate_shares)


#: CAPRI's statement blocks of 'req' mode, in CAPRI's order (feed/req_or_man_fnc.gms PART I and PART II)
BLOCKS = (DATA_AGGR_YCOW, p_stockingRate, p_dataCopy_req,
          p_milkFatCont, p_meanLiveWgt_DCOW, p_animProdDays_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW, p_fatCorMilk_DCOW,
          p_animReq_DCOW_energy, p_animReq_DCOW_dry_matter,
          p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_animReq_SCOW, p_femWgt,
          p_dailyWgtIncrease_CALF, p_animProdDays_CALF, CALF_light, p_crprReq_CALF_light, p_animReq_CALF_light,
          CALF_heavy_b1, p_crprReq_CALF_heavy_b1, p_animReq_CALF_heavy_b1,
          CALF_heavy_b2, p_crprReq_CALF_heavy_b2, p_animReq_CALF_heavy_b2,
          CALR_weaning, CALR_80_150, CALR_last, CALR_last_requirements,
          BULF_growth, BULF_requirements, HEIF_growth, HEIF_requirements, HEIR_growth, HEIR_requirements,
          SOWS_requirements, PIGF_requirements, HENS_requirements, POUF_requirements,
          SHGM_growth, SHGM_crude_protein, SHGM_requirements, SHGF_requirements, DATA_OANI_FOUT,
          p_animReq_CRPR, p_animReq_erase, p_animReq_signs, p_animReq_ENNE, p_animReq_per_day, p_animReq_DRMA,
          p_animReqSubEne,
          feed_shares_defaults, p_maxFeedShare_FOTH, p_totEnneFromFibreRichFeed, p_minFeedShare_fibre,
          feed_shares_special, p_NutContFeed_and_aggregate_shares)


def req_or_man_fnc_req(st: ReqState) -> ReqState:
    r"""CAPRI's 'req' call of feed/req_or_man_fnc.gms at "Y": every block of BLOCKS in order, on st (changed in place
    and returned). After it: st.p_animReq (per head and day; CAPRI's p_animReqLit is this, def_requirements.gms l. 33),
    st.p_animProdDays, st.p_animReqSubEne, st.p_crprReq (per head), st.p_minFeedShare, st.p_maxFeedShare and
    st.p_NutContFeed.

    The caller supplies CAPRI's inputs at the year (ReqState's docstring) and st.DATA_BAS (DATA at "BAS"), st.MAACT,
    st.MCACT, st.FEED_TO_O and st.PACT_TO_O (CAPRI's sets)."""
    for block in BLOCKS:
        block(st)
    return st

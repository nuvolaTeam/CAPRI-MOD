r"""CAPRI's manure output functions: the N, P2O5 and K2O at the tail of each animal activity, per head (MANN, MANP, MANK),
from the year's herd data (feed/req_or_man_fnc.gms called with %1 = man, PART I and PART III; CAPRI star 3.0).

CAPRI's simulation runs this once before it solves (capmod.gms l. 1090, $BATINCLUDE 'feed\req_or_man_fnc.gms' man '"Y"'
when not in baseline mode), on DATA(..., "Y"), the simulation year's data as loaded (the baseline's state). In 'man' mode
the file computes, animal by animal:
- MANP and MANK from the milk yield, the fattening days and the mean live weight, with CAPRI's fixed manure nutrient
  contents (p_NutContManureKgM3, p_addExcrPerkgMilk; feed/feed_decl.gms); not from the feed (the feed-based method,
  %Phoendogenous%, is off in CAPRI's Green Deal runs);
- MANN from the literature crude-protein requirement p_crprReq (the same functions as the 'req' mode's CRPR, at the
  data's yields), times the correction factor p_animExcrProtCorrFact over 6 kg of crude protein per kg N, less the N in
  the animal's products CRPR_EXPT (fert/calc_nexport.gms, run first in PART III).

One function per CAPRI statement block, in CAPRI's order; ManState holds CAPRI's symbols of the block (p_dataCopy,
p_meanLiveWgt, p_fatngDays, ...) as dictionaries; req_or_man_fnc_man runs the blocks in order. CAPRI's %yr_A% and %yr%
are both "Y" in 'man' mode, so the per-head parameters carry no technology index; p_crprReq and p_MANN_A carry CAPRI's
technology A. The literal tables of feed/feed_decl.gms are data (capri_data/2017/feed/req_or_man_params.csv,
tools/build/build_req_or_man_params.py), with the pig-fattening requirement tables of CAPRI's dat/feed/porkreq.gms
(p_pigsReqLowWgt, p_pigsReqHighWgt); a call without them leaves the fattened pigs out (ManState.not_computed, see
p_finalLiveWgt_PIGF).

Departures from CAPRI: none in the functions. The inputs are the caller's (req_or_man_fnc_man's docstring).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set

from capri_mod.feed.equations.manure_output.state import (  # noqa: E402,F401  the parts (moved as they were)
    DCOW, CALF, CALR, BULF, HEIF, NRUMI,
    FOUT, curRows, ManState, p_NutContManureKgM3_per_kg_day, DATA_AGGR_YCOW, p_stockingRate,
    p_dataCopy_man)
from capri_mod.feed.equations.manure_output.dairy_cows import (  # noqa: E402,F401  the parts (moved as they were)
    p_dataCopy_curRows_DCOW, p_milkFatCont, p_meanLiveWgt_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW)
from capri_mod.feed.equations.manure_output.suckler_cows import (  # noqa: E402,F401  the parts (moved as they were)
    p_dataCopy_curRows_SCOW, p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_femWgt)
from capri_mod.feed.equations.manure_output.calves import (  # noqa: E402,F401  the parts (moved as they were)
    _scaled_ms_daily, p_dailyWgtIncrease_CALF, p_animProdDays_CALF, _final_wgt_CALF, p_meanLiveWgt_CALF_light, p_fatngDays_CALF_light,
    p_dataCopy_curRows_CALF_light, _crpr_growth_lt150, _crpr_growth_gt150, p_crprReq_CALF_light, p_meanLiveWgt_CALF_heavy_b1, p_fatngDays_CALF_heavy_b1,
    p_dataCopy_curRows_CALF_heavy_b1, p_crprReq_CALF_heavy_b1, p_meanLiveWgt_CALF_heavy_b2, p_fatngDays_CALF_heavy_b2, p_dataCopy_curRows_CALF_heavy_b2, p_crprReq_CALF_heavy_b2,
    CALR_weaning, p_crprReq_CALR_weaning, CALR_80_150, p_dataCopy_curRows_CALR_80_150, p_crprReq_CALR_80_150, p_fatngDays_CALR_last,
    p_dailyWgtIncrease_CALR_last, p_meanLiveWgt_CALR_last, p_dataCopy_curRows_CALR_last, p_crprReq_CALR_last)
from capri_mod.feed.equations.manure_output.bulls_heifers import (  # noqa: E402,F401  the parts (moved as they were)
    p_dailyWgtIncrease_BULF, p_fatngDays_BULF, p_meanLiveWgt_BULF, p_dataCopy_curRows_BULF, p_dataCopy_DRMN_BULF, p_crprReq_BULF,
    p_dailyWgtIncrease_HEIF, p_fatngDays_HEIF, p_meanLiveWgt_HEIF, p_dataCopy_curRows_HEIF, p_dataCopy_DRMN_HEIF, p_crprReq_HEIF,
    p_meanLiveWgt_HEIR, p_fatngDays_HEIR, p_dailyWgtIncrease_HEIR, p_dataCopy_curRows_HEIR, p_crprReq_HEIR)
from capri_mod.feed.equations.manure_output.pigs import (  # noqa: E402,F401  the parts (moved as they were)
    p_dataCopy_curRows_SOWS, p_crprReq_SOWS, p_finalLiveWgt_PIGF, SwitchLiveWgt, _pig_classes, p_fatngDays_PIGF,
    p_dataCopy_curRows_PIGF, p_crprReq_PIGF)
from capri_mod.feed.equations.manure_output.poultry import (  # noqa: E402,F401  the parts (moved as they were)
    p_meanLiveWgt_HENS, p_dataCopy_curRows_HENS, p_crprReq_HENS, p_meanLiveWgt_POUF, p_animProdDays_POUF, p_dataCopy_curRows_POUF,
    p_crprReq_POUF)
from capri_mod.feed.equations.manure_output.sheep_goats import (  # noqa: E402,F401  the parts (moved as they were)
    p_sharGoatHerd, p_meanLiveWgt_SHGM, p_milkPerDay_SHGM, p_dataCopy_curRows_SHGM, p_crprReq_EWES, p_crprReq_GOAT,
    p_crprReq_SHGM, p_dailyWgtIncrease_SHGF, p_fatngDays_SHGF, p_meanLiveWgt_SHGF, p_dataCopy_curRows_SHGF, p_crprReq_SHGF)
from capri_mod.feed.equations.manure_output.manure_rows import (  # noqa: E402,F401  the parts (moved as they were)
    p_MANN_A, DATA_MANN, DATA_curRows)


#: CAPRI's statement blocks of 'man' mode, in CAPRI's order (feed/req_or_man_fnc.gms PART I and PART III)
BLOCKS = (DATA_AGGR_YCOW, p_stockingRate, p_dataCopy_man,
          p_dataCopy_curRows_DCOW, p_milkFatCont, p_meanLiveWgt_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW,
          p_dataCopy_curRows_SCOW, p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_femWgt,
          p_dailyWgtIncrease_CALF, p_animProdDays_CALF,
          p_meanLiveWgt_CALF_light, p_fatngDays_CALF_light, p_dataCopy_curRows_CALF_light, p_crprReq_CALF_light,
          p_meanLiveWgt_CALF_heavy_b1, p_fatngDays_CALF_heavy_b1, p_dataCopy_curRows_CALF_heavy_b1,
          p_crprReq_CALF_heavy_b1,
          p_meanLiveWgt_CALF_heavy_b2, p_fatngDays_CALF_heavy_b2, p_dataCopy_curRows_CALF_heavy_b2,
          p_crprReq_CALF_heavy_b2,
          CALR_weaning, p_crprReq_CALR_weaning, CALR_80_150, p_dataCopy_curRows_CALR_80_150, p_crprReq_CALR_80_150,
          p_fatngDays_CALR_last, p_dailyWgtIncrease_CALR_last, p_meanLiveWgt_CALR_last, p_dataCopy_curRows_CALR_last,
          p_crprReq_CALR_last,
          p_dailyWgtIncrease_BULF, p_fatngDays_BULF, p_meanLiveWgt_BULF, p_dataCopy_curRows_BULF, p_dataCopy_DRMN_BULF,
          p_crprReq_BULF,
          p_dailyWgtIncrease_HEIF, p_fatngDays_HEIF, p_meanLiveWgt_HEIF, p_dataCopy_curRows_HEIF, p_dataCopy_DRMN_HEIF,
          p_crprReq_HEIF,
          p_meanLiveWgt_HEIR, p_fatngDays_HEIR, p_dailyWgtIncrease_HEIR, p_dataCopy_curRows_HEIR, p_crprReq_HEIR,
          p_dataCopy_curRows_SOWS, p_crprReq_SOWS,
          p_finalLiveWgt_PIGF, p_fatngDays_PIGF, p_dataCopy_curRows_PIGF, p_crprReq_PIGF,
          p_meanLiveWgt_HENS, p_dataCopy_curRows_HENS, p_crprReq_HENS,
          p_meanLiveWgt_POUF, p_animProdDays_POUF, p_dataCopy_curRows_POUF, p_crprReq_POUF,
          p_sharGoatHerd, p_meanLiveWgt_SHGM, p_milkPerDay_SHGM, p_dataCopy_curRows_SHGM, p_crprReq_EWES,
          p_crprReq_GOAT, p_crprReq_SHGM,
          p_dailyWgtIncrease_SHGF, p_fatngDays_SHGF, p_meanLiveWgt_SHGF, p_dataCopy_curRows_SHGF, p_crprReq_SHGF,
          p_MANN_A, DATA_MANN, DATA_curRows)


def req_or_man_fnc_man(st: ManState) -> ManState:
    r"""CAPRI's 'man' call of feed/req_or_man_fnc.gms at "Y": every block of BLOCKS in order, on st (changed in place
    and returned). After it, st.DATA holds MANN, MANP and MANK of the animal activities, and AGGR YCOW.

    The caller supplies CAPRI's inputs at the year: DATA (the herds, yields, days, daily gains and the N in products
    CRPR_EXPT, fert/calc_nexport.gms at the year, which CAPRI runs at the start of PART III), the technologies' shares
    p_technFact, the correction factor p_animExcrProtCorrFact and the literal tables of feed/feed_decl.gms, with
    p_NutContManureKgM3 per cubic metre (p_NutContManureKgM3_per_kg_day is applied here). The functions run on the
    regions of st.RS."""
    st.p_NutContManureKgM3 = p_NutContManureKgM3_per_kg_day(st.p_NutContManureKgM3)
    for block in BLOCKS:
        block(st)
    return st

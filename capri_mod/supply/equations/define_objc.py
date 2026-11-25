r"""CAPRI's objective's linear terms (capmod/define_objc.gms, star 3.0): the plant protection cost per ha as CAPRI's
Green Deal step values it.

capri_mod/supply/policy.py (PolicyBlock._plap_capri_step_cost, the comparison switches of DEP-51) calls it.
"""
from __future__ import annotations


def p_linObjeCont_PLAP(PLAP_UVAP, percentageChange, TF_I, keep_tech_change, deflator):
    r"""The plant protection part of p_linObjeCont(regions, pacts, A) at the crop's mean technology, in the model's
    money: the crop's PLAP coefficient at the member state's UVAP (PLAP_UVAP, EUR per ha in CAPRI's 2030 money)
    changed by the Green Deal's regional percentage, (1 + pc) [TF_I] / TF_I ([TF_I] with
    greendeal_inputs_keep_tech_change), over the money deflator; 1 without a change.

    CAPRI's GAMS (capmod/define_objc.gms l. 42-44):

          p_linObjeCont(%regions%,%pacts%,A) $ p_technFact(%regions%,%pacts%,"LEVL",A)
                = (-0.001)*SUM(PACT_TO_I(%pacts%,IobjCont), DATA(%regions%,%pacts%,IobjCont,"Y") * (p_technFact(%regions%,%pacts%,IobjCont,A)+1.)
                                       * p_dataCopy(%regions%,"UVAP",IobjCont,"Y"));

    In this project's notation: P_s = q UVAP (1 + pc) [TF_I] / TF_I / deflator. Departures from CAPRI: PLAP only,
    at the mean technology (the factors' T1 - T2 part the caller's), a cost per ha (CAPRI's -0.001 x, a revenue in
    1000 EUR)."""
    ratio = (1.0 + percentageChange) * (TF_I if keep_tech_change else 1.0) / TF_I if percentageChange != 0.0 else 1.0
    return PLAP_UVAP * ratio / deflator

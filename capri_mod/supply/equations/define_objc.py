r"""CAPRI's objective's linear terms (capmod/define_objc.gms, star 3.0): an activity's variable cost of its directly
yield-dependent inputs (p_linObjeCont), and the plant protection cost per ha as CAPRI's Green Deal step values it.

capri_mod/supply/policy.py (PolicyBlock._plap_capri_step_cost, the comparison switches of DEP-51) calls
p_linObjeCont_PLAP; the animals' costs per head of DEP-13 step 3 p_linObjeCont.
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


def p_linObjeCont(DATA_I, p_technFact_I, UVAP_I):
    r"""p_linObjeCont(regions, pacts, A): the activity's variable cost in the objective's linear part, its inputs of
    IobjCont (the directly yield-dependent inputs IY, sets.gms l. 5059-5066: no fertilisers, feeds or young animals,
    which the supply model handles through its rows) at the member state's UVAP of the year, negative (1000 EUR per
    unit of the activity; CAPRI's DATA per unit, UVAP per t or 1000 units).

    CAPRI's GAMS (capmod/define_objc.gms l. 39-44):

          option kill=p_dataCopy;
          p_dataCopy(%regions%,"UVAP",IobjCont,"Y")  = sum(RU_MS(%regions%,MS),DATA(MS,"UVAP",IobjCont,"Y"));

          p_linObjeCont(%regions%,%pacts%,A) $ p_technFact(%regions%,%pacts%,"LEVL",A)
                = (-0.001)*SUM(PACT_TO_I(%pacts%,IobjCont), DATA(%regions%,%pacts%,IobjCont,"Y") * (p_technFact(%regions%,%pacts%,IobjCont,A)+1.)
                                       * p_dataCopy(%regions%,"UVAP",IobjCont,"Y"));

    DATA_I: {I: DATA(regions, pacts, I, "Y")} of the inputs of IobjCont the activity has (PACT_TO_I); p_technFact_I:
    {I: p_technFact(regions, pacts, I, A)} of technology A (absent: 0); UVAP_I: {I: the member state's UVAP(I, "Y")}
    (p_dataCopy, RU_MS). In this project's notation: c_A = -0.001 sum_I x_I (1 + t_I,A) UVAP_I. Departures from CAPRI:
    none."""
    return -0.001 * sum(float(x or 0.0) * (float(p_technFact_I.get(i, 0.0) or 0.0) + 1.0)
                        * float(UVAP_I.get(i, 0.0) or 0.0) for i, x in DATA_I.items())


def IS_members(sets_gms_text: str) -> tuple:
    r"""The members of IS(I), the inputs produced in the sector (fertilisers, feeds, young animals), as sets.gms
    declares them, from its text (the set is a literal list in CAPRI's code, not exported with sim_ini's sets).

    CAPRI's GAMS (sets.gms l. 5046-5052):

        *
            SET IS(I) Inputs intrasectorally produced /
        *
                NITF,  PHOF , POTF,
        *       Feedingsstuff + young animals
                FCER , FPRO , FENE , FMIL , FOTH , FGRA,  FCOM, FSGM, FMAI, FROO, FOFA, FSTR,
                ICAM,  ICAF,  IHEI , ICOW , IPIG , IBUL,  ILAM /;

    Departures from CAPRI: none (the comment lines inside the list are skipped, as GAMS does)."""
    import re
    m = re.search(r"SET\s+IS\(I\)[^/]*/(.*?)/\s*;", sets_gms_text, re.S | re.I)
    if not m:
        raise ValueError("sets.gms: no SET IS(I)")
    body = "\n".join(ln for ln in m.group(1).splitlines() if not ln.lstrip().startswith("*"))
    return tuple(x.strip() for x in body.replace("\n", ",").split(",") if x.strip())


def IobjCont(I, IS, IWAT, PEST_DISAGG=False, pesModDis=()):
    r"""IobjCont(rows): the directly yield-dependent inputs IY, those of p_linObjeCont: every input but those produced
    in the sector (IS), the chicks (ICHI), water (IWAT) and the mitigation input (mitiI).

    CAPRI's GAMS (sets.gms l. 5059-5067):

            SET IY(I) "Directly yield dependent inputs";
            IY(I) $ (NOT IS(I)) = YES;
            IY("ICHI")          = NO;
            IY(IWAT)            = NO;
            IY("mitiI")         = NO;

            SET IobjCont(rows) "yield dependent inputs captured in p_linObjeCont";
            IobjCont(IY)  = YES;
        $ifi %PEST_DISAGG%==ON IobjCont(pesModDis) = no;

    I, IS, IWAT: the sets' members. Departures from CAPRI: none (%PEST_DISAGG% off, the reference run's)."""
    iy = [i for i in I if i not in set(IS) and i != "ICHI" and i not in set(IWAT) and i != "mitiI"]
    if PEST_DISAGG:
        iy = [i for i in iy if i not in set(pesModDis)]
    return tuple(iy)

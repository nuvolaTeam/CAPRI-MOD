r"""CAPRI's end of the baseline feed calibration (baseline/fedtrm_fin.gms; CAPRI star 3.0): the NUTS 1 rows emptied
where they are not regional units, the corrections p_animReqCorrFac (the calibrated requirement over the requirement
function's) and the manure's protein factor times the crude protein's correction.

CAPRI runs it from capmod/def_fert_and_requirements.gms l. 42 after feed/fedtrm_cal_pw.gms
(capri_mod/feed/equations/fedtrm_cal_pw.py) and writes the corrections to results/baseline/fedtrm_<...>.gdx, which a
simulation applies (baseline/adjust.gms, adjust.py). The restart files (mefed, l. 29) and their kills (l. 31-34) are
CAPRI's file handling. One function per CAPRI statement block. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from capri_mod.feed.equations import req_or_man_fnc_req as rq


def NUTS1_emptied(NUTS1: tuple, DATA_Y: dict, p_animReq: dict, p_technFact: dict, MAACT: tuple) -> None:
    r"""The NUTS 1 regions that are not regional units (but one region): their DATA at "Y", requirements and
    technologies' shares emptied. NUTS1: CAPRI's NUTS1 after l. 36-37 (the caller's).

    CAPRI's GAMS (baseline/fedtrm_fin.gms l. 36-43):

          option kill=NUTS1;
          NUTS1(SRNUTS1) $ ((SUM(MAP_RR(SRNUTS1,RU), 1) GT 1) OR SUM(RU, SAMEAS(SRNUTS1,RU))) = NO;
        *
          DATA(NUTS1,COLS,ROWS,"Y")    = 0;
          p_animReq(NUTS1,MAACT,A,REQM)    = 0;
          p_animReq(NUTS1,MAACT,A,"DRMA")  = 0;
          p_technFact(NUTS1,MPACT,"LEVL",A)  = 0;
          p_technFact(NUTS1,MPACT,IO,A)      = 0;

    DATA_Y: {(region, column, row): value} at "Y". Departures from CAPRI: none."""
    n1 = set(NUTS1)
    for dct in (DATA_Y, p_technFact):
        for k in [k for k in dct if k[0] in n1]:
            del dct[k]
    for k in [k for k in p_animReq if k[0] in n1 and k[1] in MAACT and (k[3] in rq.REQSR or k[3] == "DRMA")]:
        del p_animReq[k]


def p_animReqCorrFac(RS: tuple, MAACT: tuple, p_animReq: dict, v_animReq_L: dict) -> dict:
    r"""The corrections: the calibrated requirement over the level the calibration leaves (the requirement function's
    for energy and protein, the lower of it and the ration's for the inequalities); the feeds' rows 1.

    CAPRI's GAMS (baseline/fedtrm_fin.gms l. 47-48):

          p_animReqCorrFac(RS,MAACT,A,REQM)  $ sum(sameas(REQM,FEED),1) = 1;
          p_animReqCorrFac(RS,MAACT,A,REQM)  = (p_animReq(RS,MAACT,A,REQM) / v_animReq.L(RS,MAACT,A,REQM) ) $ v_animReq.L(RS,MAACT,A,REQM);

    l. 48 assigns every (RS, MAACT, A, REQM), the feeds' rows included, so l. 47's 1 is overwritten: a feed's row gets
    its requirement over its level, 1, as the calibration leaves the level at the requirement (fedtrm_cal_pw.gms
    l. 275). Returns {(region, animal, A, item): factor}. Departures from CAPRI: none."""
    rs = set(RS)
    out = {}
    for k, v in v_animReq_L.items():
        r, a, t, item = k
        if r in rs and a in MAACT and item in rq.REQSR and v:
            q = p_animReq.get(k, 0.0) / v
            if q:
                out[k] = q
    return out


def p_animExcrProtCorrFact_calibrated(RU: tuple, MAACT: tuple, p_technFact: dict, p_animExcrProtCorrFact_Y: dict,
                                      corr: dict) -> None:
    r"""The manure's protein factor times the crude protein's correction.

    CAPRI's GAMS (baseline/fedtrm_fin.gms l. 52):

          p_animExcrProtCorrFact(RU,MAACT,A,"Y") $ p_technFact(RU,MAACT,"LEVL",A) = p_animExcrProtCorrFact(RU,MAACT,A,"Y") * p_animReqCorrFac(RU,MAACT,A,"CRPR");

    Departures from CAPRI: none."""
    ru = set(RU)
    for (r, a, t), v in list(p_animExcrProtCorrFact_Y.items()):
        if r in ru and a in MAACT and p_technFact.get((r, a, "LEVL", t), 0.0):
            p_animExcrProtCorrFact_Y[(r, a, t)] = v * corr.get((r, a, t, "CRPR"), 0.0)

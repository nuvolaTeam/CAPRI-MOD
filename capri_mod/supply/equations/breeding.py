"""CAPRI's breeding options' data (envind/breeding.gms; CAPRI star 3.0): the statement the model's feed supplements take
from it, the estimated dry-matter intake per head (tools/build/build_supplement_effects.py, the supplements' dosage and
cost; capri_mod/supply/nlp.py, the ration fat limit SupplementPerc_'s intake at the run's requirements).
"""
from __future__ import annotations


def p_animReqCopy_DRMA(DRMN, DRMX_abs):
    r"""p_animReqCopy(RU, DCOW, A, DRMA): the estimated average dry-matter intake per head, a quarter of the way from the
    minimum to the maximum intake (l. 234-236).

    CAPRI's GAMS (envind/breeding.gms l. 234-236):

          p_animReqCopy(RU,DCOW,A,"DRMA") $ (DATA(RU,DCOW,"LEVL","Y")*p_technFact(RU,DCOW,"LEVL",A)) = 0.0;
          p_animReqCopy(RU,DCOW,A,"DRMA") $ (p_animReqCopy(RU,DCOW,A,"DRMN") $ p_animReqCopy(RU,DCOW,A,"DRMX"))
            = p_animReqCopy(RU,DCOW,A,"DRMN") + (-p_animReqCopy(RU,DCOW,A,"DRMX") - p_animReqCopy(RU,DCOW,A,"DRMN")) / 4.;

    CAPRI stores the maximum intake with a negative sign (DRMX <= 0); the model's DMAX is its absolute value, so the
    caller passes DRMX_abs = -DRMX. breeding.gms writes it per day for the dairy cows; the model applies it per head and
    year to its cattle (the per-day division of l. 229 cancels in the ratio). CAPRI's supply model reads p_animReq(DRMA)
    from its requirement functions instead (sim_ini_21730 carries it for 2030: DE21's DCOL 17.0 kg a day, this estimate
    16.3); the model's 2017 data have no DRMA (KNOWN_ISSUES K93). Departures from CAPRI: the estimate in place of
    p_animReq(DRMA), registered with the supplements."""
    n, x = float(DRMN or 0.0), float(DRMX_abs or 0.0)
    return n + (x - n) / 4.0 if (n and x) else 0.0

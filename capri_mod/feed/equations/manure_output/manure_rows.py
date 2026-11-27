r"""The manure N per head (p_MANN_A, DATA_MANN) and the current rows (DATA_curRows) (feed/req_or_man_fnc.gms, 'man'
mode; moved from capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.manure_output.state import ManState, curRows  # noqa: E402




# ------------------------------------------------------------------ PART III: MANN, and the copy of MANP and MANK
def p_MANN_A(st: ManState) -> None:
    r"""The N at the tail per head and technology: the crude-protein requirement times CAPRI's correction factor, over 6
    kg of crude protein per kg N, less the N in the animal's products (DATA CRPR_EXPT, fert/calc_nexport.gms at the
    year, which PART III runs first: the caller's DATA), at least 0.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1824-1825):

          p_MANN_A(RS,AACT,A,%yr%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A) $ p_crprReq(RS,AACT,A,%yr%))
            = MAX(0,p_crprReq(RS,AACT,A,%yr%) * p_animExcrProtCorrFact(RS,AACT,A,%yr%) / 6.0 - DATA(RS,AACT,"CRPR_EXPT",%yr%));

    Departures from CAPRI: none."""
    st.p_MANN_A = {}
    for (r, a, t), c in st.p_crprReq.items():
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t) and c:
            st.p_MANN_A[(r, a, t)] = max(0, c * float(st.p_animExcrProtCorrFact.get((r, a, t), 0.0)) / 6.0
                                         - st.D(r, a, "CRPR_EXPT"))


def DATA_MANN(st: ManState) -> None:
    r"""The N at the tail per head: over CAPRI's technologies, by their shares.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1827-1828):

          DATA(RS,AACT,"MANN",%yr%) $ SUM(A,p_crprReq(RS,AACT,A,%yr%))
            = SUM(A, p_MANN_A(RS,AACT,A,%yr%)*p_technFact(RS,AACT,"LEVL",A));

    Departures from CAPRI: none."""
    acts = {(r, a) for (r, a, t), c in st.p_crprReq.items() if a not in ("EWES", "GOAT")}   # AACT: not the ewes, goats
    for r, a in acts:
        if sum(c for (rr, aa, t), c in st.p_crprReq.items() if rr == r and aa == a):
            st.DATA[(r, a, "MANN")] = sum(v * st.tf(r, a, "LEVL", t) for (rr, aa, t), v in st.p_MANN_A.items()
                                          if rr == r and aa == a)


def DATA_curRows(st: ManState) -> None:
    r"""P2O5 and K2O at the tail: copied to DATA from the functions' copy (CAPRI's exogenous method).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1836-1837):

          DATA(RS,AACT,curRows,%yr%)
            = p_dataCopy(RS,AACT,curRows,%yr%);

    Departures from CAPRI: only the animal activities' rows are copied (the copy's other rows are DATA's own)."""
    for (r, a, row), v in st.p_dataCopy.items():
        if row in curRows:
            st.DATA[(r, a, row)] = v

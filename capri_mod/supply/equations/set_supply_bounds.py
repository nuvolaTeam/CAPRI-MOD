r"""CAPRI's bounds of the supply models (supply/set_supply_bounds.gms, star 3.0) the model's accounts apply: the loss
shares of the nitrogen cascade between 0 and 1.

Used by capri_mod/environmental/phosphorus.py (PhosphorusBlock._p_runtot).
"""
from __future__ import annotations


def v_emiLoss_bounds(share):
    r"""v_emiLoss.lo / .up (RU, AACT, allmat, EMTYPE): a loss share of the nitrogen cascade held within [0, 1].

    CAPRI's GAMS (supply/set_supply_bounds.gms l. 240-243):

        $ifi %ghgAbatement%==on        v_emiLoss.lo(%REGIONS%,AACT,allmat,EMTYPE) = 0;
        $ifi %ghgAbatement%==on        v_emiLoss.lo(%REGIONS%,"NETF",allmat,EMTYPE) = 0;
        $ifi %ghgAbatement%==on        v_emiLoss.up(%REGIONS%,AACT,allmat,EMTYPE) = 1;
        $ifi %ghgAbatement%==on        v_emiLoss.up(%REGIONS%,"NETF",allmat,EMTYPE) = 1;

    In this project's notation: s' = min(max(s, 0), 1). Departures from CAPRI: CAPRI bounds the variables of its NLP; the
    accounts clip the cascade's shares evaluated at the solution (the same values where the bounds bind)."""
    return min(max(float(share), 0.0), 1.0)

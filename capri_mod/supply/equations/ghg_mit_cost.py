"""CAPRI's cost of the mitigation options (GHG_Mit_Cost_), by the base each option's cost is charged on."""
from __future__ import annotations


def GHG_Mit_Cost_targFertMan(v_ManureNPK_tail, v_Miti, costPar_lin, costPar_sqr, NMAN, EmiCalMan=0.0):
    """CAPRI: the manure options' part of GHG_Mit_Cost_(r), the fertiliser options aimed at applied manure
    (mitiTarget in targFertMan: the nitrification inhibitor on manure, NITR_INH with target N2OMAN).

    Source: supply/supply_model.gms l. 5057-5190 (GHG_Mit_Cost_, the standard version; its base for targFertMan
    l. 5144-5149), l. 984-1044 (InclEmiAppl_), l. 935-955 and 962-978 (ManureNPK_, manExportOrAppl_); EmiCalMan:
    envind/ghgMiti.gms l. 945-962.

    Equation (per region r, summed over the options o with a targFertMan target):

        cost_r = sum_o [ c1_o s_o + 0.5 c2_o s_o^2 ] x ManureNPK_r x (1 + incEmiAppl_r) x (1 + sum_o (NMAN_o + EmiCalMan_o) s_o)

    s_o = v_Miti(r, cropMiti, o, N2OMAN); c1, c2 = costParLin + pmpParLin - subsidy and costParSqr + pmpParSqr (CAPRI's
    accounting and calibrated parts, per t of manure N); (1 + incEmiAppl_r) = the manure N at the tail (excreted less
    the housing and storage losses and the housing runoff) over the manure N net of all gaseous losses (InclEmiAppl_),
    so ManureNPK x (1 + incEmiAppl) is the manure N at the tail, net of the trade. EmiCalMan = 0: CAPRI computes it
    inside $ontext/$offtext (ghgMiti.gms l. 945-962).

    In CAPRI-MOD (arguments): v_ManureNPK_tail = the fertilisation block's manure N pool, fertDistExcr_'s right-hand
    side (the animals' manure N applied, excreted less the housing and storage losses and the housing runoff, with the
    N the ammonia options keep and the manure trade), t; v_Miti the option's share; costPar_lin, costPar_sqr the
    calibrated terms per t of manure N (EUR); NMAN the option's othImpact NMAN (after CAPRI's restMitFert). Returns the
    cost in kEUR (the regional objective's unit).

    Departure: the manure trade enters at the tail (CAPRI scales ManureNPK, net of the trade, by the region's own tail
    factor); equal where the traded manure has the region's own loss ratio. One option (CAPRI's only targFertMan option
    in the Green Deal group is NITR_INH).
    """
    return (v_ManureNPK_tail / 1000.0) * (1 + (NMAN + EmiCalMan) * v_Miti) \
        * (costPar_lin * v_Miti + 0.5 * costPar_sqr * v_Miti * v_Miti)

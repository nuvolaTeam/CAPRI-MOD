r"""CAPRI's cost of the mitigation options (supply/supply_model.gms l. 5057-5190): GHG_Mit_Cost_, by the base each
option's cost is charged on.

Written so far: the manure options' part (K183): the fertiliser options aimed at applied manure (mitiTarget in
targFertMan: the nitrification inhibitor on manure, NITR_INH with target N2OMAN); and the mineral fertiliser options'
base (targFertSyn: the purchases, K175), on which the regional NLP's fertilisation block charges their cost.

CAPRI's GAMS, GHG_Mit_Cost_ (the standard version, l. 5057-5190; the parts per share and the targFertMan base,
l. 5144-5149; the other bases left out here):

    GHG_Mit_Cost_(RUNR).. v_GHG_Mit_Cost(RUNR)  =E=
     sum{(R_RAGG(RUNR,MSACT),mitiTech_map(MSACT,PACT,allMitiTech,mitiTarget)),
          [ (   p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"costParLin")
              + p_ghgMiti(MSACT,PACT,allMitiTech,mitiTarget,"costParLin")
              $ (NOT p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"costParLin"))) * v_Miti(RUNR,PACT,allMitiTech,mitiTarget)
            * (1 $ (NOT SAMEAS(allMitiTech,"Genet_rep")) + ... $ SAMEAS(allMitiTech,"Genet_rep") )
          + .5 * (  p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"costParSqr") + ... ) * sqr(v_Miti(RUNR,PACT,allMitiTech,mitiTarget))
          - (   p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"revenue") + ... ) * v_Miti(RUNR,PACT,allMitiTech,mitiTarget)
          + (   p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"pmpParLin") + ... ) * v_Miti(RUNR,PACT,allMitiTech,mitiTarget)
          + .5 * (  p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"pmpParSqr") + ... ) * sqr(v_Miti(RUNR,PACT,allMitiTech,mitiTarget))
          - (   p_ghgMiti(RUNR,PACT,allMitiTech,mitiTarget,"subsidy") + ... ) * v_Miti(RUNR,PACT,allMitiTech,mitiTarget) ]
        * [ ...
            + (v_ManureNPK(RUNR,"NITF") * (1 + v_incEmiAppl(RUNR)) * (1 + sum(gainsTechFert,
                                            ((p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMAN")+p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","EmiCalMan"))
                                            + (p_ghgMiti(MSACT,"cropMiti",gainsTechFert,"othImpact","NMAN")+p_ghgMiti(MSACT,"cropMiti",gainsTechFert,"othImpact","EmiCalMan"))
                                            $ (not (p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMAN")+p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","EmiCalMan"))))
                                            * v_Miti(RUNR,"cropmiti",gainsTechFert,"N2OMAN"))))
                                            $ (sameas(PACT,"cropMiti") and sum(gainsTechFert $ sameas(allMitiTech,gainsTechFert),1) and sum(targFertMan $ sameas(mitiTarget,targFertMan),1))
            ... ] ...;

Other sources: l. 983-1030 (InclEmiAppl_), l. 935-975 (ManureNPK_, manExportOrAppl_); EmiCalMan: envind/ghgMiti.gms
l. 945-962.

In this project's notation (per region r, summed over the options o with a targFertMan target):

    cost_r = sum_o [ c1_o s_o + 0.5 c2_o s_o^2 ] x ManureNPK_r x (1 + incEmiAppl_r) x (1 + sum_o (NMAN_o + EmiCalMan_o) s_o)

s_o = v_Miti(r, cropMiti, o, N2OMAN); c1, c2 = costParLin + pmpParLin - subsidy and costParSqr + pmpParSqr (CAPRI's
accounting and calibrated parts, per t of manure N); (1 + incEmiAppl_r) = the manure N at the tail (excreted less the
housing and storage losses and the housing runoff) over the manure N net of all gaseous losses (InclEmiAppl_), so
ManureNPK x (1 + incEmiAppl) is the manure N at the tail, net of the trade. EmiCalMan = 0: CAPRI computes it inside
$ontext/$offtext (ghgMiti.gms l. 945-962).

The targFertSyn base (l. 5138-5143), the mineral N purchases scaled by the options' effect on the N need met:

            - (v_netPutQuant(RUNR,"NITF") * (1 + sum(gainsTechFert,
                                            ((p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMIN")+p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","EmiCalMin"))
                                            + (p_ghgMiti(MSACT,"cropMiti",gainsTechFert,"othImpact","NMIN")+p_ghgMiti(MSACT,"cropMiti",gainsTechFert,"othImpact","EmiCalMin"))
                                            $ (not (p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMIN")+p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","EmiCalMin"))))
                                            * v_Miti(RUNR,"cropmiti",gainsTechFert,"N2OSYN"))))
                                            $ (sameas(PACT,"cropMiti") and sum(gainsTechFert $ sameas(allMitiTech,gainsTechFert),1) and sum(targFertSyn $ sameas(mitiTarget,targFertSyn),1))

In this project's notation (the options o with a targFertSyn target, N2OSYN; P = - v_netPutQuant(NITF), the
purchases, t):

    cost_r = P / 1000 x sum_o [ c1_o s_o + 0.5 c2_o s_o^2 ] x (1 + sum_o (NMIN_o + EmiCalMin_o) s_o)

the bracket and the factor composed in CapriRegionalNLP._abatement_block (its pending term), the product with the
purchases in the fertilisation block (GHG_Mit_Cost_targFertSyn).

Departure: the manure trade enters at the tail (CAPRI scales ManureNPK, net of the trade, by the region's own tail
factor); equal where the traded manure has the region's own loss ratio. One option (CAPRI's only targFertMan option in
the Green Deal group is NITR_INH).
"""
from __future__ import annotations


def GHG_Mit_Cost_targFertMan(v_ManureNPK_tail, v_Miti, costPar_lin, costPar_sqr, NMAN, EmiCalMan=0.0):
    """The manure options' part of GHG_Mit_Cost_(r) (l. 5057-5190, the targFertMan base l. 5144-5149), kEUR (the
    regional objective's unit).

    Arguments: v_ManureNPK_tail = the fertilisation block's manure N pool, fertDistExcr_'s right-hand side (the animals'
    manure N applied, excreted less the housing and storage losses and the housing runoff, with the N the ammonia
    options keep and the manure trade), t; v_Miti the option's share; costPar_lin, costPar_sqr the calibrated terms per
    t of manure N (EUR); NMAN the option's othImpact NMAN (after CAPRI's restMitFert)."""
    return (v_ManureNPK_tail / 1000.0) * (1 + (NMAN + EmiCalMan) * v_Miti) \
        * (costPar_lin * v_Miti + 0.5 * costPar_sqr * v_Miti * v_Miti)


def GHG_Mit_Cost_targFertSyn(v_netPutQuant, inv_1000, cost_base):
    """The mineral fertiliser options' part of GHG_Mit_Cost_(r) (l. 5057-5190, the targFertSyn base l. 5138-5143),
    kEUR: P / 1000 x cost_base, P the N purchases (t), cost_base = sum_o [c1_o s_o + 0.5 c2_o s_o^2] x (1 + sum_o
    (NMIN_o + EmiCalMin_o) s_o) (CapriRegionalNLP._abatement_block, K175)."""
    return v_netPutQuant * inv_1000 * cost_base

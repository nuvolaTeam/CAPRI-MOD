r"""CAPRI's cost of the mitigation options (supply/supply_model.gms l. 4984-5116): GHG_Mit_Cost_, by the base each
option's cost is charged on.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

The options' upper bounds are CAPRI's TotMitFertMin_ and TotMitFertMan_ (supply_model.gms l. 4150-4160; each option's
maximum share; the model has one target per option, so the sum over N2OSYN and N2OSYN2 is the share) and, for the catch
crops, the bound CAPRI sets on every option's share, v_Miti.up = MaxShare (supply/set_miti_bounds.gms l. 30-34; star
3.0 has no row for it: the July 2026 release adds Tot_soilCov_); written as the variables' bounds, they have no
function:

   TotMitFertMin_(RUNR,gainsTechFert) $ sum(R_RAGG(RUNR,MSACT) $ mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OSYN"),1)..
      Sum(R_RAGG(RUNR,MSACT) $ mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OSYN"),
         v_Miti(RUNR,"cropMiti", gainsTechFert,"N2OSYN") + v_Miti(RUNR,"cropMiti", gainsTechFert,"N2OSYN2"))
    =L=  p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"N2OSYN","MaxShare");

   TotMitFertMan_(RUNR,gainsTechFert) $ sum(R_RAGG(RUNR,MSACT) $ mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OSYN"),1)..
      Sum(R_RAGG(RUNR,MSACT) $ mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OMAN"),
         v_Miti(RUNR,"cropMiti", gainsTechFert,"N2OMAN") + v_Miti(RUNR,"cropMiti", gainsTechFert,"N2OMAN2"))
    =L=  p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"N2OMAN","MaxShare");

   (supply/set_miti_bounds.gms l. 30-34)
        v_Miti.up(%REGIONS%,PACT,allMitiTech,mitiTarget)
         $ sum( (R_RAGG(%REGIONS%,NUTS0),mitiTech_map(NUTS0,PACT,allMitiTech,mitiTarget))  $ (not sameas(allMitiTech,"NOC")),1)
         = sum( (R_RAGG(%REGIONS%,NUTS0),mitiTech_map(NUTS0,PACT,allMitiTech,mitiTarget)),
                    p_ghgMiti(%REGIONS%,PACT,allMitiTech,mitiTarget,"MaxShare")
                  + p_ghgMiti(NUTS0,PACT,allMitiTech,mitiTarget,"MaxShare") $ (NOT p_ghgMiti(%REGIONS%,PACT,allMitiTech,mitiTarget,"MaxShare")));

Written so far: the manure options' part (K183): the fertiliser options aimed at applied manure (mitiTarget in
targFertMan: the nitrification inhibitor on manure, NITR_INH with target N2OMAN); and the mineral fertiliser options'
base (targFertSyn: the purchases, K175), on which the regional NLP's fertilisation block charges their cost.

"""
from __future__ import annotations


def GHG_Mit_Cost_targFertMan(v_ManureNPK_tail, v_Miti, costPar_lin, costPar_sqr, NMAN, EmiCalMan=0.0):
    """The manure options' part of GHG_Mit_Cost_(r) (l. 4984-5116, the targFertMan base l. 5070-5075), kEUR (the
    regional objective's unit).

    CAPRI's GAMS, GHG_Mit_Cost_ (the standard version, l. 4984-5116; the parts per share and the targFertMan base,
    l. 5070-5075; the other bases left out here):

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

    Other sources: l. 976-1036 (InclEmiAppl_), l. 927-947 and 954-970 (ManureNPK_, manExportOrAppl_); EmiCalMan: envind/ghgMiti.gms
    l. 942-959.

    In this project's notation (per region r, summed over the options o with a targFertMan target):

        cost_r = sum_o [ c1_o s_o + 0.5 c2_o s_o^2 ] x ManureNPK_r x (1 + incEmiAppl_r) x (1 + sum_o (NMAN_o + EmiCalMan_o) s_o)

    s_o = v_Miti(r, cropMiti, o, N2OMAN); c1, c2 = costParLin + pmpParLin - subsidy and costParSqr + pmpParSqr (CAPRI's
    accounting and calibrated parts, per t of manure N); (1 + incEmiAppl_r) = the manure N at the tail (excreted less the
    housing and storage losses and the housing runoff) over the manure N net of all gaseous losses (InclEmiAppl_), so
    ManureNPK x (1 + incEmiAppl) is the manure N at the tail, net of the trade. EmiCalMan = 0: CAPRI computes it inside
    $ontext/$offtext (ghgMiti.gms l. 942-959).

    Departure: the manure trade enters at the tail (CAPRI scales ManureNPK, net of the trade, by the region's own tail
    factor); equal where the traded manure has the region's own loss ratio. One option (CAPRI's only targFertMan option in
    the Green Deal group is NITR_INH).

    Arguments: v_ManureNPK_tail = the fertilisation block's manure N pool, fertDistExcr_'s right-hand side (the animals'
    manure N applied, excreted less the housing and storage losses and the housing runoff, with the N the ammonia
    options keep and the manure trade), t; v_Miti the option's share; costPar_lin, costPar_sqr the calibrated terms per
    t of manure N (EUR); NMAN the option's othImpact NMAN (after CAPRI's restMitFert)."""
    return (v_ManureNPK_tail / 1000.0) * (1 + (NMAN + EmiCalMan) * v_Miti) \
        * (costPar_lin * v_Miti + 0.5 * costPar_sqr * v_Miti * v_Miti)


def GHG_Mit_Cost_targFertSyn(v_netPutQuant, inv_1000, cost_base):
    """The mineral fertiliser options' part of GHG_Mit_Cost_(r) (l. 4984-5116, the targFertSyn base l. 5064-5069),
    kEUR: P / 1000 x cost_base, P the N purchases (t), cost_base = sum_o [c1_o s_o + 0.5 c2_o s_o^2] x (1 + sum_o
    (NMIN_o + EmiCalMin_o) s_o) (CapriRegionalNLP._abatement_block, K175).

    The targFertSyn base (l. 5064-5069), the mineral N purchases scaled by the options' effect on the N need met:

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

    GHG_Mit_Cost_'s parts per share (CAPRI's GAMS): GHG_Mit_Cost_targFertMan's docstring.
    """
    return v_netPutQuant * inv_1000 * cost_base


def TotMit_(v_Miti):
    r"""TotMit_(r, PACT, mitiTarget) (l. 4116-4124) with the option "no control" (NOC) eliminated: the options' shares of
    one group sum to at most 1 (CAPRI: with NOC's share, to exactly 1; NOC = 1 - the sum >= 0). v_Miti: the group's
    shares; the row <= 1.

    CAPRI's GAMS, TotMit_ (l. 4116-4124):

        TotMit_(RUNR,PACT,mitiTarget) $ sum((R_RAGG(RUNR,MSACT),mitiTech_map(MSACT,PACT,AllMitiTech,mitiTarget)),1)..
           sum((R_RAGG(RUNR,MSACT),mitiTech_map(MSACT,PACT,AllMitiTech,mitiTarget))
                                                         $ ((not sum(SupplTechTot,sameas(SupplTechTot,AllMitiTech)))
                                                         and (not sum(buffabov1,sameas(buffabov1,AllMitiTech)))),
            v_Miti(RUNR,PACT,AllMitiTech,mitiTarget))
        =e= 1;
    """
    return sum(v_Miti)


def GHG_Mit_Cost_herd(stock_w, v_actLevl, c1, c2_half, d):
    r"""GHG_Mit_Cost_ of the ammonia options, charged on the herd (l. 5035-5044: v_actLevl x p_animProdDays / 365, the
    animal stock), per option: stock_w x v_actLevl x (c1 d + c2_half d^2), with d = s - s0 the share's change from its
    base (initial) share. stock_w: the places per unit of the activity x the sub-activity's weight; c1, c2_half: the
    calibrated cost terms at the base share (supply.ammonia_techs). Vectors over the options (the builder sums).

    CAPRI's GAMS, GHG_Mit_Cost_'s herd base (l. 5035-5044; the parts per share: GHG_Mit_Cost_targFertMan's docstring):

            * [   sum(A $ (p_technFact(RUNR,PACT,"LEVL",A) $ AACT(PACT)),
                  v_actLevl(RUNR,PACT,A)
                  * ( (p_animProdDays(RUNR,PACT,"T")/365)                  $ (not SupplTech(allMitiTech))
                    + (p_animReq(RUNR,PACT,"T","DRMA" %addtimedim%) * p_animProdDays(RUNR,PACT,"T") / 1000
                        * p_emisFeed(RUNR,PACT,"T",allMitiTech,"ShrOfDM")) $ ( (sameas(allMitiTech,"Line_Tot") or sameas(allMitiTech,"Nitr_Tot") or sameas(allMitiTech,"3NOP_Tot"))
                                                                             $ catact(PACT)
                                                                             $ mitiTech_map(MSACT,PACT,allMitiTech,"CH4ENT")))
                     )

    Departure in form: the cost is written around the base shares s0, c1 (s - s0) + 0.5 c2 (s - s0)^2, which is CAPRI's
    c1' s + 0.5 c2 s^2 with c1' = c1 - c2 s0 up to a constant.
    """
    return stock_w * v_actLevl * (c1 * d + c2_half * d * d)


def Tot_MitFert_(NMIN, v_Miti):
    r"""Tot_MitFert_(r) (l. 4138-4145): the fertiliser options' N saving, sum_o v_Miti(o) x NMIN(o), the left-hand side
    less 1 (the row <= max(v_cropNutNeedMultFact + p_OverFertMarkUp, 1) - 1, the spec's "ecap"). The same sum is
    NUTNED_'s mineral N factor's term (1 + sum v_Miti NMIN; nutrients.py NUTNED_availFact). NMIN, v_Miti: per option,
    in the options' order.

    CAPRI's GAMS, Tot_MitFert_ (l. 4138-4145):

       Tot_MitFert_(RUNR) $ (sum((R_RAGG(RUNR,MSACT),gainsTechFert,mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OSYN")),1))..
          Sum((gainsTechFert, R_RAGG(RUNR,MSACT)) $ mitiTech_map(MSACT,"cropMiti",gainsTechFert,"N2OSYN"),
             v_Miti(RUNR,"cropMiti", gainsTechFert,"N2OSYN")
          * ( p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMIN")
            + p_ghgMiti(MSACT,"cropMiti",gainsTechFert,"othImpact","NMIN")
            $ (not p_ghgMiti(RUNR,"cropMiti",gainsTechFert,"othImpact","NMIN")))) + 1
        =L= max(v_cropNutNeedMultFact.l(RUNR,"NITF","T") + p_OverFertMarkUp,1);
    """
    eff = 0
    for nm, s in zip(NMIN, v_Miti):
        eff = eff + nm * s
    return eff


def GHG_Mit_Cost_perShare(c1, c2_half, v_Miti):
    """GHG_Mit_Cost_'s cost per unit of the base, summed over options charged on one base (l. 4984-5116): sum_o
    c1_o s_o + 0.5 c2_o s_o^2 (c1 = costParLin + pmpParLin - subsidy, c2_half = 0.5 (costParSqr + pmpParSqr)); in the
    options' order.

    CAPRI's GAMS of the parts per share: GHG_Mit_Cost_targFertMan's docstring.
    """
    cost = 0
    for a, b, s in zip(c1, c2_half, v_Miti):
        cost = cost + (a * s + b * s * s)
    return cost


def GHG_Mit_Cost_targFertSyn_factor(NMIN_EmiCalMin, v_Miti):
    """The targFertSyn base's factor less 1 (l. 5064-5069): sum_o (NMIN_o + EmiCalMin_o) v_Miti_o, in the options'
    order.

    CAPRI's GAMS: GHG_Mit_Cost_targFertSyn's docstring.
    """
    f = 0
    for e, s in zip(NMIN_EmiCalMin, v_Miti):
        f = f + e * s
    return f


def GHG_Mit_Cost_targFertSyn_base(cost_perShare, factor):
    """The mineral fertiliser options' cost per t of N purchased (l. 5064-5069): the options' cost per share x (1 + the
    factor); the purchases multiply it in GHG_Mit_Cost_targFertSyn (the fertilisation block)."""
    return cost_perShare * (1 + factor)


def GHG_Mit_Cost_targFertMan_excr(W, c1, c2_half, v_Miti):
    """The inhibitor on manure's cost where the regional NLP has no N fertilisation block: on the excreted manure N W
    (kt), W x (c1 s + c2_half s^2). DEPARTURE from CAPRI's targFertMan base (ManureNPK x (1 + incEmiAppl) x (1 + NMAN s),
    GHG_Mit_Cost_targFertMan), which needs the block's manure N pool."""
    return W * (c1 * v_Miti + c2_half * v_Miti * v_Miti)


def GHG_Mit_Cost_catc(uaaEqu, c1, c2_half, v_Miti):
    r"""GHG_Mit_Cost_ of winter cover (the catch crops), charged on the UAA (l. 5053-5056): U x (c1 m + c2_half m^2),
    kEUR; c1 = costParLin + pmpParLin (+ the calibration's linear term), c2_half = 0.5 pmpParSqr. U is the base UAA
    where CAPRI's v_actLevl(uaaEqu) is a variable (K186: premiums.py).

    CAPRI's GAMS, GHG_Mit_Cost_'s UAA base (l. 5053-5056; the parts per share: GHG_Mit_Cost_targFertMan's docstring):

                + v_actLevl(RUNR,"uaaEqu","T") $ (    sameas(PACT,"CATC")
                                                  or (sameas(PACT,"uaarmiti") and sum(mitiTechNLim $ sameas(allMitiTech,mitiTechNLim),1))
                                                  or (sameas(PACT,"cropMiti") and sum(mitiTechBuff $ sameas(allMitiTech,mitiTechBuff),1))
                                                  or (sameas(PACT,"cropMiti") and sum(mitiTechBiod $ sameas(allMitiTech,mitiTechBiod),1)))
    """
    return uaaEqu * (c1 * v_Miti + c2_half * v_Miti * v_Miti)

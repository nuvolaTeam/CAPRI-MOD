r"""CAPRI's simulation year's report (reports/sol_simy.gms, star 3.0): the land owners' profit, the solution's feed
per head, the mitigation options' accounting cost per activity and the region's activity-based income (income I1).

capri_mod/coupling/reporting.py (ReportingBlock._welfare_supply) calls the land owners' profit; the methane chain
(tools/lib/methane_inputs.py) the feed per head; capri_mod/income (mitigation_items.py, income_module.py
income_parts) the mitigation report and the region's income.
"""
from __future__ import annotations


def DATA_ProfitLandUse(d_area, d_area_lo, area):
    r"""DATA(RU, "ProfitLandUse", "LAND", SIMY): the land rents, each land type's area x its rent at the solution, the
    dual of its land row less that of its lower bound (sequences over the land types in the same order; EUR/ha x 1000
    ha = EUR 1000).

    CAPRI's GAMS (reports/sol_simy.gms l. 181-190):

           DATA(RU,"ProfitLandUse","LAND","%SIMY%")      = DATA(RU,"UAAR","levl","%SIMY%")*DATA(RU,"UAAR","d_area","Y")*0.001;
        *                                                   hypothetical rent if ASYM were completely used for non-ag:
        *                                                   Note: valuing ASYM with the agric rent x fac should give total ProfitLandUse>0
           DATA(RU,"ProfitLandUse","INPE","%SIMY%")      = (DATA(RU,"asym","levl","y")*DATA(RU,"UAAR","d_area","Y")  *20
        *                                                   opportunity cost as part of ASYM was not used for non-ag but for UAAR:
                                                           - v_landSupCost.l(RU)) * 0.001
        *                                                   The previous calculation may still miss the transformation cost
        *                                                   between agricultural land types, see branch f2f, r9566:
        *                                                  - v_pmpCostLandMarket.l(ru)) * 0.001
                                                         ;

    In this project's notation: RENT = sum_t (d_t - d_t^lo) A_t over ARAC, GRAS, FRUN. Departures from CAPRI: per
    land type with its own dual (CAPRI's UAAR x one d_area); the non-agricultural part (INPE, l. 184-190) not
    computed; the caller's units (EUR 1000, CAPRI's million EUR x 0.001)."""
    return sum((d - lo) * a for d, lo, a in zip(d_area, d_area_lo, area))


def DATA_FEED_SIMY(v_feedInpCoeff_A, v_actLevl_A, LEVL):
    r"""DATA(RU, MAACT, FEED, SIMY) of an activity with a level: the feed per head of the solution, the technologies'
    feed input coefficients weighted by their levels over the activity's level (kg per head). The report's
    digestibility and gases (l. 1627 on) take their rations from here.

    CAPRI's GAMS (reports/sol_simy.gms l. 254-257):

        *
           DATA(RU,MAACT,FEED,"%SIMY%") $ DATA(RU,MAACT,"LEVL","%SIMY%")
                    = SUM(A $ p_maxFeedShare(RU,MAACT,A,FEED), v_feedInpCoeff.L(RU,MAACT,A,FEED)*v_actLevl.L(RU,MAACT,A))
                              / DATA(RU,MAACT,"LEVL","%SIMY%");

    v_feedInpCoeff_A, v_actLevl_A: {A: value} of the technologies with a p_maxFeedShare for the feed (the caller
    applies that condition and DATA's LEVL one). Departures from CAPRI: none."""
    return sum(float(v_feedInpCoeff_A.get(t, 0.0) or 0.0) * float(lv or 0.0) for t, lv in v_actLevl_A.items()) / LEVL


def p_ghgMiti_emisAll_cost(terms, scale):
    r"""p_ghgMiti(RU, PACT, allMitiTech, "emisAll", "cost") of an option other than NOC: its accounting cost per unit of
    the activity at the solution, summed over the option's targets (EUR per ha or per head), which the report books as
    the input mitiI (l. 1459-1461) and the income's TOIN counts.

    CAPRI's GAMS (reports/sol_simy.gms l. 1049-1072):

        *  for animal activities and rice the costs follow from the cost function used in the supply model using the optimal implementation shares
        *  NOTE: We use PACT, not MPACT to assign cropMiti and grasMiti in two steps, here the total ,and subsequently disaggreegated to crops
           p_ghgMiti(RU,PACT,allMitiTech,"emisAll","cost") $ ((not sameas(allMitiTech,"NOC")))
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,PACT,allMitiTech,mitiTarget)),
                           [ (  p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"costParLin")
                              + p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"costParLin")
                             $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"costParLin"))) * v_miti.l(RU,PACT,allMitiTech,mitiTarget)
        *                   special factor for option GENET_REP which is expressed relative to the young cow price, see envind\breeding.gms
                           * (  1                      $ (NOT SAMEAS(allMitiTech,"Genet_rep"))
                             +  p_uvagScen(MS,"YCOW")  $      SAMEAS(allMitiTech,"Genet_rep") )
                           + (  p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"costParSqr")
                             +  p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"costParSqr")
                             $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"costParSqr")))*.5*v_miti.l(RU,PACT,allMitiTech,mitiTarget)**2]
        *                   scaling factors where costs are not yet expressed per activity level
                         * [ (  (DATA(RU,PACT,"DAYS","%SIMY%")/365)               $ (not SupplTech(allMitiTech))
        *                 Dry Matter consumption times Fat share of Dry matter = Fat consumption
                              + (  p_animReq(RU,PACT,"T","DRMA") * p_animProdDays(RU,PACT,"T") / 1000
                                 * p_emisFeed(RU,PACT,"T",allMitiTech,"ShrOfDM")) $ (  SupplTechTot(allMitiTech)
                                                                                      $ mitiTech_map(MS,PACT,allMitiTech,"CH4ENT"))
                              )  $      AACT(PACT)

                            + 1  $ (not AACT(PACT)) ]
                             );
           option kill = p_uvagScen;

    terms: per target of the option (mitiTech_map), (costParLin of RU, costParLin of its member state, costParSqr of
    RU, costParSqr of its member state, v_miti.l, the factor: 1, or p_uvagScen(MS, YCOW) for Genet_rep); scale: the
    bracket's scaling of the activity (p_ghgMiti_emisAll_cost_scale). The member state's parameter applies where the
    region has none (GAMS's "$ (NOT ...)"). Departures from CAPRI: none."""
    total = 0.0
    for lin_r, lin_ms, sqr_r, sqr_ms, v, fac in terms:
        lin = float(lin_r) if lin_r else float(lin_ms or 0.0)
        sqr = float(sqr_r) if sqr_r else float(sqr_ms or 0.0)
        total += lin * float(v) * float(fac) + sqr * 0.5 * float(v) ** 2
    return total * float(scale)


def p_ghgMiti_emisAll_cost_scale(AACT, SupplTech, SupplTechTot_CH4ENT, DAYS=0.0, DRMA=0.0, prodDays=0.0, ShrOfDM=0.0):
    r"""The scaling of p_ghgMiti_emisAll_cost (l. 1063-1071 of the statement quoted there): for an animal activity
    (AACT) its days over 365, or for a supplement option counted against enteric CH4 (SupplTechTot with a CH4ENT
    target) the fat fed per head, DRMA x the production days / 1000 x the option's share of dry matter; 1 for the other
    activities. An animal's supplement option outside that case scales to 0, as in CAPRI's sum of the two conditioned
    terms. Departures from CAPRI: none."""
    if not AACT:
        return 1.0
    return (float(DAYS) / 365.0 if not SupplTech else 0.0) + \
        (float(DRMA) * float(prodDays) / 1000.0 * float(ShrOfDM) if SupplTechTot_CH4ENT else 0.0)


def _lin_sqr(lin_r, lin_ms, sqr_r, sqr_ms, v):
    """costParLin v + costParSqr 0.5 v^2 with the member state's parameter where the region has none (GAMS's
    "$ (NOT ...)" in the statements of this module)."""
    lin = float(lin_r) if lin_r else float(lin_ms or 0.0)
    sqr = float(sqr_r) if sqr_r else float(sqr_ms or 0.0)
    return lin * float(v) + sqr * 0.5 * float(v) ** 2


def p_ghgMiti_emisAll_cost_GainsTechFert(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact):
    r"""p_ghgMiti(RU, MCACT, GainsTechFert, "emisAll", "cost") of a crop with a level: the fertiliser option's cost per
    ha, its cost per t of mineral N times the crop's mineral N, and per t of manure N times its manure N, each on the
    application before the options (EUR/ha).

    CAPRI's GAMS (reports/sol_simy.gms l. 1094-1126):


        *
        *  for crop activities the mitigation costs related to mineral fertiliser will be distributed according to the estimated distribution
           p_ghgMiti(RU,MCACT,GainsTechFert,"emisAll","cost") $ DATA(RU,MCACT,"LEVL","%SIMY%")
        *             cost per ton of mineral feriliser use
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertSyn)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"costParLin")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"costParLin")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"costParLin"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)
                           + (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"costParSqr")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"costParSqr")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"costParSqr")))*.5*v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)**2])
        *             mineral fertiliser is given in kg/ha=>
                    * DATA(RU,MCACT,"NMIN","%SIMY%")/1000
        *             costs are calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMIN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OSYN")))
        *             cost per ton of manure use
                    + sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertMan)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"costParLin")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"costParLin")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"costParLin"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)
                           + (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"costParSqr")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"costParSqr")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"costParSqr")))*.5*v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)**2])
        *             manure is given in kg/head=>
                    * DATA(RU,MCACT,"NMAN","%SIMY%")/1000
        *             costs are calculated on the basis of ex-ante (without mitigation technologies) manure application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMAN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OMAN")));


    syn_terms, man_terms: per target of targFertSyn, targFertMan (lin_r, lin_ms, sqr_r, sqr_ms, v_miti.l);
    syn_othImpact, man_othImpact: per option of gainsTechFert1 (othImpact of RU, of its member state, v_Miti.l on N2OSYN,
    N2OMAN); NMIN, NMAN in kg/ha. Departures from CAPRI: none."""
    syn = sum(_lin_sqr(*t) for t in syn_terms) * float(NMIN) / 1000.0 * \
        (1.0 + sum((float(o_r) if o_r else float(o_ms or 0.0)) * float(v) for o_r, o_ms, v in syn_othImpact))
    man = sum(_lin_sqr(*t) for t in man_terms) * float(NMAN) / 1000.0 * \
        (1.0 + sum((float(o_r) if o_r else float(o_ms or 0.0)) * float(v) for o_r, o_ms, v in man_othImpact))
    return syn + man


def p_ghgMiti_emisAll_cost_UreaSubst(terms):
    r"""p_ghgMiti(RU, MCACT, "UreaSubst", "emisAll", "cost") of a crop with a level: the urea substitution's cost, the
    region's parameters at the share of cropMiti (EUR per unit of the crop).

    CAPRI's GAMS (reports/sol_simy.gms l. 1129-1132):

           p_ghgMiti(RU,MCACT,"UreaSubst","emisAll","cost") $ DATA(RU,MCACT,"LEVL","%SIMY%")
                    = sum(mitiTech_map(RU,MCACT,"UreaSubst",mitiTarget),
                       p_ghgMiti(RU,"cropMiti","UreaSubst",mitiTarget,"costParLin") * v_miti.l(RU,"cropMiti","UreaSubst",mitiTarget)
                     + p_ghgMiti(RU,"cropMiti","UreaSubst",mitiTarget,"costParSqr") *.5 * v_miti.l(RU,"cropMiti","UreaSubst",mitiTarget)**2);

    terms: per target of the crop's mitiTech_map (costParLin, costParSqr, v_miti.l of cropMiti). Departures from CAPRI:
    none."""
    return sum(float(lin) * float(v) + float(sqr) * 0.5 * float(v) ** 2 for lin, sqr, v in terms)


def p_ghgMiti_emisAll_cost_till(cost_cropMiti, LEVL, Tillset):
    r"""p_ghgMiti(RU, MCACT, mitiTechTill, "emisAll", "cost") of a crop with a level and a tillage set: cropMiti's cost
    of the tillage option (p_ghgMiti_emisAll_cost with PACT cropMiti), else none (0).

    CAPRI's GAMS (reports/sol_simy.gms l. 1134-1135):

           p_ghgMiti(RU,MCACT,mitiTechTill,"emisAll","cost") $ (DATA(RU,MCACT,"LEVL","%SIMY%") and DATA(RU,MCACT,"Tillset","Y"))
                    = p_ghgMiti(RU,"cropMiti",mitiTechTill,"emisAll","cost");

    Departures from CAPRI: none."""
    return float(cost_cropMiti) if (LEVL and Tillset) else 0.0


def p_ghgMiti_emisAll_cost_catc(cost_uaar, v_miti):
    r"""p_ghgMiti(RU, "catc", "WinterCov", "emisAll", "cost"): the winter cover's cost per ha of CATC, its cost per ha
    of UAAR over the share v_miti (CATC's level is v_miti x UAAR's), 0 below a share of 1e-8.

    CAPRI's GAMS (reports/sol_simy.gms l. 1146-1153):

        *  for winter cover crops the cost would have to be multiplied with the uaar (not the levl of catc).
        *  The following holds: levl(catc) = v_miti * levl(uaar)
        *  In order to treat the measure like the others (total cost = cost per levl * levl) we have to divide the cost per UAAR by v_miti.
        *  totalCost(catc) = costPerLevl(UAAR)*levl(UAAR) = costPerlevl(UAAR)/v_miti(catc)*v_miti(catc)*levl(UAAR)
        *                                                 =      costPerlevl(catc)        *    levl(catc)
           p_ghgMiti(RU,"catc","WinterCov","emisAll","cost")
                     = (p_ghgMiti(RU,"catc","WinterCov","emisAll","cost") / v_miti.l(RU,"catc","WinterCov","co2seq"))
                     $ (v_miti.l(RU,"catc","WinterCov","co2seq") gt 1.e-8);

    Departures from CAPRI: none."""
    return float(cost_uaar) / float(v_miti) if float(v_miti) > 1e-8 else 0.0


def p_ghgMiti_emisAll_cost_idlHis(cost_orgSoil, v_miti):
    r"""p_ghgMiti(RU, idlHisAct, "Fallow", "emisAll", "cost"): the histosols' fallowing cost per ha of the idled
    histosol activity, its cost per ha of organic soil over the share v_miti, 0 below a share of 1e-8.

    CAPRI's GAMS (reports/sol_simy.gms l. 1155-1164):

        *
        *  Same for histosol protection: the cost would have to be multiplied with the organic soil area (not the levl of IHISCR/IHISGR).
        *  The following holds: levl(idlHisAct) = v_miti(idlHisAct) * orgSoilArea(idlHisAct)
        *  In order to treat the measure like the others (total cost = cost per levl*levl) we have to divide the cost per orgSoilArea by v_miti:
        *  totalCost(idlHisAct) = costPerLevl(orgSOilArea)                                    *orgSoilArea(idlHisAct)
        *                       = costPerLevl(orgSOilArea)/v_miti(idlHisAct)*v_miti(idlHisAct)*orgSoilArea(idlHisAct)
        *                       = costPerLevl(idlHisAct)                    *levl(idlHisAct)
           p_ghgMiti(RU,idlHisAct,"Fallow","emisAll","cost")
                     = (p_ghgMiti(RU,idlHisAct,"Fallow","emisAll","cost") / v_miti.l(RU,idlHisAct,"Fallow","n2ohis"))
                     $ (v_miti.l(RU,idlHisAct,"Fallow","n2ohis") gt 1.e-8);

    Departures from CAPRI: none."""
    return float(cost_orgSoil) / float(v_miti) if float(v_miti) > 1e-8 else 0.0


def _lin(par_r, par_ms, v):
    """The parameter x v_miti, the member state's parameter where the region has none (GAMS's "$ (NOT ...)")."""
    return (float(par_r) if par_r else float(par_ms or 0.0)) * float(v)


def _fert_lin(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact):
    """The fertiliser options' revenue or subsidy per ha: per t of mineral and of manure N on the application before
    the options, as their cost (p_ghgMiti_emisAll_cost_GainsTechFert) without the quadratic term."""
    syn = sum(_lin(*t) for t in syn_terms) * float(NMIN) / 1000.0 * \
        (1.0 + sum((float(o_r) if o_r else float(o_ms or 0.0)) * float(v) for o_r, o_ms, v in syn_othImpact))
    man = sum(_lin(*t) for t in man_terms) * float(NMAN) / 1000.0 * \
        (1.0 + sum((float(o_r) if o_r else float(o_ms or 0.0)) * float(v) for o_r, o_ms, v in man_othImpact))
    return syn + man


def p_ghgMiti_emisAll_revenue(terms, scale):
    r"""p_ghgMiti(RU, PACT, allMitiTech, "emisAll", "revenue") of an option other than NOC: its revenue per unit of the
    activity at the solution, which the report books as the output mitiO (l. 1464-1465) and the income's TOOU counts.

    CAPRI's GAMS (reports/sol_simy.gms l. 1169-1183):

           p_ghgMiti(RU,PACT,allMitiTech,"emisAll","revenue") $ ((not sameas(allMitiTech,"NOC")))
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,PACT,allMitiTech,mitiTarget)),
                           [ (  p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"revenue")
                             +  p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"revenue")
                             $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"revenue"))) * v_miti.l(RU,PACT,allMitiTech,mitiTarget)]
        *                   scaling factors where costs are not yet expressed per activity level
                         * [  (  (DATA(RU,PACT,"DAYS","%SIMY%")/365)               $ (not SupplTech(allMitiTech))
        *                 Dry Matter consumption times Fat share of Dry matter = Fat consumption
                              + (  p_animReq(RU,PACT,"T","DRMA") * p_animProdDays(RU,PACT,"T") / 1000
                                 * p_emisFeed(RU,PACT,"T",allMitiTech,"ShrOfDM")) $ (  SupplTechTot(allMitiTech)
                                                                                      $ mitiTech_map(MS,PACT,allMitiTech,"CH4ENT"))
                              )  $      AACT(PACT)

                            + 1  $ (not AACT(PACT))]
                             );

    terms: per target (revenue of RU, of its member state, v_miti.l); scale: p_ghgMiti_emisAll_cost_scale. Departures
    from CAPRI: none."""
    return sum(_lin(*t) for t in terms) * float(scale)


def p_ghgMiti_emisAll_revenue_GainsTechFert(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact):
    r"""p_ghgMiti(RU, MCACT, GainsTechFert, "emisAll", "revenue") of a crop with a level (EUR/ha).

    CAPRI's GAMS (reports/sol_simy.gms l. 1185-1208):

        *  for crop activities the revenues are distributed justs as the observed components
           p_ghgMiti(RU,MCACT,GainsTechFert,"emisAll","revenue") $ DATA(RU,MCACT,"LEVL","%SIMY%")
        *             revenue per ton of mineral feriliser use
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertSyn)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"revenue")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"revenue")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"revenue"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)])
        *             mineral fertiliser is given in kg/ha=>
                    * DATA(RU,MCACT,"NMIN","%SIMY%")/1000
        *             revenue is calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMIN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OSYN")))
        *             revenue per ton of manure use
                    + sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertMan)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"revenue")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"revenue")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"revenue"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)])
        *             manure is given in kg/head=>
                    * DATA(RU,MCACT,"NMAN","%SIMY%")/1000
        *             revenue is calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMAN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OMAN")));

    The arguments as p_ghgMiti_emisAll_cost_GainsTechFert's, each term (revenue of RU, of its member state,
    v_miti.l). Departures from CAPRI: none."""
    return _fert_lin(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact)


def p_ghgMiti_emisAll_subsidy(terms, scale):
    r"""p_ghgMiti(RU, PACT, allMitiTech, "emisAll", "subsidy") of an option other than NOC: its subsidy per unit of the
    activity at the solution, which the report adds to the premiums (mitiSubs, l. 1429-1434).

    CAPRI's GAMS (reports/sol_simy.gms l. 1327-1341):

           p_ghgMiti(RU,PACT,allMitiTech,"emisAll","subsidy") $ ((not sameas(allMitiTech,"NOC")))
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,PACT,allMitiTech,mitiTarget)),
                           [ (  p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"subsidy")
                             +  p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"subsidy")
                             $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"subsidy"))) * v_miti.l(RU,PACT,allMitiTech,mitiTarget)]
        *                   scaling factors where costs are not yet expressed per activity level
                         * [ (  (DATA(RU,PACT,"DAYS","%SIMY%")/365)               $ (not SupplTech(allMitiTech))
        *                 Dry Matter consumption times Fat share of Dry matter = Fat consumption
                              + (  p_animReq(RU,PACT,"T","DRMA") * p_animProdDays(RU,PACT,"T") / 1000
                                 * p_emisFeed(RU,PACT,"T",allMitiTech,"ShrOfDM")) $ (  SupplTechTot(allMitiTech)
                                                                                      $ mitiTech_map(MS,PACT,allMitiTech,"CH4ENT"))
                              )  $      AACT(PACT)

                            + 1  $ (not AACT(PACT)) ]
                             );

    terms: per target (subsidy of RU, of its member state, v_miti.l); scale: p_ghgMiti_emisAll_cost_scale.
    Departures from CAPRI: none."""
    return sum(_lin(*t) for t in terms) * float(scale)


def p_ghgMiti_emisAll_subsidy_GainsTechFert(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact):
    r"""p_ghgMiti(RU, MCACT, GainsTechFert, "emisAll", "subsidy") of a crop with a level (EUR/ha).

    CAPRI's GAMS (reports/sol_simy.gms l. 1358-1381):

        *  for crop activities the subsidies related to mineral fertiliser will be distributed according to the estimated distribution
           p_ghgMiti(RU,MCACT,GainsTechFert,"emisAll","subsidy") $ DATA(RU,MCACT,"LEVL","%SIMY%")
        *             cost per ton of mineral feriliser use
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertSyn)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"subsidy")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"subsidy")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"subsidy"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)])
        *             mineral fertiliser is given in kg/ha=>
                    * DATA(RU,MCACT,"NMIN","%SIMY%")/1000
        *             costs are calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMIN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OSYN")))
        *             subsidy per ton of manure use
                    + sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertMan)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"subsidy")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"subsidy")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"subsidy"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)])
        *             manure is given in kg/head=>
                    * DATA(RU,MCACT,"NMAN","%SIMY%")/1000
        *             subsidies are calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMAN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OMAN")));

    The arguments as p_ghgMiti_emisAll_cost_GainsTechFert's, each term (subsidy of RU, of its member state,
    v_miti.l). Departures from CAPRI: none."""
    return _fert_lin(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact)


def p_ghgMiti_emisAll_subsidy_UreaSubst(terms):
    r"""p_ghgMiti(RU, MCACT, "UreaSubst", "emisAll", "subsidy") of a crop with a level: the region's subsidy at the
    share of cropMiti.

    CAPRI's GAMS (reports/sol_simy.gms l. 1385-1387):

           p_ghgMiti(RU,MCACT,"UreaSubst","emisAll","subsidy") $ DATA(RU,MCACT,"LEVL","%SIMY%")
                    = sum(mitiTech_map(RU,MCACT,"UreaSubst",mitiTarget),
                       p_ghgMiti(RU,"cropMiti","UreaSubst",mitiTarget,"subsidy") * v_miti.l(RU,"cropMiti","UreaSubst",mitiTarget));

    terms: per target (subsidy, v_miti.l of cropMiti). Departures from CAPRI: none."""
    return sum(float(s) * float(v) for s, v in terms)


def p_ghgMiti_emisAll_subsidy_till(subsidy_cropMiti, LEVL, Tillset):
    r"""p_ghgMiti(RU, MCACT, mitiTechTill, "emisAll", "subsidy") of a crop with a level and a tillage set: cropMiti's.

    CAPRI's GAMS (reports/sol_simy.gms l. 1389-1390):

           p_ghgMiti(RU,MCACT,mitiTechTill,"emisAll","subsidy") $ (DATA(RU,MCACT,"LEVL","%SIMY%") and DATA(RU,MCACT,"Tillset","Y"))
                    = p_ghgMiti(RU,"cropMiti",mitiTechTill,"emisAll","subsidy");

    Departures from CAPRI: none."""
    return float(subsidy_cropMiti) if (LEVL and Tillset) else 0.0


def DATA_mitiSubs(subsidy_by_tech):
    r"""DATA(RU, PACT, "mitiSubs", SIMY): the options' subsidies of the activity, summed over the options (EUR per unit
    of the activity).

    CAPRI's GAMS (reports/sol_simy.gms l. 1429):

           data(RU,PACT,"mitiSubs","%SIMY%")   = sum(allMitiTech,p_ghgMiti(RU,PACT,allMitiTech,"emisAll","subsidy")) ;

    Departures from CAPRI: none."""
    return float(sum(float(v or 0.0) for v in subsidy_by_tech))


def DATA_PRME_mitiSubs(PRME, mitiSubs):
    r"""DATA(RU, PACT, "PRME", SIMY) with the options' subsidies added: the premiums the income's MGVA counts.

    CAPRI's GAMS (reports/sol_simy.gms l. 1433-1434):

           DATA(RU,PACT,"PRMEold","%SIMY%")    = DATA(RU,PACT,"PRME","%SIMY%")  ;
           DATA(RU,PACT,"PRME","%SIMY%")       = DATA(RU,PACT,"PRME","%SIMY%") + DATA(RU,PACT,"mitiSubs","%SIMY%") ;

    Departures from CAPRI: none."""
    return float(PRME) + float(mitiSubs)


def DATA_UVAG_mitiRepRowsQ(p_infl, Y, BAS):
    r"""DATA(MS, "UVAG", mitiRepRowsQ, SIMY): the price of the mitigation effort and of its secondary output, 1000 x the
    inflation since the base year, so that mitiI and mitiO are quantities in constant prices whose value at this price
    is the options' cost and revenue.

    CAPRI's GAMS (reports/sol_simy.gms l. 1449-1453):

        *
        *      --- from mitigation cost to mitigation quantity (a service measured in constant prices)
        *
        *          First define the price of mitigation efforts to be used for deflation
           DATA(MS,"UVAG",mitiRepRowsQ,"%SIMY%") = 1000* p_infl**(CALYEA("Y")-CALYEA("BAS"));

    Departures from CAPRI: none."""
    return 1000.0 * float(p_infl) ** (int(Y) - int(BAS))


def DATA_mitiI(PACT, cost_by_tech, UVAG_mitiI):
    r"""DATA(RU, PACT, "mitiI", SIMY): the options' cost of the activity as an input in constant prices; none for CATC,
    whose costs are in its inputs already (define_greening_limits.gms).

    CAPRI's GAMS (reports/sol_simy.gms l. 1455-1461):

        *          Deflate cost to obtain effort (=mitiI) in constant prices
        *          Note: We skip CATC in this assignment because these costs are assigned to DATA in disaggregate form already
        *                in capmod\define_greening_limits.gms (so SEED, REPM...). Hence they enter the EAA and income accounting
        *                already and must not be counted twice. So we skip CATC:
           DATA(RU,PACT,"mitiI","%SIMY%") $ (not sameas(PACT,"CATC"))
                                          = sum(allMitiTech,p_ghgMiti(RU,PACT,allMitiTech,"emisAll","cost"))
                                                / sum(R_RAGG(RU,MS),DATA(MS,"UVAG","mitiI","%SIMY%"))*1000 ;

    Departures from CAPRI: none."""
    if PACT == "CATC":
        return None
    return float(sum(float(v or 0.0) for v in cost_by_tech)) / float(UVAG_mitiI) * 1000.0


def DATA_mitiO(revenue_by_tech, UVAG_mitiO):
    r"""DATA(RU, PACT, "mitiO", SIMY): the options' revenue of the activity as a secondary output in constant prices.

    CAPRI's GAMS (reports/sol_simy.gms l. 1463-1465):

        *          ... and deflate revenue to obtain secondary output (=mitiO) in constant prices
           DATA(RU,PACT,"mitiO","%SIMY%") = sum(allMitiTech,p_ghgMiti(RU,PACT,allMitiTech,"emisAll","revenue"))
                                                / sum(R_RAGG(RU,MS),DATA(MS,"UVAG","mitiO","%SIMY%"))*1000;

    Departures from CAPRI: none."""
    return float(sum(float(v or 0.0) for v in revenue_by_tech)) / float(UVAG_mitiO) * 1000.0


def p_ghgMiti_emisAll_pmpcost(terms, scale):
    r"""p_ghgMiti(RU, PACT, allMitiTech, "emisAll", "pmpcost") of an option other than NOC: its unobserved (PMP) cost
    per unit of the activity at the solution, which the report keeps apart (mitiPmp, l. 1431), out of MGVA.

    CAPRI's GAMS (reports/sol_simy.gms l. 1210-1235):

        *
        *      --- unobserved mitigation cost (or pmp cost) per activity.
        *
        *  for animal activities and rice the costs follow from unobserved components in the supply model cost function
           p_ghgMiti(RU,PACT,allMitiTech,"emisAll","pmpcost") $ ((not sameas(allMitiTech,"NOC")))
                    =    sum((R_RAGG(RU,MS),mitiTech_map(MS,PACT,allMitiTech,mitiTarget)),
                              [.5
        *                        potentially we have regionalised parameters in case that option "lowNFeed" is active:
                              * ( p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"pmpParSqr")
                                +  p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"pmpParSqr")
                                $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"pmpParSqr")))
                              * sqr(v_miti.l(RU,PACT,allMitiTech,mitiTarget))
                              + ( p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"pmpParLin")
                                + p_ghgMiti(MS,PACT,allMitiTech,mitiTarget,"pmpParLin")
                                $ (NOT p_ghgMiti(RU,PACT,allMitiTech,mitiTarget,"pmpParLin")))
                              * v_miti.l(RU,PACT,allMitiTech,mitiTarget)]
        *                   scaling factors where costs are not yet expressed per activity level
                         * [ (  (DATA(RU,PACT,"DAYS","%SIMY%")/365)               $ (not SupplTech(allMitiTech))
        *                 Dry Matter consumption times Fat share of Dry matter = Fat consumption
                              + (  p_animReq(RU,PACT,"T","DRMA") * p_animProdDays(RU,PACT,"T") / 1000
                                 * p_emisFeed(RU,PACT,"T",allMitiTech,"ShrOfDM")) $ (  SupplTechTot(allMitiTech)
                                                                                      $ mitiTech_map(MS,PACT,allMitiTech,"CH4ENT"))
                              )  $      AACT(PACT)

                            + 1  $ (not AACT(PACT)) ]
                            );

    terms: per target (pmpParLin of RU, of its member state, pmpParSqr of RU, of its member state, v_miti.l); scale:
    p_ghgMiti_emisAll_cost_scale. Departures from CAPRI: none."""
    return sum(_lin_sqr(*t) for t in terms) * float(scale)


def p_ghgMiti_emisAll_pmpcost_GainsTechFert(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact):
    r"""p_ghgMiti(RU, MCACT, GainsTechFert, "emisAll", "pmpcost") of a crop with a level (EUR/ha): the form of
    p_ghgMiti_emisAll_cost_GainsTechFert on the PMP parameters.

    CAPRI's GAMS (reports/sol_simy.gms l. 1258-1287):

        *  for crop activities the mitigation costs related to mineral fertiliser will be distributed according to the estimated distribution
           p_ghgMiti(RU,MCACT,GainsTechFert,"emisAll","pmpcost") $ DATA(RU,MCACT,"LEVL","%SIMY%")
        *             cost per ton of mineral feriliser use
                    = sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertSyn)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"pmpParLin")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"pmpParLin")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"pmpParLin"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)
                           + (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"pmpParSqr")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertSyn,"pmpParSqr")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertSyn,"pmpParSqr")))*.5*v_miti.l(RU,"cropMiti",GainsTechFert,targFertSyn)**2])
        *             mineral fertiliser is given in kg/ha=>
                    * DATA(RU,MCACT,"NMIN","%SIMY%")/1000
        *             costs are calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMIN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMIN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OSYN")))
        *             cost per ton of manure use
                    + sum((R_RAGG(RU,MS),mitiTech_map(MS,"cropMiti",GainsTechFert,targFertMan)),
                           [ (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"pmpParLin")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"pmpParLin")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"pmpParLin"))) * v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)
                           + (  p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"pmpParSqr")
                             +  p_ghgMiti(MS,"cropMiti",GainsTechFert,targFertMan,"pmpParSqr")
                             $ (NOT p_ghgMiti(RU,"cropMiti",GainsTechFert,targFertMan,"pmpParSqr")))*.5*v_miti.l(RU,"cropMiti",GainsTechFert,targFertMan)**2])
        *             mineral fertiliser is given in kg/head=>
                    * DATA(RU,MCACT,"NMAN","%SIMY%")/1000
        *             costs are calculated on the basis of ex-ante (without mitigation technologies) mineral fertilizer application
                    * (1 + sum((gainsTechFert1,R_RAGG(RU,MS)), (p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")
                    + p_ghgMiti(MS,"cropMiti",gainsTechFert1,"othImpact","NMAN") $ (not p_ghgMiti(RU,"cropMiti",gainsTechFert1,"othImpact","NMAN")))
                    * v_Miti.l(RU,"cropmiti",gainsTechFert1,"N2OMAN")));

    Each term (pmpParLin of RU, of its member state, pmpParSqr of RU, of its member state, v_miti.l). Departures from
    CAPRI: none."""
    return p_ghgMiti_emisAll_cost_GainsTechFert(syn_terms, NMIN, syn_othImpact, man_terms, NMAN, man_othImpact)


def p_ghgMiti_emisAll_pmpcost_UreaSubst(terms):
    r"""p_ghgMiti(RU, MCACT, "UreaSubst", "emisAll", "pmpcost") of a crop with a level.

    CAPRI's GAMS (reports/sol_simy.gms l. 1291-1294):

           p_ghgMiti(RU,MCACT,"UreaSubst","emisAll","pmpcost") $ DATA(RU,MCACT,"LEVL","%SIMY%")
                    = sum(mitiTech_map(RU,MCACT,"UreaSubst",mitiTarget),
                       p_ghgMiti(RU,"cropMiti","UreaSubst",mitiTarget,"pmpParLin") * v_miti.l(RU,"cropMiti","UreaSubst",mitiTarget)
                     + p_ghgMiti(RU,"cropMiti","UreaSubst",mitiTarget,"pmpParSqr") *.5 * v_miti.l(RU,"cropMiti","UreaSubst",mitiTarget)**2);

    terms: per target (pmpParLin, pmpParSqr, v_miti.l of cropMiti). Departures from CAPRI: none."""
    return p_ghgMiti_emisAll_cost_UreaSubst(terms)


def p_ghgMiti_emisAll_pmpcost_till(pmpcost_cropMiti, LEVL, Tillset):
    r"""p_ghgMiti(RU, MCACT, mitiTechTill, "emisAll", "pmpcost") of a crop with a level and a tillage set: cropMiti's.

    CAPRI's GAMS (reports/sol_simy.gms l. 1296-1297):

           p_ghgMiti(RU,MCACT,mitiTechTill,"emisAll","pmpcost") $ (DATA(RU,MCACT,"LEVL","%SIMY%") and DATA(RU,MCACT,"Tillset","Y"))
                    = p_ghgMiti(RU,"cropMiti",mitiTechTill,"emisAll","pmpcost");

    Departures from CAPRI: none."""
    return float(pmpcost_cropMiti) if (LEVL and Tillset) else 0.0


def p_ghgMiti_emisAll_pmpcost_idlHis(pmpcost_orgSoil, v_miti):
    r"""p_ghgMiti(RU, idlHisAct, "fallow", "emisAll", "pmpCost"): per ha of the idled histosol activity, 0 below a share
    of 1e-8.

    CAPRI's GAMS (reports/sol_simy.gms l. 1308-1313):

        *  For histosol protection via ISET the above standard assignment needs modification, as pmp_cost is multiplied
        *  with "share(histosol)*CROP/GRAS" in supply_model, not with ISET.LEVL = v_miti(fallow)*share(histosol)*CROP/GRAS
        *  => We need to divide the earlier assignment by v_miti(fallow) to get the cost per ha of ISET/IHISGR:
           p_ghgMiti(RU,idlHisAct,"fallow","emisAll","pmpCost")
                    = (p_ghgMiti(RU,idlHisAct,"fallow","emisAll","pmpCost") / v_miti.l(RU,idlHisAct,"fallow","N2OHIS"))
                    $ (v_miti.l(RU,idlHisAct,"fallow","N2OHIS") gt 1.e-8);

    Departures from CAPRI: none."""
    return float(pmpcost_orgSoil) / float(v_miti) if float(v_miti) > 1e-8 else 0.0


def p_ghgMiti_emisAll_pmpcost_catc(pmpcost_uaar, v_miti):
    r"""p_ghgMiti(RU, "catc", "WinterCov", "emisAll", "pmpCost"): per ha of CATC where the share is not 0; unchanged
    where it is 0 (the statement's "$ v_miti" condition, unlike the cost's threshold of 1e-8).

    CAPRI's GAMS (reports/sol_simy.gms l. 1315-1319):

        *  for winter cover crops the cost would have to be multiplied with the uaar (not the levl of catc).
        *  The following holds: levl(catc) = v_miti * levl(uaar)
        *  In order to treat the measure like the others (multiplication with the levl of catc we have to divide the cost by v_miti.
           p_ghgMiti(RU,"catc","WinterCov","emisAll","pmpCost") $ v_miti.l(RU,"catc","WinterCov","co2seq")
                     = p_ghgMiti(RU,"catc","WinterCov","emisAll","pmpCost") / v_miti.l(RU,"catc","WinterCov","co2seq");

    Departures from CAPRI: none."""
    return float(pmpcost_uaar) / float(v_miti) if float(v_miti) else float(pmpcost_uaar)


def DATA_AGGT_MGVA(MGVA, LEVL, mitiI_RU=0.0, mitiO_RU=0.0):
    r"""DATA(RSS, "AGGT", "MGVA", SIMY): the region's activity-based income, sum over the activities of their MGVA x
    level (sequences in the same order; EUR per ha or head x 1000 ha or heads = EUR 1000).

    CAPRI's GAMS (reports/sol_simy.gms l. 2586-2587):

          DATA(RSS,"AGGT","MGVA","%SIMY%") = SUM(MPACT, DATA(RSS,MPACT,"MGVA","%SIMY%")*DATA(RSS,MPACT,"LEVL","%SIMY%"))/1000;
          DATA(RSS,"EAAG","MGVAbyAct","%SIMY%") = DATA(RSS,"AGGT","MGVA","%SIMY%");

    In this project's notation: AGGT = sum_a MGVA_a L_a - mitiI_RU + mitiO_RU. Departures from CAPRI: the units (EUR
    1000; CAPRI's / 1000 to million EUR); the mitigation options' cost and revenue (EUR 1000) added at the region, where
    CAPRI has them in the activities' MGVA (sol_simy.gms l. 1471-1473; calc_inc_indic.py DATA_MGVA); the technology
    mix's net revenue on the area moved to T1, which the model keeps apart from the activities' margins
    (supply/techn_mix.py), enters as further pairs (the margin's difference per ha, the area moved)."""
    return float(sum(float(m) * float(l_) for m, l_ in zip(MGVA, LEVL))) - float(mitiI_RU) + float(mitiO_RU)

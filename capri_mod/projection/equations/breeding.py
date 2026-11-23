r"""CAPRI's requirement functions of the dairy cow (envind/breeding.gms, star 3.0): the net energy apart from
lactation, maintenance (NEM), activity (NEA) and pregnancy (NEP), which the projection layer uses to scale the ration of
a cow whose milk yield is projected (ProjectionModule._project_livestock).

Departures from CAPRI: a fixed 600 kg cow (NEM the parameter REQ_NEM = 600^0.75 x 0.386 x 365,
capri_data/codes/model_parameters.csv; CAPRI p_meanLiveWgt per region and technology); NEA and NEP as shares of NEM.
"""
from __future__ import annotations


def p_animReqCopy_NEA_share(HD, Et):
    r"""p_animReqCopy(RU, DCOW, A, "NEA") over NEM: the activity's share of the maintenance energy, 0.17 (365 - HD)
    (1 - Et / 100) / 365, HD and Et the member state's housing days and the stable share of grazing time (MITERRA's
    p_rcEmissions, the items HD and Et of the dairy cows; 0 where CAPRI has no row).

    CAPRI's GAMS (envind/breeding.gms l. 190-192):

          p_animReqCopy(RU,DCOW,A,"NEA")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386)* 0.17
             * (365-p_rcEmissions(RU,"DAICOW_L","HD"))*(1-p_rcEmissions(RU,"DAICOW_L","Et")/100);

    In this project's notation: NEA / NEM = 0.17 (365 - HD)(1 - Et / 100) / 365, NEM = W^0.75 x 0.386 x 365 (l. 185-186).
    Departures from CAPRI: none (the share of NEM; the cow's weight in NEM)."""
    return 0.17 * (365.0 - HD) * (1.0 - Et / 100.0) / 365.0


def p_animReqCopy_ENNE_nonlact(NEM, NEA_share):
    r"""p_animReqCopy(RU, DCOW, A, "ENNE") less the lactation's NEL: NEM + NEP + NEA = NEM (1.1 + NEA / NEM), NEP = 0.10
    NEM, NEA = NEM x NEA_share (p_animReqCopy_NEA_share).

    CAPRI's GAMS (envind/breeding.gms l. 185-186):

          p_animReqCopy(RU,DCOW,A,"NEM")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386) * 365.;

    CAPRI's GAMS (envind/breeding.gms l. 195-196):

          p_animReqCopy(RU,DCOW,A,"NEP")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386)* 0.10 * 365.;

    CAPRI's GAMS (envind/breeding.gms l. 198):

          p_animReqCopy(RU,DCOW,A,"ENNE") $ p_technFact(RU,DCOW,"LEVL",A) = SUM(SUBENE, p_animReqCopy(RU,DCOW,A,SUBENE));

    In this project's notation: ENNE - NEL = NEM + 0.10 NEM + NEM x NEA_share. Departures from CAPRI: NEM the fixed 600
    kg cow's (the module's docstring)."""
    return NEM * (1.1 + NEA_share)


def p_ghgMiti_maxShare_genet(elig_share, maxShare):
    r"""p_ghgMiti(RU, MAACT, techGenet, mitiTarget, "maxShare") with fixGenet_eff_to_iniValues on: the breeding
    option's cap (0.002, lowered to the max calibration run's level where smaller, l. 375-379: maxShare, data read)
    on the animal's eligible share; off, the eligible share (MaxShare 1, l. 67-70, the caller's).

    CAPRI's GAMS (envind/breeding.gms l. 72-75):

          p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"maxShare") $ ( sum((r_ragg(RU,rmssup_breed),
                                                                       mitiTech_map(rmssup_breed,MAACT,techGenet,mitiTarget)),1)
                                                                $ DATA(RU,MAACT,"LEVL","Y") )
                                                                = 0.002;

    Departures from CAPRI: as a share of the eligible heads (elig_share x maxShare; the model's share variable is per
    head)."""
    return elig_share * maxShare


def p_ghgMiti_othImpact_genet(effect_per_unit, p_ghgTech):
    r"""p_ghgMiti(RU, MPACT, "genet_eff", "othImpact", item): a breeding option's effect at the scenario's parameter
    (ENNE = - p_ghgTechFEff, CRPR half of it, MANN through the uptake, l. 306-329; the yield option's the same with
    p_ghgTechMYld): the effect per unit of the parameter (tools/build/build_genetics_effects.py, data read) times the
    parameter.

    CAPRI's GAMS (envind/breeding.gms l. 306-307):

          p_ghgMiti(RU,MPACT,"genet_eff","othImpact","ENNE") $ p_ghgMiti(RU,MPACT,"genet_eff","rumFedEff","maxShare")
            = - p_ghgTechFEff ;

    Departures from CAPRI: the effects linear in the parameter (CAPRI's ENNE is; CRPR and MANN follow it linearly,
    l. 319-329); p_mitiEffFac 1 (l. 311-314)."""
    return effect_per_unit * p_ghgTech


def p_ghgMiti_costParLin_genet(cost_floor, cost_per_unit, p_ghgTech):
    r"""p_ghgMiti(RU, MAACT, "genet_eff", "rumFedEff", "costParLin"): the breeding programme's cost per head, 5% of the
    feed cost the energy saving spares (cost per unit of the parameter, data read), at least EUR 2 (cost_floor).

    CAPRI's GAMS (envind/breeding.gms l. 335-343):

           p_ghgMiti(RU,MAACT,"genet_eff","rumFedEff","costParLin") $ (  SUM(RU_MS(RU,MS),DATA(MS,MAACT,"DAYS","Y"))
                                                                      $ p_ghgMiti(RU,MAACT,"genet_eff","rumFedEff","maxShare"))
              = max(2,0.05* SUM(FEED,DATA(RU,MAACT,FEED,"Y")*SUM(RU_MS(RU,MS),DATA(MS,"UVAG",FEED,"Y")
                                                                           / (DATA(MS,MAACT,"DAYS","Y")/365)))*0.001
                          * (-p_ghgMiti(RU,MAACT,"genet_eff","othImpact","ENNE"))
        *                   Neutralise the cost increasing effect as this should be techncical progress:
                          / p_mitiEffFac("genet_eff","%SIMY%"))

           ;

    In this project's notation: c = max(2, c_u p). Departures from CAPRI: the feed cost per unit of the parameter from
    the builder (in the model's money)."""
    return max(cost_floor, cost_per_unit * p_ghgTech)


def p_ghgMiti_pmpParsqr_genet(costParLin, relSubs1, relSubs0, costsaving_drop, floor):
    r"""p_ghgMiti(RU, MAACT, techGenet, mitiTarget, "pmpParsqr") before the division by (MaxShare - IniShare): max(floor
    x c, c (relSubs1 - relSubs0) - (costsaving0 - costsaving1)) (floor 0.2 for breeding, GENET_GAMMA_FLOOR; low_n_feed
    0.05, line_nitr 0.1; costsaving_drop the option's marginal value's drop between CAPRI's calibration runs).

    CAPRI's GAMS (envind/breeding.gms l. 447-458):

           p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"pmpParsqr")
                  $ (p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"costParLin") $ p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"MaxShare"))
        *        Adhoc fix to avoid negative pmpParsqr. If it is binding, responsiveness will be different from planned value:
        *        This lower bound is chosen higher for breeding than for other options (low_n_feed or feed additives)
        *        as convergence problems might be avoided in this way (and the net cost is zero such that the bound may often be active)
            = max[.2*abs(p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"costParLin")),
                  p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"costParLin")
                *(p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"relSubs1")-p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"relSubs0"))
                -(p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"costsaving0")-p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"costsaving1"))
                ]
            / (p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"MaxShare")-p_ghgMiti(RU,MAACT,techGenet,mitiTarget,"IniShare"))
           ;

    Departures from CAPRI: floor x c without abs (c > 0 where the option has a cost); the division by the eligible
    heads at base (the model's share per head adopting) the caller's."""
    return max(floor * costParLin, costParLin * (relSubs1 - relSubs0) - costsaving_drop)

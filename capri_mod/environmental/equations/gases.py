r"""CAPRI's emission accounts (envind/gases.gms, star 3.0): the statements the accounts compute themselves.

Most of gases.gms's emission items are the supply model's equations of the first phase (N14a), which the accounts call
(capri_mod/supply/equations/supply_model/n2o.py GWPN2OSYN_, GWPN2OCRO_, GWPN2OMAN_, GWPN2OHIS_, GWPN2OLEA_; methane.py;
gwp.py GWPCO2LIM_, GWPCO2UREA_; air_water.py). This module holds the statements they do not write: the urea
substitution's effect on the CO2 from urea (CO2UREA); and the methane per head of enteric fermentation and manure
management (sections (1) and (2), l. 302-443: the conversion ratios NEG and GENE, the gross energy intake, IPCC's tier 2
and tier 1 CH4ENT and CH4MAN, the volatile solids, the ammonia techniques' factor), which CAPRI computes at "Y" where
%ghgAbatement% is on (capmod.gms l. 1139) and in the reports (reports/sol_simy.gms). Their digestibility comes from
envind/digestibility.gms (capri_mod/supply/equations/digestibility.py). Not ported: CH4ENTfromFEED's p_emisFeed
(l. 364-377, off in CAPRI's runs) and l. 411, which sets p_animReq(GENE) back to 0 (the caller's).

EMISCALC_CO2UREA is used by capri_mod/environmental/environmental_module.py (EnvironmentalModule.compute_indicators);
the methane functions are not called by the model's run yet (they are to give the 2030 methane per head from the
feed chain, capri_mod/feed/chain.py).
"""
from __future__ import annotations


def EMISCALC_CO2UREA(CO2UREA, FracUseFert, UreaSubst):
    r"""EMISCALC(RU, MCACT, A, "CO2UREA"): the CO2 from urea with the urea substitution, the base value CO2UREA (NMIN x
    the urea share x 44/28, supply/equations/supply_model/gwp.py GWPCO2UREA_) times max(FracUseFert - v, 0) /
    FracUseFert, FracUseFert the member state's urea share of mineral N (LitRev's p_fracUseFert, K93), v the share the
    option UreaSubst switches (v_Miti.l(RU, cropMiti, UreaSubst, NH3SYN)).

    CAPRI's GAMS (envind/gases.gms l. 833-835):

           EMISCALC(RU,MCACT,A,"CO2UREA",%1) = DATA(RU,MCACT,"NMIN",%1)  * Max(sum(map_rr(MS,RU),FracUseFert(MS,"ureum"))
        $ifi %ghgTechAmmEndog%==1      - v_Miti.L(RU,"cropMiti","UreaSubst","NH3SYN")
           ,0) * 44/28;

    In this project's notation: CO2UREA' = CO2UREA x max(f - v, 0) / f = NMIN x max(f - v, 0) x 44/28. Departures from
    CAPRI: none (CAPRI's statement written as a factor on the base value, the same product)."""
    return CO2UREA * max(FracUseFert - UreaSubst, 0.0) / FracUseFert


def _reg_or_eu(v_ru, v_eu):
    """CAPRI's X(RU) + X("EU000000") $ (NOT X(RU)): the region's value, the EU's where the region has none."""
    v = float(v_ru or 0.0)
    return v if v else float(v_eu or 0.0)


def EMISCALC_NEG(DE):
    r"""EMISCALC(RU | "EU000000", MAACT, A, "NEG", "Y"): the ratio of net energy for growth to digestible energy (IPCC
    2000), from the digestibility DE in percent (l. 317-325); 0 without DE.

    CAPRI's GAMS (envind/gases.gms l. 317-325):

          EMISCALC(RU,MAACT,A,"NEG",%1)  $ EMISCALC(RU,MAACT,A,"DE",%1)
                       = 1.164 - (0.001 * 5.16  * EMISCALC(RU,MAACT,A,"DE",%1))
                        + (1.308 * 0.00001 * (EMISCALC(RU,MAACT,A,"DE",%1)**2)) - (37.4 / EMISCALC(RU,MAACT,A,"DE",%1));
        *
        *         - for for EU average
        *
          EMISCALC("EU000000",MAACT,A,"NEG",%1) $ EMISCALC("EU000000",MAACT,A,"DE",%1)
                    = 1.164 - (0.001 * 5.16  * EMISCALC("EU000000",MAACT,A,"DE",%1))
                      + (1.308 * 0.00001 * (EMISCALC("EU000000",MAACT,A,"DE",%1)**2)) - (37.4 / EMISCALC("EU000000",MAACT,A,"DE",%1));

    The regions' and the EU's statements are one formula. Departures from CAPRI: none."""
    DE = float(DE or 0.0)
    if not DE:
        return 0.0
    return 1.164 - (0.001 * 5.16 * DE) + (1.308 * 0.00001 * (DE ** 2)) - (37.4 / DE)


def EMISCALC_GENE(DE):
    r"""EMISCALC(RU | "EU000000", MAACT, A, "GENE", "Y"): the ratio of net energy for maintenance, lactation and the
    other needs to digestible energy (IPCC 2000), from DE in percent (l. 332-340); 0 without DE.

    CAPRI's GAMS (envind/gases.gms l. 332-340):

          EMISCALC(RU,MAACT,A,"GENE",%1) $ EMISCALC(RU,MAACT,A,"DE",%1)
                    = 1.123 - (0.001 * 4.092 * EMISCALC(RU,MAACT,A,"DE",%1))
                       + (1.126 * 0.00001 * (EMISCALC(RU,MAACT,A,"DE",%1)**2)) - (25.4 / EMISCALC(RU,MAACT,A,"DE",%1));
        *
        *         - for for EU average
        *
          EMISCALC("EU000000",MAACT,A,"GENE",%1) $ EMISCALC("EU000000",MAACT,A,"DE",%1)
                    = 1.123 - (0.001 * 4.092 * EMISCALC("EU000000",MAACT,A,"DE",%1))
                       + (1.126 * 0.00001 * (EMISCALC("EU000000",MAACT,A,"DE",%1)**2)) - (25.4 / EMISCALC("EU000000",MAACT,A,"DE",%1));

    The regions' and the EU's statements are one formula. Departures from CAPRI: none."""
    DE = float(DE or 0.0)
    if not DE:
        return 0.0
    return 1.123 - (0.001 * 4.092 * DE) + (1.126 * 0.00001 * (DE ** 2)) - (25.4 / DE)


def p_animReq_GENE(p_animReqSubEne, NEG, NEG_EU, GENE, GENE_EU, DE, DE_EU):
    r"""p_animReq(RU, MAACT, A, "GENE"): the gross energy intake, MJ per head and day, where the activity has a methane
    conversion factor YM (the region's or the EU's) and a share: each net energy part of the requirement functions
    (p_animReqSubEne) over its conversion ratio (NEG for growth, GENE for the others), over the digestibility (l. 346-
    352). The caller applies the condition.

    CAPRI's GAMS (envind/gases.gms l. 346-352):

          p_animReq(RU,MAACT,A,"GENE" %addtimedim%) $ ((EMISCALC(RU,MAACT,A,"YM",%1) or EMISCALC("EU000000",MAACT,A,"YM",%1)) and p_technFact(RU,MAACT,"LEVL",A))
                 = SUM( SUBENE $ p_animReqSubEne(RU,MAACT,A,SUBENE %addtimedim%),
                                p_animReqSubEne(RU,MAACT,A,SUBENE %addtimedim%)
                         / (  (EMISCALC(RU,MAACT,A,"NEG",%1)  + EMISCALC("EU000000",MAACT,A,"NEG",%1) $ (NOT EMISCALC(RU,MAACT,A,"NEG",%1)))   $ SAMEAS(SUBENE,"NEG")
                            + (EMISCALC(RU,MAACT,A,"GENE",%1) + EMISCALC("EU000000",MAACT,A,"GENE",%1) $ (NOT EMISCALC(RU,MAACT,A,"GENE",%1))) $ (NOT SAMEAS(SUBENE,"NEG"))  )
                      )
                   / ((EMISCALC(RU,MAACT,A,"DE",%1) + EMISCALC("EU000000",MAACT,A,"DE",%1) $ (NOT EMISCALC(RU,MAACT,A,"DE",%1)))/100);

    p_animReqSubEne: {SUBENE: value} of the activity and technology (capri_mod/feed/equations/req_or_man_fnc_req.py).
    A part whose ratio is 0 divides by 0 in GAMS (an execution error); it does not occur where DE is given. Departures
    from CAPRI: none."""
    neg, gene = _reg_or_eu(NEG, NEG_EU), _reg_or_eu(GENE, GENE_EU)
    de = _reg_or_eu(DE, DE_EU)
    tot = sum(float(v) / (neg if s == "NEG" else gene) for s, v in p_animReqSubEne.items() if float(v or 0.0))
    return tot / (de / 100)


def EMISCALC_CH4ENT_tier2(YM, YM_EU, GENE_req, days):
    r"""EMISCALC(RU, MAACT, A, "CH4ENT", "Y"), IPCC's tier 2: kg CH4 per head from enteric fermentation, YM (the
    region's or the EU's) times the gross energy intake times the production days over 55.65 MJ per kg CH4 (l. 357-359). The
    caller applies the condition (a YM and a share).

    CAPRI's GAMS (envind/gases.gms l. 357-359):

          EMISCALC(RU,MAACT,A,"CH4ENT",%1)  $ ((EMISCALC(RU,MAACT,A,"YM",%1) or EMISCALC("EU000000",MAACT,A,"YM",%1)) and p_technFact(RU,MAACT,"LEVL",A))
                          = (EMISCALC(RU,MAACT,A,"YM",%1) + EMISCALC("EU000000",MAACT,A,"YM",%1) $ (NOT EMISCALC(RU,MAACT,A,"YM",%1)))
                                * p_animReq(RU,MAACT,A,"GENE"%addtimedim%) * p_animProdDays(RU,MAACT,A%addtimedim%) / 55.65;

    GENE_req: p_animReq(RU, MAACT, A, "GENE") (p_animReq_GENE); days: p_animProdDays(RU, MAACT, A). Departures from
    CAPRI: none."""
    return _reg_or_eu(YM, YM_EU) * float(GENE_req or 0.0) * float(days or 0.0) / 55.65


def EMISCALC_CH4ENT_tier1(CH4ENT, CH4EN, CH4EN_EU, days, has_share):
    r"""EMISCALC(RU, MAACT, A, "CH4ENT", "Y"), IPCC's tier 1 where tier 2 gave none: the fixed coefficient per head and
    year CH4EN (the region's or the EU's) over 365 times the production days (l. 384-386).

    CAPRI's GAMS (envind/gases.gms l. 384-386):

          EMISCALC(RU,MAACT,A,"CH4ENT",%1) $ ( (NOT EMISCALC(RU,MAACT,A,"CH4ENT",%1)) and p_technFact(RU,MAACT,"LEVL",A))
               = (EMISCALC(RU,MAACT,A,"CH4EN",%1)
                + EMISCALC("EU000000",MAACT,A,"CH4EN",%1) $ (NOT EMISCALC(RU,MAACT,A,"CH4EN",%1)))/365 * p_animProdDays(RU,MAACT,A%addtimedim%);

    CH4ENT: the tier 2 value (0 where none); has_share: p_technFact(RU, MAACT, "LEVL", A) is not 0. Departures from
    CAPRI: none."""
    CH4ENT = float(CH4ENT or 0.0)
    if CH4ENT or not has_share:
        return CH4ENT
    return _reg_or_eu(CH4EN, CH4EN_EU) / 365 * float(days or 0.0)


def EMISCALC_VSER(GENE_req, GE, DE, DE_EU, ASH, ASH_EU):
    r"""EMISCALC(RU, MAACT, A, "VSER", "Y"): the volatile solids excreted, kg dry matter per day, from the gross energy
    intake, the ration's gross energy (18.45 MJ per kg where the region has none), its digestibility and ash (l. 405-
    408). The caller applies the condition (a DE, the region's or the EU's, and a share).

    CAPRI's GAMS (envind/gases.gms l. 405-408):

          EMISCALC(RU,MAACT,A,"VSER",%1) $ ( (EMISCALC(RU,MAACT,A,"DE",%1) or EMISCALC("EU000000",MAACT,A,"DE",%1)) and p_technFact(RU,MAACT,"LEVL",A))
                 =  p_animReq(RU,MAACT,A,"GENE"%addtimedim%) * (1/(EMISCALC(RU,MAACT,A,"GE",%1) * 4.184 + 18.45 $ (NOT EMISCALC(RU,MAACT,A,"GE",%1))))
                      * (1 - (EMISCALC(RU,MAACT,A,"DE",%1)  + EMISCALC("EU000000",MAACT,A,"DE",%1)  $ (NOT EMISCALC(RU,MAACT,A,"DE",%1))) / 100 + 0.04)
                      * (1 - (EMISCALC(RU,MAACT,A,"ASH",%1) + EMISCALC("EU000000",MAACT,A,"ASH",%1) $ (NOT EMISCALC(RU,MAACT,A,"ASH",%1))) / 100);

    GENE_req: p_animReq(RU, MAACT, A, "GENE") before l. 411 sets it to 0. Departures from CAPRI: none."""
    GE = float(GE or 0.0)
    return (float(GENE_req or 0.0) * (1 / (GE * 4.184 + (18.45 if not GE else 0.0)))
            * (1 - _reg_or_eu(DE, DE_EU) / 100 + 0.04)
            * (1 - _reg_or_eu(ASH, ASH_EU) / 100))


def EMISCALC_CH4MAN_tier2(VSER, B0, B0_EU, MCFMS, days):
    r"""EMISCALC(RU, MAACT, A, "CH4MAN", "Y"), IPCC's tier 2: kg CH4 per head from manure management, the volatile
    solids times the maximum CH4 capacity B0 (the region's or the EU's, m3 per kg), 0.67 kg per m3, the conversion
    factor of the management systems MCFMS and the production days (l. 420-422). The caller applies the condition (a
    share).

    CAPRI's GAMS (envind/gases.gms l. 420-422):

          EMISCALC(RU,MAACT,A,"CH4MAN",%1) $ p_technFact(RU,MAACT,"LEVL",A)
              = EMISCALC(RU,MAACT,A,"VSER",%1) * ( EMISCALC(RU,MAACT,A,"B0",%1) + EMISCALC("EU000000",MAACT,A,"B0",%1) $ (NOT EMISCALC(RU,MAACT,A,"B0",%1)))
                  * 0.67 * EMISCALC(RU,MAACT,A,"MCFMS",%1) * p_animProdDays(RU,MAACT,A%addtimedim%);

    Departures from CAPRI: none."""
    return float(VSER or 0.0) * _reg_or_eu(B0, B0_EU) * 0.67 * float(MCFMS or 0.0) * float(days or 0.0)


def EMISCALC_CH4MAN_tier1(CH4MAN, tier1_MS, tier1_EUGR, shareClim_RU, shareClim_MS, days, has_share):
    r"""EMISCALC(RU, MAACT, A, "CH4MAN", "Y"), IPCC's tier 1 where tier 2 gave none: the member state's emission factors
    of the management systems by climate (its EU group's where it has none) weighted by the region's climate shares
    (the member state's where the region has none), per year over 365 times the production days (l. 431-434).

    CAPRI's GAMS (envind/gases.gms l. 431-434):

          EMISCALC(RU,MAACT,A,"CH4MAN",%1) $ (p_technFact(RU,MAACT,"LEVL",A) and (NOT EMISCALC(RU,MAACT,A,"CH4MAN",%1)))
                 = SUM( (MS,CLIMCELS) $ MAP_RR(MS,RU), (p_tier1EmFactManMgt(MS,MAACT,A,CLIMCELS) +
                             sum(EUGR_TO_MS(EUGR,MS),p_tier1EmFactManMgt(EUGR,MAACT,A,CLIMCELS)) $ (NOT p_tier1EmFactManMgt(MS,MAACT,A,CLIMCELS))) *
                   (p_shareClimZone(RU,CLIMCELS) + p_shareClimZone(MS,CLIMCELS) $ (NOT sum(CLIMCELS1,p_shareClimZone(RU,CLIMCELS1)))) * 0.01)/365 * p_animProdDays(RU,MAACT,A%addtimedim%);

    tier1_MS, tier1_EUGR: {CLIMCELS: p_tier1EmFactManMgt(MS | its EUGR, MAACT, A, CLIMCELS)}; shareClim_RU,
    shareClim_MS: {CLIMCELS: p_shareClimZone(RU | MS, CLIMCELS)} in percent. One member state per region (MAP_RR).
    Departures from CAPRI: none."""
    CH4MAN = float(CH4MAN or 0.0)
    if CH4MAN or not has_share:
        return CH4MAN
    use_ms = not sum(float(v or 0.0) for v in shareClim_RU.values())
    cells = set(tier1_MS) | set(tier1_EUGR) | set(shareClim_RU) | set(shareClim_MS)
    tot = 0.0
    for c in cells:
        ef = _reg_or_eu(tier1_MS.get(c, 0.0), tier1_EUGR.get(c, 0.0))
        sh = float(shareClim_RU.get(c, 0.0) or 0.0) + (float(shareClim_MS.get(c, 0.0) or 0.0) if use_ms else 0.0)
        tot += ef * sh * 0.01
    return tot / 365 * float(days or 0.0)


def EMISCALC_CH4MAN_NH3_techs(CH4MAN, LossHous_Solid, LossStor_Solid, TypeShare_Solid, LossHous_Liquid,
                              LossStor_Liquid, TypeShare_Liquid):
    r"""EMISCALC(RU, MAACT, A, "CH4MAN", "Y") where %ghgAbatement% is off: the ammonia abatement techniques' effect on
    the manure's methane, applied as a factor (MITERRA's CH4 losses in housing and storage, by the solid and liquid
    systems' shares; l. 437-443). With %ghgAbatement% on CAPRI applies it in the supply model instead.

    CAPRI's GAMS (envind/gases.gms l. 437-443):

        $iftheni not %ghgAbatement%==on
          EMISCALC(RU,MAACT,A,"CH4MAN",%1) = EMISCALC(RU,MAACT,A,"CH4MAN",%1)
                                           * sum(MAP_RR(MS,RU),(1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Solid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Solid"))
                                           * p_Nemidat(MS,MAACT,"N","TypeShare","Solid")
                                           + (1. - p_Nemidat(MS,MAACT,"CH4","LossHous","Liquid") - p_Nemidat(MS,MAACT,"CH4","LossStor","Liquid"))
                                           * p_Nemidat(MS,MAACT,"N","TypeShare","Liquid"));
        $endif;

    The arguments: the member state's p_Nemidat(MS, MAACT, "CH4", LossHous | LossStor, Solid | Liquid) and
    p_Nemidat(MS, MAACT, "N", "TypeShare", Solid | Liquid). Departures from CAPRI: none."""
    f = lambda x: float(x or 0.0)                                            # noqa: E731
    return f(CH4MAN) * ((1. - f(LossHous_Solid) - f(LossStor_Solid)) * f(TypeShare_Solid)
                        + (1. - f(LossHous_Liquid) - f(LossStor_Liquid)) * f(TypeShare_Liquid))

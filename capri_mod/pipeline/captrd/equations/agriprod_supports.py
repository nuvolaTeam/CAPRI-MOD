r"""CAPTRD's statements of captrd/agriprod_supports.gms (CAPRI star 3.0, included by expert_support.gms l. 771): the
short-run supports from Eurostat's recent production statistics (p_AgriProd), as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/agriprod_supports.py (supports, _bounds) holds the
loops over the member states, the items, the years and the activities, the conditions and the order, and calls them;
the arithmetic is the port's, so the supports are unchanged. The 2019 block (l. 505-611) is the 2020 block's statements
for 2019 (both quoted); the 2018 block (l. 614-697) is not ported (2018 has COCO's data in the reference run).
"""
from __future__ import annotations


def p_AgriProd_SE_shepGoat():
    r"""p_AgriProd("SE000", shepGoat, ., yrAgriProd) from 2018: removed (a break in the series).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 233-233):

           p_AgriProd("SE000",shepGoat,itemAgriProd,yrAgriProd) $ (calyea(yrAgriProd) ge calyea("2018")) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return 0.0


def p_AgriProd_fill(before):
    r"""p_AgriProd(., "2018" / "2019" / "2020") without one: the year before's.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 238-239):

          p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2018") $ (not p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2018"))
             = p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2017");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 241-242):

          p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2019") $ (not p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2019"))
             = p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2018");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 244-245):

          p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2020") $ (not p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2020"))
             = p_AgriProd(msAgriprod,agriprod,itemAgriProd,"2019");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return before


def p_AgriProd_adNonDai(cata, dcow, calv):
    r"""p_AgriProd(., "adNonDai", "sur4", yrAgriProd): the other cattle, all cattle less dairy cows and calves, where all
    three are given (else deleted).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 250-256):

          p_AgriProd(msAgriprod,"adNonDai","sur4",yrAgriProd)
              = ( p_AgriProd(msAgriprod,"cata","sur4",yrAgriProd)
                - p_AgriProd(msAgriprod,"dcow","sur4",yrAgriProd)
                - p_AgriProd(msAgriprod,"calv","sur4",yrAgriProd))
              $ ( p_AgriProd(msAgriprod,"cata","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"dcow","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"calv","sur4",yrAgriProd));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return (cata - dcow - calv) if (cata and dcow and calv) else 0.0


def p_AgriProd_pigf(pigl20, pigf50):
    r"""p_AgriProd(., "pigf", "sur4", yrAgriProd): the fattening pigs, PIGL20 + PIGF50 where both are given (else
    deleted).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 258-262):

          p_AgriProd(msAgriprod,"pigf","sur4",yrAgriProd)
              = ( p_AgriProd(msAgriprod,"pigl20","sur4",yrAgriProd)
                + p_AgriProd(msAgriprod,"pigf50","sur4",yrAgriProd))
              $ ( p_AgriProd(msAgriprod,"pigl20","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"pigf50","sur4",yrAgriProd));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return (pigl20 + pigf50) if (pigl20 and pigf50) else 0.0


def p_AgriProd_pigf_rest(pigs, pigl00, boar, sows):
    r"""p_AgriProd(., "pigf", "sur4", yrAgriProd) without one: all pigs less piglets, boars and sows, where pigs, piglets
    and sows are given.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 264-271):

          p_AgriProd(msAgriprod,"pigf","sur4",yrAgriProd) $ (not p_AgriProd(msAgriprod,"pigf","sur4",yrAgriProd))
              = ( p_AgriProd(msAgriprod,"pigs","sur4",yrAgriProd)
                - p_AgriProd(msAgriprod,"pigl00","sur4",yrAgriProd)
                - p_AgriProd(msAgriprod,"boar","sur4",yrAgriProd)
                - p_AgriProd(msAgriprod,"sows","sur4",yrAgriProd))
              $ ( p_AgriProd(msAgriprod,"pigs","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"pigl00","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"sows","sur4",yrAgriProd));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return (pigs - pigl00 - boar - sows) if (pigs and pigl00 and sows) else 0.0


def p_AgriProd_shgt(sheps, goats):
    r"""p_AgriProd(., "shgt", "sur4", yrAgriProd): sheep and goats where both are given (else deleted).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 273-277):

          p_AgriProd(msAgriprod,"shgt","sur4",yrAgriProd)
              = ( p_AgriProd(msAgriprod,"sheps","sur4",yrAgriProd)
                + p_AgriProd(msAgriprod,"goats","sur4",yrAgriProd))
              $ ( p_AgriProd(msAgriprod,"sheps","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"goats","sur4",yrAgriProd));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return (sheps + goats) if (sheps and goats) else 0.0


def p_AgriProd_shgm(shep, goat):
    r"""p_AgriProd(., "shgm", "sur4", yrAgriProd): the milk sheep and goats where both are given (else deleted).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 279-283):

          p_AgriProd(msAgriprod,"shgm","sur4",yrAgriProd)
              = ( p_AgriProd(msAgriprod,"shep","sur4",yrAgriProd)
                + p_AgriProd(msAgriprod,"goat","sur4",yrAgriProd))
              $ ( p_AgriProd(msAgriprod,"shep","sur4",yrAgriProd)
                $ p_AgriProd(msAgriprod,"goat","sur4",yrAgriProd));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return (shep + goat) if (shep and goat) else 0.0


def p_AgriProd_MT000_2017(value):
    r"""p_AgriProd("MT000", "grof", ., "2017"): Malta's milk positions confounded in 2017, each from the next one's.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 290-290):

          p_AgriProd("MT000","grof","gmlk","2017") = p_AgriProd("MT000","grof","emlk","2017");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 291-291):

          p_AgriProd("MT000","grof","emlk","2017") = p_AgriProd("MT000","grof","cmlk","2017");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 292-292):

          p_AgriProd("MT000","grof","cmlk","2017") = p_AgriProd("MT000","grof","rmlk","2017");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return value


def p_AgriProd_grof_cmlk(rmlk, emlk, gmlk):
    r"""p_AgriProd(., "grof", "cmlk", yrAgriProd) without one: raw milk less ewe and goat milk.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 294-301):

          p_AgriProd(msAgriprod,"grof","cmlk",yrAgriProd)
              $ ( (not p_AgriProd(msAgriprod,"grof","cmlk",yrAgriProd))
                $ p_AgriProd(msAgriprod,"grof","rmlk",yrAgriProd)
                $ (p_AgriProd(msAgriprod,"grof","emlk",yrAgriProd) or (not sum(yrAgriProd1,p_AgriProd(msAgriprod,"grof","emlk",yrAgriProd1))))
                $ (p_AgriProd(msAgriprod,"grof","gmlk",yrAgriProd) or (not sum(yrAgriProd1,p_AgriProd(msAgriprod,"grof","gmlk",yrAgriProd1)))))
              =   p_AgriProd(msAgriprod,"grof","rmlk",yrAgriProd)
                - p_AgriProd(msAgriprod,"grof","emlk",yrAgriProd)
                - p_AgriProd(msAgriprod,"grof","gmlk",yrAgriProd);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return rmlk - emlk - gmlk


def p_AgriProd_yild_cmlk(grof, dcow):
    r"""p_AgriProd(., "yild", "cmlk", yrAgriProd): the milk yield in kg, cow milk (1000 t) over dairy cows (1000
    heads).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 304-305):

          p_AgriProd(msAgriprod,"yild","cmlk",yrAgriProd) $ p_AgriProd(msAgriprod,"dcow","sur4",yrAgriProd)
              =   p_AgriProd(msAgriprod,"grof","cmlk",yrAgriProd)/p_AgriProd(msAgriprod,"dcow","sur4",yrAgriProd) * 1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return grof / dcow * 1000.0


def p_AgriProd_facYr(values):
    r"""p_AgriProd(., facYr): the three years' mean around the base year, where all three are given.

    values: the three years' values, in order.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 333-337):

          p_AgriProd(msagriprod,Agriprod,itemAgriProd,facYr)
              $ (sum(yrAgriProd $ ( p_AgriProd(msAgriprod,Agriprod,itemAgriProd,yrAgriProd)
                                  $ (abs(calyea(yrAgriProd)-calYea(facYr)) le 1)           ), 1) eq 3)
              =  sum(yrAgriProd $ (abs(calyea(yrAgriProd)-calYea(facYr)) le 1),
                                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,yrAgriProd))/3;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return sum(values) / 3


def p_AgriProd_fac(values, base):
    r"""p_AgriProd(., Agriprod, "fac2020" / "fac2019" / "fac2018", facyr): the year's data over the base mean, summed
    over the items of the series (agriprod_to_item).

    values, base: the items' values of the year and of facyr, in the caller's order.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 341-347):

          p_AgriProd(msagriprod,Agriprod,"fac2020",facyr)
              $ sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr))
              = sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,"2020"))
              / sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 349-355):

          p_AgriProd(msagriprod,Agriprod,"fac2019",facyr)
              $ sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr))
              = sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,"2019"))
              / sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 358-364):

          p_AgriProd(msagriprod,Agriprod,"fac2018",facyr)
              $ sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr))
              = sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,"2018"))
              / sum(agriprod_to_item(agriProd,itemAgriProd),
                    p_AgriProd(msAgriprod,Agriprod,itemAgriProd,facyr));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return sum(values) / sum(base)


def p_AgriProd_fac_AgriProdAact(factors):
    r"""p_AgriProd(., AgriProdAact, "fac2020" / "fac2019" / "fac2018", facyr) without one: the factors of its series
    (cols_TO_agriprod) in agriProd1, else agriProd2, summed.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 370-371):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2020",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2020",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd1), p_AgriProd(msAgriprod,AgriProd1,"fac2020",facyr) );

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 373-374):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2020",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2020",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd2), p_AgriProd(msAgriprod,AgriProd2,"fac2020",facyr) );

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 376-377):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2019",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2019",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd1), p_AgriProd(msAgriprod,AgriProd1,"fac2019",facyr) );

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 379-380):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2019",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2019",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd2), p_AgriProd(msAgriprod,AgriProd2,"fac2019",facyr) );

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 382-383):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2018",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2018",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd1), p_AgriProd(msAgriprod,AgriProd1,"fac2018",facyr) );

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 385-386):

          p_AgriProd(msAgriprod,AgriProdAact,"fac2018",facyr) $ (not p_AgriProd(msAgriprod,AgriProdAact,"fac2018",facyr))
              = sum(cols_TO_agriprod(AgriprodAact,agriProd2), p_AgriProd(msAgriprod,AgriProd2,"fac2018",facyr) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return sum(factors)


def p_ExpertSupprt_absolute(factors, base):
    r"""p_ExpertSupprt(runr, ., "2020" / "2019", "absolute") of the herds, levels and milk yields (COMI): the member
    state's factor (MSagriprod_map) on the %BaseYear% mean times BASM, else on 2018's times p_data of 2018 (the dairy
    yields from YILD's factor, GROF.COMI from GROF's).

    factors: the factors of the member state's p_AgriProd regions, in the caller's order; base: BASM or p_data.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 402-405):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute")
              $ ( P_Result(runr,AgriProdAact,herdLevl,"2020","BASM") )
              = sum(MSagriprod_map(msagriprod, Runr), p_AgriProd(msAgriprod,AgriProdAact,"fac2020","20%BAS%") )
              * P_Result(runr,AgriProdAact,herdLevl,"2020","BASM");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 408-411):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute")
              $ ( P_Result(runr,AgriProdAact,herdLevl,"2018","p_data") $ (not p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute") ))
              = sum(MSagriprod_map(msagriprod, Runr), p_AgriProd(msAgriprod,AgriProdAact,"fac2020","2018" ))
              * P_Result(runr,AgriProdAact,herdLevl,"2018","p_data");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 460-466):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute")
              $ ( P_Result(runr,s_colsEst,"COMI","2020","BASM")
                $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF")))
              = sum(MSagriprod_map(msagriprod, Runr),
                     p_AgriProd(msAgriprod,"YILD","fac2020","20%BAS%") $ P_T_ActAgg(s_colsEst,"DCOW")
                   + p_AgriProd(msAgriprod,"GROF","fac2020","20%BAS%") $ sameas(s_colsEst,"GROF")     )
              * P_Result(runr,s_colsEst,"COMI","2020","BASM");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 469-475):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute")
              $ ( P_Result(runr,s_colsEst,"COMI","2018","p_data")   $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF"))
                $ (not p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute")))
              = sum(MSagriprod_map(msagriprod, Runr),
                     p_AgriProd(msAgriprod,"YILD","fac2020","2018" ) $ P_T_ActAgg(s_colsEst,"DCOW")
                   + p_AgriProd(msAgriprod,"GROF","fac2020","2018" ) $ sameas(s_colsEst,"GROF")     )
              * P_Result(runr,s_colsEst,"COMI","2018","p_data");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 512-515):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute")
              $ ( P_Result(runr,AgriProdAact,herdLevl,"2019","BASM") )
              = sum(MSagriprod_map(msagriprod, Runr), p_AgriProd(msAgriprod,AgriProdAact,"fac2019","20%BAS%") )
              * P_Result(runr,AgriProdAact,herdLevl,"2019","BASM");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 518-521):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute")
              $ ( P_Result(runr,AgriProdAact,herdLevl,"2018","p_data") $ (not p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute") ))
              = sum(MSagriprod_map(msagriprod, Runr), p_AgriProd(msAgriprod,AgriProdAact,"fac2019","2018" ))
              * P_Result(runr,AgriProdAact,herdLevl,"2018","p_data");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 567-573):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute")
              $ ( P_Result(runr,s_colsEst,"COMI","2019","BASM")
              $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF")))
              = sum(MSagriprod_map(msagriprod, Runr),
                     p_AgriProd(msAgriprod,"YILD","fac2019","20%BAS%") $ P_T_ActAgg(s_colsEst,"DCOW")
                   + p_AgriProd(msAgriprod,"GROF","fac2019","20%BAS%") $ sameas(s_colsEst,"GROF")     )
              * P_Result(runr,s_colsEst,"COMI","2019","BASM");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 576-582):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute")
              $ ( P_Result(runr,s_colsEst,"COMI","2018","p_data")   $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF"))
                $ (not p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute")))
              = sum(MSagriprod_map(msagriprod, Runr),
                     p_AgriProd(msAgriprod,"YILD","fac2019","2018" ) $ P_T_ActAgg(s_colsEst,"DCOW")
                   + p_AgriProd(msAgriprod,"GROF","fac2019","2018" ) $ sameas(s_colsEst,"GROF")     )
              * P_Result(runr,s_colsEst,"COMI","2018","p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return sum(factors) * base


def p_ExpertSupprt_Trustlevl(absolute):
    r"""p_ExpertSupprt(runr, ., "2020" / "2019", "Trustlevl"): 9.02 above 1, else 3.02 (statistics trusted, the .02 to
    check later).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 415-418):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","Trustlevl") $ p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute")
              = 9.02 $ (p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute") gt 1)
              + 3.02 $ (p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2020","absolute") le 1)
              ;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 479-483):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2020","Trustlevl")
              $ ( p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute") $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF")))
              = 9.02 $ (p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute") gt 1)
              + 3.02 $ (p_ExpertSupprt(runr,s_colsEst,"COMI","2020","absolute") le 1)
              ;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 525-528):

          p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","Trustlevl") $ p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute")
              = 9.02 $ (p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute") gt 1)
              + 3.02 $ (p_ExpertSupprt(runr,AgriProdAact,herdLevl,"2019","absolute") le 1)
              ;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 586-590):

          p_ExpertSupprt(runr,s_colsEst,"COMI","2019","Trustlevl")
              $ ( p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute")
                $ (P_T_ActAgg(s_colsEst,"DCOW") or sameas(s_colsEst,"GROF")))
              = 9.02 $ (p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute") gt 1)
              + 3.02 $ (p_ExpertSupprt(runr,s_colsEst,"COMI","2019","absolute") le 1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return 9.02 if absolute > 1.0 else 3.02


def p_result_expertLo_DAYS(lst_expost, lim_lo):
    r"""p_result(runr, meatAct, "DAYS" / "DAILY", exanteT, "expertLo") of a herd with a support: 70% of the last ex-post
    year, at least p_reqfcnlim's lower limit.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 425-427):

          p_result(runr,meatAct,rows,exanteT,"expertLo") $ ( (sameas(rows,"DAYS") or sameas(rows,"DAILY") ) $ sameas(exanteT,"2020")
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2020","absolute"))
              = max(.7*sum(Lst_exPostT,P_Result(runr,meatAct,rows,Lst_exPostT,"p_data")),p_reqfcnlim(meatAct,Rows,"lo"));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 535-537):

          p_result(runr,meatAct,rows,exanteT,"expertLo") $ ( (sameas(rows,"DAYS") or sameas(rows,"DAILY") ) $ sameas(exanteT,"2019")
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2019","absolute"))
              = max(.7*sum(Lst_exPostT,P_Result(runr,meatAct,rows,Lst_exPostT,"p_data")),p_reqfcnlim(meatAct,Rows,"lo"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return max(0.7 * lst_expost, lim_lo)


def p_result_expertUp_DAYS(lst_expost, lim_up):
    r"""p_result(runr, meatAct, "DAYS" / "DAILY", exanteT, "expertup"): 150% of the last ex-post year, at most
    p_reqfcnlim's upper limit.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 428-430):

          p_result(runr,meatAct,rows,exanteT,"expertup") $ ( (sameas(rows,"DAYS") or sameas(rows,"DAILY") ) $ sameas(exanteT,"2020")
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2020","absolute"))
              = min(1.5*sum(Lst_exPostT,P_Result(runr,meatAct,rows,Lst_exPostT,"p_data")),p_reqfcnlim(meatAct,Rows,"up"));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 538-540):

          p_result(runr,meatAct,rows,exanteT,"expertup") $ ( (sameas(rows,"DAYS") or sameas(rows,"DAILY") ) $ sameas(exanteT,"2019")
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2019","absolute"))
              = min(1.5*sum(Lst_exPostT,P_Result(runr,meatAct,rows,Lst_exPostT,"p_data")),p_reqfcnlim(meatAct,Rows,"up"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return min(1.5 * lst_expost, lim_up)


def p_result_expertLo_meat(lst_expost, bast):
    r"""p_result(runr, meatAct, meat, exanteT, "expertLo"): 70% of the smaller of the last ex-post year and BAST.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 432-437):

          p_result(runr,meatAct,meat,exanteT,"expertLo") $ ( pact_to_y(meatAct,meat)
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2020","absolute")
                                                           $ sameas(exanteT,"2020")
                                                           $ sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data"))
                                                           $ P_DATA(runr,meatAct,meat,"BAST"))
              = .7*min(sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data")),P_DATA(runr,meatAct,meat,"BAST"));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 542-547):

          p_result(runr,meatAct,meat,exanteT,"expertLo") $ ( pact_to_y(meatAct,meat)
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2019","absolute")
                                                           $ sameas(exanteT,"2019")
                                                           $ sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data"))
                                                           $ P_DATA(runr,meatAct,meat,"BAST"))
              = .7*min(sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data")),P_DATA(runr,meatAct,meat,"BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return 0.7 * min(lst_expost, bast)


def p_result_expertUp_meat(lst_expost, bast):
    r"""p_result(runr, meatAct, meat, exanteT, "expertup"): 150% of the larger of the last ex-post year and BAST.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 438-443):

          p_result(runr,meatAct,meat,exanteT,"expertup") $ (  pact_to_y(meatAct,meat)
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2020","absolute")
                                                           $ sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data"))
                                                           $ sameas(exanteT,"2020")
                                                           $ P_DATA(runr,meatAct,meat,"BAST"))
              = 1.5*max(sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data")),P_DATA(runr,meatAct,meat,"BAST"));

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 548-553):

          p_result(runr,meatAct,meat,exanteT,"expertup") $ (  pact_to_y(meatAct,meat)
                                                           $ p_ExpertSupprt(runr,meatAct,"HERD","2019","absolute")
                                                           $ sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data"))
                                                           $ sameas(exanteT,"2019")
                                                           $ P_DATA(runr,meatAct,meat,"BAST"))
              = 1.5*max(sum(Lst_exPostT,P_Result(runr,meatAct,meat,Lst_exPostT,"p_data")),P_DATA(runr,meatAct,meat,"BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return 1.5 * max(lst_expost, bast)


def p_result_expertLo_herd(absolute):
    r"""p_result(runr, ., "2020" / "2019", "expertLo") of the dairy herds and levels and of GROF.COMI: 1% below the
    support.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 447-449):

          p_result(runr,s_colsEst,herdLevl,"2020","expertLo") $ ( p_ExpertSupprt(runr,s_colsEst,herdLevl,"2020","absolute")
                                                                      $ P_T_ActAgg(s_colsEst,"DCOW"))
              = p_ExpertSupprt(runr,s_colsEst,herdLevl,"2020","absolute") *.99;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 490-491):

          p_result(runr,"GROF","COMI","2020","expertLo") $  p_ExpertSupprt(runr,"GROF","COMI","2020","absolute")
              = p_ExpertSupprt(runr,"GROF","COMI","2020","absolute") *.99;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 556-558):

          p_result(runr,s_colsEst,herdLevl,"2019","expertLo") $ ( p_ExpertSupprt(runr,s_colsEst,herdLevl,"2019","absolute")
                                                                      $ P_T_ActAgg(s_colsEst,"DCOW"))
              = p_ExpertSupprt(runr,s_colsEst,herdLevl,"2019","absolute") *.99;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 599-600):

          p_result(runr,"GROF","COMI","2019","expertLo") $  p_ExpertSupprt(runr,"GROF","COMI","2019","absolute")
              = p_ExpertSupprt(runr,"GROF","COMI","2019","absolute") *.99;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return absolute * 0.99


def p_result_expertUp_herd(absolute):
    r"""p_result(runr, ., "2020" / "2019", "expertUp") of the dairy herds and levels and of GROF.COMI: 1% above the
    support.

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 451-453):

          p_result(runr,s_colsEst,herdLevl,"2020","expertUp") $ ( p_ExpertSupprt(runr,s_colsEst,herdLevl,"2020","absolute")
                                                                      $ P_T_ActAgg(s_colsEst,"DCOW"))
              = p_ExpertSupprt(runr,s_colsEst,herdLevl,"2020","absolute") *1.01;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 493-494):

          p_result(runr,"GROF","COMI","2020","expertUp") $  p_ExpertSupprt(runr,"GROF","COMI","2020","absolute")
              = p_ExpertSupprt(runr,"GROF","COMI","2020","absolute") *1.01;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 560-562):

          p_result(runr,s_colsEst,herdLevl,"2019","expertUp") $ ( p_ExpertSupprt(runr,s_colsEst,herdLevl,"2019","absolute")
                                                                      $ P_T_ActAgg(s_colsEst,"DCOW"))
              = p_ExpertSupprt(runr,s_colsEst,herdLevl,"2019","absolute") *1.01;

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 602-603):

          p_result(runr,"GROF","COMI","2019","expertUp") $  p_ExpertSupprt(runr,"GROF","COMI","2019","absolute")
              = p_ExpertSupprt(runr,"GROF","COMI","2019","absolute") *1.01;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (agriprod_supports.supports)."""
    return absolute * 1.01


def p_ExpertSupprt_BAS(value):
    r"""p_ExpertSupprt(runr, s_colsest, s_rowsest, "2017" / "2016", "absolute") where 2020 has one: BASM of 2020,
    p_data of 2016 (the base the nowcast's change applies to).

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 701-702):

          p_ExpertSupprt(runr,s_colsest,s_rowsest,"2017","absolute") $ p_ExpertSupprt(runr,s_colsest,s_rowsest,"2020","absolute")
             = P_Result(runr,s_colsest,s_rowsest,"2020","BASM");

    CAPRI's GAMS (captrd/agriprod_supports.gms l. 703-704):

          p_ExpertSupprt(runr,s_colsest,s_rowsest,"2016","absolute") $ p_ExpertSupprt(runr,s_colsest,s_rowsest,"2020","absolute")
             = P_Result(runr,s_colsest,s_rowsest,"2016","p_data");

    Departures from CAPRI: the port writes %BaseYear% and the year before for the literal 2017 and 2016 (the same in the reference run); 
    the domain condition in the caller (agriprod_supports.supports)."""
    return value

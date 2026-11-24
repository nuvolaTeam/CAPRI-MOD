r"""CAPTRD's statements of captrd/captrd_policy.gms (CAPRI star 3.0): the sugar beet quotas and the set-aside rates in
p_data, as named functions (the milk and sugar quotas are mquota_update.py's, load_quotas.py's and
reformsugarquotas.py's, the files it includes).

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/policy.py (sugar_beet, set_aside) holds the loops
over the countries, the regions and the years and the conditions, and calls them; the arithmetic is the port's, so the
data are unchanged.
"""
from __future__ import annotations


def p_data_quotas_SUGA_MSnoSugb():
    r"""p_data(MSnoSugb, quotas, "SUGA", exanteT) without one: near zero (1e-6), the countries not to grow sugar beet
    in the projection.

    CAPRI's GAMS (captrd/captrd_policy.gms l. 73-73):

         p_data(MSnoSugb,quotas,"SUGA",exanteT) $ ((not p_data(MSnoSugb,quotas,"SUGA",exanteT)) $ msincl(MSnoSugb)) = 1.E-6;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return 1e-6


def p_data_QUTS_SUGB(quts_suga, quts_sugb_basm, quts_suga_basm, prcy_suga_basm):
    r"""p_data(MS, "QUTS", "SUGB", YEARS): the beet quota from the sugar quota, at the base year's ratio, else over the
    sugar yield (Series over (region, year); the base values each region's).

    CAPRI's GAMS (captrd/captrd_policy.gms l. 78-82):

         p_data(MS,"QUTS","SUGB",YEARS) $ (p_data(MS,"QUTS","SUGA","BASM"))
               = p_data(MS,"QUTS","SUGA",YEARS) * p_data(MS,"QUTS","SUGB","BASM")/p_data(MS,"QUTS","SUGA","BASM");

         p_data(MS,"QUTS","SUGB",YEARS) $ ( (not p_data(MS,"QUTS","SUGA","BASM")) $ p_data(MS,"PRCY","SUGA","BASM"))
               = p_data(MS,"QUTS","SUGA",YEARS) /p_data(MS,"PRCY","SUGA","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    new = (quts_suga * quts_sugb_basm / quts_suga_basm.where(quts_suga_basm != 0, 1.0)).where(quts_suga_basm != 0, 0.0)
    return new.where(quts_suga_basm != 0, (quts_suga / prcy_suga_basm.where(prcy_suga_basm != 0, 1.0))
                     .where(prcy_suga_basm != 0, 0.0))


def p_dataCopy_QUTS_SUGB_share(region_basm, regions_basm, ms_quota):
    r"""p_dataCopy(runr, "QUTS", "SUGB", YEARS): a NUTS 2 region's beet quota, its share of the regions' base quotas
    of the member state's.

    region_basm: the region's base quota; regions_basm: the regions' summed; ms_quota: the member state's of the
    year.

    CAPRI's GAMS (captrd/captrd_policy.gms l. 97-105):

            p_dataCopy(runr,"QUTS","SUGB",YEARS) $ ( p_dataCopy(MS,"QUTS","SUGB","BASM")
                                                    $ p_dataCopy(runr,"QUTS","SUGB","BASM")
                                                    $ p_dataCopy(MS,"QUTS","SUGB",YEARS))
             =
        *
        *      --- share of region on allocated quotas in base year
             p_dataCopy(runr,"QUTS","SUGB","BASM")  / SUM(runr1, p_dataCopy(runr1,"QUTS","SUGB","BASM"))
        *      --- times MS quota in current year
                      * p_dataCopy(MS,"QUTS","SUGB",YEARS);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return region_basm / regions_basm * ms_quota


def p_dataCopy_QUTS_SUGB_grof(ms_quota, region_grof, ms_grof):
    r"""p_dataCopy(runr, "QUTS", "SUGB", YEARS) of a region without a base quota: the member state's at the region's
    share of the base beet production.

    CAPRI's GAMS (captrd/captrd_policy.gms l. 109-115):

            p_dataCopy(runr,"QUTS","SUGB",YEARS)  $ ( p_dataCopy(MS,"QUTS","SUGB",YEARS)
                                                     $ (not p_dataCopy(runr,"QUTS","SUGB","BASM"))
                                                     $ p_dataCopy(MS,"GROF","SUGB","BASM"))
        *     --- MS quota in current year
              = p_dataCopy(MS,"QUTS","SUGB",YEARS)
        *     --- regional share on production in base year
                * p_dataCopy(runr,"GROF","SUGB","BASM")/p_dataCopy(MS,"GROF","SUGB","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return ms_quota * region_grof / ms_grof


def p_data_SETR_EU15(year, exante):
    r"""p_data(CurEUWestAgg, GRCU, "SETR", BASY / ExAnte): the EU-15's set-aside rate, 10% in the base year and the
    ex-ante years, none in the ex-ante years after 2007.

    year: the year; exante: it is an ex-ante year (the base year: not).

    CAPRI's GAMS (captrd/captrd_policy.gms l. 161-164):

            p_data(CurEUWestAgg,GRCU,"SETR",BASY)     = 10;
            p_data(CurEUWestAgg,GRCU,"SETR",ExAnte)   = 10;
        *pw But this deletion contradict the comment??
            p_data(CurEUWestAgg,GRCU,"SETR",YEARS) $ ((CALYEA(YEARS) GT CALYEA("2007")) AND ExAnte(YEARS)) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return 0.0 if (exante and year > 2007) else 10.0


def p_smallProdShare_fill(share_2009):
    r"""p_smallProdShare(exante, MS) without one: 2009's.

    CAPRI's GAMS (captrd/captrd_policy.gms l. 170-170):

            p_smallProdShare(exante,MS) $ (NOT p_smallProdShare(exante,MS)) = p_smallProdShare("2009",MS);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return share_2009


def p_data_SETR(eu15, eu15_base, shares, basm):
    r"""p_data(Rest, GRCU, "SETR", exAnte): the regions' rate, the EU-15's of the year scaled by their member states'
    small producers' shares (exempt from set-aside) and base rates, at most the EU-15's.

    eu15, eu15_base: the EU-15's rate of the year and of the base year; shares: (small producers' share of the base
    year, of the year) of the region's member states; basm: their base rates; both in the caller's order. Returns
    the rate (the EU-15's where the denominator is zero).

    CAPRI's GAMS (captrd/captrd_policy.gms l. 175-181):

            p_data(Rest,GRCU,"SETR",exAnte) $ (p_data("EU015000",GRCU,"SETR",exAnte) $ p_data(Rest,GRCU,"SETR","BASM"))
               = MIN(p_data("EU015000",GRCU,"SETR",exAnte),

                    p_data("EU015000",GRCU,"SETR",exAnte) * SUM( (MAP_RR(MS,Rest),BASY), (1. - MIN(p_smallProdShare(BASY, MS),p_smallProdShare(exAnte,MS))))

                       * SUM( MAP_RR(MS,Rest), p_data(MS,GRCU,"SETR","BASM"))
                         / SUM( BASY, p_data("EU015000",GRCU,"SETR",BASY) * SUM(MAP_RR(MS,Rest), (1. - p_smallProdShare(BASY,MS)))));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    num = eu15 * sum(1.0 - min(sb, st) for sb, st in shares)
    num *= sum(basm)
    den = eu15_base * sum(1.0 - sb for sb, _st in shares)
    return min(eu15, num / den) if den else eu15


def p_data_SETR_EU12_HR():
    r"""p_data(., GRCU, "SETR", exAnte) of the EU-12 (after 2007), Croatia (after 2012) and their members and regions:
    none (the EU-12's rate, zero).

    CAPRI's GAMS (captrd/captrd_policy.gms l. 186-193):

            p_data("EU015000","CERE","SETR",YEARS) $ ((CALYEA(YEARS) GT CALYEA("2007")) $ ExAnte(YEARS)) = 0;
            p_data("EU012000","CERE","SETR",YEARS) $ ((CALYEA(YEARS) GT CALYEA("2007")) $ ExAnte(YEARS)) = 0;
        *   set countries entering the EU after 2007 explicit to zero
            p_data("HR000000","CERE","SETR",YEARS) $ ((CALYEA(YEARS) GT CALYEA("2012")) $ ExAnte(YEARS)) = 0;
            p_data("HR000000",GRCU,"SETR",YEARS)   $ ((CALYEA(YEARS) GT CALYEA("2012")) $ ExAnte(YEARS)) = 0;

            p_data(MS,GRCU,"SETR",ExAnte) $ MAP_RR("EU012000",MS) = p_data("EU012000","CERE","SETR",exAnte);
            p_data(Rest,GRCU,"SETR",ExAnte) $ SUM(MAP_RR(MS,Rest) $ MAP_RR("EU012000",MS),1) = p_data("EU012000","CERE","SETR",exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.sugar_beet / set_aside)."""
    return 0.0

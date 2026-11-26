r"""The biofuel sector's expert supports: ex post, PRIMES's changes, trade, second generation, the new energy crops
(NECR), NAGR, PRCB (moved from capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations




def p_expertSupprt_expostT(value):
    r"""p_expertSupprt(MSIncl, S_colsEst, S_RowsEst, expostT, "Absolute"): p_data of the biofuel rows and columns.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 667-669):

             p_expertSupprt(MSIncl,S_colsEst,S_RowsEst,expostT,"Absolute") $ ( P_Result(MSIncl,S_colsEst,S_RowsEst,expostT,"P_DATA")
                                                                             $ (BiorowsCoco(s_rowsEst) or BioColsCoco(s_ColsEst)))
               = P_Result(MSIncl,S_colsEst,S_RowsEst,expostT,"P_DATA");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value


def p_expertSupprt_PRIMES_change(primes, pdata_base, primes_base):
    r"""p_expertSupprt(MSINCL, DOMM / MAPR, SECO_BIOF, exAnteT, "Absolute"): PRIMES's value moved by the difference
    of p_data and PRIMES in %BASprimes%, at least 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 677-679):

          p_expertSupprt(MSINCL,"DOMM",SECO_BIOF,exAnteT,"Absolute")
            = MAX(1e-14,p_primesResults(MSINCL,"DOMM",SECO_BIOF,exAnteT)
            + (P_Result(MSINCL,"DOMM",Seco_Biof,"%BASprimes%","P_DATA")-p_primesResults(MSINCL,"DOMM",SECO_BIOF,"%BASprimes%"))) ;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 693-695):

          P_expertSupprt(MSINCL,"MAPR",SECO_BIOF,exAnteT,"Absolute")
            = MAX(1e-14,p_primesResults(MSINCL,"MAPR",SECO_BIOF,exAnteT)
            + (P_Result(MSINCL,"MAPR",Seco_Biof,"%BASprimes%","P_DATA")-p_primesResults(MSINCL,"MAPR",SECO_BIOF,"%BASprimes%")) ) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1e-14, primes + (pdata_base - primes_base))


def P_expertSupprt_INDM(indm, domm):
    r"""P_expertSupprt(MSINCL, "INDM", SECO_BIOF, exAnteT, "Absolute"): PRIMES's industrial use, at most demand, at
    least 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 682-683):

          P_expertSupprt(MSINCL,"INDM",SECO_BIOF,exAnteT,"Absolute")
            = MAX(1e-14,MIN(p_primesResults(MSINCL,"INDM",SECO_BIOF,exAnteT),p_expertSupprt(MSINCL,"DOMM",SECO_BIOF,exAnteT,"Absolute")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1e-14, min(indm, domm))


def p_expertSupprt_BIOF_SECO_BIOF(domm, indm):
    r"""p_expertSupprt(MSINCL, "BIOF", SECO_BIOF, exAnteT, "Absolute"): demand less industrial use, at least
    1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 686-688):

          p_expertSupprt(MSINCL,"BIOF",SECO_BIOF,exAnteT,"Absolute")
            = MAX(1e-14,p_expertSupprt(MSINCL,"DOMM",SECO_BIOF,exAnteT,"Absolute")
                      - p_expertSupprt(MSINCL,"INDM",SECO_BIOF,exAnteT,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1e-14, domm - indm)


def P_expertSupprt_NTRD(mapr, biof, indm):
    r"""P_expertSupprt(MSINCL, "NTRD", SECO_BIOF, exAnteT, "Absolute"): production less biofuel and industrial
    use.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 810-813):

          P_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
            = P_expertSupprt(MSINCL,"MAPR",SECO_BIOF,exAnteT,"Absolute")
            - P_expertSupprt(MSINCL,"BIOF",SECO_BIOF,exAnteT,"Absolute")
            - P_expertSupprt(MSINCL,"INDM",SECO_BIOF,exAnteT,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr - biof - indm


def P_expertSupprt_NTRD_BASprimes(expt, impt):
    r"""P_expertSupprt(MSINCL, "NTRD", SECO_BIOF, "%BASprimes%", "Absolute"): p_data's exports less imports.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 815-816):

          P_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute")
            = P_Result(MSINCL,"EXPT",Seco_Biof,"%BASprimes%","P_DATA") - P_Result(MSINCL,"IMPT",Seco_Biof,"%BASprimes%","P_DATA") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return expt - impt


def p_expertSupprt_trade_up(base, ntrd, ntrd_base):
    r"""p_expertSupprt(MSINCL, "EXPT", SECO_BIOF, EXANTET, "Absolute") where net trade is at least %BASprimes%'s:
    p_data's exports plus the change of net trade.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 820-825):

          p_expertSupprt(MSINCL,"EXPT",SECO_BIOF,EXANTET,"Absolute")
             $ (   p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
                Ge p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"))
            = P_Result(MSINCL,"EXPT",Seco_Biof,"%BASprimes%","P_DATA")
            + (  p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
               - p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return base + (ntrd - ntrd_base)


def p_expertSupprt_trade_down(base, ntrd, ntrd_base):
    r"""p_expertSupprt(MSINCL, "IMPT", SECO_BIOF, EXANTET, "Absolute") where net trade is below %BASprimes%'s:
    p_data's imports less the change of net trade.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 832-837):

          p_expertSupprt(MSINCL,"IMPT",SECO_BIOF,EXANTET,"Absolute")
             $ (   p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
                LT p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"))
            = P_Result(MSINCL,"IMPT",Seco_Biof,"%BASprimes%","P_DATA")
            - (  p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
               - p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return base - (ntrd - ntrd_base)


def p_expertSupprt_trade_base(base):
    r"""p_expertSupprt(MSINCL, IMPT / EXPT, SECO_BIOF, EXANTET, "Absolute") on the other side: p_data's %BASprimes%
    imports or exports.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 827-830):

          p_expertSupprt(MSINCL,"IMPT",SECO_BIOF,EXANTET,"Absolute")
             $ (   p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
                Ge p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"))
            = P_Result(MSINCL,"IMPT",Seco_Biof,"%BASprimes%","P_DATA");

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 839-842):

          p_expertSupprt(MSINCL,"EXPT",SECO_BIOF,EXANTET,"Absolute")
            $ (   p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,exAnteT,"Absolute")
               LT p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute"))
            = P_Result(MSINCL,"EXPT",Seco_Biof,"%BASprimes%","P_DATA") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return base


def p_expertSupprt_NTRD_BASprimes_removed():
    r"""p_expertSupprt(MSINCL, "NTRD", SECO_BIOF, "%BASprimes%", "Absolute"): removed once used.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 844-844):

          p_expertSupprt(MSINCL,"NTRD",SECO_BIOF,"%BASprimes%","Absolute") = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 0.0


def p_expertSupprt_SECG(mapr, share):
    r"""p_expertSupprt(MSINCL, "SECG", BIOD / BIOE, exAnteT, "Absolute"): production times PRIMES's second generation
    share, at least 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 855-858):

          p_expertSupprt(MSINCL,"SECG","BIOD",exAnteT,"Absolute")
        *     Note: minimum value triggers fixation to zero in biofuel_bounds.gms
            = MAX(1.E-14,  p_expertSupprt(MSINCL,"MAPR","BIOD",exAnteT,"Absolute")
                         * p_primesResults(MSINCL,"biodShare","SECG",exAnteT)      );

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 860-862):

          p_expertSupprt(MSINCL,"SECG","BIOE",exAnteT,"Absolute")
            = MAX(1.E-14,  p_expertSupprt(MSINCL,"MAPR","BIOE",exAnteT,"Absolute")
                         * p_primesResults(MSINCL,"bioeShare","SECG",exAnteT)      );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1e-14, mapr * share)


def p_expertSupprt_NECR_LEVL(tset, lign):
    r"""p_expertSupprt(MSINCL, "NECR", "LEVL", exAnteT, "Absolute") where PRIMES has lignocellulosic crops: Step 1's
    set-aside (not below zero) plus PRIMES's area.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 867-873):

          p_expertSupprt(MSINCL,"NECR","LEVL",exAnteT,"Absolute") $  p_primesResults(MSINCL,"LIGN","LEVL",exAnteT)
            = MAX(0,P_Result(MSINCL,"TSET","LEVL",exAnteT,"step1"))
            + p_primesResults(MSINCL,"LIGN","LEVL",exAnteT) * (1
        * --  For Ecampa2 baseline it appears useful to introduce a cut factor (declining from ~0.9 in 2020 to ~0.5 in 2050)
        $ifi %aglinkTightLink%==on                              -0.99**max(0,(calyea(exanteT)-calyea("2015"))*2)
        $ifi %stronglycutNECR%==on                              -0.999**max(0,(calyea(exanteT)-calyea("2015"))*2)
                                                              );

    Departures from CAPRI: the factor (1) is not written (%aglinkTightLink% and %stronglycutNECR% off: their cut factors are not in the
    reference run); the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return max(0.0, tset) + lign


def p_expertSupprt_NECR_LEVL_EPS():
    r"""p_expertSupprt(MSINCL, "NECR", "LEVL", exAnteT, "Absolute") without a value where another ex-ante year has
    one: EPS (the caller stores it as such).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 877-879):

          p_expertSupprt(MSINCL,"NECR","LEVL",exAnteT,"Absolute")
            $ (    (NOT p_expertSupprt(MSINCL,"NECR","LEVL",exAnteT,"Absolute"))
               and SUM(exAnte1, p_expertSupprt(MSINCL,"NECR","LEVL",exante1,"Absolute"))) = EPS;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 0.0


def p_expertSupprt_NECR_LEVL_NT2Est(pairs, uaar):
    r"""p_expertSupprt(NT2Est, "NECR", "LEVL", exante, "Absolute") of a NUTS 2 region not a member state: its member
    state's new energy crops per ha of UAAR times its own UAAR (BASM).

    pairs: (the member state's level, its UAAR) of those with UAAR.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 883-889):

          p_expertSupprt(NT2Est,"NECR","LEVL",exante,"Absolute")
           $ ( (NOT SUM(SAMEAS(NT2Est,MS),1)) and (SUM(MS $ MAP_RR(MS,NT2Est),
                          p_result(MS,"UAAR","LEVL",exante,"BASM"))))
           = SUM(MAP_RR(MS,NT2Est),
                   p_expertSupprt(MS,"NECR","LEVL",exante,"Absolute")
                  /p_result(MS,"UAAR","LEVL",exante,"BASM"))
             * p_result(NT2Est,"UAAR","LEVL",exante,"BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(v / u for v, u in pairs) * uaar


def p_expertSupprt_NECR_LEVL_TrustLevl():
    r"""p_expertSupprt(rEst, "NECR", "LEVL", exante, "TrustLevl") where there is a level: 10.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 892-893):

          p_expertSupprt(rEst,"NECR","LEVL",exante,"TrustLevl")
            $  p_expertSupprt(rEst,"NECR","LEVL",exante,"Absolute") = 10;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 10.0


def p_expertSupprt_NECR_OCRO():
    r"""p_expertSupprt(rEst, "NECR", "OCRO", exante, "Absolute") where there is a level: the revenue, 250 EUR/ha.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 898-899):

          p_expertSupprt(rEst,"NECR","OCRO",exante,"Absolute")
            $    p_expertSupprt(rEst,"NECR","LEVL",exante,"Absolute") = 250;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 250.0


def P_DATA_nObs(support, nobs):
    r"""P_DATA(., "nObs") = 1 of the new series: where there is an ex-ante support (the new energy crops' level for
    their LEVL and OCRO; the feedstock use for PRCB and PRCBY) and no nObs yet. Returns whether nObs is set.

    support: whether the series has an ex-ante support; nobs: whether it has nObs already (False for l. 901-902,
    which do not test it).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 901-901):

          P_DATA(rEst,"NECR","LEVL","nObs") $ (SUM(exAnte,p_expertSupprt(rEst,"NECR","LEVL",exAnte,"Absolute"))) = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 902-902):

          P_DATA(rEst,"NECR","OCRO","nObs") $ (SUM(exAnte,p_expertSupprt(rEst,"NECR","LEVL",exAnte,"Absolute"))) = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1464-1465):

          P_DATA(MSIncl,COLS,SECO_BIOF,"nObs") $ (    SUM(exAnte,p_expertSupprt(MSIncl,COLS,SECO_BIOF,exAnte,"Absolute"))
                                                and (NOT P_DATA(MSIncl,COLS,SECO_BIOF,"nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1467-1468):

          P_DATA(MSIncl,COLS,"DDGS","nObs") $ (    SUM(exAnte,p_expertSupprt(MSIncl,COLS,"DDGS",exAnte,"Absolute"))
                                                and (NOT P_DATA(MSIncl,COLS,"DDGS","nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1470-1471):

          P_DATA(MSIncl,COLS,Fuel_rows,"nObs") $ (    SUM(exAnte,p_expertSupprt(MSIncl,COLS,Fuel_rows,exAnte,"Absolute"))
                                                and (NOT P_DATA(MSIncl,COLS,fuel_rows,"nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1473-1474):

          P_DATA(MSIncl,"BIOF",bioStock,"nObs") $ (    SUM(exAnte,p_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                                                and (NOT  P_DATA(MSIncl,"BIOF",bioStock,"nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1476-1477):

          P_DATA(MSIncl,"BIOF","CERE","nObs")   $ (    SUM(exAnte,p_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"Absolute"))
                                                and (NOT  P_DATA(MSIncl,"BIOF","CERE","nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1479-1480):

          P_DATA(MSIncl,"PRCB",bioStock,"nObs") $ (    SUM(exAnte,p_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                                                and (NOT  P_DATA(MSIncl,"PRCB",bioStock,"nObs")))= 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1482-1483):

          P_DATA(MSIncl,"PRCBY",bioStock,"nObs") $ (   SUM(exAnte,p_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                                                   and (NOT  P_DATA(MSIncl,"PRCBY",bioStock,"nObs")))= 1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return bool(support) and not nobs


def P_expertSupprt_NAGR(pdata_base, primes, primes_base, mapr, share):
    r"""P_expertSupprt(MSINCL, "NAGR", BIOE / BIOD, exAnteT, "Absolute") where PRIMES has non-agricultural fuels:
    p_data's %BASprimes% moved by PRIMES's change, at most production times PRIMES's share, at least 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 945-950):

          P_expertSupprt(MSINCL,"NAGR","BIOE",exAnteT,"Absolute") $ p_primesResults(MSINCL,"NAGR","BIOE",exAnteT)
            =  MAX(1e-14,MIN(   P_Result(MSINCL,"NAGR","BIOE","%BASprimes%","P_DATA")
                             +  p_primesResults(MSINCL,"NAGR","BIOE",exAnteT)
                             -  p_primesResults(MSINCL,"NAGR","BIOE","%BASprimes%"),
                                p_expertSupprt(MSINCL,"MAPR","BIOE",exAnteT,"Absolute")
                              * p_primesResults(MSINCL,"bioeShare","NAGR",exAnteT)));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 952-957):

          P_expertSupprt(MSINCL,"NAGR","BIOD",exAnteT,"Absolute") $ p_primesResults(MSINCL,"NAGR","BIOD",exAnteT)
            =  MAX(1e-14,MIN(   P_Result(MSINCL,"NAGR","BIOD","%BASprimes%","P_DATA")
                             +  p_primesResults(MSINCL,"NAGR","BIOD",exAnteT)
                             -  p_primesResults(MSINCL,"NAGR","BIOD","%BASprimes%"),
                                p_expertSupprt(MSINCL,"MAPR","BIOD",exAnteT,"Absolute")
                              * p_primesResults(MSINCL,"biodShare","NAGR",exAnteT)));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1e-14, min(pdata_base + primes - primes_base, mapr * share))


def P_expertSupprt_PRCB(extr_rates, yields):
    r"""P_expertSupprt(MSINCL, "PRCB", bioStock, exante, "Absolute") without a value: the extraction rates summed over
    the fuels, moved by Aglink's yield changes (p_BFyld against %BASprimes%) of the feedstock's group (wheat, coarse
    grains, sugar beet, vegetable oils).

    extr_rates: p_extrRates over SECO_BIOF; yields: (p_BFyld of the year, of %BASprimes%) of each group the stock is
    in.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 986-992):

          P_expertSupprt(MSINCL,"PRCB",bioStock,exante,"Absolute") $ (NOT P_expertSupprt(MSINCL,"PRCB",bioStock,exante,"Absolute"))
            =  sum(seco_bioF,p_extrRates(seco_bioF,bioStock))
              * (1 + (p_BFyld('WT','ET',exante)/p_BFyld('WT','ET',"%BASprimes%")-1) $ SAMEAS(bioStock,"SWHE")
                   + (p_BFyld('CG','ET',exante)/p_BFyld('CG','ET',"%BASprimes%")-1) $ (SAMEAS(bioStock,"BARL") or SAMEAS(bioStock,"RYEM") or SAMEAS(bioStock,"OATS")
                                                                               or SAMEAS(bioStock,"OCER") or SAMEAS(bioStock,"MAIZ"))
                   + (p_BFyld('SBE','ET',exante)/p_BFyld('SBE','ET',"%BASprimes%")-1) $ SAMEAS(bioStock,"SUGA")
                   + (p_BFyld('VL','BD',exante)/p_BFyld('VL','BD',"%BASprimes%")-1) $ bioStockOilP(bioStock));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    f = 1.0
    for y, b in yields:
        f += y / b - 1
    return sum(extr_rates) * f


def P_expertSupprt_PRCBY(byproducts):
    r"""P_expertSupprt(MSINCL, "PRCBY", bioStock, exAnte, "Absolute") without a value: the by-products' yields
    (p_byProduct) summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 995-996):

          P_expertSupprt(MSINCL,"PRCBY",bioStock,exAnte,"Absolute") $ (NOT P_expertSupprt(MSINCL,"PRCBY",bioStock,exAnte,"Absolute"))
            =  sum(Bio_By,p_byProduct(bio_By,bioStock));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(byproducts)


def P_expertSupprt_PRCB_after_lst_dgagri(last, base, year, lst_dgagri, base_year):
    r"""P_expertSupprt(MSINCL, "PRCB", bioStock, exAnteT, "Absolute") after %lst_dgagri%: its last value extrapolated
    by the change since 2020 (else the first ex-ante year), where it has one.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1001-1008):

          P_expertSupprt(MSINCL,"PRCB",bioStock,exAnteT,"Absolute") $ (  ( CALYEA(exAnteT) GT SUM(Lst_DgAgri, CALYEA(Lst_DgAgri)) )
                                                                     and SUM(Lst_DgAgri, P_expertSupprt(MSINCL,"PRCB",bioStock,Lst_DgAgri,"Absolute")))
            = SUM(Lst_DgAgri, P_expertSupprt(MSINCL,"PRCB",bioStock,Lst_DgAgri,"Absolute"))
            * (1 + (SUM(Lst_DgAgri, P_expertSupprt(MSINCL,"PRCB",bioStock,Lst_DgAgri,"Absolute"))
                   /( P_expertSupprt(MSINCL,"PRCB",bioStock,"2020","Absolute")                     $ (    exanteT("2020"))
                    + sum(fst_exante,P_expertSupprt(MSINCL,"PRCB",bioStock,fst_exante,"Absolute")) $ (not exanteT("2020")))- 1)
                 * (ordt(EXANTET) - ordT("%lst_dgagri%"))
                 / ( ordT("%lst_dgagri%") - ordT("2020") $ exanteT("2020") - ordT("Fst_exAnte")  $ (not exanteT("2020"))));

    Departures from CAPRI: CAPRI's ordT differences are taken as the calendar years' (the time set has every year); the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return last * (1 + (last / base - 1) * (year - lst_dgagri) / (lst_dgagri - base_year))


def P_expertSupprt_PRCBY_after_lst_dgagri(last):
    r"""P_expertSupprt(MSINCL, "PRCBY", bioStock, exAnteT, "Absolute") after %lst_dgagri%: its last value.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1010-1011):

          P_expertSupprt(MSINCL,"PRCBY",bioStock,exAnteT,"Absolute") $ (CALYEA(exAnteT) GT SUM(Lst_DgAgri, CALYEA(Lst_DgAgri)) )
            = SUM(Lst_DgAgri, P_expertSupprt(MSINCL,"PRCBY",bioStock,Lst_DgAgri,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return last


def p_expertSupprt_BIOF_TWIN(value):
    r"""p_expertSupprt(MSIncl, "BIOF", "TWIN", exAnteT, "Absolute"): p_data's ethanol from wine of %BASprimes%.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1073-1073):

          p_expertSupprt(MSIncl,"BIOF","TWIN",exAnteT,"Absolute") = P_Result(MSIncl,"BIOF","TWIN","%BASprimes%","P_DATA");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value


def p_expertSupprt_BIOF_SUGA(base, suga, suga_base, prcb):
    r"""p_expertSupprt(MSIncl, "BIOF", "SUGA", exanteT, "Absolute") with a processing coefficient (no supports from
    KWS): %BASprimes%'s sugar use plus PRIMES's change of sugar ethanol over the coefficient, not below zero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1109-1112):

             p_expertSupprt(MSIncl,"BIOF","SUGA",exanteT,"Absolute") $  p_expertSupprt(MSIncl,"PRCB","SUGA",exAnteT,"Absolute")
                 = Max(0,   p_expertSupprt(MSIncl,"BIOF","SUGA","%BASprimes%","Absolute")
                         + (p_primesResults(MSIncl,"SUGA","BIOE",exanteT) - p_primesResults(MSIncl,"SUGA","BIOE","%BASprimes%"))
                          / p_expertSupprt(MSIncl,"PRCB","SUGA",exAnteT,"Absolute"))  ;

    Departures from CAPRI: KWS's branch (l. 1077-1103, where an ex-ante sugar use is already there) is not ported: not reached in the
    reference run (the caller raises); the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return max(0.0, base + (suga - suga_base) / prcb)

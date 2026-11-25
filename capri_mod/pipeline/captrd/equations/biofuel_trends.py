r"""CAPTRD's statements of biofuel/biofuel_trends.gms (CAPRI star 3.0, included by captrd/expert_support.gms
l. 108 with %NewBiofuelModule% on): PRIMES's biofuel results aggregated, filled and shared out (p_primesResults), and
the expert supports of the biofuel sector built from them (p_expertSupprt's Absolute and TrustLevl, p_data's nObs), as
named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/biofuel_trends.py (trends) holds the loops over the
regions, the positions and the years, the data and the conditions (with the values from before each statement where
its right side reads what it assigns), and calls them; the arithmetic is the port's, so the trends are unchanged.
"""
from __future__ import annotations


def p_primesResults(values):
    r"""p_primesResults(primesMS, pCols, pRows, pYears): PRIMES's results summed over the units and the auxiliary
    columns and rows mapped to the position.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 339-341):

          p_primesResults(primesMS,pCols,pRows,pYears) $ CARD(p_primeswithunits)
            = SUM((allUnit,aux_to_pRows(auxRows,pRows),aux_to_pCols(auxCols,pCols)),
                  p_primesWithUnits(primesMS,auxCols,auxRows,allUnit,pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(values)


def p_primesResults_NTRD(imports):
    r"""p_primesResults(primesMS, "NTRD", pRows, pYears): minus the imports, summed over the units and auxiliary
    rows.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 344-346):

          p_primesResults(primesMS,"NTRD",pRows,pYears) $ CARD(p_primeswithunits)
            = - SUM((allUnit,aux_to_pRows(auxRows,pRows)),
                  p_primesWithUnits(primesMS,"IMPT",auxRows,allUnit,pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return -sum(imports)


def p_primesWithUnits_OILS_kton(ktoe):
    r"""p_primesWithUnits(primesMS, "BIOF", "OILS", "kton", pYears): the biodiesel from oils in 1000 t of rape seed
    (41.9 GJ per toe, 26.5 GJ/t).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 357-358):

          p_primesWithUnits(primesMS,"BIOF","OILS","kton",pYears)
            = p_primesWithUnits(primesMS,"BIOF","OILS","ktoe",pYears)*41.9/26.5;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ktoe * 41.9 / 26.5


def p_primesWithUnits_VOIL_ktoe(oils_kton, rapo_yield, impt_voil):
    r"""p_primesWithUnits(primesMS, "BIOF", "VOIL", "ktoe", pYears): the rape oil from the seed (its processing yield,
    37.2 GJ/t) plus the imported vegetable oil, not below zero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 361-364):

          p_primesWithUnits(primesMS,"BIOF","VOIL","ktoe",pYears)
            = MAX(0, p_primesWithUnits(primesMS,"BIOF","OILS","kton",pYears) * Proc_Yields("RAPO") *37.2/41.9
        *            NOTE: possibly negative imports = export require max(,) operator above
                   + p_primesWithUnits(primesMS,"IMPT","VOIL","ktoe",pYears)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(0.0, oils_kton * rapo_yield * 37.2 / 41.9 + impt_voil)


def p_primesResults_BIOF_oil(ktoe):
    r"""p_primesResults(primesMS, "BIOF", VOIL / WOIL, pYears): vegetable and waste oil in 1000 t (37.2 GJ/t).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 367-368):

          p_primesResults(primesMS,"BIOF",pRows,pYears) $ (CARD(p_primeswithunits) $ (sameas(pRows,"VOIL") or sameas(pRows,"WOIL") ))
            = p_primesWithUnits(primesMS,"BIOF",pRows,"ktoe",pYears) *41.9/37.2;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ktoe * 41.9 / 37.2


def p_primesResults_SECG_BIOD(mapr, nonfungi):
    r"""p_primesResults(primesMS, "SECG", "BIOD", pYears): second generation biodiesel, production less the
    transesterification of non-fungible stocks, not below zero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 373-374):

          p_primesResults(primesMS,"SECG","BIOD",pYears) $ CARD(p_primeswithunits)
            = MAX(0,p_primesResults(primesMS,"MAPR","BIOD",pYears) - p_primesWithUnits(primesMS,"Transest","Nonfungi","ktoe",pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(0.0, mapr - nonfungi)


def p_primesResults_SECG_BIOE(mapr, bioethan, fst, allf):
    r"""p_primesResults(primesMS, "SECG", "BIOE", pYears): second generation ethanol, production less the fermentation
    of ethanol, times one less the first generation stocks' share of all fermentation stocks (where any), not below
    zero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 377-384):

          p_primesResults(primesMS,"SECG","BIOE",pYears) $ CARD(p_primeswithunits)
            = MAX(0,(p_primesResults(primesMS,"MAPR","BIOE",pYears)
        *            In the format as of 2012 "Fermenta","Bioethan" gives 1st gen production, whereas it is empty in the pre 2012 format
                   - p_primesWithUnits(primesMS,"Fermenta","Bioethan","ktoe",pYears))
        *            In the format pre 2012 we have capacities for allFermentaStocks, which are empty as of 2012
                   * (1 - ( SUM(fstGFermentaStocks ,p_primesWithUnits(primesMS,"Fermenta",fstGFermentaStocks,"ktoe",pYears))
                          / SUM(allFermentaStocks  ,p_primesWithUnits(primesMS,"Fermenta",allFermentaStocks,"ktoe",pYears)))
                          $ SUM(allFermentaStocks  ,p_primesWithUnits(primesMS,"Fermenta",allFermentaStocks,"ktoe",pYears)) ) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(0.0, (mapr - bioethan) * (1 - ((fst / allf) if allf else 0.0)))


def p_primesResults_expostT_first_gen(value, secg):
    r"""p_primesResults(primesMS, "MAPR" / "DOMM", "BIOE", expostT): ethanol production and demand of the ex-post
    years net of the second generation.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 390-391):

          p_primesResults(primesMS,"MAPR","BIOE",expostT)
            = p_primesResults(primesMS,"MAPR","BIOE",expostT) - p_primesResults(primesMS,"SECG","BIOE",expostT) ;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 392-393):

          p_primesResults(primesMS,"DOMM","BIOE",expostT)
            = p_primesResults(primesMS,"DOMM","BIOE",expostT) - p_primesResults(primesMS,"SECG","BIOE",expostT) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value - secg


def p_primesResults_SECG_BIOE_expostT():
    r"""p_primesResults(primesMS, "SECG", "BIOE", expostT): no second generation ethanol in the ex-post years.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 394-394):

          p_primesResults(primesMS,"SECG","BIOE",expostT) = 0 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 0.0


def p_primesResults_bioeShare_SECG(secg, mapr):
    r"""p_primesResults(primesMS, "bioeShare", "SECG", pYears): the second generation's share of ethanol production,
    where there is production.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 396-397):

          p_primesResults(primesMS,"bioeShare","SECG",pYears) $ (p_primesResults(primesMS,"MAPR","BIOE",pYears) $ CARD(p_primeswithunits))
            = p_primesResults(primesMS,"SECG","BIOE",pYears) / p_primesResults(primesMS,"MAPR","BIOE",pYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return secg / mapr


def p_primesResults_bioeShare_stocks(biof, cere, suga, share_secg):
    r"""p_primesResults(primesMS, "bioeShare", SUGA / CERE, pYears): the feedstock's share of the cereal and sugar
    ethanol, times the first generation's share (one less the second generation's, at least 0.05).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 400-406):

          p_primesResults(primesMS,"bioeShare",pRows,pyears) $ ( (SAMEAS(pRows,"SUGA") or SAMEAS(pRows,"CERE"))
                                                         $ (  p_primesWithUnits(primesMS,"BIOF","CERE","ktoe",pYears)
                                                            + p_primesWithUnits(primesMS,"BIOF","SUGA","ktoe",pYears)))
            = p_primesWithUnits(primesMS,"BIOF",pRows,"ktoe",pYears)
            /(p_primesWithUnits(primesMS,"BIOF","CERE","ktoe",pYears) + p_primesWithUnits(primesMS,"BIOF","SUGA","ktoe",pYears))
        *   for fesibility reasons, we maintain at least 5% first generation biofuels.
            *MAX(0.05,1.-p_primesResults(primesMS,"bioeShare","SECG",pyears));

    Departures from CAPRI: CAPRI divides by the sum of the feedstocks' p_primesWithUnits; the port by the same sum, computed by the caller in
    the same order; the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return biof / (cere + suga) * max(0.05, 1.0 - share_secg)


def p_primesResults_fossil(primes, fossil, primes_base):
    r"""p_primesResults(primesMS, "HCOM" / "UVAP", fossilFuels, pYears): PRIMES's demand (ktoe) or price (EUR per toe)
    of the fossil fuel, plus fossilFuel.gdx's where PRIMES has none in %BASprimes%.

    primes_base: whether PRIMES has a value in %BASprimes%.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 415-418):

          p_primesResults(primesMS,"HCOM",fossilFuels,pYears)
             =   SUM(sameas(pRows,fossilfuels),p_primesWithUnits(primesMS,"HCOM",pRows,"ktoe",pYears))
             +   p_fossilFuel(primesMS,"DOMM",fossilFuels,pYears)
                 $ (Not SUM(sameas(pRows,fossilfuels),p_primesWithUnits(primesMS,"HCOM",pRows,"ktoe","%BASprimes%")));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 420-423):

          p_primesResults(primesMS,"UVAP",fossilFuels,pYears)
             =   SUM(sameas(pRows,fossilfuels),p_primesWithUnits(primesMS,"UVAP",pRows,"europertoe",pYears))
             +   p_fossilFuel(primesMS,"UVAP",fossilFuels,pYears)
                 $ (Not SUM(sameas(pRows,fossilfuels),p_primesWithUnits(primesMS,"UVAP",pRows,"europertoe","%BASprimes%")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return primes + (fossil if not primes_base else 0.0)


def p_primesResults_CTAX(ctax):
    r"""p_primesResults(primesMS, "CTAX", fossilFuels, pYears): PRIMES's excise tax (EUR per toe).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 425-426):

          p_primesResults(primesMS,"CTAX",fossilFuels,pYears)
             =   SUM(sameas(pRows,fossilfuels),p_primesWithUnits(primesMS,"CTAX",pRows,"europertoe",pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ctax


def p_primesResults_CTAX_2015(ctax_2010, ctax_2020):
    r"""p_primesResults(primesMS, "CTAX", fossilFuels, "2015") above 1.5 x the mean of 2010 and 2020: that mean.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 430-433):

          p_primesResults(primesMS,"CTAX",fossilFuels,"2015")
             $ (  p_primesResults(primesMS,"CTAX",fossilFuels,"2015") gt
                 (1.5*(p_primesResults(primesMS,"CTAX",fossilFuels,"2010")+p_primesResults(primesMS,"CTAX",fossilFuels,"2020"))/2))
             = (p_primesResults(primesMS,"CTAX",fossilFuels,"2010")+p_primesResults(primesMS,"CTAX",fossilFuels,"2020"))/2 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return (ctax_2010 + ctax_2020) / 2


def p_primesResults_BL(be, lu, share):
    r"""p_primesResults("BL000000", pCols, pRows, pYears): Belgium plus Luxembourg (Belgium's alone for the shares,
    bioeShare).

    share: the column is bioeShare.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 439-441):

          p_primesResults("BL000000",pCols,pRows,pYears)
              = p_primesResults("BE000000",pCols,pRows,pYears)
              + p_primesResults("LU000000",pCols,pRows,pYears) $ (NOT SAMEAS(pCols,"bioeShare"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return be + (lu if not share else 0.0)


def p_primesResults_BL_price(price_be, hcom_be, price_lu, hcom_lu):
    r"""p_primesResults("BL000000", UVAP / CTAX, fossilFuels, pYears): Belgium's and Luxembourg's prices and taxes
    weighted by their demand, where there is demand.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 443-449):

          p_primesResults("BL000000",pCols,fossilFuels,pYears)
              $ (  (  p_primesResults("BE000000","HCOM",fossilFuels,pYears)
                    + p_primesResults("LU000000","HCOM",fossilFuels,pYears))
                 $ (sameas(pCols,"UVAP") or sameas(pCols,"CTAX") ))
              = (p_primesResults("BE000000",pCols,fossilFuels,pYears) * p_primesResults("BE000000","HCOM",fossilFuels,pYears)
               + p_primesResults("LU000000",pCols,fossilFuels,pYears) * p_primesResults("LU000000","HCOM",fossilFuels,pYears))
              / (p_primesResults("BE000000","HCOM",fossilFuels,pYears) + p_primesResults("LU000000","HCOM",fossilFuels,pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return (price_be * hcom_be + price_lu * hcom_lu) / (hcom_be + hcom_lu)


def p_primesResults_scaleCols(value, oil_equ):
    r"""p_primesResults(MS, scaleCols, Fuels, pYears): the fuel quantities from ktoe to 1000 t (p_oilEqu).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 459-460):

          p_primesResults(MS,scaleCols,Fuels,pYears)
            = p_primesResults(MS,scaleCols,Fuels,pYears) / p_oilEqu(Fuels);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value / oil_equ


def p_primesResults_gap(values, year):
    r"""p_primesResults(MSall, pCols, pRows, pyears) without a value, with values before and after it: the mean of
    the series' values weighted by 1 / (distance in years squared + 0.01).

    values: the series' values by year, in the order of pYears (those from before the statement).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 482-492):

          p_primesResults(MSall,pCols,pRows,pyears) $ (     (NOT p_primesResults(MSall,pCols,pRows,pyears))
                                                     and Sum(pYears1 $ (    p_primesResults(MSall,pCols,pRows,pYears1)
                                                                       and (CALYEA(pYears1) GT CALYEA(pYears))),1)
                                                     and Sum(pYears1 $ (    p_primesResults(MSall,pCols,pRows,pYears1)
                                                                       and (CALYEA(pYears1) LT CALYEA(pYears))),1))

            =  SUM( (pyears1) $ p_primesResults(MSall,pCols,pRows,pyears1),
        *                                      with wgt decreasing with distance from T=pyears...
                              p_primesResults(MSall,pCols,pRows,pyears1)/(SQR(ABS(CALYEA(pyears1)-CALYEA(pyears)))+.01))
             / SUM( (pyears1) $ p_primesResults(MSall,pCols,pRows,pyears1),
                                            1.0/(SQR(ABS(CALYEA(pyears1)-CALYEA(pyears)))+.01));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    num = sum(v / ((y1 - year) ** 2 + 0.01) for y1, v in values.items())
    den = sum(1.0 / ((y1 - year) ** 2 + 0.01) for y1 in values)
    return num / den


def p_primesResults_Fillyears(value, value_next, year, year_next, fill_year):
    r"""p_primesResults(MSall, pCols, pRows, Fillyears) of a series with values: linear interpolation between PRIMES's
    year and the next (the years up to the last with biodiesel production).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 501-505):

             p_primesResults(MSall,pCols,pRows,Fillyears) $ SUM( (pyears1) $ p_primesResults(MSall,pCols,pRows,pyears1),1)
             =  p_primesResults(MSall,pCols,pRows,pYears)
             +  (CALYEA(Fillyears)-CALYEA(pYears))
             *  (p_primesResults(MSall,pCols,pRows,pYears+1) - p_primesResults(MSall,pCols,pRows,pYears))
             /  (CALYEA(pyears+1)-CALYEA(pYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value + (fill_year - year) * (value_next - value) / (year_next - year)


def p_primesResults_bioeShare_SECG_max(share):
    r"""p_primesResults(MS, "bioeShare", "SECG", yearsCur): the second generation's share at most 95%.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 512-513):

          p_primesResults(MS,"bioeShare","SECG",yearsCur)
            = MIN(0.95,p_primesResults(MS,"bioeShare","SECG",yearsCur));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return min(0.95, share)


def p_primesResults_share(value, mapr):
    r"""p_primesResults(MS, "biodShare" / "bioeShare", "SECG" / "NAGR", yearsCur): the second generation's or the
    non-agricultural fuels' share of production, at most 95%, where there is production.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 515-516):

          p_primesResults(MS,"biodShare","SECG",yearsCur) $ p_primesResults(MS,"MAPR","BIOD",yearsCur)
            = MIN(0.95,p_primesResults(MS,"SECG","BIOD",yearsCur)/p_primesResults(MS,"MAPR","BIOD",yearsCur));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 538-539):

          p_primesResults(MS,"bioeShare","SECG",yearsCur) $ p_primesResults(MS,"MAPR","BIOE",yearsCur)
            = MIN(0.95,p_primesResults(MS,"SECG","BIOE",yearsCur)/p_primesResults(MS,"MAPR","BIOE",yearsCur));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 541-542):

          p_primesResults(MS,"bioeShare","NAGR",yearsCur) $ p_primesResults(MS,"MAPR","BIOE",yearsCur)
            = MIN(0.95,p_primesResults(MS,"NAGR","BIOE",yearsCur)/p_primesResults(MS,"MAPR","BIOE",yearsCur));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 591-592):

          p_primesResults(MS,"biodShare","NAGR",yearsCur) $ p_primesResults(MS,"MAPR","BIOD",yearsCur)
            = MIN(0.95,p_primesResults(MS,"NAGR","BIOD",yearsCur)/p_primesResults(MS,"MAPR","BIOD",yearsCur));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return min(0.95, value / mapr)


def p_primesResults_P_DATA(value):
    r"""p_primesResults(MSALL, "NAGR", "BIOE" / "INDM", SECO_BIOF, expostT / exanteT): p_data's non-agricultural
    ethanol and industrial use (the last ex-post year's for the ex-ante years).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 523-523):

          p_primesResults(MSALL,"NAGR","BIOE",expostT) =  P_Result(MSALL,"NAGR","BIOE",expostT,"P_DATA");

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 524-524):

          p_primesResults(MSALL,"NAGR","BIOE",exanteT) =  sum(Lst_ExpostT,P_Result(MSALL,"NAGR","BIOE",Lst_ExpostT,"P_DATA"));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 596-596):

          p_primesResults(MSALL,"INDM",SECO_BIOF,expostT) =  P_Result(MSALL,"INDM",SECO_BIOF,expostT,"P_DATA");

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 597-597):

          p_primesResults(MSALL,"INDM",SECO_BIOF,exanteT)   =  sum(Lst_ExpostT,P_Result(MSALL,"INDM",SECO_BIOF,Lst_ExpostT,"P_DATA"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value


def p_primesResults_from_share(mapr, share):
    r"""p_primesResults(MS, "SECG" / "SUGA", "BIOE", yearsCur): ethanol production times the second generation's or
    sugar's share.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 530-531):

          p_primesResults(MS,"SECG","BIOE",yearsCur)
            = p_primesResults(MS,"MAPR","BIOE",yearsCur)*p_primesResults(MS,"bioeShare","SECG",yearsCur) ;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 641-642):

          p_primesResults(MS,"SUGA","BIOE",yearsCur)
            = p_primesResults(MS,"MAPR","BIOE",yearsCur)* p_primesResults(MS,"bioeShare","SUGA",yearsCur);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr * share


def p_primesResults_MAPR_BIOE(mapr, nagr):
    r"""p_primesResults(MS, "MAPR", "BIOE", yearsCur): ethanol production with the non-agricultural ethanol.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 534-535):

          p_primesResults(MS,"MAPR","BIOE",yearsCur)
            = p_primesResults(MS,"MAPR","BIOE",yearsCur) + p_primesResults(MS,"NAGR","BIOE",yearsCur) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr + nagr


def p_primesResults_bioeShare_stocks_MS(share, shares, share_secg, share_nagr):
    r"""p_primesResults(MS, "bioeShare", SUGA / CERE, yearsCur): the feedstock's share of the cereal and sugar shares,
    times the first generation's share (one less the second generation's and the non-agricultural's, at least 0.05).

    shares: the cereal and sugar shares summed, from before the statement.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 544-550):

          p_primesResults(MS,"bioeShare",pRows,yearsCur) $ ( (SAMEAS(pRows,"SUGA") or SAMEAS(pRows,"CERE"))
                                                         $ (  p_primesResults(MS,"bioeShare","CERE",yearsCur)
                                                            + p_primesResults(MS,"bioeShare","SUGA",yearsCur)))
            = p_primesResults(MS,"bioeShare",pRows,yearsCur)
            / (p_primesResults(MS,"bioeShare","CERE",yearsCur) + p_primesResults(MS,"bioeShare","SUGA",yearsCur))
        *     for feasibility reasons, we maintain at least 5% first generation biofuels.
            * MAX(0.05,1.-p_primesResults(MS,"bioeShare","SECG",yearsCur)-p_primesResults(MS,"bioeShare","NAGR",yearsCur));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return share / shares * max(0.05, 1.0 - share_secg - share_nagr)


def p_primesResults_WOIL_Fillyears(value, woil_2005, woil_2015, fill_year):
    r"""p_primesResults(MSALL, "BIOF", "WOIL", Fillyears) of 2006-2014 with a 2015 value: at most the line between 2005
    and 2015.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 563-569):

          p_primesResults(MSALL,"BIOF","WOIL",Fillyears) $ p_primesResults(MSALL,"BIOF","WOIL","2015")

            = min(p_primesResults(MSALL,"BIOF","WOIL",Fillyears),
                  p_primesResults(MSALL,"BIOF","WOIL","2005")
               +  (CALYEA(Fillyears)-CALYEA("2005"))
               *  (p_primesResults(MSALL,"BIOF","WOIL","2015") - p_primesResults(MSALL,"BIOF","WOIL","2005"))
               /  (CALYEA("2015")-CALYEA("2005")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return min(value, woil_2005 + (fill_year - 2005) * (woil_2015 - woil_2005) / (2015 - 2005))


def p_primesResults_BIOF_VOIL(voil, woil):
    r"""p_primesResults(MSALL, "BIOF", "VOIL", yearsCur): pure vegetable oils at least 5% of waste oil.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 574-575):

          p_primesResults(MSALL,"BIOF","VOIL",yearsCur)
            = MAX(p_primesResults(MSALL,"BIOF","VOIL",yearsCur),p_primesResults(MSALL,"BIOF","WOIL",yearsCur)*0.05);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(voil, woil * 0.05)


def p_primesResults_NAGR_BIOD(mapr, share_secg, woil, voil):
    r"""p_primesResults(MSALL, "NAGR", "BIOD", yearsCur): the first generation biodiesel times waste oil's share of
    the oils, not below zero, where there are oils.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 585-589):

          p_primesResults(MSALL,"NAGR","BIOD",yearsCur)
            $(p_primesResults(MSALL,"BIOF","WOIL",yearsCur)+p_primesResults(MSALL,"BIOF","VOIL",yearsCur))
            =  MAX(0,(p_primesResults(MSALL,"MAPR","BIOD",yearsCur) *(1- p_primesResults(MSALL,"biodShare","SECG",yearsCur)))
                     *p_primesResults(MSALL,"BIOF","WOIL",yearsCur)
                   / (p_primesResults(MSALL,"BIOF","WOIL",yearsCur)+p_primesResults(MSALL,"BIOF","VOIL",yearsCur)));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(0.0, mapr * (1 - share_secg) * woil / (woil + voil))


def p_primesResults_copy(value):
    r"""p_primesResults(MSALL, "BIOF", SECO_BIOF / "DOMM", fosfuels, YearsCur): PRIMES's demand of the biofuel as its
    biofuel use; of the fossil fuel, its household consumption as demand.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 604-605):

          p_primesResults(MSALL,"BIOF",SECO_BIOF,YearsCur)
            = p_primesResults(MSALL,"DOMM",SECO_BIOF,YearsCur) ;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 612-613):

          p_primesResults(MSALL,"DOMM",fosfuels,YearsCur)
            = p_primesResults(MSALL,"HCOM",fosfuels,YearsCur) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value


def p_primesResults_DOMM_SECO_BIOF(indm, biof):
    r"""p_primesResults(MSALL, "DOMM", SECO_BIOF, YearsCur): industrial use plus biofuel use.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 607-608):

          p_primesResults(MSALL,"DOMM",SECO_BIOF,YearsCur)
            = p_primesResults(MSALL,"INDM",SECO_BIOF,YearsCur)+p_primesResults(MSALL,"BIOF",SECO_BIOF,YearsCur) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return indm + biof


def p_primesResults_CERE_BIOE(mapr, suga, secg, nagr):
    r"""p_primesResults(MS, "CERE", "BIOE", yearsCur): ethanol from cereals, production less sugar's, the second
    generation's and the non-agricultural's, not below zero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 654-658):

          p_primesResults(MS,"CERE","BIOE",yearsCur)
            = max(0,p_primesResults(MS,"MAPR","BIOE",yearsCur)
                   -p_primesResults(MS,"SUGA","BIOE",yearsCur)
                   -p_primesResults(MS,"SECG","BIOE",yearsCur)
                   -p_primesResults(MS,"NAGR","BIOE",yearsCur));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(0.0, mapr - suga - secg - nagr)


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


def p_agrFuel(mapr, secg, nagr, suga, prcb_suga, twin, prcb_twin, bioe):
    r"""p_agrFuel(MSIncl, runBio, exanteT) with production: the fuel from agricultural feedstocks, production less
    second generation and non-agricultural fuels (and for ethanol the sugar and wine ethanol already fixed), at least
    1E-14.

    bioe: the fuel is BIOE.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1154-1168):

            p_agrFuel(MSIncl,runBio,exanteT) $ p_expertSupprt(MSIncl,"MAPR",runBio,exanteT,"Absolute")
        *                    Total production
              = MAX(1e-14,   p_expertSupprt(MSIncl,"MAPR",runBio,exanteT,"Absolute")
        *                  - second generation fuels
                           - p_expertSupprt(MSIncl,"SECG",runBio,exanteT,"Absolute")
        *                  - biofuels not based on agricultural sources
                           - p_expertSupprt(MSIncl,"NAGR",runBio,exanteT,"Absolute")
                           -(
        *                    - sugar based bioethanol already fixed
                               p_expertSupprt(MSIncl,"BIOF","SUGA",exanteT,"Absolute")
                             * p_expertSupprt(MSIncl,"PRCB","SUGA",exanteT,"Absolute")
        *                    - fixed base period ethanol from wine
                             + p_expertSupprt(MSIncl,"BIOF","TWIN",exanteT,"Absolute")
                             * p_expertSupprt(MSIncl,"PRCB","TWIN",exanteT,"Absolute")) $ SAMEAS(RUNBIO,"BIOE") )
                                             ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    fix = (suga * prcb_suga + twin * prcb_twin) if bioe else 0.0
    return max(1e-14, mapr - secg - nagr - fix)


def p_stockShare_expostT(own, products):
    r"""p_stockShare(MSIncl, runStock, expostT): the stock's share of the fuel from its stocks (PRCB x BIOF of
    p_data), where both are nonzero.

    products: PRCB x BIOF of the fuel's stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1172-1180):

            p_stockShare(MSIncl,runStock,expostT)
              $ (    SUM(STOCK_TO_FUEL(runStock1,runBio), P_Result(MSIncl,"PRCB",runStock1,expostT,"P_DATA")
                                                         *P_Result(MSIncl,"BIOF",runStock1,expostT,"P_DATA"))
                 and SUM(STOCK_TO_FUEL(runStock,runBio),  P_Result(MSIncl,"PRCB",runStock,expostT,"P_DATA")
                                                         *P_Result(MSIncl,"BIOF",runStock,expostT,"P_DATA")))
              = SUM(STOCK_TO_FUEL(runStock,runBio), P_Result(MSIncl,"PRCB",runStock,expostT,"P_DATA")
                                                    *P_Result(MSIncl,"BIOF",runStock,expostT,"P_DATA"))
              / SUM(STOCK_TO_FUEL(runStock1,runBio), P_Result(MSIncl,"PRCB",runStock1,expostT,"P_DATA")
                                                    *P_Result(MSIncl,"BIOF",runStock1,expostT,"P_DATA"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return own / sum(products)


def p_stockShare_exanteT(share_base):
    r"""p_stockShare(MSIncl, runStock, exanteT) of a stock with a processing coefficient in %BASprimes%: that year's
    share.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1184-1186):

            p_stockShare(MSIncl,runStock,exanteT)
              $ SUM(STOCK_TO_FUEL(runStock,runBio), P_Result(MSIncl,"PRCB",runStock,"%BASprimes%","P_DATA"))
                  = p_stockShare(MSIncl,runStock,"%BASprimes%");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return share_base


def p_stockShare_potential(share, potential):
    r"""p_stockShare(MSIncl, runStock, exanteT) of a stock whose DOMM has nObs: at least p_potentialStocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1189-1192):

            p_stockShare(MSIncl,runStock,exanteT)
              $  (SUM(STOCK_TO_FUEL(runStock,runBio),P_DATA(MSIncl,"DOMM",runStock,"nObs")))
              = SUM(STOCK_TO_FUEL(runStock,runBio) , MAX(p_stockShare(MSIncl,runStock,exanteT),
                                                         p_potentialStocks(MSIncl,runStock))  );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(share, potential)


def p_stockShare_runBio(shares):
    r"""p_stockShare(MSIncl, runBio, exanteT): the fuel's stocks' shares summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1196-1197):

            p_stockShare(MSIncl,runBio,exanteT)
             = SUM(STOCK_TO_FUEL(runStock1,runBio),p_stockShare(MSIncl,runStock1,exanteT)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(shares)


def p_stockShare_normalised(share, total):
    r"""p_stockShare(MSIncl, runStock, exanteT): the stock's share over the fuel's sum, where both are nonzero.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1200-1205):

            p_stockShare(MSIncl,runStock,exanteT)
              $ (    SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runBio,exanteT))
                 and SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runStock,exanteT)))

              = SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runStock,exanteT))
              / SUM(STOCK_TO_FUEL(runStock,runBio),p_stockShare(MSIncl,runBio,exanteT))  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return share / total


def p_expertSupprt_BIOF_runStock(agr_fuel, share, prcb):
    r"""p_expertSupprt(MSIncl, "BIOF", runStock, exanteT, "Absolute") with a processing coefficient: the fuel from
    agricultural feedstocks times the stock's share over the coefficient.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1210-1218):

            p_expertSupprt(MSIncl,"BIOF",runStock,exanteT,"Absolute")
               $ SUM(STOCK_TO_FUEL(runStock,runBio), p_expertSupprt(MSIncl,"PRCB",runStock,exanteT,"Absolute"))

        *       - Baseline MAPR - NAGR - SECG of respective biofuel
                = (SUM(STOCK_TO_FUEL(runStock,runBio),p_agrFuel(MSIncl,runBio,exanteT))
        *       - multiplied with shares
                * p_stockShare(MSIncl,runStock,exanteT))
        *       - divided by processing coefficient
                / p_expertSupprt(MSIncl,"PRCB",runStock,exanteT,"Absolute")  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return agr_fuel * share / prcb


def p_expertSupprt_MAPR_DDGS(pairs):
    r"""p_expertSupprt(MSIncl, "MAPR", "DDGS", exanteT, "Absolute"): the by-product yields times the feedstock use,
    summed over the stocks giving DDGS.

    pairs: (PRCBY, BIOF) of those stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1224-1227):

          p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
             $ SUM(STOCK_TO_BY(OSECO,"DDGS"), p_expertSupprt(MSIncl,"PRCBY",OSECO,exanteT,"Absolute"))
             = SUM(STOCK_TO_BY(OSECO,"DDGS"), p_expertSupprt(MSIncl,"PRCBY",OSECO,exanteT,"Absolute")
             * p_expertSupprt(MSIncl,"BIOF",OSECO,exanteT,"Absolute") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(a * b for a, b in pairs)


def p_expertSupprt_FEDM_DDGS(mapr, fpro):
    r"""p_expertSupprt(MSIncl, "FEDM", "DDGS", exanteT, "Absolute"): DDGS production times one less its share of DDGS
    and the feed protein (GROF.FPRO of BASM).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1232-1236):

          p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute")
               $ (p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")+P_Result(MSIncl,"GROF","FPRO",exanteT,"BASM"))
               = p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
               * (1. - p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
                     /(p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")+P_Result(MSIncl,"GROF","FPRO",exanteT,"BASM")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr * (1. - mapr / (mapr + fpro))


def p_expertSupprt_DOMM_DDGS(fedm):
    r"""p_expertSupprt(MSIncl, "DOMM", "DDGS", exanteT, "Absolute"): its feed use.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1238-1238):

          p_expertSupprt(MSIncl,"DOMM","DDGS",exanteT,"Absolute") = p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return fedm


def p_expertSupprt_NTRD_DDGS(mapr, domm):
    r"""p_expertSupprt(MSIncl, "NTRD", "DDGS", exanteT, "Absolute") with production: production less demand.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1240-1241):

          p_expertSupprt(MSIncl,"NTRD","DDGS",exanteT,"Absolute") $ p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute")
              = p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute") - p_expertSupprt(MSIncl,"DOMM","DDGS",exanteT,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return mapr - domm


def p_expertSupprt_IMPT_DDGS(mapr):
    r"""p_expertSupprt(MSIncl, "IMPT", "DDGS", exanteT, "Absolute") with feed use: 5% of production, at least
    1E-12.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1245-1246):

          p_expertSupprt(MSIncl,"IMPT","DDGS",exanteT,"Absolute") $ p_expertSupprt(MSIncl,"FEDM","DDGS",exanteT,"Absolute")
              = MAX(1.E-12,0.05*p_expertSupprt(MSIncl,"MAPR","DDGS",exanteT,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return max(1.E-12, 0.05 * mapr)


def p_expertSupprt_EXPT_DDGS(impt, ntrd):
    r"""p_expertSupprt(MSIncl, "EXPT", "DDGS", exanteT, "Absolute"): imports plus net trade.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1247-1248):

          p_expertSupprt(MSIncl,"EXPT","DDGS",exanteT,"Absolute")
                                    = p_expertSupprt(MSIncl,"IMPT","DDGS",exanteT,"Absolute")+p_expertSupprt(MSIncl,"NTRD","DDGS",exanteT,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return impt + ntrd


def p_expertSupprt_BIOF_small():
    r"""p_expertSupprt(MSIncl, "BIOF", bioStock, exanteT, "Absolute") below 0.01: removed (CAPRI's statement twice).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1253-1254):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
            $ ABS(p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute") lt 0.01) = 0;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1256-1257):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
          $ ABS(p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute") lt 0.01)   = 0;

    Departures from CAPRI: CAPRI's condition ABS(x lt 0.01) is the comparison's truth (x below 0.01, negative values included); the port
    tests x < 0.01 once, the second statement finding nothing left; the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return 0.0


def p_expertSupprt_BIOF_tiny():
    r"""p_expertSupprt(MSIncl, "BIOF", bioStock, exanteT, "Absolute") of a member state without a value where its
    fuels are produced and the stock had demand or biofuel use in %BASprimes%: 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1259-1264):

          p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute")
             $ ((NOT p_expertSupprt(MSIncl,"BIOF",bioStock,exanteT,"Absolute"))
                and sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exanteT,"Absolute"))
                and( P_Result(MSIncl,"domm",bioStock,"%BASprimes%","P_DATA")or P_Result(MSIncl,"BIOF",bioStock,"%BASprimes%","P_DATA"))
                and SUM(SAMEAS(MS,MSIncl),1)
                )= 1e-14;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1e-14


def P_expertSupprt_BIOF_CERE(values):
    r"""P_expertSupprt(MSIncl, "BIOF", "CERE", exAnte, "Absolute"): the cereals' feedstock use summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1271-1272):

          P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"Absolute")
            = SUM(CERE,  P_expertSupprt(MSIncl,"BIOF",CERE,exAnte,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(values)


def P_expertSupprt_PRCB_tiny(mapr):
    r"""P_expertSupprt(MSIncl, PRCB / PRCBY, bioStock, exAnte, "Absolute") of a member state's stock without feedstock
    use: 1E-14 where its fuels are produced, else removed.

    mapr: whether one of the stock's fuels has production.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1274-1278):

          P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"Absolute")
                $ ( (NOT P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                     and P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"Absolute")
                    and SUM(SAMEAS(MS,MSIncl),1)) = 1e-14
                        $ sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exAnte,"Absolute"));

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1280-1283):

          P_expertSupprt(MSIncl,"PRCBY",bioStock,exAnte,"Absolute")
           $  ((NOT P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute"))
                and SUM(SAMEAS(MS,MSIncl),1)) = 1e-14
                    $ sum(STOCK_TO_FUEL(bioStock,seco_biof), p_expertSupprt(MSIncl,"MAPR",seco_biof,exAnte,"Absolute"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1e-14 if mapr else 0.0


def P_expertSupprt_MAPR_BIOE(pairs, secg, nagr):
    r"""P_expertSupprt(MSIncl, "mapr", "bioe", exAnte, "Absolute"): ethanol production from its feedstocks (BIOF x
    PRCB), second generation and non-agricultural ethanol.

    pairs: (BIOF, PRCB) of the ethanol stocks.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1288-1293):

          P_expertSupprt(MSIncl,"mapr","bioe",exAnte,"Absolute")
            =  SUM(STOCK_TO_FUEL(bioStock,"bioe"),
               ( P_expertSupprt(MSIncl,"BIOF",biostock,exAnte,"Absolute")* P_expertSupprt(MSIncl,"prcb",biostock,exAnte,"Absolute")))
        *
               +  P_expertSupprt(MSIncl,"SECG","BIOE",exAnte,"Absolute")
               +  P_expertSupprt(MSIncl,"NAGR","BIOE",exAnte,"Absolute");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(b * p for b, p in pairs) + secg + nagr


def P_expertSupprt_constBioPos(value_2020):
    r"""P_expertSupprt(MSIncl, cols, rows, EXANTE, "Absolute") of the EU28 member states' biofuel positions
    (map_constBioPos) after 2020, with %constBionergy%: their 2020 value.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1314-1316):

          P_expertSupprt(MSIncl,cols,rows,EXANTE,"Absolute") $ ( (ordt(exante) gt ordt("2020")) $ map_constBioPos(cols,rows)
                                                               $ MS_TO_RMSAGG(MSincl,"EU028000") )
            =  P_expertSupprt(MSIncl,cols,rows,"2020","Absolute") ;

    Departures from CAPRI: EPS of 2020 is carried as EPS by the caller; the positions are the caller's (biofuel_trends.trends: hold)."""
    return value_2020


def P_expertSupprt_fossil(hcom):
    r"""P_expertSupprt(MSIncl, DOMM / HCOM, fossilFuels, EXANTE, "Absolute"): PRIMES's household consumption.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1325-1325):

          P_expertSupprt(MSIncl,"DOMM",fossilFuels,EXANTE,"Absolute") =  p_primesResults(MSIncl,"HCOM",fossilFuels,exAnte);

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1326-1326):

          P_expertSupprt(MSIncl,"HCOM",fossilFuels,EXANTE,"Absolute") =  p_primesResults(MSIncl,"HCOM",fossilFuels,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return hcom


def p_expertSupprt_INHA_fossil(hcom, inha):
    r"""p_expertSupprt(MSINCL, "INHA", fossilfuels, exAnteT, "Absolute") where p_data has the population: the
    consumption per head (kg).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1336-1337):

          p_expertSupprt(MSINCL,"INHA",fossilfuels,exAnteT,"Absolute") $ P_Result(MSINCL,"INHA","LEVL",ExAnteT,"P_Data")
            = p_expertSupprt(MSINCL,"HCOM",fossilfuels,exAnteT,"Absolute") / P_Result(MSINCL,"INHA","LEVL",ExAnteT,"P_Data") *1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return hcom / inha * 1000


def p_taxData_CTAX_2005(ctax_2005):
    r"""p_taxData(MSIncl, Seco_bioF, "CTAX", expostT) after 2005: 2005's (no change for excise taxes on biofuels after
    2005).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1347-1348):

          p_taxData(MSIncl,Seco_bioF,"CTAX",expostT) $ (OrdT(expostT) gt OrdT("2005"))
            = p_taxData(MSIncl,Seco_bioF,"CTAX","2005");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ctax_2005


def p_taxData_CTAX_per_t(ctax, oil_equ, density):
    r"""p_taxData(MSIncl, Seco_bioF, "CTAX", expostT): per toe, over p_oilEqu and p_density.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1351-1353):

          p_taxData(MSIncl,Seco_bioF,"CTAX",expostT)
            = p_taxData(MSIncl,Seco_bioF,"CTAX",expostT)
            / p_oilEqu(Seco_biof)/p_density(Seco_biof) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ctax / oil_equ / density


def P_expertSupprt_CTAX_SECO_BIOF(ctax, ctax_base, expost):
    r"""P_expertSupprt(MSIncl, "CTAX", SECO_BIOF, EXANTE, "Absolute") of a fuel with demand: the excise tax (%BASprimes%'s
    for the years not ex-post) plus 1E-14.

    expost: the year is in expostT.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1356-1360):

          P_expertSupprt(MSIncl,"CTAX",SECO_BIOF,EXANTE,"Absolute") $ SUM(yearscur,p_expertSupprt(MSINCL,"DOMM",SECO_BIOF,yearscur,"Absolute"))
             = ( p_taxData(MSIncl,Seco_bioF,"CTAX",exante)
             + p_taxData(MSIncl,Seco_bioF,"CTAX","%BASprimes%") $ (Not expostT(exante)))
        *  ensure that tax reductions are implemented (otherwise this is not fixed to zero):
             + 1e-14;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ctax + (ctax_base if not expost else 0.0) + 1e-14


def P_expertSupprt_CTAX_fossil_expostT(ctax):
    r"""P_expertSupprt(MSIncl, "CTAX", fossilFuels, expostT, "Absolute") of a fuel with demand and no tax yet:
    PRIMES's.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1364-1367):

          P_expertSupprt(MSIncl,"CTAX",fossilFuels,expostT,"Absolute")
                 $  (  SUM(yearscur,p_expertSupprt(MSINCL,"DOMM",fossilFuels,yearscur,"Absolute"))
                     $ (Not SUM(yearscur,P_expertSupprt(MSIncl,"CTAX",fossilFuels,yearscur,"Absolute"))))
            = p_primesResults(MSIncl,"CTAX",fossilFuels,expostT);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return ctax


def P_expertSupprt_CTAX_fossil_exanteT(base, ctax, ctax_base):
    r"""P_expertSupprt(MSIncl, "CTAX", FossilFuels, exanteT, "Absolute") of a fuel with demand: %BASprimes%'s plus
    PRIMES's change (where PRIMES's %BASprimes% tax exceeds 1E-12), plus 1E-14.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1370-1374):

          P_expertSupprt(MSIncl,"CTAX",FossilFuels,exanteT,"Absolute") $ SUM(yearscur,p_expertSupprt(MSINCL,"DOMM",fossilFuels,yearscur,"Absolute"))
            =     P_expertSupprt(MSIncl,"CTAX",FossilFuels,"%BASprimes%","Absolute")
                +(p_primesResults(MSIncl,"CTAX",fossilFuels,exAnteT)
                 -p_primesResults(MSIncl,"CTAX",fossilFuels,"%BASprimes%")) $ (p_primesResults(MSIncl,"CTAX",fossilFuels,"%BASprimes%") gt 1.e-12)
            + 1e-14 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return base + ((ctax - ctax_base) if ctax_base > 1.e-12 else 0.0) + 1e-14


def P_result_UVAG_basy(prices):
    r"""P_result(MSIncl, "UVAG", fuels, basy, "p_data") without a value: Aglink's EU producer prices of the fuel.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1380-1381):

          P_result(MSIncl,"UVAG",fuels,basy,"p_data") $ (NOT P_result(MSIncl,"UVAG",fuels,basy,"p_data"))
             = SUM(fuelMap(fuels,agFuels),p_Aglink("%AgEUTot%","PP",agFuels,basy));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return sum(prices)


def P_result_UVAG_expostT(uvag_basy, prices, prices_basy):
    r"""P_result(MSIncl, "UVAG", fuels, expostT, "p_data") without a value after the base year: the base year's moved by
    Aglink's EU producer prices.

    prices_basy: Aglink's prices of the base year, summed.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1383-1388):

          P_result(MSIncl,"UVAG",fuels,expostT,"p_data") $ ( (NOT P_result(MSIncl,"UVAG",fuels,expostT,"p_data"))
                                                           $ SUM((basy,fuelMap(fuels,agFuels)),p_Aglink("%AgEUTot%","PP",agFuels,basy))
                                                           $ (ORDT(expostT) GT ORDT("BAS")))
             = SUM(basy,P_result(MSIncl,"UVAG",fuels,basy,"p_data"))
             * SUM(fuelMap(fuels,agFuels),p_Aglink("%AgEUTot%","PP",agFuels,expostT))
             / SUM((basy,fuelMap(fuels,agFuels)),p_Aglink("%AgEUTot%","PP",agFuels,basy));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return uvag_basy * sum(prices) / prices_basy


def P_expertSupprt_UVAG_expostT(value):
    r"""P_expertSupprt(MSIncl, "UVAG", fuels, expostT, "Absolute") without a value: p_data's.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1390-1391):

          P_expertSupprt(MSIncl,"UVAG",fuels,expostT,"Absolute") $ (NOT P_expertSupprt(MSIncl,"UVAG",fuels,expostT,"Absolute"))
             = P_result(MSIncl,"UVAG",fuels,expostT,"p_data") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value


def P_expertSupprt_UVAG_EXANTE(uvag_base, pairs):
    r"""P_expertSupprt(MSIncl, "UVAG", fuels, EXANTE, "Absolute") of the years not ex-post: %BASprimes%'s moved by
    PRIMES's fossil fuel prices (the member state's, else the EU28's).

    pairs: (the year's price, %BASprimes%'s) of the matched fossil fuels with a %BASprimes% price.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1395-1407):

           P_expertSupprt(MSIncl,"UVAG",fuels,EXANTE,"Absolute")
                  $ ( (Not expostT(exante))
                     $ (  SUM(fuelMatch(fuels,fossilFuels),p_primesResults(MSIncl,"UVAP",fossilFuels,"%BASprimes%"))
                       or SUM(fuelMatch(fuels,fossilFuels),p_primesResults("EU028000","UVAP",fossilFuels,"%BASprimes%")))
                     )
          = P_expertSupprt(MSIncl,"UVAG",fuels,"%BASprimes%","Absolute")
            * (SUM(fuelMatch(fuels,fossilFuels), p_primesResults(MSIncl,"UVAP",fossilFuels,exAnte)
                                                /p_primesResults(MSIncl,"UVAP",fossilFuels,"%BASprimes%"))
              $ (    SUM(fuelMatch(fuels,fossilFuels),p_primesResults(MSIncl,"UVAP",fossilFuels,"%BASprimes%") ))
              +SUM(fuelMatch(fuels,fossilFuels), p_primesResults("EU028000","UVAP",fossilFuels,exAnte)
                                                /p_primesResults("EU028000","UVAP",fossilFuels,"%BASprimes%"))
              $ (not SUM(fuelMatch(fuels,fossilFuels),p_primesResults(MSIncl,"UVAP",fossilFuels,"%BASprimes%") ))
              ) ;

    Departures from CAPRI: the caller leaves out the fossil fuels without a %BASprimes% price (CAPRI divides by it); the domain condition and the loops in the caller (biofuel_trends.trends)."""
    return uvag_base * sum(a / b for a, b in pairs)


def P_expertSupprt_UVAD(uvag, ctax):
    r"""P_expertSupprt(MSIncl, "UVAD", fuels, EXANTE, "Absolute") of a fuel with demand: the producer price plus the
    excise tax.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1410-1411):

           P_expertSupprt(MSIncl,"UVAD",fuels,EXANTE,"Absolute") $ SUM(yearscur,p_expertSupprt(MSINCL,"DOMM",Fuels,yearscur,"Absolute"))
               =  P_expertSupprt(MSIncl,"UVAG",fuels,EXANTE,"Absolute") + P_expertSupprt(MSIncl,"CTAX",fuels,EXANTE,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return uvag + ctax


def P_expertSupprt_per_ton(value, oil_equ):
    r"""P_expertSupprt(MSIncl, UVAG / UVAD / CTAX, fuels, yearscur, "Absolute"): per ton (times p_oilEqu).

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1415-1416):

           P_expertSupprt(MSIncl,cols,fuels,yearscur,"Absolute") $ (SAMEAS(cols,"UVAG") or SAMEAS(cols,"UVAD") or SAMEAS(cols,"CTAX"))
               =  P_expertSupprt(MSIncl,cols,fuels,yearscur,"Absolute") * p_oilEqu(fuels);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return value * oil_equ


def p_expertSupprt_EXPD(uvad, inha):
    r"""p_expertSupprt(MSIncl, "EXPD", fuels, exAnte, "Absolute") with a consumer price and consumption per head: the
    expenditure.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1421-1423):

           p_expertSupprt(MSIncl,"EXPD",fuels,exAnte,"Absolute") $ (    P_EXPErtSupprt(MSIncl,"UVAD",fuels,EXANTE,"Absolute")
                                                                 and p_expertSupprt(MSIncl,"INHA",fuels,exAnte,"Absolute"))
                         = P_EXPErtSupprt(MSIncl,"UVAD",fuels,EXANTE,"Absolute")*p_expertSupprt(MSIncl,"INHA",fuels,exAnte,"Absolute")/1000.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return uvad * inha / 1000.


def P_expertSupprt_TrustLevl_7():
    r"""P_expertSupprt(MSIncl, ., SECO_BIOF / FossilFuels / bioStock / CERE, exAnte, "TrustLevl") of the biofuel
    positions, the fuels, the feedstocks and their coefficients with a value (PRCB and PRCBY where the feedstock is
    used): 7.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1428-1428):

          P_expertSupprt(MSIncl,COLS,SECO_BIOF,exAnte,"TrustLevl")   $ P_expertSupprt(MSIncl,COLS,SECO_BIOF,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1434-1434):

          P_expertSupprt(MSIncl,COLS,FossilFuels,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,COLS,FossilFuels,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1436-1436):

          P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"TrustLevl")  $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1438-1438):

          P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"TrustLevl")    $ P_expertSupprt(MSIncl,"BIOF","CERE",exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1440-1440):

          P_expertSupprt(MSIncl,"PRCB",bioStock,exAnte,"TrustLevl")  $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1442-1442):

          P_expertSupprt(MSIncl,"PRCBY",bioStock,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"BIOF",bioStock,exAnte,"Absolute") = 7;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 7.0


def P_expertSupprt_TrustLevl_1():
    r"""P_expertSupprt(MSIncl, IMPT / EXPT, SECO_BIOF, exAnte, "TrustLevl") and the fuels' EXPD with a value: 1.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1430-1430):

          P_expertSupprt(MSIncl,"IMPT",SECO_BIOF,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"IMPT",SECO_BIOF,exAnte,"Absolute") = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1432-1432):

          P_expertSupprt(MSIncl,"EXPT",SECO_BIOF,exAnte,"TrustLevl") $ P_expertSupprt(MSIncl,"EXPT",SECO_BIOF,exAnte,"Absolute") = 1;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1444-1446):

          p_expertSupprt(MSIncl,"EXPD",fuels,exAnte,"TrustLevl")     $ (    p_expertSupprt(MSIncl,"UVAD",fuels,exAnte,"Absolute")
                                                                      and p_expertSupprt(MSIncl,"INHA",fuels,exAnte,"Absolute")
                                                                      and p_expertSupprt(MSIncl,"EXPD",fuels,exAnte,"Absolute")) = 1.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1.


def p_expertSupprt_TrustLevl_DDGS():
    r"""p_expertSupprt(MSIncl, FEDM / DOMM / MAPR / EXPT / IMPT, "DDGS", exAnte, "TrustLevl") with a value: 3.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1448-1448):

          p_expertSupprt(MSIncl,"FEDM","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"FEDM","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1449-1449):

          p_expertSupprt(MSIncl,"DOMM","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"DOMM","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1450-1450):

          p_expertSupprt(MSIncl,"MAPR","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"MAPR","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1451-1451):

          p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"Absolute") = 3;

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1452-1452):

          p_expertSupprt(MSIncl,"IMPT","DDGS",exAnte,"TrustLevl") $ p_expertSupprt(MSIncl,"IMPT","DDGS",exAnte,"Absolute") = 3;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 3.0


def p_expertSupprt_NTRD_DDGS_TrustLevl(trust_expt, ntrd, expt):
    r"""p_expertSupprt(MSIncl, "NTRD", "DDGS", exAnte, "TrustLevl") with net trade and exports: the exports' trust
    times net trade over exports.

    CAPRI's GAMS (biofuel/biofuel_trends.gms l. 1456-1459):

          p_expertSupprt(MSIncl,"NTRD","DDGS",exAnte,"TrustLevl") $ (    p_expertSupprt(MSIncl,"NTRD","DDGS",exAnte,"Absolute")
                                                                   and p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"Absolute"))
                 = 1* p_expertSupprt(MSIncl,"EXPT","DDGS",exAnte,"TrustLevl")
                 * P_expertSupprt(MSIncl,"NTRD","DDGS",ExAnte,"Absolute")/P_expertSupprt(MSIncl,"EXPT","DDGS",ExAnte,"Absolute") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (biofuel_trends.trends)."""
    return 1 * trust_expt * ntrd / expt

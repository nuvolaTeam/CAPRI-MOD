r"""PRIMES's results for CAPTRD's biofuel trends: aggregated, filled and shared out (moved from
capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
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

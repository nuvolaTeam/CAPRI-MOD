r"""The taxes (CTAX), the unit values (UVAG, UVAD), the per-ton and EXPD supports (moved from
capri_mod/pipeline/captrd/equations/biofuel_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations




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

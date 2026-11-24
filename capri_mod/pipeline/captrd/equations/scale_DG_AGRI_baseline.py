r"""CAPTRD's statements of captrd/scale_DG_AGRI_baseline.gms (CAPRI star 3.0, captrd.gms l. 954): the DG AGRI baseline
scaled to CAPRI's base period, DGAgri1 = CAPRI's base x DGAgri's relative change, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/scale_dgagri.py (scale) holds the loops over the
regions, the positions and the years, the data and the conditions, and calls them; the arithmetic is the port's, so
the baseline is unchanged. A value is GAMS's true where nonzero, NA included (_nz, as aglink.py's).
"""
from __future__ import annotations

import math


def P_Data_BAST(values):
    r"""P_Data(Rest, ., ., "BAST"): the mean over the base years BasYrsT of the values at least 1E-12 in size (the
    tiny values of load_coco_data do not count), all the years' values summed.

    values: p_data of the base years, in order. Returns the mean, or None where no year counts.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 53-57):

          P_Data(Rest,S_ColsEst,S_RowsEst,"BAST")
        *       ... but without tiny values introduced in load_coco_data to prevent other supports and trigger fixing to zero
              $( sum(BasYrsT $ (ABS(P_Data(Rest,S_ColsEst,S_RowsEst,BasYrsT)) GE 1E-12), 1.) )
            = sum(BasYrsT, P_Data(Rest,S_ColsEst,S_RowsEst,BasYrsT))
             /sum(BasYrsT $ (ABS(P_Data(Rest,S_ColsEst,S_RowsEst,BasYrsT)) GE 1E-12), 1.);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    num = sum(values)
    n = sum(1 for v in values if abs(v) >= 1e-12)
    return num / n if n else None


def P_Result_DgAgri_yield(yild):
    r"""P_Result(Rest, ., output, Years, "DgAgri") without one: the activity's YILD moved to its product.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 62-66):

          P_Result(Rest,S_ColsEst,S_RowsEst,Years,"DgAgri") $ (  (NOT P_Result(Rest,S_ColsEst,S_RowsEst,Years,"DgAgri") )
                                                               $  P_Result(Rest,S_ColsEst,"YILD",Years,"DgAgri")
                                                               $  PACT_TO_Y(S_ColsEst,S_RowsEst)
                                                               $  PACT(S_ColsEst))
             = SUM(PACT_TO_Y(S_ColsEst,S_RowsEst),P_Result(Rest,S_ColsEst,"YILD",Years,"DgAgri"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return yild


def p_result_BAST_DGAgri(values):
    r"""p_result(., "BAST", "DGAgri"): the outlook's mean over the base years with a value (and so the EU aggregates'
    prices).

    values: DGAgri of the base years, in order. Returns the mean, or None where none has a value.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 69-72):

          p_result(Rest,S_ColsEst,S_RowsEst,"BAST","DGAgri")
              $( sum(BasYrsT $ p_result(Rest,S_ColsEst,S_RowsEst,BasYrsT,"DGAgri"), 1.) )
            = sum(BasYrsT, p_result(Rest,S_ColsEst,S_RowsEst,BasYrsT,"DGAgri"))
            /sum(BasYrsT $ p_result(Rest,S_ColsEst,S_RowsEst,BasYrsT,"DGAgri"), 1.);

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 91-94):

          p_result(CurEuropAgg,"UVAG",S_RowsEst,"BAST","DGAgri")
              $( sum(BasYrsT $ p_result(CurEuropAgg,"UVAG",S_RowsEst,BasYrsT,"DGAgri"), 1.) )
            = sum(BasYrsT, p_result(CurEuropAgg,"UVAG",S_RowsEst,BasYrsT,"DGAgri"))
            /sum(BasYrsT $ p_result(CurEuropAgg,"UVAG",S_RowsEst,BasYrsT,"DGAgri"), 1.);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    num = sum(values)
    n = sum(1 for v in values if _nz(v))
    return num / n if n else None


def p_result_UVAG_EU(values):
    r"""p_result(CurEuropAgg, "UVAG", ., Years, "DGAgri") without one: EU_WEST's prices.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 86-88):

          p_result(CurEuropAgg,"UVAG",S_RowsEst,Years,"DGAgri")
              $( (not p_result(CurEuropAgg,"UVAG",S_RowsEst,Years,"DGAgri")))
            = sum(CurEUWestAgg, p_result(CurEUWestAgg,"UVAG",S_RowsEst,Years,"DGAgri")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return sum(values)


def p_result_DGAgri1(bast, dgagri, dgagri_bast):
    r"""p_result(., Years, "DGAgri1"): CAPRI's base (BAST) times the outlook's change against its own base, from the
    member state's own outlook, else its EU part's, else the EU27's (prices and yields).

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 98-102):

          p_result(Rest,Pric,S_RowsEst,ExAnte,"DGAgri1")
              $( p_result(Rest,Pric,S_RowsEst,"BAST","DGAgri") and (not SAMEAS(Pric,"PADM")))
            = p_data(Rest,Pric,S_RowsEst,"BAST")
              * p_result(Rest,Pric,S_RowsEst,ExAnte,"DGagri")
              / p_result(Rest,Pric,S_RowsEst,"BAST","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 108-115):

             p_result(MS   ,Pric,S_RowsEst,ExAnte,"DGAgri1")
                 $(  MAP_RR(RaggEst, MS)
                   $ (not p_result(MS   ,Pric,S_RowsEst,ExAnte,"DGAgri1"))
                   $ p_result(RaggEst,Pric,S_RowsEst,"BAST","DGAgri")
                   $ (not SAMEAS(Pric,"PADM")))
               = p_data(MS   ,Pric,S_RowsEst,"BAST")
                 * p_result(RaggEst,Pric,S_RowsEst,ExAnte,"DGagri")
                 / p_result(RaggEst,Pric,S_RowsEst,"BAST","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 121-128):

             p_result(MS   ,Pric,S_RowsEst,ExAnte,"DGAgri1")
                 $(  MAP_RR(CurEUTopAgg, MS)
                   $ (not p_result(MS   ,Pric,S_RowsEst,ExAnte,"DGAgri1"))
                   $ p_result(CurEUTopAgg,Pric,S_RowsEst,"BAST","DGAgri")
                   $ (not SAMEAS(Pric,"PADM")))
               = p_data(MS   ,Pric,S_RowsEst,"BAST")
                 * p_result(CurEUTopAgg,Pric,S_RowsEst,ExAnte,"DGagri")
                 / p_result(CurEUTopAgg,Pric,S_RowsEst,"BAST","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 135-139):

          P_Result(Rest,S_ColsEst,S_RowsEst,Years,"DgAgri1") $ (  P_Result(Rest,S_ColsEst,S_RowsEst,"BAST","DgAgri")
                                                               $  PACT_TO_Y(S_ColsEst,S_RowsEst)
                                                               $  PACT(S_ColsEst))
             = P_data(Rest,S_ColsEst,S_RowsEst,"BAST")
             * P_Result(Rest,S_ColsEst,S_RowsEst,Years,"DgAgri")/P_Result(Rest,S_ColsEst,S_RowsEst,"BAST","DgAgri");

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 144-150):

             P_Result(MS,S_ColsEst,S_RowsEst,Years,"DgAgri1") $ (    (NOT P_Result(MS,S_ColsEst,S_RowsEst,Years,"DgAgri1") )
                                                                  $  P_Result(RaggEst,S_ColsEst,S_RowsEst,"BAST","DgAgri")
                                                                  $  MAP_RR(RaggEst, MS)
                                                                  $  PACT_TO_Y(S_ColsEst,S_RowsEst)
                                                                  $  PACT(S_ColsEst))
                = P_data(MS,S_ColsEst,S_RowsEst,"BAST")
                * P_Result(RaggEst,S_ColsEst,S_RowsEst,Years,"DgAgri")/P_Result(RaggEst,S_ColsEst,S_RowsEst,"BAST","DgAgri");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return bast * dgagri / dgagri_bast


def p_result_MrkBalee_tiny():
    r"""p_result(rEst, MrkBalee, Rows, Years, "DGAgri") at most 1E-10 in size: removed.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 162-163):

          p_result(rEst,MrkBalee,Rows,Years,"DGAgri") $ ( p_result(rEst,MrkBalee,Rows,Years,"DGAgri")
             and (ABS(p_result(rEst,MrkBalee,Rows,Years,"DGAgri")) LE 1.E-10)) = 0.0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return 0.0


def p_result_HCOM_INHA(inha, population):
    r"""p_result(rEst, "HCOM", ., yearsCur, "DGAgri") without one: the per-head consumption (kg) x the population (1000)
    in 1000 t.

    inha: DGAgri's per-head consumption; population: the members' p_data INHA.LEVL, in the caller's order.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 170-174):

          p_result(rEst,"HCOM",S_RowsEst,yearsCur,"DGAgri")
             $ (   p_result(rEst,"INHA",S_RowsEst,yearsCur,"DGAgri")
                $ (NOT p_result(rEst,"HCOM",S_RowsEst,yearsCur,"DGAgri")))
             = p_result(rEst,"INHA",S_RowsEst,yearsCur,"DGAgri")
               *SUM(MAP_RR(rEst,MS), p_data(MS,"INHA","LEVL",yearsCur)) * 0.001;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return inha * sum(population) * 0.001


def p_result_HCOM_DOMM(domm):
    r"""p_result(rEst, "HCOM", meats and EGGS, yearsCur, "DGAgri") without one: DOMM.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 178-182):

          p_result(rEst,"HCOM",S_RowsEst,yearsCur,"DGAgri")
             $ (  (R_T_OAGG("MEAS",S_RowsEst) or SAMEAS(S_RowsEst,"EGGS"))
                $ p_result(rEst,"DOMM",S_RowsEst,yearsCur,"DGAgri")
                $ (NOT p_result(rEst,"HCOM",S_RowsEst,yearsCur,"DGAgri")))
             = p_result(rEst,"DOMM",S_RowsEst,yearsCur,"DGAgri");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return domm


def p_data_RaggEst(values):
    r"""p_data(RaggEst, ., ., yearsCur) without one, of the EU parts with an outlook: their members' (those without
    their own outlook) summed (market balances and levels).

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 208-211):

          p_data(RaggEst,MrkBalee,S_RowsEst,yearsCur) $(  SUM(exante, p_result(RaggEst,MrkBalee,S_RowsEst,exante,"DGAgri"))
                                                        $ (NOT p_data(RaggEst,MrkBalee,S_RowsEst,yearsCur)))
            = SUM(MAP_RR(RaggEst,MS) $ (NOT p_result(MS,MrkBalee,S_RowsEst,yearsCur,"DGAgri")),
              p_data(MS,MrkBalee,S_RowsEst,yearsCur));

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 302-305):

          p_data(RaggEst,S_ColsEst,"LEVL",yearsCur) $(  SUM(ExAnte,p_result(RaggEst,S_ColsEst,"LEVL",Exante,"DGAgri"))
                                                      $ (NOT p_data(RaggEst,S_ColsEst,"LEVL",yearsCur)))
            = SUM(MAP_RR(RaggEst,MS) $ (NOT p_result(MS,S_ColsEst,"LEVL",yearsCur,"DGAgri")),
              p_data(MS,S_ColsEst,"LEVL",yearsCur));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return sum(values)


def p_result_RaggEst_net(value, members):
    r"""p_result(RaggEst, MrkBalee, ., yearsCur, "DGAgri"): the EU part's outlook net of its members' own.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 213-216):

          p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
              $ p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
            = p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
            - SUM(MAP_RR(RaggEst,MS),p_result(MS,MrkBalee,S_RowsEst,yearsCur,"DGAgri"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return value - sum(members)


def p_result_RaggEst_LEVL_net(value, members):
    r"""p_result(RaggEst, ., "LEVL", yearsCur, "DGAgri"): the EU part's level net of its members' own, not below
    zero.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 307-309):

          p_result(RaggEst,S_ColsEst,"LEVL",yearsCur,"DGAgri")
             = MAX(0,p_result(RaggEst,S_ColsEst,"LEVL",yearsCur,"DGAgri")
               -SUM(MAP_RR(RaggEst,MS),p_result(MS,S_ColsEst,"LEVL",yearsCur,"DGAgri")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return max(0.0, value - sum(members))


def p_result_nonneg(value):
    r"""p_result(rEst, MrkBalee, ., yearsCur, "DGAgri") of the balance positions but INTP and NTRD: not below zero.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 221-223):

          p_result(rEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
            $ ((NOT SAMEAS(MrkBalee,"INTP")) $ (NOT SAMEAS(MrkBalee,"NTRD")))
            = MAX(0.,p_result(rEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return max(0.0, value)


def BAST2(values, n_both):
    r"""p_data / p_result(RaggEst, ., ., "BAST2"[, "DGAgri"]): the EU part's mean over the base years where both CAPRI
    and the outlook have a value.

    values: the base years' values where the other has one, in order; n_both: the years where both have.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 229-235):

          p_data(RaggEst,MrkBalee,S_RowsEst,"BAST2")
              $ sum(BasYrsT $(  p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT)
                              $ p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri")), 1)
            = sum(BasYrsT $ (p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri")),
                             p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT))
              / sum(BasYrsT $(  p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT)
                              $ p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri")), 1) ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 237-243):

          p_result(RaggEst,MrkBalee,S_RowsEst,"BAST2","DGAgri")
                  $ sum(BasYrsT $(   p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri")
                                   $ p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT)), 1)
            = sum(BasYrsT $(p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT)),
              p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri"))
                  / sum(BasYrsT $ (  p_result(RaggEst,MrkBalee,S_RowsEst,BasYrsT,"DGAgri")
                                   $ p_data(RaggEst,MrkBalee,S_RowsEst,BasYrsT)), 1) ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 314-320):

          p_data(RaggEst,S_ColsEst,"LEVL","BAST2")
              $ sum(BasYrsT $(  p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT)
                              $ p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri")), 1)
            = sum(BasYrsT $(p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri")),
              p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT))
              / sum(BasYrsT $(  p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT)
                              $ p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri")), 1) ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 322-328):

          p_result(RaggEst,S_ColsEst,"LEVL","BAST2","DGAgri")
              $ sum(BasYrsT $ (  p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri")
                               $ p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT)), 1)
            = sum(BasYrsT $(p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT)),
              p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri"))
              / sum(BasYrsT $(  p_result(RaggEst,S_ColsEst,"LEVL",BasYrsT,"DGAgri")
                              $ p_data(RaggEst,S_ColsEst,"LEVL",BasYrsT)), 1) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return sum(values) / n_both


def p_result_DGAgri1_BAST2(value, base, dgagri_base):
    r"""p_result(., yearsCur, "DGAgri1") of the market balances and the levels: the outlook times CAPRI's base over its
    own (BAST2 for the EU parts, BAST for the member states).

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 250-257):

          p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri1")
              $ (  p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
                 $ (NOT SAMEAS(MrkBalee,"NTRD"))
                 $ p_data(RaggEst,MrkBalee,S_RowsEst,"BAST2")
                 $ p_result(RaggEst,MrkBalee,S_RowsEst,"BAST2","DGAgri") )
            = p_result(RaggEst,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
              * p_data(RaggEst,MrkBalee,S_RowsEst,"BAST2")
              / p_result(RaggEst,MrkBalee,S_RowsEst,"BAST2","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 279-286):

          p_result(MS,MrkBalee,S_RowsEst,yearsCur,"DGAgri1")
              $ (  p_result(MS,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
                 $ (NOT SAMEAS(MrkBalee,"NTRD"))
                 $ p_data(MS,MrkBalee,S_RowsEst,"BAST")
                 $ p_result(MS,MrkBalee,S_RowsEst,"BAST","DGAgri") )
            = p_result(MS,MrkBalee,S_RowsEst,yearsCur,"DGAgri")
              * p_data(MS,MrkBalee,S_RowsEst,"BAST")
              / p_result(MS,MrkBalee,S_RowsEst,"BAST","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 333-339):

          p_result(RaggEst,S_ColsEst,"LEVL",yearsCur,"DGAgri1")
              $ (  p_result(RaggEst,S_ColsEst,"LEVL",yearsCur,"DGAgri")
                 $ p_data(RaggEst,S_ColsEst,"LEVL","BAST2")
                 $ p_result(RaggEst,S_ColsEst,"LEVL","BAST2","DGAgri") )
            = p_result(RaggEst,S_ColsEst,"LEVL",yearsCur,"DGAgri")
              * p_data(RaggEst,S_ColsEst,"LEVL","BAST2")
              / p_result(RaggEst,S_ColsEst,"LEVL","BAST2","DGAgri") ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 344-350):

          p_result(MS,S_ColsEst,"LEVL",yearsCur,"DGAgri1")
              $ (  p_result(MS,S_ColsEst,"LEVL",yearsCur,"DGAgri")
                 $ p_data(MS,S_ColsEst,"LEVL","BAST")
                 $ p_result(MS,S_ColsEst,"LEVL","BAST","DGAgri") )
            = p_result(MS,S_ColsEst,"LEVL",yearsCur,"DGAgri")
              * p_data(MS,S_ColsEst,"LEVL","BAST")
              / p_result(MS,S_ColsEst,"LEVL","BAST","DGAgri") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return value * base / dgagri_base


def p_result_COMI_DGAgri1(grof, base, grof_base):
    r"""p_result(RaggEst, DOMM / PRCM, "COMI", yearsCur, "DGAgri1") without an outlook: from GROF's, at CAPRI's base
    over GROF's.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 264-272):

          p_result(RaggEst,MrkBalee,"COMI",yearsCur,"DGAgri1")
              $ (  (NOT p_result(RaggEst,MrkBalee,"COMI",yearsCur,"DGAgri"))
                 $ p_result(RaggEst,"GROF","COMI",yearsCur,"DGAgri")
                 $ (SAMEAS(MrkBalee,"DOMM") or SAMEAS(MrkBalee,"PRCM"))
                 $ p_data(RaggEst,MrkBalee,"COMI","BAST2")
                 $ p_result(RaggEst,"GROF","COMI","BAST2","DGAgri") )
            = p_result(RaggEst,"GROF","COMI",yearsCur,"DGAgri")
              * p_data(RaggEst,MrkBalee,"COMI","BAST2")
              / p_result(RaggEst,"GROF","COMI","BAST2","DGAgri") ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return grof * base / grof_base


def p_result_DGAgri1_biofuels(value, base, dgagri_base):
    r"""p_result(RaggEst, ., fuels / BIOF, yearsCur, "DGAgri1"): the outlook times CAPRI's base over its own where the
    factor lies in (0, 2); else the difference added (at least 1E-13 where not both negative).

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 364-391):

          p_result(RaggEst,MrkBalee,fuels,yearsCur,"DGAgri1")
            $ ( p_result(RaggEst,MrkBalee,fuels,yearsCur,"DGAgri")
              $ p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")
              )

            = p_result(RaggEst,MrkBalee,fuels,yearsCur,"DGAgri")

        *  relative diff. between CAPRI and AGLINK historical data added (last expost year)
            * (p_data(RaggEst,MrkBalee,fuels,"BAST2")/p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri"))
            $ ( (p_data(RaggEst,MrkBalee,fuels,"BAST2") gt 0)
              $ ((p_data(RaggEst,MrkBalee,fuels,"BAST2")/p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")) lt 2))

        *  Correcting difference with conditionals if correction factor would be dangerous (too large or zero):

        *             case 1: for NTRD that does not require further measures:
            +(( p_result(RaggEst,MrkBalee,fuels,yearsCur,"DGAgri")
              + p_data(RaggEst,MrkBalee,fuels,"BAST2")- p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri"))
            $ ((p_data(RaggEst,MrkBalee,fuels,"BAST2")+ p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")) lt 0)

        *             case 3: variables initialised positive should stay positive:
            +max(1.e-13, p_result(RaggEst,MrkBalee,fuels,yearsCur,"DGAgri")
                        +(p_data(RaggEst,MrkBalee,fuels,"BAST2")- p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")))
            $ ((p_data(RaggEst,MrkBalee,fuels,"BAST2")+ p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")) ge 0)
              )
            $ (not ( (p_data(RaggEst,MrkBalee,fuels,"BAST2") gt 0)
                   $ ((p_data(RaggEst,MrkBalee,fuels,"BAST2")/p_result(RaggEst,MrkBalee,fuels,"BAST2","DGAgri")) lt 2)))

           ;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 393-420):

          p_result(RaggEst,"BIOF",s_rowsEst,yearsCur,"DGAgri1")
            $ ( p_result(RaggEst,"BIOF",s_rowsEst,yearsCur,"DGAgri")
              $ p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")
              )

            = p_result(RaggEst,"BIOF",s_rowsEst,yearsCur,"DGAgri")

        *  relative diff. between CAPRI and AGLINK historical data added (last expost year)
            * (p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")/p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri"))
            $ ( (p_data(RaggEst,"BIOF",s_rowsEst,"BAST2") gt 0)
              $ ((p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")/p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")) lt 2))

        *  Correcting difference with conditionals if correction factor would be dangerous (too large or zero):

        *             case 1: for NTRD that does not require further measures:
            +((  p_result(RaggEst,"BIOF",s_rowsEst,yearsCur,"DGAgri")
              +  p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")- p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri"))
            $ ((p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")+ p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")) lt 0)

        *             case 3: variables initialised positive should stay positive:
            +max(1.e-13, p_result(RaggEst,"BIOF",s_rowsEst,yearsCur,"DGAgri")
                        +(p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")- p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")))
            $ ((p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")+ p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")) ge 0)
              )
            $ (not ( (p_data(RaggEst,"BIOF",s_rowsEst,"BAST2") gt 0)
                   $ ((p_data(RaggEst,"BIOF",s_rowsEst,"BAST2")/p_result(RaggEst,"BIOF",s_rowsEst,"BAST2","DGAgri")) lt 2)))

           ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    ratio_ok = base > 0 and (base / dgagri_base) < 2.0
    if ratio_ok:
        return value * base / dgagri_base
    if base + dgagri_base < 0:
        return value + base - dgagri_base
    return max(1e-13, value + (base - dgagri_base))


def p_result_DOMM_DGAgri1(positions):
    r"""p_result(RaggEst, "DOMM", ., yearsCur, "DGAgri1"): the EU part's DOMM from its positions (DOMPOS).

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 429-432):

            p_result(RaggEst,"DOMM",S_RowsEst,yearsCur,"DGAgri1")
               $ (  SUM(DOMPOS, p_result(RaggEst,DOMPOS,S_RowsEst,yearsCur,"DGAgri1"))
                  $ p_result(RaggEst,"DOMM",S_RowsEst,yearsCur,"DGAgri1"))
               = SUM(DOMPOS, p_result(RaggEst,DOMPOS,S_RowsEst,yearsCur,"DGAgri1"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (scale_dgagri.scale)."""
    return sum(positions)


def p_result_DGAgri1_removed():
    r"""p_result(., yearsCur, "DGAgri1") of seed and losses (SEDF, SEDM, LOSF, LOSM), and of the EU27: removed.

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 443-443):

          p_result(Rest,"SEDF",S_RowsEst,yearsCur,"DGAgri1")     = 0;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 444-444):

          p_result(Rest,"SEDM",S_RowsEst,yearsCur,"DGAgri1")     = 0;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 445-445):

          p_result(Rest,"LOSF",S_RowsEst,yearsCur,"DGAgri1")     = 0;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 446-446):

          p_result(Rest,"LOSM",S_RowsEst,yearsCur,"DGAgri1")     = 0;

    CAPRI's GAMS (captrd/scale_DG_AGRI_baseline.gms l. 464-464):

          p_result(CurEUTopAgg,S_ColsEst,S_RowsEst,yearsCur,"DGAgri1") = 0 ;

    Departures from CAPRI: reg_cols_rows_dropAglink2014 (l. 456) is empty in the reference run and not ported; the domain in the caller 
    (scale_dgagri.scale)."""
    return 0.0


def _nz(v):
    """GAMS's truth of a value: nonzero, NA included."""
    return v != 0.0 or math.isnan(v)

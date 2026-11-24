r"""CAPTRD's statements of captrd/adjust_trade_supports.gms (CAPRI star 3.0, define_stats_and_supports.gms l. 627; its
OILS_ADJ block, l. 47-128, is off): the member states' NTRD support implied by production and domestic use, and IMPT and
EXPT rescaled to it, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/final_supports.py (adjust_trade) holds the loops over
the member states, the rows and the ex-ante years and the conditions, and calls them; the arithmetic is the port's, so
the supports are unchanged.
"""
from __future__ import annotations


def P_Result_NTRD_Support(grof, mapr, domm, dompos, dompos_expert, domm_expert):
    r"""P_Result(MS, "NTRD", S_RowsEst, ExAnte, "Support"): production (GROF, else MAPR) less DOMM where DOMM has an
    expert but none of its positions has, else less the positions' supports.

    dompos, dompos_expert: the DOMPOS' supports and experts, in the caller's order; domm_expert: DOMM's expert.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 29-45):

            P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support")
        *            -- Kicks out COMI, for example:
              $ (  (P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"))
                 $ (P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support") or P_Result(MS,"MAPR",S_RowsEst,ExAnte,"Support") or P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support")))
            =  P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support")
             + P_Result(MS,"MAPR",S_RowsEst,ExAnte,"Support") $ (NOT P_Result(MS,"GROF",S_RowsEst,ExAnte,"Support"))
             - P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Support")
        *            -- If there are DGAgri supports for total demand but no DGAgri (or Expert) info
        *               for DOMPOS define NTRD as Prd-DOMM. Otherwise the default trend supports
        *               for DOMPOS may dominate the DGAgri info on DOMM indirectly via the support for NTRD
                     $ (   (NOT SUM(DOMPOS,   P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Expert")))
                        $  P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Expert"))
             - SUM(DOMPOS, P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Support"))
        *            -- If there are no DGAgri supports for total demand or if there is more precise info
        *               use the DOMPOS assigned above or already assigned in define_stats_and_supports
                     $ (    SUM(DOMPOS,   P_Result(MS,DOMPOS,S_RowsEst,ExAnte,"Expert"))
                        or  (NOT  P_Result(MS,"DOMM",S_RowsEst,ExAnte,"Expert")));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    dom_ex = sum(dompos_expert)
    return (grof + (mapr if not grof else 0.0) - (domm if (not dom_ex and domm_expert) else 0.0)
            - (sum(dompos) if (dom_ex or not domm_expert) else 0.0))


def P_Result_trade_series(value):
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "series"): the supports before the correction.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 134-134):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") = P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support");

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 135-135):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") = P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return value


def P_Result_NTRD_series(expt, impt):
    r"""P_Result(MS, "NTRD", S_RowsEst, ExAnte, "series"): the old implied NTRD, EXPT - IMPT.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 136-139):

            P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
            $ (  P_Result(MS,"NTRD",S_RowsEst,ExAnte,"support")
              $ (P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")))
              = (P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")-P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return expt - impt


def P_Result_IMPT_Support(impt, expt, ntrd, ntrd_series):
    r"""P_Result(MS, "IMPT", S_RowsEst, ExAnte, "Support"): the NTRD change relative to gross trade subtracted from the
    old import support (potentially negative).

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 142-147):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") $ ((   P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
                                                                + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")) GT 1.E-6)
             = P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")
        *           -- Change relative to total gross trade is substracted from old import support
             * (1. -(P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support") - P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series") )
                   /(P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") ) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return impt * (1. - (ntrd - ntrd_series) / (expt + impt))


def P_Result_EXPT_Support(impt, expt, ntrd, ntrd_series):
    r"""P_Result(MS, "EXPT", S_RowsEst, ExAnte, "Support"): the NTRD change relative to gross trade added to the old
    export support (potentially negative).

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 150-155):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") $ ((   P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
                                                                + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series")) GT 1.E-6)
             = P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series")
        *           -- Change relative to total gross trade is added to old export support
             * (1. +(P_Result(MS,"NTRD",S_RowsEst,ExAnte,"Support") - P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series") )
                   /(P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") + P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") ) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return expt * (1. + (ntrd - ntrd_series) / (expt + impt))


def P_Result_trade_series_reset():
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "series"): emptied before the estimates.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 157-158):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") = 0;
            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return 0.0


def P_Result_IMPT_series(impt_basm, impt, expt):
    r"""P_Result(MS, "IMPT", S_RowsEst, ExAnte, "series"): the import estimate, at least 1E-6 BASM, increased by any
    negative exports.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 161-165):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series") $ (  P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
                                                            or P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support")
                                                            or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") )
             = MAX(1.E-6*P_Result(MS,"IMPT",S_RowsEst,ExAnte,"BASM"),P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support"))
             + MAX(0.,-P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return max(1.E-6 * impt_basm, impt) + max(0., -expt)


def P_Result_EXPT_series(expt_basm, expt, impt):
    r"""P_Result(MS, "EXPT", S_RowsEst, ExAnte, "series"): the export estimate, at least 1E-6 BASM, increased by any
    negative imports.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 168-172):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series") $ (  P_Result(MS,"NTRD",S_RowsEst,ExAnte,"series")
                                                            or P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support")
                                                            or P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") )
             = MAX(1.E-6*P_Result(MS,"EXPT",S_RowsEst,ExAnte,"BASM"),P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support"))
             + MAX(0.,-P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return max(1.E-6 * expt_basm, expt) + max(0., -impt)


def P_Result_trade_Support(series):
    r"""P_Result(MS, "IMPT" / "EXPT", S_RowsEst, ExAnte, "Support"): the estimates.

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 174-174):

            P_Result(MS,"IMPT",S_RowsEst,ExAnte,"Support") =  P_Result(MS,"IMPT",S_RowsEst,ExAnte,"series");

    CAPRI's GAMS (captrd/adjust_trade_supports.gms l. 175-175):

            P_Result(MS,"EXPT",S_RowsEst,ExAnte,"Support") =  P_Result(MS,"EXPT",S_RowsEst,ExAnte,"series");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (final_supports.adjust_trade)."""
    return series

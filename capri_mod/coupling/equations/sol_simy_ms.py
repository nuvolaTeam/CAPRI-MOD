r"""CAPRI's farm balance and accounts at producer prices of a member state at the simulation year (reports/sol_simy.gms,
star 3.0): the net trade NETF = GROF - SEDF - LOSF - INTF of each item, its seed and losses on farm in fixed
proportion to production, the young animals' internal use, the fertilisers' purchases summed over the regions, and the
unit value at producer prices UVAG x NETF / GROF. capri_mod/income/eaa_ms.py applies them to a member state's units
(income I2c); EAAP = NETF x UVAP / 1000 is coupling/equations/sol_simy.py DATA_EAAP_IO.
"""
from __future__ import annotations


def DATA_NETF_FNUT_MSAGG(NETF_NUTS2):
    r"""DATA(MSAGG, "NETF", FNUT, SIMY): a member state's mineral fertiliser purchases, the sum over its regions' (kt).

    CAPRI's GAMS (reports/sol_simy.gms l. 315):

           DATA(MSAGG,"NETF",FNUT,"%SIMY%")       = SUM(MAP_RR(MSAGG,NUTS2), DATA(NUTS2,"NETF",FNUT,"%SIMY%"));

    Departures from CAPRI: none."""
    return float(sum(float(v) for v in NETF_NUTS2))


def DATA_INTF_IYANI(GROF_IYANI):
    r"""DATA(MS, "INTF", IYANI, SIMY): the young animals bought (the inputs IYANI) are internal use of the farms.

    CAPRI's GAMS (reports/sol_simy.gms l. 789-791):

        *      --- internal use of the young animal side always covered by "internal use"
        *
           DATA(MS,"INTF",IYANI,"%SIMY%") = DATA(MS,"GROF",IYANI,"%SIMY%");

    Departures from CAPRI: none."""
    return float(GROF_IYANI)


def DATA_INTF_OYANI(INTF_IYANI):
    r"""DATA(MS, "INTF", OYANI, SIMY): the young animals' internal use on the output side, the internal use of the inputs
    they map to (O_TO_YANI; a sequence).

    CAPRI's GAMS (reports/sol_simy.gms l. 793-795):

        *      --- .. which is identical to internal use on the output side
        *
           DATA(MS,"INTF",OYANI,"%SIMY%") = SUM( O_TO_YANI(OYANI,IYANI), DATA(MS,"INTF",IYANI,"%SIMY%"));

    Departures from CAPRI: none."""
    return float(sum(float(v) for v in INTF_IYANI))


def DATA_NETF_OYANI(GROF, INTF):
    r"""DATA(MS, "NETF", OYANI, SIMY): the young animals' net trade, their production less their internal use.

    CAPRI's GAMS (reports/sol_simy.gms l. 797-799):

        *      --- the differences to own production is "net trade"
        *
           DATA(MS,"NETF",OYANI,"%SIMY%") = DATA(MS,"GROF",OYANI,"%SIMY%") - DATA(MS,"INTF",OYANI,"%SIMY%");

    Departures from CAPRI: none."""
    return float(GROF) - float(INTF)


def DATA_SEDF_O_SIMY(GROF_SIMY, SEDF_CUR, GROF_CUR, END=True):
    r"""DATA(MS, "SEDF", O, SIMY): a final product's seed use on farm, in fixed proportion to its production at "CUR".

    CAPRI's GAMS (reports/sol_simy.gms l. 1889-1892):

        *----- seed use and v_lossQuant on farm in fixed proportion to production
        *
           DATA(MS,"SEDF",O,"%SIMY%") $ (DATA(MS,"GROF",O,"CUR")  $ DATA(MS,"SEDF",O,"CUR") $ END(O))
             = DATA(MS,"GROF",O,"%SIMY%") * DATA(MS,"SEDF",O,"CUR")/DATA(MS,"GROF",O,"CUR");

    In this project's notation: SEDF = GROF x SEDF_CUR / GROF_CUR where GROF_CUR and SEDF_CUR are not 0 and O is in END
    (0 otherwise). "CUR" is CAPRI's data of the simulation year (sim_ini_21730's "Y" for 2030; "BAS" at the base year).
    Departures from CAPRI: none."""
    return float(GROF_SIMY) * float(SEDF_CUR) / float(GROF_CUR) if (END and float(GROF_CUR) and float(SEDF_CUR)) else 0.0


def DATA_LOSF_O_SIMY(GROF_SIMY, LOSF_CUR, GROF_CUR, END=True):
    r"""DATA(MS, "LOSF", O, SIMY): a final product's losses on farm, in fixed proportion to its production at "CUR".

    CAPRI's GAMS (reports/sol_simy.gms l. 1897-1898):

           DATA(MS,"LOSF",O,"%SIMY%") $ (DATA(MS,"GROF",O,"CUR")  $ DATA(MS,"LOSF",O,"CUR") $ END(O))
             = DATA(MS,"GROF",O,"%SIMY%") * DATA(MS,"LOSF",O,"CUR")/DATA(MS,"GROF",O,"CUR");

    In this project's notation: LOSF = GROF x LOSF_CUR / GROF_CUR as DATA_SEDF_O_SIMY. Departures from CAPRI: none."""
    return float(GROF_SIMY) * float(LOSF_CUR) / float(GROF_CUR) if (END and float(GROF_CUR) and float(LOSF_CUR)) else 0.0


def DATA_NETF_MS(GROF, SEDF=0.0, LOSF=0.0, INTF=0.0):
    r"""DATA(MS, "NETF", IO, SIMY): a member state's net production or use of an item for the accounts, its gross
    production or use less its seed, losses and internal use on farm (CalNetf: the farm balance's positions but GROF
    and NETF).

    CAPRI's GAMS (reports/sol_simy.gms l. 1964-1970):

        *----- Sales activities for member state
        *
           CalNetf(FRMBAL) = YES;
           CalNetf("GROF") = NO;
           CalNetf("NETF") = NO;

           DATA(MS,"NETF",IO,"%SIMY%") = DATA(MS,"GROF",IO,"%SIMY%") - SUM(CalNetf, DATA(MS,CalNetf,IO,"%SIMY%"));

    In this project's notation: NETF = GROF - SEDF - LOSF - INTF. Departures from CAPRI: none."""
    return float(GROF) - float(SEDF) - float(LOSF) - float(INTF)


def DATA_UVAP_MS(UVAG, NETF, GROF):
    r"""DATA(MS, "UVAP", ROWS, SIMY): a member state's unit value at producer prices, its unit value in the gross
    account times its net over its gross production or use, where both are not 0 (GROF above eps) and it has a UVAG.

    CAPRI's GAMS (reports/sol_simy.gms l. 2389-2390):

           DATA(MS,"UVAP",ROWS,"%SIMY%") $ (Data(MS,"NETF",ROWS,"%SIMY%") $ (Data(MS,"GROF",ROWS,"%SIMY%") GT eps) $ Data(MS,"UVAG",ROWS,"%SIMY%"))
             =  Data(MS,"UVAG",ROWS,"%SIMY%") * Data(MS,"NETF",ROWS,"%SIMY%")/Data(MS,"GROF",ROWS,"%SIMY%");

    In this project's notation: UVAP = UVAG x NETF / GROF, so EAAP = NETF x UVAP / 1000 = EAAG x (NETF / GROF)^2 (in
    CAPRI's 2030 reference Denmark's 73 of 77 items: N fertiliser 600.68 x (226.10 / 442.38)^2 = 156.91; the others are
    the bioethanol, biodiesel, DDGS and the dairies' MILK, which no farm activity produces). Departures from CAPRI:
    none (where the condition fails, UVAP keeps its value: the caller's)."""
    if float(NETF) and float(GROF) > 1e-12 and float(UVAG):
        return float(UVAG) * float(NETF) / float(GROF)
    return None


def DATA_INTF_FNUT(GROF, NETF):
    r"""DATA(RS, "INTF", FNUT, SIMY): a region's or member state's internal use of the fertiliser nutrients, its need
    (GROF) less its purchases (NETF).

    CAPRI's GAMS (reports/sol_simy.gms l. 864-866):

        *  ---- internal use of organic fertiliser per region
        *
           DATA(RS,"INTF",FNUT,"%SIMY%") = DATA(RS,"GROF",FNUT,"%SIMY%") - DATA(RS,"NETF",FNUT,"%SIMY%");

    In this project's notation: INTF = GROF - NETF (kt). Departures from CAPRI: none."""
    return float(GROF) - float(NETF)


def DATA_LOSF_FOUT(GROF, INTF):
    r"""DATA(RS, "LOSF", FOUT, SIMY): the losses of the manure outputs (MANN, MANP, MANK), their production less their
    internal use (the manure applied, v_fertDist's EXCR at l. 870).

    CAPRI's GAMS (reports/sol_simy.gms l. 872-874):

        *       ---- v_lossQuant of organic fertiliser per region
        *
           DATA(RS,"LOSF",FOUT,"%SIMY%") = DATA(RS,"GROF",FOUT,"%SIMY%") - DATA(RS,"INTF",FOUT,"%SIMY%");

    In this project's notation: LOSF = GROF - INTF, so the manure's NETF = GROF - LOSF - INTF (DATA_NETF_MS) is 0 at
    any INTF. Departures from CAPRI: none (the split between INTF and LOSF does not enter the accounts)."""
    return float(GROF) - float(INTF)


def DATA_BALPOS_REGAGG(BALPOS_MS):
    r"""DATA(REGAGG, BALPOS, ROWS, SIMY): a regional aggregate's balance position (GROF, NETF), the sum over its member
    states' (MAP_RR).

    CAPRI's GAMS (reports/sol_simy.gms l. 2317-2322):

        $batinclude 'util\title.gms' "' Post model reporting: Member States aggregates of balance positions and other info'"
        *
        *----- Eu aggregation
        *
           DATA(REGAGG,BALPOS,ROWS,"%SIMY%")   $ (not DATA(REGAGG,BALPOS,ROWS,"%SIMY%")  )
             = SUM(MAP_RR(REGAGG,MS) $ DATA(MS,BALPOS,ROWS,"%SIMY%"),   DATA(MS,BALPOS,ROWS,"%SIMY%"));

    Departures from CAPRI: none (the model computes an aggregate only where all its member states have their accounts:
    capri_mod/income/eaa_aggregates.py)."""
    return float(sum(float(v) for v in BALPOS_MS))


def DATA_UVAG_REGAGG(GROF_MS, UVAG_MS, GROF):
    r"""DATA(REGAGG, "UVAG", ROWS, SIMY): a regional aggregate's unit value, its member states' weighted by their gross
    production (where GROF is above eps; the MAPR term for the processed products not used); None otherwise.

    CAPRI's GAMS (reports/sol_simy.gms l. 2365-2368):

           DATA(REGAGG,"UVAG",ROWS,SIMY_BAS) $ ( (DATA(REGAGG,"GROF",ROWS,SIMY_BAS) + DATA(REGAGG,"MAPR",ROWS,SIMY_BAS) $ (NOT DATA(REGAGG,"GROF",ROWS,SIMY_BAS))) GT EPS)
              = SUM(MAP_RR(REGAGG,MS) $ p_dataCopy(MS,"UVAG",ROWS,SIMY_BAS),
                      (p_dataCopy(MS,"GROF",ROWS,SIMY_BAS) + p_dataCopy(MS,"MAPR",ROWS,SIMY_BAS) $ (NOT p_dataCopy(MS,"GROF",ROWS,SIMY_BAS)))
                             * p_dataCopy(MS,"UVAG",ROWS,SIMY_BAS))/(DATA(REGAGG,"GROF",ROWS,SIMY_BAS) + DATA(REGAGG,"MAPR",ROWS,SIMY_BAS) $ (NOT DATA(REGAGG,"GROF",ROWS,SIMY_BAS)));

    Departures from CAPRI: none."""
    if not float(GROF) > 1e-12:
        return None
    return float(sum(float(g) * float(u) for g, u in zip(GROF_MS, UVAG_MS) if u is not None)) / float(GROF)


def DATA_UVAP_REGAGG(NETF_MS, UVAP_MS, NETF):
    r"""DATA(REGAGG, "UVAP", ROWS, SIMY): a regional aggregate's unit value at producer prices, its member states'
    weighted by their net production (where NETF is above eps; a member state without UVAP left out); None otherwise.

    CAPRI's GAMS (reports/sol_simy.gms l. 2394-2398):

           p_dataCopy(MS,"UVAP",ROWS,"%SIMY%") = data(MS,"UVAP",ROWS,"%SIMY%");

           DATA(REGAGG,"UVAP",ROWS,"%SIMY%") $ (DATA(REGAGG,"NETF",ROWS,"%SIMY%") GT eps)
              = SUM(MAP_RR(REGAGG,MS) $ p_DataCopy(MS,"UVAP",ROWS,"%SIMY%"),
                         p_dataCopy(MS,"NETF",ROWS,"%SIMY%") * p_DataCopy(MS,"UVAP",ROWS,"%SIMY%"))/DATA(REGAGG,"NETF",ROWS,"%SIMY%");

    Departures from CAPRI: none."""
    if not float(NETF) > 1e-12:
        return None
    return float(sum(float(n) * float(u) for n, u in zip(NETF_MS, UVAP_MS) if u is not None)) / float(NETF)


def DATA_UVAB_REGAGG(NETF_MS, UVAB_MS, NETF):
    r"""DATA(REGAGG, "UVAB", ROWS, SIMY): a regional aggregate's unit value at basic prices, as DATA_UVAP_REGAGG.

    CAPRI's GAMS (reports/sol_simy.gms l. 2400-2403):

           p_dataCopy(MS,"UVAB",ROWS,"%SIMY%") = data(MS,"UVAB",ROWS,"%SIMY%");
           DATA(REGAGG,"UVAB",ROWS,"%SIMY%") $ (DATA(REGAGG,"NETF",ROWS,"%SIMY%") GT eps)
              = SUM(MAP_RR(REGAGG,MS) $ p_dataCopy(MS,"UVAB",ROWS,"%SIMY%"),
                         p_dataCopy(MS,"NETF",ROWS,"%SIMY%") * p_dataCopy(MS,"UVAB",ROWS,"%SIMY%"))/DATA(REGAGG,"NETF",ROWS,"%SIMY%");

    Departures from CAPRI: none."""
    if not float(NETF) > 1e-12:
        return None
    return float(sum(float(n) * float(u) for n, u in zip(NETF_MS, UVAB_MS) if u is not None)) / float(NETF)

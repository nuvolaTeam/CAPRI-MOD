r"""The base year from CAPREG's data with CAPRI's corrections (l. 44-199) (capmod/load_base_data_and_trends.gms; moved
from capri_mod/projection/equations/load_base_data_and_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.projection.equations.year_data.data_sets import Data, YearSets  # noqa: E402




def DATA2_base_deletions(D2b: Data, S: YearSets) -> None:
    r"""The base year's data CAPRI does not use deleted: the animals' requirement rows, CATT, the activities' CARB, the
    EAA, the outputs' feed contents but CRPR and DRMA, and the regions' (not the member states') contents of the
    feeds but CRPR.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 44-56):

        *   --- delete data which are not used in the following
        *
           DATA2(RS,AACT,REQSR_M,"Y")   = 0;
            DATA2(RS,AACT,"CATT","Y")   = 0;
            DATA2(RS,PACT,"CARB","Y")   = 0;
        *
            SET EAA(COLS) / EAAP,EAAB,EAAG /;
            DATA2(RS,EAA,ROWS,"Y")      = 0;
        *
        *  --- delete data never needed in the following (requirement content of outputs)
        *      except those for CRPR and DRMA which are used in digestibility.gms
            DATA2(RS,REQSC,OSECO,"Y") $ (NOT (SAMEAS(REQSC,"CRPR") or SAMEAS(REQSC,"DRMA")))  = 0;
            DATA2(RU,REQSC,FEED,"Y")  $ ((NOT SUM(SAMEAS(RU,MS),1)) and (NOT SAMEAS(REQSC,"CRPR"))) = 0;

    Departures from CAPRI: none."""
    for (c, w) in D2b.keys("Y"):
        if ((c in S.AACT and (w in S.REQSR_M or w == "CATT")) or (c in S.PACT and w == "CARB")
                or c in ("EAAP", "EAAB", "EAAG") or (c in S.REQSC and w in S.OSECO and c not in ("CRPR", "DRMA"))):
            for r in list(D2b.at(c, w, "Y")):
                if r in S.RS:
                    D2b.set(r, c, w, "Y", 0)
        elif c in S.REQSC and w in S.FEED and c != "CRPR":
            for r in list(D2b.at(c, w, "Y")):
                if r in S.RU and r not in S.MS:
                    D2b.set(r, c, w, "Y", 0)


def DATA2_base_labour_and_nutrients(D2b: Data, S: YearSets) -> None:
    r"""The labour rows of MINS and PRME deleted, and CAPREG's nutrient imports and exports per ha turned into totals.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 125-131):

            DATA2(RS,"MINS","LABT","Y") = 0;
            DATA2(RS,"MINS","LABF","Y") = 0;
            DATA2(RS,"PRME","LABF","Y") = 0;

        *  --- Convert capreg data on IMPORT/EXPPRD from perha to total as in capmod output
            DATA2(RS,"EXPPRD",FNUT,"Y") = DATA2(RS,"EXPPRD",FNUT,"Y") * DATA2(RS,"UAAR","LEVL","Y") / 1000;
            DATA2(RS,"IMPORT",FNUT,"Y") = DATA2(RS,"IMPORT",FNUT,"Y") * DATA2(RS,"UAAR","LEVL","Y") / 1000;

    Departures from CAPRI: none."""
    for c, w in (("MINS", "LABT"), ("MINS", "LABF"), ("PRME", "LABF")):
        for r in list(D2b.at(c, w, "Y")):
            if r in S.RS:
                D2b.set(r, c, w, "Y", 0)
    for c in ("EXPPRD", "IMPORT"):
        for f in S.FNUT:
            for r, v in list(D2b.at(c, f, "Y").items()):
                if r in S.RS:
                    D2b.set(r, c, f, "Y", v * D2b.get(r, "UAAR", "LEVL", "Y") / 1000.)


def DATA_BAS_from_capreg(D: Data, D2b: Data, S: YearSets) -> None:
    r"""The base year on "BAS" from CAPREG's results, over the columns and rows CAPRI reads (where CAPREG has a value);
    the activities' greenhouse gas aggregates, the animals' MINS and MAXS and the area's gas aggregates deleted; the
    water rows of "Y" deleted.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 61):

            DATA(RS,CACT,"WATR","Y") = 0;

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 139-144):

            DATA(RS,ColsRead,RowsRead,"BAS") $ DATA2(RS,ColsRead,RowsRead,"Y") = DATA2(RS,ColsRead,RowsRead,"Y");
            DATA(RS,PACT,GASAGG,"BAS") = 0;
            DATA(RS,MAACT,"MINS","BAS") = 0;
            DATA(RS,MAACT,"MAXS","BAS") = 0;
            DATA(RS,"UAAR",GASAGG,"BAS") = 0;
            DATA(RS,PACT,"WATR","Y")   = 0;

    Departures from CAPRI: none."""
    for a in S.CACT:
        for r in list(D.at(a, "WATR", "Y")):
            if r in S.RS:
                D.set(r, a, "WATR", "Y", 0)
    for (c, w) in D2b.keys("Y"):
        if c in S.ColsRead and w in S.RowsRead:
            for r, v in D2b.at(c, w, "Y").items():
                if r in S.RS:
                    D.set(r, c, w, "BAS", v)
    for (c, w) in D.keys("BAS"):
        if (c in S.PACT and w in S.GASAGG) or (c in S.MAACT and w in ("MINS", "MAXS")) or (c == "UAAR" and w in S.GASAGG):
            for r in list(D.at(c, w, "BAS")):
                if r in S.RS:
                    D.set(r, c, w, "BAS", 0)
    for a in S.PACT:
        for r in list(D.at(a, "WATR", "Y")):
            if r in S.RS:
                D.set(r, a, "WATR", "Y", 0)


def check_uaar_base(D: Data, S: YearSets) -> None:
    r"""A region without the base year's agricultural area stops the run.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 192-195):

            set empty; empty(rs) $ (NOT DATA(RS,"UAAR","LEVL","BAS")) = YES;
            if ( card(empty) ne 0,
                abort "Missing base year data for agricultural area for some regions, %system.fn% %system.incline%",empty;
            );

    Departures from CAPRI: none."""
    empty = sorted(r for r in S.RS if not D.get(r, "UAAR", "LEVL", "BAS"))
    if empty:
        raise ValueError(f"Missing base year data for agricultural area for some regions: {empty}")


def DATA_CERE_HSTY(D: Data, D2b: Data, S: YearSets) -> None:
    r"""The cereals' HSTY row of CAPREG's base year at "BAS", "Y" and "TRD".

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 197-199):

            DATA(RS,"CERE","HSTY","BAS")     = DATA2(RS,"CERE","HSTY","Y");
            DATA(RS,"CERE","HSTY","Y")       = DATA2(RS,"CERE","HSTY","Y");
            DATA(RS,"CERE","HSTY","TRD")     = DATA2(RS,"CERE","HSTY","Y");

    Departures from CAPRI: none."""
    for t in ("BAS", "Y", "TRD"):
        for r in S.RS:
            D.set(r, "CERE", "HSTY", t, D2b.get(r, "CERE", "HSTY", "Y"))

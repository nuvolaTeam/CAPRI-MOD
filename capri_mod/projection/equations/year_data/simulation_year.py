r"""The simulation year's data ("Y"): the young animals, the deletions, the feed balances, the split activities, the
biofuel and milk positions (capmod/load_base_data_and_trends.gms; moved from
capri_mod/projection/equations/load_base_data_and_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.projection.equations.year_data.data_sets import Data, YearSets  # noqa: E402




def DATA_Y_(D: Data, S: YearSets, FROM_CAPTRD: set) -> None:
    r"""The year's data: the trends where CAPTRD projects the position, the base year elsewhere.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 598-599):

            DATA(RS,ColsRead,RowsRead,"Y") = DATA(RS,ColsRead,RowsRead,"BAS") $ (NOT FROM_CAPTRD(ColsRead,RowsRead))
                                           + DATA(RS,ColsRead,RowsRead,"TRD") $ FROM_CAPTRD(ColsRead,RowsRead);

    Departures from CAPRI: none."""
    keys = {(c, w) for t in ("Y", "BAS", "TRD") for (c, w) in D.keys(t) if c in S.ColsRead and w in S.RowsRead}
    for (c, w) in keys:
        src = "TRD" if (c, w) in FROM_CAPTRD else "BAS"
        for r in list(D.at(c, w, "Y")):
            if r in S.RS:
                D.set(r, c, w, "Y", 0)
        for r, v in D.at(c, w, src).items():
            if r in S.RS:
                D.set(r, c, w, "Y", v)


def DATA_Y_UAAR(D: Data, S: YearSets) -> None:
    r"""The year's agricultural area: the sum of the crop activities' levels.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 632):

            DATA(RS,"uaar","levl","Y") = SUM(cact, DATA(RS,cact,"levl","Y"));

    Departures from CAPRI: none."""
    for r in S.RS:
        D.set(r, "UAAR", "LEVL", "Y", sum(D.get(r, a, "LEVL", "Y") for a in S.CACT))


def DATA_young_animal_coefficients(D: Data, S: YearSets) -> None:
    r"""The young animals' input and output coefficients of a region from its member state's base year where missing,
    and their gross production at "TRD" and "Y".

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 664-670):

           DATA(RU,MAACT,OIYANI,"BAS") $ ((NOT DATA(RU,MAACT,OIYANI,"BAS")) and PACT_TO_IO(MAACT,OIYANI) and DATA(RU,MAACT,"LEVL","BAS"))
              = SUM(R_RAGG(RU,MS), DATA(MS,MAACT,OIYANI,"BAS"));
           DATA(RU,MAACT,OIYANI,"TRD") $ ((NOT DATA(RU,MAACT,OIYANI,"TRD")) and PACT_TO_IO(MAACT,OIYANI) and DATA(RU,MAACT,"LEVL","BAS"))
              = SUM(R_RAGG(RU,MS), DATA(MS,MAACT,OIYANI,"BAS"));
        *
           DATA(RS,"GROF",OIYANI,"TRD") = SUM(PACT_TO_IO(MAACT,OIYANI), DATA(RS,MAACT,OIYANI,"TRD")*DATA(RS,MAACT,"LEVL","TRD")) * 0.001;
           DATA(RS,"GROF",OIYANI,"Y")   = SUM(PACT_TO_IO(MAACT,OIYANI), DATA(RS,MAACT,OIYANI,"Y")  *DATA(RS,MAACT,"LEVL","Y")) * 0.001;

    Departures from CAPRI: none."""
    ms_of = {}
    for (ru, ms) in S.R_RAGG:
        if ms in S.MS:                          # the sum's index is MS
            ms_of.setdefault(ru, []).append(ms)
    pairs = [(a, y) for (a, y) in S.PACT_TO_IO if a in S.MAACT and y in S.OIYANI]
    for t in ("BAS", "TRD"):
        for (a, y) in pairs:
            for ru in S.RU:
                if not D.get(ru, a, y, t) and D.get(ru, a, "LEVL", "BAS"):
                    D.set(ru, a, y, t, sum(D.get(ms, a, y, "BAS") for ms in ms_of.get(ru, ())))
    for t in ("TRD", "Y"):
        for y in S.OIYANI:
            acts = [a for (a, yy) in pairs if yy == y]
            for r in S.RS:
                D.set(r, "GROF", y, t, sum(D.get(r, a, y, t) * D.get(r, a, "LEVL", t) for a in acts) * 0.001)


def DATA_delete_positions(D: Data, S: YearSets) -> None:
    r"""The unit values of the regions below the member states (but the fodder's), the agricultural area's rows, the
    member states' inhabitants' rows but LEVL, and the activities' requirement rows on "TRD" deleted.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 672-676):

           DATA(RS,MAPP,IO,SCEN) $ ((NOT SUM(SAMEAS(MS,RS),1)) and (NOT FODDIO(IO))) = 0;
           DATA(RS,"UAAR",IO,SCEN) = 0;
        *
           DATA(MS,"INHA",ROWS,"TRD") $ (NOT SAMEAS(ROWS,"LEVL"))= 0;
           DATA(RS,PACT,REQSR_M,"TRD")  = 0;

    Departures from CAPRI: none."""
    for t in S.SCEN:
        for (c, w) in D.keys(t):
            if c in S.MAPP and w in S.IO and w not in S.FODDIO:
                for r in list(D.at(c, w, t)):
                    if r in S.RS and r not in S.MS:
                        D.set(r, c, w, t, 0)
            if c == "UAAR" and w in S.IO:
                for r in list(D.at(c, w, t)):
                    if r in S.RS:
                        D.set(r, c, w, t, 0)
    for (c, w) in D.keys("TRD"):
        if (c == "INHA" and w != "LEVL") or (c in S.PACT and w in S.REQSR_M):
            for r in list(D.at(c, w, "TRD")):
                if (c == "INHA" and r in S.MS) or (c != "INHA" and r in S.RS):
                    D.set(r, c, w, "TRD", 0)


def DATA_MS_feed_balances(D: Data, S: YearSets) -> None:
    r"""The member states' young animals' gross production at "TRD" from "BAS" where missing; the feed use of the
    milk for feeding at its gross production; the feeds' gross production and feed use from their rows' feed use; the
    feeds' domestic use without feed use deleted; the feeds' unit values at "TRD" from "Y" where missing.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 678-693):

           DATA(MS,"GROF",OIYANI,"TRD") $ (NOT DATA(MS,"GROF",OIYANI,"TRD")) = DATA(MS,"GROF",OIYANI,"BAS");
        *

           DATA(MS,"FEDM","COMF","Y")    = DATA(MS,"GROF","COMF","Y");
           DATA(MS,"FEDM","COMF","TRD")  = DATA(MS,"GROF","COMF","TRD");

           DATA(MS,"FEDM","SGMF","Y")    = DATA(MS,"GROF","SGMF","Y");
           DATA(MS,"FEDM","SGMF","TRD")  = DATA(MS,"GROF","SGMF","TRD");

        *
           DATA(MS,"GROF",FEED,"Y")   = SUM(FEED_TO_O(FEED,ROWS), DATA(MS,"FEDM",ROWS,"Y"));
           DATA(MS,"GROF",FEED,"TRD") = SUM(FEED_TO_O(FEED,ROWS), DATA(MS,"FEDM",ROWS,"TRD"));
           DATA(MS,"FEDM",FEED,"Y")   = SUM(FEED_TO_O(FEED,ROWS), DATA(MS,"FEDM",ROWS,"Y"));
           DATA(MS,"DOMM",FEED,"Y") $ (NOT DATA(MS,"FEDM",FEED,"Y")) = 0;

           DATA(RS,"UVAG",FEED,"TRD")   $ (NOT DATA(RS,"UVAG",FEED,"TRD")) = DATA(RS,"UVAG",FEED,"Y");

    Departures from CAPRI: none."""
    for y in S.OIYANI:
        for ms in S.MS:
            if not D.get(ms, "GROF", y, "TRD"):
                D.set(ms, "GROF", y, "TRD", D.get(ms, "GROF", y, "BAS"))
    for item in ("COMF", "SGMF"):
        for t in ("Y", "TRD"):
            for ms in S.MS:
                D.set(ms, "FEDM", item, t, D.get(ms, "GROF", item, t))
    rows_of = {}
    for (f, o) in S.FEED_TO_O:
        if f in S.FEED:
            rows_of.setdefault(f, []).append(o)
    # one statement after the other, as GAMS (a feed's rows could hold another feed's FEDM, l. 690)
    for col, src in (("GROF", "Y"), ("GROF", "TRD"), ("FEDM", "Y")):
        for f in S.FEED:
            for ms in S.MS:
                D.set(ms, col, f, src, sum(D.get(ms, "FEDM", o, src) for o in rows_of.get(f, ())))
    for f in S.FEED:
        for ms in S.MS:
            if not D.get(ms, "FEDM", f, "Y"):
                D.set(ms, "DOMM", f, "Y", 0)
    for f in S.FEED:
        for r in S.RS:
            if not D.get(r, "UVAG", f, "TRD"):
                D.set(r, "UVAG", f, "TRD", D.get(r, "UVAG", f, "Y"))


def DATA_split_activities(D: Data, S: YearSets) -> None:
    r"""The split activities' (DCOL/DCOH, BULL/BULH, HEIL/HEIH, GRAE/GRAI) coefficients at "TRD", where missing, as
    their base year's times the trend's change of the activity they split; "Y" = "TRD" for them.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 697-701):

           DATA(RS,SplitActs,IOP,"TRD") $ (PACT_TO_IO(SplitActs,IOP) and (NOT DATA(RS,SplitActs,IOP,"TRD"))
                                  and SUM(DACT_TO_PACT(DACT,SplitActs), DATA(RS,DACT,IOP,"BAS")*DATA(RS,DACT,IOP,"TRD")))
            = DATA(RS,SplitActs,IOP,"BAS") * SUM(DACT_TO_PACT(DACT,SplitActs), DATA(RS,DACT,IOP,"TRD")/DATA(RS,DACT,IOP,"BAS"));
        *
           DATA(RS,SplitActs,IOP,"Y")  = DATA(RS,SplitActs,IOP,"TRD");

    Departures from CAPRI: none."""
    dacts = {}
    for (d, sa) in S.DACT_TO_PACT:
        dacts.setdefault(sa, []).append(d)
    for sa in S.SplitActs:
        ios = [io for (a, io) in S.PACT_TO_IO if a == sa and io in S.IOP]
        for io in ios:
            for r in S.RS:
                if D.get(r, sa, io, "TRD"):
                    continue
                ds = dacts.get(sa, ())
                if not sum(D.get(r, d, io, "BAS") * D.get(r, d, io, "TRD") for d in ds):
                    continue
                D.set(r, sa, io, "TRD", D.get(r, sa, io, "BAS")
                      * sum(D.get(r, d, io, "TRD") / D.get(r, d, io, "BAS") for d in ds if D.get(r, d, io, "BAS")))
        for io in S.IOP:
            for r in S.RS:
                D.set(r, sa, io, "Y", D.get(r, sa, io, "TRD"))


def DATA_delete_after_year(D: Data, S: YearSets) -> None:
    r"""The activities' non-feed coefficients on "TRD", the animals' requirement rows and the DACT activities' data
    deleted ("Y" holds what the simulation uses).

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 707-709):

           DATA(RS,PACT,IOP,"TRD")     $ (PACT_TO_IO(PACT,IOP) and (NOT SUM(SAMEAS(FEED,IOP),1))) = 0;
           DATA(RS,AACT,REQSR_M,SCEN)   = 0;
           DATA(RS,DACT,ROWS,SCEN)    = 0;

    Departures from CAPRI: none."""
    pio = {(a, io) for (a, io) in S.PACT_TO_IO if a in S.PACT and io in S.IOP and io not in S.FEED}
    for (c, w) in D.keys("TRD"):
        if (c, w) in pio:
            for r in list(D.at(c, w, "TRD")):
                if r in S.RS:
                    D.set(r, c, w, "TRD", 0)
    for t in S.SCEN:
        for (c, w) in D.keys(t):
            if (c in S.AACT and w in S.REQSR_M) or (c in S.DACT and w in S.ROWS):
                for r in list(D.at(c, w, t)):
                    if r in S.RS:
                        D.set(r, c, w, t, 0)


def DATA_NO_QUTS_SGMI(D: Data, S: YearSets) -> None:
    r"""Norway's sheep and goat milk quota at its production.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 711-713):

        *  ---- WB: intermediate solution for sheep & goat milk quota in NO
        *
           DATA("NO000000","QUTS","SGMI","Y") = DATA("NO000000","GROF","SGMI","Y");

    Departures from CAPRI: none."""
    D.set("NO000000", "QUTS", "SGMI", "Y", D.get("NO000000", "GROF", "SGMI", "Y"))


def DATA_BIOF_PRCB_WHEA(D: Data, S: YearSets) -> None:
    r"""Wheat's biofuel feedstock use, the sum of soft and durum wheat's, and its processing coefficients, soft wheat's.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 720-725):

           DATA(RMS,"BIOF","WHEA",SCEN) =  DATA(RMS,"BIOF","SWHE",SCEN) + DATA(RMS,"BIOF","DWHE",SCEN);
           DATA(RMS,"BIOF","WHEA","TRD") = DATA(RMS,"BIOF","WHEA","Y");
           DATA(RMS,"PRCB","WHEA",SCEN) =  DATA(RMS,"PRCB","SWHE",SCEN);
           DATA(RMS,"PRCB","WHEA","TRD") = DATA(RMS,"PRCB","WHEA","Y");
           DATA(RMS,"PRCBY","WHEA",SCEN) =  DATA(RMS,"PRCBY","SWHE",SCEN);
           DATA(RMS,"PRCBY","WHEA","TRD") = DATA(RMS,"PRCBY","WHEA","Y");

    SCEN: "Y" and "BAS". Departures from CAPRI: none."""
    for r in S.RMS:
        for t in S.SCEN:
            D.set(r, "BIOF", "WHEA", t, D.get(r, "BIOF", "SWHE", t) + D.get(r, "BIOF", "DWHE", t))
        D.set(r, "BIOF", "WHEA", "TRD", D.get(r, "BIOF", "WHEA", "Y"))
        for c in ("PRCB", "PRCBY"):
            for t in S.SCEN:
                D.set(r, c, "WHEA", t, D.get(r, c, "SWHE", t))
            D.set(r, c, "WHEA", "TRD", D.get(r, c, "WHEA", "Y"))


def DATA_EXOG_tiny_feedstocks(D: Data, S: YearSets) -> None:
    r"""The biofuels made from a feedstock used at 0.5 thousand t or less are put on the exogenous production (EXOG),
    and those feedstock uses deleted.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 727-735):

        ** Store biofuel quantities produced by tiny feedstocks on exog

           DATA(RMS,"Exog",Seco_BioF,SCEN) = DATA(RMS,"Exog",Seco_BioF,SCEN)
                                           + SUM(Stock_to_fuel(XX,seco_bioF) $ (DATA(RMS,"PRCB",XX,SCEN) and (DATA(RMS,"BioF",XX,SCEN) le 0.5)),
                                                DATA(RMS,"BIOF",XX,SCEN) * DATA(RMS,"PRCB",XX,SCEN));

        ** delete the respective feedstock quantities

           DATA(RMS,"BioF",XX,SCEN) $ (DATA(RMS,"BioF",XX,SCEN) le 0.5) = 0;

    Stock_to_fuel(XX, ...): the pairs whose feedstock is a market product (WHEA, not SWHE: CAPRI's XX). Departures
    from CAPRI: none."""
    for r in S.RMS:
        for t in S.SCEN:
            for f in S.Seco_BioF:
                add = sum(D.get(r, "BIOF", xx, t) * D.get(r, "PRCB", xx, t) for (xx, ff) in S.Stock_to_fuel
                          if ff == f and xx in S.XX and D.get(r, "PRCB", xx, t) and D.get(r, "BIOF", xx, t) <= 0.5)
                D.set(r, "EXOG", f, t, D.get(r, "EXOG", f, t) + add)
    for r in S.RMS:
        for t in S.SCEN:
            for xx in S.XX:
                if D.get(r, "BIOF", xx, t) <= 0.5:
                    D.set(r, "BIOF", xx, t, 0)


def DATA_FSTG_PROD_biofuels(D: Data, S: YearSets) -> None:
    r"""The first-generation biofuels' production (FSTG) from the feedstocks used and their processing coefficients,
    plus the exogenous; the biofuels' production, PROD (with the second generation, SECG, and the non-agricultural
    sources, NAGR), and their gross production and market production.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 737-752):

        *** production of biofuels first generation

           DATA(RMS,"FSTG",SECO_BioF,SCEN)  = SUM(Stock_to_fuel(XX,seco_bioF) $ (DATA(RMS,"PRCB",XX,SCEN) and DATA(RMS,"BioF",XX,SCEN)),
                                                DATA(RMS,"BIOF",XX,SCEN) * DATA(RMS,"PRCB",XX,SCEN))
                                            + DATA(RMS,"Exog",Seco_BioF,SCEN);

        ** add second generation, and non agricultural sources

           DATA(RMS,"PROD",SECO_BioF,SCEN)  = DATA(RMS,"FSTG",SECO_BioF,SCEN) +DATA(RMS,"NAGR",SECO_BioF,SCEN) +DATA(RMS,"SECG",SECO_BioF,SCEN) ;

           DATA(RMS,"PROD",SECO_BioF,"TRD") = DATA(RMS,"PROD",SECO_BioF,"Y");
           DATA(RMS,"MAPR",SECO_BioF,"TRD") = DATA(RMS,"PROD",SECO_BioF,"Y");

           DATA(RMS,"GROF",SECO_BioF,SCEN)  = DATA(RMS,"PROD",SECO_BioF,SCEN) ;
           DATA(RMS,"GROF",SECO_BioF,"TRD") = DATA(RMS,"PROD",SECO_BioF,"TRD");


    Departures from CAPRI: none."""
    for r in S.RMS:
        for t in S.SCEN:
            for f in S.Seco_BioF:
                D.set(r, "FSTG", f, t, sum(D.get(r, "BIOF", xx, t) * D.get(r, "PRCB", xx, t)
                                           for (xx, ff) in S.Stock_to_fuel
                                           if ff == f and xx in S.XX and D.get(r, "PRCB", xx, t)
                                           and D.get(r, "BIOF", xx, t))
                      + D.get(r, "EXOG", f, t))
    for r in S.RMS:
        for f in S.Seco_BioF:
            for t in S.SCEN:
                D.set(r, "PROD", f, t, D.get(r, "FSTG", f, t) + D.get(r, "NAGR", f, t) + D.get(r, "SECG", f, t))
            D.set(r, "PROD", f, "TRD", D.get(r, "PROD", f, "Y"))
            D.set(r, "MAPR", f, "TRD", D.get(r, "PROD", f, "Y"))
            for t in S.SCEN:
                D.set(r, "GROF", f, t, D.get(r, "PROD", f, t))
            D.set(r, "GROF", f, "TRD", D.get(r, "PROD", f, "TRD"))


def DATA_DDGS(D: Data, S: YearSets) -> None:
    r"""The member states' DDGS: produced from the feedstocks used for biofuels at their by-product coefficients
    (PRCBY), all fed.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 753-763):

           DATA(MS,"PROD","DDGS",SCEN) = SUM(Stock_to_by(XX,"DDGS") $ (DATA(MS,"BioF",XX,SCEN) and DATA(MS,"PRCBY",XX,SCEN)),
                                                                       DATA(MS,"BioF",XX,SCEN) *DATA(MS,"PRCBY",XX,SCEN));
           DATA(MS,"FEDM","DDGS",SCEN) = DATA(MS,"PROD","DDGS",SCEN);
           DATA(MS,"GROF","DDGS",SCEN) = DATA(MS,"PROD","DDGS",SCEN);

           DATA(MS,"PROD","DDGS","TRD") = DATA(MS,"PROD","DDGS","Y");
           DATA(MS,"FEDM","DDGS","TRD") = DATA(MS,"PROD","DDGS","Y");
           DATA(MS,"GROF","DDGS","TRD") = DATA(MS,"PROD","DDGS","Y");

           DATA(MS,"FEED","DDGS",SCEN) = DATA(MS,"FEDM","DDGS",SCEN);
           DATA(MS,"FEED","DDGS","TRD") = DATA(MS,"FEDM","DDGS","Y");

    Departures from CAPRI: none."""
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "PROD", "DDGS", t, sum(D.get(ms, "BIOF", xx, t) * D.get(ms, "PRCBY", xx, t)
                                             for (xx, b) in S.Stock_to_by
                                             if b == "DDGS" and xx in S.XX and D.get(ms, "BIOF", xx, t)
                                             and D.get(ms, "PRCBY", xx, t)))
        for t in S.SCEN:
            D.set(ms, "FEDM", "DDGS", t, D.get(ms, "PROD", "DDGS", t))
        for t in S.SCEN:
            D.set(ms, "GROF", "DDGS", t, D.get(ms, "PROD", "DDGS", t))
        for c in ("PROD", "FEDM", "GROF"):
            D.set(ms, c, "DDGS", "TRD", D.get(ms, "PROD", "DDGS", "Y"))
        for t in S.SCEN:
            D.set(ms, "FEED", "DDGS", t, D.get(ms, "FEDM", "DDGS", t))
        D.set(ms, "FEED", "DDGS", "TRD", D.get(ms, "FEDM", "DDGS", "Y"))


def DATA_PRCY_CAK(D: Data, S: YearSets) -> None:
    r"""The cakes' processing coefficients (PRCY) where the oilseeds' crushing (PRCM) is known: the cake's production
    over its oilseeds' crushing.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 765-770):

        ** if some processing coefficients are missing

           Data(RMS,"PRCY",CAK,SCEN) $  SUM(SED_TO_CAK(SED,CAK),Data(RMS,"PRCM",SED,SCEN))
                                     = Data(RMS,"PROD",CAK,SCEN) / SUM(SED_TO_CAK(SED,CAK),Data(RMS,"PRCM",SED,SCEN));

           Data(RMS,"PRCY",CAK,"TRD") = Data(RMS,"PRCY",CAK,"Y");

    Departures from CAPRI: none."""
    for r in S.RMS:
        for t in S.SCEN:
            for cak in S.CAK:
                crush = sum(D.get(r, "PRCM", sed, t) for (sed, c) in S.SED_TO_CAK if c == cak)
                if crush:
                    D.set(r, "PRCY", cak, t, D.get(r, "PROD", cak, t) / crush)
        for cak in S.CAK:
            D.set(r, "PRCY", cak, "TRD", D.get(r, "PRCY", cak, "Y"))


def DATA_MAPR_MLK_small(D: Data, S: YearSets) -> None:
    r"""The member states' dairy products whose base-year market production is 1e-3 thousand t or less: their market
    production deleted at every position (where the base has none, too).

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 772-776):

        * --- correct FATS/PROT content of raw milk to match

            DATA(MS,"MAPR",MLK,"BAS") $ (DATA(MS,"MAPR",MLK,"BAS") LE 1.E-3) = 0;
            DATA(MS,"MAPR",MLK,"Y")   $ (DATA(MS,"MAPR",MLK,"BAS") LE 1.E-3) = 0;
            DATA(MS,"MAPR",MLK,"TRD") $ (DATA(MS,"MAPR",MLK,"BAS") LE 1.E-3) = 0;

    Departures from CAPRI: none."""
    for t in ("BAS", "Y", "TRD"):
        for ms in S.MS:
            for m in S.MLK:
                if D.get(ms, "MAPR", m, "BAS") <= 1e-3:
                    D.set(ms, "MAPR", m, t, 0)


def DATA_FATSPROT_MILK(D: Data, S: YearSets) -> None:
    r"""The raw milk's fat and protein contents that match the dairy products': the fat and protein in the products
    made (market production less the processing use, times the products' contents) over the raw milk processed (PRCM
    of MILK), for "Y" (and so "TRD") and "BAS". The total, kept on (FATS or PROT, LEVL), is deleted on "BAS".

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 778-790):

            DATA(MS,FATSPROT,"LEVL","Y") =
              sum(MLK $ (NOT SAMEAS(MLK,"MILK")), (data(ms,"MAPR",MLK,"Y")-DATA(MS,"PRCM",MLK,"Y"))*data(ms,FATSPROT,mlk,"Y"));

            DATA(MS,FATSPROT,"MILK","Y") $ DATA(MS,FATSPROT,"LEVL","Y")
              = DATA(MS,FATSPROT,"LEVL","Y")/data(MS,"PRCM","MILK","Y");
            DATA(MS,FATSPROT,"MILK","TRD") = DATA(MS,FATSPROT,"MILK","Y");

            DATA(MS,FATSPROT,"LEVL","BAS") =
              sum(MLK $ (NOT SAMEAS(MLK,"MILK")), (data(ms,"MAPR",MLK,"BAS")-DATA(MS,"PRCM",MLK,"BAS"))*data(ms,FATSPROT,mlk,"BAS"));

            DATA(MS,FATSPROT,"MILK","BAS") $ DATA(MS,FATSPROT,"LEVL","BAS")
              = DATA(MS,FATSPROT,"LEVL","BAS")/data(MS,"PRCM","MILK","BAS");
            DATA(MS,FATSPROT,"LEVL","BAS") = 0;

    A raw milk processed of zero where the products hold fat or protein is a division by zero, as in GAMS.
    Departures from CAPRI: none."""
    def total(ms, fp, t):
        return sum((D.get(ms, "MAPR", m, t) - D.get(ms, "PRCM", m, t)) * D.get(ms, fp, m, t)
                   for m in S.MLK if m != "MILK")
    for fp in S.FATSPROT:
        for ms in S.MS:
            D.set(ms, fp, "LEVL", "Y", total(ms, fp, "Y"))
    for fp in S.FATSPROT:
        for ms in S.MS:
            if D.get(ms, fp, "LEVL", "Y"):
                D.set(ms, fp, "MILK", "Y", D.get(ms, fp, "LEVL", "Y") / D.get(ms, "PRCM", "MILK", "Y"))
    for fp in S.FATSPROT:
        for ms in S.MS:
            D.set(ms, fp, "MILK", "TRD", D.get(ms, fp, "MILK", "Y"))
    for fp in S.FATSPROT:
        for ms in S.MS:
            D.set(ms, fp, "LEVL", "BAS", total(ms, fp, "BAS"))
    for fp in S.FATSPROT:
        for ms in S.MS:
            if D.get(ms, fp, "LEVL", "BAS"):
                D.set(ms, fp, "MILK", "BAS", D.get(ms, fp, "LEVL", "BAS") / D.get(ms, "PRCM", "MILK", "BAS"))
    for fp in S.FATSPROT:
        for ms in S.MS:
            D.set(ms, fp, "LEVL", "BAS", 0)

r"""TRD from the trends: the small areas and quantities, the tiny levels, FROM_CAPTRD_, the losses and the fodder
(capmod/load_base_data_and_trends.gms; moved from capri_mod/projection/equations/load_base_data_and_trends.py as they
were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.projection.equations.year_data.data_sets import Data, YearSets  # noqa: E402




def DATA2_GROF_FODDI(D2: Data, S: YearSets) -> None:
    r"""The fed fodder's gross production deleted where its fodder output has none.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 301):

            DATA2(RS,"GROF",FODDI,"Y") $ (NOT SUM(FEED_TO_O(FODDI,FODDO), DATA2(RS,"GROF",FODDO,"Y"))) = 0;

    Departures from CAPRI: none."""
    for fi in S.FODDI:
        outs = [fo for (f, fo) in S.FEED_TO_O if f == fi and fo in S.FODDO]
        for r in list(D2.at("GROF", fi, "Y")):
            if r in S.RS and not sum(D2.get(r, "GROF", fo, "Y") for fo in outs):
                D2.set(r, "GROF", fi, "Y", 0)


def DATA2_feeds_not_in_base(D2: Data, D: Data, S: YearSets) -> None:
    r"""A feed without base-year gross production deleted from the trends (no requirements or contents for it), with
    its residues' feed use; and a feed use without the feed's gross production.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 309-323):

        *       -- Not digestible entries for FEDM:
        *
        *          If there is no corresponding FEED use in BAS, there will be no requirements or contents
        *          => this bulk feed would not be usable
        *          => Delete all relevant entries of this FEED (observed for FENE in BA) and underlying RESIMP
            DATA2(RS,"GROF",FEED,"Y") $ (NOT DATA(RS,"GROF",FEED,"BAS")) = 0;
            DATA2(RS,"FEDM",FEED,"Y") $ (NOT DATA(RS,"GROF",FEED,"BAS")) = 0;
            DATA2(RS,"DOMM",FEED,"Y") $ (NOT DATA(RS,"GROF",FEED,"BAS")) = 0;
            DATA2(RS,"FEDM",RESIMP,"Y") $ (  (NOT SUM(FEED_TO_O(FEED_TRD,RESIMP), DATA(RS,"FEDM",FEED_TRD,"BAS")))
                                          $   DATA2(RS,"FEDM",RESIMP,"Y") ) = 0;
            DATA2(RS,"DOMM",RESIMP,"Y") $ (NOT DATA2(RS,"FEDM",RESIMP,"Y")) = 0;
            DATA2(RS,"MAPR",RESIMP,"Y") $ (NOT DATA2(RS,"FEDM",RESIMP,"Y")) = 0;

        *          And conversely:
            DATA2(RS,"FEDM",ROWS,"Y") $ (NOT SUM(FEED_TO_O(FEED,ROWS), DATA2(RS,"GROF",FEED,"Y"))) = 0;

    Departures from CAPRI: none."""
    for f in S.FEED:
        for col in ("GROF", "FEDM", "DOMM"):
            for r in list(D2.at(col, f, "Y")):
                if r in S.RS and not D.get(r, "GROF", f, "BAS"):
                    D2.set(r, col, f, "Y", 0)
    for res in S.RESIMP:
        trd = [f for (f, o) in S.FEED_TO_O if o == res and f in S.FEED_TRD]
        for r in list(D2.at("FEDM", res, "Y")):
            if r in S.RS and not sum(D.get(r, "FEDM", f, "BAS") for f in trd):
                D2.set(r, "FEDM", res, "Y", 0)
        for col in ("DOMM", "MAPR"):
            for r in list(D2.at(col, res, "Y")):
                if r in S.RS and not D2.get(r, "FEDM", res, "Y"):
                    D2.set(r, col, res, "Y", 0)
    feeds_of = {}
    for (f, o) in S.FEED_TO_O:
        if f in S.FEED:
            feeds_of.setdefault(o, []).append(f)
    for (c, w) in D2.keys("Y"):
        if c != "FEDM" or w not in S.ROWS:
            continue
        for r in list(D2.at("FEDM", w, "Y")):
            if r in S.RS and not sum(D2.get(r, "GROF", f, "Y") for f in feeds_of.get(w, ())):
                D2.set(r, "FEDM", w, "Y", 0)


def DATA_TRD_from_trends(D: Data, D2: Data, S: YearSets) -> None:
    r"""The trends on "TRD", over the columns and rows CAPRI reads.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 325-326):

            option data2:2:3:1;
            DATA(RS,ColsRead,RowsRead,"TRD") = DATA2(RS,ColsRead,RowsRead,"Y");

    Departures from CAPRI: none."""
    for (c, w) in D.keys("TRD"):
        if c in S.ColsRead and w in S.RowsRead:
            for r in list(D.at(c, w, "TRD")):
                if r in S.RS:
                    D.set(r, c, w, "TRD", 0)
    for (c, w) in D2.keys("Y"):
        if c in S.ColsRead and w in S.RowsRead:
            for r, v in D2.at(c, w, "Y").items():
                if r in S.RS:
                    D.set(r, c, w, "TRD", v)


def DATA_TRD_small_areas(D: Data, S: YearSets) -> None:
    r"""Very small areas deleted: Greece's (EL250000) soya below 20 ha, other land below 1 m2.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 329-335):

        * very small areas provoke infeasiblities in supply lp model

            DATA(RS,"SOYA","LEVL","TRD")$(SAMEAS(RS,"EL250000") and DATA(RS,"SOYA","LEVL","TRD") lt 0.02) = 0;

        * Also often infeasiblities in supply models if some OLND area (containing RESLND) is smaller than 1 m2:

            DATA(RS,"OLND","LEVL","TRD") $ (DATA(RS,"OLND","LEVL","TRD") lt 1e-7) = 0;

    Departures from CAPRI: none."""
    if "EL250000" in S.RS and D.get("EL250000", "SOYA", "LEVL", "TRD") < 0.02:
        D.set("EL250000", "SOYA", "LEVL", "TRD", 0)
    for r, v in list(D.at("OLND", "LEVL", "TRD").items()):
        if r in S.RS and v < 1e-7:
            D.set(r, "OLND", "LEVL", "TRD", 0)


def DATA_TRD_GROF_OCRO(D: Data, S: YearSets) -> None:
    r"""The other crops' gross production from the activities' levels and yields.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 337-341):

        *TJ --- It seems as if NECR.OCRO yields and NECR.LEVL are invented in CAPTRD. If there is no OCRO.LEVL, then GROF is missing
        *       This is inconsistent and needs to be fixed "somewhere", probably in CAPTRD.

            DATA(RS,"GROF","OCRO","TRD")
              = sum(MPACT $ pact_to_o(MPACT,"OCRO"), DATA(RS,MPACT,"OCRO","TRD")*DATA(RS,MPACT,"LEVL","TRD")) / 1000;

    Departures from CAPRI: none (CAPRI's statement has no condition: every region of RS is set, to zero where no
    activity yields OCRO)."""
    acts = [a for (a, o) in S.PACT_TO_O if o == "OCRO" and a in S.MPACT]
    for r in S.RS:
        D.set(r, "GROF", "OCRO", "TRD",
              sum(D.get(r, a, "OCRO", "TRD") * D.get(r, a, "LEVL", "TRD") for a in acts) / 1000.)


def DATA_TRD_FALL_invented(D: Data, S: YearSets) -> None:
    r"""A region without any set-aside or fallow (setfPact) gets 50 ha of fallow taken from its other fodder (keeping
    at least 20 ha of it), the fallow's labour from the smallest positive of the arable activities', and the member
    states' fallow, other fodder and its yield re-aggregated.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 343-383):

        * --- If all setfPact are zero in a region, eq ecoSetAside_ is impossible or difficult (only via PULS or CATC) to comply with
        *     => invent FALL = 50ha
        loop(ru $ [not Sum(setfPact,DATA(RU,setfPact,"LEVL","TRD"))],

        *     -- store the old OFAR level on "S99" as we will try to reallocate the 50ha from OFAR to FALL:
            DATA(RU,"OFAR","LEVL","S99") = DATA(RU,"OFAR","LEVL","TRD");
        *    DATA(RU,"OFAR","LEVL","TRD")$ (not Sum(setfPact,DATA(RU,setfPact,"LEVL","TRD")))
            DATA(RU,"OFAR","LEVL","TRD")
        *        ... but preserving at least 20ha of OFAR:
               = max(.02, DATA(RU,"OFAR","LEVL","TRD")-.05);

        *     -- Apart from the areas only labour requirements are usually coming from the trends for FALL.
        *        Take them from the minimum over all (positive) arbact
            DATA(RU,"FALL",ILAB,"TRD")
               = smin(arbact $ (DATA(RU,arbact,ILAB,"TRD") gt eps), DATA(RU,arbact,ILAB,"TRD"));

        *     -- Here the "invented" area reallocation:
            DATA(RU,"FALL","LEVL","TRD") $ DATA(RU,"OFAR","LEVL","S99")
               = min(.05,DATA(RU,"OFAR","LEVL","S99")-DATA(RU,"OFAR","LEVL","TRD"));

        *     -- Adjust gross production of OFAR to match the new levels
            DATA(RU,"GROF","OFAR","TRD") = DATA(RU,"OFAR","LEVL","TRD")*DATA(RU,"OFAR","OFAR","TRD")/1000;
        );

        *     -- Reaggregate areas, gross production and yields if regional areas have been changed
        loop(ms $ sum(map_rr(ms,ru), DATA(RU,"OFAR","LEVL","S99")),
        *    DATA(MS,"FALL","LEVL","TRD") $ Sum(MAP_RR(MS,RU) $ (DATA(RU,"FALL","LEVL","TRD") le 0.05),1)
            DATA(MS,"FALL","LEVL","TRD")
               = SUM(MAP_RR(MS,RU),DATA(RU,"FALL","LEVL","TRD"));

        *    DATA(MS,"OFAR","LEVL","TRD") $ Sum(MAP_RR(MS,RU) $ (DATA(RU,"FALL","LEVL","TRD") le 0.05),1)
            DATA(MS,"OFAR","LEVL","TRD")
               = SUM(MAP_RR(MS,RU),DATA(RU,"OFAR","LEVL","TRD"));

            DATA(MS,"GROF","OFAR","TRD")
               = SUM(MAP_RR(MS,RU),DATA(RU,"GROF","OFAR","TRD"));

            DATA(MS,"OFAR","OFAR","TRD")
               = DATA(MS,"GROF","OFAR","TRD")*1000 / DATA(MS,"OFAR","LEVL","TRD");
        );
            DATA(RU,"OFAR","LEVL","S99") = 0;

    GAMS's smin over an empty set is +INF: a region without any arable activity's labour would get an infinite
    fallow labour, as in CAPRI. Departures from CAPRI: none."""
    s99 = {}
    for r in sorted(S.RU):
        if sum(D.get(r, a, "LEVL", "TRD") for a in S.setfPact):
            continue
        s99[r] = D.get(r, "OFAR", "LEVL", "TRD")
        D.set(r, "OFAR", "LEVL", "TRD", max(.02, D.get(r, "OFAR", "LEVL", "TRD") - .05))
        for il in S.ILAB:
            vals = [D.get(r, a, il, "TRD") for a in S.arbact if D.get(r, a, il, "TRD") > 0]
            D.set(r, "FALL", il, "TRD", min(vals) if vals else float("inf"))
        if s99[r]:
            D.set(r, "FALL", "LEVL", "TRD", min(.05, s99[r] - D.get(r, "OFAR", "LEVL", "TRD")))
        D.set(r, "GROF", "OFAR", "TRD", D.get(r, "OFAR", "LEVL", "TRD") * D.get(r, "OFAR", "OFAR", "TRD") / 1000.)
    for ms in sorted(S.MS):
        rus = [ru for (m, ru) in S.MAP_RR if m == ms and ru in S.RU]
        if not sum(s99.get(ru, 0.0) for ru in rus):
            continue
        for col, row in (("FALL", "LEVL"), ("OFAR", "LEVL")):
            D.set(ms, col, row, "TRD", sum(D.get(ru, col, row, "TRD") for ru in rus))
        D.set(ms, "GROF", "OFAR", "TRD", sum(D.get(ru, "GROF", "OFAR", "TRD") for ru in rus))
        D.set(ms, "OFAR", "OFAR", "TRD", D.get(ms, "GROF", "OFAR", "TRD") * 1000. / D.get(ms, "OFAR", "LEVL", "TRD"))


def DATA_TRD_small_quantities(D: Data, S: YearSets) -> None:
    r"""Tiny gross production (up to 1e-10) and feed coefficients (up to 1e-8) deleted, and the fodder outputs'
    producer prices.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 398-400):

            DATA(RS,"GROF",RowsRead,"TRD") $ (DATA(RS,"GROF",RowsRead,"TRD") LE 1.E-10) = 0;
            DATA(RS,MAACT,FEED,"TRD")      $ (DATA(RS,MAACT,FEED,"TRD")      LE 1.E-8)  = 0;
            DATA(RS,"UVAP",FODDO,"TRD") = 0;

    Departures from CAPRI: none. (l. 396-397, the biofuels' feedstocks, are not ported, module docstring.) A
    negative value is deleted too, as GAMS's "LE"."""
    for (c, w) in D.keys("TRD"):
        if c == "GROF" and w in S.RowsRead:
            lim = 1e-10
        elif c in S.MAACT and w in S.FEED:
            lim = 1e-8
        else:
            continue
        for r, v in list(D.at(c, w, "TRD").items()):
            if r in S.RS and v <= lim:
                D.set(r, c, w, "TRD", 0)
    for fo in S.FODDO:
        for r in list(D.at("UVAP", fo, "TRD")):
            if r in S.RS:
                D.set(r, "UVAP", fo, "TRD", 0)


def delete_tiny_activity_level(D: Data, S: YearSets, pos: str, tol: float) -> dict:
    r"""Activity levels below tol (less than 1 ha or head) deleted with their coefficients; the region's gross
    production of their inputs and outputs re-computed; and the member states' levels, gross production and
    coefficients re-aggregated where a region's changed. Returns CAPRI's p_problem3D (the cells flagged).

    CAPRI's GAMS (util/delete_tiny_activity_level.gms l. 7-28):

            p_problem3D(ru,mpact,"levl") $ [(DATA(ru,mpact,"levl","%POS%") gt 0) and DATA(ru,mpact,"levl","%POS%") lt %tol%] = 1;
            p_problem3D(ru,"GROF",io) $ sum(mpact $ (pact_to_io(mpact,io) and p_problem3D(ru,mpact,"levl")), 1) = 1;

            DATA(ru,mpact,"levl","%POS%") $ p_problem3D(ru,mpact,"levl") = 0;
            DATA(ru,mpact,io,"%POS%") $ p_problem3D(ru,mpact,"levl") = 0;

        *   The following corrections following the deletion of tiny levels seem necessary, but provoke problems
        *   It seems like IO coefficients are missing in some cases, so that re-computing GROF becomes impossible here.
            DATA(ru,"grof",io,"%POS%") $ p_problem3D(ru,"GROF",io)
              = sum(mpact $ pact_to_io(mpact,io), data(ru,mpact,"levl","%POS%") * data(ru,mpact,io,"%POS%")) / 1000;

            DATA(ms,mpact,"levl","%POS%") $ sum(map_rr(ms,ru), p_problem3D(ru,mpact,"levl"))
              = sum(map_rr(ms,ru), DATA(ru,mpact,"levl","%POS%"));

            DATA(ms,"GROF",IO,"%POS%") $ sum(map_rr(ms,ru), p_problem3D(ru,"GROF",io))
              = sum(map_rr(ms,ru), DATA(ru,"GROF",io,"%POS%"));

            DATA(ms,mpact,IO,"%POS%") $ [sum(map_rr(ms,ru), p_problem3D(ru,"GROF",io))
                                    and data(ms,mpact,"levl","%POS%")
                                    and pact_to_io(mpact,io)]
              = sum(map_rr(ms,ru), data(ru,mpact,"levl","%POS%") * data(ru,mpact,io,"%POS%"))
              / sum(map_rr(ms,ru), data(ru,mpact,"levl","%POS%"));

    Departures from CAPRI: none."""
    lev = {(r, a): v for a in S.MPACT for r, v in D.at(a, "LEVL", pos).items() if r in S.RU}
    flag_levl = {(r, a) for (r, a), v in lev.items() if 0 < v < tol}
    io_of = {}
    for (a, io) in S.PACT_TO_IO:
        if a in S.MPACT and io in S.IO:
            io_of.setdefault(a, []).append(io)
    flag_grof = {(r, io) for (r, a) in flag_levl for io in io_of.get(a, ())}
    for (r, a) in flag_levl:
        D.set(r, a, "LEVL", pos, 0)
        for io in S.IO:
            if D.get(r, a, io, pos):
                D.set(r, a, io, pos, 0)
    acts_of = {}
    for (a, io) in S.PACT_TO_IO:
        if a in S.MPACT:
            acts_of.setdefault(io, []).append(a)
    for (r, io) in flag_grof:
        D.set(r, "GROF", io, pos,
              sum(D.get(r, a, "LEVL", pos) * D.get(r, a, io, pos) for a in acts_of.get(io, ())) / 1000.)
    for ms in S.MS:
        rus = [ru for (m, ru) in S.MAP_RR if m == ms and ru in S.RU]
        for a in S.MPACT:
            if any((ru, a) in flag_levl for ru in rus):
                D.set(ms, a, "LEVL", pos, sum(D.get(ru, a, "LEVL", pos) for ru in rus))
        for io in S.IO:
            if not any((ru, io) in flag_grof for ru in rus):
                continue
            D.set(ms, "GROF", io, pos, sum(D.get(ru, "GROF", io, pos) for ru in rus))
            for a in acts_of.get(io, ()):
                lv = D.get(ms, a, "LEVL", pos)
                if lv:
                    D.set(ms, a, io, pos, sum(D.get(ru, a, "LEVL", pos) * D.get(ru, a, io, pos) for ru in rus)
                          / sum(D.get(ru, a, "LEVL", pos) for ru in rus))
    return {"levl": flag_levl, "GROF": flag_grof}


def check_uaar_trend(D: Data, S: YearSets) -> None:
    r"""A region without the trends' agricultural area stops the run.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 513-516):

            set empty; empty(rs) $ (NOT DATA(RS,"UAAR","LEVL","TRD")) = YES;
            if ( card(empty) ne 0, display empty;
              abort "Missing trend projection for agricultural area for some regions, %system.fn% %system.incline%",
                "in %results_in%\baseline\%trendFileName%");

    Departures from CAPRI: none."""
    empty = sorted(r for r in S.RS if not D.get(r, "UAAR", "LEVL", "TRD"))
    if empty:
        raise ValueError(f"Missing trend projection for agricultural area for some regions: {empty}")


def DATA_TRD_young_animals_fixed(D: Data, S: YearSets) -> None:
    r"""The fixed young-animal inputs and outputs per head (1000 per 1000 heads), and no production or yield of the
    activities on "TRD".

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 528-532):

            DATA(RS,FIX_YAI,IYANI,"TRD") $ (PACT_TO_I(FIX_YAI,IYANI) and DATA(RS,FIX_YAI,"LEVL","TRD")) = 1000;
            DATA(RS,FIX_YAO,OYANI,"TRD") $ (PACT_TO_O(FIX_YAO,OYANI) and DATA(RS,FIX_YAO,"LEVL","TRD")) = 1000;

            DATA(RS,PACT,"PROD","TRD") = 0;
            DATA(RS,PACT,"YILD","TRD") = 0;

    Departures from CAPRI: none."""
    for acts, rows, pairs in ((S.FIX_YAI, S.IYANI, S.PACT_TO_I), (S.FIX_YAO, S.OYANI, S.PACT_TO_O)):
        for (a, y) in pairs:
            if a in acts and y in rows:
                for r in S.RS:
                    if D.get(r, a, "LEVL", "TRD"):
                        D.set(r, a, y, "TRD", 1000.)
    for a in S.PACT:
        for w in ("PROD", "YILD"):
            for r in list(D.at(a, w, "TRD")):
                if r in S.RS:
                    D.set(r, a, w, "TRD", 0)


def FROM_CAPTRD_(D2: Data, S: YearSets) -> set:
    r"""The positions taken from the trends: those CAPTRD wrote for any member state or aggregate, the levels of the
    set-aside and of every activity, the market and feed balance positions, the emissions; not the animals' MINS and
    MAXS nor rape's NONS.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 537-563):

            FROM_CAPTRD(ColsRead,RowsRead) $ SUM(MSALL $ DATA2(MSALL,ColsRead,RowsRead,"Y"),1) = YES;
            option kill=DATA2;
        $include 'util\kill_model1.gms';
        *
        *   --- Obligatory set-aside level is probably zero for the projection period, but needs to be taken over!
        *       otherwise, base year hectarage will end up in the calibration point, and the model will become infeasible
        *
            FROM_CAPTRD(RSET,"LEVL")        = YES;
            FROM_CAPTRD("LOSF",ROWS)      = YES;
            FROM_CAPTRD("SEDF",ROWS)      = YES;
            FROM_CAPTRD("SEDM",ROWS)      = YES;
            FROM_CAPTRD("STCM",ROWS)        = YES;
            FROM_CAPTRD("SADM",ROWS)        = YES;
            FROM_CAPTRD("FEDM",Rows)        = YES;
            FROM_CAPTRD(COLS,GASAGG)        = YES;
            FROM_CAPTRD(COLS,GAS_EMIS)      = YES;
            FROM_CAPTRD(COLS,GHGSDEL_ROWS)  = YES;
            FROM_CAPTRD(COLS,"GWPA")        = YES;
            FROM_CAPTRD(MAACT,"MINS")       = NO;
            FROM_CAPTRD(MAACT,"MAXS")       = NO;

        * ag: Problem in farm types (should be loaded from res bas and never from trends)
            FROM_CAPTRD("RAPE","NONS")       = NO;
        * ag: Use "lev" from trends (also zero values that no BAS values are used)
            FROM_CAPTRD(mpact,"levl")        = YES;
        * ag: for AL grof in ft mode was missing
            FROM_CAPTRD("grof",feed)        = YES;

    Returns the (column, row) pairs within ColsRead x RowsRead, the domain the "Y" rule reads (year_data_Y); the
    additions on COLS and ROWS outside it are not kept. Departures from CAPRI: none."""
    fc = {(c, w) for (c, w) in D2.keys("Y")
          if c in S.ColsRead and w in S.RowsRead and any(r in S.MSALL for r in D2.at(c, w, "Y"))}
    for c in S.RSET:
        fc.add((c, "LEVL"))
    for c in ("LOSF", "SEDF", "SEDM", "STCM", "SADM", "FEDM"):
        fc.update((c, w) for w in S.RowsRead)
    for w in set(S.GASAGG) | set(S.GAS_EMIS) | set(S.GHGSDEL_ROWS) | {"GWPA"}:
        fc.update((c, w) for c in S.ColsRead)
    fc -= {(a, w) for a in S.MAACT for w in ("MINS", "MAXS")}
    fc.discard(("RAPE", "NONS"))
    fc.update((a, "LEVL") for a in S.MPACT)
    fc.update(("GROF", f) for f in S.FEED)
    return {(c, w) for (c, w) in fc if c in S.ColsRead and w in S.RowsRead}


def DATA_TRD_LOSF_STRA(D: Data, S: YearSets) -> None:
    r"""The straw's losses at the base year's share of its gross production.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 565-566):

            DATA(RS,"LOSF","STRA","TRD") $ DATA(RS,"GROF","STRA","BAS")
                = DATA(RS,"GROF","STRA","TRD") * DATA(RS,"LOSF","STRA","BAS")/DATA(RS,"GROF","STRA","BAS");

    Departures from CAPRI: none."""
    for r, g0 in D.at("GROF", "STRA", "BAS").items():
        if r in S.RS:
            D.set(r, "LOSF", "STRA", "TRD", D.get(r, "GROF", "STRA", "TRD") * D.get(r, "LOSF", "STRA", "BAS") / g0)


def DATA_TRD_LOSF_ratio(D: Data, S: YearSets) -> None:
    r"""The regions' losses at their member state's loss share of gross production.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 587-590):

        *      => Need for a fix:
            DATA(RU,"LOSF",losfItem,"TRD") = DATA(RU,"GROF",losfItem,"TRD")
                                           * SUM(R_RAGG(RU,MS) $ DATA(MS,"GROF",losfItem,"TRD"),
                                             DATA(MS,"LOSF",losfItem,"TRD")/DATA(MS,"GROF",losfItem,"TRD"));

    Departures from CAPRI: none (every region of RU is set: to zero where its member state has no gross
    production of the item)."""
    ms_of = {}
    for (ru, ms) in S.R_RAGG:
        if ms in S.MS:                          # the sum's index is MS
            ms_of.setdefault(ru, []).append(ms)
    for it in S.losfItem:
        for ru in S.RU:
            share = sum(D.get(ms, "LOSF", it, "TRD") / D.get(ms, "GROF", it, "TRD")
                        for ms in ms_of.get(ru, ()) if D.get(ms, "GROF", it, "TRD"))
            D.set(ru, "LOSF", it, "TRD", D.get(ru, "GROF", it, "TRD") * share)


def DATA_TRD_GROF_FODDI(D: Data, S: YearSets) -> None:
    r"""The fed fodder's gross production: its fodder outputs' gross production less losses, and less the
    exogenous industrial demand of fodder maize (energy maize), at least 0.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 592-595):

            DATA(RU,"GROF",FODDI,"TRD") = MAX(0,SUM(FEED_TO_O(FODDI,losfItem), DATA(RU,"GROF",losfItem,"TRD")
                                                                              -DATA(RU,"LOSF",losfItem,"TRD")
        *                                                                     consider the case of energy maize (in Germany)
                                                                              -DATA(RU,"INDM",losfItem,"TRD") $ SAMEAS(losfItem,"MAIF")));

    Departures from CAPRI: none."""
    for fi in S.FODDI:
        outs = [o for (f, o) in S.FEED_TO_O if f == fi and o in S.losfItem]
        for ru in S.RU:
            D.set(ru, "GROF", fi, "TRD",
                  max(0.0, sum(D.get(ru, "GROF", o, "TRD") - D.get(ru, "LOSF", o, "TRD")
                               - (D.get(ru, "INDM", o, "TRD") if o == "MAIF" else 0.0) for o in outs)))

r"""CAPRI's data of a simulation year (capmod/load_base_data_and_trends.gms l. 44-863; CAPRI star 3.0, baseline mode):
the trends, CAPTRD's DATA2 at "Y", corrected and loaded on "TRD"; "Y" = "TRD" where CAPTRD projects the item
(FROM_CAPTRD), "BAS" elsewhere; then the positions CAPRI derives, fills or deletes for the simulation.

The base year's data "BAS" are CAPREG's results with CAPRI's corrections (l. 44-199, base_year_data); the trends are
CAPTRD's (l. 290-863, year_data). One function per CAPRI statement block, in CAPRI's order.

DATA is CAPRI's DATA(region, column, row, position), Data below. GAMS's zero is an absent cell, and setting a cell to
zero deletes it. CAPRI's sets are those of sim_ini_21730 (capri_data/codes/capri, YearSets).

Since 25 November 2026 also l. 711-795: Norway's sheep milk quota, the biofuels and DDGS, the cakes' processing
coefficients, the raw milk's fat and protein, and biofuel/resids.gms (the crop residues and the second-generation
biofuels' sources; its literal parameters in capri_data/2017/supply/biofuel_resids_params.csv).

Not ported, as they set no item of the supply models' activities, feed or fodder:
- l. 298-299 (oats' INTP and INTS) and l. 303-307 (the fuels' rows, calyea);
- l. 396-397 and 402-415 (the biofuel feedstocks);
- l. 520-525 (the inland waters' INLW).

Not ported in the base year's loading: l. 34-43 (the GDX loading itself and its meta information) and l. 65-123 (the
definition of ColsRead and RowsRead: their values are taken from sim_ini_21730's sets, YearSets).

Not ported because their branch is off in CAPRI's 2030 baseline:
- l. 236-261 (farm types), l. 385-393 (%SIM% 06), l. 601-630 (a short-run scenario);
- l. 644-657 (ex post, and BAS = SIM).

The checks that only display (l. 417-434, 568-585) are not ported. The aborts are (check_uaar_trend and
assert_year_data).

Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set


class Data:
    """CAPRI's DATA(region, column, row, position) as {(position, column, row): {region: value}}. A zero value is an
    absent cell, as in GAMS."""

    def __init__(self):
        self.c = {}

    def get(self, r, c, w, t):
        d = self.c.get((t, c, w))
        return d.get(r, 0.0) if d else 0.0

    def set(self, r, c, w, t, v):
        if v == 0 or v is None:
            d = self.c.get((t, c, w))
            if d is not None:
                d.pop(r, None)
                if not d:
                    del self.c[(t, c, w)]
        else:
            self.c.setdefault((t, c, w), {})[r] = float(v)

    def at(self, c, w, t):
        """{region: value} of one column and row at one position."""
        return self.c.get((t, c, w), {})

    def keys(self, t):
        """The (column, row) pairs with a cell at position t."""
        return [(c, w) for (tt, c, w) in self.c if tt == t]


class OSet(tuple):
    """A CAPRI set: its elements in CAPRI's order, so that the loops and sums over it run in GAMS's order (a sum's last
    digits depend on it), with a set's membership test, intersection, union and difference."""

    def __new__(cls, items=()):
        t = super().__new__(cls, dict.fromkeys(items))
        t._m = frozenset(t)
        return t

    def __contains__(self, x):
        return x in self._m

    def __and__(self, other):
        return OSet(x for x in self if x in other)

    def __or__(self, other):
        return OSet(list(self) + [x for x in other if x not in self._m])

    def __sub__(self, other):
        return OSet(x for x in self if x not in other)


@dataclass
class YearSets:
    """CAPRI's sets the statements use (sim_ini_21730's sets, capri_data/codes/capri), in CAPRI's order (OSet)."""
    RS: OSet
    RU: OSet
    MS: OSet
    MSALL: OSet
    MAP_RR: OSet          # {(member state, region)}
    R_RAGG: OSet          # {(region, member state)}
    PACT: OSet
    MPACT: OSet
    MAACT: OSet
    AACT: OSet
    CACT: OSet
    DACT: OSet
    SplitActs: OSet
    DACT_TO_PACT: OSet    # {(DACT, split activity)}
    FEED: OSet
    FEED_TRD: OSet
    FODDI: OSet
    FODDO: OSet
    FODDIO: OSet
    FEED_TO_O: OSet       # {(feed, output)}
    RESIMP: OSet
    PACT_TO_IO: OSet      # {(activity, row)}
    PACT_TO_I: OSet
    PACT_TO_O: OSet
    FIX_YAI: OSet
    FIX_YAO: OSet
    IYANI: OSet
    OYANI: OSet
    OIYANI: OSet
    IO: OSet
    IOP: OSet
    O: OSet
    FOUT: OSet
    ROWS: OSet
    COLS: OSet
    ColsRead: OSet
    RowsRead: OSet
    losfItem: OSet
    REQSR_M: OSet
    REQSC: OSet
    OSECO: OSet
    RSET: OSet
    GASAGG: OSet
    GAS_EMIS: OSet
    GHGSDEL_ROWS: OSet
    MAPP: OSet
    SCEN: OSet
    ILAB: OSet
    setfPact: OSet
    arbact: OSet
    FNUT: OSet
    RMS: OSet
    XX: OSet
    Seco_BioF: OSet
    XXBIOF: OSet
    Stock_to_fuel: OSet        # {(feedstock, biofuel)}
    Stock_to_by: OSet          # {(feedstock, by-product)}
    CAK: OSet
    SED: OSet
    SED_TO_CAK: OSet           # {(oilseed, cake)}
    MLK: OSet
    FATSPROT: OSet
    PACT_TO_Y: OSet            # {(activity, its main output)}

    @classmethod
    def from_codes(cls):
        def s(n):
            return OSet(capri_set(n))

        def p(n):
            return OSet(tuple(x[:2]) for x in capri_pairs(n))
        names = {f: f for f in cls.__dataclass_fields__}
        names.update(arbact="arbAct", Seco_BioF="SECO_BIOF", XXBIOF="XXBiof", Stock_to_fuel="STOCK_TO_FUEL",
                     Stock_to_by="STOCK_TO_BY")
        pairs = {"MAP_RR", "R_RAGG", "DACT_TO_PACT", "FEED_TO_O", "PACT_TO_IO", "PACT_TO_I", "PACT_TO_O",
                 "Stock_to_fuel", "Stock_to_by", "SED_TO_CAK", "PACT_TO_Y"}
        return cls(**{f: (p(n) if f in pairs else s(n)) for f, n in names.items()})


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


def base_year_data(D: Data, D2b: Data, S: YearSets) -> None:
    """CAPRI's loading of the base year (load_base_data_and_trends.gms l. 44-199, the statements ported) from CAPREG's
    results D2b (CAPREG's DATA2 at "Y"): the base year on "BAS" of D."""
    DATA2_base_deletions(D2b, S)
    DATA2_base_labour_and_nutrients(D2b, S)
    DATA_BAS_from_capreg(D, D2b, S)
    check_uaar_base(D, S)
    DATA_CERE_HSTY(D, D2b, S)


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


@dataclass
class ResidsParams:
    """CAPRI's literal parameters of biofuel/resids.gms (capri_data/2017/supply/biofuel_resids_params.csv,
    tools/build/build_resids_params.py): p_residYield(PACT), the crop residues' dry weight per unit of the main yield;
    p_newEnergyCropYield, the new energy crops' biomass yield per member state (REST for the others); p_secgConv, the
    biomass needed per unit of second-generation biofuel."""
    p_residYield: dict
    p_newEnergyCropYield: dict
    p_secgConv: dict

    @classmethod
    def from_csv(cls, path=None):
        import csv
        from pathlib import Path
        path = path or Path(__file__).resolve().parents[3] / "capri_data" / "2017" / "supply" / \
            "biofuel_resids_params.csv"
        out = {"p_residYield": {}, "p_newEnergyCropYield": {}, "p_secgConv": {}}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                out[row["symbol"]][row["item"]] = float(row["value"])
        return cls(**out)


def DATA_ARES(D: Data, S: YearSets, P: ResidsParams) -> None:
    r"""The member states' crop residues (ARES): per hectare, the main yield times the residue's yield factor (zero
    for the activities without one), and their gross production over the main activities.

    CAPRI's GAMS (biofuel/resids.gms l. 45-46; the factors p_residYield, l. 24-35, in ResidsParams):

           Data(MS,PACT,"ARES",SCEN) = SUM(PACT_TO_Y(PACT,O), DATA(MS,PACT,O,SCEN)) *  p_residYield(PACT);
           Data(MS,"GROF","ARES",SCEN) = SUM(MPACT, DATA(MS,MPACT,"ARES",SCEN)*DATA(MS,MPACT,"LEVL",SCEN))/1000;

    The water module's statement (l. 39-41) is off in CAPRI's baseline. Departures from CAPRI: none."""
    main = {}
    for (a, o) in S.PACT_TO_Y:
        main.setdefault(a, []).append(o)
    for ms in S.MS:
        for a in S.PACT:
            for t in S.SCEN:
                D.set(ms, a, "ARES", t, sum(D.get(ms, a, o, t) for o in main.get(a, ()))
                      * P.p_residYield.get(a, 0.0))
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "GROF", "ARES", t, sum(D.get(ms, a, "ARES", t) * D.get(ms, a, "LEVL", t) for a in S.MPACT)
                  / 1000)


def _necr_yield(P: ResidsParams, ms):
    """p_newEnergyCropYield(MS) + p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS))."""
    y = P.p_newEnergyCropYield.get(ms, 0.0)
    return y + (P.p_newEnergyCropYield["REST"] if not y else 0.0)


def DATA_NECR_LEVL_1_2(D: Data, S: YearSets, P: ResidsParams, same_year: bool = False) -> None:
    r"""The new energy crops' area for second-generation biofuels (LEVL_1: half the biomass the second generation
    needs, at the crops' yield, at most 90% of their area) and the rest of their area (LEVL_2); on "CAL" those of "Y",
    or of "BAS" when the simulation year is the base year (same_year).

    CAPRI's GAMS (biofuel/resids.gms l. 69-85; p_newEnergyCropYield l. 49-57 and p_secgConv l. 64-67 in ResidsParams):

        ** We assume that Second generation biofuels are propduced 50/50 by agricultural residuals and new energy crops
        * That would require new energy crop area (Stored on levl_1)

           DATA(MS,"NECR","LEVL_1",SCEN) = MIN(DATA(MS,"NECR","LEVL",SCEN) *0.9, 0.5*SUM(XXBIOF,Data(MS,"SECG",XXBIOF,SCEN) /p_secgConv(XXBIOF))
                                            / (p_newEnergyCropYield(MS) + p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS))));


        * the NECR area that is used by other than fuel bioenergy is stored on LEVL_2

          DATA(MS,"NECR","LEVL_2",SCEN) = DATA(MS,"NECR","LEVL",SCEN)-DATA(MS,"NECR","LEVL_1",SCEN);


          DATA(MS,"NECR","LEVL_1","CAL") = DATA(MS,"NECR","LEVL_1","Y")   $ (NOT (CALYEA("BAS") = CALYEA("Y")))
                                         + DATA(MS,"NECR","LEVL_1","BAS") $ (CALYEA("Y") = CALYEA("BAS"));

          DATA(MS,"NECR","LEVL_2","CAL") = DATA(MS,"NECR","LEVL_2","Y")   $ (NOT (CALYEA("BAS") = CALYEA("Y")))
                                         + DATA(MS,"NECR","LEVL_2","BAS") $ (CALYEA("Y") = CALYEA("BAS"));

    Departures from CAPRI: none."""
    for ms in S.MS:
        for t in S.SCEN:
            need = sum(D.get(ms, "SECG", f, t) / P.p_secgConv[f] for f in S.XXBIOF)
            D.set(ms, "NECR", "LEVL_1", t, min(D.get(ms, "NECR", "LEVL", t) * 0.9, 0.5 * need / _necr_yield(P, ms)))
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "NECR", "LEVL_2", t, D.get(ms, "NECR", "LEVL", t) - D.get(ms, "NECR", "LEVL_1", t))
    for w in ("LEVL_1", "LEVL_2"):
        for ms in S.MS:
            D.set(ms, "NECR", w, "CAL", D.get(ms, "NECR", w, "BAS" if same_year else "Y"))


def DATA_SECG_ARES_bio(D: Data, S: YearSets, P: ResidsParams) -> None:
    r"""The agricultural residues for second-generation biofuels (SECG of ARES): the biomass the second generation
    needs less the new energy crops' (LEVL_1 at their yield); each biofuel's part from the new energy crops (bioNECR)
    and from the residues (bioARES).

    CAPRI's GAMS (biofuel/resids.gms l. 87-99):

        ** and Agricultural residuals

           Data(MS,"SECG","ARES",SCEN) = SUM(XXBIOF,Data(MS,"SECG",XXBIOF,SCEN) /p_secgConv(XXBIOF))
                                             - DATA(MS,"NECR","LEVL_1",SCEN)*(p_newEnergyCropYield(MS) +
                                                                                   p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS)));

           DATA(MS,"bioNECR",XXBIOF,SCEN) $ (Data(MS,"SECG","BIOE",SCEN)+Data(MS,"SECG","BIOD",SCEN))
                                          =  DATA(MS,"NECR","LEVL_1",SCEN)*(p_newEnergyCropYield(MS) +
                                                                            p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS)))
                                          * Data(MS,"SECG",XXBIOF,SCEN) /(Data(MS,"SECG","BIOE",SCEN)+Data(MS,"SECG","BIOD",SCEN));


           DATA(MS,"bioARES",XXBIOF,SCEN) =  Data(MS,"SECG",XXBIOF,SCEN)- DATA(MS,"bioNECR",XXBIOF,SCEN);

    Departures from CAPRI: none."""
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "SECG", "ARES", t, sum(D.get(ms, "SECG", f, t) / P.p_secgConv[f] for f in S.XXBIOF)
                  - D.get(ms, "NECR", "LEVL_1", t) * _necr_yield(P, ms))
    for ms in S.MS:
        for f in S.XXBIOF:
            for t in S.SCEN:
                tot = D.get(ms, "SECG", "BIOE", t) + D.get(ms, "SECG", "BIOD", t)
                if tot:
                    D.set(ms, "bioNECR", f, t, D.get(ms, "NECR", "LEVL_1", t) * _necr_yield(P, ms)
                          * D.get(ms, "SECG", f, t) / tot)
    for ms in S.MS:
        for f in S.XXBIOF:
            for t in S.SCEN:
                D.set(ms, "bioARES", f, t, D.get(ms, "SECG", f, t) - D.get(ms, "bioNECR", f, t))


def DATA_delete_contents(D: Data, S: YearSets) -> None:
    r"""The EAA's positions, the outputs' feed contents but CRPR and DRMA, and the regions' (not the member states')
    contents of the feeds deleted.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 797-803):

           SET EAA(COLS) / EAAP,EAAB,EAAG /;
           DATA(RS,EAA,IO,SCEN)      = 0;
        *
        *  --- delete data never needed in the following (feed related contents of outputs)
        *      except those for CRPR and DRMA which are used in digestibility.gms
           DATA(RS,REQSC,OSECO,SCEN) $ (NOT (SAMEAS(REQSC,"CRPR") or SAMEAS(REQSC,"DRMA")))  = 0;
           DATA(RU,REQSC,FEED,SCEN) $ (NOT SUM(SAMEAS(RU,MS),1)) = 0;

    Departures from CAPRI: none."""
    for t in S.SCEN:
        for (c, w) in D.keys(t):
            drop = ((c in ("EAAP", "EAAB", "EAAG") and w in S.IO)
                    or (c in S.REQSC and w in S.OSECO and c not in ("CRPR", "DRMA")))
            sub = c in S.REQSC and w in S.FEED
            if not (drop or sub):
                continue
            for r in list(D.at(c, w, t)):
                if r in S.RS and (drop or (r in S.RU and r not in S.MS)):
                    D.set(r, c, w, t, 0)


def assert_year_data(D: Data, S: YearSets) -> None:
    r"""The year's activity levels are at least 1e-4 where positive, and each output's gross production is its
    activities' levels times yields within 1e-4 (but ARES and the organic fertilisers): CAPRI stops otherwise.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 849-863):

        p_problemTol = 1E-4;
        p_problem2D(rs,mpact) $ [(data(rs,mpact,"levl","y") gt 0) and (data(rs,mpact,"levl","y") lt p_problemTol)]
                                  = data(rs,mpact,"levl","y");

        $batInclude 'util\assert_empty_set.gms' p_problem2D 'Trend activity level is smaller than tolerable minimum'


        * --- Verify that the loaded data satisfies basic balancing conditions
        p_problemTol = 0.0001;
        *     GROF must be LEVL*yield
        problemItem2D(rs,o) $ [(not sameas(o,"ares")) and (not fout(o)) and (abs(data(rs,"grof",o,"y")
                                  - sum(mpact $ pact_to_o(mpact,o), data(rs,mpact,"levl","y")*data(rs,mpact,o,"y"))/1000)
                                  gt p_problemTol)] = yes;

        $batInclude 'util\assert_empty_set.gms' problemItem2D 'Grof does not match levl*yield'

    Departures from CAPRI: none."""
    small = sorted((r, a, v) for a in S.MPACT for r, v in D.at(a, "LEVL", "Y").items()
                   if r in S.RS and 0 < v < 1e-4)
    if small:
        raise ValueError(f"Trend activity level is smaller than tolerable minimum: {small[:10]}")
    acts_of = {}
    for (a, o) in S.PACT_TO_O:
        if a in S.MPACT:
            acts_of.setdefault(o, []).append(a)
    bad = []
    for o in S.O:
        if o == "ARES" or o in S.FOUT:
            continue
        for r in S.RS:
            g = D.get(r, "GROF", o, "Y")
            s = sum(D.get(r, a, "LEVL", "Y") * D.get(r, a, o, "Y") for a in acts_of.get(o, ())) / 1000.
            if abs(g - s) > 1e-4:
                bad.append((r, o, g, s))
    if bad:
        raise ValueError(f"Grof does not match levl*yield: {bad[:10]}")


def year_data(D: Data, D2: Data, S: YearSets, check: bool = True, P: ResidsParams = None,
              same_year: bool = False) -> set:
    """CAPRI's sequence of load_base_data_and_trends.gms l. 297-863 for the statements ported (module docstring), on
    D (the base year on "BAS") and D2 (the trends, CAPTRD's DATA2 at "Y"); returns FROM_CAPTRD. P: biofuel/resids.gms's
    parameters (by default from capri_data); same_year: the simulation year is the base year (CALYEA, resids.gms
    l. 81-85; not in CAPRI's 2030 baseline)."""
    P = P or ResidsParams.from_csv()
    DATA2_GROF_FODDI(D2, S)
    DATA2_feeds_not_in_base(D2, D, S)
    DATA_TRD_from_trends(D, D2, S)
    DATA_TRD_small_areas(D, S)
    DATA_TRD_GROF_OCRO(D, S)
    DATA_TRD_FALL_invented(D, S)
    DATA_TRD_small_quantities(D, S)
    delete_tiny_activity_level(D, S, "TRD", 1e-3)
    check_uaar_trend(D, S)
    DATA_TRD_young_animals_fixed(D, S)
    fc = FROM_CAPTRD_(D2, S)
    DATA_TRD_LOSF_STRA(D, S)
    DATA_TRD_LOSF_ratio(D, S)
    DATA_TRD_GROF_FODDI(D, S)
    DATA_Y_(D, S, fc)
    DATA_Y_UAAR(D, S)
    DATA_young_animal_coefficients(D, S)
    DATA_delete_positions(D, S)
    DATA_MS_feed_balances(D, S)
    DATA_split_activities(D, S)
    DATA_delete_after_year(D, S)
    DATA_NO_QUTS_SGMI(D, S)
    DATA_BIOF_PRCB_WHEA(D, S)
    DATA_EXOG_tiny_feedstocks(D, S)
    DATA_FSTG_PROD_biofuels(D, S)
    DATA_DDGS(D, S)
    DATA_PRCY_CAK(D, S)
    DATA_MAPR_MLK_small(D, S)
    DATA_FATSPROT_MILK(D, S)
    DATA_ARES(D, S, P)                      # biofuel/resids.gms, included at l. 795
    DATA_NECR_LEVL_1_2(D, S, P, same_year)
    DATA_SECG_ARES_bio(D, S, P)
    DATA_delete_contents(D, S)
    delete_tiny_activity_level(D, S, "Y", 1e-3)
    if check:
        assert_year_data(D, S)
    return fc

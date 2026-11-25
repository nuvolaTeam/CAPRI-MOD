r"""CAPRI's data of the simulation year as capmod/create_sim_ini_gdx.gms leaves them before the requirements
(l. 309-369; CAPRI star 3.0, baseline mode): the animals' feed and the activities' levels at "Y" taken from the trends, energy
maize's industrial use moved to the exogenous demand, and the positions not needed later deleted ("delete temp. data
to spare memory").

It follows capri_mod/projection/equations/load_base_data_and_trends.py (create_sim_ini_gdx.gms l. 34 includes
capmod/load_base_data_and_trends.gms), on its Data and YearSets. Between the two, create_sim_ini_gdx.gms l. 35-305 run
the farm types, the technical factors, the policy agenda, the milk quotas, MITERRA's emission factors and the market
model's calibration; their statements on DATA are not ported here. Not ported either:
- l. 246-247 (the animals' feed and the levels at "Y" set to the base year's for the market model's calibration): l.
  311-312 overwrite every cell they set;
- l. 309, policy/mtr_market_del.gms: the EU_West market's policy positions (PADM, INTM, CSEi, CSEd, FSEi), the EU
  aggregates' FEOE_MAX of 2005 and p_sugarPolicyRegime; none is read by the feed chain.

One function per CAPRI statement block, in CAPRI's order; create_sim_ini_gdx_data runs them. Departures from CAPRI:
none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_set
from capri_mod.projection.equations.load_base_data_and_trends import Data, OSet, YearSets


@dataclass
class DelSets:
    """The further sets of the deletions (sim_ini_21730's, capri_data/codes/capri), in CAPRI's order."""
    OAGGR: OSet
    MRKBAL: OSet
    NONEND: OSet
    FERT_DIST: OSet
    FNUT_COLS: OSet
    I: OSet
    REQMSN: OSet

    @classmethod
    def from_codes(cls):
        return cls(**{f: OSet(capri_set(f)) for f in cls.__dataclass_fields__})


def _zero(D: Data, t: str, keep) -> None:
    """Every cell at position t whose (region, column, row) keep accepts set to zero (deleted)."""
    for (c, w) in D.keys(t):
        for r in list(D.at(c, w, t)):
            if keep(r, c, w):
                D.set(r, c, w, t, 0)


def DATA_Y_feed_and_levels_from_TRD(D: Data, S: YearSets) -> None:
    r"""The animals' feed and the activities' levels at "Y" are the trends' ("TRD").

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 311-312):

          DATA(RS,MAACT,FEED,"Y")     = DATA(RS,MAACT,FEED,"TRD");
          DATA(RS,MPACT,"LEVL","Y")   = DATA(RS,MPACT,"LEVL","TRD");

    Departures from CAPRI: none."""
    for (c, w) in set(D.keys("Y")) | set(D.keys("TRD")):
        if (c in S.MAACT and w in S.FEED) or (c in S.MPACT and w == "LEVL"):
            for r in S.RS:
                D.set(r, c, w, "Y", D.get(r, c, w, "TRD"))


def p_exoDemand_MAIF(D: Data, S: YearSets) -> dict:
    r"""Energy maize's industrial use moves to the exogenous demand p_exoDemand(RS, "DEMD", "MAIF") (deducted to obtain
    the green maize fed) and is deleted from the regional units' DATA. Returns p_exoDemand {(region, "DEMD", "MAIF"):
    value}.

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 320-323):

        *        Case of energy maize: will be deducted to obtain the feed quantity of green maize
          option kill=p_exoDemand;
          p_exoDemand(RS,"DEMD","MAIF") = DATA(RS,"INDM","MAIF","Y");
          DATA(RU,"INDM","MAIF","Y")                                                        = 0;

    Departures from CAPRI: none."""
    out = {}
    for r in S.RS:
        v = D.get(r, "INDM", "MAIF", "Y")
        if v:
            out[(r, "DEMD", "MAIF")] = v
    for r in S.RU:
        D.set(r, "INDM", "MAIF", "Y", 0)
    return out


def DATA_delete_aggregates_and_fertiliser_balance(D: Data, S: YearSets, L: DelSets) -> None:
    r"""The member states' aggregate columns (OAGGR) and export demand, the internal use of every input (INTF) and the
    net trade of the fertilisers: the member states' at "Y", the regions' but nitrogen's at "Y" and "BAS".

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 325-329):

          DATA(MS,COLS,ROWS,"Y")  $ SUM(SAMEAS(COLS,OAGGR),1)                               = 0;
          DATA(RS,"INTF",IO,"Y")                                                            = 0;
          DATA(MS,"NETF",IO,"Y")                                                            = 0;
          DATA(RS,"NETF",IO,SCEN)  $ (NOT SUM(SAMEAS(MS,RS),1) and (not sameas(IO,"NITF"))) = 0;
          DATA(MS,"EXPD",ROWS,"Y")                                                          = 0;

    Departures from CAPRI: none."""
    _zero(D, "Y", lambda r, c, w: r in S.MS and c in L.OAGGR)
    _zero(D, "Y", lambda r, c, w: r in S.RS and c == "INTF" and w in S.IO)
    _zero(D, "Y", lambda r, c, w: r in S.MS and c == "NETF" and w in S.IO)
    for t in S.SCEN:
        _zero(D, t, lambda r, c, w: r in S.RS and r not in S.MS and c == "NETF" and w in S.IO and w != "NITF")
    _zero(D, "Y", lambda r, c, w: r in S.MS and c == "EXPD")


def DATA_delete_market_balance(D: Data, S: YearSets, L: DelSets) -> None:
    r"""The member states' market balance positions at "Y" (but the feed use FEDM, and the products without a market,
    NONEND).

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 331-333):

          DATA(MS,MRKBAL,ROWS,"Y") $ ( (NOT NONEND(ROWS))
                                     $ (NOT SAMEAS(MRKBAL,"FEDM"))
                                     $ (NOT (SAMEAS(MRKBAL,"FEDM") $ SAMEAS(ROWS,"MAIF")))) = 0;

    Departures from CAPRI: none."""
    _zero(D, "Y", lambda r, c, w: r in S.MS and c in L.MRKBAL and w not in L.NONEND and c != "FEDM")


def DATA_delete_prices_fertiliser_and_labour(D: Data, S: YearSets, L: DelSets) -> None:
    r"""The member states' price indices at "BAS", the activities' fertiliser distribution and labour at "BAS" and
    "TRD", the member states' unit values at "Y" (UVAD, UVAB, UVAP) and the market regions' export and import unit
    values (UVAE, UVAI).

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 335-345):

          DATA(MS,"PRII",ROWS,"BAS")                                                        = 0;
          DATA(RS,PACT,FERT_DIST,"BAS")                                                     = 0;
          DATA(RS,PACT,FERT_DIST,"TRD")                                                     = 0;
          DATA(RS,PACT,ILAB,"BAS")                                                          = 0;
          DATA(RS,PACT,ILAB,"TRD")                                                          = 0;
          DATA(MS,"UVAD",ROWS,"Y")                                                          = 0;
        *
          DATA(MS,"UVAB",ROWS,"Y")                                                          = 0;
          DATA(MS,"UVAP",ROWS,"Y")                                                          = 0;
          DATA(RMS,"UVAE",ROWS,"Y")                                                         = 0;
          DATA(RMS,"UVAI",ROWS,"Y")                                                         = 0;

    Departures from CAPRI: none."""
    _zero(D, "BAS", lambda r, c, w: r in S.MS and c == "PRII")
    for t in ("BAS", "TRD"):
        _zero(D, t, lambda r, c, w: r in S.RS and c in S.PACT and w in L.FERT_DIST)
    for t in ("BAS", "TRD"):
        _zero(D, t, lambda r, c, w: r in S.RS and c in S.PACT and w in S.ILAB)
    _zero(D, "Y", lambda r, c, w: r in S.MS and c in ("UVAD", "UVAB", "UVAP"))
    _zero(D, "Y", lambda r, c, w: r in S.RMS and c in ("UVAE", "UVAI"))


def DATA_delete_inputs_and_data_activities(D: Data, S: YearSets, L: DelSets) -> None:
    r"""The member states' gross production of the inputs but the feeds, and the data activities' rows but their levels
    (and those of GRAS and SETA) at "Y".

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 347-349):

          DATA(MS,"GROF",I,"Y")     $ (NOT FEED(I))                                         = 0;
          DATA(RS,DACT,ROWS,"Y")$ ( (NOT SAMEAS(DACT,"GRAS")) $ (NOT SAMEAS(DACT,"SETA"))
                                  $ (NOT SAMEAS(ROWS,"LEVL")))                              = 0;

    Departures from CAPRI: none."""
    _zero(D, "Y", lambda r, c, w: r in S.MS and c == "GROF" and w in L.I and w not in S.FEED)
    _zero(D, "Y", lambda r, c, w: r in S.RS and c in S.DACT and c not in ("GRAS", "SETA") and w != "LEVL")


def DATA_delete_production_and_fertiliser_distribution(D: Data, S: YearSets, L: DelSets) -> None:
    r"""The production position PROD at "Y" and "TRD", the farmland's fertiliser distribution at "BAS" and "Y", and
    the outputs' mineral fertiliser columns at "BAS".

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 351-355):

          DATA(RS,"PROD",ROWS,"Y")                                                          = 0;
          DATA(RS,"PROD",ROWS,"TRD")                                                        = 0;
          DATA(RS,"UAAR",FERT_DIST,"BAS")                                                   = 0;
          DATA(RS,"UAAR",FERT_DIST,"Y")                                                     = 0;
          DATA(RS,FNUT_COLS,O,"BAS")                                                        = 0;

    Departures from CAPRI: none."""
    for t in ("Y", "TRD"):
        _zero(D, t, lambda r, c, w: r in S.RS and c == "PROD")
    for t in ("BAS", "Y"):
        _zero(D, t, lambda r, c, w: r in S.RS and c == "UAAR" and w in L.FERT_DIST)
    _zero(D, "BAS", lambda r, c, w: r in S.RS and c in L.FNUT_COLS and w in S.O)


def DATA_delete_regions_unit_values_and_contents(D: Data, S: YearSets, L: DelSets) -> None:
    r"""In the regions (not the member states): the unit values of the inputs and outputs but fodder at "Y", and the
    contents but crude protein at "Y" and "BAS"; in the member states the feeds' inequality contents at "BAS".

    CAPRI's GAMS (capmod/create_sim_ini_gdx.gms l. 358-369):

          RS(MS) = NO;
          option kill=MAPPR;

          MAPPR(IO) = YES;
          MAPPR(FODDO) = NO;
          MAPPR(FODDI) = NO;
          DATA(RS,MAPP,MAPPR,"Y") = 0;
          DATA(RS,REQSC,ROWS,"Y")   $ (NOT SAMEAS(REQSC,"CRPR")) = 0;
          DATA(RS,REQSC,ROWS,"BAS") $ (NOT SAMEAS(REQSC,"CRPR")) = 0;
          RS(MS) = YES;

          DATA(MS,REQMSN,FEED,"BAS")    = 0;

    MAPPR: IO without FODDO and FODDI. Departures from CAPRI: none."""
    mappr = {w for w in S.IO if w not in S.FODDO and w not in S.FODDI}
    reg = lambda r: r in S.RS and r not in S.MS                              # noqa: E731  (RS(MS) = NO)
    _zero(D, "Y", lambda r, c, w: reg(r) and c in S.MAPP and w in mappr)
    for t in ("Y", "BAS"):
        _zero(D, t, lambda r, c, w: reg(r) and c in S.REQSC and c != "CRPR" and w in S.ROWS)
    _zero(D, "BAS", lambda r, c, w: r in S.MS and c in L.REQMSN and w in S.FEED)


def create_sim_ini_gdx_data(D: Data, S: YearSets, L: DelSets = None) -> dict:
    """CAPRI's sequence of create_sim_ini_gdx.gms l. 311-369 on the year's data; returns p_exoDemand."""
    L = L or DelSets.from_codes()
    DATA_Y_feed_and_levels_from_TRD(D, S)
    exo = p_exoDemand_MAIF(D, S)
    DATA_delete_aggregates_and_fertiliser_balance(D, S, L)
    DATA_delete_market_balance(D, S, L)
    DATA_delete_prices_fertiliser_and_labour(D, S, L)
    DATA_delete_inputs_and_data_activities(D, S, L)
    DATA_delete_production_and_fertiliser_distribution(D, S, L)
    DATA_delete_regions_unit_values_and_contents(D, S, L)
    return exo

r"""CAPRI's manure output functions: the N, P2O5 and K2O at the tail of each animal activity, per head (MANN, MANP, MANK),
from the year's herd data (feed/req_or_man_fnc.gms called with %1 = man, PART I and PART III; CAPRI star 3.0).

CAPRI's simulation runs this once before it solves (capmod.gms l. 1090, $BATINCLUDE 'feed\req_or_man_fnc.gms' man '"Y"'
when not in baseline mode), on DATA(..., "Y"), the simulation year's data as loaded (the baseline's state). In 'man' mode
the file computes, animal by animal:
- MANP and MANK from the milk yield, the fattening days and the mean live weight, with CAPRI's fixed manure nutrient
  contents (p_NutContManureKgM3, p_addExcrPerkgMilk; feed/feed_decl.gms); not from the feed (the feed-based method,
  %Phoendogenous%, is off in CAPRI's Green Deal runs);
- MANN from the literature crude-protein requirement p_crprReq (the same functions as the 'req' mode's CRPR, at the
  data's yields), times the correction factor p_animExcrProtCorrFact over 6 kg of crude protein per kg N, less the N in
  the animal's products CRPR_EXPT (fert/calc_nexport.gms, run first in PART III).

One function per CAPRI statement block, in CAPRI's order; ManState holds CAPRI's symbols of the block (p_dataCopy,
p_meanLiveWgt, p_fatngDays, ...) as dictionaries; req_or_man_fnc_man runs the blocks in order. CAPRI's %yr_A% and %yr%
are both "Y" in 'man' mode, so the per-head parameters carry no technology index; p_crprReq and p_MANN_A carry CAPRI's
technology A. The literal tables of feed/feed_decl.gms are data (capri_data/2017/feed/manure_output_params.csv,
tools/build/build_manure_output_params.py), with the pig-fattening requirement tables of CAPRI's dat/feed/porkreq.gms
(p_pigsReqLowWgt, p_pigsReqHighWgt); a call without them leaves the fattened pigs out (ManState.not_computed, see
p_finalLiveWgt_PIGF).

Departures from CAPRI: none in the functions. The inputs are the caller's (req_or_man_fnc_man's docstring).
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: CAPRI's sets (sets.gms, feed/feed_decl.gms)
DCOW = ("DCOL", "DCOH")
CALF = ("CAMF", "CAFF")
CALR = ("CAMR", "CAFR")
BULF = ("BULL", "BULH")
HEIF = ("HEIL", "HEIH")
NRUMI = ("PIGF", "SOWS", "POUF", "HENS")
#: the manure rows (FOUT) and those 'man' mode assigns together (curRows: FOUT less MANN, l. 117-121)
FOUT = ("MANN", "MANP", "MANK")
curRows = ("MANP", "MANK")


@dataclass
class ManState:
    """CAPRI's symbols of one call of req_or_man_fnc.gms in 'man' mode at "Y".

    DATA: {(region, column, row): value} at the year (CAPRI's DATA(RS, COLS, ROWS, "Y")); RS: the regions computed
    (CAPRI's RS: member states and their NUTS 1 and 2 regions); MS: the member states; R_RAGG_MS: {region: its member
    state} (R_RAGG restricted to MS on the second position); GRSACT, RUMI: CAPRI's sets; p_LUUnits: {activity:
    livestock units}; p_technFact: {(region, activity, row, A): value}; p_animExcrProtCorrFact: {(region, activity, A):
    value} at "Y"; the literal tables of feed/feed_decl.gms; p_pigsReqLowWgt, p_pigsReqHighWgt: {(class, item): value}
    (empty where CAPRI's dat/feed/porkreq.gms is not available)."""
    DATA: dict
    RS: tuple
    MS: frozenset
    R_RAGG_MS: dict
    GRSACT: tuple
    RUMI: tuple
    p_LUUnits: dict
    p_technFact: dict
    p_animExcrProtCorrFact: dict
    p_NutContManureKgM3: dict
    p_addExcrPerkgMilk: dict
    p_carcassShare: dict
    p_startWgt: dict
    p_reqfcnlim: dict
    p_pigsReqLowWgt: dict = field(default_factory=dict)
    p_pigsReqHighWgt: dict = field(default_factory=dict)
    # CAPRI's parameters of the call
    p_dataCopy: dict = field(default_factory=dict)
    p_stockingRate: dict = field(default_factory=dict)
    p_milkFatCont: dict = field(default_factory=dict)
    p_meanLiveWgt: dict = field(default_factory=dict)
    p_milkPerDay: dict = field(default_factory=dict)
    p_femWgt: dict = field(default_factory=dict)
    p_dailyWgtIncrease: dict = field(default_factory=dict)
    p_animProdDays: dict = field(default_factory=dict)
    p_fatngDays: dict = field(default_factory=dict)
    p_finalLiveWgt: dict = field(default_factory=dict)
    p_sharGoatHerd: dict = field(default_factory=dict)
    p_crprReq: dict = field(default_factory=dict)
    p_MANN_A: dict = field(default_factory=dict)
    #: the animal activities whose manure the call could not compute (PIGF without CAPRI's pig requirement tables): their
    #: MANN, MANP and MANK in DATA are the input's, not the year's
    not_computed: set = field(default_factory=set)

    def D(self, r, c, row):
        """DATA(r, c, row, "Y"), 0 where absent (GAMS)."""
        return float(self.DATA.get((r, c, row), 0.0) or 0.0)

    def dc(self, r, c, row):
        """p_dataCopy(r, c, row, "Y"), 0 where absent."""
        return float(self.p_dataCopy.get((r, c, row), 0.0) or 0.0)

    def tf(self, r, c, row, a):
        """p_technFact(r, c, row, a), 0 where absent."""
        return float(self.p_technFact.get((r, c, row, a), 0.0) or 0.0)

    def techs(self, r, c):
        """CAPRI's technologies A with p_technFact(r, c, "LEVL", A) (the $-condition of p_crprReq)."""
        return [a for (rr, cc, row, a), v in self.p_technFact.items() if rr == r and cc == c and row == "LEVL" and v]

    def lim(self, c, row, bound):
        """p_reqfcnlim(c, row, bound), 0 where absent (GAMS)."""
        return float(self.p_reqfcnlim.get((c, row, bound), 0.0) or 0.0)

    def ms_sum(self, r, f):
        """SUM(R_RAGG(r, MS), f(MS))."""
        m = self.R_RAGG_MS.get(r)
        return f(m) if m is not None else 0.0

    def LEVL(self, r, c):
        """p_dataCopy(r, c, "LEVL", "Y") (CAPRI's %p_condition% in 'man' mode)."""
        return self.dc(r, c, "LEVL")


# ------------------------------------------------------------------ feed/feed_decl.gms: the manure nutrient contents
def p_NutContManureKgM3_per_kg_day(p_NutContManureKgM3: dict) -> dict:
    r"""The manure nutrient contents per kg of live weight and day (CATTLE, SOWS, PIGF, POULTRY) from CAPRI's contents
    per cubic metre (CATT, SWINE, POUL) and its manure volumes per animal.

    CAPRI's GAMS (feed/feed_decl.gms l. 146-157):

          p_NutContManureKgM3("CATTLE",FOUT)   = p_NutContManureKgM3("CATT",FOUT) * 18./(500.*365.);
        *
        *  5 m3 per sow and year, here converted per kg lievweight and day
          p_NutContManureKgM3("SOWS" ,FOUT)   = p_NutContManureKgM3("SWINE",FOUT) * 5.  / (200.*365.+10.*15.*42.);
        *
        * 1.9 M3 per pork fattening stable place and year in Germany,
        * typical slaughtered weight 90 kg
        *
          p_NutContManureKgM3("PIGF" ,FOUT)    = p_NutContManureKgM3("SWINE",FOUT) * 1.9 / ( (90./0.78-20)*0.5 * 143. * 2.3 );
        *
        *  8 m3 per 100 laying hens, here converted per kg lievweight and day
          p_NutContManureKgM3("POULTRY",FOUT)  = p_NutContManureKgM3("POUL",FOUT) * 8./( 1.9*365.*100.);

    In this project's notation: c(CATTLE) = c(CATT) x 18 / (500 x 365), c(SOWS) = c(SWINE) x 5 / (200 x 365 + 10 x
    15 x 42), c(PIGF) = c(SWINE) x 1.9 / ((90 / 0.78 - 20) x 0.5 x 143 x 2.3), c(POULTRY) = c(POUL) x 8 / (1.9 x 365 x
    100), for MANN, MANP and MANK. Departures from CAPRI: none."""
    out = dict(p_NutContManureKgM3)
    for row in FOUT:
        out[("CATTLE", row)] = p_NutContManureKgM3.get(("CATT", row), 0.0) * 18. / (500. * 365.)
        out[("SOWS", row)] = p_NutContManureKgM3.get(("SWINE", row), 0.0) * 5. / (200. * 365. + 10. * 15. * 42.)
        out[("PIGF", row)] = p_NutContManureKgM3.get(("SWINE", row), 0.0) * 1.9 / ((90. / 0.78 - 20) * 0.5 * 143. * 2.3)
        out[("POULTRY", row)] = p_NutContManureKgM3.get(("POUL", row), 0.0) * 8. / (1.9 * 365. * 100.)
    return out


# ------------------------------------------------------------------ PART I: the regional stocking rate and the copy
def DATA_AGGR_YCOW(st: ManState) -> None:
    r"""The regional stocking rate: the ruminants' livestock units per ha of fodder area (grassland, other arable
    fodder and fodder maize less its share used as energy maize), DATA(RS, "AGGR", "YCOW").

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 100-110):

          DATA(RS,"AGGR","YCOW",%yr%) $
            (SUM(GRSACT, DATA(RS,GRSACT,"LEVL",%yr%))
                        +DATA(RS,"OFAR","LEVL",%yr%)+DATA(RS,"MAIF","LEVL",%yr%))
           =
              SUM(RUMI, DATA(RS,RUMI,"LEVL",%yr%)*p_LUUnits(RUMI))
            /(SUM(GRSACT, DATA(RS,GRSACT,"LEVL",%yr%))
                           +DATA(RS,"OFAR","LEVL",%yr%)+DATA(RS,"MAIF","LEVL",%yr%)
        *                                                  correct for energy maize that should not count as fodder area
                                                       *(1-(  DATA(RS,"INDM","MAIF",%yr%)
                                                            /(DATA(RS,"INDM","MAIF",%yr%)+DATA(RS,"FEDM","MAIF",%yr%)))
                                                           $ (DATA(RS,"INDM","MAIF",%yr%)+DATA(RS,"FEDM","MAIF",%yr%))));

    Departures from CAPRI: none."""
    for r in st.RS:
        area = sum(st.D(r, g, "LEVL") for g in st.GRSACT) + st.D(r, "OFAR", "LEVL") + st.D(r, "MAIF", "LEVL")
        if not area:
            continue
        indm, fedm = st.D(r, "INDM", "MAIF"), st.D(r, "FEDM", "MAIF")
        share = indm / (indm + fedm) if (indm + fedm) else 0.0
        den = sum(st.D(r, g, "LEVL") for g in st.GRSACT) + st.D(r, "OFAR", "LEVL") + st.D(r, "MAIF", "LEVL") * (1 - share)
        st.DATA[(r, "AGGR", "YCOW")] = sum(st.D(r, a, "LEVL") * st.p_LUUnits.get(a, 0.0) for a in st.RUMI) / den


def p_stockingRate(st: ManState) -> None:
    r"""The stocking density index of each region: its member state's stocking rate, its own where it has one; a member
    state's own, 1.5 where it has none.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 112-114):

          p_stockingRate(RS,%yr%) = SUM( R_RAGG(RS,MS),DATA(MS,"AGGR","YCOW",%yr%));
          p_stockingRate(RS,%yr%) $ DATA(RS,"AGGR","YCOW",%yr%) = DATA(RS,"AGGR","YCOW",%yr%);
          p_stockingRate(MS,%yr%) = DATA(MS,"AGGR","YCOW",%yr%) + 1.5 $ (NOT DATA(MS,"AGGR","YCOW",%yr%) );

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_stockingRate[r] = st.ms_sum(r, lambda m: st.D(m, "AGGR", "YCOW"))
        if st.D(r, "AGGR", "YCOW"):
            st.p_stockingRate[r] = st.D(r, "AGGR", "YCOW")
    for m in st.MS:
        y = st.D(m, "AGGR", "YCOW")
        st.p_stockingRate[m] = y + (1.5 if not y else 0.0)


def p_dataCopy_man(st: ManState) -> None:
    r"""The copy of the data the functions work on ('man' mode: every row of the animal activities, and the sheep's and
    goats' herds).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 125-136):

          option kill=p_dataCopy;
        $iftheni.data %req% ==on
        $          ifi %FARM_M%==on   $include "util\kill_model1.gms"
                    p_dataCopy(RS,AACT,"LEVL",%yr%) = DATA(RS,AACT,"LEVL",%yr%);
                    p_dataCopy(RS,AACT,"DAYS",%yr%) = DATA(RS,AACT,"DAYS",%yr%);
                    p_dataCopy(RS,AACT,"DAILY",%yr%)= DATA(RS,AACT,"DAILY",%yr%);
                    p_dataCopy(RS,AACT,O,%yr%)      = DATA(RS,AACT,O,%yr%);
        $else.data
                    p_dataCopy(RS,AACT,ROWS,%yr%)= DATA(RS,AACT,ROWS,%yr%);
        $endif.data
          p_dataCopy(RS,"SHEP","HERD",%yr%) = DATA(RS,"SHEP","HERD",%yr%);
          p_dataCopy(RS,"GOAT","HERD",%yr%) = DATA(RS,"GOAT","HERD",%yr%);

    Departures from CAPRI: the copy holds every column of DATA (the functions read the animal activities' rows and the
    sheep's and goats' herds only, so the result is the same)."""
    st.p_dataCopy = dict(st.DATA)


# ------------------------------------------------------------------ (1) milk cows
def p_dataCopy_curRows_DCOW(st: ManState) -> None:
    r"""The dairy cows' P2O5 and K2O at the tail: an amount per kg of milk (cow milk sold and fed) plus 18 m3 of manure
    a year of a 600 kg cow.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 144-148):

        $iftheni.req2 not %req% ==on
                    p_dataCopy(RS,DCOW,curRows,%yr%) $ p_dataCopy(RS,DCOW,"LEVL",%yr%)
                      = (p_dataCopy(RS,DCOW,"COMI",%yr%) + p_dataCopy(RS,DCOW,"COMF",%yr%))  * p_addExcrPerkgMilk(curRows)
                       + p_NutContManureKgM3("CATTLE",curRows) * 365. * 600.;
        $endif.req2

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = ((st.dc(r, a, "COMI") + st.dc(r, a, "COMF")) * st.p_addExcrPerkgMilk[row]
                                                  + st.p_NutContManureKgM3[("CATTLE", row)] * 365. * 600.)


def p_milkFatCont(st: ManState) -> None:
    r"""The milk fat content, 4% in every region.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 150-152):

        * --- default if regional milk content is not known: 4 %
        *
          p_milkFatCont(RS,"FATS") = 4.0;

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_milkFatCont[(r, "FATS")] = 4.0


def p_meanLiveWgt_DCOW(st: ManState) -> None:
    r"""The dairy cows' mean live weight, 600 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 156):

          p_meanLiveWgt(RS,DCOW,%yr_A%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%) = 600.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = 600.0


def p_milkPerDay_DCOW(st: ManState) -> None:
    r"""The dairy cows' milk per lactation day ('man' mode: the data's milk sold and fed over 305 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 164-173):

          p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%)


        $iftheni.perday %req% ==on
                      =  p_dataCopy(RS,DCOW,"COMI",%yr%)*(p_technFact(RS,DCOW,"COMI",A)+1.) / 305.
                       + p_dataCopy(RS,DCOW,"COMF",%yr%)*(p_technFact(RS,DCOW,"COMF",A)+1.) / 305.;
        $else.perday
                     =  p_dataCopy(RS,DCOW,"COMI",%yr%) / 305.
                      + p_dataCopy(RS,DCOW,"COMF",%yr%) / 305.;
        $endif.perday

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            if st.LEVL(r, a):
                st.p_milkPerDay[(r, a)] = st.dc(r, a, "COMI") / 305. + st.dc(r, a, "COMF") / 305.


def p_crprReq_DCOW(st: ManState) -> None:
    r"""The dairy cows' crude-protein requirement per head and year: lactation (305 days), maintenance (365 days) and
    the dry period (42 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 175-185):

        * --- calculation of CRPR as documented in old working paper from CAPRI 1996-1999 project
        *     NOTE: In order to share the code for calulation of N-excretions (MANN) and crude protein (CRPR) we first assign to p_crprReq
        *           and then copy in PART II to p_animReq (if needed)
        *
          p_crprReq(RS,DCOW,A,%yr%) $ p_technFact(RS,DCOW,"LEVL",A)
        *     -- for lactation period
            =  ( 14. * p_milkFatCont(RS,"FATS") + 28.00 ) / 1000. * p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * 305.
        *     -- for maintenance
             + ( 117. + 0.6 * p_meanLiveWgt(RS,DCOW,%yr_A%)  ) /1000.  * 365.
        *     -- for dry period
             + 1.300 * 42.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_crprReq[(r, a, t)] = ((14. * st.p_milkFatCont[(r, "FATS")] + 28.00) / 1000.
                                           * st.p_milkPerDay.get((r, a), 0.0) * 305.
                                           + (117. + 0.6 * st.p_meanLiveWgt.get((r, a), 0.0)) / 1000. * 365.
                                           + 1.300 * 42.)


# ------------------------------------------------------------------ (2) suckler cows
def p_dataCopy_curRows_SCOW(st: ManState) -> None:
    r"""The suckler cows' P2O5 and K2O at the tail: an amount per kg of milk fed plus the manure of a 550 kg cow.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 242-245):

        $iftheni.req4 not %req% ==on
                    p_dataCopy(RS,"SCOW",curRows,%yr%) $ p_dataCopy(RS,"SCOW","LEVL",%yr%) =     p_dataCopy(RS,"SCOW","COMF",%yr%) * p_addExcrPerkgMilk(curRows)
                                                                               + p_NutContManureKgM3("CATTLE",curRows) * 365. * 550.;
        $endif.req4

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            for row in curRows:
                st.p_dataCopy[(r, "SCOW", row)] = (st.dc(r, "SCOW", "COMF") * st.p_addExcrPerkgMilk[row]
                                                   + st.p_NutContManureKgM3[("CATTLE", row)] * 365. * 550.)


def p_meanLiveWgt_SCOW(st: ManState) -> None:
    r"""The suckler cows' mean live weight, 550 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 249):

          p_meanLiveWgt(RS,"SCOW",%yr_A%)  $ %p_condition%(RS,"SCOW","LEVL",%yr_A%) = 550.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            st.p_meanLiveWgt[(r, "SCOW")] = 550.0


def p_milkPerDay_SCOW(st: ManState) -> None:
    r"""The suckler cows' milk per lactation day ('man' mode: the data's milk fed over 125 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 254-259):

          p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) $ %p_condition%(RS,"SCOW","LEVL",%yr_A%)
        $iftheni.perday1 %req% ==on
                      = p_dataCopy(RS,"SCOW","COMF",%yr%)*(p_technFact(RS,"SCOW","COMF",A)+1.) / 125. ;
        $else.perday1
                      = p_dataCopy(RS,"SCOW","COMF",%yr%) / 125;
        $endif.perday1

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SCOW"):
            st.p_milkPerDay[(r, "SCOW")] = st.dc(r, "SCOW", "COMF") / 125


def p_crprReq_SCOW(st: ManState) -> None:
    r"""The suckler cows' crude-protein requirement per head and year: lactation (125 days), maintenance (365 days) and
    the last mating period (42 days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 261-271):

        * --- calculation of CRPR as documented in old working paper from CAPRI 1996-1999 project
        *     NOTE: In order to share the code for calculation of N-excretions (MANN) and crude protein (CRPR) we first assign to p_crprReq
        *           and then copy in PART II to p_animReq (if needed)
        *
          p_crprReq(RS,"SCOW",A,%yr%) $ p_technFact(RS,"SCOW","LEVL",A)
        *      --- for lactation period
            =( 14. * p_milkFatCont(RS,"FATS") + 28.00 ) / 1000. * p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * 125.
        *      --- for maintenance (copied from HEIR)
             + (0.00127 * p_meanLiveWgt(RS,"SCOW",%yr_A%) + 0.1273 ) * 365.
        *      --- for last mating period
             + 1.300 * 42.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_crprReq[(r, "SCOW", t)] = ((14. * st.p_milkFatCont[(r, "FATS")] + 28.00) / 1000.
                                            * st.p_milkPerDay.get((r, "SCOW"), 0.0) * 125.
                                            + (0.00127 * st.p_meanLiveWgt.get((r, "SCOW"), 0.0) + 0.1273) * 365.
                                            + 1.300 * 42.)


def p_femWgt(st: ManState) -> None:
    r"""The mean live weight of an adult female, the dairy and suckler cows' weighted by their herds (550 kg where the
    region has none).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 325-332):

        *     -- weighted average of dary cows and suckler cows
          p_femWgt(RS,%yr_A%) = 550;
          p_femWgt(RS,%yr_A%) $ (     sum(DCOW,p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                                  or          (p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%)))
            =
                  (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                            + p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%))
             /    (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)) + p_dataCopy(RS,"SCOW","LEVL",%yr%));

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_femWgt[r] = 550
        num = (sum(st.LEVL(r, a) * st.p_meanLiveWgt.get((r, a), 0.0) for a in DCOW)
               + st.LEVL(r, "SCOW") * st.p_meanLiveWgt.get((r, "SCOW"), 0.0))
        if sum(st.LEVL(r, a) * st.p_meanLiveWgt.get((r, a), 0.0) for a in DCOW) or \
                st.LEVL(r, "SCOW") * st.p_meanLiveWgt.get((r, "SCOW"), 0.0):
            st.p_femWgt[r] = num / (sum(st.LEVL(r, a) for a in DCOW) + st.LEVL(r, "SCOW"))


# ------------------------------------------------------------------ (3) fattening of calves
def _scaled_ms_daily(st: ManState, r, a):
    """SUM(R_RAGG(r, MS), p_dataCopy(MS, a, "DAILY") / p_stockingRate(MS)) * p_stockingRate(r)."""
    return st.ms_sum(r, lambda m: st.dc(m, a, "DAILY") / st.p_stockingRate[m]) * st.p_stockingRate.get(r, 0.0)


def p_dailyWgtIncrease_CALF(st: ManState) -> None:
    r"""The fattened calves' daily weight gain (kg): their member state's, scaled by the region's stocking rate over the
    member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 343-347):

          p_dailyWgtIncrease(RS,CALF,%yr_A%) $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAILY","up"),
                  MAX(p_reqfcnlim(CALF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,CALF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000


def p_animProdDays_CALF(st: ManState) -> None:
    r"""The fattened calves' process length: the gain from the 50 kg start to the final live weight (the carcass over
    its share) at the daily gain, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 353-361):

          p_animProdDays(RS,CALF,%yr_A% %addtimedim%)  $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAYS","up"),
                  MAX(p_reqfcnlim(CALF,"DAYS","lo"),
                  ( p_dataCopy(RS,CALF,"BEEF",%yr%) / p_carcassShare(CALF)
        $iftheni.req6 %req% ==on
                            *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req6
                  - p_startWgt(CALF))
                  / p_dailyWgtIncrease(RS,CALF,%yr_A%) ) );

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                st.p_animProdDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def _final_wgt_CALF(st: ManState, r, a):
    """p_dataCopy(r, a, "BEEF") / p_carcassShare(a): the fattened calf's final live weight ('man' mode)."""
    return st.dc(r, a, "BEEF") / st.p_carcassShare[a]


def p_meanLiveWgt_CALF_light(st: ManState) -> None:
    r"""(a) Light calves (final live weight up to 150 kg): the mean live weight, the start weight plus half the gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 367-374):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req7 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req7
                                             / p_carcassShare(CALF))  LE 150. )
        *                          increase up to mid point of fattening period:
            = (p_startWgt(CALF) + (p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)) / 2.)
            $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) <= 150.:
                st.p_meanLiveWgt[(r, a)] = ((st.p_startWgt[a] + (st.p_animProdDays.get((r, a), 0.0)
                                                                 * st.p_dailyWgtIncrease.get((r, a), 0.0)) / 2.)
                                            if st.LEVL(r, a) else 0.0)


def p_fatngDays_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: the fattening days, the whole process (one phase).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 377-384):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req8 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req8
                                             / p_carcassShare(CALF))  LE 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
            = p_animProdDays(RS,CALF,%yr_A% %addtimedim%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) <= 150. and st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = st.p_animProdDays[(r, a)]


def p_dataCopy_curRows_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: P2O5 and K2O at the tail, the cattle manure per kg of live weight and day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 386-390):

        * --- Excretions of potassium and phosphorus...
        $iftheni.req9 not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ p_dataCopy(RS,CALF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%) ;
        $endif.req9

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt.get((r, a), 0.0))


def _crpr_growth_lt150(mlw, daily, days):
    """( - 0.00039 * mean live weight + 0.000628 * daily gain [g] - 0.0193 ) * days: the crude protein of a calf's
    growth up to 150 kg (CAPRI's coefficients, feed/req_or_man_fnc.gms l. 395-396, 459-460, 616-617)."""
    return (- 0.00039 * mlw + 0.000628 * daily * 1000. - 0.0193) * days


def _crpr_growth_gt150(mlw, daily, days):
    """( 0.00109 * mean live weight + 0.00022 * daily gain [g] + 0.2027 ) * days: the crude protein of a calf's growth
    above 150 kg (CAPRI's coefficients, feed/req_or_man_fnc.gms l. 532, 681-682)."""
    return (0.00109 * mlw + 0.00022 * daily * 1000. + 0.2027) * days


def p_crprReq_CALF_light(st: ManState) -> None:
    r"""(a) Light calves: the crude-protein requirement of the fattening.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 392-396):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = _crpr_growth_lt150(st.p_meanLiveWgt.get((r, a), 0.0),
                                                                 st.p_dailyWgtIncrease.get((r, a), 0.0),
                                                                 st.p_fatngDays[(r, a)])


def p_meanLiveWgt_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves (final live weight above 150 kg), first phase from 50 to 150 kg: mean live weight 100 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 432-438):

          p_meanLiveWgt(RS,CALF,%yr_A%)  $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req11 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req11
                                             / p_carcassShare(CALF))  GT 150. )
        *     Note: 100 = (50+150)/2 = mean weight
            = 100.  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) > 150.:
                st.p_meanLiveWgt[(r, a)] = 100. if st.LEVL(r, a) else 0.0


def p_fatngDays_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: the days of the 100 kg gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 440-448):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req12 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req12
                                             / p_carcassShare(CALF))  GT 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
        *     Note: 100 = 150-50 = increase in phase (b1):
            = 100. / p_dailyWgtIncrease(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) > 150. and st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = 100. / st.p_dailyWgtIncrease[(r, a)]


def p_dataCopy_curRows_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 450-454):

        * --- Excretions of potassium and phosphorus...
        $iftheni.req13 not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ ( p_dataCopy(RS,CALF,"LEVL",%yr%)  $ p_fatngDays(RS,CALF,%yr_A%)  )
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%) ;
        $endif.req13

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt.get((r, a), 0.0))


def p_crprReq_CALF_heavy_b1(st: ManState) -> None:
    r"""(b1) Heavy calves, first phase: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 456-460):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = _crpr_growth_lt150(st.p_meanLiveWgt.get((r, a), 0.0),
                                                                 st.p_dailyWgtIncrease.get((r, a), 0.0),
                                                                 st.p_fatngDays[(r, a)])


def p_meanLiveWgt_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase from 150 kg to the final weight: 150 kg plus half the phase's gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 493-503):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni %req% ==on
                                            *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif
                                            / p_carcassShare(CALF))  GT 150. )
        *       wgt at end of phase b1:
            =(   150.
        *         increase in b1+b2:
             +(p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)
        *         increase in b1:
               - 100 ) / 2.)  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if _final_wgt_CALF(st, r, a) > 150.:
                st.p_meanLiveWgt[(r, a)] = ((150. + (st.p_animProdDays.get((r, a), 0.0)
                                                     * st.p_dailyWgtIncrease.get((r, a), 0.0) - 100) / 2.)
                                            if st.LEVL(r, a) else 0.0)


def p_fatngDays_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: its length.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 507-518):

          p_fatngDays(RS,CALF,%yr_A%) = 0;
          p_fatngDays(RS,CALF,%yr_A%) $ ( (  ( p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif
                                             / p_carcassShare(CALF))  GT 150. )
                                        $ %p_condition%(RS,CALF,"LEVL",%yr_A%))
        *     increase in b1+b2:
            =(p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)
        *     increase in b1:
              - 100)
            / p_dailyWgtIncrease(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            st.p_fatngDays[(r, a)] = 0
            if _final_wgt_CALF(st, r, a) > 150. and st.LEVL(r, a):
                d = st.p_dailyWgtIncrease[(r, a)]
                st.p_fatngDays[(r, a)] = (st.p_animProdDays[(r, a)] * d - 100) / d


def p_dataCopy_curRows_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: P2O5 and K2O at the tail, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 521-526):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALF,curRows,%yr%) $ ( p_dataCopy(RS,CALF,"LEVL",%yr%) $ p_fatngDays(RS,CALF,%yr_A%)  )
            =  p_dataCopy(RS,CALF,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALF,%yr_A%)  * p_meanLiveWgt(RS,CALF,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt.get((r, a), 0.0))


def p_crprReq_CALF_heavy_b2(st: ManState) -> None:
    r"""(b2) Heavy calves, second phase: the crude-protein requirement, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 528-532):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = p_crprReq(RS,CALF,A,%yr%)
             + ( 0.00109 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.00022 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. + 0.2027 ) * p_fatngDays(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            if st.p_fatngDays.get((r, a)):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_gt150(
                        st.p_meanLiveWgt.get((r, a), 0.0), st.p_dailyWgtIncrease.get((r, a), 0.0), st.p_fatngDays[(r, a)])


# ------------------------------------------------------------------ (4) raising of calves
def CALR_weaning(st: ManState) -> None:
    r"""Raised calves, the first 49 days (weaning, 50 to 80 kg): fattening days, mean live weight and P2O5 and K2O at
    the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 576-583):

        $iftheni not %req% ==on
          p_fatngDays(RS,CALR,%yr_A%) $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = 49;
          p_meanLiveWgt(RS,CALR,%yr_A%) $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = (50+80)/2;
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = 49
                st.p_meanLiveWgt[(r, a)] = (50 + 80) / 2
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_weaning(st: ManState) -> None:
    r"""Raised calves, weaning: the crude protein of the milk powder, in increasing quantity over the seven weeks.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 585-589):

        * --- milking powder in increasing quantity
        *
        *     (remember that nitrogen excretions are copied below to CRPR if needed)
          p_crprReq(RS,CALR,A,%yr%)  $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
            = 0.35  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = 0.35 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49


def CALR_80_150(st: ManState) -> None:
    r"""Raised calves, the next 125 days (80 to 150 kg): mean live weight, daily gain and fattening days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 601-603):

          p_meanLiveWgt(RS,CALR,%yr_A%)      $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 80. + 150.) / 2. ;
          p_dailyWgtIncrease(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = (150.-80.)/125.;
          p_fatngDays(RS,CALR,%yr_A%)        $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 150. - 80. ) / p_dailyWgtIncrease(RS,CALR,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (80. + 150.) / 2.
                st.p_dailyWgtIncrease[(r, a)] = (150. - 80.) / 125.
                st.p_fatngDays[(r, a)] = (150. - 80.) / st.p_dailyWgtIncrease[(r, a)]


def p_dataCopy_curRows_CALR_80_150(st: ManState) -> None:
    r"""Raised calves, 80 to 150 kg: P2O5 and K2O at the tail, added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 605-610):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            =  p_dataCopy(RS,CALR,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_80_150(st: ManState) -> None:
    r"""Raised calves, 80 to 150 kg: the crude-protein requirement, added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 612-617):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
           p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
              =  p_crprReq(RS,CALR,A,%yr%)
               + ( - 0.00039 * p_meanLiveWgt(RS,CALR,%yr_A%)
                   + 0.000628 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. - 0.0193 ) * p_fatngDays(RS,CALR,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_lt150(
                        st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.p_fatngDays[(r, a)])


def p_fatngDays_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase (150 kg to the bulls' or heifers' start weight): its days, the member state's
    raising days less the first two phases', scaled by the region's stocking rate over the member state's, within
    CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 654-657):

          p_fatngDays(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
            = MAX(p_reqfcnlim(CALR,"DAYS","lo")-49-125,
                  MIN(p_reqfcnlim(CALR,"DAYS","up")-49-125,
                  SUM(R_RAGG(RS,MS),(p_dataCopy(MS,CALR,"DAYS",%yr%)-49-125)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)));

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                ms = st.ms_sum(r, lambda m: (st.dc(m, a, "DAYS") - 49 - 125) / st.p_stockingRate[m])
                st.p_fatngDays[(r, a)] = max(st.lim(a, "DAYS", "lo") - 49 - 125,
                                             min(st.lim(a, "DAYS", "up") - 49 - 125, ms * st.p_stockingRate.get(r, 0.0)))


def p_dailyWgtIncrease_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the daily gain from 150 kg to the start weight of the bulls (male calves) or the
    heifers (female calves).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 659-662):

          p_dailyWgtIncrease(RS,"CAMR",%yr_A%) $ (%p_condition%(RS,"CAMR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAMR",%yr_A%))
            = (p_startWgt("BULF") - 150) / p_fatngDays(RS,"CAMR",%yr_A%) ;
          p_dailyWgtIncrease(RS,"CAFR",%yr_A%) $ (%p_condition%(RS,"CAFR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAFR",%yr_A%))
            = (p_startWgt("HEIF") - 150) / p_fatngDays(RS,"CAFR",%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a, to in (("CAMR", "BULF"), ("CAFR", "HEIF")):
            if st.LEVL(r, a) and st.p_fatngDays.get((r, a)):
                st.p_dailyWgtIncrease[(r, a)] = (st.p_startWgt[to] - 150) / st.p_fatngDays[(r, a)]


def p_meanLiveWgt_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the mean live weight, 150 kg plus half the phase's gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 664-668):

        * --- average live weight

          p_meanLiveWgt(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
        *             increase up to mid point of raising period:
            = 150. + (p_dailyWgtIncrease(RS,CALR,%yr_A%) * p_fatngDays(RS,CALR,%yr_A%)) / 2. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = 150. + (st.p_dailyWgtIncrease.get((r, a), 0.0) * st.p_fatngDays[(r, a)]) / 2.


def p_dataCopy_curRows_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: P2O5 and K2O at the tail, added to the first two phases'.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 670-675):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
                    p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
                      =  p_dataCopy(RS,CALR,curRows,%yr%)
                       + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.dc(r, a, row) + st.p_NutContManureKgM3[("CATTLE", row)]
                                                  * st.p_fatngDays[(r, a)] * st.p_meanLiveWgt[(r, a)])


def p_crprReq_CALR_last(st: ManState) -> None:
    r"""Raised calves, the last phase: the crude-protein requirement, added to the first two phases'.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 677-682):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%)*p_technFact(RS,CALR,"LEVL",A) )
            =  p_crprReq(RS,CALR,A,%yr%)
             + (  0.00109 * p_meanLiveWgt(RS,CALR,%yr_A%)
                + 0.00022 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. + 0.2027 )  * p_fatngDays(RS,CALR,%yr_A%)  ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = st.p_crprReq.get((r, a, t), 0.0) + _crpr_growth_gt150(
                        st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease.get((r, a), 0.0), st.p_fatngDays[(r, a)])


# ------------------------------------------------------------------ (5) beef fattening
def p_dailyWgtIncrease_BULF(st: ManState) -> None:
    r"""Fattened bulls: the daily gain (kg), the member state's scaled by the region's stocking rate over the member
    state's, within CAPRI's limits; at most 0.4 kg plus 1.6 g per kg of final live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 732-745):

          p_dailyWgtIncrease(RS,BULF,%yr_A%) $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(BULF,"DAILY","up"),
                  MAX(p_reqfcnlim(BULF,"DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,BULF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

        * --- prevent high daily increase for beef with low final weights

          p_dailyWgtIncrease(RS,BULF,%yr_A%) $ ( %p_condition%(RS,BULF,"LEVL",%yr_A%) $ p_dataCopy(RS,BULF,"BEEF",%yr%)
                                               $ p_dailyWgtIncrease(RS,BULF,%yr_A%) )
            = MIN(p_dailyWgtIncrease(RS,BULF,%yr_A%),
        *pw       Permits 0.4+500*.0016= 1.2 kg per day at 500 kg, ie more than the old specification (=>1 kg)
        *         However the absolute upper limit has also been increased (1.4kg=>1.5kg) to reflect efficiency gains in the last decade
                  0.4 + ( p_dataCopy(RS,BULF,"BEEF",%yr%) / p_carcassShare(BULF) ) * 0.0016) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000
        for a in BULF:
            if st.LEVL(r, a) and st.dc(r, a, "BEEF") and st.p_dailyWgtIncrease.get((r, a)):
                st.p_dailyWgtIncrease[(r, a)] = min(st.p_dailyWgtIncrease[(r, a)],
                                                    0.4 + (st.dc(r, a, "BEEF") / st.p_carcassShare[a]) * 0.0016)


def p_fatngDays_BULF(st: ManState) -> None:
    r"""Fattened bulls: the fattening days, the gain from the 335 kg start to the final live weight at the daily gain,
    within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 749-758):

          p_fatngDays(RS,BULF,%yr_A%) $  %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *       an upper final age of 3.5 years is assumed in very extensive settings
            =  MIN(p_reqfcnlim(BULF,"DAYS","up"),
                   MAX(p_reqfcnlim(BULF,"DAYS","lo"),
                      ( p_dataCopy(RS,BULF,"BEEF",%yr%)
        $iftheni %req% ==on
                      *(p_technFact(RS,BULF,"BEEF",A)+1.)
        $endif
                      / p_carcassShare(BULF) - p_startWgt(BULF))
                      / p_dailyWgtIncrease(RS,BULF,%yr_A%) ) )  ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def p_meanLiveWgt_BULF(st: ManState) -> None:
    r"""Fattened bulls: the mean live weight, the start weight plus half the gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 760-761):

          p_meanLiveWgt(RS,BULF,%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = p_startWgt(BULF) + (p_fatngDays(RS,BULF,%yr_A%) * p_dailyWgtIncrease(RS,BULF,%yr_A%)) / 2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (st.p_startWgt[a]
                                            + (st.p_fatngDays[(r, a)] * st.p_dailyWgtIncrease[(r, a)]) / 2.)


def p_dataCopy_curRows_BULF(st: ManState) -> None:
    r"""Fattened bulls: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 763-767):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,BULF,curRows,%yr%) $ p_dataCopy(RS,BULF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,BULF,%yr_A%) * p_meanLiveWgt(RS,BULF,%yr_A%);
        *

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_dataCopy_DRMN_BULF(st: ManState) -> None:
    r"""Fattened bulls: the minimum dry matter of the fattening, by the daily gain's class (CAPRI working paper 97-12).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 772-781):

          p_dataCopy(RS,BULF,"DRMN",%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *
            =   ( ( ( 0.029 -  0.00001914 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%))  * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

                + (( ( 0.028 -  0.00001678 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%))
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

                + (( ( 0.0288 - 0.0000231  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.p_fatngDays[(r, a)]
                st.p_dataCopy[(r, a, "DRMN")] = (
                    (((0.029 - 0.00001914 * w) * w) * n) * (d <= 1.1)
                    + (((0.028 - 0.00001678 * w) * w) * n) * (1.1 < d < 1.3)
                    + (((0.0288 - 0.0000231 * w) * w) * n) * (d >= 1.3))


def p_crprReq_BULF(st: ManState) -> None:
    r"""Fattened bulls: the crude-protein requirement, a share of the minimum dry matter by the daily gain's class.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 783-792):

          p_crprReq(RS,BULF,A,%yr%) $  (p_dataCopy(RS,BULF,"LEVL",%yr%)*p_technFact(RS,BULF,"LEVL",A))
        *
            =  ((( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

               + ((( 0.1657 - 0.0001214  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

               + ((( 0.1493 - 0.00004405 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            if st.LEVL(r, a):
                w, d, dm = st.p_meanLiveWgt[(r, a)], st.p_dailyWgtIncrease[(r, a)], st.dc(r, a, "DRMN")
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = (((0.1602 - 0.0001228 * w) * dm) * (d <= 1.1)
                                               + ((0.1657 - 0.0001214 * w) * dm) * (1.1 < d < 1.3)
                                               + ((0.1493 - 0.00004405 * w) * dm) * (d >= 1.3))


# ------------------------------------------------------------------ (6) heifers fattening
def p_dailyWgtIncrease_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the daily gain (kg), as the bulls' (without the final-weight cap).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 835-839):

          p_dailyWgtIncrease(RS,HEIF,%yr_A%)  $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(HEIF,"DAILY","up"),
                  MAX(p_reqfcnlim(HEIF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,HEIF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_dailyWgtIncrease[(r, a)] = min(st.lim(a, "DAILY", "up"),
                                                    max(st.lim(a, "DAILY", "lo"), _scaled_ms_daily(st, r, a))) / 1000


def p_fatngDays_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the fattening days from the 300 kg start, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 843-852):

          p_fatngDays(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
        *       an upper final age of 3 years is implied (otherwise: reclassification to cows)
            =  MIN(p_reqfcnlim(HEIF,"DAYS","up"),
                   MAX(p_reqfcnlim(HEIF,"DAYS","lo"),
                      ( p_dataCopy(RS,HEIF,"BEEF",%yr%)
        $iftheni %req% ==on
                      *(p_technFact(RS,HEIF,"BEEF",A)+1.)
        $endif
                      / p_carcassShare(HEIF) - p_startWgt(HEIF))
                      / p_dailyWgtIncrease(RS,HEIF,%yr_A%) ) )  ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_fatngDays[(r, a)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") / st.p_carcassShare[a] - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a)]))


def p_meanLiveWgt_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 854-855):

          p_meanLiveWgt(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( p_startWgt(HEIF) + (p_fatngDays(RS,HEIF,%yr_A%) * p_dailyWgtIncrease(RS,HEIF,%yr_A%)) / 2. ) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                st.p_meanLiveWgt[(r, a)] = (st.p_startWgt[a]
                                            + (st.p_fatngDays[(r, a)] * st.p_dailyWgtIncrease[(r, a)]) / 2.)


def p_dataCopy_curRows_HEIF(st: ManState) -> None:
    r"""Fattened heifers: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 858-862):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,HEIF,curRows,%yr%) $ p_dataCopy(RS,HEIF,"LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,HEIF,%yr_A%) * p_meanLiveWgt(RS,HEIF,%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                for row in curRows:
                    st.p_dataCopy[(r, a, row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, a)]
                                                  * st.p_meanLiveWgt[(r, a)])


def p_dataCopy_DRMN_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the minimum dry matter of the fattening.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 866-867):

          p_dataCopy(RS,HEIF,"DRMN",%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( ( 0.029 - 0.00001914 * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_meanLiveWgt(RS,HEIF,%yr_A%)) * p_fatngDays(RS,HEIF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                w = st.p_meanLiveWgt[(r, a)]
                st.p_dataCopy[(r, a, "DRMN")] = ((0.029 - 0.00001914 * w) * w) * st.p_fatngDays[(r, a)]


def p_crprReq_HEIF(st: ManState) -> None:
    r"""Fattened heifers: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 869-870):

          p_crprReq(RS,HEIF,A,%yr%) $ (p_dataCopy(RS,HEIF,"LEVL",%yr%)*p_technFact(RS,HEIF,"LEVL",A))
            = ( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_dataCopy(RS,HEIF,"DRMN",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            if st.LEVL(r, a):
                for t in st.techs(r, a):
                    st.p_crprReq[(r, a, t)] = (0.1602 - 0.0001228 * st.p_meanLiveWgt[(r, a)]) * st.dc(r, a, "DRMN")


# ------------------------------------------------------------------ (7) heifers raising
def p_meanLiveWgt_HEIR(st: ManState) -> None:
    r"""Raised heifers: the mean live weight, halfway from the 300 kg start to the adult female's weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 915-918):

          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
            = (( p_startWgt("HEIR") + p_femWgt(RS,%yr_A%) ) / 2 );
          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ (%p_condition%(RS,"HEIR","LEVL",%yr_A%) $ (NOT p_meanLiveWgt(RS,"HEIR",%yr_A%)))
            = (p_startWgt("HEIR") + 575.)/2;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            st.p_meanLiveWgt[(r, "HEIR")] = ((st.p_startWgt["HEIR"] + st.p_femWgt[r]) / 2)
            if not st.p_meanLiveWgt[(r, "HEIR")]:
                st.p_meanLiveWgt[(r, "HEIR")] = (st.p_startWgt["HEIR"] + 575.) / 2


def p_fatngDays_HEIR(st: ManState) -> None:
    r"""Raised heifers: the raising days, the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 920-924):

          p_fatngDays(RS,"HEIR",%yr_A%)  $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
        *       Max days are 2 years (heifers reclassified as cows), min days are 10 months or a calving age of 12+10=22 months
            =  MIN(p_reqfcnlim("HEIR","DAYS","up"),
                   MAX(p_reqfcnlim("HEIR","DAYS","lo"),
                       SUM(R_RAGG(RS,MS),p_dataCopy(MS,"HEIR","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            st.p_fatngDays[(r, "HEIR")] = min(st.lim("HEIR", "DAYS", "up"), max(st.lim("HEIR", "DAYS", "lo"),
                                                                               st.ms_sum(r, lambda m: st.dc(m, "HEIR", "DAYS"))))


def p_dailyWgtIncrease_HEIR(st: ManState) -> None:
    r"""Raised heifers: the daily gain (kg), from the start to the mean weight over the raising days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 926-927):

          p_dailyWgtIncrease(RS,"HEIR",%yr_A%) $ p_fatngDays(RS,"HEIR",%yr_A%)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)  - p_startWgt("HEIR") ) / p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.p_fatngDays.get((r, "HEIR")):
            st.p_dailyWgtIncrease[(r, "HEIR")] = ((st.p_meanLiveWgt.get((r, "HEIR"), 0.0) - st.p_startWgt["HEIR"])
                                                  / st.p_fatngDays[(r, "HEIR")])


def p_dataCopy_curRows_HEIR(st: ManState) -> None:
    r"""Raised heifers: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 929-933):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HEIR",curRows,%yr%) $ p_dataCopy(RS,"HEIR","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"HEIR",%yr_A%) * p_meanLiveWgt(RS,"HEIR",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            for row in curRows:
                st.p_dataCopy[(r, "HEIR", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, "HEIR")]
                                                   * st.p_meanLiveWgt[(r, "HEIR")])


def p_crprReq_HEIR(st: ManState) -> None:
    r"""Raised heifers: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 935-939):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"HEIR",A,%yr%) $ (p_dataCopy(RS,"HEIR","LEVL",%yr%)*p_technFact(RS,"HEIR","LEVL",A))
            = ( 0.00127 * p_meanLiveWgt(RS,"HEIR",%yr_A%) + 0.00024 * p_dailyWgtIncrease(RS,"HEIR",%yr_A%) * 1000. + 0.1273 )
             * p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HEIR"):
            for t in st.techs(r, "HEIR"):
                st.p_crprReq[(r, "HEIR", t)] = ((0.00127 * st.p_meanLiveWgt[(r, "HEIR")]
                                                 + 0.00024 * st.p_dailyWgtIncrease.get((r, "HEIR"), 0.0) * 1000. + 0.1273)
                                                * st.p_fatngDays[(r, "HEIR")])


# ------------------------------------------------------------------ (8) sows
def p_dataCopy_curRows_SOWS(st: ManState) -> None:
    r"""Sows: P2O5 and K2O at the tail, the sow's (200 kg a year) and its piglets' (10 kg over 42 days) manure.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 986-996):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SOWS",curRows,%yr%) $ p_dataCopy(RS,"SOWS","LEVL",%yr%)
            = p_NutContManureKgM3("SOWS",curRows) * ( 365. * 200.
        *      10 kg liveweight of piglet...
             + 10.*0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%)
        *      ... over 42 days
        *pw    NOTE: might be improved using p_dataCopy(RS,"PIGF","YDAYS",%yr%), but this varies from 44 to 125 days.
        *      => revision postponed until there is time for thorough testing
             * 42);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SOWS"):
            for row in curRows:
                st.p_dataCopy[(r, "SOWS", row)] = st.p_NutContManureKgM3[("SOWS", row)] * (
                    365. * 200. + 10. * 0.001 * st.dc(r, "SOWS", "YPIG") * 42)


def p_crprReq_SOWS(st: ManState) -> None:
    r"""Sows: the crude-protein requirement, the sow's and 5.7 kg per piglet.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 998-1001):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"SOWS",A,%yr%) $ (p_dataCopy(RS,"SOWS","LEVL",%yr%)*p_technFact(RS,"SOWS","LEVL",A))
            = 101.71 + 46.5 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.)* 5.7;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SOWS"):
            for t in st.techs(r, "SOWS"):
                st.p_crprReq[(r, "SOWS", t)] = (101.71 + 46.5 + 0.001 * st.dc(r, "SOWS", "YPIG")
                                                * (st.tf(r, "SOWS", "YPIG", t) + 1.) * 5.7)


# ------------------------------------------------------------------ (9) pig fattening
def p_finalLiveWgt_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the final live weight, the carcass over its share, at least just above the lightest weight
    class of CAPRI's requirement tables (CAPRI's fix for tiny herds).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1038-1058):

          p_finalLiveWgt(RS,"PIGF",%yr_A%)  $ %p_condition%(RS,"PIGF","LEVL",%yr_A%)
            = (p_dataCopy(RS,"PIGF","PORK",%yr%)
        $iftheni %req% ==on
             *(p_technFact(RS,"PIGF","PORK",A)+1.)
        $endif
             / p_carcassShare("PIGF")) ;
        *
        * --- the version before 2013-3-10 may be reactivated as follows:
        *$setlocal SwitchLiveWgt 115
        *     after problems detected in DK (MK/PW 2013-3-10) modify setting to use high final weight function regardless of statistical weight
        $setlocal SwitchLiveWgt 0

        *     -- fix for special case where slaughter weights of PIGF may be below the smallest weight considered in req fnc
        *        (encountered in TUR with tiny LEVL): smin(porkFinWgtHi, p_pigsReqHighWgt(porkFinWgtHi,"XALW")) > p_finalLiveWgt(RS,"PIGF",%yr_A%)
        *        This gives p_fatngDays = -inf and zero requirements. To counteract this, we simply raise p_finalLiveWgt, if needed
        *        contrary to the data, to barely exceed the minimum p_pigsReqHighWgt(porkFinWgtHi,"XALW") (about 20.5 kg)

          p_finalLiveWgt(RS,"PIGF",%yr_A%)
            = max(p_finalLiveWgt(RS,"PIGF",%yr_A%),
                  SMIN(porkFinWgtLo $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF")), p_pigsReqLowWgt(porkFinWgtLo,"XALW"))+.1,
                  SMIN(porkFinWgtHi $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF")), p_pigsReqHighWgt(porkFinWgtHi,"XALW"))+.1);

    Without CAPRI's tables (dat/feed/porkreq.gms) the fattened pigs are left out: nothing is assigned, and
    ManState.not_computed names them. Departures from CAPRI: none."""
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        st.not_computed.add("PIGF")
        return
    start = st.p_startWgt["PIGF"]
    lo = min((v for (c, k), v in st.p_pigsReqLowWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    hi = min((v for (c, k), v in st.p_pigsReqHighWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    for r in st.RS:
        if st.LEVL(r, "PIGF"):
            st.p_finalLiveWgt[(r, "PIGF")] = st.dc(r, "PIGF", "PORK") / st.p_carcassShare["PIGF"]
        st.p_finalLiveWgt[(r, "PIGF")] = max(st.p_finalLiveWgt.get((r, "PIGF"), 0.0), lo, hi)


#: CAPRI's switch between its low and high final-weight requirement tables (l. 1048: 0, the high table always)
SwitchLiveWgt = 0


def _pig_classes(st: ManState, table: dict, final: float):
    """The weight classes of a pig requirement table with start weight < XALW < the final live weight."""
    start = st.p_startWgt["PIGF"]
    return [c for (c, k), v in table.items() if k == "XALW" and start < v < final]


def p_fatngDays_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the fattening days, those of the heaviest weight class below the final live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1061-1067):

          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtLo $ (     (p_pigsReqLowWgt(porkFinWgtLo,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF"))   ), p_pigsReqLowWgt(porkFinWgtLo,"XDUF"));
        *
          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) GE  %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtHi $ (     (p_pigsReqHighWgt(porkFinWgtHi,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF"))  ), p_pigsReqHighWgt(porkFinWgtHi,"XDUF"));

    Departures from CAPRI: none."""
    for r in st.RS:
        f = st.p_finalLiveWgt.get((r, "PIGF"), 0.0)
        if not f:
            continue
        table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
        st.p_fatngDays[(r, "PIGF")] = max((table[(c, "XDUF")] for c in _pig_classes(st, table, f)), default=0.0)


def p_dataCopy_curRows_PIGF(st: ManState) -> None:
    r"""Fattened pigs: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1069-1074):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"PIGF",curRows,%yr%) $ p_dataCopy(RS,"PIGF","LEVL",%yr%)
            = p_NutContManureKgM3("PIGF",curRows) * p_fatngDays(RS,"PIGF",%yr_A%)
                            * (p_finalLiveWgt(RS,"PIGF",%yr_A%)-p_startWgt("PIGF")) * 0.5;
        $endif

    Departures from CAPRI: none."""
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        return
    for r in st.RS:
        if st.LEVL(r, "PIGF"):
            for row in curRows:
                st.p_dataCopy[(r, "PIGF", row)] = (st.p_NutContManureKgM3[("PIGF", row)] * st.p_fatngDays.get((r, "PIGF"), 0.0)
                                                   * (st.p_finalLiveWgt[(r, "PIGF")] - st.p_startWgt["PIGF"]) * 0.5)


def p_crprReq_PIGF(st: ManState) -> None:
    r"""Fattened pigs: the crude-protein requirement, the sum over the weight classes up to the final live weight, plus
    15%.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1076-1092):

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"PIGF",A,%yr%) $ ( (p_dataCopy(RS,"PIGF","LEVL",%yr%)*p_technFact(RS,"PIGF","LEVL",A))
                                        $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%)
                                        $  p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SUM(porkFinWgtLo $ ( (p_pigsReqLowWgt(porkFinWgtLo,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW")>p_startWgt("PIGF")) ),      p_pigsReqLowWgt(porkFinWgtLo,"CRPR"));
        *
          p_crprReq(RS,"PIGF",A,%yr%) $ ( (p_dataCopy(RS,"PIGF","LEVL",%yr%)*p_technFact(RS,"PIGF","LEVL",A))
                                        $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) GE %SwitchLiveWgt%)
                                        $  p_finalLiveWgt(RS,"PIGF",%yr_A%) )
             = SUM(porkFinWgtHi $ ( (p_pigsReqHighWgt(porkFinWgtHi,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                  $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW")>p_startWgt("PIGF")) ),    p_pigsReqHighWgt(porkFinWgtHi,"CRPR"));
        *
        * --- unmotivated correction of Italian table from before 2007. Unclear if this is still needed, beneficial or harmful.

          p_crprReq(RS,"PIGF",A,%yr%) $ p_crprReq(RS,"PIGF",A,%yr%) = p_crprReq(RS,"PIGF",A,%yr%) * 1.15;

    Departures from CAPRI: none."""
    for r in st.RS:
        f = st.p_finalLiveWgt.get((r, "PIGF"), 0.0)
        if not (st.LEVL(r, "PIGF") and f):
            continue
        table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
        for t in st.techs(r, "PIGF"):
            st.p_crprReq[(r, "PIGF", t)] = sum(table[(c, "CRPR")] for c in _pig_classes(st, table, f))
    for k in [k for k in st.p_crprReq if k[1] == "PIGF" and st.p_crprReq[k]]:
        st.p_crprReq[k] = st.p_crprReq[k] * 1.15


# ------------------------------------------------------------------ (10) hens
def p_meanLiveWgt_HENS(st: ManState) -> None:
    r"""Laying hens: the mean live weight, 1.9 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1137):

          p_meanLiveWgt(RS,"HENS",%yr_A%) $ %p_condition%(RS,"HENS","LEVL",%yr_A%)  = 1.9;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            st.p_meanLiveWgt[(r, "HENS")] = 1.9


def p_dataCopy_curRows_HENS(st: ManState) -> None:
    r"""Laying hens: P2O5 and K2O at the tail, per 1000 hens (CAPRI's unit of the activity).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1139-1143):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HENS",curRows,%yr%) $ p_dataCopy(RS,"HENS","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_meanLiveWgt(RS,"HENS",%yr_A%) * 365. * 1000.;
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            for row in curRows:
                st.p_dataCopy[(r, "HENS", row)] = (st.p_NutContManureKgM3[("POULTRY", row)] * st.p_meanLiveWgt[(r, "HENS")]
                                                   * 365. * 1000.)


def p_crprReq_HENS(st: ManState) -> None:
    r"""Laying hens: the crude-protein requirement, maintenance and the eggs (57 g each).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1145-1148):

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"HENS",A,"ENMC") / 11.1 * 0.14 ;
          p_crprReq(RS,"HENS",A,%yr%) $ (p_dataCopy(RS,"HENS","LEVL",%yr%)*p_technFact(RS,"HENS","LEVL",A))
            = ( 0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75 + 0.57 * (p_dataCopy(RS,"HENS","EGGS",%yr%)/57.)/365.)*365.*1000./11.1*0.14;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "HENS"):
            for t in st.techs(r, "HENS"):
                st.p_crprReq[(r, "HENS", t)] = ((0.46 * st.p_meanLiveWgt[(r, "HENS")] ** 0.75
                                                 + 0.57 * (st.dc(r, "HENS", "EGGS") / 57.) / 365.) * 365. * 1000. / 11.1 * 0.14)


# ------------------------------------------------------------------ (11) poultry fattening
def p_meanLiveWgt_POUF(st: ManState) -> None:
    r"""Poultry fattening: the mean live weight, half the final weight (the meat over its share), at least 250 g.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1186-1194):

          p_meanLiveWgt(RS,"POUF",%yr_A%) $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
            = MAX(  p_dataCopy(RS,"POUF","POUM",%yr%)*0.001
        $iftheni %req% ==on
                  *(p_technFact(RS,"POUF","POUM",A)+1.)
        $endif
        *           average wgt = final wgt * 0.5, as iniital wgt is near zero
                  / p_carcassShare("POUF") * 0.5,
        *        ... but at least 250g
                 0.25) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            st.p_meanLiveWgt[(r, "POUF")] = max(st.dc(r, "POUF", "POUM") * 0.001 / st.p_carcassShare["POUF"] * 0.5, 0.25)


def p_animProdDays_POUF(st: ManState) -> None:
    r"""Poultry fattening: the process days, the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1196-1200):

        *        Max days are about 150 days (turkeys including some empty days), min days are about 30 days (broilers)
          p_animProdDays(RS,"POUF",%yr_A% %addtimedim%)  $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
                = MIN(p_reqfcnlim("POUF","DAYS","up"),
                      MAX(p_reqfcnlim("POUF","DAYS","lo"),
                          SUM(R_RAGG(RS,MS),p_dataCopy(MS,"POUF","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            st.p_animProdDays[(r, "POUF")] = min(st.lim("POUF", "DAYS", "up"), max(st.lim("POUF", "DAYS", "lo"),
                                                                                   st.ms_sum(r, lambda m: st.dc(m, "POUF", "DAYS"))))


def p_dataCopy_curRows_POUF(st: ManState) -> None:
    r"""Poultry fattening: P2O5 and K2O at the tail, per 1000 places.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1202-1206):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"POUF",curRows,%yr%) $ p_dataCopy(RS,"POUF","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_animProdDays(RS,"POUF",%yr_A% %addtimedim%) * p_meanLiveWgt(RS,"POUF",%yr_A%) * 1000.;
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            for row in curRows:
                st.p_dataCopy[(r, "POUF", row)] = (st.p_NutContManureKgM3[("POULTRY", row)] * st.p_animProdDays[(r, "POUF")]
                                                   * st.p_meanLiveWgt[(r, "POUF")] * 1000.)


def p_crprReq_POUF(st: ManState) -> None:
    r"""Poultry fattening: the crude-protein requirement, the dry matter intake of the fattening times a crude-protein
    content from 23% (500 g chicks) down to 19% (1.9 kg).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1208-1217):

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"POUF",A,"DRMA") * (0.23 - 0.04 * MAX(0,p_meanLiveWgt(RS,"POUF",%yr_A%)-0.50) ) / 0.87;
          p_crprReq(RS,"POUF",A,%yr%) $ (p_dataCopy(RS,"POUF","LEVL",%yr%)*p_technFact(RS,"POUF","LEVL",A))
        *         dry matter need according to paper 97-12
        *         (matches rule of thumb that intake is about twice the final weight)
            =  (1.6463 * ((p_meanLiveWgt(RS,"POUF",%yr_A%)*2.0)**1.3023) * 0.87 * 1000)
        *          ... which are finally linked to CRPR:
        *              starting with a CRPR content of 23 % for 500 gr weighting chicks, dropping to 19% for 1.9 kg final weight
        *             (replaces the assumption of 19% from paper 97-12)
             * (0.23 - 0.04 * MAX(0,p_meanLiveWgt(RS,"POUF",%yr_A%)-0.50) ) / 0.87;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "POUF"):
            w = st.p_meanLiveWgt[(r, "POUF")]
            for t in st.techs(r, "POUF"):
                st.p_crprReq[(r, "POUF", t)] = ((1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
                                                * (0.23 - 0.04 * max(0, w - 0.50)) / 0.87)


# ------------------------------------------------------------------ (12) sheep and goats for milk
def p_sharGoatHerd(st: ManState) -> None:
    r"""Sheep and goats for milk: the goats' share of the member state's sheep and goat herds (10% where unknown).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1250-1255):

          p_sharGoatHerd(RS,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)
                               /(p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)))
                 $      SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%))
             +0.1
                 $ (NOT SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)));

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            tot = st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))
            st.p_sharGoatHerd[r] = (st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD")
                                              / (st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))) if tot else 0.0) \
                + (0.1 if not tot else 0.0)


def p_meanLiveWgt_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the ewes' (55 kg) and goats' (60 kg) mean live weights, and the activity's, weighted
    by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1259-1264):

          p_meanLiveWgt(RS,"EWES",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 55. ;
          p_meanLiveWgt(RS,"GOAT",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 60. ;
        *
          p_meanLiveWgt(RS,"SHGM",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%)
            = p_meanLiveWgt(RS,"EWES",%yr_A%) * (1-p_sharGoatHerd(RS,%yr%))
             +p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_sharGoatHerd(RS,%yr%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            st.p_meanLiveWgt[(r, "EWES")] = 55.
            st.p_meanLiveWgt[(r, "GOAT")] = 60.
            s = st.p_sharGoatHerd.get(r, 0.0)
            st.p_meanLiveWgt[(r, "SHGM")] = st.p_meanLiveWgt[(r, "EWES")] * (1 - s) + st.p_meanLiveWgt[(r, "GOAT")] * s


def p_milkPerDay_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the milk per milking day (170 days), sold and fed.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1268-1272):

           p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) =
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMI",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMI",%yr%) / 170. +
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMF",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMF",%yr%) / 170.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            st.p_milkPerDay[(r, "SHGM")] = st.dc(r, "SHGM", "SGMI") / 170. + st.dc(r, "SHGM", "SGMF") / 170.


def p_dataCopy_curRows_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: P2O5 and K2O at the tail, the cattle manure per kg of live weight and day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1274-1278):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGM",curRows,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * 365. * p_meanLiveWgt(RS,"SHGM",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            for row in curRows:
                st.p_dataCopy[(r, "SHGM", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * 365.
                                                   * st.p_meanLiveWgt[(r, "SHGM")])


def p_crprReq_EWES(st: ManState) -> None:
    r"""Sheep and goats for milk: the ewes' crude-protein requirement, maintenance (135 days), milking (170 days) and
    the last mating period (60 days, g).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1283-1289):

          p_crprReq(RS,"EWES",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
            =   ( 0.026 + 0.0014 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *     -- for milk production
              + ( 0.0634 + 0.0012 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.0895 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( ( 2.22 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 19.88) * 1.35 ) * 60. / 1000. ;

    In this project's notation, as GAMS's precedence reads it: only the last period's term is divided by 1000.
    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            w, m = st.p_meanLiveWgt[(r, "EWES")], st.p_milkPerDay[(r, "SHGM")]
            for t in st.techs(r, "SHGM"):
                st.p_crprReq[(r, "EWES", t)] = ((0.026 + 0.0014 * w) * 135.
                                                + (0.0634 + 0.0012 * w + 0.0895 * m) * 170.
                                                + ((2.22 * w - 19.88) * 1.35) * 60. / 1000.)


def p_crprReq_GOAT(st: ManState) -> None:
    r"""Sheep and goats for milk: the goats' crude-protein requirement (g, over 1000).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1292-1299):

          p_crprReq(RS,"GOAT",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
        *        NOTE: the maintenance component of phases (1) + (2) is aggregated for GOAT: 135+170=305 days
            = ( ( 12.66 + 0.8 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *     -- for milk production
              + ( 61. * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( 1.425 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 14.666) * 60. ) / 1000. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            w, m = st.p_meanLiveWgt[(r, "GOAT")], st.p_milkPerDay[(r, "SHGM")]
            for t in st.techs(r, "SHGM"):
                st.p_crprReq[(r, "GOAT", t)] = ((12.66 + 0.8 * w) * 305. + (61. * m) * 170.
                                                + (1.425 * w + 14.666) * 60.) / 1000.


def p_crprReq_SHGM(st: ManState) -> None:
    r"""Sheep and goats for milk: the activity's crude-protein requirement, the goats' and ewes' by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1301-1304):

          p_crprReq(RS,"SHGM",A,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            =   (  p_crprReq(RS,"GOAT",A,%yr%) * p_sharGoatHerd(RS,%yr%)
                 + p_crprReq(RS,"EWES",A,%yr%) * (1-p_sharGoatHerd(RS,%yr%)))
                                        ;

    Departures from CAPRI: none (over CAPRI's technologies with an ewe's or goat's requirement)."""
    for r in st.RS:
        if st.LEVL(r, "SHGM"):
            s = st.p_sharGoatHerd.get(r, 0.0)
            for t in {k[2] for k in st.p_crprReq if k[0] == r and k[1] in ("EWES", "GOAT")}:
                st.p_crprReq[(r, "SHGM", t)] = (st.p_crprReq.get((r, "GOAT", t), 0.0) * s
                                                + st.p_crprReq.get((r, "EWES", t), 0.0) * (1 - s))


# ------------------------------------------------------------------ (13) sheep and goats fattening
def p_dailyWgtIncrease_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the daily gain (g), the member state's, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1407-1410):

          p_dailyWgtIncrease(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(p_reqfcnlim("SHGF","DAILY","up"),
                  MAX(p_reqfcnlim("SHGF","DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAILY",%yr%)))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_dailyWgtIncrease[(r, "SHGF")] = min(st.lim("SHGF", "DAILY", "up"), max(
                st.lim("SHGF", "DAILY", "lo"), st.ms_sum(r, lambda m: st.dc(m, "SHGF", "DAILY"))))


def p_fatngDays_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the fattening days, the final live weight (the carcass over its share) at the daily
    gain, between 10 and 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1414-1416):

          p_fatngDays(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(365. , MAX(10. ,( p_dataCopy(RS,"SHGF","SGMT",%yr%)/ p_carcassShare("SHGF") )
                                 /(p_dailyWgtIncrease(RS,"SHGF",%yr_A%)/1000.))) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_fatngDays[(r, "SHGF")] = min(365., max(10., (st.dc(r, "SHGF", "SGMT") / st.p_carcassShare["SHGF"])
                                                        / (st.p_dailyWgtIncrease[(r, "SHGF")] / 1000.)))


def p_meanLiveWgt_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the mean live weight, half the final weight (carcass between 8 and 25 kg).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1420-1422):

          p_meanLiveWgt(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
        *    Bounds as in coco1_anim:
            = MAX(8.,MIN(25.,p_dataCopy(RS,"SHGF","SGMT",%yr%)))/p_carcassShare("SHGF")/2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            st.p_meanLiveWgt[(r, "SHGF")] = max(8., min(25., st.dc(r, "SHGF", "SGMT"))) / st.p_carcassShare["SHGF"] / 2.


def p_dataCopy_curRows_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: P2O5 and K2O at the tail.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1425-1429):

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGF",curRows,%yr%) $ p_dataCopy(RS,"SHGF","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"SHGF",%yr_A%) * p_meanLiveWgt(RS,"SHGF",%yr_A%);
        $endif

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            for row in curRows:
                st.p_dataCopy[(r, "SHGF", row)] = (st.p_NutContManureKgM3[("CATTLE", row)] * st.p_fatngDays[(r, "SHGF")]
                                                   * st.p_meanLiveWgt[(r, "SHGF")])


def p_crprReq_SHGF(st: ManState) -> None:
    r"""Sheep and goats fattening: the crude-protein requirement (g, over 1000).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1433-1435):

          p_crprReq(RS,"SHGF",A,%yr%) $ (p_dataCopy(RS,"SHGF","LEVL",%yr%)*p_technFact(RS,"SHGF","LEVL",A))
            = ( ( 21.778 + 0.33 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.258 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%))
               * 1.35 * p_fatngDays(RS,"SHGF",%yr_A%)) / 1000.;

    Departures from CAPRI: none."""
    for r in st.RS:
        if st.LEVL(r, "SHGF"):
            for t in st.techs(r, "SHGF"):
                st.p_crprReq[(r, "SHGF", t)] = ((21.778 + 0.33 * st.p_meanLiveWgt[(r, "SHGF")]
                                                 + 0.258 * st.p_dailyWgtIncrease[(r, "SHGF")])
                                                * 1.35 * st.p_fatngDays[(r, "SHGF")]) / 1000.


# ------------------------------------------------------------------ PART III: MANN, and the copy of MANP and MANK
def p_MANN_A(st: ManState) -> None:
    r"""The N at the tail per head and technology: the crude-protein requirement times CAPRI's correction factor, over 6
    kg of crude protein per kg N, less the N in the animal's products (DATA CRPR_EXPT, fert/calc_nexport.gms at the
    year, which PART III runs first: the caller's DATA), at least 0.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1824-1825):

          p_MANN_A(RS,AACT,A,%yr%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A) $ p_crprReq(RS,AACT,A,%yr%))
            = MAX(0,p_crprReq(RS,AACT,A,%yr%) * p_animExcrProtCorrFact(RS,AACT,A,%yr%) / 6.0 - DATA(RS,AACT,"CRPR_EXPT",%yr%));

    Departures from CAPRI: none."""
    st.p_MANN_A = {}
    for (r, a, t), c in st.p_crprReq.items():
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t) and c:
            st.p_MANN_A[(r, a, t)] = max(0, c * float(st.p_animExcrProtCorrFact.get((r, a, t), 0.0)) / 6.0
                                         - st.D(r, a, "CRPR_EXPT"))


def DATA_MANN(st: ManState) -> None:
    r"""The N at the tail per head: over CAPRI's technologies, by their shares.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1827-1828):

          DATA(RS,AACT,"MANN",%yr%) $ SUM(A,p_crprReq(RS,AACT,A,%yr%))
            = SUM(A, p_MANN_A(RS,AACT,A,%yr%)*p_technFact(RS,AACT,"LEVL",A));

    Departures from CAPRI: none."""
    acts = {(r, a) for (r, a, t), c in st.p_crprReq.items() if a not in ("EWES", "GOAT")}   # AACT: not the ewes, goats
    for r, a in acts:
        if sum(c for (rr, aa, t), c in st.p_crprReq.items() if rr == r and aa == a):
            st.DATA[(r, a, "MANN")] = sum(v * st.tf(r, a, "LEVL", t) for (rr, aa, t), v in st.p_MANN_A.items()
                                          if rr == r and aa == a)


def DATA_curRows(st: ManState) -> None:
    r"""P2O5 and K2O at the tail: copied to DATA from the functions' copy (CAPRI's exogenous method).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1836-1837):

          DATA(RS,AACT,curRows,%yr%)
            = p_dataCopy(RS,AACT,curRows,%yr%);

    Departures from CAPRI: only the animal activities' rows are copied (the copy's other rows are DATA's own)."""
    for (r, a, row), v in st.p_dataCopy.items():
        if row in curRows:
            st.DATA[(r, a, row)] = v


#: CAPRI's statement blocks of 'man' mode, in CAPRI's order (feed/req_or_man_fnc.gms PART I and PART III)
BLOCKS = (DATA_AGGR_YCOW, p_stockingRate, p_dataCopy_man,
          p_dataCopy_curRows_DCOW, p_milkFatCont, p_meanLiveWgt_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW,
          p_dataCopy_curRows_SCOW, p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_femWgt,
          p_dailyWgtIncrease_CALF, p_animProdDays_CALF,
          p_meanLiveWgt_CALF_light, p_fatngDays_CALF_light, p_dataCopy_curRows_CALF_light, p_crprReq_CALF_light,
          p_meanLiveWgt_CALF_heavy_b1, p_fatngDays_CALF_heavy_b1, p_dataCopy_curRows_CALF_heavy_b1,
          p_crprReq_CALF_heavy_b1,
          p_meanLiveWgt_CALF_heavy_b2, p_fatngDays_CALF_heavy_b2, p_dataCopy_curRows_CALF_heavy_b2,
          p_crprReq_CALF_heavy_b2,
          CALR_weaning, p_crprReq_CALR_weaning, CALR_80_150, p_dataCopy_curRows_CALR_80_150, p_crprReq_CALR_80_150,
          p_fatngDays_CALR_last, p_dailyWgtIncrease_CALR_last, p_meanLiveWgt_CALR_last, p_dataCopy_curRows_CALR_last,
          p_crprReq_CALR_last,
          p_dailyWgtIncrease_BULF, p_fatngDays_BULF, p_meanLiveWgt_BULF, p_dataCopy_curRows_BULF, p_dataCopy_DRMN_BULF,
          p_crprReq_BULF,
          p_dailyWgtIncrease_HEIF, p_fatngDays_HEIF, p_meanLiveWgt_HEIF, p_dataCopy_curRows_HEIF, p_dataCopy_DRMN_HEIF,
          p_crprReq_HEIF,
          p_meanLiveWgt_HEIR, p_fatngDays_HEIR, p_dailyWgtIncrease_HEIR, p_dataCopy_curRows_HEIR, p_crprReq_HEIR,
          p_dataCopy_curRows_SOWS, p_crprReq_SOWS,
          p_finalLiveWgt_PIGF, p_fatngDays_PIGF, p_dataCopy_curRows_PIGF, p_crprReq_PIGF,
          p_meanLiveWgt_HENS, p_dataCopy_curRows_HENS, p_crprReq_HENS,
          p_meanLiveWgt_POUF, p_animProdDays_POUF, p_dataCopy_curRows_POUF, p_crprReq_POUF,
          p_sharGoatHerd, p_meanLiveWgt_SHGM, p_milkPerDay_SHGM, p_dataCopy_curRows_SHGM, p_crprReq_EWES,
          p_crprReq_GOAT, p_crprReq_SHGM,
          p_dailyWgtIncrease_SHGF, p_fatngDays_SHGF, p_meanLiveWgt_SHGF, p_dataCopy_curRows_SHGF, p_crprReq_SHGF,
          p_MANN_A, DATA_MANN, DATA_curRows)


def req_or_man_fnc_man(st: ManState) -> ManState:
    r"""CAPRI's 'man' call of feed/req_or_man_fnc.gms at "Y": every block of BLOCKS in order, on st (changed in place
    and returned). After it, st.DATA holds MANN, MANP and MANK of the animal activities, and AGGR YCOW.

    The caller supplies CAPRI's inputs at the year: DATA (the herds, yields, days, daily gains and the N in products
    CRPR_EXPT, fert/calc_nexport.gms at the year, which CAPRI runs at the start of PART III), the technologies' shares
    p_technFact, the correction factor p_animExcrProtCorrFact and the literal tables of feed/feed_decl.gms, with
    p_NutContManureKgM3 per cubic metre (p_NutContManureKgM3_per_kg_day is applied here). The functions run on the
    regions of st.RS."""
    st.p_NutContManureKgM3 = p_NutContManureKgM3_per_kg_day(st.p_NutContManureKgM3)
    for block in BLOCKS:
        block(st)
    return st

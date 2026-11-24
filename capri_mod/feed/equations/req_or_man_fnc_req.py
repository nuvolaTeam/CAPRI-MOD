r"""CAPRI's animal requirement functions: per head and technology the energy, crude protein, lysine, dry matter, fibre
and intake capacities, the production days, and the feed-share bounds and nutrient densities of the rations
(feed/req_or_man_fnc.gms called with %1 = req, PART I and PART II; CAPRI star 3.0, feed version _pw as in CAPRI's runs,
capmod/set_global_variables.gms l. 125).

CAPRI calls the file in this mode from capmod/def_requirements.gms l. 23 (the simulation year's yields; the baseline's
p_animReqLit is the result, l. 33) and in CAPREG and COCO. In 'req' mode CAPRI's %p_condition% is p_technFact (an
assignment holds where the technology has a share, not where the herd is), and the per-head parameters carry the
technology A (%yr_A% = A); the yields of a technology are the data's times (p_technFact(r, act, output, A) + 1).

One function per CAPRI statement block, in CAPRI's order; ReqState holds CAPRI's symbols of the call as dictionaries;
req_or_man_fnc_req runs the blocks in order. The stocking rate's blocks are the manure mode's (the same statements,
capri_mod/feed/equations/req_or_man_fnc.py DATA_AGGR_YCOW and p_stockingRate). The literal tables of feed/feed_decl.gms
are data (capri_data/2017/feed/req_or_man_params.csv, tools/build/build_req_or_man_params.py).

Departures from CAPRI: none in the functions. The inputs are the caller's (req_or_man_fnc_req's docstring).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)

#: CAPRI's sets (sets.gms; feed/feed_decl.gms)
SUBENE = ("NEL", "NEM", "NEA", "NEP", "NEG")
REQSE = ("ENNE", "ENMR", "ENMC", "ENMH", "ENMP")
FEED = ("FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR", "FCER", "FPRO", "FENE", "FMIL", "FOTH")
REQSR = FEED + ("ENNE", "CRPR", "LISI", "DRMN", "DRMX", "FIDI", "FILG", "FICO", "FICT", "FISM", "FISF", "TotFAT",
                "WADR", "WASE")
REQSC = ("ENNE", "CRPR", "LISI", "DRMN", "DRMX", "FIDI", "FILG", "FICO", "FICT", "FISM", "FISF", "TotFAT", "DRMA",
         "ENMR", "ENMC", "ENMH", "ENMP")
REQMSE = ("ENNE", "CRPR")
FODDI = ("FGRA", "FMAI", "FOFA", "FROO", "FCOM", "FSGM", "FSTR")
fibreRichFeed = ("FOFA", "FGRA", "FMAI")
ACATTLE = ("DCOL", "DCOH", "BULL", "BULH", "HEIL", "HEIH", "HEIR")
FeedAggr = ("FeedRough", "FeedCons", "FeedOth", "FeedTotal")
#: CAPRI's technologies A (sets.gms): the mean technology and the high- and low-yield variants
A_ALL = ("T", "T1", "T2")


@dataclass
class ReqState:
    """CAPRI's symbols of one call of req_or_man_fnc.gms in 'req' mode at "Y".

    As capri_mod/feed/equations/req_or_man_fnc.ManState (DATA, RS, MS, R_RAGG_MS, GRSACT, RUMI, p_LUUnits, p_technFact,
    the literal tables of feed/feed_decl.gms), and: AACT, CAPRI's animal activities; p_rcEmissions, {(region, MITERRA
    animal, HD | Et): value} (envind/ammo.gms l. 1156-1160); p_feedQuant, {(member state, feed): quantity}
    (capmod/load_feed.gms l. 48: the base year's GROF); p_coeffEnergyForGrowth, p_convFactEnergyUnitsToEnne,
    p_NutContFeedRef ({(activity, A, requirement, feed aggregate, MIN | MEAN | MAX): value})."""
    DATA: dict
    RS: tuple
    MS: frozenset
    R_RAGG_MS: dict
    GRSACT: tuple
    RUMI: tuple
    AACT: tuple
    p_LUUnits: dict
    p_technFact: dict
    p_rcEmissions: dict
    p_feedQuant: dict
    p_carcassShare: dict
    p_startWgt: dict
    p_reqfcnlim: dict
    p_coeffEnergyForGrowth: dict
    p_convFactEnergyUnitsToEnne: dict
    p_NutContFeedRef: dict
    p_pigsReqLowWgt: dict = field(default_factory=dict)
    p_pigsReqHighWgt: dict = field(default_factory=dict)
    #: DATA at "BAS" (the base year's fodder production and straw), and CAPRI's sets MAACT, MCACT, FEED_TO_O, PACT_TO_O
    DATA_BAS: dict = field(default_factory=dict)
    MAACT: tuple = ()
    MCACT: tuple = ()
    FEED_TO_O: frozenset = frozenset()
    PACT_TO_O: frozenset = frozenset()
    # CAPRI's parameters of the call
    p_dataCopy: dict = field(default_factory=dict)
    p_stockingRate: dict = field(default_factory=dict)
    p_milkFatCont: dict = field(default_factory=dict)
    p_meanLiveWgt: dict = field(default_factory=dict)
    p_animProdDays: dict = field(default_factory=dict)
    p_milkPerDay: dict = field(default_factory=dict)
    p_fatCorMilk: dict = field(default_factory=dict)
    p_femWgt: dict = field(default_factory=dict)
    p_dailyWgtIncrease: dict = field(default_factory=dict)
    p_fatngDays: dict = field(default_factory=dict)
    p_finalLiveWgt: dict = field(default_factory=dict)
    p_eggYield: dict = field(default_factory=dict)
    p_sharGoatHerd: dict = field(default_factory=dict)
    p_crprReq: dict = field(default_factory=dict)
    p_animReq: dict = field(default_factory=dict)
    p_animReqSubEne: dict = field(default_factory=dict)
    p_minFeedShare: dict = field(default_factory=dict)
    p_maxFeedShare: dict = field(default_factory=dict)
    p_NutContFeed: dict = field(default_factory=dict)
    p_totEnneFromFibreRichFeed: dict = field(default_factory=dict)
    #: the animal activities the call could not compute (PIGF without CAPRI's pig requirement tables)
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
        """CAPRI's technologies A with p_technFact(r, c, "LEVL", A) (CAPRI's %p_condition% in 'req' mode)."""
        return [a for a in A_ALL if self.tf(r, c, "LEVL", a)]

    def lim(self, c, row, bound):
        """p_reqfcnlim(c, row, bound), 0 where absent (GAMS)."""
        return float(self.p_reqfcnlim.get((c, row, bound), 0.0) or 0.0)

    def ms_sum(self, r, f):
        """SUM(R_RAGG(r, MS), f(MS))."""
        m = self.R_RAGG_MS.get(r)
        return f(m) if m is not None else 0.0

    def rc(self, r, animal, pos):
        """p_rcEmissions(r, animal, pos), 0 where absent."""
        return float(self.p_rcEmissions.get((r, animal, pos), 0.0) or 0.0)

    def req(self, r, c, t, item):
        """p_animReq(r, c, t, item), 0 where absent."""
        return float(self.p_animReq.get((r, c, t, item), 0.0) or 0.0)

    def g(self, d, *key):
        """d[key], 0 where absent (a GAMS parameter)."""
        return float(d.get(key if len(key) > 1 else key[0], 0.0) or 0.0)


def _set_req(st, r, c, t, item, v):
    st.p_animReq[(r, c, t, item)] = v


# ------------------------------------------------------------------ the copy of the data
def p_dataCopy_req(st: ReqState) -> None:
    r"""The copy of the data the functions work on ('req' mode: the animal activities' levels, days, daily gains and
    outputs, and the sheep's and goats' herds).

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

    Departures from CAPRI: the copy holds every column of DATA (the functions read only the rows CAPRI copies)."""
    st.p_dataCopy = dict(st.DATA)


# ------------------------------------------------------------------ (1) milk cows
def p_milkFatCont(st: ReqState) -> None:
    r"""The milk fat content, 4% in every region.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 152):

          p_milkFatCont(RS,"FATS") = 4.0;

    Departures from CAPRI: none."""
    for r in st.RS:
        st.p_milkFatCont[(r, "FATS")] = 4.0


def p_meanLiveWgt_DCOW(st: ReqState) -> None:
    r"""The dairy cows' mean live weight, 600 kg.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 156):

          p_meanLiveWgt(RS,DCOW,%yr_A%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%) = 600.0 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = 600.0


def p_animProdDays_DCOW(st: ReqState) -> None:
    r"""The dairy cows' production days, 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 160):

        $ifi %req% ==on  p_animProdDays(RS,DCOW,A %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)      = 365;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_animProdDays[(r, a, t)] = 365


def p_milkPerDay_DCOW(st: ReqState) -> None:
    r"""The dairy cows' milk per lactation day: the technology's milk sold and fed over 305 days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 164-169):

          p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) $ %p_condition%(RS,DCOW,"LEVL",%yr_A%)


        $iftheni.perday %req% ==on
                      =  p_dataCopy(RS,DCOW,"COMI",%yr%)*(p_technFact(RS,DCOW,"COMI",A)+1.) / 305.
                       + p_dataCopy(RS,DCOW,"COMF",%yr%)*(p_technFact(RS,DCOW,"COMF",A)+1.) / 305.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_milkPerDay[(r, a, t)] = (st.dc(r, a, "COMI") * (st.tf(r, a, "COMI", t) + 1.) / 305.
                                              + st.dc(r, a, "COMF") * (st.tf(r, a, "COMF", t) + 1.) / 305.)


def p_crprReq_DCOW(st: ReqState) -> None:
    r"""The dairy cows' crude-protein requirement per head and year: lactation, maintenance and the dry period.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 179-185):

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
                                           * st.g(st.p_milkPerDay, r, a, t) * 305.
                                           + (117. + 0.6 * st.g(st.p_meanLiveWgt, r, a, t)) / 1000. * 365.
                                           + 1.300 * 42.)


def p_fatCorMilk_DCOW(st: ReqState) -> None:
    r"""The dairy cows' fat-corrected milk per day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 192-193):

                    p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * ( 0.4 + 0.15 * p_milkFatCont(RS,"FATS") );

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                st.p_fatCorMilk[(r, a, t)] = st.g(st.p_milkPerDay, r, a, t) * (0.4 + 0.15 * st.p_milkFatCont[(r, "FATS")])


def p_animReq_DCOW_energy(st: ReqState) -> None:
    r"""The dairy cows' minimum dry matter of the lactation and their net energy for lactation, maintenance, activity
    (MITERRA's housing days and share) and pregnancy (IPCC 2006), and the total.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 197-222):

                    p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = (0.0185 * p_meanLiveWgt(RS,DCOW,%yr_A%) + 0.305 * p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%)) * 305.;
        *
        *               -- net energy for lactation (from IPCC: NEl)
        *
                    p_animReq(RS,DCOW,A,"NEL" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      = ( 0.4  * p_milkFatCont(RS,"FATS")  + 1.47 ) * p_milkPerDay(RS,DCOW,%yr_A% %addtimedim%) * 305.;

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEM" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386) * 365.;

        *               -- net energy for activity (from IPCC: NEa,
        *                  Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEA" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386)* 0.17
                       * (365-p_rcEmissions(RS,"DAICOW_L","HD"))*(1-p_rcEmissions(RS,"DAICOW_L","Et")/100);

        *               -- net energy for pregnancy (from IPCC: NEp, IPCC 2006)

                    p_animReq(RS,DCOW,A,"NEP" %addtimedim%)  $ p_technFact(RS,DCOW,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.386)* 0.10 * 365.;

                    p_animReq(RS,DCOW,A,"ENNE" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A) = SUM(SUBENE, p_animReq(RS,DCOW,A,SUBENE %addtimedim%));

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                w, m, fc = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_milkPerDay, r, a, t), st.g(st.p_fatCorMilk, r, a, t)
                fat = st.p_milkFatCont[(r, "FATS")]
                _set_req(st, r, a, t, "DRMN", (0.0185 * w + 0.305 * fc) * 305.)
                _set_req(st, r, a, t, "NEL", (0.4 * fat + 1.47) * m * 305.)
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.386) * 365.)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.386) * 0.17 * (365 - st.rc(r, "DAICOW_L", "HD"))
                         * (1 - st.rc(r, "DAICOW_L", "Et") / 100))
                _set_req(st, r, a, t, "NEP", (w ** 0.75 * 0.386) * 0.10 * 365.)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))


def p_animReq_DCOW_dry_matter(st: ReqState) -> None:
    r"""The dairy cows' minimum dry matter with the dry period, the digestible fibre and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 226-231):

                    p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) + ( 0.0185 * p_meanLiveWgt(RS,DCOW,%yr_A%) ) * 60. ;
                    p_animReq(RS,DCOW,A,"FIDI" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_animReq(RS,DCOW,A,"DRMN" %addtimedim%) * (p_fatCorMilk(RS,DCOW,%yr_A% %addtimedim%)/100 - 0.29 + 43.92/ 100);
                    p_animReq(RS,DCOW,A,"FICO" %addtimedim%) $ p_technFact(RS,DCOW,"LEVL",A)
                      = p_meanLiveWgt(RS,DCOW,%yr_A%)**0.75 * 0.14 * 365. * 0.7 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in DCOW:
            for t in st.techs(r, a):
                w, fc = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_fatCorMilk, r, a, t)
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0185 * w) * 60.)
                _set_req(st, r, a, t, "FIDI", st.req(r, a, t, "DRMN") * (fc / 100 - 0.29 + 43.92 / 100))
                _set_req(st, r, a, t, "FICO", w ** 0.75 * 0.14 * 365. * 0.7)


# ------------------------------------------------------------------ (2) suckler cows
def p_meanLiveWgt_SCOW(st: ReqState) -> None:
    r"""The suckler cows' mean live weight, 550 kg, and production days, 365.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 249-250):

          p_meanLiveWgt(RS,"SCOW",%yr_A%)  $ %p_condition%(RS,"SCOW","LEVL",%yr_A%) = 550.0 ;
        $ifi %req% ==on  p_animProdDays(RS,"SCOW",A %addtimedim%)      $ p_technFact(RS,"SCOW","LEVL",A) = 365. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_meanLiveWgt[(r, "SCOW", t)] = 550.0
            st.p_animProdDays[(r, "SCOW", t)] = 365.


def p_milkPerDay_SCOW(st: ReqState) -> None:
    r"""The suckler cows' milk per lactation day: the technology's milk fed over 125 days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 254-256):

          p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) $ %p_condition%(RS,"SCOW","LEVL",%yr_A%)
        $iftheni.perday1 %req% ==on
                      = p_dataCopy(RS,"SCOW","COMF",%yr%)*(p_technFact(RS,"SCOW","COMF",A)+1.) / 125. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in st.techs(r, "SCOW"):
            st.p_milkPerDay[(r, "SCOW", t)] = st.dc(r, "SCOW", "COMF") * (st.tf(r, "SCOW", "COMF", t) + 1.) / 125.


def p_crprReq_SCOW(st: ReqState) -> None:
    r"""The suckler cows' crude-protein requirement per head and year.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 265-271):

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
                                            * st.g(st.p_milkPerDay, r, "SCOW", t) * 125.
                                            + (0.00127 * st.g(st.p_meanLiveWgt, r, "SCOW", t) + 0.1273) * 365.
                                            + 1.300 * 42.)


def p_animReq_SCOW(st: ReqState) -> None:
    r"""The suckler cows' fat-corrected milk, minimum dry matter, net energy for lactation, maintenance, activity
    and pregnancy (per calf born), the total, and their dry matter, digestible fibre and intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 277-318):

                    p_fatCorMilk(RS,"SCOW",A %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * ( 0.4 + 0.15 * p_milkFatCont(RS,"FATS") ) ;
        *
        *               -- min. dry matter for lactation per. (CAPRI working paper 97-12)
        *
                    p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = (0.0185 * p_meanLiveWgt(RS,"SCOW",%yr_A%) + 0.305 * p_fatCorMilk(RS,"SCOW",%yr_A% %addtimedim%)) * 125.;
        *
        *               -- Net Energy calculation from IPCC
        *
                    p_animReq(RS,"SCOW",A,"NEL" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( 0.4  * p_milkFatCont(RS,"FATS")  + 1.47 ) * p_milkPerDay(RS,"SCOW",%yr_A% %addtimedim%) * 125.;
        *
        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEM" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386) * 365.;
        *
        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                  shares from N2O Manure Management Miterra, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386)* 0.17
                       * (365-p_rcEmissions(RS,"OCOW_L","HD"));
        *
        *               -- net energy for pregnancy (from IPCC: NEp, IPCC 2006)
        *
                    p_animReq(RS,"SCOW",A,"NEP" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.386)* 0.10 * 365.
                       * (  p_dataCopy(RS,"SCOW","YCAM",%yr%)*(p_technFact(RS,"SCOW","YCAM",A)+1)
                          + p_dataCopy(RS,"SCOW","YCAF",%yr%)*(p_technFact(RS,"SCOW","YCAF",A)+1))/1000;

                    p_animReq(RS,"SCOW",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)  = SUM(SUBENE, p_animReq(RS,"SCOW",A,SUBENE %addtimedim%));
        *
        *               -- dry matter stuff is from CAPRI working paper 97-12

                    p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) + ( 0.0185 * p_meanLiveWgt(RS,"SCOW",%yr_A%) ) * 240. ;
                    p_animReq(RS,"SCOW",A,"FIDI" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_animReq(RS,"SCOW",A,"DRMN" %addtimedim%) * (p_fatCorMilk(RS,"SCOW",%yr_A% %addtimedim%)/100 - 0.29 + 43.92/100);
                    p_animReq(RS,"SCOW",A,"FICO" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A)
                      = p_meanLiveWgt(RS,"SCOW",%yr_A%)**0.75 * 0.14 * 365. * 0.7;

    Departures from CAPRI: none."""
    a = "SCOW"
    for r in st.RS:
        for t in st.techs(r, a):
            m, w = st.g(st.p_milkPerDay, r, a, t), st.g(st.p_meanLiveWgt, r, a, t)
            fat = st.p_milkFatCont[(r, "FATS")]
            st.p_fatCorMilk[(r, a, t)] = m * (0.4 + 0.15 * fat)
            fc = st.p_fatCorMilk[(r, a, t)]
            _set_req(st, r, a, t, "DRMN", (0.0185 * w + 0.305 * fc) * 125.)
            _set_req(st, r, a, t, "NEL", (0.4 * fat + 1.47) * m * 125.)
            _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.386) * 365.)
            _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.386) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")))
            _set_req(st, r, a, t, "NEP", (w ** 0.75 * 0.386) * 0.10 * 365.
                     * (st.dc(r, a, "YCAM") * (st.tf(r, a, "YCAM", t) + 1)
                        + st.dc(r, a, "YCAF") * (st.tf(r, a, "YCAF", t) + 1)) / 1000)
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0185 * w) * 240.)
            _set_req(st, r, a, t, "FIDI", st.req(r, a, t, "DRMN") * (fc / 100 - 0.29 + 43.92 / 100))
            _set_req(st, r, a, t, "FICO", w ** 0.75 * 0.14 * 365. * 0.7)


def p_femWgt(st: ReqState) -> None:
    r"""The mean live weight of an adult female per technology, the dairy and suckler cows' weighted by their herds
    (550 kg where the region has none).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 326-332):

          p_femWgt(RS,%yr_A%) = 550;
          p_femWgt(RS,%yr_A%) $ (     sum(DCOW,p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                                  or          (p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%)))
            =
                  (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)  *p_meanLiveWgt(RS,DCOW,%yr_A%))
                            + p_dataCopy(RS,"SCOW","LEVL",%yr%)*p_meanLiveWgt(RS,"SCOW",%yr_A%))
             /    (sum(DCOW,  p_dataCopy(RS,DCOW,"LEVL",%yr%)) + p_dataCopy(RS,"SCOW","LEVL",%yr%));

    Departures from CAPRI: none."""
    for r in st.RS:
        for t in A_ALL:
            st.p_femWgt[(r, t)] = 550
            d = sum(st.dc(r, a, "LEVL") * st.g(st.p_meanLiveWgt, r, a, t) for a in DCOW)
            s = st.dc(r, "SCOW", "LEVL") * st.g(st.p_meanLiveWgt, r, "SCOW", t)
            if d or s:
                st.p_femWgt[(r, t)] = (d + s) / (sum(st.dc(r, a, "LEVL") for a in DCOW) + st.dc(r, "SCOW", "LEVL"))


# ------------------------------------------------------------------ (3) fattening of calves
def _scaled_ms(st, r, a, row):
    """SUM(R_RAGG(r, MS), p_dataCopy(MS, a, row) / p_stockingRate(MS)) * p_stockingRate(r)."""
    return st.ms_sum(r, lambda m: st.dc(m, a, row) / st.p_stockingRate[m]) * st.p_stockingRate.get(r, 0.0)


def _final_CALF(st, r, a, t):
    """The fattened calf's final live weight of the technology: p_dataCopy BEEF x (p_technFact BEEF + 1) / carcass."""
    return st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a]


def p_dailyWgtIncrease_CALF(st: ReqState) -> None:
    r"""The fattened calves' daily gain (kg): the member state's scaled by the stocking rates, within CAPRI's limits.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 343-347):

          p_dailyWgtIncrease(RS,CALF,%yr_A%) $ %p_condition%(RS,CALF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(CALF,"DAILY","up"),
                  MAX(p_reqfcnlim(CALF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,CALF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000


def p_animProdDays_CALF(st: ReqState) -> None:
    r"""The fattened calves' process length, the gain from 50 kg to the final weight at the daily gain, within
    CAPRI's limits.

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
            for t in st.techs(r, a):
                st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    _final_CALF(st, r, a, t) - st.p_startWgt[a]) / st.p_dailyWgtIncrease[(r, a, t)]))


def CALF_light(st: ReqState) -> None:
    r"""(a) Light calves (final live weight up to 150 kg): the mean live weight and the fattening days (one phase).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 367-384):

          p_meanLiveWgt(RS,CALF,%yr_A%) $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req7 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req7
                                             / p_carcassShare(CALF))  LE 150. )
        *                          increase up to mid point of fattening period:
            = (p_startWgt(CALF) + (p_animProdDays(RS,CALF,%yr_A% %addtimedim%) * p_dailyWgtIncrease(RS,CALF,%yr_A%)) / 2.)
            $ %p_condition%(RS,CALF,"LEVL",%yr_A%);
        *
        *         Fattening days for calculation of requirements equals total process length (only one phase considered)
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
            for t in A_ALL:
                light = _final_CALF(st, r, a, t) <= 150.
                if light:
                    st.p_meanLiveWgt[(r, a, t)] = ((st.p_startWgt[a] + (st.g(st.p_animProdDays, r, a, t)
                                                                        * st.g(st.p_dailyWgtIncrease, r, a, t)) / 2.)
                                                   if st.tf(r, a, "LEVL", t) else 0.0)
                st.p_fatngDays[(r, a, t)] = 0
                if light and st.tf(r, a, "LEVL", t):
                    st.p_fatngDays[(r, a, t)] = st.p_animProdDays[(r, a, t)]


def _crpr_lt150(w, d, n):
    """( - 0.00039 * mean live weight + 0.000628 * daily gain [g] - 0.0193 ) * days (l. 395-396, 459-460, 616-617)."""
    return (- 0.00039 * w + 0.000628 * d * 1000. - 0.0193) * n


def _crpr_gt150(w, d, n):
    """( 0.00109 * mean live weight + 0.00022 * daily gain [g] + 0.2027 ) * days (l. 532, 681-682)."""
    return (0.00109 * w + 0.00022 * d * 1000. + 0.2027) * n


def _neg(st, w, a, fem, d, n):
    """IPCC 2006's net energy for growth (eq. 10.6): 22.02 x (weight / (C x the adult female's)) ** 0.75 x the daily
    gain ** 1.097 x days, C = p_coeffEnergyForGrowth (l. 404-405, 468-469, 541-542, 625-626, 695-696, 801-802)."""
    return 22.02 * (w / (st.p_coeffEnergyForGrowth[a] * fem)) ** 0.75 * (d ** 1.097) * n


def p_crprReq_CALF_light(st: ReqState) -> None:
    r"""(a) Light calves: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 394-396):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = _crpr_lt150(st.g(st.p_meanLiveWgt, r, a, t),
                                                          st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_light(st: ReqState) -> None:
    r"""(a) Light calves: the net energy for growth, maintenance and activity, the total, and the minimum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 403-424):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = 22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,A)))**0.75
                    * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALF,A,"NEM" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( 0.0271 * p_meanLiveWgt(RS,CALF,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALF,%yr_A%) * 0.9 ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in A_ALL:
                n = st.g(st.p_fatngDays, r, a, t)
                if not n:
                    continue
                w, d = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t)
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", (0.0271 * w - 0.433) * n * 0.9)


def CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves (final live weight above 150 kg), the first phase from 50 to 150 kg: mean live weight
    100 kg and the days of the 100 kg gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 432-448):

          p_meanLiveWgt(RS,CALF,%yr_A%)  $ ((  p_dataCopy(RS,CALF,"BEEF",%yr%)
        $iftheni.req11 %req% ==on
                                             *(p_technFact(RS,CALF,"BEEF",A)+1.)
        $endif.req11
                                             / p_carcassShare(CALF))  GT 150. )
        *     Note: 100 = (50+150)/2 = mean weight
            = 100.  $ %p_condition%(RS,CALF,"LEVL",%yr_A%);
        *
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
            for t in A_ALL:
                heavy = _final_CALF(st, r, a, t) > 150.
                if heavy:
                    st.p_meanLiveWgt[(r, a, t)] = 100. if st.tf(r, a, "LEVL", t) else 0.0
                st.p_fatngDays[(r, a, t)] = 0
                if heavy and st.tf(r, a, "LEVL", t):
                    st.p_fatngDays[(r, a, t)] = 100. / st.p_dailyWgtIncrease[(r, a, t)]


def p_crprReq_CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves, first phase: the crude-protein requirement.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 458-460):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = ( - 0.00039 * p_meanLiveWgt(RS,CALF,%yr_A%)
                + 0.000628 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. -0.0193 ) * p_fatngDays(RS,CALF,%yr_A%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = _crpr_lt150(st.g(st.p_meanLiveWgt, r, a, t),
                                                          st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_heavy_b1(st: ReqState) -> None:
    r"""(b1) Heavy calves, first phase: the net energy for growth, maintenance and activity, the total, and the
    minimum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 467-488):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            =  22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEM" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            =  ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));

        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = ( 0.0271 * p_meanLiveWgt(RS,CALF,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALF,%yr_A%) * 0.9 ;

    Departures from CAPRI: none."""
    p_animReq_CALF_light(st)


def CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, the second phase from 150 kg to the final weight: the mean live weight and the phase's days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 493-518):

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
        *
        * --- length of second phase
        *
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
            for t in A_ALL:
                heavy = _final_CALF(st, r, a, t) > 150.
                if heavy:
                    st.p_meanLiveWgt[(r, a, t)] = ((150. + (st.g(st.p_animProdDays, r, a, t)
                                                            * st.g(st.p_dailyWgtIncrease, r, a, t) - 100) / 2.)
                                                   if st.tf(r, a, "LEVL", t) else 0.0)
                st.p_fatngDays[(r, a, t)] = 0
                if heavy and st.tf(r, a, "LEVL", t):
                    d = st.p_dailyWgtIncrease[(r, a, t)]
                    st.p_fatngDays[(r, a, t)] = (st.p_animProdDays[(r, a, t)] * d - 100) / d


def p_crprReq_CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, second phase: the crude-protein requirement, added to the first phase's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 530-532):

          p_crprReq(RS,CALF,A,%yr%) $ (p_fatngDays(RS,CALF,%yr_A%) and p_technFact(RS,CALF,"LEVL",A))
            = p_crprReq(RS,CALF,A,%yr%)
             + ( 0.00109 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.00022 * p_dailyWgtIncrease(RS,CALF,%yr_A%) * 1000. + 0.2027 ) * p_fatngDays(RS,CALF,%yr_A%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_gt150(
                        st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)])


def p_animReq_CALF_heavy_b2(st: ReqState) -> None:
    r"""(b2) Heavy calves, second phase: the net energy for growth, maintenance and activity and the minimum dry
    matter, added to the first phase's; the total; and, for every calf, the maximum dry matter and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 539-564):

          p_animReq(RS,CALF,A,"NEG" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  p_animReq(RS,CALF,A,"NEG" %addtimedim%)
             + 22.02 * (p_meanLiveWgt(RS,CALF,%yr_A%) / (p_coeffEnergyForGrowth(CALF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALF,%yr_A%)**(1.097)) * p_fatngDays(RS,CALF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALF,A,"NEM" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            = p_animReq(RS,CALF,A,"NEM" %addtimedim%) + ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALF,%yr_A%);
        *
        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALF,A,"NEA" %addtimedim%)  $ p_fatngDays(RS,CALF,%yr_A%)
            =  p_animReq(RS,CALF,A,"NEA" %addtimedim%)
             + ( p_meanLiveWgt(RS,CALF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365.* p_fatngDays(RS,CALF,%yr_A%);
        *
          p_animReq(RS,CALF,A,"ENNE" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%) = SUM(SUBENE, p_animReq(RS,CALF,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALF,A,"DRMN" %addtimedim%) $ p_fatngDays(RS,CALF,%yr_A%)
            = p_animReq(RS,CALF,A,"DRMN" %addtimedim%)
             + ( 2.433 + 0.0116 * p_meanLiveWgt(RS,CALF,%yr_A%) + 0.0002 * p_dailyWgtIncrease(RS,CALF,%yr_A%))*p_fatngDays(RS,CALF,%yr_A%)*0.9;
          p_animReq(RS,CALF,A,"DRMX" %addtimedim%)  = p_animReq(RS,CALF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,CALF,A,"FICT" %addtimedim%)  = p_animReq(RS,CALF,A,"DRMX" %addtimedim%) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALF:
            for t in A_ALL:
                n = st.g(st.p_fatngDays, r, a, t)
                if n:
                    w, d = st.g(st.p_meanLiveWgt, r, a, t), st.g(st.p_dailyWgtIncrease, r, a, t)
                    _set_req(st, r, a, t, "NEG", st.req(r, a, t, "NEG") + _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                    _set_req(st, r, a, t, "NEM", st.req(r, a, t, "NEM") + (w ** 0.75 * 0.322) * n)
                    _set_req(st, r, a, t, "NEA", st.req(r, a, t, "NEA") + (w ** 0.75 * 0.322) * 0.17
                             * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                    _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                    _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN")
                             + (2.433 + 0.0116 * w + 0.0002 * d) * n * 0.9)
            for t in A_ALL:
                if (r, a, t, "DRMN") in st.p_animReq or (r, a, t, "DRMX") in st.p_animReq:
                    _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                    _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))


# ------------------------------------------------------------------ (4) raising of calves
def CALR_weaning(st: ReqState) -> None:
    r"""Raised calves, the first 49 days (weaning): the crude protein, the net energy for lactation and the minimum
    dry matter of the milk powder.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 588-596):

          p_crprReq(RS,CALR,A,%yr%)  $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
            = 0.35  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on
          p_animReq(RS,CALR,A,"NEL" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            = 11.79 * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;
          p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
            = 0.93  * 0.1 * (2.+2.+5.+6.+7.+8.+8.)/7 * 49;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = 0.35 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49
                _set_req(st, r, a, t, "NEL", 11.79 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49)
                _set_req(st, r, a, t, "DRMN", 0.93 * 0.1 * (2. + 2. + 5. + 6. + 7. + 8. + 8.) / 7 * 49)


def CALR_80_150(st: ReqState) -> None:
    r"""Raised calves, the next 125 days (80 to 150 kg): mean live weight, daily gain and days; the crude protein; the
    net energy for growth, maintenance and activity, the total, and the minimum dry matter added to the weaning's.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 601-645):

          p_meanLiveWgt(RS,CALR,%yr_A%)      $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 80. + 150.) / 2. ;
          p_dailyWgtIncrease(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = (150.-80.)/125.;
          p_fatngDays(RS,CALR,%yr_A%)        $ %p_condition%(RS,CALR,"LEVL",%yr_A%) = ( 150. - 80. ) / p_dailyWgtIncrease(RS,CALR,%yr_A%) ;
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,CALR,curRows,%yr%)  $ p_dataCopy(RS,CALR,"LEVL",%yr%)
            =  p_dataCopy(RS,CALR,curRows,%yr%)
             + p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,CALR,%yr_A%) * p_meanLiveWgt(RS,CALR,%yr_A%);
        $endif

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
           p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%) * p_technFact(RS,CALR,"LEVL",A) )
              =  p_crprReq(RS,CALR,A,%yr%)
               + ( - 0.00039 * p_meanLiveWgt(RS,CALR,%yr_A%)
                   + 0.000628 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. - 0.0193 ) * p_fatngDays(RS,CALR,%yr_A%);
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *               -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

                    p_animReq(RS,CALR,A,"NEG" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      = 22.02 * (p_meanLiveWgt(RS,CALR,%yr_A%) / (p_coeffEnergyForGrowth(CALR) * p_femWgt(RS,%yr_A%)))**0.75
                              * (p_dailyWgtIncrease(RS,CALR,%yr_A%)**(1.097)) * p_fatngDays(RS,CALR,%yr_A%);

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
                    p_animReq(RS,CALR,A,"NEM" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      = ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALR,%yr_A%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                                       shares from N2O Manure Management Miterra, IPCC 2006)
        *
                    p_animReq(RS,CALR,A,"NEA" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
                      =  ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322)* 0.17
                       * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALR,%yr_A%);
        *
                    p_animReq(RS,CALR,A,"ENNE" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = SUM(SUBENE, p_animReq(RS,CALR,A,SUBENE %addtimedim%));
        *
        *               -- dry matter stuff is from CAPRI working paper 97-12

                    p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
                      =  p_animReq(RS,CALR,A,"DRMN" %addtimedim%)
                       + ( 0.0271 * p_meanLiveWgt(RS,CALR,%yr_A%) - 0.433 ) * p_fatngDays(RS,CALR,%yr_A%) * 0.9;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = (80. + 150.) / 2.
                st.p_dailyWgtIncrease[(r, a, t)] = (150. - 80.) / 125.
                st.p_fatngDays[(r, a, t)] = (150. - 80.) / st.p_dailyWgtIncrease[(r, a, t)]
            for t in st.techs(r, a):
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_lt150(
                        st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)])
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (0.0271 * w - 0.433) * n * 0.9)


def CALR_last(st: ReqState) -> None:
    r"""Raised calves, the last phase (150 kg to the bulls' or heifers' start weight): its days from the member
    state's raising days scaled by the stocking rates, within CAPRI's limits; the daily gain and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 654-668):

          p_fatngDays(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
            = MAX(p_reqfcnlim(CALR,"DAYS","lo")-49-125,
                  MIN(p_reqfcnlim(CALR,"DAYS","up")-49-125,
                  SUM(R_RAGG(RS,MS),(p_dataCopy(MS,CALR,"DAYS",%yr%)-49-125)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)));

          p_dailyWgtIncrease(RS,"CAMR",%yr_A%) $ (%p_condition%(RS,"CAMR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAMR",%yr_A%))
            = (p_startWgt("BULF") - 150) / p_fatngDays(RS,"CAMR",%yr_A%) ;
          p_dailyWgtIncrease(RS,"CAFR",%yr_A%) $ (%p_condition%(RS,"CAFR","LEVL",%yr_A%) $ p_fatngDays(RS,"CAFR",%yr_A%))
            = (p_startWgt("HEIF") - 150) / p_fatngDays(RS,"CAFR",%yr_A%) ;

        * --- average live weight

          p_meanLiveWgt(RS,CALR,%yr_A%) $ %p_condition%(RS,CALR,"LEVL",%yr_A%)
        *             increase up to mid point of raising period:
            = 150. + (p_dailyWgtIncrease(RS,CALR,%yr_A%) * p_fatngDays(RS,CALR,%yr_A%)) / 2. ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                ms = st.ms_sum(r, lambda m: (st.dc(m, a, "DAYS") - 49 - 125) / st.p_stockingRate[m])
                st.p_fatngDays[(r, a, t)] = max(st.lim(a, "DAYS", "lo") - 49 - 125, min(
                    st.lim(a, "DAYS", "up") - 49 - 125, ms * st.p_stockingRate.get(r, 0.0)))
        for a, to in (("CAMR", "BULF"), ("CAFR", "HEIF")):
            for t in st.techs(r, a):
                if st.g(st.p_fatngDays, r, a, t):
                    st.p_dailyWgtIncrease[(r, a, t)] = (st.p_startWgt[to] - 150) / st.p_fatngDays[(r, a, t)]
        for a in CALR:
            for t in st.techs(r, a):
                st.p_meanLiveWgt[(r, a, t)] = 150. + (st.g(st.p_dailyWgtIncrease, r, a, t)
                                                      * st.g(st.p_fatngDays, r, a, t)) / 2.


def CALR_last_requirements(st: ReqState) -> None:
    r"""Raised calves, the last phase: the crude protein, the production days (the three phases), the net energy
    for growth, maintenance and activity and the minimum dry matter added to the first two phases'; the total; the
    maximum dry matter and the intake capacity.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 679-719):

          p_crprReq(RS,CALR,A,%yr%) $ (p_dataCopy(RS,CALR,"LEVL",%yr%)*p_technFact(RS,CALR,"LEVL",A) )
            =  p_crprReq(RS,CALR,A,%yr%)
             + (  0.00109 * p_meanLiveWgt(RS,CALR,%yr_A%)
                + 0.00022 * p_dailyWgtIncrease(RS,CALR,%yr_A%) * 1000. + 0.2027 )  * p_fatngDays(RS,CALR,%yr_A%)  ;
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,CALR,%yr_A% %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = 49. + 125 + p_fatngDays(RS,CALR,%yr_A%) ;

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,CALR,A,"NEG" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            =  p_animReq(RS,CALR,A,"NEG" %addtimedim%)
             + 22.02 * (p_meanLiveWgt(RS,CALR,%yr_A%) / (p_coeffEnergyForGrowth(CALR) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,CALR,%yr_A%)**(1.097)) * p_fatngDays(RS,CALR,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,CALR,A,"NEM" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
           = p_animReq(RS,CALR,A,"NEM" %addtimedim%) + ( p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,CALR,%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,CALR,A,"NEA" %addtimedim%)  $ p_technFact(RS,CALR,"LEVL",A)
            = p_animReq(RS,CALR,A,"NEA" %addtimedim%) + (p_meanLiveWgt(RS,CALR,%yr_A%)**0.75 * 0.322) * 0.17
                                         * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365. * p_fatngDays(RS,CALR,%yr_A%);
        *
          p_animReq(RS,CALR,A,"ENNE" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = SUM(SUBENE, p_animReq(RS,CALR,A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,CALR,A,"DRMN" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)
            = p_animReq(RS,CALR,A,"DRMN" %addtimedim%)
             + (   2.433 + 0.0116 * p_meanLiveWgt(RS,CALR,%yr_A%)
                 + 0.0002 * p_dailyWgtIncrease(RS,CALR,%yr_A%) ) * p_fatngDays(RS,CALR,%yr_A%) * 0.9;
          p_animReq(RS,CALR,A,"DRMX" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)= p_animReq(RS,CALR,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,CALR,A,"FICT" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A)= p_animReq(RS,CALR,A,"DRMX" %addtimedim%);

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in CALR:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)]
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = st.g(st.p_crprReq, r, a, t) + _crpr_gt150(w, d, n)
                st.p_animProdDays[(r, a, t)] = 49. + 125 + n
                _set_req(st, r, a, t, "NEG", st.req(r, a, t, "NEG") + _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", st.req(r, a, t, "NEM") + (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", st.req(r, a, t, "NEA") + (w ** 0.75 * 0.322) * 0.17
                         * (365 - st.rc(r, "OCOW_L", "HD")) / 365. * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") + (2.433 + 0.0116 * w + 0.0002 * d) * n * 0.9)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))


# ------------------------------------------------------------------ (5) beef fattening
def BULF_growth(st: ReqState) -> None:
    r"""Fattened bulls: the daily gain (the member state's scaled by the stocking rates, within CAPRI's limits, at
    most 0.4 kg plus 1.6 g per kg of final weight), the fattening days from the 335 kg start and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 732-761):

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
        *
        * --- fattening period (depending on final weight and final weight of male calves raised) and mean wgt
        *
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
        *
          p_meanLiveWgt(RS,BULF,%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
            = p_startWgt(BULF) + (p_fatngDays(RS,BULF,%yr_A%) * p_dailyWgtIncrease(RS,BULF,%yr_A%)) / 2.;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in BULF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000
                if st.dc(r, a, "BEEF") and st.p_dailyWgtIncrease[(r, a, t)]:
                    st.p_dailyWgtIncrease[(r, a, t)] = min(st.p_dailyWgtIncrease[(r, a, t)],
                                                           0.4 + (st.dc(r, a, "BEEF") / st.p_carcassShare[a]) * 0.0016)
            for t in st.techs(r, a):
                st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a] - st.p_startWgt[a])
                    / st.p_dailyWgtIncrease[(r, a, t)]))
                st.p_meanLiveWgt[(r, a, t)] = st.p_startWgt[a] + (st.p_fatngDays[(r, a, t)]
                                                                  * st.p_dailyWgtIncrease[(r, a, t)]) / 2.


def BULF_requirements(st: ReqState) -> None:
    r"""Fattened bulls: the minimum dry matter of the fattening by the daily gain's class, the crude protein, the net
    energy for growth, maintenance and activity, the total, the dry matter and intake capacity, and the production
    days (the fattening days).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 772-826):

          p_dataCopy(RS,BULF,"DRMN",%yr_A%)  $ %p_condition%(RS,BULF,"LEVL",%yr_A%)
        *
            =   ( ( ( 0.029 -  0.00001914 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%))  * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

                + (( ( 0.028 -  0.00001678 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%))
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

                + (( ( 0.0288 - 0.0000231  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_fatngDays(RS,BULF,%yr_A%) )
                $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);
        *
          p_crprReq(RS,BULF,A,%yr%) $  (p_dataCopy(RS,BULF,"LEVL",%yr%)*p_technFact(RS,BULF,"LEVL",A))
        *
            =  ((( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) LE 1.1)

               + ((( 0.1657 - 0.0001214  * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GT 1.1 AND p_dailyWgtIncrease(RS,BULF,%yr_A%) LT 1.3)

               + ((( 0.1493 - 0.00004405 * p_meanLiveWgt(RS,BULF,%yr_A%) ) * p_dataCopy(RS,BULF,"DRMN",%yr_A%)))
               $ ( p_dailyWgtIncrease(RS,BULF,%yr_A%) GE 1.3);
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,BULF,A,"NEG" %addtimedim%)  $ p_technFact(RS,BULF,"LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,BULF,%yr_A%) / (p_coeffEnergyForGrowth(BULF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,BULF,%yr_A%)**(1.097)) * p_fatngDays(RS,BULF,%yr_A%);

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,BULF,A,"NEM" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A)
           = ( p_meanLiveWgt(RS,BULF,%yr_A%)**0.75 * 0.370) * p_fatngDays(RS,BULF,%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

          p_animReq(RS,BULF,A,"NEA" %addtimedim%)  $ p_technFact(RS,BULF,"LEVL",A)
            =  ( p_meanLiveWgt(RS,BULF,%yr_A%)**0.75 * 0.370)* 0.17
                 * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365 * p_fatngDays(RS,BULF,%yr_A%);
        *
          p_animReq(RS,BULF,A,"ENNE" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A)     = SUM(SUBENE, p_animReq(RS,BULF,A,SUBENE %addtimedim%));
        *
        *     -- take mean dry matter intake from above and derive min and max

          p_animReq(RS,BULF,A,"DRMN" %addtimedim%) = p_dataCopy(RS,BULF,"DRMN",%yr_A%);
          p_animReq(RS,BULF,A,"DRMN" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMN" %addtimedim%) * 0.8;
          p_animReq(RS,BULF,A,"DRMX" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,BULF,A,"FICT" %addtimedim%) $ p_technFact(RS,BULF,"LEVL",A) = p_animReq(RS,BULF,A,"DRMX" %addtimedim%) ;
        *
        *     -- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,BULF,%yr_A% %addtimedim%) = p_fatngDays(RS,BULF,%yr_A%)      ;

    Departures from CAPRI: none."""
    drmn = {}
    for r in st.RS:
        for a in BULF:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                drmn[(r, a, t)] = ((((0.029 - 0.00001914 * w) * w) * n) * (d <= 1.1)
                                   + (((0.028 - 0.00001678 * w) * w) * n) * (1.1 < d < 1.3)
                                   + (((0.0288 - 0.0000231 * w) * w) * n) * (d >= 1.3))
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = (((0.1602 - 0.0001228 * w) * drmn[(r, a, t)]) * (d <= 1.1)
                                               + ((0.1657 - 0.0001214 * w) * drmn[(r, a, t)]) * (1.1 < d < 1.3)
                                               + ((0.1493 - 0.00004405 * w) * drmn[(r, a, t)]) * (d >= 1.3))
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.370) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.370) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365 * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
        for a in BULF:
            for t in A_ALL:
                if (r, a, t) in drmn:
                    _set_req(st, r, a, t, "DRMN", drmn[(r, a, t)])
            for t in st.techs(r, a):
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.8)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
            for t in A_ALL:
                if (r, a, t) in st.p_fatngDays:
                    st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]


# ------------------------------------------------------------------ (6) heifers fattening
def HEIF_growth(st: ReqState) -> None:
    r"""Fattened heifers: the daily gain, the fattening days from the 300 kg start and the mean live weight.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 835-855):

          p_dailyWgtIncrease(RS,HEIF,%yr_A%)  $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = MIN(p_reqfcnlim(HEIF,"DAILY","up"),
                  MAX(p_reqfcnlim(HEIF,"DAILY","lo"),
                  SUM(R_RAGG(RS,MS),p_dataCopy(MS,HEIF,"DAILY",%yr%)/p_stockingRate(MS,%yr%))*p_stockingRate(RS,%yr%)))
             / 1000;

        * --- fattening period and mean wgt
        *
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
        *
          p_meanLiveWgt(RS,HEIF,%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( p_startWgt(HEIF) + (p_fatngDays(RS,HEIF,%yr_A%) * p_dailyWgtIncrease(RS,HEIF,%yr_A%)) / 2. ) ;

    Departures from CAPRI: none."""
    for r in st.RS:
        for a in HEIF:
            for t in st.techs(r, a):
                st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(st.lim(a, "DAILY", "lo"),
                                                                                    _scaled_ms(st, r, a, "DAILY"))) / 1000
                st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"), (
                    st.dc(r, a, "BEEF") * (st.tf(r, a, "BEEF", t) + 1.) / st.p_carcassShare[a] - st.p_startWgt[a])
                    / st.p_dailyWgtIncrease[(r, a, t)]))
                st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + (st.p_fatngDays[(r, a, t)]
                                                                   * st.p_dailyWgtIncrease[(r, a, t)]) / 2.)


def HEIF_requirements(st: ReqState) -> None:
    r"""Fattened heifers: the minimum dry matter of the fattening, the crude protein, the net energy for growth,
    maintenance and activity, the total, the dry matter and intake capacity, and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 866-904):

          p_dataCopy(RS,HEIF,"DRMN",%yr_A%) $ %p_condition%(RS,HEIF,"LEVL",%yr_A%)
            = ( ( 0.029 - 0.00001914 * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_meanLiveWgt(RS,HEIF,%yr_A%)) * p_fatngDays(RS,HEIF,%yr_A%);
        *
          p_crprReq(RS,HEIF,A,%yr%) $ (p_dataCopy(RS,HEIF,"LEVL",%yr%)*p_technFact(RS,HEIF,"LEVL",A))
            = ( 0.1602 - 0.0001228  * p_meanLiveWgt(RS,HEIF,%yr_A%) ) * p_dataCopy(RS,HEIF,"DRMN",%yr_A%);
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *      -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,HEIF,A,"NEG" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,HEIF,%yr_A%) / (p_coeffEnergyForGrowth(HEIF) * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,HEIF,%yr_A%)**(1.097)) * p_fatngDays(RS,HEIF,%yr_A%);

        *      -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,HEIF,A,"NEM" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A) = ( p_meanLiveWgt(RS,HEIF,%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,HEIF,%yr_A%);

        *      -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *         shares from N2O Manure Management Miterra, IPCC 2006)
        *
          p_animReq(RS,HEIF,A,"NEA" %addtimedim%)  $ p_technFact(RS,HEIF,"LEVL",A)
            =  ( p_meanLiveWgt(RS,HEIF,%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"))/365 * p_fatngDays(RS,HEIF,%yr_A%);


          p_animReq(RS,HEIF,A,"ENNE" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = SUM(SUBENE, p_animReq(RS,HEIF,A,SUBENE %addtimedim%));

        * --- take mean dry matter intake from above and derive min and max

          p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) = p_dataCopy(RS,HEIF,"DRMN",%yr_A%);
          p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) * 0.9;
          p_animReq(RS,HEIF,A,"DRMX" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,HEIF,A,"FICT" %addtimedim%) $ p_technFact(RS,HEIF,"LEVL",A) = p_animReq(RS,HEIF,A,"DRMX" %addtimedim%);
        *
        * ---- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,HEIF,%yr_A% %addtimedim%) = p_fatngDays(RS,HEIF,%yr_A%)      ;

    Departures from CAPRI: none."""
    drmn = {}
    for r in st.RS:
        for a in HEIF:
            for t in st.techs(r, a):
                w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
                drmn[(r, a, t)] = ((0.029 - 0.00001914 * w) * w) * n
                if st.dc(r, a, "LEVL"):
                    st.p_crprReq[(r, a, t)] = (0.1602 - 0.0001228 * w) * drmn[(r, a, t)]
                _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, n))
                _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
                _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")) / 365 * n)
                _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
        for a in HEIF:
            for t in A_ALL:
                if (r, a, t) in drmn:
                    _set_req(st, r, a, t, "DRMN", drmn[(r, a, t)])
            for t in st.techs(r, a):
                _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.9)
                _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
                _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
            for t in A_ALL:
                if (r, a, t) in st.p_fatngDays:
                    st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]


# ------------------------------------------------------------------ (7) heifers raising
def HEIR_growth(st: ReqState) -> None:
    r"""Raised heifers: the mean live weight (halfway from 300 kg to the adult female's), the raising days (the
    member state's, within CAPRI's limits) and the daily gain.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 915-927):

          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
            = (( p_startWgt("HEIR") + p_femWgt(RS,%yr_A%) ) / 2 );
          p_meanLiveWgt(RS,"HEIR",%yr_A%) $ (%p_condition%(RS,"HEIR","LEVL",%yr_A%) $ (NOT p_meanLiveWgt(RS,"HEIR",%yr_A%)))
            = (p_startWgt("HEIR") + 575.)/2;
        *
          p_fatngDays(RS,"HEIR",%yr_A%)  $ %p_condition%(RS,"HEIR","LEVL",%yr_A%)
        *       Max days are 2 years (heifers reclassified as cows), min days are 10 months or a calving age of 12+10=22 months
            =  MIN(p_reqfcnlim("HEIR","DAYS","up"),
                   MAX(p_reqfcnlim("HEIR","DAYS","lo"),
                       SUM(R_RAGG(RS,MS),p_dataCopy(MS,"HEIR","DAYS",%yr%)))) ;
        *
          p_dailyWgtIncrease(RS,"HEIR",%yr_A%) $ p_fatngDays(RS,"HEIR",%yr_A%)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)  - p_startWgt("HEIR") ) / p_fatngDays(RS,"HEIR",%yr_A%);

    Departures from CAPRI: none."""
    a = "HEIR"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + st.p_femWgt[(r, t)]) / 2
            if not st.p_meanLiveWgt[(r, a, t)]:
                st.p_meanLiveWgt[(r, a, t)] = (st.p_startWgt[a] + 575.) / 2
        for t in st.techs(r, a):
            st.p_fatngDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"),
                                                                         st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))
        for t in A_ALL:
            if st.g(st.p_fatngDays, r, a, t):
                st.p_dailyWgtIncrease[(r, a, t)] = ((st.g(st.p_meanLiveWgt, r, a, t) - st.p_startWgt[a])
                                                    / st.p_fatngDays[(r, a, t)])


def HEIR_requirements(st: ReqState) -> None:
    r"""Raised heifers: the crude protein, the net energy for growth (over the year), maintenance and activity, the
    total, the dry matter and intake capacity, and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 937-975):

          p_crprReq(RS,"HEIR",A,%yr%) $ (p_dataCopy(RS,"HEIR","LEVL",%yr%)*p_technFact(RS,"HEIR","LEVL",A))
            = ( 0.00127 * p_meanLiveWgt(RS,"HEIR",%yr_A%) + 0.00024 * p_dailyWgtIncrease(RS,"HEIR",%yr_A%) * 1000. + 0.1273 )
             * p_fatngDays(RS,"HEIR",%yr_A%);
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

        *     -- Calculation of Net energy for growth according to IPCC 2006 (Eq. 10.6)

          p_animReq(RS,"HEIR",A,"NEG" %addtimedim%)  $ p_technFact(RS,"HEIR","LEVL",A)
            =  22.02 * (p_meanLiveWgt(RS,"HEIR",%yr_A%) / (p_coeffEnergyForGrowth("HEIR") * p_femWgt(RS,%yr_A%)))**0.75
                     * (p_dailyWgtIncrease(RS,"HEIR",%yr_A%)**(1.097)) * 365.;

        *     -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

          p_animReq(RS,"HEIR",A,"NEM" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A)
            = ( p_meanLiveWgt(RS,"HEIR",%yr_A%)**0.75 * 0.322) * p_fatngDays(RS,"HEIR",%yr_A%);

        *     -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *        shares from N2O Manure Management Miterra, IPCC 2006)

          p_animReq(RS,"HEIR",A,"NEA" %addtimedim%)  $ p_technFact(RS,"HEIR","LEVL",A)
            =  ( p_meanLiveWgt(RS,"HEIR",%yr_A%)**0.75 * 0.322)* 0.17
             * (365-p_rcEmissions(RS,"OCOW_L","HD"));
        *
          p_animReq(RS,"HEIR",A,"ENNE" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = SUM(SUBENE, p_animReq(RS,"HEIR",A,SUBENE %addtimedim%));
        *
        *     -- dry matter stuff is from CAPRI working paper 97-12

          p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A)
            = (1.7770 + 0.0167 * p_meanLiveWgt(RS,"HEIR",%yr_A%) ) * p_fatngDays(RS,"HEIR",%yr_A%);
          P_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) * 0.9;
          p_animReq(RS,"HEIR",A,"DRMX" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMN" %addtimedim%) * 1.5;
          p_animReq(RS,"HEIR",A,"FICT" %addtimedim%) $ p_technFact(RS,"HEIR","LEVL",A) = p_animReq(RS,"HEIR",A,"DRMX" %addtimedim%);
        *
        * ---- total production days for conversion of requirements into daily values:

          p_animProdDays(RS,"HEIR",%yr_A% %addtimedim%) = p_fatngDays(RS,"HEIR",%yr_A%)      ;

    Departures from CAPRI: none."""
    a = "HEIR"
    for r in st.RS:
        for t in st.techs(r, a):
            w, d, n = st.p_meanLiveWgt[(r, a, t)], st.g(st.p_dailyWgtIncrease, r, a, t), st.p_fatngDays[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = (0.00127 * w + 0.00024 * d * 1000. + 0.1273) * n
            _set_req(st, r, a, t, "NEG", _neg(st, w, a, st.p_femWgt[(r, t)], d, 365.))
            _set_req(st, r, a, t, "NEM", (w ** 0.75 * 0.322) * n)
            _set_req(st, r, a, t, "NEA", (w ** 0.75 * 0.322) * 0.17 * (365 - st.rc(r, "OCOW_L", "HD")))
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, s) for s in SUBENE))
            _set_req(st, r, a, t, "DRMN", (1.7770 + 0.0167 * w) * n)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMN") * 0.9)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FICT", st.req(r, a, t, "DRMX"))
        for t in A_ALL:
            if (r, a, t) in st.p_fatngDays:
                st.p_animProdDays[(r, a, t)] = st.p_fatngDays[(r, a, t)]


# ------------------------------------------------------------------ (8) sows
def SOWS_requirements(st: ReqState) -> None:
    r"""Sows: the crude protein, the production days (365), the metabolisable energy for pigs, the dry matter,
    lysine and the minimum and maximum dry matter, per sow and its piglets.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1000-1021):

          p_crprReq(RS,"SOWS",A,%yr%) $ (p_dataCopy(RS,"SOWS","LEVL",%yr%)*p_technFact(RS,"SOWS","LEVL",A))
            = 101.71 + 46.5 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.)* 5.7;
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

          p_animProdDays(RS,"SOWS",%yr_A% %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)= 365. ;
        *
          p_animReq(RS,"SOWS",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = 0;
          p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 8219.75  +  3703.2 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%)*(p_technFact(RS,"SOWS","YPIG",A)+1.) * 404.75;
        *
          p_animReq(RS,"SOWS",A,"DRMA" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 610.35 + 261 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) *(p_technFact(RS,"SOWS","YPIG",A)+1.) * 26.1;
        *
          p_animReq(RS,"SOWS",A,"LISI" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A)
            = 0.610 + 0.372 + 0.001*p_dataCopy(RS,"SOWS","YPIG",%yr%) * (p_technFact(RS,"SOWS","YPIG",A)+1.)* 0.074;
        *
          p_animReq(RS,"SOWS",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) / 14.82 ;
        *
          p_animReq(RS,"SOWS",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SOWS","LEVL",A) = p_animReq(RS,"SOWS",A,"ENMP" %addtimedim%) / 13.47 ;

    Departures from CAPRI: none."""
    a = "SOWS"
    for r in st.RS:
        for t in st.techs(r, a):
            yp = 0.001 * st.dc(r, a, "YPIG") * (st.tf(r, a, "YPIG", t) + 1.)
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = 101.71 + 46.5 + yp * 5.7
            st.p_animProdDays[(r, a, t)] = 365.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMP", 8219.75 + 3703.2 + yp * 404.75)
            _set_req(st, r, a, t, "DRMA", 610.35 + 261 + yp * 26.1)
            _set_req(st, r, a, t, "LISI", 0.610 + 0.372 + yp * 0.074)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "ENMP") / 14.82)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "ENMP") / 13.47)


# ------------------------------------------------------------------ (9) pig fattening
#: CAPRI's switch between its low and high final-weight requirement tables (l. 1048: 0, the high table always)
SwitchLiveWgt = 0


def PIGF_requirements(st: ReqState) -> None:
    r"""Fattened pigs: the final live weight (the carcass over its share, at least just above the lightest weight
    class of CAPRI's tables), the fattening days, the crude protein (the classes' sum, plus 15%), the other
    requirements summed over the weight classes up to the final weight, and the production days (the member state's).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1038-1127):

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


          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtLo $ (     (p_pigsReqLowWgt(porkFinWgtLo,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW") > p_startWgt("PIGF"))   ), p_pigsReqLowWgt(porkFinWgtLo,"XDUF"));
        *
          p_fatngDays(RS,"PIGF",%yr_A%) $ ((p_finalLiveWgt(RS,"PIGF",%yr_A%) GE  %SwitchLiveWgt%) $ p_finalLiveWgt(RS,"PIGF",%yr_A%) )
            = SMAX(porkFinWgtHi $ (     (p_pigsReqHighWgt(porkFinWgtHi,"XALW") < p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                      $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW") > p_startWgt("PIGF"))  ), p_pigsReqHighWgt(porkFinWgtHi,"XDUF"));
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"PIGF",curRows,%yr%) $ p_dataCopy(RS,"PIGF","LEVL",%yr%)
            = p_NutContManureKgM3("PIGF",curRows) * p_fatngDays(RS,"PIGF",%yr_A%)
                            * (p_finalLiveWgt(RS,"PIGF",%yr_A%)-p_startWgt("PIGF")) * 0.5;
        $endif

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
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni.req1 %req% ==on

          p_animReq(RS,"PIGF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"PIGF","LEVL",A) = 0;

        *     -- requirements for pig with final weight < threshold

          p_animReq(RS,"PIGF",A,REQSC %addtimedim%) $ (  p_technFact(RS,"PIGF","LEVL",A)
                                         $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) LT %SwitchLiveWgt%)
                                         $ p_finalLiveWgt(RS,"PIGF",%yr_A%)
                                         $ (not sameas("CRPR",REQSC)))
            = SUM(porkFinWgtLo $ ( (p_pigsReqLowWgt(porkFinWgtLo,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqLowWgt(porkFinWgtLo,"XALW")>p_startWgt("PIGF")) ),  p_pigsReqLowWgt(porkFinWgtLo,REQSC));

        *     -- requirements for pig with final weight > threshold

          p_animReq(RS,"PIGF",A,REQSC %addtimedim%) $ (  p_technFact(RS,"PIGF","LEVL",A)
                                         $ (p_finalLiveWgt(RS,"PIGF",%yr_A%) GE %SwitchLiveWgt%)
                                         $ p_finalLiveWgt(RS,"PIGF",%yr_A%)
                                         $ (not sameas("CRPR",REQSC)))
            = SUM(porkFinWgtHi $ ( (p_pigsReqHighWgt(porkFinWgtHi,"XALW")<p_finalLiveWgt(RS,"PIGF",%yr_A%))
                                 $ (p_pigsReqHighWgt(porkFinWgtHi,"XALW")>p_startWgt("PIGF")) ), p_pigsReqHighWgt(porkFinWgtHi,REQSC));
        *
        *     -- total production days for conversion of requirements into daily values:
        *        pw091111 NOTE: These are taken from COCO, rather than from the tables,
        *        because the fattening days from the tables are in conflict with statistical information.
        *        Thus we accept some inconsistency between the fattening days implicit in the requirement calculation (Italian tables)
        *        and the production days used to convert between total and daily values. The latter are based on statistics,
        *        because they will also serve to convert between LEVL and HERD.
        *
        *pw  p_animProdDays(RS,"PIGF",%yr_A%) $ p_technFact(RS,"PIGF","LEVL",A) = MAX(p_fatngDays(RS,"PIGF",A),10);
          p_animProdDays(RS,"PIGF",%yr_A% %addtimedim%) $ p_technFact(RS,"PIGF","LEVL",A)
            = MAX(SUM(R_RAGG(RS,MS),p_dataCopy(MS,"PIGF","DAYS",%yr%)),
                  p_reqfcnlim("PIGF","DAYS","lo"));

    Without CAPRI's tables (dat/feed/porkreq.gms) the fattened pigs are left out (ReqState.not_computed).
    Departures from CAPRI: none."""
    a = "PIGF"
    if not (st.p_pigsReqLowWgt and st.p_pigsReqHighWgt):
        st.not_computed.add(a)
        return
    start = st.p_startWgt[a]
    lo = min((v for (c, k), v in st.p_pigsReqLowWgt.items() if k == "XALW" and v > start), default=0.0) + .1
    hi = min((v for (c, k), v in st.p_pigsReqHighWgt.items() if k == "XALW" and v > start), default=0.0) + .1

    def classes(table, f):
        return [c for (c, k), v in table.items() if k == "XALW" and start < v < f]
    items = sorted({k for (_, k) in st.p_pigsReqHighWgt} | {k for (_, k) in st.p_pigsReqLowWgt})
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_finalLiveWgt[(r, a, t)] = st.dc(r, a, "PORK") * (st.tf(r, a, "PORK", t) + 1.) / st.p_carcassShare[a]
        for t in A_ALL:
            st.p_finalLiveWgt[(r, a, t)] = max(st.g(st.p_finalLiveWgt, r, a, t), lo, hi)
        for t in A_ALL:
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            st.p_fatngDays[(r, a, t)] = max((table[(c, "XDUF")] for c in classes(table, f)), default=0.0)
        for t in st.techs(r, a):
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = sum(table[(c, "CRPR")] for c in classes(table, f))
        for t in A_ALL:
            if st.g(st.p_crprReq, r, a, t):
                st.p_crprReq[(r, a, t)] = st.p_crprReq[(r, a, t)] * 1.15
        for t in st.techs(r, a):
            _set_req(st, r, a, t, "ENNE", 0)
        for t in st.techs(r, a):
            f = st.p_finalLiveWgt[(r, a, t)]
            table = st.p_pigsReqLowWgt if f < SwitchLiveWgt else st.p_pigsReqHighWgt
            for item in REQSC:
                if item == "CRPR":
                    continue
                _set_req(st, r, a, t, item, sum(table.get((c, item), 0.0) for c in classes(table, f)))
        for t in st.techs(r, a):
            st.p_animProdDays[(r, a, t)] = max(st.ms_sum(r, lambda m: st.dc(m, a, "DAYS")), st.lim(a, "DAYS", "lo"))
    del items


# ------------------------------------------------------------------ (10) hens
def HENS_requirements(st: ReqState) -> None:
    r"""Laying hens (per 1000 hens): the mean live weight 1.9 kg, the crude protein, the production days, the egg
    yield per day, the metabolisable energy for chicken, the dry matter, lysine and the minimum and maximum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1137-1175):

          p_meanLiveWgt(RS,"HENS",%yr_A%) $ %p_condition%(RS,"HENS","LEVL",%yr_A%)  = 1.9;

        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"HENS",curRows,%yr%) $ p_dataCopy(RS,"HENS","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_meanLiveWgt(RS,"HENS",%yr_A%) * 365. * 1000.;
        $endif

        * --- ... and nitrogen
        *         NOTE: This should equal:  p_animReq(RS,"HENS",A,"ENMC") / 11.1 * 0.14 ;
          p_crprReq(RS,"HENS",A,%yr%) $ (p_dataCopy(RS,"HENS","LEVL",%yr%)*p_technFact(RS,"HENS","LEVL",A))
            = ( 0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75 + 0.57 * (p_dataCopy(RS,"HENS","EGGS",%yr%)/57.)/365.)*365.*1000./11.1*0.14;
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on

          p_animProdDays(RS,"HENS",%yr_A% %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = 365;

        *     -- average eggs weight (57 gr.)

          p_eggYield(RS,A) $ p_technFact(RS,"HENS","LEVL",A) = (p_dataCopy(RS,"HENS","EGGS",%yr%)*(p_technFact(RS,"HENS","EGGS",A)+1.) / 57.) / 365. ;
        *
        *     -- Requirement from Kirchgessner 7th ed, p. 453

          p_animReq(RS,"HENS",A,"ENNE" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = 0;
          p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A)
             = (  0.46 * p_meanLiveWgt(RS,"HENS",%yr_A%)**0.75
        *         - 1 MJ / 100 g eqq => 0.57 MJ / 57 g egg as assumed above
                + 0.57 * p_eggYield(RS,%yr_A%)  ) * 365. * 1000. ;
        *
          p_animReq(RS,"HENS",A,"DRMA" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) / 12. ;
        *
        *     -- mg of lysine
          p_animReq(RS,"HENS",A,"LISI" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) =
                            0.0095 * p_dataCopy(RS,"HENS","EGGS",%yr%)*(p_technFact(RS,"HENS","EGGS",A)+1.) + 60. * 1.9 ;
        *
          p_animReq(RS,"HENS",A,"DRMN" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) / 15.0 ;
        *
          p_animReq(RS,"HENS",A,"DRMX" %addtimedim%) $ p_technFact(RS,"HENS","LEVL",A) = p_animReq(RS,"HENS",A,"ENMC" %addtimedim%) /  8.0 ;

    Departures from CAPRI: none."""
    a = "HENS"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = 1.9
        for t in st.techs(r, a):
            w = st.p_meanLiveWgt[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = (0.46 * w ** 0.75 + 0.57 * (st.dc(r, a, "EGGS") / 57.) / 365.) \
                    * 365. * 1000. / 11.1 * 0.14
            st.p_animProdDays[(r, a, t)] = 365
            st.p_eggYield[(r, t)] = (st.dc(r, a, "EGGS") * (st.tf(r, a, "EGGS", t) + 1.) / 57.) / 365.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMC", (0.46 * w ** 0.75 + 0.57 * st.p_eggYield[(r, t)]) * 365. * 1000.)
            _set_req(st, r, a, t, "DRMA", st.req(r, a, t, "ENMC") / 12.)
            _set_req(st, r, a, t, "LISI", 0.0095 * st.dc(r, a, "EGGS") * (st.tf(r, a, "EGGS", t) + 1.) + 60. * 1.9)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "ENMC") / 15.0)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "ENMC") / 8.0)


# ------------------------------------------------------------------ (11) poultry fattening
def POUF_requirements(st: ReqState) -> None:
    r"""Poultry fattening (per 1000 places): the mean live weight (half the final weight, at least 250 g), the
    production days (the member state's, within CAPRI's limits), the crude protein, the dry matter, the
    metabolisable energy for chicken, lysine and the minimum and maximum dry matter.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1186-1239):

          p_meanLiveWgt(RS,"POUF",%yr_A%) $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
            = MAX(  p_dataCopy(RS,"POUF","POUM",%yr%)*0.001
        $iftheni %req% ==on
                  *(p_technFact(RS,"POUF","POUM",A)+1.)
        $endif
        *           average wgt = final wgt * 0.5, as iniital wgt is near zero
                  / p_carcassShare("POUF") * 0.5,
        *        ... but at least 250g
                 0.25) ;
        *
        *        Max days are about 150 days (turkeys including some empty days), min days are about 30 days (broilers)
          p_animProdDays(RS,"POUF",%yr_A% %addtimedim%)  $ %p_condition%(RS,"POUF","LEVL",%yr_A%)
                = MIN(p_reqfcnlim("POUF","DAYS","up"),
                      MAX(p_reqfcnlim("POUF","DAYS","lo"),
                          SUM(R_RAGG(RS,MS),p_dataCopy(MS,"POUF","DAYS",%yr%)))) ;
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"POUF",curRows,%yr%) $ p_dataCopy(RS,"POUF","LEVL",%yr%)
            = p_NutContManureKgM3("POULTRY",curRows) * p_animProdDays(RS,"POUF",%yr_A% %addtimedim%) * p_meanLiveWgt(RS,"POUF",%yr_A%) * 1000.;
        $endif

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
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni %req% ==on
        *
        *     -- dry matter need according to paper 97-12
        *        (matches rule of thumb that intake is about twice the final weight)
        *
          p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)
            = 1.6463 * ((p_meanLiveWgt(RS,"POUF",%yr_A%)*2.0)**1.3023) * 0.87 * 1000;
        *
        *      -- assume that the energy need is covered with a mix of 80% wheat and 20% soy cake
        *         (replaces the assumption of 19% from paper 97-12)
          p_animReq(RS,"POUF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A) = 0;
        *
          p_animReq(RS,"POUF",A,"ENMC" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%)/0.89 * 12.392;
        *
          p_animReq(RS,"POUF",A,"LISI" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_crprReq(RS,"POUF",A,%yr%) * 0.011 ;
        *
          p_animReq(RS,"POUF",A,"DRMN" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) * 0.8;
        *
          p_animReq(RS,"POUF",A,"DRMX" %addtimedim%) $ p_technFact(RS,"POUF","LEVL",A)  = p_animReq(RS,"POUF",A,"DRMA" %addtimedim%) * 1.2 ;

    Departures from CAPRI: none."""
    a = "POUF"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_meanLiveWgt[(r, a, t)] = max(st.dc(r, a, "POUM") * 0.001 * (st.tf(r, a, "POUM", t) + 1.)
                                              / st.p_carcassShare[a] * 0.5, 0.25)
            st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(st.lim(a, "DAYS", "lo"),
                                                                            st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))
        for t in st.techs(r, a):
            w = st.p_meanLiveWgt[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = ((1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
                                           * (0.23 - 0.04 * max(0, w - 0.50)) / 0.87)
            _set_req(st, r, a, t, "DRMA", 1.6463 * ((w * 2.0) ** 1.3023) * 0.87 * 1000)
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENMC", st.req(r, a, t, "DRMA") / 0.89 * 12.392)
            _set_req(st, r, a, t, "LISI", st.g(st.p_crprReq, r, a, t) * 0.011)
            _set_req(st, r, a, t, "DRMN", st.req(r, a, t, "DRMA") * 0.8)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMA") * 1.2)


# ------------------------------------------------------------------ (12) sheep and goats for milk
def SHGM_growth(st: ReqState) -> None:
    r"""Sheep and goats for milk: the goats' share of the member state's herds, the ewes', goats' and the activity's
    mean live weights, and the milk per milking day.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1250-1272):

          p_sharGoatHerd(RS,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            = SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)
                               /(p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)))
                 $      SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%))
             +0.1
                 $ (NOT SUM(R_RAGG(RS,MS), p_dataCopy(MS,"GOAT","HERD",%yr%)+p_dataCopy(MS,"SHEP","HERD",%yr%)));
        *
        * --- average live weights and milk yields
        *
          p_meanLiveWgt(RS,"EWES",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 55. ;
          p_meanLiveWgt(RS,"GOAT",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) = 60. ;
        *
          p_meanLiveWgt(RS,"SHGM",%yr_A%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%)
            = p_meanLiveWgt(RS,"EWES",%yr_A%) * (1-p_sharGoatHerd(RS,%yr%))
             +p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_sharGoatHerd(RS,%yr%) ;
        *
        *  --- ewes milk production period is ususally 140 - 220 days. Assumed average: 170 days

           p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)  $ %p_condition%(RS,"SHGM","LEVL",%yr_A%) =
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMI",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMI",%yr%) / 170. +
        $ifi %req% ==on (p_technFact(RS,"SHGM","SGMF",A)+1.) *
                         p_dataCopy(RS,"SHGM","SGMF",%yr%) / 170.;

    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        if st.dc(r, a, "LEVL"):
            tot = st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))
            st.p_sharGoatHerd[r] = (st.ms_sum(r, lambda m: st.dc(m, "GOAT", "HERD")
                                              / (st.dc(m, "GOAT", "HERD") + st.dc(m, "SHEP", "HERD"))) if tot else 0.0) \
                + (0.1 if not tot else 0.0)
        for t in st.techs(r, a):
            s = st.g(st.p_sharGoatHerd, r)
            st.p_meanLiveWgt[(r, "EWES", t)] = 55.
            st.p_meanLiveWgt[(r, "GOAT", t)] = 60.
            st.p_meanLiveWgt[(r, a, t)] = 55. * (1 - s) + 60. * s
            st.p_milkPerDay[(r, a, t)] = ((st.tf(r, a, "SGMI", t) + 1.) * st.dc(r, a, "SGMI") / 170.
                                          + (st.tf(r, a, "SGMF", t) + 1.) * st.dc(r, a, "SGMF") / 170.)


def SHGM_crude_protein(st: ReqState) -> None:
    r"""Sheep and goats for milk: the ewes' and goats' crude-protein requirements (maintenance, milking, the last
    mating period) and the activity's, by the goats' share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1283-1304):

          p_crprReq(RS,"EWES",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
            =   ( 0.026 + 0.0014 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *     -- for milk production
              + ( 0.0634 + 0.0012 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.0895 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( ( 2.22 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 19.88) * 1.35 ) * 60. / 1000. ;
        *

          p_crprReq(RS,"GOAT",A,%yr%) $ (p_dataCopy(RS,"SHGM","LEVL",%yr%)*p_technFact(RS,"SHGM","LEVL",A))
        *     -- for maintenance
        *        NOTE: the maintenance component of phases (1) + (2) is aggregated for GOAT: 135+170=305 days
            = ( ( 12.66 + 0.8 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *     -- for milk production
              + ( 61. * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *     -- for last mating period
              + ( 1.425 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 14.666) * 60. ) / 1000. ;
        *
          p_crprReq(RS,"SHGM",A,%yr%) $ p_dataCopy(RS,"SHGM","LEVL",%yr%)
            =   (  p_crprReq(RS,"GOAT",A,%yr%) * p_sharGoatHerd(RS,%yr%)
                 + p_crprReq(RS,"EWES",A,%yr%) * (1-p_sharGoatHerd(RS,%yr%)))
                                        ;

    As GAMS's precedence reads the ewes' statement, only the last period's term is divided by 1000.
    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        if not st.dc(r, a, "LEVL"):
            continue
        for t in st.techs(r, a):
            we, wg, m = st.p_meanLiveWgt[(r, "EWES", t)], st.p_meanLiveWgt[(r, "GOAT", t)], st.p_milkPerDay[(r, a, t)]
            st.p_crprReq[(r, "EWES", t)] = ((0.026 + 0.0014 * we) * 135.
                                            + (0.0634 + 0.0012 * we + 0.0895 * m) * 170.
                                            + ((2.22 * we - 19.88) * 1.35) * 60. / 1000.)
            st.p_crprReq[(r, "GOAT", t)] = ((12.66 + 0.8 * wg) * 305. + (61. * m) * 170.
                                            + (1.425 * wg + 14.666) * 60.) / 1000.
        s = st.g(st.p_sharGoatHerd, r)
        for t in A_ALL:
            st.p_crprReq[(r, a, t)] = (st.g(st.p_crprReq, r, "GOAT", t) * s + st.g(st.p_crprReq, r, "EWES", t) * (1 - s))


def SHGM_requirements(st: ReqState) -> None:
    r"""Sheep and goats for milk: the production days (365); the ewes' and goats' net energy for maintenance,
    activity (MITERRA's housing days) and lactation, their totals and minimum dry matter; the activity's by the goats'
    share; its maximum dry matter and intake capacity; the ewes' and goats' entries erased.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1310-1396):

                    p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = 365;
        *
        *
        *           --- requirements for ewes

        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)
        *                  NOTE (pw121011) This was mistakenly deleted in the old trunk at some point and also neglected in the new trunk!
                    p_animReq(RS,"EWES",A,"NEM" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      =  ( p_meanLiveWgt(RS,"EWES",%yr_A%)**0.75 * 0.217) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture,
        *                  shares from N2O Manure Management Miterra, IPCC 2006)
                    p_animReq(RS,"EWES",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      =  p_meanLiveWgt(RS,"EWES",%yr_A%) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%)
                       *   ( (365-p_rcEmissions(RS,"SHEGOA","HD"))* 0.0107
                            + p_rcEmissions(RS,"SHEGOA","HD") * 0.009)/365;

        *               -- net energy for lactation (from IPCC: NEl, EVmilk=4.6 MJ/kg) multiplied with milk production days (=170)

                    p_animReq(RS,"EWES",A,"NEL" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) =  ( 4.6 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.;
        *
                    p_animReq(RS,"EWES",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE, p_animReq(RS,"EWES",A,SUBENE %addtimedim%));
        *
        *               -- DRMN is added up from 3 phases: (1) only maintenance = 135 days (2) milking = 170 days (3) final mating = 60 days

                    p_animReq(RS,"EWES",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
        *                  - for maintenance
                      = ( ( ( 0.36 + 0.023 * p_meanLiveWgt(RS,"EWES",%yr_A%)) * 135.
        *                  - for milk production
                        + ( 1.112 + 0.0187 * p_meanLiveWgt(RS,"EWES",%yr_A%) + 0.279 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.
        *                  - for last mating period
                        + ( 0.0268 * p_meanLiveWgt(RS,"EWES",%yr_A%) - 0.24) * 60. ) );
        *
        *
        *           --- requirements for goats
        *
        *               -- net energy for maintenance (from IPCC: NEm=Cfi*(Weight)**0.75, IPCC 2006)

                    p_animReq(RS,"GOAT",A,"NEM" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_meanLiveWgt(RS,"GOAT",%yr_A%)**0.75 * 0.217) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%);

        *               -- net energy for activity (from IPCC: NEa, Ca: Stall/Pasture, shares from N2O Manure Management Miterra, IPCC 2006)

                    p_animReq(RS,"GOAT",A,"NEA" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                       =  p_meanLiveWgt(RS,"GOAT",%yr_A%) * p_animProdDays(RS,"SHGM",%yr_A% %addtimedim%)
                        * (  (365-p_rcEmissions(RS,"SHEGOA","HD"))* 0.0107
                           + p_rcEmissions(RS,"SHEGOA","HD") * 0.009)/365;

        *               -- net energy for lactation (from IPCC: NEl, EVmilk=4.6 MJ/kg) multiplied with milk production days (=170)

                    p_animReq(RS,"GOAT",A,"NEL" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) =  ( 4.6 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%)) * 170.;
        *
                    p_animReq(RS,"GOAT",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE,p_animReq(RS,"GOAT",A,SUBENE %addtimedim%));
        *
        *               -- DRMN is added up from 3 phases: (1) only maintenance = 135 days (2) milking = 170 days (3) final mating = 60 days
        *                  NOTE: the maintenance component of phases (1) + (2) is aggregated: 135+170=305 days
        *
                    p_animReq(RS,"GOAT",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A)
        *                  - for maintenance
                       = ( ( ( 0.55 + 0.013 * p_meanLiveWgt(RS,"GOAT",%yr_A%)) * 305.
        *                  - for milk production
                          +  0.3 * p_milkPerDay(RS,"SHGM",%yr_A% %addtimedim%) * 170.
        *                  - for last mating period
                          + ( 0.0122 * p_meanLiveWgt(RS,"GOAT",%yr_A%) + 0.5316) * 60. ) );
        *
        *
        *           --- aggregation to SHGM
        *
                    p_animReq(RS,"SHGM",A,REQSC %addtimedim%)   $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_animReq(RS,"GOAT",A,REQSC %addtimedim%) * p_sharGoatHerd(RS,%yr%)
                       +  p_animReq(RS,"EWES",A,REQSC %addtimedim%) * (1-p_sharGoatHerd(RS,%yr%)));
        *
                    p_animReq(RS,"SHGM",A,SUBENE %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A)
                      = ( p_animReq(RS,"GOAT",A,SUBENE %addtimedim%) * p_sharGoatHerd(RS,%yr%)
                       +  p_animReq(RS,"EWES",A,SUBENE %addtimedim%) * (1-p_sharGoatHerd(RS,%yr%)));


                    p_animReq(RS,"SHGM",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = 0;
                    p_animReq(RS,"SHGM",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = SUM(SUBENE, p_animReq(RS,"SHGM",A,SUBENE %addtimedim%));
        *
                    p_animReq(RS,"SHGM",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = p_animReq(RS,"SHGM",A,"DRMN" %addtimedim%) * 1.5;
                    p_animReq(RS,"SHGM",A,"FISM" %addtimedim%) $ p_technFact(RS,"SHGM","LEVL",A) = ( 120. * p_meanLiveWgt(RS,"SHGM",%yr_A%) ** 0.75 ) / 1000. * 365.;
        *
                    p_animReq(RS,"GOAT",A,REQSC %addtimedim%)  = 0;
                    p_animReq(RS,"GOAT",A,SUBENE %addtimedim%) = 0;
                    p_animReq(RS,"EWES",A,REQSC %addtimedim%)  = 0;
                    p_animReq(RS,"EWES",A,SUBENE %addtimedim%) = 0;

    Departures from CAPRI: none."""
    a = "SHGM"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_animProdDays[(r, a, t)] = 365
            n, m, hd = st.p_animProdDays[(r, a, t)], st.p_milkPerDay[(r, a, t)], st.rc(r, "SHEGOA", "HD")
            for x, k in (("EWES", 0.217), ("GOAT", 0.217)):
                w = st.p_meanLiveWgt[(r, x, t)]
                _set_req(st, r, x, t, "NEM", (w ** 0.75 * k) * n)
                _set_req(st, r, x, t, "NEA", w * n * ((365 - hd) * 0.0107 + hd * 0.009) / 365)
                _set_req(st, r, x, t, "NEL", (4.6 * m) * 170.)
                _set_req(st, r, x, t, "ENNE", sum(st.req(r, x, t, s) for s in SUBENE))
            we, wg = st.p_meanLiveWgt[(r, "EWES", t)], st.p_meanLiveWgt[(r, "GOAT", t)]
            _set_req(st, r, "EWES", t, "DRMN", ((0.36 + 0.023 * we) * 135.
                                                + (1.112 + 0.0187 * we + 0.279 * m) * 170.
                                                + (0.0268 * we - 0.24) * 60.))
            _set_req(st, r, "GOAT", t, "DRMN", ((0.55 + 0.013 * wg) * 305.
                                                + 0.3 * m * 170.
                                                + (0.0122 * wg + 0.5316) * 60.))
        s = st.g(st.p_sharGoatHerd, r)
        for t in st.techs(r, a):
            for item in REQSC + SUBENE:
                g_, e_ = st.req(r, "GOAT", t, item), st.req(r, "EWES", t, item)
                if (r, "GOAT", t, item) in st.p_animReq or (r, "EWES", t, item) in st.p_animReq \
                        or (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, g_ * s + e_ * (1 - s))
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, x) for x in SUBENE))
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FISM", (120. * st.p_meanLiveWgt[(r, a, t)] ** 0.75) / 1000. * 365.)
    for k in [k for k in st.p_animReq if k[1] in ("EWES", "GOAT")]:
        del st.p_animReq[k]


# ------------------------------------------------------------------ (13) sheep and goats fattening
def SHGF_requirements(st: ReqState) -> None:
    r"""Sheep and goats fattening: the daily gain (g, the member state's within CAPRI's limits), the fattening days,
    the mean live weight, the crude protein, the energy (from metabolisable energy for ruminants), the minimum and
    maximum dry matter, the intake capacity and the production days.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1407-1465):

          p_dailyWgtIncrease(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(p_reqfcnlim("SHGF","DAILY","up"),
                  MAX(p_reqfcnlim("SHGF","DAILY","lo"),
                      SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAILY",%yr%)))) ;

        * --- fattening period

          p_fatngDays(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
            = MIN(365. , MAX(10. ,( p_dataCopy(RS,"SHGF","SGMT",%yr%)/ p_carcassShare("SHGF") )
                                 /(p_dailyWgtIncrease(RS,"SHGF",%yr_A%)/1000.))) ;

        * --- average live weight

          p_meanLiveWgt(RS,"SHGF",%yr_A%)  $ %p_condition%(RS,"SHGF","LEVL",%yr_A%)
        *    Bounds as in coco1_anim:
            = MAX(8.,MIN(25.,p_dataCopy(RS,"SHGF","SGMT",%yr%)))/p_carcassShare("SHGF")/2.;
        *
        *
        * --- Excretions of potassium and phosphorus...
        $iftheni not %req% ==on
          p_dataCopy(RS,"SHGF",curRows,%yr%) $ p_dataCopy(RS,"SHGF","LEVL",%yr%)
            = p_NutContManureKgM3("CATTLE",curRows) * p_fatngDays(RS,"SHGF",%yr_A%) * p_meanLiveWgt(RS,"SHGF",%yr_A%);
        $endif

        * --- ... and nitrogen (copied below to CRPR if needed)
        *
          p_crprReq(RS,"SHGF",A,%yr%) $ (p_dataCopy(RS,"SHGF","LEVL",%yr%)*p_technFact(RS,"SHGF","LEVL",A))
            = ( ( 21.778 + 0.33 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.258 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%))
               * 1.35 * p_fatngDays(RS,"SHGF",%yr_A%)) / 1000.;
        *
        *
        * --- next group of statements only needed for energy, dry matter etc, but not excretions
        $iftheni.req15 %req% ==on
        *
        *            From http://www.gumpenstein.at/viehwirt/sachver.pdf, 040106 where it is clearly indicated that this is ME
        *            (gives higher requirement than the version commented out below), converted from ME into net energy lactation
        *
                    p_animReq(RS,"SHGF",A,"ENNE" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A) = 0;
                    p_animReq(RS,"SHGF",A,"ENNE" %addtimedim%)  $ p_technFact(RS,"SHGF","LEVL",A)
                         = (0.1596 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.0303 * p_dailyWgtIncrease(RS,"SHGF",%yr_A%) - 0.56)
        *                -- Assume 20% is from sucked SGMI:
                          * (1.- 0.2) * p_fatngDays(RS,"SHGF",%yr_A%) * p_convFactEnergyUnitsToEnne("ENMR");

                    p_animReq(RS,"SHGF",A,"DRMN" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = (0.038286 * p_meanLiveWgt(RS,"SHGF",%yr_A%) + 0.06381) * p_fatngDays(RS,"SHGF",%yr_A%) ;
        *
                    p_animReq(RS,"SHGF",A,"DRMX" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = p_animReq(RS,"SHGF",A,"DRMN" %addtimedim%) * 1.5;
        *
                    p_animReq(RS,"SHGF",A,"FISF" %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = ( 75. * p_meanLiveWgt(RS,"SHGF",%yr_A%)** 0.75 ) / 1000. * p_fatngDays(RS,"SHGF",%yr_A%);
        *
        *
        *               -- total production days for conversion of requirements into daily values (usually includes some empty days due to seasonality):
        *                  NOTE: Imposing additional wide constraints here is just a consistency check. Usually the bounds are set tighter in coco1_anim.
                    p_animProdDays(RS,"SHGF",%yr_A% %addtimedim%) $ p_technFact(RS,"SHGF","LEVL",A)
                      = MIN(p_reqfcnlim("SHGF","DAYS","up"),
                            MAX(p_reqfcnlim("SHGF","DAYS","lo"),
                                SUM(R_RAGG(RS,MS),p_dataCopy(MS,"SHGF","DAYS",%yr%)))) ;

    Departures from CAPRI: none."""
    a = "SHGF"
    for r in st.RS:
        for t in st.techs(r, a):
            st.p_dailyWgtIncrease[(r, a, t)] = min(st.lim(a, "DAILY", "up"), max(
                st.lim(a, "DAILY", "lo"), st.ms_sum(r, lambda m: st.dc(m, a, "DAILY"))))
            st.p_fatngDays[(r, a, t)] = min(365., max(10., (st.dc(r, a, "SGMT") / st.p_carcassShare[a])
                                                      / (st.p_dailyWgtIncrease[(r, a, t)] / 1000.)))
            st.p_meanLiveWgt[(r, a, t)] = max(8., min(25., st.dc(r, a, "SGMT"))) / st.p_carcassShare[a] / 2.
        for t in st.techs(r, a):
            w, d, n = st.p_meanLiveWgt[(r, a, t)], st.p_dailyWgtIncrease[(r, a, t)], st.p_fatngDays[(r, a, t)]
            if st.dc(r, a, "LEVL"):
                st.p_crprReq[(r, a, t)] = ((21.778 + 0.33 * w + 0.258 * d) * 1.35 * n) / 1000.
            _set_req(st, r, a, t, "ENNE", 0)
            _set_req(st, r, a, t, "ENNE", (0.1596 * w + 0.0303 * d - 0.56) * (1. - 0.2) * n
                     * st.p_convFactEnergyUnitsToEnne["ENMR"])
            _set_req(st, r, a, t, "DRMN", (0.038286 * w + 0.06381) * n)
            _set_req(st, r, a, t, "DRMX", st.req(r, a, t, "DRMN") * 1.5)
            _set_req(st, r, a, t, "FISF", (75. * w ** 0.75) / 1000. * n)
            st.p_animProdDays[(r, a, t)] = min(st.lim(a, "DAYS", "up"), max(
                st.lim(a, "DAYS", "lo"), st.ms_sum(r, lambda m: st.dc(m, a, "DAYS"))))


# ------------------------------------------------------------------ (14) other animals
def DATA_OANI_FOUT(st: ReqState) -> None:
    r"""Other animals: no manure output.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1472):

                     DATA(RS,"OANI",FOUT,%yr%) = 0;

    Departures from CAPRI: none."""
    for r in st.RS:
        for row in ("MANN", "MANP", "MANK"):
            st.DATA[(r, "OANI", row)] = 0


# ------------------------------------------------------------------ PART II: general assignments for requirements
def _techs_all(st):
    """(r, act, t) over the regions, CAPRI's animal activities and technologies."""
    return [(r, a, t) for r in st.RS for a in st.AACT for t in A_ALL]


def p_animReq_CRPR(st: ReqState) -> None:
    r"""The crude-protein requirement copied from p_crprReq, where the technology has a herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1482):

                    p_animReq(RS,AACT,A,"CRPR" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) = p_crprReq(RS,AACT,A,%yr%);

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "CRPR", st.g(st.p_crprReq, r, a, t))


def p_animReq_erase(st: ReqState) -> None:
    r"""The requirements erased where the technology has no herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1486):

                    p_animReq(RS,AACT,A,REQSR %addtimedim%) $ ( (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) EQ 0.) = 0.0;

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t) == 0.:
            for item in REQSR:
                if (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, 0.0)


def p_animReq_signs(st: ReqState) -> None:
    r"""The maximum requirements with their sign turned (minimum constraints in the supply model), the long fibre
    from the digestible fibre, and the maximum dry matter at least 1.2 times the minimum.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1491-1501):

                    p_animReq(RS,AACT,A,"DRMX" %addtimedim%) = - p_animReq(RS,AACT,A,"DRMX" %addtimedim%);
                    p_animReq(RS,AACT,A,"FICT" %addtimedim%) = - p_animReq(RS,AACT,A,"FICT" %addtimedim%);
                    p_animReq(RS,AACT,A,"FICO" %addtimedim%) = - p_animReq(RS,AACT,A,"FICO" %addtimedim%);
                    p_animReq(RS,AACT,A,"FISM" %addtimedim%) = - p_animReq(RS,AACT,A,"FISM" %addtimedim%);
                    p_animReq(RS,AACT,A,"FISF" %addtimedim%) = - p_animReq(RS,AACT,A,"FISF" %addtimedim%);

        *           --- long fiber needs derived from FIDI (see paper 97/12, p. 17)
                    p_animReq(RS,AACT,A,"FILG" %addtimedim%)  = p_animReq(RS,AACT,A,"FIDI" %addtimedim%)/3.;
        *
                    p_animReq(RS,AACT,A,"DRMX" %addtimedim%) $ p_animReq(RS,AACT,A,"DRMN" %addtimedim%)
                      = -MAX(ABS(p_animReq(RS,AACT,A,"DRMX" %addtimedim%)),ABS(p_animReq(RS,AACT,A,"DRMN" %addtimedim%))* 1.2);

    Departures from CAPRI: none."""
    for k in list(st.p_animReq):
        if k[3] in ("DRMX", "FICT", "FICO", "FISM", "FISF"):
            st.p_animReq[k] = - st.p_animReq[k]
    for (r, a, t, item) in list(st.p_animReq):
        if item == "FIDI":
            _set_req(st, r, a, t, "FILG", st.p_animReq[(r, a, t, "FIDI")] / 3.)
    for (r, a, t, item) in list(st.p_animReq):
        if item == "DRMN" and st.p_animReq[(r, a, t, item)]:
            _set_req(st, r, a, t, "DRMX", -max(abs(st.req(r, a, t, "DRMX")), abs(st.req(r, a, t, "DRMN")) * 1.2))


def p_animReq_ENNE(st: ReqState) -> None:
    r"""Every energy requirement rebased to net energy for lactation (ENNE), where the technology has a herd.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1506-1507):

                    p_animReq(RS,AACT,A,"ENNE" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A))
                      =  SUM(REQSE, p_animReq(RS,AACT,A,REQSE %addtimedim%) * p_convFactEnergyUnitsToEnne(REQSE) );

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "ENNE", sum(st.req(r, a, t, e) * st.p_convFactEnergyUnitsToEnne[e] for e in REQSE))


def p_animReq_per_day(st: ReqState) -> None:
    r"""The requirements per day instead of per head; the feeds' entries set to 1; the requirements erased where the
    technology has no share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1520-1529):

                    p_animReq(RS,AACT,A,REQSR %addtimedim%)  $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,REQSR %addtimedim%)/p_animProdDays(RS,AACT,%yr_A% %addtimedim%);
                    p_animReq(RS,AACT,A,SUBENE %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,SUBENE %addtimedim%)/p_animProdDays(RS,AACT,%yr_A% %addtimedim%);

                    p_animReq(RS,AACT,A,"Test" %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = p_animReq(RS,AACT,A,"Test" %addtimedim%) / p_animProdDays(RS,AACT,%yr_A% %addtimedim%);
        *
                    p_animReq(RS,AACT,A,FEED %addtimedim%)   $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = 1.0;
        *
                    p_animReq(RS,AACT,A,REQSR %addtimedim%)  $ (NOT p_technFact(RS,AACT,"LEVL",A)) = 0;

                    p_animReq(RS,AACT,A,"Test" %addtimedim%) $ p_animProdDays(RS,AACT,%yr_A% %addtimedim%) = 0;

    The entries "Test" are CAPRI's diagnostics, set to 0 at the end: not kept. Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        n = st.g(st.p_animProdDays, r, a, t)
        if n:
            for item in REQSR + SUBENE:
                if (r, a, t, item) in st.p_animReq:
                    st.p_animReq[(r, a, t, item)] = st.p_animReq[(r, a, t, item)] / n
            for f in FEED:
                _set_req(st, r, a, t, f, 1.0)
        if not st.tf(r, a, "LEVL", t):
            for item in REQSR:
                if (r, a, t, item) in st.p_animReq:
                    _set_req(st, r, a, t, item, 0)


def p_animReq_DRMA(st: ReqState) -> None:
    r"""The average dry matter intake per day: between the minimum and the maximum, else from either.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1534-1543):

                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $ (DATA(RS,AACT,"LEVL",%yr%)*p_technFact(RS,AACT,"LEVL",A)) = 0.0;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $ (p_animReq(RS,AACT,A,"DRMN" %addtimedim%) $ p_animReq(RS,AACT,A,"DRMX" %addtimedim%))
                      = p_animReq(RS,AACT,A,"DRMN" %addtimedim%) + (-p_animReq(RS,AACT,A,"DRMX" %addtimedim%) - p_animReq(RS,AACT,A,"DRMN"  %addtimedim%)) / 4.;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $  ( (NOT p_animReq(RS,AACT,A,"DRMA" %addtimedim%)) $ p_animReq(RS,AACT,A,"DRMN"  %addtimedim%))
                      = p_animReq(RS,AACT,A,"DRMN" %addtimedim%) * 1.1;
        *
                    p_animReq(RS,AACT,A,"DRMA" %addtimedim%) $  ( (NOT p_animReq(RS,AACT,A,"DRMA" %addtimedim%)) $ p_animReq(RS,AACT,A,"DRMX"  %addtimedim%))
                      = -p_animReq(RS,AACT,A,"DRMX" %addtimedim%) * 0.74;

    Departures from CAPRI: none."""
    for r, a, t in _techs_all(st):
        if st.D(r, a, "LEVL") * st.tf(r, a, "LEVL", t):
            _set_req(st, r, a, t, "DRMA", 0.0)
    for r, a, t in {(k[0], k[1], k[2]) for k in st.p_animReq}:
        mn, mx = st.req(r, a, t, "DRMN"), st.req(r, a, t, "DRMX")
        if mn and mx:
            _set_req(st, r, a, t, "DRMA", mn + (-mx - mn) / 4.)
        if not st.req(r, a, t, "DRMA") and mn:
            _set_req(st, r, a, t, "DRMA", mn * 1.1)
        if not st.req(r, a, t, "DRMA") and st.req(r, a, t, "DRMX"):
            _set_req(st, r, a, t, "DRMA", -st.req(r, a, t, "DRMX") * 0.74)


def p_animReqSubEne(st: ReqState) -> None:
    r"""The energy components stored apart and erased from the requirements; the production days erased where the
    technology has no share.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1548-1552):

                    p_animReqSubEne(RS,AACT,A,SUBENE %addtimedim%) = p_animReq(RS,AACT,A,SUBENE  %addtimedim%);
                    p_animReq(RS,AACT,A,SUBENE %addtimedim%)       = 0;

        *
                    p_animProdDays(RS,AACT,%yr_A% %addtimedim%) $ (NOT p_technFact(RS,AACT,"LEVL",A)) = 0;

    Departures from CAPRI: none."""
    for k in [k for k in st.p_animReq if k[3] in SUBENE]:
        st.p_animReqSubEne[k] = st.p_animReq.pop(k)
    for (r, a, t) in list(st.p_animProdDays):
        if not st.tf(r, a, "LEVL", t):
            st.p_animProdDays[(r, a, t)] = 0


# ------------------------------------------------------------------ PART II: the feed shares
def _shares(st, d, acts, feed, v, cond=None):
    """d(RS, act, A, feed) $ p_technFact(RS, act, "LEVL", A) = v (cond: a further condition on (r, act, t))."""
    for r in st.RS:
        for a in acts:
            for t in st.techs(r, a):
                if cond is None or cond(r, a, t):
                    d[(r, a, t, feed)] = v


def feed_shares_defaults(st: ReqState) -> None:
    r"""The feed shares' defaults (0 to 1); no fodder for the non-ruminants but some fodder maize for pigs; the
    protein-rich and energy-rich feed limits; the cereals' and protein-rich feeds' minimum shares of the cattle; the
    other feeds' minimum shares.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1561-1604):

                    p_minFeedShare(RS,AACT,A,FEED %addtimedim%) $ p_technFact(RS,AACT,"LEVL",A) = 0.0;
                    p_maxFeedShare(RS,AACT,A,FEED %addtimedim%) $ p_technFact(RS,AACT,"LEVL",A) = 1.0;
        *
        *           --- don t distribute fodder to non-ruminants
        *
                    p_maxFeedShare(RS,NRUMI,A,FODDI %addtimedim%)    $ p_technFact(RS,NRUMI,"LEVL",A)  = 0.0;
        $iftheni.feedpw1 %feedVersion%==_pw
                    p_maxFeedShare(RS,"SOWS",A,"FMAI" %addtimedim%)  $ p_technFact(RS,"SOWS","LEVL",A) = 0.1;
                    p_maxFeedShare(RS,"PIGF",A,"FMAI" %addtimedim%)  $ p_technFact(RS,"PIGF","LEVL",A) = 0.1;
        $endif.feedpw1
        *
                    p_maxFeedShare(RS,RUMI,A,"FPRO" %addtimedim%)    $ p_technFact(RS,RUMI,"LEVL",A)   = 0.3;
                    p_maxFeedShare(RS,NRUMI,A,"FPRO" %addtimedim%)   $ p_technFact(RS,NRUMI,"LEVL",A)  = 0.2;
                    p_maxFeedShare(RS,"SOWS",A,"FPRO" %addtimedim%)  $ p_technFact(RS,"SOWS","LEVL",A) = 0.3;
        $ifi %feedVersion%==_pw p_maxFeedShare(RS,"SOWS",A,"FPRO" %addtimedim%)  $ p_technFact(RS,"SOWS","LEVL",A) = 0.2;
        *
                    p_minFeedShare(RS,NRUMI,A,"FCER" %addtimedim%)   $ p_technFact(RS,NRUMI,"LEVL",A)  = 0.6;
        *
                    p_minFeedShare(RS,NRUMI,A,"FENE" %addtimedim%)   $ p_technFact(RS,NRUMI,"LEVL",A)  = 0.05;
                    p_maxFeedShare(RS,NRUMI,A,"FENE" %addtimedim%)   $ p_technFact(RS,NRUMI,"LEVL",A)  = 0.15;
                    p_maxFeedShare(RS,RUMI,A,"FENE" %addtimedim%)    $ p_technFact(RS,RUMI,"LEVL",A)   = 0.1;
        *
                    p_minFeedShare(RS,DCOW,A,"FCER" %addtimedim%)    $ p_technFact(RS,DCOW,"LEVL",A)   = 0.20;
                    p_minFeedShare(RS,BULF,A,"FCER" %addtimedim%)    $ p_technFact(RS,BULF,"LEVL",A)   = 0.20;
                    p_minFeedShare(RS,CALR,A,"FCER" %addtimedim%)    $ p_technFact(RS,CALR,"LEVL",A)   = 0.20;
                    p_minFeedShare(RS,CALF,A,"FCER" %addtimedim%)    $ p_technFact(RS,CALF,"LEVL",A)   = 0.20;
        *
                    p_minFeedShare(RS,HEIF,A,"FCER" %addtimedim%)    $ p_technFact(RS,HEIF,"LEVL",A)   = 0.05;
                    p_minFeedShare(RS,"HEIR",A,"FCER" %addtimedim%)  $ p_technFact(RS,"HEIR","LEVL",A) = 0.05;
                    p_minFeedShare(RS,"SCOW",A,"FCER" %addtimedim%)  $ p_technFact(RS,"SCOW","LEVL",A) = 0.05;
                    p_minFeedShare(RS,"OANI",A,"FCER" %addtimedim%)  $ p_technFact(RS,"OANI","LEVL",A) = 0.50;
        *
                    p_minFeedShare(RS,DCOW,A,"FPRO" %addtimedim%)    $ p_technFact(RS,DCOW,"LEVL",A)   = 0.10;
                    p_minFeedShare(RS,BULF,A,"FPRO" %addtimedim%)    $ p_technFact(RS,BULF,"LEVL",A)   = 0.10;
                    p_minFeedShare(RS,CALR,A,"FPRO" %addtimedim%)    $ p_technFact(RS,CALR,"LEVL",A)   = 0.10;
                    p_minFeedShare(RS,CALF,A,"FPRO" %addtimedim%)    $ p_technFact(RS,CALF,"LEVL",A)   = 0.10;
        *
                    p_minFeedShare(RS,HEIF,A,"FPRO" %addtimedim%)    $ p_technFact(RS,HEIF,"LEVL",A)   = 0.05;
                    p_minFeedShare(RS,HEIF,A,"FPRO" %addtimedim%)    $ p_technFact(RS,HEIF,"LEVL",A)   = 0.05;
        *
                    p_minFeedShare(RS,AACT,A,"FOTH" %addtimedim%)    $ p_technFact(RS,AACT,"LEVL",A)   = 0.005;
                    p_minFeedShare(RS,"SHGM",A,"FOTH" %addtimedim%)  $ p_technFact(RS,"SHGM","LEVL",A) = 0.001;
                    p_minFeedShare(RS,"SHGF",A,"FOTH" %addtimedim%)  $ p_technFact(RS,"SHGF","LEVL",A) = 0.001;
                    p_minFeedShare(RS,"SCOW",A,"FOTH" %addtimedim%)  $ p_technFact(RS,"SCOW","LEVL",A) = 0.001;

    The line 1575 holds with CAPRI's feed version _pw (the sows' protein-rich maximum 0.2). Departures from CAPRI:
    none."""
    mn, mx = st.p_minFeedShare, st.p_maxFeedShare
    for f in FEED:
        _shares(st, mn, st.AACT, f, 0.0)
        _shares(st, mx, st.AACT, f, 1.0)
    for f in FODDI:
        _shares(st, mx, NRUMI, f, 0.0)
    _shares(st, mx, ("SOWS",), "FMAI", 0.1)
    _shares(st, mx, ("PIGF",), "FMAI", 0.1)
    _shares(st, mx, st.RUMI, "FPRO", 0.3)
    _shares(st, mx, NRUMI, "FPRO", 0.2)
    _shares(st, mx, ("SOWS",), "FPRO", 0.3)
    _shares(st, mx, ("SOWS",), "FPRO", 0.2)
    _shares(st, mn, NRUMI, "FCER", 0.6)
    _shares(st, mn, NRUMI, "FENE", 0.05)
    _shares(st, mx, NRUMI, "FENE", 0.15)
    _shares(st, mx, st.RUMI, "FENE", 0.1)
    for acts in (DCOW, BULF, CALR, CALF):
        _shares(st, mn, acts, "FCER", 0.20)
    for acts in (HEIF, ("HEIR",), ("SCOW",)):
        _shares(st, mn, acts, "FCER", 0.05)
    _shares(st, mn, ("OANI",), "FCER", 0.50)
    for acts in (DCOW, BULF, CALR, CALF):
        _shares(st, mn, acts, "FPRO", 0.10)
    _shares(st, mn, HEIF, "FPRO", 0.05)
    _shares(st, mn, HEIF, "FPRO", 0.05)
    _shares(st, mn, st.AACT, "FOTH", 0.005)
    for a in ("SHGM", "SHGF", "SCOW"):
        _shares(st, mn, (a,), "FOTH", 0.001)


def p_maxFeedShare_FOTH(st: ReqState) -> None:
    r"""The other feed's maximum share: five times its share of the member state's dry matter, the same for every
    animal; twice that for the ruminants.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1608-1621):

                    p_maxFeedShare(MS,"DCOW","T","FOTH" %addtimedim%)  $ SUM( FEED $ (NOT SAMEAS(FEED,"FSTR")),
                                                      p_feedQuant(MS,FEED %addtimedim%)*DATA(MS,"DRMA",FEED,%yr%))
                      = 5.0 * p_feedQuant(MS,"FOTH" %addtimedim%)*DATA(MS,"DRMA","FOTH",%yr%)/
                               SUM( FEED $ ((NOT SAMEAS(FEED,"FSTR"))),
                                                     p_feedQuant(MS,FEED %addtimedim%)*DATA(MS,"DRMA",FEED,%yr%));

                    p_maxFeedShare(MS,AACT,A,"FOTH" %addtimedim%) $ p_technFact(MS,AACT,"LEVL",A)
                      = p_maxFeedShare(MS,"DCOW","T","FOTH" %addtimedim%);

        *
                    p_maxFeedShare(RS,AACT,A,"FOTH" %addtimedim%)
                      = SUM( R_RAGG(RS,MS), p_maxFeedShare(MS,AACT,A,"FOTH" %addtimedim%)) $ p_technFact(RS,AACT,"LEVL",A);
        *
                    p_maxFeedShare(RS,RUMI,A,"FOTH" %addtimedim%) = p_maxFeedShare(RS,RUMI,A,"FOTH" %addtimedim%)*2;

    p_feedQuant: CAPRI's member state feed quantities at the call (capmod/load_feed.gms l. 48, the base year's).
    Departures from CAPRI: none."""
    mx = st.p_maxFeedShare
    for m in st.MS:
        den = sum(st.g(st.p_feedQuant, m, f) * st.D(m, "DRMA", f) for f in FEED if f != "FSTR")
        if den:
            mx[(m, "DCOW", "T", "FOTH")] = 5.0 * st.g(st.p_feedQuant, m, "FOTH") * st.D(m, "DRMA", "FOTH") / den
    for m in st.MS:
        for a in st.AACT:
            for t in st.techs(m, a):
                mx[(m, a, t, "FOTH")] = st.g(mx, m, "DCOW", "T", "FOTH")
    for r in st.RS:
        for a in st.AACT:
            for t in A_ALL:
                mx[(r, a, t, "FOTH")] = (st.ms_sum(r, lambda m: st.g(mx, m, a, t, "FOTH"))
                                         if st.tf(r, a, "LEVL", t) else 0.0)
    for r in st.RS:
        for a in st.RUMI:
            for t in A_ALL:
                if (r, a, t, "FOTH") in mx:
                    mx[(r, a, t, "FOTH")] = mx[(r, a, t, "FOTH")] * 2


def p_totEnneFromFibreRichFeed(st: ReqState) -> None:
    r"""The energy of the region's fibre-rich fodder (grass, fodder maize, other fodder): the base year's quantities
    (from the crops' production where the data have none) at the year's energy contents (the member state's where the
    region has none).

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1623-1633):

                    option kill=p_dataCopy;
                    p_dataCopy(RS,"GROF",fibreRichFeed,"BAS") = DATA(RS,"GROF",fibreRichFeed,"BAS");

                    p_dataCopy(RS,"GROF",fibreRichFeed,"BAS") $ (NOT p_dataCopy(RS,"GROF",fibreRichFeed,"BAS"))
                       = SUM(PACT_TO_O(MCACT,O) $ (FEED_TO_O(fibreRichFeed,O) $ DATA(RS,MCACT,"LEVL",%yr%)), DATA(RS,MCACT,"LEVL",%yr%)*DATA(RS,MCACT,O,%yr%)) * 0.001;

                    p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)   = DATA(RS,"ENNE",fibreRichFeed,%yr%);
                    p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%) $ ( (NOT p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)) $ p_dataCopy(RS,"GROF",fibreRichFeed,"BAS"))
                       = SUM(R_RAGG(RS,MS),DATA(MS,"ENNE",fibreRichFeed,%yr%));

                    p_totEnneFromFibreRichFeed(RS) = SUM(fibreRichFeed, p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%));

    DATA's base year: st.DATA_BAS, {(region, column, row): value} at "BAS"; FEED_TO_O and PACT_TO_O: CAPRI's mappings
    (st.FEED_TO_O, st.PACT_TO_O); MCACT: CAPRI's crop activities. Departures from CAPRI: none."""
    st.p_dataCopy = {}
    for r in st.RS:
        for f in fibreRichFeed:
            v = st.g(st.DATA_BAS, r, "GROF", f)
            if not v:
                v = sum(st.D(r, c, o) * st.D(r, c, "LEVL") for (c, o) in st.PACT_TO_O
                        if c in st.MCACT and (f, o) in st.FEED_TO_O and st.D(r, c, "LEVL")) * 0.001
            if v:
                st.p_dataCopy[(r, "GROF", f, "BAS")] = v
            e = st.D(r, "ENNE", f)
            if not e and st.p_dataCopy.get((r, "GROF", f, "BAS")):
                e = st.ms_sum(r, lambda m: st.D(m, "ENNE", f))
            if e:
                st.p_dataCopy[(r, "ENNE", f)] = e
        st.p_totEnneFromFibreRichFeed[r] = sum(st.p_dataCopy.get((r, "GROF", f, "BAS"), 0.0)
                                               * st.p_dataCopy.get((r, "ENNE", f), 0.0) for f in fibreRichFeed)


def p_minFeedShare_fibre(st: ReqState) -> None:
    r"""The ruminants' minimum shares of the fibre-rich fodder: a share of the ration in proportion to each fodder's
    energy in the region; straw's limits where the region produces straw.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1636-1661):

                    p_minFeedShare(RS,DCOW,A,fibreRichFeed %addtimedim%)   $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,DCOW,"LEVL",A))
                     = 0.6  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

                    p_minFeedShare(RS,"SCOW",A,fibreRichFeed %addtimedim%) $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,"SCOW","LEVL",A))
                     = 0.9  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

                    p_minFeedShare(RS,BULF,A,fibreRichFeed %addtimedim%)   $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,BULF,"LEVL",A))
                     = 0.5  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

                    p_minFeedShare(RS,HEIF,A,fibreRichFeed %addtimedim%)   $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,HEIF,"LEVL",A))
                     = 0.6  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

                    p_minFeedShare(RS,CALR,A,fibreRichFeed %addtimedim%)   $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,CALR,"LEVL",A))
                     = 0.4  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

                    p_minFeedShare(RS,CALF,A,fibreRichFeed %addtimedim%)   $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,CALF,"LEVL",A))
                     = 0.2  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);

        *
                    p_minFeedShare(RS,"SHGM",A,fibreRichFeed %addtimedim%) $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,"SHGM","LEVL",A))
                    = 0.8  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);
                    p_minFeedShare(RS,"SHGF",A,fibreRichFeed %addtimedim%) $ (p_totEnneFromFibreRichFeed(RS) $ p_technFact(RS,"SHGF","LEVL",A))
                    = 0.5  * p_dataCopy(RS,"GROF",fibreRichFeed,"BAS")*p_dataCopy(RS,"ENNE",fibreRichFeed,%yr%)/p_totEnneFromFibreRichFeed(RS);
        *
                    p_minFeedShare(RS,RUMI,A,"FSTR" %addtimedim%) $ (DATA(RS,"GROF","STRA","BAS") $ p_technFact(RS,RUMI,"LEVL",A)) = 0.01;
                    p_maxFeedShare(RS,RUMI,A,"FSTR" %addtimedim%) $ (DATA(RS,"GROF","STRA","BAS") $ p_technFact(RS,RUMI,"LEVL",A)) = 0.05;

    Departures from CAPRI: none."""
    mn, mx = st.p_minFeedShare, st.p_maxFeedShare
    for acts, k in ((DCOW, 0.6), (("SCOW",), 0.9), (BULF, 0.5), (HEIF, 0.6), (CALR, 0.4), (CALF, 0.2),
                    (("SHGM",), 0.8), (("SHGF",), 0.5)):
        for r in st.RS:
            tot = st.g(st.p_totEnneFromFibreRichFeed, r)
            if not tot:
                continue
            for f in fibreRichFeed:
                v = k * st.p_dataCopy.get((r, "GROF", f, "BAS"), 0.0) * st.p_dataCopy.get((r, "ENNE", f), 0.0) / tot
                for a in acts:
                    for t in st.techs(r, a):
                        mn[(r, a, t, f)] = v
    for r in st.RS:
        if st.g(st.DATA_BAS, r, "GROF", "STRA"):
            for a in st.RUMI:
                for t in st.techs(r, a):
                    mn[(r, a, t, "FSTR")] = 0.01
                    mx[(r, a, t, "FSTR")] = 0.05


def feed_shares_special(st: ReqState) -> None:
    r"""The sheep's and goats' limit on the feeds other than fibre-rich fodder; the calves' milk; the cow milk for
    feeding (calves only, feed version _pw); the sheep and goat milk for feeding; the fodder of an animal without the
    technology; the cereals' and protein-rich feeds' minimum default; no minimum without a maximum.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1666-1714):

                    p_maxFeedShare(RS,"SHGM",A,FEED %addtimedim%) $ ( p_technFact(RS,"SHGM","LEVL",A) $ (NOT fibreRichFeed(FEED)) ) = 0.20;
                    p_maxFeedShare(RS,"SHGF",A,FEED %addtimedim%) $ ( p_technFact(RS,"SHGF","LEVL",A) $ (NOT fibreRichFeed(FEED)) ) = 0.20;
        *
        *           --- calves are assumed to be fed partially by milk based feeding stuff
        *
                    p_minFeedShare(RS,CALF,A,"FMIL" %addtimedim%) $ p_technFact(RS,CALF,"LEVL",A) = 0.05;
                    p_minFeedShare(RS,CALR,A,"FMIL" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = 0.05;
        *
        *     ... and other animals are excluded
        $ifi "%feedversion%"=="_pw" p_maxFeedShare(RS,MAACT,A,"FMIL" %addtimedim%) $ (not (CALR(mAACT) or CALF(mAACT))) = 0;

                    p_minFeedShare(RS,CALF,A,"FCOM" %addtimedim%) $ p_technFact(RS,CALF,"LEVL",A) = 0.10;
                    p_minFeedShare(RS,CALR,A,"FCOM" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = 0.10;
        *
                    p_maxFeedShare(RS,AACT,A,"FCOM" %addtimedim%)    = 0.00;
                    p_maxFeedShare(RS,ACATTLE,A,"FCOM" %addtimedim%) $ p_technFact(RS,ACATTLE,"LEVL",A) = 0.01;
        *     as p_maxFeedShare would only signal "FEED is permitted" according to the new version it appears better to discard FCOM here:
        $ifi "%feedversion%"=="_pw" p_maxFeedShare(RS,ACATTLE,A,"FCOM" %addtimedim%)  = 0;

                    p_maxFeedShare(RS,AACT,A,"FSGM" %addtimedim%) $ (NOT (SAMEAS("SHGM",AACT) or SAMEAS("SHGF",AACT)))  = 0;
        *
        *           -- not milk from cows to cows
        *
                    p_maxFeedShare(RS,DCOW,A,"FCOM" %addtimedim%)   $ p_technFact(RS,DCOW,"LEVL",A)   = 0.0;
                    p_maxFeedShare(RS,"SCOW",A,"FCOM" %addtimedim%) $ p_technFact(RS,"SCOW","LEVL",A) = 0.0;
        $ifi "%feedversion%"=="_pw"   p_maxFeedShare(RS,AACT,A,"FCOM" %addtimedim%) $ p_technFact(RS,AACT,"LEVL",A) = 0.0;
        *
        *           --- fattening calves can take up to 30 % suckler milk
        *
                    p_maxFeedShare(RS,CALF,A,"FCOM" %addtimedim%) $ p_technFact(RS,CALF,"LEVL",A) = 0.3;
        *
        *           --- raising calves can take up as much feed milk as they want
        *
                    p_maxFeedShare(RS,CALR,A,"FCOM" %addtimedim%) $ p_technFact(RS,CALR,"LEVL",A) = 1.0;
        *
        *           --- don t feed non-tradeable if not produced (only for the "empty" version, for _pw something similar is done in fedtrm_prior_pw.gms
        *
        $ifi not %feedVersion%==_pw p_maxFeedShare(RS,AACT,A,FODDI %addtimedim%) $ ((DATA(RS,"GROF",FODDI,%yr%) LE 1.E-10) $ p_technFact(RS,AACT,"LEVL",A) $ (not sameas(FODDI,"FSTR"))) = 0.0;
        $ifi not %feedVersion%==_pw p_maxFeedShare(RS,AACT,A,FODDI %addtimedim%) $ ((DATA(RS,"GROF",FODDI,%yr%) LE 1.E-10) $ p_technFact(RS,AACT,"LEVL",A) ) = 0.0;
        *
                    p_maxFeedShare(RS,AACT,A,FODDI %addtimedim%) $ ( NOT p_technFact(RS,AACT,"LEVL",A) ) = 0.0;
        *

        *            p_maxFeedShare(RS,AACT,A,FEED %addtimedim%)  $ ( NOT SUM(R_RAGG(RS,MS), p_feedQuant(MS,FEED  %addtimedim%))) = 0.0;
        *
                    p_minFeedShare(RS,AACT,A,"FCER" %addtimedim%) $ ( NOT p_minFeedShare(RS,AACT,A,"FCER" %addtimedim%)) = 0.02;
                    p_minFeedShare(RS,AACT,A,"FPRO" %addtimedim%) $ ( NOT p_minFeedShare(RS,AACT,A,"FCER" %addtimedim%)) = 0.01;

                    p_minFeedShare(RS,AACT,A,FEED %addtimedim%)   $ ( NOT p_maxFeedShare(RS,AACT,A,FEED %addtimedim%)) = 0;

    Lines 1675, 1683 and 1691 hold with CAPRI's feed version _pw, lines 1703-1704 do not. Departures from CAPRI:
    none."""
    mn, mx = st.p_minFeedShare, st.p_maxFeedShare
    for f in FEED:
        if f not in fibreRichFeed:
            _shares(st, mx, ("SHGM",), f, 0.20)
            _shares(st, mx, ("SHGF",), f, 0.20)
    _shares(st, mn, CALF, "FMIL", 0.05)
    _shares(st, mn, CALR, "FMIL", 0.05)
    for r in st.RS:
        for a in st.AACT:
            if a in st.MAACT and a not in CALR + CALF:
                for t in A_ALL:
                    mx[(r, a, t, "FMIL")] = 0
    _shares(st, mn, CALF, "FCOM", 0.10)
    _shares(st, mn, CALR, "FCOM", 0.10)
    for r in st.RS:
        for a in st.AACT:
            for t in A_ALL:
                mx[(r, a, t, "FCOM")] = 0.00
    _shares(st, mx, ACATTLE, "FCOM", 0.01)
    for r in st.RS:
        for a in ACATTLE:
            for t in A_ALL:
                mx[(r, a, t, "FCOM")] = 0
        for a in st.AACT:
            if a not in ("SHGM", "SHGF"):
                for t in A_ALL:
                    mx[(r, a, t, "FSGM")] = 0
    _shares(st, mx, DCOW, "FCOM", 0.0)
    _shares(st, mx, ("SCOW",), "FCOM", 0.0)
    _shares(st, mx, st.AACT, "FCOM", 0.0)
    _shares(st, mx, CALF, "FCOM", 0.3)
    _shares(st, mx, CALR, "FCOM", 1.0)
    for r in st.RS:
        for a in st.AACT:
            for t in A_ALL:
                if not st.tf(r, a, "LEVL", t):
                    for f in FODDI:
                        mx[(r, a, t, f)] = 0.0
    for r in st.RS:
        for a in st.AACT:
            for t in A_ALL:
                if not st.g(mn, r, a, t, "FCER"):
                    mn[(r, a, t, "FCER")] = 0.02
                if not st.g(mn, r, a, t, "FCER"):
                    mn[(r, a, t, "FPRO")] = 0.01
                for f in FEED:
                    if not st.g(mx, r, a, t, f) and (r, a, t, f) in mn:
                        mn[(r, a, t, f)] = 0


def p_NutContFeed_and_aggregate_shares(st: ReqState) -> None:
    r"""The nutrient densities of the feed aggregates (CAPRI's typical MIN, MEAN and MAX) and the shares of the
    roughage, concentrates and other feed in the ration.

    CAPRI's GAMS (feed/req_or_man_fnc.gms l. 1718-1800):

          p_NutContFeed(RS,AACT,A,REQMSE,"FeedCons","MAX" %addtimedim%) = 100;
          p_NutContFeed(RS,AACT,A,REQMSE,"FeedTotal","MAX" %addtimedim%) = 100;

          p_maxFeedShare(RS,"DCOL",A,"FeedRough" %addtimedim%) = 0.85;
          p_maxFeedShare(RS,"DCOH",A,"FeedRough" %addtimedim%) = 0.7;
          p_maxFeedShare(RS,"BULL",A,"FeedRough" %addtimedim%) = 0.8;
          p_maxFeedShare(RS,"BULH",A,"FeedRough" %addtimedim%) = 0.8;
          p_maxFeedShare(RS,"HEIL",A,"FeedRough" %addtimedim%) = 0.9;
          p_maxFeedShare(RS,"HEIH",A,"FeedRough" %addtimedim%) = 0.9;
          p_maxFeedShare(RS,"HEIR",A,"FeedRough" %addtimedim%) = 0.9;
          p_maxFeedShare(RS,"SCOW",A,"FeedRough" %addtimedim%) = 0.95;




          p_minFeedShare(RS,"DCOL",A,"FeedRough" %addtimedim%) = 0.75;
          p_minFeedShare(RS,"DCOH",A,"FeedRough" %addtimedim%) = 0.6;
          p_minFeedShare(RS,"BULL",A,"FeedRough" %addtimedim%) = 0.65;
          p_minFeedShare(RS,"BULH",A,"FeedRough" %addtimedim%) = 0.65;
          p_minFeedShare(RS,"HEIL",A,"FeedRough" %addtimedim%) = 0.65;
          p_minFeedShare(RS,"HEIH",A,"FeedRough" %addtimedim%) = 0.7;
          p_minFeedShare(RS,"HEIR",A,"FeedRough" %addtimedim%) = 0.7;
          p_minFeedShare(RS,"SCOW",A,"FeedRough" %addtimedim%) = 0.7;

          p_maxFeedShare(RS,"DCOL",A,"FeedCons" %addtimedim%) = 0.4;
          p_maxFeedShare(RS,"DCOH",A,"FeedCons" %addtimedim%) = 0.45;
          p_maxFeedShare(RS,"BULL",A,"FeedCons" %addtimedim%) = 0.4;
          p_maxFeedShare(RS,"BULH",A,"FeedCons" %addtimedim%) = 0.4;
          p_maxFeedShare(RS,"HEIL",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"HEIH",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"HEIR",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"SCOW",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"CAFF",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"CAMF",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"CAFR",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"CAMR",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"SHGM",A,"FeedCons" %addtimedim%) = 0.3;
          p_maxFeedShare(RS,"SHGF",A,"FeedCons" %addtimedim%) = 0.3;

          p_minFeedShare(RS,"DCOL",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"DCOH",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"BULL",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"BULH",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"HEIL",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"HEIH",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"HEIR",A,"FeedCons" %addtimedim%) = 0.05;
          p_minFeedShare(RS,"SCOW",A,"FeedCons" %addtimedim%) = 0.05;
          p_minFeedShare(RS,"CAFF",A,"FeedCons" %addtimedim%) = 0.15;
          p_minFeedShare(RS,"CAMF",A,"FeedCons" %addtimedim%) = 0.15;
          p_minFeedShare(RS,"CAFR",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"CAMR",A,"FeedCons" %addtimedim%) = 0.1;
          p_minFeedShare(RS,"SHGM",A,"FeedCons" %addtimedim%) = 0.05;
          p_minFeedShare(RS,"SHGF",A,"FeedCons" %addtimedim%) = 0.05;
          p_minFeedShare(RS,"SOWS",A,"FeedCons" %addtimedim%) = 0.90;
          p_minFeedShare(RS,"PIGF",A,"FeedCons" %addtimedim%) = 0.95;
          p_minFeedShare(RS,"POUF",A,"FeedCons" %addtimedim%) = 0.99;
          p_minFeedShare(RS,"HENS",A,"FeedCons" %addtimedim%) = 0.99;

          p_maxFeedShare(RS,"DCOL",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"DCOH",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"BULL",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"BULH",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"HEIL",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"HEIH",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"HEIR",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"SCOW",A,"FeedOth" %addtimedim%) = 0.1;
          p_maxFeedShare(RS,"CAFF",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"CAMF",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"CAFR",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"CAMR",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"SHGM",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"SHGF",A,"FeedOth" %addtimedim%) = 0.05;
          p_maxFeedShare(RS,"SOWS",A,"FeedOth" %addtimedim%) = 0.01;
          p_maxFeedShare(RS,"PIGF",A,"FeedOth" %addtimedim%) = 0.01;
          p_maxFeedShare(RS,"POUF",A,"FeedOth" %addtimedim%) = 1E-6;
          p_maxFeedShare(RS,"HENS",A,"FeedOth" %addtimedim%) = 1E-6;

          p_NutContFeed(RS,AACT,A,REQMSE,"FeedCons","MAX" %addtimedim%) = 0;
          p_NutContFeed(RS,AACT,A,REQMSE,"FeedTotal","MAX" %addtimedim%) =0;

        p_NutContFeed(RS,AACT,A,REQMSE,FeedAggr,"MIN" %addtimedim%) = p_NutContFeedRef(AACT,A,REQMSE,FeedAggr,"MIN");
        p_NutContFeed(RS,AACT,A,REQMSE,FeedAggr,"MEAN" %addtimedim%) = p_NutContFeedRef(AACT,A,REQMSE,FeedAggr,"MEAN");
        p_NutContFeed(RS,AACT,A,REQMSE,FeedAggr,"MAX" %addtimedim%) = p_NutContFeedRef(AACT,A,REQMSE,FeedAggr,"MAX");

    Departures from CAPRI: none."""
    mn, mx, nc = st.p_minFeedShare, st.p_maxFeedShare, st.p_NutContFeed
    rough_mx = {"DCOL": 0.85, "DCOH": 0.7, "BULL": 0.8, "BULH": 0.8, "HEIL": 0.9, "HEIH": 0.9, "HEIR": 0.9, "SCOW": 0.95}
    rough_mn = {"DCOL": 0.75, "DCOH": 0.6, "BULL": 0.65, "BULH": 0.65, "HEIL": 0.65, "HEIH": 0.7, "HEIR": 0.7,
                "SCOW": 0.7}
    cons_mx = {"DCOL": 0.4, "DCOH": 0.45, "BULL": 0.4, "BULH": 0.4, "HEIL": 0.3, "HEIH": 0.3, "HEIR": 0.3, "SCOW": 0.3,
               "CAFF": 0.3, "CAMF": 0.3, "CAFR": 0.3, "CAMR": 0.3, "SHGM": 0.3, "SHGF": 0.3}
    cons_mn = {"DCOL": 0.1, "DCOH": 0.1, "BULL": 0.1, "BULH": 0.1, "HEIL": 0.1, "HEIH": 0.1, "HEIR": 0.05, "SCOW": 0.05,
               "CAFF": 0.15, "CAMF": 0.15, "CAFR": 0.1, "CAMR": 0.1, "SHGM": 0.05, "SHGF": 0.05, "SOWS": 0.90,
               "PIGF": 0.95, "POUF": 0.99, "HENS": 0.99}
    oth_mx = {"DCOL": 0.1, "DCOH": 0.1, "BULL": 0.1, "BULH": 0.1, "HEIL": 0.1, "HEIH": 0.1, "HEIR": 0.1, "SCOW": 0.1,
              "CAFF": 0.05, "CAMF": 0.05, "CAFR": 0.05, "CAMR": 0.05, "SHGM": 0.05, "SHGF": 0.05, "SOWS": 0.01,
              "PIGF": 0.01, "POUF": 1E-6, "HENS": 1E-6}
    for r in st.RS:
        for t in A_ALL:
            for (d, table, aggr) in ((mx, rough_mx, "FeedRough"), (mn, rough_mn, "FeedRough"), (mx, cons_mx, "FeedCons"),
                                     (mn, cons_mn, "FeedCons"), (mx, oth_mx, "FeedOth")):
                for a, v in table.items():
                    d[(r, a, t, aggr)] = v
    for (a, t, q, aggr, stat), v in st.p_NutContFeedRef.items():
        for r in st.RS:
            nc[(r, a, t, q, aggr, stat)] = v


#: CAPRI's statement blocks of 'req' mode, in CAPRI's order (feed/req_or_man_fnc.gms PART I and PART II)
BLOCKS = (DATA_AGGR_YCOW, p_stockingRate, p_dataCopy_req,
          p_milkFatCont, p_meanLiveWgt_DCOW, p_animProdDays_DCOW, p_milkPerDay_DCOW, p_crprReq_DCOW, p_fatCorMilk_DCOW,
          p_animReq_DCOW_energy, p_animReq_DCOW_dry_matter,
          p_meanLiveWgt_SCOW, p_milkPerDay_SCOW, p_crprReq_SCOW, p_animReq_SCOW, p_femWgt,
          p_dailyWgtIncrease_CALF, p_animProdDays_CALF, CALF_light, p_crprReq_CALF_light, p_animReq_CALF_light,
          CALF_heavy_b1, p_crprReq_CALF_heavy_b1, p_animReq_CALF_heavy_b1,
          CALF_heavy_b2, p_crprReq_CALF_heavy_b2, p_animReq_CALF_heavy_b2,
          CALR_weaning, CALR_80_150, CALR_last, CALR_last_requirements,
          BULF_growth, BULF_requirements, HEIF_growth, HEIF_requirements, HEIR_growth, HEIR_requirements,
          SOWS_requirements, PIGF_requirements, HENS_requirements, POUF_requirements,
          SHGM_growth, SHGM_crude_protein, SHGM_requirements, SHGF_requirements, DATA_OANI_FOUT,
          p_animReq_CRPR, p_animReq_erase, p_animReq_signs, p_animReq_ENNE, p_animReq_per_day, p_animReq_DRMA,
          p_animReqSubEne,
          feed_shares_defaults, p_maxFeedShare_FOTH, p_totEnneFromFibreRichFeed, p_minFeedShare_fibre,
          feed_shares_special, p_NutContFeed_and_aggregate_shares)


def req_or_man_fnc_req(st: ReqState) -> ReqState:
    r"""CAPRI's 'req' call of feed/req_or_man_fnc.gms at "Y": every block of BLOCKS in order, on st (changed in place
    and returned). After it: st.p_animReq (per head and day; CAPRI's p_animReqLit is this, def_requirements.gms l. 33),
    st.p_animProdDays, st.p_animReqSubEne, st.p_crprReq (per head), st.p_minFeedShare, st.p_maxFeedShare and
    st.p_NutContFeed.

    The caller supplies CAPRI's inputs at the year (ReqState's docstring) and st.DATA_BAS (DATA at "BAS"), st.MAACT,
    st.MCACT, st.FEED_TO_O and st.PACT_TO_O (CAPRI's sets)."""
    for block in BLOCKS:
        block(st)
    return st

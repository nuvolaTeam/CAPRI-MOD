r"""CAPRI's sets of the 'req' call and its state (ReqState) and data copy (moved from
capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set



#: CAPRI's sets (sets.gms; feed/feed_decl.gms; capri_data/codes/capri, in CAPRI's order)
SUBENE = capri_set("SUBENE")
REQSE = capri_set("REQSE")
FEED = capri_set("FEED")
REQSR = capri_set("REQSR")
REQSC = capri_set("REQSC")
REQMSE = capri_set("REQMSE")
FODDI = capri_set("FODDI")
fibreRichFeed = capri_set("fibreRichFeed")
ACATTLE = capri_set("ACATTLE")
FeedAggr = capri_set("FeedAggr")
#: CAPRI's technologies A (sets.gms): the mean technology and the high- and low-yield variants
A_ALL = capri_set("A")


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

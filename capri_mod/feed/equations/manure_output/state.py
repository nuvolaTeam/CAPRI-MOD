r"""CAPRI's sets of the 'man' call, its state (ManState), the manure's nutrient contents, the young cows' aggregate, the
stocking rate and the data copy (moved from capri_mod/feed/equations/req_or_man_fnc.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_set



#: CAPRI's sets (sets.gms, feed/feed_decl.gms; capri_data/codes/capri, in CAPRI's order)
DCOW = capri_set("DCOW")
CALF = capri_set("CALF")
CALR = capri_set("CALR")
BULF = capri_set("BULF")
HEIF = capri_set("HEIF")
NRUMI = capri_set("NRUMI")
#: the manure rows (FOUT) and those 'man' mode assigns together (curRows: FOUT less MANN, l. 117-121)
FOUT = capri_set("FOUT")
curRows = tuple(r for r in FOUT if r != "MANN")


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

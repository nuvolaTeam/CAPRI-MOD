r"""CAPRI's preparation of the baseline feed calibration (baseline/fedtrm_prep.gms; CAPRI star 3.0, feed version "_pw"),
the parts the calibration reads: the feed coefficients of the simulation year from CAPTRD's trends, the start of the
feed input coefficients and feed quantities, straw as a feed, the aggregation to NUTS 1 and to the member state
(supply/aggreg.gms, capri_mod/feed/equations/aggreg.py), the gross production of the regions, the start of the
requirements, the member state's feed quantities and the ratio of its deliveries to its requirements.

The state is FedtrmState, for one member state and its units (CAPRI's statements run over all member states at once
and never cross one, so a member state at a time is CAPRI's result).

Not ported, as the calibration does not read them: the fertiliser distribution's start (l. 32-34), the farm types
(l. 44-57, 107-113: CAPRI's baseline runs without them), the unit values, the feed cost and the values of output and
input (l. 94-101, 117-134: they feed the feed cost row CST_, left out, claude/feed_calibration_port_plan_2026-11-24.md
section 5), the restart point (l. 139-168: CAPRI's mefed file is not in the material, so CAPRI's fallback, the start
below), and fert/calc_nexport.gms (l. 198: the N in the products, which the projection computes on its own,
capri_mod/projection/projection_module.py).

One function per CAPRI statement block. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.feed.equations import aggreg as ag


@dataclass
class FedtrmState:
    """CAPRI's symbols of the baseline feed calibration for one member state MS (all dictionaries; regions are CAPRI's
    codes): DATA {(region, column, row): value} at "Y"; DATA_TRD and DATA_BAS {(region, column, row): value} at "TRD"
    (CAPTRD's trends) and "BAS"; v_actLevl_L {(region, activity, A): level}; p_technFact {(region, activity, item, A)};
    p_animReq {(region, activity, A, item)}; p_animProdDays {(region, activity, A)}; p_minFeedShare and
    p_maxFeedShare {(region, activity, A, feed)}. The region sets: RU the member state's regional units, SRNUTS1 its
    NUTS 1 units (CAPRI's SRNUTS1 the member state maps to; the member state itself where it is one), MAP_RR the pairs
    (region, member) among them. Written: v_feedInpCoeff_L {(region, activity, A, feed)}, v_feedQuantReg_L {(region,
    feed)}, v_lossQuant_L {(region, "STRA")}, v_animReq_L {(region, activity, A, item)}, p_feedQuant {(region, feed)},
    p_aprDistAnimReq {(region, activity, A, item, stat)}, NUTS1_RAGG (the NUTS 1 units aggregated)."""
    MS: str
    RU: tuple
    SRNUTS1: tuple
    MAP_RR: frozenset
    DATA: dict
    DATA_TRD: dict
    DATA_BAS: dict
    v_actLevl_L: dict
    p_technFact: dict
    p_animReq: dict
    p_animProdDays: dict
    p_minFeedShare: dict
    p_maxFeedShare: dict
    v_feedInpCoeff_L: dict = field(default_factory=dict)
    v_feedQuantReg_L: dict = field(default_factory=dict)
    v_lossQuant_L: dict = field(default_factory=dict)
    v_animReq_L: dict = field(default_factory=dict)
    p_feedQuant: dict = field(default_factory=dict)
    p_aprDistAnimReq: dict = field(default_factory=dict)
    NUTS1_RAGG: tuple = ()
    #: the member state's NUTS 2 units (CAPRI's SRNUTS2 it maps to), the priors' (feed/fedtrm_prior_pw.gms)
    SRNUTS2: tuple = ()
    #: the feeds' nutrient densities {(region, activity, A, requirement, aggregate, MIN | MEAN | MAX)}
    #: (req_or_man_fnc.gms), and the exogenous demand {(region, "DEMD", output)} (energy maize: CAPTRD's INDM)
    p_NutContFeed: dict = field(default_factory=dict)
    p_exoDemand: dict = field(default_factory=dict)
    #: the priors (capri_mod/feed/equations/fedtrm_prior_pw.py)
    p_FeedAggrPrior: dict = field(default_factory=dict)
    p_feedBalance: dict = field(default_factory=dict)
    p_feedInpCoeffDRMA: dict = field(default_factory=dict)
    p_feedQuantDRMA: dict = field(default_factory=dict)
    p_FeedShareInAggr: dict = field(default_factory=dict)
    p_feedInpCoeff: dict = field(default_factory=dict)
    #: the calibration's variables (capri_mod/feed/equations/fedtrm_mod_pw.py GamsVar; the levels of the first four are
    #: the dictionaries above) and the solves per aggregate p_nSolved (feed/fedtrm_cal_pw.py)
    v_feedInpCoeff: object = None
    v_animReq: object = None
    v_feedQuantReg: object = None
    v_lossQuant: object = None
    v_NutContFeed: object = None
    v_FeedAggrShare: object = None
    p_nSolved: dict = field(default_factory=dict)
    MPACT: tuple = field(default_factory=lambda: capri_set("MPACT"))
    MAACT: tuple = field(default_factory=lambda: capri_set("MAACT"))
    A: tuple = field(default_factory=lambda: capri_set("A"))
    S_TACT: tuple = field(default_factory=lambda: capri_set("S_TACT"))
    FEED: tuple = field(default_factory=lambda: capri_set("FEED"))
    REQSC: tuple = field(default_factory=lambda: capri_set("REQSC"))
    REQC: tuple = field(default_factory=lambda: capri_set("REQC"))
    REQSR_M: tuple = field(default_factory=lambda: capri_set("REQSR_M"))
    #: CAPRI's REQM, an alias of REQSR (global/fromimpact/sets.gms l. 2545)
    REQM: tuple = field(default_factory=lambda: capri_set("REQSR"))
    IO: tuple = field(default_factory=lambda: capri_set("IO"))
    REQ_FEED: tuple = field(default_factory=lambda: capri_set("REQ_FEED"))
    MAACT_TO_REQM: tuple = field(default_factory=lambda: capri_pairs("MAACT_TO_REQM"))
    PACT_TO_IO: tuple = field(default_factory=lambda: capri_pairs("PACT_TO_IO"))
    PACT_TO_O: tuple = field(default_factory=lambda: capri_pairs("PACT_TO_O"))
    FEED_TO_O: tuple = field(default_factory=lambda: capri_pairs("FEED_TO_O"))
    Feed_FeedAggr: tuple = field(default_factory=lambda: capri_pairs("Feed_FeedAggr"))
    FeedAggr: tuple = field(default_factory=lambda: capri_set("FeedAggr"))
    FODDI: tuple = field(default_factory=lambda: capri_set("FODDI"))
    FODDIS: tuple = field(default_factory=lambda: capri_set("FODDIS"))
    REQMSE: tuple = field(default_factory=lambda: capri_set("REQMSE"))
    REQSR: tuple = field(default_factory=lambda: capri_set("REQSR"))
    MNRUMI: tuple = field(default_factory=lambda: capri_set("MNRUMI"))
    CACT: tuple = field(default_factory=lambda: capri_set("CACT"))
    AACT: tuple = field(default_factory=lambda: capri_set("AACT"))
    FEED_TRD: tuple = field(default_factory=lambda: capri_set("FEED_TRD"))
    RSEU: tuple = field(default_factory=lambda: capri_set("RSEU"))
    R_LEVL: tuple = field(default_factory=lambda: capri_set("R_LEVL"))

    def __post_init__(self):
        from capri_mod.feed.equations.fedtrm_mod_pw import GamsVar, free_var
        if self.v_feedInpCoeff is None:
            self.v_feedInpCoeff = GamsVar(L=self.v_feedInpCoeff_L)
            self.v_animReq = GamsVar(L=self.v_animReq_L)
            self.v_feedQuantReg = GamsVar(L=self.v_feedQuantReg_L)
            self.v_lossQuant = GamsVar(L=self.v_lossQuant_L)
            self.v_NutContFeed = free_var()
            self.v_FeedAggrShare = free_var()

    def members(self, r) -> tuple:
        """CAPRI's MAP_RR(r, member), the member r itself left out."""
        return tuple(m for (a, m) in sorted(self.MAP_RR) if a == r and m != r)

    def rall_in_ms(self) -> tuple:
        """CAPRI's RallInMS: the member state and every region it maps to (feed/fedtrm_prior_pw.gms l. 29-30)."""
        return tuple(sorted({self.MS} | {m for (a, m) in self.MAP_RR if a == self.MS}))

    def units_of(self, r) -> tuple:
        """CAPRI's SUM(MAP_RR(r, NUTS2), ...) with NUTS2 the regional units RU (capmod/def_fert_and_requirements.gms
        l. 1070-1071): r's regional units, r itself where CAPRI maps it to itself and it is one."""
        ru = set(self.RU)
        return tuple(m for (a, m) in sorted(self.MAP_RR) if a == r and m in ru)


def DATA_feed_from_trends(st: FedtrmState) -> None:
    r"""The animals' feed coefficients of the simulation year are CAPTRD's.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 25):

          DATA(RU,MAACT,FEED,"Y") = DATA(RU,MAACT,FEED,"TRD");

    Departures from CAPRI: none."""
    for (r, a, f), v in st.DATA_TRD.items():
        if r in st.RU and a in st.MAACT and f in st.FEED:
            st.DATA[(r, a, f)] = v


def v_feedInpCoeff_start(st: FedtrmState) -> None:
    r"""The feed input coefficients start at DATA's, for every technology.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 27):

          v_feedInpCoeff.L(RU,MAACT,A,FEED) = DATA(RU,MAACT,FEED,"Y");

    Departures from CAPRI: none."""
    for r in st.RU:
        for a in st.MAACT:
            for f in st.FEED:
                v = st.DATA.get((r, a, f), 0.0)
                if v:
                    for t in st.A:
                        st.v_feedInpCoeff_L[(r, a, t, f)] = v


def v_feedQuantReg_start(st: FedtrmState) -> None:
    r"""The regional feed quantities at the start: the coefficients times the herds, straw with its losses.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 29-30):

          v_feedQuantReg.L(RU,FEED)
                     = SUM( (MAACT,A), v_feedInpCoeff.L(RU,MAACT,A,FEED)*v_actLevl.L(RU,MAACT,A)) / 1000. + v_lossQuant.L(RU,"STRA") $ SAMEAS(FEED,"FSTR");;

    Departures from CAPRI: none."""
    for r in st.RU:
        for f in st.FEED:
            st.v_feedQuantReg_L[(r, f)] = (sum(st.v_feedInpCoeff_L.get((r, a, t, f), 0.0) * st.v_actLevl_L.get((r, a, t), 0.0)
                                               for a in st.MAACT for t in st.A) / 1000.0
                                           + (st.v_lossQuant_L.get((r, "STRA"), 0.0) if f == "FSTR" else 0.0))


def DATA_FSTR_from_STRA(st: FedtrmState) -> None:
    r"""Straw as a feed: its production, losses and feed use from the straw output's where not given.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 36-40):

        $iftheni.feedpw6 %feedversion%==_pw
          DATA(RS,"GROF","FSTR","Y") $ (not DATA(RS,"GROF","FSTR","Y"))= DATA(RS,"GROF","STRA","Y");
          DATA(RS,"LOSF","FSTR","Y") $ (not DATA(RS,"LOSF","FSTR","Y"))= DATA(RS,"LOSF","STRA","Y");
          DATA(RS,"FEDM","FSTR","Y") $ (not DATA(RS,"FEDM","FSTR","Y"))= DATA(RS,"GROF","STRA","Y") - DATA(RS,"LOSF","STRA","Y");
        $endif.feedpw6

    Departures from CAPRI: none."""
    for r in (st.MS,) + tuple(st.RU):
        g, lo = st.DATA.get((r, "GROF", "STRA"), 0.0), st.DATA.get((r, "LOSF", "STRA"), 0.0)
        if not st.DATA.get((r, "GROF", "FSTR"), 0.0):
            st.DATA[(r, "GROF", "FSTR")] = g
        if not st.DATA.get((r, "LOSF", "FSTR"), 0.0):
            st.DATA[(r, "LOSF", "FSTR")] = lo
        if not st.DATA.get((r, "FEDM", "FSTR"), 0.0):
            st.DATA[(r, "FEDM", "FSTR")] = g - lo


def NUTS1_aggregate(st: FedtrmState) -> None:
    r"""The NUTS 1 units with NUTS 2 units below them and not themselves a regional unit: the member state's feed
    contents, their NUTS 2 units' straw, then supply/aggreg.gms over those NUTS 2 units.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 63-76):

        $IF NOT %NTSLVL%==0  NUTS1(SRNUTS1) $ SUM(MAP_RR(MS,SRNUTS1),1) = YES;

          RAGG(NUTS1) $ (SUM(MAP_RR(NUTS1,NUTS2),1) and SUM(MAP_RR(MS,NUTS1),1)
                         and (not SUM(SAMEAS(NUTS1,NUTS2),1))) = YES;
          DATA(NUTS1,REQSC,FEED,"Y") = SUM(MAP_RR(MS,NUTS1), DATA(MS,REQSC,FEED,"Y"));
          DATA(NUTS1,"LOSF","STRA","Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"LOSF","STRA","Y"));
          DATA(NUTS1,"GROF","STRA","Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"GROF","STRA","Y"));
        $iftheni.feedpw7 %feedversion%==_pw
          DATA(NUTS1,"LOSF","FSTR","Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"LOSF","FSTR","Y"));
          DATA(NUTS1,"GROF","FSTR","Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"GROF","FSTR","Y"));
          DATA(NUTS1,"FEDM","FSTR","Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"FEDM","FSTR","Y"));
        $endif.feedpw7

        $batinclude 'supply\aggreg.gms' RAGG NUTS2 MAP_RR(RAGG,NUTS2)

    Departures from CAPRI: none."""
    ru = set(st.RU)
    st.NUTS1_RAGG = tuple(n1 for n1 in st.SRNUTS1 if n1 not in ru and st.units_of(n1))
    for n1 in st.SRNUTS1:
        for q in st.REQSC:
            for f in st.FEED:
                v = st.DATA.get((st.MS, q, f), 0.0)
                if v:
                    st.DATA[(n1, q, f)] = v
                else:
                    st.DATA.pop((n1, q, f), None)
    for n1 in st.SRNUTS1:
        kids = st.units_of(n1)
        sums = {(c, i): sum(st.DATA.get((k, c, i), 0.0) for k in kids)
                for c, i in (("LOSF", "STRA"), ("GROF", "STRA"), ("LOSF", "FSTR"), ("GROF", "FSTR"), ("FEDM", "FSTR"))}
        for (c, i), v in sums.items():
            st.DATA[(n1, c, i)] = v
    for n1 in st.NUTS1_RAGG:
        ag.aggreg(st, n1, st.units_of(n1))


def MS_aggregate(st: FedtrmState) -> None:
    r"""The member state with more than one NUTS 1 unit: supply/aggreg.gms over them.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 80-82):

          RAGG(MS) $ (SUM(MAP_RR(MS,NUTS1),1) GT 1) = YES;

        $batinclude 'supply\aggreg.gms' RAGG NUTS1 MAP_RR(RAGG,NUTS1)

    Departures from CAPRI: none."""
    if len(st.SRNUTS1) > 1:
        ag.aggreg(st, st.MS, st.SRNUTS1)


def DATA_MS_straw(st: FedtrmState) -> None:
    r"""The member state's straw production from its levels and straw yields.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 86-88):

        * --- ag: UK very strange
          DATA(MS,"GROF","STRA","Y") =  SUM( PACT_TO_O(MPACT,"STRA"), DATA(MS,MPACT,"LEVL","Y")* DATA(MS,MPACT,"STRA","Y")*0.001);
        $ifi %feedversion%==_pw   DATA(MS,"GROF","FSTR","Y") =  SUM( PACT_TO_O(MPACT,"FSTR"), DATA(MS,MPACT,"LEVL","Y")* DATA(MS,MPACT,"FSTR","Y")*0.001);

    Departures from CAPRI: none."""
    for o in ("STRA", "FSTR"):
        st.DATA[(st.MS, "GROF", o)] = sum(st.DATA.get((st.MS, a, "LEVL"), 0.0) * st.DATA.get((st.MS, a, o), 0.0)
                                          for a, o2 in st.PACT_TO_O if o2 == o and a in st.MPACT) * 0.001


def DATA_GROF_RU(st: FedtrmState) -> None:
    r"""The regional units' gross production of every input and output: their levels times the coefficients (for a
    feed, the animals' use).

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 103):

        DATA(RU,"GROF",IO,"Y")    = SUM(PACT_TO_IO(MPACT,IO), DATA(RU,MPACT,"LEVL","Y")*DATA(RU,MPACT,IO,"Y"))*0.001;

    Departures from CAPRI: none."""
    mp = set(st.MPACT)
    by_io = {}
    for a, io in st.PACT_TO_IO:
        if a in mp:
            by_io.setdefault(io, []).append(a)
    for r in st.RU:
        for io in st.IO:
            v = sum(st.DATA.get((r, a, "LEVL"), 0.0) * st.DATA.get((r, a, io), 0.0) for a in by_io.get(io, ())) * 0.001
            if v:
                st.DATA[(r, "GROF", io)] = v
            else:
                st.DATA.pop((r, "GROF", io), None)


def DATA_GROF_NUTS1(st: FedtrmState) -> None:
    r"""The NUTS 1 units' gross production, the sums of their NUTS 2 units'.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 115):

         DATA(NUTS1,"GROF",IO,"Y") = SUM(MAP_RR(NUTS1,NUTS2), DATA(NUTS2,"GROF",IO,"Y"));

    Departures from CAPRI: none."""
    for n1 in st.SRNUTS1:
        kids = st.units_of(n1)
        for io in st.IO:
            v = sum(st.DATA.get((k, "GROF", io), 0.0) for k in kids)
            if v:
                st.DATA[(n1, "GROF", io)] = v
            else:
                st.DATA.pop((n1, "GROF", io), None)


def v_animReq_start_prep(st: FedtrmState) -> None:
    r"""The requirements' levels start at the requirements.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 137):

         v_animReq.L(RSEU,MAACT,A,REQM) = p_animReq(RSEU,MAACT,A,REQM);

    Departures from CAPRI: none."""
    st.v_animReq_L.update({k: v for k, v in st.p_animReq.items() if k[1] in st.MAACT})


def p_feedQuant_MS(st: FedtrmState) -> None:
    r"""The member state's feed quantities to hold: CAPTRD's gross production of the feeds it produces in the base
    year (the base year's when the simulation year is the base year).

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 170-178):

          p_feedQuant(RSEU,FEED) = 0;
        *
        * req_or_man_fnc needs contents of FEED which were only assigned if already in load_feed.gms we had: p_feedQuant(MS,FEED) > 0
          p_feedQuant(MS,FEED) $ DATA(MS,"GROF",FEED,"BAS") = DATA(MS,"GROF",FEED,"TRD");




          if ( calyea("BAS") eq calyea("Y"), p_feedQuant(MS,FEED) = DATA(MS,"GROF",FEED,"BAS"));

    Departures from CAPRI: none (the simulation year is never the base year here: SIMY 2030, BAS 2017)."""
    st.p_feedQuant.clear()
    for f in st.FEED:
        if st.DATA_BAS.get((st.MS, "GROF", f), 0.0):
            st.p_feedQuant[(st.MS, f)] = st.DATA_TRD.get((st.MS, "GROF", f), 0.0)


def p_maxFeedShare_where_MS_has_none(st: FedtrmState) -> None:
    r"""No feed share and no regional quantity of a feed the member state has no quantity of.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 183-184):

          v_feedQuantReg.fx(RS,FEED) $ (not sum(MAP_RR(MS,RS), p_feedQuant(MS,FEED))) = 0;
          p_maxFeedShare(RS,maact,A,FEED) $ (not sum(MAP_RR(MS,RS), p_feedQuant(MS,FEED))) = 0;

    Departures from CAPRI: none (the fixed zero of v_feedQuantReg is the calibration's: its rows hold it)."""
    none = {f for f in st.FEED if not st.p_feedQuant.get((st.MS, f), 0.0)}
    rs = {st.MS} | set(st.RU)
    for k in [k for k in st.p_maxFeedShare if k[0] in rs and k[3] in none]:
        del st.p_maxFeedShare[k]
    for r in sorted(rs):
        for f in none:
            st.v_feedQuantReg_L[(r, f)] = 0.0


def p_aprDistAnimReq_ALL(st: FedtrmState) -> None:
    r"""The member state's deliveries over its requirements: 1 for every requirement, then for REQC the quantities
    times the feeds' contents over the regional units' requirements times days, herds and technology shares.

    CAPRI's GAMS (baseline/fedtrm_prep.gms l. 188-196):

          p_aprDistAnimReq(MS,"ALL","T",REQM,"Mean") = 1;

          p_aprDistAnimReq(MS,"ALL","T",REQC,"Mean") = SUM( (RU,MAACT,A) $ (MAP_RR(MS,RU) and p_animReq(RU,MAACT,A,REQC)),
             p_animReq(RU,MAACT,A,REQC)*p_animProdDays(RU,MAACT,A)*DATA(RU,MAACT,"LEVL","Y")*p_technFact(RU,MAACT,"LEVL",A) * 0.001);
        *
        * --- Total deliveries from feed divided by total requirements
        *
          p_aprDistAnimReq(MS,"ALL","T",REQC,"Mean") $ p_aprDistAnimReq(MS,"ALL","T",REQC,"Mean")
              = SUM( FEED, p_feedQuant(MS,FEED) * DATA(MS,REQC,FEED,"Y"))/p_aprDistAnimReq(MS,"ALL","T",REQC,"Mean");

    Departures from CAPRI: none."""
    ms = st.MS
    units = st.units_of(ms)
    for q in st.REQM:
        st.p_aprDistAnimReq[(ms, "ALL", "T", q, "Mean")] = 1.0
    for q in st.REQC:
        tot = sum(st.p_animReq.get((r, a, t, q), 0.0) * st.p_animProdDays.get((r, a, t), 0.0)
                  * st.DATA.get((r, a, "LEVL"), 0.0) * st.p_technFact.get((r, a, "LEVL", t), 0.0) * 0.001
                  for r in units for a in st.MAACT for t in st.A if st.p_animReq.get((r, a, t, q), 0.0))
        st.p_aprDistAnimReq[(ms, "ALL", "T", q, "Mean")] = tot
        if tot:
            st.p_aprDistAnimReq[(ms, "ALL", "T", q, "Mean")] = sum(
                st.p_feedQuant.get((ms, f), 0.0) * st.DATA.get((ms, q, f), 0.0) for f in st.FEED) / tot


#: CAPRI's statements of baseline/fedtrm_prep.gms that the calibration reads, in their order
BLOCKS = (DATA_feed_from_trends, v_feedInpCoeff_start, v_feedQuantReg_start, DATA_FSTR_from_STRA, NUTS1_aggregate,
          MS_aggregate, DATA_MS_straw, DATA_GROF_RU, DATA_GROF_NUTS1, v_animReq_start_prep, p_feedQuant_MS,
          p_maxFeedShare_where_MS_has_none, p_aprDistAnimReq_ALL)


def fedtrm_prep(st: FedtrmState) -> FedtrmState:
    r"""baseline/fedtrm_prep.gms on the parts the calibration reads: BLOCKS in order."""
    for block in BLOCKS:
        block(st)
    return st

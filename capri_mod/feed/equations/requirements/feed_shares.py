r"""The feed-share bounds, the fibre-rich feeds and the nutrient densities of the rations (feed/req_or_man_fnc.gms,
'req' mode; moved from capri_mod/feed/equations/req_or_man_fnc_req.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capri_mod.feed.equations.req_or_man_fnc import (BULF, CALF, CALR, DCOW, HEIF, NRUMI, DATA_AGGR_YCOW,  # noqa: F401
                                                     p_stockingRate)
from capri_mod.data.definitions import capri_set
from capri_mod.feed.equations.requirements.state import ACATTLE, A_ALL, FEED, FODDI, ReqState, fibreRichFeed  # noqa: E402




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

r"""CAPRI's aggregation from a lower to a higher regional level (supply/aggreg.gms, called with %1 the aggregates, %2
the lower units and %3 their map), on the symbols the baseline feed calibration reads: the activity levels and their
technology shares, the input and output coefficients, the feed input coefficients, the production days, the
requirements and the feed shares, with P_weightFeedMinMaxSharesWithCorrFactorsFlag 0 (baseline/fedtrm_prep.gms l. 21).

Each function takes the state (an object holding CAPRI's symbols as dictionaries: DATA {(region, column, row): value}
at "Y", v_actLevl_L {(region, activity, A)}, p_technFact {(region, activity, item, A)}, v_feedInpCoeff_L {(region,
activity, A, feed)}, v_feedQuantReg_L {(region, feed)}, v_lossQuant_L {(region, "STRA")}, p_animProdDays {(region,
activity, A)}, p_animReq {(region, activity, A, item)}, p_minFeedShare and p_maxFeedShare {(region, activity, A,
feed)}, and the sets MPACT, MAACT, A, S_TACT, FEED, REQSR_M, REQ_FEED, MAACT_TO_REQM, PACT_TO_IO), one aggregate p and
its lower units kids (CAPRI's %3: the members of p in %2). CAPRI's aggregates of one call are disjoint, so a call per
aggregate is CAPRI's call over the set.

Not ported (not read by the feed calibration): the set-aside obligations (l. 36-45), the premiums (l. 52-55), the
technology factors of the activities with several technologies and the sugar beet's (l. 62-78), the fertiliser
distribution and the manure (l. 90-96), the flag 1 branch (simulation mode, l. 160-185) and CAPREG's part (l. 186-238).

One function per CAPRI statement block. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

#: GAMS's EPS in a comparison: the smallest value that counts as not zero
EPS = 1e-300


def v_actLevl_aggregate(st, p, kids) -> None:
    r"""The lower units' levels where the technology does not exist set to 0, the aggregate's levels their sum, and the
    activity levels of the aggregate and of the lower units the sums over the technologies.

    CAPRI's GAMS (supply/aggreg.gms l. 25-31):

          v_actLevl.L(%2,MPACT,A) $ (NOT p_technFact(%2,MPACT,"LEVL",A)) = 0;
          v_actLevl.L(%1,MPACT,A) = SUM(%3, v_actLevl.L(%2,MPACT,A));
        *
          DATA(%1,MPACT,"LEVL","Y") =  SUM(A,v_actLevl.L(%1,MPACT,A));
          DATA(%2,MPACT,"LEVL","Y") =  SUM(A,v_actLevl.L(%2,MPACT,A));
        *
          DATA(%1,MPACT,"LEVL","Y") $ (DATA(%1,MPACT,"LEVL","Y") le eps) = 0;

    Departures from CAPRI: none."""
    for k in kids:
        for a in st.MPACT:
            for t in st.A:
                if not st.p_technFact.get((k, a, "LEVL", t), 0.0):
                    st.v_actLevl_L.pop((k, a, t), None)
    for a in st.MPACT:
        for t in st.A:
            v = sum(st.v_actLevl_L.get((k, a, t), 0.0) for k in kids)
            if v:
                st.v_actLevl_L[(p, a, t)] = v
            else:
                st.v_actLevl_L.pop((p, a, t), None)
        for r in (p,) + tuple(kids):
            lev = sum(st.v_actLevl_L.get((r, a, t), 0.0) for t in st.A)
            st.DATA[(r, a, "LEVL")] = lev
        if st.DATA[(p, a, "LEVL")] <= EPS:
            st.DATA[(p, a, "LEVL")] = 0.0


def v_feedQuantReg_aggregate(st, p, kids) -> None:
    r"""The aggregate's feed quantities and straw losses the sums of the lower units'.

    CAPRI's GAMS (supply/aggreg.gms l. 33-34):

          v_feedQuantReg.L(%1,FEED)      = SUM(%3, v_feedQuantReg.L(%2,FEED));
          v_lossQuant.L(%1,"STRA")    = SUM(%3, v_lossQuant.L(%2,"STRA"));

    Departures from CAPRI: none."""
    for f in st.FEED:
        st.v_feedQuantReg_L[(p, f)] = sum(st.v_feedQuantReg_L.get((k, f), 0.0) for k in kids)
    st.v_lossQuant_L[(p, "STRA")] = sum(st.v_lossQuant_L.get((k, "STRA"), 0.0) for k in kids)


def DATA_io_aggregate(st, p, kids) -> None:
    r"""The aggregate's input and output coefficients, the lower units' weighted by their levels.

    CAPRI's GAMS (supply/aggreg.gms l. 49-50):

          DATA(%1,MPACT,IO,"Y") $ (PACT_TO_IO(MPACT,IO) and (DATA(%1,MPACT,"LEVL","Y") gt eps))
            =  SUM( %3 $ DATA(%2,MPACT,"LEVL","Y"), DATA(%2,MPACT,IO,"Y")*DATA(%2,MPACT,"LEVL","Y"))/DATA(%1,MPACT,"LEVL","Y");

    Departures from CAPRI: none."""
    for a, io in st.PACT_TO_IO:
        lev = st.DATA.get((p, a, "LEVL"), 0.0)
        if a in st.MPACT and lev > EPS:
            st.DATA[(p, a, io)] = sum(st.DATA.get((k, a, io), 0.0) * st.DATA.get((k, a, "LEVL"), 0.0) for k in kids
                                      if st.DATA.get((k, a, "LEVL"), 0.0)) / lev


def p_technFact_LEVL_aggregate(st, p, kids) -> None:
    r"""The aggregate's technology shares of the levels.

    CAPRI's GAMS (supply/aggreg.gms l. 59-60):

          p_technFact(%1,MPACT,"LEVL",A)
            =  (v_actLevl.L(%1,MPACT,A)/DATA(%1,MPACT,"LEVL","Y")) $ (DATA(%1,MPACT,"LEVL","Y") gt eps);

    Departures from CAPRI: none."""
    for a in st.MPACT:
        lev = st.DATA.get((p, a, "LEVL"), 0.0)
        for t in st.A:
            v = st.v_actLevl_L.get((p, a, t), 0.0) / lev if lev > EPS else 0.0
            if v:
                st.p_technFact[(p, a, "LEVL", t)] = v
            else:
                st.p_technFact.pop((p, a, "LEVL", t), None)


def v_feedInpCoeff_aggregate(st, p, kids) -> None:
    r"""The aggregate's feed input coefficients, the lower units' weighted by their levels where the feed has a maximum
    share there.

    CAPRI's GAMS (supply/aggreg.gms l. 86-88):

          v_feedInpCoeff.L(%1,MAACT,S_TACT,FEED) $ (v_actLevl.L(%1,MAACT,S_TACT) gt eps)
           = SUM(%3 $ p_maxFeedShare(%2,MAACT,S_TACT,FEED), v_feedInpCoeff.L(%2,MAACT,S_TACT,FEED) * v_actLevl.L(%2,MAACT,S_TACT))
                                                   /v_actLevl.L(%1,MAACT,S_TACT);

    Departures from CAPRI: none."""
    for a in st.MAACT:
        for t in st.S_TACT:
            lev = st.v_actLevl_L.get((p, a, t), 0.0)
            if lev > EPS:
                for f in st.FEED:
                    st.v_feedInpCoeff_L[(p, a, t, f)] = sum(
                        st.v_feedInpCoeff_L.get((k, a, t, f), 0.0) * st.v_actLevl_L.get((k, a, t), 0.0) for k in kids
                        if st.p_maxFeedShare.get((k, a, t, f), 0.0)) / lev


def DATA_feed_aggregate(st, p, kids) -> None:
    r"""The aggregate's feed coefficients of DATA from its feed input coefficients and technology shares.

    CAPRI's GAMS (supply/aggreg.gms l. 98-99):

          DATA(%1,MAACT,FEED,"Y") = SUM(S_TACT $ p_technFact(%1,MAACT,"LEVL",S_TACT),
                                    v_feedInpCoeff.L(%1,MAACT,S_TACT,FEED) * p_technFact(%1,MAACT,"LEVL",S_TACT));

    Departures from CAPRI: none."""
    for a in st.MAACT:
        for f in st.FEED:
            st.DATA[(p, a, f)] = sum(st.v_feedInpCoeff_L.get((p, a, t, f), 0.0) * st.p_technFact.get((p, a, "LEVL", t), 0.0)
                                     for t in st.S_TACT if st.p_technFact.get((p, a, "LEVL", t), 0.0))


def p_animProdDays_aggregate(st, p, kids) -> None:
    r"""The aggregate's production days, the lower units' weighted by their levels.

    CAPRI's GAMS (supply/aggreg.gms l. 103-104):

          p_animProdDays(%1,MAACT,S_TACT) $ (v_actLevl.L(%1,MAACT,S_TACT) gt eps)
            = SUM(%3,  p_animProdDays(%2,MAACT,S_TACT) * v_actLevl.L(%2,MAACT,S_TACT))/v_actLevl.L(%1,MAACT,S_TACT);

    Departures from CAPRI: none."""
    for a in st.MAACT:
        for t in st.S_TACT:
            lev = st.v_actLevl_L.get((p, a, t), 0.0)
            if lev > EPS:
                st.p_animProdDays[(p, a, t)] = sum(st.p_animProdDays.get((k, a, t), 0.0) * st.v_actLevl_L.get((k, a, t), 0.0)
                                                   for k in kids) / lev


def p_animReq_aggregate(st, p, kids) -> None:
    r"""The aggregate's requirements: none without a level and days; the dry matter intake and the requirements of
    REQSR_M the lower units' weighted by their levels and days.

    CAPRI's GAMS (supply/aggreg.gms l. 108-117):

          p_animReq(%1,MAACT,S_TACT,REQSR_M)    $ ((NOT (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT))) $ MAACT_TO_REQM(MAACT,REQSR_M)) = 0.0;
          p_animReq(%1,MAACT,S_TACT,REQ_FEED) $ ((NOT (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)))) = 0.0;
        *
          p_animReq(%1,MAACT,S_TACT,"DRMA") $ ( (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)) gt eps)
            = SUM( %3, p_animReq(%2,MAACT,S_TACT,"DRMA") * v_actLevl.L(%2,MAACT,S_TACT)*p_animProdDays(%2,MAACT,S_TACT))/
                                                     (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT));
        *
          p_animReq(%1,MAACT,S_TACT,REQSR_M) $ ((v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)) $ MAACT_TO_REQM(MAACT,REQSR_M) )
            = SUM( %3, p_animReq(%2,MAACT,S_TACT,REQSR_M) * v_actLevl.L(%2,MAACT,S_TACT)*p_animProdDays(%2,MAACT,S_TACT))/
                                                           (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT));

    Departures from CAPRI: none."""
    reqm = set(st.MAACT_TO_REQM)
    for a in st.MAACT:
        for t in st.S_TACT:
            w = st.v_actLevl_L.get((p, a, t), 0.0) * st.p_animProdDays.get((p, a, t), 0.0)
            if not w:
                for q in st.REQSR_M:
                    if (a, q) in reqm:
                        st.p_animReq.pop((p, a, t, q), None)
                for q in st.REQ_FEED:
                    st.p_animReq.pop((p, a, t, q), None)
            wk = {k: st.v_actLevl_L.get((k, a, t), 0.0) * st.p_animProdDays.get((k, a, t), 0.0) for k in kids}
            if w > EPS:
                st.p_animReq[(p, a, t, "DRMA")] = sum(st.p_animReq.get((k, a, t, "DRMA"), 0.0) * wk[k] for k in kids) / w
            if w:
                for q in st.REQSR_M:
                    if (a, q) in reqm:
                        st.p_animReq[(p, a, t, q)] = sum(st.p_animReq.get((k, a, t, q), 0.0) * wk[k] for k in kids) / w


def DATA_DRMA_aggregate(st, p, kids) -> None:
    r"""The aggregate's dry matter content of a feed without one: the mean over the lower units that have it.

    CAPRI's GAMS (supply/aggreg.gms l. 119-120):

          DATA(%1,"DRMA",FEED,"Y") $ (not DATA(%1,"DRMA",FEED,"Y"))
                                   = (SUM(%3, DATA(%2,"DRMA",FEED,"Y")) / SUM(%3 $ DATA(%2,"DRMA",FEED,"Y"),1)) $ SUM(%3 $ DATA(%2,"DRMA",FEED,"Y"),1);

    Departures from CAPRI: none."""
    for f in st.FEED:
        if not st.DATA.get((p, "DRMA", f), 0.0):
            ks = [k for k in kids if st.DATA.get((k, "DRMA", f), 0.0)]
            if ks:
                st.DATA[(p, "DRMA", f)] = sum(st.DATA[(k, "DRMA", f)] for k in ks) / len(ks)


def feed_shares_aggregate(st, p, kids) -> None:
    r"""With P_weightFeedMinMaxSharesWithCorrFactorsFlag 0: the aggregate's feeds' rows of p_animReq, and its minimum
    and maximum feed shares, the lower units' weighted by their dry matter intake (the shares also by 1 -/+ the feed's
    row).

    CAPRI's GAMS (supply/aggreg.gms l. 122-135):

          if ( p_weightFeedMinMaxSharesWithCorrFactorsFlag EQ 0,


            p_animReq(%1,MAACT,S_TACT,REQ_FEED)           $ (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA"))
              = SUM(%3, p_animReq(%2,MAACT,S_TACT,REQ_FEED)* v_actLevl.L(%2,MAACT,S_TACT)*p_animProdDays(%2,MAACT,S_TACT)*p_animReq(%2,MAACT,S_TACT,"DRMA")) /
                                                    (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA"));
        *
            p_minFeedShare(%1,MAACT,S_TACT,FEED)                $ (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA")*(1-p_animReq(%1,MAACT,S_TACT,FEED)))
              = SUM(%3, p_minFeedShare(%2,MAACT,S_TACT,FEED)     * v_actLevl.L(%2,MAACT,S_TACT)*p_animProdDays(%2,MAACT,S_TACT)*p_animReq(%2,MAACT,S_TACT,"DRMA")*(1-p_animReq(%2,MAACT,S_TACT,FEED)))/
                                                    (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA")*(1-p_animReq(%1,MAACT,S_TACT,FEED)));
        *
            p_maxFeedShare(%1,MAACT,S_TACT,FEED)                $ (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA")*(1+p_animReq(%1,MAACT,S_TACT,FEED)))
              = SUM(%3, p_maxFeedShare(%2,MAACT,S_TACT,FEED) * v_actLevl.L(%2,MAACT,S_TACT)*p_animProdDays(%2,MAACT,S_TACT)*p_animReq(%2,MAACT,S_TACT,"DRMA")*(1+p_animReq(%2,MAACT,S_TACT,FEED)))/
                                                    (v_actLevl.L(%1,MAACT,S_TACT)*p_animProdDays(%1,MAACT,S_TACT)*p_animReq(%1,MAACT,S_TACT,"DRMA")*(1+p_animReq(%1,MAACT,S_TACT,FEED)));

    Departures from CAPRI: none."""
    for a in st.MAACT:
        for t in st.S_TACT:
            def dm(r):
                return (st.v_actLevl_L.get((r, a, t), 0.0) * st.p_animProdDays.get((r, a, t), 0.0)
                        * st.p_animReq.get((r, a, t, "DRMA"), 0.0))
            w = dm(p)
            if not w:
                continue
            wk = {k: dm(k) for k in kids}
            for f in st.REQ_FEED:
                st.p_animReq[(p, a, t, f)] = sum(st.p_animReq.get((k, a, t, f), 0.0) * wk[k] for k in kids) / w
            for f in st.FEED:
                for share, sg in ((st.p_minFeedShare, -1.0), (st.p_maxFeedShare, 1.0)):
                    den = w * (1.0 + sg * st.p_animReq.get((p, a, t, f), 0.0))
                    if den:
                        v = sum(share.get((k, a, t, f), 0.0) * wk[k] * (1.0 + sg * st.p_animReq.get((k, a, t, f), 0.0))
                                for k in kids) / den
                        if v:
                            share[(p, a, t, f)] = v
                        else:
                            share.pop((p, a, t, f), None)


#: CAPRI's statements of supply/aggreg.gms that the feed calibration reads, in their order
BLOCKS = (v_actLevl_aggregate, v_feedQuantReg_aggregate, DATA_io_aggregate, p_technFact_LEVL_aggregate,
          v_feedInpCoeff_aggregate, DATA_feed_aggregate, p_animProdDays_aggregate, p_animReq_aggregate,
          DATA_DRMA_aggregate, feed_shares_aggregate)


def aggreg(st, p, kids) -> None:
    r"""supply/aggreg.gms for one aggregate p over its lower units kids: BLOCKS in order."""
    for block in BLOCKS:
        block(st, p, kids)

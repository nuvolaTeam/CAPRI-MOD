r"""CAPRI's prior expectations of the baseline feed calibration (feed/fedtrm_prior_pw.gms; CAPRI star 3.0, feed version
"_pw"): the animals' dry matter intake, split into the feed aggregates by CAPRI's expected shares (p_FeedAggrPrior,
capri_data/2017/feed/fedtrm_params.csv) corrected in ten rounds towards the member state's supply of each aggregate;
the feeds' shares within an aggregate from the region's supply in dry matter; the prior mean of each feed input
coefficient (in fresh matter) and its standard error.

On FedtrmState (capri_mod/feed/equations/fedtrm_prep.py) after fedtrm_prep, for one member state and its units
(CAPRI's RallInMS). Written: p_FeedAggrPrior_iter, p_feedBalance, p_feedInpCoeffDRMA, p_feedQuantDRMA,
p_FeedShareInAggr, p_feedInpCoeff {(region, activity, "T", feed, "Mean" | "STDE")}; p_maxFeedShare at 0 where the
prior mean is not positive.

One function per CAPRI statement block. Departures from CAPRI: none in the functions.
"""
from __future__ import annotations

import csv
from pathlib import Path

#: the requirements of the priors (l. 24-27: CAPRI's statements set ReqPrior)
ReqPrior = ("ENNE", "CRPR", "DRMA")
#: the rounds of the aggregates' corrections (l. 158: corrFeedAggrRound1 * corrFeedAggrRound10)
N_ROUNDS = 10

_PARAMS = Path(__file__).resolve().parents[3] / "capri_data" / "2017" / "feed" / "fedtrm_params.csv"


def load_p_FeedAggrPrior(path: Path = _PARAMS) -> dict:
    """CAPRI's TABLE p_FeedAggrPrior (feed/fedtrm_prior_pw.gms l. 39-59), {(animal, aggregate, item): value}, from
    capri_data/2017/feed/fedtrm_params.csv (tools/build/build_fedtrm_params.py)."""
    with open(path, newline="") as f:
        return {(r["key1"], r["key2"], r["key3"]): float(r["value"]) for r in csv.DictReader(f)
                if r["symbol"] == "p_FeedAggrPrior"}


def _aggr_of(st) -> dict:
    """{feed aggregate: its feeds} of CAPRI's Feed_FeedAggr, in CAPRI's feed order."""
    out = {g: [] for g in st.FeedAggr}
    for f in st.FEED:
        for f2, g in st.Feed_FeedAggr:
            if f2 == f:
                out[g].append(f)
    return out


def p_FeedAggrPrior_rough_total(st) -> None:
    r"""The roughage's expected share the rest of the concentrates' and the other feeds'; the total's share 1.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 61-62):

        p_FeedAggrPrior(maact,"FeedRough","shInAact") = 1 - p_FeedAggrPrior(maact,"FeedCons","shInAact") - p_FeedAggrPrior(maact,"FeedOth","shInAact");
        p_FeedAggrPrior(maact,"FeedTotal","shInAact") = 1;

    Departures from CAPRI: none."""
    p = st.p_FeedAggrPrior
    for a in st.MAACT:
        p[(a, "FeedRough", "shInAact")] = 1.0 - p.get((a, "FeedCons", "shInAact"), 0.0) - p.get((a, "FeedOth", "shInAact"), 0.0)
        p[(a, "FeedTotal", "shInAact")] = 1.0


def p_feedBalance_AnimReq(st) -> None:
    r"""The member state's yearly requirements per animal (ENNE, CRPR, DRMA); its dry matter intake bounded by the
    energy requirement at the total ration's maximum and minimum energy density.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 67-82):

        p_feedBalance(MS,"FeedTotal",maact,ReqPrior,"AnimReq")   = p_animReq(MS,maact,"T",ReqPrior) * p_animProdDays(MS,maact,"T");


        *  for some animal types the DRMA calculated in requirement functions are rather inconsistent with energy requirements
        *  ---> adjust DRMA if it is not in line with a ENNE
        *
        p_feedBalance(MS,"FeedTotal",maact,"DRMA_AnimReq","AnimReq")
          = p_animReq(MS,maact,"T","DRMA") * p_animProdDays(MS,maact,"T");
        p_feedBalance(MS,"FeedTotal",maact,"DRMA_UppLim","AnimReq")
          = p_animReq(MS,maact,"T","ENNE")/ p_nutContFeed(MS,MAACT,"T","ENNE","FeedTotal","Min") * p_animProdDays(MS,maact,"T");
        p_feedBalance(MS,"FeedTotal",maact,"DRMA_LowLim","AnimReq")
          = p_animReq(MS,maact,"T","ENNE") / p_nutContFeed(MS,MAACT,"T","ENNE","FeedTotal","Max")  * p_animProdDays(MS,maact,"T");

        p_feedBalance(MS,"FeedTotal",maact,"DRMA","AnimReq")
          = MAX(p_feedBalance(MS,"FeedTotal",maact,"DRMA_LowLim","AnimReq"),
                MIN(p_feedBalance(MS,"FeedTotal",maact,"DRMA_UppLim","AnimReq"), p_feedBalance(MS,"FeedTotal",maact,"DRMA_AnimReq","AnimReq")));

    Departures from CAPRI: none."""
    ms, fb = st.MS, st.p_feedBalance
    for a in st.MAACT:
        d = st.p_animProdDays.get((ms, a, "T"), 0.0)
        for q in ReqPrior:
            fb[(ms, "FeedTotal", a, q, "AnimReq")] = st.p_animReq.get((ms, a, "T", q), 0.0) * d
        fb[(ms, "FeedTotal", a, "DRMA_AnimReq", "AnimReq")] = st.p_animReq.get((ms, a, "T", "DRMA"), 0.0) * d
        e = st.p_animReq.get((ms, a, "T", "ENNE"), 0.0)
        nmin = st.p_NutContFeed.get((ms, a, "T", "ENNE", "FeedTotal", "MIN"), 0.0)
        nmax = st.p_NutContFeed.get((ms, a, "T", "ENNE", "FeedTotal", "MAX"), 0.0)
        upp = e / nmin * d if nmin else 0.0
        low = e / nmax * d if nmax else 0.0
        fb[(ms, "FeedTotal", a, "DRMA_UppLim", "AnimReq")] = upp
        fb[(ms, "FeedTotal", a, "DRMA_LowLim", "AnimReq")] = low
        fb[(ms, "FeedTotal", a, "DRMA", "AnimReq")] = max(low, min(upp, fb[(ms, "FeedTotal", a, "DRMA_AnimReq", "AnimReq")]))


def p_feedBalance_allAni_AnimReq(st) -> None:
    r"""The member state's total requirements, and its dry matter intake by feed aggregate at the expected shares.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 85-92):

        p_feedBalance(MS,"FeedTotal","allAni",ReqPrior,"AnimReq" )
          = sum((maact), p_feedBalance(MS,"FeedTotal",maact,ReqPrior,"AnimReq") * DATA(MS,maact,"LEVL","Y") / 1000);

        * split total requirements to feed aggregates using prior expectations
        * (i.e. How much DRMA is expected to be required by roughage, concentrate feed and other feed
        p_feedBalance(MS,FeedAggr,"allAni","DRMA","AnimReq")
           = sum((maact), p_FeedAggrPrior(maact,FeedAggr,"shInAact")
           * p_feedBalance(MS,"FeedTotal",maact,"DRMA","AnimReq") * DATA(MS,maact,"LEVL","Y") / 1000);

    Departures from CAPRI: none."""
    ms, fb = st.MS, st.p_feedBalance
    lev = {a: st.DATA.get((ms, a, "LEVL"), 0.0) for a in st.MAACT}
    for q in ReqPrior:
        fb[(ms, "FeedTotal", "allAni", q, "AnimReq")] = sum(fb.get((ms, "FeedTotal", a, q, "AnimReq"), 0.0) * lev[a] / 1000
                                                            for a in st.MAACT)
    for g in st.FeedAggr:
        fb[(ms, g, "allAni", "DRMA", "AnimReq")] = sum(
            st.p_FeedAggrPrior.get((a, g, "shInAact"), 0.0) * fb.get((ms, "FeedTotal", a, "DRMA", "AnimReq"), 0.0)
            * lev[a] / 1000 for a in st.MAACT)


def p_feedBalance_FedmSup(st) -> None:
    r"""The feeds' supply of every unit: DATA's feed use.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 95):

        p_feedBalance(RallInMS,FEED,"allAni","FEDM","FedmSup") = DATA(RallInMS,"FEDM",FEED,"Y");

    Departures from CAPRI: none."""
    for r in st.rall_in_ms():
        for f in st.FEED:
            st.p_feedBalance[(r, f, "allAni", "FEDM", "FedmSup")] = st.DATA.get((r, "FEDM", f), 0.0)


def p_feedBalance_FedmSupOri(st) -> None:
    r"""The fodder's supply of every unit (straw apart): the fodder outputs' production less the member state's loss
    rate, the silage maize less the share of energy maize.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 98-111):

        p_feedBalance(RallInMS,FODDI,"allAni","FEDM","FedmSupOri")    $ (not sameas("FSTR",FODDI))
           = SUM( (MPACT,FODDO) $ (FEED_TO_O(FODDI,FODDO) and DATA(RallInMS,"GROF",FODDO,"Y")),
        *          correct for losses and non feed use (exogenous demand)
        *          In the database exogenous demand is stored as INDM, in simulation mode it is transfered to the parameter p_exoDemand
        *          (allows exogenous shifts needed in some scenarios)
              (  DATA(RallInMS,MPACT,"LEVL","Y")*DATA(RallInMS,MPACT,FODDO,"Y")
        *              correct for loss rate
                 * (1.-SUM(R_RAGG(RallInMS,MS) $ DATA(MS,"GROF",FODDO,"Y"),
                           DATA(MS,"LOSF",FODDO,"Y")/DATA(MS,"GROF",FODDO,"Y")))
        *              correct for energy maize that does not deliver fodder (in Germany 50% of MAIF)
                 * (1-(  p_exoDemand(RallInMS,"DEMD",FODDO)
                      / (p_exoDemand(RallInMS,"DEMD",FODDO)+DATA(RallInMS,"GROF",FODDI,"Y")))
                      $ ((p_exoDemand(RallInMS,"DEMD",FODDO)+DATA(RallInMS,"GROF",FODDI,"Y")) $ SAMEAS(FODDO,"MAIF"))))
                ) * 0.001;

    Departures from CAPRI: none."""
    ms = st.MS
    for r in st.rall_in_ms():
        for fi in st.FODDI:
            if fi == "FSTR":
                continue
            tot = 0.0
            for fi2, fo in st.FEED_TO_O:
                if fi2 != fi or not st.DATA.get((r, "GROF", fo), 0.0):
                    continue
                g_ms = st.DATA.get((ms, "GROF", fo), 0.0)
                loss = st.DATA.get((ms, "LOSF", fo), 0.0) / g_ms if g_ms else 0.0
                if fo == "MAIF":
                    dem = st.p_exoDemand.get((r, "DEMD", fo), 0.0)
                    den = dem + st.DATA.get((r, "GROF", fi), 0.0)
                    corr = 1.0 - (dem / den if den else 0.0)
                else:
                    corr = 1.0
                for a in st.MPACT:
                    y = st.DATA.get((r, a, fo), 0.0)
                    if y:
                        tot += st.DATA.get((r, a, "LEVL"), 0.0) * y * (1.0 - loss) * corr
            st.p_feedBalance[(r, fi, "allAni", "FEDM", "FedmSupOri")] = tot * 0.001


def p_feedBalance_FedmSup_reaggregated(st) -> None:
    r"""The fodder's supply re-aggregated: the NUTS 2 units' own, the NUTS 1 units' and the member state's the sums of
    their NUTS 2 units'.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 114-119):

        p_feedBalance(SRNUTS2,FODDI,"allAni","FEDM","FedmSup")
          = p_feedBalance(SRNUTS2,FODDI,"allAni","FEDM","FedmSupOri");
        p_feedBalance(SRNUTS1,FODDI,"allAni","FEDM","FedmSup")
          = Sum(MAP_RR(SRNUTS1,SRNUTS2), p_feedBalance(SRNUTS2,FODDI,"allAni","FEDM","FedmSupOri"));
        p_feedBalance(MS,FODDI,"allAni","FEDM","FedmSup")
          = Sum(MAP_RR(MS,SRNUTS2), p_feedBalance(SRNUTS2,FODDI,"allAni","FEDM","FedmSupOri"));

    Departures from CAPRI: none."""
    fb, n2 = st.p_feedBalance, set(st.SRNUTS2)
    for fi in st.FODDI:
        for r in st.SRNUTS2:
            fb[(r, fi, "allAni", "FEDM", "FedmSup")] = fb.get((r, fi, "allAni", "FEDM", "FedmSupOri"), 0.0)
        for r in st.SRNUTS1:
            fb[(r, fi, "allAni", "FEDM", "FedmSup")] = sum(fb.get((k, fi, "allAni", "FEDM", "FedmSupOri"), 0.0)
                                                           for (a, k) in sorted(st.MAP_RR) if a == r and k in n2)
        fb[(st.MS, fi, "allAni", "FEDM", "FedmSup")] = sum(fb.get((k, fi, "allAni", "FEDM", "FedmSupOri"), 0.0)
                                                           for (a, k) in sorted(st.MAP_RR) if a == st.MS and k in n2)


def p_feedBalance_FSTR(st) -> None:
    r"""Straw's supply: none in the units, the member state's 5% of its straw production.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 122-124):

        p_feedBalance(RallInMS,"FSTR","allAni","FEDM","FedmSup") = 0;
        p_feedBalance(MS,"FSTR","allAni","FEDM","FedmSup")
             = SUM( PACT_TO_O(MPACT,"STRA"), DATA(MS,MPACT,"LEVL","Y")*DATA(MS,MPACT,"STRA","Y")*0.001) * 0.05;

    Departures from CAPRI: none."""
    for r in st.rall_in_ms():
        st.p_feedBalance[(r, "FSTR", "allAni", "FEDM", "FedmSup")] = 0.0
    st.p_feedBalance[(st.MS, "FSTR", "allAni", "FEDM", "FedmSup")] = sum(
        st.DATA.get((st.MS, a, "LEVL"), 0.0) * st.DATA.get((st.MS, a, "STRA"), 0.0) * 0.001
        for a, o in st.PACT_TO_O if o == "STRA" and a in st.MPACT) * 0.05


def p_feedBalance_FedmSup_contents(st) -> None:
    r"""The member state's supply of energy, protein and dry matter by feed and by feed aggregate.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 127-128):

        p_feedBalance(MS,FEED,"allAni",ReqPrior,"FedmSup")    =  DATA(MS,ReqPrior,FEED,"Y") *  p_feedBalance(MS,FEED,"allAni","FEDM","FedmSup");
        p_feedBalance(MS,FeedAggr,"allAni",ReqPrior,"FedmSup")= sum(Feed_FeedAggr(Feed,FeedAggr), p_feedBalance(MS,FEED,"allAni",ReqPrior,"FedmSup"));

    Departures from CAPRI: none."""
    ms, fb, agg = st.MS, st.p_feedBalance, _aggr_of(st)
    for q in ReqPrior:
        for f in st.FEED:
            fb[(ms, f, "allAni", q, "FedmSup")] = st.DATA.get((ms, q, f), 0.0) * fb.get((ms, f, "allAni", "FEDM", "FedmSup"), 0.0)
        for g in st.FeedAggr:
            fb[(ms, g, "allAni", q, "FedmSup")] = sum(fb.get((ms, f, "allAni", q, "FedmSup"), 0.0) for f in agg[g])


def p_feedBalance_rounds(st) -> None:
    r"""Ten rounds of corrections: each aggregate's share in every animal's intake times the member state's supply
    over its expected use of the aggregate, the factor bounded per animal by maxCorrDown and maxCorrUp.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 162-189):

        p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter") = p_FeedAggrPrior(maact,FeedAggr,"shInAact");
        *   Total feed intake of aggregates in terms of DRMA based on "Animreq * prior_share" in country MS:
        p_feedBalance(MS,FeedAggr,"allAni","DRMA","Iter") = p_feedBalance(MS,FeedAggr,"allAni","DRMA","AnimReq");

        Loop(corrFeedAggrRound,

        *   Country level correction factor for feed aggregate shares = availability(FeedAgr) / feeduse(FeedAgr) :
        *   => Shares will be increased(decreased) if availability is larger(smaller) than feeduse...
            p_feedBalance(MS,FeedAggr,"allAni","CorrFac",corrFeedAggrRound) $ p_feedBalance(MS,FeedAggr,"allAni","DRMA","Iter")
              = p_feedBalance(MS,FeedAggr,"allAni","DRMA","FedmSup") / p_feedBalance(MS,FeedAggr,"allAni","DRMA","Iter");

        *   ... but not more than bounds specific for activities permit:
            p_feedBalance(MS,FeedAggr,maact,"CorrFac",corrFeedAggrRound) $  p_feedBalance(MS,FeedAggr,"allAni","DRMA","Iter")
              = max(p_FeedAggrPrior(maact,FeedAggr,"maxCorrDown"),
                    min(p_FeedAggrPrior(maact,FeedAggr,"maxCorrUp"), p_feedBalance(MS,FeedAggr,"allAni","CorrFac",corrFeedAggrRound)));

        *   corrected shares for feed aggregates in total DRMA feed intake of activities (based on the previously defined correction factor):
           p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter")
             = p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter")* p_feedBalance(MS,FeedAggr,maact,"CorrFac",corrFeedAggrRound);

        *   re-estimate feed use of aggregates based on corrected shares:
            p_feedBalance(MS,FeedAggr,"allAni","DRMA",corrFeedAggrRound)
             = sum((maact), p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter")
                            * p_feedBalance(MS,"FeedTotal",maact,"DRMA","AnimReq") * DATA(MS,maact,"LEVL","Y") / 1000);

        *   copy re-estimated feed use of aggregates to position entering the correction formula above:
            p_feedBalance(MS,FeedAggr,"allAni","DRMA","Iter") = p_feedBalance(MS,FeedAggr,"allAni","DRMA",corrFeedAggrRound);
        );

    Departures from CAPRI: none."""
    ms, fb, pr = st.MS, st.p_feedBalance, st.p_FeedAggrPrior
    lev = {a: st.DATA.get((ms, a, "LEVL"), 0.0) for a in st.MAACT}
    for g in st.FeedAggr:
        for a in st.MAACT:
            fb[(ms, g, a, "shInAact", "Iter")] = pr.get((a, g, "shInAact"), 0.0)
        fb[(ms, g, "allAni", "DRMA", "Iter")] = fb.get((ms, g, "allAni", "DRMA", "AnimReq"), 0.0)
    for k in range(1, N_ROUNDS + 1):
        rnd = f"corrFeedAggrRound{k}"
        for g in st.FeedAggr:
            it = fb.get((ms, g, "allAni", "DRMA", "Iter"), 0.0)
            if it:
                cf = fb.get((ms, g, "allAni", "DRMA", "FedmSup"), 0.0) / it
                fb[(ms, g, "allAni", "CorrFac", rnd)] = cf
                for a in st.MAACT:
                    fb[(ms, g, a, "CorrFac", rnd)] = max(pr.get((a, g, "maxCorrDown"), 0.0),
                                                         min(pr.get((a, g, "maxCorrUp"), 0.0), cf))
            for a in st.MAACT:
                fb[(ms, g, a, "shInAact", "Iter")] = (fb.get((ms, g, a, "shInAact", "Iter"), 0.0)
                                                      * fb.get((ms, g, a, "CorrFac", rnd), 0.0))
            fb[(ms, g, "allAni", "DRMA", rnd)] = sum(
                fb[(ms, g, a, "shInAact", "Iter")] * fb.get((ms, "FeedTotal", a, "DRMA", "AnimReq"), 0.0) * lev[a] / 1000
                for a in st.MAACT)
            fb[(ms, g, "allAni", "DRMA", "Iter")] = fb[(ms, g, "allAni", "DRMA", rnd)]


def p_feedInpCoeffDRMA_adjusted(st) -> None:
    r"""The corrected shares' sum, and the adjusted dry matter intake per animal and aggregate.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 192-197):

        p_feedBalance(MS,"FeedTotal",maact,"shInAact","Iter") = sum(FeedAggr, p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter"));

        *   store adjusted DRMA intake per animal and year after scaling to match DRMA supplied with feed
        p_feedInpCoeffDRMA(MS,maact,"T","FeedTotal","AnimReq") = p_feedBalance(MS,"FeedTotal",maact,"DRMA","AnimReq");
        p_feedInpCoeffDRMA(MS,maact,"T",FeedAggr,"Adjusted")   = p_feedBalance(MS,"FeedTotal",maact,"DRMA","AnimReq")
                                                               * p_feedBalance(MS,FeedAggr,maact,"shInAact","Iter");

    Departures from CAPRI: none."""
    ms, fb, fd = st.MS, st.p_feedBalance, st.p_feedInpCoeffDRMA
    for a in st.MAACT:
        fb[(ms, "FeedTotal", a, "shInAact", "Iter")] = sum(fb.get((ms, g, a, "shInAact", "Iter"), 0.0) for g in st.FeedAggr)
        intake = fb.get((ms, "FeedTotal", a, "DRMA", "AnimReq"), 0.0)
        fd[(ms, a, "T", "FeedTotal", "AnimReq")] = intake
        for g in st.FeedAggr:
            fd[(ms, a, "T", g, "Adjusted")] = intake * fb.get((ms, g, a, "shInAact", "Iter"), 0.0)


def p_feedQuantDRMA_FEDM(st) -> None:
    r"""Every unit's feed supply in dry matter (the member state's dry matter contents), by feed and by aggregate.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 200-203):

        p_feedQuantDRMA(RallInMS,FEED,"FEDM")
          =  p_feedBalance(RallInMS,FEED,"allAni","FEDM","FedmSup") * sum(MAP_RR(MS,RallInMS), DATA(MS,"DRMA",FEED,"Y"));
        p_feedQuantDRMA(RallInMS,FeedAggr,"FEDM")
          = sum(Feed_FeedAggr(FEED,FeedAggr), p_feedQuantDRMA(RallInMS,FEED,"FEDM"));

    Departures from CAPRI: none."""
    q, agg = st.p_feedQuantDRMA, _aggr_of(st)
    for r in st.rall_in_ms():
        for f in st.FEED:
            q[(r, f, "FEDM")] = st.p_feedBalance.get((r, f, "allAni", "FEDM", "FedmSup"), 0.0) * st.DATA.get((st.MS, "DRMA", f), 0.0)
        for g in st.FeedAggr:
            q[(r, g, "FEDM")] = sum(q[(r, f, "FEDM")] for f in agg[g])


def p_FeedShareInAggr_RegMean(st) -> None:
    r"""Each feed's share in its aggregate's supply in dry matter, the same for every animal; none for the total.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 206-211):

        p_FeedShareInAggr(RallInMS,MAACT,"T",Feed,FeedAggr,"RegMean") $ ( Feed_FeedAggr(FEED,FeedAggr)
                                                                        $ p_feedQuantDRMA(RallInMS,FeedAggr,"FEDM"))
          = p_feedQuantDRMA(RallInMS,FEED,"FEDM") / p_feedQuantDRMA(RallInMS,FeedAggr,"FEDM");

        *  the formula above calculates also for FeedTotal which should be deleted
        p_FeedShareInAggr(RallInMS,MAACT,"T",Feed,"FeedTotal","RegMean") = 0;

    Departures from CAPRI: none."""
    q, agg = st.p_feedQuantDRMA, _aggr_of(st)
    for r in st.rall_in_ms():
        for g in st.FeedAggr:
            if g == "FeedTotal" or not q.get((r, g, "FEDM"), 0.0):
                continue
            for f in agg[g]:
                v = q.get((r, f, "FEDM"), 0.0) / q[(r, g, "FEDM")]
                for a in st.MAACT:
                    st.p_FeedShareInAggr[(r, a, "T", f, g, "RegMean")] = v


def p_feedInpCoeffDRMA_PRIOR(st) -> None:
    r"""The prior coefficient in dry matter of a feed with a maximum share: the member state's adjusted intake of each
    aggregate holding the feed times the feed's share in the unit's supply of it.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 218-220):

        p_feedInpCoeffDRMA(RallInMS,maact,"T",Feed,"PRIOR") $ p_maxFeedShare(RallInMS,MAACT,"T",FEED)
          = sum((MAP_RR(MS,RallInMS),Feed_FeedAggr(FEED,FeedAggr)), p_feedInpCoeffDRMA(MS,maact,"T",FeedAggr,"Adjusted")
                                                                  * p_FeedShareInAggr(RallInMS,MAACT,"T",Feed,FeedAggr,"RegMean"));

    Departures from CAPRI: none."""
    ms, fd, sh = st.MS, st.p_feedInpCoeffDRMA, st.p_FeedShareInAggr
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for f in st.FEED:
                if st.p_maxFeedShare.get((r, a, "T", f), 0.0):
                    fd[(r, a, "T", f, "PRIOR")] = sum(fd.get((ms, a, "T", g, "Adjusted"), 0.0)
                                                      * sh.get((r, a, "T", f, g, "RegMean"), 0.0)
                                                      for f2, g in st.Feed_FeedAggr if f2 == f)


def p_feedInpCoeffDRMA_Mean(st) -> None:
    r"""The expected use of each feed at the prior coefficients, its scaling to the unit's supply, and the scaled prior
    mean in dry matter.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 223-232):

        p_feedQuantDRMA(RallInMS,FEED,"PRIOR")
          =  SUM((maact), p_feedInpCoeffDRMA(RallInMS,maact,"T",Feed,"PRIOR") * DATA(RallInMS,maact,"LEVL","Y") * 0.001);

        *  calculate scaling factor and adjust if regional/national feed demand+supply is known
        *  (i.e. for all feed at national level, for FODDI also at regional scale)
        p_feedQuantDRMA(RallInMS,FEED,"SCALE") $ p_feedQuantDRMA(RallInMS,FEED,"PRIOR")
          =  p_feedQuantDRMA(RallInMS,FEED,"FEDM") / p_feedQuantDRMA(RallInMS,FEED,"PRIOR");

        p_feedInpCoeffDRMA(RallInMS,maact,"T",Feed,"Mean")
          = p_feedInpCoeffDRMA(RallInMS,maact,"T",Feed,"PRIOR") * p_feedQuantDRMA(RallInMS,FEED,"SCALE");

    Departures from CAPRI: none."""
    fd, q = st.p_feedInpCoeffDRMA, st.p_feedQuantDRMA
    for r in st.rall_in_ms():
        for f in st.FEED:
            q[(r, f, "PRIOR")] = sum(fd.get((r, a, "T", f, "PRIOR"), 0.0) * st.DATA.get((r, a, "LEVL"), 0.0) * 0.001
                                     for a in st.MAACT)
            q[(r, f, "SCALE")] = q[(r, f, "FEDM")] / q[(r, f, "PRIOR")] if q[(r, f, "PRIOR")] else 0.0
            for a in st.MAACT:
                fd[(r, a, "T", f, "Mean")] = fd.get((r, a, "T", f, "PRIOR"), 0.0) * q[(r, f, "SCALE")]


def p_feedInpCoeff_Mean_STDE(st) -> None:
    r"""The prior means in fresh matter (the member state's dry matter content), their standard errors 5% of them.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 238-242):

        p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean") $ sum(MAP_RR(MS,RallInMS), DATA(MS,"DRMA",FEED,"Y"))
         = p_feedInpCoeffDRMA(RallInMS,maact,"T",Feed,"Mean") / sum(MAP_RR(MS,RallInMS), DATA(MS,"DRMA",FEED,"Y")) ;

        * set standard deviation (value = x * mean found by try and error)
        p_feedInpCoeff(RallInMS,maact,"T",Feed,"STDE")  = p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean") * 0.05 ;

    Departures from CAPRI: none."""
    pc = st.p_feedInpCoeff
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for f in st.FEED:
                dm = st.DATA.get((st.MS, "DRMA", f), 0.0)
                if dm:
                    pc[(r, a, "T", f, "Mean")] = st.p_feedInpCoeffDRMA.get((r, a, "T", f, "Mean"), 0.0) / dm
                pc[(r, a, "T", f, "STDE")] = pc.get((r, a, "T", f, "Mean"), 0.0) * 0.05


def p_feedInpCoeff_Mean_national(st) -> None:
    r"""A unit without a prior mean takes the member state's.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 245-247):

        p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean")
          $ ((not p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean")) and sum(MAP_RR(MS,RallInMS), DATA(MS,"DRMA",FEED,"Y")))
          = SUM(MAP_RR(MS,RallInMS), p_feedInpCoeffDRMA(MS,maact,"T",Feed,"Mean") / DATA(MS,"DRMA",FEED,"Y") );

    Departures from CAPRI: none."""
    pc, fd, ms = st.p_feedInpCoeff, st.p_feedInpCoeffDRMA, st.MS
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for f in st.FEED:
                dm = st.DATA.get((ms, "DRMA", f), 0.0)
                if dm and not pc.get((r, a, "T", f, "Mean"), 0.0):
                    pc[(r, a, "T", f, "Mean")] = fd.get((ms, a, "T", f, "Mean"), 0.0) / dm


def p_maxFeedShare_prior_not_positive(st) -> None:
    r"""No feed share where the prior mean is not positive.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 252):

        p_maxFeedShare(RallInMS,MAACT,"T",FEED) $ (p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean") le 0) = 0;

    Departures from CAPRI: none."""
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for f in st.FEED:
                if st.p_feedInpCoeff.get((r, a, "T", f, "Mean"), 0.0) <= 0:
                    st.p_maxFeedShare.pop((r, a, "T", f), None)


def p_feedInpCoeff_STDE_rest(st) -> None:
    r"""The standard errors of the means taken from the member state 15% of them; those of milk, straw, energy-rich
    feed and root crops 2%.

    CAPRI's GAMS (feed/fedtrm_prior_pw.gms l. 256-265):

        p_feedInpCoeff(RallInMS,maact,"T",Feed,"STDE") $ (not p_feedInpCoeff(RallInMS,maact,"T",Feed,"STDE"))
          = p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean") * 0.15;
        *  = p_feedInpCoeff(RallInMS,maact,"T",Feed,"Mean") * (0.15 $ MRUMI(MAACT) + .05 $ (not MRUMI(MAACT))) ;

        *  special for FMIL, FSTR, FROO, FENE: low value to stabilise these minor items that otherwise are often shaky:
        *  (specific numbers found by trial and error)
        p_feedInpCoeff(RallInMS,maact,"T","FMIL","STDE") = p_feedInpCoeff(RallInMS,maact,"T","FMIL","Mean") * 0.02;
        p_feedInpCoeff(RallInMS,maact,"T","FSTR","STDE") = p_feedInpCoeff(RallInMS,maact,"T","FSTR","Mean") * 0.02;
        p_feedInpCoeff(RallInMS,maact,"T","FENE","STDE") = p_feedInpCoeff(RallInMS,maact,"T","FENE","Mean") * 0.02;
        p_feedInpCoeff(RallInMS,maact,"T","FROO","STDE") = p_feedInpCoeff(RallInMS,maact,"T","FROO","Mean") * 0.02;

    Departures from CAPRI: none."""
    pc = st.p_feedInpCoeff
    for r in st.rall_in_ms():
        for a in st.MAACT:
            for f in st.FEED:
                if not pc.get((r, a, "T", f, "STDE"), 0.0):
                    pc[(r, a, "T", f, "STDE")] = pc.get((r, a, "T", f, "Mean"), 0.0) * 0.15
            for f in ("FMIL", "FSTR", "FENE", "FROO"):
                pc[(r, a, "T", f, "STDE")] = pc.get((r, a, "T", f, "Mean"), 0.0) * 0.02


#: CAPRI's statements of feed/fedtrm_prior_pw.gms, in their order
BLOCKS = (p_FeedAggrPrior_rough_total, p_feedBalance_AnimReq, p_feedBalance_allAni_AnimReq, p_feedBalance_FedmSup,
          p_feedBalance_FedmSupOri, p_feedBalance_FedmSup_reaggregated, p_feedBalance_FSTR,
          p_feedBalance_FedmSup_contents, p_feedBalance_rounds, p_feedInpCoeffDRMA_adjusted, p_feedQuantDRMA_FEDM,
          p_FeedShareInAggr_RegMean, p_feedInpCoeffDRMA_PRIOR, p_feedInpCoeffDRMA_Mean, p_feedInpCoeff_Mean_STDE,
          p_feedInpCoeff_Mean_national, p_maxFeedShare_prior_not_positive, p_feedInpCoeff_STDE_rest)


def fedtrm_prior_pw(st):
    r"""feed/fedtrm_prior_pw.gms: BLOCKS in order."""
    if not st.p_FeedAggrPrior:
        st.p_FeedAggrPrior = load_p_FeedAggrPrior()
    for block in BLOCKS:
        block(st)
    return st

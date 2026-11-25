r"""CAPRI's stop rule for the supply-market iterations (capmod/price_forecast.gms, star 3.0): the aggregates' prices,
the relative change of each item against the step before above its threshold, Norway's and Turkey's exclusion from
the 15th step, the rows' and the step's largest change and the decision to go on.

capri_mod/utils/capri_stop.py (CapriStopRule.record) loops over the steps, regions and rows and calls these.
"""
from __future__ import annotations


def p_iterChg(x1, x0):
    r"""p_iterChg(R, row, STEP): an item's relative change against the step before, % (0 where both are 0).

    CAPRI's GAMS (capmod/price_forecast.gms l. 103-123):

            p_iterChg(REGAGG,IOE,STEP) $ (
                                            p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                                          $ (   p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                                              + p_itemsInIters(REGAGG,"UVAG",IOE,"TRD")  $ (step.pos EQ 1))
        *                                          changes are only taken into account if the total quantities
        *                                          are 10 times above the change threshold:
                                          $  (    (p_itemsInIters(REGAGG,"grof",IOE,STEP) GT p_minAbsProdIterChg*10)
                                               or (p_itemsInIters(REGAGG,"Prod",IOE,STEP) gt p_minAbsFeedIterChg*10)
                                             )
                                          $  ( ABS(   p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                                                    - p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                                                    - p_itemsInIters(REGAGG,"UVAG",IOE,"TRD")  $ (step.pos EQ 1)
                                                    ) GT p_minAbsPriceIterChg)
                                          )

               = 2*(ABS(  p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                        - p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                        - p_itemsInIters(REGAGG,"UVAG",IOE,"TRD") $ (step.pos EQ 1))
                   /ABS(  p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                        + p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                        + p_itemsInIters(REGAGG,"UVAG",IOE,"TRD") $ (step.pos EQ 1))) * 100.;

    In this project's notation: c = 200 |x1 - x0| / |x1 + x0|. Departures from CAPRI: 200 x a / b (CAPRI's 2 (a / b)
    x 100: the same value up to rounding); the absolute value of the sum also for production and feed (CAPRI's
    without it, l. 139, 159: their quantities are positive)."""
    s = abs(x1 + x0)
    return 200.0 * abs(x1 - x0) / s if s > 0 else 0.0


def p_itemsInIters_UVAG(grof, grof_S1, UVAG, min_abs_prod):
    r"""p_itemsInIters(REGAGGU, "UVAG", IOE, STEP): an aggregate's price, its members' prices weighted by their first
    step's production, over the members producing now and more than 10 x p_minAbsProdIterChg in the first step
    (sequences over the members in the same order; UVAG None where a member has no price); None without weight.

    CAPRI's GAMS (capmod/price_forecast.gms l. 81-91):

            p_itemsInIters(REGAGGU,"uvag",IOE,STEP)
              = SUM(MAP_RR(REGAGGU,MS) $ (     p_itemsInIters(MS,"grof",IOE,STEP)
                                            $ (p_itemsInIters(MS,"grof",IOE,"S1") gt p_minAbsProdIterChg * 10 )),
                        p_itemsInIters(MS,"grof",IOE,"S1"));
        *
        *   --- Second step: value divivded by aggregated selling/budying quantities
        *
            p_itemsInIters(REGAGGU,"UVAG",IOE,STEP) $ p_itemsInIters(REGAGGU,"UVAG",IOE,STEP)
              = SUM(MAP_RR(REGAGGU,MS) $ (     p_itemsInIters(MS,"UVAG",IOE,STEP)
                                            $ (p_itemsInIters(MS,"grof",IOE,"S1") gt p_minAbsProdIterChg * 10)),
                  p_itemsInIters(MS,"grof",IOE,"S1")*p_itemsInIters(MS,"UVAG",IOE,STEP))/p_itemsInIters(REGAGGU,"UVAG",IOE,STEP);

    In this project's notation: P_A = sum_m q1_m P_m / sum_m q1_m. Departures from CAPRI: the members with a price
    and production now in both sums (CAPRI's weight sum asks for production, the value sum for a price; the members
    with production have a price in the model)."""
    w = [(float(q1), float(p)) for q, q1, p in zip(grof, grof_S1, UVAG)
         if float(q) and float(q1) > 10 * min_abs_prod and p is not None]
    sw = sum(x for x, _ in w)
    return sum(x * p for x, p in w) / sw if sw > 0 else None


def p_iterChg_UVAG(UVAG, UVAG_before, grof, min_abs_prod, min_abs_price):
    r"""p_iterChg(REGAGG, IOE, STEP) of an aggregate's price: the change where both prices are set, the aggregate
    produces more than 10 x p_minAbsProdIterChg (grof, the sum of its members', l. 93) and the price moved by more
    than p_minAbsPriceIterChg; None otherwise.

    CAPRI's GAMS (capmod/price_forecast.gms l. 103-116):

            p_iterChg(REGAGG,IOE,STEP) $ (
                                            p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                                          $ (   p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                                              + p_itemsInIters(REGAGG,"UVAG",IOE,"TRD")  $ (step.pos EQ 1))
        *                                          changes are only taken into account if the total quantities
        *                                          are 10 times above the change threshold:
                                          $  (    (p_itemsInIters(REGAGG,"grof",IOE,STEP) GT p_minAbsProdIterChg*10)
                                               or (p_itemsInIters(REGAGG,"Prod",IOE,STEP) gt p_minAbsFeedIterChg*10)
                                             )
                                          $  ( ABS(   p_itemsInIters(REGAGG,"UVAG",IOE,STEP)
                                                    - p_itemsInIters(REGAGG,"UVAG",IOE,STEP-1) $ (step.pos GT 1)
                                                    - p_itemsInIters(REGAGG,"UVAG",IOE,"TRD")  $ (step.pos EQ 1)
                                                    ) GT p_minAbsPriceIterChg)
                                          )

    (the value: p_iterChg). Departures from CAPRI: the first step not compared with TRD (the first step has no change,
    the caller's); the condition on "Prod" above 10 x p_minAbsFeedIterChg (a feed's own production) left out."""
    if UVAG and UVAG_before and grof > 10 * min_abs_prod and abs(UVAG - UVAG_before) > min_abs_price:
        return p_iterChg(UVAG, UVAG_before)
    return None


def p_iterChg_quantity(x, x_before, iterChg, min_abs):
    r"""p_iterChg(MS, row, STEP) of a member state's production (OM_OUTPUT) or feed use (FEED, without straw; fodder
    set to 0, l. 145, by the caller's items): the larger of the row's change so far and this one, where both
    quantities are set and they moved by more than the threshold (p_minAbsProdIterChg, p_minAbsFeedIterChg); None
    otherwise.

    CAPRI's GAMS (capmod/price_forecast.gms l. 127-141):

            p_iterChg(MS,OM_OUTPUT,STEP) $ (
                                             p_itemsInIters(MS,"grof",OM_OUTPUT,STEP)
                                             $ (  p_itemsInIters(MS,"grof",OM_OUTPUT,STEP-1)  $ (step.pos GT 1)
                                                + p_itemsInIters(MS,"grof",OM_OUTPUT,"TRD")   $ (step.pos EQ 1))
                                             $ (abs(   p_itemsInIters(MS,"grof",OM_OUTPUT,STEP)
                                                     - p_itemsInIters(MS,"grof",OM_OUTPUT,STEP-1) $ (step.pos GT 1)
                                                     - p_itemsInIters(MS,"grof",OM_OUTPUT,"TRD")  $ (step.pos EQ 1)
                                                     ) GT p_minAbsProdIterChg) )
               = MAX(p_iterChg(MS,OM_OUTPUT,STEP),
                    2*ABS(p_itemsInIters(MS,"grof",OM_OUTPUT,STEP)
                           - p_itemsInIters(MS,"grof",OM_OUTPUT,STEP-1) $ (step.pos GT 1)
                           - p_itemsInIters(MS,"grof",OM_OUTPUT,"TRD") $ (step.pos EQ 1))
                        /(   p_itemsInIters(MS,"grof",OM_OUTPUT,STEP)
                           + p_itemsInIters(MS,"grof",OM_OUTPUT,STEP-1) $ (step.pos GT 1)
                           + p_itemsInIters(MS,"grof",OM_OUTPUT,"TRD") $ (step.pos EQ 1)) * 100.);

    and feed at l. 147-160. Departures from CAPRI: the first step not compared with TRD (the caller's); the feeds are
    the traded bulks (FEED_TRD, the model's items: fodder and straw out)."""
    if x and x_before and abs(x - x_before) > min_abs:
        return max(iterChg, p_iterChg(x, x_before))
    return None


def p_iterChg_NO000000(step, from_step):
    r"""p_iterChg("NO000000", ROWS, STEP) = 0 from the 15th step (Turkey's the same): whether the member state's changes
    are dropped at the step.

    CAPRI's GAMS (capmod/price_forecast.gms l. 317-318):

            p_iterChg("NO000000",ROWS,STEP) $ (ORD(step) ge 15) = 0;
            p_iterChg("TUR",ROWS,STEP)      $ (ORD(step) ge 15) = 0;

    Departures from CAPRI: none (the step from which, 15, the caller's setting)."""
    return step >= from_step


def p_iterChg_TOT(iterChg):
    r"""p_iterChg("TOT", ROWS, STEP): a row's largest change over the member states and aggregates (the aggregates'
    own and their members', l. 321), 0 where none has one.

    CAPRI's GAMS (capmod/price_forecast.gms l. 354-355):

            p_iterChg("TOT",ROWS,STEP)  $ (NOT CARD(REGAGG))   = SMAX(MS,    p_iterChg(MS,    ROWS,STEP));
            p_iterChg("TOT",ROWS,STEP)  $ (CARD(REGAGG))       = SMAX(REGAGG,p_iterChg(REGAGG,ROWS,STEP));

    Departures from CAPRI: the largest over all regions at once (CAPRI's over the aggregates, each the larger of its
    own and its members' l. 321: the same largest)."""
    m = 0.0
    for v in iterChg:
        m = max(m, v)
    return m


def p_iterChg_TOT_MAX(iterChg, step):
    r"""p_iterChg("TOT", "MAX", STEP): the step's largest change over the rows without the young animals (and without
    manure, which the model's rows do not have), at least 1 at the first step.

    CAPRI's GAMS (capmod/price_forecast.gms l. 345-346):

            p_iterChg("TOT","MAX",STEP) $ (NOT CARD(REGAGG))   = SMAX(MS,p_iterChg(MS,"MAX",STEP));
            p_iterChg("TOT","MAX",STEP) $ CARD(REGAGG)         = SMAX(REGAGG,p_iterChg(REGAGG,"MAX",STEP));

    with p_iterChg(R, "MAX", STEP) the regions' largest over the rows without OIYANI (l. 328-335) and

            p_iterChg("TOT","MAX",STEP)  $ (step.pos eq 1) = MAX(1,p_iterChg("TOT","MAX",STEP));

    (l. 363). Departures from CAPRI: the largest over the rows' largest (p_iterChg_TOT; the same value)."""
    mx = max(iterChg, default=0.0)
    if step == 1:
        mx = max(1.0, mx)
    return mx


def p_iterChg_TOT_MAX_CUR(iterChg_TOT_MAX, iterChg_TOT, min_iter_chg, step):
    r"""p_iterChg("TOT", "MAX", "CUR"): the step's largest change where more than two rows changed by more than
    p_minIterChg, else 0 (the loop goes on while it exceeds p_minIterChg, capmod.gms l. 1369); the first step always
    goes on.

    CAPRI's GAMS (capmod/price_forecast.gms l. 370-371):

            p_iterChg("TOT","MAX","CUR") $ (step.pos GT 1)
                = p_iterChg("TOT","MAX",STEP) $ (SUM(ROWS $ (p_iterChg("TOT",ROWS,STEP) gt p_minIterChg),1) GT 2);

    Departures from CAPRI: the first step's value its maximum (CAPRI leaves CUR as it was, the loop's start: it goes
    on)."""
    count = sum(1 for v in iterChg_TOT if v > min_iter_chg)
    return (iterChg_TOT_MAX if (step == 1 or count > 2) else 0.0), count


def DATA_UVAG_forecast(weights, values):
    r"""DATA(RMSSUP, "UVAG", XX, "Y") of CAPRI's price forecast: the weighted average of the market's prices of the last
    steps (values, the latest first; floats or pandas Series), the weights 0.55 / 0.30 / 0.15, from the 20th step 0.4 /
    0.3 / 0.2 / 0.1 (define_stepWeights.gms, the latest first), normalised over the steps available.

    CAPRI's GAMS (capmod/price_forecast.gms l. 376-383):

            if( card(stepsWithWeights) and p_iterChg("TOT","MAX","CUR"),
        *
        *    --- the price for the next iteration is a weigthed average of the prices simulated for the
        *        same year in previous iterations
        *
              DATA(MS,"UVAG",UVAN_P,"Y") $ (DATA(MS,"UVAG",UVAN_P,"Y") or p_itemsInIters(MS,"UVAG",uvan_p,"TRD"))
                     = SUM(stepsWithWeights,
                                    p_itemsInIters(MS,"UVAG",UVAN_P,stepsWithWeights) * p_stepWeights(stepsWithWeights));

    (the problem products' slower smoothing, l. 386-388, define_stepweights.py p_stepWgtSpecial).

    Departures from CAPRI: the weighted sum divided by the weights available (CAPRI's weights normalised first,
    define_stepWeights.gms l. 40-41: the same value up to rounding)."""
    use = list(values)[:len(weights)]
    tot = sum(weights[:len(use)])
    out = None
    for w_, v_ in zip(weights, use):
        out = w_ * v_ if out is None else out + w_ * v_
    return out / tot

r"""CAPRI's extension of the rural development budgets (policy/extend_rd_baseline.gms, star 3.0): the plan carried
forward, the sums and counts per programme, the NUTS 2 regions' weights in their member state's money (rules 1, 3, 4
and their rescaling), the money not spent in 2007-2013 spread to the years without spend (from a NUTS 2 region's own
rest, then its NUTS 1 region's and its member state's) and the average spend after 2013.

The total public money only (rdSpendPublic: CAPRI's ceilings use it alone). capri_mod/policy/rd.py (extend_budget)
loops over the regions, programmes, measures and years and calls these; GAMS's EPS arithmetic of the RD data is in
the helpers below (rd.py imports them). Rule 2 (l. 93-106) is inside $ontext in CAPRI; not ported either.
"""
from __future__ import annotations

from capri_mod.policy.equations._gams import EPS


def _num(x) -> float:
    """A value in GAMS's arithmetic and comparisons: EPS is zero."""
    return 0.0 if x == EPS or x is None else x


def _nz(x) -> bool:
    return x == EPS or bool(x)


def _div(a, b):
    """GAMS's a / b with EPS (EPS / b stays EPS)."""
    if a == EPS:
        return EPS
    return a / b if a else None


def _gsum(values):
    """GAMS's sum with EPS terms: the sum of the numbers, EPS where only EPS and zeros, None for nothing."""
    tot, eps = 0.0, False
    for v in values:
        if v == EPS:
            eps = True
        elif v:
            tot += v
    return tot if tot else (EPS if eps else None)


def p_rdBudget_plan(plan, plan_year_before):
    r"""p_rdBudget(runr, SIMYY, rdMeasure, rdSpender, "plan") of a year after 2005 up to the year after the target year
    without a plan: the year before's; None where it has one or the year before has none.

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 61-65):

        LOOP(SIMYY $ [(calyea(SIMYY) GT 2005) AND (calyea(SIMYY) LE (%targetYear% + 1))],
            p_rdBudget(runr,SIMYY,rdMeasure,rdSpender,"plan")
            $ (NOT p_rdBudget(runr,SIMYY,rdMeasure,rdSpender,"plan"))
            = p_rdBudget(runr,SIMYY-1,rdMeasure,rdSpender,"plan");
        );

    Departures from CAPRI: from the data's second year if it starts after 2005 (the caller's range)."""
    if _nz(plan) or not _nz(plan_year_before):
        return None
    return plan_year_before


def p_rdSpendingPeriod_abs(values):
    r"""p_rdSpendingPeriod(r, rdp, rdMeasure, rdSpender, rdPlanSpend, "abs"): the sum of a programme's planned or spent
    money over its years (GAMS's sum with EPS terms; None for no record); the member states' spend the sum of their
    NUTS 2 regions' (l. 84-85), and a NUTS 1 region's or member state's without its own the same (l. 179-181, 229-231).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 68-70):

        p_rdSpendingPeriod(runr,rdp,rdMeasure,rdSpender,rdPlanSpend,"abs")
            = SUM(rdp_simyy(rdp,simyy) $ [p_rdBudget(runr,SIMYY,rdMeasure,rdSpender,rdPlanSpend) NE NA],
                p_rdBudget(runr,simyy,rdMeasure,rdSpender,rdPlanSpend));

    Departures from CAPRI: none (no NA in the data)."""
    return _gsum(values)


def p_rdSpendingPeriod_nobs(spend):
    r"""p_rdSpendingPeriod(runr, rdp, rdMeasure, rdSpender, "spend", "nobs"): the number of the programme's years with a
    spend above 0.

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 73-74):

        p_rdSpendingPeriod(runr,rdp,rdMeasure,rdSpender,"spend","nobs")
            = SUM(rdp_simyy(rdp,simyy) $ [p_rdBudget(runr,SIMYY,rdMeasure,rdSpender,"spend") GT 0], 1);

    Departures from CAPRI: none."""
    return sum(1 for v in spend if _num(v) > 0)


def p_rdSpendingPeriod_weight(spend, spend_MS):
    r"""p_rdSpendingPeriod(srnuts2_ext, "RDP 2007-2013", rdMeasure, "rdSpendPublic", "spend", "weight") by rule 1: the
    NUTS 2 region's share of its member state's spend (the caller keeps a member state's spend above 0); None where the
    region has no spend.

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 87-90):

        p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
            $ [SUM(nuts0 $ map_rr(nuts0,srnuts2_ext), p_rdSpendingPeriod(nuts0,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","abs")) gt 0]
            = p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","abs")
            / SUM(nuts0 $ map_rr(nuts0,srnuts2_ext), p_rdSpendingPeriod(nuts0,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","abs"));

    Departures from CAPRI: none."""
    return _div(spend, spend_MS) if _nz(spend) else None


def p_rdSpendingPeriod_weight_shock(spend_old, spend_old_MS, key, where=""):
    r"""p_rdSpendingPeriod(srnuts2_ext, "RDP 2007-2013", rdMeasure, "rdSpendPublic", "spend", "weight") of a region
    without one, by rule 3 (the region's share of its member state's 2000-2006 spend on the measure's policy shock,
    spend_old and spend_old_MS GAMS's sums over the shock's old measures) where the member state has such spend, else
    by rule 4 (CAPRI's key for new measures, p_rdNewMeasuresRegDist); None where neither gives one.

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 112-131):

        LOOP((nuts0,rdShocks),

        *   3)  In proportion to observed spending on the rdShock to which the measure belongs, in old RDP
            p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
            $ [(NOT p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight"))
                AND SUM(rdShocks_RDP_rdMeasure(rdShocks,"RDP 2000-2006",rdMeasure1), p_rdSpendingPeriod(nuts0,"RDP 2000-2006",rdMeasure1,"rdSpendPublic","spend","abs"))
                AND map_rr(nuts0,srnuts2_ext)
                AND rdShocks_RDP_rdMeasure(rdShocks,"RDP 2000-2006",rdMeasure)]
            = SUM(rdShocks_RDP_rdMeasure(rdShocks,"RDP 2000-2006",rdMeasure1), p_rdSpendingPeriod(srnuts2_ext,"RDP 2000-2006",rdMeasure1,"rdSpendPublic","spend","abs"))
            / SUM(rdShocks_RDP_rdMeasure(rdShocks,"RDP 2000-2006",rdMeasure1), p_rdSpendingPeriod(nuts0,"RDP 2000-2006",rdMeasure1,"rdSpendPublic","spend","abs"));


        *   4)  In proportion to the relative size of the key receipient industry in the SAM baseline.
        *       That info is stored in GDX, but there should be a better way to get it from the SAM.
            p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
            $ [(NOT p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight"))
                AND map_rr(nuts0,srnuts2_ext)
                AND rdShocks_RDP_rdMeasure(rdShocks,"RDP 2000-2006",rdMeasure)]
            = p_rdNewMeasuresRegDist(srnuts2_ext,rdShocks);
        );

    Departures from CAPRI: a member state's 2000-2006 spend written EPS with a region's above it stops (CAPRI's
    EPS / EPS; not in the data). The caller skips the regions with a weight (EPS is one)."""
    if _nz(spend_old_MS):
        if spend_old_MS == EPS:
            if spend_old not in (None, EPS):
                raise ValueError(f"extend_rd_baseline rule 3: {where} a share over EPS")
            v = EPS if spend_old == EPS else None
        else:
            v = _div(spend_old, spend_old_MS) if spend_old is not None else None
        if v is not None:
            return v
    return key if key else None


def p_rdSpendingPeriod_weight_sum(weights):
    r"""p_rdSpendingPeriod(r, "RDP 2007-2013", rdMeasure, "rdSpendPublic", "spend", "weight") of a member state (or a
    NUTS 1 region without its own, l. 189-191 and 237-239): the sum of its NUTS 2 regions' weights (GAMS's sum with
    EPS terms; None for no record).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 134-136):

        LOOP(nuts0,
            p_rdSpendingPeriod(nuts0,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
                = SUM(srnuts2_ext $ map_rr(nuts0,srnuts2_ext), p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight"));

    Departures from CAPRI: none."""
    return _gsum(weights)


def p_rdSpendingPeriod_weight_scaled(weight, weight_MS):
    r"""p_rdSpendingPeriod(srnuts2_ext, "RDP 2007-2013", rdMeasure, "rdSpendPublic", "spend", "weight") rescaled by its
    member state's sum to sum to one (the caller skips a sum written EPS).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 138-142):

            p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
                $ [map_rr(nuts0,srnuts2_ext)
                   AND p_rdSpendingPeriod(nuts0,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")]
                =  p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
                /  p_rdSpendingPeriod(nuts0,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight");

    Departures from CAPRI: none."""
    return _div(weight, weight_MS)


def p_rdSpendingPeriod_rest(plan, spend):
    r"""p_rdSpendingPeriod(r, "RDP 2007-2013", rdMeasure, rdSpender, "spend", "rest"): the planned money not spent in
    2007-2013 (at least 0), of a NUTS 2 region, a NUTS 1 region (l. 184-186) or a member state (l. 233-235).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 155-157):

        p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,rdSpender,"spend","rest")
            = MAX[0, p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,rdSpender,"plan","abs")
                    -p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,rdSpender,"spend","abs")];

    Departures from CAPRI: none."""
    return max(0.0, _num(plan) - _num(spend))


def p_rdBudget_spend(rest, nobs, n_years):
    r"""p_rdBudget(srnuts2_ext, SIMYYY, rdMeasure, rdSpender, "spend") of a 2007-2013 year without spend in a NUTS 2
    region with a weight, a rest and fewer years with spend than the programme's: its rest over its years without
    spend (the caller's conditions; n_years the programme's, CAPRI's 7).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 162-169):

        p_rdBudget(srnuts2_ext,SIMYYY,rdMeasure,rdSpender,"spend")
            $ [     (p_rdBudget(srnuts2_ext,SIMYYY,rdMeasure,rdSpender,"spend") EQ 0)
                AND (p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight"))
                AND (p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,rdSpender,"spend","rest"))
                AND (p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","nobs") LT 7)]

            = p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,rdSpender,"spend","rest")
            / (7-p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","nobs"));

    Departures from CAPRI: none (the programme's number of years from the data, 7)."""
    return rest / (n_years - nobs)


def p_rdBudget_spend_from_above(rest, weight, weight_above, nobs, n_years):
    r"""p_rdBudget(srnuts2_ext, SIMYYY, rdMeasure, rdSpender, "spend") of a 2007-2013 year without spend, from its NUTS
    1 region's rest (or its member state's, l. 247-257): the rest x the region's weight / the weight above / its years
    without spend (the caller's conditions: the region's weight above EPS, a rest, the region's, or for a member state
    the member state's, years with spend fewer than the programme's).

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 199-214):

            p_rdBudget(srnuts2_ext,SIMYYY,rdMeasure,rdSpender,"spend")
                $ [(p_rdBudget(srnuts2_ext,SIMYYY,rdMeasure,rdSpender,"spend") EQ 0)
                    AND map_rr(runr,srnuts2_ext)
                    AND (p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight") gt eps)
                    AND  p_rdSpendingPeriod(runr,"RDP 2007-2013",rdMeasure,rdSpender,"spend","rest")
                    AND (7 GT p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","nobs"))]
                =
        *         ... budget left to spend
                  p_rdSpendingPeriod(runr,"RDP 2007-2013",rdMeasure,rdSpender,"spend","rest")

        *         ... times region's share in current nuts 1
                * p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")
                / p_rdSpendingPeriod(runr,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","weight")

        *         ... divided by number of years without spend in region in period
                / (7-p_rdSpendingPeriod(srnuts2_ext,"RDP 2007-2013",rdMeasure,"rdSpendPublic","spend","nobs"));

    In this project's notation: S = R w / W / (7 - n). Departures from CAPRI: the member state's form (l. 254-257, R /
    (7 - n) x w / W) computed in the NUTS 1 order (the same value up to rounding)."""
    return rest * weight / weight_above / (n_years - nobs)


def p_rdSpendingPeriod_ave(spend_total, n_years):
    r"""p_rdSpendingPeriod(runr, rdp, rdMeasure, rdSpender, "spend", "ave"): a NUTS 2 region's average spend of
    2007-2013 (spend_total GAMS's sum of its years' spend), which every year after 2013 up to the year after the target
    year takes (l. 281-282); EPS where the sum is EPS, None where there is none.

    CAPRI's GAMS (policy/extend_rd_baseline.gms l. 275-282):

        p_rdSpendingPeriod(runr,rdp,rdMeasure,rdSpender,"spend","ave")
            = SUM(simyy $ rdp_simyy(rdp,simyy), p_rdBudget(runr,simyy,rdMeasure,rdSpender,"spend"))
            / SUM(simyy $ rdp_simyy(rdp,simyy), 1);


        *   KEY STATEMENT! Assume average spending in 2007-2013 period applies in next period as well.
        simyyy(simyy) = YES $ [(calyea(simyy) GT 2013) AND (calyea(simyy) LE (%targetYear%+1))];
        p_rdBudget(runr,simyyy,rdMeasure,rdSpender,"spend") = p_rdSpendingPeriod(runr,"RDP 2007-2013",rdMeasure,rdSpender,"spend","ave");

    Departures from CAPRI: none (2007-2013's average only, the one the step uses)."""
    return EPS if spend_total == EPS else (spend_total / n_years if spend_total else None)

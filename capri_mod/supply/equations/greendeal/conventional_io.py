r"""CAPRI's pesticide target (pol_input/greendeal/conventional_io.gms, star 3.0): the regional percentage changes of
plant protection and other inputs, and the yield loss on the conventional area.

capri_mod/supply/policy.py (PolicyBlock._apply_greendeal_input_changes, apply_pesticide_reduction) calls these.
"""
from __future__ import annotations

from capri_mod.supply.equations.greendeal.organic_io import DATA_GROF_PLAP_percentageChange as _organic_plap


def DATA_GROF_percentageChange(plapReduction, p_organicAreaTarget):
    r"""(DATA(RU, "GROF", "PLAP", "percentageChange"), DATA(RU, "GROF", "INPO", "percentageChange")): the regional
    changes of plant protection and other inputs under the pesticide target r (a share) and the organic target o_R:
    plant protection -o_R from the organic target (organic_io.gms l. 74), -r overall where o_R < r (the remaining
    target on the conventional area plus the organic part), other inputs + (r - o_R) there (otherCostChange = r).

    CAPRI's GAMS (pol_input/greendeal/conventional_io.gms l. 118-126):

             DATA(RU,"GROF","PLAP","percentageChange") $ region_plap(ru)
               =
        *    scale back pesticide reduction target with what is already achieved by organic shift
        *    because this new part only applies to the remaining (conventional) agricultural area
                (-%plapReduction% * (1 - p_organicAreaTarget(ru))
                * p_already_adjusted(ru, "pesticide", "remainingTarget") / %plapReduction%)

        *    pesticide reduction on organic area, as additional to the previous term
                 + (DATA(RU,"GROF","PLAP","percentageChange") $ p_already_adjusted(ru, "pesticide", "fromOrganic"));

    with p_already_adjusted's fromOrganic and remainingTarget (l. 104-116), and other inputs at l. 182-192:

             DATA(RU,"GROF","INPO","percentageChange")  $ (region_plap(ru)
                                                        $ (abs(p_already_adjusted(ru, "pesticide", "fromOrganic")) lt abs(%plapReduction%)))

              =
        *    cost increase from pesticide use restrictions (scaled with remaining PLAP target)
                (%otherCostChange% * (1 - p_organicAreaTarget(ru))
                * p_already_adjusted(ru, "pesticide", "remainingTarget") / %plapReduction%)

        *    plus any cost change already assumed in hte scenario
        *    Note that the organic scenario assumes a top-up for INPO.BAS (see below) => GROF.INPO.PercentageChange is still zero
                 + (DATA(RU,"GROF","INPO","percentageChange") $ p_already_adjusted(ru,"othercost","boolean"));

    (the branch without organic targets, l. 302-309, the same with o_R = 0). In this project's notation: remaining =
    (r - o_R) / (1 - o_R), PLAP = -r (1 - o_R) remaining / r - o_R = -r, INPO = r (1 - o_R) remaining / r = r - o_R.
    Departures from CAPRI: the closed forms (the same values), as shares."""
    r = max(0.0, float(plapReduction or 0.0))
    o_R = p_organicAreaTarget
    pc_plap = _organic_plap(o_R)
    pc_inpo = 0.0
    if r > 0 and o_R < r:
        pc_plap = -r
        pc_inpo = r - o_R
    return pc_plap, pc_inpo


def p_yildReduction(yildReduction_at_50, plapReduction):
    r"""%yildReduction% of the pesticide target r: the loss at CAPRI's 50% reference scaled linearly (the jrc121368
    rule: 10% at a 50% cut).

    CAPRI's GAMS (pol_input/greendeal/conventional_io.gms l. 146-159):

             DATA(RU,pesticideCrops,"Yild","percentageChange") $ ( region_plap(ru)

        *    check if the PLAP reduction target is already achieved with the organic yield redcution (yield gap)
        *    if already achieved then the conventional agriculture does not need to contribute to achieve the target => no further yield reduction
             $ (abs(p_already_adjusted(ru, "pesticide", "fromOrganic")) lt abs(%plapReduction%)) )

               =

        *    yield reduction on conventional area (scaled to regional average)
                (-%yildReduction% * (1 - p_organicAreaTargetCrops(ru,pesticideCrops))
                * p_already_adjusted(ru, "pesticide", "remainingTarget") / %plapReduction%)

        *    yield reduction on organic area (scaled to regional average)
                + (DATA(RU,pesticideCrops,"Yild","percentageChange") $ p_already_adjusted(ru, "yield", pesticideCrops));

    Departures from CAPRI: the loss scaled with the cut (CAPRI's %yildReduction% given, scaled by remainingTarget /
    %plapReduction%); star 3.0's Green Deal group runs with the yield shock off (the caller's yield_loss)."""
    return yildReduction_at_50 * (plapReduction / 0.50)


def DATA_Yild(Yild, yildReduction, conventional_share):
    r"""DATA(RU, pesticideCrops, "Yild") under the pesticide target: the yield less the loss on the crop's
    conventional share.

    CAPRI's GAMS (pol_input/greendeal/conventional_io.gms l. 155-156):

                (-%yildReduction% * (1 - p_organicAreaTargetCrops(ru,pesticideCrops))
                * p_already_adjusted(ru, "pesticide", "remainingTarget") / %plapReduction%)

    In this project's notation: Y' = Y (1 - loss (1 - o_a)). Departures from CAPRI: without the remainingTarget /
    %plapReduction% factor (the loss scaled with the cut instead, p_yildReduction)."""
    return Yild * (1.0 - yildReduction * conventional_share)


def pest_change_factor_greendeal(pc_plap, pc_organic):
    r"""The factor on every pesticide application of an EU region under the Green Deal's targets with the pesticide
    module (DATA(RU, mCact, pestoAgg, "Y") after define_inputs.gms), from the plant protection's regional change:
    conventional_io.gms sets the change factor from PLAP's total change (the organic target's and the remaining one),
    organic_io.gms sets the aggregates' percentage change to the organic target's, and define_inputs.gms applies both.

    CAPRI's GAMS (pol_input/greendeal/conventional_io.gms l. 128-134):

        $iftheni.pes46  %pest_disagg%==on
        *    Copied from pol_input\pesticides\pesti_regu50.gms:
             DATA(RU,mCact,pestoAgg,"ChangeFactor") $ region_plap(ru)= DATA(RU,"GROF","PLAP","percentageChange")/100+1;
             DATA(RU,mCact,pestoAgg,"AbsoluteChange") $ DATA(RU,mCact,pestoAgg,"ChangeFactor") =0;
        *    Not needed anymore to pass on the planned changes for all pesticides:
             DATA(RU,"GROF","PLAP","percentageChange")=0;
        $endif.pes46

    CAPRI's GAMS (pol_input/greendeal/organic_io.gms l. 74-76):

           DATA(RU,"GROF","PLAP","percentageChange") $ (region_plap(ru) $ p_organicAreaTarget(ru))
              =  -%plapReduction% * p_organicAreaTarget(ru);
        $ifi %pest_disagg%==on   DATA(RU,mCact,pestoAgg,"percentageChange") = DATA(RU,"GROF","PLAP","percentageChange") ;

    CAPRI's GAMS (capmod/define_inputs.gms l. 131-135):

                DATA(RU,mCact,pestoAgg,"Y")  $ DATA(RU,mCact,pestoAgg,"ChangeFactor")
                      = DATA(RU,mCact,pestoAgg,"Y") * DATA(RU,mCact,pestoAgg,"ChangeFactor");

                DATA(RU,mCact,pestoAgg,"Y")  $ DATA(RU,mCact,pestoAgg,"PercentageChange")
                  = DATA(RU,mCact,pestoAgg,"Y") * (1. + DATA(RU,mCact,pestoAgg,"PercentageChange")/100);

    In this project's notation, as shares: pc_plap = DATA(RU, "GROF", "PLAP", "percentageChange") / 100 after
    conventional_io.gms (DATA_GROF_percentageChange), pc_organic the organic target's (organic_io.gms l. 74; 0 without
    an organic target):

        factor = (1 + pc_plap) x (1 + pc_organic)

    Departures from CAPRI: none (as CAPRI's code runs: the organic target's cut enters twice, once in PLAP's total and
    once as the aggregates' percentage change, which looks unintended in CAPRI; the comment at organic_io.gms l. 67-71
    guards PLAP against that double count, not the aggregates)."""
    return (1.0 + float(pc_plap)) * (1.0 + float(pc_organic))

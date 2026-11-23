r"""CAPRI's mineral fertiliser reduction by crop group (pol_input/greendeal/minfert_redu_by_crop.gms, star 3.0): the
small groups exempt, the groups' mineral N caps and the residues' regulation (limCres).

capri_mod/fert/inner_fert_dist.py (InnerFertDist.mineral_caps, small_mine_groups, limcres_caps) calls these; the
listed regions' factors and the limCres relaxations are data read (mineral_redu_exemptions.csv,
mineral_redu_limcres.csv, tools/build/build_mineral_redu_rules.py).
"""
from __future__ import annotations


def p_checkSmallMine(p_minfertBaseline, listed, small_threshold):
    r"""p_checkSmallMine(ru, NGRP): whether a crop group is exempt from the reduction: its baseline mineral N per ha
    above 0 and below 30 kg (small_threshold), or the (region, group) listed for the simulation year (l. 100-232, the
    factors data read).

    CAPRI's GAMS (pol_input/greendeal/minfert_redu_by_crop.gms l. 97-98):

          p_checkSmallMine(ru,NGRP) $ (p_minfertBaseline(ru,NGRP,"MIN") lt 0.03)
            = p_minfertBaseline(ru,NGRP,"MIN");

    Departures from CAPRI: kg per ha (CAPRI's t: 0.03); the baseline the model's own calibration point's mineral N
    per ha by group (p_minfertBaseline, l. 83-85, the caller's base allocation)."""
    return p_minfertBaseline > 0 and (listed or p_minfertBaseline < small_threshold)


def p_nMaxPerHa_MIN(p_minfertBaseline, reductionTarget, small, factor=1.0):
    r"""p_nMaxPerHa(ru, NGRP, "MIN"): a group's mineral N cap per ha, factor x its baseline for the small groups (no
    backsliding; the listed regions' factor, 1 otherwise), the baseline x (1 - the reduction) for the others (the more
    stringent of that and a cap set before, l. 244-247, the caller's merge with the organic target's).

    CAPRI's GAMS (pol_input/greendeal/minfert_redu_by_crop.gms l. 237-250):

          p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ p_checkSmallMine(ru,NGRP))
            =   p_checkSmallMine(ru,NGRP);


        *   --- if p_nMaxPerHa is already set in a previous file (e.g. by organic farming target)
        *       then we take the more stringent reduction target (i.e. we use the min() function below)
        *
          p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ (not p_checkSmallMine(ru,NGRP)) $ (p_nMaxPerHa(ru,NGRP,"MIN") gt 0))
            =  min( (p_minfertBaseline(ru,NGRP,"MIN") * (1 - %reductionTarget%/100)),
                     p_nMaxPerHa(ru,NGRP,"MIN")
                            );

          p_nMaxPerHa(ru,NGRP,"MIN") $ (p_minfertBaseline(ru,NGRP,"MIN") $ (not p_checkSmallMine(ru,NGRP)) $ (not p_nMaxPerHa(ru,NGRP,"MIN")))
            =  p_minfertBaseline(ru,NGRP,"MIN") * (1 - %reductionTarget%/100);

    Departures from CAPRI: the reduction as a share; the EU-27 only (l. 258) the caller's."""
    return factor * p_minfertBaseline if small else p_minfertBaseline * (1.0 - reductionTarget)


def p_priFertDistRegu_limCres(postModePerHa, factor):
    r"""p_priFertDistRegu("limCres", RU, "priMaxPerHa", FNUT, NGRP, "y"): the residues' maximum per ha, the baseline's
    posterior mode per ha x (1.3 + the region's and group's relaxations: factor); the organic target's the same at 1.2
    (organic_minfert_redu.gms l. 115-116). The regulation's density: mode at the baseline (mode / max = 1 / factor),
    accuracy 10 (set_fert_priors.gms l. 310-323).

    CAPRI's GAMS (pol_input/greendeal/minfert_redu_by_crop.gms l. 277-282):

          p_priFertDistRegu("limCres",RU,"priMaxPerHa",FNUT,NGRP,"y")
            = p_priFertDist(ru,"postModePerHa","CRES",FNUT,NGRP,"%simy%") * (1.3
        *   Various additional relaxations to cope with infeasilities showing high marginals for the crop residue constraints:
        *   These problem cases became more frequent in the sims for results in 40_data_090724 compared to the earlier 39_data_220424
        $ife %simy%>2035                                                  +.5 $ (sameas(ru,"SE010000")   $  sameas(ngrp,"SUGB"))
        $ife %simy%>2025                                                  +.5 $ (sameas(ru,"PT200000")   $  sameas(ngrp,"SUGB"))

    Departures from CAPRI: the baseline the model's own calibration point's residues per ha (the caller's); the
    regulation on CRES for every nutrient (p_fertDistReguWgt, l. 358) the caller's."""
    return postModePerHa * factor

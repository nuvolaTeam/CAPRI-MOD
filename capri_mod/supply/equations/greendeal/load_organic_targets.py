r"""CAPRI's organic targets (pol_input/greendeal/load_organic_targets.gms, star 3.0): the member states' targets scaled
to the requested ambition.

capri_mod/supply/policy.py (PolicyBlock._organic_target_scale, _organic_region_target, _organic_crop_target) calls
these; the targets are data read (organic_targets_ms.csv).
"""
from __future__ import annotations


def p_organicTargetScale(orgTarg, outlook, reference):
    r"""The scaling of CAPRI's targets to the ambition, (orgTarg - 12) / (25 - 12) (orgTarg in %, here the share x 100;
    12 the 2021 DG AGRI outlook, 25 the reference target), at least 0.

    CAPRI's GAMS (pol_input/greendeal/load_organic_targets.gms l. 172-177):

          p_organicAreaTargetCrops(ms, ngrp)
        * scale down in case of a reduced target (for 2025-2030) in a transition phase
        * NOTE: 12% was the assummption in the 2021 DG agri outlook
                 = (%orgTarg%-12)/(25-12)
                 * sum((geo,EUROSTAT_crops) $ (crops_to_ngrp(EUROSTAT_crops,ngrp) $ geo_to_ms(geo, ms)),
                        p_organicTargetMS(geo,EUROSTAT_crops)) /100;

    Departures from CAPRI: at least 0 (CAPRI's negative below 12%)."""
    return max(0.0, (100.0 * float(orgTarg) - outlook) / (reference - outlook))


def p_organicAreaTarget(target_pp, scale):
    r"""p_organicAreaTarget(ms) and p_organicAreaTargetCrops(ms, ngrp): a target in percentage points scaled to the
    ambition, as a share within 0 and 1; a NUTS 2 region takes its member state's (l. 185, 188), VEGE and the organic
    crops not mapped to a group the UAA target (l. 187, 270-271), the others their group's (l. 266-267).

    CAPRI's GAMS (pol_input/greendeal/load_organic_targets.gms l. 183-185):

          p_organicAreaTarget(ms)      = (%orgTarg%-12)/(25-12)
                                       * sum( geo_to_ms(geo, ms), p_organicTargetUAA(geo)) /100;
          p_organicAreaTarget(srnuts2) = sum(ms $ map_rr(ms,srnuts2), p_organicAreaTarget(ms));

    Departures from CAPRI: held within 0 and 1; VEGE takes the UAA target even where its group has one (CAPRI's only
    where it has none, l. 187; organic_ngrp_class)."""
    return max(0.0, min(1.0, float(target_pp) / 100.0 * scale))

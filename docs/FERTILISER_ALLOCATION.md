# Fertiliser allocation: crop need, the inner fertiliser distribution model, mineral fertiliser caps

Status: revised 20 October 2026 against the code. In the default NLP form CAPRI's fertilisation block (NUTNED_ per
crop group and nutrient, the inner fertiliser distribution model) is part of every regional solve. The staged plan
by which the conic form was built (a linearised mineral-N substitution, a regional crop-need row, the allocation
checked after the solve) is summarised under "Conic form"; its run results (Sprint 9e) were removed.

## CAPRI's crop need (`supply/supply_model.gms`, NUTNED_)

CAPRI does not give crops fixed mineral-fertiliser rates. Each crop group's need of each nutrient (N, P2O5, K2O) must be
covered by mineral fertiliser, manure, crop residues and deposition, each net of its losses, as an equality:

```
sum_crops in group  area x need x sqrt(yield factor) x need multiplier
   =  mineral x (1 - losses) x (1 + technology gains)
   +  manure  x availability x (1 + technology gains)
   +  residues x availability + deposition ...
```

Mineral fertiliser is therefore what the crops need beyond what manure, residues and deposition cover:

1. Manure has a fertiliser value: it replaces mineral N, so shrinking herds raise mineral use where manure was used.
2. Purchases cannot be negative, and the need multiplier (CAPRI's over-fertilisation factor
   `v_cropNutNeedMultFact`) is fixed at the base in a simulation (prep_sim.gms:30): manure beyond the need is not free.
3. Manure is traded between regions (`manExportOrAppl_`, `docs/MANURE_MARKET.md`).

Verified against CAPRI's own numbers, reference run `res_2_1730greendeal_refdefaulta` (dataOut), Weser-Ems, winter
wheat, kg N/ha:

| term | value |
|---|---|
| mineral delivered (`fertDist_mine_perha`) | 192.8 |
| - mineral losses (`nutNed_mine_loss_gasRunTot_perha`) | -13.5 |
| manure delivered (`fertDist_excr_perha`) | 56.5 |
| - manure unavailable (`nutNed_excr_unavailable_perha`) | -16.5 |
| residues net (`fertDist_cres_perha` - losses) | 8.7 |
| = need (`NITF` = `nutNed_lhs` = `nutNed_rhs`) | 228.0 |

A crop's `NITF` in dataOut is its total need, not mineral fertiliser.

CAPRI's minimum mineral share NUTMIN_ (fert/fertpar.gms p_minShareMinFert) enters star 3.0's regional model only with
the inner fertiliser distribution model off (supply_model_e_list_linear.gms:61); prep_sim.gms aborts if the GUI's
minimum shares are combined with the inner model. NUTMAX_ is in no equation list of star 3.0's simulation model.

## CAPRI's inner fertiliser distribution model

star 3.0's GUI sets `useInnerFertDistModel` on. CAPRI then distributes, per region and nutrient, three sources -
mineral fertiliser (MINE), manure (EXCR), crop residues and deposition (CRES) - over 17 crop groups
(`supply/define_ngrp_sets.gms`: WHEA, BARL, MAIZ, CERE, RAPN, SUNF, SOYA, PULS, POTA, SUGB, MAIF, ROOF, OFAR, GRAS, VEGE,
PERM, OAFC) as the mode of a posterior density: gamma priors on every flow (`supply/set_fert_priors.gms`), the group
needs as equalities (NUTNED_), the regional pools (`fertDistMine_`, `fertDistExcr_`, `fertDistCres_`; CRES not to the
permanent groups GRAS and PERM), and the first-order conditions of the posterior mode (`e_fertDistPartial`,
`e_focFertDist`) as equations of the regional model. Each flow lies within 0.001 and 1000 x its prior mode; the duals
are bounded at +-10.

Priors: in a simulation CAPRI's prior mode is the baseline's posterior mode per ha x the group's area at the start of
the simulation, fixed (UPDATE_FERTMAX_IN_STEPS off, the default; prep_sim.gms -> set_fert_priors.gms). capri-mod's
priors (`tools/build/build_fert_dist_priors.py`, `fert_dist_priors_2030.csv` for N, `fert_dist_priors_npk_2030.csv` for N,
P, K) come from CAPRI's 2030 reference, crop by crop summed to the groups (the dump's rows named CERE, PERM, GRAS are
reporting aggregates over other crops, as `minfert_redu_by_crop.gms` notes): 250 CAPRI regions in 35 countries, plus
the country for model regions without a CAPRI region (Berlin, Hamburg, Bremen). Checked when built against CAPRI's own
`priFertDist` results (DE, FR, NL, BL, DK, IT): postModePerHa reproduced to 4e-5 on 4,683 values; accuracy 1.

Where CAPRI's 2030 posterior admits no allocation at the model's own base (a region whose base manure or herds differ
from CAPRI's 2030 reference), capri-mod does what CAPRI does when its baseline changes (fert/ferttrm_years.gms):
blanket priors splitting each group's need (net of the permanent crops' own residues, at least 10% of the need)
equally over its sources (a third each; a half for the
permanent groups, which take no pooled residues), half of grassland's mineral prior moved to manure, accuracy 2
(residues 5), their posterior at the model's base becoming the simulation prior
(`RegionalSupplyModel._npk_recalibrate_priors`, `InnerFertDist.calibrate`; REGISTERED, K21, K50 departure 2).

## capri-mod, NLP form (default)

`capri_regional_nlp.CapriRegionalNLP._fert_block`, data `capri_mod/fert/npk.py` (`tools/build/build_npk_balance_2030.py`,
CAPRI's 2030 reference; the builder checks NUTNED_'s identity per crop and the pools):

- per nutrient (N, P, K) and crop group: NUTNED_ as an equality; need per ha = the crop's own NITF/PHOF/POTF x
  sqrt(yield / base yield) x a need multiplier per region and nutrient, set so that NUTNED_ summed over the groups
  holds at the base with the base mineral use (REGISTERED: CAPRI's multiplier is per crop group and acts on the need
  alone; here it scales the need net of the permanent crops' own residues);
- mineral flows sum to the purchases (>= 0), bought at CAPRI's unit value of NITF/PHOF/POTF; the crops' fertiliser
  cost per ha is taken out of their margins;
- manure flows sum to the manure applied (ManureNPK_): the accounts' excretion less CAPRI's housing and storage loss
  shares (`manure_housing_losses_2030.csv`, K21), net of traded manure, plus the N the ammonia options keep through the
  N loss cascade; P2O5 and K2O per head from CAPRI's 2017 totals, applied in CAPRI's 2030 proportion;
- endogenous manure N availability (endoManAvFact on; fert/endoManAvail.gms): availability = base + slope x (manure
  per ha - base manure per ha), slope -0.0015; P and K fixed;
- fertiliser options: mineral N x (1 + sum share NMIN); inhibitor on manure: manure N x (1 + share NMAN);
- the inner model's first-order conditions inside every solve, flows 0.001-1000 x mode, duals +-10 (widened to
  +-1000 where a tiny group needs more, REGISTERED, K50 departure 3).

The allocation the regional model solved is the run's report: `results["fert_dist"]` (N, region x group: area,
mineral, manure and residue N per ha, caps where they apply) and `results["fert_npk"]` (N, P2O5, K2O by group and
source). The environmental accounts take the purchases as mineral N.

## Mineral fertiliser reduction, CAPRI's `mineRedu`

A Green Deal policy shock (EU27; scenario only): `greendeal_scenario(mineRedu=...)`, `PolicyScenario.mineral_redu`,
`run_f2f_2030.py --mine-redu`. Values as star 3.0's GUI: 00, 20, 10crp, 13crp, 17crp, 20crp.

| CAPRI | capri-mod (NLP form) |
|---|---|
| `minfert_redu_uaa.gms` ("20"): `e_synNMax`, mineral N per ha of land <= baseline x (1 - r) | purchases <= (1 - r) x base purchases per ha x current land |
| `minfert_redu_by_crop.gms` ("NNcrp"): `p_nMaxPerHa(ngrp, MIN)` = baseline per ha of the group x (1 - r), as the "f2f" regulation of the inner model (beta density, mode 0.75 x max, accuracy 0.25) | same regulation on each group's mineral flow, from the model's own base allocation (the fertilisation block at the calibration point) |
| groups below 30 kg N/ha and listed (region, group) pairs exempt: capped at 1, 1.1 or 1.2 x baseline | same; the list read from CAPRI's file by year (`tools/build/build_mineral_redu_rules.py`; 9 pairs for 2030) |
| "limCres": residues to a group at most 1.3 x baseline per ha (+0.5 for listed pairs), mode at baseline, accuracy 10, every nutrient | same |

CAPRI caps from its baseline results (`p_baselineDataout`); capri-mod from its own baseline allocation, as for the
surplus target. Where the caps leave a group's need unmet (IPOPT reports infeasibility), the duals are widened to +-1000; if that is not enough, the crop groups are exempted one at a time as CAPRI exempts groups in minfert_redu_by_crop.gms (p_checkSmallMine: the group's cap at its baseline mineral N per ha, fertiliser.exempt_cap_factor = 1.0), those whose need is out of reach under the cap first, with CAPRI's duals and then the widened ones (K71); the
relaxation is kept for the rest of the scenario and recorded in `metadata["nlp_relaxed"]` (REGISTERED, K50 departures
11, 13).

Organic area target (`pol_input/greendeal/organic_area.gms` -> `organic_minfert_redu.gms`, 'region_and_crop'): an "f2f"
regulation on each group's mineral flow at the base allocation per ha x (1 - the group's organic conversion), groups
below 10 kg N/ha at base capped at the base; "limCres" at 1.2 x base for every nutrient; with mineRedu the more
stringent mineral cap of the two holds and mineRedu's limCres. The group's conversion is capri-mod's (its organic
targets per member state and crop class, weighted by base area; REGISTERED, K50 departure 10).

## Conic form (`supply_form = "conic"`)

The conic form has no flows per crop group in the regional problem:

- one regional crop-need row for N (NUTNED_ summed over the groups), with the terms that change mineral N (manure,
  traded manure, the ammonia options' N kept, the inhibitor's relief, the fertiliser options, catch crops), mineral N
  substituted at fixed rates from the balance (`EnvironmentalModule` substitution factor); P and K are not modelled;
- NUTMIN_ as a floor on that row only when `RegionalSupplyModel.fert_dist_inside` is off
  (`use_min_mineral_share = None`: as CAPRI, K40);
- with `fert_dist_inside` (default) the inner model (`capri_mod/fert/inner_fert_dist.py`, Newton's method on the group
  and pool duals) is checked after the solve; where no allocation exists at the conic solution, the region is solved
  again in CAPRI's coupled form with IPOPT (`capri_mod/supply/capri_nlp.py`, K9);
- the mineral caps by crop group enter through their sum (mineral N <= sum_g cap_g x area_g) and the inner model then
  allocates under the regulations; the diagnosis of K49 showed that this sum can be met where the per-group caps
  cannot, one reason for the NLP form;
- a manure-application limit (170 kg N/ha or the base level, where an N target applies) that CAPRI does not have.

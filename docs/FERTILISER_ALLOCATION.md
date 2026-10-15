# Fertiliser allocation — design

Status (Sprint 9e, October 2026): **CAPRI's inner fertiliser distribution model and the Green Deal mineral
fertiliser reduction (`mineRedu`) implemented** - see the two sections at the end. Earlier: **Stages 1 (manure
trade) and 2 (mineral N follows need) implemented; base balance identical by construction (tested).** (The
minimum-mineral floor mentioned here before is not in the model: star 3.0's "Allow minimum shares of anorganic
fertilizers" is false, as in capri-mod.) Stage 2 was implemented
as a linearisation around the base rather than a new solver variable: mineral N = base rate +
manure-covered share of need − (availability/efficiency) × (1 − floor share) × manure available,
with need ∝ √yield. A new variable remains an option if the linearisation proves too coarse.

## Why

CAPRI does not give crops fixed mineral-fertiliser rates. In its supply model
(`supply/supply_model.gms`, equation `NUTNED_`), each crop group's nitrogen
**need** must be covered by mineral fertiliser, manure, crop residues and
deposition, each net of its losses:

```
Σ_crops area × need × (1 − fixation share) × over-fertilisation factor × √(yield factor)
   =  mineral N × (1 − losses) × (1 + technology gains)
   +  manure N  × availability  × (1 + technology gains)
   +  residues × availability + deposition …
```

Mineral fertiliser is therefore **whatever the crops need beyond what manure,
residues and deposition cover**. Three consequences this model lacked:

1. **Manure has a fertiliser value**: it replaces mineral N, so shrinking herds
   raises mineral use where manure was being used efficiently.
2. **In manure-surplus regions extra manure is pure surplus**: mineral use cannot
   fall below zero, so there the herd is the only lever.
3. **Manure is traded between regions** (`manExportOrAppl_`): 11% of EU manure N
   leaves its region of origin; 38 regions export more than a fifth (Weser-Ems
   31%).

## Verified against CAPRI's own numbers

From the reference run (`res_2_1730greendeal_refdefaulta`, dataOut), Weser-Ems,
winter wheat, kg N/ha:

| term | value |
|---|---|
| mineral delivered (`fertDist_mine_perha`) | 192.8 |
| − mineral losses (`nutNed_mine_loss_gasRunTot_perha`) | −13.5 |
| manure delivered (`fertDist_excr_perha`) | 56.5 |
| − manure unavailable (`nutNed_excr_unavailable_perha`) | −16.5 |
| residues net (`fertDist_cres_perha` − losses) | 8.7 |
| **= need (`NITF` = `nutNed_lhs` = `nutNed_rhs`)** | **228.0** |

A crop's `NITF` in dataOut is its **total need**, not mineral fertiliser.

## Data (in `capri_data/2017/environment/`)

- `fert_dist_priors_2030.csv`, `fert_dist_crop_groups_2030.csv` — CAPRI's mineral, manure and residue N per
  ha of each crop group in every CAPRI region (Sprint 9e; they replace `capri_fertiliser_allocation_2030.csv`,
  153 regions in 17 countries, which no code read any more).
- `capri_regional_n_balance_2030.csv` — per region: MINFER, EXCRET, MTRADE
  (manure net export), IMPORT, EXPPRD, CRESID, BIOFIX, ATMOSD, SURTOT.

Vintage 2030 (the scenario year); used for **shares and efficiencies**, not
levels, so the 2017 base levels stay this model's own.

## Model change, in stages

**Stage 1 — manure trade.** Each region's manure N enters its balance net of its
base export share, and importing regions receive it. Fixed shares at first
(CAPRI makes them endogenous with a cost). Small change, no new variable.

**Stage 2 — mineral fertiliser as a variable.** One variable per region,
`M ≥ 0` (t N), with a need-coverage row

```
Σ_c need_c · x_c  −  a_man · (1 − export) · Σ_a man_a · x_a  −  R  ≤  e_min · M
```

and cost `p_N · M` in the objective. Crops' variable costs lose their fertiliser
share (it moves to `p_N · M`); `p_N` is calibrated per region so that base
fertiliser spending is unchanged. The nitrogen balance uses `M` instead of fixed
per-crop mineral rates. Calibration requirement: the base solve must reproduce
base activity levels exactly (the PMP terms are recalibrated with the new row
binding at base). **Every baseline anchor must hold before anything else.**

**Stage 3 — technologies on the variable.** The fertiliser-efficiency
technologies act on `e_min` (CAPRI's `1 + Σ share × NMIN`), replacing the current
per-crop scaling.

**Stage 4 — validation.** Against CAPRI's reference: regional mineral use,
manure allocation and surplus; then Farm-to-Fork against Figure 5 and Table 15.

## Simplifications (documented, deliberate)

- Need is covered at **regional** level, not per crop group; CAPRI's group
  constraints (`NUTMIN_`, `NUTMAX_`) restrict where manure can go. To revisit if
  regional aggregation lets manure substitute too freely.
- Manure export shares fixed at their base values in Stage 1.
- Phosphorus and potassium are not modelled.

## Current state (October 2026)

- **Stage 2 is what the balance does.** The linearised substitution described at the
  top is active in `EnvironmentalModule.compute_nitrogen_balance`, and the supply
  model's nitrogen row captures it through the animals' coefficients (about
  (1 − factor) × manure). A separate mineral-N variable (the Stage 2 option) was
  implemented in October and **removed**: it counted substitution twice.
- **Stage 1 with endogenous trade** now exists as the optional manure market
  (`CAPRIModel.use_manure_market`), built on that substitution; see
  `docs/MANURE_MARKET.md`. With the market off, base export shares stay fixed.
- **CAPRI's manure-within-crop-need limit** (`NUTNED_` is an equality with mineral N
  ≥ 0) is applied where the nitrogen target applies.

## CAPRI's inner fertiliser distribution model (Sprint 9e)

star 3.0's GUI sets `useInnerFertDistModel` on. CAPRI then distributes, per region, the nitrogen of three
sources - mineral fertiliser (MINE), manure (EXCR), crop residues and deposition (CRES) - over 17 crop groups
(`supply/define_ngrp_sets.gms`: WHEA, BARL, MAIZ, CERE, RAPN, SUNF, SOYA, PULS, POTA, SUGB, MAIF, ROOF, OFAR, GRAS,
VEGE, PERM, OAFC) as the mode of a posterior density: gamma priors on every flow (`supply/set_fert_priors.gms`),
the group needs as equalities (`NUTNED_`), and the regional pools (`fertDistExcr_`, `fertDistCres_`; CRES not to
the permanent groups GRAS and PERM). `capri_mod/fert/inner_fert_dist.py` solves the same first-order conditions
(`e_focFertDist`) by Newton's method on the group and pool duals.

**Priors** (`tools/build_fert_dist_priors.py`, `capri_data/2017/environment/fert_dist_priors_2030.csv`): in a
simulation CAPRI's prior mode is the baseline's posterior mode per ha x the group's current area, with the
calibration's accuracy. From CAPRI's 2030 reference (`res_2_1730greendeal_refdefaulta`), crop by crop summed to the
groups (the dump's rows named CERE, PERM, GRAS are reporting aggregates over other crops, as
`minfert_redu_by_crop.gms` itself notes): 250 CAPRI regions in 35 countries, plus the country for model regions
without a CAPRI region (Berlin, Hamburg, Bremen). Checked against CAPRI's own `priFertDist` results (DE, FR, NL,
BL, DK, IT): postModePerHa reproduced to 4e-5 on 4,683 values; accuracy 1 everywhere.

**What it changes.** With every flow positive, the sum of the group equalities is the regional identity the
balance already uses (need = efficiency x mineral + availability x manure + availability x residues). So in
star 3.0's default settings the allocation changes nothing in the regional totals: it reports where the N goes,
and it is what the crop-specific mineral fertiliser reduction acts on. Each run returns
`results["fert_dist"]` (region x group: area, mineral, manure and residue N per ha, the cap where one applies).
At the baseline's totals the model returns CAPRI's priors exactly in every region (tested).

## Mineral fertiliser reduction, CAPRI's `mineRedu` (Sprint 9e)

A Green Deal policy shock (EU27; scenario only): `greendeal_scenario(mineRedu=...)`,
`PolicyScenario.mineral_redu`, `run_f2f_2030.py --mine-redu`. Values as star 3.0's GUI: 00, 20, 10crp, 13crp,
17crp, 20crp.

| CAPRI | capri-mod |
|---|---|
| `minfert_redu_uaa.gms` ("20"): `e_synNMax`, mineral N per ha of land <= baseline x (1 - r) | a row in each regional model: sum_a m_a x_a <= (1 - r) x baseline mineral N per ha x current land |
| `minfert_redu_by_crop.gms` ("NNcrp"): `p_nMaxPerHa(ngrp, MIN)` = baseline per ha of the group x (1 - r) (`nMax_`), as the "f2f" beta regulation of the inner model | caps per group from the baseline's inner-model allocation; the row sum_a (m_a - kappa_a) x_a <= 0 with kappa_a = sum_g share_ag x cap_g |
| groups below 30 kg N/ha and listed (region, group) pairs exempt: capped at 1, 1.1 or 1.2 x baseline | same; the list read from CAPRI's file by year (`tools/build_mineral_redu_rules.py`; 9 pairs for 2030) |
| "limCres": residues to a group at most 1.3 x baseline per ha (+0.5 for listed pairs), mode at baseline, accuracy 10 | same, in the inner model |

m_a is the activity's mineral N from the environmental module's own balance (linear in activity levels, at the
solve's yields and fertiliser factors - the same terms as the nitrogen-balance row), so the row and the reported
mineral N agree. The cap's shadow price drives CAPRI's fertiliser technologies inside the conic model on the same
footing as the nitrogen-balance price (each saves mineral N on both rows).

**By crop, aggregated.** CAPRI's caps are per group, but the inner model moves manure between groups freely
(no regulation on EXCR) and residues within limCres. So the condition the regional model faces is the sum over
the groups - mineral N <= sum_g cap_g x area_g - and the inner model then finds the allocation under the
regulations; it does in every region tested (the reported table carries the caps). Where the accounts' mineral N
exceeds the row's by their own adjustments (~0.1%), the caps are scaled to leave room (`cap_scale`).

**Baseline.** CAPRI caps from its baseline results (`p_baselineDataout`); capri-mod from its own baseline point,
as for the surplus target, and from its own inner-model allocation at that point.

**Technology base (fix).** Until 9e the fertiliser technologies inside the conic model scaled each crop's whole
mineral coefficient, which carries its share of the manure-covered need as well; the accounts scaled only its
mineral rate. The rows then saved ~40% more mineral N than the accounts showed (Upper Bavaria wheat: 108 against
77 kg N/ha). Now the technologies act on the mineral rate in both, as CAPRI's mineral x (1 + E).

REGISTERED:
- Per-group caps enter the regional model through their sum (the reallocation argument above); a group that has
  no manure prior and a binding cap would need its own row.
- The ammonia technologies act on the mineral row (manure N kept from losses displaces mineral N, sub x ret, as
  on the N row) where the surplus target runs alongside; with the mineral cap alone they stay at their base shares
  (their manure data come with the surplus row).
- With fertiliser technologies outside the conic model (feeding solved apart), they respond to the
  nitrogen-balance price only.
- Need factors in the allocation: sqrt(yield / base yield), area-weighted over the group's crops.

**Effect.** Farm-to-Fork 2030 (JRC121368 settings, mine00): with the inner model alone every indicator is
unchanged (s63, gap 3.31). With the technology-base fix (s60): N surplus −32.1 → −34.3% (CAPRI −33.5), fertiliser
N2O −42.9%, meat prices +3 to +9 points (beef +20.8, pork +42.9: CAPRI +24, +43), herds 1–3 points further down
(pigs −23.1%, dairy cows −13.7%); 20-indicator gap 3.31 → 3.77. The baseline's EU allocation against CAPRI's 2030
reference, mineral N per ha: wheat 115 / 94, barley 87 / 75, maize 126 / 131, rapeseed 117 / 93, sugar beet 233 /
184, grass 30 / 33 (capri-mod / CAPRI); manure is spread more heavily (capri-mod's EU manure N applied per ha is
higher), mineral N in total 10.4 against 11.4 Mt.

Green Deal 2030 (star 3.0's switchboard, surplus −50%, manure trade on; s62 mine00 against s65 mine20crp): the
surplus target already cuts EU mineral N by 55%, so the by-crop caps bind in 49 regions, where it had cut a group's
mineral N by less than a fifth (median shadow price 3.3 EUR/kg N): EU mineral N −54.7 → −55.4%, cereal price
+1.7 points, cereal output −1.1, fertiliser N2O −0.8, herds within 0.5 points. (A first run without the ammonia
options on the mineral row, s61: 58 regions, 10 EUR/kg N, cereal price +3.0.)

Manure-saturated regions (mineral N near zero) have group needs that the sources their priors allow cannot meet
(grassland takes all the manure, arable groups have only mineral and residue priors); CAPRI's over-fertilisation
factor (`v_cropNutNeedMultFact`) absorbs that, capri-mod reports these allocations as unconverged: 1 region in the
baseline (RO22), 8 in Farm-to-Fork, ~60 in the Green Deal. REGISTERED.

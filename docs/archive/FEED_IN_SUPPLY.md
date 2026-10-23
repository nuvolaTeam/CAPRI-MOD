# Feeding inside the supply model — design, and the wider coupling review

Status: **ON BY DEFAULT since October 2026** (`CAPRIModel.use_feed_in_supply = True`;
`run_f2f_2030.py --no-feed-in-supply` for the old separate ration model). Full-EU 2030 Farm-to-Fork, with
Sprints 1–2 in place: converged in 12 iterations (13 min, against 23 and 18 min without), average gap to
JRC121368 7.69 → 6.73 (sheep −20.7 → −16.7%, pork price +60 → +56%, beef price +27 → +24%; N surplus −34.6%
against CAPRI's −33.5%). Base anchors unchanged; tests pass.
Earlier status: conic regional model built (`capri_mod/supply/feed_conic.py`) and reproducing the base within
~0.3%: all 236 land-market regions solve at base (median deviation 0.24%, largest 1.48%). Replaces the separate EU feed-ration model (`capri_mod/feed/ration.py`), which is
solved apart from the regional supply models and iterated against them.

## Why

Several gaps traced over October 2026 come from solving apart what CAPRI solves together:

- pricing home-grown fodder at its shadow price created a loop between two models (ration ↔ fodder
  use ↔ fodder dual) that would not converge; CAPRI never has that loop;
- nitrate barely entered the rations: its value is the ration's protein shadow price, which a
  separately calibrated ration model puts near zero;
- genetics and feed additives act through feed requirements in CAPRI's equations, not as add-ons;
- cattle enteric methane in CAPRI follows the actual feed mix (`GWPCH4ENT_`); ours is a fixed
  factor per head, so ration shifts under Farm-to-Fork cannot change it.

## CAPRI's formulation (`supply/supply_model.gms`)

Decision variable `v_feedInpCoeff(r, animal, A, feed)`: kg of each feed per head.

| Equation | Content |
|---|---|
| `REQSN_` | requirement per head per day × production days − Σ feed per head × content ≤ 0 (dry matter, fibre) |
| `REQSE_` | the same as equality (energy, protein); low-N feed, genetics, nitrate and linseed modify it |
| `FEDUSE_` | feed use (1000 t) = Σ animals feed per head × herd / 1000 |
| `SUPBAL_` | fodder balance on that feed use |
| `QUADRF_`, `QUADRF1_` | feed PMP cost = herd × Σ feed per head × (CNST + ½ SLOP × feed per head) |
| `GWPCH4ENT_` | cattle enteric CH4 = Σ emission per kg feed × feed per head × herd |
| feed-share limits | per feed and feed aggregate, relative to total dry matter (`p_maxFeedShare`, `FeedAggr`) |

## capri-mod formulation

Variables: herds x_a (as now) and **total feed F(a, f) = feed per head × herd**. Then

- requirements: Σ_f content_f × F(a, f) − req_a × x_a ≥ 0 (or = 0) — linear;
- feed use, fodder balance, purchased-feed costs, cattle enteric CH4 — linear in F;
- feed-share limits — linear in F;
- feed PMP: x_a × Σ_f c (CNST + ½ SLOP c) with c = F/x_a gives Σ_f CNST F + ½ SLOP F²/x_a — the
  **perspective** of a quadratic, convex, representable as a **second-order cone**.

So each regional model becomes one convex conic program. Clarabel solves it exactly (interior
point); its multipliers give the shadow prices directly, replacing the code that re-detects binding
constraints (which made Clarabel fail to converge in October). The built-in active-set solver cannot
handle the cone; it remains for problems that stay quadratic.

Calibration, as in CAPRI: CNST and SLOP from CAPRI's own `p_pmpFeedInpCoeff` (already used by the
ration model where available), on a per-head basis; base feed per head from the regional rations.

## Consequences

- `capri_mod/feed/ration.py` and the ration loop in `CAPRIModel._update_rations` are replaced; market
  feed demand comes from the regional F totals.
- Nitrate, linseed, low-N feed and genetics enter the requirement equations as in CAPRI.
- Cattle enteric CH4 follows the feed mix.

## The wider coupling review (to run alongside)

Where capri-mod still departs from CAPRI's structure, to be checked one by one against the GAMS code:

1. **Solved jointly in CAPRI's supply model, separately or not at all here**: feeding (this note),
   fertiliser distribution to crops (`fertDistExcr_`, `NUTNED_` — partly), young-animal balances (herd
   links), mitigation options, manure trade.
2. **Activities**: CAPRI distinguishes intensity variants and age classes (DCOL/DCOH, BULL/BULH,
   HEIL/HEIH/HEIR, four calf activities, HENS/POUF, SHGM/SHGF; PIGF/SOWS now split, Sprint 5) where capri-mod has 10 animal
   activities; crops: CAPRI about 50, capri-mod 34.
3. **Commodities and processing**: dairy processing (butter, cheese, powders), further processed
   products, biofuels; capri-mod has 35 commodities.

Each item gets a short note: what CAPRI does, what capri-mod does, the effect on results, and whether
to adopt CAPRI's structure.

## Build log

- Base point infeasible at first: the fodder balance had left out suckler cows, heifers and sheep (raw
  head-count names); fixed in `tools/build_fodder_balance.py` (shared `HERD_ALIASES`).
- Clarabel could not solve the unscaled problem (feed ~10⁶ t, cone variables ~10¹⁰ next to herds ~10²):
  feed variables are scaled by their base totals and cones by base herds.
- Fodder roots (`FROO`) have no balance row and must keep their ration price (they had become free).
- Base reproduction: within 0.26–0.27% of the current solution.
- All regions at base: 232 of 236 tested regions solve; median deviation 0.25% (90th percentile
  0.55%). Unbounded: PL81, PL82, PL84; stalled: FI1D (national-fallback regions). Twelve regions
  (Ireland, Vienna, two Croatian regions, city-states, Ceuta and Melilla) use the solve path without
  the land market, which the conic model does not cover yet.
- Numerics: feed rows normalised; original variables scaled by their base values; rows slack by an
  enormous margin dropped. National-fallback land-market terms reach 10⁸ (Polish NUTS 2021 regions) —
  a data question recorded for the land-market builder. Result: all 236 land-market regions solve.
- Wired behind `use_feed_in_supply` (on by default since October 2026). Shadow prices come from Clarabel's own multipliers when the
  conic model solved the region (re-detection from interior-point solutions made inner loops run long).
  Same speed as the default on a two-region check, with consistent nitrogen shadow prices.
- Validation must use the full EU: on small subsets the EU egg premium oscillates (a subset artefact).
- Cattle enteric methane from the feed mix (CAPRI `GWPCH4ENT_`): gross energy per feed group from
  CAPRI's NRC table, Ym from its IPCC table (`tools/build_enteric_feed_factors.py`). Base check:
  dairy cows 169 kg CH₄ per head in Brittany and 179 in Düsseldorf, against CAPRI's 2030 reference
  ~159 and ~173 (low/high-yield average) — within 3–6%. The fixed factor used so far (117 kg) is about
  30% too low.

## Fertiliser technologies inside (design)

External mechanism today (`RegionalSupplyModel._apply_balance_price`): nine CAPRI options per member
state (`_fert_techs`, from CAPRI's mitigation table, target N2OSYN): regional shares s_t by CAPRI's
adoption rule, efficiency E = Σ s_t NMIN_t (NMIN = (QEmitt_NOC / QEmitt_t − 1)^1.1: precision farming
0.54, inhibitors 0.48, GComTN/VN 0.67/0.71, VRT 0.05–0.21, timing 0.10), mineral N per ha ×
(1 + E₀)/(1 + E) for every fertilised crop (CAPRI: mineral N × (1 + E) meets crop need), cost per ha
a(s − s₀) + ½b(s² − s₀²). With E up to ~0.5 a single first-order treatment is not accurate
((1 + E)⁻¹ = 0.67 vs 0.5 at E = 0.5).

Chosen formulation — successive linearisation inside the outer loop:
- variables H_t = s_t × A (adopted hectares; A = fertilised area, an auxiliary variable equal to the
  sum of fertilised crop areas); 0 ≤ H_t ≤ max_t A; Σ H_t ≤ A;
- cost per region a(H − s₀A) + ½b(H²/A − s₀²A) — rotated cone, as for the ammonia measures;
- mineral N in the N row: W·g(E) with W = Σ nmin_c × area_c and g(E) = (1 + E₀)/(1 + E), replaced by
  its tangent at the previous outer iteration (W̄, Ē): W g(Ē) + W̄ g′(Ē)(E − Ē), E = Σ NMIN H/Ā;
- the tangent point is updated each outer iteration, so at convergence CAPRI's exact relation holds
  and no inner loop remains.

Alternatives considered: keep them external (inner loop stays); one technology per hectare (exact
and convex, but a different aggregation from CAPRI's additive E).

## CAPRI's limits on the fertiliser technologies (implemented, with CAPRI's factors)

`GComTN` and `GComVN` are GAINS combinations (timing + nitrification inhibitors; variable-rate
technology + nitrification inhibitors), allowed up to 100% in CAPRI. What CAPRI adds, with
`restMitFert` on, is that technologies can only remove **over-fertilisation**, measured by the
regional factor x = `v_cropNutNeedMultFact` (fertiliser applied ÷ crop need):

- `Tot_MitFert_`: 1 + Σ share × NMIN ≤ max(x + 0.1, 1) (`p_OverFertMarkUp` = 0.1);
- regional maximum shares lowered where crop need lies above precision farming's level
  (`envind/ghgMiti.gms`; nitrification inhibitors keep their national maximum).

Both are implemented for the external rule and inside the conic model. With in-memory test values
(x = 1.1) both paths respect the cap exactly and choose almost the same shares, and Düsseldorf's
nitrogen price rises from about €2 to about €40/kg: without the cap, technologies made the target
almost free in moderate-surplus regions. The factor itself must come from CAPRI's results
(`results\fert\priFertDist_<country>1730….gdx`, `p_CropNutNeedMultFact`); until then the model warns
once and runs without the cap (`tools/build_overfert_factors.py` converts the export).

**With CAPRI's factors** (`crop_nut_need_mult_fact_2030.csv`; x = 1.000 in Weser-Ems, Schleswig-Holstein,
Upper Bavaria, Brittany, Düsseldorf, Lombardy): the default model's average gap from CAPRI falls from
5.5 to 4.5 points (dairy −8.4% vs CAPRI −10%, enteric methane −10.5% vs −14.6%). In the inside version
the cap is weighted by crop nitrogen need — CAPRI: "total N savings shall not exceed over-fertilisation";
identical to CAPRI's constraint under its uniform shares — since area weights let crop-specific adoption
save more nitrogen than CAPRI allows.

**Update (October 2026), cost basis and active options.** CAPRI's fertiliser-option costs are per tonne
of crop N need (`GHG_Mit_Cost_` multiplies them by mineral N × (1 + E)), not per hectare as above; both
paths now charge them per tonne (the conic model scales each crop's cost by its need n_c/1000), with
CAPRI's calibration (relative subsidies 1.2/0.2, or 0.8/0 where the regional maximum share is below 1).
Only the options CAPRI's Green Deal reference activates are offered (precision farming, timing,
inhibitors; VRT_SRUC lacks data), not the GAINS combinations. See docs/MITIGATION_IN_SUPPLY.md.

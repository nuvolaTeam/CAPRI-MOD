# EU feed ration choice — design

Status: **data built** (`feed_ration_2017.json` by `tools/build_feed_ration.py`: 235 regions, 2,084 region × animal entries, energy and protein closing to a median of 0.00%) ; **ration programme built** (`capri_mod/feed/ration.py`), not yet wired into the model — waiting for CAPRI's feed-share bounds (below).
Replaces the last fixed feed coefficients for the EU: today feed per head is
fixed (CAPRI 2017 totals ÷ herds), so EU feed demand follows herds but not feed
prices, and cake and cereal prices swing too much when herds change (Farm-to-Fork:
sunflower cake −23%).

## How CAPRI does it

Outside the EU, feed demand is a market function with feed-price elasticities
(`p_ElasFeed`) — implemented here in `feed_demand_nonEU.json` (125 region × feed
entries, own and cross).

**In the EU there is no feed-demand elasticity**: the ration is chosen inside
each regional supply model (`supply/supply_model.gms`). For every region and
animal activity, the feed input coefficients `v_feedInpCoeff(feed)` are
variables, subject to:

- **nutrient requirements** per head (`p_animReq`: energy, crude protein, dry
  matter, …) met by the feeds' nutrient contents (`%data%(…, REQMSE, FEED)`),
  `NutContFeed_`;
- **minimum and maximum feed shares** per feed and per feed aggregate
  (`MINSHR_`, `MAXSHR_`, `MINSHRAGGR_`, `MAXSHRAGGR_`);
- **shares of feeds within aggregates** around their observed means
  (`FeedShareInAggr_`), and limits on roughage (`FeedShareInAggrlimit_`);

with feed costs in the objective. Feed demand for the EU market is then the sum
over regions and animals of heads × chosen coefficients — so it responds to
relative feed prices (substitution between cakes, cereals and other feeds) while
nutrient requirements tie the total to herd sizes.

## Data — verified (CAPRI 2017 regional results, `res_17*`)

Per region and CAPRI animal activity: the base ration per head per year (kg of
fresh feed, by feed group: grass `FGRA`, fodder maize `FMAI`, other fodder `FOFA`,
roots `FROO`, straw `FSTR`, cereals `FCER`, protein-rich `FPRO`, energy-rich
`FENE`, milk feeds `FMIL`, other `FOTH`, …), the requirements per head **per day**
(energy `ENNE`, crude protein `CRPR`, dry matter `DRMN`/`DRMX`), and `DAYS`. Per
member state (and region where present): nutrient contents per kg of fresh feed
(`ENNE`, `CRPR`, dry matter `DRMA`) and unit values (`UVAG`).

**Identity check over all 4,518 region × animal cases:** ration × contents ÷ days
= requirement, to a median of 0.00% for energy and protein (nearly all within a
few percent; fattening bulls and heifers carry a ~2% surplus, i.e. slack
constraints). German dairy cows: energy 40,842 ÷ 365 = 111.9 vs 112.0; protein
789.8 ÷ 365 = 2.164 vs 2.167 kg; dry matter 19.34 vs maximum 19.30 kg/day.

**Dry-matter bounds — resolved from CAPRI's code.** For some animals base intake
is above the maximum (95th percentile +42% for high-yield dairy, +64% for sheep
and goats). CAPRI does not impose such raw bounds: at calibration it **trims the
requirements to the data** (`p_trimFeed` turns `p_animReq` into the variable
`v_animReq` in `REQSN_`/`REQSE_`, `supply_model.gms`), so the observed base
ration is feasible by construction. The equivalent here is to calibrate each
requirement bound to include the base ration. Requirements are per **production
day** (`p_animProdDays`); the dry-matter maximum also bounds each single feed at
10× (`set_supply_bounds.gms`).

**Coupling to abatement.** CAPRI's requirements are modified by mitigation
options (low-nitrogen feeding on protein, breeding for feed efficiency on all
requirements, milk-yield genetics). The ration therefore links to the abatement
module, which the simplification register already says belongs inside the solve.

## CAPRI's calibration — feed PMP (`pmp_terms/define_const_pmp_param.gms`, Part I)

Each feed coefficient carries a cost `x × (CNST + ½ × SLOP × x)`:

- `SLOP = (1 / ε_feed) × price per kg (at least 10% of the cereal price) ÷ x_ref`,
  with `x_ref` = the base feeding, or 10% of the dry-matter requirement for feeds
  used in tiny amounts (a safeguard against huge relative jumps);
- `CNST` from the shadow values of the nutrient constraints at base, so the
  **observed base ration is exactly optimal at base prices**.

Assumed own-price feed elasticities (`supply/pmp_elas.gms`): **cereals and fodder
−10, protein-rich −5, other −1, energy-rich, milk feeds and straw −0.5** (the
in-code comment says 0.1; the values are what count).

## Implementation plan (revised)

1. Ration data per region for the model's animal activities (CAPRI totals ÷
   herds, as for revenue, manure and feed per head; the model's aggregated
   activities — dairy = low + high yield, pigs = sows + fattening — take summed
   requirements, a registered aggregation).
2. Per region and animal, the feed-PMP quadratic programme above at current feed
   prices; base ration exactly optimal at base prices by construction.
3. Its ration replaces the fixed coefficients in feed costs and in the market's
   EU feed demand (cereals and cakes), keeping the coupling two-way.
4. Validation: base identical (anchors, null trajectory); EU feed use per product
   against CAPRI; Farm-to-Fork cake and cereal prices and herds against JRC121368.

## Status of the ration programme (`capri_mod/feed/ration.py`)

- **Calibration exact:** all 2,084 base rations are reproduced at base prices
  (largest relative deviation 4×10⁻¹¹, no solver failures; 0.17 s for all).
- **Responses without share bounds are too large for cattle:** +10% cereal price
  → cereal feeding −51% (dairy), −80% (bulls); pigs and poultry barely move.
  This follows mechanically from CAPRI's assumed elasticity −10, which alone
  would remove cereals at a 10% price rise; in CAPRI the **minimum and maximum
  feed shares** (`MINSHR_`, `MAXSHR_`) restrain it.
- **Data needed:** CAPRI writes the share bounds in its regional-database stage
  (`capreg/save_or_load_feeddata.gms`) to `results\capreg\Chk_feeddataTOP….gdx`,
  symbols `S_p_maxFeedShare`, `S_p_minFeedShare` (and `S_p_animProdDays`, the
  production days now approximated by days in the year).
- Registered approximations: nutrient shadow prices at base fitted by NNLS to
  feed prices (standing in for the calibration-step duals); slope reference =
  base feeding; prices of on-farm fodder and of feeds without a market held at
  base; feeds without a CAPRI elasticity (FRMI, FPRI, FENI) fixed.

### CAPRI's own feed-PMP terms (received)

`pmppar_17XX.gdx` (`p_pmpFeedInpCoeff`: `CNST`, `SLOP` per region, activity
and feed). CAPRI **adds** these terms to the profit it maximises — verified:
that reading explains marginal feed costs by nutrient prices to a median 4.6%
residual, the opposite one 54.5%. The ration model now uses CAPRI's slopes
(aggregated to model animals; 1,242 of 2,084 entries, formula elsewhere) with
constants recalibrated to our constraints, base exact. Responses are almost
unchanged (+10% cereal price: dairy cereals −52%, bulls −77%): CAPRI's
restraint comes from its **share constraints**, which remain the missing input.

### Feed-share rules (from CAPRI's code)

The bounds are not stored in CAPRI's files; they are **rules** in
`feed/req_or_man_fnc.gms`, on a dry-matter basis relative to the current total
intake (`MAXSHR_`, `MINSHR_`). The fixed rules are implemented; bounds the base
violates are widened to the base share plus a 10⁻⁶ tolerance. Base exact for
all 2,084 rations. +10% cereal price: dairy cereals −1.8% (was −52%), bulls
−2.6% (was −77%). Suckler cows (−46%) and heifers (−45%) still swing: CAPRI
restrains them with **data-driven fibre-feed minimums** (from regional fodder
energy shares) — pending, together with the maximum "other feed" share. Wiring
waits for those.

### All share rules in; the fodder balance comes first

CAPRI's data-driven rules are implemented (fibre-rich minimums from regional
fodder-energy shares, straw, sheep, calves, other feeds), with an SLSQP
fallback: no solver failures, all rations in under a second, base exact.
Dairy, bulls and calves respond plausibly; suckler cows, heifers and sheep swap
cereals for fodder freely — CAPRI's rules allow it, but in CAPRI extra fodder
needs fodder area. **The supply model has no fodder balance** (only a grassland
area limit), so wiring the ration now would make fodder free. Next: the fodder
balance from CAPRI's regional fodder production (the current yields table mixes
fresh and dry-matter bases: grass use/production 2.7, fodder maize 0.8).

### Wired in, behind a switch

`CAPRIModel.use_ration` (default off) connects the ration to livestock feed
costs, the fodder balance and EU feed demand; the projection now carries the
switch to its fresh 2030 model. Baseline identical with the switch on. Ration
updates are damped between outer iterations (undamped they oscillated against
the damped prices). Next: confirm convergence under Farm-to-Fork, add the
fodder-balance equality band, then switch on by default.

### Convergence with the ration on — diagnosed, not yet solved

Profiled Farm-to-Fork (2017 base): supply passes dominate (125 s, then 381 s),
because regional QPs fall back to the slow general solver — 30 fallbacks in
the first iteration (the normal Farm-to-Fork cost: rations are still at base
there), 97 in the second, once the ration changes the fodder rows. Every failure
is an active-set "iteration limit"; raising the cap did not help, which points
to cycling. Next: trace one failing region's QP in isolation. The switch stays
off by default.

### On by default, as in CAPRI

With the land market on, Farm-to-Fork with the ration runs in about 3 minutes;
the ration brings the cereal price (+8.4%) and cereal production (−14.7%) onto
CAPRI's (+8%, −15%). `use_ration = True` by default.

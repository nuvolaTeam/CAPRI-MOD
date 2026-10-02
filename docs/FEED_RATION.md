# EU feed ration choice — design

Status: **design complete; data verified; dry-matter question resolved** — implementation next.
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

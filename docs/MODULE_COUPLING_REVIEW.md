# Module coupling and commodity coverage — review

*October 2026. Facts below are read from the code and checked by running it.*

## Summary

Two questions: are the modules coupled as tightly as they should be, and does
the model contain more product concepts than the 33 market-clearing
commodities? **Yes to both**, and the two are connected: most coupling gaps sit
exactly where a product concept exists in one module but has no market — or no
price — in another.

The model knows **34 crop and 11 animal activities, 11 feed items, 3 nutrients,
5 land types and the outputs of 5 processing chains** (sugar, three oilseeds,
milk). Only **33 commodities clear markets**. Several concepts are therefore
represented by a fixed coefficient, a proxy price, or a module that runs after
the solve instead of inside it. Three gaps matter most for the Farm-to-Fork
results:

1. **Market prices did not reach livestock** (fixed while writing this review).
   The market-to-farm price signal was keyed by market commodity (`PORK`,
   `MILK`), while farm margins look prices up by activity (`PIGS`, `DCOW`). No
   animal ever saw a meat, milk or egg price change; rye and oats never saw the
   cereal price. Under Farm-to-Fork the pork price rose 7% and pig farmers did
   not see it.
2. **Feed demand is not linked to herds.** The market module never refers to
   animals or feed. When the pig herd falls 16%, the market does not see the
   cereals and protein those pigs no longer eat. This very likely explains why
   cereal prices rise +13% here against CAPRI's +8%.
3. **Oilseed processing has no market.** Oils and meals are defined
   (`PROCESSING_OUTPUTS`) and soybean meal is the main protein feed, but neither
   oils nor meals clear a market; meal prices are proxied from bean prices.
   Protein-feed price changes, which drive pig and poultry costs, are therefore
   approximate, and oilseed prices miss the oil–meal value split.

## How the modules are coupled today

| From → to | What passes | Strength |
|---|---|---|
| Supply → market | regional outputs → 33 EU market quantities (the "bridge") | two-way, outer loop |
| Market → supply | relative price change per commodity | two-way, outer loop — **livestock disconnected until now** |
| Land market ↔ supply | land expansion vs land shadow price, per region | two-way, inside each iteration |
| Nitrogen target ↔ supply | balance price vs balance constraint, per region | two-way, inside each iteration |
| Environment → supply | each activity's nitrogen-balance coefficient | tight: the constraint uses the environmental module's own balance |
| Supply → environment | activity levels, realised yields, fertiliser factors | post-solve accounting (consistent with the constraint) |
| Feed requirements → supply | cereal and soybean-meal costs per head | one-way: costs only, no feed market |
| Fodder balance | **none** (herds not tied to fodder area) | regional fodder use = production | **add** — before wiring the ration |
| Feed module | feed balance vs availability | **post-solve, off by default** |
| Biofuel module | biofuel demand | **post-solve, off by default** |
| Abatement → supply | technology adoption | **post-solve**: does not change activity levels (CAPRI's reference makes technologies endogenous) |
| Supply → market (feed demand) | — | **none**: herds do not affect feed demand |

## Product concepts and their status

| Concept | In the model as | Clears a market? |
|---|---|---|
| Cereals, oilseeds, sugar beet, potatoes, pulses, fruit and vegetables, wine, olives (20 crops) | activities mapped one-to-one to markets | yes |
| Rye, oats | activities | **no** — their output reaches no market; price signal fixed this turn |
| Other crops (`OCRO`, `OIND`, `NURS`, `FLOW`, `TAGR`, `TOBA`, `COTT`, `OFIB`) | activities | no — exogenous prices |
| Fodder (`GRAS`, `MAIF`, `OFOD`) | activities and feed items | no market (one `OFOD_M` market row); non-tradable in CAPRI too, but CAPRI prices them through the feed balance |
| Milk → butter, skimmed milk, cheese, whey | `MILK` split by fixed FAO ratios | yes, as markets — but no processing margin or fat/protein balance |
| Beef, pork, poultry, eggs, sheep and goat meat | animal outputs summed into markets | yes — prices did not reach farms until this turn |
| Sugar | sugar beet × fixed extraction rate (0.135) | yes |
| Oils (rapeseed, sunflower, soybean) | `PROCESSING_OUTPUTS`; one `FATS` market row | **no** separate oil markets |
| Meals (soybean, rapeseed, sunflower) | `PROCESSING_OUTPUTS`, feed items | **no** — price proxied (0.89 × soybean price) |
| Mineral fertiliser N | derived from crop need minus manure | no price formation (fixed unit cost) |
| Manure | regional supply, traded at fixed base shares | no — trade is not price-driven (CAPRI's is endogenous) |
| Land | regional land market with rents | regional, yes |
| Feed energy and protein | requirement table per head | no feed balance in the market |
| Biofuels | separate module | post-solve only |

## Simplification register

Project rule: **no fixed coefficients, proxy prices or post-solve modules unless
CAPRI does the same.** Every current exception, against what CAPRI does:

| Item | This model | CAPRI | Status |
|---|---|---|---|
| Protein-feed price | cake price index (rapeseed, sunflower, soybean cakes), weighted by CAPRI's EU feed use | oilseed-cake markets | *done* |
| Feed-cereal price mix | **fixed** weights (CAPRI 2030 feed use per cereal) | feed mix optimised per region | **replace** — endogenous feed mix (needs CAPRI's `p_ElasFeed`) |
| Feed demand, non-EU | feed part responds to feed prices with CAPRI's `p_ElasFeed` (own and cross) | `p_ElasFeed` | *done* |
| Feed demand, EU | follows herds; fixed ration per head, **no price response** | ration chosen in the supply models (`v_feedInpCoeff`) | **replace** — designed in `docs/FEED_RATION.md` |
| Energy-rich feed price | unchanged (no market) | priced through its markets | **replace** with by-product markets |
| Manure trade | **fixed** base export shares | endogenous, with a transport cost | **replace** |
| Milk products | **fixed** FAO split of milk | dairy processing with fat/protein balance | **replace** |
| Sugar | **fixed** extraction rate 0.135 | fixed processing coefficient | *as CAPRI* |
| Olives, other oilseeds | raw products traded as markets | CAPRI trades olive oil, table olives and other oils | **replace** — processing chain like crushing |
| `FATS`, `OFOD_M` markets | **placeholders**: literature parameters, hard-coded world totals and prices, linked to nothing | real products in CAPRI's market | **replace** — `FATS` by the oil markets of the crushing module |
| EU oil and cake supply | crush × yields, crush driven by the margin | crush × yields | *done* |
| EU tariffs | CAPRI's 2017 total protection on EU imports (`ImportP/(Fob+TCost)−1`) | same | *done* — levels barely affect results (constant wedge) |
| World prices | now CAPRI's base world prices (`FAO_agg` `PMRK`); five codes without an unambiguous counterpart kept | `FAO_agg` `PMRK` | *done* (5 codes to resolve) |
| Mineral-fertiliser substitution | linearised around the base | allocation inside the supply model | *equivalent at the margin*; revisit if large changes |
| Abatement technologies | **post-solve** | endogenous in the supply model ("endotech") | **replace** |
| Feed module | **post-solve**, off by default | feed balance inside the supply model | **replace** with the endogenous feed mix |
| Biofuel module | **post-solve**, off by default | biofuel demand in the market | **replace** |
| Broiler birds per place | removed — feed per head now from CAPRI totals | — | *done* |
| Livestock manure and feed per head | CAPRI 2017 totals ÷ this model's herds | per-unit coefficients on CAPRI units | *equivalent* (totals match) |

## Findings, ranked by effect on results

**1. Price signal not reaching livestock — fixed.** An activity → market map
(`ACTIVITY_PRICE_SOURCE`) now carries each commodity's price change to the
activities that earn it. Base year untouched (no signal at base).

**2. Feed demand independent of herds — fixed.** Each feed cereal's EU demand
now has a feed part that follows total cereal feed (herds × feed table) at the
cereal's feed share from CAPRI's 2030 balance (wheat 43%, barley 69%, maize 81%,
other cereals 63%). Cereal price under Farm-to-Fork +13.8% → +10.2% (CAPRI +8%).
*Original finding:* In CAPRI,
feed demand is derived from animal numbers and rations; here it is a fixed part
of each commodity's demand curve. Effects: cereal and protein prices overshoot
when herds shrink; the herd–crop feedback loop (fewer animals → cheaper feed →
partial herd recovery) is missing. *Fix*: derive EU feed demand per commodity
from herd sizes × the feed table (already in the model) and make it the feed
component of market demand, calibrated so base demand is unchanged.

**3. No oilseed crushing.** *Fix*: add oil and meal markets with fixed
extraction rates (as for sugar) and a crushing margin, so oilseed prices follow
the joint value of oil and meal and meal prices are formed, not proxied.

**4. Side modules outside the loop.** The feed and biofuel modules run after the
solve and do not feed back. Once finding 2 is fixed, the feed module's balance
could become the feed-demand source. Abatement adoption could enter the supply
model as CAPRI's reference run does ("endotech").

**5. Missing market links for minor crops.** Rye and oats produce output that
reaches no market. *Fix*: aggregate them into the other-cereals market (as
CAPRI's market aggregates), calibrated at base.

**6. Fixed processing coefficients.** Milk products by fixed shares, sugar by a
fixed extraction rate. Adequate for most uses; CAPRI's dairy fat/protein
balance matters only for dairy-specific questions.

**7. Units and scales across module boundaries.** A recurring source of error:
revenues per head computed in one place from price × yield and in another from
CAPRI's market revenue; livestock "head" meaning places in one table and birds
in another. Each module boundary should carry an explicit unit, and tests should
check that the same quantity computed by two modules agrees.

## Recommended order

1. ~~**Feed demand from herds**~~ — done.
2. **Oilseed crushing** (finding 3) — completes protein-feed prices.
3. **Rye and oats into the other-cereals market** (finding 5) — small.
4. **Abatement into the supply model** (finding 4) — needed to mirror CAPRI's
   reference run with endogenous technologies.
5. A **boundary-consistency test suite** (finding 7) — now the priority for
   livestock: every per-head coefficient (feed, manure, revenue, costs) must use
   the same unit as the herd (census stock), not CAPRI's production units.

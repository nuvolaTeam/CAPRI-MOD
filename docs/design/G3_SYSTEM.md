# G3: the market as one system (stages G3.1 and G3.2; started 14 November 2026)

The plan and the decisions are in MARKET_IPOPT_DESIGN.md (sections 7, 7.2) and the project's G3 plan; the equations
in G3_MARKET_INVENTORY.md (G3.0, refreshed 13 November 2026). This file records what is built, stage by stage.

## G3.1: capture and replay

- `MarketModule._solve_captured` (capri_mod/market/market_module.py), on with `diagnostics.capture_market_dir`
  (default "", off): before each market solve the module itself (its whole state: par, sv, seen, ev, data, the
  blocks' caches; it holds no reference back to the model, and CasADi Functions pickle), the solve's arguments and the
  run's settings; after it the equilibrium and the module's warm-start state sv; in `<dir>/market_NNN.pkl`. The
  module's attributes are stored once each by content (`<dir>/blobs/<sha256>.pkl`, persistent ids in the module's
  pickle): the data and the caches do not change between solves (two solves: 17 + 100 MB as whole pickles, the second
  under 5 MB this way).
- `tools/check/replay_market.py DIR`: each solve unpickled, solved again under the run's settings, the equilibrium
  and sv compared bit for bit (exit 1 on any difference).
- Test: capri_mod/tests/test_market_capture.py (a cold and a warm solve at +10% French wheat replay bit for bit; a
  changed result is found).

## G3.2: the blocks in CAPRI's form

### G3.2a: the import prices with every policy regime (capri_mod/market/import_prices_ad.py)

`import_price_function(sc)`: CasADi Function (r[n], sB[nb], sW[ng]) -> p over the flows with beta > 0: p = a r + b, the
quotas' change of rates (bilateral trqSigmoidFunc_ / tarSpec_ / tarAdVal_; global TRQImports_ / tarSpecW_ /
tarAdValW_; the smaller of the two by ncpcm, the last quota writing a cell winning as in `_trq_rates`), the border
measures' change (entry prices EntryPriceDriver_ / tarSpecIfEntryPrice_ / prefTriggerPrice_, flexible levies
FlexLevyNotCut_ / FlexLevy_, at the pair of policy blocks' base-flow weighted CIF price). The scenario's tariff
additions are not in it yet. Equal to `BilateralCommodity.import_prices` within 2e-16 (relative) at the base and at
random prices and sigmas: the 2017 market (128 bilateral, 70 global quotas) and the 2030 market (130 bilateral, 70
global quotas, 169 entry price cells, 239 levy cells).

### G3.2b: the trade system with supply and use as unknowns (capri_mod/market/trade_system_ad.py)

`trade_system_function(sc)`: CasADi Function (r, sB, sW, S, D) -> (bal, trq, X): the supply balance of every region
(SupBalM_: S - DS - exports), the active quotas' sigmoid equations (bilateral TradeFlowsAgg_, global TRQImports_ with
the bilateral quotas' overfill), the flows. Unlike trade_ad._system (the default solve's), supply and use are inputs,
not log-linear in the own price: in the assembled system they are unknowns defined by the supply and use blocks, so
the cross-commodity terms are exact. Equal to `BilateralCommodity.residual`, `flows` and `trq_arguments` within 3e-14
on the 2030 market at random prices, sigmas, supply and use (capri_mod/tests/test_import_prices_ad.py).

At the default solve's solutions (tools/check/g3_trade_residuals.py on the 12 captured solves of a mini-EU
Farm-to-Fork, 14 November 2026): every bilateral commodity's balances hold within 1.1e-8 of the market's scale (S0 +
D0; the default solve stops at market.tol 1e-7), the active quotas' equations within 8.8e-8. The trade system in
CAPRI's form and the default solve agree at its equilibria; the residuals are the default solve's own tolerance.

### G3.2c, first block: the EU blocks' supply of the supply models' products (tools/check/g3_supply_residuals.py)

The rows CAPRI's ProdNQ_ with the measured Hessian gives the EU market regions, written as one expression of the
system's unknowns: q_x = max(0, s0_x + sum_c H_xc dP_c + sum_g H_xg (r_g - r_g^seen) + sum_m col_xm dL_m), dP the
product prices' change against those the supply models saw, r_g the young-animal prices, dL_m each member state's raw
milk price change (the default solve gets r_g and dL_m from the alternating rounds of _milk_and_yani_clear_all; in G3
they are unknowns with their own equations). At the 12 captured solves of a mini-EU Farm-to-Fork it reproduces the
equilibrium's supply on those rows (29 in EU_WEST, 28 in EU_EAST, the K83 units outside the run added) within 2e-16,
where the rows move up to 51% from the supply models' output (median 1.9%, the first scenario iteration).

The non-EU market regions' rows (CAPRI's ProdNQ_, supply_ad.nq_rows_function: product prices, the dairy block's raw
milk price ratio, FEDE, the land rents' shift: all unknowns in G3) reproduce the equilibrium's supply the same way:
42 regions, 1,330 rows, exactly (same check).

### G3.2c, the non-EU land markets and FeedBal_ together (tools/check/g3_land_fede_residuals.py)

The default solve solves the 45 land markets and the 45 feed energy balances in turn at each evaluation, with the raw
milk prices of the previous evaluation (a lag). At the captured solutions, solving both again with the current milk
prices moves the rents by at most 5.4e-7 EUR/ha and FEDE by at most 5.3e-10 (ratio): at the default solve's
equilibria the lag is spent, and the block holds as one simultaneous system.

### G3.2c, the young-animal markets and the raw milk (tools/check/g3_supply_residuals.py, the "yani" columns)

CAPRI's yaniMarket_ of each EU market region (supply_ad.yani_function: net + H_YP dP + H_YY dr + H_YM dL = ref) at the
captured solutions, with the young-animal prices the market cleared and the member states' final milk prices. The
default solve clears the young-animal markets and the member states' raw milk in alternating rounds
(`_milk_and_yani_clear_all`): each round clears the young animals at the previous round's milk prices, then solves the
dairy blocks with the milk supply at the new young-animal prices; it stops when the milk prices change by less than
1e-10 or after 4 rounds. The raw milk balances therefore hold at the final prices by construction (the last dairy solve
uses the last young-animal prices), and the young-animal markets hold up to the last round's milk price change:
at the 12 captured solves of the mini-EU Farm-to-Fork the young-animal markets are cleared in the last 7 (no
young-animal market to check in the first 5: no young-animal state or Hessian block there), and their largest residual,
relative to the good's net supply, falls from 8.0e-7 (EU_EAST calves, the first of them) to 1.7e-9 (EU_EAST lambs, the
last) as the milk prices' change between rounds shrinks; EU_WEST from 4.4e-8 to 5.0e-12.
In G3 both are equations of one system and hold together; in the default solve the 4-round cap could be lifted at
little cost (each round is one linear solve per region and one dairy solve), which would bring it closer to CAPRI's
joint solution. Not changed: it moves results, so it waits for a validation pair.

### G3.2c, the rows the market's own blocks set: crushing, dairy products, biofuels, feed by-products

Each is an explicit function of the evaluation's current prices, with no lag: the crushing (ProcO_, procYield_) at
ev.crush_prices_now, set by the evaluation before the supply response; the dairy blocks at ev.bilat_ratio_now, the
evaluation's own price ratios (the docstring of `_dairy_eu_prices` said "lagged within an outer iteration", which no
longer held with the bilateral market; corrected); the biofuel blocks inside the demand response; the feed by-products
(MaprFeed_) from that same demand response's food and biofuel ratios (`_apply_feed_byproduct_supply`, after the
demand). In the assembled system they enter as defined quantities of the prices: no residual to check beyond their
own CasADi functions (G2b-G2g, each tested against the code it replaced).

Summary of the default solve's fixed points at its equilibria: the land and FEDE milk price lag is spent (5.4e-7
EUR/ha, 5.3e-10); the young-animal markets carry the 4-round cap's residual above; everything else holds within the
solve's tolerance or exactly.

### Next: the rest of the supply side (G3.2c), as MarketModule.supply_response composes it today

Per row of the market's supply (region x commodity), the block that defines it, in supply_response's order (each a
CasADi function already, G2b-G2g, called on numbers today; G3 calls them on the system's unknowns):

| Rows | Today | Unknowns it needs |
|---|---|---|
| EU blocks, the supply models' products | ProdNQ_ with the measured Hessian, `supply_ad.hess_rows_function` (s0 + H dP + extra), dP the price change against the prices the supply models saw (`_nq_price_change`), rows with s0 > 1e-6 | the EU blocks' price ratios; the young-animal prices (extra, `_yani_clear`) |
| EU blocks, other oils and fish (EU_MARKET_SUPPLY) | `_eu_market_supply_nq` (CAPRI's ProdNQ_ for the EU) | the EU price ratios |
| Norway, its supply models' products | its own measured Hessian, with its raw milk inside its dairy block (`_sup_milk_terms`) | Norway's prices, its dairy block's unknowns |
| other non-EU regions | ProdNQ_ (`supply_ad.nq_rows_function`): the product prices, the raw milk price (the region's dairy block), FEDE, the land rents' shift | prices, dairy u, FEDE, rents |
| oils and cakes | crushing (`processing_ad.crush_function`: ProcO_, procYield_) | the seeds' Armington prices, oil and cake producer prices |
| dairy products (EU, non-EU) | the dairy blocks (`dairy_ad.dairy_block_function`: DairyNQ_, ProcMargM_, FatsProtBal_), raw milk delivered | the blocks' u (3 per block), the raw milk price |
| raw milk (EU member states) | `_milk_and_yani_clear_all`: the member states' milk with the young-animal markets, up to 4 rounds | the member states' milk prices, the young-animal prices |
| biofuels, DDGS | `biofuel_ad` (feed_group, supply, demand, proc) | the feedstocks' prices, the biofuels' prices |
| feed by-products | MaprFeed_ (`_apply_feed_byproduct_supply`) | processing quantities |

The order of work: (1) the EU blocks' Hessian rows and the non-EU ProdNQ_ rows (most rows, linear in the unknowns);
(2) the land and FEDE block (land_residual_function, fedebal_function) as unknowns; (3) the dairy blocks and raw
milk; (4) the young-animal markets (yani_function); (5) crushing, biofuels, by-products. Each step checked at a
captured solution (G3.1): the block's rows equal the default solve's supply there. Done for (1)-(5) on 14 November
2026 (the sections above).

### Then

- G3.2d: the use side (GL demand, feed, processing, biofuels' own use) the same way.
- G3.2e: the assembled system: squareness, structural rank, the Dulmage–Mendelsohn decomposition; G3.3 IPOPT on it.

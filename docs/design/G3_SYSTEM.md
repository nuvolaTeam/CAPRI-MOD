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

### G3.2d, first check: the equilibrium as a fixed point of one evaluation (tools/check/g3_fixed_point.py)

Before writing the use side as expressions: does any block, supply or use, still read state the previous evaluation
left at the default solve's equilibria? Each capture replayed, the whole model response (`_bilateral_eval`) evaluated
twice more at the solve's final r. At three captures of the mini-EU Farm-to-Fork (market_002, a baseline solve;
market_005, the first scenario iteration's; market_011, the last): two fresh evaluations differ by at most 5.8e-11
in supply and 4.7e-11 in use (relative, scale max(|q|, 1 kt); the inner solvers' tolerances: the land / FEDE rounds
stop at 1e-10, the non-EU dairy blocks start from the last solution); a fresh evaluation differs from the solve's own
supply and use by at most 3.0e-10 and 2.4e-10; its balances hold within 3.8e-9 of the market's scale (market.tol
1e-7). So every lag is spent at the equilibrium, and the use side (GL demand, feed, processing, biofuels, raw milk
delivered) is a function of the evaluation's prices, FEDE and the supply side's quantities of the same evaluation. A
repeated evaluation cannot show the young-animal rounds' cap: each evaluation repeats the same 4 rounds from the same
start; its residual is measured directly above.

### G3.2d: the use side as one CasADi function (capri_mod/market/use_ad.py)

`use_function(mm)`: D = use(PR, RB, fede, milk, biofX, ddgs), the whole of `demand_response` on symbols: the GL
demand (gl_block_function), FeedNQ_ with FEDE, p_ElasFeed, the EU's and Norway's feed bulks with their response
within the market (feedBlk_, at the producer ratios RB), the FMIL block, the crushing (the seed at its Armington
ratio, oil and cake at their producer ratios), ProcNQ_ with ProcFudge_, the biofuel feedstock CES at the groups'
output and DDGS price, raw milk delivered (the supply side's quantities), the biofuels' own use and non-fuel
processing; the same order, floors and clip as demand_response. The market solve's calibration state (seen prices,
bulk indices, FMIL index, demand calibration) enters as constants. Built in about 1.7 s.

Checks: equal to demand_response within 1e-12 (relative) at the base and at two random draws of prices, FEDE, raw
milk and biofuel output on a solved baseline's market (capri_mod/tests/test_use_ad.py, slow); at three captured solves
of the mini-EU Farm-to-Fork, equal to the evaluation's use on all 2,610 cells within 3.8e-16
(tools/check/g3_use_residuals.py).

### G3.2c/e: the supply side as one CasADi function with its blocks' equations (capri_mod/market/supply_system_ad.py)

`supply_system(mm, exogenous_supply)`: (S, res_yani, res_dairy_eu, res_dairy_w, biofX) = supply(PA, RR, ry, uE, uW,
fede, dr), the whole of `supply_response` with the blocks it solves inside each evaluation turned into unknowns and
equations: the young-animal prices ry (yaniMarket_ of the EU market regions and Norway), each member state's dairy
block (3 unknowns: fat, protein, raw milk price; FatsProtBal_ and DairyNQ_ = ProdNQ_ MILK with the milk supply's
response to its price, the products' prices and the young-animal prices), the other regions' dairy blocks (3 each,
raw milk from CAPRI's supply function with its cross-price, FEDE and rent terms); FEDE and the rents enter as unknowns
(their equations, FeedBal_ and the land markets, are fedebal_function and land_residual_function: next). Composed: the
anticipation of the supply models' output, the EU's EU_MARKET_SUPPLY ProdNQ_, the measured Hessian's rows with the
young-animal and raw milk terms, Norway's rows, raw milk and dairy block, the K83 units outside a run, crushing, the
non-EU ProdNQ_ rows, raw milk without a block, the biofuels and DDGS. The EU's residual feeds (MaprFeed_) are left to
the assembly (they follow the use side). Built in about 1.2 s.

Two departures from the default solve, both toward CAPRI's one simultaneous system: Norway's rows respond to its dairy
block's current milk price (the default solve: the previous evaluation's, DEP-29); the young-animal markets are
equations rather than 4 alternating rounds. One default-solve form kept for now: Norway's raw milk row takes the
young-animal prices of a clearing without the milk price change (supply_response's two clearings); CAPRI has one set
of young-animal prices, so G3 should use the cleared ones there too (a decision for G3.3, it moves Norway's milk).

Checks: at the default solve's block solutions the supply equals `supply_response` within 1e-12 and the dairy
blocks' residuals are below 1e-8, at a solved market of CAPRI's base supply rows and at two random price draws around it
(capri_mod/tests/test_supply_system_ad.py, slow; no young animals or Norway there). At three captured solves of the
mini-EU Farm-to-Fork (Norway's supply models, the young-animal markets, the member states' milk response and the K83
units all present): the supply equals the evaluation's on all 2,610 cells within 6.2e-16; the dairy blocks' residuals
within 2.8e-16 of their base raw milk (78 EU, 129 other equations); the young-animal markets' residuals are the
4-round cap's (8.0e-7 at market_005, 1.7e-9 at market_011; none at market_002) (tools/check/g3_supply_system.py).

### G3.2e: the assembled system, its size and its structure (capri_mod/market/market_system_ad.py)

`market_system(mm, exogenous_supply)`: F(x) = 0 over x = (the producer price ratios of the 57 bilateral commodities in
the 45 regions, the active quotas' sigmas, the young-animal prices, the dairy blocks' unknowns, FEDE, the free rents),
F = (the supply balances SupBalM_, the quotas' sigmoids, yaniMarket_, the dairy blocks, FeedBal_, the land markets),
supply from supply_system_ad, use from use_ad, the Armington ratios from each commodity's trade block (trade_system_ad,
now with the ratios as an output), the EU's residual feeds from the use. Raw milk is a pooled commodity whose world
balance is zero identically (supply and use are the same quantity in every region): its ratio is held, its balance
returned apart (8.0e-11 kt). Built in about 7 s.

At the 12-solve mini-EU Farm-to-Fork's captures (tools/check/g3_market_system.py), market_011 / market_005 /
market_002: 3,166 / 3,166 / 3,151 unknowns and as many equations; largest residuals relative to their scales:
balances 2.1e-9 / 3.8e-9 / 9.0e-10, quotas 7.8e-8 / 8.8e-8 / 7.7e-8, young animals 1.7e-9 / 8.0e-7 / none, dairy
blocks below 3e-16, FeedBal_ below 9.1e-11, land below 1.4e-10; the system's supply and use equal the evaluation's
within 5.9e-13. On the market solved at CAPRI's base supply rows (capri_mod/tests/test_supply_system_ad.py, slow): the
balances within 1.3e-7, above market.tol (1e-7): the default solve meets its test at its own last evaluation (9.0e-8),
whose non-EU land and FEDE blocks use the previous evaluation's raw milk prices; evaluated again at the same prices
the residual is 1.3e-7, then 1.4e-7 (the lag being worked off). So the default solve's convergence test does not
control that lag; in G3 it is gone.

Structure (CasADi's Jacobian pattern, sprank and btf, the Dulmage–Mendelsohn decomposition) at market_011 (market_005
the same; market_002, without the young-animal markets, 15 unknowns and equations fewer, the same pattern otherwise):
3,176,660 non-zeros (32% of the matrix: each region's use depends on all its Armington prices through the
GL demand, and each Armington price on the commodity's prices in every region, so substituting them out fills the
Jacobian); structural rank 2,624 of 3,166. The deficiency is all in the balances: 542 region-commodity balances are
empty (no supply, use or trade: no equation), and 534 of their 542 price ratios appear in no equation either. The
other 8 enter elsewhere although their own balance is empty: Norway's CORN, FENI and SOYA (its supply models' rows
have terms in them), the cakes RAPC in RSA, SOYC in BEL and BGD, SUNC in JAP and THAI (the crushing margin and its
ProdNQ_ terms). Without the 542 empty balances and with those 542 prices fixed (as the default solve leaves them, and
as CAPRI fixes the prices of a market without production or use), the system is square, 2,624 x 2,624, with full
structural rank (the same holds on the base market: test_supply_system_ad.py), and its fine decomposition is one
strongly connected block of 2,621 equations and three of one: the
market has to be solved as one block.

For G3.3 (IPOPT on it): the substituted form is dense (32%); CAPRI keeps the Armington prices, supply and use as
variables of their own with their defining equations, which keeps the Jacobian sparse. Our recommendation is to do the
same (the blocks are already functions of those quantities) and to let IPOPT see the intermediate unknowns; to check
before building: the size of that sparse system and its factorisation time against the dense 2,624 one.

### G3.3, first trial: Newton's method on the assembled system (tools/check/g3_newton_trial.py)

From the state each captured solve started from (the previous solve's equilibrium and blocks), a damped Newton method
on the square system (the empty balances out), with the Jacobian by forward differences (about 11 s each: CasADi's
symbolic Jacobian of the substituted, 32% dense system ran out of memory beside a full run) and a backtracking line
search:

- market_011 (the last solve of the run, the supply models' output close to the previous): 2 steps, the residual
  2.0e-2 -> 1.3e-7 -> 2.5e-12, quadratic; the equilibrium equals the default solve's within 3.7e-9 on the prices
  (sigmas 1.2e-7, young animals 1.9e-9, FEDE 7.9e-10; the dairy unknowns and the rents within 2.2e-6 and 1.6e-5
  EUR/ha). The default solve took 12.6 s.
- market_005 (the first scenario solve: the supply rows move by up to 51%): with the line search on the largest
  scaled residual, 30 steps (most of them shortened) to 5.7e-8, the same equilibrium within 1.4e-8 on the prices; with
  the line search on the 2-norm it stalls at 0.46 on one quota's sigmoid equation (trq[22]). The default solve took
  43 s. The steep quota sigmoids (CAPRI's trqSigmoidFunc_, slope TRQ_SLOPE) are nearly steps: far from the solution
  Newton's linearisation of a saturated sigmoid is flat. The default solve solves them inside each commodity's trade
  system.

So the assembled system has the default solve's equilibrium as its solution, and Newton converges to it fast near it.
For G3.3: (1) the lifted sparse form (above), which also gives the exact Jacobian cheaply; (2) a globalisation that
copes with the quotas: IPOPT's filter line search on the system as constraints, or a continuation on the quotas'
slope; (3) the bounds. CAPRI's own precedent for the quotas (read 14 November 2026): the slope p_trqSigmoidSlope is
200 in the market model (arm/market_model.gms l. 336-339: the sigmoid "jumps from zero to one within the range of +-3%
of the TRQ"; "a steeper slope would be more realistic, but potentially produces more infeasibilities"); its quota
calibration starts at 10 and raises it by 10 per solve up to 200 "to maintain feasibility" (arm/trim_trqs.gms
l. 734-737, 821-823), and after an infeasible simulation solve widen_bounds.gms (l. 613-615) sets the slope of the
quotas with non-zero marginals to between 100 and 300. So a continuation on the slope is CAPRI's own way; CAPRI's
simulation solve itself is CONOPT from the previous solution.

### G3.3, second trial: the lifted form (market_system(..., lifted=True); tools/check/g3_ipopt_trial.py)

CAPRI's form: the bilateral commodities' Armington ratios, the supply and the use are unknowns of their own with their
defining equations (PAdef, Sdef, Ddef), as v_arm1Price, v_prodQuant and v_arm1Quant in m_globMarket: 10,951 unknowns
and equations at market_011 (3,166 + 2,565 + 2,610 + 2,610), 10,409 once the empty balances are out and their prices
held. At the default solve's equilibrium its definitions hold exactly and its other equations equal the substituted
form's (test_supply_system_ad.py).

- Newton's method with the exact sparse Jacobian (CasADi's rootfinder, CSparse LU), from the state market_011 started
  from: 3 steps, 2.0e-2 -> 1.3e-7 -> 7.3e-14, the same equilibrium as the default solve (prices within 3.7e-9; the
  Armington ratios, supply and use within 4.3e-9). 134 s, with a full run on the same two cores; the time is to be
  measured alone and with MUMPS (CSparse's LU is not built for this size).
- The lifted Jacobian has 290,893 non-zeros (0.27% of the matrix; the substituted form's: 32%).
- IPOPT (MUMPS, zero objective, the system as equality constraints, L-BFGS Hessian, tolerance 1e-10, alone on the
  machine): with MUMPS's defaults it stops at its first iteration (MUMPS cannot allocate 648 MB for the factor, whatever
  the process's memory limit); with mumps_mem_percent = 100 and the METIS ordering (mumps_pivot_order = 5) it solves:
  - market_011: 2 iterations (2.0e-2 -> 1.3e-7 -> 7.3e-14), 20.2 s in IPOPT (the default solve 13.4 s), the default
    solve's equilibrium within 3.7e-9 on the prices, 4.3e-9 on the Armington ratios, supply and use;
  - market_005 (the first scenario solve, start residual 3.2): 25 iterations, 127 s in IPOPT (the default solve 42 s),
    the filter line search through the quotas' sigmoids without a continuation; the default solve's equilibrium within
    1.4e-8 on the prices (sigmas 9.5e-7, young animals 5.4e-7, dairy unknowns 8.3e-6, rents 5.0e-5 EUR/ha).
  So IPOPT on CAPRI's form solves the market to the default solve's equilibrium, the hard case included, in 3 to 5
  times its time on this machine. Where the time goes (market_011): the constraints 0.02 s and their Jacobian 0.13 s
  in all; the rest is MUMPS's factorisation of the KKT matrix (about 7 s each). MUMPS's orderings: METIS 20.2 s, PORD
  19.5 s, AMD 84 s, AMF 87 s, QAMD 75 s. CasADi's set-up of the solver (its derivative functions) takes another 24 s
  per system built. So the linear algebra is the cost: an HSL solver (MA57, MA97) or SPRAL, the factorisation's
  fill-in (the regions' dense demand blocks), and building the system once per run with its constants as parameters.
- At every captured solve of the mini-EU Farm-to-Fork (G3-R on the replayed states, the plan's check for G3.3), from
  the state the solve started from:

  | Solve | Start residual | IPOPT iterations | IPOPT s | Default solve s | Prices: largest relative difference |
  |---|---|---|---|---|---|
  | market_001 | 2.7e-3 | 3 | 25.2 | 16.2 | 1.7e-9 |
  | market_002 | 1.2e-2 | 5 | 36.6 | 16.5 | 3.4e-9 |
  | market_003 | 2.7e-3 | 3 | 25.5 | 14.2 | 2.8e-9 |
  | market_004 | 5.1e-4 | 2 | 20.2 | 11.3 | 3.8e-9 |
  | market_005 | 3.2 | 25 | 118.8 | 42.6 | 1.4e-8 |
  | market_006 | 3.2 | 5 | 37.9 | 23.6 | 2.3e-8 |
  | market_007 | 1.5e-1 | 3 | 24.5 | 18.1 | 3.3e-9 |
  | market_008 | 6.9e-2 | 2 | 16.0 | 14.5 | 1.6e-9 |
  | market_009 | 1.4e-1 | 2 | 14.7 | 13.0 | 2.4e-9 |
  | market_010 | 2.4e-2 | 2 | 15.5 | 12.9 | 3.5e-9 |
  | market_011 | 2.0e-2 | 2 | 19.8 | 12.1 | 3.7e-9 |

  Every solve ends below 6e-12 (scaled) at the default solve's equilibrium. market_000, the run's first solve, has no
  system before it: the market is calibrated inside that solve (`_bilateral_calibrate`), so G3 starts from a
  calibrated module.

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

- G3.3: IPOPT on the assembled system (the intermediate quantities as unknowns, as above), started from the default
  solve's equilibrium first (it must stay there), then from the base prices; the bounds of CAPRI's table
  (G3_MARKET_INVENTORY.md) and the decisions recorded above (Norway's raw milk row, the young-animal prices' bounds,
  the member states' raw milk price floor).

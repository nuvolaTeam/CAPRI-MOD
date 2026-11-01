# Market solve with IPOPT and exact Jacobians (step G): design note

Written on 30 October 2026; the decisions of section 7 were taken the same day. Nothing here is built yet, except the trade
systems' CasADi expressions (`capri_mod/market/trade_ad.py`, step G1).

## 1. What CAPRI does

- **One simultaneous system.** CAPRI solves its market model as a single system: `SOLVE m_globMarket USING DNLP
  Minimizing v_dummy` (arm/simu_market.gms l. 107; the same statement in simu_prestep.gms l. 366; the one in
  treat_enormous_infes.gms l. 26 is inside $ontext ... $offtext, not executed: corrected 1 November 2026).
  Where the solve is infeasible CAPRI widens bounds and solves again, at most twice more (simu_market.gms l. 95-145),
  and in the last iteration accepts a sum of infeasibilities up to 0.1 (l. 289-300).
- **The objective is a dummy.** The model is square, so CONOPT is used as an equation solver started from the
  previous solution. The DNLP class is there because of non-smooth terms (e.g. min/max in the tariff and stock rules).
- **The equations** (arm/market_model.gms l. 600-720, declarations) cover:
  - supply: the land and yield block (Yield_, LandSupplyMNL_, LndSupplyEqualsDemand_, rentFromProdpriceLand_);
  - young animals: yaniMarket_ and rmsYaniMarket_;
  - feed: FeedNQ_, FeedBal_, feedBlk_, feedBlkPrice_, FeedShareEqu_;
  - dairy: DairyNQ_;
  - processing margins: ProcMargM_, ProcMargO_, ProcFudge_;
  - tariffs and tariff-rate quotas: tarSpec_, tarAdval_, trqSigmoidFunc_, TRQImports_, FlexLevy_ and the entry price
    rules;
  - intervention stocks: buyingToIntervStock_, releaseFromIntervStock_, intervStockLevel_ and the rest of that group;
  - subsidised exports;
  - biofuels: Biof_, ProdBiof_, BiofPriceRel_, BiofFeedCost_, biofDem_ and the rest of that group;
  - the Armington system: ArmBal1_, importShares_, domSalesShares_, arm2QuantShares_ (ArmFit1_ and ArmFit2_ are
    marked "not used in simulation model", l. 2685-2700; listed here until 1 November 2026 by mistake);
  - the balances: SupBalM_, expQuant_. mrkBal_, wldMarket_ and nTrd_ belong to the net-trade model m_netTrade
    (l. 4218-4239), not to m_globMarket (listed here until 1 November 2026 by mistake; the independent review, Q4).

## 2. What capri-mod does now

- **Default solve.** `BilateralSolveMixin._solve_bilateral` is a successive linearisation:
  - each step evaluates the full model response, `_bilateral_eval`: supply_response, demand_response, the feed
    by-products and each commodity's trade residual;
  - each commodity's trade system is then solved exactly, with supply and use log-linear around that point;
  - the links across commodities and blocks enter only between steps.
- **Newton–Krylov option** (`market.solver = "newton_krylov"`, market_nk.py). It solves R(z) = 0 at once:
  - z = log r, the producer price ratios over each bilateral commodity's supplying regions, plus one ratio per pooled
    commodity;
  - the Jacobian–vector products are finite differences of the full model response;
  - the preconditioner is the trade systems' exact Jacobian (trade_ad.py).
- **The NLP solve the project lead chose (step G).** IPOPT with exact derivatives of every block, so that both the
  finite differences and the successive linearisation are gone.

## 3. Proposed formulation

**G3 on standby (the project lead, 1 November 2026) pending the independent review of step G,
docs/design/G_REVIEW_2026-11-01.md: the bound policy, the objective, the acceptance tests and the inventory's
corrections are to be decided before G3 is built.**

**Changed by the project lead on 1 November 2026: G3 in CAPRI's own form (section 3.1).** The text below is the
reduced form first proposed; 3.1 replaces it for G3.

### 3.1 CAPRI's form: every quantity a variable (the project lead's choice, 1 November 2026)

- **What it is.** As m_globMarket: a square system in which each endogenous quantity is a variable with its own
  defining equation (CAPRI documentation, 2022 PDF section 5.4: "the same number of endogenous variables as
  equations"; about 70,000 of each there). Per commodity: the bilateral flows, both Armington aggregates and their
  price indices, the import, producer and consumer prices, and per behavioural region supply, human consumption,
  feed, processing and biofuel use, with the market clearing; the TRQ, dairy, feed-energy, young-animal and raw-milk
  equations as they are in CAPRI's model.
- **Against the reduced form** (the first proposal, below): the same equilibrium (substituting a defining equation
  into the others changes no solution), but the problem is larger and sparser, each equation simple and close to
  CAPRI's GAMS line for line, every quantity can carry CAPRI's bounds and is reported as solved. The reduced form has
  about 1,281 price unknowns with dense rows (flows folded into the clearing); this form has tens of thousands of
  unknowns with a few entries per row.
- **What carries over.** The blocks built so far (G2a trade with the TRQs, G2c human consumption, G2e processing) are
  CasADi expressions of their arguments; in CAPRI's form each becomes the right-hand side of its variable's defining
  equation (q - f(prices) = 0), so they are reused, not rewritten. The objective (½‖z − z₀‖² over the prices) and the
  supply side outside the NLP (market supply functions and the measured Hessian) stay as decided.
- **Linear solver.** A large sparse KKT system: MUMPS and SPRAL in OpenMP (section 9.1) to be compared on it.
- **Next.** The variable and equation list per block against m_globMarket (arm/market_model.gms), with CAPRI's bounds,
  before G3 is assembled; the remaining blocks (G2b, G2d, G2f, G2g) written as defining equations from the start.
  First inventory done 1 November 2026: docs/design/G3_MARKET_INVENTORY.md (123 equations of m_globMarket with their
  status in capri-mod; not ported and on in CAPRI's default runs: the market's land and yield block, the land-use-change
  estimation, and the intervention, subsidised-export, flexible-levy and entry-price rules where CAPRI's data have them).
  CAPRI's bounds per variable are the next part of it.

### 3.0 The reduced form (first proposal, 30 October 2026)

- **Unknowns.** x = (z, w):
  - z: the price ratios above;
  - w: the unknowns that the market blocks now solve inside the response, lifted into the NLP (section 4, the "inner
    solves" column). This is what CAPRI does: DairyNQ_, ProcMargO_ or trqSigmoidFunc_ are equations of m_globMarket,
    not nested solves.
- **Constraints.** R(z, w) = 0 (the clearing residuals, scaled as now by S0 + D0) and G(z, w) = 0 (the lifted blocks'
  equations).
- **Objective.** ½‖z − z₀‖², with z₀ the starting point (the previous outer iteration's prices). This is the
  project lead's choice.
  - **Departure.** CAPRI's objective is a dummy. Where the solution is isolated, the objective does not change it.
  - **What it changes.** It only decides which root IPOPT reaches when there are several: the one nearest the start.
    Starting CONOPT from the previous solution has a similar effect in CAPRI, but that is my reading, not something
    CAPRI's documentation states.
  - **Alternative.** A zero objective, as CAPRI's, is also possible with IPOPT; it then works as a feasibility solver.
- **Derivatives.**
  - Each block is written as a CasADi expression.
  - IPOPT gets the exact Jacobian of the constraints and the exact Hessian of the Lagrangian. The Hessian could be a
    limited-memory approximation in a first stage.
  - The supply models stay outside: as in CAPRI, the market sees them through the market supply functions and the
    Hessian measured on them. They are not re-solved inside the market NLP.
- **Non-smooth terms.** The step clip, the TRQ offsets now solved as an outer fixed point (`trq_solve`) and any
  max/min in the blocks become smooth constraints. Where CAPRI has a sigmoid (trqSigmoidFunc_), we take CAPRI's.
  Where it has none, the departure is registered. The max/min terms of the market code (the independent review, Q3
  and Q6.7; DEP-38, DEP-39): demand_ad.py (consumer price at least 0.05 p0, demand at least 0 in the sums);
  trade_ad.py l. 52 (import price at least 1e-9) and l. 163 (the TRQ sigmoid's argument clipped); demand.py l. 298,
  393, 482 (feed factor, processing, use at least 0); supply.py l. 742, 826 (market supply max(q0 + dq, 0); the
  review cites l. 741, 825) and the further floors of supply.py l. 167-415 (price ratios at least 1e-6 or 0.2, supply at
  least 0; found when checking the review's lines). Their treatment in G3 follows the bound policy still to be decided
  (review Q2).

## 4. Inventory of the market blocks (30 October 2026)

| Block | capri-mod (capri_mod/market/) | CAPRI equations | CasADi | Inner solves to lift |
|---|---|---|---|---|
| Bilateral trade, Armington nests | bilateral.py (`import_prices`, `prices`, `flows`, `residual`), bilateral_solve.py | impPrice_, ArmBal1_, importShares_, domSalesShares_, arm2QuantShares_, SupBalM_ | **yes**, trade_ad.py (supply and use as local log-linear terms; TRQ offsets as parameters) | the TRQ offsets (`trq_solve`, an outer fixed point) |
| Tariff-rate quotas | bilateral.py `trq_solve`, `_sig` | trqSigmoidFunc_, TRQImports_, tarSpec_, tarAdval_ | no | the fill, as above |
| Pooled commodities | bilateral_solve.py (world balance) | none in m_globMarket (wldMarket_, nTrd_ are m_netTrade's; a departure, DEP-31) | trivial | none |
| Market supply (EU from the supply models; non-EU supply functions) | supply.py `supply_response`, `_eu_market_supply_nq`, `_noneu_market_supply_nq`, `_region_supply_elas` | the supply part of SupBalM_; the land block | no | none in the EU part; the milk and young-animal clearing (`_milk_and_yani_clear_all`, `_yani_clear`) |
| Young animals, raw milk | supply.py `_milk_terms`, `_sup_milk_terms`, `_yani_clear` | yaniMarket_, rmsYaniMarket_ | no | the clearing loop |
| Dairy blocks | dairy.py `_dairy_solve` (Newton, l. 247-320), `_dairy_solve_ms*`, `dairy_block` | DairyNQ_ | no | the dairy Newton |
| Processing (non-quadratic), crushing | processing.py `_crush_state` (CET yields), `crush_quantities`, `_proc_nq_params` | ProcMargM_, ProcMargO_, ProcFudge_ | no | none found (closed forms) |
| Human consumption | demand.py `_gl_eval`, `gl_food_ratio`, `demand_response` | the demand system (generalised Leontief) | no | none (`_gl_refit` is calibration) |
| Feed | feed.py `noneu_fede`, `noneu_feed_change`, `eu_feed_use`, `feed_bulk_*`, `_apply_feed_byproduct_supply` | FeedNQ_, FeedBal_, feedBlk_, feedBlkPrice_ | no | the feed energy price (FeedBal_) is evaluated in sequence with the dairy price of the previous evaluation (`_bilateral_eval`, l. 265-272): a lag to lift |
| Biofuels | biofuel.py `biofuel_state`, `_biofuel_feed_group`, `biofuel_feedstock_use` | Biof_, ProdBiof_, BiofPriceRel_, BiofFeedCost_, biofDem_ | no | to check (`biofuel_state`) |
| Welfare | welfare.py | reporting only | not needed | none |

Sizes: supply.py 752 lines, dairy.py 506, demand.py 481, feed.py 424, biofuel.py 321, processing.py 311,
bilateral.py 192. The blocks to express in CasADi total about 2,800 lines of NumPy and pandas.

## 5. The question of two implementations

- **The problem.** Writing each block a second time in CasADi (as trade_ad.py did for the trade systems) keeps the
  NumPy code as the default and adds a copy, held equal by tests at random points. Every later change to a block
  must then be made twice.
- **My proposal: one implementation.** Each block is written once as a CasADi function. The default solve evaluates
  that compiled function numerically instead of the NumPy code.
- **Cost.** That rewrite of the market blocks is a behaviour-neutral move, but a large one. It would be checked like
  the refactor stages: the reference run reproduced to the last digit, or within floating-point reordering, which
  must then be stated.
- **Decision.** It is the project lead's (section 7).

## 6. Stages and checks

Each stage must pass two checks:
- the CasADi residual equals the NumPy residual at random points (relative 1e-10);
- the Jacobian equals finite differences.

1. **G2a.** The TRQ sigmoid in trade_ad.py, so the quotas leave the outer loop. **Built 30 October 2026:**
   trade_trq_function.
   - The quota offsets are unknowns, with CAPRI's sigmoid as their equations. These are trq_solve's fixed point with
     the flows' full response.
   - The existing trade_function shares the same expressions (_system).
   - capri_mod/tests/test_trade_ad.py checks the residual and the Jacobian against the numeric system.
   - No solve uses it yet: the NLP of G3 will.
2. **G2b.** Market supply and pooled commodities: the non-EU supply functions, and the EU's anticipated response
   with the measured Hessian.
3. **G2c.** Human consumption, the generalised Leontief system. **Built 31 October 2026** (taken before G2b by the
   project lead's decision of that day: G2b's market supply rests on the coupling code that refactor stage 4 is to
   restructure; G2c and G2e are market code no refactor stage touches):
   capri_mod/market/demand_ad.py.
   - Written once: DemandMixin._gl_eval and gl_food_ratio evaluate the CasADi function (gl_entry_function per
     behavioural region; gl_block_function for all of them, PR to the human consumption per cell), the NumPy code
     removed (section 7's one implementation).
   - capri_mod/tests/test_demand_ad.py: equal to the former NumPy equations at random points (worst relative
     difference 1.5e-15: CasADi's matrix-vector products sum in another order; half the values bit-identical) and
     the Jacobian equal to finite differences.
   - The model's floors (consumer price at least 5% of its calibration value, demand at least 0 in the sums) are
     fmax terms: kinks for G3, to be registered or removed there.
   - Time: 5.2 ms per gl_food_ratio call against 3.4 ms in NumPy (the SX function expanded; the MX graph took 7.6).
   - Mini-EU check (1 November 2026; G2c and G2e together, against the same run at 955470d): not bit-identical, as
     expected from the rounding above. 1,369 values differ at all, 86 by more than 1e-12 relative, 11 by more than
     1e-10, 5 by more than 1e-8: the largest are near-zero ammonia option shares in IR010000 (1.08e-7 against
     1.08e-7, 2e-5 relative) and a regional dual (DK000000, 2e-10 relative), i.e. the regional solver's tolerance;
     the same iterations (6), the same relaxed caps, the EU indicators equal to their printed digits.
4. **G2d.** Feed, with the feed energy price lifted as an unknown (FeedBal_).
5. **G2e.** Processing and crushing. **Built 31 October 2026** (with G2c, same decision):
   capri_mod/market/processing_ad.py.
   - Written once: ProcessingMixin._crush_state (ProcMargO_, ProcNQ_, ProcFudge_, ProcO_, procYield_: crush_function)
     and demand_response's ProcNQ_ of the other products (proc_nq_function) evaluate the CasADi functions; the Python
     loops removed. ProcFudge_'s log(1 + exp) is written as NumPy's logaddexp evaluates it.
   - capri_mod/tests/test_processing_ad.py: equal to the former Python code at random prices (welfare detail
     included) and the Jacobians equal to finite differences.
6. **G2f.** Dairy blocks, lifted.
7. **G2g.** Biofuels; young animals and raw milk, lifted.
8. **G3.** IPOPT on the assembled NLP.
   - **Check:** the equilibrium equals the default solve's within `market.tol` at every outer iteration of the F2F
     and GD runs, and the outer loop converges in the same number of iterations or fewer.
   - **Default:** the IPOPT solve becomes the default only after that check, by the project lead's decision.

## 7. Decisions

**Decided by the project lead on 30 October 2026 ("Step G: ok"), as recommended below:**
- the objective is ½‖z − z₀‖²;
- each block is written once, in CasADi, as a separate move stage;
- the Hessian is exact;
- the stages run in the order of section 6, the TRQ first.

The options as they were put:

1. **The objective.** ½‖z − z₀‖² (chosen) or a zero objective as CAPRI's. The two give the same solution where it
   is isolated.
2. **One or two implementations of the blocks.** See section 5. I recommend one implementation (CasADi), as a
   separate move stage.
3. **The Hessian.** Exact from CasADi or limited-memory. I recommend exact: the system is small (thousands of
   unknowns) and the expressions are available.
4. **Order of the stages.** As in section 6. The TRQ comes first because it is the only outer fixed point left in
   the trade systems.

## 8. Found while making the inventory

- supply.py, demand.py, dairy.py, feed.py, biofuel.py and processing.py import `fsolve` and never call it (an import
  marked `noqa`). This is to be removed with the next behaviour-neutral change.
- The feed energy price uses the dairy blocks' raw milk price of the *previous* evaluation (`_bilateral_eval`,
  l. 265-272). In CAPRI both are equations of the same system. This lag only affects the path, not the equilibrium,
  if the loop converges; the NLP removes it.

## 9. Linear solver (30 October 2026)

- **The market NLP will use IPOPT's linear solver setting** (supply.nlp_linear_solver, register BEYOND-11).
- **SPRAL is bundled with CasADi but serial there:** CasADi 3.8.1 builds it without OpenMP.
- **An IPOPT built with an OpenMP-enabled SPRAL is an option for this NLP.** It is much larger than a regional one,
  which is where a parallel factorisation can pay off. The project lead likes it; it is to be measured on the market
  NLP once G3 exists.
- **The benchmark on the regional solves (30 October 2026)** settles their case: MUMPS stays.
  - Setup: the 885 regional solves of the mini-EU Farm-to-Fork run, each repeated with SPRAL from the same start.
  - Where both solve (869), the objectives agree within 1e-6.
  - Serial SPRAL takes 2.4 times MUMPS's time per solve (median) and 4.2 times in total IPOPT time.
  - It also fails 2 solves that MUMPS solves.
- **Building an OpenMP SPRAL here (planned for step G, the project lead's choice of 30 October 2026).** The sandbox
  has what the build needs: gfortran, OpenMP, BLAS/LAPACK, cmake and ninja; meson and METIS 5 are to be added.
  - The plan: METIS 5, then SPRAL with OpenMP, then IPOPT 3.14.19 (CasADi 3.8.1's) with SPRAL and MUMPS, then
    CasADi pointed at that library. A build script goes under tools/; the binaries stay out of the repository.
  - The speed-up can only be measured on a machine with more cores than workers.
  - The shortcut for the comparison: HSL MA86/MA97 (OpenMP) load into CasADi's IPOPT at run time, under HSL's
    licence.

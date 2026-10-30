# Market solve with IPOPT and exact Jacobians (step G): design note

Written on 30 October 2026; the decisions of section 7 were taken the same day. Nothing here is built yet, except the trade
systems' CasADi expressions (`capri_mod/market/trade_ad.py`, step G1).

## 1. What CAPRI does

- **One simultaneous system.** CAPRI solves its market model as a single system: `SOLVE m_globMarket USING DNLP
  Minimizing v_dummy` (arm/simu_market.gms l. 107; the same statement in simu_prestep.gms l. 366 and
  treat_enormous_infes.gms l. 26).
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
  - the Armington system: ArmFit1_, ArmFit2_, ArmBal1_, importShares_, domSalesShares_, arm2QuantShares_;
  - the balances: SupBalM_, mrkBal_, wldMarket_, nTrd_.

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
  Where it has none, the departure is registered.

## 4. Inventory of the market blocks (30 October 2026)

| Block | capri-mod (capri_mod/market/) | CAPRI equations | CasADi | Inner solves to lift |
|---|---|---|---|---|
| Bilateral trade, Armington nests | bilateral.py (`import_prices`, `prices`, `flows`, `residual`), bilateral_solve.py | impPrice_, ArmFit1_, ArmFit2_, ArmBal1_, importShares_, SupBalM_ | **yes**, trade_ad.py (supply and use as local log-linear terms; TRQ offsets as parameters) | the TRQ offsets (`trq_solve`, an outer fixed point) |
| Tariff-rate quotas | bilateral.py `trq_solve`, `_sig` | trqSigmoidFunc_, TRQImports_, tarSpec_, tarAdval_ | no | the fill, as above |
| Pooled commodities | bilateral_solve.py (world balance) | wldMarket_, nTrd_ | trivial | none |
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

1. **G2a.** The TRQ sigmoid in trade_ad.py, so the quotas leave the outer loop.
2. **G2b.** Market supply and pooled commodities: the non-EU supply functions, and the EU's anticipated response
   with the measured Hessian.
3. **G2c.** Human consumption, the generalised Leontief system.
4. **G2d.** Feed, with the feed energy price lifted as an unknown (FeedBal_).
5. **G2e.** Processing and crushing.
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

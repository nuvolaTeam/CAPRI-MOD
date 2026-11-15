# G3.4: CAPRI's bounds on the market, their widening and the fudge equations (plan, 14 November 2026)

**Codes used in this document.** The plan's internal codes are kept here as written; what they stand for:

- **G1-G3.4**, the market programme (MARKET_IPOPT_DESIGN.md section 6, MARKET_SYSTEM.md): G1 the trade systems' exact Jacobian in CasADi; G2 the Newton-Krylov solve of the same equations, with G2a-G2g the market's blocks written in CasADi (a the quotas' sigmoid in the trade system, b market supply ProdNQ_ and the pooled commodities, c human consumption GL, d feed FeedNQ_ and FeedBal_, e processing and crushing, f the dairy blocks, g biofuels, young animals and raw milk); G3 the whole market as one system of equations in CAPRI's form (capri_mod/market/market_system_ad.py, market_chain.py); G3.0 the refresh of MARKET_EQUATIONS_INVENTORY.md (13 November 2026); G3.1 the capture and replay of market solves; G3.2a-e the system's blocks (import prices, the trade system, the supply side, the use side, the assembled system); G3.3 the choice of solver (the trials and the solver battery); G3.4 CAPRI's bounds, their widening and the fudge equations (MARKET_BOUNDS_PLAN.md); G3-R the regression check (the system reproduces the default solve's equilibrium); G3-C each change to CAPRI's form checked against CAPRI.

What CAPRI does (arm/market_model.gms, set_start_val.gms, simu_market.gms, widen_bounds.gms), what the model does
today, and the port. Part of the market port plan (MARKET_EQUATIONS_INVENTORY.md; the project's claude/market_port_plan.md
item 1).

## 1. CAPRI

**Bounds at the start of every market solve** (arm/set_start_val.gms; factors market_model.gms l. 322-326:
P_lowLimitFactQuant 1e-5, p_uppLimitFactQuant 1e3, P_lowLimitFactPrice 0.1, p_uppLimitFactPrice 10):

- quantities: production lower max(1e-8, min(1e-6, |L| x 1e-5)), upper max(1, |L|) x 1e3 (l. 101-108; the young
  animals wider); processing lower Proc x 1e-5, upper max(1, Proc) x 1e3 (l. 34-35); human consumption, feed, trade
  flows, Armington quantities alike; cells without data fixed at 0;
- prices: market price 0.1 to 10 x PMrk (l. 526-531), producer and consumer prices alike; raw milk (MLK) allowed
  negative where a region has neither production nor domestic sales (l. 532-534), and in the Green Deal's
  negProdPriceAllowed(rms, "MILK") (greendeal_scenarios.gms l. 66-67); the young-animal prices +-10 x (|L| + 10) x 10.

**The solve** (arm/simu_market.gms l. 90-150): m_globMarket by CONOPT (DNLP, a zero objective V_dummy), at most two
tries; after an infeasible try, widen_bounds.gms FULL; CONOPT's infeasibility report (the marginals of the variables at
bounds that the phase-1 solve names) decides what is widened.

**The widening** (arm/widen_bounds.gms): for each variable at a bound with a non-zero marginal, the bound moved far
out: production's lower bound to L - 10 x max(10, Prod, |L|) (negative allowed, l. 31-57), its upper bound x 1000;
human consumption's lower bound to max(1e-12, L - 10 x max(10, HCon, |L|)), fixed where it is at 1e-12; processing
alike (negative allowed); feed, Armington quantities, domestic sales, trade flows, prices (v_prodPrice, v_marketPrice,
v_procMarg, v_priceFatProt), the tariffs (v_tarSpec, v_tarAdVal) and import prices alike. The PRESTEP branch (l. 561)
for the pre-steps. After a step (simu_market.gms l. 155-175) the trade flows fixed by the widening are released again.

**The fudge equations** become active where a lower bound is at or below 0 after a widening: ProdFudge_ (l. 2420),
FeedFudge_ (l. 1054), ProcFudge_ (l. 1158), ProdPriceFudge_ (l. 2378), tradeFlowFudge_ (l. 2784; with the
Armington commitments only); each maps a negative auxiliary (v_prodQuantNeg, ...) to a positive quantity by
ncpcm(-x, 0, Z) (Z 1e-2 x min(1000, max(1e-11, base))). consFudge_ is not activated (human consumption is fixed at
its floor instead).

## 2. The model today

The market has no bounds: hard floors in the code (DEP-38: GL consumer price at least 0.05 x base, demand at least 0;
DEP-39: market supply max(q0 + dq, 0), feed and processing at least 0, use clipped at 0, import prices at least
1e-9), and ProcFudge_ always on (DEP-37). In CAPRI's 2030 Green Deal run the fudge equations are not generated at the
calibration point (chk_market_data: no records of ProdFudge_, FeedFudge_, ProcFudge_), and the model's floors do not
bind in the full runs; they matter for large shocks.

## 3. The port

1. **The bounds of set_start_val.gms** as data of the lifted system (G3's unknowns): the price ratios (0.1 to 10,
   CAPRI's factors), supply and use levels, the quotas' sigmas (0 to 1 by construction), the young-animal prices, raw
   milk's negative range where CAPRI allows it. The trade flows are not unknowns of the lifted form: their bounds as
   inequality constraints on the flow functions (trade_system_ad's X), or flows lifted as unknowns where a bound can
   bind. **Check:** the bounds against chk_market_data's lower and upper of every v_* cell at the calibration point
   (the dump holds them: v_prodQuant 5,692 cells, lower at a median 1.4e-9 of the level, upper 1e3; v_marketPrice
   31,200 cells, 28,425 fixed; v_tradeFlows 166,364, 139,600 fixed), as CAPTRD-MOD's bounds were checked against
   CAPTRD's.
2. **The solve with bounds:** IPOPT on the lifted system (G3's "ipopt", already with lbx/ubx), the zero objective
   as CAPRI's. Newton and the continuation stay first where no bound binds: their solution is checked against the
   bounds and handed to IPOPT where one is violated.
3. **The widening:** after an infeasible IPOPT solve, the variables to widen from a least-infeasibility (phase-1) solve
   with the bounds' multipliers, as CAPTRD-MOD does for estimate_ms.gms (estimate_nlp.py,
   captrd.nlp_infeasible_marginals = "phase1", DEP-45: IPOPT has no CONOPT's infeasibility marginals); then
   widen_bounds.gms's rules per variable family, at most two tries as simu_market.gms; the release of the fixed
   flows after the step.
4. **The fudge equations** in the lifted system where a widened lower bound is at or below 0 (ProdFudge_, FeedFudge_,
   ProcFudge_ as CAPRI's, conditional: DEP-37 removed; ProdPriceFudge_; tradeFlowFudge_ with the Armington
   commitments, item 2 of the plan). The model's floors (DEP-38, DEP-39) removed where CAPRI's bounds take their place.
   **Written (14 November 2026, evening; not yet tested in a solve): ProdFudge_.** Each floored ProdNQ_ cell of the
   supply side (the EU blocks' measured-Hessian rows, the EU's market-only products, Norway's rows, the non-EU
   regions' rows) carries a mode, an entry of a parameter fm of the lifted system (supply_system_ad.prod_fudge): 0
   the model's floor max(q, 0) (market.bounds = "none": the system as before, the default solve's), 2 the row itself
   within CAPRI's bounds, 1 CAPRI's ProdFudge_, -ncpcm(-q, 0, Z) + 1e-11 with Z = 1e-2 min(1000, max(1e-11, base)),
   where the cell's supply unknown has its lower bound at or below 0 (market_model.gms l. 2421, v_prodQuant.lo LE
   0). With market.bounds = "capri" the modes follow the bounds: 2 or 1 at the start bounds, updated after each
   widening (market_chain._fudge_modes), so the system is not rebuilt. One difference from CAPRI: CAPRI's ProdFudge_
   acts per behavioural region (RMS) and its bounds are on the RMS's v_prodQuant; here the cell is the market
   region's row and its bound the market region's S (the same where a market region is one behavioural region,
   step 1's note on S). Unit test: prod_fudge against GAMS's ncpCM formula (test_supply_system_ad.py).
   **Written (15 November 2026, night; not yet tested in a solve): ProcFudge_ and FeedFudge_ on lifted unknowns**
   (the project lead's choice (a), 00:42: CAPRI's form, not the bounds mapped onto D). With market.bounds = "capri"
   (market_system(..., lift_use=True)) the processing cells (the crushing pairs and ProcNQ_'s cells) and the non-EU
   FeedNQ_ cells are an unknown block L of the lifted system, CAPRI's v_procQuant and v_feedQuant, with a defining row
   Ldef each and a mode appended to fm after the ProdNQ_ cells': 0 the model's form (ProcFudge_ always on, crushing
   and FeedNQ_ floored at 0: the default solve's values), 1 CAPRI's fudge on the row (market_model.gms l. 1054-1063,
   1158-1163), 2 ProcNQ_'s or FeedNQ_'s row itself within its bounds (CAPRI's v_procQuant, v_feedQuant above a
   positive lower bound). The bounds are set_start_val.gms's (l. 34-37, 181-182) and the widening widen_bounds.gms's
   (l. 125-138, 192-200), in market_bounds; the modes follow the bounds (market_chain._fudge_modes). With
   market.bounds = "none" nothing is lifted: the system is the one before. Approximations, as for S: CAPRI's cells are
   per behavioural region (RMS), here per market region's cell; the crushing entries' own ProcFudge_ (per RMS, in
   processing_ad.crush_function) stays in the model's form (mode 0) and the oil and cake output of the supply side
   follows it, not the lifted crush; CAPRI's upper bound on the negative auxiliaries (v_procQuantNeg.up = 10 |lower|,
   l. 132-133) is not carried. Test: test_supply_system_ad.py::test_the_lifted_processing_and_feed_reproduce_the_default_form.
   **Written (15 November 2026, evening): the dairy blocks' net supply and the K83 units' rows as fudge cells**
   (supply_system_ad: max(0, supply - processing) and the switched-off units' max(0, b (1 + rel)) through
   prodnq_cell, so each takes a mode as the ProdNQ_ cells: 0 the model's floor, as before, 1 CAPRI's ProdFudge_, 2 the
   row within its bounds; CAPRI's ProdFudge_ covers the dairy products, XXX1, and a switched-off country is a market
   region with ProdNQ_). Approximation as above: the cell is the market region's net row, CAPRI's the RMS's gross
   v_prodQuant. **Not needed (15 November 2026):** ProdPriceFudge_ (market_model.gms l. 2378): with CAPRI's MNL land
   block (supremaMrk on) it applies to the land-using products only, and its positive price enters Yield_ alone, which
   has no feedback on quantities or prices in CAPRI's default and is not ported (MARKET_EQUATIONS_INVENTORY.md);
   tradeFlowFudge_ (l. 2784): generated only with Armington commitments, and sim_ini_21730 has no p_arm2Commit (the
   plain CES second nest is DEP-12). **First solve with CAPRI's bounds (15 November 2026, 22:40):** the solver
   battery with market.bounds = "capri" (ipopt and auto; tools/check/market_solver_battery.py, shocks wheat+5,
   f2f-like and the new milk-90 and pork-90): on wheat+5 the fixed point converged in 29 iterations (17.6 s), the
   system built in 35 s, IPOPT under the bounds had not finished after 19 minutes and was stopped. Open: the cause
   (slow convergence, the widening loop or the restoration phase), from IPOPT's log. market.bounds stays "none" by
   default. **Diagnosis (15-16 November 2026):** (1) CAPRI's start bounds fixed 781 of the 12,673 unknowns while the
   square system kept all 12,673 equations (CAPRI generates no equation for a cell it fixes): 116 Armington prices of
   regions without Armington demand and 4 small processing cells are still set by their equations (Newton moves 102
   and 4 of them under wheat+5), so the bounded system had no solution and IPOPT went to its restoration phase at the
   first iteration. Fixed: those cells keep CAPRI's ranges instead of being fixed (market_bounds.py; a departure from
   CAPRI's fixing, required by the square system); the supply and use cells fixed at 0 stay fixed (their equations
   hold there). (2) With that IPOPT takes regular steps (infeasibility 0.027 -> 0.06 in 5 iterations) but does not
   converge in 60 iterations (5.5 s each, L-BFGS Hessian) and returns to restoration. (3) Newton under
   market.bounds = "capri" (the lifted use block, the modes at 2) stalls at 1.7e-2 in 8 steps on wheat+5, where it
   converges with "none": the "capri" system itself is harder, to be traced. The project lead's experience (15
   November 2026): CAPRI with IPOPT everywhere never converges in all regions. Next: the bounds in the Newton chain
   (a semismooth Newton on the bounded system, the bounds as complementarity) instead of IPOPT, for the project
   lead's decision; first (3). **Why the chain fails (point 1, 16 November 2026, 00:00-00:20; wheat+5, pork-90,
   milk-90, milk-50, pork-50):** (a) (3) is not the bounds: Newton stalls the same on wheat+5 with market.bounds =
   "none", with every mode 0 and with every mode 2 (1.7e-2 in 8 steps); the residuals are the EU's soft wheat quota's
   sigmoid and the wheat prices around it. The continuation in the sigmoid's slope (CAPRI's trim_trqs) converges, with
   and without CAPRI's bounds (24-33 s), and the "auto" chain under CAPRI's bounds solves wheat+5 without reaching
   IPOPT (35 s). (b) Under pork-90 the fixed point converges (34 iterations, 22 s), while the continuation of the
   lifted system stalls at its first slope (25) with and without the bounds (residuals: the pork and other quotas'
   sigmoids): for large shocks the lifted system's quota continuation is weaker than the fixed point. (c) Under
   milk-90 and milk-50 the fixed point fails too ("the land markets and the feed energy balances did not settle
   together"): a separate robustness issue of the inner blocks, before any bounds. (d) The quotas' sigmas sit at their
   [0, 1] bounds where the sigmoid saturates, and the lifted solutions leave them slightly above 1 (to 1.02): hard
   for an interior-point method. Point 2 (the project lead, 16 November): the semismooth Newton (Fischer-Burmeister,
   our own on CasADi and PARDISO; no maintained Python MCP solver at this size without a licence) and scipy's
   trust-region reflective least_squares in the battery, in the chain's order. **Tests to run** (after the full-run pair, one heavy job
   at a time): the chain with market.bounds "none" identical to before (modes 0); with "capri" on the solver
   battery's shocks; a shock that drives a cell below 0 (a supply cut of 90% in one region) solved with the widening
   and the fudge, against CAPRI's rules applied by hand.
5. **The default solver:** the fixed point cannot take bounds; with G3.4 the market's default becomes the decision
   of G3-R (the mini runs) together with whether the bounds bind in the reference scenarios.

**Tests:** the bounds against the dump (1); a shock that drives a quantity or price to its bound (a supply cut of
90% in one region, a price collapse of raw milk under negProdPriceAllowed) solved with the widening, against CAPRI's
rules applied by hand; the reference runs unchanged where no bound binds.

**Beyond CAPRI, for the project lead to decide:** a least-infeasibility formulation as a diagnostic mode (decided
5 November 2026, A1: optional only).

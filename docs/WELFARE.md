# Welfare report (CAPRI reports/welfare.gms; audit M7)

Ported 27 October 2026 (capri_mod/market/welfare.py for the market's agents; CAPRIModel._welfare_supply for the
regions with supply models). It replaces the first-order consumer and producer surplus of `_compute_welfare`, which
was not CAPRI's measure. Reporting only: no result of a run changes.

## What CAPRI computes

Each agent's welfare is measured with the agent's own behavioural function, from the calibration point (TRD) to the
simulation, per behavioural region (RMS), then summed (welfare.gms l. 780-812):

| Component | Agent | CAPRI (reports/welfare.gms) | In the model |
|---|---|---|---|
| CSSP | consumers | money metric of the GL demand system, one good after the other (l. 95-140) | ported: per behavioural region, CAPRI's sequence and goods order (gl_demand_goods.csv), at the consumer prices the GL demand saw (CPRI0 + ARM1P0 (PR - 1)), the refitted commitments |
| ProfitProc | processing industry | NQ processing functions (ProcNQ_), oilseed crushing in the margins (ProcMargO_), biofuel processors' margin x first-generation output, value of the residual feeds of RMSSUP (l. 155-213) | ported: ProcNQ_ per behavioural region (the model region's base processing spread by CAPRI's), crushing per behavioural region and seed (before ProcFudge_, as CAPRI's report), biofuel margin (PPRI0 x ratio - mu_b) x output, EU residual feeds' output value |
| ProfitDairy | dairies | NQ dairy function (DairyNQ_) in the processing margins (ProcMargM_), raw milk an input (l. 215-260) | ported: per EU member state and per non-EU behavioural region |
| ProfitAgr | farms | RMSSUP: the supply models' gross value added, EAAG MGVA, less the land rents with CAPRI's land market (l. 360-380, 800-806); other regions: the NQ supply function with land and feed energy (l. 265-300) | RMSSUP (the EU, Norway): MGVA of the supply models (capri_mod/income) less the land rents at the solution (results["welfare_supply"]); other regions: the integral of the model's own supply function (constant elasticity, see below) and of CAPRI's raw milk supply function in the dairy blocks |
| ProfitFeed | feed users | not RMSSUP: the NQ feed cost function FeedNQ_ (l. 455-540) | the integral of the model's non-EU feed demand (constant elasticities p_ElasFeed, M3), good by good in the model's commodity order |
| TariffRev | budget | tariffs on every flow: specific or flexible levy + ad valorem on (PMrk + transport), TRQ regimes (l. 545-605) | per flow X (p - a0 r - tc), the quota rent taken out; flows between the EU's trade blocks excluded |
| TRQRents | quota holders | (import price - in-quota price) x min(imports, quota), half importer, half exporter (l. 610-650; sol_market.gms l. 1127) | gap x sigmoid(fill) x min(share x imports, quota): under the sigmoid regime the import price is the in-quota price plus sigmoid x gap |
| PSEs | budget | minus premiums (FEOP, FEOG of non-market products), PSE/CSE/FSE wedges, processing aids, export subsidies, intervention costs (l. 655-690) | minus the supply models' premiums (results["welfare_supply"]); the model has no market wedges, export subsidies or intervention |
| ProfitLandUse | land owners | with CAPRI's land market (supremaMrk, as CAPRI's 2030 reference run): the land rents, UAAR x d_area (sol_simy.gms l. 181); other regions: the land supply function (l. 400-440) | RMSSUP: the land rents at the solution (each land type's area x its land row's dual); other regions none: the model's non-EU supply has no land market |

Total change (CAPRIModel.compare, `welfare_EUR_million_change`): the market's components + the changes of the supply
models' ProfitAgr, ProfitLandUse and PSEs.

## How each integral is taken

- A linear (NQ) function with a symmetric Hessian (ProcNQ_, crushing in the margins, DairyNQ_, the raw milk supply):
  sum_i (q0_i + dq_i / 2) dp_i. This is the value of CAPRI's good-by-good sum for a quadratic profit function; it does
  not depend on the order. The netput Hessian of the dairy blocks is symmetric (test_dairy_profit_is_the_integral_of_its_nq_function).
- The GL money metric: CAPRI's sequence, in CAPRI's goods order. It depends on the order (the sum is not the exact
  equivalent variation e(P0, u1) - Y; for a 10% random price change in Germany they differ by 0.03%).
- The constant-elasticity non-EU supply: S0 p0 (r^(e+1) - 1) / (e + 1) per region and product (own price only, no
  order). Only the cells whose supply at the solution is that function count: crushing, dairy products, raw milk,
  biofuels and residual feeds have their own blocks.
- The constant-elasticity non-EU feed demand, which has cross-price terms: good by good in the model's commodity
  order (path-dependent, as the GL money metric).

## Differences from CAPRI

1. **Levels, as CAPRI** (the project lead's decision, 28 October 2026; before, the components other than tariffs
   and quota rents were changes only). Each market component is the change from the calibration point plus CAPRI's
   base value of that component (welfare.gms): household expenditure at the calibration prices (CSSP), processing x
   price or crushing margin (ProfitProc), dairy products x processing margin (ProfitDairy), the revenue of the regions
   without supply models less their land and feed-energy netputs (ProfitAgr), minus 20% of their feed cost
   (ProfitFeed). The base values per CAPRI region come from CAPRI's 2030 data with welfare.gms's formulas
   (tools/build/build_welfare_base.py, capri_data/2017/market/welfare_base_2030.csv); against CAPRI's 2030 reference
   levels, CSSP and ProfitDairy are equal in all 80 regions, ProfitAgr and ProfitProc within a median 4-5%, ProfitFeed
   not comparable (CHANGELOG 28 October 2026). Comparisons of two runs take the difference of the levels.
2. **Non-EU farms and feed users**: the integrals of the model's constant-elasticity functions, not CAPRI's NQ
   functions with land and feed energy (the model's non-EU supply has no land or feed-energy netputs; non-EU feed is
   M3, K73). The welfare follows the functions the market solved with, so it is consistent with the model's
   quantities; it is CAPRI's measure only where the functions are CAPRI's.
3. **TRQ rents**: CAPRI's per exporter; the model's per model exporter region (the quota, gap and share of the flow
   under the quota aggregated by build_bilateral_market.py), with the model's one price per flow.
4. **Not represented**: market PSE/CSE/FSE wedges, processing aids, export subsidies and intervention costs (the model
   has none); the land owners of the regions without supply models (no land market); CAPRI's emission tax revenues
   (not in CAPRI's total either, welfare.gms l. 790-795).
5. **CAPRI's welfare at hand: the 2030 reference's levels only** (capri_data/sources/capri_res/ref2030_welfare.csv,
   from scen_ref_2030.txt). The Green Deal file of the same pair and the res_2_1730greendeal... files carry no welfare
   rows, so no scenario change can be compared with CAPRI's. The levels the model also reports as levels can be
   compared with the model's baseline: TariffRev (EU27 4,228), TRQRents (EU27 407), the supply models' MGVA (EU27
   302,113) and PSEs (EU27 -47,259). Internal checks: the GL money metric against the first-order term and the exact
   equivalent variation, the dairy profit against a numerical line integral, the market report at base and after a
   supply shock (capri_mod/tests/test_welfare.py).
6. **The land accounts are those of CAPRI's 2030 reference run, SUPREMA's** (welfare.gms supremaMrk on, CAPRI's land
   market): the farms' profit is MGVA less the land rents (EU27 in CAPRI's reference: 302,113 - 58,994 = 243,119),
   the rents are the land owners' (ProfitLandUse 58,994). The model takes the rent at the solution from the supply
   models' land market: each land type's area x the dual of its land row (EUR/ha), CAPRI's UAAR x d_area
   (results["welfare_supply"]: MGVA, RENT, ProfitAgr, ProfitLandUse, PSEs). The rent is a transfer: the total is the
   same with or without the split.

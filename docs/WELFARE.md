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
| ProfitAgr | farms | RMSSUP: the supply models' gross value added, EAAG MGVA (l. 360-380, 800-806); other regions: the NQ supply function with land and feed energy (l. 265-300) | RMSSUP (the EU, Norway): MGVA of the supply models (capri_mod/income, results["welfare_supply"]); other regions: the integral of the model's own supply function (constant elasticity, see below) and of CAPRI's raw milk supply function in the dairy blocks |
| ProfitFeed | feed users | not RMSSUP: the NQ feed cost function FeedNQ_ (l. 455-540) | the integral of the model's non-EU feed demand (constant elasticities p_ElasFeed, M3), good by good in the model's commodity order |
| TariffRev | budget | tariffs on every flow: specific or flexible levy + ad valorem on (PMrk + transport), TRQ regimes (l. 545-605) | per flow X (p - a0 r - tc), the quota rent taken out; flows between the EU's trade blocks excluded |
| TRQRents | quota holders | (import price - in-quota price) x min(imports, quota), half importer, half exporter (l. 610-650; sol_market.gms l. 1127) | gap x sigmoid(fill) x min(share x imports, quota): under the sigmoid regime the import price is the in-quota price plus sigmoid x gap |
| PSEs | budget | minus premiums (FEOP, FEOG of non-market products), PSE/CSE/FSE wedges, processing aids, export subsidies, intervention costs (l. 655-690) | minus the supply models' premiums (results["welfare_supply"]); the model has no market wedges, export subsidies or intervention |
| ProfitLandUse | land owners | default (not SUPREMA): RMSSUP none of its own (land rents are in MGVA); other regions: the land supply function (l. 400-440) | none: the model's non-EU supply has no land market |

Total change (CAPRIModel.compare, `welfare_EUR_million_change`): the market's components + the change of the supply
models' MGVA + the change of PSEs.

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

1. **Changes, not levels** (a choice, to be decided by the project lead). CAPRI reports levels: the change plus a base
   value set by convention: household expenditure on the good at base prices (CSSP), processing margin x quantity
   (ProfitProc, ProfitDairy), 50% of the revenue as the farms' profit of the regions without supply models (100%
   under SUPREMA), the feed cost less 20% (ProfitFeed). The model reports the market's components as changes against
   the market's calibration point: the base values are conventions without data behind them (the 50% and the 20%),
   and they cancel in the comparison of two runs, which is what the welfare report is read for. TariffRev, TRQRents,
   MGVA and PSEs are levels, as in CAPRI. The levels can be added (the base values are in the model's data) if the
   CAPRI tables are wanted as such.
2. **Non-EU farms and feed users**: the integrals of the model's constant-elasticity functions, not CAPRI's NQ
   functions with land and feed energy (the model's non-EU supply has no land or feed-energy netputs; non-EU feed is
   M3, K73). The welfare follows the functions the market solved with, so it is consistent with the model's
   quantities; it is CAPRI's measure only where the functions are CAPRI's.
3. **TRQ rents**: CAPRI's per exporter; the model's per model exporter region (the quota, gap and share of the flow
   under the quota aggregated by build_bilateral_market.py), with the model's one price per flow.
4. **Not represented**: market PSE/CSE/FSE wedges, processing aids, export subsidies and intervention costs (the model
   has none); the land owners of the regions without supply models (no land market); CAPRI's emission tax revenues
   (not in CAPRI's total either, welfare.gms l. 790-795).
5. **No CAPRI scenario welfare at hand to compare with**: the CAPRI result files in hand (res_2_1730greendeal...)
   carry no welfare rows. The checks are internal: the GL money metric against the first-order term and the exact
   equivalent variation, the dairy profit against a numerical line integral, the market report at base and after a
   supply shock (capri_mod/tests/test_welfare.py).

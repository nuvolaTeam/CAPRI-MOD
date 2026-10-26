# Manure market

Status: revised 20 October 2026 against the code. Run results of the sprints in which the market was built (conic
form, before the NLP form) were removed; current results are in README section 9 (Validation) and CHANGELOG.md.

Manure trade is on by default, as in CAPRI star 3.0's GUI (`New_Manure_Trade_fromGUI = true`, CAPRI's
`manureTradeNew`): `CAPRIModel.use_manure_market = True`. It is a scenario setting (`PolicyScenario.manure_trade`,
`run(manure_trade=...)`, `run_f2f_2030.py --manure-market / --no-manure-market`) and holds for the scenario and its
baseline. The Green Deal settings run with it; `farm_to_fork_scenario()` turns it off, as JRC121368 (sect. 4.3.4: "the
model assumes that all manure generated in a region has to be used within that region").

## What CAPRI does (`manuremarket/`, `supply/supply_model.gms`)

- One manure pool per country; every pair of pools trades at 1 EUR + 0.18 EUR/t/km of fresh manure (Van der Straeten
  et al. 2010), converted to nutrient at 7.97% mean content; distances between designated centre regions from CAPRI's
  NUTS 2 distance matrix (`define_manure_market_structure.gms`: rManPool_centre, p_mPoolTradeCost).
- Each region exports to / imports from its pool with a quadratic cost (+50 EUR/t per extra 1% of its own manure
  supply), constants calibrated to the base pattern (`define_manure_trade_costs.gms`, FINALIZE) so the base trade is
  optimal.
- The pool model (`m_mPoolMarket`) maximises surplus minus transport costs over the regions' responses (a
  Takayama-Judge spatial equilibrium), solved with CONOPT and iterated with the supply models.
- Manure applied, imports included, enters the crop need (`manExportOrAppl_`, `fertDistExcr_`, NUTNED_, an equality
  with purchases >= 0), so it must fit within what the crops can use.

## Base trade

The 2030 baseline's flows between regions are CAPRI's (2030 Green Deal reference with endogenous technologies,
`res_2_1730greendeal_refpol_endotech_all_ini`: MTRADE.NITF and EXCRET.NITF per CAPRI region;
`tools/build/build_manure_trade_base.py` -> `capri_data/2017/environment/manure_trade_2030.csv`): exporting regions keep
(1 - export share) of their manure N, importing regions receive manure N per ha of cropland; 1.2 Mt N moves between EU
regions (113 exporters, 111 importers when built). The base trade counts only where the run trades manure: without
trade (Farm-to-Fork as JRC121368) the scenario and its baseline keep all manure in its region.

## capri-mod

Regional model (`RegionalSupplyModel._land_augment`, every EU solve with trade on; regions with land-market data):
an export and an import column of manure N, CAPRI's quadratic cost (slope 50 EUR/t per 1% of the region's base manure
N), exports <= manure produced at the current herds; objective: the pool price (plus, under the emission tax, the
terms below). The fertiliser value of the manure is not in the objective: CAPRI's calibrated cost constants absorb it
at the base, and deviations from the base trade follow the change in manure's value in the model.

- NLP form (default): traded manure changes the manure applied in the fertilisation block (ManureNPK_, then
  fertDistExcr_ and NUTNED_ per crop group), so an exporter must buy the mineral N its crops lose and an importer buys
  less; it enters the N-surplus row in CAPRI's terms (SURTOT_REST_ with the purchases). P2O5 and K2O move with N in the
  region's manure proportions (REGISTERED: CAPRI trades MANP and MANK as products of their own, K50 departure 4).
  Emission tax: the mineral N bought or saved is taxed through the purchases, and `_nlp_tax_terms` takes the conic
  form's term off the columns: tax x substitution factor x (soil N2O + leaching N2O factor), exactly what the columns
  carry since the leaching factor was added to them (checked 21 October 2026; the 20 October revision of this file
  described the columns before that change).
- Conic form: the columns enter the N-balance row at +-(1 - substitution factor) (the balance's availability /
  efficiency; 0 substitution where the region's mineral N is already zero), the crop-need row and the mineral-N cap
  row at -+ substitution factor, the manure-application row at +-1; under the emission tax the soil N2O of the mineral
  N bought or saved is priced on the columns.

Pools (`CAPRIModel._update_manure_pools`): CAPRI's 34 country pools and 930 links
(`capri_data/2017/environment/manure_pool_costs.json`, `tools/build/build_manure_pool_costs.py`). Each outer iteration:

1. each region's exact piecewise-linear schedule from the reduced costs of its trade columns at its solution (NLP form:
   IPOPT's bound multipliers, because the fertilisation block is not in the stored rows; conic form: the conic solve's
   duals);
2. the primal spatial equilibrium on those schedules, a convex QP solved with Clarabel (`capri_mod/supply/convex_qp.py`;
   a built-in primal-dual method where Clarabel is missing), pool balances as equalities; pool prices = the balances'
   duals;
3. a Broyden-type correction of each pool's response (regions respond less than the schedule says, because their own
   N shadow price moves as they trade) and adaptive damping of the price move (full steps while the gap falls, halved,
   to at least 0.25, when it rises).

Convergence: every pool within `manure_pool_tolerance` (0.03) of its manure supply and EU-wide conservation within the
same tolerance; with trade on, the outer-iteration cap is raised to `manure_max_outer_iter` (60) when it is 25 or more.

The N-surplus target with trade is per hectare of current farmland (CAPRI's e_SURTOTHa; always on since
27 October 2026, when its switch was removed).

## Open

- No CAPRI Green Deal scenario result is in hand to compare the regional trade with (only the reference runs).
- CAPRI's e_manureLimit_ is in its equation list with the new manure trade but acts only with p_manure_limit, set by
  `pol_input/manure/ManureNLimit*.gms`; no scenario of capri-mod uses it.

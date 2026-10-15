# Manure market — design and status

Status: **implemented, on by default as in CAPRI star 3.0's GUI** (`New_Manure_Trade_fromGUI = true`;
`CAPRIModel.use_manure_market`; a scenario setting, `PolicyScenario.manure_trade`, held for its baseline). The
Green Deal group runs with it; Farm-to-Fork as JRC121368 runs without it (sect. 4.3.4: "the model assumes that all
manure generated in a region has to be used within that region"). The market corresponds to CAPRI's
`manureTradeNew` option.

**Base trade (Sprint 9j).** The 2030 baseline's manure flows between regions are CAPRI's (2030 Green Deal reference
with endogenous technologies, `res_2_1730greendeal_refpol_endotech_all_ini`: MTRADE.NITF and EXCRET.NITF per CAPRI
region; `tools/build_manure_trade_base.py`, `manure_trade_2030.csv`): exporting regions keep (1 − export share) of
their manure N, importing regions receive manure N per ha of cropland; 1.2 Mt N moves between EU regions. The file
had been written without a builder and by CAPRI code, so Belgium, Italy, Poland, Sweden, Romania, Ireland and
others had no trade (73 exporters and 76 importers; now 113 and 111). **The base trade counts only where the run
trades manure**: without trade (Farm-to-Fork as JRC121368), the scenario and its baseline keep all manure in its
region, as the report's CAPRI did (before, the baseline of a no-trade run still carried CAPRI's 2030 trade).

## What CAPRI does (`manuremarket/`, `supply/supply_model.gms`)

- One manure pool per country; every pair of pools trades at 1 EUR + 0.18 EUR/t/km
  of fresh manure (Van der Straeten et al. 2010), converted to nutrient at 7.97% mean
  content; distances between designated centre regions from CAPRI's NUTS-2 distance
  matrix.
- Each region exports to / imports from its pool with a quadratic cost (+50 EUR/t
  per extra 1% of its own manure supply), constants calibrated to the base pattern.
- The pool model (`m_mPoolMarket`) maximises surplus minus transport costs over the
  regions' linearised responses (a Takayama–Judge spatial equilibrium), solved with
  CONOPT and iterated with the supply models.
- All manure, imports included, must fit within crop nutrient need (`NUTNED_`, an
  equality with mineral N ≥ 0).

## What capri-mod does

- **Regional model** (`RegionalSupplyModel._land_augment`), in every EU solve with trade on (Sprint 9k; before,
  only under a nitrogen target): export and import columns enter the nitrogen row, where there is one, at
  ±(1 − substitution factor) — the balance's own factor, availability/efficiency × share of need above CAPRI's
  minimum-mineral floor; 1 where a region's mineral N is already zero; the crop-need row at ∓ substitution factor;
  the mineral-N row (mineral fertiliser cap) at ∓ substitution factor; manure-application row ±1; CAPRI's quadratic
  cost; exports ≤ manure produced. Objective: the pool price alone (plus, under the emission tax, the soil N2O of the
  mineral N bought or saved) - CAPRI's calibrated cost constants (FINALIZE) absorb the fertiliser terms at a fixed
  fertiliser price, so the base trade is optimal in the baseline (deviation 0.1 kt N).
- **Crop-need row** (CAPRI NUTNED_): in every EU solve (Sprint 9k), from `SupplyModule._manure_context`.
- **Pools** (`CAPRIModel._update_manure_pools`): CAPRI's 34 country pools and 930
  links (`capri_data/2017/environment/manure_pool_costs.json`, built by
  `tools/build_manure_pool_costs.py`). Each iteration: exact regional schedules from
  the reduced costs of the trade variables; a primal spatial-equilibrium QP solved by
  an interior-point method (`capri_mod/supply/convex_qp.py`: Clarabel if installed,
  else a built-in Mehrotra predictor-corrector); pool prices = shadow prices of the
  pool balances; adaptive damping; a quasi-Newton (Broyden-type) correction of each
  pool's response.
- **Convergence**: every pool within `manure_pool_tolerance` (default 0.03) of its
  manure supply, and EU-wide conservation within the same tolerance;
  `manure_max_outer_iter` (default 60).
- **Reporting**: the environmental accounting applies each region's traded manure
  with the same substitution factor, so reported surpluses match the regional
  constraints (checked: median ratio 1.000).
- Optional: `surplus_per_current_ha` (CAPRI's per-hectare-of-current-land surplus).

## Validation (full EU, 2030 Farm-to-Fork)

Note: JRC121368 had no manure trade, so these comparisons are against a run without it; they
show the market's effect, not an error in it.


Converges in 17 iterations, under 5 minutes. Mean absolute deviation from JRC121368
over twenty indicators: market off 4.4 points, market on 6.5, market on with the
per-hectare form 6.5. The market brings pigs (−12.3% vs CAPRI −14.5%), sheep, the beef
price and greenhouse gases closer to CAPRI, but crops overshoot (cereal price about
+30% vs +8%).

## Known limitation (re-examined, Sprint 9j)

The earlier finding - importing regions giving up crops for manure fees - is not seen in the current model. Star 3.0's
Green Deal group (s79: every region's surplus per ha −50%, organic, landscape, pesticide targets, manure trade on;
converged in 21 iterations, 46 minutes): 1.1 Mt N of manure moves against the base pattern. The livestock regions
with high nitrogen prices export more (Brittany +80 kt N, Pays de la Loire +58 kt); base importers whose own targets
bind take less (Castilla y León −57 kt, Emilia-Romagna −33 kt, Midi-Pyrénées −30 kt); base exporters where the
nitrogen price is low keep more at home (Romania's Sud-Est −63 kt, Brandenburg −52 kt, Extremadura −45 kt). Crop
area falls 4.2% in the regions taking more manure against 5.4% elsewhere. The country pools clear (worst pool 0.8%).

Open: (1) no CAPRI Green Deal scenario result is in hand to compare the regional trade with (only the reference runs);
(2) the regional trade columns existed only where a nitrogen target applied (closed in Sprint 9k: every EU solve
with trade on; Green Deal s81 within 0.8 points of s79, pool prices EUR 25-28/kg N in the livestock pools; EUR 50/t
tax s82: 22 kt N moved, pool prices about −0.2 EUR/kg N); (3) the run
reports showed pool prices of 0 because the runner read them from the unprojected model (fixed in
`tools/run_f2f_2030.py`; the solve itself used the pools' own prices).

# Scenario settings: CAPRI star 3.0's defaults, and each scenario's own

Status: revised 20 October 2026 against the code.

Rule: **capri-mod is built as CAPRI star 3.0 is; every scenario carries its own settings; a setting a scenario does
not state takes capri-mod's (star 3.0's) default.** The star 3.0 defaults are those of the installation's GUI
(`GUI/capri_gui_definition.xml`, task "Run scenario with market model") and of its scenario files
(`pol_input/greendeal/*.gms`). Interface: README sections 8.1-8.4; code: `capri_mod/policy/greendeal.py`,
`capri_mod/policy/endotech.py`, `capri_mod/policy/policy_module.py` (`PolicyScenario`).

## Settings that differ between scenarios

| Setting | star 3.0 default (capri-mod) | Green Deal group (`greendeal_scenario`, `greendeal_2030_scenario`) | Farm-to-Fork as JRC121368 (`farm_to_fork_scenario`) |
|---|---|---|---|
| Manure trade (`New_Manure_Trade_fromGUI`, `manureTradeNew`) | **on** | on | **off**: "all manure generated in a region has to be used within that region" (JRC121368 p. 24) |
| Nutrient-surplus target (`surpRedu`, `surptot.gms`) | every EU NUTS 2 region's baseline surplus per ha × (1 − surpRedu/100) (`surplus_rule="star3"`) | as star 3.0 | the report's tiered rule (25/50/75/100% by 50 kg N/ha band) with nine regions capped at 36% (`surplus_rule="jrc121368"`) |
| Milk-yield genomics (`ghgTechMYld`, `refpol_endotech_all_sup.gms`) | 0 | 0 | 0.2 (the value of CAPRI's JRC121368-era endotech references; Table 17: adopted on 15% of dairy cows) |
| Feed-efficiency genomics (`ghgTechFEff`) | 0.1 | 0.1 | 0.1 |
| Low-nitrogen feeding (`ghgTechLowNFeed`, `envind/low_n_feed.gms`) | 1 | 1 | 1 (the era's references set 1; Table 17 reports 0% adopted) |
| Linseed and nitrate supplements (`ghgTechLineNitr`, `envind/line_nitr.gms`) | 1 (a switch) | 1 | 1 (Table 17: linseed 0%, nitrate 7% adopted). 3-NOP is not in the model (README 5.1) |
| Endogenous biofuel markets (`BIOF_M`) | **on** | on | on (the report does not state it) |
| Pesticide reduction (`pestRedu`, `pesticides.gms` → `conventional_io.gms`) | plant protection cut by the remaining target on the conventional area, other inputs (INPO) raised by the same percentage, minimum cover-crop area of half the target; **no yield loss** (yield shock 'off', `pestDisaggStage` none) (`pesticide_rule="star3"`) | as star 3.0 | JRC121368's rule: 10% yield loss at a 50% cut, scaled linearly; organic yield gap scaled by 0.45 so the pesticide part is not counted twice (`pesticide_rule="jrc121368"`) |

Each setting holds for the scenario AND the baseline it is compared with (CAPRI's scenario file loads its reference;
capri-mod's baseline cache is keyed by the settings). Code: `PolicyScenario.manure_trade`, `.biofuel_markets`,
`.surplus_rule`, `.surplus_cut`, `.pesticide_rule`, `.endotech`; `CAPRIModel.run(manure_trade=, biofuel_markets=,
endotech=)`; `tools/run/run_f2f_2030.py --scenario f2f|greendeal|greendeal2030`.

Note: `PolicyScenario`'s own default for `pesticide_rule` is `"jrc121368"`; `greendeal_scenario()` sets `"star3"`.
A `PolicyScenario` built by hand with a pesticide target therefore applies the JRC121368 yield loss unless told
otherwise.

Policy shocks, not configurations (scenario only, not its baseline):

- `PolicyScenario.biofuel_mandate`: CAPRI's `scen/bio_fuels/change_biof_mandate.gms` (EU and UK blending mandates
  QUTS × factor; `run_f2f_2030.py --biofuel-mandate`).
- `PolicyScenario.mineral_redu`: the Green Deal's mineral fertiliser reduction (`mineRedu`, `minfert_redu_uaa.gms` /
  `minfert_redu_by_crop.gms`, EU27 only; `run_f2f_2030.py --mine-redu`; docs/FERTILISER_ALLOCATION.md).
  `farm_to_fork_scenario()` and `greendeal_scenario()` with its defaults run without it (`mine00`), as CAPRI's
  switchboard does; `greendeal_2030_scenario()` sets `13crp`.

## CAPRI's Green Deal targets by simulation year

From P. Witzke's production batch for the star 3.0 Green Deal group (section "f2f"); the batch also sets manure
trade, the inner fertiliser model, Trustee land, endogenous biofuel markets and the policy blocks on. Only the 2030 and
2040 rows are constants in the code (`GREENDEAL_2030_TARGETS`, `GREENDEAL_2040_TARGETS`).

| Year | lndscpTarg | orgTarg | pestRedu | mineRedu | surpRedu | capri-mod |
|---|---|---|---|---|---|---|
| 2025 | 7 | 15 | 13 | 10crp | 20 | `greendeal_scenario(...)` with these values |
| 2030 | 8 | 18 | 20 | 13crp | 30 | `greendeal_2030_scenario()`; `run_f2f_2030.py --scenario greendeal2030` |
| 2035 | 9 | 22 | 26 | 17crp | 40 | `greendeal_scenario(...)` with these values |
| 2040+ | 10 | 25 | 32 | 20crp | 50 | `greendeal_scenario(**GREENDEAL_2040_TARGETS)` |

`greendeal_scenario()` with its defaults (and `run_f2f_2030.py --scenario greendeal`) applies lnds10 org25 pest50
mine00 surp50 in 2030: stronger than any year of the batch (pestRedu 50 against 32 at the end point). The comparison
of the runs with the end-point and the 2030 targets is in docs/KNOWN_ISSUES.md, K38 (19 October 2026).

Allowed values (those CAPRI's GUI offers; anything else raises): surpRedu 0/20/30/35/40/50, orgTarg 0/15/18/22/25,
pestRedu 0/5/13/15/20/26/30/32/35/40/50, lndscpTarg 0/7/8/9/10, mineRedu 00/20/10crp/13crp/17crp/20crp. Not
implemented (an error if not 0): dietShift, othPol. The JRC121368 surplus rule accepts only surpRedu 0 or 50.

## Star 3.0 defaults for a scenario run with the market model, against capri-mod

| GUI setting | star 3.0 | capri-mod |
|---|---|---|
| Endogenous bio-fuel markets (`BIOF_M`) | true | true (`CAPRIModel.biofuel_markets`; a scenario may switch off; docs/BIOFUEL_MARKET.md) |
| Dairy block (part of the market model, no GUI switch) | always | on: nine products traded, raw milk, fat and protein per member state (no switch; docs/DAIRY_PROCESSING.md) |
| New Manure Trade Module | true | true (`CAPRIModel.use_manure_market`; a scenario may switch off) |
| Use inner fertilizer model (`useInnerFertDistModel`) | **true** | true (always, in CAPRI's NLP form): CAPRI's inner fertiliser distribution model on its 2030 priors, per region and crop group, inside the regional model; it carries the crop-specific mineral fertiliser caps (`results["fert_dist"]`; docs/FERTILISER_ALLOCATION.md) |
| Policy blocks | true | EU tariffs and tariff-rate quotas in the bilateral market. The EU is one market region by default; CAPRI's two EU trade blocks are an option (`market.eu_blocks`, `run_f2f_2030.py --set market.eu_blocks=true`) |
| Non-homothetic Armington (`modArmington`) | off | plain CES (as off) |
| Explicit NTMs | false | none |
| Trustee land supply | true | CAPRI's land market with its land rules (`supply.use_land_market`; the land rules LandBalNoSlak_ always) |
| Stock changes (`stockChg`) | nost | none |
| Allow minimum shares of anorganic fertilizers (`useMinimumAnorganicShares`) | false; NUTMIN_ is in the regional model only with the inner fertiliser model off | as star 3.0: NUTMIN_ off, the inner model being always on (K40; the switches of the conic form were removed on 26 October 2026) |
| Water module, crop inputs in market | false | false (capri-mod's water module is standalone, not part of `run()`) |
| Iterations (`STEPS`) / lower weights after (`LOWSTEPS`) | 99 / 20 | `max_outer_iter` 25 (raised to 60 with manure trade), adaptive damping per commodity (README 7.4) |

Outside the GUI table: CAPRI solves its regional supply models as NLPs with CONOPT; capri-mod solves the same form
with IPOPT (a conic reformulation with Clarabel was an option until 26 October 2026).

capri-mod has every star 3.0 default of this table except the iteration scheme. Farm-to-Fork: JRC121368 does not
state its biofuel setting, so it runs with the star 3.0 default, endogenous biofuel markets on.

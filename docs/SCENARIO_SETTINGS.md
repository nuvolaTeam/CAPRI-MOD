# Scenario settings: CAPRI star 3.0's defaults, and each scenario's own

Rule (October 2026): **capri-mod is built as CAPRI star 3.0 is; every scenario carries its own settings; a setting a
scenario does not state takes capri-mod's (star 3.0's) default.** The star 3.0 defaults are those of the
installation's GUI (`GUI/capri_gui_definition.xml`, task "Run scenario with market model") and of its scenario
files (`pol_input/greendeal/*.gms`).

## Settings that differ between scenarios

| Setting | star 3.0 default (capri-mod) | Green Deal group (`greendeal_scenario`) | Farm-to-Fork as JRC121368 (`farm_to_fork_scenario`) |
|---|---|---|---|
| Manure trade (`New_Manure_Trade_fromGUI`, `manureTradeNew`) | **on** | on (default) | **off** - "all manure generated in a region has to be used within that region" (JRC121368 p. 24) |
| Nutrient-surplus target (`surpRedu`, `surptot.gms`) | every EU NUTS2 region's baseline surplus per ha x (1 - surpRedu/100) | as star 3.0 | the report's tiered rule (25/50/75/100% by 50 kg N/ha band) with nine regions capped at 36% |
| Milk-yield genomics (`ghgTechMYld`, `refpol_endotech_all_sup.gms`) | 0 | 0 | 0.2 (Table 17: adopted on 15% of dairy cows) |
| Feed efficiency (`ghgTechFEff`) | 0.1 | 0.1 | 0.1 |
| Low-nitrogen feeding (`ghgTechLowNFeed`, `envind/low_n_feed.gms`) | 1 | 1 | 1 (the era's references set 1; Table 17 reports 0% adopted) |
| Linseed, nitrate, 3-NOP feed additives (`ghgTechLineNitr`, `envind/line_nitr.gms`) | 1 (a switch) | 1 | 1 (Table 17: linseed 0%, nitrate 7% adopted); linseed and nitrate in the regional models (Sprint 9g), 3-NOP registered (CH4 only) |
| Endogenous biofuel markets (`BIOF_M`) | **on** | on (default) | on (default: the report does not state it) |

Each holds for the scenario AND the baseline it is compared with (CAPRI's scenario file loads its reference; the
baseline cache is keyed by the settings). Code: `PolicyScenario.manure_trade`, `.biofuel_markets`, `.surplus_rule`,
`.surplus_cut`, `.endotech`; `CAPRIModel.run(manure_trade=, biofuel_markets=, endotech=)`; `tools/run_f2f_2030.py --scenario f2f|greendeal`.

Policy shocks, not configurations (scenario only, not its baseline): `PolicyScenario.biofuel_mandate`, CAPRI's
`scen/bio_fuels/change_biof_mandate.gms` (EU and UK blending mandates QUTS × factor; `run_f2f_2030.py
--biofuel-mandate`); `PolicyScenario.mineral_redu`, the Green Deal's mineral fertiliser reduction (`mineRedu`,
`minfert_redu_uaa.gms` / `minfert_redu_by_crop.gms`; `run_f2f_2030.py --mine-redu`; docs/FERTILISER_ALLOCATION.md).
Farm-to-Fork as JRC121368 and the Green Deal default run without it (mine00), as CAPRI's switchboard does.

Green Deal switches take the values CAPRI's GUI offers: surpRedu 0/20/30/35/40/50, orgTarg 0/15/18/22/25,
pestRedu 0/5/13/15/20/26/30/32/35/40/50, lndscpTarg 0/7/8/9/10, mineRedu 00/20/10crp/13crp/17crp/20crp. Not
implemented (refused): dietShift, othPol.

## Star 3.0 defaults for a scenario run with the market model, against capri-mod

| GUI setting | star 3.0 | capri-mod |
|---|---|---|
| Endogenous bio-fuel markets (`BIOF_M`) | true | true (Sprint 9c, docs/BIOFUEL_MARKET.md; `PolicyScenario.biofuel_markets` may switch off) |
| Dairy block (part of the market model, no GUI switch) | always | on (Sprint 9f): nine products traded, raw milk, fat and protein per member state (docs/DAIRY_PROCESSING.md) |
| New Manure Trade Module | true | true (scenario may switch off) |
| Use inner fertilizer model (`useInnerFertDistModel`) | **true** | true (Sprint 9e): CAPRI's statistical inner model on its 2030 priors, per region and crop group (`results["fert_dist"]`); regional totals from the balance's NUTNED_, as the inner model's own sum gives them; it carries the crop-specific mineral fertiliser caps (docs/FERTILISER_ALLOCATION.md) |
| Policy blocks | true | the EU is one market region with EU tariffs and TRQs |
| Non-homothetic Armington (`modArmington`) | off | plain CES (as off) |
| Explicit NTMs | false | none |
| Trustee land supply | true | land market with CAPRI's land rules |
| Stock changes (`stockChg`) | nost | none |
| Allow minimum shares of anorganic fertilizers | false | false (no minimum mineral share) |
| Water module, crop inputs in market | false | false |
| Iterations (`STEPS`) / lower weights after (`LOWSTEPS`) | 99 / 20 | 25 outer iterations (60 with manure trade), adaptive damping |

capri-mod now has every star 3.0 default of this table (endogenous biofuel markets since Sprint 9c, the inner
fertilizer model since Sprint 9e), except the iteration scheme. Farm-to-Fork: JRC121368 does not state its biofuel setting, so it runs
with capri-mod's (star 3.0's) default, endogenous biofuel markets on.

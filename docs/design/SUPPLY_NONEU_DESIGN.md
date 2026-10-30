# Supply models for the UK, Turkey and the Western Balkans: data inventory and design

Started 30 October 2026, the step after the market structure, which batch 7 did: GBR and WBA became trade regions.
Scoping: the project document noneu_supply_regions_scoping.md (27 October 2026).

## 1. Goal, as CAPRI

CAPRI's Green Deal 2030 run solves a regional supply model for 250 units: the EU27, Norway, the UK, Turkey and the
Western Balkans. The model covers 221 units (the EU27 and Norway). The 29 to add are:
- the UK: UKC00000 ... UKN00000, 11 units;
- Turkey: TR100000 ... TRC00000, 12 units;
- the Western Balkans: one unit per country, AL000000, BA000000, CS000000, KO000000, MK000000 and MO000000.

In CAPRI their market supply is their supply models' output (RMSSUP). The market's price forecast passes their market
prices back to their models.

## 2. Data inventory (30 October 2026)

77 builders write data per regional unit or member state. The inventory took them one by one, read-only: their
sources, whether those hold the 29 units, and whether the code limits itself to the EU. Only what was grepped or read
is stated.

**The main sources already hold all 29 units.**
- CAPREG's 2017 dumps for the eight countries are extracted (work/capreg_noneu/res_17{UK,TU,AL,BA,CS,KO,MK,MO}.txt).
- So do CAPRI's 2030 results (res_2_1730greendeal_refpol_endotech_all_ini, refdefaulta) and the market dump.
- CAPRI's 2030 PMP terms (pmp_quad_techn_2030) are there too. CAPRI's own quadPact is empty for TR, WB and NO.

| Verdict | Builders |
|---|---|
| ready (41) | build_animal_pmp_capri_2030, build_capri_base, build_capri_crop_n_coefs, build_capri_gnb_components, build_capri_level_ratio, build_captrd_trajectory, build_cattle_intensity, build_code_lists, build_crop_economics_2017, build_dairy_intensity, build_eu_producer_prices, build_feed_ration, build_fert_dist_priors, build_fert_side_effects, build_fodder_balance, build_ghg_coefs_2017, build_grass_intensity, build_intensity_q_2030, build_land_market, build_land_rents, build_livestock_premium_coef, build_livestock_units, build_luc_2030, build_manure_losses, build_manure_n2o, build_manure_trade_base, build_n_deposition_substitution, build_nh3_factors, build_npk_balance_2030, build_nutrient_coefs_regional, build_overfert_factors, build_p_balance, build_pmp_capri_2030, build_pmp_recipe, build_ration_trajectory_2030, build_tariffs_2017, build_welfare_base, extract_all_from_data2, extract_gd2030_nbalance, extract_remaining_nine, ingest_pmp_terms |
| ready but for Turkey's code TUR (7) | build_capreg_national_prices, build_enteric_feed_factors, build_livestock_n_export_coef, build_livestock_output_coef, build_livestock_products, build_young_animals, extract_capri_marginal_terms |
| needs its country list changed (7) | build_dairy_processing, build_eu_market_supply_nq, build_feed_demand_nonEU, build_mineral_n_price, build_supply_elas_nonEU, build_trajectory_capri_ref, build_world_prices |
| needs data CAPRI's files lack for some of the 29 (12) | build_ad_option, build_ammonia_cost_curves, build_ammonia_tech_model, build_ammonia_technologies, build_cover_crops, build_histosol, build_irrigation_2017, build_labour_setaside, build_price_trajectory_2030, build_supply_elasticities_regional, build_winter_cover_option, ingest_pela_gtap |
| EU-only by nature (10) | build_cap_ceilings_2030, build_cap_greening, build_capri_baseline_surplus, build_capri_eu27_levels, build_crop_cost_shares, build_genetics_effects, build_lownfeed_effects, build_nuts2024_reporting, build_plant_protection_cost, build_supplement_effects |

**The data CAPRI's files lack for some of the 29.**
- the AD base data and the GAINS country map: no TR or WB;
- the ammonia farm structure (p_holdLSU, p_Heads, p_nvzShare_lu): no TR or WB; p_minStorCapND is EU-only;
- p_winterCoverShare0: UK000000 only, nationally;
- the organic-soil shares (p_orgsoilori): no TR or WB;
- the irrigated shares (p_irriShare): no CS000000, Turkey only nationally;
- CAPREG's labour items: absent in the TU and AL dumps, as in Norway's;
- the PMP estimates of estnlp (PELA, VB, VD): the UK only;
- CAPRI's 2030 market prices: no TUR.

For each of these, CAPRI must have a rule for the units without data, since its results have values for them: the
costsavings show winter cover in all 29, for example. Those rules are to be read in CAPRI's code before any data is
built. No proxy.

**Issues across the builders.**
1. **The dumps' folder.** The builders glob $WORK/capreg/res_17*.txt. The eight non-EU dumps are elsewhere, and
   builders.json lists only the EU's and Norway's.
2. **Turkey's code.** Turkey's national code is TUR, not TR000000, and its dump is res_17TU.txt. The code's
   two-letter + "000000" patterns, the `[:2] + "000000"` fallbacks and capri_member_state_codes.csv (no TR, no WB) do
   not handle it. Handling it once in tools/lib/_model_regions.py and that table clears most of the "ready but for
   TUR" rows.
3. **The UK is left out explicitly** in build_regional_units.py: `ms = {... if r["capri_ms"] != "UK000000"}` (checked).
4. **"The EU" in the builders.** Some builders use regional_units.csv as if it meant the EU, so they would take in the
   new units silently: build_dairy_processing, build_eu_market_supply_nq, build_eu_producer_prices,
   build_supplement_effects, build_world_prices, and the Norway-only skips of build_histosol and
   build_plant_protection_cost. These must read the EU from eu_market_blocks.csv (H1 of HARDCODED_TABLES.md).
5. **CAPRI's Green Deal reference** (pol_input/.../refpol_endotech_all_sup.gms l. 49-64) turns some options on for
   all supply regions and keeps others EU-only:
   - on for all: winter cover, fallowing of organic soils, mitigation in general;
   - EU only: low-N feed, breeding, linseed and nitrate.

   The model follows those switches. For example, build_histosol skipping Norway is against fallowInAllRmssup = on:
   to correct.

## 3. Design

- **The regional units.** regional_units.csv gets all 250 units: build_regional_units.py without its UK exclusion,
  and with Turkey's TUR. Every region-keyed builder then writes rows for them.
- **The switch** (agreed with the project lead, 30 October 2026: a list per country rather than one on/off switch).
  The setting run.supply_countries_outside_eu lists the countries outside the EU whose supply models are in the run,
  by CAPRI code, as CAPRI's per-country switches do (%CountriesNO000000% ... %CountriesTUR%,
  capmod/define_regional_sets.gms l. 40-77). Default ["NO000000"]: the EU27 and Norway, as now. The UK can then come
  in before Turkey and the Western Balkans.
  - definitions.SUP_NONEU_ALL holds every country outside the EU with regional units; definitions.sup_noneu() is the
    run's selection, read when the run builds its modules (not at import, so a settings file decides it).
  - The model leaves out the units of countries not selected (CAPRIModel's region list) and refuses a selected
    country without regional data. The market's non-EU supply maps (SUP_NONEU_REGIONS, SUP_NONEU_COUNTRY,
    SUP_NONEU_MS) are built per market module from the selection.
  - The check that the default is unchanged is the exact-reproduction comparison of a run before and after the data
    rebuild with the 29 units. It matters because code that sums a table over all its rows would otherwise take in
    the new units.
- **The market.** A non-EU market region has supply models when its units are in the run. The market then takes its
  supply from them, through the mechanism built for Norway (definitions.SUP_NONEU, since 30 October from the data).
  - WBA holds six countries, where NOR holds one. The model's one-to-one map from a non-EU market region to its
    member state (SUP_NONEU_MS, about 10 places) becomes one-to-many.
- **The EU's own policy** stays off outside the EU, as now for Norway: the CAP, the EU's Green Deal targets, NUTS 2024
  reporting. Each country's 2030 policy is as in CAPRI's baseline, starting with CEILVAL, which CAPRI has for the UK
  units only.
- **The order of the work** (revised 30 October 2026: the switch comes before the regional units grow, since the
  model's region constants are read from regional_units.csv):
  1. The builders that took the EU from the member-state code table read it from the EU trade blocks (done).
  2. The switch (done, see above), and the supply models' "outside the EU" test by definitions.is_eu instead of the
     units' first two letters, which are not the country code for the UK (UK, country GB) or Serbia (CS, RS) (done).
  3. Turkey's code (TUR) and the Western Balkans in the country table; build_regional_units with all 250 units.
  4. The ready builders on the 250 units.
  5. The country lists of section 2.
  6. CAPRI's rules for the missing data, read and ported.
  7. The exact-reproduction check with the default setting.
  8. The market side: SUP_NONEU one-to-many (WBA).
  9. The baseline of the 29 against CAPRI's 2030.
  10. A gate with Farm-to-Fork and the Green Deal, agreed with the project lead.

## 4. Open points

- **Mitigation outside the EU in the Green Deal runs.** CAPRI's Green Deal reference
  (pol_input/greendeal/refpol_endotech_all_sup.gms l. 49-64) sets MitiInAllRmssup on, so winter cover
  (winterCovInAllRmssup) and histosol fallowing (fallowInAllRmssup) apply in every supply region; low-N feed,
  breeding, linseed and nitrate stay EU-only. pol_input/cap_after_2023 sets it off. The model has winter cover off
  outside the EU (abatement._catc_spec) and build_histosol leaves Norway out. This concerns Norway in today's Green
  Deal runs already. Decision of the project lead (30 October 2026): aligned with CAPRI when the 29 come in, for
  Norway too.

- **The "EU-wide" price fallback** (build_eu_producer_prices) averages over all model regions. With the 29 it would
  no longer be the EU's. To decide when CAPRI's own fallback for these countries is read.
- **CEILVAL for Turkey and the Western Balkans** is absent in CAPRI's 2030 results. Presumably CAPRI has no CAP-type
  ceiling there; to confirm in its code.

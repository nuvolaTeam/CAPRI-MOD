-- Inputs under capri_data/2017/policy. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/baselines/capri_greendeal_ref/1730/policy/cap_ceilings_2030.csv
CREATE TABLE pol_cap_ceilings_2030 (
    capri_region VARCHAR NOT NULL,
    DPPIL1 DOUBLE NOT NULL,
    DPPIL2 DOUBLE NOT NULL,
    DPRD_LFA DOUBLE NOT NULL,
    DPRD_N2K DOUBLE NOT NULL,
    DPAE DOUBLE NOT NULL,
    DPNAT DOUBLE NOT NULL,
    DPTOTAL DOUBLE NOT NULL,
    PRIMARY KEY (capri_region)
);
COMMENT ON TABLE pol_cap_ceilings_2030 IS 'CAPRI''s 2030 CAP budgets and the per-activity premium split by scheme (Pillar I, LFA, Natura 2000, agri-environment). (tools/build/build_cap_ceilings_2030.py)';
INSERT INTO value_units VALUES
  ('pol_cap_ceilings_2030', 'DPPIL1', NULL, 'open', 'cap_ceilings_2030.DPPIL1: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPPIL2', NULL, 'open', 'cap_ceilings_2030.DPPIL2: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPRD_LFA', NULL, 'open', 'cap_ceilings_2030.DPRD_LFA: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPRD_N2K', NULL, 'open', 'cap_ceilings_2030.DPRD_N2K: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPAE', NULL, 'open', 'cap_ceilings_2030.DPAE: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPNAT', NULL, 'open', 'cap_ceilings_2030.DPNAT: unit to be established'),
  ('pol_cap_ceilings_2030', 'DPTOTAL', NULL, 'open', 'cap_ceilings_2030.DPTOTAL: unit to be established');

-- file: capri_data/2017/policy/cap_greening_2013_2020.csv
CREATE TABLE pol_cap_greening_2013_2020 (
    "item" VARCHAR NOT NULL,
    "key" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY ("item", "key", source)
);
COMMENT ON TABLE pol_cap_greening_2013_2020 IS 'CAPRI''s CAP 2014-2020 greening (the policy of CAPRI''s 2030 reference, pol_input/cap_after_2014/ref.gms -> (tools/build/build_cap_greening.py)';
INSERT INTO value_units VALUES
  ('pol_cap_greening_2013_2020', 'value', NULL, 'open', 'cap_greening_2013_2020.value: unit to be established');

-- file: capri_data/2017/policy/cap_greening_fleg_ms.csv
CREATE TABLE pol_cap_greening_fleg_ms (
    ms VARCHAR NOT NULL,
    fpeg_kha DOUBLE NOT NULL,
    ofar_kha DOUBLE NOT NULL,
    fleg_share DOUBLE NOT NULL,
    PRIMARY KEY (ms)
);
COMMENT ON TABLE pol_cap_greening_fleg_ms IS 'CAPRI''s CAP 2014-2020 greening (the policy of CAPRI''s 2030 reference, pol_input/cap_after_2014/ref.gms -> (tools/build/build_cap_greening.py)';
INSERT INTO value_units VALUES
  ('pol_cap_greening_fleg_ms', 'fpeg_kha', NULL, 'open', 'cap_greening_fleg_ms.fpeg_kha: unit to be established'),
  ('pol_cap_greening_fleg_ms', 'ofar_kha', NULL, 'open', 'cap_greening_fleg_ms.ofar_kha: unit to be established'),
  ('pol_cap_greening_fleg_ms', 'fleg_share', NULL, 'open', 'cap_greening_fleg_ms.fleg_share: unit to be established');

-- file: capri_data/2017/policy/cap_payments.csv
CREATE TABLE pol_cap_payments (
    region VARCHAR NOT NULL,
    BPS DOUBLE NOT NULL,
    ANC DOUBLE NOT NULL,
    AES DOUBLE NOT NULL,
    ORGANIC DOUBLE NOT NULL,
    COUPLED DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE pol_cap_payments IS 'Crop yields, producer prices, input costs and CAP premiums for every model region from CAPRI''s 2017 results (tools/build/build_crop_economics_2017.py)';
INSERT INTO value_units VALUES
  ('pol_cap_payments', 'BPS', NULL, 'open', 'cap_payments.BPS: unit to be established'),
  ('pol_cap_payments', 'ANC', NULL, 'open', 'cap_payments.ANC: unit to be established'),
  ('pol_cap_payments', 'AES', NULL, 'open', 'cap_payments.AES: unit to be established'),
  ('pol_cap_payments', 'ORGANIC', NULL, 'open', 'cap_payments.ORGANIC: unit to be established'),
  ('pol_cap_payments', 'COUPLED', NULL, 'open', 'cap_payments.COUPLED: unit to be established');

-- file: capri_data/scenarios/capri_ref_2030/capri_baseline_surplus_2030.csv
CREATE TABLE pol_capri_baseline_surplus_2030 (
    region VARCHAR NOT NULL,
    surplus_kg_n_per_ha DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, source)
);
COMMENT ON TABLE pol_capri_baseline_surplus_2030 IS 'CAPRI''s own baseline gross N surplus per ha (2030 reference), per model region: the starting point (tools/build/build_capri_baseline_surplus.py)';
INSERT INTO value_units VALUES
  ('pol_capri_baseline_surplus_2030', 'surplus_kg_n_per_ha', NULL, 'open', 'capri_baseline_surplus_2030.surplus_kg_n_per_ha: unit to be established');

-- file: capri_data/scenarios/greendeal_group/mineral_redu_exemptions.csv
CREATE TABLE pol_mineral_redu_exemptions (
    capri_region VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    factor DOUBLE NOT NULL,
    after_year BIGINT NOT NULL,
    othpol_high BIGINT NOT NULL,
    PRIMARY KEY (capri_region, ngrp, after_year)
);
-- after_year: a calendar year (key), no unit
COMMENT ON TABLE pol_mineral_redu_exemptions IS 'CAPRI''s exemptions in the crop-specific mineral fertiliser reduction (pol_input/greendeal/minfert_redu_by_crop.gms). (tools/build/build_mineral_redu_rules.py)';
INSERT INTO value_units VALUES
  ('pol_mineral_redu_exemptions', 'factor', NULL, 'open', 'mineral_redu_exemptions.factor: unit to be established'),
  ('pol_mineral_redu_exemptions', 'othpol_high', NULL, 'open', 'mineral_redu_exemptions.othpol_high: unit to be established');

-- file: capri_data/scenarios/greendeal_group/mineral_redu_limcres.csv
CREATE TABLE pol_mineral_redu_limcres (
    capri_region VARCHAR NOT NULL,
    ngrp VARCHAR,
    fnut VARCHAR,
    add DOUBLE NOT NULL,
    after_year BIGINT NOT NULL,
    UNIQUE (capri_region, ngrp, fnut)
);
COMMENT ON TABLE pol_mineral_redu_limcres IS 'CAPRI''s relaxations of the limCres regulation in the crop-specific mineral fertiliser reduction (pol_input/greendeal/minfert_redu_by_crop.gms): for a group of every nutrient (fnut empty) or for a nutrient''s every group (ngrp empty). (tools/build/build_mineral_redu_rules.py)';
INSERT INTO value_units VALUES
  ('pol_mineral_redu_limcres', 'add', NULL, 'open', 'mineral_redu_limcres.add: unit to be established'),
  ('pol_mineral_redu_limcres', 'after_year', NULL, 'open', 'mineral_redu_limcres.after_year: unit to be established');

-- file: capri_data/baselines/capri_greendeal_ref/1730/policy/premium_scheme_shares_2030.csv
CREATE TABLE pol_premium_scheme_shares_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    DPPIL1 DOUBLE NOT NULL,
    DPRD_LFA DOUBLE NOT NULL,
    DPRD_N2K DOUBLE NOT NULL,
    DPAE DOUBLE NOT NULL,
    DPNAT DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, capri_region)
);
COMMENT ON TABLE pol_premium_scheme_shares_2030 IS 'CAPRI''s 2030 CAP budgets and the per-activity premium split by scheme (Pillar I, LFA, Natura 2000, agri-environment). (tools/build/build_cap_ceilings_2030.py)';
INSERT INTO value_units VALUES
  ('pol_premium_scheme_shares_2030', 'DPPIL1', NULL, 'open', 'premium_scheme_shares_2030.DPPIL1: unit to be established'),
  ('pol_premium_scheme_shares_2030', 'DPRD_LFA', NULL, 'open', 'premium_scheme_shares_2030.DPRD_LFA: unit to be established'),
  ('pol_premium_scheme_shares_2030', 'DPRD_N2K', NULL, 'open', 'premium_scheme_shares_2030.DPRD_N2K: unit to be established'),
  ('pol_premium_scheme_shares_2030', 'DPAE', NULL, 'open', 'premium_scheme_shares_2030.DPAE: unit to be established'),
  ('pol_premium_scheme_shares_2030', 'DPNAT', NULL, 'open', 'premium_scheme_shares_2030.DPNAT: unit to be established');

INSERT INTO value_units VALUES ('pol_mineral_redu_exemptions', 'after_year', NULL, 'open', 'a calendar year (part of the key), no unit');

-- CAPRI's CAP 2014-2020 ceilings and the endogenous entitlement limit (K136, 13 November 2026)

-- file: capri_data/2017/policy/cap14_national_ceilings.csv
CREATE TABLE pol_cap14_national_ceilings (
    ms VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    ceiling_meur DOUBLE NOT NULL,
    PRIMARY KEY (ms, "year")
);
COMMENT ON TABLE pol_cap14_national_ceilings IS 'CAPRI''s CAP 2014-2020 national ceilings (Regulation 1307/2013 Annex II, p_2013_1307_AnnexII of scen/base_scenarios/CAP_2014_2020.gms) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_national_ceilings', 'year', NULL, 'open', 'cap14_national_ceilings.year: a calendar year'),
  ('pol_cap14_national_ceilings', 'ceiling_meur', 'U_MioEur', 'capri', 'cap14_national_ceilings.ceiling_meur: million EUR');

-- file: capri_data/2017/policy/cap14_ceiling_shares.csv
CREATE TABLE pol_cap14_ceiling_shares (
    ms VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    pct DOUBLE NOT NULL,
    PRIMARY KEY (ms, "year", scheme)
);
COMMENT ON TABLE pol_cap14_ceiling_shares IS 'The young-farmer, redistributive and natural-constraint payments in percent of the national ceiling (p_BPSYF, p_BPSRED, p_BPSNATCO of CAP_2014_2020.gms) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_ceiling_shares', 'year', NULL, 'open', 'cap14_ceiling_shares.year: a calendar year'),
  ('pol_cap14_ceiling_shares', 'pct', 'U_percent', 'capri', 'cap14_ceiling_shares.pct: % of the national ceiling');

-- file: capri_data/2017/policy/cap14_pillar_transfers.csv
CREATE TABLE pol_cap14_pillar_transfers (
    ms VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    pct DOUBLE NOT NULL,
    PRIMARY KEY (ms, "year")
);
COMMENT ON TABLE pol_cap14_pillar_transfers IS 'The transfer from pillar 1 to pillar 2 in percent of the national ceiling (p_cap_2013_2020_transfers_dp_rd rel of scen/Premiums/cap_2013_2020_transfers.gms; a row with 0 is a cell written EPS) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_pillar_transfers', 'year', NULL, 'open', 'cap14_pillar_transfers.year: a calendar year'),
  ('pol_cap14_pillar_transfers', 'pct', 'U_percent', 'capri', 'cap14_pillar_transfers.pct: % of the national ceiling');

-- file: capri_data/2017/policy/cap14_coupled_ceilings.csv
CREATE TABLE pol_cap14_coupled_ceilings (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    ceiling_meur DOUBLE NOT NULL,
    PRIMARY KEY (region, "year", scheme)
);
COMMENT ON TABLE pol_cap14_coupled_ceilings IS 'The ceilings of the voluntary coupled support and the crop-specific cotton payment per scheme (scen/Premiums/Coupling/vcs_2015_2020.gms, CropSpecificPremium_2015_2020.gms) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_coupled_ceilings', 'year', NULL, 'open', 'cap14_coupled_ceilings.year: a calendar year'),
  ('pol_cap14_coupled_ceilings', 'ceiling_meur', 'U_MioEur', 'capri', 'cap14_coupled_ceilings.ceiling_meur: million EUR');

-- file: capri_data/2017/policy/cap14_settings.csv
CREATE TABLE pol_cap14_settings (
    "item" VARCHAR NOT NULL,
    "key" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY ("item", "key")
);
COMMENT ON TABLE pol_cap14_settings IS 'The CAP 2014-2020 chain''s settings: greening share, BPS years, SAPS member states, the endogenously cut schemes (dpEndCut) and the year of the trend levels (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_settings', 'value', NULL, 'open', 'cap14_settings.value: by item (a share, a year or 1 for a member)');

-- file: capri_data/2017/policy/cap14_entitlement_levels.csv
CREATE TABLE pol_cap14_entitlement_levels (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    trd_kha DOUBLE NOT NULL,
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE pol_cap14_entitlement_levels IS 'CAPRI''s trend levels of its production activities (DATA(ru, mpact, LEVL, TRD) of sim_ini_21730): the crops'' sum is a region''s entitlement limit (policy/def_endCut.gms), all of them scale the rural development rates (policy/rd_logic.gms) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_entitlement_levels', 'trd_kha', NULL, 'open', 'cap14_entitlement_levels.trd_kha: 1000 ha (crops) or 1000 heads (animals)');

-- file: capri_data/2017/policy/cap14_coupled_rates.csv
CREATE TABLE pol_cap14_coupled_rates (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    "group" VARCHAR NOT NULL,
    rate DOUBLE NOT NULL,
    PRIMARY KEY (region, "year", scheme, "group")
);
COMMENT ON TABLE pol_cap14_coupled_rates IS 'The rates of the voluntary coupled support and the crop-specific cotton payment per premium group, EUR per unit of the group''s activities (scen/Premiums/Coupling/vcs_2015_2020.gms, CropSpecificPremium_2015_2020.gms) (tools/build/build_cap14_entitlements.py)';
INSERT INTO value_units VALUES
  ('pol_cap14_coupled_rates', 'year', NULL, 'open', 'cap14_coupled_rates.year: a calendar year'),
  ('pol_cap14_coupled_rates', 'rate', NULL, 'open', 'cap14_coupled_rates.rate: EUR per unit of the group''s activities (per ha or per head)');

-- file: capri_data/2017/policy/premium_entitlement_weights.csv
CREATE TABLE pol_premium_entitlement_weights (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    scheme VARCHAR NOT NULL,
    weight DOUBLE NOT NULL,
    eps INTEGER NOT NULL CHECK (eps IN (0, 1)),
    PRIMARY KEY (region, activity, scheme)
);
COMMENT ON TABLE pol_premium_entitlement_weights IS 'The share of an activity''s level holding entitlements of a scheme (p_EntlWght1 of sim_ini_21730; eps 1: written EPS, no entitlements; policy/policy.gms) (tools/build/build_premium_policy_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_premium_entitlement_weights', 'weight', 'U_ratio', 'capri', 'premium_entitlement_weights.weight: share of the level'),
  ('pol_premium_entitlement_weights', 'eps', NULL, 'open', 'premium_entitlement_weights.eps: 1 where CAPRI writes EPS');

-- file: capri_data/2017/policy/premium_settings.csv
CREATE TABLE pol_premium_settings (
    "item" VARCHAR PRIMARY KEY,
    "value" DOUBLE NOT NULL,
    source VARCHAR NOT NULL
);
COMMENT ON TABLE pol_premium_settings IS 'The flags of policy/policy.gms: ntslvl (re-aggregate the declared premiums to NUTS 1 and the member states) and p_AggregNUTS2 (farm types) of sim_ini_21730 (tools/build/build_premium_policy_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_premium_settings', 'value', NULL, 'open', 'premium_settings.value: a flag');

-- file: capri_data/2017/policy/premium_group_edits.csv
CREATE TABLE pol_premium_group_edits (
    "group" VARCHAR NOT NULL,
    from_group VARCHAR NOT NULL,
    domain VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY ("group", from_group)
);
COMMENT ON TABLE pol_premium_group_edits IS 'The premium groups CAPRI''s chain redefines at run time: the group''s activities of the domain become those of the groups on the right (pol_input/mtr_until2013.gms) (tools/build/build_cap14_entitlements.py)';

-- file: capri_data/2017/policy/rd_budget.csv
CREATE TABLE pol_rd_budget (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    measure VARCHAR NOT NULL,
    plan_spend VARCHAR NOT NULL CHECK (plan_spend IN ('plan', 'spend')),
    meur DOUBLE NOT NULL,
    eps INTEGER NOT NULL CHECK (eps IN (0, 1)),
    PRIMARY KEY (region, "year", measure, plan_spend)
);
COMMENT ON TABLE pol_rd_budget IS 'CAPRI''s rural development public money (rdSpendPublic of rd_budget.gdx) per region, year and RDP measure; eps 1: written EPS (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_budget', 'year', NULL, 'open', 'rd_budget.year: a calendar year'),
  ('pol_rd_budget', 'meur', 'U_MioEur', 'capri', 'rd_budget.meur: million EUR'),
  ('pol_rd_budget', 'eps', NULL, 'open', 'rd_budget.eps: 1 where CAPRI writes EPS');

-- file: capri_data/2017/policy/rd_programme_years.csv
CREATE TABLE pol_rd_programme_years (
    rdp VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    PRIMARY KEY (rdp, "year")
);
COMMENT ON TABLE pol_rd_programme_years IS 'The years of each rural development programme (rdp_simyy of rd_budget.gdx) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_programme_years', 'year', NULL, 'open', 'rd_programme_years.year: a calendar year');

-- file: capri_data/2017/policy/rd_scheme_measures.csv
CREATE TABLE pol_rd_scheme_measures (
    scheme VARCHAR NOT NULL,
    rdp VARCHAR NOT NULL,
    measure VARCHAR NOT NULL,
    PRIMARY KEY (scheme, rdp, measure)
);
COMMENT ON TABLE pol_rd_scheme_measures IS 'The RDP measures of each CAPRI RD payment scheme by programme (psDpay_RDP_rdMeasure, define_second_pillar_baseline.gms) (tools/build/build_rd_inputs.py)';

-- file: capri_data/2017/policy/rd_shock_measures.csv
CREATE TABLE pol_rd_shock_measures (
    shock VARCHAR NOT NULL,
    rdp VARCHAR NOT NULL,
    measure VARCHAR NOT NULL,
    PRIMARY KEY (shock, rdp, measure)
);
COMMENT ON TABLE pol_rd_shock_measures IS 'The RDP measures of the policy shocks of CAPRI''s RD schemes'' measures (rdShocks_RDP_rdMeasure, load_rdp_spend_and_budget.gms) (tools/build/build_rd_inputs.py)';

-- file: capri_data/2017/policy/rd_new_measure_keys.csv
CREATE TABLE pol_rd_new_measure_keys (
    region VARCHAR NOT NULL,
    shock VARCHAR NOT NULL,
    share DOUBLE NOT NULL,
    PRIMARY KEY (region, shock)
);
COMMENT ON TABLE pol_rd_new_measure_keys IS 'CAPRI''s regional distribution key of RD money on a measure not funded before (p_rdNewMeasuresRegDist) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_new_measure_keys', 'share', 'U_ratio', 'capri', 'rd_new_measure_keys.share: share of the country');

-- file: capri_data/2017/policy/rd_land_partition.csv
CREATE TABLE pol_rd_land_partition (
    region VARCHAR NOT NULL,
    land_cover VARCHAR NOT NULL,
    area_type VARCHAR NOT NULL,
    kha DOUBLE NOT NULL,
    PRIMARY KEY (region, land_cover, area_type)
);
COMMENT ON TABLE pol_rd_land_partition IS 'The agricultural land covers'' areas, total and in LFA, Natura 2000, HNV and NVZ (p_clueLandPart, CLUE) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_land_partition', 'kha', 'U_1000ha', 'capri', 'rd_land_partition.kha: 1000 ha');

-- file: capri_data/2017/policy/rd_fadn_ae.csv
CREATE TABLE pol_rd_fadn_ae (
    ms VARCHAR NOT NULL,
    farm_type VARCHAR NOT NULL,
    lfa VARCHAR NOT NULL,
    ae VARCHAR NOT NULL,
    unit VARCHAR NOT NULL,
    value DOUBLE NOT NULL,
    PRIMARY KEY (ms, farm_type, lfa, ae, unit)
);
COMMENT ON TABLE pol_rd_fadn_ae IS 'FADN 2005 hectares and agri-environment euros by farm type, in or out of LFA, with or without AE (p_fes) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_fadn_ae', 'value', NULL, 'open', 'rd_fadn_ae.value: by unit: ha or EUR');

-- file: capri_data/2017/policy/rd_sweden_expert.csv
CREATE TABLE pol_rd_sweden_expert (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    ceiling_meur DOUBLE NOT NULL,
    PRIMARY KEY (region, "year", scheme)
);
COMMENT ON TABLE pol_rd_sweden_expert IS 'Sweden''s RD expert data per NUTS 2 region, year and scheme (p_seLbuData) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_sweden_expert', 'year', NULL, 'open', 'rd_sweden_expert.year: a calendar year'),
  ('pol_rd_sweden_expert', 'ceiling_meur', 'U_MioEur', 'capri', 'rd_sweden_expert.ceiling_meur: million EUR');

-- file: capri_data/2017/policy/rd_sets.csv
CREATE TABLE pol_rd_sets (
    "set" VARCHAR NOT NULL,
    a VARCHAR NOT NULL,
    b VARCHAR NOT NULL,
    PRIMARY KEY ("set", a, b)
);
COMMENT ON TABLE pol_rd_sets IS 'The RD chain''s two-dimensional sets psgroup_tf8, dpae_tf8, tf8_lc (rd_static.gms) (tools/build/build_rd_inputs.py)';

-- file: capri_data/2017/policy/rd_settings.csv
CREATE TABLE pol_rd_settings (
    "item" VARCHAR NOT NULL,
    "key" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY ("item", "key")
);
COMMENT ON TABLE pol_rd_settings IS 'The RD chain''s maximum LFA and Natura 2000 amounts (p_rdMax, define_second_pillar_baseline.gms) (tools/build/build_rd_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_rd_settings', 'value', 'U_EuPerHa', 'capri', 'rd_settings.value: EUR per ha');

-- file: capri_data/2017/policy/nordic_aid_rates.csv
CREATE TABLE pol_nordic_aid_rates (
    scheme VARCHAR NOT NULL,
    "group" VARCHAR NOT NULL,
    nordic_region VARCHAR NOT NULL,
    basis VARCHAR NOT NULL CHECK (basis IN ('per_lu', 'per_ha')),
    rate DOUBLE NOT NULL,
    PRIMARY KEY (scheme, "group", nordic_region)
);
COMMENT ON TABLE pol_nordic_aid_rates IS 'CAPRI''s Nordic aid amounts by scheme, premium group and Nordic aid region: per livestock unit or ton of milk (p_nordicAid_2_5_perLU) or per ha (p_nordicAid_2_9_PerHa) (tools/build/build_nordic_aid.py)';
INSERT INTO value_units VALUES
  ('pol_nordic_aid_rates', 'rate', NULL, 'open', 'nordic_aid_rates.rate: EUR per livestock unit, ton of milk or ha (basis)');

-- file: capri_data/2017/policy/nordic_aid_ceilings.csv
CREATE TABLE pol_nordic_aid_ceilings (
    scheme VARCHAR NOT NULL,
    ms VARCHAR NOT NULL,
    ceiling_meur DOUBLE NOT NULL,
    PRIMARY KEY (scheme, ms)
);
COMMENT ON TABLE pol_nordic_aid_ceilings IS 'CAPRI''s Nordic aid ceilings per scheme and member state (tables 2.6 and 2.10 of nordicaid.gms) (tools/build/build_nordic_aid.py)';
INSERT INTO value_units VALUES
  ('pol_nordic_aid_ceilings', 'ceiling_meur', 'U_MioEur', 'capri', 'nordic_aid_ceilings.ceiling_meur: million EUR');

-- file: capri_data/2017/policy/nordic_aid_region_shares.csv
CREATE TABLE pol_nordic_aid_region_shares (
    region VARCHAR NOT NULL,
    nordic_region VARCHAR NOT NULL,
    share DOUBLE NOT NULL,
    PRIMARY KEY (region, nordic_region)
);
COMMENT ON TABLE pol_nordic_aid_region_shares IS 'The share of a CAPRI region in each Nordic aid region (p_nordicAidRegionShare, nordicaid.gms) (tools/build/build_nordic_aid.py)';
INSERT INTO value_units VALUES
  ('pol_nordic_aid_region_shares', 'share', 'U_ratio', 'capri', 'nordic_aid_region_shares.share: share of the region');

-- file: capri_data/2017/policy/nordic_aid_schemes.csv
CREATE TABLE pol_nordic_aid_schemes (
    scheme VARCHAR PRIMARY KEY,
    apptype VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    source VARCHAR NOT NULL
);
COMMENT ON TABLE pol_nordic_aid_schemes IS 'The Nordic aid schemes'' application types and the year nordicaid.gms declares them (tools/build/build_nordic_aid.py)';
INSERT INTO value_units VALUES
  ('pol_nordic_aid_schemes', 'year', NULL, 'open', 'nordic_aid_schemes.year: a calendar year');

-- file: capri_data/2017/policy/cndp_decoupled_groups.csv
CREATE TABLE pol_cndp_decoupled_groups (
    scheme VARCHAR NOT NULL,
    "group" VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (scheme, "group")
);
COMMENT ON TABLE pol_cndp_decoupled_groups IS 'The decoupled complementary national payments'' premium groups (psdpay_to_psgroup of CAP_2013_2020_CNDP.gms): the rate the ceiling over the member state''s level of the group (tools/build/build_cap14_entitlements.py)';

-- file: capri_data/2017/policy/bps_convergence_regions.csv
CREATE TABLE pol_bps_convergence_regions (
    ms VARCHAR NOT NULL,
    bps_region VARCHAR NOT NULL,
    members_of VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (ms, bps_region, members_of)
);
COMMENT ON TABLE pol_bps_convergence_regions IS 'The member states'' BPS regions (bps_region_to_ru of scen/Premiums/bps_convergence.gms, transcribed): a region''s units are those of the CAPRI region named (MAP_RR, itself included), REST the member state''s other units, EACH every NUTS 2 region its own (declared)';

-- file: capri_data/2017/policy/bps_convergence_options.csv
CREATE TABLE pol_bps_convergence_options (
    ms VARCHAR NOT NULL,
    bps_region VARCHAR NOT NULL,
    linear INTEGER NOT NULL CHECK (linear IN (0, 1)),
    rule_30_percent INTEGER NOT NULL CHECK (rule_30_percent IN (0, 1)),
    final_year BIGINT NOT NULL,
    target_share DOUBLE NOT NULL,
    gap_closure DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (ms, bps_region)
);
COMMENT ON TABLE pol_bps_convergence_options IS 'The member states'' BPS internal convergence options per BPS region (bps_convergence.gms, transcribed): linear model, 30% rule, final year, the tunnel''s target share of the average unit value and the share of the gap closed (declared)';
INSERT INTO value_units VALUES
  ('pol_bps_convergence_options', 'final_year', NULL, 'open', 'bps_convergence_options.final_year: a calendar year'),
  ('pol_bps_convergence_options', 'linear', NULL, 'open', 'bps_convergence_options.linear: 1 for the linear model'),
  ('pol_bps_convergence_options', 'rule_30_percent', NULL, 'open', 'bps_convergence_options.rule_30_percent: 1 where the 30% rule applies'),
  ('pol_bps_convergence_options', 'target_share', 'U_ratio', 'capri', 'bps_convergence_options.target_share: share of the average IUV'),
  ('pol_bps_convergence_options', 'gap_closure', 'U_ratio', 'capri', 'bps_convergence_options.gap_closure: share of the gap');

-- file: capri_data/2017/policy/mtr_declarations.csv
CREATE TABLE pol_mtr_declarations (
    line BIGINT NOT NULL,
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    "value" VARCHAR,
    special VARCHAR CHECK (special IN ('EPS', 'NA', 'APPTYPE')),
    PRIMARY KEY (line, region, "year", scheme, item)
);
COMMENT ON TABLE pol_mtr_declarations IS 'The premium declarations of the BPS key''s schemes: line 0 sim_ini_21730''s p_premDataE time series, line n the literal assignment of pol_input/mtr_until2013.gms at line n; value a number or, with special APPTYPE, an application type (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_declarations', 'line', NULL, 'open', 'mtr_declarations.line: a line number of the GAMS file'),
  ('pol_mtr_declarations', 'year', NULL, 'open', 'mtr_declarations.year: a calendar year');

-- file: capri_data/2017/policy/mtr_ceiling_tables.csv
CREATE TABLE pol_mtr_ceiling_tables (
    "table" VARCHAR NOT NULL CHECK ("table" IN ('ANNEX_VIII', 'ANNEX_VIIIa', 'ANNEX_IV', 'SAPS_AREAS')),
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY ("table", region, "year")
);
COMMENT ON TABLE pol_mtr_ceiling_tables IS 'The national ceilings of Reg. 1782/2003 Annex VIII and VIIIa and Reg. 73/2009 Annex IV (million EUR) and the SAPS areas (1000 ha, year 0) of mtr_until2013.gms (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_ceiling_tables', 'value', NULL, 'open', 'mtr_ceiling_tables.value: million EUR (the annexes) or 1000 ha (SAPS_AREAS)'),
  ('pol_mtr_ceiling_tables', 'year', NULL, 'open', 'mtr_ceiling_tables.year: a calendar year (0 for the SAPS areas)');

-- file: capri_data/2017/policy/mtr_coupling.csv
CREATE TABLE pol_mtr_coupling (
    scheme VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    ms VARCHAR NOT NULL,
    pct DOUBLE NOT NULL,
    eps INTEGER NOT NULL CHECK (eps IN (0, 1)),
    PRIMARY KEY (scheme, "year", ms)
);
COMMENT ON TABLE pol_mtr_coupling IS 'TABLE p_couplPercent_E of mtr_until2013.gms: the coupling degree of each scheme and member state from the year written; eps 1 where written EPS (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_coupling', 'eps', NULL, 'open', 'mtr_coupling.eps: 1 where CAPRI writes EPS'),
  ('pol_mtr_coupling', 'pct', 'U_percent', 'capri', 'mtr_coupling.pct: percent coupled'),
  ('pol_mtr_coupling', 'year', NULL, 'open', 'mtr_coupling.year: a calendar year');

-- file: capri_data/2017/policy/mtr_dd_targets.csv
CREATE TABLE pol_mtr_dd_targets (
    region VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    scheme VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    pct DOUBLE NOT NULL,
    eps INTEGER NOT NULL CHECK (eps IN (0, 1)),
    PRIMARY KEY (region, "year", scheme, target)
);
COMMENT ON TABLE pol_mtr_dd_targets IS 'TABLE p_premToDDTarget_E of mtr_until2013.gms: the share of a decoupled scheme going to each decoupling target (the hybrid models) (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_dd_targets', 'eps', NULL, 'open', 'mtr_dd_targets.eps: 1 where CAPRI writes EPS'),
  ('pol_mtr_dd_targets', 'pct', 'U_percent', 'capri', 'mtr_dd_targets.pct: percent of the scheme'),
  ('pol_mtr_dd_targets', 'year', NULL, 'open', 'mtr_dd_targets.year: a calendar year');

-- file: capri_data/2017/policy/mtr_dd_target_rules.csv
CREATE TABLE pol_mtr_dd_target_rules (
    line BIGINT PRIMARY KEY,
    region VARCHAR NOT NULL,
    scheme VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    pct DOUBLE NOT NULL,
    from_year BIGINT NOT NULL
);
COMMENT ON TABLE pol_mtr_dd_target_rules IS 'The decoupling target assignments of mtr_until2013.gms l. 1566-1581 in their order (scheme or target ALL: all of PSDPAY_MTR_EL or DDTarget) (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_dd_target_rules', 'line', NULL, 'open', 'mtr_dd_target_rules.line: a line number of the GAMS file'),
  ('pol_mtr_dd_target_rules', 'pct', 'U_percent', 'capri', 'mtr_dd_target_rules.pct: percent of the scheme'),
  ('pol_mtr_dd_target_rules', 'from_year', NULL, 'open', 'mtr_dd_target_rules.from_year: a calendar year');

-- file: capri_data/2017/policy/mtr_dd_nuts.csv
CREATE TABLE pol_mtr_dd_nuts (
    line BIGINT NOT NULL,
    region VARCHAR NOT NULL,
    "level" DOUBLE NOT NULL,
    PRIMARY KEY (line, region)
);
COMMENT ON TABLE pol_mtr_dd_nuts IS 'p_premToDDTargetNuts of mtr_until2013.gms: the regional flat rate''s NUTS level (0 the member state, 1 NUTS 1), the declaration''s data and the assignments, by line (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_dd_nuts', 'line', NULL, 'open', 'mtr_dd_nuts.line: a line number of the GAMS file'),
  ('pol_mtr_dd_nuts', 'level', NULL, 'open', 'mtr_dd_nuts.level: a NUTS level');

-- file: capri_data/2017/policy/mtr_modulation.csv
CREATE TABLE pol_mtr_modulation (
    "group" VARCHAR NOT NULL,
    class VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    pct DOUBLE NOT NULL,
    PRIMARY KEY ("group", class, region)
);
COMMENT ON TABLE pol_mtr_modulation IS 'TABLE p_percAffByModulation of mtr_until2013.gms: the percentage of farms by producer group and size class of the modulation cut (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_modulation', 'pct', 'U_percent', 'capri', 'mtr_modulation.pct: percent of the farms');

-- file: capri_data/2017/policy/mtr_modulation_classes.csv
CREATE TABLE pol_mtr_modulation_classes (
    class VARCHAR PRIMARY KEY,
    share DOUBLE NOT NULL
);
COMMENT ON TABLE pol_mtr_modulation_classes IS 'Prem_Mod of mtr_until2013.gms: the modulation of each size class (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_modulation_classes', 'share', 'U_ratio', 'capri', 'mtr_modulation_classes.share: share of the payments');

-- file: capri_data/2017/policy/mtr_sets.csv
CREATE TABLE pol_mtr_sets (
    "set" VARCHAR NOT NULL,
    member VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY ("set", member)
);
COMMENT ON TABLE pol_mtr_sets IS 'The sets the MTR port needs: PSDPAY_MTR_EL with mtr_until2013.gms''s additions, DPAgEu10, PSGG_TO_P (group|scheme), TRDWHE_REG, PSDPAY_MTR, PSGROUP, DDTarget (tools/build/build_mtr_inputs.py)';

-- file: capri_data/2017/policy/mtr_base_data.csv
CREATE TABLE pol_mtr_base_data (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    "column" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, item, "column")
);
COMMENT ON TABLE pol_mtr_base_data IS 'sim_ini_21730''s DATA the MTR port evaluates the premiums at: levels (BAS, TRD), the main yields (YILD) and young animals'' inputs (SLGT) at BAS, the historical yields (HSTY) and the milk quota (QUTS COMI) by column (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_base_data', 'value', NULL, 'open', 'mtr_base_data.value: by item (1000 ha or heads, kg or t per unit, 1000 t)');

-- file: capri_data/2017/policy/mtr_modif.csv
CREATE TABLE pol_mtr_modif (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    scheme VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, scheme)
);
COMMENT ON TABLE pol_mtr_modif IS 'p_premModifFact of 2030 in sim_ini_21730 above EPS: the Agenda 2000 premiums'' modification factors per activity (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_modif', 'value', 'U_ratio', 'capri', 'mtr_modif.value: factor on the premium');

-- file: capri_data/2017/policy/mtr_lu_units.csv
CREATE TABLE pol_mtr_lu_units (
    activity VARCHAR PRIMARY KEY,
    "value" DOUBLE NOT NULL
);
COMMENT ON TABLE pol_mtr_lu_units IS 'p_LUUnits of sim_ini_21730: livestock units per head, for the premiums per livestock unit (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_lu_units', 'value', NULL, 'open', 'mtr_lu_units.value: livestock units per head');

-- file: capri_data/2017/policy/mtr_rules.csv
CREATE TABLE pol_mtr_rules (
    line BIGINT PRIMARY KEY,
    rule VARCHAR NOT NULL,
    labels VARCHAR,
    rhs VARCHAR NOT NULL,
    numbers VARCHAR,
    statement VARCHAR NOT NULL
);
COMMENT ON TABLE pol_mtr_rules IS 'The assignments of mtr_until2013.gms that capri_mod/policy/mtr.py executes as rules: the rule and the statement''s quoted labels, right-hand side and numbers (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_rules', 'line', NULL, 'open', 'mtr_rules.line: a line number of the GAMS file');

-- file: capri_data/2017/policy/mtr_settings.csv
CREATE TABLE pol_mtr_settings (
    item VARCHAR PRIMARY KEY,
    "value" DOUBLE NOT NULL,
    source VARCHAR NOT NULL
);
COMMENT ON TABLE pol_mtr_settings IS 'The MTR port''s years: CAPRI''s year set, %endofMTR%, the coupling''s and decoupling targets'' first years, the years EU025000''s and EU027000''s declarations reach the member states (tools/build/build_mtr_inputs.py)';
INSERT INTO value_units VALUES
  ('pol_mtr_settings', 'value', NULL, 'open', 'mtr_settings.value: a calendar year');

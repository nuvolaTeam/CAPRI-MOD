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

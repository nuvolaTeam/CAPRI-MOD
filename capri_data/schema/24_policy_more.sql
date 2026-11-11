-- Inputs under capri_data/2017/policy. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/baselines/capri_greendeal_ref/2017_2030/policy/cap_ceilings_2030.csv
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

-- file: capri_data/baselines/capri_greendeal_ref/2017_2030/policy/premium_scheme_shares_2030.csv
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

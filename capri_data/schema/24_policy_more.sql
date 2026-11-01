-- Inputs under capri_data/2017/policy. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/2017/policy/cap_ceilings_2030.csv
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

-- file: capri_data/2017/policy/capri_baseline_surplus_2030.csv
CREATE TABLE pol_capri_baseline_surplus_2030 (
    region VARCHAR NOT NULL,
    surplus_kg_n_per_ha DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, source)
);
COMMENT ON TABLE pol_capri_baseline_surplus_2030 IS 'CAPRI''s own baseline gross N surplus per ha (2030 reference), per model region: the starting point (tools/build/build_capri_baseline_surplus.py)';
INSERT INTO value_units VALUES
  ('pol_capri_baseline_surplus_2030', 'surplus_kg_n_per_ha', NULL, 'open', 'capri_baseline_surplus_2030.surplus_kg_n_per_ha: unit to be established');

-- file: capri_data/2017/policy/mineral_redu_exemptions.csv
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

-- file: capri_data/2017/policy/mineral_redu_limcres.csv
CREATE TABLE pol_mineral_redu_limcres (
    capri_region VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    add DOUBLE NOT NULL,
    after_year BIGINT NOT NULL,
    PRIMARY KEY (capri_region, ngrp)
);
COMMENT ON TABLE pol_mineral_redu_limcres IS 'CAPRI''s exemptions in the crop-specific mineral fertiliser reduction (pol_input/greendeal/minfert_redu_by_crop.gms). (tools/build/build_mineral_redu_rules.py)';
INSERT INTO value_units VALUES
  ('pol_mineral_redu_limcres', 'add', NULL, 'open', 'mineral_redu_limcres.add: unit to be established'),
  ('pol_mineral_redu_limcres', 'after_year', NULL, 'open', 'mineral_redu_limcres.after_year: unit to be established');

-- file: capri_data/2017/policy/premium_scheme_shares_2030.csv
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

-- file: capri_data/2017/policy/tariffs.csv
CREATE TABLE pol_tariffs (
    region VARCHAR NOT NULL,
    SWHE DOUBLE NOT NULL,
    DWHE DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    CORN DOUBLE NOT NULL,
    OCER DOUBLE NOT NULL,
    RAPE DOUBLE NOT NULL,
    SUNF DOUBLE NOT NULL,
    SOYA DOUBLE NOT NULL,
    OOIL DOUBLE NOT NULL,
    SUGB DOUBLE NOT NULL,
    SUGR DOUBLE NOT NULL,
    POTA DOUBLE NOT NULL,
    PULS DOUBLE NOT NULL,
    TOMA DOUBLE NOT NULL,
    OVEG DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    CITR DOUBLE NOT NULL,
    WINE DOUBLE NOT NULL,
    OLIV DOUBLE NOT NULL,
    MILK DOUBLE NOT NULL,
    BUTR DOUBLE NOT NULL,
    SKIM DOUBLE NOT NULL,
    CHES DOUBLE NOT NULL,
    WHEY DOUBLE NOT NULL,
    BEEF DOUBLE NOT NULL,
    PORK DOUBLE NOT NULL,
    POUL DOUBLE NOT NULL,
    SGMT DOUBLE NOT NULL,
    EGGS DOUBLE NOT NULL,
    FATS DOUBLE NOT NULL,
    OFOD_M DOUBLE NOT NULL,
    RAPO DOUBLE NOT NULL,
    SUNO DOUBLE NOT NULL,
    SOYO DOUBLE NOT NULL,
    RAPC DOUBLE NOT NULL,
    SUNC DOUBLE NOT NULL,
    SOYC DOUBLE NOT NULL,
    RYEM DOUBLE NOT NULL,
    OATS DOUBLE NOT NULL,
    TAGR DOUBLE NOT NULL,
    TOBA DOUBLE NOT NULL,
    TABO DOUBLE NOT NULL,
    TEXT DOUBLE NOT NULL,
    PLMO DOUBLE NOT NULL,
    OTHO DOUBLE NOT NULL,
    FFIS DOUBLE NOT NULL,
    SFIS DOUBLE NOT NULL,
    OAQU DOUBLE NOT NULL,
    COFF DOUBLE NOT NULL,
    TEAS DOUBLE NOT NULL,
    COCO DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE pol_tariffs IS 'Import protection per trade region and commodity from CAPRI''s 2017 market results (Sprint 9r). (tools/build/build_tariffs_2017.py)';
INSERT INTO value_units VALUES
  ('pol_tariffs', 'SWHE', NULL, 'open', 'tariffs.SWHE: unit to be established'),
  ('pol_tariffs', 'DWHE', NULL, 'open', 'tariffs.DWHE: unit to be established'),
  ('pol_tariffs', 'BARL', NULL, 'open', 'tariffs.BARL: unit to be established'),
  ('pol_tariffs', 'CORN', NULL, 'open', 'tariffs.CORN: unit to be established'),
  ('pol_tariffs', 'OCER', NULL, 'open', 'tariffs.OCER: unit to be established'),
  ('pol_tariffs', 'RAPE', NULL, 'open', 'tariffs.RAPE: unit to be established'),
  ('pol_tariffs', 'SUNF', NULL, 'open', 'tariffs.SUNF: unit to be established'),
  ('pol_tariffs', 'SOYA', NULL, 'open', 'tariffs.SOYA: unit to be established'),
  ('pol_tariffs', 'OOIL', NULL, 'open', 'tariffs.OOIL: unit to be established'),
  ('pol_tariffs', 'SUGB', NULL, 'open', 'tariffs.SUGB: unit to be established'),
  ('pol_tariffs', 'SUGR', NULL, 'open', 'tariffs.SUGR: unit to be established'),
  ('pol_tariffs', 'POTA', NULL, 'open', 'tariffs.POTA: unit to be established'),
  ('pol_tariffs', 'PULS', NULL, 'open', 'tariffs.PULS: unit to be established'),
  ('pol_tariffs', 'TOMA', NULL, 'open', 'tariffs.TOMA: unit to be established'),
  ('pol_tariffs', 'OVEG', NULL, 'open', 'tariffs.OVEG: unit to be established'),
  ('pol_tariffs', 'APPL', NULL, 'open', 'tariffs.APPL: unit to be established'),
  ('pol_tariffs', 'OFRU', NULL, 'open', 'tariffs.OFRU: unit to be established'),
  ('pol_tariffs', 'CITR', NULL, 'open', 'tariffs.CITR: unit to be established'),
  ('pol_tariffs', 'WINE', NULL, 'open', 'tariffs.WINE: unit to be established'),
  ('pol_tariffs', 'OLIV', NULL, 'open', 'tariffs.OLIV: unit to be established'),
  ('pol_tariffs', 'MILK', NULL, 'open', 'tariffs.MILK: unit to be established'),
  ('pol_tariffs', 'BUTR', NULL, 'open', 'tariffs.BUTR: unit to be established'),
  ('pol_tariffs', 'SKIM', NULL, 'open', 'tariffs.SKIM: unit to be established'),
  ('pol_tariffs', 'CHES', NULL, 'open', 'tariffs.CHES: unit to be established'),
  ('pol_tariffs', 'WHEY', NULL, 'open', 'tariffs.WHEY: unit to be established'),
  ('pol_tariffs', 'BEEF', NULL, 'open', 'tariffs.BEEF: unit to be established'),
  ('pol_tariffs', 'PORK', NULL, 'open', 'tariffs.PORK: unit to be established'),
  ('pol_tariffs', 'POUL', NULL, 'open', 'tariffs.POUL: unit to be established'),
  ('pol_tariffs', 'SGMT', NULL, 'open', 'tariffs.SGMT: unit to be established'),
  ('pol_tariffs', 'EGGS', NULL, 'open', 'tariffs.EGGS: unit to be established'),
  ('pol_tariffs', 'FATS', NULL, 'open', 'tariffs.FATS: unit to be established'),
  ('pol_tariffs', 'OFOD_M', NULL, 'open', 'tariffs.OFOD_M: unit to be established'),
  ('pol_tariffs', 'RAPO', NULL, 'open', 'tariffs.RAPO: unit to be established'),
  ('pol_tariffs', 'SUNO', NULL, 'open', 'tariffs.SUNO: unit to be established'),
  ('pol_tariffs', 'SOYO', NULL, 'open', 'tariffs.SOYO: unit to be established'),
  ('pol_tariffs', 'RAPC', NULL, 'open', 'tariffs.RAPC: unit to be established'),
  ('pol_tariffs', 'SUNC', NULL, 'open', 'tariffs.SUNC: unit to be established'),
  ('pol_tariffs', 'SOYC', NULL, 'open', 'tariffs.SOYC: unit to be established'),
  ('pol_tariffs', 'RYEM', NULL, 'open', 'tariffs.RYEM: unit to be established'),
  ('pol_tariffs', 'OATS', NULL, 'open', 'tariffs.OATS: unit to be established'),
  ('pol_tariffs', 'TAGR', NULL, 'open', 'tariffs.TAGR: unit to be established'),
  ('pol_tariffs', 'TOBA', NULL, 'open', 'tariffs.TOBA: unit to be established'),
  ('pol_tariffs', 'TABO', NULL, 'open', 'tariffs.TABO: unit to be established'),
  ('pol_tariffs', 'TEXT', NULL, 'open', 'tariffs.TEXT: unit to be established'),
  ('pol_tariffs', 'PLMO', NULL, 'open', 'tariffs.PLMO: unit to be established'),
  ('pol_tariffs', 'OTHO', NULL, 'open', 'tariffs.OTHO: unit to be established'),
  ('pol_tariffs', 'FFIS', NULL, 'open', 'tariffs.FFIS: unit to be established'),
  ('pol_tariffs', 'SFIS', NULL, 'open', 'tariffs.SFIS: unit to be established'),
  ('pol_tariffs', 'OAQU', NULL, 'open', 'tariffs.OAQU: unit to be established'),
  ('pol_tariffs', 'COFF', NULL, 'open', 'tariffs.COFF: unit to be established'),
  ('pol_tariffs', 'TEAS', NULL, 'open', 'tariffs.TEAS: unit to be established'),
  ('pol_tariffs', 'COCO', NULL, 'open', 'tariffs.COCO: unit to be established');

INSERT INTO value_units VALUES ('pol_mineral_redu_exemptions', 'after_year', NULL, 'open', 'a calendar year (part of the key), no unit');

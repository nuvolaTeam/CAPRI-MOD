-- The supply models' remaining 2017 inputs (capri_data/2017/supply). Generated structure (types, NOT NULL, keys) from
-- the files on 29 October 2026; units open where no builder or CAPRI file states them (value_units).

-- file: capri_data/2017/supply/cattle_intensity.csv
CREATE TABLE sup_cattle_intensity (
    region VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    share_low DOUBLE NOT NULL,
    share_high DOUBLE NOT NULL,
    days_low DOUBLE NOT NULL,
    days_high DOUBLE NOT NULL,
    dmann_rel DOUBLE NOT NULL,
    dbeef_rel DOUBLE NOT NULL,
    dyoung_rel DOUBLE NOT NULL,
    denne_rel DOUBLE NOT NULL,
    dcrpr_rel DOUBLE NOT NULL,
    ddrmn_rel DOUBLE NOT NULL,
    ddrmx_rel DOUBLE NOT NULL,
    q_z DOUBLE NOT NULL,
    q_source VARCHAR NOT NULL,
    heads DOUBLE NOT NULL,
    q_b DOUBLE NOT NULL,
    split VARCHAR NOT NULL,
    member_low VARCHAR NOT NULL,
    member_high VARCHAR NOT NULL,
    dprod_young_m_rel DOUBLE NOT NULL,
    dprod_young_f_rel DOUBLE NOT NULL,
    dprod_cows_rel DOUBLE NOT NULL,
    duse_calves_m_rel DOUBLE NOT NULL,
    duse_calves_f_rel DOUBLE NOT NULL,
    duse_young_m_rel DOUBLE NOT NULL,
    duse_young_f_rel DOUBLE NOT NULL,
    q_z_capri2030 DOUBLE NOT NULL,
    q_source_capri2030 VARCHAR NOT NULL,
    q_b_capri2030 DOUBLE NOT NULL,
    q_z_recipe2030 DOUBLE NOT NULL,
    q_source_recipe2030 VARCHAR NOT NULL,
    q_b_recipe2030 DOUBLE NOT NULL,
    dmanp_rel DOUBLE NOT NULL,
    dmank_rel DOUBLE NOT NULL,
    share_low_2030 DOUBLE,
    share_high_2030 DOUBLE,
    days_low_2030 DOUBLE,
    days_high_2030 DOUBLE,
    dmann_rel_2030 DOUBLE,
    dmanp_rel_2030 DOUBLE,
    dmank_rel_2030 DOUBLE,
    dbeef_rel_2030 DOUBLE,
    dyoung_rel_2030 DOUBLE,
    denne_rel_2030 DOUBLE,
    dcrpr_rel_2030 DOUBLE,
    ddrmn_rel_2030 DOUBLE,
    ddrmx_rel_2030 DOUBLE,
    dprod_young_m_rel_2030 DOUBLE,
    dprod_young_f_rel_2030 DOUBLE,
    dprod_cows_rel_2030 DOUBLE,
    duse_calves_m_rel_2030 DOUBLE,
    duse_calves_f_rel_2030 DOUBLE,
    duse_young_m_rel_2030 DOUBLE,
    duse_young_f_rel_2030 DOUBLE,
    PRIMARY KEY (region, animal, capri_region, q_source, split, member_low, member_high, q_source_capri2030, q_source_recipe2030)
);
COMMENT ON TABLE sup_cattle_intensity IS 'CAPRI''s two-intensity cattle fattening activities, per model region: bulls BULL/BULH and fattening (tools/build/build_cattle_intensity.py)';
INSERT INTO value_units VALUES
  ('sup_cattle_intensity', 'share_low', NULL, 'open', 'cattle_intensity.share_low: unit to be established'),
  ('sup_cattle_intensity', 'share_high', NULL, 'open', 'cattle_intensity.share_high: unit to be established'),
  ('sup_cattle_intensity', 'days_low', NULL, 'open', 'cattle_intensity.days_low: unit to be established'),
  ('sup_cattle_intensity', 'days_high', NULL, 'open', 'cattle_intensity.days_high: unit to be established'),
  ('sup_cattle_intensity', 'dmann_rel', NULL, 'open', 'cattle_intensity.dmann_rel: unit to be established'),
  ('sup_cattle_intensity', 'dbeef_rel', NULL, 'open', 'cattle_intensity.dbeef_rel: unit to be established'),
  ('sup_cattle_intensity', 'dyoung_rel', NULL, 'open', 'cattle_intensity.dyoung_rel: unit to be established'),
  ('sup_cattle_intensity', 'denne_rel', NULL, 'open', 'cattle_intensity.denne_rel: unit to be established'),
  ('sup_cattle_intensity', 'dcrpr_rel', NULL, 'open', 'cattle_intensity.dcrpr_rel: unit to be established'),
  ('sup_cattle_intensity', 'ddrmn_rel', NULL, 'open', 'cattle_intensity.ddrmn_rel: unit to be established'),
  ('sup_cattle_intensity', 'ddrmx_rel', NULL, 'open', 'cattle_intensity.ddrmx_rel: unit to be established'),
  ('sup_cattle_intensity', 'q_z', NULL, 'open', 'cattle_intensity.q_z: unit to be established'),
  ('sup_cattle_intensity', 'heads', NULL, 'open', 'cattle_intensity.heads: unit to be established'),
  ('sup_cattle_intensity', 'q_b', NULL, 'open', 'cattle_intensity.q_b: unit to be established'),
  ('sup_cattle_intensity', 'dprod_young_m_rel', NULL, 'open', 'cattle_intensity.dprod_young_m_rel: unit to be established'),
  ('sup_cattle_intensity', 'dprod_young_f_rel', NULL, 'open', 'cattle_intensity.dprod_young_f_rel: unit to be established'),
  ('sup_cattle_intensity', 'dprod_cows_rel', NULL, 'open', 'cattle_intensity.dprod_cows_rel: unit to be established'),
  ('sup_cattle_intensity', 'duse_calves_m_rel', NULL, 'open', 'cattle_intensity.duse_calves_m_rel: unit to be established'),
  ('sup_cattle_intensity', 'duse_calves_f_rel', NULL, 'open', 'cattle_intensity.duse_calves_f_rel: unit to be established'),
  ('sup_cattle_intensity', 'duse_young_m_rel', NULL, 'open', 'cattle_intensity.duse_young_m_rel: unit to be established'),
  ('sup_cattle_intensity', 'duse_young_f_rel', NULL, 'open', 'cattle_intensity.duse_young_f_rel: unit to be established'),
  ('sup_cattle_intensity', 'q_z_capri2030', NULL, 'open', 'cattle_intensity.q_z_capri2030: unit to be established'),
  ('sup_cattle_intensity', 'q_b_capri2030', NULL, 'open', 'cattle_intensity.q_b_capri2030: unit to be established'),
  ('sup_cattle_intensity', 'q_z_recipe2030', NULL, 'open', 'cattle_intensity.q_z_recipe2030: unit to be established'),
  ('sup_cattle_intensity', 'q_b_recipe2030', NULL, 'open', 'cattle_intensity.q_b_recipe2030: unit to be established'),
  ('sup_cattle_intensity', 'dmanp_rel', NULL, 'open', 'cattle_intensity.dmanp_rel: manure P2O5 / K2O per head, low - high over the animal''s average (CAPRI MANP / MANK)'),
  ('sup_cattle_intensity', 'dmank_rel', NULL, 'open', 'cattle_intensity.dmank_rel: manure P2O5 / K2O per head, low - high over the animal''s average (CAPRI MANP / MANK)'),
  ('sup_cattle_intensity', 'share_low_2030', NULL, 'open', 'cattle_intensity.share_low_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'share_high_2030', NULL, 'open', 'cattle_intensity.share_high_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'days_low_2030', NULL, 'open', 'cattle_intensity.days_low_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'days_high_2030', NULL, 'open', 'cattle_intensity.days_high_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dmann_rel_2030', NULL, 'open', 'cattle_intensity.dmann_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dmanp_rel_2030', NULL, 'open', 'cattle_intensity.dmanp_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dmank_rel_2030', NULL, 'open', 'cattle_intensity.dmank_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dbeef_rel_2030', NULL, 'open', 'cattle_intensity.dbeef_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dyoung_rel_2030', NULL, 'open', 'cattle_intensity.dyoung_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'denne_rel_2030', NULL, 'open', 'cattle_intensity.denne_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dcrpr_rel_2030', NULL, 'open', 'cattle_intensity.dcrpr_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'ddrmn_rel_2030', NULL, 'open', 'cattle_intensity.ddrmn_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'ddrmx_rel_2030', NULL, 'open', 'cattle_intensity.ddrmx_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dprod_young_m_rel_2030', NULL, 'open', 'cattle_intensity.dprod_young_m_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dprod_young_f_rel_2030', NULL, 'open', 'cattle_intensity.dprod_young_f_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'dprod_cows_rel_2030', NULL, 'open', 'cattle_intensity.dprod_cows_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'duse_calves_m_rel_2030', NULL, 'open', 'cattle_intensity.duse_calves_m_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'duse_calves_f_rel_2030', NULL, 'open', 'cattle_intensity.duse_calves_f_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'duse_young_m_rel_2030', NULL, 'open', 'cattle_intensity.duse_young_m_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_cattle_intensity', 'duse_young_f_rel_2030', NULL, 'open', 'cattle_intensity.duse_young_f_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)');

-- file: capri_data/2017/supply/cover_crops.csv
CREATE TABLE sup_cover_crops (
    region VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    catc_share_2030 DOUBLE NOT NULL,
    catc_cost_eur_ha DOUBLE NOT NULL,
    cost_source VARCHAR NOT NULL CHECK (cost_source IN ('baseline', 'calibration')),
    biofix_t_n_ha DOUBLE,
    PRIMARY KEY (region, capri_region)
);
COMMENT ON TABLE sup_cover_crops IS 'CAPRI''s winter cover (catch) crops, CATC, per model region: 2030 level, cost, N fixation, winter cover shares. (tools/build/build_cover_crops.py)';
INSERT INTO value_units VALUES
  ('sup_cover_crops', 'catc_share_2030', NULL, 'open', 'cover_crops.catc_share_2030: unit to be established'),
  ('sup_cover_crops', 'catc_cost_eur_ha', NULL, 'open', 'cover_crops.catc_cost_eur_ha: unit to be established'),
  ('sup_cover_crops', 'biofix_t_n_ha', NULL, 'open', 'cover_crops.biofix_t_n_ha: unit to be established');

-- file: capri_data/2017/supply/crop_cost_shares.csv
CREATE TABLE sup_crop_cost_shares (
    crop VARCHAR NOT NULL,
    fert_cost_share DOUBLE NOT NULL,
    PRIMARY KEY (crop)
);
COMMENT ON TABLE sup_crop_cost_shares IS 'EU-wide share of fertiliser in a crop''s input cost, from CAPRI''s 2017 results (K31). (tools/build/build_crop_cost_shares.py)';
INSERT INTO value_units VALUES
  ('sup_crop_cost_shares', 'fert_cost_share', NULL, 'open', 'crop_cost_shares.fert_cost_share: unit to be established');

-- file: capri_data/2017/supply/crop_premium.csv
CREATE TABLE sup_crop_premium (
    region VARCHAR NOT NULL,
    SWHE DOUBLE NOT NULL,
    DWHE DOUBLE NOT NULL,
    RYEM DOUBLE NOT NULL,
    BARL DOUBLE NOT NULL,
    OATS DOUBLE NOT NULL,
    CORN DOUBLE NOT NULL,
    OCER DOUBLE NOT NULL,
    PARI DOUBLE NOT NULL,
    OCRO DOUBLE NOT NULL,
    OIND DOUBLE NOT NULL,
    NURS DOUBLE NOT NULL,
    FLOW DOUBLE NOT NULL,
    POTA DOUBLE NOT NULL,
    SUGB DOUBLE NOT NULL,
    SUNF DOUBLE NOT NULL,
    RAPE DOUBLE NOT NULL,
    SOYA DOUBLE NOT NULL,
    OOIL DOUBLE NOT NULL,
    PULS DOUBLE NOT NULL,
    TOMA DOUBLE NOT NULL,
    OVEG DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    CITR DOUBLE NOT NULL,
    TAGR DOUBLE NOT NULL,
    WINE DOUBLE NOT NULL,
    OLIV DOUBLE NOT NULL,
    TABO DOUBLE NOT NULL,
    TOBA DOUBLE NOT NULL,
    TEXT DOUBLE NOT NULL,
    GRAE DOUBLE NOT NULL,
    GRAI DOUBLE NOT NULL,
    MAIF DOUBLE NOT NULL,
    OFAR DOUBLE NOT NULL,
    ROOF DOUBLE NOT NULL,
    VSET DOUBLE NOT NULL,
    FALL DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE sup_crop_premium IS 'Crop yields, producer prices, input costs and CAP premiums for every model region from CAPRI''s 2017 results (tools/build/build_crop_economics_2017.py)';
INSERT INTO value_units VALUES
  ('sup_crop_premium', 'SWHE', NULL, 'open', 'crop_premium.SWHE: unit to be established'),
  ('sup_crop_premium', 'DWHE', NULL, 'open', 'crop_premium.DWHE: unit to be established'),
  ('sup_crop_premium', 'RYEM', NULL, 'open', 'crop_premium.RYEM: unit to be established'),
  ('sup_crop_premium', 'BARL', NULL, 'open', 'crop_premium.BARL: unit to be established'),
  ('sup_crop_premium', 'OATS', NULL, 'open', 'crop_premium.OATS: unit to be established'),
  ('sup_crop_premium', 'CORN', NULL, 'open', 'crop_premium.CORN: unit to be established'),
  ('sup_crop_premium', 'OCER', NULL, 'open', 'crop_premium.OCER: unit to be established'),
  ('sup_crop_premium', 'PARI', NULL, 'open', 'crop_premium.PARI: unit to be established'),
  ('sup_crop_premium', 'PULS', NULL, 'open', 'crop_premium.PULS: unit to be established'),
  ('sup_crop_premium', 'OCRO', NULL, 'open', 'crop_premium.OCRO: unit to be established'),
  ('sup_crop_premium', 'OIND', NULL, 'open', 'crop_premium.OIND: unit to be established'),
  ('sup_crop_premium', 'NURS', NULL, 'open', 'crop_premium.NURS: unit to be established'),
  ('sup_crop_premium', 'FLOW', NULL, 'open', 'crop_premium.FLOW: unit to be established'),
  ('sup_crop_premium', 'SUGB', NULL, 'open', 'crop_premium.SUGB: unit to be established'),
  ('sup_crop_premium', 'POTA', NULL, 'open', 'crop_premium.POTA: unit to be established'),
  ('sup_crop_premium', 'TOMA', NULL, 'open', 'crop_premium.TOMA: unit to be established'),
  ('sup_crop_premium', 'OVEG', NULL, 'open', 'crop_premium.OVEG: unit to be established'),
  ('sup_crop_premium', 'APPL', NULL, 'open', 'crop_premium.APPL: unit to be established'),
  ('sup_crop_premium', 'OFRU', NULL, 'open', 'crop_premium.OFRU: unit to be established'),
  ('sup_crop_premium', 'CITR', NULL, 'open', 'crop_premium.CITR: unit to be established'),
  ('sup_crop_premium', 'TAGR', NULL, 'open', 'crop_premium.TAGR: unit to be established'),
  ('sup_crop_premium', 'WINE', NULL, 'open', 'crop_premium.WINE: unit to be established'),
  ('sup_crop_premium', 'OLIV', NULL, 'open', 'crop_premium.OLIV: unit to be established'),
  ('sup_crop_premium', 'TABO', NULL, 'open', 'crop_premium.TABO: unit to be established'),
  ('sup_crop_premium', 'GRAE', NULL, 'open', 'crop_premium.GRAE: unit to be established'),
  ('sup_crop_premium', 'GRAI', NULL, 'open', 'crop_premium.GRAI: unit to be established'),
  ('sup_crop_premium', 'TOBA', NULL, 'open', 'crop_premium.TOBA: unit to be established'),
  ('sup_crop_premium', 'MAIF', NULL, 'open', 'crop_premium.MAIF: unit to be established'),
  ('sup_crop_premium', 'RAPE', NULL, 'open', 'crop_premium.RAPE: unit to be established'),
  ('sup_crop_premium', 'SUNF', NULL, 'open', 'crop_premium.SUNF: unit to be established'),
  ('sup_crop_premium', 'SOYA', NULL, 'open', 'crop_premium.SOYA: unit to be established'),
  ('sup_crop_premium', 'OOIL', NULL, 'open', 'crop_premium.OOIL: unit to be established'),
  ('sup_crop_premium', 'TEXT', NULL, 'open', 'crop_premium.TEXT: unit to be established'),
  ('sup_crop_premium', 'OFAR', NULL, 'open', 'crop_premium.OFAR: unit to be established'),
  ('sup_crop_premium', 'ROOF', NULL, 'open', 'crop_premium.ROOF: unit to be established'),
  ('sup_crop_premium', 'VSET', NULL, 'open', 'crop_premium.VSET: unit to be established'),
  ('sup_crop_premium', 'FALL', NULL, 'open', 'crop_premium.FALL: unit to be established');

-- file: capri_data/2017/supply/dairy_intensity.csv
CREATE TABLE sup_dairy_intensity (
    region VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    share_low DOUBLE NOT NULL,
    dcomi_rel DOUBLE NOT NULL,
    dmann_rel DOUBLE NOT NULL,
    denne_rel DOUBLE NOT NULL,
    dcrpr_rel DOUBLE NOT NULL,
    ddrmn_rel DOUBLE NOT NULL,
    ddrmx_rel DOUBLE NOT NULL,
    heads_low DOUBLE NOT NULL,
    heads_high DOUBLE NOT NULL,
    q_low DOUBLE NOT NULL,
    q_high DOUBLE NOT NULL,
    q_source VARCHAR NOT NULL,
    q_low_capri2030 DOUBLE NOT NULL,
    q_high_capri2030 DOUBLE NOT NULL,
    q_source_capri2030 VARCHAR NOT NULL,
    q_low_recipe2030 DOUBLE NOT NULL,
    q_high_recipe2030 DOUBLE NOT NULL,
    q_source_recipe2030 VARCHAR NOT NULL,
    dmanp_rel DOUBLE NOT NULL,
    dmank_rel DOUBLE NOT NULL,
    share_low_2030 DOUBLE NOT NULL,
    dcomi_rel_2030 DOUBLE NOT NULL,
    dmann_rel_2030 DOUBLE NOT NULL,
    dmanp_rel_2030 DOUBLE NOT NULL,
    dmank_rel_2030 DOUBLE NOT NULL,
    denne_rel_2030 DOUBLE NOT NULL,
    dcrpr_rel_2030 DOUBLE NOT NULL,
    ddrmn_rel_2030 DOUBLE NOT NULL,
    ddrmx_rel_2030 DOUBLE NOT NULL,
    PRIMARY KEY (region, capri_region, q_source, q_source_capri2030, q_source_recipe2030)
);
COMMENT ON TABLE sup_dairy_intensity IS 'CAPRI''s two dairy-cow activities, low-yield DCOL and high-yield DCOH, per model region. (tools/build/build_dairy_intensity.py)';
INSERT INTO value_units VALUES
  ('sup_dairy_intensity', 'share_low', NULL, 'open', 'dairy_intensity.share_low: unit to be established'),
  ('sup_dairy_intensity', 'dcomi_rel', NULL, 'open', 'dairy_intensity.dcomi_rel: unit to be established'),
  ('sup_dairy_intensity', 'dmann_rel', NULL, 'open', 'dairy_intensity.dmann_rel: unit to be established'),
  ('sup_dairy_intensity', 'denne_rel', NULL, 'open', 'dairy_intensity.denne_rel: unit to be established'),
  ('sup_dairy_intensity', 'dcrpr_rel', NULL, 'open', 'dairy_intensity.dcrpr_rel: unit to be established'),
  ('sup_dairy_intensity', 'ddrmn_rel', NULL, 'open', 'dairy_intensity.ddrmn_rel: unit to be established'),
  ('sup_dairy_intensity', 'ddrmx_rel', NULL, 'open', 'dairy_intensity.ddrmx_rel: unit to be established'),
  ('sup_dairy_intensity', 'heads_low', NULL, 'open', 'dairy_intensity.heads_low: unit to be established'),
  ('sup_dairy_intensity', 'heads_high', NULL, 'open', 'dairy_intensity.heads_high: unit to be established'),
  ('sup_dairy_intensity', 'q_low', NULL, 'open', 'dairy_intensity.q_low: unit to be established'),
  ('sup_dairy_intensity', 'q_high', NULL, 'open', 'dairy_intensity.q_high: unit to be established'),
  ('sup_dairy_intensity', 'q_low_capri2030', NULL, 'open', 'dairy_intensity.q_low_capri2030: unit to be established'),
  ('sup_dairy_intensity', 'q_high_capri2030', NULL, 'open', 'dairy_intensity.q_high_capri2030: unit to be established'),
  ('sup_dairy_intensity', 'q_low_recipe2030', NULL, 'open', 'dairy_intensity.q_low_recipe2030: unit to be established'),
  ('sup_dairy_intensity', 'q_high_recipe2030', NULL, 'open', 'dairy_intensity.q_high_recipe2030: unit to be established'),
  ('sup_dairy_intensity', 'dmanp_rel', NULL, 'open', 'dairy_intensity.dmanp_rel: manure P2O5 / K2O per head, low - high over the animal''s average (CAPRI MANP / MANK)'),
  ('sup_dairy_intensity', 'dmank_rel', NULL, 'open', 'dairy_intensity.dmank_rel: manure P2O5 / K2O per head, low - high over the animal''s average (CAPRI MANP / MANK)'),
  ('sup_dairy_intensity', 'share_low_2030', NULL, 'open', 'dairy_intensity.share_low_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'dcomi_rel_2030', NULL, 'open', 'dairy_intensity.dcomi_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'dmann_rel_2030', NULL, 'open', 'dairy_intensity.dmann_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'dmanp_rel_2030', NULL, 'open', 'dairy_intensity.dmanp_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'dmank_rel_2030', NULL, 'open', 'dairy_intensity.dmank_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'denne_rel_2030', NULL, 'open', 'dairy_intensity.denne_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'dcrpr_rel_2030', NULL, 'open', 'dairy_intensity.dcrpr_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'ddrmn_rel_2030', NULL, 'open', 'dairy_intensity.ddrmn_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)'),
  ('sup_dairy_intensity', 'ddrmx_rel_2030', NULL, 'open', 'dairy_intensity.ddrmx_rel_2030: the column at CAPRI''s 2030 Green Deal baseline (res_2_1730greendeal_refdefaulta)');

-- file: capri_data/2017/supply/grass_dm_content.csv
CREATE TABLE sup_grass_dm_content (
    region VARCHAR NOT NULL,
    drma DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE sup_grass_dm_content IS 'Crop yields, producer prices, input costs and CAP premiums for every model region from CAPRI''s 2017 results (tools/build/build_crop_economics_2017.py)';
INSERT INTO value_units VALUES
  ('sup_grass_dm_content', 'drma', NULL, 'open', 'grass_dm_content.drma: unit to be established');

-- file: capri_data/2017/supply/labour_coef.csv
CREATE TABLE sup_labour_coef (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    labt DOUBLE NOT NULL,
    labf DOUBLE NOT NULL,
    labp DOUBLE NOT NULL,
    capri_region VARCHAR NOT NULL,
    labt_2030 DOUBLE,
    labf_2030 DOUBLE,
    labp_2030 DOUBLE,
    capri_region_2030 VARCHAR NOT NULL,
    PRIMARY KEY (region, activity, capri_region, capri_region_2030)
);
COMMENT ON TABLE sup_labour_coef IS 'CAPRI''s labour accounts and its two set-aside activities, per model region (22 October 2026, the project lead''s (tools/build/build_labour_setaside.py)';
INSERT INTO value_units VALUES
  ('sup_labour_coef', 'labt', NULL, 'open', 'labour_coef.labt: unit to be established'),
  ('sup_labour_coef', 'labf', NULL, 'open', 'labour_coef.labf: unit to be established'),
  ('sup_labour_coef', 'labp', NULL, 'open', 'labour_coef.labp: unit to be established'),
  ('sup_labour_coef', 'labt_2030', NULL, 'open', 'labour_coef.labt_2030: unit to be established'),
  ('sup_labour_coef', 'labf_2030', NULL, 'open', 'labour_coef.labf_2030: unit to be established'),
  ('sup_labour_coef', 'labp_2030', NULL, 'open', 'labour_coef.labp_2030: unit to be established');

-- file: capri_data/2017/supply/land_market_2017.csv
CREATE TABLE sup_land_market_2017 (
    region VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, row, col)
);
COMMENT ON TABLE sup_land_market_2017 IS 'Build CAPRI''s land-market data per model region (docs/LAND_USE_FLEXIBILITY.md). (tools/build/build_land_market.py)';
INSERT INTO value_units VALUES
  ('sup_land_market_2017', 'value', NULL, 'open', 'land_market_2017.value: unit to be established');

-- file: capri_data/2017/supply/land_market_2017_regions.csv
CREATE TABLE sup_land_market_2017_regions (
    region VARCHAR NOT NULL,
    quad_source VARCHAR NOT NULL,
    share_of_source DOUBLE,
    min_eigenvalue DOUBLE NOT NULL,
    PRIMARY KEY (region, quad_source)
);
COMMENT ON TABLE sup_land_market_2017_regions IS 'Build CAPRI''s land-market data per model region (docs/LAND_USE_FLEXIBILITY.md). (tools/build/build_land_market.py)';
INSERT INTO value_units VALUES
  ('sup_land_market_2017_regions', 'share_of_source', NULL, 'open', 'land_market_2017_regions.share_of_source: unit to be established'),
  ('sup_land_market_2017_regions', 'min_eigenvalue', NULL, 'open', 'land_market_2017_regions.min_eigenvalue: unit to be established');

-- file: capri_data/baselines/capri_greendeal_ref/1730/supply/land_market_2030.csv
CREATE TABLE sup_land_market_2030 (
    region VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, row, col)
);
COMMENT ON TABLE sup_land_market_2030 IS 'Build CAPRI''s land-market data per model region (docs/LAND_USE_FLEXIBILITY.md). (tools/build/build_land_market.py)';
INSERT INTO value_units VALUES
  ('sup_land_market_2030', 'value', NULL, 'open', 'land_market_2030.value: unit to be established');

-- file: capri_data/baselines/capri_greendeal_ref/1730/supply/land_market_2030_regions.csv
CREATE TABLE sup_land_market_2030_regions (
    region VARCHAR NOT NULL,
    quad_source VARCHAR NOT NULL,
    share_of_source DOUBLE,
    min_eigenvalue DOUBLE NOT NULL,
    PRIMARY KEY (region, quad_source)
);
COMMENT ON TABLE sup_land_market_2030_regions IS 'Build CAPRI''s land-market data per model region (docs/LAND_USE_FLEXIBILITY.md). (tools/build/build_land_market.py)';
INSERT INTO value_units VALUES
  ('sup_land_market_2030_regions', 'share_of_source', NULL, 'open', 'land_market_2030_regions.share_of_source: unit to be established'),
  ('sup_land_market_2030_regions', 'min_eigenvalue', NULL, 'open', 'land_market_2030_regions.min_eigenvalue: unit to be established');

-- file: capri_data/2017/supply/nutrients_regional.csv
-- OCER, PULS: empty where CAPRI's data have no record, as this file's other columns (the units of the UK,
-- Turkey and the Western Balkans, 4 November 2026)
CREATE TABLE sup_nutrients_regional (
    region VARCHAR NOT NULL,
    SWHE DOUBLE,
    DWHE DOUBLE,
    RYEM DOUBLE,
    BARL DOUBLE NOT NULL,
    OATS DOUBLE,
    CORN DOUBLE,
    OCER DOUBLE,
    PARI DOUBLE,
    OCRO DOUBLE,
    OIND DOUBLE,
    NURS DOUBLE,
    FLOW DOUBLE,
    POTA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    RAPE DOUBLE,
    SOYA DOUBLE,
    OOIL DOUBLE,
    PULS DOUBLE,
    TOMA DOUBLE NOT NULL,
    OVEG DOUBLE NOT NULL,
    APPL DOUBLE NOT NULL,
    OFRU DOUBLE NOT NULL,
    CITR DOUBLE,
    TAGR DOUBLE,
    WINE DOUBLE,
    OLIV DOUBLE,
    TABO DOUBLE,
    TOBA DOUBLE,
    TEXT DOUBLE,
    GRAE DOUBLE,
    GRAI DOUBLE,
    MAIF DOUBLE,
    OFAR DOUBLE NOT NULL,
    ROOF DOUBLE,
    VSET DOUBLE,
    FALL DOUBLE,
    PRIMARY KEY (region)
);
COMMENT ON TABLE sup_nutrients_regional IS 'Rebuild every region''s base data from CAPRI. (tools/build/build_capri_base.py)';
INSERT INTO value_units VALUES
  ('sup_nutrients_regional', 'SWHE', NULL, 'open', 'nutrients_regional.SWHE: unit to be established'),
  ('sup_nutrients_regional', 'DWHE', NULL, 'open', 'nutrients_regional.DWHE: unit to be established'),
  ('sup_nutrients_regional', 'RYEM', NULL, 'open', 'nutrients_regional.RYEM: unit to be established'),
  ('sup_nutrients_regional', 'BARL', NULL, 'open', 'nutrients_regional.BARL: unit to be established'),
  ('sup_nutrients_regional', 'OATS', NULL, 'open', 'nutrients_regional.OATS: unit to be established'),
  ('sup_nutrients_regional', 'CORN', NULL, 'open', 'nutrients_regional.CORN: unit to be established'),
  ('sup_nutrients_regional', 'OCER', NULL, 'open', 'nutrients_regional.OCER: unit to be established'),
  ('sup_nutrients_regional', 'PARI', NULL, 'open', 'nutrients_regional.PARI: unit to be established'),
  ('sup_nutrients_regional', 'PULS', NULL, 'open', 'nutrients_regional.PULS: unit to be established'),
  ('sup_nutrients_regional', 'OCRO', NULL, 'open', 'nutrients_regional.OCRO: unit to be established'),
  ('sup_nutrients_regional', 'OIND', NULL, 'open', 'nutrients_regional.OIND: unit to be established'),
  ('sup_nutrients_regional', 'NURS', NULL, 'open', 'nutrients_regional.NURS: unit to be established'),
  ('sup_nutrients_regional', 'FLOW', NULL, 'open', 'nutrients_regional.FLOW: unit to be established'),
  ('sup_nutrients_regional', 'SUGB', NULL, 'open', 'nutrients_regional.SUGB: unit to be established'),
  ('sup_nutrients_regional', 'POTA', NULL, 'open', 'nutrients_regional.POTA: unit to be established'),
  ('sup_nutrients_regional', 'TOMA', NULL, 'open', 'nutrients_regional.TOMA: unit to be established'),
  ('sup_nutrients_regional', 'OVEG', NULL, 'open', 'nutrients_regional.OVEG: unit to be established'),
  ('sup_nutrients_regional', 'APPL', NULL, 'open', 'nutrients_regional.APPL: unit to be established'),
  ('sup_nutrients_regional', 'OFRU', NULL, 'open', 'nutrients_regional.OFRU: unit to be established'),
  ('sup_nutrients_regional', 'CITR', NULL, 'open', 'nutrients_regional.CITR: unit to be established'),
  ('sup_nutrients_regional', 'TAGR', NULL, 'open', 'nutrients_regional.TAGR: unit to be established'),
  ('sup_nutrients_regional', 'WINE', NULL, 'open', 'nutrients_regional.WINE: unit to be established'),
  ('sup_nutrients_regional', 'OLIV', NULL, 'open', 'nutrients_regional.OLIV: unit to be established'),
  ('sup_nutrients_regional', 'TABO', NULL, 'open', 'nutrients_regional.TABO: unit to be established'),
  ('sup_nutrients_regional', 'GRAE', NULL, 'open', 'nutrients_regional.GRAE: unit to be established'),
  ('sup_nutrients_regional', 'GRAI', NULL, 'open', 'nutrients_regional.GRAI: unit to be established'),
  ('sup_nutrients_regional', 'TOBA', NULL, 'open', 'nutrients_regional.TOBA: unit to be established'),
  ('sup_nutrients_regional', 'MAIF', NULL, 'open', 'nutrients_regional.MAIF: unit to be established'),
  ('sup_nutrients_regional', 'RAPE', NULL, 'open', 'nutrients_regional.RAPE: unit to be established'),
  ('sup_nutrients_regional', 'SUNF', NULL, 'open', 'nutrients_regional.SUNF: unit to be established'),
  ('sup_nutrients_regional', 'SOYA', NULL, 'open', 'nutrients_regional.SOYA: unit to be established'),
  ('sup_nutrients_regional', 'OOIL', NULL, 'open', 'nutrients_regional.OOIL: unit to be established'),
  ('sup_nutrients_regional', 'TEXT', NULL, 'open', 'nutrients_regional.TEXT: unit to be established'),
  ('sup_nutrients_regional', 'OFAR', NULL, 'open', 'nutrients_regional.OFAR: unit to be established'),
  ('sup_nutrients_regional', 'ROOF', NULL, 'open', 'nutrients_regional.ROOF: unit to be established'),
  ('sup_nutrients_regional', 'VSET', NULL, 'open', 'nutrients_regional.VSET: unit to be established'),
  ('sup_nutrients_regional', 'FALL', NULL, 'open', 'nutrients_regional.FALL: unit to be established');

-- file: capri_data/baselines/capri_greendeal_ref/1730/supply/techn_mix_2030.csv
CREATE TABLE sup_techn_mix_2030 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    yield_diff DOUBLE NOT NULL,
    need_diff DOUBLE NOT NULL,
    rest_cost_diff_eur_ha DOUBLE NOT NULL,
    inpo_diff DOUBLE NOT NULL,
    plap_diff DOUBLE NOT NULL,
    prem_diff_share DOUBLE NOT NULL,
    capri_region VARCHAR NOT NULL,
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE sup_techn_mix_2030 IS 'The T1 - T2 differences per ha of the items CAPRI''s technology factors move (intens/techf.gms, fert/fertned.gms, policy/rd_logic.gms, NUTNED_), per model region and crop with both technologies: the coefficients of the mix columns (S1, docs/design/S1_MIX_COLUMNS.md; tools/build/build_techn_mix_2030.py)';
INSERT INTO value_units VALUES
  ('sup_techn_mix_2030', 'yield_diff', 'U_ratio', 'capri', 'p_technFact Yield T1 - T2: outputs and nutrient removal per unit z over the crop''s per ha'),
  ('sup_techn_mix_2030', 'need_diff', 'U_ratio', 'builder', '(g_T1 - g_T2) / gbar, g = SQRT(1 + y)(1 + y) (NUTNED_): nutrient need per unit z over the crop''s need per ha'),
  ('sup_techn_mix_2030', 'rest_cost_diff_eur_ha', 'U_EuPerHa', 'builder', 'sum over SEED, REPM, REPB, ELEC, EGAS, EFUL, ELUB of the factor T1 - T2 x CAPREG''s 2017 cost per ha (coefficient x UVAG / 1000)'),
  ('sup_techn_mix_2030', 'inpo_diff', 'U_ratio', 'capri', 'p_technFact INPO T1 - T2'),
  ('sup_techn_mix_2030', 'plap_diff', 'U_ratio', 'capri', 'p_technFact PLAP T1 - T2'),
  ('sup_techn_mix_2030', 'prem_diff_share', 'U_ratio', 'builder', 'sum over the technology-differentiated schemes of PRME(scheme) / PRME(DPTOTAL) x p_technFact T1 - T2, CAPRI''s 2030 reference');

-- file: capri_data/2017/supply/plant_protection_cost.csv
CREATE TABLE sup_plant_protection_cost (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    plap_eur_ha DOUBLE,
    inpo_eur_ha DOUBLE,
    fert_eur_ha DOUBLE,
    eful_eur_ha DOUBLE,
    eful_inpo_eur_ha DOUBLE,
    yd_rest_eur_ha DOUBLE,
    yd_plap_eur_ha DOUBLE,
    yd_inpo_eur_ha DOUBLE,
    yield_growth DOUBLE,
    inpo_toin_share DOUBLE,
    capri_region VARCHAR NOT NULL,
    PRIMARY KEY (region, activity, capri_region)
);
COMMENT ON TABLE sup_plant_protection_cost IS 'CAPRI''s input costs that the Green Deal organic and pesticide targets shock, per model region and activity (2017). (tools/build/build_plant_protection_cost.py)';
INSERT INTO value_units VALUES
  ('sup_plant_protection_cost', 'plap_eur_ha', NULL, 'open', 'plant_protection_cost.plap_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'inpo_eur_ha', NULL, 'open', 'plant_protection_cost.inpo_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'fert_eur_ha', NULL, 'open', 'plant_protection_cost.fert_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'eful_eur_ha', NULL, 'open', 'plant_protection_cost.eful_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'eful_inpo_eur_ha', NULL, 'open', 'plant_protection_cost.eful_inpo_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'yd_rest_eur_ha', NULL, 'open', 'plant_protection_cost.yd_rest_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'yd_plap_eur_ha', NULL, 'open', 'plant_protection_cost.yd_plap_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'yd_inpo_eur_ha', NULL, 'open', 'plant_protection_cost.yd_inpo_eur_ha: unit to be established'),
  ('sup_plant_protection_cost', 'yield_growth', NULL, 'open', 'plant_protection_cost.yield_growth: unit to be established'),
  ('sup_plant_protection_cost', 'inpo_toin_share', NULL, 'open', 'plant_protection_cost.inpo_toin_share: unit to be established');

-- file: capri_data/2017/supply/set_aside_split.csv
CREATE TABLE sup_set_aside_split (
    region VARCHAR NOT NULL,
    prem_vset DOUBLE NOT NULL,
    prem_fall DOUBLE NOT NULL,
    prem_vset_2030 DOUBLE NOT NULL,
    prem_fall_2030 DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE sup_set_aside_split IS 'CAPRI''s premiums PRME (EUR/ha) of its two set-aside activities VSET and FALL per model region, 2017 and 2030 (the 2030 values in the model''s 2017 money), for the set-aside report (tools/build/build_labour_setaside.py; until S2, 7 November 2026, also the split of the model''s SETA and its labour)';
INSERT INTO value_units VALUES
  ('sup_set_aside_split', 'prem_vset', 'U_EuPerHa', 'capri', 'CAPRI''s PRME of VSET'),
  ('sup_set_aside_split', 'prem_fall', 'U_EuPerHa', 'capri', 'CAPRI''s PRME of FALL'),
  ('sup_set_aside_split', 'prem_vset_2030', 'U_EuPerHa', 'capri', 'CAPRI''s 2030 PRME of VSET over CAPRI''s inflation to 2030'),
  ('sup_set_aside_split', 'prem_fall_2030', 'U_EuPerHa', 'capri', 'CAPRI''s 2030 PRME of FALL over CAPRI''s inflation to 2030');

-- file: capri_data/2017/supply/winter_cover_share.csv
CREATE TABLE sup_winter_cover_share (
    region VARCHAR NOT NULL,
    crop VARCHAR NOT NULL,
    share DOUBLE NOT NULL,
    share0 DOUBLE NOT NULL,
    PRIMARY KEY (region, crop)
);
COMMENT ON TABLE sup_winter_cover_share IS 'CAPRI''s winter cover (catch) crops, CATC, per model region: 2030 level, cost, N fixation, winter cover shares. (tools/build/build_cover_crops.py)';
INSERT INTO value_units VALUES
  ('sup_winter_cover_share', 'share', NULL, 'open', 'winter_cover_share.share: unit to be established'),
  ('sup_winter_cover_share', 'share0', NULL, 'open', 'winter_cover_share.share0: unit to be established');

-- file: capri_data/2017/supply/livestock_cost_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_cost_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_cost_coef IS 'CAPRI''s variable cost per model head (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_cost_coef', c, NULL, 'open', 'livestock_cost_coef: variable cost per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_output_by_product_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_output_by_product_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity_product VARCHAR NOT NULL,
    value DOUBLE,
    PRIMARY KEY (region, activity_product)
);
COMMENT ON TABLE sup_livestock_output_by_product_coef IS 'CAPRI''s output per model head by CAPRI product (columns ACT.PRODUCT) (tools/build/build_livestock_products.py)';
INSERT INTO value_units SELECT 'sup_livestock_output_by_product_coef', c, NULL, 'open', 'livestock_output_by_product_coef: output per model head by CAPRI product (columns ACT.PRODUCT)' FROM (VALUES ('BCOW.BEEF'), ('BROI.POUM'), ('BULL.BEEF'), ('CALV.BEEF'), ('DCOW.BEEF'), ('DCOW.COMI'), ('HFRS.BEEF'), ('LAYS.EGGS'), ('LAYS.POUM'), ('PIGF.PORK'), ('PIGS.PORK'), ('SHGF.SGMT'), ('SHGM.SGMI'), ('SHGM.SGMT')) x(c);

-- file: capri_data/2017/supply/livestock_output_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_output_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_output_coef IS 'CAPRI''s main output per model head (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_output_coef', c, NULL, 'open', 'livestock_output_coef: main output per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_output_value_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_output_value_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_output_value_coef IS 'CAPRI''s output value per model head (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_output_value_coef', c, NULL, 'open', 'livestock_output_value_coef: output value per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_premium_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_premium_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_premium_coef IS 'CAPRI''s premiums per model head (tools/build/build_livestock_premium_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_premium_coef', c, NULL, 'open', 'livestock_premium_coef: premiums per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_product_value_by_market_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_product_value_by_market_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity_product VARCHAR NOT NULL,
    value DOUBLE,
    PRIMARY KEY (region, activity_product)
);
COMMENT ON TABLE sup_livestock_product_value_by_market_coef IS 'CAPRI''s value of each final product per model head by market commodity (columns ACT.MARKET) (tools/build/build_livestock_products.py)';
INSERT INTO value_units SELECT 'sup_livestock_product_value_by_market_coef', c, 'U_EuPerHd', 'builder', 'livestock_product_value_by_market_coef: value of each final product per model head by market commodity (columns ACT.MARKET)' FROM (VALUES ('BCOW.BEEF'), ('BROI.POUL'), ('BULL.BEEF'), ('CALV.BEEF'), ('DCOW.BEEF'), ('DCOW.MILK'), ('HFRS.BEEF'), ('LAYS.EGGS'), ('LAYS.POUL'), ('PIGF.PORK'), ('PIGS.PORK'), ('SHGF.SGMT'), ('SHGM.MILK'), ('SHGM.SGMT')) x(c);

-- file: capri_data/2017/supply/livestock_product_value_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_product_value_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_product_value_coef IS 'CAPRI''s final product value per model head (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_product_value_coef', c, NULL, 'open', 'livestock_product_value_coef: final product value per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_revenue_coef.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_revenue_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_revenue_coef IS 'CAPRI''s market revenue per model head (tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'sup_livestock_revenue_coef', c, NULL, 'open', 'livestock_revenue_coef: market revenue per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/livestock_units.csv
-- layout: wide, unnamed
CREATE TABLE sup_livestock_units (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE,
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE sup_livestock_units IS 'CAPRI''s livestock units per model head (tools/build/build_livestock_units.py)';
INSERT INTO value_units SELECT 'sup_livestock_units', c, NULL, 'open', 'livestock_units: livestock units per model head' FROM (VALUES ('BCOW'), ('BROI'), ('BULL'), ('CALV'), ('DCOW'), ('HFRS'), ('LAYS'), ('PIGF'), ('PIGS'), ('SHGF'), ('SHGM')) x(c);

-- file: capri_data/2017/supply/cap_premium_activity.csv
CREATE TABLE sup_cap_premium_activity (
    region VARCHAR NOT NULL,
    SWHE DOUBLE,
    DWHE DOUBLE,
    RYEM DOUBLE,
    BARL DOUBLE,
    OATS DOUBLE,
    CORN DOUBLE,
    OCER DOUBLE,
    PARI DOUBLE,
    OCRO DOUBLE,
    OIND DOUBLE,
    NURS DOUBLE,
    FLOW DOUBLE,
    POTA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    RAPE DOUBLE,
    SOYA DOUBLE,
    OOIL DOUBLE,
    PULS DOUBLE,
    TOMA DOUBLE,
    OVEG DOUBLE,
    APPL DOUBLE,
    OFRU DOUBLE,
    CITR DOUBLE,
    TAGR DOUBLE,
    WINE DOUBLE,
    OLIV DOUBLE,
    TABO DOUBLE,
    TOBA DOUBLE,
    TEXT DOUBLE,
    GRAE DOUBLE,
    GRAI DOUBLE,
    MAIF DOUBLE,
    OFAR DOUBLE,
    ROOF DOUBLE,
    VSET DOUBLE,
    FALL DOUBLE,
    AGGT DOUBLE,
    ANNC DOUBLE,
    ARAC DOUBLE,
    BEFM DOUBLE,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE,
    CAFF DOUBLE,
    CAFR DOUBLE,
    CAMF DOUBLE,
    CAMR DOUBLE,
    CATA DOUBLE,
    CERE DOUBLE,
    DCOH DOUBLE,
    DCOL DOUBLE,
    DCOW DOUBLE,
    EAAG DOUBLE,
    FODD DOUBLE,
    FRUN DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE,
    HENS DOUBLE,
    LABT DOUBLE,
    MODU DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE,
    OILS DOUBLE,
    PERM DOUBLE,
    PIGF DOUBLE,
    PKPL DOUBLE,
    POUF DOUBLE,
    RUMI DOUBLE,
    SCOW DOUBLE,
    SETF DOUBLE,
    SHGF DOUBLE,
    SHGM DOUBLE,
    SOWS DOUBLE,
    TWIN DOUBLE,
    PRIMARY KEY (region)
);
COMMENT ON TABLE sup_cap_premium_activity IS 'CAPRI''s CAP premium PRME per regional unit and activity (per ha or per head): the crop columns from crop_premium.csv (every region, model codes), the others from CAPREG''s DATA2 extract sources/capreg/capreg_cap_premium.parquet (tools/build/build_model_premium_prices.py; the model read the extract and joined them at run time until 31 October 2026)';
INSERT INTO value_units VALUES
  ('sup_cap_premium_activity', 'SWHE', NULL, 'open', 'cap_premium_activity.SWHE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'DWHE', NULL, 'open', 'cap_premium_activity.DWHE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'RYEM', NULL, 'open', 'cap_premium_activity.RYEM: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'BARL', NULL, 'open', 'cap_premium_activity.BARL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OATS', NULL, 'open', 'cap_premium_activity.OATS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CORN', NULL, 'open', 'cap_premium_activity.CORN: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OCER', NULL, 'open', 'cap_premium_activity.OCER: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'PARI', NULL, 'open', 'cap_premium_activity.PARI: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OCRO', NULL, 'open', 'cap_premium_activity.OCRO: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OIND', NULL, 'open', 'cap_premium_activity.OIND: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'NURS', NULL, 'open', 'cap_premium_activity.NURS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'FLOW', NULL, 'open', 'cap_premium_activity.FLOW: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'POTA', NULL, 'open', 'cap_premium_activity.POTA: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SUGB', NULL, 'open', 'cap_premium_activity.SUGB: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SUNF', NULL, 'open', 'cap_premium_activity.SUNF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'RAPE', NULL, 'open', 'cap_premium_activity.RAPE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SOYA', NULL, 'open', 'cap_premium_activity.SOYA: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OOIL', NULL, 'open', 'cap_premium_activity.OOIL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'PULS', NULL, 'open', 'cap_premium_activity.PULS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TOMA', NULL, 'open', 'cap_premium_activity.TOMA: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OVEG', NULL, 'open', 'cap_premium_activity.OVEG: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'APPL', NULL, 'open', 'cap_premium_activity.APPL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OFRU', NULL, 'open', 'cap_premium_activity.OFRU: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CITR', NULL, 'open', 'cap_premium_activity.CITR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TAGR', NULL, 'open', 'cap_premium_activity.TAGR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'WINE', NULL, 'open', 'cap_premium_activity.WINE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OLIV', NULL, 'open', 'cap_premium_activity.OLIV: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TABO', NULL, 'open', 'cap_premium_activity.TABO: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TOBA', NULL, 'open', 'cap_premium_activity.TOBA: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TEXT', NULL, 'open', 'cap_premium_activity.TEXT: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'GRAE', NULL, 'open', 'cap_premium_activity.GRAE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'GRAI', NULL, 'open', 'cap_premium_activity.GRAI: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'GRAS', NULL, 'open', 'cap_premium_activity.GRAS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'MAIF', NULL, 'open', 'cap_premium_activity.MAIF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'FALL', NULL, 'open', 'cap_premium_activity.FALL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'AGGT', NULL, 'open', 'cap_premium_activity.AGGT: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'ANNC', NULL, 'open', 'cap_premium_activity.ANNC: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'ARAC', NULL, 'open', 'cap_premium_activity.ARAC: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'BEFM', NULL, 'open', 'cap_premium_activity.BEFM: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'BULF', NULL, 'open', 'cap_premium_activity.BULF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'BULH', NULL, 'open', 'cap_premium_activity.BULH: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'BULL', NULL, 'open', 'cap_premium_activity.BULL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CACR', NULL, 'open', 'cap_premium_activity.CACR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CAFF', NULL, 'open', 'cap_premium_activity.CAFF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CAFR', NULL, 'open', 'cap_premium_activity.CAFR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CAMF', NULL, 'open', 'cap_premium_activity.CAMF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CAMR', NULL, 'open', 'cap_premium_activity.CAMR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CATA', NULL, 'open', 'cap_premium_activity.CATA: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'CERE', NULL, 'open', 'cap_premium_activity.CERE: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'DCOH', NULL, 'open', 'cap_premium_activity.DCOH: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'DCOL', NULL, 'open', 'cap_premium_activity.DCOL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'DCOW', NULL, 'open', 'cap_premium_activity.DCOW: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'EAAG', NULL, 'open', 'cap_premium_activity.EAAG: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'FODD', NULL, 'open', 'cap_premium_activity.FODD: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'FRUN', NULL, 'open', 'cap_premium_activity.FRUN: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'HEIF', NULL, 'open', 'cap_premium_activity.HEIF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'HEIH', NULL, 'open', 'cap_premium_activity.HEIH: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'HEIL', NULL, 'open', 'cap_premium_activity.HEIL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'HEIR', NULL, 'open', 'cap_premium_activity.HEIR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'HENS', NULL, 'open', 'cap_premium_activity.HENS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'LABT', NULL, 'open', 'cap_premium_activity.LABT: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'MODU', NULL, 'open', 'cap_premium_activity.MODU: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OANI', NULL, 'open', 'cap_premium_activity.OANI: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OAR1', NULL, 'open', 'cap_premium_activity.OAR1: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OFAR', NULL, 'open', 'cap_premium_activity.OFAR: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'OILS', NULL, 'open', 'cap_premium_activity.OILS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'PERM', NULL, 'open', 'cap_premium_activity.PERM: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'PIGF', NULL, 'open', 'cap_premium_activity.PIGF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'PKPL', NULL, 'open', 'cap_premium_activity.PKPL: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'POUF', NULL, 'open', 'cap_premium_activity.POUF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'ROOF', NULL, 'open', 'cap_premium_activity.ROOF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'RUMI', NULL, 'open', 'cap_premium_activity.RUMI: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SCOW', NULL, 'open', 'cap_premium_activity.SCOW: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SETF', NULL, 'open', 'cap_premium_activity.SETF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SHGF', NULL, 'open', 'cap_premium_activity.SHGF: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SHGM', NULL, 'open', 'cap_premium_activity.SHGM: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'SOWS', NULL, 'open', 'cap_premium_activity.SOWS: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'TWIN', NULL, 'open', 'cap_premium_activity.TWIN: unit to be established (per ha for crops, per head for animals)'),
  ('sup_cap_premium_activity', 'VSET', NULL, 'open', 'cap_premium_activity.VSET: unit to be established (per ha for crops, per head for animals)');

-- file: capri_data/2017/supply/producer_prices_regional.csv
CREATE TABLE sup_producer_prices_regional (
    model_region VARCHAR NOT NULL,
    AGGT DOUBLE,
    APPL DOUBLE,
    ARAB DOUBLE,
    BARL DOUBLE,
    BEFM DOUBLE,
    BULF DOUBLE,
    BULH DOUBLE,
    BULL DOUBLE,
    CACR DOUBLE,
    CAFF DOUBLE,
    CAFR DOUBLE,
    CAMF DOUBLE,
    CAMR DOUBLE,
    CATA DOUBLE,
    CERE DOUBLE,
    CITR DOUBLE,
    CORN DOUBLE,
    DCOH DOUBLE,
    DCOL DOUBLE,
    DCOW DOUBLE,
    DWHE DOUBLE,
    FLOW DOUBLE,
    FODD DOUBLE,
    GRAE DOUBLE,
    GRAI DOUBLE,
    GRAS DOUBLE,
    HEIF DOUBLE,
    HEIH DOUBLE,
    HEIL DOUBLE,
    HEIR DOUBLE,
    HENS DOUBLE,
    MAIF DOUBLE,
    NURS DOUBLE,
    OANI DOUBLE,
    OAR1 DOUBLE,
    OATS DOUBLE,
    OCER DOUBLE,
    OCRO DOUBLE,
    OFAR DOUBLE,
    OFRU DOUBLE,
    OILS DOUBLE,
    OIND DOUBLE,
    OLIV DOUBLE,
    OOIL DOUBLE,
    OVEG DOUBLE,
    PARI DOUBLE,
    PERM DOUBLE,
    PIGF DOUBLE,
    PKPL DOUBLE,
    POTA DOUBLE,
    POUF DOUBLE,
    PULS DOUBLE,
    RAPE DOUBLE,
    ROOF DOUBLE,
    RUMI DOUBLE,
    RYEM DOUBLE,
    SCOW DOUBLE,
    SHGF DOUBLE,
    SHGM DOUBLE,
    SOWS DOUBLE,
    SOYA DOUBLE,
    SUGB DOUBLE,
    SUNF DOUBLE,
    SWHE DOUBLE,
    TABO DOUBLE,
    TAGR DOUBLE,
    TEXT DOUBLE,
    TOBA DOUBLE,
    TOMA DOUBLE,
    TWIN DOUBLE,
    UAAR DOUBLE,
    WINE DOUBLE,
    PRIMARY KEY (model_region)
);
COMMENT ON TABLE sup_producer_prices_regional IS 'CAPRI''s regional producer prices MPRI (EUR/t) per regional unit and activity (sources/capreg/capreg_producer_prices.parquet), CAPRI''s TWIN column for WINE where it is empty (and OFAR for OFOD until S2, 7 November 2026), and a missing regional price filled with the country''s national price (sources/capreg/capreg_national_prices.parquet; tools/build/build_model_premium_prices.py; done by the model''s loader at run time until 31 October 2026)';
INSERT INTO value_units VALUES
  ('sup_producer_prices_regional', 'AGGT', NULL, 'open', 'producer_prices_regional.AGGT: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'APPL', NULL, 'open', 'producer_prices_regional.APPL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'ARAB', NULL, 'open', 'producer_prices_regional.ARAB: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'BARL', NULL, 'open', 'producer_prices_regional.BARL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'BEFM', NULL, 'open', 'producer_prices_regional.BEFM: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'BULF', NULL, 'open', 'producer_prices_regional.BULF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'BULH', NULL, 'open', 'producer_prices_regional.BULH: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'BULL', NULL, 'open', 'producer_prices_regional.BULL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CACR', NULL, 'open', 'producer_prices_regional.CACR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CAFF', NULL, 'open', 'producer_prices_regional.CAFF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CAFR', NULL, 'open', 'producer_prices_regional.CAFR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CAMF', NULL, 'open', 'producer_prices_regional.CAMF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CAMR', NULL, 'open', 'producer_prices_regional.CAMR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CATA', NULL, 'open', 'producer_prices_regional.CATA: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CERE', NULL, 'open', 'producer_prices_regional.CERE: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CITR', NULL, 'open', 'producer_prices_regional.CITR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'CORN', NULL, 'open', 'producer_prices_regional.CORN: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'DCOH', NULL, 'open', 'producer_prices_regional.DCOH: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'DCOL', NULL, 'open', 'producer_prices_regional.DCOL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'DCOW', NULL, 'open', 'producer_prices_regional.DCOW: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'DWHE', NULL, 'open', 'producer_prices_regional.DWHE: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'FLOW', NULL, 'open', 'producer_prices_regional.FLOW: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'FODD', NULL, 'open', 'producer_prices_regional.FODD: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'GRAE', NULL, 'open', 'producer_prices_regional.GRAE: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'GRAI', NULL, 'open', 'producer_prices_regional.GRAI: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'GRAS', NULL, 'open', 'producer_prices_regional.GRAS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'HEIF', NULL, 'open', 'producer_prices_regional.HEIF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'HEIH', NULL, 'open', 'producer_prices_regional.HEIH: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'HEIL', NULL, 'open', 'producer_prices_regional.HEIL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'HEIR', NULL, 'open', 'producer_prices_regional.HEIR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'HENS', NULL, 'open', 'producer_prices_regional.HENS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'MAIF', NULL, 'open', 'producer_prices_regional.MAIF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'NURS', NULL, 'open', 'producer_prices_regional.NURS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OANI', NULL, 'open', 'producer_prices_regional.OANI: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OAR1', NULL, 'open', 'producer_prices_regional.OAR1: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OATS', NULL, 'open', 'producer_prices_regional.OATS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OCER', NULL, 'open', 'producer_prices_regional.OCER: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OCRO', NULL, 'open', 'producer_prices_regional.OCRO: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OFAR', NULL, 'open', 'producer_prices_regional.OFAR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OFRU', NULL, 'open', 'producer_prices_regional.OFRU: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OILS', NULL, 'open', 'producer_prices_regional.OILS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OIND', NULL, 'open', 'producer_prices_regional.OIND: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OLIV', NULL, 'open', 'producer_prices_regional.OLIV: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OOIL', NULL, 'open', 'producer_prices_regional.OOIL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'OVEG', NULL, 'open', 'producer_prices_regional.OVEG: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'PARI', NULL, 'open', 'producer_prices_regional.PARI: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'PERM', NULL, 'open', 'producer_prices_regional.PERM: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'PIGF', NULL, 'open', 'producer_prices_regional.PIGF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'PKPL', NULL, 'open', 'producer_prices_regional.PKPL: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'POTA', NULL, 'open', 'producer_prices_regional.POTA: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'POUF', NULL, 'open', 'producer_prices_regional.POUF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'PULS', NULL, 'open', 'producer_prices_regional.PULS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'RAPE', NULL, 'open', 'producer_prices_regional.RAPE: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'ROOF', NULL, 'open', 'producer_prices_regional.ROOF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'RUMI', NULL, 'open', 'producer_prices_regional.RUMI: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'RYEM', NULL, 'open', 'producer_prices_regional.RYEM: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SCOW', NULL, 'open', 'producer_prices_regional.SCOW: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SHGF', NULL, 'open', 'producer_prices_regional.SHGF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SHGM', NULL, 'open', 'producer_prices_regional.SHGM: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SOWS', NULL, 'open', 'producer_prices_regional.SOWS: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SOYA', NULL, 'open', 'producer_prices_regional.SOYA: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SUGB', NULL, 'open', 'producer_prices_regional.SUGB: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SUNF', NULL, 'open', 'producer_prices_regional.SUNF: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'SWHE', NULL, 'open', 'producer_prices_regional.SWHE: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TABO', NULL, 'open', 'producer_prices_regional.TABO: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TAGR', NULL, 'open', 'producer_prices_regional.TAGR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TEXT', NULL, 'open', 'producer_prices_regional.TEXT: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TOBA', NULL, 'open', 'producer_prices_regional.TOBA: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TOMA', NULL, 'open', 'producer_prices_regional.TOMA: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'TWIN', NULL, 'open', 'producer_prices_regional.TWIN: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'UAAR', NULL, 'open', 'producer_prices_regional.UAAR: EUR/t as CAPRI''s MPRI, to be confirmed per column'),
  ('sup_producer_prices_regional', 'WINE', NULL, 'open', 'producer_prices_regional.WINE: EUR/t as CAPRI''s MPRI, to be confirmed per column');

-- file: capri_data/2017/supply/young_animals_2017.csv
CREATE TABLE sup_young_animals_2017 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    category VARCHAR NOT NULL CHECK (category IN ('calves', 'young', 'cows', 'piglets', 'lambs')),
    base_net_export DOUBLE NOT NULL,
    value_eur_head DOUBLE NOT NULL,
    PRIMARY KEY (region, category)
);
COMMENT ON TABLE sup_young_animals_2017 IS 'CAPRI''s young-animal balances per model region (supply_model.gms INPANI_), calves and young cattle pooled across the sexes (the model''s default): base net export and CAPRI''s national unit value (UVAG); the coefficients in young_animals_2017_coef.csv (tools/build/build_young_animals.py; young_animals_2017.json until 31 October 2026; capri_mod/data/nested_tables.py)';
INSERT INTO value_units VALUES
  ('sup_young_animals_2017', 'base_net_export', NULL, 'open', 'young_animals_2017.base_net_export: 1000 head (the builder; no unit code in the catalogue)'),
  ('sup_young_animals_2017', 'value_eur_head', NULL, 'open', 'young_animals_2017.value_eur_head: EUR per head (the builder; no unit code in the catalogue)');

-- file: capri_data/2017/supply/young_animals_2017_coef.csv
CREATE TABLE sup_young_animals_2017_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    category VARCHAR NOT NULL CHECK (category IN ('calves', 'young', 'cows', 'piglets', 'lambs')),
    side VARCHAR NOT NULL CHECK (side IN ('produce', 'use')),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    coefficient DOUBLE NOT NULL,
    PRIMARY KEY (region, category, side, activity)
);
COMMENT ON TABLE sup_young_animals_2017_coef IS 'young animals produced or used per model head of an activity (CAPRI''s YCAM..YPIG outputs, ICAM..IPIG inputs per 1000 head, LEVL weights, per model head) in the pooled balances of young_animals_2017.csv (tools/build/build_young_animals.py)';
INSERT INTO value_units VALUES
  ('sup_young_animals_2017_coef', 'coefficient', 'U_HdPerHd', 'builder', 'young_animals_2017_coef.coefficient: head per head (the builder)');

-- file: capri_data/2017/supply/young_animals_by_sex_2017.csv
CREATE TABLE sup_young_animals_by_sex_2017 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    category VARCHAR NOT NULL CHECK (category IN ('calves_m', 'calves_f', 'young_m', 'young_f', 'cows', 'piglets', 'lambs')),
    base_net_export DOUBLE NOT NULL,
    value_eur_head DOUBLE NOT NULL,
    PRIMARY KEY (region, category)
);
COMMENT ON TABLE sup_young_animals_by_sex_2017 IS 'CAPRI''s young-animal balances per model region and sex (INPANI_), read instead of young_animals_2017.csv only with the cattle member splits on (KNOWN_ISSUES K65); the coefficients in young_animals_by_sex_2017_coef.csv (tools/build/build_young_animals.py; young_animals_by_sex_2017.json until 31 October 2026)';
INSERT INTO value_units VALUES
  ('sup_young_animals_by_sex_2017', 'base_net_export', NULL, 'open', 'young_animals_by_sex_2017.base_net_export: 1000 head (the builder; no unit code in the catalogue)'),
  ('sup_young_animals_by_sex_2017', 'value_eur_head', NULL, 'open', 'young_animals_by_sex_2017.value_eur_head: EUR per head (the builder; no unit code in the catalogue)');

-- file: capri_data/2017/supply/young_animals_by_sex_2017_coef.csv
CREATE TABLE sup_young_animals_by_sex_2017_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    category VARCHAR NOT NULL CHECK (category IN ('calves_m', 'calves_f', 'young_m', 'young_f', 'cows', 'piglets', 'lambs')),
    side VARCHAR NOT NULL CHECK (side IN ('produce', 'use')),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    coefficient DOUBLE NOT NULL,
    PRIMARY KEY (region, category, side, activity)
);
COMMENT ON TABLE sup_young_animals_by_sex_2017_coef IS 'young animals produced or used per model head of an activity in the per-sex balances of young_animals_by_sex_2017.csv (tools/build/build_young_animals.py)';
INSERT INTO value_units VALUES
  ('sup_young_animals_by_sex_2017_coef', 'coefficient', 'U_HdPerHd', 'builder', 'young_animals_by_sex_2017_coef.coefficient: head per head (the builder)');

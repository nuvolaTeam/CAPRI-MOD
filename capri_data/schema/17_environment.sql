-- The environmental accounts' inputs (capri_data/2017/environment): CAPRI's emission factors, N and P coefficients and
-- the regional environmental data. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026;
-- units open where no builder or CAPRI file states them (value_units).

-- file: capri_data/2017/environment/capri_crop_n_coefs_2030.csv
CREATE TABLE env_capri_crop_n_coefs_2030 (
    capri_region VARCHAR NOT NULL,
    crop VARCHAR NOT NULL,
    levl DOUBLE NOT NULL,
    yild DOUBLE,
    nitf DOUBLE NOT NULL,
    ncrd DOUBLE,
    biofix_t DOUBLE,
    PRIMARY KEY (capri_region, crop)
);
COMMENT ON TABLE env_capri_crop_n_coefs_2030 IS 'CAPRI''s per-crop nitrogen coefficients per region, 2030 reference (for the gross N balance). (tools/build/build_capri_crop_n_coefs.py)';
INSERT INTO value_units VALUES
  ('env_capri_crop_n_coefs_2030', 'levl', NULL, 'open', 'capri_crop_n_coefs_2030.levl: unit to be established'),
  ('env_capri_crop_n_coefs_2030', 'yild', NULL, 'open', 'capri_crop_n_coefs_2030.yild: unit to be established'),
  ('env_capri_crop_n_coefs_2030', 'nitf', NULL, 'open', 'capri_crop_n_coefs_2030.nitf: unit to be established'),
  ('env_capri_crop_n_coefs_2030', 'ncrd', NULL, 'open', 'capri_crop_n_coefs_2030.ncrd: unit to be established'),
  ('env_capri_crop_n_coefs_2030', 'biofix_t', NULL, 'open', 'capri_crop_n_coefs_2030.biofix_t: unit to be established');

-- file: capri_data/2017/environment/capri_gnb_components_2030.csv
CREATE TABLE env_capri_gnb_components_2030 (
    capri_region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    kg_n_per_ha DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, "item")
);
COMMENT ON TABLE env_capri_gnb_components_2030 IS 'CAPRI''s regional gross nitrogen balance components, 2030 reference (kg N per ha). (tools/build/build_capri_gnb_components.py)';
INSERT INTO value_units VALUES
  ('env_capri_gnb_components_2030', 'kg_n_per_ha', NULL, 'open', 'capri_gnb_components_2030.kg_n_per_ha: unit to be established');

-- file: capri_data/2017/environment/climate_zones.csv
CREATE TABLE env_climate_zones (
    region VARCHAR NOT NULL,
    zone VARCHAR NOT NULL,
    pct BIGINT NOT NULL,
    PRIMARY KEY (region, zone)
);
COMMENT ON TABLE env_climate_zones IS 'climate_zones (no builder: a declared table)';
INSERT INTO value_units VALUES
  ('env_climate_zones', 'pct', NULL, 'open', 'climate_zones.pct: unit to be established');

-- file: capri_data/2017/environment/crop_co2_coef.csv
CREATE TABLE env_crop_co2_coef (
    region VARCHAR NOT NULL,
    co2lim_kg_ha DOUBLE NOT NULL,
    urea_share DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE env_crop_co2_coef IS 'CAPRI''s manure and enteric methane per head and its CO2 from liming and urea, per model region (Sprint 9s; (tools/build/build_ghg_coefs_2017.py)';
INSERT INTO value_units VALUES
  ('env_crop_co2_coef', 'co2lim_kg_ha', NULL, 'open', 'crop_co2_coef.co2lim_kg_ha: unit to be established'),
  ('env_crop_co2_coef', 'urea_share', NULL, 'open', 'crop_co2_coef.urea_share: unit to be established');

-- file: capri_data/2017/environment/crop_nut_need_mult_fact_2030.csv
CREATE TABLE env_crop_nut_need_mult_fact_2030 (
    region VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    x DOUBLE NOT NULL,
    PRIMARY KEY (region, capri_region)
);
COMMENT ON TABLE env_crop_nut_need_mult_fact_2030 IS 'CAPRI''s over-fertilisation factor per region (v_cropNutNeedMultFact, NITF, "T"). (tools/build/build_overfert_factors.py)';
INSERT INTO value_units VALUES
  ('env_crop_nut_need_mult_fact_2030', 'x', NULL, 'open', 'crop_nut_need_mult_fact_2030.x: unit to be established');

-- file: capri_data/2017/environment/enteric_feed_factors.csv
CREATE TABLE env_enteric_feed_factors (
    country VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    feed VARCHAR NOT NULL,
    ge_mcal_per_kg_dm DOUBLE NOT NULL,
    ym DOUBLE NOT NULL,
    grazing_share DOUBLE NOT NULL,
    PRIMARY KEY (country, animal, feed)
);
COMMENT ON TABLE env_enteric_feed_factors IS 'Inputs of CAPRI''s feed-based cattle enteric CH4 (GWPCH4ENT_, envind/gases.gms l. 365-376). (tools/build/build_enteric_feed_factors.py)';
INSERT INTO value_units VALUES
  ('env_enteric_feed_factors', 'ge_mcal_per_kg_dm', NULL, 'open', 'enteric_feed_factors.ge_mcal_per_kg_dm: unit to be established'),
  ('env_enteric_feed_factors', 'ym', NULL, 'open', 'enteric_feed_factors.ym: unit to be established'),
  ('env_enteric_feed_factors', 'grazing_share', NULL, 'open', 'enteric_feed_factors.grazing_share: unit to be established');

-- file: capri_data/2017/environment/fert_dist_crop_groups_2030.csv
CREATE TABLE env_fert_dist_crop_groups_2030 (
    capri_region VARCHAR NOT NULL,
    model_crop VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    share DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, model_crop, ngrp)
);
COMMENT ON TABLE env_fert_dist_crop_groups_2030 IS 'CAPRI''s priors for the inner fertiliser distribution model (supply/set_fert_priors.gms, simulation mode). (tools/build/build_fert_dist_priors.py)';
INSERT INTO value_units VALUES
  ('env_fert_dist_crop_groups_2030', 'share', NULL, 'open', 'fert_dist_crop_groups_2030.share: unit to be established');

-- file: capri_data/2017/environment/fert_dist_priors_2030.csv
CREATE TABLE env_fert_dist_priors_2030 (
    capri_region VARCHAR NOT NULL,
    "level" VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    perm BIGINT NOT NULL,
    area_kha DOUBLE NOT NULL,
    mine_kg_ha DOUBLE NOT NULL,
    excr_kg_ha DOUBLE NOT NULL,
    cres_kg_ha DOUBLE NOT NULL,
    accuracy DOUBLE NOT NULL,
    mine_eff DOUBLE NOT NULL,
    excr_avail DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, "level", ngrp)
);
COMMENT ON TABLE env_fert_dist_priors_2030 IS 'CAPRI''s priors for the inner fertiliser distribution model (supply/set_fert_priors.gms, simulation mode). (tools/build/build_fert_dist_priors.py)';
INSERT INTO value_units VALUES
  ('env_fert_dist_priors_2030', 'perm', NULL, 'open', 'fert_dist_priors_2030.perm: unit to be established'),
  ('env_fert_dist_priors_2030', 'area_kha', NULL, 'open', 'fert_dist_priors_2030.area_kha: unit to be established'),
  ('env_fert_dist_priors_2030', 'mine_kg_ha', NULL, 'open', 'fert_dist_priors_2030.mine_kg_ha: unit to be established'),
  ('env_fert_dist_priors_2030', 'excr_kg_ha', NULL, 'open', 'fert_dist_priors_2030.excr_kg_ha: unit to be established'),
  ('env_fert_dist_priors_2030', 'cres_kg_ha', NULL, 'open', 'fert_dist_priors_2030.cres_kg_ha: unit to be established'),
  ('env_fert_dist_priors_2030', 'accuracy', NULL, 'open', 'fert_dist_priors_2030.accuracy: unit to be established'),
  ('env_fert_dist_priors_2030', 'mine_eff', NULL, 'open', 'fert_dist_priors_2030.mine_eff: unit to be established'),
  ('env_fert_dist_priors_2030', 'excr_avail', NULL, 'open', 'fert_dist_priors_2030.excr_avail: unit to be established');

-- file: capri_data/2017/environment/fert_dist_priors_npk_2030.csv
CREATE TABLE env_fert_dist_priors_npk_2030 (
    capri_region VARCHAR NOT NULL,
    "level" VARCHAR NOT NULL,
    nutrient VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    perm BIGINT NOT NULL,
    area_kha DOUBLE NOT NULL,
    mine_kg_ha DOUBLE NOT NULL,
    excr_kg_ha DOUBLE NOT NULL,
    cres_kg_ha DOUBLE NOT NULL,
    accuracy DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, "level", nutrient, ngrp)
);
COMMENT ON TABLE env_fert_dist_priors_npk_2030 IS 'CAPRI''s crop nutrient balance for N, P and K (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, (tools/build/build_npk_balance_2030.py)';
INSERT INTO value_units VALUES
  ('env_fert_dist_priors_npk_2030', 'perm', NULL, 'open', 'fert_dist_priors_npk_2030.perm: unit to be established'),
  ('env_fert_dist_priors_npk_2030', 'area_kha', NULL, 'open', 'fert_dist_priors_npk_2030.area_kha: unit to be established'),
  ('env_fert_dist_priors_npk_2030', 'mine_kg_ha', NULL, 'open', 'fert_dist_priors_npk_2030.mine_kg_ha: unit to be established'),
  ('env_fert_dist_priors_npk_2030', 'excr_kg_ha', NULL, 'open', 'fert_dist_priors_npk_2030.excr_kg_ha: unit to be established'),
  ('env_fert_dist_priors_npk_2030', 'cres_kg_ha', NULL, 'open', 'fert_dist_priors_npk_2030.cres_kg_ha: unit to be established'),
  ('env_fert_dist_priors_npk_2030', 'accuracy', NULL, 'open', 'fert_dist_priors_npk_2030.accuracy: unit to be established');

-- file: capri_data/2017/environment/fertiliser_substitution_2030.csv
CREATE TABLE env_fertiliser_substitution_2030 (
    region VARCHAR NOT NULL,
    manure_availability DOUBLE NOT NULL,
    mineral_efficiency DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, source)
);
COMMENT ON TABLE env_fertiliser_substitution_2030 IS 'Atmospheric N deposition and the fertiliser substitution terms per model region, from CAPRI''s 2030 reference. (tools/build/build_n_deposition_substitution.py)';
INSERT INTO value_units VALUES
  ('env_fertiliser_substitution_2030', 'manure_availability', NULL, 'open', 'fertiliser_substitution_2030.manure_availability: unit to be established'),
  ('env_fertiliser_substitution_2030', 'mineral_efficiency', NULL, 'open', 'fertiliser_substitution_2030.mineral_efficiency: unit to be established');

-- file: capri_data/2017/environment/histosol.csv
CREATE TABLE env_histosol (
    region VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    ef_n2o_crop DOUBLE NOT NULL,
    n2o_t_ha_crop DOUBLE NOT NULL,
    co2_t_ha_crop DOUBLE NOT NULL,
    ch4_t_ha_crop DOUBLE NOT NULL,
    share_crop DOUBLE NOT NULL,
    ef_n2o_grass DOUBLE NOT NULL,
    n2o_t_ha_grass DOUBLE NOT NULL,
    co2_t_ha_grass DOUBLE NOT NULL,
    ch4_t_ha_grass DOUBLE NOT NULL,
    share_grass DOUBLE NOT NULL,
    cs0_grass DOUBLE,
    cs1_grass DOUBLE,
    maxshare_grass DOUBLE,
    cost_lin_grass DOUBLE,
    pmp_lin_grass DOUBLE,
    pmp_sqr_grass DOUBLE,
    cs0_crop DOUBLE,
    cs1_crop DOUBLE,
    maxshare_crop DOUBLE,
    cost_lin_crop DOUBLE,
    pmp_lin_crop DOUBLE,
    pmp_sqr_crop DOUBLE,
    PRIMARY KEY (region, capri_region)
);
COMMENT ON TABLE env_histosol IS 'CAPRI''s histosols (drained organic soils) per model region: emission factors and the fallowing option. (tools/build/build_histosol.py)';
INSERT INTO value_units VALUES
  ('env_histosol', 'ef_n2o_crop', NULL, 'open', 'histosol.ef_n2o_crop: unit to be established'),
  ('env_histosol', 'n2o_t_ha_crop', NULL, 'open', 'histosol.n2o_t_ha_crop: unit to be established'),
  ('env_histosol', 'co2_t_ha_crop', NULL, 'open', 'histosol.co2_t_ha_crop: unit to be established'),
  ('env_histosol', 'ch4_t_ha_crop', NULL, 'open', 'histosol.ch4_t_ha_crop: unit to be established'),
  ('env_histosol', 'share_crop', NULL, 'open', 'histosol.share_crop: unit to be established'),
  ('env_histosol', 'ef_n2o_grass', NULL, 'open', 'histosol.ef_n2o_grass: unit to be established'),
  ('env_histosol', 'n2o_t_ha_grass', NULL, 'open', 'histosol.n2o_t_ha_grass: unit to be established'),
  ('env_histosol', 'co2_t_ha_grass', NULL, 'open', 'histosol.co2_t_ha_grass: unit to be established'),
  ('env_histosol', 'ch4_t_ha_grass', NULL, 'open', 'histosol.ch4_t_ha_grass: unit to be established'),
  ('env_histosol', 'share_grass', NULL, 'open', 'histosol.share_grass: unit to be established'),
  ('env_histosol', 'cs0_grass', NULL, 'open', 'histosol.cs0_grass: unit to be established'),
  ('env_histosol', 'cs1_grass', NULL, 'open', 'histosol.cs1_grass: unit to be established'),
  ('env_histosol', 'maxshare_grass', NULL, 'open', 'histosol.maxshare_grass: unit to be established'),
  ('env_histosol', 'cost_lin_grass', NULL, 'open', 'histosol.cost_lin_grass: unit to be established'),
  ('env_histosol', 'pmp_lin_grass', NULL, 'open', 'histosol.pmp_lin_grass: unit to be established'),
  ('env_histosol', 'pmp_sqr_grass', NULL, 'open', 'histosol.pmp_sqr_grass: unit to be established'),
  ('env_histosol', 'cs0_crop', NULL, 'open', 'histosol.cs0_crop: unit to be established'),
  ('env_histosol', 'cs1_crop', NULL, 'open', 'histosol.cs1_crop: unit to be established'),
  ('env_histosol', 'maxshare_crop', NULL, 'open', 'histosol.maxshare_crop: unit to be established'),
  ('env_histosol', 'cost_lin_crop', NULL, 'open', 'histosol.cost_lin_crop: unit to be established'),
  ('env_histosol', 'pmp_lin_crop', NULL, 'open', 'histosol.pmp_lin_crop: unit to be established'),
  ('env_histosol', 'pmp_sqr_crop', NULL, 'open', 'histosol.pmp_sqr_crop: unit to be established');

-- file: capri_data/2017/environment/irrigation_2017.csv
CREATE TABLE env_irrigation_2017 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    irrigated_share DOUBLE NOT NULL,
    cnir_mm DOUBLE,
    irr2_share DOUBLE NOT NULL,
    irr2_year BIGINT NOT NULL,
    irr2_level VARCHAR NOT NULL,
    PRIMARY KEY (region, activity, irr2_level)
);
COMMENT ON TABLE env_irrigation_2017 IS 'Irrigated shares and net irrigation requirements per regional unit and crop, base year 2017, for the irrigation (tools/build/build_irrigation_2017.py)';
INSERT INTO value_units VALUES
  ('env_irrigation_2017', 'irrigated_share', NULL, 'open', 'irrigation_2017.irrigated_share: unit to be established'),
  ('env_irrigation_2017', 'cnir_mm', NULL, 'open', 'irrigation_2017.cnir_mm: unit to be established'),
  ('env_irrigation_2017', 'irr2_share', NULL, 'open', 'irrigation_2017.irr2_share: unit to be established'),
  ('env_irrigation_2017', 'irr2_year', NULL, 'open', 'irrigation_2017.irr2_year: unit to be established');

-- file: capri_data/2017/environment/luc_2030.csv
CREATE TABLE env_luc_2030 (
    capri_region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL
);
COMMENT ON TABLE env_luc_2030 IS 'CAPRI''s land-use change (LUC) transition model data (supply/supply_model.gms e_landTypes_to_LUclass, (tools/build/build_luc_2030.py)';
INSERT INTO value_units VALUES
  ('env_luc_2030', 'value', NULL, 'open', 'luc_2030.value: unit to be established');

-- file: capri_data/2017/environment/manure_housing_losses_2030.csv
CREATE TABLE env_manure_housing_losses_2030 (
    region VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    loss_share DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, animal, source)
);
COMMENT ON TABLE env_manure_housing_losses_2030 IS 'CAPRI''s manure N lost in housing and storage, per model region and animal (fertDistExcr_ input). (tools/build/build_manure_losses.py)';
INSERT INTO value_units VALUES
  ('env_manure_housing_losses_2030', 'loss_share', NULL, 'open', 'manure_housing_losses_2030.loss_share: unit to be established');

-- file: capri_data/2017/environment/manure_n2o_factors.csv
CREATE TABLE env_manure_n2o_factors (
    region VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    capri_region VARCHAR NOT NULL,
    f_man DOUBLE NOT NULL,
    f_app DOUBLE NOT NULL,
    f_gra DOUBLE NOT NULL,
    f_lea DOUBLE NOT NULL,
    PRIMARY KEY (region, animal, capri_region)
);
COMMENT ON TABLE env_manure_n2o_factors IS 'CAPRI''s manure N2O by source, per model region and animal, and the ammonia technologies'' N2O effects. (tools/build/build_manure_n2o.py)';
INSERT INTO value_units VALUES
  ('env_manure_n2o_factors', 'f_man', NULL, 'open', 'manure_n2o_factors.f_man: unit to be established'),
  ('env_manure_n2o_factors', 'f_app', NULL, 'open', 'manure_n2o_factors.f_app: unit to be established'),
  ('env_manure_n2o_factors', 'f_gra', NULL, 'open', 'manure_n2o_factors.f_gra: unit to be established'),
  ('env_manure_n2o_factors', 'f_lea', NULL, 'open', 'manure_n2o_factors.f_lea: unit to be established');

-- file: capri_data/2017/environment/manure_n2o_tech.csv
CREATE TABLE env_manure_n2o_tech (
    region VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    r_hou DOUBLE NOT NULL,
    r_app DOUBLE NOT NULL,
    PRIMARY KEY (region, animal, technology)
);
COMMENT ON TABLE env_manure_n2o_tech IS 'CAPRI''s manure N2O by source, per model region and animal, and the ammonia technologies'' N2O effects. (tools/build/build_manure_n2o.py)';
INSERT INTO value_units VALUES
  ('env_manure_n2o_tech', 'r_hou', NULL, 'open', 'manure_n2o_tech.r_hou: unit to be established'),
  ('env_manure_n2o_tech', 'r_app', NULL, 'open', 'manure_n2o_tech.r_app: unit to be established');

-- file: capri_data/2017/environment/manure_trade_2030.csv
CREATE TABLE env_manure_trade_2030 (
    region VARCHAR NOT NULL,
    export_share DOUBLE NOT NULL,
    import_kg_n_per_ha DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, source)
);
COMMENT ON TABLE env_manure_trade_2030 IS 'CAPRI''s 2030 manure trade per model region (manureTradeNew; Sprint 9j). (tools/build/build_manure_trade_base.py)';
INSERT INTO value_units VALUES
  ('env_manure_trade_2030', 'export_share', NULL, 'open', 'manure_trade_2030.export_share: unit to be established'),
  ('env_manure_trade_2030', 'import_kg_n_per_ha', NULL, 'open', 'manure_trade_2030.import_kg_n_per_ha: unit to be established');

-- file: capri_data/2017/environment/n_deposition_regional.csv
CREATE TABLE env_n_deposition_regional (
    region VARCHAR NOT NULL,
    deposition_kg_n_per_ha DOUBLE NOT NULL,
    source VARCHAR NOT NULL,
    PRIMARY KEY (region, source)
);
COMMENT ON TABLE env_n_deposition_regional IS 'Atmospheric N deposition and the fertiliser substitution terms per model region, from CAPRI''s 2030 reference. (tools/build/build_n_deposition_substitution.py)';
INSERT INTO value_units VALUES
  ('env_n_deposition_regional', 'deposition_kg_n_per_ha', NULL, 'open', 'n_deposition_regional.deposition_kg_n_per_ha: unit to be established');

-- file: capri_data/2017/environment/npk_crop_coefs_2030.csv
CREATE TABLE env_npk_crop_coefs_2030 (
    capri_region VARCHAR NOT NULL,
    model_crop VARCHAR NOT NULL,
    nutrient VARCHAR NOT NULL,
    levl_kha DOUBLE NOT NULL,
    need_kg_ha DOUBLE NOT NULL,
    pool_kg_ha DOUBLE NOT NULL,
    own_kg_ha DOUBLE NOT NULL,
    mine_kg_ha DOUBLE NOT NULL,
    main_share DOUBLE NOT NULL,
    straw_share DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, model_crop, nutrient)
);
COMMENT ON TABLE env_npk_crop_coefs_2030 IS 'CAPRI''s crop nutrient balance for N, P and K (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, (tools/build/build_npk_balance_2030.py)';
INSERT INTO value_units VALUES
  ('env_npk_crop_coefs_2030', 'levl_kha', NULL, 'open', 'npk_crop_coefs_2030.levl_kha: unit to be established'),
  ('env_npk_crop_coefs_2030', 'need_kg_ha', NULL, 'open', 'npk_crop_coefs_2030.need_kg_ha: unit to be established'),
  ('env_npk_crop_coefs_2030', 'pool_kg_ha', NULL, 'open', 'npk_crop_coefs_2030.pool_kg_ha: unit to be established'),
  ('env_npk_crop_coefs_2030', 'own_kg_ha', NULL, 'open', 'npk_crop_coefs_2030.own_kg_ha: unit to be established'),
  ('env_npk_crop_coefs_2030', 'mine_kg_ha', NULL, 'open', 'npk_crop_coefs_2030.mine_kg_ha: unit to be established'),
  ('env_npk_crop_coefs_2030', 'main_share', NULL, 'open', 'npk_crop_coefs_2030.main_share: unit to be established'),
  ('env_npk_crop_coefs_2030', 'straw_share', NULL, 'open', 'npk_crop_coefs_2030.straw_share: unit to be established');

-- file: capri_data/2017/environment/npk_region_2030.csv
CREATE TABLE env_npk_region_2030 (
    capri_region VARCHAR NOT NULL,
    "level" VARCHAR NOT NULL,
    nutrient VARCHAR NOT NULL,
    mine_eff DOUBLE NOT NULL,
    excr_avail DOUBLE NOT NULL,
    cres_avail DOUBLE NOT NULL,
    uvag_eur_t DOUBLE NOT NULL,
    mine_kt DOUBLE NOT NULL,
    excr_kt DOUBLE NOT NULL,
    pool_kt DOUBLE NOT NULL,
    own_kt DOUBLE NOT NULL,
    need_kt DOUBLE NOT NULL,
    land_kha DOUBLE NOT NULL,
    pool_scale DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, "level", nutrient)
);
COMMENT ON TABLE env_npk_region_2030 IS 'CAPRI''s crop nutrient balance for N, P and K (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_, (tools/build/build_npk_balance_2030.py)';
INSERT INTO value_units VALUES
  ('env_npk_region_2030', 'mine_eff', NULL, 'open', 'npk_region_2030.mine_eff: unit to be established'),
  ('env_npk_region_2030', 'excr_avail', NULL, 'open', 'npk_region_2030.excr_avail: unit to be established'),
  ('env_npk_region_2030', 'cres_avail', NULL, 'open', 'npk_region_2030.cres_avail: unit to be established'),
  ('env_npk_region_2030', 'uvag_eur_t', NULL, 'open', 'npk_region_2030.uvag_eur_t: unit to be established'),
  ('env_npk_region_2030', 'mine_kt', NULL, 'open', 'npk_region_2030.mine_kt: unit to be established'),
  ('env_npk_region_2030', 'excr_kt', NULL, 'open', 'npk_region_2030.excr_kt: unit to be established'),
  ('env_npk_region_2030', 'pool_kt', NULL, 'open', 'npk_region_2030.pool_kt: unit to be established'),
  ('env_npk_region_2030', 'own_kt', NULL, 'open', 'npk_region_2030.own_kt: unit to be established'),
  ('env_npk_region_2030', 'need_kt', NULL, 'open', 'npk_region_2030.need_kt: unit to be established'),
  ('env_npk_region_2030', 'land_kha', NULL, 'open', 'npk_region_2030.land_kha: unit to be established'),
  ('env_npk_region_2030', 'pool_scale', NULL, 'open', 'npk_region_2030.pool_scale: unit to be established');

-- file: capri_data/2017/environment/p_balance_crop_coefs_2030.csv
CREATE TABLE env_p_balance_crop_coefs_2030 (
    capri_region VARCHAR NOT NULL,
    model_crop VARCHAR NOT NULL,
    levl_kha DOUBLE NOT NULL,
    pret_kg_ha DOUBLE NOT NULL,
    pcrd_kg_ha DOUBLE NOT NULL,
    PRIMARY KEY (capri_region, model_crop)
);
COMMENT ON TABLE env_p_balance_crop_coefs_2030 IS 'CAPRI''s gross phosphate (P2O5) balance (reports/calc_nbalance.gms, FNUT = PHOF), the coefficients the environmental (tools/build/build_p_balance.py)';
INSERT INTO value_units VALUES
  ('env_p_balance_crop_coefs_2030', 'levl_kha', NULL, 'open', 'p_balance_crop_coefs_2030.levl_kha: unit to be established'),
  ('env_p_balance_crop_coefs_2030', 'pret_kg_ha', NULL, 'open', 'p_balance_crop_coefs_2030.pret_kg_ha: unit to be established'),
  ('env_p_balance_crop_coefs_2030', 'pcrd_kg_ha', NULL, 'open', 'p_balance_crop_coefs_2030.pcrd_kg_ha: unit to be established');

-- file: capri_data/2017/environment/livestock_ch4ent_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_ch4ent_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_ch4ent_coef IS 'CAPRI''s enteric methane CH4ENT per model head (LEVL x item over the model''s heads, tools/build/build_ghg_coefs_2017.py)';
INSERT INTO value_units SELECT 'env_livestock_ch4ent_coef', code, 'U_kgperhd', 'builder', 'kg CH4 per head (the builder: CAPRI''s kg CH4 per unit over the model''s heads)' FROM model_activities WHERE kind = 'animal';

-- file: capri_data/2017/environment/livestock_ch4man_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_ch4man_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_ch4man_coef IS 'CAPRI''s manure methane CH4MAN per model head (tools/build/build_ghg_coefs_2017.py)';
INSERT INTO value_units SELECT 'env_livestock_ch4man_coef', code, 'U_kgperhd', 'builder', 'kg CH4 per head' FROM model_activities WHERE kind = 'animal';

-- file: capri_data/2017/environment/livestock_manure_n_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_manure_n_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_manure_n_coef IS 'CAPRI''s manure N (MANN) per model head (LEVL x item over the model''s heads, tools/build/build_livestock_output_coef.py)';
INSERT INTO value_units SELECT 'env_livestock_manure_n_coef', code, 'U_kgperhd', 'builder', 'kg N per head' FROM model_activities WHERE kind = 'animal';

-- file: capri_data/2017/environment/livestock_manure_p_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_manure_p_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_manure_p_coef IS 'CAPRI''s manure P (MANP) per model head (the regional total over the model''s herd, tools/build/build_npk_balance_2030.py)';
INSERT INTO value_units SELECT 'env_livestock_manure_p_coef', code, 'U_kgperhd', 'builder', 'kg P2O5 per head (CAPRI''s P item in P2O5)' FROM model_activities WHERE kind = 'animal';

-- file: capri_data/2017/environment/livestock_manure_k_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_manure_k_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_manure_k_coef IS 'CAPRI''s manure K (MANK) per model head (tools/build/build_npk_balance_2030.py)';
INSERT INTO value_units SELECT 'env_livestock_manure_k_coef', code, 'U_kgperhd', 'builder', 'kg K2O per head (CAPRI''s K item in K2O)' FROM model_activities WHERE kind = 'animal';

-- file: capri_data/2017/environment/livestock_n_export_coef.csv
-- layout: wide, unnamed
CREATE TABLE env_livestock_n_export_coef (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value >= 0),        -- empty: the animal has no herd in the region
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE env_livestock_n_export_coef IS 'CAPRI''s N exported in animal products CRPR_EXPT per model head (fert/calc_nexport.gms; tools/build/build_livestock_n_export_coef.py)';
INSERT INTO value_units SELECT 'env_livestock_n_export_coef', code, 'U_kgperhd', 'builder', 'kg N per head' FROM model_activities WHERE kind = 'animal';

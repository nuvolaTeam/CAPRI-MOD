-- The supply models' land rents, own-price supply elasticities, fertiliser coefficients and the mineral N price.
-- Long files: the unit of each numeric column is in value_units, the column's name as the item.

-- file: capri_data/2017/supply/land_rents_2030.csv
CREATE TABLE land_rents_2030 (
    region VARCHAR PRIMARY KEY REFERENCES regional_units (region),
    capri_source VARCHAR NOT NULL,                     -- the CAPRI region(s) the rents are from (free text)
    rent_arac DOUBLE NOT NULL CHECK (rent_arac > 0),
    rent_frun DOUBLE NOT NULL CHECK (rent_frun > 0),
    rent_gras DOUBLE CHECK (rent_gras > 0)             -- empty: no grassland rent where the region has none
);
COMMENT ON TABLE land_rents_2030 IS 'CAPRI''s land rents at the 2030 reference: D_AREA of ARAC and FRUN, -D_AREA of GRAS; CAPRI''s calibration rule (supply/cal_land_nests.gms l. 204-226) where D_AREA is not positive; territory groups area-weighted, else the member state''s (tools/build/build_land_rents.py)';
INSERT INTO value_units VALUES
  ('land_rents_2030', 'rent_arac', 'U_EuPerHa', 'builder', 'CAPRI''s D_AREA of ARAC, the land balance''s dual (EUR/ha)'),
  ('land_rents_2030', 'rent_frun', 'U_EuPerHa', 'builder', 'CAPRI''s D_AREA of FRUN (EUR/ha)'),
  ('land_rents_2030', 'rent_gras', 'U_EuPerHa', 'builder', 'minus CAPRI''s D_AREA of GRAS (EUR/ha)');

-- file: capri_data/2017/supply/land_rents_2017.csv
CREATE TABLE land_rents_2017 (
    region VARCHAR PRIMARY KEY REFERENCES regional_units (region),
    capri_source VARCHAR NOT NULL,
    rent_arac DOUBLE NOT NULL CHECK (rent_arac > 0),
    rent_frun DOUBLE NOT NULL CHECK (rent_frun > 0),
    rent_gras DOUBLE CHECK (rent_gras > 0)
);
COMMENT ON TABLE land_rents_2017 IS 'CAPRI''s land rents at 2017 (res_17<MS> D_AREA ''Y''), the same rules as land_rents_2030 (tools/build/build_land_rents.py --year 2017); the land market at the 2017 market year';
INSERT INTO value_units VALUES
  ('land_rents_2017', 'rent_arac', 'U_EuPerHa', 'builder', 'CAPRI''s D_AREA of ARAC (EUR/ha)'),
  ('land_rents_2017', 'rent_frun', 'U_EuPerHa', 'builder', 'CAPRI''s D_AREA of FRUN (EUR/ha)'),
  ('land_rents_2017', 'rent_gras', 'U_EuPerHa', 'builder', 'minus CAPRI''s D_AREA of GRAS (EUR/ha)');

-- file: capri_data/2017/supply/supply_elasticities_regional.csv
-- layout: wide
CREATE TABLE supply_elasticities_regional (
    model_region VARCHAR NOT NULL REFERENCES regional_units (region),
    crop VARCHAR NOT NULL CHECK (crop IN ('BARL', 'CORN', 'DWHE', 'MAIF', 'OATS', 'OCER', 'OFAR', 'POTA', 'PULS', 'RAPE',
                                          'RYEM', 'SOYA', 'SUGB', 'SUNF', 'SWHE')),
                                          -- model codes, except CAPRI's OFAR (read as the model's OFOD, loaders l. 339)
    value DOUBLE CHECK (value > 0 AND value <= 8),     -- empty: PELA has none; <= 8: CAPRI's bound min(8, ...)
    PRIMARY KEY (model_region, crop)
);
COMMENT ON TABLE supply_elasticities_regional IS 'CAPRI''s estimated own-price supply elasticities of 15 arable crops (dat/estnlp/results.gdx PELA, 2005 slice) per model region, above 4.5 bounded by CAPRI''s rule min(8, sqrt(e) + 4.5 - sqrt(4.5)) (impose_upper_bound_on_elasticity.gms; tools/build/build_supply_elasticities_regional.py)';
INSERT INTO value_units SELECT 'supply_elasticities_regional', c, 'U_Elasticity', 'capri', 'CAPRI''s PELA (own-price elasticity of the activity''s level)'
FROM (VALUES ('BARL'), ('CORN'), ('DWHE'), ('MAIF'), ('OATS'), ('OCER'), ('OFAR'), ('POTA'), ('PULS'), ('RAPE'), ('RYEM'),
             ('SOYA'), ('SUGB'), ('SUNF'), ('SWHE')) t(c);

-- file: capri_data/2017/supply/pmp_own_price_elasticities.csv
CREATE TABLE pmp_own_price_elasticities (
    region VARCHAR NOT NULL REFERENCES capri_rall (code),
    crop VARCHAR NOT NULL REFERENCES capri_pact (code),
    own_price_elas DOUBLE NOT NULL CHECK (own_price_elas > 0),
    PRIMARY KEY (region, crop)
);
COMMENT ON TABLE pmp_own_price_elasticities IS 'CAPRI''s estimated own-price elasticities (PELA) per CAPRI region and CAPRI activity, raw (bounded on load, capri_pmp.dampen_elasticity); the elasticity-calibrated PMP''s PMP_CAPRI source (docs/PMP_ELASTICITY_WIRING.md), not the default PMP (CAPRI''s 2030 terms). No builder in the repository (DATA_SOURCING_REGISTRY: CAPRI PELA)';
INSERT INTO value_units VALUES
  ('pmp_own_price_elasticities', 'own_price_elas', 'U_Elasticity', 'capri', 'CAPRI''s PELA, own-price, unbounded');

-- file: capri_data/2017/supply/capri_own_price_elasticities.csv
-- layout: wide
CREATE TABLE capri_own_price_elasticities (
    capri_country VARCHAR NOT NULL,
    product VARCHAR NOT NULL REFERENCES capri_xx (code),
    value DOUBLE CHECK (value > 0),                    -- empty: no supply elasticity of the product in the country
    PRIMARY KEY (capri_country, product)
);
COMMENT ON TABLE capri_own_price_elasticities IS 'CAPRI''s calibrated own-price supply elasticities p_ElasSupp (''CAL'', results/arm supply_elas_*) per member state (CAPRI''s two-letter country, BL = BE + LU, IR = IE) and product; the elasticity-calibrated PMP''s CAPRI_COUNTRY source for activities no regional source covers (docs/PMP_ELASTICITY_WIRING.md), not the default PMP. No builder in the repository';
INSERT INTO value_units SELECT 'capri_own_price_elasticities', c, 'U_Elasticity', 'capri', 'CAPRI''s p_ElasSupp (own-price elasticity of supply)'
FROM (VALUES ('RYEM'), ('BARL'), ('OATS'), ('MAIZ'), ('OCER'), ('RAPE'), ('SUNF'), ('PULS'), ('POTA'), ('TEXT'), ('TOBA'),
             ('TOMA'), ('OVEG'), ('APPL'), ('OFRU'), ('TAGR'), ('TWIN'), ('YCOW'), ('YBUL'), ('YHEI'), ('YCAM'), ('YCAF'),
             ('YPIG'), ('YLAM'), ('BEEF'), ('PORK'), ('SGMT'), ('EGGS'), ('POUM'), ('SOYA'), ('CITR'), ('TABO')) t(c);

-- file: capri_data/2017/supply/nutrient_coefs_regional.csv
CREATE TABLE nutrient_coefs_regional (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    activity VARCHAR NOT NULL REFERENCES model_activities (code),
    N DOUBLE NOT NULL CHECK (N >= 0),
    P2O5 DOUBLE NOT NULL CHECK (P2O5 >= 0),
    K2O DOUBLE NOT NULL CHECK (K2O >= 0),
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE nutrient_coefs_regional IS 'CAPRI''s fertiliser coefficients NITF, PHOF, POTF of res_17<MS> DATA2 per region and model crop, level-weighted over the crop''s CAPRI activities (build_capri_base.CROP_MAP), the member state''s for a crop the region does not grow (tools/build/build_nutrient_coefs_regional.py, K100)';
INSERT INTO value_units VALUES
  ('nutrient_coefs_regional', 'N', 'U_kgperha', 'capri', 'CAPRI''s NITF (kg N per ha; CAPRI''s N requirement NRET)'),
  ('nutrient_coefs_regional', 'P2O5', 'U_kgperha', 'capri', 'CAPRI''s PHOF (kg P2O5 per ha)'),
  ('nutrient_coefs_regional', 'K2O', 'U_kgperha', 'capri', 'CAPRI''s POTF (kg K2O per ha)');

-- rule: the fertiliser coefficients are the crops', and every crop with area in a region has its coefficients
SELECT region, activity, 'not a crop' AS what FROM nutrient_coefs_regional
WHERE activity NOT IN (SELECT code FROM model_activities WHERE kind = 'crop')
UNION ALL
SELECT b.region, b.activity, 'crop with area, no coefficients' FROM base_areas b
WHERE b.value > 0 AND NOT EXISTS (SELECT 1 FROM nutrient_coefs_regional n WHERE n.region = b.region AND n.activity = b.activity);

-- file: capri_data/2017/supply/mineral_n_price.csv
CREATE TABLE mineral_n_price (
    country VARCHAR PRIMARY KEY,                       -- NUTS country prefix
    capri_code VARCHAR NOT NULL,                       -- CAPRI's two-letter country (BL for BE and LU, IR for IE)
    eur_per_t_n DOUBLE NOT NULL CHECK (eur_per_t_n > 0)
);
COMMENT ON TABLE mineral_n_price IS 'CAPRI''s 2017 unit value of mineral N fertiliser per country (res_17* national UVAG of NITF); read only with use_fert_allocation (off by default). No builder in the repository';
INSERT INTO value_units VALUES
  ('mineral_n_price', 'eur_per_t_n', 'U_EuPerTon', 'capri', 'CAPRI''s UVAG of NITF, EUR per t of N');

-- rule: the countries are CAPRI's member states (and Norway), as two-letter codes of RALL's national units
SELECT 'capri_own_price_elasticities' AS tbl, capri_country AS code FROM capri_own_price_elasticities
WHERE capri_country || '000000' NOT IN (SELECT code FROM capri_rall)
UNION ALL
SELECT 'mineral_n_price', capri_code FROM mineral_n_price WHERE capri_code || '000000' NOT IN (SELECT code FROM capri_rall)
UNION ALL
SELECT 'mineral_n_price', country FROM mineral_n_price m
WHERE NOT EXISTS (SELECT 1 FROM regional_units r WHERE r.country = m.country);

-- rule: every model region has its land rents in both years
SELECT r.region FROM regional_units r
WHERE r.region NOT IN (SELECT region FROM land_rents_2030) OR r.region NOT IN (SELECT region FROM land_rents_2017);

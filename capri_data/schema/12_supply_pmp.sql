-- The supply models' PMP terms (CAPRI's quadratic cost, supply/supply_model.gms QUADRA_, GRPLEVL_): CAPRI's 2030
-- terms and capri-mod's own with CAPRI's recipe, per model region (loaders._load_pmp_capri_2030; SupplyModule.pmp_source).
-- At run time Q_ij = g_ij / sqrt(x_i x_j) with the region's own base levels x (PMPCalibrator), so g is the curvature
-- per 100% change of the levels. Long files: the unit of each numeric column is in value_units, the column's name as
-- the item. Units: CAPRI's objective is in 1000 EUR (levels in 1000 ha or CAPRI's head units x values per unit), so a
-- crop's g is in EUR/ha and an animal's in EUR per model head (h X / r: 1000 EUR per CAPRI level unit, over the
-- model's 1000 head per CAPRI level unit).

-- file: capri_data/2017/supply/pmp_capri_2030.csv
CREATE TABLE pmp_capri_2030 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    act_i VARCHAR NOT NULL REFERENCES model_activities (code),
    act_j VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL,
    x_i DOUBLE NOT NULL CHECK (x_i > 0),
    x_j DOUBLE NOT NULL CHECK (x_j > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, act_i, act_j),
    CHECK (act_i <> act_j OR (g > 0 AND x_i = x_j))
);
COMMENT ON TABLE pmp_capri_2030 IS 'CAPRI''s 2030 PMP terms of the crops (p_pmpQuadTechn, p_pmpQuadPact of the project lead''s 2030 baseline calibration) as the Hessian on the model''s activities per territory group, g_ij = H_ij sqrt(X_i X_j) (tools/build/build_pmp_capri_2030.py, K61)';
INSERT INTO value_units VALUES
  ('pmp_capri_2030', 'g', 'U_EuPerHa', 'builder', 'H x sqrt(X_i X_j): CAPRI''s PMP Hessian (1000 EUR per (1000 ha)^2) times the levels (1000 ha); the marginal cost''s change in EUR/ha for a 100% change of the levels'),
  ('pmp_capri_2030', 'x_i', 'U_1000ha', 'capri', 'CAPRI''s 2030 reference LEVL of the territory group, summed over the model activity''s CAPRI activities'),
  ('pmp_capri_2030', 'x_j', 'U_1000ha', 'capri', 'CAPRI''s 2030 reference LEVL of the territory group, summed over the model activity''s CAPRI activities');

-- file: capri_data/2017/supply/pmp_recipe_2017.csv
CREATE TABLE pmp_recipe_2017 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    act_i VARCHAR NOT NULL REFERENCES model_activities (code),
    act_j VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL,
    x_i DOUBLE NOT NULL CHECK (x_i > 0),
    x_j DOUBLE NOT NULL CHECK (x_j > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, act_i, act_j),
    CHECK (act_i <> act_j OR (g > 0 AND x_i = x_j))
);
COMMENT ON TABLE pmp_recipe_2017 IS 'capri-mod''s own crop PMP terms with CAPRI''s recipe (supply/define_pmp_terms.gms) at the 2017 calibration point, as the Hessian on the model''s activities per territory group (tools/build/build_pmp_recipe.py, K61)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2017', 'g', 'U_EuPerHa', 'builder', 'H x sqrt(X_i X_j): CAPRI''s PMP Hessian (1000 EUR per (1000 ha)^2) times the levels (1000 ha); the marginal cost''s change in EUR/ha for a 100% change of the levels'),
  ('pmp_recipe_2017', 'x_i', 'U_1000ha', 'capri', 'CAPRI''s 2017 LEVL (res_17) of the territory group, summed over the model activity''s CAPRI activities'),
  ('pmp_recipe_2017', 'x_j', 'U_1000ha', 'capri', 'CAPRI''s 2017 LEVL (res_17) of the territory group, summed over the model activity''s CAPRI activities');

-- file: capri_data/2017/supply/pmp_recipe_2030.csv
CREATE TABLE pmp_recipe_2030 (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    act_i VARCHAR NOT NULL REFERENCES model_activities (code),
    act_j VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL,
    x_i DOUBLE NOT NULL CHECK (x_i > 0),
    x_j DOUBLE NOT NULL CHECK (x_j > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, act_i, act_j),
    CHECK (act_i <> act_j OR (g > 0 AND x_i = x_j))
);
COMMENT ON TABLE pmp_recipe_2030 IS 'capri-mod''s own crop PMP terms with CAPRI''s recipe (supply/define_pmp_terms.gms) at the 2030 calibration point, as the Hessian on the model''s activities per territory group (tools/build/build_pmp_recipe.py, K61)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2030', 'g', 'U_EuPerHa', 'builder', 'H x sqrt(X_i X_j): CAPRI''s PMP Hessian (1000 EUR per (1000 ha)^2) times the levels (1000 ha); the marginal cost''s change in EUR/ha for a 100% change of the levels'),
  ('pmp_recipe_2030', 'x_i', 'U_1000ha', 'capri', 'CAPRI''s 2030 reference LEVL of the territory group, summed over the model activity''s CAPRI activities'),
  ('pmp_recipe_2030', 'x_j', 'U_1000ha', 'capri', 'CAPRI''s 2030 reference LEVL of the territory group, summed over the model activity''s CAPRI activities');

-- file: capri_data/2017/supply/pmp_capri_2030_animals.csv
CREATE TABLE pmp_capri_2030_animals (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_capri_2030_animals IS 'CAPRI''s 2030 PMP terms of the animal activities (p_pmpQuadTechn(act, T, T)) as herd curvature per model animal, intensity pairs DCOL/DCOH, BULL/BULH, HEIL/HEIH by their Schur complement, g = h X / r (tools/build/build_animal_pmp_capri_2030.py, K61)';
INSERT INTO value_units VALUES
  ('pmp_capri_2030_animals', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_capri_2030_animals', 'x_capri', NULL, 'open', 'CAPRI''s 2030 reference LEVL of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_capri_2030_animals', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- file: capri_data/2017/supply/pmp_capri_2030_animals_members.csv
CREATE TABLE pmp_capri_2030_animals_members (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_capri_2030_animals_members IS 'as pmp_capri_2030_animals with the heifers'' three activities and the calves per sex as split members (--splits; read only with RegionalSupplyModel.use_cattle_member_splits, off by default, K65)';
INSERT INTO value_units VALUES
  ('pmp_capri_2030_animals_members', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_capri_2030_animals_members', 'x_capri', NULL, 'open', 'CAPRI''s 2030 reference LEVL of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_capri_2030_animals_members', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- file: capri_data/2017/supply/pmp_recipe_2017_animals.csv
CREATE TABLE pmp_recipe_2017_animals (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_recipe_2017_animals IS 'capri-mod''s own animal PMP terms with CAPRI''s recipe at the 2017 calibration point, as herd curvature per model animal (tools/build/build_pmp_recipe.py, build_animal_pmp_capri_2030.py)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2017_animals', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_recipe_2017_animals', 'x_capri', NULL, 'open', 'CAPRI''s 2017 LEVL (res_17) of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_recipe_2017_animals', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- file: capri_data/2017/supply/pmp_recipe_2017_animals_members.csv
CREATE TABLE pmp_recipe_2017_animals_members (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_recipe_2017_animals_members IS 'as pmp_recipe_2017_animals with the heifers'' and calves'' split members (--splits; read only with use_cattle_member_splits, K65)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2017_animals_members', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_recipe_2017_animals_members', 'x_capri', NULL, 'open', 'CAPRI''s 2017 LEVL (res_17) of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_recipe_2017_animals_members', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- file: capri_data/2017/supply/pmp_recipe_2030_animals.csv
CREATE TABLE pmp_recipe_2030_animals (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_recipe_2030_animals IS 'capri-mod''s own animal PMP terms with CAPRI''s recipe at the 2030 calibration point, as herd curvature per model animal (tools/build/build_pmp_recipe.py, build_animal_pmp_capri_2030.py)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2030_animals', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_recipe_2030_animals', 'x_capri', NULL, 'open', 'CAPRI''s 2030 reference LEVL of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_recipe_2030_animals', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- file: capri_data/2017/supply/pmp_recipe_2030_animals_members.csv
CREATE TABLE pmp_recipe_2030_animals_members (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    g DOUBLE NOT NULL CHECK (g > 0),
    x_capri DOUBLE NOT NULL CHECK (x_capri > 0),
    level_ratio DOUBLE NOT NULL CHECK (level_ratio > 0),
    capri_regions VARCHAR NOT NULL,                    -- the territory group's CAPRI regions, space-separated
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE pmp_recipe_2030_animals_members IS 'as pmp_recipe_2030_animals with the heifers'' and calves'' split members (--splits; read only with use_cattle_member_splits, K65)';
INSERT INTO value_units VALUES
  ('pmp_recipe_2030_animals_members', 'g', 'U_EuPerHd', 'builder', 'h X / r: CAPRI''s herd curvature (1000 EUR per CAPRI level unit squared) times the level over level_ratio; EUR per model head for a 100% change of the herd'),
  ('pmp_recipe_2030_animals_members', 'x_capri', NULL, 'open', 'CAPRI''s 2030 reference LEVL of the animal''s CAPRI activities in CAPRI''s unit of each: 1000 head (U_1000hd), poultry (LAYS, BROI) million head (U_Miohd); two units in one column'),
  ('pmp_recipe_2030_animals_members', 'level_ratio', 'U_ratio', 'builder', 'the model''s herd (1000 head) per unit of CAPRI''s LEVL (capri_level_ratio.csv, tools/build/build_capri_level_ratio.py)');

-- rule: the crop terms are symmetric (g_ij = g_ji, both stored) and their activities are crops
SELECT 'pmp_capri_2030' AS tbl, a.region, a.act_i, a.act_j FROM pmp_capri_2030 a
LEFT JOIN pmp_capri_2030 b ON b.region = a.region AND b.act_i = a.act_j AND b.act_j = a.act_i
WHERE b.g IS NULL OR abs(a.g - b.g) > 1e-9 * greatest(abs(a.g), 1)
   OR a.act_i NOT IN (SELECT code FROM model_activities WHERE kind = 'crop')
UNION ALL
SELECT 'pmp_recipe_2017' AS tbl, a.region, a.act_i, a.act_j FROM pmp_recipe_2017 a
LEFT JOIN pmp_recipe_2017 b ON b.region = a.region AND b.act_i = a.act_j AND b.act_j = a.act_i
WHERE b.g IS NULL OR abs(a.g - b.g) > 1e-9 * greatest(abs(a.g), 1)
   OR a.act_i NOT IN (SELECT code FROM model_activities WHERE kind = 'crop')
UNION ALL
SELECT 'pmp_recipe_2030' AS tbl, a.region, a.act_i, a.act_j FROM pmp_recipe_2030 a
LEFT JOIN pmp_recipe_2030 b ON b.region = a.region AND b.act_i = a.act_j AND b.act_j = a.act_i
WHERE b.g IS NULL OR abs(a.g - b.g) > 1e-9 * greatest(abs(a.g), 1)
   OR a.act_i NOT IN (SELECT code FROM model_activities WHERE kind = 'crop');

-- rule: each activity has one level per region (x_i the same in every term of the activity) and its diagonal term
SELECT 'pmp_capri_2030' AS tbl, region, act_i FROM pmp_capri_2030 GROUP BY region, act_i
HAVING count(DISTINCT x_i) > 1 OR count(*) FILTER (WHERE act_i = act_j) <> 1
UNION ALL
SELECT 'pmp_recipe_2017' AS tbl, region, act_i FROM pmp_recipe_2017 GROUP BY region, act_i
HAVING count(DISTINCT x_i) > 1 OR count(*) FILTER (WHERE act_i = act_j) <> 1
UNION ALL
SELECT 'pmp_recipe_2030' AS tbl, region, act_i FROM pmp_recipe_2030 GROUP BY region, act_i
HAVING count(DISTINCT x_i) > 1 OR count(*) FILTER (WHERE act_i = act_j) <> 1;

-- rule: the animal terms' activities are animals
SELECT 'pmp_capri_2030_animals' AS tbl, region, animal FROM pmp_capri_2030_animals WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
UNION ALL
SELECT 'pmp_capri_2030_animals_members' AS tbl, region, animal FROM pmp_capri_2030_animals_members WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
UNION ALL
SELECT 'pmp_recipe_2017_animals' AS tbl, region, animal FROM pmp_recipe_2017_animals WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
UNION ALL
SELECT 'pmp_recipe_2017_animals_members' AS tbl, region, animal FROM pmp_recipe_2017_animals_members WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
UNION ALL
SELECT 'pmp_recipe_2030_animals' AS tbl, region, animal FROM pmp_recipe_2030_animals WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal')
UNION ALL
SELECT 'pmp_recipe_2030_animals_members' AS tbl, region, animal FROM pmp_recipe_2030_animals_members WHERE animal NOT IN (SELECT code FROM model_activities WHERE kind = 'animal');

-- rule: every CAPRI region named in a territory group is in CAPRI's RALL
SELECT tbl, code FROM (
SELECT DISTINCT 'pmp_capri_2030' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_capri_2030
UNION ALL
SELECT DISTINCT 'pmp_recipe_2017' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2017
UNION ALL
SELECT DISTINCT 'pmp_recipe_2030' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2030
UNION ALL
SELECT DISTINCT 'pmp_capri_2030_animals' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_capri_2030_animals
UNION ALL
SELECT DISTINCT 'pmp_capri_2030_animals_members' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_capri_2030_animals_members
UNION ALL
SELECT DISTINCT 'pmp_recipe_2017_animals' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2017_animals
UNION ALL
SELECT DISTINCT 'pmp_recipe_2017_animals_members' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2017_animals_members
UNION ALL
SELECT DISTINCT 'pmp_recipe_2030_animals' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2030_animals
UNION ALL
SELECT DISTINCT 'pmp_recipe_2030_animals_members' AS tbl, unnest(string_split(capri_regions, ' ')) AS code FROM pmp_recipe_2030_animals_members
) t WHERE code NOT IN (SELECT code FROM capri_rall);

-- rule: a region's animal terms and its crop terms come from the same territory group (the same CAPRI regions)
SELECT DISTINCT 'pmp_capri_2030_animals' AS tbl, a.region FROM pmp_capri_2030_animals a JOIN pmp_capri_2030 c ON c.region = a.region WHERE c.capri_regions <> a.capri_regions
UNION ALL
SELECT DISTINCT 'pmp_recipe_2017_animals' AS tbl, a.region FROM pmp_recipe_2017_animals a JOIN pmp_recipe_2017 c ON c.region = a.region WHERE c.capri_regions <> a.capri_regions
UNION ALL
SELECT DISTINCT 'pmp_recipe_2030_animals' AS tbl, a.region FROM pmp_recipe_2030_animals a JOIN pmp_recipe_2030 c ON c.region = a.region WHERE c.capri_regions <> a.capri_regions;

-- file: capri_data/2017/supply/capri_level_ratio.csv
-- layout: wide, unnamed
CREATE TABLE capri_level_ratio (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    value DOUBLE CHECK (value > 0),       -- empty: the region has no CAPRI level of the animal
    PRIMARY KEY (region, animal)
);
COMMENT ON TABLE capri_level_ratio IS 'the model''s base herd per unit of CAPRI''s 2017 LEVL of the animal''s CAPRI activities, per territory group (tools/build/build_capri_level_ratio.py, K27): converts CAPRI''s additive bound and the PMP herd terms to the model''s heads';
INSERT INTO value_units SELECT 'capri_level_ratio', code, 'U_ratio', 'builder', 'the model''s herd (1000 head; poultry converted from CAPRI''s million) over CAPRI''s LEVL in CAPRI''s unit of the activity'
FROM model_activities WHERE kind = 'animal' AND code NOT IN ('OANI');

-- rule: the animal terms' level ratio is capri_level_ratio.csv's
SELECT 'pmp_capri_2030_animals' AS tbl, a.region, a.animal FROM pmp_capri_2030_animals a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9
UNION ALL
SELECT 'pmp_capri_2030_animals_members' AS tbl, a.region, a.animal FROM pmp_capri_2030_animals_members a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9
UNION ALL
SELECT 'pmp_recipe_2017_animals' AS tbl, a.region, a.animal FROM pmp_recipe_2017_animals a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9
UNION ALL
SELECT 'pmp_recipe_2017_animals_members' AS tbl, a.region, a.animal FROM pmp_recipe_2017_animals_members a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9
UNION ALL
SELECT 'pmp_recipe_2030_animals' AS tbl, a.region, a.animal FROM pmp_recipe_2030_animals a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9
UNION ALL
SELECT 'pmp_recipe_2030_animals_members' AS tbl, a.region, a.animal FROM pmp_recipe_2030_animals_members a LEFT JOIN capri_level_ratio r ON r.region = a.region AND r.animal = a.animal
WHERE r.value IS NULL OR abs(a.level_ratio / r.value - 1) > 1e-9;

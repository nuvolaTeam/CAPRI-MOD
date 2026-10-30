-- CAPRI's Green Deal targets per member state, the organic yield gaps and the yields' price elasticities.
-- Long files: the unit of each numeric column is in value_units (99_rules.sql).

-- file: capri_data/2017/policy/landscape_targets_ms.csv
CREATE TABLE landscape_targets_ms (
    member_state VARCHAR PRIMARY KEY,                   -- NUTS-0 code, as CAPRI's files key them
    landscape_pp DOUBLE CHECK (landscape_pp >= 0 AND landscape_pp <= 100)   -- empty: CAPRI sets no target
);
COMMENT ON TABLE landscape_targets_ms IS 'CAPRI''s p_landscapeTargets: share of UAA in non-productive landscape elements to reach (gams/pol_input/greendeal/landscape_targets.gdx; tools/build/build_greendeal_targets.py)';
INSERT INTO value_units VALUES ('landscape_targets_ms', 'landscape_pp', 'U_percent', 'capri', 'p_landscapeTargets, percent of UAA');

-- file: capri_data/2017/policy/organic_targets_ms.csv
CREATE TABLE organic_targets_ms (
    member_state VARCHAR PRIMARY KEY,
    arable_pp DOUBLE CHECK (arable_pp >= 0 AND arable_pp <= 100),
    grassland_pp DOUBLE CHECK (grassland_pp >= 0 AND grassland_pp <= 100),
    permanent_pp DOUBLE CHECK (permanent_pp >= 0 AND permanent_pp <= 100),
    uaa_pp DOUBLE CHECK (uaa_pp >= 0 AND uaa_pp <= 100)
);
COMMENT ON TABLE organic_targets_ms IS 'CAPRI''s organic targets per member state: p_organicTargetMS (ARA, J0000, PECR) and p_organicTargetUAA (gams/pol_input/greendeal/organic_targets*.gdx; tools/build/build_greendeal_targets.py)';
INSERT INTO value_units VALUES
  ('organic_targets_ms', 'arable_pp', 'U_percent', 'capri', 'p_organicTargetMS(MS, ARA)'),
  ('organic_targets_ms', 'grassland_pp', 'U_percent', 'capri', 'p_organicTargetMS(MS, J0000)'),
  ('organic_targets_ms', 'permanent_pp', 'U_percent', 'capri', 'p_organicTargetMS(MS, PECR)'),
  ('organic_targets_ms', 'uaa_pp', 'U_percent', 'capri', 'p_organicTargetUAA(MS)');

-- file: capri_data/2017/policy/organic_yield_gap.csv
CREATE TABLE organic_yield_gap (
    peseta_region VARCHAR PRIMARY KEY CHECK (peseta_region IN ('CEN', 'CES', 'NE', 'SE', 'UK_IR')),
    cereals DOUBLE CHECK (cereals BETWEEN -100 AND 0),
    fruits DOUBLE CHECK (fruits BETWEEN -100 AND 0),
    grass DOUBLE CHECK (grass BETWEEN -100 AND 0),
    maize DOUBLE CHECK (maize BETWEEN -100 AND 0),
    milk DOUBLE CHECK (milk BETWEEN -100 AND 0),
    nonfruit_perm DOUBLE CHECK (nonfruit_perm BETWEEN -100 AND 0),
    oilseeds DOUBLE CHECK (oilseeds BETWEEN -100 AND 0),
    vegetables DOUBLE CHECK (vegetables BETWEEN -100 AND 0),
    wheat DOUBLE CHECK (wheat BETWEEN -100 AND 0)
);
COMMENT ON TABLE organic_yield_gap IS 'organic-to-conventional yield gaps per PESETA macro-region and product group, FADN estimates by the JRC (SUPREMA), CAPRI''s dat/pesticides/yield_effects_ppp.xlsx sheet yld_gap (tools/build/build_organic_yield_gap.py)';
INSERT INTO value_units SELECT 'organic_yield_gap', c, 'U_percent', 'capri', 'percent difference of organic to conventional yield'
FROM (VALUES ('cereals'), ('fruits'), ('grass'), ('maize'), ('milk'), ('nonfruit_perm'), ('oilseeds'), ('vegetables'),
             ('wheat')) t(c);

-- file: capri_data/2017/policy/organic_yield_gap_regions.csv
CREATE TABLE organic_yield_gap_regions (
    ms VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    peseta_region VARCHAR NOT NULL REFERENCES organic_yield_gap (peseta_region)
);
COMMENT ON TABLE organic_yield_gap_regions IS 'CAPRI''s member states and their PESETA macro-region of the organic yield gaps: set ms2peseta of inputs/load_organic_yieldgap.gms (tools/build/build_organic_yield_gap.py)';

-- file: capri_data/2017/policy/organic_yield_gap_groups.csv
CREATE TABLE organic_yield_gap_groups (
    activity VARCHAR PRIMARY KEY REFERENCES model_activities (code),
    "group" VARCHAR NOT NULL CHECK ("group" IN ('cereals', 'fruits', 'grass', 'maize', 'milk', 'nonfruit_perm', 'oilseeds', 'vegetables', 'wheat'))
);
COMMENT ON TABLE organic_yield_gap_groups IS 'the model''s crops and their product group of the organic yield gaps: set pact2yieldGap of inputs/load_organic_yieldgap.gms through the CAPRI supply-model codes of codes/model_activities.csv; the animals left out as CAPRI leaves them out of organicCrops (tools/build/build_organic_yield_gap.py)';

-- file: capri_data/2017/supply/yield_price_elasticity.csv
CREATE TABLE yield_price_elasticity (
    crop VARCHAR PRIMARY KEY REFERENCES model_activities (code),
    elasticity DOUBLE NOT NULL CHECK (elasticity > 0),
    source VARCHAR NOT NULL
);
COMMENT ON TABLE yield_price_elasticity IS 'CAPRI''s p_yieldElas (supply/yield_elas.gms: cereals 0.3, oilseeds 0.2, potatoes 0.2) on the model''s crops (tools/build/build_yield_price_elasticity.py)';
INSERT INTO value_units VALUES ('yield_price_elasticity', 'elasticity', 'U_Elasticity', 'capri', 'p_yieldElas, yield on own price');

-- rule: the targets' member states are the EU's (NUTS-0 prefixes of CAPRI's member states)
SELECT 'landscape' AS tbl, member_state FROM landscape_targets_ms
WHERE member_state NOT IN (SELECT country FROM regional_units)
UNION ALL
SELECT 'organic', member_state FROM organic_targets_ms WHERE member_state NOT IN (SELECT country FROM regional_units);

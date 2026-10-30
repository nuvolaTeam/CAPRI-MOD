-- Inputs declared on 29 October 2026 that belong to no other declaration file. Structure from the files; units open where not stated.

-- file: capri_data/2017/abatement/ammonia/FracUseFert.csv
CREATE TABLE misc_fracusefert (
    region VARCHAR NOT NULL,
    fertiliser VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, fertiliser)
);
COMMENT ON TABLE misc_fracusefert IS 'CAPRI''s FracUseFert(region, fertiliser): shares of urea (Ureum) and other mineral N fertiliser per country, which envind/ammo.gms l. 287-292 loads from dat/miterra/LitRev_inputs.gdx (ammoLitRev on) (tools/build/build_ammonia_tech_inputs.py, not in the pipeline trace).';
INSERT INTO value_units VALUES
  ('misc_fracusefert', 'value', NULL, 'open', 'FracUseFert.value: unit to be established');

-- file: capri_data/codes/model_units.csv
CREATE TABLE misc_model_units (
    code VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    used_by VARCHAR NOT NULL,
    PRIMARY KEY (code, description, used_by)
);
COMMENT ON TABLE misc_model_units IS 'The model''s own units that CAPRI''s unit catalogue (CAPRIunits.gms) lacks: code, description and the tables using it; hand-kept, no builder; tools/build/build_unit_catalogue.py adds them to units.csv with capri = no.';


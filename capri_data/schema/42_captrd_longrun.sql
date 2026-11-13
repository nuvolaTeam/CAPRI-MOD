-- Input of CAPTRD's long-run supports (captrd/longrun_supports.gms l. 105; capri_mod/pipeline/captrd/longrun_supports.py),
-- by tools/build/build_captrd_longrun.py.

-- file: capri_data/pipeline/captrd/dat/longrun_p_longruninfoall.csv
CREATE TABLE ctrd_longrun_p_longruninfoall (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "row" VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL,
    "year" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, "row", info, scenario, "year")
);
COMMENT ON TABLE ctrd_longrun_p_longruninfoall IS 'The long-run change factors, data and shares p_longRunInfoAll(region, col, row, info, scenario, year or B2000) of results/global/longrun_info_fac_defaulta.gdx for the scenario of the setting captrd.longrun_scenario (CAPTRD''s %SelecScen%), the member states CAPTRD projects and World; 0 rows: the reference run''s selection globiom_eu_bright_s0_2023+REFERENCE+REFERENCE has no records in that file (tools/build/build_captrd_longrun.py).';
INSERT INTO value_units VALUES
  ('ctrd_longrun_p_longruninfoall', 'value', NULL, 'open', 'longrun_p_longruninfoall.value: by info (factorB2000: change factor over 2000; data: GLOBIOM''''s level; share: demand share)');

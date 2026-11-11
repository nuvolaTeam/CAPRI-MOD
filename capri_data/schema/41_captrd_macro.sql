-- Inputs of the Aglink load's population data p_aglinkMacro (baseline/load_aglink2023dgAgri.gms l. 905-1068) and of
-- the UN population fallback (longrun_supports.gms l. 386-389; capri_mod/pipeline/captrd/macro.py), by
-- tools/build/build_captrd_macro.py.

-- file: capri_data/pipeline/captrd/sets/macro/globiomcountry.csv
CREATE TABLE ctrd_macro_globiomcountry (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_macro_globiomcountry IS 'The set GlobiomCountry (the GLOBIOM countries; dat/global/reg_mappings.xlsx Sheet1!Y2:Y250, l. 931): one member per row, 180 (e.g. Armenia, Afghanistan, Albania); written by tools/build/build_captrd_macro.py.';

-- file: capri_data/pipeline/captrd/sets/macro/globiomcountry_faoreg.csv
CREATE TABLE ctrd_macro_globiomcountry_faoreg (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_macro_globiomcountry_faoreg IS 'The set GlobiomCountry_FAOreg (the GLOBIOM countries to the FAO regions (with Taiwan.214, l. 943); Sheet1!Y2:Z250, l. 939): one member per row, 183 (e.g. Armenia.1, Afghanistan.2, Albania.3); written by tools/build/build_captrd_macro.py.';

-- file: capri_data/pipeline/captrd/sets/macro/faoreg_aglinkregions.csv
CREATE TABLE ctrd_macro_faoreg_aglinkregions (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_macro_faoreg_aglinkregions IS 'The set FAOreg_AGLINKregions (the FAO regions to the Aglink regions; Sheet1!R2:S250, l. 948): one member per row, 231 (e.g. 1.ASC, 2.ASL, 3.EUE); written by tools/build/build_captrd_macro.py.';

-- file: capri_data/pipeline/captrd/sets/macro/iso_faoreg.csv
CREATE TABLE ctrd_macro_iso_faoreg (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_macro_iso_faoreg IS 'The set ISO_FAOreg (the ISO countries to the FAO regions (with PSE.299, global/iso_to_fao_regions.gms l. 23); Sheet1!U2:V250, the range of iso_to_fao_regions.gms''s $CALL): one member per row, 214 (e.g. AFG.2, ALB.3, DZA.4); written by tools/build/build_captrd_macro.py.';

-- file: capri_data/pipeline/captrd/dat/macro_p_aglinkmacroeu.csv
CREATE TABLE ctrd_macro_p_aglinkmacroeu (
    ctrcode VARCHAR NOT NULL,
    "var" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ctrcode, "var", "year")
);
COMMENT ON TABLE ctrd_macro_p_aglinkmacroeu IS 'The EU countries'' Aglink macro data p_aglinkMacroEU(ctrCode, var, year) of dat/baseline/aglink2023macro.xlsx (sheet for_gams, A2:D5600; load_aglink2023dgAgri.gms l. 924), the rows of POP and GDPR; 2214 rows (tools/build/build_captrd_macro.py).';
INSERT INTO value_units VALUES
  ('ctrd_macro_p_aglinkmacroeu', 'value', NULL, 'open', 'macro_p_aglinkmacroeu.value: by var (POP: population; GDPR: real GDP index of Aglink)');

-- file: capri_data/pipeline/captrd/dat/macro_ssp_data.csv
CREATE TABLE ctrd_macro_ssp_data (
    source VARCHAR NOT NULL,
    ssp VARCHAR NOT NULL,
    "var" VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (source, ssp, "var", country, "year")
);
COMMENT ON TABLE ctrd_macro_ssp_data IS 'SSP2''s population (IIASA) and GDP (OECD) per GLOBIOM country, SSP_data of dat/baseline/data_SSPV3_update.gdx (load_aglink2023dgAgri.gms l. 959); 14072 rows (tools/build/build_captrd_macro.py).';
INSERT INTO value_units VALUES
  ('ctrd_macro_ssp_data', 'value', NULL, 'open', 'macro_ssp_data.value: by var (POP: 1000 persons; GDP: as the SSP database)');

-- file: capri_data/pipeline/captrd/dat/macro_worldpop.csv
CREATE TABLE ctrd_macro_worldpop (
    "year" INTEGER NOT NULL,
    region VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY ("year", region)
);
COMMENT ON TABLE ctrd_macro_worldpop IS 'The UN population WorldPop(year, region) of dat/arm/allpop.gdx (captrd.gms l. 614), the nonzero records; 28179 rows (tools/build/build_captrd_macro.py).';
INSERT INTO value_units VALUES
  ('ctrd_macro_worldpop', 'value', NULL, 'open', 'macro_worldpop.value: 1000 persons');

-- Inputs under capri_data/pipeline/captrd/dat for CAPTRD's expert supports from DG AGRI's dairy data
-- (captrd/expert_support.gms l. 365-760; capri_mod/pipeline/captrd/dairy_supports.py), written by
-- tools/build/build_captrd_dairy.py from CAPRI's dat/baseline/dairy_targets_agri.gms and recent_mlk_yld.gdx.

-- file: capri_data/pipeline/captrd/dat/dairy_p_cowmilkprod.csv
CREATE TABLE ctrd_dairy_p_cowmilkprod (
    ms_agri VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agri, "year")
);
COMMENT ON TABLE ctrd_dairy_p_cowmilkprod IS 'CAPRI''s p_cowMilkProd(ms_agri, year): cow milk production, historical and forecast (DG AGRI''s 2015 market outlook), from dat/baseline/dairy_targets_agri.gms (included at expert_support.gms l. 370); 28 countries x 1990-2025, 1,008 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_dairy_p_cowmilkprod', 'value', 'U_1000t', 'capri', 'dairy_targets_agri.gms: "thousand tonnes"');

-- file: capri_data/pipeline/captrd/dat/dairy_p_dcowmilkprod.csv
CREATE TABLE ctrd_dairy_p_dcowmilkprod (
    ms_agri VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agri, "year")
);
COMMENT ON TABLE ctrd_dairy_p_dcowmilkprod IS 'CAPRI''s p_DcowMilkProd(ms_agri, year): dairy cow milk production, historical and forecast, from dat/baseline/dairy_targets_agri.gms; not used by expert_support.gms (it uses p_cowMilkProd to avoid a break in the Polish series, l. 396), kept with the file''s other tables; 1,008 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_dairy_p_dcowmilkprod', 'value', 'U_1000t', 'capri', 'dairy_targets_agri.gms: "thousand tonnes"');

-- file: capri_data/pipeline/captrd/dat/dairy_p_milkdeliveries.csv
CREATE TABLE ctrd_dairy_p_milkdeliveries (
    ms_agri VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agri, "year")
);
COMMENT ON TABLE ctrd_dairy_p_milkdeliveries IS 'CAPRI''s p_milkDeliveries(ms_agri, year): milk delivered to dairies, historical and forecast, from dat/baseline/dairy_targets_agri.gms (its description repeats p_DcowMilkProd''s); 1,008 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_dairy_p_milkdeliveries', 'value', 'U_1000t', 'capri', 'dairy_targets_agri.gms: "thousand tonnes"');

-- file: capri_data/pipeline/captrd/dat/dairy_p_nrcows.csv
CREATE TABLE ctrd_dairy_p_nrcows (
    ms_agri VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agri, "year")
);
COMMENT ON TABLE ctrd_dairy_p_nrcows IS 'CAPRI''s p_nrCows(ms_agri, year): number of dairy cows, historical and forecast, from dat/baseline/dairy_targets_agri.gms; 1,008 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_dairy_p_nrcows', 'value', 'U_1000hd', 'capri', 'dairy_targets_agri.gms: "thousan heads"');

-- file: capri_data/pipeline/captrd/dat/dairy_p_dairycowyield.csv
CREATE TABLE ctrd_dairy_p_dairycowyield (
    ms_agri VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agri, "year")
);
COMMENT ON TABLE ctrd_dairy_p_dairycowyield IS 'CAPRI''s p_dairyCowYield(ms_agri, year): milk yield of dairy cows, historical and forecast, from dat/baseline/dairy_targets_agri.gms (Poland''s recomputed from production and cows in expert_support.gms l. 416); 1,008 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_dairy_p_dairycowyield', 'value', 'U_kgperhd', 'capri', 'dairy_targets_agri.gms: "kg/cow"');

-- file: capri_data/pipeline/captrd/dat/dairy_ms_agri_to_ms.csv
CREATE TABLE ctrd_dairy_ms_agri_to_ms (
    ms_agri VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    PRIMARY KEY (ms_agri, region)
);
COMMENT ON TABLE ctrd_dairy_ms_agri_to_ms IS 'CAPRI''s set ms_agri_TO_MS(ms_agri, MS): DG AGRI''s country codes to CAPRI''s member states, from dat/baseline/dairy_targets_agri.gms; 28 pairs (tools/build/build_captrd_dairy.py).';

-- file: capri_data/pipeline/captrd/dat/p_recentmlkyld.csv
CREATE TABLE ctrd_p_recentmlkyld (
    region VARCHAR NOT NULL,
    "year" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE ctrd_p_recentmlkyld IS 'CAPRI''s p_recentMlkYld(region, year): recent milk yields GROF.CMLK/DCOW.SUR4 by year and, under year Y, their annual change 2014/15-2019/20 (the parameter''s description), from dat/baseline/recent_mlk_yld.gdx (read at expert_support.gms l. 474; converted to Parquet by tools/build/convert_capri_gdx.py); 352 rows (tools/build/build_captrd_dairy.py).';
INSERT INTO value_units VALUES
  ('ctrd_p_recentmlkyld', 'value', NULL, 'open', 'p_recentmlkyld.value: kg/head by year, a relative annual change under year Y (CAPRI states no unit)');

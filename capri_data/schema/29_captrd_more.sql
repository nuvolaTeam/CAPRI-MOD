-- CAPTRD's sets and data files under capri_data/pipeline/captrd not declared in 28_captrd_sets.sql (29 October 2026). Structure (types, NOT NULL, keys) from the files; units open where no builder or CAPRI file states them.

-- file: capri_data/pipeline/captrd/dat/p_byproduct.csv
CREATE TABLE ctrd_p_byproduct (
    byproduct VARCHAR NOT NULL,
    stock VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (byproduct, stock)
);
COMMENT ON TABLE ctrd_p_byproduct IS 'CAPRI''s p_ByProduct(byproduct, stock): by-product (DDGS, GLYC) per ton of feedstock converted to biofuel, from dat/biofuel/biofuel_technology_params.gms (as CSV: capri_data/sources/capri_dat/biofuel/biofuel_technology_params_p_ByProduct.csv, tools/build/convert_sources_to_csv.py), which captrd.gms l. 340-341 includes; 14 rows (tools/build/build_captrd_dat.py).';
INSERT INTO value_units VALUES
  ('ctrd_p_byproduct', 'value', NULL, 'open', 'p_byproduct.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_extrrates.csv
CREATE TABLE ctrd_p_extrrates (
    fuel VARCHAR NOT NULL,
    stock VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (fuel, stock)
);
COMMENT ON TABLE ctrd_p_extrrates IS 'CAPRI''s p_ExtrRates(fuel, stock): biofuel (BIOE, BIOD) per ton of feedstock, from dat/biofuel/biofuel_technology_params.gms (as CSV: capri_data/sources/capri_dat/biofuel/biofuel_technology_params_p_ExtrRates.csv, tools/build/convert_sources_to_csv.py), which captrd.gms l. 340-341 includes; 17 rows (tools/build/build_captrd_dat.py).';
INSERT INTO value_units VALUES
  ('ctrd_p_extrrates', 'value', NULL, 'open', 'p_extrrates.value: unit to be established');

-- file: capri_data/pipeline/captrd/dat/p_luunits.csv
CREATE TABLE ctrd_p_luunits (
    act VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE ctrd_p_luunits IS 'CAPRI''s p_LUUnits(act): livestock units per head of an animal activity, from dat/policy/livestock_units.gms (as CSV: capri_data/sources/capri_dat/policy/livestock_units_p_LUUnits.csv, tools/build/convert_sources_to_csv.py), included at captrd.gms l. 349 and used for the stocking density LU (prep_data_for_estimation.gms l. 202-203); 18 rows (tools/build/build_captrd_dat.py).';
INSERT INTO value_units VALUES
  ('ctrd_p_luunits', 'value', NULL, 'open', 'p_luunits.value: unit to be established');

-- file: capri_data/pipeline/captrd/sets/aact.csv
CREATE TABLE ctrd_aact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_aact IS 'CAPRI''s global set AACT (animal production activities; gams/sets.gms l. 2284): one member per row in d0, 22 members (e.g. DCOL, DCOH, BULL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/bio_cols.csv
CREATE TABLE ctrd_bio_cols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_cols IS 'CAPRI''s global set Bio_Cols (biofuel columns: non-agricultural, first and second generation, exogenous, energy share; gams/sets.gms l. 1731): one member per row in d0, 5 members (e.g. NAGR, FSTG, HCOS); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/biofuels.csv
CREATE TABLE ctrd_biofuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_biofuels IS 'CAPRI''s global set BIOFUELS (biofuels; gams/sets.gms l. 4449): one member per row in d0, 2 members (e.g. BIOE, BIOD); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/biorepcols.csv
CREATE TABLE ctrd_biorepcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_biorepcols IS 'CAPRI''s global set bioRepCols (ethanol distinguished by source; gams/sets.gms l. 4531): one member per row in d0, 24 members (e.g. bioESwhe, bioECere); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/biostock.csv
CREATE TABLE ctrd_biostock (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_biostock IS 'CAPRI''s global set bioStock (feedstocks used for biofuel production; gams/sets.gms l. 5000): one member per row in d0, 16 members (e.g. SWHE, RYEM, BARL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/breedact.csv
CREATE TABLE ctrd_breedact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_breedact IS 'CAPTRD''s own set breedAct (female breeding animals entering the slgwFem_ equation; gams/captrd/sets_captrd.gms l. 334): one member per row in d0, 6 members (e.g. DCOL, SCOW, SOWS); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/cact.csv
CREATE TABLE ctrd_cact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_cact IS 'CAPRI''s global set CACT (crop production activities; gams/sets.gms l. 2197): one member per row in d0, 48 members (e.g. SWHE, DWHE, RYEM); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/cols_load.csv
CREATE TABLE ctrd_cols_load (
    d0 VARCHAR
);
COMMENT ON TABLE ctrd_cols_load IS 'CAPTRD''s COLS_LOAD, the CAPREG columns CAPTRD loads: DB_COLS minus the sets and items removed at gams/captrd.gms l. 419-448, plus HOLD (l. 445); one member per row in d0, 370 members (the first is the empty label, a member of CAPRI''s DB_COLS); built from sim_ini_21730''s DB_COLS by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/corfeedlosf.csv
CREATE TABLE ctrd_corfeedlosf (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_corfeedlosf IS 'CAPRI''s global set corFeedLosf (feed items whose losses coco2 may adjust; gams/sets.gms l. 5590): one member per row in d0, 5 members (e.g. FGRA, FMAI); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/cropo.csv
CREATE TABLE ctrd_cropo (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_cropo IS 'CAPRI''s global set CROPO (crop outputs; gams/sets.gms l. 4565): one member per row in d0, 37 members (e.g. SWHE, DWHE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/dact.csv
CREATE TABLE ctrd_dact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_dact IS 'CAPRI''s global set DACT (production activities aggregated in the database; gams/sets.gms l. 2279): one member per row in d0, 7 members (e.g. GRAS, OSET, DCOW); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/dact_to_pact.csv
CREATE TABLE ctrd_dact_to_pact (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_dact_to_pact IS 'CAPRI''s global mapping DACT_TO_PACT (database activity to its model variants; gams/sets.gms l. 3084): one pair per row (d0, d1), 17 pairs (e.g. GRAS.GRAE, OSET.ISET); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/dmpact.csv
CREATE TABLE ctrd_dmpact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_dmpact IS 'CAPRI''s global set DMPACT (model activities aggregated to database activities; gams/sets.gms l. 3091-3093): one member per row in d0, 12 members (e.g. GRAE, ISET); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/domm_set.csv
CREATE TABLE ctrd_domm_set (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_domm_set IS 'CAPRI''s global set DOMM (market balance columns adding up to domestic use; gams/sets.gms l. 3124): one member per row in d0, 8 members (e.g. FEDM, SEDM, INDM); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/dompos.csv
CREATE TABLE ctrd_dompos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_dompos IS 'CAPTRD''s own set DOMPOS (domestic use positions; gams/captrd/sets_captrd.gms l. 318-320): one member per row in d0, 9 members (e.g. FEDM, SEDF, HCOM); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/feed.csv
CREATE TABLE ctrd_feed (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_feed IS 'CAPRI''s global set FEED (feedingstuff as inputs; gams/sets.gms l. 4732): one member per row in d0, 12 members (e.g. FGRA, FMAI); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/feed_to_o.csv
CREATE TABLE ctrd_feed_to_o (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_feed_to_o IS 'CAPRI''s global mapping FEED_TO_O (feed aggregate to the outputs fed; gams/sets.gms l. 5622): one pair per row (d0, d1), 63 pairs (e.g. FGRA.GRAS, FMAI.MAIF); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/fix_yai.csv
CREATE TABLE ctrd_fix_yai (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fix_yai IS 'CAPRI''s global set FIX_YAI (animals with a fixed young-animal input coefficient; gams/sets.gms l. 5055): one member per row in d0, 14 members (e.g. BULL, HEIL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/fosfuels.csv
CREATE TABLE ctrd_fosfuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fosfuels IS 'CAPRI''s global set FOSFUELS (fossil fuels; gams/sets.gms l. 4450): one member per row in d0, 2 members (e.g. DISL, GASL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/fout.csv
CREATE TABLE ctrd_fout (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fout IS 'CAPRI''s global set FOUT (N, P2O5, K2O output of animals and crops; gams/sets.gms l. 5496): one member per row in d0, 3 members (e.g. MANN, MANP, MANK); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/fuel_rows.csv
CREATE TABLE ctrd_fuel_rows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fuel_rows IS 'CAPRI''s global set FUEL_ROWS (fuel rows; gams/sets.gms l. 4447): one member per row in d0, 3 members (e.g. DISL, GASL, CRDO); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/fuels.csv
CREATE TABLE ctrd_fuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fuels IS 'CAPRI''s global set FUELS (fuels; gams/sets.gms l. 4451; sets_captrd.gms l. 268-269 declares fuels with the same four members): one member per row in d0, 4 members (e.g. BIOE, DISL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/iyani.csv
CREATE TABLE ctrd_iyani (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_iyani IS 'CAPRI''s global set IYANI (young animals as inputs; gams/sets.gms l. 4731): one member per row in d0, 8 members (e.g. ICAM, IHEI); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/landusearto.csv
CREATE TABLE ctrd_landusearto (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_landusearto IS 'CAPRI''s global set LandUseARTO (mutually exclusive land uses adding up to ARTO; gams/sets.gms l. 2910, the variant without %land_hilda%): one member per row in d0, 5 members (e.g. UAAR, FORE, OLND); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/maact.csv
CREATE TABLE ctrd_maact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_maact IS 'CAPRI''s global set MAACT (animal production activities in the model; gams/sets.gms l. 2274): one member per row in d0, 18 members (e.g. DCOL, BULL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/map_rr.csv
CREATE TABLE ctrd_map_rr (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_map_rr IS 'CAPRI''s global mapping Map_RR (regional hierarchy: aggregate to country, country to NUTS1, NUTS1 to NUTS2; gams/sets.gms l. 7442): one pair per row (d0, d1), 823 pairs (e.g. BL000000.BL200000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/mcact.csv
CREATE TABLE ctrd_mcact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mcact IS 'CAPRI''s global set MCACT (crop production activities in the model; gams/sets.gms l. 2234): one member per row in d0, 44 members (e.g. SWHE, BARL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/meat.csv
CREATE TABLE ctrd_meat (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_meat IS 'CAPTRD''s own set MEAT (meats; gams/captrd/sets_captrd.gms l. 274): one member per row in d0, 4 members (e.g. BEEF, PORK); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/mpact.csv
CREATE TABLE ctrd_mpact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mpact IS 'CAPRI''s global set MPACT (production activities of the supply model; gams/sets.gms l. 2206): one member per row in d0, 89 members (e.g. SWHE, DCOL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/mrkbalee.csv
CREATE TABLE ctrd_mrkbalee (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mrkbalee IS 'CAPTRD''s own set MrkBaleE (extended market balance positions to estimate; gams/captrd/sets_captrd.gms l. 297-304): one member per row in d0, 20 members (e.g. GROF, IMPT, DOMM); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/ms.csv
CREATE TABLE ctrd_ms (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ms IS 'CAPTRD''s MS, the countries potentially in estimation (gams/captrd/sets_captrd.gms l. 54-56: / sets.rmssup /; RMSSUP = SET.NUTS0 at gams/sets.gms l. 8264): one member per row in d0, 35 members (e.g. BL000000, DK000000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/msnoeu28.csv
CREATE TABLE ctrd_msnoeu28 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_msnoeu28 IS 'CAPRI''s global set MSnoEU28 (supply countries outside the EU28; gams/sets.gms l. 7945): one member per row in d0, 9 members (e.g. NO000000, TUR); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/ncnc.csv
CREATE TABLE ctrd_ncnc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ncnc IS 'CAPRI''s NCNC, the common nutrient coefficients (declared /SET.NCNC_POS/ at gams/captrd.gms l. 621; the same in capmod.gms l. 235): one member per row in d0, 24 members (e.g. N_CAL, N_PRO, VIT_C); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/o.csv
CREATE TABLE ctrd_o (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_o IS 'CAPRI''s global set O (outputs; gams/sets.gms l. 4552): one member per row in d0, 63 members (e.g. SWHE, DWHE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/oyani.csv
CREATE TABLE ctrd_oyani (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_oyani IS 'CAPRI''s global set OYANI (young animals as outputs; gams/sets.gms l. 4589): one member per row in d0, 8 members (e.g. YCOW, YCAM); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/oyani_rows.csv
CREATE TABLE ctrd_oyani_rows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_oyani_rows IS 'CAPRI''s global set OYANI_ROWS (young animals; gams/sets.gms l. 3273): one member per row in d0, 8 members (e.g. YCOW, YBUL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/p_t_actagg.csv
CREATE TABLE ctrd_p_t_actagg (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_p_t_actagg IS 'CAPRI''s P_T_ActAgg, activities and products to aggregates and back (gams/reports/aggreg_sets.gms l. 68, included at captrd.gms l. 186): one pair per row (d0, d1), 588 pairs (e.g. SWHE.CERE); copied from sim_ini_21730 by tools/build/build_captrd_sets.py. CAPTRD''s additions at sets_captrd.gms l. 366-372 (e.g. SCOW.CATO) are not in it.';

-- file: capri_data/pipeline/captrd/sets/pact_to_i.csv
CREATE TABLE ctrd_pact_to_i (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_pact_to_i IS 'CAPRI''s global mapping PACT_TO_I (production activity to the inputs it uses; gams/sets.gms l. 5292): one pair per row (d0, d1), 1148 pairs (e.g. SWHE.NITF); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/pact_to_io.csv
CREATE TABLE ctrd_pact_to_io (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_pact_to_io IS 'CAPRI''s global mapping PACT_TO_IO (union of PACT_TO_O and PACT_TO_I; gams/sets.gms l. 5370-5372): one pair per row (d0, d1), 1424 pairs (e.g. SWHE.SWHE, SWHE.NITF); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/pact_to_o.csv
CREATE TABLE ctrd_pact_to_o (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_pact_to_o IS 'CAPRI''s global mapping PACT_TO_O (production activity to its main and secondary outputs; gams/sets.gms l. 5187): one pair per row (d0, d1), 280 pairs (e.g. SWHE.STRA); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/pact_to_y.csv
CREATE TABLE ctrd_pact_to_y (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_pact_to_y IS 'CAPRI''s global mapping PACT_TO_Y (production activity to its main output; gams/sets.gms l. 5377): one pair per row (d0, d1), 68 pairs (e.g. SWHE.SWHE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/prcd.csv
CREATE TABLE ctrd_prcd (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_prcd IS 'CAPRI''s global mapping PRCD (d0 is processed from d1; gams/sets.gms l. 4956): one pair per row (d0, d1), 23 pairs (e.g. WHEP.MILK); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/quotas.csv
CREATE TABLE ctrd_quotas (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_quotas IS 'CAPRI''s global set QUOTAS (quota columns; gams/sets.gms l. 8740): one member per row in d0, 3 members (e.g. QUTS, QUTA); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/reqsc.csv
CREATE TABLE ctrd_reqsc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_reqsc IS 'CAPRI''s global set REQSC (nutrient contents; gams/sets.gms l. 2133): one member per row in d0, 17 members (e.g. ENNE, CRPR); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/rmaggsup.csv
CREATE TABLE ctrd_rmaggsup (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_rmaggsup IS 'CAPRI''s RmAggSup, market regions built from supply regions (gams/sets.gms l. 8367-8370), plus EU013000 added by CAPTRD (sets_captrd.gms l. 184, %EU_EASTBUR% set at l. 173): one member per row in d0, 43 members (e.g. ARG, USA); from sim_ini_21730''s RmAggSup by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/rms_to_rm.csv
CREATE TABLE ctrd_rms_to_rm (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_rms_to_rm IS 'CAPRI''s global mapping RMS_TO_RM (countries and aggregates to market aggregates, loaded from aggregation\%reg_agg%.gdx; gams/sets.gms l. 8269-8272): one pair per row (d0, d1), 80 pairs (e.g. BL000000.A_EU_WEST); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/rows_load.csv
CREATE TABLE ctrd_rows_load (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_rows_load IS 'CAPTRD''s ROWS_LOAD, the CAPREG rows CAPTRD loads: DB_ROWS minus the sets and items removed at gams/captrd.gms l. 420, 450-481; one member per row in d0, 536 members (e.g. 3NOP, AComLN); built from sim_ini_21730''s DB_ROWS by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/seco.csv
CREATE TABLE ctrd_seco (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_seco IS 'CAPRI''s global set SECO (processed outputs; gams/sets.gms l. 4527): one member per row in d0, 20 members (e.g. BIOE, RAPO, DDGS); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/seco_biof.csv
CREATE TABLE ctrd_seco_biof (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_seco_biof IS 'CAPRI''s global set SECO_BIOF (biofuels; gams/sets.gms l. 4530): one member per row in d0, 2 members (e.g. BIOE, BIOD); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/secom.csv
CREATE TABLE ctrd_secom (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_secom IS 'CAPRI''s global set SECOM (secondary products including dairy, SECO + MLKSECO; gams/sets.gms l. 4926-4927): one member per row in d0, 29 members (e.g. BIOE, WHEP); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/splitacts.csv
CREATE TABLE ctrd_splitacts (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_splitacts IS 'CAPRI''s global set SplitActs (disaggregated activities in the model; gams/sets.gms l. 2310): one member per row in d0, 8 members (e.g. GRAE, DCOL); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/srnuts2.csv
CREATE TABLE ctrd_srnuts2 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_srnuts2 IS 'CAPRI''s global set SRNUTS2 (sub-regions that are NUTS2 regions; gams/sets.gms l. 7803): one member per row in d0, 250 members (e.g. DK000000, BL210000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/stock_to_by.csv
CREATE TABLE ctrd_stock_to_by (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_stock_to_by IS 'CAPRI''s global mapping STOCK_TO_BY (biofuel feedstock to by-product DDGS or GLYC; gams/sets.gms l. 5017): one pair per row (d0, d1), 12 pairs (e.g. SWHE.DDGS); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/stock_to_fuel.csv
CREATE TABLE ctrd_stock_to_fuel (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_stock_to_fuel IS 'CAPRI''s global mapping STOCK_TO_FUEL (biofuel feedstock to BIOE or BIOD; gams/sets.gms l. 4996): one pair per row (d0, d1), 14 pairs (e.g. SWHE.BIOE); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/urbannuts.csv
CREATE TABLE ctrd_urbannuts (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_urbannuts IS 'CAPRI''s global set urbanNUTS (NUTS2 regions without agriculture; gams/sets.gms l. 7858): one member per row in d0, 8 members (e.g. BL100000, DE300000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';


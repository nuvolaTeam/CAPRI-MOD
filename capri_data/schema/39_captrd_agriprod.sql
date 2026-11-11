-- Inputs of CAPTRD's supports from Eurostat's recent production statistics (captrd/agriprod_supports.gms, included
-- by captrd/expert_support.gms l. 771; capri_mod/pipeline/captrd/agriprod_supports.py): the file's sets, the
-- agriprod data (dat/coco/Agri_Prod.gdx) and the feed requirements' limits (tools/build/build_captrd_agriprod.py).

-- file: capri_data/pipeline/captrd/sets/agriprod/shepgoatori.csv
CREATE TABLE ctrd_ap_shepgoatori (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_shepgoatori IS 'The set shepGoatOri of captrd/agriprod_supports.gms (the December survey''s sheep and goat series; l. 25-30), as written: one member per row, 4 (e.g. SHEP, GOAT, SHEPS); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprodori.csv
CREATE TABLE ctrd_ap_agriprodori (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprodori IS 'The set agriprodOri of captrd/agriprod_supports.gms (the December survey''s series that guide the short-run projections; l. 31-47), as written: one member per row, 25 (e.g. CATA, SCOW, DCOW); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprodcalc.csv
CREATE TABLE ctrd_ap_agriprodcalc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprodcalc IS 'The set agriprodCalc of captrd/agriprod_supports.gms (the series derived from them; l. 49-55), as written: one member per row, 5 (e.g. PIGF, AdNonDai, SHGT); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprod.csv
CREATE TABLE ctrd_ap_agriprod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprod IS 'The set agriprod of captrd/agriprod_supports.gms (every survey series plus the activity levels to target; l. 57-62), as written: one member per row, 42 (e.g. CATA, SCOW, DCOW); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprod1.csv
CREATE TABLE ctrd_ap_agriprod1 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprod1 IS 'The set agriprod1 of captrd/agriprod_supports.gms (the first-choice series of an activity without its own; l. 64-70), as written: one member per row, 5 (e.g. DCOW, CALV, AdNonDai); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprod2.csv
CREATE TABLE ctrd_ap_agriprod2 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprod2 IS 'The set agriprod2 of captrd/agriprod_supports.gms (the second-choice series; l. 72-75), as written: one member per row, 2 (e.g. CATA, SHEPS); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/shepgoat.csv
CREATE TABLE ctrd_ap_shepgoat (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_shepgoat IS 'The set shepGoat of captrd/agriprod_supports.gms (the sheep and goat original series; l. 77-79), as written: one member per row, 4 (e.g. SHEP, GOAT, SHEPS); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprodaact.csv
CREATE TABLE ctrd_ap_agriprodaact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprodaact IS 'The set agriProdAact of captrd/agriprod_supports.gms (the target animal activities; l. 81-86), as written: one member per row, 16 (e.g. DCOL, DCOH, SCOW); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprodcact.csv
CREATE TABLE ctrd_ap_agriprodcact (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprodcact IS 'The set agriProdCact of captrd/agriprod_supports.gms (the target crop activities; l. 88-90), as written: one member per row, 10 (e.g. SWHE, SUGB, DWHE); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprodmlk.csv
CREATE TABLE ctrd_ap_agriprodmlk (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_agriprodmlk IS 'The set agriProdMlk of captrd/agriprod_supports.gms (the target milk variables; l. 92-94), as written: one member per row, 2 (e.g. GROF, YILD); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/cols_to_agriprod.csv
CREATE TABLE ctrd_ap_cols_to_agriprod (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ap_cols_to_agriprod IS 'The set cols_TO_agriprod of captrd/agriprod_supports.gms (CAPRI''s animal activities to the series groups; l. 98-106), as written: one member per row, 30 (e.g. CAMR.CALV, CAFR.CALV, CAMF.CALV); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/msagriprod.csv
CREATE TABLE ctrd_ap_msagriprod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_msagriprod IS 'The set MSagriprod of captrd/agriprod_supports.gms (the member states in COCO''s notation; l. 108-145), as written: one member per row, 36 (e.g. BE000, LU000, DK000); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/msagriprod_map.csv
CREATE TABLE ctrd_ap_msagriprod_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ap_msagriprod_map IS 'The set MSagriprod_map of captrd/agriprod_supports.gms (COCO''s member states to CAPRI''s regions; l. 146-183), as written: one member per row, 36 (e.g. BE000.BL000000, LU000.BL400000, DK000.DK000000); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/fac.csv
CREATE TABLE ctrd_ap_fac (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_fac IS 'The set fac of captrd/agriprod_supports.gms (the change factors to the nowcast years; l. 189), as written: one member per row, 3 (e.g. fac2018, fac2019, fac2020); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/itemagriprod.csv
CREATE TABLE ctrd_ap_itemagriprod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_itemagriprod IS 'The set itemAgriProd of captrd/agriprod_supports.gms (the items of the agriprod data used; l. 191-195), as written: one member per row, 9 (e.g. SUR4, LEVL, RMLK); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/mlkagriprod.csv
CREATE TABLE ctrd_ap_mlkagriprod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_mlkagriprod IS 'The set mlkAgriProd of captrd/agriprod_supports.gms (the milk types loaded; l. 197-199), as written: one member per row, 4 (e.g. RMLK, CMLK, EMLK); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/agriprod_to_item.csv
CREATE TABLE ctrd_ap_agriprod_to_item (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ap_agriprod_to_item IS 'The set agriprod_to_item of captrd/agriprod_supports.gms (the series to their nowcast items; l. 201-207), as written: one member per row, 35 (e.g. DCOW.SUR4, CALV.SUR4, AdNonDai.SUR4); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/agriprod/facyr.csv
CREATE TABLE ctrd_ap_facyr (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ap_facyr IS 'The set facyr of captrd/agriprod_supports.gms (the base years of the change factors, %BaseYear% (2017 as the reference run) and 2018; l. 214), as written: one member per row, 2 (e.g. 2017, 2018); read by tools/build/build_captrd_agriprod.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/dat/agriprod_p_agriprod.csv
CREATE TABLE ctrd_agriprod_p_agriprod (
    ms_agriprod VARCHAR NOT NULL,
    agriprod VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (ms_agriprod, agriprod, item, "year")
);
COMMENT ON TABLE ctrd_agriprod_p_agriprod IS 'Eurostat''s recent production statistics p_AgriProd(msAgriprod, agriprod, itemAgriProd, year) of dat/coco/Agri_Prod.gdx (read by captrd/agriprod_supports.gms l. 229), the records of the file''s domains and of the years from 2010; 10104 rows (tools/build/build_captrd_agriprod.py).';
INSERT INTO value_units VALUES
  ('ctrd_agriprod_p_agriprod', 'value', NULL, 'open', 'agriprod_p_agriprod.value: by item (SUR4: 1000 heads of the December survey; LEVL: 1000 ha; the milk items: 1000 t)');

-- file: capri_data/pipeline/captrd/dat/agriprod_p_reqfcnlim.csv
CREATE TABLE ctrd_agriprod_p_reqfcnlim (
    act VARCHAR NOT NULL,
    "row" VARCHAR NOT NULL,
    bound VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (act, "row", bound)
);
COMMENT ON TABLE ctrd_agriprod_p_reqfcnlim IS 'The table p_reqfcnlim(COLS, ROWS, lo/up) of gams/feed/feed_decl.gms l. 284: the absolute limits of days and daily growth in the feed requirement functions; 45 rows (tools/build/build_captrd_agriprod.py).';
INSERT INTO value_units VALUES
  ('ctrd_agriprod_p_reqfcnlim', 'value', NULL, 'open', 'agriprod_p_reqfcnlim.value: by row (DAYS: days; DAILY: g per day)');

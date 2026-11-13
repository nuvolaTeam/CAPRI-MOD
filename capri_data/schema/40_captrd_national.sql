-- Inputs of CAPTRD's national expert supports (captrd/national_supports.gms, included by captrd/expert_support.gms
-- l. 779; capri_mod/pipeline/captrd/national_supports.py): the file's sets and the NECP herds
-- (dat/baseline/necp_expert.gms), by tools/build/build_captrd_national.py.

-- file: capri_data/pipeline/captrd/sets/national/xpcols.csv
CREATE TABLE ctrd_nat_xpcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_nat_xpcols IS 'The set xpCOLS of captrd/national_supports.gms (the columns or column groups of the national sources; l. 52-75), as written (labels with blanks kept): one member per row, 22 (e.g. BROIL, Castrated horses , CATO); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/national/xpdisagg.csv
CREATE TABLE ctrd_nat_xpdisagg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_nat_xpdisagg IS 'The set xpDisAgg of captrd/national_supports.gms (the disaggregate animal categories, given a higher trust level; l. 77-91), as written (labels with blanks kept): one member per row, 13 (e.g. BROIL, DCOW, DUCKS); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/national/xprows.csv
CREATE TABLE ctrd_nat_xprows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_nat_xprows IS 'The set xpROWS of captrd/national_supports.gms (the rows or row groups of the national sources; l. 95-108), as written (labels with blanks kept): one member per row, 12 (e.g. COMI, NITF, LEV1); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/national/expert_to_cols.csv
CREATE TABLE ctrd_nat_expert_to_cols (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_nat_expert_to_cols IS 'The set Expert_to_cols of captrd/national_supports.gms (the national sources'' columns to CAPRI''s columns; l. 112-123), as written (labels with blanks kept): one member per row, 43 (e.g. CATT.DCOL, CATT.DCOH, DCOW.DCOL); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/national/expert_to_rows.csv
CREATE TABLE ctrd_nat_expert_to_rows (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_nat_expert_to_rows IS 'The set Expert_to_rows of captrd/national_supports.gms (the national sources'' rows to CAPRI''s rows; l. 125-137), as written (labels with blanks kept): one member per row, 13 (e.g. COMI.COMI, SWHE.SWHE, BARL.BARL); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/national/absdairyrunr.csv
CREATE TABLE ctrd_nat_absdairyrunr (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_nat_absdairyrunr IS 'The set absDairyRunr of captrd/national_supports.gms (the regions whose dairy supports stay in absolute form; l. 1516-1535), as written (labels with blanks kept): one member per row, 18 (e.g. BL000000, DK000000, DE000000); read by tools/build/build_captrd_national.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/dat/national_p_fromnecp.csv
CREATE TABLE ctrd_national_p_fromnecp (
    region VARCHAR NOT NULL,
    xpcol VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, xpcol, "year")
);
COMMENT ON TABLE ctrd_national_p_fromnecp IS 'The member states'' herds and mineral nitrogen from their NECPs, p_fromNECP(rAll, xpCols, simyy) of dat/baseline/necp_expert.gms (M Kesting, P Witzke, 8 April 2025; read by captrd/national_supports.gms l. 149), the nonzero records; 869 rows (tools/build/build_captrd_national.py).';
INSERT INTO value_units VALUES
  ('ctrd_national_p_fromnecp', 'value', NULL, 'open', 'national_p_fromnecp.value: by xpcol (the herds: 1000 heads; NITF: kt N)');

-- Inputs under capri_data/pipeline/captrd/sets. Generated structure (types, NOT NULL, keys) from the files on 29 October 2026; units open where no
-- builder or CAPRI file states them (value_units).

-- file: capri_data/pipeline/captrd/sets/cropc_to_g.csv
CREATE TABLE ctrd_cropc_to_g (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_cropc_to_g IS 'cropc_to_g (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/fixyield.csv
CREATE TABLE ctrd_fixyield (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_fixyield IS 'fixyield (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/grpc.csv
CREATE TABLE ctrd_grpc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_grpc IS 'grpc (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/grpr.csv
CREATE TABLE ctrd_grpr (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_grpr IS 'grpr (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/mrkbale.csv
CREATE TABLE ctrd_mrkbale (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_mrkbale IS 'mrkbale (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/noyielddrop.csv
CREATE TABLE ctrd_noyielddrop (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_noyielddrop IS 'noyielddrop (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/reqst.csv
CREATE TABLE ctrd_reqst (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_reqst IS 'reqst (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/rows_to_g.csv
CREATE TABLE ctrd_rows_to_g (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_rows_to_g IS 'rows_to_g (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/s_colsest.csv
CREATE TABLE ctrd_s_colsest (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_s_colsest IS 's_colsest (no builder: a declared table)';

-- file: capri_data/pipeline/captrd/sets/s_rowsest.csv
CREATE TABLE ctrd_s_rowsest (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_s_rowsest IS 's_rowsest (no builder: a declared table)';

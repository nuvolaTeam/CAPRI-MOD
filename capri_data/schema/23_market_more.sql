-- The market's remaining inputs (capri_data/2017/market). Generated structure (types, NOT NULL, keys) from the files on
-- 29 October 2026; units open where no builder or CAPRI file states them (value_units).

-- file: capri_data/2017/market/bilateral_flows_2017.csv
CREATE TABLE mkt_bilateral_flows_2017 (
    commodity VARCHAR NOT NULL,
    importer VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    q_kt DOUBLE NOT NULL,
    a DOUBLE NOT NULL,
    b DOUBLE NOT NULL,
    a0 DOUBLE NOT NULL,
    ta_pct DOUBLE NOT NULL,
    tc DOUBLE NOT NULL,
    PRIMARY KEY (commodity, importer, exporter)
);
COMMENT ON TABLE mkt_bilateral_flows_2017 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_flows_2017', 'q_kt', NULL, 'open', 'bilateral_flows_2017.q_kt: unit to be established'),
  ('mkt_bilateral_flows_2017', 'a', NULL, 'open', 'bilateral_flows_2017.a: unit to be established'),
  ('mkt_bilateral_flows_2017', 'b', NULL, 'open', 'bilateral_flows_2017.b: unit to be established'),
  ('mkt_bilateral_flows_2017', 'a0', NULL, 'open', 'bilateral_flows_2017.a0: unit to be established'),
  ('mkt_bilateral_flows_2017', 'ta_pct', NULL, 'open', 'bilateral_flows_2017.ta_pct: unit to be established'),
  ('mkt_bilateral_flows_2017', 'tc', NULL, 'open', 'bilateral_flows_2017.tc: unit to be established');

-- file: capri_data/2017/market/bilateral_flows_2017_eu2.csv
CREATE TABLE mkt_bilateral_flows_2017_eu2 (
    commodity VARCHAR NOT NULL,
    importer VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    q_kt DOUBLE NOT NULL,
    a DOUBLE NOT NULL,
    b DOUBLE NOT NULL,
    a0 DOUBLE NOT NULL,
    ta_pct DOUBLE NOT NULL,
    tc DOUBLE NOT NULL,
    PRIMARY KEY (commodity, importer, exporter)
);
COMMENT ON TABLE mkt_bilateral_flows_2017_eu2 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_flows_2017_eu2', 'q_kt', NULL, 'open', 'bilateral_flows_2017_eu2.q_kt: unit to be established'),
  ('mkt_bilateral_flows_2017_eu2', 'a', NULL, 'open', 'bilateral_flows_2017_eu2.a: unit to be established'),
  ('mkt_bilateral_flows_2017_eu2', 'b', NULL, 'open', 'bilateral_flows_2017_eu2.b: unit to be established'),
  ('mkt_bilateral_flows_2017_eu2', 'a0', NULL, 'open', 'bilateral_flows_2017_eu2.a0: unit to be established'),
  ('mkt_bilateral_flows_2017_eu2', 'ta_pct', NULL, 'open', 'bilateral_flows_2017_eu2.ta_pct: unit to be established'),
  ('mkt_bilateral_flows_2017_eu2', 'tc', NULL, 'open', 'bilateral_flows_2017_eu2.tc: unit to be established');

-- file: capri_data/2017/market/bilateral_flows_2030.csv
CREATE TABLE mkt_bilateral_flows_2030 (
    commodity VARCHAR NOT NULL,
    importer VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    q_kt DOUBLE NOT NULL,
    a DOUBLE NOT NULL,
    b DOUBLE NOT NULL,
    a0 DOUBLE NOT NULL,
    ta_pct DOUBLE NOT NULL,
    tc DOUBLE NOT NULL,
    PRIMARY KEY (commodity, importer, exporter)
);
COMMENT ON TABLE mkt_bilateral_flows_2030 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_flows_2030', 'q_kt', NULL, 'open', 'bilateral_flows_2030.q_kt: unit to be established'),
  ('mkt_bilateral_flows_2030', 'a', NULL, 'open', 'bilateral_flows_2030.a: unit to be established'),
  ('mkt_bilateral_flows_2030', 'b', NULL, 'open', 'bilateral_flows_2030.b: unit to be established'),
  ('mkt_bilateral_flows_2030', 'a0', NULL, 'open', 'bilateral_flows_2030.a0: unit to be established'),
  ('mkt_bilateral_flows_2030', 'ta_pct', NULL, 'open', 'bilateral_flows_2030.ta_pct: unit to be established'),
  ('mkt_bilateral_flows_2030', 'tc', NULL, 'open', 'bilateral_flows_2030.tc: unit to be established');

-- file: capri_data/2017/market/bilateral_flows_2030_eu2.csv
CREATE TABLE mkt_bilateral_flows_2030_eu2 (
    commodity VARCHAR NOT NULL,
    importer VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    q_kt DOUBLE NOT NULL,
    a DOUBLE NOT NULL,
    b DOUBLE NOT NULL,
    a0 DOUBLE NOT NULL,
    ta_pct DOUBLE NOT NULL,
    tc DOUBLE NOT NULL,
    PRIMARY KEY (commodity, importer, exporter)
);
COMMENT ON TABLE mkt_bilateral_flows_2030_eu2 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_flows_2030_eu2', 'q_kt', NULL, 'open', 'bilateral_flows_2030_eu2.q_kt: unit to be established'),
  ('mkt_bilateral_flows_2030_eu2', 'a', NULL, 'open', 'bilateral_flows_2030_eu2.a: unit to be established'),
  ('mkt_bilateral_flows_2030_eu2', 'b', NULL, 'open', 'bilateral_flows_2030_eu2.b: unit to be established'),
  ('mkt_bilateral_flows_2030_eu2', 'a0', NULL, 'open', 'bilateral_flows_2030_eu2.a0: unit to be established'),
  ('mkt_bilateral_flows_2030_eu2', 'ta_pct', NULL, 'open', 'bilateral_flows_2030_eu2.ta_pct: unit to be established'),
  ('mkt_bilateral_flows_2030_eu2', 'tc', NULL, 'open', 'bilateral_flows_2030_eu2.tc: unit to be established');

-- file: capri_data/2017/market/bilateral_regions_2017.csv
CREATE TABLE mkt_bilateral_regions_2017 (
    commodity VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    pmrk DOUBLE NOT NULL,
    prod_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, region)
);
COMMENT ON TABLE mkt_bilateral_regions_2017 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_regions_2017', 'pmrk', NULL, 'open', 'bilateral_regions_2017.pmrk: unit to be established'),
  ('mkt_bilateral_regions_2017', 'prod_kt', NULL, 'open', 'bilateral_regions_2017.prod_kt: unit to be established');

-- file: capri_data/2017/market/bilateral_regions_2017_eu2.csv
CREATE TABLE mkt_bilateral_regions_2017_eu2 (
    commodity VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    pmrk DOUBLE NOT NULL,
    prod_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, region)
);
COMMENT ON TABLE mkt_bilateral_regions_2017_eu2 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_regions_2017_eu2', 'pmrk', NULL, 'open', 'bilateral_regions_2017_eu2.pmrk: unit to be established'),
  ('mkt_bilateral_regions_2017_eu2', 'prod_kt', NULL, 'open', 'bilateral_regions_2017_eu2.prod_kt: unit to be established');

-- file: capri_data/2017/market/bilateral_regions_2030.csv
CREATE TABLE mkt_bilateral_regions_2030 (
    commodity VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    pmrk DOUBLE NOT NULL,
    prod_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, region)
);
COMMENT ON TABLE mkt_bilateral_regions_2030 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_regions_2030', 'pmrk', NULL, 'open', 'bilateral_regions_2030.pmrk: unit to be established'),
  ('mkt_bilateral_regions_2030', 'prod_kt', NULL, 'open', 'bilateral_regions_2030.prod_kt: unit to be established');

-- file: capri_data/2017/market/bilateral_regions_2030_eu2.csv
CREATE TABLE mkt_bilateral_regions_2030_eu2 (
    commodity VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    pmrk DOUBLE NOT NULL,
    prod_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, region)
);
COMMENT ON TABLE mkt_bilateral_regions_2030_eu2 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_regions_2030_eu2', 'pmrk', NULL, 'open', 'bilateral_regions_2030_eu2.pmrk: unit to be established'),
  ('mkt_bilateral_regions_2030_eu2', 'prod_kt', NULL, 'open', 'bilateral_regions_2030_eu2.prod_kt: unit to be established');

-- file: capri_data/2017/market/bilateral_trq_2017.csv
CREATE TABLE mkt_bilateral_trq_2017 (
    commodity VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    quota_kt DOUBLE NOT NULL,
    gap_eur_t DOUBLE NOT NULL,
    imports_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, exporter)
);
COMMENT ON TABLE mkt_bilateral_trq_2017 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_trq_2017', 'quota_kt', NULL, 'open', 'bilateral_trq_2017.quota_kt: unit to be established'),
  ('mkt_bilateral_trq_2017', 'gap_eur_t', NULL, 'open', 'bilateral_trq_2017.gap_eur_t: unit to be established'),
  ('mkt_bilateral_trq_2017', 'imports_kt', NULL, 'open', 'bilateral_trq_2017.imports_kt: unit to be established');

-- file: capri_data/2017/market/bilateral_trq_2030.csv
CREATE TABLE mkt_bilateral_trq_2030 (
    commodity VARCHAR NOT NULL,
    exporter VARCHAR NOT NULL,
    quota_kt DOUBLE NOT NULL,
    gap_eur_t DOUBLE NOT NULL,
    imports_kt DOUBLE NOT NULL,
    PRIMARY KEY (commodity, exporter)
);
COMMENT ON TABLE mkt_bilateral_trq_2030 IS 'CAPRI''s bilateral trade data for the model''s trade regions (Sprint 8m: CAPRI''s full market). (tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('mkt_bilateral_trq_2030', 'quota_kt', NULL, 'open', 'bilateral_trq_2030.quota_kt: unit to be established'),
  ('mkt_bilateral_trq_2030', 'gap_eur_t', NULL, 'open', 'bilateral_trq_2030.gap_eur_t: unit to be established'),
  ('mkt_bilateral_trq_2030', 'imports_kt', NULL, 'open', 'bilateral_trq_2030.imports_kt: unit to be established');

-- file: capri_data/2017/market/biofuel_feedstock_2017.csv
CREATE TABLE mkt_biofuel_feedstock_2017 (
    ms VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    biofuel VARCHAR NOT NULL,
    feedstock VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    biof_kt DOUBLE NOT NULL,
    prcb DOUBLE NOT NULL,
    prcby DOUBLE NOT NULL,
    byproduct VARCHAR,
    feed_price DOUBLE NOT NULL,
    byproduct_price DOUBLE NOT NULL,
    rho DOUBLE NOT NULL,
    numeraire BIGINT NOT NULL
);
COMMENT ON TABLE mkt_biofuel_feedstock_2017 IS 'Market year 2017: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_feedstock_2017', 'biof_kt', NULL, 'open', 'biofuel_feedstock_2017.biof_kt: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'prcb', NULL, 'open', 'biofuel_feedstock_2017.prcb: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'prcby', NULL, 'open', 'biofuel_feedstock_2017.prcby: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'feed_price', NULL, 'open', 'biofuel_feedstock_2017.feed_price: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'byproduct_price', NULL, 'open', 'biofuel_feedstock_2017.byproduct_price: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'rho', NULL, 'open', 'biofuel_feedstock_2017.rho: unit to be established'),
  ('mkt_biofuel_feedstock_2017', 'numeraire', NULL, 'open', 'biofuel_feedstock_2017.numeraire: unit to be established');

-- file: capri_data/2017/market/biofuel_feedstock_2030.csv
CREATE TABLE mkt_biofuel_feedstock_2030 (
    ms VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    biofuel VARCHAR NOT NULL,
    feedstock VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    biof_kt DOUBLE NOT NULL,
    prcb DOUBLE NOT NULL,
    prcby DOUBLE NOT NULL,
    byproduct VARCHAR,
    feed_price DOUBLE NOT NULL,
    byproduct_price DOUBLE NOT NULL,
    rho DOUBLE NOT NULL,
    numeraire BIGINT NOT NULL
);
COMMENT ON TABLE mkt_biofuel_feedstock_2030 IS 'Market year 2030: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_feedstock_2030', 'biof_kt', NULL, 'open', 'biofuel_feedstock_2030.biof_kt: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'prcb', NULL, 'open', 'biofuel_feedstock_2030.prcb: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'prcby', NULL, 'open', 'biofuel_feedstock_2030.prcby: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'feed_price', NULL, 'open', 'biofuel_feedstock_2030.feed_price: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'byproduct_price', NULL, 'open', 'biofuel_feedstock_2030.byproduct_price: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'rho', NULL, 'open', 'biofuel_feedstock_2030.rho: unit to be established'),
  ('mkt_biofuel_feedstock_2030', 'numeraire', NULL, 'open', 'biofuel_feedstock_2030.numeraire: unit to be established');

-- file: capri_data/2017/market/biofuel_market_2017.csv
CREATE TABLE mkt_biofuel_market_2017 (
    ms VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    biofuel VARCHAR NOT NULL,
    rmssup BIGINT NOT NULL,
    prod_kt DOUBLE NOT NULL,
    x0_kt DOUBLE NOT NULL,
    fixed_kt DOUBLE NOT NULL,
    ppri DOUBLE NOT NULL,
    pmrk DOUBLE NOT NULL,
    bfc DOUBLE NOT NULL,
    pr0 DOUBLE NOT NULL,
    sup_scale DOUBLE NOT NULL,
    sup_alfa DOUBLE NOT NULL,
    sup_beta DOUBLE NOT NULL,
    sup_slope DOUBLE NOT NULL,
    sup_turn DOUBLE NOT NULL,
    biof_kt DOUBLE NOT NULL,
    cpri DOUBLE NOT NULL,
    arm1p DOUBLE NOT NULL,
    fossil_cpri DOUBLE NOT NULL,
    hcon_kt DOUBLE NOT NULL,
    oil_eq DOUBLE NOT NULL,
    oil_eq_fossil DOUBLE NOT NULL,
    quts DOUBLE NOT NULL,
    cal_share DOUBLE NOT NULL,
    dem_max DOUBLE NOT NULL,
    dem_slope DOUBLE NOT NULL,
    dem_turn DOUBLE NOT NULL,
    proc_kt DOUBLE NOT NULL,
    proc_hess DOUBLE NOT NULL,
    inpe DOUBLE NOT NULL,
    PRIMARY KEY (ms, region, biofuel)
);
COMMENT ON TABLE mkt_biofuel_market_2017 IS 'Market year 2017: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_market_2017', 'rmssup', NULL, 'open', 'biofuel_market_2017.rmssup: unit to be established'),
  ('mkt_biofuel_market_2017', 'prod_kt', NULL, 'open', 'biofuel_market_2017.prod_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'x0_kt', NULL, 'open', 'biofuel_market_2017.x0_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'fixed_kt', NULL, 'open', 'biofuel_market_2017.fixed_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'ppri', NULL, 'open', 'biofuel_market_2017.ppri: unit to be established'),
  ('mkt_biofuel_market_2017', 'pmrk', NULL, 'open', 'biofuel_market_2017.pmrk: unit to be established'),
  ('mkt_biofuel_market_2017', 'bfc', NULL, 'open', 'biofuel_market_2017.bfc: unit to be established'),
  ('mkt_biofuel_market_2017', 'pr0', NULL, 'open', 'biofuel_market_2017.pr0: unit to be established'),
  ('mkt_biofuel_market_2017', 'sup_scale', NULL, 'open', 'biofuel_market_2017.sup_scale: unit to be established'),
  ('mkt_biofuel_market_2017', 'sup_alfa', NULL, 'open', 'biofuel_market_2017.sup_alfa: unit to be established'),
  ('mkt_biofuel_market_2017', 'sup_beta', NULL, 'open', 'biofuel_market_2017.sup_beta: unit to be established'),
  ('mkt_biofuel_market_2017', 'sup_slope', NULL, 'open', 'biofuel_market_2017.sup_slope: unit to be established'),
  ('mkt_biofuel_market_2017', 'sup_turn', NULL, 'open', 'biofuel_market_2017.sup_turn: unit to be established'),
  ('mkt_biofuel_market_2017', 'biof_kt', NULL, 'open', 'biofuel_market_2017.biof_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'cpri', NULL, 'open', 'biofuel_market_2017.cpri: unit to be established'),
  ('mkt_biofuel_market_2017', 'arm1p', NULL, 'open', 'biofuel_market_2017.arm1p: unit to be established'),
  ('mkt_biofuel_market_2017', 'fossil_cpri', NULL, 'open', 'biofuel_market_2017.fossil_cpri: unit to be established'),
  ('mkt_biofuel_market_2017', 'hcon_kt', NULL, 'open', 'biofuel_market_2017.hcon_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'oil_eq', NULL, 'open', 'biofuel_market_2017.oil_eq: unit to be established'),
  ('mkt_biofuel_market_2017', 'oil_eq_fossil', NULL, 'open', 'biofuel_market_2017.oil_eq_fossil: unit to be established'),
  ('mkt_biofuel_market_2017', 'quts', NULL, 'open', 'biofuel_market_2017.quts: unit to be established'),
  ('mkt_biofuel_market_2017', 'cal_share', NULL, 'open', 'biofuel_market_2017.cal_share: unit to be established'),
  ('mkt_biofuel_market_2017', 'dem_max', NULL, 'open', 'biofuel_market_2017.dem_max: unit to be established'),
  ('mkt_biofuel_market_2017', 'dem_slope', NULL, 'open', 'biofuel_market_2017.dem_slope: unit to be established'),
  ('mkt_biofuel_market_2017', 'dem_turn', NULL, 'open', 'biofuel_market_2017.dem_turn: unit to be established'),
  ('mkt_biofuel_market_2017', 'proc_kt', NULL, 'open', 'biofuel_market_2017.proc_kt: unit to be established'),
  ('mkt_biofuel_market_2017', 'proc_hess', NULL, 'open', 'biofuel_market_2017.proc_hess: unit to be established'),
  ('mkt_biofuel_market_2017', 'inpe', NULL, 'open', 'biofuel_market_2017.inpe: unit to be established');

-- file: capri_data/2017/market/biofuel_market_2030.csv
CREATE TABLE mkt_biofuel_market_2030 (
    ms VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    biofuel VARCHAR NOT NULL,
    rmssup BIGINT NOT NULL,
    prod_kt DOUBLE NOT NULL,
    x0_kt DOUBLE NOT NULL,
    fixed_kt DOUBLE NOT NULL,
    ppri DOUBLE NOT NULL,
    pmrk DOUBLE NOT NULL,
    bfc DOUBLE NOT NULL,
    pr0 DOUBLE NOT NULL,
    sup_scale DOUBLE NOT NULL,
    sup_alfa DOUBLE NOT NULL,
    sup_beta DOUBLE NOT NULL,
    sup_slope DOUBLE NOT NULL,
    sup_turn DOUBLE NOT NULL,
    biof_kt DOUBLE NOT NULL,
    cpri DOUBLE NOT NULL,
    arm1p DOUBLE NOT NULL,
    fossil_cpri DOUBLE NOT NULL,
    hcon_kt DOUBLE NOT NULL,
    oil_eq DOUBLE NOT NULL,
    oil_eq_fossil DOUBLE NOT NULL,
    quts DOUBLE NOT NULL,
    cal_share DOUBLE NOT NULL,
    dem_max DOUBLE NOT NULL,
    dem_slope DOUBLE NOT NULL,
    dem_turn DOUBLE NOT NULL,
    proc_kt DOUBLE NOT NULL,
    proc_hess DOUBLE NOT NULL,
    inpe DOUBLE NOT NULL,
    PRIMARY KEY (ms, region, biofuel)
);
COMMENT ON TABLE mkt_biofuel_market_2030 IS 'Market year 2030: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_market_2030', 'rmssup', NULL, 'open', 'biofuel_market_2030.rmssup: unit to be established'),
  ('mkt_biofuel_market_2030', 'prod_kt', NULL, 'open', 'biofuel_market_2030.prod_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'x0_kt', NULL, 'open', 'biofuel_market_2030.x0_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'fixed_kt', NULL, 'open', 'biofuel_market_2030.fixed_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'ppri', NULL, 'open', 'biofuel_market_2030.ppri: unit to be established'),
  ('mkt_biofuel_market_2030', 'pmrk', NULL, 'open', 'biofuel_market_2030.pmrk: unit to be established'),
  ('mkt_biofuel_market_2030', 'bfc', NULL, 'open', 'biofuel_market_2030.bfc: unit to be established'),
  ('mkt_biofuel_market_2030', 'pr0', NULL, 'open', 'biofuel_market_2030.pr0: unit to be established'),
  ('mkt_biofuel_market_2030', 'sup_scale', NULL, 'open', 'biofuel_market_2030.sup_scale: unit to be established'),
  ('mkt_biofuel_market_2030', 'sup_alfa', NULL, 'open', 'biofuel_market_2030.sup_alfa: unit to be established'),
  ('mkt_biofuel_market_2030', 'sup_beta', NULL, 'open', 'biofuel_market_2030.sup_beta: unit to be established'),
  ('mkt_biofuel_market_2030', 'sup_slope', NULL, 'open', 'biofuel_market_2030.sup_slope: unit to be established'),
  ('mkt_biofuel_market_2030', 'sup_turn', NULL, 'open', 'biofuel_market_2030.sup_turn: unit to be established'),
  ('mkt_biofuel_market_2030', 'biof_kt', NULL, 'open', 'biofuel_market_2030.biof_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'cpri', NULL, 'open', 'biofuel_market_2030.cpri: unit to be established'),
  ('mkt_biofuel_market_2030', 'arm1p', NULL, 'open', 'biofuel_market_2030.arm1p: unit to be established'),
  ('mkt_biofuel_market_2030', 'fossil_cpri', NULL, 'open', 'biofuel_market_2030.fossil_cpri: unit to be established'),
  ('mkt_biofuel_market_2030', 'hcon_kt', NULL, 'open', 'biofuel_market_2030.hcon_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'oil_eq', NULL, 'open', 'biofuel_market_2030.oil_eq: unit to be established'),
  ('mkt_biofuel_market_2030', 'oil_eq_fossil', NULL, 'open', 'biofuel_market_2030.oil_eq_fossil: unit to be established'),
  ('mkt_biofuel_market_2030', 'quts', NULL, 'open', 'biofuel_market_2030.quts: unit to be established'),
  ('mkt_biofuel_market_2030', 'cal_share', NULL, 'open', 'biofuel_market_2030.cal_share: unit to be established'),
  ('mkt_biofuel_market_2030', 'dem_max', NULL, 'open', 'biofuel_market_2030.dem_max: unit to be established'),
  ('mkt_biofuel_market_2030', 'dem_slope', NULL, 'open', 'biofuel_market_2030.dem_slope: unit to be established'),
  ('mkt_biofuel_market_2030', 'dem_turn', NULL, 'open', 'biofuel_market_2030.dem_turn: unit to be established'),
  ('mkt_biofuel_market_2030', 'proc_kt', NULL, 'open', 'biofuel_market_2030.proc_kt: unit to be established'),
  ('mkt_biofuel_market_2030', 'proc_hess', NULL, 'open', 'biofuel_market_2030.proc_hess: unit to be established'),
  ('mkt_biofuel_market_2030', 'inpe', NULL, 'open', 'biofuel_market_2030.inpe: unit to be established');

-- file: capri_data/2017/market/biofuel_use_share_2017.csv
CREATE TABLE mkt_biofuel_use_share_2017 (
    commodity VARCHAR NOT NULL,
    biof_kt DOUBLE NOT NULL,
    use_kt DOUBLE NOT NULL,
    share DOUBLE NOT NULL,
    PRIMARY KEY (commodity)
);
COMMENT ON TABLE mkt_biofuel_use_share_2017 IS 'Market year 2017: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_use_share_2017', 'biof_kt', NULL, 'open', 'biofuel_use_share_2017.biof_kt: unit to be established'),
  ('mkt_biofuel_use_share_2017', 'use_kt', NULL, 'open', 'biofuel_use_share_2017.use_kt: unit to be established'),
  ('mkt_biofuel_use_share_2017', 'share', NULL, 'open', 'biofuel_use_share_2017.share: unit to be established');

-- file: capri_data/2017/market/biofuel_use_share_2030.csv
CREATE TABLE mkt_biofuel_use_share_2030 (
    commodity VARCHAR NOT NULL,
    biof_kt DOUBLE NOT NULL,
    use_kt DOUBLE NOT NULL,
    share DOUBLE NOT NULL,
    PRIMARY KEY (commodity)
);
COMMENT ON TABLE mkt_biofuel_use_share_2030 IS 'Market year 2030: CAPRI''s biofuel markets: feedstock demand, biofuel supply and biofuel demand, per CAPRI market region. (tools/build/build_biofuel_market.py)';
INSERT INTO value_units VALUES
  ('mkt_biofuel_use_share_2030', 'biof_kt', NULL, 'open', 'biofuel_use_share_2030.biof_kt: unit to be established'),
  ('mkt_biofuel_use_share_2030', 'use_kt', NULL, 'open', 'biofuel_use_share_2030.use_kt: unit to be established'),
  ('mkt_biofuel_use_share_2030', 'share', NULL, 'open', 'biofuel_use_share_2030.share: unit to be established');

-- file: capri_data/2017/market/crushing_parameters_2017.csv
CREATE TABLE mkt_crushing_parameters_2017 (
    region VARCHAR NOT NULL,
    seed VARCHAR NOT NULL,
    crush_kt DOUBLE NOT NULL,
    oil_yield DOUBLE NOT NULL,
    cake_yield DOUBLE NOT NULL,
    elasticity DOUBLE NOT NULL,
    elasticity_source VARCHAR NOT NULL,
    crush_share_of_use DOUBLE,
    capri_regions VARCHAR NOT NULL,
    PRIMARY KEY (region, seed, elasticity_source, capri_regions)
);
COMMENT ON TABLE mkt_crushing_parameters_2017 IS 'CAPRI''s oilseed crushing per model trade region at the 2017 market year: crush = PROC of the seed, oil and cake yields = CAPRI''s PRCY, from CAPRI''s market data of 2017 (tools/build/build_crushing_parameters.py)';
INSERT INTO value_units VALUES
  ('mkt_crushing_parameters_2017', 'crush_kt', NULL, 'open', 'crushing_parameters_2017.crush_kt: unit to be established'),
  ('mkt_crushing_parameters_2017', 'oil_yield', NULL, 'open', 'crushing_parameters_2017.oil_yield: unit to be established'),
  ('mkt_crushing_parameters_2017', 'cake_yield', NULL, 'open', 'crushing_parameters_2017.cake_yield: unit to be established'),
  ('mkt_crushing_parameters_2017', 'elasticity', NULL, 'open', 'crushing_parameters_2017.elasticity: unit to be established'),
  ('mkt_crushing_parameters_2017', 'crush_share_of_use', NULL, 'open', 'crushing_parameters_2017.crush_share_of_use: unit to be established');

-- file: capri_data/2017/market/crushing_parameters_2030.csv
CREATE TABLE mkt_crushing_parameters_2030 (
    region VARCHAR NOT NULL,
    seed VARCHAR NOT NULL,
    crush_kt DOUBLE NOT NULL,
    oil_yield DOUBLE NOT NULL,
    cake_yield DOUBLE NOT NULL,
    elasticity DOUBLE NOT NULL,
    elasticity_source VARCHAR NOT NULL,
    crush_share_of_use DOUBLE,
    capri_regions VARCHAR NOT NULL,
    PRIMARY KEY (region, seed, elasticity_source, capri_regions)
);
COMMENT ON TABLE mkt_crushing_parameters_2030 IS 'CAPRI''s oilseed crushing per model trade region at the 2030 market year: crush = PROC of the seed, oil and cake yields = CAPRI''s PRCY, from CAPRI''s market data of 2030 (tools/build/build_crushing_parameters.py)';
INSERT INTO value_units VALUES
  ('mkt_crushing_parameters_2030', 'crush_kt', NULL, 'open', 'crushing_parameters_2030.crush_kt: unit to be established'),
  ('mkt_crushing_parameters_2030', 'oil_yield', NULL, 'open', 'crushing_parameters_2030.oil_yield: unit to be established'),
  ('mkt_crushing_parameters_2030', 'cake_yield', NULL, 'open', 'crushing_parameters_2030.cake_yield: unit to be established'),
  ('mkt_crushing_parameters_2030', 'elasticity', NULL, 'open', 'crushing_parameters_2030.elasticity: unit to be established'),
  ('mkt_crushing_parameters_2030', 'crush_share_of_use', NULL, 'open', 'crushing_parameters_2030.crush_share_of_use: unit to be established');

-- file: capri_data/2017/market/dairy_eu_balance.csv
CREATE TABLE mkt_dairy_eu_balance (
    product VARCHAR NOT NULL,
    prod_kt DOUBLE NOT NULL,
    hcom_kt DOUBLE NOT NULL,
    fedm_kt DOUBLE NOT NULL,
    indm_kt DOUBLE NOT NULL,
    losm_kt DOUBLE NOT NULL,
    proc_kt DOUBLE NOT NULL,
    net_imports_kt DOUBLE NOT NULL,
    capri_extra_eu_net_imports_kt DOUBLE NOT NULL,
    eta_hcom DOUBLE NOT NULL,
    PRIMARY KEY (product)
);
COMMENT ON TABLE mkt_dairy_eu_balance IS 'CAPRI''s dairy processing, per member state: fat and protein balance and the dairies'' normalised (tools/build/build_dairy_processing.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_eu_balance', 'prod_kt', NULL, 'open', 'dairy_eu_balance.prod_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'hcom_kt', NULL, 'open', 'dairy_eu_balance.hcom_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'fedm_kt', NULL, 'open', 'dairy_eu_balance.fedm_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'indm_kt', NULL, 'open', 'dairy_eu_balance.indm_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'losm_kt', NULL, 'open', 'dairy_eu_balance.losm_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'proc_kt', NULL, 'open', 'dairy_eu_balance.proc_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'net_imports_kt', NULL, 'open', 'dairy_eu_balance.net_imports_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'capri_extra_eu_net_imports_kt', NULL, 'open', 'dairy_eu_balance.capri_extra_eu_net_imports_kt: unit to be established'),
  ('mkt_dairy_eu_balance', 'eta_hcom', NULL, 'open', 'dairy_eu_balance.eta_hcom: unit to be established');

-- file: capri_data/2017/market/dairy_eu_demand_elas.csv
CREATE TABLE mkt_dairy_eu_demand_elas (
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    elas DOUBLE NOT NULL,
    PRIMARY KEY (row, col)
);
COMMENT ON TABLE mkt_dairy_eu_demand_elas IS 'CAPRI''s dairy processing, per member state: fat and protein balance and the dairies'' normalised (tools/build/build_dairy_processing.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_eu_demand_elas', 'elas', NULL, 'open', 'dairy_eu_demand_elas.elas: unit to be established');

-- file: capri_data/2017/market/dairy_hessian.csv
CREATE TABLE mkt_dairy_hessian (
    ms VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    h DOUBLE NOT NULL,
    PRIMARY KEY (ms, row, col)
);
COMMENT ON TABLE mkt_dairy_hessian IS 'CAPRI''s dairy processing, per member state: fat and protein balance and the dairies'' normalised (tools/build/build_dairy_processing.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_hessian', 'h', NULL, 'open', 'dairy_hessian.h: unit to be established');

-- file: capri_data/2017/market/dairy_processing.csv
CREATE TABLE mkt_dairy_processing (
    ms VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    price DOUBLE NOT NULL,
    q_kt DOUBLE,
    proc_kt DOUBLE,
    fats_pct DOUBLE,
    prot_pct DOUBLE,
    csei DOUBLE,
    PRIMARY KEY (ms, "item")
);
COMMENT ON TABLE mkt_dairy_processing IS 'CAPRI''s dairy processing, per member state: fat and protein balance and the dairies'' normalised (tools/build/build_dairy_processing.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_processing', 'price', NULL, 'open', 'dairy_processing.price: unit to be established'),
  ('mkt_dairy_processing', 'q_kt', NULL, 'open', 'dairy_processing.q_kt: unit to be established'),
  ('mkt_dairy_processing', 'proc_kt', NULL, 'open', 'dairy_processing.proc_kt: unit to be established'),
  ('mkt_dairy_processing', 'fats_pct', NULL, 'open', 'dairy_processing.fats_pct: unit to be established'),
  ('mkt_dairy_processing', 'prot_pct', NULL, 'open', 'dairy_processing.prot_pct: unit to be established'),
  ('mkt_dairy_processing', 'csei', NULL, 'open', 'dairy_processing.csei: unit to be established');

-- file: capri_data/2017/market/dairy_world_demand_elas.csv
CREATE TABLE mkt_dairy_world_demand_elas (
    rms VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    elas DOUBLE NOT NULL,
    PRIMARY KEY (rms, row, col)
);
COMMENT ON TABLE mkt_dairy_world_demand_elas IS 'CAPRI''s dairy block for the non-EU market regions (dairy Stage 4). (tools/build/build_dairy_world_blocks.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_world_demand_elas', 'elas', NULL, 'open', 'dairy_world_demand_elas.elas: unit to be established');

-- file: capri_data/2017/market/dairy_world_hessian.csv
CREATE TABLE mkt_dairy_world_hessian (
    rms VARCHAR NOT NULL,
    row VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    h DOUBLE NOT NULL,
    PRIMARY KEY (rms, row, col)
);
COMMENT ON TABLE mkt_dairy_world_hessian IS 'CAPRI''s dairy block for the non-EU market regions (dairy Stage 4). (tools/build/build_dairy_world_blocks.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_world_hessian', 'h', NULL, 'open', 'dairy_world_hessian.h: unit to be established');

-- file: capri_data/2017/market/dairy_world_processing.csv
CREATE TABLE mkt_dairy_world_processing (
    trade_region VARCHAR NOT NULL,
    rms VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    price DOUBLE NOT NULL,
    q_kt DOUBLE,
    proc_kt DOUBLE,
    fats_pct DOUBLE,
    prot_pct DOUBLE,
    hcon_kt DOUBLE,
    feed_kt DOUBLE,
    net_imports_kt DOUBLE,
    PRIMARY KEY (trade_region, rms, "item")
);
COMMENT ON TABLE mkt_dairy_world_processing IS 'CAPRI''s dairy block for the non-EU market regions (dairy Stage 4). (tools/build/build_dairy_world_blocks.py)';
INSERT INTO value_units VALUES
  ('mkt_dairy_world_processing', 'price', NULL, 'open', 'dairy_world_processing.price: unit to be established'),
  ('mkt_dairy_world_processing', 'q_kt', NULL, 'open', 'dairy_world_processing.q_kt: unit to be established'),
  ('mkt_dairy_world_processing', 'proc_kt', NULL, 'open', 'dairy_world_processing.proc_kt: unit to be established'),
  ('mkt_dairy_world_processing', 'fats_pct', NULL, 'open', 'dairy_world_processing.fats_pct: unit to be established'),
  ('mkt_dairy_world_processing', 'prot_pct', NULL, 'open', 'dairy_world_processing.prot_pct: unit to be established'),
  ('mkt_dairy_world_processing', 'hcon_kt', NULL, 'open', 'dairy_world_processing.hcon_kt: unit to be established'),
  ('mkt_dairy_world_processing', 'feed_kt', NULL, 'open', 'dairy_world_processing.feed_kt: unit to be established'),
  ('mkt_dairy_world_processing', 'net_imports_kt', NULL, 'open', 'dairy_world_processing.net_imports_kt: unit to be established');

-- file: capri_data/2017/market/eu_ms_balance_2030.csv
CREATE TABLE mkt_eu_ms_balance_2030 (
    ms VARCHAR NOT NULL,
    block VARCHAR NOT NULL,
    product VARCHAR NOT NULL,
    commodity VARCHAR,
    prod_kt DOUBLE NOT NULL,
    hcon_kt DOUBLE NOT NULL,
    feed_kt DOUBLE NOT NULL,
    proc_kt DOUBLE NOT NULL,
    biof_kt DOUBLE NOT NULL
);
COMMENT ON TABLE mkt_eu_ms_balance_2030 IS 'CAPRI''s 2030 market balance per EU member state (Data_CAL of data_market_1730defaulta), for the market with the EU (tools/build/build_eu_ms_balance.py)';
INSERT INTO value_units VALUES
  ('mkt_eu_ms_balance_2030', 'prod_kt', NULL, 'open', 'eu_ms_balance_2030.prod_kt: unit to be established'),
  ('mkt_eu_ms_balance_2030', 'hcon_kt', NULL, 'open', 'eu_ms_balance_2030.hcon_kt: unit to be established'),
  ('mkt_eu_ms_balance_2030', 'feed_kt', NULL, 'open', 'eu_ms_balance_2030.feed_kt: unit to be established'),
  ('mkt_eu_ms_balance_2030', 'proc_kt', NULL, 'open', 'eu_ms_balance_2030.proc_kt: unit to be established'),
  ('mkt_eu_ms_balance_2030', 'biof_kt', NULL, 'open', 'eu_ms_balance_2030.biof_kt: unit to be established');

-- file: capri_data/2017/market/feed_byproducts.csv
CREATE TABLE mkt_feed_byproducts (
    product VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    use VARCHAR NOT NULL,
    base_kt DOUBLE NOT NULL,
    weight DOUBLE NOT NULL,
    prod0_kt DOUBLE NOT NULL,
    PRIMARY KEY (product, commodity, use)
);
COMMENT ON TABLE mkt_feed_byproducts IS 'CAPRI''s residual feed products FENI and FPRI as markets (arm/market_model.gms MaprFeed_; Sprint 9h). (tools/build/build_feed_byproducts.py)';
INSERT INTO value_units VALUES
  ('mkt_feed_byproducts', 'base_kt', NULL, 'open', 'feed_byproducts.base_kt: unit to be established'),
  ('mkt_feed_byproducts', 'weight', NULL, 'open', 'feed_byproducts.weight: unit to be established'),
  ('mkt_feed_byproducts', 'prod0_kt', NULL, 'open', 'feed_byproducts.prod0_kt: unit to be established');

-- file: capri_data/2017/market/gl_demand_b.csv
CREATE TABLE mkt_gl_demand_b (
    rms VARCHAR NOT NULL,
    i VARCHAR NOT NULL,
    j VARCHAR NOT NULL,
    b DOUBLE NOT NULL,
    PRIMARY KEY (rms, i, j)
);
COMMENT ON TABLE mkt_gl_demand_b IS 'CAPRI''s food demand system (Generalised Leontief) per behavioural region, for the market model (October 2026). (tools/build/build_gl_demand.py)';
INSERT INTO value_units VALUES
  ('mkt_gl_demand_b', 'b', NULL, 'open', 'gl_demand_b.b: unit to be established');

-- file: capri_data/2017/market/gl_demand_goods.csv
CREATE TABLE mkt_gl_demand_goods (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    good VARCHAR NOT NULL,
    model_commodity VARCHAR,
    d DOUBLE NOT NULL,
    cpri DOUBLE NOT NULL,
    hcon DOUBLE NOT NULL,
    use DOUBLE NOT NULL,
    arm1p DOUBLE NOT NULL
);
COMMENT ON TABLE mkt_gl_demand_goods IS 'CAPRI''s food demand system (Generalised Leontief) per behavioural region, for the market model (October 2026). (tools/build/build_gl_demand.py)';
INSERT INTO value_units VALUES
  ('mkt_gl_demand_goods', 'd', NULL, 'open', 'gl_demand_goods.d: unit to be established'),
  ('mkt_gl_demand_goods', 'cpri', NULL, 'open', 'gl_demand_goods.cpri: unit to be established'),
  ('mkt_gl_demand_goods', 'hcon', NULL, 'open', 'gl_demand_goods.hcon: unit to be established'),
  ('mkt_gl_demand_goods', 'use', NULL, 'open', 'gl_demand_goods.use: unit to be established'),
  ('mkt_gl_demand_goods', 'arm1p', NULL, 'open', 'gl_demand_goods.arm1p: unit to be established');

-- file: capri_data/2017/market/gl_demand_regions.csv
CREATE TABLE mkt_gl_demand_regions (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    Y DOUBLE NOT NULL,
    inha DOUBLE NOT NULL,
    max_rel_err DOUBLE NOT NULL,
    PRIMARY KEY (rms, model_region)
);
COMMENT ON TABLE mkt_gl_demand_regions IS 'CAPRI''s food demand system (Generalised Leontief) per behavioural region, for the market model (October 2026). (tools/build/build_gl_demand.py)';
INSERT INTO value_units VALUES
  ('mkt_gl_demand_regions', 'Y', NULL, 'open', 'gl_demand_regions.Y: unit to be established'),
  ('mkt_gl_demand_regions', 'inha', NULL, 'open', 'gl_demand_regions.inha: unit to be established'),
  ('mkt_gl_demand_regions', 'max_rel_err', NULL, 'open', 'gl_demand_regions.max_rel_err: unit to be established');

-- file: capri_data/2017/market/processing_nq_base.csv
CREATE TABLE mkt_processing_nq_base (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    proc_kt DOUBLE NOT NULL,
    use_kt DOUBLE NOT NULL,
    inpe DOUBLE NOT NULL,
    PRIMARY KEY (rms, model_region, commodity)
);
COMMENT ON TABLE mkt_processing_nq_base IS 'CAPRI''s processing demand functions (arm/market_model.gms ProcNQ_) per behavioural region, for the market. (tools/build/build_processing_nq.py)';
INSERT INTO value_units VALUES
  ('mkt_processing_nq_base', 'proc_kt', NULL, 'open', 'processing_nq_base.proc_kt: unit to be established'),
  ('mkt_processing_nq_base', 'use_kt', NULL, 'open', 'processing_nq_base.use_kt: unit to be established'),
  ('mkt_processing_nq_base', 'inpe', NULL, 'open', 'processing_nq_base.inpe: unit to be established');

-- file: capri_data/2017/market/processing_nq_hessian.csv
CREATE TABLE mkt_processing_nq_hessian (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    x VARCHAR NOT NULL,
    y VARCHAR NOT NULL,
    h DOUBLE NOT NULL,
    arm1p_x DOUBLE NOT NULL,
    arm1p_y DOUBLE NOT NULL,
    PRIMARY KEY (rms, model_region, x, y)
);
COMMENT ON TABLE mkt_processing_nq_hessian IS 'CAPRI''s processing demand functions (arm/market_model.gms ProcNQ_) per behavioural region, for the market. (tools/build/build_processing_nq.py)';
INSERT INTO value_units VALUES
  ('mkt_processing_nq_hessian', 'h', NULL, 'open', 'processing_nq_hessian.h: unit to be established'),
  ('mkt_processing_nq_hessian', 'arm1p_x', NULL, 'open', 'processing_nq_hessian.arm1p_x: unit to be established'),
  ('mkt_processing_nq_hessian', 'arm1p_y', NULL, 'open', 'processing_nq_hessian.arm1p_y: unit to be established');

-- file: capri_data/2017/market/processing_seeds.csv
CREATE TABLE mkt_processing_seeds (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    seed VARCHAR NOT NULL,
    oil VARCHAR NOT NULL,
    cake VARCHAR NOT NULL,
    proc_kt DOUBLE NOT NULL,
    arm1p_seed DOUBLE NOT NULL,
    prcy_oil DOUBLE NOT NULL,
    prcy_cake DOUBLE NOT NULL,
    ppri_oil DOUBLE NOT NULL,
    ppri_cake DOUBLE NOT NULL,
    prod_oil_kt DOUBLE NOT NULL,
    prod_cake_kt DOUBLE NOT NULL,
    rho_proc DOUBLE NOT NULL,
    PRIMARY KEY (rms, model_region, seed, oil, cake)
);
COMMENT ON TABLE mkt_processing_seeds IS 'CAPRI''s oilseed crushing per behavioural region, for the market''s processing block (arm/market_model.gms ProcMargO_, (tools/build/build_processing_seeds.py)';
INSERT INTO value_units VALUES
  ('mkt_processing_seeds', 'proc_kt', NULL, 'open', 'processing_seeds.proc_kt: unit to be established'),
  ('mkt_processing_seeds', 'arm1p_seed', NULL, 'open', 'processing_seeds.arm1p_seed: unit to be established'),
  ('mkt_processing_seeds', 'prcy_oil', NULL, 'open', 'processing_seeds.prcy_oil: unit to be established'),
  ('mkt_processing_seeds', 'prcy_cake', NULL, 'open', 'processing_seeds.prcy_cake: unit to be established'),
  ('mkt_processing_seeds', 'ppri_oil', NULL, 'open', 'processing_seeds.ppri_oil: unit to be established'),
  ('mkt_processing_seeds', 'ppri_cake', NULL, 'open', 'processing_seeds.ppri_cake: unit to be established'),
  ('mkt_processing_seeds', 'prod_oil_kt', NULL, 'open', 'processing_seeds.prod_oil_kt: unit to be established'),
  ('mkt_processing_seeds', 'prod_cake_kt', NULL, 'open', 'processing_seeds.prod_cake_kt: unit to be established'),
  ('mkt_processing_seeds', 'rho_proc', NULL, 'open', 'processing_seeds.rho_proc: unit to be established');

-- file: capri_data/2017/market/sugar_processing.csv
CREATE TABLE mkt_sugar_processing (
    ms VARCHAR NOT NULL,
    beet_grof_kt DOUBLE NOT NULL,
    beet_prcm_kt DOUBLE NOT NULL,
    sugar_mapr_kt DOUBLE NOT NULL,
    prcy DOUBLE NOT NULL,
    sugar_per_beet DOUBLE NOT NULL,
    PRIMARY KEY (ms)
);
COMMENT ON TABLE mkt_sugar_processing IS 'CAPRI''s sugar processing per member state: white sugar from sugar beet (arm/data_cal.gms, set_prices.gms). (tools/build/build_sugar_processing.py)';
INSERT INTO value_units VALUES
  ('mkt_sugar_processing', 'beet_grof_kt', NULL, 'open', 'sugar_processing.beet_grof_kt: unit to be established'),
  ('mkt_sugar_processing', 'beet_prcm_kt', NULL, 'open', 'sugar_processing.beet_prcm_kt: unit to be established'),
  ('mkt_sugar_processing', 'sugar_mapr_kt', NULL, 'open', 'sugar_processing.sugar_mapr_kt: unit to be established'),
  ('mkt_sugar_processing', 'prcy', NULL, 'open', 'sugar_processing.prcy: unit to be established'),
  ('mkt_sugar_processing', 'sugar_per_beet', NULL, 'open', 'sugar_processing.sugar_per_beet: unit to be established');

-- file: capri_data/2017/market/use_components.csv
CREATE TABLE mkt_use_components (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    commodity VARCHAR NOT NULL,
    hcon_kt DOUBLE NOT NULL,
    feed_kt DOUBLE NOT NULL,
    proc_kt DOUBLE NOT NULL,
    biof_kt DOUBLE NOT NULL,
    arm1_kt DOUBLE,
    PRIMARY KEY (rms, model_region, commodity)
);
COMMENT ON TABLE mkt_use_components IS 'CAPRI''s Armington use split into its four components per behavioural region (arm/market_model.gms ArmBal1_): (tools/build/build_use_components.py)';
INSERT INTO value_units VALUES
  ('mkt_use_components', 'hcon_kt', NULL, 'open', 'use_components.hcon_kt: unit to be established'),
  ('mkt_use_components', 'feed_kt', NULL, 'open', 'use_components.feed_kt: unit to be established'),
  ('mkt_use_components', 'proc_kt', NULL, 'open', 'use_components.proc_kt: unit to be established'),
  ('mkt_use_components', 'biof_kt', NULL, 'open', 'use_components.biof_kt: unit to be established'),
  ('mkt_use_components', 'arm1_kt', NULL, 'open', 'use_components.arm1_kt: unit to be established');

-- file: capri_data/2017/market/welfare_base_2030.csv
CREATE TABLE mkt_welfare_base_2030 (
    rms VARCHAR NOT NULL,
    model_region VARCHAR NOT NULL,
    component VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (rms, model_region, component)
);
COMMENT ON TABLE mkt_welfare_base_2030 IS 'CAPRI''s welfare report levels at the calibration point (reports/welfare.gms): the base terms CAPRI adds to each (tools/build/build_welfare_base.py)';
INSERT INTO value_units VALUES
  ('mkt_welfare_base_2030', 'value', NULL, 'open', 'welfare_base_2030.value: unit to be established');

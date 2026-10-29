-- The market's base inputs: world prices, the non-EU supply elasticities, the feed bulks, the Armington substitution
-- elasticities, the processing yields. Long files: the unit of each numeric column is in value_units (99_rules.sql).

-- file: capri_data/2017/market/world_prices.csv
CREATE TABLE world_prices (
    commodity VARCHAR PRIMARY KEY,                     -- a market commodity, or DWHE / SUGB (rule below)
    price DOUBLE NOT NULL CHECK (price > 0)
);
COMMENT ON TABLE world_prices IS 'world market prices 2017: CAPRI''s FAO_agg p_dataMarket World PMRK BAS of the commodity''s CAPRI product; OLIV from OLIO by the EU''s oil extraction; FPRI CAPRI''s export-weighted 2017 market prices; DWHE, SUGB kept for the outer loop''s price index (tools/build/build_world_prices.py, provenance sources/world_price_provenance.json)';
INSERT INTO value_units VALUES
  ('world_prices', 'price', 'U_EuPerTon', 'capri', 'CAPRI''s PMRK (EUR/t); OLIV per t of olives (builder)');

-- file: capri_data/2017/market/supply_elas_region.csv
CREATE TABLE supply_elas_region (
    region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    commodity VARCHAR NOT NULL REFERENCES model_commodities (code),
    elasticity DOUBLE NOT NULL CHECK (elasticity > 0),
    capri_regions VARCHAR NOT NULL,                    -- the trade region's CAPRI regions, space-separated
    prod_kt DOUBLE NOT NULL CHECK (prod_kt >= 0),
    PRIMARY KEY (region, commodity)
);
COMMENT ON TABLE supply_elas_region IS 'CAPRI''s own-price market supply elasticities p_elasSupp of the non-EU market regions per model trade region, production-weighted over its CAPRI regions (tools/build/build_supply_elas_nonEU.py); with market.noneu_supply_nq (default) the non-EU supply is CAPRI''s ProdNQ_ (noneu_market_supply_nq.csv) and this file serves Norway''s products without a supply model and the setting''s off state';
INSERT INTO value_units VALUES
  ('supply_elas_region', 'elasticity', 'U_Elasticity', 'capri', 'CAPRI''s p_elasSupp (own-price), weighted by production'),
  ('supply_elas_region', 'prod_kt', 'U_1000t', 'capri', 'the weights: CAPRI''s production of the trade region''s CAPRI regions');

-- file: capri_data/2017/market/feed_bulks_eu.csv
CREATE TABLE feed_bulks_eu (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    bulk VARCHAR NOT NULL CHECK (bulk IN ('FCER', 'FPRO', 'FENE', 'FOTH', 'FMIL')),
    product VARCHAR NOT NULL REFERENCES capri_xx (code),
    commodity VARCHAR NOT NULL REFERENCES model_commodities (code),
    feed_kt DOUBLE NOT NULL CHECK (feed_kt >= 0),
    arm1p DOUBLE NOT NULL CHECK (arm1p >= 0),
    rho DOUBLE NOT NULL CHECK (rho >= 0),
    PRIMARY KEY (ms, product)
);
COMMENT ON TABLE feed_bulks_eu IS 'CAPRI''s feed bulks per member state: 2030 feed use (FEED) of each product of the bulk (FEED_TO_O), the EU27yr19 Arm1 prices of markmarket_greendeal_1730et_base_1717, p_rhoFeed of arm/market1.gms l. 78-95 (tools/build/build_feed_bulks.py; docs/FEED_MARKETS.md)';
INSERT INTO value_units VALUES
  ('feed_bulks_eu', 'feed_kt', 'U_1000t', 'capri', 'CAPRI''s FEED (1000 t)'),
  ('feed_bulks_eu', 'arm1p', 'U_EuPerTon', 'capri', 'CAPRI''s ARM1P (EUR/t)'),
  ('feed_bulks_eu', 'rho', 'U_Elasticity', 'capri', 'CAPRI''s p_rhoFeed, the substitution elasticity of the products in the bulk');

-- file: capri_data/2017/market/feed_bulks_no.csv
CREATE TABLE feed_bulks_no (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    bulk VARCHAR NOT NULL CHECK (bulk IN ('FCER', 'FPRO', 'FENE', 'FOTH', 'FMIL')),
    product VARCHAR NOT NULL REFERENCES capri_xx (code),
    commodity VARCHAR NOT NULL REFERENCES model_commodities (code),
    feed_kt DOUBLE NOT NULL CHECK (feed_kt >= 0),
    arm1p DOUBLE NOT NULL CHECK (arm1p >= 0),
    rho DOUBLE NOT NULL CHECK (rho >= 0),
    use_kt DOUBLE NOT NULL CHECK (use_kt >= 0),
    PRIMARY KEY (ms, product)
);
COMMENT ON TABLE feed_bulks_no IS 'Norway''s feed bulks (KNOWN_ISSUES K56): CAPRI''s 2030 FEED and ARM1P of NO000000 and its use HCOM + FEDM + INDM + BIOF + LOSM + PRCM per product (tools/build/build_feed_bulks.py)';
INSERT INTO value_units VALUES
  ('feed_bulks_no', 'feed_kt', 'U_1000t', 'capri', 'CAPRI''s FEED (1000 t)'),
  ('feed_bulks_no', 'arm1p', 'U_EuPerTon', 'capri', 'CAPRI''s ARM1P (EUR/t)'),
  ('feed_bulks_no', 'rho', 'U_Elasticity', 'capri', 'CAPRI''s p_rhoFeed'),
  ('feed_bulks_no', 'use_kt', 'U_1000t', 'capri', 'CAPRI''s HCOM + FEDM + INDM + BIOF + LOSM + PRCM (1000 t)');

-- file: capri_data/2017/market/feed_bulks_eu_share.csv
CREATE TABLE feed_bulks_eu_share (
    commodity VARCHAR PRIMARY KEY REFERENCES model_commodities (code),
    feed_kt DOUBLE NOT NULL CHECK (feed_kt >= 0),
    use_kt DOUBLE NOT NULL CHECK (use_kt > 0),
    share DOUBLE NOT NULL CHECK (share >= 0 AND share <= 1),
    CHECK (abs(share - least(1, feed_kt / use_kt)) <= 1e-9)     -- capped at 1 (DDGS, FPRI: CAPRI's FEDM above the use summed)
);
COMMENT ON TABLE feed_bulks_eu_share IS 'the feed share of the EU''s use per model commodity in the bulks, CAPRI''s 2030 reference, processing included in the use (tools/build/build_feed_bulks.py)';
INSERT INTO value_units VALUES
  ('feed_bulks_eu_share', 'feed_kt', 'U_1000t', 'capri', 'CAPRI''s 2030 EU FEED (1000 t)'),
  ('feed_bulks_eu_share', 'use_kt', 'U_1000t', 'capri', 'CAPRI''s 2030 EU use, processing included (1000 t)'),
  ('feed_bulks_eu_share', 'share', 'U_ratio', 'builder', 'min(1, feed_kt / use_kt)');

-- file: capri_data/2017/market/armington_rho.csv
CREATE TABLE armington_rho (
    commodity VARCHAR PRIMARY KEY REFERENCES model_commodities (code),
    capri VARCHAR NOT NULL REFERENCES capri_xx (code),
    rho1 DOUBLE NOT NULL CHECK (rho1 > 0),
    rho2 DOUBLE NOT NULL CHECK (rho2 > 0)
);
COMMENT ON TABLE armington_rho IS 'CAPRI''s Armington substitution elasticities per market commodity: rho1 between domestic sales and the import aggregate, rho2 among the import origins (arm/market1.gms, special_ch/market1_ch.gms; tools/build/build_bilateral_market.py)';
INSERT INTO value_units VALUES
  ('armington_rho', 'rho1', 'U_Elasticity', 'capri', 'CAPRI''s first-stage Armington substitution elasticity'),
  ('armington_rho', 'rho2', 'U_Elasticity', 'capri', 'CAPRI''s second-stage Armington substitution elasticity');

-- file: capri_data/2017/market/processing_yields.csv
CREATE TABLE processing_yields (
    ms VARCHAR NOT NULL,                               -- a CAPRI member state, or _EU (the EU total)
    raw VARCHAR NOT NULL REFERENCES capri_pact (code),   -- CAPRI's crop output row, named as its activity (OLIV, PARI)
    product VARCHAR NOT NULL REFERENCES capri_xx (code),
    raw_kt DOUBLE NOT NULL CHECK (raw_kt > 0),
    product_kt DOUBLE NOT NULL CHECK (product_kt >= 0),
    yield DOUBLE NOT NULL CHECK (yield >= 0),
    PRIMARY KEY (ms, raw, product),
    CHECK (abs(yield - product_kt / raw_kt) <= 1e-9)
);
COMMENT ON TABLE processing_yields IS 'processing yields: olive oil per t of olives per member state, milled rice per t of paddy for the EU (tools/build/build_processing_yields.py)';
INSERT INTO value_units VALUES
  ('processing_yields', 'raw_kt', 'U_1000t', 'capri', 'CAPRI''s quantity of the raw product processed (1000 t)'),
  ('processing_yields', 'product_kt', 'U_1000t', 'capri', 'CAPRI''s quantity of the processed product (1000 t)'),
  ('processing_yields', 'yield', 'U_ratio', 'builder', 't of product per t of raw product');

-- rule: the world prices' rows are market commodities, or DWHE and SUGB (kept for the outer loop's price index)
SELECT commodity FROM world_prices
WHERE commodity NOT IN (SELECT code FROM model_commodities) AND commodity NOT IN ('DWHE', 'SUGB');

-- rule: every market commodity has a world price
SELECT code FROM model_commodities WHERE code NOT IN (SELECT commodity FROM world_prices);

-- rule: the non-EU supply elasticities' CAPRI regions are in RALL
SELECT DISTINCT code FROM (SELECT unnest(string_split(capri_regions, ' ')) AS code FROM supply_elas_region) t
WHERE code NOT IN (SELECT code FROM capri_rall);

-- rule: a CAPRI feed product belongs to one bulk and one model commodity, the same in the EU's and Norway's tables
SELECT product, count(DISTINCT bulk) AS bulks, count(DISTINCT commodity) AS commodities FROM (
    SELECT product, bulk, commodity FROM feed_bulks_eu UNION ALL SELECT product, bulk, commodity FROM feed_bulks_no) t
GROUP BY product HAVING count(DISTINCT bulk) > 1 OR count(DISTINCT commodity) > 1;

-- rule: a CAPRI feed product's bulk is CAPRI's market one, FEED_TO_XX: FEED_TO_O within the market products plus
-- wheat WHEA (the market's aggregate of SWHE and DWHE) in FCER (arm/arm_sets.gms l. 508-509)
SELECT DISTINCT b.bulk, b.product FROM (SELECT bulk, product FROM feed_bulks_eu UNION SELECT bulk, product FROM feed_bulks_no) b
WHERE NOT EXISTS (SELECT 1 FROM capri_feed_to_o f WHERE f.feed = b.bulk AND f.row = b.product)
  AND NOT (b.bulk = 'FCER' AND b.product = 'WHEA');

-- rule: one rho per bulk and region (p_rhoFeed is per bulk)
SELECT ms, bulk FROM (SELECT ms, bulk, rho FROM feed_bulks_eu UNION ALL SELECT ms, bulk, rho FROM feed_bulks_no) t
GROUP BY ms, bulk HAVING count(DISTINCT rho) > 1;

-- rule: the feed shares' commodities are commodities of the EU's bulks
SELECT commodity FROM feed_bulks_eu_share WHERE commodity NOT IN (SELECT commodity FROM feed_bulks_eu);

-- rule: the processing yields' member states are in RALL
SELECT ms FROM processing_yields WHERE ms <> '_EU' AND ms NOT IN (SELECT code FROM capri_rall);

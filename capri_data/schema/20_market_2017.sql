-- The market's supply functions outside the supply models (CAPRI's ProdNQ_) and the region maps they are summed over.
-- Long files: the unit of each numeric column is in value_units with the column's name as the item.

-- file: capri_data/schema/codes/model_trade_regions.csv
CREATE TABLE model_trade_regions (
    code VARCHAR PRIMARY KEY,
    capri_rm VARCHAR REFERENCES capri_rall (code),     -- empty: ROW, the CAPRI regions mapped to no other
    mapping_source VARCHAR NOT NULL                    -- the source of the row
);
COMMENT ON TABLE model_trade_regions IS 'the bilateral market''s trade regions in their order and the CAPRI region each stands for (market region or trade block of CAPRI''s market data); no builder: a declared code list, read by capri_mod/data/definitions.py (ALL_TRADE_REGIONS, TRADE_REGION_OF_CAPRI) and tools/build/recalibrate_trade_2017.py (REGION_MAP)';

-- file: capri_data/shared/rms_to_rm.csv
CREATE TABLE rms_to_rm (
    rms VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    rm VARCHAR NOT NULL REFERENCES capri_rall (code)
);
COMMENT ON TABLE rms_to_rm IS 'CAPRI''s behavioural regions (RMS) and the market region (RM) of each (gams/aggregation/defaultA.agg, rms_to_rm; tools/build/build_gl_demand.py)';

-- file: capri_data/2017/market/eu_market_supply_nq.csv
CREATE TABLE eu_market_supply_nq (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    x VARCHAR NOT NULL CHECK (x IN ('OTHO', 'FFIS', 'SFIS', 'OAQU')),
    y VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    h DOUBLE NOT NULL,
    ppri_y DOUBLE NOT NULL CHECK (ppri_y > 0),
    inpe DOUBLE NOT NULL CHECK (inpe > 0),
    h_ratio DOUBLE NOT NULL,
    PRIMARY KEY (ms, x, y)
);
COMMENT ON TABLE eu_market_supply_nq IS 'CAPRI''s market supply functions of the EU products no supply model produces, per member state: p_hessNQSupp at CAL completed as arm/market1.gms (elas_2_1730defaulta.csv), Data_CAL PPRI, INPE 2030 (tools/build/build_eu_market_supply_nq.py)';
INSERT INTO value_units VALUES
  ('eu_market_supply_nq', 'h', 'U_1000tPerEuPerTonOverINPE', 'capri', 'CAPRI''s p_hessNQSupp (ProdNQ_, arm/market_model.gms l. 1529-1572: quantity in 1000 t, prices over INPE)'),
  ('eu_market_supply_nq', 'ppri_y', 'U_EuPerTon', 'capri', 'CAPRI''s PPRI (CAPRIunits: U_EuPerTon)'),
  ('eu_market_supply_nq', 'inpe', 'U_1unit', 'builder', 'the price index of the non-agricultural good, 1.019^13 in 2030'),
  ('eu_market_supply_nq', 'h_ratio', 'U_1000tPerPriceRatio', 'builder', 'h x ppri_y / inpe');

-- file: capri_data/2017/market/noneu_market_supply_nq.csv
CREATE TABLE noneu_market_supply_nq (
    trade_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    rms VARCHAR NOT NULL REFERENCES rms_to_rm (rms),
    x VARCHAR NOT NULL,                                   -- the model's commodity, or MILK (raw milk)
    y VARCHAR,                                            -- empty: a column without a model price, held
    capri_x VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    capri_y VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    h DOUBLE NOT NULL,
    ppri_y DOUBLE NOT NULL CHECK (ppri_y >= 0),           -- 0: no CAPRI price (FEDE)
    inpe DOUBLE NOT NULL CHECK (inpe > 0),
    h_ratio DOUBLE NOT NULL,
    PRIMARY KEY (rms, capri_x, capri_y),
    CHECK ((ppri_y > 0) OR (h_ratio = 0 AND y IS NULL))
);
COMMENT ON TABLE noneu_market_supply_nq IS 'CAPRI''s market supply functions of the non-EU market regions (ProdNQ_): p_hessNQSupp at CAL completed as arm/market1.gms, Data_CAL PPRI, INPE 2030 (tools/build/build_noneu_market_supply_nq.py; K54-3)';
INSERT INTO value_units VALUES
  ('noneu_market_supply_nq', 'h', 'U_1000tPerEuPerTonOverINPE', 'capri', 'CAPRI''s p_hessNQSupp (ProdNQ_, arm/market_model.gms l. 1529-1572: quantity in 1000 t, prices over INPE)'),
  ('noneu_market_supply_nq', 'ppri_y', 'U_EuPerTon', 'capri', 'CAPRI''s PPRI (CAPRIunits: U_EuPerTon)'),
  ('noneu_market_supply_nq', 'inpe', 'U_1unit', 'builder', 'the price index of the non-agricultural good, 1.019^13 in 2030'),
  ('noneu_market_supply_nq', 'h_ratio', 'U_1000tPerPriceRatio', 'builder', 'h x ppri_y / inpe');

-- rule: the market supply functions' model codes are market commodities (raw milk included), mapped from CAPRI's; a
-- column may also be FEDE, the region's feed energy price (CAPRI's FeedBal_, audit M3; its regions: 22_market_feed_energy.sql)
SELECT DISTINCT 'noneu x' AS what, x AS code FROM noneu_market_supply_nq
WHERE x NOT IN (SELECT code FROM model_commodities)
UNION ALL
SELECT DISTINCT 'noneu y', y FROM noneu_market_supply_nq
WHERE y IS NOT NULL AND y NOT IN (SELECT code FROM model_commodities) AND y <> 'FEDE'
UNION ALL
SELECT DISTINCT 'noneu x/capri_x', x || '/' || capri_x FROM noneu_market_supply_nq n
WHERE NOT EXISTS (SELECT 1 FROM model_commodities m WHERE m.code = n.x AND m.capri_code = n.capri_x);

-- rule: each behavioural region's trade region is its market region's
SELECT n.rms, n.trade_region, r.rm FROM (SELECT DISTINCT rms, trade_region FROM noneu_market_supply_nq) n
JOIN rms_to_rm r USING (rms)
LEFT JOIN model_trade_regions t ON t.capri_rm = r.rm
WHERE coalesce(t.code, 'ROW') <> n.trade_region;

-- rule: CAPRI's Hessian is symmetric in prices once completed (h_xy = h_yx: arm/market1.gms l. 574)
SELECT a.rms, a.capri_x, a.capri_y, a.h, b.h FROM noneu_market_supply_nq a
JOIN noneu_market_supply_nq b ON a.rms = b.rms AND a.capri_x = b.capri_y AND a.capri_y = b.capri_x
WHERE a.h <> b.h
UNION ALL
SELECT a.ms, a.x, a.y, a.h, b.h FROM eu_market_supply_nq a
JOIN eu_market_supply_nq b ON a.ms = b.ms AND a.x = b.y AND a.y = b.x
WHERE a.h <> b.h;

-- rule: every column of the long tables declared here has its unit, every unit is in the catalogue
SELECT t.tbl, t.item FROM (VALUES ('eu_market_supply_nq', 'h'), ('eu_market_supply_nq', 'ppri_y'),
    ('eu_market_supply_nq', 'inpe'), ('eu_market_supply_nq', 'h_ratio'), ('noneu_market_supply_nq', 'h'),
    ('noneu_market_supply_nq', 'ppri_y'), ('noneu_market_supply_nq', 'inpe'), ('noneu_market_supply_nq', 'h_ratio'))
    t(tbl, item)
WHERE NOT EXISTS (SELECT 1 FROM value_units v WHERE v.tbl = t.tbl AND v.item = t.item AND v.unit IN (SELECT code FROM units));

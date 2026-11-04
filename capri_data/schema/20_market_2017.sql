-- The market's supply functions outside the supply models (CAPRI's ProdNQ_) and the region maps they are summed over.
-- Long files: the unit of each numeric column is in value_units with the column's name as the item.

-- file: capri_data/codes/model_trade_regions.csv
CREATE TABLE model_trade_regions (
    code VARCHAR PRIMARY KEY,
    capri_rm VARCHAR REFERENCES capri_rall (code),     -- empty: ROW, the CAPRI regions mapped to no other
    mapping_source VARCHAR NOT NULL                    -- the source of the row
);
COMMENT ON TABLE model_trade_regions IS 'the bilateral market''s trade regions in their order and the CAPRI region each stands for (market region or trade block of CAPRI''s market data); no builder: a declared code list, read by capri_mod/data/definitions.py (ALL_TRADE_REGIONS, TRADE_REGION_OF_CAPRI) and tools/build/recalibrate_trade_2017.py (REGION_MAP)';

-- file: capri_data/codes/model_market_regions.csv
CREATE TABLE model_market_regions (
    rm VARCHAR PRIMARY KEY REFERENCES capri_rm (code),
    model_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    source VARCHAR NOT NULL                            -- why the market region is in that model region
);
COMMENT ON TABLE model_market_regions IS 'the market''s grouping step: each of CAPRI''s 45 market regions (RM) and the model''s market region it belongs to (26 their own, A_EU_WEST and A_EU_EAST the model''s EU27, 17 its ROW); no builder: declared, read by tools/lib/_market_regions.py for every builder of the market''s data (MARKET_REGIONS_INVENTORY.md stage 1; stages 2-3 change only this table)';

-- rule: every one of CAPRI's market regions has its model region
SELECT code FROM capri_rm WHERE code NOT IN (SELECT rm FROM model_market_regions);

-- file: capri_data/shared/rms_to_rm.csv
CREATE TABLE rms_to_rm (
    rms VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    rm VARCHAR NOT NULL REFERENCES capri_rall (code)
);
COMMENT ON TABLE rms_to_rm IS 'CAPRI''s behavioural regions (RMS) and the market region (RM) of each (gams/aggregation/defaultA.agg, rms_to_rm; tools/build/build_gl_demand.py)';

-- file: capri_data/2017/market/eu_market_supply_nq.csv
CREATE TABLE eu_market_supply_nq (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    x VARCHAR NOT NULL REFERENCES model_commodities (code),   -- the product, the model's code
    y VARCHAR,                                                -- the price's product, the model's code; empty: held
    capri_x VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    capri_y VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    h DOUBLE NOT NULL,
    ppri_y DOUBLE NOT NULL CHECK (ppri_y >= 0),
    inpe DOUBLE NOT NULL CHECK (inpe > 0),
    h_ratio DOUBLE NOT NULL,
    PRIMARY KEY (ms, capri_x, capri_y),
    CHECK ((ppri_y > 0) OR (h_ratio = 0 AND y IS NULL))
);
COMMENT ON TABLE eu_market_supply_nq IS 'CAPRI''s market supply functions of the EU member states, every product (ProdNQ_): p_hessNQSupp at CAL completed as arm/market1.gms (elas_2_1730defaulta.csv), Data_CAL PPRI, INPE 2030 (tools/build/build_eu_market_supply_nq.py)';
INSERT INTO value_units VALUES
  ('eu_market_supply_nq', 'h', 'U_1000tPerEuPerTonOverINPE', 'capri', 'CAPRI''s p_hessNQSupp (ProdNQ_, arm/market_model.gms l. 1529-1572: quantity in 1000 t, prices over INPE)'),
  ('eu_market_supply_nq', 'ppri_y', 'U_EuPerTon', 'capri', 'CAPRI''s PPRI (CAPRIunits: U_EuPerTon)'),
  ('eu_market_supply_nq', 'inpe', 'U_1unit', 'builder', 'the price index of the non-agricultural good, 1.019^13 in 2030'),
  ('eu_market_supply_nq', 'h_ratio', 'U_1000tPerPriceRatio', 'builder', 'h x ppri_y / inpe');

-- file: capri_data/2017/market/eu_market_supply_base.csv
CREATE TABLE eu_market_supply_base (
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    x VARCHAR NOT NULL REFERENCES model_commodities (code),
    capri_x VARCHAR NOT NULL REFERENCES capri_xx1 (code),
    prod_cal DOUBLE NOT NULL CHECK (prod_cal <> 0),   -- CAPRI writes -1e-08 for a product it keeps at practically none
    PRIMARY KEY (ms, capri_x)
);
COMMENT ON TABLE eu_market_supply_base IS 'the EU member states'' production at CAPRI''s calibration point, the quantity of their ProdNQ_ (Data_CAL PROD at CAL, data_market_1730defaulta.csv; tools/build/build_eu_market_supply_nq.py)';
INSERT INTO value_units VALUES
  ('eu_market_supply_base', 'prod_cal', 'U_1000t', 'capri', 'CAPRI''s PROD (1000 t)');

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
COMMENT ON TABLE noneu_market_supply_nq IS 'CAPRI''s market supply functions of the non-EU market regions (ProdNQ_): p_hessNQSupp at CAL completed as arm/market1.gms, the land demand rows (x TCRP, FODFAL, FRUN) with their sign turned as arm/market1.gms l. 593, Data_CAL PPRI, INPE 2030 (tools/build/build_noneu_market_supply_nq.py; K54-3; the land market, PORTS_STAGE4.md stage 7)';
INSERT INTO value_units VALUES
  ('noneu_market_supply_nq', 'h', 'U_1000tPerEuPerTonOverINPE', 'capri', 'CAPRI''s p_hessNQSupp (ProdNQ_, arm/market_model.gms l. 1529-1572: quantity in 1000 t, prices over INPE)'),
  ('noneu_market_supply_nq', 'ppri_y', 'U_EuPerTon', 'capri', 'CAPRI''s PPRI (CAPRIunits: U_EuPerTon)'),
  ('noneu_market_supply_nq', 'inpe', 'U_1unit', 'builder', 'the price index of the non-agricultural good, 1.019^13 in 2030'),
  ('noneu_market_supply_nq', 'h_ratio', 'U_1000tPerPriceRatio', 'builder', 'h x ppri_y / inpe');

-- rule: the market supply functions' model codes are market commodities (raw milk included), mapped from CAPRI's, or
-- CAPRI's market land types TCRP, FODFAL, FRUN under their own codes (the land market, noneu_land_market.csv); a
-- column may also be FEDE, the region's feed energy price (CAPRI's FeedBal_, audit M3; its regions: 22_market_feed_energy.sql)
SELECT DISTINCT 'noneu x' AS what, x AS code FROM noneu_market_supply_nq
WHERE x NOT IN (SELECT code FROM model_commodities) AND x NOT IN ('TCRP', 'FODFAL', 'FRUN')
UNION ALL
SELECT DISTINCT 'noneu y', y FROM noneu_market_supply_nq
WHERE y IS NOT NULL AND y NOT IN (SELECT code FROM model_commodities) AND y NOT IN ('FEDE', 'TCRP', 'FODFAL', 'FRUN')
UNION ALL
SELECT DISTINCT 'noneu x/capri_x', x || '/' || capri_x FROM noneu_market_supply_nq n
WHERE NOT EXISTS (SELECT 1 FROM model_commodities m WHERE m.code = n.x AND m.capri_code = n.capri_x)
  AND NOT (n.x IN ('TCRP', 'FODFAL', 'FRUN') AND n.x = n.capri_x);

-- file: capri_data/2017/market/noneu_land_market.csv
CREATE TABLE noneu_land_market (
    trade_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    rms VARCHAR NOT NULL REFERENCES rms_to_rm (rms),
    lu VARCHAR NOT NULL CHECK (lu IN ('FORE', 'ARTIF', 'OLND', 'TCRP', 'FODFAL', 'FRUN')),
    land_kha DOUBLE NOT NULL CHECK (land_kha >= 0),
    rent DOUBLE NOT NULL,
    alu DOUBLE NOT NULL,
    endogenous INTEGER NOT NULL CHECK (endogenous IN (0, 1)),   -- 1: the rent clears the land market
    avail_kha DOUBLE NOT NULL CHECK (avail_kha > 0),
    PRIMARY KEY (rms, lu)
);
COMMENT ON TABLE noneu_land_market IS 'CAPRI''s market land block per non-EU market region without supply models (LandSupplyMNL_, LndSupplyEqualsDemand_, rentFromProdpriceLand_, arm/market_model.gms l. 1696-1790): land, rent, MNL constant p_aLU CUR and ARTO - INLW per land type, from sim_ini_21730 (tools/build/build_noneu_market_supply_nq.py build_land_market; PORTS_STAGE4.md stage 7)';
INSERT INTO value_units VALUES
  ('noneu_land_market', 'land_kha', 'U_1000ha', 'capri', 'CAPRI v_land (1000 ha)'),
  ('noneu_land_market', 'rent', 'U_EuPerHa', 'capri', 'CAPRI v_rentPerHa'),
  ('noneu_land_market', 'alu', 'U_ratio', 'capri', 'CAPRI p_aLU CUR, the constant of the MNL exponent (dimensionless)'),
  ('noneu_land_market', 'endogenous', 'U_1unit', 'builder', 'a flag: 1 where the rent is free (v_rentPerHa bounds), 0 fixed'),
  ('noneu_land_market', 'avail_kha', 'U_1000ha', 'capri', 'CAPRI DATA ARTO - INLW LEVL CUR (1000 ha)');

-- file: capri_data/2017/market/noneu_land_mnl.csv
CREATE TABLE noneu_land_mnl (
    rms VARCHAR NOT NULL REFERENCES rms_to_rm (rms),
    lu VARCHAR NOT NULL,
    lu1 VARCHAR NOT NULL,
    b DOUBLE NOT NULL,
    PRIMARY KEY (rms, lu, lu1)
);
COMMENT ON TABLE noneu_land_mnl IS 'CAPRI''s MNL land supply coefficients p_bLu CUR per non-EU market region (the exponent of land type lu in the rent of lu1), from sim_ini_21730 (tools/build/build_noneu_market_supply_nq.py build_land_market)';
INSERT INTO value_units VALUES
  ('noneu_land_mnl', 'b', 'U_ratio', 'capri', 'CAPRI p_bLu CUR, per EUR/ha of rent (the exponent is dimensionless)');

-- rule: each land market region's land types are in its MNL coefficients
SELECT DISTINCT m.rms, m.lu FROM noneu_land_mnl m
WHERE NOT EXISTS (SELECT 1 FROM noneu_land_market l WHERE l.rms = m.rms AND l.lu = m.lu)
   OR NOT EXISTS (SELECT 1 FROM noneu_land_market l WHERE l.rms = m.rms AND l.lu = m.lu1);

-- rule: each behavioural region's trade region is its market region's
SELECT n.rms, n.trade_region, r.rm FROM (SELECT DISTINCT rms, trade_region FROM noneu_market_supply_nq) n
JOIN rms_to_rm r USING (rms)
LEFT JOIN model_trade_regions t ON t.capri_rm = r.rm
WHERE coalesce(t.code, 'ROW') <> n.trade_region;

-- rule: CAPRI's Hessian is symmetric in prices once completed (h_xy = h_yx: arm/market1.gms l. 574), before the land
-- rows' sign is turned (l. 593): a term between a product and a land type is minus its transpose
SELECT a.rms, a.capri_x, a.capri_y, a.h, b.h FROM noneu_market_supply_nq a
JOIN noneu_market_supply_nq b ON a.rms = b.rms AND a.capri_x = b.capri_y AND a.capri_y = b.capri_x
WHERE CASE WHEN (a.capri_x IN ('TCRP', 'FODFAL', 'FRUN')) <> (a.capri_y IN ('TCRP', 'FODFAL', 'FRUN'))
           THEN a.h <> -b.h ELSE a.h <> b.h END
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

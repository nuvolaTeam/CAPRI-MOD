-- The non-EU feed demand functions and feed energy balance (audit M3), the EU's cake feed weights and EU supply
-- elasticities. Long files: the unit of each numeric column is in value_units (99_rules.sql).

-- file: capri_data/2017/market/feed_cal_content.csv
CREATE TABLE feed_cal_content (
    product VARCHAR PRIMARY KEY REFERENCES capri_xx (code),
    kcal_per_kg DOUBLE NOT NULL CHECK (kcal_per_kg > 0)
);
COMMENT ON TABLE feed_cal_content IS 'CAPRI''s calorie content per market product, p_calContent = p_nutrientCont(x, Energ_cal) of dat/arm/nutrient_cont_usda.gdx (arm/market_model.gms l. 300-313; tools/build/build_feed_energy.py)';
INSERT INTO value_units VALUES ('feed_cal_content', 'kcal_per_kg', 'U_kcalPerKg', 'capri', 'USDA Energ_cal per kg, CAPRI''s p_calContent');

-- file: capri_data/2017/market/noneu_feed_energy.csv
CREATE TABLE noneu_feed_energy (
    rms VARCHAR PRIMARY KEY REFERENCES rms_to_rm (rms),
    rm VARCHAR NOT NULL REFERENCES capri_rall (code),
    fede_kcal DOUBLE NOT NULL CHECK (fede_kcal > 0),
    fede_price DOUBLE NOT NULL CHECK (fede_price > 0),
    ave_feed_cost DOUBLE NOT NULL CHECK (ave_feed_cost > 0),
    feed_cost_share DOUBLE NOT NULL CHECK (feed_cost_share >= 0.7),
    solves INTEGER NOT NULL CHECK (solves BETWEEN 1 AND 100)
);
COMMENT ON TABLE noneu_feed_energy IS 'the feed energy balance of CAPRI''s non-EU behavioural regions without supply models at the 2030 calibration: FEDE quantity and price (arm/market1.gms l. 402-408), average feed cost and the feed-cost share of the fit (arm/feed_conv.gms; tools/build/build_feed_energy.py)';
INSERT INTO value_units VALUES
  ('noneu_feed_energy', 'fede_kcal', 'U_MioKcal', 'capri', 'sum of CAPRI''s FEED (1000 t) x p_calContent (kcal/kg)'),
  ('noneu_feed_energy', 'fede_price', 'U_EuPer1000Kcal', 'capri', 'sum FEED x ARM1P (EUR/t) over fede_kcal'),
  ('noneu_feed_energy', 'ave_feed_cost', 'U_EuPer1000Kcal', 'capri', 'p_aveFeedCost: sum FEED x (ARM1P - FSEi) over fede_kcal'),
  ('noneu_feed_energy', 'feed_cost_share', 'U_ratio', 'capri', 'p_feedCostShare, 0.7 raised by 0.1 per infeasible solve'),
  ('noneu_feed_energy', 'solves', 'U_1unit', 'builder', 'the number of solves of the fit (a count)');

-- file: capri_data/2017/market/noneu_feed_conv.csv
CREATE TABLE noneu_feed_conv (
    rms VARCHAR NOT NULL REFERENCES noneu_feed_energy (rms),
    product VARCHAR NOT NULL CHECK (product IN ('BEEF', 'PORK', 'SGMT', 'POUM', 'EGGS', 'MILK')),
    prod_kt DOUBLE NOT NULL CHECK (prod_kt > 0),
    conv DOUBLE NOT NULL CHECK (conv > 0),
    feed_conv DOUBLE NOT NULL CHECK (feed_conv > 0),
    expected DOUBLE NOT NULL CHECK (expected > 0),
    upper DOUBLE NOT NULL,
    binding INTEGER NOT NULL CHECK (binding IN (0, 1)),
    PRIMARY KEY (rms, product),
    CHECK (conv <= upper * (1 + 1e-12) AND conv >= 0.001 * expected * (1 - 1e-12) AND conv <= 20 * expected * (1 + 1e-12))
);
COMMENT ON TABLE noneu_feed_conv IS 'CAPRI''s feed conversion factors pv_feedConv per region and animal product (XX_ANIM_FEED), fitted as arm/feed_conv.gms m_fitFeedConv at the 2030 calibration data (tools/build/build_feed_energy.py)';
INSERT INTO value_units VALUES
  ('noneu_feed_conv', 'prod_kt', 'U_1000t', 'capri', 'CAPRI''s PROD at CAL'),
  ('noneu_feed_conv', 'conv', 'U_ratio', 'capri', 'the fitted pv_feedConv: feed energy per energy of the product (maize-equivalent rate x calorie ratio)'),
  ('noneu_feed_conv', 'feed_conv', 'U_kcalPerKg', 'capri', 'conv x p_calContent of the product: kcal fed per kg of product, the value FeedBal_ uses'),
  ('noneu_feed_conv', 'expected', 'U_ratio', 'capri', 'p_expMeanFeedConv'),
  ('noneu_feed_conv', 'upper', 'U_ratio', 'builder', 'the smaller of 20 x expected and FeedCost_''s bound'),
  ('noneu_feed_conv', 'binding', 'U_1unit', 'builder', '1 where FeedCost_ binds (a flag)');

-- file: capri_data/2017/market/noneu_feed_base.csv
CREATE TABLE noneu_feed_base (
    trade_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    rms VARCHAR NOT NULL REFERENCES noneu_feed_energy (rms),
    capri_x VARCHAR NOT NULL REFERENCES capri_xx (code),
    x VARCHAR,                                            -- the model commodity; empty: none
    feed_kt DOUBLE NOT NULL CHECK (feed_kt > 0),
    kcal_per_kg DOUBLE NOT NULL CHECK (kcal_per_kg >= 0),   -- 0: no calorie content (p_noCal: FPRI, DDGS)
    PRIMARY KEY (rms, capri_x)
);
COMMENT ON TABLE noneu_feed_base IS 'the same regions'' feed per CAPRI product at CAL (Data_CAL FEED of data_market_1730defaulta) with its calories (tools/build/build_noneu_feed_nq.py)';
INSERT INTO value_units VALUES
  ('noneu_feed_base', 'feed_kt', 'U_1000t', 'capri', 'CAPRI''s FEED at CAL'),
  ('noneu_feed_base', 'kcal_per_kg', 'U_kcalPerKg', 'capri', 'p_calContent');

-- file: capri_data/2017/market/noneu_feed_totals.csv
CREATE TABLE noneu_feed_totals (
    trade_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    x VARCHAR NOT NULL REFERENCES model_commodities (code),
    feed_kt DOUBLE NOT NULL CHECK (feed_kt > 0),
    PRIMARY KEY (trade_region, x)
);
COMMENT ON TABLE noneu_feed_totals IS 'CAPRI''s feed at CAL of every non-EU behavioural region of a trade region per model commodity, the regions with supply models included (tools/build/build_noneu_feed_nq.py)';
INSERT INTO value_units VALUES ('noneu_feed_totals', 'feed_kt', 'U_1000t', 'capri', 'sum of CAPRI''s FEED at CAL');

-- file: capri_data/2017/market/noneu_feed_nq.csv
CREATE TABLE noneu_feed_nq (
    trade_region VARCHAR NOT NULL REFERENCES model_trade_regions (code),
    rms VARCHAR NOT NULL REFERENCES noneu_feed_energy (rms),
    x VARCHAR,                                            -- the model commodity fed; empty: none
    y VARCHAR NOT NULL,                                   -- a model commodity's price or FEDE
    capri_x VARCHAR NOT NULL REFERENCES capri_xx (code),
    capri_y VARCHAR NOT NULL,
    h DOUBLE NOT NULL,
    p0_y DOUBLE NOT NULL CHECK (p0_y > 0),
    inpe DOUBLE NOT NULL CHECK (inpe > 0),
    h_ratio DOUBLE NOT NULL,
    PRIMARY KEY (rms, capri_x, capri_y),
    CHECK ((y = 'FEDE') = (capri_y = 'FEDE'))
);
COMMENT ON TABLE noneu_feed_nq IS 'CAPRI''s feed functions FeedNQ_ (p_hessNQFeed at CAL completed as arm/market1.gms l. 553-575) of the non-EU regions of FeedBal_, in the ratio form h x p0_y / INPE (tools/build/build_noneu_feed_nq.py, audit M3)';
INSERT INTO value_units VALUES
  ('noneu_feed_nq', 'h', NULL, 'open', 'CAPRI''s p_hessNQFeed: 1000 t per EUR/t over INPE for the product prices, per EUR per 1000 kcal over INPE for FEDE; two units in one column'),
  ('noneu_feed_nq', 'p0_y', NULL, 'open', 'ARM1P of the market region (U_EuPerTon) or the FEDE price (U_EuPer1000Kcal); two units in one column'),
  ('noneu_feed_nq', 'inpe', 'U_1unit', 'builder', '1.019^13, the market''s price index of the non-agricultural good in 2030'),
  ('noneu_feed_nq', 'h_ratio', 'U_1000tPerPriceRatio', 'builder', 'h x p0_y / inpe');

-- file: capri_data/2017/market/eu_cake_feed_bas.csv
CREATE TABLE eu_cake_feed_bas (
    product VARCHAR PRIMARY KEY CHECK (product IN ('RAPC', 'SUNC', 'SOYC')),
    feed_kt DOUBLE NOT NULL CHECK (feed_kt > 0)
);
COMMENT ON TABLE eu_cake_feed_bas IS 'the EU''s base-period feed use of the oilseed cakes, CAPRI''s FAO_agg p_dataMarket FEDM BAS summed over the member states: the weights of the supply models'' cake index (tools/build/build_eu_cake_feed.py)';
INSERT INTO value_units VALUES ('eu_cake_feed_bas', 'feed_kt', 'U_1000t', 'capri', 'FAO_agg FEDM (t) / 1000');

-- file: capri_data/2017/market/supply_elas_eu.csv
CREATE TABLE supply_elas_eu (
    commodity VARCHAR PRIMARY KEY REFERENCES model_commodities (code),
    capri_code VARCHAR NOT NULL REFERENCES capri_xx (code),
    elasticity DOUBLE NOT NULL CHECK (elasticity > 0),
    member_states INTEGER NOT NULL CHECK (member_states BETWEEN 1 AND 26)
);
COMMENT ON TABLE supply_elas_eu IS 'the EU rows'' own-price supply elasticity: median of CAPRI''s p_elasSupp (elas1717 CAL) over the model''s EU member states per market commodity (tools/build/build_capri_supply_elas_market.py)';
INSERT INTO value_units VALUES
  ('supply_elas_eu', 'elasticity', 'U_Elasticity', 'capri', 'CAPRI''s p_elasSupp, own-price, median'),
  ('supply_elas_eu', 'member_states', 'U_1unit', 'builder', 'how many member states have it (a count)');

-- rule: FedeBal_ holds at the calibration point (energy of the feed = output x feed conversion) in every region
SELECT e.rms, e.fede_kcal, b.fed, c.need FROM noneu_feed_energy e
JOIN (SELECT rms, sum(feed_kt * kcal_per_kg) AS fed FROM noneu_feed_base GROUP BY rms) b ON b.rms = e.rms
JOIN (SELECT rms, sum(prod_kt * feed_conv) AS need FROM noneu_feed_conv GROUP BY rms) c ON c.rms = e.rms
WHERE abs(b.fed - e.fede_kcal) > 1e-9 * e.fede_kcal OR abs(c.need - e.fede_kcal) > 1e-9 * e.fede_kcal;

-- rule: a feed conversion factor's energy per kg is the factor times the product's calories
SELECT c.rms, c.product FROM noneu_feed_conv c JOIN feed_cal_content k ON k.product = c.product
WHERE abs(c.feed_conv - c.conv * k.kcal_per_kg) > 1e-9 * c.feed_conv;

-- rule: the feed functions' terms are those of products the region feeds, and their trade region is the region's
SELECT DISTINCT n.rms, n.capri_x FROM noneu_feed_nq n
LEFT JOIN noneu_feed_base b ON b.rms = n.rms AND b.capri_x = n.capri_x
WHERE b.rms IS NULL OR b.trade_region <> n.trade_region;

-- rule: the market supply functions' FEDE column belongs to the regions of FeedBal_
SELECT DISTINCT rms FROM noneu_market_supply_nq WHERE y = 'FEDE' AND rms NOT IN (SELECT rms FROM noneu_feed_energy);

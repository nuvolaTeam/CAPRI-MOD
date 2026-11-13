-- Inputs of CAPTRD's biofuel trends (biofuel/biofuel_trends.gms, included by captrd/expert_support.gms l. 108;
-- capri_mod/pipeline/captrd/biofuel_trends.py): CAPRI's global sets the file uses (tools/build/build_captrd_sets.py),
-- the file's own sets and PRIMES's, the fossil fuels' and the excise taxes' data (tools/build/build_captrd_biofuel.py).

-- file: capri_data/pipeline/captrd/sets/cere.csv
CREATE TABLE ctrd_cere (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_cere IS 'CAPRI''s global set CERE (cereals according to the Grandes Cultures definition; gams/sets.gms l. 2146): one member per row in d0, 7 members (e.g. SWHE, DWHE, RYEM); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the biofuel trends.';

-- file: capri_data/pipeline/captrd/sets/biostockoilp.csv
CREATE TABLE ctrd_biostockoilp (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_biostockoilp IS 'CAPRI''s global set bioStockOilP (the oil feedstocks of biofuels; gams/sets.gms l. 5161): one member per row in d0, 5 members (e.g. RAPO, SUNO, SOYO); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the biofuel trends.';

-- file: capri_data/pipeline/captrd/sets/bio_by.csv
CREATE TABLE ctrd_bio_by (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_by IS 'CAPRI''s global set BIO_BY (by-products of biofuel production; gams/sets.gms l. 5167): one member per row in d0, 2 members (e.g. DDGS, GLYC); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the biofuel trends.';

-- file: capri_data/pipeline/captrd/sets/oseco.csv
CREATE TABLE ctrd_oseco (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_oseco IS 'CAPRI''s global set OSECO (outputs and secondary products; gams/sets.gms l. 5080-5081): one member per row in d0, 92 members (e.g. SWHE, DWHE, RYEM); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the biofuel trends.';

-- file: capri_data/pipeline/captrd/sets/balpos.csv
CREATE TABLE ctrd_balpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_balpos IS 'CAPRI''s global set BALPOS (positions of the farm and market balance; gams/sets.gms l. 3155): one member per row in d0, 22 members (e.g. GROF, SEDF, LOSF); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py, for the biofuel trends.';

-- file: capri_data/pipeline/captrd/sets/biofuel/agfuels.csv
CREATE TABLE ctrd_bio_agfuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_agfuels IS 'The set agFuels of biofuel/biofuel_trends.gms (Aglink''s fuel codes; l. 211-212), as written: one member per row, 4 (e.g. GAS, DIE, ET); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/allfermentastocks.csv
CREATE TABLE ctrd_bio_allfermentastocks (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_allfermentastocks IS 'The set allFermentaStocks of biofuel/biofuel_trends.gms (feedstocks of ethanol by fermentation; l. 187-188), as written: one member per row, 3 (e.g. LIGN, cere, suga); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/allunit.csv
CREATE TABLE ctrd_bio_allunit (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_allunit IS 'The set AllUnit of biofuel/biofuel_trends.gms (the units of PRIMES''s results; l. 81-93), as written: one member per row, 8 (e.g. GWh, ktoe, 1000); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/aux_to_pcols.csv
CREATE TABLE ctrd_bio_aux_to_pcols (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_bio_aux_to_pcols IS 'The set aux_to_pCols of biofuel/biofuel_trends.gms (PRIMES''s columns to the aggregated columns; l. 191-197), as written: one member per row, 8 (e.g. SUGB.SUGB, CERE.CERE, LIGN.LIGN); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/aux_to_prows.csv
CREATE TABLE ctrd_bio_aux_to_prows (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_bio_aux_to_prows IS 'The set aux_to_pRows of biofuel/biofuel_trends.gms (PRIMES''s rows to the aggregated rows; l. 198-207), as written: one member per row, 5 (e.g. NonFungi.BIOD, Fungible.BIOD, Bioethan.BIOE); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/auxcols.csv
CREATE TABLE ctrd_bio_auxcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_auxcols IS 'The set auxCols of biofuel/biofuel_trends.gms (PRIMES''s result columns; l. 96-128), as written: one member per row, 21 (e.g. BIOF, IMPT, MAPR); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/auxrows.csv
CREATE TABLE ctrd_bio_auxrows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_auxrows IS 'The set auxRows of biofuel/biofuel_trends.gms (PRIMES''s result rows; l. 129-176), as written: one member per row, 27 (e.g. CERE, OILS, SUGA); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/fstgfermentastocks.csv
CREATE TABLE ctrd_bio_fstgfermentastocks (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_fstgfermentastocks IS 'The set FstGFermentaStocks of biofuel/biofuel_trends.gms (first-generation feedstocks of ethanol by fermentation; l. 189-190), as written: one member per row, 2 (e.g. cere, suga); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/fuelmap.csv
CREATE TABLE ctrd_bio_fuelmap (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_bio_fuelmap IS 'The set fuelMap of biofuel/biofuel_trends.gms (CAPRI''s fuels to Aglink''s; l. 215-219), as written: one member per row, 4 (e.g. GASL.GAS, DISL.DIE, BIOE.ET); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/fuelmatch.csv
CREATE TABLE ctrd_bio_fuelmatch (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_bio_fuelmatch IS 'The set fuelMatch of biofuel/biofuel_trends.gms (biofuels to their fossil substitute; l. 213-214), as written: one member per row, 4 (e.g. BIOE.GASL, BIOD.DISL, GASL.GASL); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/pcols.csv
CREATE TABLE ctrd_bio_pcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_pcols IS 'The set pCols of biofuel/biofuel_trends.gms (the aggregated PRIMES columns; l. 180-183), as written: one member per row, 14 (e.g. CERE, SUGB, bioeShare); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/prows.csv
CREATE TABLE ctrd_bio_prows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_prows IS 'The set pRows of biofuel/biofuel_trends.gms (the aggregated PRIMES rows; l. 184-185), as written: one member per row, 11 (e.g. LIGN, cere, suga); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/pyears.csv
CREATE TABLE ctrd_bio_pyears (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_pyears IS 'The set pYears of biofuel/biofuel_trends.gms (the years with PRIMES''s results; l. 208-209), as written: one member per row, 15 (e.g. 2000, 2005, 2010); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/scalecols.csv
CREATE TABLE ctrd_bio_scalecols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_scalecols IS 'The set scaleCols of biofuel/biofuel_trends.gms (the columns converted from ktoe to 1000 t; l. 456-457, transcribed by the builder), as written: one member per row, 6 (e.g. secG, mapr, domm); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/sets/biofuel/primesms_extra.csv
CREATE TABLE ctrd_bio_primesms_extra (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_bio_primesms_extra IS 'The set primesMs of biofuel/biofuel_trends.gms (the labels primesMs adds to CAPRI''s MSALL; l. 201-202, transcribed by the builder), as written: one member per row, 2 (e.g. BE000000, LU000000); read by tools/build/build_captrd_biofuel.py (tools/lib/gams_sets.py).';

-- file: capri_data/pipeline/captrd/dat/biofuel_p_potentialstocks.csv
CREATE TABLE ctrd_biofuel_p_potentialstocks (
    region VARCHAR NOT NULL,
    stock VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, stock)
);
COMMENT ON TABLE ctrd_biofuel_p_potentialstocks IS 'CAPRI''s table p_potentialStocks(region, stock) of biofuel/biofuel_trends.gms l. 1019-1050: the minimum share of each feedstock in a country''s biofuel production; 310 rows (tools/build/build_captrd_biofuel.py).';
INSERT INTO value_units VALUES
  ('ctrd_biofuel_p_potentialstocks', 'value', 'U_ratio', 'capri', 'biofuel_trends.gms: shares');

-- file: capri_data/pipeline/captrd/dat/biofuel_proc_yields.csv
CREATE TABLE ctrd_biofuel_proc_yields (
    "row" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY ("row")
);
COMMENT ON TABLE ctrd_biofuel_proc_yields IS 'CAPTRD''s parameter Proc_Yields(rows) (gams/captrd.gms l. 356-363): processing yields of oil seeds (oil and cake per ton of seed); the biofuel trends use RAPO''s; 6 rows (tools/build/build_captrd_biofuel.py).';
INSERT INTO value_units VALUES
  ('ctrd_biofuel_proc_yields', 'value', 'U_ratio', 'capri', 'captrd.gms: t per t of seed');

-- file: capri_data/pipeline/captrd/dat/biofuel_p_primeswithunits.csv
CREATE TABLE ctrd_biofuel_p_primeswithunits (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "row" VARCHAR NOT NULL,
    unit VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, "row", unit, "year")
);
COMMENT ON TABLE ctrd_biofuel_p_primeswithunits IS 'PRIMES''s biofuel results p_PrimesWithUnits(region, column, row, unit, year) of dat/biofuel/primes_ref_060722.gdx (the reference run''s %primesBiofuelFile%), as the GDX holds them, the unit in its own column; 28993 rows (tools/build/build_captrd_biofuel.py).';
INSERT INTO value_units VALUES
  ('ctrd_biofuel_p_primeswithunits', 'value', NULL, 'open', 'biofuel_p_primeswithunits.value: by row (the unit column or the item: ktoe for quantities, EUR/toe for prices)');

-- file: capri_data/pipeline/captrd/dat/biofuel_p_fossilfuel.csv
CREATE TABLE ctrd_biofuel_p_fossilfuel (
    region VARCHAR NOT NULL,
    col VARCHAR NOT NULL,
    "row" VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, col, "row", "year")
);
COMMENT ON TABLE ctrd_biofuel_p_fossilfuel IS 'PRIMES''s fossil fuel demand (DOMM) and prices (UVAP) p_fossilFuel(region, item, fuel, year) of dat/biofuel/fossilFuel.gdx, used where p_PrimesWithUnits lacks them; 1232 rows (tools/build/build_captrd_biofuel.py).';
INSERT INTO value_units VALUES
  ('ctrd_biofuel_p_fossilfuel', 'value', NULL, 'open', 'biofuel_p_fossilfuel.value: by row (the unit column or the item: ktoe for quantities, EUR/toe for prices)');

-- file: capri_data/pipeline/captrd/dat/biofuel_p_taxdata.csv
CREATE TABLE ctrd_biofuel_p_taxdata (
    region VARCHAR NOT NULL,
    fuel VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, fuel, item, "year")
);
COMMENT ON TABLE ctrd_biofuel_p_taxdata IS 'The excise taxes p_taxData(region, fuel, CTAX, year) of dat/biofuel/Biofuel_data.gms (EURACTIV); 1200 rows (tools/build/build_captrd_biofuel.py).';
INSERT INTO value_units VALUES
  ('ctrd_biofuel_p_taxdata', 'value', NULL, 'open', 'biofuel_p_taxdata.value: EUR per 1000 l (Biofuel_data.gms)');

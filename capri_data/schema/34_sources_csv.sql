-- The CSV conversion of the sources that were not CSV (the project lead's decision, 30 October 2026: input data in .csv), written by tools/build/convert_sources_to_csv.py from the originals in git history (commit 6d25163). Structure (types, NOT NULL, keys) from the files; units open where the source states none.

-- file: capri_data/sources/capri_dat/biofuel/biofuel_technology_params_p_ByProduct.csv
CREATE TABLE src_biofuel_technology_params_p_byproduct (
    byproduct VARCHAR NOT NULL,
    stock VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (byproduct, stock)
);
COMMENT ON TABLE src_biofuel_technology_params_p_byproduct IS 'CAPRI''s p_ByProduct(byproduct, stock) from dat/biofuel/biofuel_technology_params.gms l. 52-69 ("processing coefficient per ton of product converted to bio fuel", t/t, DDGS and glycerine), every record as the file writes it, converted to CSV by tools/build/convert_sources_to_csv.py; read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_biofuel_technology_params_p_byproduct', 'value', 'U_ratio', 'capri', 't of by-product per t of feedstock (the file: Conversion coefficients for biofuel by-products (t/t))');

-- file: capri_data/sources/capri_dat/biofuel/biofuel_technology_params_p_ExtrRates.csv
CREATE TABLE src_biofuel_technology_params_p_extrrates (
    fuel VARCHAR NOT NULL,
    stock VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (fuel, stock)
);
COMMENT ON TABLE src_biofuel_technology_params_p_extrrates IS 'CAPRI''s p_ExtrRates(fuel, stock) from dat/biofuel/biofuel_technology_params.gms l. 24-47 ("Conversion rates biofuel from feedstock", t/t, RED 2009 and Aglink 2005), every record as the file writes it (labels in its case: BIOE, BioE, BioD), converted to CSV by tools/build/convert_sources_to_csv.py; read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_biofuel_technology_params_p_extrrates', 'value', 'U_ratio', 'capri', 't of biofuel per t of feedstock (the file: Conversion coefficients ... (t/t))');

-- file: capri_data/sources/capri_dat/coco/milk_quota_dat_p_MQuotaDat.csv
CREATE TABLE src_milk_quota_dat_p_mquotadat (
    region VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, info, "year")
);
COMMENT ON TABLE src_milk_quota_dat_p_mquotadat IS 'CAPRI''s TABLE p_MQuotaDat(region, info, year) from dat/coco/milk_quota_dat.gms l. 17-135 ("Milk quota data from DG Agri used in coco, captrd, capmod": quotas for deliveries QUTdel and direct sales QUTdir, deliveries Delivs, direct sales DSTOTL, 1993-2014), every cell with a number, as written, converted to CSV by tools/build/convert_sources_to_csv.py; read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_milk_quota_dat_p_mquotadat', 'value', NULL, 'open', 'milk_quota_dat_p_MQuotaDat.value: the file states no unit');

-- file: capri_data/sources/capri_dat/policy/livestock_units_p_LUUnits.csv
CREATE TABLE src_livestock_units_p_luunits (
    act VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE src_livestock_units_p_luunits IS 'CAPRI''s p_LUUnits(act) from dat/policy/livestock_units.gms l. 25-82 ("Livestock units" per animal and year, Eurostat''s LSU glossary; HENS and POUF per 1000 animals), as written, converted to CSV by tools/build/convert_sources_to_csv.py; read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_livestock_units_p_luunits', 'value', NULL, 'open', 'livestock units per head (per 1000 head for HENS, POUF); no unit code for it');

-- file: capri_data/sources/capri_dat/policy/smal_pshar_p_smallProdShare.csv
CREATE TABLE src_smal_pshar_p_smallprodshare (
    "year" BIGINT NOT NULL,
    region VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "year")
);
COMMENT ON TABLE src_smal_pshar_p_smallprodshare IS 'CAPRI''s TABLE p_smallProdShare(year, region) from dat/policy/smal_pshar.gms l. 27-57 ("Share of small producers not falling under the compulsory set-aside regime", 1993-2020), every cell with a number, as written, converted to CSV by tools/build/convert_sources_to_csv.py; read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_smal_pshar_p_smallprodshare', 'value', 'U_ratio', 'capri', 'a share (the file: Share of small producers ...)');

-- file: capri_data/sources/capri_dat/policy/wintercovershare_p_winterCoverShare0.csv
CREATE TABLE src_wintercovershare_p_wintercovershare0 (
    region VARCHAR NOT NULL,
    act VARCHAR NOT NULL,
    "value" VARCHAR NOT NULL,
    PRIMARY KEY (region, act)
);
COMMENT ON TABLE src_wintercovershare_p_wintercovershare0 IS 'CAPRI''s p_winterCoverShare0(region, act) from dat/policy/wintercovershare.gms l. 18-221 ("Share of crop in a region which provides winter cover"; EU, member-state and some NUTS 2 entries), as written: value is a number or eps (GAMS''s explicit zero, kept as text); converted to CSV by tools/build/convert_sources_to_csv.py (capri_gams/wintercovershare.gms was the same file); read by tools/build/build_cover_crops.py (read_wcs: eps -> 0, act upper-cased) and tools/build/build_winter_cover_option.py.';

-- file: capri_data/sources/capri_gams/baseline/labour_ageline_p_minLabourPerAct.csv
CREATE TABLE src_labour_ageline_p_minlabourperact (
    act VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (act)
);
COMMENT ON TABLE src_labour_ageline_p_minlabourperact IS 'CAPRI''s p_minLabourPerAct(act) from gams/baseline/labour_ageline.gms l. 92-153 (minimum labour requirement per activity, h, the average of the 5 lowest countries in 2008), as written, converted to CSV by tools/build/convert_sources_to_csv.py (the statement only; the file is CAPRI code); read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_labour_ageline_p_minlabourperact', 'value', NULL, 'open', 'hours per activity unit (ha or head) (the file''s comment); no single unit code');

-- file: capri_data/sources/capri_gams/envind/gascoeff_p_nutContCropOutput_STRA.csv
CREATE TABLE src_gascoeff_p_nutcontcropoutput_stra (
    output VARCHAR NOT NULL,
    nutrient VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (output, nutrient)
);
COMMENT ON TABLE src_gascoeff_p_nutcontcropoutput_stra IS 'CAPRI''s p_nutContCropOutput("STRA", FNUT) from gams/envind/gascoeff.gms l. 359 (TABLE p_nutContCropOutput l. 347: "retention of pure nutrient in kg per t harvested material"), the straw row tools/build/build_npk_balance_2030.py read with a pattern (its extraction moved to tools/build/convert_sources_to_csv.py), the numbers as written (5., 3., 18.); read by tools/build/build_npk_balance_2030.py.';
INSERT INTO value_units VALUES
  ('src_gascoeff_p_nutcontcropoutput_stra', 'value', NULL, 'open', 'kg per t of straw (the table''s text); no unit code for it');

-- file: capri_data/sources/capri_gams/fert/fertpar_MAXF.csv
CREATE TABLE src_fertpar_maxf (
    nutrient VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    multiplier DOUBLE NOT NULL,
    PRIMARY KEY (nutrient)
);
COMMENT ON TABLE src_fertpar_maxf IS 'CAPRI''s MAXF(FNUT) from gams/fert/fertpar.gms: value the assignments MAXF("NITF"|"PHOF"|"POTF") = v (l. 387-389), multiplier the following MAXF(FNUT) = MAXF(FNUT) * 2.0 (l. 391) ("Maximum input of nutrient for activities without yield dependency", l. 384); extracted by the patterns of tools/build/build_npk_balance_2030.py (moved to tools/build/convert_sources_to_csv.py), which reads value x multiplier.';
INSERT INTO value_units VALUES
  ('src_fertpar_maxf', 'value', NULL, 'open', 'fertpar.gms states no unit'),
  ('src_fertpar_maxf', 'multiplier', 'U_ratio', 'capri', 'a factor (l. 391)');

-- file: capri_data/sources/capri_gams/fert/fertpar_doubleMaxf.csv
CREATE TABLE src_fertpar_doublemaxf (
    activity VARCHAR NOT NULL,
    PRIMARY KEY (activity)
);
COMMENT ON TABLE src_fertpar_doublemaxf IS 'CAPRI''s set doubleMaxf(PACT) from gams/fert/fertpar.gms l. 393 ("Activities for which the above maximum loads are doubled"), extracted by the pattern of tools/build/build_npk_balance_2030.py (moved to tools/build/convert_sources_to_csv.py), which reads it.';

-- file: capri_data/sources/capri_gams/fert/fertpar_p_nfixRate_gras.csv
CREATE TABLE src_fertpar_p_nfixrate_gras (
    region VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE src_fertpar_p_nfixrate_gras IS 'CAPRI''s p_nfixRate_gras(RALL) from gams/fert/fertpar.gms l. 265-293 ("Regional N fixation rate for grassland", per member state), extracted by the patterns of tools/lib/_capri_digest.py (moved to tools/build/convert_sources_to_csv.py), which reads it (for tools/build/build_supplement_effects.py).';
INSERT INTO value_units VALUES
  ('src_fertpar_p_nfixrate_gras', 'value', NULL, 'open', 'fertpar.gms states no unit (a rate)');

-- file: capri_data/sources/capri_gams/fert/fertpar_p_nitrFact_RALL_GRAE_BioFix.csv
CREATE TABLE src_fertpar_p_nitrfact_rall_grae_biofix (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    factor VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, factor)
);
COMMENT ON TABLE src_fertpar_p_nitrfact_rall_grae_biofix IS 'CAPRI''s p_nitrFact("RALL", "GRAE", "BioFix") from gams/fert/fertpar.gms l. 236 (TABLE p_nitrFact l. 209), the default of p_nfixRate_gras (l. 295), the one cell tools/lib/_capri_digest.py read with a pattern (moved to tools/build/convert_sources_to_csv.py); read by tools/lib/_capri_digest.py.';
INSERT INTO value_units VALUES
  ('src_fertpar_p_nitrfact_rall_grae_biofix', 'value', NULL, 'open', 'fertpar.gms states no unit (a rate)');

-- file: capri_data/sources/capri_gams/inputs/yieldIY_p_inputDemandFactor.csv
CREATE TABLE src_yieldiy_p_inputdemandfactor (
    activity VARCHAR NOT NULL,
    input VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (activity, input)
);
COMMENT ON TABLE src_yieldiy_p_inputdemandfactor IS 'CAPRI''s TABLE p_inputDemandFactor(act, input) from gams/inputs/yieldIY.gms l. 29-96 ("Estimated yield dependent term of linear input demand function": the share of the input that depends on yield), each number under its nearest column header, as tools/build/build_plant_protection_cost.py read it (its extraction moved to tools/build/convert_sources_to_csv.py; the blanks are 1 by l. 103, applied by the reader); read by tools/build/build_plant_protection_cost.py.';
INSERT INTO value_units VALUES
  ('src_yieldiy_p_inputdemandfactor', 'value', 'U_ratio', 'capri', 'a share of the input (yieldIY.gms l. 24-27)');

-- file: capri_data/sources/capri_gams/pol_input/mquota_update_PMQuotaReg.csv
CREATE TABLE src_mquota_update_pmquotareg (
    region VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, info, "year")
);
COMMENT ON TABLE src_mquota_update_pmquotareg IS 'CAPRI''s TABLE PMQuotaReg(region, QUTtot, year) from gams/pol_input/mquota_update.gms l. 35-65 ("Total quota", deliveries and direct sales incl. the restructuring reserve, 2004-2014, per member state), every cell with a number, as written, converted to CSV by tools/build/convert_sources_to_csv.py (the statement only; the file is CAPRI code); read (upper-cased) by tools/build/build_captrd_dat.py.';
INSERT INTO value_units VALUES
  ('src_mquota_update_pmquotareg', 'value', NULL, 'open', 'mquota_update.gms states no unit (build_captrd_dat.py: 1000 t)');

-- file: capri_data/sources/capri_star/nutrient_cont_usda_p_nutrientCont.csv
CREATE TABLE src_nutrient_cont_usda_p_nutrientcont (
    product VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (product, "item")
);
COMMENT ON TABLE src_nutrient_cont_usda_p_nutrientcont IS 'CAPRI''s p_nutrientCont(product, item) of dat/arm/nutrient_cont_usda.gdx (USDA nutrient contents), from its Excel export nutrient_cont_usda_export.xlsx (sheet p_nutrientCont, 1320 rows, no header), integers as integers and other numbers as repr of the cell''s float, converted to CSV by tools/build/convert_sources_to_csv.py; read by tools/build/build_feed_energy.py (item Energ_cal: kcal per kg).';
INSERT INTO value_units VALUES
  ('src_nutrient_cont_usda_p_nutrientcont', 'value', NULL, 'open', 'per item, named in the item (Water_g, Energ_cal, Protein_g, ...)');

-- file: capri_data/sources/envind/fao_landuse_2000_P.csv
CREATE TABLE src_fao_landuse_2000_p (
    fao_code VARCHAR NOT NULL,
    climate_zone VARCHAR NOT NULL,
    land_use VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (fao_code, climate_zone, land_use)
);
COMMENT ON TABLE src_fao_landuse_2000_p IS 'P(fao_code, climate_zone, land_use) of CAPRI''s FAO land use 2000 by country and climate zone (gdxdump of fao_landuse_2000.gdx, "FROM MDB2GMS"), every record as dumped, converted from the gdxdump text fao_landuse_2000_P.txt by tools/build/convert_sources_to_csv.py; read by tools/build/build_histosol.py (which leaves out the last record, as its former parser did).';
INSERT INTO value_units VALUES
  ('src_fao_landuse_2000_p', 'value', NULL, 'open', 'the dump states no unit (an area)');

-- file: capri_data/sources/envind/ipcc_wetlands_p_emifacOrganicSoil_ori.csv
CREATE TABLE src_ipcc_wetlands_p_emifacorganicsoil_ori (
    gas VARCHAR NOT NULL,
    land_use VARCHAR NOT NULL,
    climate_zone VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (gas, land_use, climate_zone)
);
COMMENT ON TABLE src_ipcc_wetlands_p_emifacorganicsoil_ori IS 'CAPRI''s p_emifacOrganicSoil_ori(gas, land_use, climate_zone), IPCC 2013 Wetlands Supplement emission factors of drained organic soils (gdxdump of ipcc_wetlands.gdx), every record as dumped, converted from the gdxdump text by tools/build/convert_sources_to_csv.py; read by tools/build/build_histosol.py (which leaves out the last record, N2O grslnd tropical, as its former parser did).';
INSERT INTO value_units VALUES
  ('src_ipcc_wetlands_p_emifacorganicsoil_ori', 'value', NULL, 'open', 'per gas (kg N2O-N, ... per ha); the dump states no unit');

-- file: capri_data/sources/envind/orgsoil_share_p_orgsoilori.csv
CREATE TABLE src_orgsoil_share_p_orgsoilori (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item")
);
COMMENT ON TABLE src_orgsoil_share_p_orgsoilori IS 'CAPRI''s p_OrgSoilOri(region, item) ("Original information related to organic soils for CAPRI NUTS2 regions (and MS aggregates)": shares sog/soc/sof_regN2_rk and areas O/C/G/F_regN2), gdxdump of orgsoil_share.gdx, every record as dumped, converted from the gdxdump text by tools/build/convert_sources_to_csv.py; read by tools/build/build_histosol.py (which leaves out the last record, as its former parser did).';
INSERT INTO value_units VALUES
  ('src_orgsoil_share_p_orgsoilori', 'value', NULL, 'open', 'per item (shares and areas)');

-- file: capri_data/sources/market/eu_tariff_provenance.csv
CREATE TABLE src_eu_tariff_provenance (
    commodity VARCHAR NOT NULL,
    previous DOUBLE,
    capri_code VARCHAR,
    ad_valorem_pct DOUBLE,
    specific_eur_t DOUBLE,
    total_ave_pct DOUBLE,
    eu_imports_kt DOUBLE,
    kept VARCHAR,
    PRIMARY KEY (commodity)
);
COMMENT ON TABLE src_eu_tariff_provenance IS 'The EU row of the tariffs (tools/build/build_tariffs_2017.py) with its provenance, one row per commodity, the former eu_tariff_provenance.json (its rows; its _source: CAPRI res_0_1717cap_after_2014_cal_from_data_caldefaulta dataOut, EU27yr19 <- NONEU, 2017: total ad-valorem equivalent = ImportP/(Fob+TCost)-1), numbers as written, empty where the JSON had no field or null; converted to CSV by tools/build/convert_sources_to_csv.py; read by tools/build/build_tariffs_2017.py.';
INSERT INTO value_units VALUES
  ('src_eu_tariff_provenance', 'previous', 'U_percent', 'builder', 'the EU tariff before the CAPRI values (%, as the JSON''s fields)'),
  ('src_eu_tariff_provenance', 'ad_valorem_pct', 'U_percent', 'builder', 'the field name'),
  ('src_eu_tariff_provenance', 'specific_eur_t', 'U_EuPerTon', 'builder', 'the field name'),
  ('src_eu_tariff_provenance', 'total_ave_pct', 'U_percent', 'builder', 'the field name'),
  ('src_eu_tariff_provenance', 'eu_imports_kt', 'U_1000t', 'builder', 'the field name');

-- file: capri_data/sources/ghgtech/LitRevFertTech_p_litRevFertTechs_all.csv
CREATE TABLE src_litrevferttech_p_litrevferttechs_all (
    region VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    system VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, technology, activity, system, "item")
);
COMMENT ON TABLE src_litrevferttech_p_litrevferttechs_all IS 'CAPRI''s p_litRevFertTechs(region, technology, activity, system, item) ("outputs regarding fertilizer technologies"), every record of the project lead''s gdxdump of dat/scen/ghgtech/LitRevFertTech.gdx (15 significant digits; capri_dat/ghgtech/LitRevFertTech_p_litRevFertTechs.csv holds the same records at full precision), converted from the gdxdump text by tools/build/convert_sources_to_csv.py; read by tools/build/build_fert_side_effects.py (the NO3 records of NITR_INH -> LitRevFertTech_p_litRevFertTechs_no3.csv).';
INSERT INTO value_units VALUES
  ('src_litrevferttech_p_litrevferttechs_all', 'value', NULL, 'open', 'relative changes of emissions (the dump states no unit)');

-- file: capri_data/sources/ghgtech/miti_data_jul15_p_ghgMiti.csv
CREATE TABLE src_miti_data_jul15_p_ghgmiti (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    info VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, technology, target, info)
);
COMMENT ON TABLE src_miti_data_jul15_p_ghgmiti IS 'CAPRI''s p_ghgMiti(region, activity, technology, target, info) ("information for CAPRI activities without specification of production system") of the project lead''s gdxdump of dat/scen/ghgtech/miti_data_jul15.gdx (the mitigation data of the Green Deal runs, miti_data_type = _jul15), every record as dumped, converted from the gdxdump text miti_data_jul15_p_ghgMiti.txt by tools/build/convert_sources_to_csv.py; read by tools/build/build_fert_options_jul15.py (cropMiti, N2OSYN).';
INSERT INTO value_units VALUES
  ('src_miti_data_jul15_p_ghgmiti', 'value', NULL, 'open', 'per info (shares, costs, QEmitt)');

-- file: capri_data/sources/policy/minfert_redu_by_crop_limCres.csv
CREATE TABLE src_minfert_redu_by_crop_limcres (
    capri_region VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    add DOUBLE NOT NULL,
    after_year BIGINT NOT NULL,
    PRIMARY KEY (capri_region, ngrp)
);
COMMENT ON TABLE src_minfert_redu_by_crop_limcres IS 'CAPRI''s relaxations of the limCres regulation (crop residues to a group at most 1.3 x baseline per ha) by +add for listed (ru, NGRP) in pol_input/greendeal/minfert_redu_by_crop.gms ($ife lines l. 281-356), each with its simulation-year condition ($ifthene %simy%>YYYY: after_year, strict), as tools/build/build_mineral_redu_rules.py parsed them (its parse moved unchanged to tools/build/convert_sources_to_csv.py; numbers as the parse''s floats); read by tools/build/build_mineral_redu_rules.py.';
INSERT INTO value_units VALUES
  ('src_minfert_redu_by_crop_limcres', 'add', 'U_ratio', 'capri', 'added to the factor 1.3 of the baseline residues per ha'),
  ('src_minfert_redu_by_crop_limcres', 'after_year', NULL, 'open', 'a year (no unit)');

-- file: capri_data/sources/policy/minfert_redu_by_crop_p_checkSmallMine.csv
CREATE TABLE src_minfert_redu_by_crop_p_checksmallmine (
    capri_region VARCHAR NOT NULL,
    ngrp VARCHAR NOT NULL,
    factor DOUBLE NOT NULL,
    after_year BIGINT NOT NULL,
    othpol_high BIGINT NOT NULL,
    PRIMARY KEY (capri_region, ngrp, after_year)
);
COMMENT ON TABLE src_minfert_redu_by_crop_p_checksmallmine IS 'CAPRI''s listed exemptions p_checkSmallMine(ru, NGRP) = factor x p_minfertBaseline (adhoc fixes for unclear infeasibilities; factor 1 where the statement has none) in pol_input/greendeal/minfert_redu_by_crop.gms (l. 110-228), each with its simulation-year condition ($ifthene %simy%>YYYY: after_year, strict) and othPol == high (othpol_high 1), as tools/build/build_mineral_redu_rules.py parsed them (its parse moved unchanged to tools/build/convert_sources_to_csv.py; numbers as the parse''s floats); read by tools/build/build_mineral_redu_rules.py.';
INSERT INTO value_units VALUES
  ('src_minfert_redu_by_crop_p_checksmallmine', 'factor', 'U_ratio', 'capri', 'a factor on the baseline mineral N per ha'),
  ('src_minfert_redu_by_crop_p_checksmallmine', 'after_year', NULL, 'open', 'a year (no unit)'),
  ('src_minfert_redu_by_crop_p_checksmallmine', 'othpol_high', NULL, 'open', 'a flag (no unit)');

-- file: capri_data/sources/water/cropwat_p_cropwatReq.csv
CREATE TABLE src_cropwat_p_cropwatreq (
    region VARCHAR NOT NULL,
    crop VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, crop, "item")
);
COMMENT ON TABLE src_cropwat_p_cropwatreq IS 'CAPRI''s p_cropwatReq(region, crop, item) ("crop water requirements (mm) from CROPWAT": CPET, CRAIN, CNIR in mm; YRATIO, YFACT ratios), every record of the gdxdump cropwat.gms (as uploaded), converted from the gdxdump text by tools/build/convert_sources_to_csv.py; read by tools/build/build_irrigation_2017.py (CNIR).';
INSERT INTO value_units VALUES
  ('src_cropwat_p_cropwatreq', 'value', NULL, 'open', 'mm for CPET, CRAIN, CNIR; ratios for YRATIO, YFACT');

-- file: capri_data/sources/water/irrishare_p_irriShare.csv
CREATE TABLE src_irrishare_p_irrishare (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "type" VARCHAR NOT NULL,
    "year" BIGINT NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item", "type", "year")
);
COMMENT ON TABLE src_irrishare_p_irrishare IS 'CAPRI''s p_irriShare(region, item, type, year) ("share of irrigable and irrigated area in UAAR (%)": IRRI irrigable, IRR2 irrigated once a year; Eurostat FSS), every record of the gdxdump irrishare.gms (as uploaded), converted from the gdxdump text by tools/build/convert_sources_to_csv.py; read by tools/build/build_irrigation_2017.py (IRR2 IRSH).';
INSERT INTO value_units VALUES
  ('src_irrishare_p_irrishare', 'value', NULL, 'open', 'the dump says % but holds shares (0.0217): unit to be established');

-- Sets of CAPRI's conversion of GLOBIOM-EU's projections into long-run change factors (global/convert_globiom.gms,
-- GLOBIOM-EU branch; capri_mod/pipeline/captrd/globiom.py), by tools/build/build_captrd_globiom_sets.py.

-- file: capri_data/pipeline/captrd/sets/globiom/demposdis.csv
CREATE TABLE ctrd_globiom_demposdis (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_demposdis IS 'CAPRI''s set DemPosDis (the disaggregated demand positions mapped to GLOBIOM; gams/global/convert_globiom.gms l. 1711-1716): one member per row in d0, 3 records (e.g. FEDM, HCOM, BIOF); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/globiom_to_cols.csv
CREATE TABLE ctrd_globiom_globiom_to_cols (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_globiom_to_cols IS 'CAPRI''s set GLOBIOM_TO_COLS (GLOBIOM''s columns to CAPRI''s columns; gams/global/convert_globiom.gms l. 1045-1120): one tuple per row (d0, d1), 69 records (e.g. BARL.BARL, BeaD.PULS, ChkP.PULS); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/globiom_to_rows.csv
CREATE TABLE ctrd_globiom_globiom_to_rows (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_globiom_to_rows IS 'CAPRI''s set GLOBIOM_TO_ROWS (GLOBIOM''s rows to CAPRI''s rows; gams/global/convert_globiom.gms l. 865-949): one tuple per row (d0, d1), 64 records (e.g. Whea.SWHE, Whea.DWHE, Whea.WHEA); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/globiomcols.csv
CREATE TABLE ctrd_globiom_globiomcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_globiomcols IS 'CAPRI''s set GLOBIOMcols (GLOBIOM''s columns (crops, land uses, animals, positions); gams/global/convert_globiom.gms l. 964-1035): one member per row in d0, 58 records (e.g. BARL, BeaD, Cass); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/globiommacro.csv
CREATE TABLE ctrd_globiom_globiommacro (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_globiommacro IS 'CAPRI''s set GLOBIOMmacro (GLOBIOM''s macroeconomic items; gams/global/convert_globiom.gms l. 1037-1042): one member per row in d0, 4 records (e.g. POP, GDP, POP_RelChng); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/globiomrows.csv
CREATE TABLE ctrd_globiom_globiomrows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_globiomrows IS 'CAPRI''s set GLOBIOMrows (GLOBIOM''s rows (products and items); gams/global/convert_globiom.gms l. 694-852): one member per row in d0, 55 records (e.g. PlmO, RapO, SoyO); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/longtext_globiom_faoregmap.csv
CREATE TABLE ctrd_globiom_longtext_globiom_faoregmap (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    d2 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1, d2)
);
COMMENT ON TABLE ctrd_globiom_longtext_globiom_faoregmap IS 'CAPRI''s set longtext_GLOBIOM_FAOREGMAP (GLOBIOM''s countries (long name, GLOBIOM label) to FAO region codes; gams/global/globiom_to_fao_reg.gms l. 13-99): one tuple per row (d0, d1, d2), 192 records (e.g. Afghanistan.Afghanistan.2, Albania.Albania.3, Algeria.Algeria.4); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/longyr.csv
CREATE TABLE ctrd_globiom_longyr (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_longyr IS 'CAPRI''s set longYr (the years of GLOBIOM data and projections; gams/global/convert_globiom.gms l. 412-425): one member per row in d0, 13 records (e.g. 1999, 2000, 2001); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/longyrsel.csv
CREATE TABLE ctrd_globiom_longyrsel (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_longyrsel IS 'CAPRI''s set longYrSel (the years collected from the projections; gams/global/convert_globiom.gms l. 428-431): one member per row in d0, 10 records (e.g. B2000, 2017, 2000); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/longyrselwo00.csv
CREATE TABLE ctrd_globiom_longyrselwo00 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_longyrselwo00 IS 'CAPRI''s set longYrSelWo00 (those years without 2000; gams/global/convert_globiom.gms l. 434-437): one member per row in d0, 9 records (e.g. B2000, 2017, 2010); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/macro.csv
CREATE TABLE ctrd_globiom_macro (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_macro IS 'CAPRI''s set Macro (CAPRI''s macro columns (INHA, GDP); gams/global/convert_globiom.gms l. 1043): one member per row in d0, 2 records (e.g. INHA, GDP); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/mono.csv
CREATE TABLE ctrd_globiom_mono (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_mono IS 'CAPRI''s set MONO (GLOBIOM''s monogastric animals; gams/global/convert_globiom.gms l. 621-623): one member per row in d0, 4 records (e.g. PIGS, PTRB, PTRH); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/mrkpos.csv
CREATE TABLE ctrd_globiom_mrkpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_mrkpos IS 'CAPRI''s set MrkPos (the market positions used; gams/global/convert_globiom.gms l. 1723-1728): one member per row in d0, 6 records (e.g. FEDM, HCOM, BIOF); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/poles_to_globiomregion.csv
CREATE TABLE ctrd_globiom_poles_to_globiomregion (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_poles_to_globiomregion IS 'CAPRI''s set POLES_to_GLOBIOMregion (POLES regions to GLOBIOM regions; gams/global/convert_globiom.gms l. 1177-1205): one tuple per row (d0, d1), 27 records (e.g. BRAp.BrazilReg, CANp.CanadaReg, CHNp.ChinaReg); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/polesregion.csv
CREATE TABLE ctrd_globiom_polesregion (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_polesregion IS 'CAPRI''s set POLESregion (the POLES regions of GLOBIOM-EU; gams/global/convert_globiom.gms l. 1155-1175): one member per row in d0, 19 records (e.g. BRAp, CANp, CHNp); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/procpr.csv
CREATE TABLE ctrd_globiom_procpr (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_procpr IS 'CAPRI''s set PROCPR (GLOBIOM''s processing outputs; gams/global/convert_globiom.gms l. 661-691): one member per row in d0, 40 records (e.g. sawnwood, woodpulp, ow_biomass); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/tradepos.csv
CREATE TABLE ctrd_globiom_tradepos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_tradepos IS 'CAPRI''s set TradePos (the trade positions; gams/global/convert_globiom.gms l. 1718-1721): one member per row in d0, 2 records (e.g. IMPT, EXPT); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/vegoil.csv
CREATE TABLE ctrd_globiom_vegoil (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_vegoil IS 'CAPRI''s set vegoil (GLOBIOM''s vegetable oils; gams/global/convert_globiom.gms l. 855-860): one member per row in d0, 4 records (e.g. SUNO, RAPO, SOYO); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/yldfeedconv.csv
CREATE TABLE ctrd_globiom_yldfeedconv (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_yldfeedconv IS 'CAPRI''s set YLDFEEDCONV (GLOBIOM''s yield and feed conversion growth rows; gams/global/convert_globiom.gms l. 1136-1141): one member per row in d0, 2 records (e.g. YieldGrowth, FeedConvGrowth); read from the GLOBIOM-EU branch of the source by tools/build/build_captrd_globiom_sets.py.';

-- CAPRI's sets the conversion uses, copied from the run's instantiation in sim_ini_21730

-- file: capri_data/pipeline/captrd/sets/globiom/rmall.csv
CREATE TABLE ctrd_globiom_rmall (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_rmall IS 'CAPRI''s set RMall, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 113 records (e.g. BL000000, DK000000, DE000000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/rw.csv
CREATE TABLE ctrd_globiom_rw (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_rw IS 'CAPRI''s set RW, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 20 records (e.g. NONEU_EU, ASIA, AFRICA); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/rm.csv
CREATE TABLE ctrd_globiom_rm (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_rm IS 'CAPRI''s set RM, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 45 records (e.g. UK000000, NO000000, TUR); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/rms.csv
CREATE TABLE ctrd_globiom_rms (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_rms IS 'CAPRI''s set RMS, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 80 records (e.g. BL000000, DK000000, DE000000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/rw_to_rm.csv
CREATE TABLE ctrd_globiom_rw_to_rm (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_rw_to_rm IS 'CAPRI''s set RW_TO_RM, as convert_globiom.gms and create_longrun_info.gms use it: one tuple per row (d0, d1), 185 records (e.g. NONEU_EU.UK000000, NONEU_EU.NO000000, NONEU_EU.TUR); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/rms_to_rm.csv
CREATE TABLE ctrd_globiom_rms_to_rm (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_rms_to_rm IS 'CAPRI''s set RMS_TO_RM, as convert_globiom.gms and create_longrun_info.gms use it: one tuple per row (d0, d1), 80 records (e.g. BL000000.A_EU_WEST, DK000000.A_EU_WEST, DE000000.A_EU_WEST); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/nuts0.csv
CREATE TABLE ctrd_globiom_nuts0 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_nuts0 IS 'CAPRI''s set NUTS0, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 35 records (e.g. BL000000, DK000000, DE000000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/msall.csv
CREATE TABLE ctrd_globiom_msall (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_msall IS 'CAPRI''s set MSALL, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 41 records (e.g. BL000000, DK000000, DE000000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/euallagg.csv
CREATE TABLE ctrd_globiom_euallagg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_euallagg IS 'CAPRI''s set EUAllAgg, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 12 records (e.g. A_EU_WEST, A_EU_EAST, EU028000); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/faoregions.csv
CREATE TABLE ctrd_globiom_faoregions (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_faoregions IS 'CAPRI''s set FAORegions, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 230 records (e.g. 1, 2, 3); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/faoregions_map.csv
CREATE TABLE ctrd_globiom_faoregions_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_globiom_faoregions_map IS 'CAPRI''s set FAORegions_map, as convert_globiom.gms and create_longrun_info.gms use it: one tuple per row (d0, d1), 227 records (e.g. BL000000.255, BL000000.256, DK000000.54); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/secom.csv
CREATE TABLE ctrd_globiom_secom (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_secom IS 'CAPRI''s set SECOM, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 29 records (e.g. BIOE, BIOD, WHEP); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/sets/globiom/landusearto.csv
CREATE TABLE ctrd_globiom_landusearto (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_globiom_landusearto IS 'CAPRI''s set LandUseARTO, as convert_globiom.gms and create_longrun_info.gms use it: one member per row in d0, 5 records (e.g. FORE, ARTIF, INLW); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_globiom_sets.py.';

-- file: capri_data/pipeline/captrd/dat/globiom_scenarios.csv
CREATE TABLE ctrd_globiom_scenarios (
    scenario VARCHAR NOT NULL,
    glo_scen VARCHAR,
    file VARCHAR NOT NULL,
    macro_scen VARCHAR NOT NULL,
    bioen_scen VARCHAR NOT NULL,
    iea_scen VARCHAR NOT NULL,
    PRIMARY KEY (scenario)
);
COMMENT ON TABLE ctrd_globiom_scenarios IS 'The GLOBIOM-EU long-run selections of gams/global/convert_globiom.gms l. 269-286: per selection (SelecScen) its glo_scen option (empty: the default branch), the GLOBIOM file (GLOfilename, in dat/global) and its scenario (macroScen, bioEnScen, IEAscen of SelecScen_map); 3 records; transcribed in tools/build/build_captrd_globiom_sets.py.';

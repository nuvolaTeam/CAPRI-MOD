-- Inputs under capri_data/pipeline/captrd/sets/aglink2023dgAgri: CAPTRD's Aglink-COSIMO 2023 sets and mappings, read
-- from CAPRI's GAMS files by tools/build/build_captrd_aglink_sets.py (tools/lib/gams_sets.py); for CAPTRD-MOD's Aglink stage
-- (capri_mod/pipeline/captrd/aglink.py). Generated structure, 10 November 2026. GAMS allows the empty label '' (CAPRI's
-- cols has one, Aglink's products_map uses it as the parent of every product): those columns may be empty.

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/_aliases.csv
CREATE TABLE ctrd_ag_aliases (
    alias VARCHAR NOT NULL,
    "set" VARCHAR NOT NULL,
    PRIMARY KEY (alias)
);
COMMENT ON TABLE ctrd_ag_aliases IS 'GAMS aliases of these sets (upper case): alias, the set it names';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/_unparsed.csv
CREATE TABLE ctrd_ag_unparsed (
    file VARCHAR NOT NULL,
    "line" BIGINT NOT NULL,
    statement VARCHAR NOT NULL,
    handled VARCHAR NOT NULL,
    PRIMARY KEY (file, "line")
);
COMMENT ON TABLE ctrd_ag_unparsed IS 'the statements of the Aglink set files the reader leaves to the builder: transcribed there, or not needed (checks, displays, parameters, FAO sets)';
INSERT INTO value_units VALUES
  ('ctrd_ag_unparsed', 'line', NULL, 'open', 'a line number of the GAMS file');

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_balPos.csv
CREATE TABLE ctrd_ag_ag_balpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_balpos IS 'CAPTRD''s Aglink set ag_balPos, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_BioVar.csv
CREATE TABLE ctrd_ag_ag_biovar (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_biovar IS 'CAPTRD''s Aglink set ag_BioVar, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_colsFrm.csv
CREATE TABLE ctrd_ag_ag_colsfrm (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_colsfrm IS 'CAPTRD''s Aglink set ag_colsFrm, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_colsV.csv
CREATE TABLE ctrd_ag_ag_colsv (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_colsv IS 'CAPTRD''s Aglink set ag_colsV, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_EUreg.csv
CREATE TABLE ctrd_ag_ag_eureg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_eureg IS 'CAPTRD''s Aglink set ag_EUreg, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_macroVar.csv
CREATE TABLE ctrd_ag_ag_macrovar (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_macrovar IS 'CAPTRD''s Aglink set ag_macroVar, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_macroVarNoFoe.csv
CREATE TABLE ctrd_ag_ag_macrovarnofoe (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_macrovarnofoe IS 'CAPTRD''s Aglink set ag_macroVarNoFoe, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_market.csv
CREATE TABLE ctrd_ag_ag_market (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_market IS 'CAPTRD''s Aglink set ag_market, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_marketMap.csv
CREATE TABLE ctrd_ag_ag_marketmap (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_ag_marketmap IS 'CAPTRD''s Aglink set ag_marketMap, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_Other.csv
CREATE TABLE ctrd_ag_ag_other (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_other IS 'CAPTRD''s Aglink set ag_Other, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_Prim.csv
CREATE TABLE ctrd_ag_ag_prim (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_prim IS 'CAPTRD''s Aglink set ag_Prim, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_Regs.csv
CREATE TABLE ctrd_ag_ag_regs (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_regs IS 'CAPTRD''s Aglink set ag_Regs, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_Rows.csv
CREATE TABLE ctrd_ag_ag_rows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_rows IS 'CAPTRD''s Aglink set ag_Rows, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_Seco.csv
CREATE TABLE ctrd_ag_ag_seco (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_seco IS 'CAPTRD''s Aglink set ag_Seco, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ag_var.csv
CREATE TABLE ctrd_ag_ag_var (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ag_var IS 'CAPTRD''s Aglink set ag_var, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agBalPos.csv
CREATE TABLE ctrd_ag_agbalpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agbalpos IS 'CAPTRD''s Aglink set agBalPos, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agBioF.csv
CREATE TABLE ctrd_ag_agbiof (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agbiof IS 'CAPTRD''s Aglink set agBioF, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agBioVar.csv
CREATE TABLE ctrd_ag_agbiovar (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agbiovar IS 'CAPTRD''s Aglink set agBioVar, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agByprod.csv
CREATE TABLE ctrd_ag_agbyprod (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agbyprod IS 'CAPTRD''s Aglink set agByprod, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agCols.csv
CREATE TABLE ctrd_ag_agcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agcols IS 'CAPTRD''s Aglink set agCols, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agColsBio_hierarhy.csv
CREATE TABLE ctrd_ag_agcolsbio_hierarhy (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    d2 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1, d2)
);
COMMENT ON TABLE ctrd_ag_agcolsbio_hierarhy IS 'CAPTRD''s Aglink set agColsBio_hierarhy, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agColsBio_map.csv
CREATE TABLE ctrd_ag_agcolsbio_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_agcolsbio_map IS 'CAPTRD''s Aglink set agColsBio_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agColsFrm.csv
CREATE TABLE ctrd_ag_agcolsfrm (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agcolsfrm IS 'CAPTRD''s Aglink set agColsFrm, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agColsSummable.csv
CREATE TABLE ctrd_ag_agcolssummable (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agcolssummable IS 'CAPTRD''s Aglink set agColsSummable, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agColsV.csv
CREATE TABLE ctrd_ag_agcolsv (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agcolsv IS 'CAPTRD''s Aglink set agColsV, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agEUparts.csv
CREATE TABLE ctrd_ag_ageuparts (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ageuparts IS 'CAPTRD''s Aglink set agEUparts, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agEUreg.csv
CREATE TABLE ctrd_ag_ageureg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ageureg IS 'CAPTRD''s Aglink set agEUreg, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agEurop.csv
CREATE TABLE ctrd_ag_ageurop (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ageurop IS 'CAPTRD''s Aglink set agEurop, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agFosF.csv
CREATE TABLE ctrd_ag_agfosf (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agfosf IS 'CAPTRD''s Aglink set agFosF, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agFuels.csv
CREATE TABLE ctrd_ag_agfuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agfuels IS 'CAPTRD''s Aglink set agFuels, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agFuels_o.csv
CREATE TABLE ctrd_ag_agfuels_o (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agfuels_o IS 'CAPTRD''s Aglink set agFuels_o, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLC.csv
CREATE TABLE ctrd_ag_aglc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglc IS 'CAPTRD''s Aglink set AGLC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLCOSallC.csv
CREATE TABLE ctrd_ag_aglcosallc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglcosallc IS 'CAPTRD''s Aglink set AGLCOSallC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLCOSC.csv
CREATE TABLE ctrd_ag_aglcosc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglcosc IS 'CAPTRD''s Aglink set AGLCOSC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLCOSnoEUNC.csv
CREATE TABLE ctrd_ag_aglcosnoeunc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglcosnoeunc IS 'CAPTRD''s Aglink set AGLCOSnoEUNC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglink.csv
CREATE TABLE ctrd_ag_aglink (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglink IS 'CAPTRD''s Aglink set aglink, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkAct_map.csv
CREATE TABLE ctrd_ag_aglinkact_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkact_map IS 'CAPTRD''s Aglink set aglinkAct_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLINKBioCols.csv
CREATE TABLE ctrd_ag_aglinkbiocols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkbiocols IS 'CAPTRD''s Aglink set AGLINKBioCols, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLINKBioColsQ.csv
CREATE TABLE ctrd_ag_aglinkbiocolsq (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkbiocolsq IS 'CAPTRD''s Aglink set AGLINKBioColsQ, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLINKBioColsV.csv
CREATE TABLE ctrd_ag_aglinkbiocolsv (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkbiocolsv IS 'CAPTRD''s Aglink set AGLINKBioColsV, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLINKBioRows.csv
CREATE TABLE ctrd_ag_aglinkbiorows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkbiorows IS 'CAPTRD''s Aglink set AGLINKBioRows, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkCols.csv
CREATE TABLE ctrd_ag_aglinkcols (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkcols IS 'CAPTRD''s Aglink set aglinkCols, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkCols_bioMap.csv
CREATE TABLE ctrd_ag_aglinkcols_biomap (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkcols_biomap IS 'CAPTRD''s Aglink set aglinkCols_bioMap, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkCols_map.csv
CREATE TABLE ctrd_ag_aglinkcols_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkcols_map IS 'CAPTRD''s Aglink set aglinkCols_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkCols_no_agBalPos.csv
CREATE TABLE ctrd_ag_aglinkcols_no_agbalpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkcols_no_agbalpos IS 'CAPTRD''s Aglink set aglinkCols_no_agBalPos, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkColsMapped.csv
CREATE TABLE ctrd_ag_aglinkcolsmapped (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkcolsmapped IS 'CAPTRD''s Aglink set aglinkColsMapped, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AGLINKFuelMatch.csv
CREATE TABLE ctrd_ag_aglinkfuelmatch (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkfuelmatch IS 'CAPTRD''s Aglink set AGLINKFuelMatch, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkRegions_map.csv
CREATE TABLE ctrd_ag_aglinkregions_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkregions_map IS 'CAPTRD''s Aglink set aglinkRegions_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AglinkRegionsMapped.csv
CREATE TABLE ctrd_ag_aglinkregionsmapped (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkregionsmapped IS 'CAPTRD''s Aglink set AglinkRegionsMapped, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/AglinkRegionsNotMapped.csv
CREATE TABLE ctrd_ag_aglinkregionsnotmapped (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkregionsnotmapped IS 'CAPTRD''s Aglink set AglinkRegionsNotMapped, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkRows_map.csv
CREATE TABLE ctrd_ag_aglinkrows_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_aglinkrows_map IS 'CAPTRD''s Aglink set aglinkRows_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkRowsMapped.csv
CREATE TABLE ctrd_ag_aglinkrowsmapped (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkrowsmapped IS 'CAPTRD''s Aglink set aglinkRowsMapped, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/aglinkYears.csv
CREATE TABLE ctrd_ag_aglinkyears (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_aglinkyears IS 'CAPTRD''s Aglink set aglinkYears, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agMacroVar.csv
CREATE TABLE ctrd_ag_agmacrovar (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agmacrovar IS 'CAPTRD''s Aglink set agMacroVar, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agOther.csv
CREATE TABLE ctrd_ag_agother (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agother IS 'CAPTRD''s Aglink set agOther, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agPrim.csv
CREATE TABLE ctrd_ag_agprim (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agprim IS 'CAPTRD''s Aglink set agPrim, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agRegs.csv
CREATE TABLE ctrd_ag_agregs (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agregs IS 'CAPTRD''s Aglink set agRegs, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agRows.csv
CREATE TABLE ctrd_ag_agrows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agrows IS 'CAPTRD''s Aglink set agRows, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agRowsAggregate_map.csv
CREATE TABLE ctrd_ag_agrowsaggregate_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_agrowsaggregate_map IS 'CAPTRD''s Aglink set agRowsAggregate_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agSeco.csv
CREATE TABLE ctrd_ag_agseco (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agseco IS 'CAPTRD''s Aglink set agSeco, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/agYears.csv
CREATE TABLE ctrd_ag_agyears (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_agyears IS 'CAPTRD''s Aglink set agYears, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/biofC.csv
CREATE TABLE ctrd_ag_biofc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_biofc IS 'CAPTRD''s Aglink set biofC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/BIOFUELS.csv
CREATE TABLE ctrd_ag_biofuels (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_biofuels IS 'CAPTRD''s Aglink set BIOFUELS, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/bioSource.csv
CREATE TABLE ctrd_ag_biosource (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_biosource IS 'CAPTRD''s Aglink set bioSource, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/bioSource_map.csv
CREATE TABLE ctrd_ag_biosource_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_biosource_map IS 'CAPTRD''s Aglink set bioSource_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/CCC.csv
CREATE TABLE ctrd_ag_ccc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ccc IS 'CAPTRD''s Aglink set CCC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/chkset1.csv
CREATE TABLE ctrd_ag_chkset1 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_chkset1 IS 'CAPTRD''s Aglink set chkset1, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/COLS.csv
CREATE TABLE ctrd_ag_cols (
    d0 VARCHAR
);
COMMENT ON TABLE ctrd_ag_cols IS 'CAPRI''s global set cols (capri_sources/reference/sets/simini_21730) with the elements baseline/aglink2023dgAgri_mappings.gms l. 63-64 adds';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ColsMappedAglink.csv
CREATE TABLE ctrd_ag_colsmappedaglink (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_colsmappedaglink IS 'CAPTRD''s Aglink set ColsMappedAglink, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/colums.csv
CREATE TABLE ctrd_ag_colums (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_colums IS 'CAPTRD''s Aglink set colums, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/COSC.csv
CREATE TABLE ctrd_ag_cosc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_cosc IS 'CAPTRD''s Aglink set COSC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/EUNAGGP_M.csv
CREATE TABLE ctrd_ag_eunaggp_m (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_eunaggp_m IS 'CAPTRD''s Aglink set EUNAGGP_M, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/EUNC.csv
CREATE TABLE ctrd_ag_eunc (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_eunc IS 'CAPTRD''s Aglink set EUNC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/EUparts.csv
CREATE TABLE ctrd_ag_euparts (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_euparts IS 'CAPTRD''s Aglink set EUparts, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/EUreg.csv
CREATE TABLE ctrd_ag_eureg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_eureg IS 'CAPTRD''s Aglink set EUreg, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/EuropReg.csv
CREATE TABLE ctrd_ag_europreg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_europreg IS 'CAPTRD''s Aglink set EuropReg, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/FAODataType.csv
CREATE TABLE ctrd_ag_faodatatype (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_faodatatype IS 'CAPTRD''s Aglink set FAODataType, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/FAORegionsNotUpto2013.csv
CREATE TABLE ctrd_ag_faoregionsnotupto2013 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_faoregionsnotupto2013 IS 'CAPTRD''s Aglink set FAORegionsNotUpto2013, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/FAORegionsNotUpto2013ini.csv
CREATE TABLE ctrd_ag_faoregionsnotupto2013ini (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_faoregionsnotupto2013ini IS 'CAPTRD''s Aglink set FAORegionsNotUpto2013ini, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/for.csv
CREATE TABLE ctrd_ag_for (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_for IS 'CAPTRD''s Aglink set for, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/m_eq.csv
CREATE TABLE ctrd_ag_m_eq (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_m_eq IS 'CAPTRD''s Aglink set m_eq, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/majorAglinkProd_map.csv
CREATE TABLE ctrd_ag_majoraglinkprod_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_majoraglinkprod_map IS 'CAPTRD''s Aglink set majorAglinkProd_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/map_CROP_FERTCP.csv
CREATE TABLE ctrd_ag_map_crop_fertcp (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_map_crop_fertcp IS 'CAPTRD''s Aglink set map_CROP_FERTCP, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/map_CROP_FERTQC.csv
CREATE TABLE ctrd_ag_map_crop_fertqc (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_map_crop_fertqc IS 'CAPTRD''s Aglink set map_CROP_FERTQC, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/map_CROP_FERTQCHA.csv
CREATE TABLE ctrd_ag_map_crop_fertqcha (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_map_crop_fertqcha IS 'CAPTRD''s Aglink set map_CROP_FERTQCHA, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/map_FERT_QCCP.csv
CREATE TABLE ctrd_ag_map_fert_qccp (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_map_fert_qccp IS 'CAPTRD''s Aglink set map_FERT_QCCP, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/map_FERTQC_FERTQCHA.csv
CREATE TABLE ctrd_ag_map_fertqc_fertqcha (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_map_fertqc_fertqcha IS 'CAPTRD''s Aglink set map_FERTQC_FERTQCHA, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/measures_map.csv
CREATE TABLE ctrd_ag_measures_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_measures_map IS 'CAPTRD''s Aglink set measures_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ModAggs.csv
CREATE TABLE ctrd_ag_modaggs (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_modaggs IS 'CAPTRD''s Aglink set ModAggs, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/not_m_eq.csv
CREATE TABLE ctrd_ag_not_m_eq (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_not_m_eq IS 'CAPTRD''s Aglink set not_m_eq, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/PPP.csv
CREATE TABLE ctrd_ag_ppp (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_ppp IS 'CAPTRD''s Aglink set PPP, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/products_map.csv
CREATE TABLE ctrd_ag_products_map (
    d0 VARCHAR,
    d1 VARCHAR NOT NULL
);
COMMENT ON TABLE ctrd_ag_products_map IS 'CAPTRD''s Aglink set products_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/regions_map.csv
CREATE TABLE ctrd_ag_regions_map (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_ag_regions_map IS 'CAPTRD''s Aglink set regions_map, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/RM.csv
CREATE TABLE ctrd_ag_rm (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_rm IS 'CAPTRD''s Aglink set RM, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/RmAggSup.csv
CREATE TABLE ctrd_ag_rmaggsup (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_rmaggsup IS 'CAPTRD''s Aglink set RmAggSup, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/ROWS.csv
CREATE TABLE ctrd_ag_rows (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_rows IS 'CAPRI''s global set rows (capri_sources/reference/sets/simini_21730) with the elements baseline/aglink2023dgAgri_mappings.gms l. 63-64 adds';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/RowsMappedAglink.csv
CREATE TABLE ctrd_ag_rowsmappedaglink (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_rowsmappedaglink IS 'CAPTRD''s Aglink set RowsMappedAglink, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/used.csv
CREATE TABLE ctrd_ag_used (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_used IS 'CAPTRD''s Aglink set used, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/wldAgg.csv
CREATE TABLE ctrd_ag_wldagg (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_wldagg IS 'CAPTRD''s Aglink set wldAgg, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

-- file: capri_data/pipeline/captrd/sets/aglink2023dgAgri/wldAgg1.csv
CREATE TABLE ctrd_ag_wldagg1 (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_ag_wldagg1 IS 'CAPTRD''s Aglink set wldAgg1, as GAMS compiles baseline/aglink2023dgAgri_sets.gms (with mainsets_MTO2023.gms), global/fao_codes_new.gms and baseline/aglink2023dgAgri_mappings.gms';

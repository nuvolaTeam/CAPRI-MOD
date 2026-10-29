-- CAPRI's ammonia technologies and MITERRA N cascade inputs (envind/ammo_tech.gms, ammo_cost.gms, ghgMiti.gms), read by
-- the regional models' ammonia options and the environmental accounts. Most values carry the units of CAPRI's
-- MITERRA files, which CAPRI does not state: declared open (value_units), with the CAPRI symbol as the basis.

-- file: capri_data/2017/abatement/ammonia/ControlStrategies.csv
CREATE TABLE amm_controlstrategies (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    strategy VARCHAR NOT NULL,
    "item" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, strategy, "item")
);
COMMENT ON TABLE amm_controlstrategies IS 'MITERRA control strategies by year (LitRev_non_changeable_parameters ControlStrat_TS), percent of animals (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_controlstrategies', 'value', NULL, 'open', 'ControlStrategies value');

-- file: capri_data/2017/abatement/ammonia/EmFracFert.csv
CREATE TABLE amm_emfracfert (
    region VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    fertiliser VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, gas, fertiliser)
);
COMMENT ON TABLE amm_emfracfert IS 'emission fractions of mineral fertiliser by type (p_emFracFert: urea, other) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_emfracfert', 'value', NULL, 'open', 'EmFracFert value');

-- file: capri_data/2017/abatement/ammonia/FracEmAppl.csv
CREATE TABLE amm_fracemappl (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, gas)
);
COMMENT ON TABLE amm_fracemappl IS 'emission fractions at manure application (LitRev_inputs FracEmAppl) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_fracemappl', 'value', NULL, 'open', 'FracEmAppl value');

-- file: capri_data/2017/abatement/ammonia/FracEmGrazing.csv
CREATE TABLE amm_fracemgrazing (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, "item")
);
COMMENT ON TABLE amm_fracemgrazing IS 'emission fractions on grazing (FracEmGrazing) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_fracemgrazing', 'value', NULL, 'open', 'FracEmGrazing value');

-- file: capri_data/2017/abatement/ammonia/FracEmHouse.csv
CREATE TABLE amm_fracemhouse (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, gas)
);
COMMENT ON TABLE amm_fracemhouse IS 'emission fractions in housing (FracEmHouse) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_fracemhouse', 'value', NULL, 'open', 'FracEmHouse value');

-- file: capri_data/2017/abatement/ammonia/FracEmStorage.csv
CREATE TABLE amm_fracemstorage (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, gas)
);
COMMENT ON TABLE amm_fracemstorage IS 'emission fractions in storage (FracEmStorage) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_fracemstorage', 'value', NULL, 'open', 'FracEmStorage value');

-- file: capri_data/2017/abatement/ammonia/NN_CorrFertFactDeviation.csv
CREATE TABLE amm_nn_corrfertfactdeviation (
    region VARCHAR NOT NULL,
    fertiliser VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, fertiliser, "year")
);
COMMENT ON TABLE amm_nn_corrfertfactdeviation IS 'MITERRA correction of the fertiliser factors by year (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_nn_corrfertfactdeviation', 'value', NULL, 'open', 'NN_CorrFertFactDeviation value');

-- file: capri_data/2017/abatement/ammonia/RCEmissions.csv
CREATE TABLE amm_rcemissions (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, "item")
);
COMMENT ON TABLE amm_rcemissions IS 'MITERRA emission and excretion coefficients per animal (RCEmissions) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_rcemissions', 'value', NULL, 'open', 'RCEmissions value');

-- file: capri_data/2017/abatement/ammonia/ad_option.csv
CREATE TABLE amm_ad_option (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    lg DOUBLE NOT NULL,
    ini DOUBLE NOT NULL,
    "max" DOUBLE NOT NULL,
    r_ch4 DOUBLE NOT NULL,
    costParLin DOUBLE NOT NULL,
    costParSqr DOUBLE NOT NULL,
    revenue DOUBLE NOT NULL,
    pmpParSqr DOUBLE NOT NULL,
    thresh DOUBLE NOT NULL,
    slope DOUBLE NOT NULL,
    vser DOUBLE NOT NULL,
    vser_source VARCHAR NOT NULL,
    PRIMARY KEY (region, activity, vser_source)
);
COMMENT ON TABLE amm_ad_option IS 'CAPRI''s anaerobic digestion option AD_AnCh per unit and activity (envind/ammo_tech.gms; build_ad_option.py) (tools/build/build_ad_option.py)';
INSERT INTO value_units VALUES
  ('amm_ad_option', 'lg', NULL, 'open', 'ad_option lg'),
  ('amm_ad_option', 'ini', NULL, 'open', 'ad_option ini'),
  ('amm_ad_option', 'max', NULL, 'open', 'ad_option max'),
  ('amm_ad_option', 'r_ch4', NULL, 'open', 'ad_option r_ch4'),
  ('amm_ad_option', 'costParLin', NULL, 'open', 'ad_option costParLin'),
  ('amm_ad_option', 'costParSqr', NULL, 'open', 'ad_option costParSqr'),
  ('amm_ad_option', 'revenue', NULL, 'open', 'ad_option revenue'),
  ('amm_ad_option', 'pmpParSqr', NULL, 'open', 'ad_option pmpParSqr'),
  ('amm_ad_option', 'thresh', NULL, 'open', 'ad_option thresh'),
  ('amm_ad_option', 'slope', NULL, 'open', 'ad_option slope'),
  ('amm_ad_option', 'vser', NULL, 'open', 'ad_option vser');

-- file: capri_data/2017/abatement/ammonia/ammonia_tech_model.csv
CREATE TABLE amm_ammonia_tech_model (
    region VARCHAR NOT NULL,
    animal VARCHAR NOT NULL,
    "sub" VARCHAR NOT NULL,
    weight DOUBLE NOT NULL,
    stock_factor DOUBLE NOT NULL,
    mann_rel DOUBLE NOT NULL,
    technology VARCHAR NOT NULL,
    "group" VARCHAR NOT NULL,
    kappa1 DOUBLE NOT NULL,
    slope DOUBLE,
    thresh DOUBLE NOT NULL,
    ini DOUBLE NOT NULL,
    "max" DOUBLE NOT NULL,
    rH DOUBLE NOT NULL,
    rS DOUBLE NOT NULL,
    rA DOUBLE NOT NULL,
    g DOUBLE NOT NULL,
    fG DOUBLE NOT NULL,
    fH DOUBLE NOT NULL,
    fS DOUBLE NOT NULL,
    fA DOUBLE NOT NULL,
    lg DOUBLE,
    r_ch4 DOUBLE,
    PRIMARY KEY (region, animal, "sub", technology, "group")
);
COMMENT ON TABLE amm_ammonia_tech_model IS 'the ammonia technologies on the model''s animals: CAPRI''s options, weights and the N cascade terms (build_ammonia_tech_model.py) (tools/build/build_ammonia_tech_model.py)';
INSERT INTO value_units VALUES
  ('amm_ammonia_tech_model', 'weight', NULL, 'open', 'ammonia_tech_model weight'),
  ('amm_ammonia_tech_model', 'stock_factor', NULL, 'open', 'ammonia_tech_model stock_factor'),
  ('amm_ammonia_tech_model', 'mann_rel', NULL, 'open', 'ammonia_tech_model mann_rel'),
  ('amm_ammonia_tech_model', 'kappa1', NULL, 'open', 'ammonia_tech_model kappa1'),
  ('amm_ammonia_tech_model', 'slope', NULL, 'open', 'ammonia_tech_model slope'),
  ('amm_ammonia_tech_model', 'thresh', NULL, 'open', 'ammonia_tech_model thresh'),
  ('amm_ammonia_tech_model', 'ini', NULL, 'open', 'ammonia_tech_model ini'),
  ('amm_ammonia_tech_model', 'max', NULL, 'open', 'ammonia_tech_model max'),
  ('amm_ammonia_tech_model', 'rH', NULL, 'open', 'ammonia_tech_model rH'),
  ('amm_ammonia_tech_model', 'rS', NULL, 'open', 'ammonia_tech_model rS'),
  ('amm_ammonia_tech_model', 'rA', NULL, 'open', 'ammonia_tech_model rA'),
  ('amm_ammonia_tech_model', 'g', NULL, 'open', 'ammonia_tech_model g'),
  ('amm_ammonia_tech_model', 'fG', NULL, 'open', 'ammonia_tech_model fG'),
  ('amm_ammonia_tech_model', 'fH', NULL, 'open', 'ammonia_tech_model fH'),
  ('amm_ammonia_tech_model', 'fS', NULL, 'open', 'ammonia_tech_model fS'),
  ('amm_ammonia_tech_model', 'fA', NULL, 'open', 'ammonia_tech_model fA'),
  ('amm_ammonia_tech_model', 'lg', NULL, 'open', 'ammonia_tech_model lg'),
  ('amm_ammonia_tech_model', 'r_ch4', NULL, 'open', 'ammonia_tech_model r_ch4');

-- file: capri_data/2017/abatement/ammonia/ammonia_technologies.csv
CREATE TABLE amm_ammonia_technologies (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    CostParLin DOUBLE,
    CostParSqr DOUBLE,
    IniShare DOUBLE NOT NULL,
    MaxShare DOUBLE NOT NULL,
    qemitt DOUBLE,
    applicability DOUBLE NOT NULL,
    liquid_share DOUBLE NOT NULL,
    grazing_share DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, technology, target)
);
COMMENT ON TABLE amm_ammonia_technologies IS 'CAPRI''s ammonia technologies p_ghgMiti per CAPRI region and activity (envind/ammo_tech.gms; build_ammonia_technologies.py) (tools/build/build_ammonia_technologies.py)';
INSERT INTO value_units VALUES
  ('amm_ammonia_technologies', 'CostParLin', NULL, 'open', 'ammonia_technologies CostParLin'),
  ('amm_ammonia_technologies', 'CostParSqr', NULL, 'open', 'ammonia_technologies CostParSqr'),
  ('amm_ammonia_technologies', 'IniShare', NULL, 'open', 'ammonia_technologies IniShare'),
  ('amm_ammonia_technologies', 'MaxShare', NULL, 'open', 'ammonia_technologies MaxShare'),
  ('amm_ammonia_technologies', 'qemitt', NULL, 'open', 'ammonia_technologies qemitt'),
  ('amm_ammonia_technologies', 'applicability', NULL, 'open', 'ammonia_technologies applicability'),
  ('amm_ammonia_technologies', 'liquid_share', NULL, 'open', 'ammonia_technologies liquid_share'),
  ('amm_ammonia_technologies', 'grazing_share', NULL, 'open', 'ammonia_technologies grazing_share');

-- file: capri_data/2017/abatement/ammonia/bNumAniRAINS.csv
CREATE TABLE amm_bnumanirains (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    "year" INTEGER NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, "year")
);
COMMENT ON TABLE amm_bnumanirains IS 'animal numbers of the RAINS categories by year (MITERRA) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_bnumanirains', 'value', NULL, 'open', 'bNumAniRAINS value');

-- file: capri_data/2017/abatement/ammonia/capri_mann_days_2030.csv
CREATE TABLE amm_capri_mann_days_2030 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, "item")
);
COMMENT ON TABLE amm_capri_mann_days_2030 IS 'CAPRI''s 2030 levels, manure N and stable days per CAPRI region and activity (build_ammonia_herd_inputs.py) (tools/build/build_ammonia_herd_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_capri_mann_days_2030', 'value', NULL, 'open', 'capri_mann_days_2030 value');

-- file: capri_data/2017/abatement/ammonia/costs/p_addDemand.csv
CREATE TABLE amm_p_adddemand (
    technology VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    input VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (technology, animal_cat, manure_system, input)
);
COMMENT ON TABLE amm_p_adddemand IS 'additional input demand of the ammonia technologies (envind/ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_adddemand', 'value', NULL, 'open', 'p_addDemand value');

-- file: capri_data/2017/abatement/ammonia/costs/p_applic.csv
CREATE TABLE amm_p_applic (
    country VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (country, animal_cat, manure_system, technology)
);
COMMENT ON TABLE amm_p_applic IS 'applicability of the ammonia technologies by country (ammo_cost.gms), percent (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_applic', 'value', NULL, 'open', 'p_applic value');

-- file: capri_data/2017/abatement/ammonia/costs/p_costParAppl.csv
CREATE TABLE amm_p_costparappl (
    technology VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    coefficient VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (technology, animal_cat, manure_system, coefficient)
);
COMMENT ON TABLE amm_p_costparappl IS 'cost coefficients of the application techniques (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_costparappl', 'value', NULL, 'open', 'p_costParAppl value');

-- file: capri_data/2017/abatement/ammonia/costs/p_fixedOpCost.csv
CREATE TABLE amm_p_fixedopcost (
    technology VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (technology, animal_cat, manure_system)
);
COMMENT ON TABLE amm_p_fixedopcost IS 'fixed operating cost shares of the housing and storage techniques (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_fixedopcost', 'value', NULL, 'open', 'p_fixedOpCost value');

-- file: capri_data/2017/abatement/ammonia/costs/p_inputCost.csv
CREATE TABLE amm_p_inputcost (
    country VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (country, "item")
);
COMMENT ON TABLE amm_p_inputcost IS 'input prices of the ammonia cost model by country (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_inputcost', 'value', NULL, 'open', 'p_inputCost value');

-- file: capri_data/2017/abatement/ammonia/costs/p_invCoeff.csv
CREATE TABLE amm_p_invcoeff (
    technology VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    coefficient VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (technology, animal_cat, manure_system, coefficient)
);
COMMENT ON TABLE amm_p_invcoeff IS 'investment coefficients of the housing and storage techniques (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_invcoeff', 'value', NULL, 'open', 'p_invCoeff value');

-- file: capri_data/2017/abatement/ammonia/costs/p_kgNPerM3.csv
CREATE TABLE amm_p_kgnperm3 (
    activity VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (activity, manure_system)
);
COMMENT ON TABLE amm_p_kgnperm3 IS 'manure N content per m3 by activity and system (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_kgnperm3', 'value', NULL, 'open', 'p_kgNPerM3 value');

-- file: capri_data/2017/abatement/ammonia/costs/p_minStorCapND.csv
CREATE TABLE amm_p_minstorcapnd (
    region VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    nvz VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, manure_system, nvz, animal_cat)
);
COMMENT ON TABLE amm_p_minstorcapnd IS 'minimum storage capacity in and outside nitrate vulnerable zones, months (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_minstorcapnd', 'value', NULL, 'open', 'p_minStorCapND value');

-- file: capri_data/2017/abatement/ammonia/costs/p_sharGL.csv
CREATE TABLE amm_p_shargl (
    country VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (country, manure_system, animal_cat)
);
COMMENT ON TABLE amm_p_shargl IS 'share of grassland application by country (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_shargl', 'value', NULL, 'open', 'p_sharGL value');

-- file: capri_data/2017/abatement/ammonia/costs/p_storTime.csv
CREATE TABLE amm_p_stortime (
    region VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    animal_cat VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, manure_system, animal_cat)
);
COMMENT ON TABLE amm_p_stortime IS 'storage time by country, months (ammo_cost.gms) (tools/build/build_ammonia_cost_tables.py)';
INSERT INTO value_units VALUES
  ('amm_p_stortime', 'value', NULL, 'open', 'p_storTime value');

-- file: capri_data/2017/abatement/ammonia/n_cascade_effects.csv
CREATE TABLE amm_n_cascade_effects (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, technology, "item")
);
COMMENT ON TABLE amm_n_cascade_effects IS 'the technologies'' effects on the N cascade items per region and activity (envind/ghgMiti.gms; build_n_cascade.py) (tools/build/build_n_cascade.py)';
INSERT INTO value_units VALUES
  ('amm_n_cascade_effects', 'value', NULL, 'open', 'n_cascade_effects value');

-- file: capri_data/2017/abatement/ammonia/n_cascade_factors.csv
CREATE TABLE amm_n_cascade_factors (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    factor VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, activity, factor)
);
COMMENT ON TABLE amm_n_cascade_factors IS 'the N cascade factors per region and activity (build_n_cascade.py) (tools/build/build_n_cascade.py)';
INSERT INTO value_units VALUES
  ('amm_n_cascade_factors', 'value', NULL, 'open', 'n_cascade_factors value');

-- file: capri_data/2017/abatement/ammonia/n_cascade_region.csv
CREATE TABLE amm_n_cascade_region (
    region VARCHAR NOT NULL,
    factor VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, factor)
);
COMMENT ON TABLE amm_n_cascade_region IS 'the regional N cascade factors (build_n_cascade.py) (tools/build/build_n_cascade.py)';
INSERT INTO value_units VALUES
  ('amm_n_cascade_region', 'value', NULL, 'open', 'n_cascade_region value');

-- file: capri_data/2017/abatement/ammonia/n_leaching_region.csv
CREATE TABLE amm_n_leaching_region (
    region VARCHAR NOT NULL,
    leach_base DOUBLE,
    leach_ini DOUBLE NOT NULL,
    exp_imp DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE amm_n_leaching_region IS 'regional leaching fractions (build_n_leaching.py) (tools/build/build_n_leaching.py)';
INSERT INTO value_units VALUES
  ('amm_n_leaching_region', 'leach_base', NULL, 'open', 'n_leaching_region leach_base'),
  ('amm_n_leaching_region', 'leach_ini', NULL, 'open', 'n_leaching_region leach_ini'),
  ('amm_n_leaching_region', 'exp_imp', NULL, 'open', 'n_leaching_region exp_imp');

-- file: capri_data/2017/abatement/ammonia/p_Heads.csv
CREATE TABLE amm_p_heads (
    region VARCHAR NOT NULL,
    ad_activity VARCHAR NOT NULL,
    size_class VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, ad_activity, size_class)
);
COMMENT ON TABLE amm_p_heads IS 'heads by anaerobic-digestion activity and holding size class (build_ammonia_herd_inputs.py) (tools/build/build_ammonia_herd_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_heads', 'value', NULL, 'open', 'p_Heads value');

-- file: capri_data/2017/abatement/ammonia/p_factRunStor.csv
CREATE TABLE amm_p_factrunstor (
    manure_system VARCHAR NOT NULL,
    tech_class VARCHAR NOT NULL,
    storage_type VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (manure_system, tech_class, storage_type)
);
COMMENT ON TABLE amm_p_factrunstor IS 'storage run-off factors (LitRev_input_manStor) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_factrunstor', 'value', NULL, 'open', 'p_factRunStor value');

-- file: capri_data/2017/abatement/ammonia/p_fracStorType.csv
CREATE TABLE amm_p_fracstortype (
    region VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    storage_type VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, manure_system, storage_type)
);
COMMENT ON TABLE amm_p_fracstortype IS 'storage type shares (LitRev_input_manStor) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_fracstortype', 'value', NULL, 'open', 'p_fracStorType value');

-- file: capri_data/2017/abatement/ammonia/p_holdLSU.csv
CREATE TABLE amm_p_holdlsu (
    region VARCHAR NOT NULL,
    animal_group VARCHAR NOT NULL,
    size_class VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_group, size_class)
);
COMMENT ON TABLE amm_p_holdlsu IS 'holdings by livestock units size class (dat/scen/ghgtech/holdingsLSU) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_holdlsu', 'value', NULL, 'open', 'p_holdLSU value');

-- file: capri_data/2017/abatement/ammonia/p_litRevAmmoTechsAdd.csv
CREATE TABLE amm_p_litrevammotechsadd (
    region VARCHAR NOT NULL,
    technology VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    manure_system VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, technology, activity, manure_system, "item")
);
COMMENT ON TABLE amm_p_litrevammotechsadd IS 'literature-review side effects of four technologies (LitRevAmmoTech) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_litrevammotechsadd', 'value', NULL, 'open', 'p_litRevAmmoTechsAdd value');

-- file: capri_data/2017/abatement/ammonia/p_nvzShare_lu.csv
CREATE TABLE amm_p_nvzshare_lu (
    region VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region)
);
COMMENT ON TABLE amm_p_nvzshare_lu IS 'Nitrates-Directive zone share of the land (dat/envind/nvzShare_LU) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_p_nvzshare_lu', 'value', NULL, 'open', 'p_nvzShare_lu value');

-- file: capri_data/2017/abatement/ammonia/rLFRest.csv
CREATE TABLE amm_rlfrest (
    region VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, "item")
);
COMMENT ON TABLE amm_rlfrest IS 'MITERRA loss fractions of the rest (rLFRest) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_rlfrest', 'value', NULL, 'open', 'rLFRest value');

-- file: capri_data/2017/abatement/ammonia/reducControlStrategies.csv
CREATE TABLE amm_reduccontrolstrategies (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    strategy VARCHAR NOT NULL,
    "item" VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, strategy, "item")
);
COMMENT ON TABLE amm_reduccontrolstrategies IS 'emission reductions of the control strategies (reducControlStrategies) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_reduccontrolstrategies', 'value', NULL, 'open', 'reducControlStrategies value');

-- file: capri_data/2017/abatement/ammonia/reducEmHouse.csv
CREATE TABLE amm_reducemhouse (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    tech_class VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, gas, tech_class)
);
COMMENT ON TABLE amm_reducemhouse IS 'housing emission reductions, percent (reducEmHouse) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_reducemhouse', 'value', NULL, 'open', 'reducEmHouse value');

-- file: capri_data/2017/abatement/ammonia/reducEmStorage.csv
CREATE TABLE amm_reducemstorage (
    region VARCHAR NOT NULL,
    animal_mitt VARCHAR NOT NULL,
    gas VARCHAR NOT NULL,
    tech_class VARCHAR NOT NULL,
    "value" DOUBLE NOT NULL,
    PRIMARY KEY (region, animal_mitt, gas, tech_class)
);
COMMENT ON TABLE amm_reducemstorage IS 'storage emission reductions, percent (reducEmStorage) (tools/build/build_ammonia_tech_inputs.py)';
INSERT INTO value_units VALUES
  ('amm_reducemstorage', 'value', NULL, 'open', 'reducEmStorage value');

-- No rule on the region codes: CAPRI's MITERRA files carry codes outside RALL (other NUTS versions: Turkish and
-- Norwegian NUTS-2 regions, FR9x, HR03/HR04, SI01/SI02, LU000000), which the model's units do not read.

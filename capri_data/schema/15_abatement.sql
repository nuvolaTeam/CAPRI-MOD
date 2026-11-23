-- The mitigation options of the regional models: CAPRI's active technologies, the fertiliser options and their side
-- effects, the animal options (genetics, low-N feed, feed supplements), the winter cover option, the feed nutrient
-- contents and CAPRI's milk yield trends. Units in value_units (99_rules.sql); 'open' where no builder or CAPRI file
-- states one.

-- file: capri_data/2017/abatement/active_technologies.csv
CREATE TABLE active_technologies (
    "group" VARCHAR NOT NULL CHECK ("group" IN ('Amm', 'Fert', 'Feed', 'Carb', 'Other')),
    technology VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL
);
COMMENT ON TABLE active_technologies IS 'CAPRI''s activeTech of its Green Deal reference (gams/pol_input/greendeal/refpol_endotech_all_sup.gms; tools/build/build_active_technologies.py)';

-- file: capri_data/2017/abatement/fert_options_jul15.csv
CREATE TABLE fert_options_jul15 (
    region VARCHAR NOT NULL REFERENCES capri_rall (code),     -- a member state, or a unit for VRT_SRUC and VRT_KTBL
    option VARCHAR NOT NULL CHECK (option IN ('FERTTIME', 'NITR_INH', 'PRECFARM', 'VARRTECH_X', 'VRT_H', 'VRT_KTBL',
                                              'VRT_L', 'VRT_M', 'VRT_SRUC')),
    costParLin DOUBLE CHECK (costParLin > 0),
    costParSqr DOUBLE,
    pmpParSqr DOUBLE,
    revenue DOUBLE,
    relSubs0 DOUBLE CHECK (relSubs0 >= 0),
    relSubs1 DOUBLE CHECK (relSubs1 >= relSubs0),
    IniShare DOUBLE CHECK (IniShare BETWEEN 0 AND 1),
    MaxShare DOUBLE NOT NULL CHECK (MaxShare > 0 AND MaxShare <= 1),
    QEmitt DOUBLE CHECK (QEmitt > 0),
    QEmitt_noc DOUBLE NOT NULL CHECK (QEmitt_noc > 0),
    PRIMARY KEY (region, option)
);
COMMENT ON TABLE fert_options_jul15 IS 'CAPRI''s fertiliser mitigation options p_ghgMiti (cropMiti) of its July 2015 calibration file, national and, for the farm-size cost curves, regional (envind/ghgMiti.gms; tools/build/build_fert_options_jul15.py)';
INSERT INTO value_units VALUES
  ('fert_options_jul15', 'costParLin', NULL, 'open', 'p_ghgMiti costParLin'),
  ('fert_options_jul15', 'costParSqr', NULL, 'open', 'p_ghgMiti costParSqr'),
  ('fert_options_jul15', 'pmpParSqr', NULL, 'open', 'p_ghgMiti pmpParSqr'),
  ('fert_options_jul15', 'revenue', NULL, 'open', 'p_ghgMiti revenue'),
  ('fert_options_jul15', 'relSubs0', 'U_ratio', 'builder', 'subsidy at the initial share relative to costParLin'),
  ('fert_options_jul15', 'relSubs1', 'U_ratio', 'builder', 'subsidy at the maximum share relative to costParLin'),
  ('fert_options_jul15', 'IniShare', 'U_ratio', 'capri', 'p_ghgMiti IniShare, share of the activity'),
  ('fert_options_jul15', 'MaxShare', 'U_ratio', 'capri', 'p_ghgMiti MaxShare, share of the activity'),
  ('fert_options_jul15', 'QEmitt', NULL, 'open', 'p_ghgMiti QEmitt, emission factor with the option'),
  ('fert_options_jul15', 'QEmitt_noc', NULL, 'open', 'p_ghgMiti QEmitt of NOC, the emission factor without option');

-- file: capri_data/2017/abatement/fert_side_effects.csv
CREATE TABLE fert_side_effects (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    technology VARCHAR NOT NULL CHECK (technology IN ('NITR_INH', 'NITR_INH_MAN')),
    item VARCHAR NOT NULL CHECK (item IN ('N2OSYN', 'NH3SYN', 'NOXSYN', 'NH3APP', 'N2OAPP', 'NO3SLEA', 'NO3SRUN',
                                          'NO3MLEA', 'NO3MRUN')),
    value DOUBLE NOT NULL CHECK (value > -1 AND value < 1),
    capri_region VARCHAR NOT NULL,   -- the CAPRI region the value is from, or '<country> median' (rule below)
    PRIMARY KEY (region, technology, item)
);
COMMENT ON TABLE fert_side_effects IS 'CAPRI''s literature-review side effects of the inhibitors p_litRevFertTechs, weighted as envind/ghgMiti.gms l. 552-563 (tools/build/build_fert_side_effects.py)';
INSERT INTO value_units VALUES ('fert_side_effects', 'value', 'U_ratio', 'builder', 'relative change of the emission factor per kg N with the option');

-- rule: a side effect's source is a CAPRI region, or the median over a country's CAPRI regions (the builder's
-- registered rule for units CAPRI's file does not carry: NUTS 2016 splits, Norway)
SELECT region, capri_region FROM fert_side_effects
WHERE capri_region NOT IN (SELECT code FROM capri_rall)
  AND NOT (capri_region LIKE '% median' AND length(capri_region) = 9 AND substr(capri_region, 1, 2) = substr(region, 1, 2));

-- file: capri_data/2017/abatement/mitigation/p_nutCont.csv
CREATE TABLE p_nutCont (
    feed VARCHAR NOT NULL,
    nutrient VARCHAR NOT NULL,
    value DOUBLE NOT NULL CHECK (value >= 0),
    PRIMARY KEY (feed, nutrient)
);
COMMENT ON TABLE p_nutCont IS 'CAPRI''s feed nutrient contents p_nutCont (tools/build/build_mitigation_inputs.py)';
INSERT INTO value_units VALUES ('p_nutCont', 'value', NULL, 'open', 'per nutrient its own unit (energy, protein, dry matter, amino acids)');

-- file: capri_data/2017/abatement/mitigation/trends_milk_yield_1730.csv
CREATE TABLE trends_milk_yield_1730 (
    region VARCHAR NOT NULL,
    activity VARCHAR NOT NULL REFERENCES capri_pact (code) CHECK (activity IN ('DCOL', 'DCOH')),
    milk_yield_kg DOUBLE NOT NULL CHECK (milk_yield_kg > 0),
    PRIMARY KEY (region, activity)
);
COMMENT ON TABLE trends_milk_yield_1730 IS 'CAPRI''s 2030 milk yields of its trend projection per CAPRI region and dairy activity (tools/build/build_mitigation_inputs.py)';
INSERT INTO value_units VALUES ('trends_milk_yield_1730', 'milk_yield_kg', 'U_kgperhd', 'builder', 'milk per cow and year');

-- file: capri_data/2017/abatement/mitigation/winter_cover_option.csv
CREATE TABLE winter_cover_option (
    region VARCHAR PRIMARY KEY REFERENCES regional_units (region),
    capri_region VARCHAR NOT NULL REFERENCES capri_rall (code),
    uaar_kha DOUBLE NOT NULL CHECK (uaar_kha > 0),
    ini_share DOUBLE NOT NULL CHECK (ini_share BETWEEN 0 AND 1),
    max_share DOUBLE NOT NULL CHECK (max_share >= ini_share AND max_share <= 1),
    cost_lin_eur_ha DOUBLE NOT NULL CHECK (cost_lin_eur_ha >= 0),
    subs0 DOUBLE NOT NULL,
    subs1 DOUBLE NOT NULL,
    pmp_sqr DOUBLE NOT NULL CHECK (pmp_sqr > 0),
    pmp_lin DOUBLE NOT NULL,
    "case" INTEGER NOT NULL CHECK ("case" IN (1, 2, 3))
);
COMMENT ON TABLE winter_cover_option IS 'CAPRI''s winter cover option v_Miti(CATC, WinterCov, CO2SEQ) and its calibrated cost curve (cover_crops.gms l. 550-700; tools/build/build_winter_cover_option.py)';
INSERT INTO value_units VALUES
  ('winter_cover_option', 'uaar_kha', 'U_1000ha', 'builder', 'CAPRI''s UAAR'),
  ('winter_cover_option', 'ini_share', 'U_ratio', 'capri', 'IniShare, share of UAAR'),
  ('winter_cover_option', 'max_share', 'U_ratio', 'capri', 'MaxShare, share of UAAR'),
  ('winter_cover_option', 'cost_lin_eur_ha', 'U_EuPerHa', 'builder', 'costParLin per ha of UAAR'),
  ('winter_cover_option', 'subs0', 'U_EuPerHa', 'builder', 'Subs0 = relSubs0 x costParLin'),
  ('winter_cover_option', 'subs1', 'U_EuPerHa', 'builder', 'Subs1 = relSubs1 x costParLin'),
  ('winter_cover_option', 'pmp_sqr', 'U_EuPerHa', 'builder', 'pmpParSqr per unit of the share squared, per ha of UAAR'),
  ('winter_cover_option', 'pmp_lin', 'U_EuPerHa', 'builder', 'pmpParLin per unit of the share, per ha of UAAR'),
  ('winter_cover_option', 'case', NULL, 'open', 'the calibration case of cover_crops.gms (a category, no unit)');

-- file: capri_data/2017/abatement/mitigation/tillage_options.csv
CREATE TABLE tillage_options (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    technology VARCHAR NOT NULL CHECK (technology IN ('ConsTill', 'NoTill')),
    till_region VARCHAR NOT NULL CHECK (till_region IN ('North', 'Center', 'South')),
    tillage_kha DOUBLE NOT NULL CHECK (tillage_kha > 0),
    tillset_share DOUBLE NOT NULL CHECK (tillset_share > 0 AND tillset_share <= 1),
    ini_share DOUBLE NOT NULL CHECK (ini_share BETWEEN 0 AND 1),
    max_share DOUBLE NOT NULL CHECK (max_share >= ini_share AND max_share <= 1),
    cost_lin_eur_ha DOUBLE NOT NULL,
    costsaving0_eur_ha DOUBLE NOT NULL,
    max_increase DOUBLE NOT NULL CHECK (max_increase > 0 AND max_increase <= 1),
    relsubs0 DOUBLE NOT NULL,
    relsubs1 DOUBLE NOT NULL,
    subs0 DOUBLE NOT NULL,
    subs1 DOUBLE NOT NULL,
    pmp_sqr DOUBLE NOT NULL CHECK (pmp_sqr > 0),
    pmp_lin DOUBLE NOT NULL,
    "case" INTEGER NOT NULL CHECK ("case" IN (1, 2, 3, 4)),
    n2osyn DOUBLE NOT NULL CHECK (n2osyn <= 0),
    no3slea DOUBLE NOT NULL CHECK (no3slea <= 0),
    no3mlea DOUBLE NOT NULL CHECK (no3mlea <= 0),
    co2ero DOUBLE NOT NULL,
    PRIMARY KEY (region, technology)
);
COMMENT ON TABLE tillage_options IS 'CAPRI''s conservation and no tillage options v_Miti(cropMiti, ConsTill|NoTill, N2OSYN) per model region: the tillage area, the initial share (SAPM survey), costParLin, costsaving0 from CAPRI''s ini run, the calibrated cost curve (case 1-4) and the effects on the N2O of mineral N, the leaching of soil and manure N and erosion (envind/tillage.gms l. 314-849; tools/build/build_tillage_options.py)';
INSERT INTO value_units VALUES
  ('tillage_options', 'tillage_kha', 'U_1000ha', 'builder', 'the levels of the tillage crops (CFACTOR_ARAB) at CAPRI''s 2030 baseline'),
  ('tillage_options', 'tillset_share', 'U_ratio', 'builder', 'DATA(ru, UAAR, TILLSET): the tillage area over the crop area'),
  ('tillage_options', 'ini_share', 'U_ratio', 'capri', 'IniShare, share of the tillage area'),
  ('tillage_options', 'max_share', 'U_ratio', 'capri', 'MaxShare, share of the tillage area'),
  ('tillage_options', 'cost_lin_eur_ha', 'U_EuPerHa', 'capri', 'costParLin per ha of tillage area, the base year''s money (CAPRI''s inflation to 2030 and the model''s deflator cancel)'),
  ('tillage_options', 'costsaving0_eur_ha', 'U_EuPerHa', 'builder', 'costsaving0: the ini run''s v_Miti.m per ha of tillage area, over the model''s deflator(2030)'),
  ('tillage_options', 'max_increase', 'U_ratio', 'capri', 'MaxIncrease, share of the tillage area'),
  ('tillage_options', 'relsubs0', 'U_ratio', 'capri', 'relSubs0, relative to costParLin'),
  ('tillage_options', 'relsubs1', 'U_ratio', 'capri', 'relSubs1, relative to costParLin'),
  ('tillage_options', 'subs0', 'U_EuPerHa', 'builder', 'Subs0 per ha of tillage area'),
  ('tillage_options', 'subs1', 'U_EuPerHa', 'builder', 'Subs1 per ha of tillage area'),
  ('tillage_options', 'pmp_sqr', 'U_EuPerHa', 'builder', 'pmpParSqr per unit of the share squared, per ha of tillage area'),
  ('tillage_options', 'pmp_lin', 'U_EuPerHa', 'builder', 'pmpParLin per unit of the share, per ha of tillage area'),
  ('tillage_options', 'case', NULL, 'open', 'the calibration case of tillage.gms (a category, no unit)'),
  ('tillage_options', 'n2osyn', 'U_ratio', 'capri', 'othImpact N2OSYN: relative change of the N2O of mineral N at share 1'),
  ('tillage_options', 'no3slea', 'U_ratio', 'capri', 'othImpact NO3SLEA x tillset_share: relative change of the leaching of soil N at share 1'),
  ('tillage_options', 'no3mlea', 'U_ratio', 'capri', 'othImpact NO3MLEA x tillset_share: relative change of the leaching of manure N at share 1'),
  ('tillage_options', 'co2ero', NULL, 'open', 'othImpact CO2ERO: the erosion factor tillage.gms sets (l. 547-549; no unit stated)');

-- file: capri_data/2017/abatement/mitigation/urea_subst_option.csv
CREATE TABLE urea_subst_option (
    ms VARCHAR PRIMARY KEY REFERENCES capri_rall (code),
    frac_urea DOUBLE NOT NULL CHECK (frac_urea > 0 AND frac_urea <= 1),
    max_share DOUBLE NOT NULL CHECK (max_share > 0 AND max_share <= 1),
    nh3_othimpact DOUBLE NOT NULL,
    cost_lin_eur_t DOUBLE NOT NULL,
    relsubs0 DOUBLE NOT NULL,
    relsubs1 DOUBLE NOT NULL,
    subs0 DOUBLE NOT NULL,
    subs1 DOUBLE NOT NULL,
    pmp_sqr DOUBLE NOT NULL CHECK (pmp_sqr > 0),
    pmp_lin DOUBLE NOT NULL,
    "case" INTEGER NOT NULL CHECK ("case" IN (3, 4))
);
COMMENT ON TABLE urea_subst_option IS 'CAPRI''s urea substitution v_Miti(cropMiti, UreaSubst, NH3SYN) per member state: MaxShare the urea share of mineral N, the NH3 factor difference, the cost per t of N switched and the calibrated cost curve (envind/ammo_tech.gms l. 2353-2375, 2840-2977, 3041-3047, 3100-3107; tools/build/build_urea_subst_option.py)';
INSERT INTO value_units VALUES
  ('urea_subst_option', 'frac_urea', 'U_ratio', 'capri', 'p_fracUseFert(ms, Ureum)'),
  ('urea_subst_option', 'max_share', 'U_ratio', 'capri', 'MaxShare, share of the mineral N bought'),
  ('urea_subst_option', 'nh3_othimpact', 'U_ratio', 'capri', 'othImpact NH3SYN: the NH3 emission factor of urea less the others'''),
  ('urea_subst_option', 'cost_lin_eur_t', 'U_EuPerTon', 'builder', 'costParLin per t of N switched: CAPRI''s base-year figure (not inflated, ammo_tech.gms) over the model''s deflator(2030)'),
  ('urea_subst_option', 'relsubs0', 'U_ratio', 'capri', 'relSubs0, relative to costParLin'),
  ('urea_subst_option', 'relsubs1', 'U_ratio', 'capri', 'relSubs1, relative to costParLin'),
  ('urea_subst_option', 'subs0', 'U_EuPerTon', 'builder', 'Subs0 per t of N bought'),
  ('urea_subst_option', 'subs1', 'U_EuPerTon', 'builder', 'Subs1 per t of N bought'),
  ('urea_subst_option', 'pmp_sqr', 'U_EuPerTon', 'builder', 'pmpParSqr per unit of the share squared, per t of N bought'),
  ('urea_subst_option', 'pmp_lin', 'U_EuPerTon', 'builder', 'pmpParLin per unit of the share, per t of N bought'),
  ('urea_subst_option', 'case', NULL, 'open', 'the calibration case of ammo_tech.gms (a category, no unit)');

-- file: capri_data/2017/abatement/mitigation/legsh_option.csv
CREATE TABLE legsh_option (
    region VARCHAR PRIMARY KEY REFERENCES regional_units (region),
    ms VARCHAR NOT NULL REFERENCES capri_rall (code),
    fleg_share DOUBLE NOT NULL CHECK (fleg_share BETWEEN 0 AND 1),
    nfix_rate_gras DOUBLE NOT NULL CHECK (nfix_rate_gras > 0 AND nfix_rate_gras < 0.15),
    biofix_ofar DOUBLE NOT NULL CHECK (biofix_ofar > 0 AND biofix_ofar < 1),
    othimpact_biofix DOUBLE NOT NULL CHECK (othimpact_biofix > 0),
    data_nitf_ofar DOUBLE NOT NULL CHECK (data_nitf_ofar > 0),
    mult_fact_nitf DOUBLE NOT NULL CHECK (mult_fact_nitf > 0),
    add_fact_nitf DOUBLE NOT NULL,
    need_share DOUBLE NOT NULL CHECK (need_share > 0 AND need_share < 1),
    cost_lin_eur_ha DOUBLE NOT NULL CHECK (cost_lin_eur_ha > 0),
    pmp_lin DOUBLE NOT NULL,
    pmp_sqr DOUBLE NOT NULL CHECK (pmp_sqr > 0),
    subs0 DOUBLE NOT NULL,
    subs1 DOUBLE NOT NULL,
    max_share DOUBLE NOT NULL CHECK (max_share > 0 AND max_share <= 1)
);
COMMENT ON TABLE legsh_option IS 'CAPRI''s increased legume share in temporary grassland v_Miti(OFAR, LegSh, BioFix) per model region: othImpact BioFix, the share of other arable fodder''s N need it removes, and its cost per ha of OFAR (envind/leg_share.gms l. 33-47, miti_data_jul15; tools/build/build_legsh_option.py)';
INSERT INTO value_units VALUES
  ('legsh_option', 'fleg_share', 'U_ratio', 'capri', 'DATA(r, FLEG, LEVL, BAS): the fodder legumes'' share of other arable fodder'),
  ('legsh_option', 'nfix_rate_gras', 'U_ratio', 'capri', 'p_nfixRate_gras of the member state (fertpar.gms; the GRAE rate where none)'),
  ('legsh_option', 'biofix_ofar', 'U_ratio', 'capri', 'p_nitrFact(r, OFAR, BioFix)'),
  ('legsh_option', 'othimpact_biofix', 'U_ratio', 'capri', 'othImpact BioFix of the member state: the relative change of OFAR''s fixation at share 1'),
  ('legsh_option', 'data_nitf_ofar', 'U_kgperha', 'capri', 'DATA(r, OFAR, NITF, Y), fertned.gms'),
  ('legsh_option', 'mult_fact_nitf', 'U_ratio', 'capri', 'v_cropNutNeedMultFact(r, NITF, T)'),
  ('legsh_option', 'add_fact_nitf', 'U_kgperha', 'capri', 'v_cropNutNeedAddFact(r, NITF)'),
  ('legsh_option', 'need_share', 'U_ratio', 'builder', 'the share of OFAR''s N need in NUTNED_ removed at share 1'),
  ('legsh_option', 'cost_lin_eur_ha', 'U_EuPerHa', 'builder', 'costParLin per ha of OFAR x (1 - FLEG), the base year''s money'),
  ('legsh_option', 'pmp_lin', 'U_EuPerHa', 'builder', 'pmpParLin per ha of OFAR x (1 - FLEG), without p_fertCostGains'),
  ('legsh_option', 'pmp_sqr', 'U_EuPerHa', 'builder', 'pmpParSqr per unit of the share squared, per ha of OFAR x (1 - FLEG)'),
  ('legsh_option', 'subs0', 'U_EuPerHa', 'builder', 'Subs0 per ha of OFAR x (1 - FLEG)'),
  ('legsh_option', 'subs1', 'U_EuPerHa', 'builder', 'Subs1 per ha of OFAR x (1 - FLEG)'),
  ('legsh_option', 'max_share', 'U_ratio', 'capri', 'MaxShare, share of OFAR');

-- the three animal option tables share their effect columns: relative changes per unit of the option's parameter
-- file: capri_data/2017/abatement/mitigation/genetics_effects.csv
CREATE TABLE genetics_effects (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    option VARCHAR NOT NULL CHECK (option IN ('genet_yld', 'genet_eff')),
    tech_param VARCHAR NOT NULL CHECK (tech_param IN ('ghgTechMYld', 'ghgTechFEff')),
    elig_share DOUBLE NOT NULL CHECK (elig_share > 0 AND elig_share <= 1),
    d_milk_rel DOUBLE NOT NULL, d_ener_rel DOUBLE NOT NULL, d_crpr_rel DOUBLE NOT NULL, d_drmn_rel DOUBLE NOT NULL,
    d_drmx_rel DOUBLE NOT NULL, d_mann_rel DOUBLE NOT NULL,
    cost_floor DOUBLE NOT NULL CHECK (cost_floor >= 0),
    cost_per_unit DOUBLE NOT NULL CHECK (cost_per_unit >= 0),
    relsubs0 DOUBLE NOT NULL CHECK (relsubs0 >= 0),
    relsubs1 DOUBLE NOT NULL CHECK (relsubs1 > relsubs0),
    max_share DOUBLE NOT NULL CHECK (max_share > 0 AND max_share <= 1),
    dsav DOUBLE,
    PRIMARY KEY (region, animal, option)
);
COMMENT ON TABLE genetics_effects IS 'CAPRI''s breeding options (envind/breeding.gms) on the model''s animals (tools/build/build_genetics_effects.py)';

-- file: capri_data/2017/abatement/mitigation/lownfeed_effects.csv
CREATE TABLE lownfeed_effects (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    option VARCHAR NOT NULL CHECK (option = 'lowNFeed'),
    tech_param VARCHAR NOT NULL CHECK (tech_param = 'ghgTechLowNFeed'),
    elig_share DOUBLE NOT NULL CHECK (elig_share > 0 AND elig_share <= 1),
    d_milk_rel DOUBLE NOT NULL, d_ener_rel DOUBLE NOT NULL, d_crpr_rel DOUBLE NOT NULL CHECK (d_crpr_rel <= 0),
    d_drmn_rel DOUBLE NOT NULL, d_drmx_rel DOUBLE NOT NULL, d_mann_rel DOUBLE NOT NULL CHECK (d_mann_rel <= 0),
    cost_floor DOUBLE NOT NULL CHECK (cost_floor >= 0),
    cost_per_unit DOUBLE NOT NULL CHECK (cost_per_unit >= 0),
    relsubs0 DOUBLE NOT NULL CHECK (relsubs0 >= 0),
    relsubs1 DOUBLE NOT NULL CHECK (relsubs1 > relsubs0),
    gamma_floor DOUBLE NOT NULL CHECK (gamma_floor > 0),
    dsav DOUBLE NOT NULL,
    PRIMARY KEY (region, animal, option)
);
COMMENT ON TABLE lownfeed_effects IS 'CAPRI''s low-protein feeding option LowNFeed (envind/low_n_feed.gms) on the model''s animals (tools/build/build_lownfeed_effects.py)';

-- file: capri_data/2017/abatement/mitigation/supplement_effects.csv
CREATE TABLE supplement_effects (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    option VARCHAR NOT NULL CHECK (option IN ('LINE_Tot', 'Nitr_Tot', '3NOP_Tot')),
    tech_param VARCHAR NOT NULL CHECK (tech_param = 'ghgTechLineNitr'),
    param_switch INTEGER NOT NULL CHECK (param_switch IN (0, 1)),
    elig_share DOUBLE NOT NULL CHECK (elig_share > 0 AND elig_share <= 1),
    d_milk_rel DOUBLE NOT NULL, d_ener_rel DOUBLE NOT NULL, d_crpr_rel DOUBLE NOT NULL, d_drmn_rel DOUBLE NOT NULL,
    d_drmx_rel DOUBLE NOT NULL, d_mann_rel DOUBLE NOT NULL,
    cost_floor DOUBLE NOT NULL CHECK (cost_floor >= 0),
    cost_per_unit DOUBLE NOT NULL CHECK (cost_per_unit > 0),
    relsubs0 DOUBLE NOT NULL CHECK (relsubs0 >= 0),
    relsubs1 DOUBLE NOT NULL CHECK (relsubs1 > relsubs0),
    gamma_floor DOUBLE NOT NULL CHECK (gamma_floor > 0),
    ch4ent_rel DOUBLE NOT NULL CHECK (ch4ent_rel > -1 AND ch4ent_rel <= 0),
    shr_of_dm DOUBLE NOT NULL CHECK (shr_of_dm > 0 AND shr_of_dm < 1),
    dm_intake DOUBLE NOT NULL CHECK (dm_intake > 0),
    dsav DOUBLE NOT NULL,
    PRIMARY KEY (region, animal, option)
);
COMMENT ON TABLE supplement_effects IS 'CAPRI''s feed supplements linseed, nitrate and 3-NOP (envind/line_nitr.gms) on the model''s animals, on CAPRI''s 2030 requirements per activity (sim_ini_21730 p_animReq; tools/build/build_supplement_effects.py)';

INSERT INTO value_units SELECT t, c, 'U_ratio', 'builder', 'relative change per unit of the option''s parameter'
FROM (VALUES ('genetics_effects'), ('lownfeed_effects'), ('supplement_effects')) a(t),
     (VALUES ('d_milk_rel'), ('d_ener_rel'), ('d_crpr_rel'), ('d_drmn_rel'), ('d_drmx_rel'), ('d_mann_rel'),
             ('elig_share'), ('relsubs0'), ('relsubs1')) b(c);
INSERT INTO value_units SELECT t, c, 'U_EuPerHd', 'builder', 'EUR per head adopting (cost = max(floor, per unit x parameter)); dsav: CAPRI''s cost-saving drop between its two calibration runs'
FROM (VALUES ('genetics_effects'), ('lownfeed_effects'), ('supplement_effects')) a(t),
     (VALUES ('cost_floor'), ('cost_per_unit'), ('dsav')) b(c);
INSERT INTO value_units VALUES
  ('genetics_effects', 'max_share', 'U_ratio', 'capri', 'MaxShare of breeding.gms (0.002, its cap)'),
  ('lownfeed_effects', 'gamma_floor', 'U_ratio', 'builder', 'floor of the curvature relative to costParLin'),
  ('supplement_effects', 'gamma_floor', 'U_ratio', 'builder', 'floor of the curvature relative to costParLin'),
  ('supplement_effects', 'ch4ent_rel', 'U_ratio', 'builder', 'relative change of enteric CH4 of the adopting animals'),
  ('supplement_effects', 'shr_of_dm', 'U_ratio', 'capri', 'ShrOfDM, the supplement''s share of dry matter'),
  ('supplement_effects', 'dm_intake', 'U_kgperhd', 'builder', 'dry-matter intake per head and year: 365 x CAPRI''s 2030 p_animReq(DRMA) of the animal''s activities, weighted by their places (LEVL x DAYS / 365)'),
  ('supplement_effects', 'param_switch', NULL, 'open', 'a switch (1 on)');

-- file: capri_data/2017/abatement/mitigation/supplement_fat.csv
CREATE TABLE supplement_fat (
    region VARCHAR NOT NULL REFERENCES regional_units (region),
    animal VARCHAR NOT NULL REFERENCES model_activities (code),
    feed VARCHAR NOT NULL,
    ee DOUBLE NOT NULL CHECK (ee >= 0 AND ee < 100),
    dm_content DOUBLE NOT NULL CHECK (dm_content >= 0 AND dm_content <= 1),
    tot_fat DOUBLE NOT NULL CHECK (tot_fat >= 0 AND tot_fat < 1),
    PRIMARY KEY (region, animal, feed)
);
COMMENT ON TABLE supplement_fat IS 'The fat of the feed bulks per model region and cattle animal with linseed, the data of CAPRI''s ration fat limit SupplementPerc_ (supply_model.gms l. 608-633): ether extract (envind/digestibility.gms), dry-matter content and p_emisFeed TotFAT (envind/line_nitr.gms l. 175-176; tools/build/build_supplement_fat.py)';
INSERT INTO value_units VALUES
  ('supplement_fat', 'ee', 'U_percent', 'capri', 'p_digestPar(RU, CATACT, FEED, EE): the feed bulk''s ether extract, % of dry matter'),
  ('supplement_fat', 'dm_content', 'U_ratio', 'capri', 'p_DryMatterContent(RU, FEED): dry matter per kg as fed'),
  ('supplement_fat', 'tot_fat', 'U_ratio', 'builder', 'p_emisFeed(RU, CATACT, T, FEED, TotFAT): kg of fat per kg as fed');

-- rule: the active technologies' options the model builds are in CAPRI's file
SELECT option FROM (SELECT DISTINCT upper(option) AS option FROM fert_options_jul15) f
WHERE option NOT IN (SELECT upper(technology) FROM active_technologies)
  AND option NOT IN ('VARRTECH_X', 'VRT_H', 'VRT_KTBL', 'VRT_L', 'VRT_M');

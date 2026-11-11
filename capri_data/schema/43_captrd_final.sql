-- Sets of the last steps of CAPTRD's supports (captrd/adjust_to_biof_supports.gms and adjust_trade_supports.gms,
-- included by captrd/define_stats_and_supports.gms l. 597, 627; capri_mod/pipeline/captrd/final_supports.py), by
-- tools/build/build_captrd_sets.py.

-- file: capri_data/pipeline/captrd/sets/oseeds.csv
CREATE TABLE ctrd_oseeds (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_oseeds IS 'CAPTRD''s own set Oseeds (oilseeds as outputs; gams/captrd/sets_captrd.gms l. 262-266): one member per row in d0, 3 members (RAPE, SUNF, SOYA); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/tradeest.csv
CREATE TABLE ctrd_tradeest (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_tradeest IS 'CAPTRD''s own set tradeEst (the trade positions estimated; gams/captrd/sets_captrd.gms l. 314-316): one member per row in d0, 3 members (IMPT, EXPT, NTRD); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/shiftsugbpos.csv
CREATE TABLE ctrd_shiftsugbpos (
    d0 VARCHAR NOT NULL,
    PRIMARY KEY (d0)
);
COMMENT ON TABLE ctrd_shiftsugbpos IS 'CAPTRD''s own set ShiftSugbPos (the sugar beet positions shifted along with GROF; gams/captrd/sets_captrd.gms l. 323-325): one member per row in d0, 6 members (e.g. FEDM, INDM, EAAG); transcribed in tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/sed_to_oil.csv
CREATE TABLE ctrd_sed_to_oil (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_sed_to_oil IS 'The mapping SED_TO_OIL (oilseeds to their oils; gams/captrd/sets_captrd.gms l. 287): one pair per row (d0, d1), 3 pairs (e.g. RAPE.RAPO); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730), whose members are the same, by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/oil_to_cak.csv
CREATE TABLE ctrd_oil_to_cak (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_oil_to_cak IS 'The mapping OIL_TO_CAK (oils to their cakes; gams/captrd/sets_captrd.gms l. 289): one pair per row (d0, d1), 3 pairs (e.g. RAPO.RAPC); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730), whose members are the same, by tools/build/build_captrd_sets.py.';

-- file: capri_data/pipeline/captrd/sets/bio_prcd.csv
CREATE TABLE ctrd_bio_prcd (
    d0 VARCHAR NOT NULL,
    d1 VARCHAR NOT NULL,
    PRIMARY KEY (d0, d1)
);
COMMENT ON TABLE ctrd_bio_prcd IS 'CAPRI''s global mapping BIO_PRCD (biofuels to their feedstocks; gams/sets.gms l. 4981): one pair per row (d0, d1), 12 pairs (e.g. BIOE.MAIZ, BIOD.RAPO); copied from CAPRI''s instantiation in sim_ini_21730 (capri_reference/sets/simini_21730) by tools/build/build_captrd_sets.py.';

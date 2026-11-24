"""CAPRI's supply/supply_model.gms (star 3.0, 5,631 lines), one module per block of the file.

Each module holds the equations of one of CAPRI's blocks, as the file's own banners divide it, one function per
equation named as CAPRI's equation (or as the equation's term the function writes, under its equation), with CAPRI's
GAMS statement, its file and lines, the equation in this project's notation and the departures in the docstrings. The
232 equations of CAPRI's simulation model m_capModQ, the block each belongs to and whether CAPRI's 2030 Green Deal
step has it: docs/dev/supply_equations_inventory.csv (planned_module). A module is added when its first equation is
written.

    module          CAPRI block (supply/supply_model.gms)                                           lines
    feeding.py      the feeding block: REQSE_, FEDUSE_; the rows of the feed calibration's model     520-840
                    m_hpdFeed (NutContFeed_, FeedAggrShare_, FEDUSEA_, FEDUSES_, FEDAGGR_)
    nutrients.py    the fertilising block: the pools (fertDistExcr_, fertDistMine_, fertDistCres_,  870-1279
                    ManureNPK_), NUTNED_
    n_surplus.py    the nutrient surplus: e_EXCRET, e_GASRUNANI, e_ATMOSD, e_CRESID, e_EXPPRD,      1280-1497,
                    e_BIOFIX, e_SURTOTHa's idled histosols; nminInputSh_, nmanInputSh_;           1791-1886
                    SURTOT_REST_
    inner_fert.py   the inner fertiliser model: e_fertDistPartial, e_fertDistPartialRegu,          1498-1790
                    e_fertDistReguMax, e_focFertDist
    n_flow.py       the nitrogen flow: the manure N loss cascade (GRAZN_, HOUSN_, STORN_,           3206-3471
                    RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_) and mineral N's
                    (GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_); the leaching (LEACHN_, AMMOAGG_)
    fert_limits.py  the fertiliser application limits: e_synNMax                                  4501-4601
    markets.py      the market balances: SUPBAL_ (the non-tradable fodder)                         4602-4674
    objective.py    the objective: LINEAR_'s terms (the mineral N purchases, the activities' net    4675-5056,
                    revenues); QUADRF_ with QUADRF1_, QUADRA_ with GRPLEVL_, OBJEQF_              5358-5433
    mitigation.py   the mitigation options: GHG_Mit_Cost_ (the targFertMan and targFertSyn bases)  4130-4392,
                                                                                                  5057-5357
    premiums.py     the premiums: winterCover_, catcMiti_, ecoSetAside_'s catch crops,              1887-2026
                    overShotEntl_ (with sumEntl_), permGrasGreening_
    set_aside.py    the set-aside block: e_setaLandscape, idleHisto_                               2225-2375
    land.py         the land block: LandBalNoSlak_, e_artoBal; the LUC estimation (e_FocLUC,       2376-2534,
                    e_luClassInitial, e_luClassFinal); LandMarket_ (the objective's block)        4903-4914
    methane.py      the methane block: GWPCH4ENT_, GWPCH4MAN_ (with their aact rows)              3062-3205
    air_water.py    NH3, NOx and NO3: NH3MAN_, NH3TOT_, NO3RUN_, NO3LEA_                          3472-3633
    n2o.py          the N2O block: GWPN2OMAN_, GWPN2OSYN_, GWPN2OCRO_, GWPN2OAMM_, GWPN2OHIS_,    3634-3966
                    GWPN2OLEA_
    gwp.py          CO2 and the total: GWPCO2LIM_, GWPCO2UREA_, GWPTOT_                            3966-4015

The other blocks, by the inventory, have no function: young_animals.py (841-869; INPANI_ in the net revenues),
lulucf.py (2656-3061, 4016-4129; not in the model), sugar.py (5434-5498; empty in the step); the BFP indicators
(2027-2224), the water block (2535-2655) and the pesticide block (4393-4500) are off in CAPRI's 2030 Green Deal step.
"""

"""CAPRI's crop nutrient data in the simulation year, as fert/fertned.gms sets them.

capmod/def_fert_and_requirements.gms runs fert/fertned.gms in the simulation year ($BATINCLUDE 'fert/fertned.gms'
MCACT, l. 134), after l. 126 has set DATA(RS,MCACT,"O_HP","Y") = 0 for the crops with a level and after
fert/fertpar.gms (l. 121; this package's fertpar.py) has set the fixation rates. fertned.gms then rebuilds, for every
crop and region, the nutrient content of the crop's outputs per ha, DATA(RS,crop,FNUT,"Y") (NITF, PHOF, POTF: the
removal of e_EXPPRD and the need of NUTNED_, supply/supply_model.gms l. 1095-1137, 1417-1434) and its deliveries to the
soil, DATA(RS,crop,FOUT,"Y") (MANN, MANP, MANK: deposition, mineralisation and crop residues, e_CRESID l. 1393-1414,
and the residue pool fertDistCres_). CAPRI's global setting CropResi_IDEAG_NG is off in the simulation
(capmod/set_global_variables.gms l. 218), so fertned's "old code" branches hold.

The functions below follow fertned.gms statement by statement (the CAPRI file and lines in each docstring). They work on
one region and crop at a time; the sets are CAPRI's (sets.gms): PACT_TO_Y (l. 5377-5456, the crop's main outputs
curRows), FODF (l. 5606, the fodder outputs OFAR, GRAS, ROOF, MAIF), FOUT_T_N (l. 5501-5502, MANN.NITF, MANP.PHOF,
MANK.POTF), doubleMaxf (fert/fertpar.gms l. 393). Used by tools/build/build_capri_crop_n_coefs.py on CAPRI's 2030
simulation data (sim_ini_21730's DATA at "Y"), whose results the gross N balance's crop terms take
(capri_mod/environmental/nitrogen.py, _capri_crop_n; KNOWN_ISSUES K191).

DATA_FNUT (the K185 rule for the crops without a main output) stays as it was.
"""
from __future__ import annotations

#: the arguments of fertned_at_yields that CAPRI's data fix, in its order: the columns of
#: capri_crop_fertned_parts_2030.csv (tools/build/build_capri_crop_n_coefs.py)
FERTNED_PARTS = ("o_hp", "stra", "need_main", "need_stra", "maxf", "double_maxf", "resid_rel", "resid_pact", "losf_stra",
                 "grof_stra")


def O_HP(yield_RS: float, LEVL: float, O_HP_MS: float = None, yield_MS: float = None) -> float:
    r"""The crop's main-output yield fertned uses (O_HP, kg per ha of the main output) in the simulation year.

    CAPRI's GAMS (capmod/def_fert_and_requirements.gms l. 126):

          DATA(RS,MCACT,"O_HP","Y") $ DATA(RS,MCACT,"LEVL","Y")  = 0;

    CAPRI's GAMS (fert/fertned.gms l. 82-96):

           p_dataCopy(RS,%pacts%,"O_HP",%Y%) $ (not p_dataCopy(RS,%pacts%,"LEVL",%Y%)) = 0;
           p_dataCopy(RS,%pacts%,"O_HP",%Y%)
              $ ( (NOT SUM( PACT_TO_Y(%pacts%,curRows), p_dataCopy(RS,%pacts%,curRows,%Y%))) $ p_dataCopy(RS,%pacts%,"LEVL",%Y%)) = 0;
           p_dataCopy(MS,%pacts%,"O_HP",%Y%) $ (NOT p_dataCopy(MS,%pacts%,"O_HP",%Y%))
                = SUM( PACT_TO_Y(%pacts%,curRows), p_dataCopy(MS,%pacts%,curRows,%Y%));
           p_dataCopy(RS,%pacts%,"O_HP",%Y%) $ ( (NOT p_dataCopy(RS,%pacts%,"O_HP",%Y%)) $ p_dataCopy(RS,%pacts%,"LEVL",%Y%))
                  = SUM(PACT_TO_Y(%pacts%,curRows), p_dataCopy(RS,%pacts%,curRows,%Y%)
                          * SUM(Map_RR(MS,RS), p_dataCopy(MS,%pacts%,"O_HP",%Y%)/p_dataCopy(MS,%pacts%,curRows,%Y%)))
                                      $ SUM(Map_RR(MS,RS), p_dataCopy(MS,%pacts%,"O_HP",%Y%));

    In this project's notation, y the main-output yield (the sum over PACT_TO_Y) of region r and of its member state:

        O_HP(r) = y(r) x O_HP(ms) / y(ms),  O_HP(ms) = y(ms) (zeroed at l. 126, so rebuilt from the yield)
                = y(r)

    so in the simulation year the "smoothed" yield is the year's yield. yield_MS and O_HP_MS: the member state's
    (None: O_HP(ms) = y(ms), as in the simulation). Zero without a level or a yield."""
    if not (float(LEVL or 0.0) > 0.0) or not (float(yield_RS or 0.0) > 0.0):
        return 0.0
    if O_HP_MS is None or yield_MS is None or not float(yield_MS) > 0.0:
        return float(yield_RS)
    return float(yield_RS) * float(O_HP_MS) / float(yield_MS)


def p_residRel(content: float, Resid: float, fodder: bool) -> float:
    r"""The nutrient of the crop residues over that of the residues and the main harvested product (fertned.gms, old
    code, CropResi_IDEAG_NG off).

    CAPRI's GAMS (fert/fertned.gms l. 130-140):

           p_residRel(RS,curRows,FNUT_COLS,%Y%) $ ([p_dataCopy(RS,FNUT_COLS,curRows,%Y%)+RESID(curRows,FNUT_COLS)] $ Resid(curRows,FNUT_COLS))
               = Resid(curRows,FNUT_COLS)
               /(p_dataCopy(RS,FNUT_COLS,curRows,%Y%)+Resid(curRows,FNUT_COLS));
           p_residRel(RS,FODF,FNUT_COLS,%Y%) $ ([p_dataCopy(RS,FNUT_COLS,FODF,%Y%)+RESID(FODF,FNUT_COLS)] $ Resid(FODF,FNUT_COLS))
               = .5*Resid(FODF,FNUT_COLS)
               /(p_dataCopy(RS,FNUT_COLS,FODF,%Y%)+.5*Resid(FODF,FNUT_COLS));

    In this project's notation, c the nutrient content of the output (kg per t: DATA(r, FNUT, output, "Y")), R its
    residues' content (Resid, kg per t of harvested material: def_gascoeff.py Resid), the fodder outputs (FODF) taking half
    of R (CAPRI's note: the other half is the above-ground losses, LOSF, added at l. 228, p_residRel_LOSF):

        rr = R / (c + R)            rr = 0.5 R / (c + 0.5 R)  for fodder

    Zero without residues (R = 0: the cereals but maize)."""
    R = float(Resid or 0.0) * (0.5 if fodder else 1.0)
    c = float(content or 0.0)
    return R / (c + R) if (R > 0.0 and c + R > 0.0) else 0.0


def p_cropNeed(content: float, residRel: float) -> float:
    r"""The nutrient per t of main output, residues included (kg per t).

    CAPRI's GAMS (fert/fertned.gms l. 150-151):

           p_cropNeed(RS,curRows,FNUT_COLS,%Y%) $ ([p_residRel(RS,curRows,FNUT_COLS,%Y%) LT 1] $ p_dataCopy(RS,FNUT_COLS,curRows,%Y%))
                = p_dataCopy(RS,FNUT_COLS,curRows,%Y%) /(1-p_residRel(RS,curRows,FNUT_COLS,%Y%)) ;

    In this project's notation: need = c / (1 - rr), zero where c = 0 or rr >= 1."""
    c, rr = float(content or 0.0), float(residRel or 0.0)
    return c / (1.0 - rr) if (c and rr < 1.0) else 0.0


def DATA_FNUT_yield(O_HP_: float, STRA: float, need_main: list, need_STRA: float, MAXF: float,
                    doubleMaxf: bool) -> float:
    r"""DATA(RS, crop, FNUT, "Y"): the nutrient (N, P2O5, K2O) in the crop's outputs per ha, kg per ha; the removal of
    e_EXPPRD and the base of NUTNED_'s need.

    The branch with CropResi_IDEAG_NG off; the water module's term inside is defined only in fertned's second call
    (water/irri_yields.gms), not in the simulation year's first. CAPRI's GAMS (fert/fertned.gms l. 180-193):

           DATA(RS,%pacts%,FNUT,%Y%) $ (p_dataCopy(RS,%pacts%,"LEVL",%Y%) $ p_dataCopy(RS,%pacts%,"O_HP",%Y%))
                = MIN(MAXF(FNUT)*(1 + 1 $ doubleMaxf(%pacts%))
        $iftheni.wats3 defined MWAggAct
                                    + (1 /(sum(map_aa(MWAggAct,%pacts%),p_dataCopy(RS,MWAggAct,"IRSH",%Y%)
                                                                   +(1-p_dataCopy(RS,MWAggAct,"IRSH",%Y%))
                                                                   *p_dataCopy(RS,MWAggAct,"YRATIO",%Y%)))-1)
                                    $ (ru(rs) $ sum(map_aa(MWAggAct,%pacts%),p_dataCopy(RS,MWAggAct,"IRSH",%Y%)))
        $endif.wats3
                    ,SUM( PACT_TO_Y(%pacts%,curRows),
                        MAX(15.0,  p_dataCopy(RS,%pacts%,"O_HP",%Y%)*0.001 * p_cropNeed(RS,curRows,FNUT,%Y%)
                                 + p_dataCopy(RS,%pacts%,"STRA",%Y%)*0.001 * p_cropNeed(RS,"STRA",FNUT,%Y%))));

    In this project's notation, for crop a with main outputs o (PACT_TO_Y), O_HP its yield (kg/ha), STRA its straw
    (kg/ha), need_o and need_STRA the nutrient per t (p_cropNeed):

        DATA(a, n) = min( MAXF(n) x (1 + [a in doubleMaxf]),
                          sum_o max(15, O_HP x need_o / 1000 + STRA x need_STRA / 1000) )

    need_main: the list of need_o over the crop's main outputs. MAXF: fertpar.gms's MAXF(n) (l. 384-391, the value
    already doubled there). Zero without a level or O_HP (the condition; DATA_FNUT's rule)."""
    if not float(O_HP_ or 0.0) > 0.0:
        return 0.0
    s = sum(max(15.0, float(O_HP_) * 0.001 * float(n) + float(STRA or 0.0) * 0.001 * float(need_STRA or 0.0))
            for n in need_main)
    return min(float(MAXF) * (2.0 if doubleMaxf else 1.0), s)


def p_residRel_LOSF(residRel: float, LOSF: float, GROF: float) -> float:
    r"""The fodder outputs' residue relation with their above-ground losses (fertned.gms, CropResi_IDEAG_NG off).

    CAPRI's GAMS (fert/fertned.gms l. 228):

        $ifi %CropResi_IDEAG_NG% == off   p_residRel(RS,FODF,FNUT_COLS,%Y%) $ DATA(RS,"GROF",FODF,%Y%)    = p_residRel(RS,FODF,FNUT_COLS,%Y%) + DATA(RS,"LOSF",FODF,%Y%)/DATA(RS,"GROF",FODF,%Y%);

    In this project's notation, for a fodder output: rr' = rr + LOSF / GROF (the region's losses over its gross
    production of the fodder). After the nutrient content of l. 180-193, so it enters the deliveries only."""
    g = float(GROF or 0.0)
    return float(residRel or 0.0) + (float(LOSF or 0.0) / g if g else 0.0)


def DATA_FOUT_dep(AtmDep: float, Mineralis: float = 0.0) -> float:
    r"""DATA(RS, crop, "MANN", "Y") before the residues: deposition and mineralisation, kg N per ha.

    CAPRI's GAMS (fert/fertned.gms l. 242-249):

           DATA(RS,%pacts%,FOUT,%Y%)  = 0;
           DATA(RS,%pacts%,"MANN",%Y%) $ DATA(RS,%pacts%,"LEVL",%Y%)
             =  p_nitrBalance(RS,"AtmDep") + p_nitrBalance(RS,"Mineralis");

    p_nitrBalance(RS, "Mineralis") is not set in CAPRI's 2030 data (sim_ini_21730's p_nitrBalance holds Leach and
    Denitri only), so 0."""
    return float(AtmDep or 0.0) + float(Mineralis or 0.0)


def DATA_FOUT_resid(DATA_FOUT: float, DATA_FNUT: float, residRel: float) -> float:
    r"""DATA(RS, crop, FOUT, "Y") of a crop with residues (residFnutPact): the deliveries plus the residues' share of the
    crop's nutrient, at most 95% of it.

    CAPRI's GAMS (fert/fertned.gms l. 252-271):

           DATA(RS,residFnutPact,FOUT,%Y%) $ DATA(RS,residFnutPact,"LEVL",%Y%)
                  = min( DATA(RS,residFnutPact,FOUT,%Y%)
                       + SUM( FOUT_T_N(FOUT,FNUT), DATA(RS,residFnutPact,FNUT,%Y%)
                                                 * SUM(PACT_TO_Y(residFnutPact,curRows), p_residRel(RS,curRows,FNUT,%Y%))),
                         .95*SUM( FOUT_T_N(FOUT,FNUT), DATA(RS,residFnutPact,FNUT,%Y%)))
                                                 ;

    In this project's notation, for the delivery f of nutrient n (MANN of NITF, MANP of PHOF, MANK of POTF):
    DATA(a, f) = min(DATA(a, f) + DATA(a, n) x rr_n, 0.95 x DATA(a, n)), rr_n summed over the crop's main outputs
    (residRel: that sum)."""
    n = float(DATA_FNUT or 0.0)
    return min(float(DATA_FOUT or 0.0) + n * float(residRel or 0.0), 0.95 * n)


def DATA_FOUT_straw(DATA_FOUT: float, STRA: float, LOSF_STRA: float, GROF_STRA: float, content_STRA: float) -> float:
    r"""DATA(RS, crop, FOUT, "Y") with the straw left on the field (CropResi_IDEAG_NG off).

    CAPRI's GAMS (fert/fertned.gms l. 277-286):

        $iftheni.Sa3 %CropResi_IDEAG_NG% == off
           DATA(RS,%pacts%,FOUT,%Y%) $ p_dataCopy(RS,"GROF","STRA",%Y%)
            =   DATA(RS,%pacts%,FOUT,%Y%)
                  + p_dataCopy(RS,%pacts%,"STRA",%Y%) * 0.001 * p_dataCopy(RS,"LOSF","STRA",%Y%)/p_dataCopy(RS,"GROF","STRA",%Y%)
                                                      * SUM( FOUT_T_NC(FOUT,FNUT_COLS), p_dataCopy(RS,FNUT_COLS,"STRA",%Y%));
        $endif.Sa3

    In this project's notation: DATA(a, f) + STRA_a / 1000 x LOSF(STRA) / GROF(STRA) x c(n, STRA), STRA_a the crop's
    straw (kg/ha), c(n, STRA) the straw's nutrient content (kg per t)."""
    g = float(GROF_STRA or 0.0)
    if not g:
        return float(DATA_FOUT or 0.0)
    return float(DATA_FOUT or 0.0) + float(STRA or 0.0) * 0.001 * float(LOSF_STRA or 0.0) / g * float(content_STRA or 0.0)


def O_HP_yieldGrowth(O_HP_BAS: float, p_yieldGrowth: float) -> float:
    r"""DATA(RS, crop, "O_HP", "Y") after a change of the crop's yield: the base's O_HP times the yield's growth.

    CAPRI's GAMS (capmod/define_inputs.gms l. 80-82 and 89-92; run after the scenario's yield shifts, capmod.gms l. 772,
    and by supply/endog_yields.gms l. 139 after each price-driven yield update, before fert/fertned.gms, l. 148):

        p_yieldGrowth(RS,%pacts%) $ p_dataCopy(RS,%pacts%,"LEVL","BAS")
          = SUM(PACT_TO_Y(%pacts%,curRows) $ p_dataCopy(RS,%pacts%,curRows,"BAS"),
              p_dataCopy(RS,%pacts%,curRows,"Y")/p_dataCopy(RS,%pacts%,curRows,"BAS") );
        ...
        p_dataCopy(RS,%pacts%,"O_HP","BAS")  = DATA(RS,%pacts%,"O_HP","BAS");
        *
        DATA(RS,%pacts%,"O_HP","Y") $ p_yieldGrowth(RS,%pacts%)
             = p_dataCopy(RS,%pacts%,"O_HP","BAS") * p_yieldGrowth(RS,%pacts%);

    In this project's notation O_HP(y) = O_HP_BAS x y / y_BAS. The model applies it to its own base, the simulation
    year's O_HP at CAPRI's 2030 reference yield y0 (O_HP above: the year's yield), with p_yieldGrowth = y / y0.

    Departure from CAPRI (not ported, small): CAPRI's base here is the base period's O_HP and yield ("BAS"), whose ratio
    in sim_ini_21730 is 1 within 0.3% (median 1.000, 10th-90th percentile 0.997-1.003, 12,750 crop rows); after the
    scenario's yield shifts capmod/def_fert_and_requirements.gms l. 126 zeroes O_HP and fertned rebuilds it from the
    shifted yield itself (O_HP above), so the ratio enters only CAPRI's price-driven yield updates."""
    return float(O_HP_BAS or 0.0) * float(p_yieldGrowth or 0.0)


def fertned_at_yields(o_hp: float, stra: float, need_main: float, need_stra: float, maxf: float, double_maxf,
                      resid_rel: float, resid_pact, losf_stra: float, grof_stra: float, yldFac: float,
                      yldFac_STRA: float, AtmDep: float = 0.0, nitrogen: bool = True) -> tuple:
    r"""(DATA(RS, crop, FNUT, "Y"), DATA(RS, crop, FOUT, "Y")) of one crop and nutrient at other yields than the data's:
    CAPRI's fert/fertned.gms rerun on them, as supply/endog_yields.gms does after each price-driven yield update (l. 139,
    148: capmod/define_inputs.gms, then fertned.gms) and as the simulation's first call does after the scenario's yield
    shifts (capmod.gms l. 757, 772, 1084).

    The statements, in CAPRI's order (each in its own function of this module):

        O_HP      = O_HP_yieldGrowth(o_hp, yldFac)                        define_inputs.gms l. 80-92
        STRA      = stra x yldFac_STRA                                    capmod/shift_yields.gms l. 45-49 (every output
                                                                          of PACT_TO_O, straw included, by the scenario's
                                                                          yield change; endog_yields.gms l. 111-116
                                                                          updates the main output only)
        DATA(FNUT) = DATA_FNUT_yield(O_HP, STRA, [need_main], need_stra, maxf, double_maxf)   fertned.gms l. 180-193
        DATA(FOUT) = DATA_FOUT_dep(AtmDep)  (MANN; 0 for MANP, MANK)                          fertned.gms l. 242-249
        DATA(FOUT) = DATA_FOUT_resid(DATA(FOUT), DATA(FNUT), resid_rel)   residFnutPact only  fertned.gms l. 252-271
        DATA(FOUT) = DATA_FOUT_straw(DATA(FOUT), STRA, losf_stra, grof_stra, need_stra)        fertned.gms l. 277-286

    The arguments are fertned's at CAPRI's 2030 reference (tools/build/build_capri_crop_n_coefs.py,
    capri_crop_fertned_parts_2030.csv): o_hp the year's main-output yield and stra the straw (kg/ha), need_main and
    need_stra p_cropNeed of the main output and of straw (kg per t; straw has no residue relation, so its need is its
    content, the content l. 277-286 uses), maxf and double_maxf fertpar.gms's MAXF and doubleMaxf, resid_rel the main
    output's p_residRel (with the fodder's LOSF / GROF, l. 228), resid_pact residFnutPact (l. 159), losf_stra and
    grof_stra the region's straw losses and production. yldFac: the main-output yield over the data's; yldFac_STRA: the
    straw's (the scenario's yield shift, without the price response). AtmDep: the region's deposition (kg N/ha;
    p_nitrBalance(RS, "Mineralis") is not set in CAPRI's 2030 data, DATA_FOUT_dep). nitrogen: the nutrient is NITF
    (MANN carries the deposition)."""
    ohp = O_HP_yieldGrowth(o_hp, yldFac)
    s = float(stra or 0.0) * float(yldFac_STRA)
    n = DATA_FNUT_yield(ohp, s, [need_main], need_stra, maxf, bool(double_maxf))
    f = DATA_FOUT_dep(AtmDep) if nitrogen else 0.0
    if resid_pact:
        f = DATA_FOUT_resid(f, n, resid_rel)
    f = DATA_FOUT_straw(f, s, losf_stra, grof_stra, need_stra)
    return n, f


def p_technFact_MANN(technFact_NITF: float, DATA_MANN: float, AtmDep: float, Mineralis: float = 0.0) -> float:
    r"""p_technFact(RS, crop, "MANN", A): a technology variant's factor on the crop's N deliveries to the soil, after
    fertned.gms (the factor sim_ini_21730 carries, +-0.2, is the techf.gms factor of every output, before fertned runs
    in the simulation year).

    CAPRI's GAMS (fert/fertned.gms l. 324-335):

          p_technFact(RS,%pacts%,"MANN",A) $ (DATA(RS,%pacts%,"MANN",%Y%)
                                                  $ DATA(RS,%pacts%,"NITF",%Y%)
                                                  $ p_technFact(RS,%pacts%,"LEVL",A)
                                                  $ tact(%pacts%))

              = ( (p_technFact(RS,%pacts%,"NITF",A)+1) *
                      (DATA(RS,%pacts%,"MANN",%Y%) -p_nitrBalance(RS,"AtmDep")
                                                   -p_nitrBalance(RS,"Mineralis"))

                     + p_nitrBalance(RS,"AtmDep")
                     + p_nitrBalance(RS,"Mineralis") )
                           / DATA(RS,%pacts%,"MANN",%Y%) - 1.;

    In this project's notation, with tf the variant's p_technFact(crop, NITF, A) (its yield factor, l. 205-206), M the
    crop's DATA(MANN) and d the deposition (plus mineralisation, not set in CAPRI's 2030 data: DATA_FOUT_dep):
    p_technFact(MANN, A) = ((1 + tf)(M - d) + d) / M - 1 = tf (M - d) / M: only the residues move with the variant's
    yield. (P2O5 and K2O keep the yield factor, l. 314-318.) Without M or DATA(NITF) the statement does not apply:
    None (the caller keeps the factor it had)."""
    M = float(DATA_MANN or 0.0)
    if not M:
        return None
    d = float(AtmDep or 0.0) + float(Mineralis or 0.0)
    return ((float(technFact_NITF) + 1.0) * (M - d) + d) / M - 1.0


def DATA_FNUT(need_data: float, O_HP: float) -> float:
    r"""CAPRI's DATA(RS, crop, FNUT, "Y") after fertned.gms for the crop's need (K185): the crop's nutrient need per
    ha, zero for a crop without a main-output yield O_HP (fallow, set-aside); kg per ha.

    CAPRI's GAMS (fert/fertned.gms l. 98-99):

           DATA(RS,%pacts%,FNUT,%Y%) $  p_dataCopy(RS,%pacts%,"LEVL",%Y%) = 0;
           DATA(RS,%pacts%,FNUT,%Y%) $  (not p_dataCopy(RS,%pacts%,"O_HP",%Y%)) = 0;

    then l. 180-193 (DATA_FNUT_yield) for the crops with a main output, and l. 233, DATA(RS,"FALL",FNUT,%Y%) = 0.0.
    NUTNED_ (supply/supply_model.gms l. 1095-1137) sums v_actLevl x DATA(crop, FNUT, "Y") x ... over the crops of each
    nutrient group, so a crop without a main output (no O_HP: fallow FALL and set-aside VSET, which are not in
    PACT_TO_Y, sets.gms l. 5377-5456) adds nothing to its group's need. CAPRI's own margins confirm it: at the 2030 base
    the first-order condition of FALL and VSET holds without a need term (reports/margcr.gms: D_AREA + D_PMPL + D_PREM +
    D_NUT = 0, D_PROV = 0) in every interior case, including the regions where sim_ini's DATA carries an NITF for them
    (DE B3: 4.66 kg N/ha), while their group OAFC has positive duals (TEXT, TOBA).

    In this project's notation, for crop a of region r and nutrient n:

        need(r, a, n) = need_data(r, a, n)   if O_HP(r, a) > 0
                        0                    otherwise

    with need_data the crop's need per ha of CAPRI's 2030 reference (npk_crop_coefs_2030.csv, need_kg_ha: CAPRI's own
    need of NUTNED_, from DATA_FNUT_yield's value) and O_HP the crop's main-output yield (the region's yields, t/ha).
    The model's data have area without a main-output yield only for FALL and VSET (yields.csv: 247 and 166 regions).

    Departures from CAPRI: none in the rule; the need itself is CAPRI's reported 2030 value (its yield response is the
    NLP's: capri_mod/fert/npk.py, yield_shares)."""
    return float(need_data) if float(O_HP or 0.0) > 0.0 else 0.0


def p_technFact_FNUT(techn_fact):
    r"""p_technFact(RS, crop, FNUT, A): a technology variant's factor on the crop's nutrient rows (removal, fixation,
    residues: e_EXPPRD, e_BIOFIX, e_CRESID), its yield factor's p_technFact(crop, yield, A) as 1 + tf, tf the variant's
    relative change of the yield (the technology mix columns', 0 for the default variant).

    CAPRI's GAMS (fert/fertned.gms l. 206-207):

           p_technFact(RS,%pacts%,FNUT,A) $ p_technFact(RS,%pacts%,"LEVL",A)
                = SUM(PACT_TO_Y(%pacts%,curRows), p_technFact(RS,%pacts%,curRows,A));

    In this project's notation: the rows of variant A x (1 + tf_A). Departures from CAPRI: the SRNUTS1 fill of l. 213-214
    (the NUTS1 regions without the factor) is not ported (the model's units carry their own)."""
    return 1.0 + float(techn_fact or 0.0)

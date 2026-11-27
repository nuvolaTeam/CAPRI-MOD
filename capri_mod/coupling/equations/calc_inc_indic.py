r"""CAPRI's income indicators per activity (reports/calc_inc_indic.gms, star 3.0), which its simulation year's report
calls on the supply models' regions (reports/sol_simy.gms l. 2533). capri_mod/income/income_module.py
(IncomeDistributionModule.income_parts) calls them at each regional solution (income I1).
"""
from __future__ import annotations


def DATA_MGVA(r, FEED_lin, FEED_sol, TOIN_lin=0.0, TOIN_Y=None, TOOU_FOUT=0.0, REV_lin_FODDO=0.0, TOOU_FODDO=None):
    r"""DATA(RU, MPACT, "MGVA", SIMY) of an activity with a level, per ha or head (EUR): its outputs less its inputs at
    the solution, valued at the simulation year's unit values, plus its premiums.

    CAPRI's GAMS (reports/calc_inc_indic.gms l. 30-49):

            DATA(%regions%,MPACT,"TOOU","%SIMY%")  $ p_dataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              = SUM( PACT_TO_O(MPACT,O), p_dataCopy(%regions%,MPACT,O,"%SIMY%") * p_dataCopy(%regions%,"UVAG",O,"%SIMY%"))   * 0.001;
            DATA(%regions%,MPACT,"TOOU","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"TOOU","%SIMY%");
        *
            p_dataCopy(%regions%,"UVAG",I,"%SIMY%")      = DATA(%regions%,"UVAG",I,"%SIMY%");
            p_dataCopy(%regions%,MPACT,I,"%SIMY%")       = DATA(%regions%,MPACT,I,"%SIMY%");
            DATA(%regions%,MPACT,"TOIN","%SIMY%") $ p_DataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              =  SUM( PACT_TO_I(MPACT,I) $ p_DataCopy(%regions%,MPACT,I,"%SIMY%"),
                     p_DataCopy(%regions%,MPACT,I,"%SIMY%") * p_DataCopy(%regions%,"UVAG",I,"%SIMY%")) * 0.001;
            DATA(%regions%,MPACT,"TOIN","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"TOIN","%SIMY%");
        *
            DATA(%regions%,MPACT,"GVAP","%SIMY%") $ DATA(%regions%,MPACT,"LEVL","%SIMY%")
              =  DATA(%regions%,MPACT,"TOOU","%SIMY%")   - DATA(%regions%,MPACT,"TOIN","%SIMY%");
            DATA(%regions%,MPACT,"GVAP","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"GVAP","%SIMY%");
        *
        *   ---- modified gross value added
        *
            DATA(%regions%,MPACT,"MGVA","%SIMY%") $ DATA(%regions%,MPACT,"LEVL","%SIMY%")
               =  DATA(%regions%,MPACT,"GVAP","%SIMY%") + DATA(%regions%,MPACT,"PRME","%SIMY%");
            DATA(%regions%,MPACT,"MGVA","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"MGVA","%SIMY%");

    In this project's notation: MGVA_a = TOOU_a - TOIN_a + PRME_a. The model's form: the activity's linear margin r_a
    (supply_module._compute_net_revenues, LINEAR_netRevenue: revenue - input cost + premium per unit, at the solve's
    prices) less the change of its feed, the solved ration per unit at its report prices FEED_sol against the feed
    value per unit the margin carries FEED_lin (CAPRI's TOIN takes the solution's feed, sol_simy.gms l. 254-257), and,
    for a crop at the simulation year, less the change of its other inputs, CAPRI's TOIN at the year's coefficients
    TOIN_Y (DATA_TOIN_Y) against the base cost the margin carries TOIN_lin, and, for a crop, plus its residues'
    nutrients, the outputs MANN, MANP, MANK of its TOOU that its margin does not hold (TOOU_FOUT, DATA_TOOU_FOUT), and,
    for a fodder crop, its fodder output at CAPRI's UVAG(FODDO) (TOOU_FODDO: YILD x DATA_UVAG_FODDO, sol_simy.py) in
    place of the output its margin carries at its producer price (REV_lin_FODDO; KNOWN_ISSUES K213):

        MGVA_a = r_a - (FEED_sol_a - FEED_lin_a) - (TOIN_Y_a - TOIN_lin_a) + TOOU_FOUT_a + (TOOU_FODDO_a - REV_lin_FODDO_a)

    The margin's changes of the inputs within the run (the Green Deal's PLAP and INPO changes, the yields' input update,
    the organic top-up) act on CAPRI's year coefficients already (register DEP-21) and stay in r_a.

    Departures from CAPRI: the activity's outputs, inputs and premiums are not kept item by item, so TOOU, TOIN and
    GVAP are not computed apart; the mitigation options' cost and revenue, which sol_simy.gms l. 1471-1473 put in the
    activities' TOIN and TOOU (mitiI, mitiO), are booked at the region (coupling/equations/sol_simy.py
    DATA_AGGT_MGVA), since the model has several of them per region only (the fertiliser options, urea substitution,
    the winter cover: capri_mod/income/mitigation_items.py); the region's total is the same (register DEP-54)."""
    v = float(r) - (float(FEED_sol) - float(FEED_lin)) + float(TOOU_FOUT)
    if TOOU_FODDO is not None:
        v += float(TOOU_FODDO) - float(REV_lin_FODDO)
    if TOIN_Y is not None:
        v -= float(TOIN_Y) - float(TOIN_lin)
    return v


def DATA_TOIN_Y(iy_uvag, TF_I, need_kg_ha, uvag_fnut):
    r"""DATA(RU, MPACT, "TOIN", SIMY) of a crop at the simulation year's coefficients (EUR per ha): its directly
    yield-dependent inputs at the year's coefficients (capmod/define_inputs.gms) at the simulation year's UVAG, with the
    input-saving progress TF_I, plus its fertilisers' need at their unit value.

    CAPRI's GAMS (reports/calc_inc_indic.gms l. 34-39, the inputs' value; capmod/define_inputs.gms l. 108-112, the
    yield-dependent inputs' coefficients):

            p_dataCopy(%regions%,"UVAG",I,"%SIMY%")      = DATA(%regions%,"UVAG",I,"%SIMY%");
            p_dataCopy(%regions%,MPACT,I,"%SIMY%")       = DATA(%regions%,MPACT,I,"%SIMY%");
            DATA(%regions%,MPACT,"TOIN","%SIMY%") $ p_DataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              =  SUM( PACT_TO_I(MPACT,I) $ p_DataCopy(%regions%,MPACT,I,"%SIMY%"),
                     p_DataCopy(%regions%,MPACT,I,"%SIMY%") * p_DataCopy(%regions%,"UVAG",I,"%SIMY%")) * 0.001;
            DATA(%regions%,MPACT,"TOIN","Y")   $ DATA(%regions%,MPACT,"LEVL","%SIMY%") = DATA(%regions%,MPACT,"TOIN","%SIMY%");

                p_dataCopy(RS,%pacts%,IY,"BAS") = DATA(RS,%pacts%,IY,"BAS");
                DATA(RS,%pacts%,IY,"Y") $ p_dataCopy(RS,%pacts%,IY,"BAS")
                    = ( p_dataCopy(RS,%pacts%,IY,"BAS")
                         * (1-p_inputDemandFactor(%pacts%,IY) + p_inputDemandFactor(%pacts%,IY) * p_yieldGrowth(RS,%pacts%)))
                                             * TF_I(RS,IY,"T");

    In this project's notation: TOIN_a = TF_I x sum_IY DATA_I(BAS) (1 - f + f G) UVAG_I + sum_FNUT n_FNUT UVAG_FNUT /
    1000; iy_uvag the first sum before TF_I (input_coefs_2030.csv iy_uvag_eur_ha, tools/build/build_input_coefs_2030.py,
    in the model's money), need_kg_ha and uvag_fnut per nutrient (CAPRI's 2030 need per crop and the member state's
    UVAG of the nutrient, EUR per t; capri_mod/fert/npk.py). Checked against CAPRI's 2030 reference (dataOut TOIN at
    the solution, a check only): Denmark's soft wheat 1,761.2 against 1,764.8 EUR/ha and rapeseed 2,188.2 against
    2,188.4 in CAPRI's 2030 money.

    Departures from CAPRI: the year's coefficients of the mean technology (CAPRI's DATA(SIMY) weights them with the
    technology mix, sol_simy.gms l. 377-384; the model's mix column carries the difference T1 - T2 in its margin); WIRR
    (irrigation water, the water module off) not valued."""
    return float(TF_I) * float(iy_uvag) + sum(float(n) * float(u) for n, u in zip(need_kg_ha, uvag_fnut)) / 1000.0


def DATA_TOOU_FOUT(FOUT_kg, UVAG_FOUT):
    r"""The part of DATA(RU, MPACT, "TOOU", SIMY) of a crop that its residues' nutrients make (EUR per ha): its outputs
    MANN, MANP, MANK (PACT_TO_O, global/fromimpact/sets.gms l. 2253ff: SWHE.(SWHE, STRA, MANN, MANP, MANK), RAPE.(RAPE,
    MANN, MANP, MANK) ...) at their unit values. With the straw at zero (KNOWN_ISSUES K211) it is CAPRI's secondary
    revenue SREV = TOOU - MREV (reports/aggreg_res_data.gms l. 281-282).

    CAPRI's GAMS (reports/calc_inc_indic.gms l. 30-31):

            DATA(%regions%,MPACT,"TOOU","%SIMY%")  $ p_dataCopy(%regions%,MPACT,"LEVL","%SIMY%")
              = SUM( PACT_TO_O(MPACT,O), p_dataCopy(%regions%,MPACT,O,"%SIMY%") * p_dataCopy(%regions%,"UVAG",O,"%SIMY%"))   * 0.001;

    In this project's notation: TOOU_FOUT_a = sum over FOUT of DATA(a, FOUT) x UVAG(FOUT) / 1000, DATA(a, FOUT) the
    crop's residues' nutrient per ha at the solution (kg N, P2O5, K2O; the residue deliveries the regional model's
    nutrient balance takes at the solve's yields, supply/fertilisation.py _npk_spec, RegionalResults.last_fout) and
    UVAG(FOUT) the member state's unit value at the simulation year (EUR per t; npk_region_2030.csv fout_uvag_eur_t,
    DATA_UVAG_IO_SIMY of CAPRI's base year value). Checked against CAPRI's 2030 reference (dataOut, a check only):
    FR24's soft wheat 41.14 x 631.55 + 16.56 x 1,353.57 + 99.35 x 570.25 = 105.05 EUR per ha, its SREV 105.05.

    Departures from CAPRI: the mean technology's coefficients (the model's technology mix column carries the residues'
    difference T1 - T2 on the area moved; CAPRI's DATA(SIMY) weights them, sol_simy.gms l. 377-384), as DATA_TOIN_Y."""
    return sum(float(q) * float(u) for q, u in zip(FOUT_kg, UVAG_FOUT)) / 1000.0

r"""CAPRI's 2004-2013 premium regime (pol_input/mtr_until2013.gms, star 3.0): its assignments other than one literal
value, the rules capri_mod/policy/mtr.py executes at their lines (mtr_rules.csv: the statement's labels and numbers,
tools/build/build_mtr_inputs.py), the modulation's total shares, the coupling degree and the decoupling targets.

Each function returns the value its statement assigns to one record, or None where the statement's condition leaves
the record as it is (an assigned 0 deletes the record, as GAMS stores no zero: the caller's _Series). The literal
values (mtr_declarations.csv, the numbers of mtr_rules.csv and mtr_dd_target_rules.csv) are data read, not here (the
project lead's decision, 23 November 2026). Three rules are selections of records with no value to compute and stay
in the caller: eps_in_year (l. 589-590, 635-636, 677-678: EPS in the year for each item the region has in some
year), delete_year (l. 594) and rdel (l. 741, the regions outside the run: none).
"""
from __future__ import annotations

from capri_mod.policy.equations._gams import EPS, NA, above_eps, as_number, nonzero


def p_premDataE_DPMTR_CEILVAL(annex):
    r"""p_premDataE(MS, SIMY, "DPMTR", "CEILVAL"): the national ceiling of the single payment, the year's value of
    Annex VIII (EU_WEST's members, UK000000) or VIIIa (SI000000, MT000000) of Regulation 1782/2003 (0 deletes).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 214-217):

            p_premDataE(MS,SIMYY,"DPMTR","CEILVAL") $  MAP_RR("EU_WEST",MS) = P_1782_2003_ANNEX_VIII(MS,SIMYY);
            p_premDataE("UK000000",SIMYY,"DPMTR","CEILVAL") = P_1782_2003_ANNEX_VIII("UK000000",SIMYY);
            p_premDataE("SI000000",SIMYY,"DPMTR","CEILVAL") = P_1782_2003_ANNEX_VIIIa(SIMYY,"SI000000");
            p_premDataE("MT000000",SIMYY,"DPMTR","CEILVAL") = P_1782_2003_ANNEX_VIIIa(SIMYY,"MT000000");

    Departures from CAPRI: none (the annexes' values, mtr_ceiling_tables.csv, are data read)."""
    return annex


def p_premDataE_DPMTR_CEILVAL_net(CEILVAL_years, annex_IV):
    r"""p_premDataE(MS, SIMY, "DPMTR", "CEILVAL") of a member state with a ceiling in some year: the net ceiling of
    Annex IV of Regulation 73/2009 where it has one for the year; None otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 222-223):

            p_premDataE(MS,SIMYY,"DPMTR","CEILVAL") $ (sum(simyy1, p_premDataE(MS,SIMYY1,"DPMTR","CEILVAL")) $ p_73_2009_ANNEX_IV(MS,SIMYY))
               = p_73_2009_ANNEX_IV(MS,SIMYY);

    Departures from CAPRI: none (Belgium's net ceiling its two parts', l. 167, by the caller)."""
    return annex_IV if (sum(as_number(v) for v in CEILVAL_years) and annex_IV) else None


def p_premDataE_dpSaps_ceilVal(annex_VIIIa):
    r"""p_premDataE(RUNR, SIMY, "dpSaps", "ceilVal") of a SAPS member state (RUNR: those with an Annex VIIIa ceiling,
    Slovenia and Malta out): the Annex VIIIa ceiling where there is one; None otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 237):

            p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") $ P_1782_2003_ANNEX_VIIIa(SIMYY,RUNR) = P_1782_2003_ANNEX_VIIIa(SIMYY,RUNR);

    Departures from CAPRI: none."""
    return annex_VIIIa if annex_VIIIa else None


def p_premDataE_dpSaps_ceilVal_net(ceilVal, annex_IV):
    r"""p_premDataE(RUNR, SIMY, "dpSaps", "ceilVal") with a ceiling: the net ceiling of Annex IV where there is one;
    None otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 238-239):

            p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") $ (p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") $ p_73_2009_ANNEX_IV(RUNR,SIMYY))
                = p_73_2009_ANNEX_IV(RUNR,SIMYY);

    Departures from CAPRI: none."""
    return annex_IV if (nonzero(ceilVal) and annex_IV) else None


def p_premDataE_CEILVAL_fill(CEILVAL, CEILVAL_year_before):
    r"""p_premDataE(MS, SIMY, "dpSaps" or "dpmtr", "CEILVAL") of a year without a ceiling, from the base year to
    %endofMTR%: the year before's (None, no record, where the year has one: as GAMS's assignment of no record, which
    leaves none).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 264-269):

            LOOP( SIMYY $ ((CALYEA(SIMYY) GE CALYEA("BAS")) $ (CALYEA(SIMYY) LE %endofMTR%)),
                p_premDataE(MS,SIMYY,"dpSaps","CEILVAL")  $ (NOT p_premDataE(MS,SIMYY,"dpSaps","CEILVAL"))
                  = p_premDataE(MS,SIMYY-1,"dpSaps","CEILVAL");
                p_premDataE(MS,SIMYY,"dpmtr","CEILVAL")  $ (NOT p_premDataE(MS,SIMYY,"dpmtr","CEILVAL"))
                  = p_premDataE(MS,SIMYY-1,"dpmtr","CEILVAL");
                );

    Departures from CAPRI: none."""
    return None if nonzero(CEILVAL) else CEILVAL_year_before


def p_premDataE_dpSaps_ceilLev(ceilVal, saps_area):
    r"""p_premDataE(RUNR, SIMY, "dpSaps", "ceilLev") with a ceiling: the SAPS area (P_SAPS_AREAS; 0 deletes); None
    without a ceiling.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 275):

            p_premDataE(RUNR,SIMYY,"dpSaps","ceilLev") $ p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") = P_SAPS_AREAS(RUNR);

    Departures from CAPRI: none."""
    return saps_area if nonzero(ceilVal) else None


def p_premDataE_dpSaps_ceilLev_UAAR(ceilVal, ceilLev, UAAR):
    r"""p_premDataE(RUNR, SIMY, "dpSaps", "ceilLev") with a ceiling and no area: the base year's UAAR; None otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 277):

            p_premDataE(RUNR,SIMYY,"dpSaps","ceilLev") $ (p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") $  (not p_premDataE(RUNR,SIMYY,"dpSaps","ceilLev"))) = DATA(RUNR,"UAAR","LEVL","BAS");

    Departures from CAPRI: none."""
    return UAAR if (nonzero(ceilVal) and not nonzero(ceilLev)) else None


def p_premDataE_dpSaps_pgSaps(ceilLev_condition, ceilVal, ceilLev, factor):
    r"""p_premDataE(RUNR, SIMY, "dpSaps", "pgSaps") with an area: the SAPS rate per ha, the ceiling over the area times
    the factor (1000, mtr_rules.csv); None without an area (ceilLev_condition, the record the condition reads: the
    area, as mtr_rules.csv names it).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 279-280):

            p_premDataE(RUNR,SIMYY,"dpSaps","pgSaps")  $ p_premDataE(RUNR,SIMYY,"dpSaps","ceilLev")
                = p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal")/p_premDataE(RUNR,SIMYY,"dpSaps","ceilLev")*1000;

    In this project's notation: rate = C / A x 1000. Departures from CAPRI: none."""
    if not nonzero(ceilLev_condition):
        return None
    return as_number(ceilVal) / as_number(ceilLev) * factor


def p_premDataE_where(condition, value):
    r"""p_premDataE(R, SIMY, scheme, item) = value where a record of the region is set (a ceiling value, CAPRI's $
    condition), None otherwise: the SAPS member states' application type (l. 282), Slovenia's bull and sheep premiums
    (l. 309-310, 325-326: perLevl and the rates of mtr_rules.csv), the dairy cow and sheep ceilings EPS where SAPS is
    paid (l. 721-722).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 282):

            p_premDataE(RUNR,SIMYY,"dpSaps","appType") $ p_premDataE(RUNR,SIMYY,"dpSaps","ceilVal") = perLevl;

    and l. 309, 310, 325, 326, 721, 722 (the same form). Departures from CAPRI: none."""
    return value if nonzero(condition) else None


def p_premDataE_DPPULS_PGPROT(CEILLEV):
    r"""p_premDataE(MS, "2004", "DPPULS", "PGPROT") of an EU-27 member state without a protein crop area: EPS; None
    otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 544):

            p_premDataE(MS,"2004","DPPULS","PGPROT") $ (MAP_RR("EU027000",MS) $ (NOT p_premDataE(MS,"2004","DPPULS","CEILLEV")))  = eps;

    Departures from CAPRI: none."""
    return None if nonzero(CEILLEV) else EPS


def p_premDataE_DPDWHETR_PGDWHE(numbers):
    r"""p_premDataE(TRDWHE_REG, year, "DPDWHETR", "PGDWHE"): the durum wheat premium of the traditional regions, the sum
    of the statement's numbers (285 + 40, mtr_rules.csv).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 599-601):

            p_premDataE(TRDWHE_REG,"2004","DPDWHETR","PGDWHE")  = 285. + 40;
            p_premDataE("EU025000","2004","DPDWHETR","APPTYPE") = perLevl;
            p_premDataE(TRDWHE_REG,"2007","DPDWHETR","PGDWHE") = 285. + 40;

    Departures from CAPRI: none (the application type of l. 600 is a literal value, data read)."""
    return sum(float(x) for x in numbers)


def p_premDataE_DPDCOW_PGDCOW(year, from_year, value):
    r"""p_premDataE("EU025000" or "BUR", SIMY, "DPDCOW", "PGDCOW") after the year given (2006, 2007) up to the
    simulation year: the dairy premium per t of quota (24.49, mtr_rules.csv); None before.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 697):

            p_premDataE("EU025000",SIMY,"DPDCOW","PGDCOW") $ ((CALYEA(SIMY) GT CALYEA("2006")) $ (CALYEA(SIMY) LE CALYEA("Y"))) =  24.49;

    and the same for BUR from 2007 (l. 700). Departures from CAPRI: written at the simulation year only (the only year
    the chain reads)."""
    return value if year > from_year else None


def p_premDataE_DPDCOW_CEILVAL(PGDCOW, QUTS):
    r"""p_premDataE(RS, SIMY, "DPDCOW", "CEILVAL") of the regions of EU025000's (BUR's) member states: the aggregate's
    dairy premium per t times the region's milk quota.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 704-705):

            p_premDataE(RS,SIMY,"DPDCOW","CEILVAL") $ SUM(MAP_RR(MS,RS) $ MAP_RR("EU025000",MS),1) = p_premDataE("EU025000",SIMY,"DPDCOW","PGDCOW") * DATA(RS,"QUTS","COMI",SIMY);
            p_premDataE(RS,SIMY,"DPDCOW","CEILVAL") $ SUM(MAP_RR(MS,RS) $ MAP_RR("BUR",MS),1)      = p_premDataE("BUR",SIMY,"DPDCOW","PGDCOW")      * DATA(RS,"QUTS","COMI",SIMY);

    Departures from CAPRI: at the simulation year with the base data's milk quota (mtr_base_data.csv)."""
    return PGDCOW * QUTS


def p_premDataE_DPNE_DCOW_CEILVAL(CEILVAL, factor):
    r"""p_premDataE(RS, year, "DPNE_DCOW", "CEILVAL") of 2005-2007: the dairy envelope scaled by the factor (1.42,
    mtr_rules.csv); None where it is EPS or NA (kept as GAMS's comment wants).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 710-712):

            p_premDataE(RS,"2005","DPNE_DCOW","CEILVAL") =  p_premDataE(RS,"2005","DPNE_DCOW","CEILVAL") * 1.42;
            p_premDataE(RS,"2006","DPNE_DCOW","CEILVAL") =  p_premDataE(RS,"2006","DPNE_DCOW","CEILVAL") * 1.42;
            p_premDataE(RS,"2007","DPNE_DCOW","CEILVAL") =  p_premDataE(RS,"2007","DPNE_DCOW","CEILVAL") * 1.42;

    Departures from CAPRI: none."""
    if CEILVAL in (EPS, NA):
        return None
    return float(CEILVAL) * float(factor)


def p_premDataE_AT_DPSCOW_CEILLEV(CEILLEV, number, add):
    r"""p_premDataE("AT000000", "2004", "DPSCOW", "CEILLEV"): Austria's suckler cow ceiling, its own plus 50 (l. 717),
    then the bull ceiling's minus 50 (l. 718; the numbers of mtr_rules.csv); add says which.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 717-718):

            p_premDataE("AT000000","2004","DPSCOW","CEILLEV")         =  p_premDataE("AT000000","2004","DPSCOW","CEILLEV") + 50.;
            p_premDataE("AT000000","2004","DPSCOW","CEILLEV")         =  p_premDataE("AT000000","2004","DPBULF","CEILLEV") - 50.;

    Departures from CAPRI: none."""
    return as_number(CEILLEV) + float(number) if add else as_number(CEILLEV) - float(number)


def p_percAffByModulation_Tot(percAffByModulation, Prem_Mod):
    r"""p_percAffByModulation(PSGG, "Tot", MS): the share of a producer group's payments subject to modulation, the sum
    over the payment classes of their share x the class's modulation rate (sequences in the same order).

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 832-833):

           p_percAffByModulation(PSGG,"Tot","BL400000") = SUM( ModClass, p_percAffByModulation(PSGG,ModClass,"BL400000") * Prem_Mod(ModClass));
           p_percAffByModulation(PSGG,"Tot",MS)         = SUM( ModClass, p_percAffByModulation(PSGG,ModClass,MS)         * Prem_Mod(ModClass));

    Departures from CAPRI: none (the classes' shares and rates, mtr_modulation*.csv, data read)."""
    t = 0.0
    for v, m in zip(percAffByModulation, Prem_Mod):
        t += v * m
    return t


def p_couplPercent_fill(couplPercent, couplPercent_year_before):
    r"""p_couplPercent(PSDPAY, SIMYY, MS) of a year from 2006 to %endofMTR% without a coupling degree: the year
    before's; None where it has one or the year before has none.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 980-981):

            LOOP( SIMYY $ ((CALYEA(SIMYY) GE CALYEA("2006")) $ (CALYEA(SIMYY) LE %endofMTR%)),
                p_couplPercent(PSDPAY,SIMYY,MS) $ (NOT p_couplPercent(PSDPAY,SIMYY,MS)) = p_couplPercent(PSDPAY,SIMYY-1,MS);

    Departures from CAPRI: none."""
    if nonzero(couplPercent) or not nonzero(couplPercent_year_before):
        return None
    return couplPercent_year_before


def p_couplPercent(couplPercent):
    r"""p_couplPercent(PSDPAY, SIMY, MS) of the simulation year (the other years killed): EPS read as 0.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 990-991):

            p_couplPercent(PSDPAY,SIMYY,MS) $ (NOT SUM(SAMEAS(SIMYY,SIMY),1))  = 0;
            p_couplPercent(PSDPAY,SIMY,MS)  $ (p_couplPercent(PSDPAY,SIMY,MS) eq eps)   = 0;

    Departures from CAPRI: none (100 up to 2005 and for the EU-11's and BUR's SAPS, l. 977, 985-987, and the 2006
    cells outside the member states dropped, l. 978, by the caller)."""
    return 0.0 if couplPercent == EPS else couplPercent


def p_premToDDTarget_E_fill(premToDDTarget_E, premToDDTarget_E_year_before):
    r"""p_premToDDTarget_E(MS, SIMYY, PSDPAY_MTR_EL, DDTarget) of a year from 2006 to max(%endofMTR%, the simulation
    year) without a share: the year before's; None where it has one or the year before has none.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 1555-1558):

            LOOP( SIMYY $ ((CALYEA(SIMYY) GE CALYEA("2006")) $ (CALYEA(SIMYY) LE max{%endofMTR%,%SIMY%})),
                   p_premToDDTarget_E(MS,SIMYY,PSDPAY_MTR_EL,DDTarget) $ (   (not p_premToDDTarget_E(MS,SIMYY,PSDPAY_MTR_EL,DDTarget))
                                                                              and p_premToDDTarget_E(MS,SIMYY-1,PSDPAY_MTR_EL,DDTarget))
                       = p_premToDDTarget_E(MS,SIMYY-1,PSDPAY_MTR_EL,DDTarget);

    Departures from CAPRI: none."""
    if nonzero(premToDDTarget_E) or not nonzero(premToDDTarget_E_year_before):
        return None
    return premToDDTarget_E_year_before


def p_premToDDTarget(premToDDTarget_E):
    r"""p_premToDDTarget(MS, SIMY, PSDPAY_MTR_EL, DDTarget): the simulation year's share above EPS; None otherwise.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 1561-1562):

                p_premToDDTarget(MS,SIMY,PSDPAY_MTR_EL,DDTarget) $ (p_premToDDTarget_E(MS,SIMY,PSDPAY_MTR_EL,DDTarget) gt eps)
                 = p_premToDDTarget_E(MS,SIMY,PSDPAY_MTR_EL,DDTarget);

    Departures from CAPRI: none."""
    return premToDDTarget_E if above_eps(premToDDTarget_E) else None


def p_premToDDTarget_rule(value, year, from_year):
    r"""p_premToDDTarget(R, SIMY, scheme, target) of the statements from 2006 (BUR's, EU011000's and EU010000's dairy and
    sheep payments to DDRARE; EU_WEST, Malta and Slovenia: all targets 0, then DDFRMS 100 or Slovenia's 67 and 33):
    the statement's value (mtr_dd_target_rules.csv, data read; 0 deletes) from the year given; None before.

    CAPRI's GAMS (pol_input/mtr_until2013.gms l. 1566-1581):

                p_premToDDTarget("BUR",SIMY,"DPDCOW","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;
                p_premToDDTarget("BUR",SIMY,"DPSHGM","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;
                p_premToDDTarget("EU011000",SIMY,"DPDCOW","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;
                p_premToDDTarget("EU011000",SIMY,"DPSHGM","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;
                p_premToDDTarget("EU010000",SIMY,"DPDCOW","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;
                p_premToDDTarget("EU010000",SIMY,"DPSHGM","DDRARE") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;

                p_premToDDTarget("EU_WEST",SIMY,PSDPAY_MTR_EL,DDTarget) $ (CALYEA(SIMY) GE CALYEA("2006")) = 0;
                p_premToDDTarget("EU_WEST",SIMY,PSDPAY_MTR_EL,"DDFRMS") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;

                p_premToDDTarget("MT000000",SIMY,PSDPAY_MTR_EL,DDTarget) $ (CALYEA(SIMY) GE CALYEA("2006")) = 0;
                p_premToDDTarget("MT000000",SIMY,PSDPAY_MTR_EL,"DDFRMS") $ (CALYEA(SIMY) GE CALYEA("2006")) = 100;

                p_premToDDTarget("SI000000",SIMY,PSDPAY_MTR_EL,DDTarget) $ (CALYEA(SIMY) GE CALYEA("2006")) = 0;
                p_premToDDTarget("SI000000",SIMY,PSDPAY_MTR_EL,"DDRARA") $ (CALYEA(SIMY) GE CALYEA("2006")) = 67;
                p_premToDDTarget("SI000000",SIMY,PSDPAY_MTR_EL,"DDRGRA") $ (CALYEA(SIMY) GE CALYEA("2006")) = 33;

    Departures from CAPRI: none."""
    return value if year >= from_year else None

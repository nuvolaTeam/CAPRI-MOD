r"""CAPRI's declared premiums (policy/policy.gms, star 3.0): the declarations read for the year, the levels summed up
the regional hierarchy, the rates, application types and entitlement weights passed down it, the application factor,
PRMD and its re-aggregation, and the entitlement weight.

Each function computes one statement for one (region, activity, scheme); capri_mod/policy/declared.py
(declared_premiums, _levels) and capri_mod/policy/mtr.py (policy_inputs) loop over them and keep GAMS's records (None:
no record, the statement's condition false). GAMS's values (EPS, NA, a $-condition) are in _gams.py.
"""
from __future__ import annotations

from capri_mod.policy.equations._gams import NA, above_eps, gams_sum, nonzero

#: CAPRI's application types and the numbers policy.gms gives them to sum them over the levels above (l. 166-173)
APPTYPES = {"perLevl": 1, "perSlgthd": 2, "perYield": 3, "perHistY": 4, "perLiveStockUnit": 5}
_APPTYPE_CI = {k.lower(): v for k, v in APPTYPES.items()}    # GAMS's identifiers ignore case (perLivestockUnit)


def p_premData(value):
    r"""p_premData(RSEU, PSDPAY_T, PSPOS_GRP): the year's declaration of a scheme's item in a region, NA read as no
    record (None).

    CAPRI's GAMS (policy/policy.gms l. 24-25):

            p_premData(RSEU,PSDPAY_T,PSPOS_GRP)
             = p_premDataE(RSEU,%1,PSDPAY_T,PSPOS_GRP) $ (p_premDataE(RSEU,%1,PSDPAY_T,PSPOS_GRP) ne NA);

    Departures from CAPRI: none (the year's value, %1, is def_policy.gms's last value up to it, the caller's)."""
    return None if value == NA else value


def p_dataCopy_LEVL(LEVL):
    r"""p_dataCopy(R, PPPACT, "LEVL", "Y") of a NUTS 1 region, member state or EU aggregate: the sum of the levels of
    the regions below it (the caller's order).

    CAPRI's GAMS (policy/policy.gms l. 132-137):

            p_dataCopy(NUTS1A,PPPACT,"LEVL","Y") $ CARD(NUTS2)
                 = SUM(NUTS2 $ (MAP_RR(NUTS1A,NUTS2) or sameas(NUTS1A,NUTS2)), p_dataCopy(NUTS2,PPPACT,"LEVL","Y"));

            p_dataCopy(MSAGG,PPPACT,"LEVL","Y")       = SUM(Map_RR(MSAGG,NUTS2),    p_dataCopy(NUTS2,PPPACT,"LEVL","Y"));

            p_dataCopy(REGAGGP,PPPACT,"LEVL","Y")     = SUM(MAP_RR(REGAGGP,MS), p_dataCopy(MS,PPPACT,"LEVL","Y"));

    In this project's notation: L_R = sum_{r below R} L_r. Departures from CAPRI: the units of the run only (the regions
    below outside it are not in the data)."""
    return sum(LEVL)


def p_premPaym_APPTYPE(APPTYPE):
    r"""p_premPaym(RSEU, PPPACT, PSDPAY, "APPTYPE"): the number of a region's own application type (a name, any case,
    or already a number), so that the levels below can sum it.

    CAPRI's GAMS (policy/policy.gms l. 156-173):

            p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") $ ((   (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") gt eps)
                                                          $  p_dataCopy(RSEU,PPPACT,"LEVL","Y")) $ PSDPAY_T_A(PPPACT,PSDPAY))
                = p_premData(RSEU,PSDPAY,"APPTYPE") $ (p_premData(RSEU,PSDPAY,"APPTYPE") ne eps);

        *
        *   --- convert acronyms temp. to numerical values so that the SUM() operator can be used
        *       (the p_premPaym "APPTYPE" position is deleted later on, so we use in here the numerical values
        *        The acronyms are not replaced all over the code as they ease editing the tables)
        *
        *
            p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") $ (  (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") gt eps) $ PSDPAY_T_A(PPPACT,PSDPAY))
                 =   1 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq perLevl)
                   + 2 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq perSlgthd)
                   + 3 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq perYield)
                   + 4 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq perHistY)
                   + 5 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq perLiveStockUnit)
                   + 6 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq noDirPay)
                   + 7 $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq noPriceSup);

    Departures from CAPRI: Norway's types (noDirPay 6, noPriceSup 7) not here (capri_mod/policy/norway.py gives
    Norway's payments); the conditions (a rate above EPS, a level) the caller's."""
    return _APPTYPE_CI[APPTYPE.lower()] if isinstance(APPTYPE, str) else int(APPTYPE)


def p_premPaym_PRMR(PRMR, PRMR_above):
    r"""p_premPaym(R, PPPACT, PSDPAY, "PRMR") of a region without a rate of its own (EPS is one): the sum of the
    regions' above it (R_RAGG), GAMS's sum of values that may be EPS; None where it keeps its own or the sum gives no
    record. The member states take it from REGEU1015 then REGAGGP, NUTS 1 from the member states, NUTS 2 from NUTS 1.

    CAPRI's GAMS (policy/policy.gms l. 194-196):

            p_premPaym(MS,PPPACT,PSDPAY,"PRMR") $ ((     (NOT p_premPaym(MS,PPPACT,PSDPAY,"PRMR"))
                                                      $  p_dataCopy(MS,PPPACT,"LEVL","Y")) $ PSDPAY_T_A(PPPACT,PSDPAY))
                = SUM(R_RAGG(MS,REGEU1015), p_premPaym(REGEU1015,PPPACT,PSDPAY,"PRMR"));

    and the same at l. 198-200 (from REGAGGP), 237-239 (NUTS 1 from MSAGG) and 266-268 (NUTS 2 from NUTS 1).
    Departures from CAPRI: none (the level's condition the caller's)."""
    if nonzero(PRMR):
        return None
    return gams_sum(PRMR_above)


def p_premPaym_APPTYPE_inherit(PRMR, APPTYPE, APPTYPE_above):
    r"""p_premPaym(R, PPPACT, PSDPAY, "APPTYPE") of a region with a rate above EPS and no application type of its own:
    the sum of the numbers of the regions above it; None where the condition is false or the sum is 0.

    CAPRI's GAMS (policy/policy.gms l. 203-205):

            p_premPaym(MS,PPPACT,PSDPAY,"APPTYPE") $ (    ((p_premPaym(MS,PPPACT,PSDPAY,"PRMR") gt eps)
                                                       $  (NOT p_premPaym(MS,PPPACT,PSDPAY,"APPTYPE"))) $ PSDPAY_T_A(PPPACT,PSDPAY))
              = SUM(R_RAGG(MS,REGEU1015), p_premPaym(REGEU1015,PPPACT,PSDPAY,"APPTYPE"));

    and the same at l. 207-209 (from REGAGGP), 246-248 (NUTS 1) and 276-278 (NUTS 2). Departures from CAPRI: none."""
    if not (above_eps(PRMR) and not APPTYPE):
        return None
    t = sum(APPTYPE_above)
    return t if t else None


def p_entlWght1(PRMR, entlWght1, entlWght1_above):
    r"""p_entlWght1(R, PPPACT, PSDPAY) of a region with a rate above EPS and no weight of its own (EPS is one): GAMS's
    sum of the regions' above it; None where the condition is false or the sum gives no record.

    CAPRI's GAMS (policy/policy.gms l. 211-213):

            p_entlWght1(MS,PPPACT,PSDPAY) $ ((     (p_premPaym(MS,PPPACT,PSDPAY,"PRMR") gt eps)
                                                $  (NOT p_entlWght1(MS,PPPACT,PSDPAY))) $ PSDPAY_T_A(PPPACT,PSDPAY))
             = SUM(R_RAGG(MS,REGEU1015), p_entlWght1(REGEU1015,PPPACT,PSDPAY));

    and the same at l. 215-217 (from REGAGGP), 241-243 (NUTS 1) and 270-273 (NUTS 2). Departures from CAPRI: none."""
    if not (above_eps(PRMR) and not nonzero(entlWght1)):
        return None
    return gams_sum(entlWght1_above)


def p_premPaym_ApFact(APPTYPE, Y=0.0, HSTY=None, HSTY_CERE=0.0, LU=0.0, NONCAP=None):
    r"""p_premPaym(RSEU, PPPACT, PSDPAY, "Ap_premModifFactT"): the application factor of a rate above EPS: 1 per level
    or slaughtered head (types 1, 2); the main yield / 1000 per yield (3), the historical yield (the cereals' where the
    activity has none) per historical yield (4), the livestock units (5), plus for DPNONCAP the subsidies per unit of
    output (NONCAP, given only for that scheme); 0 for no type.

    CAPRI's GAMS (policy/policy.gms l. 317-355):

            p_premPaym(RSEU,PPPACT,PSDPAY,"Ap_premModifFactT") $ ( (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") GT eps)
                                                                     $ (   (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") EQ 1)
                                                                        OR (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") EQ 2))
                                                                      $ PSDPAY_T_A(PPPACT,PSDPAY))
                =
        *     --- apptype perLevl: fixed premium per ha or head
        *     --- apptype perSlgtHd: slaughterings
                     1;

            p_premPaym(RSEU,PPPACT,PSDPAY,"Ap_premModifFactT") $ ( (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") GT eps)
                                                                   $ ( (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") gt 2) $ PSDPAY_T_A(PPPACT,PSDPAY)))

                =
        *     --- apptype perYield: main yield
                   + (sum(PACT_TO_Y(PPPACT,O), p_dataCopy(RSEU,PPPACT,O,"Y")) * 0.001)
                                                     $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq 3)
        *     --- apptype perHisty: historic yield
                   + (p_dataCopy(RSEU,PPPACT,"HSTY","Y") + p_dataCopy(RSEU,"CERE","HSTY","Y") $ (NOT p_dataCopy(RSEU,PPPACT,"HSTY","Y")))
                                                     $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq 4)

        *     --- apptype perLiveStockUnit: Live stock unit
                   + p_LUUnits(pppact)                $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq 5)

    (l. 341-350, Norway's types 6 and 7, with MS_NO on) and

                   + sum(PACT_TO_Y(PPPACT,O), p_dataCopy(RSEU,PPPACT,O,"Y") * 0.001 * p_nonCAPPremOutput(RSEU,O,%1)) $ SAMEAS(PSDPAY,"DPNONCAP");

    Departures from CAPRI: Norway's types not here (capri_mod/policy/norway.py); NONCAP the caller's factor (the sum of
    yield / 1000 x subsidy per unit), not computed here."""
    if APPTYPE in (1, 2):
        return 1.0
    f = 0.0
    if APPTYPE > 2:
        if APPTYPE == 3:
            f += Y * 0.001
        elif APPTYPE == 4:
            f += HSTY or HSTY_CERE
        elif APPTYPE == 5:
            f += LU
        if NONCAP is not None:
            f += NONCAP
    return f


def p_premPaym_PRMD(PRMR, ApFact):
    r"""p_premPaym(RSEU, PPPACT, PSDPAY, "PRMD"): the declared premium per unit of the activity, its rate times the
    application factor, for a rate above EPS (a rate written EPS is set to 0 first, l. 312-313, and so gives none).

    CAPRI's GAMS (policy/policy.gms l. 362-364):

            p_premPaym(RSEU,PPPACT,PSDPAY,"PRMD") $ PSDPAY_T_A(PPPACT,PSDPAY)
                =    p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR")
                   * p_premPaym(RSEU,PPPACT,PSDPAY,"Ap_premModifFactT") $ (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") GT eps);

    In this project's notation: PRMD = PRMR x f. Departures from CAPRI: none (the caller keeps PRMD where f is
    nonzero, as GAMS stores no zero)."""
    return PRMR * ApFact


def p_premPaym_PRMD_reaggregate(PRMD_below, LEVL_below, LEVL):
    r"""p_premPaym(R, PPPACT, PSDPAY, "PRMD") of a NUTS 1 region, a member state or an EU aggregate: the level-weighted
    average of the regions' below it that have a PRMD (sequences in the same order); None where the sum is 0. The
    caller applies the condition (a level above EPS, NTSLVL for NUTS 1 and the member states) and the 0 where the
    region has no level (l. 377, 385, 393, 402).

    CAPRI's GAMS (policy/policy.gms l. 381-383):

            p_premPaym(NUTS1A,PPPACT,PSDPAY,"PRMD") $ (( (p_dataCopy(NUTS1A,PPPACT,"LEVL","Y") gt eps) and NTSLVL) $ PSDPAY_T_A(PPPACT,PSDPAY))
                = sum(MAP_RR(NUTS1A,NUTS2) $ p_premPaym(NUTS2,PPPACT,PSDPAY,"PRMD"),
                         p_premPaym(NUTS2,PPPACT,PSDPAY,"PRMD")*p_dataCopy(NUTS2,PPPACT,"LEVL","Y"))/p_dataCopy(NUTS1A,PPPACT,"LEVL","Y");

    and the same at l. 389-391 (the member states from SRNUTS1) and 398-400 (REGAGGP from the member states).
    In this project's notation: PRMD_R = sum_{r below, PRMD_r} PRMD_r L_r / L_R. Departures from CAPRI: none."""
    v = sum(p * lv for p, lv in zip(PRMD_below, LEVL_below) if p)
    return v / LEVL if v else None


def p_entlWght(entlWght1, APPTYPE, SLGT=0.0):
    r"""p_entlWght(RSEU, PPPACT, PSDPAY): the entitlement weight of a rate above EPS: the weight declared (1 where none,
    0 where EPS), times the slaughtered share of the heads (the slaughter coefficient / 1000) for the schemes per
    slaughtered head (type 2).

    CAPRI's GAMS (policy/policy.gms l. 406-412):

            p_entlWght(RSEU,PPPACT,PSDPAY) $ ( (p_premPaym(RSEU,PPPACT,PSDPAY,"PRMR") GT eps) $ PSDPAY_T_A(PPPACT,PSDPAY))

                =  ( 1 $ (NOT p_entlWght1(RSEU,PPPACT,PSDPAY))
                            + p_entlWght1(RSEU,PPPACT,PSDPAY) $ (p_entlWght1(RSEU,PPPACT,PSDPAY) GT eps))

                  * ( 1. $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") ne 2)
                      + (sum(PACT_TO_I(PPPACT,IYANI), p_dataCopy(RSEU,PPPACT,IYANI,"Y")) * 0.001) $ (p_premPaym(RSEU,PPPACT,PSDPAY,"APPTYPE") eq 2));

    Departures from CAPRI: none (SLGT the caller's slaughter coefficient of the activity)."""
    base = 1.0 if not nonzero(entlWght1) else (entlWght1 if above_eps(entlWght1) else 0.0)
    if APPTYPE == 2:
        base *= SLGT * 0.001
    return base

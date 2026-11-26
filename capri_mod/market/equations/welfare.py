r"""CAPRI's welfare report (reports/welfare.gms, star 3.0): the agricultural profit of the supply models' regions
(ProfitAgr), which the income report computes (capri_mod/income/income_module.py IncomeDistributionModule), and the
market's agents' components (block A4): the GL money metric of the consumers (CSSP, with its price path), the
processing industry's profit (ProfitProc: the processing, the residual feeds and the biofuel industry) and the feed
industry's (ProfitFeed). capri_mod/market/welfare.py (WelfareMixin) loops over the regions and goods and calls them.
"""
from __future__ import annotations

import numpy as np


def p_welfareRes_ProfitAgr(MGVA, LEVL):
    r"""p_welfareRes(RMSSUP, "ProfitAgr"): the agricultural profit, sum over the activities of their gross value added per
    unit (MGVA, the model's net revenue per ha or head) times their levels (sequences in the same order).

    CAPRI's GAMS (reports/welfare.gms l. 448-449):

           p_welfareRes(RMSSUP,"ProfitAgr",XX1,"%SIMY%")
              = SUM(PACT_TO_XX(MPACT,XX1), DATA(RMSSUP,MPACT,"MGVA","%SIMY%") * DATA(RMSSUP,MPACT,"LEVL","%SIMY%")*0.001);

    In this project's notation: ProfitAgr = sum_a MGVA_a L_a. Departures from CAPRI: the units (EUR 1000 from EUR per ha
    or head and 1000 ha or heads; CAPRI's x 0.001 to million EUR); one sum over the activities, not by product (income
    I3); CAPRI's outputs and inputs no activity produces or uses (l. 451-456: the EAAG of NECR, ARES, LRES, SERI, RQUO,
    SERO, NASA; mitiI and mitiO are the activities' since sol_simy.gms l. 1471-1473) not added: none of them is an item
    of the model. Not called by the model's reports yet: the region's total is p_welfareRes_EAAG_ProfitAgr."""
    return float(sum(m * l_ for m, l_ in zip(MGVA, LEVL)))


def p_welfareRes_EAAG_ProfitAgr(MGVA, RENT):
    r"""p_welfareRes(RMSSUP, "EAAG", "ProfitAgr") and p_welfareRes(RMSSUP, "ProfitAgr", "INCE"): the farms' total
    profit, the region's income less the land rents (CAPRI's land market, supremaMrk, as in its 2030 reference run).

    CAPRI's GAMS (reports/welfare.gms l. 841-846):

           p_welfareRes(RMSSUP,"EAAG","ProfitAgr","%SIMY%")   = DATA(RMSSUP,"EAAG","MGVA","%SIMY%")
        $ifi %supremaMrk%==on                                 - DATA(RMSSUP,"EAAG","RENT","%SIMY%")
        *                                                      - DATA(RMSSUP,"EAAG","EmiNetTaxAgr","%SIMY%")
                                                              ;

           p_welfareRes(RMSSUP,"ProfitAgr","INCE","%SIMY%")   = p_welfareRes(RMSSUP,"EAAG","ProfitAgr","%SIMY%")   ;

    In this project's notation: ProfitAgr = MGVA - RENT. Departures from CAPRI: the region's activity-based income
    (sol_simy.gms l. 2586, AGGT, coupling/equations/sol_simy.py DATA_AGGT_MGVA) in place of the product-based EAAG
    MGVA, which CAPRI compares with it (sol_simy.gms l. 2600-2615: a difference above EUR 1,000 is reported) and the
    model does not compute yet (income I2); the caller's units."""
    return float(MGVA) - float(RENT)


def p_pbGL(B):
    r"""p_pbGL(RMS, XX1, YY1, "CUR"): the GL demand's B made symmetric, a missing b_ij taking b_ji (B a matrix; the
    caller's reading sets both halves of each record).

    CAPRI's GAMS (reports/welfare.gms l. 100):

           p_pbGL(RMS,XX1,YY1,"CUR")      $ (not p_pbGL(RMS,XX1,YY1,"CUR") )     = p_pbGL(RMS,YY1,XX1,"CUR");

    Departures from CAPRI: none (where both are set they are equal in the data)."""
    out = np.array(B, dtype=float, copy=True)
    m = (out == 0.0) & (out.T != 0.0)
    out[m] = out.T[m]
    return out


def PS_Y(CPRI0, PR, ARM1P0, has_market):
    r"""PS_Y(RMS, XX1): the consumer prices the GL demand saw at the simulation: CPRI0 + (PR - 1) ARM1P0 for the goods
    with a market (has_market; PR the market's price ratios of those goods, in order), floored at 5% of CPRI0
    (arrays over the region's GL goods).

    CAPRI's GAMS (reports/welfare.gms l. 107-116):

           PS_CAL(RMS,XX1)  = DATA(RMS,"Cpri",XX1,"TRD");
           PS_Y(RMS,XX1)    = PS_CAL(RMS,XX1);

        *
           LOOP ( XX1,
        *
        *      --- set price in current market to price in simulation
        *          ( all markets "after" XX are still at reference prices)
        *
               PS_Y(RMS,XX1)   = DATA(RMS,"Cpri",XX1,"%SIMY%");

    Departures from CAPRI: the simulation's consumer price as the model's GL demand computes it (gl_food_ratio, with
    its 5% floor), not DATA Cpri of the simulation (the same price where the floor does not bind); the loop over the
    goods is the caller's (_gl_money_metric)."""
    p = np.array(CPRI0, dtype=float, copy=True)
    m = np.asarray(has_market)
    p[m] = p[m] + (PR - 1.0) * ARM1P0[m]
    return np.maximum(p, 0.05 * CPRI0)


def p_welfareRes_CSSP(B, d, Y, PS_CAL, PS_Y):
    r"""p_welfareRes(RMS, "CSSP", XX1, SIMY): the equivalent variation of the step that moves good XX1 from the
    calibration price to the simulation one, EUR per head: G(PS_CAL) / G(PS_Y) (Y - d PS_Y) - (Y - d PS_CAL) with
    G(p) = sum_ij b_ij sqrt(p_i p_j) and d PS_CAL the demand's FS at the prices before the step (v_GLDemandFS, l. 120).

    CAPRI's GAMS (reports/welfare.gms l. 124-138):

               p_welfareRes(RMS,"CSSP",XX1,"%SIMY%") $ p_pbGL(RMS,XX1,XX1,"CUR")
        *
        *        --- value of function G = SUMij Bij Pi-0.5 Pj-0.5
        *
                  =    SUM( (YY1,ZZ1) $ p_pbGL(RMS,YY1,ZZ1,"CUR"),
                             p_pbGL(RMS,YY1,ZZ1,"CUR")
                                  * SQRT(PS_CAL(RMS,YY1) *  PS_CAL(RMS,ZZ1) * 1.E-6))
                     / SUM( (YY1,ZZ1) $ p_pbGL(RMS,YY1,ZZ1,"CUR"),
                             p_pbGL(RMS,YY1,ZZ1,"CUR")
                                  * SQRT(PS_Y(RMS,YY1) * PS_Y(RMS,ZZ1) * 1.E-6))
        *
                      *  (DATA(RMS,"Ince","LEVL","CUR")/DATA(RMS,"INHA","LEVL","CUR")
                            - SUM(ZZ1 $ p_pdGL(RMS,ZZ1,"CUR"), p_pdGL(RMS,ZZ1,"CUR") * PS_Y(RMS,ZZ1))/1000.)
        *
                       - (DATA(RMS,"Ince","LEVL","CUR")/DATA(RMS,"INHA","LEVL","CUR") -  v_GLDemandFS.l(RMS));

    In this project's notation: EV = G(P0) / G(P1) (Y - d P1) - (Y - d P0). Departures from CAPRI: G as sqrt(p) B
    sqrt(p) (CAPRI's x 1e-6 inside the roots cancels in the ratio); the model's units (Y per head, d in its prices);
    the caller skips a good without an own b term (the condition)."""
    G = lambda p: float(np.sqrt(p) @ B @ np.sqrt(p))
    return G(PS_CAL) / G(PS_Y) * (Y - float(d @ PS_Y)) - (Y - float(d @ PS_CAL))


def p_welfareRes_ProfitProc(q0, dq, dp):
    r"""p_welfareRes(RMS, "ProfitProc", XX, SIMY) of the processing (ProcNQ_, the goods other than oilseeds and
    biofuels): one processed good's term on the straight path, (q0 + dq / 2) dp, q0 its base processing, dq the
    processing's change (the Hessian's response to the price changes) and dp the change of its Armington price; the
    caller subtracts it (the goods are inputs) and sums over the goods.

    CAPRI's GAMS (reports/welfare.gms l. 183-187):

               p_welfareRes(RMS,"ProfitProc",XX,"%SIMY%")
                 =          SUM(  ZZ $ p_cnstNQProc(RMS,ZZ), p_cnstNQProc(RMS,ZZ)    * (PS_Y(RMS,ZZ) - PS_CAL(RMS,ZZ))) * 0.001
                    + 0.5 * SUM( (ZZ,YY) $ p_hessNQProc(RMS,ZZ,YY,"CUR"),
                                           p_hessNQProc(RMS,ZZ,YY,"CUR")
                                             * ( PS_Y(RMS,ZZ)*PS_Y(RMS,YY) -PS_CAL(RMS,ZZ)*PS_CAL(RMS,YY))) * 0.001;

    In this project's notation: dPi = - sum_x (q0_x + dq_x / 2) dp_x. Departures from CAPRI: the straight-path
    integral of the linear processing, all prices at once (CAPRI's good by good, the same value for its symmetric
    Hessian); the normalisation by the input price (l. 193) and the margin at the calibration point (l. 195-196) not
    applied (the components are changes plus CAPRI's base values, capri_mod/market/welfare.py)."""
    return (q0 + 0.5 * dq) * dp


def p_welfareRes_ProfitProc_RESIMPX(Prod, PPRI0, price_ratio, Prod0):
    r"""p_welfareRes(RMSSUP, "ProfitProc", RESIMPX, SIMY): the residual feeds' (FENI, FPRI) output value change of the
    regions with supply models, Prod x PPRI at the simulation less at the reference, million EUR (the simulation's
    PPRI the reference's times the market's price ratio).

    CAPRI's GAMS (reports/welfare.gms l. 201-204):

           p_welfareRes(RMSSUP,"ProfitProc",RESIMPX,"%SIMY%") $ DATA(RMSSUP,"Prod",RESIMPX,"TRD")
             =  p_welfareRes(RMSSUP,"ProfitProc",RESIMPX,"%SIMY%")
                 + (  ( DATA(RMSSUP,"Prod",RESIMPX,"%SIMY%") * DATA(RMSSUP,"PPRI",RESIMPX,"%SIMY%"))
                    - ( DATA(RMSSUP,"Prod",RESIMPX,"TRD")    * DATA(RMSSUP,"PPRI",RESIMPX,"TRD"))) * 0.001;

    Departures from CAPRI: / 1000 (CAPRI's x 0.001: the same value up to rounding); per model region (the EU's)."""
    return (Prod * PPRI0 * price_ratio - Prod0 * PPRI0) / 1000.0


def p_welfareRes_ProfitProc_XXBIOF(ProcMarg, FSTG, ProcMarg0, FSTG0):
    r"""p_welfareRes(RMS, "ProfitProc", XXBIOF, SIMY): the biofuel industry's profit change, its margin x its first
    generation output at the simulation less at the reference, million EUR.

    CAPRI's GAMS (reports/welfare.gms l. 211-213):

           p_welfareRes(RMS,"ProfitProc",XXBIOF,"%SIMY%") $ (DATA(RMS,"Prod",XXBIOF,"TRD") and data(RMS,"ProcMarg",XXBIOF,"%SIMY%"))
            = data(rms,"procMarg",XXBIOF,"%SIMY%") * DATA(RMS,"FSTG",XXBIOF,"%SIMY%") * 0.001
            - data(rms,"procMarg",XXBIOF,"TRD")    * DATA(RMS,"FSTG",XXBIOF,"TRD")    * 0.001;

    Departures from CAPRI: the difference divided by 1000 (CAPRI's each term x 0.001: the same value up to
    rounding)."""
    return (ProcMarg * FSTG - ProcMarg0 * FSTG0) / 1000.0


def p_welfareRes_ProfitFeed(p0, price_ratio, q0, dq):
    r"""p_welfareRes(RMS, "ProfitFeed", XX1, SIMY) of the regions without supply models with CAPRI's feed functions
    (FeedNQ_): one feed's (or the feed energy's, FEDE) term on the straight path, p0 (r - 1) (q0 + dq / 2), the
    caller subtracting the feeds' and adding the energy's.

    CAPRI's GAMS (reports/welfare.gms l. 507-514):

               p_welfareRes(RMS,"ProfitFeed",XX1,"%SIMY%") $ p_cnstNQFeed(RMS,XX1)
                 =          - SUM(  ZZ1 $ p_cnstNQFeed(RMS,ZZ1),
                                    p_cnstNQFeed(RMS,ZZ1) * ( PS_Y(RMS,ZZ1) - PS_CAL(RMS,ZZ1))) * 0.001

                      - 0.5 * SUM( (ZZ1,YY1) $ p_hessNQFeed(RMS,ZZ1,YY1,"CUR"),
                                     p_hessNQFeed(RMS,ZZ1,YY1,"CUR")
                                     * ( PS_Y(RMS,ZZ1) * PS_Y(RMS,YY1)
                                       - PS_CAL(RMS,ZZ1) * PS_CAL(RMS,YY1) ))  * 0.001;

    with the prices PS_Y (l. 497-505) the Armington prices net of FSEi over the input price, FEDE's its producer
    price. In this project's notation: dPi = - sum_x p0_x (r_x - 1)(F0_x + dF_x / 2) + p_E (phi - 1)(E0 + dE / 2).
    Departures from CAPRI: the straight-path integral (all prices at once; CAPRI's good by good, the same value for
    its symmetric Hessian); the energy's term from the energy fed (REGISTERED: it stands for CAPRI's FEDE row)."""
    return p0 * (price_ratio - 1.0) * (q0 + 0.5 * dq)


def p_welfareRes_Welfare(components):
    r"""p_welfareRes(RMAll, "Welfare", ROWS1, SIMY): the total welfare, the sum of its components per region (a
    DataFrame of the components by region; pandas' sum over the columns).

    CAPRI's GAMS (reports/welfare.gms l. 872-885):

           p_welfareRes(RMAll,"Welfare",ROWS1,"%SIMY%")
              =  p_welfareRes(RMAll,"CSSP",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"ProfitProc",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"ProfitDairy",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"ProfitAgr",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"ProfitFeed",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"TariffRev",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"ProfitLandUse",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"TRQRents",ROWS1,"%SIMY%")
        *        need to include emission tax levied on agriculture in RMSSUP if this emission tax is deducted from ag income
        *       + p_welfareRes(RMAll,"EmiNetTaxAgr",ROWS1,"%SIMY%")
        *        need to include emission tax levied on processing or input supply industry if these have decreased PRIC and increased CPRI
        *       + p_welfareRes(RMAll,"EmiNetTaxOth",ROWS1,"%SIMY%")
               + p_welfareRes(RMAll,"PSES",ROWS1,"%SIMY%");

    Departures from CAPRI: the market's agents' components (CSSP, ProfitProc, ProfitDairy, ProfitAgr, ProfitFeed,
    TariffRev, TRQRents); the supply models' ProfitLandUse and PSES are coupling/reporting.py's, added in its totals."""
    return components.sum(axis=1)

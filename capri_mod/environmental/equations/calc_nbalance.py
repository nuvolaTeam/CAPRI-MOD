r"""CAPRI's gross nutrient balance (reports/calc_nbalance.gms, star 3.0): the items of the phosphate balance (FNUT =
PHOF) the accounts compute, the manure P2O5 run off (RUNANI) and the sums IMPORT, SURTOT, SURSOI.

For phosphate CAPRI's sums have no BIOFIX, ATMOSD, MINSAT, GASANI, GASMIN, RUNMIN or GASRES terms (their $ SAMEAS(FNUT,
"NITF") conditions, or no data), so they reduce to the forms below. CAPRI reports the items in 1000 t and per ha of UAAR;
the accounts keep t P2O5 (1000 ha x kg/ha). MTRADE enters with ManureTradeReporting on (the manure trade).

Used by capri_mod/environmental/phosphorus.py (PhosphorusBlock.compute_phosphorus_balance) and p_balance.py (balance).
"""
from __future__ import annotations


def DATA_RUNANI(LEVL, MANP, RunTot):
    r"""DATA(RUNR, "RUNANI", PHOF): one animal's term of the manure P2O5 run off, its level x its manure P2O5 per head x
    its manure N's runoff share RunTot (v_emiLoss.l(N, RunTot), CAPRI's N share applied to P). The caller sums over the
    animals (MAACT).

    CAPRI's GAMS (reports/calc_nbalance.gms l. 103-105):

           DATA(RUNR,"RUNANI",FNUT,%1)       = SUM(MAACT $ DATA(RUNR,MAACT,"LEVL",%1),
                                                     SUM(FOUT_T_N(FOUT, FNUT), DATA(RUNR,MAACT,"LEVL",%1) * DATA(RUNR,MAACT,FOUT,%1)
                                                        * (v_emiLoss.l(RUNR,MAACT,"N","RunTot") + p_emiLoss(RUNR,MAACT,"N","RunTot") $ (not v_emiLoss.l(RUNR,MAACT,"N","RunTot"))))) * 0.001;

    In this project's notation: RUNANI = sum_a L_a MANP_a RunTot_a. Departures from CAPRI: the units (t, not 1000 t: no
    x 0.001); RunTot from the loss cascade at the solution's option shares (capri_mod/environmental/phosphorus.py
    _p_runtot), CAPRI's p_emiLoss fallback where v_emiLoss is 0 not needed (the cascade gives a share everywhere it has
    data; none elsewhere)."""
    return LEVL * MANP * RunTot


def DATA_IMPORT(EXCRET, MTRADE, MINFER, CRESID):
    r"""DATA(RUNR, "IMPORT", PHOF): the phosphate entering the soil, EXCRET - MTRADE + MINFER + CRESID.

    CAPRI's GAMS (reports/calc_nbalance.gms l. 237-243):

           DATA(RUNR,"IMPORT",FNUT,%1)   =    DATA(RUNR,"EXCRET",FNUT,%1)
        $ifi  %ManureTradeReporting% == on         - DATA(RUNR,"MTRADE",FNUT,%1)
                                          + DATA(RUNR,"MINFER",FNUT,%1)
                                          + DATA(RUNR,"BIOFIX",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"ATMOSD",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"MINSAT",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"CRESID",FNUT,%1);

    Departures from CAPRI: none (the NITF terms are 0 for PHOF)."""
    return EXCRET - MTRADE + MINFER + CRESID


def DATA_SURTOT(IMPORT, EXPPRD):
    r"""DATA(RUNR, "SURTOT", PHOF): the gross phosphate surplus, IMPORT - EXPPRD (CAPRI writes the sum out; the same
    additions in the same order).

    CAPRI's GAMS (reports/calc_nbalance.gms l. 305-313):

           DATA(RUNR,"SURTOT",FNUT,%1)   =    DATA(RUNR,"EXCRET",FNUT,%1)
        $ifi  %ManureTradeReporting% == on         - DATA(RUNR,"MTRADE",FNUT,%1)
                                          + DATA(RUNR,"MINFER",FNUT,%1)
                                          + DATA(RUNR,"BIOFIX",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"ATMOSD",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"MINSAT",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"CRESID",FNUT,%1)
                                          - DATA(RUNR,"EXPPRD",FNUT,%1)
                                          ;

    Departures from CAPRI: none."""
    return IMPORT - EXPPRD


def DATA_SURSOI(SURTOT, RUNANI):
    r"""DATA(RUNR, "SURSOI", PHOF): the phosphate surplus to the soil, SURTOT - RUNANI (phosphate has no gaseous losses).

    CAPRI's GAMS (reports/calc_nbalance.gms l. 247-265):

           DATA(RUNR, "SURSOI", FNUT, %1) =
        *   v_nutSurSoiKt.L(RUNR, FNUT) $(v_nutSurSoiKt.L(RUNR, FNUT))
        *                                  + (
                                            DATA(RUNR,"EXCRET",FNUT,%1)
        $ifi  %ManureTradeReporting% == on         - DATA(RUNR,"MTRADE",FNUT,%1)
                                          + DATA(RUNR,"MINFER",FNUT,%1)
                                          + DATA(RUNR,"BIOFIX",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"ATMOSD",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"MINSAT",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          + DATA(RUNR,"CRESID",FNUT,%1)
                                          - DATA(RUNR,"EXPPRD",FNUT,%1)
                                          - DATA(RUNR,"GASANI",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          - DATA(RUNR,"GASMIN",FNUT,%1) $ SAMEAS(FNUT,"NITF")
                                          - DATA(RUNR,"RUNANI",FNUT,%1) $ DATA(RUNR,"RUNANI",FNUT,%1)
                                          - DATA(RUNR,"RUNMIN",FNUT,%1) $ DATA(RUNR,"RUNMIN",FNUT,%1)
                                          - DATA(RUNR,"GASRES",FNUT,%1)  $ SAMEAS(FNUT,"NITF")
        *                                   )$(NOT v_nutSurSoiKt.L(RUNR, FNUT))
                                          ;

    Departures from CAPRI: none (the NITF terms are 0 for PHOF; RUNMIN has no data for phosphate)."""
    return SURTOT - RUNANI

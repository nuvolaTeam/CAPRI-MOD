r"""CAPTRD's bound statements of captrd/biofuel_bounds.gms (CAPRI star 3.0): the biofuels' bounds (fix_est.gms l. 845), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (the assignments
refactor's style: one function per statement block, named after the bounded symbol, V_EstV.LO / .UP / .FX). The
functions take the numbers the statement reads and return the bound; capri_mod/pipeline/captrd/estimate_bounds.py
(bounds) holds the domain conditions, the loops over the sets and the order of the statements, and calls them. A
bound "before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its
order of operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_PRCB(c, support):
    r"""V_EstV.LO and .UP of the biofuel feedstocks' processing (PRCB: 0.1% around the support) and their yields
    (PRCBY: fixed at the support). Returns (lo, up).

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 19-24):

           V_EstV.LO(REST,"PRCB",bioStock,exAnte)     $ (P_DATA(Rest,"PRCB",bioStock,"nObs") ) = P_Result(Rest,"PRCB",bioStock,Exante,"SUPPORT") * 0.999;
           V_EstV.L(REST,"PRCB",bioStock,exAnte)      $ (P_DATA(Rest,"PRCB",bioStock,"nObs") ) = P_Result(Rest,"PRCB",bioStock,Exante,"SUPPORT") * 1;
           V_EstV.UP(REST,"PRCB",bioStock,exAnte)     $ (P_DATA(Rest,"PRCB",bioStock,"nObs") ) = P_Result(Rest,"PRCB",bioStock,Exante,"SUPPORT") * 1.001;
           V_EstV.LO(REST,"PRCBY",bioStock,exAnte)    $ (P_DATA(Rest,"PRCBY",bioStock,"nObs") ) = P_Result(Rest,"PRCBY",bioStock,Exante,"SUPPORT") * 1;
           V_EstV.L(REST,"PRCBY",bioStock,exAnte)     $ (P_DATA(Rest,"PRCBY",bioStock,"nObs") ) = P_Result(Rest,"PRCBY",bioStock,Exante,"SUPPORT") * 1;
           V_EstV.UP(REST,"PRCBY",bioStock,exAnte)    $ (P_DATA(Rest,"PRCBY",bioStock,"nObs") ) = P_Result(Rest,"PRCBY",bioStock,Exante,"SUPPORT") * 1;

    the levels V_EstV.L CAPRI sets alongside (l. 20, 23) are the start point's, not set here; the domain condition in the
    caller (estimate_bounds._biofuel)."""
    if c == "PRCB":
        return support * 0.999, support * 1.001
    return support, support


def V_EstV_BIOF_bioStock(support):
    r"""V_EstV.LO and .UP of a feedstock's biofuel use: 80% and 120% of its support. Returns (lo, up).

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 27-28):

           V_EstV.LO(REST,"BIOF",bioStock,exAnte)    $ (P_DATA(Rest,"BIOF",bioStock,"nObs") ) = P_Result(Rest,"BIOF",bioStock,Exante,"SUPPORT") * 0.8;
           V_EstV.UP(REST,"BIOF",bioStock,exAnte)    $ (P_DATA(Rest,"BIOF",bioStock,"nObs") ) = P_Result(Rest,"BIOF",bioStock,Exante,"SUPPORT") * 1.2;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return support * 0.8, support * 1.2


def V_EstV_lo_BIOF_SUGA():
    r"""V_EstV.LO of sugar's biofuel use where sugar beet's production is fixed at zero: zero.

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 31-31):

           V_EstV.LO(REST,"BIOF","SUGA",exAnte)    $ (V_EstV.up(REST,"GROF","SUGB",exAnte) = 0) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_SECO_BIOF(c, support):
    r"""V_EstV.LO and .UP of the biofuels' secondary products' positions around their supports (MAPR, INDM, NAGR,
    UVAD 5%, BIOF -0.01% and +5%, SECG 1%). Returns (lo, up).

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 34-45):

           V_EstV.LO(REST,"MAPR",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"MAPR",SECO_BIOF,"nObs") ) = P_Result(Rest,"MAPR",SECO_BIOF,Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"MAPR",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"MAPR",SECO_BIOF,"nObs") ) = P_Result(Rest,"MAPR",SECO_BIOF,Exante,"SUPPORT") * 1.05;
           V_EstV.LO(REST,"BIOF",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"BIOF",SECO_BIOF,"nObs") ) = P_Result(Rest,"BIOF",SECO_BIOF,Exante,"SUPPORT") * 0.9999;
           V_EstV.UP(REST,"BIOF",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"BIOF",SECO_BIOF,"nObs") ) = P_Result(Rest,"BIOF",SECO_BIOF,Exante,"SUPPORT") * 1.05;
           V_EstV.LO(REST,"INDM",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"INDM",SECO_BIOF,"nObs") ) = P_Result(Rest,"INDM",SECO_BIOF,Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"INDM",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"INDM",SECO_BIOF,"nObs") ) = P_Result(Rest,"INDM",SECO_BIOF,Exante,"SUPPORT") * 1.05;
           V_EstV.LO(REST,"SECG",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"SECG",SECO_BIOF,"nObs") ) = P_Result(Rest,"SECG",SECO_BIOF,Exante,"SUPPORT") * 0.99;
           V_EstV.UP(REST,"SECG",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"SECG",SECO_BIOF,"nObs") ) = P_Result(Rest,"SECG",SECO_BIOF,Exante,"SUPPORT") * 1.01;
           V_EstV.LO(REST,"NAGR",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"NAGR",SECO_BIOF,"nObs") ) = P_Result(Rest,"NAGR",SECO_BIOF,Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"NAGR",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"NAGR",SECO_BIOF,"nObs") ) = P_Result(Rest,"NAGR",SECO_BIOF,Exante,"SUPPORT") * 1.05;
           V_EstV.LO(REST,"UVAD",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"UVAD",SECO_BIOF,"nObs") ) = P_Result(Rest,"UVAD",SECO_BIOF,Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"UVAD",SECO_BIOF,exAnte)    $ (P_DATA(Rest,"UVAD",SECO_BIOF,"nObs") ) = P_Result(Rest,"UVAD",SECO_BIOF,Exante,"SUPPORT") * 1.05;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    fl, fu = {"MAPR": (0.95, 1.05), "BIOF": (0.9999, 1.05), "INDM": (0.95, 1.05), "SECG": (0.99, 1.01),
              "NAGR": (0.95, 1.05), "UVAD": (0.95, 1.05)}[c]
    return support * fl, support * fu


def V_EstV_fx_NAGR_SECG():
    r"""V_EstV.FX of NAGR and SECG of the biofuels' secondary products without data: zero.

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 46-47):

           V_EstV.FX(REST,"NAGR",SECO_BIOF,exAnte)    $ ( NOT P_DATA(Rest,"NAGR",SECO_BIOF,"nObs") ) = 0;
           V_EstV.FX(REST,"SECG",SECO_BIOF,exAnte)    $ ( NOT P_DATA(Rest,"SECG",SECO_BIOF,"nObs") ) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_NECR(support):
    r"""V_EstV.LO and .UP of the energy crops' level and output (NECR, LEVL and OCRO): 5% around the support.
    Returns (lo, up).

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 51-55):

           V_EstV.LO(REST,"NECR","LEVL",exAnte)    $ (P_DATA(Rest,"NECR","LEVL","nObs") ) = P_Result(Rest,"NECR","LEVL",Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"NECR","LEVL",exAnte)    $ (P_DATA(Rest,"NECR","LEVL","nObs") ) = P_Result(Rest,"NECR","LEVL",Exante,"SUPPORT") * 1.05;

           V_EstV.LO(REST,"NECR","OCRO",exAnte)    $ (P_DATA(Rest,"NECR","LEVL","nObs") ) = P_Result(Rest,"NECR","OCRO",Exante,"SUPPORT") * 0.95;
           V_EstV.UP(REST,"NECR","OCRO",exAnte)    $ (P_DATA(Rest,"NECR","LEVL","nObs") ) = P_Result(Rest,"NECR","OCRO",Exante,"SUPPORT") * 1.05;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return support * 0.95, support * 1.05


def V_EstV_fx_BIOF_tiny():
    r"""V_EstV.FX of a biofuel position with a support of at most 1e-14: zero.

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 59-61):

          V_EstV.FX(REST,cols,rows,exAnte) $ (  (ABS(P_Result(Rest,cols,rows,Exante,"SUPPORT")) LE 1e-14)
                                              $ P_Result(Rest,cols,rows,Exante,"SUPPORT")
                                              $ (BIOFrelatedCOLS(cols) or BIOFrelatedROWS(rows))) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_fx_BIOF_CERE_MAPR_BIOE():
    r"""V_EstV.FX of the cereals' biofuel use and ethanol's processing below 1e-13 of support: zero.

    CAPRI's GAMS (captrd/biofuel_bounds.gms l. 64-65):

          V_EstV.FX(REST,"BIOF","CERE",exAnte) $ (P_Result(Rest,"BIOF","CERE",Exante,"SUPPORT") LT 1e-13) = 0;
          V_EstV.FX(REST,"MAPR","BIOE",exAnte) $ (P_Result(Rest,"MAPR","BIOE",Exante,"SUPPORT") LT 1e-13) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0

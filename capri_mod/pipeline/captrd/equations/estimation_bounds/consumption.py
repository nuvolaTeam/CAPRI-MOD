r"""CAPTRD's estimation bounds of the population, the food shares and human consumption (captrd/fix_est.gms; moved from
capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




def V_EstV_INHA(bast, basm, n_bast, n_bas):
    r"""V_EstV.LO and .UP of a food intake: 2% a year around BAST, else BASM.

    bast, basm: p_data(., "INHA", w, "BAST" / "BASM"); n_bast, n_bas: OrdT(ExanteT) - OrdT("BAST") and -
    OrdT("BAS"). Returns (lo, up).

    As GAMS reads the statement, the second $ conditions the exponent only (it binds to the operand before it), so
    where BAST exists the second term is BASM x 0.98^0 = BASM: the bounds are BAST x 0.98^n + BASM and BAST x 1.02^n
    + BASM, about twice the intended ones. Kept as coded: CAPTRD's stored bounds show it in every country and year
    (CAPRI-ERROR, not fixed: the bounds CAPTRD then widens are these).

    CAPRI's GAMS (captrd/fix_est.gms l. 269-279):

           v_estV.LO(Rest,"INHA",S_RowsEst,ExanteT) $ (p_data(Rest,"INHA",S_RowsEst,"nObs") $ (NOT GRPR(S_RowsEst))
                                                       $(NOT p_globiomTightLink(Rest,"INHA",S_RowsEst,"%SelecScen%",ExanteT))
                                                       $ (NOT P_Result(Rest,"INHA",S_RowsEst,ExanteT,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA",S_RowsEst,"BAST") * 0.98**(OrdT(ExanteT)-OrdT("BAST")) $ (    p_data(Rest,"INHA",S_RowsEst,"BAST") )
                + p_data(Rest,"INHA",S_RowsEst,"BASM") * 0.98**(OrdT(ExanteT)-OrdT("BAS"))  $ (not p_data(Rest,"INHA",S_RowsEst,"BAST") );
        *
           v_estV.UP(Rest,"INHA",S_RowsEst,ExanteT) $ (p_data(Rest,"INHA",S_RowsEst,"nObs") $ (NOT GRPR(S_RowsEst))
                                                       $(NOT p_globiomTightLink(Rest,"INHA",S_RowsEst,"%SelecScen%",ExanteT))
                                                       $ (NOT P_Result(Rest,"INHA",S_RowsEst,ExanteT,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA",S_RowsEst,"BAST") * 1.02**(OrdT(ExanteT)-OrdT("BAST")) $ (    p_data(Rest,"INHA",S_RowsEst,"BAST") )
                + p_data(Rest,"INHA",S_RowsEst,"BASM") * 1.02**(OrdT(ExanteT)-OrdT("BAS"))  $ (not p_data(Rest,"INHA",S_RowsEst,"BAST") );

    none (CAPRI's reading of the $, above); p_globiomTightLink is empty (l. 261-264 sets nothing); the domain condition in
    the caller (estimate_bounds.bounds)."""
    e2 = 0 if bast else n_bas
    lo = (bast * 0.98 ** n_bast if bast else 0.0) + basm * 0.98 ** e2
    up = (bast * 1.02 ** n_bast if bast else 0.0) + basm * 1.02 ** e2
    return lo, up


def V_EstV_foodSh(base, n):
    r"""V_EstV.LO and .UP of a food share: 0.2% a year around BAST, else BASM.

    base: BAST, else BASM; n: the years since it. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 284-292):

           v_estV.LO(Rest,"foodSh",S_RowsEst,ExanteT) $ (p_data(Rest,"foodSh",S_RowsEst,"nObs")
                                                       $ (NOT P_Result(Rest,"foodSh",S_RowsEst,ExanteT,"coco")) $ NUTS0(Rest))
                = (p_data(Rest,"foodSh",S_RowsEst,"BAST") * 0.998**(OrdT(ExanteT)-OrdT("BAST"))) $ (    p_data(Rest,"foodSh",S_RowsEst,"BAST") )
                + (p_data(Rest,"foodSh",S_RowsEst,"BASM") * 0.998**(OrdT(ExanteT)-OrdT("BAS")) ) $ (not p_data(Rest,"foodSh",S_RowsEst,"BAST") );
        *
           v_estV.UP(Rest,"foodSh",S_RowsEst,ExanteT) $ (p_data(Rest,"foodSh",S_RowsEst,"nObs")
                                                       $ (NOT P_Result(Rest,"foodSh",S_RowsEst,ExanteT,"coco")) $ NUTS0(Rest))
                = (p_data(Rest,"foodSh",S_RowsEst,"BAST") * 1.002**(OrdT(ExanteT)-OrdT("BAST"))) $ (    p_data(Rest,"foodSh",S_RowsEst,"BAST") )
                + (p_data(Rest,"foodSh",S_RowsEst,"BASM") * 1.002**(OrdT(ExanteT)-OrdT("BAS")) ) $ (not p_data(Rest,"foodSh",S_RowsEst,"BAST") );

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return base * 0.998 ** n, base * 1.002 ** n


def V_EstV_INHA_MEAS_CERE(g, basm, n):
    r"""V_EstV.LO and .UP of the food intake of meats (1% a year) and cereals (0.6% a year).

    g: "MEAS" or "CERE"; basm: p_data(., "INHA", g, "BASM"); n: OrdT(Exante) - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 300-318):

           v_estV.UP(Rest,"INHA","MEAS",Exante) $ (p_data(Rest,"INHA","MEAS","nObs")
                                                       $(NOT p_globiomTightLink(Rest,"INHA","MEAS","%SelecScen%",Exante))
                                                       $ (NOT P_Result(Rest,"HCOM","MEAS",ExAnte,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA","MEAS","BASM") * 1.01**(OrdT(Exante)-OrdT("BAS"));

           v_estV.LO(Rest,"INHA","MEAS",Exante) $ (p_data(Rest,"INHA","MEAS","nObs")
                                                       $(NOT p_globiomTightLink(Rest,"INHA","MEAS","%SelecScen%",Exante))
                                                       $ (NOT P_Result(Rest,"HCOM","MEAS",ExAnte,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA","MEAS","BASM") * 0.99**(OrdT(Exante)-OrdT("BAS"));
        *
           v_estV.UP(Rest,"INHA","CERE",Exante) $ (p_data(Rest,"INHA","CERE","nObs")
                                                       $(NOT p_globiomTightLink(Rest,"INHA","CERE","%SelecScen%",Exante))
                                                       $ (NOT P_Result(Rest,"HCOM","CERE",ExAnte,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA","CERE","BASM") * 1.006**(OrdT(Exante)-OrdT("BAS"));

           v_estV.LO(Rest,"INHA","CERE",Exante) $ (p_data(Rest,"INHA","CERE","nObs")
                                                       $(NOT p_globiomTightLink(Rest,"INHA","CERE","%SelecScen%",Exante))
                                                       $ (NOT P_Result(Rest,"HCOM","CERE",ExAnte,"coco")) $ NUTS0(Rest))
                = p_data(Rest,"INHA","CERE","BASM") * 0.994**(OrdT(Exante)-OrdT("BAS"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    hi, lw = {"MEAS": (1.01, 0.99), "CERE": (1.006, 0.994)}[g]
    return basm * lw ** n, basm * hi ** n


def V_EstV_INHA_seco_bioF():
    r"""V_EstV.LO and .UP of the food intake of the biofuels' secondary products: free above zero. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 322-323):

           v_estV.UP(Rest,"INHA",seco_bioF,Exante) $ (p_data(Rest,"INHA",seco_bioF,"nObs") $ NUTS0(Rest)) = +inf;
           v_estV.LO(Rest,"INHA",seco_bioF,Exante) $ (p_data(Rest,"INHA",seco_bioF,"nObs") $ NUTS0(Rest) ) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0, float("inf")


def V_EstV_HCOM(up_inha, lo_inha, pop):
    r"""V_EstV.UP and .LO of human consumption from the food intake's bounds and the population, and DOMM's upper
    bound at least HCOM's (and 1e9).

    up_inha, lo_inha: V_EstV.UP / .LO(., "INHA", w); pop: p_result(., "INHA", "LEVL", "p_data"). Returns (up_hcom,
    up_domm, lo_hcom).

    CAPRI's GAMS (captrd/fix_est.gms l. 328-339):

           v_estV.UP(Rest,"HCOM",S_RowsEst,Exante) $ (p_data(Rest,"INHA",S_RowsEst,"nObs") $ NUTS0(Rest)
                                                       $(NOT p_globiomTightLink(Rest,"INHA",S_RowsEst,"%SelecScen%",Exante)))

              = v_estV.UP(Rest,"INHA",S_RowsEst,Exante) * p_result(Rest,"INHA","LEVL",ExAnte,"p_data")  * 0.001 * 1000.;
        *
        *      prevent that HCOM is indirectly bounded upwards (perhaps to zero)
           v_estV.UP(Rest,"DOMM",S_RowsEst,Exante) $ (p_data(Rest,"INHA",S_RowsEst,"nObs") $ NUTS0(Rest))
              = MAX(v_estV.UP(Rest,"HCOM",S_RowsEst,Exante),1.E+9);

           v_estV.LO(Rest,"HCOM",S_RowsEst,Exante) $ (p_data(Rest,"INHA",S_RowsEst,"nObs") $ NUTS0(Rest)
                                                       $(NOT p_globiomTightLink(Rest,"INHA",S_RowsEst,"%SelecScen%",Exante)))
              = v_estV.LO(Rest,"INHA",S_RowsEst,Exante) * p_result(Rest,"INHA","LEVL",ExAnte,"p_data") * 0.001 / 1000.;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    up_hcom = up_inha * pop * 0.001 * 1000.0
    up_domm = max(up_hcom, 1.0e9)
    lo_hcom = lo_inha * pop * 0.001 / 1000.0
    return up_hcom, up_domm, lo_hcom

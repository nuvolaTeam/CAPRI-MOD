r"""CAPTRD's estimation bounds of the yields' growth and the unit values (captrd/fix_est.gms; moved from
capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




def p_data_GROF_maxFacPerY(ms, n_pork, n_pouf, west, east):
    r"""p_data(Rest, "GROF", PORK / POUF, "maxFacPerY"): the largest yearly growth of pork and poultry production in
    the EU (1% and 1.5% in the west, 1.5% and 2% in the east; the Netherlands' and Denmark's pork their own).

    ms: the member state; n_pork, n_pouf: GROF has data; west, east: the member state's EU aggregate
    (MS_TO_RMSAGG). Returns {row: factor} in the statements' order.

    CAPRI's GAMS (captrd/fix_est.gms l. 206-225):

           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ( p_data(Rest,"GROF",s_rowsEst,"nObs")
                                                        $ sameas("PORK",s_rowsEst)
                                                        $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.01;
           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ((SAMEAS(Rest,"NL000000") ) $ sameas("PORK",s_rowsEst))                             = 1.0025;
           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ((SAMEAS(Rest,"DK000000") ) $ sameas("PORK",s_rowsEst))                             = 1.005;

        *         - poultry production in EU15: 1.5% per year
        *           (a bit more than for pork becasue dem$ growth is stronger $ manure might be incinerated)
           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ( p_data(Rest,"GROF",s_rowsEst,"nObs")
                                                        $ sameas("POUF",s_rowsEst)
                                                        $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.015;

        *         - In EU12 we permit 0.5% more growth compared to EU15
           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ( p_data(Rest,"GROF",s_rowsEst,"nObs")
                                                        $ sameas("PORK",s_rowsEst)
                                                        $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.015;

           p_data(Rest,"GROF",s_rowsEst,"maxFacPerY") $ ( p_data(Rest,"GROF",s_rowsEst,"nObs")
                                                        $ sameas("POUF",s_rowsEst)
                                                        $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.02;

    the Netherlands' and Denmark's factors are set whatever GROF's data (as coded); none other."""
    maxf = {}
    if n_pork and west:
        maxf["PORK"] = 1.01
    if ms == "NL000000":
        maxf["PORK"] = 1.0025
    if ms == "DK000000":
        maxf["PORK"] = 1.005
    if n_pouf and west:
        maxf["POUF"] = 1.015
    if n_pork and east:
        maxf["PORK"] = 1.015
    if n_pouf and east:
        maxf["POUF"] = 1.02
    return maxf


def V_EstV_up_GROF_maxFac(up, base, fct, n):
    r"""V_EstV.UP of pork's or poultry's production: at most the base growing by maxFacPerY a year.

    up: the bound before (+inf where none); base: BAST, else BASM; fct: maxFacPerY; n: the years since the base
    (OrdT(ExanteT) - OrdT("BAST" or "BAS")).

    CAPRI's GAMS (captrd/fix_est.gms l. 229-234):

            V_EstV.UP(Rest,"GROF",s_rowsEst,exAnteT) $ p_data(Rest,"GROF",s_rowsEst,"maxFacPerY")
               = min( V_EstV.UP(Rest,"GROF",s_rowsEst,exAnteT),
                     (P_DATA(Rest,"GROF",s_rowsEst,"BAST")
                     +P_DATA(Rest,"GROF",s_rowsEst,"BASM") $ (NOT P_DATA(Rest,"GROF",s_rowsEst,"BAST")))
                     *p_data(Rest,"GROF",s_rowsEst,"maxFacPerY")**(OrdT(ExanteT)-OrdT("BAST") $ (    P_DATA(Rest,"GROF",s_rowsEst,"BAST"))
                                                                                -OrdT("BAS")  $ (NOT P_DATA(Rest,"GROF",s_rowsEst,"BAST"))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(up, base * fct ** n)


def V_EstV_UVAG(basm, bas, n, w, grpr):
    r"""V_EstV.LO and .UP of a producer price: 2% a year around the larger and the smaller of BASM and BAS (5% for
    OCRO, OANI and MILK).

    basm, bas: p_data(., "UVAG", w, "BASM" / "BAS"); n: OrdT(Exante) - OrdT("BAS"); w: the row; grpr: w is a group
    of products (GRPR). Returns (lo, up), or None for a group (no bound).

    CAPRI's GAMS (captrd/fix_est.gms l. 238-256):

           v_estV.UP(Rest,"UVAG",S_RowsEst,Exante) $ (p_data(Rest,"UVAG",S_RowsEst,"nObs") $ (NOT GRPR(S_RowsEst)) $ (not sameas(s_rowsEst,"milk"))
                                                       $ (NOT P_Result(Rest,"UVAG",S_RowsEst,ExAnte,"coco")) $ NUTS0(Rest))
                = MAX(p_data(Rest,"UVAG",S_RowsEst,"BASM"),p_data(Rest,"UVAG",S_RowsEst,"BAS")) * 1.02**(OrdT(Exante)-OrdT("BAS")) ;

           v_estV.LO(Rest,"UVAG",S_RowsEst,Exante) $ (p_data(Rest,"UVAG",S_RowsEst,"nObs") $ (NOT GRPR(S_RowsEst)) $ (not sameas(s_rowsEst,"milk"))
                                                       $ (NOT P_Result(Rest,"UVAG",S_RowsEst,ExAnte,"coco")) $ NUTS0(Rest))
                = MIN(p_data(Rest,"UVAG",S_RowsEst,"BASM"),p_data(Rest,"UVAG",S_RowsEst,"BAS")) * 0.98**(OrdT(Exante)-OrdT("BAS")) ;
        *
        *  --- more drastic changes (+/- 5 % per annum) allowed for prices of the residual categories "other crops/animals" and "MILK" (indirectly constrained)
        *
           v_estV.UP(Rest,"UVAG",s_rowsEst,Exante) $ (p_data(Rest,"UVAG",s_rowsEst,"nObs")
                                                       $ (sameas(s_rowsEst,"OCRO") or sameas(s_rowsEst,"OANI") or sameas(s_rowsEst,"milk"))
                                                       $ (NOT P_Result(Rest,"UVAG",s_rowsEst,ExAnte,"coco")) $ NUTS0(Rest))
                = MAX(p_data(Rest,"UVAG",s_rowsEst,"BASM"),p_data(Rest,"UVAG",s_rowsEst,"BAS")) * 1.05**(OrdT(Exante)-OrdT("BAS")) ;

           v_estV.LO(Rest,"UVAG",s_rowsEst,Exante) $ (p_data(Rest,"UVAG",s_rowsEst,"nObs")
                                                       $ (sameas(s_rowsEst,"OCRO") or sameas(s_rowsEst,"OANI") or sameas(s_rowsEst,"milk"))
                                                       $ (NOT P_Result(Rest,"UVAG",s_rowsEst,ExAnte,"coco")) $ NUTS0(Rest))
                = MIN(p_data(Rest,"UVAG",s_rowsEst,"BASM"),p_data(Rest,"UVAG",s_rowsEst,"BAS")) * 0.95**(OrdT(Exante)-OrdT("BAS")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    if w in ("OCRO", "OANI", "MILK"):
        hi, lw = 1.05, 0.95
    elif not grpr:
        hi, lw = 1.02, 0.98
    else:
        return None
    return min(basm, bas) * lw ** n, max(basm, bas) * hi ** n

r"""CAPTRD's estimation bounds of the maximum yields, cereals, grass, meat, days and the requirement functions
(captrd/fix_est.gms; moved from capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




def V_EstV_up_max_yields(up, bast, bsy):
    r"""V_EstV.UP of a yield of the crops with maximum yields in the years with data: at most 1.5 x the larger of
    BAST and BSY.

    up: the bound before (+inf where none); bast, bsy: p_data(., c, w, "BAST" / "BSY").

    CAPRI's GAMS (captrd/fix_est.gms l. 553-559):

           v_estV.UP(REST,CropsWithMaximumYields,ROWS,exAnteD) $ (   p_data(Rest,CropsWithMaximumYields,ROWS,"nObs")
                                                                  $ (   p_data(Rest,CropsWithMaximumYields,ROWS,"BAST")
                                                                     or p_data(Rest,CropsWithMaximumYields,ROWS,"BSY") )
                                                                  $ (NOT p_globiomTightLink(Rest,CropsWithMaximumYields,"YILD","%SelecScen%",exAnteD))
                                                                  $ PACT_TO_Y(CropsWithMaximumYields,ROWS))
              = MIN(v_estV.UP(REST,CropsWithMaximumYields,ROWS,exAnteD),
                    1.5*MAX(p_data(Rest,CropsWithMaximumYields,ROWS,"BAST"),p_data(Rest,CropsWithMaximumYields,ROWS,"BSY")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(up, 1.5 * max(bast, bsy))


def V_EstV_up_CERE(up):
    r"""V_EstV.UP of a cereal's yield: at most 15 t.

    CAPRI's GAMS (captrd/fix_est.gms l. 565-567):

           v_estV.UP(REST,CERE,S_RowsEst,exAnte) $ ((Pact_to_Y(CERE,S_RowsEst) $ p_data(Rest,CERE,S_RowsEst,"nObs"))
                                                 $ (NOT p_globiomTightLink(Rest,CERE,"YILD","%SelecScen%",exAnte)))
               = MIN(15000,v_estV.UP(REST,CERE,S_RowsEst,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(15000.0, up)


def V_EstV_up_physical(k, basm, up):
    r"""V_EstV.UP of a crop's yield at its physical limit (kg per ha), at least its base.

    k: (crop, row), one of the statements'; basm: p_data(., crop, row, "BASM"); up: the bound before (+inf where
    none).

    CAPRI's GAMS (captrd/fix_est.gms l. 569-584):

           v_estV.UP(REST,"MAIF","MAIF",exAnte) $ (p_data(Rest,"MAIF","MAIF","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"MAIF","YILD","%SelecScen%",exAnte)))
               = MAX( p_data(REST,"MAIF","MAIF","BASM"),MIN(90000,v_estV.UP(REST,"MAIF","MAIF",exAnte)));

           v_estV.UP(REST,"POTA","POTA",exAnte) $ (p_data(Rest,"POTA","POTA","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"POTA","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"POTA","POTA","BASM"),MIN(55000,v_estV.UP(REST,"POTA","POTA",exAnte)));

           v_estV.UP(REST,"SUGB","SUGB",exAnte) $ (p_data(Rest,"SUGB","SUGB","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"SUGB","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"SUGB","SUGB","BASM"),MIN(90000,v_estV.UP(REST,"SUGB","SUGB",exAnte)));


           v_estV.UP(REST,"ROOF","ROOF",exAnte) $ (p_data(Rest,"ROOF","ROOF","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"ROOF","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"ROOF","ROOF","BASM"),MIN(110000,v_estV.UP(REST,"ROOF","ROOF",exAnte)));

    CAPRI's GAMS (captrd/fix_est.gms l. 604-646):

           v_estV.UP(REST,"OFAR","OFAR",exAnte) $ (p_data(Rest,"OFAR","OFAR","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"OFAR","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"OFAR","OFAR","BASM"),MIN(90000,v_estV.UP(REST,"OFAR","OFAR",exAnte)));

           v_estV.UP(REST,"TOBA","TOBA",exAnte) $ (p_data(Rest,"TOBA","TOBA","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"TOBA","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"TOBA","TOBA","BASM"),MIN(4500,v_estV.UP(REST,"TOBA","TOBA",exAnte)));

           v_estV.UP(REST,"CITR","CITR",exAnte) $ (p_data(Rest,"CITR","CITR","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"CITR","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"CITR","CITR","BASM"),MIN(30000,v_estV.UP(REST,"CITR","CITR",exAnte)));

           v_estV.UP(REST,"TAGR","TAGR",exAnte) $ (p_data(Rest,"TAGR","TAGR","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"TAGR","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"TAGR","TAGR","BASM"),MIN(30000,v_estV.UP(REST,"TAGR","TAGR",exAnte)));

           v_estV.UP(REST,"APPL","APPL",exAnte) $ (p_data(Rest,"APPL","APPL","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"APPL","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"APPL","APPL","BASM"),MIN(100000,v_estV.UP(REST,"APPL","APPL",exAnte)));

           v_estV.UP(REST,"TWIN","TWIN",exAnte) $ (p_data(Rest,"TWIN","TWIN","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"TWIN","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"TWIN","TWIN","BASM"),MIN(20000,v_estV.UP(REST,"TWIN","TWIN",exAnte)));

           v_estV.UP(REST,"OLIV","OLIV",exAnte) $ (p_data(Rest,"OLIV","OLIV","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"OLIV","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"OLIV","OLIV","BASM"),MIN(4500,v_estV.UP(REST,"OLIV","OLIV",exAnte)));

           v_estV.UP(REST,"OVEG","OVEG",exAnte) $ (p_data(Rest,"OVEG","OVEG","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"OVEG","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"OVEG","OVEG","BASM"),MIN(60000,v_estV.UP(REST,"OVEG","OVEG",exAnte)));

           v_estV.UP(REST,"OFRU","OFRU",exAnte) $ (p_data(Rest,"OFRU","OFRU","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"OFRU","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"OFRU","OFRU","BASM"),MIN(110000,v_estV.UP(REST,"OFRU","OFRU",exAnte)));

           v_estV.UP(REST,"TEXT","TEXT",exAnte) $ (p_data(Rest,"TEXT","TEXT","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"TEXT","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"TEXT","TEXT","BASM"),MIN(11000,v_estV.UP(REST,"TEXT","TEXT",exAnte)));
        *
           v_estV.UP(REST,"TABO","TABO",exAnte) $ (p_data(Rest,"TABO","TABO","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"TABO","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"TABO","TABO","BASM"),MIN(11000,v_estV.UP(REST,"TABO","TABO",exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    limit = {("MAIF", "MAIF"): 90000.0, ("POTA", "POTA"): 55000.0, ("SUGB", "SUGB"): 90000.0,
             ("ROOF", "ROOF"): 110000.0, ("OFAR", "OFAR"): 90000.0, ("TOBA", "TOBA"): 4500.0,
             ("CITR", "CITR"): 30000.0, ("TAGR", "TAGR"): 30000.0, ("APPL", "APPL"): 100000.0,
             ("TWIN", "TWIN"): 20000.0, ("OLIV", "OLIV"): 4500.0, ("OVEG", "OVEG"): 60000.0,
             ("OFRU", "OFRU"): 110000.0, ("TEXT", "TEXT"): 11000.0, ("TABO", "TABO"): 11000.0}[k]
    return max(basm, min(limit, up))


def V_EstV_up_GRAS(c, nl, basm, up_gras):
    r"""V_EstV.UP of grass's yield on GRAI and GRAE: 80 and 40 t (160 and 80 t in the Netherlands), at least the
    base, from GRAS's own upper bound.

    c: "GRAI" or "GRAE"; nl: the region is the Netherlands' (MAP_RR("NL000000", Rest)); basm: the base CAPRI takes
    (GRAI's own for GRAI, GRAS's for GRAE, GRAE's own in the Netherlands); up_gras: V_EstV.UP(., "GRAS", "GRAS").

    CAPRI's GAMS (captrd/fix_est.gms l. 586-602):

           v_estV.UP(REST,"GRAI","GRAS",exAnte) $ (p_data(Rest,"GRAI","GRAS","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"GRAI","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"GRAI","GRAS","BASM"),MIN(80000,v_estV.UP(REST,"GRAS","GRAS",exAnte)));

           v_estV.UP(REST,"GRAE","GRAS",exAnte) $ (p_data(Rest,"GRAE","GRAS","nObs")
                                                 $ (NOT p_globiomTightLink(Rest,"GRAE","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"GRAS","GRAS","BASM"),MIN(40000,v_estV.UP(REST,"GRAS","GRAS",exAnte)));

           v_estV.UP(REST,"GRAI","GRAS",exAnte) $ (p_data(Rest,"GRAI","GRAS","nObs")
                                                  $ MAP_RR("NL000000",Rest)
                                                 $ (NOT p_globiomTightLink(Rest,"GRAI","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"GRAI","GRAS","BASM"),MIN(160000,v_estV.UP(REST,"GRAS","GRAS",exAnte)));

           v_estV.UP(REST,"GRAE","GRAS",exAnte) $ (p_data(Rest,"GRAE","GRAS","nObs")
                                                    $ MAP_RR("NL000000",Rest)
                                                 $ (NOT p_globiomTightLink(Rest,"GRAE","YILD","%SelecScen%",exAnte)))
              = MAX( p_data(REST,"GRAE","GRAS","BASM"),MIN(80000,v_estV.UP(REST,"GRAS","GRAS",exAnte)));

    the Netherlands' lines apply to the member state itself (the port's ms == NL000000); the domain condition in the
    caller (estimate_bounds.bounds)."""
    limit = {("GRAI", False): 80000.0, ("GRAE", False): 40000.0, ("GRAI", True): 160000.0,
             ("GRAE", True): 80000.0}[(c, nl)]
    return max(basm, min(limit, up_gras))


def V_EstV_lo_max_yields(lo, up):
    r"""V_EstV.LO of a yield of the crops with maximum yields: at most 90% of its upper bound.

    CAPRI's GAMS (captrd/fix_est.gms l. 648-652):

           v_estV.LO(REST,CropsWithMaximumYields,ROWS,exAnte) $ (    p_data(Rest,CropsWithMaximumYields,ROWS,"nObs")
                                                                  $ (NOT p_globiomTightLink(Rest,CropsWithMaximumYields,"YILD","%SelecScen%",exAnte))
                                                                  $ PACT_TO_Y(CropsWithMaximumYields,ROWS))
              = MIN(v_estV.LO(REST,CropsWithMaximumYields,ROWS,exAnte),
                    v_estV.UP(REST,CropsWithMaximumYields,ROWS,exAnte)*0.9);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(lo, up * 0.9)


def V_EstV_MEAT(basm, x, span):
    r"""V_EstV.LO and .UP of an animal's meat yield: the base plus and minus up to 20% at the last ex-ante year.

    basm: p_data(., a, m, "BASM"); x: MAX(OrdT("BAS") + 1, OrdT(ExAnte)) - OrdT("BAS"); span: OrdT("lst_exAnte") -
    OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 655-664):

           v_estV.lo(REST,MAACT,MEAT,exAnte)  $ (p_data(Rest,MAACT,MEAT,"nObs") $ (NOT P_Result(Rest,MAACT,MEAT,ExAnte,"coco")))
               = p_data(REST,MAACT,MEAT,"BASM")*( 1.
        $ifi not "%FixExogenFactGlobiom%"=="ON" - 0.20  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        *fw      relax bounds on slaughter weights in favour of tight link to GLOBIOM
        $ifi     "%FixExogenFactGlobiom%"=="ON" - 0.40  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        *
           v_estV.up(REST,MAACT,MEAT,exAnte)  $ (p_data(Rest,MAACT,MEAT,"nObs") $ (NOT P_Result(Rest,MAACT,MEAT,ExAnte,"coco")))
               = p_data(REST,MAACT,MEAT,"BASM")*( 1.
        $ifi not "%FixExogenFactGlobiom%"=="ON" + 0.20  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        $ifi     "%FixExogenFactGlobiom%"=="ON" + 0.40  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));

    %FixExogenFactGlobiom% is off (the 20%, not the 40%); the domain condition in the caller (estimate_bounds.bounds)."""
    r = 0.20 * x / span
    return basm * (1.0 - r), basm * (1.0 + r)


def V_EstV_DAYS(basm, x, span):
    r"""V_EstV.LO and .UP of an animal's days: the base plus and minus up to 30% at the last ex-ante year.

    basm: p_data(., a, "DAYS", "BASM"); x, span: as V_EstV_MEAT. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 666-672):

           v_estV.lO(REST,MAACT,"DAYS",exAnte)  $ (p_data(Rest,MAACT,"DAYS","nObs") $ (NOT P_Result(Rest,MAACT,"DAYS",ExAnte,"coco")))
               = p_data(REST,MAACT,"DAYS","BASM")
               * (1. - 0.30  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        *
           v_estV.up(REST,MAACT,"DAYS",exAnte)  $ (p_data(Rest,MAACT,"DAYS","nObs") $ (NOT P_Result(Rest,MAACT,"DAYS",ExAnte,"coco")))
               = p_data(REST,MAACT,"DAYS","BASM")
               * (1. + 0.30  * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    r = 0.30 * x / span
    return basm * (1.0 - r), basm * (1.0 + r)


def V_EstV_reqfcnlim(bound, lo, up, v):
    r"""V_EstV.LO or .UP of a requirement within the requirement functions' limits (p_reqfcnlim).

    bound: "lo" or "up"; lo, up: the bounds before (-inf / +inf where none); v: p_reqfcnlim(MAACT, w, bound).
    Returns the new bound, or None for another bound.

    CAPRI's GAMS (captrd/fix_est.gms l. 675-678):

           v_estV.LO(Rest,MAACT,s_RowsEst,exAnte) $ (p_reqfcnlim(MAACT,s_RowsEst,"lo") $ p_data(Rest,MAACT,"LEVL","nObs"))
                          = MAX(v_estV.LO(Rest,MAACT,s_RowsEst,exAnte),p_reqfcnlim(MAACT,s_RowsEst,"lo"));
           v_estV.UP(Rest,MAACT,s_RowsEst,exAnte) $ (p_reqfcnlim(MAACT,s_RowsEst,"up")  $ p_data(Rest,MAACT,"LEVL","nObs"))
                          = MIN(v_estV.UP(Rest,MAACT,s_RowsEst,exAnte),p_reqfcnlim(MAACT,s_RowsEst,"up"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    if bound == "lo":
        return max(lo, v)
    if bound == "up":
        return min(up, v)
    return None

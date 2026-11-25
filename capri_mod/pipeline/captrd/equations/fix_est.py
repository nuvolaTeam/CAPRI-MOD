r"""CAPTRD's bound statements of captrd/fix_est.gms (CAPRI star 3.0): the bounds of the member-state and NUTS 2 estimations, as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (the assignments
refactor's style: one function per statement block, named after the bounded symbol, V_EstV.LO / .UP / .FX). The
functions take the numbers the statement reads and return the bound; capri_mod/pipeline/captrd/estimate_bounds.py
(bounds) holds the domain conditions, the loops over the sets and the order of the statements, and calls them. A
bound "before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its
order of operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_IO(base, yrs, span, w, uaar_act):
    r"""V_EstV.LO and .UP of an activity's input or output coefficient in the ex-ante years without data: at most
    2.5% a year from the base, and at most 30% (10% for YCAM, YCAF and, below, SGMI) up to the last ex-ante year;
    the second upper limit lifted (+10) for the crops (P_T_ActAgg(., "UAAR")), YCHI and SGMI, the second lower one
    for YCHI (-1).

    base: BAST, else BASM; yrs: the years since it (OrdT(ExanteT) - OrdT("BAST" or "BAS")); span: the last ex-ante
    year's (OrdT("Lst_exAnte") - the same); w: the row; uaar_act: the activity is one of the UAAR aggregate's.
    Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 25-63):

           v_estV.LO(Rest,MPACT,S_RowsEst,ExanteT) $ (    p_data(Rest,MPACT,S_RowsEst,"nObs")
                                                     $ (NOT P_Result(Rest,MPACT,S_RowsEst,ExAnte,"coco"))
                                                     $ ((p_globiomTightLink(Rest,MPACT,"YILD","%SelecScen%",exanteT)
                                                      - p_globiomTightLink(Rest,MPACT,"YILD","%SelecScen%","20%BAS%"))
                                                      > -0.025 * (OrdT(exanteT) - OrdT("BAS")))
                                                     $ S_ColsEst(MPACT) $ PACT_TO_IO(MPACT,S_RowsEst))
              = (p_data(Rest,MPACT,S_RowsEst,"BAST") + p_data(Rest,MPACT,S_RowsEst,"BASM") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST")))
              * max(0.975**(OrdT(ExanteT)-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                        - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST"))),
                    (1-(.3 - .2 $ (sameas(S_RowsEst,"ycam") or sameas(S_RowsEst,"ycaf") or sameas(S_RowsEst,"sgmi")))
                            *(OrdT(ExanteT)-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                       - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST")))
                         /(OrdT("Lst_exAnte")-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                       - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST"))))
        *                                              deactivate the second upper bound for young chicken for POUF or HENS
        *                                              (produced flexibly by specialised breeders):
                                                        -1 $ sameas(s_rowsEst,"YCHI"));
        *
           v_estV.UP(Rest,MPACT,S_RowsEst,ExanteT) $ (     p_data(Rest,MPACT,S_RowsEst,"nObs")
                                                     $ (NOT P_Result(Rest,MPACT,S_RowsEst,ExAnte,"coco"))
                                                     $ ((p_globiomTightLink(Rest,MPACT,"YILD","%SelecScen%",exanteT)
                                                      - p_globiomTightLink(Rest,MPACT,"YILD","%SelecScen%","20%BAS%"))
                                                      < 0.025 * (OrdT(exanteT) - OrdT("BAS")))
                                                     $ S_ColsEst(MPACT) $ PACT_TO_IO(MPACT,S_RowsEst))
              = (p_data(Rest,MPACT,S_RowsEst,"BAST") + p_data(Rest,MPACT,S_RowsEst,"BASM") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST")))
              * min(1.025**(OrdT(ExanteT)-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                        - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST"))),
                    (1+(.3 - .2 $ (sameas(S_RowsEst,"ycam") or sameas(S_RowsEst,"ycaf")))
                        *(OrdT(ExanteT)-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                       - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST")))
                         /(OrdT("Lst_exAnte")-OrdT("BAST") $ p_data(Rest,MPACT,S_RowsEst,"BAST")
                                       - OrdT("BAS") $ (not p_data(Rest,MPACT,S_RowsEst,"BAST"))))
        *           deactivate the second upper bound for crop yields (treated below)
                    +10 $ (  P_T_ActAgg(mPact,"UAAR")
        *           and young chicken for POUF or HENS (produced flexibly by specialised breeders):
                          or sameas(s_rowsEst,"YCHI")
        *           and sheep milk (no special treatment below like for cow milk):
                          or sameas(s_rowsEst,"SGMI")
                    ));

    the GLOBIOM yield condition holds (p_globiomTightLink is empty in the reference run: 0 - 0 > -0.025 x the years); the
    domain condition in the caller (estimate_bounds.bounds)."""
    frac = yrs / span
    lo_share = 0.3 - (0.2 if w in ("YCAM", "YCAF", "SGMI") else 0.0)
    lo = base * max(0.975 ** yrs, 1 - lo_share * frac - (1.0 if w == "YCHI" else 0.0))
    up_share = 0.3 - (0.2 if w in ("YCAM", "YCAF") else 0.0)
    deact = 10.0 if (uaar_act or w in ("YCHI", "SGMI")) else 0.0
    up = base * min(1.025 ** yrs, 1 + up_share * frac + deact)
    return lo, up


def V_EstV_OYANI_expert(lo, up):
    r"""V_EstV.LO and .UP of a young-animal output with an expert level up to 2020: the bounds widened to 50% and
    150%.

    lo, up: the bounds set before (None where none is). Returns (lo, up), None kept.

    CAPRI's GAMS (captrd/fix_est.gms l. 70-74):

           v_estV.LO(Rest,MPACT,OYANI,ExanteT) $ (P_Result(Rest,MPACT,"LEVL",ExanteT,"Expert") and (CalYea(ExAnteT) le CalYea("2020")))
             = v_estV.LO(Rest,MPACT,OYANI,ExanteT) *0.5;

           v_estV.UP(Rest,MPACT,OYANI,ExanteT) $ (P_Result(Rest,MPACT,"LEVL",ExanteT,"Expert") and (CalYea(ExAnteT) le CalYea("2020")))
             = v_estV.UP(Rest,MPACT,OYANI,ExanteT) *1.5;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return (None if lo is None else lo * 0.5), (None if up is None else up * 1.5)


def V_EstV_IYANI_cows(lo, up):
    r"""V_EstV.LO and .UP of the cows' young-animal inputs: widened to 90% and 110% (to reduce STCM of YCOW).

    lo, up: the bounds set before (None where none is). Returns (lo, up), None kept.

    CAPRI's GAMS (captrd/fix_est.gms l. 79-86):

           v_estV.LO(Rest,CowsAct,IYANI,ExanteT) $ (  P_Result(Rest,CowsAct,"LEVL",ExanteT,"BASM")
                                                   $ (P_Result(Rest,"GROF","ICOW",ExanteT,"BASM")
                                                     +P_Result(Rest,"GROF","YCOW",ExanteT,"BASM")))
             = .9*v_estV.LO(Rest,CowsAct,IYANI,ExanteT);
           v_estV.UP(Rest,CowsAct,IYANI,ExanteT) $ (  P_Result(Rest,CowsAct,"LEVL",ExanteT,"BASM")
                                                   $ (P_Result(Rest,"GROF","ICOW",ExanteT,"BASM")
                                                     +P_Result(Rest,"GROF","YCOW",ExanteT,"BASM")))
             = 1.1*v_estV.UP(Rest,CowsAct,IYANI,ExanteT);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return (None if lo is None else lo * 0.9), (None if up is None else up * 1.1)


def V_EstV_SLGW(basm, n):
    r"""V_EstV.LO and .UP of a breeding activity's slaughter weight: 0.5% a year around the base.

    basm: p_data(., "SLGW", "BASM"); n: OrdT(Exante) - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 90-96):

           v_estV.LO(Rest,breedAct,"SLGW",Exante) $ (    p_data(Rest,breedAct,"SLGW","nObs")
                                                     $ (NOT P_Result(Rest,breedAct,"SLGW",ExAnte,"coco")))
              = p_data(Rest,breedAct,"SLGW","BASM")*0.995**(OrdT(Exante)-OrdT("BAS"));
        *
           v_estV.UP(Rest,breedAct,"SLGW",Exante) $ (    p_data(Rest,breedAct,"SLGW","nObs")
                                                     $ (NOT P_Result(Rest,breedAct,"SLGW",ExAnte,"coco")))
              = p_data(Rest,breedAct,"SLGW","BASM")*1.005**(OrdT(Exante)-OrdT("BAS"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.995 ** n, basm * 1.005 ** n


def V_EstV_FEED(basm, drmn, drmx, n):
    r"""V_EstV.LO and .UP of a marketable feed coefficient: 10% a year around the base, widened by 1% of half the
    dry matter range.

    basm: p_data(MAACT, Feed, "BASM"); drmn, drmx: p_data(MAACT, "DRMN" / "DRMX", "BASM"); n: OrdT(Exante) -
    OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 101-111):

           v_estV.LO(Rest,MAACT,Feed,Exante) $ (    p_data(Rest,MAACT,Feed,"nObs")
                                                $ S_ColsEst(MAACT) $ PACT_TO_IO(MAACT,Feed))
              = MAX(0.0,  p_data(Rest,MAACT,Feed,"BASM")
                        -(p_data(Rest,MAACT,"DRMN","BASM")-p_data(Rest,MAACT,"DRMX","BASM"))/2*0.01)
              * 0.90**(OrdT(Exante)-OrdT("BAS"));
        *
           v_estV.UP(Rest,MAACT,Feed,Exante) $ (    p_data(Rest,MAACT,Feed,"nObs")
                                                $ S_ColsEst(MAACT) $ PACT_TO_IO(MAACT,Feed))
              =    (    p_data(Rest,MAACT,Feed,"BASM")
                      +(p_data(Rest,MAACT,"DRMN","BASM")-p_data(Rest,MAACT,"DRMX","BASM"))/2*0.01)
              * 1.10**(OrdT(Exante)-OrdT("BAS"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    dr = (drmn - drmx) / 2 * 0.01
    return max(0.0, basm - dr) * 0.90 ** n, (basm + dr) * 1.10 ** n


def V_EstV_FODDI(basm, drmn, drmx, n, outputs):
    r"""V_EstV.LO and .UP of a non-marketable feed coefficient: 5% a year around the base, the dry matter range as
    for the feeds, and a safeguard against a large change of the fodder's output in COCO (twice and half the ratio
    of COCO to BASM, 1 where either is zero, summed over the fodder's outputs).

    basm, drmn, drmx, n: as V_EstV_FEED; outputs: (P_Result(., "GROF", o, "Coco"), P_Result(., "GROF", o, "BASM"))
    of the fodder's outputs o (FEED_TO_O), in the caller's order. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 116-142):

           v_estV.LO(Rest,MAACT,FoddI,Exante) $ (  p_data(Rest,MAACT,FoddI,"nObs")
                                                 $ S_ColsEst(MAACT) $ PACT_TO_IO(MAACT,FoddI))
              = MAX(0.0, p_data(Rest,MAACT,FoddI,"BASM")
                       -(p_data(Rest,MAACT,"DRMN","BASM")-p_data(Rest,MAACT,"DRMX","BASM"))/2*0.01)
              * MIN( 0.95**(OrdT(Exante)-OrdT("BAS")),
        *            Safeguard against dramatic decline of related fodder output feed use in COCO
        *            that may require a declease in feed coefficients to adjust
                     2* SUM(FEED_TO_O(FODDI,FODDO),( P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                   / P_Result(Rest,"GROF",FoddO,ExAnte,"BASM"))
                                                  $ (      P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                         $ P_Result(Rest,"GROF",FoddO,ExAnte,"BASM"))
                   + 1                            $ (NOT ( P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                         $ P_Result(Rest,"GROF",FoddO,ExAnte,"BASM")))));
        *
           v_estV.UP(Rest,MAACT,FoddI,Exante) $ (  p_data(Rest,MAACT,FoddI,"nObs")
                                                 $ S_ColsEst(MAACT) $ PACT_TO_IO(MAACT,FoddI))
              =    (     p_data(Rest,MAACT,FoddI,"BASM")
                       +(p_data(Rest,MAACT,"DRMN","BASM")-p_data(Rest,MAACT,"DRMX","BASM"))/2*0.01)
              * MAX( 1.05**(OrdT(Exante)-OrdT("BAS")),
        *            Safeguard against dramatic increase of related fodder output feed use in COCO
        *            that may require an increase in feed coefficients to adjust
                     .5*SUM(FEED_TO_O(FODDI,FODDO),( P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                   / P_Result(Rest,"GROF",FoddO,ExAnte,"BASM"))
                                                  $ (      P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                         $ P_Result(Rest,"GROF",FoddO,ExAnte,"BASM"))
                   + 1                            $ (NOT ( P_Result(Rest,"GROF",FoddO,ExAnte,"Coco")
                                                         $ P_Result(Rest,"GROF",FoddO,ExAnte,"BASM")))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    dr = (drmn - drmx) / 2 * 0.01
    ratio = 0.0
    for cc, bb in outputs:
        ratio += (cc / bb) if (cc and bb) else 1.0
    r_lo, r_up = 2 * ratio, 0.5 * ratio
    return max(0.0, basm - dr) * min(0.95 ** n, r_lo), (basm + dr) * max(1.05 ** n, r_up)


def V_EstV_ReqsT(support):
    r"""V_EstV.LO and .UP of a requirement (relative): 50% and 150% of its support. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 144-150):

           v_estV.LO(Rest,MAACT,ReqsT,ExAnte)  $ ( (p_data(Rest,MAACT,ReqsT,"Const")  + p_data(Rest,MAACT,ReqsT,"Slope"))
                                                   $ p_data(Rest,MAACT,"LEVL","nObs"))
                 = P_Result(Rest,MAACT,ReqsT,ExAnte,"Support") * 0.5;
        *
           v_estV.UP(Rest,MAACT,ReqsT,ExAnte)  $ ((p_data(Rest,MAACT,ReqsT,"Const")  + p_data(Rest,MAACT,ReqsT,"Slope"))
                                                   $ p_data(Rest,MAACT,"LEVL","nObs"))
                 = P_Result(Rest,MAACT,ReqsT,ExAnte,"Support") * 1.5;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return support * 0.5, support * 1.5


def V_EstV_lo_ReqsTE(support):
    r"""V_EstV.LO of an energy requirement (ReqsTE, relative): 98% of its support.

    CAPRI's GAMS (captrd/fix_est.gms l. 153-155):

           v_estV.LO(Rest,MAACT,ReqsTE,ExAnte)  $ ((p_data(Rest,MAACT,ReqsTE,"Const")  + p_data(Rest,MAACT,ReqsTE,"Slope"))
                                                   $ p_data(Rest,MAACT,"LEVL","nObs"))
                 = P_Result(Rest,MAACT,ReqsTE,ExAnte,"Support") * 0.98;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return support * 0.98


def V_EstV_lo_CRPR(lo, n_expt, const, slope, supports, eff):
    r"""V_EstV.LO of the crude protein requirement: at least 1.5 x the N excretion over the requirement function
    (Const + Slope x the main outputs' supports), times the feeding efficiency.

    lo: the bound before (-inf where none); n_expt: p_data(., "N_EXPT", "BASM"); const, slope: p_data(., "CRPR",
    "Const" / "Slope"); supports: the supports of the outputs (PACT_TO_Y) with data; eff: 0.998^(OrdT(exAnte) -
    OrdT("2000")). Returns the bound, or None where the requirement function is zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 157-163):

           v_estV.LO(Rest,MAACT,"CRPR",ExAnte)  $ ((p_data(Rest,MAACT,"CRPR","Const")  + p_data(Rest,MAACT,"CRPR","Slope"))
                                                    $ p_data(Rest,MAACT,"LEVL","nObs"))
                 = MAX(v_estV.LO(Rest,MAACT,"CRPR",ExAnte),
                        p_data(Rest,MAACT,"N_EXPT","BASM")*1.5/
                       (p_data(Rest,MAACT,"CRPR","Const")  + p_data(Rest,MAACT,"CRPR","Slope")
                                  * SUM(PACT_TO_Y(MAACT,O) $ p_data(Rest,MAACT,O,"nObs"), P_Result(Rest,MAACT,O,ExAnte,"Support")))
                     * (0.998**(OrdT(exAnte)-OrdT("2000"))));

    the bound is left as it is where the requirement function is zero (CAPRI would divide by zero); the domain condition
    in the caller (estimate_bounds.bounds)."""
    k = const + slope * sum(supports)
    if not k:
        return None
    return max(lo, n_expt * 1.5 / k * eff)


def V_EstV_up_ReqsTE(lo):
    r"""V_EstV.UP of an energy requirement: its lower bound / 0.98 x 1.02.

    CAPRI's GAMS (captrd/fix_est.gms l. 165-167):

           v_estV.UP(Rest,MAACT,ReqsTE,ExAnte)  $ ((p_data(Rest,MAACT,ReqsTE,"Const")  + p_data(Rest,MAACT,ReqsTE,"Slope"))
                                                    $ p_data(Rest,MAACT,"LEVL","nObs"))
                 = v_estV.LO(Rest,MAACT,ReqsTE,ExAnte)/0.98*1.02;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return lo / 0.98 * 1.02


def V_EstV_NoYieldDrop(basm, gras, n, prev, up):
    r"""V_EstV.LO and .UP of a crop yield that may not fall: at least the base growing by 0.25% a year (0.05% for
    grass), and the previous year's estimate (the base where that year has data); the upper bound at least 1.01 x
    the lower.

    basm: p_data(., w, "BASM"); gras: the activity is a grass (DACT_TO_PACT("GRAS", .)); n: OrdT(Exante) -
    OrdT("BAS"); prev: the previous year's EstP, its BASM if that year has data, 0 where there is none (Before
    empty); up: the upper bound before (+inf where none). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 171-191):

           v_estV.LO(Rest,NoYieldDrop,S_RowsEst,Exante) $ (    p_data(Rest,NoYieldDrop,S_RowsEst,"nObs")
                                                           $ (NOT P_Result(Rest,NoYieldDrop,S_RowsEst,ExAnte,"coco"))
                                                           $ (NOT p_globiomTightLink(Rest,NoYieldDrop,"YILD","%SelecScen%",exAnte))
                                                           $ S_ColsEst(NoYieldDrop) $ PACT_TO_Y(NoYieldDrop,S_RowsEst))
              = p_data(Rest,NoYieldDrop,S_RowsEst,"BASM")
        *                For gras, basically stagnating yields are possible according to statistics in several MS
              * (1.0025 - 0.002 $ DACT_TO_PACT("GRAS",NoYieldDrop) )**(OrdT(Exante)-OrdT("BAS"));

           v_estV.LO(Rest,NoYieldDrop,S_RowsEst,exAnte) $ (    p_data(Rest,NoYieldDrop,S_RowsEst,"nObs")
                                                           $ (NOT P_Result(Rest,NoYieldDrop,S_RowsEst,ExAnte,"coco"))
                                                           $ (NOT p_globiomTightLink(Rest,NoYieldDrop,"YILD","%SelecScen%",exAnte))
                                                           $ S_ColsEst(NoYieldDrop) $ PACT_TO_Y(NoYieldDrop,S_RowsEst))
              = MAX(v_estV.LO(Rest,NoYieldDrop,S_RowsEst,Exante),
                   SUM( Before(exAnte,Years),   EstP(Rest,NoYieldDrop,S_RowsEst,Years)      $ (NOT SUM(SAMEAS(Years,exAnteD),1))
                                              + p_data(Rest,NoYieldDrop,S_RowsEst,"BASM")   $      SUM(SAMEAS(Years,exAnteD),1) ));
        *
           v_estV.UP(Rest,NoYieldDrop,S_RowsEst,Exante) $ (    p_data(Rest,NoYieldDrop,S_RowsEst,"nObs")
                                                           $ (NOT P_Result(Rest,NoYieldDrop,S_RowsEst,ExAnte,"coco"))
                                                           $ (NOT p_globiomTightLink(Rest,NoYieldDrop,"YILD","%SelecScen%",exAnte))
                                                           $ S_ColsEst(NoYieldDrop) $ PACT_TO_Y(NoYieldDrop,S_RowsEst))
              = MAX(v_estV.LO(Rest,NoYieldDrop,S_RowsEst,exAnte)*1.01,v_estV.UP(Rest,NoYieldDrop,S_RowsEst,Exante));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    g = 0.002 if gras else 0.0
    lo = basm * (1.0025 - g) ** n
    lo = max(lo, prev)
    return lo, max(lo * 1.01, up)


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


def V_EstV_LEVL_crops(basm, land, t, ord_bas, span_bas):
    r"""V_EstV.LO and .UP of a crop's or crop group's area: the base plus and minus a deviation that grows with the
    years (at least 20% of the span) and falls with the crop's share of the land.

    basm: p_data(., c, "LEVL", "BASM"); land: UAAR's BASM less GRAS's (not for GRAE and GRAI), positive; t, ord_bas:
    OrdT(ExAnte), OrdT("BAS"); span_bas: OrdT("lst_exAnte") - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 344-381):

           v_estV.UP(Rest,S_ColsEst,"LEVL",ExAnte) $ (    ((p_data(Rest,"UAAR","LEVL","BASM")
                                                           -p_data(Rest,"GRAS","LEVL","BASM")
                                                              $ (NOT (   SAMEAS(S_ColsEst,"GRAE")
                                                                      or SAMEAS(S_ColsEst,"GRAI")))) GT 0)
                                                      $ (SUM(SAMEAS(CACT,S_ColsEst),1) or GRPC(S_ColsEst))
                                                      $ (NOT P_Result(Rest,S_ColsEst,"LEVL",ExAnte,"coco"))
                                                      $ p_data(Rest,S_ColsEst,"Levl","nObs"))
               = MAX(p_data(Rest,S_ColsEst,"LEVL","BASM")+0.1,
                       p_data(Rest,S_ColsEst,"LEVL","BASM")
                     +(  p_data(Rest,S_ColsEst,"LEVL","BASM")
                       /(p_data(Rest,"UAAR","LEVL","BASM")
                       -p_data(Rest,"GRAS","LEVL","BASM") $ (NOT (   SAMEAS(S_ColsEst,"GRAE")
                                                                  or SAMEAS(S_ColsEst,"GRAI")))))**0.25/4
                     *(p_data(Rest,"UAAR","LEVL","BASM")
                      -p_data(Rest,"GRAS","LEVL","BASM") $ (NOT (    SAMEAS(S_ColsEst,"GRAE")
                                                                 or SAMEAS(S_ColsEst,"GRAI"))))
                     * MAX(0.2, (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))
                               /(OrdT("lst_exAnte")-OrdT("BAS"))));

           v_estV.lo(Rest,S_ColsEst,"LEVL",ExAnte) $ (    ((p_data(Rest,"UAAR","LEVL","BASM")
                                                           -p_data(Rest,"GRAS","LEVL","BASM")
                                                              $ (NOT (   SAMEAS(S_ColsEst,"GRAE")
                                                                      or SAMEAS(S_ColsEst,"GRAI")))) GT 0)
                                                      $ (SUM(SAMEAS(CACT,S_ColsEst),1) or GRPC(S_ColsEst))
                                                      $ (NOT P_Result(Rest,S_ColsEst,"LEVL",ExAnte,"coco"))
                                                      $ p_data(Rest,S_ColsEst,"Levl","nObs")
                                                      )
               = MAX(1.E-5,
                       p_data(Rest,S_ColsEst,"LEVL","BASM")
                     -(  p_data(Rest,S_ColsEst,"LEVL","BASM")
                       /(p_data(Rest,"UAAR","LEVL","BASM")
                       -p_data(Rest,"GRAS","LEVL","BASM") $ (NOT (   SAMEAS(S_ColsEst,"GRAE")
                                                                  or SAMEAS(S_ColsEst,"GRAI")))))**0.25/4
                     *(p_data(Rest,"UAAR","LEVL","BASM")
                      -p_data(Rest,"GRAS","LEVL","BASM") $ (NOT (    SAMEAS(S_ColsEst,"GRAE")
                                                                 or SAMEAS(S_ColsEst,"GRAI"))))
                     * MAX(0.2, (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))
                               /(OrdT("lst_exAnte")-OrdT("BAS"))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    dev = (basm / land) ** 0.25 / 4 * land * max(0.2, (max(ord_bas + 1, t) - ord_bas) / span_bas)
    return max(1.0e-5, basm - dev), max(basm + 0.1, basm + dev)


def V_EstV_lo_GRSACT(lo, bast, basm):
    r"""V_EstV.LO of permanent grassland in the EU: at least 98% of BAST, else of BASM.

    lo: the bound before (-inf where none); bast, basm: p_data(., c, "LEVL", "BAST" / "BASM").

    CAPRI's GAMS (captrd/fix_est.gms l. 390-401):

           v_estV.LO(Rest,GRSACT,"LEVL",ExAnte) $ ( MAP_RR("EU028000",Rest)
                                                  $ (NOT P_Result(Rest,GRSACT,"LEVL",ExAnte,"coco"))
                                                  $ p_data(Rest,GRSACT,"Levl","nObs")

        *                                   set it for years before 2015 too (before the policy applies),
        *                                   to avoid bumps in projected trends...
        *                                          $ (ExAnte.val lt 2015)
                                                  )

              = MAX(v_estV.LO(Rest,GRSACT,"LEVL",ExAnte),
                    p_data(Rest,GRSACT,"LEVL","BAST")*0.98
                   +p_data(Rest,GRSACT,"LEVL","BASM")*0.98 $ (not p_data(Rest,GRSACT,"LEVL","BAST")) );

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return max(lo, bast * 0.98 + (basm * 0.98 if not bast else 0.0))


def V_EstV_lo_MAACT(basm):
    r"""V_EstV.LO of an animal activity's herd: 20% of its base.

    CAPRI's GAMS (captrd/fix_est.gms l. 408-409):

           v_estV.LO(Rest,MAACT,"LEVL",ExAnte) $ p_data(Rest,MAACT,"LEVL","BASM")
              = p_data(Rest,MAACT,"LEVL","BASM")*0.2;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.2


def p_data_LEVL_facs(acts, ms, n_pigf, n_pouf, west, east):
    r"""p_data(Rest, MAACT, "LEVL", "minFacPerY" / "maxFacPerY" / "minFacTot" / "maxFacTot"): the herds' yearly
    and total change, 0.9-1.05 a year and 0.2-4 in all; the pigs' and poultry's own in the EU (the Netherlands' and
    Denmark's pigs their own).

    acts: the animal activities with data and not in COCO, in the caller's order; ms, west, east: as
    p_data_GROF_maxFacPerY; n_pigf, n_pouf: PIGF's and POUF's levels have data. Returns (minp, maxp, mint, maxt),
    {activity: factor}.

    CAPRI's GAMS (captrd/fix_est.gms l. 413-463):

           p_data(Rest,MAACT,"LEVL","minFacPerY") $ ((NOT P_Result(Rest,MAACT,"LEVL",ExAnte,"coco")) $ p_data(Rest,MAACT,"LEVL","nObs"))= .9;
           p_data(Rest,MAACT,"LEVL","maxFacPerY") $ ((NOT P_Result(Rest,MAACT,"LEVL",ExAnte,"coco")) $ p_data(Rest,MAACT,"LEVL","nObs"))= 1.05;

        *         - more restrictive bounds for PIGF in EU15 (tailored to UK, but very strong decline is also nonsence elewhere):

           p_data(Rest,"PIGF","LEVL","minFacPerY") $ ( p_data(Rest,"PIGF","LEVL","nObs")
                                                     $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = .98;

        *pw       - only moderate increase of pork $ poultry production in EU15 allowed due to
        *           cross-compliance (Water $ nitrate directive)
        *
           p_data(Rest,"PIGF","LEVL","maxFacPerY") $ ( p_data(Rest,"PIGF","LEVL","nObs")
                                                     $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.01;
           p_data(Rest,"PIGF","LEVL","maxFacPerY") $ (SAMEAS(Rest,"NL000000") )                                                          = 1.0025;
           p_data(Rest,"PIGF","LEVL","maxFacPerY") $ (SAMEAS(Rest,"DK000000") )                                                          = 1.005;

        *         - poultry production in EU15: 1.5% per year
        *           (a bit more than for pork becasue dem$ growth is stronger $ manure might be incinerated)
           p_data(Rest,"POUF","LEVL","maxFacPerY") $ ( p_data(Rest,"POUF","LEVL","nObs")
                                                     $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.015;

        *         - In EU12 we permit 0.5% more growth compared to EU15
           p_data(Rest,"PIGF","LEVL","maxFacPerY") $ ( p_data(Rest,"PIGF","LEVL","nObs")
                                                     $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))       = 1.015;

           p_data(Rest,"POUF","LEVL","maxFacPerY") $ ( p_data(Rest,"POUF","LEVL","nObs")
                                                     $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))       = 1.02;

        *
        *      -- constrain total relative changes relative to BASM or BAST
        *
           p_data(Rest,MAACT,"LEVL","minFacTot") $ ((NOT P_Result(Rest,MAACT,"LEVL",ExAnte,"coco")) $ p_data(Rest,MAACT,"LEVL","nObs"))= .2;
           p_data(Rest,MAACT,"LEVL","maxFacTot") $ ((NOT P_Result(Rest,MAACT,"LEVL",ExAnte,"coco")) $ p_data(Rest,MAACT,"LEVL","nObs"))= 4.;

        *pw       - only moderate increase of pork $ poultry production in EU15 allowed due to
        *           cross-compliance (Water $ nitrate directive)
        *
           p_data(Rest,"PIGF","LEVL","maxFacTot") $ ( p_data(Rest,"PIGF","LEVL","nObs")
                                                     $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.4;

        *         - poultry production in EU15:
        *           (a bit more than for pork becasue dem$ growth is stronger $ manure might be incinerated)
           p_data(Rest,"POUF","LEVL","maxFacTot") $ ( p_data(Rest,"POUF","LEVL","nObs")
                                                     $ SUM((CurEUWestAgg,MS_TO_RMSAGG(MSEst,CurEUWestAgg)) $ SAMEAS(Rest,MSEst),1))      = 1.7;

        *         - In EU12 we permit more growth compared to EU15
           p_data(Rest,"PIGF","LEVL","maxFacTot") $ ( p_data(Rest,"PIGF","LEVL","nObs")
                                                     $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))       = 1.7;

           p_data(Rest,"POUF","LEVL","maxFacTot") $ ( p_data(Rest,"POUF","LEVL","nObs")
                                                     $ SUM((CurEUEastAgg,MS_TO_RMSAGG(MSEst,CurEUEastAgg)) $ SAMEAS(Rest,MSEst),1))       = 2.3;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    minp, maxp, mint, maxt = {}, {}, {}, {}
    for a in acts:
        minp[a], maxp[a], mint[a], maxt[a] = 0.9, 1.05, 0.2, 4.0
    if n_pigf and west:
        minp["PIGF"] = 0.98
        maxp["PIGF"] = 1.01
    if ms == "NL000000":
        maxp["PIGF"] = 1.0025
    if ms == "DK000000":
        maxp["PIGF"] = 1.005
    if n_pouf and west:
        maxp["POUF"] = 1.015
    if n_pigf and east:
        maxp["PIGF"] = 1.015
    if n_pouf and east:
        maxp["POUF"] = 1.02
    if n_pigf and west:
        maxt["PIGF"] = 1.4
    if n_pouf and west:
        maxt["POUF"] = 1.7
    if n_pigf and east:
        maxt["PIGF"] = 1.7
    if n_pouf and east:
        maxt["POUF"] = 2.3
    return minp, maxp, mint, maxt


def V_EstV_up_MAACT_LEVL(up, bast, bas, fac, tot, n_t, n_b, span_t, span_b):
    r"""V_EstV.UP of a herd in the ex-ante years without data: at most the larger of BAST and BAS growing by
    maxFacPerY a year, and of their linear growth to maxFacTot at the last ex-ante year.

    up: the bound before (+inf where none); bast, bas: p_data(., a, "LEVL", "BAST" / "BAS"); fac, tot: maxFacPerY,
    maxFacTot (0 where none); n_t, n_b: OrdT(ExanteT) - OrdT("BAST") and - OrdT("BAS"); span_t, span_b:
    OrdT("Lst_exAnte") less the same.

    CAPRI's GAMS (captrd/fix_est.gms l. 467-482):

            V_EstV.UP(Rest,mAACT,"LEVL",exAnteT) $ p_data(Rest,MAACT,"LEVL","maxFacPerY")
               = min( V_EstV.UP(Rest,mAACT,"LEVL",exAnteT),
                      max( P_DATA(Rest,mAACT,"LEVL","BAST")
                          *p_data(Rest,MAACT,"LEVL","maxFacPerY")**(OrdT(ExanteT)-OrdT("BAST")),
                           P_DATA(Rest,mAACT,"LEVL","BAS")
                          *p_data(Rest,MAACT,"LEVL","maxFacPerY")**(OrdT(ExanteT)-OrdT("BAS"))
                          ),
                      max( P_DATA(Rest,mAACT,"LEVL","BAST")
                          *(1+(p_data(Rest,MAACT,"LEVL","maxFacTot")-1)
                             *(OrdT(ExanteT)-OrdT("BAST"))
                             /(OrdT("Lst_exAnte")-OrdT("BAST"))),
                           P_DATA(Rest,mAACT,"LEVL","BAS")
                          *(1+(p_data(Rest,MAACT,"LEVL","maxFacTot")-1)
                             *(OrdT(ExanteT)-OrdT("BAS"))
                             /(OrdT("Lst_exAnte")-OrdT("BAS")))
                         ));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(up, max(bast * fac ** n_t, bas * fac ** n_b),
               max(bast * (1 + (tot - 1) * n_t / span_t), bas * (1 + (tot - 1) * n_b / span_b)))


def V_EstV_lo_MAACT_LEVL(lo, bast, bas, fac, tot, n_t, n_b, span_t, span_b):
    r"""V_EstV.LO of a herd in the ex-ante years without data: at least the smaller of BAST and BAS falling by
    minFacPerY a year and of their linear change to minFacTot, and BAS's own where BAST is zero.

    lo: the bound before (-inf where none); the others as V_EstV_up_MAACT_LEVL with minFacPerY and minFacTot.

    CAPRI's GAMS (captrd/fix_est.gms l. 484-507):

            V_EstV.lo(Rest,mAACT,"LEVL",exAnteT) $ p_data(Rest,MAACT,"LEVL","minFacPerY")
               = max( V_EstV.lo(Rest,mAACT,"LEVL",exAnteT),
                      (P_DATA(Rest,mAACT,"LEVL","BAS")
                      *p_data(Rest,MAACT,"LEVL","minFacPerY")**(OrdT(ExanteT)-OrdT("BAS")))
                      $ (not P_DATA(Rest,mAACT,"LEVL","BAST")),
                      min( P_DATA(Rest,mAACT,"LEVL","BAST")
                          *p_data(Rest,MAACT,"LEVL","minFacPerY")**(OrdT(ExanteT)-OrdT("BAST")),
                           P_DATA(Rest,mAACT,"LEVL","BAS")
                          *p_data(Rest,MAACT,"LEVL","minFacPerY")**(OrdT(ExanteT)-OrdT("BAS"))
                          ),
                      (P_DATA(Rest,mAACT,"LEVL","BAS")
                      *(1+(p_data(Rest,MAACT,"LEVL","minFacTot")-1)
                         *(OrdT(ExanteT)-OrdT("BAS"))
                         /(OrdT("Lst_exAnte")-OrdT("BAS"))))
                      $ (not P_DATA(Rest,mAACT,"LEVL","BAST")),
                      min( P_DATA(Rest,mAACT,"LEVL","BAST")
                          *(1+(p_data(Rest,MAACT,"LEVL","minFacTot")-1)
                             *(OrdT(ExanteT)-OrdT("BAST"))
                             /(OrdT("Lst_exAnte")-OrdT("BAST"))),
                           P_DATA(Rest,mAACT,"LEVL","BAS")
                          *(1+(p_data(Rest,MAACT,"LEVL","minFacTot")-1)
                             *(OrdT(ExanteT)-OrdT("BAS"))
                             /(OrdT("Lst_exAnte")-OrdT("BAS")))
                         ));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    cand = [lo, min(bast * fac ** n_t, bas * fac ** n_b),
            min(bast * (1 + (tot - 1) * n_t / span_t), bas * (1 + (tot - 1) * n_b / span_b))]
    if not bast:
        cand += [bas * fac ** n_b, bas * (1 + (tot - 1) * n_b / span_b)]
    else:
        cand += [0.0, 0.0]
    return max(cand)


def V_EstV_up_TWIN(ms, basm):
    r"""V_EstV.UP of wine's area under the CMO's planting rights: the base plus the member state's rights (1000 ha).

    ms: the member state; basm: p_data(ms, "TWIN", "LEVL", "BASM"). Returns the bound, or None for a member state
    without rights.

    CAPRI's GAMS (captrd/fix_est.gms l. 512-521):

           v_estV.UP("DE000000","TWIN","LEVL",RESY) $ rest("DE000000") =  p_data("DE000000","TWIN","LEVL","BASM") + 1.534;
           v_estV.UP("EL000000","TWIN","LEVL",RESY) $ rest("EL000000") =  p_data("EL000000","TWIN","LEVL","BASM") + 1.098;
           v_estV.UP("ES000000","TWIN","LEVL",RESY) $ rest("ES000000") =  p_data("ES000000","TWIN","LEVL","BASM") + 17.355;
           v_estV.UP("FR000000","TWIN","LEVL",RESY) $ rest("FR000000") =  p_data("FR000000","TWIN","LEVL","BASM") + 13.565;
           v_estV.UP("IT000000","TWIN","LEVL",RESY) $ rest("IT000000") =  p_data("IT000000","TWIN","LEVL","BASM") + 12.933;
           v_estV.UP("BL000000","TWIN","LEVL",RESY) $ rest("BL000000") =  p_data("BL000000","TWIN","LEVL","BASM") +  0.018;
        * ag: never fix a region below MS
           v_estV.UP(Rest,"TWIN","LEVL",RESY) $ (SAMEAS(Rest,"BL400000"))  =  p_data(Rest,"TWIN","LEVL","BASM") +  0.018;
           v_estV.UP("AT000000","TWIN","LEVL",RESY) $ REST("AT000000")  =  p_data("AT000000","TWIN","LEVL","BASM") +  0.737;
           v_estV.UP("PT000000","TWIN","LEVL",RESY) $ REST("PT000000")  =  p_data("PT000000","TWIN","LEVL","BASM") +  3.760;

    BL400000's line (l. 519, a region of Belgium as its own Rest) is not ported: the port bounds member states and the
    regions of the NUTS 2 estimation by their own codes, so BL400000 would take it as a region (none of the reference's
    regions is BL400000); the years RESY, the simulation years, are the caller's."""
    rights = {"DE000000": 1.534, "EL000000": 1.098, "ES000000": 17.355, "FR000000": 13.565, "IT000000": 12.933,
              "BL000000": 0.018, "AT000000": 0.737, "PT000000": 3.760}
    if ms not in rights:
        return None
    return basm + rights[ms]


def V_EstV_up_OOIL(basm, n):
    r"""V_EstV.UP of other oils' area: 1% a year above the base.

    CAPRI's GAMS (captrd/fix_est.gms l. 525-528):

           v_estV.UP(REST,"OOIL","LEVL",exAnte)
                                                   $ ( (NOT P_Result(Rest,"OOIL","LEVL",ExAnte,"coco"))
                                                       $ p_data(Rest,"OOIL","LEVL","nObs"))
                = p_data(REST,"OOIL","LEVL","BASM") * (1.01**(OrdT(exAnte)-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 1.01 ** n


def V_EstV_fx_young_animals():
    r"""V_EstV.FX of the fixed young-animal coefficients (FIX_YAI's inputs, FIX_YAO's outputs): 1000 a head.

    CAPRI's GAMS (captrd/fix_est.gms l. 534-538):

           v_estV.FX(Rest,FIX_YAI,IYANI,Exante) $ (p_data(Rest,FIX_YAI,"LEVL","nObs") $ PACT_TO_I(FIX_YAI,IYANI)) = 1000;
           p_data(Rest,FIX_YAI,IYANI,"nObs")    $ (p_data(Rest,FIX_YAI,"LEVL","nObs") $ PACT_TO_I(FIX_YAI,IYANI)) = 1;

           v_estV.FX(Rest,FIX_YAO,OYANI,Exante) $ (p_data(Rest,FIX_YAO,"LEVL","nObs") $ PACT_TO_O(FIX_YAO,OYANI)) = 1000;
           p_data(Rest,FIX_YAO,OYANI,"nObs")    $ (p_data(Rest,FIX_YAO,"LEVL","nObs") $ PACT_TO_O(FIX_YAO,OYANI)) = 1;

    the nObs flags CAPRI sets alongside (l. 535, 538) are not set here: the bounds do not change the data."""
    return 1000.0


def V_EstV_fx_FixYield(bas):
    r"""V_EstV.FX of a fixed yield (FixYield): its BAS.

    CAPRI's GAMS (captrd/fix_est.gms l. 541-541):

           v_estV.FX(Rest,FixYield,O,Exante)    $ p_data(Rest,FixYield,O,"nObs")    = p_data(Rest,FixYield,O,"BAS");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return bas


def V_EstV_fx_DAYS():
    r"""V_EstV.FX of the days of the activities with 365 days (AACTwith365days), set twice by CAPRI.

    CAPRI's GAMS (captrd/fix_est.gms l. 542-542):

           v_estV.FX(Rest,AACTwith365days,"DAYS",Exante)    $ p_data(Rest,AACTwith365days,"DAYS","nObs")    = 365;

    CAPRI's GAMS (captrd/fix_est.gms l. 679-679):

           v_estV.FX(Rest,MAACT,"DAYS",exAnte) $ AACTwith365days(MAACT) = 365;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 365.0


def V_EstV_STRA():
    r"""V_EstV.LO and .UP of the cereals' straw yields: free from 0 to 30 t. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 547-548):

           v_estV.UP(REST,CERE,"STRA",exAnte) $ p_data(Rest,CERE,"STRA","nObs") = 30000;
           v_estV.LO(REST,CERE,"STRA",exAnte) $ p_data(Rest,CERE,"STRA","nObs") = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0, 30000.0


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


def V_EstV_MLKSECO(basm, x, span):
    r"""V_EstV.LO and .UP of a milk content of a dairy product: the base plus and minus up to 20% at the last
    ex-ante year.

    basm: p_data(., m, s, "BASM"); x, span: as V_EstV_MEAT. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 681-687):

           v_estV.lO(REST,MLKCNT,MLKSECO,exAnte) $ (p_data(Rest,MLKCNT,MLKSECO,"nObs") $ NUTS0(Rest))
               = p_data(REST,MLKCNT,MLKSECO,"BASM")
               * (1. - 0.20 * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        *
           v_estV.UP(REST,MLKCNT,MLKSECO,exAnte) $ (p_data(Rest,MLKCNT,MLKSECO,"nObs") $ NUTS0(Rest))
               = p_data(REST,MLKCNT,MLKSECO,"BASM")
               * (1. + 0.20 * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    r = 0.20 * x / span
    return basm * (1.0 - r), basm * (1.0 + r)


def V_EstV_fx_MLKCNT(basm):
    r"""V_EstV.FX of the milk contents of MILK, BUTT and SMIP: their base.

    CAPRI's GAMS (captrd/fix_est.gms l. 689-691):

           v_estV.fx(REST,MLKCNT,"MILK",exAnte)  $ p_data(Rest,MLKCNT,"MILK","nObs")  = p_data(REST,MLKCNT,"MILK","BASM");
           v_estV.fx(REST,MLKCNT,"BUTT",exAnte)  $ p_data(Rest,MLKCNT,"BUTT","nObs")  = p_data(REST,MLKCNT,"BUTT","BASM");
           v_estV.fx(REST,MLKCNT,"SMIP",exAnte)  $ p_data(Rest,MLKCNT,"SMIP","nObs")  = p_data(REST,MLKCNT,"SMIP","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_PRCY(basm, proc_yield):
    r"""V_EstV.LO and .UP of a processing yield: 1% around the base; for the oilseeds' cakes and oils within 10% of
    their technical yields (Proc_Yields), which the bounds include.

    basm: p_data(., "PRCY", s, "BASM"); proc_yield: Proc_Yields(s) (captrd.gms), None where the product has none.
    Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 693-700):

           v_estV.LO(REST,"PRCY",SECO,exAnte)    $ p_data(Rest,"PRCY",SECO,"nObs")   = p_data(Rest,"PRCY",SECO,"BASM")*0.99;
           v_estV.UP(REST,"PRCY",SECO,exAnte)    $ p_data(Rest,"PRCY",SECO,"nObs")   = p_data(Rest,"PRCY",SECO,"BASM")*1.01;

        *        Try to squeeze prcy into range arround BAS and tech coefficeints in line with bounds in data_cal
           v_estV.LO(REST,"PRCY",SECO,exAnte)    $ (p_data(Rest,"PRCY",SECO,"nObs") $ Proc_yields(SECO))
               = min(max(Proc_Yields(SECO) * 0.90,p_data(Rest,"PRCY",SECO,"BASM")*0.99),Proc_Yields(SECO)) ;
           v_estV.UP(REST,"PRCY",SECO,exAnte)    $ (p_data(Rest,"PRCY",SECO,"nObs") $ Proc_yields(SECO))
               = max(min(Proc_Yields(SECO) * 1.1,p_data(Rest,"PRCY",SECO,"BASM")*1.01),Proc_Yields(SECO)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    lo, up = basm * 0.99, basm * 1.01
    if proc_yield is not None:
        py = proc_yield
        lo = min(max(py * 0.90, basm * 0.99), py)
        up = max(min(py * 1.1, basm * 1.01), py)
    return lo, up


def V_EstV_fx_PRCY_MILK(basm):
    r"""V_EstV.FX of raw milk's processing yield: its base.

    CAPRI's GAMS (captrd/fix_est.gms l. 702-702):

           v_estV.FX(REST,"PRCY","MILK",exAnte)  $ p_data(Rest,"PRCY","MILK","nObs")     = p_data(Rest,"PRCY","MILK","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_PRCY_MLKSECO(basm):
    r"""V_EstV.LO and .UP of a dairy product's processing yield: 50% and 150% of its base. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 704-705):

           v_estV.LO(REST,"PRCY",MLKSECO,exAnte) $ p_data(Rest,"PRCY",MLKSECO,"nObs")   = p_data(Rest,"PRCY",MLKSECO,"BASM")*0.50;
           v_estV.UP(REST,"PRCY",MLKSECO,exAnte) $ p_data(Rest,"PRCY",MLKSECO,"nObs")   = p_data(Rest,"PRCY",MLKSECO,"BASM")*1.50;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.50, basm * 1.50


def V_EstV_up_STCM(levels, cows):
    r"""V_EstV.UP of a young animal's stock change: 20% of the herds producing it (YCOW's with the dairy and
    suckler cows' herds added to each).

    levels: p_data(., a, "LEVL", "BASM") of the activities producing it (PACT_TO_O), in the caller's order; cows:
    DCOW's and SCOW's BASM summed for YCOW, else 0.

    CAPRI's GAMS (captrd/fix_est.gms l. 707-711):

           v_estV.UP(REST,"STCM",OYANI,exAnte) $ NUTS0(Rest)
                                                   = 0.2*ABS(SUM(PACT_TO_O(MPACT,OYANI),
                                                                   p_data(Rest,MPACT,"LEVL","BASM")
                                                                +  p_data(Rest,"DCOW","LEVL","BASM") $ SAMEAS(OYANI,"YCOW")
                                                                +  p_data(Rest,"SCOW","LEVL","BASM") $ SAMEAS(OYANI,"YCOW")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    tot = 0.0
    for levl in levels:
        tot += levl + cows
    return 0.2 * abs(tot)


def V_EstV_lo_MrkBalee(e, lo):
    r"""V_EstV.LO of a market balance position, not fixed and not negative: at least 1e-8 (the losses and the
    seed and feed uses SEDM, SEDF, LOSM, LOSF from 1e-8 only).

    e: the column; lo: the bound before.

    CAPRI's GAMS (captrd/fix_est.gms l. 713-723):

           v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) $ (
                                                         (v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) GE 0)
                                                       $ (v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) NE v_estV.up(REST,MrkBalee,S_RowsEst,exAnte))
                                                       $ p_data(Rest,MrkBalee,S_RowsEst,"nObs")
                                                       $ NUTS0(Rest))
              = MAX(v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte)
                          $ (NOT (   SAMEAS(MrkBalee,"SEDM")
                                  or SAMEAS(MrkBalee,"SEDF")
                                  or SAMEAS(MrkBalee,"LOSM")
                                  or SAMEAS(MrkBalee,"LOSF"))),
                    1.E-8  );

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    keep = lo if e not in ("SEDM", "SEDF", "LOSM", "LOSF") else 0.0
    return max(keep, 1.0e-8)


def V_EstV_lo_STCM(up):
    r"""V_EstV.LO of a young animal's stock change: minus its upper bound.

    CAPRI's GAMS (captrd/fix_est.gms l. 725-725):

           v_estV.lO(REST,"STCM",OYANI,exAnte) $ NUTS0(Rest)  = -v_estV.UP(REST,"STCM",OYANI,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -up


def V_EstV_NTRD():
    r"""V_EstV.LO and .UP of net trade: free. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 727-728):

           v_estV.UP(REST,"NTRD",S_RowsEst,exAnte) $ NUTS0(Rest) = +inf;
           v_estV.lO(REST,"NTRD",S_RowsEst,exAnte) $ NUTS0(REST)  = -inf;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -float("inf"), float("inf")


def V_EstV_INTP(support):
    r"""V_EstV.LO and .UP of intervention stocks: within twice the support's size. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 730-734):

           v_estV.lo(Rall,"INTP",S_RowsEst,Exante) $ p_data(Rall,"INTP",S_RowsEst,"nObs")
               = -ABS(P_Result(Rall,"INTP",S_RowsEst,Exante,"Support")) * 2;

           v_estV.UP(Rall,"INTP",S_RowsEst,Exante) $ p_data(Rall,"INTP",S_RowsEst,"nObs")
               = +ABS(P_Result(Rall,"INTP",S_RowsEst,Exante,"Support")) * 2;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -abs(support) * 2, abs(support) * 2


def V_EstV_GROF_labour(w, basm, mins, maxs):
    r"""V_EstV.LO and .UP of labour (LABO, LABN, LABH): the base times LABO's exogenous minimum and maximum shares,
    widened by 5 points for LABO and LABN.

    w: the row; basm: p_data(., "GROF", w, "BASM"); mins, maxs: p_result(., "MINS" / "MAXS", "LABO", "p_data").
    Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 740-756):

           v_estV.LO(Rest,"GROF","LABO",exante) $ p_data(Rest,"GROF","LABO","BASM")
               = MAX(0,p_data(Rest,"GROF","LABO","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data") - 0.05));

           v_estV.LO(Rest,"GROF","LABN",exante) $ p_data(Rest,"GROF","LABN","BASM")
               = Max(0,p_data(Rest,"GROF","LABN","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data") - 0.05));

           v_estV.LO(Rest,"GROF","LABH",exante) $ p_data(Rest,"GROF","LABH","BASM")
               = MAX(0,p_data(Rest,"GROF","LABH","BASM") * (p_result(REST,"MINS","LABO",EXANTE,"p_data")));

           v_estV.UP(Rest,"GROF","LABO",exante) $ p_data(Rest,"GROF","LABO","BASM")
               = p_data(Rest,"GROF","LABO","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data") + 0.05);

           v_estV.UP(Rest,"GROF","LABN",exante) $ p_data(Rest,"GROF","LABN","BASM")
               = p_data(Rest,"GROF","LABN","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data") + 0.05);

           v_estV.UP(Rest,"GROF","LABH",exante) $ p_data(Rest,"GROF","LABH","BASM")
               = p_data(Rest,"GROF","LABH","BASM") * (p_result(REST,"MAXS","LABO",EXANTE,"p_data"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    dl, du = {"LABO": (-0.05, 0.05), "LABN": (-0.05, 0.05), "LABH": (0.0, 0.0)}[w]
    return max(0.0, basm * (mins + dl)), basm * (maxs + du)


def V_EstV_expert_corridor(lo, up, expert):
    r"""V_EstV.LO and .UP of a position whose support is the expert's: within at least 10% of it.

    lo, up: the bounds before; expert: P_Result(., "Expert"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 764-780):

           v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) $   (
                                                              (  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                              EQ P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Support"))
                                                          $ (  v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte))
                                                          $  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                          $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs"))
           = MIN(v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte), 0.9*P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert"));

           v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte)   $ (
                                                              (  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                              EQ P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Support"))
                                                          $ (  v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte))
                                                          $  P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert")
                                                          $ p_data(Rest,S_ColsEst,S_RowsEst,"nObs"))
           = MAX(v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte), 1.1*P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"Expert"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return min(lo, 0.9 * expert), max(up, 1.1 * expert)


def V_EstV_UAAR(basm, n):
    r"""V_EstV.LO and .UP of the utilised agricultural area: at most the base, falling by at most 0.2% a year.

    basm: p_data(., "UAAR", "LEVL", "BASM"); n: OrdT(exAnte) - OrdT("BAS"). Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 785-795):

           v_estV.UP(REST,"UAAR","LEVL",exAnte)
                                                   $ (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
           = p_data(REST,"UAAR","LEVL","BASM");

        *       ... and cannot change by more than -0.2% per annum
        *      (Even though this is less than observed in some MS15 (ES, IT, AT, PT, SE, FI))
        *
           v_estV.lO(REST,"UAAR","LEVL",exAnte)
                                                   $ (NOT P_Result(Rest,"UAAR","LEVL",ExAnte,"coco"))
           = p_data(REST,"UAAR","LEVL","BASM")
                                                * (0.998**(OrdT(exAnte)-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.998 ** n, basm


def V_EstV_ARTIF(basm, n_obs, up, t, ord_bas, as_coded):
    r"""V_EstV.LO and .UP of artificial land: at least its base, at most growing by 2% a year (and the upper bound
    before).

    basm: p_data(MSEst, "ARTIF", "LEVL", "BASM"); n_obs: it has data; up: the bound before (+inf where none); t,
    ord_bas: OrdT(ExAnte), OrdT("BAS"); as_coded: l. 810's parenthesis as coded. Returns (lo, up).

    l. 810 reads 1.02**(OrdT(ExAnte)) - OrdT("BAS"): the year as the exponent (CAPRI-ERROR, a misplaced parenthesis;
    FIX-7). Fixed (the default, as_coded False), 1.02**(OrdT(ExAnte) - OrdT("BAS")) as the comment's "max. 2%
    increase per year"; the max with the previous bound kept, as coded, so where that is the standard 1e9 the bound
    stays 1e9.

    CAPRI's GAMS (captrd/fix_est.gms l. 805-811):

           v_estV.LO(MSEst,"ARTIF","LEVL",exAnte) $ Rest(MSest)
                       = sum(REST $ (MAP_RR(MSEst,Rest) $ p_data(Rest,"ARTIF","LEVL","nObs")),
                                     P_DATA(REST,"ARTIF","LEVL","BASM"));
        *       -- let's impose a suitable upper bound (max. 2% increase per year, or the previous bound)
           v_estV.UP(MSEst,"ARTIF","LEVL",exAnte) $ Rest(MSest)
                      = max( v_estV.LO(MSEst,"ARTIF","LEVL",exAnte) * 1.02**(OrdT(ExAnte)) - OrdT("BAS"),
                             v_estV.UP(MSEst,"ARTIF","LEVL",exAnte));

    l. 810's parenthesis (above, setting captrd.artif_upper_bound_as_coded); the sum over the member state's regions is
    the member state's own BASM (the member state's estimation only)."""
    lo = basm if n_obs else 0.0
    cap = lo * 1.02 ** t - ord_bas if as_coded else lo * 1.02 ** (t - ord_bas)
    return lo, max(cap, up)


def V_EstV_fx_land(basm):
    r"""V_EstV.FX of the fixed land uses ARTO, INLW and KITC: their base.

    CAPRI's GAMS (captrd/fix_est.gms l. 814-816):

           v_estV.FX(Rest,"ARTO","LEVL",exAnte) = P_DATA(Rest,"ARTO","LEVL","BASM");
           v_estV.FX(Rest,"INLW","LEVL",exAnte) = P_DATA(Rest,"INLW","LEVL","BASM");
           v_estV.FX(Rest,"KITC","LEVL",exAnte) = P_DATA(Rest,"KITC","LEVL","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_fx_RSET():
    r"""V_EstV.FX of the set-aside activities' levels where the western EU has no set-aside rate: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 822-822):

            v_estV.fx(REST,RSET,"LEVL",exAnte) $ (not sum((grcu,CurEUWestAgg),p_data(CurEUWestAgg,GRCU,"SETR",ExAnte))) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_fx_tiny_support():
    r"""V_EstV.FX of a position with a near-zero support and COCO value in the years with data: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 827-834):

            v_estV.FX(REST,s_colsEst,s_rowsEst,exAnte) $ (    P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")
        *                                           do not interfere with comi_Bounds (as COMI is only completed in coco2)
                                                $ (not (SAMEAS(s_rowsEst,"COMI") or SAMEAS(s_rowsEst,"SUGA")))
                                                $ (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"SUPPORT")) lt 1e-12)
                                                $ ExAnteD(ExAnte)
                                                $ (ABS(P_Result(Rest,s_colsEst,s_rowsEst,Exante,"coco")) lt 1e-12)
                                                $ P_Result(Rest,s_colsEst,s_rowsEst,Exante,"p_data")
                                                )  = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0


def V_EstV_lo_SUGB():
    r"""V_EstV.LO of sugar beet's level, EAAG and TOOU where it has no production: zero.

    CAPRI's GAMS (captrd/fix_est.gms l. 849-851):

           v_estV.LO(Rest,"SUGB","LEVL",Exante) $ (v_estV.LO(Rest,"GROF","SUGB",Exante) eq  0) = 0;
           v_estV.LO(Rest,"EAAG","SUGB",Exante) $ (v_estV.LO(Rest,"GROF","SUGB",Exante) eq  0) = 0;
           v_estV.LO(Rest,"SUGB","TOOU",Exante) $ (v_estV.up(Rest,"GROF","SUGB",Exante) eq  0) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return 0.0

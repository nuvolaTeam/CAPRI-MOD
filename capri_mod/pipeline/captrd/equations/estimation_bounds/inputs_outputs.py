r"""CAPTRD's estimation bounds of the inputs and outputs, young animals, feeds, fodder and requirements
(captrd/fix_est.gms; moved from capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
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

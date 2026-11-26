r"""CAPTRD's estimation bounds of the crop and animal levels, TWIN, OOIL, the fixed yields, days and straw
(captrd/fix_est.gms; moved from capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




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

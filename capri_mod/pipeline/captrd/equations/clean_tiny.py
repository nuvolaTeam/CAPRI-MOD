r"""CAPTRD's statements of captrd/clean_tiny.gms (CAPRI star 3.0, included by estimate_ms.gms l. 446 after Solve2): the
cleaning of tiny values from the member state's result, the flags, bounds, starting levels and variances of its last
solve, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/clean_tiny.py (clean) holds the loops over the
positions, the conditions and the solve, and calls them; the arithmetic is the port's, so the cleaning is unchanged.
p_tiny is sets_captrd.gms's (0.1), p_tinyR the regional one.
"""
from __future__ import annotations

import math


def p_tinyR(p_tiny, n_nuts2):
    r"""p_tinyR: p_tiny x the square root of the member state's NUTS 2 regions.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 22-22):

             p_tinyR = p_tiny*SQRT(SUM(MAP_RR(Rest,NT2),1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return p_tiny * math.sqrt(n_nuts2)


def p_result_Tiny(value):
    r"""p_result(., "SupportTiny" / "wVarErrTiny" / "Step3Tiny" / "loTiny" / "upTiny"): Solve2's support, variance,
    level (of the positions with observations, DOMM.DDGS not, or a support) and finite bounds kept for the restore;
    the support set to Step3Tiny (l. 59).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 26-43):

             p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"SupportTiny") = p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support");
             P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErrTiny") = P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErr") ;
             P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Step3Tiny")  = v_estV.L(Rest,S_ColsEst,S_RowsEst,Exante)
                                                                  $ (  ( p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
        *                                                              DOMM.DDGS is only activated in DOMM_ or SSQS_ if there is a support:
        *                                                              => entries on v_estv may stem from old restart files
                                                                       $ (NOT (sameas(S_ColsEst,"DOMM") $ sameas(S_RowsEst,"DDGS"))))
                                                                    or p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"));
             p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"loTiny")
                = v_estV.LO(Rest,S_ColsEst,S_RowsEst,Exante) $ ( (   p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
                                                                or p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"))
                                                             $ (v_estV.LO(Rest,S_ColsEst,S_RowsEst,Exante) GT -INF))
                                                                ;
             p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"upTiny")
                = v_estV.UP(Rest,S_ColsEst,S_RowsEst,Exante) $ ( (   p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
                                                                or p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"))
                                                             $ (v_estV.UP(Rest,S_ColsEst,S_RowsEst,Exante) LT INF))
                                                                ;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 59-59):

             p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Support") = p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Step3Tiny");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return value


def V_EstV_keep(level, p_tiny):
    r"""V_EstV.UP and .LO of a bounded position whose bounds are apart: within 0.5% of its level, at most 3 p_tiny away
    (not below zero for a positive level); a zero level fixes it at zero. Returns (lo, up).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 62-83):

             v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte) $ ( (  (v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte) LT inf)
                                                            or (v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) GT -inf))
                                                          $ (  p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"upTiny")
                                                            GT p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"loTiny")))
               = MAX(1.005*v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte),.995*v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte),
        *            The maximum adjustment of tiny values will be p_tiny/2, like in rounding to p_tiny.
        *            => other variables may need to adjust to preserve market balances.
        *            Allowing a larger adjustment than p_tiny helps to clean RowsTiny=LEVL, because:
        *            1) p_tinyR>p_tiny for MS with several NUTS2
        *            2) Typically YILD>1000kg/ha, say 10000kg/ha => removing a LEVL=.1 requires removing GROF=10*.1=1.0 in the example.
        *            The "cost" of rigorous cleaning of LEVL are thus larger adjustments in other positions.
                     v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte)+3*p_tiny)
                 $ v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte);

             v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) $ ( (  (v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte) LT inf)
                                                            or (v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) GT -inf))
                                                          $ (  p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"upTiny")
                                                            GT p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"loTiny")))
               = MIN(1.005*v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte),.995*v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte),
        *            In spite of some leeway, positive items must not become negative:
                     MAX(v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte)-3*p_tiny,-inf $ ( v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte) lt 0)))
                 $ v_estV.l(Rest,S_ColsEst,S_RowsEst,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    v = level
    up = max(1.005 * v, 0.995 * v, v + 3.0 * p_tiny) if v else 0.0
    lo = min(1.005 * v, 0.995 * v, max(v - 3.0 * p_tiny, -float("inf") if v < 0 else 0.0)) if v else 0.0
    return lo, up


def P_Result_wVarErr_kept(support):
    r"""P_Result(., "wVarErr") of the kept positions with a support: trust level 2, at least 0.01.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 85-89):

             P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErr") $ ( ( P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"))
                                                                   $ (  p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"upTiny")
                                                                     GT p_result(MS,S_ColsEst,S_RowsEst,ExAnte,"loTiny")))
        *                                                   corresponds to low trustlevl = 2:
             = MAX(SQR(P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support") * 0.05 / 3 * (10/2)),.01);

    Departures from CAPRI: the port computes support x (0.05 / 3) x 10 / 2 where CAPRI writes support x 0.05 / 3 x (10 / 2) (the order of
    operations may differ in the last digit); the domain condition in the caller (clean_tiny.clean)."""
    return max((support * (0.05 / 3) * 10.0 / 2.0) ** 2, 0.01)


def p_result_Support_down():
    r"""p_result(., "Support") of a position pulled to zero: -1 (below p_tiny / 2 or p_tinyR / 2, and passed on from
    the levels to GROF, EAAG, fodder FEDM and DOMM, the market positions without imports, INHA and EXPE, the fodder
    inputs).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 94-96):

             p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Support") $ (  (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") LT (p_tiny/2))
                                                                  $  (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") GT 0)  )
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 121-123):

             p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Support") $ ( (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") LT (p_tinyR/2))
                                                                  $ (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") GT 0))
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 127-128):

             p_result(Rest,"GROF",S_RowsEst,ExAnte,"Support") $ (SUM(PACT_TO_Y(S_ColsEst,S_RowsEst),p_result(Rest,S_ColsEst,"LEVL",ExAnte,"Support"))  EQ -1)
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 132-133):

             p_result(Rest,"EAAG",S_RowsEst,ExAnte,"Support") $ (p_result(Rest,"GROF",S_RowsEst,ExAnte,"Support")  EQ -1)
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 137-140):

             p_result(Rest,"FEDM",FODF,ExAnte,"Support") $ (p_result(Rest,"GROF",FODF,ExAnte,"Support")  EQ -1)
                 = -1;
             p_result(Rest,"DOMM",FODF,ExAnte,"Support") $ (p_result(Rest,"GROF",FODF,ExAnte,"Support")  EQ -1)
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 144-148):

             p_result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support") $ (  (   (p_result(Rest,"GROF",S_RowsEst,ExAnte,"Support")  EQ -1)
                                                                       or (p_result(Rest,"MAPR",S_RowsEst,ExAnte,"Support")  EQ -1))
                                                                   $  (p_result(Rest,"IMPT",S_RowsEst,ExAnte,"Support")  LE 0)
                                                                   $ (DOMPOS(S_ColsEst) or SAMEAS("DOMM",S_ColsEst)  or SAMEAS("EXPT",S_COlsEst)))
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 152-154):

             p_result(Rest,s_colsEst,S_RowsEst,ExAnte,"Support") $ ( (p_result(Rest,"HCOM",S_RowsEst,ExAnte,"Support")  EQ -1)
                                                                   $ (SAMEAS(S_ColsEst,"INHA") or SAMEAS(S_ColsEst,"EXPE")))
                 = -1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 158-159):

             p_result(Rest,ColsTinyFodd,Foddi,ExAnte,"Support") $ (SUM(FEDACT_TO_FODDI(FEDACT,FODDI),p_result(Rest,Fedact,"LEVL",ExAnte,"Support"))  EQ -1)
                 = -1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return -1.0


def P_Result_NTRD_Support(expt, impt):
    r"""P_Result(., "NTRD", ., "Support") where exports or imports are pulled to zero: the flagged trade's net.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 100-103):

             P_Result(Rest,"NTRD",S_RowsEst,exAnte,"Support") $ ( (   (p_result(Rest,"EXPT",S_RowsEst,ExAnte,"Support")  EQ -1)
                                                                  or  (p_result(Rest,"IMPT",S_RowsEst,ExAnte,"Support")  EQ -1) )
                                                                $ (v_estV.UP(MS,"NTRD",S_RowsEst,Exante) GT v_estV.LO(MS,"NTRD",S_RowsEst,Exante) ))
             = MAX(0,p_result(Rest,"EXPT",S_RowsEst,ExAnte,"Support"))  - MAX(0,p_result(Rest,"IMPT",S_RowsEst,ExAnte,"Support"))  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return max(0.0, expt) - max(0.0, impt)


def p_result_Support_up():
    r"""p_result(., "Support") of a position between p_tiny / 2 and p_tiny (p_tinyR for RowsTiny): +1, pulled up.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 108-110):

             p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Support") $ ( (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") GE (p_tiny/2))
                                                                  $ (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") LE p_tiny))
                 = 1;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 164-166):

             p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Support") $ ( (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") GE (p_tinyR/2))
                                                                  $ (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") LE p_tinyR))
                 = 1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return 1.0


def V_EstV_up_tiny(tiny):
    r"""V_EstV.UP of a position pulled up, not fixed: p_tiny (p_tinyR for RowsTiny).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 113-116):

             v_estV.UP(Rest,ColsTiny,S_RowsEst,exAnte) $ ( (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") GE (p_tiny/2))
                                                         $ (p_result(Rest,ColsTiny,S_RowsEst,ExAnte,"Step3Tiny") LE p_tiny)
                                                         $ (v_estV.UP(Rest,ColsTiny,S_RowsEst,exAnte) GT v_estV.LO(Rest,ColsTiny,S_RowsEst,exAnte)))
                 = p_tiny;

    CAPRI's GAMS (captrd/clean_tiny.gms l. 168-171):

             v_estV.UP(Rest,S_ColsEst,RowsTiny,exAnte) $ ( (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") GE (p_tinyR/2))
                                                         $ (p_result(Rest,S_ColsEst,RowsTiny,ExAnte,"Step3Tiny") LE p_tinyR)
                                                         $ (v_estV.UP(Rest,S_ColsEst,RowsTiny,exAnte) GT v_estV.LO(Rest,S_ColsEst,RowsTiny,exAnte)))
                 = p_tinyR;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return tiny


def V_EstV_fx_flagged(level):
    r"""V_EstV.FX of the yields of flagged outputs and activities and the unit values of flagged outputs: their
    level.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 176-184):

             v_estV.fx(Rest,Pact,S_RowsEst,exAnte) $ ( (   (p_result(Rest,"GROF",S_RowsEst,ExAnte,"Support") EQ -1)
                                                        or (p_result(Rest,Pact,"LEVL",ExAnte,"Support") EQ -1))
                                                     $ PACT_TO_O(Pact,S_RowsEst) $ S_ColsEst(PACT))
                 = v_estV.l(Rest,Pact,S_RowsEst,exAnte) ;

        *    --- same for UVAGs

             v_estV.fx(Rest,"UVAG",S_RowsEst,exAnte) $ (p_result(Rest,"GROF",S_RowsEst,ExAnte,"Support") EQ -1)
                 = v_estV.l(Rest,"UVAG",S_RowsEst,exAnte) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return level


def V_EstV_lo_pulled():
    r"""V_EstV.LO of a position pulled to zero (the -1 not its own level), not fixed: zero.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 189-195):

             v_estV.LO(Rest,s_ColsEst,S_RowsEst,exAnte)  $ (  (p_result(Rest,s_colsEst,S_RowsEst,ExAnte,"Support") EQ -1)
        *                                                  indicator that the "-1" is not the original value:
                                                           $  (  p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Support")
                                                              NE p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Step3Tiny"))
                                                           $  (  v_estV.UP(Rest,s_ColsEst,S_RowsEst,exAnte)
                                                              GT v_estV.LO(Rest,s_ColsEst,S_RowsEst,exAnte)))
                 = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return 0.0


def V_EstV_lo_MrkBaleE_GRPR(level, p_tiny):
    r"""V_EstV.LO of a market balance position's group when a component is pulled to zero: within 1% of its level, at
    most 10 p_tiny away (not below zero for a positive level).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 200-207):

             v_estV.LO(Rest,MrkBaleE,GRPR,exAnte) $ ( SUM(ROWS_TO_G(s_ROWSest,GRPR) $ ( p_data(Rest,MrkBaleE,s_RowsEst,"nObs")
                                                                                      $ (P_Result(Rest,MrkBaleE,S_RowsEst,ExAnte,"Support") EQ -1)),1)
                                                    $ (v_estV.UP(Rest,MrkBaleE,GRPR,exAnte) GT v_estV.LO(Rest,MrkBaleE,GRPR,exAnte)))

               = MIN(1.01*v_estV.l(Rest,MrkBaleE,GRPR,exAnte),.99*v_estV.l(Rest,MrkBaleE,GRPR,exAnte),
        *            In spite of some leeway, positive items must not become negative:
                     MAX(v_estV.l(Rest,MrkBaleE,GRPR,exAnte)-10*p_tiny,-inf $ ( v_estV.l(Rest,MrkBaleE,GRPR,exAnte) lt 0)))
                 $ v_estV.l(Rest,MrkBaleE,GRPR,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    v = level
    return min(1.01 * v, 0.99 * v, max(v - 10.0 * p_tiny, -float("inf") if v < 0 else 0.0)) if v else 0.0


def V_EstV_lo_GRPC(level, p_tinyR):
    r"""V_EstV.LO of a crop group's level when a crop is pulled to zero: within 1% of its level, at most 10 p_tinyR
    away, not below zero.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 210-215):

             v_estV.LO(Rest,GRPC,"LEVL",exAnte) $ ( SUM(CROPC_TO_G(MCACT,GRPC) $ ( p_data(Rest,MCACT,"LEVL","nObs")
                                                                                 $ (P_Result(Rest,MCACT,"LEVL",ExAnte,"Support") EQ -1 )), 1)
                                                  $ (v_estV.UP(Rest,GRPC,"LEVL",exAnte) GT v_estV.LO(Rest,GRPC,"LEVL",exAnte)))

               = MIN(1.01*v_estV.l(Rest,GRPC,"LEVL",exAnte),.99*v_estV.l(Rest,GRPC,"LEVL",exAnte),MAX(v_estV.l(Rest,GRPC,"LEVL",exAnte)-10*p_tinyR,0))
                 $ v_estV.l(Rest,GRPC,"LEVL",exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    v = level
    return min(1.01 * v, 0.99 * v, max(v - 10.0 * p_tinyR, 0.0)) if v else 0.0


def V_EstV_UVAG_GRPR(level):
    r"""V_EstV.LO and .UP of a group's unit value when a component's EAAG is pulled to zero: 1% or 1 around its level
    (not below zero). Returns (lo, up).

    CAPRI's GAMS (captrd/clean_tiny.gms l. 220-232):

             v_estV.LO(Rest,"UVAG",GRPR,exAnte) $ ( SUM(ROWS_TO_G(s_ROWSest,GRPR) $ ( p_data(Rest,"EAAG",s_RowsEst,"nObs")
                                                                                      $ (P_Result(Rest,"EAAG",S_RowsEst,ExAnte,"Support") EQ -1)), 1)
                                                    $ (v_estV.UP(Rest,"UVAG",GRPR,exAnte) GT v_estV.LO(Rest,"UVAG",GRPR,exAnte)))

               = MIN(.99*v_estV.l(Rest,"UVAG",GRPR,exAnte),MAX(v_estV.l(Rest,"UVAG",GRPR,exAnte)-1,0))
                 $ v_estV.l(Rest,"UVAG",GRPR,exAnte);

             v_estV.UP(Rest,"UVAG",GRPR,exAnte) $ ( SUM(ROWS_TO_G(s_ROWSest,GRPR) $ ( p_data(Rest,"EAAG",s_RowsEst,"nObs")
                                                                                      $ (P_Result(Rest,"EAAG",S_RowsEst,ExAnte,"Support") EQ -1)), 1)
                                                    $ (v_estV.UP(Rest,"UVAG",GRPR,exAnte) GT v_estV.LO(Rest,"UVAG",GRPR,exAnte)))

               = MAX(1.01*v_estV.l(Rest,"UVAG",GRPR,exAnte),v_estV.l(Rest,"UVAG",GRPR,exAnte)+1)
                 $ v_estV.l(Rest,"UVAG",GRPR,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    v = level
    lo = min(0.99 * v, max(v - 1.0, 0.0)) if v else 0.0
    up = max(1.01 * v, v + 1.0) if v else 0.0
    return lo, up


def V_EstV_l_planned(flag, lo, up, p_tiny, p_tinyR, rows_tiny):
    r"""V_EstV.L at the planned solution: 0 where pulled to zero (and the lower bound 0), p_tinyR or p_tiny where
    pulled up to it. Returns the level, or None where the level stays.

    flag: the support's flag (-1, 1); lo, up: the bounds; rows_tiny: the row is in RowsTiny.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 237-247):

             v_estV.L(Rest,S_ColsEst,S_RowsEst,exAnte)  $ (  (P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support") EQ -1 )
                                                          $  (v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte) EQ 0) )
                 = 0;

             v_estV.L(Rest,S_ColsEst,S_RowsEst,exAnte)  $ (  (P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support") EQ 1 )
                                                          $  (v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte) EQ p_tiny) )
                 = p_tiny;

             v_estV.L(Rest,S_ColsEst,RowsTiny,exAnte)  $ (  (P_Result(Rest,S_ColsEst,RowsTiny,ExAnte,"Support") EQ 1 )
                                                          $ (v_estV.UP(Rest,S_ColsEst,RowsTiny,exAnte) EQ p_tinyR) )
                 = p_tinyR;

    Departures from CAPRI: CAPRI sets the p_tiny level, then the p_tinyR level of RowsTiny over it; the port tests p_tinyR first (the same
    result); the domain condition in the caller (clean_tiny.clean)."""
    if flag == -1 and lo == 0:
        return 0.0
    if flag == 1 and rows_tiny and up == p_tinyR:
        return p_tinyR
    if flag == 1 and up == p_tiny:
        return p_tiny
    return None


def P_Result_wVarErr_flagged(support, levl):
    r"""P_Result(., "wVarErr") of a flagged position not fixed: trust level 10, a level's x (1 - 0.9).

    support: the flag; levl: the row is LEVL.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 253-257):

             P_Result(Rest,S_ColsEst,S_RowsEst,exAnte,"wVarErr")
                        $ ( (P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support"))
                          $ (p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Support") NE p_result(Rest,S_Colsest,S_RowsEst,ExAnte,"Step3Tiny"))
                          $ (v_estV.UP(Rest,S_ColsEst,S_RowsEst,exAnte) GT v_estV.LO(Rest,S_ColsEst,S_RowsEst,exAnte)))
             = SQR(P_Result(Rest,S_ColsEst,S_RowsEst,ExAnte,"Support") * 0.05 / 3 * (10/10))*(1-.9 $ SAMEAS(S_RowsEst,"LEVL"));

    Departures from CAPRI: the order of operations as P_Result_wVarErr_kept's; the domain condition in the caller (clean_tiny.clean)."""
    return (support * (0.05 / 3) * 10.0 / 10.0) ** 2 * (1.0 - 0.9 * levl)


def P_Result_wVarErr_NTRD():
    r"""P_Result(., "NTRD", ., "wVarErr") where exports or imports are pulled to zero: trust level 1, weak.

    CAPRI's GAMS (captrd/clean_tiny.gms l. 260-263):

             P_Result(Rest,"NTRD",S_RowsEst,exAnte,"wVarErr") $ ( (   (p_result(Rest,"EXPT",S_RowsEst,ExAnte,"Support")  EQ -1)
                                                                  or  (p_result(Rest,"IMPT",S_RowsEst,ExAnte,"Support")  EQ -1) )
                                                                $ (v_estV.UP(MS,"NTRD",S_RowsEst,Exante) GT v_estV.LO(MS,"NTRD",S_RowsEst,Exante) ))
             = SQR(1.0 * 0.05 / 3 * (10/1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (clean_tiny.clean)."""
    return (1.0 * (0.05 / 3) * 10.0 / 1.0) ** 2

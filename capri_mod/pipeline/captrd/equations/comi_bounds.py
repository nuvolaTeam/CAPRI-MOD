r"""CAPTRD's bound statements of captrd/comi_bounds.gms (CAPRI star 3.0): milk's bounds (fix_est.gms l. 840), as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (the assignments
refactor's style: one function per statement block, named after the bounded symbol, V_EstV.LO / .UP / .FX). The
functions take the numbers the statement reads and return the bound; capri_mod/pipeline/captrd/estimate_bounds.py
(bounds) holds the domain conditions, the loops over the sets and the order of the statements, and calls them. A
bound "before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its
order of operations, so the bounds are unchanged.
"""
from __future__ import annotations


def V_EstV_fx_quotas(quota):
    r"""V_EstV.FX of the dairies' milk (PRCM) and human consumption (HCOM) of milk at their quotas (QUTA, QUTB).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 23-27):

            V_EstV.Fx(Rest,"PRCM","COMI",exante) $ (p_result(Rest,"QUTA","COMI",exante,"p_data") $ NUTS0(Rest))
               = p_result(Rest,"QUTA","COMI",exante,"p_data");

            V_EstV.Fx(Rest,"HCOM","COMI",exante) $ (p_result(Rest,"QUTB","COMI",exante,"p_data") $ NUTS0(Rest))
              = p_result(Rest,"QUTB","COMI",exante,"p_data");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return quota


def V_EstV_up_LOSF_COMI(base, n):
    r"""V_EstV.UP of milk's losses: at least 2e-8, falling by 2% a year from BAST, else BASM.

    base: BAST, else BASM; n: the years since it.

    CAPRI's GAMS (captrd/comi_bounds.gms l. 32-47):

            V_EstV.UP(Rest,"LOSF","COMI",exAnte) $ (  P_DATA(Rest,"LOSF","COMI","nObs")
        *                                             avoid interference with specific expert bounds
                                                    $ (NOT p_result(Rest,"LOSF","COMI",exante,"expertup") )
        *                                             avoid interference with coco supports ex post
                                                    $ (NOT p_result(Rest,"LOSF","COMI",exante,"p_data") ))
               = MAX(2.E-8,
                     (P_DATA(Rest,"LOSF","COMI","BAST")
                     +P_DATA(Rest,"LOSF","COMI","BASM") $ (NOT P_DATA(Rest,"LOSF","COMI","BAST")))*(1-0.02)
        *pw080513       Max(.) included to tackle rare case of zero LOSF.COMI expost
        *               => assignment is not deactivated by $ (NOT p_result(Rest,"LOSF","COMI",exante,"p_data") )
        *               => OrdT(Exante)<OrdT("BAST") => mess for V_EstV.UP and V_EstV.LO
        *               NOTE: Symmetric safeguards for PRCM.COMI (etc) are omitted below as the probability
        *                     of encountering zero PRCM.COMI (etc) expost is very small
                      **MAX(0,(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,"LOSF","COMI","BAST"))
                                           -OrdT("BAS")  $ (NOT P_DATA(Rest,"LOSF","COMI","BAST")) ))
               )  ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return max(2.0e-8, base * (1 - 0.02) ** max(0, n))


def V_EstV_lo_LOSF_COMI(base, n):
    r"""V_EstV.LO of milk's losses: falling by 4% a year from BAST, else BASM.

    CAPRI's GAMS (captrd/comi_bounds.gms l. 50-59):

            V_EstV.LO(Rest,"LOSF","COMI",exAnte) $ (  P_DATA(Rest,"LOSF","COMI","nObs")
        *                                             avoid interference with specific expert bounds
                                                    $ (NOT p_result(Rest,"LOSF","COMI",exante,"expertlo") )
        *                                             avoid interference with coco supports ex post
                                                    $ (NOT p_result(Rest,"LOSF","COMI",exante,"p_data") ))
               =      (P_DATA(Rest,"LOSF","COMI","BAST")
                      +P_DATA(Rest,"LOSF","COMI","BASM") $ (NOT P_DATA(Rest,"LOSF","COMI","BAST")))*(1-0.04)
        *               Max(.) included to tackle rare case of zero LOSF.COMI expost
                      **MAX(0,(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,"LOSF","COMI","BAST"))
                                     -OrdT("BAS")  $ (NOT P_DATA(Rest,"LOSF","COMI","BAST")) ));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return base * (1 - 0.04) ** max(0, n)


def V_EstV_PRCM_COMI(pb, pbr, lf_bast, lf_basm, t, ord_bast, ord_bas):
    r"""V_EstV.LO and .UP of the dairies' milk in the Western Balkans, Bulgaria and Romania without a quota: the
    base plus 30% and 60% of the losses' and feed's decline (2% a year), the upper bound at least the base growing
    by 4% a year.

    pb: PRCM's BAST, else BASM; pbr: its ordinal (OrdT("BAST" or "BAS")); lf_bast, lf_basm: LOSF's and FEDM's BAST
    and BASM, summed; t, ord_bast, ord_bas: the ordinals. Returns (lo, up).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 64-98):

            V_EstV.LO(Rest,"PRCM","COMI",exante) $ (  (NOT p_result(Rest,"QUTA","COMI",exante,"p_data"))
        *                                             avoid interference with coco supports ex post
                                                    $ (NOT p_result(Rest,"PRCM","COMI",exante,"p_data"))
                                                    $ (R_NUTS0_WBA7(Rest) or R_NUTS0_BUR(Rest))
                                                    $ P_DATA(Rest,"PRCM","COMI","nObs"))
                = P_DATA(Rest,"PRCM","COMI","BAST")
                 +P_DATA(Rest,"PRCM","COMI","BASM") $ (NOT P_DATA(Rest,"PRCM","COMI","BAST"))
                 + MAX(2.E-8,
                        (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))
                       +(P_DATA(Rest,"LOSF","COMI","BASM")+P_DATA(Rest,"FEDM","COMI","BASM"))
                         $ (NOT  (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))))
                 * (1.-(1.-0.02)**(ORDT(exante)
                                  -ORDT("BAST")  $      (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))
                                  -ORDT("BAS") $ (NOT (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST")))))*0.3;

            V_EstV.UP(Rest,"PRCM","COMI",exante) $ (  (NOT p_result(Rest,"QUTA","COMI",exante,"p_data"))
        *                                             avoid interference with coco supports ex post
                                                    $ (NOT p_result(Rest,"PRCM","COMI",exante,"p_data"))
                                                    $ (R_NUTS0_WBA7(Rest) or R_NUTS0_BUR(Rest))
                                                    $ P_DATA(Rest,"PRCM","COMI","nObs"))
                = MAX((P_DATA(Rest,"PRCM","COMI","BAST")
                      +P_DATA(Rest,"PRCM","COMI","BASM") $ (NOT P_DATA(Rest,"PRCM","COMI","BAST")))
                      + MAX(2.E-8,
                            (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))
                           +(P_DATA(Rest,"LOSF","COMI","BASM")+P_DATA(Rest,"FEDM","COMI","BASM"))
                            $ (NOT  (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))))
                      * (1.-(1.-0.02)**(ORDT(exante)
                                       -ORDT("BAST")  $      (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST"))
                                       -ORDT("BAS") $ (NOT (P_DATA(Rest,"LOSF","COMI","BAST")+P_DATA(Rest,"FEDM","COMI","BAST")))))*0.6,

                      ( P_DATA(Rest,"PRCM","COMI","BAST")
                       +P_DATA(Rest,"PRCM","COMI","BASM") $ (NOT P_DATA(Rest,"PRCM","COMI","BAST")))
                      * (1.+0.04)**(ORDT(exante)
                                   -ORDT("BAST")  $       P_DATA(Rest,"PRCM","COMI","BAST")
                                   -ORDT("BAS") $ (NOT  P_DATA(Rest,"PRCM","COMI","BAST"))));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    if lf_bast:
        lf, ref = lf_bast, ord_bast
    else:
        lf, ref = lf_basm, ord_bas
    lf = max(2.0e-8, lf)
    lo = pb + lf * (1.0 - (1.0 - 0.02) ** (t - ref)) * 0.3
    up = max(pb + lf * (1.0 - (1.0 - 0.02) ** (t - ref)) * 0.6, pb * 1.04 ** (t - pbr))
    return lo, up


def V_EstV_HCOM_COMI(base, n):
    r"""V_EstV.LO and .UP of milk's human consumption in the Western Balkans without a quota: 1% a year around
    BAST, else BASM (at least 2e-8). Returns (lo, up).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 103-119):

            V_EstV.LO(Rest,"HCOM","COMI",exante) $ (      (NOT p_result(Rest,"QUTB","COMI",exante,"p_data"))
                                                      $   (NOT p_result(Rest,"HCOM","COMI",exante,"p_data"))
                                                      $ R_NUTS0_WBA7(Rest) $ P_DATA(Rest,"HCOM","COMI","BASM"))
               = MAX(2.E-8,
                     (P_DATA(Rest,"HCOM","COMI","BAST")
                     +P_DATA(Rest,"HCOM","COMI","BASM") $ (NOT P_DATA(Rest,"HCOM","COMI","BAST"))))*(1-0.01)
                      **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,"HCOM","COMI","BAST"))
                                     -OrdT("BAS")  $ (NOT P_DATA(Rest,"HCOM","COMI","BAST")) );

            V_EstV.UP(Rest,"HCOM","COMI",exante) $ (      (NOT p_result(Rest,"QUTB","COMI",exante,"p_data"))
                                                      $   (NOT p_result(Rest,"HCOM","COMI",exante,"p_data"))
                                                      $ R_NUTS0_WBA7(Rest) $ P_DATA(Rest,"HCOM","COMI","BASM"))
               = MAX(2.E-8,
                     (P_DATA(Rest,"HCOM","COMI","BAST")
                     +P_DATA(Rest,"HCOM","COMI","BASM") $ (NOT P_DATA(Rest,"HCOM","COMI","BAST"))))*(1+0.01)
                      **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(Rest,"HCOM","COMI","BAST"))
                                     -OrdT("BAS")  $ (NOT P_DATA(Rest,"HCOM","COMI","BAST")) );

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return max(2.0e-8, base) * (1 - 0.01) ** n, max(2.0e-8, base) * (1 + 0.01) ** n


def P_DATA_DCOW_COMI(dcol_comi, dcol_levl, dcoh_comi, dcoh_levl, dcow_comi):
    r"""P_DATA(MS, "DCOW", "COMI", stat): the dairy cows' milk yield, the mean of the low- and high-yield cows'
    weighted by their herds (stat BASM or BAST).

    dcol_*, dcoh_*: DCOL's and DCOH's COMI and LEVL; dcow_comi: DCOW's own, kept where the herds are zero.

    CAPRI's GAMS (captrd/comi_bounds.gms l. 126-134):

            P_DATA(MS,"DCOW","COMI","BASM") $ (P_DATA(MS,"DCOL","LEVL","BASM") + P_DATA(MS,"DCOH","LEVL","BASM"))
              =   (P_DATA(MS,"DCOL","COMI","BASM") * P_DATA(MS,"DCOL","LEVL","BASM")
                   + P_DATA(MS,"DCOH","COMI","BASM")* P_DATA(MS,"DCOH","LEVL","BASM"))
                  / (P_DATA(MS,"DCOL","LEVL","BASM") + P_DATA(MS,"DCOH","LEVL","BASM"));

            P_DATA(MS,"DCOW","COMI","BAST") $ (P_DATA(MS,"DCOL","LEVL","BAST") + P_DATA(MS,"DCOH","LEVL","BAST"))
              =   (P_DATA(MS,"DCOL","COMI","BAST") * P_DATA(MS,"DCOL","LEVL","BAST")
                   + P_DATA(MS,"DCOH","COMI","BAST")* P_DATA(MS,"DCOH","LEVL","BAST"))
                  / (P_DATA(MS,"DCOL","LEVL","BAST") + P_DATA(MS,"DCOH","LEVL","BAST"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    lv = dcol_levl + dcoh_levl
    return ((dcol_comi * dcol_levl + dcoh_comi * dcoh_levl) / lv) if lv else dcow_comi


def V_EstV_COMI(basm, ms_base, ms_basm, dy, ref_yield, late, n, expertup, expertlo):
    r"""V_EstV.UP and .LO of a milk yield: the region's base (corrected for the member state's step from BASM to
    BAST) growing by 1.25% (0.25%) a year plus 0.75% of the member state's gap to the reference yield and 0.75%
    (less 0.25%) for a late last ex-ante year; an expert's bound instead where there is one.

    basm: p_data(Rest, c, "COMI", "BASM"); ms_base, ms_basm: the member state's BAST, else BASM, and its BASM;
    dy: the member state's DCOW yield (BAST, else BASM: P_DATA_DCOW_COMI); ref_yield: p_refMlkYld; late:
    max(0, 2050 - Lst_exAnte) / (2050 - %lst_dgagri%); n: the years since DCOW's base; expertup, expertlo:
    P_Result(Rest, c, "COMI", "expertup" / "expertlo"). Returns (up, lo).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 139-186):

            V_EstV.UP(Rest,S_ColsEst,"COMI",exAnte) $ ( P_DATA(Rest,S_ColsEst,"COMI","nObs")
        *                                             No bounds setting if COCO data are present
        *                                             1) Should be ok even if deviating strongly from BASM.
        *                                             2) Otherwise nowcasting close to coco data will be inhibited.
                                                      $ (NOT P_Result(MS,S_ColsEst,"COMI",Exante,"p_data"))
                                                      $ P_DATA(MS,S_ColsEst,"COMI","BASM")
                                                      $ PACT_TO_Y(S_ColsEst,"COMI"))
              = [  P_DATA(Rest,S_ColsEst,"COMI","BASM")
        *          Correct for a possible jump in the MS data from BASM to BAST:
                 * ( P_DATA(MS,S_ColsEst,"COMI","BAST")
                   + P_DATA(MS,S_ColsEst,"COMI","BASM") $ (NOT P_DATA(MS,S_ColsEst,"COMI","BAST")))
                 /   P_DATA(MS,S_ColsEst,"COMI","BASM")
                 * (1 + (0.0125 + 0.0075 * (  p_refMlkYld
                                           -(P_DATA(MS,"DCOW","COMI","BAST")
                                            +P_DATA(MS,"DCOW","COMI","BASM") $ (NOT P_DATA(MS,"DCOW","COMI","BAST")))) / p_refMlkYld
        *               add 0.75% for short run projection horizons where wider bounds are less dangerous
                        +0.0075*(max(0,OrdT("2050")-OrdT("Lst_exAnte"))/ (OrdT("2050")-OrdT("%lst_dgagri%")) )))
                   **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(MS,"DCOW","COMI","BAST"))
                                   -OrdT("BAS")  $ (NOT P_DATA(MS,"DCOW","COMI","BAST")) ) ]
        *      Avoid interference with expert bounds here (but release_comi_yields.gms may operate):
               $ (NOT P_Result(Rest,S_ColsEst,"COMI",Exante,"expertup"))
             + P_Result(Rest,S_ColsEst,"COMI",Exante,"expertup")
               $ (    P_Result(Rest,S_ColsEst,"COMI",Exante,"expertup"))
                                   ;


            V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte) $ (P_DATA(Rest,S_ColsEst,"COMI","nObs")
        *pw unclear purpose of using FULL_MAP_RR for .lo but not for .up: $ (NOT SUM(FULL_MAP_RR(MS,Rest), P_Result(MS,S_ColsEst,"COMI",Exante,"p_data")))
                                                      $ (NOT P_Result(MS,S_ColsEst,"COMI",Exante,"p_data"))
                                                      $ P_DATA(MS,S_ColsEst,"COMI","BASM")
                                                      $ PACT_TO_Y(S_ColsEst,"COMI"))
              =  [  P_DATA(Rest,S_ColsEst,"COMI","BASM")
        *          Correct for a possible jump in the MS data from BASM to BAST:
                 * ( P_DATA(MS,S_ColsEst,"COMI","BAST")
                   + P_DATA(MS,S_ColsEst,"COMI","BASM") $ (NOT P_DATA(MS,S_ColsEst,"COMI","BAST")))
                 /   P_DATA(MS,S_ColsEst,"COMI","BASM")
                 * (1 + (0.0025 + 0.0075 * (  p_refMlkYld
                                          -(P_DATA(MS,"DCOW","COMI","BAST")
                                           +P_DATA(MS,"DCOW","COMI","BASM") $ (NOT P_DATA(MS,"DCOW","COMI","BAST")))) / p_refMlkYld
        *               deduct 0.25% for short run projection horizons where wider bounds are less dangerous
                        -0.0025*(max(0,OrdT("2050")-OrdT("Lst_exAnte"))/ (OrdT("2050")-OrdT("%lst_dgagri%")) )))
                    **(OrdT(Exante)-OrdT("BAST") $ (    P_DATA(MS,"DCOW","COMI","BAST"))
                                   -OrdT("BAS")  $ (NOT P_DATA(MS,"DCOW","COMI","BAST")) ) ]
        *      Avoid interference with expert bounds here (but release_comi_yields.gms may operate):
               $ (NOT P_Result(Rest,S_ColsEst,"COMI",Exante,"expertlo"))
             + P_Result(Rest,S_ColsEst,"COMI",Exante,"expertlo")
               $ (    P_Result(Rest,S_ColsEst,"COMI",Exante,"expertlo"))
                                   ;

    the member state's own bounds of l. 193-229 (SUM(MAP_RR(MS, Rest), 1) GT 1) apply only with NUTS 2 regions in Rest:
    not at the member state's level, and the regions' estimation has its own; %FixExogenFactGlobiom% is off (l. 232-247);
    the domain condition in the caller (estimate_bounds._comi)."""
    base = basm * ms_base / ms_basm
    gap = (ref_yield - dy) / ref_yield
    if expertup:
        up = expertup
    else:
        up = base * (1 + (0.0125 + 0.0075 * gap + 0.0075 * late)) ** n
    if expertlo:
        lo = expertlo
    else:
        lo = base * (1 + (0.0025 + 0.0075 * gap - 0.0025 * late)) ** n
    return up, lo


def V_EstV_COMI_corridor(lo, up, support, is_ms):
    r"""V_EstV.LO and .UP of a milk yield whose member-state support is the expert's: within at least 5% (the
    member state) or 10% (a region) of the support.

    lo, up: the bounds before; support: P_Result(Rest, c, "COMI", "Support"); is_ms: Rest is the member state.
    Returns (lo, up).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 252-268):

           v_estV.LO(Rest,S_ColsEst,"COMI",exAnte) $   (
                                                              SUM(MAP_RR(MS,Rest) $ (  P_Result(MS,S_ColsEst,"COMI",exAnte,"Expert")
                                                                                    EQ P_Result(MS,S_ColsEst,"COMI",exAnte,"Support")),1)
                                                          $ (  v_estV.LO(Rest,S_ColsEst,"COMI",exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,"COMI",exAnte))
                                                          $  P_Result(Rest,S_ColsEst,"COMI",exAnte,"Support")
                                                          $ p_data(Rest,S_ColsEst,"COMI","nObs") $ PACT_TO_Y(S_ColsEst,"COMI"))
           = MIN(v_estV.LO(Rest,S_ColsEst,"COMI",exAnte), (0.9 +.05 $ sameas(Rest,MS))*P_Result(Rest,S_ColsEst,"COMI",exAnte,"Support"));

           v_estV.UP(Rest,S_ColsEst,"COMI",exAnte)   $ (
                                                              SUM(MAP_RR(MS,Rest) $ (  P_Result(MS,S_ColsEst,"COMI",exAnte,"Expert")
                                                                                    EQ P_Result(MS,S_ColsEst,"COMI",exAnte,"Support")),1)
                                                          $ (  v_estV.LO(Rest,S_ColsEst,"COMI",exAnte)
                                                              NE v_estV.UP(Rest,S_ColsEst,"COMI",exAnte))
                                                          $  P_Result(Rest,S_ColsEst,"COMI",exAnte,"Support")
                                                          $ p_data(Rest,S_ColsEst,"COMI","nObs")  $ PACT_TO_Y(S_ColsEst,"COMI"))
           = MAX(v_estV.UP(Rest,S_ColsEst,"COMI",exAnte), (1.1 -.05 $ sameas(Rest,MS))*P_Result(Rest,S_ColsEst,"COMI",exAnte,"Support"));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    wid = 0.05 if is_ms else 0.10
    return min(lo, (1.0 - wid) * support), max(up, (1.0 + wid) * support)


def V_EstV_COMI_prev(lo, up, step3, is_ms, n):
    r"""V_EstV.LO and .UP of a milk yield from the third ex-ante year: at least the previous ex-ante year's Step3
    (the member state's growing by 0.25% a year), the upper bound at least 1.1 x the lower where not fixed.

    lo, up: the bounds before; step3: the previous year's P_Result(., "Step3"), None where that year is not after
    Lst_exPostT (or there is none); is_ms: Rest is the member state; n: the years since that year. Returns (lo, up),
    up None where it stays.

    l. 278: the previous year's yield grows by 0.25% a year for the member state only (1 + .0025 $ sameas(Rest,
    MS)); a region keeps it (found 12 November 2026: Ireland's regions in 2050).

    CAPRI's GAMS (captrd/comi_bounds.gms l. 273-287):

            V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte) $ (P_DATA(Rest,S_ColsEst,"COMI","nObs")
                                                      $ (ORDT(ExAnte) GT (ORDT("fst_exante")+2))
                                                      $ (V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte) gt 0)
                                                      $ PACT_TO_Y(S_ColsEst,"COMI"))
                      = max(sum(Before(exAnte,Years) $ (ordt(years) gt OrdT("Lst_exPostT")),P_Result(Rest,S_ColsEst,"COMI",years, "Step3")
                                                                                            *(1+.0025 $ sameas(Rest,MS))**(ordt(exante)-ordt(years))),
                            V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte) )
                  ;
            V_EstV.up(Rest,S_ColsEst,"COMI",exAnte) $ (P_DATA(Rest,S_ColsEst,"COMI","nObs")
                                                      $ (ORDT(ExAnte) GT (ORDT("fst_exante")+2))
                                                      $ (V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte) gt 0)
                                                      $ V_EstV.range(Rest,S_ColsEst,"COMI",exAnte)
                                                      $ PACT_TO_Y(S_ColsEst,"COMI"))
                      = max(V_EstV.up(Rest,S_ColsEst,"COMI",exAnte),V_EstV.lo(Rest,S_ColsEst,"COMI",exAnte)*1.1)
                  ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    growth = 1.0025 if is_ms else 1.0
    prev = step3 * growth ** n if step3 is not None else 0.0
    lo = max(prev, lo)
    return lo, (max(up, lo * 1.1) if lo != up else None)

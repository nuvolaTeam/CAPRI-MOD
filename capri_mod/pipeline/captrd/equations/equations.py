r"""CAPTRD's consistency equations of the member-state estimation m_trendMS (captrd/equations.gms, CAPRI star 3.0).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the equation style of
the supply and market refactors); this docstring keeps the block's overview and notation.

Each function returns the equation's residual, lhs - rhs (zero for =E=, at most zero for =L=, at least zero for
=G=), for one member state and ex-ante year; capri_mod/pipeline/captrd/estimate_ms.py (residuals) holds the domain
conditions, the loops over the sets and the senses, and calls these with the terms it gathers in the sets' order.
The terms are V_EstV's values or, for the NLP, CasADi symbols (estimate_nlp.solve): the functions are arithmetic
only, in the order of operations the port had, so both give the same residuals and the same expressions.

In this project's notation: V(c, w) is V_EstV(Rest, c, w, exAnteY) (zero where not given, as a GAMS level), n(c, w)
p_data(Rest, c, w, "nObs") nonzero, bas(c, w) p_data(Rest, c, w, "BAS"). CAPTRD's Rest and MSEst are the member state
alone in estimate_ms.gms l. 41-46, so CARD(Rest) = 1 and the EU000000 exclusions do not apply. SSQS_, the
objective, also serves the NUTS 2 estimation m_trendNT2 (estimate_nuts2.objective, CARD(Rest) > 1, with the
regions' weights).
"""
from __future__ import annotations


def AREAB_(levels, uaar):
    r"""The arable area: the crop activities' levels with data sum to UAAR.

    levels: V(m, LEVL) of the crops m with data (the caller's order); uaar: V(UAAR, LEVL).

    CAPRI's GAMS, AREAB_ (captrd/equations.gms l. 107-112):

           AREAB_(Rest,exAnteY) $ (  ((NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1))
                                   $ SUM(S_ColsEst(MCACT),1) ) ..
        *
              SUM(MCACT $ p_data(Rest,MCACT,"LEVL","nObs"), V_EstV(Rest,MCACT,"LEVL",exAnteY))
        *
              =E= V_EstV(Rest,"UAAR","LEVL",exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return sum(levels) - uaar


def LANDUSEB_(levels, arto):
    r"""The land use: the land types' levels with data sum to ARTO.

    levels: V(m, LEVL) of the land types of LandUseARTO with data; arto: V(ARTO, LEVL).

    CAPRI's GAMS, LANDUSEB_ (captrd/equations.gms l. 116-121):

           LANDUSEB_(Rest,exAnteY) $ (  ((NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1))
                                      $ SUM(S_ColsEst(LandUseARTO),1) ) ..
        *
              SUM(LandUseARTO $ p_data(Rest,LandUseARTO,"LEVL","nObs"), V_EstV(Rest,LandUseARTO,"LEVL",exAnteY))
        *
              =E= V_EstV(Rest,"ARTO","LEVL",exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return sum(levels) - arto


def STRA_(stra, terms):
    r"""The straw yield: a crop's straw follows its main outputs at the base year's ratio.

    stra: V(m, STRA); terms: (V(m, o), bas(m, STRA), bas(m, o)) of the crop's main outputs o with a base.

    CAPRI's GAMS, STRA_ (captrd/equations.gms l. 125-133):

           STRA_(Rest,MCACT,exAnteY) $ (  SUM(PACT_TO_Y(MCACT,O), p_data(Rest,MCACT,O,"BAS"))
                                        $ P_DATA(Rest,MCACT,"LEVL","nObs") $ (KeepStrawRelation eq 1)
                                        $ P_DATA(Rest,MCACT,"STRA","nObs") $ (KeepStrawRelation eq 1)
                                        $ PACT_TO_O(MCACT,"STRA") $ S_ColsEst(MCACT)
                                         ) ..
        *
              V_EstV(Rest,MCACT,"STRA",exAnteY) =E=
                SUM(PACT_TO_Y(MCACT,O) $ p_data(Rest,MCACT,O,"BAS"),
                   V_EstV(Rest,MCACT,O,exAnteY) * p_data(Rest,MCACT,"STRA","BAS")/p_data(Rest,MCACT,O,"BAS"));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return stra - sum(v * bs / bo for v, bs, bo in terms)


def OSET_(terms, rset_levels):
    r"""Obligatory set-aside: the arable crops' levels at the set-aside rate give the set-aside areas.

    terms: (V(a, LEVL), the rate SETR in %) of the arable activities with data, the rates P_Result's p_data of the
    year; rset_levels: V(r, LEVL) of the set-aside activities.

    CAPRI's GAMS, OSET_ (captrd/equations.gms l. 141-147):

           OSET_(rEst,exAnteY) $ SUM(MCACT $ (   S_ColsEst(MCACT)
                                               $ p_data(rEst,MCACT,"LEVL","nobs")
                                               $ p_data(rEst,MCact,"SETR",exAnteY)), 1) ..
        *
              SUM( arbAct $ p_data(rEst,arbAct,"LEVL","nObs"), V_EstV(rEst,arbAct,"LEVL",exAnteY)
                  * 0.01 * p_data(rEst,arbAct,"SETR",exAnteY)/(1.-0.01 * p_data(rEst,arbAct,"SETR",exAnteY)) )
              =E=  SUM(RSET,V_EstV(rEst,RSET,"LEVL",exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    lhs = 0.0
    for v, sr in terms:
        lhs += v * 0.01 * sr / (1.0 - 0.01 * sr)
    return lhs - sum(rset_levels)


def GROF_(products, grof):
    r"""Gross production: the yields per ha or head times the levels, in 1000 t.

    products: (V(a, w), V(a, LEVL)) of the activities a producing w with data; grof: V(GROF, w).

    CAPRI's GAMS, GROF_ (captrd/equations.gms l. 151-167):

           GROF_(Rest,S_RowsEst,exAnteY) $ (  p_data(Rest,"GROF",S_RowsEst,"nObs")
                                            $ (NOT GRPR(S_RowsEst))
                                            $ (NOT ROWS_LAB(S_RowsEst))
                                            $  SUM(PACT_TO_IO(MPACT,S_RowsEst),1)
        *
        *           --- take out equation if MSGROF_ or NT2GROF_ is operating, but there is only
        *  WB??         one sub-region with production <=> linear dependencies with MSGROF or NT2GROF equations
        *
                                            $ (   (CARD(Rest) eq 1)
                                               or (SUM(Rest1 $ p_data(Rest1,"GROF",S_RowsEst,"nObs"),1 ) ge 1) )
                                           ) ..
        *
              SUM(MPACT $ (PACT_TO_IO(MPACT,S_RowsEst) AND p_data(Rest,MPACT,S_RowsEst,"nObs")
                 and p_data(Rest,MPACT,"LEVL","nObs")),
                 V_EstV(Rest,MPACT,S_RowsEst,exAnteY) * V_EstV(Rest,MPACT,"LEVL",exAnteY)) * 0.001
        *
              =E= V_EstV(Rest,"GROF",S_RowsEst,exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return sum(x * lv for x, lv in products) * 0.001 - grof


def LABO_(labh, labn, labo):
    r"""Labour: the hired and the family labour sum to the total.

    V(GROF, LABH), V(GROF, LABN), V(GROF, LABO).

    CAPRI's GAMS, LABO_ (captrd/equations.gms l. 172-176):

           LABO_(Rest,exAnteY) $ (p_data(Rest,"GROF","LABO","nObs")) ..
        *
              V_EstV(Rest,"GROF","LABH",exAnteY) + V_EstV(Rest,"GROF","LABN",exAnteY)
        *
              =E= V_EstV(Rest,"GROF","LABO",exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return labh + labn - labo


def MAPR_(pairs, vinasse, mapr):
    r"""Secondary products: processing quantities times the processing yields (molasses less the ethanol beets'
    vinasse).

    pairs: (V(PRCM, w), V(PRCY, s)) of the primary products w of the secondary s; vinasse: (V(BIOF, SUGA), V(PRCY,
    SUGA), V(PRCY, MOLA)) for molasses where PRCY of SUGA has a positive lower bound, else None; mapr: V(MAPR, s).

    CAPRI's GAMS, MAPR_ (captrd/equations.gms l. 286-307):

           MAPR_(Rest,SECOD   ,exAnteY) $ p_data(Rest,"MAPR",SECOD   ,"nObs")..
        *
              V_EstV(Rest,"MAPR",SECOD,exAnteY)

              =E=
        *
              SUM(PRCD(SECOD,S_RowsEst) $ (p_data(Rest,"PRCM",S_RowsEst,"nObs") $ p_data(Rest,"PRCY",SECOD,"nObs")),
                 V_EstV(Rest,"PRCM",S_RowsEst,exAnteY) * V_EstV(Rest,"PRCY",SECOD,exAnteY))

        *      --  for those sugar beet qunatities that end up in Ethanol no molasses s produced but a by product vinasse.
        *          Vinasse is similar to molasses but contains only 10% of the energy of molasses
        *          => When expressed in molasse  equivalent, ethanol beets produce 90% less by-product than sugar beets
        *          => we correct molasses production downward by 90% of the MOLA quantiy that would have been produced if
        *             the ethanol beets had been ordinary sugar beets.
        *          ethanol beet quantity...
              - (  V_EstV(rest,"BIOF","SUGA",exAntey)
                  /V_EstV(Rest,"PRCY","SUGA",exAnteY)
        *          ... times processing coefficient that was implicitly included above...
                 * V_EstV(Rest,"PRCY","MOLA",exAnteY)
        *          ... requiring a 90% downscaling, as ethanol beets only give energy poor vinasses rather than energy rich molasses
                 * 0.9) $ (SAMEAS(SECOD,"MOLA") $ (V_EstV.lo(Rest,"PRCY","SUGA",exAnteY) gt eps))
              ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    rhs = sum(prcm * prcy for prcm, prcy in pairs)
    if vinasse is not None:
        biof, prcy_suga, prcy_mola = vinasse
        rhs -= biof / prcy_suga * prcy_mola * 0.9
    return mapr - rhs


def SugaQuot_(quota, uses, mapr):
    r"""The sugar quota: the sugar produced at most the quota plus its industrial, biofuel and loss uses.

    quota: P_Result's p_data of QUTS SUGA; uses: V(c, SUGA) of INDM, BIOF, LOSM with data; mapr: V(MAPR, SUGA).

    CAPRI's GAMS, SugaQuot_ (captrd/equations.gms l. 311-321):

           SugaQuot_(Rest,exAnteY) $ (  p_result(Rest,"QUTS","SUGA",exAnteY,"p_data")
                                      $ (NOT p_result(Rest,"MAPR","SUGA",exAnteY,"coco") ) )..

              V_EstV(Rest,"MAPR","SUGA",exAnteY)

              =L=   p_result(Rest,"QUTS","SUGA",exAnteY,"p_data")
        *           Industrial sugar of various forms is out of quota according to Reg 318/2006, Article 12
                  + V_EstV(Rest,"INDM","SUGA",exAnteY)  $ p_data(Rest,"INDM","SUGA","nObs")
                  + V_EstV(Rest,"BIOF","SUGA",exAnteY)  $ p_data(Rest,"BIOF","SUGA","nObs")
        *           Losses are assumed to be out of quota as well
                  + V_EstV(Rest,"LOSM","SUGA",exAnteY)  $ p_data(Rest,"LOSM","SUGA","nObs");

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    rhs = quota + sum(uses)
    return mapr - rhs


def SugaMinBiof_(mapr, biof):
    r"""The sugar produced at least the sugar to biofuels.

    V(MAPR, SUGA), V(BIOF, SUGA).

    CAPRI's GAMS, SugaMinBiof_ (captrd/equations.gms l. 326-331):

           SugaMinBiof_(Rest,exAnteY) $ (  p_data(Rest,"BIOF","SUGA","nObs")
                                      $ (NOT p_result(Rest,"MAPR","SUGA",exAnteY,"coco") ) )..

              V_EstV(Rest,"MAPR","SUGA",exAnteY)

              =G= V_EstV(Rest,"BIOF","SUGA",exAnteY) ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return mapr - biof


def MaizMinIndm_(indm, prci):
    r"""Maize's industrial use at least its processing input.

    V(INDM, MAIZ), V(PRCI, MAIZ).

    CAPRI's GAMS, MaizMinIndm_ (captrd/equations.gms l. 337-341):

              MaizMinIndm_(Rest,exAnteY) $ p_data(Rest,"PRCI","MAIZ","nObs")..

              V_EstV(Rest,"INDM","MAIZ",exAnteY)

              =G= V_EstV(Rest,"PRCI","MAIZ",exAnteY) ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return indm - prci


def MaprByFeed_(num_terms, den_terms, bas_mapr, mapr):
    r"""By-products of the residual imports: in proportion to their primary products' processing and uses, at the
    base year's ratio.

    num_terms: (V(HCOM, w), n(HCOM, w), V(PRCM, w), n(PRCM, w), V(INDM, w), n(INDM, w), V(BIOF, w), n(BIOF, w) and w
    is SUGA) per primary product w; den_terms: (bas(HCOM, w), bas(PRCM, w), bas(INDM, w), bas(BIOF, w), w is SUGA);
    bas_mapr: bas(MAPR, b); mapr: V(MAPR, b).

    CAPRI's GAMS, MaprByFeed_ (captrd/equations.gms l. 346-367):

           MaprByFeed_(Rest,RESIMP,exAnteY) $ p_data(Rest,"MAPR",RESIMP,"nObs") ..

              V_EstV(Rest,"MAPR",RESIMP,exAnteY)

              =E=
        *
        *        --- output in the base year
        *
              p_data(Rest,"MAPR",RESIMP,"BAS") *
        *
        *        --- multiplied with changes in producing processing
        *
              SUM(RESIMP_T_O(RESIMP,ROWS),
                   V_EstV(Rest,"HCOM",ROWS,exAnteY) $ p_data(Rest,"HCOM",ROWS,"nObs")
                 + V_EstV(Rest,"PRCM",ROWS,exAnteY) $ p_data(Rest,"PRCM",ROWS,"nObs")
                 + V_EstV(Rest,"INDM",ROWS,exAnteY) $ p_data(Rest,"INDM",ROWS,"nObs")
                 + V_EstV(Rest,"BIOF",ROWS,exAnteY) $ (p_data(Rest,"BIOF",ROWS,"nObs") and SAMEAS(ROWS,"SUGA")))
               /   SUM(RESIMP_T_O(RESIMP,ROWS),
                   p_data(Rest,"HCOM",ROWS,"BAS")
                 + p_data(Rest,"PRCM",ROWS,"BAS")
                 + p_data(Rest,"INDM",ROWS,"BAS")
                 + p_data(Rest,"BIOF",ROWS,"BAS") $ SAMEAS(ROWS,"SUGA"));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    num = sum(h * nh + p * np + i * ni + b * nb for h, nh, p, np, i, ni, b, nb in num_terms)
    den = sum(bh + bp + bi + bb * suga for bh, bp, bi, bb, suga in den_terms)
    return mapr - bas_mapr * num / den


def MLKCNT_(terms, prcm_milk, milk):
    r"""The milk contents: the processed milk's content equals the dairy products' content.

    terms: (V(MAPR, s), V(PRCM, s), n(PRCM, s), V(m, s)) of the dairy products s with data; prcm_milk: V(PRCM,
    MILK); milk: V(m, MILK) of the content m.

    CAPRI's GAMS, MLKCNT_ (captrd/equations.gms l. 373-381):

           MLKCNT_(Rest,MLKCNT,exAnteY) $ p_data(Rest,MLKCNT,"MILK","nObs") ..
        *
              V_EstV(Rest,"PRCM","MILK",exAnteY)  * V_EstV(Rest,MLKCNT,"MILK",exAnteY)

              =E=

              SUM(MLKSECO $ (p_data(Rest,"MAPR",MLKSECO,"nObs") and p_data(Rest,MLKCNT,MLKSECO,"nObs")),
                 (V_EstV(Rest,"MAPR",MLKSECO,exAnteY)-V_EstV(Rest,"PRCM",MLKSECO,exAnteY) $ p_data(Rest,"PRCM",MLKSECO,"nObs"))
                 * V_EstV(Rest,MLKCNT,MLKSECO,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    rhs = sum((mapr - prcm * np) * v for mapr, prcm, np, v in terms)
    return prcm_milk * milk - rhs


def EAAG_(eaag, uvag, grof):
    r"""The revenue per product: the unit value times the production, in million EUR.

    V(EAAG, w), V(UVAG, w), V(GROF, w).

    CAPRI's GAMS, EAAG_ (captrd/equations.gms l. 385-390):

           EAAG_(Rest,S_RowsEst,exAnteY) $ ( p_data(Rest,"EAAG",S_RowsEst,"nObs")
                                           $ p_data(Rest,"UVAG",S_RowsEst,"nObs")
                                           $ p_data(Rest,"GROF",S_RowsEst,"nObs"))..
        *
              V_EstV(Rest,"EAAG",S_RowsEst,exAnteY)
              =E= V_EstV(Rest,"UVAG",S_RowsEst,exAnteY) * V_EstV(Rest,"GROF",S_RowsEst,exAnteY) * 0.001;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return eaag - uvag * grof * 0.001


def REVE_(toou, terms):
    r"""The revenue per activity: its outputs times their unit values.

    toou: V(a, TOOU); terms: (V(a, w), V(UVAG, w)) of the activity's outputs with data.

    CAPRI's GAMS, REVE_ (captrd/equations.gms l. 394-402):

           REVE_(Rest,MPACT,exAnteY) $ ( (V_ESTV.UP(Rest,MPACT,"LEVL",exAnteY) GT 0)
                                       $ (V_ESTV.UP(Rest,MPACT,"LEVL",exAnteY) LT inf)
                                       $ p_data(Rest,MPACT,"TOOU","nObs")) ..
        *
              V_EstV(Rest,MPACT,"TOOU",exAnteY)
              =E= SUM(S_RowsEst $ (  PACT_TO_O(MPACT,S_RowsEst)
                                   $ p_data(Rest,MPACT,S_RowsEst,"nObs")
                                   $ p_data(Rest,"UVAG",S_RowsEst,"nObs")),
                 V_EstV(Rest,MPACT,S_RowsEst,exAnteY) * V_EstV(Rest,"UVAG",S_RowsEst,exAnteY)) * 0.001;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return toou - sum(x * u for x, u in terms) * 0.001


def UVAD_(uvad, uvag, cssp):
    r"""The consumer price: the producer price plus the consumer subsidy equivalent.

    V(UVAD, w), V(UVAG, w), V(CSSP, w).

    CAPRI's GAMS, UVAD_ (captrd/equations.gms l. 406-411):

           UVAD_(Rest,S_RowsEst,exAnteY)  $ (  p_data(Rest,"CSSP",S_RowsEst,"nObs")
                                             $ p_data(Rest,"UVAD",S_RowsEst,"nObs")
                                             $ p_data(Rest,"UVAG",S_RowsEst,"nObs")) ..
        *
              V_EstV(Rest,"UVAD",S_RowsEst,exAnteY)
              =E= V_EstV(Rest,"UVAG",S_RowsEst,exAnteY) + V_EstV(Rest,"CSSP",S_RowsEst,exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return uvad - uvag - cssp


def UVADfuel_(uvad, uvag, ctax):
    r"""The consumer price of fuels: the producer price plus the consumer tax.

    V(UVAD, w), V(UVAG, w), V(CTAX, w).

    CAPRI's GAMS, UVADfuel_ (captrd/equations.gms l. 415-420):

           UVADfuel_(Rest,S_RowsEst,exAnteY)  $ (  p_data(Rest,"CTAX",S_RowsEst,"nObs")
                                             $ p_data(Rest,"UVAD",S_RowsEst,"nObs")
                                             $ p_data(Rest,"UVAG",S_RowsEst,"nObs")) ..
        *
              V_EstV(Rest,"UVAD",S_RowsEst,exAnteY)
              =E= V_EstV(Rest,"UVAG",S_RowsEst,exAnteY) + V_EstV(Rest,"CTAX",S_RowsEst,exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return uvad - uvag - ctax


def EXPE_(expe, uvad, hcom, inha):
    r"""The consumer expenditure per product: the consumer price times the consumption per head.

    V(EXPE, w), V(UVAD, w), V(HCOM, w); inha: P_Result's p_data of INHA LEVL.

    CAPRI's GAMS, EXPE_ (captrd/equations.gms l. 425-432):

           EXPE_(Rest,S_RowsEst,exAnteY)  $ (  p_data(Rest,"EXPE",S_RowsEst,"nObs")
                                             $ p_data(Rest,"UVAD",S_RowsEst,"nObs")
                                             $ p_data(Rest,"HCOM",S_RowsEst,"nObs")
                                             $ (NOT SAMEAS(S_RowsEst,"LEVL")) ) ..
        *
              V_EstV(Rest,"EXPE",S_RowsEst,exAnteY)
              =E= V_EstV(Rest,"UVAD",S_RowsEst,exAnteY)
                * V_EstV(Rest,"HCOM",S_RowsEst,exAnteY)/p_result(Rest,"Inha","Levl",exAnteY,"p_data") ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return expe - uvad * hcom / inha


def EXPETOT_(expe_levl, expes):
    r"""The total consumer expenditure: the sum over the products.

    expe_levl: V(EXPE, LEVL); expes: V(EXPE, w) of the products (not the groups) with data.

    CAPRI's GAMS, EXPETOT_ (captrd/equations.gms l. 437-441):

           EXPETOT_(Rest,exAnteY)  $  p_data(Rest,"EXPE","LEVL","nObs") ..

              V_EstV(Rest,"EXPE","LEVL",exAnteY)
              =E= SUM( S_RowsEst $ ( (NOT (SAMEAS(S_RowsEst,"LEVL") or GRPR(S_RowsEst)))
                                    $ p_data(Rest,"Expe",S_RowsEst,"nObs")), V_EstV(Rest,"EXPE",S_RowsEst,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return expe_levl - sum(expes)


def FEED_(grof, fedm):
    r"""A feed aggregate's production: its products' feed use.

    grof: V(GROF, f); fedm: V(FEDM, w) of the products w of the feed f with data.

    CAPRI's GAMS, FEED_ (captrd/equations.gms l. 445-450):

           FEED_(Rest,Feed,exAnteY) $ (  SUM( FEED_TO_O(FEED,S_RowsEst), p_data(rest,"FEDM",S_RowsEst,"nobs"))
                                       $ p_data(Rest,"GROF",Feed,"nObs")) ..
        *

              V_EstV(Rest,"GROF",Feed,exAnteY) =E= SUM( FEED_TO_O(FEED,S_RowsEst) $ p_data(Rest,"FEDM",S_RowsEst,"nObs"),
              V_EstV(Rest,"FEDM",S_RowsEst,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return grof - sum(fedm)


def DDGS_(mapr_ddgs, terms):
    r"""DDGS from the ethanol feedstocks: their biofuel use times the by-product yield.

    mapr_ddgs: V(MAPR, DDGS); terms: (V(BIOF, o), V(PRCBY, o)) of the stocks o with data and a by-product yield.

    CAPRI's GAMS, DDGS_ (captrd/equations.gms l. 454-458):

           DDGS_(Rest,exAnteY) $ SUM(STOCK_TO_BY(OSECO,"DDGS") $ (p_data(Rest,"BIOF",OSECO,"nObs")*V_EstV.l(Rest,"PRCBY",OSECO,exAnteY)),1) ..
        *
             V_EstV(Rest,"MAPR","DDGS",exAnteY) =E= SUM(STOCK_TO_BY(OSECO,"DDGS") $ (p_data(Rest,"BIOF",OSECO,"nObs")
                *V_EstV.l(Rest,"PRCBY",OSECO,exAnteY)),
                V_EstV(Rest,"BIOF",OSECO,exAnteY)*V_EstV(Rest,"PRCBY",OSECO,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return mapr_ddgs - sum(biof * prcby for biof, prcby in terms)


def BIOF_(mapr, nagr, secg, terms):
    r"""Biofuel production: from the agricultural feedstocks, plus the non-agricultural and second-generation
    supply.

    V(MAPR, s), V(NAGR, s), V(SECG, s); terms: (V(BIOF, b), V(PRCB, b)) of the feedstocks with data.

    CAPRI's GAMS, BIOF_ (captrd/equations.gms l. 463-470):

           BIOF_(Rest,SECO_BIOF,exAnteY) $ SUM(STOCK_TO_FUEL(bioStock,SECO_BIOF)
                                               $ (p_data(Rest,"BIOF",bioStock,"nObs")*V_EstV.l(Rest,"PRCB",bioStock,exAnteY)),1) ..
        *
              V_EstV(Rest,"MAPR",SECO_BIOF,exAnteY) - V_EstV(Rest,"NAGR",SECO_BIOF,exAnteY)
              - V_EstV(Rest,"SECG",SECO_BIOF,exAnteY)
              =E=  SUM(STOCK_TO_FUEL(bioStock,SECO_BIOF)
                 $ (p_data(Rest,"BIOF",bioStock,"nObs")*p_data(Rest,"PRCB",bioStock,"nObs")),
                 (V_EstV(Rest,"BIOF",bioStock,exAnteY)*V_EstV(Rest,"PRCB",bioStock,exAnteY)));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return mapr - nagr - secg - sum(biof * prcb for biof, prcb in terms)


def REQS_(const, slope, outputs, eff, req, feeds):
    r"""An animal's requirement: the requirement function of its main output, times the feeding efficiency, met by
    the feeds' contents.

    const, slope: p_data's Const and Slope of (a, r); outputs: V(a, o) of the main outputs with data; eff: the
    feeding efficiency factor of the year; req: V(a, r); feeds: (V(a, f), the content BASM(r, f)) of the feeds with
    data, the member state's contents (MSEst is the member state).

    CAPRI's GAMS, REQS_ (captrd/equations.gms l. 514-535):

           REQS_(Rest,MAACT,ReqsT,exAnteY) $ (  (p_data(Rest,MAACT,ReqsT,"Const")  + p_data(Rest,MAACT,ReqsT,"Slope"))
                                              $ S_ColsEst(MAACT)
                                              $ (V_EstV.UP(Rest,MAACT,ReqsT,exAnteY) ne 0)
                                              $ p_data(Rest,MAACT,"LEVL","nObs")) ..
        *
        *         --- requirement as linear function of main output coefficient, assumming 0.2% t.p. in feeding efficiency
        *
              (p_data(Rest,MAACT,ReqsT,"Const")  + p_data(Rest,MAACT,ReqsT,"Slope")
                 * SUM(PACT_TO_Y(MAACT,O) $ p_data(Rest,MAACT,O,"nObs"), V_EstV(Rest,MAACT,O,exAnteY)))
                 *[ (1/p_globiomTightLink(Rest,MAACT,"FEED","%SelecScen%",exAnteY))
                            $ (    p_globiomTightLink(Rest,MAACT,"FEED","%SelecScen%",exAnteY))
                  + (0.998**(OrdT(exAnteY)-OrdT("2000")))
                            $ (NOT p_globiomTightLink(Rest,MAACT,"FEED","%SelecScen%",exAnteY))]

        *
                 * V_EstV(Rest,MAACT,ReqST,exAnteY)

        *
        *         ---- deliveries from feed intake
        *
              =E= SUM(Feed $ p_data(Rest,MAACT,Feed,"nObs"),
                 V_EstV(Rest,MAACT,Feed,exAnteY) * SUM(MAP_RR(MSEst,Rest),p_data(MSEst,ReqsT,Feed,"BASM")));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    yo = sum(outputs)
    lhs = (const + slope * yo) * eff * req
    rhs = sum(v * c for v, c in feeds)
    return lhs - rhs


def LU_(lu, terms, uaar):
    r"""The livestock density: the animals' livestock units per ha of UAAR.

    lu: V(LU, LEVL); terms: (V(a, LEVL), p_LUUnits(a)) of the animal activities with data; uaar: V(UAAR, LEVL).

    CAPRI's GAMS, LU_ (captrd/equations.gms l. 540-544):

           LU_(Rest,exAnteY) $ SUM(MAACT, p_data(Rest,MAACT,"LEVL","nObs")) ..
        *
              V_EstV(Rest,"LU","LEVL",exAnteY) =E=
              SUM(MAACT $ p_data(Rest,MAACT,"LEVL","nObs"), V_EstV(Rest,MAACT,"LEVL",exAnteY)
              * p_LUUnits(MAACT))/V_EstV(Rest,"UAAR","LEVL",exAnteY);

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return lu - sum(v * u for v, u in terms) / uaar


def OYANI_(grof, stcm, not_calf, inputs):
    r"""Young animals: their production is their use as inputs plus the stock change (not for the calves).

    grof: V(GROF, o); stcm: V(STCM, o); not_calf: o is not YCAM or YCAF; inputs: V(GROF, i) of the inputs i of o
    with data.

    CAPRI's GAMS, OYANI_ (captrd/equations.gms l. 548-555):

           OYANI_(Rest,OYANI,exAnteY) $ (  p_data(Rest,"GROF",OYANI,"nObs")
                                         $ ( (NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1) )) ..
        *
              V_EstV(Rest,"GROF",OYANI,exAnteY)
              - V_EstV(Rest,"STCM",OYANI,exAnteY) $ ( (NOT SAMEAS(OYANI,"YCAM")) and (NOT SAMEAS(OYANI,"YCAF")) )
        *
              =E=  SUM( IYANI $ (O_TO_YANI(OYANI,IYANI) $ p_data(Rest,"GROF",IYANI,"nObs")),
                 V_EstV(Rest,"GROF",IYANI,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return grof - stcm * not_calf - sum(inputs)


def SlgwFem_(slgw, inputs, meats):
    r"""The slaughter weight of the breeding activities' females: the meat over the young animals bought.

    slgw: V(b, SLGW); inputs: V(b, i) of the young-animal inputs; meats: V(b, m) of the meat outputs.

    CAPRI's GAMS, SlgwFem_ (captrd/equations.gms l. 561-565):

              SlgwFem_(Rest,breedAct,exAnteY)  $ p_data(Rest,breedAct,"SLGW","nObs")..

                V_EstV(Rest,breedAct,"SLGW",exAnteY) *  SUM(PACT_TO_I(breedAct,IYANI),V_EstV(Rest,breedAct,IYANI,exAnteY))

                   =E=  SUM(PACT_TO_O(breedAct,MEAT),V_ESTV(Rest,breedAct,MEAT,exAnteY)) *1000;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return slgw * sum(inputs) - sum(meats) * 1000


def FinalWgt_(meats, carcass_share, start_wgt, daily, g, days, edays):
    r"""The final weight: the carcass weight over its share equals the start weight plus the daily gain over the
    days fed.

    meats: V(c, m) of the meat outputs; carcass_share: p_carcassShare(c); start_wgt: p_startWgt(c); daily: V(c,
    DAILY); g: 1 for poultry, else 0.001; days: V(c, DAYS); edays: BASM's EDAYS of c.

    CAPRI's GAMS, FinalWgt_ (captrd/equations.gms l. 572-582):

           FinalWgt_(Rest,S_ColsEst,exAnteY) $ ( (V_ESTV.LO(Rest,S_ColsEst,"DAYS",exAnteY) NE V_ESTV.UP(Rest,S_ColsEst,"DAYS",exAnteY))
                                               $ SUM(PACT_TO_Y(S_ColsEst,MEAT),p_data(Rest,"GROF",MEAT,"nObs"))
                                               $ p_carcassShare(S_ColsEst))..
        *
                SUM(PACT_TO_Y(S_ColsEst,MEAT),V_ESTV(Rest,S_ColsEst,MEAT,exAnteY)) / p_carcassShare(S_ColsEst)

                    =E=   p_startWgt(S_ColsEst)
                        + V_ESTV(Rest,S_ColsEst,"DAILY",exAnteY)
                        * ( 1. $ P_T_ActAgg(S_ColsEst,"POUL") + 0.001 $ (NOT P_T_ActAgg(S_ColsEst,"POUL")))
                        * ( V_ESTV(Rest,S_ColsEst,"DAYS",exAnteY) -  p_data(Rest,S_ColsEst,"EDAYS","BASM"))
                        ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return sum(meats) / carcass_share - (start_wgt + daily * g * (days - edays))


def Dailyup_(daily, beef, carcass_share):
    r"""Bulls' daily gain at most 0.4 kg plus 0.0016 per kg of live weight.

    V(b, DAILY), V(b, BEEF), p_carcassShare(b).

    CAPRI's GAMS, Dailyup_ (captrd/equations.gms l. 587-593):

           Dailyup_(Rest,BULF,exAnteY) $  p_data(Rest,"GROF","BEEF","nObs") ..
        *
                    V_ESTV(Rest,BULF,"DAILY",exAnteY)/1000
        *
                    =L= .4 + V_ESTV(Rest,BULF,"BEEF",exAnteY) / p_carcassShare(BULF) * .0016

                        ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return daily / 1000 - (0.4 + beef / carcass_share * 0.0016)


def HERD_(herd, levl, days):
    r"""The herd: the activity level times the days per year.

    V(a, HERD), V(a, LEVL), V(a, DAYS).

    CAPRI's GAMS, HERD_ (captrd/equations.gms l. 599-604):

           HERD_(Rest,MAACT,exAnteY) $ ( (V_ESTV.LO(Rest,MAACT,"HERD",exAnteY) NE V_ESTV.UP(Rest,MAACT,"HERD",exAnteY))
                                       $ p_data(Rest,MAACT,"HERD","nObs")
                                       $ p_data(Rest,MAACT,"LEVL","nObs"))..
        *
                V_EstV(Rest,MAACT,"HERD",exAnteY) =E=
                                     V_EstV(Rest,MAACT,"LEVL",exAnteY) * V_EstV(Rest,MAACT,"DAYS",exAnteY) /365;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return herd - levl * days / 365


def SplitFix_(levl, his):
    r"""The split activities: the low variant's level equals its high variants'.

    levl: V(c, LEVL); his: V(h, LEVL) of the high variants.

    CAPRI's GAMS, SplitFix_ (captrd/equations.gms l. 609-613):

           SplitFix_(Rest,s_ColsEst,exAnteY) $ ( (V_ESTV.LO(Rest,S_ColsEst,"LEVL",exAnteY) NE V_ESTV.UP(Rest,S_ColsEst,"LEVL",exAnteY))
                                               $ p_data(Rest,s_ColsEst,"LEVL","nObs")
                                               $ SplitActsLo(s_COLSEst))..
        *
                V_EstV(Rest,s_ColsEst,"LEVL",exAnteY) =E= SUM(LO_TO_HI(s_COLSEst,SplitActs),V_EstV(Rest,SplitActs,"LEVL",exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return levl - sum(his)


def SEED_(grof, n_grof, uses):
    r"""Seed and on-farm losses keep 5% of production.

    grof: V(GROF, w); n_grof: n(GROF, w); uses: V(c, w) of SEDM, SEDF, LOSF with data.

    CAPRI's GAMS, SEED_ (captrd/equations.gms l. 618-630):

           SEED_(Rest,S_RowsEst,exAnteY) $ (  p_data(Rest,"GROF",S_RowsEst,"nObs")
                                            $ (    p_data(Rest,"SEDM",S_RowsEst,"nObs") or p_data(Rest,"SEDF",S_RowsEst,"nObs")
                                                or p_data(Rest,"LOSF",S_RowsEst,"nObs"))
                                            $ (NOT GRPR(S_RowsEst))
                                            $ ( (NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1) )) ..
        *
              V_EstV(Rest,"GROF",S_RowsEst,exAnteY)*0.95 $ p_data(Rest,"GROF",S_RowsEst,"nObs")

              =G=
        *
              +V_EstV(Rest,"SEDM",S_RowsEst,exAnteY)  $ p_data(Rest,"SEDM",S_RowsEst,"nObs")
              +V_EstV(Rest,"SEDF",S_RowsEst,exAnteY)  $ p_data(Rest,"SEDF",S_RowsEst,"nObs")
              +V_EstV(Rest,"LOSF",S_RowsEst,exAnteY)  $ (p_data(Rest,"LOSF",S_RowsEst,"nObs") );

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return grof * 0.95 * n_grof - sum(uses)


def PosUp_(v, qv, bas_cw, qb):
    r"""The seed and loss rates at least 80% of the base year's, less 0.1 (=G=).

    v: V(c, w); qv, qb: the quantity the rate refers to now and in the base year (GROF, or for LOSM the market
    supply: the caller's sum); bas_cw: bas(c, w).

    CAPRI's GAMS, PosUp_ (captrd/equations.gms l. 637-670):

           PosUp_(Rest,S_ColsEst,S_RowsEst,exAnteY) $ (    (   (    p_data(Rest,"GROF",S_RowsEst,"BAS")
                                                                $   (   SAMEAS(S_ColsEst,"SEDM")
                                                                     or SAMEAS(S_ColsEst,"SEDF")
                                                                     or (    SAMEAS(S_ColsEst,"LOSF")
        *pw                                                                  remove lower limit for subsistence cons (may decline quickly):
                                                                          $ (NOT SAMEAS(S_RowsEst,"COMI"))
                                                                          $ (NOT SAMEAS(S_RowsEst,"SGMI"))
        *pw                                                                  ... or LOSF.BEEF where we have booked the meat, to be destroyed, of mad cows:
                                                                          $ (NOT SAMEAS(S_RowsEst,"BEEF"))
                                                                        )) )
                                                            or (    ( p_data(Rest,"MAPR",S_RowsEst,"BAS")
                                                                     +p_data(Rest,"GROF",S_RowsEst,"BAS")
                                                                     +p_data(Rest,"IMPT",S_RowsEst,"BAS"))
                                                                $   SAMEAS(S_ColsEst,"LOSM")
                                                                $   (not exanteD(exanteY))                )  )
                                                       $   p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
                                                       $   (NOT GRPR(S_RowsEst))
                                                      ) ..
        *
              V_EstV(Rest,S_ColsEst,S_RowsEst,exAnteY)

              =G=
                 (  V_EstV(Rest,"GROF",S_RowsEst,exAnteY) $ (    SAMEAS(S_ColsEst,"SEDM") or SAMEAS(S_ColsEst,"SEDF")
                                                              or SAMEAS(S_ColsEst,"LOSF"))
                 + (   V_EstV(Rest,"GROF",S_RowsEst,exAnteY) $ p_data(Rest,"GROF",S_RowsEst,"nObs")
                 + V_EstV(Rest,"MAPR",S_RowsEst,exAnteY) $ ((NOT p_data(Rest,"GROF",S_RowsEst,"nObs")) $ p_data(Rest,"MAPR",S_RowsEst,"nObs"))
                 + V_EstV(Rest,"IMPT",S_RowsEst,exAnteY) $ p_data(Rest,"IMPT",S_RowsEst,"nObs")) $ SAMEAS(S_ColsEst,"LOSM"))

               * p_data(Rest,S_ColsEst,S_RowsEst,"BAS")/
                 (  p_data(Rest,"GROF",S_RowsEst,"BAS") $ (SAMEAS(S_ColsEst,"SEDM") or SAMEAS(S_ColsEst,"SEDF") or SAMEAS(S_ColsEst,"LOSF"))

                 + ( p_data(Rest,"GROF",S_RowsEst,"BAS") $ p_data(Rest,"GROF",S_RowsEst,"nObs")
                     +p_data(Rest,"MAPR",S_RowsEst,"BAS") $ ((NOT p_data(Rest,"GROF",S_RowsEst,"nObs")) $ p_data(Rest,"MAPR",S_RowsEst,"nObs"))
                     +p_data(Rest,"IMPT",S_RowsEst,"BAS") $ p_data(Rest,"IMPT",S_RowsEst,"nObs")) $  SAMEAS(S_ColsEst,"LOSM"))  * 0.8 - 0.1;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return v - (qv * bas_cw / qb * 0.8 + (-0.1))


def PosLo_(v, qv, bas_cw, qb):
    r"""The seed and loss rates at most 120% of the base year's, plus 0.1 (=L=).

    as PosUp_.

    CAPRI's GAMS, PosLo_ (captrd/equations.gms l. 672-710):

           PosLo_(Rest,S_ColsEst,S_RowsEst,exAnteY) $ (

                                     (  (     p_data(Rest,"GROF",S_RowsEst,"BAS")
                                         $   (    SAMEAS(S_ColsEst,"SEDM")
                                               or SAMEAS(S_ColsEst,"SEDF")
                                               or (    SAMEAS(S_ColsEst,"LOSF")
        *pw                                           remove upper limit for subsistence cons (may decline quickly):
                                                   $ (NOT SAMEAS(S_RowsEst,"COMI"))
                                                   $ (NOT SAMEAS(S_RowsEst,"SGMI"))
                                                   $ (NOT SAMEAS(S_RowsEst,"BEEF"))
                                                   )) )

                                     or ( ( p_data(Rest,"MAPR",S_RowsEst,"BAS") $ (NOT p_data(Rest,"GROF",S_RowsEst,"BAS"))
                                          + p_data(Rest,"GROF",S_RowsEst,"BAS")
                                          + p_data(Rest,"IMPT",S_RowsEst,"BAS"))
                                        $ SAMEAS(S_ColsEst,"LOSM")
                                        $ (not exanteD(exanteY)))
                                     )
                                  $  p_data(Rest,S_ColsEst,S_RowsEst,"nObs")
                                  $  (NOT GRPR(S_RowsEst))
                                             ) ..
        *

                V_EstV(Rest,S_ColsEst,S_RowsEst,exAnteY)

                      =L=

                  (  V_EstV(Rest,"GROF",S_RowsEst,exAnteY) $ (SAMEAS(S_ColsEst,"SEDM") or SAMEAS(S_ColsEst,"SEDF") or SAMEAS(S_ColsEst,"LOSF"))

                  + (  V_EstV(Rest,"GROF",S_RowsEst,exAnteY) $ p_data(Rest,"GROF",S_RowsEst,"nObs")
                     + V_EstV(Rest,"MAPR",S_RowsEst,exAnteY) $ ((NOT p_data(Rest,"GROF",S_RowsEst,"nObs")) and p_data(Rest,"MAPR",S_RowsEst,"nObs"))
                     + V_EstV(Rest,"IMPT",S_RowsEst,exAnteY) $ p_data(Rest,"IMPT",S_RowsEst,"nObs")) $ SAMEAS(S_ColsEst,"LOSM"))

               * p_data(Rest,S_ColsEst,S_RowsEst,"BAS")/
                  (  p_data(Rest,"GROF",S_RowsEst,"BAS") $ (SAMEAS(S_ColsEst,"SEDM") or SAMEAS(S_ColsEst,"SEDF") or SAMEAS(S_ColsEst,"LOSF"))

                  + ( p_data(Rest,"GROF",S_RowsEst,"BAS") $ p_data(Rest,"GROF",S_RowsEst,"nObs")
                     +p_data(Rest,"MAPR",S_RowsEst,"BAS") $ ((NOT p_data(Rest,"GROF",S_RowsEst,"nObs")) and p_data(Rest,"MAPR",S_RowsEst,"nObs"))
                     +p_data(Rest,"IMPT",S_RowsEst,"BAS") $  p_data(Rest,"IMPT",S_RowsEst,"nObs")) $ SAMEAS(S_ColsEst,"LOSM"))  * 1.2 + 0.1;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return v - (qv * bas_cw / qb * 1.2 + 0.1)


def MBAL_(grof, n_grof, mapr, n_mapr_only, impt, n_impt, uses):
    r"""The market balance: production (GROF, else MAPR) plus imports equal the uses.

    grof, mapr, impt: V(GROF, w), V(MAPR, w), V(IMPT, w) with their conditions (n_mapr_only: MAPR with data and GROF
    without); uses: V(c, w) of the uses with data.

    CAPRI's GAMS, MBAL_ (captrd/equations.gms l. 715-737):

           MBAL_(Rest,S_RowsEst,exAnteY) $ (  SUM(MrkBalE $ ((NOT SAMEAS(MrkBale,"GROF")) $ (NOT SAMEAS(MrkBale,"MAPR"))),
                                                             p_data(Rest,MrkBalE,S_RowsEst,"nObs"))
                                            $ (NOT GRPR(S_RowsEst)) $ (NOT ReqST(S_RowsEst))
                                            $ ( (NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1) )
                                            ) ..
        *
                V_EstV(Rest,"GROF",S_RowsEst,exAnteY) $ p_data(Rest,"GROF",S_RowsEst,"nObs")
               +V_EstV(Rest,"MAPR",S_RowsEst,exAnteY) $ ((NOT p_data(Rest,"GROF",S_RowsEst,"nObs")) and p_data(Rest,"MAPR",S_RowsEst,"nObs"))
               +V_EstV(Rest,"IMPT",S_RowsEst,exAnteY) $ p_data(Rest,"IMPT",S_RowsEst,"nObs")

                      =E=
        *
                V_EstV(Rest,"FEDM",S_RowsEst,exAnteY)  $ p_data(Rest,"FEDM",S_RowsEst,"nObs")
               +V_EstV(Rest,"SEDM",S_RowsEst,exAnteY)  $ p_data(Rest,"SEDM",S_RowsEst,"nObs")
               +V_EstV(Rest,"SEDF",S_RowsEst,exAnteY)  $ p_data(Rest,"SEDF",S_RowsEst,"nObs")
               +V_EstV(Rest,"INDM",S_RowsEst,exAnteY)  $ p_data(Rest,"INDM",S_RowsEst,"nObs")
               +V_EstV(Rest,"PRCM",S_RowsEst,exAnteY)  $ p_data(Rest,"PRCM",S_RowsEst,"nObs")
               +V_EstV(Rest,"BIOF",S_RowsEst,exAnteY)  $ p_data(Rest,"BIOF",S_RowsEst,"nObs")
               +V_EstV(Rest,"HCOM",S_RowsEst,exAnteY)  $ p_data(Rest,"HCOM",S_RowsEst,"nObs")
               +V_EstV(Rest,"LOSM",S_RowsEst,exAnteY)  $ p_data(Rest,"LOSM",S_RowsEst,"nObs")
               +V_EstV(Rest,"LOSF",S_RowsEst,exAnteY)  $ p_data(Rest,"LOSF",S_RowsEst,"nObs")
               +V_EstV(Rest,"EXPT",S_RowsEst,exAnteY)  $ p_data(Rest,"EXPT",S_RowsEst,"nObs")
               +V_EstV(Rest,"INTP",S_RowsEst,exAnteY)  $ p_data(Rest,"INTP",S_RowsEst,"nObs");

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return (grof * n_grof + mapr * n_mapr_only + impt * n_impt) - sum(uses)


def NUTBAL_(ince, terms):
    r"""The intake per head of a nutrient: the consumption per head times the contents.

    ince: V(k, INCE); terms: (V(INHA, w), p_NCNC_CONT(w, k)) of the products with data.

    CAPRI's GAMS, NUTBAL_ (captrd/equations.gms l. 741-746):

           NUTBAL_(Rest,NCNC,exAnteY) $ p_data(Rest,NCNC,"INCE","nObs")  ..
        *

               V_EstV(Rest,NCNC,"INCE",exAnteY) *365             =E=

                sum (S_RowsEst  $ p_data(Rest,"INHA",S_RowsEst,"nObs"), V_EstV(Rest,"INHA",S_RowsEst,exAnteY) * p_NCNC_CONT(S_RowsEst,NCNC) )  ;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return ince * 365 - sum(v * c for v, c in terms)


def HCOM_(hcom, losf, is_mlko, foodsh, inha_w, inha):
    r"""Human consumption: the consumption (with the losses of the milk products) at its food share equals the
    consumption per head times the population.

    V(HCOM, w), V(LOSF, w), w in MLKO, V(foodSh, w), V(INHA, w); inha: P_Result's p_data of INHA LEVL.

    CAPRI's GAMS, HCOM_ (captrd/equations.gms l. 751-756):

           HCOM_(Rest,S_RowsEst,exAnteY) $ (p_data(Rest,"HCOM",S_RowsEst,"nObs") $ p_data(Rest,"Inha",S_RowsEst,"nObs") $ (NOT SAMEAS(S_RowsEst,"LEVL"))) ..

        *         V_EstV(Rest,"HCOM",S_RowsEst,exAnteY) * p_data(Rest,"foodSh",S_RowsEst,"BAS")
                 (V_EstV(Rest,"HCOM",S_RowsEst,exAnteY) + V_EstV(Rest,"LOSF",S_RowsEst,exAnteY) $ mlkO(s_rowsEst))
                 * V_EstV(Rest,"foodSh",S_RowsEst,exAnteY)
                    =E= V_EstV(Rest,"Inha",S_RowsEst,exAnteY) * p_result(Rest,"Inha","Levl",exAnteY,"p_data") * 0.001;

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return (hcom + losf * is_mlko) * foodsh - inha_w * inha * 0.001


def DOMM_(domm, parts):
    r"""The domestic use: the sum of its positions.

    domm: V(DOMM, w); parts: V(d, w) of the positions DOMPOS with data.

    CAPRI's GAMS, DOMM_ (captrd/equations.gms l. 760-766):

           DOMM_(Rest,S_RowsEst,exAnteY) $ ( (   p_result(Rest,"DOMM",S_RowsEst,exAnteY,"Support")
                                              or p_data(Rest,"DOMM",S_RowsEst,"nObs")
                                              or SUM(DOMPOS $ (   p_result(Rest,DOMPOS,S_RowsEst,exAnteY,"Support")
                                                               or p_data(Rest,DomPos,S_RowsEst,"nObs") ),1))
                                           $ (NOT FUEL_ROWS(S_RowsEst))) ..

                 V_EstV(Rest,"DOMM",S_RowsEst,exAnteY) =E= SUM(DOMPOS $ p_data(Rest,DomPos,S_RowsEst,"nObs"), V_EstV(Rest,DOMPOS,S_RowsEst,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return domm - sum(parts)


def NTRD_(ntrd, expt, n_expt, impt, n_impt):
    r"""Net trade: exports less imports.

    V(NTRD, w), V(EXPT, w) with n(EXPT, w), V(IMPT, w) with n(IMPT, w).

    CAPRI's GAMS, NTRD_ (captrd/equations.gms l. 770-777):

           NTRD_(Rest,S_RowsEst,exAnteY) $ (  p_result(Rest,"NTRD",S_RowsEst,exAnteY,"Support")
                                            $ (    p_data(Rest,"EXPT",S_RowsEst,"nObs")
                                               or  p_data(Rest,"IMPT",S_RowsEst,"nObs")
                                               )) ..


                 V_EstV(Rest,"NTRD",S_RowsEst,exAnteY) =E=  V_EstV(Rest,"EXPT",S_RowsEst,exAnteY)  $ p_data(Rest,"EXPT",S_RowsEst,"nObs")
                                                           -V_EstV(Rest,"IMPT",S_RowsEst,exAnteY)  $ p_data(Rest,"IMPT",S_RowsEst,"nObs");

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return ntrd - expt * n_expt + impt * n_impt


def MBALGRP_(total, parts):
    r"""A group's market balance position: the sum of its products'.

    total: V(e, g); parts: V(e, w) of the group's products with data.

    CAPRI's GAMS, MBALGRP_ (captrd/equations.gms l. 781-786):

           MBALGRP_(Rest,MrkBaleE,GRPR,exAnteY) $ (  (SUM(Rows $ (ROWS_TO_G(ROWS,GRPR) and p_data(Rest,MrkBaleE,Rows,"nObs")), 1) GT 1)
                                                   $ p_data(Rest,MrkBaleE,GRPR,"nObs")
                                                   $ ( (NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1) )) ..
        *
                V_EstV(Rest,MrkBaleE,GRPR,exAnteY) =E= SUM(Rows $ (ROWS_TO_G(ROWS,GRPR) and p_data(Rest,MrkBaleE,Rows,"nObs")),
                                                                                                    V_EstV(rest,MrkBaleE,Rows,exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return total - sum(parts)


def GRPLVL_(total, parts):
    r"""A crop group's level: the sum of its crops'.

    total: V(g, LEVL); parts: V(m, LEVL) of the group's crops with data.

    CAPRI's GAMS, GRPLVL_ (captrd/equations.gms l. 790-795):

           GRPLVL_(Rest,GRPC,exAnteY) $ (  (SUM(CROPC_TO_G(MCACT,GRPC) $ p_data(Rest,MCACT,"LEVL","nObs"), 1) GT 1)
                                         $ p_data(Rest,GRPC,"LEVL","nObs")
                                         $ ( (NOT SAMEAS(rest,"EU000000")) OR (CARD(Rest) EQ 1) )) ..
        *
                V_EstV(Rest,GRPC,"LEVL",exAnteY) =E=
                 SUM(CROPC_TO_G(MCACT,GRPC) $ p_data(Rest,MCACT,"LEVL","nObs"), V_EstV(rest,MCACT,"LEVL",exAnteY));

    Departures from CAPRI: none; the domain condition and the sums' sets in the caller (estimate_ms.residuals)."""
    return total - sum(parts)


def SSQS_(terms):
    r"""The estimation's objective: the weighted squared deviations of the estimates from their supports, over their
    standard errors, times 1000, plus STCM of the young animals pulled to zero; over the same sum at 10% of the
    supports, plus 1.

    terms: in the sum's order, (v, support, wVarErr, g) for a deviation of V(c, w) = v from p_result(.., "Support"),
    g the region's weight or None for CARD(Rest) = 1 (estimate_ms.objective: the weight 1, so no factor), and (s, sg)
    for the pull of s = V(STCM, o) with sg = p_result(.., "GROF", o, .., "support"). A deviation's standard error is
    max(sqrt(wVarErr), p_weightStdErr x support) + 1e-5, p_weightStdErr = 0.005; the pull's scale max(0.05 x sg, 1e-5).

    CAPRI's GAMS, SSQS_ (captrd/equations.gms l. 801-875):

           SCALAR p_weightStdErr /0.005 /;

           SSQS_ ..
        *
              SSQ
        *
              =E= 10 $ TestFeasible
        *
              + (SUM( (rest,S_ColsEst,S_RowsEst,exAnteY)
                              $ ( (V_EstV.lo(rest,S_ColsEst,S_RowsEst,exAnteY) ne V_EstV.up(rest,S_ColsEst,S_RowsEst,exAnteY))
                                 $ p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"wVarErr")
                                 $ p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support")),
        *
                 SQR( (V_EstV(rest,S_ColsEst,S_RowsEst,exAnteY) - p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support"))

                 / ( MAX( SQRT( p_result(Rest,S_ColsEst,S_RowsEst,exAnteY,"wVarErr")),
                   p_weightStdErr * p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support")) + 1.E-5))

                 * (
        *
        *  --- weight for gross production: share of regional activity levels on total activity level
        *
              MAX(0.001,(              SUM(PACT_TO_IO(MPACT,S_RowsEst), p_data(rest,MPACT,"LEVL","BASM"))+1.E-5)
                           /SUM(rest1, SUM(PACT_TO_IO(MPACT,S_RowsEst), p_data(Rest1,MPACT,"LEVL","BASM"))+1.E-5))
               $ (  (NOT SUM(SAMEAS(S_ColsEst,MPACT),1)) $ (CARD(Rest) GT 1))
        *
        *  --- weight of deviations for activity, I/O-coefficients and other activity specific coefficients increases
        *  --- with weight of activity on aggregate
        *
              + MAX(0.001,(p_data(rest,S_ColsEst,"LEVL","BASM")+1.E-5)/SUM(rest1,(p_data(Rest1,S_ColsEst,"LEVL","BASM")+1.E-5)))
                      $ ( SUM(SAMEAS(S_ColsEst,MPACT),1)  $ (CARD(Rest) GT 1))

              + 1 $ (CARD(Rest) EQ 1)

              )) * 1000
        *
        *  --- pull stcm of oyani to zero
        *
              + SUM( (rest,oyani,exAnteY) $ (p_data(Rest,"STCM",OYANI,"nObs") $ exanteT(exAnteY)
                                            $ p_result(Rest,"GROF",OYANI,exAnteY,"support")),
                                 SQR( V_EstV(Rest,"STCM",OYANI,exAnteY)
                                    / MAX( .05* p_result(Rest,"GROF",OYANI,exAnteY,"support"),1.E-5))) *1000

              ) $ (Not TestFeasible)
        *
        *           --------- scaling of objective
        *

              / (SUM( (rest,S_ColsEst,S_RowsEst,exAnteY)
                             $ (  (V_EstV.lo(rest,S_ColsEst,S_RowsEst,exAnteY) ne V_EstV.up(rest,S_ColsEst,S_RowsEst,exAnteY))
                                $ p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"wVarErr")
                                $ p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support")),

                 SQR( (0.10*p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support"))

                         / ( MAX( SQRT( p_result(Rest,S_ColsEst,S_RowsEst,exAnteY,"wVarErr")),
                                     p_weightStdErr * p_result(rest,S_ColsEst,S_RowsEst,exAnteY,"Support")) + 1.E-5))
        *
                 * (
        *
        *  --- weight for gross production: share of regional activity levels on total activity level
                 MAX(0.001,(           SUM(PACT_TO_IO(MPACT,S_RowsEst), p_data(rest,MPACT,"LEVL","BASM"))+1.E-5)
                    /SUM(rest1, SUM(PACT_TO_IO(MPACT,S_RowsEst), p_data(Rest1,MPACT,"LEVL","BASM"))+1.E-5))
        *
                    $ ( (NOT SUM(SAMEAS(S_ColsEst,MPACT),1)) $ (CARD(Rest) GT 1))
        *
        *  --- weight of deviations for I/O-coefficients and other activity specific coefficients increases
        *  --- with crop share/stocking density, to avoid larger corrections for more important activities
        *
                 + MAX(0.001,(p_data(rest,S_ColsEst,"LEVL","BASM")+1.E-5)/SUM(rest1,(p_data(Rest1,S_ColsEst,"LEVL","BASM")+1.E-5)))
                         $ ( SUM(SAMEAS(S_ColsEst,MPACT),1)  $ (CARD(Rest) GT 1))

                 + 1 $ (CARD(Rest) EQ 1)

                 )) +1);

    Departures from CAPRI: the TestFeasible branch (10 $ TestFeasible, the sums $ (NOT TestFeasible)) is not ported
    (CAPTRD-MOD has no TestFeasible mode). The domain conditions (lo ne up, wVarErr and Support nonzero;
    nObs, exanteT and GROF's support for the pull), the sums over the regions and the weights g (PACT_TO_IO's
    activities or the column's own LEVL BASM share, at least 0.001) in the callers (estimate_ms.objective,
    estimate_nuts2.objective). The terms may be a generator: each is added as it comes, so V's symbols are taken in
    the callers' order."""
    num, den = 0.0, 1.0
    for t in terms:
        if len(t) == 2:
            s, sg = t
            num = num + (s / max(0.05 * sg, 1.0e-5)) ** 2 * 1000.0
            continue
        v, sv, wv, g = t
        sig = max(wv ** 0.5, 0.005 * sv) + 1.0e-5
        if g is None:
            num = num + ((v - sv) / sig) ** 2 * 1000.0
            den += (0.10 * sv / sig) ** 2
        else:
            num = num + ((v - sv) / sig) ** 2 * g * 1000.0
            den += (0.10 * sv / sig) ** 2 * g
    return num / den

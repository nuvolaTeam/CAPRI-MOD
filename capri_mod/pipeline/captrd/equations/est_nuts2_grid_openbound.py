r"""CAPTRD's bound statements of captrd/est_Nuts2_grid_openbound.gms (CAPRI star 3.0): the bounds the NUTS 2 estimation opens after an infeasible solve, as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the bounded symbol: V_EstV.LO / .UP / .FX / .L). The functions take the numbers the statement reads
and return the bound; capri_mod/pipeline/captrd/estimate_nuts2.py (_open_bounds) holds the
domain conditions, the loops over the regions and the sets and the order of the statements, and calls them. A bound
"before" is the one an earlier statement set (-inf / +inf where none did); the arithmetic is the port's, in its order of
operations, so the bounds are unchanged.
"""
from __future__ import annotations

from capri_mod.pipeline.captrd.equations.estimate_nuts2 import _grof_sums


def V_EstV_fx_FEED(support):
    r"""V_EstV.FX of a feed coefficient the member state's feed balance blocks, after 60 tries: its support.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 40-43):

             v_estV.FX(Rest,mPact,Feed,exAnte) $ ( (ABS(SUM(RaggEst,%FEEDI%.M(RaggEst,mPact,FEED,exAnte))) gt eps)
                                                 $ p_data(Rest,mPact,FEED,"nObs")
                                                 $ (nRepeatedSolves(%REGIOND%) > 60))
                  = P_Result(Rest,mPact,Feed,exAnte,"Support");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return support


def V_EstV_up_FEED_fixed(lo):
    r"""V_EstV.UP of a fixed feed coefficient the feed balance blocks: opened to max(1.5 x, + 1).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 50-54):

             v_estV.UP(Rest,mPact,Feed,exAnte) $ ( (ABS(SUM(RaggEst,%FEEDI%.M(RaggEst,mPact,FEED,exAnte))) gt eps)
                                                 $ (v_estV.LO(Rest,mPact,Feed,exAnte) eq v_estV.UP(Rest,mPact,Feed,exAnte))
                                                 $ p_data(Rest,mPact,FEED,"nObs")
                                                 )
                 = MAX(v_estV.LO(Rest,mPact,Feed,exAnte) * 1.5,v_estV.LO(Rest,mPact,Feed,exAnte)+1.0);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(lo * 1.5, lo + 1.0)


def V_EstV_up_coef(up):
    r"""V_EstV.UP of a coefficient or requirement at its upper bound with a multiplier: + max(0.1, 25%).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 58-79):

             v_estV.UP(Rest,mPact,S_RowsEst,exAnte)      $ (
        *
        *          --- and the variable is at its upper bounds, or no iteration (pre-triangular error, variable may not have been moved)
        *
                                                         (  (v_estV.UP(Rest,mPact,S_RowsEst,exAnte) EQ v_estV.L(Rest,mPact,S_RowsEst,exAnte))

        *          --- or the requirement equation is binding, and we deal with a requirement
                                                          or SUM(REQST $ SAMEAS(REQST,S_RowsEst), ABS(REQS_.M(Rest,mPact,REQST,exAnte))))
        *
        *          --- and the solver has attached a marginal value (i.e.the bound contributes to the infeasibilities ..)
        *
                                                         $ ((ABS(v_estV.M(Rest,mPact,S_RowsEst,exAnte)) GT EPS) or (%MODELTRD%.iterusd EQ 0))
        *
        *          --- an input or output coefficient or a animal requirement with observations in the base
        *
                                                         $ (PACT_TO_IO(mPact,S_RowsEst) or ReqST(S_RowsEst))
        *
                                                         $ p_data(Rest,mPact,S_RowsEst,"nObs")
        *
                                                            )

                   = v_estV.UP(Rest,mPact,S_RowsEst,exAnte) + MAX(0.1,0.25*ABS(v_estV.UP(Rest,mPact,S_RowsEst,exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return up + max(0.1, 0.25 * abs(up))


def V_EstV_lo_coef(lo, basm, req, yld, feed):
    r"""V_EstV.LO of a coefficient or requirement at its lower bound with a multiplier: - max(0.1, 25% of it; 5%
    for a yield, 100% for a feed), at least zero; - max(0.1, 25%) for a negative base (not a requirement).

    lo: the bound before; basm: p_data(Rest, a, w, "BASM"); req, yld, feed: w is a requirement (REQST), a yield
    (PACT_TO_Y), a feed.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 81-113):

             v_estV.LO(Rest,mPact,S_RowsEst,exAnte)      $ (

        *
        *          --- prevent drops in yields during the first 30 trials for main output coefficients and for activities where the yields
        *              are not supposed to decrease
                                                         ( (nRepeatedSolves(%REGIOND%) > 30) or (NOT PACT_TO_Y(mPact,S_RowsEst))
                                                              or (NOT noYieldDrop(mPact)) or SAMEAS(S_RowsEst,"COMI"))
        *
        *          --- and the variable is at its lower bounds, or no iteration (pre-triangular error, variable may not have been moved)
        *
                                                        $  (  (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) EQ v_estV.L(Rest,mPact,S_RowsEst,exAnte))

        *          --- or the requirement equation is binding, and we deal with a requirement
                                                          or SUM(REQST $ SAMEAS(REQST,S_RowsEst), ABS(REQS_.M(Rest,mPact,REQST,exAnte))))
        *
        *          --- and the solver has attached a marginal value (i.e. the bound contributes to the infeasibilities ..)
        *
                                                         $ ((ABS(v_estV.M(Rest,mPact,S_RowsEst,exAnte)) GT EPS) or (%MODELTRD%.iterusd EQ 0))

        *
        *          --- an input or output coefficient or a animal requirement with observations in the base
        *
                                                         $(PACT_TO_IO(mPact,S_RowsEst) or ReqST(S_RowsEst))
        *
                                                         $ p_data(Rest,mPact,S_RowsEst,"nObs")
                                                          )

                   = MAX(0,v_estV.LO(Rest,mPact,S_RowsEst,exAnte) - MAX(0.1,(0.25-0.20 $ PACT_TO_Y(mPact,S_RowsEst)
                                                                                 +0.75 $ SUM(SAMEAS(FEED,S_RowsEst),1)  ) * ABS(v_estV.LO(Rest,mPact,S_RowsEst,exAnte))))
                             $ ( (p_data(Rest,mPact,S_RowsEst,"BASM") GE 0) or REQST(S_RowsEst))

                        +  (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) - MAX(0.1,0.25*ABS(v_estV.LO(Rest,mPact,S_RowsEst,exAnte))))
                             $ ( (p_data(Rest,mPact,S_RowsEst,"BASM") LT 0) and (NOT REQST(S_RowsEst)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    if basm >= 0 or req:
        share = 0.25 - (0.20 if yld else 0.0) + (0.75 if feed else 0.0)
        return max(0.0, lo - max(0.1, share * abs(lo)))
    return lo - max(0.1, 0.25 * abs(lo))


def V_EstV_REQST(lo, up):
    r"""V_EstV.LO and .UP of a requirement below 25 tries: within [min(0.1, up), 10]. Returns (lo, up).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 118-124):

             v_estV.LO(Rest,mPact,REQST,exAnte) $ (p_data(Rest,mPact,REQST,"nObs") $ (nRepeatedSolves(%REGIOND%) < 25))
                = Min(10,Max(MIN(0.1,v_estV.UP(Rest,mPact,REQST,exAnte)),v_estV.LO(Rest,mPact,REQST,exAnte)));
        *
        *    --- during the first 25 trials, requirement corrections cannot exceed factor 10
        *
             v_estV.UP(Rest,mPact,REQST,exAnte) $ (p_data(Rest,mPact,REQST,"nObs") $ (nRepeatedSolves(%REGIOND%) < 25))
                = MIN(10,v_estV.UP(Rest,mPact,REQST,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return min(10.0, max(min(0.1, up), lo)), min(10.0, up)


def V_EstV_up_LEVL_open(up):
    r"""V_EstV.UP of a level at its upper bound with a multiplier after 10 tries: x 1.25, at least + 0.1.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 132-137):

             v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte)      $ ( (ABS(v_estV.M(Rest,S_ColsEst,"LEVL",exAnte)) GT EPS) and (nRepeatedSolves(%REGIOND%) > 10)
                                                               $   (    (v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte) EQ v_estV.L(Rest,S_ColsEst,"LEVL",exAnte))
                                                                      or (%MODELTRD%.iterusd EQ 0))
                                                               $ p_data(Rest,S_ColsEst,"LEVL","nObs")
                                                                      )
                   = MAX(v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte)*1.25,v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte)+0.1);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(up * 1.25, up + 0.1)


def V_EstV_lo_LEVL_open(lo, uaar):
    r"""V_EstV.LO of a level at its lower bound with a multiplier after 10 tries (UAAR after 20): x 0.75 (UAAR x
    0.99), at least - 0.1 below, the floor 1e-5 where the bound was at least that.

    lo: the bound before; uaar: the column is UAAR.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 144-151):

             v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)      $ ((ABS(v_estV.M(Rest,S_ColsEst,"LEVL",exAnte)) GT EPS) and (nRepeatedSolves(%REGIOND%) > 10)
                                                           $  ( (NOT SAMEAS(S_ColsEst,"UAAR")) or (nRepeatedSolves(%REGIOND%) > 20))
                                                           $  (    (v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) EQ v_estV.L(Rest,S_ColsEst,"LEVL",exAnte))
                                                                 or (%MODELTRD%.iterusd EQ 0))
                                                           $ p_data(Rest,S_ColsEst,"LEVL","nObs"))

                   = MAX(1.E-5 $ (v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) ge 1.E-5),
                          MIN(v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)*(0.75 + 0.24 $ SAMEAS(S_ColsEst,"UAAR")),v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)-0.1));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    fac = 0.99 if uaar else 0.75
    return max(1.0e-5 if lo >= 1.0e-5 else 0.0, min(lo * fac, lo - 0.1))


def V_EstV_lo_LEVL_floor(lo, up):
    r"""V_EstV.LO of a level: the floor 1e-5 where the bound was at least that, at most the upper bound.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 153-156):

             v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)  $ p_data(Rest,S_ColsEst,"LEVL","nObs")
                   = MIN(v_estV.UP(Rest,S_ColsEst,"LEVL",exAnte),
                        MAX(1.E-5 $ (v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) ge 1.E-5),
                            v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return min(up, max(1.0e-5 if lo >= 1.0e-5 else 0.0, lo))


def V_EstV_lo_LEVL_ms(lo, level_ms, n_regions):
    r"""V_EstV.LO of a region's level where the member state's level is below the regions' lower bounds: at most
    80% of its average over the regions.

    lo: the bound before; level_ms: the member state's level; n_regions: CARD(Rest).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 160-165):

             v_estV.LO(Rest,S_ColsEst,"LEVL",exante) $ ( ( sum(RaggEst, v_estV.l(RaggEst,S_colsEst,"LEVL",exAnte))
                                                            lt sum(Rest1 $ v_estV.LO(Rest1,S_ColsEst,"LEVL",exante),
                                                                           v_estV.LO(Rest1,S_ColsEst,"LEVL",exante)))
                                                        $ p_data(Rest,S_ColsEst,"LEVL","nObs"))
               = Min(v_estV.LO(Rest,S_ColsEst,"LEVL",exante),
                    sum(RaggEst, v_estV.l(RaggEst,S_colsEst,"LEVL",exAnte)) / card(Rest) * 0.8);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return min(lo, level_ms / n_regions * 0.8)


def V_EstV_up_LEVL_ms(up, level_ms, n_regions):
    r"""V_EstV.UP of a region's level where the member state's level is above the regions' upper bounds: at least
    120% of its average over the regions.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 169-174):

             v_estV.UP(Rest,S_ColsEst,"LEVL",exante) $ (( sum(RaggEst, v_estV.l(RaggEst,S_colsEst,"LEVL",exAnte))
                                                            gt sum(Rest1 $ v_estV.UP(Rest1,S_ColsEst,"LEVL",exante),
                                                                           v_estV.UP(Rest1,S_ColsEst,"LEVL",exante)))
                                                        $ p_data(Rest,S_ColsEst,"LEVL","nObs"))
               = Max(v_estV.UP(Rest,S_ColsEst,"LEVL",exante),
                    sum(RaggEst, v_estV.l(RaggEst,S_colsEst,"LEVL",exAnte)) / card(Rest) * 1.2);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(up, level_ms / n_regions * 1.2)


def V_EstV_lo_LEVL_zero():
    r"""V_EstV.LO of a level at the floor 1e-5 after 20 tries: zero.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 178-181):

             v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte)  $ ( (v_estV.LO(Rest,S_ColsEst,"LEVL",exAnte) eq 1.E-5)
                                                          $  (nRepeatedSolves(%REGIOND%) > 20)
                                                          $ p_data(Rest,S_ColsEst,"LEVL","nObs")
                                                          ) = 0 ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return 0.0


def V_EstV_up_GROF_open(up):
    r"""V_EstV.UP of a production at its upper bound with a multiplier: x 2, at least + 0.1.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 186-192):

             v_estV.UP(Rest,"GROF",S_RowsEst,exAnte)      $ ( (ABS(v_estV.M(Rest,"GROF",S_RowsEst,exAnte)) GT EPS)
                                                          $   (   (v_estV.UP(Rest,"GROF",S_RowsEst,exAnte) EQ v_estV.L(Rest,"GROF",S_RowsEst,exAnte))
                                                             or (%MODELTRD%.iterusd EQ 0)
                                                             )
                                                          $ p_data(Rest,"GROF",s_RowsEst,"nObs")
                                                             )
                   = MAX(v_estV.UP(Rest,"GROF",S_RowsEst,exAnte)*2.0,v_estV.UP(Rest,"GROF",S_RowsEst,exAnte)+0.1);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(up * 2.0, up + 0.1)


def V_EstV_lo_GROF_open(lo):
    r"""V_EstV.LO of a production at its lower bound with a multiplier: x 0.5, at least - 0.1 below, not below
    zero.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 194-199):

             v_estV.LO(Rest,"GROF",S_RowsEst,exAnte)      $ ((ABS(v_estV.M(Rest,"GROF",S_RowsEst,exAnte)) GT EPS)
                                                       $   (    (v_estV.LO(Rest,"GROF",S_RowsEst,exAnte) EQ v_estV.L(Rest,"GROF",S_RowsEst,exAnte))
                                                             or (%MODELTRD%.iterusd EQ 0))
                                                       $ p_data(Rest,"GROF",s_RowsEst,"nObs")
                                                             )
                   = MAX(0,MIN(v_estV.LO(Rest,"GROF",S_RowsEst,exAnte)*0.5,v_estV.LO(Rest,"GROF",S_RowsEst,exAnte)-0.1));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(0.0, min(lo * 0.5, lo - 0.1))


def V_EstV_GROF_range(lo, up, terms):
    r"""V_EstV.LO and .UP of a production without a multiplier: at least the range its activities' levels' and
    coefficients' bounds give (as estimate_nuts2.gms l. 234-253).

    lo, up: the bounds before; terms: as estimate_nuts2.V_EstV_GROF. Returns (lo, up).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 204-237):

             v_estV.LO(Rest,"GROF",S_RowsEst,exante) $  ( (NOT (ABS(v_estV.M(Rest,"GROF",S_RowsEst,exAnte)) GT EPS))
                       $ SUM(mPact $ (
                                     p_data(Rest,mPact,S_RowsEst,"nObs")
                                   $ p_data(Rest,mPact,"LEVL","nObs")
                                   $ PACT_TO_IO(mPact,S_RowsEst)),1)
                        $ p_data(Rest,"GROF",S_RowsEst,"nObs"))
                   = MIN(v_estV.LO(Rest,"GROF",S_RowsEst,exante),
                       SUM(mPact $ ( p_data(Rest,mPact,S_RowsEst,"nObs") $ p_data(Rest,mPact,"LEVL","nObs") $ PACT_TO_IO(mPact,S_RowsEst)),
                                          (   MIN(v_estV.LO(Rest,mPact,"LEVL",exAnte),v_estV.UP(Rest,mPact,"LEVL",exAnte))
                                                $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) GT 0)
                                            + MAX(v_estV.LO(Rest,mPact,"LEVL",exAnte),v_estV.UP(Rest,mPact,"LEVL",exAnte))
                                                $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) LT 0))
                                              * v_estV.LO(Rest,mPact,S_RowsEst,exAnte)
                                              * (   0.99 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) GT 0)
                                                  + 1.01 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) LT 0)))/1000);

             v_estV.UP(Rest,"GROF",S_RowsEst,exante) $ ( (NOT (ABS(v_estV.M(Rest,"GROF",S_RowsEst,exAnte)) GT EPS))
                     $ SUM(mPact $ ( p_data(Rest,mPact,S_RowsEst,"nObs")
                                 $ p_data(Rest,mPact,"LEVL","nObs")
                                 $ PACT_TO_IO(mPact,S_RowsEst)),1)
                        $ p_data(Rest,"GROF",S_RowsEst,"nObs"))

                   = MAX(v_estV.UP(Rest,"GROF",S_RowsEst,exante),
                          SUM(mPact $ (  p_data(Rest,mPact,S_RowsEst,"nObs")
                                       $ p_data(Rest,mPact,"LEVL","nObs")
                                       $ PACT_TO_IO(mPact,S_RowsEst)),

                                          (   MAX(v_estV.LO(Rest,mPact,"LEVL",exAnte),v_estV.UP(Rest,mPact,"LEVL",exAnte))
                                                 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) GT 0)
                                            + MIN(v_estV.LO(Rest,mPact,"LEVL",exAnte),v_estV.UP(Rest,mPact,"LEVL",exAnte))
                                                 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) LT 0))
                                              * v_estV.UP(Rest,mPact,S_RowsEst,exAnte)
                                              * (   0.99 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) LT 0)
                                                  + 1.01 $ (v_estV.LO(Rest,mPact,S_RowsEst,exAnte) GT 0)))/1000 +1.);

    Departures from CAPRI: the port's x 0.001 for CAPRI's / 1000 (estimate_nuts2.V_EstV_GROF); the domain condition and the activities in the
    caller (estimate_nuts2._open_bounds)."""
    lsum, usum = _grof_sums(terms)
    return min(lo, lsum * 0.001), max(up, usum * 0.001 + 1.0)


def V_EstV_up_GROF_fodder(up, ups):
    r"""V_EstV.UP of a fodder's production with data: at least the summed upper bounds of its linked fodder.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 243-247):

             v_estV.UP(Rest,"GROF",FODDI,exAnte) $ p_data(Rest,"GROF",FODDI,"nObs")
                  = MAX(v_estV.UP(Rest,"GROF",FODDI,exAnte),SUM(feed_to_O(FODDI,FODDO), v_estV.UP(Rest,"GROF",FODDO,exAnte)));

             v_estV.UP(Rest,"GROF",FODDO,exAnte) $ p_data(Rest,"GROF",FODDO,"nObs")
                  = MAX(v_estV.UP(Rest,"GROF",FODDO,exAnte),SUM(feed_to_O(FODDI,FODDO), v_estV.UP(Rest,"GROF",FODDI,exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return max(up, sum(ups))


def V_EstV_lo_GROF_fodder(lo, los):
    r"""V_EstV.LO of a fodder's production with data: at most the summed lower bounds of its linked fodder.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 249-253):

             v_estV.LO(Rest,"GROF",FODDI,exAnte) $ p_data(Rest,"GROF",FODDI,"nObs")
               = MIN(v_estV.LO(Rest,"GROF",FODDI,exAnte),SUM(feed_to_O(FODDI,FODDO), v_estV.LO(Rest,"GROF",FODDO,exAnte)));

             v_estV.LO(Rest,"GROF",FODDO,exAnte) $ p_data(Rest,"GROF",FODDO,"nObs")
               = MIN(v_estV.LO(Rest,"GROF",FODDO,exAnte),SUM(feed_to_O(FODDI,FODDO), v_estV.LO(Rest,"GROF",FODDI,exAnte)));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return min(lo, sum(los))


def V_EstV_fx_young_animals():
    r"""V_EstV.FX of the fixed young-animal coefficients: 1000 a head.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 255-257):

             v_estV.FX(Rest,FIX_YAI,IYANI,Exante) $ (PACT_TO_I(FIX_YAI,IYANI) $ p_data(Rest,FIX_YAI,"LEVL","nObs")) = 1000;

             v_estV.FX(Rest,FIX_YAO,OYANI,Exante) $ (PACT_TO_O(FIX_YAO,OYANI) $ p_data(Rest,FIX_YAO,"LEVL","nObs")) = 1000;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return 1000.0


def V_EstV_fx_no_ms_level():
    r"""V_EstV.FX of an activity's positions where the member state's result has no level: zero.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 260-261):

             v_estV.FX(Rest,mPact,S_RowsEst,exAnte) $ ( (NOT SUM(RaggEst, P_Result(RaggEst,mPact,"LEVL",exAnte,"Step3")))
                                                         $ p_data(Rest,mPact,S_RowsEst,"nObs")) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return 0.0


def V_EstV_lo_LOSF(lo_grof, losf_ms, grof_ms):
    r"""V_EstV.LO of a fodder's losses: 90% of its production's lower bound at the member state's loss rate.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 265-269):

             v_estV.LO(Rest,"LOSF",losfFromCoco2,exAnte) $ ( (v_estV.LO(Rest,"GROF",losfFromCoco2,exAnte) ge 0)
                                                          $ (v_estV.range(Rest,"GROF",losfFromCoco2,exAnte) gt 0))
                = .9 * v_estV.LO(Rest,"GROF",losfFromCoco2,exAnte)
                * SUM(MSEst $ ESTP(MSEst,"GROF",losfFromCoco2,exAnte),
                               ESTP(MSEST,"LOSF",losfFromCoco2,exAnte)/ESTP(MSEst,"GROF",losfFromCoco2,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    rate = losf_ms / grof_ms if grof_ms else 0.0
    return 0.9 * lo_grof * rate


def V_EstV_up_LOSF(up_grof, losf_ms, grof_ms):
    r"""V_EstV.UP of a fodder's losses: 110% of its production's upper bound at the member state's loss rate.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 271-276):

             v_estV.UP(Rest,"LOSF",losfFromCoco2,exAnte) $ (   (v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte) ge 0)
                                                          $ (v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte) lt inf)
                                                          $ (v_estV.range(Rest,"GROF",losfFromCoco2,exAnte) gt 0))
                = 1.1 * v_estV.UP(Rest,"GROF",losfFromCoco2,exAnte)
                * SUM(MSEst $ ESTP(MSEst,"GROF",losfFromCoco2,exAnte),
                               ESTP(MSEST,"LOSF",losfFromCoco2,exAnte)/ESTP(MSEst,"GROF",losfFromCoco2,exAnte));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    rate = losf_ms / grof_ms if grof_ms else 0.0
    return 1.1 * up_grof * rate


def V_EstV_fx_land(basm):
    r"""V_EstV.FX of the fixed land uses ARTO, INLW and KITC: their base.

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 282-284):

             v_estV.FX(REST,"ARTO","LEVL",exAnte) = P_DATA(REST,"ARTO","LEVL","BASM");
             v_estV.FX(REST,"INLW","LEVL",exAnte) = P_DATA(REST,"INLW","LEVL","BASM");
             v_estV.FX(REST,"KITC","LEVL",exAnte) = P_DATA(REST,"KITC","LEVL","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the regions and the sets and the bounds
    it reads in the caller (estimate_nuts2._open_bounds)."""
    return basm


def V_EstV_lo_ARTIF(basm, step3_ms, basm_ms, arto, inlw, lo_uaar):
    r"""V_EstV.LO of a region's artificial land: 99% of the smaller of the national change applied to its base and
    the land left beside the inland waters and UAAR's lower bound (as estimate_nuts2.gms l. 361-366).

    CAPRI's GAMS (captrd/est_Nuts2_grid_openbound.gms l. 287-292):

              v_estV.LO(REST,"ARTIF","LEVL",exAnte) = .99 * min( P_DATA(REST,"ARTIF","LEVL","BASM")
                                                                *P_Result(MS,"ARTIF","LEVL",ExAnte,"Step3")
                                                                /P_DATA(MS,"ARTIF","LEVL","BASM"),
                                                                 P_DATA(REST,"ARTO","LEVL","BASM")
                                                                -P_DATA(Rest,"INLW","LEVL","BASM")
                                                                -v_estV.lo(Rest,"UAAR","LEVL",exAnte))    ;

    Departures from CAPRI: only where the member state's base is nonzero (CAPRI would divide by zero); the domain in the caller 
    (estimate_nuts2._open_bounds)."""
    return 0.99 * min(basm * step3_ms / basm_ms, arto - inlw - lo_uaar)

r"""CAPRI's fudging functions (arm/market_model.gms l. 2376-2434): the smooth max that keeps a normalised quadratic
quantity positive (ProdFudge_; the feed's FeedFudge_, l. 1054-1063 of the feed block, and the processing's ProcFudge_
in the assembled system take the same form).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the whole-market system's supply cells and lifted cells (capri_mod/market/supply_system_ad.py prod_fudge, the
cell's mode: 0 the model's floor, 1 CAPRI's fudge, 2 the row within its bounds; market_system_ad.py's lifted
processing and non-EU feed cells call prod_fudge too). ProdPriceFudge_ (l. 2378-2392) feeds only Yield_ in the step
(v_prodPricePos, l. 1802; the other users are not in the step), a recursive block the model does not have (land.py's
docstring).

In this project's notation, for a cell's ProdNQ_ row qr (kt) with base production b (DATA Prod):

    ProdFudge_  q = max(qr, 0) + z log1p(exp(-|qr| / z)) + 1e-11,  z = 0.01 min(1000, max(1e-11, b))

which is CAPRI's -ncpcm(-qr, 0, z) + 1e-11 (GAMS's ncpCM(x, y, z) = x - z ln(1 + exp((x - y) / z))), written so that
exp's argument stays at or below 0. Departures from CAPRI: the row unscaled (CAPRI divides both sides by
|DATA Prod| + 0.1); CAPRI generates the row where the cell's lower bound is at or below 0 (after a widening of the
bounds), the model by the cell's mode (capri_mod/market/market_chain.py _fudge_modes). The processing's ProcFudge_ of
the market's CasADi blocks (processing.py ProcFudge_) writes the same smooth max in another arrangement, which rounds
differently: the two forms are kept, each where it is.
"""
from __future__ import annotations


def ProdFudge_Z(base):
    r"""ProdFudge_'s smoothing parameter z = 0.01 min(1000, max(1e-11, b)), b the cell's base production (a number;
    CAPRI's DATA Prod, ProdFudge_ l. 2420-2432). A float."""
    return 1e-2 * min(1000.0, max(1e-11, float(base)))


def ProdFudge_(qr, z):
    r"""ProdFudge_(RMS, XX1) (l. 2420-2432): CAPRI's smooth max of a cell's ProdNQ_ row qr, max(qr, 0) + z
    log1p(exp(-|qr| / z)) + 1e-11, z ProdFudge_Z of the cell's base production. CasADi. FeedFudge_ (l. 1053-1063) is
    the same function of a feed row, z from the feed at the calibration point.

    CAPRI's GAMS, ProdFudge_ (l. 2420-2432):

      ProdFudge_(RMS,XX1) $ (
                                   ((v_prodQuant.lo(RMS,XX1) ne v_prodQuant.up(RMS,XX1)))
                                 $ (XXX1(XX1) or XXX1("Fede"))
                                 $ (not XXBIOF(XX1))
                                 $ (not sum(sameas(xxOmYani,XX1),1))
                                 $ (v_prodQuant.lo(RMS,XX1) LE 0)
                                 $ DATA(RMS,"Prod",XX1,"CUR")
                                 $ (NOT SAMEAS(XX1,"DDGS")) ) ..
            v_prodQuant(RMS,XX1)
                /(abs(DATA(RMS,"Prod",XX1,"CUR"))+0.1)
             =E=  (-ncpcm(-v_prodQuantNeg(RMS,XX1),0,1.E-2*min(1000,Max(1.E-11,data(RMS,"Prod",XX1,"CUR")))) + 1.E-11)
                /(abs(DATA(RMS,"Prod",XX1,"CUR"))+0.1);

    CAPRI's GAMS, FeedFudge_ (l. 1053-1063):

      FeedFudge_(RMS,XX) $ (      (v_feedQuant.lo(RMS,XX) LE 0)
                                $ (XXX(XX) or XXX1("FEDE"))
                                $ (v_feedQuant.LO(RMS,XX) ne v_feedQuant.UP(RMS,XX))
                                $ DATA(RMS,"Feed",XX,"CUR")) ..
          v_feedQuant(RMS,XX)/(abs(DATA(RMS,"Feed",XX,"CUR"))+0.1)
             =E=  (-ncpcm(-v_feedQuantNeg(RMS,XX), 0,1.E-2*min(1000,max(1.E-11,data(RMS,"Feed",XX,"CUR"))))  + 1.E-11)
                             /(abs(DATA(RMS,"Feed",XX,"CUR"))+0.1);
    """
    import casadi as ca
    return ca.fmax(qr, 0.0) + z * ca.log1p(ca.exp(-ca.fabs(qr) / z)) + 1e-11

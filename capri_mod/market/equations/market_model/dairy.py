r"""CAPRI's dairy equations (arm/market_model.gms l. 1065-1114, of the behavioural functions): the dairies' normalised
quadratic netput (DairyNQ_), the processing margin of the dairy products (ProcMargM_) and the balances of milk fat and
protein (FatsProtBal_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the dairy block's algebra (capri_mod/market/dairy.py DairyMixin._dairy_algebra: ProcMargM_, DairyNQ_'s matrix,
FatsProtBal_'s rows) and its CasADi block (dairy_ad.py dairy_block_function: the output, the raw milk row, the fat and
protein residuals with the dairy products' processing, ProcNQ_ and ProcFudge_ of processing.py).

In this project's notation, per dairy region s, with z the price ratios - 1 of the nine products, raw milk, fat and
protein (p_k, p_F, p_P CAPRI's prices at the calibration point, f_k and r_k the products' fat and protein contents,
H_s the region's Hessian with the MILK row reversed, INPE_s its INPE price):

    ProcMargM_    dm_k = p_k z_k - f_k p_F z_F - r_k p_P z_P          (Mm_s z)
    DairyNQ_      dQ_s = H_s dm / INPE_s = G_s z,  Q = Q0 + G z  (G = sum_s G_s); the raw milk row: the dairies' demand
                  G_M z - kq z_M = the milk delivered's change
    FatsProtBal_  sum_k (+-) f_k dQ_k = - sum_k f_k dproc_k (fat; protein with r), the signs milk in, products out

CAPRI's tax at the dairies on raw milk (CSEI) is fixed in the simulation and drops out of the margin's change.

Departures from CAPRI: the block linear in z (CAPRI's NQ netput is linear in its normalised prices; the margins' change
is linear in the price ratios) and solved with the raw milk, fat and protein prices as the unknowns (one Newton step);
the rows unscaled; the processing change of the products (ProcNQ_, audit M9) enters the fat and protein rows.
"""
from __future__ import annotations


def ProcMargM_(p, f, pF, r, pP):
    r"""ProcMargM_(RMS, XXX) (l. 1089-1099), a dairy product's margin change per unit of the price ratios: its
    coefficients on z_k, z_F and z_P, (p, -f pF, -r pP): the product's price less its fat and protein contents at their
    prices. Returns the three coefficients.

    CAPRI's GAMS, ProcMargM_ (l. 1089-1099):

     ProcMargM_(RMS,MLK) $ (SUM(YY, ABS(p_hessNQDairy(RMS,MLK,YY,"CUR")))
                               $ (XXX(MLK) or (sameas(MLK,"MILK") $ sum(YYY(MLK1),1)) )) ..
    *
         v_procMarg(RMS,MLK)/(abs(DATA(RMS,"ProcMarg",MLK,"CUR"))+1)
          =E= (  v_prodPrice(RMS,MLK)
    *             For MILK there is no PPRI_ equ => A tax/subsidy collected/paid at dairy level is introduced here via CSEI:
    *             => will increase input cost for dairies (in tax case) and exert downward pressure on v_prodprice(MILK)
               - DATA(RMS,"CSEI",MLK,"CUR") $ sameas(MLK,"MILK")
               - DATA(RMS,"Fats",MLK,"CUR")*v_priceFatProt(RMS,"Fats")
               - DATA(RMS,"Prot",MLK,"CUR")*v_priceFatProt(RMS,"Prot")  )
             /(abs(DATA(RMS,"ProcMarg",MLK,"CUR"))+1);
    """
    return p, -f * pF, -r * pP


def DairyNQ_G(H, Mm, inpe):
    r"""DairyNQ_(RMS, XXX) (l. 1069-1084), a region's netput change per unit of z: H Mm / INPE (NumPy), H the region's
    Hessian (the MILK row reversed), Mm its ProcMargM_ matrix.

    CAPRI's GAMS, DairyNQ_ (l. 1069-1084):

     DairyNQ_(RMS,MLK) $ ( (xxx(MLK) or (sameas(MLK,"MILK") $ sum(YYY(MLK1),1)) )
                              $ (v_prodQuant.lo(RMS,MLK) ne v_prodQuant.up(RMS,MLK))
                                          $ DATA(RMS,"Prod",MLK,"CUR"))..
         ( v_prodQuantNeg(RMS,MLK) $ ( v_prodQuant.LO(RMS,MLK) LE 0)
     +     v_prodQuant(RMS,MLK)    $ ( V_prodQuant.LO(RMS,MLK) GT 0) )
                                                                  / (DATA(RMS,"Prod",MLK,"CUR")+0.1)
            =E= (p_cnstNQDairy(RMS,MLK)
               + SUM( YY $ (   DATA(RMS,"PPri",YY,"CUR")     $ (NOT MLK(YY))
                             + DATA(RMS,"ProcMarg",YY,"CUR") $ MLK(YY)),
                                 p_hessNQDairy(RMS,MLK,YY,"CUR")
                  * (   v_prodPrice(RMS,YY)  $ (NOT MLK(YY))
                      + v_procMarg(RMS,YY)   $  MLK(YY)      ) /v_prodPrice(RMS,"Inpe")))
                                                                 / (DATA(RMS,"Prod",MLK,"CUR")+0.1);
    """
    return H @ Mm / inpe


def DairyNQ_(Q0, G, z):
    r"""DairyNQ_'s output of the block, Q0 + G z (kt; CasADi). CAPRI's GAMS: DairyNQ_G's docstring."""
    import casadi as ca
    return Q0 + ca.mtimes(G, z)


def DairyNQ_milk(GM, z, kq, zM, mrhs):
    r"""DairyNQ_ for raw milk as the block's row: the dairies' milk demand change GM z less the supply's response kq zM
    and the milk delivered's change mrhs, = 0 (CasADi). CAPRI's GAMS: DairyNQ_G's docstring."""
    import casadi as ca
    return ca.dot(GM, z) - kq * zM - mrhs


def FatsProtBal_row(sgn, f, Gs):
    r"""FatsProtBal_(RMS, XXX) (l. 1103-1112), a region's term of the fat (or protein) row: (sgn f) Gs, sgn +1 for raw
    milk and -1 for the products, f the contents (NumPy).

    CAPRI's GAMS, FatsProtBal_ (l. 1103-1112):

     FatsProtBal_(RMS,FatsProt) $ ( (v_priceFatProt.lo(RMS,FatsProt) ne v_priceFatProt.up(RMS,FatsProt))
                                    $ (sum(XXX(MLK),1) ge 1))..
         (v_prodQuant(RMS,"MILK") * DATA(RMS,FatsProt,"MILK","CUR"))
             / (DATA(RMS,"PROD","MILK","CUR")* DATA(RMS,FatsProt,"MILK","CUR")+1)
               =E= SUM(MLK $ (NOT SAMEAS(MLK,"MILK")),
                         (  v_prodQuant(RMS,MLK) $ DATA(RMS,"Prod",MLK,"CUR")
                          - v_procQuant(RMS,MLK) $ DATA(RMS,"Proc",MLK,"CUR"))
                                                                   * DATA(RMS,FatsProt,MLK,"CUR"))
             / (DATA(RMS,"PROD","MILK","CUR")* DATA(RMS,FatsProt,"MILK","CUR")+1);
    """
    return (sgn * f) @ Gs


def FatsProtBal_(row, z, rproc):
    r"""FatsProtBal_ as the block's residual: row z - rproc, rproc the products' processing change in fat (or
    protein), - sum_k f_k dproc_k (CasADi). CAPRI's GAMS: FatsProtBal_row's docstring."""
    import casadi as ca
    return ca.dot(row, z) - rproc

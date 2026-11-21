r"""CAPRI's demand system (arm/market_model.gms l. 816-918, the first block of the behavioural functions): human
consumption per behavioural region from the Generalised Leontief expenditure function, its terms F (GLDemandFS_), G
(GLDemandGS_) and the derivatives G_i (GLDemandGis_), and the demand itself (XiS_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the GL demand of one behavioural region as the model evaluates it (capri_mod/market/demand_ad.py
gl_entry_function, the CasADi function every caller uses: DemandMixin._gl_eval and gl_food_ratio, use_ad.py, the
assembled market system). The consumer prices: prices.py CPri_.

Not written: consFudge_ (l. 905-916), CAPRI's Fischer-Burmeister smoothing (ncpcm) of a human consumption that may turn
negative (v_consQuantNeg); the model floors each good's demand at 0 in the sums per model region instead
(demand_ad.py gl_block_function, fmax): a porting difference.

In this project's notation, per behavioural region (p the consumer prices in EUR/kg, d the commitments in kg per head,
B the symmetric GL matrix, Y the income per head, ir its ratio to the calibration point, INHA the inhabitants):

    GLDemandFS_   F = d' p
    GLDemandGS_   G = sqrt(p)' B sqrt(p)
    GLDemandGis_  G_i = (B sqrt(p))_i / sqrt(p_i)
    XiS_          x_i = [G_i / G (Y ir - F) + d_i] INHA / 1000          (1000 t)

Departures from CAPRI: CAPRI divides each row by its value at the calibration point (the equations' own comments: "only
for scaling purposes", "to bring the equation around unity"), and GLDemandGS_ by 10,000; the model writes the rows
unscaled, the same solution. The parameters are CAPRI's 2030 calibration with the commitments re-fitted to the model's
base use (DemandMixin._gl_refit, CAPRI's arm/recalibrate_commitments.gms: the calibration block, C). The functions take
CasADi expressions (the block's SX graph).
"""
from __future__ import annotations


def GLDemandFS_(d, p):
    r"""GLDemandFS_(RMS) (l. 826-839): F, the commitments' value at the consumer prices, d' p (EUR per head; CAPRI's
    p_pdGL x v_consPrice x 1e-3 with prices in EUR/t, the model's in EUR/kg).

    CAPRI's GAMS, GLDemandFS_ (l. 826-839):

     GLDemandFS_(RMS) $ sum(xxx $ v_consQuant.range(RMS,XXX),1) ..
    *
         v_GLDemandFS(RMS) /
    *
    *         --- the following term (also found o the RHS) is only for scaling purposes
    *             to bring the equation around unity
    *
              (SUM(XX1 $ p_pdGL(RMS,XX1,"CUR"),
                                 DATA(RMS,"CPRI",XX1,"CUR") * p_pdGL(RMS,XX1,"CUR")*1.E-3) + 0.1)
          =E= SUM(XX1 $ p_pdGl(RMS,XX1,"CUR"),
                                 v_consPrice(RMS,XX1) * p_pdGL(RMS,XX1,"CUR")*1.E-3)
            / (SUM(XX1 $ p_pdGL(RMS,XX1,"CUR"),
                                 DATA(RMS,"CPRI",XX1,"CUR") * p_pdGL(RMS,XX1,"CUR")*1.E-3) + 0.1);
    """
    import casadi as ca
    return ca.dot(d, p)


def GLDemandGS_(sq, Bs):
    r"""GLDemandGS_(RMS) (l. 845-854): G = sqrt(p)' B sqrt(p), written as the dot product of sq = sqrt(p) with
    Bs = B sqrt(p) (the builder's product, which GLDemandGis_ shares; CAPRI's sum over the pairs of p_pbGL x
    sqrt(p_x p_y x 1e-6)).

    CAPRI's GAMS, GLDemandGS_ (l. 845-854):

     GLDemandGS_(RMS) $ sum(xxx $ v_consQuant.range(RMS,XXX),1) ..
    *
    *    --- due to DF in the calibration of the parameter set, it is possible
    *        to fix v_GLDemandGS durign a value. That value is 10000. and
    *        use in the equation for scaling to bring the equation to unity in the
    *        calibration point
    *
         v_GLDemandGS(RMS)/10000. =E= SUM( (XX1,YY1) $ p_pbGL(RMS,XX1,YY1,"CUR"),
                                            p_pbGL(RMS,XX1,YY1,"CUR")
                                              * SQRT(v_consPrice(RMS,XX1)*v_consPrice(RMS,YY1)*1.E-6) )/10000.;
    """
    import casadi as ca
    return ca.dot(sq, Bs)


def GLDemandGis_(Bs, sq):
    r"""GLDemandGis_(RMS, XXX) (l. 860-886; CAPRI's definition spells it GLDemandGiS_): G_i = (B sqrt(p))_i /
    sqrt(p_i), the derivatives of G, as Bs / sq. CAPRI multiplies and divides by the calibration price "only to
    stabilize the numerical solution" (its comment); the model does not.

    CAPRI's GAMS, GLDemandGiS_ (l. 860-886):

     GLDemandGiS_(RMS,XXX) $ (  (v_consQuant.LO(RMS,XXX) ne v_consQuant.UP(RMS,XXX))
                              $ DATA(RMS,"HCon",XXX,"CUR"))  ..
         v_GLDemandGis(RMS,XXX)
    *
    *                --- the following is only a scaling term to bring the equation around unity
    *                    in  calibration point. It is also found on the RHS
    *
                     /   (SUM( YY1 $ p_pbGl(RMS,XXX,YY1,"CUR"),
                                     p_pbGL(RMS,XXX,YY1,"CUR")
                                       * SQRT(DATA(RMS,"CPRI",YY1,"CUR")/DATA(RMS,"CPRI",XXX,"CUR"))) + 0.1)
                     =E= [SUM( YY1 $ p_pbGl(RMS,XXX,YY1,"CUR"),
                                         p_pbGL(RMS,XXX,YY1,"CUR")
    *
    *                                  ---- the division / multiplication by DATA(RMS,"CPRI",XXX,"CUR")
    *                                       cancel out and are only introduced to stabilize
    *                                       the numerical solution
    *
                                       * SQRT(v_consPrice(RMS,YY1)/DATA(RMS,"CPRI",XXX,"CUR")))
                                       * SQRT(DATA(RMS,"CPRI",XXX,"CUR")/v_consPrice(RMS,XXX))
                         ]
    *
                     /   (SUM( YY1 $ p_pbGl(RMS,XXX,YY1,"CUR"),
                                     p_pbGL(RMS,XXX,YY1,"CUR")
                                       * SQRT(DATA(RMS,"CPRI",YY1,"CUR")/DATA(RMS,"CPRI",XXX,"CUR"))) + 0.1);
    """
    return Bs / sq


def XiS_(Gi, G, Y, ir, F, d, inha):
    r"""XiS_(RMS, XXX) (l. 891-903): the human consumption, x_i = [G_i / G (Y ir - F) + d_i] INHA / 1000 (1000 t;
    CAPRI's DATA(Ince) / DATA(INHA) is Y, the model moves it by the income ratio ir).

    CAPRI's GAMS, XiS_ (l. 891-903):

     XiS_(RMS,XXX)  $ (  (v_consQuant.LO(RMS,XXX) ne v_consQuant.UP(RMS,XXX))
                       $ DATA(RMS,"HCon",XXX,"CUR")) ..
    *
         (  v_consQuant(RMS,XXX)    $ ( v_consQuant.LO(RMS,XXX) GT 0)
          + v_consQuantNeg(RMS,XXX) $ ( v_consQuant.LO(RMS,XXX) LE 0)
         )
         /(DATA(RMS,"HCon",XXX,"CUR")+0.1) =E=
    *
           ((v_GLDemandGis(RMS,XXX)/v_GLDemandGS(RMS)
               * ( DATA(RMS,"Ince","Levl","CUR")/DATA(RMS,"INHA","LEVL","CUR") - v_GLDemandFS(RMS))
                  + p_pdGL(RMS,XXX,"CUR")) * DATA(RMS,"INHA","LEVL","CUR")/1000.)/(DATA(RMS,"HCon",XXX,"CUR")+0.1);
    """
    return (Gi / G * (Y * ir - F) + d) * inha / 1000.0

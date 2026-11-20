r"""CAPRI's feed equations (arm/market_model.gms l. 919-1064, of the behavioural functions): the feed bulks of the
regions with supply models (feedBlkPrice_, feedBlk_, FeedShareEqu_) and the feed of the other regions, their
normalised quadratic feed demand (FeedNQ_) and the feed energy balance (FeedBal_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the market's CasADi feed blocks (capri_mod/market/feed_ad.py: feedblk_function, feedblk_factor_function,
feednq_function, fedebal_function), which FeedMixin (capri_mod/market/feed.py), use_ad.py and the assembled market
system evaluate. FeedFudge_ (l. 1054-1063), CAPRI's smooth max on a non-EU feed that may turn negative, is the
assembled system's (its lifted feed cells, market_system_ad.py with supply_system_ad.prod_fudge): with ProdFudge_, M3.
FeedShift_ (l. 922-944) is not in m_globMarket's list (commented out at l. 4188).

In this project's notation, for a bulk of a region with supply models (s CAPRI's value shares, r the products'
Armington price ratios to the calibration point, floored at 1e-6, rho the substitution parameter, q0 the 2030 feed,
k the bulk's change against its base) and for a non-EU behavioural region (ra its trade region's Armington ratios, rp
its producer ratios, m its raw milk ratio, dr its land rents' changes, FEDE the feed energy's price ratio):

    feedBlkPrice_   pb = (sum_i s_i r_i^(1 - rho))^(1 / (1 - rho))
    FeedShareEqu_   q_i = q0_i k (pb / r_i)^rho
    feedBlk_        k's response within the market solve: exp(sum_y e_y log(r_y / sv_y)) (sv the ratios the supply
                    models saw)
    FeedNQ_         feed_x = q0_x + sum_y h_xy (ra_y - 1) + h_xF (FEDE - 1)
    FeedBal_        sum_x kcal_x feed_x = sum_a conv_a prod_a, solved for FEDE in closed form (linear in FEDE)

Departures from CAPRI: the rows unscaled; the bulk's price and shares in ratios to CAPRI's calibration point (CAPRI
normalises by the products' average Armington price + 1); feedBlk_'s level is the supply models' bulk (its constant
p_feedBlkCnst at their view, the market solve's response on top, audit M4), the product prices' cross terms left out
where a price is missing (w = 0); FeedNQ_'s Hessian on the price ratios (CAPRI's on the prices normalised by INPE's,
less the feed subsidy FSEi); FeedBal_'s production side ProdNQ_'s terms (M3) in the same linear form.
"""
from __future__ import annotations


def feedBlkPrice_(s, rr, rho):
    r"""feedBlkPrice_(RMSSUP, FEED_TRD) (l. 951-965): the bulk's CES price index, (sum_i s_i rr_i^(1 - rho))^(1 /
    (1 - rho)), s CAPRI's value shares (p_dpCESFeed), rr the products' price ratios (floored), rho p_rhoFeed. CasADi.

    CAPRI's GAMS, feedBlkPrice_ (l. 951-965):

     feedBlkPrice_(RMSSUP,FEED_TRD) $ SUM(FEED_TO_XX(FEED_TRD,XXX) $ DATA(RMSSUP,"FEED",XXX,"CUR"), 1) ..
      v_feedBlkPrice(RMSSUP,feed_trd)
              / SUM(FEED_TO_XX(FEED_TRD,XX) $ DATA(RMSSUP,"FEED",XX,"CUR"), sum(RMS_TO_RM(RMSSUP,RM), DATA(RM,"Arm1P",XX,"CUR")+1))
              * SUM(FEED_TO_XX(FEED_TRD,XX) $ DATA(RMSSUP,"FEED",XX,"CUR"), 1)
       =E= SUM(FEED_TO_XX(FEED_TRD,XX) $ DATA(RMSSUP,"FEED",XX,"CUR"),
                                               p_dpCESFeed(RMSSUP,XX)
             * (  sum(RMS_TO_RM(RMSSUP,RM),v_arm1Price(RM,XX))
                   / SUM(YY $ (FEED_TO_XX(FEED_TRD,YY) $ DATA(RMSSUP,"FEED",YY,"CUR")), sum(RMS_TO_RM(RMSSUP,RM), DATA(RM,"Arm1P",YY,"CUR")+1))
                    * SUM(YY $ (FEED_TO_XX(FEED_TRD,YY) $ DATA(RMSSUP,"FEED",YY,"CUR")), 1)
                )
                                               **(1-p_rhoFeed(RMSSUP,FEED_TRD)))
                                                    ** (1/(1-p_rhoFeed(RMSSUP,FEED_TRD)));
    """
    import casadi as ca
    return ca.dot(s, rr ** (1.0 - rho)) ** (1.0 / (1.0 - rho))


def feedBlk_(w, e, r, sv):
    r"""feedBlk_(RMSSUP, FEED_TRD) (l. 972-993), the bulk's response within the market solve: exp(sum_y w_y e_y
    log(r_y / sv_y)), e the bulk's elasticities to the products' prices (p_feedBlkElas), r the region's price ratios,
    sv those its supply models saw, w 1 where both are given (the ratios floored at 1e-300). CasADi.

    CAPRI's GAMS, feedBlk_ (l. 972-993):

     feedBlk_(RMSSUP,FEED_TRD) $ ( SUM(FEED_TO_XX(FEED_TRD,XXX) $ DATA(RMSSUP,"FEED",XXX,"CUR"), 1) $ v_feedBlk.range(RMSSUP,FEED_TRD)) ..
         log(v_feedBlk(RMSSUP,FEED_TRD))
                  / log((SUM(FEED_TO_XX(FEED_TRD,XX), DATA(RMSSUP,"FEED",XX,"CUR")) + 0.1))
              =E= (
    *
    *              ---- effect of own and cross prices of bulkd (FCER,FPRO ...)
    *
                   sum(FEED_TRD1 $ p_feedBlkElas(RMSSUP,FEED_TRD,FEED_TRD1),
                              p_feedBlkElas(RMSSUP,FEED_TRD,FEED_TRD1)
                                    * log(v_feedBlkPrice(RMSSUP,FEED_TRD1)))
    *
    *              ---- cross effects with other prices in supply model
    *
                  +sum(XX $ (p_feedBlkElas(RMSSUP,FEED_TRD,XX) $ data(rmssup,"prod",xx,"cur")),
                              p_feedBlkElas(RMSSUP,FEED_TRD,XX)
                                    * log(max(1.E-3,v_prodPrice(RMSSUP,XX))))
                                     + p_feedBlkCnst(RMSSUP,FEED_TRD))
                  / log((SUM(FEED_TO_XX(FEED_TRD,XX), DATA(RMSSUP,"FEED",XX,"CUR")) + 0.1));
    """
    import casadi as ca
    t = e * ca.log(ca.fmax(r, 1e-300) / ca.fmax(sv, 1e-300))
    return ca.exp(ca.dot(w, t))


def FeedShareEqu_(q0, k, pb, rr, rho):
    r"""FeedShareEqu_(RMSSUP, XXX) (l. 999-1012; CAPRI's definition spells it feedShareEqu_): each product's feed in
    the bulk, q0 k (pb / rr)^rho (kt).

    CAPRI's GAMS, feedShareEqu_ (l. 999-1012):

     feedShareEqu_(RMSSUP,XXX) $ ( (v_feedQuant.LO(RMSSUP,XXX) ne v_feedQuant.UP(RMSSUP,XXX))
                                        $ DATA(RMSSUP,"Feed",XXX,"CUR") ) ..
         v_feedQuant(RMSSUP,XXX)/(abs(DATA(RMSSUP,"Feed",XXX,"CUR"))+0.1)
                  =E= sum(FEED_TO_XX(FEED_TRD,XXX),
                      v_feedBlk(RMSSUP,FEED_TRD)/(abs(DATA(RMSSUP,"Feed",XXX,"CUR"))+0.1)
                     * p_dpCESFeed(RMSSUP,XXX)
    *   ... times ratio of output price to factor price plus tax, to the power of the substitution elasticity
                     * [ v_feedBlkPrice(RMSSUP,FEED_TRD) / sum(RMS_TO_RM(RMSSUP,RM),v_arm1Price(RM,XXX)) ] ** p_rhoFeed(RMSSUP,FEED_TRD));
    """
    return q0 * k * (pb / rr) ** rho


def FeedNQ_(H, ra, hF, fede):
    r"""FeedNQ_(RMS, XX) (l. 1033-1048), the feeds' change from their base (kt) in a non-EU behavioural region:
    H (ra - 1) + hF (FEDE - 1), H CAPRI's Hessian terms on the Armington price ratios, hF on the feed energy's.
    CasADi.

    CAPRI's GAMS, FeedNQ_ (l. 1033-1048):

     FeedNQ_(RMS,XX) $ (   (v_feedQuant.LO(RMS,XX) ne v_feedQuant.UP(RMS,XX))
                         $ (XXX(XX) or XXX1("FEDE"))
                         $ (NOT RMSSUP(RMS))
                         $ DATA(RMS,"Feed",XX,"CUR") ) ..
         ( v_feedQuantNeg(RMS,XX) $ ( v_feedQuant.LO(RMS,XX) LE 0)
     +     v_feedQuant(RMS,XX)    $ ( v_feedQuant.LO(RMS,XX) GT 0)) / (abs(DATA(RMS,"Feed",XX,"CUR"))+0.1)
    *
    *                 --- constant term of NQ function, p_hessNQFeed: symmetric Hessian
    *
                 =E=   ( p_cnstNQFeed(RMS,XX)
                        + SUM( (RMS_TO_RM(RMS,RM),YY1) $ ( DATA(RM,"arm1P",YY1,"CUR") or sameas(YY1,"FEDE")),
                                       p_hessNQFeed(RMS,XX,YY1,"CUR")
                                          * (  (v_arm1Price(RM,YY1)-DATA(RMS,"FSEi",YY1,"CUR")) $ (not sameas(YY1,"Fede"))
                                             + v_prodPrice(RMS,"Fede") $ sameas(YY1,"FEDE"))/v_arm1Price(RM,"Inpe")))
                       /  (abs(DATA(RMS,"Feed",XX,"CUR"))+0.1);
    """
    import casadi as ca
    return ca.mtimes(H, ra - 1.0) + hF * (fede - 1.0)


def FeedBal_(e0, aF, n0, aN, fede):
    r"""FeedBal_(RMS) (l. 1018-1028), its residual: the energy fed less the energy the animals need (Mcal x 1000),
    (e0 + aF (FEDE - 1)) - (n0 + aN (FEDE - 1)); e0 and n0 the two sides at FEDE = 1 (FeedNQ_'s and ProdNQ_'s terms
    with their calories and conversion factors), aF and aN their slopes in FEDE.

    CAPRI's GAMS, FeedBal_ (l. 1018-1028):

     FeedBal_(RMS) $ ( XXX1("FEDE") $ (not RMSSUP(RMS)) ) ..
           SUM(XX $ DATA(RMS,"Feed",XX,"CUR"),
               v_feedQuant(RMS,XX) * p_calContent(XX))
           /  (SUM(XX $ DATA(RMS,"Feed",XX,"CUR"),
                   DATA(RMS,"feed",XX,"CUR") * p_calContent(XX))+0.1)
             =E= SUM( XX_ANIM_FEED $ DATA(RMS,"PROD",XX_ANIM_FEED,"CUR"),
                    v_prodQuant(RMS,XX_ANIM_FEED) * pv_feedConv(RMS,XX_ANIM_FEED,"CUR"))
              /  (SUM(XX $ DATA(RMS,"Feed",XX,"CUR"),
                    DATA(RMS,"feed",XX,"CUR") * p_calContent(XX))+0.1);
    """
    return (e0 + aF * (fede - 1.0)) - (n0 + aN * (fede - 1.0))


def FeedBal_fede(e0, n0, den):
    r"""FeedBal_ solved for the feed energy's price ratio (it is linear in FEDE): 1 + (n0 - e0) / den, den = aF - aN
    (FeedBal_'s terms). CAPRI's GAMS: FeedBal_'s docstring."""
    return 1.0 + (n0 - e0) / den

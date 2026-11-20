r"""CAPRI's biofuel equations (arm/market_model.gms l. 1180-1439, of the behavioural functions): the first-generation
supply (SupplyBiof_) at the producer price relative to the feedstock cost (BiofPriceRel_), the feedstocks' cost
(BiofFeedCost_) and its CES aggregate (BiofFeedCostAgg_), the feedstock demand (Biof_) with the numeraire's from the
output (ProdBiof_), and the biofuel use (biofDemshare_, biofDem_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the market's CasADi biofuel block (capri_mod/market/biofuel_ad.py: feed_group_function, supply_function,
demand_function), which BiofuelMixin (biofuel.py), use_ad.py and supply_system_ad.py evaluate. MaprBiof_ (the output:
first generation + the fixed NAGR, SECG and EXOG) and prodQuantBiofBy_ (the DDGS of the cereal feedstocks) are running
sums in biofuel.py and supply_system_ad.py (the latter's DDGS sum a CasADi dot product, NumPy's sum the former's: they
round differently; both kept). CSugarPrice_ is empty in the step (its domain needs a sugar quota, DATA(QUTS, SUGA) >
eps; 0 + eps from 2017, policy/reformsugarquotas.gms l. 136-142).

In this project's notation, per CAPRI region and biofuel (r the feedstocks' Armington price ratios, p0 their prices,
PRCBY their by-products' yields at the by-product's price p_by (DDGS at its producer price ratio), dp CAPRI's CES
shares, rho the substitution parameter, X the first-generation output, PRCB the processing yields, rb the biofuel's
producer price ratio, PPRI0 its price; cp its consumer price, fossil CPRI the fossil fuel's):

    BiofFeedCost_     mu_f = max(p0_f r_f - PRCBY_f p_by,f, 1e-6)
    BiofFeedCostAgg_  mu_b = (sum_f dp_f mu_f^(1 - rho))^(1 / (1 - rho))
    Biof_             q_f = dp_f X (mu_b / mu_f)^rho                    (f not the numeraire)
    ProdBiof_         q_num = max(0, (X - sum_(f != num) q_f PRCB_f) / PRCB_num)
    BiofPriceRel_     PR = PPRI0 rb / mu_b
    SupplyBiof_       X = max(0, scale PR + exp(alfa + beta log(PR + 0.01)) SIGMOID(slope (PR - turn)))
    biofDemshare_     share = QUTS + MAX SIGMOID(Slope (cp / fossil CPRI - Turn))
    biofDem_          BIOF = share HCON oilEqu_fossil / oilEqu_b

Departures from CAPRI: the rows unscaled; SIGMOID's argument clipped to [-500, 500] (exp's overflow); the floors
max(0, .) and max(1e-6, .) the model's; the consumer price written apart from prices.py's CPri_ (cpri + arm1p (ra -
1), the factors in the other order: the same value; biofuel_ad.py demand_function, floored at 1e-6); the biofuels'
non-fuel processing a third form of ProcNQ_'s own term (biofuel_ad.py proc_function); total fuel use and the fossil
prices fixed.
"""
from __future__ import annotations


def SIGMOID(x):
    r"""CAPRI's sigmoid, 1 / (1 + exp(-x)), with x clipped to [-500, 500] (the model's: exp overflows beyond). CasADi."""
    import casadi as ca
    return 1.0 / (1.0 + ca.exp(-ca.fmin(ca.fmax(x, -500.0), 500.0)))


def BiofFeedCost_(p0, r, by):
    r"""BiofFeedCost_(RMS, XXBIOF, XX) (l. 1283-1307): the feedstocks' cost per unit of input less their by-products'
    value, max(p0 r - by, 1e-6) (by = PRCBY x the by-product's price ratio). CasADi.

    CAPRI's GAMS, BiofFeedCost_ (l. 1283-1307):

      biofFeedCost_(RMS,XBioStock) $ (   DATA(RMS,"Biof",XBioStock,"CUR")
                                      $ DATA(RMS,"PRCB",XBioStock,"CUR")
    *
    *                              --- input cost is not fixed
    *
                                      $ (v_biofFeedCost.lo(RMS,XBioStock) ne v_biofFeedCost.up(RMS,XBioStock))
    *
                                   ) ..
         v_biofFeedCost(RMS,XBioStock)/(DATA(RMS,"BiofFeedCost",XBioStock,"CUR")+1) =E=
                    [
    *                  --- by feedstock cost per unit of input
                            SUM((RMS_TO_RM(RMS,RM), SAMEAS(XBioStock,XX)),
                                         v_Arm1Price(RM,XX)       $ ((NOT sameas(XX,"SUGA")) or (data(RMS,"QUTS","SUGA","CUR") le eps))
                                       + v_cSugarPrice(RMS)       $ (SAMEAS(XX,"SUGA") and (data(RMS,"QUTS","SUGA","CUR") gt eps))
                             )
    *                  -- minus value of by product per ton of input
                       - SUM(Stock_to_By(XBioStock,bio_By), DATA(RMS,"PRCBY",XBioStock,"CUR")*v_prodPrice(RMS,bio_By))
                 ]
    $iftheni.mark2 %markupBiofFeedCost%==on
                 * (1+p_markupBiofFeedCost(RMS,XBioStock))
    $endif.mark2
                /(DATA(RMS,"BiofFeedCost",XBioStock,"CUR")+1) ;
    """
    import casadi as ca
    return ca.fmax(p0 * r - by, 1e-6)


def BiofFeedCostAgg_(dp, mu, rho):
    r"""BiofFeedCostAgg_(RMS, XXBIOF) (l. 1313-1334; CAPRI's definition spells it biofFeedCostAgg_): the feedstocks'
    CES cost, (sum_f dp_f mu_f^(1 - rho))^(1 / (1 - rho)). CasADi.

    CAPRI's GAMS, biofFeedCostAgg_ (l. 1313-1334):

      biofFeedCostAgg_(RMS,XXBIOF) $ (
    *
    *                              --- some first generation output produced in calibration point
    *
                                     (SUM(Stock_to_Fuel(XBioStock,XXBioF),
                                        DATA(RMS,"BIOF",XBioStock,"CUR")*DATA(RMS,"PRCB",XBioStock,"CUR")))
    *
    *                              --- margin not fixed
    *
                                   $ (v_biofFeedCost.lo(RMS,XXBIOF) ne v_biofFeedCost.up(RMS,XXBIOF))
                                   $ DATA(RMS,"PROD",XXBIOF,"CUR")
                                   ) ..
        v_biofFeedCost(RMS,XXBIOF)
          /(DATA(RMS,"BiofFeedCost",XXBIOF,"CUR")+1)
            =E=
                  SUM(Stock_to_fuel(XBioStock,XXBiof) $ p_dpCesBiof(RMS,XBioStock),
                         p_dpCesBiof(RMS,XBioStock)  * (v_biofFeedCost(RMS,XBioStock)/(data(RMS,"BiofFeedCost",XXBIOF,"CUR")+1)) ** (1-p_rhoBioFuel(RMS,XXBiof))
                     ) ** (1/(1-p_rhoBioFuel(RMS,XXBiof)));
    """
    import casadi as ca
    return ca.dot(dp, mu ** (1.0 - rho)) ** (1.0 / (1.0 - rho))


def Biof_(dp, X, mub, mu, rho):
    r"""Biof_(RMS, XX) (l. 1341-1382): the feedstocks' demand from the CES, dp X (mu_b / mu_f)^rho (kt; the numeraire's
    replaced by ProdBiof_).

    CAPRI's GAMS, Biof_ (l. 1341-1382):

     Biof_(RMS,XX) $ (
    *
    *          Can be seen as paired to v_bioProcQuant with the exemption of the numeraire
    *
    *
    *       --- don't enforce share equation for fixed quantities (arm\widen_bounds.gms)
    *
                    ( v_biofProcQuant.LO(RMS,XX) NE v_biofProcQuant.UP(RMS,XX))
                    $ (v_biofProcQuant.UP(RMS,XX) ne 0)
    *
    *       --- introduce if XX is matched to a biofuel XXX (BIOE/BIOD) in the current solve
    *           or if XX is in the current solve (XXX), in both cases, processing coefficient must ne non-zero
    *
                    $ (    SUM(Stock_to_fuel(XX,XXX), DATA(RMS,"PRCB",XX,"CUR"))
                        or SUM(Stock_to_fuel(XXX,XXBIOF) $ SAMEAS(XX,XXX), DATA(RMS,"PRCB",XXX,"CUR"))
                      )
    *
    *       --- not working for the numeraire feedstock which is used to define relative prices
    *           and serves as the anchor quantity
    *
                    $ (NOT SUM(BIOF_NUM(RMS,XXBioF,XX),1))
                    $ DATA(RMS,"Biof",XX,"CUR")
                  )  ..
    *
    *
           v_biofProcQuant(RMS,XX)/(DATA(RMS,"Biof",XX,"CUR")+0.1)
            =E= [
                 SUM(Stock_to_fuel(XX,XXBiof),
    *
    *                 ---- a share of output production quantity
    *
                       p_dpCESBiof(RMS,XX) * v_prodBiof(RMS,XXBioF)
    *
    *                ---- times output prices divided by feedcost cost
    *                     exponent the substiution elasticity
    *
                     * (v_biofFeedCost(RMS,XXBIOF) / v_biofFeedCost(RMS,XX)) ** p_rhoBioFuel(RMS,XXBIOF)
                   )
                 ]/(DATA(RMS,"Biof",XX,"CUR")+0.1);
    """
    return dp * X * (mub / mu) ** rho


def ProdBiof_(X, rest, prcb):
    r"""ProdBiof_(RMS, XXBIOF) (l. 1233-1246), solved for the numeraire feedstock: max(0, (X - rest) / prcb), rest the
    other feedstocks' output (sum_(f != num) q_f PRCB_f), prcb the numeraire's processing yield. CasADi.

    CAPRI's GAMS, ProdBiof_ (l. 1233-1246):

     prodBiof_(RMS,XXBioF) $ (
                       (SUM(Stock_to_fuel(YbioStock,XXBioF), DATA(RMS,"BioF",YbioStock,"CUR")) GT 1)
    *                --- the numerarie is not fixed
                     $ (NOT SUM(BIOF_NUM(RMS,XXBioF,XX) $ (v_BiofProcQuant.LO(RMS,XX) EQ v_biofProcQuant.UP(RMS,XX)),1))
    *                --- at least one feedstock in data base
                     $  SUM(Stock_to_fuel(XXX,XXBioF) $ (DATA(RMS,"PRCB",XXX,"CUR") $ DATA(RMS,"BioF",XXX,"CUR")),1)
                     $ DATA(RMS,"Prod",XXBioF,"CUR")) ..
         v_prodBiof(RMS,XXBioF)/(DATA(RMS,"Prod",XXBioF,"CUR")+0.1) =E=
              SUM(Stock_to_fuel(XX,XXBioF) $ (DATA(RMS,"PRCB",XX,"CUR") $ DATA(RMS,"BioF",XX,"CUR")),
                                           v_biofProcQuant(RMS,XX) * DATA(RMS,"PRCB",XX,"CUR"))
                                /(DATA(RMS,"Prod",XXBioF,"CUR")+0.1);
    """
    import casadi as ca
    return ca.fmax(0.0, (X - rest) / prcb)


def BiofPriceRel_(ppri, rb, mub):
    r"""BiofPriceRel_(RMS, XXBIOF) (l. 1384-1388; CAPRI's definition spells it biofPriceRel_): the biofuel's producer
    price relative to its feedstock cost, PPRI0 rb / mu_b.

    CAPRI's GAMS, biofPriceRel_ (l. 1384-1388):

     biofPriceRel_(RMS,XXBIOF) $ (DATA(RMS,"PROD",XXBIOF,"CUR") $ DATA(RMS,"biofPriceRel",XXBIOF,"CUR") $ XXX1(XXBIOF)) ..
       v_biofPriceRel(RMS,XXBIOF)/(DATA(RMS,"biofPriceRel",XXBIOF,"CUR")+1)
           =E= [v_prodPrice(RMS,XXBiof) / v_biofFeedCost(RMS,XXBIOF)]
               /(DATA(RMS,"biofPriceRel",XXBIOF,"CUR")+1);
    """
    return ppri * rb / mub


def SupplyBiof_(scale, PR, alfa, beta, slope, turn):
    r"""SupplyBiof_(RMS, XXBIOF) (l. 1186-1205): the first-generation output, max(0, scale PR + exp(alfa + beta log(PR
    + 0.01)) SIGMOID(slope (PR - turn))). CasADi.

    CAPRI's GAMS, SupplyBiof_ (l. 1186-1205):

     SupplyBiof_(RMS,XXBIOF) $     ( DATA(RMS,"BiofPriceRel",XXBIOF,"CUR")
                                  $ (SUM(Stock_to_Fuel(XBioStock,XXBioF),
                                        DATA(RMS,"BIOF",XBioStock,"CUR")*DATA(RMS,"PRCB",XBioStock,"CUR")))
                                  $ ((v_prodBiof.lo(RMS,XXBioF) ne v_prodBiof.up(RMS,XXBioF)) or p_trim)
                                  $ (v_prodQuant.lo(RMS,XXBioF) ne v_prodQuant.up(RMS,XXBioF))
                                  $ DATA(RMS,"PROD",XXBIOF,"CUR")
                                  $ XXX1(XXBIOF)
                                  $ p_endoBioMarket
                                   ) ..
         v_prodBiof(RMS,XXBioF)/(DATA(RMS,"Prod",XXBioF,"CUR")+0.1)
          =E=
    *              --- small linear term to avoid zero production and zero slope..
                  (p_bioSupPar(RMS,XXBIOF,"scale")*v_biofPriceRel(RMS,XXBIOF)
    *             --- double log part
                  + exp(p_bioSupPar(RMS,XXBIOF,"alfa") + p_bioSupPar(RMS,XXBIOF,"beta")*log(v_biofPriceRel(RMS,XXBIOF)+1e-2))
    *                      --- multipied to sigmoid function that guarantees steeper slope
                                       * SIGMOID(p_bioSupPar(RMS,XXBIOF,"SLOPE")
                                                *(v_biofPriceRel(RMS,XXBIOF)
                                                  -p_bioSupPar (RMS,XXBIOF,"Turn"))))/(DATA(RMS,"Prod",XXBioF,"CUR")+0.1);
    """
    import casadi as ca
    return ca.fmax(0.0, scale * PR + ca.exp(alfa + beta * ca.log(PR + 1e-2)) * SIGMOID(slope * (PR - turn)))


def biofDemshare_(quts, dmax, slope, cp, fossil, turn):
    r"""biofDemshare_(RMS, XXBIOF) (l. 1393-1415): the biofuel's share in the fuel use, QUTS + MAX SIGMOID(Slope (cp /
    fossil CPRI - Turn)) (QUTS with the mandate applied). CasADi.

    CAPRI's GAMS, biofDemshare_ (l. 1393-1415):

     biofDemShare_(RMS,XXBIOF) $ (
                                         SUM(fuelMatch(XXBioF,Fuel_Rows), Data(RMS,"CPRI",fuel_rows,"CUR"))
                                       $ p_bioDemPar(RMS,XXBioF,"Slope")
                                       $ sum(sameas(xxx,xxBiof),1)
                                       $ (v_biofProcQuant.range(RMS,XXBIOF) ne 0)
                                       $ ((v_consShareBioF.range(RMS,XXBIOF) NE 0) or p_trim)
                                       $ xxx1(XXBIOF)
                                       $ DATA(RMS,"BIOF",XXBIOF,"CUR")
                                       $ p_endoBioMarket)..
         v_consShareBioF(RMS,XXBioF)  =E=
    *
    *         --- fixed share (= blending quota relative)
    *
              Data(RMS,"QUTS",XXBIOF,"CUR")
    *
    *         -- sigmoid function, assumes that rather small shares are used even at high prices,
    *            "TURN" reflects the quota
    *
           +  (SIGMOID(p_bioDemPar(RMS,XXBioF,"Slope")
                                    *(v_consprice(RMS,XXBIOF) / SUM(fuelMatch(XXBioF,Fuel_Rows), Data(RMS,"CPRI",fuel_rows,"CUR"))
                                      -p_bioDemPar(RMS,XXBioF,"Turn"))))*p_bioDemPar(RMS,XXBioF,"Max");
    """
    return quts + dmax * SIGMOID(slope * (cp / fossil - turn))


def biofDem_(share, hcon, oil_fossil, oil_b):
    r"""biofDem_(RMS, XXBIOF) (l. 1421-1438): the biofuel use, share x HCON x oilEqu_fossil / oilEqu_b (kt; the total
    fuel use HCON fixed).

    CAPRI's GAMS, biofDem_ (l. 1421-1438):

     biofDem_(RMS,XXBioF) $ (DATA(RMS,"BIOF",XXBIOF,"CUR")
                            $ XXX1(xxBiof)
                            $ (v_biofProcQuant.range(RMS,XXBIOF) ne 0)
                            $ p_endoBioMarket )..
        v_biofProcQuant(RMS,XXBIOF)/(DATA(RMS,"BIOF",XXBIOF,"CUR")+0.1)
           =E=
    *
    *          --- share of biofuels in total fossil fuel demand,
    *              reflecting oil equivalent differences
    *
               v_consShareBioF(RMS,XXBioF)/p_oilEqu(XXbioF)
    *
    *          --- total demand for fossil fuels (diesel, gasoline) in oil equivalents
    *
                * SUM(fuelMatch(XXBioF,Fuel_Rows), Data(RMS,"HCON",fuel_rows,"CUR") * p_oilEqu(fuel_Rows))
                       /(DATA(RMS,"BIOF",XXBIOF,"CUR")+0.1);
    """
    return share * hcon * oil_fossil / oil_b

r"""CAPRI's land equations in the market (arm/market_model.gms l. 1657-1995, of the behavioural functions), the
SUPREMA land block of the step (supremaMrk on, capmod/set_global_variables.gms l. 386) outside the EU: the land
supply (LandSupplyMNL_), its market clearing with ProdNQ_'s land rows (LndSupplyEqualsDemand_), the rents
(rentFromProdpriceLand_), and the land-use change (luc_market on, l. 395): the land classes (LinkLuWithShares_) and
the transitions' estimation (luClassFinal_, luClassInitial_, FocLUC_ with derivativeOfGammaLUC_).

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026, the supply phase); this docstring keeps the block's overview, notation and departures.

Written: the land market of each non-EU CAPRI region (capri_mod/market/supply_ad.py land_residual_function, which
SupplyMixin.noneu_land_solve and the assembled system, market_system_ad.py, evaluate; the land types' levels of the
report, capri_mod/market/luc.py noneu_land_levels) and the land-use change of the report (luc.py final_classes,
solve_region).

In this project's notation, per non-EU CAPRI region (l the MNL's land types FORE, ARTIF, OLND, TCRP, FODFAL, FRUN;
the free ones TCRP, FODFAL, FRUN; rent0 the rents at calibration, dr the free rents' change, aLU and bLu CAPRI's MNL
parameters, A = ARTO - INLW; L0 + the price terms the land demand of ProdNQ_'s land rows, H its rent terms; for the
land-use change the classes c, the transitions j from f(j) to t(j) with annual factors a_j, the gamma priors alpha_j,
beta_j, the duals mu (final classes) and lambda (initial classes)):

    rentFromProdpriceLand_  rent_l = rent0_l + dr_l (the free types; FORE, ARTIF, OLND fixed)
    LandSupplyMNL_          land_l = A exp(aLU_l + sum_k bLu_lk rent_k) / sum_m exp(aLU_m + sum_k bLu_mk rent_k)
    LndSupplyEqualsDemand_  L0 + the price terms + H dr - land = 0 (the free types)
    LinkLuWithShares_       land_c = sum_k share_ck land_k
    luClassFinal_           sum_{j: t(j) = c} a_j x_j = land_c;   luClassInitial_  sum_{j: f(j) = c} a_j x_j = initial_c
    FocLUC_                 -beta_j + (alpha_j - 1) / x_j + mu_t(j) + lambda_f(j) = 0 (derivativeOfGammaLUC_ in it),
                            solved for x_j = (alpha_j - 1) / (beta_j - mu_t(j) - lambda_f(j))

Departures from CAPRI: the rows unscaled; the land supply in LandSupplyMNL_'s symmetric form, with the exponents
shifted by their largest (CasADi's mmax, NumPy's max): CAPRI's scenario step takes the asymmetric form instead
(p_useSymmetricMNL = 0 outside the baseline, l. 216-218; NumeraireLand_ and LandSupplyRatio_, l. 1758-1790, the
numeraire the land type with the largest exponent at the start values, arm/set_start_val.gms l. 617-621), equal in
exact arithmetic where the commitment term DATA LEVL_1 is 0 (to confirm on the step's data); the rents' change is the
land's producer price change (rentFromProdpriceLand_'s PSEd a constant, v_glucCostPerHa fixed: no LULUCF carbon tax
in the step); the land-use change a report, the duals' common shift fixed by the first initial class's lambda at 0
(luc.py), v_derivativeOfLogDensSlakMrkt at 0. Not in the model: Yield_, LandAgrFromYld_ and ScaleLandAgr_ (l.
1795-1861, the yields and land use per product, with ProdPriceFudge_), a recursive block: v_yield, v_landAgrTmp and
v_landAgr enter no other row of the step (market_model.gms l. 1685-1687, 1869-1872 are in LandAgrFromXX_ and LandAgr_,
which supremaMrk switches off); derivativeOfNormalLUC_ and derivativeOfSpikeLUC_ are empty (every transition has a
gamma prior, luc.py).
"""
from __future__ import annotations

import numpy as np


def rentFromProdpriceLand_(rent0, free, dr):
    r"""rentFromProdpriceLand_(RMS, luAgrMrk) (l. 1707-1722): the MNL's rents, rent0 with the free types' change dr
    added (the rent's change the land's producer price change; FORE, ARTIF, OLND at rent0). CasADi (an SX vector);
    rent0 numbers, free the free types' indexes.

    CAPRI's GAMS, rentFromProdpriceLand_ (l. 1707-1722):

      rentFromProdpriceLand_(RMS,luAgrMrk) $ (  DATA(RMS,luAgrMrk, "LEVL", "CUR")
                                                 $ (v_rentPerHa.range(RMS,luAgrMrk))
                                                 )..
         v_rentPerHa(RMS,luAgrMrk)  =E= sum(sameas(luAgrMrk,xx1Land),v_prodprice(RMS,xx1Land) + DATA(RMS,"PSEd",xx1Land,"CUR") )
     $iftheni.spam123 %supremaMrk%==on
                                     - (                                       v_glucCostPerHa(RMS,"crop")    $ sameas(luAgrMrk,"tcrp")
                                       +                                       v_glucCostPerHa(RMS,"crop")    $ sameas(luAgrMrk,"frun")
                                       +( p_shFstInSecMrk(RMS,"gras","fodfal")*v_glucCostPerHa(RMS,"grslnd")
                                         +p_shFstInSecMrk(RMS,"tgrs","fodfal")*v_glucCostPerHa(RMS,"crop")  ) $ sameas(luAgrMrk,"fodfal")
                                       ) $ p_carbonTax(RMS,"GLUC","perton") ;
     $endif.spam123
                                ;
    """
    import casadi as ca
    rent = ca.SX(ca.DM(np.asarray(rent0, float)))
    for k, i in enumerate(free):
        rent[i] = rent[i] + dr[k]
    return rent


def LandSupplyMNL_(avail, alu, B, rent):
    r"""LandSupplyMNL_(RMS, luEla) (l. 1737-1746): the land of each MNL type, avail softmax(aLU + bLu rent), the
    exponents shifted by their largest; avail ARTO - INLW (1000 ha), alu, B CAPRI's v_aLU and p_bLu (numbers), rent
    rentFromProdpriceLand_'s. CasADi. CAPRI's step takes NumeraireLand_ and LandSupplyRatio_ (the module's docstring).

    CAPRI's GAMS, LandSupplyMNL_ (l. 1737-1746):

      LandSupplyMNL_(RMS,luEla) $ (  DATA(RMS, "ARTO", "LEVL", "CUR")
                                  $  (v_land.range(RMS,luela) or v_aLU.range(RMS,luEla))
                                  $  p_useSymmetricMNL(RMS)
                                      )..
         v_land(RMS,luela)  =E= (DATA(RMS, "ARTO", "LEVL", "CUR") - DATA(RMS, "INLW", "LEVL", "CUR"))
                                *  exp(v_aLU(RMS,luEla)  + sum(luELa1,p_bLu(RMS,luEla,luEla1,"CUR") *v_rentPerHa(RMS,luEla1)) )
                                /sum(luEla2,
                                   exp(v_aLU(RMS,luEla2) + sum(luELa1,p_bLu(RMS,luEla2,luEla1,"CUR")*v_rentPerHa(RMS,luEla1)) )
                                    ) ;

    CAPRI's GAMS, NumeraireLand_ (l. 1758-1776):

      NumeraireLand_(RMS,luEla) $ (  DATA(RMS, "ARTO", "LEVL", "CUR")
                                  $  rms_luNum(rms,luEla)
                                  $  (v_land.range(RMS,luEla) or v_aLU.range(RMS,luEla))
                                  $  (not p_useSymmetricMNL(RMS))
                                  )..
         v_land(RMS,luELa)
       =E= (DATA(RMS, "ARTO", "LEVL", "CUR") - DATA(RMS, "INLW", "LEVL", "CUR") - sum(luELa1,DATA(RMS,luEla1, "LEVL_1", "CUR")))
         / (1+sum(rms_notluNum(rms,luEla2),
                  exp( v_aLU(RMS,luELa2)-v_aLU(RMS,luEla)
                     + sum(luELa1,(p_bLu(RMS,luELa2,luEla1,"CUR")-p_bLu(RMS,luEla,luEla1,"CUR"))*v_rentPerHa(RMS,luEla1)))))
        +  sum(rms_luNum(rms,luEla),DATA(RMS,luEla, "LEVL_1", "CUR"))
                     ;

    CAPRI's GAMS, LandSupplyRatio_ (l. 1779-1790):

      LandSupplyRatio_(RMS,luEla2) $ (  DATA(RMS, "ARTO", "LEVL", "CUR")
                                  $  (v_land.range(RMS,luEla2) or v_aLU.range(RMS,luEla2))
                                  $  rms_notluNum(rms,luEla2)
                                  $  (sum(rms_luNum(rms,luEla),v_land.lo(RMS,luEla)) gt 0)
                                  $  (not p_useSymmetricMNL(RMS))
                                  )..
           log( (v_land(RMS,luEla2)- DATA(RMS,luEla2, "LEVL_1", "CUR"))
              / sum(rms_luNum(rms,luEla),v_land(RMS,luEla)-DATA(RMS,luEla, "LEVL_1", "CUR")) )
      =E=   v_aLU(RMS,luEla2)-sum(rms_luNum(rms,luEla),v_aLU(RMS,luELa))
          + sum(luELa1,(p_bLu(RMS,luEla2,luEla1,"CUR")-sum(rms_luNum(rms,luEla),p_bLu(RMS,luEla,luEla1,"CUR")))*v_rentPerHa(RMS,luEla1))
           ;
    """
    import casadi as ca
    z = ca.DM(np.asarray(alu, float)) + ca.mtimes(ca.DM(np.asarray(B, float)), rent)
    e = ca.exp(z - ca.mmax(z))
    sh = e / ca.sum1(e)
    return float(avail) * sh


def LandSupplyMNL_levels(avail, alu, B, rent):
    r"""LandSupplyMNL_ (l. 1737-1746) in NumPy, for the report (luc.py noneu_land_levels): avail exp(z - max z) /
    sum exp(z - max z), z = aLU + bLu rent (the factors in this order, which rounds otherwise than LandSupplyMNL_'s
    CasADi form). CAPRI's GAMS: LandSupplyMNL_'s docstring."""
    z = np.asarray(alu, float) + np.asarray(B, float) @ rent
    e = np.exp(z - z.max())
    return avail * e / e.sum()


def LndSupplyEqualsDemand_(base, H, dr, S, free):
    r"""LndSupplyEqualsDemand_(RMS, luAgrMrk) (l. 1698-1701): the free types' land demand less their supply, base +
    H dr - S[free]: base ProdNQ_'s land rows at the prices (L0 + the price terms, an input), H their terms in the
    rents' change dr (numbers), S LandSupplyMNL_'s land. CasADi.

    CAPRI's GAMS, LndSupplyEqualsDemand_ (l. 1698-1701):

      LndSupplyEqualsDemand_(RMS,luAgrMrk) $ ( DATA(RMS,luAgrMrk, "LEVL", "CUR")
                                             $ sum(sameas(luAgrMrk,xx1Land),v_prodQuant.range(RMS,xx1Land)))..
         v_land(RMS,luAgrMrk)  =E= sum(sameas(luAgrMrk,xx1Land),v_prodQuant(RMS,xx1Land) );
    """
    import casadi as ca
    return base + ca.mtimes(ca.DM(np.asarray(H, float)), dr) - ca.vertcat(*[S[i] for i in free])


def LinkLuWithShares_(sh, lv, target):
    r"""LinkLuWithShares_(RMS, luMrkMod) (l. 1923-1930): the land of target, sum_k share_k land_k over its sources
    (sh {target: {source: share}}, lv {land type: 1000 ha}). Floats.

    CAPRI's GAMS, LinkLuWithShares_ (l. 1923-1930):

         LinkLuWithShares_(RMS,luMrkMod)                   $( (not RMSSUP(RMS))
                                                  $ (sum(xx1Land,v_prodQuant.range(RMS,xx1Land)) or p_trimlnd)
                                                  $ sum(luMrkMod1, p_shFstInSecMrk(RMS,luMrkMod,luMrkMod1))
                                               )..
       (v_land(RMS,luMrkMod)+ 1.E-6)
           /(data(RMS,luMrkMod,"levl","CUR")+ 1.E-6)
        =E= (sum(luMrkMod1, p_shFstInSecMrk(RMS,luMrkMod,luMrkMod1)* v_land(RMS,luMrkMod1))+ 1.E-6)/
            (data(RMS,luMrkMod,"levl","CUR")+ 1.E-6);
    """
    return sum(s * float(lv.get(src, 0.0)) for src, s in sh.get(target, {}).items())


def FocLUC_(al, be, A, z):
    r"""FocLUC_(rms, LUCpos) (l. 1960-1968) with derivativeOfGammaLUC_ (l. 1980-1985), solved for the transitions:
    x = (alpha - 1) / (beta - A' z), z the duals (mu of the final classes, lambda of the initial ones), A the classes'
    incidence of the transitions (To over From). NumPy. Returns (x, beta - A' z).

    CAPRI's GAMS, FocLUC_ (l. 1960-1968):

          FocLUC_(rms,LUCpos) $ ((not RMSSUP(RMS))
                                          $ (sum(xx1Land,v_prodQuant.range(RMS,xx1Land)) or p_trimlnd)
                                )..
       v_derivativeOfLogDensityMrkt(rms,LUCpos)
         + v_derivativeOfLogDensSlakMrkt(rms,LUCpos)
         + SUM(LUC_TO_LUclass(LUCpos,LUclass1),v_dualOfLUCtoCurClassMrkt(rms,LUclass1))
         + SUM(LUC_FROM_LUclass(LUCpos,LUclass),v_dualOfLUCfromIniClassMrkt(rms,LUclass))
       =E= 0;

    CAPRI's GAMS, derivativeOfGammaLUC_ (l. 1980-1985):

       derivativeOfGammaLUC_(rms,LUCpos)$( (not RMSSUP(RMS))
                                          $ (sum(xx1Land,v_prodQuant.range(RMS,xx1Land)) or p_trimlnd)
                                           $ [p_lucpriorMrk("distributionFamily",rms,LUCpos,"T") eq gammaDensity]
                                          )..
       v_derivativeOfLogDensityMrkt(rms,LUCpos)
       =E= -p_lucpriorMrk("beta",rms,LUCpos,"T") + (p_lucpriorMrk("alpha",rms,LUCpos,"T")-1) * 1/v_lucpos(rms,LUCpos);
    """
    den = be - A.T @ z
    return (al - 1.0) / den, den


def luClassFinal_Initial(A, fac, x, b):
    r"""luClassFinal_(rms, LUclass1) (l. 1938-1945) and luClassInitial_(rms, LUclass) (l. 1950-1955), stacked: A (fac
    x) - b, A the final classes' incidence over the initial ones', fac the annual factors, b the final land per class
    over the initial land. NumPy.

    CAPRI's GAMS, luClassFinal_ (l. 1938-1945):

         luClassFinal_(rms,LUclass1)$ ( (not RMSSUP(RMS))
                                      $ (sum(xx1Land,v_prodQuant.range(RMS,xx1Land)) or p_trimlnd)
                                   ) ..
       ( v_land(RMS,LUClass1) + 1.E-6)
           /(data(RMS,luclass1,"levl","CUR")+ 1.E-6)
         =E= (sum(luc_to_luClass(lucPos,LUclass1),v_lucpos(RMS,LUCpos)*p_lucAnnualFac(lucPos)) + 1.E-6)
           /(data(RMS,luclass1,"levl","CUR")+ 1.E-6)   ;

    CAPRI's GAMS, luClassInitial_ (l. 1950-1955):

         luClassInitial_(rms,LUclass) $ ((not RMSSUP(RMS))
                                          $ (sum(xx1Land,v_prodQuant.range(RMS,xx1Land)) or p_trimlnd)
                                          )..
       (  sum(luc_from_luClass(lucPos,LUclass), v_lucpos(RMS,LUCpos)*p_lucAnnualFac(lucPos)) + 1.E-6)
        / (p_lucPriorMrk("initialLandUse",RMS,LUclass,"T") + 1.E-6) =E= 1;
    """
    return A @ (fac * x) - b

r"""CAPRI's assignment of the market's prices to the supply models' data (arm/set_prices.gms, star 3.0), the part the
model writes as CAPRI's statement: the purchased feed bulks' unit values (l. 376-412, the Laspeyres version that
set_prices.gms sets on at l. 388). Called in a simulation with the trend point (simu_market.gms l. 236:
set_prices.gms 'TRD'), so %1 is "TRD" there: the bulk's price moves from CAPRI's 2030 baseline price by the
Laspeyres index of its market ingredients' Armington prices, times the share of the bulk they cover.

The rest of the file is written elsewhere: the outputs' unit values (l. 43-89: capri_mod/supply/supply_module.py,
K169), durum wheat's and sugar beet's (K168). The non-tradable fodders' UVAG scaled with FCER's (l. 435-458) are not
written: the supply model's objective has them only in its calibration step (supply_model.gms l. 4664-4668,
p_PMPStep1), and the envind files that read the feeds' UVAG run before the simulation's iterations (capmod.gms
l. 1097-1139, the loop from l. 1353).
"""
from __future__ import annotations


def DATA_UVAG_FEED_TRD_Y(uvag_trd, w, r, food_trd, food_y, grof_trd):
    r"""DATA(RMSSUP, "UVAG", FEED_TRD, "Y"): the bulk's unit value in the simulation, from the trend point's (l. 394-412;
    %1 = "TRD", the Laspeyres version, laspeyres_uvag on, l. 388).

    CAPRI's GAMS (arm/set_prices.gms l. 376-377, 394-412):

          DATA(RMSSUP,"FOOD",FEED_TRD,yTrdBas)
             = SUM(FEED_TO_O(FEED_TRD,MARR), DATA(RMSSUP,"FEDM",MARR,yTrdBas));
          ...
          DATA(RMSSUP,"UVAG",FEED_TRD,"Y") $ ( (DATA(RMSSUP,"FOOD",FEED_TRD,"TRD") GE 0.1)
                                             $ (DATA(RMSSUP,"FOOD",FEED_TRD,"Y") GE 0.1)
          $iftheni.las1 %laspeyres_uvag%==on
                                             $ SUM(FEED_TO_O(FEED_TRD,MARR), DATA(RMSSUP,"ARM1P",MARR,%1)*DATA(RMSSUP,"FEDM",MARR,%1))
          $endif.las1
                                             $ DATA(RMSSUP,"GROF",FEED_TRD,"TRD"))
        *
               =   DATA(RMSSUP,"UVAG",FEED_TRD,%1)
        *
          $iftheni.las2 %laspeyres_uvag%==on
        *
        *        --- times Laspeyres index of price changes of ingredients in simulation against %1, using reference situation weights
        *
               * [ 1 +   (  SUM(FEED_TO_O(FEED_TRD,MARR), DATA(RMSSUP,"ARM1P",MARR,"Y") * DATA(RMSSUP,"FEDM",MARR,%1))
                         /  SUM(FEED_TO_O(FEED_TRD,MARR), DATA(RMSSUP,"ARM1P",MARR,%1)  * DATA(RMSSUP,"FEDM",MARR,%1)) -1 )
        *
        *             -- weighted with share of covered ingredients on total in calibration point

                       * MIN(1,DATA(RMSSUP,"FOOD",FEED_TRD,"TRD")/DATA(RMSSUP,"GROF",FEED_TRD,"TRD")) ]

    Arguments in the model's terms: uvag_trd the bulk's price at the trend point (1 for the ratio to it); w the
    ingredients' weights ARM1P(TRD) x FEDM(TRD); r their Armington price ratios ARM1P(Y) / ARM1P(TRD) (DATA(RMSSUP,
    "ARM1P", XX, "Y") is the member state's market block's v_arm1Price, l. 34); food_trd and food_y the ingredients'
    feed at the trend point and in the simulation; grof_trd the bulk's total feed at the trend point. Where the
    condition fails CAPRI leaves the unit value as it was (the trend's, set before the simulation): uvag_trd."""
    sw = sum(float(x) for x in w)
    if not (food_trd >= 0.1 and food_y >= 0.1 and sw and grof_trd):
        return float(uvag_trd)
    las = sum(float(a) * float(b) for a, b in zip(r, w)) / sw
    return float(uvag_trd) * (1.0 + (las - 1.0) * min(1.0, float(food_trd) / float(grof_trd)))

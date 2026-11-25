r"""CAPRI's assignment of the market's prices to the supply models' data (arm/set_prices.gms, star 3.0), the part the
model writes as CAPRI's statement: the purchased feed bulks' unit values (l. 376-412, the Laspeyres version that
set_prices.gms sets on at l. 388). Called in a simulation with the trend point (simu_market.gms l. 236:
set_prices.gms 'TRD'), so %1 is "TRD" there: the bulk's price moves from CAPRI's 2030 baseline price by the
Laspeyres index of its market ingredients' Armington prices, times the share of the bulk they cover.

The outputs' unit values as relative changes (l. 43-96: DATA_UVAG_Y, DATA_UVAG_DWHE, block A5; called by
capri_mod/supply/supply_module.py and capri_mod/model.py, K168, K169). The non-tradable fodders' UVAG scaled with FCER's (l. 435-458) are not
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


def DATA_UVAG_Y(price_change, factor):
    r"""DATA(RMSSUP, "UVAG", MARR, "Y") as a relative change: an output's unit value moves by its market price's
    absolute change (UVAG + v_prodPrice - PPri), i.e. by the market's relative price change times PPri / UVAG at the
    trend point (factor; price_transmission_2030.csv, tools/build/build_price_transmission_2030.py); the paddy's and
    olives' the same through their factors (l. 81-89), the milks' with the PSEI (l. 66-74).

    CAPRI's GAMS (arm/set_prices.gms l. 44-47):

          DATA(RMSSUP,"UVAG",MARR,"Y") $ SUM(CAP_TO_TRD(MARR,XX), DATA(RMSSUP,"Ppri",XX,%1))
            = DATA(RMSSUP,"UVAG",MARR,%1) +
                  SUM(CAP_TO_TRD(MARR,XX),
                          v_prodPrice.L(RMSSUP,XX)-DATA(RMSSUP,"PPri",XX,%1) $ DATA(RMSSUP,"UVAG",MARR,%1));

    In this project's notation: dUVAG / UVAG0 = (dP / P0) (P0 / UVAG0). Departures from CAPRI: in relative changes with
    the factor at the trend point (the same change); the chickens' and the young animals' inputs (l. 101-109) not
    covered (the young animals have their own markets)."""
    return price_change * factor


def DATA_UVAG_DWHE(share, price_change):
    r"""DATA(RMSSUP, "UVAG", "DWHE", "Y") as a relative change: durum wheat's unit value moves by half of the wheat
    aggregate's relative price change (share 0.5); sugar beet's by sugar's (share 1, l. 93-96).

    CAPRI's GAMS (arm/set_prices.gms l. 59-61):

          DATA(RMSSUP,"UVAG","DWHE","Y") $ SUM(CAP_TO_TRD("DWHE",XX), DATA(RMSSUP,"Ppri",XX,%1))
            = DATA(RMSSUP,"UVAG","DWHE",%1) * (1. + 0.5 *
                 SUM(CAP_TO_TRD("DWHE",XX), (v_prodPrice.L(RMSSUP,XX)/DATA(RMSSUP,"PPri",XX,%1) -1.) ));

    In this project's notation: dUVAG / UVAG0 = s (P / P0 - 1). Departures from CAPRI: none (the shares,
    model_price_follows.csv, data read: capri_mod/data/definitions.py PRICE_FOLLOWS_SHARE)."""
    return share * price_change

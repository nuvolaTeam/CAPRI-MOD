r"""CAPRI's hand-over of the supply models' results to the market (arm/simu_calibration_to_supply.gms, star 3.0): the
marketed production from the gross production and the young animals' net supply.

capri_mod/coupling/bridge.py (BridgeBlock._marketed_supply) and young_animals.py (YoungAnimalBlock.
_young_animal_balance) call them.
"""
from __future__ import annotations


def p_itemsInIters_prod(grof, prod_grof):
    r"""p_itemsInIters(RMSSUP, "prod", XX_SUPPLY, STEP): a product's marketed production, the supply models' gross
    production times CAPRI's marketed over gross production at the calibration point (prod_grof,
    market_prod_grof_2030.csv; 0 where CAPRI has no marketed production: not marketed); rice and olive oil from the
    paddy and olive harvest the same way (l. 230-236). DATA Prod CUR takes it (l. 245-255).

    CAPRI's GAMS (arm/simu_calibration_to_supply.gms l. 221-226):

          p_itemsInIters(RMSSUP,"prod",XX_SUPPLY,STEP) $ ( (not xxOmYani(XX_SUPPLY))
                                                         $ p_itemsInIters(RMSSUP,"prod",XX_SUPPLY,"trd")
                                                         $ p_itemsInIters(RMSSUP,"grof",XX_SUPPLY,"trd"))
                    = SUM(CAP_TO_TRD(ROWS,XX_SUPPLY), p_itemsInIters(RMSSUP,"grof",ROWS,STEP))
        *        -- consider possible differences between PROD and GROF due to definitions and deviations from PROD targets in data_fit
                    *  p_itemsInIters(RMSSUP,"prod",XX_SUPPLY,"trd")/p_itemsInIters(RMSSUP,"grof",XX_SUPPLY,"trd");

    In this project's notation: Prod = GROF x (Prod / GROF)_cal. Departures from CAPRI: the ratio per member state from
    CAPRI's calibration point (data read, tools/build/build_market_prod_grof_2030.py), raw milk with its own rule (the
    caller's); its product set the model's."""
    return grof * prod_grof


def DATA_Prod_OMYANI(balance, grof, youngAnimUse):
    r"""DATA(RMSSUP, "Prod", OMYANI, "CUR"): a young-animal good's net supply, the supply models' production less their
    use of young animals; the caller adds unit by unit (balance, the sum of the units before, CAPRI's sum over
    MAP_RR(RMSSUP, RU)).

    CAPRI's GAMS (arm/simu_calibration_to_supply.gms l. 166-175):

          DATA(RMSSUP,"Prod",OMS,"CUR") $ (DATA(RMSSUP,"Prod",OMS,"CUR") or (DATA(RMSSUP,"Prod",OMS,"TRD") $ omYAni(OMS)))
             = p_itemsInIters(RMSSUP,"grof",OMS,STEP)
        *
        *    --- beware: "prod" for OMYANI is production, and not net put as used in market model
        *                 therefore, we have to subtract the young animal use
        *
              - sum(MAP_RR(RMSSUP,RU), v_youngAnimUse.L(RU,OMS)) $ omYAni(OMS)

        *                 (ensure that at least +eps is assigned for yanimarket_)
              + eps $ omYani(OMS);

    In this project's notation: N = sum_r (P_r - U_r). Departures from CAPRI: per young-animal market (the EU or each
    of its trade blocks), the units' production and use summed in turn (the same value up to rounding); no EPS added
    (0 is a value here)."""
    return balance + grof - youngAnimUse

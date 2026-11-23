r"""CAPRI's biofuel parameters (biofuel/def_biofuel_params.gms, star 3.0): the CES shares of the feedstocks.

capri_mod/market/biofuel.py (BiofuelMixin._biofuel_params) calls it.
"""
from __future__ import annotations


def p_dpCESBiof(biofProcQuant, prodBiof, BiofFeedCost_stock, BiofFeedCost, rho):
    r"""p_dpCESBiof(RMS, XX): a feedstock's CES share parameter in its biofuel, its use over the biofuel's output times
    (its feedstock cost over the biofuel's CES feedstock cost) ^ rho (arrays over the feedstocks).

    CAPRI's GAMS (biofuel/def_biofuel_params.gms l. 419-436):

              p_dpCESBiof(RMS,XX) $ (DATA(RMS,"Biof",XX,"CUR") $ v_biofFeedCost.l(RMS,XX) $ sum(Stock_to_fuel(XX,XXBiof),v_prodBiof.l(RMS,XXBioF)))
                 = (v_biofProcQuant.l(RMS,XX)
        *          * SUM(Stock_to_Fuel(XBioStock,XXBioF),DATA(RMS,"PRCB",XBioStock,"CUR"))
                   )
                   /[
                     SUM(Stock_to_fuel(XX,XXBiof),
        *
        *                 ---- a share of output production quantity
        *
                             v_prodBiof.l(RMS,XXBioF)
        *
        *                ---- times output prices divided by processing margin
        *                     exponent the processing margin
        *
                         * (v_biofFeedCost.l(RMS,XXBIOF) / v_biofFeedCost.l(RMS,XX)) ** p_rhoBioFuel(RMS,XXBIOF)

                       )
                     ];

    In this project's notation: dp_x = q_x / X (mu_x / mu_b)^rho. Departures from CAPRI: written as q / X x (mu_x /
    mu_b)^rho (CAPRI's q / (X (mu_b / mu_x)^rho), the same value up to rounding); the feedstock cost mu_x the price net
    of the by-products' value (the caller's)."""
    return biofProcQuant / prodBiof * (BiofFeedCost_stock / BiofFeedCost) ** rho

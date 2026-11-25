r"""CAPRI's market solution's report (reports/sol_market.gms, star 3.0): the biofuel industry's margin and the
tariff-rate quotas' rents.

capri_mod/market/welfare.py (WelfareMixin._welfare_biofuel_byproducts, _welfare_trade) calls them.
"""
from __future__ import annotations

import numpy as np


def DATA_ProcMarg_XXBIOF(PPRI0, price_ratio, BiofFeedCost):
    r"""DATA(RMS, "ProcMarg", XXBIOF, SIMY): the biofuel's processing margin, its producer price less its feedstock
    cost per t of biofuel (the producer price the reference's times the market's price ratio; at the reference the
    ratio is 1).

    CAPRI's GAMS (reports/sol_market.gms l. 694-695):

           DATA(RMS,"ProcMarg",XX,"%SIMY%")          = v_procMarg.L(RMS,XX);
           DATA(RMS,"ProcMarg",XXBIOF,"%SIMY%")      = v_prodPrice.l(RMS,XXBIOF) - v_BiofFeedCost.L(RMS,XXBIOF);

    Departures from CAPRI: the feedstock cost the CES cost of the model's biofuel state (mu_b), CAPRI's
    v_BiofFeedCost; the dairy margins (l. 697-700) are the dairy blocks'."""
    return PPRI0 * price_ratio - BiofFeedCost


def p_trqBilat_Rent(base, ta, ta_pref, ts, ts_pref, X, Q, fill):
    r"""p_trqBilat(RMTP, RMTP1, XX, "Rent", SIMY): a quota's rents per flow, before / 1000: the flows' wedge between
    their rates and the quota's preferential ones on the exporter price plus transport (base), at least 0, times the
    flows' share of the in-quota imports (X x min(1, Q / fill), fill the quota's imports); arrays over the quota's
    flows.

    CAPRI's GAMS (reports/sol_market.gms l. 1127-1135):

           p_trqBilat(RMTP,RMTP1,XX,"Rent","%SIMY%")    $  (  (p_trqBilat(RMTP,RMTP1,XX,"TrqNT","CUR") gt eps)
                                                            $ (p_trqBilat(RMTP,RMTP1,XX,"TrqNT","CUR") ne 1.E+10))
               =   MAX(0,   p_impPrice(RMTP,RMTP1,XX,"%SIMY%")

                          - (DATA(RMTP1,"PMrk",XX,"%SIMY%")+v_transpCost.l(RMTP,RMTP1,XX))*p_exchgRateChangeFactor(RMTP,RMTP1)
                                     * (1 + 0.01 * p_trqBilat(RMTP,RMTP1,XX,"TaPref","%SIMY%"))
                          - p_trqBilat(RMTP,RMTP1,XX,"TsPref","%SIMY%"))

                          * MIN(p_trqBilat(RMTP,RMTP1,XX,"ImportsR","%SIMY%"),p_trqBilat(RMTP,RMTP1,XX,"TrqNT","CUR")) * 0.001;

    In this project's notation: rent = max(0, base (ta - ta_pref) / 100 + (ts - ts_pref)) X min(1, Q / fill).
    Departures from CAPRI: the import price's wedge from the flow's rates (the model's sigmoid TRQ regime) and the
    in-quota imports shared over the quota's flows (CAPRI's min(imports, quota) per bilateral quota); no exchange rate
    change factor; NaN rates (no rate) read as 0."""
    u = np.nan_to_num(base * (ta - ta_pref) / 100.0) + np.nan_to_num(ts - ts_pref)
    return np.maximum(u, 0.0) * X * min(1.0, Q / fill)

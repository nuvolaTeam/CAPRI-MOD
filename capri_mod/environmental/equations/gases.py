r"""CAPRI's emission accounts (envind/gases.gms, star 3.0): the statements the accounts compute themselves.

Most of gases.gms's emission items are the supply model's equations of the first phase (N14a), which the accounts call
(capri_mod/supply/equations/supply_model/n2o.py GWPN2OSYN_, GWPN2OCRO_, GWPN2OMAN_, GWPN2OHIS_, GWPN2OLEA_; methane.py;
gwp.py GWPCO2LIM_, GWPCO2UREA_; air_water.py). This module holds the statements they do not write: the urea
substitution's effect on the CO2 from urea (CO2UREA).

Used by capri_mod/environmental/environmental_module.py (EnvironmentalModule.compute_indicators).
"""
from __future__ import annotations


def EMISCALC_CO2UREA(CO2UREA, FracUseFert, UreaSubst):
    r"""EMISCALC(RU, MCACT, A, "CO2UREA"): the CO2 from urea with the urea substitution, the base value CO2UREA (NMIN x
    the urea share x 44/28, supply/equations/supply_model/gwp.py GWPCO2UREA_) times max(FracUseFert - v, 0) /
    FracUseFert, FracUseFert the member state's urea share of mineral N (LitRev's p_fracUseFert, K93), v the share the
    option UreaSubst switches (v_Miti.l(RU, cropMiti, UreaSubst, NH3SYN)).

    CAPRI's GAMS (envind/gases.gms l. 833-835):

           EMISCALC(RU,MCACT,A,"CO2UREA",%1) = DATA(RU,MCACT,"NMIN",%1)  * Max(sum(map_rr(MS,RU),FracUseFert(MS,"ureum"))
        $ifi %ghgTechAmmEndog%==1      - v_Miti.L(RU,"cropMiti","UreaSubst","NH3SYN")
           ,0) * 44/28;

    In this project's notation: CO2UREA' = CO2UREA x max(f - v, 0) / f = NMIN x max(f - v, 0) x 44/28. Departures from
    CAPRI: none (CAPRI's statement written as a factor on the base value, the same product)."""
    return CO2UREA * max(FracUseFert - UreaSubst, 0.0) / FracUseFert

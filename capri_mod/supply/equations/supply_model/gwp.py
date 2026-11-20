r"""CAPRI's CO2 and global warming block (supply/supply_model.gms l. 3966-4015): CO2 from liming (GWPCO2LIM_) and
urea (GWPCO2UREA_), the CO2 subtotal (GWPCO2_) and the total GGWP (GWPTOT_), the emission tax's base.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

The model computes them in the accounts after the solve (environmental/ghg.py compute_ghg, environmental_module.py
compute_indicators); supply/ghg_tax.py takes GGWP for the emission tax (_ghg_total), option A as methane.py.

Not written: GWPCO2_ (l. 3968-3970), GCO2 = CO2LIM: the liming item enters GWPTOT_'s sum directly.

In this project's notation (kt CO2-eq):

    GWPCO2LIM_   (sum_c x_c) x l / 1000        l CAPRI's CO2LIM per ha of the region's UAAR (crop_co2_coef.csv)
    GWPCO2UREA_  M x u x 44/28                 M the mineral N (kt), u the member state's urea share
    GWPTOT_      the accounts' items' sum less CO2UREA (CAPRI: GCH4 x GWP + GN2O x GWP + GCO2 + NETTRD)

Departures from CAPRI: one liming coefficient per ha for every crop (CAPRI: EMISCALC(CO2LIM) per activity); the urea
share is fixed (CAPRI: IniShare - v_Miti(UreaSubst), the urea substitution option not built, KNOWN_ISSUES K93);
GWPTOT_ has no NETTRD (CAPRI's permits bought as a security device, priced at 10 x the tax). compute_ghg's own CO2UREA
(on the crops' base mineral rates) is replaced in compute_indicators by GWPCO2UREA_ on the balance's mineral N.
"""
from __future__ import annotations

from capri_mod.units import M_CO2, M_UREA_N


def GWPCO2LIM_(land, CO2LIM):
    r"""GWPCO2LIM_(r) (l. 3975-3980): the crop activities' levels summed (1000 ha) x CAPRI's liming CO2 per ha
    (kg) / 1000, kt CO2.

    CAPRI's GAMS, GWPCO2LIM_ (l. 3975-3980):

       GWPCO2LIM_(RUNR)..
            v_CO2EquEmis(RUNR,"CO2LIM")=E=
                   SUM( (MCACT,A)  $ (p_technFact(RUNR,MCACT,"LEVL",A)),
                                      v_actLevl(RUNR,MCACT,A) *   EMISCALC(RUNR,MCACT,A,"CO2LIM","Y")) *.001 ;
    """
    return land * CO2LIM / 1e3


def GWPCO2UREA_(M_kt, urea_share):
    r"""GWPCO2UREA_(r) (l. 3984-3990): the mineral N (kt) x the urea share x 44/28, kt CO2.

    CAPRI's GAMS, GWPCO2UREA_ (l. 3984-3990):

       GWPCO2UREA_(RUNR)..
            v_CO2EquEmis(RUNR,"CO2UREA")=E=
                   - v_netPutQuant(RUNR,"NITF")
                   * (p_ghgMiti(RUNR,"cropMiti","UreaSubst","NH3SYN","IniShare") - v_Miti(RUNR,"cropMiti","UreaSubst","NH3SYN"))
                   * 44/28;
    """
    return M_kt * urea_share * M_CO2 / M_UREA_N


def GWPTOT_(ghg_total, CO2UREA):
    r"""GWPTOT_(r) (l. 3997-4002), GGWP: the accounts' total over their items (CH4, N2O and CO2 in CO2-eq) less
    CO2UREA, which CAPRI's GCO2 leaves out (GWPCO2_: CO2LIM only).

    CAPRI's GAMS, GWPTOT_ (l. 3997-4002):

        GWPTOT_(RUNR)  ..
    *
            v_CO2EquEmis(RUNR,"GGWP")  =E= v_CO2EquEmis(RUNR,"GCH4") *p_globWarmPot("GCH4")
                                         + v_CO2EquEmis(RUNR,"GN2O") *p_globWarmPot("GN2O")
                                         + v_CO2EquEmis(RUNR,"GCO2")
                                         + v_CO2EquEmis(RUNR,"NETTRD");
    """
    return ghg_total - CO2UREA

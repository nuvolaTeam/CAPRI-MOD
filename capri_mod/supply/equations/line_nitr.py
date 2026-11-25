"""CAPRI's feed supplements (envind/line_nitr.gms; CAPRI star 3.0, run with %ghgTechLineNitr% on as in CAPRI's Green
Deal runs, pol_input/greendeal/refpol_endotech_all_sup.gms): the statements of the ration's fat limit, SupplementPerc_
(supply/supply_model.gms l. 608-633; equations/supply_model/feeding.py SupplementPerc_), the model's builders take.

The other statements of line_nitr.gms (the dosages, the effects on enteric CH4 and the requirements, the costs and their
calibration) are in tools/build/build_supplement_effects.py, which predates the equation style.

Used by tools/build/build_supplement_fat.py; p_ghgMiti_AComLN by capri_mod/environmental/environmental_module.py
(EnvironmentalModule.compute_indicators).
"""
from __future__ import annotations


def p_emisFeed_TotFAT_FEED(EE_FEED, p_DryMatterContent_FEED):
    r"""p_emisFeed(RU, CATACT, T, FEED, TotFAT): a feed bulk's fat per unit of fresh matter, its ether extract (% of dry
    matter, equations/digestibility.py p_digestPar_FEED) times its dry-matter content (l. 175-176).

    CAPRI's GAMS (envind/line_nitr.gms l. 173-176):

        *      Effects of Line interact with fat content of bulk FEEDs: SupplementPerc_  limits total fat intake, including from FEED bulks
        *      => we need the total fat content of feed bulks
           p_emisFeed(RU,CATACT,"T",FEED,"TotFAT") $ p_DryMatterContent(RU,FEED)
                 = p_digestPar(RU,CATACT,FEED,"EE") * p_DryMatterContent(RU,FEED)  / 100;

    In this project's notation: TotFAT(f) = EE(f) / 100 x DM(f), kg of fat per kg of the feed as fed (the unit of the
    rations, v_feedInpCoeff). Departures from CAPRI: none."""
    dm = float(p_DryMatterContent_FEED or 0.0)
    return float(EE_FEED) * dm / 100.0 if dm else 0.0


def p_ghgMiti_AComLN(rL, rN, sL, sN):
    r"""p_ghgMiti(ms_LiNi, CATACT, "AComLN", "CH4ENT", "QEmitt") in the model's form: the change of an animal's enteric
    CH4 factor where linseed and nitrate are fed to the same animals, rL rN min(sL, sN), rL and rN the options' relative
    changes of the factor (QEmitt / NOC - 1), sL and sN their shares of the herd; the caller adds it to 1 + sL rL + sN rN.

    CAPRI's GAMS (envind/line_nitr.gms l. 110-122):

           p_ghgMiti(ms_LiNi,CATACT,"AComLN","CH4ENT","QEmitt")
            $ (p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT","QEmitt") $ p_ghgMiti(ms_LiNi,CATACT,"AComLN","CH4ENT","MaxShare"))
            = p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT","QEmitt")
            * p_ghgMiti(ms_LiNi,CATACT,"LINE","CH4ENT","QEmitt")/p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT","QEmitt")
            * p_ghgMiti(ms_LiNi,CATACT,"Nitr","CH4ENT","QEmitt")/p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT","QEmitt")
            ;
           p_ghgMiti(ms_LiNi,CATACT,"AComLN","CH4ENT_3k","QEmitt")
            $ (p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT_3k","QEmitt") $ p_ghgMiti(ms_LiNi,CATACT,"AComLN","CH4ENT","MaxShare"))
            = p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT_3k","QEmitt")
            * p_ghgMiti(ms_LiNi,CATACT,"LINE","CH4ENT_3k","QEmitt")/p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT_3k","QEmitt")
            * p_ghgMiti(ms_LiNi,CATACT,"Nitr","CH4ENT_3k","QEmitt")/p_ghgMiti(ms_LiNi,CATACT,"NOC","CH4ENT_3k","QEmitt")
            ;

    In this project's notation: f = 1 + sL rL + sN rN + rL rN min(sL, sN). Departures from CAPRI: CAPRI's AComLN is an
    option of its own (its factor QEmitt(NOC) x QEmitt(LINE) / QEmitt(NOC) x QEmitt(Nitr) / QEmitt(NOC), the product of
    the two options' relative factors, adopted with its own share); the model applies that product on the overlap of the
    two options' shares, without a share of its own (the A0 inventory's porting differences)."""
    return rL * rN * min(sL, sN)

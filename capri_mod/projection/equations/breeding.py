r"""CAPRI's requirement functions of the dairy cow (envind/breeding.gms, star 3.0): the net energy apart from
lactation, maintenance (NEM), activity (NEA) and pregnancy (NEP), which the projection layer uses to scale the ration of
a cow whose milk yield is projected (ProjectionModule._project_livestock).

Departures from CAPRI: a fixed 600 kg cow (NEM the parameter REQ_NEM = 600^0.75 x 0.386 x 365,
capri_data/codes/model_parameters.csv; CAPRI p_meanLiveWgt per region and technology); NEA and NEP as shares of NEM.
"""
from __future__ import annotations


def p_animReqCopy_NEA_share(HD, Et):
    r"""p_animReqCopy(RU, DCOW, A, "NEA") over NEM: the activity's share of the maintenance energy, 0.17 (365 - HD)
    (1 - Et / 100) / 365, HD and Et the member state's housing days and the stable share of grazing time (MITERRA's
    p_rcEmissions, the items HD and Et of the dairy cows; 0 where CAPRI has no row).

    CAPRI's GAMS (envind/breeding.gms l. 190-192):

          p_animReqCopy(RU,DCOW,A,"NEA")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386)* 0.17
             * (365-p_rcEmissions(RU,"DAICOW_L","HD"))*(1-p_rcEmissions(RU,"DAICOW_L","Et")/100);

    In this project's notation: NEA / NEM = 0.17 (365 - HD)(1 - Et / 100) / 365, NEM = W^0.75 x 0.386 x 365 (l. 185-186).
    Departures from CAPRI: none (the share of NEM; the cow's weight in NEM)."""
    return 0.17 * (365.0 - HD) * (1.0 - Et / 100.0) / 365.0


def p_animReqCopy_ENNE_nonlact(NEM, NEA_share):
    r"""p_animReqCopy(RU, DCOW, A, "ENNE") less the lactation's NEL: NEM + NEP + NEA = NEM (1.1 + NEA / NEM), NEP = 0.10
    NEM, NEA = NEM x NEA_share (p_animReqCopy_NEA_share).

    CAPRI's GAMS (envind/breeding.gms l. 185-186):

          p_animReqCopy(RU,DCOW,A,"NEM")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386) * 365.;

    CAPRI's GAMS (envind/breeding.gms l. 195-196):

          p_animReqCopy(RU,DCOW,A,"NEP")  $ p_technFact(RU,DCOW,"LEVL",A)
            =  ( p_meanLiveWgt(RU,DCOW,A)**0.75 * 0.386)* 0.10 * 365.;

    CAPRI's GAMS (envind/breeding.gms l. 198):

          p_animReqCopy(RU,DCOW,A,"ENNE") $ p_technFact(RU,DCOW,"LEVL",A) = SUM(SUBENE, p_animReqCopy(RU,DCOW,A,SUBENE));

    In this project's notation: ENNE - NEL = NEM + 0.10 NEM + NEM x NEA_share. Departures from CAPRI: NEM the fixed 600
    kg cow's (the module's docstring)."""
    return NEM * (1.1 + NEA_share)

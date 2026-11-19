"""CAPRI's nutrient need per ha of a crop in the simulation year, as fert/fertned.gms sets it (K185).

CAPRI's GAMS (fert/fertned.gms l. 98-99, 180-192 and 233; run in the simulation year by
capmod/def_fert_and_requirements.gms l. 134, $BATINCLUDE 'fert/fertned.gms' MCACT, after l. 125 has set
DATA(RS,MCACT,"O_HP","Y") = 0 for the crops with a level and l. 93-96 of fertned.gms has rebuilt O_HP from the crop's
main outputs, PACT_TO_Y):

    DATA(RS,%pacts%,FNUT,%Y%) $  p_dataCopy(RS,%pacts%,"LEVL",%Y%) = 0;
    DATA(RS,%pacts%,FNUT,%Y%) $  (not p_dataCopy(RS,%pacts%,"O_HP",%Y%)) = 0;

    DATA(RS,%pacts%,FNUT,%Y%) $ (p_dataCopy(RS,%pacts%,"LEVL",%Y%) $ p_dataCopy(RS,%pacts%,"O_HP",%Y%))
         = MIN(MAXF(FNUT)*(1 + 1 $ doubleMaxf(%pacts%))
             ,SUM( PACT_TO_Y(%pacts%,curRows),
                 MAX(15.0,  p_dataCopy(RS,%pacts%,"O_HP",%Y%)*0.001 * p_cropNeed(RS,curRows,FNUT,%Y%)
                          + p_dataCopy(RS,%pacts%,"STRA",%Y%)*0.001 * p_cropNeed(RS,"STRA",FNUT,%Y%))));

    DATA(RS,"FALL",FNUT,%Y%) = 0.0;

NUTNED_ (supply/supply_model.gms l. 1103-1145) then sums v_actLevl x DATA(crop, FNUT, "Y") x ... over the crops of
each nutrient group, so a crop without a main output (no O_HP: fallow FALL and set-aside VSET, which are not in
PACT_TO_Y, sets.gms l. 5534-5613) adds nothing to its group's need. CAPRI's own margins confirm it: at the 2030 base the
first-order condition of FALL and VSET holds without a need term (reports/margcr.gms: D_AREA + D_PMPL + D_PREM + D_NUT
= 0, D_PROV = 0) in every interior case, including the regions where sim_ini's DATA carries an NITF for them (DE B3:
4.66 kg N/ha), while their group OAFC has positive duals (TEXT, TOBA).

In this project's notation, for crop a of region r and nutrient n:

    need(r, a, n) = need_data(r, a, n)   if O_HP(r, a) > 0
                    0                    otherwise

with need_data the crop's need per ha of CAPRI's 2030 reference (npk_crop_coefs_2030.csv, need_kg_ha: CAPRI's
reported DATA(crop, NITF | PHOF | POTF), net of fixation, which for a crop with a main output is fertned's value) and
O_HP the crop's main-output yield (the region's yields, t/ha). The model's data have area without a main-output yield
only for FALL and VSET (yields.csv: 247 and 166 regions).

Departures from CAPRI: none in the rule. The fertned value itself (the MIN / MAX of l. 180-192) is not recomputed
here: the need of a crop with a main output is CAPRI's reported 2030 value, and its yield response is the NLP's
(capri_mod/fert/npk.py, yield_shares).
"""
from __future__ import annotations


def DATA_FNUT(need_data: float, O_HP: float) -> float:
    """CAPRI's DATA(RS, crop, FNUT, "Y") after fertned.gms (l. 98-99, 180-192, 233): the crop's nutrient need per ha,
    zero for a crop without a main-output yield O_HP (fallow, set-aside); kg per ha."""
    return float(need_data) if float(O_HP or 0.0) > 0.0 else 0.0

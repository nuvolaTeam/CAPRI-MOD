r"""CAPRI's market balances (supply/supply_model.gms l. 4543-4615): SUPBAL_, the balance of each output and input of
the region.

CAPRI's GAMS statement of each equation is in the docstring of the function that writes it (the project lead's
decision of 19 November 2026); this docstring keeps the block's overview, notation and departures.

Written: SUPBAL_ for the non-tradable fodder (CAPRI's FODDO: grass, fodder maize, other fodder), the fodder balances
of the regional QP (supply/livestock.py _fodder_rows, rows "fodder_<feed>") and their equalities in the regional NLP
(CapriRegionalNLP.__init__, with FEDUSE_'s feed use). For the tradable outputs and inputs SUPBAL_ defines the sales
v_netPutQuant, which the model substitutes into the objective: each activity's outputs at their prices in its net
revenue (supply_module._compute_net_revenues), the feeds bought at their prices in QUADRF_ (objective.py), the young
animals at the change of their prices (INPANI_'s use per head; supply/livestock.py _apply_young_animal_prices).

In this project's notation, for a fodder f with its crop c (area x_c, usable fodder u_c per ha) and the animals a
(herd h_a, use per head t_a; in the NLP the flexible part FEDUSE_'s F / 1000):

    SUPBAL_ (fodder):  sum_a t_a h_a - u_c x_c = G,   G the base gap (base rations x base herds - u_c x base area)

Departures from CAPRI (docs/FODDER_BALANCE.md): u_c is CAPRI's base fodder use over the base fodder area (its on-farm
share, p_onFarmShare, and the base yield embedded; CAPRI's production moves with v_yldMit); the base gap G is held as a
constant (K36, K46: CAPRI's baseline holds its balances); the QP's right-hand side has a tolerance of 1e-9 x the row's
scale.
"""
from __future__ import annotations

import numpy as np


def SUPBAL_fodder(width, use, crops):
    r"""SUPBAL_(r, FODDO) (l. 4551-4611) as the regional QP's fodder balance row over width columns: the use per head
    on the animals' columns (use: {column: t per head}), minus the usable fodder per ha on the crops' (crops: {column:
    t per ha}). The right-hand side: SUPBAL_fodder_rhs.

    CAPRI's GAMS, SUPBAL_ (l. 4551-4611):

        SUPBAL_(RUNR_OMS_IN_SUPBAL(RUNR,OMS) %addtimedim%)  ..
    *
    *                                      --- sales or purchases
    *                                          (exemption: fodder which is not tradeable)
    *
             v_netPutQuant(RUNR,OMS)    $ ( (NOT FODDO(OMS)) or ((p_PMPStep1 eq 1) $ (NOT SAMEAS(OMS,"STRA")))
                                             or (p_exoDemand(RUNR,"UVAG",OMS) $ (p_PMPStep1 eq 1)))
    *
    *                                      --- young animals needed in regions
    *                                          (defined in equation INPANIE_)
    *
             + v_youngAnimUse(RUNR,OMS)  $ OMYANI(OMS)
    *
    *                                      --- non-tradable feed use (FGRA,FOFA ...)           (Foodi    OMS)
    *                                          (defined in equation FEDUSE_)  1:1 relation for  FGRA  to GRAS, FMAI to MAIF ....
             + SUM((FEED_TO_O(FODDI,OMS)), v_feedQuantReg(RUNR,FODDI  %addtimedim%))
    *
    *                                      --- feed use of tradables bulks (FCER,FPRO ...)
    *                                          (defined in equation FEDUSE_)
             +  v_feedQuantReg(RUNR,OMS %addtimedim%) $ feedRows(OMS)
    $iftheni.Pes29 %PEST_DISAGG%==ON
             + v_pestiQuantReg(RUNR,OMS)  $ pesModDis(OMS)
    *
    $endif.Pes29
             + p_exoDemand(RUNR,"DEMD",OMS)
    *
                                =E=
    *
    *                                      --- total output: activity level * output coefficient
    *                                      ---               * technology factor for alternative
    *
            SUM( (MPACT,A) $ (PACT_TO_O(MPACT,OMS) $ p_technFact(RUNR,MPACT,"LEVL",A)),
                v_actLevl(RUNR,MPACT,A) * (%data%(RUNR,MPACT,OMS,"Y")
    $iftheni.till6 %ghgAbatement%==on
    *      --- mitigation effect on yield considered
                 * v_yldMit(RUNR,MPACT)
    $endif.till6
    *      --- endogenous pesticide use considered
    $iftheni.Pes1 %PEST_DISAGG%==ON
                 * (1 +(v_yldPestFac(RUNR,mPact,A)-1) $ (v_yldPestFac.range(RUNR,mPact,A) $ cact(mpact)))
    $endif.Pes1
                 * (p_technFact(RUNR,MPACT,OMS,A)+1.) * 0.001)
    $iftheni.icow7 %ghgAbatement%==on
    *                                          -- possible modification by mitigation option genet_rep that reduces replacement rate
                 * (1+v_Miti(RUNR,MPACT,"genet_rep","anyFemCat")*p_ghgMiti(RUNR,MPACT,"genet_rep","othImpact","BEEF")
                                                               $ (PACT_TO_I(MPACT,"ICOW") $ SAMEAS(OMS,"BEEF")))
    *                                          -- possible modification by mitigation option genet_yld that increases milk yields
                 * (1+v_Miti(RUNR,MPACT,"genet_yld","mlkYld")*p_ghgMiti(RUNR,MPACT,"genet_yld","othImpact","COMI")
                                                               $ (PACT_TO_Y(MPACT,"COMI") $ SAMEAS(OMS,"COMI")))
    $endif.icow7
               )
    *                                      --- keep seed and v_lossQuant in
    *                                      --- constant proportion
    *
                                                   * (1. - p_onFarmShare(RUNR,OMS))
    $ifi %consLCA% == ON     - p_addLoss(RUNR,OMS) * (1. - p_onFarmShare(RUNR,OMS))
    ;
    """
    row = np.zeros(width)
    for j, t in use.items():
        row[j] = t
    for j, u in crops.items():
        row[j] = -float(u)
    return row


def SUPBAL_fodder_rhs(row_base, x0, scale):
    r"""SUPBAL_fodder's right-hand side: the balance's gap at the base (the row at the base rations, row_base, at the
    base levels x0) + 1e-9 x the row's scale (a tolerance; not in CAPRI). CAPRI's GAMS: SUPBAL_fodder's docstring."""
    return float(row_base @ x0) + 1e-9 * scale


def SUPBAL_fodder_use(row_scaled, v_feedQuantReg, inv_rs):
    r"""SUPBAL_ for a non-tradable fodder in the regional NLP, scaled by the row's scale rs: the QP's row (its animals'
    cells replaced, the fixed feeds' FEDUSE_ on the herd columns) / rs, + the flexible feeds' FEDUSE_ sum (CAPRI's
    v_feedQuantReg, 1000 t) / rs; the builder makes it an equality at the right-hand side / rs. CAPRI's GAMS:
    SUPBAL_fodder's docstring."""
    return row_scaled + v_feedQuantReg * inv_rs

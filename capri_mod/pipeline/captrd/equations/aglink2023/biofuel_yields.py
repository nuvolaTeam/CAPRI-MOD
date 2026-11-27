r"""The biofuels' yields (p_BFyld) and the feedstock quantities (baseline/load_aglink2023dgAgri.gms; moved from
capri_mod/pipeline/captrd/equations/load_aglink2023dgAgri.py as they were, 26 November 2026).
"""
from __future__ import annotations

import math




def p_BFyld(qp, bf):
    r"""p_BFyld(feedstock, fuel, agYears) where the EU's feedstock is used for biofuels: the EU's biofuel production
    from it over that use.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 508-509):

          p_BFyld('WT','ET',agYears) $ p_aglink('EUN','BF','WT',agYears)
            = p_aglink('EUN','QP..WT','ET',agYears)/p_aglink('EUN','BF','WT',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 515-516):

          p_BFyld('MA','ET',agYears) $ p_aglink('EUN','BF','MA',agYears)
            = p_aglink('EUN','QP..MA','ET',agYears)/p_aglink('EUN','BF','MA',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 518-519):

          p_BFyld('OCG','ET',agYears) $ p_aglink('EUN','BF','OCG',agYears)
            = p_aglink('EUN','QP..OCG','ET',agYears)/p_aglink('EUN','BF','OCG',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 528-530):

          p_BFyld('CG','ET',agYears) $ p_aglink('EUN','BF','CG',agYears)
            = p_aglink('EUN','QP..CG','ET',agYears)
              /p_aglink('EUN','BF','CG',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 537-538):

          p_BFyld('SBE','ET',agYears) $ p_aglink('EUN','BF','SBE',agYears)
            = p_aglink('EUN','QP..SBE','ET',agYears)/p_aglink('EUN','BF','SBE',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 540-541):

          p_BFyld('VL','BD',agYears) $ p_aglink('EUN','BF','VL',agYears)
            = p_aglink('EUN','QP..VL','BD',agYears)/p_aglink('EUN','BF','VL',agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return qp / bf


def p_BFyld_copy(value):
    r"""p_BFyld('CG', 'ET', .) without a value: wheat's; p_BFyld('WTS', 'ET', .): wheat's.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 534-535):

          p_BFyld('CG','ET',agYears) $ (not p_BFyld('CG','ET',agYears))
            = p_BFyld('WT','ET',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 544-544):

          p_BFyld('WTS','ET',agYears) = p_BFyld('WT','ET',agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value


def p_aglink_QP_CG(ma, ocg):
    r"""p_aglink(agRegs, 'QP..CG', 'ET', agYears) without a value: from maize and the other coarse grains.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 525-526):

          p_aglink(agRegs,'QP..CG','ET',agYears) $ (not p_aglink(agRegs,'QP..CG','ET',agYears))
            = p_aglink(agRegs,'QP..MA','ET',agYears) + p_aglink(agRegs,'QP..OCG','ET',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return ma + ocg


def p_aglink_QP_feedstock(bf, yld):
    r"""p_aglink(agEurop, 'QP..WT' / 'QP..WTS' / 'QP..CG' / 'QP..SBE' / 'QP..VL', ., agYears) (the EU's own but WTS
    kept): the feedstock's biofuel use times the EU's yield.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 554-555):

          p_aglink(agEurop,'QP..WT','ET',agYears) $ (not  sameas(agEurop,'EUN'))
            = p_aglink(agEurop,'BF','WT',agYears)*p_BFyld('WT','ET',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 557-558):

          p_aglink(agEurop,'QP..WTS','ET',agYears)
            = p_aglink(agEurop,'BF','WT',agYears)*p_BFyld('WTS','ET',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 560-561):

          p_aglink(agEurop,'QP..CG','ET',agYears) $ (not  sameas(agEurop,'EUN'))
            = p_aglink(agEurop,'BF','CG',agYears)*p_BFyld('CG','ET',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 563-564):

          p_aglink(agEurop,'QP..SBE','ET',agYears) $ (not  sameas(agEurop,'EUN'))
            = p_aglink(agEurop,'BF','SBE',agYears)*p_BFyld('SBE','ET',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 566-567):

          p_aglink(agEurop,'QP..VL','BD',agYears) $ (not  sameas(agEurop,'EUN'))
            = p_aglink(agEurop,'BF','VL',agYears)*p_BFyld('VL','BD',agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return bf * yld

r"""CAPTRD's statements of baseline/load_aglink2023dgAgri.gms (CAPRI star 3.0, captrd.gms l. 593): Aglink-COSIMO's
cube rebooked (p_aglinkOri), the European regions' data (p_aglink) and the biofuels' feedstock yields (p_BFyld), the
mapping to CAPRI's regions, columns and rows (p_aglinkTrd) stored as p_result(..., "DGAgri"), and the population of the
macro data (p_SSPAglink, p_aglinkMacro), as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block or repeated form, named after the assigned symbol). capri_mod/pipeline/captrd/aglink.py (read_aglink, eu_data,
to_capri, dgagri) and macro.py (inha) hold the loops over the regions, positions and years, the mappings and the
conditions, and call them; the arithmetic is the port's, so the outlook is unchanged. NA is float('nan'); _nz is GAMS's
truth of a value (nonzero, NA included).
"""
from __future__ import annotations

import math


def p_aglinkOri(value):
    r"""p_aglinkOri(c, m, p, simyy) of the cube's entries not booked as in 2022 (p_dbvar); Aglink 2019's fish (FH,
    p_fish) where it has a value.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 160-160):

         p_aglinkOri(c,m,p,simyy) $ (not aglink2022_booking(p,m)) =  p_dbvar(c,p,m,simyy) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 208-210):

          p_AGLINKOri(AGLINKRegions,AGLINKCOLS,"FH",AGLINKYears)
            $ p_fish(AGLINKRegions,AGLINKCOLS,"FH",AGLINKYears)
          = p_fish(AGLINKRegions,AGLINKCOLS,"FH",AGLINKYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value


def p_aglinkOri_rebooked(values):
    r"""p_aglinkOri(c, m11, p11, simyy) of the 2020 booking without a value: the 2022 booking's biofuel production by
    feedstock summed (map_for_rebooking).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 162-163):

         p_aglinkOri(c,m11,p11,simyy) $ ((not p_aglinkOri(c,m11,p11,simyy)) $ aglink2020_booking(p11,m11))
         = sum(map_for_rebooking(p,m,p11,m11) $ aglink2022_booking(p,m), p_dbvar(c,p,m,simyy)) ;

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them); the domain condition and the loops in the caller (aglink.py)."""
    t = 0.0
    for v in values:
        t += v
    return t


def p_aglink(value, demand_pos):
    r"""p_aglink(agEurop, agCols, agRows, agYears) of the rows and years without irregular data (NA, UNDF):
    p_aglinkOri, not below zero for the demand positions (QCandPosA).

    demand_pos: the column is in QCandPosA.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 231-234):

          p_aglink(agEurop,agCols,agRows,agYears) $ (not sum(iregularData(agEurop,agCols1,agRows,agYears),1))
              = p_aglinkOri(agEurop,agCols,agRows,agYears)        $ (NOT QCandPosA(agCols))
        *pw     after finding negative OU and QC for ET in 2000+2001:
              + MAX(0,p_aglinkOri(agEurop,agCols,agRows,agYears)) $      QCandPosA(agCols);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return _max0(value) if demand_pos else value


def p_aglink_WLD_XP(xp, xr):
    r"""p_aglink('WLD', 'XP', agBioF / 'OIL', agYears): the world prices of the biofuels and of oil times the EU's
    exchange rate.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 238-238):

          p_aglink('WLD','XP',agBioF,agYears) = p_aglinkOri('WLD','XP',agBioF,agYears)*p_aglinkOri('EUN','XR','ME',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 239-239):

          p_aglink('WLD','XP','OIL',agYears)  = p_aglinkOri('WLD','XP','OIL' ,agYears) *p_aglinkOri('EUN','XR','ME',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return xp * xr


def p_aglink_sum(values):
    r"""p_aglink('EUN', agColsSummable, ., .) without a value: its parts' (agEUparts) for all rows, wheat and raw milk;
    p_aglink(agEUreg, ., 'CG', .) the coarse grains, (., ., 'WT', .) the wheats, ('FE', 'OM') the meals,
    ('BF', 'CG') the coarse grains' biofuel use, ('QP..NAGR', agBioF) the non-agricultural sources (bioORES),
    ('QP', agBioF) the biofuel sources without duplicates: the parts' or members' summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 246-247):

          p_aglink('EUN',agColsSummable,agRows,agYears) $( not p_aglink('EUN',agColsSummable,agRows,agYears) )
           = sum(agEUparts,p_aglink(agEUparts,agColsSummable,agRows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 282-283):

          p_aglink(agEUreg,agColsSummable,'CG',agYears)
            = sum(aglinkCG, p_aglink(agEUreg,agColsSummable,aglinkCG,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 298-299):

          p_aglink('EUN',agColsSummable,aglinkWT,agYears) $ (not p_aglink('EUN',agColsSummable,aglinkWT,agYears))
           = sum(agEUparts,p_aglink(agEUparts,agColsSummable,aglinkWT,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 303-304):

          p_aglink(agEurop,agColsSummable,'WT',agYears) $ (not p_aglink(agEurop,agColsSummable,'WT',agYears))
            = sum(aglinkWT, p_aglink(agEurop,agColsSummable,aglinkWT,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 343-344):

          p_aglink('EUN',agColsSummable,'MK',agYears) $ (not  p_aglink('EUN',agColsSummable,'MK',agYears))
            = sum(agEUparts, p_aglink(agEUparts,agColsSummable,'MK',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 373-374):

           p_aglink(agEUparts,'FE','OM',agYears) $ (not p_aglink(agEUparts,'FE','OM',agYears))
                    = sum(agRows $ agRowsAggregate_map('OM',agRows), p_aglink(agEUparts,'FE',agRows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 522-523):

          p_aglink(agRegs,'BF','CG',agYears) $ (not p_aglink(agRegs,'BF','CG',agYears))
            = sum(AgRows $ agRowsAggregate_map('CG',agRows),  p_aglink(agRegs,'BF',AgRows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 688-689):

          p_aglink(agEurop,'QP..NAGR',agBiof,agYears) $  (not p_aglink(agEurop,'QP..NAGR',agBiof,agYears))
            = sum(aglinkCols_bioMap("bioORES",AGLINKCols), p_aglink(agEurop,AGLINKCols,agBiof,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 719-720):

           p_aglink(agEurop,'QP',agBiof,agYears)
              = sum(bioSrcNoDupl, p_aglink(agEurop,bioSrcNoDupl,agBiof,agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(values)


def p_aglinkTrd_sum(values):
    r"""p_aglinkTrd(EuropReg, balPos / GRPC, CERE / OILS, .) of the groups without a value: the members'
    summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1298-1300):

          p_aglinkTrd(EuropReg,balPos,GRPR,years) $ ( (sameas(GRPR,'CERE') or  sameas(GRPR,'OILS'))
                                                    $ (not p_aglinkTrd(EuropReg,balPos,GRPR,years) ))
            = sum(ROWS_TO_G(rows,GRPR), p_aglinkTrd(EuropReg,balPos,rows,years));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1302-1304):

          p_aglinkTrd(EuropReg,GRPC,'LEVL',years) $ ( (sameas(GRPC,'CERE') or  sameas(GRPC,'OILS'))
                                                    $ (not p_aglinkTrd(EuropReg,GRPC,'LEVL',years) ))
            = sum(CROPC_TO_G(cact,GRPC), p_aglinkTrd(EuropReg,cact,'LEVL',years));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(values)


def p_aglink_FOA(foa, fo, foa_pos, fo_pos, wst_dist):
    r"""p_aglink(agRegs, 'FOA', agRows, agYears) where QC is not NA: food available, else its positions (FOAposA), else
    food use's positions (FOposA) plus distribution waste.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 250-254):

         p_aglink(agRegs,'FOA',agRows,agYears) $ ( p_aglink(agRegs,'QC',agRows,agYears) ne NA)
            = p_aglink(agRegs,'FOA',agRows,agYears)
                 +(sum(FOAposA,p_aglink(agRegs,FOAposA,agRows,agYears)) $(not p_aglink(agRegs,'FOA',agRows,agYears)))
                 +((sum(FOposA,p_aglink(agRegs,FOposA,agRows,agYears))+p_aglink(agRegs,"WST..DIST",agRows,agYears))
                         $((not p_aglink(agRegs,"FOA",agRows,agYears))$ (not p_aglink(agRegs,"FO",agRows,agYears))));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return foa + (sum(foa_pos) if not _nz(foa) else 0.0) \
        + ((sum(fo_pos) + wst_dist) if (not _nz(foa) and not _nz(fo)) else 0.0)


def p_aglink_QC_WYP(qc_eun, qp, qp_eun, qc):
    r"""p_aglink(agEUparts, 'QC', 'WYP', agYears) where neither QP is NA: the EU's whey powder demand by the part's
    production share, where both produce and the part has no demand.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 260-265):

          p_aglink(agEUparts,'QC','WYP',agYears) $ ( (p_aglink(agEUparts,'QP','WYP',agYears) ne NA)
                                                   $ (p_aglink('EUN','QP','WYP',agYears) ne NA))
            = p_aglink('EUN','QC','WYP',agYears)
              *( p_aglink(agEUparts,'QP','WYP',agYears)/p_aglink('EUN','QP','WYP',agYears) )
                $ ( ((p_aglink(agEUparts,'QP','WYP',agYears)*p_aglink('EUN','QP','WYP',agYears)) ne 0)
                and (p_aglink(agEUparts,'QC','WYP',agYears)eq 0) ) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    cond = (qp * qp_eun != 0) and (qc == 0)
    return qc_eun * (qp / qp_eun) if cond else 0.0


def p_aglink_copy(value):
    r"""p_aglink(agEurop, ., ., .) of the other European regions: the aggregates OCG, OOS and WT copied to their
    members; QC of sugar beet and raw milk: production; FE of raw milk: FU where its positions are zero; FO of the
    fossil fuels and of the EU regions' rows without a breakdown: QC; the EU's parts' fuel prices: the EU's.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 287-287):

          p_aglink(agEurop,agCols,aglinkOCG,agYears) $ (not agEUreg(agEurop)) = p_aglink(agEurop,agCols,'OCG',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 290-290):

          p_aglink(agEurop,agCols,'RP',agYears) $ (not agEUreg(agEurop)) = p_aglink(agEurop,agCols,'OOS',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 291-291):

          p_aglink(agEurop,agCols,'SF',agYears) $ (not agEUreg(agEurop)) = p_aglink(agEurop,agCols,'OOS',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 308-308):

          p_aglink(agEurop,agCols,aglinkWT,agYears) $ (not agEUreg(agEurop)) = p_aglink(agEurop,agCols,'WT',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 312-312):

          p_aglink(agEurop,'QC','SBE',agYears) = p_aglink(agEurop,'QP','SBE',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 323-323):

          p_aglink(agEurop,'QC','MK',agYears) = p_aglink(agEurop,'QP','MK',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 332-337):

          p_aglink(agEurop,'FE','MK',agYears) $ ( (not  sameas(agEurop,'EUN'))
                                                $ p_aglink(agEurop,'FU','MK',agYears)
                                                $ ((p_aglink(agEurop,'FE','MK',agYears)
                                                   +p_aglink(agEurop,'OU','MK',agYears)
                                                   +p_aglink(agEurop,'QP..DS','MK',agYears)) eq 0))
            = p_aglink(agEurop,'FU','MK',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 359-359):

          p_aglink(agEurop,'FO',agFosF,agYears) = p_aglink(agEurop,'QC',agFosF,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 389-391):

          p_aglink(agEUreg,'FO',agRows,agYears) $ (p_aglink(agEUreg,'QC',agRows,agYears)
              and (not sum(QCposA, p_aglink(agEUreg,QCposA,agRows,agYears))))
            = p_aglink(agEUreg,'QC',agRows,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 822-822):

          p_aglink(agEuparts,agPri,agFuels,agYears)  = p_aglink("EUN",agPri,agFuels,agYears)  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value


def p_aglink_difference(a, b):
    r"""p_aglink(agEurop, ., ., .): OU of sugar beet = QC - BF; DEL of raw milk = QC - FU (where none); BF of the
    biofuels = QC - OU; NT = EX - IM (where trade), of the biofuels QP - QC; PP of the fossil fuels = CP - TAX.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 316-317):

          p_aglink(agEurop,'OU','SBE',agYears) = p_aglink(agEurop,'QC','SBE',agYears)
                                               - p_aglink(agEurop,'BF','SBE',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 339-340):

          p_aglink(agEurop,'DEL','MK',agYears) $ ((not  sameas(agEurop,'EUN')) $ (not p_aglink(agEurop,'DEL','MK',agYears)))
             = p_aglink(agEurop,'QC','MK',agYears)-p_aglink(agEurop,'FU','MK',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 353-354):

          p_aglink(agEurop,'BF',agBiof,agYears) = p_aglink(agEurop,'QC',agBiof,agYears)
            - p_aglink(agEurop,'OU',agBiof,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 426-428):

          p_aglink(agEurop,'NT',agRows,agYears) $((p_aglink(agEurop,'EX',agRows,agYears) +
              p_aglink(agEurop,'IM',agRows,agYears)) >0)
            = p_aglink(agEurop,'EX',agRows,agYears)-p_aglink(agEurop,'IM',agRows,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 433-434):

          p_aglink(agEurop,'NT',agBiof,agYears) $(p_aglink(agEurop,'QC',agBiof,agYears))
            = p_aglink(agEurop,'QP',agBiof,agYears)-p_aglink(agEurop,'QC',agBiof,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 742-742):

          p_aglink(agEurop,'NT',agBioF,agYears) = p_aglink(agEurop,'QP',agBioF,agYears)-p_aglink(agEurop,'QC',agBioF,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 750-750):

           p_aglink(agEurop,'bf',agBioF,agYears) = p_aglink(agEurop,'QC',agBioF,agYears) -  p_aglink(agEurop,'OU',agBioF,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 815-816):

          p_aglink(agEurop,'PP',agFosF,agYears)
            = p_aglink(agEurop,'CP',agFosF,agYears) - p_aglink(agEurop,'TAX',agFosF,agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return a - b


def p_aglink_FU_MK(fe, ou, ds):
    r"""p_aglink(agEurop, 'FU', 'MK', agYears) without a value, not the EU: feed, other use and direct sales.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 328-329):

          p_aglink(agEurop,'FU','MK',agYears) $ ((not  sameas(agEurop,'EUN')) $ (not p_aglink(agEurop,'FU','MK',agYears)))
             = p_aglink(agEurop,'FE','MK',agYears)+p_aglink(agEurop,'OU','MK',agYears)+p_aglink(agEurop,'QP..DS','MK',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return fe + ou + ds


def p_aglink_removed():
    r"""p_aglink(agEurop, 'FE', 'BV', .) and ('FU', agBiof, .); stock changes of at most 1E-3 in size: removed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 349-349):

          p_aglink(agEurop,'FE','BV',agYears) = 0;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 356-356):

          p_aglink(agEurop,'FU',agBiof,agYears) = 0;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 446-447):

          p_aglink(agEurop,'VST',agRows,agYears) $(abs(p_aglink(agEurop,'VST',agRows,agYears)) LE 1.e-3)
            = 0 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 0.0


def p_aglink_OU_MOL(qc, qc_pos):
    r"""p_aglink(agEurop, 'OU', 'MOL', agYears) without a value: molasses' demand less its positions, not below
    zero.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 364-365):

          p_aglink(agEurop,'OU','MOL',agYears) $ (not p_aglink(agEurop,'OU','MOL',agYears))
            = max(0,p_aglink(agEurop,'QC','MOL',agYears)-sum(QCposA,p_aglink(agEurop,QCposA,'MOL',agYears)))  ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return _max0(qc - sum(qc_pos))


def p_aglink_FO_OL(qc, bf, ou):
    r"""p_aglink(agEUparts, 'FO', 'OL', agYears): oils' food use, demand less biofuel and other use.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 379-381):

           p_aglink(agEUparts,'FO','OL',agYears)
                    = p_aglink(agEUparts,'QC','OL',agYears)
                      - p_aglink(agEUparts,'BF','OL',agYears) - p_aglink(agEUparts,'OU','OL',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return qc - bf - ou


def p_aglink_QC(qc_pos, fu, milk):
    r"""p_aglink(agEurop, 'QC', agRows, agYears): demand as its positions (QCposA), raw milk's without FU.

    milk: the row is MK.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 403-405):

          p_aglink(agEurop,'QC',agRows,agYears) = sum(QCposA, p_aglink(agEurop,QCposA,agRows,agYears))
                                                - p_aglink(agEurop,'FU',agRows,agYears) $ sameas(agRows,'MK')
                                                   ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(qc_pos) - (fu if milk else 0.0)


def p_aglink_VST(qp, qc, nt):
    r"""p_aglink(agEurop, 'VST', agRows, agYears) with production and demand: the stock change.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 440-443):

          p_aglink(agEurop,'VST',agRows,agYears) $(p_aglink(agEurop,'QP',agRows,agYears)
              and p_aglink(agEurop,'QC',agRows,agYears))
            = p_aglink(agEurop,'QP',agRows,agYears) - p_aglink(agEurop,'QC',agRows,agYears)
              - p_aglink(agEurop,'NT',agRows,agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return qp - qc - nt


def p_aglink_VST_parts(vst_eun, qp, qc, qp_eun, qc_eun):
    r"""p_aglink(agEUparts, 'VST', agRows, agYears) where the EU has a stock change: the EU's by the part's share of
    production plus demand (0 where the EU's sum is not positive).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 451-455):

          p_aglink(agEUparts,'VST',agRows,agYears)$(p_aglink('EUN','VST',agRows,agYears) )
            = (p_aglink('EUN','VST',agRows,agYears)*(p_aglink(agEUparts,'QP',agRows,agYears)
              + p_aglink(agEUparts,'QC',agRows,agYears)) / (p_aglink('EUN','QP',agRows,agYears)
              + p_aglink('EUN','QC',agRows,agYears)) )
                $((p_aglink('EUN','QP',agRows,agYears)+ p_aglink('EUN','QC',agRows,agYears)) > 0) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    den = qp_eun + qc_eun
    return vst_eun * (qp + qc) / den if den > 0 else 0.0


def p_aglink_NT_parts(qp, qc, vst):
    r"""p_aglink(agEUparts, 'NT', agRows, agYears): production less demand and stock change, where production plus
    demand is positive.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 459-463):

          p_aglink(agEUparts,'NT',agRows,agYears)
            = ( p_aglink(agEUparts,'QP',agRows,agYears)
              - p_aglink(agEUparts,'QC',agRows,agYears)
              - p_aglink(agEUparts,'VST',agRows,agYears) )
                $( (p_aglink(agEUparts,'QP',agRows,agYears)+p_aglink(agEUparts,'QC',agRows,agYears)) > 0 ) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return (qp - qc - vst) if (qp + qc) > 0 else 0.0


def p_aglink_1000t(value, density):
    r"""p_aglink(agEurop, aglinkBioColsQ / QC / FO, agBioF / agFosF, agYears) with a value: the fuels' quantities
    times their density.

    density: p_density summed over the fuel's CAPRI rows (aglinkRows_map), by the caller.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 491-493):

          p_aglink(agEurop,aglinkBioColsQ,agBioF,agYears) $( p_aglink(agEurop,aglinkBioColsQ,agBioF,agYears) )
            = p_aglink(agEurop,aglinkBioColsQ,agBioF,agYears)
              * sum(aglinkRows_map(biofuels,agBioF),p_density(biofuels)) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 495-497):

          p_aglink(agEurop,'QC',agFosF,agYears) $( p_aglink(agEurop,'QC',agFosF,agYears) )
            = p_aglink(agEurop,'QC',agFosF,agYears)
              * sum(aglinkRows_map(fosfuels,agFosF),p_density(fosfuels)) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 499-501):

          p_aglink(agEurop,'FO',agFosF,agYears) $( p_aglink(agEurop,'FO',agFosF,agYears) )
            = p_aglink(agEurop,'FO',agFosF,agYears)
              * sum(aglinkRows_map(fosfuels,agFosF),p_density(fosfuels)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value * density


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


def P_Data_BAST(values):
    r"""P_Data(MS, "NAGR" / "DOMM", seco_biof, "BAST"): the mean over BasYrsT of the values at least 1E-12 in size,
    all the years' values summed. Returns the mean, or None where no year counts.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 626-629):

          P_Data(MS,"NAGR",seco_biof,"BAST")
              $( sum(BasYrsT $ (ABS(P_Data(MS,"NAGR",seco_biof,BasYrsT)) GE 1E-12), 1.) )
            = sum(BasYrsT, P_Data(MS,"NAGR",seco_biof,BasYrsT))
             /sum(BasYrsT $ (ABS(P_Data(MS,"NAGR",seco_biof,BasYrsT)) GE 1E-12), 1.);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 631-634):

          P_Data(MS,"DOMM",seco_biof,"BAST")
              $( sum(BasYrsT $ (ABS(P_Data(MS,"DOMM",seco_biof,BasYrsT)) GE 1E-12), 1.) )
            = sum(BasYrsT, P_Data(MS,"DOMM",seco_biof,BasYrsT))
             /sum(BasYrsT $ (ABS(P_Data(MS,"DOMM",seco_biof,BasYrsT)) GE 1E-12), 1.);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    n = sum(1 for v in values if abs(v) >= 1e-12)
    return sum(values) / n if n else None


def p_share_E14(e14, e13):
    r"""p_nagrShare, p_demShare('E14', .): the old member states' share of the EU's non-agricultural biofuels,
    biofuel demand (BAST) and fossil fuel demand (BASM).

    e14, e13: the sums over REU14 and the new member states.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 637-642):

          p_nagrShare('E14','ET')
             $ (sum(reu14, p_data(reu14,"NAGR","BIOE","BAST"))
             + sum(reu13, p_data(reu13,"NAGR","BIOE","BAST")))
            = sum(reu14, p_data(reu14,"NAGR","BIOE","BAST"))
            / (sum(reu14, p_data(reu14,"NAGR","BIOE","BAST"))
            + sum(reu13, p_data(reu13,"NAGR","BIOE","BAST")));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 648-653):

          p_nagrShare('E14','BD')
             $ (sum(reu14, p_data(reu14,"NAGR","BIOD","BAST"))
             + sum(reu13, p_data(reu13,"NAGR","BIOD","BAST")))
            = sum(reu14, p_data(reu14,"NAGR","BIOD","BAST"))
            / (sum(reu14, p_data(reu14,"NAGR","BIOD","BAST"))
            + sum(reu13, p_data(reu13,"NAGR","BIOD","BAST")));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 667-672):

          p_demShare('E14','ET')
            $ (sum(reu14, p_data(reu14,'DOMM','BIOE','BAST'))
            +  sum(reu13, p_data(reu13,'DOMM','BIOE','BAST')))
            = sum(reu14, p_data(reu14,'DOMM','BIOE','BAST'))
            / (sum(reu14, p_data(reu14,'DOMM','BIOE','BAST'))
            +  sum(reu13, p_data(reu13,'DOMM','BIOE','BAST'))) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 673-678):

          p_demShare('E14','BD')
            $ (sum(reu14, p_data(reu14,'DOMM','BIOD','BAST'))
            + sum(reu13, p_data(reu13,'DOMM','BIOD','BAST')))
            = sum(reu14, p_data(reu14,'DOMM','BIOD','BAST'))
            / (sum(reu14, p_data(reu14,'DOMM','BIOD','BAST'))
            + sum(reu13, p_data(reu13,'DOMM','BIOD','BAST'))) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 756-758):

          p_demShare('E14','DIE')  = sum(reu14, p_data(reu14,'DOMM','DISL','BASM'))
            / (sum(reu14, p_data(reu14,'DOMM','DISL','BASM'))
            +  sum(reu13, p_data(reu13,'DOMM','DISL','BASM'))) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 759-761):

          p_demShare('E14','GAS')  = sum(reu14, p_data(reu14,'DOMM','GASL','BASM'))
            / (sum(reu14, p_data(reu14,'DOMM','GASL','BASM'))
            + sum(reu13, p_data(reu13,'DOMM','GASL','BASM'))) ;

    Departures from CAPRI: the sums over the member states are the caller's; the biofuels' shares are 0 where both sums are 0 (CAPRI's $),
    the fossil fuels' are not guarded (nor are CAPRI's); the domain condition and the loops in the caller (aglink.py)."""
    return e14 / (e14 + e13)


def p_share_NMS(share_e14):
    r"""p_nagrShare, p_secgShare, p_demShare('NMS', .): one less the old member states'.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 655-655):

          p_nagrShare('NMS',agBioF) = 1-p_nagrShare('E14',agBioF);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 664-664):

          p_secgShare('NMS',agBiof) = 1-p_secgShare('E14',agBiof);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 679-679):

          p_demShare('NMS',agBioF) = 1-p_demShare('E14',agBioF);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 762-762):

          p_demShare('NMS',agFosF) = 1-p_demShare('E14',agFosF);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 1 - share_e14


def p_secgShare_E14(fuel):
    r"""p_secgShare('E14', BD / ET): the second generation's share of the EU's biofuels in the old member states
    (85% of biodiesel, 50% of ethanol).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 662-662):

          p_secgShare('E14','BD') = 0.85;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 663-663):

          p_secgShare('E14','ET') = 0.50;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 0.85 if fuel == "BD" else 0.50


def p_aglink_parts_share(eun, share):
    r"""p_aglink(agEUparts, 'QP..NAGR' / 'QP..SEC' / 'QC', agBioF / agFosF, agYears): the EU's times the part's
    share.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 691-692):

          p_aglink(agEUparts,'QP..NAGR',agBioF,agYears) $  p_aglink('EUN','QP..NAGR',agBiof,agYears)
            = p_aglink('EUN','QP..NAGR',agBiof,agYears) * p_nagrShare(agEUparts,agBiof) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 699-700):

          p_aglink(agEUparts,'QP..SEC',agBIof,agYears) $ p_aglink('EUN','QP..SEC',agBIof,agYears)
            = p_aglink('EUN','QP..SEC',agBIof,agYears)  *p_secgShare(agEUparts,agBIof) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 736-737):

          p_aglink(agEUparts,'QC',agBiof,agYears)
            = p_aglink('EUN','QC',agBiof,agYears)*p_demShare(agEUparts,agBiof) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 765-766):

          p_aglink(agEUparts,'QC',agFosF,agYears)
            = p_aglink('EUN','QC',agFosF,agYears)*p_demShare(agEUparts,agFosF) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return eun * share


def p_aglink_QP_SEC(ares, ecr):
    r"""p_aglink(agEurop, 'QP..SEC', agBIof, agYears) without a value: from agricultural residues and energy crops.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 696-697):

          p_aglink(agEurop,'QP..SEC',agBIof,agYears) $ (not p_aglink(agEurop,'QP..SEC',agBIof,agYears))
            = p_aglink(agEurop,'QP..ARES',agBIof,agYears)+p_aglink(agEurop,'QP..ECR',agBIof,agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return ares + ecr


def p_aglink_QC_EUN(qp, qcs, qps):
    r"""p_aglink('EUN', 'QC', agBiof, aglinkYears) without a value: production times the demand over production of
    the years within 5 with both.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 725-733):

          p_aglink('EUN','QC',agBiof,aglinkYears) $ ((not p_aglink('EUN','QC',agBiof,aglinkYears)) $ agYears(aglinkYears)
            $ sum(agYears $ ((abs(calyea(aglinkYears)-calyea(agYears)) le 5) $ p_aglink('EUN','QP',agBiof,agYears) $ p_aglink('EUN','QC',agBiof,agYears)),
                  p_aglink('EUN','QP',agBiof,agYears)))
            = p_aglink('EUN','QP',agBiof,aglinkYears)
            * sum(agYears $ ((abs(calyea(aglinkYears)-calyea(agYears)) le 5) $ p_aglink('EUN','QP',agBiof,agYears) $ p_aglink('EUN','QC',agBiof,agYears)),
                  p_aglink('EUN','QC',agBiof,agYears))
            / sum(agYears $ ((abs(calyea(aglinkYears)-calyea(agYears)) le 5) $ p_aglink('EUN','QP',agBiof,agYears) $ p_aglink('EUN','QC',agBiof,agYears)),
                  p_aglink('EUN','QP',agBiof,agYears))
              ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return qp * sum(qcs) / sum(qps)


def p_aglink_OU_parts(ou_eun, qc, qc_eun):
    r"""p_aglink(agEUparts, 'OU', agBioF, agYears): the EU's other use by the part's share of demand.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 747-748):

          p_aglink(agEUparts,'OU',agBioF,agYears)
            = p_aglink('EUN','OU',agBioF,agYears)*p_aglink(agEUparts,'QC',agBioF,agYears)/p_aglink('EUN','QC',agBioF,agYears) ;

    Departures from CAPRI: the caller gives 0 where the EU has no demand (CAPRI divides by it); the domain condition and the loops in the caller (aglink.py)."""
    return ou_eun * qc / qc_eun


def p_aglink_XR(value, xr_eun, xr):
    r"""p_aglink(agEurop, agPri, agFuels, agYears) with an exchange rate: the fuel prices in EUR (the EU's rate over
    the region's).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 792-794):

          p_aglink(agEurop,agPri,agFuels,agYears)  $ p_aglinkOri(agEurop,'XR','ME',agYears)
            = p_aglink(agEurop,agPri,agFuels,agYears)
            * p_aglinkOri('EUN','XR','ME',agYears)/ p_aglinkOri(agEurop,'XR','ME',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value * xr_eun / xr


def p_aglink_per_toe(value, density, oil_equ):
    r"""p_aglink(agEurop, agPri, agBioF / agFosF, agYears), p_aglink('WLD', 'XP', agBioF, .): per toe (x 10 / density /
    p_oilEqu, both summed over the fuel's CAPRI rows by the caller).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 798-802):

          p_aglink(agEurop,agPri,agBioF,agYears)
        *  - to 1000 liters
          = p_aglink(agEurop,agPri,agBioF,agYears) * 10
        *  - to ton                                                    - to toe
            / sum(aglinkRows_map(biofuels,agBioF),p_density(biofuels))  / sum(aglinkRows_map(biofuels,agBioF),p_oilEqu(biofuels));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 804-805):

          p_aglink('WLD','XP',agBioF,agYears)  = p_aglink('WLD','XP',agBioF,agYears) * 10
            / sum(aglinkRows_map(biofuels,agBioF),p_density(biofuels))  / sum(aglinkRows_map(biofuels,agBioF),p_oilEqu(biofuels));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 810-812):

          p_aglink(agEurop,agPri,agFosF,agYears) = p_aglink(agEurop,agPri,agFosF,agYears) * 10
        *    - to ton                                                   - to toe
            / sum(aglinkRows_map(fosfuels,agFosF),p_density(fosfuels))  / sum(aglinkRows_map(fosfuels,agFosF),p_oilEqu(fosfuels));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value * 10 / density / oil_equ


def p_aglink_XP_OIL(value, density):
    r"""p_aglink('WLD', 'XP', 'OIL', agYears): crude oil's world price per ton (x 10 / CRDO's density).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 819-819):

          p_aglink('WLD','XP','OIL',agYears)  = p_aglink('WLD','XP','OIL',agYears) * 10 / p_density('CRDO') ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value * 10 / density


def p_aglinkTrd_sum(values):
    r"""p_aglinkTrd(EuropReg, ., ., agYears): Aglink's values summed over the region's Aglink regions and the mapped
    columns and rows (the direct links, population, exchange rates, GDP deflator, areas, cows, gross production,
    biofuels by source, HFCS, the EU's prices, margins, taxes, consumer and producer prices, tariffs); the EU27's
    over its parts.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 878-880):

          p_aglinkTrd(EuropReg,colsMappedAglink,rowsMappedAglink,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),
            aglinkCols_map(colsMappedAglink,aglinkColsMapped),aglinkRows_map(rowsMappedAglink,aglinkRowsMapped)),
            p_aglink(agEurop,aglinkColsMapped,aglinkRowsMapped,agYears)) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 887-888):

          p_aglinkTrd(EuropReg,'INHA','LEVL',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'POP','ME',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 894-895):

          p_aglinkTrd(EuropReg,'XR','LEVL',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'XR','ME',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 898-899):

          p_aglinkTrd(EuropReg,'GDPI','LEVL',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'GDPI','ME',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1075-1079):

          p_aglinkTrd(EuropReg,cols,'LEVL',agYears)
        *     condition needed, otherwise macro info is deleted
            $ sum((aglinkRegions_map(EuropReg,agEurop),aglinkAct_map(cols,agRows)),1)
            = sum((aglinkRegions_map(EuropReg,agEurop),aglinkAct_map(cols,agRows)),
                     p_aglink(agEurop,'AH',agRows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1090-1091):

          p_aglinkTrd(EuropReg,dcows,'LEVL',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'CI','MK',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1093-1094):

          p_aglinkTrd(EuropReg,'SCOW','LEVL',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'CI','BV',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1116-1117):

          p_aglinkTrd(EuropReg,'GROF',rows,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),
            aglinkRows_map(rows,agPrim)), p_aglink(agEurop,'QP',agPrim,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1132-1132):

          p_aglinkTrd('EU27yr19',colsGrof,rows,agYears) = sum(EUparts,p_aglinkTrd(EUparts,colsGrof,rows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1162-1162):

          p_aglinkTrd('EU27yr19',colsInd,rows,agYears) = sum(EUparts,p_aglinkTrd(EUparts,colsInd,rows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1166-1167):

          p_aglinkTrd(EuropReg,'INDM','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
             p_aglink(agEurop,'OU','ET',agYears)) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1187-1187):

          p_aglinkTrd('EU27yr19',colsHcom,rows,agYears) = sum(EUparts,p_aglinkTrd(EUparts,colsHcom,rows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1225-1226):

          p_aglinkTrd(EuropReg,'GROF','COMI',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP','MK',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1228-1229):

          p_aglinkTrd(EuropReg,'LOSF','COMI',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'FE','MK',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1234-1235):

          p_aglinkTrd(EuropReg,'PRCM','COMI',agYears) =  sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'DEL','MK',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1254-1255):

          p_aglinkTrd(EuropReg,'NAGR','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..NAGR','ET',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1257-1258):

          p_aglinkTrd(EuropReg,'NAGR','BIOD',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..NAGR','BD',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1260-1261):

          p_aglinkTrd(EuropReg,'SECG','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..SEC','ET',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1263-1264):

          p_aglinkTrd(EuropReg,'SECG','BIOD',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..SEC','BD',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1268-1269):

          p_aglinkTrd(EuropReg,'bioeWhea','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..WT','ET',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1271-1272):

          p_aglinkTrd(EuropReg,'bioECgra','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..CG','ET',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1274-1275):

          p_aglinkTrd(EuropReg,'bioeSuga','BIOE',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..SBE','ET',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1277-1278):

          p_aglinkTrd(EuropReg,'bioDOilP','BIOD',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'QP..VL','BD',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1318-1319):

          p_aglinkTrd(EuropReg,'HCOS','HFCS',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            p_aglink(agEurop,'FO..SHR','HFCS',agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1368-1370):

          p_aglinkTrd(EuropReg,pric,rows,agYears) $ EUreg(EuropReg)
          = sum((aglinkRegions_map(EuropReg,agEurop), aglinkRows_map(rows,agRows)),
                 p_aglink(agEurop,'PP',agRows,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1381-1382):

          p_aglinkTrd(EuropReg,'PROCMARG',biofuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(biofuels,agbiof)),
            p_aglink(agEurop,'MAR',agbiof,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1384-1385):

          p_aglinkTrd(EuropReg,'CTAX',fuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(fuels,agfuels)),
            p_aglink(agEurop,'TAX',agfuels,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1395-1396):

          p_aglinkTrd(EuropReg,'UVAD',fuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(fuels,agfuels)),
            p_aglink(agEurop,'CP',agfuels,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1398-1399):

          p_aglinkTrd(EuropReg,'UVAP',biofuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(biofuels,agbiof)),
            p_aglink(agEurop,'PP',agbiof,agYears));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1410-1411):

          p_aglinkTrd(EuropReg,'TARS',biofuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(biofuels,agBioF)),
            p_aglink(agEurop,'TSP',agBioF,agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(values)


def p_aglink_XR_parts(xr_eun):
    r"""p_aglink('E14' / 'NMS', 'XR', 'ME', agYears) without a value: the EU's exchange rate.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 891-891):

        p_aglink('E14','XR','ME',agYears) $ (not p_aglink('E14','XR','ME',agYears)) = p_aglink('EUN','XR','ME',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 892-892):

        p_aglink('NMS','XR','ME',agYears) $ (not p_aglink('NMS','XR','ME',agYears)) = p_aglink('EUN','XR','ME',agYears);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return xr_eun


def p_aglinkTrd_YILD(values):
    r"""p_aglinkTrd(EuropReg, cols, 'YILD', agYears): Aglink's yields (t/ha) in kg/ha, summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1083-1085):

          p_aglinkTrd(EuropReg,cols,'YILD',agYears) = sum((agEurop,agRows)
              $(aglinkRegions_map(EuropReg,agEurop) and aglinkAct_map(cols,agRows)),
            1000*p_aglink(agEurop,'YLD',agRows,agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(1000 * v for v in values)


def p_aglinkTrd_BIOF_SUGA(values):
    r"""p_aglinkTrd(EuropReg, 'BIOF', 'SUGA', agYears): 16% of the sugar beet used for biofuels.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1102-1103):

          p_aglinkTrd(EuropReg,'BIOF','SUGA',agYears) = 0.16 *
            sum(aglinkRegions_map(EuropReg,agEurop),p_aglink(agEurop,'BF','SBE',agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 0.16 * sum(values)


def p_domShare(value, total):
    r"""p_domShare(EuropReg, colsGrof / colsInd / colsHcom, rowsMappedAglink): the member states' BASM of the column
    over GROF's, or over the group's sum.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1123-1126):

          p_domShare(EuropReg,colsGrof,rowsMappedAglink)
            $ sum(aglinkRegions_map(MS,agEurop) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,'GROF',rowsMappedAglink,'BASM'))
            = sum(aglinkRegions_map(MS,agEurop) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsGROF,rowsMappedAglink,'BASM'))
            / sum(aglinkRegions_map(MS,agEurop) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,'GROF',rowsMappedAglink,'BASM'));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1149-1152):

          p_domShare(EuropReg,colsInd,rowsMappedAglink)
            $ sum((colsInd1,aglinkRegions_map(MS,agEurop)) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsInd1,rowsMappedAglink,'BASM'))
            = sum(aglinkRegions_map(MS,agEurop) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsInd,rowsMappedAglink,'BASM'))
            / sum((colsInd1,aglinkRegions_map(MS,agEurop)) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsInd1,rowsMappedAglink,'BASM'));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1177-1180):

          p_domShare(EuropReg,colsHcom,rowsMappedAglink)
            $ sum((colsHcom1,aglinkRegions_map(MS,agEurop)) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsHcom1,rowsMappedAglink,'BASM'))
            = sum(aglinkRegions_map(MS,agEurop) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsHcom,rowsMappedAglink,'BASM'))
            / sum((colsHcom1,aglinkRegions_map(MS,agEurop)) $ aglinkRegions_map(EuropReg,agEurop), p_data(MS,colsHcom1,rowsMappedAglink,'BASM'));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value / total


def p_aglinkTrd_colsGrof(share, grof):
    r"""p_aglinkTrd(EuropReg, colsGrof, rows, agYears) with a share: the share of gross production.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1129-1130):

          p_aglinkTrd(EuropReg,colsGrof,rows,agYears) $(p_domShare(EuropReg,colsGrof,rows))
            = p_domShare(EuropReg,colsGrof,rows) * p_aglinkTrd(EuropReg,'GROF',rows,agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return share * grof


def p_aglinkTrd_colsInd(share, quads):
    r"""p_aglinkTrd(EuropReg, colsInd, rows, agYears): the share of Aglink's crush, delivery, sweetener and other
    use.

    quads: (CR, DEL, SWG, OU) of the region's Aglink regions and rows.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1155-1160):

          p_aglinkTrd(EuropReg,colsInd,rows,agYears)
            = sum( (aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(rows,agRows)),
              p_domShare(EuropReg,colsInd,rows) * (p_aglink(agEurop,'CR',agRows,agYears)
                                                 + p_aglink(agEurop,'DEL',agRows,agYears)
                                                 + p_aglink(agEurop,'SWG',agRows,agYears)
                                                 + p_aglink(agEurop,'OU',agRows,agYears)) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(share * (a + b + c + d) for a, b, c, d in quads)


def p_aglinkTrd_removed():
    r"""p_aglinkTrd(EuropReg, 'LOSM', 'BIOE', .), (., 'MILK', .), (pric, 'RICE', .) once copied to PARI: removed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1169-1169):

          p_aglinkTrd(EuropReg,'LOSM','BIOE',agYears) = 0 ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1242-1242):

          p_aglinkTrd(EuropReg,cols,'MILK',agYears) =  0;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1375-1375):

          p_aglinkTrd(EuropReg,pric,'RICE',agYears) = 0.;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 0.0


def p_result_DGAgri_EXPT_IMPT():
    r"""p_result(EUreg, 'EXPT' / 'IMPT', ., ., 'DGAgri'): the EU regions' exports and imports removed (they
    do not include the EU's internal trade).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1441-1441):

          p_result(EUreg,'EXPT',rows,years,'DGAgri') = 0 ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1442-1442):

          p_result(EUreg,'IMPT',rows,years,'DGAgri') = 0 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return 0.0


def p_aglinkTrd_colsHcom(n, share, hcom):
    r"""p_aglinkTrd(EuropReg, colsHcom, rows, agYears): the share of HCOM, summed over the region's Aglink regions and
    rows (n equal terms).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1183-1185):

          p_aglinkTrd(EuropReg,colsHcom,rows,agYears)
            = sum( (aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(rows,agRows)),
              p_domShare(EuropReg,colsHcom,rows) *  p_aglinkTrd(EuropReg,'HCOM',rows,agYears));

    Departures from CAPRI: the sum of n equal terms is written n x the term; the domain condition and the loops in the caller (aglink.py)."""
    return n * share * hcom


def p_aglinkTrd_DOMM_negative(value, domm, stcm):
    r"""p_aglinkTrd(EuropReg, HCOM / DOMM, rows, agYears) where DOMM + STCM is negative: raised to 1E-6 above.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1195-1198):

          p_aglinkTrd(EuropReg,cols,rows,agYears) $ ((sameas(cols,'HCOM') or sameas(cols,'DOMM'))
            $ ((p_aglinkTrd(EuropReg,'DOMM',rows,agYears)+ p_aglinkTrd(EuropReg,'STCM',rows,agYears)) lt 0))
            = p_aglinkTrd(EuropReg,cols,rows,agYears)
            - (p_aglinkTrd(EuropReg,'DOMM',rows,agYears)+ p_aglinkTrd(EuropReg,'STCM',rows,agYears))+1e-6;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value - (domm + stcm) + 1e-6


def p_aglinkTrd_plus(a, b):
    r"""p_aglinkTrd(EuropReg, 'DOMM', rows, .) with the stock change; DOMM of COMI = PRCM + HCOM; WHEA (balance
    positions, LEVL) without a value: SWHE + DWHE.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1200-1201):

          p_aglinkTrd(EuropReg,'DOMM',rows,agYears) = p_aglinkTrd(EuropReg,'DOMM',rows,agYears)
            + p_aglinkTrd(EuropReg,'STCM',rows,agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1237-1238):

          p_aglinkTrd(EuropReg,'DOMM','COMI',agYears) = p_aglinkTrd(EuropReg,'PRCM','COMI',agYears)
            + p_aglinkTrd(EuropReg,'HCOM','COMI',agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1309-1310):

          p_aglinkTrd(EuropReg,balPos,'WHEA',years) $ (not p_aglinkTrd(EuropReg,balPos,'WHEA',years) )
          =  p_aglinkTrd(EuropReg,balPos,'SWHE',years) + p_aglinkTrd(EuropReg,balPos,'DWHE',years) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1312-1313):

          p_aglinkTrd(EuropReg,'WHEA','LEVL',years) $ (not p_aglinkTrd(EuropReg,'WHEA','LEVL',years) )
          = p_aglinkTrd(EuropReg,'SWHE','LEVL',years)  + p_aglinkTrd(EuropReg,'DWHE','LEVL',years) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return a + b


def p_aglinkTrd_copy(value):
    r"""p_aglinkTrd(EuropReg, cols, ., agYears) outside the EU: the oilseeds' cakes and oils from OILM and OILO; MILK's
    MAPR = PRCM of COMI, DOMM = MAPR, PRCM = DOMM; PARI's prices: RICE's.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1218-1219):

          p_aglinkTrd(EuropReg,cols,rows,agYears) $ ( (not EUreg(EuropReg)) $ sum(SED_TO_CAK(oSeeds,ROWS),1))
            = p_aglinkTrd(EuropReg,cols,"OILM",agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1220-1221):

          p_aglinkTrd(EuropReg,cols,rows,agYears) $ ( (not EUreg(EuropReg)) $ sum(SED_TO_OIL(oSeeds,ROWS),1))
            = p_aglinkTrd(EuropReg,cols,"OILO",agYears) ;

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1244-1244):

          p_aglinkTrd(EuropReg,'MAPR','MILK',agYears) = p_aglinkTrd(EuropReg,'PRCM','COMI',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1246-1246):

          p_aglinkTrd(EuropReg,'DOMM','MILK',agYears) = p_aglinkTrd(EuropReg,'MAPR','MILK',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1248-1248):

          p_aglinkTrd(EuropReg,'PRCM','MILK',agYears) = p_aglinkTrd(EuropReg,'DOMM','MILK',agYears);

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1374-1374):

          p_aglinkTrd(EuropReg,pric,'PARI',agYears) = p_aglinkTrd(EuropReg,pric,'RICE',agYears) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value


def p_result_DGAgri(value):
    r"""p_result(EuropReg, cols, rows, years, 'DGAgri'): p_aglinkTrd where not NA.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1436-1437):

          p_result(EuropReg,cols,rows,years,'DGAgri')$(p_aglinkTrd(EuropReg,cols,rows,years) ne NA)
            = p_aglinkTrd(EuropReg,cols,rows,years);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return value


def p_aglinkTrd_HCOM_COMI(pairs):
    r"""p_aglinkTrd(EuropReg, 'HCOM', 'COMI', agYears): raw milk's other use and direct sales, summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1231-1232):

          p_aglinkTrd(EuropReg,'HCOM','COMI',agYears) =  sum(aglinkRegions_map(EuropReg,agEurop),
              p_aglink(agEurop,'OU','MK',agYears) + p_aglink(agEurop,'QP..DS','MK',agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(o + d for o, d in pairs)


def p_aglinkTrd_Exog(qp, parts):
    r"""p_aglinkTrd(EuropReg, 'bioeExog' / 'biodExog', ., agYears): production less the feedstocks', the
    non-agricultural and the second generation biofuels, not below zero.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1282-1288):

          p_aglinkTrd(EuropReg,'bioeExog','BIOE',agYears)
          = max(0, p_aglinkTrd(EuropReg,'QP','BIOE',agYears)
            - p_aglinkTrd(EuropReg,'bioeWhea','BIOE',agYears)
            - p_aglinkTrd(EuropReg,'bioECgra','BIOE',agYears)
            - p_aglinkTrd(EuropReg,'bioeSuga','BIOE',agYears)
            - p_aglinkTrd(EuropReg,'NAGR','BIOE',agYears)
            - p_aglinkTrd(EuropReg,'SECG','BIOE',agYears) );

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1290-1294):

          p_aglinkTrd(EuropReg,'biodExog','BIOD',agYears)
          = max(0,p_aglinkTrd(EuropReg,'QP','BIOD',agYears)
           - p_aglinkTrd(EuropReg,'bioDOilP','BIOD',agYears)
            - p_aglinkTrd(EuropReg,'NAGR','BIOD',agYears)
            - p_aglinkTrd(EuropReg,'SECG','BIOD',agYears) );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    v = qp
    for x in parts:
        v = v - x
    return max(0.0, v)


def p_aglinkTrd_S1COM(pairs):
    r"""p_aglinkTrd(EuropReg, 'S1COM', 'HFCS', agYears): HFCS's self-sufficiency (QP / QC where QC), summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1322-1324):

          p_aglinkTrd(EuropReg,'S1COM','HFCS',agYears) = sum(aglinkRegions_map(EuropReg,agEurop),
            (p_aglink(agEurop,'QP','HFCS',agYears)/p_aglink(agEurop,'QC','HFCS',agYears))
            $ p_aglink(agEurop,'QC','HFCS',agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(a / b for a, b in pairs)


def p_aglinkTrd_pric_XR(triples):
    r"""p_aglinkTrd(EuropReg, pric, rows, agYears) outside the EU, with an exchange rate: the producer prices in EUR,
    summed.

    triples: (PP, the EU's rate, the region's rate).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1360-1365):

          p_aglinkTrd(EuropReg,pric,rows,agYears) $ ((not EUreg(EuropReg))
                                                  $  sum(aglinkRegions_map(EuropReg,agEurop), p_aglinkOri(agEurop,'XR','ME',agYears)))
          = sum((aglinkRegions_map(EuropReg,agEurop), aglinkRows_map(rows,agRows)),
                 p_aglink(agEurop,'PP',agRows,agYears)
                           * p_aglinkOri('EUN','XR','ME',agYears)/ p_aglinkOri(agEurop,'XR','ME',agYears)
                           );

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(pp * xe / x for pp, xe, x in triples)


def p_aglinkTrd_UVAG_biofuels(values):
    r"""p_aglinkTrd(EuropReg, 'UVAG', biofuels, agYears): 85% of Aglink's producer price.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1392-1393):

          p_aglinkTrd(EuropReg,'UVAG',biofuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(biofuels,agbiof)),
            p_aglink(agEurop,'PP',agbiof,agYears)) * 0.85;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(values) * 0.85


def p_aglinkTrd_UVAP_fosfuels(pairs):
    r"""p_aglinkTrd(EuropReg, 'UVAP', fosfuels, agYears): the consumer price less the tax, summed.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1401-1402):

          p_aglinkTrd(EuropReg,'UVAP',fosfuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(fosfuels,agFosF)),
            p_aglink(agEurop,'CP',agFosF,agYears)-p_aglink(agEurop,'TAX',agFosF,agYears));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(cp - tax for cp, tax in pairs)


def p_aglinkTrd_TARV(values):
    r"""p_aglinkTrd(EuropReg, 'TARV', biofuels, agYears): the ad valorem tariff in percent.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1413-1414):

          p_aglinkTrd(EuropReg,'TARV',biofuels,agYears) = sum((aglinkRegions_map(EuropReg,agEurop),aglinkRows_map(biofuels,agBioF)),
            p_aglink(agEurop,'TAV',agBioF,agYears))*100;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return sum(values) * 100


def p_aglinkTrd_DDGS(quads):
    r"""p_aglinkTrd(EuropReg, pric, 'DDGS', agYears): the prices of distillers' grains and corn gluten feed weighted
    by their production, summed over the region's Aglink regions with production.

    quads: (PP DDG, QP DDG, PP CGF, QP CGF).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1420-1424):

          p_aglinkTrd(EuropReg,pric,'DDGS',agYears)= sum(aglinkRegions_map(EuropReg,agEurop)
              $(p_aglink(agEurop,'QP','DDG',agYears)+p_aglink(agEurop,'QP','CGF',agYears)),
            (p_aglink(agEurop,'PP','DDG',agYears)*p_aglink(agEurop,'QP','DDG',agYears)
            + p_aglink(agEurop,'PP','CGF',agYears)*p_aglink(agEurop,'QP','CGF',agYears))/
            (p_aglink(agEurop,'QP','DDG',agYears)+p_aglink(agEurop,'QP','CGF',agYears)));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them); the domain condition and the loops in the caller (aglink.py)."""
    v = 0.0
    for pd_, qd, pc, qc in quads:
        v += (pd_ * qd + pc * qc) / (qd + qc)
    return v


def p_result_DGAgri_max0(value):
    r"""p_result(EuropReg, cols, rows, years, 'DGAGRI') but NTRD: not below zero.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1446-1447):

           p_result(EuropReg,cols,rows,years,'DGAGRI') $ (not sameas(cols,'NTRD'))
              = max(0, p_result(EuropReg,cols,rows,years,'DGAGRI'));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (aglink.py and macro.py)."""
    return max(0.0, value)


def p_SSPAglink_INHA_2000(pop):
    r"""p_SSPAglink(GlobiomCountry, "INHA", "SSP2", "2000"): IIASA's SSP2 population.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 965-965):

          p_SSPAglink(GlobiomCountry,"INHA","SSP2","2000") = p_SSPMacroOri("IIASA","SSP2","POP",GlobiomCountry,"2000")     ;

    Departures from CAPRI: the domain condition and the loops in the caller (macro.inha)."""
    return pop


def p_SSPAglink_INHA_agYears(inha_2000, pairs):
    r"""p_SSPAglink(GlobiomCountry(TAW), "INHA", "SSP2", agYears) without a value: 2000's times the population's
    change from 2000 of the country's Aglink regions (POP ME) or EU countries (p_aglinkMacroEU).

    pairs: (the year's population, 2000's) of those with a 2000 value.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 982-985):

          p_SSPAglink(GlobiomCountryTAW,"INHA","SSP2",agYears) $ (not p_SSPAglink(GlobiomCountryTAW,"INHA","SSP2",agYears))
            = p_SSPAglink(GlobiomCountryTAW,"INHA","SSP2","2000")
            * sum((GlobiomCountry_FAOreg(GlobiomCountryTAW,FAOregions),FAOreg_AGMacroreg(FAOregions,AGLINKRegions)),
                  p_AGLINKOri(AGLINKRegions,"POP","ME",AGYears)/p_AGLINKOri(AGLINKRegions,"POP","ME","2000"));

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 994-997):

          p_SSPAglink(GlobiomCountry,"INHA","SSP2",agYears) $ (not p_SSPAglink(GlobiomCountry,"INHA","SSP2",agYears))
            = p_SSPAglink(GlobiomCountry,"INHA","SSP2","2000")
            * sum((GlobiomCountry_FAOreg(GlobiomCountry,FAOregions),FAOreg_AGMacroreg(FAOregions,ctrcode)),
                  p_aglinkMacroEU(ctrcode,"POP",AGYears)/p_aglinkMacroEU(ctrcode,"POP","2000"));

    Departures from CAPRI: CAPRI divides by each 2000 value; the caller leaves out those without one; the loops in the caller (macro.inha)."""
    return inha_2000 * sum(a / b for a, b in pairs)


def p_SSPAglink_INHA_after_lst_dgagri(inha_lst, ssp, ssp_lst):
    r"""p_SSPAglink(GlobiomCountry, "INHA", "SSP2", years) after %lst_dgagri%: %lst_dgagri%'s times SSP2's change.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1006-1009):

          p_SSPAglink(GlobiomCountry,"INHA","SSP2",years) $ ( (calyea(years) gt calyea("%lst_dgagri%"))
                                                            $ p_SSPMacroOri("IIASA","SSP2","POP",GlobiomCountry,"%lst_dgagri%"))
             = p_SSPAglink(GlobiomCountry,"INHA","SSP2","%lst_dgagri%")
             * p_SSPMacroOri("IIASA","SSP2","POP",GlobiomCountry,years)/p_SSPMacroOri("IIASA","SSP2","POP",GlobiomCountry,"%lst_dgagri%")     ;

    Departures from CAPRI: the domain condition and the loops in the caller (macro.inha)."""
    return inha_lst * ssp / ssp_lst


def p_SSPAglink_interpolated(value, value_next, year, year_next, fill_year):
    r"""p_SSPAglink(GlobiomCountryTaw, macro, "SSP2", simyyy) between two SSP years: linear.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1041-1045):

              p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",simyyy)  $ SUM( (sspYr1) $ p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",sspYr1),1)
              =  p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",sspYr)
              +  (ORDT(simyyy)-ORDT(sspYr))
              *  (p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",sspYr+1) - p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",sspYr))
              /  (ORDT(sspYr+1)-ORDT(sspYr));

    Departures from CAPRI: CAPRI's ORDT differences are taken as calendar years (the time set has every year); the loops in the caller 
    (macro.inha)."""
    return value + (fill_year - year) * (value_next - value) / (year_next - year)


def p_aglinkMacro(values):
    r"""p_aglinkMacro(rmAll, macro, Years): the countries' population summed to CAPRI's regions (GlobiomCountry_FAOreg,
    FAOregions_map).

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1051-1052):

          p_aglinkMacro(rmAll,macro,Years)=sum((GlobiomCountry_FAOreg(GlobiomCountryTaw,FAOregions),FAOregions_map(rmAll,FAOregions)),
          p_SSPAglink(GlobiomCountryTaw,macro,"SSP2",years) );

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them); the loops in the caller 
    (macro.inha)."""
    t = 0.0
    for v in values:
        t += v
    return t


def p_aglinkMacro_BAS(values):
    r"""p_aglinkMacro(RMS, macro, "BAS"): the mean of the nonzero values within a year of %BaseYear%.

    values: the nonzero values.

    CAPRI's GAMS (baseline/load_aglink2023dgAgri.gms l. 1064-1067):

          p_aglinkMacro(RMS,macro,"BAS") $ SUM(years $ ( (ABS(OrdT(years)-OrdT("20%BAS%")) LE 1)
              and p_aglinkMacro(RMS,macro,years)),1.)
            = SUM(years $ (ABS(OrdT(years)-OrdT("20%BAS%")) LE 1),p_aglinkMacro(RMS,macro,years))
              / SUM(years $ ((ABS(OrdT(years)-OrdT("20%BAS%")) LE 1) and p_aglinkMacro(RMS,macro,years)),1.);

    Departures from CAPRI: the domain condition and the loops in the caller (macro.inha)."""
    return sum(values) / len(values)


def _nz(v):
    """GAMS's truth of a value: nonzero, NA included."""
    return v != 0.0 or math.isnan(v)


def _max0(v):
    """GAMS's MAX(0, v): NA stays NA."""
    return v if math.isnan(v) else max(0.0, v)

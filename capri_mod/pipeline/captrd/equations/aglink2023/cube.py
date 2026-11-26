r"""Aglink's cube: p_aglinkOri rebooked, p_aglink and its sums, differences and parts
(baseline/load_aglink2023dgAgri.gms; moved from capri_mod/pipeline/captrd/equations/load_aglink2023dgAgri.py as they
were, 26 November 2026).
"""
from __future__ import annotations

import math
from capri_mod.pipeline.captrd.equations.aglink2023.macro import _max0, _nz  # noqa: E402




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

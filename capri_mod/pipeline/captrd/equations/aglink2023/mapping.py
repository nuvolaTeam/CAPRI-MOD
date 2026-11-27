r"""p_aglinkTrd: Aglink mapped to CAPRI's regions, columns and rows; p_result's DGAgri
(baseline/load_aglink2023dgAgri.gms; moved from capri_mod/pipeline/captrd/equations/load_aglink2023dgAgri.py as they
were, 26 November 2026).
"""
from __future__ import annotations

import math




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

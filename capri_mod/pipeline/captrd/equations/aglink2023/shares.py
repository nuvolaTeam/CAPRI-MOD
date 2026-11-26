r"""The base data, the EU-14's and the new member states' shares, second generation, the exchange rates and the oils
(baseline/load_aglink2023dgAgri.gms; moved from capri_mod/pipeline/captrd/equations/load_aglink2023dgAgri.py as they
were, 26 November 2026).
"""
from __future__ import annotations

import math




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

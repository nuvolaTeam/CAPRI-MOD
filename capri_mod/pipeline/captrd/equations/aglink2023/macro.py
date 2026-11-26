r"""The population (p_SSPAglink) and the macro data (p_aglinkMacro) (baseline/load_aglink2023dgAgri.gms; moved from
capri_mod/pipeline/captrd/equations/load_aglink2023dgAgri.py as they were, 26 November 2026).
"""
from __future__ import annotations

import math




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

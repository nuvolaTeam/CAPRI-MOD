r"""CAPTRD's statements of global/convert_globiom.gms (CAPRI star 3.0, --GlobiomVersion=Globiom_EU): GLOBIOM-EU's
projections collected on p_GLOBIOM, mapped to CAPRI's regions, columns and rows (p_GLOBIOMmapped), and turned into the
long-run information p_globiomInfo (data, factorB2000, share), with the base year's change factors from B2000, as named
functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/globiom.py (collect, mapped, factors, base_factors)
holds the loops over the regions, items and years, the records' grouping, the filters and the conditions, and calls
them; the arithmetic is the port's, so the conversion is unchanged. The set statements (the region mapping, l.
1213-1243; the years kept, l. 1702-1708; projCols / projRows, l. 2025-2031 and 2111-2112) and the abort of l. 2093
stay in globiom.py.
"""
from __future__ import annotations


def p_MACRO(value):
    r"""p_MACRO(GLOBIOMregion, POP / GDP, macroScen, LongYr): MacroScen_DATA's population and GDP; where there is no
    population, its relative change (POP_RelChng).

    CAPRI's GAMS (global/convert_globiom.gms l. 1364-1364):

        p_MACRO(GLOBIOMregion,'POP',macroScen,LongYr) = MacroScen_DATA(macroScen,GLOBIOMregion,'POP',LongYr);

    CAPRI's GAMS (global/convert_globiom.gms l. 1365-1365):

        p_MACRO(GLOBIOMregion,'GDP',macroScen,LongYr) = MacroScen_DATA(macroScen,GLOBIOMregion,'GDP',LongYr);

    CAPRI's GAMS (global/convert_globiom.gms l. 1380-1381):

           p_MACRO(GLOBIOMragg,'POP',macroScen,LongYr) $ (NOT p_MACRO(GLOBIOMragg,'POP',macroScen,LongYr))
           = MacroScen_DATA(macroScen,GLOBIOMragg,'POP_RelChng',LongYr);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value


def p_MACRO_POP_1000(pop):
    r"""p_MACRO(GLOBIOMragg, 'POP', macroScen, LongYr): GLOBIOM's regions' population in 1000.

    CAPRI's GAMS (global/convert_globiom.gms l. 1377-1377):

           p_MACRO(GLOBIOMragg,'POP',macroScen,LongYr) = 1000* p_MACRO(GLOBIOMragg,'POP',macroScen,LongYr);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return 1000 * pop


def p_MACRO_GDP_RelChng(gdppcap, pop):
    r"""p_MACRO(GLOBIOMragg, 'GDP', macroScen, LongYr) without GDP: the relative changes of GDP per head times
    population's.

    CAPRI's GAMS (global/convert_globiom.gms l. 1378-1379):

           p_MACRO(GLOBIOMragg,'GDP',macroScen,LongYr) $ (NOT p_MACRO(GLOBIOMragg,'GDP',macroScen,LongYr))
           = MacroScen_DATA(macroScen,GLOBIOMragg,'GDPpCAP_RelChng',LongYr)*MacroScen_DATA(macroScen,GLOBIOMragg,'POP_RelChng',LongYr) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return gdppcap * pop


def _added(values):
    """The values added one at a time in their order (as the port accumulated them; Python's sum() is
    compensated)."""
    t = 0.0
    for v in values:
        t += v
    return t


def p_globiomTrade(values):
    r"""p_globiomTrade(GLOBIOMragg, GLOBIOMragg1, ALLITEM, SelecScen, ScenYear): the scenario's trade
    records (TRADE_COMPARE) summed.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1385-1387):

        p_globiomTrade(GLOBIOMragg,GLOBIOMragg1,ALLITEM,SelecScen,ScenYear)
        = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,
           TRADE_COMPARE(ALLITEM,GLOBIOMragg1,GLOBIOMragg,"Level",macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_PRICE(values):
    r"""p_PRICE(GLOBIOMragg, ALLITEM, SelecScen, ScenYear): the scenario's price records (PRICE_COMPARE2)
    summed.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1390-1392):

        p_PRICE(GLOBIOMragg,ALLITEM,SelecScen,ScenYear)
        = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,
              PRICE_COMPARE2(ALLITEM,GLOBIOMragg,macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_PROCESS(values):
    r"""p_PROCESS(GLOBIOMragg, ALLITEM, SelecScen, ScenYear): the scenario's processing records
    (PROCESS_COMPARE2) summed over the processes, without the vegetable oils going to FAME.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1394-1400):

        p_PROCESS(GLOBIOMragg,ALLITEM,SelecScen,ScenYear)
        = sum((ALLPROCESS,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen))
        *        Exclude processing of veg oils: avoids adding of oils as input to FAME and output of crush
        $iftheni.gf23 %detailedProducts%==yes
               $ (not (toFAME(ALLPROCESS) $ vegoil(allItem)))
        $endif.gf23
              ,PROCESS_COMPARE2(GLOBIOMragg,ALLPROCESS,ALLITEM,macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_DEMAND(values):
    r"""p_DEMAND(GLOBIOMragg, ALLITEM, SelecScen, ScenYear): the scenario's demand records
    (DemQuantity_Compare) summed.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1402-1404):

        p_DEMAND(GLOBIOMragg,ALLITEM,SelecScen,ScenYear)
        = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,
             DemQuantity_Compare(ALLITEM,GLOBIOMragg,"Level",macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_SUPPLY(values):
    r"""p_SUPPLY(GLOBIOMragg, ALLITEM, SelecScen, ScenYear): the scenario's supply records
    (SupQuantity_Compare) summed.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1406-1408):

        p_SUPPLY(GLOBIOMragg,ALLITEM,SelecScen,ScenYear)
        = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,
             SupQuantity_Compare(ALLITEM,GLOBIOMragg,"Level",macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_FEED(values):
    r"""p_FEED(GLOBIOMragg, ALLITEM, SelecScen, ScenYear): the scenario's feed records (FeedQuantity_Compare)
    summed.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1410-1412):

        p_FEED(GLOBIOMragg,ALLITEM,SelecScen,ScenYear)
        = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,
             FeedQuantity_Compare(ALLITEM,GLOBIOMragg,"Level",macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_CROP_AREA(values):
    r"""p_CROP_AREA(GLOBIOMcountry, CRP, SelecScen, ScenYear): GLOBIOM's countries' crop area records
    (ACR_COMPARE) summed over the cells, the AEZ classes and the crop technologies.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1460-1462):

        p_CROP_AREA(GLOBIOMcountry,%CRP%,SelecScen,ScenYear)
        = sum((allcolrow,AEZCLASS,CROPTECH,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)),
              ACR_COMPARE(GLOBIOMcountry,allcolrow,"Alti_Any","Slp_Any","Soil_Any",AEZCLASS,%CRP%,CROPTECH,macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_LAND(values):
    r"""p_LAND(GLOBIOMcountry, allLC_TYPE, SelecScen, ScenYear): GLOBIOM's countries' land records summed over
    the cells and the AEZ classes.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1464-1466):

        p_LAND(GLOBIOMcountry,allLC_TYPE,SelecScen,ScenYear)
        = sum((allcolrow,AEZCLASS,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)) ,
              %land_name%(GLOBIOMcountry,allcolrow,"Alti_Any","Slp_Any","Soil_Any",AEZCLASS,allLC_Type,macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_LIVESTOCK(any_values, cell_values):
    r"""p_LIVESTOCK(GLOBIOMcountry, ANIMAL, SelecScen, ScenYear): the herd of AnyColRow and aez_any, else the cells'
    of the other AEZ classes summed.

    CAPRI's GAMS (global/convert_globiom.gms l. 1451-1458):

        p_LIVESTOCK(GLOBIOMcountry,ANIMAL,SelecScen,ScenYear)
        = sum((rLIVE_SYSTEM,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)),
              LIVE_COMPARE(GLOBIOMcountry,"AnyColRow","Alti_Any","Slp_Any","Soil_Any","aez_any",rLIVE_SYSTEM,ANIMAL,macroScen,BioenScen,IEAscen,ScenYear))
        + sum((allcolrow,aez_not_any,rLIVE_SYSTEM,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)),
              LIVE_COMPARE(GLOBIOMcountry,allcolrow,"Alti_Any","Slp_Any","Soil_Any",aez_not_any,rLIVE_SYSTEM,ANIMAL,macroScen,BioenScen,IEAscen,ScenYear))
        *  avoid double counting if some LIVE_COMPARE versions have (eg) BOVD totals on aez_any plus the diaggregate info on aez_not_any:
         $ (Not sum((rLIVE_SYSTEM,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)),
              LIVE_COMPARE(GLOBIOMcountry,"AnyColRow","Alti_Any","Slp_Any","Soil_Any","aez_any",rLIVE_SYSTEM,ANIMAL,macroScen,BioenScen,IEAscen,ScenYear)));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    a = 0.0
    for v in any_values:
        a += v
    c = 0.0
    for v in cell_values:
        c += v
    return a + (c if not a else 0.0)


def p_CROP_AREA_ligherba(area, values):
    r"""p_CROP_AREA(GLOBIOMregion, "ligherba", SelecScen, ScenYear): the perennial area (PERENNIAL_COMPARE) summed
    over the cells and AEZ classes.

    area: the area before the statement (from ACR_COMPARE's LIGHERBA records, where any).

    CAPRI's GAMS (global/convert_globiom.gms l. 1469-1471):

        p_CROP_AREA(GLOBIOMregion,"ligherba",SelecScen,ScenYear)
        = sum((allcolrow,AEZCLASS,SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen)) ,
              PERENNIAL_COMPARE(GLOBIOMregion,allcolrow,"Alti_Any","Slp_Any","Soil_Any",AEZCLASS,macroScen,BioenScen,IEAscen,ScenYear));

    Departures from CAPRI: CAPRI assigns the perennial sum; the port adds it to the crop area's LIGHERBA records (none in GLOBIOM-EU's files:
    the conversion test's results equal CAPRI's); the domain condition and the loops in the caller (globiom.py)."""
    for v in values:
        area = area + v
    return area


def p_LIVESTOCK_ragg(values):
    r"""p_LIVESTOCK(GLOBIOMragg, ANIMAL, SelecScen, ScenYear): GLOBIOM's countries' herds summed
    to its regions (REGION58_COUNTRY_MAP).

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1474-1475):

        p_LIVESTOCK(GLOBIOMragg,ANIMAL,SelecScen,ScenYear)
        = sum(REGION%Nragg%_COUNTRY_MAP(GLOBIOMragg,GLOBIOMCOUNTRY),p_LIVESTOCK(GLOBIOMcountry,ANIMAL,SelecScen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_CROP_AREA_ragg(values):
    r"""p_CROP_AREA(GLOBIOMragg, CRP, SelecScen, ScenYear): GLOBIOM's countries' crop areas summed to
    its regions (REGION58_COUNTRY_MAP).

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1476-1477):

        p_CROP_AREA(GLOBIOMragg,%CRP%,SelecScen,ScenYear)
        = sum(REGION%Nragg%_COUNTRY_MAP(GLOBIOMragg,GLOBIOMCOUNTRY),p_CROP_AREA(GLOBIOMcountry,%CRP%,SelecScen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_LAND_ragg(values):
    r"""p_LAND(GLOBIOMragg, allLC_TYPE, SelecScen, ScenYear): GLOBIOM's countries' land summed to its
    regions (REGION58_COUNTRY_MAP).

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1478-1479):

        p_LAND(GLOBIOMragg,allLC_TYPE,SelecScen,ScenYear)
        = sum(REGION%Nragg%_COUNTRY_MAP(GLOBIOMragg,GLOBIOMCOUNTRY),p_LAND(GLOBIOMcountry,allLC_TYPE,SelecScen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_GLOBIOM(value):
    r"""p_GLOBIOM(GLOBIOMragg, ., ., SelecScen, ScenYear): land use, macro data, herds and crop areas (LEVEL), prices,
    supply (ProdQ), demand (DN), processing (BIOM), feed (FTN) of GLOBIOM's columns and rows; the processing products'
    processing as their production (PRODQ).

    CAPRI's GAMS (global/convert_globiom.gms l. 1586-1586):

        p_GLOBIOM(GLOBIOMragg,GLOBIOMcols,"LEVEL",SelecScen,ScenYear)  = SUM(SAMEAS(GLobiomCols,allLC_Type),p_LAND(GLOBIOMragg,allLC_TYPE,SelecScen,ScenYear)) ;

    CAPRI's GAMS (global/convert_globiom.gms l. 1588-1589):

        p_GLOBIOM(GLOBIOMregion,GLOBIOMmacro,"LEVEL",SelecScen,LongYr)
                  = SUM(SelecScen_map(selecScen,macroScen,bioEnScen,IEAscen) ,p_MACRO(GLOBIOMregion,GLOBIOMmacro,macroScen,LongYr));

    CAPRI's GAMS (global/convert_globiom.gms l. 1590-1590):

        p_GLOBIOM(GLOBIOMragg,ANIMAL,"LEVEL",SelecScen,ScenYear) $ GLobiomCols(ANIMAL) = p_LIVESTOCK(GLOBIOMragg,ANIMAL,SelecScen,ScenYear) ;

    CAPRI's GAMS (global/convert_globiom.gms l. 1591-1591):

        p_GLOBIOM(GLOBIOMragg,%CRP%,"LEVEL",SelecScen,ScenYear) $ GLobiomCols(%CRP%) = p_CROP_AREA(GLOBIOMragg,%CRP%,SelecScen,ScenYear)  ;

    CAPRI's GAMS (global/convert_globiom.gms l. 1592-1592):

        p_GLOBIOM(GLOBIOMragg,"Price",GLOBIOMrows,SelecScen,ScenYear) = p_PRICE(GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear) ;

    CAPRI's GAMS (global/convert_globiom.gms l. 1593-1593):

        p_GLOBIOM(GLOBIOMragg,"ProdQ",GLOBIOMrows,SelecScen,ScenYear) = p_supply(GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear);

    CAPRI's GAMS (global/convert_globiom.gms l. 1594-1594):

        p_GLOBIOM(GLOBIOMragg,"DN",GLOBIOMrows,SelecScen,ScenYear) = p_demand(GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear);

    CAPRI's GAMS (global/convert_globiom.gms l. 1597-1597):

        p_GLOBIOM(GLOBIOMragg,"BIOM",GLOBIOMrows,SelecScen,ScenYear) = p_process(GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear);

    CAPRI's GAMS (global/convert_globiom.gms l. 1598-1598):

        p_GLOBIOM(GLOBIOMragg,"FTN",GLOBIOMrows,SelecScen,ScenYear) = p_feed(GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear);

    CAPRI's GAMS (global/convert_globiom.gms l. 1601-1601):

        p_GLOBIOM(GLOBIOMragg,"PRODQ",PROCPR,SelecScen,ScenYear) $ GLobiomrows(PROCPR) = p_GLOBIOM(GLOBIOMragg,"BIOM",PROCPR,SelecScen,ScenYear);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value


def p_GLOBIOM_trade(values):
    r"""p_GLOBIOM(GLOBIOMragg, EXPTA / IMPTA, GLOBIOMrows, SelecScen, ScenYear): the region's trade flows summed over
    the partners.

    CAPRI's GAMS (global/convert_globiom.gms l. 1595-1595):

        p_GLOBIOM(GLOBIOMragg,"EXPTA",GLOBIOMrows,SelecScen,ScenYear) = sum(GLOBIOMragg1,p_globiomTrade(GLOBIOMragg1,GLOBIOMragg,GLOBIOMrows,SelecScen,ScenYear));

    CAPRI's GAMS (global/convert_globiom.gms l. 1596-1596):

        p_GLOBIOM(GLOBIOMragg,"IMPTA",GLOBIOMrows,SelecScen,ScenYear) = sum(GLOBIOMragg1,p_globiomTrade(GLOBIOMragg,GLOBIOMragg1,GLOBIOMrows,SelecScen,ScenYear));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    t = 0.0
    for v in values:
        t += v
    return t


def p_GLOBIOM_ALMILK(bvmilk, sgmilk):
    r"""p_GLOBIOM(GLOBIOMragg, "PRODQ", "ALMILK", SelecScen, ScenYear): cow and sheep and goat milk.

    CAPRI's GAMS (global/convert_globiom.gms l. 1599-1600):

        p_GLOBIOM(GLOBIOMragg,"PRODQ","ALMILK",SelecScen,ScenYear) = p_GLOBIOM(GLOBIOMragg,"PRODQ","BVMILK",SelecScen,ScenYear) +
                                                           p_GLOBIOM(GLOBIOMragg,"PRODQ","SGMILK",SelecScen,ScenYear);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return bvmilk + sgmilk


def p_GLOBIOM_BIOM_PROCPR():
    r"""p_GLOBIOM(GLOBIOMragg, "BIOM", PROCPR, SelecScen, ScenYear): removed (the processing products' production).

    CAPRI's GAMS (global/convert_globiom.gms l. 1602-1602):

        p_GLOBIOM(GLOBIOMragg,"BIOM",PROCPR,SelecScen,ScenYear) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return 0.0


def p_GLOBIOM_DG(biom, process_yield):
    r"""p_GLOBIOM(GLOBIOMragg, "PRODQ", Corn_Dg / Whea_Dg, SelecScen, ScenYear): the processing of maize or wheat times
    the distillers' grains' yield of the ethanol process (processData).

    CAPRI's GAMS (global/convert_globiom.gms l. 1603-1604):

        p_GLOBIOM(GLOBIOMragg,"PRODQ","Corn_Dg",SelecScen,ScenYear) = p_GLOBIOM(GLOBIOMragg,"BIOM","Corn",SelecScen,ScenYear) *
                                                               processData(GLOBIOMragg,"CorntoEthol","Corn_DG");

    CAPRI's GAMS (global/convert_globiom.gms l. 1605-1606):

        p_GLOBIOM(GLOBIOMragg,"PRODQ","Whea_Dg",SelecScen,ScenYear) = p_GLOBIOM(GLOBIOMragg,"BIOM","Whea",SelecScen,ScenYear) *
                                                               processData(GLOBIOMragg,"WheatoEthol","Whea_DG");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return biom * process_yield


def p_GLOBIOMmappedCols(values):
    r"""p_GLOBIOMmappedCols(RMall, COLSMappedToGlobiom, GLOBIOMROWSmapped, SelecScen, longYrSel) but UVAP: GLOBIOM's
    regions' values summed over the region's GLOBIOM regions and the columns mapped.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1743-1746):

                       p_GLOBIOMmappedCols(RMall,COLSMappedToGlobiom,GLOBIOMROWSmapped,SelecScen,longYrSel)
                             $ (not sameas(colsMappedToGlobiom,"UVAP"))
                             = SUM((rmAll_to_GLOBIOM(RMALL,GLOBIOMragg),COLS_TO_GLOBIOM(COLSMappedToGlobiom,GLOBIOMCOLSMapped)),
                                    p_GLOBIOM(GLOBIOMragg,GLOBIOMcolsMapped,GLOBIOMrowsMapped,SelecScen,longYrSel));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_GLOBIOMmapped_rows(values):
    r"""p_GLOBIOMmapped(RMall, COLSMappedToGlobiom, ROWSMappedToGlobiom, SelecScen, longYrSel): the mapped columns'
    values summed over the GLOBIOM rows mapped to CAPRI's row.

    values: the records in the file's order.

    CAPRI's GAMS (global/convert_globiom.gms l. 1757-1759):

                       p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSel)
                             = SUM(rows_TO_GLOBIOM(RowsMappedToGlobiom,GLOBIOMrowsMapped),
                                    p_GLOBIOMmappedCOLS(RMall,COLSMappedToGlobiom,GLOBIOMrowsMapped,SelecScen,longYrSel));

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    return _added(values)


def p_GLOBIOMmappedCols_UVAP(pairs):
    r"""p_GLOBIOMmappedCols(RMall, "UVAP", GLOBIOMROWSmapped, SelecScen, longYrSel) with production: the prices of the
    region's GLOBIOM regions weighted by their production.

    pairs: (PRICE, PRODQ) of the GLOBIOM regions with production.

    CAPRI's GAMS (global/convert_globiom.gms l. 1748-1755):

                       p_GLOBIOMmappedCols(RMall,"UVAP",GLOBIOMROWSmapped,SelecScen,longYrSel)
                             $ SUM((rmAll_to_GLOBIOM(RMALL,GLOBIOMragg)),
                                    p_GLOBIOM(GLOBIOMragg,"PRODQ",GLOBIOMrowsMapped,SelecScen,longYrSel))
                             = SUM((rmAll_to_GLOBIOM(RMALL,GLOBIOMragg)),
                                    p_GLOBIOM(GLOBIOMragg,"PRICE",GLOBIOMrowsMapped,SelecScen,longYrSel)
                                   *p_GLOBIOM(GLOBIOMragg,"PRODQ",GLOBIOMrowsMapped,SelecScen,longYrSel))
                             / SUM((rmAll_to_GLOBIOM(RMALL,GLOBIOMragg)),
                                    p_GLOBIOM(GLOBIOMragg,"PRODQ",GLOBIOMrowsMapped,SelecScen,longYrSel));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    num = 0.0
    den = 0.0
    for p, q in pairs:
        num += p * q
        den += q
    return num / den


def p_GLOBIOMmapped_B2000(value):
    r"""p_GLOBIOMmapped(RMall, ., ., SelecScen, 'B2000'): 2000's values (2000 then removed, l. 1874);
    p_globiomInfo(RMall, ., ., 'data', SelecScen, longYrSel): the mapped values.

    CAPRI's GAMS (global/convert_globiom.gms l. 1872-1873):

             p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'B2000')
                = p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'2000') ;

    CAPRI's GAMS (global/convert_globiom.gms l. 1913-1914):

             p_globiomInfo(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,'data',SelecScen,longYrSel)
                = p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSel) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value


def p_GLOBIOMmapped_SUGA(suga, sugb):
    r"""p_GLOBIOMmapped(RMALL, MrkPos, "SUGA", SelecScen, longYrSel): sugar from cane (9.4%) and beet (15%).

    CAPRI's GAMS (global/convert_globiom.gms l. 1884-1887):

             p_GLOBIOMmapped(RMALL,MrkPos,"SUGA",SelecScen,longYrSel)
        *         Remember mapping of cane to SUGA above:
                = p_GLOBIOMmapped(RMALL,MrkPos,"SUGA",SelecScen,longYrSel) * p_prcy("SUGC")
                + p_GLOBIOMmapped(RMALL,MrkPos,"SUGB",SelecScen,longYrSel) * p_prcy("SUGB");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return suga * 0.094 + sugb * 0.15


def p_GLOBIOMmapped_removed():
    r"""p_GLOBIOMmapped(., '2000') once copied to B2000; p_GLOBIOMmapped(RMALL, MrkPos, "SUGB", ., .) but PROD once in
    SUGA: removed.

    CAPRI's GAMS (global/convert_globiom.gms l. 1874-1874):

             p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'2000') = 0;

    CAPRI's GAMS (global/convert_globiom.gms l. 1889-1889):

             p_GLOBIOMmapped(RMALL,MrkPos,"SUGB",SelecScen,longYrSel) $ (NOT SAMEAS(MrkPos,"PROD")) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return 0.0


def p_globiomInfo_factorB2000_removed():
    r"""p_globiomInfo's factorB2000 of NECR and of the demand and trade positions (shares instead): removed.

    CAPRI's GAMS (global/convert_globiom.gms l. 1976-1976):

          p_globiomInfo(RMALL,'NECR',rows,'factorB2000',SelecScen,longYrSel) = 0;

    CAPRI's GAMS (global/convert_globiom.gms l. 1993-1993):

          p_globiomInfo(RMALL,DemPosDis,rows,'factorB2000',SelecScen,longYrSel) = 0;

    CAPRI's GAMS (global/convert_globiom.gms l. 2006-2006):

          p_globiomInfo(RMALL,TradePos,rows,'factorB2000',SelecScen,longYrSel) = 0;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return 0.0


def p_GLOBIOMmapped_DOMM(hcom, biof, fedm):
    r"""p_GLOBIOMmapped(RMALL, "DOMM", ROWSMappedToGlobiom, SelecScen, longYrSel): human consumption, biofuel use and
    feed.

    CAPRI's GAMS (global/convert_globiom.gms l. 1894-1897):

             p_GLOBIOMmapped(RMALL,"DOMM",ROWSMappedToGlobiom,SelecScen,longYrSel)
                 = p_GLOBIOMmapped(RMALL,"HCOM",ROWSMappedToGlobiom,SelecScen,longYrSel)
                 + p_GLOBIOMmapped(RMALL,"BIOF",ROWSMappedToGlobiom,SelecScen,longYrSel)
                 + p_GLOBIOMmapped(RMALL,"FEDM",ROWSMappedToGlobiom,SelecScen,longYrSel);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return hcom + biof + fedm


def p_GLOBIOMmapped_DOMM_PROD(value):
    r"""p_GLOBIOMmapped(RMALL, "DOMM", COMI / SGMI / SUGB, ., .): production; p_GLOBIOMmapped(RMALL, "PROD",
    youngHeif, ., .): the heifers' herd (HEIR.LEVL).

    CAPRI's GAMS (global/convert_globiom.gms l. 1900-1903):

             p_GLOBIOMmapped(RMALL,"DOMM",ROWSMappedToGlobiom,SelecScen,longYrSel) $ (   SAMEAS(RowsMappedToGlobiom,"COMI")
                                                                                          or SAMEAS(RowsMappedToGlobiom,"SGMI")
                                                                                          or SAMEAS(RowsMappedToGlobiom,"SUGB"))
                 = p_GLOBIOMmapped(RMALL,"PROD",ROWSMappedToGlobiom,SelecScen,longYrSel);

    CAPRI's GAMS (global/convert_globiom.gms l. 1911-1911):

             p_GLOBIOMmapped(RMALL,"PROD",youngHeif,SelecScen,longYrSel)    = p_GLOBIOMmapped(RMALL,"HEIR","LEVL",SelecScen,longYrSel);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value


def p_GLOBIOMmapped_World_UVAP(triples):
    r"""p_GLOBIOMmapped("World", "UVAP", ROWSMappedToGlobiom, SelecScen, longYrSel): the market regions' prices
    weighted by production plus demand, where there are any.

    triples: (UVAP, PROD, DOMM) of the world's market regions.

    CAPRI's GAMS (global/convert_globiom.gms l. 1919-1927):

             p_GLOBIOMmapped("World","UVAP",ROWSMappedToGlobiom,SelecScen,longYrSel)
                 $ SUM(RW_TO_RM("World",RM), (p_GLOBIOMmapped(RM,"PROD",ROWSMappedToGlobiom,SelecScen,longYrSel)
                                             +p_GLOBIOMmapped(RM,"DOMM",ROWSMappedToGlobiom,SelecScen,longYrSel)))
                 = SUM(RW_TO_RM("World",RM),  p_GLOBIOMmapped(RM,"UVAP",ROWSMappedToGlobiom,SelecScen,longYrSel)
                                            *(p_GLOBIOMmapped(RM,"PROD",ROWSMappedToGlobiom,SelecScen,longYrSel)
                                             +p_GLOBIOMmapped(RM,"DOMM",ROWSMappedToGlobiom,SelecScen,longYrSel)))
                 / SUM(RW_TO_RM("World",RM), (p_GLOBIOMmapped(RM,"PROD",ROWSMappedToGlobiom,SelecScen,longYrSel)
                                             +p_GLOBIOMmapped(RM,"DOMM",ROWSMappedToGlobiom,SelecScen,longYrSel)))
                 ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return sum(u * (p + d) for u, p, d in triples) / sum(p + d for u, p, d in triples)


def p_globiomInfo_factorB2000(value, b2000):
    r"""p_globiomInfo(RMall, ., ., 'factorB2000', SelecScen, longYrSelWo00) where B2000 is positive (BIOF not): the
    year's value over B2000's, 1E-6 where the year has none.

    CAPRI's GAMS (global/convert_globiom.gms l. 1938-1944):

             p_globiomInfo(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,'factorB2000',SelecScen,longYrSelWo00)
                            $ ( (p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'B2000') gt eps)
                              $ (Not SAMEAS(COLSMappedToGlobiom,'BIOF')))
                 = (  p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSelWo00)
                   /  p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'B2000')  )
                                   $        p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSelWo00)
                   + 1e-6          $ (NOT   p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSelWo00)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value / b2000 if value else 1e-6


def p_globiomInfo_factorB2000_one():
    r"""p_globiomInfo(RMall, ., ., 'factorB2000', SelecScen, longYrSelWo00) of the market and world regions where
    neither B2000 nor the year has a positive value, of a position with projections: 1.

    CAPRI's GAMS (global/convert_globiom.gms l. 1948-1956):

             p_globiomInfo(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,'factorB2000',SelecScen,longYrSelWo00)
                            $ ( (p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,'B2000') le eps)
                              $ (p_GLOBIOMmapped(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,SelecScen,longYrSelWo00) le eps)
                              $ (Not p_globiomInfo(RMall,COLSMappedToGlobiom,ROWSMappedToGlobiom,'factorB2000',SelecScen,longYrSelWo00))
                              $ nonEmptyColsRows(COLSMappedToGlobiom,ROWSMappedToGlobiom)
                              $ (Not SAMEAS(COLSMappedToGlobiom,'BIOF'))
        *                       no assignment of 1 to irrelevant regions like "EU", "RW", "Allimporters" etc
                              $ (RM(RMall) or RMS(RMall) or RW(RMall)))
                 = 1;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return 1.0


def p_globiomInfo_factorB2000_RM(values):
    r"""p_globiomInfo(RM, macro, "LEVL", 'factorB2000', SelecScen, longYrSelWo00) without a value: the mean of its
    parts' factors (those with one).

    values: the parts' factors, zeros included.

    CAPRI's GAMS (global/convert_globiom.gms l. 1969-1973):

          p_globiomInfo(RM,macro,"LEVL",'factorB2000',SelecScen,longYrSelWo00) $ (    (NOT p_globiomInfo(RM,macro,"LEVL",'factorB2000',SelecScen,longYrSelWo00))
                                                                   and SUM(RMS_TO_RM(RMS,RM) $ p_globiomInfo(RMS,macro,"LEVL",'factorB2000',SelecScen,longYrSelWo00),1))

               = SUM(RMS_TO_RM(RMS,RM), p_globiomInfo(RMS,macro,"LEVL",'factorB2000',SelecScen,longYrSelWo00))
               / SUM(RMS_TO_RM(RMS,RM) $ p_globiomInfo(RMS,macro,"LEVL",'factorB2000',SelecScen,longYrSelWo00),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    n = sum(1 for v in values if v)
    return sum(values) / n


def p_globiomInfo_share_DemPosDis(value, domm):
    r"""p_globiomInfo(RMALL, DemPosDis, rows, 'share', SelecScen, longYrSel) with demand: the demand component's share
    of DOMM.

    CAPRI's GAMS (global/convert_globiom.gms l. 1989-1990):

          p_globiomInfo(RMALL,DemPosDis,rows,'share',SelecScen,longYrSel) $ p_GLOBIOMmapped(RMALL,"DOMM",ROWS,SelecScen,longYrSel)
                 =p_GLOBIOMmapped(RMALL,DemPosDis,ROWS,SelecScen,longYrSel)/p_GLOBIOMmapped(RMALL,"DOMM",ROWS,SelecScen,longYrSel);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value / domm


def p_globiomInfo_share_TradePos(value, domm, prod):
    r"""p_globiomInfo(RMALL, TradePos, rows, 'share', SelecScen, longYrSel): imports or exports over demand plus
    production, where there are any.

    CAPRI's GAMS (global/convert_globiom.gms l. 2000-2003):

          p_globiomInfo(RMALL,TradePos,rows,'share',SelecScen,longYrSel)
                 $ (p_GLOBIOMmapped(RMALL,"DOMM",ROWS,SelecScen,longYrSel)+p_GLOBIOMmapped(RMALL,"PROD",ROWS,SelecScen,longYrSel))
                 =  p_GLOBIOMmapped(RMALL,TradePos,ROWS,SelecScen,longYrSel)
                 / (p_GLOBIOMmapped(RMALL,"DOMM",ROWS,SelecScen,longYrSel)+p_GLOBIOMmapped(RMALL,"PROD",ROWS,SelecScen,longYrSel));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value / (domm + prod)


def p_baseDat_mean(values):
    r"""p_baseDat(., ., ., Bas00AndBAS): the mean of the three years of B2000 (1999-2001) or of the base year, of
    CAPREG's time series (NUTS0) and p_worldPop (INHA.LEVL).

    CAPRI's GAMS (global/convert_globiom.gms l. 2053-2055):

                p_baseDat(NUTS0,projCols,projRows,Bas00AndBAS) $ projColsRows(projCols,projRows)
        *          NOTE: The completions in create_longrun_info.gms have ensured that P_CAPREGDATA is filled completely on BasCur
                = SUM(BasCUR, P_capregData(NUTS0,projCols,projRows,BasCUR))/3;

    CAPRI's GAMS (global/convert_globiom.gms l. 2102-2102):

               p_baseDat(RMall,"INHA","LEVL",Bas00AndBAS) = SUM(BasCUR, p_worldPop(BasCur,RMALL) )/3;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return sum(values) / 3


def p_baseDat_dataMarket(values):
    r"""p_baseDat(RMall, projCols, projRows, Bas00AndBAS) of the regions but the member states (GDP of all): the mean
    of p_dataMarket's three years.

    CAPRI's GAMS (global/convert_globiom.gms l. 2096-2098):

               p_baseDat(RMall,projCols,projRows,Bas00AndBAS) $ (   ((NOT SUM(SAMEAS(RMALL,NUTS0),1)) or sameas(projCols,"GDP"))
                                                                 $  projColsRows(projCols,projRows))
               = SUM(BasCUR, p_dataMarket(RMAll,projCols,projRows,BasCUR))/3;

    Departures from CAPRI: the values are added one at a time in their order (as the port accumulated them; Python's sum() is compensated);
    the domain condition and the loops in the caller (globiom.py)."""
    t = 0.0
    for v in values:
        t += v
    return t / 3


def p_baseDat_YILD(yields, levels):
    r"""p_baseDat(NUTS0, projCols, "YILD", Bas00AndBAS) with a level: the yields weighted by the levels.

    CAPRI's GAMS (global/convert_globiom.gms l. 2058-2061):

                p_baseDat(NUTS0,projCols,"YILD",Bas00AndBAS)
                $ (SUM(BasCUR,P_capregData(NUTS0,projCols,"LEVL",BasCUR)) )
                = SUM(BasCUR,P_capregData(NUTS0,projCols,"YILD",BasCUR) * P_capregData(NUTS0,projCols,"LEVL",BasCUR))
                / SUM(BasCUR,                                      P_capregData(NUTS0,projCols,"LEVL",BasCUR)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return sum(y * lv for y, lv in zip(yields, levels)) / sum(levels)


def p_baseDat_UVAP(prices, grof):
    r"""p_baseDat(NUTS0, "UVAP", projRows, Bas00AndBAS): the prices weighted by gross production (1 where there is
    none).

    CAPRI's GAMS (global/convert_globiom.gms l. 2064-2067):

                p_baseDat(NUTS0,"UVAP",projRows,Bas00AndBAS)
                = SUM(BasCUR, (P_capregData(NUTS0,"UVAP",projRows,BasCUR) )
                            * (P_capregData(NUTS0,"GROF",projRows,BasCUR) + 1 $ (NOT P_capregData(NUTS0,"GROF",projRows,BasCUR))))
                / SUM(BasCUR, (P_capregData(NUTS0,"GROF",projRows,BasCUR) + 1 $ (NOT P_capregData(NUTS0,"GROF",projRows,BasCUR))));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    wts = [x if x else 1.0 for x in grof]
    return sum(u * w for u, w in zip(prices, wts)) / sum(wts)


def p_dataMarket_1999(value_2000):
    r"""p_dataMarket(RMAll, projCols, projRows, "1999") without a value, for B2000: 2000's.

    CAPRI's GAMS (global/convert_globiom.gms l. 2075-2080):

               p_dataMarket(RMAll,projCols,projRows,"1999") $ (   (NOT p_dataMarket(RMAll,projCols,projRows,"1999"))
                                                                $ p_dataMarket(RMAll,projCols,projRows,"2000")
                                                                $ ((NOT SUM(SAMEAS(RMALL,NUTS0),1)) or sameas(projCols,"GDP"))
                                                                $ projColsRows(projCols,projRows)
                                                                $ SAMEAS(Bas00AndBAS,"B2000") )
               = p_dataMarket(RMAll,projCols,projRows,"2000");

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return value_2000


def p_globiomInfo_share_landuse(data, base):
    r"""p_globiomInfo(rmAll, Cols, "LEVL", 'share', SelecScen, "B2000") of the land uses of the member states:
    GLOBIOM's B2000 over CAPRI's (at least 0.001).

    CAPRI's GAMS (global/convert_globiom.gms l. 2125-2126):

            p_globiomInfo(rmAll,Cols,"LEVL",'share',SelecScen,"B2000") $ (landuseARTO(cols) $ MSall(rmAll))
                  = p_globiomInfo(rmAll,Cols,"LEVL",'data',SelecScen,"B2000") / MAX(.001, p_baseDat(rmAll,Cols,"LEVL","B2000")) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return data / max(.001, base)


def p_globiomInfo_factorB2000_BAS(base, b2000):
    r"""p_globiomInfo(RMALL, projCols, projRows, 'factorB2000', SelecScen, "20%BAS%") of a projected position: one plus
    the change from B2000 to the base year where both are positive, at least 0.1.

    CAPRI's GAMS (global/convert_globiom.gms l. 2131-2140):

            p_globiomInfo(RMALL,projCols,projRows,'factorB2000',SelecScen,"20%BAS%")
               $ SUM(longYrSelWo00, p_globiomInfo(RMall,projcols,projrows,'factorB2000',SelecScen,longYrSelWo00))
        *        small change factors relative to 2000 may give huge change factors relative to BAS =>
               = MAX(.1,(  1.
        *                If we are lacking one nonzero Basedat, assume a change factor of 1 from B2000 to BAS
        *                (better than loosing the information altogether)
                         + (p_baseDat(RMall,projCols,projRows,"20%BAS%")/p_baseDat(RMall,projCols,projRows,"B2000")-1)
                            $ (    (p_baseDat(RMall,projCols,projRows,"20%BAS%") GT 0)
                               and (p_baseDat(RMall,projCols,projRows,"B2000") GT 0))
                            ));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return max(.1, 1. + ((base / b2000 - 1) if (base > 0 and b2000 > 0) else 0.0))


def p_globiomInfo_GDP_real(factor, years):
    r"""p_globiomInfo(RMALL, "GDP", "LEVL", 'factorB2000', SelecScen, "20%BAS%"): in real terms (1.9% inflation a
    year).

    years: the base year less 2000.

    CAPRI's GAMS (global/convert_globiom.gms l. 2144-2145):

            p_globiomInfo(RMALL,"GDP","LEVL",'factorB2000',SelecScen,"20%BAS%")
               = p_globiomInfo(RMALL,"GDP","LEVL",'factorB2000',SelecScen,"20%BAS%")/1.019**(calyea("20%BAS%")-calyea("2000"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (globiom (collect, mapped, factors, base_factors))."""
    return factor / 1.019 ** years

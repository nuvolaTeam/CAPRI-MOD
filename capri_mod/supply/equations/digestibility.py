"""CAPRI's composition of the feeds per regional unit and cattle activity (envind/digestibility.gms, the standard path
with GHGLCA off; CAPRI star 3.0), the statements the model's builders take from it: the dry-matter contents, the grass and
other fodder rows, the fat of the products, and the feed bulks' values as the member state's feed-use weighted means of
their products'.

Used by tools/lib/_capri_digest.py (the ration's fibre and fat for 3-NOP, tools/build/build_supplement_effects.py; the
feed bulks' ether extract for the ration's fat limit SupplementPerc_, tools/build/build_supplement_fat.py). CAPRI's
table p_digestPar("EU", "DCOL", product, item) (envind/def_digestibility.gms) with its DEF_PRD fill (l. 37-38) is read by
_capri_digest.table(); every regional unit and cattle activity starts from it (l. 41).

In this project's notation: g the grazing share of the activity (p_NEMIDAT TypeShare GRAZ), n the member state's grass
N-fixation rate after l. 44-45, s the region's fodder legume share (DATA(RU, FLEG, LEVL)), T(row) the table's value of an
item, w(row) the member state's feed use (FEDM + INTF) of a product times its dry-matter content in the unit.
The rest of the file, for the methane of enteric fermentation and manure (envind/gases.gms; capri_mod/environmental/
equations/gases.py): CAPRI's own fibre and crude protein where they agree with the table (l. 64-94), the NRC 2001
energy chain to the digestible and gross energy (l. 97-143), the discount for the intake above maintenance (l. 146-170)
and the ration's digestibility, ash and gross energy per cattle activity (l. 241-253). Not ported: the GHGLCA path
(l. 174-196, off in CAPRI's runs), the items stored for checking (l. 260-284) and clean_digestibility.gms (l. 286, off
where capmod calls the file). p_emisFeed's gross energy (l. 255-258) is ported: %CH4ENTfromFEED% is on in capmod and
CAPREG (capmod/set_global_variables.gms l. 226, capreg/set_global_variables.gms l. 143); until 25 November 2026 this
docstring said it was off, which was wrong.
"""
from __future__ import annotations


def p_DryMatterContent(DATA_RU_DRMA, DATA_MS_DRMA):
    r"""p_DryMatterContent(RU, ROWS): the unit's dry-matter content of a product, the member state's where the unit has
    none (l. 31-33).

    CAPRI's GAMS (envind/digestibility.gms l. 31-33):

        p_DryMatterContent(RU,ROWS )  = DATA(RU,"DRMA",ROWS,%1) + DATA(RU,"DRMA",ROWS,%lY%) $ (NOT DATA(RU,"DRMA",ROWS,%1));
        p_DryMatterContent(RU,ROWS )  $ (NOT p_DryMatterContent(RU,ROWS ))
                                     = sum(MAP_RR(MS,RU),DATA(MS,"DRMA",ROWS,%1)+DATA(MS,"DRMA",ROWS,%lY%) $ (NOT DATA(MS,"DRMA",ROWS,%1)));

    The dumps the builders read (CAPRI's 2017 regional results) carry the year Y alone (%1 and %lY% the same).
    Departures from CAPRI: none."""
    v = float(DATA_RU_DRMA or 0.0)
    return v if v else float(DATA_MS_DRMA or 0.0)


def p_nfixRate_gras_digest(p_nfixRate_gras_MS):
    r"""p_nfixRate_gras(MS) as digestibility.gms uses it: 0.05 where the member state has none, at most 0.75 (l. 44-45).

    CAPRI's GAMS (envind/digestibility.gms l. 44-45):

        p_nfixRate_gras(MS) $ (NOT p_nfixRate_gras(MS)) = 0.05;
        p_nfixRate_gras(MS) = min(p_nfixRate_gras(MS),0.75);

    Departures from CAPRI: none."""
    v = float(p_nfixRate_gras_MS or 0.0)
    return min(v if v else 0.05, 0.75)


def p_digestPar_GRAS(GRAZ, nfix, GRPS, LGPS, GRSI, LGSI, GRHA, LGHA):
    r"""p_digestPar(RU, CATACT, GRAS, item): grazed grass and legume pasture for the grazing share, half silage and half
    hay for the rest, grass and legumes by the grass's fixation rate (l. 49-54).

    CAPRI's GAMS (envind/digestibility.gms l. 49-54):

        p_digestPar(RU,CATACT,"GRAS",DIGSET) =
                                 sum(MAP_RR(MS,RU),p_NEMIDAT(MS,CATACT,"N","TypeShare","GRAZ")
                                 * ((1 - p_nfixRate_gras(MS)/0.75) * p_digestPar("EU","DCOL","GRPS",DIGSET) + p_nfixRate_gras(MS)/0.75 * p_digestPar("EU","DCOL","LGPS",DIGSET)) +
                                (1 - p_NEMIDAT(MS,CATACT,"N","TypeShare","GRAZ"))
                                 * (((1 - p_nfixRate_gras(MS)/0.75) * p_digestPar("EU","DCOL","GRSI",DIGSET) + p_nfixRate_gras(MS)/0.75 * p_digestPar("EU","DCOL","LGSI",DIGSET)) * 0.5 +
                                    ((1 - p_nfixRate_gras(MS)/0.75) * p_digestPar("EU","DCOL","GRHA",DIGSET) + p_nfixRate_gras(MS)/0.75 * p_digestPar("EU","DCOL","LGHA",DIGSET)) * 0.5));

    In this project's notation, with m(a, b) = (1 - n / 0.75) T(a) + n / 0.75 T(b):

        GRAS = g m(GRPS, LGPS) + (1 - g) (0.5 m(GRSI, LGSI) + 0.5 m(GRHA, LGHA))

    Departures from CAPRI: none."""
    k = float(nfix) / 0.75
    mix = lambda a, b: (1 - k) * float(a) + k * float(b)
    g = float(GRAZ)
    return g * mix(GRPS, LGPS) + (1 - g) * (mix(GRSI, LGSI) * 0.5 + mix(GRHA, LGHA) * 0.5)


def p_digestPar_OFAR(GRAS, LGSI, LGHA, FLEG_LEVL):
    r"""p_digestPar(RU, CATACT, OFAR, item) where the unit has fodder legumes: the grass row for the share 1 - s, legume
    silage and hay half and half for s (l. 56-58); elsewhere OFAR keeps the table's value (l. 41).

    CAPRI's GAMS (envind/digestibility.gms l. 56-58):

        p_digestPar(RU,CATACT,"OFAR",DIGSET) $ DATA(RU,"FLEG","LEVL",%1) =
                                 p_digestPar(RU,CATACT,"GRAS",DIGSET) * (1 - DATA(RU,"FLEG","LEVL",%1))
                                 + (0.5 * p_digestPar("EU","DCOL","LGSI",DIGSET) + 0.5 * p_digestPar("EU","DCOL","LGHA",DIGSET)) * DATA(RU,"FLEG","LEVL",%1);

    The caller applies the condition (s > 0). Departures from CAPRI: none."""
    s = float(FLEG_LEVL)
    return float(GRAS) * (1 - s) + (0.5 * float(LGSI) + 0.5 * float(LGHA)) * s


def p_digestPar_FAT(EE, FAT):
    r"""p_digestPar(RU, CATACT, ROWS, FAT): the ether extract less 1 where it is at least 1, the table's value otherwise
    (l. 60).

    CAPRI's GAMS (envind/digestibility.gms l. 60):

        p_digestPar(RU,CATACT,ROWS,"FAT") $ (p_digestPar(RU,CATACT,ROWS,"EE") >= 1) = p_digestPar(RU,CATACT,ROWS,"EE") - 1;

    Departures from CAPRI: none."""
    return float(EE) - 1 if float(EE or 0.0) >= 1 else float(FAT or 0.0)


def p_digestPar_shFEED(w_row, w_rows_of_bulk):
    r"""p_digestPar(RU, FEED, ROWS, shFEED): a product's share in its feed bulk, the member state's feed use (FEDM + INTF)
    times the unit's dry-matter content over the bulk's products' (l. 200-212); none where the bulk's sum is 0.

    CAPRI's GAMS (envind/digestibility.gms l. 200-212):

           p_digestPar(RU,"FEED",ROWS,"shFEED") $ sum((FEED_TO_O(FEED,ROWS1),MAP_RR(MS,RU)) $ FEED_TO_O(FEED,ROWS),
                                               (DATA(MS,"FEDM",ROWS1,%1) + DATA(MS,"FEDM",ROWS1,%lY%) $ (NOT DATA(MS,"FEDM",ROWS1,%1))
                                              + DATA(MS,"INTF",ROWS1,%1) + DATA(MS,"INTF",ROWS1,%lY%) $ (NOT DATA(MS,"INTF",ROWS1,%1)))
                                              * p_DryMatterContent(RU,ROWS1)   )
                                 =sum(MAP_RR(MS,RU),
                                               (DATA(MS,"FEDM",ROWS,%1) + DATA(MS,"FEDM",ROWS,%lY%) $ (NOT DATA(MS,"FEDM",ROWS,%1))
                                              + DATA(MS,"INTF",ROWS,%1) + DATA(MS,"INTF",ROWS,%lY%) $ (NOT DATA(MS,"INTF",ROWS,%1)))
                                              * p_DryMatterContent(RU,ROWS)   )
        *  Using the sum rather than the preassigned FEED ensures reasonable weights even if sum(ROWS)<>FEED
                                 /sum((FEED_TO_O(FEED,ROWS1),MAP_RR(MS,RU)) $ FEED_TO_O(FEED,ROWS),
                                               (DATA(MS,"FEDM",ROWS1,%1) + DATA(MS,"FEDM",ROWS1,%lY%) $ (NOT DATA(MS,"FEDM",ROWS1,%1))
                                              + DATA(MS,"INTF",ROWS1,%1) + DATA(MS,"INTF",ROWS1,%lY%) $ (NOT DATA(MS,"INTF",ROWS1,%1)))
                                              * p_DryMatterContent(RU,ROWS1)  );

    In this project's notation: sh(row) = w(row) / sum_{row' in the bulk} w(row'). Each product is in one bulk of
    FEED_TO_O (capri_data/codes/capri/FEED_TO_O.csv), so the sum over the bulks containing the row is its bulk's.
    Departures from CAPRI: none."""
    W = float(w_rows_of_bulk)
    return float(w_row) / W if W else 0.0


def p_digestPar_FEED(values_rows, shFEED_rows):
    r"""p_digestPar(RU, CATACT, FEED, item) of a feed bulk: its products' values weighted by their shares (l. 214-232:
    DE, GE, ASH, EE, NDF, FAT alike).

    CAPRI's GAMS (envind/digestibility.gms l. 223-225, the ether extract; DE, GE, ASH, NDF and FAT, l. 214-221 and
    227-232, are written the same way):

        *  ether extract is used to calulate the fat content of bulk FEED (in %ghg_abatement% file: envind\line_nitr.gms)
           p_digestPar(RU,CATACT,FEED,"EE") =
                               sum((FEED_TO_O(FEED,ROWS)), p_digestPar(RU,CATACT,ROWS,"EE") * p_digestPar(RU,"FEED",ROWS,"shFEED"));

    In this project's notation: v(FEED) = sum_{row in FEED} v(row) sh(row). Departures from CAPRI: none."""
    return float(sum(float(v) * float(s) for v, s in zip(values_rows, shFEED_rows)))


def p_nutPerDryMt(DATA_item, DM):
    r"""p_nutPerDryMt(RU, CATACT, FIDI | CRPR, ROWS): CAPRI's own fibre or crude protein content of a product per dry
    matter, in percent (l. 64-67); none where the product has no dry-matter content or no content.

    CAPRI's GAMS (envind/digestibility.gms l. 64-67):

        p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) $ (p_DryMatterContent(RU,ROWS) and DATA(RU,"FIDI",ROWS,%1)) =
                                                              DATA(RU,"FIDI",ROWS,%1)/p_DryMatterContent(RU,ROWS) * 100;
        p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) $ (p_DryMatterContent(RU,ROWS)  and DATA(RU,"CRPR",ROWS,%1)) =
                                                              DATA(RU,"CRPR",ROWS,%1)/p_DryMatterContent(RU,ROWS) * 100;

    DATA_item: DATA(RU, FIDI | CRPR, ROWS, "Y"); DM: p_DryMatterContent(RU, ROWS). Departures from CAPRI: none."""
    d, dm = float(DATA_item or 0.0), float(DM or 0.0)
    return d / dm * 100 if (dm and d) else 0.0


def p_nutPerDryMt_bounds(FIDI, CRPR, NDF, CP):
    r"""CAPRI's own contents kept only where both lie within max(20%, 5 points) of the table's NDF and CP: the fibre's
    first, then the crude protein's with the fibre as the first statement left it (l. 73-83). Returns (FIDI, CRPR).

    CAPRI's GAMS (envind/digestibility.gms l. 73-83):

        p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) $
                                                              ((p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) > p_digestPar(RU,CATACT,ROWS,"NDF") + Max(p_digestPar(RU,CATACT,ROWS,"NDF") * 0.2,5)) or
                                (p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) < p_digestPar(RU,CATACT,ROWS,"NDF") - Max(p_digestPar(RU,CATACT,ROWS,"NDF") * 0.2,5)) or
                                (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) > p_digestPar(RU,CATACT,ROWS,"CP") + Max(p_digestPar(RU,CATACT,ROWS,"CP") * 0.2,5))   or
                                (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) < p_digestPar(RU,CATACT,ROWS,"CP") - Max(p_digestPar(RU,CATACT,ROWS,"CP") * 0.2,5))) = 0;

        p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) $
                                                              ((p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) > p_digestPar(RU,CATACT,ROWS,"NDF") + Max(p_digestPar(RU,CATACT,ROWS,"NDF") * 0.2,5)) or
                                (p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) < p_digestPar(RU,CATACT,ROWS,"NDF") - Max(p_digestPar(RU,CATACT,ROWS,"NDF") * 0.2,5)) or
                                (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) > p_digestPar(RU,CATACT,ROWS,"CP") + Max(p_digestPar(RU,CATACT,ROWS,"CP") * 0.2,5))   or
                                (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) < p_digestPar(RU,CATACT,ROWS,"CP") - Max(p_digestPar(RU,CATACT,ROWS,"CP") * 0.2,5))) = 0;

    The second statement reads the fibre after the first: where the fibre went to 0 (or was 0) the crude protein goes
    too unless the table's NDF is at most 5. Departures from CAPRI: none."""
    NDF, CP = float(NDF or 0.0), float(CP or 0.0)

    def out(F, C):
        return (F > NDF + max(NDF * 0.2, 5) or F < NDF - max(NDF * 0.2, 5)
                or C > CP + max(CP * 0.2, 5) or C < CP - max(CP * 0.2, 5))
    F, C = float(FIDI or 0.0), float(CRPR or 0.0)
    if out(F, C):
        F = 0.0
    if out(F, C):
        C = 0.0
    return F, C


def _within(FIDI, CRPR, FAT, ASH, NDICP):
    """The condition of l. 87-89 and 92-94 besides the item's own: the shares add to at most 100 and the fibre is above
    the neutral detergent insoluble crude protein."""
    return (CRPR + FIDI + FAT + ASH + NDICP <= 100) and FIDI > NDICP


def p_digestPar_CP(CP, CRPR, FIDI, FAT, ASH, NDICP):
    r"""p_digestPar(RU, CATACT, ROWS, CP): CAPRI's crude protein per dry matter in place of the table's where it is
    kept (l. 86-89).

    CAPRI's GAMS (envind/digestibility.gms l. 86-89):

        p_digestPar(RU,CATACT,ROWS,"CP")$
                                                              (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) and (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) + p_nutPerDryMt(RU,CATACT,"FIDI",ROWS)
                                                              + p_digestPar(RU,CATACT,ROWS,"FAT") + p_digestPar(RU,CATACT,ROWS,"ASH") + p_digestPar(RU,CATACT,ROWS,"NDICP") <= 100) and
                                (p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) > p_digestPar(RU,CATACT,ROWS,"NDICP"))) = p_nutPerDryMt(RU,CATACT,"CRPR",ROWS);

    CRPR, FIDI: p_nutPerDryMt after l. 73-83. Departures from CAPRI: none."""
    CRPR, FIDI = float(CRPR or 0.0), float(FIDI or 0.0)
    if CRPR and _within(FIDI, CRPR, float(FAT or 0.0), float(ASH or 0.0), float(NDICP or 0.0)):
        return CRPR
    return float(CP or 0.0)


def p_digestPar_NDF_data(NDF, CRPR, FIDI, FAT, ASH, NDICP):
    r"""p_digestPar(RU, CATACT, ROWS, NDF): CAPRI's fibre per dry matter in place of the table's NDF where it is kept
    (l. 91-94).

    CAPRI's GAMS (envind/digestibility.gms l. 91-94):

        p_digestPar(RU,CATACT,ROWS,"NDF")$
                                                              (p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) and (p_nutPerDryMt(RU,CATACT,"CRPR",ROWS) + p_nutPerDryMt(RU,CATACT,"FIDI",ROWS)
                                                              + p_digestPar(RU,CATACT,ROWS,"FAT") + p_digestPar(RU,CATACT,ROWS,"ASH") + p_digestPar(RU,CATACT,ROWS,"NDICP") <= 100) and
                                (p_nutPerDryMt(RU,CATACT,"FIDI",ROWS) > p_digestPar(RU,CATACT,ROWS,"NDICP"))) = p_nutPerDryMt(RU,CATACT,"FIDI",ROWS);

    CRPR, FIDI: p_nutPerDryMt after l. 73-83. Departures from CAPRI: none."""
    CRPR, FIDI = float(CRPR or 0.0), float(FIDI or 0.0)
    if FIDI and _within(FIDI, CRPR, float(FAT or 0.0), float(ASH or 0.0), float(NDICP or 0.0)):
        return FIDI
    return float(NDF or 0.0)


def p_digestPar_NDF_min(NDF, NDICP, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, NDF) at least NDICP + 0.1 for the products with an equation class (l. 99-100).

    CAPRI's GAMS (envind/digestibility.gms l. 97-100):

        * guarantee that TDNFC and TDNDF don't become negative

        p_digestPar(RU,CATACT,ROWS,"NDF") $ p_digestPar(RU,CATACT,ROWS,"CAT") =
                                                              MAX(p_digestPar(RU,CATACT,ROWS,"NDF"),p_digestPar(RU,CATACT,ROWS,"NDICP")+0.1);

    Departures from CAPRI: none."""
    NDF = float(NDF or 0.0)
    return max(NDF, float(NDICP or 0.0) + 0.1) if CAT else NDF


def p_digestPar_TDNFC(NDF, NDICP, CP, EE, ASH, PAF, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, TDNFC): the truly digestible non-fibre carbohydrate (NRC 2001; l. 104-106); 0
    without an equation class (the table has no TDNFC).

    CAPRI's GAMS (envind/digestibility.gms l. 102-106):

        * for calculation see NRC 2001

        p_digestPar(RU,CATACT,ROWS,"TDNFC") $ p_digestPar(RU,CATACT,ROWS,"CAT") =
                                                              0.98 * (100 - p_digestPar(RU,CATACT,ROWS,"NDF") + p_digestPar(RU,CATACT,ROWS,"NDICP") - p_digestPar(RU,CATACT,ROWS,"CP")
                                                              - p_digestPar(RU,CATACT,ROWS,"EE") - p_digestPar(RU,CATACT,ROWS,"ASH")) * p_digestPar(RU,CATACT,ROWS,"PAF");

    Departures from CAPRI: none."""
    if not CAT:
        return 0.0
    f = lambda x: float(x or 0.0)                                            # noqa: E731
    return 0.98 * (100 - f(NDF) + f(NDICP) - f(CP) - f(EE) - f(ASH)) * f(PAF)


def p_digestPar_TDCP(CP, ADICP, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, TDCP): the truly digestible crude protein by equation class: concentrates (1),
    forages (2), animal products (3) (l. 108-115); 0 without CP or class.

    CAPRI's GAMS (envind/digestibility.gms l. 108-115):

        p_digestPar(RU,CATACT,ROWS,"TDCP")$((p_digestPar(RU,CATACT,ROWS,"CAT")=1) and p_digestPar(RU,CATACT,ROWS,"CP"))  =
                               (1 - 0.4 * p_digestPar(RU,CATACT,ROWS,"ADICP")/p_digestPar(RU,CATACT,ROWS,"CP")) * p_digestPar(RU,CATACT,ROWS,"CP");

        p_digestPar(RU,CATACT,ROWS,"TDCP")$((p_digestPar(RU,CATACT,ROWS,"CAT")=2) and p_digestPar(RU,CATACT,ROWS,"CP"))  =
                               p_digestPar(RU,CATACT,ROWS,"CP") * exp(-1.2 * (p_digestPar(RU,CATACT,ROWS,"ADICP")/p_digestPar(RU,CATACT,ROWS,"CP")));

        p_digestPar(RU,CATACT,ROWS,"TDCP")$((p_digestPar(RU,CATACT,ROWS,"CAT")=3) and p_digestPar(RU,CATACT,ROWS,"CP")) =
                                                              p_digestPar(RU,CATACT,ROWS,"CP");

    Departures from CAPRI: none."""
    import math
    CP, ADICP, CAT = float(CP or 0.0), float(ADICP or 0.0), float(CAT or 0.0)
    if not CP:
        return 0.0
    if CAT == 1:
        return (1 - 0.4 * ADICP / CP) * CP
    if CAT == 2:
        return CP * math.exp(-1.2 * (ADICP / CP))
    if CAT == 3:
        return CP
    return 0.0


def p_digestPar_TDFA(FAT):
    r"""p_digestPar(RU, CATACT, ROWS, TDFA): the truly digestible fat, the fat (l. 117).

    CAPRI's GAMS (envind/digestibility.gms l. 117):

        p_digestPar(RU,CATACT,ROWS,"TDFA") = p_digestPar(RU,CATACT,ROWS,"FAT");

    Departures from CAPRI: none."""
    return float(FAT or 0.0)


def p_digestPar_TDNDF(NDF, NDICP, LI, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, TDNDF): the truly digestible neutral detergent fibre (l. 119-121); 0 without NDF
    or class.

    CAPRI's GAMS (envind/digestibility.gms l. 119-121):

        p_digestPar(RU,CATACT,ROWS,"TDNDF") $ (p_digestPar(RU,CATACT,ROWS,"NDF") and p_digestPar(RU,CATACT,ROWS,"CAT")) =
                               0.75 * (p_digestPar(RU,CATACT,ROWS,"NDF") - p_digestPar(RU,CATACT,ROWS,"NDICP") - p_digestPar(RU,CATACT,ROWS,"LI"))
                                                        * (1 - (p_digestPar(RU,CATACT,ROWS,"LI")/(p_digestPar(RU,CATACT,ROWS,"NDF") - p_digestPar(RU,CATACT,ROWS,"NDICP")))**0.667);

    With a class, NDF >= NDICP + 0.1 (l. 99-100), so the power's base is not negative. Departures from CAPRI: none."""
    NDF, NDICP, LI = float(NDF or 0.0), float(NDICP or 0.0), float(LI or 0.0)
    if not (NDF and CAT):
        return 0.0
    return 0.75 * (NDF - NDICP - LI) * (1 - (LI / (NDF - NDICP)) ** 0.667)


def p_digestPar_TDN(TDNFC, TDCP, TDFA, TDNDF, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, TDN): the total digestible nutrients at maintenance (l. 123-125); 0 without class.

    CAPRI's GAMS (envind/digestibility.gms l. 123-125):

        p_digestPar(RU,CATACT,ROWS,"TDN") $ p_digestPar(RU,CATACT,ROWS,"CAT")  =
                               p_digestPar(RU,CATACT,ROWS,"TDNFC") + p_digestPar(RU,CATACT,ROWS,"TDCP") + p_digestPar(RU,CATACT,ROWS,"TDFA") * 2.25
                                                        + p_digestPar(RU,CATACT,ROWS,"TDNDF") - 7;

    Departures from CAPRI: none."""
    if not CAT:
        return 0.0
    return float(TDNFC) + float(TDCP) + float(TDFA) * 2.25 + float(TDNDF) - 7


def p_digestPar_DE_maintenance(TDNFC, TDNDF, TDCP, TDFA, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, DE): the digestible energy at maintenance, Mcal per kg dry matter: plant feeds
    (classes 1 and 2) with the fibre's, animal products (class 3) without (l. 127-132); 0 otherwise (the table has no
    DE).

    CAPRI's GAMS (envind/digestibility.gms l. 127-132):

        p_digestPar(RU,CATACT,ROWS,"DE") $ ((p_digestPar(RU,CATACT,ROWS,"CAT") <= 2) and (p_digestPar(RU,CATACT,ROWS,"CAT") > 0))  =
                               (p_digestPar(RU,CATACT,ROWS,"TDNFC") + p_digestPar(RU,CATACT,ROWS,"TDNDF"))/100 * 4.2
                                                        + p_digestPar(RU,CATACT,ROWS,"TDCP")/100 * 5.6 + p_digestPar(RU,CATACT,ROWS,"TDFA")/100 * 9.4 - 0.3;

        p_digestPar(RU,CATACT,ROWS,"DE") $ (p_digestPar(RU,CATACT,ROWS,"CAT") = 3)        = p_digestPar(RU,CATACT,ROWS,"TDNFC")/100 * 4.2
                                                              + p_digestPar(RU,CATACT,ROWS,"TDCP")/100 * 5.6 + p_digestPar(RU,CATACT,ROWS,"TDFA")/100 * 9.4 - 0.3;

    Departures from CAPRI: none."""
    CAT = float(CAT or 0.0)
    if 0 < CAT <= 2:
        return (float(TDNFC) + float(TDNDF)) / 100 * 4.2 + float(TDCP) / 100 * 5.6 + float(TDFA) / 100 * 9.4 - 0.3
    if CAT == 3:
        return float(TDNFC) / 100 * 4.2 + float(TDCP) / 100 * 5.6 + float(TDFA) / 100 * 9.4 - 0.3
    return 0.0


def p_digestPar_GE(CP, FAT, ASH, CAT):
    r"""p_digestPar(RU, CATACT, ROWS, GE): the gross energy, Mcal per kg dry matter (l. 134-136); 0 without class.

    CAPRI's GAMS (envind/digestibility.gms l. 134-136):

        p_digestPar(RU,CATACT,ROWS,"GE") $ p_digestPar(RU,CATACT,ROWS,"CAT") =
                                                              p_digestPar(RU,CATACT,ROWS,"CP")/100 * 5.6 + p_digestPar(RU,CATACT,ROWS,"FAT")/100 * 9.4
                                                              + (100 - p_digestPar(RU,CATACT,ROWS,"CP") - p_digestPar(RU,CATACT,ROWS,"FAT") - p_digestPar(RU,CATACT,ROWS,"ASH"))/100 * 4.2;

    Departures from CAPRI: none."""
    if not CAT:
        return 0.0
    CP, FAT, ASH = float(CP or 0.0), float(FAT or 0.0), float(ASH or 0.0)
    return CP / 100 * 5.6 + FAT / 100 * 9.4 + (100 - CP - FAT - ASH) / 100 * 4.2


#: the vegetable oils of l. 139-143 and their DE and GE (INRA 2002)
VEG_OILS = ("RAPO", "SUNO", "SOYO", "OLIO", "OTHO")


def p_digestPar_DE_GE_oils(row, DE, GE):
    r"""p_digestPar(RU, CATACT, ROWS, DE | GE) of the vegetable oils: INRA 2002's 8.27 and 9.39 (l. 138-143). Returns
    (DE, GE).

    CAPRI's GAMS (envind/digestibility.gms l. 138-143):

        * for vegetable oils use digestibility values from INRA 2002
        p_digestPar(RU,CATACT,ROWS,"DE") $
                                                              (SAMEAS(ROWS,"RAPO") or SAMEAS(ROWS,"SUNO") or SAMEAS(ROWS,"SOYO") or SAMEAS(ROWS,"OLIO") or SAMEAS(ROWS,"OTHO")) = 8.27;

        p_digestPar(RU,CATACT,ROWS,"GE") $
                                                              (SAMEAS(ROWS,"RAPO") or SAMEAS(ROWS,"SUNO") or SAMEAS(ROWS,"SOYO") or SAMEAS(ROWS,"OLIO") or SAMEAS(ROWS,"OTHO")) = 9.39;

    Departures from CAPRI: none."""
    return (8.27, 9.39) if row in VEG_OILS else (float(DE or 0.0), float(GE or 0.0))


def p_actualIntake(ENNE, NEM, technFact):
    r"""p_actualIntake(RU, CATACT): the intake above maintenance, the sum over the technologies of the energy
    requirement over the maintenance's, less 1 (l. 150-153); 0 where the activity has no maintenance requirement.

    CAPRI's GAMS (envind/digestibility.gms l. 146-153):

        * calculate the discount for actual intake above maintainance level

        * determine actual intake level above maintainance

        p_actualIntake(RU,CATACT) $ sum(A,p_animReq(RU,CATACT,A,"NEM" %addtimedim%))  =
                             SUM(A $ (p_technFact(RU,CATACT,"LEVL",A) and p_animReq(RU,CATACT,A,"NEM" %addtimedim%)),
                             p_animReq(RU,CATACT,A,"ENNE" %addtimedim%)
                                                      /p_animReq(RU,CATACT,A,"NEM" %addtimedim%)) - 1;

    ENNE, NEM, technFact: {A: p_animReq(RU, CATACT, A, ENNE | NEM)}, {A: p_technFact(RU, CATACT, "LEVL", A)}. The
    ratios are summed over the technologies, as CAPRI writes it. Departures from CAPRI: none."""
    if not sum(float(v or 0.0) for v in NEM.values()):
        return 0.0
    return sum(float(ENNE.get(t, 0.0) or 0.0) / float(NEM[t]) for t in NEM
               if float(technFact.get(t, 0.0) or 0.0) and float(NEM[t] or 0.0)) - 1


def p_digestPar_DIS(TDN, CAT, actualIntake):
    r"""p_digestPar(RU, CATACT, ROWS, DIS): the discount of the digestible energy for the intake above maintenance, at
    most down to a TDN of 60, and 1 for the products with a TDN of 60 or less (l. 157-165, in order); 0 where the
    activity has no intake above maintenance.

    CAPRI's GAMS (envind/digestibility.gms l. 155-165):

        * calculate discount factor

        p_digestPar(RU,CATACT,ROWS,"DIS") $ ((p_digestPar(RU,CATACT,ROWS,"TDN") > 60) and p_actualIntake(RU,CATACT)) =
                              (p_digestPar(RU,CATACT,ROWS,"TDN") - (0.18 * p_digestPar(RU,CATACT,ROWS,"TDN") - 10.3) * p_actualIntake(RU,CATACT))
                                                       / p_digestPar(RU,CATACT,ROWS,"TDN");

        p_digestPar(RU,CATACT,ROWS,"DIS") $ ((p_digestPar(RU,CATACT,ROWS,"TDN") <= 60) and p_digestPar(RU,CATACT,ROWS,"CAT") and p_actualIntake(RU,CATACT)) = 1;

        p_digestPar(RU,CATACT,ROWS,"DIS") $ ((p_digestPar(RU,CATACT,ROWS,"TDN") * p_digestPar(RU,CATACT,ROWS,"DIS") < 60) and p_digestPar(RU,CATACT,ROWS,"DIS") and
                             (p_digestPar(RU,CATACT,ROWS,"TDN") >= 60)) =
                              60 / p_digestPar(RU,CATACT,ROWS,"TDN");

    Departures from CAPRI: none."""
    TDN, AI = float(TDN or 0.0), float(actualIntake or 0.0)
    DIS = 0.0
    if TDN > 60 and AI:
        DIS = (TDN - (0.18 * TDN - 10.3) * AI) / TDN
    if TDN <= 60 and CAT and AI:
        DIS = 1.0
    if TDN * DIS < 60 and DIS and TDN >= 60:
        DIS = 60 / TDN
    return DIS


def p_digestPar_DE_intake(DE, DIS):
    r"""p_digestPar(RU, CATACT, ROWS, DE): the digestible energy at the actual intake (l. 169-170).

    CAPRI's GAMS (envind/digestibility.gms l. 167-170):

        * calculate digestible energy at actual intake

        p_digestPar(RU,CATACT,ROWS,"DE") $ (p_digestPar(RU,CATACT,ROWS,"DE") and p_digestPar(RU,CATACT,ROWS,"DIS")) =
                              p_digestPar(RU,CATACT,ROWS,"DE") * p_digestPar(RU,CATACT,ROWS,"DIS");

    Departures from CAPRI: none."""
    DE, DIS = float(DE or 0.0), float(DIS or 0.0)
    return DE * DIS if (DE and DIS) else DE


def EMISCALC_DE_ASH_GE(ration, DM, DE, GE, ASH):
    r"""EMISCALC(RU, CATACT, "T", DE | ASH | GE, "Y"): the ration's digestibility in percent (at least 50), ash and
    gross energy, the feed bulks' values weighted by the ration's dry matter (l. 241-253). Returns (DE, ASH, GE), each 0
    where the ration has no dry matter.

    CAPRI's GAMS (envind/digestibility.gms l. 241-253):

        EMISCALC(RU,CATACT,"T","DE",%1) $ sum(FEED,DATA(RU,CATACT,FEED,%1) * p_DryMatterContent(RU,FEED) ) =
                               sum(FEED $ p_digestPar(RU,CATACT,FEED,"GE"),p_digestPar(RU,CATACT,FEED,"DE")/p_digestPar(RU,CATACT,FEED,"GE") *
                               DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) / sum(FEED,DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) * 100;
        * avoid very low digestibilities which may even create negative NEG in gases.gms
        EMISCALC(RU,CATACT,"T","DE",%1) $ EMISCALC(RU,CATACT,"T","DE",%1) = max(50,EMISCALC(RU,CATACT,"T","DE",%1));


        EMISCALC(RU,CATACT,"T","ASH",%1) $ sum(FEED,DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) =
                               sum(FEED $ p_digestPar(RU,CATACT,FEED,"ASH"),p_digestPar(RU,CATACT,FEED,"ASH") *
                               DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) / sum(FEED,DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED));
        EMISCALC(RU,CATACT,"T","GE",%1) $ sum(FEED,DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) =
                               sum(FEED $ p_digestPar(RU,CATACT,FEED,"GE"),p_digestPar(RU,CATACT,FEED,"GE") *
                               DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED)) / sum(FEED,DATA(RU,CATACT,FEED,%1) *  p_DryMatterContent(RU,FEED));

    ration: {FEED: DATA(RU, CATACT, FEED, "Y")}, kg per head; DM: {FEED: p_DryMatterContent(RU, FEED)}; DE, GE, ASH:
    {FEED: p_digestPar(RU, CATACT, FEED, item)} (the bulks', p_digestPar_FEED). Departures from CAPRI: none."""
    w = {f: float(q or 0.0) * float(DM.get(f, 0.0) or 0.0) for f, q in ration.items()}
    tot = sum(w.values())
    if not tot:
        return 0.0, 0.0, 0.0
    de = sum(float(DE.get(f, 0.0) or 0.0) / float(GE[f]) * x for f, x in w.items() if float(GE.get(f, 0.0) or 0.0)) \
        / tot * 100
    if de:
        de = max(50.0, de)
    ash = sum(float(ASH[f]) * x for f, x in w.items() if float(ASH.get(f, 0.0) or 0.0)) / tot
    ge = sum(float(GE[f]) * x for f, x in w.items() if float(GE.get(f, 0.0) or 0.0)) / tot
    return de, ash, ge


def p_emisFeed_GE(GE_FEED):
    r"""p_emisFeed(RU, CATACT, "T", FEED, "GE"): the feed bulk's gross energy, Mcal per kg dry matter, for the methane
    of enteric fermentation from the feeds (%CH4ENTfromFEED% on: capmod/set_global_variables.gms l. 226, capreg/
    set_global_variables.gms l. 143; gases.gms l. 367-376, capri_mod/environmental/equations/gases.py p_emisFeed_CH4ENT)
    (l. 255-258).

    CAPRI's GAMS (envind/digestibility.gms l. 255-258):

        $iftheni.emisfeed1 %CH4ENTfromFEED%==on
        *  gross energy content of bulk FEED is used in calculation of CH4ENT of cattle activities:
           p_emisFeed(RU,CATACT,"T",FEED,"GE") = p_digestPar(RU,CATACT,FEED,"GE") ;
        $endif.emisfeed1

    GE_FEED: p_digestPar(RU, CATACT, FEED, "GE") (p_digestPar_FEED). Departures from CAPRI: none."""
    return float(GE_FEED or 0.0)

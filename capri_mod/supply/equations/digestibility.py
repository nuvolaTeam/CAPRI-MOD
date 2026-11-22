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

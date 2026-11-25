"""The port of CAPRI's year data (capri_mod/projection/equations/load_base_data_and_trends.py): its statements on
small cases built from CAPRI's own sets, each against what the GAMS statement it quotes gives."""
from __future__ import annotations

import dataclasses

import pytest

from capri_mod.projection.equations import load_base_data_and_trends as ly


@pytest.fixture(scope="module")
def S():
    return ly.YearSets.from_codes()


def test_the_year_data_takes_the_trends_where_captrd_projects_and_the_base_year_elsewhere(S):
    """DATA_Y_ (l. 598-599): Y = TRD for a FROM_CAPTRD position, BAS for the others, and a position with neither is
    deleted from Y."""
    D = ly.Data()
    r = "DK000000"
    D.set(r, "SWHE", "LEVL", "BAS", 500.)
    D.set(r, "SWHE", "LEVL", "TRD", 450.)
    D.set(r, "SWHE", "NITF", "BAS", 200.)
    D.set(r, "SWHE", "NITF", "TRD", 180.)
    D.set(r, "BARL", "LEVL", "Y", 7.)              # an old Y without BAS or TRD
    ly.DATA_Y_(D, S, {("SWHE", "LEVL")})
    assert D.get(r, "SWHE", "LEVL", "Y") == 450.
    assert D.get(r, "SWHE", "NITF", "Y") == 200.
    assert D.get(r, "BARL", "LEVL", "Y") == 0.


def test_from_captrd_holds_the_trends_positions_and_every_activity_level_but_the_animals_mins(S):
    """FROM_CAPTRD_ (l. 537-563): the positions of the member states' trends, every activity's LEVL, the feeds' GROF,
    the FEDM row; not an animal's MINS even where the trends hold it."""
    D2 = ly.Data()
    D2.set("DK000000", "SWHE", "NITF", "Y", 180.)
    D2.set("DK000000", "DCOW", "MINS", "Y", 1.)
    D2.set("DK000000", "SWHE", "PHOF", "Y", 60.)
    fc = ly.FROM_CAPTRD_(D2, S)
    assert ("SWHE", "NITF") in fc and ("SWHE", "PHOF") in fc
    assert ("DCOW", "MINS") not in fc
    assert ("BARL", "LEVL") in fc and ("GROF", "FCER") in fc
    assert ("FEDM", "SWHE") in fc


def test_a_tiny_level_is_deleted_and_the_member_state_reaggregated(S):
    """delete_tiny_activity_level (util/delete_tiny_activity_level.gms l. 7-28): a regional level below the tolerance
    deleted with its coefficients, the region's gross production of its outputs re-computed, the member state's level
    and coefficient re-aggregated."""
    ms = "DE000000"
    rus = sorted(ru for (m, ru) in S.MAP_RR if m == ms and ru in S.RU)[:2]
    a, b = rus
    S2 = dataclasses.replace(S, RU=ly.OSet(rus), MS=ly.OSet([ms]), RS=ly.OSet(rus + [ms]))
    D = ly.Data()
    for r, lev, y in ((a, 0.0005, 6000.), (b, 100., 8000.)):
        D.set(r, "SWHE", "LEVL", "Y", lev)
        D.set(r, "SWHE", "SWHE", "Y", y)
        D.set(r, "GROF", "SWHE", "Y", lev * y / 1000.)
    D.set(ms, "SWHE", "LEVL", "Y", 100.0005)
    D.set(ms, "SWHE", "SWHE", "Y", 7999.99)
    flags = ly.delete_tiny_activity_level(D, S2, "Y", 1e-3)
    assert (a, "SWHE") in flags["levl"]
    assert D.get(a, "SWHE", "LEVL", "Y") == 0. and D.get(a, "SWHE", "SWHE", "Y") == 0.
    assert D.get(a, "GROF", "SWHE", "Y") == 0.
    assert D.get(ms, "SWHE", "LEVL", "Y") == 100.
    assert D.get(ms, "SWHE", "SWHE", "Y") == pytest.approx(8000.)


def test_the_regions_losses_take_their_member_states_share(S):
    """DATA_TRD_LOSF_ratio (l. 587-590): LOSF = GROF x the member state's LOSF / GROF."""
    ms = "DE000000"
    ru = sorted(ru for (m, ru) in S.MAP_RR if m == ms and ru in S.RU and ru != ms)[0]
    S2 = dataclasses.replace(S, RU=ly.OSet([ru]), MS=ly.OSet([ms]), RS=ly.OSet([ru, ms]))
    D = ly.Data()
    D.set(ms, "GROF", "MAIF", "TRD", 1000.)
    D.set(ms, "LOSF", "MAIF", "TRD", 50.)
    D.set(ru, "GROF", "MAIF", "TRD", 200.)
    D.set(ru, "LOSF", "MAIF", "TRD", 3.)
    ly.DATA_TRD_LOSF_ratio(D, S2)
    assert D.get(ru, "LOSF", "MAIF", "TRD") == pytest.approx(10.)


def test_the_year_keeps_capris_order_of_its_sets(S):
    """The sets keep CAPRI's order (the loops and sums run in GAMS's order) and a set's membership test."""
    assert S.SCEN == ("Y", "BAS") and "BAS" in S.SCEN and "TRD" not in S.SCEN
    assert list(S.Seco_BioF) == ["BIOE", "BIOD"]
    assert ("RAPE", "RAPC") in S.SED_TO_CAK


def test_the_raw_milks_fat_and_protein_match_the_dairy_products(S):
    """DATA_MAPR_MLK_small (l. 772-776) and DATA_FATSPROT_MILK (l. 778-790): a product with no base-year market
    production loses its market production at "Y" too; the raw milk's fat content is the fat in the products made over
    the raw milk processed, and its total is deleted at "BAS"."""
    ms = "DK000000"
    S2 = dataclasses.replace(S, MS=ly.OSet([ms]), RS=ly.OSet([ms]))
    D = ly.Data()
    D.set(ms, "MAPR", "BUTT", "BAS", 100.)
    D.set(ms, "MAPR", "BUTT", "Y", 110.)
    D.set(ms, "MAPR", "CHES", "Y", 50.)                 # no base-year market production: deleted at Y
    D.set(ms, "FATS", "BUTT", "Y", 0.8)
    D.set(ms, "FATS", "BUTT", "BAS", 0.8)
    D.set(ms, "PRCM", "MILK", "Y", 4000.)
    D.set(ms, "PRCM", "MILK", "BAS", 3600.)
    ly.DATA_MAPR_MLK_small(D, S2)
    assert D.get(ms, "MAPR", "CHES", "Y") == 0. and D.get(ms, "MAPR", "BUTT", "Y") == 110.
    ly.DATA_FATSPROT_MILK(D, S2)
    assert D.get(ms, "FATS", "MILK", "Y") == pytest.approx(110. * 0.8 / 4000.)
    assert D.get(ms, "FATS", "MILK", "TRD") == D.get(ms, "FATS", "MILK", "Y")
    assert D.get(ms, "FATS", "MILK", "BAS") == pytest.approx(100. * 0.8 / 3600.)
    assert D.get(ms, "FATS", "LEVL", "BAS") == 0. and D.get(ms, "FATS", "LEVL", "Y") == pytest.approx(88.)


def test_the_crop_residues_and_the_second_generations_sources(S):
    """resids.gms l. 45-46, 69-99: ARES per ha is the main yield times p_residYield (zero for the activities without
    one), its gross production over the levels; the new energy crops cover half the second generation's biomass, at most
    90% of their area, the residues the rest."""
    ms = "DK000000"
    S2 = dataclasses.replace(S, MS=ly.OSet([ms]), RS=ly.OSet([ms]))
    P = ly.ResidsParams(p_residYield={"BARL": 1.45}, p_newEnergyCropYield={"REST": 10.},
                        p_secgConv={"BIOE": 0.15, "BIOD": 0.7})
    D = ly.Data()
    D.set(ms, "BARL", "BARL", "Y", 6000.)
    D.set(ms, "BARL", "LEVL", "Y", 600.)
    D.set(ms, "POTA", "ARES", "Y", 3.)                  # no factor: deleted
    ly.DATA_ARES(D, S2, P)
    assert D.get(ms, "BARL", "ARES", "Y") == pytest.approx(8700.)
    assert D.get(ms, "POTA", "ARES", "Y") == 0.
    assert D.get(ms, "GROF", "ARES", "Y") == pytest.approx(8700. * 600. / 1000.)
    D.set(ms, "SECG", "BIOE", "Y", 3.)
    D.set(ms, "NECR", "LEVL", "Y", 100.)
    ly.DATA_NECR_LEVL_1_2(D, S2, P)
    assert D.get(ms, "NECR", "LEVL_1", "Y") == pytest.approx(0.5 * 3. / 0.15 / 10.)
    assert D.get(ms, "NECR", "LEVL_2", "Y") == pytest.approx(100. - 1.)
    assert D.get(ms, "NECR", "LEVL_1", "CAL") == D.get(ms, "NECR", "LEVL_1", "Y")
    ly.DATA_SECG_ARES_bio(D, S2, P)
    assert D.get(ms, "SECG", "ARES", "Y") == pytest.approx(20. - 10.)
    assert D.get(ms, "bioNECR", "BIOE", "Y") == pytest.approx(10.)
    assert D.get(ms, "bioARES", "BIOE", "Y") == pytest.approx(3. - 10.)

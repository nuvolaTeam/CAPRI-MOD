"""The year's data as create_sim_ini_gdx.gms l. 311-369 leaves them (capri_mod/projection/equations/
create_sim_ini_gdx_data.py): its statements on small cases built from CAPRI's own sets, each against what the GAMS
statement it quotes gives."""
from __future__ import annotations

import dataclasses

import pytest

from capri_mod.projection.equations import create_sim_ini_gdx_data as csd
from capri_mod.projection.equations import load_base_data_and_trends as ly


@pytest.fixture(scope="module")
def S():
    return ly.YearSets.from_codes()


@pytest.fixture(scope="module")
def L():
    return csd.DelSets.from_codes()


def _de(S):
    ms = "DE000000"
    ru = sorted(ru for (m, ru) in S.MAP_RR if m == ms and ru in S.RU and ru != ms)[0]
    return ms, ru, dataclasses.replace(S, RU=ly.OSet([ru]), MS=ly.OSet([ms]), RS=ly.OSet([ms, ru]))


def test_energy_maize_moves_to_the_exogenous_demand(S):
    """l. 320-323: p_exoDemand(RS, "DEMD", "MAIF") takes INDM of MAIF, which the regional units lose (the member state
    keeps it)."""
    ms, ru, S2 = _de(S)
    D = ly.Data()
    D.set(ms, "INDM", "MAIF", "Y", 900.)
    D.set(ru, "INDM", "MAIF", "Y", 40.)
    exo = csd.p_exoDemand_MAIF(D, S2)
    assert exo == {(ms, "DEMD", "MAIF"): 900., (ru, "DEMD", "MAIF"): 40.}
    assert D.get(ru, "INDM", "MAIF", "Y") == 0. and D.get(ms, "INDM", "MAIF", "Y") == 900.


def test_the_member_states_market_balance_goes_but_feed_use(S, L):
    """l. 331-333: the member states' market balance positions at "Y" are deleted, but FEDM and the products without a
    market (NONEND); the regions' stay."""
    ms, ru, S2 = _de(S)
    D = ly.Data()
    D.set(ms, "HCOM", "BARL", "Y", 50.)
    D.set(ms, "FEDM", "BARL", "Y", 3000.)
    D.set(ms, "HCOM", "NURS", "Y", 7.)
    D.set(ru, "HCOM", "BARL", "Y", 5.)
    csd.DATA_delete_market_balance(D, S2, L)
    assert D.get(ms, "HCOM", "BARL", "Y") == 0.
    assert D.get(ms, "FEDM", "BARL", "Y") == 3000. and D.get(ms, "HCOM", "NURS", "Y") == 7.
    assert D.get(ru, "HCOM", "BARL", "Y") == 5.


def test_the_regions_lose_their_contents_but_crude_protein(S, L):
    """l. 358-369: in the regions (not the member state) the contents but CRPR go at "Y" and "BAS"; the member state
    loses its feeds' inequality contents at "BAS" only."""
    ms, ru, S2 = _de(S)
    D = ly.Data()
    for r in (ms, ru):
        for c in ("CRPR", "ENNE"):
            D.set(r, c, "FCER", "Y", 1.)
            D.set(r, c, "FCER", "BAS", 1.)
        D.set(r, "DRMN", "FCER", "BAS", 0.9)
    csd.DATA_delete_regions_unit_values_and_contents(D, S2, L)
    assert D.get(ru, "CRPR", "FCER", "Y") == 1. and D.get(ru, "ENNE", "FCER", "Y") == 0.
    assert D.get(ru, "ENNE", "FCER", "BAS") == 0.
    assert D.get(ms, "ENNE", "FCER", "Y") == 1. and D.get(ms, "DRMN", "FCER", "BAS") == 0.

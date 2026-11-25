"""CAPRI's Green Deal targets by simulation year of its production series (register DEP-20): the table built from the
batch's section "f2f" (tools/build/build_greendeal_batch_targets.py, greendeal_targets_by_year.csv) and the scenarios
made from it (policy/greendeal.py greendeal_targets, greendeal_series_scenario)."""
import csv
import dataclasses
import sys
from pathlib import Path

import pytest

from capri_mod.policy import greendeal as G

ROOT = Path(__file__).resolve().parents[2]


def _rows():
    with open(G.TARGETS_BY_YEAR, newline="") as f:
        return list(csv.DictReader(f))


def test_every_year_of_the_series_is_a_scenario_of_capris_group():
    """Each row is a scenario greendeal_scenario accepts (the GUI's options, dietShift and othPol 00), named as CAPRI
    names it (greendeal_scenarios.gms l. 192) from the row's values as the batch writes them; manure trade on."""
    rows = _rows()
    assert [int(r["year"]) for r in rows] == [2025, 2030, 2035, 2040, 2050]
    for r in rows:
        sc = G.greendeal_series_scenario(int(r["year"]))
        want = "greendeal_lnds{lndscpTarg}_org{orgTarg}_pest{pestRedu}_mine{mineRedu}_surp{surpRedu}_diet{dietShift}" \
               "_oth{othPol}".format(**r)
        assert sc.name == want and sc.manure_trade is True and sc.greendeal_group
        assert sc.set_aside_requirement == int(r["lndscpTarg"]) / 100.0 and sc.surplus_cut == int(r["surpRedu"]) / 100.0
    with pytest.raises(ValueError):
        G.greendeal_targets(2045)


def test_the_2030_step_is_the_tables_2030_row():
    """greendeal_2030_scenario is the 2030 row with manure trade on (the constant it replaced: lnds8 org18 pest20
    mine13crp surp30)."""
    t = G.greendeal_targets(2030)
    assert t == dict(lndscpTarg=8, orgTarg=18, pestRedu=20, mineRedu="13crp", surpRedu=30, dietShift=0, othPol=0)
    assert dataclasses.asdict(G.greendeal_2030_scenario()) == dataclasses.asdict(
        G.greendeal_scenario(**t, manure_trade=True))


def test_the_table_follows_from_capris_batch():
    """The builder reproduces the table from CAPRI's batch and GUI definition (skipped without capri_sources/gui)."""
    sys.path.insert(0, str(ROOT / "tools" / "build"))
    import build_greendeal_batch_targets as B
    if not (B.BATCH.exists() and B.GUI_DEF.exists() and B.GMS.exists()):
        pytest.skip("CAPRI's GUI batch, GUI definition or greendeal_scenarios.gms not in capri_sources")
    B.main(check=True)


def test_the_batch_parser_on_a_small_section():
    """The parser: the section's values, a year's block overriding them, comments skipped, the scenario name's
    settings only; CAPRI's name template with %gdversion% empty."""
    sys.path.insert(0, str(ROOT / "tools" / "build"))
    import build_greendeal_batch_targets as B
    name, keys = B.scenNameFromGroup("$setglobal gdversion\n$setglobal scenNameFromGroup  greendeal%gdversion%_lnds"
                                     "%lndscpTarg%_org%orgTarg%\n")
    assert keys == ["lndscpTarg", "orgTarg"] and name({"lndscpTarg": "8", "orgTarg": "18"}) == "greendeal_lnds8_org18"
    assert name({"lndscpTarg": "00", "orgTarg": "00"}) == "greendeal_reference"
    lines = ["IF %x% = ON", "IF %f2f% = ON", "  Landscape elements target = 10", "*  Landscape elements target = 00",
             "  Organic agriculture target = 25", "  Number of iterations = 30", " FOR curYear = 2040",
             "    IF %curYear%=2030", "      Landscape elements target = 8",
             "      Reference scenario for carbon accounting = res_2_%bas%25greendeal_xdefaultA", "    ENDIF",
             "  ENDFOR", "ENDIF", "ENDIF"]
    sec = B.batch_section(lines, "f2f")
    titles = {"Landscape elements target": "lndscpTarg", "Organic agriculture target": "orgTarg"}
    base, years, refs = B.section_settings(sec, titles, keys)
    assert base == {"lndscpTarg": "10", "orgTarg": "25"} and years == {2030: {"lndscpTarg": "8"}}
    assert refs == {2030: "res_2_%bas%25greendeal_xdefaultA"}

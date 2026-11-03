"""Scenarios as data (refactor stage 5): each scenario folder gives the scenario its Python factory gives, field by
field; the definitions are checked before a run (capri_mod/scenarios/definition.py)."""
from __future__ import annotations

import dataclasses

import pytest
from pydantic import ValidationError

from capri_mod.scenarios import definition as D


def _factories():
    from capri_mod.policy.greendeal import farm_to_fork_scenario, greendeal_2030_scenario
    from capri_mod.scenarios.scenarios import carbon_tax_scenario, set_aside_10_scenario
    return {
        "farm_to_fork_jrc121368": farm_to_fork_scenario,
        "greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00": greendeal_2030_scenario,
        "CARBON_TAX_50": lambda: carbon_tax_scenario(50.0),
        "SET_ASIDE_10PCT": set_aside_10_scenario,
    }


@pytest.mark.parametrize("name", sorted(_factories()))
def test_a_scenario_folder_gives_its_factorys_scenario(name):
    got = D.to_policy_scenario(D.load(name))
    want = _factories()[name]()
    assert dataclasses.asdict(got) == dataclasses.asdict(want)


def test_every_scenario_folder_is_read_and_its_reference_exists():
    kinds = D.available()
    assert {"ref_star3", "ref_jrc121368"} <= {k for k, v in kinds.items() if v == "reference"}
    for name, kind in kinds.items():
        d = D.load(name)
        assert D.trajectory_of(d) in ("capri_ref_2030", "captrd_2030", "null")
        if kind == "scenario":
            assert D.load(d.reference).kind == "reference"


def test_a_definition_is_checked_before_a_run(tmp_path):
    """Unknown keys, a scenario without reference, a reference with shocks and a folder whose name differs from
    its definition's stop before a run."""
    with pytest.raises(ValidationError):
        D.ScenarioDef(name="x", kind="scenario", reference="ref_star3", no_such_key=1)
    with pytest.raises(ValidationError):
        D.ScenarioDef(name="x", kind="scenario")
    with pytest.raises(ValidationError):
        D.ScenarioDef(name="x", kind="reference", trajectory="null", shocks={"carbon_tax": 10.0})
    with pytest.raises(ValidationError):
        D.ScenarioDef(name="x", kind="scenario", reference="r", shocks={"carbon_tax": -1.0})
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "settings.toml").write_text('[scenario]\nname = "b"\nkind = "reference"\ntrajectory = "null"\n')
    with pytest.raises(ValueError, match="not its folder"):
        D.load("a", root=tmp_path)


def test_a_scenario_takes_its_references_settings_unless_it_gives_its_own(tmp_path):
    (tmp_path / "r").mkdir()
    (tmp_path / "r" / "settings.toml").write_text(
        '[scenario]\nname = "r"\nkind = "reference"\ntrajectory = "null"\nmanure_trade = false\n'
        '[scenario.endotech]\nghgTechMYld = 0.2\n')
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "settings.toml").write_text(
        '[scenario]\nname = "s"\nkind = "scenario"\nreference = "r"\n[scenario.endotech]\nghgTechFEff = 0.3\n')
    d = D.load("s", root=tmp_path)
    assert d.manure_trade is False and d.endotech.as_dict() == {"ghgTechMYld": 0.2, "ghgTechFEff": 0.3}
    assert D.trajectory_of(d, root=tmp_path) == "null"


def test_a_user_scenario_is_created_checked_and_built(tmp_path):
    """python -m capri_mod.scenarios new / check: a scenario in the user's own folder, on a reference of the
    repository's, with a table; a wrong Green Deal value and a code the model does not have stop the check."""
    from capri_mod.scenarios.__main__ import main
    from capri_mod import settings as S
    d = str(tmp_path)
    old = S.current()
    assert main(["new", "my_tax", "--reference", "ref_star3", "--dir", d]) == 0
    assert S.current() is old, "--dir must not outlive the command"
    f = tmp_path / "my_tax" / "settings.toml"
    f.write_text(f.read_text().replace("# carbon_tax = 0.0 ", "carbon_tax = 80.0 "))
    (tmp_path / "my_tax" / "tariff_changes.csv").write_text("region,commodity,change_pct\nUSA,BARL,-10\n")
    try:
        S.activate(S.load([], overrides={"run.scenarios_dir": d}))
        assert main(["check", "my_tax", "--dir", d]) == 0
        sc = D.to_policy_scenario(D.load("my_tax"))
        assert sc.carbon_tax == 80.0 and sc.tariff_changes == {"USA": {"BARL": -10.0}} and sc.manure_trade is None
        (tmp_path / "my_tax" / "tariff_changes.csv").write_text("region,commodity,change_pct\nUSA,NOPE,-10\n")
        with pytest.raises(ValueError, match="NOPE"):
            D.to_policy_scenario(D.load("my_tax"))
        assert main(["new", "my_gd", "--reference", "ref_star3", "--group", "greendeal_group", "--dir", d]) == 0
        g = tmp_path / "my_gd" / "settings.toml"
        g.write_text(g.read_text().replace("orgTarg = 0 ", "orgTarg = 12 "))
        with pytest.raises(ValueError, match="orgTarg=12"):
            D.to_policy_scenario(D.load("my_gd"))
        assert main(["check", "my_gd", "--dir", d]) == 1
    finally:
        S.activate(old)

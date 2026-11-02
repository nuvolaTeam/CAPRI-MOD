"""Scenarios as data (refactor stage 5; docs/design/STAGE5_INVENTORY.md, the project lead's decisions of
3 November 2026).

Each reference and each scenario is a folder capri_data/scenarios/<name>/ with a settings.toml (and, where a scenario
has them, its datasets as CSV files). Its [scenario] table is read into a typed definition (pydantic, checked before a
run): a reference names the trajectory it projects along; a scenario names its reference and gives CAPRI's switches of
its scenario group ([greendeal]) or its shocks ([shocks]). The definition is turned into the model's PolicyScenario by
the same functions that build it from Python (capri_mod/policy/greendeal.py), so a scenario read from its folder is
the scenario the Python factory gives (capri_mod/tests/test_scenario_folders.py).

As CAPRI's scenario files include their reference (pol_input/greendeal/greendeal_scenarios.gms l. 58-60), the settings
that hold for a scenario and its baseline (manure trade, biofuel markets, the endogenous technologies) come from the
reference unless the scenario gives its own; the run's own settings win over both (capri_mod/settings).

The trajectory folders (capri_ref_2030, captrd_2030, null; capri_mod/projection/scenario_io.py) have no [scenario]
table and are not read here.
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2] / "capri_data" / "scenarios"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Endotech(_Strict):
    """CAPRI's endogenous-technology settings (capri_mod/policy/endotech.py STAR3_DEFAULTS); absent keys take the
    run's settings ([endotech])."""
    ghgTechMYld: Optional[float] = None
    ghgTechFEff: Optional[float] = None
    ghgTechLowNFeed: Optional[float] = None
    ghgTechLineNitr: Optional[float] = None
    fixGenetToIni: Optional[float] = None

    def as_dict(self) -> Dict[str, float]:
        return {k: float(v) for k, v in self.model_dump().items() if v is not None}


class GreenDeal(_Strict):
    """CAPRI's Green Deal scenario group switches (greendeal_scenarios.gms; the GUI's values) and the model's rules;
    the allowed values are checked by greendeal.greendeal_scenario, the one place that holds them."""
    lndscpTarg: int = 0
    orgTarg: int = 0
    pestRedu: int = 0
    mineRedu: str = "00"
    surpRedu: int = 0
    dietShift: int = 0
    othPol: int = 0
    surplus_rule: Literal["star3", "jrc121368"] = "star3"
    pesticide_rule: Literal["star3", "jrc121368"] = "star3"


class Shocks(_Strict):
    """Policy shocks of a scenario outside the Green Deal group."""
    carbon_tax: float = Field(0.0, ge=0.0)
    set_aside_requirement: float = Field(0.0, ge=0.0, le=1.0)


class ScenarioDef(_Strict):
    """A reference or a scenario as its folder defines it."""
    name: str
    kind: Literal["reference", "scenario"]
    description: str = ""
    #: the CAPRI files the definition follows (paths under CAPRI's gams folder)
    capri_files: List[str] = Field(default_factory=list)
    #: a reference: the trajectory folder it projects along
    trajectory: Optional[str] = None
    #: a scenario: its reference's folder
    reference: Optional[str] = None
    #: where the scenario runs on another reference than CAPRI's, the reason (shown with every run)
    reference_note: str = ""
    manure_trade: Optional[bool] = None
    biofuel_markets: Optional[bool] = None
    endotech: Endotech = Field(default_factory=Endotech)
    greendeal: Optional[GreenDeal] = None
    shocks: Shocks = Field(default_factory=Shocks)

    @model_validator(mode="after")
    def _kind(self):
        if self.kind == "reference":
            if self.reference or self.greendeal is not None or self.shocks != Shocks():
                raise ValueError(f"{self.name}: a reference has no reference, Green Deal switches or shocks")
            if not self.trajectory:
                raise ValueError(f"{self.name}: a reference names its trajectory")
        else:
            if not self.reference:
                raise ValueError(f"{self.name}: a scenario names its reference")
            if self.trajectory:
                raise ValueError(f"{self.name}: a scenario's trajectory is its reference's")
        return self


def _read(name: str, root: Path) -> ScenarioDef:
    f = root / name / "settings.toml"
    if not f.exists():
        raise FileNotFoundError(f"no scenario folder {name!r} under {root} (settings.toml)")
    with open(f, "rb") as fh:
        doc = tomllib.load(fh)
    if "scenario" not in doc:
        raise ValueError(f"{f}: no [scenario] table (a trajectory folder, not a scenario)")
    d = ScenarioDef(**doc["scenario"])
    if d.name != name:
        raise ValueError(f"{f}: name {d.name!r} is not its folder's {name!r}")
    return d


def load(name: str, root: Optional[Path] = None) -> ScenarioDef:
    """A scenario (or reference) read from its folder, checked; for a scenario its reference is read and checked too,
    and the settings the scenario does not give are taken from it."""
    root = Path(root) if root is not None else ROOT
    d = _read(name, root)
    if d.kind == "reference":
        return d
    ref = _read(d.reference, root)
    if ref.kind != "reference":
        raise ValueError(f"{name}: its reference {d.reference!r} is a scenario")
    upd = {}
    for k in ("manure_trade", "biofuel_markets"):
        if getattr(d, k) is None and getattr(ref, k) is not None:
            upd[k] = getattr(ref, k)
    et = {**ref.endotech.as_dict(), **d.endotech.as_dict()}
    if et != d.endotech.as_dict():
        upd["endotech"] = Endotech(**et)
    return d.model_copy(update=upd) if upd else d


def trajectory_of(d: ScenarioDef, root: Optional[Path] = None) -> str:
    """The trajectory folder a scenario projects along: its reference's."""
    return d.trajectory if d.kind == "reference" else _read(d.reference, Path(root) if root else ROOT).trajectory


def to_policy_scenario(d: ScenarioDef):
    """The model's PolicyScenario of a definition, built by the functions that build it from Python."""
    from capri_mod.policy.policy_module import PolicyScenario
    from capri_mod.policy.greendeal import greendeal_scenario
    if d.kind == "reference":
        raise ValueError(f"{d.name}: a reference is run as the baseline, not as a scenario")
    if d.greendeal is not None:
        g = d.greendeal
        sc = greendeal_scenario(lndscpTarg=g.lndscpTarg, orgTarg=g.orgTarg, pestRedu=g.pestRedu,
                                mineRedu=g.mineRedu, surpRedu=g.surpRedu, dietShift=g.dietShift, othPol=g.othPol,
                                surplus_rule=g.surplus_rule, manure_trade=d.manure_trade,
                                endotech=d.endotech.as_dict(), pesticide_rule=g.pesticide_rule)
        sc.name, sc.description = d.name, d.description or sc.description
        sc.biofuel_markets = d.biofuel_markets
        if d.shocks != Shocks():
            raise ValueError(f"{d.name}: shocks with the Green Deal group are not defined yet")
        return sc
    return PolicyScenario(name=d.name, description=d.description, manure_trade=d.manure_trade,
                          biofuel_markets=d.biofuel_markets, endotech=d.endotech.as_dict(),
                          carbon_tax=float(d.shocks.carbon_tax),
                          set_aside_requirement=float(d.shocks.set_aside_requirement))


def available(root: Optional[Path] = None) -> Dict[str, str]:
    """{folder: kind} of the scenario folders (trajectory folders left out)."""
    root = Path(root) if root is not None else ROOT
    out = {}
    for f in sorted(root.glob("*/settings.toml")):
        with open(f, "rb") as fh:
            doc = tomllib.load(fh)
        if "scenario" in doc:
            out[f.parent.name] = doc["scenario"].get("kind", "")
    return out

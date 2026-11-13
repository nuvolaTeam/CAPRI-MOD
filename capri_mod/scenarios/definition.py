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
#: the tables a scenario folder may hold, their columns, and the PolicyScenario field each fills
TABLES = {
    "coupled_support.csv": (("activity", "value"), "coupled_support"),
    "premium_factors.csv": (("region", "activity", "factor"), "premium_factor_regional"),
    "tariff_changes.csv": (("region", "commodity", "change_pct"), "tariff_changes"),
    "trq_volume_changes.csv": (("commodity", "change_kt"), "trq_volume_changes"),
    # CAPRI's obligatory set-aside rate in percent by regional unit and arable activity (DATA(ru, act, "SETR"),
    # supply_model.gms SETA_)
    "set_aside_rates.csv": (("region", "activity", "setr_pct"), "set_aside_rates"),
}


def roots() -> List[Path]:
    """Where scenario folders are looked for: the run's own folder (setting run.scenarios_dir), then the repository's
    (capri_data/scenarios). A user's scenario may name a reference or group of either."""
    out = []
    try:
        from capri_mod.settings import current as _settings
        user = str(_settings().get("run.scenarios_dir") or "")
    except Exception:
        user = ""
    if user:
        out.append(Path(user).expanduser())
    out.append(ROOT)
    return out


def find(name: str, root: Optional[Path] = None) -> Path:
    """The folder of a scenario, reference or group: under root if given, else the first of roots() holding it."""
    for r in ([Path(root)] if root is not None else []) + roots():
        if (r / name / "settings.toml").exists():
            return r / name
    raise FileNotFoundError(f"no scenario folder {name!r} (looked in {[str(r) for r in roots()]})")


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
    fallowInAllRmssup: Optional[float] = None
    winterCovInAllRmssup: Optional[float] = None

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


def _policy_defaults():
    from capri_mod.policy.policy_module import PolicyScenario
    return {k: f.default for k, f in PolicyScenario.__dataclass_fields__.items()}


#: the model's PolicyScenario defaults, the shocks' defaults (one definition)
_POLICY_DEFAULTS = _policy_defaults()


class Shocks(_Strict):
    """A scenario's policy shocks (the fields of the model's PolicyScenario, capri_mod/policy/policy_module.py, with
    their defaults there); tables of shocks are CSV files of the folder (TABLES)."""
    #: CAPRI's emission tax, EUR per t CO2-eq (ghgTax, pol_input/ecampa/carbtax50_endotech_*.gms)
    carbon_tax: float = Field(0.0, ge=0.0)
    #: a set-aside floor as a share of UAA (not with the Green Deal group: its landscape target sets it)
    set_aside_requirement: float = Field(0.0, ge=0.0, le=1.0)
    #: change of the BISS rate, EUR per ha
    biss_rate_change: float = 0.0
    #: relative changes of CAPRI's rural-development budgets (policy/rd_logic.gms), e.g. -0.2 for a 20% cut
    lfa_budget_change: float = Field(0.0, gt=-1.0)
    ae_budget_change: float = Field(0.0, gt=-1.0)
    n2k_budget_change: float = Field(0.0, gt=-1.0)
    #: share of Pillar I reported as eco-schemes (reporting only)
    eco_scheme_budget_pct: float = Field(_POLICY_DEFAULTS["eco_scheme_budget_pct"], ge=0.0, le=1.0)
    #: the EU and UK blending mandates times this factor (scen/bio_fuels/change_biof_mandate.gms)
    biofuel_mandate: Optional[float] = Field(None, ge=0.0)
    #: production quotas, 1000 t (none by default)
    milk_quota: Optional[float] = Field(None, ge=0.0)
    sugar_quota: Optional[float] = Field(None, ge=0.0)
    #: a member state's raw milk price may fall below zero (the Green Deal group sets it, greendeal_scenarios.gms
    #: l. 66-67); None: the scenario group's or the model's default
    negative_milk_price: Optional[bool] = None


class ScenarioDef(_Strict):
    """A reference or a scenario as its folder defines it."""
    name: str
    kind: Literal["reference", "scenario"]
    description: str = ""
    #: the short name in its runs' result names (capri_mod/io_results.result_name: res_2_1730<short_name>...), as
    #: CAPRI's result files carry the scenario's file name; empty: the folder's name
    short_name: str = ""
    #: the CAPRI files the definition follows (paths under CAPRI's gams folder)
    capri_files: List[str] = Field(default_factory=list)
    #: a reference: the trajectory folder it projects along
    trajectory: Optional[str] = None
    #: a scenario: its reference's folder
    reference: Optional[str] = None
    #: where the scenario runs on another reference than CAPRI's, the reason (shown with every run)
    reference_note: str = ""
    #: a scenario: the group whose data it reads (capri_data/scenarios/<group>/, a [group] folder), if any
    group: Optional[str] = None
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
            if self.greendeal is not None and self.group != "greendeal_group":
                raise ValueError(f"{self.name}: a Green Deal scenario reads the group greendeal_group")
        return self


def _read(name: str, root: Optional[Path] = None) -> ScenarioDef:
    f = find(name, root) / "settings.toml"
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
    d = _read(name, root)
    if d.kind == "reference":
        return d
    ref = _read(d.reference, root)
    if ref.kind != "reference":
        raise ValueError(f"{name}: its reference {d.reference!r} is a scenario")
    if d.group is not None:
        with open(find(d.group, root) / "settings.toml", "rb") as fh:
            if tomllib.load(fh).get("group", {}).get("name") != d.group:
                raise ValueError(f"{name}: its group {d.group!r} is not a group folder")
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
    return d.trajectory if d.kind == "reference" else _read(d.reference, root).trajectory


def tables(name: str, root: Optional[Path] = None) -> Dict[str, dict]:
    """The scenario's tables (TABLES) read from its folder and checked: their columns, and every code one of the
    model's (activities, regional units, market commodities, market regions). {PolicyScenario field: value}."""
    import csv
    from capri_mod.data.definitions import ALL_ACTIVITIES, MARKET_COMMODITIES, ALL_TRADE_REGIONS
    from capri_mod.data.inputs import current as _inputs
    with open(_inputs().path("regional_units.csv", "codes"), newline="") as fh:
        units = {r["region"] for r in csv.DictReader(fh)}
    known = {"activity": set(ALL_ACTIVITIES), "commodity": set(MARKET_COMMODITIES)}
    folder, out = find(name, root), {}
    for fname, (cols, field) in TABLES.items():
        f = folder / fname
        if not f.exists():
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            head = tuple(rows[0].keys()) if rows else tuple(csv.reader(open(f)).__next__())
        if head != cols:
            raise ValueError(f"{f}: columns {list(head)}, expected {list(cols)}")
        for i, r in enumerate(rows, start=2):
            for c in cols[:-1]:
                ok = (r[c] in units) if (c == "region" and fname in ("premium_factors.csv", "set_aside_rates.csv")) else \
                     (r[c] in set(ALL_TRADE_REGIONS)) if c == "region" else (r[c] in known[c])
                if not ok:
                    raise ValueError(f"{f} line {i}: {c} {r[c]!r} is not one of the model's")
            float(r[cols[-1]])
        if fname == "coupled_support.csv":
            out[field] = {r["activity"]: float(r["value"]) for r in rows}
        elif fname == "trq_volume_changes.csv":
            out[field] = {r["commodity"]: float(r["change_kt"]) for r in rows}
        else:
            k1, k2, v = cols
            d = {}
            for r in rows:
                d.setdefault(r[k1], {})[r[k2]] = float(r[v])
            out[field] = d
    return out


def to_policy_scenario(d: ScenarioDef, root: Optional[Path] = None):
    """The model's PolicyScenario of a definition, built by the functions that build it from Python, with its shocks
    and its folder's tables."""
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
        if d.shocks.set_aside_requirement:
            raise ValueError(f"{d.name}: a set-aside floor with the Green Deal group (its landscape target sets it)")
    else:
        sc = PolicyScenario(name=d.name, description=d.description, manure_trade=d.manure_trade,
                            biofuel_markets=d.biofuel_markets, endotech=d.endotech.as_dict(),
                            set_aside_requirement=float(d.shocks.set_aside_requirement))
    sh = d.shocks
    for f in ("carbon_tax", "biss_rate_change", "lfa_budget_change", "ae_budget_change", "n2k_budget_change",
              "eco_scheme_budget_pct"):
        if getattr(sh, f) != Shocks.model_fields[f].default or f == "carbon_tax":
            setattr(sc, f, float(getattr(sh, f)))
    for f in ("biofuel_mandate", "milk_quota", "sugar_quota", "negative_milk_price"):
        if getattr(sh, f) is not None:
            setattr(sc, f, getattr(sh, f))
    for f, v in tables(d.name, root).items():
        setattr(sc, f, v)
    return sc


def available(root: Optional[Path] = None) -> Dict[str, str]:
    """{folder: kind} of the scenario folders (trajectory folders left out)."""
    out = {}
    for f in sorted(f for r in ([Path(root)] if root is not None else roots()[::-1]) for f in r.glob("*/settings.toml")):
        with open(f, "rb") as fh:
            doc = tomllib.load(fh)
        if "scenario" in doc:
            out[f.parent.name] = doc["scenario"].get("kind", "")
    return out

"""The scenario assistant's tool layer (capri_gradio/capri_gui.py): what a language model, or the GUI's own forms,
may do with capri-mod. Every call is checked here before anything is written or run.

The language model never touches files, code or the model: it answers with tool calls, which this module validates
against the scenario definition (capri_mod/scenarios/definition.py, pydantic) and the settings (capri_mod/settings),
and executes locally. Only the request and the small summaries returned here leave the machine. Runs are started by
the user in the GUI, never by the model (start_run is not among the model's tools).

Tools for the model (MODEL_TOOLS): list_scenarios, describe_scenario, make_scenario, list_settings, list_runs,
run_summary. The GUI also uses start_run, run_status and the job registry.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from capri_mod.scenarios import definition as SD  # noqa: E402

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,79}$")


def _greendeal_values() -> Dict[str, tuple]:
    """The Green Deal switches' allowed values as capri-mod implements them (CAPRI star 3.0's GUI values;
    capri_mod/policy/greendeal.py); dietShift and othPol are not implemented, so 0 only."""
    from capri_mod.policy import greendeal as G
    out = {k: tuple(v) for k, v in G._SUPPORTED.items()}
    out["mineRedu"] = tuple(G._MINE_REDU)
    for k in G._NOT_IMPLEMENTED:
        out[k] = (0,)
    return out


GREENDEAL_VALUES = _greendeal_values()


# --------------------------------------------------------------------------- #
# Where user scenarios and runs go
# --------------------------------------------------------------------------- #
def default_scenarios_dir() -> Path:
    """The run's own scenario folder (setting run.scenarios_dir), else user_scenarios/ in the repository (ignored by
    git): the assistant writes there, never into capri_data/scenarios."""
    from capri_mod.settings import current
    d = str(current().get("run.scenarios_dir") or "")
    return Path(d).expanduser() if d else ROOT / "user_scenarios"


# --------------------------------------------------------------------------- #
# A small TOML writer for a scenario's [scenario] table (strings, numbers, booleans, lists of strings, subtables)
# --------------------------------------------------------------------------- #
def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    raise TypeError(f"no TOML form for {type(v).__name__}")


def scenario_toml(d: SD.ScenarioDef, comment: str = "") -> str:
    """The settings.toml of a scenario definition: the fields that differ from the defaults, CAPRI's order kept."""
    data = d.model_dump(exclude_defaults=True)
    data.setdefault("name", d.name)
    data.setdefault("kind", d.kind)
    sub = {k: data.pop(k) for k in ("endotech", "greendeal", "shocks") if isinstance(data.get(k), dict)}
    if d.greendeal is not None and "greendeal" not in sub:
        sub["greendeal"] = {}
    lines = [f"# {c}" for c in comment.splitlines() if c.strip()] if comment else []
    lines.append("[scenario]")
    for k, v in data.items():
        if v is not None:
            lines.append(f"{k} = {_toml_value(v)}")
    for t, vals in sub.items():
        lines += ["", f"[scenario.{t}]"] + [f"{k} = {_toml_value(v)}" for k, v in vals.items() if v is not None]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
def list_scenarios(scenarios_dir: Optional[Path] = None) -> dict:
    """The references and scenarios a new scenario can build on or be compared with: {name: {kind, description,
    reference, where}}."""
    out = {}
    roots = ([Path(scenarios_dir)] if scenarios_dir else []) + [SD.ROOT]
    for r in roots:
        for name, kind in SD.available(r).items():
            if name in out:
                continue
            try:
                d = SD._read(name, r)
                out[name] = {"kind": kind, "description": d.description, "reference": d.reference or "",
                             "where": "user" if r != SD.ROOT else "repository"}
            except Exception as e:                     # a broken folder is shown, not hidden
                out[name] = {"kind": kind, "error": str(e), "where": "user" if r != SD.ROOT else "repository"}
    return out


def describe_scenario(name: str, scenarios_dir: Optional[Path] = None) -> dict:
    """A scenario's or reference's definition as stored, with the reference's settings it inherits."""
    root = _root_of(name, scenarios_dir)
    d = SD.load(name, root)
    return {"definition": d.model_dump(exclude_defaults=True), "settings_toml": (SD.find(name, root) /
                                                                               "settings.toml").read_text()}


def scenario_schema() -> dict:
    """The JSON schema of make_scenario's input: CAPRI-mod's scenario definition, kind fixed to "scenario"."""
    s = SD.ScenarioDef.model_json_schema()
    s["properties"].pop("kind", None)
    s["properties"].pop("trajectory", None)
    s["required"] = ["name", "reference"]
    # the Green Deal switches' allowed values, from the one place that holds them (capri_mod/policy/greendeal.py)
    gd = s.get("$defs", {}).get("GreenDeal", {}).get("properties", {})
    for k, vals in GREENDEAL_VALUES.items():
        if k in gd:
            gd[k]["enum"] = list(vals)
    s["description"] = ("A capri-mod scenario on a reference: either the Green Deal scenario group's switches "
                        "(set group = \"greendeal_group\" and the table greendeal) or policy shocks (table shocks). "
                        "Only the fields that differ from their defaults are needed.")
    return s


def make_scenario(args: dict, scenarios_dir: Optional[Path] = None, overwrite: bool = False) -> dict:
    """Check a scenario definition and write it to scenarios_dir/<name>/settings.toml. Returns {"ok", "name", "path",
    "toml"} or {"ok": False, "errors": [...]} (nothing written). A name of the repository's scenarios is refused."""
    sdir = Path(scenarios_dir) if scenarios_dir else default_scenarios_dir()
    a = {k: v for k, v in dict(args or {}).items() if v not in (None, "", {}, [])}
    a["kind"] = "scenario"
    errors = []
    name = str(a.get("name", ""))
    if not NAME_RE.match(name):
        errors.append(f"name {name!r}: 3-80 characters, a letter first, then letters, digits or _")
    if name in SD.available(SD.ROOT):
        errors.append(f"name {name!r} is a scenario of the repository: choose another")
    try:
        d = SD.ScenarioDef(**a)
    except Exception as e:
        return {"ok": False, "errors": errors + _pydantic_errors(e)}
    refs = {n for n, k in list_scenarios(sdir).items() if k.get("kind") == "reference"}
    if d.reference not in refs:
        errors.append(f"reference {d.reference!r} is not one of the references: {sorted(refs)}")
    if d.group is not None and d.group not in _groups():
        errors.append(f"group {d.group!r} is not a group folder: {sorted(_groups())}")
    if d.greendeal is not None:
        try:                                            # the switches' allowed values live in greendeal.py
            from capri_mod.policy.greendeal import greendeal_scenario
            g = d.greendeal
            greendeal_scenario(lndscpTarg=g.lndscpTarg, orgTarg=g.orgTarg, pestRedu=g.pestRedu, mineRedu=g.mineRedu,
                               surpRedu=g.surpRedu, dietShift=g.dietShift, othPol=g.othPol,
                               surplus_rule=g.surplus_rule, pesticide_rule=g.pesticide_rule)
        except Exception as e:
            errors.append(f"Green Deal switches: {e}")
    folder = sdir / name
    if folder.exists() and not overwrite:
        errors.append(f"{folder} exists (overwrite to replace it)")
    if errors:
        return {"ok": False, "errors": errors}
    folder.mkdir(parents=True, exist_ok=True)
    text = scenario_toml(d, comment=f"written by the capri-mod GUI, {time.strftime('%Y-%m-%d %H:%M')}")
    (folder / "settings.toml").write_text(text)
    try:                                                # read back exactly as a run will read it
        SD.load(name, sdir)
    except Exception as e:
        return {"ok": False, "errors": [f"written but not readable back: {e}"], "path": str(folder)}
    warnings = []
    if (d.greendeal is None or d.greendeal == SD.GreenDeal()) and d.shocks == SD.Shocks():
        warnings.append("no Green Deal switch and no shock differs from the reference: the run will reproduce the "
                        "baseline")
    return {"ok": True, "name": name, "path": str(folder), "toml": text, "warnings": warnings}


def list_settings(prefix: str = "") -> dict:
    """The run settings (capri_mod/settings/defaults.toml) under a prefix, with their default values: what a run's
    overrides may change."""
    from capri_mod import settings as S
    return {k: v for k, v in S._defaults_flat().items() if k.startswith(prefix)}


def check_overrides(overrides: Dict[str, object]) -> List[str]:
    """The errors of a run's setting overrides: unknown keys, values of another type than the default's."""
    from capri_mod import settings as S
    base, errs = S._defaults_flat(), []
    for k, v in (overrides or {}).items():
        if k not in base:
            errs.append(f"unknown setting {k!r}")
        elif not S._type_ok(base[k], v):
            errs.append(f"{k}: {v!r} is not of the default's type ({type(base[k]).__name__})")
    return errs


def list_runs(results_dir: Optional[Path] = None) -> list:
    """The stored runs (newest first): result name, label, status, scenario, run id, converged, iterations, settings
    changed."""
    import results_data as RD
    r = RD.runs(results_dir or RD.default_store())
    cols = ["result name", "label", "status", "scenario", "run_id", "converged", "iterations", "regions",
            "settings changed"]
    return r[cols].head(20).to_dict("records") if not r.empty else []


def run_summary(scenario: str, run_id: str, results_dir: Optional[Path] = None) -> dict:
    """A small summary of a stored run for the model: its convergence and the Farm-to-Fork indicators (% change from
    the baseline, EU27) beside JRC121368's; numbers rounded, each with the run's id."""
    import results_data as RD
    root = results_dir or RD.default_store()
    meta = RD.run_summary(root, scenario, run_id)
    ind = RD.jrc_indicators(root, [RD.run_label(scenario, run_id)])
    col = RD.run_label(scenario, run_id)
    regions = str((meta.get("options") or {}).get("regions") or "")
    return {"run": col, "converged": meta.get("conv"), "iterations": meta.get("it"),
            "settings_changed": meta.get("settings_changed"),
            "subset_of_regions": bool(regions),
            "note": ("a run on a subset of regional units: its EU figures are not comparable with CAPRI's "
                     "(KNOWN_ISSUES K83)") if regions else "",
            "indicators_pct_change": {r["indicator"]: {"run": round(float(r[col]), 2),
                                                       "JRC121368": r["JRC121368 (CAPRI)"]}
                                      for r in ind.to_dict("records")}}


#: the tools a language model may call, with their JSON input schemas (provider-neutral; llm.py adapts them)
def model_tools() -> List[dict]:
    return [
        {"name": "list_scenarios", "description": "List the references and scenarios (name, kind, description).",
         "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "describe_scenario", "description": "A scenario's or reference's full definition.",
         "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"],
                          "additionalProperties": False}},
        {"name": "make_scenario",
         "description": ("Write a new scenario after checking it. Fails with a list of errors if the definition is "
                         "not valid; then correct it and call again. Does not run it: the user starts the run."),
         "input_schema": scenario_schema()},
        {"name": "list_settings", "description": "Run settings with their defaults, under a prefix such as 'market.'.",
         "input_schema": {"type": "object", "properties": {"prefix": {"type": "string"}},
                          "additionalProperties": False}},
        {"name": "list_runs", "description": "The stored runs, newest first.",
         "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "run_summary", "description": "Convergence and Farm-to-Fork indicators of a stored run.",
         "input_schema": {"type": "object", "properties": {"scenario": {"type": "string"},
                                                           "run_id": {"type": "string"}},
                          "required": ["scenario", "run_id"], "additionalProperties": False}},
    ]


def call_tool(name: str, args: dict, scenarios_dir: Optional[Path] = None,
              results_dir: Optional[Path] = None) -> dict:
    """Execute one of the model's tools; any failure is returned as {"ok": False, "errors": [...]}, never raised."""
    try:
        if name == "list_scenarios":
            return {"ok": True, "scenarios": list_scenarios(scenarios_dir)}
        if name == "describe_scenario":
            return {"ok": True, **describe_scenario(args["name"], scenarios_dir)}
        if name == "make_scenario":
            return make_scenario(args, scenarios_dir)
        if name == "list_settings":
            return {"ok": True, "settings": list_settings(args.get("prefix", ""))}
        if name == "list_runs":
            return {"ok": True, "runs": list_runs(results_dir)}
        if name == "run_summary":
            return {"ok": True, **run_summary(args["scenario"], args["run_id"], results_dir)}
        return {"ok": False, "errors": [f"unknown tool {name!r}"]}
    except Exception as e:
        return {"ok": False, "errors": [f"{type(e).__name__}: {e}"]}


# --------------------------------------------------------------------------- #
# Runs (started by the user in the GUI)
# --------------------------------------------------------------------------- #
@dataclass
class Job:
    scenario: str
    cmd: List[str]
    log: Path
    out: Path
    proc: Optional[subprocess.Popen] = None
    started: float = field(default_factory=time.time)
    owner: str = ""                     # the browser session that started it (a shared page)

    def status(self) -> dict:
        rc = self.proc.poll() if self.proc else None
        text = self.log.read_text(errors="replace") if self.log.exists() else ""
        its = re.findall(r"^\[[^\]]+\] (.*iteration \d+:.*)$", text, flags=re.M)
        saved = re.search(r"^saved .*$", text, flags=re.M)
        return {"running": self.proc is not None and rc is None, "returncode": rc,
                "seconds": round(time.time() - self.started), "iterations": its[-30:],
                "saved": saved.group(0) if saved else "", "tail": "\n".join(text.splitlines()[-15:])}


JOBS: Dict[str, Job] = {}


def run_command(scenario: str, out: Path, scenarios_dir: Optional[Path] = None, regions: str = "",
                overrides: Optional[Dict[str, object]] = None) -> List[str]:
    """The run script's command line for a scenario (tools/run/run_f2f_2030.py, as the project's runs)."""
    cmd = [sys.executable, str(ROOT / "tools" / "run" / "run_f2f_2030.py"), str(out), "--scenario", scenario]
    if scenarios_dir:
        cmd += ["--scenarios-dir", str(scenarios_dir)]
    if regions:
        cmd += ["--regions", regions]
    for k, v in (overrides or {}).items():
        cmd += ["--set", f"{k}={json.dumps(v) if not isinstance(v, str) else v}"]
    return cmd


def start_run(scenario: str, scenarios_dir: Optional[Path] = None, regions: str = "",
              overrides: Optional[Dict[str, object]] = None, runs_dir: Optional[Path] = None,
              workers: int = 2, owner: str = "") -> dict:
    """Start a run in the background (one at a time: a run takes the machine's cores). Returns {"ok", "job"}."""
    going = [j for j in JOBS.values() if j.status()["running"]]
    if going:
        mins = round((time.time() - going[0].started) / 60)
        return {"ok": False, "errors": [f"a run is going (started {mins} minutes ago): one at a time"]}
    errs = check_overrides(overrides or {})
    known = list_scenarios(scenarios_dir)
    if known.get(scenario, {}).get("kind") != "scenario":
        names = sorted(k for k, v in known.items() if v.get("kind") == "scenario")
        errs.append(f"{scenario!r} is not a scenario: {names}")
    if errs:
        return {"ok": False, "errors": errs}
    rdir = Path(runs_dir) if runs_dir else ROOT / "user_runs"
    rdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out, log = rdir / f"{scenario}_{stamp}.pkl", rdir / f"{scenario}_{stamp}.log"
    cmd = run_command(scenario, out, scenarios_dir, regions, overrides)
    env = {**os.environ, "CAPRI_WORKERS": str(workers), "PYTHONHASHSEED": "0"}
    fh = open(log, "w")
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=fh, stderr=subprocess.STDOUT, env=env)
    jid = f"{scenario}_{stamp}"
    JOBS[jid] = Job(scenario=scenario, cmd=cmd, log=log, out=out, proc=proc, owner=owner)
    return {"ok": True, "job": jid, "log": str(log)}


def stop_run(jid: str, owner: Optional[str] = None) -> dict:
    """Stop a run; with owner given (a shared page), only the session that started it may."""
    j = JOBS.get(jid)
    if j is None or j.proc is None or j.proc.poll() is not None:
        return {"ok": False, "errors": [f"no running job {jid!r}"]}
    if owner is not None and j.owner != owner:
        return {"ok": False, "errors": ["the run was started by another session"]}
    j.proc.terminate()
    return {"ok": True}


def _root_of(name: str, scenarios_dir: Optional[Path]) -> Optional[Path]:
    if scenarios_dir and (Path(scenarios_dir) / name / "settings.toml").exists():
        return Path(scenarios_dir)
    return None


def _groups() -> set:
    import tomllib
    out = set()
    for f in SD.ROOT.glob("*/settings.toml"):
        with open(f, "rb") as fh:
            if "group" in tomllib.load(fh):
                out.add(f.parent.name)
    return out


def _pydantic_errors(e) -> List[str]:
    try:
        return [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()]
    except Exception:
        return [str(e)]

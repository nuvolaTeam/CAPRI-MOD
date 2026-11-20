#!/usr/bin/env python3
"""Inventory of CAPRI's calibration systems against CAPRI-mod's code (the refactor's second phase, block C0;
docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md section 5).

One row per equation of the calibration models the plan names (CAPRI star 3.0), each model's MODEL statement read
with its nested models and $include files followed, plus one row per calibration system CAPRI writes as assignments
rather than a model (the PMP terms, the Armington shares):

- system: the calibration system (SYSTEMS below: the fertiliser priors, the land supply estimation, the land-use
  change estimation, the market's Armington calibration, the PMP terms);
- models: the MODEL statements listing the equation (nested models expanded);
- capri_definition: file and lines of each definition found in the star 3.0 tree;
- solved_in: the statements that solve the system's models (file:line; commented ones left out);
- capri_run: where CAPRI runs the system (by hand, SYSTEMS: the baseline calibration, the generation of the
  simulation's start point sim_ini, or the Green Deal step), with its source;
- model_files_citing: the files of capri_mod and tools/build naming the equation, with the count (a pointer);
- status, model_location, notes: written by hand and kept when the inventory is rebuilt.

    python tools/refactor/calibration_equations_inventory.py GAMS_DIR [--out docs/dev/calibration_equations_inventory.csv]

GAMS_DIR is CAPRI's gams folder (star 3.0: arm/market_model.gms 4,607 lines).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAND = ("status", "model_location", "notes")

_spec = importlib.util.spec_from_file_location("_sup_inv", Path(__file__).with_name("supply_equations_inventory.py"))
_sup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sup)
definitions = _sup.definitions

# the calibration systems: (system, file holding the MODEL statements, the models to list, where CAPRI runs it)
SYSTEMS = [
    ("fertiliser priors", "fert/fert_mod.gms", ["m_fertDist"],
     "baseline calibration: capmod/def_fert_and_requirements.gms solves it through fert/ferttrm_cor_tj.gms (l. 903) "
     "and exits for a scenario before (l. 173, BASELINE off)"),
    ("fertiliser priors", "supply/supply_model.gms", ["m_dualFertDist"],
     "not solved in star 3.0: its includes (fert/solve_only_inner_fertdist_model.gms) are commented out in "
     "supply/pmp.gms l. 256 and 273; m_dualFertDistFOC's equations are in the simulation model (the supply phase)"),
    ("land supply estimation", "supply/declare_calibration_models_for_land_supply.gms",
     ["m_land_supply_estim", "m_land_supply_equations_without_objective", "m_LandSupply"],
     "baseline calibration: supply/cal_land_nests.gms (l. 640-657, solve_land_supply_estimation.gms), part of "
     "supply/calibrate_supply.gms, which capmod.gms includes with BASELINE on (l. 1416-1424)"),
    ("land-use change estimation", "supply/declare_calibration_models_for_luc.gms",
     ["m_estLUCfromMaxDens", "m_estLUCfromFOC"],
     "the supply models' start: supply/prep_sim_luc.gms (l. 472-568), from supply/pmp.gms l. 228 and "
     "supply/def_start_value_and_data.gms l. 58 (REPORTS_ENV on); the supply phase's N14b"),
    ("market Armington calibration", "arm/market_model.gms", ["m_calibKVT"],
     "solved only with modArmington == extendedKVT (arm/cal_armington.gms l. 218; the file exits at l. 89 with "
     "modArmington off)"),
]
# the systems CAPRI writes as assignments (no MODEL statement): (system, name, CAPRI's files, where CAPRI runs it)
ASSIGNMENTS = [
    ("PMP terms", "PMP terms (p_pmpCnst, p_pmpQuadTechn, p_pmpQuadPact, p_pmpQuadLandTypes)",
     "supply/calibrate_supply.gms (m_capMod, m_capModQ solved at the calibration point), supply/define_pmp_terms.gms, "
     "supply/pmp_terms/*.gms",
     "baseline calibration: capmod.gms l. 1416-1424 (BASELINE on); the step reads them from the baseline's pmppar "
     "files (capmod/create_sim_ini_gdx.gms l. 491) and prepares them (supply/prep_sim_pmp_terms.gms)"),
    ("market Armington calibration", "Armington shares (p_dpCESTrade)", "arm/cal_armington.gms",
     "the simulation's start point: arm/market1.gms l. 625, which capmod/create_sim_ini_gdx.gms includes (l. 266, "
     "MARKET_M on) when sim_ini is generated (capmod.gms l. 646, generateSimIni)"),
]


def _model_text(G: Path, rel: str) -> list:
    """The file's lines with its $include files spliced in (relative to G), $ontext blocks dropped."""
    out, skip = [], False
    for raw in (G / rel).read_text(errors="replace").splitlines():
        s = raw.strip()
        if re.match(r"\$ontext", s, re.I):
            skip = True
            continue
        if re.match(r"\$offtext", s, re.I):
            skip = False
            continue
        if skip:
            continue
        m = re.match(r"\$\s*include\s+['\"]?([^'\"\s]+)['\"]?", s, re.I)
        if m and (G / m.group(1).replace("\\", "/")).exists():
            out += _model_text(G, m.group(1).replace("\\", "/"))
            continue
        out.append(raw)
    return out


def model_statements(G: Path, rel: str) -> dict:
    """{model (lower case): (name, [(entry, condition)])} of the MODEL statements of a file, includes followed."""
    out, cur, stack, pending = {}, None, [], None
    for raw in _model_text(G, rel):
        line = raw.strip()
        m = re.match(r"model\s+(m_\w+)\s*(\".*?\")?\s*(/(.*))?$", line, re.I)
        if m and cur is None:
            if m.group(3) is None:
                pending = m.group(1)            # the list's '/' on a following line
                continue
            cur, pending = m.group(1), None
            out[cur.lower()], stack = (cur, []), []
            line = m.group(4).strip()
            if not line:
                continue
        elif pending and cur is None and line.startswith("/"):
            cur, pending = pending, None
            out[cur.lower()], stack = (cur, []), []
            line = line[1:].strip()
            if not line:
                continue
        elif pending and cur is None and line and not line.startswith("*"):
            pending = None
        if cur is None or not line or line.startswith("*"):
            continue
        m = re.match(r"\$iftheni?\.(\w+)\s+(.*)", line, re.I)
        if m:
            stack.append(m.group(2).strip())
            continue
        if re.match(r"\$else", line, re.I):
            stack[-1] = "NOT(" + stack[-1] + ")"
            continue
        if re.match(r"\$endif", line, re.I):
            stack.pop()
            continue
        cond = ""
        m = re.match(r"\$\s*(ifi|ife|if)(\.\w+)?\s+(not\s+)?(\S+\s*==\s*\S+)\s+(.*)", line, re.I)
        if m:
            cond = (m.group(3) or "") + m.group(4)
            line = m.group(5)
        elif line.startswith("$"):
            continue
        end = "/" in line
        for name in re.split(r"[,\s/;]+", line.split("*")[0]):
            if re.match(r"^[A-Za-z]\w*$", name):
                out[cur.lower()][1].append((name, " & ".join(c for c in stack + [cond] if c)))
        if end:
            cur = None
    return out


def expand(stmts: dict, model: str, cond: str = "", path=()) -> list:
    """[(equation, condition, the models it is listed in)] of a model, nested models expanded."""
    name, entries = stmts[model.lower()]
    rows = []
    for n, c in entries:
        cc = " & ".join(x for x in (cond, c) if x)
        if n.lower() in stmts:
            rows += expand(stmts, n, cc, path + (name,))
        else:
            rows.append((n, cc, path + (name,)))
    return rows


def solve_sites(G: Path, models: list) -> list:
    pat = re.compile(r"^\s*solve\s+(" + "|".join(re.escape(m) for m in models) + r")\b", re.I)
    hits = []
    for f in sorted(G.rglob("*.gms")):
        for i, line in enumerate(f.read_text(errors="replace").splitlines()):
            if pat.match(line):
                hits.append(f"{f.relative_to(G).as_posix()}:{i + 1}")
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/dev/calibration_equations_inventory.csv")
    a = ap.parse_args()
    G = a.gams_dir
    old = {(r["system"], r["equation"]): r for r in csv.DictReader(a.out.open())} if a.out.exists() else {}
    texts = {p: p.read_text(errors="replace") for d in ("capri_mod", "tools/build")
             for p in sorted((ROOT / d).rglob("*.py")) if "tests" not in p.parts}
    cols = ["system", "equation", "models", "condition_in_model_list", "capri_definition", "solved_in", "capri_run",
            "model_files_citing", *HAND]
    rows = []
    for system, rel, models, run in SYSTEMS:
        stmts = model_statements(G, rel)
        eqs, seen = [], {}
        for m in models:
            for n, c, path in expand(stmts, m):
                k = n.lower()
                if k not in seen:
                    seen[k] = (n, c, list(path))
                    eqs.append(k)
                else:
                    seen[k][2].extend(x for x in path if x not in seen[k][2])
        defs = definitions(G, set(eqs))
        sites = "; ".join(solve_sites(G, models))
        for k in eqs:
            n, c, path = seen[k]
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9])", re.I)
            hits = sorted(((len(pat.findall(t)), p.relative_to(ROOT).as_posix()) for p, t in texts.items()
                           if pat.search(t)), key=lambda h: (-h[0], h[1]))
            rows.append({"system": system, "equation": n, "models": "; ".join(dict.fromkeys(path)),
                         "condition_in_model_list": c, "capri_definition": "; ".join(defs.get(k, ["not found"])),
                         "solved_in": sites, "capri_run": run,
                         "model_files_citing": "; ".join(f"{p} ({c_})" for c_, p in hits[:6])})
    for system, name, files, run in ASSIGNMENTS:
        rows.append({"system": system, "equation": name, "models": "(assignments)", "condition_in_model_list": "",
                     "capri_definition": files, "solved_in": "", "capri_run": run, "model_files_citing": ""})
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            r.update({h: old.get((r["system"], r["equation"]), {}).get(h, "") for h in HAND})
            w.writerow(r)
    from collections import Counter
    print(f"{len(rows)} rows ({dict(Counter(r['system'] for r in rows))}) -> {a.out}")


if __name__ == "__main__":
    main()

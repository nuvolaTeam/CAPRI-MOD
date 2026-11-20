#!/usr/bin/env python3
"""Inventory of CAPRI's market-model equations against CAPRI-mod's code (the refactor's second phase, block M0;
docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md).

One row per equation of CAPRI's market simulation model m_globMarket (arm/market_model.gms, CAPRI star 3.0: its MODEL
statement, which nests m_bevFunctionsMarket) and of the net trade model m_netTrade (which nests the same behavioural
functions), with the $if condition each is listed under. For each:

- models: the MODEL statements listing it (m_bevFunctionsMarket, m_globMarket, m_netTrade);
- planned_module: the module of capri_mod/market/equations/market_model/ it goes to, by the block of market_model.gms
  its definition is in (the file's banners, BLOCKS below);
- in_gd2030_step: whether it is in m_globMarket with its condition true in CAPRI's 2030 Green Deal step, with the
  switches of docs/dev/market_equations_gd_switches.csv (each with its source); m_netTrade's rows are "no" (CAPRI
  solves m_netTrade only in arm/ini_netTradeModel.gms, which no file of star 3.0 includes);
- capri_definition: file and lines of each definition found in the star 3.0 tree;
- model_files_citing: the files of capri_mod (tests apart) naming the equation, with the count (a first pointer, not
  proof that the equation is ported);
- status, model_location, notes: written by hand, block by block, and kept when the inventory is rebuilt.

    python tools/refactor/market_equations_inventory.py GAMS_DIR [--out docs/dev/market_equations_inventory.csv]

GAMS_DIR is CAPRI's gams folder (the one holding arm/market_model.gms, 4,607 lines in star 3.0).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAND = ("status", "model_location", "notes")
MODELS = ("m_bevFunctionsMarket", "m_globMarket", "m_netTrade")

_spec = importlib.util.spec_from_file_location("_sup_inv", Path(__file__).with_name("supply_equations_inventory.py"))
_sup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sup)
definitions, active = _sup.definitions, _sup.active

# the blocks of arm/market_model.gms's equations (first line, last line, module), from the file's banners (CAPRI
# star 3.0, 4,607 lines): QUANTITIES - behavioural functions (l. 816-1995: the demand system, feed, dairy, oilseed
# processing, biofuels, by-products, the supply NQ functions and the young animals, input markets, land), LULUCF
# CARBON EFFECTS (l. 1996-2375), the fudging functions and the regional aggregation (l. 2376-2478), the net trade
# model's equations (l. 2479-2594), the adding up conditions and the Armington system (l. 2595-2841), PRICES
# (l. 2842-3130), the policy representation (l. 3131-3768: TRQs and tariffs, intervention stocks, subsidised exports)
# and the objectives (l. 3769-4149: FlipFlop_, the calibration's)
BLOCKS = [(816, 918, "demand"), (919, 1064, "feed"), (1065, 1114, "dairy"), (1115, 1179, "processing"),
          (1180, 1439, "biofuels"), (1440, 1523, "processing"), (1524, 1656, "supply"), (1657, 1995, "land"),
          (1996, 2375, "lulucf"), (2376, 2434, "fudging"), (2435, 2478, "aggregation"), (2479, 2594, "net_trade"),
          (2595, 2841, "armington"), (2842, 3130, "prices"), (3131, 3488, "border"), (3489, 3768, "intervention"),
          (3769, 4149, "objective")]


def market_definitions(G: Path, names: set) -> dict:
    """Definitions in arm/market_model.gms first ('name(domain) $ cond ..', the condition up to 60 lines: the market's
    long $ conditions), then, for the names not defined there, anywhere in the tree (the supply tool's definitions)."""
    lines = (G / "arm/market_model.gms").read_text(errors="replace").splitlines()
    defs = {}
    for i, line in enumerate(lines):
        if line.startswith("*"):
            continue
        m = re.match(r"^\s*([A-Za-z]\w*)\s*(\(|\$|\.\.)", line)
        if not m or m.group(1).lower() not in names:
            continue
        j, text = i, ""
        while j < len(lines) and j < i + 60:
            if not lines[j].startswith("*"):
                text += " " + lines[j]
            if ".." in text or ";" in text:
                break
            j += 1
        k = text.find("..")
        # a definition: '..' before the statement ends (the declarations at l. 571-815 and the MODEL lists carry none;
        # the market's conditions read v_x.LO and v_x.UP, so an attribute does not mark an assignment here)
        if k < 0 or ";" in text[:k]:
            continue
        e = j
        while e < len(lines) and not re.search(r";\s*(\*.*)?$", lines[e]):
            e += 1
        defs.setdefault(m.group(1).lower(), []).append(f"arm/market_model.gms:{i + 1}-{e + 1}")
    rest = {n for n in names if n not in defs}
    if rest:
        for n, d in definitions(G, rest).items():
            defs[n] = d
    return defs


def model_statements(G: Path) -> dict:
    """{model: [(entry, condition)]} of the MODEL statements of arm/market_model.gms, the $if conditions followed."""
    lines = (G / "arm/market_model.gms").read_text(errors="replace").splitlines()
    out, cur, stack = {}, None, []
    for raw in lines:
        line = raw.strip()
        m = re.match(r"model\s+(m_\w+)\s*(\".*?\")?\s*/(.*)$", line, re.I)
        if m and cur is None:
            cur = m.group(1)
            out[cur], stack = [], []
            line = m.group(3).strip()
            if not line:
                continue
        if cur is None:
            continue
        if not line or line.startswith("*"):
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
                out[cur].append((name, " & ".join(c for c in stack + [cond] if c)))
        if end:
            cur = None
    return out


def expand(stmts: dict, model: str, cond: str = "") -> list:
    """The model's equations, nested models expanded: [(equation, condition)]."""
    rows = []
    for n, c in stmts.get(model, []):
        cc = " & ".join(x for x in (cond, c) if x)
        if n in stmts:
            rows += expand(stmts, n, cc)
        else:
            rows.append((n, cc))
    return rows


def module_of(defn: str) -> str:
    m = re.match(r"arm/market_model\.gms:(\d+)", defn)
    if not m:
        return "outside market_model.gms"
    ln = int(m.group(1))
    return next((nm + ".py" for a, b, nm in BLOCKS if a <= ln <= b), "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/dev/market_equations_inventory.csv")
    ap.add_argument("--switches", type=Path, default=ROOT / "docs/dev/market_equations_gd_switches.csv")
    a = ap.parse_args()
    G = a.gams_dir
    sw = {r["switch"].lower(): r["value"] for r in csv.DictReader(a.switches.open())}
    stmts = model_statements(G)
    glob, net, bev = expand(stmts, "m_globMarket"), expand(stmts, "m_netTrade"), expand(stmts, "m_bevFunctionsMarket")
    eqs, seen, cond, models = [], set(), {}, {}
    for model, rows in (("m_globMarket", glob), ("m_netTrade", net)):
        for n, c in rows:
            models.setdefault(n.lower(), [])
            if model not in models[n.lower()]:
                models[n.lower()].append(model)
            if n.lower() not in seen:
                seen.add(n.lower())
                eqs.append(n)
                cond[n.lower()] = c if model == "m_globMarket" else ""
    for n, _ in bev:
        if "m_bevFunctionsMarket" not in models[n.lower()]:
            models[n.lower()].insert(0, "m_bevFunctionsMarket")
    gcond = {n.lower(): c for n, c in glob}
    defs = market_definitions(G, seen)
    old = {r["equation"]: r for r in csv.DictReader(a.out.open())} if a.out.exists() else {}
    texts = {p: p.read_text(errors="replace") for p in sorted((ROOT / "capri_mod").rglob("*.py"))
             if "tests" not in p.parts}
    cols = ["equation", "models", "planned_module", "in_gd2030_step", "condition_in_model_list", "capri_definition",
            "model_files_citing", *HAND]
    n_step = 0
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for n in eqs:
            k = n.lower()
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9])", re.I)
            hits = sorted(((len(pat.findall(t)), p.relative_to(ROOT).as_posix()) for p, t in texts.items()
                           if pat.search(t)), key=lambda h: (-h[0], h[1]))
            d = defs.get(k, ["not found"])
            step = k in gcond and active(gcond[k], sw)
            n_step += step
            row = {"equation": n, "models": "; ".join(models[k]), "planned_module": module_of(d[0]),
                   "in_gd2030_step": "yes" if step else "no",
                   "condition_in_model_list": gcond.get(k, "(m_netTrade only)"),
                   "capri_definition": "; ".join(d), "model_files_citing": "; ".join(f"{p} ({c})" for c, p in hits)}
            row.update({h: old.get(n, {}).get(h, "") for h in HAND})
            w.writerow(row)
    print(f"{len(eqs)} equations ({len(set(x.lower() for x, _ in glob))} in m_globMarket, "
          f"{len(set(x.lower() for x, _ in bev))} of them in m_bevFunctionsMarket; "
          f"{len(set(x.lower() for x, _ in net))} in m_netTrade), {n_step} in the Green Deal step -> {a.out}")


if __name__ == "__main__":
    main()

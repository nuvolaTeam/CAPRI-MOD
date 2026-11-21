#!/usr/bin/env python3
"""Inventory of CAPRI's supply-model equations against CAPRI-mod's code (the plan of refactor/supply-equations).

One row per equation of CAPRI's simulation model m_capModQ (star 3.0): the equations listed in
supply/supply_model_e_list_linear.gms (with supply_model_e_list_FOCfert.gms) and supply_model_e_list_quatratic.gms,
with the $if condition each is listed under. For each:

- capri_group: CAPRI's own grouping, the comment header of its declaration (supply/supply_model.gms l. 181-511);
- planned_module: the module of capri_mod/supply/equations/supply_model/ it goes to, by the block of
  supply_model.gms its definition is in (the file's own banners, BLOCKS below);
- in_gd2030_step: whether the condition holds in CAPRI's 2030 Green Deal step, with the switches of
  docs/dev/supply_equations_gd_switches.csv (each with its source);
- capri_definition: file and lines of each definition found in the star 3.0 tree (two where CAPRI has alternatives);
- model_files_citing: the files of capri_mod (tests apart) naming the equation, with the count (a first pointer, not
  proof that the equation is ported: many rows of the regional model do not carry CAPRI's name);
- status, model_location, notes: written by hand, block by block, and kept when the inventory is rebuilt.

    python tools/refactor/supply_equations_inventory.py GAMS_DIR [--out docs/dev/supply_equations_inventory.csv]

GAMS_DIR is CAPRI's gams folder (the one holding supply/supply_model.gms).
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAND = ("status", "model_location", "notes")

# the blocks of supply/supply_model.gms (first line, last line, module), from the file's banners (CAPRI star 3.0, the
# copy of the project lead's runs: 5,557 lines; until 20 November 2026 these were the July 2026 release's lines, 5,631);
# GHG_Mit_Cost_ and its check parts (l. 4984-5283, in the objective block) go to mitigation.py, with the options'
# constraints
BLOCKS = [(512, 832, "feeding"), (833, 861, "young_animals"), (862, 1271, "nutrients"), (1272, 1489, "n_surplus"),
          (1490, 1782, "inner_fert"), (1783, 1878, "n_surplus"), (1879, 2015, "premiums"), (2016, 2213, "bfp"),
          (2214, 2357, "set_aside"), (2358, 2516, "land"), (2517, 2637, "water"), (2638, 3043, "lulucf"),
          (3044, 3188, "methane"), (3189, 3454, "n_flow"), (3455, 3616, "air_water"), (3617, 3949, "n2o"),
          (3950, 3998, "gwp"), (3999, 4112, "lulucf"), (4113, 4350, "mitigation"), (4351, 4441, "pesticides"),
          (4442, 4542, "fert_limits"), (4543, 4615, "markets"), (4616, 4983, "objective"),
          (4984, 5283, "mitigation"), (5284, 5359, "objective"), (5360, 5424, "sugar")]


def model_list(G: Path, path: str):
    """(equation, condition) in the order of CAPRI's list file, includes followed."""
    rows, stack, skip = [], [], False
    for raw in (G / path).read_text(errors="replace").splitlines():
        line = raw.strip()
        if re.match(r"\$ontext", line, re.I):
            skip = True
        if re.match(r"\$offtext", line, re.I):
            skip = False
            continue
        if skip or not line or line.startswith("*"):
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
        if re.match(r"\$include", line, re.I):
            inc = re.search(r"'([^']+)'", line).group(1)
            rows += [(n, " & ".join([c for c in stack + [c2] if c])) for n, c2 in model_list(G, inc)]
            continue
        cond = ""
        m = re.match(r"\$\s*(ifi|ife|if)(\.\w+)?\s+(not\s+)?(\S+\s*==\s*\S+|%\w+%\S*\s*>\s*\S+|\S+==\S+)\s+(.*)",
                     line, re.I)
        if m:
            cond = (m.group(3) or "") + m.group(4)
            line = m.group(5)
        elif line.startswith("$"):
            continue
        for name in re.split(r"[,\s]+", line):
            if re.match(r"^[A-Za-z]\w*$", name) and not name.lower().startswith("m_"):
                rows.append((name, " & ".join([c for c in stack + [cond] if c])))
    return rows


def capri_groups(G: Path) -> dict:
    sm = (G / "supply/supply_model.gms").read_text(errors="replace").splitlines()
    group, groups = "objective", {}
    for i in range(180, 512):                         # the declarations, l. 181-511 (star 3.0)
        line = sm[i]
        h = re.match(r"^\*\s*-{2,}\s*(.+?)\s*$", line) or re.match(r"^\*-{2,}(.+?)\s*$", line)
        if h and len(h.group(1)) > 3 and "mihaly" not in h.group(1):
            group = h.group(1).strip(" -")
            continue
        m = re.match(r"^\s*(?:\$\S+\s+\S+\s+)?([A-Za-z]\w*)", line)
        if m and not line.lstrip().startswith("*"):
            groups.setdefault(m.group(1).lower(), group)
    for name in ("e_normalizefertdist", "e_fertdistpartial", "e_focfertdist", "e_fertdistpartialregu",
                 "e_fertdistregumax", "e_fertdistperha"):                       # declared at l. 1516-1521
        groups[name] = "inner fertiliser model"
    return groups


def definitions(G: Path, names: set) -> dict:
    """Definitions 'name(domain) $ cond ..' in all .gms files: file:first-last."""
    defs = {}
    for f in sorted(G.rglob("*.gms")):
        lines = f.read_text(errors="replace").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("*"):
                continue
            m = re.match(r"^\s*([A-Za-z]\w*)\s*(\(|\$|\.\.|%|$)", line)
            if not m or m.group(1).lower() not in names:
                continue
            j, text = i, ""
            while j < len(lines) and j < i + 12:
                if not lines[j].startswith("*"):
                    text += " " + lines[j]
                if ".." in text or ";" in text:
                    break
                j += 1
            k = text.find("..")
            # a definition, not an assignment (name.lo = ...), a listing or a statement ended before '..'
            if k < 0 or ";" in text[:k] or re.match(r"\s*\w+\s*\.(?!\.)", text) \
                    or re.search(r"(?<![<>=!])=(?!=)", text[:k]):
                continue
            e = j
            while e < len(lines) and not re.search(r";\s*(\*.*)?$", lines[e]):
                e += 1
            defs.setdefault(m.group(1).lower(), []).append(f"{f.relative_to(G).as_posix()}:{i + 1}-{e + 1}")
    return defs


def active(cond: str, sw: dict) -> bool:
    for part in [p.strip() for p in cond.split(" & ") if p.strip()]:
        neg = False
        m = re.match(r"NOT\((.*)\)$", part)
        if m:
            neg, part = True, m.group(1)
        if part.lower().startswith("not "):
            neg, part = not neg, part[4:]
        sub = re.sub(r"%(\w+)%", lambda mm: sw.get(mm.group(1).lower(), "OFF"), part)   # unset switches are off
        if ">" in sub:
            a, b = sub.split(">")
            val = float(a) > float(b)
        else:
            a, b = [x.strip() for x in sub.split("==")]
            val = a.lower() == b.lower()
        if val == neg:
            return False
    return True


def module_of(defn: str) -> str:
    m = re.match(r"supply/supply_model\.gms:(\d+)", defn)
    if not m:
        return "outside supply_model.gms"
    ln = int(m.group(1))
    return next((nm + ".py" for a, b, nm in BLOCKS if a <= ln <= b), "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/dev/supply_equations_inventory.csv")
    ap.add_argument("--switches", type=Path, default=ROOT / "docs/dev/supply_equations_gd_switches.csv")
    a = ap.parse_args()
    G = a.gams_dir
    sw = {r["switch"].lower(): r["value"] for r in csv.DictReader(a.switches.open())}
    eqs, seen = [], set()
    for n, c in model_list(G, "supply/supply_model_e_list_linear.gms") + \
            model_list(G, "supply/supply_model_e_list_quatratic.gms"):
        if n.lower() not in seen and n.lower() != "m_capmod":
            seen.add(n.lower())
            eqs.append((n, c))
    groups, defs = capri_groups(G), definitions(G, seen)
    old = {r["equation"]: r for r in csv.DictReader(a.out.open())} if a.out.exists() else {}
    texts = {p: p.read_text(errors="replace") for p in sorted((ROOT / "capri_mod").rglob("*.py"))
             if "tests" not in p.parts}
    cols = ["equation", "capri_group", "planned_module", "in_gd2030_step", "condition_in_model_list",
            "capri_definition", "model_files_citing", *HAND]
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for n, c in eqs:
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9])", re.I)
            hits = sorted(((len(pat.findall(t)), p.relative_to(ROOT).as_posix()) for p, t in texts.items()
                           if pat.search(t)), key=lambda h: (-h[0], h[1]))
            d = defs.get(n.lower(), ["not found"])
            row = {"equation": n, "capri_group": groups.get(n.lower(), ""), "planned_module": module_of(d[0]),
                   "in_gd2030_step": "yes" if active(c, sw) else "no", "condition_in_model_list": c,
                   "capri_definition": "; ".join(d), "model_files_citing": "; ".join(f"{p} ({k})" for k, p in hits)}
            row.update({h: old.get(n, {}).get(h, "") for h in HAND})
            w.writerow(row)
    print(f"{len(eqs)} equations, {sum(1 for n, c in eqs if active(c, sw))} in the Green Deal step -> {a.out}")


if __name__ == "__main__":
    main()

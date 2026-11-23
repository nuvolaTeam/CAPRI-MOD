#!/usr/bin/env python3
"""Inventory of the CAPRI statements the model's code ports or cites, against CAPRI star 3.0 (the refactor's third
phase, block A0; docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md).

The model's code (capri_mod/, outside its equations/ packages, pipeline/ and tests/) cites CAPRI's GAMS files in its
docstrings and comments. Each citation is read with the lines it gives ("file.gms l. a-b", "file.gms:a") or, without
lines, the CAPRI symbols it names that the file assigns; it is resolved to the statement blocks of the star 3.0 file
there (one assignment, or the consecutive assignments to one symbol: a value and its fallback, the branches of a $if).
One row per statement block cited, and one per file cited without a block (its citing places merged):

- capri_file, lines: the CAPRI file and the block's lines (star 3.0); "(file)" for a citation without a block;
- symbol: the assigned symbol (with its attribute, v_x.fx), or the equation, declaration or control statement;
- kind: assignment, equation, declaration, model, solve, option, control, other (the statement's own kind);
  "file" for a file-level citation;
- cited_by: the model's places citing it (module:line function), and how each cites it (lines, symbol, file);
- in_style: the functions of the equations/ packages that already quote the block (file and overlapping lines);
- block: the phase's block of the citing modules (A1-A5, by the plan's section 3; "out" for pipeline/);
- locked: the citing modules the main line is changing now (the plan's section 3: left alone until A5);
- status, takes, function, notes: written by hand (kept when the inventory is rebuilt; takes: the block that moves
  a row to move); the tool proposes a status in
  status_proposed: "equation (phases 1-2)", "already in the style", "to move", "citation for context only", "lines
  hold no statement", "file not in star 3.0". The reviewed statuses add "not ported: <reason>", "citation wrong:
  <what>" and "data read: <the CSV and its builder>" (a CAPRI literal value or table the model reads as data, out of
  scope with the builders' rework; the project lead, 23 November 2026).

    python tools/refactor/assignments_inventory.py GAMS_DIR [--out docs/dev/assignments_inventory.csv]

GAMS_DIR is CAPRI's gams folder (star 3.0: supply/supply_model.gms 5,557 lines, arm/market_model.gms 4,607).
"""
from __future__ import annotations

import argparse
import ast
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAND = ("status", "takes", "function", "notes")

# the plan's section 3: the blocks by module (capri_mod/ relative paths); the main line's files left alone until A5
BLOCK_OF = {
    "A1": ["environmental/ghg.py", "environmental/environmental_module.py", "environmental/nitrogen.py",
           "environmental/phosphorus.py", "environmental/p_balance.py", "environmental/luc.py",
           "environmental/ammonia.py", "environmental/biodiversity.py", "supply/n_leaching.py"],
    "A2": ["policy/mtr.py", "policy/bps.py", "policy/cap14_premiums.py", "policy/declared.py", "policy/premium_cut.py",
           "policy/premium_response.py", "policy/premiums.py", "policy/rd.py", "policy/nordic_aid.py",
           "policy/norway.py", "policy/policy_module.py", "supply/entitlements.py"],
    "A3": ["projection/prices.py", "projection/projection_module.py", "projection/trajectory.py",
           "projection/reconcile.py", "projection/captrd_import.py"],
    "A4": ["coupling/price_step.py", "coupling/hessian.py", "coupling/bridge.py", "coupling/young_animals.py",
           "coupling/feed.py", "coupling/manure.py", "coupling/reporting.py", "market/welfare.py",
           "market/market_bounds.py", "market/supply.py", "market/demand.py", "market/feed.py", "market/bilateral.py"],
    "A5": ["policy/greendeal.py", "supply/policy.py", "policy/endotech.py", "fert/inner_fert_dist.py", "fert/npk.py",
           "supply/abatement.py", "supply/supply_module.py", "supply/livestock.py", "supply/land.py",
           "supply/fertilisation.py", "feed/ration.py", "data/loaders.py", "model.py"],
}
LOCKED = {"supply/fertilisation.py", "supply/abatement.py", "supply/capri_regional_nlp.py",
          "supply/equations/ghgmiti.py", "fert/npk.py", "policy/greendeal.py", "supply/policy.py",
          "supply/livestock.py"}
# modules outside the plan's table, assigned by A0 (by what they port: the CAPRI files they cite)
A0_BLOCK = {"income/income_module.py": "A1", "water/water_module.py": "A1", "supply/ghg_tax.py": "A1",
            "supply/n_cascade.py": "A1", "utils/capri_stop.py": "A4", "supply/capri_pmp.py": "A4",
            "scenarios/definition.py": "A2", "runlog.py": "context", "io_results.py": "context", "units.py": "context",
            "scenarios/__main__.py": "context", "scenarios/scenarios.py": "context", "biofuel/__init__.py": "A4"}
# the other modules outside the plan's table: their block by area
AREA_BLOCK = [("environmental/", "A1"), ("policy/", "A2"), ("projection/", "A3"), ("coupling/", "A4"),
              ("market/", "A4"), ("supply/", "A5"), ("fert/", "A5"), ("feed/", "A5"), ("data/", "A5")]

CIT = re.compile(r"(?<![\w/\\.])((?:[A-Za-z_][\w\-]*[/\\])*[A-Za-z_][\w\-]*\.gms)\b", re.I)
LINES = re.compile(r"^\s*(?:[,;]?\s*)?(?:\(\s*)?(?:l\.|lines?)\s*(\d+(?:\s*[-–]\s*\d+)?(?:\s*(?:,|and)\s*\d+"
                   r"(?:\s*[-–]\s*\d+)?)*)|^:(\d+(?:-\d+)?)", re.I)
IDENT = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\b")
DECL = ("parameter", "parameters", "set", "sets", "scalar", "scalars", "table", "variable", "variables",
        "positive", "negative", "free", "binary", "integer", "equation", "equations", "alias", "acronym",
        "acronyms", "file", "singleton")
CONTROL = ("loop", "if", "while", "for", "repeat", "else", "elseif")


# --------------------------------------------------------------------------- CAPRI's statements
def _strip_gms(text: str) -> list:
    """(line number, code text) of a GAMS file's code lines: comment lines (* in column 1), $ontext blocks and
    end-of-line comments (!! ...) dropped; $ control lines kept as their own statements."""
    out, skip = [], False
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.rstrip()
        st = s.strip()
        if re.match(r"\$ontext", st, re.I):
            skip = True
            continue
        if re.match(r"\$offtext", st, re.I):
            skip = False
            continue
        if skip or not st or s.startswith("*"):
            continue
        out.append((i, s.split("!!")[0]))
    return out


def _lhs_symbol(text: str):
    """(kind, symbol) of one statement's text."""
    t = text.strip()
    if t.startswith("$"):
        return "control", t.split()[0]
    w = re.match(r"([A-Za-z_]\w*)", t)
    if not w:
        return "other", ""
    first = w.group(1).lower()
    if first in DECL:
        return "declaration", (IDENT.findall(t[w.end():]) or [""])[0]
    if first == "model":
        return "model", (IDENT.findall(t[w.end():]) or [""])[0]
    if first == "solve":
        return "solve", (IDENT.findall(t[w.end():]) or [""])[0]
    if first in ("option", "options"):
        return "option", t[w.end():].strip()[:40]
    if first in ("display", "abort", "put", "putclose", "execute_unload", "execute_load", "execute"):
        return "other", first
    if first in CONTROL:
        # the first statement inside the control: after the control's condition or domain, up to its first comma
        depth, k = 0, w.end()
        while k < len(t):
            if t[k] == "(":
                depth += 1
            elif t[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            elif t[k] == "," and depth == 1:
                inner = t[k + 1:]
                kd, sy = _lhs_symbol(inner)
                return (kd, sy) if kd in ("assignment", "equation") else ("control", first)
            k += 1
        return "control", first
    # an equation: name(domain) $ cond .. ; an assignment: target(...) $ cond = ...
    if re.search(r"\.\.(?!\.)", t.split("=")[0]) and not re.match(r"[A-Za-z_]\w*\.[A-Za-z]", t):
        return "equation", w.group(1)
    m = re.search(r"(?<![=<>!])=(?![=eElLgGnN]?=)(?![eElLgGnN]=)", t)
    if m:
        lhs = t[:m.start()]
        a = re.match(r"\s*([A-Za-z_]\w*)(\.(?:l|lo|up|fx|m|scale|prior|range)\b)?", lhs, re.I)
        if a:
            key = re.search(r"\(\s*[^)]*?[\"']([A-Za-z][\w\-]*)[\"']", lhs[a.end():a.end() + 200])
            return "assignment", a.group(1) + (a.group(2) or "") + (f'("{key.group(1)}")' if key else "")
    return "other", first


def statements(G: Path, rel: str) -> list:
    """[(first line, last line, kind, symbol)] of a star 3.0 file's statements, in order (a statement ends at ';' or
    is a $ control line)."""
    out, cur, start = [], "", None
    for ln, s in _strip_gms((G / rel).read_text(errors="replace")):
        st = s.strip()
        if st.startswith("$") and not cur:
            out.append((ln, ln, "control", st.split()[0]))
            continue
        parts = re.split(r";", s)
        for j, part in enumerate(parts):
            if part.strip():
                if start is None:
                    start = ln
                cur += " " + part
            if j < len(parts) - 1:
                if cur.strip():
                    out.append((start, ln, *_lhs_symbol(cur)))
                cur, start = "", None
    if cur.strip():
        out.append((start, start, *_lhs_symbol(cur)))
    return out


def _base(sym: str) -> str:
    """A block's identity: the symbol without its attribute, with its key (EMISCALC("N2OSYN")), lower case."""
    m = re.match(r"([A-Za-z_]\w*)(?:\.\w+)?(\(.*\))?$", sym)
    if not m:
        return sym.lower()
    key = m.group(2) or ""
    # a region's code is not a statement's identity (a table of values per region is one block): CAPRI's regional
    # units (ES130000), member states (DE000000), market regions (EU_WEST, USA ...) are dropped from the key
    if re.match(r'\("(?:[A-Z]{2}\d{6}|[A-Z]{2}0{6}|[A-Z]{2}\d{2,4})"\)$', key):
        key = ""
    return (m.group(1) + key).lower()


def _names(sym: str) -> set:
    """The names a citation may use for a block: its symbol and its key."""
    m = re.match(r"([A-Za-z_]\w*)(?:\.\w+)?(?:\(\"(.*)\"\))?$", sym)
    return {x.lower() for x in (m.groups() if m else (sym,)) if x and len(x) >= 3}


def sections(G: Path, rel: str) -> dict:
    """{number: (first line, last line, item)} of a file's numbered comment headers ('* (16) CO2LIME ...'), each up to
    the next; item the header's first upper-case name (the statements of that item), or ''."""
    lines = (G / rel).read_text(errors="replace").splitlines()
    heads = [(int(m.group(1)), i + 1, m.group(2) or "") for i, ln in enumerate(lines)
             for m in [re.match(r"\*\s*\((\d+)\)\s*([A-Z][A-Z0-9]{2,})?", ln)] if m]
    return {n: (a, (heads[k + 1][1] - 1) if k + 1 < len(heads) else len(lines), it)
            for k, (n, a, it) in enumerate(heads)}


def blocks(stmts: list) -> list:
    """The statement blocks: consecutive assignments to one symbol (its attribute aside) merged; each other
    statement a block of its own. [(first, last, kind, symbol)]."""
    out = []
    for a, b, k, s in stmts:
        base = _base(s)
        sym = base.split("(")[0]
        # one block: the same symbol and key (a value and its fallback), or the same symbol on the next line (a table
        # of values written one key per line)
        if out and k == "assignment" and out[-1][2] == "assignment" and (
                _base(out[-1][3]) == base or (_base(out[-1][3]).split("(")[0] == sym and a <= out[-1][1] + 1)):
            out[-1] = (out[-1][0], b, k, out[-1][3])
            continue
        out.append((a, b, k, s))
    return out


# --------------------------------------------------------------------------- the model's citations
def _module_functions(path: Path) -> list:
    """[(first line, last line, qualified name)] of the module's functions and classes."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    out = []

    def walk(node, prefix=""):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = prefix + n.name
                out.append((n.lineno, n.end_lineno or n.lineno, q))
                walk(n, q + ".")
    walk(tree)
    return out


def _holder(funcs: list, ln: int) -> str:
    best = None
    for a, b, q in funcs:
        if a <= ln <= b and (best is None or a >= best[0]):
            best = (a, q)
    return best[1] if best else "(module)"


def _ranges(spec: str) -> list:
    out = []
    for part in re.split(r"\s*(?:,|and)\s*", spec):
        m = re.match(r"(\d+)(?:\s*[-–]\s*(\d+))?", part)
        if m:
            a = int(m.group(1))
            b = int(m.group(2) or a)
            if b >= a:
                out.append((a, b))
    return out


def _resolve(G: Path, name: str, index: dict) -> list:
    """The star 3.0 files a cited name can be: the relative path if it exists, else every file of that base name."""
    rel = name.replace("\\", "/")
    for cand in (rel, rel.lower()):
        if (G / cand).exists():
            return [cand]
    base = rel.split("/")[-1].lower()
    hits = index.get(base, [])
    tail = rel.lower()
    exact = [h for h in hits if h.lower().endswith(tail)]
    return exact or hits


def block_of(rel: str) -> str:
    for b, mods in BLOCK_OF.items():
        if rel in mods:
            return b
    if rel in A0_BLOCK:
        return A0_BLOCK[rel]
    if rel.startswith("pipeline/"):
        return "out"
    for prefix, b in AREA_BLOCK:
        if rel.startswith(prefix):
            return b
    return "A0 decides"


def in_style(G: Path) -> dict:
    """{capri file: [(first, last, 'module.function')]} of the quotes in the equations/ packages ("CAPRI's GAMS ...
    (file l. a-b)")."""
    out = defaultdict(list)
    pat = re.compile(r"CAPRI's GAMS[^(\n]*\(([\w/\\\-.]+\.gms)\s+l\.\s*(\d+)(?:\s*-\s*(\d+))?", re.I)
    for p in sorted((ROOT / "capri_mod").rglob("equations/**/*.py")):
        funcs = _module_functions(p)
        for i, line in enumerate(p.read_text().splitlines(), 1):
            for m in pat.finditer(line):
                a = int(m.group(2))
                b = int(m.group(3) or a)
                out[m.group(1).replace("\\", "/").lower()].append(
                    (a, b, f"{p.relative_to(ROOT / 'capri_mod').as_posix()}:{_holder(funcs, i)}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/dev/assignments_inventory.csv")
    a = ap.parse_args()
    G = a.gams_dir
    index = defaultdict(list)
    for f in G.rglob("*.gms"):
        index[f.name.lower()].append(f.relative_to(G).as_posix())
    cache, styled = {}, in_style(G)

    def blks(rel):
        if rel not in cache:
            cache[rel] = blocks(statements(G, rel))
        return cache[rel]

    rows = {}                                   # (file, first, last) -> row

    def row(rel, a_, b_, kind, sym):
        k = (rel, a_, b_)
        if k not in rows:
            rows[k] = {"capri_file": rel, "lines": f"{a_}-{b_}" if a_ else "(file)", "symbol": sym, "kind": kind,
                       "cited_by": [], "blocks": set(), "locked": set()}
        return rows[k]

    mods = sorted(p for p in (ROOT / "capri_mod").rglob("*.py")
                  if not any(x in p.relative_to(ROOT / "capri_mod").parts for x in ("equations", "pipeline", "tests")))
    n_cit = 0
    for p in mods:
        rel_m = p.relative_to(ROOT / "capri_mod").as_posix()
        funcs = _module_functions(p)
        lines = p.read_text().splitlines()
        for i, line in enumerate(lines, 1):
            for m in CIT.finditer(line):
                n_cit += 1
                where = f"{rel_m}:{i} {_holder(funcs, i)}"
                files = _resolve(G, m.group(1), index)
                after = line[m.end():] + " " + (lines[i] if i < len(lines) else "")
                lm = LINES.match(after)
                if not files:
                    r = row(m.group(1), 0, 0, "file not in star 3.0", "")
                    r["cited_by"].append(where + " (file)")
                    r["blocks"].add(block_of(rel_m))
                    if rel_m in LOCKED:
                        r["locked"].add(rel_m)
                    continue
                rel = files[0] if len(files) == 1 else files[0]
                bl = blks(rel)
                hit = []
                sm = re.match(r"\s*\((\d+)\)", line[m.end():])
                if not lm and sm and int(sm.group(1)) in sections(G, rel):
                    x, y, item = sections(G, rel)[int(sm.group(1))]
                    hit = [blk for blk in bl if blk[0] <= y and blk[1] >= x and blk[2] in ("assignment", "equation")]
                    if item:
                        # the item's own statements (the header's name, or a name that starts with it: CO2LIME, CO2LIM)
                        hit = [blk for blk in hit if any(item.lower().startswith(nm) or nm.startswith(item.lower())
                                                         for nm in _names(blk[3]))] or hit[:1]
                    how = "section"
                elif lm:
                    for x, y in _ranges(lm.group(1) or lm.group(2)):
                        hit += [blk for blk in bl if blk[0] <= y and blk[1] >= x and blk[2] != "control"]
                    how = "lines"
                    if not hit:
                        r = row(rel, *(_ranges(lm.group(1) or lm.group(2))[0]), "lines hold no statement", "")
                        r["cited_by"].append(where + " (lines)")
                        r["blocks"].add(block_of(rel_m))
                        if rel_m in LOCKED:
                            r["locked"].add(rel_m)
                        continue
                else:
                    names = {w.lower() for w in IDENT.findall(line)}
                    hit = [blk for blk in bl if blk[2] in ("assignment", "equation") and blk[3]
                           and _names(blk[3]) & names]
                    how = "symbol"
                if not hit:
                    hit, how = [(0, 0, "file", "")], "file"
                for x, y, kd, sy in dict.fromkeys(hit):
                    r = row(rel, x, y, kd, sy)
                    r["cited_by"].append(f"{where} ({how}{', ambiguous: ' + str(len(files)) if len(files) > 1 else ''})")
                    r["blocks"].add(block_of(rel_m))
                    if rel_m in LOCKED:
                        r["locked"].add(rel_m)
    old = {}
    if a.out.exists():
        for r in csv.DictReader(a.out.open()):
            old[(r["capri_file"], r["lines"], r["symbol"])] = r
    cols = ["capri_file", "lines", "symbol", "kind", "status_proposed", "block", "locked", "in_style", "cited_by", *HAND]
    out_rows = []
    for (rel, x, y), r in sorted(rows.items()):
        st = [q for (p_, q_, q) in styled.get(rel.lower(), []) if x and p_ <= y and q_ >= x]
        kind = r["kind"]
        if kind == "file not in star 3.0":
            prop = "file not in star 3.0"
        elif kind == "lines hold no statement":
            prop = "lines hold no statement"
        elif st:
            prop = "already in the style"
        elif kind == "equation":
            prop = "equation (phases 1-2)"
        elif kind == "assignment":
            prop = "to move"
        else:
            prop = "citation for context only"
        o = {"capri_file": rel, "lines": r["lines"], "symbol": r["symbol"], "kind": kind, "status_proposed": prop,
             "block": "; ".join(sorted(r["blocks"])), "locked": "; ".join(sorted(r["locked"])),
             "in_style": "; ".join(dict.fromkeys(st)), "cited_by": "; ".join(dict.fromkeys(r["cited_by"]))}
        o.update({h: old.get((rel, r["lines"], r["symbol"]), {}).get(h, "") for h in HAND})
        out_rows.append(o)
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    from collections import Counter
    print(f"{n_cit} citations in {len(mods)} modules -> {len(out_rows)} rows: "
          f"{dict(Counter(r['status_proposed'] for r in out_rows))} -> {a.out}")


if __name__ == "__main__":
    main()

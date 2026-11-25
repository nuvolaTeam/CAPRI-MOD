#!/usr/bin/env python3
"""Check the CAPRI line citations next to an equation's name against a CAPRI copy (the equation refactor's citation
check).

A citation such as "catcMiti_ (l. 2005-2010)", "e_BIOFIX: l. 1438-1461" or "GHG_Mit_Cost_ (supply/supply_model.gms
l. 4984-5116)" must point at that equation in the copy given, which must be CAPRI star 3.0 (until 20 November 2026 the
refactor and some main-line entries cited CAPRI's July 2026 release: docs/dev/EQUATION_REFACTOR_HANDOFF.md, the
correction at its top). The cited range must hold one of the equation's definitions ("NAME(...) $ ... ..") or start
inside its body (between its definition and the next equation's). Only citations whose file is a GAMS file with
equation definitions are checked: the file named in the citation, else the last .gms file named earlier on the line,
else the module's default (supply_model/ -> supply/supply_model.gms, market/equations/ -> arm/market_model.gms); a
citation right after another kind of file (foo.py l. 12) is skipped.

Statement blocks (the third phase, docs/dev/ASSIGNMENTS_REFACTOR_PLAN.md section 4): the "CAPRI's GAMS (file l. a-b)"
header in the docstring of a function named after an assigned symbol (p_animReqCopy_NEA_share: the longest prefix of
the name the file assigns, p_animReqCopy) must hold an assignment to that symbol (within 2 lines). The statements are read with
tools/refactor/assignments_inventory.py's parser; a name the file neither defines nor assigns is not checked.

    python tools/refactor/check_gams_citations.py GAMS_DIR [FILES...]

Without FILES: capri_mod/, docs/ (except docs/dev/EQUATION_REFACTOR_PLAN_REST.md and EQUATION_REFACTOR_BRIEF.md, kept
with the release's lines as written), tools/ and CHANGELOG.md. Exit status 1 if a citation fails.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("_asg_inv", Path(__file__).with_name("assignments_inventory.py"))
_asg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_asg)
HEADER = re.compile(r"CAPRI's GAMS[^(\n]*\(([A-Za-z0-9_./]+\.gms)\s+l\.\s*(\d+)(?:\s*-\s*(\d+))?\)")
DEFAULTS = {"supply/equations/supply_model/": "supply/supply_model.gms", "market/equations/": "arm/market_model.gms"}
KEPT_AS_WRITTEN = {"docs/dev/EQUATION_REFACTOR_PLAN_REST.md", "docs/dev/EQUATION_REFACTOR_BRIEF.md"}
FILE_RE = re.compile(r"([A-Za-z0-9_./]+\.gms)")
CIT = re.compile(r"(?:(?P<f>[A-Za-z0-9_./]+\.gms)(?::|,? l\. ))?(?:(?<=\.gms:)|(?<=\.gms l\. )|(?<=\.gms, l\. )|"
                 r"(?<=\bl\. ))(?P<n>\d{1,5})(?:-(?P<m>\d{1,5}))?")
# the equation's name right before the citation: NAME, NAME(...), NAME_ (l. or NAME: l.
NAMED = re.compile(r"([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*|e_[A-Za-z0-9_]+)(\([^()]{0,40}\))?\s*[(:,]?\s*"
                   r"(?:\([^()]{0,30}\.gms\s*)?$")
NONGAMS = re.compile(r"[A-Za-z0-9_]\.(py|csv|md|toml|txt|json|parquet|gdx)[`'\")]?,?\s*(l\.\s*)?$")


class Defs:
    """Equation definitions of the copy's files: name -> definition lines, and the equation each line belongs to."""

    def __init__(self, root: Path):
        self.root = root
        self.cache: dict[str, tuple[dict, list] | None] = {}
        self.acache: dict[str, dict] = {}

    def assigned(self, rel: str) -> dict:
        """symbol (lower case, attribute and key aside) -> [(first line, last line)] of the file's assignments."""
        if rel not in self.acache:
            out: dict = {}
            if (self.root / rel).exists():
                for a, b, kind, sym in _asg.statements(self.root, rel):
                    if kind == "assignment" and sym:
                        out.setdefault(re.split(r"[.(]", sym)[0].lower(), []).append((a, b))
            self.acache[rel] = out
        return self.acache[rel]

    def resolve(self, name: str) -> str | None:
        name = name.strip("`'\"(")
        if (self.root / name).exists():
            return name
        hits = sorted({p.relative_to(self.root).as_posix() for p in self.root.rglob(Path(name).name)})
        return hits[0] if len(hits) == 1 else None

    def of(self, rel: str):
        """(name -> [(definition line, last line)], None): an equation runs from its definition to the line whose code
        ends with ';' (GAMS comment lines and inline comments aside)."""
        if rel not in self.cache:
            p = self.root / rel
            if not p.exists():
                self.cache[rel] = None
                return None
            lines = p.read_text(errors="replace").splitlines()
            defs = {}
            for i, line in enumerate(lines, 1):
                m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?[^*]*\.\.", line)
                if not m or line.lstrip().startswith("*"):
                    continue
                end = i
                for j in range(i, min(len(lines), i + 600) + 1):
                    code = lines[j - 1]
                    if code.startswith("*"):                 # a GAMS comment: '*' in the first column only
                        continue
                    if code.rstrip().endswith(";"):
                        end = j
                        break
                defs.setdefault(m.group(1).lower(), []).append((i, end))
            self.cache[rel] = (defs, None) if defs else None
        return self.cache[rel]


def _holds(spans, n, hi) -> bool:
    return any(n - 2 <= a <= hi + 2 or (a <= n and hi <= b + 1) for a, b in spans)


def check_text(rel: str, text: str, D: Defs) -> list[str]:
    out = []
    dflt = next((v for k, v in DEFAULTS.items() if k in rel), None)
    lines = text.splitlines()
    func = None
    for ln, line in enumerate(lines, 1):
        fm = re.match(r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
        if fm:
            func = fm.group(1)
        hm = HEADER.search(line)
        if hm and func and rel.endswith(".py"):
            rp = D.resolve(hm.group(1))
            asg = D.assigned(rp) if rp else {}
            parts = func.split("_")
            sym = next((s_ for s_ in ("_".join(parts[:k]).lower() for k in range(len(parts), 0, -1)) if s_ in asg), None)
            if sym:
                n, hi = int(hm.group(2)), int(hm.group(3) or hm.group(2))
                if not _holds(asg[sym], n, hi):
                    out.append(f"{rel}:{ln}: {func}'s quote ({hm.group(1)} l. {n}-{hi}) does not hold an assignment "
                               f"to {sym} (assigned at l. {', '.join(f'{a}-{b}' for a, b in asg[sym][:6])})")
        prev = lines[ln - 2] if ln > 1 else ""
        for mm in CIT.finditer(line):
            pre = line[:mm.start()]
            wrapped = (prev.strip() + " " + pre) if prev.strip() else pre        # prose wraps: the name may be above
            if not mm.group("f") and NONGAMS.search(pre[-40:]):
                continue
            named = NAMED.search(pre[-90:].rstrip(" (l."))
            if not named:
                continue
            eqn = named.group(1).lower()
            before = FILE_RE.findall(pre)
            fname = mm.group("f") or (before[-1] if before else dflt)
            rp = D.resolve(fname) if fname else None
            info = D.of(rp) if rp else None
            if not info or eqn not in info[0]:
                continue
            defs = info[0]
            n = int(mm.group("n"))
            hi = int(mm.group("m") or n)
            # any equation of the file named just before the citation may be the one cited (a list of names, or two
            # names followed by their two ranges); the range must hold its definition line or lie within the equation
            near = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*|e_[A-Za-z0-9_]+", wrapped[-160:])}
            near = [e for e in near | {eqn} if e in defs]
            if any(n - 2 <= d <= hi + 2 or (d <= n and hi <= end + 1) for e in near for d, end in defs[e]):
                continue
            out.append(f"{rel}:{ln}: {mm.group(0)} does not hold {named.group(1)} in {rp} (defined at l. "
                       f"{', '.join(f'{d}-{e}' for d, e in defs[eqn])})")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("files", nargs="*", type=Path)
    a = ap.parse_args()
    D = Defs(a.gams_dir)
    if a.files:
        files = [f if f.is_absolute() else ROOT / f for f in a.files]
    else:
        files = [p for d in ("capri_mod", "docs", "tools") for p in (ROOT / d).rglob("*")
                 if p.suffix in (".py", ".md", ".csv", ".toml") and "__pycache__" not in p.parts]
        files += [ROOT / "CHANGELOG.md"]
    problems = []
    for f in sorted(files):
        rel = f.relative_to(ROOT).as_posix() if ROOT in f.parents else str(f)
        if rel in KEPT_AS_WRITTEN:
            continue
        problems += check_text(rel, f.read_text(errors="replace"), D)
    for p in problems:
        print(p)
    print(f"{len(files)} files checked, {len(problems)} citations that do not hold their equation")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

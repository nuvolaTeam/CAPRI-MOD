#!/usr/bin/env python3
"""Check the CAPRI GAMS text quoted in the code's docstrings against a CAPRI copy (the equation refactor's quote check).

The equation refactor quotes each CAPRI equation it ports in the docstring of the function that writes it (the project
lead's decision of 19 November 2026). This tool checks every quote against the CAPRI copy given, which must be CAPRI
star 3.0, the code of the project lead's runs (until 20 November 2026 the refactor read CAPRI's July 2026 release by
mistake: docs/dev/EQUATION_REFACTOR_HANDOFF.md, the correction at its top).

Two checks:
1. Quoted blocks: the lines after a line containing "CAPRI's GAMS", indented deeper than that line. Each block,
   compared without white space and case and with GAMS comment lines dropped on both sides, must appear as a
   contiguous run in one of the .gms files the header names (or the module's default file); and the header's first
   cited line (l. N) must lie within 3 lines of where the run starts.
2. Quoted lines anywhere: a docstring or comment line that looks like GAMS (v_..(, p_..(, %data%, =L=, $ifi, ...)
   must appear in the copy, compared without white space and case (catches quotes outside a "CAPRI's GAMS" block).

    python tools/refactor/check_gams_quotes.py GAMS_DIR [FILES...] [--expect supply/supply_model.gms=5557]

GAMS_DIR is CAPRI's gams folder. Without FILES the refactor's modules are checked (capri_mod/supply/equations/,
capri_mod/market/equations/ when it exists). Exit status 1 if a check fails.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {"supply/equations/supply_model/": "supply/supply_model.gms",
            "market/equations/": "arm/market_model.gms"}
GAMSY = re.compile(r"(v_[A-Za-z]+\(|p_[A-Za-z]+\(|%data%|=[lLeEgG]=|\$ifi|\$iftheni|sum\(\s*\(|R_RAGG)")
PROSE = re.compile(r"\b(the|is|are|of|its|from|with|x|in this|read|set in|not)\b")
norm = lambda s: re.sub(r"\s+", "", s.strip().replace("\\", "/")).lower()


class Copy:
    """The CAPRI copy: its files' normalised lines, read on demand."""

    def __init__(self, root: Path):
        self.root = root
        self._lines: dict[str, list[str] | None] = {}
        self._code: dict[str, set[str]] = {}
        self._all: set[str] | None = None

    def resolve(self, name: str) -> str | None:
        name = name.strip("`'\"(").replace("\\", "/")
        if (self.root / name).exists():
            return name
        hits = sorted({p.relative_to(self.root).as_posix() for p in self.root.rglob(Path(name).name)})
        return hits[0] if len(hits) == 1 else None

    def lines(self, rel: str) -> list[str] | None:
        """The file's normalised code lines, a GAMS comment ('*' in the first column) as ''."""
        if rel not in self._lines:
            p = self.root / rel
            self._lines[rel] = ([("" if x.startswith("*") else norm(x)) for x in p.read_text(errors="replace").splitlines()]
                                if p.exists() else None)
            if self._lines[rel] is not None:
                self._code[rel] = set(self._lines[rel])
        return self._lines[rel]

    def code(self, rel: str) -> set[str]:
        self.lines(rel)
        return self._code.get(rel, set())

    def all_lines(self) -> set[str]:
        if self._all is None:
            self._all = set()
            for p in self.root.rglob("*.gms"):
                try:
                    self._all.update(t for t in (norm(x) for x in p.read_text(errors="replace").splitlines())
                                     if len(t) > 10)
                except OSError:
                    pass
        return self._all


def find_run(hay: list[str], run: list[str], code: set[str] | None = None) -> list[int]:
    """1-based start lines where run (normalised) appears in hay (the file's code lines, blanks and comments skipped).
    A quoted line starting with '*' is a GAMS comment unless it is one of the file's code lines (a continuation line
    such as '* 0.001;'): the quote's indentation does not keep GAMS's first column."""
    code = code or set()
    run = [x for x in run if x and (not x.startswith("*") or x in code)]
    if not run:
        return []
    idx = [i for i, x in enumerate(hay) if x]
    seq = [hay[i] for i in idx]
    return [idx[k] + 1 for k in range(len(seq) - len(run) + 1) if seq[k:k + len(run)] == run]


def blocks(text: str):
    """(line, header, quoted lines): the lines after a "CAPRI's GAMS" header, indented deeper than the header."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if "CAPRI's GAMS" not in lines[i]:
            i += 1
            continue
        head = lines[i]
        hind = len(head) - len(head.lstrip())
        j, body = i + 1, []
        while j < len(lines):
            line = lines[j]
            if line.strip():
                if len(line) - len(line.lstrip()) <= hind or line.strip().startswith('"""'):
                    break
            body.append(line.replace('"""', ""))
            j += 1
            if line.rstrip().endswith('"""'):
                break
        yield i + 1, head, body
        i = j


def default_file(path: str) -> str | None:
    return next((v for k, v in DEFAULTS.items() if k in path.replace("\\", "/")), None)


def check_file(path: Path, copy: Copy) -> list[str]:
    rel = path.relative_to(ROOT).as_posix() if path.is_absolute() and ROOT in path.parents else str(path)
    text = path.read_text()
    out = []
    in_blocks = set()
    for ln, head, body in blocks(text):
        in_blocks.update(range(ln, ln + len(body) + 1))
        runs, cur = [], []
        for x in body:
            t = norm(x)
            if not t:
                continue
            if t.startswith("...") and len(t) < 8:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            cur.append(t)
        if cur:
            runs.append(cur)
        if not runs:
            continue
        files = [f for f in (copy.resolve(g) for g in re.findall(r"([A-Za-z0-9_./\\]+\.gms)", head)) if f]
        dflt = default_file(rel)
        cands = list(dict.fromkeys(files[::-1] + ([dflt] if dflt else [])))
        found = None
        for f in cands:
            hay = copy.lines(f)
            if hay is None:
                continue
            starts = [find_run(hay, r, copy.code(f)) for r in runs]
            if all(starts):
                found = (f, starts)
                break
        if not found:
            out.append(f"{rel}:{ln}: quoted GAMS not found in {', '.join(cands) or 'any named file'}: {head.strip()[:90]}")
            continue
        f, starts = found
        cited = re.findall(r"l\. (\d+)(?:-(\d+))?", head)
        if cited:
            a = int(cited[0][0])
            b = int(cited[0][1] or a)
            if not any(a - 3 <= s <= b + 3 for s in starts[0]):
                at = ", ".join(str(x) for x in starts[0][:4])
                out.append(f"{rel}:{ln}: cited l. {a}, the quote is at l. {at} of {f}: {head.strip()[:80]}")
    # lines that look like GAMS outside the blocks
    allg = None
    for i, line in enumerate(text.splitlines(), 1):
        if i in in_blocks or not GAMSY.search(line):
            continue
        t = norm(line)
        if len(t) < 20 or t.startswith(("#", "return", "def", "obj", "g_rows")):
            continue
        if "=" in line and ("(" in line and line.lstrip().startswith(("obj", "self.", "lam", "x[", "y[", "s_", "m_"))):
            continue
        if "..." in line or PROSE.search(line):
            continue                       # an elided quote, or a sentence that names GAMS symbols
        allg = allg if allg is not None else copy.all_lines()
        if t not in allg and line.strip().startswith(("$", "+", "-", "*", "=", "v_", "p_", "%", "sum(", "SUM(")) \
                and not line.strip().startswith(("- **", "* ", "-- ")):
            out.append(f"{rel}:{i}: GAMS-like line not in the copy: {line.strip()[:100]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gams_dir", type=Path)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--expect", action="append", default=[],
                    help="FILE=LINES: stop unless the copy's file has that many lines (e.g. supply/supply_model.gms=5557, "
                         "CAPRI star 3.0)")
    a = ap.parse_args()
    copy = Copy(a.gams_dir)
    for e in a.expect:
        f, n = e.split("=")
        got = len((a.gams_dir / f).read_text(errors="replace").splitlines())
        if got != int(n):
            print(f"the CAPRI copy's {f} has {got} lines, not {n}: not the copy expected", file=sys.stderr)
            return 2
    files = a.files or sorted(p for d in ("capri_mod/supply/equations", "capri_mod/market/equations")
                              for p in (ROOT / d).rglob("*.py") if (ROOT / d).exists())
    problems = []
    for f in files:
        problems += check_file(f if f.is_absolute() else (ROOT / f), copy)
    for p in problems:
        print(p)
    print(f"{len(files)} files checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

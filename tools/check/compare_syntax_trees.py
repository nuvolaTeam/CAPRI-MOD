#!/usr/bin/env python3
"""Whether a change leaves the Python code's syntax trees as they were (the code quality plan, steps 6 and 8).

A change of comments only, or a formatter's, does not change what Python runs: the files' syntax trees (ast) are the
same before and after, as comments and layout are not in the tree. This compares the tree of every .py file that
differs between two revisions, and needs no model run.

    python tools/check/compare_syntax_trees.py REV_A [REV_B] [--docstrings exact|normalised|ignored] [--paths P ...]

REV_B defaults to the working tree. --docstrings: "exact" (the default; a docstring is code, a string constant),
"normalised" (each docstring compared with its lines stripped and blank lines dropped: a formatter's re-indentation
passes, a changed word does not) or "ignored" (docstrings left out, for a change of docstrings and comments).
--paths limits the comparison to files under these paths. Exit status 1 if a tree differs or a file does not parse
on one side; a file added or deleted between the revisions is reported, and fails the check, as it is not a
change of layout.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODES = ("exact", "normalised", "ignored")


def _docstring_owner(node) -> bool:
    return isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))


def tree_dump(src: str, docstrings: str = "exact") -> str:
    """The source's syntax tree as a string, without positions; docstrings as the mode says."""
    tree = ast.parse(src)
    if docstrings != "exact":
        for n in ast.walk(tree):
            if not (_docstring_owner(n) and n.body and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str)):
                continue
            if docstrings == "ignored":
                n.body = n.body[1:] or [ast.Pass()]
            else:
                c = n.body[0].value
                c.value = "\n".join(ln.strip() for ln in c.value.splitlines() if ln.strip())
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def same_tree(src_a: str, src_b: str, docstrings: str = "exact") -> bool:
    return tree_dump(src_a, docstrings) == tree_dump(src_b, docstrings)


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def _source(rev: str | None, path: str) -> str | None:
    if rev is None:
        p = ROOT / path
        return p.read_text() if p.exists() else None
    r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def changed_files(rev_a: str, rev_b: str | None, paths) -> list:
    args = ["diff", "--name-only", rev_a] + ([rev_b] if rev_b else []) + ["--"] + (list(paths) or ["."])
    return sorted(f for f in _git(*args).splitlines() if f.endswith(".py"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("rev_a")
    ap.add_argument("rev_b", nargs="?", default=None, help="default: the working tree")
    ap.add_argument("--docstrings", choices=MODES, default="exact")
    ap.add_argument("--paths", nargs="*", default=[])
    a = ap.parse_args(argv)
    files = changed_files(a.rev_a, a.rev_b, a.paths)
    bad = []
    for f in files:
        sa, sb = _source(a.rev_a, f), _source(a.rev_b, f)
        if sa is None or sb is None:
            bad.append((f, "added" if sa is None else "deleted"))
            continue
        try:
            if not same_tree(sa, sb, a.docstrings):
                bad.append((f, "the syntax tree differs"))
        except SyntaxError as e:
            bad.append((f, f"does not parse: {e}"))
    for f, why in bad:
        print(f"{f}: {why}")
    print(f"{len(files)} changed .py files compared (docstrings {a.docstrings}), {len(bad)} with a different tree")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

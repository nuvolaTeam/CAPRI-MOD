"""Guards of the exact data I/O (KNOWN_ISSUES K82, K88): floats reach the model as CAPRI stored them.

Two risks, checked statically (seconds, nothing is run):
- reading: pandas' default CSV float parser is not exact (about two thirds of full-precision values come back one unit
  in the last place off); every pandas CSV read of the model, its builders and its checks must parse floats exactly
  (float_precision="round_trip", capri_mod/csvio.read_csv, or a wrapper that sets it) or read text (dtype=str). The
  csv module with float() is exact.
- writing: to_csv without float_format writes each float exactly (its shortest round-trip form); what loses digits
  is rounding the values before they are written. No builder rounds what it writes (K88); a rounding outside a printed
  message fails the test.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: builder -> roundings of values outside print/f-strings that are allowed (none since K88 was fixed)
ROUNDING_ALLOWED: dict = {}


def _parents(tree):
    par = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            par[c] = n
    return par


def test_csv_float_reads_are_exact():
    bad = []
    for root in ("capri_mod", "tools"):
        for p in sorted((ROOT / root).rglob("*.py")):
            if "tests" in p.parts or p.name == "csvio.py":
                continue
            src = p.read_text()
            tree = ast.parse(src)
            par = _parents(tree)
            for n in ast.walk(tree):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "read_csv"
                        and isinstance(n.func.value, ast.Name) and n.func.value.id in ("pd", "pandas", "_pd")):
                    continue
                if {k.arg for k in n.keywords} & {"float_precision", "dtype"}:
                    continue
                q, ok = n, False
                while q in par:                        # a wrapper that sets float_precision for its callers
                    q = par[q]
                    if isinstance(q, ast.FunctionDef) and "float_precision" in (ast.get_source_segment(src, q) or ""):
                        ok = True
                        break
                if not ok:
                    bad.append(f"{p.relative_to(ROOT)}:{n.lineno}")
    assert not bad, f"CSV float reads that are not exact (use capri_mod.csvio.read_csv): {bad}"


def test_builders_do_not_round_what_they_write():
    found = Counter()
    for p in sorted((ROOT / "tools" / "build").glob("*.py")):
        tree = ast.parse(p.read_text())
        par = _parents(tree)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            if isinstance(n.func, ast.Attribute) and n.func.attr == "to_csv" and any(k.arg == "float_format"
                                                                                    for k in n.keywords):
                found[p.name] += 1
                continue
            if not ((isinstance(n.func, ast.Name) and n.func.id == "round")
                    or (isinstance(n.func, ast.Attribute) and n.func.attr == "round")):
                continue
            q, message = n, False
            while q in par:                            # rounding inside a printed message is fine
                q = par[q]
                if isinstance(q, ast.JoinedStr) or (isinstance(q, ast.Call) and isinstance(q.func, ast.Name)
                                                    and q.func.id == "print"):
                    message = True
                    break
            if not message:
                found[p.name] += 1
    over = {f: (n, ROUNDING_ALLOWED.get(f, 0)) for f, n in found.items() if n > ROUNDING_ALLOWED.get(f, 0)}
    assert not over, f"builders rounding values they write (found, allowed): {over} - write full precision (K88)"

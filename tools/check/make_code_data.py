"""The numbers held in the model's code, as SQL: capri_data/schema/03_code_data.sql (generated).

The data checks see the CSV files; a number written in the code escapes them. This scan lists the numbers in the
model's code (capri_mod, tests left out) that may be data, one row per (file, scope, value):
  file    the module
  scope   where the number stands: the name it is assigned to (FEED_ELAS, SupplyModule.nlp_tol) or the function it
          is written in (SupplyModule._organic_limits), qualified by its class
  value   the number
  n       how often the value stands in that scope
  lines   the lines (for reading only: they move with every edit, so they are not part of the key)
  excerpt the start of the first line

What is listed:
  - every number in a module-level or class-level assignment except 0, 1 and -1 (named constants and tables), the
    fields of a dataclass included;
  - every other number written in the code, except: 0, 1, -1, the integers up to 12, 0.5, the powers of ten
    (unit factors), numbers below 1e-5 in absolute value (tolerances), and numbers in a printed or formatted message,
    in round() or in range().
The exceptions are a filter, not a judgement: a number they leave out can still be data (a target of 10 written
inline); the named constants are listed whatever their size for that reason.

Each listed number needs a classification in capri_data/schema/04_code_data_status.sql (kept by hand: where the
number comes from, and whether it belongs in the code); the rule there fails on a number without one. After editing
the code, run this script and classify the new rows.

    python tools/check/make_code_data.py           # writes capri_data/schema/03_code_data.sql
    python tools/check/make_code_data.py --check   # exit 1 if the file is not up to date (the test)
"""
from __future__ import annotations

import argparse
import ast
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "schema" / "03_code_data.sql"
SKIP_CALLS = {"print", "round", "range", "warn", "format"}


def _trivial(v) -> bool:
    v = float(v)
    if v in (0.0, 1.0, -1.0, 0.5):
        return True
    if abs(v) < 1e-5:
        return True
    if v == int(v) and abs(v) <= 12:
        return True
    return v > 0 and abs(math.log10(v) - round(math.log10(v))) < 1e-12


def _number(n):
    if isinstance(n, ast.Constant) and type(n.value) in (int, float):
        return n.value
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) \
            and type(n.operand.value) in (int, float):
        return -n.operand.value
    return None


def scan(root: Path = ROOT):
    """{(file, scope, value): [lines]} and the first line's text of each."""
    found = defaultdict(list)
    text = {}
    for p in sorted((root / "capri_mod").rglob("*.py")):
        if "tests" in p.parts:
            continue
        rel = str(p.relative_to(root))
        src = p.read_text(encoding="utf-8")
        src_lines = src.splitlines()
        tree = ast.parse(src)

        def visit(node, scope, named, skip):
            if isinstance(node, ast.UnaryOp) and _number(node) is not None:
                v = _number(node)
                children = []
            elif isinstance(node, ast.Constant) and type(node.value) in (int, float):
                v = node.value
                children = []
            else:
                v = None
                children = None
            if v is not None:
                keep = (v not in (0, 1, -1)) if named else not _trivial(v)
                if keep and not skip:
                    key = (rel, scope, float(v))
                    found[key].append(node.lineno)
                    text.setdefault(key, src_lines[node.lineno - 1].strip()[:120])
                return
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in node.decorator_list:
                    visit(d, scope, named, skip)
                for d in node.args.defaults + node.args.kw_defaults:
                    if d is not None:
                        visit(d, scope, named, skip)
                inner = (scope + "." if scope else "") + node.name
                for s in node.body:
                    visit(s, inner, False, skip)
                return
            if isinstance(node, ast.ClassDef):
                for s in node.body:
                    statement(s, (scope + "." if scope else "") + node.name)
                return
            if isinstance(node, ast.JoinedStr):
                return
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                if name in SKIP_CALLS:
                    return
            if isinstance(node, ast.Slice):                      # str(e)[:40]: a length, not data
                return
            for c in ast.iter_child_nodes(node):
                visit(c, scope, named, skip)

        def statement(s, scope):
            """A module-level or class-level statement: an assignment's value is a named constant."""
            if isinstance(s, (ast.Assign, ast.AnnAssign)):
                tg = s.targets if isinstance(s, ast.Assign) else [s.target]
                names = [t.id for t in tg if isinstance(t, ast.Name)]
                if names and s.value is not None:
                    visit(s.value, (scope + "." if scope else "") + names[0], True, False)
                    return
            if isinstance(s, ast.ClassDef):
                inner = (scope + "." if scope else "") + s.name
                for d in s.decorator_list:
                    visit(d, scope, False, False)
                for b in s.body:
                    statement(b, inner)
                return
            visit(s, scope, False, False)

        for s in tree.body:
            statement(s, "")
    return found, text


def _q(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def render(found, text) -> str:
    lines = [
        "-- The numbers held in the model's code: generated by tools/check/make_code_data.py; do not edit by hand.",
        "-- Their classification (where each comes from, whether it belongs in the code): 04_code_data_status.sql.",
        "",
        "CREATE TABLE code_data (",
        "    file VARCHAR NOT NULL,",
        "    scope VARCHAR NOT NULL,",
        "    value DOUBLE NOT NULL,",
        "    n INTEGER NOT NULL,",
        "    lines VARCHAR NOT NULL,",
        "    excerpt VARCHAR,",
        "    PRIMARY KEY (file, scope, value)",
        ");",
        "COMMENT ON TABLE code_data IS 'the numbers in the model code that may be data (tools/check/make_code_data.py)';",
    ]
    if found:
        lines.append("INSERT INTO code_data VALUES")
        vals = []
        for (f, s, v), ls in sorted(found.items()):
            vals.append(f"  ({_q(f)}, {_q(s or '<module>')}, {v!r}, {len(ls)}, {_q(','.join(map(str, ls)))}, "
                        f"{_q(text[(f, s, v)])})")
        lines.append(",\n".join(vals) + ";")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    found, text = scan()
    out = render(found, text)
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == out
        print("up to date" if ok else f"{OUT.relative_to(ROOT)} is not up to date: run tools/check/make_code_data.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(out, encoding="utf-8")
    print(f"{len(found)} rows ({sum(len(v) for v in found.values())} numbers) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

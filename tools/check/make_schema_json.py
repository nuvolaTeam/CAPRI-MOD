"""The data declarations as one JSON file: capri_data/schema/schema.json (generated, do not edit).

The declarations are the SQL files under capri_data/schema (tools/check/validate_data.py enforces them on the CSVs).
This script builds their catalogue in DuckDB (the tables created, the code lists loaded, no data checked) and writes
what a program or a person needs to know about each table without reading SQL:

  tables      one entry per declared CSV file, by table name:
                file, declared_in (the .sql file), layout (wide, unnamed), comment,
                columns [{name, type, not_null, comment}], primary_key, unique, foreign_keys
                [{columns, references, ref_columns}], checks (the CHECK expressions),
                units [{item, unit, status, basis}] (value_units: per column of a long table, per item of a wide one),
                provenance {nature, origins, builder, sources} (01_provenance.sql),
                notes [{kind (origin, gap), note, evidence, checked}] (02_provenance_notes.sql),
                read_by {model, builders, checks, tests} (see below)
  metadata    the tables that describe the others (value_units, provenance, code_data, ...): columns and comment
  rules       the rules (queries that must return no rows), with their file and text
  code_data   the numbers held in the model's code by status and action (03_code_data.sql, 04_code_data_status.sql)
  other_notes the checked notes on data files that are not declared (JSON data files)

read_by: builders from the pipeline's trace (tools/pipeline/builders.json, exact); model, checks and tests from a
static scan of the Python files under capri_mod and tools/check for a string that names the file (a literal ending
in its name, or an f-string that matches it and whose fixed text, the extension aside, has three letters or more in
its last path part; docstrings left out). The scan finds a file named in the code, not a
file read at run time: a name assembled otherwise is missed, and a name in a comment string or a write counts.

    python tools/check/make_schema_json.py           # writes capri_data/schema/schema.json
    python tools/check/make_schema_json.py --check   # exit 1 if schema.json is not up to date (the test)
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "schema" / "schema.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_data as V  # noqa: E402


def _names_in_code(root: Path):
    """{python file: (set of string literals, [compiled f-string patterns])}, docstrings left out."""
    out = {}
    files = [p for p in (root / "capri_mod").rglob("*.py")] + [p for p in (root / "tools" / "check").rglob("*.py")]
    for p in sorted(files):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body \
                    and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                docs.add(id(n.body[0].value))
        lits, pats = set(), []
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and ".csv" in n.value:
                lits.add(n.value)
            elif isinstance(n, ast.JoinedStr):
                parts, fixed = [], ""
                for v in n.values:
                    if isinstance(v, ast.Constant):
                        parts.append(re.escape(str(v.value)))
                        fixed += str(v.value)
                    else:
                        parts.append("[^/]+")
                pat = "".join(parts)
                # an f-string whose fixed text names little more than the extension (f"{name}.csv") names no file
                stem = fixed.rsplit("/", 1)[-1].replace(".csv", "")
                if ".csv" in fixed and len(re.sub(r"[^A-Za-z]", "", stem)) >= 3:
                    pats.append(re.compile(r"(?:^|.*/)" + pat + "$"))
        out[str(p.relative_to(root))] = (lits, pats)
    return out


def _readers(files, root: Path):
    code = _names_in_code(root)
    tasks = json.loads((root / "tools" / "pipeline" / "builders.json").read_text())["tasks"]
    by_input = defaultdict(set)
    for t in tasks:
        for i in t["inputs"]:
            by_input[i].add(t["builder"])
    res = {}
    for f in files:
        base = f.rsplit("/", 1)[-1]
        rel = f.split("capri_data/", 1)[-1]
        hit = {"model": [], "builders": sorted(by_input.get(f, ())), "checks": [], "tests": []}
        for py, (lits, pats) in code.items():
            named = any(x == base or x.endswith("/" + base) or x.endswith(rel) for x in lits) \
                or any(p.match(rel) or p.match(base) for p in pats)
            if not named:
                continue
            if "/tests/" in py:
                hit["tests"].append(py)
            elif py.startswith("tools/check/"):
                hit["checks"].append(py)
            else:
                hit["model"].append(py)
        res[f] = hit
    return res


def build(root: Path = ROOT) -> dict:
    import duckdb
    con = duckdb.connect()
    V.validate(root, verbose=False, con=con, declarations_only=True)
    declared = dict(con.execute("SELECT tbl, file FROM _declared").fetchall())
    where, lay, rules = {}, {}, []
    for sql_file in sorted((root / "capri_data" / "schema").glob("*.sql")):
        for kind, arg, stmt in V.parse(sql_file.read_text(encoding="utf-8")):
            if kind == "table":
                t = re.match(r"\s*CREATE\s+TABLE\s+(\w+)", stmt, re.I).group(1)
                where[t] = sql_file.name
                lay[t] = sorted(V.layout(stmt))
            elif kind == "rule":
                rules.append({"file": sql_file.name, "rule": arg})
            elif re.match(r"\s*CREATE\s+TABLE", stmt, re.I):
                where[re.match(r"\s*CREATE\s+TABLE\s+(\w+)", stmt, re.I).group(1)] = sql_file.name

    def q(sql, *a):
        return con.execute(sql, list(a)).fetchall()

    tcomment = dict(q("SELECT table_name, comment FROM duckdb_tables() WHERE NOT temporary"))
    cols = defaultdict(list)
    for t, c, typ, nullable, cm in q("SELECT table_name, column_name, data_type, is_nullable, comment FROM duckdb_columns() "
                                     "WHERE NOT internal AND database_name <> 'temp' ORDER BY table_name, column_index"):
        cols[t].append({"name": c, "type": typ, "not_null": not nullable, **({"comment": cm} if cm else {})})
    cons = defaultdict(lambda: {"primary_key": [], "unique": [], "foreign_keys": [], "checks": []})
    for t, ct, cc, expr, rt, rc in q("SELECT table_name, constraint_type, constraint_column_names, expression, "
                                     "referenced_table, referenced_column_names FROM duckdb_constraints() "
                                     "ORDER BY table_name, constraint_index"):
        d = cons[t]
        if ct == "PRIMARY KEY":
            d["primary_key"] = list(cc)
        elif ct == "UNIQUE":
            d["unique"].append(list(cc))
        elif ct == "FOREIGN KEY":
            d["foreign_keys"].append({"columns": list(cc), "references": rt, "ref_columns": list(rc)})
        elif ct == "CHECK" and expr:
            d["checks"].append(expr)
    units = defaultdict(list)
    for t, item, unit, status, basis in q("SELECT tbl, item, unit, status, basis FROM value_units ORDER BY tbl, item"):
        units[t].append({"item": item, "unit": unit, "status": status, "basis": basis})
    prov = {f: {"nature": n, "origins": o, "builder": b, "sources": s}
            for f, n, o, b, s in q("SELECT file, nature, origins, builder, sources FROM provenance")}
    notes = defaultdict(list)
    for f, k, n, e, c in q("SELECT file, kind, note, evidence, CAST(checked AS VARCHAR) FROM provenance_notes "
                           "ORDER BY file, kind DESC, n"):
        notes[f].append({"kind": k, "note": n, "evidence": e, "checked": c})
    readers = _readers(sorted(declared.values()), root)

    tables = {}
    for t in sorted(declared):
        f = declared[t]
        c = cons[t]
        tables[t] = {
            "file": f, "declared_in": where.get(t), "layout": lay.get(t, []), "comment": tcomment.get(t),
            "columns": cols[t], "primary_key": c["primary_key"], "unique": c["unique"],
            "foreign_keys": c["foreign_keys"], "checks": c["checks"], "units": units.get(t, []),
            "provenance": prov.get(f), "notes": notes.get(f, []), "read_by": readers[f],
        }
    meta = {t: {"declared_in": where.get(t), "comment": tcomment.get(t), "columns": cols[t],
                "primary_key": cons[t]["primary_key"]}
            for t in sorted(cols) if t not in declared and not t.startswith("_")}
    code = {}
    if "code_data_status" in cols:
        code = {f"{s}/{a}": n for s, a, n in q("SELECT status, action, count(*) FROM code_data_status "
                                               "GROUP BY ALL ORDER BY 1, 2")}
    return {
        "_doc": "The data declarations of capri_data/schema/*.sql as JSON, generated by tools/check/make_schema_json.py "
                "(do not edit; edit the .sql files and run the script). The CSV files are the data; the .sql files "
                "declare them and tools/check/validate_data.py enforces the declarations.",
        "tables": tables, "metadata": meta, "rules": rules, "code_data": code,
        "other_notes": {f: n for f, n in sorted(notes.items()) if f not in set(declared.values())},
    }


def render(doc) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = render(build())
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == out
        print("up to date" if ok else f"{OUT.relative_to(ROOT)} is not up to date: run tools/check/make_schema_json.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(out, encoding="utf-8")
    doc = json.loads(out)
    print(f"{len(doc['tables'])} tables, {len(doc['metadata'])} metadata tables, {len(doc['rules'])} rules "
          f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

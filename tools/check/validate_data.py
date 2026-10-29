"""The data checks: the declarations under capri_data/schema enforced on the CSV files (docs/design/DATA_SCHEMA_DUCKDB.md).

Each `capri_data/schema/*.sql` file declares tables (DuckDB DDL: column types, NOT NULL, PRIMARY KEY, UNIQUE,
REFERENCES to the code lists, CHECK ranges; units and sources as comments) and rules (queries that must return no
rows). A `-- file: <path>` line names the CSV a CREATE TABLE loads; a `-- rule: <text>` line makes the next statement
a rule. Files run in name order, so a file can reference the tables of the files before it.

For each declared CSV, in an in-memory database, the check lists every violation, not only the first:
  columns   the file's header against the declared columns (names and order)
  types     values that do not convert to the declared type (CSV line numbers)
  not null  empty values in NOT NULL columns
  keys      duplicate PRIMARY KEY / UNIQUE values
  refs      values not in the referenced table (a code no code list knows)
  checks    rows that fail a CHECK expression
then loads the file into the declared table, so DuckDB enforces the same declarations. The rules run after all loads.
The CSVs stay the stored data; the database is built for the check and not kept.

    python tools/check/validate_data.py                  # every declaration; exit 1 on a violation
    python tools/check/validate_data.py --root DIR       # another checkout (the tests' copies)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOW = 5          # examples shown per violation


def parse(sql_text):
    """The statements of a declaration file, each with its kind ('table' with its CSV, 'rule' with its text, 'sql')."""
    out, buf, pending_file, pending_rule = [], [], None, None
    for line in sql_text.splitlines():
        s = line.strip()
        m = re.match(r"--\s*file:\s*(\S+)", s)
        if m and not buf:
            pending_file = m.group(1)
            continue
        m = re.match(r"--\s*rule:\s*(.+)", s)
        if m and not buf:
            pending_rule = m.group(1).strip()
            continue
        if not buf and (not s or s.startswith("--")):
            continue
        buf.append(line)
        if s.split("--")[0].rstrip().endswith(";"):
            stmt = "\n".join(buf)
            if pending_rule is not None:
                out.append(("rule", pending_rule, stmt))
            elif re.match(r"\s*CREATE\s+TABLE", stmt, re.I) and pending_file:
                out.append(("table", pending_file, stmt))
            else:
                out.append(("sql", None, stmt))
            buf, pending_file, pending_rule = [], None, None
    if buf:
        raise ValueError("a statement without its closing ';'")
    return out


def check_table(con, table, csv_path):
    """Every violation of the table's declarations in the CSV, as (kind, message) pairs; then the load."""
    v = []
    cols = con.execute("SELECT column_name, data_type, is_nullable FROM duckdb_columns() WHERE table_name = ? "
                       "ORDER BY column_index", [table]).fetchall()
    names = [c[0] for c in cols]
    con.execute("CREATE OR REPLACE TEMP TABLE _stage AS SELECT row_number() OVER () + 1 AS _line, * "
                "FROM read_csv(?, header = false, all_varchar = true, auto_detect = false, "
                f"columns = {{{', '.join(repr(f'c{i}') + ': ' + repr('VARCHAR') for i in range(_ncols(csv_path)))}}}, "
                "skip = 1)", [str(csv_path)])
    header = _header(csv_path)
    if header != names:
        return [("columns", f"header {header} against declared {names}")]
    ren = ", ".join(f'c{i} AS "{n}"' for i, n in enumerate(names))
    con.execute(f"CREATE OR REPLACE TEMP TABLE _raw AS SELECT _line, {ren} FROM _stage")
    # types and not null
    for n, typ, nullable in cols:
        if typ != "VARCHAR":
            bad = con.execute(f'SELECT _line, "{n}" FROM _raw WHERE "{n}" IS NOT NULL AND "{n}" <> \'\' '
                              f'AND TRY_CAST("{n}" AS {typ}) IS NULL LIMIT {SHOW}').fetchall()
            if bad:
                v.append(("types", f"{n} ({typ}): " + ", ".join(f"line {l}: {x!r}" for l, x in bad)))
        if not nullable:
            bad = con.execute(f'SELECT _line FROM _raw WHERE "{n}" IS NULL OR "{n}" = \'\' LIMIT {SHOW}').fetchall()
            if bad:
                v.append(("not null", f"{n} empty at lines {[b[0] for b in bad]}"))
    if v:
        return v
    typed = ", ".join(f'CAST(NULLIF("{n}", \'\') AS {t}) AS "{n}"' for n, t, _ in cols)
    con.execute(f"CREATE OR REPLACE TEMP TABLE _typed AS SELECT _line, {typed} FROM _raw")
    cons = con.execute("SELECT constraint_type, constraint_column_names, expression, referenced_table, "
                       "referenced_column_names FROM duckdb_constraints() WHERE table_name = ?", [table]).fetchall()
    for ctype, ccols, expr, rtab, rcols in cons:
        q = ", ".join(f'"{c}"' for c in ccols)
        if ctype in ("PRIMARY KEY", "UNIQUE"):
            bad = con.execute(f"SELECT {q}, list(_line) FROM _typed GROUP BY {q} HAVING count(*) > 1 "
                              f"LIMIT {SHOW}").fetchall()
            if bad:
                v.append(("keys", f"{ctype} ({', '.join(ccols)}) repeated: "
                          + "; ".join(f"{b[:-1]} at lines {b[-1]}" for b in bad)))
        elif ctype == "FOREIGN KEY":
            on = " AND ".join(f't."{a}" = r."{b}"' for a, b in zip(ccols, rcols))
            notnull = " AND ".join(f't."{a}" IS NOT NULL' for a in ccols)
            bad = con.execute(f"SELECT {', '.join('t.' + chr(34) + c + chr(34) for c in ccols)}, t._line FROM _typed t "
                              f"WHERE {notnull} AND NOT EXISTS (SELECT 1 FROM {rtab} r WHERE {on}) "
                              f"LIMIT {SHOW}").fetchall()
            if bad:
                n_bad = con.execute(f"SELECT count(*) FROM _typed t WHERE {notnull} AND NOT EXISTS "
                                    f"(SELECT 1 FROM {rtab} r WHERE {on})").fetchone()[0]
                v.append(("refs", f"({', '.join(ccols)}) not in {rtab}: {n_bad} rows, e.g. "
                          + ", ".join(f"{b[:-1]} line {b[-1]}" for b in bad)))
        elif ctype == "CHECK" and expr:
            bad = con.execute(f"SELECT _line FROM _typed WHERE NOT ({expr}) LIMIT {SHOW}").fetchall()
            if bad:
                v.append(("checks", f"{expr} fails at lines {[b[0] for b in bad]}"))
    if not v:
        con.execute(f"INSERT INTO {table} SELECT {', '.join(chr(34) + n + chr(34) for n in names)} FROM _typed")
    return v


def _header(path):
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh))


def _ncols(path):
    return len(_header(path))


def validate(root=ROOT, verbose=True):
    """All declarations under root/capri_data/schema checked; returns the violations as (where, kind, message)."""
    import duckdb
    root = Path(root)
    con = duckdb.connect()
    found, declared = [], []
    for sql_file in sorted((root / "capri_data" / "schema").glob("*.sql")):
        for kind, arg, stmt in parse(sql_file.read_text(encoding="utf-8")):
            if kind == "table":
                con.execute(stmt)
                table = re.match(r"\s*CREATE\s+TABLE\s+(\w+)", stmt, re.I).group(1)
                path = root / arg
                declared.append(arg)
                if not path.exists():
                    found.append((arg, "file", "declared file missing"))
                    continue
                for k, msg in check_table(con, table, path):
                    found.append((arg, k, msg))
            elif kind == "rule":
                rows = con.execute(stmt).fetchall()
                if rows:
                    found.append((f"{sql_file.name}: {arg}", "rule", f"{len(rows)} rows, e.g. {rows[:SHOW]}"))
            else:
                con.execute(stmt)
    if verbose:
        all_csv = [p for p in (root / "capri_data").rglob("*.csv") if "archive" not in p.parts]
        print(f"{len(declared)} files declared of {len(all_csv)} CSV files under capri_data; "
              f"{len(found)} violations")
        for where, k, msg in found:
            print(f"  {where} [{k}] {msg}")
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args()
    sys.exit(1 if validate(a.root) else 0)


if __name__ == "__main__":
    main()

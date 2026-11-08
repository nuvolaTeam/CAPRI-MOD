"""The data checks: the declarations under capri_data/schema enforced on the CSV files (docs/design/DATA_SCHEMA_DUCKDB.md).

Each `capri_data/schema/*.sql` file declares tables (DuckDB DDL: column types, NOT NULL, PRIMARY KEY, UNIQUE,
REFERENCES to the code lists, CHECK ranges; units and sources as comments) and rules (queries that must return no
rows). A `-- file: <path>` line names the CSV a CREATE TABLE loads; a `-- rule: <text>` line makes the next statement
a rule. Files run in name order, so a file can reference the tables of the files before it.

A `-- layout:` line between the file line and its CREATE TABLE says how the CSV is laid out:
  wide      regions in rows, codes as columns (yields.csv): the table is declared long, (key, item, value), the
            CSV's first column is the key, every other header an item; so the headers are checked against a code
            list by the item column's REFERENCES, and the values by the value column's type and CHECK
  unnamed   the first header is empty (a pandas index written without a name) and stands for the first declared column

For each declared CSV, in an in-memory database, the check lists every violation, not only the first:
  columns   the file's header against the declared columns (names and order)
  types     values that do not convert to the declared type (CSV line numbers)
  not null  empty values in NOT NULL columns
  keys      duplicate PRIMARY KEY / UNIQUE values
  refs      values not in the referenced table (a code no code list knows)
  checks    rows that fail a CHECK expression
then loads the file into the declared table, so DuckDB enforces the same declarations. A CSV under capri_data
(archive/ left out) without a declaration is a violation too, and so are a missing file of the catalogue
(05_file_catalogue.sql, the files that are not CSV) and a staple crop with an implausible gross margin (margins();
both from the former MANIFEST.json validator, merged here on 31 October 2026). The rules can use the temporary table
_declared (file, tbl): the files declared so far and their tables. A rule runs where it stands, in file order: it can use the tables declared before it.
The CSVs stay the stored data; the database is built for the check and not kept, unless --db names a file to keep
it in (a copy for querying, rebuilt from the CSVs each time; a table whose file breaks a declaration stays empty).

    python -m capri_mod.data.validate_data                  # every declaration; exit 1 on a violation
    python -m capri_mod.data.validate_data --root DIR       # another checkout (the tests' copies)
    python -m capri_mod.data.validate_data --db data.duckdb # also keep the database (built anew; not kept in git)
(tools/check/validate_data.py, the same command line, kept for the gates and dodo.py)
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
    out, buf, pending_file, pending_rule, pending_layout = [], [], None, None, ""
    for line in sql_text.splitlines():
        s = line.strip()
        m = re.match(r"--\s*file:\s*(\S+)", s)
        if m and not buf:
            pending_file = m.group(1)
            continue
        if re.match(r"--\s*layout:", s) and not buf and pending_file:
            pending_layout = s
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
                out.append(("table", pending_file, stmt + ("\n" + pending_layout if pending_layout else "")))
            else:
                out.append(("sql", None, stmt))
            buf, pending_file, pending_rule, pending_layout = [], None, None, ""
    if buf:
        raise ValueError("a statement without its closing ';'")
    return out


def layout(stmt):
    """The layout words of a declaration (its `-- layout:` line): a subset of {'wide', 'unnamed'}."""
    m = re.search(r"--\s*layout:\s*(.+)", stmt)
    words = set(re.findall(r"\w+", m.group(1))) if m else set()
    if words - {"wide", "unnamed"}:
        raise ValueError(f"unknown layout {sorted(words - {'wide', 'unnamed'})}")
    return words


def check_table(con, table, csv_path, lay=frozenset()):
    """Every violation of the table's declarations in the CSV, as (kind, message) pairs; then the load."""
    v = []
    cols = con.execute("SELECT column_name, data_type, is_nullable FROM duckdb_columns() WHERE table_name = ? "
                       "ORDER BY column_index", [table]).fetchall()
    names = [c[0] for c in cols]
    if str(csv_path).endswith(".parquet"):
        # a table of capri_data/sources (Parquet since 8 November 2026, data layout step (c)): its values as text, in
        # the file's row order, line numbers as its former CSV's (header line 1); a null is an empty cell
        sel = ", ".join(f'CAST("{n}" AS VARCHAR) AS c{i}' for i, n in enumerate(_parquet_names(csv_path)))
        con.execute(f"CREATE OR REPLACE TEMP TABLE _stage AS SELECT file_row_number + 2 AS _line, {sel} "
                    "FROM read_parquet(?, file_row_number = true) ORDER BY file_row_number", [str(csv_path)])
    else:
        con.execute("CREATE OR REPLACE TEMP TABLE _stage AS SELECT row_number() OVER () + 1 AS _line, * "
                    "FROM read_csv(?, header = false, all_varchar = true, auto_detect = false, "
                    f"columns = {{{', '.join(repr(f'c{i}') + ': ' + repr('VARCHAR') for i in range(_ncols(csv_path)))}}}, "
                    "skip = 1)", [str(csv_path)])
    header = _header(csv_path)
    if "unnamed" in lay and header and header[0] == "":
        header = [names[0]] + header[1:]
    if "wide" in lay:
        if len(names) != 3 or header[0] != names[0] or len(header) < 2:
            return [("columns", f"wide file: first header {header[:1]} against the key {names[:1]}, and a declared "
                     f"(key, item, value) of 3 columns ({names})")]
        items = ", ".join("'" + h.replace("'", "''") + "'" for h in header[1:])
        vals = ", ".join(f"c{i}" for i in range(1, len(header)))
        con.execute(f'CREATE OR REPLACE TEMP TABLE _raw AS SELECT _line, c0 AS "{names[0]}", unnest([{items}]) AS '
                    f'"{names[1]}", unnest([{vals}]) AS "{names[2]}" FROM _stage')
    elif header != names:
        return [("columns", f"header {header} against declared {names}")]
    else:
        ren = ", ".join(f'c{i} AS "{n}"' for i, n in enumerate(names))
        con.execute(f"CREATE OR REPLACE TEMP TABLE _raw AS SELECT _line, {ren} FROM _stage")
    # types and not null (in a wide file the item is named with the line)
    at = f"_line || ' ' || \"{names[1]}\"" if "wide" in lay else "_line"
    for n, typ, nullable in cols:
        if typ != "VARCHAR":
            bad = con.execute(f'SELECT {at}, "{n}" FROM _raw WHERE "{n}" IS NOT NULL AND "{n}" <> \'\' '
                              f'AND TRY_CAST("{n}" AS {typ}) IS NULL LIMIT {SHOW}').fetchall()
            if bad:
                v.append(("types", f"{n} ({typ}): " + ", ".join(f"line {l}: {x!r}" for l, x in bad)))
        if not nullable:
            bad = con.execute(f'SELECT {at} FROM _raw WHERE "{n}" IS NULL OR "{n}" = \'\' LIMIT {SHOW}').fetchall()
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


def _parquet_names(path):
    import pyarrow.parquet as pq
    return list(pq.read_schema(path).names)


def _header(path):
    """The column names as the file's CSV header writes them (a Parquet table's unnamed index column: "")."""
    if str(path).endswith(".parquet"):
        return ["" if n.startswith("Unnamed: ") else n for n in _parquet_names(path)]
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh))


def _ncols(path):
    return len(_header(path))


def validate(root=ROOT, verbose=True, con=None, declarations_only=False):
    """All declarations under root/capri_data/schema checked; returns the violations as (where, kind, message).
    con: the connection to build the database in (a new in-memory one by default; tools/check/make_schema_json.py
    passes its own to read the catalogue afterwards). declarations_only: the tables are created and only the code
    lists (00_codes.sql) loaded, the rules are not run: the catalogue without the data checks."""
    import duckdb
    root = Path(root)
    con = con if con is not None else duckdb.connect()
    con.execute("CREATE TEMP TABLE _declared (file VARCHAR PRIMARY KEY, tbl VARCHAR)")   # for the rules
    found, declared = [], []
    for sql_file in sorted((root / "capri_data" / "schema").glob("*.sql")):
        for kind, arg, stmt in parse(sql_file.read_text(encoding="utf-8")):
            if kind == "table":
                con.execute(stmt)
                table = re.match(r"\s*CREATE\s+TABLE\s+(\w+)", stmt, re.I).group(1)
                path = root / arg
                declared.append(arg)
                con.execute("INSERT INTO _declared VALUES (?, ?)", [arg, table])
                if declarations_only and not sql_file.name.startswith("00_"):
                    continue
                if not path.exists():
                    found.append((arg, "file", "declared file missing"))
                    continue
                try:
                    for k, msg in check_table(con, table, path, layout(stmt)):
                        found.append((arg, k, msg))
                except duckdb.Error as e:                    # not a CSV the declaration can read (ragged lines)
                    found.append((arg, "file", str(e).splitlines()[0]))
            elif kind == "rule":
                if declarations_only:
                    continue
                rows = con.execute(stmt).fetchall()
                if rows:
                    found.append((f"{sql_file.name}: {arg}", "rule", f"{len(rows)} rows, e.g. {rows[:SHOW]}"))
            else:
                con.execute(stmt)
    if declarations_only:
        return found
    all_csv = sorted([str(p.relative_to(root)) for p in (root / "capri_data").rglob("*.csv") if "archive" not in p.parts]
                     + [str(p.relative_to(root)) for p in (root / "capri_data" / "sources").rglob("*.parquet")])
    found += [(f, "undeclared", "a data file under capri_data without a declaration") for f in all_csv
              if f not in set(declared)]
    found += [(str(p.relative_to(root)), "format", "a Parquet file outside capri_data/sources: the model's inputs are CSV")
              for p in (root / "capri_data").rglob("*.parquet") if "sources" not in p.relative_to(root / "capri_data").parts]
    found += catalogue_files(con, root)
    margin_found, margin_note = margins(root)
    found += margin_found
    if verbose:
        print(f"input margins: {margin_note}")
        print(f"{len(declared)} files declared of {len(all_csv)} data files under capri_data (CSV; Parquet under sources); "
              f"{len(found)} violations")
        for where, k, msg in found:
            print(f"  {where} [{k}] {msg}")
    return found


def catalogue_files(con, root):
    """The catalogue's files that are not CSV (JSON files, Parquet tables, folders; 05_file_catalogue.sql): each must
    exist (the CSV and Parquet tables are checked as declarations, rule in 99_rules.sql)."""
    try:
        rows = con.execute("SELECT file FROM file_catalogue WHERE file NOT LIKE '%.csv' ORDER BY file").fetchall()
    except Exception:                                    # no catalogue declared (a partial copy)
        return []
    return [(f, "catalogue", "catalogued file missing") for (f,) in rows if not (Path(root) / f).exists()]


#: the margin check (from the former MANIFEST.json validator, capri_mod/data/validate_data.py until 31 October 2026):
#: fodder and other non-marketed activities are left out; a staple crop whose gross margin with its CAP payments falls
#: below ARTIFACT_LOSS EUR/ha is a violation (a data error, as the sugar-price bug once was); specialty crops are
#: reported below their looser threshold, not counted as violations
NON_MARKET = {"GRAE", "GRAI", "MAIF", "OFAR", "ROOF", "VSET", "FALL"}
STAPLES = {"SWHE", "DWHE", "BARL", "CORN", "RYEM", "OATS", "RAPE", "SUNF", "SOYA", "POTA", "SUGB", "PULS"}
SPECIALTY = {"OVEG", "TOMA", "APPL", "OFRU", "CITR", "OLIV", "PULS", "TAGR", "TWIN", "TABO", "WINE"}
ARTIFACT_LOSS, ARTIFACT_LOSS_SPECIALTY = -1000.0, -8000.0


def margins(root):
    """Gross margins of the grown crops at the base (price x yield - cost + CAP payment per ha), as the supply module
    reads them: (violations, note). A negative market margin made good by the CAP payment is normal; a small loss
    after it may be real; a staple crop below ARTIFACT_LOSS is a violation."""
    import pandas as pd
    sys.path.insert(0, str(Path(root)))
    from capri_mod.data.loaders import resolve_data_file
    from capri_mod.tableio import read_input
    D = Path(root) / "capri_data"
    try:
        y = read_input(resolve_data_file(D, "yields.csv"), index_col=0)
        c = read_input(resolve_data_file(D, "variable_costs.csv"), index_col=0)
        areas = read_input(resolve_data_file(D, "base_areas.csv"), index_col=0)
        pr = read_input(resolve_data_file(D, "producer_prices.csv"), index_col=0)
        price = pr[pr.columns[0]]
        # the regional prices as the model reads them (2017/supply/producer_prices_regional.csv: CAPRI's MPRI with its
        # TWIN and OFAR columns and the national fallback; until 31 October 2026 the CAPREG extract without them)
        reg_price = read_input(resolve_data_file(D, "producer_prices_regional.csv"), index_col=0)
        cap = read_input(resolve_data_file(D, "cap_payments.csv"), index_col=0)
    except Exception as e:                               # a partial copy without the supply files
        return [], f"not checked ({str(e)[:60]})"
    # a cell that is not a number is a type violation of its declaration, reported there: here it is skipped
    num = lambda f: f.apply(pd.to_numeric, errors="coerce")  # noqa: E731
    y, c, areas, cap = num(y), num(c), num(areas), num(cap)
    price = pd.to_numeric(price, errors="coerce")
    reg_price = num(reg_price) if not reg_price.empty else reg_price
    cap_ha = cap.sum(axis=1) if cap.shape[1] > 1 else cap[cap.columns[0]]
    crops = [k for k in areas.columns if k in y.columns and k in c.columns and k in price.index and k not in NON_MARKET]
    supported, marginal, artifacts, checked = 0, [], [], 0
    for reg in areas.index:
        sub = float(cap_ha[reg]) if reg in cap_ha.index and pd.notna(cap_ha[reg]) else 0.0
        for crop in crops:
            grown = areas.at[reg, crop]
            if pd.isna(grown) or grown <= 1.0:
                continue
            p_ = price[crop]
            if pd.isna(p_):
                continue
            if (not reg_price.empty and reg in reg_price.index and crop in reg_price.columns
                    and pd.notna(reg_price.at[reg, crop]) and reg_price.at[reg, crop] > 0):
                p_ = float(reg_price.at[reg, crop])
            yld = y.at[reg, crop] if reg in y.index else None
            cost = c.at[reg, crop] if reg in c.index else None
            if yld is None or cost is None or pd.isna(yld) or pd.isna(cost):
                continue
            checked += 1
            m_ = float(yld) * float(p_) - float(cost)
            if m_ + sub >= 0:
                supported += m_ < 0
                continue
            lim = ARTIFACT_LOSS_SPECIALTY if crop in SPECIALTY else ARTIFACT_LOSS
            (artifacts if m_ + sub < lim else marginal).append((reg, crop, m_ + sub))
    staple = [a_ for a_ in artifacts if a_[1] in STAPLES]
    note = (f"{checked} grown region-crops; {supported} negative at market prices and made good by the CAP payment, "
            f"{len(marginal)} at a small loss after it, {len(artifacts) - len(staple)} specialty crops below "
            f"{ARTIFACT_LOSS_SPECIALTY:.0f} EUR/ha, {len(staple)} staple crops below {ARTIFACT_LOSS:.0f} EUR/ha")
    found = [(f"{r}/{k}", "margin", f"staple crop's gross margin after CAP {m:+.0f} EUR/ha") for r, k, m in
             sorted(staple, key=lambda t: t[2])]
    return found, note


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--db", default=None, help="also keep the database: a DuckDB file built anew at this path")
    a = ap.parse_args()
    con = None
    if a.db:
        import duckdb
        Path(a.db).unlink(missing_ok=True)
        con = duckdb.connect(a.db)
    found = validate(a.root, con=con)
    if con is not None:
        con.close()
        print(f"database kept: {a.db}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()

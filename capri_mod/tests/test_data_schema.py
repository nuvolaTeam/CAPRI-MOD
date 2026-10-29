"""The data declarations (capri_data/schema, tools/check/validate_data.py; docs/design/DATA_SCHEMA_DUCKDB.md): the
repository's data meet them, and every kind of violation is found, with the CSV line, in a damaged copy."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "check"))
duckdb = pytest.importorskip("duckdb")
import validate_data as V  # noqa: E402


def test_the_data_meet_their_declarations():
    assert V.validate(ROOT, verbose=False) == []


def _copy(tmp_path):
    """A checkout holding only the declarations and the files they name."""
    root = tmp_path / "repo"
    for sql in (ROOT / "capri_data" / "schema").glob("*.sql"):
        (root / "capri_data" / "schema").mkdir(parents=True, exist_ok=True)
        shutil.copy(sql, root / "capri_data" / "schema" / sql.name)
        for kind, arg, _ in V.parse(sql.read_text()):
            if kind == "table":
                (root / arg).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / arg, root / arg)
    return root


def _edit(root, rel, fn):
    p = root / rel
    lines = p.read_text().splitlines()
    p.write_text("\n".join(fn(lines)) + "\n")


def test_each_kind_of_violation_is_found_with_its_line(tmp_path):
    root = _copy(tmp_path)
    assert V.validate(root, verbose=False) == []
    acts, comms = "capri_data/schema/codes/model_activities.csv", "capri_data/schema/codes/model_commodities.csv"
    units = "capri_data/shared/regional_units.csv"
    # a duplicate key: line 2 repeated at the end
    _edit(root, acts, lambda l: l + [l[1]])
    # a code no list knows, at line 3
    _edit(root, comms, lambda l: l[:2] + [",".join([l[2].split(",")[0], "NOSUCH"] + l[2].split(",")[2:])] + l[3:])
    # a failed CHECK (country of two letters), at line 2
    _edit(root, units, lambda l: [l[0], ",".join(l[1].split(",")[:2] + ["XYZ"])] + l[2:])
    found = {(w, k): m for w, k, m in V.validate(root, verbose=False)}
    n_acts = len((root / acts).read_text().splitlines())
    assert f"at lines [2, {n_acts}]" in found[(acts, "keys")]
    assert "NOSUCH" in found[(comms, "refs")] and "line 3" in found[(comms, "refs")]
    assert "fails at lines [2]" in found[(units, "checks")]


def test_a_wrong_header_and_a_wrong_type_are_found(tmp_path):
    root = _copy(tmp_path)
    sql = root / "capri_data" / "schema" / "99_test.sql"
    (root / "t.csv").write_text("key,value\nA,1.5\nB,x\nC,\n")
    sql.write_text("-- file: t.csv\nCREATE TABLE t (key VARCHAR PRIMARY KEY, value DOUBLE NOT NULL CHECK (value >= 0));\n")
    found = V.validate(root, verbose=False)
    assert [(w, k) for w, k, _ in found] == [("t.csv", "types"), ("t.csv", "not null")]
    assert "line 3: 'x'" in found[0][2] and "[4]" in found[1][2]
    (root / "t.csv").write_text("value,key\n1,A\n")
    assert [k for _, k, _ in V.validate(root, verbose=False)] == ["columns"]

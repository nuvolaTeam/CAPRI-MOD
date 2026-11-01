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
    assert set(V.validate(root, verbose=False)) == set(V.validate(ROOT, verbose=False))   # the copy is the repository
    acts, comms = "capri_data/codes/model_activities.csv", "capri_data/codes/model_commodities.csv"
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
    base = V.validate(root, verbose=False)                 # the repository's own violations, if any, left aside
    sql = root / "capri_data" / "schema" / "99_test.sql"
    (root / "t.csv").write_text("key,value\nA,1.5\nB,x\nC,\n")
    sql.write_text("-- file: t.csv\nCREATE TABLE t (key VARCHAR PRIMARY KEY, value DOUBLE NOT NULL CHECK (value >= 0));\n")
    found = [x for x in V.validate(root, verbose=False) if x not in base]
    assert [(w, k) for w, k, _ in found] == [("t.csv", "types"), ("t.csv", "not null")]
    assert "line 3: 'x'" in found[0][2] and "[4]" in found[1][2]
    (root / "t.csv").write_text("value,key\n1,A\n")
    assert [k for x in V.validate(root, verbose=False) if x not in base for _, k, _ in [x]] == ["columns"]


def test_a_wide_file_is_checked_long(tmp_path):
    """A wide file (regions in rows, codes as columns) is read as (region, item, value): a bad value is named with its
    line and column; an unknown column header is a code no list knows, and the unit rule finds the item without unit."""
    root = _copy(tmp_path)
    y = "capri_data/2017/supply/yields.csv"
    first = lambda line, new: ",".join([line.split(",")[0], new] + line.split(",")[2:])  # noqa: E731
    _edit(root, y, lambda l: [l[0], first(l[1], "4.x")] + l[2:])
    found = {(w, k): m for w, k, m in V.validate(root, verbose=False)}
    assert "line 2 SWHE: '4.x'" in found[(y, "types")]
    _edit(root, y, lambda l: [l[0].replace(",SWHE,", ",XXXX,"), first(l[1], "4.5")] + l[2:])
    found = {(w, k): m for w, k, m in V.validate(root, verbose=False)}
    assert "XXXX" in found[(y, "refs")] and "not in model_activities" in found[(y, "refs")]
    rule = [m for (w, k), m in found.items() if k == "rule" and "unit declared" in w]
    assert rule and "('yields', 'SWHE', 'unit declared for an item not in the table')" in rule[0]


@pytest.mark.parametrize("tool", ["make_provenance.py", "make_code_data.py", "make_schema_json.py"])
def test_the_generated_declarations_are_up_to_date(tool):
    """01_provenance.sql (from the pipeline's trace), 03_code_data.sql (the numbers in the model's code) and schema.json
    (the declarations as JSON) are generated: each matches what its tool writes today."""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check" / tool), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]

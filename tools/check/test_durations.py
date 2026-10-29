"""Refresh capri_mod/tests/durations.json (the test order of conftest.py) from a test run's JUnit report.

    python -m pytest -n 2 --junitxml=run.xml
    python tools/check/test_durations.py run.xml [--min 5]
"""
from __future__ import annotations
import argparse
import datetime
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("junit")
    ap.add_argument("--min", type=float, default=5.0, help="keep tests at least this long (seconds)")
    a = ap.parse_args()
    d = {}
    for tc in ET.parse(a.junit).iter("testcase"):
        node = tc.get("classname").replace(".", "/") + ".py::" + tc.get("name")
        d[node] = round(float(tc.get("time") or 0.0), 1)
    d = {k: v for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if v >= a.min}
    out = ROOT / "capri_mod" / "tests" / "durations.json"
    out.write_text(json.dumps({"_note": f"seconds per test, from {Path(a.junit).name} ({datetime.date.today()}); "
                                        "conftest.py starts the longest first", "durations": d}, indent=1) + "\n")
    print(f"{len(d)} tests of at least {a.min} s written to {out}")


if __name__ == "__main__":
    main()

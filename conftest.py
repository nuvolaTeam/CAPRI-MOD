"""Test order: the tests measured longest start first (capri_mod/tests/durations.json), so that with parallel test
processes (python -m pytest -n 2) a long test does not start last and leave one process working alone; the others keep
their collection order. Durations are refreshed from a run's JUnit report with tools/check/test_durations.py."""
import json
from pathlib import Path

_DUR = Path(__file__).parent / "capri_mod" / "tests" / "durations.json"


def pytest_collection_modifyitems(config, items):
    try:
        dur = json.loads(_DUR.read_text()).get("durations", {})
    except (OSError, ValueError):
        return
    if not dur:
        return
    order = {it.nodeid: i for i, it in enumerate(items)}
    items.sort(key=lambda it: (-float(dur.get(it.nodeid, 0.0)), order[it.nodeid]))

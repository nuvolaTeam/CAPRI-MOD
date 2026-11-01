#!/usr/bin/env python3
"""Check that the counts the README states match the code and the data declarations.

Counts in prose drift as the model grows (the README said 32 market commodities after rice made it 33, and 51 tests
after the suite reached 56); each was found by a reader, not a check. This compares them with the code: the tests
pytest collects, the market commodities, the activities, and the data files declared under capri_data/schema
(capri_data/schema/schema.json, generated from the declarations).

Until 29 October 2026 the script also checked that every capability recorded in DATA_SOURCING_REGISTRY.json was
mentioned in the README or the CHANGELOG. The registry's log moved to docs/KNOWN_ISSUES_REGISTRY_LOG.md and the
registry was retired (its provenance notes are checked statements in capri_data/schema/02_provenance_notes.sql), so
that check went with it.

Exit codes: 0 = the counts match; 1 = at least one does not.

    python tools/check/check_doc_coverage.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Counts written into the README must match the code
# ---------------------------------------------------------------------------
# Counts in prose drift as the model grows: the README said 32 market
# commodities after rice made it 33, and 51 tests after the suite reached 56.
# Each was found by a reader, not a check. This compares them with the code.
def check_readme_counts(root: Path) -> list:
    import re, json, sys as _sys
    _sys.path.insert(0, str(root))
    from capri_mod.data.definitions import CROPS, ANIMALS, MARKET_COMMODITIES
    import ast as _ast
    # the tests as pytest collects them (both test folders of pyproject's testpaths, parametrized cases each counted),
    # the number the README states; without pytest the count is skipped. (Until 29 October 2026 the test functions of
    # capri_mod/tests were counted by parsing, which missed the pipeline tests and the parametrized cases: 199 against
    # pytest's 229.)
    readme = (root / "README.md").read_text()
    import subprocess as _sp
    try:
        _out = _sp.run([_sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=root,
                       capture_output=True, text=True, timeout=300).stdout
        _m = re.search(r"(\d+) tests? collected", _out)
        _n_tests = int(_m.group(1)) if _m else None
    except Exception:
        _n_tests = None
    actual = {
        "tests": _n_tests,
        "market commodities": len(MARKET_COMMODITIES),
        "activities": len(CROPS) + len(ANIMALS),
        "crops": len(CROPS),
        "livestock": len(ANIMALS),
        "declared data files": len(json.load(open(root / "capri_data" / "schema" / "schema.json"))["tables"]),
    }
    patterns = {
        "tests": [r"\| Test suite \| (\d+) tests"],
        "market commodities": [r"\| Market commodities \| (\d+) \|", r"\*\*(\d+) market\s+commodities\*\*"],
        "activities": [r"\| Activities \| (\d+) \(", r"\*\*(\d+) activities\*\*", r"over (\d+) activities"],
        "crops": [r"\((\d+) crops, \d+ livestock\)"],
        "livestock": [r"\(\d+ crops, (\d+) livestock\)"],
        "declared data files": [r"### 4\.2 The (\d+) declared data files", r"(\d+) declared data files"],
    }
    problems = []
    for what, pats in patterns.items():
        if actual[what] is None:
            continue
        for pat in pats:
            for m in re.finditer(pat, readme):
                if int(m.group(1)) != actual[what]:
                    problems.append(f"README says {m.group(1)} {what}; the code has {actual[what]}")
    return problems


def main() -> int:
    probs = check_readme_counts(Path(__file__).resolve().parents[2])
    for p in probs:
        print("  [COUNT] " + p)
    if probs:
        print("README counts disagree with the code - update the README.")
        return 1
    print("README counts (tests, commodities, activities, declared data files) match the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

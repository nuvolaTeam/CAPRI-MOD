#!/usr/bin/env python3
"""Check that capabilities recorded in the registry reach the user-facing docs.

Why this exists
---------------
Over the course of this project, every new capability went into
`DATA_SOURCING_REGISTRY.json` immediately and the README or CHANGELOG lagged —
five separate times, each caught by a human asking "did you update the docs?"
rather than by anything mechanical. The registry is where the work is recorded;
the README and CHANGELOG are what people actually read. An asymmetry that
reliable deserves a check rather than a resolution to remember.

This is the documentation equivalent of `check_regression.py`: it does not judge
whether the prose is good, only whether a capability or fix recorded as
significant is mentioned anywhere a reader would find it.

Exit codes
----------
0 = every flagged entry is mentioned in at least one user-facing document
1 = at least one is not

Usage
-----
    python tools/check_doc_coverage.py [--list]

``--list`` prints every checked entry and where it was found, rather than only
the failures.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = _ROOT / "capri_data" / "DATA_SOURCING_REGISTRY.json"
USER_DOCS = ("README.md", "CHANGELOG.md", "CAPRI_REFERENCE.md", "DATA_FIXES.md")

#: Entry natures that a reader should be able to find in the docs. Pure
#: investigations and verifications need not surface; new capabilities, fixed
#: bugs and acquired data must.
MUST_SURFACE = {
    "NEW_CAPABILITY", "STRUCTURAL_EXTENSION", "SILENT_FAILURE_BUG",
    "DESIGN_FIX", "DATA_ACQUIRED", "BUG_FOUND", "CALIBRATION_FIX",
    "DATA_INCONSISTENCY_BUG", "MEASUREMENT_ERROR_CORRECTED",
    "CORRECTION_OF_MY_OWN_ERROR", "NEW_INSTRUMENT",
}


def _keywords(name: str, entry: dict) -> list[str]:
    """Search terms that would indicate this entry is mentioned.

    Terms must be SPECIFIC. A first version split the registry key into words
    and matched them as substrings, which passed a deliberately-undocumented
    probe entry because "deliberate" occurs inside "deliberately" in the README.
    A checker that cannot fail is worse than none, so:

      * matching is on WORD BOUNDARIES, not substrings
      * single generic words are not enough on their own — an entry qualifies
        only via its full key, a file path it names, or a PAIR of its
        distinctive words appearing together in one document
    """
    stop = {"and", "the", "for", "with", "from", "not", "was", "are", "our",
            "its", "own", "new", "fix", "fixed", "bug", "data", "capri", "mod",
            "deliberate", "probe", "found", "error", "check", "test", "base"}
    parts = [p for p in re.split(r"[_\-]", name)
             if len(p) > 4 and p not in stop]
    note = json.dumps(entry)
    paths = re.findall(r"[a-z_]+/[a-z_]+\.(?:py|json)", note)[:3]
    return {"key": name.replace("_", " "), "words": parts, "paths": paths}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true",
                    help="show every checked entry, not only failures")
    args = ap.parse_args()

    registry = json.loads(REGISTRY.read_text())
    datasets = registry.get("datasets", {})

    corpus = {}
    for doc in USER_DOCS:
        path = _ROOT / doc
        corpus[doc] = path.read_text().lower() if path.exists() else ""

    checked, missing, found = 0, [], []
    for name, entry in datasets.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("nature", "") not in MUST_SURFACE:
            continue
        checked += 1
        k = _keywords(name, entry)

        def _mentions(text: str) -> bool:
            # the full key, spaced out, is an unambiguous mention
            if k["key"].lower() in text:
                return True
            # a file path the entry names is a strong, specific signal
            if any(pth.lower() in text for pth in k["paths"]):
                return True
            # otherwise require TWO distinctive words, on word boundaries,
            # in the same document
            seen = sum(1 for w in k["words"]
                       if re.search(r"\b" + re.escape(w.lower()) + r"\w{0,3}\b",
                                    text))
            return seen >= 2

        hits = [d for d, text in corpus.items() if _mentions(text)]
        if hits:
            found.append((name, hits))
        else:
            missing.append((name, entry.get("nature", "?")))

    print(f"Documentation coverage — {checked} entries require a mention\n")
    if args.list:
        for name, hits in found:
            print(f"  [ok  ] {name}  → {', '.join(hits)}")
        print()

    if missing:
        print(f"{len(missing)} recorded in the registry but NOT in any "
              "user-facing document:\n")
        for name, nature in missing:
            print(f"  [MISSING] {name}  ({nature})")
        print("\nThe registry is where the work is recorded; the README and "
              "CHANGELOG are what people read. Add a mention, or change the "
              "entry's nature if it genuinely need not surface.")
        return 1

    print(f"All {checked} entries are mentioned in at least one of: "
          f"{', '.join(USER_DOCS)}.")
    return 0


def _counts_gate() -> int:
    probs = check_readme_counts(Path(__file__).resolve().parent.parent)
    for p in probs:
        print("  [COUNT] " + p)
    if probs:
        print("README counts disagree with the code - update the README.")
        return 1
    print("README counts (tests, commodities, activities, inputs) match the code.")
    return 0





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
    # count tests by parsing, not importing: importing needs pytest, which a
    # documentation check should not depend on
    _tree = _ast.parse((root / "capri_mod" / "tests" / "test_capri.py").read_text())
    readme = (root / "README.md").read_text()
    actual = {
        "tests": sum(1 for n in _tree.body if isinstance(n, _ast.FunctionDef)
                     and n.name.startswith("test_")),
        "market commodities": len(MARKET_COMMODITIES),
        "activities": len(CROPS) + len(ANIMALS),
        "crops": len(CROPS),
        "livestock": len(ANIMALS),
        "declared inputs": len(json.load(open(root / "capri_data" / "INPUT_MANIFEST.json"))["inputs"]),
    }
    patterns = {
        "tests": [r"\| Test suite \| (\d+) tests"],
        "market commodities": [r"\| Market commodities \| (\d+) \|", r"\*\*(\d+) market\s+commodities\*\*"],
        "activities": [r"\| Activities \| (\d+) \(", r"\*\*(\d+) activities\*\*", r"over (\d+) activities"],
        "crops": [r"\((\d+) crops, \d+ livestock\)"],
        "livestock": [r"\(\d+ crops, (\d+) livestock\)"],
        "declared inputs": [r"### 4\.2 The (\d+) declared inputs", r"(\d+) declared inputs, each"],
    }
    problems = []
    for what, pats in patterns.items():
        for pat in pats:
            for m in re.finditer(pat, readme):
                if int(m.group(1)) != actual[what]:
                    problems.append(f"README says {m.group(1)} {what}; the code has {actual[what]}")
    return problems


if __name__ == "__main__":
    _rc = main()
    _rc2 = _counts_gate()
    sys.exit(_rc or _rc2)

"""The equation refactor's checks against CAPRI star 3.0 (docs/dev/MARKET_EQUATION_REFACTOR_PLAN.md section 4): every
quoted CAPRI GAMS block in the refactor's modules is star 3.0's text, and every line citation next to an equation's
name in the repository holds that equation in star 3.0 (tools/refactor/check_gams_quotes.py, check_gams_citations.py).

Skipped where CAPRI's GAMS sources are not at hand (capri_sources/gams or $CAPRI_SOURCES/gams, docs/EXTERNAL_SOURCES.md;
they are not in the repository) or are not star 3.0 (supply/supply_model.gms of 5,557 lines)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCES = Path(os.environ["CAPRI_SOURCES"]).expanduser().resolve() if os.environ.get("CAPRI_SOURCES") \
    else ROOT / "capri_sources"
GAMS = SOURCES / "gams"
STAR3_LINES = 5557


def _star3() -> Path:
    sm = GAMS / "supply" / "supply_model.gms"
    if not sm.exists():
        pytest.skip("CAPRI's GAMS sources are not at hand (capri_sources/gams)")
    n = len(sm.read_text(errors="replace").splitlines())
    if n != STAR3_LINES:
        pytest.skip(f"capri_sources/gams is not CAPRI star 3.0 (supply_model.gms has {n} lines)")
    return GAMS


def _run(tool: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "tools" / "refactor" / tool), *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=1800)


def test_quoted_gams_is_capri_star3s_text():
    g = _star3()
    r = _run("check_gams_quotes.py", str(g), "--expect", f"supply/supply_model.gms={STAR3_LINES}")
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]


def test_gams_citations_hold_their_equations():
    g = _star3()
    r = _run("check_gams_citations.py", str(g))
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]

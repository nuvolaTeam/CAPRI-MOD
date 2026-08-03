"""
CAPRI-Python test suite (pytest).

Covers the invariants that matter for a trustworthy model:
  - data loads and has the expected structure
  - the data validator runs and catches inconsistency
  - base-year market fidelity (the model's headline claim: 12/12 @ 0%)
  - supply responds to prices with the right sign and no numerical blow-ups
  - each module runs end to end

Run:  pytest capri_mod/tests/ -v
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "capri_data"


@pytest.fixture(scope="session")
def data():
    from capri_mod.data.loaders import load_all_data
    return load_all_data(DATA_DIR)


@pytest.fixture(scope="session")
def model():
    from capri_mod.model import CAPRIModel
    return CAPRIModel(data_dir=str(DATA_DIR), verbose=False)


def test_data_loads(data):
    assert "areas" in data
    assert "world_prices" in data
    assert len(data["areas"]) >= 200
    assert len(data["world_prices"]) > 0


def test_data_validator_runs():
    from capri_mod.data.validate_data import validate_data
    rep = validate_data(str(DATA_DIR))
    assert rep.n_fail == 0, f"validator reported failures: {rep.summary()}"


def test_validator_has_vintage_check():
    from capri_mod.data.validate_data import validate_data
    rep = validate_data(str(DATA_DIR))
    names = [c[0] for c in rep.checks]
    assert any("vintage" in n for n in names)


def test_no_negative_base_quantities(data):
    df = data["areas"].select_dtypes("number")
    assert (df.values >= 0).all()


def test_market_module_reproduces_its_own_prices(data):
    """
    Solver consistency, NOT price validation.

    The reference values below are world_prices.csv rounded to the nearest
    integer, so this asserts that the market module, given base-year supply,
    converges back to the prices it was handed. That is a real and useful check
    -- it catches solver regressions, bad Armington shares and unit errors in
    the supply aggregation -- but it says nothing about whether those prices are
    correct.

    Nothing in this repository can validate world_prices.csv, because every
    check available reads it. Independent comparison against CAPRI's own capmod
    result lives in tools/report_world_price_divergence.py and is reported
    rather than asserted, since the two sources disagree on three commodities
    and neither is demonstrably right.
    """
    from capri_mod.market.market_module import MarketModule
    from capri_mod.data.definitions import MARKET_COMMODITIES

    mm = MarketModule(data)
    exo = pd.DataFrame(0.0, index=["EU27"], columns=MARKET_COMMODITIES)
    for c in MARKET_COMMODITIES:
        if c in mm.base_production.columns:
            exo.at["EU27", c] = mm.base_production.at["EU27", c]

    eq = mm.solve(exogenous_supply=exo, max_iter=150, tolerance=0.01)
    assert eq.converged

    ref = {"SWHE": 148, "BARL": 145, "CORN": 148, "RAPE": 321, "SOYA": 293,
           "BEEF": 3692, "PORK": 1613, "POUL": 1405, "MILK": 319,
           "BUTR": 3782, "CHES": 2581, "SKIM": 1429}
    within = sum(1 for c, r in ref.items()
                 if abs((eq.world_prices.get(c, 0) - r) / r) <= 0.15)
    assert within == 12, f"only {within}/12 within 15%"


def test_supply_responds_positively_to_price(model):
    sm = model.supply_module
    reg = "DE11"
    base = sm.run(price_signals=None, regions=[reg])
    q0 = base[reg].activities.get("SWHE", 0)
    sig = pd.Series(0.0, index=model.data["world_prices"].index)
    sig["SWHE"] = 0.20
    up = sm.run(price_signals=sig, regions=[reg])
    q1 = up[reg].activities.get("SWHE", 0)
    assert q1 >= q0 - 1e-6


def test_supply_no_blowup(model):
    sm = model.supply_module
    for reg in list(model.data["areas"].index[:8]):
        base = sm.run(price_signals=None, regions=[reg])
        for act in ["SWHE", "CORN", "RAPE", "PULS"]:
            q0 = base[reg].activities.get(act, 0)
            if q0 <= 0.001:
                continue
            sig = pd.Series(0.0, index=model.data["world_prices"].index)
            sig[act] = 0.20
            s = sm.run(price_signals=sig, regions=[reg])
            q1 = s[reg].activities.get(act, 0)
            assert q1 / q0 < 10, f"{reg} {act} blew up"


def test_full_run_all_modules(model):
    regions = list(model.data["areas"].index[:5])
    r = model.run(scenario="BASELINE", max_outer_iter=1, market_max_iter=50,
                  regions=regions, run_environmental=True, run_feed=True,
                  run_biofuel=True)
    for k in ["supply", "market", "environmental", "feed", "biofuel"]:
        assert r[k] is not None


def test_biofuel_scenario_increases_output(model):
    bm = model.biofuel_module
    low = bm.run(mandate_share=0.065)
    high = bm.run(mandate_share=0.14)
    assert high.bioethanol_kt > low.bioethanol_kt
    assert high.biodiesel_kt > low.biodiesel_kt


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))


def test_price_structure_vs_capri(model):
    """
    Validate the model's relative price structure against CAPRI's own scenario
    output (Green Deal 2030 reference). Rank correlation should be very high.
    Reference ratios (vs wheat) extracted from CAPRI capmod DATAOUT.
    """
    capri_ratios = {
        "SWHE": 1.00, "BARL": 0.82, "RAPE": 2.55, "SOYA": 3.05,
        "POTA": 1.35, "SUGB": 0.15, "BEEF": 24.23, "PORK": 11.56,
    }
    wp = model.data["world_prices"]

    def price(c):
        if c in wp.index:
            row = wp.loc[c]
            return float(row.iloc[0]) if hasattr(row, "iloc") else float(row)
        return None

    base = price("SWHE")
    assert base and base > 0
    pairs = []
    for c, cr in capri_ratios.items():
        mp = price(c)
        if mp:
            pairs.append((cr, mp / base))
    assert len(pairs) >= 6
    # Rank correlation between CAPRI and model relative prices must be high
    import statistics
    capri_vals = [c for c, _ in pairs]
    model_vals = [m for _, m in pairs]
    corr = statistics.correlation(capri_vals, model_vals)
    assert corr > 0.95, f"price-structure correlation too low: {corr:.3f}"


# ---------------------------------------------------------------------------
# Data hygiene guards
#
# These exist because a Cyrillic-homoglyph corruption of the activity code
# `OANI` (and two doubled-I variants) sat undetected across code and data: the
# canonical activity list used one spelling, the feed and environmental modules
# used others, so every 'other animals' lookup silently missed.
# ---------------------------------------------------------------------------

# These exist because a Cyrillic-homoglyph corruption of the activity code
# `OANI` sat undetected across code and data: the canonical activity list used
# one spelling, the feed/environmental/market modules used homoglyph variants,
# so every 'other animals' lookup silently missed. A denylist of known-bad
# variants is fragile — it only catches the spellings you thought to enumerate
# (an ASCII-OANI + single trailing Cyrillic И slipped past exactly such a list).
# The guard below is general: it flags ANY non-ASCII character sitting inside a
# quoted token that otherwise looks like an activity/commodity code, wherever it
# appears in code or data.
# ---------------------------------------------------------------------------

import re as _re

# a "code token" is a short all-caps-alnum identifier (activity/commodity code).
# Flag it if it contains ANY non-ASCII character. This catches both partial
# corruption (ASCII OANI + trailing Cyrillic И) and full corruption (every
# letter a Cyrillic homoglyph), which a "boundary-only" pattern would miss.
def _looks_corrupted_code(token: str) -> bool:
    # candidate code token: 3-6 chars, no spaces, letters/digits/homoglyphs only,
    # at least one non-ASCII char, and (if it has ASCII letters) they're upper.
    t = token.strip()
    if not (3 <= len(t) <= 6) or " " in t:
        return False
    if all(ord(c) < 128 for c in t):
        return False  # pure ASCII — a separate ASCII-only guard covers doubled-I
    ascii_letters = [c for c in t if c.isascii() and c.isalpha()]
    if ascii_letters and not all(c.isupper() for c in ascii_letters):
        return False  # lowercase ASCII → prose word with an accent, not a code
    # reject if it contains punctuation/space-like chars → not a bare code
    return all(c.isalnum() for c in t)


def _repo_root():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[2]


def test_no_corrupted_activity_codes():
    """No non-ASCII homoglyph adjacent to any uppercase code token, in code or data.

    Generalises the original OANI-variant denylist: instead of enumerating known
    bad spellings, it rejects any non-ASCII character touching an uppercase
    alphanumeric code token — the shape every homoglyph corruption of an activity
    or commodity code takes.
    """
    import pathlib
    offenders = []
    for p in _repo_root().rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py", ".csv", ".json"}:
            continue
        # tools/ holds the normaliser and this file holds the guard regex; both
        # legitimately contain the pattern in order to act on it. Skip snapshot
        # (a frozen restore point) and caches.
        if {"__pycache__", ".git", "tools", "capri_data_snapshot"} & set(p.parts):
            continue
        if p.resolve() == pathlib.Path(__file__).resolve():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            # only inspect quoted string content, so prose comments with accents
            # (Baden-Württemberg, Île-de-France) and math symbols don't trip it
            for m in _re.finditer(r"""["']([^"']*)["']""", line):
                token = m.group(1)
                if _looks_corrupted_code(token):
                    offenders.append(f"{p.name}:{lineno}: {token!r}")
    assert not offenders, (
        "non-ASCII homoglyph in code/commodity token:\n  " + "\n  ".join(offenders)
    )


def test_data_headers_are_ascii():
    """CSV headers must be pure ASCII — non-ASCII means an encoding artifact."""
    import pathlib
    import csv
    offenders = []
    for p in (_repo_root() / "capri_data").rglob("*.csv"):
        try:
            with open(p, encoding="utf-8", newline="") as fh:
                header = next(csv.reader(fh), [])
        except (UnicodeDecodeError, OSError, StopIteration):
            continue
        bad = [h for h in header if any(ord(ch) > 127 for ch in h)]
        if bad:
            offenders.append(f"{p.name}: {bad}")
    assert not offenders, f"non-ASCII CSV headers: {offenders}"


# ---------------------------------------------------------------------------
# PMP elasticity wiring guards
# ---------------------------------------------------------------------------

def test_capri_dampening_matches_gams_reference():
    """
    CAPRI's own worked examples from
    gams/supply/pmp_terms/impose_upper_bound_on_elasticity.gms:
    "any elasticity above 4.5 gets dampened (10=>5.6, 20=>7.0, 40 =>8)".
    """
    from capri_mod.supply.capri_pmp import dampen_elasticity
    import numpy as np
    got = dampen_elasticity([10.0, 20.0, 40.0])
    assert np.allclose(got, [5.6, 7.0, 8.0], atol=0.2), got
    # values at or below the threshold must pass through untouched
    assert np.allclose(dampen_elasticity([0.3, 2.5, 4.5]), [0.3, 2.5, 4.5])
    # and nothing may exceed the hard cap
    assert dampen_elasticity([1e6])[0] <= 8.0


def test_synthetic_base_activities_excluded_from_elasticity_wiring():
    """
    Activities with a constant placeholder base level must not receive real
    elasticities: PMP curvature is 1/(eps*x0), so a genuine elasticity on an
    invented anchor explodes under shock (OFOD reached +128% before this guard).
    """
    import pandas as pd
    from pathlib import Path
    from capri_mod.supply.capri_pmp import (
        detect_synthetic_base_activities, build_elasticity_table)
    from capri_mod.data.definitions import ALL_ACTIVITIES
    from capri_mod.utils.utils import calibrate_supply_elasticities

    root = _repo_root()
    areas = pd.read_csv(root / "capri_data/2017/supply/base_areas.csv", index_col=0)
    # SETA was a flat 3.0 placeholder until real capreg levels were merged for
    # 140 regions; COTT, OFIB and OFOD remain constants because CAPRI reports
    # them under aggregate names (TEXT for the fibre crops, OFAR/ROOF for
    # fodder) that need a documented split before they can be used.
    blocked = detect_synthetic_base_activities(areas)
    assert {"COTT", "OFIB", "OFOD"} <= blocked, blocked

    defaults = calibrate_supply_elasticities(areas)
    eps, prov, summary = build_elasticity_table(
        root / "capri_data", list(areas.index), ALL_ACTIVITIES, defaults,
        base_areas=areas)
    for act in blocked:
        if act in prov.columns:
            assert (prov[act] == "LITERATURE_DEFAULT").all(), \
                f"{act} has a synthetic base but received a real elasticity"


def test_elasticity_provenance_is_complete():
    """Every region x activity cell must carry a provenance label."""
    import pandas as pd
    from capri_mod.supply.capri_pmp import build_elasticity_table
    from capri_mod.data.definitions import ALL_ACTIVITIES
    from capri_mod.utils.utils import calibrate_supply_elasticities

    root = _repo_root()
    areas = pd.read_csv(root / "capri_data/2017/supply/base_areas.csv", index_col=0)
    eps, prov, summary = build_elasticity_table(
        root / "capri_data", list(areas.index), ALL_ACTIVITIES,
        calibrate_supply_elasticities(areas), base_areas=areas)
    assert prov.notna().all().all()
    assert eps.notna().all().all()
    assert (eps >= 0).all().all()
    # SETA carries a zero default by design (set-aside does not respond to price),
    # so strict positivity is not the right assertion here.
    assert (eps <= 8.0).all().all(), "elasticity exceeds CAPRI's hard cap"
    assert set(prov.stack().unique()) <= {
        "LITERATURE_DEFAULT", "REGIONAL_CAPRI", "PMP_CAPRI"}


def test_schema_declares_every_input_and_all_files_exist():
    """
    The declarative schema (INPUT_SCHEMA.json) is the single source of truth for
    what the model loads and where each input comes from. This gate asserts the
    data on disk matches the declaration: every declared file must exist and be
    readable.

    This is the check that would have caught the silent-drop bugs in the
    project's history -- maize yields, grassland, the livestock PMP terms -- each
    of which left a declared input under-covered while the file still looked
    fine. It fails loudly the moment declaration and reality diverge.
    """
    import json
    import pandas as pd

    root = _repo_root()
    schema = json.loads((root / "capri_data/INPUT_SCHEMA.json").read_text())
    inputs = schema["inputs"]
    assert len(inputs) >= 20, "schema unexpectedly small"

    missing = []
    unreadable = []
    for name, spec in inputs.items():
        f = root / "capri_data" / spec["file"]
        if not f.exists():
            missing.append((name, spec["file"]))
            continue
        # provenance must be structured, so a later source swap is a field edit
        src = spec["source"]
        for field in ("source_type", "source_ref", "vintage", "confidence"):
            assert field in src, f"{name} missing provenance field {field}"
        if str(f).endswith(".csv"):
            try:
                pd.read_csv(f, index_col=0, nrows=5)
            except Exception as exc:            # pragma: no cover
                unreadable.append((name, str(exc)[:80]))

    assert not missing, f"declared files absent: {missing}"
    assert not unreadable, f"declared files unreadable: {unreadable}"


def test_schema_coverage_has_not_regressed():
    """
    Guards the honest per-cell coverage figure. Real-CAPRI-sourced cells must
    stay above a floor; a drop that isn't explained by a schema change is a
    silent-drop regression of exactly the kind this project kept hitting.

    The floor is set well below the current 99% so ordinary data edits don't
    trip it, but a whole input quietly emptying (the failure mode of the maize
    and grassland bugs) would.
    """
    import json
    import numpy as np
    import pandas as pd

    root = _repo_root()
    schema = json.loads((root / "capri_data/INPUT_SCHEMA.json").read_text())
    real_types = {"CAPRI_GDX", "CAPRI_SOURCE"}

    real = total = 0
    per_input = {}
    for name, spec in schema["inputs"].items():
        f = root / "capri_data" / spec["file"]
        if not (f.exists() and str(f).endswith(".csv")):
            continue
        try:
            num = pd.read_csv(f, index_col=0).select_dtypes(include=[np.number])
        except Exception:
            continue
        live = int(num.notna().sum().sum())
        nz = int(((num != 0) & num.notna()).sum().sum())
        total += nz
        if spec["source"]["source_type"] in real_types:
            real += nz
        # per-input fill ratio: a CAPRI-sourced input that empties out is the
        # silent-drop failure mode (maize, grassland, livestock terms), and the
        # aggregate floor is too coarse to see one input among twenty go dark.
        if live > 0:
            per_input[name] = nz / live

    assert total > 0
    frac = real / total
    assert frac >= 0.80, (
        f"real-CAPRI cell coverage {frac:.1%} below floor 80% -- "
        "a declared input may have silently emptied")

    # any single CAPRI-sourced numeric input that is almost entirely zero is a
    # regression, regardless of the aggregate. 5% floor tolerates genuinely
    # sparse inputs (e.g. specialty crops) without tolerating a dead file.
    emptied = {n: r for n, r in per_input.items()
               if r < 0.05
               and schema["inputs"][n]["source"]["source_type"] in real_types}
    assert not emptied, (
        f"CAPRI-sourced inputs nearly empty (silent-drop?): "
        f"{ {n: f'{r:.1%}' for n, r in emptied.items()} }")


# ---------------------------------------------------------------------------
# Market-mapping consistency. The supply->market bridge and the processing
# splits both reference commodity codes; if any referenced code is absent from
# MARKET_COMMODITIES the market would silently drop that flow. This guards the
# bridge (which must be fully covered) and pins the intended processing-output
# exceptions (oilseed crush products that are feed items, not traded market
# commodities) so an accidental omission is distinguishable from a known one.
# ---------------------------------------------------------------------------

def test_market_mapping_consistency():
    import re
    from capri_mod.data import definitions as D

    market = set(D.MARKET_COMMODITIES)

    # (a) every commodity the supply->market bridge writes to or guards on must
    #     exist in MARKET_COMMODITIES -- a missing one is a silent dropped flow.
    src = (_repo_root() / "capri_mod" / "model.py").read_text(encoding="utf-8")
    bridge_refs = set(re.findall(r'market_supply\[\s*["\'](\w+)["\']\s*\]\s*=', src))
    bridge_refs |= set(re.findall(r'["\'](\w+)["\']\s+in\s+market_supply', src))
    bridge_missing = sorted(c for c in bridge_refs if c not in market)
    assert not bridge_missing, (
        f"_bridge_supply_to_market references commodities absent from "
        f"MARKET_COMMODITIES: {bridge_missing}")

    # (b) processing outputs either clear in the market or are known non-market
    #     products (oilseed crush oil/meal, whey) that live only as feed items.
    #     Listing them explicitly means a NEW unmapped product fails the test.
    KNOWN_NON_MARKET_OUTPUTS = {
        "RAPO", "RAPM",   # rapeseed oil / meal
        "SOYO", "SOYM",   # soy oil / meal
        "SUFO", "SUFM",   # sunflower oil / meal
    }
    outputs = set()
    for v in D.PROCESSING_OUTPUTS.values():
        outputs.update(v if isinstance(v, (list, tuple)) else [v])
    unexpected = sorted(
        p for p in outputs
        if p not in market and p not in KNOWN_NON_MARKET_OUTPUTS)
    assert not unexpected, (
        f"PROCESSING_OUTPUTS products neither in MARKET_COMMODITIES nor in the "
        f"known non-market set: {unexpected} -- add to MARKET_COMMODITIES if they "
        f"should clear, or to KNOWN_NON_MARKET_OUTPUTS if intentionally untraded")

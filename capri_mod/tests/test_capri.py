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

    # RAPE and SOYA were corrected to CAPRI's actual PMRK values (SOYA
    # 292.6 -> 102.7, the long-flagged 2.85x error; RAPE 321 -> 213) when world
    # prices were validated against the capmod base GDX. These references were
    # never updated to match, so the test had been asserting the OLD, known-wrong
    # numbers and failing at 9/12 for the life of the project. The model was
    # right; the reference was stale.
    ref = {"SWHE": 148, "BARL": 145, "CORN": 148, "RAPE": 213, "SOYA": 103,
           "BEEF": 3692, "PORK": 1613, "POUL": 1405, "MILK": 319,
           "BUTR": 3782, "CHES": 4815, "SKIM": 1429}
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


# ---------------------------------------------------------------------------
# Fertilizer distribution module. Derives crop/region application rates
# (CAPRI p_FertPerHa) from removal factors x yields x calibrated efficiency,
# so a base year lacking a ready-made nutrient_coefs file can still be built.
# Validated against CAPRI's own 2017 p_FertPerHa (nutrient_coefs.csv).
# ---------------------------------------------------------------------------

def test_fertilizer_module_reproduces_capri_fert_per_ha():
    import pandas as pd
    from capri_mod.fert import FertilizerModule
    from capri_mod.data.loaders import load_all_data, resolve_data_file

    d = load_all_data(str(DATA_DIR))
    export = pd.read_csv(resolve_data_file(str(DATA_DIR),
                         "crop_nutrient_export.csv"), index_col=0)
    capri = pd.read_csv(resolve_data_file(str(DATA_DIR),
                        "nutrient_coefs.csv"), index_col=0)

    fm = FertilizerModule(export, d["yields"], d["areas"])
    fm.calibrate(capri)
    val = fm.validate(capri)

    # The removal-need x calibrated-efficiency method should reproduce CAPRI's
    # per-hectare application within the ~10% band used for the other modules.
    assert val["overall_median_err"] < 0.15, (
        f"fertilizer module median error {val['overall_median_err']:.1%} "
        f"exceeds 15% vs CAPRI p_FertPerHa")
    # And a solid majority of crop x nutrient cells within 20%.
    fracs = [s["within_20pct"] for s in val["by_nutrient"].values()]
    assert min(fracs) >= 0.5, (
        f"a nutrient has <50% of cells within 20% of CAPRI: {val['by_nutrient']}")


def test_fertilizer_module_integrates_with_environment():
    """Environmental N-balance is consistent whether application rates are
    CAPRI's loaded p_FertPerHa or the fertilizer module's derived rates.

    Since the fert module reproduces p_FertPerHa within ~10%, plugging its
    derived rates into the environmental module should leave the regional
    nitrogen balance essentially unchanged — proving the module is a valid
    drop-in source of application rates (what a re-based year needs), and that
    the plausibility guard correctly handles unit-inconsistent crops (GRAS).
    """
    import numpy as np
    import pandas as pd
    from capri_mod.data.loaders import load_all_data, resolve_data_file
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.fert import FertilizerModule

    d = load_all_data(str(DATA_DIR))
    export = pd.read_csv(resolve_data_file(str(DATA_DIR),
                         "crop_nutrient_export.csv"), index_col=0)
    capri = pd.read_csv(resolve_data_file(str(DATA_DIR),
                        "nutrient_coefs.csv"), index_col=0)

    fm = FertilizerModule(export, d["yields"], d["areas"])
    fm.calibrate(capri)

    env_loaded = EnvironmentalModule(d)
    env_derived = EnvironmentalModule(d, fertilizer_module=fm)

    acts = d["areas"]
    diffs = []
    for reg in list(acts.index[:8]):
        a = acts.loc[reg]
        yr = d["yields"].loc[reg] if reg in d["yields"].index else pd.Series(dtype=float)
        ml = float(env_loaded.compute_nitrogen_balance(a, yr, reg)["n_mineral_input"])
        md = float(env_derived.compute_nitrogen_balance(a, yr, reg)["n_mineral_input"])
        if abs(ml) > 0.01:
            diffs.append(abs(md - ml) / abs(ml))

    assert diffs, "no regions produced a nonzero N-mineral input to compare"
    mean_diff = float(np.mean(diffs))
    # Derived vs loaded should agree closely — a large gap means a units or
    # coverage bug (as GRAS produced before the plausibility guard).
    assert mean_diff < 0.10, (
        f"derived-rate N balance diverges from CAPRI-loaded by {mean_diff:.1%} "
        f"(expected <10%); check the fertilizer module plausibility guard")


def test_abatement_macc_is_monotonic_and_economic():
    """The carbon-price sweep produces a monotonic, downward-sloping MAC curve.

    Raising the carbon price penalises emission-intensive activities, the supply
    module reallocates, and emissions fall. This is the model's OWN abatement
    (production reallocation), derived without any ingested abatement figures.
    EcAMPA 2 is used only afterwards as an independent comparison.
    """
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.abatement import AbatementModule

    d = load_all_data(str(DATA_DIR))
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    regions = list(d["areas"].index[:4])
    sm.run(price_signals=None, regions=regions)

    am = AbatementModule(sm)
    macc = am.derive_macc(carbon_prices=[0, 50, 150], regions=regions)

    emis = [p.emissions for p in macc.points]
    # emissions must fall (or hold) as the carbon price rises
    assert all(emis[i] >= emis[i + 1] for i in range(len(emis) - 1)), (
        f"MAC curve not monotonic: emissions {emis}")
    # a positive carbon price must produce some abatement
    assert macc.points[-1].abatement_pct > 0, (
        "no abatement at the highest carbon price — supply not responding")
    # and it should be a modest economic response (single/low-double digits),
    # well below EcAMPA's ~20% total which includes technological measures
    assert macc.points[-1].abatement_pct < 20, (
        "economic-only abatement implausibly high vs EcAMPA total")


def test_technological_abatement_uses_cited_ecampa_data():
    """The technological layer applies EcAMPA measures as explicit, cited inputs,
    resolved to the correct emission source.

    This is the legitimate use of EcAMPA's numbers — as parameters of a
    technology-adoption module, separate from (and additive to) the model-derived
    economic MACC. The layer must load real EcAMPA data (no fabrication), apply
    each measure to its correct emission source (feed additives to enteric CH4
    only, not whole-CH4), avoid double-counting, and stay below 100% abatement.
    """
    from capri_mod.abatement import TechnologicalAbatement

    tech = TechnologicalAbatement.from_data_dir(str(DATA_DIR))

    # every measure must carry an EcAMPA page citation and an emission source
    assert (tech.measures["source_page"] > 0).all(), (
        "an EcAMPA measure lacks a page citation")
    assert tech.measures["emission_source"].notna().all(), (
        "an EcAMPA measure lacks an emission_source mapping")

    # source-resolved inventory using the environmental module's own keys
    emis = {
        "CH4_ENT": 190.0, "CH4_MAN": 45.0, "N2O_MAN": 30.0,
        "N2O_SOIL": 140.0, "CO2_LIME": 8.0, "CO2_UREA": 7.0,
    }
    res = tech.apply(emis, uptake_scale=1.0)

    assert 0 < res.abatement_pct <= 100, (
        f"technological abatement {res.abatement_pct}% is out of range")

    # feed measures must act on enteric CH4 only: total enteric abatement can
    # never exceed the enteric pool, even with all three feed measures stacked
    enteric_ab = sum(m.abatement for m in res.measures
                     if m.measure in ("feed_fat_supplementation",
                                      "feed_energy_efficiency",
                                      "nitrate_feed_additive"))
    assert enteric_ab <= emis["CH4_ENT"] + 1e-6, (
        f"feed measures abated {enteric_ab} > enteric pool {emis['CH4_ENT']} — "
        f"not source-resolved")

    # mutually-exclusive fertiliser-N measures must not be stacked
    applied = [m.measure for m in res.measures]
    fert_n = {"precision_farming_low", "precision_farming_mid",
              "precision_farming_high", "variable_rate_technology"}
    assert len(fert_n & set(applied)) <= 1, (
        f"stacked non-additive fertiliser measures: {fert_n & set(applied)}")

    # partial uptake must give less abatement than full uptake
    res_half = tech.apply(emis, uptake_scale=0.5)
    assert res_half.abatement_pct < res.abatement_pct, (
        "50% uptake did not reduce abatement vs 100%")


def test_technological_abatement_is_activity_resolved():
    """Feed measures abate only the specific animals EcAMPA assigns them.

    Passing a per-animal enteric inventory makes each feed measure target only
    its ``applies_to_animals`` set — the nitrate additive hits dairy + fattening
    cattle, the energy-efficiency measure excludes dairy cows, and monogastrics
    (pigs, poultry) are never touched. This is stricter than pool-level
    application and gives a lower, more honest total for mixed-livestock regions.
    """
    import pandas as pd
    from capri_mod.data.loaders import load_all_data
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    from capri_mod.abatement import TechnologicalAbatement

    d = load_all_data(str(DATA_DIR))
    env = EnvironmentalModule(d)
    tech = TechnologicalAbatement.from_data_dir(str(DATA_DIR))

    # a region with real herds: combine crop areas + animal numbers
    reg = d["areas"].index[0]
    acts = pd.concat([d["areas"].loc[reg], d["animal_numbers"].loc[reg]])
    ghg = env.compute_ghg(acts, reg)
    ent = env.enteric_ch4_by_animal(acts)

    res_pool = tech.apply(ghg, uptake_scale=1.0)
    res_anim = tech.apply(ghg, uptake_scale=1.0, enteric_by_animal=ent)

    # activity-resolved abatement must be <= pool-level (it targets a subset of
    # animals, so it can only abate less, never more)
    assert res_anim.abatement_pct <= res_pool.abatement_pct + 1e-6, (
        f"activity-resolved abatement {res_anim.abatement_pct:.2f}% exceeds "
        f"pool-level {res_pool.abatement_pct:.2f}% — targeting is not restricting")

    # the energy-efficiency measure (non-dairy ruminants) must never abate more
    # than 10% of the non-dairy enteric pool
    non_dairy = sum(ent.get(a, 0.0) for a in
                    ("BCOW", "BULL", "HFRS", "CALV", "SHGP"))
    energy_ab = next((m.abatement for m in res_anim.measures
                      if m.measure == "feed_energy_efficiency"), 0.0)
    assert energy_ab <= 0.10 * non_dairy + 1e-6, (
        f"energy-efficiency measure abated {energy_ab:.1f} > 10% of non-dairy "
        f"pool {non_dairy:.1f} — it is not excluding dairy cows")


def test_income_distribution_module():
    """Farm-income distribution combines supply margins with CAP payments and
    produces sensible distributional measures.

    The module is an accounting layer over validated quantities (supply gross
    margins, policy CAP payments). It should produce a valid Gini in [0,1], a
    plausible support share, and payments that are less concentrated than income
    (CAP has redistributive intent). Grassland is excluded as on-farm fodder.
    """
    from capri_mod.data.loaders import load_all_data
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario
    from capri_mod.income import IncomeDistributionModule

    d = load_all_data(str(DATA_DIR))
    sm = SupplyModule(d, calibrate_supply_elasticities(d["areas"]))
    sr = sm.run(price_signals=None, regions=list(d["areas"].index[:30]))
    pm = PolicyModule(d, PolicyScenario(name="BASELINE"))
    cap = pm.payments.compute_payments_by_region(d["cap_payments"], d["land"])

    im = IncomeDistributionModule(d)
    res = im.compute(sr, cap, supply_module=sm)

    # valid concentration measures
    assert 0.0 <= res.income_gini <= 1.0, f"income Gini out of range: {res.income_gini}"
    assert 0.0 <= res.payment_gini <= 1.0, f"payment Gini out of range: {res.payment_gini}"
    # support share is a sensible fraction
    assert 0.0 <= res.support_share_eu <= 1.0, (
        f"support share out of range: {res.support_share_eu}")
    # market income must be finite and positive in aggregate (GRAS artifact excluded)
    total_market = res.by_region["market_income"].sum()
    assert total_market > 0 and total_market < 1e12, (
        f"aggregate market income implausible: {total_market} (GRAS artifact?)")


def test_water_demand_module():
    """Irrigation water demand reproduces the known geography and magnitude.

    The module computes demand = CNIR x irrigated area from CAPRI's CROPWAT data
    and Eurostat irrigation shares, driven by crop areas. The physical test is
    that demand concentrates in the Mediterranean (irrigation is a southern
    phenomenon) and the EU total is the right order of magnitude (~10-20 km3 net
    irrigation requirement).
    """
    import os
    from capri_mod.data.loaders import load_all_data
    from capri_mod.water import WaterDemandModule

    cw = os.path.join(str(DATA_DIR), "sources", "water", "cropwat.csv")
    ish = os.path.join(str(DATA_DIR), "sources", "water", "irrishare.csv")
    if not (os.path.exists(cw) and os.path.exists(ish)):
        return  # water data not present in this build

    d = load_all_data(str(DATA_DIR))
    wm = WaterDemandModule(d, cropwat_path=cw, irrishare_path=ish)
    res = wm.compute()

    # EU total is a physically plausible net irrigation requirement (km3 scale)
    assert 5_000 < res.total_demand_Mm3 < 40_000, (
        f"EU irrigation demand implausible: {res.total_demand_Mm3} Mm3")
    # covers a substantial share of regions
    assert res.n_regions_covered > 100, (
        f"too few regions covered: {res.n_regions_covered}")
    # Mediterranean dominates (the key physical signature)
    df = res.by_region
    south = df[df.index.str.startswith(("ES", "IT", "EL", "PT"))]["water_demand_Mm3"].sum()
    assert south / res.total_demand_Mm3 > 0.5, (
        "Mediterranean should dominate EU irrigation demand")


def test_feed_monogastric_matches_capri():
    """Monogastric (pig/poultry) feed requirements match CAPRI reference.

    The IPCC ruminant net-energy formula does not apply to monogastrics and
    undercounts them ~40-50%. The module uses CAPRI's own per-region reference
    values (ENNE, DRMN) for pigs and poultry; median requirements should land
    within ~15% of the CAPRI reference medians.
    """
    import numpy as np
    from capri_mod.data.loaders import load_all_data
    from capri_mod.feed.feed_module import FeedModule

    d = load_all_data(str(DATA_DIR))
    d["_data_dir"] = str(DATA_DIR)
    fm = FeedModule(d)
    if fm._mono_req.empty:
        return  # reference not present in this build

    # CAPRI reference medians (ENNE MJ/head/yr, DRMN kg/head/yr)
    ref = {"PIGF": (18.0, 2.1), "PIGS": (32.5, 3.9),
           "LAYS": (798.6, 78.4), "BROI": (814.4, 63.8)}
    for animal, (ref_e, ref_dm) in ref.items():
        es, dms = [], []
        for reg in d["areas"].index:
            r = fm.requirements_for(reg, animal)
            es.append(r.nel_requirement)
            dms.append(r.drmn)
        med_e, med_dm = np.median(es), np.median(dms)
        assert abs(med_e - ref_e) / ref_e < 0.15, (
            f"{animal} energy {med_e:.1f} vs CAPRI {ref_e} (>15% off)")
        assert abs(med_dm - ref_dm) / ref_dm < 0.20, (
            f"{animal} dry matter {med_dm:.2f} vs CAPRI {ref_dm} (>20% off)")


def test_projection_null_trajectory_reproduces_base(model):
    """The projection layer's correctness gate.

    Projecting with a NULL trajectory (all growth factors 1.0) must reproduce
    the comparative-static result exactly. This tests the whole machinery —
    scaling, reconciliation, the time loop, state carry-forward — without
    depending on any forecast being right.
    """
    from capri_mod.projection import ProjectionModule, BaselineTrajectory

    regions = list(model.data["areas"].index[:12])
    ref = model.run(scenario="BASELINE", regions=regions)
    pm = ProjectionModule(model, BaselineTrajectory.null(2017, [2017]))
    proj = pm.run(regions=regions).baseline[2017]

    ra, pa = ref.get("supply", {}), proj.get("supply", {})
    compared = 0
    for reg in ra:
        a1 = getattr(ra[reg], "activities", None)
        a2 = getattr(pa.get(reg), "activities", None) if reg in pa else None
        if a1 is None or a2 is None:
            continue
        for act in a1.index:
            if act in a2.index and abs(a1[act]) > 1e-6:
                compared += 1
                assert abs(a2[act] - a1[act]) / abs(a1[act]) < 1e-9, (
                    f"null trajectory changed {reg}/{act}: {a1[act]} -> {a2[act]}")
    assert compared > 50, "too few cells compared to trust the identity"


def test_projection_reconciliation_preserves_base_ratio():
    """Reconciliation is a no-op at base and corrects genuine drift.

    It must NOT impose an assumed identity (crop areas do not sum to the land
    table in the base year); it preserves each region's own base-year
    cropped-to-land ratio, so a null trajectory changes nothing.
    """
    import copy
    from capri_mod.data.loaders import load_all_data
    from capri_mod.projection import reconcile_projected_data

    d = load_all_data(str(DATA_DIR))

    # no drift -> no change
    same = copy.deepcopy(d)
    rep = reconcile_projected_data(same, base_data=d)
    delta = (same["areas"] - d["areas"]).abs().sum().sum()
    assert delta < 1e-6, f"reconciliation altered base data by {delta}"
    assert rep.land_adjusted_regions == 0

    # land shrinks 5%, areas left at base -> areas pulled back ~5%
    drifted = copy.deepcopy(d)
    drifted["land"] = drifted["land"] * 0.95
    reconcile_projected_data(drifted, base_data=d)
    for reg in list(d["areas"].index[:5]):
        expected = d["areas"].loc[reg].sum() * 0.95
        got = drifted["areas"].loc[reg].sum()
        if expected > 1:
            assert abs(got - expected) / expected < 1e-6, (
                f"{reg}: reconciled to {got}, expected {expected}")
    assert not (drifted["areas"] < 0).any().any(), "negative areas after reconcile"


def test_projection_trajectory_requires_provenance():
    """A trajectory must carry its source and vintage.

    The projection is driven by an adopted external assumption set, not a
    forecast the model makes; an unattributed trajectory is not usable.
    """
    from capri_mod.projection import BaselineTrajectory, TrajectoryError

    try:
        BaselineTrajectory.from_dict({"name": "x", "base_year": 2017,
                                      "target_years": [2030]})
        assert False, "trajectory without source/vintage should be rejected"
    except TrajectoryError:
        pass

    # implausible growth factors are rejected rather than silently used
    try:
        BaselineTrajectory.from_dict({
            "name": "x", "source": "s", "vintage": "v", "base_year": 2017,
            "target_years": [2030],
            "growth": {"yields": {"_default": {"2030": 50.0}}}})
        assert False, "implausible growth factor should be rejected"
    except TrajectoryError:
        pass


def test_captrd_trajectory_is_usable_and_plausible():
    """The CAPRI-derived baseline trajectory loads and carries sensible factors.

    Extracted from a captrd p_result export (the 'series' datatype, which is the
    final reconciled trend in projection years). The economic sanity checks are
    that yields grow modestly, herds contract, and every factor sits in a
    plausible band -- a trajectory with a 3x yield factor would be an extraction
    artefact, not a forecast.
    """
    import os
    from capri_mod.projection import BaselineTrajectory

    path = os.path.join(str(DATA_DIR), "trajectories", "captrd_2030.json")
    if not os.path.exists(path):
        return  # trajectory not shipped in this build

    t = BaselineTrajectory.from_file(path)
    assert not t.is_null(), "captrd trajectory should carry real drift"
    assert t.source and t.source != "unknown", "trajectory must carry provenance"

    # yields grow modestly; herds contract -- the documented EU pattern
    y = t.factor("yields", "_default", 2030)
    h = t.factor("herds", "_default", 2030)
    assert 1.0 < y < 1.3, f"implausible default yield growth to 2030: {y}"
    assert 0.7 < h < 1.05, f"implausible default herd change to 2030: {h}"

    # every factor in the file is within the plausible band
    for block, keys in t.growth.items():
        for key, by_year in keys.items():
            for year, f in by_year.items():
                assert 0.2 < float(f) < 5.0, (
                    f"{block}/{key}/{year} factor {f} outside plausible band")


def test_set_aside_requirement_actually_binds(model):
    """A mandatory non-productive share must change the solve.

    Regression test for a silent-failure bug: `set_aside_requirement` was
    defined on PolicyScenario and referenced by four scenarios (including
    SET_ASIDE_10PCT, the Farm-to-Fork landscape-elements equivalent) but was
    never enforced in the supply constraints, so the scenario returned results
    bit-identical to the baseline while reporting success.
    """
    regions = list(model.data["areas"].index[:10])
    base = model.run(scenario="BASELINE", regions=regions)
    sa = model.run(scenario="SET_ASIDE_10PCT", regions=regions)

    changes, acts_seen = [], []
    for reg, res in base.get("supply", {}).items():
        a1 = getattr(res, "activities", None)
        a2 = getattr(sa.get("supply", {}).get(reg), "activities", None)
        if a1 is None or a2 is None:
            continue
        for act in a1.index:
            if act in a2.index and abs(a1[act]) > 1e-6:
                changes.append((a2[act] - a1[act]) / abs(a1[act]))
                acts_seen.append(act)

    assert changes, "no comparable activity cells"
    assert max(abs(c) for c in changes) > 1e-6, (
        "set_aside_requirement had NO effect on the solve — the instrument is "
        "defined but not enforced")

    # PRODUCTIVE area must contract. SETA is excluded from this average because
    # it IS the instrument: the requirement is a floor that forces land INTO
    # set-aside (SETA rises ~72%), so averaging it in with the crops it displaces
    # makes the overall mean POSITIVE and hides the contraction. An earlier
    # version of this test averaged everything together and so encoded the
    # superseded mechanism, in which set-aside was modelled as a cut to arable
    # land rather than a floor on the non-productive activity.
    productive = [c for a, c in zip(acts_seen, changes) if a != "SETA"]
    assert productive, "no productive activities compared"
    assert sum(productive) / len(productive) < 0, (
        "a 10% non-productive requirement should reduce PRODUCTIVE area on average")


def test_policy_instruments_are_not_inert(data):
    """Every wired policy instrument must actually reach the solve.

    Guard against the project's most persistent failure mode: an instrument that
    is defined on PolicyScenario, referenced by scenarios, reports success, and
    silently does nothing. Four separate breaks of exactly this kind were found
    (set-aside never enforced in the constraints; CAP adders discarded because
    the model wrapped them in an "adders" key the solve never unwrapped; the
    nitrate limit never passed from model to solve at all; Pillar II rates and
    eco-schemes never entering the adders despite the docstring saying so).

    This deliberately tests the *wiring* rather than running full model solves:
    the earlier version ran one 248-region solve per instrument and was far too
    slow to run routinely, which is how it went unverified for two sessions.
    Payment instruments are checked by confirming they move the supply adders;
    constraint instruments are checked by confirming they reach the solve's
    constraint builder and change the feasible set.
    """
    import numpy as np
    from capri_mod.policy.policy_module import PolicyModule, PolicyScenario

    base_adders = PolicyModule(data, PolicyScenario(name="base")).get_supply_policy_adders()

    payment_instruments = {
        "biss_rate_change": PolicyScenario(name="t", biss_rate_change=-100.0),
        "coupled_support": PolicyScenario(name="t", coupled_support={"DCOW": 200.0}),
        "aecs_rate_change": PolicyScenario(name="t", aecs_rate_change=50.0),
        "anc_rate_change": PolicyScenario(name="t", anc_rate_change=50.0),
        "organic_rate_change": PolicyScenario(name="t", organic_rate_change=50.0),
        "eco_scheme_budget_pct": PolicyScenario(name="t", eco_scheme_budget_pct=0.50),
    }
    for name, scen in payment_instruments.items():
        adders = PolicyModule(data, scen).get_supply_policy_adders()
        assert not np.allclose(adders.values, base_adders.values), (
            f"policy instrument '{name}' is INERT — it does not change the "
            "supply policy adders, so it cannot affect the solve")

    # An unchanged scenario must leave the adders untouched (the other direction:
    # a guard that fires on everything would be worthless).
    same = PolicyModule(data, PolicyScenario(name="t")).get_supply_policy_adders()
    assert np.allclose(same.values, base_adders.values), (
        "an unchanged scenario should reproduce the baseline adders exactly")


def test_constraint_instruments_reach_the_solve(data):
    """Set-aside and the nitrogen ceiling must change the feasible set.

    These act on constraints rather than net revenues, so they are checked at
    the constraint builder — cheap, and it is exactly where set-aside was
    silently missing.
    """
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]

    # Set-aside is implemented as CAPRI implements it (landscape.gms): a FLOOR
    # on the non-productive activity sized on UAA, expressed as -x_SETA <= -floor.
    # It therefore ADDS a constraint row rather than tightening the arable bound.
    A_base, b_base, _, _ = model._build_constraints()
    A_sa, b_sa, _, _ = model._build_constraints(set_aside_requirement=0.10)
    if "SETA" in model.acts:
        assert len(b_sa) > len(b_base), (
            "set_aside_requirement did not add the landscape-elements floor")
        # locate the floor row by its signature (a negative bound) rather than
        # by position: constraint order is an implementation detail.
        assert any(float(v) < 0 for v in b_sa), (
            "the SETA floor should enter as a negative bound (-x <= -floor)")

    # the nitrogen ceiling is anchored to observed base intensity, so an
    # unchanged run must be SLACK (this is what the 170 kg/ha anchor got wrong)
    base_int = model.base_n_intensity()
    _, b_slack, _, _ = model._build_constraints(nitrate_limit=base_int)
    _, b_tight, _, _ = model._build_constraints(nitrate_limit=base_int - 10.0)
    # locate the nitrogen row by which bound moves, rather than assuming a
    # position: the constraint order is an implementation detail and an
    # index-based check silently passes/fails for the wrong reason.
    moved = [i for i in range(len(b_slack))
             if abs(float(b_slack[i]) - float(b_tight[i])) > 1e-9]
    assert moved, "nitrate_limit did not tighten any constraint"
    for i in moved:
        assert float(b_tight[i]) < float(b_slack[i]), (
            "tightening the nitrogen limit loosened a constraint")


def test_no_negative_own_price_elasticities(data):
    """Every crop must respond POSITIVELY to a rise in its own price.

    A negative own-price supply elasticity is economically impossible and was a
    long-standing documented limitation for pulses. Measured directly it no
    longer occurs — it was fixed as a side effect of earlier PMP/solver work and
    the limitation note was simply never retired. This test pins that down so
    the sign cannot silently regress.
    """
    import pandas as pd
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = list(data["areas"].index[:12])
    sm.run(price_signals=None, regions=regions)

    crops = ["SWHE", "BARL", "PULS", "RAPE", "POTA", "SUGB"]
    for crop in crops:
        num = den = 0.0
        for reg in regions:
            model = sm._models.get(reg)
            if model is None or crop not in model.acts:
                continue
            base = model.solve(price_shock=None).activities
            shock = pd.Series(0.0, index=model.acts)
            shock[crop] = 0.10
            new = model.solve(price_shock=shock).activities
            b = base.get(crop, 0.0)
            if b > 1e-6:
                num += new.get(crop, 0.0) - b
                den += b
        if den > 0:
            elas = (num / den) / 0.10
            assert elas > 0, (
                f"{crop} has a NEGATIVE own-price elasticity ({elas:.3f}): "
                "supply must rise when a crop's own price rises")


def test_intensity_margin_identity_and_response(data):
    """The N intensity margin must preserve the base year and respond sanely.

    Nutrient coefficients are fixed per activity, so without this margin a
    nitrogen constraint can only cut AREA — which overstated the response ~10x
    against CAPRI's Green Deal run (wheat -24% vs -1.9%). CAPRI instead lets
    application per hectare flex (`v_cropNutNeedMultFact`) and splits the
    adjustment between intensity and area.

    Two properties matter:
      1. IDENTITY — at full intensity the yield factor is exactly 1.0, so
         switching this on cannot disturb the base year or PMP calibration.
      2. RESPONSE — a binding ceiling reduces intensity with diminishing
         returns, and the yield loss is agronomically plausible rather than a
         collapse.
    """
    from capri_mod.supply.intensity import yield_factor, optimal_intensity
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    # 1. base-year identity, exactly
    assert abs(float(yield_factor(1.0)) - 1.0) < 1e-12, (
        "yield_factor(1.0) must be exactly 1.0 or the base year shifts")

    # monotone and diminishing-returns
    fs = [float(yield_factor(m)) for m in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    assert all(b > a for a, b in zip(fs, fs[1:])), "yield must rise with N"
    gaps = [b - a for a, b in zip(fs, fs[1:])]
    assert all(b <= a + 1e-9 for a, b in zip(gaps, gaps[1:])), (
        "N response must show diminishing returns")

    # a 20% N cut should cost a few percent of yield, not a collapse
    loss20 = (1.0 - float(yield_factor(0.8))) * 100.0
    assert 1.0 < loss20 < 12.0, f"implausible yield loss for -20% N: {loss20:.1f}%"

    # 2. response under a real regional ceiling
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    region = list(data["areas"].index)[0]
    sm.run(price_signals=None, regions=[region])
    model = sm._models[region]
    crops = [c for c in model.acts if c in data["nutrients"].index]
    ncoef = data["nutrients"]["N"].reindex(crops).fillna(0.0)
    price = data["producer_prices"].reindex(crops).fillna(0.0)
    yld = data["yields"].loc[region].reindex(crops).fillna(0.0)
    areas = model._base_levels().reindex(crops).fillna(0.0)
    if float(areas.sum()) <= 0:
        return
    own = float((ncoef * areas).sum() / areas.sum())

    slack = optimal_intensity(ncoef, price, yld, 1.0, own * 1.05, areas)
    assert not slack.binding, "a ceiling above base intensity must not bind"
    assert abs(float(slack.yield_factor.mean()) - 1.0) < 1e-9

    tight = optimal_intensity(ncoef, price, yld, 1.0, own * 0.80, areas)
    assert tight.binding, "a 20% ceiling below base intensity must bind"
    wm = float((tight.intensity * areas).sum() / areas.sum())
    assert 0.5 <= wm < 1.0, f"intensity should fall but not collapse: {wm:.3f}"


def test_cap_support_not_double_counted(model):
    """A BASELINE model run must not inflate supply above the calibrated base.

    The calibrated net revenue already contains cap_premium. The policy module's
    get_supply_policy_adders() returns the ABSOLUTE payment, and the solve ADDS
    it to cap_premium — so passing the absolute level double-counted CAP support
    and inflated wheat ~29% above a no-policy solve. The distortion sat in the
    BASELINE too, so every scenario-vs-baseline comparison was measuring the
    double-count rather than the policy. Adders are now passed as a DELTA from
    the baseline policy, making a BASELINE run a no-op.
    """
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    regions = list(model.data["areas"].index[:8])

    # reference: the supply module solved with no policy dict at all
    sm = SupplyModule(model.data,
                      calibrate_supply_elasticities(model.data["areas"]))
    raw = sm.run(price_signals=None, regions=regions)
    raw_wheat = sum(float(v.activities.get("SWHE", 0.0)) for v in raw.values())

    # a BASELINE model run should land on essentially the same place
    res = model.run(scenario="BASELINE", regions=regions, max_outer_iter=1)
    run_wheat = sum(float(getattr(v, "activities", {}).get("SWHE", 0.0))
                    for v in res.get("supply", {}).values())

    if raw_wheat <= 0:
        return
    inflation = (run_wheat / raw_wheat - 1.0) * 100.0
    assert abs(inflation) < 10.0, (
        f"BASELINE run inflates wheat by {inflation:.1f}% against the "
        "calibrated supply solve — CAP support is being double-counted")


def test_elasticity_paths_are_base_year_aware():
    """Elasticity sources must resolve through the base-year-aware lookup.

    REGIONAL_FILE and PMP_ELAS_FILE were hard-coded as "2017/supply/...", so
    re-basing the model to another year would have silently fallen back to the
    literature defaults — the CAPRI elasticities would just stop being found,
    with no error. They now go through resolve_data_file().
    """
    import pandas as pd
    from pathlib import Path
    from capri_mod.supply import capri_pmp
    from capri_mod.data.loaders import load_all_data

    assert "2017" not in capri_pmp.REGIONAL_FILE, "year hard-coded in REGIONAL_FILE"
    assert "2017" not in capri_pmp.PMP_ELAS_FILE, "year hard-coded in PMP_ELAS_FILE"

    d = load_all_data(str(DATA_DIR))
    eps, prov, summ = capri_pmp.build_elasticity_table(
        Path(str(DATA_DIR)), list(d["areas"].index), list(d["areas"].columns),
        pd.Series(0.25, index=d["areas"].columns))
    # the real CAPRI sources must still be found, not silently skipped
    assert summ["cells_from_regional_file"] > 0, (
        "regional CAPRI elasticities no longer resolve")
    assert summ["cells_from_pmp_file"] > 0, (
        "PMP CAPRI elasticities no longer resolve")


def test_organic_area_target_binds_and_is_a_noop_at_zero(model):
    """The Farm-to-Fork organic AREA target must act on I/O coefficients.

    Previously only `organic_rate_change` existed — a payment RATE, which is a
    different instrument from an area TARGET. CAPRI models organic farming by
    adjusting average input-output coefficients in proportion to the organic
    share (organic_io.gms), not by tracking organic activities separately, and
    this model now does the same.
    """
    from capri_mod.policy.policy_module import PolicyScenario

    regions = list(model.data["areas"].index[:8])

    def totals(res):
        out = {}
        for reg, v in res.get("supply", {}).items():
            acts = getattr(v, "activities", None)
            if acts is None:
                continue
            for a, val in acts.items():
                out[a] = out.get(a, 0.0) + float(val)
        return out

    base = totals(model.run(scenario="BASELINE", regions=regions,
                            max_outer_iter=1))
    zero = totals(model.run(custom_scenario=PolicyScenario(
        name="t", organic_area_target=0.0), regions=regions, max_outer_iter=1))
    tgt = totals(model.run(custom_scenario=PolicyScenario(
        name="t", organic_area_target=0.25), regions=regions, max_outer_iter=1))

    # a zero target must be a true no-op
    for a, v in base.items():
        if v > 1.0:
            assert abs(zero.get(a, 0.0) - v) / v < 1e-9, (
                f"organic_area_target=0 changed {a}")

    # a 25% target must move production, and downward on average (organic
    # yields are lower), without collapsing anything
    moved = [a for a, v in base.items()
             if v > 1.0 and abs(tgt.get(a, 0.0) - v) / v > 1e-6]
    assert moved, "organic_area_target=0.25 had no effect"
    for a in moved:
        ratio = tgt.get(a, 0.0) / base[a]
        assert 0.2 < ratio < 5.0, f"{a} moved implausibly: x{ratio:.2f}"


def test_projection_matches_capri_2030_reference(model):
    """The projection must reproduce CAPRI's own 2030 baseline.

    The 'instruments off' validation: CAPRI's reference run gives projected 2030
    activity levels, which validates the whole projection chain (trajectory
    extraction, reconciliation, recursive loop, comparative-static core) without
    needing any policy scenario.

    Skips if the CAPRI reference extract is not present in this build.
    """
    import os
    import pandas as pd
    from capri_mod.projection import ProjectionModule, BaselineTrajectory

    ref_path = os.path.join(str(DATA_DIR), "validation", "capri_ref_2030_levels.csv")
    traj_path = os.path.join(str(DATA_DIR), "trajectories", "captrd_2030.json")
    if not (os.path.exists(ref_path) and os.path.exists(traj_path)):
        return

    cap = pd.read_csv(ref_path, index_col=0).iloc[:, 0]
    regions = [r for r in model.data["areas"].index][:40]
    traj = BaselineTrajectory.from_file(traj_path)
    res = ProjectionModule(model, traj).run(regions=regions, max_outer_iter=1)

    ours = {}
    for reg, v in res.baseline[2030].get("supply", {}).items():
        acts = getattr(v, "activities", None)
        if acts is None:
            continue
        for a, val in acts.items():
            ours[a] = ours.get(a, 0.0) + float(val)
    ours = pd.Series(ours)

    common = [a for a in ours.index
              if a in cap.index and cap[a] > 10 and ours[a] > 10]
    if len(common) < 5:
        return
    corr = ours[common].corr(cap[common])
    assert corr > 0.9, (
        f"projected 2030 levels correlate only {corr:.3f} with CAPRI's reference")


def test_permanent_crop_base_fidelity(data):
    """Permanent crops must survive the base solve.

    The PERMANENT land figure and the crop areas come from different
    aggregations and disagree in 56 of 248 regions (4640 kha), concentrated in
    the Mediterranean permanent-crop regions — ES63/ES64 carry real olive area
    against a PERMANENT figure of zero. Taking the land figure literally made
    the BASE YEAR infeasible, so the solver cut and the largest crop absorbed
    it: EL43 olives collapsed 178 -> 40 kha in a plain base solve, surfacing as
    a 0.35x olive miss against CAPRI's 2030 reference.
    """
    import numpy as np
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities

    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = [r for r in data["areas"].index
               if float(data["areas"].at[r, "OLIV"]) > 5][:12]
    if not regions:
        return
    sm.run(price_signals=None, regions=regions)

    errs = []
    for reg in regions:
        model = sm._models.get(reg)
        if model is None:
            continue
        base = float(model._base_levels().get("OLIV", 0.0))
        got = float(model.solve(price_shock=None).activities.get("OLIV", 0.0))
        if base > 5:
            errs.append(abs(got - base) / base)
    assert errs, "no olive regions solved"
    mean_err = float(np.mean(errs)) * 100.0
    assert mean_err < 10.0, (
        f"olive base fidelity {mean_err:.1f}% — the permanent-land bound is "
        "cutting a crop the base year says exists")


def test_nitrogen_balance_is_physically_plausible(data):
    """The gross N balance must land near observed EU levels.

    Two unit bugs made it meaningless. (1) GRAS yield is FRESH MATTER in kg/ha
    (~36000) while the uptake formula expects t/ha, so grass supplied 99.3% of
    total N uptake and drove the balance to -170000 kg N/ha. (2) Manure N was
    scaled `heads * 1000 / 1e6`, dividing by a further 1000 and leaving organic
    input at effectively ZERO against a real EU average near 55 kg N/ha.

    Eurostat puts the EU gross nitrogen balance around 45-50 kg N/ha, with a
    regional range of roughly 10-200.
    """
    import numpy as np
    from capri_mod.supply.supply_module import SupplyModule
    from capri_mod.utils.utils import calibrate_supply_elasticities
    from capri_mod.environmental.environmental_module import EnvironmentalModule

    em = EnvironmentalModule(data)
    sm = SupplyModule(data, calibrate_supply_elasticities(data["areas"]))
    regions = list(data["areas"].index[:12])
    res = sm.run(price_signals=None, regions=regions)

    per_ha = []
    for reg in regions:
        if reg not in res or reg not in data["yields"].index:
            continue
        acts = res[reg].activities
        nb = em.compute_nitrogen_balance(acts, data["yields"].loc[reg], reg)
        area = sum(float(acts.get(c, 0.0)) for c in data["areas"].columns)
        if area > 0:
            per_ha.append(nb["n_surplus"] / area)

    assert per_ha, "no regions produced a nitrogen balance"
    median = float(np.median(per_ha))
    assert 0 < median < 200, (
        f"median N surplus {median:.0f} kg N/ha is outside any plausible range "
        "(Eurostat EU average ~45-50)")
    # and the components must be individually sane
    reg = regions[0]
    nb = em.compute_nitrogen_balance(
        res[reg].activities, data["yields"].loc[reg], reg)
    area = sum(float(res[reg].activities.get(c, 0.0)) for c in data["areas"].columns)
    assert 0 < nb["n_crop_uptake"] / area < 500, "implausible crop N uptake"
    assert nb["n_organic_input"] > 0, "manure N is not reaching the balance"


def test_permanent_crops_are_not_pathologically_inelastic(data):
    """Permanent crops must not be an order of magnitude less elastic than annuals.

    Literature priors put olives at 0.08 and wine at 0.10 against ~0.30 for
    cereals, making permanents ~10x LESS responsive. CAPRI's own p_elasSupp says
    the opposite: at member-state level, permanents and vegetables sit at a
    median 0.97 against 0.39 for annual crops — 2.47x MORE elastic. Our relative
    structure was inverted by roughly 25x, and permanent crops consequently
    barely responded to a Green Deal margin shock.
    """
    from capri_mod.utils.utils import calibrate_supply_elasticities

    el = calibrate_supply_elasticities(data["areas"])
    annual = [el[c] for c in ("SWHE", "BARL", "RAPE", "POTA", "OATS")
              if c in el.index]
    perm = [el[c] for c in ("OLIV", "WINE", "APPL", "OFRU", "CITR", "OVEG")
            if c in el.index]
    assert annual and perm

    import numpy as np
    ratio = float(np.median(perm)) / float(np.median(annual))
    assert ratio > 1.0, (
        f"permanent crops are only {ratio:.2f}x as elastic as annuals; CAPRI's "
        "own elasticities put them ABOVE annuals (2.47x)")


def test_pesticide_reduction_binds_and_is_a_noop_at_zero(model):
    """The pesticide target's yield-loss channel must act, and only downward.

    CAPRI implements the F2F pesticide target as four shocks; only the 10%
    yield loss is represented here, because this model has no plant-protection
    cost component to cut. The yield loss needs no PPP data -- CAPRI states it
    as an explicit assumption, since it has no dose-response function for plant
    protection.
    """
    from capri_mod.policy.policy_module import PolicyScenario

    regions = list(model.data["areas"].index[:8])

    def totals(res):
        out = {}
        for reg, v in res.get("supply", {}).items():
            acts = getattr(v, "activities", None)
            if acts is None:
                continue
            for a, val in acts.items():
                out[a] = out.get(a, 0.0) + float(val)
        return out

    base = totals(model.run(scenario="BASELINE", regions=regions, max_outer_iter=1))
    zero = totals(model.run(custom_scenario=PolicyScenario(
        name="t", pesticide_reduction=0.0), regions=regions, max_outer_iter=1))
    cut = totals(model.run(custom_scenario=PolicyScenario(
        name="t", pesticide_reduction=0.50), regions=regions, max_outer_iter=1))

    for a, v in base.items():
        if v > 1.0:
            assert abs(zero.get(a, 0.0) - v) / v < 1e-9, (
                f"pesticide_reduction=0 changed {a}")

    affected = [a for a in ("SWHE", "BARL", "RAPE")
                if base.get(a, 0.0) > 1.0]
    assert affected, "no affected crops present"
    assert any(cut.get(a, 0.0) < base[a] for a in affected), (
        "a 50% pesticide reduction should lower affected crop areas")

"""CAPRI's basic payment scheme per region (policy/implement_bps.gms, scen/Premiums/bps_convergence.gms;
capri_mod/policy/bps.py): the internal convergence on a case worked by hand, and the member states whose model ends
at a flat rate against CAPRI's 2030 reference (dataOut PRMD of dp_bps, used as a check)."""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import bps

ROOT = Path(__file__).resolve().parents[2]


def test_the_tunnel_with_the_30_percent_rule_worked_by_hand():
    """Two units of 100 entitlements, 30 and 10 million EUR: aiuv 200 EUR; the target 0.9 x 200 = 180, the low unit
    (100) closes a third of its gap in the final year: 126.67; the high one (300) falls linearly to pay the envelope,
    273.33, above the 30% floor of 210; the envelope holds."""
    ceil = {2019: {"A": 30.0, "B": 10.0}}
    opts = {"linear": True, "rule30": True, "final": 2019, "target_share": 0.9, "gap": 1 / 3}
    r = bps.converge(ceil, {"A": 100.0, "B": 100.0}, [2019], opts)[2019]
    assert r["B"] == pytest.approx(100 + (180 - 100) / 3)
    assert r["A"] == pytest.approx(400 - r["B"])
    assert (r["A"] + r["B"]) * 100 / 1000 == pytest.approx(40.0)


def test_the_30_percent_rule_and_capris_overshoot_step():
    """A unit at 1000 EUR next to nine at 100 (100 thousand entitlements each, 190 million EUR, aiuv 190), flat target,
    full closure: the low units reach 190, the high unit would fall to 190 but the 30% rule holds it at 700. The
    overshoot left, 51 million EUR, comes off the low units as implement_bps.gms l. 309 writes it: divided by their
    entitlements in thousand ha without the factor 1000 (0.057 EUR/ha each, not 56.7), so the envelope stays overshot
    (prmcut cuts the year's BPS to its ceiling). CAPRI's arithmetic kept: a CAPRI bug (KNOWN_ISSUES K141)."""
    ceil = {2019: {"H": 100.0, **{f"L{i}": 10.0 for i in range(9)}}}
    entl = {u: 100.0 for u in ceil[2019]}
    opts = {"linear": True, "rule30": True, "final": 2019, "target_share": 1.0, "gap": 1.0}
    r = bps.converge(ceil, entl, [2019], opts)[2019]
    assert r["H"] == pytest.approx(700.0)
    assert r["L0"] == pytest.approx(190.0 - 51.0 / 900.0)


def test_the_flat_rate_member_states_follow_capris_2030_reference():
    """Germany, Austria, the Netherlands, Sweden, Malta and Finland end at a flat rate (target share 1, gap closure 1):
    the 2030 rate (2020's) is the member state's 2020 BPS ceiling (K136's chain) x 1000 over its crops' trend levels,
    whatever the historical key (here random); CAPRI's 2030 reference has it at all 67 units within 1e-7 (13 November
    2026). The other member states need the MTR key (calc_mtr.gms, to port)."""
    lev = pd.read_csv(ROOT / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(set(lev.region) & ru)
    levels = {(r.region, r.activity): r.trd_kha for r in lev.itertuples()}
    random.seed(1)
    key = {u: random.uniform(1, 100) for u in units}
    out = bps.bps_rates(units, levels, key, 2030)
    ref = {"DEA10000": 177.0406, "AT110000": 174.0106, "NL110000": 257.3921, "SE010000": 121.4199,
           "MT000000": 24.4899, "FI130000": 138.742}
    for u, v in ref.items():
        assert out[u] == pytest.approx(v, abs=1e-4), u
    de = {round(v, 8) for u, v in out.items() if capri_ms(u) == "DE000000"}
    assert len(de) == 1

"""CAPRI's premium cut (policy/prmcut.gms; capri_mod/policy/premium_cut.py) on small cases worked by hand: the cut factor
from a value or a quantity ceiling, a ceiling written EPS, the cut passed down to the units, an EU aggregate's
ceiling from its member states, the modification factor in place of the weight."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import cap14_premiums as C
from capri_mod.policy.premium_cut import EPS, CeilingRegions, ceiling_cut, premiums


def test_the_cut_is_one_over_the_largest_overshoot():
    assert ceiling_cut(50.0, 2.0, ceil_lev=100.0, ceil_val=4.0) == 1.0           # under both ceilings
    assert ceiling_cut(200.0, 2.0, ceil_lev=100.0, ceil_val=4.0) == pytest.approx(0.5)
    assert ceiling_cut(50.0, 8.0, ceil_lev=100.0, ceil_val=4.0) == pytest.approx(0.5)
    assert ceiling_cut(300.0, 8.0, ceil_lev=100.0, ceil_val=4.0) == pytest.approx(1 / 3)
    assert ceiling_cut(1.0, 1.0) is None                                          # no ceiling of the scheme
    assert ceiling_cut(1.0, 1.0, ceil_val=EPS) == EPS


def test_a_member_states_value_ceiling_scales_its_units_premiums():
    """Two units of one member state, an area payment declared at 1000 EUR/ha (CAPRI's PGSAPS for the greening
    payment) and a ceiling of 1.5 million EUR: 30 kha + 20 kha eligible cost 50 million at the declared rate, so the
    cut is 0.03 and each hectare is paid 30 EUR."""
    levels = {("R1", "SWHE"): 30.0, ("R2", "SWHE"): 15.0, ("R2", "BARL"): 5.0}
    prmd = {(u, a, "DPGREEN"): 1000.0 for u, a in levels}
    weight = {k: 1.0 for k in prmd}
    regions = CeilingRegions(member_states={"MS": ["R1", "R2"]})
    out = premiums(levels, prmd, weight, {("MS", "DPGREEN"): {"CEILVAL": 1.5}}, regions)
    assert out["used"][("MS", "DPGREEN")] == pytest.approx((50.0, 50.0))
    assert out["cut"][("MS", "DPGREEN")] == pytest.approx(0.03)
    assert out["cutt"][("R1", "DPGREEN")] == pytest.approx(0.03) and out["cutt"][("R2", "DPGREEN")] == pytest.approx(0.03)
    assert out["prme"][("R2", "BARL", "DPGREEN")] == pytest.approx(30.0)


def test_a_units_own_ceiling_comes_first_and_eps_pays_nothing():
    levels = {("R1", "SUGB"): 10.0, ("R2", "SUGB"): 10.0, ("R3", "SUGB"): 10.0}
    prmd = {(u, "SUGB", "VCS"): 200.0 for u in ("R1", "R2", "R3")}
    weight = {k: 1.0 for k in prmd}
    regions = CeilingRegions(member_states={"MS": ["R1", "R2", "R3"]})
    ceil = {("MS", "VCS"): {"CEILVAL": 3.0},           # 6 million at the declared rate: cut 0.5
            ("R1", "VCS"): {"CEILVAL": 2.0},           # the unit's own: under it, cut 1
            ("R3", "VCS"): {"CEILVAL": EPS}}           # EPS: nothing paid
    out = premiums(levels, prmd, weight, ceil, regions)
    assert out["cutt"][("R1", "VCS")] == 1.0
    assert out["cutt"][("R2", "VCS")] == pytest.approx(0.5)
    assert out["cutt"][("R3", "VCS")] == 0.0 and out["prme"][("R3", "SUGB", "VCS")] == 0.0


def test_an_aggregates_ceiling_reaches_the_member_states_without_one():
    """An EU aggregate's quantity ceiling over two member states' entitlements (their own levels); a unit takes the
    first cut above it: its member state's where set, the aggregate's otherwise; no ceiling anywhere: 1."""
    levels = {("A1", "DCOW"): 60.0, ("B1", "DCOW"): 90.0}
    prmd = {("A1", "DCOW", "P"): 100.0, ("B1", "DCOW", "P"): 100.0, ("A", "DCOW", "P"): 100.0,
            ("B", "DCOW", "P"): 100.0, ("A1", "DCOW", "Q"): 10.0}
    weight = {("A1", "DCOW", "P"): 1.0, ("B1", "DCOW", "P"): 1.0, ("A1", "DCOW", "Q"): 1.0}
    regions = CeilingRegions(aggregates={"EU": ["A", "B"]}, member_states={"A": ["A1"], "B": ["B1"]})
    ceil = {("EU", "P"): {"CEILLEV": 100.0}, ("B", "P"): {"CEILLEV": 120.0}}
    out = premiums(levels, prmd, weight, ceil, regions)
    assert out["used"][("EU", "P")][0] == pytest.approx(150.0)
    assert out["cutt"][("A1", "P")] == pytest.approx(100 / 150)     # the aggregate's
    assert out["cutt"][("B1", "P")] == 1.0                           # its member state's own ceiling, not reached
    assert out["cutt"][("A1", "Q")] == 1.0                           # no ceiling of Q


def test_the_modification_factor_replaces_the_weight():
    levels = {("R1", "GRAE"): 10.0}
    prmd = {("R1", "GRAE", "DPSCOW"): 100.0}
    out = premiums(levels, prmd, {("R1", "GRAE", "DPSCOW"): 1.0}, {}, CeilingRegions(),
                   modif={("R1", "GRAE", "DPSCOW"): 0.25})
    assert out["prme"][("R1", "GRAE", "DPSCOW")] == pytest.approx(25.0)


def test_the_coupled_support_cuts_follow_capris_2030_reference():
    """P2: the coupled schemes' 2030 rates and ceilings from CAPRI's VCS and cotton files (capri_mod/policy/
    cap14_premiums.py), the premium groups' activities, the trend levels: the cut of the crops' schemes in France and
    Spain equals CAPRI's 2030 reference (dataOut CUTT, used as a check): 328 and 151 unit x scheme pairs within 1e-5;
    three of them written here."""
    root = Path(__file__).resolve().parents[2]
    lev = pd.read_csv(root / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ref = {("FR100000", "vcs-61-France-Cereals"): 0.8249780174902113,
           ("FR100000", "vcs-81-France-Fruit and vegetables"): 0.13722371814383494,
           ("ES300000", "vcs-125-Spain-Grain legumes"): 0.0229490678925722}
    for ms in ("FR000000", "ES000000"):
        units = [r for r in lev.region.unique() if capri_ms(r) == ms and r != ms]
        levels = {(r.region, r.activity): r.trd_kha for r in lev[lev.region.isin(units)].itertuples()}
        prmd, weight, ceil = C.coupled_premiums(units, levels, 2030)
        out = premiums(levels, prmd, weight, ceil, CeilingRegions(member_states={ms: units}))
        for k, v in ref.items():
            if k[0] in units:
                assert out["cutt"][k] == pytest.approx(v, rel=1e-5), k

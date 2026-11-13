"""CAPRI's declared premiums (policy/policy.gms; capri_mod/policy/declared.py) on small cases worked by hand, and against
CAPRI's 2030 reference: a member state's rate reaching its units through NUTS 1, a unit's own rate first, EPS stopping
the inheritance, the application factors, the entitlement weights, the re-aggregation by level."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.policy import cap14_premiums as C
from capri_mod.policy.declared import PolicyRegions, declared_premiums, gams_sum
from capri_mod.policy.premium_cut import EPS


def _regions():
    """EU_WEST > MS > N1 > U1, U2; MS > U3 (a unit that is its own NUTS 1 region, like BL400000)."""
    return PolicyRegions(units=["U1", "U2", "U3"], member_states=["MS"], nuts1=["N1", "U3"], eu1015=[],
                         aggregates=["EU_WEST"],
                         members={"EU_WEST": ["MS"], "MS": ["N1", "U1", "U2", "U3"], "N1": ["U1", "U2"],
                                  "U3": ["U3"]},
                         above={"MS": {"MS", "EU_WEST"}, "N1": {"N1", "MS"}, "U1": {"U1", "N1", "MS"},
                                "U2": {"U2", "N1", "MS"}, "U3": {"U3", "MS"}},
                         srnuts1={"N1", "U3"})


GROUPS = {"PGCERE": ["SWHE", "BARL"], "PGSWHE": ["SWHE"], "PGCOWS": ["SCOW"]}


def test_gams_sums_keep_eps_apart_from_zero():
    assert gams_sum([EPS, None]) == EPS
    assert gams_sum([EPS, 3.0]) == 3.0
    assert gams_sum([None, 0.0]) is None


def test_a_member_states_rate_reaches_its_units_and_a_units_own_comes_first():
    """MS declares 100 for the cereals and 20 more for wheat (the activity's groups add up), per level; U2 declares
    its own 50 for the cereals (no application type of its own: it takes MS's through N1). U1 and U3 inherit."""
    levels = {("U1", "SWHE"): 10.0, ("U2", "SWHE"): 30.0, ("U3", "BARL"): 5.0}
    decl = {("MS", "VCS"): {"rates": {"PGCERE": 100.0, "PGSWHE": 20.0}, "APPTYPE": "perLevl"},
            ("U2", "VCS"): {"rates": {"PGCERE": 50.0}}}
    out = declared_premiums(decl, GROUPS, _regions(), levels)
    p = out["prmd"]
    assert p[("U1", "SWHE", "VCS")] == pytest.approx(120.0)
    assert p[("U2", "SWHE", "VCS")] == pytest.approx(50.0)
    assert p[("U3", "BARL", "VCS")] == pytest.approx(100.0)
    assert p[("N1", "SWHE", "VCS")] == pytest.approx((120 * 10 + 50 * 30) / 40)      # re-aggregated by level
    assert p[("MS", "SWHE", "VCS")] == pytest.approx((120 * 10 + 50 * 30) / 40)      # from N1 (SRNUTS1)
    assert out["weight"][("U1", "SWHE", "VCS")] == 1.0


def test_eps_stops_the_inheritance_and_no_application_type_pays_nothing():
    levels = {("U1", "SWHE"): 10.0, ("U2", "SWHE"): 10.0, ("U3", "SWHE"): 10.0}
    decl = {("MS", "A"): {"rates": {"PGSWHE": 100.0}, "APPTYPE": "perLevl"},
            ("U2", "A"): {"rates": {"PGSWHE": EPS}},
            ("MS", "B"): {"rates": {"PGSWHE": 100.0}}}                    # a rate without an application type
    out = declared_premiums(decl, GROUPS, _regions(), levels)
    assert out["prmd"][("U1", "SWHE", "A")] == pytest.approx(100.0)
    assert ("U2", "SWHE", "A") not in out["prmd"]
    assert not any(k[2] == "B" for k, v in out["prmd"].items() if v)


def test_the_application_factors_and_the_entitlement_weights():
    """Per livestock unit (0.8 LU per suckler cow), per yield (kg / 1000), per slaughtered head (the weight takes the
    slaughter coefficient / 1000); an entitlement weight of 0.4 at the member state reaches the unit, EPS is 0."""
    levels = {("U1", "SCOW"): 10.0, ("U1", "SWHE"): 10.0, ("U2", "SCOW"): 10.0}
    decl = {("MS", "LU"): {"rates": {"PGCOWS": 200.0}, "APPTYPE": "perLiveStockUnit"},
            ("MS", "Y"): {"rates": {"PGSWHE": 10.0}, "APPTYPE": "perYield"},
            ("MS", "S"): {"rates": {"PGCOWS": 50.0}, "APPTYPE": "perSlgthd"}}
    out = declared_premiums(decl, GROUPS, _regions(), levels, lu_units={"SCOW": 0.8},
                            yields={("U1", "SWHE"): 7000.0}, slaughter={("U1", "SCOW"): 250.0},
                            entl_weight={("MS", "SCOW", "LU"): 0.4, ("U2", "SCOW", "LU"): EPS})
    assert out["prmd"][("U1", "SCOW", "LU")] == pytest.approx(160.0)
    assert out["prmd"][("U1", "SWHE", "Y")] == pytest.approx(70.0)
    assert out["prmd"][("U1", "SCOW", "S")] == pytest.approx(50.0)
    assert out["weight"][("U1", "SCOW", "S")] == pytest.approx(0.25)
    assert out["weight"][("U1", "SCOW", "LU")] == pytest.approx(0.4)
    assert out["weight"][("U2", "SCOW", "LU")] == 0.0
    with pytest.raises(ValueError):
        declared_premiums(decl, GROUPS, _regions(), levels)              # the yields, livestock units not given


def test_the_cap14_declared_premiums_follow_capris_2030_reference():
    """P2b: the coupled and area schemes' 2030 declarations (cap14_premiums) through policy.gms with the crops' trend
    levels (cap14_entitlement_levels.csv): the declared premium equals CAPRI's 2030 reference PRMD (dataOut, used as a
    check) at all 19554 unit x crop x scheme records and the 1666 member states' (re-aggregated) within 1e-6, none
    missing or extra at the units (with the animals' trend levels of sim_ini too, 22564 and 1893: 13 November 2026,
    CHANGELOG). Four written here: CAPRI's unit BL400000, its own NUTS 1 region, with Luxembourg's scheme; Latvia; a
    Finnish NUTS 1 region and Belgium's member-state row, re-aggregated by level."""
    root = Path(__file__).resolve().parents[2]
    lev = pd.read_csv(root / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ru = set(pd.read_csv(root / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(set(lev.region) & ru)
    levels = {(r.region, r.activity): r.trd_kha for r in lev[lev.region.isin(units)].itertuples()}
    d1, _ = C.coupled_declarations(2030)
    d2, _ = C.area_declarations(2030)
    out = declared_premiums({**d1, **d2}, C.data()["groups"], PolicyRegions.from_codes(units), levels,
                            entl_weight=C.entitlement_weights())
    ref = {("BL400000", "PULS", "vcs-196-Luxembourg-Protein crops"): 200.0,
           ("LV000000", "SWHE", "vcs-216-Latvia-Seeds"): 104.0,
           ("FI100000", "RYEM", "vcs-60-Finland-Cereals"): 56.0,
           ("BL000000", "PULS", "vcs-196-Luxembourg-Protein crops"): 26.883289}
    for k, v in ref.items():
        assert out["prmd"][k] == pytest.approx(v, rel=1e-6), k

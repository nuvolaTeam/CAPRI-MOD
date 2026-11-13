"""CAPRI's rural development payments (policy/extend_rd_baseline.gms, policy/rd_logic.gms; capri_mod/policy/rd.py)
against CAPRI's own numbers, used as checks: the restart file's RD money and CAPRI's 2030 reference results."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import cap14_premiums as C
from capri_mod.policy import rd
from capri_mod.policy.declared import PolicyRegions, declared_premiums
from capri_mod.policy.premium_cut import EPS, CeilingRegions, premiums

ROOT = Path(__file__).resolve().parents[2]


def _levels():
    lev = pd.read_csv(ROOT / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    return {(r.region, r.activity): r.trd_kha for r in lev.itertuples()}


def test_the_rd_money_after_2013_is_the_2007_2013_average_and_eps_spend_keeps_a_region_out():
    """Greece's Kentriki Makedonia (EL120000): measure 214's average spend of 2007-2013 (four years spent, 18.509 million
    EUR a year over seven, as sim_ini's 2020 agri-environment ceilings sum it); measure 216's spend there is written
    EPS, so the region takes no share of Greece's unspent 216 plan (its weight is EPS, not above it) and its money
    after 2013 is EPS; a region with 216 spend takes its share of the plan."""
    B = rd.extend_budget(rd.data(), 2030)
    assert B[("EL120000", 2020, "214", "spend")] == pytest.approx((30.141 + 39.906 + 17.956 + 41.56) / 7, abs=1e-3)
    assert B[("EL120000", 2020, "216", "spend")] == EPS
    assert B[("EL110000", 2020, "216", "spend")] > 0.139 / 7


def test_the_rd_declared_premiums_follow_capris_2030_reference():
    """P2c: the RD schemes' 2030 declarations from rd_budget.gdx (extend_rd_baseline, rd_logic, def_policy's fill)
    at the trend levels, through policy.gms: their ceilings and rates equal sim_ini's (2607 ceilings, 3658 rates;
    13 November 2026), and the declared premiums CAPRI's 2030 reference PRMD at 21673 of the 21733 unit x activity x
    scheme records within 1e-6. The 60 others are Praha's (CZ010000): in CAPRI's simulation its own rates are absent
    and it takes the Czech ones, as when its levels are zero at the chain's call (open). Written here: an LFA rate,
    a Natura 2000 rate at a unit, an agri-environment rate capped at 2000 EUR, a Swedish expert rate."""
    L = _levels()
    out = rd.rd_declarations(L, 2030, C.data()["groups"], base_weights=C.entitlement_weights())
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted({u for u, _ in L} & ru)
    dp = declared_premiums(out["declarations"], C.data()["groups"], PolicyRegions.from_codes(units), L)
    ref = {("FR100000", "SWHE", "DPRD_LFA"): 19.769586287010732, ("AT110000", "DCOL", "DPRD_AE5"): 2000.0,
           ("AT110000", "BULH", "DPRD_AE8"): 54.306771, ("SE010000", "SWHE", "DPRD_SeExte"): 300.0}
    for k, v in ref.items():
        assert dp["prmd"][k] == pytest.approx(v, rel=1e-6), k


def test_the_rd_cuts_and_effective_premiums_with_the_weights_killed():
    """CAP_2014_2020.gms l. 77 kills the entitlement weights before the year's policy.gms: an animal's RD premium is
    the declared one times the cut, weight 1 (CAPRI's 2030 reference: Austria's AE8 cut 0.476514, the bulls' 25.878
    EUR; the dairy cows' AE5 2000 EUR uncut). With rd_logic's livestock-unit weights the cut would differ."""
    L = _levels()
    out = rd.rd_declarations(L, 2030, C.data()["groups"], base_weights=C.entitlement_weights())
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(u for u in ru if capri_ms(u) == "AT000000")
    Lm = {k: v for k, v in L.items() if k[0] in units}
    dp = declared_premiums(out["declarations"], C.data()["groups"], PolicyRegions.from_codes(units), Lm)
    mm = pd.read_csv(ROOT / "capri_data" / "codes" / "capri" / "MAP_RR.csv")
    nuts1 = {r: [u for u in mm[mm.region == r].member if u in units] for r in ("AT100000", "AT200000", "AT300000")}
    ceil = {k: v for k, v in out["ceilings"].items() if k[0] == "AT000000" or k[0] in units or k[0] in nuts1}
    prmd = {k: v for k, v in dp["prmd"].items() if k[0] in units and v}
    res = premiums(Lm, prmd, {k: 1.0 for k in prmd}, ceil, CeilingRegions(member_states={"AT000000": units}, nuts1=nuts1))
    assert res["cutt"][("AT110000", "DPRD_AE8")] == pytest.approx(0.476514, rel=1e-5)
    assert res["prme"][("AT110000", "BULH", "DPRD_AE8")] == pytest.approx(25.877963, rel=1e-5)
    assert res["prme"][("AT110000", "DCOH", "DPRD_AE5")] == pytest.approx(2000.0, rel=1e-9)

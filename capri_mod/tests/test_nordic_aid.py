"""CAPRI's Nordic aid (policy/nordicaid.gms; capri_mod/policy/nordic_aid.py) through policy.gms (declared.py), against
CAPRI's 2030 reference results (dataOut PRMD, used as a check)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import cap14_premiums as C
from capri_mod.policy import nordic_aid as N
from capri_mod.policy.declared import PolicyRegions, declared_premiums

ROOT = Path(__file__).resolve().parents[2]


def test_the_nordic_aid_follows_capris_2030_reference():
    """The 1995 declarations carried to 2030: Finland's and Sweden's declared Nordic aid equals the reference PRMD at
    all 198 unit x activity x scheme records within 1e-6 (13 November 2026, with sim_ini's 2030 milk yields). Written
    here: the milk aid per yield (FI130000's dairy cows: its Nordic regions' shares x EUR per ton, x 6.3685 t per cow,
    sim_ini's DATA "Y"), a sows' aid per livestock unit, the cereals' aid per ha, the suckler cows'."""
    lev = pd.read_csv(ROOT / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(u for u in ru if capri_ms(u) in ("FI000000", "SE000000"))
    levels = {(r.region, r.activity): r.trd_kha for r in lev.itertuples() if r.region in units}
    lu = pd.read_csv(ROOT / "capri_data" / "pipeline" / "captrd" / "dat" / "p_luunits.csv")
    decl, ceilings = N.nordic_declarations(2030)
    assert ceilings[("FI000000", "dpNoaMilk")]["CEILVAL"] == pytest.approx(225.22)
    out = declared_premiums(decl, C.data()["groups"], PolicyRegions.from_codes(units), levels,
                            yields={("FI130000", "DCOL"): 6368.520137}, lu_units=dict(zip(lu.act, lu.value)))
    ref = {("FI130000", "DCOL", "dpNoaMilk"): 819.6285415807765, ("SE070000", "SOWS", "dpNoaPigs"): 89.782,
           ("FI130000", "OATS", "dpNoaCere"): 20.3, ("FI130000", "SCOW", "dpNoaBovi"): 313.12}
    for k, v in ref.items():
        assert out["prmd"][k] == pytest.approx(v, rel=1e-6), k

"""CAPRI's 2004-2013 premium regime for the BPS's historical key (pol_input/mtr_until2013.gms, policy/calc_mtr_top.gms,
policy/calc_mtr.gms; capri_mod/policy/mtr.py): the GAMS semantics of the file's assignments, the coupling degree and
the decoupling targets of 2030, and the key against CAPRI's 2030 reference BPS rates (dataOut PRMD of dp_bps, used as
a check)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capri_mod.policy import bps, mtr
from capri_mod.policy.premium_cut import EPS

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def year_2030():
    P = mtr.mtr_series(2030, 2017)
    return mtr.declarations_of_year(P, 2030)


def test_the_files_assignments_as_gams_executes_them(year_2030):
    """Slovenia's bull premium ceiling assigned 0 in 2012 and 2013 (l. 306-307) deletes those records, so 2030 carries
    2011's (10.077 / 0.75) with the rate and type of l. 309-310; the Health Check's EPS of 2012 (l. 589) ends France's
    protein premium; France's MTR ceiling is the net ceiling of 2013 (Annex IV, l. 222)."""
    assert year_2030[("SI000000", "DPBULF")] == {"CEILVAL": pytest.approx(10.077 / 0.75), "APPTYPE": "perLevl",
                                                 "PGBULF": 180.0}
    assert year_2030[("FR000000", "DPPULS")] == {"CEILLEV": EPS, "PGPROT": EPS}
    assert year_2030[("FR000000", "DPMTR")]["CEILVAL"] == pytest.approx(7853.1)


def test_coupling_and_decoupling_targets_of_2030():
    """The coupling loop runs to %endofMTR% (2020) only and l. 990 keeps the simulation year's: nothing is coupled in
    2030 (France's suckler cows 75% in 2020). The targets: France's units DDFRMS (EU_WEST, l. 1574), Denmark's hybrid
    model from the table (bulls 25% all land, 75% farm flat rate), Slovenia 67% arable / 33% grassland (l. 1580)."""
    assert not any(mtr.coupling(2030).values())
    assert mtr.coupling(2020)[("DPSCOW", "FR000000")] == 75.0
    T = mtr.dd_targets(2030, ["FR240000", "DK000000", "SI000000"])
    assert T[("FR240000", "DPGRCU", "DDFRMS")] == 100.0
    assert (T[("DK000000", "DPBULF", "DDRARE")], T[("DK000000", "DPBULF", "DDFRMF")]) == (25.0, 75.0)
    assert (T[("SI000000", "DPGRCU", "DDRARA")], T[("SI000000", "DPGRCU", "DDRGRA")]) == (67.0, 33.0)


def test_the_key_gives_capris_2030_bps_rates():
    """The member states whose BPS converges in a tunnel get CAPRI's 2030 rate from the ported key (13 November 2026:
    Belgium, Greece, Spain, Italy, Portugal and Ireland within 3e-5 at every unit; France within 0.6% but Corsica,
    its own BPS region, 5% low, KNOWN_ISSUES K142)."""
    lev = pd.read_csv(ROOT / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ms = ("BL", "EL", "ES", "IT", "PT", "IR", "FR")
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(u for u in set(lev.region) & ru if u.startswith(ms))
    levels = {(r.region, r.activity): r.trd_kha for r in lev.itertuples() if r.region in set(units)}
    key = mtr.mtr_key(units, levels, 2030, 2017)
    out = bps.bps_rates(units, levels, key, 2030)
    ref = {"BL210000": 191.399821, "IR010000": 161.791527, "IR020000": 188.281110, "ES300000": 77.709541,
           "IT400000": 152.214564, "PT110000": 96.045417, "EL300000": 174.927077}
    for u, v in ref.items():
        assert out[u] == pytest.approx(v, rel=3e-5), u
    assert out["FR240000"] == pytest.approx(89.945954, rel=6e-3)
    assert out["FR830000"] == pytest.approx(17.629655, rel=6e-2)

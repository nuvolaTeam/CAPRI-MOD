"""CAPRI's premiums of 2030, all ported schemes together (capri_mod/policy/premiums.py): the declared premiums of the
year cut by prmcut at CAPRI's trend levels against CAPRI's 2030 reference (dataOut PRME, used as a check). For the
whole EU (13 November 2026): 47,262 against 47,260 million EUR, 92% of the unit x activity totals within 1e-4; the
differences France's BPS (K142) and the RD port's (K140)."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import pytest

from capri_mod.data.definitions import capri_ms
from capri_mod.policy import premiums as PM

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cut_2030():
    lev = pd.read_csv(ROOT / "capri_data" / "2017" / "policy" / "cap14_entitlement_levels.csv")
    ru = set(pd.read_csv(ROOT / "capri_data" / "codes" / "regional_units.csv").region)
    units = sorted(u for u in set(lev.region) & ru if capri_ms(u) in ("IR000000", "FI000000", "EL000000",
                                                                       "DE000000", "FR000000"))
    levels = {(r.region, r.activity): r.trd_kha for r in lev.itertuples() if r.region in set(units)}
    yp = PM.year_premiums(units, levels, 2030, 2017)
    return yp.cut(levels)


def test_each_scheme_family_against_capris_reference(cut_2030):
    """One premium of each family: Ireland's suckler cow welfare payment (48 EUR per cow), its BPS (the MTR key),
    its RD natural constraint payment, Finland's Nordic milk aid, Greece's cotton payment, Germany's greening."""
    ref = {("IR010000", "SCOW", "DPIRSCOW"): 48.0, ("IR010000", "SWHE", "dp_bps"): 161.7915265,
           ("IR010000", "GRAE", "DPRD_LFA"): 58.2784242, ("FI130000", "DCOL", "dpNoaMilk"): 819.6285416,
           ("EL120000", "TEXT", "cscs-Greece-Cotton"): 234.0, ("DE110000", "SWHE", "DPGREEN"): 85.6648249}
    got = {(u, a, s.lower()): v for (u, a, s), v in cut_2030.items()}
    for (u, a, s), v in ref.items():
        assert got[(u, a, s.lower())] == pytest.approx(v, rel=1e-6), (u, a, s)


def test_the_premium_per_activity_over_all_schemes(cut_2030):
    """The sum over the schemes per unit and activity (the model's premium per activity): Ireland's suckler cows,
    Germany's low-yield dairy cows within 1e-4 (the RD port's agri-environment and Natura 2000 premiums up to 2e-5
    off, K140); France's soft wheat within K142's BPS gap."""
    tot = defaultdict(float)
    for (u, a, s), v in cut_2030.items():
        if v and v != "EPS":
            tot[(u, a)] += v
    assert tot[("IR010000", "SCOW")] == pytest.approx(82.7121038, rel=1e-4)
    assert tot[("DE110000", "DCOL")] == pytest.approx(137.0631088, rel=1e-4)
    assert tot[("FR240000", "SWHE")] == pytest.approx(225.4736775, rel=2e-3)

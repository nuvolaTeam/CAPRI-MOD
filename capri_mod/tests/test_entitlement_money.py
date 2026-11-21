"""The entitlement cut in the model's money (capri_mod/supply/entitlements.py region_limit; KNOWN_ISSUES K174)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_cut_is_capris_over_the_years_money_deflator():
    """CAPRI's cut is in its money of the simulation year (the ceilings' nominal amounts), the model's objective in
    base-year money with CAPRI's premiums over the deflator (K108): Spain's cut 118.06 EUR/ha of 2030 is 92.4 in the
    model's money, the ratio of CAPRI's soft-wheat premium in ES420000 (182.93) to the model's (143.23)."""
    from capri_mod.data.inputs import money_deflator, current
    from capri_mod.supply import entitlements as E
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    import _money
    dfl = money_deflator(2030)
    assert dfl == _money.deflator(2030)                 # the builders' number
    assert money_deflator(current().base_year) == 1.0
    acts = ["SWHE", "DWHE", "BARL", "GRAE", "FALL"]
    cut, limit, cols = E.region_limit("ES420000", acts, 2030)
    capri = E.ms_cuts(2030)["ES000000"]
    assert abs(capri - 118.06) < 0.01 and abs(cut - capri / dfl) < 1e-12
    with open(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"
              / "capri_cap_premium_2030.csv", newline="") as fh:
        prem = {r["region"]: r for r in csv.DictReader(fh)}
    swhe = float(prem["ES420000"]["SWHE"])
    assert abs(swhe * dfl - 182.932131) < 1e-3          # dataOut('ES420000','','PRME','SWHE','2030')
    assert len(cols) >= 3 and limit > 0

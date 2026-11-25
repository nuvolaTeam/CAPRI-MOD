"""CAPRI's 2030 rations and requirements as factors on the 2017 rations (tools/build/build_ration_trajectory_2030.py:
capri_ref_ration_2030.csv from CAPRI's solved reference, chain_ration_2030.csv from the ported chain's start, the
projection's default), KNOWN_ISSUES K201: the bulls' and heifers' factors from CAPRI's elementary activities."""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
TRAJ = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"
F30 = TRAJ / "capri_ref_ration_2030.csv"


@pytest.mark.parametrize("name", ["capri_ref_ration_2030.csv", "chain_ration_2030.csv"])
def test_every_2017_ration_has_capris_2030_requirements(name):
    """Every region x animal ration of 2017 has CAPRI's 2030 requirement and methane factors in both files (until K201
    none of the 249 bull rations had one: the builder read CAPRI's aggregate BULF, which has no DAYS in the 2030
    reference)."""
    from capri_mod.data.nested_tables import read_feed_rations
    raw = read_feed_rations(ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv")
    t = pd.read_csv(TRAJ / name, keep_default_na=False, float_precision="round_trip")
    for q in ("req_ENNE", "req_CRPR", "req_DMIN", "req_DMAX", "ghg_CH4MAN"):
        cov = set(map(tuple, t[t["item"] == q][["region", "animal"]].values))
        miss = {(r, a) for r, acts in raw.items() for a in acts} - cov
        assert not miss, (q, sorted(miss)[:5])


def test_the_bulls_factor_is_capris_elementary_activities():
    """DE21's bulls: CAPRI's 2030 energy requirement per head over its 2017 one, LEVL-weighted over BULL and BULH with
    their DAYS (the requirement rows' p_animReq x p_animProdDays, supply/supply_model.gms l. 521-590). CAPRI's values:
    res_2_1730greendeal_refdefaulta dataOut at 2030, ENNE per day and DAYS, BULL 52.4187798863137 x 203.129402299191,
    BULH 65.1807208083636 x 304.538179612978, LEVL 33.0307 each; res_17DE.txt at Y, BULL 53.2856491691183 x
    204.93182621374, BULH 66.3852901325123 x 307.464378026377, LEVL 43.0378 each (the two levels equal to 1e-7 in
    both years, so the weights cancel within the tolerance)."""
    t = pd.read_csv(F30, keep_default_na=False, float_precision="round_trip").set_index(["region", "animal", "item"])
    e30 = 52.4187798863137 * 203.129402299191 + 65.1807208083636 * 304.538179612978
    e17 = 53.2856491691183 * 204.93182621374 + 66.3852901325123 * 307.464378026377
    assert float(t.at[("DE210000", "BULL", "req_ENNE"), "factor"]) == pytest.approx(e30 / e17, rel=1e-6)

"""CAPRI's new energy crops (NECR) as a model activity (register DEP-9, KNOWN_ISSUES K138): a fixed crop on permanent
land, with a level and an output at the simulation year only, its output OCRO at OCRO's unit value."""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
NECR_2030 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "necr_2030.csv"


def test_necr_is_a_fixed_crop_on_permanent_land():
    """CAPRI's MFCACT (sets.gms l. 131-143) and its land type FRUN (landTypes_to_pact); one technology."""
    from capri_mod.data.definitions import CROPS
    from capri_mod.supply.regional_supply.tables import FIXED_ACTIVITIES, ACTIVITY_CLASSES
    assert "NECR" in CROPS and "NECR" in FIXED_ACTIVITIES
    assert ACTIVITY_CLASSES["NECR"]["land_type"] == "FRUN" and ACTIVITY_CLASSES["NECR"]["technologies"] == "1"


def test_the_year_data_carry_capris_2030_level_and_output():
    """DATA_NECR_Y: Denmark's 2030 NECR is sim_ini_21730's DATA(DK000000, NECR, LEVL | OCRO, Y) (99.58 thousand ha,
    250 per ha as OCRO / 1000); no level in the base year, as CAPREG's; nothing at another year."""
    from capri_mod.projection.projection_module import ProjectionModule
    t = pd.read_csv(NECR_2030, index_col=0)
    assert t.at["DK000000", "levl_kha"] == pytest.approx(99.58091120402729, rel=1e-12)
    assert t.at["DK000000", "yield"] == pytest.approx(0.24999287726574582, rel=1e-12)
    areas = pd.DataFrame({"OCRO": [1.0, 2.0]}, index=["DK000000", "AT130000"])
    yields = pd.DataFrame({"OCRO": [3.5, 3.0]}, index=["DK000000", "AT130000"])
    data = {"necr_2030": t, "areas": areas.copy(), "yields": yields.copy()}
    ProjectionModule.DATA_NECR_Y(data, 2017)
    assert "NECR" not in data["areas"].columns
    ProjectionModule.DATA_NECR_Y(data, 2030)
    assert data["areas"].at["DK000000", "NECR"] == t.at["DK000000", "levl_kha"]
    assert data["yields"].at["DK000000", "NECR"] == t.at["DK000000", "yield"]
    assert data["areas"].at["AT130000", "NECR"] == 0.0 and "AT130000" not in t.index


def test_necr_takes_ocros_unit_value():
    """UVAG_PACT_TO_Y: NECR's one output is OCRO (PACT_TO_Y NECR.OCRO, sets.gms l. 5411), valued at OCRO's unit value;
    an activity with a price of its own keeps it."""
    from capri_mod.supply.regional_supply.region_build import UVAG_PACT_TO_Y
    p = UVAG_PACT_TO_Y(pd.Series({"OCRO": 1364.28, "SWHE": 180.0, "GRAE": 30.0}))
    assert p["NECR"] == 1364.28 and p["SWHE"] == 180.0 and p["GRAE"] == 30.0
    p = UVAG_PACT_TO_Y(pd.Series({"OCRO": 1364.28, "NECR": 999.0}))
    assert p["NECR"] == 999.0

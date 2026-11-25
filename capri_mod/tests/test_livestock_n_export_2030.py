"""CAPRI's 2030 N in livestock products (tools/build/build_livestock_n_export_2030.py, fert/calc_nexport.gms;
ProjectionModule.req_or_man_fnc_CRPR_EXPT_Y; KNOWN_ISSUES K202)."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
T30 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "livestock_n_export_coef_2030.csv"


def _builder():
    spec = importlib.util.spec_from_file_location("bne", ROOT / "tools" / "build" / "build_livestock_n_export_2030.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_calc_nexport_gives_capris_2017_values():
    """calc_nexport_CRPR_EXPT on CAPRI's 2017 items gives CAPRI's CRPR_EXPT. sim_ini_21730 DATA at "BAS", DE21:
    the low-yield dairy cows (COMI 5222.549823362889, COMF 208.61293722964268, BEEF 77.55172013938592, YCAM and YCAF
    404.3694398786418, ICOW 269.4864512658409; CRPR_EXPT 30.291898142519916) and the sows (YPIG 24029.867365354356,
    PORK 58.52989629045183, IPIG 467.9426405119249; CRPR_EXPT 13.71154825916621)."""
    f = _builder().calc_nexport_CRPR_EXPT
    d = {"COMI": 5222.549823362889, "COMF": 208.61293722964268, "BEEF": 77.55172013938592,
         "YCAM": 404.3694398786418, "YCAF": 404.3694398786418, "ICOW": 269.4864512658409}
    assert f("DCOL", d) == pytest.approx(30.291898142519916, rel=1e-12)
    assert f("SOWS", {"YPIG": 24029.867365354356, "PORK": 58.52989629045183, "IPIG": 467.9426405119249}) == \
        pytest.approx(13.71154825916621, rel=1e-12)


def test_the_projection_to_capris_2030_reference_takes_its_n_in_products():
    """project_data with CAPRI's 2030 reference as the trajectory: the N in products per head is the 2030 table's
    wherever it has a value (a trend projection keeps 2017 x the yield factor)."""
    from capri_mod.data.inputs import trajectories_dir
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import BaselineTrajectory, ProjectionModule
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False)
    pm = ProjectionModule(m, BaselineTrajectory.from_file(str(ROOT / "capri_data" / "scenarios" / "capri_ref_2030")),
                          capri_prices_dir=str(trajectories_dir(str(ROOT / "capri_data"), 2030)))
    data, _ = pm.project_data(2030)
    t = pd.read_csv(T30, index_col=0, float_precision="round_trip")
    n = data["livestock_n_export_coef"]
    k = 0
    for a in t.columns.intersection(n.columns):
        for r in t.index[t[a].notna()].intersection(n.index):
            assert float(n.at[r, a]) == float(t.at[r, a]), (r, a)
            k += 1
    assert k > 2000

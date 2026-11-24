"""CAPRI's animal requirement functions (capri_mod/feed/equations/req_or_man_fnc_req.py: feed/req_or_man_fnc.gms with
%1 = req) against CAPRI's 2030 Green Deal reference run's start (sim_ini_21730: p_animReqLit, p_animProdDays,
p_animReqSubEne, p_crprReq, p_NutContFeed)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "check"), str(ROOT / "tools" / "lib")]

from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402


def test_dairy_cows_give_capris_2030_literature_requirements():
    """DE21's low-yield dairy cows at the reference run's start (sim_ini_21730, DATA at "Y": LEVL 165.50810036816625,
    COMI 5885.022365464989, COMF 199.13227084845536; technology T with share 1; MITERRA's housing days 341, no share
    Et): CAPRI's p_animReqLit per head and day, ENNE 103.17130752032679, CRPR 2.0267780532885737, DRMN
    16.184019627604386, DRMX -19.42082355312526, FIDI 5.643051730126346, FILG 1.8810172433754484, FICO
    -11.880631167498539, DRMA 16.993220608984604; 365 production days."""
    import check_manure_output_2030 as chk
    P = chk.params()
    r = "DE210000"
    data = {(r, "DCOL", "LEVL"): 165.50810036816625, (r, "DCOL", "COMI"): 5885.022365464989,
            (r, "DCOL", "COMF"): 199.13227084845536}
    st = rq.ReqState(DATA=data, RS=(r,), MS=frozenset({"DE000000"}), R_RAGG_MS={r: "DE000000"}, GRSACT=(), RUMI=("DCOL",),
                     AACT=("DCOL",), p_LUUnits=P["p_LUUnits"], p_technFact={(r, "DCOL", "LEVL", "T"): 1.0},
                     p_rcEmissions={(r, "DAICOW_L", "HD"): 341.0}, p_feedQuant={},
                     p_carcassShare=P["p_carcassShare"], p_startWgt=P["p_startWgt"], p_reqfcnlim=P["p_reqfcnlim"],
                     p_coeffEnergyForGrowth=P["p_coeffEnergyForGrowth"],
                     p_convFactEnergyUnitsToEnne=P["p_convFactEnergyUnitsToEnne"],
                     p_NutContFeedRef=P["p_NutContFeedRef"], MAACT=("DCOL",))
    rq.req_or_man_fnc_req(st)
    want = {"ENNE": 103.17130752032679, "CRPR": 2.0267780532885737, "DRMN": 16.184019627604386,
            "DRMX": -19.42082355312526, "FIDI": 5.643051730126346, "FILG": 1.8810172433754484,
            "FICO": -11.880631167498539, "DRMA": 16.993220608984604}
    for item, v in want.items():
        assert st.p_animReq[(r, "DCOL", "T", item)] == pytest.approx(v, rel=1e-12), item
    assert st.p_animProdDays[(r, "DCOL", "T")] == 365


def test_every_region_and_animal_gives_capris_2030_requirements():
    """tools/check/check_requirements_2030.py: all of CAPRI's regional units of the reference run, all animal
    activities, every requirement, the production days, the energy components, the crude protein and the rations'
    nutrient densities at 1e-6."""
    from paths import REFERENCE
    if not (REFERENCE / "simini" / "simini_21730" / "p_rcEmissions.csv.gz").exists():
        pytest.skip("CAPRI's reference run is not available")
    import check_requirements_2030 as chk
    argv = sys.argv
    sys.argv = ["check_requirements_2030.py", "--rtol", "1e-6"]
    try:
        assert chk.main() == 0
    finally:
        sys.argv = argv

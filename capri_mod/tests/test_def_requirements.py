"""CAPRI's requirements at a simulation's start (capri_mod/feed/equations/def_requirements.py, adjust.py,
create_sim_ini_gdx.py: capmod/def_requirements.gms, baseline/adjust.gms, capmod/create_sim_ini_gdx.gms l. 421-461)
against CAPRI's 2030 Green Deal reference run's start (sim_ini_21730: p_animReq, p_animExcrProtCorrFact, the feed
shares, the production days)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "check"), str(ROOT / "tools" / "lib")]

from capri_mod.feed.equations import adjust as adj  # noqa: E402
from capri_mod.feed.equations import def_requirements as dr  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402


def test_dairy_cows_give_capris_2030_corrected_requirements():
    """DE21's low-yield dairy cows (the requirement call's inputs of test_req_or_man_fnc_req.py) with CAPREG's 2017
    corrections (reqrel_17DE, p_animReqCorrFac1: ENNE 0.1717641490152375, CRPR 0.1821294712144481, DRMX
    -0.05709027029004399, FILG 2.257473544002691, FICO -0.2406005505074451; the last three erased, inequalities) and the
    baseline calibration's (fedtrm_21730DEdefaulta, p_animReqCorrFac): sim_ini_21730's p_animReq per head and day,
    ENNE 114.79708863137989, CRPR 2.2312383513836362, DRMN 15.163045778957681, DRMX -19.749946719930865, FIDI
    5.356832969955205, FILG 5.427183581528434, FICO -8.399619380466984, DRMA 16.993220608984604, and the manure's protein
    factor 1.1008794711208327."""
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
    capreg = {(r, "DCOL", "T", "ENNE"): 0.1717641490152375, (r, "DCOL", "T", "CRPR"): 0.1821294712144481,
              (r, "DCOL", "T", "DRMX"): -0.05709027029004399, (r, "DCOL", "T", "FILG"): 2.257473544002691,
              (r, "DCOL", "T", "FICO"): -0.2406005505074451}
    d = dr.DefReqInputs(RU=(r,), MPACT=("DCOL",), PACT_TO_Y=frozenset({("DCOL", "COMI")}), DATA_BAS={},
                        p_animReqCorrFac=capreg, SIMY=2030, BAS=2017)
    dr.def_requirements(st, d)
    fed = {"ENNE": 0.9746186025165379, "CRPR": 0.9558234732231625, "DRMN": 1.0, "DRMX": 0.9908727976753026,
           "FIDI": 1.0, "FILG": 2.961315630230511, "FICO": 0.7256430778091006}
    fed = {(r, "DCOL", "T", i): v for i, v in fed.items()} | {(r, "DCOL", "T", f): 1.0 for f in rq.FEED}
    a = adj.AdjustInputs(RU=(r,), p_animReqCorrFac1=fed, p_animExcrProtCorrFact_Y=d.p_animExcrProtCorrFact_Y,
                         p_feedInpCoeffLoad={}, DATA_TRD={})
    adj.p_animReq_corrected(st, a)
    adj.p_animExcrProtCorrFact_corrected(st, a)
    want = {"ENNE": 114.79708863137989, "CRPR": 2.2312383513836362, "DRMN": 15.163045778957681,
            "DRMX": -19.749946719930865, "FIDI": 5.356832969955205, "FILG": 5.427183581528434,
            "FICO": -8.399619380466984, "DRMA": 16.993220608984604}
    for item, v in want.items():
        assert st.p_animReq[(r, "DCOL", "T", item)] == pytest.approx(v, rel=1e-12), item
    assert a.p_animExcrProtCorrFact_Y[(r, "DCOL", "T")] == pytest.approx(1.1008794711208327, rel=1e-12)


def test_every_region_and_animal_gives_capris_2030_simulation_start():
    """tools/check/check_sim_ini_requirements_2030.py: all of CAPRI's regional units with a calibration file (AL
    without), all animal activities: p_animReq, the protein factor, the feed shares, the production days and DATA's days
    at 1e-6."""
    from paths import REFERENCE
    if not (REFERENCE / "simini" / "simini_21730" / "v_feedInpCoeff.csv.gz").exists():
        pytest.skip("CAPRI's reference run is not available")
    import check_sim_ini_requirements_2030 as chk
    try:
        chk._raw(None)
    except Exception as e:        # no access to the gated raw dataset
        pytest.skip(f"the raw dataset is not available: {e}")
    argv = sys.argv
    sys.argv = ["check_sim_ini_requirements_2030.py", "--rtol", "1e-6"]
    try:
        assert chk.main() == 0
    finally:
        sys.argv = argv


def test_calibration_corrections_follow_capris_statements_after_the_solve():
    """feed/fedtrm_cal_pw.gms l. 762-812 and baseline/fedtrm_fin.gms l. 47-52 on one animal and two feeds: the energy
    requirement recomputed from the ration (correction = ration / requirement), an inequality requirement at the lower
    of the requirement and the ration (FILG 2.0 against a ration of 0.5: correction 4), the maximum dry matter at most
    -1.2 x the minimum, the feeds' rows 1, the protein factor times the crude protein's correction."""
    from capri_mod.feed.equations import fedtrm_cal_pw as cal
    from capri_mod.feed.equations import fedtrm_fin as fin
    r, a, t = "XX110000", "DCOL", "T"
    req = {(r, a, t, "ENNE"): 100.0, (r, a, t, "CRPR"): 2.0, (r, a, t, "DRMN"): 15.0, (r, a, t, "DRMX"): -17.0,
           (r, a, t, "FILG"): 2.0, (r, a, t, "FGRA"): 1.067}
    fic = {(r, a, t, "FGRA"): 10000.0, (r, a, t, "FCER"): 1000.0}
    cont = {("XX000000", "ENNE", "FGRA"): 3.0, ("XX000000", "ENNE", "FCER"): 9.0,
            ("XX000000", "CRPR", "FGRA"): 0.05, ("XX000000", "CRPR", "FCER"): 0.1,
            ("XX000000", "DRMN", "FGRA"): 0.5, ("XX000000", "DRMN", "FCER"): 0.9,
            ("XX000000", "DRMX", "FGRA"): -0.5, ("XX000000", "DRMX", "FCER"): -0.9,
            ("XX000000", "FILG", "FGRA"): 0.01, ("XX000000", "FILG", "FCER"): 0.08}
    c = cal.CalState(RUNR=(r,), MAACT=(a,), p_animReq=dict(req), v_feedInpCoeff_L=fic,
                     p_animProdDays={(r, a, t): 365.0}, p_maxFeedShare={k: 1.0 for k in fic},
                     DATA_content=cont, R_RAGG_MS={r: "XX000000"}, DATA_LEVL={(r, a): 10.0})
    cal.v_animReq_start(c)
    cal.after_solve(c)
    corr = fin.p_animReqCorrFac((r,), (a,), c.p_animReq, c.v_animReq_L)
    enne = (10000 * 3.0 + 1000 * 9.0) / 365
    assert corr[(r, a, t, "ENNE")] == pytest.approx(enne / 100.0, rel=1e-14)
    assert c.p_animReq[(r, a, t, "ENNE")] == pytest.approx(enne, rel=1e-14)
    assert corr[(r, a, t, "FILG")] == pytest.approx(2.0 / ((10000 * 0.01 + 1000 * 0.08) / 365), rel=1e-14)
    # DRMX: min(-17, -1.2 x 15 = -18) = -18, then min(-18, the ration's -15.15...) = -18: correction -17 / -18
    assert corr[(r, a, t, "DRMX")] == pytest.approx(17.0 / 18.0, rel=1e-14)
    assert corr[(r, a, t, "DRMN")] == pytest.approx(1.0, rel=1e-14)
    assert corr[(r, a, t, "FGRA")] == 1.0
    prot = {(r, a, t): 1.1}
    fin.p_animExcrProtCorrFact_calibrated((r,), (a,), {(r, a, "LEVL", t): 1.0}, prot, corr)
    assert prot[(r, a, t)] == pytest.approx(1.1 * ((10000 * 0.05 + 1000 * 0.1) / 365) / 2.0, rel=1e-14)


def test_every_region_gives_capris_2030_calibration_corrections_from_its_solution():
    """tools/check/check_fedtrm_after_solve_2030.py: with CAPRI's calibrated feed input coefficients, the corrections
    of every regional unit with a calibration file equal CAPRI's fedtrm_21730<CC>defaulta at 1e-6, the calibrated
    energy and protein requirements and the protein factor sim_ini_21730's."""
    from paths import REFERENCE
    if not (REFERENCE / "simini" / "simini_21730" / "v_feedInpCoeff.csv.gz").exists():
        pytest.skip("CAPRI's reference run is not available")
    import check_fedtrm_after_solve_2030 as chk
    try:
        chk.sim._raw(None)
    except Exception as e:        # no access to the gated raw dataset
        pytest.skip(f"the raw dataset is not available: {e}")
    argv = sys.argv
    sys.argv = ["check_fedtrm_after_solve_2030.py", "--rtol", "1e-6"]
    try:
        assert chk.main() == 0
    finally:
        sys.argv = argv

"""CAPRI's manure output functions (capri_mod/feed/equations/req_or_man_fnc.py: feed/req_or_man_fnc.gms with %1 = man)
against CAPRI's 2030 Green Deal reference run (res_2_1730greendeal_refdefaulta, dataOut at 2030)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "check"), str(ROOT / "tools" / "lib")]

from capri_mod.feed.equations import req_or_man_fnc as rm  # noqa: E402


def _state(data, tf, corr):
    import check_manure_output_2030 as chk
    P = chk.params()
    return rm.ManState(DATA=dict(data), RS=("DE210000",), MS=frozenset({"DE000000"}), R_RAGG_MS={"DE210000": "DE000000"},
                       GRSACT=(), RUMI=(), p_LUUnits=P["p_LUUnits"], p_technFact=tf, p_animExcrProtCorrFact=corr,
                       p_NutContManureKgM3=P["p_NutContManureKgM3"], p_addExcrPerkgMilk=P["p_addExcrPerkgMilk"],
                       p_carcassShare=P["p_carcassShare"], p_startWgt=P["p_startWgt"], p_reqfcnlim=P["p_reqfcnlim"])


def test_dairy_cows_sows_and_hens_give_capris_2030_manure():
    """DE21 at the reference run's start (sim_ini_21730, DATA at "Y"): the low-yield dairy cows (LEVL
    165.50810036816625, COMI 5885.022365464989, COMF 199.13227084845536), the sows (LEVL 25.526665359218754, YPIG
    26681.00270345063) and the hens (LEVL 0.6787660876910439, EGGS 22260.928377857952), technology T with share 1,
    p_animExcrProtCorrFact at "Y" 1.1008794711208327, 1.0663141706523578 and 1.1295335512431848, the N in products
    at 2030 by fert/calc_nexport.gms 33.86864797493963, 15.015664809908968 and 494.1292147962953. CAPRI's dataOut at
    2030: MANN 101.865018400898, MANP 67.5366185452538, MANK 147.395526790673 (DCOL); 38.3518871018968,
    17.5207988491162, 17.5207988491162 (SOWS); 679.595210924217, 504, 408 (HENS)."""
    r = "DE210000"
    data = {(r, "DCOL", "LEVL"): 165.50810036816625, (r, "DCOL", "COMI"): 5885.022365464989,
            (r, "DCOL", "COMF"): 199.13227084845536, (r, "DCOL", "CRPR_EXPT"): 33.86864797493963,
            (r, "SOWS", "LEVL"): 25.526665359218754, (r, "SOWS", "YPIG"): 26681.00270345063,
            (r, "SOWS", "CRPR_EXPT"): 15.015664809908968,
            (r, "HENS", "LEVL"): 0.6787660876910439, (r, "HENS", "EGGS"): 22260.928377857952,
            (r, "HENS", "CRPR_EXPT"): 494.1292147962953}
    tf = {(r, a, "LEVL", "T"): 1.0 for a in ("DCOL", "SOWS", "HENS")}
    corr = {(r, "DCOL", "T"): 1.1008794711208327, (r, "SOWS", "T"): 1.0663141706523578,
            (r, "HENS", "T"): 1.1295335512431848}
    st = rm.req_or_man_fnc_man(_state(data, tf, corr))
    want = {"DCOL": (101.865018400898, 67.5366185452538, 147.395526790673),
            "SOWS": (38.3518871018968, 17.5207988491162, 17.5207988491162),
            "HENS": (679.595210924217, 504.0, 408.0)}
    for a, w in want.items():
        got = tuple(st.DATA[(r, a, i)] for i in ("MANN", "MANP", "MANK"))
        assert got == pytest.approx(w, rel=1e-12), a


def test_no_pig_tables_leaves_the_fattening_pigs_out():
    """Without CAPRI's pig requirement tables (dat/feed/porkreq.gms) the fattened pigs' manure is not computed and the
    call says so: DATA keeps the input's MANN."""
    r = "DE210000"
    st = rm.req_or_man_fnc_man(_state({(r, "PIGF", "LEVL"): 1.0, (r, "PIGF", "PORK"): 90.0,
                                       (r, "PIGF", "MANN"): 7.0}, {(r, "PIGF", "LEVL", "T"): 1.0},
                                      {(r, "PIGF", "T"): 1.1}))
    assert st.not_computed == {"PIGF"}
    assert st.DATA[(r, "PIGF", "MANN")] == 7.0


def test_every_region_and_animal_gives_capris_2030_manure():
    """tools/check/check_manure_output_2030.py: all regions of the reference run (member states without regions,
    NUTS 2 regions, the non-EU units), all animal activities, MANN, MANP and MANK at 1e-6."""
    from paths import BASELINE_REF, REFERENCE
    if not ((REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz").exists() and Path(BASELINE_REF).exists()):
        pytest.skip("CAPRI's reference run is not available")
    import check_manure_output_2030 as chk
    argv = sys.argv
    sys.argv = ["check_manure_output_2030.py", "--rtol", "1e-6"]
    try:
        assert chk.main() == 0
    finally:
        sys.argv = argv

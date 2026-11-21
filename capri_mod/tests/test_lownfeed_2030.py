"""CAPRI's low-nitrogen feeding at the simulation year (envind/low_n_feed.gms; KNOWN_ISSUES K194): the option's cut
and manure effect are built from the 2030 requirements CAPRI's simulation loads from sim_ini_21730 (p_animReq after
the 2030 baseline's feed calibration, p_animReqLit, p_animExcrProtCorrFact), not from CAPREG's 2017 factors
(tools/build/build_lownfeed_effects.py)."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("_lnf", ROOT / "tools" / "build" / "build_lownfeed_effects.py")
LNF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LNF)
CSV = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "lownfeed_effects.csv"

# sim_ini_21730, DE210000, 'T': p_animReq / p_animReqLit of CRPR and ENNE, DATA MANN (BAS) and CRPR_EXPT (Y)
DE21 = {"DCOL": dict(req=(2.2312, 114.7971), lit=(2.0268, 103.1713), excr=1.1009),
        "DCOH": dict(req=(2.9043, 142.784), lit=(2.9026, 135.1802), excr=1.0006)}


def test_the_cut_is_capris_formula_on_the_2030_excess():
    """low_n_feed.gms l. 88-96: 0.15 x the protein excess / (1 + 0.5 x the energy excess); DE21's low-yield dairy cows
    carry a 10% protein excess in 2030, its high-yield ones almost none (CAPRI's Green Deal adopts the option on DCOL
    and not on DCOH there)."""
    c = DE21["DCOL"]
    cut = LNF.lowNFeed_cut(c["req"][0], c["lit"][0], c["req"][1], c["lit"][1])
    eC, eE = c["req"][0] / c["lit"][0] - 1, c["req"][1] / c["lit"][1] - 1
    assert cut == pytest.approx(0.15 * eC / (1 + 0.5 * eE)) and 0.0140 < cut < 0.0146
    h = DE21["DCOH"]
    assert LNF.lowNFeed_cut(h["req"][0], h["lit"][0], h["req"][1], h["lit"][1]) < 1e-4
    # no option where the ration is not above the requirement (l. 90)
    assert LNF.lowNFeed_cut(1.0, 1.0, 50.0, 49.0) is None and LNF.lowNFeed_cut(0.9, 1.0, 50.0, 49.0) is None


def test_the_manure_and_cost_terms():
    """l. 117-120: MANN changes by the cut times (MANN + CRPR_EXPT) / MANN; l. 129-142: the cost factor on the feed
    cost, 0.06 x cut / max(0.001, p_animExcrProtCorrFact - 1 - cut)."""
    assert LNF.lowNFeed_MANN(-0.02, 100.0, 30.0) == pytest.approx(-0.026)
    assert LNF.lowNFeed_costParLin_factor(-0.0143, 1.1009) == pytest.approx(0.06 * 0.0143 / (0.1009 - 0.0143))
    assert LNF.lowNFeed_costParLin_factor(-0.02, 1.01) == pytest.approx(0.06 * 0.02 / 0.001)


def test_the_effects_file_is_on_the_2030_basis():
    """lownfeed_effects.csv: DE21's dairy cows (DCOL and DCOH, weighted by CAPRI's 2030 levels) lose about 0.9% of their
    manure N per adopting head (2017 basis: 3.3%), FR52's about 4% (8.1%), as CAPRI's Green Deal shows per adopting
    head (DE21 DCOL 1.9%, DCOH none; FR52 DCOL 2.7%, DCOH 5.8%)."""
    t = pd.read_csv(CSV).set_index(["region", "animal"])
    de, fr = float(t.at[("DE210000", "DCOW"), "d_mann_rel"]), float(t.at[("FR520000", "DCOW"), "d_mann_rel"])
    assert -0.0125 < de < -0.0065 and -0.050 < fr < -0.030
    assert (t.d_mann_rel <= t.d_crpr_rel + 1e-12).all() and (t.d_crpr_rel < 0).all()

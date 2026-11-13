"""CAPRI's land-use-change estimation of the market outside the EU (luc_market; capri_mod/market/luc.py)."""
from pathlib import Path

import numpy as np
import pandas as pd

from capri_mod.market.luc import LU_CLASSES, LucParams, final_classes, solve_region

MKT = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"


def _params():
    return LucParams.from_frames(*(pd.read_csv(MKT / f"luc_market_{n}.csv", keep_default_na=False)
                                   for n in ("priors", "classes", "shares")))


def _cal_land():
    lm = pd.read_csv(MKT / "noneu_land_market.csv", keep_default_na=False)
    return {r: dict(zip(g.lu, g.land_kha.astype(float))) for r, g in lm.groupby("rms")}


def test_luc_market_reproduces_capris_calibration_point():
    """At CAPRI's 2030 calibration land (the land block's v_land), the shares give the final land per class and the
    system (luClassInitial_, luClassFinal_, FocLUC_ with the gamma priors) gives CAPRI's transitions at CAL in every
    region with the land block (DATA LEVL CAL, sim_ini_21730)."""
    prm, land = _params(), _cal_land()
    assert set(prm.regions) == set(land)
    worst = 0.0
    for r, d in prm.regions.items():
        x, info = solve_region(d, final_classes(d, land[r]))
        assert info["residual"] < 1e-6 * max(1.0, float(d["initial"].max())), r
        worst = max(worst, float(np.max(np.abs(x - d["level_cal"]) / np.maximum(np.abs(d["level_cal"]), 1e-3))))
    assert worst < 1e-6


def test_luc_market_moves_with_the_land():
    """More fodder land and less forest in Brazil: the balances hold at the new final land, the forest-to-grassland
    and forest-to-cropland transitions rise, the forest's own diagonal falls, every transition stays positive."""
    prm, land = _params(), _cal_land()
    d, l0 = prm.regions["BRA"], dict(land["BRA"])
    x0, _ = solve_region(d, final_classes(d, l0))
    l1 = dict(l0)
    shift = 0.01 * l0["FODFAL"]
    l1["FODFAL"] += shift
    l1["FORE"] -= shift
    fin = final_classes(d, l1)
    x1, info = solve_region(d, fin)
    assert info["residual"] < 1e-6 * float(d["initial"].max())
    assert np.allclose(d["To"] @ (d["fac"] * x1), [fin[c] for c in LU_CLASSES], rtol=0, atol=1e-6 * d["initial"].max())
    i = {p: k for k, p in enumerate(d["pos"])}
    assert x1[i["FORGRS"]] > x0[i["FORGRS"]] and x1[i["FORCRP"]] > x0[i["FORCRP"]]
    assert x1[i["FORFOR"]] < x0[i["FORFOR"]]
    assert (x1 > 0).all()

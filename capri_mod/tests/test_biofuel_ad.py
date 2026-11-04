"""Step G2g, first part: CAPRI's biofuel block in CasADi (capri_mod/market/biofuel_ad.py) equals the code biofuel.py had
until 4 November 2026 (written out here as the reference: _biofuel_feed_group, _sigmoid and biofuel_state's
equations)."""
import numpy as np
import pandas as pd
import pytest


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500.0, 500.0)))


def _feed_group_ref(mm, g, ratio, X=None, ddgs_ratio=1.0):
    """BiofuelMixin._biofuel_feed_group before the move."""
    r = np.array([float(ratio.get(c, 1.0)) if c else 1.0 for c in g["comm"]])
    by = g["by"] * np.where(g["ddgs"], float(ddgs_ratio), 1.0)
    mu = np.maximum(g["p0"] * r - by, 1e-6)
    rho = g["rho"]
    mub = float((g["dp"] * mu ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
    if X is None:
        X = g["X0"] * float((mm.biofuel_output_scale or {}).get(g["fuel"], 1.0))
    q = g["dp"] * X * (mub / mu) ** rho
    n = g["num"]
    rest = float((q * g["prcb"]).sum() - q[n] * g["prcb"][n])
    q[n] = max(0.0, (X - rest) / g["prcb"][n])
    return q, mub


def _state_ref(mm, prod_ratio, arm_ratio, mand):
    """biofuel_state's equations before the move (endogenous biofuel markets)."""
    bm, bp = mm._biofuel_market_params(), mm._biofuel_params()
    scale = mm.biofuel_output_scale or {}
    rows = bm.get("rows", {})
    X, MUB, ddgs = {}, {}, {}

    def aratio(reg, c):
        return float(arm_ratio.at[reg, c]) if (c and reg in arm_ratio.index and c in arm_ratio.columns) else 1.0
    for g in bp.get("groups", []):
        reg, key = g["region"], (g["ms"], g["fuel"])
        dr = float(prod_ratio.at[reg, "DDGS"]) if ("DDGS" in prod_ratio.columns and reg in prod_ratio.index) else 1.0
        q1, mub = _feed_group_ref(mm, g, {c: aratio(reg, c) for c in g["comm"] if c}, 1.0, dr)
        MUB[key] = mub
        d = rows.get(key)
        x = g["X0"] * float(scale.get(g["fuel"], 1.0))
        if d is not None and float(d["pr0"]) > 0:
            rb = float(prod_ratio.at[reg, g["fuel"]])
            PR = float(d["ppri"]) * rb / mub
            x = float(d["sup_scale"]) * PR + np.exp(float(d["sup_alfa"]) + float(d["sup_beta"]) * np.log(PR + 1e-2)) \
                * float(_sigmoid(float(d["sup_slope"]) * (PR - float(d["sup_turn"]))))
            x = max(0.0, x)
        X[key] = x
        ddgs[reg] = ddgs.get(reg, 0.0) + float((q1 * x * g["prcby"] * g["ddgs"]).sum())
    use, proc = {}, {}
    for (ms, fuel), d in rows.items():
        reg = d["region"]
        ra = aratio(reg, fuel)
        u = float(d["biof_kt"])
        if float(d["dem_slope"]) != 0.0 and float(d["fossil_cpri"]) > 0:
            cp = max(1e-6, float(d["cpri"]) + float(d["arm1p"]) * (ra - 1.0))
            quts = float(d["quts"]) * (mand if d["mandate_region"] else 1.0)
            share = quts + float(d["dem_max"]) * float(
                _sigmoid(float(d["dem_slope"]) * (cp / float(d["fossil_cpri"]) - float(d["dem_turn"]))))
            u = share * float(d["hcon_kt"]) * float(d["oil_eq_fossil"]) / float(d["oil_eq"])
        use[(reg, fuel)] = use.get((reg, fuel), 0.0) + u
        pc = float(d["proc_kt"])
        if pc > 0 and float(d["proc_hess"]) != 0.0 and float(d["inpe"]) > 0:
            pc = max(0.0, pc - float(d["proc_hess"]) * float(d["arm1p"]) * (ra - 1.0) / float(d["inpe"]))
        proc[(reg, fuel)] = proc.get((reg, fuel), 0.0) + pc
    return {"X": X, "mub": MUB, "use": use, "proc": proc, "ddgs": ddgs}


@pytest.fixture(scope="module")
def market():
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    return MarketModule(load_all_data(Path(__file__).resolve().parents[2] / "capri_data"))


def _rel(a, b):
    return abs(a - b) / max(abs(b), 1e-12)


@pytest.mark.parametrize("seed", [0, 1])
def test_feed_groups_equal_the_former_code(market, seed):
    mm = market
    rng = np.random.default_rng(seed)
    groups = mm._biofuel_params().get("groups", [])
    assert len(groups) > 20
    for g in groups:
        ratio = {c: float(np.exp(0.4 * rng.standard_normal())) for c in g["comm"] if c}
        X, dd = float(rng.uniform(0.2, 3.0)) * g["X0"], float(np.exp(0.3 * rng.standard_normal()))
        q, mub = mm._biofuel_feed_group(g, ratio, X, dd)
        qr, mubr = _feed_group_ref(mm, g, ratio, X, dd)
        assert _rel(mub, mubr) < 1e-13, (g["ms"], g["fuel"])
        assert np.all(np.abs(q - qr) <= 1e-12 * np.maximum(np.abs(qr), 1e-9 * g["X0"])), (g["ms"], g["fuel"], q, qr)
        assert np.allclose(mm._biofuel_feed_group(g, {}, None, 1.0)[0], _feed_group_ref(mm, g, {})[0], rtol=1e-12)


@pytest.mark.parametrize("seed", [0, 1])
def test_biofuel_markets_equal_the_former_code(market, seed):
    """Supply (SupplyBiof_), use (biofDemShare_, biofDem_) and non-fuel processing at random price ratios, the mandate
    shifted; the clipped sigmoid's tails included (prices far from the reference)."""
    mm = market
    rng = np.random.default_rng(10 + seed)
    regs, cols = list(mm.regions), list(mm.commodities)
    P = pd.DataFrame(np.exp(0.5 * rng.standard_normal((len(regs), len(cols)))), index=regs, columns=cols)
    A = pd.DataFrame(np.exp(0.5 * rng.standard_normal((len(regs), len(cols)))), index=regs, columns=cols)
    mm.biofuel_mandate = 1.3
    try:
        new = mm.biofuel_state(P, A, endogenous=True)
        ref = _state_ref(mm, P, A, 1.3)
    finally:
        mm.biofuel_mandate = 1.0
    for k in ("X", "mub", "use", "proc", "ddgs"):
        assert new[k].keys() == ref[k].keys() and len(ref[k]) > 0, k
        for key, v in ref[k].items():
            assert abs(new[k][key] - v) <= 1e-12 * max(abs(v), 1.0), (k, key, new[k][key], v)

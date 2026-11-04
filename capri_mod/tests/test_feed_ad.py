"""Step G2d: CAPRI's non-EU feed block (FeedNQ_, FeedBal_) in CasADi (capri_mod/market/feed_ad.py) equals the loops
feed.py had until 4 November 2026 (written out here as the reference), and FEDE clears the balance's residual."""
import numpy as np
import pandas as pd
import pytest


def _fede_loop(P, arm_ratio, prod_ratio, mr, land):
    """FeedMixin.noneu_fede before the move."""
    out = {}
    for rms, d in P["rms"].items():
        tr = d.get("tr")
        if tr is None or tr not in arm_ratio.index:
            continue
        ra, rp = arm_ratio.loc[tr], prod_ratio.loc[tr] if tr in prod_ratio.index else arm_ratio.loc[tr]
        e0 = aF = 0.0
        for x, q0 in d["feed0"].items():
            k = d["kcal"].get(x, 0.0)
            if not k:
                continue
            dq = 0.0
            for y, h in d["terms"].get(x, {}).items():
                if y == "FEDE":
                    aF += k * h
                elif y in ra.index:
                    dq += h * (float(ra[y]) - 1.0)
            e0 += k * (q0 + dq)
        n0 = aN = 0.0
        for a, cv in d["conv"].items():
            dq = 0.0
            for y, h in d["sterms"].get(a, {}).items():
                if y == "FEDE":
                    aN += cv * h
                elif y == "MILK":
                    dq += h * (float(mr.get(tr, 1.0)) - 1.0)
                elif y in rp.index:
                    dq += h * (float(rp[y]) - 1.0)
            lr = (land or {}).get(rms)
            if lr:
                for u, h in (d.get("lterms") or {}).get(a, {}).items():
                    dq += h * lr.get(u, 0.0)
            n0 += cv * (d["prod0"].get(a, 0.0) + dq)
        den = aF - aN
        out[rms] = 1.0 + (n0 - e0) / den if den > 0 else 1.0
    return out


def _feed_change_loop(P, arm_ratio, fede):
    """FeedMixin.noneu_feed_change before the move."""
    dF = {}
    for rms, d in P["rms"].items():
        tr = d.get("tr")
        if tr is None or tr not in arm_ratio.index:
            continue
        ra = arm_ratio.loc[tr]
        ph = float(fede.get(rms, 1.0))
        for x, q0 in d["feed0"].items():
            xm = d["xm"].get(x)
            if not xm:
                continue
            dq = 0.0
            for y, h in d["terms"].get(x, {}).items():
                if y == "FEDE":
                    dq += h * (ph - 1.0)
                elif y in ra.index:
                    dq += h * (float(ra[y]) - 1.0)
            dF[(tr, xm)] = dF.get((tr, xm), 0.0) + dq
    return {k: v / P["totals"][k] for k, v in dF.items() if P["totals"].get(k, 0.0) > 0}


@pytest.fixture(scope="module")
def market():
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    return MarketModule(load_all_data(Path(__file__).resolve().parents[2] / "capri_data"))


@pytest.mark.parametrize("seed", [0, 1])
def test_feed_block_equals_the_loops(market, seed):
    mm = market
    rng = np.random.default_rng(seed)
    cols = list(mm.commodities)
    A = pd.DataFrame(1.0 + 0.3 * rng.standard_normal((len(mm.regions), len(cols))), index=mm.regions, columns=cols)
    R = pd.DataFrame(1.0 + 0.3 * rng.standard_normal((len(mm.regions), len(cols))), index=mm.regions, columns=cols)
    mr = {r: 1.0 + 0.2 * rng.standard_normal() for r in mm.regions}
    P = mm._noneu_feed_params()
    land = {rms: {u: 30.0 * rng.standard_normal() for t in (d.get("lterms") or {}).values() for u in t}
            for rms, d in P["rms"].items()}
    ref, new = _fede_loop(P, A, R, mr, land), mm.noneu_fede(A, R, mr, land)
    assert ref.keys() == new.keys() and len(ref) > 10
    for k in ref:
        assert abs(new[k] - ref[k]) <= 1e-11 * max(1.0, abs(ref[k])), (k, ref[k], new[k])
    fede = {k: 1.0 + 0.1 * rng.standard_normal() for k in ref}
    r2, n2 = _feed_change_loop(P, A, fede), mm.noneu_feed_change(A, fede)
    assert r2.keys() == n2.keys() and len(r2) > 10
    for k in r2:
        assert abs(n2[k] - r2[k]) <= 1e-12 + 1e-11 * abs(r2[k]), (k, r2[k], n2[k])


def test_fede_clears_the_balance(market):
    """At FEDE = fede_star the FeedBal_ residual is 0 (where the balance responds to FEDE)."""
    mm = market
    P = mm._noneu_feed_params()
    cols = list(mm.commodities)
    n = 0
    for rms, d in list(P["rms"].items())[:30]:
        f, lts = mm._fedebal_fn(rms, d, cols)
        ra = np.full(len(cols), 1.1)
        star, _ = f(ra, ra, 1.05, np.zeros(len(lts)), 1.0)
        _, res = f(ra, ra, 1.05, np.zeros(len(lts)), float(star))
        if float(star) != 1.0:
            assert abs(float(res)) < 1e-6 * max(1.0, sum(d["feed0"].values())), rms
            n += 1
    assert n > 0

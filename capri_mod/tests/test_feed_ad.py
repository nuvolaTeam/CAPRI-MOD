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


def _bulk_loop(d, price_ratio, k):
    """feedBlkPrice_ and feedShareEqu_ as FeedMixin.feed_bulk_price_ratio, eu_feed_use and sup_feed_use had them."""
    r = np.array([max(float(price_ratio.get(c, 1.0)), 1e-6) if c else 1.0 for c in d["comm"]])
    rho = d["rho"]
    pb = float((d["s"] * r ** (1.0 - rho)).sum()) ** (1.0 / (1.0 - rho))
    return pb, d["q0"] * k * (pb / r) ** rho


@pytest.mark.parametrize("seed", [0, 1])
def test_feed_bulks_equal_the_loops(market, seed):
    """The EU's and the supply-model countries' feed bulks (feed_ad.feedblk_function) equal the loops feed.py had
    until 4 November 2026: the bulk price index, and the feed use per commodity summed over the bulks."""
    mm = market
    rng = np.random.default_rng(seed)
    fb = mm._feed_bulk_params()
    comm = sorted({c for d in list(fb["bulks"].values()) + list((fb.get("bulks_sup") or {}).values())
                   for c in d["comm"] if c})
    pr = {c: float(np.exp(0.3 * rng.standard_normal())) for c in comm}
    pr[comm[0]] = -0.5                                     # the floor at 1e-6
    bix = {k: float(np.exp(0.2 * rng.standard_normal())) for k in fb["bulks"]}
    bf = {k: float(np.exp(0.1 * rng.standard_normal())) for k in fb["bulks"]}
    old = mm.seen.feed_bulk_index
    mm.seen.feed_bulk_index = bix
    try:
        ref = {}
        for (ms, b), d in fb["bulks"].items():
            pb, q = _bulk_loop(d, pr, bix[(ms, b)] * bf[(ms, b)])
            assert abs(mm.feed_bulk_price_ratio(ms, b, pr) - _bulk_loop(d, pr, 1.0)[0]) <= 1e-13 * pb
            for c, x in zip(d["comm"], q):
                if c:
                    ref[c] = ref.get(c, 0.0) + float(x)
        new = mm.eu_feed_use(pr, bulk_factor=bf)
        assert ref.keys() == new.keys() and len(ref) > 5
        for c in ref:
            assert abs(new[c] - ref[c]) <= 1e-12 * max(1.0, abs(ref[c])), (c, ref[c], new[c])
        for reg, mss in mm.SUP_NONEU_MS.items():
            ref = {}
            for (ms, b), d in (fb.get("bulks_sup") or {}).items():
                if ms in mss:
                    for c, x in zip(d["comm"], _bulk_loop(d, pr, 1.0)[1]):
                        if c:
                            ref[c] = ref.get(c, 0.0) + float(x)
            new = mm.sup_feed_use(reg, pr)
            assert ref.keys() == new.keys()
            for c in ref:
                assert abs(new[c] - ref[c]) <= 1e-12 * max(1.0, abs(ref[c])), (reg, c, ref[c], new[c])
    finally:
        mm.seen.feed_bulk_index = old


def test_feed_bulk_market_factor_equals_the_loop(market, monkeypatch):
    """feedBlk_'s response within the market solve (feed_ad.feedblk_factor_function): exp(sum e log(r / r_seen)) over
    the prices given and positive, as FeedMixin.feed_bulk_market_factor had it until 4 November 2026."""
    mm = market
    rng = np.random.default_rng(4)
    fb = mm._feed_bulk_params()
    comm = sorted({c for d in fb["bulks"].values() for c in d["comm"] if c})
    E = {k: {y: float(rng.uniform(-0.5, 0.5)) for y in rng.choice(comm, 6, replace=False)} for k in list(fb["bulks"])[:40]}
    monkeypatch.setattr(mm, "_feed_bulk_elas", lambda: E)
    seen = {c: float(np.exp(0.2 * rng.standard_normal())) for c in comm}
    seen[comm[1]] = 0.0                                    # a price seen at 0: its term left out
    monkeypatch.setattr(mm.seen, "eu_price_seen", seen)
    prices = {c: float(np.exp(0.3 * rng.standard_normal())) for c in comm[3:]}   # some prices not given
    prices[comm[4]] = -1.0                                 # a negative price: its term left out
    from capri_mod import settings
    with settings.override({"market.feed_bulk_in_market": True}):
        new = mm.feed_bulk_market_factor(prices)
    assert new.keys() == E.keys()
    for k, el in E.items():
        s = 0.0
        for y, e in el.items():
            r = prices.get(y)
            if r is None:
                continue
            sv = float(seen.get(y, 1.0))
            if r > 0 and sv > 0:
                s += e * np.log(float(r) / sv)
        assert abs(new[k] - np.exp(s)) <= 1e-13 * np.exp(s), (k, new[k], np.exp(s))

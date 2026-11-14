"""G3.2d: the market's use side in CasADi (capri_mod/market/use_ad.py) equals MarketModule.demand_response at random
prices, feed energy prices, raw milk deliveries and biofuel outputs, on the market of a solved baseline."""
import numpy as np
import pandas as pd
import pytest


@pytest.mark.slow
def test_the_use_side_in_casadi_equals_demand_response(solved_market):
    from capri_mod.market.use_ad import use_function, use_inputs
    mm = solved_market
    regions, comms = list(mm.regions), list(mm.commodities)
    nR, nC = len(regions), len(comms)
    rng = np.random.default_rng(14112026)
    dom0 = mm._dom0().reindex(index=regions, columns=comms)
    oc = sorted({x for v in mm.CRUSH_CHAINS.values() for x in v if x in comms})
    fede0 = dict(mm.ev.fede_now or {})
    milk0 = (mm.ev.eu_milk_supply_now, dict(mm.ev.sup_milk_now or {}), dict(mm.ev.world_milk_now or {}))
    worst, checked, base = 0.0, 0, None
    for trial in range(3):
        PRr = rng.uniform(0.8, 1.25, (nR, nC)) if trial else np.ones((nR, nC))
        RBr = rng.uniform(0.8, 1.25, (nR, nC)) if trial else np.ones((nR, nC))
        mm.ev.bilat_ratio_now = pd.DataFrame(RBr, index=regions, columns=comms)
        if fede0:
            mm.ev.fede_now = {k: float(v) * (rng.uniform(0.9, 1.1) if trial else 1.0) for k, v in fede0.items()}
        if isinstance(milk0[0], dict):
            mm.ev.eu_milk_supply_now = {k: float(v) * rng.uniform(0.95, 1.05) for k, v in milk0[0].items()}
        mm.ev.sup_milk_now = {k: float(v) * rng.uniform(0.95, 1.05) for k, v in milk0[1].items()}
        mm.ev.world_milk_now = {k: float(v) * rng.uniform(0.95, 1.05) for k, v in milk0[2].items()}
        dp = dom0 * PRr
        cpd = dp.copy()
        cpd[oc] = dom0[oc] * mm.ev.bilat_ratio_now[oc]
        mm.ev.crush_prices_now = cpd
        D_num = mm.demand_response(dp, mm.world_prices_base).reindex(index=regions, columns=comms)
        f, lay = use_function(mm)
        D_ad = np.asarray(f(*use_inputs(mm, lay)), float)
        mm.ev.crush_prices_now = None
        ref = D_num.to_numpy(dtype=float)
        d = np.abs(D_ad - ref) / np.maximum(np.abs(ref), 1.0)
        worst = max(worst, float(d.max()))
        checked += int((ref > 0).sum())
        if trial == 0:
            base = ref
        else:
            # the random prices move the use (the check is not between two constants)
            assert float((np.abs(ref - base) / np.maximum(np.abs(base), 1.0)).max()) > 0.05
    assert checked > 1000
    assert worst <= 1e-12, worst

"""G3.2c/e: the market's supply side as one CasADi function with its blocks' equations (capri_mod/market/
supply_system_ad.py) equals MarketModule.supply_response, and the blocks' residuals vanish, at the evaluation's own
block solutions: at a solved market and at random prices around it (the market of the model's data at CAPRI's base
supply rows: crushing, the dairy blocks, the non-EU ProdNQ_ rows with FEDE and the land rents, biofuels). The young
animals, the member states' raw milk response and Norway's supply models need a supply run's state: checked at captured
solves of a Farm-to-Fork run (tools/check/g3_supply_system.py, G3_SYSTEM.md)."""
import numpy as np
import pytest


@pytest.mark.slow
def test_the_supply_system_equals_supply_response_at_its_block_solutions():
    from pathlib import Path
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.market.supply_system_ad import supply_inputs, supply_system
    root = Path(__file__).resolve().parents[2]
    mm = MarketModule(load_all_data(str(root / "capri_data")))
    exo = mm.capri_base_supply_rows()
    assert mm.solve(exogenous_supply=exo).converged
    r0 = mm.sv.bilat_last_r.copy()
    rng = np.random.default_rng(14112026)
    byp = {(reg, p) for reg in mm.EU for p in mm.eu_feed_byproduct_output(reg)}
    base = None
    for trial in range(3):
        r = r0 * (rng.uniform(0.85, 1.2, r0.shape) if trial else 1.0)
        S1, _, PAr, _, _ = mm._bilateral_eval(r, exo, None)
        f, lay = supply_system(mm, exo)
        PA = PAr.reindex(index=lay["regions"], columns=lay["cols"]).fillna(1.0).to_numpy(dtype=float)
        out = f(*supply_inputs(mm, lay, PA))
        S = np.asarray(out[0], float)
        ref = S1.reindex(index=lay["regions"], columns=lay["cols"]).to_numpy(dtype=float)
        d = np.abs(S - ref) / np.maximum(np.abs(ref), 1.0)
        for i, rg in enumerate(lay["regions"]):
            for j, c in enumerate(lay["cols"]):
                if (rg, c) in byp:
                    d[i, j] = 0.0
        assert float(d.max()) <= 1e-12, (trial, float(d.max()))
        for k in (2, 3):
            e = np.asarray(out[k], float).ravel()
            assert e.size and float(np.abs(e).max()) <= 1e-8, (trial, k, float(np.abs(e).max()))
        if base is None:
            base = ref
        else:
            # the random prices move the supply (the check is not between two constants)
            assert float((np.abs(ref - base) / np.maximum(np.abs(base), 1.0)).max()) > 0.05

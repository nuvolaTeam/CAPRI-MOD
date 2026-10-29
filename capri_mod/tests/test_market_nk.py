"""Step G2: the market's Newton-Krylov solve (capri_mod/market/market_nk.py) reaches the default solve's equilibrium."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.mark.slow
def test_newton_krylov_reaches_the_default_solves_equilibrium():
    """The full market (every trade region, CAPRI's base data) after a 10% cut of EU beef and 5% of EU soft wheat:
    the Newton-Krylov solve and the default successive linearisation stop at the same prices (relative 1e-6: both stop
    at the market tolerance 1e-7 on the residuals)."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.market.market_module import MarketModule
    from capri_mod.settings import override
    data = load_all_data(str(Path(__file__).resolve().parents[2] / "capri_data"))
    out = {}
    for solver in ("fixed_point", "newton_krylov"):
        with override({"market.solver": solver}):
            mm = MarketModule(data)
            exo = pd.DataFrame(0.0, index=["EU27"], columns=MARKET_COMMODITIES)
            for c in MARKET_COMMODITIES:
                if c in mm.par.base_production.columns:
                    exo.at["EU27", c] = mm.par.base_production.at["EU27", c]
            eq0 = mm.solve(exogenous_supply=exo)
            mm.set_eu_base(exo.loc["EU27"], eq0.consumption.loc["EU27"])
            exo1 = exo.copy()
            exo1.at["EU27", "BEEF"] *= 0.9
            exo1.at["EU27", "SWHE"] *= 0.95
            eq1 = mm.solve(exogenous_supply=exo1)
            assert eq1.converged
            out[solver] = eq1.domestic_prices
    a, b = out["fixed_point"], out["newton_krylov"]
    rel = (a - b).abs() / a.abs().clip(lower=1e-9)
    top = rel.stack().sort_values(ascending=False).head(5)
    print("largest differences:", top.to_dict(), {k: (a.loc[k], b.loc[k]) for k in top.index[:3]})
    assert float(np.nanmax(rel.to_numpy())) < 1e-6

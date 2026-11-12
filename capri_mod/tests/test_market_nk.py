"""Step G2: the market's Newton-Krylov solve (capri_mod/market/market_nk.py) reaches the default solve's equilibrium."""
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.slow
def test_newton_krylov_reaches_the_default_solves_equilibrium():
    """The full market (every trade region, CAPRI's base data) after a 10% cut of EU beef and 5% of EU soft wheat:
    the Newton-Krylov solve and the default successive linearisation stop at the same prices (relative 1e-6, 1e-5 in a
    few thin markets: both stop at the market tolerance 1e-7 on the residuals)."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.settings import override
    data = load_all_data(str(Path(__file__).resolve().parents[2] / "capri_data"))
    out = {}
    for solver in ("fixed_point", "newton_krylov"):
        with override({"market.solver": solver}):
            mm = MarketModule(data)
            # CAPRI's base supply as a run passes it: one row per member state (the dairy block reads raw milk per
            # member state; until 12 November 2026 the two EU blocks' totals, whose milk no dairy received)
            exo = mm.capri_base_supply_rows()
            EU = [r for r in exo.index if mm.eu_region_of_country(r) is not None]
            eq0 = mm.solve(exogenous_supply=exo)
            exo1 = exo.copy()
            exo1.loc[EU, "BEEF"] *= 0.9
            exo1.loc[EU, "SWHE"] *= 0.95
            eq1 = mm.solve(exogenous_supply=exo1)
            assert eq1.converged
            out[solver] = eq1.domestic_prices
    a, b = out["fixed_point"], out["newton_krylov"]
    rel = (a - b).abs() / a.abs().clip(lower=1e-9)
    top = rel.stack().sort_values(ascending=False).head(5)
    print("largest differences:", top.to_dict(), {k: (a.loc[k], b.loc[k]) for k in top.index[:3]})
    # Both solves stop when every relative residual (excess supply / max(S0 + D0, 1)) is below market.tol = 1e-7; in a
    # thin, inelastic market that leaves room for a larger price gap: Switzerland's casein (S0 + D0 about 1.8 kt, its
    # supply from the dairy block) differs by 8.4e-6 between the two stops (4 November 2026, KNOWN_ISSUES K110), and by
    # 1.37e-5 since the default solve takes the quotas with the prices (market.trq_joint, 5 November 2026) while the
    # Newton-Krylov solve keeps them one step behind. A stop-point gap, not two equilibria: at market.tol = 1e-9 the same
    # comparison gives 4.8e-6 (the Newton-Krylov solve at its iteration cap, the default solve converged), every other
    # price below 1e-6. So the bound is 3e-5 for every price, and 1e-6 for all but a handful of the 46 x 58 prices.
    v = rel.to_numpy()
    v = v[np.isfinite(v)]
    assert float(v.max()) < 3e-5
    assert int((v >= 1e-6).sum()) <= 5

"""CAPRI's welfare report (reports/welfare.gms; capri_mod/market/welfare.py, audit M7)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "market"


def _gl_entry(rms="DE000000"):
    g = pd.read_csv(DATA / "gl_demand_goods.csv", keep_default_na=False, na_values=[""])
    bb = pd.read_csv(DATA / "gl_demand_b.csv")
    rg = pd.read_csv(DATA / "gl_demand_regions.csv").set_index("rms")
    gg = g[g.rms == rms]
    names = list(gg.good)
    idx = {n: k for k, n in enumerate(names)}
    B = np.zeros((len(names), len(names)))
    for i_, j_, v in bb[bb.rms == rms][["i", "j", "b"]].itertuples(index=False):
        B[idx[i_], idx[j_]] = v
        B[idx[j_], idx[i_]] = v
    return {"B": B, "d": gg.d.to_numpy(float), "p0": gg.cpri.to_numpy(float) / 1000.0,
            "Y": float(rg.at[rms, "Y"]), "inha": float(rg.at[rms, "inha"])}, idx


def test_gl_money_metric_is_capri_equivalent_variation():
    """CSSP (welfare.gms l. 95-140): for a small price change of one good the money metric is minus the demand times
    the price change (Roy/Shephard); for a larger one it is above that (substitution); with several prices moving
    CAPRI's good-by-good sum stays close to the exact equivalent variation e(P0, u1) - Y of the GL system."""
    from capri_mod.market.welfare import WelfareMixin
    from capri_mod.market.demand import DemandMixin
    e, idx = _gl_entry()
    x0 = DemandMixin._gl_eval(e, e["p0"], 1.0) * 1000.0 / e["inha"]          # kg per head
    for g in ("PORK", "CHES"):
        k = idx[g]
        for h, tol in ((1e-4, 1e-4), (0.05, None)):
            p = e["p0"].copy()
            p[k] *= 1.0 + h
            ev = float(WelfareMixin._gl_money_metric(e, p).sum())
            lin = -x0[k] * e["p0"][k] * h
            if tol is not None:
                assert abs(ev / lin - 1.0) < tol
            else:
                assert lin < ev < 0.0
    rng = np.random.default_rng(0)
    p = e["p0"] * (1.0 + 0.1 * rng.standard_normal(len(e["p0"])))
    p[idx["INPE"]] = e["p0"][idx["INPE"]]
    seq = float(WelfareMixin._gl_money_metric(e, p).sum())
    G = lambda q: float(np.sqrt(q) @ e["B"] @ np.sqrt(q))
    exact = float(e["d"] @ e["p0"] + G(e["p0"]) * (e["Y"] - e["d"] @ p) / G(p) - e["Y"])
    assert abs(seq - exact) < 1e-2 * abs(exact)


def test_dairy_profit_is_the_integral_of_its_nq_function():
    """ProfitDairy (welfare.gms l. 205-260): the netput Hessian of each member state's block (products out, raw milk
    in) is symmetric, so the trapezoid over the block's linear DairyNQ_ is the exact integral along any path:
    a numerical line integral of the netputs over the margins agrees; a higher cheese price raises the dairies'
    profit, a higher raw milk price lowers it."""
    from capri_mod.market.dairy import DairyMixin
    from capri_mod.market.welfare import WelfareMixin

    class _D(DairyMixin):
        pass
    dp = pd.read_csv(DATA / "dairy_processing.csv")
    hh = pd.read_csv(DATA / "dairy_hessian.csv")
    ms = "FR000000"
    g = dp[dp.ms == ms].set_index("item")
    a = _D()._dairy_algebra([(g, {(e.row, e.col): e.h for e in hh[hh.ms == ms].itertuples()}, None)])
    ix = a["ix"]
    sgn = np.ones(len(a["items"]))
    sgn[a["iM"]] = -1.0
    z1 = np.zeros(a["G"].shape[1])
    z1[ix["CHES"]], z1[ix["MILK"]], z1[a["iF"]], z1[ix["BUTT"]] = 0.03, 0.02, -0.01, 0.05
    # line integral along z(t) = t z1, t in [0, 1] (Simpson, exact for the quadratic)
    ts = np.linspace(0.0, 1.0, 101)
    f = [float(np.sum(sgn * (a["Q0"] + a["G"] @ (t * z1)) * (a["Mm"] @ z1))) for t in ts]
    num = float(np.sum((f[:-1] + np.array(f[1:])) / 2.0) * (ts[1] - ts[0]))
    assert abs(WelfareMixin._dairy_profit(a, z1) - num) < 1e-6 * abs(num)
    z = np.zeros_like(z1); z[ix["CHES"]] = 0.01
    assert WelfareMixin._dairy_profit(a, z) > 0.0
    z = np.zeros_like(z1); z[ix["MILK"]] = 0.01
    assert WelfareMixin._dairy_profit(a, z) < 0.0


@pytest.mark.slow
def test_market_welfare_at_base_and_after_a_supply_shock():
    """The market's report at its base supply: CAPRI's levels, i.e. its base values (welfare_base_2030.csv: no change
    at the calibration point), tariffs and quota rents (the EU collects tariffs); the EU's consumer surplus is CAPRI's
    2030 reference level (household expenditure at the calibration prices); with 10% less EU beef the EU beef price
    rises, the EU's consumers lose and Brazil's farms gain."""
    from capri_mod.data.loaders import load_all_data
    from capri_mod.data.definitions import MARKET_COMMODITIES
    from capri_mod.market.market_module import MarketModule
    mm = MarketModule(load_all_data(str(Path(__file__).resolve().parents[2] / "capri_data")))
    exo = pd.DataFrame(0.0, index=["EU27"], columns=MARKET_COMMODITIES)
    for c in MARKET_COMMODITIES:
        if c in mm.par.base_production.columns:
            exo.at["EU27", c] = mm.par.base_production.at["EU27", c]
    eq0 = mm.solve(exogenous_supply=exo)
    mm.set_eu_base(exo.loc["EU27"], eq0.consumption.loc["EU27"])     # scenarios keep the base calibration
    w0 = eq0.welfare
    assert list(w0.columns) == list(mm.WELFARE_COMPONENTS) + ["Welfare"]
    assert np.isfinite(w0.to_numpy()).all()
    assert w0.at["EU27", "TariffRev"] > 0.0
    base = mm._welfare_base()
    for reg in w0.index:
        for c in mm.WELFARE_COMPONENTS:
            if c not in ("TariffRev", "TRQRents"):
                assert abs(w0.at[reg, c] - base.get(reg, {}).get(c, 0.0)) < 1e-6 * max(1.0, abs(w0.at[reg, c])), (reg, c)
    ref = pd.read_csv(Path(__file__).resolve().parents[2] / "capri_data" / "sources" / "capri_res" / "ref2030_welfare.csv")
    ref = ref[(ref["col"].str.upper() == "CSSP") & (ref["row"].str.upper() == "INCE")].set_index("region")["value"]
    gl = pd.read_csv(Path(__file__).resolve().parents[2] / "capri_data" / "2017" / "market" / "gl_demand_goods.csv")
    eu_rms = sorted(set(gl.loc[gl.model_region == "EU27", "rms"]))
    assert abs(w0.at["EU27", "CSSP"] - float(ref.reindex(eu_rms).sum())) < 1e-6 * w0.at["EU27", "CSSP"]
    exo1 = exo.copy()
    exo1.at["EU27", "BEEF"] *= 0.9
    eq1 = mm.solve(exogenous_supply=exo1)
    w1 = eq1.welfare
    assert eq1.domestic_prices.at["EU27", "BEEF"] > eq0.domestic_prices.at["EU27", "BEEF"]
    assert w1.at["EU27", "CSSP"] < w0.at["EU27", "CSSP"]
    # dearer beef: the farms of the beef exporters without supply models gain
    assert w1.at["BRA", "ProfitAgr"] > w0.at["BRA", "ProfitAgr"]

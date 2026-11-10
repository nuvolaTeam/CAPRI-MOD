"""Does the market alone reproduce CAPRI's 2030 calibrated market in every market region? (MARKET_REGIONS_INVENTORY §5,
stages 2-3: "base reproduces")

The market module is built from the model's data, the supply of the EU's and the other supply-model countries'
market regions held at their base production, and solved at base world prices with no scenario. Its production,
trade flows and market prices per region are compared with CAPRI's 2030 market data the market is calibrated on
(capri_data/2030/market/bilateral_regions_2030.csv: PMRK and PROD per market region; bilateral_flows_2030.csv:
ImportQ per pair; CAPRI's markmarket_greendeal_1730et_base_1717 dataOut, tools/build/build_bilateral_market.py).

Prints, per region: the largest relative gaps of production and prices, and the flows' total absolute gap; then the
worst cells overall. Exit status 1 when a region's production or a flow differs by more than --tol (relative, default
1e-6) or a price by more than --price-tol (default 1e-6).

    python tools/check/check_market_base.py [--tol 1e-6] [--price-tol 1e-6] [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MKT = ROOT / "capri_data" / "2017" / "market"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=1e-6)
    ap.add_argument("--price-tol", type=float, default=1e-6)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    data = load_all_data(ROOT / "capri_data")
    data["market_year"] = 2030                         # CAPRI's 2030 market (the projection layer sets it in a run)
    mm = MarketModule(data)
    held = list(mm.EU) + list(getattr(mm, "SUP", ()))
    bp = mm.par.base_production
    exo = pd.DataFrame(0.0, index=held, columns=list(mm.commodities))
    for r in held:
        for c in mm.commodities:
            if c in bp.columns and r in bp.index:
                exo.at[r, c] = float(bp.at[r, c])
    eq = mm.solve(exogenous_supply=exo)
    rg = pd.read_csv(MKT.parents[1] / "2030" / "market" / "bilateral_regions_2030.csv", float_precision="round_trip")
    fl = pd.read_csv(MKT.parents[1] / "2030" / "market" / "bilateral_flows_2030.csv", float_precision="round_trip")
    rows = []
    for t in rg.itertuples(index=False):
        if t.region not in eq.production.index or t.commodity not in eq.production.columns:
            continue
        q = float(eq.production.at[t.region, t.commodity])
        p = float(eq.domestic_prices.at[t.region, t.commodity])
        rows.append(dict(kind="production", region=t.region, commodity=t.commodity, model=q, capri=float(t.prod_kt)))
        rows.append(dict(kind="price", region=t.region, commodity=t.commodity, model=p, capri=float(t.pmrk)))
    tf = eq.trade_flows
    for t in fl.itertuples(index=False):
        if t.importer == t.exporter or t.commodity not in tf.columns:
            continue
        k = (t.exporter, t.importer)
        q = float(tf.at[k, t.commodity]) if k in tf.index else 0.0
        rows.append(dict(kind="flow", region=t.importer, partner=t.exporter, commodity=t.commodity, model=q,
                         capri=float(t.q_kt)))
    d = pd.DataFrame(rows)
    d["gap"] = d.model - d.capri
    d["rel"] = d.gap.abs() / d.capri.abs().clip(lower=1.0)
    if a.csv:
        d.to_csv(a.csv, index=False)
    print(f"market converged: {eq.converged}, {eq.iterations} rounds; {d.region.nunique()} regions compared")
    for kind in ("production", "price", "flow"):
        g = d[d.kind == kind]
        print(f"{kind:10s}: {len(g)} cells, max relative gap {g.rel.max():.3g}, mean {g.rel.mean():.3g}, "
              f"above 1e-6: {(g.rel > 1e-6).sum()}, above 1e-3: {(g.rel > 1e-3).sum()}")
    per = d.groupby(["region", "kind"]).rel.max().unstack().fillna(0.0)
    print(per.sort_values(list(per.columns), ascending=False).head(20).to_string(float_format=lambda x: f"{x:.2e}"))
    print(d.sort_values("rel", ascending=False).head(25).to_string(index=False, float_format=lambda x: f"{x:.6g}"))
    bad = ((d.kind != "price") & (d.rel > a.tol)) | ((d.kind == "price") & (d.rel > a.price_tol))
    sys.exit(1 if bad.any() else 0)


if __name__ == "__main__":
    main()

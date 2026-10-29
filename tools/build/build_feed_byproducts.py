"""CAPRI's residual feed products FENI and FPRI as markets (arm/market_model.gms MaprFeed_; Sprint 9h).

CAPRI trades two residual feeds (set RESIMP) bilaterally like any market product: FENI, energy-rich feed
(sugar-beet processing by-products, manioc, cassava, roots and tubers), in the energy bulk FENE, and FPRI, the
by-products of milling, in the protein bulk FPRO. Their only use is feed (DOMM = FEED). In the regions with supply
models their output is a fixed share of the processing of the parent products (MaprFeed_):

  v_prodQuant(r, RESIMP) = p_feedByProdShare(r, RESIMP) x sum_{XX in RESIMP_T_O} [HCon + Proc (+ BiofProc for SUGA)]
  RESIMP_T_O: FPRI <- WHEA, SWHE, DWHE, RYEM, BARL, OATS, MAIZ, OCER, PARI;  FENI <- SUGA

elsewhere a supply function (prodNQ_) with CAPRI's own-price supply elasticities.

The model's EU is one market region, so the share is the EU's: EU production of the 2030 reference over the
2030 human consumption (HCOM) and processing (PRCM) of the parents, with sugar's biofuel processing (BIOF) for FENI
(CAPRI's EU27 balance, capri_eu27_market_balance_2030_ref.json); each parent model commodity's weight is its part
of that sum, and the market moves the output with the parents' food and processing use (MarketModule).

Output:
  capri_data/2017/market/feed_byproducts.csv   product, commodity, use (food|biofuel), base_kt, weight, prod0_kt

The world prices of FENI, FPRI and nine other products, which this builder wrote into world_prices.csv in place until
29 October 2026, are written with every other row by tools/build/build_world_prices.py (the table's one writer).

    python tools/build/build_feed_byproducts.py
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
MKT = ROOT / "capri_data" / "2017" / "market"
#: CAPRI RESIMP_T_O (global/fromimpact/sets.gms) mapped to model commodities, with the balance items CAPRI sums
PARENTS = {"FPRI": {"SWHE": ("WHEA", "SWHE", "DWHE"), "BARL": ("BARL",), "CORN": ("MAIZ",),
                    "OCER": ("OCER",), "RYEM": ("RYEM",), "OATS": ("OATS",), "PARI": ("PARI",)},
           "FENI": {"SUGR": ("SUGA",)}}


def main():
    bal = json.load(open(ROOT / "capri_data" / "validation" / "capri_eu27_market_balance_2030_ref.json"))["products"]
    # the EU's production: the model's EU27 trade region (tools/build/build_bilateral_market.py)
    breg = _read_csv(MKT / "bilateral_regions_2030.csv")
    rows = []
    for rp, par in PARENTS.items():
        p0 = float(breg.loc[(breg.commodity == rp) & (breg.region == "EU27"), "prod_kt"].sum())
        parts = []
        for c, caps in par.items():
            food = sum(float(bal.get(x, {}).get(k, 0.0)) for x in caps for k in ("HCOM", "PRCM"))
            parts.append((c, "food", food))
            if rp == "FENI":
                parts.append((c, "biofuel", sum(float(bal.get(x, {}).get("BIOF", 0.0)) for x in caps)))
        tot = sum(q for _, _, q in parts)
        for c, use, q in parts:
            if q > 0:
                rows.append(dict(product=rp, commodity=c, use=use, base_kt=q, weight=q / tot,
                                 prod0_kt=p0))
        print(f"{rp}: EU production {p0:.0f} kt = {p0 / tot:.4f} x {tot:.0f} kt of parent use")
    pd.DataFrame(rows).to_csv(MKT / "feed_byproducts.csv", index=False)


if __name__ == "__main__":
    main()

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

Outputs:
  capri_data/2017/market/feed_byproducts.csv   product, commodity, use (food|biofuel), base_kt, weight, prod0_kt
  capri_data/2017/market/world_prices.csv      + FENI, RYEM, OATS, TAGR, TOBA, TABO, TEXT, PLMO, OTHO (FAO_agg World PMRK BAS, as the other rows), FPRI (FAO_agg
                                               has no world price for it: CAPRI's 2017 market, export-weighted
                                               market prices of the exporting regions, bilateral_*_2017.csv)
  capri_data/sources/world_price_provenance.json  + FENI, FPRI

    python tools/build/build_feed_byproducts.py
"""
from __future__ import annotations
import json, re
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
MKT = ROOT / "capri_data" / "2017" / "market"
FAO = Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt")
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

    # world prices
    wp = _read_csv(MKT / "world_prices.csv", index_col=0)
    col = wp.columns[0]
    prov_f = ROOT / "capri_data" / "sources" / "world_price_provenance.json"
    prov = json.load(open(prov_f))
    if FAO.exists():
        # FENI, and the CAPRI market products added later (rye, oats: CERE_DEF; table grapes, tobacco)
        for line in open(FAO, errors="ignore"):
            m = re.match(r"^'World'\.'PMRK'\.'(FENI|RYEM|OATS|TAGR|TOBA|TABO|TEXT|PLMO|OTHO|FFIS|SFIS|OAQU|COFF|TEAS|COCO)'\.'BAS'\s+([-\d.Ee+]+)", line)
            if m:
                p = m.group(1)
                wp.loc[p, col] = float(m.group(2))
                prov[p] = {"capri_code": p, "source": "FAO_agg_17_defaulta p_dataMarket 'World'.'PMRK'.'BAS'",
                           "previous": None}
    fl = _read_csv(MKT / "bilateral_flows_2017.csv")
    f = fl[(fl.commodity == "FPRI") & (fl.importer != fl.exporter)]
    rg = _read_csv(MKT / "bilateral_regions_2017.csv")
    pm = rg[rg.commodity == "FPRI"].set_index("region")["pmrk"]
    ex = f.groupby("exporter")["q_kt"].sum()
    fp = float(sum(q * float(pm.get(r, 0.0)) for r, q in ex.items()) / ex.sum())
    wp.loc["FPRI", col] = fp
    prov["FPRI"] = {"capri_code": "FPRI", "source": "CAPRI market_base_1717: export-weighted PMRK of the exporting "
                    "regions (FAO_agg has no World PMRK for FPRI); tools/build/build_feed_byproducts.py", "previous": None}
    wp.to_csv(MKT / "world_prices.csv")
    json.dump(prov, open(prov_f, "w"), indent=1)
    print(f"world prices: FENI {wp.at['FENI', col]}, FPRI {fp:.2f}")


if __name__ == "__main__":
    main()

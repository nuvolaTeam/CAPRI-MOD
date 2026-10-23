"""Build the non-EU market regions' own-price supply elasticities from CAPRI's calibrated market model.

CAPRI's market model gives every non-EU region its own supply function (arm/market_model.gms, normalised quadratic
with the Hessian p_hessNQSupp calibrated to p_elasSupp(region, product, product', "CAL")). capri-mod's market used one
own-price elasticity per product for every non-EU region (CAPRI's EU median, else the Armington eps). This builder
takes CAPRI's own-price p_elasSupp per CAPRI region (sources/arm/capri_supply_elas_market_1717.csv, from the 2017
calibration run's elas_2_1717 file) and aggregates it to the model's trade regions with CAPRI's 2017 production
(sources/market/bilateral_dataout_2017.csv.xz, item PROD) as weights, through the same region and product maps as the
bilateral market (tools/build/recalibrate_trade_2017.py REGION_MAP, CAPRI regions not mapped there being the model's ROW;
tools/build/build_bilateral_market.py MODEL). Products CAPRI's market produces by processing (dairy products, oils and cakes,
biofuels, DDGS) have no p_elasSupp and keep the market's previous value.

REGISTERED: own-price terms only. CAPRI's non-EU supply functions also carry cross-price terms (p_elasSupp off the
diagonal, p_hessNQSupp); the model's non-EU supply stays one-product-at-a-time.

Output: capri_data/2017/market/supply_elas_region.csv
    region, commodity, elasticity, capri_regions, prod_kt
(only region-commodity pairs with a CAPRI value and CAPRI production; the market keeps its previous value elsewhere)

    python tools/build/build_supply_elas_nonEU.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]

ELAS = ROOT / "capri_data" / "sources" / "arm" / "capri_supply_elas_market_1717.csv"
PROD = ROOT / "capri_data" / "sources" / "market" / "bilateral_dataout_2017.csv.xz"
OUT = ROOT / "capri_data" / "2017" / "market" / "supply_elas_region.csv"


def main():
    from recalibrate_trade_2017 import REGION_MAP, AGGREGATES
    from build_bilateral_market import MODEL as CAPRI_CODES          # model commodity -> CAPRI product(s)
    from build_feed_bulks import EU_MS
    from capri_mod.data.definitions import MARKET_COMMODITIES

    el = pd.read_csv(ELAS)
    own = el[el["prod"] == el["wrt"]][["region", "prod", "value"]]
    src = pd.read_csv(PROD, keep_default_na=False)
    prod = src[(src["item"] == "PROD") & (src["r2"] == "")][["r1", "product", "value"]]
    prod = prod.assign(value=pd.to_numeric(prod["value"], errors="coerce").fillna(0.0))
    pw = {(r, p): v for r, p, v in prod.itertuples(index=False)}

    eu = set(EU_MS) | {"EU27yr19"}
    def trade_region(r):
        if r in eu or r in AGGREGATES:
            return None
        return REGION_MAP.get(r, "ROW")

    rows = []
    for c in MARKET_COMMODITIES:
        codes = CAPRI_CODES.get(c, (c,))
        if len(codes) != 1:
            continue
        k = codes[0]
        g = own[own["prod"] == k]
        acc = {}
        for r, _, e in g.itertuples(index=False):
            tr = trade_region(r)
            w = float(pw.get((r, k), 0.0))
            if tr is None or tr == "EU27" or w <= 0:
                continue
            a = acc.setdefault(tr, [0.0, 0.0, []])
            a[0] += w * float(e); a[1] += w; a[2].append(r)
        for tr, (num, den, regs) in sorted(acc.items()):
            rows.append({"region": tr, "commodity": c, "elasticity": round(num / den, 6),
                         "capri_regions": " ".join(sorted(regs)), "prod_kt": round(den, 3)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"{OUT.relative_to(ROOT)}: {len(out)} region-commodity pairs, {out.region.nunique()} regions, "
          f"{out.commodity.nunique()} commodities; elasticity median {out.elasticity.median():.3f}, "
          f"range {out.elasticity.min():.3f} to {out.elasticity.max():.3f}")


if __name__ == "__main__":
    main()

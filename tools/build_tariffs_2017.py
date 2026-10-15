"""Import protection per trade region and commodity from CAPRI's 2017 market results (Sprint 9r).

The market's domestic price levels (MarketModule.domestic_prices: world price x (1 + tariff / 100)) take a tariff per
trade region and commodity. Only the EU row came from CAPRI (capri_data/sources/eu_tariff_provenance.json); the other
regions had no data file and the loader generated them at random (EU value x 0.5-0.8 plus uniform noise). The noise
was drawn from a module-level generator, so each CAPRIModel built in a process got different tariffs, and with them
different crushing parameters for the oilseed chains (MarketModule._biofuel_params uses the price levels).

Now every region takes CAPRI's own measure, as the EU row: the TOTAL ad-valorem equivalent of protection on its
imports from outside the region (ad valorem + specific tariffs + tariff-rate quota effects, as CAPRI priced them):

    tariff[I, c] = 100 x ( sum_(i in I, j not in I) ImportQ x ImportP / sum ImportQ x (Fob + TCost) - 1 )

over CAPRI's bilateral flows in market_base_1717 (the same extract as tools/build_bilateral_market.py,
capri_data/sources/market/bilateral_dataout_2017.csv.xz), CAPRI regions mapped to the model's trade regions as there.
The EU row keeps its documented values (eu_tariff_provenance.json; the same formula on CAPRI's EU27yr19 <- NONEU
aggregate); the check printed below recomputes it from the member states. Commodities a region does not import, or
without a CAPRI market (DWHE: durum is in CAPRI's wheat market; SUGB, MILK, FATS, OFOD_M, OOIL), take 0: no
protection is measured, and the bilateral market carries CAPRI's own import prices in any case.

Output: capri_data/2017/policy/tariffs.csv (trade region x commodity, % ad valorem equivalent).

    python tools/build_tariffs_2017.py
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "capri_data" / "2017" / "policy" / "tariffs.csv"
SRC = ROOT / "capri_data" / "sources" / "market" / "bilateral_dataout_2017.csv.xz"
PROV = ROOT / "capri_data" / "sources" / "eu_tariff_provenance.json"


def main():
    from build_bilateral_market import CAPRI
    from recalibrate_trade_2017 import REGION_MAP, AGGREGATES
    from capri_mod.data.definitions import ALL_TRADE_REGIONS
    prov = json.load(open(PROV))["rows"]
    cols = list(prov)                                   # the commodities of the EU row
    df = pd.read_csv(SRC, keep_default_na=False)
    df = df[df["item"].isin(("ImportQ", "ImportP", "Fob", "TCost"))]
    skip = lambda r: r in AGGREGATES or r.startswith(("EU0", "EU_", "A_EU")) or (
        r.endswith("000000") and r not in ("UK000000", "NO000000"))
    pair = defaultdict(dict)
    for r in df.itertuples(index=False):
        if r.r2 and not skip(r.r1) and not skip(r.r2) and r.product in CAPRI:
            pair[(r.product, r.r1, r.r2)][r.item] = float(r.value)
    num, den = defaultdict(float), defaultdict(float)
    for (p, i, j), d in pair.items():
        mi, mj = REGION_MAP.get(i, "ROW"), REGION_MAP.get(j, "ROW")
        q, ip, fob, tc = d.get("ImportQ", 0.0), d.get("ImportP", 0.0), d.get("Fob", 0.0), d.get("TCost", 0.0)
        if i == j or mi == mj or q <= 1e-6 or ip <= 0 or fob <= 0:
            continue
        num[(mi, CAPRI[p])] += q * ip
        den[(mi, CAPRI[p])] += q * (fob + tc)
    rows = {}
    for reg in ALL_TRADE_REGIONS:
        if reg == "EU27":
            rows[reg] = {c: float(v.get("total_ave_pct", v.get("previous", 0.0))) for c, v in prov.items()}
            continue
        rows[reg] = {c: (round(100.0 * (num[(reg, c)] / den[(reg, c)] - 1.0), 4) if den.get((reg, c), 0) > 0 else 0.0)
                     for c in cols}
    out = pd.DataFrame(rows).T[cols]
    out.index.name = "region"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT)
    chk = {c: round(100.0 * (num[("EU27", c)] / den[("EU27", c)] - 1.0), 1) for c in ("BEEF", "BUTR", "SUGR", "OLIV", "PORK")
           if den.get(("EU27", c), 0) > 0}
    print(f"wrote {OUT.relative_to(ROOT)}: {out.shape[0]} regions x {out.shape[1]} commodities")
    print("EU row kept:", {c: rows['EU27'][c] for c in chk}, "| recomputed from the member states:", chk)
    print("median by region:", out.median(axis=1).round(1).to_dict())


if __name__ == "__main__":
    main()

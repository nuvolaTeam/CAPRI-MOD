"""CAPRI's sugar processing per member state: white sugar from sugar beet (arm/data_cal.gms, set_prices.gms).

In CAPRI sugar beet is not a world market product; member states process it into white sugar SUGA with the
processing yield PRCY(SUGA) = MAPR(SUGA) / PRCM(SUGB) (arm/data_cal.gms 1336) and the beet price follows the
sugar price (arm/set_prices.gms: UVAG(SUGB) x v_prodPrice(SUGA) / PPRI(SUGA)). The rest of the beet harvest
(feed, losses, some trade: 4% of EU beet in the 2030 reference) is not processed.

The model converted every tonne of beet into 0.135 t of sugar and also sold the whole harvest on a world sugar
BEET market with an invented world total (1,900 Mt). CAPRI's 2030 reference has yields of 0.13 (HU) to 0.19 (DK),
EU 0.162, and 96% of the beet processed: EU sugar 16.6 Mt from 105.9 Mt of beet, 15.6% of the harvest by weight,
against the model's 13.5%.

From CAPRI's 2030 Green Deal reference (markmarket_greendeal_1730et_base_1717, year 2030), per member state:
GROF(SUGB) beet harvest, PRCM(SUGB) beet processed, MAPR(SUGA) sugar produced, PRCY(SUGA); the bridge uses
sugar_per_beet = MAPR(SUGA) / GROF(SUGB) = PRCY x processed share.

Output: capri_data/2017/market/sugar_processing.csv  ms, beet_grof_kt, beet_prcm_kt, sugar_mapr_kt, prcy,
        sugar_per_beet

    python tools/build/build_sugar_processing.py
"""
from __future__ import annotations
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DUMP = Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt")
SRC_KEEP = ROOT / "capri_data" / "sources" / "market" / "sugar_processing_dataout_2030.csv"
KEYS = {("GROF", "SUGB"), ("PRCM", "SUGB"), ("MAPR", "SUGA"), ("PRCY", "SUGA")}


def main():
    if DUMP.exists():
        pat = re.compile(r"^'([A-Z]{2}000000)'\.''\.'(GROF|PRCM|MAPR|PRCY)'\.'(SUGB|SUGA)'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, open(DUMP, errors="ignore")) if m and (m.group(2), m.group(3)) in KEYS]
        pd.DataFrame(rows, columns=["ms", "item", "product", "value"]).to_csv(SRC_KEEP, index=False)
    src = pd.read_csv(SRC_KEEP)
    v = {(r["ms"], r["item"], r["product"]): float(r["value"]) for _, r in src.iterrows()}
    out = []
    for ms in sorted({r for r, *_ in v}):
        g, p, s = v.get((ms, "GROF", "SUGB"), 0.0), v.get((ms, "PRCM", "SUGB"), 0.0), v.get((ms, "MAPR", "SUGA"), 0.0)
        if g > 0 and s > 0:
            out.append(dict(ms=ms, beet_grof_kt=g, beet_prcm_kt=p, sugar_mapr_kt=s,
                            prcy=v.get((ms, "PRCY", "SUGA"), s / p if p else 0.0), sugar_per_beet=s / g))
    df = pd.DataFrame(out)
    df.to_csv(ROOT / "capri_data" / "2017" / "market" / "sugar_processing.csv", index=False, float_format="%.8g")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"total: beet {df.beet_grof_kt.sum():.0f} kt, sugar {df.sugar_mapr_kt.sum():.0f} kt, "
          f"sugar per beet {df.sugar_mapr_kt.sum() / df.beet_grof_kt.sum():.4f}")


if __name__ == "__main__":
    main()

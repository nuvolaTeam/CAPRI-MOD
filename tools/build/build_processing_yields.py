"""CAPRI's processed market products of olives and paddy rice (2030 reference): olive oil per tonne of olives
and milled rice per tonne of paddy.

CAPRI's market model trades olive oil (OLIO), not olives, and milled rice (RICE), not paddy (bilateral ImportQ:
no OLIV or PARI flows). The olive price follows the olive oil price (arm/set_prices.gms). The model's OLIV and
PARI markets therefore carry olive oil and milled rice: the supply bridge converts the harvest with CAPRI's own
ratios of the 2030 reference.

  olive oil:  MAPR(OLIO) / GROF(OLIV) per member state (EU 0.20)
  rice:       MAPR(RICE) / GROF(PARI) of the EU (0.40) - CAPRI mills paddy in a few member states only
              (IT, PT, BG, ...) and the EU rice market is the EU total, so one EU ratio is used everywhere

Output: capri_data/2017/market/processing_yields.csv  ms, raw, product, raw_kt, product_kt, yield
        (ms "_EU" = EU27 total)

    python tools/build/build_processing_yields.py
"""
from __future__ import annotations
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DUMP = Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt")
KEEP = ROOT / "capri_data" / "sources" / "market" / "processing_yields_dataout_2030.csv"
PAIRS = (("OLIV", "OLIO"), ("PARI", "RICE"))
EU27 = {"BL", "SE", "DK", "DE", "EL", "ES", "FR", "IR", "IT", "NL", "AT", "PT", "FI", "CY", "EE", "LV", "LT", "MT",
        "PL", "SK", "BG", "CZ", "HU", "SI", "RO", "HR"}


def main():
    if DUMP.exists():
        pat = re.compile(r"^'([A-Z]{2}000000)'\.''\.'(GROF|MAPR)'\.'(OLIV|OLIO|PARI|RICE)'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, open(DUMP, errors="ignore")) if m]
        pd.DataFrame(rows, columns=["ms", "item", "product", "value"]).to_csv(KEEP, index=False)
    src = pd.read_csv(KEEP)
    v = {(r["ms"], r["item"], r["product"]): float(r["value"]) for _, r in src.iterrows()}
    out = []
    for raw, prod in PAIRS:
        tr = tp = 0.0
        for ms in sorted({k[0] for k in v}):
            g, q = v.get((ms, "GROF", raw), 0.0), v.get((ms, "MAPR", prod), 0.0)
            if ms[:2] in EU27:
                tr += g; tp += q
            if raw == "OLIV" and g > 0 and q > 0:
                out.append(dict(ms=ms, raw=raw, product=prod, raw_kt=g, product_kt=q, **{"yield": q / g}))
        out.append(dict(ms="_EU", raw=raw, product=prod, raw_kt=tr, product_kt=tp, **{"yield": tp / tr if tr else 0.0}))
    df = pd.DataFrame(out)
    df.to_csv(ROOT / "capri_data" / "2017" / "market" / "processing_yields.csv", index=False, float_format="%.8g")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()

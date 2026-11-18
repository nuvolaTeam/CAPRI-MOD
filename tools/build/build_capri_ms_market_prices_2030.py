"""CAPRI's 2030 market prices of the EU member states with their production and market use, for the baseline check
(tools/check/compare_baseline_capri.py; the results pages' "Baseline vs CAPRI").

The model's market sets each region's base price to CAPRI's own market price PMRK of the market year (market_module.
_reference_prices) and reports the EU27 price as the production-weighted average of its two EU blocks (use-weighted
where the EU produces none; bilateral_solve._with_eu_aggregate). CAPRI's EU27yr19 row is not that average: its PMRK of
maize is 163 EUR/t while every member state's is 214-220, and its producer unit value UVAP is another price again
(tomatoes PMRK 820, UVAP 465). The check therefore compares the model's EU27 price with the member states' PMRK
weighted as the model weights them.

Source: CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF, the
run the model's 2030 base reproduces): PMRK, GROF (gross production), DOMM (market use) of the 26 EU member states at
2030, CAPRI's market products.

Output
  capri_data/validation/capri_ms_market_prices_2030_ref.csv: ms, product, pmrk_eur_t, grof_kt, domm_kt
  (rows with a PMRK only)

    python tools/build/build_capri_ms_market_prices_2030.py [--src ZIP]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)

OUT = ROOT / "capri_data" / "validation" / "capri_ms_market_prices_2030_ref.csv"
#: CAPRI's EU member states (dataOut codes; EU27yr19 without the United Kingdom)
EU_MS = ("AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
         "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")
ITEMS = {"PMRK": "pmrk_eur_t", "GROF": "grof_kt", "DOMM": "domm_kt"}


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    rx = re.compile(r"^'([A-Z]{2})000000'\.''\.'(PMRK|GROF|DOMM)'\.'([A-Z0-9]+)'\.'2030'\s+(\S+)")
    val = {}
    for line in lines(a.src):
        if "'2030'" not in line:
            continue
        m = rx.match(line)
        if m and m.group(1) in EU_MS:
            val[(m.group(1) + "000000", m.group(3), m.group(2))] = num(m.group(4))
    keys = sorted({(ms, p) for (ms, p, it) in val if it == "PMRK" and val[(ms, p, it)] > 0})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ms", "product"] + list(ITEMS.values()))
        for ms, p in keys:
            w.writerow([ms, p] + [repr(float(val.get((ms, p, it), 0.0))) for it in ITEMS])
    print(f"{OUT.name}: {len(keys)} member state x product rows, {len({p for _, p in keys})} products")


if __name__ == "__main__":
    main()

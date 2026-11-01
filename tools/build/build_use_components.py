"""CAPRI's Armington use split into its four components per behavioural region (arm/market_model.gms ArmBal1_):

    v_arm1Quant(RM, XX) = sum_{RMS in RM} [ HCON + FEED + PROC + BIOF ]

ArmBal1_ has no other use: each component has its own behavioural equation where CAPRI has one (GL food demand,
FeedNQ_ / feed bulks, ProcNQ_, the biofuel block) and is fixed at its data value where it has none.

Output: capri_data/2017/market/use_components.csv
    rms, model_region, commodity, hcon_kt, feed_kt, proc_kt, biof_kt, arm1_kt
from CAPRI's 2030 calibration (data_market_1730defaulta, Data_CAL 'CAL'), CAPRI products mapped to the model's market
commodities (tools/build/build_bilateral_market.py MODEL; several CAPRI products may sum into one). arm1_kt is the
region's ARM1 of the market region where the behavioural region is its own market region (RM_AND_RMS), else empty; the
builder reports how closely HCON + FEED + PROC + BIOF reproduces it.

    python tools/build/build_use_components.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market" / "use_components.csv"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS2 as _EU_FROM_DATA  # noqa: E402  (capri_data/shared/eu_market_blocks.csv)
EU = set(_EU_FROM_DATA)                                  # CAPRI's EU member states, from the data
ITEMS = ("HCON", "FEED", "PROC", "BIOF", "ARM1")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def main() -> None:
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build")]
    import build_bilateral_market as BM
    from recalibrate_trade_2017 import trade_region
    g2m = {g: m for m, gs in BM.MODEL.items() for g in gs}
    rms_set = set(_read_csv(ROOT / "capri_data" / "shared" / "rms.csv")["rms"])
    pat = re.compile(r"^'([^']*)'\.'(" + "|".join(ITEMS) + r")'\.'([A-Za-z]+)'\.'CAL'\s+(\S+)")
    v = defaultdict(float)
    for line in open(DATA, encoding="latin-1"):
        if not line.startswith("'"):
            continue
        m = pat.match(line)
        if m and m.group(1) in rms_set and m.group(3) in g2m:
            v[(m.group(1), g2m[m.group(3)], m.group(2))] += num(m.group(4))
    mreg = lambda r: "EU27" if (r[:2] in EU and r.endswith("000000")) else trade_region(r)
    keys = sorted({(r, c) for (r, c, _) in v})
    rows, worst = [], 0.0
    for r, c in keys:
        h, f, p, b = (v.get((r, c, it), 0.0) for it in ("HCON", "FEED", "PROC", "BIOF"))
        a = v.get((r, c, "ARM1"))
        if h + f + p + b <= 0:
            continue
        if a:
            worst = max(worst, abs(h + f + p + b - a) / a)
        rows.append(dict(rms=r, model_region=mreg(r), commodity=c, hcon_kt=h, feed_kt=f, proc_kt=p, biof_kt=b,
                         arm1_kt=a if a else float("nan")))
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False, lineterminator="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(t)} region-commodities in {t.rms.nunique()} behavioural regions; "
          f"largest relative gap of HCON + FEED + PROC + BIOF to ARM1 where CAPRI stores ARM1 for the region: {worst:.2e}")


if __name__ == "__main__":
    main()

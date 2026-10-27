"""EU-wide crop producer prices (producer_prices.csv), the fallback where a region has no CAPRI price (October 2026).

Every region's crop price comes from CAPRI's regional or national MPRI (capreg_producer_prices.csv, written by
tools/build/build_crop_economics_2017.py); the EU-wide file only fills a crop a member state does not grow. Its crop rows
were of unrecorded source and far from CAPRI's (other vegetables 30.8 EUR/t against a CAPRI median of about 500,
tomatoes 33.5, olives 49.5, tobacco 43.8, wine 95.5). They are rewritten as CAPRI's production-weighted EU price over
the model regions: sum(area x yield x price) / sum(area x yield), CAPRI's 2017 values. Livestock rows are kept
(tools/build/build_shg_split.py and earlier builders). Grass keeps its own price basis (dry matter, build_crop_economics).
Other marketable and industrial crops, nurseries and flowers get no row (CAPRI carries them as values).

    python tools/build/build_eu_producer_prices.py
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SUP = ROOT / "capri_data" / "2017" / "supply"
DEST = ROOT / "capri_data" / "2017" / "market" / "producer_prices.csv"


def main() -> None:
    areas = _read_csv(SUP / "base_areas.csv", index_col=0)
    ylds = _read_csv(SUP / "yields.csv", index_col=0)
    prices = _read_csv(ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv", index_col=0)
    pp = _read_csv(DEST, index_col=0)
    col = pp.columns[0]
    changed = {}
    for c in areas.columns:
        # set-aside has no output; other marketable and industrial crops, nurseries and flowers are carried in CAPRI as
        # values, not tonnes (DATA_SOURCING_REGISTRY), so a per-tonne EU price is not defined for them
        if c in ("SETA", "OCRO", "OIND", "NURS", "FLOW") or c not in ylds.columns or c not in prices.columns:
            continue
        q = (areas[c] * ylds[c]).reindex(prices.index).fillna(0.0)
        p = prices[c]
        ok = (q > 0) & p.notna() & (p > 0)
        if q[ok].sum() <= 0:
            continue
        v = round(float((q[ok] * p[ok]).sum() / q[ok].sum()), 4)
        old = float(pp.at[c, col]) if c in pp.index else float("nan")
        pp.loc[c, col] = v
        changed[c] = (old, v)
    pp.to_csv(DEST)
    print(f"wrote {DEST.relative_to(ROOT)}: {len(changed)} crop prices")
    for c, (o, v) in changed.items():
        print(f"  {c:5s} {o:>10.2f} -> {v:>10.2f}")


if __name__ == "__main__":
    main()

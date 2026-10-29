"""EU-wide crop producer prices (producer_prices.csv), the fallback where a region has no CAPRI price (October 2026).

Every region's crop price comes from CAPRI's regional or national MPRI (capreg_producer_prices.csv, written by
tools/build/build_crop_economics_2017.py); the EU-wide file only fills a crop a member state does not grow. Its crop rows
were of unrecorded source and far from CAPRI's (other vegetables 30.8 EUR/t against a CAPRI median of about 500,
tomatoes 33.5, olives 49.5, tobacco 43.8, wine 95.5). They are rewritten as CAPRI's production-weighted EU price over
the model regions: sum(area x yield x price) / sum(area x yield), CAPRI's 2017 values. This builder is the table's one
writer (29 October 2026), built from scratch: the crop rows above; SHGM and SHGF, CAPREG's prices weighted by the herds
(tools/lib/_sheep_goat.py, as the retired build_shg_split.py); the rows no builder computes from
sources/unsourced/producer_prices_no_builder.csv (set-aside's 0; ten livestock rows of unrecorded origin, KNOWN_ISSUES
K72). Rows in the model's activity order. Grass keeps its own price basis (dry matter, build_crop_economics).
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
#: the rows no builder computes (set-aside's 0 by convention; the livestock rows of unrecorded origin, KNOWN_ISSUES K72)
NO_BUILDER = ROOT / "capri_data" / "sources" / "unsourced" / "producer_prices_no_builder.csv"
import sys as _sys  # noqa: E402
_sys.path[:0] = [str(ROOT / "tools" / "lib"), str(ROOT)]
import _sheep_goat as SG  # noqa: E402
from capri_mod.data import definitions as D  # noqa: E402


def main() -> None:
    areas = _read_csv(SUP / "base_areas.csv", index_col=0)
    ylds = _read_csv(SUP / "yields.csv", index_col=0)
    herds = _read_csv(SUP / "animal_numbers.csv", index_col=0)
    prices = _read_csv(ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv", index_col=0)
    rows = {}
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
        rows[c] = float((q[ok] * p[ok]).sum() / q[ok].sum())
    n_crops = len(rows)
    # sheep and goats: CAPREG's regional prices weighted by the herds (tools/lib/_sheep_goat.py)
    rows.update(SG.eu_prices(herds, prices))
    # the rows no builder computes, declared with their note (set-aside's 0; the other livestock of K72)
    nb = _read_csv(NO_BUILDER, index_col=0)
    for a, v in nb["price"].items():
        if a in rows:
            raise ValueError(f"{NO_BUILDER.name}: {a} is computed here as well")
        rows[a] = float(v)
    order = [c for c in list(D.CROPS) + list(D.ANIMALS) if c in rows]
    order += [c for c in rows if c not in order]
    pd.DataFrame({"price": [rows[c] for c in order]}, index=order).to_csv(DEST)
    print(f"wrote {DEST.relative_to(ROOT)}: {n_crops} crop prices, SHGM and SHGF, {len(nb)} rows from "
          f"{NO_BUILDER.relative_to(ROOT)}")

if __name__ == "__main__":
    main()

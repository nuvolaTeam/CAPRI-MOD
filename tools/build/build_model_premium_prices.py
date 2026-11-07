"""The model's CAP premium per activity and regional producer prices, from CAPRI's 2017 CAPREG extracts.

Until 31 October 2026 the model read capri_data/sources/capreg/ at run time and did this work in its loaders
(capri_mod/data/loaders.load_cap_premium, load_regional_producer_prices): the sources are the builders' layer, so the
work moved here, unchanged, and the model reads the two files this builder writes.

  capri_data/2017/supply/cap_premium_activity.csv
      CAPRI's premium PRME per regional unit and activity (sources/intermediate/capreg/capreg_cap_premium.csv, CAPREG DATA2, per ha
      or per head), the crop columns replaced by the model-coded crop premiums of every region
      (2017/supply/crop_premium.csv, tools/build/build_crop_economics_2017.py): the CAPREG file covers 192 regions in
      CAPRI's codes, so 56 regions, and fodder, set-aside, wine and fibre everywhere, had no crop premium of their own.
  capri_data/2017/supply/producer_prices_regional.csv
      CAPRI's regional producer prices MPRI (sources/intermediate/capreg/capreg_producer_prices.csv, EUR/t) with two of CAPRI's own
      corrections: the five crops CAPRI codes otherwise take its columns (TWIN for WINE; OFAR for OFOD until S2), and a region
      without a regional price takes its country's national price (sources/intermediate/capreg/capreg_national_prices.csv) before
      the EU-wide one (wine: 95.5 EUR/t in eleven vine-growing regions before, against CAPRI's national 1,362-1,923).

    python tools/build/build_model_premium_prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.data.definitions import MS_CODE  # noqa: E402
from capri_mod.tableio import read_input  # noqa: E402

SRC = ROOT / "capri_data" / "sources" / "intermediate" / "capreg"
SUP = ROOT / "capri_data" / "2017" / "supply"
PREMIUM = SUP / "cap_premium_activity.csv"
PRICES = SUP / "producer_prices_regional.csv"
#: CAPRI's activity codes of crops the model names otherwise (the price columns)
CAPRI_PRICE_ALIASES = {"TWIN": ["WINE"]}   # OFAR the model's own since S2 (7 November 2026; before OFAR -> OFOD)


def cap_premium() -> pd.DataFrame:
    base = read_input(SRC / "capreg_cap_premium.csv", index_col=0)
    crop = read_input(SUP / "crop_premium.csv", index_col=0)
    return crop.join(base[[k for k in base.columns if k not in crop.columns]], how="left")


def producer_prices() -> pd.DataFrame:
    prices = read_input(SRC / "capreg_producer_prices.csv", index_col=0)
    for src, targets in CAPRI_PRICE_ALIASES.items():
        if src not in prices.columns:
            continue
        for tgt in targets:
            if tgt not in prices.columns or prices[tgt].isna().all():
                prices[tgt] = prices[src]
    nat = read_input(SRC / "capreg_national_prices.csv", index_col=0)
    for col in prices.columns:
        if col not in nat.columns:
            continue
        missing = prices[col].isna()
        if not missing.any():
            continue
        for reg in prices.index[missing]:
            cc = MS_CODE.get(str(reg)[:2], str(reg)[:2])
            if cc in nat.index and pd.notna(nat.at[cc, col]) and nat.at[cc, col] > 0:
                prices.at[reg, col] = float(nat.at[cc, col])
    return prices


def main() -> None:
    for out, df in ((PREMIUM, cap_premium()), (PRICES, producer_prices())):
        df.to_csv(out)
        print(f"wrote {out.relative_to(ROOT)}: {df.shape[0]} regions x {df.shape[1]} columns")


if __name__ == "__main__":
    main()

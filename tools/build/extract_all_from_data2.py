"""
Comprehensive extraction of every model input available from capreg DATA2.

Motivation
----------
Most files in capri_data were labelled REAL_CAPRI with a vague source string
("CAPRI", "CAPRI SUA"), which meant they came through the Excel export path
rather than from a GDX read. That path is what produced the Cyrillic homoglyph
corruption, the ragged vintages and the dropped regional detail. This tool
re-derives those inputs from the DATA2 dumps instead, so their provenance is a
GDX read with an explicit year.

What DATA2 contains that the model needs
----------------------------------------
    MPRI              producer price, EUR/t, REGIONAL
    NITF PHOF POTF    N / P2O5 / K2O application, kg/ha, REGIONAL
    FERT SEED REPM    cost components, EUR/ha
    REPB ELEC EGAS
    EFUL ELUB INPO
    TOIN              total intermediate input, EUR/ha
    YILD LEVL COMI    yields and activity levels
    ENNE CRPR DRMN    feed requirements
    DRMX DAYS
    MANN MANP MANK    manure nutrients

Deliberate caution on costs
---------------------------
TOIN is the sum over ALL intermediate inputs, which is not the same concept as
the model's variable_costs. For DE11 soft wheat, TOIN is 743.3 EUR/ha against
the model's 374.5. Some of that gap is definitional rather than error, so this
tool extracts the components separately and reports them; it does not assume the
two concepts are interchangeable.

PLAP is also unsafe: in these dumps it carries the same value as PESTOTAL
(4706.3 for DE11 SWHE), which is a pesticide quantity index rather than EUR/ha.
It is excluded.

Until 29 October 2026 it also printed a comparison with the model's producer_prices.csv and nutrient_coefs.csv; that
made the extract read tables built from it (a cycle in the data pipeline, docs/design/DATA_PIPELINE_DOIT.md) and was
removed: the extract reads CAPRI's dumps and the regional units only.

Usage
-----
    python tools/build/extract_all_from_data2.py --export-dir /path/to/capri_export
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
RECORD = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+([-\d.Ee+]+)")

PRICE_ITEM = "MPRI"
# EUR/ha cost components. PLAP is excluded: it duplicates PESTOTAL, a quantity
# index, not a cost.
COST_ITEMS = ["FERT", "SEED", "REPM", "REPB", "ELEC", "EGAS",
              "EFUL", "ELUB", "INPO", "IRRO", "CAOF"]
TOTAL_INPUT = "TOIN"

WANTED = ({PRICE_ITEM, TOTAL_INPUT} | set(COST_ITEMS))


def parse(path: Path, keep: set) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RECORD.match(line)
            if m and m.group(3) in keep:
                rows.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))
    return pd.DataFrame(rows, columns=["region", "activity", "item", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    files = sorted(args.export_dir.glob("DATA2_*.txt"))
    print(f"parsing {len(files)} member state files for {len(WANTED)} items...")
    df = pd.concat([parse(f, WANTED) for f in files], ignore_index=True)
    df = df.drop_duplicates(["region", "activity", "item"], keep="last")

    # the model's regions are CAPRI's regional units (shared/regional_units.csv): each CAPRI row is its own region's
    # (until 27 October 2026 mapped to NUTS-2016 regions through shared/nuts_crosswalk.json, 21 regions unmatched)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from _model_regions import is_unit
    df["model_region"] = df.region.where(df.region.map(is_unit))
    df = df.dropna(subset=["model_region"])
    df["activity"] = df.activity.replace({"MAIZ": "CORN"})

    out = args.data_dir / "sources" / "capreg"
    out.mkdir(parents=True, exist_ok=True)
    summary = {}

    # ---- producer prices, EUR/t, regional --------------------------------
    pr = df[df.item == PRICE_ITEM].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")
    pr = pr.where(pr > 0)
    # CAPRI's regional producer prices as extracted (CAPRI's codes); the model's table capreg_producer_prices.csv is
    # assembled from it by tools/build/build_crop_economics_2017.py (one writer per file, 29 October 2026)
    pr.to_csv(out / "capreg_producer_prices_extract.csv")
    summary["producer_prices"] = {
        "regions": int(pr.shape[0]), "activities": int(pr.shape[1]),
        "values": int(pr.notna().sum().sum())}
    print(f"\nproducer prices : {pr.shape[0]} regions x {pr.shape[1]} activities")

    # (CAPRI's NITF/PHOF/POTF per region were written to capreg_nutrient_coefs.csv until 29 October 2026; nothing read
    # them - build_nutrient_coefs_regional reads CAPRI's dumps directly - and the file was removed: KNOWN_ISSUES K103)

    # ---- cost components, EUR/ha: compared with TOIN for the summary only (written to capreg_cost_components.csv.xz
    # until 30 October 2026; nothing read it and the file was removed, the project lead's decision: KNOWN_ISSUES K103)
    co = df[df.item.isin(COST_ITEMS + [TOTAL_INPUT])]
    comp = co[co.item != TOTAL_INPUT].groupby(
        ["model_region", "activity"]).value.sum().rename("components")
    tot = co[co.item == TOTAL_INPUT].set_index(
        ["model_region", "activity"]).value.rename("toin")
    cmp_ = pd.concat([comp, tot], axis=1).dropna()
    ratio = (cmp_.components / cmp_.toin).median()
    summary["cost_components"] = {
        "records": int(len(co)),
        "components_over_toin_median": float(ratio)}
    print(f"cost components : {len(co):,} records; "
          f"sum of components is {ratio:.0%} of TOIN")

    (args.data_dir / "validation").mkdir(exist_ok=True)
    (args.data_dir / "validation" / "data2_extraction_summary.json").write_text(
        json.dumps(summary, indent=1))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()

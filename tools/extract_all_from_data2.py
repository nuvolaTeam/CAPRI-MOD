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

Usage
-----
    python tools/extract_all_from_data2.py --export-dir /path/to/capri_export
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RECORD = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+([-\d.Ee+]+)")

PRICE_ITEM = "MPRI"
NUTRIENT_ITEMS = {"NITF": "N", "PHOF": "P2O5", "POTF": "K2O"}
# EUR/ha cost components. PLAP is excluded: it duplicates PESTOTAL, a quantity
# index, not a cost.
COST_ITEMS = ["FERT", "SEED", "REPM", "REPB", "ELEC", "EGAS",
              "EFUL", "ELUB", "INPO", "IRRO", "CAOF"]
TOTAL_INPUT = "TOIN"

WANTED = ({PRICE_ITEM, TOTAL_INPUT} | set(NUTRIENT_ITEMS) | set(COST_ITEMS))


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

    cw = json.loads((args.data_dir / "shared/nuts_crosswalk.json").read_text())
    rev = {}
    for mr, codes in cw.get("aliases", {}).items():
        for c in codes:
            rev.setdefault(c, mr)
    for mr, c in cw["resolved"].items():
        rev.setdefault(c, mr)
    df["model_region"] = df.region.map(rev)
    df = df.dropna(subset=["model_region"])
    df["activity"] = df.activity.replace({"MAIZ": "CORN"})

    out = args.data_dir / "sources" / "capreg"
    out.mkdir(parents=True, exist_ok=True)
    summary = {}

    # ---- producer prices, EUR/t, regional --------------------------------
    pr = df[df.item == PRICE_ITEM].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")
    pr = pr.where(pr > 0)
    pr.to_csv(out / "capreg_producer_prices.csv")
    summary["producer_prices"] = {
        "regions": int(pr.shape[0]), "activities": int(pr.shape[1]),
        "values": int(pr.notna().sum().sum())}
    print(f"\nproducer prices : {pr.shape[0]} regions x {pr.shape[1]} activities")

    # ---- nutrient application, kg/ha, regional ---------------------------
    nu = df[df.item.isin(NUTRIENT_ITEMS)].copy()
    nu["nutrient"] = nu.item.map(NUTRIENT_ITEMS)
    nu = nu[["model_region", "activity", "nutrient", "value"]]
    nu.to_csv(out / "capreg_nutrient_coefs.csv", index=False)
    summary["nutrient_coefs"] = {
        "records": int(len(nu)),
        "regions": int(nu.model_region.nunique()),
        "activities": int(nu.activity.nunique())}
    print(f"nutrient coefs  : {len(nu):,} records, "
          f"{nu.model_region.nunique()} regions, {nu.activity.nunique()} activities")

    # ---- cost components, EUR/ha ----------------------------------------
    co = df[df.item.isin(COST_ITEMS + [TOTAL_INPUT])]
    co.to_csv(out / "capreg_cost_components.csv", index=False)
    comp = co[co.item != TOTAL_INPUT].groupby(
        ["model_region", "activity"]).value.sum().rename("components")
    tot = co[co.item == TOTAL_INPUT].set_index(
        ["model_region", "activity"]).value.rename("toin")
    cmp_ = pd.concat([comp, tot], axis=1).dropna()
    ratio = (cmp_.components / cmp_.toin).median()
    summary["cost_components"] = {
        "records": int(len(co)),
        "components_over_toin_median": round(float(ratio), 3)}
    print(f"cost components : {len(co):,} records; "
          f"sum of components is {ratio:.0%} of TOIN")

    # ---- comparison with what the model currently uses -------------------
    print("\n--- against current model inputs ---")
    cur_p = pd.read_csv(args.data_dir / "2017/market/producer_prices.csv", index_col=0)
    col = cur_p.columns[0]
    rows = []
    for a in pr.columns:
        if a in cur_p.index:
            capri = float(pr[a].median())
            model = float(cur_p.at[a, col])
            if capri > 0 and model > 0:
                rows.append((a, model, capri, 100 * (model - capri) / capri))
    dp = pd.DataFrame(rows, columns=["activity", "model", "capri_median", "dev_pct"])
    print(f"\nproducer prices, {len(dp)} activities comparable:")
    print(f"  median |deviation| : {dp.dev_pct.abs().median():.1f}%")
    print(dp.reindex(dp.dev_pct.abs().sort_values(ascending=False).index)
          .head(8).round(1).to_string(index=False))

    cur_n = pd.read_csv(args.data_dir / "2017/environment/nutrient_coefs.csv",
                        index_col=0)
    npiv = nu.pivot_table(index="activity", columns="nutrient",
                          values="value", aggfunc="median")
    common = [a for a in npiv.index if a in cur_n.index]
    devs = []
    for a in common:
        for n in ("N", "P2O5", "K2O"):
            if n in cur_n.columns and n in npiv.columns:
                m, c = cur_n.at[a, n], npiv.at[a, n]
                if c and c > 0 and pd.notna(m):
                    devs.append(abs(m - c) / c * 100)
    print(f"\nnutrient coefficients, {len(common)} activities comparable:")
    print(f"  median |deviation| : {np.median(devs):.1f}%")
    print("  model values are national constants; CAPRI's vary by region "
          f"(N across regions for SWHE: "
          f"{nu[(nu.activity=='SWHE') & (nu.nutrient=='N')].value.min():.0f}"
          f"-{nu[(nu.activity=='SWHE') & (nu.nutrient=='N')].value.max():.0f} kg/ha)")

    (args.data_dir / "validation").mkdir(exist_ok=True)
    (args.data_dir / "validation" / "data2_extraction_summary.json").write_text(
        json.dumps(summary, indent=1))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()

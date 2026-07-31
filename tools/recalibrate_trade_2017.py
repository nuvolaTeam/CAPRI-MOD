"""
Recalibrate the trade matrix from CAPRI's 2017 capmod result.

The problem being fixed
----------------------
The market module builds Armington import shares from `trade_flows_2021.csv` --
a 2021 matrix inside a 2017 base-year model. The Armington shares therefore
describe a different year from the supply side they are matched against.

CAPRI's capmod base-year result (res_0_1717, BAS=17 SIM=17) carries bilateral
ImportQ at 2017, which is the right year and CAPRI's own calibration.

Two concordances, both declared rather than inferred
----------------------------------------------------
CAPRI's trade regions are a mix of countries and blocs and do not line up with
the model's 29 regions one-for-one. Anything CAPRI reports that the model does
not model separately is folded into ROW, and the aggregates that overlap
(NONEU, ASIA, MID_INC, HI_INC, LDC and similar) are excluded outright -- they
are supersets of the individual regions and including them double-counts.

Commodity codes differ too: the market module uses supply-activity names where
CAPRI's market model uses its own.

What is checked before writing
------------------------------
The extra-EU import share per commodity is compared between the 2021 and 2017
matrices. That share is what the Armington first nest actually turns on, so a
large move there is the substantive change; a small one means the recalibration
is cosmetic and not worth the disruption.

Usage
-----
    python tools/recalibrate_trade_2017.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

# CAPRI capmod region -> model trade region. Regions absent here fold into ROW.
REGION_MAP = {
    "EU": "EU27", "EU27yr19": "EU27",
    "USA": "USA", "CAN": "CAN", "BRA": "BRA", "ARG": "ARG",
    "AUS": "AUS", "NZL": "NZL", "CHN": "CHN", "IND": "IND",
    "RUS": "RUS", "UKR": "UKR", "TUR": "TUR", "MEX": "MEX",
    "INDO": "IDN", "JAP": "JPN", "SKOR": "KOR", "THAI": "THA",
    "VIET": "VNM", "PAK": "PAK", "BGD": "BGD", "NGA": "NGA",
    "ZAF": "ZAF", "RSA": "ZAF", "ETH": "ETH", "MOR": "MAR",
}

# Overlapping aggregates. These are supersets of the regions above and must be
# dropped, not mapped: including them counts the same trade more than once.
AGGREGATES = {
    "World", "NONEU", "NONEU_EU", "ASIA", "AFRICA", "MID_INC", "HI_INC",
    "LDC", "LDCACP", "ACP", "MSA_ACP", "AFR_LDC", "AFR_REST", "ASOCE_LDC",
    "ASOCE_REST", "MER", "MER_OTH", "MED", "FSU", "N_AM", "MS_AM", "ANZ",
    "A_EU_EAST", "A_EU_WEST", "WBA", "REU", "URUPAR",
}

# model commodity -> CAPRI market commodity
COMMODITY_MAP = {
    "SWHE": "WHEA", "CORN": "MAIZ", "POUL": "POUM",
    "BUTR": "BUTT", "SKIM": "SMIP",
}

DUMP = Path("/mnt/user-data/uploads/_symbols_base1717.txt")
RECORD = re.compile(
    r"^'([^']+)'\.'([^']+)'\.'ImportQ'\.'([A-Z0-9]+)'\.'2017'\s+([-\d.Ee+]+)")


def extra_eu_share(flows: pd.DataFrame, commodities) -> pd.Series:
    """Share of EU27 imports coming from outside EU27, per commodity."""
    out = {}
    for c in commodities:
        if c not in flows.columns:
            continue
        rows = [(e, i) for (e, i) in flows.index if i == "EU27"]
        if not rows:
            continue
        total = float(flows.loc[rows, c].sum())
        if total <= 0:
            continue
        intra = float(flows.loc[[(e, i) for (e, i) in rows if e == "EU27"], c].sum()) \
            if ("EU27", "EU27") in flows.index else 0.0
        out[c] = 100 * (total - intra) / total
    return pd.Series(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=DUMP)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cur_path = args.data_dir / "shared" / "trade_flows_2021.csv"
    cur = pd.read_csv(cur_path, index_col=[0, 1])
    commodities = list(cur.columns)
    print(f"current matrix: {cur.shape[0]} region pairs x {len(commodities)} commodities")

    inv_comm = {v: k for k, v in COMMODITY_MAP.items()}
    rows = []
    with open(args.dump, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RECORD.match(line)
            if not m:
                continue
            imp_raw, exp_raw, comm_raw, val = m.groups()
            if imp_raw in AGGREGATES or exp_raw in AGGREGATES:
                continue
            imp = REGION_MAP.get(imp_raw, "ROW")
            exp = REGION_MAP.get(exp_raw, "ROW")
            comm = inv_comm.get(comm_raw, comm_raw)
            if comm not in commodities:
                continue
            rows.append((exp, imp, comm, float(val)))

    raw = pd.DataFrame(rows, columns=["exporter", "importer", "commodity", "qty"])
    print(f"records mapped : {len(raw):,}")
    new = raw.pivot_table(index=["exporter", "importer"], columns="commodity",
                          values="qty", aggfunc="sum").fillna(0.0)
    new = new.reindex(columns=commodities, fill_value=0.0)
    print(f"new matrix     : {new.shape[0]} region pairs x {new.shape[1]} commodities")
    print(f"commodities with any flow: {int((new.sum() > 0).sum())}/{len(commodities)}")

    # --- the check that matters -----------------------------------------
    s_old = extra_eu_share(cur, commodities)
    s_new = extra_eu_share(new, commodities)
    common = [c for c in s_new.index if c in s_old.index]
    cmp_ = pd.DataFrame({"share_2021": s_old[common].round(1),
                         "share_2017": s_new[common].round(1)})
    cmp_["change_pp"] = (cmp_.share_2017 - cmp_.share_2021).round(1)
    cmp_ = cmp_.reindex(cmp_.change_pp.abs().sort_values(ascending=False).index)
    print("\nextra-EU import share, the quantity the Armington first nest turns on:")
    print(cmp_.head(12).to_string())
    print(f"\nmedian absolute change: {cmp_.change_pp.abs().median():.1f} pp")

    if args.dry_run:
        print("\n[dry run] nothing written")
        return

    out = args.data_dir / "shared" / "trade_flows_2017.csv"
    new.to_csv(out)
    backup = cur_path.with_suffix(".csv.superseded_by_2017")
    if not backup.exists():
        shutil.copy(cur_path, backup)

    rep = args.data_dir / "validation" / "trade_recalibration_2017.json"
    rep.write_text(json.dumps({
        "source": "capmod res_0_1717 dataOut ImportQ, 2017",
        "region_pairs": int(new.shape[0]),
        "records_mapped": int(len(raw)),
        "aggregates_excluded": sorted(AGGREGATES),
        "median_share_change_pp": float(cmp_.change_pp.abs().median()),
        "extra_eu_share": cmp_.to_dict("index"),
    }, indent=1))
    print(f"\nwritten: {out}\nreport : {rep}")


if __name__ == "__main__":
    main()

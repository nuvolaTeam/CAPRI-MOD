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
the model's 30 regions one-for-one. Anything CAPRI reports that the model does
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
    python tools/build/recalibrate_trade_2017.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
#: CAPRI's region code (market region or trade block of its market data) -> the model's trade region, from the
#: declared table capri_data/shared/trade_regions.csv (Norway NO000000 -> NOR, KNOWN_ISSUES K56; the United Kingdom
#: UK000000 -> GBR and the Western Balkans' block WBA, batch 7). Regions absent there fold into ROW.
TRADE_REGIONS_CSV = Path(__file__).resolve().parents[2] / "capri_data" / "shared" / "trade_regions.csv"
REGION_MAP = {r: t for r, t in _read_csv(TRADE_REGIONS_CSV, dtype=str, keep_default_na=False)[
    ["capri_region", "trade_region"]].itertuples(index=False) if r}

#: CAPRI's mapping of behavioural regions (RMS) to market regions (RM): set RMS_TO_RM of its instantiation, written by
#: tools/build/build_gl_demand.py. A behavioural region that is not a market region of its own (the Western Balkan
#: countries AL, BA, CS, KO, MK, MO of the block WBA) belongs to its market region's trade region.
RMS_TO_RM_CSV = Path(__file__).resolve().parents[2] / "capri_data" / "shared" / "rms_to_rm.csv"


@_ft.lru_cache(maxsize=1)
def _rms_to_rm() -> dict:
    return dict(_read_csv(RMS_TO_RM_CSV)[["rms", "rm"]].itertuples(index=False))


def trade_region(r: str, default: str = "ROW") -> str:
    """The model's trade region of a CAPRI region: a market region by REGION_MAP, a behavioural region by its market
    region (RMS_TO_RM), anything else -> default. EU member states map to their A_EU_* blocks, not to EU27: callers
    treat the EU first. A source that holds both a block and its members must use one level only (no double count)."""
    if r in REGION_MAP:
        return REGION_MAP[r]
    rm = _rms_to_rm().get(r)
    return REGION_MAP.get(rm, default) if rm is not None else default


# Overlapping aggregates. These are supersets of the regions above and must be
# dropped, not mapped: including them counts the same trade more than once.
AGGREGATES = {
    # CAPRI REPORTING sums, derived from the data (2026-10): the 44 trading regions
    # (39 behavioural regions + 5 trade-only blocks EU27yr19, URUPAR, WBA, MER_OTH,
    # MED) reproduce ImportQ(World, World) exactly for all 71 traded products, and
    # every code below overshoots when added (checked for all 71 traded products in 2017).
    # The previous hand-made list dropped GENUINE regions (URUPAR, MED, AFR_LDC,
    # AFR_REST, ASOCE_LDC, ASOCE_REST, FSU, REU, MSA_ACP, WBA) and kept "EU" and
    # "AllImporters", double-counting the EU and rest of world.
    "ACP", "AFRICA", "ANZ", "ASIA", "A_EU_EAST", "A_EU_WEST", "AllImporters", "EU", "HI_INC", "LDC", "LDCACP", "MER", "MID_INC", "MS_AM", "NONEU", "NONEU_EU", "N_AM", "World",
}

# model commodity -> CAPRI market commodity
COMMODITY_MAP = {
    "SWHE": "WHEA", "CORN": "MAIZ", "POUL": "POUM",
    "BUTR": "BUTT", "SKIM": "SMIP",
    # added 2026-10, the same renames as the world prices: without them these
    # commodities had NO trade at all in the matrix
    "SUGR": "SUGA", "WINE": "TWIN", "WHEY": "WHEP", "SGMT": "SGMT",
}

DUMP = Path("/mnt/user-data/uploads/res_0_1717cap_after_2014_cal_from_data_caldefaulta.csv")
# RSA is a different CAPRI region from ZAF (South Africa) -> ROW.
#: the commodities beyond the 2021 matrix's columns: sheep and goat meat, and the oilseed-crushing products (added for
#: the crushing module). Until 29 October 2026 the builder took SGMT from the columns of its own output (a read of the
#: file it writes); the column list is now declared here, in the same order.
EXTRA_COMMODITIES = ["SGMT", "RAPO", "SUNO", "SOYO", "RAPC", "SUNC", "SOYC"]
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

    cur_path = args.data_dir / "sources" / "fao_2021" / "trade_flows_2021.csv"
    cur = _read_csv(cur_path, index_col=[0, 1])
    commodities = list(dict.fromkeys(list(cur.columns) + EXTRA_COMMODITIES))
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
    cmp_ = pd.DataFrame({"share_2021": s_old[common], "share_2017": s_new[common]})
    cmp_["change_pp"] = cmp_.share_2017 - cmp_.share_2021
    cmp_ = cmp_.reindex(cmp_.change_pp.abs().sort_values(ascending=False).index)
    print("\nextra-EU import share, the quantity the Armington first nest turns on:")
    print(cmp_.head(12).round(1).to_string())
    print(f"\nmedian absolute change: {cmp_.change_pp.abs().median():.1f} pp")

    if args.dry_run:
        print("\n[dry run] nothing written")
        return

    out = args.data_dir / "shared" / "trade_flows_2017.csv"
    new.to_csv(out)

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

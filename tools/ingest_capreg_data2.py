"""
Ingest CAPRI's capreg DATA2 dumps into model-ready tables.

Input is the gdxdump listing format produced by `dump_capreg_explicit.gms`:

    Parameter DATA2(*,*,*,*) /
    'DE110000'.'SWHE'.'YILD'.'Y' 7612.58107953842,

The fourth index is a constant 'Y' in every record, so the payload is
DATA2(region, activity, item).

Region codes are CAPRI's 8-character form and resolve to model NUTS-2 codes via
shared/nuts_crosswalk.json. Unlike COCO, this data is genuinely regional and
covers livestock as well as crops.

Yield item is not uniform
-------------------------
For crop activities the yield lives in YILD, in kg/ha, verified against known
values (German SWHE 7612.6 kg/ha, BARL 6648.2 kg/ha).

For dairy it does not. DE000000 DCOW YILD is 2535, which is not a German milk
yield; the actual figure is in COMI, 8384.4 kg/head at DE110000. YILD for DCOW
appears to be a different concept, so COMI is used instead. Pig fattening
PIGF YILD of 81.9 kg/head reads as carcass weight and is used as-is.

GRAS is deliberately left alone: capreg reports 410.9 for DE000000 while COCO2
national reports 17770 kg/ha for the same year. Those cannot both be kg/ha, the
definitions clearly differ, and guessing a conversion would repeat the mistake
that produced the synthetic values in the first place.

Usage
-----
    python tools/ingest_capreg_data2.py --export-dir /path/to/capri_export
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

RECORD = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+([-\d.Ee+]+)")

# Items worth keeping. Everything else in DATA2 is environmental accounting,
# labour or trade detail that the model does not currently consume.
KEEP = {"YILD", "LEVL", "COMI", "HERD", "PROD",
        # Feed requirement levels, per animal activity:
        #   ENNE  net energy requirement
        #   CRPR  crude protein requirement
        #   DRMN  dry matter intake, minimum
        #   DRMX  dry matter intake, maximum
        #   DAYS  production days per year
        # These are the levels that reqrel's p_animReqCorrFac1 corrects, and
        # they are what feed_requirements.csv needs. The reqrel dump itself
        # carries only the correction factors (roughly +/-10% adjustments to
        # ENNE and CRPR), not the requirements.
        "ENNE", "CRPR", "DRMN", "DRMX", "DAYS"}

REQUIREMENT_ITEMS = ["ENNE", "CRPR", "DRMN", "DRMX", "DAYS"]

# Activity -> item that actually holds the yield.
YIELD_ITEM = {"DCOW": "COMI", "DCOL": "COMI", "DCOH": "COMI"}
DEFAULT_YIELD_ITEM = "YILD"

# Activities whose capreg definition disagrees with the model's and where no
# conversion is defensible without documentation.
#
# GRAS   capreg reports 410.9 for DE000000 while COCO2 national reports 17770
#        for the same year. Those cannot both be kg/ha; the definitions differ.
#
# OANI   not a units problem, a conceptual one. In CAPRI, OANI is a share-index
#        pseudo-activity, not a herd. LEVL is exactly 1.0 at national level and
#        the regional LEVLs sum to 1.0 across NUTS-1 (verified for DE, FR, IT,
#        PL), so LEVL is a regional share of the national "other animals"
#        residual. YILD is then whatever makes PROD = LEVL * YILD / 1000 come
#        out right -- 932709 for Germany. There is no per-head yield to import
#        because CAPRI does not model one.
#
#        The rescaling in cons_levls.gms:877 is unrelated: it multiplies LEVL by
#        1000 and divides the coefficients by 1000 so that the cons_yields
#        bounds (which assume LEVL=1 means 1000 ha or head) apply, then reverses
#        both at line 2617. It is internal and symmetric, and does not describe
#        the delivered data.
YIELD_EXCLUDE = {"GRAS", "GRAE", "GRAI", "OANI"}

# CAPRI names grain maize MAIZ; the model calls it CORN. Without this the
# extract carries MAIZ, the merge looks for CORN, and 181 regions of real grain
# maize yields are silently skipped.
ACTIVITY_ALIASES = {"MAIZ": "CORN"}


def parse_file(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RECORD.match(line)
            if not m:
                continue
            region, activity, item, value = m.groups()
            if item not in KEEP:
                continue
            rows.append((region, activity, item, float(value)))
    return pd.DataFrame(rows, columns=["region", "activity", "item", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    ap.add_argument("--out-dir", type=Path,
                    default=Path("capri_data/sources/capreg"))
    args = ap.parse_args()

    files = sorted(args.export_dir.glob("DATA2_*.txt"))
    if not files:
        raise SystemExit(f"no DATA2_*.txt under {args.export_dir}")
    print(f"parsing {len(files)} member state files...")

    frames = [parse_file(f) for f in files]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["region", "activity", "item"], keep="last")
    print(f"  {len(df):,} records kept "
          f"({df.region.nunique()} CAPRI regions, {df.activity.nunique()} activities)")

    cw_path = args.data_dir / "shared" / "nuts_crosswalk.json"
    cw_all = json.loads(cw_path.read_text())
    rev = {}
    for model_region, codes in cw_all.get("aliases", {}).items():
        for c in codes:
            rev.setdefault(c, model_region)
    for model_region, c in cw_all["resolved"].items():
        rev.setdefault(c, model_region)
    df["model_region"] = df.region.map(rev)

    model_regions = pd.read_csv(
        args.data_dir / "2017/supply/yields.csv", index_col=0).index
    matched = df.dropna(subset=["model_region"])
    print(f"  {matched.model_region.nunique()} of {len(model_regions)} "
          "model regions reachable")

    # --- yields --------------------------------------------------------
    want = matched.copy()
    want["is_yield"] = [
        it == YIELD_ITEM.get(act, DEFAULT_YIELD_ITEM) and act not in YIELD_EXCLUDE
        for act, it in zip(want.activity, want.item)]
    want["activity"] = want.activity.replace(ACTIVITY_ALIASES)
    matched["activity"] = matched.activity.replace(ACTIVITY_ALIASES)
    yld = want[want.is_yield].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")
    yld = yld / 1000.0                       # kg/ha or kg/head -> t
    lev = matched[matched.item == "LEVL"].pivot_table(
        index="model_region", columns="activity", values="value", aggfunc="last")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    yld.to_csv(args.out_dir / "capreg_yields.csv")
    lev.to_csv(args.out_dir / "capreg_levels.csv")

    # Feed requirements, long format: one row per region x activity x item.
    req = matched[matched.item.isin(REQUIREMENT_ITEMS)][
        ["model_region", "activity", "item", "value"]]
    req.to_csv(args.out_dir / "capreg_feed_requirements.csv", index=False)
    print(f"feed requirements: {len(req):,} records, "
          f"{req.model_region.nunique()} regions, "
          f"{req.activity.nunique()} animal activities")

    print(f"\nyields : {yld.shape[0]} regions x {yld.shape[1]} activities, "
          f"{int(yld.notna().sum().sum()):,} values")
    print(f"levels : {lev.shape[0]} regions x {lev.shape[1]} activities")

    # --- what this closes ----------------------------------------------
    cur = pd.read_csv(args.data_dir / "2017/supply/yields.csv", index_col=0)
    livestock = ["DCOW", "BCOW", "BULL", "HFRS", "CALV", "SHGP",
                 "PIGS", "PIGF", "LAYS", "BROI", "OANI"]
    have_ls = [a for a in livestock if a in yld.columns]
    print(f"\nlivestock yields now available: {len(have_ls)}/{len(livestock)} "
          f"-> {have_ls}")
    for a in have_ls[:6]:
        n = int(yld[a].notna().sum())
        print(f"   {a:5s} {n:3d} regions, median {yld[a].median():8.3f} "
              f"(model currently {cur[a].median():.3f}, synthetic)")

    print(f"\nwritten: {args.out_dir}/capreg_yields.csv, capreg_levels.csv")


if __name__ == "__main__":
    main()

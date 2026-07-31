"""
Ingest CAPRI's PMP quadratic terms from the pmppar_17*.gdx dumps.

Two symbols:

  p_pmpQuadTechn(region, activity, T1, T1)   own-activity diagonal
  p_pmpQuadPact(region, group, group)        cross-group off-diagonal

Together these are CAPRI's Q matrix. The Python calibrator currently derives the
diagonal from elasticities and invents the off-diagonals as a uniform
rho = 0.05 / (n - 1), with a comment conceding the value is chosen for numerical
stability rather than economics. The real cross-group terms are structured and
signed -- CERE/CER2 is -0.65 in Germany, CERE/OILS -0.22 -- so the substitution
patterns they encode are not reproducible by any uniform constant.

The group mapping is EPRD_TO_GRP from gams/sets.gms:2918, already ported into
capri_pmp.py. Note that the variant in gams/capdis/sets.gms uses a different
group set and must not be used.

Usage
-----
    python tools/ingest_pmp_terms.py --export-dir /path/to/capri_export
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

TECHN = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9]+)'\.'(?:T1|T)'\.'(?:T1|T)'\s+([-\d.Ee+]+)")
PACT = re.compile(
    r"^'([A-Z]{2}[A-Z0-9]{6})'\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\s+([-\d.Ee+]+)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    cw = json.loads((args.data_dir / "shared/nuts_crosswalk.json").read_text())
    rev = {}
    for model_region, codes in cw.get("aliases", {}).items():
        for c in codes:
            rev.setdefault(c, model_region)
    for model_region, c in cw["resolved"].items():
        rev.setdefault(c, model_region)

    techn, pact = [], []
    for f in sorted(args.export_dir.glob("quadTechn_*.txt")):
        for line in open(f, encoding="utf-8", errors="replace"):
            m = TECHN.match(line)
            if m:
                techn.append((m.group(1), m.group(2), float(m.group(3))))
    for f in sorted(args.export_dir.glob("quadPact_*.txt")):
        for line in open(f, encoding="utf-8", errors="replace"):
            m = PACT.match(line)
            if m:
                pact.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))

    dt = pd.DataFrame(techn, columns=["region", "activity", "value"])
    dp = pd.DataFrame(pact, columns=["region", "group1", "group2", "value"])
    dt["model_region"] = dt.region.map(rev)
    dp["model_region"] = dp.region.map(rev)
    dt = dt.dropna(subset=["model_region"]).drop_duplicates(
        ["model_region", "activity"], keep="last")
    dp = dp.dropna(subset=["model_region"]).drop_duplicates(
        ["model_region", "group1", "group2"], keep="last")

    # CAPRI names grain maize MAIZ; the model calls it CORN.
    dt["activity"] = dt.activity.replace({"MAIZ": "CORN"})

    out = args.data_dir / "sources" / "capreg"
    out.mkdir(parents=True, exist_ok=True)
    dt[["model_region", "activity", "value"]].to_csv(
        out / "pmp_quad_techn.csv", index=False)
    dp[["model_region", "group1", "group2", "value"]].to_csv(
        out / "pmp_quad_pact.csv", index=False)

    print(f"quadTechn: {len(dt):,} records, {dt.model_region.nunique()} model regions, "
          f"{dt.activity.nunique()} activities")
    print(f"quadPact : {len(dp):,} records, {dp.model_region.nunique()} model regions, "
          f"{dp.group1.nunique()} groups")
    off = dp[dp.group1 != dp.group2]
    print(f"\noff-diagonal cross-group terms: {len(off):,}")
    print(f"  negative (substitutes) : {100*(off.value < 0).mean():.0f}%")
    print(f"  median magnitude       : {off.value.abs().median():.4f}")
    print("\nmedian by group pair:")
    print(off.groupby(["group1", "group2"]).value.median().round(3)
          .sort_values().head(12).to_string())


if __name__ == "__main__":
    main()

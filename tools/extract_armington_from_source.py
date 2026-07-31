"""
Extract CAPRI's Armington elasticities from the GAMS source.

No CAPRI run and no GDX are required: the values are literal assignments in the
model source, which is already available.

Where they live
---------------
`gams/arm/market1.gms` sets blanket defaults (p_rhoArm1 = 8.0, p_rhoArm2 = 10.0)
and then overrides a handful of commodities. At line 165 it does an
UNCONDITIONAL include:

    * ---- The following file was commented as "Special adjustments for
    *      Switzerland" but actually assigns most CES elasticities
    $INCLUDE '..\\gams\\special_ch\\market1_ch.gms'

So despite the directory name, `special_ch/market1_ch.gms` is the authoritative
source for most of the Armington elasticities, and CAPRI's own comment says so.
Its header gives the provenance:

    Fontagne L., Guimbard H. and Orefice G. (2019) "Product-Level Trade
    Elasticities", CEPII Working Paper. Information available at HS6 level and
    afterward aggregated by FOAG to the CAPRI market model products using as
    weights RG group imports.

This also settles the earlier confusion. dat/arm/GTP57_134.gdx is the raw GTAP
database, whose sector-level elasticities (gro = 1.30 for all coarse grains)
never matched the model's commodity-level values. CAPRI does not use GTAP for
these at all -- it uses CEPII estimates aggregated at product level.

Precedence, matching how GAMS executes the file
-----------------------------------------------
    1. defaults from market1.gms          rhoArm1 8.0, rhoArm2 10.0
    2. commodity overrides in market1.gms CHES, FRMI, OVEG, OFRU, PORK, ...
    3. market1_ch.gms                     included last, so it wins

Region-conditional assignments (those carrying a $ RM_TO_RMTP(RM,"TUR") or
similar) are recorded separately rather than applied, since the model has no
equivalent regional dimension on this parameter.

Usage
-----
    python tools/extract_armington_from_source.py --gams-dir /path/to/gams
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# Unconditional: p_rhoArmN(RM,"XXXX") = value;
PLAIN = re.compile(
    r'^\s*p_rhoArm([12])\s*\(\s*RM\s*,\s*"([A-Z0-9]+)"\s*\)\s*=\s*([\d.]+)\s*;',
    re.M | re.I)
# Blanket: p_rhoArmN(RM,XX) = value;   (XX is the commodity set)
BLANKET = re.compile(
    r'^\s*p_rhoArm([12])\s*\(\s*RM\s*,\s*(XX|XXBIOF)\s*\)\s*=\s*([\d.]+)\s*;',
    re.M | re.I)
# Region-conditional, recorded but not applied.
CONDITIONAL = re.compile(
    r'^\s*p_rhoArm([12])\s*\(\s*RM\s*,\s*"([A-Z0-9]+)"\s*\)\s*\$\s*'
    r'([^=]+?)=\s*([\d.]+)\s*;',
    re.M | re.I)


def read(path: Path) -> str:
    # CAPRI sources are latin-1: the CEPII citation carries accented characters.
    return path.read_text(encoding="latin1")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams-dir", required=True, type=Path)
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    market1 = args.gams_dir / "arm" / "market1.gms"
    ch = args.gams_dir / "special_ch" / "market1_ch.gms"
    for p in (market1, ch):
        if not p.exists():
            raise SystemExit(f"not found: {p}")

    values: dict[str, dict[str, float]] = {}
    defaults: dict[str, float] = {}
    conditional = []

    # 1. blanket defaults
    for m in BLANKET.finditer(read(market1)):
        if m.group(2).upper() == "XX":
            defaults[f"rhoArm{m.group(1)}"] = float(m.group(3))

    # 2 and 3, in file order: market1.gms then the include
    for path in (market1, ch):
        text = read(path)
        for m in PLAIN.finditer(text):
            values.setdefault(m.group(2), {})[f"rhoArm{m.group(1)}"] = \
                float(m.group(3))
        for m in CONDITIONAL.finditer(text):
            conditional.append({
                "commodity": m.group(2),
                "param": f"rhoArm{m.group(1)}",
                "condition": " ".join(m.group(3).split()),
                "value": float(m.group(4)),
                "file": path.name,
            })

    df = pd.DataFrame(values).T.sort_index()
    df.index.name = "commodity"
    for col, val in defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    print(f"commodities with explicit values : {len(df)}")
    print(f"blanket defaults                 : {defaults}")
    print(f"region-conditional (not applied) : {len(conditional)}")

    ratio = (df.rhoArm2 / df.rhoArm1).dropna()
    print(f"rhoArm2 / rhoArm1                : median {ratio.median():.2f}")

    out = args.data_dir / "sources" / "capri_source"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "capri_armington_elasticities.csv")
    (out / "capri_armington_conditional.json").write_text(
        json.dumps({"defaults": defaults, "conditional": conditional}, indent=1))

    # comparison with the incumbent
    cur = args.data_dir / "2017/market/armington_params.csv"
    if cur.exists():
        ca = pd.read_csv(cur, index_col=0)
        common = [c for c in df.index if c in ca.index]
        if common and "sigma" in ca.columns:
            cmp_ = pd.DataFrame({"model_sigma": ca.loc[common, "sigma"],
                                 "capri_rhoArm1": df.loc[common, "rhoArm1"]})
            cmp_["dev_pct"] = ((cmp_.model_sigma - cmp_.capri_rhoArm1).abs()
                               / cmp_.capri_rhoArm1 * 100).round(1)
            print(f"\nagainst armington_params.csv, {len(common)} commodities: "
                  f"median deviation {cmp_.dev_pct.median():.1f}%")
            print(cmp_.sort_values("dev_pct", ascending=False).head(8).to_string())

    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()

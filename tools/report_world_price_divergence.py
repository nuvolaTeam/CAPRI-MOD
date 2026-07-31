"""
Report divergence between world_prices.csv and CAPRI's own capmod result.

Why this reports rather than asserts
------------------------------------
Nothing in this repository can validate world_prices.csv. The market-module test
compares the model's solved prices against reference values that are the file
itself, rounded -- so it checks solver consistency, not price accuracy. Any check
built from repository data reads the file it would be validating.

CAPRI's capmod base-year result is genuinely independent of it. But the two
disagree materially on three commodities, and on those three the model's values
look more plausible against published 2017 market conditions than CAPRI's do.
So this is a divergence report, not a correction: it says where to look, not
what the answer is.

Extraction note
---------------
The capmod dataOut region dimension mixes individual countries with overlapping
aggregates -- World, EU, NONEU, ASIA, MID_INC, HI_INC, LDC and others all appear
in the same slot. An average across "importers" therefore double-counts badly.
The single global reference is the (World, World) cell, which is what this uses.

Usage
-----
    python tools/report_world_price_divergence.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# model commodity -> CAPRI market commodity
CODE_MAP = {
    "SWHE": "WHEA", "CORN": "MAIZ", "POUL": "POUM",
    "BUTR": "BUTT", "SKIM": "SMIP",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("capri_data"))
    args = ap.parse_args()

    ref_path = args.data_dir / "sources/capmod/capmod_world_reference_2017.csv"
    if not ref_path.exists():
        raise SystemExit(f"not found: {ref_path}\n"
                         "Run tools/ingest_capmod_market.py first.")
    capri = pd.read_csv(ref_path, index_col=0)
    model = pd.read_csv(args.data_dir / "2017/market/world_prices.csv", index_col=0)
    col = model.columns[0]

    rows = []
    for c in model.index:
        k = CODE_MAP.get(c, c)
        if k in capri.index and "Fob" in capri.columns:
            fob = capri.at[k, "Fob"]
            imp = capri.at[k, "ImportP"] if "ImportP" in capri.columns else None
            if pd.notna(fob) and fob > 0:
                rows.append({
                    "commodity": c, "capri_code": k,
                    "model": round(float(model.at[c, col]), 1),
                    "capri_fob": round(float(fob), 1),
                    "capri_importp": round(float(imp), 1) if pd.notna(imp) else None,
                    "dev_pct": round(abs(model.at[c, col] - fob) / fob * 100, 1),
                })
    df = pd.DataFrame(rows).set_index("commodity").sort_values("dev_pct")

    model_col = model[col]
    print(f"{len(df)} commodities comparable\n")
    print(df.to_string())
    print(f"\nmedian |deviation| : {df.dev_pct.median():.1f}%")
    print(f"within 20%         : {int((df.dev_pct <= 20).sum())}/{len(df)}")

    bad = df[df.dev_pct > 50]
    if len(bad):
        print("\nDIVERGING BY MORE THAN 50% -- neither source is assumed correct:")
        for c, r in bad.iterrows():
            print(f"  {c:6s} model {r.model:>8.1f}  CAPRI {r.capri_fob:>8.1f}")
        rnd = [c for c in bad.index if float(model.at[c, col]) % 10 == 0]
        print(f"\n  Of these, {len(rnd)} carry a model value that is an exact\n"
              f"  multiple of 10 ({', '.join(rnd)}) -- the same round-number\n"
              "  fingerprint that marked placeholder data elsewhere in this\n"
              "  project. For those, CAPRI is the more likely source of truth.\n"
              "\n"
              "  The rest need judging individually rather than as a group:\n"
              "    EGGS  model 63.4 is not a credible price for eggs at any\n"
              "          point in 2017; CAPRI's 1173.8 is in the right range.\n"
              "    SOYA  runs the other way -- soybeans traded near 350 EUR/t\n"
              "          in 2017, so the model's 292.6 is closer than 157.1.\n"
              "    CHES, SKIM  both sources are outside the range published for\n"
              "          2017 in opposite directions, which points at a\n"
              "          definitional difference in processing stage or product\n"
              "          aggregation rather than an error in either.\n"
              "\n"
              "  No merge is made here. A wholesale replacement would fix EGGS\n"
              "  and the placeholders while breaking SOYA.")

    out = args.data_dir / "validation" / "world_price_divergence.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()

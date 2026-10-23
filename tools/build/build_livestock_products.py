"""Livestock output by final product, and product values by market (dairy Stage 1, sheep and goat milk).

Writes, from CAPRI's 2017 regional results (res_17<MS>.txt):
  capri_data/2017/supply/livestock_output_by_product_coef.csv    ACT.PRODUCT, kt per 1000 head
      (the split of livestock_output_coef.csv: sheep and goats into meat SGMT and milk SGMI, dairy cows
      into milk COMI and cull-cow beef ...); the market bridge sends SGMI to raw milk, SGMT to meat
  capri_data/2017/supply/livestock_product_value_by_market_coef.csv   now with SHGP.MILK (sheep and goat
      milk value moves with the raw milk price)

    python tools/build/build_livestock_products.py [--dump-dir /home/claude/work/capreg]
"""
import argparse, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import build_livestock_output_coef as B
    D = ROOT / "capri_data" / "2017" / "supply"
    q = B.build_product_quantities(Path(a.dump_dir))
    tot = pd.read_csv(D / "livestock_output_coef.csv", index_col=0)
    for act in tot.columns:
        parts = [c for c in q.columns if c.startswith(act + ".")]
        if parts:
            d = (q[parts].sum(axis=1) - tot[act]).abs().max()
            print(f"  {act}: products {', '.join(p.split('.')[1] for p in parts)}; max |sum - total| {d:.2e}")
    q.to_csv(D / "livestock_output_by_product_coef.csv")
    old = pd.read_csv(D / "livestock_product_value_by_market_coef.csv", index_col=0)
    new = B.build_product_values_by_market(Path(a.dump_dir))
    same = [c for c in old.columns if c in new.columns]
    print(f"by-market values: unchanged columns max |diff| {float((new[same] - old[same]).abs().max().max()):.2e}; "
          f"new {sorted(set(new.columns) - set(old.columns))}")
    new.to_csv(D / "livestock_product_value_by_market_coef.csv")
    print("wrote livestock_output_by_product_coef.csv, livestock_product_value_by_market_coef.csv")

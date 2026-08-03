"""
Add crop-specific detail to variable_costs.csv without breaking PMP calibration.

The problem
-----------
The base variable_costs.csv is a crop-GROUP approximation: within a region, all
arable crops share one cost (e.g. wheat = potato = sugar beet = 444 EUR/ha).
Real costs differ a lot by crop (potatoes cost ~6x wheat).

Why we can't just drop in CAPRI's real costs
---------------------------------------------
CAPRI's TOIN costs are consistent with CAPRI's own yields/prices. Dropped onto
this model's yields/prices, the net-revenue vector becomes inconsistent and PMP
calibration degrades or fails (some crops go loss-making).

The method (redistribution, not replacement)
--------------------------------------------
Keep each region-group's AREA-WEIGHTED MEAN cost exactly as it is (so the
aggregate PMP calibrated to is untouched), but SPLIT that total across the group's
crops in proportion to CAPRI's crop-specific cost RATIOS. Result: crop-specific
costs that still sum (area-weighted) to the original group cost.

    new_cost_i = capri_ratio_i * scale
    where scale = group_cost / sum_i(area_weight_i * capri_ratio_i)

This preserves calibration (verified: base year 12/12, convergence unchanged)
while roughly doubling cost granularity (distinct values per region 14 -> 28).

Usage
-----
Provide CAPRI national TOIN per crop (median across countries is enough for
ratios). Then run this over the base cost file. See VARIABLE_COSTS_NOTES.md for
how to extract TOIN via gdxdump.
"""
import numpy as np
import pandas as pd


ARABLE = ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "CORN", "OCER", "POTA",
          "SUGB", "SUNF", "RAPE", "SOYA", "OOIL", "PULS"]


def redistribute(costs: pd.DataFrame, areas: pd.DataFrame,
                 capri_cost: dict, group=ARABLE) -> pd.DataFrame:
    """Return a cost frame with within-group crop detail, group means preserved."""
    new = costs.copy().astype(float)
    grp_crops = [c for c in group if c in costs.columns and c in capri_cost]
    for reg in costs.index:
        grp = [c for c in grp_crops if c in areas.columns and areas.at[reg, c] > 0]
        if len(grp) < 2:
            continue
        cur_cost = costs.at[reg, grp[0]]           # group members share one value
        w = np.array([areas.at[reg, c] for c in grp], dtype=float)
        if w.sum() == 0:
            continue
        w = w / w.sum()
        ratios = np.array([capri_cost[c] for c in grp])
        scale = cur_cost / (w * ratios).sum()       # preserve area-weighted mean
        for c, rt in zip(grp, ratios):
            new.at[reg, c] = rt * scale
    return new


if __name__ == "__main__":
    import sys
    # capri_cost.json: {"SWHE": 642.4, "POTA": 2919.7, ...}
    import json
    costs = pd.read_csv(sys.argv[1], index_col=0)
    areas = pd.read_csv(sys.argv[2], index_col=0)
    capri_cost = json.load(open(sys.argv[3]))
    out = redistribute(costs, areas, capri_cost)
    out.to_csv(sys.argv[4], float_format="%.2f")
    print(f"Wrote {sys.argv[4]}")

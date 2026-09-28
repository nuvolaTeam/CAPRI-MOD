#!/usr/bin/env python3
"""Compare a policy scenario against the baseline, EU-wide.

Why this exists as a tool
-------------------------
The Farm-to-Fork numbers reported in this project were for a long time computed
on the FIRST 30 REGIONS in index order - overwhelmingly German and Austrian.
CAPRI's published figures are EU-wide, and permanent crops are marginal in that
sample: Europe's olives, vines and citrus are in Spain, Italy, Greece and
Portugal, none of which were included. A convenience subset became the basis of
a published comparison, exactly as `max_outer_iter=1` once did.

So the comparison lives here, it runs every region by default, and it runs to
convergence. If a subset is ever wanted, it has to be asked for explicitly.

Usage
-----
    python tools/run_policy_comparison.py                 # all four F2F instruments
    python tools/run_policy_comparison.py --pesticide 0.5 # one instrument
    python tools/run_policy_comparison.py --regions 30    # explicit subset, flagged
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CEREALS = ("SWHE", "DWHE", "BARL", "OATS", "RYEM", "CORN", "OCER", "PARI")
OILSEEDS = ("RAPE", "SUNF", "SOYA", "OOIL")
PERMANENT = ("APPL", "OFRU", "CITR", "OLIV", "TAGR", "WINE", "TOMA", "OVEG")
#: published CAPRI results for the full Farm-to-Fork package (JRC121368)
CAPRI_F2F = {"cereals": -15.0, "oilseeds": -15.0, "permanent": -12.0}


def _totals(result) -> pd.Series:
    out: dict = {}
    for _, res in result.get("supply", {}).items():
        for act, val in res.activities.items():
            out[act] = out.get(act, 0.0) + float(val)
    return pd.Series(out)


def _group(series: pd.Series, group) -> float:
    return sum(float(series.get(c, 0.0)) for c in group if c in series.index)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", type=int, default=None,
                    help="limit to the first N regions (NOT recommended; the "
                         "first regions in index order are all German/Austrian "
                         "and contain almost no permanent crops)")
    ap.add_argument("--pesticide", type=float, default=0.50)
    ap.add_argument("--organic", type=float, default=0.25)
    ap.add_argument("--set-aside", type=float, default=0.10)
    ap.add_argument("--no-nutrient", action="store_true")
    ap.add_argument("--out", default=None, help="write results to this file too")
    args = ap.parse_args()

    from capri_mod.model import CAPRIModel
    from capri_mod.policy.policy_module import PolicyScenario

    model = CAPRIModel(data_dir=str(_ROOT / "capri_data"), verbose=False)
    regions = list(model.data["areas"].index)
    if args.regions:
        regions = regions[:args.regions]
        print(f"WARNING: restricted to {len(regions)} regions — not comparable "
              "with CAPRI's EU-wide published figures")
    else:
        print(f"running all {len(regions)} regions")

    started = time.time()
    base = _totals(model.run(scenario="BASELINE", regions=regions))
    scenario = PolicyScenario(
        name="F2F",
        pesticide_reduction=args.pesticide,
        organic_area_target=args.organic,
        set_aside_requirement=args.set_aside,
        nutrient_surplus_target=not args.no_nutrient)
    shocked = _totals(model.run(custom_scenario=scenario, regions=regions))

    lines = []
    for name, group in (("cereals", CEREALS), ("oilseeds", OILSEEDS),
                        ("permanent", PERMANENT)):
        b, s = _group(base, group), _group(shocked, group)
        if b <= 0:
            continue
        change = (s / b - 1.0) * 100.0
        capri = CAPRI_F2F[name]
        lines.append(f"{name:10s} {change:+7.2f}%   CAPRI {capri:+.0f}%   "
                     f"ratio {change / capri:4.2f}   base {b:9,.0f} kha")
    lines.append(f"({len(regions)} regions, {time.time() - started:.0f}s)")

    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

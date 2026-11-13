"""CAPRI's slack on the partial derivative of the fertiliser distribution priors in the Green Deal group
(supply/set_fert_priors.gms l. 664-785, v_fertDistPartialSlack): "Fix unclear infeasibilities related to crops with tiny
areas and fertiliser need". With %scenarioGroup%==greendeal (l. 672, whatever the simulation year), CAPRI frees the
slack of e_fertDistPartial (supply_model.gms l. 1535-1546: (partial + beta) (fertDist + slack) = alpha - 1) in a listed
set of NUTS 2 regions (curNuts2, l. 680-707):
  for every nutrient, source and crop group of such a region whose prior mode is below 5e-3 (1000 t), within +-mode;
  for the listed (region, group) pairs (extraSlackRegion_to_ngrp, l. 709-738), for every nutrient and source, within
  +-(mode + 0.1) (1000 t).
The slack has no cost in CAPRI's objective.

This builder reads the Green Deal block of the file (the $iftheni.nuts2g block) and writes
capri_data/scenarios/greendeal_group/fert_partial_slack.csv: capri_region, ngrp (empty: the region's tiny-prior rule
only), as CAPRI lists them. The model applies the rule (RegionalSupplyModel._npk_spec).

    python tools/build/build_fert_partial_slack.py [CAPRI gams folder, default capri_sources/gams]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import to_csv  # noqa: E402

import pandas as pd  # noqa: E402

OUT = ROOT / "capri_data" / "scenarios" / "greendeal_group" / "fert_partial_slack.csv"


def parse(text: str) -> pd.DataFrame:
    """The Green Deal block's curNuts2 regions and extraSlackRegion_to_ngrp pairs, in the file's order."""
    m = re.search(r"\$iftheni\.nuts2g\s+%scenarioGroup%==greendeal(.*?)\$endif\.nuts2g", text, re.S | re.I)
    if m is None:
        raise SystemExit("set_fert_priors.gms: the Green Deal block ($iftheni.nuts2g) not found")
    blk = "\n".join(l for l in m.group(1).splitlines() if not l.lstrip().startswith("*"))
    regs = re.findall(r'curNuts2\("([A-Z0-9]+)"\)\s*=\s*yes', blk, re.I)
    pairs = re.findall(r'extraSlackRegion_to_ngrp\("([A-Z0-9]+)"\s*,\s*"([A-Z]+)"\)\s*=\s*yes', blk, re.I)
    if not regs:
        raise SystemExit("set_fert_priors.gms: no curNuts2 region in the Green Deal block")
    missing = sorted({r for r, _ in pairs} - set(regs))
    if missing:
        raise SystemExit(f"set_fert_priors.gms: listed pairs of regions outside curNuts2: {missing}")
    rows = [(r, g) for r, g in pairs]
    rows += [(r, "") for r in regs if r not in {p for p, _ in pairs}]
    return pd.DataFrame(rows, columns=["capri_region", "ngrp"])


def main():
    gams = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "gams"
    src = gams / "supply" / "set_fert_priors.gms"
    df = parse(src.read_text(encoding="latin-1"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    to_csv(df, OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {df.capri_region.nunique()} regions, {int((df.ngrp != '').sum())} listed "
          f"(region, group) pairs")


if __name__ == "__main__":
    main()

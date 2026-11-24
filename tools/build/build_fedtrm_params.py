"""CAPRI's literal table of the baseline feed calibration's priors (capri_data/2017/feed/fedtrm_params.csv), the data
of capri_mod/feed/equations/fedtrm_prior_pw.py.

Read from CAPRI star 3.0's feed/fedtrm_prior_pw.gms (capri_sources/gams):
- p_FeedAggrPrior(maact, feed aggregate.item): the expected shares of the feed aggregates FeedCons and FeedOth in an
  animal's dry matter intake (shInAact) and the bounds of their corrections in the priors' rounds (maxCorrUp,
  maxCorrDown, also for FeedRough) (the TABLE, l. 39-59; FeedRough's and FeedTotal's shares are statements of the
  module, l. 61-62).

Output, long: symbol, key1 (the animal), key2 (the feed aggregate), key3 (the item), value.

    python tools/build/build_fedtrm_params.py [--gams capri_sources/gams]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from gams_text import read_text, table_records  # noqa: E402  (GAMS's table layout)
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)

OUT = ROOT / "capri_data" / "2017" / "feed" / "fedtrm_params.csv"


def p_FeedAggrPrior(gams: Path) -> list[tuple]:
    """TABLE p_FeedAggrPrior: rows the animal activities, columns <feed aggregate>.<item>."""
    rows = []
    for a, col, v in table_records(read_text(gams / "feed" / "fedtrm_prior_pw.gms"), "p_FeedAggrPrior", 1, "",
                                   unquote=True):
        g, item = col.split(".")
        rows.append(("p_FeedAggrPrior", a, g, item, float(v)))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    a = ap.parse_args()
    rows = p_FeedAggrPrior(a.gams)
    t = pd.DataFrame(rows, columns=["symbol", "key1", "key2", "key3", "value"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(t)} rows ({', '.join(f'{s} {n}' for s, n in t.symbol.value_counts().items())})")


if __name__ == "__main__":
    main()

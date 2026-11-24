"""CAPRI's 2030 total feed use of each purchased feed bulk per member state, the denominator of the share of the bulk
that the market's ingredients cover in CAPRI's update of the bulk prices (arm/set_prices.gms l. 382-421, the Laspeyres
version; capri_mod/market/equations/set_prices.py; register DEP-14).

    DATA(MS, "GROF", FEED_TRD, "TRD") = SUM(FEED_TO_O(FEED, ROWS), DATA(MS, "FEDM", ROWS, "TRD"))
        (capmod/load_base_data_and_trends.gms l. 688): every row of the bulk, the market's products and the others
        (MOLA in FENE, OOIL in FOTH: "rows like OOIL are not in set MARR", set_prices.gms l. 374)

The value is CAPRI's simulation data at the trend point (sim_ini_21730's DATA, "TRD"), for the member states with a
row of the five bulks (sets.gms OM_OBJE l. 5135-5136) in feed_bulks_eu.csv or feed_bulks_noneu.csv (the EU's and
Norway's). The bulk's market products' feed (FOOD of set_prices.gms l. 375-376) is feed_bulks_*.csv's feed_kt summed.

Sources: capri_sources/reference/simini/simini_21730/DATA.csv.gz; capri_data/2017/market/feed_bulks_eu.csv,
feed_bulks_noneu.csv.

Output: capri_data/2017/market/feed_bulks_grof.csv
    ms, bulk, grof_kt

    python tools/build/build_feed_bulk_grof.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import REFERENCE, need  # noqa: E402  (CAPRI's material outside the repository)

SIMINI = REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"
M = ROOT / "capri_data" / "2017" / "market"
OUT = M / "feed_bulks_grof.csv"
BULKS = ("FCER", "FPRO", "FENE", "FMIL", "FOTH")


def main(check: bool = False):
    pairs = set()
    for f in ("feed_bulks_eu.csv", "feed_bulks_noneu.csv"):
        # the code pairs only, read as text (no float of these files is used; test_exact_io.py)
        t = pd.read_csv(M / f, keep_default_na=False, dtype=str)
        pairs |= {(r.ms, r.bulk) for r in t.itertuples() if r.bulk in BULKS}
    grof = {}
    with gzip.open(need(SIMINI, "CAPRI's simulation data"), "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["d1"] == "GROF" and r["d3"] == "TRD" and (r["d0"], r["d2"]) in pairs:
                grof[(r["d0"], r["d2"])] = float(r["value"])
    missing = sorted(pairs - set(grof))
    if missing:
        raise ValueError(f"no GROF at TRD in sim_ini_21730 for {missing[:10]} ({len(missing)})")
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ms", "bulk", "grof_kt"])
    for (ms, b) in sorted(grof):
        w.writerow([ms, b, repr(grof[(ms, b)])])
    text = buf.getvalue()
    print(f"feed_bulks_grof: {len(grof)} member-state bulks")
    if check:
        if OUT.read_text() != text:
            raise SystemExit(f"{OUT.relative_to(ROOT)} differs from sim_ini_21730")
        print("unchanged:", OUT.relative_to(ROOT))
        return
    OUT.write_text(text)
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)

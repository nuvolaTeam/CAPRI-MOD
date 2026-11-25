#!/usr/bin/env python3
"""Check the port of CAPRI's year data (capri_mod/projection/equations/load_base_data_and_trends.py) against CAPRI's
own: the year's data "Y" of sim_ini_21730 rebuilt from its base year "BAS" and CAPRI's trends
(trends_1730, CAPTRD's DATA2), then compared cell by cell with sim_ini_21730's "Y".

sim_ini's "Y" is written after the whole of capmod's preparation, so cells that later statements set (create_sim_ini_
gdx.gms l. 300-365, define_inputs.gms, the requirements, ...) differ; the report groups the differences by column and
row so that they can be traced to those statements. CAPRI's results are only checked against, nothing is taken from
them into the port.

    python3 tools/check/check_year_data_2030.py --ms DK [--rtol 1e-9] [--show 20] [--bas capreg] [--items feed]

--sim-ini applies create_sim_ini_gdx.gms l. 311-369 too (capri_mod/projection/equations/create_sim_ini_gdx_data.py),
the deletions before CAPRI writes sim_ini. --cells CSV compares only the cells of the file at "Y"
(check_fedtrm_cal_2030.py --record writes the cells the feed chain reads); --items feed only the cells the feed chain
reads (the activities' columns, the feeds' contents, balance positions, unit values and losses: feed_cells).

With --sim-ini, on the cells the feed chain reads, the differences left are the five pairs CAPRI sets later: the
stocking rate AGGR.YCOW (feed/req_or_man_fnc.gms l. 100) and the data activities' levels GRAS, DCOW, BULF, HEIF
(inflation_and_trend_interpolation.gms l. 146): Denmark 5 of 1,153 cells, Germany 169 of 40,052 (34 units).

With --bas capreg the base year itself is rebuilt too: CAPREG's results (capri_sources/reference/capreg_base/17, CAPREG's
DATA2 at "Y") through CAPRI's base year loading (base_year_data), compared with sim_ini_21730's "BAS" first; the year's
data are then built on it. Without, the year's data are built on sim_ini_21730's "BAS".
"""
from __future__ import annotations

import argparse
import dataclasses
import gzip
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "check"), str(ROOT / "tools" / "lib")]

from capri_mod.projection.equations import load_base_data_and_trends as ly  # noqa: E402

SIMINI = ROOT / "capri_sources" / "reference" / "simini" / "simini_21730" / "DATA.csv.gz"
TRENDS = ROOT / "capri_sources" / "exports" / "trends_1730.csv"
CAPREG = ROOT / "capri_sources" / "reference" / "capreg_base" / "17"
_REC = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'([^']*)'\s+(\S+?),?\s*$")


def _num(s: str) -> float:
    s = s.strip().rstrip(",")
    return 0.0 if s.upper() == "EPS" else float(s)


def read_simini(regions: set, positions=("BAS", "TRD", "Y")) -> ly.Data:
    import csv
    D = ly.Data()
    with gzip.open(SIMINI, "rt", newline="") as f:
        for r, c, w, t, v, *_ in csv.reader(f):
            if r in regions and t in positions:
                try:
                    D.set(r, c, w, t, float(v))
                except ValueError:
                    continue
    return D


def read_trends(regions: set) -> ly.Data:
    D2 = ly.Data()
    with open(TRENDS) as f:
        for line in f:
            m = _REC.match(line)
            if m and m.group(1) in regions and m.group(4) == "Y":
                D2.set(m.group(1), m.group(2), m.group(3), "Y", _num(m.group(5)))
    return D2


def read_capreg(ms: str, regions: set) -> ly.Data:
    """CAPREG's results of the member state (DATA2 at "Y")."""
    import csv
    D2b = ly.Data()
    with gzip.open(CAPREG / f"{ms}.csv.gz", "rt", newline="") as f:
        rd = csv.reader(f)
        next(rd)
        for r, c, w, t, v, *_ in rd:
            if r in regions and t == "Y":
                D2b.set(r, c, w, "Y", float(v))
    return D2b


def feed_cells(S: ly.YearSets):
    """The cells the feed chain reads: the columns of DATA that the requirement call takes from sim_ini
    (check_requirements_2030.state_2030: the animal and crop activities and OTHER_COLS) and those the baseline feed
    calibration adds (the feeds' contents REQSC, their unit values UVAG and losses LOSF)."""
    import check_requirements_2030 as req
    cols = set(S.AACT) | set(S.CACT) | set(req.OTHER_COLS) | set(S.REQSC) | {"UVAG", "LOSF"}
    return lambda c, w: c in cols


def _compare(D: ly.Data, ref: ly.Data, regions: set, pos: str, rtol: float, show: int, only=None) -> None:
    keys = set(D.keys(pos)) | set(ref.keys(pos))
    if only is not None:
        keys = {k for k in keys if only(*k)}
    n, bad, ex = 0, Counter(), {}
    for (c, w) in keys:
        for r in regions:
            x, y = D.get(r, c, w, pos), ref.get(r, c, w, pos)
            n += 1
            if abs(x - y) > rtol * max(1.0, abs(y)):
                bad[(c, w)] += 1
                ex.setdefault((c, w), (r, x, y))
    print(f"{pos}: cells compared {n}; differing {sum(bad.values())} in {len(bad)} column x row pairs")
    by_col = Counter()
    for (c, w), k in bad.items():
        by_col[c] += k
    print("  by column:", by_col.most_common(show))
    for (c, w), k in bad.most_common(show):
        r, x, y = ex[(c, w)]
        print(f"  {c:8s} {w:8s} {k:5d}  e.g. {r}: port {x:.6g} sim_ini {y:.6g}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", required=True, help="the member state's two letters (DK, DE, ...)")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--show", type=int, default=20)
    ap.add_argument("--bas", choices=("simini", "capreg"), default="simini")
    ap.add_argument("--items", choices=("all", "feed"), default="all",
                    help="feed: only the cells the feed chain reads (feed_cells)")
    ap.add_argument("--sim-ini", action="store_true",
                    help="apply create_sim_ini_gdx.gms l. 311-369 after the year's data (create_sim_ini_gdx_data)")
    ap.add_argument("--cells", type=Path, default=None,
                    help="only the cells of this CSV (position, column, row), as check_fedtrm_cal_2030.py --record "
                         "writes the cells the feed chain reads")
    a = ap.parse_args(argv)

    S = ly.YearSets.from_codes()
    mine = {r for r in S.RS if r.startswith(a.ms)}
    loaded = mine | set(S.MSALL)
    S = dataclasses.replace(S, RS=S.RS & loaded, RU=S.RU & loaded, MS=S.MS & loaded)
    ref = read_simini(mine, ("Y", "BAS"))
    if a.bas == "capreg":
        own = ly.Data()
        D2b = read_capreg(a.ms, mine)
        Sm = dataclasses.replace(S, RS=S.RS & mine, RU=S.RU & mine, MS=S.MS & mine)
        ly.base_year_data(own, D2b, Sm)
        _compare(own, ref, mine, "BAS", a.rtol, a.show)
        D = read_simini(loaded - mine, ("BAS",))       # the other member states' base year, for FROM_CAPTRD
        for (t, c, w), d in own.c.items():            # the member state's base year loading, every position
            for r, v in d.items():
                D.set(r, c, w, t, v)
    else:
        D = read_simini(loaded, ("BAS",))
    D2 = read_trends(loaded)
    print(f"{a.ms}: {len(mine)} regions; BAS {sum(len(v) for (t, *_), v in D.c.items() if t == 'BAS')} cells, "
          f"trends {sum(len(v) for v in D2.c.values())} cells")
    fc = ly.year_data(D, D2, S, check=False)
    if a.sim_ini:
        from capri_mod.projection.equations import create_sim_ini_gdx_data as csd
        csd.create_sim_ini_gdx_data(D, S)
    print(f"FROM_CAPTRD: {len(fc)} positions")
    try:
        ly.assert_year_data(D, S)
        print("CAPRI's asserts: passed")
    except ValueError as e:
        print(f"CAPRI's asserts: {e}")
    only = feed_cells(S) if a.items == "feed" else None
    if a.cells:
        rec = pd.read_csv(a.cells, dtype=str, keep_default_na=False)
        keep = {(c, w) for t, c, w in zip(rec.position, rec.column, rec.row) if t == "Y"}
        only = (lambda c, w: (c, w) in keep)
    _compare(D, ref, mine, "Y", a.rtol, a.show, only)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""EU-wide share of fertiliser in a crop's input cost, from CAPRI's 2017 results (K31).

The supply module's fallback (FERT_COST_SHARE) for the fertiliser cost per ha of a crop CAPRI does not grow in a
region; plant_protection_cost.csv carries CAPRI's regional costs everywhere else. Over CAPRI's NUTS2 regions of the 27
member states, weighted by CAPRI's 2017 activity levels:

    fert_cost_share  = sum L x FERT / sum L x TOIN

the model crops as CAPRI activities summed (tools/build/build_capri_base.CROP_MAP). The plant-protection and
other-input shares this file also held were dropped on 24 October 2026: the Green Deal instruments now apply CAPRI's
regional changes to CAPRI's regional rows only, where CAPRI has a coefficient.

Source: CAPRI 2017 results res_17<MS>.txt (LEVL, FERT, TOIN per activity).
Output: capri_data/2017/supply/crop_cost_shares.csv (crop, fert_cost_share). Set-aside is computed like the other crops
(CAPRI's SETA and FALL: where CAPRI gives them an input cost, 40 regional rows, all of it is fertiliser, so the share
is 1). Until 29 October 2026 the builder skipped set-aside and kept the file's row as it was (a read of its own output;
the value, 1.0, is the same).

    python tools/build/build_crop_cost_shares.py [--dump-dir /home/claude/work/capreg] [--out FILE]
"""
from __future__ import annotations

import sys
import argparse, glob, importlib.util, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft

import importlib.util as _ilu
_sp_mr = _ilu.spec_from_file_location("_mr", Path(__file__).resolve().parents[2] / "tools" / "lib" / "_model_regions.py")
_mr = _ilu.module_from_spec(_sp_mr); _sp_mr.loader.exec_module(_mr)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "capri_data" / "2017" / "supply" / "crop_cost_shares.csv"
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'(FERT|TOIN|LEVL)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS2 as _EU_FROM_DATA  # noqa: E402  (capri_data/shared/eu_market_blocks.csv)
EU27 = set(_EU_FROM_DATA)                                  # CAPRI's EU member states, from the data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--out", type=Path, default=DEST)
    a = ap.parse_args()
    v = defaultdict(dict)
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m and m.group(1)[:2] in EU27 and _mr.regional_row(m.group(1)):     # the units of DK, EE ... included (K87)
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    sp = importlib.util.spec_from_file_location("base", ROOT / "tools" / "build" / "build_capri_base.py")
    base = importlib.util.module_from_spec(sp); sp.loader.exec_module(base)
    crops = dict(base.CROP_MAP)
    tot = defaultdict(lambda: defaultdict(float))
    for reg, d in v.items():
        for col, acts in crops.items():
            for act in acts:
                L, T = d.get((act, "LEVL"), 0.0), d.get((act, "TOIN"), 0.0)
                if L <= 0 or T <= 0:
                    continue
                tot[col]["toin"] += L * T
                tot[col]["fert"] += L * d.get((act, "FERT"), 0.0)
    new = pd.DataFrame({c: {"fert_cost_share": t["fert"] / t["toin"]} for c, t in tot.items() if t["toin"] > 0}).T
    new = new.sort_index()
    new.index.name = "crop"
    new[["fert_cost_share"]].to_csv(a.out)
    print(f"wrote {a.out}: {len(new)} crops")
    print(new.to_string())


if __name__ == "__main__":
    main()

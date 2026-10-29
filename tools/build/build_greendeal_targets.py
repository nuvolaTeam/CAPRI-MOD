"""CAPRI's Green Deal targets per member state, from its policy input GDX files (KNOWN_ISSUES K101).

    landscape_targets_ms.csv  member_state, landscape_pp
        p_landscapeTargets(MS) of gams/pol_input/greendeal/landscape_targets.gdx: the share of UAA in non-productive
        landscape elements to reach, percentage points (load_landscape_targets.gms)
    organic_targets_ms.csv    member_state, arable_pp, grassland_pp, permanent_pp, uaa_pp
        p_organicTargetMS(MS, ARA / J0000 / PECR) of organic_targets.gdx (arable land, grassland, permanent crops) and
        p_organicTargetUAA(MS) of organic_targets_uaa.gdx, percentage points (load_organic_targets.gms)

Rows: the member states (NUTS-0 codes, as CAPRI's files key them) of any of the three symbols, sorted; a member state
a symbol does not carry has an empty cell (CAPRI sets no target there: landscape CY, ES, FI; organic by land type PT).
Until 29 October 2026 both files had no builder (written from a dump at 15 significant digits); the values are now the
GDX's doubles.

    python tools/build/build_greendeal_targets.py [--gams DIR] [--gdxlib DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _gdx import read_symbol  # noqa: E402

GAMS = Path("/home/claude/work/allgms/gams")
OUT = ROOT / "capri_data" / "2017" / "policy"
#: CAPRI's land types of p_organicTargetMS and the file's columns
ORGANIC_COLS = {"ARA": "arable_pp", "J0000": "grassland_pp", "PECR": "permanent_pp"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=GAMS)
    ap.add_argument("--gdxlib", default=None)
    a = ap.parse_args()
    gd = a.gams / "pol_input" / "greendeal"
    land = {ms: v for ms, v in read_symbol(gd / "landscape_targets.gdx", "p_landscapeTargets", a.gdxlib)}
    org = read_symbol(gd / "organic_targets.gdx", "p_organicTargetMS", a.gdxlib)
    uaa = {ms: v for ms, v in read_symbol(gd / "organic_targets_uaa.gdx", "p_organicTargetUAA", a.gdxlib)}
    unknown = sorted({lt for _, lt, _ in org} - set(ORGANIC_COLS))
    if unknown:
        raise SystemExit(f"p_organicTargetMS has land types {unknown} the file has no column for")
    ms = sorted(set(land) | {m for m, _, _ in org} | set(uaa))

    lt = pd.DataFrame({"landscape_pp": pd.Series(land, dtype=float)}).reindex(ms)
    lt.index.name = "member_state"
    lt.to_csv(OUT / "landscape_targets_ms.csv")

    ot = pd.DataFrame(index=pd.Index(ms, name="member_state"), columns=[*ORGANIC_COLS.values(), "uaa_pp"], dtype=float)
    for m, t, v in org:
        ot.at[m, ORGANIC_COLS[t]] = v
    for m, v in uaa.items():
        ot.at[m, "uaa_pp"] = v
    ot.to_csv(OUT / "organic_targets_ms.csv")
    print(f"landscape_targets_ms.csv: {lt.landscape_pp.notna().sum()} of {len(ms)} member states; "
          f"organic_targets_ms.csv: {ot.notna().all(axis=1).sum()} complete rows")


if __name__ == "__main__":
    main()

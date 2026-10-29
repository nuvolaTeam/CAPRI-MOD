"""CAPRI's own-price elasticities of crop yields, p_yieldElas (supply/yield_elas.gms), on the model's crops
(KNOWN_ISSUES K101).

    capri_data/2017/supply/yield_price_elasticity.csv   crop, elasticity, source

CAPRI sets p_yieldElas(MS, CERE) = 0.3, (MS, OILS) = 0.2, (MS, "POTA") = 0.2 for every member state (yield_elas.gms),
CERE and OILS the Grandes Cultures sets of global/fromimpact/sets.gms (CERE_COLS, OILS_COLS). This builder reads the
assignments p_yieldElas(MS, <set or "activity">) = <value> and expands the sets in their listed order; CAPRI's
activities named as the model's crops by capri_data/schema/codes/model_activities.csv (MAIZ is CORN). Until 29 October
2026 the file had no builder (the same values, written by hand).

    python tools/build/build_yield_price_elasticity.py [--gams DIR]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAMS = Path("/home/claude/work/allgms/gams")
OUT = ROOT / "capri_data" / "2017" / "supply" / "yield_price_elasticity.csv"


def set_members(text: str, name: str) -> list[str]:
    """The members of SET <name> "..." / ... / in their listed order."""
    m = re.search(r"SET\s+" + re.escape(name) + r"\b[^/]*/(.*?)/\s*;", text, re.S | re.I)
    if not m:
        raise KeyError(f"set {name} not found")
    return [l.split()[0] for l in m.group(1).splitlines() if l.strip() and not l.lstrip().startswith("*")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=GAMS)
    a = ap.parse_args()
    sets = (a.gams / "global" / "fromimpact" / "sets.gms").read_text(errors="ignore")
    groups = {"CERE": set_members(sets, "CERE_COLS"), "OILS": set_members(sets, "OILS_COLS")}
    src = (a.gams / "supply" / "yield_elas.gms").read_text(errors="ignore")
    with open(ROOT / "capri_data" / "schema" / "codes" / "model_activities.csv", newline="") as f:
        to_model = {r["capri_codes"]: r["code"] for r in csv.DictReader(f) if r["kind"] == "crop"}
    rows = []
    for m in re.finditer(r"^\s*p_yieldElas\(\s*MS\s*,\s*(\"?)(\w+)\1\s*\)\s*=\s*([\d.Ee+-]+)\s*;", src, re.M):
        quoted, key, v = m.group(1), m.group(2), float(m.group(3))
        members = [key] if quoted else groups[key]
        for c in members:
            if c not in to_model:
                raise SystemExit(f"CAPRI activity {c} has no model crop (model_activities.csv)")
            note = f" ({c})" if to_model[c] != c else ""
            rows.append((to_model[c], v, f"CAPRI supply/yield_elas.gms p_yieldElas(MS,{key}){note}"))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["crop", "elasticity", "source"])
        w.writerows(rows)
    print(f"{OUT.name}: {len(rows)} crops")


if __name__ == "__main__":
    main()

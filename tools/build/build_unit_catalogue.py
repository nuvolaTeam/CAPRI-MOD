"""The unit catalogue of the data declarations (capri_data/codes/units.csv): CAPRI's units, and the model's own.

CAPRI declares its units in gams/CAPRIunits.gms (Witzke and Britz, 2009): the set capri_u, one acronym per unit with
its description ("U_TonPerHa" "Metric ton per ha"), used to give each COLS x ROWS cell of CAPRI's tables a unit
(P_CAPRIunits). The current source declares 39 units; the CAPRIunits.gdx shipped next to it is an older compile (21
units, prices of 2000), so the list is read from the .gms. The per-cell table needs GAMS to compile and is not used: the
declarations (capri_data/schema/*.sql) give each column its unit from this catalogue.

The model's tables use some units CAPRI does not list (CAPRI's catalogue has t/ha but not t per head); they are kept in
capri_data/codes/model_units.csv and added with capri = no, so a declaration can only name a unit that is in the catalogue and every unit not
CAPRI's is visible.

Output: capri_data/codes/units.csv  code, description, capri (yes|no)

    python tools/build/build_unit_catalogue.py [--gms /home/claude/work/allgms/gams/CAPRIunits.gms]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "codes" / "units.csv"

#: the model's own units, those of its tables that CAPRI's catalogue does not have (hand-kept, one row per unit with
#: the tables that use it): code, description, used_by
MODEL_UNITS = ROOT / "capri_data" / "codes" / "model_units.csv"


def capri_units(gms: Path) -> list[tuple[str, str]]:
    """The elements of the set capri_u in CAPRIunits.gms with their descriptions."""
    text = gms.read_text(errors="ignore")
    m = re.search(r"SET\s+capri_u\s*/(.*?)/\s*;", text, re.S | re.I)
    if not m:
        raise SystemExit(f"{gms}: no set capri_u")
    out = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s or s.startswith("*"):
            continue
        u = re.match(r"(U_\w+)\s+\"([^\"]*)\"", s)
        if u:
            out.append((u.group(1), u.group(2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gms", type=Path, default=Path("/home/claude/work/allgms/gams/CAPRIunits.gms"))
    a = ap.parse_args()
    cu = capri_units(a.gms)
    have = {c.lower() for c, _ in cu}
    with open(MODEL_UNITS, newline="", encoding="utf-8") as fh:
        own = [(r["code"], r["description"]) for r in csv.DictReader(fh)]
    dup = [c for c, _ in own if c.lower() in have]
    if dup:
        raise SystemExit(f"{MODEL_UNITS.name}: CAPRI has these units already: {dup}")
    rows = [(c, d, "yes") for c, d in cu] + [(c, d, "no") for c, d in own]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(("code", "description", "capri"))
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(cu)} CAPRI units, {len(rows) - len(cu)} of the model's own")


if __name__ == "__main__":
    main()

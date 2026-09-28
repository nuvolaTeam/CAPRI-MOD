#!/usr/bin/env python3
"""Build per-region livestock output coefficients from CAPRI capreg DATA2 dumps.

Why this exists
---------------
The model used each livestock activity's CAPRI ``YILD`` as its marketed output.
For fattening pigs and laying hens that is right (``YILD`` equals ``PORK`` /
``EGGS``). For breeding and suckler activities it is not: CAPRI's ``YILD`` there
measures offspring or liveweight, and the marketed product sits in a separate
item — suckler cows carry a ``YILD`` of 422.6 but produce 21.8 of beef, sows
19,917 against 50.6 of pork. So ``gross_output`` for most livestock was not a
tonnage of anything saleable, and had to be suppressed as NaN.

This script rebuilds livestock output from CAPRI's **final-product** items
instead: ``COMI`` (cow milk), ``BEEF``, ``PORK``, ``POUM`` (poultry meat),
``EGGS``, ``SGMT`` / ``SGMI`` (sheep and goat meat and milk). Young-animal items
(``YCAM``, ``YCAF``, ``YPIG`` …) are deliberately excluded: they are produced by
one activity and consumed by another, so counting them would double-count.

Validation (recorded in DATA_SOURCING_REGISTRY)
------------------------------------------------
Summing LEVL x final-product coefficient over CAPRI's *elementary* activities
reproduces CAPRI's own aggregate rows exactly, and the EU27 totals match real
2017 EU production: milk 0.95, beef 0.94, pork 1.01, poultry 0.98, eggs 1.08,
sheep and goat meat 1.01.

Two traps this avoids, both hit while building it:
  * aggregate rows (UAAR, CATA, RUMI, AGGT, …) and the expenditure row EXPD
    carry product items too; summing them gave totals thousands of times too
    high
  * DCOL/DCOH and BULH are intensity VARIANTS of DCOW and BULF; including them
    doubles milk and inflates beef

Method
------
For each model region and model activity::

    coefficient = CAPRI final-product total (kt) / model head count (1000 head)

so that ``level x coefficient`` reproduces CAPRI's regional output exactly at
base and scales with the model's own herd in scenarios. Where a country has no
regional CAPRI rows (CY, DK, EE, HR, LT, LV, MT, SI), the national total is used
and spread over the country's regions by their share of the model's head count.

Usage
-----
    python tools/build_livestock_output_coef.py <dir with res_17<CC>.txt dumps>
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FINAL_PRODUCTS = ("COMI", "BEEF", "PORK", "POUM", "EGGS", "SGMT", "SGMI")
#: CAPRI's market revenue per activity unit. For crops it equals the model's
#: price x yield exactly (wheat in DE11: 135.6 x 6.15 = 833.7 = MREV), so it is
#: the same concept, and for livestock it replaces a revenue built from YILD -
#: which for breeding and suckler activities is not a marketed product at all.
REVENUE_ITEM = "MREV"

#: CAPRI elementary livestock activity -> this model's activity. Verified to
#: reproduce CAPRI's aggregate rows exactly; intensity variants (DCOL, DCOH,
#: BULH) are excluded because they double-count their parent activity.
CAPRI_TO_MODEL = {
    "DCOW": "DCOW",
    "SCOW": "BCOW",
    "BULF": "BULL",
    "HEIF": "HFRS", "HEIR": "HFRS",
    "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
    "SOWS": "PIGS", "PIGF": "PIGS",   # the model keeps all pigs in PIGS
    "HENS": "LAYS",
    "POUF": "BROI",
    "SHGM": "SHGP", "SHGF": "SHGP",
}

#: CAPRI country code -> NUTS country prefixes used by this model.
COUNTRY_PREFIXES = {"BL": ("BE", "LU"), "IR": ("IE",)}

# CAPRI region codes are 8 characters and MAY contain letters after the
# country code (DEA10000, FRB00000). A first version accepted digits only and
# silently dropped every letter-coded region -- a third of Germany's milk and
# nearly all of France's.
_ROW = re.compile(r"'([A-Z]{2}[A-Z0-9]{6})'\.'([^']+)'\.'([^']+)'\.'Y'\s+([^,\s]+)")


def _num(tok: str) -> float:
    """Parse a gdxdump value. GAMS writes ``Eps`` for an explicit tiny
    non-zero and ``NA`` / ``UNDF`` / ``INF`` for special values; a naive
    numeric pattern matched the leading 'E' of 'Eps' and crashed."""
    t = tok.strip().upper()
    if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF"):
        return 0.0
    return float(tok)


def _capri_totals(dump_dir: Path, value_item: str = None):
    """(8-char region, model activity) -> final-product total in kt.

    With ``value_item`` (e.g. MREV) it returns LEVL x that item instead, i.e.
    the activity's total market revenue in thousand EUR.
    """
    totals = defaultdict(float)
    for path in sorted(glob.glob(str(dump_dir / "res_17*.txt"))):
        levl, coef = {}, defaultdict(float)
        for line in open(path, errors="ignore"):
            m = _ROW.match(line)
            if not m:
                continue
            reg, act, item, val = m.group(1), m.group(2), m.group(3), _num(m.group(4))
            if act not in CAPRI_TO_MODEL:
                continue
            if item == "LEVL":
                levl[(reg, act)] = val
            elif value_item is not None:
                if item == value_item:
                    coef[(reg, act)] += val
            elif item in FINAL_PRODUCTS:
                coef[(reg, act)] += val
        for key, lv in levl.items():
            if key in coef:
                reg, act = key
                # the /1000 converts product kilograms to kilotonnes; a money
                # value (MREV) needs no such conversion
                scale = 1.0 if value_item is not None else 1000.0
                totals[(reg, CAPRI_TO_MODEL[act])] += lv * coef[key] / scale
    return totals


def build(dump_dir: Path, value_item: str = None) -> pd.DataFrame:
    from capri_mod.data.loaders import load_all_data

    data = load_all_data(str(_ROOT / "capri_data"))
    herds = data["animal_numbers"]
    model_regions = set(herds.index)
    model_acts = sorted(set(CAPRI_TO_MODEL.values()))

    corr = json.loads((_ROOT / "capri_data" / "shared" /
                       "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]

    def to_model(code8):
        for cand in corr.get(code8, []):
            if cand in model_regions:
                return cand
        return None

    totals = _capri_totals(dump_dir, value_item)

    regional = defaultdict(float)          # (model region, act) -> kt
    national = defaultdict(float)          # (capri country, act) -> kt
    for (code8, act), kt in totals.items():
        if code8.endswith("000000"):
            national[(code8[:2], act)] += kt
            continue
        # Only codes that map to a model region are used. NUTS-1 aggregates
        # (DE100000, FR200000 ...) never map to a NUTS-2 model region, so this
        # also stops them being added on top of their own NUTS-2 regions.
        reg = to_model(code8)
        if reg is not None:
            regional[(reg, act)] += kt

    coef = pd.DataFrame(index=sorted(model_regions), columns=model_acts, dtype=float)

    for (reg, act), kt in regional.items():
        heads = float(herds.at[reg, act]) if act in herds.columns else 0.0
        if heads > 0:
            coef.at[reg, act] = kt / heads

    # Residual allocation: whatever part of the national total was NOT placed
    # on a mapped region is spread over the country's remaining model regions,
    # in proportion to their head count. This covers countries with only a
    # national row (CY, DK, EE, HR, LT, LV, MT, SI) and countries whose regional
    # codes only partly map, without double-counting either.
    for (cc, act), nat_kt in national.items():
        if act not in herds.columns:
            continue
        prefixes = COUNTRY_PREFIXES.get(cc, (cc,))
        regs = [r for r in model_regions if r.startswith(prefixes)]
        placed = sum(regional.get((r, act), 0.0) for r in regs)
        rest = [r for r in regs
                if pd.isna(coef.at[r, act]) and float(herds.at[r, act]) > 0]
        residual = nat_kt - placed
        heads = float(herds.loc[rest, act].sum()) if rest else 0.0
        if residual > 0 and heads > 0:
            for r in rest:
                coef.at[r, act] = residual / heads

    return coef


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out = build(src)
    dest = _ROOT / "capri_data" / "2017" / "supply" / "livestock_output_coef.csv"
    out.to_csv(dest)
    print(f"wrote {dest} — {out.notna().sum().sum()} region x activity coefficients "
          f"(kt per 1000 head)")

    # Market revenue per head, the same way: CAPRI's own regional revenue
    # divided by the model's head count. This replaces a livestock revenue
    # built from price x YILD, which for breeding and suckler activities values
    # a quantity that is not a marketed product - it left gross_margin
    # dominated by pigs and barely moving under policy.
    rev = build(src, REVENUE_ITEM)
    dest2 = _ROOT / "capri_data" / "2017" / "supply" / "livestock_revenue_coef.csv"
    rev.to_csv(dest2)
    print(f"wrote {dest2} — {rev.notna().sum().sum()} coefficients "
          f"(1000 EUR per 1000 head)")

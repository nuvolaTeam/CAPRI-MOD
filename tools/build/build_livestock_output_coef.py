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
    python tools/build/build_livestock_output_coef.py <dir with res_17<CC>.txt dumps>
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FINAL_PRODUCTS = ("COMI", "BEEF", "PORK", "POUM", "EGGS", "SGMT", "SGMI")
#: CAPRI's market revenue per activity unit. For crops it equals the model's
#: price x yield exactly (wheat in DE11: 135.6 x 6.15 = 833.7 = MREV), so it is
#: the same concept, and for livestock it replaces a revenue built from YILD -
#: which for breeding and suckler activities is not a marketed product at all.
REVENUE_ITEM = "MREV"
#: CAPRI final product -> the model's market whose price moves it. Sheep and goat milk is raw milk
#: delivered to dairies with cow milk (CAPRI sets.gms PRCD MILK.(COMI,SGMI)), so it moves with MILK.
PRODUCT_MARKET = {"COMI": "MILK", "BEEF": "BEEF", "PORK": "PORK", "POUM": "POUL", "EGGS": "EGGS", "SGMT": "SGMT",
                  "SGMI": "MILK"}


def build_product_quantities(dump_dir: Path) -> pd.DataFrame:
    """Quantity of each final product per model head, columns 'ACT.PRODUCT' (kt per 1000 head): the
    split of livestock_output_coef (their sum) into CAPRI's products - sheep and goats into meat SGMT
    and milk SGMI, dairy cows into milk COMI and cull-cow beef."""
    cols = {}
    for prod in FINAL_PRODUCTS:
        c = build(dump_dir, f"QTY:{prod}")
        for act in c.columns:
            if c[act].fillna(0).abs().sum() > 0:
                cols[f"{act}.{prod}"] = c[act]
    return pd.DataFrame(cols).sort_index(axis=1)


def build_product_values_by_market(dump_dir: Path) -> pd.DataFrame:
    """Value of each final product per model head, columns 'ACT.MARKET' (EUR per head): a market
    price change moves an animal's revenue by quantity x price change, product by product (a dairy
    cow's cull-cow beef moves with the beef price, her milk with the milk price)."""
    cols = {}
    for prod, mkt in PRODUCT_MARKET.items():
        c = build(dump_dir, f"FINAL_VALUE:{prod}")
        for act in c.columns:
            if c[act].fillna(0).abs().sum() > 0:
                cols[f"{act}.{mkt}"] = c[act]
    return pd.DataFrame(cols).sort_index(axis=1)

#: CAPRI elementary livestock activity -> this model's activity. Verified to
#: reproduce CAPRI's aggregate rows exactly; intensity variants (DCOL, DCOH,
#: BULH) are excluded because they double-count their parent activity.
CAPRI_TO_MODEL = {
    "DCOW": "DCOW",
    "SCOW": "BCOW",
    "BULF": "BULL",
    "HEIF": "HFRS", "HEIR": "HFRS",
    "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
    "SOWS": "PIGS", "PIGF": "PIGF",   # PIGS = sows (with piglets to 20 kg), PIGF = fattening pigs (CAPRI's split)
    "HENS": "LAYS",
    "POUF": "BROI",
    "SHGM": "SHGM", "SHGF": "SHGF",    # sheep and goats for milk / for fattening (CAPRI's split, October 2026)
}

#: CAPRI country code -> NUTS country prefixes used by this model.

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


def _capri_totals(dump_dir: Path, value_item: str = None, products=FINAL_PRODUCTS):
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
            elif item in products:
                coef[(reg, act)] += val
        for key, lv in levl.items():
            if key in coef:
                reg, act = key
                # the /1000 converts product kilograms to kilotonnes; a money
                # value (MREV) needs no such conversion
                scale = 1.0 if value_item is not None else 1000.0
                totals[(reg, CAPRI_TO_MODEL[act])] += lv * coef[key] / scale
    return totals


def _final_product_value_totals(dump_dir: Path, products=FINAL_PRODUCTS):
    """(8-char region, model activity) -> value of final products, 1000 EUR: LEVL x quantity x the
    member state's unit value (UVAG). Young animals are left out. This is the part of an animal's
    output whose value moves with meat, milk and egg prices; it is not CAPRI's MREV, whose content
    differs by activity: for activities that only raise young animals it IS their sales (sows: 24.0
    piglets x EUR 25.43 = 610.9 = MREV in DE94; raised calves CAMR: YBUL x UVAG = 623.7 = MREV), for
    suckler cows it is a quarter of their beef value."""
    totals = defaultdict(float)
    for path in sorted(glob.glob(str(dump_dir / "res_17*.txt"))):
        levl, qty, uvag = {}, defaultdict(dict), {}
        for line in open(path, errors="ignore"):
            m = _ROW.match(line)
            if not m:
                continue
            reg, act, item, val = m.group(1), m.group(2), m.group(3), _num(m.group(4))
            if act == "UVAG" and reg.endswith("000000") and item in products:
                uvag[(reg[:2], item)] = val
            elif act in CAPRI_TO_MODEL:
                if item == "LEVL":
                    levl[(reg, act)] = val
                elif item in products:
                    qty[(reg, act)][item] = val
        for key, lv in levl.items():
            reg, act = key
            v = sum(q * uvag.get((reg[:2], it), 0.0) for it, q in qty.get(key, {}).items()) / 1000.0
            if v:
                totals[(reg, CAPRI_TO_MODEL[act])] += lv * v
    return totals


def build(dump_dir: Path, value_item: str = None) -> pd.DataFrame:
    from capri_mod.data.loaders import load_all_data

    data = load_all_data(str(_ROOT / "capri_data"))
    herds = data["animal_numbers"]
    model_regions = set(herds.index)
    model_acts = sorted(set(CAPRI_TO_MODEL.values()))


    # CAPRI regions -> model regions in GROUPS covering the same territory (tools/lib/_model_regions.py:
    # one to one, splits, merges). The first-candidate rule used before put a split parent's whole
    # total on one part (Finland FI1B: all of Etelae-Suomi's manure on Uusimaa's herd, 990 kg N per
    # dairy cow) and left renamed or split regions (Poland, Saxony, Bolzano/Trento, Budapest,
    # Ireland) to the national-remainder average.
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    _mr = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    code_to_group, groups = _mr.capri_groups(sorted(model_regions))

    if value_item == "FINAL_VALUE":
        totals = _final_product_value_totals(dump_dir)
    elif value_item and value_item.startswith("FINAL_VALUE:"):          # one final product only
        totals = _final_product_value_totals(dump_dir, (value_item.split(":", 1)[1],))
    elif value_item and value_item.startswith("QTY:"):                  # one final product's quantity
        totals = _capri_totals(dump_dir, None, (value_item.split(":", 1)[1],))
    else:
        totals = _capri_totals(dump_dir, value_item)

    grouped = defaultdict(float)           # (group, act) -> kt
    national = defaultdict(float)          # (capri country, act) -> kt
    for (code8, act), kt in totals.items():
        if code8.endswith("000000") and not _mr.is_unit(code8):   # a member state's total (DK000000 is a unit)
            national[(code8[:2], act)] += kt
            continue
        # Only codes in a group with model regions are used. NUTS-1 aggregates
        # (DE100000, FR200000 ...) are in none, so they are never added on top
        # of their own NUTS-2 regions.
        g = code_to_group.get(code8)
        if g is not None:
            grouped[(g, act)] += kt

    coef = pd.DataFrame(index=sorted(model_regions), columns=model_acts, dtype=float)
    regional = defaultdict(float)          # (model region, act) -> kt placed (by heads within a group)
    for (g, act), kt in grouped.items():
        regs_g = sorted(groups[g][1])
        heads = float(herds.loc[regs_g, act].sum()) if act in herds.columns else 0.0
        if heads > 0:
            for r in regs_g:
                coef.at[r, act] = kt / heads
                regional[(r, act)] += kt * float(herds.at[r, act]) / heads

    # Residual allocation: whatever part of the national total was NOT placed
    # on a mapped region is spread over the country's remaining model regions,
    # in proportion to their head count. This covers countries with only a
    # national row (CY, DK, EE, HR, LT, LV, MT, SI) and countries whose regional
    # codes only partly map, without double-counting either.
    for (cc, act), nat_kt in national.items():
        if act not in herds.columns:
            continue
        regs = [r for r in model_regions if r.startswith(cc)]        # CAPRI's codes: BL, IR as CAPRI has them
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
    # Livestock COSTS the same way: CAPRI's regional LEVL x TOIN (total inputs,
    # incl. young-animal purchases and feed) divided by the model's head count.
    # Costs used to be CAPRI's per-head TOIN while revenue was total / model
    # heads: where model heads differ from CAPRI's activity level (bulls and
    # heifers several-fold) revenue was inflated and costs were not - Brittany's
    # bulls earned an 88% margin (CAPRI 15-34%).
    cst = build(src, "TOIN")
    dest3 = _ROOT / "capri_data" / "2017" / "supply" / "livestock_cost_coef.csv"
    cst.to_csv(dest3)
    print(f"wrote {dest3} — {cst.notna().sum().sum()} coefficients (1000 EUR per 1000 head)")
    # ...and REVENUE on the matching basis: CAPRI's total output TOOU (incl. the
    # young animals breeders produce), LEVL x TOOU / model heads. TOOU - TOIN is
    # CAPRI's own margin (GVAP); MREV omits calves, so MREV - TOIN made suckler
    # cows lose 11 times their revenue.
    tou = build(src, "TOOU")
    dest4 = _ROOT / "capri_data" / "2017" / "supply" / "livestock_output_value_coef.csv"
    tou.to_csv(dest4)
    print(f"wrote {dest4} — {tou.notna().sum().sum()} coefficients (1000 EUR per 1000 head)")

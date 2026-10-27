"""Crop yields, producer prices, input costs and CAP premiums for every model region from CAPRI's 2017 results
(Sprint 9s: synthetic data removed, docs/SYNTHETIC_DATA_AUDIT.md A1-A3, A5).

What was wrong. tools/build/build_capri_base.py rebuilt areas and herds from all 27 dumps but its per-hectare pass took only
the FIRST CAPRI activity of each model crop and skipped wine costs and the textile crops; premiums were never rebuilt
at all. So:
  - CAP premiums came from a 192-region extraction (capreg_cap_premium.csv, CAPRI codes); the other 56 regions, and
    fodder, set-aside, wine and fibre everywhere (codes OFAR, SETA/FALL, TWIN, TEXT never matched), fell back to
    cap_payments.csv's BPS - the loader's random generator written to disk (1,957 region x crop cells);
  - wine and fibre costs were template fills (wine 1,313 EUR/ha against CAPRI's 4,500-8,000); fibre yields a
    lognormal draw (1.5 t/ha against CAPRI's 3.8); wine prices of 36 regions national fills.

Now, per model region (the region map of build_capri_base: renames, merges, splits, Ireland, Norway) and model crop
(build_capri_base.CROP_MAP), over the CAPRI activities a summed into the crop,
with the region's source weights w:
    area      A = sum w LEVL_a
    yield     sum w LEVL_a YILD_a / A                              (t/ha: YILD / 1000)
    price     sum w LEVL_a YILD_a MPRI_a / sum w LEVL_a YILD_a     (revenue / production, EUR/t)
    cost      sum w LEVL_a TOIN_a / A                              (EUR/ha)
    premium   sum w LEVL_a PRME_a / A                              (EUR/ha)
A crop the region does not grow (A = 0) takes its member state's CAPRI values (the national row), so a crop that
enters later has CAPRI's own numbers, not a template. Grass keeps its own yield and price (build_capri_base: dry
matter and MREV-based price; CAPRI's grass price is a dummy of 1,000 EUR/t).

Outputs (crop columns only; animal columns untouched):
  capri_data/2017/supply/yields.csv, variable_costs.csv
  capri_data/2017/supply/crop_premium.csv               (new: region x model crop, EUR/ha)
  capri_data/sources/capreg/capreg_producer_prices.csv  (model-coded crop columns written for all regions)
  capri_data/2017/policy/cap_payments.csv               (the payment engine's per-region rates: BPS = CAPRI's
      premiums per ha of UAA, UAAR PRME; ANC, AES, ORGANIC, COUPLED = 0 - CAPRI's results carry no split by
      instrument. The file held the loader's random draw.)

    python tools/build/build_crop_economics_2017.py [dump dir, default /home/claude/work/capreg]
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
import build_capri_base as B  # noqa: E402

ITEMS = ("LEVL", "YILD", "TOIN", "MPRI", "PRME", "MREV", "GRAS")
GRASS_DM = ROOT / "capri_data" / "2017" / "supply" / "grass_dm_content.csv"
PREMIUM = ROOT / "capri_data" / "2017" / "supply" / "crop_premium.csv"
PAYMENTS = ROOT / "capri_data" / "2017" / "policy" / "cap_payments.csv"


def read(dump_dir: Path) -> dict:
    out: dict = defaultdict(lambda: defaultdict(dict))
    for path in sorted(dump_dir.glob("res_17*.txt")):
        for line in open(path, errors="ignore"):
            m = B._ROW.match(line)
            if m and m.group(3) in ITEMS:
                out[m.group(1)][m.group(3)][m.group(2)] = B._num(m.group(4))
    return out


def crop_codes():
    m = {c: tuple(a) for c, a in B.CROP_MAP.items()}
    return m


def values(capri, sources, codes):
    """(area, yield t/ha, price EUR/t, cost EUR/ha, premium EUR/ha) over the sources, or None without area."""
    A = Q = V = C = P = 0.0
    for c, w in sources:
        it = capri.get(c, {})
        for a in codes:
            lv = w * it.get("LEVL", {}).get(a, 0.0)
            if lv <= 0:
                continue
            y = it.get("YILD", {}).get(a, 0.0)
            A += lv
            Q += lv * y
            V += lv * y * it.get("MPRI", {}).get(a, 0.0)
            C += lv * it.get("TOIN", {}).get(a, 0.0)
            P += lv * it.get("PRME", {}).get(a, 0.0)
    if A <= 0:
        return None
    return A, Q / A / 1000.0, (V / Q if Q > 0 else 0.0), C / A, P / A


def national(reg):
    return MS_CODE.get(reg[:2], reg[:2]) + "000000"


def main(dump_dir: Path):
    capri = read(dump_dir)
    yields = _read_csv(B.YIELDS, index_col=0)
    costs = _read_csv(B.COSTS, index_col=0)
    prices = _read_csv(B.PRICES, index_col=0)
    areas = _read_csv(B.AREAS, index_col=0)
    spec = B.build_spec(capri, list(areas.index))
    cmap = crop_codes()
    crops = [c for c in cmap if c in yields.columns or c in costs.columns]
    prem = pd.DataFrame(0.0, index=areas.index, columns=crops)
    n_reg = n_nat = 0
    for reg in areas.index:
        src = spec.get(reg, ())
        nat = ((national(reg), 1.0),)
        for col in crops:
            codes = cmap[col]
            v = values(capri, src, codes) if src else None
            if v is None:
                v = values(capri, nat, codes)
                n_nat += v is not None
            else:
                n_reg += 1
            if v is None:
                continue                                 # CAPRI has the crop nowhere in the member state
            _, y, p, cst, pr = v
            if col != "GRAS":
                if col in yields.columns:
                    yields.at[reg, col] = y
                if p > 0:
                    prices.at[reg, col] = p
            if col in costs.columns:
                costs.at[reg, col] = cst
            prem.at[reg, col] = pr
    pay = pd.DataFrame(0.0, index=areas.index, columns=["BPS", "ANC", "AES", "ORGANIC", "COUPLED"])
    for reg in areas.index:
        v = values(capri, spec.get(reg, ()), ("UAAR",)) if spec.get(reg) else None
        v = v or values(capri, ((national(reg), 1.0),), ("UAAR",))
        pay.at[reg, "BPS"] = v[4] if v else 0.0
    pay.index.name = "region"
    pay.to_csv(PAYMENTS)
    # GRASS: CAPRI's dry-matter content (DRMA of GRAS, 0.22 in every region) for the loader's fresh-to-dry conversion,
    # and the grass price on that basis: CAPRI's revenue per ha (MREV; its grass MPRI is a dummy 1,000) over the
    # dry-matter yield (build_capri_base used a share of 0.20)
    dm = pd.Series(0.0, index=areas.index, name="drma")
    for reg in areas.index:
        src = spec.get(reg) or ((national(reg), 1.0),)
        vals = [capri.get(c, {}).get("GRAS", {}).get("DRMA", 0.0) for c, _ in src]
        vals = [v for v in vals if v > 0] or [capri.get(national(reg), {}).get("GRAS", {}).get("DRMA", 0.0)]
        dm[reg] = vals[0]
        mrev = sum(w * capri.get(c, {}).get("LEVL", {}).get("GRAS", 0.0) * capri.get(c, {}).get("MREV", {}).get("GRAS", 0.0)
                   for c, w in src)
        lv = sum(w * capri.get(c, {}).get("LEVL", {}).get("GRAS", 0.0) for c, w in src)
        # CAPRI's grass yield is the GRAS output of the GRAS activity (kg fresh matter per ha; its YILD item is the
        # revenue); 56 regions carried a template value (~5 t/ha) instead
        fy = (sum(w * capri.get(c, {}).get("LEVL", {}).get("GRAS", 0.0) * capri.get(c, {}).get("GRAS", {}).get("GRAS", 0.0)
                  for c, w in src) / lv) if lv > 0 else 0.0
        if fy <= 0:
            it_ = capri.get(national(reg), {})
            fy = it_.get("GRAS", {}).get("GRAS", 0.0)
        if "GRAS" in yields.columns:
            yields.at[reg, "GRAS"] = fy                  # 0 where CAPRI has no grassland (Malta)
        raw = float(yields.at[reg, "GRAS"]) if "GRAS" in yields.columns else 0.0
        dmy = raw / 1000.0 * dm[reg] if raw > 100 else raw
        if lv > 0 and dmy > 0 and "GRAS" in prices.columns:
            prices.at[reg, "GRAS"] = mrev / lv / dmy
    dm.index.name = "region"
    dm.to_csv(GRASS_DM)
    yields.to_csv(B.YIELDS)
    costs.to_csv(B.COSTS)
    prices.to_csv(B.PRICES)
    prem.index.name = "region"
    prem.to_csv(PREMIUM)
    print(f"{n_reg} region x crop cells from the region's own CAPRI rows, {n_nat} from its member state; "
          f"wrote yields, costs, prices and {PREMIUM.relative_to(ROOT)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/capreg"))

"""CAPRI's two sheep-and-goat activities, SHGM (milk) and SHGF (fattening): their input cost per head and their EU
producer prices, as the retired tools/build/build_shg_split.py computed them (October 2026), unchanged. Used by the
tables' owners: build_crop_economics_2017.py (variable_costs.csv) and build_eu_producer_prices.py
(producer_prices.csv).

  costs   CAPRI's TOIN level-weighted over the region's CAPRI group (tools/lib/_model_regions.capri_groups; the member
          state's row where the group has no regional rows), 2017 results (res_17*.txt dumps, item 'Y')
  prices  CAPREG's regional producer prices (sources/capreg/capreg_producer_prices.csv) herd-weighted over the units
          (animal_numbers.csv)
"""
from __future__ import annotations

import glob
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ACTS = ("SHGM", "SHGF")


def costs(dump: Path, regions) -> pd.DataFrame:
    """regions x (SHGM, SHGF): input cost per head (NaN where CAPRI has none)."""
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    v = defaultdict(dict)
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'(SHGM|SHGF)'\.'(LEVL|YILD|TOIN)'\.'Y'\s+([-\d.Ee+]+)")
    for p in sorted(glob.glob(str(Path(dump) / "res_17*.txt"))):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                v[(m.group(1), m.group(2))][m.group(3)] = float(m.group(4))
    _c2g, groups = mr.capri_groups(list(regions))

    def weighted(codes, act, item):
        num = den = 0.0
        for c in codes:
            d = v.get((c, act), {})
            if d.get("LEVL", 0) > 0:                     # an absent item is 0 (GAMS): milk sheep without milk
                num += d["LEVL"] * d.get(item, 0.0); den += d["LEVL"]
        return num / den if den > 0 else None

    out = pd.DataFrame(index=pd.Index(list(regions)), columns=list(ACTS), dtype=float)
    for act in ACTS:
        col = pd.Series(float("nan"), index=out.index)
        for codes, regs in groups.values():
            x = weighted([c for c in codes if mr.regional_row(c)], act, "TOIN")
            if x is not None:
                for r in regs:
                    if r in col.index:
                        col[r] = x
        for r in col.index[col.isna()]:
            x = weighted([mr.national_code(r)], act, "TOIN")
            if x is not None:
                col[r] = x
        out[act] = col
    return out


def eu_prices(herds: pd.DataFrame, capreg_prices: pd.DataFrame) -> dict:
    """{SHGM: EUR/t, SHGF: EUR/t}: the units' CAPREG prices weighted by their herds."""
    out = {}
    for act in ACTS:
        w = herds[act].reindex(capreg_prices.index).fillna(0.0)
        x = capreg_prices[act].where(capreg_prices[act] > 0)
        ok = x.notna() & (w > 0)
        out[act] = float((x[ok] * w[ok]).sum() / w[ok].sum())
    return out

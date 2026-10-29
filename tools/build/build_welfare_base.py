"""CAPRI's welfare report levels at the calibration point (reports/welfare.gms): the base terms CAPRI adds to each
component's change, per behavioural region (RMS), from CAPRI's own 2030 market data.

CAPRI reports welfare as levels: each component is its change from the calibration point (the integral of the agent's
behavioural function) plus a base value set by a convention (welfare.gms):
  CSSP         + sum_x HCON_x CPRI_x                                         (l. 148-149)
  ProfitProc   + sum_x PROC_x (PROCMARG_x for oilseeds, PPRI_x otherwise), x with an own term in p_hessNQProc
                                                                              (l. 193-196)
  ProfitDairy  + sum_x PROD_x PROCMARG_x, x a dairy product with an own term in p_hessNQDairy   (l. 272-274)
  ProfitAgr    + sum_x PROD_x PPRI_x, x with an own term in p_hessNQSupp, regions without supply models; with the
               SUPREMA land accounts (supremaMrk on, as CAPRI's 2030 reference: EU27 ProfitAgr = MGVA - rents) 100% of
               the revenue for products (XX) and minus 100% for the netputs that are not market products (XX1 not XX:
               the land types, feed energy, other inputs; here the items without an Armington price) (l. 333-340)
  ProfitFeed   - 0.2 sum_x FEED_x ARM1P_x (ARM1P of the region's market region), regions without supply models
               (l. 539-543)
x: CAPRI's products; values in EUR million (x 0.001). The regions with supply models (CAPRI RMSSUP: their ProfitAgr
is the supply models' MGVA less rents, their ProfitFeed none) are the model's: the EU member states and Norway.

Sources: CAPRI's 2030 market calibration (data_market_1730defaulta.csv: Data_CAL PROD, PPRI, PROC, FEED, ARM1P, HCON,
CPRI at CAL), its NQ Hessians (elas_2_1730defaulta.csv: p_hessNQProc, p_hessNQDairy, p_hessNQSupp at CAL) and the
2030 processing margins of its market solution (markmarket_greendeal_1730et_base_1717.txt: PROCMARG at 2030).

Output: capri_data/2017/market/welfare_base_2030.csv  rms, model_region, component, value

    python tools/build/build_welfare_base.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

UP = Path("/mnt/user-data/uploads")
ELAS = UP / "elas_2_1730defaulta.csv"
DATA = UP / "data_market_1730defaulta.csv"
DUMP = UP / "markmarket_greendeal_1730et_base_1717.txt"
OUT = ROOT / "capri_data" / "2017" / "market" / "welfare_base_2030.csv"
#: CAPRI's oilseeds (SED: their processing is priced at the crushing margin)
SED = {"RAPE", "SUNF", "SOYA", "OLIV"}
ITEMS = ("PROD", "PPRI", "PROC", "FEED", "ARM1P", "HCON", "CPRI")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def own_terms(path: Path) -> dict:
    """{parameter: {(rms, x)}}: the own (diagonal) terms of CAPRI's NQ Hessians at CAL."""
    pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    want = {"p_hessNQProc", "p_hessNQDairy", "p_hessNQSupp"}
    out, cur = defaultdict(set), None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur not in want or not line.startswith("'"):
                continue
            m = pat.match(line)
            if m and m.group(2) == m.group(3) and num(m.group(4)) != 0.0:
                out[cur].add((m.group(1), m.group(2)))
    return out


def main():
    own = own_terms(ELAS)
    pat = re.compile(r"^'([^']*)'\.'(" + "|".join(ITEMS) + r")'\.'([A-Za-z0-9_]+)'\.'CAL'\s+(\S+)")
    d = {}
    with open(DATA, encoding="latin-1") as fh:
        cur = None
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur != "Data_CAL" or not line.startswith("'"):
                continue
            m = pat.match(line)
            if m:
                d[(m.group(1), m.group(2), m.group(3))] = num(m.group(4))
    pm = re.compile(r"^'([^']*)'\.''\.'PROCMARG'\.'([A-Za-z0-9_]+)'\.'2030'\s+(\S+)")
    marg = {}
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PROCMARG'" in line:
                m = pm.match(line)
                if m:
                    marg[(m.group(1), m.group(2))] = num(m.group(3))
    g = read_csv(ROOT / "capri_data" / "2017" / "market" / "gl_demand_goods.csv")
    mreg = dict(zip(g.rms, g.model_region))
    r2m = read_csv(ROOT / "capri_data" / "shared" / "rms_to_rm.csv")
    r2m = dict(zip(r2m.rms, r2m.rm))
    units = read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv")
    rmssup = set(units.capri_ms) | {"NO000000"}               # the model's regions with supply models
    xx = {x for (_, it, x) in d if it == "ARM1P"}                 # CAPRI's market products (XX)
    gl = read_csv(ROOT / "capri_data" / "2017" / "market" / "gl_demand_goods.csv")
    val = defaultdict(float)
    # CSSP: the goods of the GL demand system (HCON x CPRI at CAL, gl_demand_goods.csv, built from the same data)
    for r, h, c in gl[["rms", "hcon", "cpri"]].itertuples(index=False):
        val[(r, "CSSP")] += float(h) * float(c) * 0.001
    for (r, it, x), v in d.items():
        if r not in mreg:
            continue
        if it == "PROC" and v and (r, x) in own["p_hessNQProc"]:
            p = marg.get((r, x), 0.0) if x in SED else d.get((r, "PPRI", x), 0.0)
            val[(r, "ProfitProc")] += v * p * 0.001
        if it == "PROD" and v and (r, x) in own["p_hessNQDairy"] and (r, x) in marg:
            val[(r, "ProfitDairy")] += v * marg[(r, x)] * 0.001
        if r in rmssup:
            continue
        if it == "PROD" and v and (r, x) in own["p_hessNQSupp"]:
            sgn = 1.0 if x in xx else -1.0
            val[(r, "ProfitAgr")] += sgn * v * d.get((r, "PPRI", x), 0.0) * 0.001
        if it == "FEED" and v:
            a1 = d.get((r2m.get(r, r), "ARM1P", x), d.get((r, "ARM1P", x), 0.0))
            val[(r, "ProfitFeed")] -= 0.2 * v * a1 * 0.001
    rows = [(r, mreg[r], c, v) for (r, c), v in sorted(val.items())]
    out = pd.DataFrame(rows, columns=["rms", "model_region", "component", "value"])
    to_csv(out, OUT, index=False)
    tot = out.groupby("component").value.sum()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} rows, {out.rms.nunique()} regions; totals (EUR million): "
          + ", ".join(f"{k} {v:,.0f}" for k, v in tot.items()))


if __name__ == "__main__":
    main()

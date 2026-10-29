"""CAPRI's market supply functions of the regions outside the EU (arm/market_model.gms ProdNQ_, l. 1529-1572): the
normalised-quadratic supply of every non-EU CAPRI market region, own and cross-price terms, from CAPRI's own terms
(market audit, programme step D: "non-EU supply in CAPRI's NQ form", KNOWN_ISSUES K54-3).

ProdNQ_: v_prodQuant(RMS, x) = p_cnstNQSupp + sum_y p_hessNQSupp(RMS, x, y) x v_prodPrice(RMS, y) / v_prodPrice(RMS,
"INPE") (+ the feed-bulk price terms, which CAPRI's 2030 Hessian does not carry for any region). The change from the
calibration point is sum_y h_xy x (the change of y's producer price) / INPE. The producer price moves with the market
price by CAPRI's relative margin (PPri_, l. 3046-3060; the support items PSEi, PSEd, AREP are not in CAPRI's 2030
calibration data for these regions, so the margin is the whole price), so the change of y's producer price is
PPRI0_y x (y's price ratio - 1) and each term is written as h_xy x PPRI0_y / INPE: kt per unit change of y's price
ratio, the form of the EU's other oils and fish (build_eu_market_supply_nq.py) and of the market supply Hessian.
INPE is the price of the non-agricultural good in 2030 (1.2772 in every region, CAPRI's 2030 market dump, as
build_eu_market_supply_nq.py takes it); it does not move in a simulation.

Columns kept: the prices the model has for the region: its market products (the bilateral market's product map,
build_bilateral_market.MODEL) and raw milk (the region's dairy block, capri_mod/market/dairy.py). Columns written with
the model code empty and held at their calibration value by the market (registered, docs/DEPARTURES_FROM_CAPRI.md):
the feed energy price FEDE (CAPRI's FeedBal_ of the non-EU regions, market audit M3, not built; no FEDE price in
CAPRI's calibration data, so these terms are written with h_ratio 0) and the rents of the land inputs of CAPRI's
market land use (TCRP land for temporary crops, FRUN for permanent crops, FODFAL fodder and fallow: xx1Land,
arm/arm_sets.gms l. 140-150; the model has no land market outside the EU's supply models). The young animals carry
only a placeholder own term (1) in CAPRI's export, no cross terms. Rows: every model market product and raw milk;
the input rows (FEDE, the land types) and the young animals are left out.

The Hessian is completed as CAPRI's market model completes it on loading (tools/lib/_capri_nq.py, arm/market1.gms
l. 539-574): tiny cross terms deleted, products without ProdNQ_ deleted (for the regions with supply models in CAPRI,
here Norway, the UK, Turkey and the Western Balkans, also FPRI, FENI, FEDE), and made symmetric (the export stores
each cross term once, under one of the two products).

For the UK, Turkey and the Western Balkans CAPRI's supply is its supply models' (RMSSUP), the market's function being
recalibrated to them each iteration; the model has no supply models there (a registered difference), so their
function stays at CAPRI's calibration point, as for the regions without supply models.

Sources: CAPRI's NQ supply Hessian at the calibration point (elas_2_1730defaulta.csv: p_hessNQSupp at CAL), the
regions' producer prices and production there (data_market_1730defaulta.csv: Data_CAL PPRI, PROD at CAL), the 2030
price of the non-agricultural good (markmarket_greendeal_1730et_base_1717.txt: PPRI INPE 2030), CAPRI's market
regions (capri_data/shared/rms_to_rm.csv) and the model's trade regions (recalibrate_trade_2017.REGION_MAP, others
ROW).

Output: capri_data/2017/market/noneu_market_supply_nq.csv
    trade_region, rms, x, y, capri_x, capri_y, h, ppri_y, inpe, h_ratio      (x, y model codes; y empty: held)

    python tools/build/build_noneu_market_supply_nq.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

from _capri_nq import read_supply_hessian  # noqa: E402

UP = Path("/mnt/user-data/uploads")
ELAS = UP / "elas_2_1730defaulta.csv"
DATA = UP / "data_market_1730defaulta.csv"
DUMP = UP / "markmarket_greendeal_1730et_base_1717.txt"
RMS_TO_RM = ROOT / "capri_data" / "shared" / "rms_to_rm.csv"
UNITS = ROOT / "capri_data" / "sources" / "capri_res" / "gd2030_endotech_ini_nbalance.csv"
OUT = ROOT / "capri_data" / "2017" / "market" / "noneu_market_supply_nq.csv"
#: CAPRI's EU market regions (trade blocks): their member states' supply is the supply models'
EU_RM = ("A_EU_WEST", "A_EU_EAST", "EU27yr19")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def read_param(path: Path, name: str, pat: re.Pattern, keep) -> list:
    out, cur = [], None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur != name or not line.startswith("'"):
                continue
            m = pat.match(line)
            if m and keep(m):
                out.append(m.groups())
    return out


def main():
    from recalibrate_trade_2017 import REGION_MAP
    from build_bilateral_market import CAPRI as CAPRI_TO_MODEL       # CAPRI product -> model commodity
    to_model = dict(CAPRI_TO_MODEL)
    to_model["MILK"] = "MILK"                                        # raw milk: the region's dairy block
    rm_of = dict(read_csv(RMS_TO_RM)[["rms", "rm"]].itertuples(index=False))
    noneu = {r for r, m in rm_of.items() if m not in EU_RM}

    # CAPRI's regions with supply models (RMSSUP) outside the EU: the countries of its supply-model units in the Green
    # Deal 2030 run (Norway, the UK, Turkey, the Western Balkans; Turkey's units TR..., its market region TUR)
    ctry = {str(u)[:2] for u in read_csv(UNITS)["region"].unique()}
    rmssup = {r for r in noneu if (r.endswith("000000") and r[:2] in ctry) or (r == "TUR" and "TR" in ctry)}
    hess = read_supply_hessian(ELAS, lambda r: r in noneu, rmssup)
    terms = sorted((r, x, y, h) for (r, x, y), h in hess.items() if x in to_model and y != "INPE")
    ep = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    elas = {(r, x, y): num(v) for r, x, y, v in read_param(ELAS, "p_elasSupp", ep, lambda m: m.group(1) in noneu)}
    stored = {(r, x, y) for r, x, y, _ in read_param(ELAS, "p_hessNQSupp", ep, lambda m: m.group(1) in noneu)}
    dp = re.compile(r"^'([^']*)'\.'(PPRI|PROD)'\.'([^']*)'\.'CAL'\s+(\S+)")
    data = {(r, it, p): num(v) for r, it, p, v in read_param(DATA, "Data_CAL", dp, lambda m: m.group(1) in noneu)}
    inpe = {}
    p3 = re.compile(r"^'([^']+)'\.''\.'PPRI'\.'INPE'\.'2030'\s+(\S+)")
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PPRI'.'INPE'" in line:
                m = p3.match(line)
                if m:
                    inpe[m.group(1)] = num(m.group(2))

    rows, missing = [], set()
    held = defaultdict(float)
    for r, x, y, h in terms:
        if not inpe.get(r):
            missing.add((r, "INPE 2030"))
            continue
        p = data.get((r, "PPRI", y), 0.0)
        if not p:
            # a price CAPRI's calibration data does not carry for the region (FEDE: the feed energy balance's
            # shadow price; young animals priced at RM level): such a column is held, its term not usable
            held[y] += 0.0
            rows.append((REGION_MAP.get(rm_of[r], "ROW"), r, to_model[x], "", x, y, h, 0.0, inpe[r], 0.0))
            continue
        ym = to_model.get(y, "")
        rows.append((REGION_MAP.get(rm_of[r], "ROW"), r, to_model[x], ym, x, y, h, p, inpe[r], h * p / inpe[r]))
        if not ym:
            held[y] += abs(h * p / inpe[r])
    if missing:
        raise SystemExit(f"no CAPRI 2030 INPE for {sorted(missing)[:10]}")
    out = pd.DataFrame(rows, columns=["trade_region", "rms", "x", "y", "capri_x", "capri_y", "h", "ppri_y", "inpe",
                                      "h_ratio"]).sort_values(["trade_region", "rms", "x", "capri_y"])
    to_csv(out, OUT, index=False)

    # checks: the terms give CAPRI's p_elasSupp at the calibration point (h x PPRI_y / INPE / PROD_x, CAPRI's elasticity definition)
    worst, n = 0.0, 0
    for t in out.itertuples(index=False):
        if (t.rms, t.capri_x, t.capri_y) not in stored:
            continue                                       # a term completed from its transpose (_capri_nq step 3)
        e = elas.get((t.rms, t.capri_x, t.capri_y))
        q = data.get((t.rms, "PROD", t.capri_x), 0.0)
        if e is None or not q > 0 or not t.ppri_y:
            continue
        n += 1
        worst = max(worst, abs(t.h_ratio / q - e) / max(abs(e), 1e-3))
    used = out[out.y != ""]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} terms, {out.rms.nunique()} CAPRI regions, "
          f"{out.trade_region.nunique()} trade regions; {len(used)} on model prices "
          f"({int((used.x == used.y).sum())} own-price, {int((used.x != used.y).sum())} cross)")
    print(f"  p_elasSupp reproduced on {n} terms: worst relative deviation {worst:.2e}")
    tot = float(out.h_ratio.abs().sum())
    print("  held at calibration (no model price): " + ", ".join(
        f"{y} {v / tot:.2%}" for y, v in sorted(held.items(), key=lambda kv: -kv[1]) if v > 0)
          + f"; without a CAPRI price: {sorted(y for y, v in held.items() if v == 0.0)}")


if __name__ == "__main__":
    main()

"""CAPRI's non-EU feed demand functions FeedNQ_ (audit M3): p_hessNQFeed at the 2030 calibration point, with the feed
energy price FEDE, per behavioural region without supply models.

CAPRI (arm/market_model.gms l. 1032-1047), for a region r outside the regions with supply models and a product x it
feeds (DATA(r, "Feed", x, CAL) > 0):

    feed_x = cnst_x + sum_y h_xy * (arm1P_y - FSEi_y) / INPE  +  h_x,FEDE * FEDE / INPE

y the products with an Arm1 price in r's market region and FEDE, the region's feed energy price (paired with FeedBal_,
tools/build/build_feed_energy.py); the Hessian completed on loading as arm/market1.gms (tools/lib/_capri_nq.py
read_feed_hessian: tiny cross terms deleted, symmetric). In the model's ratio form, with base prices p0 and the price
ratios rho of the region's market:

    feed_x = feed0_x + sum_y h_ratio_xy * (rho_y - 1),     h_ratio = h * p0_y / INPE

p0_y: CAPRI's ARM1P of the market region at CAL (FSEi: 0, the file has none), for FEDE the region's FEDE price at CAL
(noneu_feed_energy.csv); INPE 1.019^13, the market's non-agricultural price index in 2030 (as
build_noneu_market_supply_nq.py). Check: the terms reproduce CAPRI's p_ElasFeed (h x p0_y / INPE / feed0_x) on every
stored product term; the FEDE column's p_ElasFeed equals h x FEDE / feed0 without the INPE (CAPRI's elasticity
calibration normalises FEDE by the region's PPri INPE, 1 in its data, arm/trim_elas.gms l. 950), while FeedNQ_ divides
by the market region's INPE: the market's response to FEDE is CAPRI's equation's, so 1 / INPE of the calibrated
elasticity (REGISTERED as CAPRI's own).

Outputs (capri_data/2017/market):
  noneu_feed_nq.csv    trade_region, rms, x, y, capri_x, capri_y, h, p0_y, inpe, h_ratio   (x, y model codes; y FEDE,
                       or empty for a price the model does not have: held)
  noneu_feed_base.csv  trade_region, rms, capri_x, x, feed_kt, kcal_per_kg   (every product the region feeds at CAL)
  noneu_feed_totals.csv trade_region, x, feed_kt   (CAPRI's feed at CAL of all the trade region's non-EU behavioural
                       regions per model commodity, the members with supply models included: the base the regions'
                       feed changes are relative to)

    python tools/build/build_noneu_feed_nq.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _capri_nq import read_feed_hessian  # noqa: E402
from build_noneu_market_supply_nq import DATA, ELAS, num, read_param  # noqa: E402

OUT = ROOT / "capri_data" / "2017" / "market"
INPE = 1.019 ** 13


def main() -> None:
    from recalibrate_trade_2017 import REGION_MAP
    from build_bilateral_market import CAPRI as CAPRI_TO_MODEL
    to_model = dict(CAPRI_TO_MODEL)
    with open(OUT / "noneu_feed_energy.csv", newline="") as f:
        fe = {r["rms"]: r for r in csv.DictReader(f)}
    with open(OUT / "feed_cal_content.csv", newline="") as f:
        cal = {r["product"]: float(r["kcal_per_kg"]) for r in csv.DictReader(f)}
    regs = set(fe)
    rms_rm = {r: fe[r]["rm"] for r in regs}
    keep = regs | set(rms_rm.values())
    pat = re.compile(r"^'([^']*)'\.'(FEED|ARM1P)'\.'([^']*)'\.'CAL'\s+(\S+)")
    data = {(r, it, p): num(v) for r, it, p, v in read_param(DATA, "Data_CAL", pat, lambda m: m.group(1) in keep)}
    hess = read_feed_hessian(ELAS, lambda r: r in regs)
    # every non-EU behavioural region's feed at CAL, for the trade regions' totals (the members with supply models in
    # CAPRI, outside FeedBal_'s domain, included: their feed is held)
    with open(ROOT / "capri_data" / "shared" / "rms_to_rm.csv", newline="") as f:
        rm_all = {r["rms"]: r["rm"] for r in csv.DictReader(f)}
    from build_noneu_market_supply_nq import EU_RM
    noneu_all = {r for r, m in rm_all.items() if m not in EU_RM}
    fpat = re.compile(r"^'([^']*)'\.'(FEED)'\.'([^']*)'\.'CAL'\s+(\S+)")
    tot = {}
    for r, _, x, v in read_param(DATA, "Data_CAL", fpat, lambda m: m.group(1) in noneu_all):
        xm = to_model.get(x, "")
        q = num(v)
        if xm and q > 0:
            k = (REGION_MAP.get(rm_all[r], "ROW"), xm)
            tot[k] = tot.get(k, 0.0) + q
    ep = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    elas = {(r, x, y): num(v) for r, x, y, v in read_param(ELAS, "p_ElasFeed", ep, lambda m: m.group(1) in regs)}
    stored = {(r, x, y) for r, x, y, _ in read_param(ELAS, "p_hessNQFeed", ep, lambda m: m.group(1) in regs)}

    rows, base = [], []
    for r in sorted(regs):
        rm = rms_rm[r]
        tr = REGION_MAP.get(rm, "ROW")
        feed0 = {x: data[(r, "FEED", x)] for (rr, it, x) in data if rr == r and it == "FEED" and data[(r, "FEED", x)] > 0}
        for x in sorted(feed0):
            base.append((tr, r, x, to_model.get(x, ""), repr(feed0[x]), repr(cal.get(x, 0.0))))
        for (rr, x, y), h in sorted(hess.items()):
            if rr != r or x not in feed0 or y == "INPE":
                continue                                       # INPE: the numeraire, fixed (no change)
            if y == "FEDE":
                p0, ym = float(fe[r]["fede_price"]), "FEDE"
            else:
                p0 = data.get((rm, "ARM1P", y), 0.0)
                if not p0:
                    continue                                   # FeedNQ_ sums over the products with an Arm1 price
                ym = to_model.get(y, "")
            rows.append((tr, r, to_model.get(x, ""), ym, x, y, repr(h), repr(p0), repr(INPE), repr(h * p0 / INPE)))
    with open(OUT / "noneu_feed_nq.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["trade_region", "rms", "x", "y", "capri_x", "capri_y", "h", "p0_y", "inpe", "h_ratio"])
        w.writerows(rows)
    with open(OUT / "noneu_feed_totals.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["trade_region", "x", "feed_kt"])
        w.writerows((tr, x, repr(q)) for (tr, x), q in sorted(tot.items()))
    with open(OUT / "noneu_feed_base.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["trade_region", "rms", "capri_x", "x", "feed_kt", "kcal_per_kg"])
        w.writerows(base)

    # check: CAPRI's p_ElasFeed on the stored terms
    worst, n, fede = 0.0, 0, []
    for t in rows:
        r, x, y = t[1], t[4], t[5]
        if (r, x, y) not in stored or (r, x, y) not in elas:
            continue
        q = data.get((r, "FEED", x), 0.0)
        e = elas[(r, x, y)]
        if y == "FEDE":
            fede.append(float(t[9]) * INPE / q / e if e else 1.0)
            continue
        n += 1
        worst = max(worst, abs(float(t[9]) / q - e) / max(abs(e), 1e-3))
    held = sum(1 for t in rows if t[3] == "")
    print(f"noneu_feed_nq.csv: {len(rows)} terms, {len(regs)} regions ({held} on prices the model does not have); "
          f"noneu_feed_base.csv: {len(base)} feed products")
    print(f"  p_ElasFeed reproduced on {n} product terms: worst relative deviation {worst:.2e}; FEDE terms "
          f"(elasticity x INPE): ratio {min(fede):.8f} to {max(fede):.8f} over {len(fede)}")


if __name__ == "__main__":
    main()

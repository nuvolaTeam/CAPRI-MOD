"""CAPRI's non-EU feed demand per model trade region: the feed share of use and the feed-price elasticities.

CAPRI (arm/market_model.gms FeedNQ_): every non-EU behavioural region (RMS) has feed demand per product from its
normalised quadratic feed cost function, calibrated to p_ElasFeed(RMS, feed, price-of). The model's market has one
row per trade region; a trade region is one CAPRI region (USA, CHN, ...) or an aggregate of several (ROW, and the
regions the model groups), so each region gets:

  feed share    sum FEED / sum (HCON + FEED + PROC + BIOF) over its CAPRI regions, CAPRI's 2030 calibration
                (data_market_1730defaulta, CAL) - the same data and use categories as the GL food demand
                (gl_demand_*), the processing functions (processing_nq_*) and the biofuel feedstocks, so that the
                four blocks together hold the region's whole use (CAPRI has no other use in arm1: armBal_)
  elasticities  p_ElasFeed(RMS, feed, price-of, 'CAL') from elas_2_1730defaulta (same vintage), for every product
                CAPRI gives a feed function that the model trades (cereals, cakes, oilseeds, pulses, potatoes, fish
                and dairy products fed, ...); for an aggregate the feed-weighted mean over its CAPRI regions

Before 19 October 2026 the shares came from FAO_agg 2017 (FEDM/DOMM) and the elasticities from elas_2_1717, and only
for trade regions identical to one CAPRI region: ROW, Turkey, South Korea, Morocco and New Zealand had no feed
function, and their feed use (e.g. 96% of ROW's soybean cake) fell on the generic own-price response (eta).

CAPRI region -> trade region: tools/build/recalibrate_trade_2017.py REGION_MAP (as tools/build/build_processing_nq.py), over
CAPRI's 80 behavioural regions; EU member states are left out (EU feed comes from the supply models' feed bulks,
tools/build/build_feed_bulks.py). Norway (trade region NOR since KNOWN_ISSUES K56) has no p_ElasFeed either: its feed
comes from its supply models through its bulks (feed_bulks_no.csv), as CAPRI's. REGISTERED: CAPRI's other
supply-model regions (United Kingdom, the Western Balkans, Turkey) have no p_ElasFeed - their feed comes from CAPRI's
supply models, which capri-mod does not have for them: in ROW their feed counts in the feed share and follows the
elasticities of ROW's other regions; Turkey, a trade region of its own, keeps the generic own-price response.

Output: capri_data/2017/market/feed_demand_nonEU.json {"_source", "parameters": {"REGION|COMM": {feed_share,
elasticities}}}; source extracts capri_data/sources/market/feed_demand_nonEU_{elas,use}_2030.csv.

    python tools/build/build_feed_demand_nonEU.py
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KEEP_E = ROOT / "capri_data" / "sources" / "market" / "feed_demand_nonEU_elas_2030.csv"
KEEP_U = ROOT / "capri_data" / "sources" / "market" / "feed_demand_nonEU_use_2030.csv"
DEST = ROOT / "capri_data" / "2017" / "market" / "feed_demand_nonEU.json"
USES = ("HCON", "FEED", "PROC", "BIOF")
EU = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
      "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elas", type=Path, default=Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv"))
    ap.add_argument("--data", type=Path, default=Path("/mnt/user-data/uploads/data_market_1730defaulta.csv"))
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from capri_mod.data.definitions import ALL_TRADE_REGIONS
    from recalibrate_trade_2017 import REGION_MAP
    import build_bilateral_market as BM
    # every CAPRI market product the model trades (tools/build/build_bilateral_market.py MODEL: model -> CAPRI products)
    g2m = {g: m for m, gs in BM.MODEL.items() for g in gs}
    caps = set(g2m)
    if a.elas.exists():
        rows, cur = [], None
        pat = re.compile(r"^'([^']+)'\.'([A-Z]+)'\.'([A-Z]+)'\.'CAL'\s+([-\d.Ee+]+)")
        for line in open(a.elas, encoding="latin-1"):
            if line.startswith("Parameter"):
                if cur == "p_ElasFeed":
                    break
                cur = line.split("(")[0].split()[1]
                continue
            if cur != "p_ElasFeed":
                continue
            m = pat.match(line)
            if m and m.group(2) in caps and m.group(3) in caps:
                rows.append(dict(rms=m.group(1), feed=m.group(2), price_of=m.group(3), value=float(m.group(4))))
        pd.DataFrame(rows).to_csv(KEEP_E, index=False, float_format="%.12g")
        print(f"extracted {len(rows)} p_ElasFeed rows -> {KEEP_E.relative_to(ROOT)}")
    if a.data.exists():
        rows = []
        pat = re.compile(r"^'([^']+)'\.'(" + "|".join(USES) + r")'\.'([A-Z]+)'\.'CAL'\s+([-\d.Ee+]+)")
        for line in open(a.data, encoding="latin-1"):
            m = pat.match(line)
            if m and m.group(3) in caps:
                rows.append(dict(rms=m.group(1), item=m.group(2), product=m.group(3), value=float(m.group(4))))
        pd.DataFrame(rows).to_csv(KEEP_U, index=False, float_format="%.12g")
        print(f"extracted {len(rows)} use rows -> {KEEP_U.relative_to(ROOT)}")
    el = pd.read_csv(KEEP_E)
    us = pd.read_csv(KEEP_U)
    # CAPRI's behavioural regions (RMS: the 80 regions of its processing functions, the same elasticity export);
    # the data also hold trade blocks and reporting sums of them (A_EU_*, EU, MED, MER, MER_OTH, URUPAR, WBA)
    beh = set(pd.read_csv(ROOT / "capri_data" / "2017" / "market" / "processing_nq_base.csv").rms)
    rms_set = set(el.rms)
    is_eu = lambda r: r[:2] in EU and r.endswith("000000")
    mreg = lambda r: REGION_MAP.get(r, "ROW")
    # CAPRI products -> model commodities (several CAPRI products of one commodity: quantities add up, the price
    # columns of one commodity's products add up - one price - and the rows are weighted by their feed below)
    E = defaultdict(lambda: defaultdict(float))
    U = defaultdict(float)
    for r in us.itertuples(index=False):
        if r.product in g2m:
            U[(r.rms, r.item, g2m[r.product])] += float(r.value)
    Fp = defaultdict(float)
    for r in us.itertuples(index=False):
        if r.item == "FEED" and r.product in g2m:
            Fp[(r.rms, r.product)] += float(r.value)
    wrow = defaultdict(float)
    for r in el.itertuples(index=False):
        if r.feed in g2m and r.price_of in g2m:
            w = Fp.get((r.rms, r.feed), 0.0)
            E[(r.rms, g2m[r.feed])][g2m[r.price_of]] += w * float(r.value)
    for r in el.drop_duplicates(["rms", "feed"]).itertuples(index=False):
        if r.feed in g2m:
            wrow[(r.rms, g2m[r.feed])] += Fp.get((r.rms, r.feed), 0.0)
    for k, d in E.items():
        if wrow.get(k, 0.0) > 0:
            for c2 in d:
                d[c2] /= wrow[k]
    FEEDS = sorted({g2m[p] for p in set(el.feed) if p in g2m})
    trade = set(ALL_TRADE_REGIONS) - {"EU27"}
    feed, use, wel = defaultdict(float), defaultdict(float), defaultdict(lambda: defaultdict(float))
    members = defaultdict(set)
    for rms in sorted(beh):
        if is_eu(rms):
            continue
        R = mreg(rms)
        if R not in trade:
            continue
        for c in FEEDS:
            f = U.get((rms, "FEED", c), 0.0)
            u = sum(U.get((rms, x, c), 0.0) for x in USES)
            if u <= 0:
                continue
            use[(R, c)] += u
            feed[(R, c)] += f
            e = E.get((rms, c))
            if f > 0 and e and c in e and wrow.get((rms, c), 0.0) > 0:
                members[(R, c)].add(rms)
                for c2, v in e.items():
                    wel[(R, c)][c2] += f * v
    params = {}
    for (R, c), u in sorted(use.items()):
        f = feed[(R, c)]
        if f <= 0 or not members[(R, c)]:
            continue
        fe = sum(U.get((rm, "FEED", c), 0.0) for rm in members[(R, c)])
        params[f"{R}|{c}"] = {"feed_share": round(f / u, 4),
                              "elasticities": {c2: round(v / fe, 4) for c2, v in wel[(R, c)].items()},
                              "capri_regions": sorted(members[(R, c)])}
    src = ("CAPRI 2030 calibration: feed share = sum FEED / sum (HCON + FEED + PROC + BIOF) over the trade region's "
           "CAPRI regions (data_market_1730defaulta CAL); elasticities = p_ElasFeed(RMS, feed, price-of, 'CAL') from "
           "elas_2_1730defaulta, feed-weighted over the CAPRI regions of an aggregate, every product with a CAPRI feed "
           "function that the model trades (CAPRI -> model products: tools/build/build_bilateral_market.py MODEL). Non-EU regions only: EU feed comes from the supply models' feed "
           "bulks (tools/build/build_feed_bulks.py). tools/build/build_feed_demand_nonEU.py")
    json.dump({"_source": src, "parameters": params}, open(DEST, "w"), indent=1)
    regs = sorted({k.split("|")[0] for k in params})
    print(f"wrote {DEST.relative_to(ROOT)}: {len(params)} entries, {len(regs)} regions {regs}")
    miss = sorted(trade - set(regs))
    print(f"trade regions without a feed function: {miss}")


if __name__ == "__main__":
    main()

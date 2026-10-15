"""CAPRI's feed demand of the non-EU regions (arm/market_model.gms FeedNQ_, as elasticities p_ElasFeed).

Outside the EU CAPRI has no supply models; each region's feed demand is a normalised quadratic function of the
feed prices, calibrated to CAPRI's feed elasticities p_ElasFeed(region, feed, price of). The model uses those
elasticities in constant-elasticity form for the feed part of each region's use (MarketModule.demand_response):

  feed_c = feed_c0 x prod_j (P_j / P_j0)^p_ElasFeed(r, c, j)       over the model's feed commodities j

Sources:
  elasticities  elas_2_1717defaulta p_ElasFeed(r, c, j, 'CAL'), restricted to the model's feed commodities
                (WHEA -> SWHE, MAIZ -> CORN, OCER -> OCER, BARL, RAPC, SUNC, SOYC, DDGS); the other-cereals column
                is CAPRI's OCER cross-elasticity (rye and oats are separate CAPRI products), rounded to 4 decimals
  feed share    FEDM / DOMM of the product group (FAO_agg_17_defaulta p_dataMarket BAS; other cereals include rye
                and oats); DDGS: 1 (all DDGS use is feed in CAPRI, FEED = DOMM; FAO_agg has no DDGS balance)
  regions       the model's non-EU trade regions whose CAPRI region (same code, or INDO, JAP, THAI, VIET) has
                p_ElasFeed and FAO_agg feed use

DDGS (Sprint 9d): the ethanol by-product is a market commodity now; its own row (feed share 1) and its column in
the other rows (e.g. USA maize +0.12 to the DDGS price) come from the same p_ElasFeed. For the regions without a
CAPRI row (ROW and the regions not listed) the market's generic demand applies, with DDGS's own-price elasticity
in armington_params.csv set to the mean of CAPRI's own-price p_ElasFeed of DDGS over the CAPRI regions that
are not listed (written by this builder).

Output: capri_data/2017/market/feed_demand_nonEU.json {"_source", "parameters": {"REGION|COMM": {feed_share,
elasticities}}}; source extracts capri_data/sources/market/feed_demand_nonEU_{elas,fao}_2017.csv.

    python tools/build_feed_demand_nonEU.py
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEEP_E = ROOT / "capri_data" / "sources" / "market" / "feed_demand_nonEU_elas_2017.csv"
KEEP_F = ROOT / "capri_data" / "sources" / "market" / "feed_demand_nonEU_fao_2017.csv"
DEST = ROOT / "capri_data" / "2017" / "market" / "feed_demand_nonEU.json"
ARM = ROOT / "capri_data" / "2017" / "market" / "armington_params.csv"
FEEDS = {"SWHE": "WHEA", "BARL": "BARL", "CORN": "MAIZ", "OCER": "OCER", "RAPC": "RAPC", "SUNC": "SUNC",
         "SOYC": "SOYC", "DDGS": "DDGS",
         # Sprint 9h: the residual feeds, market products now
         "FENI": "FENI", "FPRI": "FPRI"}
GROUP = {"SWHE": ("WHEA",), "BARL": ("BARL",), "CORN": ("MAIZ",), "OCER": ("OCER", "RYEM", "OATS"),
         "RAPC": ("RAPC",), "SUNC": ("SUNC",), "SOYC": ("SOYC",), "FENI": ("FENI",), "FPRI": ("FPRI",)}
CODE = {"IDN": "INDO", "JPN": "JAP", "THA": "THAI", "VNM": "VIET"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elas", type=Path, default=Path("/mnt/user-data/uploads/elas_2_1717defaulta.csv"))
    ap.add_argument("--fao", type=Path, default=Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt"))
    ap.add_argument("--regions", default="", help="comma list of model regions (default: every non-EU trade region)")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.definitions import ALL_TRADE_REGIONS
    caps = set(FEEDS.values()) | {"RYEM", "OATS"}
    if a.elas.exists():
        txt = open(a.elas, errors="ignore").read()
        i = txt.index("Parameter p_ElasFeed")
        j = txt.index("Parameter ", i + 10)
        pat = re.compile(r"^'([^']+)'\.'([A-Z]+)'\.'([A-Z]+)'\.'CAL'\s+([-\d.Ee+]+)", re.M)
        rows = [dict(region=m.group(1), feed=m.group(2), price_of=m.group(3), value=float(m.group(4)))
                for m in pat.finditer(txt[i:j]) if m.group(2) in caps and m.group(3) in caps]
        pd.DataFrame(rows).to_csv(KEEP_E, index=False, float_format="%.12g")
        print(f"extracted {len(rows)} p_ElasFeed rows -> {KEEP_E.relative_to(ROOT)}")
    if a.fao.exists():
        out = subprocess.run(["grep", "-E", r"^'[^']+'\.'(FEDM|DOMM)'\.'(" + "|".join(sorted(caps)) + r")'\.'BAS'",
                              str(a.fao)], capture_output=True, text=True).stdout
        pat = re.compile(r"^'([^']+)'\.'(FEDM|DOMM)'\.'([A-Z]+)'\.'BAS'\s+([-\d.Ee+]+)")
        rows = [dict(region=m.group(1), item=m.group(2), product=m.group(3), value=float(m.group(4)))
                for m in map(pat.match, out.splitlines()) if m]
        pd.DataFrame(rows).to_csv(KEEP_F, index=False, float_format="%.12g")
        print(f"extracted {len(rows)} FAO_agg rows -> {KEEP_F.relative_to(ROOT)}")
    el = pd.read_csv(KEEP_E)
    E = {}
    for r in el.itertuples(index=False):
        E.setdefault((r.region, r.feed), {})[r.price_of] = float(r.value)
    fa = pd.read_csv(KEEP_F)
    F = {(r.region, r.item, r.product): float(r.value) for r in fa.itertuples(index=False)}
    regs = [r for r in (a.regions.split(",") if a.regions else ALL_TRADE_REGIONS) if r and r != "EU27"]
    params, listed = {}, set()
    for r in regs:
        cr = CODE.get(r, r)
        for c, row in FEEDS.items():
            e = E.get((cr, row))
            if not e or row not in e:
                continue
            if c == "DDGS":
                share = 1.0
            else:
                fed = sum(F.get((cr, "FEDM", p), 0.0) for p in GROUP[c])
                dom = sum(F.get((cr, "DOMM", p), 0.0) for p in GROUP[c])
                if not (fed > 0 and dom > 0):
                    continue
                share = fed / dom
            el_ = {c2: round(e[r2], 4) for c2, r2 in FEEDS.items() if r2 in e}
            params[f"{r}|{c}"] = {"feed_share": round(share, 4), "elasticities": el_}
            listed.add(cr)
    src = ("CAPRI: feed share = FEDM/DOMM (FAO_agg_17_defaulta p_dataMarket BAS; other cereals incl. rye and oats; "
           "DDGS 1); elasticities = p_ElasFeed(r, feed, price-of, 'CAL') from elas_2_1717defaulta, restricted to the "
           "model's feed commodities (WHEA->SWHE, MAIZ->CORN, DDGS). NON-EU regions only: in CAPRI, EU feed demand "
           "comes from the supply models' feed bulks (tools/build_feed_bulks.py). tools/build_feed_demand_nonEU.py")
    json.dump({"_source": src, "parameters": params}, open(DEST, "w"), indent=1)
    # DDGS own-price elasticity for the regions without a CAPRI row (generic demand): the mean of CAPRI's own-price
    # p_ElasFeed of DDGS over the CAPRI regions not listed above
    # (Sprint 9h: the same for the residual feeds FENI and FPRI)
    arm = pd.read_csv(ARM, index_col=0)
    for c_ in ("DDGS", "FENI", "FPRI"):
        rest = [e[c_] for (cr, row), e in E.items() if row == c_ and c_ in e and cr not in listed]
        eta = sum(rest) / len(rest) if rest else 0.0
        if c_ in arm.index:
            arm.at[c_, "eta"] = round(eta, 4)
        print(f"{c_} own-price elasticity for the other regions: {eta:.4f} (mean over {len(rest)} CAPRI regions)")
    arm.to_csv(ARM)
    print(f"wrote {DEST.relative_to(ROOT)}: {len(params)} entries, regions {sorted({k.split('|')[0] for k in params})}")


if __name__ == "__main__":
    main()

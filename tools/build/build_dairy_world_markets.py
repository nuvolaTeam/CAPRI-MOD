"""World base balances of the traded dairy products from CAPRI's FAO_agg (dairy processing, Stage 2).

The market's world dairy-product balances were not CAPRI's: butter, skimmed milk powder and whey powder
never matched CAPRI's codes (BUTT, SMIP, WHEP), so every non-EU region got an invented share of a
hard-coded world total (skimmed milk powder 8,000 kt, whey 15,000 kt); cheese came from a FAO item that
is not cheese (USA 28 kt, CAPRI 5,889 kt; world 3,378 kt with the EU at 80%). With the dairy block the
EU's product supply moves, and a world market in which the EU is four fifths of world cheese turned an
EU supply cut into a world price jump.

This builder takes CAPRI's own base-period balances (FAO_agg p_dataMarket, year BAS: MAPR production,
DOMM domestic use, IMPT, EXPT) for every CAPRI behavioural region, maps them to the model's trade regions
(the same concordance as tools/build/recalibrate_trade_2017.py; regions the model does not separate fold into
ROW; EU member states, the UK and other European countries outside EU27 are skipped / fold into ROW as
there), and converts tonnes to kt.

Output: capri_data/2017/market/dairy_world_baseline.json  {"REGION|COMM": {production, consumption,
imports, exports}} for BUTR, SKIM, CHES, WHEY, FRMI, CREM, COCM, WMIO, CASE (model codes); EU27 is listed for reference only (the
market takes the EU from the dairy block).

    python tools/build/build_dairy_world_markets.py [--src /mnt/user-data/uploads/fao_agg_17_datamarket.txt]
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_KEEP = ROOT / "capri_data" / "sources" / "fao_agg_2017" / "fao_agg_dairy_products_bas.csv"
COMM = {"BUTT": "BUTR", "SMIP": "SKIM", "CHES": "CHES", "WHEP": "WHEY",
        # Sprint 9f: CAPRI's other dairy products, traded bilaterally as in CAPRI (model codes = CAPRI codes)
        "FRMI": "FRMI", "CREM": "CREM", "COCM": "COCM", "WMIO": "WMIO", "CASE": "CASE"}
ITEMS = {"MAPR": "production", "DOMM": "consumption", "IMPT": "imports", "EXPT": "exports"}
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS as _EU_FROM_DATA  # noqa: E402  (capri_data/shared/eu_market_blocks.csv)
EU_MS = set(_EU_FROM_DATA)                                  # CAPRI's EU member states, from the data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt"))
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from recalibrate_trade_2017 import AGGREGATES, trade_region
    pat = re.compile(r"^'([^']+)'\.'(" + "|".join(ITEMS) + r")'\.'(" + "|".join(COMM) + r")'\.'BAS'\s+([-\d.Ee+]+)")
    if a.src.exists():
        rows = []
        for line in open(a.src, errors="ignore"):
            m = pat.match(line)
            if m:
                rows.append(m.groups())
        SRC_KEEP.parent.mkdir(parents=True, exist_ok=True)
        with open(SRC_KEEP, "w") as f:
            f.write("region,item,product,tonnes\n")
            for r in rows:
                f.write(",".join(r) + "\n")
        print(f"extracted {len(rows)} rows -> {SRC_KEEP.relative_to(ROOT)}")
    out = defaultdict(lambda: defaultdict(float))
    seen = set()
    for line in open(SRC_KEEP).read().splitlines()[1:]:
        reg, item, prod, t = line.split(",")
        if reg in AGGREGATES or reg.startswith(("EU0", "EU_", "A_EU")) or reg in ("EU27yr19",):
            continue
        tr = "EU27" if reg in EU_MS else trade_region(reg)
        out[f"{tr}|{COMM[prod]}"][ITEMS[item]] += float(t) / 1000.0
        seen.add(reg)
    res = {k: dict(d) for k, d in sorted(out.items())}
    dest = ROOT / "capri_data" / "2017" / "market" / "dairy_world_baseline.json"
    json.dump({"_source": "CAPRI FAO_agg p_dataMarket (fao_agg_17_datamarket), year BAS, items MAPR DOMM IMPT EXPT; "
                          "tools/build/build_dairy_world_markets.py", "_unit": "1000 t", "balances": res},
              open(dest, "w"), indent=1)
    for c in COMM.values():
        w = sum(v.get("production", 0.0) for k, v in res.items() if k.endswith("|" + c))
        eu = res.get(f"EU27|{c}", {}).get("production", 0.0)
        top = sorted(((k.split("|")[0], v.get("production", 0.0)) for k, v in res.items() if k.endswith("|" + c)),
                     key=lambda x: -x[1])[:5]
        print(f"{c}: world {w:9.0f} kt, EU27 {eu:7.0f} ({eu / w:.0%}); top {', '.join(f'{r} {x:.0f}' for r, x in top)}")
    print(f"wrote {dest.relative_to(ROOT)} from {len(seen)} CAPRI regions")


if __name__ == "__main__":
    main()

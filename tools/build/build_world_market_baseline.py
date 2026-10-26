"""World base balances of the market commodities from CAPRI's FAO_agg (one source for every region).

What it replaces (capri_mod/market/market_module.py _calibrate_baseline): every region's base production came
from a mix of a FAO extract (fao_market_baseline.json), CAPRI's FAO_agg extended SUA, and, where neither had the
item under the model's code, an invented allocation (a hard-coded world total split by fixed regional shares).
The mix was not CAPRI's and in places not even the right product:
  - sugar: the primary extract's "SUGR" is sugar CANE (Brazil 715 Mt), so world sugar was 1,768 Mt against
    CAPRI's 168 Mt of sugar, and the EU (16.6 Mt) was 1% of a world market of which it is 10%;
  - pork 171 Mt (CAPRI 120), eggs 126 (84), maize 1,591 (1,136), wine 70 (27): the EU's weight in those world
    markets, which decides how far an EU supply cut moves world prices, was understated by a third to a half;
  - rye and oats had no world market at all (the model's OCER).
CAPRI's market model takes every region's balance from its FAO_agg database (p_dataMarket); this builder takes
CAPRI's base-period balances (year BAS: MAPR production, DOMM domestic use, IMPT, EXPT) for every CAPRI
behavioural region and maps them to the model's trade regions as tools/build/build_dairy_world_markets.py does
(concordance of tools/build/recalibrate_trade_2017.py; aggregates skipped; regions not separated fold into ROW; EU
member states sum to EU27).

Model commodity <- CAPRI products:
  SWHE <- WHEA (CAPRI's world market is wheat; the model's DWHE world market has no CAPRI counterpart and is left
          as it was: REGISTERED), BARL, CORN <- MAIZ, RYEM, OATS, OCER separate as in CAPRI (formerly OCER + RYEM + OATS, the model's other-cereals market
          carries rye and oats, as its supply bridge now does), RAPE, SUNF, SOYA, SUGR <- SUGA (white sugar), POTA,
          PULS, TOMA, OVEG, APPL, OFRU, CITR, WINE <- TWIN, MILK, BEEF, PORK, POUL <- POUM, SHGM <- SGMT, EGGS,
          RAPO, SUNO, SOYO, RAPC, SUNC, SOYC, BUTR <- BUTT, SKIM <- SMIP, CHES, WHEY <- WHEP. Not the residual feeds FENI and FPRI: FAO_agg's
base balances of these are not CAPRI's market balances (world FPRI 2 Mt against CAPRI's EU 27 Mt alone); their
bases are CAPRI's market results (bilateral flows; the EU's production MaprFeed_, tools/build/build_feed_byproducts.py).
Not covered (no CAPRI world balance under a matching product): DWHE, PARI (CAPRI's world market is milled RICE,
the model's is paddy), OOIL, OLIV (CAPRI trades olive oil OLIO). These keep the market's previous base.

Output: capri_data/2017/market/world_market_baseline.json {"balances": {"REGION|COMM": {production,
consumption, imports, exports}}} in 1000 t; EU27 = sum of member states (imports/exports include intra-EU trade,
so only production and consumption are used for the EU).

    python tools/build/build_world_market_baseline.py [--src /mnt/user-data/uploads/fao_agg_17_datamarket.txt]
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_KEEP = ROOT / "capri_data" / "sources" / "fao_agg_2017" / "fao_agg_market_balances_bas.csv"
MODEL = {
    "SWHE": ("WHEA",), "BARL": ("BARL",), "CORN": ("MAIZ",), "OCER": ("OCER",), "RYEM": ("RYEM",), "OATS": ("OATS",),
    "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",), "SUGR": ("SUGA",), "POTA": ("POTA",),
    "PULS": ("PULS",), "TOMA": ("TOMA",), "OVEG": ("OVEG",), "APPL": ("APPL",), "OFRU": ("OFRU",),
    "CITR": ("CITR",), "TAGR": ("TAGR",), "TOBA": ("TOBA",), "TABO": ("TABO",), "TEXT": ("TEXT",), "PLMO": ("PLMO",), "OTHO": ("OTHO",),
    "FFIS": ("FFIS",), "SFIS": ("SFIS",), "OAQU": ("OAQU",), "COFF": ("COFF",), "TEAS": ("TEAS",), "COCO": ("COCO",), "WINE": ("TWIN",), "MILK": ("MILK",), "BEEF": ("BEEF",), "PORK": ("PORK",),
    "POUL": ("POUM",), "SGMT": ("SGMT",), "EGGS": ("EGGS",), "RAPO": ("RAPO",), "SUNO": ("SUNO",),
    "SOYO": ("SOYO",), "RAPC": ("RAPC",), "SUNC": ("SUNC",), "SOYC": ("SOYC",), "BUTR": ("BUTT",),
    "SKIM": ("SMIP",), "CHES": ("CHES",), "WHEY": ("WHEP",),
}
CAPRI = {c: m for m, cs in MODEL.items() for c in cs}
ITEMS = {"MAPR": "production", "DOMM": "consumption", "IMPT": "imports", "EXPT": "exports"}
EU_MS = {"BL000000", "SE000000", "DK000000", "DE000000", "EL000000", "ES000000", "FR000000", "IR000000",
         "IT000000", "NL000000", "AT000000", "PT000000", "FI000000", "CY000000", "EE000000", "LV000000",
         "LT000000", "MT000000", "PL000000", "SK000000", "BG000000", "CZ000000", "HU000000", "SI000000",
         "RO000000", "HR000000"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("/mnt/user-data/uploads/fao_agg_17_datamarket.txt"))
    a = ap.parse_args()
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from recalibrate_trade_2017 import REGION_MAP, AGGREGATES
    if a.src.exists():
        pat = re.compile(r"^'([^']+)'\.'(" + "|".join(ITEMS) + r")'\.'(" + "|".join(CAPRI) + r")'\.'BAS'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, open(a.src, errors="ignore")) if m]
        SRC_KEEP.parent.mkdir(parents=True, exist_ok=True)
        with open(SRC_KEEP, "w") as f:
            f.write("region,item,product,tonnes\n")
            f.writelines(",".join(r) + "\n" for r in rows)
        print(f"extracted {len(rows)} rows -> {SRC_KEEP.relative_to(ROOT)}")
    out = defaultdict(lambda: defaultdict(float))
    seen = set()
    for line in open(SRC_KEEP).read().splitlines()[1:]:
        reg, item, prod, t = line.split(",")
        if reg in AGGREGATES or reg.startswith(("EU0", "EU_", "A_EU")) or reg == "EU27yr19":
            continue
        tr = "EU27" if reg in EU_MS else REGION_MAP.get(reg, "ROW")
        out[f"{tr}|{CAPRI[prod]}"][ITEMS[item]] += float(t) / 1000.0
        seen.add(reg)
    res = {k: {i: round(v, 3) for i, v in d.items()} for k, d in sorted(out.items())}
    dest = ROOT / "capri_data" / "2017" / "market" / "world_market_baseline.json"
    json.dump({"_source": "CAPRI FAO_agg p_dataMarket (fao_agg_17_datamarket), year BAS, items MAPR DOMM IMPT EXPT; "
                          "tools/build/build_world_market_baseline.py",
               "_unit": "1000 t", "_products": {m: list(cs) for m, cs in MODEL.items()}, "balances": res},
              open(dest, "w"), indent=1)
    for m in MODEL:
        w = sum(v.get("production", 0.0) for k, v in res.items() if k.endswith("|" + m))
        eu = res.get(f"EU27|{m}", {}).get("production", 0.0)
        print(f"{m:5s} world {w:10.0f} kt, EU27 {eu:8.0f} ({eu / w if w else 0:.0%})")
    print(f"wrote {dest.relative_to(ROOT)} from {len(seen)} CAPRI regions")


if __name__ == "__main__":
    main()

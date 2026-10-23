"""CAPRI's feed bulks in the market for the member states (arm/market_model.gms feedBlkPrice_, feedShareEqu_).

In CAPRI the supply models demand feed BULKS (FCER cereals, FPRO protein-rich feed, ...; v_feedBlk); the market
splits each bulk of a member state into market products with a CES on the products' Arm1 prices:

  feedBlkPrice_  P_B   = (sum_i dp_i p_i^(1-rho_B))^(1/(1-rho_B))            (bulk price index; to the supply models)
  feedShareEqu_  q_i   = v_feedBlk_B x dp_i x (P_B / p_i)^rho_B               (feed use of product i)

with rho_B = p_rhoFeed (arm/market1.gms, member states: FCER 6, FPRO 6 "more substitutable, especially FPRO
(containing DDGS)") and dp_i calibrated so the reference is reproduced; calibrated at the reference this is
  q_i / q_i0 = (B / B0) x ((P_B / P_B0) / (p_i / p_i0))^rho_B,
  P_B / P_B0 = (sum_i s_i (p_i / p_i0)^(1 - rho_B))^(1 / (1 - rho_B)),  s_i = p_i0 q_i0 / sum_j p_j0 q_j0.
Bulk products (CAPRI FEED_TO_XX = FEED_TO_O within the market products, plus WHEA in FCER): FCER WHEA, RYEM, BARL,
OATS, MAIZ, OCER, RICE; FPRO PULS, RAPO, SUNO, SOYO, OLIO, OTHO, RAPC, SUNC, SOYC, OLIC, OTHC, DDGS, FPRI, SFIS,
FFIS, OAQU.

Source: CAPRI 2030 Green Deal reference market results (markmarket_greendeal_1730et_base_1717 dataOut): FEED per
member state and product, ARM1P of the EU trade block EU27yr19; kept as
capri_data/sources/market/feed_bulks_dataout_2030.csv.

Model commodity of each product: WHEA -> SWHE, MAIZ -> CORN, RYEM, OATS, OCER as themselves, RICE -> PARI, OLIO -> OLIV,
BARL, PULS, RAPO, SUNO, SOYO, RAPC, SUNC, SOYC, DDGS, OTHO and the fish products SFIS, FFIS, OAQU by name (markets
since 18 October 2026); OLIC, OTHC have no model market: their prices stay at the 2030 reference (REGISTERED).

Outputs (capri_data/2017/market/)
  feed_bulks_eu.csv         ms, bulk, product, commodity, feed_kt, arm1p, rho
  feed_bulks_no.csv         the same for Norway (its own ARM1P; KNOWN_ISSUES K56), plus use_kt (Norway's use of the
                            product, HCOM + FEDM + INDM + BIOF + LOSM + PRCM): the price indices of its supply models'
                            feed bulks and its feed demand in its own market region NOR
  feed_bulks_eu_share.csv   commodity, feed_kt, use_kt, share  (EU27 2030 reference: FEDM / (HCOM + FEDM + INDM
                            + BIOF + LOSM + PRCM) of the product group, the part of EU use that is feed;
                            the dairy products' feed is the dairy block's FMIL, not listed)
  capri_data/2017/feed/feed_cereal_mix_2030.csv  cereal, fedm_kt  (EU27 FCER feed per cereal with a model producer
                            price; replaces a hand-entered table that had rye and oats inside OCER)

    python tools/build/build_feed_bulks.py [--dump /mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt]
"""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "market" / "feed_bulks_dataout_2030.csv"
DEST = ROOT / "capri_data" / "2017" / "market"
GAMS = Path("/home/claude/work/allgms/gams")
BULKS = {"FCER": ("WHEA", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "RICE"),
         "FPRO": ("PULS", "RAPO", "SUNO", "SOYO", "OLIO", "OTHO", "RAPC", "SUNC", "SOYC", "OLIC", "OTHC", "DDGS",
                  "FPRI", "SFIS", "FFIS", "OAQU"),
         # Sprint 9h: CAPRI's other tradable bulks (global/fromimpact/sets.gms FEED_TO_O, MLK_DISAGG)
         "FENE": ("MOLA", "STAR", "FENI"),
         "FOTH": ("POTA", "RAPE", "SUNF", "SOYA", "OLIV", "OOIL", "TEXT", "TOMA", "OVEG", "APPL", "OFRU", "CITR",
                  "TAGR", "TABO", "TWIN", "SUGA", "EGGS", "PORK", "BEEF"),
         "FMIL": ("SMIP", "WMIO", "CASE", "WHEP", "BUTT", "CREM", "COCM", "CHES", "FRMI")}
#: CAPRI's balance items of domestic use (the EU's feed share of use below; Norway's in feed_bulks_no.csv)
USE_ITEMS = ("HCOM", "FEDM", "INDM", "BIOF", "LOSM", "PRCM")
COMMODITY = {"WHEA": "SWHE", "MAIZ": "CORN", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER", "RICE": "PARI",
             "OLIO": "OLIV", "BARL": "BARL", "PULS": "PULS", "RAPO": "RAPO", "SUNO": "SUNO", "SOYO": "SOYO",
             "RAPC": "RAPC", "SUNC": "SUNC", "SOYC": "SOYC", "DDGS": "DDGS",
             # Sprint 9h: residual feeds traded (FENI, FPRI), other feed products with a model market
             "FENI": "FENI", "FPRI": "FPRI", "POTA": "POTA", "RAPE": "RAPE", "SUNF": "SUNF", "SOYA": "SOYA",
             "OOIL": "OOIL", "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL", "OFRU": "OFRU", "CITR": "CITR",
             "TWIN": "WINE", "SUGA": "SUGR", "EGGS": "EGGS", "PORK": "PORK", "BEEF": "BEEF",
             # markets since October 2026: table grapes, table olives
             "TAGR": "TAGR", "TABO": "TABO", "TEXT": "TEXT",
             # markets since 18 October 2026: other vegetable oils, fish
             "OTHO": "OTHO", "SFIS": "SFIS", "FFIS": "FFIS", "OAQU": "OAQU",
             "SMIP": "SKIM", "WMIO": "WMIO", "CASE": "CASE", "WHEP": "WHEY", "BUTT": "BUTR", "CREM": "CREM",
             "COCM": "COCM", "CHES": "CHES", "FRMI": "FRMI"}
#: the dairy products' feed use is the dairy block's (MarketModule, FMIL); not in the generic feed share table
DAIRY = {"SKIM", "WMIO", "CASE", "WHEY", "BUTR", "CREM", "COCM", "CHES", "FRMI"}
#: the product groups of the model commodities in CAPRI's EU balance (for the feed share of use)
GROUPS = {"SWHE": ("SWHE", "DWHE"), "CORN": ("MAIZ",), "OCER": ("OCER",), "RYEM": ("RYEM",), "OATS": ("OATS",), "PARI": ("RICE",),
          "OLIV": ("OLIO",), "BARL": ("BARL",), "PULS": ("PULS",), "RAPO": ("RAPO",), "SUNO": ("SUNO",),
          "SOYO": ("SOYO",), "RAPC": ("RAPC",), "SUNC": ("SUNC",), "SOYC": ("SOYC",), "DDGS": ("DDGS",),
          "FENI": ("FENI",), "FPRI": ("FPRI",), "POTA": ("POTA",), "RAPE": ("RAPE",), "SUNF": ("SUNF",),
          "SOYA": ("SOYA",), "OOIL": ("OOIL",), "TOMA": ("TOMA",), "OVEG": ("OVEG",), "APPL": ("APPL",),
          "OFRU": ("OFRU",), "CITR": ("CITR",), "WINE": ("TWIN",), "SUGR": ("SUGA",), "EGGS": ("EGGS",),
          "PORK": ("PORK",), "BEEF": ("BEEF",), "TAGR": ("TAGR",), "TABO": ("TABO",), "TEXT": ("TEXT",),
          "OTHO": ("OTHO",), "SFIS": ("SFIS",), "FFIS": ("FFIS",), "OAQU": ("OAQU",)}
EU_MS = {"BL000000", "SE000000", "DK000000", "DE000000", "EL000000", "ES000000", "FR000000", "IR000000",
         "IT000000", "NL000000", "AT000000", "PT000000", "FI000000", "CY000000", "EE000000", "LV000000",
         "LT000000", "MT000000", "PL000000", "SK000000", "BG000000", "CZ000000", "HU000000", "SI000000",
         "RO000000", "HR000000"}


#: the FCER cereals weighted in the supply models' feed cereal price level (written to feed_cereal_mix_2030.csv)
FEED_CEREAL_MIX = ("SWHE", "BARL", "CORN", "RYEM", "OATS", "OCER")


def rho_feed():
    """p_rhoFeed of the member states (RMSSUP) as arm/market1.gms sets it, last assignment winning."""
    rho = {b: 4.0 for b in BULKS}
    f = GAMS / "arm" / "market1.gms"
    for line in open(f, errors="ignore"):
        if line.lstrip().startswith("*"):
            continue
        m = re.match(r'\s*p_rhoFeed\(RMSSUP,(?:"([A-Z]+)"|FEED)\)\s*=\s*([0-9.]+)', line)
        if m:
            if m.group(1) is None:
                rho = {k: float(m.group(2)) for k in rho}
            elif m.group(1) in rho:
                rho[m.group(1)] = float(m.group(2))
    return rho


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path,
                    default=Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt"))
    a = ap.parse_args()
    prods = sorted({p for v in BULKS.values() for p in v} | set(BULKS) | {x for g in GROUPS.values() for x in g})
    if a.dump.exists():
        txt = subprocess.run(["grep", "-E", r"^'[^']+'\.''\.'(FEED|ARM1P|" + "|".join(USE_ITEMS) + r")'\.'("
                              + "|".join(prods) + r")'\.'2030'", str(a.dump)], capture_output=True, text=True).stdout
        pat = re.compile(r"^'([^']+)'\.''\.'(FEED|ARM1P|" + "|".join(USE_ITEMS) + r")'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        # Norway's balance items (its use per product, for the feed share of its use) are kept for Norway only
        rows = [r for r in rows if (r[0] in EU_MS or r[0] in ("EU27yr19", "NO000000"))
                and (r[1] in ("FEED", "ARM1P") or r[0] == "NO000000")]
        pd.DataFrame(rows, columns=["region", "item", "product", "value"]).to_csv(SRC, index=False)
        print(f"extracted {len(rows)} rows -> {SRC.relative_to(ROOT)}")
    src = pd.read_csv(SRC)
    v = {(r.region, r.item, r.product): float(r.value) for r in src.itertuples()}
    rho = rho_feed()
    out, worst = [], []
    for ms in sorted(EU_MS):
        for b, items in BULKS.items():
            tot = 0.0
            for p in items:
                q = v.get((ms, "FEED", p), 0.0)
                pr = v.get(("EU27yr19", "ARM1P", p), 0.0)
                if q > 1e-6 and pr > 0:
                    out.append(dict(ms=ms, bulk=b, product=p, commodity=COMMODITY.get(p, ""), feed_kt=q, arm1p=pr,
                                    rho=rho[b]))
                    tot += q
            bt = v.get((ms, "FEED", b), 0.0)
            if bt > 10:
                worst.append((abs(tot / bt - 1), ms, b, tot, bt))
    df = pd.DataFrame(out)
    df.to_csv(DEST / "feed_bulks_eu.csv", index=False, float_format="%.8g")
    # Norway (CAPRI RMSSUP = NUTS0, so feedBlkPrice_ and feedShareEqu_ hold for it too): its bulks at its own Arm1
    # prices, for its supply models' bulk price indices and its feed demand in its own market region NOR (KNOWN_ISSUES
    # K56; Norway is not in the EU's feed demand); use_kt = its use of the product (HCOM + FEDM + INDM + BIOF + LOSM +
    # PRCM, as the EU's feed share of use below), for the feed share of Norway's use
    no = []
    for b, items in BULKS.items():
        for p in items:
            q = v.get(("NO000000", "FEED", p), 0.0)
            pr = v.get(("NO000000", "ARM1P", p), 0.0)
            if q > 1e-6 and pr > 0:
                use = sum(v.get(("NO000000", k, x), 0.0) for k in USE_ITEMS
                          for x in GROUPS.get(COMMODITY.get(p, ""), (p,)))
                no.append(dict(ms="NO000000", bulk=b, product=p, commodity=COMMODITY.get(p, ""), feed_kt=q, arm1p=pr,
                               rho=rho[b], use_kt=use))
    pd.DataFrame(no).to_csv(DEST / "feed_bulks_no.csv", index=False, float_format="%.8g")
    print(f"feed_bulks_no.csv: {len(no)} rows (Norway's bulks: price indices and feed demand)")
    bal = json.load(open(ROOT / "capri_data" / "validation" / "capri_eu27_market_balance_2030_ref.json"))["products"]
    sh = []
    for c, grp in GROUPS.items():
        # the residual feeds are used as feed only (CAPRI DOMM = FEED)
        # total use includes processing (PRCM: crushing of the oilseeds fed whole, cereal processing), as the
        # model's EU use does (Sprint 9h; before only HCOM + FEDM + INDM + BIOF + LOSM)
        use = sum(float(bal.get(x, {}).get(k, 0.0)) for x in grp
                  for k in ("HCOM", "FEDM", "INDM", "BIOF", "LOSM", "PRCM"))
        if c in ("FENI", "FPRI"):
            use = sum(float(bal.get(x, {}).get("FEDM", 0.0)) for x in grp)
        fed = float(df.loc[df.commodity == c, "feed_kt"].sum())
        if use > 0 and fed > 0:
            sh.append(dict(commodity=c, feed_kt=round(fed, 3), use_kt=round(use, 3), share=min(1.0, fed / use)))
    pd.DataFrame(sh).to_csv(DEST / "feed_bulks_eu_share.csv", index=False, float_format="%.6g")
    # EU27 2030 feed use of the FCER cereals with a model producer price: the weights of the feed cereal price
    # level in the supply models (supply_module FEED_CEREAL_MIX, projection/prices.py). RICE (milled) is left out:
    # the model has no producer price for it (0.2% of FCER).
    mix = (df[(df.bulk == "FCER") & df.commodity.isin(FEED_CEREAL_MIX)].groupby("commodity")["feed_kt"].sum()
           .reindex(FEED_CEREAL_MIX).round(1))
    mix.rename("fedm_kt").rename_axis("cereal").to_csv(ROOT / "capri_data" / "2017" / "feed" / "feed_cereal_mix_2030.csv")
    print("feed_cereal_mix_2030.csv:", mix.to_dict())
    worst.sort(reverse=True)
    print(f"feed_bulks_eu.csv: {len(df)} rows, {df.ms.nunique()} member states; rho {rho}")
    print("products against CAPRI's bulk total, worst: " + "; ".join(f"{ms} {b} {t:.0f}/{bt:.0f}" for _, ms, b, t, bt in worst[:4]))
    print(df.groupby(["bulk", "product"])["feed_kt"].sum().round(0).to_string())
    print(pd.DataFrame(sh).to_string(index=False))


if __name__ == "__main__":
    main()

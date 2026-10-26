"""CAPRI's bilateral trade data for the model's trade regions (Sprint 8m: CAPRI's full market).

CAPRI's market model (arm/market_model.gms) clears, per market region and product, the region's own good:
domestic sales + exports = production (SupBalM_), with total use an Armington aggregate of domestic sales and
an import aggregate (arm1PriceAgg_, arm2QuantShares_, rho1 = p_rhoArm1) and the import aggregate a CES over
origins (rho2 = p_rhoArm2) of bilateral flows priced at (exporter market price + transport cost) x (1 + ad
valorem tariff) + specific tariff (impPrice_). This builder takes, from CAPRI's own market results, every
bilateral flow and its price components and aggregates them to the model's trade regions:

  year 2017: market_base_1717 (CAPRI's base market, BAS = SIM = 2017)
  year 2030: markmarket_greendeal_1730et_base_1717 (CAPRI's 2030 Green Deal reference)

Per (importer I, exporter J) of the model, over the CAPRI region pairs (i, j) mapped to them:
  q      = sum ImportQ                                   (1000 t; I = J: domestic sales incl. trade between
                                                          CAPRI regions folded into the same model region)
  a      = sum ImportQ x Fob x (1 + TaAppl/100) / q      exporter-price part of the import price
  b      = sum ImportQ x [TCost x (1 + TaAppl/100) + ts] / q,  ts = ImportP - (Fob + TCost)(1 + TaAppl/100)
                                                          (specific tariffs and TRQ effects as CAPRI priced them)
  so that the base import price ImportP (quantity-weighted) = a + b and, with the exporter's market price
  moving by r_J, the import price is a r_J + b - CAPRI's impPrice_ aggregated exactly at the base composition.
  a0     = sum ImportQ x Fob / q (the same without the ad valorem tariff, for tariff scenarios)
  tc     = sum ImportQ x TCost / q (transport cost: with a0 the base of an ad valorem tariff change, impPrice_)
For I = J the price is the region's own market price (a = 1 x PMRK, b = 0).
Per region and product: PMRK (production-weighted), PROD.
Substitution elasticities rho1, rho2 per product: arm/market1.gms (8 / 10) overridden by special_ch/
market1_ch.gms (CEPII, Fontagne, Guimbard & Orefice 2019), as CAPRI includes it.

Model commodity <- CAPRI products: SWHE <- WHEA (durum is part of CAPRI's wheat market), CORN <- MAIZ,
RYEM, OATS, OCER as CAPRI (arm_sets CERE_DEF), PARI <- RICE (milled), SUGR <- SUGA, WINE <- TWIN, OLIV <- OLIO (olive oil),
BUTR <- BUTT, SKIM <- SMIP, WHEY <- WHEP, POUL <- POUM, SHGM <- SGMT, the rest by name (biofuels BIOE, BIOD
included; DDGS, the ethanol plants' feed by-product, too; the dairy products FRMI, CREM, COCM, WMIO, CASE; the residual feeds FENI, FPRI). Raw milk and other
oilseeds have no CAPRI bilateral trade (MILK: 31 cells of a few tonnes; OOIL: none).

Outputs (capri_data/2017/market/):
  bilateral_flows_<year>.csv    commodity, importer, exporter, q_kt, a, b, a0, ta_pct, tc
  bilateral_regions_<year>.csv  commodity, region, pmrk, prod_kt
  armington_rho.csv             commodity, capri, rho1, rho2

    python tools/build/build_bilateral_market.py               (EU as one region, EU27yr19)
    python tools/build/build_bilateral_market.py --eu-blocks   (CAPRI's two EU trade blocks: *_eu2.csv)
"""
from __future__ import annotations
import re, subprocess, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = {2017: Path("/mnt/user-data/uploads/market_base_1717.txt"),
       2030: Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt")}
KEEP = ROOT / "capri_data" / "sources" / "market"
GAMS = Path("/home/claude/work/allgms/gams")
MODEL = {
    "SWHE": ("WHEA",), "BARL": ("BARL",), "CORN": ("MAIZ",), "OCER": ("OCER",), "RYEM": ("RYEM",), "OATS": ("OATS",), "PARI": ("RICE",),
    "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",), "SUGR": ("SUGA",), "POTA": ("POTA",),
    "PULS": ("PULS",), "TOMA": ("TOMA",), "OVEG": ("OVEG",), "APPL": ("APPL",), "OFRU": ("OFRU",),
    "CITR": ("CITR",), "TAGR": ("TAGR",), "TOBA": ("TOBA",), "TABO": ("TABO",), "TEXT": ("TEXT",), "PLMO": ("PLMO",), "OTHO": ("OTHO",),
    "FFIS": ("FFIS",), "SFIS": ("SFIS",), "OAQU": ("OAQU",), "COFF": ("COFF",), "TEAS": ("TEAS",), "COCO": ("COCO",), "WINE": ("TWIN",), "OLIV": ("OLIO",), "BUTR": ("BUTT",), "SKIM": ("SMIP",),
    "CHES": ("CHES",), "WHEY": ("WHEP",), "BEEF": ("BEEF",), "PORK": ("PORK",), "POUL": ("POUM",),
    "SGMT": ("SGMT",), "EGGS": ("EGGS",), "RAPO": ("RAPO",), "SUNO": ("SUNO",), "SOYO": ("SOYO",),
    "RAPC": ("RAPC",), "SUNC": ("SUNC",), "SOYC": ("SOYC",),
    # biofuels: traded market products with endogenous biofuel markets (BIOF_M, docs/BIOFUEL_MARKET.md)
    "BIOE": ("BIOE",), "BIOD": ("BIOD",),
    # distillers' dried grains from ethanol plants (CAPRI prodQuantBiofBy_), a traded protein feed
    "DDGS": ("DDGS",),
    # CAPRI's other dairy products, traded bilaterally as the four above (dairy block: arm/market_model.gms
    # DairyNQ_, ProcMargM_, FatsProtBal_; Sprint 9f): fresh milk products, cream, concentrated milk, whole milk
    # powder, casein - model codes = CAPRI codes
    "FRMI": ("FRMI",), "CREM": ("CREM",), "COCM": ("COCM",), "WMIO": ("WMIO",), "CASE": ("CASE",),
    # CAPRI's residual feed products (RESIMP), traded bilaterally; EU supply from milling and sugar processing
    # (MaprFeed_; Sprint 9h): energy-rich feed FENI (sugar-beet by-products, manioc, roots) and milling
    # by-products FPRI
    "FENI": ("FENI",), "FPRI": ("FPRI",),
}
CAPRI = {c: m for m, cs in MODEL.items() for c in cs}
PAIR_ITEMS = ("ImportQ", "ImportP", "Fob", "TCost", "TaAppl")
REG_ITEMS = ("PMRK", "PROD")


def rho_table():
    """p_rhoArm1/2: 8 and 10 by default (arm/market1.gms), market1_ch.gms values where set."""
    r = defaultdict(lambda: {1: 8.0, 2: 10.0})
    f = GAMS / "special_ch" / "market1_ch.gms"
    if f.exists():
        for m in re.finditer(r'p_rhoArm([12])\(RM,"([A-Z]+)"\)\s*=\s*([0-9.]+)', f.read_text(errors="ignore")):
            r[m.group(2)][int(m.group(1))] = float(m.group(3))
    return r


EU_BLOCKS = {"A_EU_WEST": "EU_WEST", "A_EU_EAST": "EU_EAST"}


def extract(year, eu_blocks=False):
    """eu_blocks: keep CAPRI's two EU trade blocks (A_EU_WEST, A_EU_EAST, defaultA.agg) instead of the EU27yr19
    reporting block, for the market with the EU as two regions (docs/archive/MARKET_STRUCTURE_PLAN.md step 3)."""
    src = SRC[year]
    keep = KEEP / f"bilateral_dataout_{year}{'_eu2' if eu_blocks else ''}.csv.xz"
    if src.exists():
        prods = "|".join(CAPRI)
        pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'(" + "|".join(PAIR_ITEMS + REG_ITEMS) + r")'\.'(" + prods
                         + r")'\.'" + str(year) + r"'\s+([-\d.Ee+]+)")
        # grep first: the 2030 dump is 390 MB
        txt = subprocess.run(["grep", "-E", r"'(" + "|".join(PAIR_ITEMS + REG_ITEMS) + r")'\.'(" + prods + r")'\.'" + str(year) + "'",
                              str(src)], capture_output=True, text=True).stdout
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        # keep only what is used: pairs that carry a flow, regions' own items; no reporting aggregates
        from recalibrate_trade_2017 import AGGREGATES as _AG
        if eu_blocks:
            _AG = (set(_AG) - set(EU_BLOCKS)) | {"EU27yr19"}
        flow = {(a, b, p) for a, b, it, p, v in rows if it == "ImportQ" and float(v) > 1e-6}
        rows = [r for r in rows if r[0] not in _AG and r[1] not in _AG
                and (r[1] == "" or (r[0], r[1], r[3]) in flow)]
        pd.DataFrame(rows, columns=["r1", "r2", "item", "product", "value"]).to_csv(keep, index=False)
        print(f"{year}: extracted {len(rows)} rows -> {keep.relative_to(ROOT)}")
    return pd.read_csv(keep, keep_default_na=False)


def build(year, REGION_MAP, AGGREGATES, eu_blocks=False):
    df = extract(year, eu_blocks)
    df["value"] = df["value"].astype(float)
    sfx = "_eu2" if eu_blocks else ""
    if eu_blocks:
        REGION_MAP = {k: v for k, v in REGION_MAP.items() if k != "EU27yr19"}
        REGION_MAP.update(EU_BLOCKS)
        AGGREGATES = (set(AGGREGATES) - set(EU_BLOCKS)) | {"EU27yr19"}
        skip = lambda r: r in AGGREGATES or r.startswith(("EU0", "EU_")) or (r.endswith("000000") and r not in ("UK000000", "NO000000"))
    else:
        skip = lambda r: r in AGGREGATES or r.startswith(("EU0", "EU_", "A_EU")) or (r.endswith("000000") and r not in ("UK000000", "NO000000"))
    mp = lambda r: REGION_MAP.get(r, "ROW")
    pair = defaultdict(dict)
    reg = defaultdict(dict)
    for r in df.itertuples(index=False):
        if r.item in PAIR_ITEMS:
            if skip(r.r1) or skip(r.r2):
                continue
            pair[(r.product, r.r1, r.r2)][r.item] = r.value
        elif r.r2 == "" and not skip(r.r1):
            reg[(r.product, r.r1)][r.item] = r.value
    trading = {i for (_, i, j) in pair if i == j} | {j for (_, i, j) in pair if i == j}
    reg = {k: v for k, v in reg.items() if k[1] in trading}
    agg = defaultdict(lambda: defaultdict(float))
    for (p, i, j), d in pair.items():
        q = d.get("ImportQ", 0.0)
        if q <= 1e-6:
            continue
        mi, mj, mc = mp(i), mp(j), CAPRI[p]
        if i == j or mi == mj:                        # domestic sales of the model region
            pm = reg.get((p, j), {}).get("PMRK", d.get("Fob", 0.0))
            a, b, a0, ta, tc = pm, 0.0, pm, 0.0, 0.0
            mj = mi
        else:
            fob, tc, ta, ip = d.get("Fob", 0.0), d.get("TCost", 0.0), d.get("TaAppl", 0.0), d.get("ImportP", 0.0)
            if fob <= 0 or ip <= 0:
                continue
            ts = ip - (fob + tc) * (1 + ta / 100.0)
            a, b, a0 = fob * (1 + ta / 100.0), tc * (1 + ta / 100.0) + ts, fob
        k = agg[(mc, mi, mj)]
        k["q"] += q; k["qa"] += q * a; k["qb"] += q * b; k["qa0"] += q * a0; k["qta"] += q * ta; k["qtc"] += q * tc
    rows = [dict(commodity=c, importer=i, exporter=j, q_kt=v["q"], a=v["qa"] / v["q"], b=v["qb"] / v["q"],
                 a0=v["qa0"] / v["q"], ta_pct=v["qta"] / v["q"], tc=v["qtc"] / v["q"])
            for (c, i, j), v in agg.items() if v["q"] > 0]
    fl = pd.DataFrame(rows).sort_values(["commodity", "importer", "exporter"])
    ra = defaultdict(lambda: defaultdict(float))
    for (p, r), d in reg.items():
        pr, pm = d.get("PROD", 0.0), d.get("PMRK", 0.0)
        k = ra[(CAPRI[p], mp(r))]
        k["prod"] += max(pr, 0.0); k["pv"] += max(pr, 0.0) * pm; k["pm_any"] = max(k["pm_any"], pm)
    rrows = [dict(commodity=c, region=r, pmrk=(v["pv"] / v["prod"] if v["prod"] > 0 else v["pm_any"]), prod_kt=v["prod"])
             for (c, r), v in ra.items()]
    rg = pd.DataFrame(rrows).sort_values(["commodity", "region"])
    dest = ROOT / "capri_data" / "2017" / "market"
    fl.to_csv(dest / f"bilateral_flows_{year}{sfx}.csv", index=False, float_format="%.8g")
    rg.to_csv(dest / f"bilateral_regions_{year}{sfx}.csv", index=False, float_format="%.8g")
    # checks: exports + domestic sales = production (CAPRI SupBalM_, stock changes aside)
    worst = []
    for c in MODEL:
        f = fl[fl.commodity == c]
        if f.empty:
            continue
        sup = f.groupby("exporter")["q_kt"].sum()
        pr = rg[rg.commodity == c].set_index("region")["prod_kt"]
        for r in sup.index:
            if pr.get(r, 0) > 100:
                worst.append((abs(sup[r] / pr[r] - 1), c, r, sup[r], pr[r]))
    worst.sort(reverse=True)
    print(f"{year}: {len(fl)} flows, {fl.commodity.nunique()} commodities; supply balance worst: "
          + "; ".join(f"{c} {r} {s:.0f}/{p:.0f}" for _, c, r, s, p in worst[:5]))
    eur = ("EU_WEST", "EU_EAST") if eu_blocks else ("EU27",)
    eu = fl[fl.importer.isin(eur) & ~fl.exporter.isin(eur)].groupby("commodity")["q_kt"].sum()
    print(f"  EU extra-EU imports (kt): " + ", ".join(f"{c} {v:.0f}" for c, v in eu.items() if c in ("BEEF", "PORK", "POUL", "SWHE", "SOYA", "CHES")))
    return fl, rg


def build_trq(year, REGION_MAP, AGGREGATES):
    """EU tariff-rate quotas per model exporter (CAPRI's bilateral TRQs of the EU policy block 'EU').

    Per CAPRI exporter j with an EU quota TrqNT: in-quota price p_in = (Fob + TCost)(1 + TaAppl/100) (+ the
    applied specific in-quota tariff), out-of-quota price p_out = (Fob + TCost)(1 + TAMFN/100) + TSMFN (MFN).
    Aggregated to the model exporter: quota = sum TrqNT, gap = quota-weighted p_out - p_in, base imports from
    the exporters with a quota. Output bilateral_trq_<year>.csv: commodity, exporter, quota_kt, gap_eur_t,
    imports_kt."""
    src = SRC[year]
    keep = KEEP / f"bilateral_trq_dataout_{year}.csv"
    items = ("TrqNT", "TAMFN", "TSMFN", "TaAppl", "TsAppl", "Fob", "TCost", "ImportQ")
    if src.exists():
        prods = "|".join(CAPRI)
        txt = subprocess.run(["grep", "-E", r"^'EU'\.'[^']*'\.'(" + "|".join(items) + r")'\.'(" + prods + r")'\.'" + str(year) + "'",
                             str(src)], capture_output=True, text=True).stdout
        pat = re.compile(r"^'EU'\.'([^']*)'\.'([A-Za-z]+)'\.'([A-Z]+)'\.'\d+'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        pd.DataFrame(rows, columns=["exporter", "item", "product", "value"]).to_csv(keep, index=False)
    df = pd.read_csv(keep, keep_default_na=False)
    d = defaultdict(dict)
    for r in df.itertuples(index=False):
        d[(r.product, r.exporter)][r.item] = float(r.value)
    mfn_s = {p: d.get((p, "World"), {}).get("TSMFN", 0.0) for p in CAPRI}
    mfn_a = {p: d.get((p, "World"), {}).get("TAMFN", 0.0) for p in CAPRI}
    agg = defaultdict(lambda: defaultdict(float))
    for (p, j), v in d.items():
        q = v.get("TrqNT", 0.0)
        if q <= 0 or q >= 1e8 or j in AGGREGATES or j in ("World", "") or j.startswith(("EU", "A_EU")):   # 1e10: no quota (free access)
            continue
        fob, tc = v.get("Fob", 0.0), v.get("TCost", 0.0)
        if fob <= 0:
            continue
        p_in = (fob + tc) * (1 + v.get("TaAppl", 0.0) / 100.0) + max(0.0, v.get("TsAppl", 0.0))
        p_out = (fob + tc) * (1 + v.get("TAMFN", mfn_a.get(p, 0.0)) / 100.0) + mfn_s.get(p, 0.0)
        mj = REGION_MAP.get(j, "ROW")
        if mj == "EU27":
            continue
        k = agg[(CAPRI[p], mj)]
        k["quota"] += q; k["qg"] += q * max(0.0, p_out - p_in); k["imp"] += v.get("ImportQ", 0.0)
    rows = [dict(commodity=c, exporter=j, quota_kt=v["quota"], gap_eur_t=v["qg"] / v["quota"], imports_kt=v["imp"])
            for (c, j), v in agg.items() if v["quota"] > 0]
    out = pd.DataFrame(rows).sort_values(["commodity", "exporter"])
    out.to_csv(ROOT / "capri_data" / "2017" / "market" / f"bilateral_trq_{year}.csv", index=False, float_format="%.8g")
    tot = out.groupby("commodity")[["quota_kt", "imports_kt"]].sum()
    print(f"{year} EU TRQs: " + ", ".join(f"{c} {r.imports_kt:.0f}/{r.quota_kt:.0f}" for c, r in tot.iterrows()))
    return out


def main():
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from recalibrate_trade_2017 import REGION_MAP, AGGREGATES
    KEEP.mkdir(parents=True, exist_ok=True)
    blocks = "--eu-blocks" in sys.argv
    for y in (2017, 2030):
        build(y, REGION_MAP, AGGREGATES, eu_blocks=blocks)
        if not blocks:
            build_trq(y, REGION_MAP, AGGREGATES)        # the EU's quotas are the same for one or two EU regions
    if blocks:
        return
    rt = rho_table()
    rows = [dict(commodity=m, capri=cs[0], rho1=rt[cs[0]][1], rho2=rt[cs[0]][2]) for m, cs in MODEL.items()]
    pd.DataFrame(rows).to_csv(ROOT / "capri_data" / "2017" / "market" / "armington_rho.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()

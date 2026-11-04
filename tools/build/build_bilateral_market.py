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

    python tools/build/build_bilateral_market.py   (CAPRI's two EU market regions; the one-EU form, EU27yr19, and
                                                    its *_eu2.csv twin names were removed on 3 November 2026)
"""
from __future__ import annotations
import csv, re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import EXPORTS, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _market_regions import model_region  # noqa: E402  (the market's grouping step: CAPRI region -> model region)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = {2017: EXPORTS / "market_base_1717.txt",
       2030: EXPORTS / "markmarket_greendeal_1730et_base_1717.txt"}
KEEP = ROOT / "capri_data" / "sources" / "market"
GAMS = SOURCES / "gams"
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


def extract(year):
    """CAPRI's market regions with the EU as its two A_EU_WEST and A_EU_EAST (defaultA.agg), not the EU27yr19
    reporting block (the one-EU extract and its files were removed on 3 November 2026, market move stage 3)."""
    src = SRC[year]
    keep = KEEP / f"bilateral_dataout_{year}.csv.xz"
    if src.exists():
        prods = "|".join(CAPRI)
        pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'(" + "|".join(PAIR_ITEMS + REG_ITEMS) + r")'\.'(" + prods
                         + r")'\.'" + str(year) + r"'\s+([-\d.Ee+]+)")
        # grep first: the 2030 dump is 390 MB
        txt = grep(r"'(" + "|".join(PAIR_ITEMS + REG_ITEMS) + r")'\.'(" + prods + r")'\.'" + str(year) + "'", str(src))
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        # keep only what is used: pairs that carry a flow, regions' own items; no reporting aggregates
        from recalibrate_trade_2017 import AGGREGATES as _AG
        _AG = (set(_AG) - set(EU_BLOCKS)) | {"EU27yr19"}
        flow = {(a, b, p) for a, b, it, p, v in rows if it == "ImportQ" and float(v) > 1e-6}
        rows = [r for r in rows if r[0] not in _AG and r[1] not in _AG
                and (r[1] == "" or (r[0], r[1], r[3]) in flow)]
        pd.DataFrame(rows, columns=["r1", "r2", "item", "product", "value"]).to_csv(keep, index=False)
        print(f"{year}: extracted {len(rows)} rows -> {keep.relative_to(ROOT)}")
    return _read_csv(keep, keep_default_na=False)


def build(year, AGGREGATES):
    df = extract(year)
    df["value"] = df["value"].astype(float)
    sfx = ""
    AGGREGATES = (set(AGGREGATES) - set(EU_BLOCKS)) | {"EU27yr19"}
    skip = lambda r: r in AGGREGATES or r.startswith(("EU0", "EU_")) or (r.endswith("000000") and r not in ("UK000000", "NO000000"))
    # the model's market region of each CAPRI region: the grouping step (tools/lib/_market_regions.py; until 3 November
    # 2026 REGION_MAP.get(r, "ROW"), the EU blocks added here)
    mp = lambda r: model_region(r, eu_as_blocks=True)
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
    fl.to_csv(dest / f"bilateral_flows_{year}{sfx}.csv", index=False)
    rg.to_csv(dest / f"bilateral_regions_{year}{sfx}.csv", index=False)
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
    eur = ("EU_WEST", "EU_EAST")
    eu = fl[fl.importer.isin(eur) & ~fl.exporter.isin(eur)].groupby("commodity")["q_kt"].sum()
    print(f"  EU extra-EU imports (kt): " + ", ".join(f"{c} {v:.0f}" for c, v in eu.items() if c in ("BEEF", "PORK", "POUL", "SWHE", "SOYA", "CHES")))
    return fl, rg


def build_trq(year, AGGREGATES):
    """CAPRI's bilateral tariff-rate quotas of every importer (p_trqBilat: TrqNT with its in- and out-of-quota rates),
    on CAPRI's policy blocks (RMTP; RM_TO_RMTP), per model commodity (MARKET_REGIONS_INVENTORY §5 stage 4,
    docs/design/PORTS_STAGE4.md). A quota counts where TrqNT > 0 and below 1E+9 (CAPRI: not 1E+10, free access, nor
    "prohibitive", an acronym the listing does not print as a number). Rates as CAPRI holds them for the pair: ad
    valorem TaMFN, TaPref (%), specific TsMFN, TsPref (EUR/t); one missing is 0, as in CAPRI's equations, which switch
    a rate only where one of its two values is above eps. CAPRI products of one model commodity (none at present with
    quotas on the same pair) would be summed, rates quota-weighted.
    Output bilateral_trq_<year>.csv: importer, exporter (policy blocks), commodity, quota_kt, ta_mfn, ta_pref, ts_mfn,
    ts_pref, importer_regions, exporter_regions (the blocks' market regions, "|"-joined), regime (bilateral, with_global:
    the importer also has a global quota on the product, entry_price: a preferential trigger price is set). Until 4 November 2026 the EU's quotas only, summed per model exporter with a price gap frozen at the base
    (DEP-34, DEP-35, DEP-36)."""
    src = SRC[year]
    keep = KEEP / f"bilateral_trq_dataout_{year}.csv"
    items = ("TRQNT", "TAMFN", "TAPREF", "TSMFN", "TSPREF", "PREFTRIGPRICE")
    if src.exists():
        prods = "|".join(CAPRI)
        txt = grep(r"(?i)^'[^']*'\.'[^']*'\.'(" + "|".join(items) + r")'\.'(" + prods + r")'\.'" + str(year) + "'",
                   str(src))
        pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'([A-Za-z]+)'\.'([A-Z]+)'\.'\d+'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        rows = [(a, b, it.upper(), pr, v) for a, b, it, pr, v in rows if it.upper() in items
                and (b != "World" or it.upper() != "PREFTRIGPRICE")]
        pd.DataFrame(rows, columns=["importer", "exporter", "item", "product", "value"]).to_csv(keep, index=False)
    df = _read_csv(keep, keep_default_na=False)
    d = defaultdict(dict)
    for r in df.itertuples(index=False):
        d[(r.importer, r.exporter, r.product)][r.item] = float(r.value)
    # CAPRI's policy blocks (codes/capri/RMTP.csv); the listing also reports aggregates (World, HI_INC, NONEU_EU,
    # the EU's market regions A_EU_*), which are not quota holders
    with open(ROOT / "capri_data" / "codes" / "capri" / "RMTP.csv", newline="") as fh:
        rmtp = {r["code"] for r in csv.DictReader(fh)}
    agg = defaultdict(lambda: defaultdict(float))
    for (i, j, p), v in d.items():
        q = v.get("TRQNT", 0.0)
        if q <= 0 or q >= 1e9 or i == j or i not in rmtp or j not in rmtp:
            continue
        k = agg[(i, j, CAPRI[p])]
        k["q"] += q
        # CAPRI's regime of the pair (arm/set_tariffs.gms, market_model.gms): the entry price system where a
        # preferential trigger price is set (tariffs fixed at TARV and the entry price's specific part: stage 6); with
        # a global (erga omnes, exporter "World") quota of the importer that has rates, the smaller of the two rates
        # (ncpcm in tarAdval_, tarSpec_: stage 5); else the bilateral sigmoid alone (stage 4)
        gl = d.get((i, "World", p), {})
        has_gl = 0 < gl.get("TRQNT", 0.0) < 1e9 and any(gl.get(x, 0.0) > 0 for x in ("TAMFN", "TAPREF", "TSMFN", "TSPREF"))
        reg = "entry_price" if v.get("PREFTRIGPRICE", 0.0) > 0 else ("with_global" if has_gl else "bilateral")
        if k.get("regime", reg) != reg:
            raise ValueError(f"{i} <- {j} {CAPRI[p]}: CAPRI products of one model commodity in two TRQ regimes")
        k["regime"] = reg
        for it in ("TAMFN", "TAPREF", "TSMFN", "TSPREF"):
            k[it] += q * v.get(it, 0.0)
    # each policy block's market regions as the model names them (RM_TO_RMTP; the EU's two as EU_WEST, EU_EAST)
    members = defaultdict(list)
    with open(ROOT / "capri_data" / "codes" / "capri" / "RM_TO_RMTP.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            members[r["rmtp"]].append(model_region(r["rm"], eu_as_blocks=True))
    rows = [dict(importer=i, exporter=j, commodity=c, quota_kt=v["q"], ta_mfn=v["TAMFN"] / v["q"],
                 ta_pref=v["TAPREF"] / v["q"], ts_mfn=v["TSMFN"] / v["q"], ts_pref=v["TSPREF"] / v["q"],
                 importer_regions="|".join(members[i]), exporter_regions="|".join(members[j]), regime=v["regime"])
            for (i, j, c), v in agg.items()]
    out = pd.DataFrame(rows).sort_values(["importer", "commodity", "exporter"])
    out.to_csv(ROOT / "capri_data" / "2017" / "market" / f"bilateral_trq_{year}.csv", index=False)
    print(f"{year} bilateral TRQs: {len(out)} quotas; per importer: " + ", ".join(
        f"{i} {n}" for i, n in out.importer.value_counts().items()) + "; per regime: " + ", ".join(
        f"{r} {n}" for r, n in out.regime.value_counts().items()))
    return out


def main():
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    from recalibrate_trade_2017 import AGGREGATES
    KEEP.mkdir(parents=True, exist_ok=True)
    for y in (2017, 2030):
        build(y, AGGREGATES)
        build_trq(y, AGGREGATES)        # the EU's quotas (the same for one or two EU regions)
    rt = rho_table()
    rows = [dict(commodity=m, capri=cs[0], rho1=rt[cs[0]][1], rho2=rt[cs[0]][2]) for m, cs in MODEL.items()]
    pd.DataFrame(rows).to_csv(ROOT / "capri_data" / "2017" / "market" / "armington_rho.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()

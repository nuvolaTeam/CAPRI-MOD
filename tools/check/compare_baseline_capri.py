"""How closely the model's 2030 BASELINE reproduces CAPRI star 3.0's own 2030 reference (like for like).

The Farm-to-Fork comparison with JRC121368 mixes the model's simplifications with the difference between CAPRI
versions (JRC's 2020 CAPRI, base 2012, OECD-FAO 2017-2026 baseline; our star 3.0 data, base 2017). CAPRI's 2030
Green Deal reference of the version we have (res_2_1730greendeal_refdefaulta; capri_data/validation) has no
version gap: with no policy shock the model should land on it, and what it misses is the model's own doing.

Compared, EU27, model baseline of a run saved by tools/run/run_f2f_2030.py against CAPRI's reference:
  activity levels  (1000 ha / 1000 heads)   capri_eu27_levels_2030_ref.csv (EU27yr19 LEVL, extracted from
                                            markmarket_greendeal_1730et_base_1717); laying hens: CAPRI counts
                                            1000s of the model's unit; fattened pigs and broilers are left out
                                            (CAPRI counts animals produced a year, the model places)
  market production (1000 t)                capri_eu27_market_balance_2030_ref.json MAPR (GROF where no MAPR);
                                            in a run with market.demand_calibration = "capri" (S7) the market takes
                                            the marketed production (CAPRI's grofNEprod: gross x PROD/GROF at the
                                            calibration point), so the block compares it with CAPRI's own marketed
                                            production instead: the sum over the EU's member states of
                                            DATA(ms, "Prod", product, "CAL") of sim_ini_21730
                                            (capri_data/2017/market/market_prod_grof_2030.csv, prod_kt)
  market domestic use (1000 t)              GROF + IMPT - EXPT: the model's market works with gross production, so
                                            its use holds CAPRI's on-farm seed and losses (SEDF, LOSF) besides
                                            CAPRI's market use DOMM (HCOM + FEDM + SEDM + INDM + PRCM + BIOF + LOSM;
                                            DOMM + SEDF + LOSF = GROF + IMPT - EXPT, checked on barley). Until
                                            5 November 2026 the sum HCOM + FEDM + INDM + BIOF + LOSM + PRCM, which
                                            leaves out seed and on-farm use (cereals 8-10% short of the balance)
  producer prices (EUR/t)                   UVAP; the model's prices are CAPRI's 2030 prices in 2017 money, so
                                            the price block reports each ratio against the median ratio
                                            (the deflator), i.e. the RELATIVE price structure

Usage: python tools/check/compare_baseline_capri.py RUN.pkl [--csv OUT.csv]
"""
import argparse
import json
import pickle
from pathlib import Path

import numpy as np
__import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from capri_mod.io_results import load_run  # a run pickle or a stored run, "store:ROOT:SCENARIO[:RUN_ID]"

ROOT = Path(__file__).resolve().parents[2]
ACT = {"SWHE": "SWHE", "DWHE": "DWHE", "RYEM": "RYEM", "BARL": "BARL", "OATS": "OATS", "CORN": "MAIZ",
       "OCER": "OCER", "PARI": "PARI", "RAPE": "RAPE", "SUNF": "SUNF", "SOYA": "SOYA", "OOIL": "OOIL",
       "SUGB": "SUGB", "POTA": "POTA", "PULS": "PULS", "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL",
       "OFRU": "OFRU", "CITR": "CITR", "OLIV": "OLIV", "WINE": "TWIN", "TAGR": "TAGR", "TOBA": "TOBA", "TABO": "TABO",
       "TEXT": "TEXT", "OIND": "OIND", "OCRO": "OCRO", "NURS": "NURS", "FLOW": "FLOW", "GRAE": "GRAE",
       "GRAI": "GRAI", "MAIF": "MAIF", "OFAR": "OFAR", "ROOF": "ROOF", "FALL": "FALL", "VSET": "VSET",
       "DCOW": "DCOW", "BCOW": "SCOW", "CALV": "CAMF+CAFF+CAMR+CAFR",
       "PIGS": "SOWS", "SHGM": "SHGM", "SHGF": "SHGF", "LAYS": "HENS"}
UNIT = {"LAYS": 1000.0}
MKT = {"SWHE": "SWHE+DWHE", "BARL": "BARL", "CORN": "MAIZ", "RYEM": "RYEM", "OATS": "OATS", "OCER": "OCER", "PARI": "RICE",
       "RAPE": "RAPE", "SUNF": "SUNF", "SOYA": "SOYA", "OOIL": "OOIL", "SUGR": "SUGA", "POTA": "POTA",
       "PULS": "PULS", "TOMA": "TOMA", "OVEG": "OVEG", "APPL": "APPL", "OFRU": "OFRU", "CITR": "CITR",
       "WINE": "TWIN", "OLIV": "OLIO", "TAGR": "TAGR", "TOBA": "TOBA", "TABO": "TABO", "TEXT": "TEXT", "MILK": "COMI+SGMI", "BUTR": "BUTT", "SKIM": "SMIP", "CHES": "CHES",
       "WHEY": "WHEP", "BEEF": "BEEF", "PORK": "PORK", "POUL": "POUM", "SGMT": "SGMT", "EGGS": "EGGS",
       "RAPO": "RAPO", "SUNO": "SUNO", "SOYO": "SOYO", "PLMO": "PLMO", "OTHO": "OTHO", "RAPC": "RAPC", "SUNC": "SUNC", "SOYC": "SOYC",
       "BIOE": "BIOE", "BIOD": "BIOD", "DDGS": "DDGS", "FRMI": "FRMI", "CREM": "CREM", "COCM": "COCM", "WMIO": "WMIO",
       "CASE": "CASE", "FENI": "FENI", "FPRI": "FPRI"}
USE = ("HCOM", "FEDM", "INDM", "BIOF", "LOSM", "PRCM")
# the model's market products as CAPRI's in market_prod_grof_2030.csv (its products are CAPRI's XX; the others the same)
PROD_CODE = {"SWHE": "WHEA", "CORN": "MAIZ", "PARI": "RICE", "OLIV": "OLIO", "POUL": "POUM", "WINE": "TWIN"}


def capri_mode(o) -> bool:
    """The run's market takes the marketed production (market.demand_calibration = "capri", S7)."""
    s = (o.get("meta") or {}).get("settings") or {}
    return str((s.get("market") or {}).get("demand_calibration", "")) == "capri"


def capri_marketed_production():
    """CAPRI's marketed production at the 2030 calibration point, EU27 (the member states of
    capri_data/shared/eu_market_blocks.csv), per CAPRI market product, kt."""
    import csv
    from capri_mod.data.definitions import EU_MS_BLOCK
    out = {}
    with open(ROOT / "capri_data" / "2017" / "market" / "market_prod_grof_2030.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["capri_ms"] in EU_MS_BLOCK:
                out[r["product"]] = out.get(r["product"], 0.0) + float(r["prod_kt"])
    return out


def _sum(d, expr, f):
    vals = [f(d, k) for k in expr.split("+")]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def rows(o):
    ref_lv = {}
    for line in open(ROOT / "capri_data" / "validation" / "capri_eu27_levels_2030_ref.csv").read().splitlines()[1:]:
        k, v = line.split(",")
        ref_lv[k] = float(v)
    bal = json.load(open(ROOT / "capri_data" / "validation" / "capri_eu27_market_balance_2030_ref.json"))["products"]
    ab = o["act"][0]
    out = []
    for m, c in ACT.items():
        r = _sum(ref_lv, c, lambda d, k: d.get(k))
        if r and m in ab and r > 1:
            out.append(("activity", m, c, float(ab[m]) / UNIT.get(m, 1.0), r))
    # growth 2017 -> 2030 where the units differ: the model counts census heads (CAPREG HERD; its BULL is CAPRI's
    # low-intensity bull herd, its HFRS the fattening heifers, PIGF and BROI places), CAPRI's levels are
    # activity levels (animals fattened a year); the growth rates are comparable
    try:
        import pandas as _pd
        an = _pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv", index_col=0,
                         float_precision="round_trip")
        an = an[[not str(r).startswith("NO") for r in an.index]].sum()
        l17 = {}
        for line in open(ROOT / "capri_data" / "validation" / "capri_eu27_levels_2017_capreg.csv").read().splitlines()[1:]:
            k, v = line.split(",")
            l17[k] = float(v)
        for m, col, c in (("BULL", "BULL", "BULF"), ("HFRS", "HEIF", "HEIF+HEIR"), ("PIGF", "PIGF", "PIGF"),
                          ("BROI", "POUL", "POUF")):
            r30 = _sum(ref_lv, c, lambda d, k: d.get(k))
            r17 = _sum(l17, c, lambda d, k: d.get(k))
            if m in ab and col in an.index and r30 and r17 and an[col] > 0:
                u = 1000.0 if m == "BROI" else 1.0   # broilers: animal_numbers in 1000s of the activity unit
                out.append(("growth 2017-2030", m, c, float(ab[m]) / (float(an[col]) * u) * 100, r30 / r17 * 100))
    except FileNotFoundError:
        pass
    bm = o.get("base_market") or {}
    prod, cons, price = bm.get("prod", {}), bm.get("cons", {}), bm.get("price", {})
    mkt_prod = capri_marketed_production() if capri_mode(o) else None
    for m, c in MKT.items():
        if mkt_prod is not None and mkt_prod.get(PROD_CODE.get(m, m)):
            # a product the supply models hand over (CAPRI's XX_SUPPLY): its marketed production; the processed
            # products (oils, cakes, dairy products, biofuels) do not pass grofNEprod and keep the block below
            c_ = PROD_CODE.get(m, m)
            if m in prod:
                out.append(("production (PROD)", m, c_, float(prod[m]), mkt_prod[c_]))
        else:
            rp = _sum(bal, c, lambda d, k: (d.get(k) or {}).get("MAPR", (d.get(k) or {}).get("GROF")))
            if rp and m in prod:
                out.append(("production", m, c, float(prod[m]), rp))
        ru = _sum(bal, c, lambda d, k: (float(d[k]["GROF"]) + float(d[k].get("IMPT", 0.0)) - float(d[k].get("EXPT", 0.0)))
                  if (d.get(k) or {}).get("GROF") is not None else
                  (sum(float((d.get(k) or {}).get(i, 0.0)) for i in USE) or None))
        if mkt_prod is not None and mkt_prod.get(PROD_CODE.get(m, m)):
            # the marketed production's use: CAPRI's PROD + IMPT - EXPT (its market use, without the seed and losses
            # its supply models keep), the same products and trade as above
            nt = _sum(bal, c, lambda d, k: (float(d[k].get("IMPT", 0.0)) - float(d[k].get("EXPT", 0.0))) if d.get(k) else None)
            ru = mkt_prod[PROD_CODE.get(m, m)] + (nt or 0.0)
            if ru and m in cons:
                out.append(("domestic use (PROD)", m, c, float(cons[m]), ru))
            continue
        if ru and m in cons:
            out.append(("domestic use", m, c, float(cons[m]), ru))
    pr = []
    for m, c in MKT.items():
        if "+" in c:
            continue
        rv = (bal.get(c) or {}).get("UVAP")
        if rv and price.get(m):
            pr.append((m, c, float(price[m]), float(rv)))
    if pr:
        defl = float(np.median([p / r for _, _, p, r in pr]))
        out += [("price (relative)", m, c, p / defl, r) for m, c, p, r in pr]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    o = load_run(a.run)
    if not o.get("base_market"):
        raise SystemExit("run has no base_market block: re-run tools/run/run_f2f_2030.py")
    out = rows(o)
    print(f"{'block':17s} {'model':6s} {'CAPRI':22s} {'model':>11s} {'CAPRI':>11s} {'dev %':>8s}")
    blocks = {}
    for b, m, c, x, r in out:
        d = (x / r - 1) * 100
        blocks.setdefault(b, []).append((abs(d), r))
        flag = "  <-- " if abs(d) > 25 else ""
        print(f"{b:17s} {m:6s} {c:22s} {x:11.1f} {r:11.1f} {d:+8.1f}{flag}")
    print()
    for b, v in blocks.items():
        ad = np.array([x for x, _ in v]); w = np.array([y for _, y in v])
        print(f"{b:17s} n={len(v):2d}  median |dev| {np.median(ad):5.1f}%   size-weighted |dev| {np.sum(ad * w) / np.sum(w):5.1f}%"
              f"   within 10%: {np.mean(ad <= 10):.0%}")
    if a.csv:
        import csv
        with open(a.csv, "w", newline="") as f:
            w_ = csv.writer(f)
            w_.writerow(["block", "model", "capri", "model_value", "capri_value", "dev_pct"])
            for b, m, c, x, r in out:
                w_.writerow([b, m, c, round(x, 3), round(r, 3), round((x / r - 1) * 100, 2)])


if __name__ == "__main__":
    main()

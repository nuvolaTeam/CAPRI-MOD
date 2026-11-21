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
                                            in a run with market.demand_calibration = "capri" (CAPRI's market calibration) the market takes
                                            the marketed production (CAPRI's grofNEprod: gross x PROD/GROF at the
                                            calibration point), so the block compares it with CAPRI's own marketed
                                            production instead: the sum over the EU's member states of
                                            DATA(ms, "Prod", product, "CAL") of sim_ini_21730
                                            (capri_data/baselines/capri_greendeal_ref/1730/market/market_prod_grof_2030.csv, prod_kt)
  market domestic use (1000 t)              GROF + IMPT - EXPT: the model's market works with gross production, so
                                            its use holds CAPRI's on-farm seed and losses (SEDF, LOSF) besides
                                            CAPRI's market use DOMM (HCOM + FEDM + SEDM + INDM + PRCM + BIOF + LOSM;
                                            DOMM + SEDF + LOSF = GROF + IMPT - EXPT, checked on barley). Until
                                            5 November 2026 the sum HCOM + FEDM + INDM + BIOF + LOSM + PRCM, which
                                            leaves out seed and on-farm use (cereals 8-10% short of the balance)
  animals in CAPRI's units                  the model's heads in each EU unit over capri_level_ratio.csv (model
                                            heads per unit of CAPRI's level) against CAPRI's EU27 level: bulls,
                                            heifers, fattened pigs and broilers (CAPRI counts animals fattened a
                                            year, the model places), calves and fattened sheep and goats; and the
                                            model's 2017 herds of the EU units the same way against CAPREG's 2017
                                            EU27 levels (capri_eu27_levels_2017_capreg.csv). Until 18 November 2026
                                            a 2017-2030 growth compared the model's EU 2030 level with its 2017 herd
                                            of all 250 units (the UK, Turkey and the Western Balkans included), and
                                            calves and fattened sheep and goats in heads
  market prices (EUR/t)                     the model's EU27 price (its two EU blocks weighted by production, by
                                            use where the EU produces none) against CAPRI's member states' market
                                            prices PMRK weighted the same way (capri_ms_market_prices_2030_ref.csv),
                                            the same money: the market works in CAPRI's 2030 prices. Until 18
                                            November 2026 against CAPRI's EU27yr19 producer unit value UVAP after a
                                            median deflator: another price (tomatoes PMRK 820, UVAP 465 EUR/t) and
                                            an aggregate that is not the member states' average (maize EU27yr19
                                            PMRK 163, every member state 214-220)

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
       "DCOW": "DCOW", "BCOW": "SCOW", "PIGS": "SOWS", "SHGM": "SHGM", "LAYS": "HENS"}
#: animals whose model heads are not CAPRI's level unit: compared in CAPRI's units (capri_level_ratio.csv)
ACT_RATIO = {"BULL": "BULF", "HFRS": "HEIF+HEIR", "PIGF": "PIGF", "BROI": "POUF", "CALV": "CAMF+CAFF+CAMR+CAFR",
             "SHGF": "SHGF"}
#: the model's market commodities -> CAPRI's market product of PMRK
PRICE_CODE = {"SWHE": "WHEA", "PARI": "RICE", "OLIV": "OLIO", "POUL": "POUM", "WINE": "TWIN", "MILK": "MILK",
              "CORN": "MAIZ", "SUGR": "SUGA", "BUTR": "BUTT", "SKIM": "SMIP", "WHEY": "WHEP"}
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
    """The run's market takes the marketed production (CAPRI's market calibration): every run since 8 November 2026, when the setting
    market.demand_calibration was removed with its "supply" form; a run of 6-8 November with "supply" set is not. (A
    run before 6 November 2026 has no such setting either and was in the "supply" form: not told apart here.)"""
    s = (o.get("meta") or {}).get("settings") or {}
    return str((s.get("market") or {}).get("demand_calibration", "capri")) == "capri"


def capri_marketed_production():
    """CAPRI's marketed production at the 2030 calibration point, EU27 (the member states of
    capri_data/codes/eu_market_blocks.csv), per CAPRI market product, kt."""
    import csv
    from capri_mod.data.definitions import EU_MS_BLOCK
    out = {}
    with open(ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "market" / "market_prod_grof_2030.csv", newline="") as fh:
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
    # animals whose heads are not CAPRI's level unit, in CAPRI's units: each EU unit's baseline heads over its model
    # heads per unit of CAPRI's level (capri_level_ratio.csv, CAPRI's 2017 levels; bulls and heifers are census
    # stocks, fattened pigs and broilers places, against CAPRI's animals fattened a year)
    try:
        import pandas as _pd
        from capri_mod.data.definitions import is_eu
        rat = _pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "capri_level_ratio.csv", index_col=0,
                           float_precision="round_trip")
        reg = (o.get("act_regional") or (None,))[0] or {}
        for m, c in ACT_RATIO.items():
            r30 = _sum(ref_lv, c, lambda d, k: d.get(k))
            if not r30 or m not in rat.columns:
                continue
            tot, seen = 0.0, 0
            for rg, lv in reg.items():
                if not is_eu(rg) or m not in (lv or {}):
                    continue
                q = rat.at[rg, m] if rg in rat.index else float("nan")
                if float(lv[m] or 0.0) > 0 and q == q and q > 0:
                    tot += float(lv[m]) / float(q)
                    seen += 1
            if seen:
                out.append(("activity (CAPRI units)", m, c, tot, r30))
        # the 2017 base the same way: the model's 2017 herds of the EU units (animal_numbers.csv) over the same ratio
        # against CAPREG's EU27 2017 levels (the sum over the member states of res_17<CC>'s LEVL)
        an = _pd.read_csv(ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv", index_col=0,
                          float_precision="round_trip")
        l17 = {}
        for line in open(ROOT / "capri_data" / "validation" / "capri_eu27_levels_2017_capreg.csv").read().splitlines()[1:]:
            k, v = line.split(",")
            l17[k] = float(v)
        for m, col, c, u in (("BULL", "BULL", "BULF", 1.0), ("HFRS", "HEIF", "HEIF+HEIR", 1.0), ("PIGF", "PIGF", "PIGF", 1.0),
                             ("BROI", "POUL", "POUF", 1000.0), ("PIGS", "PIGS", "SOWS", 1.0)):
            r17 = _sum(l17, c, lambda d, k: d.get(k))
            if not r17 or col not in an.columns or m not in rat.columns:
                continue
            tot = 0.0
            for rg in an.index:
                q = rat.at[rg, m] if rg in rat.index else float("nan")
                if is_eu(rg) and q == q and q > 0:
                    tot += float(an.at[rg, col]) * u / float(q)   # broilers: animal_numbers in 1000s of the unit
            out.append(("2017 herd (CAPRI units)", m, c, tot, r17))
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
    # market prices: CAPRI's member states' PMRK weighted by their production (by market use where the EU produces
    # none), as the model's EU27 row weights its blocks; the same money (the market works in CAPRI's 2030 prices)
    fp = ROOT / "capri_data" / "validation" / "capri_ms_market_prices_2030_ref.csv"
    if fp.exists():
        import csv as _csv
        pm = {}
        with open(fp, newline="") as fh:
            for r_ in _csv.DictReader(fh):
                pm.setdefault(r_["product"], []).append((float(r_["pmrk_eur_t"]), float(r_["grof_kt"]),
                                                         float(r_["domm_kt"])))
        for m in MKT:
            c = PRICE_CODE.get(m, m)
            v = pm.get(c)
            if not v or not price.get(m):
                continue
            wp = sum(g for _, g, _ in v)
            w = [(p_, g if wp > 0 else d) for p_, g, d in v]
            sw = sum(x for _, x in w)
            if sw > 0:
                out.append(("market price", m, c, float(price[m]), sum(p_ * x for p_, x in w) / sw))
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

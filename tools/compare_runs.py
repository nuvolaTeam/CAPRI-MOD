"""Compare 2030 Farm-to-Fork runs saved by tools/run_f2f_2030.py (and CAPRI's results).

Twenty indicators from JRC121368 (prices, herds, production, nitrogen surplus, N2O, CH4,
GHG) plus ammonia, for one or two runs; --capri adds CAPRI's figures and the mean absolute
deviation of each run from them.

Usage: python tools/compare_runs.py RUN_A.pkl [RUN_B.pkl] [--capri]
"""
import argparse
import pickle

import numpy as np

# JRC121368 (EUR 30317 EN) Farm-to-Fork combined scenario, EU27, % change from baseline
CAPRI = {"cereal price": 8, "oilseed price": 11, "veg+perm price": 15, "beef price": 24, "pork price": 43,
         "poultry price": 18, "milk price": 1.5, "dairy cows": -10, "beef animals": -18, "pigs": -14.5,
         "poultry": -16.5, "sheep+goats": -9.5, "cereals prod": -15, "oilseeds prod": -15.5, "veg+perm prod": -12,
         "N surplus": -33.5, "fertiliser N2O": -40.4, "enteric CH4": -14.6, "manure CH4": -12.2, "GHG total": -14.8,
         "ammonia": -33.0, "beef production": -14.0, "manure N2O": -3.2}


def _producer_prices():
    import csv
    from pathlib import Path
    f = Path(__file__).resolve().parents[1] / "capri_data" / "2017" / "market" / "producer_prices.csv"
    try:
        return {r[""]: float(r["price"]) for r in csv.DictReader(open(f))}
    except Exception:
        return {}


_PP = _producer_prices()


def indicators(o):
    p = o["prices"]
    g = lambda cs: np.mean([p[c] for c in cs if c in p]) * 100
    ob0 = o["out"][0]

    def gv(cs):
        """Price index weighted by base production value (CAPRI's aggregates are value-weighted;
        an unweighted mean let soybeans, 9% of EU oilseed output, carry a third of the index)."""
        w = {c: float(ob0.get(c, 0.0)) * _PP.get(c, 0.0) for c in cs if c in p}
        tw = sum(w.values())
        return sum(p[c] * w[c] for c in w) / tw * 100 if tw > 0 else g(cs)
    out = {"cereal price": gv(["SWHE", "BARL", "CORN"]), "oilseed price": gv(["RAPE", "SUNF", "SOYA"]),
           "veg+perm price": g(["TOMA", "OVEG", "APPL", "OFRU", "CITR", "OLIV", "WINE"]),
           "beef price": g(["BEEF"]), "pork price": g(["PORK"]), "poultry price": g(["POUL"]), "milk price": g(["MILK"])}
    ab, as_ = o["act"]
    for lab, acts in [("dairy cows", ["DCOW"]), ("beef animals", ["BULL", "BCOW", "HFRS", "CALV"]),
                      ("pigs", ["PIGS", "PIGF"]), ("poultry", ["BROI", "LAYS"]), ("sheep+goats", ["SHGP"])]:
        out[lab] = (sum(as_.get(x, 0) for x in acts) / sum(ab.get(x, 0) for x in acts) - 1) * 100
    ob, os_ = o["out"]
    for lab, cs in [("cereals", ["SWHE", "DWHE", "BARL", "CORN", "OCER", "PARI"]), ("oilseeds", ["RAPE", "SUNF", "SOYA"]),
                    ("veg+perm", ["TOMA", "OVEG", "APPL", "OFRU", "CITR", "OLIV", "WINE", "TAGR"])]:
        out[lab + " prod"] = (sum(os_.get(x, 0) for x in cs) / sum(ob.get(x, 0) for x in cs) - 1) * 100
    if o.get("prod"):
        pb, ps = o["prod"]
        if pb.get("BEEF"):
            out["beef production"] = (ps["BEEF"] / pb["BEEF"] - 1) * 100
    eb, es = o["environmental"]
    for lab, c in [("N surplus", "n_surplus"), ("fertiliser N2O", "ghg_soil_n2o"), ("enteric CH4", "ghg_enteric"),
                   ("manure CH4", "ghg_manure_ch4"), ("GHG total", "ghg_total"), ("ammonia", "nh3_total"),
                   ("manure N2O", "ghg_manure_n2o")]:
        if lab == "GHG total" and "ghg_non_co2" in eb and "ghg_non_co2" in es:
            c = "ghg_non_co2"            # JRC121368's figure is non-CO2 GHG (Sprint 9s; older runs: all items)
        if c in eb:
            out[lab] = (es[c].sum() / eb[c].sum() - 1) * 100
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--capri", action="store_true")
    a = ap.parse_args()
    objs = [pickle.load(open(f, "rb")) for f in a.runs]
    res = [indicators(o) for o in objs]
    heads = [f"run{i + 1}" for i in range(len(res))] + (["CAPRI"] if a.capri else [])
    print(f"{'':16s} " + " ".join(f"{h:>8s}" for h in heads) + (f" {'B - A':>8s}" if len(res) == 2 else ""))
    for k in res[0]:
        vals = [r.get(k, float("nan")) for r in res]
        row = " ".join(f"{v:+8.1f}" for v in vals)
        if a.capri:
            row += f" {CAPRI.get(k, float('nan')):+8.1f}"
        if len(res) == 2:
            row += f" {vals[1] - vals[0]:+8.1f}"
        print(f"{k:16s} {row}")
    for i, o in enumerate(objs):
        print(f"run{i + 1}: {a.runs[i]} | {o.get('meta')}")
    # adoption vs JRC121368 Table 17 (baseline -> Farm-to-Fork, % adoption rate)
    groups = [("nitrification inhibitors (incl. combinations)", "fert", ("NITR_INH", "GComTN", "GComVN"), (0, 18)),
              ("precision farming (incl. variable rate)", "fert", ("PRECFARM", "VRT_L", "VRT_M", "VRT_H", "VarRTech_X", "VRT_SRUC"), (0, 35)),
              ("nitrification inhibitors on manure", "fert", ("NITR_INH_MAN",), None),
              ("fertiliser timing", "fert", ("FERTTIME",), None),
              ("low-emission housing", "amm", ("LowEmHous",), (12, 12)),
              ("covered manure storage (incl. with air purif.)", "amm", ("CovStorHigh", "CovStorLow", "AirPurCovHigh", "AirPurCovLow"), (14, 34)),
              ("air purification (incl. with cover)", "amm", ("AirPur", "AirPurCovHigh", "AirPurCovLow"), (0, 10)),
              ("acidification", "amm", ("ManAcid",), None),
              ("low-emission spreading", "amm", ("AmmAppLE", "AmmAppHE"), None)]
    if any(o.get("adoption") for o in objs):
        print("\nadoption rate, % (baseline -> 2030 Farm-to-Fork; JRC121368 Table 17)")
        print(f"{'':50s} " + " ".join(f"{h:>13s}" for h in heads))
        for lab, kind, keys, capri in groups:
            cells = []
            for o in objs:
                vals = []
                for key in ("adoption_base", "adoption"):
                    ad = o.get(key)
                    if not ad:
                        vals.append(float("nan")); continue
                    d = ad[0] if kind == "fert" else ad[1]
                    vals.append(100 * sum(d.get(k, 0.0) for k in keys))
                cells.append(f"{vals[0]:5.1f} ->{vals[1]:5.1f}")
            if a.capri:
                cells.append(f"{capri[0]:5.0f} ->{capri[1]:5.0f}" if capri else f"{'-':>13s}")
            print(f"{lab:50s} " + " ".join(f"{c:>13s}" for c in cells))
        cells = []
        for o in objs:
            cc = o.get("cover_crops") or {}
            el = float(cc.get("eligible", 0.0) or 0.0)
            cells.append(f"{100 * cc['base'] / el:5.1f} ->{100 * cc['scenario'] / el:5.1f}" if el > 0 else f"{'-':>13s}")
        if a.capri:
            cells.append(f"{23:5.0f} ->{32:5.0f}")
        print(f"{'catch crops / winter cover (% of eligible area)':50s} " + " ".join(f"{c:>13s}" for c in cells))
        cells = []
        for o in objs:
            ds_ = o.get("dairy_split") or {}
            cw = float(ds_.get("cows", 0.0) or 0.0)
            cells.append(f"{50.0:5.1f} ->{100 * (0.5 * cw + float(ds_.get('low_shift', 0.0))) / cw:5.1f}" if cw > 0 else f"{'-':>13s}")
        if a.capri:
            cells.append(f"{'-':>13s}")
        print(f"{'low-yield dairy cows, DCOL (% of dairy cows)':50s} " + " ".join(f"{c:>13s}" for c in cells))
        for a_, lab_ in (("BULL", "low-intensity bulls, BULL (% of bull stalls)"), ("HFRS", "low-intensity heifers, HEIL (% of heifer stalls)")):
            cells = []
            for o in objs:
                cs_ = (o.get("cattle_split") or {}).get(a_) or {}
                hb, hs = float(cs_.get("heads_base", 0.0) or 0.0), float(cs_.get("heads", 0.0) or 0.0)
                cells.append(f"{100 * float(cs_.get('low_base', 0.0)) / hb:5.1f} ->{100 * float(cs_.get('low', 0.0)) / hs:5.1f}"
                             if hb > 0 and hs > 0 else f"{'-':>13s}")
            if a.capri:
                cells.append(f"{'-':>13s}")
            print(f"{lab_:50s} " + " ".join(f"{c:>13s}" for c in cells))
        for opt_, lab_, cap_ in (("genet_yld", "higher milk yield (% of dairy cows)", (0, 15)),
                                 ("genet_eff", "higher ruminant efficiency (% of non-dairy ruminants)", (5, 9))):
            cells = []
            for o in objs:
                g_ = (o.get("genetics") or {}).get(opt_) or {}
                h_ = float(g_.get("heads", 0.0) or 0.0)
                cells.append(f"{0.0:5.1f} ->{100 * float(g_.get('adopting', 0.0)) / h_:5.1f}" if h_ > 0 else f"{'-':>13s}")
            if a.capri:
                cells.append(f"{cap_[0]:5.0f} ->{cap_[1]:5.0f}")
            print(f"{lab_:50s} " + " ".join(f"{c:>13s}" for c in cells))
        cells = []
        for o in objs:
            ln = o.get("lownfeed") or {}
            mn_ = float(ln.get("manure_n", 0.0) or 0.0)
            cells.append(f"{0.0:5.1f} ->{100 * float(ln.get('adopting_n', 0.0)) / mn_:5.1f}" if mn_ > 0 else f"{'-':>13s}")
        if a.capri:
            cells.append(f"{0:5.0f} ->{0:5.0f}")
        print(f"{'low nitrogen feed (% of manure N)':50s} " + " ".join(f"{c:>13s}" for c in cells))
        # JRC121368 Table 17 (Farm-to-Fork): linseed 0 -> 0, nitrate 0 -> 7 (maximum 27, 44)
        for opt_, lab_, cap_ in (("LINE_Tot", "feed additive linseed (% of cattle heads)", (0, 0)),
                                 ("Nitr_Tot", "feed additive nitrate (% of cattle heads)", (0, 7))):
            cells = []
            for o in objs:
                g_ = (o.get("supplements") or {}).get(opt_) or {}
                h_ = float(g_.get("heads", 0.0) or 0.0)
                cells.append(f"{0.0:5.1f} ->{100 * float(g_.get('adopting', 0.0)) / h_:5.1f}" if h_ > 0 else f"{'-':>13s}")
            if a.capri:
                cells.append(f"{cap_[0]:5.0f} ->{cap_[1]:5.0f}")
            print(f"{lab_:50s} " + " ".join(f"{c:>13s}" for c in cells))
        cells = []
        for o in objs:
            hs = o.get("histosol") or {}
            el = float(hs.get("eligible", 0.0) or 0.0)
            cells.append(f"{0.0:5.1f} ->{100 * float(hs.get('fallow', 0.0)) / el:5.1f}" if el > 0 else f"{'-':>13s}")
        if a.capri:
            cells.append(f"{2:5.0f} ->{9:5.0f}")
        print(f"{'fallowing histosols (% of histosol area)':50s} " + " ".join(f"{c:>13s}" for c in cells))
    if a.capri:
        for i, r in enumerate(res):
            d20 = [abs(r[k] - CAPRI[k]) for k in CAPRI if k not in ("ammonia", "beef production", "manure N2O") and k in r]
            d21 = [abs(r[k] - CAPRI[k]) for k in CAPRI if k not in ("beef production", "manure N2O") and k in r]
            print(f"run{i + 1}: mean absolute deviation from CAPRI - 20 indicators {np.mean(d20):.2f}, with ammonia {np.mean(d21):.2f}")


if __name__ == "__main__":
    main()

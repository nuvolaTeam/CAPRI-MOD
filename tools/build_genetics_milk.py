"""Milk-yield potential of CAPRI's breeding option genet_yld (envind/breeding.gms l. ~70-85).

TOP(act) = mean projected 2030 milk yield (COMI) of DK, PT, SE, FI (baseline trends)
gain(r, act) = ghgTechMYld x min(Y(r) x (1 - curb), max(0, TOP - Y(r))),  ghgTechMYld = 0.2
curbs: HR 0.6, LT 0.6, KO 0.6, SI 0.2, PL 0.2 ("convergence problems")
Aggregated to the model's DCOW (DCOL + DCOH weighted by CAPRI's 2030 activity levels) and
to NUTS 2 regions (capri8_to_nuts).
Output: capri_data/2017/abatement/mitigation/genetics_milk_yield.csv
"""
import csv, json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
MYLD = 0.2
CURB = {"HR": 0.6, "LT": 0.6, "KO": 0.6, "SI": 0.2, "PL": 0.2}


def main():
    t = pd.read_csv(M / "trends_milk_yield_1730.csv")
    Y = {(r.region, r.activity): r.milk_yield_kg for r in t.itertuples()}
    top = {a: sum(Y.get((c, a), 0) for c in ("DK000000", "PT000000", "SE000000", "FI000000")) / 4 for a in ("DCOL", "DCOH")}
    md = pd.read_csv(ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "capri_mann_days_2030.csv")
    L = {(r.region, r.activity): r.value for r in md[md.item == "LEVL"].itertuples()}
    c8 = json.load(open(ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json"))["capri8_to_nuts"]
    rows = []
    regional_ctry = {k[:2] for k in c8 if not k.endswith("000000")}
    for r8, nuts in c8.items():
        # a national code stands for all its NUTS 2 regions only where CAPRI has no
        # regional codes for that country (e.g. DK, IE); otherwise regions win
        if r8.endswith("000000") and len(nuts) > 1 and r8[:2] in regional_ctry:
            continue
        num = den = y0 = 0.0
        for a in ("DCOL", "DCOH"):
            y, lv = Y.get((r8, a)), L.get((r8, a), 0.0)
            if not y or not lv:
                continue
            curb = CURB.get(r8[:2], 0.0)
            g = MYLD * min(y * (1 - curb), max(0.0, top[a] - y))
            num += lv * g; y0 += lv * y; den += lv
        if den > 0:
            for n2 in nuts:
                rows.append([n2, r8, round(y0 / den, 1), round(num / den, 1), round(num / y0, 6)])
    # national fallback for model regions without a regional CAPRI entry (REGISTERED)
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("_mr", ROOT / "tools" / "_model_regions.py"); _mr = _iu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    def _calc(r8):
        num = den = y0 = 0.0
        for a in ("DCOL", "DCOH"):
            y, lv = Y.get((r8, a)), L.get((r8, a), 0.0)
            if not y or not lv:
                continue
            g = MYLD * min(y * (1 - CURB.get(r8[:2], 0.0)), max(0.0, top[a] - y))
            num += lv * g; y0 += lv * y; den += lv
        return (round(y0 / den, 1), round(num / den, 1), round(num / y0, 6)) if den > 0 else None
    have = {r[0] for r in rows}
    for reg in _mr.model_regions():
        if reg not in have:
            v = _calc(_mr.national_code(reg))
            if v:
                rows.append([reg, _mr.national_code(reg)] + list(v))
    with open(M / "genetics_milk_yield.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["region", "capri_region", "milk_yield_kg", "gain_kg", "rel_gain"]); w.writerows(rows)
    return top, rows


if __name__ == "__main__":
    top, rows = main()
    print("TOP:", {k: round(v) for k, v in top.items()}, "|", len(rows), "regions")

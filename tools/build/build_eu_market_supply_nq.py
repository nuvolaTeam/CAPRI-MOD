"""CAPRI's market supply functions of the EU member states (arm/market_model.gms ProdNQ_), every product, from CAPRI's
own terms, and the member states' production at CAPRI's calibration point.

Two uses in the market (capri_mod/market/supply.py):
- the EU products no supply model produces (EU_MARKET_SUPPLY: other vegetable oils OTHO, the fish products FFIS,
  SFIS, OAQU): their EU supply is the member states' ProdNQ_, as in CAPRI;
- the part of the EU outside a run on a subset of regional units (KNOWN_ISSUES K83): CAPRI keeps a country switched
  off in the market with its ProdNQ_ (it leaves RMSSUP, capmod/create_sim_ini_gdx.gms l. 73).

ProdNQ_ (market_model.gms l. 1529-1560): v_prodQuant(RMS, x) = p_cnstNQSupp + sum_y p_hessNQSupp(RMS, x, y) x
v_prodPrice(RMS, y) / v_prodPrice(RMS, "INPE"). The change from the calibration point is sum_y h_xy x (the change of
y's producer price) / INPE. The market's supply functions work in price ratios, so each term is written as h_xy x
PPRI0_y / INPE: kt per unit change of y's price ratio (the member state's producer price moves with its market price,
PPri_ with a fixed margin). INPE is the price of the non-agricultural good in the simulation year: the calibration file
stores 1, which CAPRI's market model overwrites with the inflation factor before the simulation (arm/market1.gms;
1.019^13 = 1.2772 in 2030), taken from CAPRI's 2030 market dump as tools/build/build_processing_nq.py does. With it the
terms give CAPRI's p_elasSupp at the calibration point (FR other oils 0.979 against 0.979). INPE does not move in a
simulation and is left out as a price.

The Hessian is completed as CAPRI's market model completes it on loading (tools/lib/_capri_nq.py, arm/market1.gms
l. 539-574), the member states being RMSSUP. Rows (x): the model's market commodities and raw milk (MILK); columns
(y): the same, written with the model code empty where the model has no such price (the young animals, which carry
only a placeholder own term in CAPRI's export; the market holds such columns at their calibration value, as the
non-EU functions do, build_noneu_market_supply_nq.py). Until 31 October 2026 the file held OTHO, FFIS, SFIS and OAQU
only, and y in CAPRI's code: the market, looking y up among the model's commodities, dropped the 143 terms on MAIZ,
WHEA, SUGA, OLIO, POUM, RICE and TWIN (0.8% of their absolute sum).

Sources: CAPRI's NQ supply Hessian at the calibration point (elas_2_1730defaulta.csv: p_hessNQSupp at CAL), the
member states' producer prices and production there (data_market_1730defaulta.csv: Data_CAL PPRI, PROD at CAL) and
the 2030 price of the non-agricultural good (markmarket_greendeal_1730et_base_1717.txt: PPRI INPE 2030); the member
states: CAPRI's EU trade blocks (shared/eu_market_blocks.csv); the codes: codes/model_commodities.csv.

Output:
  capri_data/2017/market/eu_market_supply_nq.csv    ms, x, y, capri_x, capri_y, h, ppri_y, inpe, h_ratio
                                                     (x, y model codes; y empty: no model price, held)
  capri_data/2017/market/eu_market_supply_base.csv  ms, x, capri_x, prod_cal (1000 t, Data_CAL PROD at CAL)

    python tools/build/build_eu_market_supply_nq.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build")]
from capri_mod.csvio import read_csv, to_csv  # noqa: E402
from _capri_nq import read_supply_hessian  # noqa: E402
from _model_regions import EU_MS  # noqa: E402  (shared/eu_market_blocks.csv)
from build_noneu_market_supply_nq import ELAS, DATA, DUMP, num, read_param  # noqa: E402

OUT = ROOT / "capri_data" / "2017" / "market" / "eu_market_supply_nq.csv"
OUT_BASE = ROOT / "capri_data" / "2017" / "market" / "eu_market_supply_base.csv"


def main():
    com = read_csv(ROOT / "capri_data" / "codes" / "model_commodities.csv")
    to_model = dict(zip(com.capri_code, com.code))
    to_model["MILK"] = "MILK"                                        # raw milk: the member state's dairy block
    ms_eu = set(EU_MS)
    hess = read_supply_hessian(ELAS, lambda r: r in ms_eu, ms_eu)
    terms = sorted((ms, x, y, h) for (ms, x, y), h in hess.items() if x in to_model and y != "INPE")
    dp = re.compile(r"^'([^']*)'\.'(PPRI|PROD)'\.'([^']*)'\.'CAL'\s+(\S+)")
    data = {(r, it, p): num(v) for r, it, p, v in read_param(DATA, "Data_CAL", dp, lambda m: m.group(1) in ms_eu)}
    inpe = {}
    p3 = re.compile(r"^'([^']+)'\.''\.'PPRI'\.'INPE'\.'2030'\s+(\S+)")
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PPRI'.'INPE'" in line:
                m = p3.match(line)
                if m:
                    inpe[m.group(1)] = num(m.group(2))
    rows, missing = [], set()
    for ms, x, y, h in terms:
        if not inpe.get(ms):
            missing.add((ms, "INPE 2030"))
            continue
        p = data.get((ms, "PPRI", y), 0.0)
        ym = to_model.get(y, "")
        if not p or not ym:
            # a column without a model price (the young animals) or without CAPRI's price: held, its term not used
            rows.append((ms, to_model[x], "", x, y, h, p, inpe[ms], 0.0))
            continue
        rows.append((ms, to_model[x], ym, x, y, h, p, inpe[ms], h * p / inpe[ms]))
    if missing:
        raise SystemExit(f"no CAPRI 2030 INPE for {sorted(missing)[:10]}")
    out = pd.DataFrame(rows, columns=["ms", "x", "y", "capri_x", "capri_y", "h", "ppri_y", "inpe", "h_ratio"]
                       ).sort_values(["ms", "capri_x", "capri_y"])
    to_csv(out, OUT, index=False)
    base = sorted((ms, to_model[x], x, data[(ms, "PROD", x)]) for ms in ms_eu for x in sorted(to_model)
                  if data.get((ms, "PROD", x)))
    to_csv(pd.DataFrame(base, columns=["ms", "x", "capri_x", "prod_cal"]), OUT_BASE, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} terms, {out.ms.nunique()} member states, "
          f"{out.capri_x.nunique()} products ({int((out.y == '').sum())} held); "
          f"{OUT_BASE.name}: {len(base)} member state x product production values")


if __name__ == "__main__":
    main()

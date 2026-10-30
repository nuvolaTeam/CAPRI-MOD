"""CAPRI's market supply functions of the EU products that no supply model produces (arm/market_model.gms ProdNQ_):
other vegetable oils (OTHO) and the fish products (FFIS, SFIS, OAQU), per EU member state, from CAPRI's own terms.

ProdNQ_ (market_model.gms l. 1529-1560): v_prodQuant(RMS, x) = p_cnstNQSupp + sum_y p_hessNQSupp(RMS, x, y) x
v_prodPrice(RMS, y) / v_prodPrice(RMS, "INPE"). For these products the constant is not recalibrated to a supply model
(simu_calibration_to_supply.gms recalibrates only the supply models' products), so the change from the calibration
point is sum_y h_xy x (the change of y's producer price) / INPE. The market's supply functions work in price ratios
(capri_mod/market/supply.py), so each term is written as h_xy x PPRI0_y / INPE0: kt per unit change of y's price
ratio (the member state's producer price moves with its market price, PPri_ with a fixed margin). INPE is the price
of the non-agricultural good in the simulation year: the calibration file stores 1, which CAPRI's market model
overwrites with the inflation factor before the simulation (arm/market1.gms; 1.019^13 = 1.2772 in 2030), taken from
CAPRI's 2030 market dump as tools/build/build_processing_nq.py does. With it the terms give CAPRI's p_elasSupp at the
calibration point (FR other oils 0.979 against 0.979). INPE does not move in a simulation and is left out as a price.

Sources: CAPRI's NQ supply Hessian at the calibration point (elas_2_1730defaulta.csv: p_hessNQSupp at CAL), the
member states' producer prices there (data_market_1730defaulta.csv: Data_CAL PPRI at CAL) and the 2030 price of the
non-agricultural good (markmarket_greendeal_1730et_base_1717.txt: PPRI INPE 2030).

Output: capri_data/2017/market/eu_market_supply_nq.csv  ms, x, y, capri_y, h, ppri_y, inpe, h_ratio: y the price's
product in the model's code (codes/model_commodities.csv), capri_y CAPRI's. Until 31 October 2026 y was CAPRI's code,
which the market looks up among the model's: the 143 terms on MAIZ, WHEA, SUGA, OLIO, POUM, RICE and TWIN (0.8% of
the terms' absolute sum) were dropped.

    python tools/build/build_eu_market_supply_nq.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import read_csv, to_csv  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from _capri_nq import read_supply_hessian  # noqa: E402

UP = Path("/mnt/user-data/uploads")
ELAS = UP / "elas_2_1730defaulta.csv"
DATA = UP / "data_market_1730defaulta.csv"
DUMP = UP / "markmarket_greendeal_1730et_base_1717.txt"
OUT = ROOT / "capri_data" / "2017" / "market" / "eu_market_supply_nq.csv"
#: the EU products CAPRI supplies through a market supply function only (capri_mod/market/market_module.py
#: EU_MARKET_SUPPLY)
PRODUCTS = ("OTHO", "FFIS", "SFIS", "OAQU")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def main():
    ms_eu = set(read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv").capri_ms)
    # CAPRI's Hessian completed as its market model does on loading (tools/lib/_capri_nq.py: tiny terms and products
    # without ProdNQ_ deleted, made symmetric; until 29 October 2026 only the terms stored under these products' rows
    # were read, and the cross terms stored under the other product's row were missed); the member states are RMSSUP
    hess = read_supply_hessian(ELAS, lambda r: r in ms_eu, ms_eu)
    terms = sorted((ms, x, y, h) for (ms, x, y), h in hess.items() if x in PRODUCTS)
    want = {(ms, y) for ms, _, y, _ in terms}
    pp = re.compile(r"^'([^']*)'\.'PPRI'\.'([^']*)'\.'CAL'\s+(\S+)")
    price = {}
    cur = None
    with open(DATA, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("Parameter"):
                cur = line.split("(")[0].split()[1]
                continue
            if cur != "Data_CAL" or not line.startswith("'"):
                continue
            m = pp.match(line)
            if m and (m.group(1), m.group(2)) in want:
                price[(m.group(1), m.group(2))] = num(m.group(3))
    inpe = {}
    p3 = re.compile(r"^'([^']+)'\.''\.'PPRI'\.'INPE'\.'2030'\s+(\S+)")
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PPRI'.'INPE'" in line:
                m = p3.match(line)
                if m:
                    inpe[m.group(1)] = num(m.group(2))
    com = read_csv(ROOT / "capri_data" / "codes" / "model_commodities.csv")
    to_model = dict(zip(com.capri_code, com.code))
    rows = []
    missing = set()
    for ms, x, y, h in terms:
        if y == "INPE":
            continue                                  # the input price index does not move in a simulation
        p = price.get((ms, y))
        if not inpe.get(ms):
            missing.add((ms, x, "INPE 2030"))
            continue
        inpe_ = inpe[ms]
        if not p:
            missing.add((ms, x, y))
            continue
        if y not in to_model:
            missing.add((ms, x, f"{y}: no model commodity"))
            continue
        rows.append((ms, x, to_model[y], y, h, p, inpe_, h * p / inpe_))
    if missing:
        raise SystemExit(f"no CAPRI price (Data_CAL PPRI, or the 2030 PPRI INPE) or model code for {sorted(missing)[:10]}")
    out = pd.DataFrame(rows, columns=["ms", "x", "y", "capri_y", "h", "ppri_y", "inpe", "h_ratio"]).sort_values(
        ["ms", "x", "capri_y"])
    to_csv(out, OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} terms, {out.ms.nunique()} member states; "
          + ", ".join(f"{x} {int((out.x == x).sum())}" for x in PRODUCTS))


if __name__ == "__main__":
    main()

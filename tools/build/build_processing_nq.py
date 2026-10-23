"""CAPRI's processing demand functions (arm/market_model.gms ProcNQ_) per behavioural region, for the market.

CAPRI (ProcNQ_, ProcMargO_):
    PROC_x = cnst_x + sum_y H_xy z_y / P_INPE,   z_y = processing margin of oilseed y (ProcMargO_: oil and cake value
                                                   per tonne minus the seed price), or PRCA_y - Arm1 price of y
                                                   for the other processed products
with H = p_hessNQProc (normalised-quadratic profit function: cross terms among the crushed oilseeds and among the
vegetable oils, own terms for the other processed products). CAPRI re-calibrates the constant to the current point
and keeps H; so does the market (MarketModule._proc_nq_params): the processing of each product moves from the
model's base by H x the change of the margins (oilseeds) or of the prices (other products).

This extracts, from CAPRI's 2030 calibration (elas_2_1730defaulta CAL; data_market_1730defaulta Data_CAL), per
behavioural region: H (upper triangle as stored, symmetrised by the reader), processing PROC and total use
(HCON + FEED + PROC + BIOF) per product; and P_INPE, the price of the non-agricultural good, from CAPRI's 2030 market
dump (PPRI INPE 2030 = 1.019^13 = 1.2772 in every region). The calibration file stores PPri INPE = 1, but CAPRI's
market model overwrites it with the inflation factor before the simulation (arm/market1.gms: PPri INPE CUR =
p_inflationFactor = p_infl^(Y - BAS)), and ProcNQ_ divides by that CUR value - as the dairy and biofuel blocks do.

Outputs (capri_data/2017/market/):
  processing_nq_hessian.csv  rms, model_region, x, y, h          (CAPRI products mapped to model commodities)
  processing_nq_base.csv     rms, model_region, commodity, proc_kt, use_kt, inpe

    python tools/build/build_processing_nq.py
"""
from __future__ import annotations
import re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ELAS = Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv")
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
DUMP = Path("/mnt/user-data/uploads/markmarket_greendeal_1730et_base_1717.txt")
OUT = ROOT / "capri_data" / "2017" / "market"
EU = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
      "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}
USES = ("HCON", "FEED", "PROC", "BIOF")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def main() -> None:
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import build_bilateral_market as BM
    from recalibrate_trade_2017 import REGION_MAP
    g2m = {g: m for m, gs in BM.MODEL.items() for g in gs}
    h = []
    cur = None
    pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    for line in open(ELAS, encoding="latin-1"):
        if line.startswith("Parameter"):
            cur = line.split("(")[0].split()[1]
            continue
        if cur != "p_hessNQProc" or not line.startswith("'"):
            continue
        m = pat.match(line)
        if m:
            h.append((m.group(1), m.group(2), m.group(3), num(m.group(4))))
    regs = {r for r, _, _, _ in h}
    v = defaultdict(float)
    pat2 = re.compile(r"^'([^']*)'\.'(PROC|HCON|FEED|BIOF|PPRI)'\.'([A-Za-z]+)'\.'CAL'\s+(\S+)")
    for line in open(DATA, encoding="latin-1"):
        if not line.startswith("'"):
            continue
        m = pat2.match(line)
        if m and m.group(1) in regs:
            v[(m.group(1), m.group(2), m.group(3))] = num(m.group(4))
    inpe = {}
    pat3 = re.compile(r"^'([^']+)'\.''\.'PPRI'\.'INPE'\.'2030'\s+(\S+)")
    with open(DUMP, encoding="latin-1") as fh:
        for line in fh:
            if "'PPRI'.'INPE'" in line:
                m = pat3.match(line)
                if m:
                    inpe[m.group(1)] = num(m.group(2))
    missing = sorted(r for r in regs if r not in inpe)
    if missing:
        raise SystemExit(f"no 2030 PPRI INPE in the dump for {missing}")
    mreg = lambda r: "EU27" if (r[:2] in EU and r.endswith("000000")) else REGION_MAP.get(r, "ROW")
    rows_h = [(r, mreg(r), g2m[x], g2m[y], val) for r, x, y, val in h if x in g2m and y in g2m and val != 0.0]
    rows_b = []
    for r in sorted(regs):
        prods = {x for rr, x, _, _ in h if rr == r} | {y for rr, _, y, _ in h if rr == r}
        for p in sorted(prods):
            if p not in g2m:
                continue
            pr = v.get((r, "PROC", p), 0.0)
            use = sum(v.get((r, u, p), 0.0) for u in USES)
            rows_b.append((r, mreg(r), g2m[p], pr, use, inpe[r]))
    hh = pd.DataFrame(rows_h, columns=["rms", "model_region", "x", "y", "h"])
    bb = pd.DataFrame(rows_b, columns=["rms", "model_region", "commodity", "proc_kt", "use_kt", "inpe"])
    hh.to_csv(OUT / "processing_nq_hessian.csv", index=False, float_format="%.10g")
    bb.to_csv(OUT / "processing_nq_base.csv", index=False, float_format="%.10g")
    print(f"{len(hh)} Hessian terms in {hh.rms.nunique()} regions; {len(bb)} region-products")
    print(hh[hh.x != hh.y].groupby("x").y.apply(lambda s: sorted(set(s))).to_dict())


if __name__ == "__main__":
    main()

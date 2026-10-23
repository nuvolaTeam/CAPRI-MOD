"""CAPRI's food demand system (Generalised Leontief) per behavioural region, for the market model (October 2026).

CAPRI (arm/market_model.gms:826-916), per region and head:
    x_i = [G_i / G (Y - F) + d_i] INHA / 1000,   F = sum_i d_i p_i,   G = sum_ij b_ij sqrt(p_i p_j),
    G_i = sum_j b_ij sqrt(p_j / p_i),   p = consumer price / 1000 (EUR/kg),   Y = INCE / INHA
with the non-agricultural good INPE at a fixed price closing the budget. d = p_pdGL, b = p_pbGL (upper triangle,
symmetrised), calibrated by arm/trim_elas.gms to CAPRI's elasticities at the calibration point.

This extracts, for every region with GL parameters in CAPRI's 2030 calibration (elas_2_1730defaulta, CAL), the
parameters and the calibration point (data_market_1730defaulta Data_CAL: CPRI, HCON, INCE, INHA, and the region's
other uses for the food share), and checks that the stored parameters reproduce CAPRI's human consumption at the
calibration point.

Outputs (capri_data/2017/market/):
  gl_demand_goods.csv    rms, model_region, good, model_commodity, d, cpri, hcon, use   (use: HCON + FEED + PROC +
                         BIOF + INDM + LOSM of the good, CAL)
  gl_demand_b.csv        rms, i, j, b                                                    (i <= j as CAPRI stores)
  gl_demand_regions.csv  rms, model_region, Y, inha, max_rel_err                         (check at CAL)

    python tools/build/build_gl_demand.py
"""
from __future__ import annotations
import re, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ELAS = Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv")
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market"
EU = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
      "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}
USES = ("HCON", "FEED", "PROC", "BIOF", "INDM", "LOSM")


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def read_elas():
    d, b = defaultdict(dict), defaultdict(dict)
    cur = None
    pat = re.compile(r"^'([^']*)'\.'([^']*)'\.(?:'([^']*)'\.)?'CAL'\s+(\S+)")
    for line in open(ELAS, encoding="latin-1"):
        if line.startswith("Parameter"):
            cur = line.split("(")[0].split()[1]
            continue
        if cur not in ("p_pdGL", "p_pbGL") or not line.startswith("'"):
            continue
        m = pat.match(line)
        if not m:
            continue
        if cur == "p_pdGL" and m.group(3) is None:
            d[m.group(1)][m.group(2)] = num(m.group(4))
        elif cur == "p_pbGL" and m.group(3) is not None:
            b[m.group(1)][(m.group(2), m.group(3))] = num(m.group(4))
    return d, b


def read_data(regions):
    v = {}
    pat = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'CAL'\s+(\S+)")
    for line in open(DATA, encoding="latin-1"):
        if not line.startswith("'"):
            continue
        m = pat.match(line)
        if m and m.group(1) in regions and (m.group(2) in ("CPRI",) + USES or m.group(2) in ("INCE", "INHA")):
            v[(m.group(1), m.group(2), m.group(3))] = num(m.group(4))
    return v


def model_maps():
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import build_bilateral_market as BM
    from recalibrate_trade_2017 import REGION_MAP
    good_to_model = {}
    for mc, goods in BM.MODEL.items():
        for g in goods:
            good_to_model.setdefault(g, mc)
    return good_to_model, REGION_MAP


def main() -> None:
    d, b = read_elas()
    regions = sorted(d)
    v = read_data(set(regions))
    g2m, rmap = model_maps()
    rows_g, rows_b, rows_r = [], [], []
    for r in regions:
        goods = list(d[r])
        if not goods:
            continue
        mr = "EU27" if r[:2] in EU and r.endswith("000000") else rmap.get(r, "ROW")
        inha = v.get((r, "INHA", "LEVL"), 0.0)
        Y = v.get((r, "INCE", "LEVL"), 0.0) / inha if inha > 0 else 0.0
        idx = {g: i for i, g in enumerate(goods)}
        n = len(goods)
        B = np.zeros((n, n))
        for (i, j), x in b[r].items():
            if i in idx and j in idx:
                B[idx[i], idx[j]] = x
                B[idx[j], idx[i]] = x
                rows_b.append((r, i, j, x))
        p = np.array([v.get((r, "CPRI", g), 0.0) / 1000.0 for g in goods])
        dv = np.array([d[r][g] for g in goods])
        q = np.array([v.get((r, "HCON", g), 0.0) for g in goods])
        err = float("nan")
        if inha > 0 and np.all(p > 0):
            G = float((B * np.sqrt(np.outer(p, p))).sum())
            Gi = (B * np.sqrt(p[None, :] / p[:, None])).sum(axis=1)
            F = float(dv @ p)
            x = (Gi / G * (Y - F) + dv) * inha / 1000.0
            ok = [i for i, g in enumerate(goods) if g != "INPE" and q[i] > 1e-3]
            err = float(max(abs(x[i] - q[i]) / q[i] for i in ok)) if ok else float("nan")
        for i, g in enumerate(goods):
            use = sum(v.get((r, u, g), 0.0) for u in USES)
            rows_g.append((r, mr, g, g2m.get(g, ""), dv[i], p[i] * 1000.0, q[i], use))
        rows_r.append((r, mr, Y, inha, err))
    pd.DataFrame(rows_g, columns=["rms", "model_region", "good", "model_commodity", "d", "cpri", "hcon", "use"]) \
        .to_csv(OUT / "gl_demand_goods.csv", index=False, float_format="%.10g")
    pd.DataFrame(rows_b, columns=["rms", "i", "j", "b"]).to_csv(OUT / "gl_demand_b.csv", index=False, float_format="%.10g")
    reg = pd.DataFrame(rows_r, columns=["rms", "model_region", "Y", "inha", "max_rel_err"])
    reg.to_csv(OUT / "gl_demand_regions.csv", index=False, float_format="%.10g")
    print(f"{len(reg)} regions, {len(rows_g)} region-goods, {len(rows_b)} b terms; worst reproduction of CAPRI's food "
          f"demand at CAL: {reg.max_rel_err.max():.2e}")
    print(reg.groupby("model_region").rms.count().to_dict())


if __name__ == "__main__":
    main()

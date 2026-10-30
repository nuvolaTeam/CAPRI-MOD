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
  gl_demand_goods.csv    rms, model_region, good, model_commodity, d, cpri, hcon, use, arm1p   (use: HCON + FEED +
                         PROC + BIOF + INDM + LOSM of the good, CAL; arm1p: the Armington price ARM1P of the good in
                         the region's market region RM (RMS_TO_RM), CAL: CAPRI's consumer price moves with it,
                         Cpri_ = Arm1P + margins, market_model.gms l. 3032-3039)
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

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
ELAS = Path("/mnt/user-data/uploads/elas_2_1730defaulta.csv")
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from _model_regions import EU_MS2 as _EU_FROM_DATA  # noqa: E402  (capri_data/shared/eu_market_blocks.csv)
EU = set(_EU_FROM_DATA)                                  # CAPRI's EU member states, from the data
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
        if m and (m.group(1) in regions and (m.group(2) in ("CPRI",) + USES or m.group(2) in ("INCE", "INHA"))
                  or m.group(2) == "ARM1P"):
            v[(m.group(1), m.group(2), m.group(3))] = num(m.group(4))
    return v


def model_maps():
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import build_bilateral_market as BM
    from recalibrate_trade_2017 import REGION_MAP
    good_to_model = {}
    for mc, goods in BM.MODEL.items():
        for g in goods:
            good_to_model.setdefault(g, mc)
    return good_to_model, REGION_MAP


#: CAPRI's mapping of behavioural regions to market regions (set RMS_TO_RM of CAPRI's own instantiation,
#: capri_reference/sets/simini_21730, tools/build/build_capri_sets_reference.py), kept as model input
RMS_TO_RM_SRC = ROOT / "capri_reference" / "sets" / "simini_21730" / "RMS_TO_RM.csv"
RMS_TO_RM = ROOT / "capri_data" / "shared" / "rms_to_rm.csv"


def rms_to_rm() -> dict:
    if RMS_TO_RM_SRC.exists():
        m = _read_csv(RMS_TO_RM_SRC)[["d0", "d1"]].rename(columns={"d0": "rms", "d1": "rm"})
        m.to_csv(RMS_TO_RM, index=False)
        # CAPRI's behavioural regions (set RMS), for the builders that read CAPRI's data rows per region
        _read_csv(RMS_TO_RM_SRC.parent / "RMS.csv")[["d0"]].rename(columns={"d0": "rms"}) \
            .to_csv(RMS_TO_RM.parent / "rms.csv", index=False)
    m = _read_csv(RMS_TO_RM)
    return dict(zip(m.rms, m.rm))


def main() -> None:
    d, b = read_elas()
    r2m = rms_to_rm()
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
            rm = r2m.get(r, r)                      # a region that is its own market region (RM_AND_RMS)
            rows_g.append((r, mr, g, g2m.get(g, ""), dv[i], p[i] * 1000.0, q[i], use, v.get((rm, "ARM1P", g), float("nan"))))
        rows_r.append((r, mr, Y, inha, err))
    pd.DataFrame(rows_g, columns=["rms", "model_region", "good", "model_commodity", "d", "cpri", "hcon", "use", "arm1p"]) \
        .to_csv(OUT / "gl_demand_goods.csv", index=False)
    pd.DataFrame(rows_b, columns=["rms", "i", "j", "b"]).to_csv(OUT / "gl_demand_b.csv", index=False)
    reg = pd.DataFrame(rows_r, columns=["rms", "model_region", "Y", "inha", "max_rel_err"])
    reg.to_csv(OUT / "gl_demand_regions.csv", index=False)
    print(f"{len(reg)} regions, {len(rows_g)} region-goods, {len(rows_b)} b terms; worst reproduction of CAPRI's food "
          f"demand at CAL: {reg.max_rel_err.max():.2e}")
    print(reg.groupby("model_region").rms.count().to_dict())


if __name__ == "__main__":
    main()

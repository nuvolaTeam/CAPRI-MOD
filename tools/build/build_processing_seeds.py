"""CAPRI's oilseed crushing per behavioural region, for the market's processing block (arm/market_model.gms ProcMargO_,
ProcNQ_, ProcO_, procYield_).

CAPRI, per behavioural region RMS and oilseed SED with its oil OIL and cake CAK:
    margin   v_procMarg(SED) = - v_arm1Price(RM, SED) + PRCY_CAK x v_prodPrice(CAK) + PRCY_OIL x v_prodPrice(OIL)
    crush    PROC(SED) = cnst + sum_y H(SED, y) x margin_y / P_INPE            (ProcNQ_; H in processing_nq_hessian.csv)
    output   PROD(OIL) = PROC(SED) x yield(OIL), PROD(CAK) = PROC(SED) x yield(CAK)   (ProcO_)
    yields   CET in the oil/cake producer price ratio with p_rhoProc = 0.01 (arm/market1.gms l. 185), corrected to keep
             the calibration point's mass balance (procYield_)
The prices enter as changes from the calibration point: ARM1P of the seed in the region's market region (RMS_TO_RM),
PPRI of the oil and cake in the behavioural region.

Output: capri_data/2017/market/processing_seeds.csv
    rms, model_region, seed, oil, cake, proc_kt, arm1p_seed, prcy_oil, prcy_cake, ppri_oil, ppri_cake, prod_oil_kt,
    prod_cake_kt, rho_proc
from CAPRI's 2030 calibration (data_market_1730defaulta, Data_CAL, 'CAL'). A region is listed where CAPRI crushes the
seed (PROC > 0) and produces its oil or cake.

    python tools/build/build_processing_seeds.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = Path("/mnt/user-data/uploads/data_market_1730defaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "market" / "processing_seeds.csv"
CHAINS = {"RAPE": ("RAPO", "RAPC"), "SUNF": ("SUNO", "SUNC"), "SOYA": ("SOYO", "SOYC")}
RHO_PROC = 0.01                       # arm/market1.gms l. 185: p_rhoProc(RMS,SED) = 0.01
EU = {"AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
      "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}


def num(s: str) -> float:
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def main() -> None:
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build")]
    from recalibrate_trade_2017 import REGION_MAP
    goods = set(CHAINS) | {x for oc in CHAINS.values() for x in oc}
    pat = re.compile(r"^'([^']*)'\.'(PROC|PROD|PRCY|PPRI|ARM1P)'\.'([A-Z]+)'\.'CAL'\s+(\S+)")
    v = {}
    for line in open(DATA, encoding="latin-1"):
        if not line.startswith("'"):
            continue
        m = pat.match(line)
        if m and m.group(3) in goods:
            v[(m.group(1), m.group(2), m.group(3))] = num(m.group(4))
    r2m = pd.read_csv(ROOT / "capri_data" / "shared" / "rms_to_rm.csv")      # CAPRI's RMS_TO_RM
    r2m = dict(zip(r2m.rms, r2m.rm))
    # CAPRI's behavioural regions (set RMS; aggregates such as EU, MER or the trade blocks also carry data rows)
    rms_set = set(pd.read_csv(ROOT / "capri_data" / "shared" / "rms.csv")["rms"])
    rms_all = sorted({r for (r, it, g) in v if it == "PROC" and r in rms_set})
    mreg = lambda r: "EU27" if (r[:2] in EU and r.endswith("000000")) else REGION_MAP.get(r, "ROW")
    rows = []
    for r in rms_all:
        for s, (o, c) in CHAINS.items():
            q = v.get((r, "PROC", s), 0.0)
            po, pc = v.get((r, "PROD", o), 0.0), v.get((r, "PROD", c), 0.0)
            if q <= 0 or (po <= 0 and pc <= 0):
                continue
            rows.append(dict(rms=r, model_region=mreg(r), seed=s, oil=o, cake=c, proc_kt=q,
                             arm1p_seed=v.get((r2m.get(r, r), "ARM1P", s), float("nan")),
                             prcy_oil=v.get((r, "PRCY", o), 0.0), prcy_cake=v.get((r, "PRCY", c), 0.0),
                             ppri_oil=v.get((r, "PPRI", o), 0.0), ppri_cake=v.get((r, "PPRI", c), 0.0),
                             prod_oil_kt=po, prod_cake_kt=pc, rho_proc=RHO_PROC))
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False, float_format="%.10g", lineterminator="\n")
    bad = t[~(t.arm1p_seed > 0)]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(t)} region-seeds in {t.rms.nunique()} regions; "
          f"without a seed Armington price: {len(bad)}")
    # check: PRCY reproduces CAPRI's oil and cake output at the calibration point
    err = ((t.proc_kt * t.prcy_oil - t.prod_oil_kt).abs() / t.prod_oil_kt.where(t.prod_oil_kt > 0)).max()
    print(f"max relative error of PROC x PRCY against PROD (oil): {err:.2e}")


if __name__ == "__main__":
    main()

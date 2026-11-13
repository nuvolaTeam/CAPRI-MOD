"""CAPRI's land-use-change estimation of the market model outside the EU (luc_market: arm/market_model.gms
LinkLuWithShares_, luClassInitial_, luClassFinal_, FocLUC_, derivativeOfGammaLUC_, l. 1918-1990; on with REPORTS_ENV,
capmod/set_global_variables.gms l. 395). Per non-EU market region without supply models, the 36 land transitions
between CAPRI's six UNFCCC land classes (FORE, ARTIF, CROP, WETLND, GRSLND, RESLND) are the mode of a gamma posterior
given the initial land per class (the initial land-use year) and the final land per class (the market's land types
at the simulated point, linked to the classes by the shares p_shFstInSecMrk).

Sources: the project lead's sim_ini_21730 (capri_sources/reference/simini/simini_21730, tools/build/
build_simini_reference.py): p_lucPriorMrk (alpha, beta, lower, upper, mode, initialLandUse and the years "observed"
and "initialLandUse" of World/calyea), p_shFstInSecMrk, DATA (CAL land of the market's land types, INLW at CUR, the
transitions at CAL) and CAPRI's sets (capri_sources/reference/sets/simini_21730: LUCpos, luClass, luc_from_luClass,
luc_to_luClass). The annual factor of the off-diagonal transitions is the observed year minus the initial year
(arm/prep_market.gms l. 178: 2030 - 2025 = 5 in this run, the initial land use read from the 2025 baseline file,
nondefaultLUfileMrk); the diagonal's is 1. sim_ini's own p_lucAnnualFac (1 everywhere) is written before
prep_market sets it and is not used.

Outputs (capri_data/2017/market/):
  luc_market_priors.csv   rms, lucpos, from_class, to_class, annual_factor, alpha, beta, lower, upper, level_cal
                          (level_cal: CAPRI's transition at its 2030 calibration point, DATA LEVL CAL; the start
                          point, as CAPRI's v_lucpos.l = DATA CUR, arm/define_land_params.gms l. 1098)
  luc_market_classes.csv  rms, luclass, initial_kha (p_lucPriorMrk initialLandUse), inlw_kha (DATA INLW LEVL CUR)
  luc_market_shares.csv   rms, target, source, share (p_shFstInSecMrk: the land classes and ARAC, GRAS, TGRS as
                          shares of the market's land types)

Check (the build stops otherwise): capri_mod/market/luc.py solved at CAPRI's CAL land reproduces CAPRI's CAL
transitions in every region (relative to max(|level|, 1e-3), at most 1e-4: CONOPT's own tolerance in the data), the
initial and final balances hold, and the final land per class from the shares equals CAPRI's DATA CAL of the class.

    python tools/build/build_luc_market.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib",)]
from paths import REFERENCE  # noqa: E402
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

SIM = REFERENCE / "simini" / "simini_21730"
SETS = REFERENCE / "sets" / "simini_21730"
MKT = ROOT / "capri_data" / "2017" / "market"
PRIORS, CLASSES, SHARES = MKT / "luc_market_priors.csv", MKT / "luc_market_classes.csv", MKT / "luc_market_shares.csv"
#: the market's land types the classes are linked from (luMrkMod's own levels; LandSupplyMNL_'s six and INLW)
LAND_TYPES = ("FORE", "ARTIF", "OLND", "TCRP", "FODFAL", "FRUN", "INLW")
#: CAPRI's tolerance for the check against its calibration point (CONOPT's solution in the data)
CHECK_TOL = 1e-4


def main():
    P = read_csv(SIM / "p_lucPriorMrk.csv.gz", keep_default_na=False)
    SH = read_csv(SIM / "p_shFstInSecMrk.csv.gz", keep_default_na=False)
    D = read_csv(SIM / "DATA.csv.gz", keep_default_na=False, usecols=["d0", "d1", "d2", "d3", "value"])
    pos = list(read_csv(SETS / "LUCpos.csv", keep_default_na=False).d0)
    cls = list(read_csv(SETS / "luClass.csv", keep_default_na=False).d0)
    fr = read_csv(SETS / "luc_from_luClass.csv", keep_default_na=False)
    fr = fr[fr.d1.isin(cls)].set_index("d0").d1.to_dict()
    to = read_csv(SETS / "luc_to_luClass.csv", keep_default_na=False).set_index("d0").d1.to_dict()
    yrs = P[(P.d1 == "World") & (P.d2 == "calyea")].set_index("d0").value.astype(float)
    off = float(yrs["observed"] - yrs["initialLandUse"])
    pr = P[P.d3 == "T"].pivot_table(index=["d1", "d2"], columns="d0", values="value", aggfunc="first")
    fam = pr["distributionFamily"].dropna().unique()
    if len(fam) != 1:
        raise SystemExit(f"distribution families {fam}: only CAPRI's gamma density is ported (every transition has a "
                         f"positive mode in sim_ini_21730)")
    lev = D[D.d2 == "LEVL"]
    cal = {(t.d0, t.d1): float(t.value) for t in lev[lev.d3 == "CAL"].itertuples(index=False)}
    cur = {(t.d0, t.d1): float(t.value) for t in lev[lev.d3 == "CUR"].itertuples(index=False)}
    regs = sorted(set(P[P.d0 == "alpha"].d1))
    rows_p, rows_c, rows_s = [], [], []
    for r in regs:
        for p in pos:
            a, b, lo, up = (float(pr.at[(r, p), k]) for k in ("alpha", "beta", "lower", "upper"))
            rows_p.append((r, p, fr[p], to[p], 1.0 if fr[p] == to[p] else off, a, b, lo, up, cal.get((r, p), 0.0)))
        for c in cls:
            rows_c.append((r, c, float(pr.at[(r, c), "initialLandUse"]) if (r, c) in pr.index else 0.0,
                           cur.get((r, "INLW"), 0.0)))
        for t in SH[(SH.d0 == r) & (SH.d1 != "meanFromEU")].itertuples(index=False):
            rows_s.append((r, t.d1, t.d2, float(t.value)))
    pri = pd.DataFrame(rows_p, columns=["rms", "lucpos", "from_class", "to_class", "annual_factor", "alpha", "beta",
                                        "lower", "upper", "level_cal"])
    clas = pd.DataFrame(rows_c, columns=["rms", "luclass", "initial_kha", "inlw_kha"])
    shr = pd.DataFrame(rows_s, columns=["rms", "target", "source", "share"])
    to_csv(pri, PRIORS, index=False)
    to_csv(clas, CLASSES, index=False)
    to_csv(shr, SHARES, index=False)
    print(f"wrote {PRIORS.relative_to(ROOT)} ({len(regs)} regions x {len(pos)} transitions, annual factor {off:g}), "
          f"{CLASSES.relative_to(ROOT)}, {SHARES.relative_to(ROOT)} ({len(shr)} shares)")
    # the check: the port at CAPRI's calibration point
    from capri_mod.market.luc import LucParams, final_classes, solve_region
    prm = LucParams.from_frames(pri, clas, shr)
    worst = (0.0, "", "")
    for r in regs:
        land = {u: cal.get((r, u), 0.0) for u in LAND_TYPES if u != "INLW"}
        fin = final_classes(prm.regions[r], land)
        for c in cls:
            if abs(fin[c] - cal.get((r, c), 0.0)) > 1e-6 * max(1.0, cal.get((r, c), 0.0)):
                raise SystemExit(f"{r} {c}: the shares give {fin[c]:.6f}, CAPRI's DATA CAL {cal.get((r, c), 0.0):.6f}")
        x, info = solve_region(prm.regions[r], fin)
        ref = prm.regions[r]["level_cal"]
        rel = np.abs(x - ref) / np.maximum(np.abs(ref), 1e-3)
        k = int(np.argmax(rel))
        if rel[k] > worst[0]:
            worst = (float(rel[k]), r, prm.regions[r]["pos"][k])
        if info["residual"] > CHECK_TOL * max(1.0, float(np.max(prm.regions[r]["initial"]))):
            raise SystemExit(f"{r}: balances not met ({info['residual']:.3g})")
    print(f"  the port at CAPRI's CAL land against CAPRI's CAL transitions: worst relative deviation {worst[0]:.2e} "
          f"({worst[1]} {worst[2]})")
    if worst[0] > CHECK_TOL:
        raise SystemExit("the land-use-change port does not reproduce CAPRI's calibration point")


if __name__ == "__main__":
    main()

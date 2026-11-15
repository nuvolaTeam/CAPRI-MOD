"""The port of CAPRI's bounds, their widening and the fudge equations, step 1: CAPRI's start bounds as the model computes them (capri_mod/market/market_bounds.py) against the bounds
in CAPRI's dump of its market model at the calibration point (chk_market_data_<run>.gdx as parquet, --dump; a check
only).

The market is solved at CAPRI's base supply rows (the calibration point), the whole-market system's lifted form is built there and its
start bounds computed; compared per market region and commodity (CAPRI's RM; A_EU_WEST / A_EU_EAST the model's EU
blocks):
  price      r's bounds x PMrk (the model's Pd0)      against v_marketPrice.lower / .upper
  Armington  PA's bounds x PA0                        against v_arm1Price.lower / .upper
  use        D's bounds                               against v_arm1Quant.lower / .upper
  supply     S's bounds                               against v_prodQuant.lower / .upper of the market region (CAPRI
                                                      sums its behavioural regions' bounds; the model bounds the
                                                      market region's level, market_bounds.py)
Prints per family the cells, the largest relative gap of the lower and of the upper bound (scale max(|CAPRI|, 1e-6) for
the lower, max(|CAPRI|, 1) for the upper), the cells fixed in one and not the other; --csv writes every cell.

    python tools/check/check_capri_market_bounds.py --dump DIR [--csv OUT.csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args()
    from capri_mod.data.loaders import load_all_data
    from capri_mod.market.market_module import MarketModule
    from capri_mod.market.market_chain import build
    from capri_mod.market.market_bounds import capri_start_bounds
    data = load_all_data(ROOT / "capri_data")
    data["market_year"] = 2030
    mm = MarketModule(data)
    exo = mm.capri_base_supply_rows()
    eq = mm.solve(exogenous_supply=exo)
    print(f"market converged {eq.converged} in {eq.iterations} iterations", flush=True)
    ctx = build(mm, mm.sv.bilat_last_r.copy(), exo, None)
    lay, x0 = ctx["lay"], ctx["x0"]
    lb, ub = capri_start_bounds(mm, lay, x0)
    regions, cols = list(lay["regions"]), list(lay["cols"])
    nR = len(regions)
    sysd = mm.par.bilat
    bcols = [c for c in cols if c in sysd]
    m2r = pd.read_parquet(a.dump / "RM_TO_RMS.parquet")
    ours = {rm: (rm[2:] if rm.startswith("A_") else rm) for rm in m2r.d1.unique()}

    def capri(name):
        d = pd.read_parquet(a.dump / f"{name}.parquet")
        d = d[d.d1.isin(ours)].copy()
        d["region"] = d.d1.map(ours)
        return d.set_index(["region", "d2"])[["level", "lower", "upper"]]

    rows = []
    o = 0
    for name, n in lay["x"]:
        if name.startswith("r_"):
            c = name[2:]
            ref = capri("v_marketPrice")
            pd0 = np.asarray(sysd[c].Pd0, float)
            for i, rg in enumerate(sysd[c].regions):
                if (rg, c) in ref.index:
                    t = ref.loc[(rg, c)]
                    rows.append(dict(family="price", region=rg, commodity=c, model_lo=lb[o + i] * pd0[i],
                                     model_up=ub[o + i] * pd0[i], capri_lo=t.lower, capri_up=t.upper))
        elif name in ("PA", "D", "S"):
            fam, sym = {"PA": ("Armington", "v_arm1Price"), "D": ("use", "v_arm1Quant"),
                        "S": ("supply", "v_prodQuant")}[name]
            ref = capri(sym)
            if name == "PA":
                for k, c in enumerate(bcols):
                    pa0 = np.asarray(sysd[c].PA0, float)
                    for i, rg in enumerate(regions):
                        if (rg, c) in ref.index:
                            t = ref.loc[(rg, c)]
                            j = o + k * nR + i
                            rows.append(dict(family=fam, region=rg, commodity=c, model_lo=lb[j] * pa0[i],
                                             model_up=ub[j] * pa0[i], capri_lo=t.lower, capri_up=t.upper))
            else:
                for jc, c in enumerate(cols):                 # column by column
                    for i, rg in enumerate(regions):
                        if (rg, c) in ref.index:
                            t = ref.loc[(rg, c)]
                            j = o + jc * nR + i
                            rows.append(dict(family=fam, region=rg, commodity=c, model_lo=lb[j], model_up=ub[j],
                                             capri_lo=t.lower, capri_up=t.upper))
        o += n
    d = pd.DataFrame(rows)
    d["lo_rel"] = (d.model_lo - d.capri_lo).abs() / d.capri_lo.abs().clip(lower=1e-6)
    d["up_rel"] = (d.model_up - d.capri_up).abs() / d.capri_up.abs().clip(lower=1.0)
    d["fixed_model"] = d.model_lo == d.model_up
    d["fixed_capri"] = d.capri_lo == d.capri_up
    if a.csv:
        d.to_csv(a.csv, index=False)
    for fam, g in d.groupby("family", sort=False):
        print(f"{fam:10s}: {len(g):6d} cells; lower bound largest relative gap {g.lo_rel.max():.3g} "
              f"(above 1e-6: {int((g.lo_rel > 1e-6).sum())}); upper {g.up_rel.max():.3g} "
              f"(above 1e-6: {int((g.up_rel > 1e-6).sum())}); fixed in CAPRI only {int((g.fixed_capri & ~g.fixed_model).sum())}, "
              f"in the model only {int((g.fixed_model & ~g.fixed_capri).sum())}")
    w = d.assign(worst=d[["lo_rel", "up_rel"]].max(axis=1)).sort_values("worst", ascending=False)
    print(w.groupby("family").head(5)[["family", "region", "commodity", "model_lo", "capri_lo", "model_up",
                                        "capri_up"]].to_string(index=False, float_format=lambda v: f"{v:.6g}"))


if __name__ == "__main__":
    main()

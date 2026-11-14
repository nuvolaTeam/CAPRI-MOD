"""G3.2c, first block: the EU market regions' supply of the supply models' products (CAPRI's ProdNQ_ with the
measured Hessian) written as one expression of the system's unknowns, checked at the default solve's solutions.

In the default solve (SupplyMixin.supply_response) the rows come out of a sequence: the young-animal markets and the
member states' raw milk cleared in alternating rounds (_milk_and_yani_clear_all), then the rows
s0 + H dP + extra (supply_ad.hess_rows_function). In G3 the young-animal prices and the member states' milk prices are
unknowns, so the rows are one expression:

    q_x = max(0, s0_x + sum_c H_xc dP_c + sum_g H_xg (r_g - r_g^seen) + sum_m col_xm dL_m)

dP the product prices' change against those the supply models saw (SupplyMixin._nq_price_change), r_g the young-animal
prices the market cleared (ev.yani_market_now) and r_g^seen those the models saw, dL_m each member state's raw milk
price change against the one its models saw (the dairy block's ms_price_ratio less milk_seen_ms), col the Hessian's
products' response to the member state's milk price (SupplyMixin._milk_terms). Rows set later by the market's own
blocks (crushing, dairy, biofuels, feed by-products) are left out, and the EU's units outside a run on a subset (K83)
are added as the default solve adds them.

Each capture (G3.1) is replayed so the module holds its state after the solve; reported per solve and EU market
region: the largest difference between the expression and the equilibrium's supply on those rows, relative to
max(1, |supply|).

    python tools/check/g3_supply_residuals.py runs/capture [--files market_000.pkl,...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "check"))


def eu_rows_expression(mm, reg, cols, exogenous_supply, r):
    """(xs, q, used rows) of reg at the solution: the expression above, numerically."""
    H = (mm.par.supply_hessian or {}).get("blocks", {}).get(reg)
    hc = (getattr(mm, "_hess_cache", None) or {}).get(reg)
    if H is None or hc is None:
        return [], np.zeros(0), np.zeros(0, dtype=bool)
    _, xs, xj, Hm, _ = hc
    # s0: the supply models' output (supply_response: base production overwritten by the EU rows where they supply)
    base = mm.par.base_production.loc[reg, cols].astype(float).copy()
    ex = mm.eu_rows(exogenous_supply)
    xr = mm._eu_excluded_rows()
    for c in exogenous_supply.columns:
        if c not in cols:
            continue
        eu_val = float(ex.at[reg, c]) if reg in ex.index else 0.0
        x_val = float(xr.at[reg, c]) if (xr is not None and reg in xr.index and c in xr.columns) else 0.0
        if eu_val > 1e-6 or (xr is not None and eu_val + x_val > 1e-6):
            base[c] = eu_val
    s0 = base.to_numpy(dtype=float)[xj]
    seen_all = mm.seen.eu_price_seen
    seen = (seen_all.loc[reg] if isinstance(seen_all, pd.DataFrame) and reg in seen_all.index
            else (seen_all if isinstance(seen_all, pd.Series) else None))
    sv = (np.maximum(np.nan_to_num(seen.reindex(cols).to_numpy(dtype=float), nan=1.0), 0.2)
          if seen is not None else np.ones(len(cols)))
    for j, c in enumerate(cols):
        if c in mm.EU_MARKET_SUPPLY:
            sv[j] = 1.0
    rr = np.maximum(np.nan_to_num(r.loc[reg, cols].to_numpy(dtype=float), nan=1.0), 1e-6)
    dP = mm._nq_price_change(rr - sv, cols)
    extra = np.zeros(len(xs))
    st = (mm.seen.yani_state or {}).get(reg) or {}
    goods = [g for g in st.get("goods", []) if ("YANI:" + g) in H.index and ("YANI:" + g) in H.columns]
    if goods:
        now = (mm.ev.yani_market_now or {}).get(reg) or {}
        dlev = np.array([float(now.get(g, st["seen"].get(g, 1.0))) - float(st["seen"].get(g, 1.0)) for g in goods])
        H_PY = H.reindex(index=list(xs), columns=["YANI:" + g for g in goods]).fillna(0.0).to_numpy(dtype=float)
        extra += H_PY @ dlev
    mt = mm._milk_terms(cols, xs, H, reg)
    dl = mm.ev.dairy_last
    if mt is not None and dl is not None and "ms_price_ratio" in dl:
        dL = np.array([float(dl["ms_price_ratio"][m]["MILK"]) - float(mm.seen.milk_seen_ms.get(m, 1.0))
                       for m in mt["ms"]])
        extra += mt["col"] @ dL
    q = np.maximum(s0 + Hm @ dP + extra, 0.0)
    return list(xs), q, s0 > 1e-6


def noneu_rows_expression(mm, reg, cols, r):
    """(rows, q, used) of a non-EU market region at the solution: CAPRI's ProdNQ_ (supply_ad.nq_rows_function) at its
    price ratios, its dairy block's raw milk price ratio (1 + z_M), its CAPRI regions' feed energy prices FEDE and the
    land rents' shift: all unknowns of G3 (the rents and FEDE solved in turn in the default solve's evaluation)."""
    P = mm._noneu_nq_params()
    d = P.get(reg)
    if d is None:
        return [], np.zeros(0), np.zeros(0, dtype=bool)
    fr = mm._nq_rows(("noneu", reg), d["rows"], None, cols, d.get("fede") or {})
    if fr is None:
        return [], np.zeros(0), np.zeros(0, dtype=bool)
    f, rows, rms = fr
    wl, wp = mm.ev.dairy_world_last or {}, mm._dairy_world_params() or {}
    m = 1.0 + float(wl[reg]["z"][wp[reg]["iM"]]) if (reg in wl and reg in wp) else 1.0
    fede = mm.ev.fede_now or {}
    lsh = mm._noneu_land_shift(reg)
    rr = r.loc[reg, cols].to_numpy(dtype=float)
    rr = np.maximum(np.where(np.isnan(rr), 1.0, rr), 1e-6)
    q0 = mm._nq_q0(reg, rows)
    q = np.asarray(f(q0, rr, m, np.array([float(fede.get(s_, 1.0)) for s_ in rms]),
                     np.array([float(lsh.get(x, 0.0)) for x in rows]))[0]).ravel()
    return list(rows), q, q0 > 0


def check(path: Path) -> dict:
    from replay_market import load_module
    from capri_mod.settings import override
    with open(path, "rb") as fh:
        rec = pickle.load(fh)
    mm = load_module(rec["module"], path.parent / "blobs")
    with override(rec["settings"].replace({"diagnostics.capture_market_dir": ""})):
        eq = mm.solve(**rec["args"])
    exo = rec["args"]["exogenous_supply"]
    if exo is None:
        return {}
    r = mm.sv.bilat_last_r
    cols = [c for c in mm.commodities if c in mm.par.base_production.columns]
    later = set(mm.DAIRY_TRADED.values()) | {"MILK", "DDGS"}
    for o, c in mm.CRUSH_CHAINS.values():
        later |= {o, c}
    later |= {c for c in cols if str(c).startswith("BIO")}
    # the EU's units outside the run (K83): their member states' functions, added after the rows
    add = pd.DataFrame(0.0, index=mm.par.base_production.index, columns=cols)
    mm._add_eu_excluded(add, cols, lambda reg_: r.loc[reg_, cols].to_numpy(dtype=float))
    out = {}
    for reg in mm.EU:
        xs, q, used = eu_rows_expression(mm, reg, cols, exo, r)
        keep = [i for i, x in enumerate(xs) if used[i] and x not in later]
        if not keep:
            continue
        got = np.array([float(eq.production.at[reg, xs[i]]) for i in keep])
        want = np.array([q[i] + float(add.at[reg, xs[i]]) for i in keep])
        rel = np.abs(got - want) / np.maximum(np.abs(got), 1.0)
        k = int(np.argmax(rel))
        out[reg] = (float(rel[k]), xs[keep[k]], len(keep))
    # the non-EU market regions (Norway's supply-model products are its models'; biofuels and DDGS set later)
    sup = set(getattr(mm, "SUP", ()))
    for reg in (mm._noneu_nq_params() or {}):
        if reg not in eq.production.index:
            continue
        rows, q, used = noneu_rows_expression(mm, reg, cols, r)
        keep = [i for i, x in enumerate(rows) if used[i] and x in eq.production.columns and x not in later
                and not (reg in sup)]
        if not keep:
            continue
        got = np.array([float(eq.production.at[reg, rows[i]]) for i in keep])
        rel = np.abs(got - q[keep]) / np.maximum(np.abs(got), 1.0)
        k = int(np.argmax(rel))
        out[reg] = (float(rel[k]), rows[keep[k]], len(keep))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--files", default="")
    a = ap.parse_args()
    files = ([a.folder / f for f in a.files.split(",")] if a.files else sorted(a.folder.glob("market_*.pkl")))
    for f in files:
        res = check(f)
        eu = {k: v for k, v in res.items() if k in ("EU_WEST", "EU_EAST")}
        ne = {k: v for k, v in res.items() if k not in eu}
        w = max(ne.items(), key=lambda kv: kv[1][0]) if ne else None
        print(f"{f.name}: " + "; ".join(f"{reg} largest {v[0]:.2e} ({v[1]}) over {v[2]} rows" for reg, v in eu.items())
              + (f"; non-EU: {len(ne)} regions, {sum(v[2] for v in ne.values())} rows, largest {w[1][0]:.2e} "
                 f"({w[0]}, {w[1][1]})" if w else ""), flush=True)


if __name__ == "__main__":
    main()
